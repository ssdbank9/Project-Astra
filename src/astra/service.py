from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import importer
from .auth import hash_password, normalize_email
from .db import V15_EXPECTED_REVISION_SQL, owner_request_intent_key, transaction


ROLES = {"owner", "chairman", "member"}
STATUSES = {
    "draft", "assigned", "in_progress", "submitted", "changes_requested",
    "completed", "on_hold", "delayed", "cancelled", "abandoned", "reopened",
}
CRITICALITIES = {"critical", "high", "normal", "low", None}
# Transitions that carry mandatory records (submission, acceptance, checkpoint,
# revised timeline) and must go through their dedicated lifecycle actions rather
# than a plain field update.
GOVERNED_STATUSES = {"submitted", "completed", "on_hold", "reopened"}
MANAGER_ORDINARY_STATUSES = {"draft", "assigned", "in_progress", "delayed"}
PROTECTED_STATUSES = {"changes_requested", "completed", "on_hold", "cancelled", "abandoned", "reopened"}
# Statuses a task may not be moved OUT of by a plain field update either: leaving them
# needs the record its lifecycle action writes (reopen, acceptance, hold release), so a
# Manager's attempt becomes an Owner request and the Owner is pointed at that action
# (adversarial review AS-1, 2026-09-22).
LOCKED_SOURCE_STATUSES = GOVERNED_STATUSES | PROTECTED_STATUSES | {"cancelled", "abandoned"}
REOPEN_ONLY_STATUSES = {"completed", "cancelled", "abandoned"}
UNSUBMITTABLE_STATUSES = frozenset({"submitted", "completed", "cancelled", "abandoned"})
REVIEWER_ROLES = {"reviewer", "approver", "collaborator"}
# SRFCZD: the request payload fields that carry an Owner-action request's intent. A
# direct Owner action resolves only the pending requests whose values for these fields
# equal what it executed; the free-text reason/note, the requester and expected_revision
# (filtered separately) are not intent. A field a request payload does not carry is not
# compared (only update_task_status omits from_status, when the source is not locked).
OWNER_REQUEST_INTENT_FIELDS = {
    "update_task_status": ("status", "from_status"),
    "accept_submission": ("submission_id",),
    "request_changes": ("submission_id",),
    "reopen_task": ("new_due_date",),
    "set_on_hold": ("checkpoint_date", "owner_user_id"),
    "approve_schedule_proposal": ("proposal_id",),
    "reject_schedule_proposal": ("proposal_id",),
    "close_project": ("exceptional", "residual_work"),
}
# The request fields callers and the API see. intent_key and expected_revision (schema 15,
# ticket WNXSDA) are lookup columns derived from these and are not part of a request.
OWNER_REQUEST_FIELDS = (
    "id", "project_id", "task_id", "action", "payload_json", "reason", "requested_by",
    "requested_at", "status", "decided_by", "decided_at", "decision_reason",
)
OWNER_REQUEST_COLUMNS = ",".join(OWNER_REQUEST_FIELDS)
OWNER_REQUEST_COLUMNS_R = ",".join(f"r.{field}" for field in OWNER_REQUEST_FIELDS)
# A dedicated reopen also satisfies a Manager's generic request to move a terminal task
# back into work, but never one to cancel, abandon, hold or otherwise govern it.
REOPEN_EQUIVALENT_STATUSES = frozenset(MANAGER_ORDINARY_STATUSES | {"reopened"})

LOGIN_WINDOW_SECONDS = 900
LOGIN_MAX_FAILURES = 5

# Approved baseline entities from the handoff (Section 4). Seeded only on explicit
# owner request; never injected automatically.
APPROVED_ENTITIES = [
    "Rupani Foundation USA",
    "Rupani Foundation Pakistan",
    "Rupani IB College",
    "Apex & Co",
    "Apex Amanat Microfinance",
    "Ibn Sina Medical College",
    "Ibn Sina Foundation",
    "RDI - Global",
    "RDI Pakistan",
    "Tax Exempt",
]


def now_text() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid4())


def row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


class Forbidden(PermissionError):
    pass


class Conflict(ValueError):
    """The requested write was based on state that is no longer current."""


@dataclass(frozen=True)
class OwnerDecision:
    """The Owner approval being executed (EXEZPM).

    Passed explicitly to a governed action so the action re-checks and resolves
    exactly this request. It is never stored on the service instance, so a nested
    or concurrent call cannot inherit or clear another approval's context.
    """

    request_id: str
    reason: str = ""


class ImportBlocked(Forbidden):
    """A non-permitted import attempt. Raised inside the import path and audited by the
    caller once no transaction is open, so the audit row survives the rollback."""

    def __init__(self, actor: dict, project: dict | None, action: str):
        super().__init__("Only the App Owner or a Manager of the target project may import into it.")
        self.actor, self.project, self.action = actor, project, action


class AstraService:
    def __init__(self, connection: sqlite3.Connection):
        self.db = connection

    def owner_exists(self) -> bool:
        return bool(self.db.execute("SELECT 1 FROM users WHERE global_role='owner'").fetchone())

    def login_is_throttled(self, email: str) -> bool:
        """True when this email has reached the failed-attempt cap inside the window."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=LOGIN_WINDOW_SECONDS)).isoformat()
        count = self.db.execute(
            "SELECT COUNT(*) c FROM login_attempts WHERE email=? AND success=0 AND attempted_at>=?",
            (email, cutoff),
        ).fetchone()["c"]
        return count >= LOGIN_MAX_FAILURES

    def record_login_attempt(self, email: str, ip: str, success: bool) -> None:
        self.db.execute(
            "INSERT INTO login_attempts VALUES(?,?,?,?,?)",
            (new_id(), email, ip or "", now_text(), 1 if success else 0),
        )
        if success:
            self.db.execute("DELETE FROM login_attempts WHERE email=? AND success=0", (email,))

    def cleanup_expired_sessions(self) -> None:
        self.db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_text(),))

    def revoke_user_sessions(self, user_id: str) -> int:
        cursor = self.db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        return cursor.rowcount

    def create_initial_owner(self, email: str, display_name: str, password: str) -> dict:
        if self.owner_exists():
            raise ValueError("An owner account already exists.")
        user_id = new_id()
        self.db.execute(
            "INSERT INTO users(id,email,display_name,password_hash,global_role,created_at) VALUES(?,?,?,?,?,?)",
            (user_id, normalize_email(email), display_name.strip() or "Owner", hash_password(password), "owner", now_text()),
        )
        return self.get_user(user_id)

    def get_user(self, user_id: str) -> dict:
        user = row_dict(self.db.execute(
            "SELECT id,email,display_name,global_role,active,created_at FROM users WHERE id=?", (user_id,)
        ).fetchone())
        if not user:
            raise KeyError("User not found.")
        return user

    def create_user(self, actor: dict, email: str, display_name: str, password: str, role: str = "member") -> dict:
        self.require_owner(actor)
        if role not in ROLES or role == "owner":
            raise ValueError("New users may be Chairman or member; owner transfer is a separate operation.")
        email = normalize_email(email)
        if not display_name.strip():
            raise ValueError("A display name is required.")
        if self.db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            raise ValueError("A user with this email already exists.")
        user_id = new_id()
        self.db.execute(
            "INSERT INTO users VALUES(?,?,?,?,?,?,?,?)",
            (user_id, email, display_name.strip(), hash_password(password), role, 1, now_text(), actor["id"]),
        )
        return self.get_user(user_id)

    def list_users(self, actor: dict) -> list[dict]:
        if actor["global_role"] not in {"owner", "chairman"}:
            raise Forbidden("User directory access denied.")
        rows = self.db.execute(
            "SELECT id,email,display_name,global_role,active,created_at FROM users ORDER BY display_name COLLATE NOCASE"
        ).fetchall()
        return [dict(row) for row in rows]

    def set_user_active(self, actor: dict, user_id: str, active: bool) -> dict:
        self.require_owner(actor)
        if user_id == actor["id"]:
            raise ValueError("You cannot change your own active status.")
        target = self.get_user(user_id)
        if target["global_role"] == "owner":
            raise ValueError("The owner account cannot be deactivated.")
        self.db.execute("UPDATE users SET active=? WHERE id=?", (1 if active else 0, user_id))
        if not active:
            self.revoke_user_sessions(user_id)
        return self.get_user(user_id)

    def list_assignable_users(self, actor: dict, project_id: str) -> list[dict]:
        if not self.can_manage_project(actor, project_id):
            raise Forbidden("Task-management access denied.")
        self._require_project(project_id)
        rows = self.db.execute(
            """SELECT DISTINCT u.id, u.display_name, u.email FROM users u
               WHERE u.active=1 AND (
                   u.global_role IN ('owner','chairman')
                   OR EXISTS(SELECT 1 FROM memberships m WHERE m.user_id=u.id AND m.project_id=?)
               )
               ORDER BY u.display_name COLLATE NOCASE""",
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def revoke_project_access(self, actor: dict, project_id: str, user_id: str) -> None:
        self.require_owner(actor)
        self.db.execute("DELETE FROM memberships WHERE project_id=? AND user_id=?", (project_id, user_id))

    def list_memberships(self, actor: dict, project_id: str | None = None) -> list[dict]:
        self.require_owner(actor)
        query = (
            "SELECT m.project_id, m.user_id, m.role, p.name project_name, u.display_name user_name "
            "FROM memberships m JOIN projects p ON p.id=m.project_id JOIN users u ON u.id=m.user_id"
        )
        params: tuple = ()
        if project_id:
            query += " WHERE m.project_id=?"
            params = (project_id,)
        query += " ORDER BY p.name COLLATE NOCASE, u.display_name COLLATE NOCASE"
        return [dict(row) for row in self.db.execute(query, params).fetchall()]

    # --- Entities and cross-entity project filing ---

    def get_entity(self, entity_id: str) -> dict:
        entity = row_dict(self.db.execute("SELECT * FROM entities WHERE id=?", (entity_id,)).fetchone())
        if not entity:
            raise KeyError("Entity not found.")
        return entity

    def list_entities(self, actor: dict) -> list[dict]:
        rows = self.db.execute("SELECT * FROM entities ORDER BY name COLLATE NOCASE").fetchall()
        return [dict(row) for row in rows]

    def create_entity(self, actor: dict, name: str) -> dict:
        self.require_owner(actor)
        name = str(name).strip()
        if not name:
            raise ValueError("Entity name is required.")
        if self.db.execute("SELECT 1 FROM entities WHERE name=?", (name,)).fetchone():
            raise ValueError("An entity with this name already exists.")
        entity_id = new_id()
        self.db.execute(
            "INSERT INTO entities VALUES(?,?,?,?,?)", (entity_id, name, 1, now_text(), actor["id"])
        )
        return self.get_entity(entity_id)

    def set_entity_active(self, actor: dict, entity_id: str, active: bool) -> dict:
        self.require_owner(actor)
        self.get_entity(entity_id)
        self.db.execute("UPDATE entities SET active=? WHERE id=?", (1 if active else 0, entity_id))
        return self.get_entity(entity_id)

    def seed_default_entities(self, actor: dict) -> list[str]:
        self.require_owner(actor)
        created = []
        for name in APPROVED_ENTITIES:
            if not self.db.execute("SELECT 1 FROM entities WHERE name=?", (name,)).fetchone():
                self.db.execute(
                    "INSERT INTO entities VALUES(?,?,?,?,?)", (new_id(), name, 1, now_text(), actor["id"])
                )
                created.append(name)
        return created

    def set_project_entities(self, actor: dict, project_id: str, entity_ids: list) -> list[dict]:
        # The owner chooses a project's filing entities; a cross-entity project keeps one
        # stable project id with several entity links rather than duplicated projects.
        self.require_owner(actor)
        self._require_project(project_id)
        seen = []
        with transaction(self.db):
            self.db.execute("DELETE FROM project_entities WHERE project_id=?", (project_id,))
            for entity_id in entity_ids or []:
                if entity_id in seen:
                    continue
                if not self.db.execute("SELECT 1 FROM entities WHERE id=?", (entity_id,)).fetchone():
                    raise ValueError("Unknown entity.")
                self.db.execute("INSERT INTO project_entities VALUES(?,?)", (project_id, entity_id))
                seen.append(entity_id)
        return self.list_project_entities(actor, project_id)

    def list_project_entities(self, actor: dict, project_id: str) -> list[dict]:
        self.get_project(actor, project_id)
        rows = self.db.execute(
            """SELECT e.id, e.name FROM project_entities pe JOIN entities e ON e.id=pe.entity_id
               WHERE pe.project_id=? ORDER BY e.name COLLATE NOCASE""",
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _attach_entities(self, projects: list[dict]) -> list[dict]:
        if not projects:
            return projects
        ids = [project["id"] for project in projects]
        placeholders = ",".join("?" for _ in ids)
        rows = self.db.execute(
            f"""SELECT pe.project_id, e.id, e.name FROM project_entities pe JOIN entities e ON e.id=pe.entity_id
                WHERE pe.project_id IN ({placeholders}) ORDER BY e.name COLLATE NOCASE""",
            tuple(ids),
        ).fetchall()
        by_project: dict[str, list] = {pid: [] for pid in ids}
        for row in rows:
            by_project[row["project_id"]].append({"id": row["id"], "name": row["name"]})
        for project in projects:
            project["entities"] = by_project.get(project["id"], [])
        return projects

    # --- Project working calendar (permissive by default: every day is a working day) ---

    def _project_working_days(self, project_id: str) -> set:
        row = self.db.execute("SELECT working_days FROM projects WHERE id=?", (project_id,)).fetchone()
        days = row["working_days"] if row and row["working_days"] else "0123456"
        return {int(c) for c in days if c in "0123456"}

    def is_working_day(self, project_id: str, day_iso: str) -> bool:
        if date.fromisoformat(day_iso).weekday() not in self._project_working_days(project_id):
            return False
        holiday = self.db.execute(
            "SELECT 1 FROM project_holidays WHERE project_id=? AND holiday_date=?", (project_id, day_iso)
        ).fetchone()
        return not holiday

    def working_days_between(self, project_id: str, start_iso: str, end_iso: str) -> int:
        start, end = date.fromisoformat(start_iso), date.fromisoformat(end_iso)
        if end < start:
            start, end = end, start
        working = self._project_working_days(project_id)
        holidays = {
            r["holiday_date"] for r in self.db.execute(
                "SELECT holiday_date FROM project_holidays WHERE project_id=?", (project_id,)
            ).fetchall()
        }
        count, day = 0, start
        while day <= end:
            if day.weekday() in working and day.isoformat() not in holidays:
                count += 1
            day += timedelta(days=1)
        return count

    def get_project_calendar(self, actor: dict, project_id: str) -> dict:
        project = self.get_project(actor, project_id)
        return {"working_days": project.get("working_days") or "0123456",
                "holidays": self.list_holidays(actor, project_id)}

    def set_working_days(self, actor: dict, project_id: str, days) -> str:
        self.require_owner(actor)
        self._require_project(project_id)
        if isinstance(days, (list, tuple)):
            days = "".join(str(x) for x in days)
        cleaned = "".join(sorted({c for c in str(days) if c in "0123456"}))
        if not cleaned:
            raise ValueError("At least one working day is required.")
        self.db.execute("UPDATE projects SET working_days=? WHERE id=?", (cleaned, project_id))
        return cleaned

    def list_holidays(self, actor: dict, project_id: str) -> list[dict]:
        self.get_project(actor, project_id)
        rows = self.db.execute(
            "SELECT holiday_date, label FROM project_holidays WHERE project_id=? ORDER BY holiday_date", (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def add_holiday(self, actor: dict, project_id: str, holiday_date, label: str = "") -> list[dict]:
        self.require_owner(actor)
        self._require_project(project_id)
        day = self._date(holiday_date)
        if not day:
            raise ValueError("A holiday date is required.")
        self.db.execute(
            "INSERT OR REPLACE INTO project_holidays(project_id,holiday_date,label,created_by,created_at)"
            " VALUES(?,?,?,?,?)",
            (project_id, day, str(label).strip(), actor["id"], now_text()),
        )
        return self.list_holidays(actor, project_id)

    def remove_holiday(self, actor: dict, project_id: str, holiday_date) -> None:
        self.require_owner(actor)
        self.db.execute(
            "DELETE FROM project_holidays WHERE project_id=? AND holiday_date=?", (project_id, self._date(holiday_date))
        )

    # --- Budgets and per-entity portfolio roll-up ---

    def set_project_budget(self, actor: dict, project_id: str, amount, currency: str) -> dict:
        self.require_owner(actor)
        self._require_project(project_id)
        if amount in (None, ""):
            amount = None
        else:
            amount = float(amount)
            if amount < 0:
                raise ValueError("Budget cannot be negative.")
        currency = (str(currency).strip().upper() or "PKR")
        self.db.execute(
            "UPDATE projects SET budget_amount=?, budget_currency=? WHERE id=?", (amount, currency, project_id)
        )
        return self.get_project(actor, project_id)

    def set_project_schedule(self, actor: dict, project_id: str, start_date, target_date, reason: str = "") -> dict:
        # Project dates are informational — recorded and change-logged, never a
        # constraint on task dates (matches the permissive calendar decision).
        if not self.can_manage_project(actor, project_id):
            raise Forbidden("Project-management access denied.")
        project = self.get_project(actor, project_id)
        start_date = self._date(start_date)
        target_date = self._date(target_date)
        if start_date and target_date and target_date < start_date:
            raise ValueError("Target date cannot be earlier than the start date.")
        old = {"start_date": project.get("start_date"), "target_date": project.get("target_date")}
        new = {"start_date": start_date, "target_date": target_date}
        if old == new:
            raise ValueError("The project schedule is already set to those dates.")
        reason = str(reason or "").strip()
        if not reason:
            raise ValueError("A reason is required to change the project schedule.")
        with transaction(self.db):
            self.db.execute(
                "UPDATE projects SET start_date=?, target_date=? WHERE id=?",
                (start_date, target_date, project_id),
            )
            self._project_event(project_id, actor["id"], "project_schedule_changed",
                                {"before": old, "after": new}, reason)
        return self.get_project(actor, project_id)

    def set_primary_entity(self, actor: dict, project_id: str, entity_id) -> dict:
        self.require_owner(actor)
        self._require_project(project_id)
        entity_id = entity_id or None
        if entity_id:
            linked = {e["id"] for e in self.list_project_entities(actor, project_id)}
            if entity_id not in linked:
                raise ValueError("The primary entity must be one of the project's entities.")
        self.db.execute("UPDATE projects SET primary_entity_id=? WHERE id=?", (entity_id, project_id))
        return self.get_project(actor, project_id)

    def _rollup_entity_id(self, project: dict):
        # A project's budget/tasks roll up to its primary entity; if none is set but the
        # project has exactly one entity, that one; otherwise unassigned (never double-counted).
        if project.get("primary_entity_id"):
            return project["primary_entity_id"]
        entities = project.get("entities", [])
        return entities[0]["id"] if len(entities) == 1 else None

    def portfolio_rollup(self, actor: dict) -> list[dict]:
        projects = self.list_projects(actor)
        tasks = self.list_tasks(actor)
        entity_name = {e["id"]: e["name"] for e in self.list_entities(actor)}
        closed = {"completed", "cancelled", "abandoned"}
        buckets: dict = {}

        def bucket(eid):
            if eid not in buckets:
                buckets[eid] = {
                    "entity_id": eid,
                    "entity_name": entity_name.get(eid, "Unassigned") if eid else "Unassigned",
                    "project_count": 0, "open": 0, "overdue": 0, "critical": 0, "budgets": {},
                }
            return buckets[eid]

        project_rollup = {}
        for project in projects:
            eid = self._rollup_entity_id(project)
            project_rollup[project["id"]] = eid
            b = bucket(eid)
            b["project_count"] += 1
            if project.get("budget_amount") is not None:
                currency = project.get("budget_currency") or "PKR"
                b["budgets"][currency] = round(b["budgets"].get(currency, 0) + project["budget_amount"], 2)
        for task in tasks:
            b = bucket(project_rollup.get(task["project_id"]))
            if task["status"] not in closed:
                b["open"] += 1
                if task.get("criticality") == "critical":
                    b["critical"] += 1
            if task.get("due_state") == "overdue":
                b["overdue"] += 1
        result = sorted((b for b in buckets.values() if b["entity_id"]), key=lambda b: b["entity_name"].lower())
        if None in buckets:
            result.append(buckets[None])
        return result

    def require_owner(self, actor: dict) -> None:
        if not actor.get("active") or actor.get("global_role") != "owner":
            raise Forbidden("Owner access required.")

    def can_view_project(self, actor: dict, project_id: str) -> bool:
        if actor["global_role"] in {"owner", "chairman"}:
            return True
        return bool(self.db.execute(
            "SELECT 1 FROM memberships WHERE project_id=? AND user_id=?", (project_id, actor["id"])
        ).fetchone())

    def can_manage_project(self, actor: dict, project_id: str) -> bool:
        if actor["global_role"] == "owner":
            return True
        row = self.db.execute(
            "SELECT role FROM memberships WHERE project_id=? AND user_id=?", (project_id, actor["id"])
        ).fetchone()
        return bool(row and row["role"] == "manager")

    def create_project(self, actor: dict, name: str, description: str = "", timezone_name: str = "Asia/Karachi") -> dict:
        self.require_owner(actor)
        if not name.strip():
            raise ValueError("Project name is required.")
        project_id = new_id()
        self.db.execute(
            "INSERT INTO projects(id,name,description,timezone,created_at,created_by) VALUES(?,?,?,?,?,?)",
            (project_id, name.strip(), description.strip(), timezone_name, now_text(), actor["id"]),
        )
        return self.get_project(actor, project_id)

    def get_project(self, actor: dict, project_id: str) -> dict:
        if not self.can_view_project(actor, project_id):
            raise Forbidden("Project access denied.")
        project = row_dict(self.db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
        if not project:
            raise KeyError("Project not found.")
        return self._attach_entities([project])[0]

    def list_projects(self, actor: dict) -> list[dict]:
        if actor["global_role"] in {"owner", "chairman"}:
            rows = self.db.execute("SELECT * FROM projects ORDER BY name COLLATE NOCASE").fetchall()
        else:
            rows = self.db.execute(
                "SELECT p.* FROM projects p JOIN memberships m ON m.project_id=p.id WHERE m.user_id=? ORDER BY p.name COLLATE NOCASE",
                (actor["id"],),
            ).fetchall()
        return self._attach_entities([dict(row) for row in rows])

    def grant_project_access(self, actor: dict, project_id: str, user_id: str, role: str) -> None:
        self.require_owner(actor)
        if role not in {"manager", "member", "viewer"}:
            raise ValueError("Invalid project role.")
        self.db.execute(
            "INSERT INTO memberships VALUES(?,?,?,?,?) ON CONFLICT(project_id,user_id) DO UPDATE SET role=excluded.role",
            (project_id, user_id, role, now_text(), actor["id"]),
        )

    def _require_project(self, project_id: str) -> None:
        if not self.db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            raise KeyError("Project not found.")

    def _validate_assignee(self, project_id: str, owner_user_id: str | None) -> str | None:
        if not owner_user_id:
            return None
        row = self.db.execute(
            "SELECT active, global_role FROM users WHERE id=?", (owner_user_id,)
        ).fetchone()
        if not row:
            raise ValueError("Assigned owner is not a known user.")
        if not row["active"]:
            raise ValueError("Assigned owner is not an active user.")
        if row["global_role"] in {"owner", "chairman"}:
            return owner_user_id
        member = self.db.execute(
            "SELECT 1 FROM memberships WHERE project_id=? AND user_id=?", (project_id, owner_user_id)
        ).fetchone()
        if not member:
            raise ValueError("Assigned owner must have access to this project.")
        return owner_user_id

    def create_task(self, actor: dict, payload: dict) -> dict:
        project_id = str(payload.get("project_id", ""))
        if not self.can_manage_project(actor, project_id):
            raise Forbidden("Task-management access denied.")
        self._require_project(project_id)
        title = str(payload.get("title", "")).strip()
        if not title:
            raise ValueError("Task title is required.")
        owner_user_id = self._validate_assignee(project_id, payload.get("owner_user_id") or None)
        status = payload.get("status", "draft")
        criticality = payload.get("criticality") or None
        if status not in STATUSES or criticality not in CRITICALITIES:
            raise ValueError("Invalid task status or criticality.")
        if actor["global_role"] != "owner" and status not in MANAGER_ORDINARY_STATUSES:
            raise Forbidden("Managers may create tasks only in an ordinary working status.")
        start_date = self._date(payload.get("start_date"))
        due_date = self._date(payload.get("due_date"))
        if start_date and due_date and due_date < start_date:
            raise ValueError("Due date cannot be earlier than start date.")
        parent_task_id = payload.get("parent_task_id") or None
        predecessor_task_id = payload.get("predecessor_task_id") or None
        if parent_task_id:
            parent = self.get_task(actor, parent_task_id)
            if parent["project_id"] != project_id:
                raise ValueError("A parent task must belong to the same project.")
        if predecessor_task_id:
            predecessor = self.get_task(actor, predecessor_task_id)
            if predecessor["project_id"] != project_id:
                raise ValueError("A predecessor task must belong to the same project.")
        task_id = new_id()
        timestamp = now_text()
        with transaction(self.db):
            self.db.execute(
                """INSERT INTO tasks(id,project_id,parent_task_id,title,description,owner_user_id,status,criticality,
                   start_date,due_date,progress,created_at,created_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (task_id, project_id, parent_task_id, title, str(payload.get("description", "")).strip(),
                 owner_user_id, status, criticality, start_date, due_date,
                 self._progress(payload.get("progress")), timestamp, actor["id"], timestamp),
            )
            self._ensure_baseline(task_id)
            task = self.get_task(actor, task_id)
            self._event(task_id, actor["id"], "task_created", None, task, payload.get("reason"))
            if predecessor_task_id:
                self.db.execute(
                    "INSERT INTO task_dependencies VALUES(?,?,?)",
                    (predecessor_task_id, task_id, "finish_to_start"),
                )
                self._event(
                    task_id,
                    actor["id"],
                    "dependency_added",
                    None,
                    {"predecessor_task_id": predecessor_task_id, "dependency_type": "finish_to_start"},
                    None,
                )
        return task

    def update_task(self, actor: dict, task_id: str, payload: dict,
        *, owner_decision: OwnerDecision | None = None,
    ) -> dict:
        before = self.get_task(actor, task_id)
        if not self.can_manage_project(actor, before["project_id"]):
            raise Forbidden("Task-management access denied.")
        expected_revision = payload.get("expected_revision")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise ValueError("An integer expected_revision is required to update a task.")
        if expected_revision != before["revision"]:
            raise Conflict(
                f"Task revision conflict: expected {expected_revision}, current revision is {before['revision']}."
            )
        merged = {**before, **payload}
        status = merged["status"]
        criticality = merged.get("criticality") or None
        if status not in STATUSES or criticality not in CRITICALITIES:
            raise ValueError("Invalid task status or criticality.")
        status_changed = status != before["status"]
        if status_changed and status == "submitted":
            raise ValueError("Use the dedicated submitted action for this transition.")
        # SRFCZD R5 (SEM-2): refused for a Manager too, before any request exists; the Owner
        # could never approve a generic request into these statuses.
        if status_changed and status in GOVERNED_STATUSES:
            raise ValueError(f"Use the dedicated {status.replace('_', ' ')} action for this transition.")
        # T8WHJR: with the status unchanged, a closed task has nothing an update may write, so
        # the call is refused even when no field differs (a reason-only save must not bump the
        # revision or add a task_updated event). The revision predicate below keeps a task
        # closed after this check out of the write.
        if before["status"] in REOPEN_ONLY_STATUSES and not status_changed:
            raise ValueError(
                f"A {before['status']} task is immutable; reopen the task first with the dedicated reopen task action."
            )
        if criticality != (before.get("criticality") or None):
            raise ValueError("Use the confirm criticality action to change criticality.")
        reason = str(payload.get("reason", "")).strip() or None
        sensitive_change = any(before.get(key) != merged.get(key) for key in ("start_date", "due_date", "status"))
        if sensitive_change and not reason:
            raise ValueError("A reason is required for schedule or status changes.")
        if status_changed and status in {"cancelled", "abandoned", "on_hold", "delayed", "reopened"} and not reason:
            raise ValueError("This lifecycle change requires a reason.")
        start_date, due_date = self._date(merged.get("start_date")), self._date(merged.get("due_date"))
        if start_date and due_date and due_date < start_date:
            raise ValueError("Due date cannot be earlier than start date.")
        title = str(merged.get("title", "")).strip()
        if not title:
            raise ValueError("Task title is required.")
        if "owner_user_id" in payload:
            owner_user_id = self._validate_assignee(before["project_id"], payload.get("owner_user_id") or None)
        else:
            owner_user_id = before.get("owner_user_id")
        if status_changed and before["status"] in LOCKED_SOURCE_STATUSES:
            # The source status is protected too: a Manager may only request the change and
            # the Owner leaves completed / cancelled / abandoned through reopen_task (reason
            # and revised due date) and submitted through the submission decision. There is
            # no dedicated release action for on_hold, changes_requested or reopened, so the
            # Owner's update with a reason is the recorded path out of those. Leaving review is
            # refused for a Manager as well (SEM-2): only the submission decision does it.
            if before["status"] == "submitted":
                raise ValueError("A submitted task leaves review through the dedicated accept or request changes action.")
            # SRFCZD R6 (R5-1): from a terminal status only a move back into ordinary work
            # may become a Manager request, which reopen then reconciles (handoff 7.1). Any
            # other target (cancelled, abandoned, changes_requested) could never be approved
            # or resolved, so it is refused for a Manager too, with the Owner's message.
            reopen_refusal = (
                f"A {before['status']} task is not edited back into work; use the dedicated reopen task action "
                "(reason and revised due date) so the reopening is recorded."
            )
            if before["status"] in REOPEN_ONLY_STATUSES and status not in REOPEN_EQUIVALENT_STATUSES:
                raise ValueError(reopen_refusal)
            if actor["global_role"] != "owner":
                return self._request_protected_action(
                    actor,
                    before,
                    "update_task_status",
                    {"status": status, "from_status": before["status"], "reason": reason,
                     "expected_revision": before["revision"]},
                    reason or "",
                )
            if before["status"] in REOPEN_ONLY_STATUSES:
                raise ValueError(reopen_refusal)
        if status_changed and actor["global_role"] != "owner" and status in PROTECTED_STATUSES:
            return self._request_protected_action(
                actor,
                before,
                "update_task_status",
                {"status": status, "reason": reason, "expected_revision": before["revision"]},
                reason or "",
            )
        with transaction(self.db):
            # An approval re-checks, under the write lock, that its request is still pending.
            self._assert_active_request_revision(before, owner_decision)
            cursor = self.db.execute(
                """UPDATE tasks SET title=?,description=?,owner_user_id=?,status=?,criticality=?,start_date=?,due_date=?,
                   progress=?,updated_at=?,revision=revision+1 WHERE id=? AND revision=?""",
                (title, str(merged.get("description", "")).strip(), owner_user_id,
                 status, criticality, start_date, due_date, self._progress(merged.get("progress")), now_text(), task_id,
                 expected_revision),
            )
            if cursor.rowcount != 1:
                raise Conflict("Task revision conflict: the task changed before this update could be saved.")
            self._ensure_baseline(task_id)
            after = self.get_task(actor, task_id)
            self._event(task_id, actor["id"], "task_updated", before, after, reason)
            if status_changed:
                self._resolve_pending_requests(
                    actor,
                    "update_task_status",
                    project_id=before["project_id"],
                    intent={"status": status, "from_status": before["status"]},
                    task_id=task_id,
                    expected_revision=expected_revision,
                    decision_reason=reason or "",
                    owner_decision=owner_decision,
                )
        return after

    # T8WHJR (Aly Jafferani, 2026-09-23): a completed, cancelled or abandoned task is a fixed
    # record. reopen_task (reason and revised due date) is the only write that changes it;
    # attachment links and final results may still be added, since evidence often arrives
    # after closure, and a closed task may still become the predecessor of an open task.
    @staticmethod
    def _refuse_closed(task: dict) -> None:
        if task["status"] in REOPEN_ONLY_STATUSES:
            raise ValueError(f"A {task['status']} task is a fixed record; reopen the task first.")

    def _refuse_closed_in_transaction(self, task_id: str) -> None:
        """Re-read the status under the write lock: a task closed after the pre-check is a 409."""
        row = self.db.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row and row["status"] in REOPEN_ONLY_STATUSES:
            raise Conflict(f"The task was {row['status']} before this change could be saved; reopen the task first.")

    def get_task(self, actor: dict, task_id: str) -> dict:
        task = row_dict(self.db.execute(
            """SELECT t.*, u.display_name owner_name, p.name project_name, p.timezone project_timezone FROM tasks t
               LEFT JOIN users u ON u.id=t.owner_user_id JOIN projects p ON p.id=t.project_id WHERE t.id=?""",
            (task_id,),
        ).fetchone())
        if not task:
            raise KeyError("Task not found.")
        if not self.can_view_project(actor, task["project_id"]):
            raise Forbidden("Task access denied.")
        return task

    # QY0WG2 (owner decision 2026-09-15): the task list offers BOTH orderings as a
    # user-selectable toggle, not a single hard-coded one. "criticality" sorts by
    # consequence first (Critical>High>Normal>Low, Unrated last) then nearest due
    # date; "due_date" sorts by nearest/overdue date first (undated last) then by
    # criticality. Both end on title as a stable tiebreaker.
    SORT_MODES = ("criticality", "due_date")
    _CRITICALITY_RANK = ("CASE t.criticality WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
                         "WHEN 'normal' THEN 2 WHEN 'low' THEN 3 ELSE 4 END")
    _DUE_DATE_KEY = "COALESCE(t.due_date,'9999-12-31')"

    def list_tasks(self, actor: dict, project_id: str | None = None, sort: str = "criticality") -> list[dict]:
        sort = sort if sort in self.SORT_MODES else "criticality"
        clauses, params = [], []
        if project_id:
            if not self.can_view_project(actor, project_id):
                raise Forbidden("Project access denied.")
            clauses.append("t.project_id=?")
            params.append(project_id)
        if actor["global_role"] not in {"owner", "chairman"}:
            clauses.append("EXISTS(SELECT 1 FROM memberships m WHERE m.project_id=t.project_id AND m.user_id=?)")
            params.append(actor["id"])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        if sort == "due_date":
            order_by = f" ORDER BY {self._DUE_DATE_KEY}, {self._CRITICALITY_RANK}, t.title COLLATE NOCASE"
        else:
            order_by = f" ORDER BY {self._CRITICALITY_RANK}, {self._DUE_DATE_KEY}, t.title COLLATE NOCASE"
        rows = self.db.execute(
            """SELECT t.*, u.display_name owner_name, p.name project_name, p.timezone project_timezone FROM tasks t
               LEFT JOIN users u ON u.id=t.owner_user_id JOIN projects p ON p.id=t.project_id"""
            + where
            + order_by,
            params,
        ).fetchall()
        today_by_tz: dict[str | None, str] = {}
        result = []
        for row in rows:
            item = dict(row)
            tz_name = item.get("project_timezone")
            if tz_name not in today_by_tz:
                today_by_tz[tz_name] = self._today_in_timezone(tz_name)
            today = today_by_tz[tz_name]
            item["due_state"] = self._due_state(item.get("due_date"), item["status"], today)
            item["days_to_due"] = (
                None if not item.get("due_date")
                else (date.fromisoformat(item["due_date"]) - date.fromisoformat(today)).days
            )
            result.append(item)
        self._add_dependency_state(result)
        self._add_critical_path(result)
        for item in result:
            item["next_action"] = self._next_action(item)
        return result

    @staticmethod
    def _duration_days(task: dict) -> int:
        start, due = task.get("start_date"), task.get("due_date")
        if start and due:
            return max(1, (date.fromisoformat(due) - date.fromisoformat(start)).days + 1)
        return 1

    def _add_critical_path(self, tasks: list[dict]) -> list[dict]:
        for task in tasks:
            task["is_critical_path"] = False
        by_id = {task["id"]: task for task in tasks}
        if not by_id:
            return tasks
        placeholders = ",".join("?" for _ in by_id)
        params = tuple(by_id) + tuple(by_id)
        rows = self.db.execute(
            f"""SELECT predecessor_task_id, successor_task_id FROM task_dependencies
                WHERE predecessor_task_id IN ({placeholders}) AND successor_task_id IN ({placeholders})""",
            params,
        ).fetchall()
        edges_by_project: dict[str, list] = {}
        tasks_by_project: dict[str, list] = {}
        for task in tasks:
            tasks_by_project.setdefault(task["project_id"], []).append(task["id"])
        for row in rows:
            pred, succ = row["predecessor_task_id"], row["successor_task_id"]
            if by_id[pred]["project_id"] == by_id[succ]["project_id"]:
                edges_by_project.setdefault(by_id[pred]["project_id"], []).append((pred, succ))
        for project_id, task_ids in tasks_by_project.items():
            for task_id in self._critical_path_nodes(task_ids, edges_by_project.get(project_id, []), by_id):
                by_id[task_id]["is_critical_path"] = True
        return tasks

    def _critical_path_nodes(self, task_ids: list, edges: list, by_id: dict) -> set:
        """Critical activities in one project by full CPM (AYW0QC, owner decision
        2026-09-15): a forward pass (earliest start/finish) and backward pass
        (latest start/finish) over the finish-to-start dependency network yield a
        slack per activity; every zero-slack activity is critical. This marks ALL
        parallel critical paths, not just a single longest chain.

        Cancelled/abandoned tasks are excluded. Only tasks in the dependency
        network (with a predecessor or successor) participate; an isolated task is
        never on the critical path. With no edges at all there is no critical path.
        """
        active = {tid for tid in task_ids if by_id[tid]["status"] not in ("cancelled", "abandoned")}
        preds = {tid: [] for tid in active}
        succ = {tid: [] for tid in active}
        indeg = {tid: 0 for tid in active}
        has_edge = False
        for pred, s in edges:
            if pred in active and s in active:
                preds[s].append(pred)
                succ[pred].append(s)
                indeg[s] += 1
                has_edge = True
        if not has_edge:
            return set()
        # The network is the connected part; isolated tasks are ignored entirely.
        network = {tid for tid in active if preds[tid] or succ[tid]}
        # Kahn topological order (dependencies are acyclic by construction).
        queue = [tid for tid in network if indeg[tid] == 0]
        remaining = {tid: indeg[tid] for tid in network}
        topo = []
        while queue:
            node = queue.pop(0)
            topo.append(node)
            for nxt in succ[node]:
                remaining[nxt] -= 1
                if remaining[nxt] == 0:
                    queue.append(nxt)
        if len(topo) != len(network):  # a cycle slipped in — refuse to guess
            return set()
        duration = {tid: self._duration_days(by_id[tid]) for tid in network}
        # Forward pass: earliest start / earliest finish.
        es, ef = {}, {}
        for node in topo:
            es[node] = max((ef[p] for p in preds[node] if p in network), default=0)
            ef[node] = es[node] + duration[node]
        project_end = max(ef.values())
        # Backward pass: latest finish / latest start (over reverse topo order).
        lf, ls = {}, {}
        for node in reversed(topo):
            lf[node] = min((ls[s] for s in succ[node] if s in network), default=project_end)
            ls[node] = lf[node] - duration[node]
        # Zero-slack activities are critical (float compares exactly on ints).
        return {node for node in network if ls[node] - es[node] == 0}

    @staticmethod
    def _next_action(task: dict) -> str:
        status = task["status"]
        if status in {"completed", "cancelled", "abandoned"}:
            return "None"
        if task.get("next_action_note"):
            # A human-written next action (imported from the sheet) wins over the derived rule while the task is open.
            return task["next_action_note"]
        if task.get("is_blocked"):
            return "Blocked by predecessors"
        if status == "submitted":
            return "Awaiting acceptance"
        if status == "changes_requested":
            return "Rework by owner"
        if status == "on_hold":
            return "Resume at checkpoint"
        if not task.get("owner_user_id"):
            return "Assign an owner"
        if not task.get("due_date"):
            return "Set a due date"
        return "In progress by owner"

    def search(self, actor: dict, query: str) -> dict:
        term = str(query).strip()
        if not term:
            return {"tasks": [], "projects": []}
        like = f"%{term}%"
        if actor["global_role"] in {"owner", "chairman"}:
            task_rows = self.db.execute(
                """SELECT t.id,t.title,t.status,p.name project_name FROM tasks t JOIN projects p ON p.id=t.project_id
                   WHERE t.title LIKE ? OR t.description LIKE ? ORDER BY t.title COLLATE NOCASE LIMIT 50""",
                (like, like),
            ).fetchall()
            project_rows = self.db.execute(
                "SELECT id,name FROM projects WHERE name LIKE ? ORDER BY name COLLATE NOCASE LIMIT 50", (like,)
            ).fetchall()
        else:
            task_rows = self.db.execute(
                """SELECT t.id,t.title,t.status,p.name project_name FROM tasks t JOIN projects p ON p.id=t.project_id
                   WHERE (t.title LIKE ? OR t.description LIKE ?)
                     AND EXISTS(SELECT 1 FROM memberships m WHERE m.project_id=t.project_id AND m.user_id=?)
                   ORDER BY t.title COLLATE NOCASE LIMIT 50""",
                (like, like, actor["id"]),
            ).fetchall()
            project_rows = self.db.execute(
                """SELECT p.id,p.name FROM projects p JOIN memberships m ON m.project_id=p.id
                   WHERE m.user_id=? AND p.name LIKE ? ORDER BY p.name COLLATE NOCASE LIMIT 50""",
                (actor["id"], like),
            ).fetchall()
        return {"tasks": [dict(r) for r in task_rows], "projects": [dict(r) for r in project_rows]}

    def export_tasks(self, actor: dict, filters: dict) -> dict:
        # Authorization is inherited from list_tasks; only the actor's visible tasks are ever returned.
        tasks = self.list_tasks(actor, filters.get("project_id") or None, filters.get("sort") or "criticality")
        status = filters.get("status") or None
        entity = filters.get("entity_id") or None
        criticality = filters.get("criticality") or None
        owner = (filters.get("owner") or "").lower()
        band = filters.get("band") or None
        open_only = bool(filters.get("open_only"))
        entity_projects = None
        if entity:
            entity_projects = {
                p["id"] for p in self.list_projects(actor) if any(e["id"] == entity for e in p.get("entities", []))
            }

        def keep(t: dict) -> bool:
            if status and t["status"] != status:
                return False
            if criticality:
                if criticality == "unrated" and t.get("criticality"):
                    return False
                if criticality != "unrated" and t.get("criticality") != criticality:
                    return False
            if owner and owner not in (t.get("owner_name") or "").lower():
                return False
            if open_only and t["status"] in ("completed", "cancelled", "abandoned"):
                return False
            if entity_projects is not None and t["project_id"] not in entity_projects:
                return False
            if band == "overdue" and t.get("due_state") != "overdue":
                return False
            if band == "today" and t.get("due_state") != "today":
                return False
            if band and band.isdigit():
                days = t.get("days_to_due")
                if days is None or days < 0 or days > int(band):
                    return False
            return True

        return {"as_of": now_text(), "filters": filters, "tasks": [t for t in tasks if keep(t)]}

    def task_detail(self, actor: dict, task_id: str) -> dict:
        task = self.get_task(actor, task_id)
        is_owner = actor["global_role"] == "owner"
        is_manager = self._is_project_manager(actor, task["project_id"])
        task["permissions"] = {
            "can_edit_ordinary": is_owner or is_manager,
            "can_request_protected": is_manager or self._is_approver(task_id, actor["id"]),
            "can_decide_protected": is_owner,
            "can_manage_files": is_owner,
            "can_read_files": True,
        }
        task["due_state"] = self._due_state(
            task.get("due_date"), task["status"], self._today_in_timezone(task.get("project_timezone"))
        )
        task["dependencies"] = self.get_task_dependencies(actor, task_id)
        task["submissions"] = self.list_task_submissions(actor, task_id)
        task["reviewers"] = self.list_task_reviewers(actor, task_id)
        task["attachments"] = self.list_task_attachments(actor, task_id)
        task["final_results"] = self.list_task_final_results(actor, task_id)
        subtasks = self.list_subtasks(actor, task_id)
        task["subtasks"] = subtasks
        task["subtask_rollup"] = {
            "total": len(subtasks),
            "completed": sum(1 for s in subtasks if s["status"] == "completed"),
        }
        task["baseline"] = {"start_date": task.get("baseline_start_date"), "due_date": task.get("baseline_due_date")}
        task["imported_fields"] = self._imported_fields(task)
        task["schedule_proposals"] = self.list_schedule_proposals(actor, task_id)
        if task.get("due_date"):
            today = self._today_in_timezone(task.get("project_timezone"))
            task["working_days_to_due"] = self.working_days_between(task["project_id"], today, task["due_date"])
        else:
            task["working_days_to_due"] = None
        if task.get("parent_task_id"):
            parent = self.db.execute(
                "SELECT title FROM tasks WHERE id=?", (task["parent_task_id"],)
            ).fetchone()
            task["parent_title"] = parent["title"] if parent else None
        else:
            task["parent_title"] = None
        return task

    def task_events(self, actor: dict, task_id: str) -> list[dict]:
        self.get_task(actor, task_id)
        rows = self.db.execute(
            """SELECT e.*, u.display_name actor_name FROM task_events e
               LEFT JOIN users u ON u.id=e.actor_user_id
               WHERE e.task_id=? ORDER BY e.occurred_at,e.id""",
            (task_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    # --- Lifecycle: submissions, acceptance, review, reopening, holds ---

    def get_submission(self, actor: dict, submission_id: str) -> dict:
        row = row_dict(self.db.execute(
            """SELECT s.*, t.project_id, sb.display_name submitted_by_name, db.display_name decided_by_name
               FROM task_submissions s JOIN tasks t ON t.id=s.task_id
               LEFT JOIN users sb ON sb.id=s.submitted_by
               LEFT JOIN users db ON db.id=s.decided_by WHERE s.id=?""",
            (submission_id,),
        ).fetchone())
        if not row:
            raise KeyError("Submission not found.")
        if not self.can_view_project(actor, row["project_id"]):
            raise Forbidden("Submission access denied.")
        return row

    def list_task_submissions(self, actor: dict, task_id: str) -> list[dict]:
        self.get_task(actor, task_id)
        rows = self.db.execute(
            """SELECT s.*, sb.display_name submitted_by_name, db.display_name decided_by_name
               FROM task_submissions s LEFT JOIN users sb ON sb.id=s.submitted_by
               LEFT JOIN users db ON db.id=s.decided_by
               WHERE s.task_id=? ORDER BY s.version""",
            (task_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _is_approver(self, task_id: str, user_id: str) -> bool:
        return bool(self.db.execute(
            "SELECT 1 FROM task_reviewers WHERE task_id=? AND user_id=? AND role='approver'",
            (task_id, user_id),
        ).fetchone())

    def _is_project_manager(self, actor: dict, project_id: str) -> bool:
        return bool(self.db.execute(
            "SELECT 1 FROM memberships WHERE project_id=? AND user_id=? AND role='manager'",
            (project_id, actor["id"]),
        ).fetchone())

    def _request_protected_action(
        self,
        actor: dict,
        task: dict,
        action: str,
        payload: dict | None = None,
        reason: str = "",
    ) -> dict:
        if not (self._is_project_manager(actor, task["project_id"])
                or self._is_approver(task["id"], actor["id"])):
            self._event(
                task["id"], actor["id"], "protected_action_blocked", None,
                {"action": action, "payload": payload or {}}, "Actor cannot request this Owner action",
            )
            raise Forbidden("Only a project Manager or designated approver may request this Owner action.")
        request_payload = dict(payload or {})
        request_payload.setdefault("expected_revision", task["revision"])
        payload_json = json.dumps(request_payload, default=str, sort_keys=True)
        request_reason = str(reason or "").strip()
        request = {
            "id": None,
            "project_id": task["project_id"],
            "task_id": task["id"],
            "action": action,
            "payload_json": payload_json,
            "reason": request_reason,
            "requested_by": actor["id"],
            "requested_at": None,
            "status": "pending",
            "decided_by": None,
            "decided_at": None,
            "decision_reason": None,
        }
        with transaction(self.db):
            # Review SVC-2: the request is only as good as the state it was based on; a task
            # changed (for example closed) after the caller's checks is a 409, not a queued 202.
            current = self.db.execute("SELECT revision FROM tasks WHERE id=?", (task["id"],)).fetchone()
            if not current or current["revision"] != request_payload["expected_revision"]:
                raise Conflict("Task revision conflict: the task changed before this request could be filed.")
            existing = self._pending_request_by_intent(request)
            if existing:
                return {"request": existing}
            request_id, requested_at = new_id(), now_text()
            request["id"], request["requested_at"] = request_id, requested_at
            self._insert_owner_request(request)
            self._event(
                task["id"], actor["id"], "protected_action_requested", None,
                {"request_id": request_id, "action": action, "payload": request_payload},
                request_reason or None,
            )
        return {"request": request}

    def _request_protected_project_action(
        self,
        actor: dict,
        project: dict,
        action: str,
        payload: dict | None = None,
        reason: str = "",
    ) -> dict:
        if not self._is_project_manager(actor, project["id"]):
            event_id = new_id()
            occurred_at = now_text()
            self._project_event(
                project["id"], actor["id"], "protected_action_blocked",
                {"event_id": event_id, "action": action, "payload": payload or {}},
                "Actor cannot request this Owner action",
            )
            owner = self.db.execute("SELECT id FROM users WHERE global_role='owner'").fetchone()
            if owner and owner["id"] != actor["id"]:
                self.db.execute(
                    "INSERT OR IGNORE INTO notifications"
                    "(id,user_id,event_id,task_id,kind,summary,created_at) VALUES(?,?,?,?,?,?,?)",
                    (new_id(), owner["id"], event_id, None, "protected_action_blocked",
                     f"blocked {action.replace('_', ' ')} attempt: {project['name']}", occurred_at),
                )
            raise Forbidden("Only a project Manager may request this Owner action.")
        request_payload = dict(payload or {})
        payload_json = json.dumps(request_payload, default=str, sort_keys=True)
        request_reason = str(reason or "").strip()
        request = {
            "id": None,
            "project_id": project["id"],
            "task_id": None,
            "action": action,
            "payload_json": payload_json,
            "reason": request_reason,
            "requested_by": actor["id"],
            "requested_at": None,
            "status": "pending",
            "decided_by": None,
            "decided_at": None,
            "decision_reason": None,
        }
        with transaction(self.db):
            existing = self._pending_request_by_intent(request)
            if existing:
                return {"request": existing}
            request_id, requested_at = new_id(), now_text()
            request["id"], request["requested_at"] = request_id, requested_at
            self._insert_owner_request(request)
            self._project_event(
                project["id"], actor["id"], "protected_action_requested",
                {"request_id": request_id, "action": action, "payload": request_payload},
                request_reason or None,
            )
            owner = self.db.execute("SELECT id FROM users WHERE global_role='owner'").fetchone()
            if owner and owner["id"] != actor["id"]:
                self.db.execute(
                    "INSERT OR IGNORE INTO notifications"
                    "(id,user_id,event_id,task_id,kind,summary,created_at) VALUES(?,?,?,?,?,?,?)",
                    (new_id(), owner["id"], request_id, None, "protected_action_requested",
                     f"{action.replace('_', ' ')} requested: {project['name']}", requested_at),
                )
        return {"request": request}

    @staticmethod
    def _request_intent_key(request: dict) -> str:
        return owner_request_intent_key(
            request["project_id"], request["task_id"], request["action"],
            request["payload_json"], request["reason"], request["requested_by"],
        )

    def _pending_request_by_intent(self, request: dict) -> dict | None:
        """The pending request an identical new one would duplicate, found by the unique
        intent key (schema 15) rather than by comparing payload text per row. Callers
        hold the write transaction, so the lookup and their INSERT cannot interleave with
        another writer; the unique index refuses a duplicate even if they did."""
        row = self.db.execute(
            f"SELECT {OWNER_REQUEST_COLUMNS} FROM owner_action_requests"
            " WHERE intent_key=? AND status='pending'",
            (self._request_intent_key(request),),
        ).fetchone()
        return dict(row) if row else None

    def _insert_owner_request(self, request: dict) -> None:
        self.db.execute(
            "INSERT INTO owner_action_requests"
            "(id,project_id,task_id,action,payload_json,reason,requested_by,requested_at,status,"
            "intent_key,expected_revision) VALUES(?,?,?,?,?,?,?,?,?,?,"
            + V15_EXPECTED_REVISION_SQL.format(payload="?") + ")",
            (request["id"], request["project_id"], request["task_id"], request["action"],
             request["payload_json"], request["reason"], request["requested_by"],
             request["requested_at"], request["status"], self._request_intent_key(request),
             request["payload_json"], request["payload_json"]),
        )

    def _owner_action_request(self, actor: dict, request_id: str) -> dict:
        self.require_owner(actor)
        row = row_dict(self.db.execute(
            f"""SELECT {OWNER_REQUEST_COLUMNS_R}, p.name project_name, t.title task_title, u.display_name requested_by_name
               FROM owner_action_requests r
               JOIN projects p ON p.id=r.project_id
               LEFT JOIN tasks t ON t.id=r.task_id
               JOIN users u ON u.id=r.requested_by WHERE r.id=?""",
            (request_id,),
        ).fetchone())
        if not row:
            raise KeyError("Owner-action request not found.")
        row["payload"] = json.loads(row["payload_json"])
        return row

    @staticmethod
    def _residual_work_matches(requested: list | None, current: list | None) -> bool:
        """Whether a close request's recorded residual work is still the open work.

        Compared as {task id: status}; titles and order are not intent. A recorded item
        without a status (a request made before statuses were recorded) matches any status.
        Both a direct close's reconciliation and an approval's re-check use this test.
        """
        requested_work = {item["id"]: item.get("status") for item in requested or []}
        current_work = {item["id"]: item.get("status") for item in current or []}
        return requested_work.keys() == current_work.keys() and all(
            status is None or status == current_work[task_id] for task_id, status in requested_work.items()
        )

    @staticmethod
    def _request_intent_matches(action: str, payload: dict, intent: dict) -> bool:
        # An intent value given as a frozenset accepts any of its members.
        for field in OWNER_REQUEST_INTENT_FIELDS[action]:
            if field not in payload:
                continue
            requested, executed = payload[field], intent.get(field)
            if field == "residual_work":
                matched = AstraService._residual_work_matches(requested, executed)
            elif isinstance(executed, frozenset):
                matched = requested in executed
            else:
                matched = requested == executed
            if not matched:
                return False
        return True

    def _resolve_pending_requests(
        self,
        actor: dict,
        action: str,
        *,
        project_id: str,
        intent: dict,
        task_id: str | None = None,
        expected_revision: int | None = None,
        decision_reason: str = "",
        owner_decision: OwnerDecision | None = None,
    ) -> None:
        """Resolve the active approval and the equivalent requests the executed action satisfied.

        Only pending requests whose intent fields (see OWNER_REQUEST_INTENT_FIELDS)
        match ``intent`` are resolved; any other request stays pending and untouched.
        An approval resolves its own request first, then (G9G9PX, SEM-3) every other
        request this same test matches, exactly as a direct Owner action would; their
        events name the approved request. Callers invoke this inside the action's
        transaction, so the governed state and its queue record cannot commit
        independently. An approved request records the Owner's own decision note,
        never the Manager's request reason that the governed action itself carries.
        """
        active_id = owner_decision.request_id if owner_decision else None
        active_rows = []
        if active_id:
            decision_reason = owner_decision.reason
            active_rows = self.db.execute(
                "SELECT * FROM owner_action_requests WHERE id=? AND status='pending'",
                (active_id,),
            ).fetchall()
        # Scope, action and revision are indexed columns (schema 15). The intent test
        # below stays in Python by design: it is semantic, not an exact match (fields
        # absent from older payloads are skipped, a frozenset intent accepts any member,
        # residual_work items without a status match any status, and it spans
        # requesters), so an exact key such as intent_key would change which requests
        # an Owner action resolves.
        query = (
            "SELECT * FROM owner_action_requests"
            " WHERE project_id=? AND task_id IS ? AND action=? AND status='pending'"
        )
        params: list = [project_id, task_id, action]
        if task_id is not None and expected_revision is not None:
            query += " AND expected_revision=?"
            params.append(expected_revision)
        rows = self.db.execute(query, params).fetchall()
        rows = [
            row for row in rows
            if row["id"] != active_id
            and self._request_intent_matches(action, json.loads(row["payload_json"]), intent)
        ]
        rows = list(active_rows) + rows
        timestamp = now_text()
        decision_reason = str(decision_reason or "").strip() or None
        for row in rows:
            cursor = self.db.execute(
                """UPDATE owner_action_requests
                   SET status='approved', decided_by=?, decided_at=?, decision_reason=?
                   WHERE id=? AND status='pending'""",
                (actor["id"], timestamp, decision_reason, row["id"]),
            )
            if cursor.rowcount != 1:
                continue
            detail = {"request_id": row["id"], "action": action, "status": "approved",
                      "request_reason": row["reason"]}
            if active_id and row["id"] != active_id:
                detail["approved_request_id"] = active_id
                detail["resolution"] = "same_intent_as_approved_request"
            if row["task_id"]:
                self._event(
                    row["task_id"], actor["id"], "protected_action_approved",
                    {"request_id": row["id"], "status": "pending"}, detail, decision_reason,
                )
            else:
                self._project_event(
                    row["project_id"], actor["id"], "protected_action_approved", detail, decision_reason,
                )

    def _assert_active_request_revision(self, task: dict, owner_decision: OwnerDecision | None) -> None:
        if owner_decision is None:
            return
        request_id = owner_decision.request_id
        row = self.db.execute(
            "SELECT task_id,payload_json FROM owner_action_requests WHERE id=? AND status='pending'",
            (request_id,),
        ).fetchone()
        if not row or row["task_id"] != task["id"]:
            raise Conflict("Owner-action request conflict: the pending request changed.")
        expected_revision = json.loads(row["payload_json"]).get("expected_revision")
        if expected_revision is not None and expected_revision != task["revision"]:
            raise Conflict(
                f"Task revision conflict: request expected {expected_revision}, "
                f"current revision is {task['revision']}."
            )

    def decide_owner_action_request(
        self, actor: dict, request_id: str, decision: str, reason: str = ""
    ) -> dict:
        request = self._owner_action_request(actor, request_id)
        if request["status"] != "pending":
            raise Conflict("Owner-action request conflict: this request has already been decided.")
        decision = str(decision or "").strip().lower()
        if decision not in {"approved", "rejected", "cancelled"}:
            raise ValueError("Decision must be approved, rejected, or cancelled.")
        reason = str(reason or "").strip()
        if decision in {"rejected", "cancelled"}:
            if not reason:
                raise ValueError(f"A reason is required when a request is {decision}.")
            timestamp = now_text()
            with transaction(self.db):
                cursor = self.db.execute(
                    """UPDATE owner_action_requests
                       SET status=?, decided_by=?, decided_at=?, decision_reason=?
                       WHERE id=? AND status='pending'""",
                    (decision, actor["id"], timestamp, reason, request_id),
                )
                if cursor.rowcount != 1:
                    raise Conflict("Owner-action request conflict: this request has already been decided.")
                detail = {"request_id": request_id, "action": request["action"], "status": decision}
                if request["task_id"]:
                    self._event(
                        request["task_id"], actor["id"], f"protected_action_{decision}",
                        {"request_id": request_id, "status": "pending"}, detail, reason,
                    )
                else:
                    self._project_event(
                        request["project_id"], actor["id"], f"protected_action_{decision}", detail, reason
                    )
            return {"request": self._owner_action_request(actor, request_id)}

        payload = request["payload"]
        if request["task_id"] and payload.get("expected_revision") is not None:
            task = self.get_task(actor, request["task_id"])
            if task["revision"] != payload["expected_revision"]:
                raise Conflict(
                    f"Task revision conflict: request expected {payload['expected_revision']}, "
                    f"current revision is {task['revision']}."
                )
        result = self._execute_owner_action_request(actor, request, payload, reason)
        decided = self._owner_action_request(actor, request_id)
        if decided["status"] != "approved":
            raise RuntimeError("Approved action completed without resolving its Owner request.")
        return {"request": decided, "result": result}

    def _execute_owner_action_request(self, actor: dict, request: dict, payload: dict, reason: str):
        action = request["action"]
        decision = OwnerDecision(request_id=request["id"], reason=reason)
        if action == "update_task_status":
            return self.update_task(actor, request["task_id"], {
                "status": payload["status"],
                "reason": payload.get("reason") or request["reason"],
                "expected_revision": payload["expected_revision"],
            }, owner_decision=decision)
        if action == "accept_submission":
            return self.accept_submission(
                actor, payload["submission_id"], payload.get("decision_note", ""), payload.get("checklist"),
                owner_decision=decision,
            )
        if action == "request_changes":
            return self.request_changes(
                actor, payload["submission_id"], payload.get("reason") or request["reason"],
                owner_decision=decision,
            )
        if action == "reopen_task":
            return self.reopen_task(
                actor, request["task_id"], payload.get("reason") or request["reason"], payload.get("new_due_date"),
                owner_decision=decision,
            )
        if action == "set_on_hold":
            return self.set_on_hold(
                actor, request["task_id"], payload.get("reason") or request["reason"],
                payload.get("checkpoint_date"), payload.get("owner_user_id"),
                owner_decision=decision,
            )
        if action == "approve_schedule_proposal":
            return self.approve_schedule_proposal(
                actor, payload["proposal_id"], payload.get("decision_reason") or reason,
                owner_decision=decision,
            )
        if action == "reject_schedule_proposal":
            return self.reject_schedule_proposal(
                actor, payload["proposal_id"], payload.get("reason") or request["reason"],
                owner_decision=decision,
            )
        if action == "close_project":
            return self.close_project(
                actor, request["project_id"], payload.get("note", ""), bool(payload.get("exceptional")),
                owner_decision=decision,
            )
        raise ValueError(f"Unsupported Owner action request: {action}.")

    def list_owner_action_requests(self, actor: dict, status: str | None = "pending") -> list[dict]:
        self.require_owner(actor)
        params: list[str] = []
        where = ""
        if status:
            if status not in {"pending", "approved", "rejected", "cancelled"}:
                raise ValueError("Invalid owner-action request status.")
            where = " WHERE r.status=?"
            params.append(status)
        rows = self.db.execute(
            f"""SELECT {OWNER_REQUEST_COLUMNS_R}, p.name project_name, t.title task_title, u.display_name requested_by_name
               FROM owner_action_requests r
               JOIN projects p ON p.id=r.project_id
               LEFT JOIN tasks t ON t.id=r.task_id
               JOIN users u ON u.id=r.requested_by"""
            + where + " ORDER BY r.requested_at DESC, r.id DESC",
            params,
        ).fetchall()
        result = []
        for row in rows:
            request = dict(row)
            request["payload"] = json.loads(request["payload_json"])
            result.append(request)
        return result

    def _may_submit(self, actor: dict, task) -> bool:
        """Project Manager (or Owner), the Task Owner, or a task collaborator. The caller
        has already established that the actor can view the task's project."""
        return bool(
            self.can_manage_project(actor, task["project_id"])
            or actor["id"] == task["owner_user_id"]
            or self.db.execute(
                "SELECT 1 FROM task_reviewers WHERE task_id=? AND user_id=? AND role='collaborator'",
                (task["id"], actor["id"]),
            ).fetchone()
        )

    def submit_task(self, actor: dict, task_id: str, note: str = "") -> dict:
        task = self.get_task(actor, task_id)
        if not self._may_submit(actor, task):
            raise Forbidden("You are not authorized to submit this task.")
        if task["status"] in UNSUBMITTABLE_STATUSES:
            raise ValueError(f"A {task['status']} task cannot be submitted; reopen it first if needed.")
        expected_revision = task["revision"]
        submission_id = new_id()
        timestamp = now_text()
        note = str(note).strip()
        with transaction(self.db):
            # Re-read under the write lock (03G8EH). The permission and status checks
            # above ran before BEGIN IMMEDIATE, so a concurrent submit, an Owner cancel
            # or acceptance, or a reassignment may have landed since; only a task still
            # at the revision those checks saw may be submitted. Removing a collaborator
            # or revoking project access does not bump the revision, so the permission
            # is evaluated again here too.
            current = self.db.execute(
                "SELECT id, project_id, owner_user_id, status, revision FROM tasks WHERE id=?", (task_id,)
            ).fetchone()
            if current is None or current["revision"] != expected_revision:
                raise Conflict("Submission conflict: the task changed before it could be submitted; reload it and try again.")
            if current["status"] in UNSUBMITTABLE_STATUSES:
                raise Conflict(f"Submission conflict: the task is now {current['status']}.")
            if not (self.can_view_project(actor, current["project_id"]) and self._may_submit(actor, current)):
                raise Conflict("Submission conflict: your access to this task changed before it could be submitted.")
            version = self.db.execute(
                "SELECT COALESCE(MAX(version),0) m FROM task_submissions WHERE task_id=?", (task_id,)
            ).fetchone()["m"] + 1
            blocked = sorted(UNSUBMITTABLE_STATUSES)
            cursor = self.db.execute(
                "UPDATE tasks SET status='submitted', updated_at=?, revision=revision+1"
                f" WHERE id=? AND revision=? AND status NOT IN ({','.join('?' * len(blocked))})",
                (timestamp, task_id, expected_revision, *blocked),
            )
            if cursor.rowcount != 1:
                raise Conflict("Submission conflict: the task changed before it could be submitted; reload it and try again.")
            self.db.execute(
                "INSERT INTO task_submissions(id,task_id,version,submitted_by,submitted_at,note,status)"
                " VALUES(?,?,?,?,?,?,'submitted')",
                (submission_id, task_id, version, actor["id"], timestamp, note),
            )
            self._event(task_id, actor["id"], "task_submitted", None,
                        {"submission_id": submission_id, "version": version, "note": note}, None)
        return self.get_submission(actor, submission_id)

    def accept_submission(self, actor: dict, submission_id: str, decision_note: str = "", checklist=None,
        *, owner_decision: OwnerDecision | None = None,
    ) -> dict:
        submission = self.get_submission(actor, submission_id)
        task = self.get_task(actor, submission["task_id"])
        if submission["status"] != "submitted":
            raise ValueError("Only a pending submission can be accepted.")
        if actor["global_role"] != "owner":
            return self._request_protected_action(
                actor,
                task,
                "accept_submission",
                {"submission_id": submission_id, "decision_note": str(decision_note or "").strip(),
                 "checklist": checklist},
                str(decision_note or "").strip(),
            )
        timestamp = now_text()
        decision_note = str(decision_note).strip()
        checklist_text = json.dumps(checklist, default=str, sort_keys=True) if checklist else None
        expected_task_revision = task["revision"]
        with transaction(self.db):
            # Re-read after the write lock is held. Two Owner requests may both have
            # observed "submitted" before entering this transaction; only the first
            # may decide it and emit the acceptance event.
            submission = self.get_submission(actor, submission_id)
            task = self.get_task(actor, submission["task_id"])
            if task["revision"] != expected_task_revision:
                raise Conflict("Submission decision conflict: the task changed before acceptance began.")
            self._assert_active_request_revision(task, owner_decision)
            if submission["status"] != "submitted" or task["status"] != "submitted":
                raise Conflict("Submission decision conflict: this submission is no longer pending.")
            cursor = self.db.execute(
                "UPDATE task_submissions SET status='accepted', decided_by=?, decided_at=?, decision_note=?, checklist=?"
                " WHERE id=? AND status='submitted'",
                (actor["id"], timestamp, decision_note, checklist_text, submission_id),
            )
            if cursor.rowcount != 1:
                raise Conflict("Submission decision conflict: this submission is no longer pending.")
            cursor = self.db.execute(
                "UPDATE tasks SET status='completed', accepted_submission_id=?, updated_at=?, revision=revision+1"
                " WHERE id=? AND status='submitted' AND revision=?",
                (submission_id, timestamp, task["id"], task["revision"]),
            )
            if cursor.rowcount != 1:
                raise Conflict("Submission decision conflict: the task changed before acceptance was saved.")
            self._event(task["id"], actor["id"], "submission_accepted", {"status": task["status"]},
                        {"submission_id": submission_id, "version": submission["version"], "status": "completed"},
                        decision_note or None)
            self._resolve_pending_requests(
                actor,
                "accept_submission",
                project_id=task["project_id"],
                intent={"submission_id": submission_id},
                task_id=task["id"],
                expected_revision=task["revision"],
                decision_reason=decision_note,
                owner_decision=owner_decision,
            )
            # CS93C6 (owner decision 2026-09-15): acceptance does NOT auto-add the
            # submission to the final-results repository. Every final result is an
            # explicit manual mark (see mark_final_result) — an accepted submission
            # becomes eligible to be marked, but is not recorded automatically.
        return self.get_submission(actor, submission_id)

    def request_changes(self, actor: dict, submission_id: str, reason: str,
        *, owner_decision: OwnerDecision | None = None,
    ) -> dict:
        submission = self.get_submission(actor, submission_id)
        task = self.get_task(actor, submission["task_id"])
        if submission["status"] != "submitted":
            raise ValueError("Only a pending submission can be returned for changes.")
        reason = str(reason).strip()
        if not reason:
            raise ValueError("A reason is required to request changes.")
        if actor["global_role"] != "owner":
            return self._request_protected_action(
                actor, task, "request_changes", {"submission_id": submission_id, "reason": reason}, reason
            )
        timestamp = now_text()
        expected_task_revision = task["revision"]
        with transaction(self.db):
            submission = self.get_submission(actor, submission_id)
            task = self.get_task(actor, submission["task_id"])
            if task["revision"] != expected_task_revision:
                raise Conflict("Submission decision conflict: the task changed before the decision began.")
            self._assert_active_request_revision(task, owner_decision)
            if submission["status"] != "submitted" or task["status"] != "submitted":
                raise Conflict("Submission decision conflict: this submission is no longer pending.")
            cursor = self.db.execute(
                "UPDATE task_submissions SET status='changes_requested', decided_by=?, decided_at=?, decision_note=?"
                " WHERE id=? AND status='submitted'",
                (actor["id"], timestamp, reason, submission_id),
            )
            if cursor.rowcount != 1:
                raise Conflict("Submission decision conflict: this submission is no longer pending.")
            cursor = self.db.execute(
                "UPDATE tasks SET status='changes_requested', updated_at=?, revision=revision+1"
                " WHERE id=? AND status='submitted' AND revision=?",
                (timestamp, task["id"], task["revision"]),
            )
            if cursor.rowcount != 1:
                raise Conflict("Submission decision conflict: the task changed before the decision was saved.")
            self._event(task["id"], actor["id"], "changes_requested", None,
                        {"submission_id": submission_id, "version": submission["version"]}, reason)
            self._resolve_pending_requests(
                actor,
                "request_changes",
                project_id=task["project_id"],
                intent={"submission_id": submission_id},
                task_id=task["id"],
                expected_revision=task["revision"],
                decision_reason=reason,
                owner_decision=owner_decision,
            )
        return self.get_submission(actor, submission_id)

    def reopen_task(self, actor: dict, task_id: str, reason: str, new_due_date,
        *, owner_decision: OwnerDecision | None = None,
    ) -> dict:
        task = self.get_task(actor, task_id)
        if task["status"] not in {"completed", "cancelled", "abandoned"}:
            raise ValueError("Only a completed, cancelled, or abandoned task can be reopened.")
        reason = str(reason).strip()
        if not reason:
            raise ValueError("A reason is required to reopen a task.")
        new_due = self._date(new_due_date)
        if not new_due:
            raise ValueError("A revised timeline (new due date) is required to reopen a task.")
        if actor["global_role"] != "owner":
            return self._request_protected_action(
                actor, task, "reopen_task", {"reason": reason, "new_due_date": new_due}, reason
            )
        timestamp = now_text()
        before = {"status": task["status"], "due_date": task.get("due_date")}
        with transaction(self.db):
            current = self.get_task(actor, task_id)
            if current["revision"] != task["revision"]:
                raise Conflict("Task revision conflict: the task changed before reopening began.")
            self._assert_active_request_revision(current, owner_decision)
            # accepted_submission_id is retained so the prior accepted version stays visible.
            cursor = self.db.execute(
                "UPDATE tasks SET status='reopened', due_date=?, updated_at=?, revision=revision+1"
                " WHERE id=? AND revision=? AND status IN ('completed','cancelled','abandoned')",
                (new_due, timestamp, task_id, current["revision"]),
            )
            if cursor.rowcount != 1:
                raise Conflict("Task revision conflict: the task changed before it could be reopened.")
            self._event(task_id, actor["id"], "task_reopened", before,
                        {"status": "reopened", "due_date": new_due}, reason)
            self._resolve_pending_requests(
                actor,
                "reopen_task",
                project_id=task["project_id"],
                intent={"new_due_date": new_due},
                task_id=task_id,
                expected_revision=task["revision"],
                decision_reason=reason,
                owner_decision=owner_decision,
            )
            # A Manager may have attempted to move a terminal task back into work
            # through the generic editor. That creates an update_task_status request,
            # but the Owner must still use this dedicated reopen path so a revised
            # timeline is recorded. A proper direct reopen therefore supersedes that
            # matching request as well as an explicit reopen_task request.
            self._resolve_pending_requests(
                actor,
                "update_task_status",
                project_id=task["project_id"],
                intent={"status": REOPEN_EQUIVALENT_STATUSES, "from_status": current["status"]},
                task_id=task_id,
                expected_revision=task["revision"],
                decision_reason=reason,
                owner_decision=owner_decision,
            )
        return self.get_task(actor, task_id)

    def set_on_hold(self, actor: dict, task_id: str, reason: str, checkpoint_date, hold_owner_id=None,
        *, owner_decision: OwnerDecision | None = None,
    ) -> dict:
        task = self.get_task(actor, task_id)
        if task["status"] in REOPEN_ONLY_STATUSES:
            raise ValueError(f"A {task['status']} task must be reopened before it can be put on hold.")
        reason = str(reason).strip()
        if not reason:
            raise ValueError("On-hold work requires a reason.")
        checkpoint = self._date(checkpoint_date)
        if not checkpoint:
            raise ValueError("On-hold work requires a mandatory follow-up checkpoint date.")
        hold_owner = self._validate_assignee(task["project_id"], hold_owner_id or task.get("owner_user_id"))
        if not hold_owner:
            raise ValueError("On-hold work requires a responsible owner.")
        if actor["global_role"] != "owner":
            return self._request_protected_action(
                actor,
                task,
                "set_on_hold",
                {"reason": reason, "checkpoint_date": checkpoint, "owner_user_id": hold_owner},
                reason,
            )
        timestamp = now_text()
        with transaction(self.db):
            current = self.get_task(actor, task_id)
            if current["revision"] != task["revision"]:
                raise Conflict("Task revision conflict: the task changed before the hold began.")
            self._assert_active_request_revision(current, owner_decision)
            if current["status"] in REOPEN_ONLY_STATUSES:
                raise Conflict(f"A {current['status']} task must be reopened before it can be put on hold.")
            cursor = self.db.execute(
                "UPDATE tasks SET status='on_hold', owner_user_id=?, updated_at=?, revision=revision+1"
                " WHERE id=? AND revision=?",
                (hold_owner, timestamp, task_id, current["revision"]),
            )
            if cursor.rowcount != 1:
                raise Conflict("Task revision conflict: the task changed before it could be put on hold.")
            self.db.execute(
                "INSERT INTO task_checkpoints(id,task_id,checkpoint_date,reason,owner_user_id,created_by,created_at)"
                " VALUES(?,?,?,?,?,?,?)",
                (new_id(), task_id, checkpoint, reason, hold_owner, actor["id"], timestamp),
            )
            self._event(task_id, actor["id"], "task_on_hold", {"status": task["status"]},
                        {"status": "on_hold", "checkpoint_date": checkpoint, "owner_user_id": hold_owner}, reason)
            self._resolve_pending_requests(
                actor,
                "set_on_hold",
                project_id=task["project_id"],
                intent={"checkpoint_date": checkpoint, "owner_user_id": hold_owner},
                task_id=task_id,
                expected_revision=task["revision"],
                decision_reason=reason,
                owner_decision=owner_decision,
            )
        return self.get_task(actor, task_id)

    def list_subtasks(self, actor: dict, task_id: str) -> list[dict]:
        # D73AQW: the Gantt step segments, their tooltip and the detail dialog's
        # Subtasks list share this one read shape, so it carries the schedule and
        # ownership fields as well as the roll-up basics. Read-only; no schema change.
        self.get_task(actor, task_id)
        rows = self.db.execute(
            """SELECT t.id, t.title, t.status, t.start_date, t.due_date, t.criticality, t.progress,
                      t.parent_task_id, t.owner_user_id, u.display_name owner_name
               FROM tasks t LEFT JOIN users u ON u.id=t.owner_user_id
               WHERE t.parent_task_id=? ORDER BY t.title COLLATE NOCASE""",
            (task_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _task_ancestors(self, task_id: str) -> set:
        ancestors, current = set(), task_id
        while True:
            row = self.db.execute("SELECT parent_task_id FROM tasks WHERE id=?", (current,)).fetchone()
            parent = row["parent_task_id"] if row else None
            if not parent or parent in ancestors:
                break
            ancestors.add(parent)
            current = parent
        return ancestors

    def set_parent(self, actor: dict, task_id: str, parent_task_id) -> dict:
        task = self.get_task(actor, task_id)
        if not self.can_manage_project(actor, task["project_id"]):
            raise Forbidden("Task-management access denied.")
        self._refuse_closed(task)
        parent_task_id = parent_task_id or None
        if parent_task_id:
            if parent_task_id == task_id:
                raise ValueError("A task cannot be its own parent.")
            parent = self.get_task(actor, parent_task_id)
            if parent["project_id"] != task["project_id"]:
                raise ValueError("A parent task must belong to the same project.")
            # Reject if the proposed parent is a descendant of this task (would form a cycle).
            if task_id in self._task_ancestors(parent_task_id):
                raise ValueError("That parent would create a subtask cycle.")
        timestamp = now_text()
        before = {"parent_task_id": task.get("parent_task_id")}
        with transaction(self.db):
            self._refuse_closed_in_transaction(task_id)
            self.db.execute(
                "UPDATE tasks SET parent_task_id=?, updated_at=?, revision=revision+1 WHERE id=?",
                (parent_task_id, timestamp, task_id),
            )
            self._event(task_id, actor["id"], "parent_changed", before, {"parent_task_id": parent_task_id}, None)
        return self.get_task(actor, task_id)

    def confirm_criticality(self, actor: dict, task_id: str, criticality, reason: str) -> dict:
        task = self.get_task(actor, task_id)
        if not self.can_manage_project(actor, task["project_id"]):
            raise Forbidden("Task-management access denied.")
        self._refuse_closed(task)
        criticality = criticality or None
        if criticality not in CRITICALITIES:
            raise ValueError("Invalid criticality.")
        reason = str(reason).strip()
        if not reason:
            raise ValueError("A reason is required to confirm criticality.")
        old = task.get("criticality") or None
        if old == criticality:
            raise ValueError("Criticality is already set to that level.")
        timestamp = now_text()
        with transaction(self.db):
            self._refuse_closed_in_transaction(task_id)
            self.db.execute(
                "UPDATE tasks SET criticality=?, updated_at=?, revision=revision+1 WHERE id=?",
                (criticality, timestamp, task_id),
            )
            self._event(task_id, actor["id"], "criticality_changed",
                        {"criticality": old}, {"criticality": criticality}, reason)
        return self.get_task(actor, task_id)

    def add_task_reviewer(self, actor: dict, task_id: str, user_id: str, role: str) -> None:
        task = self.get_task(actor, task_id)
        if not self.can_manage_project(actor, task["project_id"]):
            raise Forbidden("Task-management access denied.")
        self._refuse_closed(task)  # review SVC-1: people are not evidence
        if role not in REVIEWER_ROLES:
            raise ValueError("Invalid reviewer role.")
        if not user_id:
            raise ValueError("A user is required.")
        self._validate_assignee(task["project_id"], user_id)
        with transaction(self.db):
            self._refuse_closed_in_transaction(task_id)
            self.db.execute(
                "INSERT OR IGNORE INTO task_reviewers VALUES(?,?,?,?,?)",
                (task_id, user_id, role, now_text(), actor["id"]),
            )

    def remove_task_reviewer(self, actor: dict, task_id: str, user_id: str, role: str) -> None:
        task = self.get_task(actor, task_id)
        if not self.can_manage_project(actor, task["project_id"]):
            raise Forbidden("Task-management access denied.")
        self._refuse_closed(task)
        with transaction(self.db):
            self._refuse_closed_in_transaction(task_id)
            self.db.execute(
                "DELETE FROM task_reviewers WHERE task_id=? AND user_id=? AND role=?", (task_id, user_id, role)
            )

    def list_task_reviewers(self, actor: dict, task_id: str) -> list[dict]:
        self.get_task(actor, task_id)
        rows = self.db.execute(
            """SELECT r.user_id, r.role, u.display_name FROM task_reviewers r JOIN users u ON u.id=r.user_id
               WHERE r.task_id=? ORDER BY r.role, u.display_name COLLATE NOCASE""",
            (task_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    # --- Attachments: links to files that live in a folder outside Astra ---
    #
    # Astra deliberately stores no bytes. An attachment is a LINK — a local
    # filesystem path plus its metadata. Deleting one removes the link record,
    # never the file on disk. The task's own authorization gates the link
    # record (who can see it in-app); it cannot gate the file on disk.

    def add_task_attachment(self, actor: dict, task_id: str, path: str, display_name: str = "", note: str = "") -> dict:
        task = self.get_task(actor, task_id)
        if actor["global_role"] != "owner":
            self._event(
                task_id, actor["id"], "attachment_add_blocked", None,
                {"attempted_path": str(path or "").strip()}, "Owner-only file management",
            )
            raise Forbidden("Owner access required for file management.")
        path = str(path or "").strip()
        if not path:
            raise ValueError("A file path is required.")
        display_name = str(display_name or "").strip() or os.path.basename(path.rstrip("/\\")) or path
        attachment_id = new_id()
        with transaction(self.db):
            self.db.execute(
                "INSERT INTO task_attachments(id,task_id,path,display_name,note,added_by,added_at)"
                " VALUES(?,?,?,?,?,?,?)",
                (attachment_id, task_id, path, display_name, str(note or "").strip(), actor["id"], now_text()),
            )
            self._event(task_id, actor["id"], "attachment_added", None,
                        {"path": path, "display_name": display_name}, None)
        return self._get_attachment(task_id, attachment_id)

    def list_task_attachments(self, actor: dict, task_id: str) -> list[dict]:
        # get_task enforces the same view authorization the whole task has.
        self.get_task(actor, task_id)
        rows = self.db.execute(
            """SELECT a.*, u.display_name added_by_name FROM task_attachments a
               LEFT JOIN users u ON u.id=a.added_by WHERE a.task_id=? ORDER BY a.added_at, a.id""",
            (task_id,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["exists"] = self._path_exists(item["path"])
            result.append(item)
        return result

    def remove_task_attachment(self, actor: dict, task_id: str, attachment_id: str) -> None:
        task = self.get_task(actor, task_id)  # validates existence and visibility first
        row = self.db.execute(
            "SELECT path, display_name FROM task_attachments WHERE id=? AND task_id=?",
            (attachment_id, task_id),
        ).fetchone()
        if not row:
            raise KeyError("Attachment not found.")
        if actor["global_role"] != "owner":
            self._event(
                task["id"], actor["id"], "attachment_removal_blocked", None,
                {"attachment_id": attachment_id, "display_name": row["display_name"]},
                "Owner-only file management",
            )
            raise Forbidden("Owner access required for file management.")
        with transaction(self.db):
            self.db.execute("DELETE FROM task_attachments WHERE id=? AND task_id=?", (attachment_id, task_id))
            # Removing the link never touches the file on disk.
            self._event(task_id, actor["id"], "attachment_removed",
                        {"path": row["path"], "display_name": row["display_name"]}, None, None)

    def _get_attachment(self, task_id: str, attachment_id: str) -> dict:
        row = row_dict(self.db.execute(
            """SELECT a.*, u.display_name added_by_name FROM task_attachments a
               LEFT JOIN users u ON u.id=a.added_by WHERE a.id=? AND a.task_id=?""",
            (attachment_id, task_id),
        ).fetchone())
        if not row:
            raise KeyError("Attachment not found.")
        row["exists"] = self._path_exists(row["path"])
        return row

    @staticmethod
    def _path_exists(path: str) -> bool:
        # Best-effort: a linked file can be moved or renamed outside Astra, so
        # this flags dead links in the UI. Never fatal if the check itself fails.
        try:
            return os.path.exists(path)
        except (OSError, ValueError):
            return False

    # --- Templates: reusable STRUCTURE snapshots (never evidence or history) ---
    #
    # A template captures the shape of recurring work — task titles, hierarchy,
    # criticality, dependencies, attachment links, a SUGGESTED owner (by name),
    # and dates as day OFFSETS from an anchor — as a JSON snapshot. It deliberately
    # omits everything that is evidence or history: live status/progress, revisions,
    # baselines, events, submissions, checkpoints, schedule proposals and
    # notifications. Instantiating one re-applies the offsets to a fresh anchor
    # date, starts every task in 'draft', and pre-fills each suggested owner when
    # they are still an assignable project member (otherwise unassigned). Owner-only.

    @staticmethod
    def _compute_anchor(rows: list[dict]) -> str | None:
        dates = [r[key] for r in rows for key in ("start_date", "due_date") if r[key]]
        return min(dates) if dates else None  # ISO dates compare chronologically

    @staticmethod
    def _offset(date_str: str | None, anchor: str | None):
        if not date_str or not anchor:
            return None
        return (date.fromisoformat(date_str) - date.fromisoformat(anchor)).days

    @staticmethod
    def _apply_offset(anchor_date: str | None, offset):
        if anchor_date is None or offset is None:
            return None
        return (date.fromisoformat(anchor_date) + timedelta(days=int(offset))).isoformat()

    def _subtree_rows(self, root_id: str) -> list[dict]:
        collected: dict[str, dict] = {}
        frontier = [root_id]
        while frontier:
            current = frontier.pop()
            if current in collected:
                continue
            row = row_dict(self.db.execute("SELECT * FROM tasks WHERE id=?", (current,)).fetchone())
            if not row:
                continue
            collected[current] = row
            children = self.db.execute("SELECT id FROM tasks WHERE parent_task_id=?", (current,)).fetchall()
            frontier.extend(child["id"] for child in children)
        return list(collected.values())

    def _snapshot_tasks(self, rows: list[dict]) -> dict:
        rows = sorted(rows, key=lambda r: (r["created_at"], r["id"]))
        anchor = self._compute_anchor(rows)
        local_of = {r["id"]: index for index, r in enumerate(rows)}
        tasks = []
        for row in rows:
            parent = row["parent_task_id"]
            attachments = [dict(a) for a in self.db.execute(
                "SELECT path, display_name, note FROM task_attachments WHERE task_id=? ORDER BY added_at, id",
                (row["id"],),
            ).fetchall()]
            # 8B9NBH (owner decision 2026-09-15): carry a SUGGESTED owner — the
            # display name of who held the task last cycle — so instantiation can
            # pre-fill them instead of always leaving the task unassigned. It is a
            # hint only (resolved by name at instantiation), never a stored user id.
            suggested_owner = None
            if row["owner_user_id"]:
                owner_row = self.db.execute(
                    "SELECT display_name FROM users WHERE id=?", (row["owner_user_id"],)
                ).fetchone()
                if owner_row:
                    suggested_owner = owner_row["display_name"]
            tasks.append({
                "local_id": local_of[row["id"]],
                "title": row["title"],
                "description": row["description"],
                "criticality": row["criticality"],
                "start_offset": self._offset(row["start_date"], anchor),
                "due_offset": self._offset(row["due_date"], anchor),
                "parent_local_id": local_of.get(parent) if parent in local_of else None,
                "suggested_owner": suggested_owner,
                "attachments": attachments,
            })
        ids = set(local_of)
        dependencies = []
        for dep in self.db.execute(
            "SELECT predecessor_task_id, successor_task_id FROM task_dependencies"
        ).fetchall():
            if dep["predecessor_task_id"] in ids and dep["successor_task_id"] in ids:
                dependencies.append({
                    "predecessor_local_id": local_of[dep["predecessor_task_id"]],
                    "successor_local_id": local_of[dep["successor_task_id"]],
                })
        return {"anchor": anchor, "tasks": tasks, "dependencies": dependencies}

    def _store_template(self, actor: dict, kind: str, name: str, description: str, body: dict) -> dict:
        name = str(name or "").strip()
        if not name:
            raise ValueError("A template name is required.")
        template_id = new_id()
        self.db.execute(
            "INSERT INTO templates(id,kind,name,description,body_json,created_by,created_at) VALUES(?,?,?,?,?,?,?)",
            (template_id, kind, name, str(description or "").strip(),
             json.dumps(body, default=str, sort_keys=True), actor["id"], now_text()),
        )
        return self.get_template(actor, template_id)

    def save_project_as_template(self, actor: dict, project_id: str, name: str, description: str = "") -> dict:
        self.require_owner(actor)
        project = self.get_project(actor, project_id)
        rows = [dict(r) for r in self.db.execute(
            "SELECT * FROM tasks WHERE project_id=?", (project_id,)
        ).fetchall()]
        body = self._snapshot_tasks(rows)
        body["kind"] = "project"
        body["project"] = {
            "description": project.get("description", ""),
            "timezone": project.get("timezone", "Asia/Karachi"),
            "working_days": project.get("working_days", "0123456"),
        }
        return self._store_template(actor, "project", name, description, body)

    def save_task_as_template(self, actor: dict, task_id: str, name: str, description: str = "") -> dict:
        self.require_owner(actor)
        self.get_task(actor, task_id)  # existence + view (owner sees all)
        rows = self._subtree_rows(task_id)
        body = self._snapshot_tasks(rows)
        body["kind"] = "task"
        body["project"] = None
        return self._store_template(actor, "task", name, description, body)

    def list_templates(self, actor: dict, kind: str | None = None) -> list[dict]:
        self.require_owner(actor)
        query = ("SELECT t.id,t.kind,t.name,t.description,t.body_json,t.created_at,u.display_name created_by_name"
                 " FROM templates t LEFT JOIN users u ON u.id=t.created_by")
        params: list = []
        if kind:
            query += " WHERE t.kind=?"
            params.append(kind)
        query += " ORDER BY t.name COLLATE NOCASE"
        result = []
        for row in self.db.execute(query, params).fetchall():
            item = dict(row)
            body = json.loads(item.pop("body_json"))
            item["task_count"] = len(body.get("tasks", []))
            result.append(item)
        return result

    def get_template(self, actor: dict, template_id: str) -> dict:
        self.require_owner(actor)
        row = row_dict(self.db.execute(
            "SELECT t.*, u.display_name created_by_name FROM templates t LEFT JOIN users u ON u.id=t.created_by"
            " WHERE t.id=?", (template_id,),
        ).fetchone())
        if not row:
            raise KeyError("Template not found.")
        row["body"] = json.loads(row.pop("body_json"))
        return row

    def delete_template(self, actor: dict, template_id: str) -> None:
        self.require_owner(actor)
        if not self.db.execute("SELECT 1 FROM templates WHERE id=?", (template_id,)).fetchone():
            raise KeyError("Template not found.")
        self.db.execute("DELETE FROM templates WHERE id=?", (template_id,))

    def _resolve_suggested_owner(self, project_id: str, name: str | None) -> str | None:
        """Map a template's suggested-owner display name to a currently assignable
        user for this project. Returns None when the name is missing, unknown,
        ambiguous, inactive, or not permitted on the project — the task then
        instantiates unassigned (8B9NBH)."""
        if not name:
            return None
        rows = self.db.execute(
            "SELECT id FROM users WHERE display_name=? AND active=1", (name,)
        ).fetchall()
        if len(rows) != 1:  # unknown or ambiguous -> no pre-fill
            return None
        try:
            return self._validate_assignee(project_id, rows[0]["id"])
        except (ValueError, Forbidden):
            return None

    def _instantiate_tasks(self, actor: dict, body: dict, project_id: str,
                           root_parent_id: str | None, anchor_date: str | None, source_name: str) -> None:
        tasks = body.get("tasks", [])
        timestamp = now_text()
        id_of: dict[int, str] = {}
        for task in tasks:  # pass 1 — insert every row, parents wired in pass 2
            new_task_id = new_id()
            id_of[task["local_id"]] = new_task_id
            start_date = self._apply_offset(anchor_date, task.get("start_offset"))
            due_date = self._apply_offset(anchor_date, task.get("due_offset"))
            # Pre-fill the suggested owner when they are still an assignable member;
            # otherwise leave it unassigned.
            owner_user_id = self._resolve_suggested_owner(project_id, task.get("suggested_owner"))
            self.db.execute(
                """INSERT INTO tasks(id,project_id,parent_task_id,title,description,owner_user_id,status,criticality,
                   start_date,due_date,progress,created_at,created_by,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (new_task_id, project_id, None, task["title"], task.get("description", ""),
                 owner_user_id, "draft", task.get("criticality"), start_date, due_date, None,
                 timestamp, actor["id"], timestamp),
            )
        for task in tasks:  # pass 2 — hierarchy, baseline, creation event
            new_task_id = id_of[task["local_id"]]
            parent_local = task.get("parent_local_id")
            if parent_local is not None:
                parent_id = id_of.get(parent_local)
            else:
                parent_id = root_parent_id
            if parent_id:
                self.db.execute("UPDATE tasks SET parent_task_id=? WHERE id=?", (parent_id, new_task_id))
            self._ensure_baseline(new_task_id)
            self._event(new_task_id, actor["id"], "task_created", None,
                        {"title": task["title"], "from_template": source_name}, None)
        for dep in body.get("dependencies", []):
            pred = id_of.get(dep.get("predecessor_local_id"))
            succ = id_of.get(dep.get("successor_local_id"))
            if pred and succ:
                self.db.execute(
                    "INSERT OR IGNORE INTO task_dependencies VALUES(?,?,?)", (pred, succ, "finish_to_start")
                )
        for task in tasks:  # attachment links copied last
            new_task_id = id_of[task["local_id"]]
            for attachment in task.get("attachments", []):
                self.db.execute(
                    "INSERT INTO task_attachments(id,task_id,path,display_name,note,added_by,added_at)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (new_id(), new_task_id, attachment["path"], attachment["display_name"],
                     attachment.get("note", ""), actor["id"], timestamp),
                )

    def create_project_from_template(self, actor: dict, template_id: str, name: str, anchor_date=None) -> dict:
        self.require_owner(actor)
        template = self.get_template(actor, template_id)
        if template["kind"] != "project":
            raise ValueError("This template does not create a project.")
        name = str(name or "").strip()
        if not name:
            raise ValueError("A project name is required.")
        anchor_date = self._date(anchor_date)
        body = template["body"]
        meta = body.get("project") or {}
        with transaction(self.db):
            project_id = new_id()
            self.db.execute(
                "INSERT INTO projects(id,name,description,timezone,working_days,created_at,created_by)"
                " VALUES(?,?,?,?,?,?,?)",
                (project_id, name, meta.get("description", ""), meta.get("timezone", "Asia/Karachi"),
                 meta.get("working_days", "0123456"), now_text(), actor["id"]),
            )
            self._instantiate_tasks(actor, body, project_id, None, anchor_date, template["name"])
        return self.get_project(actor, project_id)

    def create_task_from_template(self, actor: dict, template_id: str, project_id: str,
                                  parent_task_id=None, anchor_date=None) -> dict:
        self.require_owner(actor)
        template = self.get_template(actor, template_id)
        if template["kind"] != "task":
            raise ValueError("This template does not create a task.")
        self._require_project(project_id)
        parent_task_id = parent_task_id or None
        if parent_task_id:
            parent = self.get_task(actor, parent_task_id)
            if parent["project_id"] != project_id:
                raise ValueError("A parent task must belong to the same project.")
        anchor_date = self._date(anchor_date)
        body = template["body"]
        with transaction(self.db):
            self._instantiate_tasks(actor, body, project_id, parent_task_id, anchor_date, template["name"])
        return {"project_id": project_id, "created": len(body.get("tasks", []))}

    # --- Final results: a searchable index of accepted deliverables ---
    #
    # Every final result is an explicit manual mark (CS93C6): an accepted
    # submission or an attachment link is marked by hand — nothing is recorded
    # automatically on acceptance. The repository is scoped exactly like the task
    # board: owner/chairman see all, everyone else only their own projects.

    def mark_final_result(self, actor: dict, task_id: str, source_type: str, source_id: str, note: str = "") -> dict:
        task = self.get_task(actor, task_id)
        if actor["global_role"] != "owner":
            self._event(
                task_id, actor["id"], "final_result_mark_blocked", None,
                {"source_type": source_type, "source_id": source_id},
                "Owner-only final-result publication",
            )
            raise Forbidden("Owner access required for final-result publication.")
        if source_type not in {"submission", "attachment"}:
            raise ValueError("A final result is a submission or an attachment.")
        note = str(note or "").strip()
        timestamp = now_text()
        result_id = new_id()
        if source_type == "submission":
            submission = self.db.execute(
                "SELECT version, status FROM task_submissions WHERE id=? AND task_id=?", (source_id, task_id)
            ).fetchone()
            if not submission:
                raise KeyError("Submission not found on this task.")
            if submission["status"] != "accepted":
                raise ValueError("Only an accepted submission can be a final result.")
            title = f"{task['title']} (v{submission['version']})"
            columns, values = ("submission_id",), (source_id,)
        else:
            attachment = self.db.execute(
                "SELECT display_name FROM task_attachments WHERE id=? AND task_id=?", (source_id, task_id)
            ).fetchone()
            if not attachment:
                raise KeyError("Attachment not found on this task.")
            title = attachment["display_name"]
            columns, values = ("attachment_id",), (source_id,)
        with transaction(self.db):
            cursor = self.db.execute(
                f"INSERT OR IGNORE INTO final_results(id,task_id,source_type,{columns[0]},title,note,marked_by,marked_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (result_id, task_id, source_type, values[0], title, note, actor["id"], timestamp),
            )
            if cursor.rowcount == 1:
                self._event(task_id, actor["id"], "final_result_marked", None,
                            {"source_type": source_type, "title": title}, note or None)
        return self._get_final_result_for_source(task_id, source_type, source_id)

    def unmark_final_result(self, actor: dict, result_id: str) -> None:
        row = self.db.execute(
            "SELECT fr.task_id, fr.title, t.project_id FROM final_results fr JOIN tasks t ON t.id=fr.task_id"
            " WHERE fr.id=?", (result_id,)
        ).fetchone()
        if not row:
            raise KeyError("Final result not found.")
        self.get_task(actor, row["task_id"])
        if actor["global_role"] != "owner":
            self._event(
                row["task_id"], actor["id"], "final_result_unmark_blocked", None,
                {"result_id": result_id, "title": row["title"]},
                "Owner-only final-result publication",
            )
            raise Forbidden("Owner access required for final-result publication.")
        with transaction(self.db):
            cursor = self.db.execute("DELETE FROM final_results WHERE id=?", (result_id,))
            if cursor.rowcount != 1:
                raise KeyError("Final result not found.")
            self._event(row["task_id"], actor["id"], "final_result_unmarked", {"title": row["title"]}, None, None)

    def _get_final_result_for_source(self, task_id: str, source_type: str, source_id: str) -> dict:
        column = "submission_id" if source_type == "submission" else "attachment_id"
        row = row_dict(self.db.execute(
            f"SELECT * FROM final_results WHERE task_id=? AND {column}=?", (task_id, source_id)
        ).fetchone())
        if not row:
            raise KeyError("Final result not found.")
        return row

    def list_final_results(self, actor: dict, filters: dict | None = None) -> list[dict]:
        filters = filters or {}
        clauses, params = [], []
        if actor["global_role"] not in {"owner", "chairman"}:
            clauses.append("EXISTS(SELECT 1 FROM memberships m WHERE m.project_id=t.project_id AND m.user_id=?)")
            params.append(actor["id"])
        if filters.get("project_id"):
            clauses.append("t.project_id=?")
            params.append(filters["project_id"])
        if filters.get("type") in {"submission", "attachment"}:
            clauses.append("fr.source_type=?")
            params.append(filters["type"])
        if filters.get("from"):
            clauses.append("fr.marked_at>=?")
            params.append(self._date(filters["from"]))
        if filters.get("to"):
            clauses.append("fr.marked_at<=?")
            params.append(self._date(filters["to"]) + "T23:59:59")
        if filters.get("entity_id"):
            clauses.append("EXISTS(SELECT 1 FROM project_entities pe WHERE pe.project_id=t.project_id AND pe.entity_id=?)")
            params.append(filters["entity_id"])
        if str(filters.get("q") or "").strip():
            like = f"%{filters['q'].strip()}%"
            clauses.append("(fr.title LIKE ? OR t.title LIKE ? OR p.name LIKE ?)")
            params.extend([like, like, like])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.db.execute(
            """SELECT fr.*, t.title task_title, t.project_id, p.name project_name,
                      u.display_name marked_by_name, a.path attachment_path, s.version submission_version
               FROM final_results fr JOIN tasks t ON t.id=fr.task_id JOIN projects p ON p.id=t.project_id
               LEFT JOIN users u ON u.id=fr.marked_by
               LEFT JOIN task_attachments a ON a.id=fr.attachment_id
               LEFT JOIN task_submissions s ON s.id=fr.submission_id"""
            + where + " ORDER BY fr.marked_at DESC, fr.id DESC",
            params,
        ).fetchall()
        result = [dict(row) for row in rows]
        return self._attach_entity_names(result)

    def _attach_entity_names(self, rows: list[dict]) -> list[dict]:
        for row in rows:
            entities = self.db.execute(
                """SELECT e.name FROM project_entities pe JOIN entities e ON e.id=pe.entity_id
                   WHERE pe.project_id=? ORDER BY e.name COLLATE NOCASE""",
                (row["project_id"],),
            ).fetchall()
            row["entities"] = [entity["name"] for entity in entities]
        return rows

    def export_final_results(self, actor: dict, filters: dict | None = None) -> dict:
        return {"as_of": now_text(), "filters": filters or {}, "results": self.list_final_results(actor, filters)}

    def list_task_final_results(self, actor: dict, task_id: str) -> list[dict]:
        self.get_task(actor, task_id)  # inherits the task's view authorization
        rows = self.db.execute(
            "SELECT id, source_type, submission_id, attachment_id, title FROM final_results WHERE task_id=?",
            (task_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def close_project(self, actor: dict, project_id: str, note: str = "", exceptional: bool = False,
        *, owner_decision: OwnerDecision | None = None,
    ) -> dict:
        project = self.get_project(actor, project_id)
        if project["status"] == "closed":
            raise ValueError("This project is already closed.")
        outstanding = [dict(row) for row in self.db.execute(
            "SELECT id,title,status FROM tasks WHERE project_id=? AND status NOT IN ('completed','cancelled','abandoned')"
            " ORDER BY title COLLATE NOCASE",
            (project_id,),
        ).fetchall()]
        note = str(note).strip()
        if actor["global_role"] != "owner":
            if outstanding and not note:
                raise ValueError("A closure request with outstanding work requires a note.")
            return self._request_protected_project_action(
                actor,
                project,
                "close_project",
                {"note": note, "exceptional": bool(outstanding), "residual_work": outstanding},
                note,
            )
        # An approval is re-checked against its request inside the transaction below.
        if outstanding and owner_decision is None:
            if not exceptional:
                raise ValueError("This project has outstanding work; an exceptional owner closure is required.")
            if not note:
                raise ValueError("Exceptional closure requires a note describing the residual work.")
        timestamp = now_text()
        with transaction(self.db):
            current = row_dict(self.db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
            if not current or current["status"] == "closed":
                raise Conflict("Project closure conflict: this project is already closed.")
            outstanding = [dict(row) for row in self.db.execute(
                "SELECT id,title,status FROM tasks WHERE project_id=?"
                " AND status NOT IN ('completed','cancelled','abandoned') ORDER BY title COLLATE NOCASE",
                (project_id,),
            ).fetchall()]
            if owner_decision is not None:
                request_id = owner_decision.request_id
                row = self.db.execute(
                    "SELECT project_id,action,payload_json FROM owner_action_requests WHERE id=? AND status='pending'",
                    (request_id,),
                ).fetchone()
                if not row or row["project_id"] != project_id or row["action"] != "close_project":
                    raise Conflict("Owner-action request conflict: the pending request changed.")
                requested = json.loads(row["payload_json"])
                if (
                    bool(requested.get("exceptional")) != bool(outstanding)
                    or not self._residual_work_matches(requested.get("residual_work"), outstanding)
                ):
                    raise Conflict(
                        "Project closure conflict: the project's open work changed since this close was "
                        "requested; review and decide again."
                    )
            if outstanding and not exceptional:
                raise Conflict("Project closure conflict: outstanding work now requires exceptional closure.")
            if outstanding and not note:
                raise Conflict("Project closure conflict: outstanding work now requires a closure note.")
            cursor = self.db.execute(
                "UPDATE projects SET status='closed', closed_at=?, closed_by=?, closure_note=?, closure_is_exceptional=?"
                " WHERE id=? AND status<>'closed'",
                (timestamp, actor["id"], note, 1 if outstanding else 0, project_id),
            )
            if cursor.rowcount != 1:
                raise Conflict("Project closure conflict: this project is already closed.")
            self._project_event(
                project_id, actor["id"], "project_closed",
                {"exceptional": bool(outstanding), "note": note, "residual_work": outstanding}, note or None,
            )
            self._resolve_pending_requests(
                actor,
                "close_project",
                project_id=project_id,
                intent={"note": note, "exceptional": bool(outstanding), "residual_work": outstanding},
                decision_reason=note,
                owner_decision=owner_decision,
            )
        return self.get_project(actor, project_id)

    def project_events(self, actor: dict, project_id: str) -> list[dict]:
        self.get_project(actor, project_id)
        rows = self.db.execute(
            """SELECT e.*, u.display_name actor_name FROM project_events e
               LEFT JOIN users u ON u.id=e.actor_user_id WHERE e.project_id=? ORDER BY e.occurred_at,e.id""",
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _project_event(self, project_id: str, actor_id: str, kind: str, detail: dict | None, reason: str | None) -> None:
        self.db.execute(
            "INSERT INTO project_events VALUES(?,?,?,?,?,?,?)",
            (new_id(), project_id, kind, actor_id, now_text(), reason,
             json.dumps(detail, default=str, sort_keys=True) if detail is not None else None),
        )

    # --- Schedule revisions: baseline / current / pending ---

    def _ensure_baseline(self, task_id: str) -> None:
        # The baseline is the ORIGINAL schedule — captured the first time a task has any
        # start/due date, and never silently overwritten afterwards.
        self.db.execute(
            "UPDATE tasks SET baseline_start_date=start_date, baseline_due_date=due_date"
            " WHERE id=? AND baseline_start_date IS NULL AND baseline_due_date IS NULL"
            " AND (start_date IS NOT NULL OR due_date IS NOT NULL)",
            (task_id,),
        )

    def _impacted_successors(self, task_id: str) -> list[dict]:
        rows = self.db.execute(
            """SELECT s.id, s.title FROM task_dependencies d JOIN tasks s ON s.id=d.successor_task_id
               WHERE d.predecessor_task_id=? AND s.status NOT IN ('completed','cancelled','abandoned')
               ORDER BY s.title COLLATE NOCASE""",
            (task_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_schedule_proposal(self, actor: dict, proposal_id: str) -> dict:
        row = row_dict(self.db.execute(
            """SELECT p.*, t.project_id, pb.display_name proposed_by_name, db.display_name decided_by_name
               FROM task_schedule_proposals p JOIN tasks t ON t.id=p.task_id
               LEFT JOIN users pb ON pb.id=p.proposed_by LEFT JOIN users db ON db.id=p.decided_by
               WHERE p.id=?""",
            (proposal_id,),
        ).fetchone())
        if not row:
            raise KeyError("Schedule proposal not found.")
        if not self.can_view_project(actor, row["project_id"]):
            raise Forbidden("Schedule proposal access denied.")
        return row

    def list_schedule_proposals(self, actor: dict, task_id: str) -> list[dict]:
        self.get_task(actor, task_id)
        rows = self.db.execute(
            """SELECT p.*, pb.display_name proposed_by_name, db.display_name decided_by_name
               FROM task_schedule_proposals p LEFT JOIN users pb ON pb.id=p.proposed_by
               LEFT JOIN users db ON db.id=p.decided_by
               WHERE p.task_id=? ORDER BY p.proposed_at DESC""",
            (task_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def propose_schedule(self, actor: dict, task_id: str, start_date, due_date, reason: str) -> dict:
        task = self.get_task(actor, task_id)
        if not self.can_manage_project(actor, task["project_id"]):
            raise Forbidden("Task-management access denied.")
        self._refuse_closed(task)
        reason = str(reason).strip()
        if not reason:
            raise ValueError("A reason is required to propose a schedule change.")
        start, due = self._date(start_date), self._date(due_date)
        if start and due and due < start:
            raise ValueError("Due date cannot be earlier than start date.")
        proposal_id, timestamp = new_id(), now_text()
        with transaction(self.db):
            self._refuse_closed_in_transaction(task_id)
            self.db.execute(
                "INSERT INTO task_schedule_proposals(id,task_id,start_date,due_date,reason,proposed_by,proposed_at,status)"
                " VALUES(?,?,?,?,?,?,?,'pending')",
                (proposal_id, task_id, start, due, reason, actor["id"], timestamp),
            )
            self._event(task_id, actor["id"], "schedule_proposed", None,
                        {"start_date": start, "due_date": due}, reason)
        proposal = self.get_schedule_proposal(actor, proposal_id)
        # Dependents are shown, never silently rescheduled.
        proposal["impacted_successors"] = self._impacted_successors(task_id)
        return proposal

    def approve_schedule_proposal(self, actor: dict, proposal_id: str, decision_reason: str = "",
        *, owner_decision: OwnerDecision | None = None,
    ) -> dict:
        proposal = self.get_schedule_proposal(actor, proposal_id)
        task = self.get_task(actor, proposal["task_id"])
        if proposal["status"] != "pending":
            raise ValueError("Only a pending schedule proposal can be approved.")
        self._refuse_closed(task)
        if actor["global_role"] != "owner":
            return self._request_protected_action(
                actor,
                task,
                "approve_schedule_proposal",
                {"proposal_id": proposal_id, "decision_reason": str(decision_reason or "").strip()},
                str(decision_reason or "").strip(),
            )
        timestamp = now_text()
        before = {"start_date": task.get("start_date"), "due_date": task.get("due_date")}
        after = {"start_date": proposal["start_date"], "due_date": proposal["due_date"]}
        expected_task_revision = task["revision"]
        with transaction(self.db):
            proposal = self.get_schedule_proposal(actor, proposal_id)
            task = self.get_task(actor, proposal["task_id"])
            if task["revision"] != expected_task_revision:
                raise Conflict("Task revision conflict: the task changed before schedule approval began.")
            # Defence in depth: every closing write bumps the revision, so the check above
            # already refuses a task closed after the pre-check (review SVC-4).
            self._refuse_closed_in_transaction(task["id"])
            self._assert_active_request_revision(task, owner_decision)
            if proposal["status"] != "pending":
                raise Conflict("Schedule decision conflict: this proposal is no longer pending.")
            cursor = self.db.execute(
                "UPDATE tasks SET start_date=?, due_date=?, updated_at=?, revision=revision+1"
                " WHERE id=? AND revision=?",
                (proposal["start_date"], proposal["due_date"], timestamp, task["id"], task["revision"]),
            )
            if cursor.rowcount != 1:
                raise Conflict("Task revision conflict: the task changed before the schedule was approved.")
            self._ensure_baseline(task["id"])
            cursor = self.db.execute(
                "UPDATE task_schedule_proposals SET status='approved', decided_by=?, decided_at=?, decision_reason=?"
                " WHERE id=? AND status='pending'",
                (actor["id"], timestamp, str(decision_reason).strip() or None, proposal_id),
            )
            if cursor.rowcount != 1:
                raise Conflict("Schedule decision conflict: this proposal is no longer pending.")
            self._event(task["id"], actor["id"], "schedule_revised", before, after, proposal["reason"])
            self._resolve_pending_requests(
                actor,
                "approve_schedule_proposal",
                project_id=task["project_id"],
                intent={"proposal_id": proposal_id},
                task_id=task["id"],
                expected_revision=task["revision"],
                decision_reason=str(decision_reason or "").strip(),
                owner_decision=owner_decision,
            )
        return self.get_task(actor, task["id"])

    def reject_schedule_proposal(self, actor: dict, proposal_id: str, reason: str,
        *, owner_decision: OwnerDecision | None = None,
    ) -> dict:
        proposal = self.get_schedule_proposal(actor, proposal_id)
        task = self.get_task(actor, proposal["task_id"])
        if proposal["status"] != "pending":
            raise ValueError("Only a pending schedule proposal can be rejected.")
        reason = str(reason).strip()
        if not reason:
            raise ValueError("A reason is required to reject a schedule proposal.")
        if actor["global_role"] != "owner":
            return self._request_protected_action(
                actor, task, "reject_schedule_proposal", {"proposal_id": proposal_id, "reason": reason}, reason
            )
        with transaction(self.db):
            proposal = self.get_schedule_proposal(actor, proposal_id)
            task = self.get_task(actor, proposal["task_id"])
            self._assert_active_request_revision(task, owner_decision)
            if proposal["status"] != "pending":
                raise Conflict("Schedule decision conflict: this proposal is no longer pending.")
            cursor = self.db.execute(
                "UPDATE task_schedule_proposals SET status='rejected', decided_by=?, decided_at=?, decision_reason=?"
                " WHERE id=? AND status='pending'",
                (actor["id"], now_text(), reason, proposal_id),
            )
            if cursor.rowcount != 1:
                raise Conflict("Schedule decision conflict: this proposal is no longer pending.")
            self._event(task["id"], actor["id"], "schedule_proposal_rejected", None,
                        {"proposal_id": proposal_id}, reason)
            self._resolve_pending_requests(
                actor,
                "reject_schedule_proposal",
                project_id=task["project_id"],
                intent={"proposal_id": proposal_id},
                task_id=task["id"],
                expected_revision=task["revision"],
                decision_reason=reason,
                owner_decision=owner_decision,
            )
        return self.get_schedule_proposal(actor, proposal_id)

    def add_task_dependency(
        self,
        actor: dict,
        predecessor_task_id: str,
        successor_task_id: str,
        dependency_type: str = "finish_to_start",
    ) -> dict:
        predecessor = self.get_task(actor, predecessor_task_id)
        successor = self.get_task(actor, successor_task_id)
        if not self.can_manage_project(actor, successor["project_id"]):
            raise Forbidden("Task-management access denied.")
        if predecessor["project_id"] != successor["project_id"]:
            raise ValueError("Dependencies must stay within one project.")
        if predecessor_task_id == successor_task_id:
            raise ValueError("A task cannot depend on itself.")
        if dependency_type != "finish_to_start":
            raise ValueError("Only finish-to-start dependencies are currently supported.")
        # Only the successor changes; a closed task may still be added as a predecessor.
        self._refuse_closed(successor)
        value = {
            "predecessor_task_id": predecessor_task_id,
            "successor_task_id": successor_task_id,
            "dependency_type": dependency_type,
            "created": True,
        }
        with transaction(self.db):
            self._refuse_closed_in_transaction(successor_task_id)
            existing = self.db.execute(
                """SELECT 1 FROM task_dependencies
                   WHERE predecessor_task_id=? AND successor_task_id=?""",
                (predecessor_task_id, successor_task_id),
            ).fetchone()
            if existing:
                return {**value, "created": False}
            cycle = self.db.execute(
                """WITH RECURSIVE descendants(task_id) AS (
                       SELECT successor_task_id FROM task_dependencies WHERE predecessor_task_id=?
                       UNION
                       SELECT d.successor_task_id FROM task_dependencies d
                       JOIN descendants r ON d.predecessor_task_id=r.task_id
                   )
                   SELECT 1 FROM descendants WHERE task_id=? LIMIT 1""",
                (successor_task_id, predecessor_task_id),
            ).fetchone()
            if cycle:
                raise ValueError("This dependency would create a cycle.")
            self.db.execute(
                "INSERT INTO task_dependencies VALUES(?,?,?)",
                (predecessor_task_id, successor_task_id, dependency_type),
            )
            self._event(successor_task_id, actor["id"], "dependency_added", None, value, None)
        return value

    def remove_task_dependency(
        self, actor: dict, predecessor_task_id: str, successor_task_id: str, reason: str
    ) -> None:
        successor = self.get_task(actor, successor_task_id)
        if not self.can_manage_project(actor, successor["project_id"]):
            raise Forbidden("Task-management access denied.")
        self._refuse_closed(successor)
        reason = str(reason).strip()
        if not reason:
            raise ValueError("A reason is required to remove a dependency.")
        existing = self.db.execute(
            """SELECT dependency_type FROM task_dependencies
               WHERE predecessor_task_id=? AND successor_task_id=?""",
            (predecessor_task_id, successor_task_id),
        ).fetchone()
        if not existing:
            raise KeyError("Dependency not found.")
        before = {
            "predecessor_task_id": predecessor_task_id,
            "successor_task_id": successor_task_id,
            "dependency_type": existing["dependency_type"],
        }
        with transaction(self.db):
            self._refuse_closed_in_transaction(successor_task_id)
            self.db.execute(
                """DELETE FROM task_dependencies
                   WHERE predecessor_task_id=? AND successor_task_id=?""",
                (predecessor_task_id, successor_task_id),
            )
            self._event(successor_task_id, actor["id"], "dependency_removed", before, None, reason)

    def get_task_dependencies(self, actor: dict, task_id: str) -> list[dict]:
        task = self.get_task(actor, task_id)
        rows = self.db.execute(
            """SELECT d.predecessor_task_id,d.successor_task_id,d.dependency_type,
                      p.title predecessor_title,p.status predecessor_status,
                      s.title successor_title
               FROM task_dependencies d
               JOIN tasks p ON p.id=d.predecessor_task_id
               JOIN tasks s ON s.id=d.successor_task_id
               WHERE d.predecessor_task_id=? OR d.successor_task_id=?
               ORDER BY p.title COLLATE NOCASE,s.title COLLATE NOCASE""",
            (task_id, task_id),
        ).fetchall()
        return [
            {
                **dict(row),
                "direction": "incoming" if row["successor_task_id"] == task["id"] else "outgoing",
                "blocking": row["successor_task_id"] == task["id"] and row["predecessor_status"] != "completed",
            }
            for row in rows
        ]

    def _add_dependency_state(self, tasks: list[dict]) -> list[dict]:
        if not tasks:
            return tasks
        task_ids = {task["id"] for task in tasks}
        placeholders = ",".join("?" for _ in task_ids)
        rows = self.db.execute(
            f"""SELECT d.successor_task_id,d.predecessor_task_id,t.title,t.status
                FROM task_dependencies d JOIN tasks t ON t.id=d.predecessor_task_id
                WHERE d.successor_task_id IN ({placeholders})
                ORDER BY t.title COLLATE NOCASE""",
            tuple(task_ids),
        ).fetchall()
        incoming = {task_id: [] for task_id in task_ids}
        for row in rows:
            incoming[row["successor_task_id"]].append({
                "task_id": row["predecessor_task_id"],
                "title": row["title"],
                "status": row["status"],
                "blocking": row["status"] != "completed",
            })
        for task in tasks:
            task["predecessors"] = incoming[task["id"]]
            task["blocked_by"] = [item for item in task["predecessors"] if item["blocking"]]
            task["is_blocked"] = bool(task["blocked_by"])
        return tasks

    def _event(self, task_id: str, actor_id: str, kind: str, before: dict | None, after: dict | None, reason: str | None,
               *, notify: bool = True) -> None:
        event_id = new_id()
        self.db.execute(
            "INSERT INTO task_events VALUES(?,?,?,?,?,?,?,?)",
            (event_id, task_id, kind, actor_id, now_text(), reason,
             json.dumps(before, default=str, sort_keys=True) if before else None,
             json.dumps(after, default=str, sort_keys=True) if after else None),
        )
        if notify:
            self._notify_owner(event_id, task_id, actor_id, kind)

    def _notify_owner(self, event_id: str, task_id: str, actor_id: str, kind: str) -> None:
        # Durable record for the app owner of every task change made by someone else.
        # The owner's own actions are already visible to them, so they are not self-notified.
        owner = self.db.execute("SELECT id FROM users WHERE global_role='owner'").fetchone()
        if not owner or owner["id"] == actor_id:
            return
        row = self.db.execute("SELECT title FROM tasks WHERE id=?", (task_id,)).fetchone()
        title = row["title"] if row else task_id
        summary = f"{kind.replace('_', ' ')}: {title}"
        # INSERT OR IGNORE with the unique (user_id, event_id) index makes retries idempotent.
        self.db.execute(
            "INSERT OR IGNORE INTO notifications(id,user_id,event_id,task_id,kind,summary,created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (new_id(), owner["id"], event_id, task_id, kind, summary, now_text()),
        )

    def list_notifications(self, actor: dict, unread_only: bool = False) -> list[dict]:
        query = ("SELECT n.*, t.title task_title FROM notifications n LEFT JOIN tasks t ON t.id=n.task_id"
                 " WHERE n.user_id=?")
        if unread_only:
            query += " AND n.read_at IS NULL"
        query += " ORDER BY n.created_at DESC, n.id DESC LIMIT 200"
        return [dict(row) for row in self.db.execute(query, (actor["id"],)).fetchall()]

    def unread_notification_count(self, actor: dict) -> int:
        return self.db.execute(
            "SELECT COUNT(*) c FROM notifications WHERE user_id=? AND read_at IS NULL", (actor["id"],)
        ).fetchone()["c"]

    def mark_notification_read(self, actor: dict, notification_id: str) -> None:
        row = self.db.execute("SELECT user_id FROM notifications WHERE id=?", (notification_id,)).fetchone()
        if not row:
            raise KeyError("Notification not found.")
        if row["user_id"] != actor["id"]:
            raise Forbidden("Notification access denied.")
        # Marking read only sets read_at; it never deletes the record or changes task state.
        self.db.execute(
            "UPDATE notifications SET read_at=? WHERE id=? AND read_at IS NULL", (now_text(), notification_id)
        )

    def mark_all_notifications_read(self, actor: dict) -> int:
        cursor = self.db.execute(
            "UPDATE notifications SET read_at=? WHERE user_id=? AND read_at IS NULL", (now_text(), actor["id"])
        )
        return cursor.rowcount

    @staticmethod
    def _date(value) -> str | None:
        if value in (None, ""):
            return None
        return date.fromisoformat(str(value)).isoformat()

    @staticmethod
    def _progress(value) -> int | None:
        if value in (None, ""):
            return None
        number = int(value)
        if not 0 <= number <= 100:
            raise ValueError("Progress must be between 0 and 100.")
        return number

    @staticmethod
    def _today_in_timezone(tz_name: str | None) -> str:
        """Current calendar date in the project's governing timezone.

        A date-only deadline runs through the end of that local day, so the
        comparison date must be 'now' as seen in the project's timezone rather
        than the server's local date. Falls back to the server date only if the
        timezone name is missing or the IANA database is unavailable.
        """
        if tz_name:
            try:
                return datetime.now(ZoneInfo(tz_name)).date().isoformat()
            except (ZoneInfoNotFoundError, ValueError):
                pass
        return date.today().isoformat()

    @staticmethod
    def _due_state(due_date: str | None, status: str, today: str) -> str:
        if status in {"completed", "cancelled", "abandoned"}:
            return "closed"
        if not due_date:
            return "undated"
        days = (date.fromisoformat(due_date) - date.fromisoformat(today)).days
        if days < 0:
            return "overdue"
        if days == 0:
            return "today"
        if days <= 7:
            return "soon"
        return "scheduled"

    # --- Excel / CSV import (C9KPH6) ---
    #
    # The service is the authorization boundary: the App Owner may import into any
    # project and is the only one who may create a project from a file; a project
    # Manager may import into the projects they manage, with every Owner-only
    # action downgraded to a per-row warning by the engine. Viewers, members and
    # read-only Chairmen are blocked, audited and the Owner is notified.

    IMPORT_OPTION_KEYS = {"valid_rows_only", "default_reason"}

    def _import_config(self) -> importer.TemplateConfig:
        row = self.db.execute("SELECT config_json FROM import_template_config WHERE id=1").fetchone()
        return importer.TemplateConfig.from_json(row["config_json"] if row else None)

    def _manages_any_project(self, actor: dict) -> bool:
        return bool(self.db.execute(
            "SELECT 1 FROM memberships WHERE user_id=? AND role='manager' LIMIT 1", (actor["id"],)
        ).fetchone())

    def get_import_template_config(self, actor: dict) -> dict:
        if not actor.get("active"):
            raise Forbidden("Import access denied.")
        if actor["global_role"] != "owner" and not self._manages_any_project(actor):
            raise Forbidden("Only the App Owner and project Managers may read the import template settings.")
        row = self.db.execute("SELECT * FROM import_template_config WHERE id=1").fetchone()
        config = importer.TemplateConfig.from_json(row["config_json"] if row else None)
        result = config.to_dict()
        result["version"] = row["version"] if row else 0
        result["updated_at"] = row["updated_at"] if row else None
        updated_by = None
        if row and row["updated_by"]:
            user = self.db.execute("SELECT display_name FROM users WHERE id=?", (row["updated_by"],)).fetchone()
            updated_by = user["display_name"] if user else None
        result["updated_by_name"] = updated_by
        result["custom_types"] = list(importer.CUSTOM_TYPES)
        result["can_edit"] = actor["global_role"] == "owner"
        return result

    def set_import_template_config(self, actor: dict, payload: dict) -> dict:
        self.require_owner(actor)
        if payload is None or payload.get("reset"):
            config = importer.TemplateConfig.default()
        elif payload.get("preset"):
            config = importer.TemplateConfig.preset(str(payload["preset"]))
        else:
            config = importer.TemplateConfig.normalize(payload.get("columns", []))
        with transaction(self.db):
            row = self.db.execute("SELECT version FROM import_template_config WHERE id=1").fetchone()
            version = (row["version"] if row else 0) + 1
            self.db.execute(
                "INSERT INTO import_template_config(id,version,config_json,updated_at,updated_by) VALUES(1,?,?,?,?)"
                " ON CONFLICT(id) DO UPDATE SET version=excluded.version, config_json=excluded.config_json,"
                " updated_at=excluded.updated_at, updated_by=excluded.updated_by",
                (version, config.to_json(), now_text(), actor["id"]),
            )
        return self.get_import_template_config(actor)

    def import_template(self, actor: dict, fmt: str, project_id: str | None = None) -> tuple[bytes, str, str]:
        """The template a signed-in user downloads; built from the current configuration.

        With ``project_id`` the Tasks sheet comes pre-filled with that project's tasks
        (App Owner: any project; Manager: the projects they manage; others 403). Tasks
        that have no Import Key get one assigned and stored first (T-001 ... continuing
        above the highest in use, ``import_key_assigned`` event), so a later upload of
        the file updates the same tasks instead of creating duplicates.
        """
        if not actor.get("active"):
            raise Forbidden("Sign in required.")
        if actor["global_role"] != "owner" and not self._manages_any_project(actor):
            # The template carries the configured labels, list values and hash: the same
            # people who may read the configuration (authorization matrix row 20).
            raise Forbidden("Only the App Owner or a project Manager may download the import template.")
        if fmt not in ("csv", "xlsx"):
            raise ValueError("Unknown template format.")
        config = self._import_config()
        tasks = project = people = None
        key_offset = 0
        stem = "astra-import-template"
        if project_id:
            project_row = self._template_project(actor, project_id)
            tasks, project, people, key_offset = self._template_prefill(actor, project_row, config)
            stem = "astra-import-" + (re.sub(r"[^A-Za-z0-9]+", "-", project_row["name"]).strip("-").lower()[:40] or "project")
        if fmt == "csv":
            return (importer.build_template_csv(config, tasks=tasks).encode("utf-8-sig"), stem + ".csv",
                    "text/csv; charset=utf-8")
        payload = importer.build_template_xlsx(config, tasks=tasks, project=project, people=people, key_offset=key_offset)
        return payload, stem + ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def _template_project(self, actor: dict, project_id: str) -> dict:
        project = row_dict(self.db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
        if not project:
            raise KeyError("Project not found.")
        if actor["global_role"] != "owner" and not self._is_project_manager(actor, project_id):
            raise Forbidden("Only the App Owner or a Manager of the project may download its filled template.")
        return project

    def _template_prefill(self, actor: dict, project: dict, config: importer.TemplateConfig):
        """(task rows, Project-sheet values, People rows, key formula offset) for a project-scoped template.

        Assigns and stores Import Keys for tasks that lack one, in one transaction. Row
        values are chosen so that re-uploading the file unedited previews every task as
        unchanged: the Description column carries the full stored description, Notes the
        text of its "Notes:" section, Original Due Date stays blank (a baseline is never
        overwritten), Type only repeats a value the task already carries in import_extras.
        """
        project_id = project["id"]
        with transaction(self.db):
            tasks = [dict(row) for row in self.db.execute(
                "SELECT * FROM tasks WHERE project_id=? ORDER BY created_at, rowid", (project_id,))]
            missing = [task for task in tasks if not task.get("import_key")]
            if missing:
                fresh = importer.assign_sequence_keys([t["import_key"] for t in tasks if t.get("import_key")], len(missing))
                for task, key in zip(missing, fresh):
                    self.db.execute("UPDATE tasks SET import_key=? WHERE id=?", (key, task["id"]))
                    self._event(task["id"], actor["id"], "import_key_assigned", {"import_key": None}, {"import_key": key},
                                "Assigned when the project's import template was downloaded", notify=False)
                    task["import_key"] = key
            users = {row["id"]: dict(row) for row in self.db.execute("SELECT id, email, display_name, active FROM users")}
            reviewers: dict[str, dict[str, list]] = {}
            for row in self.db.execute(
                """SELECT r.task_id, r.role, u.email FROM task_reviewers r JOIN users u ON u.id=r.user_id
                   JOIN tasks t ON t.id=r.task_id WHERE t.project_id=? ORDER BY r.created_at""", (project_id,)):
                reviewers.setdefault(row["task_id"], {}).setdefault(row["role"], []).append(row["email"])
            predecessors: dict[str, list] = {}
            key_of = {task["id"]: task["import_key"] for task in tasks}
            for row in self.db.execute(
                """SELECT d.predecessor_task_id p, d.successor_task_id s FROM task_dependencies d
                   JOIN tasks t ON t.id=d.successor_task_id WHERE t.project_id=?""", (project_id,)):
                if row["p"] in key_of:
                    predecessors.setdefault(row["s"], []).append(key_of[row["p"]])
            attachments: dict[str, list] = {}
            for row in self.db.execute(
                "SELECT a.task_id, a.path FROM task_attachments a JOIN tasks t ON t.id=a.task_id WHERE t.project_id=? ORDER BY a.added_at",
                (project_id,)):
                attachments.setdefault(row["task_id"], []).append(row["path"])
            members = [dict(row) for row in self.db.execute(
                """SELECT m.user_id, m.role, u.email, u.display_name FROM memberships m JOIN users u ON u.id=m.user_id
                   WHERE m.project_id=? AND u.active=1 ORDER BY m.created_at, u.email""", (project_id,))]

        def as_date(iso):
            try:
                return date.fromisoformat(iso[:10]) if iso else None
            except ValueError:
                return None

        def row_for(task: dict) -> dict:
            row = {
                "import_key": task["import_key"], "title": task["title"],
                "parent_key": key_of.get(task.get("parent_task_id") or "", ""),
                "owner_email": users.get(task.get("owner_user_id") or "", {}).get("email", ""),
                "start_date": as_date(task.get("start_date")), "due_date": as_date(task.get("due_date")),
                "status": importer.STATUS_LABEL_BY_CODE.get(task["status"], ""),
                "criticality": (task.get("criticality") or "").capitalize(),
                "progress": task.get("progress"), "next_action": task.get("next_action_note") or "",
                "description": task.get("description") or "", "notes": importer.notes_section(task.get("description") or ""),
                "milestone": "Yes" if task.get("is_milestone") else "No",
                "collaborators": "; ".join(reviewers.get(task["id"], {}).get("collaborator", [])),
                "reviewers": "; ".join(reviewers.get(task["id"], {}).get("reviewer", [])),
                "approvers": "; ".join(reviewers.get(task["id"], {}).get("approver", [])),
                "predecessors": "; ".join(predecessors.get(task["id"], [])),
                "attachment_links": "; ".join(attachments.get(task["id"], [])),
            }
            if task.get("import_extras"):
                try:
                    extras = json.loads(task["import_extras"])
                except ValueError:
                    extras = {}
                for key, value in extras.items():
                    column = config.by_key.get(key)
                    if column is None:
                        continue
                    row[key] = as_date(value) if column.kind == "date" and isinstance(value, str) else value
            return row

        # Parents before their steps, each level ordered by start, due, title.
        children: dict[str, list] = {}
        for task in tasks:
            children.setdefault(task.get("parent_task_id") if task.get("parent_task_id") in key_of else None, []).append(task)

        def order(items):
            return sorted(items, key=lambda t: (t.get("start_date") or "9999", t.get("due_date") or "9999", t["title"].casefold()))

        rows, stack = [], list(reversed(order(children.get(None, []))))
        seen = set()
        while stack:
            task = stack.pop()
            if task["id"] in seen:
                continue
            seen.add(task["id"])
            rows.append(row_for(task))
            stack.extend(reversed(order(children.get(task["id"], []))))
        for task in tasks:  # any task whose parent chain is broken still gets a row
            if task["id"] not in seen:
                rows.append(row_for(task))
        manager = next((m for m in members if m["role"] == "manager"), None)
        if manager is None and project.get("manager_user_id") in users:
            manager = users[project["manager_user_id"]]
        working_days = {code: label for label, code in importer.WORKING_DAY_LABELS.items()}
        header = {
            "name": project["name"], "manager_email": manager["email"] if manager else "",
            "timezone": project.get("timezone") or "Asia/Karachi", "description": project.get("description") or "",
            "working_days": working_days.get(project.get("working_days") or "", ""),
            "start_date": as_date(project.get("start_date")), "target_date": as_date(project.get("target_date")),
        }
        people = ([(m["email"], m["display_name"], m["role"].capitalize(), "") for m in members]
                  if config.is_extended() else None)
        key_offset = importer.next_key_offset(key_of.values(), len(rows))
        return rows, header, people, key_offset

    def import_targets(self, actor: dict) -> dict:
        """Projects the actor may import into, and whether they may create one from a file."""
        if not actor.get("active"):
            raise Forbidden("Sign in required.")
        if actor["global_role"] == "owner":
            rows = self.db.execute(
                "SELECT id, name FROM projects WHERE status<>'closed' ORDER BY name COLLATE NOCASE"
            ).fetchall()
            return {"projects": [dict(r) for r in rows], "can_create_project": True, "can_edit_template": True}
        rows = self.db.execute(
            """SELECT p.id, p.name FROM projects p JOIN memberships m ON m.project_id=p.id
               WHERE m.user_id=? AND m.role='manager' AND p.status<>'closed' ORDER BY p.name COLLATE NOCASE""",
            (actor["id"],),
        ).fetchall()
        return {"projects": [dict(r) for r in rows], "can_create_project": False, "can_edit_template": False}

    def _import_blocked(self, actor: dict, project: dict | None, action: str) -> None:
        """Refuse a non-permitted import attempt; the caller audits it (see _audit_import_blocked)."""
        raise ImportBlocked(actor, project, action)

    def _audit_import_blocked(self, blocked: ImportBlocked) -> None:
        """Audit a blocked import attempt and notify the Owner. Runs in autocommit, after any
        rollback, so the record is kept whatever else the request had started. Without a
        target project only the Owner notification is written (there is no project to
        audit against)."""
        actor, project, action = blocked.actor, blocked.project, blocked.action
        event_id = new_id()
        occurred_at = now_text()
        label = project["name"] if project else "new project"
        if project:
            self._project_event(
                project["id"], actor["id"], "protected_action_blocked",
                {"event_id": event_id, "action": action, "payload": {}}, "Actor cannot import into this project",
            )
        owner = self.db.execute("SELECT id FROM users WHERE global_role='owner'").fetchone()
        if owner and owner["id"] != actor["id"]:
            self.db.execute(
                "INSERT OR IGNORE INTO notifications(id,user_id,event_id,task_id,kind,summary,created_at)"
                " VALUES(?,?,?,?,?,?,?)",
                (new_id(), owner["id"], event_id, None, "protected_action_blocked",
                 f"blocked {action.replace('_', ' ')} attempt: {label}", occurred_at),
            )

    def _import_authorize(self, actor: dict, project_id: str | None, action: str) -> tuple[bool, dict | None]:
        if not actor.get("active"):
            raise Forbidden("Sign in required.")
        is_owner = actor["global_role"] == "owner"
        project = None
        if project_id:
            project = row_dict(self.db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
            if not project:
                raise KeyError("Project not found.")
            if project["status"] == "closed":
                raise ValueError("This project is closed; reopen it before importing.")
        if not is_owner:
            if not project:
                if actor["global_role"] == "chairman" or not self._manages_any_project(actor):
                    self._import_blocked(actor, None, action)
                raise ValueError("Choose the project you manage as the import target; only the App Owner may import without one.")
            if not self._is_project_manager(actor, project["id"]):
                self._import_blocked(actor, project, action)
        return is_owner, project

    @staticmethod
    def _import_options(options) -> dict:
        options = dict(options or {})
        unknown = set(options) - AstraService.IMPORT_OPTION_KEYS
        if unknown:
            raise ValueError(f"Unknown import option(s): {', '.join(sorted(unknown))}.")
        return {
            "valid_rows_only": bool(options.get("valid_rows_only")),
            "default_reason": str(options.get("default_reason") or "").strip()[:200],
        }

    def _import_engine(self, actor: dict, project_id: str | None, filename: str, data: bytes, options: dict, action: str):
        is_owner, project = self._import_authorize(actor, project_id, action)
        options = self._import_options(options)
        config = self._import_config()
        parsed = importer.parse_upload(filename, data, config)
        new_project_name = None
        if project is None:
            header_name = parsed.project_header.get("name")
            names = sorted({importer.normalize_text(row.cells.get("project")) for row in parsed.rows
                            if importer.normalize_text(row.cells.get("project"))})
            if header_name:
                names = [header_name]
            if not names:
                raise ValueError("Choose a target project, or fill the Project sheet so Astra knows where the rows go.")
            if len(names) > 1:
                raise ValueError("The file names several projects (" + "; ".join(names) + "). Import one project per file.")
            matches = self.db.execute(
                "SELECT * FROM projects WHERE name=? COLLATE NOCASE", (names[0],)
            ).fetchall()
            if len(matches) > 1:
                raise ValueError(f"Several projects are named '{names[0]}'; choose the target project explicitly.")
            if matches:
                project = dict(matches[0])
                if project["status"] == "closed":
                    raise ValueError("This project is closed; reopen it before importing.")
            else:
                new_project_name = names[0]
        engine = importer.ImportEngine(
            self.db, config, actor=actor, is_owner=is_owner, project=project, new_project_name=new_project_name,
            filename=filename, options=options,
        )
        preview = engine.validate(parsed)
        return engine, preview, options

    def import_preview(self, actor: dict, project_id: str | None, filename: str, data: bytes, options=None) -> dict:
        """Parse and validate; writes nothing (a blocked attempt is audited)."""
        try:
            engine, preview, options = self._import_engine(actor, project_id, filename, data, options, "import_preview")
        except ImportBlocked as blocked:
            self._audit_import_blocked(blocked)
            raise
        preview["sha256"] = importer.sha256_hex(data)
        preview["plan_fingerprint"] = importer.plan_fingerprint(engine)
        preview["filename"] = os.path.basename(filename or "upload")
        preview["options"] = options
        preview["can_commit"] = preview["summary"]["errors"] == 0 or options["valid_rows_only"]
        return preview

    def import_commit(self, actor: dict, project_id: str | None, filename: str, data: bytes, options=None,
                      expected_sha256: str | None = None, expected_plan: str | None = None,
                      plan_required: bool = False) -> dict:
        """Re-validate the same bytes inside the write transaction and apply the plan.

        Validation (cycle checks, the snapshot of existing tasks) and apply share one
        ``BEGIN IMMEDIATE``, so no other writer can add a dependency or parent between the
        two (review DI-2). ``expected_plan`` is the preview's plan fingerprint: when the
        same bytes now produce a different plan (a key taken by a hand-made task, a task
        edited in the meantime) the commit is refused with HTTP 409 (review DI-3). The HTTP
        route sets ``plan_required`` so every commit over the API follows a preview.
        """
        digest = importer.sha256_hex(data)
        if expected_sha256 and expected_sha256.casefold() != digest:
            raise importer.ImportConflict("The file changed since the preview. Run the preview again before importing.")
        import_id = new_id()
        try:
            with transaction(self.db):
                engine, preview, options = self._import_engine(actor, project_id, filename, data, options, "import_commit")
                if plan_required and not expected_plan:
                    raise ValueError("Run the preview first: the commit needs the preview's plan fingerprint (X-Plan-Fingerprint).")
                if expected_plan and expected_plan.casefold() != importer.plan_fingerprint(engine):
                    raise importer.ImportConflict(
                        "The project changed since the preview (a task was added, keyed or edited in the meantime), so "
                        "the file would now do something else; nothing was written. Run the preview again and check it."
                    )
                if preview["summary"]["errors"] and not options["valid_rows_only"]:
                    raise ValueError("The file has rows with errors. Fix them or tick 'Import valid rows only'.")
                if not any(row["action"] != "error" for row in preview["rows"]):
                    raise ValueError("Nothing to import: every row has errors.")
                summary = self._import_apply(actor, engine, filename, digest, import_id, options)
        except ImportBlocked as blocked:
            self._audit_import_blocked(blocked)
            raise
        except sqlite3.IntegrityError as exc:
            # Another writer took one of these Import Keys between preview and commit; the
            # transaction is rolled back, and the client gets a 409 with a retry hint.
            if "import_key" in str(exc):
                raise importer.ImportConflict(
                    "Another import or edit took one of these Import Keys while this import ran; nothing was written. "
                    "Run the preview again and retry."
                ) from exc
            raise
        summary["import_id"] = import_id
        summary["report_url"] = f"/api/imports/{import_id}/report.csv"
        return summary

    def _import_apply(self, actor: dict, engine, filename: str, digest: str, import_id: str, options: dict) -> dict:
        """The body of the import transaction (see import_commit)."""
        if engine.project is None:
            project_id = self._create_project_from_header(actor, engine.new_project_name, engine.project_header)
            engine.project = {"id": project_id, "name": engine.new_project_name}
            engine.project_id = project_id
            for user_id, role in engine.grants.items():  # users named in the rows get access (manager stays manager)
                self.db.execute("INSERT OR IGNORE INTO memberships VALUES(?,?,?,?,?)",
                                (project_id, user_id, role, now_text(), actor["id"]))
        else:
            project_id = engine.project["id"]
        summary = engine.apply(self, project_id, import_id, valid_rows_only=options["valid_rows_only"])
        summary["project"] = {"id": project_id, "name": engine.project["name"], "create": engine.new_project_name is not None}
        summary["filename"] = os.path.basename(filename or "upload")
        summary["sha256"] = digest
        header = engine.project_header
        if header.get("as_of_date") or header.get("source_document"):
            summary["plan_as_of"] = header.get("as_of_date")
            summary["source_document"] = header.get("source_document")
        self._project_event(
            project_id, actor["id"], "import_committed",
            {"import_id": import_id, "filename": summary["filename"], "sha256": digest,
             "counts": {k: summary[k] for k in ("rows", "create", "update", "unchanged", "skipped_errors", "dependencies")}},
            None,
        )
        self.db.execute(
            "INSERT INTO imports(id,project_id,actor_user_id,filename,sha256,created_at,summary_json,report_csv)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (import_id, project_id, actor["id"], summary["filename"], digest, now_text(),
             json.dumps(summary, default=str, sort_keys=True), engine.report_csv()),
        )
        owner = self.db.execute("SELECT id FROM users WHERE global_role='owner'").fetchone()
        if owner and owner["id"] != actor["id"]:
            self.db.execute(
                "INSERT OR IGNORE INTO notifications(id,user_id,event_id,task_id,kind,summary,created_at)"
                " VALUES(?,?,?,?,?,?,?)",
                (new_id(), owner["id"], import_id, None, "import_committed",
                 f"import committed: {summary['filename']} into {engine.project['name']}"
                 f" ({summary['create']} created, {summary['update']} updated)", now_text()),
            )
        return summary

    def _create_project_from_header(self, actor: dict, name: str, header: dict) -> str:
        """Owner-only: the Project sheet of the workbook becomes the new project. Runs inside the import transaction."""
        project_id = new_id()
        description = header.get("description", "")
        if header.get("sponsor_email"):
            description = (description + "\n\n" if description else "") + f"Sponsor / Executive Owner: {header['sponsor_email']}"
        timezone_name = header.get("timezone") or "Asia/Karachi"
        try:
            ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError):
            timezone_name = "Asia/Karachi"
        working_days = importer.WORKING_DAY_LABELS.get(header.get("working_days", ""), "0123456")
        manager_id = None
        if header.get("manager_email"):
            row = self.db.execute(
                "SELECT id FROM users WHERE email=? AND active=1", (normalize_email(header["manager_email"]),)
            ).fetchone()
            manager_id = row["id"] if row else None
        self.db.execute(
            """INSERT INTO projects(id,name,description,manager_user_id,timezone,working_days,start_date,target_date,
               created_at,created_by) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (project_id, name, description, manager_id, timezone_name, working_days,
             header.get("start_date"), header.get("target_date"), now_text(), actor["id"]),
        )
        if manager_id:
            self.db.execute(
                "INSERT INTO memberships VALUES(?,?,?,?,?) ON CONFLICT(project_id,user_id) DO UPDATE SET role=excluded.role",
                (project_id, manager_id, "manager", now_text(), actor["id"]),
            )
        if header.get("entity"):
            entity = self.db.execute(
                "SELECT id FROM entities WHERE name=? COLLATE NOCASE AND active=1", (header["entity"],)
            ).fetchone()
            if entity:
                self.db.execute("INSERT OR IGNORE INTO project_entities VALUES(?,?)", (project_id, entity["id"]))
        return project_id

    def list_imports(self, actor: dict, project_id: str | None = None) -> list[dict]:
        if not actor.get("active"):
            raise Forbidden("Sign in required.")
        query = ("SELECT i.id, i.project_id, i.filename, i.sha256, i.created_at, i.summary_json, i.actor_user_id,"
                 " u.display_name actor_name, p.name project_name FROM imports i"
                 " LEFT JOIN users u ON u.id=i.actor_user_id LEFT JOIN projects p ON p.id=i.project_id")
        clauses, params = [], []
        if project_id:
            clauses.append("i.project_id=?")
            params.append(project_id)
        if actor["global_role"] != "owner":
            clauses.append("(i.actor_user_id=? OR EXISTS(SELECT 1 FROM memberships m WHERE m.project_id=i.project_id"
                           " AND m.user_id=? AND m.role='manager'))")
            params.extend([actor["id"], actor["id"]])
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY i.created_at DESC LIMIT 200"
        result = []
        for row in self.db.execute(query, params).fetchall():
            item = dict(row)
            item["summary"] = json.loads(item.pop("summary_json") or "{}")
            result.append(item)
        return result

    def import_report(self, actor: dict, import_id: str) -> dict:
        if not actor.get("active"):
            raise Forbidden("Sign in required.")
        row = row_dict(self.db.execute("SELECT * FROM imports WHERE id=?", (import_id,)).fetchone())
        if not row:
            raise KeyError("Import not found.")
        allowed = (actor["global_role"] == "owner" or row["actor_user_id"] == actor["id"]
                   or (row["project_id"] and self._is_project_manager(actor, row["project_id"])))
        if not allowed:
            raise Forbidden("Import report access denied.")
        stamp = row["created_at"][:19].replace(":", "-")
        return {"filename": f"astra-import-report-{stamp}.csv", "csv": row["report_csv"], "import": row}

    def _imported_fields(self, task: dict) -> list[dict]:
        """Custom template columns stored on the task, labelled from the current configuration."""
        raw = task.get("import_extras")
        if not raw:
            return []
        try:
            extras = json.loads(raw)
        except ValueError:
            return []
        config = self._import_config()
        labels = {item["key"]: item["label"] for item in config.columns if item.get("custom")}
        result = []
        for key in sorted(extras):
            value = extras[key]
            column = config.by_key.get(key)
            if column is not None and column.kind == "date":
                value = importer.display_date(value)
            result.append({"key": key, "label": labels.get(key, key), "value": value})
        return result
