from __future__ import annotations

import threading
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from astra import service as service_module
from astra.db import connect, transaction as database_transaction
from astra.service import AstraService


class AstraStateIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "integrity.sqlite3"
        self.db = connect(self.db_path)
        self.service = AstraService(self.db)
        self.owner = self.service.create_initial_owner(
            "owner@example.org", "Owner", "correct horse battery"
        )

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_stale_task_update_is_rejected_without_state_or_event_change(self):
        project = self.service.create_project(self.owner, "Concurrency")
        task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Original"}
        )
        first = self.service.update_task(
            self.owner,
            task["id"],
            {"title": "First writer", "expected_revision": task["revision"]},
        )
        events_before = len(self.service.task_events(self.owner, task["id"]))

        with self.assertRaisesRegex(ValueError, "revision|conflict|stale"):
            self.service.update_task(
                self.owner,
                task["id"],
                {"title": "Stale writer", "expected_revision": task["revision"]},
            )

        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual(current["title"], "First writer")
        self.assertEqual(current["revision"], first["revision"])
        self.assertEqual(len(self.service.task_events(self.owner, task["id"])), events_before)

    def test_terminal_tasks_reject_ordinary_edits_until_reopened(self):
        project = self.service.create_project(self.owner, "Terminal states")
        completed = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Completed"}
        )
        submission = self.service.submit_task(self.owner, completed["id"], "done")
        self.service.accept_submission(self.owner, submission["id"], "accepted")

        terminal_tasks = [self.service.get_task(self.owner, completed["id"])]
        for status in ("cancelled", "abandoned"):
            task = self.service.create_task(
                self.owner, {"project_id": project["id"], "title": status.title()}
            )
            terminal_tasks.append(
                self.service.update_task(
                    self.owner,
                    task["id"],
                    {
                        "status": status,
                        "reason": "terminal test",
                        "expected_revision": task["revision"],
                    },
                )
            )

        for task in terminal_tasks:
            events_before = len(self.service.task_events(self.owner, task["id"]))
            ordinary_changes = (
                {"title": f"Edited {task['status']}"},
                {"due_date": "2027-07-01"},
                {"progress": 42},
            )
            for change in ordinary_changes:
                with self.subTest(status=task["status"], field=next(iter(change))):
                    with self.assertRaisesRegex(ValueError, "reopen"):
                        self.service.update_task(
                            self.owner,
                            task["id"],
                            {**change, "expected_revision": task["revision"]},
                        )
                    current = self.service.get_task(self.owner, task["id"])
                    self.assertEqual(current["revision"], task["revision"])
                    self.assertEqual(
                        len(self.service.task_events(self.owner, task["id"])), events_before
                    )
            with self.subTest(status=task["status"], action="hold"):
                with self.assertRaisesRegex(ValueError, "reopened"):
                    self.service.set_on_hold(
                        self.owner, task["id"], "late hold", "2027-06-01", self.owner["id"]
                    )

    def test_concurrent_acceptance_has_one_winner_and_one_event(self):
        project = self.service.create_project(self.owner, "Acceptance")
        task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Deliverable"}
        )
        submission = self.service.submit_task(self.owner, task["id"], "ready")
        barrier = threading.Barrier(2)
        outcomes = []
        lock = threading.Lock()

        @contextmanager
        def synchronized_transaction(connection):
            barrier.wait(timeout=5)
            with database_transaction(connection):
                yield

        def accept(label):
            connection = connect(self.db_path)
            try:
                service = AstraService(connection)
                actor = service.get_user(self.owner["id"])
                try:
                    service.accept_submission(actor, submission["id"], label)
                except Exception as exc:  # the loser must be a domain conflict
                    result = ("error", type(exc).__name__, str(exc))
                else:
                    result = ("accepted", label)
                with lock:
                    outcomes.append(result)
            finally:
                connection.close()

        with patch.object(service_module, "transaction", synchronized_transaction):
            threads = [threading.Thread(target=accept, args=(label,)) for label in ("one", "two")]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual([result[0] for result in outcomes].count("accepted"), 1, outcomes)
        self.assertEqual([result[0] for result in outcomes].count("error"), 1, outcomes)
        accepted_events = [
            event for event in self.service.task_events(self.owner, task["id"])
            if event["event_type"] == "submission_accepted"
        ]
        self.assertEqual(len(accepted_events), 1)

    def test_equivalent_protected_retries_reuse_one_pending_request_and_event(self):
        project = self.service.create_project(self.owner, "Idempotent requests")
        manager = self.service.create_user(
            self.owner, "manager@example.org", "Manager", "manager password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Governed"}
        )
        payload = {
            "status": "cancelled",
            "reason": "Manager recommendation",
            "expected_revision": task["revision"],
        }

        first = self.service.update_task(manager, task["id"], payload)
        second = self.service.update_task(manager, task["id"], payload)

        self.assertEqual(first["request"]["id"], second["request"]["id"])
        self.assertEqual(len(self.service.list_owner_action_requests(self.owner)), 1)
        requested_events = [
            event for event in self.service.task_events(self.owner, task["id"])
            if event["event_type"] == "protected_action_requested"
        ]
        self.assertEqual(len(requested_events), 1)

    def test_owner_can_decide_requests_and_stale_approval_stays_pending(self):
        project = self.service.create_project(self.owner, "Owner decisions")
        manager = self.service.create_user(
            self.owner, "decisions@example.org", "Manager", "manager password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")

        def requested_task(title):
            task = self.service.create_task(
                self.owner, {"project_id": project["id"], "title": title}
            )
            outcome = self.service.update_task(
                manager,
                task["id"],
                {
                    "status": "cancelled",
                    "reason": f"Request {title}",
                    "expected_revision": task["revision"],
                },
            )
            return task, outcome["request"]

        approved_task, approved_request = requested_task("Approve")
        rejected_task, rejected_request = requested_task("Reject")
        cancelled_task, cancelled_request = requested_task("Cancel")
        stale_task, stale_request = requested_task("Stale")
        direct_task, direct_request = requested_task("Direct")

        terminal_task = self.service.create_task(
            self.owner,
            {"project_id": project["id"], "title": "Terminal direct", "owner_user_id": manager["id"]},
        )
        terminal_submission = self.service.submit_task(manager, terminal_task["id"], "done")
        self.service.accept_submission(self.owner, terminal_submission["id"], "accepted")
        terminal_task = self.service.get_task(self.owner, terminal_task["id"])
        terminal_request = self.service.update_task(
            manager,
            terminal_task["id"],
            {
                "status": "in_progress",
                "reason": "More work is needed",
                "expected_revision": terminal_task["revision"],
            },
        )["request"]

        approved = self.service.decide_owner_action_request(
            self.owner, approved_request["id"], "approved", "Owner agrees"
        )
        rejected = self.service.decide_owner_action_request(
            self.owner, rejected_request["id"], "rejected", "Owner declines"
        )
        cancelled = self.service.decide_owner_action_request(
            self.owner, cancelled_request["id"], "cancelled", "No longer needed"
        )
        self.assertEqual(approved["request"]["status"], "approved")
        self.assertEqual(rejected["request"]["status"], "rejected")
        self.assertEqual(cancelled["request"]["status"], "cancelled")
        self.assertEqual(self.service.get_task(self.owner, approved_task["id"])["status"], "cancelled")
        self.assertEqual(self.service.get_task(self.owner, rejected_task["id"])["status"], "draft")
        self.assertEqual(self.service.get_task(self.owner, cancelled_task["id"])["status"], "draft")

        self.service.update_task(
            self.owner,
            direct_task["id"],
            {
                "status": "cancelled",
                "reason": "Owner performed the requested action directly",
                "expected_revision": direct_task["revision"],
            },
        )
        self.service.reopen_task(
            self.owner,
            terminal_task["id"],
            "Owner recorded the required revised timeline",
            "2027-08-01",
        )
        all_requests = {
            request["id"]: request
            for request in self.service.list_owner_action_requests(self.owner, status=None)
        }
        self.assertEqual(all_requests[direct_request["id"]]["status"], "approved")
        self.assertEqual(all_requests[terminal_request["id"]]["status"], "approved")

        self.service.update_task(
            self.owner,
            stale_task["id"],
            {"title": "Changed first", "expected_revision": stale_task["revision"]},
        )
        with self.assertRaisesRegex(ValueError, "revision|conflict|stale"):
            self.service.decide_owner_action_request(
                self.owner, stale_request["id"], "approved", "Too late"
            )
        pending = {
            request["id"]: request
            for request in self.service.list_owner_action_requests(self.owner)
        }
        self.assertEqual(pending[stale_request["id"]]["status"], "pending")

    def test_owner_approval_dispatches_every_supported_protected_action(self):
        project = self.service.create_project(self.owner, "Decision dispatch")
        manager = self.service.create_user(
            self.owner, "dispatch@example.org", "Manager", "manager password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")

        accepted_task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Accept", "owner_user_id": manager["id"]}
        )
        accepted_submission = self.service.submit_task(manager, accepted_task["id"], "ready")
        requested = self.service.accept_submission(manager, accepted_submission["id"], "recommend")
        self.service.decide_owner_action_request(self.owner, requested["request"]["id"], "approved")
        self.assertEqual(self.service.get_task(self.owner, accepted_task["id"])["status"], "completed")

        changes_task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Changes", "owner_user_id": manager["id"]}
        )
        changes_submission = self.service.submit_task(manager, changes_task["id"], "draft")
        requested = self.service.request_changes(manager, changes_submission["id"], "revise")
        self.service.decide_owner_action_request(self.owner, requested["request"]["id"], "approved")
        self.assertEqual(self.service.get_task(self.owner, changes_task["id"])["status"], "changes_requested")

        reopen_task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Reopen", "owner_user_id": manager["id"]}
        )
        reopen_submission = self.service.submit_task(manager, reopen_task["id"], "done")
        self.service.accept_submission(self.owner, reopen_submission["id"], "accepted")
        requested = self.service.reopen_task(manager, reopen_task["id"], "new scope", "2027-03-01")
        self.service.decide_owner_action_request(self.owner, requested["request"]["id"], "approved")
        self.assertEqual(self.service.get_task(self.owner, reopen_task["id"])["status"], "reopened")

        hold_task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Hold", "owner_user_id": manager["id"]}
        )
        requested = self.service.set_on_hold(
            manager, hold_task["id"], "vendor", "2027-04-01", manager["id"]
        )
        self.service.decide_owner_action_request(self.owner, requested["request"]["id"], "approved")
        self.assertEqual(self.service.get_task(self.owner, hold_task["id"])["status"], "on_hold")

        schedule_task = self.service.create_task(
            self.owner,
            {
                "project_id": project["id"],
                "title": "Schedule",
                "owner_user_id": manager["id"],
                "due_date": "2027-01-01",
            },
        )
        proposal = self.service.propose_schedule(manager, schedule_task["id"], None, "2027-02-01", "later")
        requested = self.service.approve_schedule_proposal(manager, proposal["id"], "recommend")
        self.service.decide_owner_action_request(self.owner, requested["request"]["id"], "approved")
        self.assertEqual(self.service.get_task(self.owner, schedule_task["id"])["due_date"], "2027-02-01")

        rejected_proposal = self.service.propose_schedule(
            manager, schedule_task["id"], None, "2027-03-01", "too late"
        )
        requested = self.service.reject_schedule_proposal(manager, rejected_proposal["id"], "not suitable")
        self.service.decide_owner_action_request(self.owner, requested["request"]["id"], "approved")
        self.assertEqual(
            self.service.get_schedule_proposal(self.owner, rejected_proposal["id"])["status"], "rejected"
        )

        close_project = self.service.create_project(self.owner, "Close dispatch")
        self.service.grant_project_access(self.owner, close_project["id"], manager["id"], "manager")
        requested = self.service.close_project(manager, close_project["id"], "finished")
        self.service.decide_owner_action_request(self.owner, requested["request"]["id"], "approved")
        self.assertEqual(self.service.get_project(self.owner, close_project["id"])["status"], "closed")

    def test_repeated_final_result_marking_emits_only_real_state_changes(self):
        project = self.service.create_project(self.owner, "Final results")
        task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Final"}
        )
        submission = self.service.submit_task(self.owner, task["id"], "done")
        self.service.accept_submission(self.owner, submission["id"], "accepted")

        first = self.service.mark_final_result(
            self.owner, task["id"], "submission", submission["id"]
        )
        second = self.service.mark_final_result(
            self.owner, task["id"], "submission", submission["id"]
        )
        self.assertEqual(first["id"], second["id"])
        marked_events = [
            event for event in self.service.task_events(self.owner, task["id"])
            if event["event_type"] == "final_result_marked"
        ]
        self.assertEqual(len(marked_events), 1)

        self.service.unmark_final_result(self.owner, first["id"])
        self.service.mark_final_result(
            self.owner, task["id"], "submission", submission["id"]
        )
        marked_events = [
            event for event in self.service.task_events(self.owner, task["id"])
            if event["event_type"] == "final_result_marked"
        ]
        self.assertEqual(len(marked_events), 2)


if __name__ == "__main__":
    unittest.main()
