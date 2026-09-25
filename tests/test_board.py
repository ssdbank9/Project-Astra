"""Lock #12: governed board drag and drop (JN1QYG), task locks and Gantt date drags,
bulk changes and WIP limits. Service-level behaviour; the HTTP and UI sides are in
test_web.py."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from astra.db import connect
from astra.service import AstraService, Conflict, Forbidden, NeedsConfirmation


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
        undone = self.service.undo_board_move(self.manager, self.task["id"], {"event_id": result["undo"]["event_id"]})
        self.assertEqual(undone["status"], "draft")
        kinds = [(e["event_type"], e["reason"]) for e in self.events()]
        self.assertEqual(kinds[-2][1], "Board move: Draft → In progress")
        self.assertTrue(kinds[-1][1].startswith("Undo of Draft → In progress (event "))
        self.assertEqual(len(kinds), 3)  # history is appended to, never rewritten
        # Undo twice, or someone else's undo, is refused.
        with self.assertRaises(ValueError):
            self.service.undo_board_move(self.manager, self.task["id"], {"event_id": result["undo"]["event_id"]})
        second = self.move(self.manager, "ready")
        with self.assertRaisesRegex(ValueError, "no board move of yours"):
            self.service.undo_board_move(self.owner, self.task["id"], {"event_id": second["undo"]["event_id"]})
        # A later change in between: not reversed blindly.
        self.service.update_task(self.owner, self.task["id"], {"expected_revision": self.fresh()["revision"],
                                                               "title": "Draft plan v2"})
        with self.assertRaisesRegex(Conflict, "changed after your move"):
            self.service.undo_board_move(self.manager, self.task["id"], {"event_id": second["undo"]["event_id"]})

    def test_undo_window_is_fifteen_seconds_plus_grace(self):
        result = self.move(self.manager, "ready")
        old = (datetime.now(timezone.utc) - timedelta(seconds=21)).isoformat()
        self.db.execute("UPDATE task_events SET occurred_at=? WHERE id=?", (old, result["undo"]["event_id"]))
        with self.assertRaisesRegex(ValueError, "Undo window has passed"):
            self.service.undo_board_move(self.manager, self.task["id"], {"event_id": result["undo"]["event_id"]})

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


if __name__ == "__main__":
    unittest.main()
