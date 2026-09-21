import http.client
import inspect
import json
import os
import re
import tempfile
import threading
import unittest

from astra.web import AstraHandler, AstraServer


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

    def test_governed_status_shortcut_rejected_over_http(self):
        cookie, csrf = self._owner_session()
        _, project = self.request("POST", "/api/projects", {"name": "Guard"}, cookie=cookie, csrf=csrf)
        _, task = self.request("POST", "/api/tasks", {
            "project_id": project["project"]["id"], "title": "G",
        }, cookie=cookie, csrf=csrf)
        response, payload = self.request("POST", f"/api/tasks/{task['task']['id']}", {
            "status": "completed", "reason": "shortcut",
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
        response, payload = self.request("POST", f"/api/tasks/{task_id}", {"title": "  "}, cookie=cookie, csrf=csrf)
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


if __name__ == "__main__":
    unittest.main()
