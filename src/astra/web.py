from __future__ import annotations

import csv
import io
import json
import mimetypes
import os
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, unquote, urlparse

from .auth import dummy_password_hash, new_token, token_digest, verify_password
from .db import connect, database_path
from .importer import FORMULA_PREFIXES, ImportConflict, ImportTooLarge
from .service import AstraService, Conflict, Forbidden, now_text


SESSION_COOKIE = "astra_session"
JSON_MAX_BYTES = 1_000_000
# Raw file uploads (Excel/CSV import) get their own ceiling; JSON stays at 1 MB.
IMPORT_MAX_BYTES = 5 * 1024 * 1024
# Fonts are served by Astra itself (4T4DEA), so the page needs no third-party origin.
CONTENT_SECURITY_POLICY = ("default-src 'self'; style-src 'self'; script-src 'self'; font-src 'self'; "
                           "base-uri 'none'; frame-ancestors 'none'")
# Only these files are served from static/. The Inter files carry their version in the name
# (Inter 4.001, Google Fonts css2 v20 latin and latin-ext subsets), so they can be cached for a year.
STATIC_FILES = {"index.html", "app.js", "style.css", "fonts/Inter-OFL.txt"}
FONT_FILES = {"fonts/inter-latin-4.001.woff2", "fonts/inter-latin-ext-4.001.woff2"}


class PayloadTooLarge(ValueError):
    pass


def _as_of_slug(as_of: str | None) -> str:
    """Filesystem-safe token derived from an ISO 'as of' timestamp for CSV filenames.

    Provenance used to live in a leading '# Astra export — as of ...' comment row,
    which broke header-first CSV parsing; it now rides in the download filename.
    """
    text = (as_of or "").strip()
    if not text:
        return "export"
    safe = []
    for ch in text:
        safe.append(ch if (ch.isalnum() or ch in "-_") else "-")
    slug = "".join(safe).strip("-")
    # Collapse runs of '-' so 2026-09-15T23-34-13-123456-00-00 stays readable.
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "export"


def _csv_cell(value) -> str:
    """A task/final-results export cell a spreadsheet opens as text (CWE-1236).

    Same rule as importer.csv_cell (template and import-report CSVs): a value starting with
    = + - @ tab or CR gets a leading single quote. Unlike csv_cell it does not normalise the
    value (no trimming, no Yes/No for booleans), so the export keeps the exact stored text."""
    if value is None:
        return ""
    text = str(value)
    return "'" + text if text.startswith(FORMULA_PREFIXES) else text


# Filter keys as they appear in a CSV download's filename; anything not listed (sort, format)
# does not narrow the rows and is left out.
_FILTER_LABELS = {
    "project_id": "project", "entity_id": "entity", "status": "status", "criticality": "criticality",
    "owner": "owner", "band": "band", "risk": "risk", "open_only": "open-only", "type": "type", "from": "from",
    "to": "to", "q": "search",
}
_FILTER_VALUE_MAX = 40
_FILTER_SEGMENT_MAX = 160


def _filter_slug(filters: dict | None) -> str:
    """'__key=value' per active filter, for the CSV filename (owner decision 2026-09-15: the
    CSV starts with its header row, so as-of and filters travel in the filename). Values keep
    only letters, digits, '.', '-' and '_' so nothing unsafe reaches Content-Disposition; an
    over-long list ends in '__more' and the JSON export (?format omitted) carries it in full."""
    parts = []
    for key, label in _FILTER_LABELS.items():
        value = (filters or {}).get(key)
        if value is True:
            parts.append(f"__{label}")
            continue
        text = str(value or "").strip()
        if not text:
            continue
        safe = "".join(ch if (ch.isascii() and (ch.isalnum() or ch in ".-_")) else "-" for ch in text)
        while "--" in safe:
            safe = safe.replace("--", "-")
        while "__" in safe:
            safe = safe.replace("__", "_")
        safe = safe.strip("-_")[:_FILTER_VALUE_MAX] or "-"
        parts.append(f"__{label}={safe}")
    segment = ""
    for part in parts:
        if len(segment) + len(part) > _FILTER_SEGMENT_MAX:
            return segment + "__more"
        segment += part
    return segment


class AstraHandler(BaseHTTPRequestHandler):
    server_version = "Astra/0.1"

    def do_GET(self):
        self.db = connect(self.server.db_path)
        self._service = AstraService(self.db)
        try:
            path = urlparse(self.path).path
            if path == "/api/me":
                user, csrf = self._require_user()
                return self._json({"user": user, "csrf": csrf})
            if path == "/api/projects":
                user, _ = self._require_user()
                return self._json({"projects": self.service.list_projects(user)})
            if path == "/api/tasks":
                user, _ = self._require_user()
                q = parse_qs(urlparse(self.path).query)
                project = q.get("project_id", [None])[0]
                sort = q.get("sort", ["criticality"])[0]
                return self._json({"tasks": self.service.list_tasks(user, project, sort), "today": self.service.app_today()})
            if path == "/api/task-dependencies":
                user, _ = self._require_user()
                task_id = parse_qs(urlparse(self.path).query).get("task_id", [""])[0]
                if not task_id:
                    raise ValueError("task_id is required.")
                return self._json({"dependencies": self.service.get_task_dependencies(user, task_id)})
            if path == "/api/users":
                user, _ = self._require_user()
                return self._json({"users": self.service.list_users(user)})
            if path == "/api/user-events":
                user, _ = self._require_user()
                return self._json({"events": self.service.list_user_events(user)})
            if path == "/api/memberships":
                user, _ = self._require_user()
                project = parse_qs(urlparse(self.path).query).get("project_id", [None])[0]
                return self._json({"memberships": self.service.list_memberships(user, project)})
            if path == "/api/assignable-users":
                user, _ = self._require_user()
                project = parse_qs(urlparse(self.path).query).get("project_id", [""])[0]
                if not project:
                    raise ValueError("project_id is required.")
                return self._json({"users": self.service.list_assignable_users(user, project)})
            if path == "/api/entities":
                user, _ = self._require_user()
                return self._json({"entities": self.service.list_entities(user)})
            if path == "/api/portfolio":
                user, _ = self._require_user()
                return self._json({"portfolio": self.service.portfolio_rollup(user)})
            if path == "/api/templates":
                user, _ = self._require_user()
                kind = parse_qs(urlparse(self.path).query).get("kind", [None])[0]
                return self._json({"templates": self.service.list_templates(user, kind)})
            if path.startswith("/api/templates/") and path.count("/") == 3:
                user, _ = self._require_user()
                return self._json({"template": self.service.get_template(user, path.split("/")[3])})
            if path == "/api/final-results":
                user, _ = self._require_user()
                query = parse_qs(urlparse(self.path).query)
                filters = {k: query.get(k, [None])[0] for k in ("project_id", "entity_id", "type", "from", "to", "q")}
                if query.get("format", [""])[0] == "csv":
                    return self._csv_final_results(self.service.export_final_results(user, filters))
                return self._json({"results": self.service.list_final_results(user, filters)})
            if path == "/api/notifications":
                user, _ = self._require_user()
                unread_only = parse_qs(urlparse(self.path).query).get("unread", ["0"])[0] in ("1", "true")
                return self._json({
                    "notifications": self.service.list_notifications(user, unread_only),
                    "unread": self.service.unread_notification_count(user),
                })
            if path == "/api/owner-action-requests":
                user, _ = self._require_user()
                status = parse_qs(urlparse(self.path).query).get("status", ["pending"])[0] or None
                return self._json({"requests": self.service.list_owner_action_requests(user, status)})
            if path == "/api/search":
                user, _ = self._require_user()
                term = parse_qs(urlparse(self.path).query).get("q", [""])[0]
                return self._json({"results": self.service.search(user, term)})
            if path in ("/api/import/template.xlsx", "/api/import/template.csv"):
                user, _ = self._require_user()
                project = parse_qs(urlparse(self.path).query).get("project_id", [""])[0].strip() or None
                payload, filename, content_type = self.service.import_template(user, path.rsplit(".", 1)[1], project)
                return self._download(payload, filename, content_type)
            if path == "/api/import/targets":
                user, _ = self._require_user()
                return self._json({"targets": self.service.import_targets(user)})
            if path == "/api/import/template-config":
                user, _ = self._require_user()
                return self._json({"config": self.service.get_import_template_config(user)})
            if path == "/api/imports":
                user, _ = self._require_user()
                project = parse_qs(urlparse(self.path).query).get("project_id", [None])[0]
                return self._json({"imports": self.service.list_imports(user, project)})
            if path.startswith("/api/imports/") and path.endswith("/report.csv"):
                user, _ = self._require_user()
                report = self.service.import_report(user, path.split("/")[3])
                return self._download(report["csv"].encode("utf-8-sig"), report["filename"], "text/csv; charset=utf-8")
            if path == "/api/export":
                user, _ = self._require_user()
                query = parse_qs(urlparse(self.path).query)
                filters = {k: query.get(k, [None])[0] for k in ("project_id", "status", "entity_id", "criticality", "owner", "band", "risk", "sort")}
                filters["open_only"] = query.get("open_only", ["0"])[0] in ("1", "true")
                export = self.service.export_tasks(user, filters)
                if query.get("format", [""])[0] == "csv":
                    return self._csv(export)
                return self._json({"export": export})
            if path.startswith("/api/projects/") and path.endswith("/calendar"):
                user, _ = self._require_user()
                project_id = path.split("/")[3]
                return self._json({"calendar": self.service.get_project_calendar(user, project_id)})
            if path.startswith("/api/projects/") and path.endswith("/events") and path.count("/") == 4:
                user, _ = self._require_user()
                project_id = path.split("/")[3]
                return self._json({"events": self.service.project_events(user, project_id)})
            if path.startswith("/api/tasks/") and path.endswith("/events"):
                user, _ = self._require_user()
                task_id = path.split("/")[3]
                return self._json({"events": self.service.task_events(user, task_id)})
            if path.startswith("/api/tasks/") and path.count("/") == 3:
                user, _ = self._require_user()
                task_id = path.split("/")[3]
                return self._json({"task": self.service.task_detail(user, task_id)})
            if path == "/" or path.startswith("/static/"):
                return self._static("index.html" if path == "/" else path.removeprefix("/static/"))
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._error(exc)
        finally:
            self.db.close()

    def do_POST(self):
        self.db = connect(self.server.db_path)
        self._service = AstraService(self.db)
        try:
            path = urlparse(self.path).path
            payload = self._body(path)
            if path == "/api/login":
                return self._login(payload)
            user, csrf = self._require_user()
            if self.headers.get("X-CSRF-Token") != csrf:
                raise Forbidden("Invalid request token.")
            if path == "/api/logout":
                self._delete_session()
                return self._json({"ok": True}, cookie=self._session_cookie("", 0))
            if path == "/api/logout-all":
                revoked = self.service.revoke_user_sessions(user["id"])
                return self._json({"ok": True, "revoked": revoked}, cookie=self._session_cookie("", 0))
            if path == "/api/projects":
                project = self.service.create_project(user, payload.get("name", ""), payload.get("description", ""))
                return self._json({"project": project}, HTTPStatus.CREATED)
            if path == "/api/tasks":
                return self._json({"task": self.service.create_task(user, payload)}, HTTPStatus.CREATED)
            if path == "/api/task-dependencies":
                dependency = self.service.add_task_dependency(
                    user,
                    str(payload.get("predecessor_task_id", "")),
                    str(payload.get("successor_task_id", "")),
                    str(payload.get("dependency_type", "finish_to_start")),
                )
                status = HTTPStatus.CREATED if dependency["created"] else HTTPStatus.OK
                return self._json({"dependency": dependency}, status)
            if path == "/api/users":
                created = self.service.create_user(
                    user,
                    str(payload.get("email", "")),
                    str(payload.get("display_name", "")),
                    str(payload.get("password", "")),
                    str(payload.get("role", "member")),
                )
                return self._json({"user": created}, HTTPStatus.CREATED)
            if path == "/api/project-access":
                self.service.grant_project_access(
                    user,
                    str(payload.get("project_id", "")),
                    str(payload.get("user_id", "")),
                    str(payload.get("role", "")),
                )
                return self._json({"ok": True})
            if path == "/api/entities/seed":
                return self._json({"created": self.service.seed_default_entities(user)})
            if path == "/api/entities":
                return self._json({"entity": self.service.create_entity(user, payload.get("name", ""))}, HTTPStatus.CREATED)
            if path.startswith("/api/entities/") and path.endswith("/active"):
                entity_id = path.split("/")[3]
                return self._json({"entity": self.service.set_entity_active(user, entity_id, bool(payload.get("active")))})
            if path.startswith("/api/projects/") and path.endswith("/entities"):
                project_id = path.split("/")[3]
                return self._json({"entities": self.service.set_project_entities(user, project_id, payload.get("entity_ids", []))})
            if path.startswith("/api/projects/") and path.endswith("/working-days"):
                project_id = path.split("/")[3]
                return self._json({"working_days": self.service.set_working_days(user, project_id, payload.get("days", ""))})
            if path.startswith("/api/projects/") and path.endswith("/holidays"):
                project_id = path.split("/")[3]
                holidays = self.service.add_holiday(user, project_id, payload.get("date"), payload.get("label", ""))
                return self._json({"holidays": holidays})
            if path.startswith("/api/projects/") and path.endswith("/schedule"):
                project_id = path.split("/")[3]
                project = self.service.set_project_schedule(
                    user, project_id, payload.get("start_date"), payload.get("target_date"), payload.get("reason", "")
                )
                return self._json({"project": project})
            if path.startswith("/api/projects/") and path.endswith("/budget"):
                project_id = path.split("/")[3]
                project = self.service.set_project_budget(user, project_id, payload.get("amount"), payload.get("currency", "PKR"))
                return self._json({"project": project})
            if path.startswith("/api/projects/") and path.endswith("/primary-entity"):
                project_id = path.split("/")[3]
                project = self.service.set_primary_entity(user, project_id, payload.get("entity_id"))
                return self._json({"project": project})
            if path == "/api/import/preview":
                preview = self.service.import_preview(
                    user, self._header_text("X-Project-Id") or None, self._header_text("X-Filename"),
                    payload.get("_raw", b""), self._header_json("X-Options"),
                )
                return self._json({"preview": preview})
            if path == "/api/import/commit":
                result = self.service.import_commit(
                    user, self._header_text("X-Project-Id") or None, self._header_text("X-Filename"),
                    payload.get("_raw", b""), self._header_json("X-Options"), self._header_text("X-Sha256") or None,
                    self._header_text("X-Plan-Fingerprint") or None, plan_required=True,
                )
                return self._json({"result": result}, HTTPStatus.CREATED)
            if path == "/api/notifications/read-all":
                return self._json({"read": self.service.mark_all_notifications_read(user)})
            if path.startswith("/api/notifications/") and path.endswith("/read"):
                notification_id = path.split("/")[3]
                self.service.mark_notification_read(user, notification_id)
                return self._json({"ok": True})
            if (path.startswith("/api/owner-action-requests/") and path.endswith("/decision")
                    and path.count("/") == 4):
                request_id = path.split("/")[3]
                result = self.service.decide_owner_action_request(
                    user, request_id, payload.get("decision", ""), payload.get("reason", "")
                )
                return self._json(result)
            if path.startswith("/api/users/") and path.endswith("/secondary-owner") and path.count("/") == 4:
                granted = self.service.grant_secondary_owner(user, path.split("/")[3], payload.get("reason", ""))
                return self._json({"user": granted}, HTTPStatus.CREATED)
            if path.startswith("/api/users/") and path.endswith("/password") and path.count("/") == 4:
                raw = self._cookie_value(SESSION_COOKIE)
                if not isinstance(payload.get("password"), str):
                    raise ValueError("Password must be text.")
                updated = self.service.reset_user_password(
                    user, path.split("/")[3], payload["password"],
                    keep_session=token_digest(raw) if raw else None,
                )
                return self._json({"user": updated})
            if path.startswith("/api/users/") and path.endswith("/active"):
                user_id = path.split("/")[3]
                updated = self.service.set_user_active(user, user_id, bool(payload.get("active")))
                return self._json({"user": updated})
            if path.startswith("/api/tasks/") and path.endswith("/submit"):
                task_id = path.split("/")[3]
                submission = self.service.submit_task(user, task_id, payload.get("note", ""))
                return self._json({"submission": submission}, HTTPStatus.CREATED)
            if path.startswith("/api/tasks/") and path.endswith("/reopen"):
                task_id = path.split("/")[3]
                outcome = self.service.reopen_task(user, task_id, payload.get("reason", ""), payload.get("new_due_date"))
                return self._json(outcome, HTTPStatus.ACCEPTED) if "request" in outcome else self._json({"task": outcome})
            if path.startswith("/api/tasks/") and path.endswith("/hold"):
                task_id = path.split("/")[3]
                outcome = self.service.set_on_hold(
                    user, task_id, payload.get("reason", ""), payload.get("checkpoint_date"), payload.get("owner_user_id")
                )
                return self._json(outcome, HTTPStatus.ACCEPTED) if "request" in outcome else self._json({"task": outcome})
            if path.startswith("/api/tasks/") and path.endswith("/criticality"):
                task_id = path.split("/")[3]
                task = self.service.confirm_criticality(
                    user, task_id, payload.get("criticality"), payload.get("reason", ""),
                    payload.get("expected_revision"),
                )
                return self._json({"task": task})
            if path.startswith("/api/tasks/") and path.endswith("/parent"):
                task_id = path.split("/")[3]
                task = self.service.set_parent(user, task_id, payload.get("parent_task_id"))
                return self._json({"task": task})
            if path.startswith("/api/tasks/") and path.endswith("/schedule-proposals"):
                task_id = path.split("/")[3]
                proposal = self.service.propose_schedule(
                    user, task_id, payload.get("start_date"), payload.get("due_date"), payload.get("reason", "")
                )
                return self._json({"proposal": proposal}, HTTPStatus.CREATED)
            if path.startswith("/api/schedule-proposals/") and path.endswith("/approve"):
                proposal_id = path.split("/")[3]
                outcome = self.service.approve_schedule_proposal(user, proposal_id, payload.get("decision_reason", ""))
                return self._json(outcome, HTTPStatus.ACCEPTED) if "request" in outcome else self._json({"task": outcome})
            if path.startswith("/api/schedule-proposals/") and path.endswith("/reject"):
                proposal_id = path.split("/")[3]
                outcome = self.service.reject_schedule_proposal(user, proposal_id, payload.get("reason", ""))
                return self._json(outcome, HTTPStatus.ACCEPTED) if "request" in outcome else self._json({"proposal": outcome})
            if path.startswith("/api/submissions/") and path.endswith("/accept"):
                submission_id = path.split("/")[3]
                outcome = self.service.accept_submission(
                    user, submission_id, payload.get("decision_note", ""), payload.get("checklist")
                )
                return self._json(outcome, HTTPStatus.ACCEPTED) if "request" in outcome else self._json({"submission": outcome})
            if path.startswith("/api/submissions/") and path.endswith("/request-changes"):
                submission_id = path.split("/")[3]
                outcome = self.service.request_changes(user, submission_id, payload.get("reason", ""))
                return self._json(outcome, HTTPStatus.ACCEPTED) if "request" in outcome else self._json({"submission": outcome})
            if path == "/api/task-reviewers":
                self.service.add_task_reviewer(
                    user, str(payload.get("task_id", "")), str(payload.get("user_id", "")), str(payload.get("role", ""))
                )
                return self._json({"ok": True})
            if path.startswith("/api/tasks/") and path.endswith("/attachments"):
                task_id = path.split("/")[3]
                attachment = self.service.add_task_attachment(
                    user, task_id, str(payload.get("path", "")),
                    str(payload.get("display_name", "")), str(payload.get("note", "")),
                )
                return self._json({"attachment": attachment}, HTTPStatus.CREATED)
            if path == "/api/final-results":
                result = self.service.mark_final_result(
                    user, str(payload.get("task_id", "")), str(payload.get("source_type", "")),
                    str(payload.get("source_id", "")), str(payload.get("note", "")),
                )
                return self._json({"result": result}, HTTPStatus.CREATED)
            if path == "/api/templates/from-project":
                template = self.service.save_project_as_template(
                    user, str(payload.get("project_id", "")), str(payload.get("name", "")),
                    str(payload.get("description", "")),
                )
                return self._json({"template": template}, HTTPStatus.CREATED)
            if path == "/api/templates/from-task":
                template = self.service.save_task_as_template(
                    user, str(payload.get("task_id", "")), str(payload.get("name", "")),
                    str(payload.get("description", "")),
                )
                return self._json({"template": template}, HTTPStatus.CREATED)
            if path.startswith("/api/templates/") and path.endswith("/create-project"):
                template_id = path.split("/")[3]
                project = self.service.create_project_from_template(
                    user, template_id, str(payload.get("name", "")), payload.get("anchor_date"),
                    payload.get("role_assignments"),
                )
                return self._json({"project": project}, HTTPStatus.CREATED)
            if path.startswith("/api/templates/") and path.endswith("/create-task"):
                template_id = path.split("/")[3]
                result = self.service.create_task_from_template(
                    user, template_id, str(payload.get("project_id", "")),
                    payload.get("parent_task_id"), payload.get("anchor_date"),
                    payload.get("role_assignments"),
                )
                return self._json({"result": result}, HTTPStatus.CREATED)
            if path.startswith("/api/projects/") and path.endswith("/close"):
                project_id = path.split("/")[3]
                outcome = self.service.close_project(
                    user, project_id, payload.get("note", ""), bool(payload.get("exceptional"))
                )
                return self._json(outcome, HTTPStatus.ACCEPTED) if "request" in outcome else self._json({"project": outcome})
            if path.startswith("/api/tasks/") and path.count("/") == 3:
                task_id = path.split("/")[3]
                outcome = self.service.update_task(user, task_id, payload)
                return self._json(outcome, HTTPStatus.ACCEPTED) if "request" in outcome else self._json({"task": outcome})
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._error(exc)
        finally:
            self.db.close()

    def do_PUT(self):
        self.db = connect(self.server.db_path)
        self._service = AstraService(self.db)
        try:
            path = urlparse(self.path).path
            payload = self._body(path)
            user, csrf = self._require_user()
            if self.headers.get("X-CSRF-Token") != csrf:
                raise Forbidden("Invalid request token.")
            if path == "/api/import/template-config":
                return self._json({"config": self.service.set_import_template_config(user, payload)})
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._error(exc)
        finally:
            self.db.close()

    def do_DELETE(self):
        self.db = connect(self.server.db_path)
        self._service = AstraService(self.db)
        try:
            path = urlparse(self.path).path
            payload = self._body(path)
            user, csrf = self._require_user()
            if self.headers.get("X-CSRF-Token") != csrf:
                raise Forbidden("Invalid request token.")
            if path == "/api/task-dependencies":
                self.service.remove_task_dependency(
                    user,
                    str(payload.get("predecessor_task_id", "")),
                    str(payload.get("successor_task_id", "")),
                    str(payload.get("reason", "")),
                )
                return self._json({"ok": True})
            if path == "/api/project-access":
                self.service.revoke_project_access(
                    user,
                    str(payload.get("project_id", "")),
                    str(payload.get("user_id", "")),
                )
                return self._json({"ok": True})
            if path == "/api/task-reviewers":
                self.service.remove_task_reviewer(
                    user,
                    str(payload.get("task_id", "")),
                    str(payload.get("user_id", "")),
                    str(payload.get("role", "")),
                )
                return self._json({"ok": True})
            if path == "/api/project-holidays":
                self.service.remove_holiday(user, str(payload.get("project_id", "")), payload.get("date"))
                return self._json({"ok": True})
            if path == "/api/task-attachments":
                self.service.remove_task_attachment(
                    user, str(payload.get("task_id", "")), str(payload.get("attachment_id", ""))
                )
                return self._json({"ok": True})
            if path == "/api/templates":
                self.service.delete_template(user, str(payload.get("template_id", "")))
                return self._json({"ok": True})
            if path == "/api/final-results":
                self.service.unmark_final_result(user, str(payload.get("result_id", "")))
                return self._json({"ok": True})
            if path.startswith("/api/users/") and path.endswith("/secondary-owner") and path.count("/") == 4:
                revoked = self.service.revoke_secondary_owner(user, path.split("/")[3], payload.get("reason", ""))
                return self._json({"user": revoked})
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._error(exc)
        finally:
            self.db.close()

    @property
    def service(self) -> AstraService:
        return self._service

    def _login(self, payload: dict):
        email = str(payload.get("email", "")).strip().casefold()
        ip = self.client_address[0] if self.client_address else ""
        password = payload.get("password", "")
        password = password if isinstance(password, str) else ""
        # 3M2AYA (Aly, 2026-09-24): no lockout; a wrong password or unknown email just says so.
        row = self.db.execute("SELECT * FROM users WHERE email=? AND active=1", (email,)).fetchone()
        # An unknown or inactive email is checked against a dummy hash, so it takes as long.
        matches = verify_password(password, row["password_hash"] if row else dummy_password_hash())
        if not row or not matches:
            self.service.record_login_attempt(email, ip, False)
            return self._json({"error": "Incorrect email or password."}, HTTPStatus.UNAUTHORIZED)
        self.service.record_login_attempt(email, ip, True)
        self.service.cleanup_expired_sessions()
        raw, csrf = new_token(), new_token()
        expires = datetime.now(timezone.utc) + timedelta(hours=12)
        self.db.execute(
            "INSERT INTO sessions VALUES(?,?,?,?,?)",
            (token_digest(raw), row["id"], csrf, now_text(), expires.isoformat()),
        )
        user = self.service.get_user(row["id"])
        return self._json({"user": user, "csrf": csrf}, cookie=self._session_cookie(raw, 43200))

    @staticmethod
    def _session_cookie(value: str, max_age: int) -> str:
        # Secure is opt-in via ASTRA_SECURE_COOKIES so local HTTP development keeps
        # working; deployment behind HTTPS should set it to mark the cookie Secure.
        secure = "; Secure" if os.environ.get("ASTRA_SECURE_COOKIES") else ""
        return f"{SESSION_COOKIE}={value}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}{secure}"

    def _require_user(self):
        raw = self._cookie_value(SESSION_COOKIE)
        if not raw:
            raise Forbidden("Sign in required.")
        row = self.db.execute(
            """SELECT s.csrf_token,s.expires_at,u.id,u.email,u.display_name,u.global_role,u.active,u.created_at,
                      u.is_primary_owner
               FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?""",
            (token_digest(raw),),
        ).fetchone()
        if not row or not row["active"] or row["expires_at"] <= now_text():
            raise Forbidden("Session expired.")
        user = {key: row[key] for key in
                ("id", "email", "display_name", "global_role", "active", "created_at", "is_primary_owner")}
        return user, row["csrf_token"]

    def _delete_session(self):
        raw = self._cookie_value(SESSION_COOKIE)
        if raw:
            self.db.execute("DELETE FROM sessions WHERE token_hash=?", (token_digest(raw),))

    def _cookie_value(self, name: str):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        return cookie[name].value if name in cookie else None

    # Routes that take the request body as raw file bytes; every other route is JSON
    # with the 1 MB ceiling whatever Content-Type the client declares.
    RAW_BODY_ROUTES = frozenset({"/api/import/preview", "/api/import/commit"})

    def _body(self, path: str) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().casefold()
        if path in self.RAW_BODY_ROUTES:
            # Raw upload (import): bytes are handed to the service untouched.
            if length > IMPORT_MAX_BYTES:
                raise PayloadTooLarge("The file is larger than 5 MB.")
            return {"_raw": self.rfile.read(length), "_content_type": content_type}
        if length > JSON_MAX_BYTES:
            raise ValueError("Request is too large.")
        raw = self.rfile.read(length)
        return json.loads(raw or b"{}")

    def _header_text(self, name: str) -> str:
        # Header values travel percent-encoded so non-ASCII filenames survive HTTP.
        return unquote(self.headers.get(name, "") or "").strip()

    def _header_json(self, name: str) -> dict:
        text = self._header_text(name)
        if not text:
            return {}
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be a JSON object.")
        return value

    def _download(self, payload: bytes, filename: str, content_type: str):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, value: dict, status=HTTPStatus.OK, cookie: str | None = None):
        # allow_nan=False: a NaN or Infinity would be a body no browser can parse (review DI-4).
        payload = json.dumps(value, default=str, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(payload)

    def _csv(self, export: dict):
        columns = ["project_name", "title", "owner_name", "status", "criticality",
                   "start_date", "due_date", "due_state", "next_action", "is_critical_path"]
        buffer = io.StringIO()
        # Header row first, no in-band comment line: some parsers/Excel treat a
        # leading "# ..." line as data. Provenance (as-of + active filters) rides in the filename.
        writer = csv.writer(buffer)
        writer.writerow(columns)
        for task in export["tasks"]:
            writer.writerow([_csv_cell(task.get(column)) for column in columns])
        payload = buffer.getvalue().encode("utf-8")
        filename = f"astra-export-{_as_of_slug(export.get('as_of'))}{_filter_slug(export.get('filters'))}.csv"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _csv_final_results(self, export: dict):
        columns = ["title", "source_type", "task_title", "project_name", "entities",
                   "attachment_path", "submission_version", "marked_by_name", "marked_at"]
        buffer = io.StringIO()
        # Header row first, no in-band comment line. As-of + active filters ride in the filename.
        writer = csv.writer(buffer)
        writer.writerow(columns)
        for item in export["results"]:
            row = dict(item)
            row["entities"] = "; ".join(row.get("entities") or [])
            writer.writerow([_csv_cell(row.get(column)) for column in columns])
        payload = buffer.getvalue().encode("utf-8")
        filename = f"astra-final-results-{_as_of_slug(export.get('as_of'))}{_filter_slug(export.get('filters'))}.csv"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _static(self, name: str):
        if name not in STATIC_FILES and name not in FONT_FILES:
            return self.send_error(HTTPStatus.NOT_FOUND)
        payload = files("astra").joinpath("static", *name.split("/")).read_bytes()
        if name in FONT_FILES:
            content_type, cache = "font/woff2", "public, max-age=31536000, immutable"
        elif name.endswith(".txt"):
            content_type, cache = "text/plain; charset=utf-8", "no-cache"
        else:
            content_type, cache = mimetypes.guess_type(name)[0] or "application/octet-stream", "no-cache"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.end_headers()
        self.wfile.write(payload)

    def _error(self, exc: Exception):
        if isinstance(exc, Forbidden):
            return self._json({"error": str(exc)}, HTTPStatus.FORBIDDEN)
        if isinstance(exc, (Conflict, ImportConflict)):
            return self._json({"error": str(exc)}, HTTPStatus.CONFLICT)
        if isinstance(exc, (PayloadTooLarge, ImportTooLarge)):
            return self._json({"error": str(exc)}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        if isinstance(exc, KeyError):
            return self._json({"error": str(exc).strip("'")}, HTTPStatus.NOT_FOUND)
        if isinstance(exc, (ValueError, json.JSONDecodeError)):
            return self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        self.log_error("Unhandled error: %r", exc)
        return self._json({"error": "Internal server error."}, HTTPStatus.INTERNAL_SERVER_ERROR)


class AstraServer(ThreadingHTTPServer):
    def __init__(self, address):
        super().__init__(address, AstraHandler)
        self.db_path = database_path()
        self.db = connect(self.db_path)
        self.service = AstraService(self.db)

    def server_close(self):
        super().server_close()
        # A failed bind raises inside __init__ before self.db exists.
        if getattr(self, "db", None) is not None:
            self.db.close()


def serve(host: str, port: int):
    server = AstraServer((host, port))
    print(f"Astra is running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
