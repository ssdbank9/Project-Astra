"""9MK29X: characterization of AstraService.update_task.

These pin the observable contract of update_task (exception type, exact message,
check order, event types and request payloads) so that restructuring its body
into helpers cannot change behaviour unnoticed. Every refusal is also checked to
leave the task row, its revision and its event log untouched.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from astra import service as service_module
from astra.db import connect, transaction as database_transaction
from astra.service import AstraService, Conflict, Forbidden


class UpdateTaskContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "contract.sqlite3"
        self.db = connect(self.db_path)
        self.service = AstraService(self.db)
        self.owner = self.service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")
        self.project = self.service.create_project(self.owner, "Contract")
        self.manager = self.service.create_user(self.owner, "manager@example.org", "Manager", "manager password safe")
        self.service.grant_project_access(self.owner, self.project["id"], self.manager["id"], "manager")
        self.viewer = self.service.create_user(self.owner, "viewer@example.org", "Viewer", "viewer password safe")
        self.service.grant_project_access(self.owner, self.project["id"], self.viewer["id"], "viewer")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    # helpers -----------------------------------------------------------------

    def _task(self, title="Task", **fields):
        return self.service.create_task(self.owner, {"project_id": self.project["id"], "title": title, **fields})

    def _set_status(self, task, status):
        """Put a task in a status directly, bypassing lifecycle actions (fixture only)."""
        with database_transaction(self.db):
            self.db.execute("UPDATE tasks SET status=? WHERE id=?", (status, task["id"]))
        return self.service.get_task(self.owner, task["id"])

    def _event_types(self, task_id):
        return [event["event_type"] for event in self.service.task_events(self.owner, task_id)]

    def _snapshot(self, task_id):
        return self.service.get_task(self.owner, task_id), self._event_types(task_id)

    def _assert_refused(self, actor, task, payload, exc_type, message):
        before = self._snapshot(task["id"])
        with self.assertRaises(exc_type) as caught:
            self.service.update_task(actor, task["id"], payload)
        self.assertIs(type(caught.exception), exc_type)
        self.assertEqual(str(caught.exception), message)
        self.assertEqual(self._snapshot(task["id"]), before)

    def _pending_requests(self, task_id):
        return self.db.execute(
            "SELECT action,payload_json,reason FROM owner_action_requests WHERE task_id=? AND status='pending'",
            (task_id,),
        ).fetchall()

    # authorization and revision ----------------------------------------------

    def test_viewer_is_forbidden_before_revision_is_read(self):
        task = self._task()
        self._assert_refused(self.viewer, task, {"title": "x"}, Forbidden, "Task-management access denied.")

    def test_expected_revision_must_be_an_integer(self):
        task = self._task()
        message = "An integer expected_revision is required to update a task."
        for bad in (None, "1", 1.0, True):
            with self.subTest(expected_revision=bad):
                payload = {"title": "x"} if bad is None else {"title": "x", "expected_revision": bad}
                self._assert_refused(self.owner, task, payload, ValueError, message)

    def test_stale_expected_revision_is_a_conflict_with_both_revisions(self):
        task = self._task()
        self._assert_refused(
            self.owner, task, {"title": "x", "expected_revision": task["revision"] + 5}, Conflict,
            f"Task revision conflict: expected {task['revision'] + 5}, current revision is {task['revision']}.",
        )

    def test_revision_is_checked_before_field_validation(self):
        task = self._task()
        self._assert_refused(
            self.owner, task, {"status": "bogus", "expected_revision": task["revision"] + 1}, Conflict,
            f"Task revision conflict: expected {task['revision'] + 1}, current revision is {task['revision']}.",
        )

    # field validation messages -------------------------------------------------

    def test_field_validation_messages(self):
        task = self._task(start_date="2027-01-10")
        rev = task["revision"]
        cases = [
            ({"status": "bogus"}, "Invalid task status or criticality."),
            ({"criticality": "extreme"}, "Invalid task status or criticality."),
            ({"status": "submitted", "reason": "r"}, "Use the dedicated submitted action for this transition."),
            ({"status": "on_hold", "reason": "r"}, "Use the dedicated on hold action for this transition."),
            ({"status": "completed", "reason": "r"}, "Use the dedicated completed action for this transition."),
            ({"status": "reopened", "reason": "r"}, "Use the dedicated reopened action for this transition."),
            ({"criticality": "high"}, "Use the confirm criticality action to change criticality."),
            ({"due_date": "2027-02-01"}, "A reason is required for schedule or status changes."),
            ({"status": "in_progress"}, "A reason is required for schedule or status changes."),
            ({"due_date": "2027-01-01", "reason": "r"}, "Due date cannot be earlier than start date."),
            ({"title": "   "}, "Task title is required."),
        ]
        for change, message in cases:
            with self.subTest(change=change):
                self._assert_refused(self.owner, task, {**change, "expected_revision": rev}, ValueError, message)

    def test_status_check_precedes_criticality_and_reason_checks(self):
        task = self._task()
        self._assert_refused(
            self.owner, task, {"status": "on_hold", "criticality": "high", "expected_revision": task["revision"]},
            ValueError, "Use the dedicated on hold action for this transition.",
        )

    def test_unknown_assignee_is_refused(self):
        task = self._task()
        before = self._snapshot(task["id"])
        with self.assertRaises(ValueError):
            self.service.update_task(self.owner, task["id"], {
                "owner_user_id": "no-such-user", "expected_revision": task["revision"],
            })
        self.assertEqual(self._snapshot(task["id"]), before)

    # closed and locked sources -------------------------------------------------

    def test_closed_task_is_immutable_even_for_a_reason_only_save(self):
        for status in ("completed", "cancelled", "abandoned"):
            with self.subTest(status=status):
                task = self._set_status(self._task(f"Closed {status}"), status)
                message = (f"A {status} task is immutable; reopen the task first with the dedicated "
                           "reopen task action.")
                for change in ({"reason": "only a reason"}, {"title": "Edited"}, {"criticality": "high"}):
                    self._assert_refused(self.owner, task, {**change, "expected_revision": task["revision"]},
                                         ValueError, message)

    def test_closed_task_moved_to_a_non_work_status_gets_the_reopen_refusal(self):
        for actor_name in ("owner", "manager"):
            actor = getattr(self, actor_name)
            task = self._set_status(self._task(f"Done {actor_name}"), "completed")
            with self.subTest(actor=actor_name):
                self._assert_refused(
                    actor, task, {"status": "cancelled", "reason": "r", "expected_revision": task["revision"]},
                    ValueError,
                    "A completed task is not edited back into work; use the dedicated reopen task action "
                    "(reason and revised due date) so the reopening is recorded.",
                )
                self.assertEqual(self._pending_requests(task["id"]), [])

    def test_owner_moving_a_closed_task_back_into_work_gets_the_reopen_refusal(self):
        task = self._set_status(self._task(), "cancelled")
        self._assert_refused(
            self.owner, task, {"status": "in_progress", "reason": "r", "expected_revision": task["revision"]},
            ValueError,
            "A cancelled task is not edited back into work; use the dedicated reopen task action "
            "(reason and revised due date) so the reopening is recorded.",
        )

    def test_submitted_task_leaves_review_only_through_the_decision(self):
        for actor_name in ("owner", "manager"):
            actor = getattr(self, actor_name)
            task = self._set_status(self._task(f"Submitted {actor_name}"), "submitted")
            with self.subTest(actor=actor_name):
                self._assert_refused(
                    actor, task, {"status": "in_progress", "reason": "r", "expected_revision": task["revision"]},
                    ValueError,
                    "A submitted task leaves review through the dedicated accept or request changes action.",
                )
                self.assertEqual(self._pending_requests(task["id"]), [])

    # request routing -------------------------------------------------------------

    def test_manager_leaving_a_locked_source_files_a_request_with_from_status(self):
        task = self._set_status(self._task(), "cancelled")
        result = self.service.update_task(self.manager, task["id"], {
            "status": "in_progress", "reason": "Back to work", "expected_revision": task["revision"],
        })
        rows = self._pending_requests(task["id"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(result["request"]["action"], "update_task_status")
        self.assertEqual(rows[0]["action"], "update_task_status")
        self.assertEqual(rows[0]["reason"], "Back to work")
        self.assertEqual(json.loads(rows[0]["payload_json"]), {
            "status": "in_progress", "from_status": "cancelled", "reason": "Back to work",
            "expected_revision": task["revision"],
        })
        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual((current["status"], current["revision"]), ("cancelled", task["revision"]))
        self.assertNotIn("task_updated", self._event_types(task["id"]))
        self.assertIn("protected_action_requested", self._event_types(task["id"]))

    def test_manager_moving_into_a_protected_status_files_a_request_without_from_status(self):
        task = self._task()
        self.service.update_task(self.manager, task["id"], {
            "status": "cancelled", "reason": "No longer needed", "expected_revision": task["revision"],
        })
        rows = self._pending_requests(task["id"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(json.loads(rows[0]["payload_json"]), {
            "status": "cancelled", "reason": "No longer needed", "expected_revision": task["revision"],
        })
        self.assertEqual(self.service.get_task(self.owner, task["id"])["status"], "draft")
        self.assertNotIn("task_updated", self._event_types(task["id"]))

    def test_manager_request_for_a_reasonless_lifecycle_change_is_refused_first(self):
        task = self._task()
        self._assert_refused(
            self.manager, task, {"status": "cancelled", "expected_revision": task["revision"]},
            ValueError, "A reason is required for schedule or status changes.",
        )
        self.assertEqual(self._pending_requests(task["id"]), [])

    def test_owner_writes_a_protected_status_directly(self):
        task = self._task()
        after = self.service.update_task(self.owner, task["id"], {
            "status": "cancelled", "reason": "Owner cancels", "expected_revision": task["revision"],
        })
        self.assertEqual((after["status"], after["revision"]), ("cancelled", task["revision"] + 1))
        self.assertEqual(self._event_types(task["id"]).count("task_updated"), 1)
        self.assertEqual(self._pending_requests(task["id"]), [])

    # write and audit -------------------------------------------------------------

    def test_successful_update_writes_fields_bumps_revision_and_records_one_event(self):
        task = self._task(description="old")
        after = self.service.update_task(self.owner, task["id"], {
            "title": "  New title  ", "description": "  new  ", "progress": 40,
            "due_date": "2027-03-01", "reason": "Schedule", "owner_user_id": self.manager["id"],
            "expected_revision": task["revision"],
        })
        self.assertEqual(
            (after["title"], after["description"], after["progress"], after["due_date"], after["owner_user_id"],
             after["revision"]),
            ("New title", "new", 40, "2027-03-01", self.manager["id"], task["revision"] + 1),
        )
        events = [event for event in self.service.task_events(self.owner, task["id"])
                  if event["event_type"] == "task_updated"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["reason"], "Schedule")

    def test_owner_update_resolves_an_equivalent_pending_manager_request(self):
        task = self._task()
        self.service.update_task(self.manager, task["id"], {
            "status": "cancelled", "reason": "Manager asks", "expected_revision": task["revision"],
        })
        self.assertEqual(len(self._pending_requests(task["id"])), 1)
        self.service.update_task(self.owner, task["id"], {
            "status": "cancelled", "reason": "Owner agrees", "expected_revision": task["revision"],
        })
        self.assertEqual(self._pending_requests(task["id"]), [])

    def test_revision_predicate_conflict_message_when_the_row_moves_under_the_write(self):
        task = self._task()
        other = connect(self.db_path)
        self.addCleanup(other.close)
        fired = []

        @contextmanager
        def edit_first(connection):
            if connection is self.db and not fired:
                fired.append(True)
                AstraService(other).update_task(self.owner, task["id"], {
                    "title": "Other writer", "expected_revision": task["revision"],
                })
            with database_transaction(connection):
                yield

        with patch.object(service_module, "transaction", edit_first):
            with self.assertRaises(Conflict) as caught:
                self.service.update_task(self.owner, task["id"], {
                    "title": "Late writer", "expected_revision": task["revision"],
                })
        self.assertEqual(str(caught.exception),
                         "Task revision conflict: the task changed before this update could be saved.")
        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual((current["title"], current["revision"]), ("Other writer", task["revision"] + 1))
        self.assertEqual(self._event_types(task["id"]).count("task_updated"), 1)

    def test_approval_refused_when_its_request_is_decided_under_the_write(self):
        """The pending-request re-check runs inside the write transaction: a request
        rejected after the approval's pre-checks but before its write is a Conflict and
        leaves the task unchanged."""
        task = self._task()
        request = self.service.update_task(self.manager, task["id"], {
            "status": "cancelled", "reason": "Manager asks", "expected_revision": task["revision"],
        })["request"]
        other = connect(self.db_path)
        self.addCleanup(other.close)
        fired = []
        original_update = AstraService.update_task

        def update_spy(service, *args, **kwargs):
            if kwargs.get("owner_decision") is not None:
                fired.append("approval-write")
            return original_update(service, *args, **kwargs)

        @contextmanager
        def reject_first(connection):
            if connection is self.db and fired == ["approval-write"]:
                fired.append("rejected")
                with database_transaction(other):
                    other.execute(
                        "UPDATE owner_action_requests SET status='rejected', decision_reason='no' WHERE id=?",
                        (request["id"],),
                    )
            with database_transaction(connection):
                yield

        with patch.object(AstraService, "update_task", update_spy), \
                patch.object(service_module, "transaction", reject_first):
            with self.assertRaises(Conflict) as caught:
                self.service.decide_owner_action_request(self.owner, request["id"], "approved", "ok")
        self.assertEqual(fired, ["approval-write", "rejected"])
        self.assertEqual(str(caught.exception), "Owner-action request conflict: the pending request changed.")
        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual((current["status"], current["revision"]), ("draft", task["revision"]))
        self.assertNotIn("task_updated", self._event_types(task["id"]))


if __name__ == "__main__":
    unittest.main()
