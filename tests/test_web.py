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
from unittest import mock
from html.parser import HTMLParser
from importlib.resources import files
from pathlib import Path

from astra.web import AstraHandler, AstraServer

from link_roots import allow_attachment_roots, link

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
        allow_attachment_roots(self)
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

    def _get_bytes(self, path):
        self.connection.request("GET", path)
        response = self.connection.getresponse()
        return response, response.read()

    def test_favicon_is_a_small_svg_on_the_static_allowlist(self):
        # 3C1Z74: no more favicon 404 in the console; the icon is one allowlisted SVG with no script.
        response, body = self._get_bytes("/static/favicon.svg")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Type"), "image/svg+xml")
        self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
        self.assertIn("default-src 'self'", response.getheader("Content-Security-Policy"))
        self.assertTrue(body.startswith(b"<svg "))
        self.assertLess(len(body), 1024)
        self.assertNotIn(b"<script", body.lower())
        self.assertNotIn(b"href", body)
        for path in ("/static/favicon.ico", "/static/Favicon.svg", "/static/favicon.svg/"):
            self.assertEqual(self._get_bytes(path)[0].status, 404, path)
        _, page = self._get_bytes("/")
        self.assertIn(b'<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">', page)

    def test_inter_font_is_served_by_astra_with_strict_allowlist_and_caching(self):
        # 4T4DEA: the page needs no third-party origin; the versioned font files cache for a year.
        for name in ("inter-latin-4.001.woff2", "inter-latin-ext-4.001.woff2"):
            response, body = self._get_bytes(f"/static/fonts/{name}")
            self.assertEqual(response.status, 200, name)
            self.assertEqual(response.getheader("Content-Type"), "font/woff2")
            self.assertEqual(response.getheader("Cache-Control"), "public, max-age=31536000, immutable")
            self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
            self.assertEqual(body[:4], b"wOF2")
            self.assertEqual(int(response.getheader("Content-Length")), len(body))
        response, body = self._get_bytes("/static/fonts/Inter-OFL.txt")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
        self.assertIn(b"SIL Open Font License, Version 1.1", body)
        for path in ("/static/fonts/", "/static/fonts/other.woff2", "/static/fonts/%2e%2e/app.js",
                     "/static/fonts/../web.py", "/static/inter-latin-4.001.woff2", "/static/FONTS/Inter-OFL.txt",
                     "/static/fonts/inter-latin-4.001.woff2/"):
            response, _ = self._get_bytes(path)
            self.assertEqual(response.status, 404, path)
        response, _ = self._get_bytes("/")
        csp = response.getheader("Content-Security-Policy")
        self.assertIn("font-src 'self'", csp)
        self.assertIn("style-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertEqual(response.getheader("Cache-Control"), "no-cache")

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

    def test_export_applies_the_home_tile_filters(self):
        # VPYGY5: the Risk filter and "No due date" behind the Home tiles narrow the export the same way.
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Tiles"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        _, first = self.request("POST", "/api/tasks", {"project_id": pid, "title": "First", "due_date": "2099-01-01"}, cookie=cookie, csrf=csrf)
        _, second = self.request("POST", "/api/tasks", {"project_id": pid, "title": "Second", "due_date": "2099-02-01"}, cookie=cookie, csrf=csrf)
        self.request("POST", "/api/tasks", {"project_id": pid, "title": "Undated"}, cookie=cookie, csrf=csrf)
        self.request("POST", "/api/task-dependencies", {"predecessor_task_id": first["task"]["id"],
                                                        "successor_task_id": second["task"]["id"]}, cookie=cookie, csrf=csrf)
        titles = lambda q: sorted(t["title"] for t in self.request("GET", f"/api/export?project_id={pid}&{q}", cookie=cookie)[1]["export"]["tasks"])
        self.assertEqual(titles("band=undated"), ["Undated"])
        self.assertEqual(titles("risk=blocked"), ["Second"])
        self.assertIn("Second", titles("risk=atrisk"))
        self.assertNotIn("Undated", titles("risk=atrisk"))
        self.connection.request("GET", f"/api/export?project_id={pid}&risk=blocked&format=csv", None, {"Cookie": cookie})
        response = self.connection.getresponse()
        self.assertIn("__risk=blocked", response.getheader("Content-Disposition"))
        response.read()
        # Review L4: an unknown risk value narrows nothing and is not named in the filename.
        self.assertEqual(titles("risk=anything"), ["First", "Second", "Undated"])
        self.connection.request("GET", f"/api/export?project_id={pid}&risk=anything&format=csv", None, {"Cookie": cookie})
        response = self.connection.getresponse()
        self.assertNotIn("risk", response.getheader("Content-Disposition"))
        response.read()

    def test_tasks_and_projects_carry_the_servers_today(self):
        # FKVHH8 review M1: Home, My Work and the calendar read "today" from the server, never the browser.
        from datetime import datetime
        from zoneinfo import ZoneInfo
        cookie, csrf = self._owner_session()
        self.request("POST", "/api/projects", {"name": "Clock", "timezone": "Pacific/Pago_Pago"}, cookie=cookie, csrf=csrf)
        karachi = lambda: datetime.now(ZoneInfo("Asia/Karachi")).date().isoformat()
        before = karachi()
        _, tasks = self.request("GET", "/api/tasks", cookie=cookie)
        self.assertIn(tasks["today"], {before, karachi()})  # both sides of a midnight during the request
        self.assertEqual(tasks["timezone"], "Asia/Karachi")  # lock #11 review L3: the real field, not a stub
        _, projects = self.request("GET", "/api/projects", cookie=cookie)
        clock = next(p for p in projects["projects"] if p["name"] == "Clock")
        self.assertEqual(clock["today"], datetime.now(ZoneInfo(clock["timezone"])).date().isoformat())

    def test_export_risk_rules_each_on_their_own(self):
        # Review L3: one task per rule, so each filter is proven by a task that only it matches.
        from astra.service import AstraService
        svc = AstraService.__new__(AstraService)
        base = {"project_id": "p", "status": "in_progress", "due_state": "scheduled", "is_blocked": False, "is_critical_path": False}
        tasks = [{**base, "title": "Only blocked", "is_blocked": True}, {**base, "title": "Only critical", "is_critical_path": True},
                 {**base, "title": "Only delayed", "status": "delayed"}, {**base, "title": "Only overdue", "due_state": "overdue"},
                 {**base, "title": "Healthy"}]
        svc.list_tasks = lambda actor, project=None, sort="criticality": [dict(t) for t in tasks]
        titles = lambda risk: sorted(t["title"] for t in svc.export_tasks({"id": "u"}, {"risk": risk})["tasks"])
        self.assertEqual(titles("blocked"), ["Only blocked"])
        self.assertEqual(titles("critical"), ["Only critical"])
        self.assertEqual(titles("atrisk"), ["Only blocked", "Only critical", "Only delayed", "Only overdue"])
        self.assertEqual(len(titles("anything")), 5)
        self.assertIsNone(svc.export_tasks({"id": "u"}, {"risk": "anything"})["filters"]["risk"])

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
        _, attachment = self.request("POST", f"/api/tasks/{task_id}/attachments", {"path": link("out", "final.pdf")}, cookie=cookie, csrf=csrf)
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

    def test_repeated_failures_never_lock_anyone_out(self):
        # 3M2AYA (Aly, Slack ts 1790279102.044719): just say the password is incorrect.
        for _ in range(21):
            response, payload = self.request("POST", "/api/login", {
                "email": "owner@example.org", "password": "wrong password guess",
            })
            self.assertEqual(response.status, 401)
            self.assertEqual(payload["error"], "Incorrect email or password.")
        response, payload = self.request("POST", "/api/login", {
            "email": "nobody@example.org", "password": "anything at all",
        })
        self.assertEqual((response.status, payload["error"]), (401, "Incorrect email or password."))
        response, payload = self.request("POST", "/api/login", {
            "email": "owner@example.org", "password": "correct horse battery",
        })
        self.assertEqual(response.status, 200)
        self.assertEqual(payload["user"]["email"], "owner@example.org")

    def test_unknown_and_long_emails_are_checked_against_a_dummy_hash(self):
        # Review 8 L1/M1: the same 401 and the same PBKDF2 work whether or not the email exists.
        from astra import web as web_module
        from astra.auth import dummy_password_hash
        seen = []
        real_verify = web_module.verify_password

        def spy(password, encoded):
            seen.append(encoded)
            return real_verify(password, encoded)

        with mock.patch.object(web_module, "verify_password", side_effect=spy):
            for email in ("nobody@example.org", "y" * 400 + "@example.org"):
                response, payload = self.request("POST", "/api/login", {"email": email, "password": "some guess"})
                self.assertEqual((response.status, payload["error"]), (401, "Incorrect email or password."))
            response, payload = self.request("POST", "/api/login", {"email": "owner@example.org", "password": 12345})
            self.assertEqual((response.status, payload["error"]), (401, "Incorrect email or password."))
        self.assertEqual(seen[:2], [dummy_password_hash()] * 2)
        self.assertNotEqual(seen[2], dummy_password_hash())  # a real account uses its own hash

    def test_owner_resets_a_password_over_http(self):
        owner_cookie, owner_csrf = self._owner_session()
        _, created = self.request("POST", "/api/users", {
            "email": "forgot@example.org", "display_name": "Forgot", "password": "old password",
            "role": "member"}, cookie=owner_cookie, csrf=owner_csrf)
        user_id = created["user"]["id"]
        response, member_login = self.request("POST", "/api/login", {"email": "forgot@example.org",
                                                                     "password": "old password"})
        member_cookie = response.getheader("Set-Cookie").split(";", 1)[0]
        for csrf in (None, "wrong-token"):
            response, _ = self.request("POST", f"/api/users/{user_id}/password", {"password": "new pass 8"},
                                       cookie=owner_cookie, csrf=csrf)
            self.assertEqual(response.status, 403)
        response, payload = self.request("POST", f"/api/users/{user_id}/password", {"password": "1234567"},
                                         cookie=owner_cookie, csrf=owner_csrf)
        self.assertEqual((response.status, payload["error"]), (400, "Password must contain at least 8 characters."))
        for value in (12345678, [1, 2, 3, 4, 5, 6, 7, 8]):
            response, payload = self.request("POST", f"/api/users/{user_id}/password", {"password": value},
                                             cookie=owner_cookie, csrf=owner_csrf)
            self.assertEqual((response.status, payload["error"]), (400, "Password must be text."))
        response, payload = self.request("POST", f"/api/users/{user_id}/password", {"password": "new pass 8"},
                                         cookie=member_cookie, csrf=member_login["csrf"])
        self.assertEqual(response.status, 403)  # a member cannot reset anyone
        response, payload = self.request("POST", f"/api/users/{user_id}/password", {"password": "new pass 8"},
                                         cookie=owner_cookie, csrf=owner_csrf)
        self.assertEqual(response.status, 200)
        self.assertNotIn("password", json.dumps(payload).replace("password_", ""))
        response, _ = self.request("GET", "/api/tasks", cookie=member_cookie)
        self.assertEqual(response.status, 403)  # the member's session was revoked
        response, _ = self.request("POST", "/api/login", {"email": "forgot@example.org", "password": "new pass 8"})
        self.assertEqual(response.status, 200)
        response, _ = self.request("POST", "/api/users/no-such-user/password",
                                   {"password": "new pass 8"}, cookie=owner_cookie, csrf=owner_csrf)
        self.assertEqual(response.status, 404)
        # Resetting your own password keeps the session you are using.
        _, me = self.request("GET", "/api/me", cookie=owner_cookie)
        response, _ = self.request("POST", f"/api/users/{me['user']['id']}/password", {"password": "owner new 8"},
                                   cookie=owner_cookie, csrf=owner_csrf)
        self.assertEqual(response.status, 200)
        response, _ = self.request("GET", "/api/tasks", cookie=owner_cookie)
        self.assertEqual(response.status, 200)
        _, audit = self.request("GET", "/api/user-events", cookie=owner_cookie)
        resets = [e for e in audit["events"] if e["event_type"] == "password_reset"]
        self.assertEqual([e["reason"] for e in resets], ["in app", "in app"])

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
            "path": link("reports", "audit-memo.pdf"), "note": "Board copy",
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
            "path": link("evidence", "owner.pdf"),
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
            "path": link("evidence", "manager.pdf"),
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

    # 6G89SJ (Owner decision 2026-09-19, Item 4): attachment denials proven over HTTP.
    def _attachment_fixture(self, name):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": name}, cookie=cookie, csrf=csrf)
        project_id = project["project"]["id"]
        _, task = self.request("POST", "/api/tasks", {"project_id": project_id, "title": f"{name} task"},
                               cookie=cookie, csrf=csrf)
        task_id = task["task"]["id"]
        response, added = self.request("POST", f"/api/tasks/{task_id}/attachments", {"path": link(name, "memo.pdf")},
                                       cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        return cookie, csrf, project_id, task_id, added["attachment"]["id"]

    def _user_session(self, owner_cookie, owner_csrf, key, global_role, project_id=None, project_role=None):
        password = f"{key} password safe"
        _, created = self.request("POST", "/api/users", {
            "email": f"{key}@example.org", "display_name": key.title(), "password": password, "role": global_role,
        }, cookie=owner_cookie, csrf=owner_csrf)
        if project_role:
            self.request("POST", "/api/project-access", {
                "project_id": project_id, "user_id": created["user"]["id"], "role": project_role,
            }, cookie=owner_cookie, csrf=owner_csrf)
        response, login = self.request("POST", "/api/login", {"email": f"{key}@example.org", "password": password})
        self.assertEqual(response.status, 200)
        return response.getheader("Set-Cookie").split(";", 1)[0], login["csrf"]

    def test_attachment_authorization_matrix_over_http(self):
        owner_cookie, owner_csrf, project_id, task_id, attachment_id = self._attachment_fixture("Matrix")
        sessions = {
            "viewer": self._user_session(owner_cookie, owner_csrf, "att-viewer", "member", project_id, "viewer"),
            "chairman": self._user_session(owner_cookie, owner_csrf, "att-chair", "chairman"),
            "outsider": self._user_session(owner_cookie, owner_csrf, "att-outsider", "member"),
        }
        expected_read = {"viewer": 200, "chairman": 200, "outsider": 403}
        for who, (cookie, csrf) in sessions.items():
            with self.subTest(who=who):
                response, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=cookie)
                self.assertEqual(response.status, expected_read[who])
                if response.status == 200:
                    self.assertEqual([a["id"] for a in detail["task"]["attachments"]], [attachment_id])
                    self.assertFalse(detail["task"]["permissions"]["can_manage_files"])
                else:
                    self.assertNotIn("task", detail)
                response, _ = self.request("POST", f"/api/tasks/{task_id}/attachments",
                                           {"path": link("Matrix", f"{who}.pdf")}, cookie=cookie, csrf=csrf)
                self.assertEqual(response.status, 403)
                response, _ = self.request("DELETE", "/api/task-attachments",
                                           {"task_id": task_id, "attachment_id": attachment_id}, cookie=cookie, csrf=csrf)
                self.assertEqual(response.status, 403)
        response, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=owner_cookie)
        self.assertEqual([a["id"] for a in detail["task"]["attachments"]], [attachment_id])

    def test_attachment_mutations_reject_missing_and_wrong_csrf(self):
        owner_cookie, owner_csrf, project_id, task_id, attachment_id = self._attachment_fixture("Tokens")
        _, other_csrf = self._user_session(owner_cookie, owner_csrf, "att-token", "member", project_id, "viewer")
        for label, token in (("missing", None), ("wrong", "not-the-token"), ("another session's", other_csrf)):
            with self.subTest(token=label):
                response, payload = self.request("POST", f"/api/tasks/{task_id}/attachments",
                                                 {"path": link("Tokens", "forged.pdf")}, cookie=owner_cookie, csrf=token)
                self.assertEqual(response.status, 403)
                self.assertIn("request token", payload["error"])
                response, payload = self.request("DELETE", "/api/task-attachments",
                                                 {"task_id": task_id, "attachment_id": attachment_id},
                                                 cookie=owner_cookie, csrf=token)
                self.assertEqual(response.status, 403)
                self.assertIn("request token", payload["error"])
        response, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=owner_cookie)
        self.assertEqual([a["id"] for a in detail["task"]["attachments"]], [attachment_id])

    def test_attachment_removal_needs_the_matching_task(self):
        cookie, csrf, project_id, task_id, attachment_id = self._attachment_fixture("Pairing")
        _, other = self.request("POST", "/api/tasks", {"project_id": project_id, "title": "Other task"},
                                cookie=cookie, csrf=csrf)
        for body in ({"task_id": other["task"]["id"], "attachment_id": attachment_id},
                     {"task_id": task_id, "attachment_id": "no-such-attachment"}):
            with self.subTest(body=body):
                response, _ = self.request("DELETE", "/api/task-attachments", body, cookie=cookie, csrf=csrf)
                self.assertEqual(response.status, 404)
        response, _ = self.request("POST", "/api/tasks/no-such-task/attachments", {"path": link("Pairing", "x.pdf")},
                                   cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 404)
        response, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=cookie)
        self.assertEqual([a["id"] for a in detail["task"]["attachments"]], [attachment_id])

    def test_attachment_marked_as_final_result_is_not_removed_over_http(self):
        cookie, csrf, _, task_id, attachment_id = self._attachment_fixture("Kept")
        response, marked = self.request("POST", "/api/final-results", {
            "task_id": task_id, "source_type": "attachment", "source_id": attachment_id,
        }, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 201)
        response, payload = self.request("DELETE", "/api/task-attachments",
                                         {"task_id": task_id, "attachment_id": attachment_id}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 409)
        self.assertEqual(payload["error"], "Unmark the final result first.")
        response, listed = self.request("GET", "/api/final-results", cookie=cookie)
        self.assertEqual([r["id"] for r in listed["results"]], [marked["result"]["id"]])
        response, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=cookie)
        self.assertEqual([a["id"] for a in detail["task"]["attachments"]], [attachment_id])
        response, _ = self.request("DELETE", "/api/final-results", {"result_id": marked["result"]["id"]},
                                   cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        response, _ = self.request("DELETE", "/api/task-attachments",
                                   {"task_id": task_id, "attachment_id": attachment_id}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)

    def test_attachment_path_outside_the_rules_is_rejected_over_http(self):
        cookie, csrf, _, task_id, attachment_id = self._attachment_fixture("Rules")
        for path, message in ((r"\\server\share\memo.pdf", "UNC"), ("https://example.org/memo.pdf", "URL"),
                              ("memo.pdf", "full path"), (link("Rules", "..", "..", "memo.pdf"), r"'\.\.'"),
                              (link("Rules", "CON"), "Device names"), ("", "required")):
            with self.subTest(path=path):
                response, payload = self.request("POST", f"/api/tasks/{task_id}/attachments", {"path": path},
                                                 cookie=cookie, csrf=csrf)
                self.assertEqual(response.status, 400)
                self.assertRegex(payload["error"], message)
        response, detail = self.request("GET", f"/api/tasks/{task_id}", cookie=cookie)
        self.assertEqual([a["id"] for a in detail["task"]["attachments"]], [attachment_id])

    def test_server_command_transfer_applies_on_the_next_request(self):
        # PDDS2D: after 'astra transfer-primary' the old primary's sessions are gone, the new
        # primary can grant owner access, and the People screen data lists the event.
        owner_cookie, owner_csrf = self._owner_session()
        _, deputy = self.request("POST", "/api/users", {
            "email": "deputy@example.org", "display_name": "Deputy", "password": "deputy password safe",
            "role": "member"}, cookie=owner_cookie, csrf=owner_csrf)
        response, _ = self.request("POST", f"/api/users/{deputy['user']['id']}/secondary-owner", {"reason": "cover"},
                                   cookie=owner_cookie, csrf=owner_csrf)
        self.assertIn(response.status, (200, 201))
        self.server.service.transfer_primary_owner("deputy@example.org", {"via": "cli", "os_user": "op", "host": "h"})
        response, payload = self.request("GET", "/api/tasks", cookie=owner_cookie)
        self.assertEqual(response.status, 403)  # the old primary's session no longer exists
        self.assertEqual(payload["error"], "Session expired.")
        response, login = self.request("POST", "/api/login", {"email": "deputy@example.org",
                                                              "password": "deputy password safe"})
        deputy_cookie, deputy_csrf = response.getheader("Set-Cookie").split(";", 1)[0], login["csrf"]
        self.assertEqual(login["user"]["is_primary_owner"], 1)
        _, member = self.request("POST", "/api/users", {
            "email": "next@example.org", "display_name": "Next", "password": "next password safe",
            "role": "member"}, cookie=deputy_cookie, csrf=deputy_csrf)
        response, _ = self.request("POST", f"/api/users/{member['user']['id']}/secondary-owner", {"reason": "help"},
                                   cookie=deputy_cookie, csrf=deputy_csrf)
        self.assertIn(response.status, (200, 201))
        response, audit = self.request("GET", "/api/user-events", cookie=deputy_cookie)
        self.assertIn("primary_owner_transferred", {e["event_type"] for e in audit["events"]})

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
            "path": link("out", "final.pdf"),
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
        _, attachment = self.request("POST", f"/api/tasks/{task_id}/attachments", {"path": link("out", f"{title}.pdf")}, cookie=cookie, csrf=csrf)
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
        # 5WZ4A8 review gap 3: the change is readable back over HTTP with its audit fields.
        response, history = self.request("GET", f"/api/projects/{pid}/events", cookie=cookie)
        self.assertEqual(response.status, 200)
        rows = [e for e in history["events"] if e["event_type"] == "project_schedule_changed"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reason"], "Kickoff scheduled")
        self.assertEqual(rows[0]["actor_name"], "Owner")
        self.assertEqual(json.loads(rows[0]["detail_json"]), {
            "before": {"start_date": None, "target_date": None},
            "after": {"start_date": "2026-02-01", "target_date": "2026-05-01"},
        })

    def test_project_schedule_and_history_authorization_over_http(self):
        # 5WZ4A8 review gaps 1 and 4: a viewer and a non-member get 403 on the change;
        # the viewer may read the history, the non-member may not; a manager may change dates.
        owner_cookie, owner_csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Guarded HTTP"}, cookie=owner_cookie, csrf=owner_csrf)
        pid = project["project"]["id"]
        users = {}
        for key, role in (("viewer", "viewer"), ("outsider", None), ("manager", "manager")):
            _, created = self.request("POST", "/api/users", {
                "email": f"{key}-sched@example.org", "display_name": key.title(),
                "password": f"{key} password safe", "role": "member",
            }, cookie=owner_cookie, csrf=owner_csrf)
            users[key] = created["user"]["id"]
            if role:
                self.request("POST", "/api/project-access", {
                    "project_id": pid, "user_id": created["user"]["id"], "role": role,
                }, cookie=owner_cookie, csrf=owner_csrf)
        change = {"start_date": "2026-02-01", "target_date": "2026-05-01", "reason": "Try"}
        sessions = {key: self._login_as(f"{key}-sched@example.org", f"{key} password safe") for key in users}
        for key in ("viewer", "outsider"):
            cookie, csrf = sessions[key]
            with self.subTest(actor=key):
                response, _ = self.request("POST", f"/api/projects/{pid}/schedule", change, cookie=cookie, csrf=csrf)
                self.assertEqual(response.status, 403)
        _, history = self.request("GET", f"/api/projects/{pid}/events", cookie=owner_cookie)
        self.assertEqual([e for e in history["events"] if e["event_type"] == "project_schedule_changed"], [])
        cookie, csrf = sessions["manager"]
        response, updated = self.request("POST", f"/api/projects/{pid}/schedule", change, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        self.assertEqual(updated["project"]["start_date"], "2026-02-01")
        response, history = self.request("GET", f"/api/projects/{pid}/events", cookie=sessions["viewer"][0])
        self.assertEqual(response.status, 200)
        rows = [e for e in history["events"] if e["event_type"] == "project_schedule_changed"]
        self.assertEqual([(r["actor_user_id"], r["reason"]) for r in rows], [(users["manager"], "Try")])
        response, _ = self.request("GET", f"/api/projects/{pid}/events", cookie=sessions["outsider"][0])
        self.assertEqual(response.status, 403)
        response, _ = self.request("GET", f"/api/projects/{pid}/events")
        self.assertIn(response.status, (401, 403))

    def test_project_history_kinds_are_limited_for_non_managers_over_http(self):
        # ZSZ9T2: the server filters; a viewer or member never receives owner-request or
        # import rows. K62ZAP: a Chairman gets the full list like the Owner.
        owner_cookie, owner_csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Filtered HTTP"}, cookie=owner_cookie, csrf=owner_csrf)
        pid = project["project"]["id"]
        for key, global_role, role in (("chairman", "chairman", None), ("viewer", "member", "viewer"),
                                       ("member", "member", "member"), ("manager", "member", "manager"),
                                       ("outsider", "member", None)):
            _, created = self.request("POST", "/api/users", {
                "email": f"{key}-kinds@example.org", "display_name": key.title(),
                "password": f"{key} password safe", "role": global_role,
            }, cookie=owner_cookie, csrf=owner_csrf)
            if role:
                self.request("POST", "/api/project-access", {
                    "project_id": pid, "user_id": created["user"]["id"], "role": role,
                }, cookie=owner_cookie, csrf=owner_csrf)
        service = self.server.service
        owner_id = service.db.execute("SELECT id FROM users WHERE global_role='owner'").fetchone()["id"]
        every = ["project_schedule_changed", "import_committed", "protected_action_requested",
                 "protected_action_rejected", "project_closed"]
        for kind in every:
            # Only the kinds a non-manager must not see carry the sensitive filename.
            hidden = kind not in ("project_schedule_changed", "project_closed")
            detail = {"filename": "secret-plan.xlsx"} if hidden else {"note": "public"}
            service._project_event(pid, owner_id, kind, detail, f"reason for {kind}")
        filtered = ["project_schedule_changed", "project_closed"]
        expected = {"owner": every, "manager": every, "chairman": every, "viewer": filtered, "member": filtered}
        cookies = {"owner": owner_cookie}
        for key in ("chairman", "viewer", "member", "manager", "outsider"):
            cookies[key] = self._login_as(f"{key}-kinds@example.org", f"{key} password safe")[0]
        for key, kinds in expected.items():
            with self.subTest(actor=key):
                response, history = self.request("GET", f"/api/projects/{pid}/events", cookie=cookies[key])
                self.assertEqual(response.status, 200)
                # Order-independent: back-to-back rows can share a timestamp on coarse clocks.
                self.assertCountEqual([e["event_type"] for e in history["events"]], kinds)
                if kinds == filtered:
                    self.assertNotIn("secret-plan.xlsx", json.dumps(history))
        response, _ = self.request("GET", f"/api/projects/{pid}/events", cookie=cookies["outsider"])
        self.assertEqual(response.status, 403)

    def test_task_history_hides_approval_rows_from_non_managers_over_http(self):
        # K62ZAP: Owner, Chairman and managers get every task event; a member, viewer or
        # non-manager approver gets ordinary kinds plus their own rows; a non-member gets 403.
        owner_cookie, owner_csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Task history HTTP"}, cookie=owner_cookie, csrf=owner_csrf)
        pid = project["project"]["id"]
        _, task = self.request("POST", "/api/tasks", {"project_id": pid, "title": "Audited"},
                               cookie=owner_cookie, csrf=owner_csrf)
        tid = task["task"]["id"]
        users = {}
        for key, global_role, role in (("chairman", "chairman", None), ("manager", "member", "manager"),
                                       ("member", "member", "member"), ("viewer", "member", "viewer"),
                                       ("approver", "member", "member"), ("outsider", "member", None)):
            _, created = self.request("POST", "/api/users", {
                "email": f"{key}-task-kinds@example.org", "display_name": key.title(),
                "password": f"{key} password safe", "role": global_role,
            }, cookie=owner_cookie, csrf=owner_csrf)
            users[key] = created["user"]["id"]
            if role:
                self.request("POST", "/api/project-access", {"project_id": pid, "user_id": users[key], "role": role},
                             cookie=owner_cookie, csrf=owner_csrf)
        service = self.server.service
        owner_id = service.db.execute("SELECT id FROM users WHERE global_role='owner'").fetchone()["id"]
        service.add_task_reviewer(service.get_user(owner_id), tid, users["approver"], "approver")
        for kind in ("task_updated", "protected_action_requested", "protected_action_rejected",
                     "final_result_mark_blocked", "import_key_assigned"):
            secret = None if kind == "task_updated" else {"payload": "secret-payload"}
            service._event(tid, owner_id, kind, None, secret, None, notify=False)
        service._event(tid, users["approver"], "protected_action_requested", None, {"note": "own"}, None, notify=False)
        # The approver's hidden row on a second project/task must not leak into this task's history.
        owner = service.get_user(owner_id)
        other = service.create_project(owner, "Task history HTTP B")
        service.grant_project_access(owner, other["id"], users["approver"], "member")
        other_task = service.create_task(owner, {"project_id": other["id"], "title": "Elsewhere"})
        service._event(other_task["id"], users["approver"], "protected_action_blocked", None,
                       {"note": "elsewhere"}, None, notify=False)
        # Review 12b M1: adding the approver is now a task event; like approvals it is manager-level history.
        every = ["task_created", "reviewer_added", "task_updated", "protected_action_requested", "protected_action_rejected",
                 "final_result_mark_blocked", "import_key_assigned", "protected_action_requested"]
        ordinary = ["task_created", "task_updated"]
        expected = {"owner": every, "chairman": every, "manager": every, "member": ordinary, "viewer": ordinary,
                    "approver": ordinary + ["protected_action_requested"]}
        for key, kinds in expected.items():
            cookie = owner_cookie if key == "owner" else \
                self._login_as(f"{key}-task-kinds@example.org", f"{key} password safe")[0]
            with self.subTest(actor=key):
                response, history = self.request("GET", f"/api/tasks/{tid}/events", cookie=cookie)
                self.assertEqual(response.status, 200)
                # Order-independent: back-to-back rows can share a timestamp on coarse clocks.
                self.assertCountEqual([e["event_type"] for e in history["events"]], kinds)
                self.assertNotIn("elsewhere", json.dumps(history))
                if key in ("member", "viewer", "approver"):
                    self.assertNotIn("secret-payload", json.dumps(history))
        cookie = self._login_as("outsider-task-kinds@example.org", "outsider password safe")[0]
        response, _ = self.request("GET", f"/api/tasks/{tid}/events", cookie=cookie)
        self.assertEqual(response.status, 403)

    def test_secondary_owner_routes_enforce_primary_control_over_http(self):
        # GTEYTG (Aly, ts 1790245584.314119): only the primary grants or removes owner
        # access; a secondary cannot touch the primary or another secondary.
        owner_cookie, owner_csrf = self._owner_session()
        response, me = self.request("GET", "/api/me", cookie=owner_cookie)
        self.assertEqual(me["user"]["is_primary_owner"], 1)
        primary_id = me["user"]["id"]
        ids = {}
        for key, role in (("first", "member"), ("second", "member"), ("plain", "member"), ("chair", "chairman")):
            _, created = self.request("POST", "/api/users", {
                "email": f"{key}-owner@example.org", "display_name": key.title(),
                "password": f"{key} password safe", "role": role,
            }, cookie=owner_cookie, csrf=owner_csrf)
            ids[key] = created["user"]["id"]
        for key in ("first", "second"):
            response, granted = self.request("POST", f"/api/users/{ids[key]}/secondary-owner",
                                             {"reason": "cover"}, cookie=owner_cookie, csrf=owner_csrf)
            self.assertEqual(response.status, 201)
            self.assertEqual((granted["user"]["global_role"], granted["user"]["is_primary_owner"]), ("owner", 0))
        response, _ = self.request("POST", f"/api/users/{ids['plain']}/secondary-owner", {"reason": " "},
                                   cookie=owner_cookie, csrf=owner_csrf)
        self.assertEqual(response.status, 400)
        response, _ = self.request("POST", "/api/users/no-such-user/secondary-owner", {"reason": "x"},
                                   cookie=owner_cookie, csrf=owner_csrf)
        self.assertEqual(response.status, 404)
        _, listed = self.request("GET", "/api/users", cookie=owner_cookie)
        flags = {u["id"]: u["is_primary_owner"] for u in listed["users"]}
        self.assertEqual((flags[primary_id], flags[ids["first"]], flags[ids["plain"]]), (1, 0, 0))

        first_cookie, first_csrf = self._login_as("first-owner@example.org", "first password safe")
        response, me = self.request("GET", "/api/me", cookie=first_cookie)
        self.assertEqual((me["user"]["global_role"], me["user"]["is_primary_owner"]), ("owner", 0))
        forbidden = [
            ("POST", f"/api/users/{ids['plain']}/secondary-owner", {"reason": "promote"}),
            ("DELETE", f"/api/users/{ids['second']}/secondary-owner", {"reason": "demote"}),
            ("DELETE", f"/api/users/{primary_id}/secondary-owner", {"reason": "coup"}),
            ("POST", f"/api/users/{primary_id}/active", {"active": False}),
            ("POST", f"/api/users/{ids['second']}/active", {"active": False}),
        ]
        for method, path, body in forbidden:
            with self.subTest(actor="secondary", method=method, path=path):
                response, _ = self.request(method, path, body, cookie=first_cookie, csrf=first_csrf)
                self.assertEqual(response.status, 403)
        # A secondary still has ordinary Owner powers and can read the owner-access audit.
        response, _ = self.request("POST", "/api/projects", {"name": "Deputy's"}, cookie=first_cookie, csrf=first_csrf)
        self.assertEqual(response.status, 201)
        response, audit = self.request("GET", "/api/user-events", cookie=first_cookie)
        self.assertEqual(response.status, 200)
        kinds = [e["event_type"] for e in audit["events"]]
        self.assertEqual(kinds.count("secondary_owner_granted"), 2)
        self.assertEqual(kinds.count("owner_change_blocked"), len(forbidden))

        chair_cookie, chair_csrf = self._login_as("chair-owner@example.org", "chair password safe")
        for method, path in (("POST", f"/api/users/{ids['plain']}/secondary-owner"),
                             ("DELETE", f"/api/users/{ids['first']}/secondary-owner")):
            with self.subTest(actor="chairman", method=method):
                response, _ = self.request(method, path, {"reason": "x"}, cookie=chair_cookie, csrf=chair_csrf)
                self.assertEqual(response.status, 403)
        response, _ = self.request("GET", "/api/user-events", cookie=chair_cookie)
        self.assertEqual(response.status, 403)

        response, revoked = self.request("DELETE", f"/api/users/{ids['first']}/secondary-owner", {"reason": "back"},
                                         cookie=owner_cookie, csrf=owner_csrf)
        self.assertEqual(response.status, 200)
        self.assertEqual(revoked["user"]["global_role"], "member")
        response, _ = self.request("GET", "/api/me", cookie=first_cookie)
        self.assertEqual(response.status, 403, "a removed secondary's sessions are revoked")

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


class AstraAssignmentWebTests(unittest.TestCase):
    """3FQEKB over HTTP: the pickers' purpose, and the Chairman assigning from the panel."""

    setUp, tearDown = AstraWebTests.setUp, AstraWebTests.tearDown
    request, _owner_session, _login_as = AstraWebTests.request, AstraWebTests._owner_session, AstraWebTests._login_as

    def test_pickers_and_the_chairmans_assignee_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Assign HTTP"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        made = {}
        for email, name, role in (("chair@example.org", "Chair", "chairman"), ("vi@example.org", "Vi", "member"),
                                  ("mo@example.org", "Mo", "member")):
            _, user = self.request("POST", "/api/users", {"email": email, "display_name": name, "password": "a password safe",
                                                          "role": role}, cookie=cookie, csrf=csrf)
            made[name] = user["user"]["id"]
        for name, role in (("Vi", "viewer"), ("Mo", "member")):
            self.request("POST", "/api/project-access", {"project_id": pid, "user_id": made[name], "role": role},
                         cookie=cookie, csrf=csrf)
        _, task = self.request("POST", "/api/tasks", {"project_id": pid, "title": "Top"}, cookie=cookie, csrf=csrf)
        task = task["task"]

        def picker(purpose, who=cookie):
            response, body = self.request("GET", f"/api/assignable-users?project_id={pid}&for={purpose}", cookie=who)
            return response.status, {u["display_name"]: u["project_role"] for u in body.get("users", [])}
        self.assertEqual(picker("task")[1], {"Mo": "member", "Owner": None})
        self.assertEqual(picker("subtask")[1], {"Mo": "member", "Owner": None, "Vi": "viewer"})
        self.assertEqual(picker("everyone")[0], 400)
        # The Chairman assigns over the panel's route; other fields are refused (403).
        ccookie, ccsrf = self._login_as("chair@example.org", "a password safe")
        self.assertEqual(picker("task", ccookie), (200, {"Mo": "member", "Owner": None}))
        response, refused = self.request("POST", f"/api/tasks/{task['id']}", {"title": "Mine", "owner_user_id": made["Mo"],
                                         "expected_revision": task["revision"]}, cookie=ccookie, csrf=ccsrf)
        self.assertEqual(response.status, 403)
        response, saved = self.request("POST", f"/api/tasks/{task['id']}", {"owner_user_id": made["Mo"], "reason": "",
                                       "expected_revision": task["revision"]}, cookie=ccookie, csrf=ccsrf)
        self.assertEqual((response.status, saved["task"]["owner_user_id"]), (200, made["Mo"]))
        # Nobody assigns the Chairman, and a viewer gets no top-level task (400 with the reason).
        for user_id, text in ((made["Chair"], "is the Chairman"), (made["Vi"], "viewer can be given subtasks only")):
            response, body = self.request("POST", f"/api/tasks/{task['id']}", {"owner_user_id": user_id,
                                          "expected_revision": saved["task"]["revision"]}, cookie=cookie, csrf=csrf)
            self.assertEqual(response.status, 400)
            self.assertIn(text, body["error"])
        _, detail = self.request("GET", f"/api/tasks/{task['id']}", cookie=ccookie)
        self.assertEqual((detail["task"]["permissions"]["assign_only"], detail["task"]["needs_new_assignee"]), (True, False))


class AstraGovernedDragWebTests(unittest.TestCase):
    """Lock #12 over HTTP: board moves, locks, date drags, bulk changes and WIP limits."""

    setUp, tearDown = AstraWebTests.setUp, AstraWebTests.tearDown
    request, _owner_session, _login_as = AstraWebTests.request, AstraWebTests._owner_session, AstraWebTests._login_as

    def _project_with_manager(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Drag HTTP"}, cookie=cookie, csrf=csrf)
        pid = project["project"]["id"]
        _, manager = self.request("POST", "/api/users", {"email": "pm@example.org", "display_name": "PM",
                                                         "password": "manager password safe"}, cookie=cookie, csrf=csrf)
        self.request("POST", "/api/project-access", {"project_id": pid, "user_id": manager["user"]["id"],
                                                     "role": "manager"}, cookie=cookie, csrf=csrf)
        _, task = self.request("POST", "/api/tasks", {"project_id": pid, "title": "Card"}, cookie=cookie, csrf=csrf)
        return (cookie, csrf), self._login_as("pm@example.org", "manager password safe"), pid, task["task"]

    def test_board_move_undo_and_order_over_http(self):
        (ocookie, ocsrf), (cookie, csrf), pid, task = self._project_with_manager()
        response, moved = self.request("POST", f"/api/tasks/{task['id']}/board-move",
                                       {"to_column": "progress", "expected_revision": task["revision"]},
                                       cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        self.assertEqual(moved["task"]["status"], "in_progress")
        response, undone = self.request("POST", f"/api/tasks/{task['id']}/undo-move",
                                        {"event_id": moved["undo"]["event_id"]}, cookie=cookie, csrf=csrf)
        self.assertEqual((response.status, undone["task"]["status"]), (200, "draft"))
        # A dialog target answers 409 with what to confirm; a manager's close files a request (202).
        rev = undone["task"]["revision"]
        response, ask = self.request("POST", f"/api/tasks/{task['id']}/board-move",
                                     {"to_column": "closed", "expected_revision": rev}, cookie=cookie, csrf=csrf)
        self.assertEqual((response.status, ask["confirm"]), (409, "close"))
        response, filed = self.request("POST", f"/api/tasks/{task['id']}/board-move",
                                       {"to_column": "closed", "expected_revision": rev, "status": "cancelled",
                                        "reason": "Duplicate"}, cookie=cookie, csrf=csrf)
        self.assertEqual((response.status, filed["request"]["action"]), (202, "update_task_status"))
        response, order = self.request("POST", f"/api/projects/{pid}/board-order",
                                       {"column": "draft", "task_ids": [task["id"]]}, cookie=cookie, csrf=csrf)
        self.assertEqual((response.status, order["order"]), (200, [task["id"]]))
        # Without the CSRF token nothing moves.
        response, _ = self.request("POST", f"/api/tasks/{task['id']}/board-move",
                                   {"to_column": "ready", "expected_revision": rev}, cookie=cookie)
        self.assertEqual(response.status, 403)

    def test_review_12a_dependency_rule_in_the_panel_over_http(self):
        (ocookie, ocsrf), (cookie, csrf), pid, task = self._project_with_manager()
        _, first = self.request("POST", "/api/tasks", {"project_id": pid, "title": "First"}, cookie=ocookie, csrf=ocsrf)
        response, _ = self.request("POST", "/api/task-dependencies", {"predecessor_task_id": first["task"]["id"],
                                   "successor_task_id": task["id"]}, cookie=ocookie, csrf=ocsrf)
        self.assertIn(response.status, (200, 201))
        _, detail = self.request("GET", f"/api/tasks/{task['id']}", cookie=cookie)
        body = {"status": "in_progress", "reason": "start", "expected_revision": detail["task"]["revision"]}
        response, refused = self.request("POST", f"/api/tasks/{task['id']}", body, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 400)
        self.assertIn("Only an owner may override a dependency", refused["error"])
        response, ask = self.request("POST", f"/api/tasks/{task['id']}", body, cookie=ocookie, csrf=ocsrf)
        self.assertEqual((response.status, ask["confirm"], ask["impact"]), (409, "dependencies", ["First"]))
        response, done = self.request("POST", f"/api/tasks/{task['id']}", {**body, "override_dependencies": True},
                                      cookie=ocookie, csrf=ocsrf)
        self.assertEqual(response.status, 200)
        response, submit = self.request("POST", f"/api/tasks/{task['id']}/submit", {"note": "done"}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 400)

    def test_review_12c_limits_in_one_request_and_strict_revisions_over_http(self):
        (ocookie, ocsrf), (cookie, csrf), pid, task = self._project_with_manager()
        response, saved = self.request("POST", f"/api/projects/{pid}/wip-limits",
                                       {"limits": {"ready": 2, "progress": "3"}, "reason": "plan"}, cookie=ocookie, csrf=ocsrf)
        self.assertEqual((response.status, saved["wip_limits"]), (200, {"ready": 2, "progress": 3}))
        response, bad = self.request("POST", f"/api/projects/{pid}/wip-limits", {"limits": {"ready": 2.5}},
                                     cookie=ocookie, csrf=ocsrf)
        self.assertEqual(response.status, 400)
        response, bad = self.request("POST", f"/api/projects/{pid}/bulk/apply",
                                     {"task_ids": [task["id"]], "action": "status", "value": "ready",
                                      "expected_revisions": [1]}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 400)
        self.assertIn("expected_revisions", bad["error"])

    def test_bulk_change_and_wip_limits_over_http(self):
        (ocookie, ocsrf), (cookie, csrf), pid, task = self._project_with_manager()
        _, second = self.request("POST", "/api/tasks", {"project_id": pid, "title": "Card 2"}, cookie=ocookie, csrf=ocsrf)
        ids = [task["id"], second["task"]["id"]]
        response, _ = self.request("POST", f"/api/projects/{pid}/wip-limits", {"column": "ready", "max_tasks": 1},
                                   cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 403)  # a manager does not configure limits
        response, limits = self.request("POST", f"/api/projects/{pid}/wip-limits", {"column": "ready", "max_tasks": 1},
                                        cookie=ocookie, csrf=ocsrf)
        self.assertEqual((response.status, limits["wip_limits"]), (200, {"ready": 1}))
        response, preview = self.request("POST", f"/api/projects/{pid}/bulk/preview",
                                         {"task_ids": ids, "action": "status", "value": "ready"}, cookie=cookie, csrf=csrf)
        self.assertEqual((response.status, preview["preview"]["counts"]), (200, {"ok": 2, "blocked": 0}))
        self.assertEqual(preview["preview"]["wip"]["limit"], 1)
        revisions = {i["id"]: i["revision"] for i in preview["preview"]["ok"]}
        body = {"task_ids": ids, "action": "status", "value": "ready", "expected_revisions": revisions}
        response, refused = self.request("POST", f"/api/projects/{pid}/bulk/apply", body, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 400)
        self.assertIn("work-in-progress limit", refused["error"])
        response, ask = self.request("POST", f"/api/projects/{pid}/bulk/apply", body, cookie=ocookie, csrf=ocsrf)
        self.assertEqual((response.status, ask["confirm"]), (409, "wip"))
        response, done = self.request("POST", f"/api/projects/{pid}/bulk/apply", {**body, "override_wip": True},
                                      cookie=ocookie, csrf=ocsrf)
        self.assertEqual((response.status, len(done["tasks"]), done["undo"]["seconds"]), (200, 2, 15))
        response, undone = self.request("POST", f"/api/projects/{pid}/bulk/undo", {"bulk_id": done["bulk_id"]},
                                        cookie=ocookie, csrf=ocsrf)
        self.assertEqual((response.status, len(undone["tasks"])), (200, 2))
        response, _ = self.request("POST", f"/api/projects/{pid}/bulk/preview",
                                   {"task_ids": ids, "action": "status", "value": "ready"}, cookie=cookie)
        self.assertEqual(response.status, 403)  # no CSRF token, no change

    def test_locks_and_gantt_reschedule_over_http(self):
        (ocookie, ocsrf), (cookie, csrf), pid, task = self._project_with_manager()
        tid = task["id"]
        response, got = self.request("POST", f"/api/tasks/{tid}/lock", {"kind": "edit"}, cookie=cookie, csrf=csrf)
        self.assertEqual((response.status, got["lock"]["seconds"]), (200, 60))
        # The owner's write is refused with who holds the lock and until when.
        response, refused = self.request("POST", f"/api/tasks/{tid}", {"title": "Owner rename",
                                         "expected_revision": task["revision"]}, cookie=ocookie, csrf=ocsrf)
        self.assertEqual(response.status, 409)
        self.assertEqual((refused["lock"]["holder_name"], refused["lock"]["kind"]), ("PM", "edit"))
        self.assertIn("is being changed by PM", refused["error"])
        response, _ = self.request("POST", f"/api/tasks/{tid}/lock/force", {"reason": "urgent"}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 403)  # only an owner force-unlocks
        response, _ = self.request("POST", f"/api/tasks/{tid}/lock/force", {"reason": "urgent"}, cookie=ocookie, csrf=ocsrf)
        self.assertEqual(response.status, 200)
        response, ended = self.request("POST", f"/api/tasks/{tid}/lock/renew", {"token": got["lock"]["token"]},
                                       cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 409)
        self.assertIn("has ended", ended["error"])
        # A Gantt drag: ordinary moves apply with Undo; one past the project target asks first.
        self.request("POST", f"/api/projects/{pid}/schedule", {"start_date": "2026-10-01", "target_date": "2026-12-31",
                                                               "reason": "Plan"}, cookie=ocookie, csrf=ocsrf)
        response, detail = self.request("GET", f"/api/tasks/{tid}", cookie=cookie)
        rev = detail["task"]["revision"]
        response, moved = self.request("POST", f"/api/tasks/{tid}/reschedule",
                                       {"start_date": "2026-10-05", "due_date": "2026-10-09", "expected_revision": rev},
                                       cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        response, undone = self.request("POST", f"/api/tasks/{tid}/undo-move", {"event_id": moved["undo"]["event_id"]},
                                        cookie=cookie, csrf=csrf)
        self.assertEqual((response.status, undone["task"]["due_date"]), (200, None))
        rev = undone["task"]["revision"]
        response, ask = self.request("POST", f"/api/tasks/{tid}/reschedule",
                                     {"due_date": "2027-01-10", "expected_revision": rev}, cookie=cookie, csrf=csrf)
        self.assertEqual((response.status, ask["confirm"]), (409, "impact"))
        self.assertTrue(any("after the project target (2026-12-31)" in i for i in ask["impact"]))
        response, done = self.request("POST", f"/api/tasks/{tid}/reschedule",
                                      {"due_date": "2027-01-10", "expected_revision": rev, "confirmed": True},
                                      cookie=cookie, csrf=csrf)
        self.assertEqual((response.status, done["task"]["due_date"]), (200, "2027-01-10"))
        self.assertNotIn("undo", done)
        response, bad = self.request("POST", f"/api/tasks/{tid}/reschedule",
                                     {"start_date": "2027-02-01", "due_date": "2027-01-10",
                                      "expected_revision": done["task"]["revision"]}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 400)
        self.assertIn("after the due date", bad["error"])


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
        # 3M2AYA review 8 L2: only the primary is offered a reset on the primary's row.
        rule = re.search(r"function canResetPassword\(u,viewerIsPrimary\)\{return ([^}]*)\}", self.js)
        self.assertIsNotNone(rule)
        self.assertEqual(rule.group(1), "!!u.active&&(!u.is_primary_owner||viewerIsPrimary)")
        if shutil.which("node"):
            probe = ("const canResetPassword=(u,viewerIsPrimary)=>" + rule.group(1) + ";"
                     "console.log(JSON.stringify([[{active:1,is_primary_owner:1},false],[{active:1,is_primary_owner:1},true],"
                     "[{active:1,is_primary_owner:0},false],[{active:0,is_primary_owner:0},true]]"
                     ".map(([u,p])=>canResetPassword(u,p))))")
            result = subprocess.run(["node", "-e", probe], capture_output=True, text=True, timeout=30)
            self.assertEqual(json.loads(result.stdout), [False, True, True, False])
        # PDDS2D: server-command events are labelled on the People screen.
        for phrase in ('primary_owner_transferred:"Primary owner transferred"', 'password_reset:"Password reset"',
                       '" via server command"', 'data-reset-password=', 'id="reset-password-form"',
                       'const MIN_PASSWORD=8;', 'minlength="${MIN_PASSWORD}"',
                       '"Your password has been changed. Your other sessions were signed out."',
                       '"Blocked password reset of the primary owner"'):
            self.assertIn(phrase, self.js)


class AstraFoundationStaticTests(unittest.TestCase):
    """4T4DEA: the design foundation (tokens, self-hosted font, focus, motion, no CSP-blocked styles)."""

    @classmethod
    def setUpClass(cls):
        cls.js = (STATIC / "app.js").read_text(encoding="utf-8")
        cls.css = (STATIC / "style.css").read_text(encoding="utf-8")
        cls.html = (STATIC / "index.html").read_text(encoding="utf-8")

    def test_no_inline_style_attributes_reach_the_page(self):
        # style-src 'self' drops style="..." attributes, so styling must come from classes.
        self.assertNotIn('style="', self.js)
        self.assertNotIn("style='", self.js)
        self.assertNotIn('style="', self.html)
        self.assertRegex(self.css, r"(?m)^\.fine \{ color: var\(--muted\); font-size: var\(--fs-small\);")

    def test_font_faces_point_at_the_served_files_only(self):
        from astra import web
        urls = re.findall(r'url\("([^"]+)"\)', self.css)
        self.assertEqual(sorted(urls), sorted(web.FONT_FILES))
        shipped = {f"fonts/{p.name}" for p in (STATIC / "fonts").iterdir()}
        self.assertEqual(shipped, web.FONT_FILES | {"fonts/Inter-OFL.txt"})
        self.assertIn("fonts/Inter-OFL.txt", web.STATIC_FILES)
        self.assertEqual(self.css.count("@font-face"), 2)
        self.assertIn("font-display: swap", self.css)
        self.assertRegex(self.css, r":root \{\n  font-family: Inter,")
        pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('"static/fonts/*"', pyproject)

    def test_tokens_type_scale_focus_and_reduced_motion(self):
        for token in ("--surface:", "--line:", "--muted:", "--space-4:", "--radius:", "--shadow-2:",
                      "--fs-caption: 11px", "--fs-small: 12px", "--fs-body: 14px", "--fs-lead: 16px",
                      "--fs-title: 20px", "--fs-display: 24px"):
            self.assertIn(token, self.css)
        # Today's palette is kept.
        for colour in ("--navy: #172a46", "--teal: #0c7c86", "--red: #c53a48", "--amber: #d98d16"):
            self.assertIn(colour, self.css)
        self.assertIn(":focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }", self.css)
        motion = self.css[self.css.index("@media (prefers-reduced-motion: reduce)"):]
        motion = motion[:motion.index("\n}\n")]
        self.assertIn("*, *::before, *::after { transition-duration: .01ms !important;", motion)
        self.assertIn("animation-duration: .01ms !important", motion)

    def test_text_tokens_meet_contrast_on_their_backgrounds(self):
        # Lock #9 review M5: recompute every text/background token pair from style.css (WCAG 1.4.3, 4.5:1).
        root = self.css[self.css.index(":root {"):self.css.index("}\n* { box-sizing")]
        tok = dict(re.findall(rf"--([a-z0-9-]+):\s*({HEX})", root, flags=re.I))
        pairs = [("muted", bg) for bg in ("surface", "canvas", "surface-2", "surface-3")]
        pairs += [("text-2", "surface-3"), ("rail-text", "navy"), ("teal-light", "navy"), ("navy", "badge"), ("teal", "surface")]
        pairs += [(f"chip-{c}", f"chip-{c}-bg") for c in ("red", "amber", "purple", "teal", "blue", "gray", "green")]
        pairs += [("chip-teal", "teal-soft")]
        # FKVHH8 review L1: links in unread Inbox rows sit on the unread tint.
        pairs += [("teal-dark", "teal-soft")]
        self.assertIn(".note-row.unread button.link { color: var(--teal-dark); }", self.css)
        self.assertRegex(self.css, r"\.note-row\.unread \{[^}]*background: var\(--teal-soft\)")
        for fg, bg in pairs:
            self.assertGreaterEqual(contrast_ratio(tok[fg], tok[bg]), 4.5, f"--{fg} on --{bg}")
        self.assertGreaterEqual(contrast_ratio("#FFFFFF", tok["teal"]), 4.5, "white on --teal buttons")
        # One muted grey: no literal copy of the old grey is left outside the token block.
        self.assertNotIn("#667085", self.css)
        self.assertNotRegex(self.css[self.css.index("}\n* { box-sizing"):], r"(?<![\w-])color: var\(--(amber|gray)\)")

    def test_task_links_are_44px_targets_on_phones_and_tablets(self):
        # Lock #10 review L2 (WCAG 2.5.8; lock #9 set 44px below 1024px).
        # Lock #11 review L4/L5: one touch-width block; task links are buttons, so the 44px button rule covers
        # them (row titles included), and only links inside a sentence, small print or a table cell drop to 24px.
        self.assertEqual(self.css.count("@media (max-width: 1023px)"), 1)
        block = self.css[self.css.index("@media (max-width: 1023px) {"):]
        block = block[:block.index("\n}\n")]
        self.assertRegex(block, r"button:not\(\.step\):not\(\.bar\):not\(\.expand\):not\(\.step-more\):not\(\.track\):not\(\.cal-item\), "
                                r"\.button-link, \.card-link, \.tabs a, \.fine a,\s*input[^{]*\{ min-height: 44px; \}")
        self.assertIn(":is(p, small, td, th) button.link:not(.row-title):not(.work-title) { min-height: 24px; }", block)
        self.assertIn("#board-divide, #cal-scope { min-height: 44px; }", block)
        self.assertEqual(block.count(".avatar, .panel-close"), 1)

    def test_touch_widths_get_44px_targets_16px_fields_and_room_for_the_bottom_bar(self):
        # 3C1Z74: one block for phones and tablets rather than per-screen rules.
        block = self.css[self.css.index("/* 3C1Z74: touch widths"):]
        block = block[block.index("@media (max-width: 1023px) {"):]
        block = block[:block.index("\n}\n") if "\n}\n" in block else len(block)]
        self.assertRegex(block, r"button:not\(\.step\)[^{]*\.tabs a, \.fine a,\s*input:not\(\[type=\"checkbox\"\]\)[^{]*select, textarea \{ min-height: 44px; \}")
        # Review 11 L1: :is() takes #search-box's weight, so class rules such as .dep-remove input (12.8px),
        # .sched-reject-reason and .col-list input.tpl-label cannot win back a smaller size.
        self.assertIn(":is(input, select, textarea, #search-box) { font-size: 16px; }", block)
        # No field rule anywhere uses an id selector, so none can outweigh it.
        self.assertFalse([r for r in re.findall(r"(?m)^[^@{}\n]*#[\w-]+[^{}\n]*\{[^}]*font-size", self.css)
                          if re.search(r"\b(input|select|textarea)\b", r) and "#search-box" not in r])
        self.assertIn("#detail-full { display: none; }", block)
        self.assertIn("env(safe-area-inset-bottom)", block)
        phone = self.css[self.css.rindex("@media (max-width: 760px)"):]
        self.assertIn(".shell { grid-template-columns: minmax(0, 1fr); padding-bottom: calc(72px + env(safe-area-inset-bottom)); }", self.css)
        self.assertIn("env(safe-area-inset-bottom)", self.css[self.css.index(".rail { position: fixed;"):][:300])
        self.assertTrue(phone)

    def test_legend_keys_and_sign_in_landmark(self):
        # Lock #11 review L3: each legend swatch is wrapped with its label so it never wraps away from it,
        # and the sign-in card is a main landmark named by its heading.
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        self.assertIn('<span class="key"><i class="proj-target-key"></i>Project target</span>', html)
        self.assertEqual(html.count('<span class="key">'), 8)
        self.assertRegex(self.css, r"\.legend \.key \{[^}]*white-space: nowrap;")
        self.assertIn('<main id="login" class="login-card" aria-labelledby="login-title">', html)
        self.assertIn('<h1 id="login-title">Project command centre</h1>', html)
        self.assertNotIn('<section id="login"', html)

    def test_gantt_project_flags_meet_contrast(self):
        # 3C1Z74: the target flag was white on #d1495b (4.36:1); it now uses --red.
        root = self.css[self.css.index(":root {"):self.css.index("}\n* { box-sizing")]
        tok = dict(re.findall(rf"--([a-z0-9-]+):\s*({HEX})", root, flags=re.I))
        self.assertIn(".proj-flag.target { background: var(--red); }", self.css)
        self.assertGreaterEqual(contrast_ratio("#FFFFFF", tok["red"]), 4.5)
        self.assertGreaterEqual(contrast_ratio("#FFFFFF", "#7a5af5"), 4.5)  # .proj-flag.start
        self.assertNotIn("#d1495b", self.css.lower())
        self.assertIn(".brand { font-weight: 800; letter-spacing: .18em; color: var(--teal-dark); }", self.css)

    def test_toolbar_wraps_instead_of_scrolling_sideways(self):
        self.assertRegex(self.css, r"(?m)^\.toolbar \{[^}]*flex-wrap: wrap;")
        # PZTYC9: the header became the top bar; on phones it wraps the search onto its own row.
        phone = self.css[self.css.rindex("@media (max-width: 760px)"):]
        self.assertRegex(phone, r"\.topbar \{[^}]*flex-wrap: wrap;")


# PZTYC9 / DR3PKR: the shell and the task panel run under node with a small DOM stub that records
# listeners, focus and history. Like the other drivers it offers only location.hash, history.replaceState
# and history.back (no pushState), so the router has to work without pushState.
SHELL_DRIVER = r"""
const fs=require("fs");
const src=fs.readFileSync(process.argv[2],"utf8"),mode=process.argv[3];
// FKVHH8 review M1: a browser whose clock and timezone disagree with the server (run with TZ and FAKE_NOW).
if(process.env.FAKE_NOW){const RealDate=Date,NOW=RealDate.parse(process.env.FAKE_NOW);
  globalThis.Date=class extends RealDate{constructor(...a){if(a.length)super(...a);else super(NOW)}static now(){return NOW}}}
const store={},docListeners={};
function el(id){
  const cls=new Set(),listeners={};
  const t={_id:id,innerHTML:"",textContent:"",value:"",checked:false,hidden:false,open:false,style:{},dataset:{},_attrs:{},isConnected:true,
    setAttribute(k,v){t._attrs[k]=String(v)},getAttribute(k){return t._attrs[k]??null},removeAttribute(k){delete t._attrs[k]},hasAttribute(k){return k in t._attrs},
    addEventListener(k,f){(listeners[k]=listeners[k]||[]).push(f)},dispatchEvent(e){(listeners[e.type]||[]).forEach(f=>f(e));return true},
    classList:{add:(...c)=>c.forEach(x=>cls.add(x)),remove:(...c)=>c.forEach(x=>cls.delete(x)),toggle:(c,on)=>{if(on===undefined?!cls.has(c):on)cls.add(c);else cls.delete(c)},contains:c=>cls.has(c)},
    _classes:()=>[...cls].sort(),_listeners:listeners,
    focus(){globalThis.__focused=t._id;document.activeElement=p},blur(){},select(){},showModal(){t.open=true},close(){t.open=false},
    contains(n){return n===p},closest(){return null},querySelector(s){return document.querySelector(s)},querySelectorAll(){return[]}};
  const p=new Proxy(t,{get(o,k){if(k===Symbol.toPrimitive)return()=>"";if(k in o)return o[k];return function(){return el()}}});
  return p;
}
globalThis.document={
  querySelector(s){if(store[s])return store[s];if(s.includes(":not([hidden])")||s.includes("[open]"))return null;return store[s]=el(s)},
  querySelectorAll(){return[]},getElementById(s){return document.querySelector("#"+s)},createElement(){return el()},
  addEventListener(k,f){(docListeners[k]=docListeners[k]||[]).push(f)},body:el("body"),documentElement:el("html")};
document.activeElement=document.body;
globalThis.window=globalThis;globalThis.addEventListener=(k,f)=>{globalThis["__on_"+k]=f};
globalThis.localStorage={getItem(){return null},setItem(){}};
globalThis.Option=function(t,v){return{text:t,value:v}};
globalThis.CSS={escape:s=>String(s)};
// 3C1Z74 review M1: media queries match only the full-screen panel width, and only when __narrow is set.
globalThis.matchMedia=q=>({get matches(){return !!globalThis.__narrow&&/1023px/.test(q)},addEventListener(){}});
const fetches=[];
globalThis.fetch=u=>{fetches.push(u);return new Promise(()=>{})};
if(mode!=="main"){
  const me=mode==="boot-me-fails"?null:{user:{id:"u1",display_name:"Omar Malik",global_role:"member"},csrf:"c"};
  globalThis.fetch=async u=>{fetches.push(u);const ok=u==="/api/me"&&!!me;return {ok,status:ok?200:500,json:async()=>ok?me:{error:"server down"}}};
}
const calls=[];
globalThis.location={hash:"",search:"",pathname:"/",origin:"http://astra",replace(u){calls.push(["location.replace",u])}};
globalThis.history={replaceState(a,b,url){calls.push(["replace",url]);location.hash=url},back(){calls.push(["back"])}};
// Seed what the menu wiring reads at load time.
document.querySelector("#more-btn").setAttribute("aria-controls","more-menu");document.querySelector("#more-menu").hidden=true;
document.querySelector("#detail-dialog").hidden=true;
(0,eval)(src+";globalThis.__a={parseRoute,filtersFromUrl,homeQuery,syncFilters,applyRoute,state,openPanel,closePanel,routeHash,taskLink,taskApi,panelState,noteFilters,showToast,projectActions,showApp,stepPanel,renderHome,boardColumn,renderBoard,renderProject,PROJECT_TABS,renderMyWork,calendarMonth,calExpanded,renderInbox,renderGantt,asOfText,bulk,gdrag,leases,phoneMQ};");
const a=globalThis.__a,out={},tick=()=>new Promise(r=>setTimeout(r,0));
const keydown=(key,target,extra={})=>{const e={key,target,ctrlKey:false,metaKey:false,altKey:false,defaultPrevented:false,prevented:false,preventDefault(){this.prevented=true;this.defaultPrevented=true},stopPropagation(){},...extra};(docListeners.keydown||[]).forEach(f=>f(e));return e.prevented};
const U1="11111111-1111-4111-8111-111111111111",U2="22222222-2222-4222-8222-222222222222",U3="33333333-3333-4333-8333-333333333333";
(async()=>{
if(mode==="home"){
  // VPYGY5: the Command Center drawn from loaded tasks, for an owner, a member and an empty install.
  const T=(o)=>({project_id:"p1",project_name:"P",owner_name:"Sara",status:"in_progress",due_state:"scheduled",days_to_due:20,due_date:"2026-10-20",is_blocked:false,is_critical_path:false,owner_user_id:"u2",...o});
  a.state.projects=[{id:"p1",name:"P"}];
  a.state.tasks=[T({id:"t1",title:"Late <img src=x onerror=alert(1)>",owner_user_id:"u1",due_state:"overdue",days_to_due:-3,due_date:"2026-09-22"}),
    T({id:"t2",title:"Waiting",is_blocked:true}),T({id:"t3",title:"Tight",is_critical_path:true,days_to_due:2}),
    T({id:"t4",title:"No date",due_state:"undated",days_to_due:null,due_date:null,owner_user_id:"u1"}),
    T({id:"t5",title:"Soon",owner_user_id:"u1",days_to_due:3}),T({id:"t6",title:"Now",owner_user_id:"u1",due_state:"today",days_to_due:0}),
    T({id:"t7",title:"Done late",status:"completed",due_state:"closed",days_to_due:-9,is_critical_path:true}),
    T({id:"t8",title:"Edge of the week",days_to_due:7,due_date:"2026-10-02"}),T({id:"t9",title:"Past the week",days_to_due:8,due_date:"2026-10-03"})];
  a.state.today="2026-09-25";
  a.state.ownerRequests=[{id:"r1",action:"update_task_status",task_id:U1,task_title:"<b>Tax</b>",project_name:"P",requested_by_name:"Mia Manager",requested_at:"2026-09-23T10:00:00Z",reason:"why",payload:{status:"cancelled"}}];
  const q=s=>document.querySelector(s),grab=()=>({strip:q("#home-strip").innerHTML,decisions:q("#home-decisions").innerHTML,decisionsHidden:q("#home-decisions-card").hidden,
    next:q("#home-next").innerHTML,risk:q("#home-risk").innerHTML,week:q("#home-week").innerHTML,empty:q("#home-empty").hidden,grid:q("#home-grid").hidden,asof:q("#home-asof").textContent,ganttLinkHidden:q("#home-gantt-link").hidden});
  a.state.user={id:"u1",display_name:"Aly J",global_role:"owner"};a.renderHome();out.owner=grab();
  a.state.user={id:"u1",display_name:"Omar M",global_role:"member"};a.renderHome();out.member=grab();
  a.state.projects=[];a.renderHome();out.emptyMember=grab();
  a.state.user={id:"u1",display_name:"Aly J",global_role:"owner"};a.renderHome();out.emptyOwner=grab();
  // Approve and Review on Home go through the same calls as the Inbox.
  globalThis.prompt=()=>"ok";fetches.splice(0);
  const home=q("#home-view"),click=m=>home._listeners.click[0]({target:{closest:s=>m[s]||null}});
  click({"[data-home-decision]":{dataset:{requestId:"r1",homeDecision:"approved"}}});
  click({"[data-detail]":{dataset:{detail:U1}}});
  await tick();out.clicks=fetches.slice();
  // Review L7: one /api/portfolio fetch per Home visit, even when the Inbox refresh redraws Home.
  a.state.projects=[{id:"p1",name:"P"}];location.hash="#/home";a.panelState.rendered=null;fetches.splice(0);
  try{a.applyRoute(false,false)}catch(e){out.homeRouteError=String(e)}
  for(let i=0;i<5;i++)await tick();a.renderHome();a.renderHome();await tick();
  out.portfolioFetches=fetches.filter(u=>String(u).startsWith("/api/portfolio")).length;
  // Old #/home?<filters> links land on the portfolio timeline.
  location.hash="#/home?due=7&open=1";calls.splice(0);
  try{a.applyRoute(false,false)}catch(e){out.routeError=String(e)}
  out.redirect=[calls.filter(c=>c[0]==="replace").slice(0,1),location.hash];
  process.stdout.write(JSON.stringify(out));return;
}
if(mode==="board"){
  // CR121Z: the 11 statuses land in 7 read-only columns; lanes, collapsed columns and escaping.
  const statuses=["draft","assigned","in_progress","submitted","changes_requested","completed","on_hold","delayed","cancelled","abandoned","reopened"];
  out.columns=Object.fromEntries(statuses.map(st=>[st,a.boardColumn({status:st,is_blocked:false})]));
  out.blockedColumns=Object.fromEntries(statuses.map(st=>[st,a.boardColumn({status:st,is_blocked:true})]));
  const T=o=>({project_id:U1,project_name:"P",status:"in_progress",due_state:"scheduled",days_to_due:9,due_date:"2026-10-04",owner_name:"Sara Khan",owner_user_id:"u-sara",criticality:"high",...o});
  const tasks=[T({id:"a",title:"Plan <img src=x onerror=alert(1)>",status:"draft",owner_name:"",owner_user_id:null,criticality:null}),
    T({id:"b",title:"Build",is_blocked:true,blocked_by:[{title:"Plan"}],is_critical_path:true}),
    T({id:"c",title:"Ship",status:"completed",due_state:"closed"}),T({id:"d",title:"Step one",parent_task_id:"b",status:"completed"}),
    T({id:"e",title:"Step two",parent_task_id:"b"}),T({id:"f",title:"Drop",status:"cancelled",owner_name:"Omar Malik",owner_user_id:"u-omar",criticality:"low"})];
  out.board=a.renderBoard(tasks,"");out.byOwner=a.renderBoard(tasks,"owner");out.byCrit=a.renderBoard(tasks,"criticality");
  out.emptyBoard=a.renderBoard([],"");
  out.evilLanes=a.renderBoard([T({id:"z",title:"Z",owner_name:"<b>x</b>",owner_user_id:"u-x"})],"owner");
  // 3C1Z74: two people with the same display name keep separate lanes.
  out.sameName=a.renderBoard([T({id:"s1",title:"One",owner_user_id:"u-a"}),T({id:"s2",title:"Two",owner_user_id:"u-b"}),T({id:"s3",title:"Three",owner_user_id:"u-a"})],"owner");
  out.tabs=a.PROJECT_TABS.map(([k])=>k);
  out.routes=["#/project/"+U1+"/board?divide=owner","#/project/"+U1,"#/project/"+U1+"/nope","#/project/p1/board","#/my-work/calendar","#/my-work/other"]
    .map(h=>{const r=a.parseRoute(h);return [r.name,r.id,r.tab,r.path,r.params.toString()]});
  // An unknown project says so; a known one draws its tabs.
  a.state.user={id:"u1",display_name:"A B",global_role:"member"};a.state.projects=[{id:U1,name:"P",status:"active",entities:[]}];a.state.tasks=tasks;
  a.renderProject(a.parseRoute("#/project/"+U2+"/board"));out.missing=document.querySelector("#project-body").innerHTML;
  a.renderProject(a.parseRoute("#/project/"+U1+"/board"));out.tabsHtml=document.querySelector("#project-tabs").innerHTML;
  out.memberActions=["#project-capture","#project-save-template","#project-close"].map(s=>document.querySelector(s).hidden);
  a.state.user.global_role="owner";a.renderProject(a.parseRoute("#/project/"+U1+"/overview"));
  out.ownerActions=["#project-capture","#project-save-template","#project-close"].map(s=>document.querySelector(s).hidden);
  out.facts=document.querySelector("#project-facts").textContent;out.overview=document.querySelector("#project-body").innerHTML;
  // Lock #11 review L2: a project's Timeline uses that project's today and timezone.
  a.state.today="2026-09-25";a.state.timezone="Asia/Karachi";
  a.state.projects=[{id:U1,name:"P",status:"active",entities:[],start_date:"2026-09-26",target_date:"2026-10-30",today:"2026-09-26",timezone:"Pacific/Auckland"}];
  try{a.renderProject(a.parseRoute("#/project/"+U1+"/timeline"));out.timelineAsOf=document.querySelector("#as-of").textContent;out.timelineGantt=document.querySelector("#gantt").innerHTML}catch(e){out.timelineError=String(e.stack)}
  a.state.projects=[{id:U1,name:"P",status:"active",entities:[]}];
  // Review L8: an unknown tab shows Overview and the link is rewritten to say so.
  location.hash="#/project/"+U1+"/nope?divide=owner";calls.splice(0);
  try{a.applyRoute(false,false)}catch(e){out.tabRouteError=String(e)}
  out.tabFix=[calls.filter(c=>c[0]==="replace"),location.hash];
  process.stdout.write(JSON.stringify(out));return;
}
if(mode==="drag"){
  // JN1QYG: movable cards, the saved order, the dialog each column needs, and the move/Undo round trip.
  const realAskMove=askMove;
  const T=o=>({project_id:U1,project_name:"P",status:"draft",due_state:"scheduled",days_to_due:9,due_date:"2026-10-04",owner_name:"Sara",owner_user_id:"u-sara",criticality:"high",revision:3,...o});
  a.state.user={id:"u1",display_name:"PM",global_role:"member"};
  a.state.projects=[{id:U1,name:"P",status:"active",entities:[],can_manage:true}];
  const tasks=[T({id:"a",title:"A <b>",board_rank:2}),T({id:"b",title:"B",board_rank:1}),T({id:"c",title:"C"}),T({id:"x",title:"X",status:"submitted"})];
  a.state.tasks=tasks;
  out.movable=a.renderBoard(tasks,"");
  a.state.projects[0].can_manage=false;out.readOnly=a.renderBoard(tasks,"");a.state.projects[0].can_manage=true;
  out.order=columnOrder(U1,"draft");
  out.kinds=[["draft","blocked"],["draft","closed"],["draft","submitted"],["submitted","accepted"],["draft","accepted"],["completed","progress"],["cancelled","draft"],["draft","ready"]]
    .map(([st,col])=>moveDialogKind({status:st},col));
  const posts=[];let reply=()=>null;
  globalThis.fetch=async(u,opt)=>{posts.push([u,opt&&opt.body?JSON.parse(opt.body):null]);const r=reply(u)||{};const status=r.status||200;return {ok:status<400,status,json:async()=>r.body||{}}};
  globalThis.load=async()=>{posts.push(["load"])};
  const timers=[],realST=globalThis.setTimeout;globalThis.setTimeout=(f,ms)=>{timers.push(ms);return 0};
  reply=u=>u.endsWith("/board-move")?{body:{task:{...tasks[2],status:"assigned",revision:4},undo:{event_id:"ev1",seconds:15}}}:null;
  await moveCard({...tasks[2]},"ready");
  out.movePosts=posts.splice(0);out.moveToast=document.querySelector("#toast").innerHTML;out.toastTimers=timers.splice(0);
  await document.querySelector("#toast-action")._listeners.click[0]();for(let i=0;i<10;i++)await new Promise(r=>realST(r,0));
  out.undoPosts=posts.splice(0);
  reply=u=>u.endsWith("/board-move")?{status:400,body:{error:"B waits on A; only an owner may override."}}:null;
  await moveCard({...tasks[1]},"progress");out.refusedToast=document.querySelector("#toast").innerHTML;out.refusedPosts=posts.splice(0);
  globalThis.askMove=async()=>null;await moveCard({...tasks[0]},"closed");out.cancelPosts=posts.splice(0);
  globalThis.askMove=async kind=>kind==="close"?{status:"cancelled",reason:"Duplicate"}:{override_dependencies:true};
  reply=u=>u.endsWith("/board-move")?{status:202,body:{request:{id:"r1",action:"update_task_status"}}}:null;
  await moveCard({...tasks[0]},"closed");out.requestPosts=posts.splice(0);out.requestToast=document.querySelector("#toast").innerHTML;
  let n=0;reply=u=>u.endsWith("/board-move")?(n++?{body:{task:{...tasks[1],status:"in_progress",revision:4}}}:{status:409,body:{error:"B waits on A.",confirm:"dependencies",impact:["A"]}}):null;
  a.state.user.global_role="owner";await moveCard({...tasks[1]},"progress");out.overridePosts=posts.splice(0);
  n=0;reply=u=>u.endsWith("/board-move")?[{status:409,body:{error:"deps",confirm:"dependencies",impact:["A"]}},{status:409,body:{error:"full",confirm:"wip",impact:["Ready is full."]}},{body:{task:{...tasks[1],status:"assigned",revision:4}}}][n++]:null;
  globalThis.askMove=async kind=>kind==="wip"?{override_wip:true}:{override_dependencies:true};
  await moveCard({...tasks[1]},"ready");out.wipPosts=posts.splice(0).filter(p=>p[0].endsWith("/board-move")).map(p=>p[1]);
  reply=()=>null;
  await saveColumnOrder(U1,"draft",["c","b","a"],true);out.orderPosts=posts.splice(0);
  await document.querySelector("#toast-action")._listeners.click.at(-1)();for(let i=0;i<10;i++)await new Promise(r=>realST(r,0));out.orderUndoPosts=posts.splice(0);
  globalThis.setTimeout=realST;
  const attrs={};const btn={dataset:{moveMenu:"a"},isConnected:true,setAttribute(k,v){attrs[k]=v},getBoundingClientRect:()=>({left:10,bottom:20}),focus(){globalThis.__focused="opener"}};
  openMoveMenu(btn);out.menu=document.querySelector("#move-menu").innerHTML;out.openedExpanded=attrs["aria-expanded"];
  // Review 12a L6/L7: Escape closes the menu and puts focus back on the button that opened it;
  // closing it from elsewhere resets that same button.
  const menuEl=document.querySelector("#move-menu");globalThis.__focused=null;
  menuEl._listeners.keydown[0]({key:"Escape",preventDefault(){},stopPropagation(){},currentTarget:menuEl});
  out.escape={hidden:menuEl.hidden,focused:globalThis.__focused,expanded:attrs["aria-expanded"]};
  menuEl.id="move-menu";openMoveMenu(btn);globalThis.document.querySelectorAll=sel=>sel===".menu:not([hidden])"?[menuEl]:[];
  closeMenus();out.closedElsewhere=attrs["aria-expanded"];globalThis.document.querySelectorAll=()=>[];
  // Review 12a I1: a card in Blocked only because of a dependency offers Put on hold.
  a.state.tasks=[...tasks,T({id:"w",title:"W",is_blocked:true,blocked_by:[{title:"A"}]})];
  openMoveMenu({...btn,dataset:{moveMenu:"w"}});out.waitingMenu=menuEl.innerHTML;a.state.tasks=tasks;
  // Review 12a L7: the dialog escapes the title.
  realAskMove("hold",{title:'<img src=x onerror="globalThis.__xss=1">',project_id:U1,owner_user_id:"u-sara"},"blocked");
  out.escapedDialog=document.querySelector("#move-form").innerHTML;
  // Review 12a M1: the panel's dependency confirm retries with the override, or sends nothing more.
  const sent=[];let calls=0;
  const send=async more=>{sent.push(more);if(!calls++){const e=new Error("waits");e.status=409;e.confirm="dependencies";e.impact=["A"];throw e}return {task:{}}};
  globalThis.askMove=async()=>({override_dependencies:true});out.panelConfirm=[await withDependencyConfirm({title:"T"},"in_progress",send),sent.slice()];
  calls=0;sent.length=0;globalThis.askMove=async()=>null;out.panelCancel=[await withDependencyConfirm({title:"T"},"in_progress",send),sent.slice()];
  process.stdout.write(JSON.stringify(out));return;
}
if(mode==="gantt"){
  // X07XV4: draggable bars, the date maths, the reschedule round trip and the lease helpers.
  const T=o=>({project_id:U1,project_name:"P",status:"in_progress",due_state:"scheduled",days_to_due:9,owner_name:"Sara",owner_user_id:"u-sara",criticality:"high",revision:3,start_date:"2026-10-05",due_date:"2026-10-08",...o});
  a.state.user={id:"u1",display_name:"PM",global_role:"member"};a.state.today="2026-09-25";
  a.state.projects=[{id:U1,name:"P",status:"active",entities:[],can_manage:true,start_date:"2026-10-01",target_date:"2026-12-31"}];
  const tasks=[T({id:"g1",title:"Move <me>"}),T({id:"g2",title:"Closed",status:"completed"}),T({id:"g3",title:"Undated",start_date:null,due_date:null})];
  a.state.tasks=tasks;a.state.viewOverride="chart";
  a.renderGantt(tasks);out.canDrag=document.querySelector("#gantt").innerHTML;
  a.state.projects[0].can_manage=false;a.renderGantt(tasks);out.cannotDrag=document.querySelector("#gantt").innerHTML;a.state.projects[0].can_manage=true;
  out.span=document.querySelector("#gantt").dataset.span;
  const t=tasks[0];
  out.dates={move:barDates(t,null,3),start:barDates(t,"start",2),startClamp:barDates(t,"start",9),end:barDates(t,"end",-1),endClamp:barDates(t,"end",-9),
    noStart:barDates({...t,start_date:null},null,2),growStart:barDates({...t,start_date:null},"start",-2)};
  out.tips=[dateTip(t,barDates(t,null,3),3),dateTip(t,barDates(t,"end",-1),-1),dateTip(t,{start_date:t.start_date,due_date:t.due_date},0)];
  const posts=[];let reply=()=>null;
  globalThis.fetch=async(u,opt)=>{posts.push([u,opt&&opt.body?JSON.parse(opt.body):null]);const r=reply(u)||{};const status=r.status||200;return {ok:status<400,status,json:async()=>r.body||{}}};
  globalThis.load=async()=>{posts.push(["load"])};
  const timers=[],realST=globalThis.setTimeout;globalThis.setTimeout=(f,ms)=>{timers.push(ms);return 0};
  const realAskMove=askMove;const intervals=[];globalThis.setInterval=(f,ms)=>{intervals.push(ms);return intervals.length};globalThis.clearInterval=()=>{};
  const flush=async()=>{for(let i=0;i<10;i++)await new Promise(r=>realST(r,0))};
  reply=u=>u.endsWith("/reschedule")?{body:{task:{...t,start_date:"2026-10-08",due_date:"2026-10-11"},undo:{event_id:"ev9",seconds:15}}}:null;
  await rescheduleTask(t,barDates(t,null,3),3);
  out.movePosts=posts.splice(0);out.moveToast=document.querySelector("#toast").innerHTML;out.timers=timers.splice(0);
  await document.querySelector("#toast-action")._listeners.click.at(-1)();await flush();out.undoPosts=posts.splice(0);
  let n=0;reply=u=>u.endsWith("/reschedule")?(n++?{body:{task:t,impact:["It is on the critical path."]}}:{status:409,body:{error:"Consequences.",confirm:"impact",impact:["It is on the critical path."]}}):null;
  const asked=[];globalThis.askMove=async(kind,task,col,err)=>{asked.push([kind,err.impact,err.dates]);return {confirmed:true}};
  await rescheduleTask(t,barDates(t,"end",20),20);out.impactPosts=posts.splice(0);out.asked=asked;out.impactToast=document.querySelector("#toast").innerHTML;
  globalThis.askMove=async()=>null;n=0;await rescheduleTask(t,barDates(t,"end",20),20);out.cancelPosts=posts.splice(0);
  reply=u=>u.endsWith("/reschedule")?{status:400,body:{error:"The start date (2026-10-20) would be after the due date (2026-10-10)."}}:null;
  await rescheduleTask(t,barDates(t,null,1),1);out.refusedToast=document.querySelector("#toast").innerHTML;posts.splice(0);
  // Leases: take, keep, renew timer, release; a refused one names the holder.
  reply=u=>u.endsWith("/lock")?{body:{lock:{token:"tok1",seconds:60}}}:null;
  out.take=await takeLease("g1","drag");out.again=await takeLease("g1","drag");out.intervals=intervals.slice();
  await dropLease("g1");out.leasePosts=posts.splice(0);
  const held={holder_user_id:"u-sara",holder_name:"Sara <K>",kind:"edit",expires_at:"2026-09-25T10:00:30+00:00"};
  reply=u=>u.endsWith("/lock")?{status:409,body:{error:"busy",lock:held}}:null;
  const refused=await takeLease("g1","edit");out.refusedLease=[refused.ok,refused.err.lock.holder_name];posts.splice(0);
  // Review 12b L1: a drag borrows your edit lease and leaves it alone; each caller releases its own kind.
  reply=u=>u.endsWith("/lock")?{body:{lock:{token:"tokE",seconds:60}}}:null;
  await takeLease("g1","edit");out.borrow=await takeLease("g1","drag");await dropLease("g1","drag");
  out.afterDragDrop=[a.leases.has("g1"),posts.filter(p=>p[0].endsWith("/lock/release")).length];
  // Closing the panel releases the edit lease (review 12b L9).
  const panel=document.querySelector("#detail-dialog");panel.hidden=false;a.panelState.shown="g1";a.closePanel(true);await flush();
  out.closeReleased=[a.leases.has("g1"),posts.splice(0).filter(p=>p[0].endsWith("/lock/release")).map(p=>p[1])];
  // rescheduleTask releases the drag lease it ran under.
  reply=u=>u.endsWith("/lock")?{body:{lock:{token:"tokD",seconds:60}}}:u.endsWith("/reschedule")?{body:{task:t,undo:{event_id:"ev10",seconds:15}}}:null;
  await takeLease("g1","drag");await rescheduleTask(t,barDates(t,null,1),1);
  out.reschedReleased=[a.leases.has("g1"),posts.splice(0).filter(p=>p[0].endsWith("/lock/release")).map(p=>p[1])];
  // Review 12b L8: the tip counts the change applied (a start drag clamped at the due date is +3, not +30).
  out.clampedTip=dateTip(t,barDates(t,"start",30),appliedDays(t,barDates(t,"start",30)));
  // Review 12b I6: a lock refusal from the server reads in local time, as the toast does.
  reply=()=>({status:409,body:{error:"“T” is being changed by Sara (an edit); their lock runs out at 10:00:30 UTC unless they keep working.",lock:held}});
  try{await api(taskApi("g1"),{method:"POST",body:"{}"})}catch(err){out.lockMessage=[err.message,lockTime(held)]}
  globalThis.setTimeout=realST;
  // Review 12b L9: touch and phones never start a bar drag; a mouse on a wide screen does.
  const barStub={dataset:{drag:"g1",x:"10",w:"4"},closest:sel=>sel===".timeline"?{getBoundingClientRect:()=>({width:700})}:null};
  const down=pointerType=>{a.gdrag.bar=null;document.querySelector("#gantt")._listeners.pointerdown[0]({target:{closest:sel=>sel==="[data-drag]"?barStub:null},button:0,pointerType,clientX:5,pointerId:1});return !!a.gdrag.bar};
  document.querySelector("#gantt").dataset.span="8380800000";
  out.startDrag={mouse:down("mouse"),touch:down("touch")};const setPhone=v=>Object.defineProperty(a.phoneMQ,"matches",{value:v,configurable:true,writable:true});
  setPhone(true);out.startDrag.phone=down("mouse");setPhone(false);a.gdrag.bar=null;
  // The impact dialog escapes what it lists.
  const dlg=document.querySelector("#move-dialog");dlg.showModal=()=>{};
  realAskMove("impact",t,null,{impact:['<img src=x onerror="globalThis.__xss=3">'],dates:barDates(t,"end",2)});out.impactDialog=document.querySelector("#move-form").innerHTML;
  out.banner=lockBanner(held,"",true);out.bannerNoForce=lockBanner(held,"",false);
  out.chipOther=boardCard(T({id:"c1",title:"Card",lock:held}),[],true);
  out.chipMine=boardCard(T({id:"c2",title:"Card",lock:{...held,holder_user_id:"u1"}}),[],true);
  // Review 12d L2: Escape cancels a bar drag, puts the bar back and sends nothing.
  const bar={classList:{remove(){},add(){}},style:{left:"55%",width:"9%"}};
  Object.assign(a.gdrag,{bar,active:true,x0:10,w0:4,t,lease:null});posts.splice(0);
  keydown("Escape",document.body);
  out.escape=[a.gdrag.bar,a.gdrag.active,bar.style.left,bar.style.width,posts.filter(p=>p[0].endsWith("/reschedule")).length];
  // An edit form left idle for a minute lets its lease go instead of renewing it.
  reply=()=>null;posts.splice(0);
  const idle={token:"tokI",kind:"edit",last:Date.now()-61000,timer:null};a.leases.set("g9",idle);
  await renewLease("g9",idle);await flush();
  out.idle=[a.leases.has("g9"),posts.splice(0).map(p=>[p[0],p[1]])];
  process.stdout.write(JSON.stringify(out));return;
}
if(mode==="bulk"){
  // XV92JJ: pick boxes, Shift-click ranges, the preview and apply round trip, Undo, and WIP counts.
  const T=o=>({project_id:U1,project_name:"P",status:"draft",due_state:"scheduled",days_to_due:9,due_date:"2026-10-04",owner_name:"Sara",owner_user_id:"u-sara",criticality:"high",revision:3,...o});
  a.state.user={id:"u1",display_name:"PM",global_role:"member"};a.state.today="2026-09-25";
  a.state.projects=[{id:U1,name:"P",status:"active",entities:[],can_manage:true,wip_limits:{ready:1,draft:3}}];
  const tasks=[T({id:"a",title:"A"}),T({id:"b",title:"B"}),T({id:"c",title:"C",status:"assigned"}),T({id:"d",title:"D",status:"assigned"})];
  a.state.tasks=tasks;
  location.hash="#/project/"+U1+"/board";out.scope=bulkScope();
  a.bulk.ids.add("b");out.board=a.renderBoard(tasks,"");a.bulk.ids.clear();
  location.hash="#/home";out.noScope=bulkScope();out.boardElsewhere=boardCard(tasks[0],[],false);
  location.hash="#/project/"+U1+"/list";
  out.range=[pickRange(["a","b","c","d"],"a","c"),pickRange(["a","b","c","d"],"d","b"),pickRange(["a","b"],"x","b")];
  const posts=[];let reply=()=>null;
  globalThis.fetch=async(u,opt)=>{posts.push([u,opt&&opt.body?JSON.parse(opt.body):null]);const r=reply(u)||{};const status=r.status||200;return {ok:status<400,status,json:async()=>r.body||{}}};
  globalThis.load=async()=>{posts.push(["load"])};
  const timers=[],realST=globalThis.setTimeout;globalThis.setTimeout=(f,ms)=>{timers.push(ms);return 0};
  const flush=async()=>{for(let i=0;i<10;i++)await new Promise(r=>realST(r,0))};
  a.bulk.ids=new Set(["a","b"]);a.bulk.pid=U1;a.bulk.action="status";document.querySelector("#bulk-input").value="ready";
  out.payload=bulkPayload();
  const plan={action:"status",value:"ready",summary:"status to Ready",ok:[{id:"a",title:"A",revision:3},{id:"b",title:"B",revision:4}],blocked:[],impact:[],
    wip:{count:2,limit:1,incoming:2,message:"Ready is at its work-in-progress limit.",column:"ready",can_override:true},counts:{ok:2,blocked:0}};
  reply=u=>u.endsWith("/bulk/preview")?{body:{preview:plan}}:u.endsWith("/bulk/apply")?{body:{bulk_id:"bk1",tasks:[{id:"a"},{id:"b"}],summary:"status to Ready",undo:{bulk_id:"bk1",seconds:15}}}:u.endsWith("/bulk/undo")?{body:{tasks:[{id:"a"},{id:"b"}]}}:null;
  const realAskBulk=askBulk;
  const asked=[];globalThis.askBulk=async p=>{asked.push(p.counts);return {override_wip:true}};
  await reviewBulk(U1);out.applyPosts=posts.splice(0);out.applyToast=document.querySelector("#toast").innerHTML;out.timers=timers.splice(0);out.cleared=a.bulk.ids.size;
  await document.querySelector("#toast-action")._listeners.click.at(-1)();await flush();out.undoPosts=posts.splice(0);
  // Removing the blocked tasks narrows the selection and previews again.
  a.bulk.ids=new Set(["a","b","c"]);let round=0;
  reply=u=>u.endsWith("/bulk/preview")?{body:{preview:round++?{...plan,blocked:[]}:{...plan,wip:null,blocked:[{id:"c",title:"C",reason:"is already Ready"}],counts:{ok:2,blocked:1}}}}:null;
  globalThis.askBulk=async p=>p.blocked.length?{drop:true}:null;
  await reviewBulk(U1);out.afterDrop=[...a.bulk.ids];out.dropPosts=posts.splice(0).map(p=>p[1]&&p[1].task_ids);
  // A refused apply says nothing changed.
  a.bulk.ids=new Set(["a"]);reply=u=>u.endsWith("/bulk/preview")?{body:{preview:{...plan,wip:null}}}:u.endsWith("/bulk/apply")?{status:409,body:{error:"“A” changed since the preview; nothing was changed. Preview again."}}:null;
  globalThis.askBulk=async()=>({override_wip:false});await reviewBulk(U1);out.refusedToast=document.querySelector("#toast").innerHTML;posts.splice(0);
  globalThis.setTimeout=realST;
  // The preview dialog: blocked items, no Apply until they are removed; a limit a manager cannot pass.
  globalThis.askBulk=realAskBulk;
  // Review 12c I1: selected tasks the filters hide are counted in the bar.
  location.hash="#/project/"+U1+"/list";a.bulk.ids=new Set(["a","b"]);a.bulk.pid=U1;
  const barEl=document.querySelector("#bulk-bar");barEl.hidden=true;barEl.innerHTML="";
  const countEl={textContent:""};barEl.querySelector=sel=>sel==="#bulk-count"?countEl:{addEventListener(){},value:"status",set innerHTML(v){}};
  renderBulkBar();out.hiddenNote=countEl.textContent;
  const dlg=document.querySelector("#move-dialog");dlg.showModal=()=>{};dlg.close=()=>{};
  askBulk({...plan,wip:null,blocked:[{id:"c",title:"C <x>",reason:"is already Ready"}],counts:{ok:2,blocked:1}});out.dialogBlocked=document.querySelector("#move-form").innerHTML;
  askBulk({...plan,wip:{...plan.wip,can_override:false}});out.dialogWipManager=document.querySelector("#move-form").innerHTML;
  askBulk(plan);out.dialogWipOwner=document.querySelector("#move-form").innerHTML;
  // Review 12d L2: what the preview lists is escaped, and going over a limit needs the tick.
  const X='<img src=x onerror="globalThis.__xss=5">';
  askBulk({...plan,wip:null,ok:[{id:"a",title:X,revision:3}],blocked:[{id:"c",title:X,reason:X}],impact:[{id:"a",title:X,impact:[X]}],counts:{ok:1,blocked:1}});
  out.dialogXss=document.querySelector("#move-form").innerHTML;out.pickXss=pickBox({id:"z",title:X});
  const pending=askBulk(plan),form=document.querySelector("#move-form"),tick=document.querySelector('[name="override_wip"]');
  document.querySelector("#move-error").textContent="";tick.checked=false;form.onsubmit({preventDefault(){}});
  out.tickError=document.querySelector("#move-error").textContent;tick.checked=true;form.onsubmit({preventDefault(){}});out.ticked=await pending;
  // Only an owner sees Limits…; a member (no project management) sees no pick boxes.
  location.hash="#/project/"+U1+"/board";
  out.limitsManager=a.renderBoard(tasks,"").includes('id="wip-settings"');
  a.state.user={...a.state.user,global_role:"owner"};out.limitsOwner=a.renderBoard(tasks,"").includes('id="wip-settings"');
  a.state.user={...a.state.user,global_role:"member"};a.state.projects[0].can_manage=false;
  const memberBoard=a.renderBoard(tasks,"");out.memberBoard=[memberBoard.includes("bulk-pick"),memberBoard.includes("wip-settings")];
  // Review 12e L1: bulkScope() itself refuses a member on the List route (no pick column), while
  // 3FQEKB lets the Chairman (can_assign) and a manager select.
  location.hash="#/project/"+U1+"/list";a.state.projects[0].can_assign=false;
  const tableEl={innerHTML:""},groups={top:tasks.slice(0,2),childrenOf:new Map(),stepIndex:new Map()};
  out.scopeMember=bulkScope();renderScheduleTable(groups,tableEl);out.memberTable=tableEl.innerHTML.includes("bulk-pick");
  a.state.projects[0].can_assign=true;out.scopeChairman=bulkScope();renderScheduleTable(groups,tableEl);out.chairmanTable=tableEl.innerHTML.includes("bulk-pick");
  // Review 13a L1: on the board the Chairman gets no pick boxes and no list pick column.
  location.hash="#/project/"+U1+"/board";out.scopeChairmanBoard=bulkScope();renderScheduleTable(groups,tableEl);
  out.chairmanBoardTable=tableEl.innerHTML.includes("bulk-pick");out.chairmanBoard=a.renderBoard(tasks,"").includes("bulk-pick");
  location.hash="#/project/"+U1+"/list";
  a.state.projects[0].can_manage=true;out.scopeManager=bulkScope();a.state.projects[0].can_assign=false;
  location.hash="#/project/"+U1+"/board";
  a.state.projects[0].can_manage=true;
  // Shift-click takes the range from the last box; Shift+Arrow adds the next box.
  location.hash="#/project/"+U1+"/list";
  const boxes=["a","b","c","d"].map(id=>{const b={dataset:{pick:id},checked:false,focus(){},matches:()=>false,closest:sel=>sel==="[data-pick]"?b:null};return b});
  const realQSA=document.querySelectorAll;document.querySelectorAll=sel=>sel==="[data-pick]"?boxes:[];
  a.bulk.ids=new Set();a.bulk.last=null;a.bulk.pid=U1;
  const click=(b,shiftKey)=>{b.checked=!b.checked;(docListeners.click||[]).forEach(f=>{try{f({target:b,shiftKey,button:0,preventDefault(){},stopPropagation(){}})}catch{}})};
  click(boxes[0],false);click(boxes[2],true);out.shiftClick=[...a.bulk.ids].sort();
  a.bulk.ids=new Set();a.bulk.last=null;keydown("ArrowDown",boxes[1],{shiftKey:true});out.shiftArrow=[...a.bulk.ids].sort();
  document.querySelectorAll=realQSA;
  // Review 12d M2: the Inbox card names what approving overrides (escaped), and Approve confirms
  // each rule the server names in turn; a cancelled confirm decides nothing.
  a.state.user={id:"u9",display_name:"Aly",global_role:"owner"};
  const req={id:"r1",action:"update_task_status",task_id:"a",task_title:"A",project_id:U1,project_name:"P",requested_by_name:"Sara",
    requested_at:"2026-09-25T10:00:00Z",reason:"back",payload:{status:"in_progress",from_status:"on_hold"},
    gates:{lines:["Waits on "+X,"In progress is at 1 of 1"],column:"progress"}};
  a.renderInbox([],[req,{...req,id:"r2",gates:{lines:[],column:"progress"}}]);out.inboxGates=document.querySelector("#inbox-body").innerHTML;
  globalThis.prompt=()=>"ok";globalThis.openInbox=async()=>{};
  const asks=[];globalThis.askMove=async(kind,task,column)=>{asks.push([kind,task.title,column]);return kind==="wip"?{override_wip:true}:{override_dependencies:true}};
  let n=0;posts.splice(0);
  reply=u=>u.includes("/decision")?(++n===1?{status:409,body:{error:"waits",confirm:"dependencies",impact:["Pre"]}}:n===2?{status:409,body:{error:"full",confirm:"wip",impact:["full"]}}:{body:{request:{}}}):null;
  await decideOwnerRequest("r1","approved");out.decisionPosts=posts.splice(0).filter(p=>p[0].includes("/decision")).map(p=>p[1]);out.decisionAsks=asks.splice(0);
  globalThis.askMove=async()=>null;n=0;await decideOwnerRequest("r1","approved");
  out.cancelledPosts=posts.splice(0).map(p=>p[0]);
  // 3FQEKB: pickers ask for the purpose, label viewers and keep a current owner the rules now forbid.
  const opts=[];const sel={innerHTML:"",add:o=>opts.push([o.text,o.value,!!o.selected])};
  reply=u=>u.startsWith("/api/assignable-users")?{body:{users:[{id:"u-m",display_name:"Mo Member",project_role:"member"},{id:"u-v",display_name:"Vi <b>Viewer</b>",project_role:"viewer"}]}}:null;
  posts.splice(0);await fillAssignees(U1,sel,"u-chair","subtask","Chair Person");
  out.pickerUrl=posts.splice(0).map(p=>p[0]);out.pickerOptions=opts.splice(0);
  await fillAssignees(U1,sel,"u-m");out.pickerKept=opts.splice(0);
  // The chip on a card and a List row, and the Home tile for owners and managers only.
  const flagged=T({id:"f",title:"Flagged",needs_new_assignee:true,owner_name:"Chair Person"});
  out.flaggedCard=boardCard(flagged,[],true);out.plainCard=boardCard(T({id:"p",title:"Plain"}),[],true);
  out.collabCard=boardCard(T({id:"k",title:"Collab",needs_new_collaborator:true}),[],true);
  const rowEl={innerHTML:""};location.hash="#/project/"+U1+"/list";
  renderScheduleTable({top:[flagged],childrenOf:new Map(),stepIndex:new Map()},rowEl);out.flaggedRow=rowEl.innerHTML;
  a.state.tasks=[flagged,T({id:"q",title:"Other"})];
  const tiles=()=>homeTiles().map(t=>t[0]+":"+t[3]);
  a.state.user={id:"u9",display_name:"Aly",global_role:"owner"};out.tilesOwner=tiles();
  a.state.user={id:"u2",display_name:"PM",global_role:"member"};out.tilesManager=tiles();
  a.state.projects[0].can_manage=false;a.state.projects[0].can_assign=true;out.tilesChairman=tiles();
  // The Chairman's bulk bar offers Assign only.
  const bar2=document.querySelector("#bulk-bar");bar2.hidden=true;bar2.innerHTML="";
  bar2.querySelector=sel=>sel==="#bulk-count"?{textContent:""}:{addEventListener(){},value:"assignee",set innerHTML(v){}};
  a.bulk.ids=new Set(["f"]);a.bulk.pid=U1;a.bulk.action="status";renderBulkBar();out.chairmanBar=bar2.innerHTML;out.chairmanAction=a.bulk.action;
  a.state.projects[0].can_manage=true;a.state.projects[0].can_assign=false;
  process.stdout.write(JSON.stringify(out));return;
}
if(mode==="work"){
  // FKVHH8: My Work groups, the month calendar and the Inbox tabs.
  const T=o=>({project_id:"p1",project_name:"P",status:"in_progress",owner_user_id:"u1",due_state:"scheduled",days_to_due:20,due_date:"2026-10-15",...o});
  const body=()=>document.querySelector("#my-work-body").innerHTML,inbox=()=>document.querySelector("#inbox-body").innerHTML;
  a.state.user={id:"u1",display_name:"Omar M",global_role:"member"};a.state.today="2026-09-25";
  a.state.tasks=[T({id:"w7",title:"Edge",days_to_due:7,due_date:"2026-10-02"}),T({id:"l8",title:"Past edge",days_to_due:8,due_date:"2026-10-03"}),
    T({id:"o1",title:"Late",due_state:"overdue",days_to_due:-2,due_date:"2026-09-23"}),T({id:"d1",title:"Now",due_state:"today",days_to_due:0,due_date:"2026-09-25"}),
    T({id:"w1",title:"Soon",days_to_due:4,due_date:"2026-09-29"}),T({id:"l1",title:"Later <b>x</b>"}),T({id:"n1t",title:"Someday",due_state:"undated",days_to_due:null,due_date:null}),
    T({id:"x1",title:"Not mine",owner_user_id:"u2",days_to_due:5,due_date:"2026-09-30"}),T({id:"c1",title:"Done",status:"completed",due_state:"closed"})];
  location.hash="#/my-work";a.renderMyWork(a.parseRoute("#/my-work"));out.list=body();
  a.state.workQuery="soon";a.renderMyWork(a.parseRoute("#/my-work"));out.filtered=body();
  a.state.workQuery="zzz";a.renderMyWork(a.parseRoute("#/my-work"));out.noMatch=body();a.state.workQuery="";
  const mine=a.state.tasks.filter(t=>t.owner_user_id==="u1"&&t.status!=="completed");
  const many=[...Array(5)].map((_,i)=>T({id:"m"+i,title:i?"Many "+i:"Many <img src=x>",due_date:"2026-09-30",days_to_due:5}));
  out.month=a.calendarMonth([...mine,...many],2026,8,"2026-09-25","mine");
  a.calExpanded.add("2026-09-30");out.expanded=a.calendarMonth([...mine,...many],2026,8,"2026-09-25","all");a.calExpanded.clear();
  out.feb=a.calendarMonth([],2027,1,"2026-09-25","mine");
  location.hash="#/my-work/calendar?month=2026-10&scope=all";a.renderMyWork(a.parseRoute(location.hash));out.calRoute=body();
  location.hash="#/my-work";a.renderMyWork(a.parseRoute("#/my-work"));out.listAfterCal=body();
  // No month in the link: the server's today decides the month and the today ring, not the browser's clock.
  location.hash="#/my-work/calendar";a.renderMyWork(a.parseRoute(location.hash));out.calDefault=body();
  a.state.today="2026-10-01";a.renderMyWork(a.parseRoute(location.hash));out.calNewMonth=body();a.state.today="2026-09-25";
  a.state.tasks=[];a.renderMyWork(a.parseRoute("#/my-work"));out.emptyList=body();
  // 3C1Z74: the Gantt today line and the portfolio "As of" follow the server's today (25 Sep), not the
  // browser's clock (24 Sep). The project starts on 25 Sep, so its start line and the today line coincide.
  a.state.projects=[{id:"p1",name:"P",start_date:"2026-09-25",target_date:"2026-10-20",entities:[]}];a.state.viewOverride="chart";a.state.timezone="Asia/Karachi";
  try{a.renderGantt([T({id:"g1",title:"G",start_date:"2026-09-20",due_date:"2026-09-30"})]);out.gantt=document.querySelector("#gantt").innerHTML}catch(e){out.ganttError=String(e.stack)}
  out.asOf=a.asOfText();a.state.viewOverride=null;
  const N=[{id:"n1",summary:"task assigned: Alpha",task_id:U1,task_title:"Alpha",created_at:new Date().toISOString(),read_at:null},
    {id:"n2",summary:"old <i>note</i>",task_id:null,task_title:null,created_at:"2026-01-02T10:00:00Z",read_at:"2026-01-03T00:00:00Z"}];
  const R=[{id:"r1",action:"close_project",project_name:"P",requested_by_name:"Mia",requested_at:"2026-09-24T10:00:00Z",reason:"done",payload:{}}];
  location.hash="#/inbox";a.renderInbox(N,[]);out.memberDefault=inbox();
  location.hash="#/inbox?tab=all";a.renderInbox(N,[]);out.memberAll=inbox();
  location.hash="#/inbox?tab=needs";a.renderInbox(N,[]);out.memberNeeds=inbox();
  location.hash="#/inbox";a.renderInbox(N.map(n=>({...n,read_at:"2026-09-25T00:00:00Z"})),[]);out.memberAllRead=inbox();
  a.state.user.global_role="owner";
  location.hash="#/inbox";a.renderInbox(N,R);out.ownerDefault=inbox();
  location.hash="#/inbox?tab=all";a.renderInbox(N,R);out.ownerAll=inbox();
  location.hash="#/inbox?tab=unread";a.renderInbox(N,R);out.ownerUnread=inbox();
  location.hash="#/inbox";a.renderInbox([],[]);out.ownerEmpty=inbox();
  process.stdout.write(JSON.stringify(out));return;
}
if(mode!=="main"){
  for(let i=0;i<10;i++)await tick();
  out.login=document.querySelector("#login").hidden;out.app=document.querySelector("#app").hidden;
  out.toast=document.querySelector("#toast").innerHTML;out.fetches=fetches.slice(0,1);
  process.stdout.write(JSON.stringify(out));return;
}
const panel=document.querySelector("#detail-dialog"),app=document.querySelector("#app");
let closes=0;panel.addEventListener("close",()=>closes++);
const snap=()=>({hash:location.hash,hidden:panel.hidden,app:app._classes(),calls:calls.splice(0),closes,full:document.querySelector("#detail-full").getAttribute("href"),focused:globalThis.__focused||null});
// Router
out.parsed=["","#","#/","#/home","#/my-work","#/inbox","#/projects","#/nope","#main","#/home?status=delayed&open=1",
  "#/task/"+U1,"#/task/a%2Fb","#/task/%E0%A4%A","#/home/%zz","#/task/"]
  .map(h=>{const p=a.parseRoute(h);return [p.name,p.id,p.params.toString()]});
a.filtersFromUrl(new URLSearchParams("project=p1&status=delayed&entity=e1&crit=unrated&due=7&owner=Sara%20K&sort=due_date&open=1"));
out.values=["#project-filter","#status-filter","#entity-filter","#crit-filter","#band-filter","#owner-filter","#sort-filter"].map(s=>document.querySelector(s).value);
out.open=document.querySelector("#open-only").checked;
out.query=a.homeQuery();a.syncFilters();
out.replaced=calls.splice(0);out.homeHref=a.state.portfolioHash;
a.filtersFromUrl(new URLSearchParams(""));out.cleared=a.homeQuery();out.sortDefault=document.querySelector("#sort-filter").value;
out.hashchange=typeof globalThis.__on_hashchange;out.pushState=typeof history.pushState;
a.state.user=null;out.noUser=a.applyRoute(true)===undefined;
// Escaping: a filter value and a toast text written as markup must come back as text.
document.querySelector("#owner-filter").value='<img src=x onerror=alert(1)>';a.state.tasks=[];a.noteFilters(0);
out.chips=document.querySelector("#filter-note").innerHTML;
a.showToast('“<img src=x onerror=alert(2)>” was added',"Show <b>it</b>",()=>{});out.toast=document.querySelector("#toast").innerHTML;
document.querySelector("#owner-filter").value="";calls.splice(0);
// Role gating: owner-only items in the More menu and the account menu.
out.roles={};
for(const [role,pid] of [["member","p1"],["owner",""],["owner","p1"]]){
  a.state.user={id:"u",display_name:"A B",global_role:role};document.querySelector("#project-filter").value=pid;a.projectActions();a.showApp();
  out.roles[role+(pid?"+project":"")]=["#close-project","#save-template-btn","#project-history-btn","#people","#new-project"].map(s=>document.querySelector(s).hidden);
}
document.querySelector("#project-filter").value="";
// Menus toggle aria-expanded.
const more=document.querySelector("#more-btn");
more._listeners.click[0]({detail:1});out.menuOpen=[more.getAttribute("aria-expanded"),document.querySelector("#more-menu").hidden];
more._listeners.click[0]({detail:1});out.menuClosed=[more.getAttribute("aria-expanded"),document.querySelector("#more-menu").hidden];
// Keys: no page-wide single-key shortcuts; Ctrl K still focuses search.
a.state.user={id:"u",display_name:"A B",global_role:"owner"};globalThis.__focused=null;
out.slash=[keydown("/",document.body),globalThis.__focused,document.querySelector("#keys-dialog").open];
out.question=[keydown("?",document.body),document.querySelector("#keys-dialog").open];
keydown("k",document.body,{ctrlKey:true});out.ctrlK=globalThis.__focused;
// Panel: open, swap, close; focus returns to the opener.
location.hash="#/home?status=delayed";calls.splice(0);
const opener=document.querySelector("#opener");opener.focus();
a.openPanel(U1);out.open1=snap();
a.openPanel(U2);out.swap=snap();
out.jOutside=keydown("j",document.body);
out.jInside=keydown("j",panel);
const field=el("#field");field.closest=s=>s.includes("input")?field:null;panel.contains=n=>n===panel||n===field;field.focus();
out.escField=[keydown("Escape",field),globalThis.__focused,panel.hidden];
a.closePanel(false);out.close=snap();
// A re-rendered opener is found again by its task id.
const gone=document.querySelector("#gone");gone.focus();gone.setAttribute("data-detail",U1);gone.dataset.detail=U1;gone.classList.add("link");
a.openPanel(U1);gone.isConnected=false;
const again=document.querySelector(`[data-view]:not([hidden]) .link[data-detail="${U1}"]`)||(store[`[data-view]:not([hidden]) .link[data-detail="${U1}"]`]=el("replacement"));
a.closePanel(false);out.reopenedFocus=snap();
// M2: a filter picked while the panel is open survives closing it.
location.hash="#/portfolio";calls.splice(0);document.querySelector("#body").focus();
a.openPanel(U1);document.querySelector("#crit-filter").value="critical";a.syncFilters();out.filterWhileOpen=snap();
a.closePanel(false);out.filterKept=snap();
document.querySelector("#crit-filter").value="";
// A panel opened from a link closes with replaceState, never leaving the app.
location.hash="#/inbox?task="+U3;a.panelState.pushed=null;calls.splice(0);
a.openPanel(U3);out.linkOpen=snap();a.closePanel(false);out.linkClose=snap();
// The task page is the same panel and closes to the last screen.
location.hash="#/task/"+U2;a.panelState.lastView="#/my-work";calls.splice(0);
a.openPanel(U2);out.pageOpen=snap();a.closePanel(false);out.pageClose=snap();
a.closePanel(false);out.closeTwice=snap();
out.links=[a.taskLink("a/b"),a.taskApi("a/b","/events"),a.routeHash(a.parseRoute("#/home?due=7&task=x"),null),a.routeHash(a.parseRoute("#/my-work"),"y z")];
// L1: a link whose task id is not a task id fetches nothing; the first load after sign-in fetches the task again.
a.state.user={id:"u",display_name:"A B",global_role:"owner"};a.state.projects=[];a.state.tasks=[];
fetches.splice(0);location.hash="#/my-work?task=..%2F..%2Fapi%2Fusers";a.applyRoute(false,false);out.badIdFetches=fetches.slice();
a.closePanel(true);a.panelState.shown=U1;panel.hidden=false;fetches.splice(0);location.hash="#/my-work?task="+U1;a.state.loads=1;a.applyRoute(false,true);
out.firstLoadFetches=fetches.slice();
// Re-review: j/k follow the screen's own order of task links (deduplicated).
const realQSA=document.querySelectorAll;
document.querySelectorAll=s=>s.includes("[data-detail]")?[U3,U1,U3,U2].map(id=>({dataset:{detail:id},closest:()=>null})):[];
location.hash="#/my-work?task="+U1;a.panelState.shown=U1;calls.splice(0);fetches.splice(0);
a.stepPanel(1);out.jNext=[calls.splice(0),fetches.splice(0)];
location.hash="#/my-work?task="+U1;a.panelState.shown=U1;a.stepPanel(-1);out.kPrev=[calls.splice(0),fetches.splice(0)];
a.panelState.shown=U2;a.stepPanel(1);out.jAtEnd=[calls.splice(0),fetches.splice(0)];
document.querySelectorAll=realQSA;
// 3C1Z74 review M1: while the panel covers the screen, the rail, top bar and skip link are inert.
const inert=()=>[".rail",".topbar","#skip-link"].map(s=>document.querySelector(s).getAttribute("inert"));
a.closePanel(true);location.hash="#/my-work";globalThis.__narrow=true;a.openPanel(U2);out.inertNarrowOpen=inert();
a.closePanel(true);out.inertNarrowClosed=inert();
globalThis.__narrow=false;a.openPanel(U2);out.inertWideOpen=inert();a.closePanel(true);
// Re-review N1/N2: only a plain notice gets a timer; any notice is cleared when the screen changes.
const realST=globalThis.setTimeout;let timers=[];globalThis.setTimeout=(f,ms)=>{timers.push(ms);return 0};
location.hash="#/home";
a.showToast("plain");const plainTimers=timers.splice(0);
a.showToast("with action","Show it",()=>{});const actionTimers=timers.splice(0);
a.showToast("copy by hand",null,null,true);const stickyTimers=timers.splice(0);out.stickyHtml=document.querySelector("#toast").innerHTML;
globalThis.setTimeout=realST;
out.toastTimers=[plainTimers,actionTimers,stickyTimers];
a.state.user=null;location.hash="#/home?task="+U1;globalThis.__on_hashchange();out.toastSameScreen=document.querySelector("#toast").innerHTML!=="";
location.hash="#/my-work";globalThis.__on_hashchange();out.toastOtherScreen=document.querySelector("#toast").innerHTML;
// H1: signing out reloads the page (no DOM or state survives for the next person).
calls.splice(0);globalThis.fetch=async u=>({ok:true,status:200,json:async()=>({})});
await document.querySelector("#logout").onclick();await document.querySelector("#logout-all").onclick();
out.signOut=[calls.filter(c=>c[0]==="location.replace"),a.state.user];
process.stdout.write(JSON.stringify(out));
})().catch(e=>{console.error(e);process.exit(1)});
"""


# FKVHH8 review M1: the browser is in Pago Pago (UTC-11) at 10:00 on 24 Sep while the server's day
# (Asia/Karachi) is already 25 Sep; anything that trusts the browser's clock lands a day early.
BROWSER_ELSEWHERE = {"TZ": "Pacific/Pago_Pago", "FAKE_NOW": "2026-09-24T21:00:00Z"}


def _run_shell_driver(mode, env=None):
    with tempfile.TemporaryDirectory() as tmp:
        driver = Path(tmp) / "shell.js"
        driver.write_text(SHELL_DRIVER, encoding="utf-8")
        result = subprocess.run(["node", str(driver), str(STATIC / "app.js"), mode],
                                capture_output=True, text=True, timeout=60,
                                env={**os.environ, **(env or {})})
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


U1, U2, U3 = ("11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222",
              "33333333-3333-4333-8333-333333333333")


@unittest.skipUnless(shutil.which("node"), "node is needed to run app.js")
class AstraShellRouterTests(unittest.TestCase):
    """PZTYC9: one link per screen, and the Home filters survive reload, Back and a pasted link."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run_shell_driver("main")
        cls.js = (STATIC / "app.js").read_text(encoding="utf-8")
        cls.html = (STATIC / "index.html").read_text(encoding="utf-8")

    def test_routes_parse_and_unknown_or_malformed_hashes_fall_back_to_home(self):
        home = ["home", None, ""]
        self.assertEqual(self.out["parsed"], [
            home, home, home, home, ["my-work", None, ""], ["inbox", None, ""], ["projects", None, ""], home,
            home, ["home", None, "status=delayed&open=1"], ["task", U1, ""],
            home, home, home, home])   # not a task id; truncated %-escape (review M3); bad escape; no id

    def test_filters_round_trip_through_the_url_with_replace_state(self):
        self.assertEqual(self.out["values"], ["p1", "delayed", "e1", "unrated", "7", "Sara K", "due_date"])
        self.assertTrue(self.out["open"])
        query = "project=p1&status=delayed&entity=e1&crit=unrated&due=7&owner=Sara+K&sort=due_date&open=1"
        self.assertEqual(self.out["query"], query)
        # VPYGY5: the filtered dashboard is #/portfolio; Home is the Command Center.
        self.assertEqual(self.out["replaced"], [["replace", "#/portfolio?" + query]])
        self.assertEqual(self.out["homeHref"], "#/portfolio?" + query)
        self.assertEqual(self.out["cleared"], "")
        self.assertEqual(self.out["sortDefault"], "criticality")

    def test_router_needs_no_push_state(self):
        self.assertEqual(self.out["pushState"], "undefined")
        self.assertEqual(self.out["hashchange"], "function")
        self.assertTrue(self.out["noUser"])
        self.assertNotRegex(self.js, r"\.pushState\(")

    def test_chip_and_toast_text_is_escaped(self):
        # Lock #9 review M5: a filter value or task title written as markup comes back as text.
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;<span", self.out["chips"])
        self.assertIn('id="clear-filters" data-clear="all">Clear all</button>', self.out["chips"])
        self.assertIn("&lt;img src=x onerror=alert(2)&gt;", self.out["toast"])
        self.assertIn("Show &lt;b&gt;it&lt;/b&gt;", self.out["toast"])
        self.assertIn('id="toast-dismiss"', self.out["toast"])
        for html in (self.out["chips"], self.out["toast"]):
            self.assertNotIn("<img", html)
            self.assertNotIn("<b>", html)

    def test_notices_with_an_action_or_a_manual_step_have_no_timer_and_stay_on_their_screen(self):
        # Lock #9 re-review N1/N2 and L9.
        self.assertEqual(self.out["toastTimers"], [[6000], [], []])
        self.assertIn('id="toast-dismiss"', self.out["stickyHtml"])
        self.assertTrue(self.out["toastSameScreen"])      # the task param changing is the same screen
        self.assertEqual(self.out["toastOtherScreen"], "")

    def test_owner_only_items_are_hidden_for_other_roles(self):
        # [close project, save as template, project history, people, new project] hidden?
        self.assertEqual(self.out["roles"]["member+project"], [True, True, False, True, True])
        self.assertEqual(self.out["roles"]["owner"], [True, True, True, False, False])
        self.assertEqual(self.out["roles"]["owner+project"], [False, False, False, False, False])

    def test_menus_toggle_aria_expanded(self):
        self.assertEqual(self.out["menuOpen"], ["true", False])
        self.assertEqual(self.out["menuClosed"], ["false", True])

    def test_no_page_wide_single_key_shortcuts(self):
        # Lock #9 review M4 (WCAG 2.1.4): / and ? do nothing; Ctrl K still reaches search.
        self.assertEqual(self.out["slash"], [False, None, False])
        self.assertEqual(self.out["question"], [False, False])
        self.assertEqual(self.out["ctrlK"], "#search-box")
        self.assertIn('aria-keyshortcuts="Control+K"', self.html)
        self.assertIn('role="menuitem" id="keys-btn">Keyboard shortcuts</button>', self.html)

    def test_signing_out_reloads_the_page(self):
        # Lock #9 review H1: nothing the previous person saw survives for the next one.
        replaced, user = self.out["signOut"]
        self.assertEqual(replaced, [["location.replace", "/"], ["location.replace", "/"]])
        self.assertIsNone(user)

    def test_a_failed_first_load_is_not_a_sign_out(self):
        # Lock #9 review M3: /api/me succeeded, the task load failed: stay signed in and say so.
        out = _run_shell_driver("boot-load-fails")
        self.assertTrue(out["login"])
        self.assertFalse(out["app"])
        self.assertIn("could not load your work (server down)", out["toast"])
        out = _run_shell_driver("boot-me-fails")
        self.assertFalse(out["login"])

    def test_home_command_center_for_owner_member_and_empty_install(self):
        out = _run_shell_driver("home", BROWSER_ELSEWHERE)
        owner, member = out["owner"], out["member"]
        tiles = dict(re.findall(r'data-tile="(\w+)" data-tone="\w+" href="([^"]+)"><strong>(\d+)</strong>', owner["strip"]) and
                     [(k, (h, int(n))) for k, h, n in re.findall(r'data-tile="(\w+)" data-tone="\w+" href="([^"]+)"><strong>(\d+)</strong>', owner["strip"])])
        self.assertEqual(tiles, {
            "overdue": ("#/portfolio?due=overdue&open=1", 1), "blocked": ("#/portfolio?risk=blocked&open=1", 1),
            "awaiting": ("#/inbox", 1), "week": ("#/portfolio?due=7&open=1", 4),
            "critical": ("#/portfolio?risk=critical&open=1", 1), "undated": ("#/portfolio?due=undated&open=1", 1)})
        # Review L5: "as of" is said once for the row, not on every tile.
        self.assertIn("Open work past its due date</span>", owner["strip"])
        self.assertNotIn("as of", owner["strip"])
        self.assertTrue(owner["asof"].startswith("Counts as of "))
        # Owner decisions: live buttons, a Review that opens the task, text escaped.
        self.assertFalse(owner["decisionsHidden"])
        self.assertIn('data-home-decision="approved" data-request-id="r1"', owner["decisions"])
        self.assertIn('data-home-decision="rejected" data-request-id="r1"', owner["decisions"])
        self.assertIn(f'data-detail="{U1}">Review</button>', owner["decisions"])
        self.assertIn("&lt;b&gt;Tax&lt;/b&gt;", owner["decisions"])
        self.assertEqual(out["clicks"][:2], ["/api/owner-action-requests/r1/decision", f"/api/tasks/{U1}"])
        # My next actions: my open work grouped Today / This week / Later; closed work never shows.
        nxt = owner["next"]
        self.assertLess(nxt.index(">Today<"), nxt.index('data-detail="t1"'))
        self.assertLess(nxt.index('data-detail="t6"'), nxt.index(">This week<"))
        self.assertLess(nxt.index(">This week<"), nxt.index('data-detail="t5"'))
        self.assertLess(nxt.index(">Later<"), nxt.index('data-detail="t4"'))
        self.assertNotIn('data-detail="t2"', nxt)
        self.assertIn("Late &lt;img src=x onerror=alert(1)&gt;", nxt)
        # At risk: worst first, open only.
        risk = owner["risk"]
        self.assertEqual(re.findall(r'data-detail="(t\d)"', risk), ["t1", "t2", "t3"])
        self.assertIn("▲ 3 days overdue", risk)
        self.assertIn("⊘ Blocked", risk)
        self.assertIn("◆ Critical path", risk)
        # Review M1/M2: the strip is today plus the next 7 days, labelled from the server's today (25 Sep)
        # although the browser's clock says 24 Sep, and its bars add up to the "Due in 7 days" tile.
        week = owner["week"]
        days = re.findall(r'<strong>(\d+)</strong><span>([^<]+)</span>', week)
        self.assertEqual([d for _, d in days], ["Today", "Sat 26", "Sun 27", "Mon 28", "Tue 29", "Wed 30", "Thu 1", "Fri 2"])
        self.assertEqual(sum(int(n) for n, _ in days), tiles["week"][1])
        self.assertEqual(days[7][0], "1")  # t8, due in exactly 7 days, is inside the week
        self.assertIn("due Friday 2 October", week)
        self.assertIn("Today and the next 7 days · 4 open items due", week)
        self.assertEqual(out["portfolioFetches"], 1)
        self.assertNotIn("homeRouteError", out)
        # A member sees no Awaiting Owner tile and no decisions.
        self.assertNotIn('data-tile="awaiting"', member["strip"])
        self.assertTrue(member["decisionsHidden"])
        # A new install: one empty state, with the next step only for the owner.
        self.assertFalse(out["emptyOwner"]["empty"])
        self.assertTrue(out["emptyOwner"]["grid"])
        # Lock #11: the Portfolio Gantt button shows once there is a project, and not on an empty install.
        self.assertFalse(owner["ganttLinkHidden"])
        self.assertTrue(out["emptyOwner"]["ganttLinkHidden"])
        self.assertTrue(out["emptyMember"]["decisionsHidden"])
        # Old dashboard links move to the portfolio timeline.
        self.assertNotIn("routeError", out)
        self.assertEqual(out["redirect"], [[["replace", "#/portfolio?due=7&open=1"]], "#/portfolio?due=7&open=1"])

    def test_shell_landmarks_rail_top_bar_and_menus(self):
        html = self.html
        self.assertIn('<nav class="rail" aria-label="Main">', html)
        for href, label in (("#/home", "Home"), ("#/my-work", "My Work"), ("#/inbox", "Inbox"), ("#/projects", "Projects")):
            self.assertRegex(html, rf'<a class="rail-item" href="{href}" data-nav="{href[2:]}"[^>]*>.*?<span>{label}</span>')
        self.assertRegex(html, r'<button type="button" class="rail-item" id="new-task">.*?<span>Capture</span></button>')
        self.assertIn('<a class="skip-link" id="skip-link" href="#main">Skip to content</a>', html)
        self.assertIn('<main id="main" tabindex="-1">', html)
        user_menu = html[html.index('id="user-menu"'):]
        user_menu = user_menu[:user_menu.index("</div>\n      </div>")]
        for item in ('id="people"', 'id="keys-btn"', 'id="logout"', 'id="logout-all"'):
            self.assertIn(item, user_menu)
        more = html[html.index('id="more-menu"'):]
        more = more[:more.index("</div>")]
        for item in ("portfolio-btn", "final-results-btn", "templates-btn", "import-btn", "export-btn",
                     "project-history-btn", "save-template-btn", "close-project"):
            self.assertIn(f'role="menuitem" id="{item}"', more)
        # The filter bar holds filters only; Clear all is rendered at the end of the chip row.
        toolbar = html[html.index('<section class="toolbar"'):]
        toolbar = toolbar[:toolbar.index("</section>")]
        self.assertNotIn("<button", toolbar)
        self.assertNotIn('id="inbox-dialog"', html)
        self.assertRegex(html, r'data-view="inbox"[^>]*><div id="inbox-body"')
        self.assertRegex(html, r'data-view="projects"[^>]*>\s*<div class="page-actions"><a class="quiet button-link portfolio-link" href="#/portfolio">Portfolio timeline</a><button type="button" id="new-project" hidden>')
        self.assertIn("Portfolio Gantt", html)
        self.assertIn('<dialog id="keys-dialog"', html)
        self.assertIn('<div id="toast" class="toast" role="status" aria-live="polite"></div>', html)

    def test_capture_reuses_the_create_form(self):
        self.assertIn('<h2 id="task-dialog-title">Capture a task</h2>', self.html)
        self.assertIn('<details class="more-fields"><summary>More fields</summary>', self.html)
        self.assertIn('document.querySelector("#new-task").onclick=openCapture;', self.js)
        self.assertIn('showToast(`“${task.title}” was added · the current filters hide it`,"Show it",showAllOnPortfolio)', self.js)
        self.assertIn('data-request-decision="approved"', self.js)


@unittest.skipUnless(shutil.which("node"), "node is needed to run app.js")
class AstraProjectPageTests(unittest.TestCase):
    """CR121Z: the project page, its tabs and the read-only board."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run_shell_driver("board")

    def test_statuses_map_into_seven_columns(self):
        self.assertEqual(self.out["columns"], {
            "draft": "draft", "assigned": "ready", "in_progress": "progress", "reopened": "progress",
            "changes_requested": "progress", "delayed": "progress", "on_hold": "blocked", "submitted": "submitted",
            "completed": "accepted", "cancelled": "closed", "abandoned": "closed"})
        # Waiting on a predecessor moves open work to Blocked; submitted and closed work stays put.
        blocked = self.out["blockedColumns"]
        for status in ("draft", "assigned", "in_progress", "reopened", "changes_requested", "delayed", "on_hold"):
            self.assertEqual(blocked[status], "blocked", status)
        self.assertEqual((blocked["submitted"], blocked["completed"], blocked["cancelled"]), ("submitted", "accepted", "closed"))

    def test_board_cards_columns_and_collapsed_owner_columns(self):
        board = self.out["board"]
        heads = re.findall(r'class="col col-head[^"]*" data-col="(\w+)"', board)
        self.assertEqual(heads, ["draft", "ready", "progress", "blocked", "submitted", "accepted", "closed"])
        # Steps are not cards; their parent says how many are done.
        self.assertEqual(re.findall(r'data-detail="(\w)"', board), ["a", "b"])
        self.assertIn("Steps 1 of 2 done", board)
        self.assertIn("⊘ Waits on Plan", board)
        self.assertIn("◆ Critical path", board)
        self.assertIn("Plan &lt;img src=x onerror=alert(1)&gt;", board)
        self.assertNotIn("<img", board)
        # Accepted and Closed start collapsed with a toggle; their cards are counted, not drawn.
        self.assertIn('data-toggle-col="accepted" aria-expanded="false"', board)
        self.assertIn('data-toggle-col="closed" aria-expanded="false"', board)
        self.assertIn('<p class="col-hidden">1</p>', board)
        self.assertIn("No tasks in this project yet.", self.out["emptyBoard"])

    def test_divide_by_owner_and_criticality(self):
        lanes = lambda html: re.findall(r'<h3 class="lane-head">([^<]+) <span class="count">(\d+)</span>', html)
        self.assertEqual(lanes(self.out["byOwner"]), [("Omar Malik", "1"), ("Sara Khan", "2"), ("Unassigned", "1")])
        self.assertEqual(lanes(self.out["byCrit"]), [("High", "2"), ("Low", "1"), ("Unrated", "1")])
        self.assertEqual(lanes(self.out["board"]), [])
        self.assertIn('<option value="owner" selected>Owner</option>', self.out["byOwner"])
        # Review L3: owner names can come from an import file, so lane names are escaped.
        self.assertIn('<h3 class="lane-head">&lt;b&gt;x&lt;/b&gt; <span class="count">1</span></h3>', self.out["evilLanes"])
        self.assertNotIn("<b>x</b>", self.out["evilLanes"])
        # 3C1Z74: lanes are keyed by user id; two people named Sara Khan get two lanes.
        self.assertEqual(lanes(self.out["sameName"]), [("Sara Khan (1 of 2)", "2"), ("Sara Khan (2 of 2)", "1")])
        # Review L6: an unrated card shows no rating badge; the task panel still flags it.
        self.assertNotIn("Unrated", self.out["board"].split("board-card", 1)[1].split("</article>", 1)[0])
        css = (STATIC / "style.css").read_text(encoding="utf-8")
        self.assertIn(".lane-head { position: sticky; left: 0;", css)

    def test_a_project_timeline_uses_its_own_today_and_timezone(self):
        self.assertNotIn("timelineError", self.out)
        self.assertTrue(self.out["timelineAsOf"].endswith("(Pacific/Auckland)"), self.out["timelineAsOf"])
        self.assertIn("26", self.out["timelineAsOf"])
        gantt = self.out["timelineGantt"]
        today = re.findall(r'class="today-line" data-x="([^"]+)"', gantt)
        start = re.findall(r'class="proj-line start" data-x="([^"]+)"', gantt)
        self.assertTrue(today)
        self.assertEqual(len(set(today)), 1)  # one line, drawn in every row
        self.assertAlmostEqual(float(today[0]), float(start[0]), places=6)  # the project's 26 Sep, not the app's 25th
        self.assertIn('mountGantt(document.querySelector("#gantt-panel"),null);state.ganttDay=null;', (STATIC / "app.js").read_text(encoding="utf-8"))

    def test_an_unknown_project_tab_is_rewritten_to_overview(self):
        self.assertNotIn("tabRouteError", self.out)
        self.assertEqual(self.out["tabFix"], [[["replace", f"#/project/{U1}/overview?divide=owner"]], f"#/project/{U1}/overview?divide=owner"])

    def test_header_and_every_lane_share_one_grid_template(self):
        html = self.out["byOwner"]
        # Every row, header included, is a .board-cols grid with seven cells, so one CSS template sizes them all.
        rows = re.findall(r'<div class="board-cols( board-head)?"', html)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0], " board-head")
        css = (STATIC / "style.css").read_text(encoding="utf-8")
        rule = re.search(r"\n\.board-cols \{([^}]*)\}", css).group(1)
        self.assertIn("grid-template-columns: repeat(7, minmax(180px, 1fr))", rule)
        # A content-sized row (max-content) let a lane's long titles widen its own columns out of line.
        self.assertIn("min-width: 1332px", rule)
        self.assertNotIn("max-content", rule)

    def test_project_routes_tabs_and_actions(self):
        self.assertEqual(self.out["tabs"], ["overview", "list", "board", "timeline", "activity"])
        self.assertEqual(self.out["routes"], [
            ["project", U1, "board", f"project/{U1}/board", "divide=owner"],
            ["project", U1, "overview", f"project/{U1}/overview", ""],
            ["project", U1, "overview", f"project/{U1}/overview", ""],
            ["home", None, None, "home", ""],                      # not a project id
            ["my-work", "calendar", None, "my-work/calendar", ""],
            ["my-work", None, None, "my-work", ""]])
        self.assertIn("This project is not available", self.out["missing"])
        self.assertIn(f'href="#/project/{U1}/board" aria-current="page">Board</a>', self.out["tabsHtml"])
        # [capture, save as template, close] hidden? Members can add tasks; only owners save or close.
        self.assertEqual(self.out["memberActions"], [False, True, True])
        self.assertEqual(self.out["ownerActions"], [False, False, False])
        self.assertIn("tasks, 2 steps", self.out["facts"])
        self.assertIn('<progress id="project-progress" max="100" value="33">', self.out["overview"])


@unittest.skipUnless(shutil.which("node"), "node is needed to run app.js")
class AstraBoardDragDriverTests(unittest.TestCase):
    """JN1QYG: movable cards, the Move to menu, the dialog each column needs and the Undo round trip."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run_shell_driver("drag")

    def test_only_managers_and_owners_get_movable_cards(self):
        self.assertEqual(self.out["movable"].count('class="link card-move" data-move-menu='), 4)
        self.assertIn('aria-haspopup="menu"', self.out["movable"])
        self.assertIn('aria-label="Move “A &lt;b&gt;” to…">Move to…</button>', self.out["movable"])
        self.assertNotIn("card-move", self.out["readOnly"])
        self.assertNotIn("data-card", self.out["readOnly"])
        self.assertIn("read-only for your role", self.out["readOnly"])

    def test_the_saved_order_decides_the_column(self):
        self.assertEqual(self.out["order"], ["b", "a", "c"])  # rank 1, rank 2, then unranked
        self.assertLess(self.out["movable"].index('data-card="b"'), self.out["movable"].index('data-card="a"'))

    def test_each_column_asks_for_what_its_rule_needs(self):
        self.assertEqual(self.out["kinds"], ["hold", "close", "submit", "accept", None, "reopen", "reopen", None])

    def test_an_ordinary_move_posts_once_and_offers_undo_for_fifteen_seconds(self):
        self.assertEqual(self.out["movePosts"][0], ["/api/tasks/c/board-move", {"to_column": "ready", "expected_revision": 3}])
        self.assertIn("Moved “C” from Draft to Ready.", self.out["moveToast"])
        self.assertIn('id="toast-action">Undo</button>', self.out["moveToast"])
        self.assertIn(15000, self.out["toastTimers"])
        self.assertEqual(self.out["undoPosts"][0], ["/api/tasks/c/undo-move", {"event_id": "ev1"}])
        # ...and the card goes back to its old place in Draft.
        self.assertEqual(self.out["undoPosts"][1], ["/api/projects/11111111-1111-4111-8111-111111111111/board-order",
                                                    {"column": "draft", "task_ids": ["b", "a", "c"]}])

    def test_a_refused_drop_snaps_back_with_the_servers_reason(self):
        self.assertIn("“B” stays in Draft: B waits on A; only an owner may override.", self.out["refusedToast"])
        self.assertNotIn("toast-action", self.out["refusedToast"])
        self.assertEqual(len([p for p in self.out["refusedPosts"] if p[0].endswith("/board-move")]), 1)

    def test_cancelling_the_dialog_sends_nothing(self):
        self.assertEqual(self.out["cancelPosts"], [])

    def test_a_managers_protected_drop_files_a_request(self):
        self.assertEqual(self.out["requestPosts"][0][1], {"to_column": "closed", "expected_revision": 3,
                                                          "status": "cancelled", "reason": "Duplicate"})
        self.assertIn("Sent to an owner for approval: “A &lt;b&gt;” to Closed.", self.out["requestToast"])
        self.assertNotIn("Undo", self.out["requestToast"])

    def test_an_owner_overrides_a_dependency_only_after_confirming(self):
        moves = [p[1] for p in self.out["overridePosts"] if p[0].endswith("/board-move")]
        self.assertEqual(moves, [{"to_column": "progress", "expected_revision": 3},
                                 {"to_column": "progress", "expected_revision": 3, "override_dependencies": True}])

    def test_an_owner_confirms_each_override_once_in_turn(self):
        self.assertEqual(self.out["wipPosts"], [
            {"to_column": "ready", "expected_revision": 3},
            {"to_column": "ready", "expected_revision": 3, "override_dependencies": True},
            {"to_column": "ready", "expected_revision": 3, "override_dependencies": True, "override_wip": True}])

    def test_review_12a_menu_focus_expanded_state_hold_item_and_escaping(self):
        self.assertEqual(self.out["openedExpanded"], "true")
        self.assertEqual(self.out["escape"], {"hidden": True, "focused": "opener", "expanded": "false"})
        self.assertEqual(self.out["closedElsewhere"], "false")
        self.assertTrue(self.out["waitingMenu"].startswith('<button type="button" role="menuitem" data-move-to="blocked">Put on hold'))
        self.assertIn("&lt;img src=x onerror=&quot;globalThis.__xss=1&quot;&gt;", self.out["escapedDialog"])
        self.assertNotIn("<img", self.out["escapedDialog"])
        self.assertEqual(self.out["panelConfirm"], [{"task": {}}, [{}, {"override_dependencies": True}]])
        self.assertEqual(self.out["panelCancel"], [None, [{}]])

    def test_reorder_saves_and_undo_restores_the_previous_order(self):
        url = "/api/projects/11111111-1111-4111-8111-111111111111/board-order"
        self.assertEqual(self.out["orderPosts"], [[url, {"column": "draft", "task_ids": ["c", "b", "a"]}]])
        self.assertEqual(self.out["orderUndoPosts"][0], [url, {"column": "draft", "task_ids": ["b", "a", "c"]}])

    def test_phones_scroll_and_use_the_menu_and_no_inline_styles_are_written(self):
        js = (STATIC / "app.js").read_text(encoding="utf-8")
        css = (STATIC / "style.css").read_text(encoding="utf-8")
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        self.assertIn('e.target.closest(".card-move,.bulk-pick")||phoneMQ.matches)return;', js)  # phones never start a drag
        self.assertIn("if(drag.touch){if(moved>8){clearTimeout(drag.timer);drag.card=null}return}", js)  # a swipe scrolls
        self.assertIn('if(e.key==="Escape"&&drag.active)', js)
        for rule in (".drag-ghost{", ".board .col.drop-target{", ".drop-marker{", ".move-menu{"):
            self.assertIn(rule, css.replace(" {", "{"))
        for hook in ('id="move-dialog"', 'id="move-form"', 'id="move-menu" role="menu"', 'id="board-live" class="sr-only" aria-live="polite"'):
            self.assertIn(hook, html)
        self.assertNotIn("style=", html)

    def test_move_to_menu_lists_the_moves_up_down_first(self):
        menu = self.out["menu"]
        self.assertTrue(menu.startswith('<button type="button" role="menuitem" data-move-to="up">'))
        self.assertLess(menu.index('data-move-to="down"'), menu.index('data-move-to="ready"'))
        self.assertNotIn('data-move-to="draft"', menu)  # its own column is not offered
        self.assertEqual(menu.count('role="menuitem"'), 8)


@unittest.skipUnless(shutil.which("node"), "node is needed to run app.js")
class AstraGanttDragDriverTests(unittest.TestCase):
    """X07XV4: draggable Gantt bars, their date maths, the reschedule round trip and leases."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run_shell_driver("gantt")

    def test_only_open_dated_bars_of_a_managed_project_are_draggable(self):
        self.assertEqual(self.out["canDrag"].count('data-drag="g1"'), 1)
        self.assertEqual(self.out["canDrag"].count("data-drag="), 1)  # not the closed or the undated task
        self.assertIn('<i class="bar-grip start" data-edge="start" aria-hidden="true"></i>', self.out["canDrag"])
        self.assertNotIn("data-drag", self.out["cannotDrag"])
        self.assertNotIn("bar-grip", self.out["cannotDrag"])
        self.assertNotIn("style=", self.out["canDrag"])
        self.assertGreater(int(self.out["span"]), 0)

    def test_moving_and_resizing_shift_the_right_dates_and_never_invert_them(self):
        d = self.out["dates"]
        self.assertEqual(d["move"], {"start_date": "2026-10-08", "due_date": "2026-10-11"})
        self.assertEqual(d["start"], {"start_date": "2026-10-07", "due_date": "2026-10-08"})
        self.assertEqual(d["startClamp"], {"start_date": "2026-10-08", "due_date": "2026-10-08"})
        self.assertEqual(d["end"], {"start_date": "2026-10-05", "due_date": "2026-10-07"})
        self.assertEqual(d["endClamp"], {"start_date": "2026-10-05", "due_date": "2026-10-05"})
        self.assertEqual(d["noStart"], {"start_date": None, "due_date": "2026-10-10"})
        self.assertEqual(d["growStart"], {"start_date": "2026-10-06", "due_date": "2026-10-08"})
        self.assertEqual(self.out["tips"], ["Start Oct 8 · Due Oct 11 (+3 days)", "Due Oct 7 (-1 day)", "No change"])

    def test_an_ordinary_drag_posts_the_dates_and_offers_undo(self):
        self.assertEqual(self.out["movePosts"][0], ["/api/tasks/g1/reschedule", {
            "start_date": "2026-10-08", "due_date": "2026-10-11", "expected_revision": 3}])
        self.assertIn('id="toast-action">Undo</button>', self.out["moveToast"])
        self.assertIn(15000, self.out["timers"])
        self.assertEqual(self.out["undoPosts"][0], ["/api/tasks/g1/undo-move", {"event_id": "ev9"}])

    def test_a_drag_with_consequences_asks_then_retries_confirmed(self):
        moves = [p[1] for p in self.out["impactPosts"] if p[0].endswith("/reschedule")]
        self.assertEqual([m.get("confirmed") for m in moves], [None, True])
        self.assertEqual(self.out["asked"][0][:2], ["impact", ["It is on the critical path."]])
        self.assertIn("The other owners have been told.", self.out["impactToast"])
        self.assertNotIn("Undo", self.out["impactToast"])
        self.assertEqual(len([p for p in self.out["cancelPosts"] if p[0].endswith("/reschedule")]), 1)

    def test_a_refused_drag_keeps_the_dates_and_says_why(self):
        self.assertIn("keeps its dates: The start date (2026-10-20) would be after the due date", self.out["refusedToast"])

    def test_a_lease_is_taken_once_renewed_every_20_seconds_and_released(self):
        self.assertEqual((self.out["take"], self.out["again"]), ({"ok": True}, {"ok": True, "borrowed": False}))
        self.assertEqual(self.out["intervals"], [20000])
        self.assertEqual(self.out["leasePosts"], [["/api/tasks/g1/lock", {"kind": "drag"}],
                                                  ["/api/tasks/g1/lock/release", {"token": "tok1"}]])
        self.assertEqual(self.out["refusedLease"], [False, "Sara <K>"])

    def test_review_12d_escape_puts_the_bar_back_and_an_idle_form_lets_go(self):
        self.assertEqual(self.out["escape"], [None, False, "10%", "4%", 0])
        self.assertEqual(self.out["idle"], [False, [["/api/tasks/g9/lock/release", {"token": "tokI"}]]])

    def test_review_12b_leases_tip_lock_time_touch_and_escaping(self):
        self.assertEqual(self.out["borrow"], {"ok": True, "borrowed": True})
        self.assertEqual(self.out["afterDragDrop"], [True, 0])  # the edit lease is still held
        self.assertEqual(self.out["closeReleased"], [False, [{"token": "tokE"}]])
        self.assertEqual(self.out["reschedReleased"], [False, [{"token": "tokD"}]])
        self.assertEqual(self.out["clampedTip"], "Start Oct 8 (+3 days)")
        message, local = self.out["lockMessage"]
        self.assertIn(f"runs out at {local} unless", message)
        self.assertNotIn("UTC", message)
        self.assertEqual(self.out["startDrag"], {"mouse": True, "touch": False, "phone": False})
        self.assertIn("&lt;img src=x onerror=&quot;globalThis.__xss=3&quot;&gt;", self.out["impactDialog"])
        self.assertNotIn("<img", self.out["impactDialog"])

    def test_others_see_who_holds_a_lock_and_owners_can_force_it(self):
        self.assertIn("Sara &lt;K&gt; is changing this task (an edit)", self.out["banner"])
        self.assertIn('id="force-unlock">Force unlock</button>', self.out["banner"])
        self.assertNotIn("force-unlock", self.out["bannerNoForce"])
        self.assertIn('class="tag lock-chip" data-tone="amber">🔒 Sara &lt;K&gt;', self.out["chipOther"])
        self.assertNotIn("lock-chip", self.out["chipMine"])  # your own lease is not a warning


@unittest.skipUnless(shutil.which("node"), "node is needed to run app.js")
class AstraBulkDriverTests(unittest.TestCase):
    """XV92JJ: selection, the bulk preview and apply round trip, bulk Undo and WIP counts."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run_shell_driver("bulk")

    def test_pick_boxes_show_only_on_a_managed_project_page(self):
        self.assertEqual(self.out["scope"], "11111111-1111-4111-8111-111111111111")
        self.assertEqual(self.out["board"].count('class="bulk-pick"'), 4)
        self.assertIn('class="board-card is-picked" data-card="b"', self.out["board"])
        self.assertIn('aria-label="Select “A”"', self.out["board"])
        self.assertIsNone(self.out["noScope"])
        self.assertNotIn("bulk-pick", self.out["boardElsewhere"])

    def test_column_heads_show_the_limit_and_an_overfull_column(self):
        self.assertIn('<span class="count">2 / 3<span class="sr-only"> (work-in-progress limit 3)</span></span>', self.out["board"])
        self.assertIn('<span class="count over-limit">2 / 1', self.out["board"])

    def test_shift_click_takes_the_range_in_display_order(self):
        self.assertEqual(self.out["range"], [["a", "b", "c"], ["b", "c", "d"], ["b"]])

    def test_preview_then_apply_sends_the_previewed_revisions_and_offers_undo(self):
        posts = [p for p in self.out["applyPosts"] if p[0] != "load" and "import" not in p[0]]
        self.assertEqual(posts[0][1], {"task_ids": ["a", "b"], "action": "status", "value": "ready"})
        self.assertEqual(posts[1][1], {"task_ids": ["a", "b"], "action": "status", "value": "ready",
                                       "expected_revisions": {"a": 3, "b": 4}, "override_wip": True,
                                       "confirmed": False})
        self.assertIn("Changed 2 tasks: status to Ready.", self.out["applyToast"])
        self.assertEqual(self.out["timers"], [15000])
        self.assertEqual(self.out["cleared"], 0)
        self.assertEqual(self.out["undoPosts"][0], ["/api/projects/11111111-1111-4111-8111-111111111111/bulk/undo",
                                                    {"bulk_id": "bk1"}])

    def test_removing_blocked_tasks_narrows_the_selection_and_previews_again(self):
        self.assertEqual(self.out["afterDrop"], ["a", "b"])
        self.assertEqual(self.out["dropPosts"], [["a", "b", "c"], ["a", "b"]])

    def test_a_refused_apply_says_nothing_changed_once(self):
        self.assertIn("“A” changed since the preview; nothing was changed. Preview again.", self.out["refusedToast"])
        self.assertEqual(self.out["refusedToast"].lower().count("nothing was changed"), 1)

    def test_the_bar_counts_selected_tasks_the_filters_hide(self):
        self.assertEqual(self.out["hiddenNote"], "2 selected · 2 hidden by filters")

    def test_the_limits_dialog_saves_every_column_in_one_request(self):
        js = (STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn('body:JSON.stringify({limits:Object.fromEntries(changed.map(k=>[k,data[k]||null])),reason:data.reason})', js)
        self.assertNotIn("for(const k of changed)await api", js)

    def test_review_12e_bulk_scope_refuses_a_member_and_takes_the_chairman(self):
        self.assertIsNone(self.out["scopeMember"])
        self.assertFalse(self.out["memberTable"])
        self.assertEqual(self.out["scopeChairman"], "11111111-1111-4111-8111-111111111111")
        self.assertTrue(self.out["chairmanTable"])
        self.assertEqual(self.out["scopeManager"], "11111111-1111-4111-8111-111111111111")

    def test_3fqekb_pickers_label_viewers_and_keep_a_forbidden_current_owner(self):
        self.assertEqual(self.out["pickerUrl"],
                         ["/api/assignable-users?project_id=11111111-1111-4111-8111-111111111111&for=subtask"])
        self.assertEqual(self.out["pickerOptions"], [["Mo Member", "u-m", False], ["Vi <b>Viewer</b> (viewer)", "u-v", False],
                                                     ["Chair Person (needs a new assignee)", "u-chair", True]])
        self.assertEqual(self.out["pickerKept"], [["Mo Member", "u-m", True], ["Vi <b>Viewer</b> (viewer)", "u-v", False]])

    def test_review_13a_the_chairman_selects_in_the_list_only(self):
        self.assertIsNone(self.out["scopeChairmanBoard"])
        self.assertFalse(self.out["chairmanBoardTable"])
        self.assertFalse(self.out["chairmanBoard"])

    def test_review_13a_a_forbidden_collaborator_flags_the_card(self):
        self.assertIn("⚠ Collaborator not allowed", self.out["collabCard"])
        self.assertNotIn("Needs a new assignee", self.out["collabCard"])

    def test_3fqekb_the_needs_a_new_assignee_chip_and_home_count(self):
        chip = '<span class="tag reassign-chip" data-tone="amber">⚠ Needs a new assignee</span>'
        self.assertIn(chip, self.out["flaggedCard"])
        self.assertNotIn("reassign-chip", self.out["plainCard"])
        self.assertIn(f"Chair Person {chip}</td>", self.out["flaggedRow"])
        self.assertIn("reassign:1", self.out["tilesOwner"])
        self.assertIn("reassign:1", self.out["tilesManager"])
        self.assertNotIn("reassign:1", self.out["tilesChairman"])  # the Chairman manages no project

    def test_3fqekb_the_chairmans_bulk_bar_offers_assign_only(self):
        self.assertIn('<select id="bulk-action"><option value="assignee">Assignee</option></select>', self.out["chairmanBar"])
        self.assertNotIn('value="status"', self.out["chairmanBar"])
        self.assertEqual(self.out["chairmanAction"], "assignee")

    def test_review_12d_the_preview_and_pick_boxes_escape_what_they_show(self):
        for html in (self.out["dialogXss"], self.out["pickXss"]):
            self.assertNotIn("<img", html)
        self.assertEqual(self.out["dialogXss"].count("&lt;img"), 5)  # ok, blocked title and reason, impact title and text
        self.assertIn('aria-label="Select “&lt;img', self.out["pickXss"])

    def test_review_12d_going_over_a_limit_needs_the_tick(self):
        self.assertEqual(self.out["tickError"], "Tick “Go over the limit” to apply, or change fewer tasks.")
        self.assertEqual(self.out["ticked"], {"override_wip": True})

    def test_review_12d_limits_are_an_owners_and_pick_boxes_a_managers(self):
        self.assertFalse(self.out["limitsManager"])
        self.assertTrue(self.out["limitsOwner"])
        self.assertEqual(self.out["memberBoard"], [False, False])

    def test_review_12d_shift_click_and_shift_arrow_select_ranges(self):
        self.assertEqual(self.out["shiftClick"], ["a", "b", "c"])
        self.assertEqual(self.out["shiftArrow"], ["b", "c"])

    def test_review_12d_the_inbox_card_shows_what_approving_overrides(self):
        html = self.out["inboxGates"]
        self.assertNotIn("<img", html)
        self.assertIn('<p class="request-gates"><strong>Approving overrides:</strong> Waits on &lt;img', html)
        self.assertIn(" · In progress is at 1 of 1</p>", html)
        self.assertEqual(html.count("request-gates"), 1)  # a request that overrides nothing says nothing

    def test_review_12d_approve_confirms_each_rule_in_turn(self):
        self.assertEqual(self.out["decisionAsks"], [["dependencies", "A", "progress"], ["wip", "A", "progress"]])
        self.assertEqual(self.out["decisionPosts"], [
            {"decision": "approved", "reason": "ok"},
            {"decision": "approved", "reason": "ok", "override_dependencies": True},
            {"decision": "approved", "reason": "ok", "override_dependencies": True, "override_wip": True}])
        self.assertEqual([p for p in self.out["cancelledPosts"] if "/decision" in p], [
            "/api/owner-action-requests/r1/decision"])  # the first ask only; nothing more is sent
        self.assertNotIn("load", self.out["cancelledPosts"])

    def test_the_preview_withholds_apply_until_it_can_succeed(self):
        blocked = self.out["dialogBlocked"]
        self.assertIn("2 of 3 tasks will change", blocked)
        self.assertIn("<strong>C &lt;x&gt;</strong> is already Ready", blocked)
        self.assertIn("data-bulk-drop>Remove blocked from selection", blocked)
        self.assertNotIn('type="submit"', blocked)
        self.assertNotIn('type="submit"', self.out["dialogWipManager"])  # a manager cannot pass a limit
        self.assertNotIn("override_wip", self.out["dialogWipManager"])
        self.assertIn('name="override_wip"', self.out["dialogWipOwner"])
        self.assertIn('type="submit">Apply to 2 tasks', self.out["dialogWipOwner"])


@unittest.skipUnless(shutil.which("node"), "node is needed to run app.js")
class AstraMyWorkInboxTests(unittest.TestCase):
    """FKVHH8: My Work groups and month calendar, and the Inbox tabs."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run_shell_driver("work", BROWSER_ELSEWHERE)

    def test_my_work_lists_five_groups_with_counts_and_only_my_open_work(self):
        html = self.out["list"]
        groups = re.findall(r'<h3>([\w ]+) <span class="count">(\d+)</span>', html)
        self.assertEqual(groups, [("Overdue", "1"), ("Today", "1"), ("This week", "2"), ("Later", "2"), ("No date", "1")])
        self.assertIn('<h2>Open work you own <span class="count">7</span></h2>', html)
        # Review M2: "This week" ends 7 days out, inclusive, as on the "Due in 7 days" tile.
        section = lambda key: re.search(rf'data-group="{key}">(.*?)</section>', html, re.S).group(1)
        self.assertIn('data-detail="w7"', section("week"))
        self.assertIn('data-detail="l8"', section("later"))
        self.assertNotIn("Not mine", html)
        self.assertNotIn(">Done<", html)
        self.assertIn("Later &lt;b&gt;x&lt;/b&gt;", html)
        self.assertIn('data-detail="o1"', html)
        self.assertIn('<a href="#/my-work" aria-current="page">List</a>', html)
        self.assertIn('id="my-work-search"', html)

    def test_filter_keeps_empty_groups_and_says_when_nothing_matches(self):
        groups = re.findall(r'<h3>([\w ]+) <span class="count">(\d+)</span>', self.out["filtered"])
        self.assertEqual(groups, [("Overdue", "0"), ("Today", "0"), ("This week", "1"), ("Later", "0"), ("No date", "0")])
        self.assertIn("Nothing overdue.", self.out["filtered"])
        self.assertIn("No open work you own matches “zzz”.", self.out["noMatch"])
        self.assertIn("Nothing is assigned to you", self.out["emptyList"])

    def test_month_grid_starts_on_monday_marks_today_and_folds_busy_days(self):
        html = self.out["month"]
        cells = re.findall(r'<li class="cal-day([^"]*)"><p class="cal-date"><span aria-hidden="true">(\d+)</span>', html)
        self.assertEqual(len(cells), 35)  # September 2026 starts on a Tuesday: Aug 31 to Oct 4
        self.assertEqual(cells[0], (" out", "31"))
        self.assertEqual(cells[1], ("", "1"))
        self.assertIn((" today", "25"), cells)
        self.assertIn("<span>Mon</span><span>Tue</span>", html)
        day = re.search(r'Wednesday 30 September, 5 tasks</span></p>(.*?)</li>', html).group(1)
        self.assertEqual(day.count('class="cal-item"'), 3)
        self.assertIn('data-cal-more="2026-09-30" aria-expanded="false">+2 more</button>', day)
        self.assertIn('data-detail="o1" data-tone="overdue"', html)
        self.assertIn('data-detail="d1" data-tone="today"', html)
        self.assertIn("Many &lt;img src=x&gt;", html)
        self.assertNotIn("<img", html)
        self.assertIn("8 open tasks due in September · 1 with no due date", html)
        expanded = re.search(r'Wednesday 30 September, 5 tasks</span></p>(.*?)</li>', self.out["expanded"]).group(1)
        self.assertEqual(expanded.count('class="cal-item"'), 5)
        self.assertIn('aria-expanded="true">Show fewer</button>', expanded)

    def test_month_links_keep_scope_and_the_route_reads_month(self):
        html = self.out["month"]
        self.assertIn('href="#/my-work/calendar?month=2026-08">', html)
        self.assertIn('href="#/my-work/calendar?month=2026-10">', html)
        self.assertIn('href="#/my-work/calendar?month=2026-09">Today</a>', html)
        self.assertIn('href="#/my-work/calendar?month=2026-10&scope=all">Next', self.out["expanded"])
        route = self.out["calRoute"]
        self.assertIn('<h2 class="cal-title" id="cal-title">October 2026</h2>', route)
        self.assertIn('<option value="all" selected>', route)
        self.assertIn('aria-current="page">Calendar</a>', route)
        # The List tab's Calendar link returns to the month last shown.
        self.assertIn('href="#/my-work/calendar?month=2026-10&amp;scope=all">Calendar</a>', self.out["listAfterCal"])
        # Review M1: with no month in the link, the server's today picks the month and the today ring
        # (the browser's clock says 24 Sep; the server says 25 Sep, then 1 Oct).
        self.assertIn('<h2 class="cal-title" id="cal-title">September 2026</h2>', self.out["calDefault"])
        self.assertIn('<li class="cal-day today"><p class="cal-date"><span aria-hidden="true">25</span>', self.out["calDefault"])
        self.assertIn('<h2 class="cal-title" id="cal-title">October 2026</h2>', self.out["calNewMonth"])
        self.assertIn('<li class="cal-day today"><p class="cal-date"><span aria-hidden="true">1</span>', self.out["calNewMonth"])
        feb = self.out["feb"]
        self.assertEqual(len(re.findall(r'<li class="cal-day', feb)), 28)  # February 2027 is exactly four weeks
        self.assertNotIn("cal-day out", feb)
        self.assertIn("Nothing is due in February 2027.", feb)

    def test_gantt_today_line_and_as_of_use_the_servers_today(self):
        # 3C1Z74: the browser says 24 Sep (Pago Pago); the server's today is 25 Sep, the project's start.
        self.assertNotIn("ganttError", self.out)
        gantt = self.out["gantt"]
        today = re.findall(r'class="today-line" data-x="([^"]+)"', gantt)
        start = re.findall(r'class="proj-line start" data-x="([^"]+)"', gantt)
        self.assertEqual(len(today), 1)
        self.assertTrue(start)
        self.assertAlmostEqual(float(today[0]), float(start[0]), places=6)
        self.assertIn("25", self.out["asOf"])
        self.assertIn("2026", self.out["asOf"])
        self.assertTrue(self.out["asOf"].startswith("Due dates as of "))
        self.assertTrue(self.out["asOf"].endswith("(Asia/Karachi)"))

    def test_phone_agenda_lists_only_days_with_work(self):
        agenda = self.out["month"].split('<ol class="cal-agenda"', 1)[1]
        self.assertEqual(re.findall(r'class="agenda-date">(\w+ \d+ \w+)', agenda), ["Wed 23 Sep", "Fri 25 Sep", "Tue 29 Sep", "Wed 30 Sep"])
        self.assertIn('Fri 25 Sep <span class="badge" data-level="info">Today</span>', agenda)
        css = (STATIC / "style.css").read_text(encoding="utf-8")
        # Review 11 M2: the agenda replaces the grid on every touch width (below 1024px), not only phones.
        touch = css[css.index("@media (max-width: 1023px) {"):]
        touch = touch[:touch.index("\n}\n")]
        self.assertIn(".cal-month { display: none; }", touch)
        self.assertIn(".cal-agenda { display: block; }", touch)
        self.assertIn(":not(.cal-item)", touch)
        self.assertIn(".cal-agenda { display: none;", css)

    def test_inbox_tabs_for_a_member(self):
        html = self.out["memberDefault"]
        self.assertNotIn("Needs action", html)
        self.assertIn('<a href="#/inbox?tab=unread" aria-current="page">Unread <span class="count">1</span></a>', html)
        self.assertIn('class="note-row unread"', html)
        self.assertIn(f'data-detail="{U1}" data-read-on-open="n1">Open task</button>', html)
        self.assertIn('data-read="n1">Mark read</button>', html)
        self.assertNotIn("old &lt;i&gt;", html)
        self.assertIn('id="read-all" class="quiet">', html)
        every = self.out["memberAll"]
        self.assertIn("old &lt;i&gt;note&lt;/i&gt;", every)
        self.assertIn('<h3 class="note-day">Earlier</h3>', every)
        self.assertNotIn('data-read="n2"', every)
        self.assertIn('aria-current="page">Unread', self.out["memberNeeds"])  # Needs action is for Owners only
        self.assertIn('aria-current="page">All', self.out["memberAllRead"])
        self.assertIn('id="read-all" class="quiet" disabled>', self.out["memberAllRead"])

    def test_inbox_puts_owner_requests_first(self):
        html = self.out["ownerDefault"]
        self.assertIn('<a href="#/inbox?tab=needs" aria-current="page">Needs action <span class="count">1</span></a>', html)
        self.assertIn('data-request-decision="approved" data-request-id="r1"', html)
        self.assertIn('id="inbox-error"', html)
        every = self.out["ownerAll"]
        self.assertLess(every.index("Needs your decision"), every.index("<h2>Notifications</h2>"))
        self.assertNotIn("data-request-decision", self.out["ownerUnread"])
        self.assertIn("Nothing is waiting for your decision", self.out["ownerEmpty"])


@unittest.skipUnless(shutil.which("node"), "node is needed to run app.js")
class AstraTaskPanelTests(unittest.TestCase):
    """DR3PKR: the docked task panel has its own link, and Back, close and reload agree with it."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run_shell_driver("main")
        cls.js = (STATIC / "app.js").read_text(encoding="utf-8")
        cls.html = (STATIC / "index.html").read_text(encoding="utf-8")
        cls.css = (STATIC / "style.css").read_text(encoding="utf-8")

    def test_opening_adds_the_task_to_the_link_and_swapping_replaces_it(self):
        opened = self.out["open1"]
        self.assertEqual(opened["hash"], f"#/home?status=delayed&task={U1}")
        self.assertFalse(opened["hidden"])
        self.assertEqual(opened["app"], ["panel-open"])
        self.assertEqual(opened["calls"], [])          # a first open assigns the hash: a history entry of its own
        self.assertEqual(opened["full"], f"#/task/{U1}")
        self.assertEqual(opened["focused"], "#detail-heading")
        swapped = self.out["swap"]
        self.assertEqual(swapped["calls"], [["replace", f"#/home?status=delayed&task={U2}"]])
        self.assertEqual(swapped["full"], f"#/task/{U2}")

    def test_closing_goes_back_and_returns_focus_to_the_opener(self):
        closed = self.out["close"]
        self.assertTrue(closed["hidden"])
        self.assertEqual(closed["app"], [])
        self.assertEqual(closed["calls"], [["back"]])
        self.assertEqual(closed["closes"], 1)
        self.assertEqual(closed["focused"], "#opener")
        # The opener was re-rendered while the panel was open: its replacement gets focus.
        self.assertEqual(self.out["reopenedFocus"]["focused"], "replacement")

    def test_keys_inside_and_outside_the_panel(self):
        self.assertFalse(self.out["jOutside"])   # j does nothing unless focus is in the panel (review M4)
        self.assertTrue(self.out["jInside"])
        # Esc in a panel field keeps focus in the panel; the panel stays open (review L2).
        self.assertEqual(self.out["escField"], [True, "#detail-heading", False])

    def test_a_filter_picked_while_the_panel_is_open_survives_closing_it(self):
        # Lock #9 review M2.
        self.assertEqual(self.out["filterWhileOpen"]["hash"], f"#/portfolio?crit=critical&task={U1}")
        kept = self.out["filterKept"]
        self.assertEqual(kept["calls"], [["replace", "#/portfolio?crit=critical"]])
        self.assertEqual(kept["hash"], "#/portfolio?crit=critical")

    def test_a_panel_opened_from_a_link_closes_without_leaving_the_app(self):
        self.assertEqual(self.out["linkOpen"]["calls"], [])
        self.assertEqual(self.out["linkOpen"]["hash"], f"#/inbox?task={U3}")
        self.assertEqual(self.out["linkClose"]["calls"], [["replace", "#/inbox"]])

    def test_what_is_behind_a_full_screen_panel_is_inert(self):
        # 3C1Z74 review M1: below 1024px the panel covers the screen; Tab must not reach what it hides.
        self.assertEqual(self.out["inertNarrowOpen"], ["", "", ""])
        self.assertEqual(self.out["inertNarrowClosed"], [None, None, None])
        self.assertEqual(self.out["inertWideOpen"], [None, None, None])  # at 1024px+ the page stays usable
        js = (STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn('...document.querySelectorAll("[data-view]")])', js)
        self.assertIn('fullMQ.addEventListener("change",syncPanelInert)', js)

    def test_the_task_page_is_the_same_panel_and_closes_to_the_last_screen(self):
        self.assertEqual(self.out["pageOpen"]["app"], ["panel-open", "task-page"])
        self.assertEqual(self.out["pageOpen"]["hash"], f"#/task/{U2}")
        self.assertEqual(self.out["pageClose"]["hash"], "#/my-work")
        self.assertEqual(self.out["pageClose"]["app"], [])
        closes = self.out["pageClose"]["closes"]
        self.assertEqual(self.out["closeTwice"]["closes"], closes)   # closing a closed panel does nothing
        self.assertEqual(self.out["links"], ["#/task/a%2Fb", "/api/tasks/a%2Fb/events", "#/home?due=7", "#/my-work?task=y+z"])

    def test_task_ids_from_a_link_are_checked_and_fetched_fresh(self):
        # Lock #9 review L1 and H1: a non-id fetches nothing; the first load after sign-in re-fetches.
        self.assertEqual(self.out["badIdFetches"], [])
        self.assertEqual(self.out["firstLoadFetches"], [f"/api/tasks/{U1}", f"/api/tasks/{U1}/events"])

    def test_panel_markup_order_and_layout(self):
        html, js, css = self.html, self.js, self.css
        self.assertNotIn('<dialog id="detail-dialog"', html)
        self.assertRegex(html, r'<aside id="detail-dialog" class="task-panel" aria-labelledby="detail-heading" hidden>')
        panel = html[html.index('<aside id="detail-dialog"'):html.index("</aside>")]
        for part in ('id="detail-copy"', 'id="detail-full"', 'id="detail-close" aria-label="Close task"', '<div id="detail-body"></div>'):
            self.assertIn(part, panel)
        # At 1024px and wider the panel sits below the top bar (review M1) and is narrower up to 1279px (L5).
        self.assertRegex(css, r"@media \(min-width: 1024px\) \{\n  \.task-panel \{ top: var\(--topbar-h\); \}")
        self.assertRegex(css, r"@media \(min-width: 1024px\) and \(max-width: 1279px\) \{\n  :root \{ --panel-w: 380px; \}")
        self.assertRegex(css, r"@media \(max-width: 1023px\) \{\n[^}]*\}\n  \.task-panel \{ left: 0;")
        # Re-review N3: 44px panel close and avatar wherever the panel is full screen.
        # Lock #11 review L4: the button rule gives the 44px height; this keeps the 44px width.
        self.assertRegex(css, r"@media \(max-width: 1023px\) \{\n  \.avatar, \.panel-close \{ min-width: 44px; \}")
        topbar_z = int(re.search(r"\.topbar \{[^}]*z-index: (\d+)", css).group(1))
        panel_z = int(re.search(r"\.task-panel \{[^}]*z-index: (\d+)", css).group(1))
        self.assertGreater(topbar_z, panel_z)   # the account menu opens over the panel
        # Details, steps and dependencies come before the one Lifecycle block (review L6).
        body = js[js.index('document.querySelector("#detail-body").innerHTML=`'):]
        body = body[:body.index('document.querySelector("#detail-edit")?.addEventListener')]
        self.assertEqual(body.count("${lifecycle}"), 1)
        self.assertLess(body.index('<p class="desc">'), body.index("${subtasks}"))
        self.assertLess(body.index("${subtasks}"), body.index('<div class="deps">'))
        self.assertLess(body.index('<div class="deps">'), body.index("${lifecycle}"))
        self.assertLess(body.index("${lifecycle}"), body.index("${reviewers}"))

    def test_j_and_k_follow_the_order_of_the_screen_behind(self):
        # Screen order U3, U1, U2 (U3 listed twice): from U1, j goes to U2 and k to U3; past the end nothing.
        calls, fetches = self.out["jNext"]
        self.assertEqual(calls, [["replace", f"#/my-work?task={U2}"]])
        self.assertEqual(fetches, [f"/api/tasks/{U2}", f"/api/tasks/{U2}/events"])
        calls, fetches = self.out["kPrev"]
        self.assertEqual(calls, [["replace", f"#/my-work?task={U3}"]])
        self.assertEqual(self.out["jAtEnd"], [[], []])

    def test_state_chips_carry_a_glyph_or_word(self):
        chips = self.js[self.js.index("function stateTags(task){"):self.js.index("function roleLine(perms){")]
        for text in ('`▲ ${due||"Overdue"}`', '"⊘ Blocked"', '"◆ Critical path"', '"✓ "', '"∥ "'):
            self.assertIn(text, chips)


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
VIEWER_PERMS = {"can_edit_ordinary": False, "can_request_protected": False,
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
  if(sc.requests){state.user={global_role:"owner"};state.loads=1;location.hash=sc.hash||"";renderInbox(sc.notes||[],sc.requests);location.hash=""}
  else{detailTaskId=sc.task.id;renderDetail(sc.task,[])}
  const pick=sc.click||sc.submitAt;
  // 5GK6SB: match the named attribute only, so data-remove-pred="t1" never matches data-remove-succ="t1".
  const key=pick&&pick[0].replace(/^data-/,"").replace(/-([a-z])/g,(_,c)=>c.toUpperCase());
  const target=pick?document.querySelectorAll("["+pick[0]+"]").find(n=>n.dataset[key]===pick[1])
    :document.querySelector(sc.submit||sc.button);
  if(sc.closeDetail){ // Close on a task opened from the inbox; loadsSince says whether anything was saved meanwhile
    // PZTYC9: the inbox is a page now (#/inbox), not a dialog under the task.
    location.hash="#/inbox";state.loads+=sc.closeDetail.loadsSince;calls.length=0;
    const handlers=document.querySelector("#detail-dialog")._l.close||[];await Promise.all(handlers.map(f=>f()));
    location.hash="";return {calls,threw:null,handlers:handlers.length,messages:{}};
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
        # 6G89SJ: a viewer's dialog, with a stored link that was not checked (exists None),
        # and an Owner's with a checked link that is missing (exists False).
        cases["viewer-unchecked"] = _detail_task("in_progress", VIEWER_PERMS)
        cases["viewer-unchecked"]["attachments"][0]["exists"] = None
        cases["owner-missing"] = _detail_task("in_progress", OWNER_PERMS)
        cases["owner-missing"]["attachments"][0]["exists"] = False
        # 3FQEKB: the Chairman's dialog carries the assignee control; a flagged task shows its chip.
        cases["chairman-in_progress"] = _detail_task("in_progress", {**VIEWER_PERMS, "can_assign": True, "assign_only": True,
                                                                     "can_submit": False})
        cases["chairman-in_progress"]["needs_new_assignee"] = True
        # Review 13a: a viewer who is a valid collaborator may submit; a flagged collaborator row is marked.
        cases["viewer-collaborator"] = _detail_task("in_progress", {**VIEWER_PERMS, "can_submit": True})
        cases["viewer-collaborator"]["needs_new_collaborator"] = True
        cases["viewer-collaborator"]["reviewers"] = [{"display_name": "Chair <b>", "role": "collaborator", "user_id": "u3",
                                                      "not_allowed": True}]
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

    def test_review_13a_the_chairman_and_viewers_see_no_forms_the_server_refuses(self):
        for case in ("chairman-in_progress", "viewer-collaborator", "viewer-unchecked"):
            html = self.html[case]
            with self.subTest(case=case):
                for refused in ('id="parent-form"', 'id="crit-form"', 'id="sched-form"', 'id="add-dep-select"',
                                "data-remove-pred=", 'id="add-reviewer-button"', "data-remove-reviewer-user",
                                "data-approve-sched", 'id="detail-edit"'):
                    self.assertNotIn(refused, html, refused)
                self.assertIn("Depends on: <strong>Before</strong>", html)  # the lists stay
                self.assertIn("Reviewers &amp; approvers", html)
        self.assertNotIn('data-life="submit"', self.html["chairman-in_progress"])
        self.assertIn('data-life="submit"', self.html["viewer-collaborator"])
        self.assertIn('data-life="submit"', self.html["owner-in_progress"])  # no can_submit key: unchanged

    def test_review_13a_the_panel_sends_empty_dates_as_null(self):
        js = (REPO / "src" / "astra" / "static" / "app.js").read_text(encoding="utf-8")
        body = js[js.index("async function submitDetailEdit("):js.index("async function addDependency(")]
        self.assertIn('for(const k of ["start_date","due_date"])if(k in body&&!body[k])body[k]=null;', body)

    def test_review_13a_a_forbidden_collaborator_is_marked(self):
        html = self.html["viewer-collaborator"]
        self.assertIn("Chair &lt;b&gt; · collaborator <span class=\"tag reassign-chip\" data-tone=\"amber\">⚠ Not allowed as a "
                      "collaborator here: remove</span>", html)
        self.assertIn("⚠ Collaborator not allowed", html)

    def test_3fqekb_the_chairman_sees_the_assignee_control_and_the_chip(self):
        html = self.html["chairman-in_progress"]
        self.assertIn('<form id="detail-assign">', html)
        self.assertIn("<button value=\"save\">Save assignee</button>", html)
        self.assertNotIn('<form id="detail-edit">', html)
        self.assertIn("You can assign this task to someone. Other changes are made by the project&#39;s managers.", html)
        self.assertIn("⚠ Needs a new assignee", html)
        for who in ("owner", "manager"):
            with self.subTest(who=who):
                self.assertIn('<form id="detail-edit">', self.html[f"{who}-in_progress"])
                self.assertNotIn('id="detail-assign"', self.html[f"{who}-in_progress"])

    def test_a_manager_puts_work_on_hold_rather_than_requesting_it(self):
        # Aly 2026-09-25 (Slack ts 1790342529.695749): managers hold directly, with a reason.
        for who in ("owner", "manager"):
            with self.subTest(who=who):
                html = self.html[f"{who}-in_progress"]
                self.assertIn('<form data-life="hold">', html)
                self.assertIn("<button>Put on hold</button>", html)
                self.assertNotIn("Request Owner hold", html)

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

    def test_attachment_form_is_absent_for_a_viewer_and_unchecked_links_are_not_called_missing(self):
        viewer = self.html["viewer-unchecked"]
        self.assertIn("data-copy-path=", viewer)  # Owner Item 3: viewers keep metadata and Copy path
        for refused in ('id="attachment-form"', 'data-remove-attachment=', 'data-mark-fr-att=', "Link file"):
            self.assertNotIn(refused, viewer, refused)
        self.assertIn("Read/download only", viewer)
        self.assertIn("Report", viewer)
        self.assertNotIn("(file not found)", viewer)
        self.assertIn("(file not found)", self.html["owner-missing"])

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
            # FKVHH8 review L3: opening a notification's task marks that notification read.
            "inbox-open-marks-read": {"requests": [], "task": owner_open, "click": ["data-detail", U1], "notes": [
                {"id": "n1", "summary": "task assigned: Alpha", "task_id": U1, "task_title": "Alpha",
                 "created_at": "2026-09-25T08:00:00Z", "read_at": None}]},
            "inbox-open-read-note": {"requests": [], "task": owner_open, "hash": "#/inbox?tab=all", "click": ["data-detail", U1], "notes": [
                {"id": "n2", "summary": "task assigned: Alpha", "task_id": U1, "task_title": "Alpha",
                 "created_at": "2026-09-25T08:00:00Z", "read_at": "2026-09-25T09:00:00Z"}]},
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

    def test_opening_a_notification_task_marks_it_read(self):
        calls = self._ran("inbox-open-marks-read")["calls"]
        self.assertIn({"reload": True}, calls)
        self.assertIn({"path": "/api/notifications/n1/read", "method": "POST", "body": {}}, calls)
        # An already-read notification is not marked again.
        calls = self._ran("inbox-open-read-note")["calls"]
        self.assertIn({"reload": True}, calls)
        self.assertFalse([c for c in calls if "path" in c])

    def test_a_refused_inbox_decision_shows_the_reason_inline(self):
        run = self._ran("inbox-decision-refused")
        self.assertNotIn({"reloadInbox": True}, run["calls"])
        self.assertFalse([c for c in run["calls"] if "alert" in c])
        self.assertEqual(run["messages"].get("inbox-error"), "Owner cannot do that.")

    def test_no_reason_given_is_muted_inside_a_request(self):
        css = (STATIC / "style.css").read_text(encoding="utf-8")
        # Lock #9 review L8: one muted grey token everywhere (its contrast is checked in AstraFoundationStaticTests).
        self.assertIn(".owner-request .request-detail p.muted { color: var(--muted); }", css)

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


class AstraProjectHistoryUiTests(unittest.TestCase):
    """5WZ4A8: the project's date-change history has a user-facing surface."""

    @classmethod
    def setUpClass(cls):
        cls.js = (STATIC / "app.js").read_text(encoding="utf-8")
        cls.html = (STATIC / "index.html").read_text(encoding="utf-8")

    def test_project_history_dialog_reads_the_project_events_endpoint(self):
        self.assertIn('id="project-history-btn"', self.html)
        self.assertIn('<dialog id="project-history-dialog">', self.html)
        self.assertIn("api(`/api/projects/${projectId}/events`)", self.js)
        # The button is tied to a single selected project.
        self.assertIn('document.querySelector("#project-history-btn").hidden=!document.querySelector("#project-filter").value;', self.js)

    def test_schedule_change_renders_before_after_and_reason_escaped(self):
        render = self.js[self.js.index("function renderProjectEvent(ev){"):]
        render = render[:render.index("\n}\n") + 3]
        self.assertIn('project_schedule_changed:"Project dates changed"', self.js)
        self.assertIn("escapeHtml(b[k]||\"\u2014\")} \u2192 ${escapeHtml(a[k]||\"\u2014\")}", render)
        self.assertIn("escapeHtml(ev.reason)", render)
        self.assertIn("escapeHtml(who)", render)


if __name__ == "__main__":
    unittest.main()
