from __future__ import annotations

import json
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

    # SRFCZD R2: approving a request records the Owner's decision note as the
    # request's decision reason and on protected_action_approved; the governed
    # action itself still carries the Manager's reason, which is why it was asked.
    def test_owner_approval_records_owner_decision_note_not_manager_reason(self):
        project, manager = self._intent_fixture("Decision note")

        def request_status(task):
            return self.service.update_task(
                manager, task["id"],
                {"status": "cancelled", "reason": "manager reason", "expected_revision": task["revision"]},
            )["request"]

        def request_hold(task):
            return self.service.set_on_hold(
                manager, task["id"], "manager reason", "2027-04-01", manager["id"]
            )["request"]

        def request_reopen(task):
            return self.service.reopen_task(manager, task["id"], "manager reason", "2027-03-01")["request"]

        cases = (
            ("update_task_status", request_status, "task_updated", False),
            ("set_on_hold", request_hold, "task_on_hold", False),
            ("reopen_task", request_reopen, "task_reopened", True),
        )
        for action, make_request, action_event, needs_completed in cases:
            for owner_note, expected in (("OWNER NOTE", "OWNER NOTE"), ("", None), ("   ", None)):
                with self.subTest(action=action, owner_note=owner_note):
                    title = f"{action} {owner_note!r}"
                    if needs_completed:
                        task = self._completed_task(project, manager, title)
                    else:
                        task = self.service.create_task(
                            self.owner,
                            {"project_id": project["id"], "title": title, "owner_user_id": manager["id"]},
                        )
                    request = make_request(task)
                    decided = self.service.decide_owner_action_request(
                        self.owner, request["id"], "approved", owner_note
                    )["request"]
                    self.assertEqual(decided["status"], "approved")
                    self.assertEqual(decided["reason"], "manager reason")
                    self.assertEqual(decided["decision_reason"], expected)
                    events = self.service.task_events(self.owner, task["id"])
                    approved = [
                        event for event in events
                        if event["event_type"] == "protected_action_approved"
                        and request["id"] in (event["after_json"] or "")
                    ]
                    self.assertEqual(len(approved), 1)
                    self.assertEqual(approved[0]["reason"], expected)
                    detail = json.loads(approved[0]["after_json"])
                    self.assertEqual(detail["request_reason"], "manager reason")
                    governed = [event for event in events if event["event_type"] == action_event]
                    self.assertEqual(governed[-1]["reason"], "manager reason")

        # Schedule approval keeps its existing proposal decision reason (the Manager's
        # recommendation when given); the request row still records the Owner's note.
        task = self.service.create_task(
            self.owner,
            {"project_id": project["id"], "title": "Schedule note", "owner_user_id": manager["id"],
             "due_date": "2027-01-01"},
        )
        proposal = self.service.propose_schedule(manager, task["id"], None, "2027-02-01", "later")
        request = self.service.approve_schedule_proposal(manager, proposal["id"], "manager reason")["request"]
        decided = self.service.decide_owner_action_request(
            self.owner, request["id"], "approved", "OWNER NOTE"
        )["request"]
        self.assertEqual(decided["decision_reason"], "OWNER NOTE")
        self.assertEqual(
            self.service.get_schedule_proposal(self.owner, proposal["id"])["decision_reason"], "manager reason"
        )

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

    # SRFCZD: a direct Owner action reconciles only the pending requests whose
    # intent matches what was executed; every other request stays pending with no
    # protected_action_approved event (a later approval of a stale one gets 409).
    def _intent_fixture(self, name):
        project = self.service.create_project(self.owner, name)
        manager = self.service.create_user(
            self.owner, f"{name.lower().replace(' ', '-')}@example.org", "Manager", "manager password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        return project, manager

    def _completed_task(self, project, manager, title):
        task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": title, "owner_user_id": manager["id"]}
        )
        submission = self.service.submit_task(manager, task["id"], "done")
        self.service.accept_submission(self.owner, submission["id"], "accepted")
        return self.service.get_task(self.owner, task["id"])

    def _request_status(self, request_id):
        requests = self.service.list_owner_action_requests(self.owner, status=None)
        return {request["id"]: request for request in requests}[request_id]["status"]

    def _approved_event_count(self, request_id, task_id=None, project_id=None):
        if task_id is not None:
            events = self.service.task_events(self.owner, task_id)
            details = [event["after_json"] for event in events if event["event_type"] == "protected_action_approved"]
        else:
            events = self.service.project_events(self.owner, project_id)
            details = [event["detail_json"] for event in events if event["event_type"] == "protected_action_approved"]
        return sum(1 for detail in details if detail and request_id in detail)

    def _assert_untouched(self, request, task_id=None, project_id=None):
        self.assertEqual(self._request_status(request["id"]), "pending")
        self.assertEqual(self._approved_event_count(request["id"], task_id, project_id), 0)

    def _assert_resolved(self, request, task_id=None, project_id=None):
        self.assertEqual(self._request_status(request["id"]), "approved")
        self.assertEqual(self._approved_event_count(request["id"], task_id, project_id), 1)

    def test_direct_status_change_leaves_request_for_another_status_pending(self):
        project, manager = self._intent_fixture("Intent status")
        for owner_status in ("in_progress", "delayed"):
            with self.subTest(owner_status=owner_status):
                task = self.service.create_task(
                    self.owner, {"project_id": project["id"], "title": f"Status {owner_status}"}
                )
                request = self.service.update_task(
                    manager, task["id"],
                    {"status": "cancelled", "reason": "Manager wants it cancelled",
                     "expected_revision": task["revision"]},
                )["request"]
                self.service.update_task(
                    self.owner, task["id"],
                    {"status": owner_status, "reason": "Owner keeps it going",
                     "expected_revision": task["revision"]},
                )
                self._assert_untouched(request, task_id=task["id"])

    def test_direct_reopen_leaves_terminal_cancel_or_abandon_request_pending(self):
        project, manager = self._intent_fixture("Intent reopen")
        for requested in ("cancelled", "abandoned"):
            with self.subTest(requested=requested):
                task = self._completed_task(project, manager, f"Reopen {requested}")
                request = self.service.update_task(
                    manager, task["id"],
                    {"status": requested, "reason": "Manager wants it closed out",
                     "expected_revision": task["revision"]},
                )["request"]
                self.service.reopen_task(self.owner, task["id"], "Owner reopens instead", "2027-08-01")
                self._assert_untouched(request, task_id=task["id"])

        task = self._completed_task(project, manager, "Reopen matching")
        back_to_work = self.service.update_task(
            manager, task["id"],
            {"status": "in_progress", "reason": "More work", "expected_revision": task["revision"]},
        )["request"]
        same_date = self.service.reopen_task(manager, task["id"], "More work", "2027-08-01")["request"]
        other_date = self.service.reopen_task(manager, task["id"], "Much later", "2030-12-31")["request"]
        self.service.reopen_task(self.owner, task["id"], "Owner reopens", "2027-08-01")
        self._assert_resolved(back_to_work, task_id=task["id"])
        self._assert_resolved(same_date, task_id=task["id"])
        self._assert_untouched(other_date, task_id=task["id"])

    def test_direct_schedule_decision_resolves_only_the_same_proposal(self):
        project, manager = self._intent_fixture("Intent schedule")
        for decision in ("approve", "reject"):
            with self.subTest(decision=decision):
                task = self.service.create_task(
                    self.owner,
                    {"project_id": project["id"], "title": f"Schedule {decision}",
                     "owner_user_id": manager["id"], "due_date": "2027-01-01"},
                )
                proposal_a = self.service.propose_schedule(manager, task["id"], None, "2027-02-01", "A")
                proposal_b = self.service.propose_schedule(manager, task["id"], None, "2027-03-01", "B")
                if decision == "approve":
                    request_a = self.service.approve_schedule_proposal(manager, proposal_a["id"], "take A")["request"]
                    request_b = self.service.approve_schedule_proposal(manager, proposal_b["id"], "take B")["request"]
                    self.service.approve_schedule_proposal(self.owner, proposal_a["id"], "Owner takes A")
                else:
                    request_a = self.service.reject_schedule_proposal(manager, proposal_a["id"], "drop A")["request"]
                    request_b = self.service.reject_schedule_proposal(manager, proposal_b["id"], "drop B")["request"]
                    self.service.reject_schedule_proposal(self.owner, proposal_a["id"], "Owner drops A")
                self._assert_resolved(request_a, task_id=task["id"])
                self._assert_untouched(request_b, task_id=task["id"])
                self.assertEqual(
                    self.service.get_schedule_proposal(self.owner, proposal_b["id"])["status"], "pending"
                )

    def test_direct_hold_resolves_only_the_same_checkpoint_and_hold_owner(self):
        project, manager = self._intent_fixture("Intent hold")
        other = self.service.create_user(
            self.owner, "intent-hold-other@example.org", "Other", "other password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], other["id"], "member")
        cases = (
            ("different checkpoint", "2030-12-31", manager, False),
            ("different hold owner", "2027-04-01", other, False),
            ("same intent", "2027-04-01", manager, True),
        )
        for label, checkpoint, hold_owner, matches in cases:
            with self.subTest(label=label):
                task = self.service.create_task(
                    self.owner,
                    {"project_id": project["id"], "title": f"Hold {label}", "owner_user_id": manager["id"]},
                )
                request = self.service.set_on_hold(
                    manager, task["id"], "vendor", "2027-04-01", manager["id"]
                )["request"]
                self.service.set_on_hold(self.owner, task["id"], "Owner hold", checkpoint, hold_owner["id"])
                if matches:
                    self._assert_resolved(request, task_id=task["id"])
                else:
                    self._assert_untouched(request, task_id=task["id"])

    def test_direct_cancel_leaves_another_managers_abandon_request_pending(self):
        project, manager = self._intent_fixture("Intent cancel")
        second = self.service.create_user(
            self.owner, "intent-cancel-second@example.org", "Second", "second password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], second["id"], "manager")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Cancel"})
        cancel = self.service.update_task(
            manager, task["id"],
            {"status": "cancelled", "reason": "Cancel it", "expected_revision": task["revision"]},
        )["request"]
        abandon = self.service.update_task(
            second, task["id"],
            {"status": "abandoned", "reason": "Abandon it", "expected_revision": task["revision"]},
        )["request"]
        self.service.update_task(
            self.owner, task["id"],
            {"status": "cancelled", "reason": "Owner cancels", "expected_revision": task["revision"]},
        )
        self._assert_resolved(cancel, task_id=task["id"])
        self._assert_untouched(abandon, task_id=task["id"])

    def test_direct_close_resolves_only_the_same_residual_set_whatever_the_note(self):
        _, manager = self._intent_fixture("Intent close")
        for label in ("different note", "different residual set", "same intent"):
            with self.subTest(label=label):
                project = self.service.create_project(self.owner, f"Close {label}")
                self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
                self.service.create_task(self.owner, {"project_id": project["id"], "title": "Residual A"})
                residual_b = self.service.create_task(
                    self.owner, {"project_id": project["id"], "title": "Residual B"}
                )
                request = self.service.close_project(manager, project["id"], "A and B remain")["request"]
                note = "A and B remain"
                if label == "different note":
                    note = "Owner closes with other residual notes"
                elif label == "different residual set":
                    self.service.update_task(
                        self.owner, residual_b["id"],
                        {"status": "cancelled", "reason": "Not needed",
                         "expected_revision": residual_b["revision"]},
                    )
                self.service.close_project(self.owner, project["id"], note, exceptional=True)
                if label != "different residual set":
                    self._assert_resolved(request, project_id=project["id"])
                else:
                    self._assert_untouched(request, project_id=project["id"])


if __name__ == "__main__":
    unittest.main()
