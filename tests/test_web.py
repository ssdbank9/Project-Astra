import http.client
import inspect
import json
import os
import re
import tempfile
import threading
import unittest
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
        _, detail = self.request("GET", f"/api/tasks/{task['id']}", cookie=owner_cookie)
        self.assertEqual(detail["task"]["status"], "cancelled")

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


if __name__ == "__main__":
    unittest.main()
