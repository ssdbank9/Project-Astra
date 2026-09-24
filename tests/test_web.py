import csv
import http.client
import io
import inspect
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from importlib.resources import files
from pathlib import Path

from astra.web import AstraHandler, AstraServer

STATIC = Path(str(files("astra").joinpath("static")))
REPO = Path(__file__).resolve().parents[1]
HEX = r"#[0-9A-Fa-f]{6}"


def relative_luminance(colour):
    channels = [int(colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


class AstraWebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("ASTRA_HOME")
        os.environ["ASTRA_HOME"] = self.temp.name
        self.server = AstraServer(("127.0.0.1", 0))
        self.server.service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        if self.old_home is None:
            os.environ.pop("ASTRA_HOME", None)
        else:
            os.environ["ASTRA_HOME"] = self.old_home
        self.temp.cleanup()

    def request(self, method, path, body=None, *, cookie=None, csrf=None):
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        if csrf:
            headers["X-CSRF-Token"] = csrf
        self.connection.request(method, path, json.dumps(body).encode() if body is not None else None, headers)
        response = self.connection.getresponse()
        content_type = response.getheader("Content-Type", "")
        payload = json.loads(response.read()) if content_type.startswith("application/json") else None
        return response, payload

    def test_authenticated_project_task_gantt_data_workflow(self):
        response, login = self.request("POST", "/api/login", {"email": "owner@example.org", "password": "correct horse battery"})
        self.assertEqual(response.status, 200)
        cookie = response.getheader("Set-Cookie").split(";", 1)[0]
        csrf = login["csrf"]
        response, project_payload = self.request("POST", "/api/projects", {"name": "AIOU"}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        response, task_payload = self.request("POST", "/api/tasks", {"project_id": project_payload["project"]["id"], "title": "Approve implementation schedule", "start_date": "2026-09-14", "due_date": "2026-09-21", "criticality": "critical"}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        self.assertEqual(task_payload["task"]["project_name"], "AIOU")
        response, tasks = self.request("GET", "/api/tasks", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(len(tasks["tasks"]), 1)

    def test_state_change_rejects_missing_csrf(self):
        response, _ = self.request("POST", "/api/login", {"email": "owner@example.org", "password": "correct horse battery"})
        cookie = response.getheader("Set-Cookie").split(";", 1)[0]
        response, payload = self.request("POST", "/api/projects", {"name": "Forbidden"}, cookie=cookie)
        self.assertEqual(response.status, 403)
        self.assertIn("request token", payload["error"])

    def test_static_shell_loads_without_authentication(self):
        self.connection.request("GET", "/")
        response = self.connection.getresponse()
        body = response.read().decode()
        self.assertEqual(response.status, 200)
        self.assertIn("Portfolio Gantt", body)

    def test_dependency_api_reports_blocked_task_and_rejects_cycle(self):
        response, login = self.request("POST", "/api/login", {
            "email": "owner@example.org", "password": "correct horse battery",
        })
        cookie = response.getheader("Set-Cookie").split(";", 1)[0]
        csrf = login["csrf"]
        _, project_payload = self.request(
            "POST", "/api/projects", {"name": "Dependency API"}, cookie=cookie, csrf=csrf
        )
        project_id = project_payload["project"]["id"]
        _, first_payload = self.request(
            "POST", "/api/tasks", {"project_id": project_id, "title": "First"}, cookie=cookie, csrf=csrf
        )
        _, second_payload = self.request(
            "POST", "/api/tasks", {"project_id": project_id, "title": "Second"}, cookie=cookie, csrf=csrf
        )
        first_id, second_id = first_payload["task"]["id"], second_payload["task"]["id"]
        response, _ = self.request("POST", "/api/task-dependencies", {
            "predecessor_task_id": first_id, "successor_task_id": second_id,
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        response, tasks = self.request("GET", "/api/tasks", cookie=cookie)
        self.assertEqual(response.status, 200)
        second = next(task for task in tasks["tasks"] if task["id"] == second_id)
        self.assertTrue(second["is_blocked"])
        response, error = self.request("POST", "/api/task-dependencies", {
            "predecessor_task_id": second_id, "successor_task_id": first_id,
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 400)
        self.assertIn("cycle", error["error"])


    def _owner_session(self):
        response, login = self.request("POST", "/api/login", {
            "email": "owner@example.org", "password": "correct horse battery",
        })
        cookie = response.getheader("Set-Cookie").split(";", 1)[0]
        return cookie, login["csrf"]

    def test_task_detail_endpoint_returns_task_and_dependencies(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Detail"}, cookie=cookie, csrf=csrf)
        project_id = project["project"]["id"]
        _, first = self.request("POST", "/api/tasks", {"project_id": project_id, "title": "First"}, cookie=cookie, csrf=csrf)
        _, second = self.request("POST", "/api/tasks", {
            "project_id": project_id, "title": "Second", "predecessor_task_id": first["task"]["id"],
        }, cookie=cookie, csrf=csrf)
        response, detail = self.request("GET", f"/api/tasks/{second['task']['id']}", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(detail["task"]["title"], "Second")
        self.assertTrue(any(d["direction"] == "incoming" for d in detail["task"]["dependencies"]))

    def test_task_create_on_missing_project_returns_404_not_500(self):
        cookie, csrf = self._owner_session()
        response, payload = self.request(
            "POST", "/api/tasks", {"project_id": "no-such-project", "title": "Ghost"}, cookie=cookie, csrf=csrf
        )
        self.assertEqual(response.status, 404)
        self.assertIn("Project not found", payload["error"])

    def test_user_management_and_assignment_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Team"}, cookie=cookie, csrf=csrf)
        project_id = project["project"]["id"]
        response, created = self.request("POST", "/api/users", {
            "email": "t@example.org", "display_name": "Teammate", "password": "teammate password", "role": "member",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        member_id = created["user"]["id"]
        response, _ = self.request("POST", "/api/project-access", {
            "project_id": project_id, "user_id": member_id, "role": "member",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        _, assignable = self.request("GET", f"/api/assignable-users?project_id={project_id}", cookie=cookie)
        self.assertIn(member_id, {u["id"] for u in assignable["users"]})
        response, task = self.request("POST", "/api/tasks", {
            "project_id": project_id, "title": "Assigned", "owner_user_id": member_id,
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        self.assertEqual(task["task"]["owner_user_id"], member_id)

    def test_deactivated_user_cannot_log_in(self):
        cookie, csrf = self._owner_session()
        _, created = self.request("POST", "/api/users", {
            "email": "gone@example.org", "display_name": "Gone", "password": "gone password here", "role": "member",
        }, cookie=cookie, csrf=csrf)
        member_id = created["user"]["id"]
        response, _ = self.request("POST", f"/api/users/{member_id}/active", {"active": False}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        response, _ = self.request("POST", "/api/login", {"email": "gone@example.org", "password": "gone password here"})
        self.assertEqual(response.status, 401)

    def test_submission_and_acceptance_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Flow"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        _, task = self.request("POST", "/api/tasks", {"project_id": pid, "title": "Deliver"}, cookie=cookie, csrf=csrf)
        tid = task["task"]["id"]
        response, sub = self.request("POST", f"/api/tasks/{tid}/submit", {"note": "done"}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        sid = sub["submission"]["id"]
        response, _ = self.request("POST", f"/api/submissions/{sid}/accept", {"decision_note": "ok"}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        _, detail = self.request("GET", f"/api/tasks/{tid}", cookie=cookie)
        self.assertEqual(detail["task"]["status"], "completed")
        self.assertEqual(detail["task"]["accepted_submission_id"], sid)

    def test_manager_protected_acceptance_returns_202_and_owner_can_list_request(self):
        owner_cookie, owner_csrf = self._owner_session()
        _, project = self.request(
            "POST", "/api/projects", {"name": "Governed HTTP"}, cookie=owner_cookie, csrf=owner_csrf
        )
        project_id = project["project"]["id"]
        _, manager = self.request("POST", "/api/users", {
            "email": "http-manager@example.org", "display_name": "HTTP Manager",
            "password": "manager password safe", "role": "member",
        }, cookie=owner_cookie, csrf=owner_csrf)
        self.request("POST", "/api/project-access", {
            "project_id": project_id, "user_id": manager["user"]["id"], "role": "manager",
        }, cookie=owner_cookie, csrf=owner_csrf)
        login_response, manager_login = self.request(
            "POST", "/api/login", {"email": "http-manager@example.org", "password": "manager password safe"}
        )
        manager_cookie = login_response.getheader("Set-Cookie").split(";", 1)[0]
        manager_csrf = manager_login["csrf"]
        _, task = self.request("POST", "/api/tasks", {
            "project_id": project_id, "title": "Manager deliverable",
        }, cookie=manager_cookie, csrf=manager_csrf)
        task_id = task["task"]["id"]
        _, submission = self.request(
            "POST", f"/api/tasks/{task_id}/submit", {"note": "Ready"},
            cookie=manager_cookie, csrf=manager_csrf,
        )

        response, requested = self.request(
            "POST", f"/api/submissions/{submission['submission']['id']}/accept",
            {"decision_note": "Manager recommendation"}, cookie=manager_cookie, csrf=manager_csrf,
        )

        self.assertEqual(response.status, 202)
        self.assertEqual(requested["request"]["action"], "accept_submission")
        _, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=owner_cookie)
        self.assertEqual(detail["task"]["status"], "submitted")
        response, queue = self.request("GET", "/api/owner-action-requests", cookie=owner_cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(queue["requests"][0]["requested_by_name"], "HTTP Manager")

    # SRFCZD R6 (R5-1): a Manager's generic edit from a terminal status to another
    # terminal status is a 400 with the Owner's message, never an unapprovable request.
    def test_manager_terminal_to_terminal_update_is_400_without_a_request(self):
        owner_cookie, owner_csrf = self._owner_session()
        _, project = self.request(
            "POST", "/api/projects", {"name": "Terminal HTTP"}, cookie=owner_cookie, csrf=owner_csrf
        )
        project_id = project["project"]["id"]
        _, manager = self.request("POST", "/api/users", {
            "email": "terminal-manager@example.org", "display_name": "Terminal Manager",
            "password": "manager password safe", "role": "member",
        }, cookie=owner_cookie, csrf=owner_csrf)
        self.request("POST", "/api/project-access", {
            "project_id": project_id, "user_id": manager["user"]["id"], "role": "manager",
        }, cookie=owner_cookie, csrf=owner_csrf)
        manager_cookie, manager_csrf = self._login_as("terminal-manager@example.org", "manager password safe")
        _, task = self.request("POST", "/api/tasks", {
            "project_id": project_id, "title": "Cancelled work",
        }, cookie=owner_cookie, csrf=owner_csrf)
        task_id = task["task"]["id"]
        response, cancelled = self.request("POST", f"/api/tasks/{task_id}", {
            "status": "cancelled", "reason": "Owner cancels", "expected_revision": task["task"]["revision"],
        }, cookie=owner_cookie, csrf=owner_csrf)
        self.assertEqual(response.status, 200)

        response, error = self.request("POST", f"/api/tasks/{task_id}", {
            "status": "abandoned", "reason": "Manager asks",
            "expected_revision": cancelled["task"]["revision"],
        }, cookie=manager_cookie, csrf=manager_csrf)

        self.assertEqual(response.status, 400)
        self.assertIn("A cancelled task is not edited back into work", error["error"])
        response, queue = self.request("GET", "/api/owner-action-requests", cookie=owner_cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(queue["requests"], [])

    def _login_as(self, email, password):
        response, login = self.request("POST", "/api/login", {"email": email, "password": password})
        self.assertEqual(response.status, 200)
        return response.getheader("Set-Cookie").split(";", 1)[0], login["csrf"]

    def test_read_only_roles_protected_attempts_return_403_and_notify_owner_over_http(self):
        owner_cookie, owner_csrf = self._owner_session()
        _, project = self.request(
            "POST", "/api/projects", {"name": "Read-only HTTP"}, cookie=owner_cookie, csrf=owner_csrf
        )
        project_id = project["project"]["id"]
        _, task = self.request("POST", "/api/tasks", {
            "project_id": project_id, "title": "Owner deliverable",
        }, cookie=owner_cookie, csrf=owner_csrf)
        task_id = task["task"]["id"]
        _, submission = self.request(
            "POST", f"/api/tasks/{task_id}/submit", {"note": "Ready"}, cookie=owner_cookie, csrf=owner_csrf
        )
        submission_id = submission["submission"]["id"]
        self.request("POST", "/api/users", {
            "email": "http-chair@example.org", "display_name": "HTTP Chairman",
            "password": "chairman password safe", "role": "chairman",
        }, cookie=owner_cookie, csrf=owner_csrf)
        _, viewer = self.request("POST", "/api/users", {
            "email": "http-viewer@example.org", "display_name": "HTTP Viewer",
            "password": "viewer password safe", "role": "member",
        }, cookie=owner_cookie, csrf=owner_csrf)
        self.request("POST", "/api/project-access", {
            "project_id": project_id, "user_id": viewer["user"]["id"], "role": "viewer",
        }, cookie=owner_cookie, csrf=owner_csrf)

        for email, password in (
            ("http-chair@example.org", "chairman password safe"),
            ("http-viewer@example.org", "viewer password safe"),
        ):
            cookie, csrf = self._login_as(email, password)
            with self.subTest(actor=email):
                response, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=cookie)
                self.assertEqual(response.status, 200)
                self.assertFalse(detail["task"]["permissions"]["can_request_protected"])
                self.assertFalse(detail["task"]["permissions"]["can_decide_protected"])
                response, _ = self.request(
                    "POST", f"/api/submissions/{submission_id}/accept", {"decision_note": "approve"},
                    cookie=cookie, csrf=csrf,
                )
                self.assertEqual(response.status, 403)
                response, _ = self.request(
                    "POST", f"/api/projects/{project_id}/close", {"note": "close"}, cookie=cookie, csrf=csrf
                )
                self.assertEqual(response.status, 403)
                response, _ = self.request("GET", "/api/owner-action-requests", cookie=cookie)
                self.assertEqual(response.status, 403)

        _, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=owner_cookie)
        self.assertEqual(detail["task"]["status"], "submitted")
        _, projects = self.request("GET", "/api/projects", cookie=owner_cookie)
        self.assertEqual([p["status"] for p in projects["projects"] if p["id"] == project_id], ["active"])
        _, queue = self.request("GET", "/api/owner-action-requests", cookie=owner_cookie)
        self.assertEqual(queue["requests"], [])
        _, inbox = self.request("GET", "/api/notifications", cookie=owner_cookie)
        blocked = [n for n in inbox["notifications"] if n["kind"] == "protected_action_blocked"]
        self.assertEqual(len(blocked), 4)

    def test_every_mutation_route_delegates_to_the_service_layer(self):
        # Authorization lives in AstraService. Every POST/DELETE route branch must call a
        # service method and no route may write to the database directly. Session
        # bookkeeping (/api/login, /api/logout) is the only exception and is listed here.
        session_only = {"/api/login", "/api/logout"}
        route_pattern = re.compile(r'if path(?: == "([^"]+)"| *(?:\.startswith\("([^"]+)")?.*?endswith\("([^"]+)"\))')
        for handler in (AstraHandler.do_POST, AstraHandler.do_DELETE):
            source = inspect.getsource(handler)
            self.assertNotIn("self.db.execute", source, handler.__name__)
            branches = []
            for line in source.splitlines():
                stripped = line.strip()
                if stripped.startswith("if path"):
                    branches.append([stripped, []])
                elif branches and not stripped.startswith("self.send_error"):
                    branches[-1][1].append(stripped)
            self.assertGreater(len(branches), 5, handler.__name__)
            for header, body in branches:
                match = route_pattern.search(header)
                route = next((g for g in (match.groups() if match else ()) if g), header)
                if route in session_only:
                    continue
                with self.subTest(handler=handler.__name__, route=header):
                    self.assertTrue(
                        any("self.service." in line for line in body),
                        f"{header} does not call an AstraService method",
                    )

    def test_manager_cannot_edit_a_completed_task_back_into_work_over_http(self):
        # AS-1 over HTTP: 202 with a request row, the task itself unchanged.
        service = self.server.service
        owner = dict(service.db.execute("SELECT * FROM users WHERE global_role='owner'").fetchone())
        manager = service.create_user(owner, "http-manager@example.org", "Manager", "manager password safe")
        project = service.create_project(owner, "Source guard HTTP")
        service.grant_project_access(owner, project["id"], manager["id"], "manager")
        task = service.create_task(owner, {"project_id": project["id"], "title": "Done", "owner_user_id": manager["id"]})
        submission = service.submit_task(manager, task["id"], "done")
        service.accept_submission(owner, submission["id"], "ok")
        current = service.get_task(owner, task["id"])
        cookie, csrf = self._login_as("http-manager@example.org", "manager password safe")
        response, payload = self.request("POST", f"/api/tasks/{task['id']}", {
            "status": "in_progress", "reason": "oops", "expected_revision": current["revision"],
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 202)
        self.assertEqual(payload["request"]["action"], "update_task_status")
        response, payload = self.request("GET", f"/api/tasks/{task['id']}", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(payload["task"]["status"], "completed")

    def test_stale_task_update_returns_http_409_without_overwriting(self):
        cookie, csrf = self._owner_session()
        _, project = self.request(
            "POST", "/api/projects", {"name": "HTTP revisions"}, cookie=cookie, csrf=csrf
        )
        _, created = self.request(
            "POST",
            "/api/tasks",
            {"project_id": project["project"]["id"], "title": "Original"},
            cookie=cookie,
            csrf=csrf,
        )
        task = created["task"]
        response, updated = self.request(
            "POST",
            f"/api/tasks/{task['id']}",
            {"title": "First writer", "expected_revision": task["revision"]},
            cookie=cookie,
            csrf=csrf,
        )
        self.assertEqual(response.status, 200)

        response, conflict = self.request(
            "POST",
            f"/api/tasks/{task['id']}",
            {"title": "Stale writer", "expected_revision": task["revision"]},
            cookie=cookie,
            csrf=csrf,
        )

        self.assertEqual(response.status, 409)
        self.assertRegex(conflict["error"], "revision|conflict|stale")
        _, detail = self.request("GET", f"/api/tasks/{task['id']}", cookie=cookie)
        self.assertEqual(detail["task"]["title"], "First writer")
        self.assertEqual(detail["task"]["revision"], updated["task"]["revision"])

    def test_owner_can_approve_protected_request_over_http(self):
        owner_cookie, owner_csrf = self._owner_session()
        _, project = self.request(
            "POST", "/api/projects", {"name": "HTTP decisions"}, cookie=owner_cookie, csrf=owner_csrf
        )
        project_id = project["project"]["id"]
        _, manager = self.request(
            "POST",
            "/api/users",
            {
                "email": "decision-manager@example.org",
                "display_name": "Decision Manager",
                "password": "manager password safe",
                "role": "member",
            },
            cookie=owner_cookie,
            csrf=owner_csrf,
        )
        self.request(
            "POST",
            "/api/project-access",
            {"project_id": project_id, "user_id": manager["user"]["id"], "role": "manager"},
            cookie=owner_cookie,
            csrf=owner_csrf,
        )
        manager_cookie, manager_csrf = self._login_as(
            "decision-manager@example.org", "manager password safe"
        )
        _, created = self.request(
            "POST",
            "/api/tasks",
            {"project_id": project_id, "title": "Governed"},
            cookie=manager_cookie,
            csrf=manager_csrf,
        )
        task = created["task"]
        response, requested = self.request(
            "POST",
            f"/api/tasks/{task['id']}",
            {
                "status": "cancelled",
                "reason": "Manager recommends cancellation",
                "expected_revision": task["revision"],
            },
            cookie=manager_cookie,
            csrf=manager_csrf,
        )
        self.assertEqual(response.status, 202)

        response, decision = self.request(
            "POST",
            f"/api/owner-action-requests/{requested['request']['id']}/decision",
            {"decision": "approved", "reason": "Owner agrees"},
            cookie=owner_cookie,
            csrf=owner_csrf,
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(decision["request"]["status"], "approved")
        # SRFCZD R2: the Owner's posted note is the recorded decision reason.
        self.assertEqual(decision["request"]["decision_reason"], "Owner agrees")
        self.assertEqual(decision["request"]["reason"], "Manager recommends cancellation")
        _, detail = self.request("GET", f"/api/tasks/{task['id']}", cookie=owner_cookie)
        self.assertEqual(detail["task"]["status"], "cancelled")

    def test_non_owner_decision_on_a_request_returns_403_and_leaves_it_pending(self):
        owner_cookie, owner_csrf = self._owner_session()
        _, project = self.request(
            "POST", "/api/projects", {"name": "HTTP non-owner decisions"}, cookie=owner_cookie, csrf=owner_csrf
        )
        project_id = project["project"]["id"]
        for email, name, role in (
            ("forbidden-manager@example.org", "Forbidden Manager", "manager"),
            ("forbidden-viewer@example.org", "Forbidden Viewer", "viewer"),
        ):
            _, user = self.request("POST", "/api/users", {
                "email": email, "display_name": name, "password": f"{role} password safe", "role": "member",
            }, cookie=owner_cookie, csrf=owner_csrf)
            self.request("POST", "/api/project-access", {
                "project_id": project_id, "user_id": user["user"]["id"], "role": role,
            }, cookie=owner_cookie, csrf=owner_csrf)
        manager_cookie, manager_csrf = self._login_as("forbidden-manager@example.org", "manager password safe")
        viewer_cookie, viewer_csrf = self._login_as("forbidden-viewer@example.org", "viewer password safe")
        _, created = self.request(
            "POST", "/api/tasks", {"project_id": project_id, "title": "Governed"}, cookie=owner_cookie, csrf=owner_csrf
        )
        task = created["task"]
        response, requested = self.request("POST", f"/api/tasks/{task['id']}", {
            "status": "cancelled", "reason": "Manager recommends cancellation", "expected_revision": task["revision"],
        }, cookie=manager_cookie, csrf=manager_csrf)
        self.assertEqual(response.status, 202)
        request_id = requested["request"]["id"]

        for label, cookie, csrf in (("manager", manager_cookie, manager_csrf), ("viewer", viewer_cookie, viewer_csrf)):
            for decision in ("approved", "rejected"):
                with self.subTest(actor=label, decision=decision):
                    response, _ = self.request(
                        "POST", f"/api/owner-action-requests/{request_id}/decision",
                        {"decision": decision, "reason": "not mine"}, cookie=cookie, csrf=csrf,
                    )
                    self.assertEqual(response.status, 403)

        _, queue = self.request("GET", "/api/owner-action-requests", cookie=owner_cookie)
        self.assertEqual([(r["id"], r["status"]) for r in queue["requests"]], [(request_id, "pending")])
        _, detail = self.request("GET", f"/api/tasks/{task['id']}", cookie=owner_cookie)
        self.assertEqual(detail["task"]["status"], "draft")

    def test_stylesheet_declares_each_bare_class_once_and_the_import_dialog_uses_namespaced_classes(self):
        # Merged-state review MS-1..MS-6: the Gantt steps (D73AQW) and the import dialog (C9KPH6)
        # both declared bare .step, .chip and .muted, so whichever rule came last repainted the
        # other feature while the suite stayed green. A bare single-class selector may be
        # declared once at top level (a grouped list such as `.summary div, .panel, .toolbar` is a
        # shared base, not a second declaration), and the import dialog only uses namespaced classes.
        from pathlib import Path
        static = Path(inspect.getfile(AstraHandler)).parent / "static"
        raw_css = (static / "style.css").read_text(encoding="utf-8")
        css = re.sub(r"/\*.*?\*/", "", raw_css, flags=re.S)
        counts, depth, selector_start = {}, 0, 0
        for index, char in enumerate(css):
            if char == "{":
                if depth == 0:
                    selector = css[selector_start:index].strip()
                    if re.fullmatch(r"\.[A-Za-z0-9_-]+", selector):   # rules inside @media may repeat a selector
                        counts[selector] = counts.get(selector, 0) + 1
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    selector_start = index + 1
        self.assertEqual(depth, 0, "unbalanced braces in style.css")
        duplicates = sorted(name for name, n in counts.items() if n > 1)
        self.assertEqual(duplicates, [], f"bare class selectors declared more than once: {duplicates}")
        for expected in (".wiz-steps", ".wiz-step", ".wiz-n", ".import-chip", ".sr-only"):
            self.assertIn(expected, counts)
        import_block = raw_css[raw_css.index("/* C9KPH6"):raw_css.index("/* end C9KPH6 */")]
        self.assertNotRegex(import_block, r"(?m)^\.(step|steps|step-n|chip|muted|visually-hidden)\b")
        html = (static / "index.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r'class="(step|steps|step-n|chip)[" ]')
        self.assertIn('<li class="wiz-step" data-step="upload"', html)
        script = (static / "app.js").read_text(encoding="utf-8")
        self.assertIn('name="expected_revision"', script)
        self.assertIn("body.expected_revision=Number(body.expected_revision)", script)
        self.assertIn('data-request-decision="approved"', script)
        import_section = script[script.index("async function openImport"):]
        self.assertNotRegex(import_section, r'class="(step|steps|step-n|chip)[" ]')
        self.assertNotIn("#import-steps .step\"", import_section)
        self.assertNotIn("visually-hidden", import_section)
        self.assertIn('querySelectorAll("#import-steps .wiz-step")', import_section)
        self.assertIn('class="import-chip"', import_section)

    def test_governed_status_shortcut_rejected_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Guard"}, cookie=cookie, csrf=csrf)
        _, task = self.request("POST", "/api/tasks", {
            "project_id": project["project"]["id"], "title": "G",
        }, cookie=cookie, csrf=csrf)
        response, payload = self.request("POST", f"/api/tasks/{task['task']['id']}", {
            "status": "completed", "reason": "shortcut", "expected_revision": task["task"]["revision"],
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 400)
        self.assertIn("dedicated", payload["error"])

    def test_set_parent_and_rollup_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Tree"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        _, parent = self.request("POST", "/api/tasks", {"project_id": pid, "title": "Parent"}, cookie=cookie, csrf=csrf)
        _, child = self.request("POST", "/api/tasks", {"project_id": pid, "title": "Child"}, cookie=cookie, csrf=csrf)
        parent_id, child_id = parent["task"]["id"], child["task"]["id"]
        response, _ = self.request("POST", f"/api/tasks/{child_id}/parent", {"parent_task_id": parent_id}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        _, detail = self.request("GET", f"/api/tasks/{parent_id}", cookie=cookie)
        self.assertEqual(detail["task"]["subtask_rollup"], {"total": 1, "completed": 0})

    def test_task_list_sort_toggle_over_http(self):
        # QY0WG2: /api/tasks?sort= selects the order; both modes are reachable.
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "SortHTTP", "timezone": "UTC"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        self.request("POST", "/api/tasks", {"project_id": pid, "title": "Crit late", "criticality": "critical", "due_date": "2099-01-01"}, cookie=cookie, csrf=csrf)
        self.request("POST", "/api/tasks", {"project_id": pid, "title": "Low soon", "criticality": "low", "due_date": "2026-01-01"}, cookie=cookie, csrf=csrf)
        _, by_crit = self.request("GET", f"/api/tasks?project_id={pid}&sort=criticality", cookie=cookie)
        self.assertEqual([t["title"] for t in by_crit["tasks"]], ["Crit late", "Low soon"])
        _, by_due = self.request("GET", f"/api/tasks?project_id={pid}&sort=due_date", cookie=cookie)
        self.assertEqual([t["title"] for t in by_due["tasks"]], ["Low soon", "Crit late"])

    def test_search_and_export_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Findable"}, cookie=cookie, csrf=csrf)
        self.request("POST", "/api/tasks", {"project_id": project["project"]["id"], "title": "Needle task"}, cookie=cookie, csrf=csrf)
        _, search = self.request("GET", "/api/search?q=Needle", cookie=cookie)
        self.assertEqual([t["title"] for t in search["results"]["tasks"]], ["Needle task"])
        _, export = self.request("GET", "/api/export", cookie=cookie)
        self.assertIn("as_of", export["export"])
        self.connection.request("GET", "/api/export?format=csv", None, {"Cookie": cookie})
        response = self.connection.getresponse()
        disposition = response.getheader("Content-Disposition")
        body = response.read().decode()
        self.assertEqual(response.status, 200)
        self.assertIn("text/csv", response.getheader("Content-Type"))
        self.assertIn("Needle task", body)
        # Y3WC71: header row must be first — no leading '# Astra export' comment line.
        first_line = body.splitlines()[0]
        self.assertFalse(first_line.startswith("#"), f"CSV should not lead with a comment row: {first_line!r}")
        self.assertTrue(first_line.startswith("project_name"), f"first line should be the header: {first_line!r}")
        # Provenance (as-of) now rides in the download filename instead of an in-band row.
        self.assertIsNotNone(disposition)
        self.assertRegex(disposition, r'filename="astra-export-\d{4}-\d{2}-\d{2}.*\.csv"')

    def _get_raw(self, path, cookie=None):
        self.connection.request("GET", path, None, {"Cookie": cookie} if cookie else {})
        response = self.connection.getresponse()
        return response, response.read().decode("utf-8")

    def test_export_scope_isolation_over_http(self):
        # Y3WC71 review gaps 1 and 4: a member's export (JSON and CSV) never carries another
        # project's task, a hidden project_id is 403, and anonymous search/export are 403.
        cookie, csrf = self._owner_session()
        _, visible = self.request("POST", "/api/projects", {"name": "Scoped visible"}, cookie=cookie, csrf=csrf)
        _, hidden = self.request("POST", "/api/projects", {"name": "Scoped hidden"}, cookie=cookie, csrf=csrf)
        visible_id, hidden_id = visible["project"]["id"], hidden["project"]["id"]
        self.request("POST", "/api/tasks", {"project_id": visible_id, "title": "Visible export task"}, cookie=cookie, csrf=csrf)
        self.request("POST", "/api/tasks", {"project_id": hidden_id, "title": "Secret hidden task"}, cookie=cookie, csrf=csrf)
        _, member = self.request("POST", "/api/users", {
            "email": "scoped@example.org", "display_name": "Scoped", "password": "member password safe", "role": "member",
        }, cookie=cookie, csrf=csrf)
        response, _ = self.request("POST", "/api/project-access", {
            "project_id": visible_id, "user_id": member["user"]["id"], "role": "viewer",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        member_cookie, _ = self._login_as("scoped@example.org", "member password safe")
        response, export = self.request("GET", "/api/export", cookie=member_cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual([t["title"] for t in export["export"]["tasks"]], ["Visible export task"])
        response, body = self._get_raw("/api/export?format=csv", member_cookie)
        self.assertEqual(response.status, 200)
        self.assertIn("Visible export task", body)
        self.assertNotIn("Secret hidden task", body)
        response, _ = self.request("GET", f"/api/export?project_id={hidden_id}", cookie=member_cookie)
        self.assertEqual(response.status, 403)
        response, _ = self._get_raw(f"/api/export?format=csv&project_id={hidden_id}", member_cookie)
        self.assertEqual(response.status, 403)
        for path in ("/api/export", "/api/export?format=csv", "/api/search?q=Secret", "/api/final-results?format=csv"):
            response, _ = self._get_raw(path)
            self.assertEqual(response.status, 403, path)

    def test_csv_exports_neutralise_formula_cells(self):
        # Y3WC71 review gap 2 (CWE-1236): a cell a spreadsheet would evaluate is quoted, in both
        # the task export and the final-results export, the same way importer.csv_cell does it.
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "=HYPERLINK(\"http://x\")"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        titles = ["=1+1", "+SUM(A1:A2)", "-2+3", "@cmd", "\tTabbed", "\rReturn", "Plain title"]
        for title in titles:
            response, _ = self.request("POST", "/api/tasks", {"project_id": pid, "title": title}, cookie=cookie, csrf=csrf)
            self.assertEqual(response.status, 201, title)
        _, body = self._get_raw("/api/export?format=csv&sort=title", cookie)
        rows = list(csv.DictReader(io.StringIO(body)))
        exported = {row["title"] for row in rows}
        _, tasks = self.request("GET", "/api/tasks", cookie=cookie)
        stored = {t["title"] for t in tasks["tasks"]}  # the service may trim tab/CR off a title
        for title in stored:
            if title.startswith(("=", "+", "-", "@", "\t", "\r")):
                self.assertIn("'" + title, exported, title)
                self.assertNotIn(title, exported, f"formula cell left live: {title!r}")
        self.assertTrue({"'=1+1", "'+SUM(A1:A2)", "'-2+3", "'@cmd"} <= exported, exported)
        self.assertIn("Plain title", exported)
        # Tab and CR leads are neutralised by the cell helper itself, whatever the service stores.
        from astra.web import _csv_cell
        for value, expected in (("\tx", "'\tx"), ("\rx", "'\rx"), ("=1", "'=1"), ("a=1", "a=1"),
                                (None, ""), (3, "3"), ("", "")):
            self.assertEqual(_csv_cell(value), expected, repr(value))
        self.assertEqual({row["project_name"] for row in rows}, {"'=HYPERLINK(\"http://x\")"})
        task_id = next(t["id"] for t in tasks["tasks"] if t["title"] == "=1+1")
        _, attachment = self.request("POST", f"/api/tasks/{task_id}/attachments", {"path": "/out/final.pdf"}, cookie=cookie, csrf=csrf)
        response, _ = self.request("POST", "/api/final-results", {
            "task_id": task_id, "source_type": "attachment", "source_id": attachment["attachment"]["id"],
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        response, body = self._get_raw("/api/final-results?format=csv", cookie)
        self.assertEqual(response.status, 200)
        self.assertTrue(body.startswith("title,"), body[:40])
        self.assertRegex(response.getheader("Content-Disposition"), r'filename="astra-final-results-\d{4}-\d{2}-\d{2}.*\.csv"')
        [row] = list(csv.DictReader(io.StringIO(body)))
        self.assertEqual(row["task_title"], "'=1+1")
        self.assertEqual(row["project_name"], "'=HYPERLINK(\"http://x\")")

    def test_csv_export_filename_names_the_active_filters(self):
        # Y3WC71 review gap 3: the owner moved provenance out of the CSV body (header row first);
        # the active filters ride in the download filename next to the as-of stamp.
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Filtered"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        self.request("POST", "/api/tasks", {"project_id": pid, "title": "Keep", "status": "in_progress"}, cookie=cookie, csrf=csrf)
        response, body = self._get_raw(f"/api/export?format=csv&status=in_progress&open_only=1&band=7&project_id={pid}&sort=title", cookie)
        self.assertEqual(response.status, 200)
        self.assertTrue(body.startswith("project_name,"), body[:40])
        disposition = response.getheader("Content-Disposition")
        self.assertRegex(disposition, r'^attachment; filename="astra-export-\d{4}-\d{2}-\d{2}[^"/\\]*\.csv"$')
        filename = disposition.split('filename="', 1)[1].rstrip('"')
        self.assertIn(f"__project={pid}", filename)
        self.assertIn("__status=in_progress", filename)
        self.assertIn("__band=7", filename)
        self.assertIn("__open-only", filename)
        self.assertNotIn("sort", filename)  # ordering is not a filter
        response, _ = self._get_raw("/api/export?format=csv", cookie)
        self.assertNotIn("__", response.getheader("Content-Disposition"))  # unfiltered: as-of only
        response, _ = self._get_raw('/api/final-results?format=csv&type=attachment&q=a%22b/c%5Cd', cookie)
        filename = response.getheader("Content-Disposition").split('filename="', 1)[1].rstrip('"')
        self.assertIn("__type=attachment", filename)
        self.assertIn("__search=a-b-c-d", filename)  # quote, slash and backslash never reach the header

    def test_schedule_proposal_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "SchedHTTP"}, cookie=cookie, csrf=csrf)
        _, task = self.request("POST", "/api/tasks", {
            "project_id": project["project"]["id"], "title": "T", "due_date": "2026-10-05",
        }, cookie=cookie, csrf=csrf)
        tid = task["task"]["id"]
        response, prop = self.request("POST", f"/api/tasks/{tid}/schedule-proposals", {
            "due_date": "2026-10-20", "reason": "slip",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        response, _ = self.request("POST", f"/api/schedule-proposals/{prop['proposal']['id']}/approve", {}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        _, detail = self.request("GET", f"/api/tasks/{tid}", cookie=cookie)
        self.assertEqual(detail["task"]["due_date"], "2026-10-20")
        self.assertEqual(detail["task"]["baseline"]["due_date"], "2026-10-05")

    def test_confirm_criticality_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "CritHTTP"}, cookie=cookie, csrf=csrf)
        _, task = self.request("POST", "/api/tasks", {
            "project_id": project["project"]["id"], "title": "T",
        }, cookie=cookie, csrf=csrf)
        tid = task["task"]["id"]
        response, updated = self.request("POST", f"/api/tasks/{tid}/criticality", {
            "criticality": "critical", "reason": "urgent",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        self.assertEqual(updated["task"]["criticality"], "critical")
        # QY0WG2 review gap 2: the audit event over HTTP carries actor, old and new value.
        _, events = self.request("GET", f"/api/tasks/{tid}/events", cookie=cookie)
        change = [e for e in events["events"] if e["event_type"] == "criticality_changed"][-1]
        self.assertEqual(change["actor_name"], "Owner")
        self.assertEqual(json.loads(change["before_json"]), {"criticality": None})
        self.assertEqual(json.loads(change["after_json"]), {"criticality": "critical"})
        self.assertEqual(change["reason"], "urgent")

    def test_confirm_criticality_over_http_refuses_member_and_bad_input(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "CritGuard"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        _, task = self.request("POST", "/api/tasks", {"project_id": pid, "title": "T", "criticality": "low"},
                               cookie=cookie, csrf=csrf)
        tid = task["task"]["id"]
        url = f"/api/tasks/{tid}/criticality"
        # Missing, null and blank reasons, and a non-string level, are 400s that change nothing.
        for body in ({"criticality": "high"}, {"criticality": "high", "reason": None},
                     {"criticality": "high", "reason": "  "}, {"criticality": ["high"], "reason": "x"},
                     {"criticality": {"level": "high"}, "reason": "x"}):
            with self.subTest(body=body):
                response, error = self.request("POST", url, body, cookie=cookie, csrf=csrf)
                self.assertEqual(response.status, 400)
                self.assertIn("error", error)
        # A stale expected_revision is a 409.
        response, _ = self.request("POST", url, {"criticality": "high", "reason": "x", "expected_revision": 99},
                                   cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 409)
        # A plain project member (not a manager) is refused with 403.
        _, member = self.request("POST", "/api/users", {
            "email": "crit-member@example.org", "display_name": "Crit Member",
            "password": "member password safe", "role": "member",
        }, cookie=cookie, csrf=csrf)
        self.request("POST", "/api/project-access", {
            "project_id": pid, "user_id": member["user"]["id"], "role": "member",
        }, cookie=cookie, csrf=csrf)
        login_response, member_login = self.request(
            "POST", "/api/login", {"email": "crit-member@example.org", "password": "member password safe"})
        member_cookie = login_response.getheader("Set-Cookie").split(";", 1)[0]
        response, error = self.request("POST", url, {"criticality": "critical", "reason": "mine"},
                                       cookie=member_cookie, csrf=member_login["csrf"])
        self.assertEqual(response.status, 403)
        _, current = self.request("GET", f"/api/tasks/{tid}", cookie=cookie)
        self.assertEqual(current["task"]["criticality"], "low")
        _, events = self.request("GET", f"/api/tasks/{tid}/events", cookie=cookie)
        self.assertFalse([e for e in events["events"] if e["event_type"] == "criticality_changed"])

    def test_export_honours_sort_parameter(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "ExportSort"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        for title, crit, due in (("Low soon", "low", "2030-01-02"), ("Critical late", "critical", "2030-03-01"),
                                 ("Normal mid", "normal", "2030-02-01")):
            self.request("POST", "/api/tasks", {"project_id": pid, "title": title, "criticality": crit,
                                                "due_date": due}, cookie=cookie, csrf=csrf)
        _, by_crit = self.request("GET", f"/api/export?project_id={pid}&sort=criticality", cookie=cookie)
        _, by_due = self.request("GET", f"/api/export?project_id={pid}&sort=due_date", cookie=cookie)
        self.assertEqual([t["title"] for t in by_crit["export"]["tasks"]], ["Critical late", "Normal mid", "Low soon"])
        self.assertEqual([t["title"] for t in by_due["export"]["tasks"]], ["Low soon", "Normal mid", "Critical late"])
        self.connection.request("GET", f"/api/export?project_id={pid}&sort=due_date&format=csv", None, {"Cookie": cookie})
        response = self.connection.getresponse()
        body = response.read().decode("utf-8-sig")
        self.assertLess(body.index("Low soon"), body.index("Critical late"))

    def test_close_project_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "ToClose"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        response, closed = self.request("POST", f"/api/projects/{pid}/close", {"note": "wrap"}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        self.assertEqual(closed["project"]["status"], "closed")

    def test_portfolio_and_budget_over_http(self):
        cookie, csrf = self._owner_session()
        self.request("POST", "/api/entities/seed", {}, cookie=cookie, csrf=csrf)
        _, ents = self.request("GET", "/api/entities", cookie=cookie)
        rdi = next(e["id"] for e in ents["entities"] if e["name"] == "RDI Pakistan")
        _, project = self.request("POST", "/api/projects", {"name": "Budgeted"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        self.request("POST", f"/api/projects/{pid}/entities", {"entity_ids": [rdi]}, cookie=cookie, csrf=csrf)
        response, _ = self.request("POST", f"/api/projects/{pid}/budget", {"amount": 250000, "currency": "pkr"}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        response, pf = self.request("GET", "/api/portfolio", cookie=cookie)
        self.assertEqual(response.status, 200)
        roll = {r["entity_name"]: r for r in pf["portfolio"]}
        self.assertEqual(roll["RDI Pakistan"]["budgets"], {"PKR": 250000})  # currency upper-cased

    def test_project_calendar_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "CalHTTP"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        _, cal = self.request("GET", f"/api/projects/{pid}/calendar", cookie=cookie)
        self.assertEqual(cal["calendar"]["working_days"], "0123456")  # permissive default
        response, _ = self.request("POST", f"/api/projects/{pid}/working-days", {"days": "01234"}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        response, hol = self.request("POST", f"/api/projects/{pid}/holidays", {"date": "2026-12-25", "label": "Holiday"}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        self.assertEqual(hol["holidays"][0]["holiday_date"], "2026-12-25")
        _, cal = self.request("GET", f"/api/projects/{pid}/calendar", cookie=cookie)
        self.assertEqual(cal["calendar"]["working_days"], "01234")

    def test_entities_and_project_filing_over_http(self):
        cookie, csrf = self._owner_session()
        response, seeded = self.request("POST", "/api/entities/seed", {}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        self.assertIn("Tax Exempt", seeded["created"])
        _, entities = self.request("GET", "/api/entities", cookie=cookie)
        entity_id = next(e["id"] for e in entities["entities"] if e["name"] == "RDI Pakistan")
        _, project = self.request("POST", "/api/projects", {"name": "Filed"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        response, filed = self.request("POST", f"/api/projects/{pid}/entities", {"entity_ids": [entity_id]}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        self.assertEqual([e["name"] for e in filed["entities"]], ["RDI Pakistan"])
        _, projects = self.request("GET", "/api/projects", cookie=cookie)
        target = next(p for p in projects["projects"] if p["id"] == pid)
        self.assertEqual([e["id"] for e in target["entities"]], [entity_id])

    def test_notification_inbox_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "N"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        # Create a manager and a session for them.
        _, mgr = self.request("POST", "/api/users", {
            "email": "mgr@example.org", "display_name": "Mgr", "password": "manager password ok", "role": "member",
        }, cookie=cookie, csrf=csrf)
        self.request("POST", "/api/project-access", {
            "project_id": pid, "user_id": mgr["user"]["id"], "role": "manager",
        }, cookie=cookie, csrf=csrf)
        resp, mgr_login = self.request("POST", "/api/login", {"email": "mgr@example.org", "password": "manager password ok"})
        mgr_cookie = resp.getheader("Set-Cookie").split(";", 1)[0]
        mgr_csrf = mgr_login["csrf"]
        # Manager creates a task -> owner gets a notification.
        self.request("POST", "/api/tasks", {"project_id": pid, "title": "Mgr task"}, cookie=mgr_cookie, csrf=mgr_csrf)
        response, inbox = self.request("GET", "/api/notifications", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(inbox["unread"], 1)
        nid = inbox["notifications"][0]["id"]
        response, _ = self.request("POST", f"/api/notifications/{nid}/read", {}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        _, inbox2 = self.request("GET", "/api/notifications", cookie=cookie)
        self.assertEqual(inbox2["unread"], 0)

    def test_login_is_throttled_after_repeated_failures(self):
        for _ in range(5):
            response, _ = self.request("POST", "/api/login", {
                "email": "owner@example.org", "password": "wrong password guess",
            })
            self.assertEqual(response.status, 401)
        response, payload = self.request("POST", "/api/login", {
            "email": "owner@example.org", "password": "correct horse battery",
        })
        self.assertEqual(response.status, 429)
        self.assertIn("Too many", payload["error"])

    def test_logout_all_revokes_other_sessions(self):
        cookie1, csrf1 = self._owner_session()
        cookie2, csrf2 = self._owner_session()
        response, payload = self.request("POST", "/api/logout-all", {}, cookie=cookie2, csrf=csrf2)
        self.assertEqual(response.status, 200)
        self.assertGreaterEqual(payload["revoked"], 2)
        response, _ = self.request("GET", "/api/me", cookie=cookie1)
        self.assertEqual(response.status, 403)

    def test_blank_title_update_returns_400_and_preserves_task(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Titles"}, cookie=cookie, csrf=csrf)
        _, task = self.request("POST", "/api/tasks", {
            "project_id": project["project"]["id"], "title": "Keep me",
        }, cookie=cookie, csrf=csrf)
        task_id = task["task"]["id"]
        response, payload = self.request(
            "POST",
            f"/api/tasks/{task_id}",
            {"title": "  ", "expected_revision": task["task"]["revision"]},
            cookie=cookie,
            csrf=csrf,
        )
        self.assertEqual(response.status, 400)
        self.assertIn("title", payload["error"])
        response, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=cookie)
        self.assertEqual(detail["task"]["title"], "Keep me")

    def test_task_attachment_link_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Deliverables"}, cookie=cookie, csrf=csrf)
        _, task = self.request("POST", "/api/tasks", {
            "project_id": project["project"]["id"], "title": "Final audit memo",
        }, cookie=cookie, csrf=csrf)
        task_id = task["task"]["id"]
        response, added = self.request("POST", f"/api/tasks/{task_id}/attachments", {
            "path": "/reports/audit-memo.pdf", "note": "Board copy",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        self.assertEqual(added["attachment"]["display_name"], "audit-memo.pdf")
        response, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=cookie)
        self.assertEqual(len(detail["task"]["attachments"]), 1)
        attachment_id = added["attachment"]["id"]
        response, _ = self.request("DELETE", "/api/task-attachments", {
            "task_id": task_id, "attachment_id": attachment_id,
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        response, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=cookie)
        self.assertEqual(detail["task"]["attachments"], [])

    def test_file_and_final_result_mutations_are_owner_only_over_http(self):
        owner_cookie, owner_csrf = self._owner_session()
        _, project = self.request(
            "POST", "/api/projects", {"name": "Owner files"}, cookie=owner_cookie, csrf=owner_csrf
        )
        project_id = project["project"]["id"]
        _, task = self.request("POST", "/api/tasks", {
            "project_id": project_id, "title": "Governed evidence",
        }, cookie=owner_cookie, csrf=owner_csrf)
        task_id = task["task"]["id"]
        _, attachment = self.request("POST", f"/api/tasks/{task_id}/attachments", {
            "path": "/evidence/owner.pdf",
        }, cookie=owner_cookie, csrf=owner_csrf)
        _, submission = self.request(
            "POST", f"/api/tasks/{task_id}/submit", {"note": "ready"},
            cookie=owner_cookie, csrf=owner_csrf,
        )
        submission_id = submission["submission"]["id"]
        self.request(
            "POST", f"/api/submissions/{submission_id}/accept", {"decision_note": "owner accepts"},
            cookie=owner_cookie, csrf=owner_csrf,
        )
        _, manager = self.request("POST", "/api/users", {
            "email": "file-manager@example.org", "display_name": "File Manager",
            "password": "manager password safe", "role": "member",
        }, cookie=owner_cookie, csrf=owner_csrf)
        self.request("POST", "/api/project-access", {
            "project_id": project_id, "user_id": manager["user"]["id"], "role": "manager",
        }, cookie=owner_cookie, csrf=owner_csrf)
        login_response, manager_login = self.request(
            "POST", "/api/login", {"email": "file-manager@example.org", "password": "manager password safe"}
        )
        manager_cookie = login_response.getheader("Set-Cookie").split(";", 1)[0]
        manager_csrf = manager_login["csrf"]

        response, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=manager_cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(len(detail["task"]["attachments"]), 1)
        response, _ = self.request("POST", f"/api/tasks/{task_id}/attachments", {
            "path": "/evidence/manager.pdf",
        }, cookie=manager_cookie, csrf=manager_csrf)
        self.assertEqual(response.status, 403)
        response, _ = self.request("DELETE", "/api/task-attachments", {
            "task_id": task_id, "attachment_id": attachment["attachment"]["id"],
        }, cookie=manager_cookie, csrf=manager_csrf)
        self.assertEqual(response.status, 403)
        response, _ = self.request("POST", "/api/final-results", {
            "task_id": task_id, "source_type": "submission", "source_id": submission_id,
        }, cookie=manager_cookie, csrf=manager_csrf)
        self.assertEqual(response.status, 403)

        response, _ = self.request("POST", "/api/final-results", {
            "task_id": task_id, "source_type": "submission", "source_id": submission_id,
        }, cookie=owner_cookie, csrf=owner_csrf)
        self.assertEqual(response.status, 201)
        response, listed = self.request("GET", "/api/final-results", cookie=manager_cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(len(listed["results"]), 1)
        _, notifications = self.request("GET", "/api/notifications", cookie=owner_cookie)
        kinds = {item["kind"] for item in notifications["notifications"]}
        self.assertIn("attachment_removal_blocked", kinds)

    def test_project_template_roundtrip_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Template source"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        self.request("POST", "/api/tasks", {
            "project_id": pid, "title": "Plan", "start_date": "2026-05-01", "due_date": "2026-05-05",
        }, cookie=cookie, csrf=csrf)
        response, saved = self.request("POST", "/api/templates/from-project", {
            "project_id": pid, "name": "Reusable plan",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        template_id = saved["template"]["id"]
        response, listed = self.request("GET", "/api/templates", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(len(listed["templates"]), 1)
        response, created = self.request("POST", f"/api/templates/{template_id}/create-project", {
            "name": "Made from template", "anchor_date": "2027-05-01",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        new_pid = created["project"]["id"]
        response, tasks = self.request("GET", f"/api/tasks?project_id={new_pid}", cookie=cookie)
        self.assertEqual(len(tasks["tasks"]), 1)
        self.assertEqual(tasks["tasks"][0]["start_date"], "2027-05-01")
        self.assertEqual(tasks["tasks"][0]["status"], "draft")
        response, _ = self.request("DELETE", "/api/templates", {"template_id": template_id}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)

    def test_templates_carry_roles_and_apply_role_picks_over_http(self):
        # 8B9NBH: suggested owners are roles; the Owner picks a person per role.
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Role source"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        _, pm = self.request("POST", "/api/users", {
            "email": "pm@example.org", "display_name": "PM", "password": "member password safe",
        }, cookie=cookie, csrf=csrf)
        pm_id = pm["user"]["id"]
        self.request("POST", "/api/project-access", {"project_id": pid, "user_id": pm_id, "role": "manager"},
                     cookie=cookie, csrf=csrf)
        _, task = self.request("POST", "/api/tasks", {"project_id": pid, "title": "Plan", "owner_user_id": pm_id},
                               cookie=cookie, csrf=csrf)
        response, saved = self.request("POST", "/api/templates/from-project", {"project_id": pid, "name": "P"},
                                       cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        self.assertEqual(saved["template"]["body"]["tasks"][0]["suggested_role"], "manager")
        _, listed = self.request("GET", "/api/templates", cookie=cookie)
        self.assertEqual(listed["templates"][0]["roles"], ["manager"])
        _, other = self.request("POST", "/api/users", {
            "email": "pm2@example.org", "display_name": "PM2", "password": "member password safe",
        }, cookie=cookie, csrf=csrf)
        response, created = self.request("POST", f"/api/templates/{saved['template']['id']}/create-project", {
            "name": "Next cycle", "role_assignments": {"manager": other["user"]["id"]},
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        _, tasks = self.request("GET", f"/api/tasks?project_id={created['project']['id']}", cookie=cookie)
        self.assertEqual(tasks["tasks"][0]["owner_user_id"], other["user"]["id"])
        response, error = self.request("POST", f"/api/templates/{saved['template']['id']}/create-project", {
            "name": "Bad", "role_assignments": {"auditor": pm_id},
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 400)
        # Task subtree: saved and applied into the source project, where the role has one holder.
        response, task_tmpl = self.request("POST", "/api/templates/from-task", {
            "task_id": task["task"]["id"], "name": "T",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        response, result = self.request("POST", f"/api/templates/{task_tmpl['template']['id']}/create-task", {
            "project_id": pid,
        }, cookie=cookie, csrf=csrf)
        self.assertEqual((response.status, result["result"]["created"]), (201, 1))
        _, tasks = self.request("GET", f"/api/tasks?project_id={pid}", cookie=cookie)
        self.assertEqual([t["owner_user_id"] for t in tasks["tasks"]], [pm_id, pm_id])

    def test_final_results_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Results HTTP"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        _, task = self.request("POST", "/api/tasks", {"project_id": pid, "title": "Final memo"}, cookie=cookie, csrf=csrf)
        task_id = task["task"]["id"]
        _, submission = self.request("POST", f"/api/tasks/{task_id}/submit", {"note": "ready"}, cookie=cookie, csrf=csrf)
        submission_id = submission["submission"]["id"]
        response, _ = self.request("POST", f"/api/submissions/{submission_id}/accept", {
            "decision_note": "approved",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        # CS93C6: acceptance does NOT auto-record a final result — the repository is empty.
        response, listed = self.request("GET", "/api/final-results", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(len(listed["results"]), 0)
        # The accepted submission must be marked by hand to appear.
        response, marked_sub = self.request("POST", "/api/final-results", {
            "task_id": task_id, "source_type": "submission", "source_id": submission_id,
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        response, listed = self.request("GET", "/api/final-results", cookie=cookie)
        self.assertEqual(len(listed["results"]), 1)
        _, attachment = self.request("POST", f"/api/tasks/{task_id}/attachments", {
            "path": "/out/final.pdf",
        }, cookie=cookie, csrf=csrf)
        response, marked = self.request("POST", "/api/final-results", {
            "task_id": task_id, "source_type": "attachment", "source_id": attachment["attachment"]["id"],
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        response, only_att = self.request("GET", "/api/final-results?type=attachment", cookie=cookie)
        self.assertEqual(len(only_att["results"]), 1)
        response, _ = self.request("DELETE", "/api/final-results", {
            "result_id": marked["result"]["id"],
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        response, after = self.request("GET", "/api/final-results", cookie=cookie)
        self.assertEqual(len(after["results"]), 1)  # only the manually-marked submission remains

    def _mark_final_attachment(self, cookie, csrf, project_id, title, marked_at):
        _, task = self.request("POST", "/api/tasks", {"project_id": project_id, "title": title}, cookie=cookie, csrf=csrf)
        task_id = task["task"]["id"]
        _, attachment = self.request("POST", f"/api/tasks/{task_id}/attachments", {"path": f"/out/{title}.pdf"}, cookie=cookie, csrf=csrf)
        response, marked = self.request("POST", "/api/final-results", {
            "task_id": task_id, "source_type": "attachment", "source_id": attachment["attachment"]["id"],
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        # marked_at is stamped with "now"; pin it to a known instant for the date filters.
        self.server.service.db.execute("UPDATE final_results SET marked_at=? WHERE id=?", (marked_at, marked["result"]["id"]))
        self.server.service.db.commit()

    def test_final_results_filters_and_csv_export_over_http(self):
        # CS93C6 review gaps 2-3: the date filter (and the others) narrow both the JSON list and
        # the CSV export; the CSV is header-first, names its filters, and is scoped to the caller.
        cookie, csrf = self._owner_session()
        _, alpha = self.request("POST", "/api/projects", {"name": "FR Alpha"}, cookie=cookie, csrf=csrf)
        _, beta = self.request("POST", "/api/projects", {"name": "FR Beta"}, cookie=cookie, csrf=csrf)
        alpha_id, beta_id = alpha["project"]["id"], beta["project"]["id"]
        self._mark_final_attachment(cookie, csrf, alpha_id, "March memo", "2026-03-05T10:00:00.000000+00:00")
        self._mark_final_attachment(cookie, csrf, alpha_id, "April memo", "2026-04-30T23:59:59.999999+00:00")
        self._mark_final_attachment(cookie, csrf, beta_id, "Hidden brief", "2026-04-10T09:00:00.000000+00:00")

        def titles(query):
            response, body = self.request("GET", "/api/final-results" + query, cookie=cookie)
            self.assertEqual(response.status, 200, query)
            return sorted(r["task_title"] for r in body["results"])

        self.assertEqual(titles(""), ["April memo", "Hidden brief", "March memo"])
        self.assertEqual(titles("?from=2026-04-01"), ["April memo", "Hidden brief"])
        self.assertEqual(titles("?to=2026-03-31"), ["March memo"])
        self.assertEqual(titles("?from=2026-04-30&to=2026-04-30"), ["April memo"])
        self.assertEqual(titles(f"?project_id={alpha_id}&from=2026-04-01"), ["April memo"])
        self.assertEqual(titles("?q=brief"), ["Hidden brief"])
        response, error = self.request("GET", "/api/final-results?from=not-a-date", cookie=cookie)
        self.assertEqual(response.status, 400)

        response, body = self._get_raw(f"/api/final-results?format=csv&project_id={alpha_id}&from=2026-04-01&to=2026-04-30", cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Type"), "text/csv; charset=utf-8")
        reader = csv.reader(io.StringIO(body))
        self.assertEqual(next(reader), ["title", "source_type", "task_title", "project_name", "entities",
                                        "attachment_path", "submission_version", "marked_by_name", "marked_at"])
        rows = list(reader)
        self.assertEqual([(row[2], row[3], row[1]) for row in rows], [("April memo", "FR Alpha", "attachment")])
        filename = response.getheader("Content-Disposition").split('filename="', 1)[1].rstrip('"')
        self.assertTrue(filename.startswith("astra-final-results-"), filename)
        for part in (f"__project={alpha_id}", "__from=2026-04-01", "__to=2026-04-30"):
            self.assertIn(part, filename)

        # A member of Alpha only: neither the list nor the CSV carries Beta's result.
        _, member = self.request("POST", "/api/users", {
            "email": "fr-member@example.org", "display_name": "FR Member", "password": "member password safe", "role": "member",
        }, cookie=cookie, csrf=csrf)
        self.request("POST", "/api/project-access", {
            "project_id": alpha_id, "user_id": member["user"]["id"], "role": "viewer",
        }, cookie=cookie, csrf=csrf)
        member_cookie, _ = self._login_as("fr-member@example.org", "member password safe")
        response, listed = self.request("GET", "/api/final-results?from=2026-04-01", cookie=member_cookie)
        self.assertEqual([r["task_title"] for r in listed["results"]], ["April memo"])
        response, body = self._get_raw("/api/final-results?format=csv", member_cookie)
        self.assertEqual(response.status, 200)
        self.assertEqual(sorted(row["task_title"] for row in csv.DictReader(io.StringIO(body))), ["April memo", "March memo"])
        self.assertNotIn("Hidden brief", body)

    def test_project_schedule_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Timed"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        response, updated = self.request("POST", f"/api/projects/{pid}/schedule", {
            "start_date": "2026-02-01", "target_date": "2026-05-01", "reason": "Kickoff scheduled",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        self.assertEqual(updated["project"]["target_date"], "2026-05-01")
        # A change without a reason is rejected.
        response, payload = self.request("POST", f"/api/projects/{pid}/schedule", {
            "start_date": "2026-02-01", "target_date": "2026-06-01",
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 400)
        self.assertIn("reason", payload["error"])

    def test_task_detail_subtasks_carry_step_schedule_fields_over_http(self):
        # D73AQW: GET /api/tasks/{id} subtasks include the fields the Gantt step
        # tooltip and the detail dialog render (start, criticality, progress, owner id, parent).
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "StepsHTTP"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        _, parent = self.request("POST", "/api/tasks", {"project_id": pid, "title": "Parent"}, cookie=cookie, csrf=csrf)
        parent_id = parent["task"]["id"]
        _, step = self.request("POST", "/api/tasks", {
            "project_id": pid, "title": "Step one", "parent_task_id": parent_id,
            "start_date": "2026-11-02", "due_date": "2026-11-06", "criticality": "normal", "progress": 25,
        }, cookie=cookie, csrf=csrf)
        response, detail = self.request("GET", f"/api/tasks/{parent_id}", cookie=cookie)
        self.assertEqual(response.status, 200)
        subtasks = detail["task"]["subtasks"]
        self.assertEqual(len(subtasks), 1)
        self.assertEqual(subtasks[0]["id"], step["task"]["id"])
        self.assertEqual(subtasks[0]["start_date"], "2026-11-02")
        self.assertEqual(subtasks[0]["due_date"], "2026-11-06")
        self.assertEqual(subtasks[0]["criticality"], "normal")
        self.assertEqual(subtasks[0]["progress"], 25)
        self.assertEqual(subtasks[0]["parent_task_id"], parent_id)
        self.assertIn("owner_user_id", subtasks[0])
        # The step's own detail names its parent so the dialog can render the back-link.
        _, step_detail = self.request("GET", f"/api/tasks/{step['task']['id']}", cookie=cookie)
        self.assertEqual(step_detail["task"]["parent_title"], "Parent")
        self.assertEqual(step_detail["task"]["parent_task_id"], parent_id)

    def test_undated_parent_with_undated_steps_over_http(self):
        # GF-16 / MS-4: the chip "n steps need dates" is built from children with neither date; an
        # undated parent returns exactly that shape (nulls, never invented dates) for its steps.
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "UndatedSteps"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        _, parent = self.request("POST", "/api/tasks", {"project_id": pid, "title": "All-undated parent"}, cookie=cookie, csrf=csrf)
        parent_id = parent["task"]["id"]
        for title in ("Undated kid 1", "Undated kid 2"):
            self.request("POST", "/api/tasks", {"project_id": pid, "title": title, "parent_task_id": parent_id}, cookie=cookie, csrf=csrf)
        _, listing = self.request("GET", "/api/tasks", cookie=cookie)
        kids = [t for t in listing["tasks"] if t["parent_task_id"] == parent_id]
        self.assertEqual(len(kids), 2)
        self.assertTrue(all(t["start_date"] is None and t["due_date"] is None for t in kids))
        parent_row = next(t for t in listing["tasks"] if t["id"] == parent_id)
        self.assertIsNone(parent_row["start_date"])
        self.assertIsNone(parent_row["due_date"])
        self.assertEqual(parent_row["due_state"], "undated")


class AstraStaticAssetTests(unittest.TestCase):
    """D73AQW adversarial-review follow-ups pinned on the shipped static files.

    The Gantt is rendered client-side, so these tests read app.js / style.css / index.html
    as text: the colour tokens are recomputed as WCAG contrast ratios and the structural
    fixes (chip and +N placement, parent-sized track, focus return, short labels, wrap
    texture, legend wording) are asserted on the source that produces them.
    """

    @classmethod
    def setUpClass(cls):
        cls.js = (STATIC / "app.js").read_text(encoding="utf-8")
        cls.css = (STATIC / "style.css").read_text(encoding="utf-8")
        cls.html = (STATIC / "index.html").read_text(encoding="utf-8")
        cls.readme = (REPO / "README.md").read_text(encoding="utf-8")
        cls.contract = (REPO / "docs" / "design" / "gantt-steps-contract.md").read_text(encoding="utf-8")

    def _tokens(self, suffix):
        return dict(re.findall(rf"--step-(\d){suffix}:\s*({HEX})", self.css))

    def test_step_edge_tokens_reach_3_to_1_on_tint_tracks_and_white(self):
        # GF-3: the stripe and border are drawn from a per-hue edge token; every edge must separate
        # a segment from its own tint, from every track tint and from white at >= 3:1 (WCAG 1.4.11).
        hues, tints, edges = self._tokens(""), self._tokens("-tint"), self._tokens("-edge")
        self.assertEqual(sorted(hues), list("1234567"))
        self.assertEqual(sorted(tints), list("1234567"))
        self.assertEqual(sorted(edges), list("1234567"))
        track_rules = re.findall(rf"\.bar\.track[^{{]*\{{[^}}]*?background:\s*({HEX})", self.css)
        self.assertGreaterEqual(len(track_rules), 8, "default, overdue, soon/today, scheduled, blocked, closed, critical, derived")
        ink = re.search(rf"--ink:\s*({HEX})", self.css).group(1)
        done_text = re.search(rf"\.step\.done \{{[^}}]*color:\s*({HEX})", self.css).group(1)
        for i in "1234567":
            self.assertGreaterEqual(contrast_ratio(edges[i], tints[i]), 3.0, f"edge {i} vs tint {i}")
            for background in track_rules + ["#FFFFFF"]:
                self.assertGreaterEqual(contrast_ratio(edges[i], background), 3.0, f"edge {i} vs {background}")
            self.assertGreaterEqual(contrast_ratio(ink, tints[i]), 4.5, f"ink on tint {i}")
            self.assertGreaterEqual(contrast_ratio(done_text, tints[i]), 4.5, f"done text on tint {i}")
        # The segment and swatch draw border and stripe from --edge and no longer carry the white ring.
        self.assertRegex(self.css, r"\.step \{[^}]*border: 1px solid var\(--edge, var\(--gray\)\)[^}]*box-shadow: inset 0 -3px 0 var\(--edge, var\(--gray\)\);")
        self.assertRegex(self.css, r"\.sw \{[^}]*border: 1px solid var\(--edge, var\(--gray\)\)")
        self.assertNotIn("inset 0 0 0 1px #fff", self.css)
        for i in "1234567":
            self.assertIn(f".step-c{i}, .sw.step-c{i} {{ --hue: var(--step-{i}); --tint: var(--step-{i}-tint); --edge: var(--step-{i}-edge); }}", self.css)

    def test_undated_chip_and_more_button_never_cover_a_step(self):
        # GF-1 / GF-16: the chip is built before the dated branch and rendered in the meta column
        # (no timeline position), so an all-undated parent gets it too and no step sits under it.
        self.assertLess(self.js.index('class="chip step-undated"'), self.js.index("if(!ext){bar="))
        self.assertNotIn('class="chip step-undated" data-detail="${id}" data-x=', self.js)
        self.assertIn("${derived}${undatedChip}${metaMore}${overrunText}", self.js)
        self.assertRegex(self.css, r"\.chip \{ position: relative; display: inline-flex;")
        # +N sits outside the track (right, left with .flip, or in the meta column), never pinned inside it.
        self.assertRegex(self.css, r"\.step-more \{ position: absolute; left: 100%;")
        self.assertNotRegex(self.css, r"\.step-more \{[^}]*right: 2px")
        self.assertRegex(self.css, r"\.step-more\.flip \{ left: auto; right: 100%;")
        self.assertIn('place=100-(left+width)>=need?"":(left>=need?" flip":" in-meta")', self.js)
        self.assertIn('if(place===" in-meta")metaMore=`<br>${moreBtn}${moreList}`;', self.js)
        # GF-7: the same 44px hit area as a step; decorative marker lines never intercept the pointer.
        self.assertIn('.step-more::before { content: ""; position: absolute; left: 0; right: 0; top: -13px; bottom: -13px; }', self.css)
        self.assertRegex(self.css, r"\.today-line \{[^}]*pointer-events: none")
        self.assertRegex(self.css, r"\.proj-line \{[^}]*pointer-events: none")

    def test_track_is_sized_from_the_parents_own_dates_and_names_overruns(self):
        # GF-2: a dated parent's track comes from its own dates; steps outside them overhang onto a
        # dashed neutral extension and are named in the parent's tooltip and meta column.
        self.assertIn("const ext=ownDates?dateExtent(t,[]):dateExtent(t,kids);", self.js)
        self.assertIn('class="track-ext before"', self.js)
        self.assertIn('class="track-ext after" data-x="100"', self.js)
        self.assertIn('overruns.push(`Step ${idx} ends ${d} day${d===1?"":"s"} after the parent`)', self.js)
        self.assertIn('overruns.push(`Step ${idx} starts ${d} day${d===1?"":"s"} before the parent`)', self.js)
        self.assertIn("tipAttrs(t,null,kids.length,overruns)", self.js)
        self.assertIn('<span class="overrun-text">', self.js)
        # Steps are no longer clamped into the track, so an overhang is drawn rather than clipped.
        self.assertNotIn("x:Math.max(0,(pct(ks)-left)/width*100)", self.js)
        self.assertNotIn("w:Math.min(100-x,wPct/width*100)", self.js)
        self.assertRegex(self.css, r"\.track-ext \{[^}]*border: 1px dashed var\(--gray\)[^}]*pointer-events: none")

    def test_focus_returns_to_a_visible_control(self):
        # GF-6: Escape in a +N list, a dialog opened from a list link, and any re-render.
        self.assertIn("const held=l.contains(document.activeElement)", self.js)
        self.assertIn('if(b){b.setAttribute("aria-expanded","false");if(held)b.focus()}', self.js)
        self.assertIn('const list=b.closest(".step-more-list");', self.js)
        self.assertIn("const focusKey=focusKeyIn(el);", self.js)
        self.assertIn("restoreFocus(el,focusKey);", self.js)
        self.assertIn('n.focus({preventScroll:true})', self.js)

    def test_step_labels_are_short_and_tooltip_follows_the_focused_element(self):
        # GF-8: aria-label carries position and name only; the tooltip text is linked through
        # aria-describedby while visible and cleared when that same element loses focus.
        self.assertIn("`Step ${idx} of ${total}, ${t.title}`", self.js)
        self.assertNotIn("Press Enter for details", self.js)
        self.assertIn('gantt.addEventListener("focusin",e=>{if(e.target.matches("[data-tip]"))showTip(e.target)});', self.js)
        self.assertIn('gantt.addEventListener("focusout",e=>{if(e.target.matches("[data-tip]")&&e.target===tipFor)hideTip()});', self.js)
        self.assertIn('if(isMore(e.target))return;', self.js)

    def test_wrap_texture_legend_and_docs_agree(self):
        # GF-10: 8+ steps use a doubled stripe, on-hold keeps the hatching, so both can show at once.
        self.assertIn(".step.wrap, .sw.wrap { box-shadow: inset 0 -3px 0 var(--edge), inset 0 -4px 0 var(--tint), inset 0 -6px 0 var(--edge); }", self.css)
        self.assertNotRegex(self.css, r"\.step\.wrap[^}]*repeating-linear-gradient")
        self.assertRegex(self.css, r"\.step\.hold \{[^}]*repeating-linear-gradient")
        # list item, name-column kicker, Schedule table and detail-dialog subtasks all carry it
        self.assertEqual(self.js.count('>STEP_HUES?" wrap":""}'), 4)
        # DTJ-06: legend, contract and README describe the shipped behaviour.
        self.assertIn("+N not drawn at this scale (too small or overlapping)", self.html)
        self.assertNotIn("too small to draw", self.html)
        self.assertIn("8+ repeats the colours with a doubled stripe", self.html)
        self.assertIn("not drawn at this scale (too small or overlapping)", self.contract)
        self.assertIn("--step-1-edge", self.contract)
        for phrase in ("steps", "tooltip", "chevron", "Schedule table", "phone width"):
            self.assertIn(phrase, self.readme)


# ARZWV7: renderDetail is run under node against a permissive DOM stub, so these tests read the
# markup the dialog really renders. The server stays the authority; this pins the UX only.
DETAIL_DRIVER = r"""
const fs=require("fs");
const src=fs.readFileSync(process.argv[2],"utf8");
const cases=JSON.parse(fs.readFileSync(0,"utf8"));
const store={};
function el(key){
  const t={innerHTML:"",textContent:"",value:"",style:{},dataset:{},options:[],open:false};
  return new Proxy(t,{get(o,k){
    if(k===Symbol.toPrimitive)return()=>"";
    if(k in o)return o[k];
    if(k==="querySelectorAll")return()=>[];
    if(k==="querySelector")return s=>document.querySelector(s);
    if(k==="classList")return{add(){},remove(){},toggle(){},contains(){return false}};
    return function(){return el()};
  },set(o,k,v){o[k]=v;return true}});
}
globalThis.document={querySelector(s){return store[s]||(store[s]=el(s))},querySelectorAll(){return[]},
  getElementById(s){return document.querySelector("#"+s)},createElement(){return el()},addEventListener(){},body:el(),documentElement:el()};
globalThis.window=globalThis;globalThis.addEventListener=()=>{};
globalThis.localStorage={getItem(){return null},setItem(){}};
globalThis.fetch=()=>new Promise(()=>{});
globalThis.Option=function(t,v){return{text:t,value:v}};
globalThis.location={hash:"",search:""};globalThis.history={replaceState(){}};
const driver=`;globalThis.__render=(task)=>{renderDetail(task,[]);return document.querySelector("#detail-body").innerHTML};`;
(0,eval)(src+driver);
const out={};
for(const [name,task] of Object.entries(cases))out[name]=globalThis.__render(task);
process.stdout.write(JSON.stringify(out));
"""

OWNER_PERMS = {"can_edit_ordinary": True, "can_request_protected": False,
               "can_decide_protected": True, "can_manage_files": True, "can_read_files": True}
MANAGER_PERMS = {"can_edit_ordinary": True, "can_request_protected": True,
                 "can_decide_protected": False, "can_manage_files": False, "can_read_files": True}


def _detail_task(status, permissions):
    submission_status = "submitted" if status == "submitted" else "accepted"
    return {
        "id": "t1", "title": "Synthetic task", "project_id": "p1", "project_name": "P", "status": status,
        "revision": 3, "criticality": "high", "due_state": "closed", "start_date": "2026-09-01",
        "due_date": "2026-10-10", "progress": None, "description": "", "owner_user_id": None,
        "permissions": permissions, "baseline": {}, "subtasks": [], "final_results": [],
        "dependencies": [
            {"direction": "incoming", "predecessor_title": "Before", "successor_title": "Synthetic task",
             "predecessor_task_id": "t0", "successor_task_id": "t1", "blocking": False},
            {"direction": "outgoing", "predecessor_title": "Synthetic task", "successor_title": "After",
             "predecessor_task_id": "t1", "successor_task_id": "t2", "blocking": False},
        ],
        "reviewers": [{"display_name": "Reviewer", "role": "approver", "user_id": "u2"}],
        "attachments": [{"id": "a1", "display_name": "Report", "path": "C:\\x\\report.pdf", "exists": True,
                         "added_at": "2026-09-01T00:00:00Z", "added_by_name": "Owner"}],
        "submissions": [{"id": "s1", "version": 1, "status": submission_status, "submitted_by_name": "Owner"}],
        "schedule_proposals": [{"id": "sp1", "status": "pending", "start_date": "2026-09-02",
                                "due_date": "2026-10-11", "reason": "slip", "proposed_by_name": "Owner"}],
    }


CONFLICT_TEXT = "This task changed since you opened it"
INBOX_REQUESTS = [
    {"id": "r1", "action": "update_task_status", "task_id": "t9", "task_title": "Vendor shortlist",
     "project_name": "P", "requested_by_name": "Mia Manager", "requested_at": "2026-09-23T10:00:00Z",
     "reason": "Client withdrew <b>the site</b>",
     "payload": {"status": "in_progress", "from_status": "cancelled", "expected_revision": 1}},
    {"id": "r2", "action": "update_task_status", "task_id": "t8", "task_title": "Site survey",
     "project_name": "P", "requested_by_name": "Mia Manager", "requested_at": "2026-09-23T10:00:00Z",
     "reason": "", "payload": {"status": "abandoned", "expected_revision": 1}},
]
CLOSE_REQUEST = [
    {"id": "r3", "action": "close_project", "task_id": None, "task_title": None, "project_name": "Harbour works",
     "requested_by_name": "Mia Manager", "requested_at": "2026-09-23T10:00:00Z", "reason": "All delivered",
     "payload": {"exceptional": False}},
]


# ARZWV7 round 2: a stricter stub that runs the dialog's real click/submit wiring. An id selector
# resolves only if that id is in index.html or in the markup renderDetail just wrote, so a handler
# that reaches for a missing element fails here the way it fails in a browser.
WIRING_DRIVER = r"""
const fs=require("fs");
const src=fs.readFileSync(process.argv[2],"utf8");
const indexIds=new Set([...fs.readFileSync(process.argv[3],"utf8").matchAll(/id="([^"]+)"/g)].map(m=>m[1]));
const scenarios=JSON.parse(fs.readFileSync(0,"utf8"));
const store={};let dyn={},nodes={};
const camel=s=>s.replace(/-([a-z])/g,(_,c)=>c.toUpperCase());
function el(init){
  const t={innerHTML:"",textContent:"",value:"",style:{},dataset:{},options:[],open:false,hidden:false,_l:{},...(init||{})};
  t.addEventListener=(k,f)=>{(t._l[k]=t._l[k]||[]).push(f)};
  t.classList={add(){},remove(){},toggle(){},contains(){return false}};
  t.querySelector=s=>document.querySelector(s);t.querySelectorAll=s=>document.querySelectorAll(s);
  t.insertAdjacentHTML=(pos,h)=>{t.innerHTML=pos==="afterbegin"?h+t.innerHTML:t.innerHTML+h};
  return new Proxy(t,{get(o,k){if(k===Symbol.toPrimitive)return()=>"";if(k in o)return o[k];return function(){return el()}},
    set(o,k,v){o[k]=v;if(k==="innerHTML"&&o.isBody){dyn={};nodes={}}return true}});
}
// 0D9Q3X: a message written as markup reads back as text, with its detail line after a newline.
globalThis.htmlText=h=>String(h||"").replace(/<small[^>]*>/g,"\n").replace(/<[^>]+>/g,"")
  .replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&amp;/g,"&");
function bodyHtml(){return ["#detail-body","#inbox-body"].map(k=>store[k]?store[k].innerHTML:"").join("")}
globalThis.bodyHtml=bodyHtml;
globalThis.__resetBodies=()=>{for(const k of ["#detail-body","#inbox-body"])if(store[k])store[k].innerHTML=""};
globalThis.document={
  querySelector(s){
    const m=/^#([\w-]+)$/.exec(s);
    if(!m)return el();
    if(s==="#detail-body"||s==="#inbox-body")return store[s]||(store[s]=el({isBody:true}));
    if(indexIds.has(m[1]))return store[s]||(store[s]=el());
    if(bodyHtml().includes(`id="${m[1]}"`))return dyn[m[1]]||(dyn[m[1]]=el());
    return null;
  },
  querySelectorAll(s){
    const m=/\[([\w-]+)\]$/.exec(s.split(",").pop().trim());if(!m)return[];
    const attr=m[1];if(nodes[attr])return nodes[attr];
    const found=[];
    for(const tag of bodyHtml().matchAll(new RegExp(`<\\w+[^>]*\\b${attr}="[^"]*"[^>]*>`,"g"))){
      const dataset={};for(const a of tag[0].matchAll(/data-([\w-]+)="([^"]*)"/g))dataset[camel(a[1])]=a[2];
      found.push(el({dataset,parentElement:{querySelector:()=>({value:globalThis.__reason||""})}}));
    }
    return nodes[attr]=found;
  },
  getElementById(s){return document.querySelector("#"+s)},createElement(){return el()},addEventListener(){},body:el(),documentElement:el()};
globalThis.window=globalThis;globalThis.addEventListener=()=>{};
globalThis.localStorage={getItem(){return null},setItem(){}};
globalThis.fetch=()=>new Promise(()=>{});
globalThis.Option=function(t,v){return{text:t,value:v}};
globalThis.FormData=function(form){return form.__entries||[]};
globalThis.location={hash:"",search:""};globalThis.history={replaceState(){}};
const harness=`;const realApi=api;
// 0D9Q3X: the real api() with a fake fetch, so the HTTP status it puts on a thrown error is pinned.
globalThis.__probeApi=async(status,body)=>{
  const savedFetch=globalThis.fetch;globalThis.fetch=async()=>({ok:status<400,status,json:async()=>body});
  try{return {ok:true,data:await realApi("/api/x",{method:"POST",body:"{}"})}}
  catch(e){return {ok:false,status:e.status??null,message:e.message}}
  finally{globalThis.fetch=savedFetch}};
globalThis.__run=async(sc)=>{
  if(sc.probe)return globalThis.__probeApi(sc.probe.status,sc.probe.body);
  const calls=[];
  __resetBodies();
  api=async(path,opts)=>{
    const method=opts&&opts.method;
    if(!method||method==="GET"){if(path.startsWith("/api/owner-action-requests"))calls.push({reloadInbox:true});
      return {notifications:[],unread:0,requests:sc.requestsAfter||sc.requests||[]}}
    calls.push({path,method,body:opts&&opts.body?JSON.parse(opts.body):null});
    if(sc.fail){const e=new Error(sc.fail);if(sc.status)e.status=sc.status;throw e}return {}};
  // 0D9Q3X: the reload re-renders, so a message written to the pre-reload node is lost here as in a browser.
  load=async()=>{calls.push({load:true})};openDetail=async()=>{calls.push({reload:true});
    if(sc.reloadFails){document.querySelector("#detail-body").innerHTML='<p class="error">Task not found.</p>';return null}
    renderDetail(sc.taskAfter||sc.task,[]);return sc.taskAfter||sc.task};
  globalThis.prompt=()=>sc.prompt??"";globalThis.alert=m=>{calls.push({alert:m})};
  globalThis.__reason=sc.reason||"";
  if(sc.requests){state.user={global_role:"owner"};state.loads=1;renderInbox([],sc.requests)}
  else{detailTaskId=sc.task.id;renderDetail(sc.task,[])}
  const pick=sc.click||sc.submitAt;
  // 5GK6SB: match the named attribute only, so data-remove-pred="t1" never matches data-remove-succ="t1".
  const key=pick&&pick[0].replace(/^data-/,"").replace(/-([a-z])/g,(_,c)=>c.toUpperCase());
  const target=pick?document.querySelectorAll("["+pick[0]+"]").find(n=>n.dataset[key]===pick[1])
    :document.querySelector(sc.submit||sc.button);
  if(sc.closeDetail){ // Close on a task opened from the inbox; loadsSince says whether anything was saved meanwhile
    const inbox=document.querySelector("#inbox-dialog");inbox.open=true;state.loads+=sc.closeDetail.loadsSince;calls.length=0;
    const handlers=document.querySelector("#detail-dialog")._l.close||[];await Promise.all(handlers.map(f=>f()));
    inbox.open=false;return {calls,threw:null,handlers:handlers.length,messages:{}};
  }
  if(!target)return {missing:true};
  await new Promise(r=>setTimeout(r,0));calls.length=0;
  if(sc.entries)target.__entries=sc.entries;
  const handlers=target._l[sc.submit||sc.submitAt?"submit":"click"]||[];
  let threw=null;
  try{await Promise.all(handlers.map(f=>f({target,preventDefault(){}})))}catch(e){threw=String(e)}
  const messages={};
  for(const m of bodyHtml().matchAll(/id="([\\w-]*(?:error|conflict))"/g)){const n=document.querySelector("#"+m[1]);const t=n&&(n.textContent||htmlText(n.innerHTML));if(t)messages[m[1]]=t}
  return {calls,threw,handlers:handlers.length,messages,html:sc.requests?bodyHtml():undefined};
};`;
(0,eval)(src+harness);
(async()=>{const out={};for(const [name,sc] of Object.entries(scenarios))out[name]=await globalThis.__run(sc);
  process.stdout.write(JSON.stringify(out))})().catch(e=>{console.error(e);process.exit(1)});
"""


class _StatusSelect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_select, self.disabled, self.options, self.found = False, None, [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "select" and a.get("name") == "status":
            self.in_select, self.found = True, True
            self.disabled = "disabled" in a or a.get("aria-disabled") == "true"
        elif tag == "option" and self.in_select:
            self.options.append(a.get("value"))
            self._pending = a.get("value") is None

    def handle_data(self, data):
        if self.in_select and getattr(self, "_pending", False):
            self.options[-1] = data.strip()
            self._pending = False

    def handle_endtag(self, tag):
        if tag == "select":
            self.in_select = False


def _status_select(markup):
    parser = _StatusSelect()
    parser.feed(markup)
    return parser


@unittest.skipUnless(shutil.which("node"), "node is needed to render app.js")
class AstraDetailDialogStatusGateTests(unittest.TestCase):
    """ARZWV7: the task dialog offers only edits the server accepts for the task's status."""

    @classmethod
    def setUpClass(cls):
        cases = {}
        for status in ("completed", "cancelled", "abandoned", "submitted", "in_progress"):
            cases[f"owner-{status}"] = _detail_task(status, OWNER_PERMS)
            cases[f"manager-{status}"] = _detail_task(status, MANAGER_PERMS)
        with tempfile.TemporaryDirectory() as tmp:
            driver = Path(tmp) / "driver.js"
            driver.write_text(DETAIL_DRIVER, encoding="utf-8")
            result = subprocess.run(
                ["node", str(driver), str(REPO / "src" / "astra" / "static" / "app.js")],
                input=json.dumps(cases), capture_output=True, text=True, timeout=60,
            )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        cls.html = json.loads(result.stdout)

    def test_closed_task_hides_refused_forms_and_says_reopen_first(self):
        for who in ("owner", "manager"):
            for status in ("completed", "cancelled", "abandoned"):
                with self.subTest(who=who, status=status):
                    html = self.html[f"{who}-{status}"]
                    self.assertIn("Reopen this task to change it", html)
                    self.assertIn('class="state-note"', html)
                    for refused in ('id="crit-form"', 'id="parent-form"', 'id="sched-form"', "data-approve-sched",
                                    'id="add-reviewer-button"', "data-remove-reviewer-user", 'id="add-dep-select"',
                                    'data-remove-pred="t0"', 'name="title"', 'name="due_date" type="date" value'):
                        self.assertNotIn(refused, html, refused)
                    # Still allowed on a closed task: reject a proposal, unlink a successor, read lists.
                    self.assertIn("data-reject-sched", html)
                    self.assertIn('data-remove-pred="t1"', html)
                    self.assertIn("Reviewer · approver", html)
                    self.assertIn("Current: <strong>high</strong>", html)
                    self.assertIn('data-life="reopen"', html)
                    self.assertIn('data-goto-reopen', html)
                    self.assertIn('id="dep-error"', html)  # the kept Remove (Blocks) has somewhere to report
                    self.assertNotIn("Go to ", html)

    def test_closed_task_keeps_attachments_and_final_result_marking_for_the_owner(self):
        for status in ("completed", "cancelled", "abandoned"):
            with self.subTest(status=status):
                html = self.html[f"owner-{status}"]
                self.assertIn('id="attachment-form"', html)
                self.assertIn('data-mark-fr-att="a1"', html)
                self.assertIn('data-remove-attachment="a1"', html)
                self.assertIn('>Reopen</button>', html)
        self.assertIn('data-mark-fr-sub="s1"', self.html["owner-completed"])
        self.assertIn("Request Owner reopening", self.html["manager-cancelled"])
        self.assertIn(">Reopen task…</button>", self.html["owner-completed"])
        self.assertIn(">Request reopening…</button>", self.html["manager-completed"])

    def test_manager_status_request_sits_under_reopen_as_the_alternative(self):
        for status in ("completed", "cancelled", "abandoned"):
            with self.subTest(status=status):
                html = self.html[f"manager-{status}"]
                lifecycle = html[html.index('<div class="lifecycle">'):html.index('<div class="reviewers">')]
                self.assertLess(lifecycle.index('id="reopen-form"'), lifecycle.index('id="detail-edit"'))
                self.assertIn("Or, instead of reopening, ask to move it straight back into work.", lifecycle)
                self.assertIn(">Request status change</button>", lifecycle)
                self.assertEqual(html.count('id="detail-edit"'), 1)

    def test_owner_on_a_closed_task_gets_no_status_select(self):
        for status in ("completed", "cancelled", "abandoned"):
            with self.subTest(status=status):
                self.assertFalse(_status_select(self.html[f"owner-{status}"]).found)

    def test_manager_on_a_closed_task_may_only_request_ordinary_work(self):
        for status in ("completed", "cancelled", "abandoned"):
            with self.subTest(status=status):
                select = _status_select(self.html[f"manager-{status}"])
                self.assertTrue(select.found)
                self.assertFalse(select.disabled)
                self.assertEqual([o for o in select.options if o], ["draft", "assigned", "in_progress", "delayed"])
                for never in ("cancelled", "abandoned", "changes_requested", "completed", "reopened", "on_hold"):
                    self.assertNotIn(never, select.options)

    def test_submitted_task_locks_status_and_points_to_the_decision(self):
        for who in ("owner", "manager"):
            with self.subTest(who=who):
                html = self.html[f"{who}-submitted"]
                select = _status_select(html)
                self.assertTrue(select.found)
                self.assertTrue(select.disabled)
                self.assertEqual(select.options, ["submitted"])
                self.assertIn('aria-disabled="true" aria-describedby="status-locked-hint"', html)
                self.assertNotIn(' disabled aria-describedby', html)  # aria-disabled keeps it focusable, so the hint is read
                self.assertIn('id="status-locked-hint"', html)
                self.assertIn('name="title"', html)  # the other fields still save on a submitted task
                self.assertIn('data-life="accept"', html)

    def test_submitted_hint_names_the_buttons_this_viewer_has(self):
        # 5GK6SB: a Manager's buttons ask the Owner; the hint must not send them looking for "Accept".
        expected = {"owner": ("Use Accept &amp; complete or Request changes under Lifecycle.",
                              ">Accept &amp; complete</button>", ">Request changes</button>"),
                    "manager": ("Use Request Owner acceptance or Request Owner to return changes under Lifecycle.",
                                ">Request Owner acceptance</button>", ">Request Owner to return changes</button>")}
        for who, (hint, *buttons) in expected.items():
            with self.subTest(who=who):
                html = self.html[f"{who}-submitted"]
                start = html.index('id="status-locked-hint"')
                self.assertIn(hint, html[start:html.index("</p>", start)])
                for button in buttons:
                    self.assertIn(button, html)
        html = self.html["manager-submitted"]
        start = html.index('id="status-locked-hint"')
        self.assertNotIn("Use Accept or Request changes", html[start:html.index("</p>", start)])

    def test_submitted_hint_sits_under_the_status_field(self):
        # 5GK6SB: the hint follows the Status select and comes before the next field in the grid.
        for who in ("owner", "manager"):
            with self.subTest(who=who):
                html = self.html[f"{who}-submitted"]
                edit = html[html.index('id="detail-edit"'):]
                grid = edit[edit.index('<div class="grid">'):]
                select_end = grid.index("</select>", grid.index('name="status"'))
                self.assertLess(select_end, grid.index('id="status-locked-hint"'))
                self.assertLess(grid.index('id="status-locked-hint"'), grid.index('name="start_date"'))

    def test_closed_statuses_are_listed_once(self):
        # 5GK6SB: buildLifecycle reuses CLOSED_STATUSES rather than a second copy that could drift.
        src = (REPO / "src" / "astra" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertEqual(src.count('["completed","cancelled","abandoned"]'), 1)
        self.assertIn("const closed=CLOSED_STATUSES.includes(task.status)", src[src.index("function buildLifecycle"):])

    def test_open_task_is_unchanged(self):
        html = self.html["owner-in_progress"]
        select = _status_select(html)
        self.assertEqual(select.options, ["draft", "assigned", "in_progress", "changes_requested",
                                          "delayed", "cancelled", "abandoned"])
        self.assertFalse(select.disabled)
        self.assertNotIn('class="state-note"', html)
        for form in ('id="crit-form"', 'id="parent-form"', 'id="sched-form"', 'id="add-reviewer-button"',
                     'id="add-dep-select"', 'id="detail-edit"'):
            self.assertIn(form, html)


@unittest.skipUnless(shutil.which("node"), "node is needed to run app.js")
class AstraDetailDialogWiringTests(unittest.TestCase):
    """ARZWV7: the controls a closed or submitted task keeps still work when clicked."""

    @classmethod
    def setUpClass(cls):
        owner_done, manager_done = _detail_task("completed", OWNER_PERMS), _detail_task("completed", MANAGER_PERMS)
        owner_open, owner_submitted = _detail_task("in_progress", OWNER_PERMS), _detail_task("submitted", OWNER_PERMS)
        scenarios = {
            "unlink-successor-closed": {"task": owner_done, "click": ["data-remove-pred", "t1"], "reason": "not needed"},
            "unlink-successor-closed-refused": {"task": owner_done, "click": ["data-remove-pred", "t1"],
                                                "fail": "A reason is required."},
            "unlink-predecessor-open": {"task": owner_open, "click": ["data-remove-pred", "t0"], "reason": "wrong link"},
            # 5GK6SB: on an open t1 the incoming Remove carries data-remove-succ="t1"; the click must not land there.
            "unlink-successor-open": {"task": owner_open, "click": ["data-remove-pred", "t1"], "reason": "not needed"},
            "add-predecessor-open-empty": {"task": owner_open, "button": "#add-dep-button"},
            "reject-proposal-closed-refused": {"task": owner_done, "click": ["data-reject-sched", "sp1"],
                                               "fail": "A reason is required."},
            "save-submitted": {"task": owner_submitted, "submit": "#detail-edit",
                               "entries": [["expected_revision", "3"], ["title", "Renamed"], ["status", "submitted"],
                                           ["reason", ""]]},
            "manager-request-closed": {"task": manager_done, "submit": "#detail-edit",
                                       "entries": [["expected_revision", "3"], ["status", "in_progress"],
                                                   ["reason", "more work found"]]},
            # 0D9Q3X: a 409 reloads the task; any other refusal keeps the form and the server's message.
            "save-conflict": {"task": owner_open, "submit": "#detail-edit", "status": 409,
                              "fail": "Task revision conflict: expected 3, current revision is 4.",
                              "entries": [["expected_revision", "3"], ["title", "Renamed"]]},
            "save-refused": {"task": owner_open, "submit": "#detail-edit", "status": 400,
                             "fail": "A reason is required.", "entries": [["expected_revision", "3"], ["title", "X"]]},
            "submit-conflict": {"task": owner_open, "submitAt": ["data-life", "submit"], "status": 409,
                                "fail": "Task revision conflict.", "entries": [["note", "done"]]},
            "inbox-decision-conflict": {"requests": INBOX_REQUESTS, "click": ["data-request-decision", "approved"],
                                        "prompt": "ok", "status": 409,
                                        "fail": "Task revision conflict: request expected 1, current revision is 2."},
            "inbox-decision-refused": {"requests": INBOX_REQUESTS, "click": ["data-request-decision", "approved"],
                                       "prompt": "ok", "status": 400, "fail": "Owner cannot do that."},
            # 0D9Q3X round 2: the plain line names what to do; the server's reason follows it.
            "inbox-decision-conflict-gone": {"requests": INBOX_REQUESTS, "requestsAfter": INBOX_REQUESTS[1:],
                                             "click": ["data-request-decision", "approved"], "prompt": "ok",
                                             "status": 409,
                                             "fail": "Owner-action request conflict: this request has already been decided."},
            "inbox-close-project-conflict": {"requests": CLOSE_REQUEST, "click": ["data-request-decision", "approved"],
                                             "prompt": "ok", "status": 409,
                                             "fail": "Project closure conflict: the project's open work changed since "
                                                     "this close was requested; review and decide again."},
            "submit-conflict-now-closed": {"task": owner_open, "taskAfter": _detail_task("cancelled", OWNER_PERMS),
                                           "submitAt": ["data-life", "submit"], "status": 409,
                                           "fail": "Task revision conflict.", "entries": [["note", "done"]]},
            "save-conflict-reload-fails": {"task": owner_open, "submit": "#detail-edit", "status": 409,
                                           "reloadFails": True, "fail": "Submission conflict: your access changed.",
                                           "entries": [["expected_revision", "3"], ["title", "Renamed"]]},
            "api-409": {"probe": {"status": 409, "body": {"error": "Task revision conflict."}}},
            "api-ok": {"probe": {"status": 200, "body": {"task": {"id": "t1"}}}},
            "close-task-after-save": {"requests": INBOX_REQUESTS, "closeDetail": {"loadsSince": 1}},
            "close-task-unchanged": {"requests": INBOX_REQUESTS, "closeDetail": {"loadsSince": 0}},
        }
        with tempfile.TemporaryDirectory() as tmp:
            driver = Path(tmp) / "wiring.js"
            driver.write_text(WIRING_DRIVER, encoding="utf-8")
            static = REPO / "src" / "astra" / "static"
            result = subprocess.run(["node", str(driver), str(static / "app.js"), str(static / "index.html")],
                                    input=json.dumps(scenarios), capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        cls.out = json.loads(result.stdout)

    def _ran(self, name):
        run = self.out[name]
        self.assertFalse(run.get("missing"), f"{name}: control not rendered")
        self.assertGreater(run["handlers"], 0, f"{name}: control not wired")
        self.assertIsNone(run["threw"], f"{name}: {run['threw']}")
        return run

    def test_unlinking_a_successor_on_a_closed_task_sends_the_request(self):
        run = self._ran("unlink-successor-closed")
        self.assertEqual(run["calls"][0], {"path": "/api/task-dependencies", "method": "DELETE",
                                           "body": {"predecessor_task_id": "t1", "successor_task_id": "t2",
                                                    "reason": "not needed"}})
        self.assertIn({"reload": True}, run["calls"])

    def test_a_refused_unlink_on_a_closed_task_shows_the_reason(self):
        run = self._ran("unlink-successor-closed-refused")
        self.assertIn("A reason is required.", run["messages"].values())

    def test_dependency_controls_on_an_open_task_still_work(self):
        run = self._ran("unlink-predecessor-open")
        self.assertEqual(run["calls"][0]["body"]["predecessor_task_id"], "t0")
        run = self._ran("unlink-successor-open")
        self.assertEqual(run["calls"][0]["body"], {"predecessor_task_id": "t1", "successor_task_id": "t2",
                                                   "reason": "not needed"})
        run = self._ran("add-predecessor-open-empty")
        self.assertEqual(run["calls"], [])
        self.assertIn("Choose a predecessor task.", run["messages"].values())

    def test_a_refused_proposal_rejection_on_a_closed_task_shows_the_reason(self):
        run = self._ran("reject-proposal-closed-refused")
        self.assertEqual(run["calls"][0]["path"], "/api/schedule-proposals/sp1/reject")
        self.assertIn("A reason is required.", run["messages"].values())

    def test_saving_a_submitted_task_leaves_the_locked_status_out(self):
        run = self._ran("save-submitted")
        body = run["calls"][0]["body"]
        self.assertEqual(body["title"], "Renamed")
        self.assertNotIn("status", body)

    def test_manager_status_request_on_a_closed_task_sends_the_status(self):
        run = self._ran("manager-request-closed")
        self.assertEqual(run["calls"][0]["body"]["status"], "in_progress")

    def test_a_conflicting_save_reloads_the_task_and_says_it_changed(self):
        run = self._ran("save-conflict")
        self.assertEqual(run["calls"][0]["path"], "/api/tasks/t1")
        self.assertIn({"load": True}, run["calls"])
        self.assertIn({"reload": True}, run["calls"])
        self.assertIn(CONFLICT_TEXT, run["messages"].get("detail-edit-error", ""))

    def test_a_conflicting_submit_reloads_the_task_and_says_it_changed(self):
        run = self._ran("submit-conflict")
        self.assertEqual(run["calls"][0]["path"], "/api/tasks/t1/submit")
        self.assertIn({"reload": True}, run["calls"])
        self.assertIn(CONFLICT_TEXT, run["messages"].get("lifecycle-error", ""))

    def test_a_conflict_keeps_the_servers_reason_under_the_plain_line(self):
        self.assertIn(".error .conflict-detail { display: block;", (STATIC / "style.css").read_text(encoding="utf-8"))
        message = self._ran("save-conflict")["messages"]["detail-edit-error"]
        self.assertEqual(message.split("\n"), [
            "This task changed since you opened it, so nothing was saved. It now shows the latest version; "
            "check it and try again.",
            "Task revision conflict: expected 3, current revision is 4."])

    def test_a_conflict_that_leaves_the_task_read_only_does_not_say_try_again(self):
        message = self._ran("submit-conflict-now-closed")["messages"].get("lifecycle-error", "")
        self.assertIn("It is now Cancelled; this is the latest version.", message)
        self.assertNotIn("try again", message)
        self.assertIn("Task revision conflict.", message)

    def test_a_conflict_whose_reload_fails_does_not_claim_the_latest_is_shown(self):
        run = self._ran("save-conflict-reload-fails")
        message = run["messages"].get("detail-conflict", "")
        self.assertIn("It could not be reloaded.", message)
        self.assertNotIn("latest version", message)
        self.assertIn("Submission conflict: your access changed.", message)

    def test_a_stale_request_still_listed_says_reject_or_cancel_it(self):
        message = self._ran("inbox-decision-conflict")["messages"]["inbox-error"]
        first, detail = message.split("\n")
        self.assertIn("Status change · Vendor shortlist", first)
        self.assertIn("can no longer be approved", first)
        self.assertIn("Reject or cancel it.", first)
        self.assertEqual(detail, "Task revision conflict: request expected 1, current revision is 2.")

    def test_a_request_decided_elsewhere_says_nothing_was_decided(self):
        message = self._ran("inbox-decision-conflict-gone")["messages"]["inbox-error"]
        self.assertIn("nothing was decided", message)
        self.assertNotIn("Reject or cancel", message)
        self.assertIn("this request has already been decided", message)

    def test_a_project_close_conflict_keeps_its_reason_and_does_not_mention_a_task(self):
        run = self._ran("inbox-close-project-conflict")
        message = run["messages"]["inbox-error"]
        self.assertIn("Close project · Harbour works", message)
        self.assertIn("the project's open work changed since this close was requested", message)
        self.assertNotIn("task", message.split("\n")[0].lower())
        self.assertNotIn("data-detail=", run["html"])  # no Open task link on a project request

    def test_api_puts_the_http_status_on_a_thrown_error(self):
        self.assertEqual(self.out["api-409"], {"ok": False, "status": 409, "message": "Task revision conflict."})
        self.assertEqual(self.out["api-ok"], {"ok": True, "data": {"task": {"id": "t1"}}})

    def test_closing_a_task_opened_from_the_inbox_refreshes_the_inbox_only_after_a_save(self):
        self.assertIn({"reloadInbox": True}, self._ran("close-task-after-save")["calls"])
        self.assertNotIn({"reloadInbox": True}, self._ran("close-task-unchanged")["calls"])

    def test_any_other_refusal_keeps_the_form_and_the_servers_message(self):
        run = self._ran("save-refused")
        self.assertNotIn({"reload": True}, run["calls"])
        self.assertEqual(run["messages"].get("detail-edit-error"), "A reason is required.")

    def test_a_conflicting_inbox_decision_reloads_the_inbox_and_says_it_changed(self):
        run = self._ran("inbox-decision-conflict")
        self.assertEqual(run["calls"][0]["path"], "/api/owner-action-requests/r1/decision")
        self.assertIn({"load": True}, run["calls"])
        self.assertIn({"reloadInbox": True}, run["calls"])
        self.assertFalse([c for c in run["calls"] if "alert" in c])
        self.assertIn("can no longer be approved", run["messages"].get("inbox-error", ""))

    def test_a_refused_inbox_decision_shows_the_reason_inline(self):
        run = self._ran("inbox-decision-refused")
        self.assertNotIn({"reloadInbox": True}, run["calls"])
        self.assertFalse([c for c in run["calls"] if "alert" in c])
        self.assertEqual(run["messages"].get("inbox-error"), "Owner cannot do that.")

    def test_no_reason_given_is_muted_inside_a_request(self):
        css = (STATIC / "style.css").read_text(encoding="utf-8")
        self.assertIn(".owner-request .request-detail p.muted { color: #667085; }", css)

    def test_inbox_request_shows_target_status_from_status_and_reason_escaped(self):
        html = self._ran("inbox-decision-refused")["html"]
        self.assertIn("Change status from <strong>Cancelled</strong> to <strong>In progress</strong>", html)
        self.assertIn("Change status to <strong>Abandoned</strong>", html)
        self.assertIn("Reason: Client withdrew &lt;b&gt;the site&lt;/b&gt;", html)
        self.assertNotIn("<b>the site</b>", html)
        self.assertIn("No reason given.", html)
        self.assertIn('data-detail="t9"', html)  # Open task, to check it before deciding


FINAL_RESULTS_DRIVER = r"""
const fs=require("fs");
const src=fs.readFileSync(process.argv[2],"utf8");
const store={};globalThis.__anchors=[];
function el(init){
  const t={innerHTML:"",textContent:"",value:"",style:{},dataset:{},open:false,hidden:false,_l:{},...(init||{})};
  t.addEventListener=(k,f)=>{(t._l[k]=t._l[k]||[]).push(f)};
  t.classList={add(){},remove(){},toggle(){},contains(){return false}};
  t.showModal=()=>{t.open=true};t.close=()=>{t.open=false};
  return new Proxy(t,{get(o,k){if(k===Symbol.toPrimitive)return()=>"";if(k in o)return o[k];return function(){return el()}}});
}
globalThis.document={querySelector(s){return store[s]||(store[s]=el())},querySelectorAll(){return[]},
  getElementById(s){return document.querySelector("#"+s)},
  createElement(){const a=el();globalThis.__anchors.push(a);return a},addEventListener(){},body:el(),documentElement:el()};
globalThis.window=globalThis;globalThis.addEventListener=()=>{};
globalThis.localStorage={getItem(){return null},setItem(){}};
globalThis.fetch=()=>new Promise(()=>{});
globalThis.location={hash:"",search:""};globalThis.history={replaceState(){}};
const harness=`;globalThis.__run=async(sc)=>{
  const calls=[];api=async(path)=>{calls.push(path);return {results:[]}};
  renderFinalResults([],sc.initial||{});
  const html=document.querySelector("#final-results-body").innerHTML;
  for(const [id,v] of Object.entries(sc.values||{}))document.querySelector("#"+id).value=v;
  await document.querySelector("#fr-apply").onclick();
  const afterApply=document.querySelector("#final-results-body").innerHTML;
  document.querySelector("#fr-export").onclick();
  return {html,afterApply,calls,exportHref:__anchors.length?__anchors[__anchors.length-1].href:null};
};`;
(0,eval)(src+harness);
(async()=>{const sc=JSON.parse(fs.readFileSync(0,"utf8"));process.stdout.write(JSON.stringify(await globalThis.__run(sc)))})()
  .catch(e=>{console.error(e);process.exit(1)});
"""


@unittest.skipUnless(shutil.which("node"), "node is needed to run app.js")
class AstraFinalResultsDialogTests(unittest.TestCase):
    """CS93C6 review gap 2: the Final results dialog filters by marked date, and Export CSV
    carries the same date range as the list."""

    def _run(self, scenario):
        with tempfile.TemporaryDirectory() as tmp:
            driver = Path(tmp) / "final_results.js"
            driver.write_text(FINAL_RESULTS_DRIVER, encoding="utf-8")
            result = subprocess.run(["node", str(driver), str(REPO / "src" / "astra" / "static" / "app.js")],
                                    input=json.dumps(scenario), capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_date_range_is_sent_by_filter_and_by_export(self):
        out = self._run({"values": {"fr-project": "", "fr-entity": "", "fr-type": "attachment",
                                    "fr-from": "2026-04-01", "fr-to": "2026-04-30", "fr-q": ""}})
        self.assertRegex(out["html"], r'<input id="fr-from" type="date"')
        self.assertRegex(out["html"], r'<input id="fr-to" type="date"')
        self.assertIn("Marked from", out["html"])
        self.assertEqual(out["calls"], ["/api/final-results?type=attachment&from=2026-04-01&to=2026-04-30"])
        self.assertEqual(out["exportHref"], "/api/final-results?type=attachment&from=2026-04-01&to=2026-04-30&format=csv")

    def test_applied_dates_stay_in_the_inputs_after_filtering(self):
        out = self._run({"initial": {"from": "2026-04-01", "to": "2026-04-30"},
                         "values": {"fr-project": "", "fr-entity": "", "fr-type": "",
                                    "fr-from": "2026-05-01", "fr-to": "", "fr-q": ""}})
        self.assertIn('id="fr-from" type="date" value="2026-04-01"', out["html"])
        self.assertIn('id="fr-to" type="date" value="2026-04-30"', out["html"])
        self.assertEqual(out["calls"], ["/api/final-results?from=2026-05-01"])
        self.assertIn('id="fr-from" type="date" value="2026-05-01"', out["afterApply"])
        self.assertIn('id="fr-to" type="date" value=""', out["afterApply"])


if __name__ == "__main__":
    unittest.main()
