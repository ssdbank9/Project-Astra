"""Aly's Q1 decision: approver designation grants acceptance recommendations only."""
import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from astra import service as service_module
from astra.db import connect, transaction as database_transaction
from astra.service import AstraService, Conflict, Forbidden


class ApproverPermissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "approvers.sqlite3"
        self.db = connect(self.db_path)
        self.addCleanup(self.db.close)
        self.service = s = AstraService(self.db)
        self.owner = s.create_initial_owner("owner@example.org", "Owner", "owner password safe")
        self.project = s.create_project(self.owner, "Approver scope")
        self.people = {}
        for name, global_role, project_role in (
            ("chairman", "chairman", None), ("viewer", "member", "viewer"),
            ("member", "member", "member"), ("manager", "member", "manager"),
        ):
            person = s.create_user(self.owner, f"{name}@example.org", name.title(), "test password safe", global_role)
            self.people[name] = person
            if project_role:
                s.grant_project_access(self.owner, self.project["id"], person["id"], project_role)

    def task(self, title="Work"):
        return self.service.create_task(self.owner, {
            "project_id": self.project["id"], "title": title,
            "owner_user_id": self.people["member"]["id"],
        })

    def designate(self, task, person):
        self.service.add_task_reviewer(self.owner, task["id"], person["id"], "approver")

    def business_state(self, task):
        s = self.service
        return (s.get_task(self.owner, task["id"]), s.list_task_submissions(self.owner, task["id"]),
                s.list_schedule_proposals(self.owner, task["id"]), s.list_owner_action_requests(self.owner))

    def test_designation_grants_only_the_acceptance_permission_flag(self):
        task = self.task()
        for name, person in self.people.items():
            self.designate(task, person)
            with self.subTest(role=name):
                permissions = self.service.task_detail(person, task["id"])["permissions"]
                self.assertTrue(permissions["can_request_accept_submission"])
                self.assertEqual(permissions["can_request_protected"], name == "manager")
                self.assertEqual(permissions["can_edit_ordinary"], name == "manager")
                self.assertFalse(permissions["can_decide_protected"])
                self.assertFalse(permissions["can_manage_files"])

    def test_designated_roles_request_acceptance_once_and_owner_decides(self):
        s = self.service
        for name, person in self.people.items():
            with self.subTest(role=name):
                task = self.task(name)
                self.designate(task, person)
                submission = s.submit_task(self.owner, task["id"], "Ready")
                before = (s.get_task(self.owner, task["id"]), s.get_submission(self.owner, submission["id"]))
                first = s.accept_submission(person, submission["id"], "Recommend acceptance")["request"]
                second = s.accept_submission(person, submission["id"], "Recommend acceptance")["request"]
                self.assertEqual(first["id"], second["id"])
                self.assertEqual(first["action"], "accept_submission")
                self.assertEqual(before, (s.get_task(self.owner, task["id"]),
                                         s.get_submission(self.owner, submission["id"])))
                requested = [e for e in s.task_events(self.owner, task["id"])
                             if e["event_type"] == "protected_action_requested"]
                self.assertEqual(len(requested), 1)
                s.accept_submission(self.owner, submission["id"], "Accepted")
                self.assertEqual(s.get_task(self.owner, task["id"])["status"], "completed")
                self.assertEqual(s.get_submission(self.owner, submission["id"])["decided_by"], self.owner["id"])
                self.assertEqual(s._owner_action_request(self.owner, first["id"])["status"], "approved")

    def test_designation_does_not_grant_other_protected_actions(self):
        s = self.service
        for name in ("chairman", "viewer", "member"):
            person = self.people[name]
            opened, submitted, closed = self.task("Open"), self.task("Submitted"), self.task("Closed")
            for task in (opened, submitted, closed):
                self.designate(task, person)
            proposal = s.propose_schedule(self.owner, opened["id"], "2027-03-01", "2027-03-04", "Replan")
            submission = s.submit_task(self.owner, submitted["id"], "Ready")
            s.update_task(self.owner, closed["id"], {
                "status": "cancelled", "reason": "Closed", "expected_revision": closed["revision"],
            })
            attempts = [
                ("set_on_hold", opened, lambda: s.set_on_hold(person, opened["id"], "Wait", "2027-03-04")),
                ("reopen_task", closed, lambda: s.reopen_task(person, closed["id"], "Resume", "2027-04-01")),
                ("request_changes", submitted, lambda: s.request_changes(person, submission["id"], "Revise")),
                ("approve_schedule_proposal", opened, lambda: s.approve_schedule_proposal(person, proposal["id"], "Yes")),
                ("reject_schedule_proposal", opened, lambda: s.reject_schedule_proposal(person, proposal["id"], "No")),
            ]
            for action, task, attempt in attempts:
                with self.subTest(role=name, action=action):
                    before = self.business_state(task)
                    events_before = len(s.task_events(self.owner, task["id"]))
                    with self.assertRaises(Forbidden):
                        attempt()
                    self.assertEqual(before, self.business_state(task))
                    events = s.task_events(self.owner, task["id"])
                    self.assertEqual(len(events), events_before + 1)
                    self.assertEqual(events[-1]["event_type"], "protected_action_blocked")
                    self.assertEqual(json.loads(events[-1]["after_json"])["action"], action)

    def test_manager_powers_do_not_depend_on_approver_designation(self):
        s, manager = self.service, self.people["manager"]
        opened, submitted, closed = self.task("Open"), self.task("Submitted"), self.task("Closed")
        held = s.set_on_hold(manager, opened["id"], "Wait", "2027-03-04")
        self.assertEqual(held["status"], "on_hold")
        self.assertNotIn("request", held)
        submission = s.submit_task(self.owner, submitted["id"], "Ready")
        self.assertEqual(s.request_changes(manager, submission["id"], "Revise")["request"]["action"], "request_changes")
        s.update_task(self.owner, closed["id"], {
            "status": "cancelled", "reason": "Closed", "expected_revision": closed["revision"],
        })
        self.assertEqual(s.reopen_task(manager, closed["id"], "Resume", "2027-04-01")["request"]["action"], "reopen_task")

    def test_reviewer_without_designation_cannot_request_acceptance(self):
        s, task = self.service, self.task()
        submission = s.submit_task(self.owner, task["id"], "Ready")
        for name in ("chairman", "viewer", "member"):
            person = self.people[name]
            s.add_task_reviewer(self.owner, task["id"], person["id"], "reviewer")
            with self.subTest(role=name), self.assertRaises(Forbidden):
                s.accept_submission(person, submission["id"], "Recommend")
        self.assertEqual(s.list_owner_action_requests(self.owner), [])

    def test_acceptance_permission_is_revalidated_after_concurrent_access_change(self):
        s = self.service
        cases = ("remove_designation", "revoke_access", "deactivate", "manager_downgrade")
        for change in cases:
            with self.subTest(change=change):
                person = s.create_user(self.owner, f"race-{change}@example.org", change, "race test password")
                s.grant_project_access(self.owner, self.project["id"], person["id"],
                                       "manager" if change == "manager_downgrade" else "viewer")
                task = self.task(change)
                if change != "manager_downgrade":
                    self.designate(task, person)
                submission = s.submit_task(self.owner, task["id"], "Ready")
                other = connect(self.db_path)
                self.addCleanup(other.close)
                other_service = AstraService(other)
                changed, after_change = [], []

                @contextmanager
                def change_before_write(connection):
                    if connection is self.db and not changed:
                        changed.append(True)
                        if change == "remove_designation":
                            other_service.remove_task_reviewer(self.owner, task["id"], person["id"], "approver")
                        elif change == "revoke_access":
                            other_service.revoke_project_access(self.owner, task["project_id"], person["id"])
                        elif change == "deactivate":
                            other_service.set_user_active(self.owner, person["id"], False)
                        else:
                            other_service.grant_project_access(self.owner, task["project_id"], person["id"], "viewer")
                        after_change.append(tuple(self.db.iterdump()))
                    with database_transaction(connection):
                        yield

                with patch.object(service_module, "transaction", change_before_write):
                    with self.assertRaises(Forbidden):
                        s.accept_submission(person, submission["id"], "Recommend")
                self.assertEqual(changed, [True])
                self.assertEqual(tuple(self.db.iterdump()), after_change[0])
    def test_revoked_or_inactive_designation_is_refused_before_requesting(self):
        s = self.service
        person = self.people["viewer"]
        task = self.task()
        self.designate(task, person)
        submission = s.submit_task(self.owner, task["id"], "Ready")
        s.set_user_active(self.owner, person["id"], False)
        with self.assertRaises(Forbidden):
            s.accept_submission(person, submission["id"], "Recommend")
        self.assertEqual(s.list_owner_action_requests(self.owner), [])

    def test_legacy_pending_submission_on_a_nonsubmitted_task_cannot_be_recommended(self):
        s, person = self.service, self.people["viewer"]
        task = self.task()
        self.designate(task, person)
        submission = s.submit_task(self.owner, task["id"], "Ready")
        # Historical inconsistent data: a pending version is still linked to ordinary work.
        self.db.execute("UPDATE tasks SET status='draft', revision=revision+1 WHERE id=?", (task["id"],))
        before = tuple(self.db.iterdump())
        with self.assertRaisesRegex(Conflict, "no longer pending"):
            s.accept_submission(person, submission["id"], "Recommend")
        self.assertEqual(tuple(self.db.iterdump()), before)
