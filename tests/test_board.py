"""Lock #12: governed board drag and drop (JN1QYG), task locks and Gantt date drags,
bulk changes and WIP limits. Service-level behaviour; the HTTP and UI sides are in
test_web.py."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from astra.db import connect
from astra.service import (LOCK_GUARDED_KINDS, AstraService, Conflict, Forbidden, NeedsConfirmation, RuleRefusal,
                           TaskLocked)
from link_roots import allow_attachment_roots, link


class BoardFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / "board.sqlite3")
        self.service = AstraService(self.db)
        s = self.service
        self.owner = s.create_initial_owner("owner@example.org", "Owner", "owner password safe")
        self.second = s.create_user(self.owner, "second@example.org", "Second Owner", "second password safe")
        s.grant_secondary_owner(self.owner, self.second["id"], "cover")
        self.second = s.get_user(self.second["id"])
        self.manager = s.create_user(self.owner, "manager@example.org", "Manager", "manager password safe")
        self.member = s.create_user(self.owner, "member@example.org", "Member", "member password safe")
        self.project = s.create_project(self.owner, "Board project")
        pid = self.project["id"]
        s.grant_project_access(self.owner, pid, self.manager["id"], "manager")
        s.grant_project_access(self.owner, pid, self.member["id"], "member")
        self.task = s.create_task(self.owner, {"project_id": pid, "title": "Draft plan", "owner_user_id": self.member["id"]})

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def fresh(self, task_id=None):
        return self.service.get_task(self.owner, task_id or self.task["id"])

    def move(self, actor, to, task_id=None, **extra):
        task = self.fresh(task_id)
        return self.service.move_task(actor, task["id"], {"to_column": to, "expected_revision": task["revision"], **extra})

    def events(self, task_id=None):
        return self.service.task_events(self.owner, task_id or self.task["id"])


class BoardMoveTests(BoardFixture):
    def test_ordinary_moves_apply_with_a_system_reason_and_offer_undo(self):
        result = self.move(self.manager, "ready")
        self.assertEqual(result["task"]["status"], "assigned")
        self.assertEqual(result["undo"]["seconds"], 15)
        event = self.events()[-1]
        self.assertEqual((event["event_type"], event["reason"]), ("task_updated", "Board move: Draft → Ready"))
        self.assertEqual(result["undo"]["event_id"], event["id"])
        # The owners hear of a manager's status change as they do today.
        self.assertTrue(any(n["kind"] == "task_updated" for n in self.service.list_notifications(self.owner)))

    def test_undo_is_a_new_audited_change_and_refuses_after_a_later_change(self):
        result = self.move(self.manager, "progress")
        undone = self.service.undo_move(self.manager, self.task["id"], {"event_id": result["undo"]["event_id"]})
        self.assertEqual(undone["status"], "draft")
        kinds = [(e["event_type"], e["reason"]) for e in self.events()]
        self.assertEqual(kinds[-2][1], "Board move: Draft → In progress")
        self.assertTrue(kinds[-1][1].startswith("Undo of Draft → In progress (event "))
        self.assertEqual(len(kinds), 3)  # history is appended to, never rewritten
        # Undo twice, or someone else's undo, is refused.
        with self.assertRaises(ValueError):
            self.service.undo_move(self.manager, self.task["id"], {"event_id": result["undo"]["event_id"]})
        second = self.move(self.manager, "ready")
        with self.assertRaisesRegex(ValueError, "no move of yours"):
            self.service.undo_move(self.owner, self.task["id"], {"event_id": second["undo"]["event_id"]})
        # A later change in between: not reversed blindly.
        self.service.update_task(self.owner, self.task["id"], {"expected_revision": self.fresh()["revision"],
                                                               "title": "Draft plan v2"})
        with self.assertRaisesRegex(Conflict, "changed after your move"):
            self.service.undo_move(self.manager, self.task["id"], {"event_id": second["undo"]["event_id"]})

    def test_undo_window_is_fifteen_seconds_plus_grace(self):
        result = self.move(self.manager, "ready")
        old = (datetime.now(timezone.utc) - timedelta(seconds=21)).isoformat()
        self.db.execute("UPDATE task_events SET occurred_at=? WHERE id=?", (old, result["undo"]["event_id"]))
        with self.assertRaisesRegex(ValueError, "Undo window has passed"):
            self.service.undo_move(self.manager, self.task["id"], {"event_id": result["undo"]["event_id"]})

    def test_members_and_viewers_cannot_move_and_the_refusal_is_audited_and_noticed(self):
        with self.assertRaises(Forbidden):
            self.move(self.member, "ready")
        self.assertEqual(self.fresh()["status"], "draft")
        blocked = self.events()[-1]
        self.assertEqual(blocked["event_type"], "board_move_blocked")
        self.assertEqual(json.loads(blocked["after_json"]), {"column": "ready"})
        notices = [n for n in self.service.list_notifications(self.owner) if n["kind"] == "board_move_blocked"]
        self.assertEqual(len(notices), 1)

    def test_stale_board_is_a_conflict_not_an_audited_block(self):
        with self.assertRaises(Conflict):
            self.service.move_task(self.manager, self.task["id"], {"to_column": "ready", "expected_revision": 99})
        self.assertNotIn("board_move_blocked", [e["event_type"] for e in self.events()])

    def test_managers_protected_drops_file_the_existing_owner_requests(self):
        self.move(self.manager, "progress")
        closed = self.move(self.manager, "closed", status="cancelled", reason="Not needed")
        self.assertEqual(closed["request"]["action"], "update_task_status")
        self.assertEqual(self.fresh()["status"], "in_progress")

    def test_a_managers_drop_onto_blocked_holds_directly_without_undo(self):
        # Aly 2026-09-25 (Slack ts 1790342529.695749): managers put work on hold directly, with a reason.
        with self.assertRaises(NeedsConfirmation) as caught:
            self.move(self.manager, "blocked")
        self.assertEqual(caught.exception.confirm, "hold")
        held = self.move(self.manager, "blocked", reason="Vendor late", checkpoint_date="2026-10-10")
        self.assertEqual(held["task"]["status"], "on_hold")
        self.assertNotIn("undo", held)
        self.assertEqual(self.events()[-1]["event_type"], "task_on_hold")
        # Leaving Blocked is still an Owner decision for a manager.
        back = self.move(self.manager, "progress")
        self.assertEqual(back["request"]["action"], "update_task_status")
        self.assertEqual(self.fresh()["status"], "on_hold")

    def test_dialog_targets_ask_first(self):
        for column, kind in (("blocked", "hold"), ("closed", "close"), ("submitted", "submit")):
            with self.assertRaises(NeedsConfirmation) as caught:
                self.move(self.owner, column)
            self.assertEqual(caught.exception.confirm, kind)
        with self.assertRaisesRegex(ValueError, "Only a submitted task can be accepted"):
            self.move(self.owner, "accepted")

    def test_submit_and_accept_by_drag_reuse_the_lifecycle_actions(self):
        submitted = self.move(self.manager, "submitted", confirmed=True, note="Ready for review")
        self.assertEqual(submitted["task"]["status"], "submitted")
        self.assertNotIn("undo", submitted)
        # A manager's accept becomes an Owner request; an owner (primary or secondary) accepts.
        self.assertEqual(self.move(self.manager, "accepted", confirmed=True)["request"]["action"], "accept_submission")
        accepted = self.move(self.second, "accepted", confirmed=True)
        self.assertEqual(accepted["task"]["status"], "completed")
        # Leaving Accepted reopens, with a reason and a revised due date.
        with self.assertRaises(NeedsConfirmation) as caught:
            self.move(self.owner, "progress")
        self.assertEqual(caught.exception.confirm, "reopen")
        reopened = self.move(self.owner, "progress", reason="Auditor query", new_due_date="2026-11-01")
        self.assertEqual(reopened["task"]["status"], "reopened")

    def test_dependency_blocks_forward_moves_and_only_owners_override(self):
        pid = self.project["id"]
        first = self.service.create_task(self.owner, {"project_id": pid, "title": "Collect data"})
        self.service.add_task_dependency(self.owner, first["id"], self.task["id"])
        with self.assertRaisesRegex(ValueError, "waits on Collect data"):
            self.move(self.manager, "progress")
        self.assertEqual(self.events()[-1]["event_type"], "board_move_blocked")
        with self.assertRaises(NeedsConfirmation) as caught:
            self.move(self.owner, "progress")
        self.assertEqual((caught.exception.confirm, caught.exception.impact), ("dependencies", ["Collect data"]))
        moved = self.move(self.owner, "progress", override_dependencies=True)
        self.assertEqual(moved["task"]["status"], "in_progress")
        override = self.events()[-1]
        self.assertEqual((override["event_type"], json.loads(override["before_json"])),
                         ("dependency_override", {"blocked_by": ["Collect data"]}))
        # Moving back to Ready is not gated.
        self.assertEqual(self.move(self.manager, "ready")["task"]["status"], "assigned")

    def test_reorder_saves_the_column_order_and_is_history_only(self):
        pid = self.project["id"]
        second = self.service.create_task(self.owner, {"project_id": pid, "title": "Second"})
        third = self.service.create_task(self.owner, {"project_id": pid, "title": "Third"})
        order = [third["id"], self.task["id"], second["id"]]
        self.assertEqual(self.service.reorder_board(self.manager, pid, "draft", order), order)
        ranks = {t["id"]: t["board_rank"] for t in self.service.list_tasks(self.owner, pid)}
        self.assertEqual([ranks[i] for i in order], [1.0, 2.0, 3.0])
        event = self.service.project_events(self.owner, pid)[-1]
        self.assertEqual(event["event_type"], "board_reordered")
        self.assertEqual(json.loads(event["detail_json"])["after"], order)
        self.assertFalse([n for n in self.service.list_notifications(self.owner) if n["kind"] == "board_reordered"])
        self.assertEqual(self.fresh()["revision"], self.task["revision"])  # the order is not a task edit
        with self.assertRaises(Forbidden):
            self.service.reorder_board(self.member, pid, "draft", order)
        with self.assertRaises(Conflict):
            self.service.reorder_board(self.owner, pid, "ready", order)


class Review12aTests(BoardFixture):
    """Review 12a follow-ups on the board: the dependency rule on every path, undo markers,
    revisions checked under the write lock, whole-column ranks and which refusals are audited."""

    def waiting(self):
        first = self.service.create_task(self.owner, {"project_id": self.project["id"], "title": "Collect data"})
        self.service.add_task_dependency(self.owner, first["id"], self.task["id"])
        return first

    def test_m1_the_dependency_rule_holds_in_the_panel_and_the_api_too(self):
        self.waiting()
        rev = self.fresh()["revision"]
        with self.assertRaisesRegex(RuleRefusal, "waits on Collect data; it can move to In progress once that is completed"):
            self.service.update_task(self.manager, self.task["id"], {"status": "in_progress", "reason": "go", "expected_revision": rev})
        with self.assertRaisesRegex(RuleRefusal, "Only an owner may override a dependency"):
            self.service.submit_task(self.manager, self.task["id"], "done")
        with self.assertRaises(NeedsConfirmation) as caught:
            self.service.update_task(self.owner, self.task["id"], {"status": "in_progress", "reason": "go", "expected_revision": rev})
        self.assertEqual((caught.exception.confirm, caught.exception.impact), ("dependencies", ["Collect data"]))
        self.assertEqual(self.fresh()["status"], "draft")
        self.service.update_task(self.owner, self.task["id"], {"status": "in_progress", "reason": "go", "expected_revision": rev,
                                                              "override_dependencies": True})
        kinds = [e["event_type"] for e in self.events()]
        self.assertEqual(kinds[-2:], ["task_updated", "dependency_override"])  # one transaction, in order
        submission = self.service.submit_task(self.owner, self.task["id"], "done", override_dependencies=True)
        with self.assertRaises(NeedsConfirmation):
            self.service.accept_submission(self.owner, submission["id"], "ok")
        self.service.accept_submission(self.owner, submission["id"], "ok", override_dependencies=True)
        self.assertEqual(self.fresh()["status"], "completed")
        self.assertEqual([e["event_type"] for e in self.events()].count("dependency_override"), 3)

    def test_m1_l5_a_failed_write_leaves_no_override_behind(self):
        self.waiting()
        with self.assertRaises(Conflict):
            self.service.update_task(self.owner, self.task["id"], {"status": "in_progress", "reason": "go",
                                     "expected_revision": 99, "override_dependencies": True})
        self.assertNotIn("dependency_override", [e["event_type"] for e in self.events()])

    def test_l1_only_a_marked_board_move_can_be_undone(self):
        rev = self.fresh()["revision"]
        self.service.update_task(self.manager, self.task["id"], {"status": "assigned", "reason": "Board move: fake",
                                                                 "expected_revision": rev})
        fake = self.events()[-1]
        with self.assertRaisesRegex(ValueError, "no move of yours"):
            self.service.undo_move(self.manager, self.task["id"], {"event_id": fake["id"]})
        self.assertEqual(self.fresh()["status"], "assigned")
        # A move out of a status the board never offers Undo for is not undoable either.
        self.db.execute("UPDATE tasks SET status='changes_requested' WHERE id=?", (self.task["id"],))
        moved = self.move(self.owner, "ready")
        self.assertNotIn("undo", moved)
        with self.assertRaises(ValueError):
            self.service.undo_move(self.owner, self.task["id"], {"event_id": self.events()[-1]["id"]})

    def test_l2_a_stale_blocked_move_is_refused_under_the_write_lock(self):
        rev = self.fresh()["revision"]
        with self.assertRaises(Conflict):
            self.service.move_task(self.manager, self.task["id"], {"to_column": "blocked", "expected_revision": rev - 1,
                                   "reason": "late", "checkpoint_date": "2027-01-01"})
        self.service.update_task(self.owner, self.task["id"], {"title": "Renamed", "expected_revision": rev})
        for write in (lambda: self.service.set_on_hold(self.manager, self.task["id"], "late", "2027-01-01",
                                                       self.member["id"], expected_revision=rev),
                      lambda: self.service.submit_task(self.manager, self.task["id"], "done", expected_revision=rev)):
            with self.assertRaises(Conflict):
                write()
        self.assertEqual(self.fresh()["status"], "draft")

    def test_l3_a_partial_reorder_renumbers_the_whole_column(self):
        pid = self.project["id"]
        b = self.service.create_task(self.owner, {"project_id": pid, "title": "B"})
        c = self.service.create_task(self.owner, {"project_id": pid, "title": "C"})
        self.service.reorder_board(self.manager, pid, "draft", [self.task["id"], b["id"], c["id"]])
        after = self.service.reorder_board(self.manager, pid, "draft", [c["id"]])
        self.assertEqual(after, [c["id"], self.task["id"], b["id"]])
        ranks = sorted(t["board_rank"] for t in self.service.list_tasks(self.owner, pid))
        self.assertEqual(ranks, [1.0, 2.0, 3.0])  # no ties
        # A card that changes column is appended there unranked.
        self.move(self.manager, "ready", task_id=c["id"])
        self.assertIsNone(self.fresh(c["id"])["board_rank"])

    def test_l4_only_permission_and_rule_refusals_are_audited(self):
        self.move(self.manager, "ready")
        with self.assertRaisesRegex(ValueError, "already in Ready"):
            self.move(self.owner, "ready")
        with self.assertRaisesRegex(ValueError, "Only a submitted task can be accepted"):
            self.move(self.owner, "accepted")
        self.assertNotIn("board_move_blocked", [e["event_type"] for e in self.events()])
        with self.assertRaises(Forbidden):
            self.move(self.member, "draft")
        self.waiting()
        with self.assertRaises(RuleRefusal):
            self.move(self.manager, "progress")
        self.assertEqual([e["event_type"] for e in self.events()].count("board_move_blocked"), 2)

    def test_l7_member_refusal_accept_confirm_and_the_notice_cap(self):
        with self.assertRaisesRegex(Forbidden, "Only an owner or a manager of this project can move its tasks on the board"):
            self.move(self.member, "ready")
        self.service.submit_task(self.manager, self.task["id"], "done")
        with self.assertRaises(NeedsConfirmation) as caught:
            self.move(self.owner, "accepted")
        self.assertEqual(caught.exception.confirm, "accept")
        viewer = self.service.create_user(self.owner, "viewer@example.org", "Viewer", "viewer password safe")
        self.service.grant_project_access(self.owner, self.project["id"], viewer["id"], "viewer")
        for _ in range(6):
            with self.assertRaises(Forbidden):
                self.move(viewer, "ready")
        notices = [n for n in self.service.list_notifications(self.owner)
                   if n["kind"] == "board_move_blocked" and n["actor_user_id"] == viewer["id"]]
        self.assertEqual(len(notices), 5)
        self.assertEqual(len([e for e in self.events() if e["event_type"] == "board_move_blocked"
                              and e["actor_user_id"] == viewer["id"]]), 6)

    def test_undo_back_into_a_full_column_meets_the_wip_limit(self):
        pid = self.project["id"]
        moved = self.move(self.manager, "ready")
        other = self.service.create_task(self.owner, {"project_id": pid, "title": "Other"})
        self.service.set_wip_limit(self.owner, pid, "draft", 1)  # Other already fills Draft
        with self.assertRaisesRegex(RuleRefusal, "Draft is at its work-in-progress limit: 1 of 1"):
            self.service.undo_move(self.manager, self.task["id"], {"event_id": moved["undo"]["event_id"]})
        self.assertEqual(self.fresh()["status"], "assigned")
        # An owner's move out of Ready, then Ready fills to its limit: the Undo asks first.
        owned = self.move(self.owner, "progress")
        self.service.set_wip_limit(self.owner, pid, "ready", 1)
        self.service.update_task(self.owner, other["id"], {"status": "assigned", "reason": "fill Ready",
                                                           "expected_revision": self.fresh(other["id"])["revision"]})
        with self.assertRaises(NeedsConfirmation) as caught:
            self.service.undo_move(self.owner, self.task["id"], {"event_id": owned["undo"]["event_id"]})
        self.assertEqual(caught.exception.confirm, "wip")
        self.assertEqual(self.fresh()["status"], "in_progress")
        undone = self.service.undo_move(self.owner, self.task["id"], {"event_id": owned["undo"]["event_id"],
                                                                      "override_wip": True})
        self.assertEqual(undone["status"], "assigned")
        kinds = [e["event_type"] for e in self.events()]
        self.assertEqual(kinds[-2:], ["task_updated", "wip_limit_override"])  # one transaction, in order
        self.assertEqual(json.loads(self.events()[-1]["before_json"])["column"], "ready")

    def test_a_reorder_touching_a_task_someone_else_holds_writes_nothing(self):
        pid = self.project["id"]
        b = self.service.create_task(self.owner, {"project_id": pid, "title": "B"})
        self.service.reorder_board(self.manager, pid, "draft", [self.task["id"], b["id"]])
        events_before = len(self.service.project_events(self.owner, pid))
        self.service.acquire_task_lock(self.owner, b["id"], "edit")
        with self.assertRaisesRegex(TaskLocked, "is being changed by Owner") as caught:
            self.service.reorder_board(self.manager, pid, "draft", [b["id"], self.task["id"]])
        self.assertEqual(caught.exception.lock["holder_user_id"], self.owner["id"])
        ranks = {t["id"]: t["board_rank"] for t in self.service.list_tasks(self.owner, pid)}
        self.assertEqual((ranks[self.task["id"]], ranks[b["id"]]), (1.0, 2.0))
        self.assertEqual(len(self.service.project_events(self.owner, pid)), events_before)
        # The holder may reorder their own task.
        self.assertEqual(self.service.reorder_board(self.owner, pid, "draft", [b["id"]])[0], b["id"])

    def test_i1_a_card_blocked_only_by_a_dependency_can_be_put_on_hold(self):
        self.waiting()
        with self.assertRaises(NeedsConfirmation) as caught:
            self.move(self.manager, "blocked")
        self.assertEqual(caught.exception.confirm, "hold")
        held = self.move(self.manager, "blocked", reason="Vendor late", checkpoint_date="2027-01-01")
        self.assertEqual(held["task"]["status"], "on_hold")
        with self.assertRaisesRegex(ValueError, "already in Blocked"):
            self.move(self.manager, "blocked", reason="again", checkpoint_date="2027-01-02")


class Review12bTests(BoardFixture):
    """Review 12b follow-ups: every task write under the lease, renewals, the date-impact rule on
    every path, Undo marks, strict confirmation flags and the finish-to-start boundary."""

    def setUp(self):
        super().setUp()
        allow_attachment_roots(self)
        self.pid = self.project["id"]

    def new(self, title, **k):
        return self.service.create_task(self.owner, {"project_id": self.pid, "title": title, **k})

    def rev(self, task_id):
        return self.fresh(task_id)["revision"]

    def test_m1_l9_every_guarded_kind_and_every_write_path_respects_the_lease(self):
        s, o = self.service, self.owner
        self.assertEqual(LOCK_GUARDED_KINDS, frozenset({
            "task_updated", "task_submitted", "submission_accepted", "changes_requested", "task_reopened",
            "task_on_hold", "schedule_proposed", "schedule_revised", "schedule_proposal_rejected", "parent_changed",
            "dependency_added", "dependency_removed", "dependency_override", "criticality_changed",
            "attachment_added", "attachment_removed", "final_result_marked", "final_result_unmarked",
            "reviewer_added", "reviewer_removed"}))
        # The guard itself, for every kind.
        s.acquire_task_lock(self.manager, self.task["id"], "edit")
        for kind in sorted(LOCK_GUARDED_KINDS):
            with self.subTest(kind=kind), self.assertRaises(TaskLocked):
                s._event(self.task["id"], o["id"], kind, None, None, None, notify=False)
        parent, other = self.new("Parent"), self.new("Other")

        def submitted(t):
            return s.submit_task(o, t["id"], "done")

        def accepted(t):
            s.accept_submission(o, submitted(t)["id"], "ok")

        def attached(t):
            return s.add_task_attachment(o, t["id"], link("evidence", t["id"] + ".pdf"))

        def proposed(t):
            return s.propose_schedule(o, t["id"], "2027-02-01", "2027-02-05", "move")

        def linked(t):
            s.add_task_dependency(o, other["id"], t["id"])

        writes = {  # kind: (setup as the owner before the lease, the write the lease must refuse)
            "task_updated": (None, lambda t, _: s.update_task(o, t["id"], {"title": "x", "expected_revision": self.rev(t["id"])})),
            "task_submitted": (None, lambda t, _: s.submit_task(o, t["id"], "done")),
            "submission_accepted": (submitted, lambda t, sub: s.accept_submission(o, sub["id"], "ok")),
            "changes_requested": (submitted, lambda t, sub: s.request_changes(o, sub["id"], "redo")),
            "task_reopened": (accepted, lambda t, _: s.reopen_task(o, t["id"], "again", "2027-03-01")),
            "task_on_hold": (None, lambda t, _: s.set_on_hold(o, t["id"], "wait", "2027-01-01", self.member["id"])),
            "schedule_proposed": (None, lambda t, _: s.propose_schedule(o, t["id"], "2027-02-01", "2027-02-05", "m")),
            "schedule_revised": (proposed, lambda t, p: s.approve_schedule_proposal(o, p["id"], "ok")),
            "schedule_proposal_rejected": (proposed, lambda t, p: s.reject_schedule_proposal(o, p["id"], "no")),
            "parent_changed": (None, lambda t, _: s.set_parent(o, t["id"], parent["id"])),
            "dependency_added": (None, lambda t, _: s.add_task_dependency(o, other["id"], t["id"])),
            "dependency_removed": (linked, lambda t, _: s.remove_task_dependency(o, other["id"], t["id"], "unlink")),
            "criticality_changed": (None, lambda t, _: s.confirm_criticality(o, t["id"], "high", "evidence")),
            "attachment_added": (None, lambda t, _: s.add_task_attachment(o, t["id"], link("new.pdf"))),
            "attachment_removed": (attached, lambda t, a: s.remove_task_attachment(o, t["id"], a["id"])),
            "final_result_marked": (attached, lambda t, a: s.mark_final_result(o, t["id"], "attachment", a["id"])),
            "final_result_unmarked": (lambda t: s.mark_final_result(o, t["id"], "attachment", attached(t)["id"]),
                                      lambda t, r: s.unmark_final_result(o, r["id"])),
            "reviewer_added": (None, lambda t, _: s.add_task_reviewer(o, t["id"], self.member["id"], "reviewer")),
            "reviewer_removed": (lambda t: s.add_task_reviewer(o, t["id"], self.member["id"], "reviewer"),
                                 lambda t, _: s.remove_task_reviewer(o, t["id"], self.member["id"], "reviewer")),
        }
        # dependency_override only ever rides with a status change, which task_updated guards first.
        self.assertEqual(set(writes) | {"dependency_override"}, set(LOCK_GUARDED_KINDS))
        for kind, (setup, write) in writes.items():
            with self.subTest(write=kind):
                t = self.new(f"Locked {kind}")
                made = setup(t) if setup else None
                before = (self.rev(t["id"]), len(self.events(t["id"])))
                s.acquire_task_lock(self.manager, t["id"], "edit")
                with self.assertRaises(TaskLocked):
                    write(t, made)
                self.assertEqual((self.rev(t["id"]), len(self.events(t["id"]))), before)
        # A link from a locked predecessor is refused too.
        free = self.new("Free")
        with self.assertRaises(TaskLocked):
            s.add_task_dependency(o, self.task["id"], free["id"])
        s.force_unlock_task(o, self.task["id"])
        s.add_task_dependency(o, self.task["id"], free["id"])
        s.acquire_task_lock(self.manager, self.task["id"], "edit")
        with self.assertRaises(TaskLocked):
            s.remove_task_dependency(o, self.task["id"], free["id"], "unlink")

    def test_m1_reviewer_changes_are_audited(self):
        self.service.add_task_reviewer(self.owner, self.task["id"], self.member["id"], "approver")
        self.service.add_task_reviewer(self.owner, self.task["id"], self.member["id"], "approver")  # no-op, no row
        self.service.remove_task_reviewer(self.owner, self.task["id"], self.member["id"], "approver")
        rows = [(e["event_type"], json.loads(e["after_json"] or e["before_json"])) for e in self.events()
                if e["event_type"].startswith("reviewer_")]
        self.assertEqual(rows, [("reviewer_added", {"user_id": self.member["id"], "role": "approver"}),
                                ("reviewer_removed", {"user_id": self.member["id"], "role": "approver"})])

    def test_l3_an_expired_lease_is_not_revived_by_renewing(self):
        lock = self.service.acquire_task_lock(self.manager, self.task["id"], "edit")
        self.db.execute("UPDATE task_locks SET expires_at=?", ((datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat(),))
        self.service.update_task(self.owner, self.task["id"], {"title": "Changed meanwhile", "expected_revision": self.rev(self.task["id"])})
        with self.assertRaisesRegex(Conflict, "has ended"):
            self.service.renew_task_lock(self.manager, self.task["id"], lock["token"])

    def test_l9_another_persons_token_does_not_release_a_lease(self):
        lock = self.service.acquire_task_lock(self.manager, self.task["id"], "edit")
        self.assertEqual(self.service.release_task_lock(self.owner, self.task["id"], lock["token"]), {"released": False})
        self.assertEqual(self.service.task_detail(self.owner, self.task["id"])["lock"]["holder_user_id"], self.manager["id"])

    def test_l2_a_panel_date_change_with_consequences_asks_first(self):
        self.service.set_project_schedule(self.owner, self.pid, "2026-10-01", "2026-12-31", "Plan")
        body = {"due_date": "2027-01-10", "reason": "later", "expected_revision": self.rev(self.task["id"])}
        with self.assertRaises(NeedsConfirmation) as caught:
            self.service.update_task(self.manager, self.task["id"], body)
        self.assertEqual(caught.exception.confirm, "impact")
        self.assertTrue(any("after the project target (2026-12-31)" in i for i in caught.exception.impact))
        with self.assertRaises(NeedsConfirmation):  # L7: only a real true confirms
            self.service.update_task(self.manager, self.task["id"], {**body, "confirmed": "yes"})
        self.assertIsNone(self.fresh()["due_date"])
        self.service.update_task(self.manager, self.task["id"], {**body, "confirmed": True})
        kinds = [e["event_type"] for e in self.events()]
        self.assertEqual(kinds[-2:], ["task_updated", "schedule_impact_confirmed"])  # one transaction
        for owner in (self.owner, self.second):
            self.assertTrue([n for n in self.service.list_notifications(owner) if n["kind"] == "schedule_impact_confirmed"])
        # A date change without consequences applies as before.
        self.service.update_task(self.manager, self.task["id"], {"due_date": "2026-12-01", "reason": "earlier",
                                                                 "expected_revision": self.rev(self.task["id"])})
        self.assertEqual(self.fresh()["due_date"], "2026-12-01")

    def test_l4_only_marked_gantt_moves_undo_and_confirmed_ones_do_not(self):
        side = self.new("Side", start_date="2026-10-05", due_date="2026-10-08")
        self.service.update_task(self.manager, side["id"], {"due_date": "2026-10-09", "reason": "Gantt drag: fake",
                                                            "expected_revision": self.rev(side["id"])})
        with self.assertRaisesRegex(ValueError, "no move of yours"):
            self.service.undo_move(self.manager, side["id"], {"event_id": self.events(side["id"])[-1]["id"]})
        self.service.set_project_schedule(self.owner, self.pid, "2026-10-01", "2026-10-10", "Plan")
        moved = self.service.reschedule_task(self.manager, side["id"], {"start_date": "2026-10-05", "due_date": "2026-10-12",
                                             "expected_revision": self.rev(side["id"]), "confirmed": True})
        self.assertNotIn("undo", moved)
        moved_event = [e for e in self.events(side["id"]) if e["event_type"] == "task_updated"][-1]
        with self.assertRaisesRegex(ValueError, "no move of yours"):
            self.service.undo_move(self.manager, side["id"], {"event_id": moved_event["id"]})

    def test_l7_flags_must_be_true_not_just_truthy(self):
        first = self.new("Collect")
        self.service.add_task_dependency(self.owner, first["id"], self.task["id"])
        with self.assertRaises(NeedsConfirmation):
            self.move(self.owner, "progress", override_dependencies="true")
        with self.assertRaises(NeedsConfirmation):
            self.move(self.owner, "submitted", confirmed=1, override_dependencies=True)
        self.service.set_wip_limit(self.owner, self.pid, "ready", 1)
        self.move(self.owner, "ready", task_id=first["id"])
        free = self.new("Free")
        with self.assertRaises(NeedsConfirmation):
            self.move(self.owner, "ready", task_id=free["id"], override_wip="yes")

    def test_i1_a_successor_may_start_on_the_day_its_predecessor_is_due(self):
        first = self.new("First", start_date="2026-10-01", due_date="2026-10-20")
        then = self.new("Then", start_date="2026-10-21", due_date="2026-11-10")
        self.service.add_task_dependency(self.owner, first["id"], then["id"])
        probe = {**self.fresh(then["id"]), "is_critical_path": False, "project_target_date": None}
        self.assertEqual(self.service._schedule_impact(probe, "2026-10-20", "2026-11-10"), [])
        self.assertEqual(len(self.service._schedule_impact(probe, "2026-10-19", "2026-11-10")), 1)

    def test_l6_l9_refused_api_moves_notice_owners_up_to_the_cap(self):
        side = self.new("Side", start_date="2026-10-05", due_date="2026-10-08")
        for _ in range(6):
            with self.assertRaises(Forbidden):
                self.service.reschedule_task(self.member, side["id"], {"due_date": "2026-10-09", "expected_revision": self.rev(side["id"])})
        with self.assertRaises(ValueError):  # plain validation: back to the actor only
            self.service.reschedule_task(self.manager, side["id"], {"due_date": "not a date", "expected_revision": self.rev(side["id"])})
        self.assertEqual([e["event_type"] for e in self.events(side["id"])].count("gantt_move_blocked"), 6)
        notices = [n for n in self.service.list_notifications(self.owner) if n["kind"] == "gantt_move_blocked"]
        self.assertEqual(len(notices), 5)


class Review12cTests(BoardFixture):
    """Review 12c follow-ups: the work-in-progress limit on every status-changing write, bulk
    drift and leases, strict inputs, and the limits dialog in one transaction."""

    def setUp(self):
        super().setUp()
        self.pid = self.project["id"]

    def new(self, title, **k):
        return self.service.create_task(self.owner, {"project_id": self.pid, "title": title, **k})

    def rev(self, task_id):
        return self.fresh(task_id)["revision"]

    def kinds(self, task_id):
        return [e["event_type"] for e in self.events(task_id)]

    def test_m1_panel_create_and_promotion_meet_the_limit(self):
        self.new("In Ready", status="assigned")
        self.service.set_wip_limit(self.owner, self.pid, "ready", 1)
        body = {"status": "assigned", "reason": "ready", "expected_revision": self.rev(self.task["id"])}
        with self.assertRaisesRegex(RuleRefusal, "Ready is at its work-in-progress limit: 1 of 1"):
            self.service.update_task(self.manager, self.task["id"], body)
        with self.assertRaises(NeedsConfirmation) as caught:
            self.service.update_task(self.owner, self.task["id"], body)
        self.assertEqual(caught.exception.confirm, "wip")
        self.service.update_task(self.owner, self.task["id"], {**body, "override_wip": True})
        self.assertEqual(self.kinds(self.task["id"])[-2:], ["task_updated", "wip_limit_override"])  # L4: one transaction
        with self.assertRaises(RuleRefusal):
            self.service.create_task(self.manager, {"project_id": self.pid, "title": "Too many", "status": "assigned"})
        self.assertFalse([t for t in self.service.list_tasks(self.owner, self.pid) if t["title"] == "Too many"])
        made = self.service.create_task(self.owner, {"project_id": self.pid, "title": "Owner's", "status": "assigned",
                                                     "override_wip": True})
        self.assertIn("wip_limit_override", self.kinds(made["id"]))
        step = self.service.create_task(self.owner, {"project_id": self.pid, "title": "Step", "status": "assigned",
                                                     "parent_task_id": self.task["id"]})  # a step does not count
        with self.assertRaises(RuleRefusal):
            self.service.set_parent(self.manager, step["id"], None)
        self.assertEqual(self.fresh(step["id"])["parent_task_id"], self.task["id"])

    def test_m1_hold_submit_reopen_and_owner_approval(self):
        s = self.service
        held = self.new("Held")
        s.set_on_hold(self.owner, held["id"], "wait", "2027-01-01", self.member["id"])
        s.set_wip_limit(self.owner, self.pid, "blocked", 1)
        with self.assertRaisesRegex(RuleRefusal, "Blocked is at its work-in-progress limit"):
            s.set_on_hold(self.manager, self.task["id"], "wait", "2027-01-01", self.member["id"])
        # Entering Blocked because of a dependency is not refused: nobody moved the card.
        first = self.new("First")
        s.add_task_dependency(self.owner, first["id"], self.task["id"])
        self.assertEqual(s._column_counts(self.owner, self.pid)["blocked"], 2)
        s.remove_task_dependency(self.owner, first["id"], self.task["id"], "unlink")
        s.set_wip_limit(self.owner, self.pid, "submitted", 1)
        s.submit_task(self.owner, first["id"], "done")
        work = s.create_task(self.owner, {"project_id": self.pid, "title": "Member work", "owner_user_id": self.member["id"]})
        with self.assertRaises(RuleRefusal):
            s.submit_task(self.member, work["id"], "done")
        self.assertEqual(self.fresh(work["id"])["status"], "draft")
        # Reopening into a full In progress asks the owner.
        s.accept_submission(self.owner, [x for x in s.list_task_submissions(self.owner, first["id"])][0]["id"], "ok")
        s.set_wip_limit(self.owner, self.pid, "progress", 1)
        s.update_task(self.owner, self.task["id"], {"status": "in_progress", "reason": "go", "expected_revision": self.rev(self.task["id"])})
        with self.assertRaises(NeedsConfirmation):
            s.reopen_task(self.owner, first["id"], "again", "2027-03-01")
        s.reopen_task(self.owner, first["id"], "again", "2027-03-01", override_wip=True)
        self.assertEqual(self.kinds(first["id"])[-2:], ["task_reopened", "wip_limit_override"])
        # Review 12d M2: an owner's approval of a manager's off-hold request into the full column
        # asks the owner first; only the confirmed approval goes over, in the owner's name.
        s.set_wip_limit(self.owner, self.pid, "blocked", None)
        request = s.update_task(self.manager, held["id"], {"status": "in_progress", "reason": "vendor back",
                                                          "expected_revision": self.rev(held["id"])})["request"]
        with self.assertRaises(NeedsConfirmation) as asked:
            s.decide_owner_action_request(self.owner, request["id"], "approved", "ok")
        self.assertEqual(asked.exception.confirm, "wip")
        self.assertEqual(self.fresh(held["id"])["status"], "on_hold")
        self.assertNotIn("wip_limit_override", self.kinds(held["id"]))
        self.assertEqual(s._owner_action_request(self.owner, request["id"])["status"], "pending")
        s.decide_owner_action_request(self.owner, request["id"], "approved", "ok", override_wip=True)
        self.assertEqual(self.fresh(held["id"])["status"], "in_progress")
        row = self.service.db.execute("SELECT actor_user_id FROM task_events WHERE task_id=? AND event_type='wip_limit_override'",
                                      (held["id"],)).fetchone()
        self.assertEqual(row["actor_user_id"], self.owner["id"])

    def test_m1_bulk_undo_meets_the_limit(self):
        s = self.service
        other = self.new("Other")
        plan = s.bulk_preview(self.manager, self.pid, {"task_ids": [self.task["id"], other["id"]], "action": "status", "value": "ready"})
        out = s.bulk_apply(self.manager, self.pid, {"task_ids": [self.task["id"], other["id"]], "action": "status", "value": "ready",
                                                    "expected_revisions": {i["id"]: i["revision"] for i in plan["ok"]}})
        self.new("Filler")  # Draft now holds one card; the bulk moved the others out
        s.set_wip_limit(self.owner, self.pid, "draft", 1)
        with self.assertRaisesRegex(RuleRefusal, "Draft is at its work-in-progress limit"):
            s.bulk_undo(self.manager, self.pid, {"bulk_id": out["bulk_id"]})
        self.assertEqual({self.fresh(i)["status"] for i in (self.task["id"], other["id"])}, {"assigned"})

    def test_l1_a_plan_that_drifts_after_the_preview_is_refused(self):
        s = self.service
        a, b, c = self.new("A"), self.new("B"), self.new("C")
        s.set_wip_limit(self.owner, self.pid, "progress", 2)
        ids = [a["id"], b["id"]]
        plan = s.bulk_preview(self.manager, self.pid, {"task_ids": ids, "action": "status", "value": "progress"})
        self.assertIsNone(plan["wip"])
        real = s._take_bulk_leases

        def meanwhile(*args, **kwargs):  # another move lands between the plan and the write
            s.update_task(self.owner, c["id"], {"status": "in_progress", "reason": "go", "expected_revision": self.rev(c["id"])})
            return real(*args, **kwargs)
        s._take_bulk_leases = meanwhile
        with self.assertRaisesRegex(Conflict, "changed since the preview"):
            s.bulk_apply(self.manager, self.pid, {"task_ids": ids, "action": "status", "value": "progress",
                                                  "expected_revisions": {i["id"]: i["revision"] for i in plan["ok"]}})
        s._take_bulk_leases = real
        self.assertEqual({self.fresh(i)["status"] for i in ids}, {"draft"})
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM task_locks").fetchone()[0], 0)

    def test_l2_a_bulk_keeps_the_actors_own_lease(self):
        s = self.service
        lock = s.acquire_task_lock(self.manager, self.task["id"], "edit")
        other = self.new("Other")
        ids = [self.task["id"], other["id"]]
        plan = s.bulk_preview(self.manager, self.pid, {"task_ids": ids, "action": "status", "value": "ready"})
        s.bulk_apply(self.manager, self.pid, {"task_ids": ids, "action": "status", "value": "ready",
                                              "expected_revisions": {i["id"]: i["revision"] for i in plan["ok"]}})
        row = self.db.execute("SELECT kind, token FROM task_locks WHERE task_id=?", (self.task["id"],)).fetchone()
        self.assertEqual((row["kind"], row["token"]), ("edit", lock["token"]))
        self.assertEqual(s.renew_task_lock(self.manager, self.task["id"], lock["token"])["token"], lock["token"])

    def test_l3_strict_revisions_and_out_of_range_dates(self):
        s = self.service
        body = {"task_ids": [self.task["id"]], "action": "status", "value": "ready"}
        for bad in ([1], {self.task["id"]: True}, {self.task["id"]: "1"}, None):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "expected_revisions"):
                s.bulk_apply(self.manager, self.pid, {**body, "expected_revisions": bad})
        far = self.new("Far", due_date="9999-12-25")
        plan = s.bulk_preview(self.manager, self.pid, {"task_ids": [far["id"]], "action": "due_shift", "value": 10})
        self.assertEqual(plan["blocked"][0]["reason"], "the new date is out of range")

    def test_l4_a_bulk_override_is_recorded_with_the_bulk(self):
        s = self.service
        other = self.new("Other")
        s.set_wip_limit(self.owner, self.pid, "ready", 1)
        ids = [self.task["id"], other["id"]]
        plan = s.bulk_preview(self.owner, self.pid, {"task_ids": ids, "action": "status", "value": "ready"})
        real = s._project_event
        calls = []

        def failing(project_id, actor_id, kind, *args, **kwargs):
            calls.append(kind)
            if kind == "wip_limit_override":
                raise RuntimeError("disk full")
            return real(project_id, actor_id, kind, *args, **kwargs)
        s._project_event = failing
        with self.assertRaises(RuntimeError):
            s.bulk_apply(self.owner, self.pid, {"task_ids": ids, "action": "status", "value": "ready", "override_wip": True,
                                                "expected_revisions": {i["id"]: i["revision"] for i in plan["ok"]}})
        s._project_event = real
        self.assertEqual(calls, ["bulk_change", "wip_limit_override"])
        self.assertEqual({self.fresh(i)["status"] for i in ids}, {"draft"})  # the whole bulk rolled back

    def test_l6_limits_are_whole_numbers_and_save_together(self):
        s = self.service
        for bad in (2.7, "2.7", "abc", True, [], -1, 1000):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                s.set_wip_limit(self.owner, self.pid, "ready", bad)
        self.assertEqual(s.set_wip_limit(self.owner, self.pid, "ready", "3"), {"ready": 3})
        self.assertEqual(s.set_wip_limits(self.owner, self.pid, {"ready": 3, "progress": 2, "blocked": "4"}, "Plan"),
                         {"ready": 3, "progress": 2, "blocked": 4})
        changed = [json.loads(e["detail_json"])["column"] for e in s.project_events(self.owner, self.pid)
                   if e["event_type"] == "wip_limit_changed"]
        self.assertEqual(changed, ["ready", "progress", "blocked"])  # ready unchanged the second time
        with self.assertRaises(ValueError):
            s.set_wip_limits(self.owner, self.pid, {"draft": 2, "accepted": 1})
        self.assertNotIn("draft", s.wip_limits(self.pid))  # nothing saved when one column is refused
        with self.assertRaises(Forbidden):
            s.set_wip_limits(self.manager, self.pid, {"draft": 2})


class Review12dTests(BoardFixture):
    """Re-review 12d: the bulk write stays short however large the project, an approval meets
    the same rules as acting directly, reopen and schedule approval ask about new dates, and
    the revert experiments that survived 12c."""

    def setUp(self):
        super().setUp()
        self.pid = self.project["id"]

    def new(self, title, **k):
        return self.service.create_task(self.owner, {"project_id": self.pid, "title": title, **k})

    def rev(self, task_id):
        return self.fresh(task_id)["revision"]

    def kinds(self, task_id):
        return [e["event_type"] for e in self.events(task_id)]

    def request_for(self, task_id):
        return next(r for r in self.service.list_owner_action_requests(self.owner) if r["task_id"] == task_id)

    def event_actor(self, task_id, kind):
        row = self.db.execute("SELECT actor_user_id FROM task_events WHERE task_id=? AND event_type=?"
                              " ORDER BY occurred_at DESC, rowid DESC LIMIT 1", (task_id, kind)).fetchone()
        return row["actor_user_id"] if row else None

    def test_m1_a_200_task_bulk_in_a_1000_task_project_is_quick(self):
        import time
        s = self.service
        now = datetime.now(timezone.utc).isoformat()
        rows = [(f"t{i:04d}", self.pid, f"Big {i}", now, self.owner["id"], now) for i in range(1000)]
        self.db.executemany(  # seeded directly: 1000 create_task calls would only slow the suite
            "INSERT INTO tasks(id,project_id,title,description,status,criticality,due_date,created_at,created_by,updated_at)"
            " VALUES(?,?,?,'','draft','normal','2026-11-10',?,?,?)", rows)
        for i in range(0, 60, 2):  # some waits, as in the reviewer's probe
            s.add_task_dependency(self.owner, f"t{i:04d}", f"t{i + 1:04d}")
        s.set_wip_limit(self.owner, self.pid, "ready", 500)
        ids = [f"t{i:04d}" for i in range(100, 300)]
        body = {"task_ids": ids, "action": "status", "value": "ready"}
        plan = s.bulk_preview(self.manager, self.pid, body)
        self.assertEqual(plan["counts"]["ok"], 200)
        started = time.monotonic()
        done = s.bulk_apply(self.manager, self.pid, {**body, "expected_revisions": {i["id"]: i["revision"] for i in plan["ok"]}})
        applied = time.monotonic() - started
        started = time.monotonic()
        s.bulk_undo(self.manager, self.pid, {"bulk_id": done["bulk_id"]})
        undone = time.monotonic() - started
        # A generous bound: the 12d build took 33 s here; the snapshot build takes a fraction of a second.
        self.assertLess(applied, 2.0)
        self.assertLess(undone, 2.0)
        self.assertEqual({self.fresh(i)["status"] for i in ids}, {"draft"})

    def test_m1_single_task_paths_load_the_project_at_most_once(self):
        s = self.service
        s.set_wip_limits(self.owner, self.pid, {"ready": 5, "progress": 5, "submitted": 5, "blocked": 5})
        pred = self.new("Pred", due_date="2026-11-01")
        succ = self.new("Succ", start_date="2026-11-03", due_date="2026-11-05")
        s.add_task_dependency(self.owner, pred["id"], succ["id"])
        loads = []
        real = s.list_tasks
        s.list_tasks = lambda *a, **k: loads.append(1) or real(*a, **k)
        try:
            steps = {
                "board move": lambda: self.move(self.manager, "ready"),
                "panel status": lambda: s.update_task(self.manager, self.task["id"], {
                    "status": "in_progress", "reason": "go", "expected_revision": self.rev(self.task["id"])}),
                "panel dates": lambda: s.update_task(self.manager, self.task["id"], {
                    "due_date": "2026-11-20", "reason": "later", "expected_revision": self.rev(self.task["id"])}),
                "gantt drag": lambda: s.reschedule_task(self.manager, pred["id"], {
                    "start_date": None, "due_date": "2026-11-02", "expected_revision": self.rev(pred["id"]),
                    "confirmed": True}),
                "submit": lambda: s.submit_task(self.manager, self.task["id"], "done"),
                "hold": lambda: s.set_on_hold(self.manager, succ["id"], "wait", "2027-01-01", self.member["id"]),
            }
            for name, step in steps.items():
                loads.clear()
                step()
                with self.subTest(path=name):
                    self.assertLessEqual(len(loads), 1)
        finally:
            s.list_tasks = real

    def test_m2_the_reviewers_repro_an_accept_request_filed_while_waiting(self):
        s = self.service
        pre = self.new("Pre")
        s.update_task(self.owner, pre["id"], {"status": "in_progress", "reason": "go", "expected_revision": self.rev(pre["id"])})
        w = s.create_task(self.owner, {"project_id": self.pid, "title": "W", "owner_user_id": self.member["id"]})
        submission = s.submit_task(self.member, w["id"], "done")
        s.add_task_dependency(self.manager, pre["id"], w["id"])
        filed = s.accept_submission(self.manager, submission["id"], "looks fine")
        self.assertIn("request", filed)
        request = self.request_for(w["id"])
        self.assertEqual(request["gates"]["lines"], ["Waits on Pre"])  # shown on the Inbox card
        with self.assertRaises(NeedsConfirmation) as asked:
            s.decide_owner_action_request(self.owner, request["id"], "approved", "ok")
        self.assertEqual((asked.exception.confirm, asked.exception.impact), ("dependencies", ["Pre"]))
        self.assertEqual(self.fresh(w["id"])["status"], "submitted")
        self.assertNotIn("dependency_override", self.kinds(w["id"]))
        self.assertEqual(self.request_for(w["id"])["status"], "pending")
        s.decide_owner_action_request(self.owner, request["id"], "approved", "ok", override_dependencies=True)
        self.assertEqual(self.fresh(w["id"])["status"], "completed")
        self.assertEqual(self.event_actor(w["id"], "dependency_override"), self.owner["id"])
        # "True" only: a truthy flag is not a confirmation.
        with self.assertRaises(NeedsConfirmation):
            other = s.create_task(self.owner, {"project_id": self.pid, "title": "W2", "owner_user_id": self.member["id"]})
            sub2 = s.submit_task(self.member, other["id"], "done")
            s.add_task_dependency(self.manager, pre["id"], other["id"])
            s.accept_submission(self.manager, sub2["id"], "fine")
            s.decide_owner_action_request(self.owner, self.request_for(other["id"])["id"], "approved", "ok",
                                          override_dependencies="yes")

    def test_m2_a_wait_added_after_the_request_was_filed_still_asks(self):
        s = self.service
        pre = self.new("Pre")
        held = self.new("Held")
        s.set_on_hold(self.owner, held["id"], "wait", "2027-01-01", self.member["id"])
        request = s.update_task(self.manager, held["id"], {"status": "in_progress", "reason": "back",
                                                          "expected_revision": self.rev(held["id"])})["request"]
        self.assertEqual(self.request_for(held["id"])["gates"]["lines"], [])
        s.add_task_dependency(self.owner, pre["id"], held["id"])
        self.assertEqual(self.request_for(held["id"])["gates"]["lines"], ["Waits on Pre"])
        with self.assertRaises(NeedsConfirmation) as asked:
            s.decide_owner_action_request(self.owner, request["id"], "approved", "ok")
        self.assertEqual(asked.exception.confirm, "dependencies")
        s.decide_owner_action_request(self.owner, request["id"], "approved", "ok", override_dependencies=True)
        self.assertEqual(self.fresh(held["id"])["status"], "in_progress")

    def test_m2_the_card_names_the_limit_and_the_dates(self):
        s = self.service
        s.set_project_schedule(self.owner, self.pid, None, "2026-12-31", "plan")
        busy = self.new("Busy")
        s.update_task(self.owner, busy["id"], {"status": "in_progress", "reason": "go", "expected_revision": self.rev(busy["id"])})
        s.set_wip_limit(self.owner, self.pid, "progress", 1)
        held = self.new("Held")
        s.set_on_hold(self.owner, held["id"], "wait", "2027-01-01", self.member["id"])
        s.update_task(self.manager, held["id"], {"status": "in_progress", "reason": "back", "expected_revision": self.rev(held["id"])})
        self.assertEqual(self.request_for(held["id"])["gates"], {"lines": ["In progress is at 1 of 1"], "column": "progress"})
        late = self.new("Late", due_date="2026-12-01")
        s.propose_schedule(self.manager, late["id"], None, "2027-02-01", "slipped")
        proposal = s.list_schedule_proposals(self.owner, late["id"])[0]
        s.approve_schedule_proposal(self.manager, proposal["id"], "please")
        lines = self.request_for(late["id"])["gates"]["lines"]
        self.assertEqual(lines, ["The new due date is after the project target (2026-12-31)."])

    def test_l1_reopen_and_schedule_approval_ask_about_new_dates(self):
        s = self.service
        s.set_project_schedule(self.owner, self.pid, None, "2026-12-31", "plan")
        done = self.new("Done", due_date="2026-11-01")
        s.submit_task(self.owner, done["id"], "done")
        s.accept_submission(self.owner, s.list_task_submissions(self.owner, done["id"])[0]["id"], "ok")
        with self.assertRaises(NeedsConfirmation) as asked:
            s.reopen_task(self.owner, done["id"], "again", "2027-03-01")
        self.assertEqual(asked.exception.confirm, "impact")
        self.assertEqual(self.fresh(done["id"])["status"], "completed")
        s.reopen_task(self.owner, done["id"], "again", "2027-03-01", confirmed=True)
        self.assertEqual(self.kinds(done["id"])[-2:], ["task_reopened", "schedule_impact_confirmed"])
        # The owner approving a proposal directly, and through a manager's request.
        late = self.new("Late", due_date="2026-12-01")
        s.propose_schedule(self.manager, late["id"], None, "2027-02-01", "slipped")
        proposal = s.list_schedule_proposals(self.owner, late["id"])[0]
        with self.assertRaises(NeedsConfirmation):
            s.approve_schedule_proposal(self.owner, proposal["id"], "ok")
        self.assertEqual(self.fresh(late["id"])["due_date"], "2026-12-01")
        request = s.approve_schedule_proposal(self.manager, proposal["id"], "please")["request"]
        with self.assertRaises(NeedsConfirmation):
            s.decide_owner_action_request(self.owner, request["id"], "approved", "ok")
        s.decide_owner_action_request(self.owner, request["id"], "approved", "ok", confirmed=True)
        self.assertEqual(self.fresh(late["id"])["due_date"], "2027-02-01")
        self.assertEqual(self.kinds(late["id"])[-3:-1], ["schedule_revised", "schedule_impact_confirmed"])
        self.assertEqual(self.event_actor(late["id"], "schedule_impact_confirmed"), self.owner["id"])
        # A reopen date inside the target asks nothing.
        again = self.new("Again", due_date="2026-11-01")
        s.submit_task(self.owner, again["id"], "done")
        s.accept_submission(self.owner, s.list_task_submissions(self.owner, again["id"])[0]["id"], "ok")
        s.reopen_task(self.owner, again["id"], "again", "2026-11-20")
        self.assertNotIn("schedule_impact_confirmed", self.kinds(again["id"]))

    # ---- L2: revert experiments that survived 12c ----

    def test_l2_a_step_does_not_count_toward_a_limit(self):
        s = self.service
        s.update_task(self.owner, self.task["id"], {"status": "assigned", "reason": "r", "expected_revision": self.rev(self.task["id"])})
        self.new("Step", status="assigned", parent_task_id=self.task["id"])
        self.assertEqual(s._column_counts(self.owner, self.pid).get("ready"), 1)
        s.set_wip_limit(self.owner, self.pid, "ready", 2)
        other = self.new("Other")
        self.move(self.manager, "ready", other["id"])  # 2 of 2: the step is not counted
        self.assertEqual(self.fresh(other["id"])["status"], "assigned")

    def test_l2_a_bulk_takes_at_most_200_tasks(self):
        ids = [f"x{i}" for i in range(201)]
        with self.assertRaisesRegex(ValueError, "Select between 1 and 200 tasks"):
            self.service.bulk_preview(self.manager, self.pid, {"task_ids": ids, "action": "status", "value": "ready"})

    def test_l2_bulk_undo_closes_after_the_window(self):
        s = self.service
        body = {"task_ids": [self.task["id"]], "action": "status", "value": "ready"}
        plan = s.bulk_preview(self.manager, self.pid, body)
        done = s.bulk_apply(self.manager, self.pid, {**body, "expected_revisions": {i["id"]: i["revision"] for i in plan["ok"]}})
        old = (datetime.now(timezone.utc) - timedelta(seconds=21)).isoformat()
        self.db.execute("UPDATE project_events SET occurred_at=? WHERE event_type='bulk_change'", (old,))
        with self.assertRaisesRegex(ValueError, "Undo window has passed"):
            s.bulk_undo(self.manager, self.pid, {"bulk_id": done["bulk_id"]})
        self.assertEqual(self.fresh()["status"], "assigned")

    def test_l2_a_waiting_task_is_blocked_in_a_bulk_move_to_in_progress(self):
        s = self.service
        pre = self.new("Pre")
        s.add_task_dependency(self.owner, pre["id"], self.task["id"])
        plan = s.bulk_preview(self.owner, self.pid, {"task_ids": [self.task["id"]], "action": "status", "value": "progress"})
        self.assertEqual(plan["blocked"][0]["reason"], "waits on Pre; move it on its own")

    def test_l2_a_board_move_out_of_changes_requested_is_not_undoable(self):
        s = self.service
        submission = s.submit_task(self.owner, self.task["id"], "done")
        s.request_changes(self.owner, submission["id"], "fix it")
        out = self.move(self.owner, "ready")
        self.assertNotIn("undo", out)
        event = s._latest_event_id(self.task["id"], self.owner["id"], "task_updated")
        # Even an event carrying the board's mark is refused when it left a status the board
        # never offers Undo from (the server's own check, not the client's).
        row = self.db.execute("SELECT after_json FROM task_events WHERE id=?", (event,)).fetchone()
        self.db.execute("UPDATE task_events SET after_json=? WHERE id=?",
                        (json.dumps({**json.loads(row["after_json"]), "move_kind": "board"}), event))
        with self.assertRaisesRegex(ValueError, "no move of yours to undo"):
            s.undo_move(self.owner, self.task["id"], {"event_id": event})

    def test_l2_a_dependency_driven_blocked_entry_is_not_refused(self):
        s = self.service
        s.set_on_hold(self.owner, self.new("Held")["id"], "wait", "2027-01-01", self.member["id"])
        s.set_wip_limit(self.owner, self.pid, "blocked", 1)
        pre = self.new("Pre")
        step = self.new("Step", parent_task_id=self.task["id"])
        s.add_task_dependency(self.owner, pre["id"], step["id"])
        s.set_parent(self.manager, step["id"], None)  # promoted into Blocked by its wait: not a move
        self.assertEqual(s._column_counts(self.owner, self.pid)["blocked"], 2)
        self.assertNotIn("wip_limit_override", self.kinds(step["id"]))

    def test_l2_locks_and_limits_go_with_their_task_and_project(self):
        cascades = {t: {r["table"]: r["on_delete"] for r in self.db.execute(f"PRAGMA foreign_key_list({t})").fetchall()}
                    for t in ("task_locks", "wip_limits")}
        self.assertEqual(cascades["task_locks"].get("tasks"), "CASCADE")
        self.assertEqual(cascades["wip_limits"].get("projects"), "CASCADE")


class TaskLockTests(BoardFixture):
    """X07XV4: a lock is a renewable lease; others cannot change the task while it lives."""

    def edit(self, actor, **fields):
        return self.service.update_task(actor, self.task["id"], {"expected_revision": self.fresh()["revision"], **fields})

    def expire(self):
        old = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self.db.execute("UPDATE task_locks SET expires_at=?", (old,))

    def test_a_lease_holds_off_everyone_else_until_it_is_released(self):
        lock = self.service.acquire_task_lock(self.manager, self.task["id"], "edit")
        self.assertEqual((lock["kind"], lock["seconds"]), ("edit", 60))
        with self.assertRaises(TaskLocked) as caught:
            self.edit(self.owner, title="Owner rename")
        self.assertIn("is being changed by Manager (an edit)", str(caught.exception))
        self.assertEqual(caught.exception.lock["holder_user_id"], self.manager["id"])
        self.assertEqual(self.fresh()["title"], "Draft plan")  # the refused write rolled back
        self.assertEqual(self.edit(self.manager, title="Manager rename")["title"], "Manager rename")
        # Everyone who can see the task sees who holds it.
        listed = next(t for t in self.service.list_tasks(self.member, self.project["id"]) if t["id"] == self.task["id"])
        self.assertEqual((listed["lock"]["holder_name"], listed["lock"]["kind"]), ("Manager", "edit"))
        self.assertEqual(self.service.task_detail(self.member, self.task["id"])["lock"]["holder_user_id"], self.manager["id"])
        self.assertEqual(self.service.release_task_lock(self.manager, self.task["id"], lock["token"]), {"released": True})
        self.assertEqual(self.edit(self.owner, title="Owner rename")["title"], "Owner rename")
        self.assertIsNone(self.service.task_detail(self.owner, self.task["id"])["lock"])

    def test_the_same_holder_keeps_one_token_and_a_second_person_is_refused(self):
        first = self.service.acquire_task_lock(self.manager, self.task["id"], "drag")
        again = self.service.acquire_task_lock(self.manager, self.task["id"], "edit")
        self.assertEqual(first["token"], again["token"])
        with self.assertRaisesRegex(TaskLocked, "Manager"):
            self.service.acquire_task_lock(self.owner, self.task["id"], "drag")

    def test_an_abandoned_lease_expires_and_is_not_taken_back_by_renewing(self):
        lock = self.service.acquire_task_lock(self.manager, self.task["id"], "drag")
        self.expire()
        self.assertEqual(self.edit(self.owner, title="After expiry")["title"], "After expiry")
        taken = self.service.acquire_task_lock(self.owner, self.task["id"], "edit")
        with self.assertRaises(TaskLocked):
            self.service.renew_task_lock(self.manager, self.task["id"], lock["token"])
        self.service.release_task_lock(self.owner, self.task["id"], taken["token"])
        with self.assertRaisesRegex(Conflict, "has ended"):
            self.service.renew_task_lock(self.manager, self.task["id"], lock["token"])

    def test_renewing_extends_the_lease(self):
        lock = self.service.acquire_task_lock(self.manager, self.task["id"], "edit")
        self.db.execute("UPDATE task_locks SET expires_at=?",
                        ((datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat(),))
        renewed = self.service.renew_task_lock(self.manager, self.task["id"], lock["token"])
        self.assertGreater(renewed["expires_at"], (datetime.now(timezone.utc) + timedelta(seconds=50)).isoformat())

    def test_only_people_who_may_change_the_task_take_a_lease(self):
        with self.assertRaises(Forbidden):
            self.service.acquire_task_lock(self.member, self.task["id"], "edit")
        with self.assertRaisesRegex(ValueError, "Unknown lock kind"):
            self.service.acquire_task_lock(self.manager, self.task["id"], "peek")

    def test_an_owner_force_unlocks_with_an_audit_event_and_a_notice_to_the_holder(self):
        self.service.acquire_task_lock(self.manager, self.task["id"], "edit")
        with self.assertRaises(Forbidden):
            self.service.force_unlock_task(self.manager, self.task["id"], "mine")
        self.service.force_unlock_task(self.second, self.task["id"], "Needed for the audit call")
        event = self.events()[-1]
        self.assertEqual((event["event_type"], event["reason"]), ("task_lock_forced", "Needed for the audit call"))
        self.assertEqual(json.loads(event["before_json"])["holder_user_id"], self.manager["id"])
        held = [n for n in self.service.list_notifications(self.manager) if n["kind"] == "task_lock_forced"]
        self.assertEqual(len(held), 1)
        self.assertIn("by Second Owner", held[0]["summary"])
        self.assertTrue([n for n in self.service.list_notifications(self.owner) if n["kind"] == "task_lock_forced"])
        self.assertIsNone(self.service.task_detail(self.owner, self.task["id"])["lock"])
        with self.assertRaisesRegex(ValueError, "Nobody holds a lock"):
            self.service.force_unlock_task(self.owner, self.task["id"])

    def test_every_write_path_revalidates_the_lock(self):
        pid = self.project["id"]
        other = self.service.create_task(self.owner, {"project_id": pid, "title": "Other"})
        self.service.acquire_task_lock(self.manager, self.task["id"], "edit")
        rev = self.fresh()["revision"]
        writes = {
            "board move": lambda: self.service.move_task(self.owner, self.task["id"], {"to_column": "ready", "expected_revision": rev}),
            "hold": lambda: self.service.set_on_hold(self.owner, self.task["id"], "late", "2027-01-01", self.member["id"]),
            "submit": lambda: self.service.submit_task(self.owner, self.task["id"], "done"),
            "dependency": lambda: self.service.add_task_dependency(self.owner, other["id"], self.task["id"]),
            "criticality": lambda: self.service.confirm_criticality(self.owner, self.task["id"], "high", "evidence"),
            "gantt": lambda: self.service.reschedule_task(self.owner, self.task["id"], {"due_date": "2027-01-05", "expected_revision": rev}),
        }
        for name, write in writes.items():
            with self.subTest(write=name):
                with self.assertRaises(TaskLocked):
                    write()
        self.assertEqual(self.fresh()["revision"], rev)
        self.assertEqual(self.fresh()["status"], "draft")
        # Audit rows of refused attempts are still written while the task is locked.
        with self.assertRaises(Forbidden):
            self.move(self.member, "ready")
        self.assertEqual(self.events()[-1]["event_type"], "board_move_blocked")

    def test_an_owner_decision_on_a_locked_task_waits_and_the_request_stays_pending(self):
        self.move(self.manager, "progress")
        request = self.move(self.manager, "closed", status="cancelled", reason="Not needed")["request"]
        self.service.acquire_task_lock(self.manager, self.task["id"], "edit")
        with self.assertRaises(TaskLocked):
            self.service.decide_owner_action_request(self.owner, request["id"], "approved", "ok")
        self.assertEqual(self.fresh()["status"], "in_progress")
        pending = [r["id"] for r in self.service.list_owner_action_requests(self.owner)]
        self.assertIn(request["id"], pending)


class GanttRescheduleTests(BoardFixture):
    """X07XV4: dragging or resizing a Gantt bar moves the task's dates."""

    def setUp(self):
        super().setUp()
        s, pid = self.service, self.project["id"]
        s.set_project_schedule(self.owner, pid, "2026-10-01", "2026-12-31", "Plan")
        self.first = s.create_task(self.owner, {"project_id": pid, "title": "Collect data",
                                                "start_date": "2026-10-01", "due_date": "2026-10-20"})
        self.then = s.create_task(self.owner, {"project_id": pid, "title": "Write report",
                                               "start_date": "2026-10-21", "due_date": "2026-11-10"})
        s.add_task_dependency(self.owner, self.first["id"], self.then["id"])
        self.side = s.create_task(self.owner, {"project_id": pid, "title": "Side task",
                                               "start_date": "2026-10-05", "due_date": "2026-10-08"})

    def drag(self, actor, task, **dates):
        current = self.fresh(task["id"])
        return self.service.reschedule_task(actor, task["id"], {"expected_revision": current["revision"], **dates})

    def test_an_ordinary_drag_applies_with_a_system_reason_and_undo(self):
        moved = self.drag(self.manager, self.side, start_date="2026-10-07", due_date="2026-10-10")
        self.assertEqual((moved["task"]["start_date"], moved["task"]["due_date"]), ("2026-10-07", "2026-10-10"))
        event = self.events(self.side["id"])[-1]
        self.assertEqual(event["reason"], "Gantt drag: start 2026-10-05 → 2026-10-07, due 2026-10-08 → 2026-10-10")
        self.assertEqual(moved["undo"], {"event_id": event["id"], "seconds": 15})
        undone = self.service.undo_move(self.manager, self.side["id"], {"event_id": event["id"]})
        self.assertEqual((undone["start_date"], undone["due_date"]), ("2026-10-05", "2026-10-08"))
        self.assertTrue(self.events(self.side["id"])[-1]["reason"].startswith("Undo of start 2026-10-05 → 2026-10-07"))

    def test_a_resize_changes_one_end_only(self):
        moved = self.drag(self.owner, self.side, start_date="2026-10-05", due_date="2026-10-12")
        self.assertEqual(self.events(self.side["id"])[-1]["reason"], "Gantt drag: due 2026-10-08 → 2026-10-12")
        self.assertIn("undo", moved)

    def test_breaking_a_dependency_asks_first_then_tells_the_other_owners(self):
        with self.assertRaises(NeedsConfirmation) as caught:
            self.drag(self.manager, self.first, start_date="2026-10-01", due_date="2026-10-25")
        self.assertEqual(caught.exception.confirm, "impact")
        self.assertTrue(any("Write report starts on 2026-10-21, before this is due (2026-10-25)" in i
                            for i in caught.exception.impact))
        self.assertEqual(self.fresh(self.first["id"])["due_date"], "2026-10-20")
        moved = self.drag(self.manager, self.first, start_date="2026-10-01", due_date="2026-10-25", confirmed=True)
        self.assertNotIn("undo", moved)
        self.assertEqual(moved["impact"], caught.exception.impact)
        event = self.events(self.first["id"])[-1]
        self.assertEqual(event["event_type"], "schedule_impact_confirmed")
        for owner in (self.owner, self.second):
            self.assertTrue([n for n in self.service.list_notifications(owner) if n["kind"] == "schedule_impact_confirmed"])
        # The successor is left where it was.
        self.assertEqual(self.fresh(self.then["id"])["start_date"], "2026-10-21")

    def test_starting_before_a_predecessor_is_due_and_passing_the_target_count_as_impact(self):
        with self.assertRaises(NeedsConfirmation) as caught:
            self.drag(self.owner, self.then, start_date="2026-10-15", due_date="2027-01-05")
        text = " ".join(caught.exception.impact)
        self.assertIn("before Collect data is due (2026-10-20)", text)
        self.assertIn("after the project target (2026-12-31)", text)
        self.assertIn("critical path", text)

    def test_invalid_dates_are_refused_and_only_people_who_cannot_drag_are_audited(self):
        with self.assertRaisesRegex(ValueError, "would be after the due date"):
            self.drag(self.manager, self.side, start_date="2026-10-20", due_date="2026-10-10")
        with self.assertRaisesRegex(ValueError, "real calendar dates"):
            self.drag(self.manager, self.side, start_date="2026-02-30", due_date="2026-10-10")
        with self.assertRaises(Forbidden):
            self.drag(self.member, self.side, start_date="2026-10-06", due_date="2026-10-09")
        # Review 12a L4: plain validation goes back to the actor; the refused permission is audited.
        kinds = [e["event_type"] for e in self.events(self.side["id"])]
        self.assertEqual(kinds.count("gantt_move_blocked"), 1)
        self.assertEqual(self.fresh(self.side["id"])["due_date"], "2026-10-08")
        with self.assertRaises(Conflict):
            self.service.reschedule_task(self.manager, self.side["id"], {"expected_revision": 99, "due_date": "2026-10-09"})
        self.assertEqual([e["event_type"] for e in self.events(self.side["id"])].count("gantt_move_blocked"), 1)


class WipLimitTests(BoardFixture):
    """XV92JJ: optional work-in-progress limits per board column, set by an owner."""

    def test_only_an_owner_sets_a_limit_and_every_change_is_in_history(self):
        pid = self.project["id"]
        with self.assertRaises(Forbidden):
            self.service.set_wip_limit(self.manager, pid, "ready", 3)
        self.assertEqual(self.service.set_wip_limit(self.second, pid, "ready", 3, "Keep Ready short"), {"ready": 3})
        self.assertEqual(self.service.set_wip_limit(self.owner, pid, "ready", "5"), {"ready": 5})
        self.assertEqual(self.service.set_wip_limit(self.owner, pid, "ready", None), {})
        changes = [json.loads(e["detail_json"]) for e in self.service.project_events(self.owner, pid)
                   if e["event_type"] == "wip_limit_changed"]
        self.assertEqual([(c["before"], c["after"]) for c in changes], [(None, 3), (3, 5), (5, None)])
        for column, value in (("accepted", 3), ("ready", 0.5), ("ready", 1000), ("ready", True), ("ready", "x")):
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                self.service.set_wip_limit(self.owner, pid, column, value)
        self.service.set_wip_limit(self.owner, pid, "progress", 2)
        listed = next(p for p in self.service.list_projects(self.member) if p["id"] == pid)
        self.assertEqual(listed["wip_limits"], {"progress": 2})

    def test_a_move_over_the_limit_is_refused_and_only_an_owner_goes_over(self):
        pid = self.project["id"]
        self.service.set_wip_limit(self.owner, pid, "ready", 1)
        self.move(self.manager, "ready")
        other = self.service.create_task(self.owner, {"project_id": pid, "title": "Second"})
        with self.assertRaisesRegex(ValueError, "Ready is at its work-in-progress limit: 1 of 1"):
            self.move(self.manager, "ready", task_id=other["id"])
        self.assertEqual(self.events(other["id"])[-1]["event_type"], "board_move_blocked")
        with self.assertRaises(NeedsConfirmation) as caught:
            self.move(self.owner, "ready", task_id=other["id"])
        self.assertEqual(caught.exception.confirm, "wip")
        moved = self.move(self.owner, "ready", task_id=other["id"], override_wip=True)
        self.assertEqual(moved["task"]["status"], "assigned")
        override = self.events(other["id"])[-1]
        self.assertEqual((override["event_type"], json.loads(override["before_json"])["limit"]), ("wip_limit_override", 1))
        self.assertTrue([n for n in self.service.list_notifications(self.second) if n["kind"] == "wip_limit_override"])
        # Moving out of a full column, and within a column, is never limited.
        self.assertEqual(self.move(self.manager, "draft", task_id=other["id"])["task"]["status"], "draft")


class BulkChangeTests(BoardFixture):
    """XV92JJ: bulk status, assignee and due-date changes: previewed, all or nothing, undoable."""

    def setUp(self):
        super().setUp()
        pid = self.project["id"]
        make = lambda title, **k: self.service.create_task(self.owner, {"project_id": pid, "title": title, **k})
        self.a = make("Alpha", due_date="2026-10-10")
        self.b = make("Bravo", start_date="2026-10-01", due_date="2026-10-12")
        self.c = make("Charlie")
        self.ids = [self.task["id"], self.a["id"], self.b["id"], self.c["id"]]

    def preview(self, actor, action, value, ids=None):
        return self.service.bulk_preview(actor, self.project["id"], {"task_ids": ids or self.ids, "action": action, "value": value})

    def apply(self, actor, action, value, ids=None, **extra):
        plan = self.preview(actor, action, value, ids)
        revisions = {item["id"]: item["revision"] for item in plan["ok"]}
        return self.service.bulk_apply(actor, self.project["id"], {"task_ids": ids or self.ids, "action": action,
                                                                   "value": value, "expected_revisions": revisions, **extra})

    def test_preview_counts_and_names_the_blocked_tasks(self):
        self.service.submit_task(self.owner, self.c["id"], "done")
        self.move(self.owner, "ready", task_id=self.a["id"])
        plan = self.preview(self.manager, "status", "ready")
        self.assertEqual(plan["counts"], {"ok": 2, "blocked": 2})
        reasons = {b["title"]: b["reason"] for b in plan["blocked"]}
        self.assertEqual(reasons, {"Alpha": "is already Ready", "Charlie": "is submitted; change it on its own"})
        with self.assertRaisesRegex(ValueError, "Remove the blocked tasks first"):
            self.apply(self.manager, "status", "ready")
        self.assertEqual(self.fresh()["status"], "draft")  # nothing changed

    def test_apply_is_one_change_with_one_notice_and_per_task_history(self):
        out = self.apply(self.manager, "status", "progress")
        self.assertEqual(len(out["tasks"]), 4)
        for task_id in self.ids:
            self.assertEqual(self.fresh(task_id)["status"], "in_progress")
            self.assertEqual(self.events(task_id)[-1]["reason"], "Bulk change: status to In progress")
        parent = self.service.project_events(self.owner, self.project["id"])[-1]
        self.assertEqual(parent["event_type"], "bulk_change")
        self.assertEqual(len(json.loads(parent["detail_json"])["tasks"]), 4)
        notices = self.service.list_notifications(self.owner)
        self.assertEqual([n["kind"] for n in notices if n["kind"] in ("bulk_change", "task_updated")], ["bulk_change"])
        self.assertIn("bulk change: 4 tasks · status to In progress · by Manager", notices[0]["summary"])

    def test_a_task_in_use_by_someone_else_stops_the_whole_change(self):
        self.service.acquire_task_lock(self.owner, self.b["id"], "edit")
        plan = self.preview(self.manager, "status", "ready")
        self.assertEqual(plan["blocked"], [{"id": self.b["id"], "title": "Bravo", "revision": self.b["revision"],
                                            "reason": "is being changed by Owner"}])
        revisions = {i: self.fresh(i)["revision"] for i in self.ids}
        with self.assertRaisesRegex(ValueError, "Nothing was changed.*“Bravo” is being changed by Owner"):
            self.service.bulk_apply(self.manager, self.project["id"], {"task_ids": self.ids, "action": "status",
                                    "value": "ready", "expected_revisions": revisions})
        # The bulk leases themselves are all or nothing: one held task and none are taken.
        with self.assertRaisesRegex(TaskLocked, "1 of the tasks is being changed by someone else \\(“Bravo” by Owner\\)"):
            self.service._take_bulk_leases(self.manager, self.ids, "tok")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM task_locks WHERE kind='bulk'").fetchone()[0], 0)
        self.assertEqual([self.fresh(i)["status"] for i in self.ids], ["draft"] * 4)

    def test_a_failure_part_way_rolls_every_task_back(self):
        real, calls = self.service._apply_task_update, []
        def failing(*args, **kwargs):
            calls.append(1)
            if len(calls) == 3:
                raise Conflict("simulated")
            return real(*args, **kwargs)
        self.service._apply_task_update = failing
        with self.assertRaisesRegex(Conflict, "simulated"):
            self.apply(self.owner, "status", "ready")
        self.service._apply_task_update = real
        self.assertEqual([self.fresh(i)["status"] for i in self.ids], ["draft"] * 4)
        self.assertNotIn("bulk_change", [e["event_type"] for e in self.service.project_events(self.owner, self.project["id"])])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM task_locks").fetchone()[0], 0)

    def test_a_stale_preview_changes_nothing(self):
        plan = self.preview(self.manager, "status", "ready")
        revisions = {item["id"]: item["revision"] for item in plan["ok"]}
        self.service.update_task(self.owner, self.a["id"], {"title": "Alpha 2", "expected_revision": self.a["revision"]})
        with self.assertRaisesRegex(Conflict, "changed since the preview"):
            self.service.bulk_apply(self.manager, self.project["id"], {"task_ids": self.ids, "action": "status",
                                    "value": "ready", "expected_revisions": revisions})
        self.assertEqual(self.fresh()["status"], "draft")

    def test_assignee_and_due_date_offsets(self):
        out = self.apply(self.manager, "assignee", self.manager["id"], ids=[self.a["id"], self.b["id"]])
        self.assertEqual({self.fresh(t["id"])["owner_user_id"] for t in out["tasks"]}, {self.manager["id"]})
        self.assertEqual(self.preview(self.manager, "assignee", self.manager["id"], [self.a["id"]])["blocked"][0]["reason"],
                         "is already assigned to Manager")
        with self.assertRaises(ValueError):
            self.preview(self.manager, "assignee", self.second["id"] + "x", [self.a["id"]])
        self.service.set_project_schedule(self.owner, self.project["id"], "2026-10-01", "2026-10-11", "Plan")
        plan = self.preview(self.manager, "due_shift", 3)
        self.assertEqual({b["title"]: b["reason"] for b in plan["blocked"]},
                         {"Draft plan": "has no due date", "Charlie": "has no due date"})
        self.assertEqual([i["title"] for i in plan["impact"]], ["Alpha", "Bravo"])  # both pass the target
        with self.assertRaises(NeedsConfirmation) as caught:  # review 12c L5: consequences are confirmed
            self.apply(self.manager, "due_shift", 3, ids=[self.a["id"], self.b["id"]])
        self.assertEqual(caught.exception.confirm, "impact")
        with self.assertRaises(NeedsConfirmation):
            self.apply(self.manager, "due_shift", 3, ids=[self.a["id"], self.b["id"]], confirmed="yes")
        self.apply(self.manager, "due_shift", 3, ids=[self.a["id"], self.b["id"]], confirmed=True)
        self.assertEqual((self.fresh(self.b["id"])["start_date"], self.fresh(self.b["id"])["due_date"]),
                         ("2026-10-04", "2026-10-15"))
        self.assertEqual(self.fresh(self.a["id"])["due_date"], "2026-10-13")
        with self.assertRaisesRegex(ValueError, "whole number of days"):
            self.preview(self.manager, "due_shift", 0)

    def test_bulk_undo_restores_every_task_once_and_only_if_none_changed(self):
        out = self.apply(self.manager, "status", "ready")
        with self.assertRaisesRegex(ValueError, "no bulk change of yours"):
            self.service.bulk_undo(self.owner, self.project["id"], {"bulk_id": out["bulk_id"]})
        self.service.bulk_undo(self.manager, self.project["id"], {"bulk_id": out["bulk_id"]})
        self.assertEqual([self.fresh(i)["status"] for i in self.ids], ["draft"] * 4)
        self.assertTrue(self.events(self.a["id"])[-1]["reason"].startswith("Undo of bulk change (status to Ready)"))
        with self.assertRaisesRegex(ValueError, "already been undone"):
            self.service.bulk_undo(self.manager, self.project["id"], {"bulk_id": out["bulk_id"]})
        again = self.apply(self.manager, "status", "ready")
        self.service.update_task(self.owner, self.c["id"], {"title": "Charlie 2", "expected_revision": self.fresh(self.c["id"])["revision"]})
        with self.assertRaisesRegex(Conflict, "“Charlie” changed after the bulk change"):
            self.service.bulk_undo(self.manager, self.project["id"], {"bulk_id": again["bulk_id"]})
        self.assertEqual(self.fresh(self.a["id"])["status"], "assigned")  # nothing was undone

    def test_members_cannot_change_in_bulk_and_the_limit_applies(self):
        with self.assertRaises(Forbidden):
            self.preview(self.member, "status", "ready")
        self.service.set_wip_limit(self.owner, self.project["id"], "ready", 2)
        plan = self.preview(self.manager, "status", "ready")
        self.assertEqual((plan["wip"]["count"], plan["wip"]["limit"], plan["wip"]["incoming"], plan["wip"]["can_override"]),
                         (0, 2, 4, False))
        with self.assertRaisesRegex(ValueError, "work-in-progress limit"):
            self.apply(self.manager, "status", "ready")
        with self.assertRaises(NeedsConfirmation):
            self.apply(self.owner, "status", "ready")
        self.apply(self.owner, "status", "ready", override_wip=True)
        kinds = [e["event_type"] for e in self.service.project_events(self.owner, self.project["id"])]
        self.assertEqual(kinds[-2:], ["bulk_change", "wip_limit_override"])


if __name__ == "__main__":
    unittest.main()
