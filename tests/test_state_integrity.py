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
        self.assertEqual([result[1] for result in outcomes if result[0] == "error"], ["Conflict"], outcomes)
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
        self._approve_and_assert_resolved(requested["request"], task_id=accepted_task["id"])
        self.assertEqual(self.service.get_task(self.owner, accepted_task["id"])["status"], "completed")

        changes_task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Changes", "owner_user_id": manager["id"]}
        )
        changes_submission = self.service.submit_task(manager, changes_task["id"], "draft")
        requested = self.service.request_changes(manager, changes_submission["id"], "revise")
        self._approve_and_assert_resolved(requested["request"], task_id=changes_task["id"])
        self.assertEqual(self.service.get_task(self.owner, changes_task["id"])["status"], "changes_requested")

        reopen_task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Reopen", "owner_user_id": manager["id"]}
        )
        reopen_submission = self.service.submit_task(manager, reopen_task["id"], "done")
        self.service.accept_submission(self.owner, reopen_submission["id"], "accepted")
        requested = self.service.reopen_task(manager, reopen_task["id"], "new scope", "2027-03-01")
        self._approve_and_assert_resolved(requested["request"], task_id=reopen_task["id"])
        self.assertEqual(self.service.get_task(self.owner, reopen_task["id"])["status"], "reopened")

        hold_task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Hold", "owner_user_id": manager["id"]}
        )
        requested = self.service.set_on_hold(
            manager, hold_task["id"], "vendor", "2027-04-01", manager["id"]
        )
        self._approve_and_assert_resolved(requested["request"], task_id=hold_task["id"])
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
        self._approve_and_assert_resolved(requested["request"], task_id=schedule_task["id"])
        self.assertEqual(self.service.get_task(self.owner, schedule_task["id"])["due_date"], "2027-02-01")

        rejected_proposal = self.service.propose_schedule(
            manager, schedule_task["id"], None, "2027-03-01", "too late"
        )
        requested = self.service.reject_schedule_proposal(manager, rejected_proposal["id"], "not suitable")
        self._approve_and_assert_resolved(requested["request"], task_id=schedule_task["id"])
        self.assertEqual(
            self.service.get_schedule_proposal(self.owner, rejected_proposal["id"])["status"], "rejected"
        )

        close_project = self.service.create_project(self.owner, "Close dispatch")
        self.service.grant_project_access(self.owner, close_project["id"], manager["id"], "manager")
        requested = self.service.close_project(manager, close_project["id"], "finished")
        self._approve_and_assert_resolved(requested["request"], project_id=close_project["id"])
        self.assertEqual(self.service.get_project(self.owner, close_project["id"])["status"], "closed")

    def _approve_and_assert_resolved(self, request, task_id=None, project_id=None):
        decided = self.service.decide_owner_action_request(self.owner, request["id"], "approved")
        self.assertEqual(decided["request"]["status"], "approved")
        self._assert_resolved(request, task_id=task_id, project_id=project_id)

    # SRFCZD R2: approving a request records the Owner's decision note as the
    # request's decision reason and on protected_action_approved; the governed
    # action itself still carries the Manager's reason, which is why it was asked.
    def test_owner_approval_records_owner_decision_note_not_manager_reason(self):
        project, manager = self._intent_fixture("Decision note")

        def new_task(title, **fields):
            return self.service.create_task(
                self.owner,
                {"project_id": project["id"], "title": title, "owner_user_id": manager["id"], **fields},
            )

        def task_events(task_id):
            return lambda: [
                (event["event_type"], event["after_json"], event["reason"])
                for event in self.service.task_events(self.owner, task_id)
            ]

        def request_status(title):
            task = new_task(title)
            return self.service.update_task(
                manager, task["id"],
                {"status": "cancelled", "reason": "manager reason", "expected_revision": task["revision"]},
            )["request"], task_events(task["id"])

        def request_hold(title):
            task = new_task(title)
            return self.service.set_on_hold(
                manager, task["id"], "manager reason", "2027-04-01", manager["id"]
            )["request"], task_events(task["id"])

        def request_reopen(title):
            task = self._completed_task(project, manager, title)
            return self.service.reopen_task(
                manager, task["id"], "manager reason", "2027-03-01"
            )["request"], task_events(task["id"])

        # SRFCZD R5 (SEM-5): the submission, schedule-rejection and project-close paths
        # record the Owner's note too; close_project's approval is a project event.
        def request_accept(title):
            task = new_task(title)
            submission = self.service.submit_task(manager, task["id"], "ready")
            return self.service.accept_submission(
                manager, submission["id"], "manager reason"
            )["request"], task_events(task["id"])

        def request_changes(title):
            task = new_task(title)
            submission = self.service.submit_task(manager, task["id"], "draft")
            return self.service.request_changes(
                manager, submission["id"], "manager reason"
            )["request"], task_events(task["id"])

        def request_schedule_reject(title):
            task = new_task(title, due_date="2027-01-01")
            proposal = self.service.propose_schedule(manager, task["id"], None, "2027-02-01", "later")
            return self.service.reject_schedule_proposal(
                manager, proposal["id"], "manager reason"
            )["request"], task_events(task["id"])

        def request_close(title):
            close = self.service.create_project(self.owner, title)
            self.service.grant_project_access(self.owner, close["id"], manager["id"], "manager")
            return self.service.close_project(manager, close["id"], "manager reason")["request"], lambda: [
                (event["event_type"], event["detail_json"], event["reason"])
                for event in self.service.project_events(self.owner, close["id"])
            ]

        cases = (
            ("update_task_status", request_status, "task_updated"),
            ("set_on_hold", request_hold, "task_on_hold"),
            ("reopen_task", request_reopen, "task_reopened"),
            ("accept_submission", request_accept, "submission_accepted"),
            ("request_changes", request_changes, "changes_requested"),
            ("reject_schedule_proposal", request_schedule_reject, "schedule_proposal_rejected"),
            ("close_project", request_close, "project_closed"),
        )
        for action, make_request, action_event in cases:
            for owner_note, expected in (("OWNER NOTE", "OWNER NOTE"), ("", None), ("   ", None)):
                with self.subTest(action=action, owner_note=owner_note):
                    request, events = make_request(f"{action} {owner_note!r}")
                    self.assertEqual(request["action"], action)
                    decided = self.service.decide_owner_action_request(
                        self.owner, request["id"], "approved", owner_note
                    )["request"]
                    self.assertEqual(decided["status"], "approved")
                    self.assertEqual(decided["reason"], "manager reason")
                    self.assertEqual(decided["decision_reason"], expected)
                    approved = [
                        (detail, reason) for event_type, detail, reason in events()
                        if event_type == "protected_action_approved" and request["id"] in (detail or "")
                    ]
                    self.assertEqual(len(approved), 1)
                    self.assertEqual(approved[0][1], expected)
                    self.assertEqual(json.loads(approved[0][0])["request_reason"], "manager reason")
                    governed = [reason for event_type, _, reason in events() if event_type == action_event]
                    self.assertEqual(governed[-1], "manager reason")

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

    # SRFCZD R6 (R5-1): a terminal task's generic edit into another terminal or governed
    # status is refused for a Manager before any request exists (no Owner approval or
    # direct action could ever resolve it), so reopen only ever meets back-to-work
    # requests. It resolves the matching ones and leaves every other request pending.
    def test_direct_reopen_resolves_only_matching_requests(self):
        project, manager = self._intent_fixture("Intent reopen")
        for requested in ("cancelled", "abandoned"):
            with self.subTest(requested=requested):
                task = self._completed_task(project, manager, f"Reopen {requested}")
                with self.assertRaisesRegex(ValueError, "not edited back into work"):
                    self.service.update_task(
                        manager, task["id"],
                        {"status": requested, "reason": "Manager wants it closed out",
                         "expected_revision": task["revision"]},
                    )
                self.assertEqual(
                    [r for r in self.service.list_owner_action_requests(self.owner, status=None)
                     if r["task_id"] == task["id"]],
                    [],
                )

        task = self._completed_task(project, manager, "Reopen matching")
        sibling = self._completed_task(project, manager, "Reopen sibling")
        back_to_work = self.service.update_task(
            manager, task["id"],
            {"status": "in_progress", "reason": "More work", "expected_revision": task["revision"]},
        )["request"]
        sibling_back_to_work = self.service.update_task(
            manager, sibling["id"],
            {"status": "in_progress", "reason": "More work", "expected_revision": sibling["revision"]},
        )["request"]
        same_date = self.service.reopen_task(manager, task["id"], "More work", "2027-08-01")["request"]
        other_date = self.service.reopen_task(manager, task["id"], "Much later", "2030-12-31")["request"]
        self.service.reopen_task(self.owner, task["id"], "Owner reopens", "2027-08-01")
        self._assert_resolved(back_to_work, task_id=task["id"])
        self._assert_resolved(same_date, task_id=task["id"])
        self._assert_untouched(other_date, task_id=task["id"])
        self._assert_untouched(sibling_back_to_work, task_id=sibling["id"])

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


    # SRFCZD R3: approving a Manager's close request re-checks, inside the close
    # transaction, that the open work is still the residual set the request recorded.
    # A changed set refuses with 409 and leaves the project open and the request pending.
    def _close_request_fixture(self, name):
        project, manager = self._intent_fixture(name)
        self.service.create_task(self.owner, {"project_id": project["id"], "title": "Residual A"})
        request = self.service.close_project(manager, project["id"], "A remains")["request"]
        self.assertTrue(json.loads(request["payload_json"])["exceptional"])
        return project, manager, request

    def _project_event_types(self, project_id):
        return [event["event_type"] for event in self.service.project_events(self.owner, project_id)]

    def test_close_approval_refuses_when_open_work_changed_since_request(self):
        project, _, request = self._close_request_fixture("Close changed")
        self.service.create_task(self.owner, {"project_id": project["id"], "title": "Residual B"})
        _, manager = self._intent_fixture("Close changed plain")
        plain = self.service.create_project(self.owner, "Close changed from none")
        self.service.grant_project_access(self.owner, plain["id"], manager["id"], "manager")
        plain_request = self.service.close_project(manager, plain["id"], "finished")["request"]
        self.assertFalse(json.loads(plain_request["payload_json"])["exceptional"])
        self.service.create_task(self.owner, {"project_id": plain["id"], "title": "Late work"})
        status_project, _, status_request = self._close_request_fixture("Close status changed")
        residual = self.service.list_tasks(self.owner, status_project["id"])[0]
        self.service.update_task(
            self.owner, residual["id"], {"status": "in_progress", "reason": "Started", "expected_revision": residual["revision"]}
        )

        for label, target, pending in (
            ("task added", project, request),
            ("non-exceptional request now has work", plain, plain_request),
            ("residual status changed", status_project, status_request),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    service_module.Conflict, "open work changed since this close was requested"
                ):
                    self.service.decide_owner_action_request(self.owner, pending["id"], "approved", "ok")
                self.assertEqual(self.service.get_project(self.owner, target["id"])["status"], "active")
                self._assert_untouched(pending, project_id=target["id"])
                self.assertNotIn("project_closed", self._project_event_types(target["id"]))

    def test_close_approval_succeeds_when_open_work_is_unchanged(self):
        project, _, request = self._close_request_fixture("Close unchanged")

        decided = self.service.decide_owner_action_request(self.owner, request["id"], "approved", "ok")

        self.assertEqual(decided["request"]["status"], "approved")
        closed = self.service.get_project(self.owner, project["id"])
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["closure_is_exceptional"], 1)
        self._assert_resolved(request, project_id=project["id"])

    def test_direct_owner_close_with_changed_work_behaves_as_before(self):
        project, _, request = self._close_request_fixture("Close direct")
        self.service.create_task(self.owner, {"project_id": project["id"], "title": "Residual B"})

        closed = self.service.close_project(self.owner, project["id"], "A and B remain", exceptional=True)

        self.assertEqual(closed["status"], "closed")
        self._assert_untouched(request, project_id=project["id"])
        self.assertIn("project_closed", self._project_event_types(project["id"]))

    # SRFCZD R5 (SEM-1): a direct close reconciles a Manager's close request only when
    # every residual task still has the status the request recorded, the same test an
    # approval applies; otherwise approving that request would return 409.
    def test_direct_close_leaves_request_pending_when_a_residual_status_changed(self):
        project, _, request = self._close_request_fixture("Close residual status")
        residual = self.service.list_tasks(self.owner, project["id"])[0]
        self.assertEqual(residual["status"], "draft")
        self.service.update_task(
            self.owner, residual["id"],
            {"status": "in_progress", "reason": "Started", "expected_revision": residual["revision"]},
        )

        closed = self.service.close_project(self.owner, project["id"], "A remains", exceptional=True)

        self.assertEqual(closed["status"], "closed")
        self._assert_untouched(request, project_id=project["id"])

    # SRFCZD R5 (SEM-4): residual titles and their order are not intent. Renaming a
    # residual task (which also reorders the title-sorted list) before the Owner closes
    # still resolves the request, directly or through its approval.
    def test_renamed_residual_work_still_resolves_or_approves_the_close_request(self):
        for path in ("direct", "approval"):
            with self.subTest(path=path):
                project, manager = self._intent_fixture(f"Close rename {path}")
                alpha = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Alpha"})
                self.service.create_task(self.owner, {"project_id": project["id"], "title": "Bravo"})
                request = self.service.close_project(manager, project["id"], "Alpha and Bravo remain")["request"]
                self.service.update_task(
                    self.owner, alpha["id"], {"title": "Zulu", "expected_revision": alpha["revision"]}
                )
                if path == "direct":
                    self.service.close_project(self.owner, project["id"], "Owner closes", exceptional=True)
                else:
                    decided = self.service.decide_owner_action_request(self.owner, request["id"], "approved", "ok")
                    self.assertEqual(decided["request"]["status"], "approved")
                self.assertEqual(self.service.get_project(self.owner, project["id"])["status"], "closed")
                self._assert_resolved(request, project_id=project["id"])

    def test_close_approval_racing_a_reject_rolls_back_without_closing(self):
        project, _, request = self._close_request_fixture("Close race")
        original = self.service._execute_owner_action_request

        def reject_first(*args, **kwargs):
            with database_transaction(self.db):
                self.db.execute(
                    "UPDATE owner_action_requests SET status='rejected', decision_reason='no' WHERE id=?",
                    (request["id"],),
                )
            return original(*args, **kwargs)

        with patch.object(self.service, "_execute_owner_action_request", side_effect=reject_first):
            with self.assertRaisesRegex(service_module.Conflict, "pending request changed"):
                self.service.decide_owner_action_request(self.owner, request["id"], "approved", "ok")

        self.assertEqual(self.service.get_project(self.owner, project["id"])["status"], "active")
        self.assertEqual(self._request_status(request["id"]), "rejected")
        self.assertNotIn("project_closed", self._project_event_types(project["id"]))


    # SRFCZD R4: two-connection races. Each call runs on its own connection; both pass
    # their pre-checks, then meet at a barrier inside service.transaction, so only the
    # guards inside the transaction can keep the second writer out.
    def _race(self, *calls):
        barrier = threading.Barrier(len(calls))
        local = threading.local()
        outcomes = [None] * len(calls)

        @contextmanager
        def synchronized_transaction(connection):
            if not getattr(local, "waited", False):
                local.waited = True
                barrier.wait(timeout=5)
            with database_transaction(connection):
                yield

        def run(index, call):
            connection = connect(self.db_path)
            try:
                try:
                    outcomes[index] = ("ok", call(AstraService(connection)))
                except Exception as exc:
                    outcomes[index] = ("error", exc)
            finally:
                connection.close()

        with patch.object(service_module, "transaction", synchronized_transaction):
            threads = [threading.Thread(target=run, args=(index, call)) for index, call in enumerate(calls)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=15)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        return outcomes

    def _one_winner(self, outcomes, loser_type=service_module.Conflict):
        winners = [value for kind, value in outcomes if kind == "ok"]
        losers = [value for kind, value in outcomes if kind == "error"]
        self.assertEqual(len(winners), 1, outcomes)
        self.assertEqual(len(losers), 1, outcomes)
        self.assertIs(type(losers[0]), loser_type, outcomes)
        return winners[0]

    def _task_event_count(self, task_id, event_type):
        return sum(1 for event in self.service.task_events(self.owner, task_id) if event["event_type"] == event_type)

    def _as(self, user):
        return lambda service: service.get_user(user["id"])

    def test_concurrent_task_updates_at_one_revision_have_one_winner_and_one_event(self):
        project = self.service.create_project(self.owner, "Update race")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Original"})
        owner = self._as(self.owner)

        def update(title):
            return lambda service: service.update_task(
                owner(service), task["id"], {"title": title, "expected_revision": task["revision"]}
            )

        winner = self._one_winner(self._race(update("First writer"), update("Second writer")))

        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual(current["revision"], task["revision"] + 1)
        self.assertEqual(current["title"], winner["title"])
        self.assertEqual(self._task_event_count(task["id"], "task_updated"), 1)

    def test_task_update_refuses_when_task_is_cancelled_before_its_write(self):
        project = self.service.create_project(self.owner, "Cancelled mid-update")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Original"})
        other = connect(self.db_path)
        self.addCleanup(other.close)
        interleaved = []

        @contextmanager
        def cancel_first(connection):
            if connection is self.db and not interleaved:
                interleaved.append(True)
                AstraService(other).update_task(self.owner, task["id"], {
                    "status": "cancelled", "reason": "Owner cancelled", "expected_revision": task["revision"],
                })
            with database_transaction(connection):
                yield

        with patch.object(service_module, "transaction", cancel_first):
            with self.assertRaises(service_module.Conflict):
                self.service.update_task(
                    self.owner, task["id"], {"title": "Late edit", "progress": 50, "expected_revision": task["revision"]}
                )

        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual(interleaved, [True])
        self.assertEqual((current["status"], current["title"]), ("cancelled", "Original"))
        self.assertEqual(current["revision"], task["revision"] + 1)
        self.assertEqual(self._task_event_count(task["id"], "task_updated"), 1)

    def test_concurrent_equivalent_manager_requests_create_one_pending_request_and_event(self):
        project, manager = self._intent_fixture("Request race")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Governed"})
        payload = {"status": "cancelled", "reason": "Manager recommendation", "expected_revision": task["revision"]}
        request = lambda service: service.update_task(self._as(manager)(service), task["id"], dict(payload))

        outcomes = self._race(request, request)

        self.assertEqual([kind for kind, _ in outcomes], ["ok", "ok"], outcomes)
        self.assertEqual(len({value["request"]["id"] for _, value in outcomes}), 1)
        self.assertEqual(len(self.service.list_owner_action_requests(self.owner)), 1)
        self.assertEqual(self._task_event_count(task["id"], "protected_action_requested"), 1)

    def test_concurrent_equivalent_close_requests_create_one_pending_request_and_event(self):
        project, manager = self._intent_fixture("Close request race")
        self.service.create_task(self.owner, {"project_id": project["id"], "title": "Residual"})
        request = lambda service: service.close_project(self._as(manager)(service), project["id"], "Residual remains")

        outcomes = self._race(request, request)

        self.assertEqual([kind for kind, _ in outcomes], ["ok", "ok"], outcomes)
        self.assertEqual(len({value["request"]["id"] for _, value in outcomes}), 1)
        self.assertEqual(len(self.service.list_owner_action_requests(self.owner)), 1)
        self.assertEqual(self._project_event_types(project["id"]).count("protected_action_requested"), 1)

    def test_non_owner_cannot_approve_or_reject_a_request(self):
        project, manager = self._intent_fixture("Non-owner decisions")
        viewer = self.service.create_user(self.owner, "viewer@example.org", "Viewer", "viewer password safe")
        self.service.grant_project_access(self.owner, project["id"], viewer["id"], "viewer")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Governed"})
        request = self.service.update_task(manager, task["id"], {
            "status": "cancelled", "reason": "Manager recommendation", "expected_revision": task["revision"],
        })["request"]

        for label, actor in (("manager", manager), ("viewer", viewer)):
            for decision in ("approved", "rejected"):
                with self.subTest(actor=label, decision=decision):
                    with self.assertRaises(service_module.Forbidden):
                        self.service.decide_owner_action_request(actor, request["id"], decision, "not mine")
                    self.assertEqual(self._request_status(request["id"]), "pending")
        self.assertEqual(self.service.get_task(self.owner, task["id"])["status"], "draft")

    def test_stale_hold_approval_is_refused_and_request_stays_pending(self):
        project, manager = self._intent_fixture("Stale hold")
        task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Hold", "owner_user_id": manager["id"]}
        )
        request = self.service.set_on_hold(manager, task["id"], "vendor", "2027-04-01", manager["id"])["request"]
        edited = self.service.update_task(
            self.owner, task["id"], {"title": "Unrelated edit", "expected_revision": task["revision"]}
        )

        with self.assertRaises(service_module.Conflict):
            self.service.decide_owner_action_request(self.owner, request["id"], "approved", "ok")

        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual((current["status"], current["revision"]), ("draft", edited["revision"]))
        self._assert_untouched(request, task_id=task["id"])
        self.assertEqual(self._task_event_count(task["id"], "task_on_hold"), 0)

    def test_concurrent_rejections_have_one_winner_and_one_event(self):
        project, manager = self._intent_fixture("Reject race")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Governed"})
        request = self.service.update_task(manager, task["id"], {
            "status": "cancelled", "reason": "Manager recommendation", "expected_revision": task["revision"],
        })["request"]

        def reject(note):
            return lambda service: service.decide_owner_action_request(
                self._as(self.owner)(service), request["id"], "rejected", note
            )

        winner = self._one_winner(self._race(reject("first no"), reject("second no")))

        decided = self.service.list_owner_action_requests(self.owner, status="rejected")
        self.assertEqual([row["decision_reason"] for row in decided], [winner["request"]["decision_reason"]])
        self.assertEqual(self._task_event_count(task["id"], "protected_action_rejected"), 1)

    def test_status_approval_racing_a_reject_is_refused_without_changing_the_task(self):
        project, manager = self._intent_fixture("Status approve race")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Governed"})
        request = self.service.update_task(manager, task["id"], {
            "status": "cancelled", "reason": "Manager recommendation", "expected_revision": task["revision"],
        })["request"]
        other = connect(self.db_path)
        self.addCleanup(other.close)
        original = self.service._execute_owner_action_request

        def reject_first(*args, **kwargs):
            AstraService(other).decide_owner_action_request(self.owner, request["id"], "rejected", "no")
            return original(*args, **kwargs)

        with patch.object(self.service, "_execute_owner_action_request", side_effect=reject_first):
            with self.assertRaises(service_module.Conflict):
                self.service.decide_owner_action_request(self.owner, request["id"], "approved", "ok")

        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual((current["status"], current["revision"]), ("draft", task["revision"]))
        self.assertEqual(self._request_status(request["id"]), "rejected")
        self.assertEqual(self._task_event_count(task["id"], "task_updated"), 0)
        self.assertEqual(self._approved_event_count(request["id"], task_id=task["id"]), 0)

    def test_concurrent_unmark_final_result_emits_one_event(self):
        project = self.service.create_project(self.owner, "Unmark race")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Final"})
        submission = self.service.submit_task(self.owner, task["id"], "done")
        self.service.accept_submission(self.owner, submission["id"], "accepted")
        result = self.service.mark_final_result(self.owner, task["id"], "submission", submission["id"])
        unmark = lambda service: service.unmark_final_result(self._as(self.owner)(service), result["id"])

        self._one_winner(self._race(unmark, unmark), loser_type=KeyError)

        self.assertEqual(self.service.list_task_final_results(self.owner, task["id"]), [])
        self.assertEqual(self._task_event_count(task["id"], "final_result_unmarked"), 1)

    # 03G8EH: submit_task used to check status and allocate MAX(version)+1 before
    # BEGIN IMMEDIATE and then UPDATE the task with no status or revision predicate.
    def _submission_rows(self, task_id):
        return [
            tuple(row) for row in self.db.execute(
                "SELECT version,status,note FROM task_submissions WHERE task_id=? ORDER BY version,submitted_at",
                (task_id,),
            ).fetchall()
        ]

    def _submit_fixture(self, name):
        project, manager = self._intent_fixture(name)
        task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Deliverable", "owner_user_id": manager["id"]}
        )
        return manager, task

    def test_concurrent_submissions_have_one_winner_one_row_and_one_event(self):
        manager, task = self._submit_fixture("Submit race")

        def submit(note):
            return lambda service: service.submit_task(self._as(manager)(service), task["id"], note)

        winner = self._one_winner(self._race(submit("first click"), submit("second click")))

        self.assertEqual(self._submission_rows(task["id"]), [(1, "submitted", winner["note"])])
        self.assertEqual(self._task_event_count(task["id"], "task_submitted"), 1)
        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual((current["status"], current["revision"]), ("submitted", task["revision"] + 1))

    def _interleave_before_submit_write(self, action):
        """Run ``action`` on another connection once submit_task has passed its
        pre-checks, immediately before its first transaction starts."""
        other = connect(self.db_path)
        self.addCleanup(other.close)
        interleaved = []

        @contextmanager
        def other_writer_first(connection):
            if connection is self.db and not interleaved:
                interleaved.append(True)
                action(AstraService(other))
            with database_transaction(connection):
                yield

        return other_writer_first, interleaved

    def test_submit_refuses_when_the_owner_cancels_before_its_write(self):
        manager, task = self._submit_fixture("Cancelled mid-submit")

        def cancel(service):
            service.update_task(self.owner, task["id"], {
                "status": "cancelled", "reason": "Owner cancelled", "expected_revision": task["revision"],
            })

        hook, interleaved = self._interleave_before_submit_write(cancel)
        with patch.object(service_module, "transaction", hook):
            with self.assertRaises(service_module.Conflict):
                self.service.submit_task(manager, task["id"], "late submit")

        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual(interleaved, [True])
        self.assertEqual((current["status"], current["revision"]), ("cancelled", task["revision"] + 1))
        self.assertEqual(self._submission_rows(task["id"]), [])
        self.assertEqual(self._task_event_count(task["id"], "task_submitted"), 0)

    def test_submit_refuses_when_the_task_is_submitted_and_accepted_before_its_write(self):
        manager, task = self._submit_fixture("Accepted mid-submit")

        def submit_and_accept(service):
            submission = service.submit_task(service.get_user(manager["id"]), task["id"], "first")
            service.accept_submission(self.owner, submission["id"], "accepted")

        hook, interleaved = self._interleave_before_submit_write(submit_and_accept)
        with patch.object(service_module, "transaction", hook):
            with self.assertRaises(service_module.Conflict):
                self.service.submit_task(manager, task["id"], "late submit")

        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual(interleaved, [True])
        self.assertEqual(current["status"], "completed")
        self.assertEqual(self._submission_rows(task["id"]), [(1, "accepted", "first")])
        self.assertEqual(self._task_event_count(task["id"], "task_submitted"), 1)

    def test_submit_refuses_when_the_task_is_reassigned_away_before_its_write(self):
        project = self.service.create_project(self.owner, "Reassigned mid-submit")
        member = self.service.create_user(self.owner, "member@example.org", "Member", "member password safe")
        self.service.grant_project_access(self.owner, project["id"], member["id"], "member")
        task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Deliverable", "owner_user_id": member["id"]}
        )

        def reassign(service):
            # No status change: only the revision records that the submitter's
            # permission check is now stale.
            service.update_task(self.owner, task["id"], {
                "owner_user_id": self.owner["id"], "expected_revision": task["revision"],
            })

        hook, interleaved = self._interleave_before_submit_write(reassign)
        with patch.object(service_module, "transaction", hook):
            with self.assertRaises(service_module.Conflict):
                self.service.submit_task(member, task["id"], "no longer mine")

        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual(interleaved, [True])
        self.assertEqual((current["owner_user_id"], current["status"]), (self.owner["id"], task["status"]))
        self.assertEqual(self._submission_rows(task["id"]), [])
        self.assertEqual(self._task_event_count(task["id"], "task_submitted"), 0)
        with self.assertRaises(service_module.Forbidden):   # a fresh attempt is refused outright
            self.service.submit_task(member, task["id"], "retry")

    # Review SVC-1: removing a collaborator or revoking project access does not bump
    # tasks.revision, so the permission itself must be re-checked under the lock.
    def _member(self, project, email):
        member = self.service.create_user(self.owner, email, "Member", "member password safe")
        self.service.grant_project_access(self.owner, project["id"], member["id"], "member")
        return member

    def _assert_not_submitted(self, task):
        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual((current["status"], current["revision"]), (task["status"], task["revision"]))
        self.assertEqual(self._submission_rows(task["id"]), [])
        self.assertEqual(self._task_event_count(task["id"], "task_submitted"), 0)

    def test_submit_refuses_when_the_collaborator_is_removed_before_its_write(self):
        project = self.service.create_project(self.owner, "Collaborator removed mid-submit")
        collaborator = self._member(project, "collaborator@example.org")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Shared work"})
        self.service.add_task_reviewer(self.owner, task["id"], collaborator["id"], "collaborator")
        task = self.service.get_task(self.owner, task["id"])

        def remove(service):
            service.remove_task_reviewer(self.owner, task["id"], collaborator["id"], "collaborator")

        hook, interleaved = self._interleave_before_submit_write(remove)
        with patch.object(service_module, "transaction", hook):
            with self.assertRaises(service_module.Conflict):
                self.service.submit_task(collaborator, task["id"], "no longer a collaborator")

        self.assertEqual(interleaved, [True])
        self._assert_not_submitted(task)
        with self.assertRaises(service_module.Forbidden):
            self.service.submit_task(collaborator, task["id"], "retry")

    def test_submit_refuses_when_project_access_is_revoked_before_its_write(self):
        project = self.service.create_project(self.owner, "Access revoked mid-submit")
        member = self._member(project, "revoked@example.org")
        task = self.service.create_task(
            self.owner, {"project_id": project["id"], "title": "Owned work", "owner_user_id": member["id"]}
        )

        def revoke(service):
            service.revoke_project_access(self.owner, project["id"], member["id"])

        hook, interleaved = self._interleave_before_submit_write(revoke)
        with patch.object(service_module, "transaction", hook):
            with self.assertRaises(service_module.Conflict):   # not a 403 after a committed write
                self.service.submit_task(member, task["id"], "access gone")

        self.assertEqual(interleaved, [True])
        self._assert_not_submitted(task)


    # SRFCZD R5 (RT-1): every governed action re-checks its Owner request inside its own
    # transaction. A reject that lands at the lock, after the approval's pre-checks, refuses
    # the approval with 409 and leaves the task, its record and the rejection as they were.
    def test_each_action_approval_racing_a_reject_is_refused_without_changing_the_task(self):
        project, manager = self._intent_fixture("Guard race")

        def new_task(title, **fields):
            return self.service.create_task(
                self.owner,
                {"project_id": project["id"], "title": title, "owner_user_id": manager["id"], **fields},
            )

        def submission_status(submission_id):
            return lambda: self.service.get_submission(self.owner, submission_id)["status"]

        def proposal_status(proposal_id):
            return lambda: self.service.get_schedule_proposal(self.owner, proposal_id)["status"]

        def accept(title):
            task = new_task(title)
            submission = self.service.submit_task(manager, task["id"], "ready")
            request = self.service.accept_submission(manager, submission["id"], "recommend")["request"]
            return task["id"], request, submission_status(submission["id"])

        def changes(title):
            task = new_task(title)
            submission = self.service.submit_task(manager, task["id"], "draft")
            request = self.service.request_changes(manager, submission["id"], "revise")["request"]
            return task["id"], request, submission_status(submission["id"])

        def reopen(title):
            task = self._completed_task(project, manager, title)
            request = self.service.reopen_task(manager, task["id"], "new scope", "2027-03-01")["request"]
            return task["id"], request, lambda: None

        def hold(title):
            task = new_task(title)
            request = self.service.set_on_hold(manager, task["id"], "vendor", "2027-04-01", manager["id"])["request"]
            return task["id"], request, lambda: None

        def schedule(decide):
            def make(title):
                task = new_task(title, due_date="2027-01-01")
                proposal = self.service.propose_schedule(manager, task["id"], None, "2027-02-01", "later")
                request = decide(manager, proposal["id"], "manager reason")["request"]
                return task["id"], request, proposal_status(proposal["id"])
            return make

        cases = (
            ("accept_submission", accept),
            ("request_changes", changes),
            ("reopen_task", reopen),
            ("set_on_hold", hold),
            ("approve_schedule_proposal", schedule(self.service.approve_schedule_proposal)),
            ("reject_schedule_proposal", schedule(self.service.reject_schedule_proposal)),
        )
        other = connect(self.db_path)
        self.addCleanup(other.close)
        for action, make in cases:
            with self.subTest(action=action):
                task_id, request, record_status = make(f"Race {action}")
                self.assertEqual(request["action"], action)
                before = self.service.get_task(self.owner, task_id)
                record_before = record_status()
                interleaved = []

                # SRFCZD R6 (R5-2): the reject lands at the lock, after every pre-check the
                # action runs before `with transaction` and before its BEGIN IMMEDIATE, so
                # only a guard inside the transaction can refuse the approval.
                @contextmanager
                def reject_at_the_lock(connection):
                    if connection is self.db and not interleaved:
                        interleaved.append(True)
                        AstraService(other).decide_owner_action_request(self.owner, request["id"], "rejected", "no")
                    with database_transaction(connection):
                        yield

                with patch.object(service_module, "transaction", reject_at_the_lock):
                    with self.assertRaisesRegex(service_module.Conflict, "pending request changed"):
                        self.service.decide_owner_action_request(self.owner, request["id"], "approved", "ok")

                self.assertEqual(interleaved, [True])
                current = self.service.get_task(self.owner, task_id)
                fields = ("status", "revision", "due_date")
                self.assertEqual([current[f] for f in fields], [before[f] for f in fields])
                self.assertEqual(record_status(), record_before)
                self.assertEqual(self._request_status(request["id"]), "rejected")
                self.assertEqual(self._approved_event_count(request["id"], task_id=task_id), 0)

    # SRFCZD R5 (RT-2): an approval whose dispatched action fails must not leave the
    # service instance in approval mode for the next, unrelated Owner action.
    def test_failed_approval_clears_the_active_request_for_the_next_action(self):
        project, _, request = self._close_request_fixture("Close flag reset")
        self.service.create_task(self.owner, {"project_id": project["id"], "title": "Residual B"})

        with self.assertRaisesRegex(service_module.Conflict, "open work changed since this close was requested"):
            self.service.decide_owner_action_request(self.owner, request["id"], "approved", "OWNER NOTE")

        self.assertIsNone(self.service._active_owner_request_id)
        self.assertEqual(self.service._active_owner_decision_reason, "")
        task = self.service.list_tasks(self.owner, project["id"])[0]
        updated = self.service.update_task(
            self.owner, task["id"], {"title": "Unrelated edit", "expected_revision": task["revision"]}
        )
        self.assertEqual(updated["title"], "Unrelated edit")
        self._assert_untouched(request, project_id=project["id"])

    # SRFCZD R5 (SEM-2): a Manager's generic edit into a governed status, or out of review,
    # is refused before any request exists, with the Owner's message: the Owner could never
    # approve it and no direct action reconciles it. A terminal task edited back into work
    # still becomes a request, which a dedicated reopen resolves (handoff 7.1).
    def test_manager_generic_update_refuses_governed_targets_and_leaving_review(self):
        project, manager = self._intent_fixture("Governed generic")

        def make(source, title):
            task = self.service.create_task(
                self.owner, {"project_id": project["id"], "title": title, "owner_user_id": manager["id"]}
            )
            if source == "completed":
                return self._completed_task(project, manager, title + " done")
            if source == "submitted":
                self.service.submit_task(manager, task["id"], "ready")
            return self.service.get_task(self.owner, task["id"])

        on_review = "A submitted task leaves review through the dedicated accept or request changes action."
        cases = (
            ("draft", "on_hold", "Use the dedicated on hold action for this transition."),
            ("draft", "completed", "Use the dedicated completed action for this transition."),
            ("draft", "reopened", "Use the dedicated reopened action for this transition."),
            ("completed", "on_hold", "Use the dedicated on hold action for this transition."),
            ("completed", "reopened", "Use the dedicated reopened action for this transition."),
            ("submitted", "in_progress", on_review),
            ("submitted", "cancelled", on_review),
        )
        for source, target, message in cases:
            with self.subTest(source=source, target=target):
                task = make(source, f"{source} to {target}")
                events_before = len(self.service.task_events(self.owner, task["id"]))
                with self.assertRaises(ValueError) as caught:
                    self.service.update_task(
                        manager, task["id"],
                        {"status": target, "reason": "Manager asks", "expected_revision": task["revision"]},
                    )
                self.assertEqual(str(caught.exception), message)
                current = self.service.get_task(self.owner, task["id"])
                self.assertEqual((current["status"], current["revision"]), (source, task["revision"]))
                self.assertEqual(len(self.service.task_events(self.owner, task["id"])), events_before)
                self.assertEqual(self.service.list_owner_action_requests(self.owner), [])

        task = make("completed", "Back to work")
        request = self.service.update_task(
            manager, task["id"],
            {"status": "in_progress", "reason": "More work", "expected_revision": task["revision"]},
        )["request"]
        self.assertEqual(json.loads(request["payload_json"])["from_status"], "completed")
        self.service.reopen_task(self.owner, task["id"], "Owner reopens", "2027-08-01")
        self._assert_resolved(request, task_id=task["id"])

    # T8WHJR: a completed, cancelled or abandoned task is a fixed record. Only the
    # governed reopen (reason and revised due date) changes it; evidence (attachment
    # links, final results) may still be added after closure.
    def _closed_fixture(self, name):
        project, manager = self._intent_fixture(name)
        neighbour = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Open neighbour"})
        closed = []
        for status in ("completed", "cancelled", "abandoned"):
            task = self.service.create_task(
                self.owner, {"project_id": project["id"], "title": f"Closed {status}", "owner_user_id": manager["id"]}
            )
            self.service.add_task_dependency(self.owner, neighbour["id"], task["id"])
            self.service.add_task_reviewer(self.owner, task["id"], manager["id"], "reviewer")
            proposal = self.service.propose_schedule(self.owner, task["id"], "2027-01-04", "2027-01-08", "planned move")
            if status == "completed":
                submission = self.service.submit_task(manager, task["id"], "done")
                self.service.accept_submission(self.owner, submission["id"], "accepted")
            else:
                current = self.service.get_task(self.owner, task["id"])
                self.service.update_task(self.owner, task["id"], {
                    "status": status, "reason": "closing", "expected_revision": current["revision"],
                })
            closed.append((self.service.get_task(self.owner, task["id"]), proposal))
        return project, manager, neighbour, closed

    def _snapshot(self, task_id):
        task = self.service.get_task(self.owner, task_id)
        dependencies = sorted(
            (row["predecessor_task_id"], row["successor_task_id"])
            for row in self.service.get_task_dependencies(self.owner, task_id)
        )
        proposals = sorted(
            (row["id"], row["status"]) for row in self.service.list_schedule_proposals(self.owner, task_id)
        )
        reviewers = sorted((row["user_id"], row["role"]) for row in self.service.list_task_reviewers(self.owner, task_id))
        return task, dependencies, proposals, reviewers, len(self.service.task_events(self.owner, task_id))

    def test_closed_task_refuses_structural_and_schedule_writes_until_reopened(self):
        project, manager, neighbour, closed = self._closed_fixture("Closed writes")
        parent = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Would-be parent"})
        requests_before = len(self.service.list_owner_action_requests(self.owner, status=None))
        for task, proposal in closed:
            for actor in (self.owner, manager):
                role = actor["global_role"] if actor is self.owner else "manager"
                writes = {
                    "set_parent": lambda: self.service.set_parent(actor, task["id"], parent["id"]),
                    "confirm_criticality": lambda: self.service.confirm_criticality(
                        actor, task["id"], "critical", "late evidence"),
                    "propose_schedule": lambda: self.service.propose_schedule(
                        actor, task["id"], "2027-02-01", "2027-02-05", "late move"),
                    "approve_schedule_proposal": lambda: self.service.approve_schedule_proposal(
                        actor, proposal["id"], "approve late"),
                    "add_task_dependency": lambda: self.service.add_task_dependency(
                        actor, parent["id"], task["id"]),
                    "remove_task_dependency": lambda: self.service.remove_task_dependency(
                        actor, neighbour["id"], task["id"], "late unlink"),
                    # Review SVC-1: people are not evidence; an approver added after closure
                    # could otherwise file a reopen request.
                    "add_task_reviewer": lambda: self.service.add_task_reviewer(
                        actor, task["id"], self.owner["id"], "approver"),
                    "remove_task_reviewer": lambda: self.service.remove_task_reviewer(
                        actor, task["id"], manager["id"], "reviewer"),
                }
                for name, write in writes.items():
                    with self.subTest(status=task["status"], role=role, write=name):
                        before = self._snapshot(task["id"])
                        with self.assertRaisesRegex(ValueError, "reopen the task first") as refused:
                            write()
                        self.assertIs(type(refused.exception), ValueError)  # 400 from the pre-check, not 409
                        self.assertEqual(self._snapshot(task["id"]), before)
        self.assertEqual(len(self.service.list_owner_action_requests(self.owner, status=None)), requests_before)

    def test_closed_task_writes_work_again_after_the_governed_reopen(self):
        project, manager, neighbour, closed = self._closed_fixture("Closed reopen")
        task, _ = closed[0]
        self.service.reopen_task(self.owner, task["id"], "more work", "2027-03-01")
        self.assertEqual(self.service.set_parent(self.owner, task["id"], neighbour["id"])["parent_task_id"],
                         neighbour["id"])
        self.assertEqual(self.service.confirm_criticality(self.owner, task["id"], "high", "evidence")["criticality"],
                         "high")
        self.service.remove_task_dependency(self.owner, neighbour["id"], task["id"], "unlink")

    def test_closed_task_may_be_a_predecessor_and_still_takes_evidence(self):
        project, manager, neighbour, closed = self._closed_fixture("Closed evidence")
        task, _ = closed[0]  # completed
        successor = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Open successor"})
        for actor in (self.owner, manager):
            with self.subTest(role="owner" if actor is self.owner else "manager"):
                added = self.service.add_task_dependency(actor, task["id"], successor["id"])
                self.assertTrue(added["created"])
                self.service.remove_task_dependency(actor, task["id"], successor["id"], "test unlink")
        revision = self.service.get_task(self.owner, task["id"])["revision"]
        attachment = self.service.add_task_attachment(self.owner, task["id"], "/data/signed-after-close.pdf")
        submission_id = self.db.execute(
            "SELECT id FROM task_submissions WHERE task_id=?", (task["id"],)).fetchone()["id"]
        result = self.service.mark_final_result(self.owner, task["id"], "submission", submission_id)
        self.service.unmark_final_result(self.owner, result["id"])
        self.service.remove_task_attachment(self.owner, task["id"], attachment["id"])
        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual((current["status"], current["revision"]), ("completed", revision))

    def test_update_task_on_a_closed_task_with_no_change_writes_nothing(self):
        project, manager, neighbour, closed = self._closed_fixture("Closed no-op")
        for task, _ in closed:
            payloads = (
                {"reason": "just a note"},
                {"title": task["title"], "reason": "same title"},
                {},
            )
            for payload in payloads:
                with self.subTest(status=task["status"], payload=sorted(payload)):
                    before = self._snapshot(task["id"])
                    with self.assertRaisesRegex(ValueError, "reopen the task first"):
                        self.service.update_task(
                            self.owner, task["id"], {**payload, "expected_revision": task["revision"]}
                        )
                    self.assertEqual(self._snapshot(task["id"]), before)

    def _close_between_precheck_and_write(self, task, closer):
        other = connect(self.db_path)
        self.addCleanup(other.close)
        interleaved = []

        @contextmanager
        def close_first(connection):
            if connection is self.db and not interleaved:
                interleaved.append(True)
                closer(AstraService(other))
            with database_transaction(connection):
                yield

        return interleaved, close_first

    def _closers(self, task_id):
        """Close the task on a second connection: by cancelling it, or by accepting its
        pending submission (review SVC-4). Each returns the status it leaves."""
        def cancel(service):
            current = service.get_task(self.owner, task_id)
            service.update_task(self.owner, task_id, {
                "status": "cancelled", "reason": "Owner cancelled", "expected_revision": current["revision"],
            })

        def accept(service):
            submission = service.db.execute(
                "SELECT id FROM task_submissions WHERE task_id=? AND status='submitted'", (task_id,)).fetchone()
            service.accept_submission(self.owner, submission["id"], "accepted")

        return {"cancelled": cancel, "completed": accept}

    def test_writes_refuse_when_the_task_closes_before_their_write(self):
        project, manager = self._intent_fixture("Closed mid-write")
        parent = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Parent"})
        neighbour = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Neighbour"})
        writes = {
            "set_parent": lambda task: self.service.set_parent(self.owner, task["id"], parent["id"]),
            "confirm_criticality": lambda task: self.service.confirm_criticality(
                self.owner, task["id"], "critical", "evidence"),
            "propose_schedule": lambda task: self.service.propose_schedule(
                self.owner, task["id"], "2027-02-01", "2027-02-05", "move"),
            "add_task_dependency": lambda task: self.service.add_task_dependency(
                self.owner, parent["id"], task["id"]),
            "remove_task_dependency": lambda task: self.service.remove_task_dependency(
                self.owner, neighbour["id"], task["id"], "unlink"),
            "add_task_reviewer": lambda task: self.service.add_task_reviewer(
                self.owner, task["id"], self.owner["id"], "approver"),
            "remove_task_reviewer": lambda task: self.service.remove_task_reviewer(
                self.owner, task["id"], manager["id"], "reviewer"),
        }
        for closed_as in ("cancelled", "completed"):
            for name, write in writes.items():
                with self.subTest(closed_as=closed_as, write=name):
                    task = self.service.create_task(
                        self.owner, {"project_id": project["id"], "title": f"Racing {name} {closed_as}"})
                    self.service.add_task_dependency(self.owner, neighbour["id"], task["id"])
                    self.service.add_task_reviewer(self.owner, task["id"], manager["id"], "reviewer")
                    if closed_as == "completed":
                        self.service.submit_task(self.owner, task["id"], "ready")
                    events_before = [e["event_type"] for e in self.service.task_events(self.owner, task["id"])]
                    interleaved, close_first = self._close_between_precheck_and_write(
                        task, self._closers(task["id"])[closed_as])
                    with patch.object(service_module, "transaction", close_first):
                        with self.assertRaises(service_module.Conflict):
                            write(task)
                    self.assertEqual(interleaved, [True])
                    current = self.service.get_task(self.owner, task["id"])
                    self.assertEqual(current["status"], closed_as)
                    self.assertIsNone(current["parent_task_id"])
                    self.assertIsNone(current["criticality"])
                    self.assertEqual(
                        [r["predecessor_task_id"] for r in self.service.get_task_dependencies(self.owner, task["id"])],
                        [neighbour["id"]],
                    )
                    self.assertEqual(self.service.list_schedule_proposals(self.owner, task["id"]), [])
                    self.assertEqual(
                        [(r["user_id"], r["role"]) for r in self.service.list_task_reviewers(self.owner, task["id"])],
                        [(manager["id"], "reviewer")],
                    )
                    written = [e["event_type"] for e in self.service.task_events(self.owner, task["id"])][len(events_before):]
                    self.assertNotIn("parent_changed", written)
                    self.assertNotIn("criticality_changed", written)
                    self.assertNotIn("schedule_proposed", written)
                    self.assertNotIn("dependency_added", written)
                    self.assertNotIn("dependency_removed", written)

    def test_schedule_approval_refuses_when_the_task_closes_before_its_write(self):
        project, manager = self._intent_fixture("Closed mid-approval")
        for closed_as in ("cancelled", "completed"):
            for role, actor in (("owner", self.owner), ("manager", manager)):
                with self.subTest(closed_as=closed_as, role=role):
                    task = self.service.create_task(
                        self.owner, {"project_id": project["id"], "title": f"Racing approval {closed_as} {role}"})
                    proposal = self.service.propose_schedule(self.owner, task["id"], "2027-02-01", "2027-02-05", "move")
                    if closed_as == "completed":
                        self.service.submit_task(self.owner, task["id"], "ready")
                    requests_before = len(self.service.list_owner_action_requests(self.owner, status=None))
                    interleaved, close_first = self._close_between_precheck_and_write(
                        task, self._closers(task["id"])[closed_as])
                    with patch.object(service_module, "transaction", close_first):
                        # Review SVC-2: a Manager's request is refused too, not queued as a 202.
                        with self.assertRaises(service_module.Conflict):
                            self.service.approve_schedule_proposal(actor, proposal["id"], "approve")
                    self.assertEqual(interleaved, [True])
                    current = self.service.get_task(self.owner, task["id"])
                    self.assertEqual((current["status"], current["start_date"], current["due_date"]),
                                     (closed_as, None, None))
                    self.assertEqual(self.service.get_schedule_proposal(self.owner, proposal["id"])["status"], "pending")
                    self.assertEqual(self._task_event_count(task["id"], "schedule_revised"), 0)
                    self.assertEqual(self._task_event_count(task["id"], "protected_action_requested"), 0)
                    self.assertEqual(len(self.service.list_owner_action_requests(self.owner, status=None)),
                                     requests_before)

    # SRFCZD R6 (R5-1): from completed, cancelled or abandoned, a Manager's generic edit to
    # any status that is not ordinary work (cancelled, abandoned, changes_requested) is
    # refused with the Owner's message and creates no request: the Owner could never
    # approve it (400) and reopen reconciles only back-to-work requests. Terminal back to
    # ordinary work still becomes a request (handoff 7.1), for every terminal source.
    def test_manager_generic_update_refuses_terminal_to_non_work_targets(self):
        project, manager = self._intent_fixture("Terminal generic")

        def make(source, title):
            if source == "completed":
                return self._completed_task(project, manager, title)
            task = self.service.create_task(
                self.owner, {"project_id": project["id"], "title": title, "owner_user_id": manager["id"]}
            )
            return self.service.update_task(
                self.owner, task["id"],
                {"status": source, "reason": "Owner closes it", "expected_revision": task["revision"]},
            )

        for source in ("completed", "cancelled", "abandoned"):
            owner_message = (
                f"A {source} task is not edited back into work; use the dedicated reopen task action "
                "(reason and revised due date) so the reopening is recorded."
            )
            for target in ("cancelled", "abandoned", "changes_requested"):
                if target == source:
                    continue
                with self.subTest(source=source, target=target):
                    task = make(source, f"{source} to {target}")
                    self.assertEqual(task["status"], source)
                    events_before = len(self.service.task_events(self.owner, task["id"]))
                    for actor in (manager, self.owner):
                        with self.assertRaises(ValueError) as caught:
                            self.service.update_task(
                                actor, task["id"],
                                {"status": target, "reason": "Asks", "expected_revision": task["revision"]},
                            )
                        self.assertEqual(str(caught.exception), owner_message)
                    current = self.service.get_task(self.owner, task["id"])
                    self.assertEqual((current["status"], current["revision"]), (source, task["revision"]))
                    self.assertEqual(len(self.service.task_events(self.owner, task["id"])), events_before)
                    self.assertEqual(self.service.list_owner_action_requests(self.owner, status=None), [])

        for source in ("completed", "cancelled", "abandoned"):
            with self.subTest(source=source, target="in_progress"):
                task = make(source, f"{source} back to work")
                request = self.service.update_task(
                    manager, task["id"],
                    {"status": "in_progress", "reason": "More work", "expected_revision": task["revision"]},
                )["request"]
                self.assertEqual(json.loads(request["payload_json"])["from_status"], source)
                self.service.reopen_task(self.owner, task["id"], "Owner reopens", "2027-08-01")
                self._assert_resolved(request, task_id=task["id"])

if __name__ == "__main__":
    unittest.main()
