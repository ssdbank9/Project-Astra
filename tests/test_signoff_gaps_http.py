"""HTTP-level tests for gaps found in an independent review of the sign-off work.

Every test starts a real AstraServer on 127.0.0.1 (port 0) and talks to it over
http.client with a real session cookie and CSRF token. Each one pins a guard that must
fail the test when the guard is removed:

* CS93C6  final results filtered by entity (JSON list and CSV export)
* GTEYTG  only the primary owner grants or revokes a secondary owner
* XDA2JR  the project calendar is owner-only
* 8B9NBH  every template route is owner-only
* 9R7A87  setting a parent task needs project management rights
* XX9RFM  closing a project / changing its dates tells the other owner, not the actor
* X07XV4  the 409 for a locked task names the holder and gives the expiry
* 3FQEKB  the Chairman may bulk Assign and nothing else in bulk
* HS3JRY  a manager may not change a project's target date (the start date is fine)
"""
import csv
import http.client
import io
import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timezone

from astra.web import AstraServer

OWNER_EMAIL, OWNER_PASSWORD = "owner@example.org", "correct horse battery"
PASSWORD = "a long test password"
ROLES = ("manager", "member", "viewer", "chairman")


class Session:
    """One signed-in user: the cookie, the CSRF token and the user record."""

    def __init__(self, cookie, csrf, user):
        self.cookie, self.csrf, self.user = cookie, csrf, user

    @property
    def id(self):
        return self.user["id"]


class HttpFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("ASTRA_HOME")
        os.environ["ASTRA_HOME"] = self.temp.name
        self.server = None
        self.thread = None
        # addCleanup also runs when a later setUp step raises, so nothing leaks.
        self.addCleanup(self._cleanup)
        self.server = AstraServer(("127.0.0.1", 0))
        self.service = self.server.service
        self.service.create_initial_owner(OWNER_EMAIL, "Owner", OWNER_PASSWORD)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]
        self.owner = self.login(OWNER_EMAIL, OWNER_PASSWORD)

    def _cleanup(self):
        try:
            if self.thread is not None:
                self.server.shutdown()
            if self.server is not None:
                self.server.server_close()
            if self.thread is not None:
                self.thread.join(timeout=5)
                self.assertFalse(self.thread.is_alive(), "server thread did not exit")
        finally:
            if self.old_home is None:
                os.environ.pop("ASTRA_HOME", None)
            else:
                os.environ["ASTRA_HOME"] = self.old_home
            self.temp.cleanup()

    # --- HTTP plumbing -------------------------------------------------------------------

    def raw(self, method, path, body=None, session=None, csrf=True):
        headers = {"Content-Type": "application/json"}
        if session is not None:
            headers["Cookie"] = session.cookie
            if csrf:
                headers["X-CSRF-Token"] = session.csrf
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            data = json.dumps(body).encode() if body is not None else None
            connection.request(method, path, data, headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def call(self, method, path, body=None, session=None, csrf=True):
        status, headers, raw = self.raw(method, path, body, session, csrf)
        if headers.get("Content-Type", "").startswith("application/json"):
            return status, json.loads(raw)
        return status, None

    def login(self, email, password):
        status, headers, raw = self.raw("POST", "/api/login", {"email": email, "password": password})
        self.assertEqual(status, 200, raw)
        payload = json.loads(raw)
        return Session(headers["Set-Cookie"].split(";", 1)[0], payload["csrf"], payload["user"])

    def owner_actor(self):
        return self.service.get_user(self.owner.id)

    def make_user(self, label, role="member"):
        """Create an account with the service and sign it in over HTTP. The forced
        first-login password change is cleared: these tests are about permissions."""
        user = self.service.create_user(self.owner_actor(), f"{label}@example.org", label.title(), PASSWORD, role)
        self.service.db.execute("UPDATE users SET must_change_password=0 WHERE id=?", (user["id"],))
        self.service.db.commit()
        return self.login(f"{label}@example.org", PASSWORD)

    def make_project(self, name="Alpha", members=()):
        status, body = self.call("POST", "/api/projects", {"name": name}, self.owner)
        self.assertEqual(status, 201, body)
        pid = body["project"]["id"]
        for session, role in members:
            status, body = self.call("POST", "/api/project-access",
                                     {"project_id": pid, "user_id": session.id, "role": role}, self.owner)
            self.assertEqual(status, 200, body)
        return pid

    def make_task(self, pid, title="Task", **extra):
        status, body = self.call("POST", "/api/tasks", {"project_id": pid, "title": title, **extra}, self.owner)
        self.assertEqual(status, 201, body)
        return body["task"]

    def get_task(self, tid):
        status, body = self.call("GET", f"/api/tasks/{tid}", session=self.owner)
        self.assertEqual(status, 200, body)
        return body["task"]

    def role_cast(self):
        """A project plus one signed-in user per role the permission tests look at."""
        manager, member = self.make_user("manager"), self.make_user("member")
        viewer, chairman = self.make_user("viewer"), self.make_user("chairman", "chairman")
        pid = self.make_project("Cast", [(manager, "manager"), (member, "member"), (viewer, "viewer")])
        return pid, {"manager": manager, "member": member, "viewer": viewer, "chairman": chairman}


class FinalResultsEntityFilterTests(HttpFixture):
    """CS93C6: the entity filter narrows the JSON list and the CSV export."""

    def _finalise(self, pid, title):
        task = self.make_task(pid, title)
        status, sub = self.call("POST", f"/api/tasks/{task['id']}/submit", {"note": "ready"}, self.owner)
        self.assertEqual(status, 201, sub)
        sid = sub["submission"]["id"]
        status, body = self.call("POST", f"/api/submissions/{sid}/accept", {"decision_note": "ok"}, self.owner)
        self.assertEqual(status, 200, body)
        status, body = self.call("POST", "/api/final-results", {
            "task_id": task["id"], "source_type": "submission", "source_id": sid}, self.owner)
        self.assertEqual(status, 201, body)

    def test_final_results_filtered_by_entity_over_http_and_in_the_csv(self):
        actor = self.owner_actor()
        east = self.service.create_entity(actor, "East Foundation")
        west = self.service.create_entity(actor, "West Foundation")
        east_pid, west_pid = self.make_project("East project"), self.make_project("West project")
        none_pid = self.make_project("Unattached project")
        for pid, entity in ((east_pid, east), (west_pid, west)):
            status, body = self.call("POST", f"/api/projects/{pid}/entities", {"entity_ids": [entity["id"]]},
                                     self.owner)
            self.assertEqual(status, 200, body)
        self._finalise(east_pid, "East memo")
        self._finalise(west_pid, "West memo")
        self._finalise(none_pid, "Loose memo")

        def listed(query):
            status, body = self.call("GET", "/api/final-results" + query, session=self.owner)
            self.assertEqual(status, 200, body)
            return sorted(r["task_title"] for r in body["results"])

        self.assertEqual(listed(""), ["East memo", "Loose memo", "West memo"])
        self.assertEqual(listed(f"?entity_id={east['id']}"), ["East memo"])
        self.assertEqual(listed(f"?entity_id={west['id']}"), ["West memo"])
        self.assertEqual(listed("?entity_id=no-such-entity"), [])

        status, headers, raw = self.raw("GET", f"/api/final-results?format=csv&entity_id={east['id']}",
                                        session=self.owner)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/csv; charset=utf-8")
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
        self.assertEqual([(r["task_title"], r["entities"]) for r in rows], [("East memo", "East Foundation")])
        status, _, raw = self.raw("GET", "/api/final-results?format=csv", session=self.owner)
        self.assertEqual(sorted(r["task_title"] for r in csv.DictReader(io.StringIO(raw.decode("utf-8")))),
                         ["East memo", "Loose memo", "West memo"])
        self.assertIn(f"__entity={east['id']}", self.raw(
            "GET", f"/api/final-results?format=csv&entity_id={east['id']}", session=self.owner)[1]["Content-Disposition"])


class SecondaryOwnerRouteTests(HttpFixture):
    """GTEYTG: granting and revoking owner access is the primary owner's alone."""

    def test_a_plain_member_cannot_grant_or_revoke_a_secondary_owner(self):
        member = self.make_user("plain")
        target = self.make_user("target")
        second = self.service.create_user(self.owner_actor(), "second@example.org", "Second", PASSWORD, "member")
        self.service.db.execute("UPDATE users SET must_change_password=0 WHERE id=?", (second["id"],))
        self.service.db.commit()
        self.service.grant_secondary_owner(self.owner_actor(), second["id"], "Cover for the primary")
        self.assertEqual(self.service.get_user(second["id"])["global_role"], "owner")

        status, body = self.call("POST", f"/api/users/{target.id}/secondary-owner", {"reason": "Please"}, member)
        self.assertEqual(status, 403, body)
        self.assertEqual(self.service.get_user(target.id)["global_role"], "member")

        status, body = self.call("DELETE", f"/api/users/{second['id']}/secondary-owner", {"reason": "Please"}, member)
        self.assertEqual(status, 403, body)
        self.assertEqual(self.service.get_user(second["id"])["global_role"], "owner")
        self.assertTrue(self.service.get_user(second["id"])["active"])

        # The refusals are not silent successes: the attempt is audited, nothing was granted.
        events = [r["event_type"] for r in self.service.db.execute(
            "SELECT event_type FROM user_events WHERE event_type IN ('secondary_owner_granted','secondary_owner_revoked')"
        ).fetchall()]
        self.assertEqual(events, ["secondary_owner_granted"])

        # The primary owner can still do both, so the 403s above are about the caller.
        status, body = self.call("POST", f"/api/users/{target.id}/secondary-owner", {"reason": "Cover"}, self.owner)
        self.assertEqual((status, body["user"]["global_role"]), (201, "owner"))
        status, body = self.call("DELETE", f"/api/users/{target.id}/secondary-owner", {"reason": "Done"}, self.owner)
        self.assertEqual((status, body["user"]["global_role"]), (200, "member"))


class ProjectCalendarRouteTests(HttpFixture):
    """XDA2JR: only an owner edits a project's working days and holidays."""

    def _calendar(self, pid):
        status, body = self.call("GET", f"/api/projects/{pid}/calendar", session=self.owner)
        self.assertEqual(status, 200, body)
        return body["calendar"]

    def test_only_an_owner_edits_the_project_calendar(self):
        pid, cast = self.role_cast()
        status, body = self.call("POST", f"/api/projects/{pid}/holidays", {"date": "2026-12-25", "label": "Keep"},
                                 self.owner)
        self.assertEqual(status, 200, body)
        before = self._calendar(pid)
        self.assertEqual(before["holidays"], [{"holiday_date": "2026-12-25", "label": "Keep"}])
        routes = (
            ("POST", f"/api/projects/{pid}/working-days", {"days": "01234"}),
            ("POST", f"/api/projects/{pid}/holidays", {"date": "2026-12-31", "label": "Intruder"}),
            ("DELETE", "/api/project-holidays", {"project_id": pid, "date": "2026-12-25"}),
        )
        for role, session in cast.items():
            for method, path, body in routes:
                with self.subTest(role=role, route=f"{method} {path}"):
                    status, payload = self.call(method, path, body, session)
                    self.assertEqual(status, 403, payload)
                    self.assertEqual(self._calendar(pid), before)
        # The owner is not blocked by the same requests.
        status, body = self.call("POST", f"/api/projects/{pid}/working-days", {"days": "01234"}, self.owner)
        self.assertEqual((status, body["working_days"]), (200, "01234"))
        status, body = self.call("POST", f"/api/projects/{pid}/holidays", {"date": "2026-12-31", "label": "Ok"},
                                 self.owner)
        self.assertEqual(status, 200, body)
        status, body = self.call("DELETE", "/api/project-holidays", {"project_id": pid, "date": "2026-12-25"},
                                 self.owner)
        self.assertEqual(status, 200, body)
        after = self._calendar(pid)
        self.assertEqual(after["working_days"], "01234")
        self.assertEqual(after["holidays"], [{"holiday_date": "2026-12-31", "label": "Ok"}])


class TemplateRouteTests(HttpFixture):
    """8B9NBH: saving, reading, applying and deleting templates is owner-only."""

    def test_only_an_owner_uses_any_template_route(self):
        pid, cast = self.role_cast()
        task = self.make_task(pid, "Template source")
        status, body = self.call("POST", "/api/templates/from-project",
                                 {"project_id": pid, "name": "Project shape"}, self.owner)
        self.assertEqual(status, 201, body)
        project_template = body["template"]["id"]
        status, body = self.call("POST", "/api/templates/from-task",
                                 {"task_id": task["id"], "name": "Task shape"}, self.owner)
        self.assertEqual(status, 201, body)
        task_template = body["template"]["id"]

        def snapshot():
            status, body = self.call("GET", "/api/templates", session=self.owner)
            self.assertEqual(status, 200, body)
            status, projects = self.call("GET", "/api/projects", session=self.owner)
            status, tasks = self.call("GET", "/api/tasks", session=self.owner)
            return (sorted(t["name"] for t in body["templates"]),
                    sorted(p["name"] for p in projects["projects"]), len(tasks["tasks"]))

        before = snapshot()
        self.assertEqual(before[0], ["Project shape", "Task shape"])
        routes = (
            ("save project template", "POST", "/api/templates/from-project",
             {"project_id": pid, "name": "Intruder project template"}),
            ("save task template", "POST", "/api/templates/from-task",
             {"task_id": task["id"], "name": "Intruder task template"}),
            ("apply: create project", "POST", f"/api/templates/{project_template}/create-project",
             {"name": "Intruder project"}),
            ("apply: create task", "POST", f"/api/templates/{task_template}/create-task", {"project_id": pid}),
            ("delete project template", "DELETE", "/api/templates", {"template_id": project_template}),
            ("delete task template", "DELETE", "/api/templates", {"template_id": task_template}),
            ("list templates", "GET", "/api/templates", None),
            ("read template", "GET", f"/api/templates/{project_template}", None),
        )
        for role, session in cast.items():
            for label, method, path, body in routes:
                with self.subTest(role=role, route=label):
                    status, payload = self.call(method, path, body, session)
                    self.assertEqual(status, 403, payload)
                    self.assertEqual(snapshot(), before)
        # The owner is not blocked by the same routes.
        status, body = self.call("POST", f"/api/templates/{project_template}/create-project",
                                 {"name": "Owner project"}, self.owner)
        self.assertEqual(status, 201, body)
        status, body = self.call("POST", f"/api/templates/{task_template}/create-task", {"project_id": pid},
                                 self.owner)
        self.assertEqual(status, 201, body)
        status, body = self.call("DELETE", "/api/templates", {"template_id": task_template}, self.owner)
        self.assertEqual(status, 200, body)


class SetParentRouteTests(HttpFixture):
    """9R7A87: only a manager (or an owner) of the project sets a task's parent."""

    def test_a_project_member_who_is_not_a_manager_cannot_set_a_parent(self):
        pid, cast = self.role_cast()
        parent = self.make_task(pid, "Parent")
        child = self.make_task(pid, "Child")
        for role in ("member", "viewer", "chairman"):
            with self.subTest(role=role):
                before = self.get_task(child["id"])
                status, body = self.call("POST", f"/api/tasks/{child['id']}/parent",
                                         {"parent_task_id": parent["id"]}, cast[role])
                self.assertEqual(status, 403, body)
                after = self.get_task(child["id"])
                self.assertIsNone(after["parent_task_id"])
                self.assertEqual(after["revision"], before["revision"])
        # A manager can; the same request succeeds and moves the task under its parent.
        status, body = self.call("POST", f"/api/tasks/{child['id']}/parent",
                                 {"parent_task_id": parent["id"]}, cast["manager"])
        self.assertEqual((status, body["task"]["parent_task_id"]), (200, parent["id"]))
        # So can the owner, for a second task.
        other = self.make_task(pid, "Other child")
        status, body = self.call("POST", f"/api/tasks/{other['id']}/parent",
                                 {"parent_task_id": parent["id"]}, self.owner)
        self.assertEqual((status, body["task"]["parent_task_id"]), (200, parent["id"]))
        # And a refused member cannot undo a manager's placement either.
        status, body = self.call("POST", f"/api/tasks/{child['id']}/parent", {"parent_task_id": None}, cast["member"])
        self.assertEqual(status, 403, body)
        self.assertEqual(self.get_task(child["id"])["parent_task_id"], parent["id"])


class ProjectNoticeToOtherOwnerTests(HttpFixture):
    """XX9RFM: closing a project and changing its dates reach the other owner, not the actor."""

    def _notices(self, session, kind):
        status, body = self.call("GET", "/api/notifications", session=session)
        self.assertEqual(status, 200, body)
        return [n for n in body["notifications"] if n["kind"] == kind]

    def test_close_and_date_change_notify_the_second_owner_and_not_the_actor(self):
        second_user = self.service.create_user(self.owner_actor(), "second@example.org", "Second Owner", PASSWORD)
        self.service.db.execute("UPDATE users SET must_change_password=0 WHERE id=?", (second_user["id"],))
        self.service.db.commit()
        self.service.grant_secondary_owner(self.owner_actor(), second_user["id"], "Second owner")
        second = self.login("second@example.org", PASSWORD)
        self.assertEqual(second.user["global_role"], "owner")
        pid = self.make_project("Notice project")

        status, body = self.call("POST", f"/api/projects/{pid}/schedule", {
            "start_date": "2026-02-01", "target_date": "2026-05-01", "reason": "Kickoff"}, self.owner)
        self.assertEqual(status, 200, body)
        status, body = self.call("POST", f"/api/projects/{pid}/close", {"note": "Finished"}, self.owner)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["project"]["status"], "closed")

        dates = self._notices(second, "project_schedule_changed")
        closed = self._notices(second, "project_closed")
        self.assertEqual(len(dates), 1, dates)
        self.assertEqual(len(closed), 1, closed)
        self.assertIn("Notice project", dates[0]["summary"])
        self.assertIn("2026-05-01", dates[0]["summary"])
        self.assertIn("by Owner", dates[0]["summary"])
        self.assertIn("Notice project", closed[0]["summary"])
        self.assertIn("by Owner", closed[0]["summary"])
        for kind in ("project_schedule_changed", "project_closed"):
            self.assertEqual(self._notices(self.owner, kind), [], f"the acting owner is told about {kind}")


class LockedTaskConflictTests(HttpFixture):
    """X07XV4: the 409 for a task someone else is changing names them and says until when."""

    def test_the_conflict_names_the_holder_and_carries_the_expiry(self):
        manager = self.make_user("holder", "member")
        pid = self.make_project("Locks", [(manager, "manager")])
        task = self.make_task(pid, "Contended")
        status, got = self.call("POST", f"/api/tasks/{task['id']}/lock", {"kind": "edit"}, manager)
        self.assertEqual(status, 200, got)
        expires = got["lock"]["expires_at"]

        def check(status, refused):
            self.assertEqual(status, 409, refused)
            lock = refused["lock"]
            self.assertEqual((lock["holder_name"], lock["kind"]), ("Holder", "edit"))
            self.assertEqual(lock["holder_user_id"], manager.id)
            self.assertEqual(lock["expires_at"], expires)
            stamp = datetime.fromisoformat(lock["expires_at"])
            self.assertGreater(stamp, datetime.now(timezone.utc))
            self.assertIn("Holder", refused["error"])
            self.assertIn(expires[11:19], refused["error"])

        # A write by someone else is refused with the lease details...
        status, refused = self.call("POST", f"/api/tasks/{task['id']}", {
            "title": "Owner rename", "expected_revision": task["revision"]}, self.owner)
        check(status, refused)
        self.assertEqual(self.get_task(task["id"])["title"], "Contended")
        # ...and so is a second person trying to take the lock.
        status, refused = self.call("POST", f"/api/tasks/{task['id']}/lock", {"kind": "drag"}, self.owner)
        check(status, refused)


class ChairmanBulkRouteTests(HttpFixture):
    """3FQEKB: the Chairman's bulk rights are Assign and nothing else."""

    def test_the_chairman_may_bulk_assign_but_not_change_status_or_dates(self):
        worker = self.make_user("worker")
        chairman = self.make_user("boss", "chairman")
        pid = self.make_project("Bulk", [(worker, "member")])
        tasks = [self.make_task(pid, f"Card {n}", due_date="2026-11-10") for n in (1, 2)]
        ids = [t["id"] for t in tasks]
        base = f"/api/projects/{pid}/bulk"

        # Preview then apply an assignment as the Chairman.
        status, preview = self.call("POST", f"{base}/preview",
                                    {"task_ids": ids, "action": "assignee", "value": worker.id}, chairman)
        self.assertEqual(status, 200, preview)
        self.assertEqual(preview["preview"]["counts"], {"ok": 2, "blocked": 0})
        revisions = {i["id"]: i["revision"] for i in preview["preview"]["ok"]}
        status, done = self.call("POST", f"{base}/apply", {
            "task_ids": ids, "action": "assignee", "value": worker.id, "expected_revisions": revisions}, chairman)
        self.assertEqual(status, 200, done)
        self.assertEqual(len(done["tasks"]), 2)
        for tid in ids:
            self.assertEqual(self.get_task(tid)["owner_user_id"], worker.id)

        # Every other bulk action is refused, at preview and at apply, and changes nothing.
        before = {tid: self.get_task(tid) for tid in ids}
        attempts = (
            ("status", "ready"),
            ("due_shift", 3),
        )
        for action, value in attempts:
            for step in ("preview", "apply"):
                with self.subTest(action=action, step=step):
                    body = {"task_ids": ids, "action": action, "value": value,
                            "expected_revisions": {t["id"]: t["revision"] for t in before.values()}}
                    status, refused = self.call("POST", f"{base}/{step}", body, chairman)
                    self.assertEqual(status, 403, refused)
                    for tid in ids:
                        self.assertEqual(self.get_task(tid), before[tid])
        # The same status change is open to the owner, so the refusal above is about the role.
        status, preview = self.call("POST", f"{base}/preview", {"task_ids": ids, "action": "status", "value": "ready"},
                                    self.owner)
        self.assertEqual((status, preview["preview"]["counts"]["ok"]), (200, 2))


class ManagerProjectDatesTests(HttpFixture):
    """HS3JRY (5WZ4A8 B1): changing the target date is owner-only; the start date is not."""

    def _dates(self, pid):
        status, body = self.call("GET", "/api/projects", session=self.owner)
        project = next(p for p in body["projects"] if p["id"] == pid)
        return project["start_date"], project["target_date"]

    def test_a_manager_cannot_change_the_target_date_but_can_change_the_start_date(self):
        manager = self.make_user("pm")
        pid = self.make_project("Dates", [(manager, "manager")])
        status, body = self.call("POST", f"/api/projects/{pid}/schedule", {
            "start_date": "2026-02-01", "target_date": "2026-05-01", "reason": "Plan"}, self.owner)
        self.assertEqual(status, 200, body)

        refused = (
            ("move the target", {"start_date": "2026-02-01", "target_date": "2026-06-01"}),
            ("bring the target forward", {"start_date": "2026-02-01", "target_date": "2026-04-01"}),
            ("clear the target", {"start_date": "2026-02-01", "target_date": None}),
            ("start and target", {"start_date": "2026-02-15", "target_date": "2026-07-01"}),
        )
        for label, dates in refused:
            with self.subTest(label):
                status, payload = self.call("POST", f"/api/projects/{pid}/schedule",
                                            {**dates, "reason": "Manager edit"}, manager)
                self.assertEqual(status, 403, payload)
                self.assertEqual(self._dates(pid), ("2026-02-01", "2026-05-01"))
        status, events = self.call("GET", f"/api/projects/{pid}/events", session=self.owner)
        self.assertEqual([e["event_type"] for e in events["events"] if e["event_type"] == "project_schedule_changed"],
                         ["project_schedule_changed"])  # only the owner's own change

        # A start-only change (target untouched) is still allowed to the manager.
        status, payload = self.call("POST", f"/api/projects/{pid}/schedule", {
            "start_date": "2026-02-15", "target_date": "2026-05-01", "reason": "Kickoff slipped"}, manager)
        self.assertEqual(status, 200, payload)
        self.assertEqual(self._dates(pid), ("2026-02-15", "2026-05-01"))
        # The owner can change the target, so the refusals were about the role.
        status, payload = self.call("POST", f"/api/projects/{pid}/schedule", {
            "start_date": "2026-02-15", "target_date": "2026-06-01", "reason": "Agreed"}, self.owner)
        self.assertEqual(status, 200, payload)
        self.assertEqual(self._dates(pid), ("2026-02-15", "2026-06-01"))


if __name__ == "__main__":
    unittest.main()
