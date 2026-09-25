"""Lock #12: governed board drag and drop (JN1QYG), task locks and Gantt date drags,
bulk changes and WIP limits. Service-level behaviour; the HTTP and UI sides are in
test_web.py."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from astra.db import connect
from astra.service import AstraService, Conflict, Forbidden, NeedsConfirmation, TaskLocked


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

    def test_invalid_dates_and_people_who_cannot_drag_are_refused_and_audited(self):
        with self.assertRaisesRegex(ValueError, "would be after the due date"):
            self.drag(self.manager, self.side, start_date="2026-10-20", due_date="2026-10-10")
        with self.assertRaisesRegex(ValueError, "real calendar dates"):
            self.drag(self.manager, self.side, start_date="2026-02-30", due_date="2026-10-10")
        with self.assertRaises(Forbidden):
            self.drag(self.member, self.side, start_date="2026-10-06", due_date="2026-10-09")
        kinds = [e["event_type"] for e in self.events(self.side["id"])]
        self.assertEqual(kinds.count("gantt_move_blocked"), 3)
        self.assertEqual(self.fresh(self.side["id"])["due_date"], "2026-10-08")
        with self.assertRaises(Conflict):
            self.service.reschedule_task(self.manager, self.side["id"], {"expected_revision": 99, "due_date": "2026-10-09"})
        self.assertEqual([e["event_type"] for e in self.events(self.side["id"])].count("gantt_move_blocked"), 3)


if __name__ == "__main__":
    unittest.main()
