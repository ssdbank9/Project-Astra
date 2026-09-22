"""Excel / CSV import: template contract and configuration, locked template
builder, upload parser, row validation and the commit plan.

The service layer (``AstraService.import_preview`` / ``import_commit``) owns
authorization and the database transaction; this module owns everything that
does not need a decision about *who* is importing: reading the file, matching
headers, coercing cells, and turning rows into a validated plan. The engine
receives the actor's capability (App Owner or project Manager) as data and
downgrades protected actions to per-row warnings for Managers.

Dates inside this feature are shown as dd-mm-yyyy (the Owner's convention) and
stored as ISO like the rest of Astra. Stdlib only. See
``docs/design/excel-import.md`` for the user-facing contract.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import math
import os
import re
import struct
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .xlsx_reader import (CellError, Percent, XlsxError, XlsxTooLarge, column_letter, read_workbook,
                          serial_to_date)

TEMPLATE_SHEET = "Tasks"
README_SHEET = "README"
MARKER_SHEET = "_astra"
MARKER_NAME = "AstraTemplateVersion"
FINGERPRINT_NAME = "AstraHeaderFingerprint"
# Sheet protection guards against accidental edits; it is not a secret. The
# password is documented so the App Owner can unlock a sheet deliberately.
TEMPLATE_SHEET_PASSWORD = "astra-template"
EXAMPLE_KEY = "EXAMPLE-001"
EXAMPLE_KEY_PREFIXES = ("EXAMPLE-", "EX-")

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 2000
MAX_COLUMNS = 40
MAX_CELL_CHARS = 4000
MAX_TITLE_CHARS = 200
MAX_NOTE_CHARS = 200
MAX_KEY_CHARS = 40
MAX_LABEL_CHARS = 60
MAX_LIST_LITERAL = 255          # Excel's limit for an inline dropdown list
TEMPLATE_DATA_ROWS = 2000       # rows carrying validation and unlocked cells
NUMBER_LIMIT = 1e15             # custom Number columns: finite and within +-1e15 (review DI-4)
# A CSV cell longer than the module default (128 KiB) must reach E_CELL_TOO_LONG, not csv.Error.
csv.field_size_limit(max(csv.field_size_limit(), 2 * MAX_FILE_BYTES))
DATE_MIN = date(2000, 1, 1)
DATE_MAX = date(2100, 12, 31)
EXCEL_EPOCH = date(1899, 12, 30)
DISPLAY_DATE_FORMAT = "dd-mm-yyyy"

KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
ISO_DATE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T].*)?$")
DMY_DATE = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$")
DEPENDENCY_TYPES = ("FS", "SS", "FF", "SF")
# A predecessor item is "KEY [type] [lag]": a 40-character key plus blanks, a two-letter type and a
# lag such as "+ 12 days". Anything longer cannot be valid and is refused before parsing, so a
# hostile cell costs one length check (regression review SECURITY-1).
MAX_PRED_ITEM_CHARS = 200
LIST_SEPARATOR = ";"
CUSTOM_PREFIX = "x_"
CUSTOM_KEY_PATTERN = re.compile(r"^x_[a-z0-9_]{1,40}$")   # a client-supplied custom key; slug_key() output fits it
CUSTOM_TYPES = ("text", "number", "date", "list")
CORE_KEYS = ("import_key", "title", "start_date", "due_date", "status", "owner_email")
# What a Manager sees for any person the file names who cannot be assigned here, whatever the
# reason (regression review SECURITY-4); the App Owner gets the precise finding instead.
NEUTRAL_PERSON_MESSAGE = "'{text}' is not an active member of this project; ask the App Owner to grant access, then re-import."


@dataclass(frozen=True)
class Column:
    header: str
    key: str
    kind: str                      # string|text|email|email_list|date|integer|enum|boolean|string_list
    required: bool = False
    aliases: tuple = ()
    allowed: tuple = ()
    width: int = 16
    example: str = ""
    prompt: str = ""
    note: str = ""                 # one line of context (README / header guidance)
    target: str = ""               # where the value lands in Astra (README dictionary)
    vkind: str = "long"            # Excel validation kind: key|key_ref|key_list|text|short|long|email|email_list|date|date_due|list|percent|int


STATUS_LABELS = (
    ("Draft", "draft"), ("Assigned", "assigned"), ("In progress", "in_progress"),
    ("Submitted", "submitted"), ("Changes requested", "changes_requested"),
    ("Completed", "completed"), ("On hold", "on_hold"), ("Delayed", "delayed"),
    ("Cancelled", "cancelled"), ("Abandoned", "abandoned"), ("Reopened", "reopened"),
)
CRITICALITY_LABELS = ("Critical", "High", "Normal", "Low")
TYPE_LABELS = ("Task", "Milestone", "Action item")
PROJECT_ROLE_LABELS = ("Manager", "Member", "Viewer")
TIMEZONE_LABELS = ("Asia/Karachi", "Asia/Dubai", "Asia/Kolkata", "Europe/London", "America/New_York",
                   "America/Chicago", "America/Denver", "America/Los_Angeles", "America/Toronto", "UTC")
WORKING_DAY_LABELS = {"Every day": "0123456", "Mon-Fri": "01234", "Mon-Sat": "012345", "Sun-Thu": "01236"}
# Approved baseline entities (service.APPROVED_ENTITIES); duplicated to avoid an import cycle.
ENTITY_LABELS = ("Rupani Foundation USA", "Rupani Foundation Pakistan", "Rupani IB College", "Apex & Co",
                 "Apex Amanat Microfinance", "Ibn Sina Medical College", "Ibn Sina Foundation",
                 "RDI - Global", "RDI Pakistan", "Tax Exempt")

COLUMNS: tuple[Column, ...] = (
    Column("Import Key", "import_key", "string", required=True,
           aliases=("Key", "ID", "UID", "Task ID", "External ID", "#"), width=14, example="RA-001", vkind="key",
           prompt="Required. A short stable id such as RA-001. Letters, digits, . _ - only, no spaces, unique in this sheet. Re-importing the same key UPDATES that task instead of duplicating it.",
           note="Stable id for the row. Parent Key and Predecessors refer to it. Never renumber after the first import.",
           target="tasks.import_key (unique per project) - drives create vs update"),
    Column("Project", "project", "string", aliases=("Project Name",), width=30, example="", vkind="text",
           prompt="Leave blank; the Project sheet and the Import screen name the project.",
           target="projects.name"),
    Column("Entity", "entity", "string_list", aliases=("Entities", "Filing Entity"), width=20, example="", vkind="long",
           prompt="Existing entity names separated by ;  App Owner only.", target="project_entities"),
    Column("Parent Key", "parent_key", "string",
           aliases=("Parent", "Subtask Of", "Parent ID", "Parent Import Key"), width=12, example="", vkind="key_ref",
           prompt="Optional. Import Key of the task this row is a STEP of. Leave blank for a top-level task.",
           note="Makes this row a step (subtask). The parent must be another row in this sheet or an existing task's key.",
           target="tasks.parent_task_id"),
    Column("Title", "title", "string", required=True,
           aliases=("Task", "Task Name", "Name", "Action Item / Deliverable", "Action / Deliverable"), width=46,
           example="Submit accreditation application and upload the evidence receipt", vkind="text",
           prompt="Required. What has to be delivered, up to 200 characters. One row per task, step, milestone or action item.",
           note="The task name shown in Astra's list, board and Gantt.", target="tasks.title"),
    Column("Description", "description", "text", aliases=("Details", "Notes/Description"), width=40,
           example="Application for Career-related Programme candidacy. Acceptance: receipt uploaded to the shared drive.", vkind="long",
           prompt="Optional. Scope, acceptance criteria, links to minutes. Replaces the description on re-import only when non-empty.",
           note="Free text.", target="tasks.description"),
    Column("Owner Email", "owner_email", "email",
           aliases=("Owner", "Task Owner", "Assignee", "Responsible", "Assigned To"), width=26,
           example="jamal@example.org", vkind="email",
           prompt="One work email of a person who already exists in Astra and has access to the project. Exactly one accountable owner per row; put helpers in Collaborators.",
           note="Matched by email, never by name. Unknown email -> the row imports unassigned with a warning.",
           target="tasks.owner_user_id via users.email"),
    Column("Collaborators", "collaborators", "email_list", aliases=("Collaborator Emails", "Contributors"), width=28,
           example="waseem@example.org", vkind="email_list",
           prompt="Optional. Emails separated by ; (semicolon). Groups such as 'Academic Team' cannot be assigned - name the people.",
           note="People who help deliver. Import adds, never removes.", target="task_reviewers(role=collaborator)"),
    Column("Reviewers", "reviewers", "email_list", aliases=("Reviewer Emails",), width=22, example="", vkind="email_list",
           prompt="Emails separated by ;", target="task_reviewers(role=reviewer)"),
    Column("Approvers", "approvers", "email_list", aliases=("Approver Emails",), width=22, example="", vkind="email_list",
           prompt="Emails separated by ;", target="task_reviewers(role=approver)"),
    Column("Start Date", "start_date", "date", aliases=("Start", "Planned Start"), width=13, example="01-09-2026", vkind="date",
           prompt="Optional. A real date. Shows as dd-mm-yyyy. If unsure how your Excel reads dates, type yyyy-mm-dd (e.g. 2026-09-07). Never type TBD here - put it in Notes.",
           note="Displayed dd-mm-yyyy. Blank = unscheduled.", target="tasks.start_date"),
    Column("Due Date", "due_date", "date",
           aliases=("Due", "Finish", "End Date", "Deadline", "Due / Milestone", "Revised Due Date"), width=13,
           example="15-09-2026", vkind="date_due",
           prompt="Optional. A real date on or after Start Date. Shows as dd-mm-yyyy; type yyyy-mm-dd if unsure. Never type TBD, Immediate or 'Sept 7-10' here - put the wording in Notes.",
           note="The current committed date. If it moved, keep the first commitment in Original Due Date.", target="tasks.due_date"),
    Column("Duration (days)", "duration_days", "integer", aliases=("Duration", "Days"), width=10, example="", vkind="int",
           prompt="Whole days, used only when one of Start/Due is blank.", target="derived: fills the missing date"),
    Column("Original Due Date", "baseline_due_date", "date",
           aliases=("Baseline Due", "Baseline Finish", "Original Deadline"), width=13, example="15-09-2026", vkind="date",
           prompt="Optional. The date first committed, if Due Date has since been revised. Blank = same as Due Date.",
           note="Becomes the baseline once and is never overwritten later. App Owner import only; a Manager's import leaves it for the Owner.",
           target="tasks.baseline_due_date"),
    Column("Status", "status", "enum", allowed=tuple(label for label, _ in STATUS_LABELS), width=16,
           example="Assigned", vkind="list",
           prompt="Pick from the list. Blank = Draft (Assigned when Owner Email is filled). Delayed / On hold / Cancelled / Abandoned / Reopened need a Reason.",
           note="Completed, Submitted, On hold and Reopened are accepted on first import only; later changes need their lifecycle action in Astra.",
           target="tasks.status"),
    Column("% Complete", "progress", "integer", aliases=("Percent Complete", "Progress", "PercentComplete", "Complete %"),
           width=10, example="0", vkind="percent",
           prompt="Optional. Whole number 0-100 (type 40, not 40%). Astra never invents a percentage.",
           note="Declared progress; separate from accepted-step roll-up.", target="tasks.progress"),
    Column("Criticality", "criticality", "enum", allowed=CRITICALITY_LABELS, width=12, example="High", vkind="list",
           prompt="Optional. Critical, High, Normal or Low. Blank = Unrated (shown as such).",
           note="Changing it on re-import needs a Reason.", target="tasks.criticality"),
    Column("Predecessors", "predecessors", "string_list", aliases=("Depends On", "Predecessor Keys", "Blocked By"),
           width=18, example="EX-001", vkind="key_list",
           prompt="Optional. Import Keys this row waits for, separated by ; (finish-to-start). Example: RA-001; RA-002",
           note="Finish-to-start only today. SS/FF/SF suffixes and lags (RA-001SS+2d) are kept in Notes until Astra supports them.",
           target="task_dependencies (finish_to_start)"),
    Column("Milestone", "milestone", "boolean", allowed=("Yes", "No"), width=10, example="No", vkind="list",
           prompt="Yes / No (superseded by Type).", target="tasks.is_milestone"),
    Column("Next Action / Decision Needed", "next_action", "string",
           aliases=("Next Action", "Next Step", "Decision / Support Required", "Decision / Support"), width=34,
           example="Confirm the evidence checklist with the registrar", vkind="short",
           prompt="Optional, up to 200 characters. The very next step, or the decision / support the owner needs from leadership.",
           note="Shown as the task's Next action while the task is open.", target="tasks.next_action_note"),
    Column("Reason (if delayed or changed)", "reason", "string",
           aliases=("Reason", "Reason if Delayed / At Risk", "Change Reason"), width=28,
           example="Two departments returned receipts a week late", vkind="long",
           prompt="Why the status or dates changed. Required for Delayed / On hold / Cancelled / Abandoned / Reopened and for any date, status or criticality change on re-import.",
           note="Recorded in the task's audit trail.", target="task_events.reason"),
    Column("Notes", "notes", "text", aliases=("Comments", "Remarks"), width=40,
           example="Example row - see README. Source minute: Board 28-08-2026 item 4.", vkind="long",
           prompt="Optional. Anything Astra has no column for: the original prose date (TBD, Ongoing), a group owner, context.",
           note="Appended to the description as a 'Notes:' section; nothing in the sheet is silently lost.",
           target="tasks.description (Notes: section)"),
    Column("Attachment Links", "attachment_links", "string_list", aliases=("Attachments", "Links", "Evidence Links"),
           width=30, example="", vkind="long",
           prompt="Paths or URLs separated by ;  App Owner import only.", target="task_attachments"),
)
COLUMN_BY_KEY = {column.key: column for column in COLUMNS}

# The "Full" preset (workbook v2, 2026-09-22): 18 of 25 columns on. The App Owner
# switches presets or single columns in Template settings; custom columns keep the
# x_ prefix.
FULL_TEMPLATE_COLUMNS: tuple[dict, ...] = (
    {"key": "import_key", "label": "Import Key", "enabled": True, "custom": False},
    {"key": "title", "label": "Title", "enabled": True, "custom": False},
    {"key": "x_type", "label": "Type", "enabled": True, "custom": True, "type": "list",
     "values": list(TYPE_LABELS), "required": False},
    {"key": "parent_key", "label": "Parent Key", "enabled": True, "custom": False},
    {"key": "owner_email", "label": "Owner Email", "enabled": True, "custom": False},
    {"key": "collaborators", "label": "Collaborators", "enabled": True, "custom": False},
    {"key": "start_date", "label": "Start Date", "enabled": True, "custom": False},
    {"key": "due_date", "label": "Due Date", "enabled": True, "custom": False},
    {"key": "baseline_due_date", "label": "Original Due Date", "enabled": True, "custom": False},
    {"key": "status", "label": "Status", "enabled": True, "custom": False},
    {"key": "progress", "label": "% Complete", "enabled": True, "custom": False},
    {"key": "criticality", "label": "Criticality", "enabled": True, "custom": False},
    {"key": "predecessors", "label": "Predecessors", "enabled": True, "custom": False},
    {"key": "next_action", "label": "Next Action / Decision Needed", "enabled": True, "custom": False},
    {"key": "reason", "label": "Reason (if delayed or changed)", "enabled": True, "custom": False},
    {"key": "x_risk_dependency", "label": "Risk / Dependency", "enabled": True, "custom": True, "type": "text",
     "values": [], "required": False},
    {"key": "description", "label": "Description", "enabled": True, "custom": False},
    {"key": "notes", "label": "Notes", "enabled": True, "custom": False},
    {"key": "duration_days", "label": "Duration (days)", "enabled": False, "custom": False},
    {"key": "reviewers", "label": "Reviewers", "enabled": False, "custom": False},
    {"key": "approvers", "label": "Approvers", "enabled": False, "custom": False},
    {"key": "attachment_links", "label": "Attachment Links", "enabled": False, "custom": False},
    {"key": "project", "label": "Project", "enabled": False, "custom": False},
    {"key": "entity", "label": "Entity", "enabled": False, "custom": False},
    {"key": "milestone", "label": "Milestone", "enabled": False, "custom": False},
)
# The "Simple" preset is the built-in default (Aly, 2026-09-22): nine columns, keys
# pre-filled in the template. Every other column stays defined but off.
SIMPLE_ENABLED: tuple[tuple[str, str], ...] = (
    ("import_key", "Import Key"), ("title", "Title"), ("parent_key", "Step of (Key)"), ("owner_email", "Owner Email"),
    ("start_date", "Start Date"), ("due_date", "Due Date"), ("status", "Status"), ("criticality", "Criticality"),
    ("notes", "Notes"),
)
SIMPLE_TEMPLATE_COLUMNS: tuple[dict, ...] = tuple(
    [{"key": key, "label": label, "enabled": True, "custom": False} for key, label in SIMPLE_ENABLED]
    + [{**item, "enabled": False} for item in FULL_TEMPLATE_COLUMNS if item["key"] not in {k for k, _ in SIMPLE_ENABLED}]
)
PRESETS = {"simple": SIMPLE_TEMPLATE_COLUMNS, "full": FULL_TEMPLATE_COLUMNS}
DEFAULT_TEMPLATE_COLUMNS = SIMPLE_TEMPLATE_COLUMNS
SIMPLE_KEYS = frozenset(key for key, _ in SIMPLE_ENABLED)
SIMPLE_PROMPTS = {
    "import_key": "Filled in for you (T-001, T-002 ...) as soon as you type the Title. You may overwrite it with your own short id (letters, digits, . _ -, no spaces, unique). Keep it the same on every re-upload.",
    "title": "Required. The task, step or action item, up to 200 characters. One row each.",
    "parent_key": "Optional. The Import Key of the task this row is a step of (for example T-001). Leave blank for a top-level task.",
    "notes": "Optional. Anything else: the decision or support needed, a risk, the wording of an unknown date (TBD), who else helps.",
}
TYPE_COLUMN_KEY = "x_type"           # custom list column whose "Milestone" value sets tasks.is_milestone
CUSTOM_PROMPTS = {
    "x_type": ("Task = ordinary work. Milestone = zero-length event (Start = Due). Action item = a committed follow-up from a meeting. Blank = Task.",
               "Milestone rows are drawn as zero-length events and their moves are Owner-protected.",
               "Milestone -> tasks.is_milestone; label kept in tasks.import_extras"),
    "x_risk_dependency": ("Optional. One line on what could derail this row or what it depends on outside this plan.",
                          "Kept with the task (read-only) until Astra has a RAID register.",
                          "tasks.import_extras['x_risk_dependency']"),
}

_STATUS_BY_LABEL = {label.casefold(): code for label, code in STATUS_LABELS}
STATUS_LABEL_BY_CODE = {code: label for label, code in STATUS_LABELS}
NOTES_MARKER = "Notes:\n"


def notes_section(description: str) -> str:
    """The text the importer filed under "Notes:" in a task description, or ''."""
    index = (description or "").find(NOTES_MARKER)
    return description[index + len(NOTES_MARKER):].strip() if index >= 0 else ""
STATUS_SYNONYMS = {
    **_STATUS_BY_LABEL,
    **{code.replace("_", " "): code for _, code in STATUS_LABELS},
    **{code: code for _, code in STATUS_LABELS},
    "not started": "unstarted", "to do": "unstarted", "todo": "unstarted", "open": "unstarted", "new": "unstarted",
    "planned": "unstarted", "wip": "in_progress", "ongoing": "in_progress", "started": "in_progress",
    "active": "in_progress", "done": "completed", "complete": "completed", "closed": "completed",
    "finished": "completed", "delayed/at risk": "delayed", "at risk": "delayed", "late": "delayed",
    "overdue": "delayed", "blocked": "on_hold", "hold": "on_hold", "paused": "on_hold", "dropped": "cancelled",
    "canceled": "cancelled",
}
CRITICALITY_SYNONYMS = {
    "critical": "critical", "high": "high", "normal": "normal", "low": "low", "urgent": "critical",
    "p1": "critical", "p2": "high", "p3": "normal", "p4": "low", "medium": "normal", "unrated": None, "none": None,
}
TRUE_WORDS = {"yes", "y", "true", "1", "✓", "x", "milestone"}
FALSE_WORDS = {"no", "n", "false", "0"}

# Mirrors service.GOVERNED_STATUSES / PROTECTED_STATUSES / MANAGER_ORDINARY_STATUSES;
# duplicated so this module has no import cycle with service.py.
GOVERNED = {"submitted", "completed", "on_hold", "reopened"}
PROTECTED = {"changes_requested", "completed", "on_hold", "cancelled", "abandoned", "reopened"}
# Statuses an import never sets on an existing task, Owner included: each needs the
# record its lifecycle action writes (a submission, a checkpoint, a hold note).
NO_IMPORT_ON_UPDATE = GOVERNED | {"changes_requested"}
MANAGER_ORDINARY = {"draft", "assigned", "in_progress", "delayed"}
NO_RECORD_ON_CREATE = {"submitted", "changes_requested", "completed", "on_hold", "reopened"}
CLOSED = {"completed", "cancelled", "abandoned"}
# Statuses an import may not move a task OUT of either (review AS-2): leaving them needs the
# record the lifecycle action writes (reopen, acceptance, hold release), so the stored status
# is kept - W_GOVERNED_STATUS for the Owner, W_PROTECTED_STATUS for a Manager.
LOCKED_SOURCE = GOVERNED | PROTECTED | CLOSED


class ImportFileError(ValueError):
    """The whole file is unusable (format, headers, limits)."""


class ImportConflict(ValueError):
    """The bytes sent to commit differ from the previewed bytes, or another writer
    took an Import Key while the commit ran (HTTP 409)."""


class ImportTooLarge(ImportFileError):
    """The upload, or what the workbook would inflate to, is above the limits (HTTP 413)."""


# --------------------------------------------------------------------------- helpers

def normalize_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, date):
        return display_date(value.isoformat())
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, CellError):
        return value.message
    return clean_text(unicodedata.normalize("NFC", str(value))).strip()


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def split_list(value) -> list[str]:
    text = normalize_text(value)
    if not text:
        return []
    return [item.strip() for item in text.split(LIST_SEPARATOR) if item.strip()]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plan_fingerprint(engine) -> str:
    """What the validated plan would do: sha256 over the sorted (Import Key, action, existing
    task id) triples. Preview returns it and commit compares it, so a plan that changed under
    the same bytes (a key taken by a hand-made task, a task edited meanwhile) is refused
    instead of silently turning a create into an update (review DI-3)."""
    items = sorted((result.key, result.action, (result.existing or {}).get("id") or "") for result in engine.rows)
    return hashlib.sha256(json.dumps(items, ensure_ascii=False).encode("utf-8")).hexdigest()


def excel_serial(day: date) -> int:
    return (day - EXCEL_EPOCH).days


def display_date(iso: str | None) -> str:
    """ISO yyyy-mm-dd -> dd-mm-yyyy for this feature's screens and reports."""
    if not iso:
        return ""
    try:
        parsed = date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    return parsed.strftime("%d-%m-%Y")


def slug_key(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_")
    return CUSTOM_PREFIX + (slug or "column")[:40]


# Characters XML 1.0 forbids even when escaped: C0 controls other than tab, LF and CR, lone
# surrogates and U+FFFE/U+FFFF. escape() leaves them in place, so one such byte in a task title
# made the Owner's pre-filled workbook unreadable (regression review SECURITY-3).
ILLEGAL_TEXT = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def clean_text(text) -> str:
    """Drop the characters no workbook or CSV cell may carry; every string written to a file
    or read from an upload passes through here (normalize_text, _xml, _xml_text, the CSV writers)."""
    return ILLEGAL_TEXT.sub("", str(text))


def _xml(text: str) -> str:
    """Escape for attribute values (quotes included)."""
    return escape(clean_text(text), {'"': "&quot;"})


def _xml_text(text: str) -> str:
    """Escape for element text, where quotes may stay literal."""
    return escape(clean_text(text))


def _protection_hash(password: str, salt: bytes, spin: int) -> str:
    digest = hashlib.sha512(salt + password.encode("utf-16-le")).digest()
    for index in range(spin):
        digest = hashlib.sha512(digest + struct.pack("<I", index)).digest()
    return base64.b64encode(digest).decode("ascii")


# --------------------------------------------------------------------------- template configuration

@dataclass
class ActiveColumn:
    key: str
    label: str
    kind: str                      # built-in kinds or custom text|number|date|list
    custom: bool
    required: bool = False
    values: tuple = ()
    builtin: Column | None = None

    @property
    def prompt(self) -> str:
        if self.builtin:
            return self.builtin.prompt or self.builtin.kind
        if self.key in CUSTOM_PROMPTS:
            return CUSTOM_PROMPTS[self.key][0]
        if self.kind == "list":
            return "Pick from the list: " + ", ".join(self.values)
        if self.kind == "date":
            return "A real date (dd-mm-yyyy; type yyyy-mm-dd if unsure)."
        if self.kind == "number":
            return "A number."
        return "Free text, up to 4000 characters."

    @property
    def note(self) -> str:
        if self.builtin:
            return self.builtin.note
        return CUSTOM_PROMPTS.get(self.key, ("", "", ""))[1]

    @property
    def target(self) -> str:
        if self.builtin:
            return self.builtin.target
        return CUSTOM_PROMPTS.get(self.key, ("", "", f"tasks.import_extras['{self.key}']"))[2]

    @property
    def vkind(self) -> str:
        if self.builtin:
            return self.builtin.vkind
        return {"list": "list", "date": "date", "number": "number"}.get(self.kind, "long")

    @property
    def core(self) -> bool:
        return self.key in CORE_KEYS

    @property
    def width(self) -> int:
        if self.builtin:
            return self.builtin.width
        return {"list": 14, "date": 13, "number": 12}.get(self.kind, 30)

    @property
    def example(self) -> str:
        return self.builtin.example if self.builtin else ""


class TemplateConfig:
    """The Owner-editable shape of the import template.

    ``columns`` lists every built-in column (enabled or not) plus custom columns,
    in template order. Core columns cannot be disabled or renamed.
    """

    def __init__(self, columns: list[dict]):
        self.columns = columns
        self.active: list[ActiveColumn] = []
        for item in columns:
            if not item.get("enabled", True):
                continue
            if item.get("custom"):
                self.active.append(ActiveColumn(
                    key=item["key"], label=item["label"], kind=item["type"], custom=True,
                    required=bool(item.get("required")), values=tuple(item.get("values") or ()),
                ))
            else:
                builtin = COLUMN_BY_KEY[item["key"]]
                self.active.append(ActiveColumn(
                    key=builtin.key, label=item.get("label") or builtin.header, kind=builtin.kind, custom=False,
                    required=builtin.required, values=builtin.allowed, builtin=builtin,
                ))
        self.by_key = {column.key: column for column in self.active}

    @classmethod
    def default(cls) -> "TemplateConfig":
        return cls.preset("simple")

    @classmethod
    def preset(cls, name: str) -> "TemplateConfig":
        if name not in PRESETS:
            raise ValueError(f"Unknown preset '{name}'. Use one of: {', '.join(PRESETS)}.")
        return cls.normalize([dict(item) for item in PRESETS[name]])

    def is_extended(self) -> bool:
        """True when anything beyond the Simple preset's nine columns is enabled."""
        return any(column.key not in SIMPLE_KEYS for column in self.active)

    @classmethod
    def from_json(cls, text: str | None) -> "TemplateConfig":
        if not text:
            return cls.default()
        data = json.loads(text)
        return cls.normalize(data.get("columns", []))

    @staticmethod
    def normalize(raw_columns) -> "TemplateConfig":
        """Validate a submitted column list and return a config; raises ValueError."""
        if not isinstance(raw_columns, list):
            raise ValueError("columns must be a list.")
        columns: list[dict] = []
        seen_keys: set[str] = set()
        seen_labels: dict[str, str] = {}
        for raw in raw_columns:
            if not isinstance(raw, dict):
                raise ValueError("Each column must be an object.")
            key = str(raw.get("key") or "").strip()
            label = unicodedata.normalize("NFC", str(raw.get("label") or "")).strip()
            custom = bool(raw.get("custom")) or key.startswith(CUSTOM_PREFIX) or (key and key not in COLUMN_BY_KEY)
            if custom:
                if not label:
                    raise ValueError("A custom column needs a label.")
                if len(label) > MAX_LABEL_CHARS:
                    raise ValueError(f"Column label '{label}' is longer than {MAX_LABEL_CHARS} characters.")
                if not key or not key.startswith(CUSTOM_PREFIX):
                    key = slug_key(label)
                elif not CUSTOM_KEY_PATTERN.match(key):
                    # The key names a defined range and a validation formula in the workbook.
                    raise ValueError(f"Column '{label}': key '{key}' must be x_ followed by 1-40 lower-case letters, digits or underscores.")
                base, suffix = key, 2
                while key in seen_keys or key in COLUMN_BY_KEY:
                    tail = f"_{suffix}"
                    key = base[:len(CUSTOM_PREFIX) + 40 - len(tail)] + tail
                    suffix += 1
                kind = str(raw.get("type") or "text").strip().casefold()
                if kind not in CUSTOM_TYPES:
                    raise ValueError(f"Column '{label}': type must be one of {', '.join(CUSTOM_TYPES)}.")
                values = []
                if kind == "list":
                    for value in raw.get("values") or []:
                        text = unicodedata.normalize("NFC", str(value)).strip()
                        if text and text not in values:
                            values.append(text)
                    if not values:
                        raise ValueError(f"Column '{label}': a list column needs at least one allowed value.")
                    if any("," in value or '"' in value for value in values):
                        raise ValueError(f"Column '{label}': list values may not contain commas or quotes.")
                    if len(",".join(values)) > MAX_LIST_LITERAL:
                        raise ValueError(f"Column '{label}': the list is too long for an Excel dropdown ({MAX_LIST_LITERAL} characters).")
                item = {
                    "key": key, "label": label, "enabled": bool(raw.get("enabled", True)), "custom": True,
                    "type": kind, "values": values, "required": bool(raw.get("required")),
                }
            else:
                if key not in COLUMN_BY_KEY:
                    raise ValueError(f"Unknown built-in column '{key}'.")
                builtin = COLUMN_BY_KEY[key]
                enabled = bool(raw.get("enabled", True))
                if key in CORE_KEYS:
                    if not enabled:
                        raise ValueError(f"'{builtin.header}' is a core column and cannot be disabled.")
                    if label and label != builtin.header:
                        raise ValueError(f"'{builtin.header}' is a core column and cannot be renamed.")
                    label = builtin.header
                label = label or builtin.header
                if len(label) > MAX_LABEL_CHARS:
                    raise ValueError(f"Column label '{label}' is longer than {MAX_LABEL_CHARS} characters.")
                item = {"key": key, "label": label, "enabled": enabled, "custom": False}
            if key in seen_keys:
                raise ValueError(f"Column '{label}' appears twice.")
            seen_keys.add(key)
            if item["enabled"]:
                folded = collapse(label)
                if folded in seen_labels:
                    raise ValueError(f"Two columns share the label '{label}'.")
                seen_labels[folded] = key
            columns.append(item)
        for builtin in COLUMNS:  # every built-in stays listed so it can be re-enabled
            if builtin.key not in seen_keys:
                if builtin.key in CORE_KEYS:
                    raise ValueError(f"'{builtin.header}' is a core column and must stay in the template.")
                columns.append({"key": builtin.key, "label": builtin.header, "enabled": False, "custom": False})
        enabled_count = sum(1 for item in columns if item["enabled"])
        if enabled_count > MAX_COLUMNS:
            raise ValueError(f"The template may have at most {MAX_COLUMNS} columns; {enabled_count} are enabled.")
        return TemplateConfig(columns)

    def to_dict(self) -> dict:
        return {
            "columns": [dict(item) for item in self.columns],
            "core_keys": list(CORE_KEYS),
            "hash": self.hash(),
            "labels": list(self.labels()),
            "presets": {name: [item["key"] for item in columns if item["enabled"]] for name, columns in PRESETS.items()},
            "extended": self.is_extended(),
        }

    def to_json(self) -> str:
        return json.dumps({"columns": self.columns}, sort_keys=True, ensure_ascii=False)

    def hash(self) -> str:
        """Version marker written into the template: changes whenever the active shape changes."""
        shape = [
            [column.key, column.label, column.kind, list(column.values), column.required]
            for column in self.active
        ]
        return hashlib.sha256(json.dumps(shape, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]

    def labels(self) -> tuple:
        return tuple(column.label for column in self.active)

    def fingerprint(self) -> str:
        """Header fingerprint written to _astra!B2 (labels only; informational)."""
        return hashlib.sha256("|".join(self.labels()).encode("utf-8")).hexdigest()[:16]

    def match_header(self, text: str):
        """Return (column, matched_by_alias) for a header cell, or (None, False)."""
        wanted = collapse(text)
        if not wanted:
            return None, False
        for column in self.active:
            if collapse(column.label) == wanted:
                return column, False
        for column in self.active:
            if column.builtin and (
                collapse(column.builtin.header) == wanted
                or any(collapse(alias) == wanted for alias in column.builtin.aliases)
            ):
                return column, True
        return None, False


# --------------------------------------------------------------------------- template workbook (v2)
#
# Seven sheets: README (locked), Project (label / value / guidance; Value column
# unlocked), Tasks (header row 1 from the configuration, 2,000 unlocked data rows,
# frozen header, autofilter, dropdowns from named ranges, date and shape rules),
# Example (three worked rows, fully locked), People (email, name, role, notes, a
# computed "Used in Tasks" count), Lists (hidden; the named ranges the dropdowns
# read) and _astra (veryHidden; B1 configuration hash, B2 header fingerprint, B3
# template family, B4 build time). Written with zipfile only. Header hover
# comments from the openpyxl reference need a VML part and are not emitted; their
# text lives in the input messages and the README dictionary instead.

TEMPLATE_FAMILY = "astra-import-v2"
SIMPLE_FAMILY = "astra-import-simple"
PROJECT_SHEET = "Project"
PEOPLE_SHEET = "People"
EXAMPLE_SHEET = "Example"
LISTS_SHEET = "Lists"
PEOPLE_ROWS = 200
NAVY, SLATE, TEAL, PALE_RED, GREY, PALE_GREY, BAND, WHITE = (
    "FF172A46", "FF475467", "FF0F6E6E", "FFFEE4E2", "FF667085", "FFF2F4F7", "FFF8FAFC", "FFFFFFFF")

# cellXfs indices written by _styles_xml
XF_LOCKED, XF_HEAD_CORE, XF_HEAD_OPTIONAL, XF_HEAD_CUSTOM = 0, 1, 2, 3
XF_TEXT, XF_DATE, XF_INT, XF_NUMBER, XF_CENTER = 4, 5, 6, 7, 8
XF_WRAP_LOCKED, XF_EX_TEXT, XF_EX_DATE, XF_EX_CENTER, XF_TITLE, XF_SUBTLE = 9, 10, 11, 12, 13, 14
XF_LABEL_REQ, XF_LABEL, XF_GUIDANCE, XF_FORMULA, XF_HEAD_SLATE_PLAIN, XF_DATE_LOCKED = 15, 16, 17, 18, 19, 20

PROJECT_FIELDS = (
    # (label, kind, required, guidance, astra target)
    ("Project Name", "text", True, "The project as it should appear in Astra. Pick the same project on the Import screen; the App Owner may create it from this row.", "projects.name"),
    ("Description", "long", False, "One paragraph: purpose, scope, the meeting or mandate it comes from.", "projects.description"),
    ("Filing Entity", "list:Lists_Entity", False, "The approved entity this project rolls up to. Leave blank if unsure; the App Owner files it in Astra.", "project_entities (App Owner only)"),
    ("Project Manager Email", "email", False, "The person who manages the project day to day. Must already exist in Astra (see People).", "projects.manager_user_id + memberships(role=manager)"),
    ("Sponsor / Executive Owner Email", "email", False, "The executive accountable for the outcome.", "not stored yet - written into the description on import"),
    ("Timezone", "list:Lists_Timezone", False, "Governs what 'end of day' means for due dates. Default Asia/Karachi.", "projects.timezone"),
    ("Working Days", "list:Lists_WorkingDays", False, "Which weekdays count as working days. Default: Every day (Astra's permissive calendar).", "projects.working_days"),
    ("Planned Start Date", "date", False, "First planned working day of the project (dd-mm-yyyy; type yyyy-mm-dd if unsure).", "projects.start_date"),
    ("Planned Finish Date", "date", False, "Target completion date (informational; never constrains tasks).", "projects.target_date"),
    ("Plan As-of Date", "date", False, "The date this plan was last reviewed (for example the meeting date).", "import record note"),
    ("Source Document", "text", False, "Original file, version or minute reference this workbook was built from.", "import record note"),
    ("Prepared By Email", "email", False, "Who filled this workbook in.", "informational; the importer records the logged-in user"),
)
SIMPLE_PROJECT_FIELDS = (
    ("Project Name", "text", True, "The project as it should appear in Astra. Pick the same project on the Import screen; the App Owner may create it from this row.", "projects.name"),
    ("Project Manager Email", "email", False, "Who runs the project day to day. Must already exist in Astra.", "projects.manager_user_id"),
    ("Timezone", "list:Lists_Timezone", False, "What 'end of day' means for due dates. Default Asia/Karachi.", "projects.timezone"),
)
PROJECT_FIELD_KEYS = {
    "Project Name": "name", "Description": "description", "Filing Entity": "entity",
    "Project Manager Email": "manager_email", "Sponsor / Executive Owner Email": "sponsor_email",
    "Timezone": "timezone", "Working Days": "working_days", "Planned Start Date": "start_date",
    "Planned Finish Date": "target_date", "Plan As-of Date": "as_of_date", "Source Document": "source_document",
    "Prepared By Email": "prepared_by_email",
}
PEOPLE_HEADERS = (
    ("Email", 30, "Work email exactly as the App Owner created it in Astra. This is what Tasks!Owner Email must match."),
    ("Full Name", 26, "Display name for the App Owner to use when creating the account."),
    ("Role on project", 16, "Manager (runs the project, may import), Member (does work) or Viewer (read only)."),
    ("Notes", 40, "Anything the App Owner needs: team, title, whether the account already exists."),
    ("Used in Tasks", 13, "Computed: how many Tasks rows name this email as Owner or Collaborator. 0 = not referenced."),
)
SIMPLE_EXAMPLE_ROWS = (
    {"import_key": "EX-001", "title": "Submit accreditation application and upload the evidence receipt",
     "owner_email": "jamal@example.org", "start_date": date(2026, 9, 1), "due_date": date(2026, 9, 15), "status": "Assigned",
     "criticality": "High", "notes": "Example row. Decision needed: confirm the evidence checklist with the registrar."},
    {"import_key": "EX-001.1", "title": "Collect signed evidence receipts from all departments", "parent_key": "EX-001",
     "owner_email": "waseem@example.org", "start_date": date(2026, 9, 1), "due_date": date(2026, 9, 12), "status": "In progress",
     "criticality": "Normal", "notes": "A step: 'Step of (Key)' points at EX-001."},
)
EXAMPLE_ROWS = (
    {"import_key": "EX-001", "title": "Submit accreditation application and upload the evidence receipt", "x_type": "Task",
     "owner_email": "jamal@example.org", "collaborators": "waseem@example.org", "start_date": date(2026, 9, 1),
     "due_date": date(2026, 9, 15), "baseline_due_date": date(2026, 9, 15), "status": "Assigned", "progress": 0,
     "criticality": "High", "next_action": "Confirm the evidence checklist with the registrar",
     "x_risk_dependency": "Portal closes 20-09-2026; late submission slips a full cycle",
     "description": "Application for Career-related Programme candidacy. Acceptance: receipt uploaded to the shared drive.",
     "notes": "Example row - see README. Source minute: Board 28-08-2026 item 4.", "milestone": "No"},
    {"import_key": "EX-001.1", "title": "Collect signed evidence receipts from all departments", "x_type": "Action item",
     "parent_key": "EX-001", "owner_email": "waseem@example.org", "collaborators": "sajjad@example.org; jamal@example.org",
     "start_date": date(2026, 9, 1), "due_date": date(2026, 9, 12), "baseline_due_date": date(2026, 9, 8),
     "status": "Delayed", "progress": 40, "criticality": "Normal",
     "next_action": "Chase the two departments that have not signed", "reason": "Two departments returned receipts a week late",
     "notes": "A step: Parent Key points at EX-001. Original Due Date kept because Due Date moved.", "duration_days": 12},
    {"import_key": "EX-002", "title": "Board approves the final DP/CP subject list", "x_type": "Milestone",
     "owner_email": "aly@example.org", "start_date": date(2026, 9, 30), "due_date": date(2026, 9, 30), "status": "Assigned",
     "criticality": "Critical", "predecessors": "EX-001", "next_action": "Table the subject list at the September board meeting",
     "notes": "A milestone: Start = Due. Waits for EX-001 (finish-to-start).", "milestone": "Yes"},
)


def _inline(ref: str, text: str, style: int) -> str:
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{_xml_text(text)}</t></is></c>'


def _number(ref: str, value, style: int) -> str:
    return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'


def _formula(ref: str, formula: str, style: int) -> str:
    # No cached <v>: Excel computes on open (workbook has fullCalcOnLoad).
    return f'<c r="{ref}" s="{style}" t="str"><f>{_xml_text(formula)}</f></c>'


def _cell(ref: str, value, style_text: int, style_date: int, style_number: int) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, date):
        return _number(ref, excel_serial(value), style_date)
    if isinstance(value, bool):
        return _inline(ref, "Yes" if value else "No", style_text)
    if isinstance(value, (int, float)):
        return _number(ref, value, style_number)
    return _inline(ref, str(value), style_text)


def _protection_xml(hash_value: str, salt_value: str, spin: int, *, allow_rows: bool = False,
                    allow_filter: bool = False) -> str:
    # In <sheetProtection> a "1" LOCKS the action. Widening columns stays allowed
    # everywhere; adding or removing rows and filtering only where asked for.
    rows = "0" if allow_rows else "1"
    return (
        f'<sheetProtection algorithmName="SHA-512" hashValue="{hash_value}" saltValue="{salt_value}" '
        f'spinCount="{spin}" sheet="1" objects="1" scenarios="1" formatCells="1" formatColumns="0" '
        f'formatRows="{rows}" insertColumns="1" insertRows="{rows}" insertHyperlinks="1" deleteColumns="1" '
        f'deleteRows="{rows}" sort="1" autoFilter="{"0" if allow_filter else "1"}" pivotTables="1" '
        f'selectLockedCells="0" selectUnlockedCells="0"/>'
    )


def _validation(kind: str, sqref: str, prompt_title: str, prompt: str, error: str, *, style: str = "stop", **attrs) -> str:
    formulas = ""
    if "formula1" in attrs:
        formulas += f"<formula1>{_xml_text(attrs.pop('formula1'))}</formula1>"
    if "formula2" in attrs:
        formulas += f"<formula2>{_xml_text(attrs.pop('formula2'))}</formula2>"
    extra = "".join(f' {name}="{_xml(value)}"' for name, value in attrs.items())
    return (
        f'<dataValidation type="{kind}"{extra} allowBlank="1" showInputMessage="1" showErrorMessage="1" '
        f'errorStyle="{style}" errorTitle="Astra import template" error="{_xml(error[:255])}" '
        f'promptTitle="{_xml(prompt_title[:32])}" prompt="{_xml(prompt[:255])}" sqref="{sqref}">{formulas}</dataValidation>'
    )


def _cf_rule(sqref: str, formula: str, dxf: int, priority: int) -> str:
    return (f'<conditionalFormatting sqref="{sqref}"><cfRule type="expression" dxfId="{dxf}" priority="{priority}">'
            f'<formula>{_xml_text(formula)}</formula></cfRule></conditionalFormatting>')


def _sheet(body: str, *, tab: str | None = None) -> str:
    pr = f'<sheetPr><tabColor rgb="{tab}"/></sheetPr>' if tab else ""
    return (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' + pr + body + '</worksheet>'
    )


def _styles_xml() -> str:
    def xf(num_fmt=0, font=0, fill=0, *, unlocked=False, align="", border=1):
        attrs = f'numFmtId="{num_fmt}" fontId="{font}" fillId="{fill}" borderId="{border}" xfId="0"'
        if num_fmt:
            attrs += ' applyNumberFormat="1"'
        if font:
            attrs += ' applyFont="1"'
        if fill:
            attrs += ' applyFill="1"'
        if align:
            attrs += ' applyAlignment="1"'
        if unlocked:
            attrs += ' applyProtection="1"'
        inner = (f"<alignment {align}/>" if align else "") + ('<protection locked="0"/>' if unlocked else "")
        return f"<xf {attrs}>{inner}</xf>" if inner else f"<xf {attrs}/>"

    wrap, center, top = 'wrapText="1" vertical="top"', 'horizontal="center" vertical="top"', 'vertical="top"'
    head = 'horizontal="center" vertical="center" wrapText="1"'
    xfs = [
        xf(),                                                   # 0 locked default
        xf(0, 1, 2, align=head),                                # 1 header core (navy)
        xf(0, 1, 3, align=head),                                # 2 header optional (slate)
        xf(0, 1, 4, align=head),                                # 3 header custom (teal)
        xf(0, 0, 0, unlocked=True, align=wrap),                 # 4 unlocked text
        xf(164, 0, 0, unlocked=True, align=center),             # 5 unlocked date
        xf(1, 0, 0, unlocked=True, align=center),               # 6 unlocked integer
        xf(2, 0, 0, unlocked=True, align=center),               # 7 unlocked number
        xf(0, 0, 0, unlocked=True, align=center),               # 8 unlocked centred text (keys, lists)
        xf(0, 0, 0, align=wrap),                                # 9 locked wrapped text
        xf(0, 2, 0, align=wrap),                                # 10 example text (italic grey)
        xf(164, 2, 0, align=center),                            # 11 example date
        xf(0, 2, 0, align=center),                              # 12 example centred
        xf(0, 3, 2, align='vertical="center"', border=0),       # 13 README title (white on navy)
        xf(0, 4, 0, align=wrap, border=0),                      # 14 README subtle grey
        xf(0, 1, 2, align=top),                                 # 15 Project label required (navy)
        xf(0, 5, 5, align=top),                                 # 16 Project label (bold on pale grey)
        xf(0, 4, 0, align=wrap),                                # 17 guidance (grey, wrapped)
        xf(0, 4, 0, align='horizontal="center"'),               # 18 formula cell (grey, locked)
        xf(0, 1, 3, align='vertical="center"'),                 # 19 slate header, no wrap
        xf(164, 0, 0, align=center),                            # 20 locked date
    ]
    return (
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<numFmts count="1"><numFmt numFmtId="164" formatCode="{DISPLAY_DATE_FORMAT}"/></numFmts>'
        '<fonts count="6">'
        '<font><sz val="11"/><color rgb="FF101828"/><name val="Calibri"/></font>'
        f'<font><b/><sz val="11"/><color rgb="{WHITE}"/><name val="Calibri"/></font>'
        f'<font><i/><sz val="11"/><color rgb="{GREY}"/><name val="Calibri"/></font>'
        f'<font><b/><sz val="16"/><color rgb="{WHITE}"/><name val="Calibri"/></font>'
        f'<font><sz val="10"/><color rgb="{GREY}"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><color rgb="FF101828"/><name val="Calibri"/></font>'
        '</fonts>'
        '<fills count="7"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
        f'<fill><patternFill patternType="solid"><fgColor rgb="{NAVY}"/><bgColor indexed="64"/></patternFill></fill>'
        f'<fill><patternFill patternType="solid"><fgColor rgb="{SLATE}"/><bgColor indexed="64"/></patternFill></fill>'
        f'<fill><patternFill patternType="solid"><fgColor rgb="{TEAL}"/><bgColor indexed="64"/></patternFill></fill>'
        f'<fill><patternFill patternType="solid"><fgColor rgb="{PALE_GREY}"/><bgColor indexed="64"/></patternFill></fill>'
        f'<fill><patternFill patternType="solid"><fgColor rgb="{PALE_RED}"/><bgColor indexed="64"/></patternFill></fill>'
        '</fills>'
        '<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>'
        '<border><left style="thin"><color rgb="FFD0D5DD"/></left><right style="thin"><color rgb="FFD0D5DD"/></right>'
        '<top style="thin"><color rgb="FFD0D5DD"/></top><bottom style="thin"><color rgb="FFD0D5DD"/></bottom><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        f'<cellXfs count="{len(xfs)}">{"".join(xfs)}</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        f'<dxfs count="2"><dxf><fill><patternFill patternType="solid"><fgColor rgb="{PALE_RED}"/><bgColor rgb="{PALE_RED}"/></patternFill></fill></dxf>'
        f'<dxf><fill><patternFill patternType="solid"><fgColor rgb="{BAND}"/><bgColor rgb="{BAND}"/></patternFill></fill></dxf></dxfs>'
        '</styleSheet>'
    )


class _TemplateWorkbook:
    """Builds the seven-sheet template for one configuration."""

    def __init__(self, config: TemplateConfig, *, tasks=None, project=None, people=None, key_offset: int = 0):
        self.config = config
        self.columns = config.active
        self.extended = config.is_extended()
        self.family = TEMPLATE_FAMILY if self.extended else SIMPLE_FAMILY
        self.project_fields = PROJECT_FIELDS if self.extended else SIMPLE_PROJECT_FIELDS
        self.example_rows = list(EXAMPLE_ROWS if self.extended else SIMPLE_EXAMPLE_ROWS)
        self.tasks = tasks or []
        self.project = project or {}
        self.people = people or []
        # Pre-filled key formula: T-(ROW()-1+key_offset). A project-scoped download sets the
        # offset so the blank rows below the existing tasks continue above the highest T-nnn in use.
        self.key_offset = int(key_offset or 0)
        self.letter = {column.key: column_letter(index) for index, column in enumerate(self.columns, start=1)}
        self.last_col = column_letter(len(self.columns))
        self.last_row = TEMPLATE_DATA_ROWS + 1
        salt = os.urandom(16)
        self.spin = 100000
        self.hash_value = _protection_hash(TEMPLATE_SHEET_PASSWORD, salt, self.spin)
        self.salt_value = base64.b64encode(salt).decode("ascii")
        self.lists: list[tuple[str, str, tuple]] = [
            ("Lists_Status", "Status", tuple(label for label, _ in STATUS_LABELS)),
            ("Lists_Criticality", "Criticality", CRITICALITY_LABELS),
            ("Lists_Type", "Type", TYPE_LABELS),
            ("Lists_YesNo", "Yes / No", ("Yes", "No")),
            ("Lists_ProjectRole", "Role on project", PROJECT_ROLE_LABELS),
            ("Lists_Timezone", "Timezone", TIMEZONE_LABELS),
            ("Lists_WorkingDays", "Working days", tuple(WORKING_DAY_LABELS)),
            ("Lists_Entity", "Entity", ENTITY_LABELS),
        ]
        for column in self.columns:  # custom list columns get their own named range
            if column.custom and column.kind == "list":
                self.lists.append((f"Lists_{column.key}", column.label, tuple(column.values)))

    def protect(self, **kwargs) -> str:
        return _protection_xml(self.hash_value, self.salt_value, self.spin, **kwargs)

    def prompt(self, column: ActiveColumn) -> str:
        if not self.extended and column.key in SIMPLE_PROMPTS:
            return SIMPLE_PROMPTS[column.key]
        return column.prompt

    def list_name(self, column: ActiveColumn) -> str:
        if column.custom:
            return f"Lists_{column.key}"
        return {"status": "Lists_Status", "criticality": "Lists_Criticality", "milestone": "Lists_YesNo"}.get(column.key, "")

    # ---- Tasks / Example ---------------------------------------------------
    def data_styles(self, column: ActiveColumn, *, example: bool) -> tuple[int, int, int]:
        """(text style, date style, number style) for a data cell of this column."""
        if example:
            return (XF_EX_CENTER if column.vkind in ("key", "key_ref", "list", "percent", "int", "date", "date_due", "number") else XF_EX_TEXT,
                    XF_EX_DATE, XF_EX_CENTER)
        if column.vkind in ("date", "date_due"):
            return XF_DATE, XF_DATE, XF_DATE
        if column.vkind in ("percent", "int"):
            return XF_INT, XF_DATE, XF_INT
        if column.vkind == "number":
            return XF_NUMBER, XF_DATE, XF_NUMBER
        if column.vkind in ("key", "key_ref", "list"):
            return XF_CENTER, XF_DATE, XF_CENTER
        return XF_TEXT, XF_DATE, XF_INT

    def header_row(self) -> str:
        cells = []
        for index, column in enumerate(self.columns, start=1):
            style = XF_HEAD_CUSTOM if column.custom else (XF_HEAD_CORE if column.core else XF_HEAD_OPTIONAL)
            cells.append(_inline(f"{column_letter(index)}1", column.label, style))
        return f'<row r="1" ht="34" customHeight="1">{"".join(cells)}</row>'

    def task_rows(self, rows, *, example: bool) -> str:
        out = []
        styles = [self.data_styles(column, example=example) for column in self.columns]
        last = len(rows) + 1 if example else self.last_row
        for number in range(2, last + 1):
            row = rows[number - 2] if number - 2 < len(rows) else {}
            cells = []
            for index, column in enumerate(self.columns, start=1):
                text_style, date_style, number_style = styles[index - 1]
                ref = f"{column_letter(index)}{number}"
                cell = _cell(ref, row.get(column.key), text_style, date_style, number_style)
                if not cell and column.key == "import_key" and not example:
                    # Pre-filled key: appears as T-001, T-002 ... once the Title is typed; the user may overwrite it.
                    title_col = self.letter["title"]
                    base = f"ROW()-1{self.key_offset:+d}" if self.key_offset else "ROW()-1"
                    cell = _formula(ref, f'IF({title_col}{number}="","","T-"&TEXT({base},"000"))', text_style)
                cells.append(cell or f'<c r="{ref}" s="{text_style}"/>')
            long = any(len(str(value or "")) > 60 for value in row.values())
            height = ' ht="48" customHeight="1"' if row and (example or long) else ""
            out.append(f'<row r="{number}"{height}>{"".join(cells)}</row>')
        return "".join(out)

    def task_validations(self) -> str:
        key_col = self.letter["import_key"]
        start_col = self.letter["start_date"]
        keys_range = f"${key_col}$2:${key_col}${self.last_row}"
        rules = []
        for column in self.columns:
            letter = self.letter[column.key]
            rng = f"{letter}2:{letter}{self.last_row}"
            c = f"{letter}2"
            label, prompt, kind = column.label, self.prompt(column), column.vkind
            if kind == "key":
                rules.append(_validation("custom", rng, label, prompt,
                    "Import Key: 1-40 characters, no spaces, letters/digits/._- only, and unique in this sheet.",
                    formula1=f'AND(LEN({c})>0,LEN({c})<=40,ISERROR(FIND(" ",{c})),COUNTIF({keys_range},{c})=1)'))
            elif kind == "key_ref":
                rules.append(_validation("custom", rng, label, prompt,
                    "Parent Key must be the Import Key of another row in this sheet (or of a task already in Astra - press Yes to keep it).",
                    style="warning", formula1=f'AND({c}<>{key_col}2,COUNTIF({keys_range},{c})=1)'))
            elif kind == "key_list":
                rules.append(_validation("custom", rng, label, prompt,
                    "Separate keys with ; (semicolon), not commas, and do not list the row's own key.",
                    style="warning", formula1=f'AND(ISERROR(FIND(",",{c})),ISERROR(FIND({key_col}2,{c})))'))
            elif kind == "text":
                rules.append(_validation("textLength", rng, label, prompt, f"{label} must be 1 to 200 characters.",
                                         operator="between", formula1="1", formula2="200"))
            elif kind == "short":
                rules.append(_validation("textLength", rng, label, prompt, "Up to 200 characters.",
                                         operator="lessThanOrEqual", formula1="200"))
            elif kind == "long":
                rules.append(_validation("textLength", rng, label, prompt, "Up to 4000 characters.",
                                         operator="lessThanOrEqual", formula1="4000"))
            elif kind == "email":
                rules.append(_validation("custom", rng, label, prompt, "Enter one work email (name@domain), no spaces, no names.",
                    formula1=f'AND(ISNUMBER(FIND("@",{c})),ISERROR(FIND(" ",{c})),ISNUMBER(FIND(".",{c},FIND("@",{c})+1)),ISERROR(FIND(";",{c})),LEN({c})<=254)'))
            elif kind == "email_list":
                rules.append(_validation("custom", rng, label, prompt, "Emails only, separated by ; (semicolon). Names and commas are not accepted.",
                    formula1=f'AND(ISNUMBER(FIND("@",{c})),ISERROR(FIND(",",{c})))'))
            elif kind == "date":
                rules.append(_validation("date", rng, label, prompt,
                    "Enter a real date between 01-01-2000 and 31-12-2100 (type yyyy-mm-dd if unsure). Put TBD or wording in Notes and leave this blank.",
                    operator="between", formula1=str(excel_serial(DATE_MIN)), formula2=str(excel_serial(DATE_MAX))))
            elif kind == "date_due":
                rules.append(_validation("custom", rng, label, prompt,
                    "Due Date must be a real date between 01-01-2000 and 31-12-2100 and not before Start Date. Put TBD or wording in Notes.",
                    formula1=f'AND(ISNUMBER({c}),{c}>=DATE(2000,1,1),{c}<=DATE(2100,12,31),OR({start_col}2="",{c}>={start_col}2))'))
            elif kind == "percent":
                rules.append(_validation("whole", rng, label, prompt, "Enter a whole number from 0 to 100.",
                                         operator="between", formula1="0", formula2="100"))
            elif kind == "int":
                rules.append(_validation("whole", rng, label, prompt, "Enter a whole number of days (1 to 3660).",
                                         operator="between", formula1="1", formula2="3660"))
            elif kind == "number":
                rules.append(_validation("decimal", rng, label, prompt, "Enter a number.",
                                         operator="between", formula1="-1000000000000", formula2="1000000000000"))
            elif kind == "list":
                rules.append(_validation("list", rng, label, prompt, "Choose a value from the dropdown list.",
                                         formula1=self.list_name(column)))
        return f'<dataValidations count="{len(rules)}">{"".join(rules)}</dataValidations>'

    def task_conditional_formats(self) -> str:
        a, t = self.letter["import_key"], self.letter["title"]
        s, d = self.letter["start_date"], self.letter["due_date"]
        row_has_data = f"COUNTA(${a}2:${self.last_col}2)>0"
        return "".join([
            _cf_rule(f"{a}2:{a}{self.last_row}", f'AND(${a}2="",{row_has_data})', 0, 1),
            _cf_rule(f"{t}2:{t}{self.last_row}", f'AND(${t}2="",{row_has_data})', 0, 2),
            _cf_rule(f"{d}2:{d}{self.last_row}", f"AND(ISNUMBER(${s}2),ISNUMBER(${d}2),${d}2<${s}2)", 0, 3),
            _cf_rule(f"{a}2:{self.last_col}{self.last_row}", "MOD(ROW(),2)=0", 1, 4),
        ])

    def tasks_sheet(self, rows, *, example: bool) -> str:
        cols = []
        for index, column in enumerate(self.columns, start=1):
            text_style = self.data_styles(column, example=example)[0]
            style = XF_LOCKED if example else text_style
            cols.append(f'<col min="{index}" max="{index}" width="{column.width}" customWidth="1" style="{style}"/>')
        selected = ' tabSelected="1"' if rows and not example else ""
        body = (
            f'<dimension ref="A1:{self.last_col}{max(1, len(rows) + 1)}"/>'
            f'<sheetViews><sheetView{selected} workbookViewId="0">'
            + ('<pane xSplit="2" ySplit="1" topLeftCell="C2" activePane="bottomRight" state="frozen"/>'
               '<selection pane="topRight" activeCell="C1" sqref="C1"/><selection pane="bottomLeft" activeCell="A2" sqref="A2"/>'
               '<selection pane="bottomRight" activeCell="C2" sqref="C2"/>' if not example else "")
            + '</sheetView></sheetViews><sheetFormatPr defaultRowHeight="15"/>'
            f'<cols>{"".join(cols)}</cols>'
            f'<sheetData>{self.header_row()}{self.task_rows(rows, example=example)}</sheetData>'
        )
        if example:
            body += self.protect()
        else:
            body += self.protect(allow_rows=True, allow_filter=True)
            body += f'<autoFilter ref="A1:{self.last_col}{self.last_row}"/>'
            body += self.task_conditional_formats()
            body += self.task_validations()
        body += '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        return _sheet(body, tab=GREY if example else NAVY)

    # ---- Project ---------------------------------------------------------
    def project_sheet(self) -> str:
        rows = [f'<row r="1" ht="24" customHeight="1">{_inline("A1", "Field", XF_HEAD_SLATE_PLAIN)}'
                f'{_inline("B1", "Value (fill in)", XF_HEAD_SLATE_PLAIN)}{_inline("C1", "Guidance", XF_HEAD_SLATE_PLAIN)}</row>']
        rules = []
        for number, (label, kind, required, guidance, target) in enumerate(self.project_fields, start=2):
            ref = f"B{number}"
            value = self.project.get(PROJECT_FIELD_KEYS[label])
            cells = [_inline(f"A{number}", label + (" *" if required else ""), XF_LABEL_REQ if required else XF_LABEL)]
            if kind == "date":
                cells.append(_cell(ref, value, XF_DATE, XF_DATE, XF_DATE) or f'<c r="{ref}" s="{XF_DATE}"/>')
                rules.append(_validation("date", ref, label, guidance, "Enter a real date (type yyyy-mm-dd if unsure).",
                                         operator="between", formula1=str(excel_serial(DATE_MIN)), formula2=str(excel_serial(DATE_MAX))))
            else:
                cells.append(_cell(ref, value, XF_TEXT, XF_DATE, XF_TEXT) or f'<c r="{ref}" s="{XF_TEXT}"/>')
                if kind.startswith("list:"):
                    rules.append(_validation("list", ref, label, guidance, "Choose from the list.", formula1=kind.split(":", 1)[1]))
                elif kind == "email":
                    rules.append(_validation("custom", ref, label, guidance, "Enter one work email (name@domain).",
                                             formula1=f'AND(ISNUMBER(FIND("@",{ref})),ISERROR(FIND(" ",{ref})))'))
                elif kind == "text":
                    rules.append(_validation("textLength", ref, label, guidance, "1 to 200 characters.",
                                             operator="between", formula1="1", formula2="200"))
                else:
                    rules.append(_validation("textLength", ref, label, guidance, "Up to 4000 characters.",
                                             operator="lessThanOrEqual", formula1="4000"))
            cells.append(_inline(f"C{number}", f"{guidance}  Astra: {target}", XF_GUIDANCE))
            rows.append(f'<row r="{number}" ht="36" customHeight="1">{"".join(cells)}</row>')
        body = (
            f'<dimension ref="A1:C{len(self.project_fields) + 1}"/>'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            '<selection pane="bottomLeft" activeCell="B2" sqref="B2"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="15"/>'
            '<cols><col min="1" max="1" width="30" customWidth="1"/><col min="2" max="2" width="46" customWidth="1"/>'
            '<col min="3" max="3" width="70" customWidth="1"/></cols>'
            f'<sheetData>{"".join(rows)}</sheetData>'
            + self.protect()
            + _cf_rule("B2", '$B$2=""', 0, 1)
            + f'<dataValidations count="{len(rules)}">{"".join(rules)}</dataValidations>'
        )
        return _sheet(body, tab=SLATE)

    # ---- People ----------------------------------------------------------
    def people_sheet(self) -> str:
        owner_col, collab_col = self.letter["owner_email"], self.letter.get("collaborators")
        head = "".join(
            _inline(f"{column_letter(index)}1", text, XF_HEAD_CORE if index <= 2 else XF_HEAD_OPTIONAL)
            for index, (text, _, _) in enumerate(PEOPLE_HEADERS, start=1)
        )
        rows = [f'<row r="1" ht="30" customHeight="1">{head}</row>']
        last = PEOPLE_ROWS + 1
        for number in range(2, last + 1):
            values = self.people[number - 2] if number - 2 < len(self.people) else ()
            cells = []
            for index in range(1, 5):
                value = values[index - 1] if index - 1 < len(values) else ""
                cells.append(_cell(f"{column_letter(index)}{number}", value, XF_TEXT, XF_DATE, XF_TEXT) or "")
            usage = f'COUNTIF(Tasks!${owner_col}$2:${owner_col}${self.last_row},A{number})'
            if collab_col:
                usage += f'+COUNTIF(Tasks!${collab_col}$2:${collab_col}${self.last_row},"*"&A{number}&"*")'
            cells.append(_formula(f"E{number}", f'IF(A{number}="","",{usage})', XF_FORMULA))
            rows.append(f'<row r="{number}">{"".join(cells)}</row>')
        rules = [
            _validation("custom", f"A2:A{last}", "Email", PEOPLE_HEADERS[0][2],
                        "One work email (name@domain), no spaces, unique in this sheet.",
                        formula1=f'AND(ISNUMBER(FIND("@",A2)),ISERROR(FIND(" ",A2)),COUNTIF($A$2:$A${last},A2)=1)'),
            _validation("textLength", f"B2:B{last}", "Full Name", PEOPLE_HEADERS[1][2], "1 to 120 characters.",
                        operator="between", formula1="1", formula2="120"),
            _validation("list", f"C2:C{last}", "Role on project", PEOPLE_HEADERS[2][2], "Choose Manager, Member or Viewer.",
                        formula1="Lists_ProjectRole"),
        ]
        cols = "".join(
            f'<col min="{index}" max="{index}" width="{width}" customWidth="1" style="{XF_TEXT if index <= 4 else XF_FORMULA}"/>'
            for index, (_, width, _) in enumerate(PEOPLE_HEADERS, start=1)
        )
        body = (
            f'<dimension ref="A1:E{last}"/>'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="15"/>'
            f'<cols>{cols}</cols><sheetData>{"".join(rows)}</sheetData>'
            + self.protect(allow_rows=True)
            + _cf_rule(f"A2:A{last}", 'AND($A2="",COUNTA($B2:$D2)>0)', 0, 1)
            + f'<dataValidations count="{len(rules)}">{"".join(rules)}</dataValidations>'
        )
        return _sheet(body, tab=SLATE)

    # ---- Lists / marker ----------------------------------------------------
    def lists_sheet(self) -> str:
        rows: dict[int, list[str]] = {}
        cols = []
        for index, (_, title, values) in enumerate(self.lists, start=1):
            letter = column_letter(index)
            rows.setdefault(1, []).append(_inline(f"{letter}1", title, XF_HEAD_SLATE_PLAIN))
            for number, value in enumerate(values, start=2):
                rows.setdefault(number, []).append(_inline(f"{letter}{number}", value, XF_LOCKED))
            width = max(14, max((len(v) for v in values), default=10) + 2)
            cols.append(f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>')
        sheet_rows = "".join(f'<row r="{number}">{"".join(cells)}</row>' for number, cells in sorted(rows.items()))
        body = (f'<dimension ref="A1:{column_letter(len(self.lists))}{max(rows)}"/>'
                '<sheetViews><sheetView workbookViewId="0"/></sheetViews><sheetFormatPr defaultRowHeight="15"/>'
                f'<cols>{"".join(cols)}</cols><sheetData>{sheet_rows}</sheetData>' + self.protect())
        return _sheet(body, tab=GREY)

    def list_defined_names(self) -> str:
        names = []
        for index, (name, _, values) in enumerate(self.lists, start=1):
            letter = column_letter(index)
            names.append(f'<definedName name="{_xml(name)}">{LISTS_SHEET}!${letter}$2:${letter}${len(values) + 1}</definedName>')
        return "".join(names)

    def marker_sheet(self) -> str:
        built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = [(MARKER_NAME, self.config.hash()), (FINGERPRINT_NAME, self.config.fingerprint()),
                ("AstraTemplateFamily", self.family), ("AstraTemplateBuilt", built)]
        sheet_rows = "".join(
            f'<row r="{number}">{_inline(f"A{number}", key, XF_LOCKED)}{_inline(f"B{number}", value, XF_LOCKED)}</row>'
            for number, (key, value) in enumerate(rows, start=1)
        )
        body = ('<dimension ref="A1:B4"/><sheetViews><sheetView workbookViewId="0"/></sheetViews>'
                '<sheetFormatPr defaultRowHeight="15"/><cols><col min="1" max="2" width="26" customWidth="1"/></cols>'
                f'<sheetData>{sheet_rows}</sheetData>' + self.protect())
        return _sheet(body)

    # ---- README ------------------------------------------------------------
    def readme_sheet(self) -> str:
        if not self.extended:
            return self.simple_readme_sheet()
        rows, merges = [], []
        number = 0

        def line(text: str, style: int = XF_WRAP_LOCKED, *, height: int | None = None, merge: bool = True):
            nonlocal number
            number += 1
            ht = f' ht="{height}" customHeight="1"' if height else ""
            fill = ""
            if style == XF_TITLE:
                fill = "".join(f'<c r="{column_letter(i)}{number}" s="{XF_TITLE}"/>' for i in range(2, 6))
            rows.append(f'<row r="{number}"{ht}>{_inline(f"A{number}", text, style)}{fill}</row>')
            if merge:
                merges.append(f'<mergeCell ref="A{number}:E{number}"/>')

        line("Astra import template  -  how to fill this workbook", XF_TITLE, height=30)
        line(f"Template family {self.family}  |  column set {self.config.hash()}  |  dates display dd-mm-yyyy  |  "
             f"built {date.today():%d-%m-%Y}", XF_SUBTLE)
        line("")
        line("Five steps", XF_LABEL, merge=True)
        for text in (
            "1. Project sheet: fill the Value column. Project Name is required; everything else helps the App Owner set the project up correctly.",
            "2. People sheet: list every person who will appear in Tasks (Owner Email, Collaborators) with their work email and role. Send it to the App Owner, who creates the accounts and grants project access BEFORE you upload. Astra never creates users from a file.",
            "3. Tasks sheet: one row per task, step, milestone or action item. Only Import Key and Title are required; fill the rest as far as you know it. Look at the Example sheet first - it shows a task, a delayed step under it and a milestone that waits for the task.",
            "4. Do not touch the header row, do not add or hide columns, do not paste over the header. The sheets are protected against that; if you need another column, ask the App Owner to add it in Astra (Import > Template settings) and download the template again.",
            "5. Upload in Astra (Import). You see a preview of every row with its warnings and errors before anything is written. Fix, re-upload, then confirm. Nothing is deleted by an import and an existing baseline is never overwritten.",
        ):
            line(text, height=32)
        line("")
        line("Rules that make the upload seamless", XF_LABEL)
        status_list = ", ".join(label for label, _ in STATUS_LABELS)
        for text in (
            "Import Key is the row's permanent id (RA-001, WEB-12, M-3). Keep it forever: re-importing the same key updates the task; a new key creates a new task. Parent Key and Predecessors refer to it. Add new rows at the bottom; do not insert or delete rows in the middle - pre-filled keys follow the row number and a shifted key updates the wrong task.",
            "Dates are real dates only. Cells display dd-mm-yyyy. If your Excel reads dates month-first, type yyyy-mm-dd (2026-09-07) and it will still display 07-09-2026. Never type TBD, Immediate, Ongoing or 'Sept 7-10' into a date cell - the cell will refuse it; write that wording in Notes and leave the date blank.",
            "One accountable owner per row, by work email. Helpers go in Collaborators, separated by ; (semicolon). A group such as 'Academic Team' cannot own a task - name a person and mention the group in Notes.",
            f"Status: {status_list}. Blank = Draft (Assigned once an owner is given). Delayed, On hold, Cancelled, Abandoned and Reopened need a Reason. Completed, Submitted, On hold and Reopened are taken on the FIRST import only; afterwards those transitions happen in Astra, where their records are kept.",
            "Type: Task, Milestone or Action item. A Milestone is a zero-length event - give it one date (Start = Due). An Action item is a committed follow-up from a meeting; it behaves like a task.",
            "A step (subtask) is a row whose Parent Key is another row's Import Key. Predecessors are the Import Keys this row waits for (finish-to-start); separate several with ; .",
            "Original Due Date is the first commitment, Due Date is the current one. Fill Original Due Date only when the date has already moved; otherwise Astra records the first Due Date as the baseline automatically.",
            "% Complete is a whole number 0-100 you declare; Astra never invents one. Criticality is Critical, High, Normal, Low or blank (Unrated).",
            "Anything Astra has no column for goes in Notes. Nothing in the sheet is silently lost: the preview lists what landed where.",
            "App Owner-only cells: Original Due Date, Filing Entity, Attachment Links, Project and Entity. A project Manager's import keeps them for the Owner and says so in the preview.",
            f"Protection: all sheets are protected against accidental edits (password: {TEMPLATE_SHEET_PASSWORD}). Data cells are open; headers and structure are not. The App Owner may unlock a sheet deliberately, but a changed header row is rejected on upload.",
            f"Limits: {MAX_ROWS:,} task rows, 5 MB, {MAX_TITLE_CHARS} characters per Title, {MAX_CELL_CHARS:,} per text cell. Save as .xlsx (not .xlsm/.xls).",
        ):
            line(text, height=32)
        line("")
        line("Header colours", XF_LABEL)
        for text, style in (("Navy header = core column (always present; Import Key and Title are required)", XF_HEAD_CORE),
                            ("Slate header = optional built-in column (the App Owner can hide or rename it)", XF_HEAD_OPTIONAL),
                            ("Teal header = column added by the App Owner for this organisation", XF_HEAD_CUSTOM)):
            line(text, style)
        line("Pale red cell = required value missing on a row that has content, or a Due Date before its Start Date.", XF_SUBTLE)
        line("")
        line("Tasks columns", XF_LABEL)
        number += 1
        heads = ("Column", "Required", "What to enter", "Example", "Where it lands in Astra")
        rows.append(f'<row r="{number}">' + "".join(
            _inline(f"{column_letter(i)}{number}", head, XF_HEAD_SLATE_PLAIN) for i, head in enumerate(heads, start=1)) + "</row>")
        for column in self.columns:
            number += 1
            example = ""
            for sample in self.example_rows:
                if sample.get(column.key) not in (None, ""):
                    example = sample[column.key]
                    break
            example = example.strftime("%d-%m-%Y") if isinstance(example, date) else str(example)
            required = "yes" if column.required else ("core" if column.core else "no")
            values = (column.label, required, column.prompt, example, column.target)
            rows.append(f'<row r="{number}" ht="48" customHeight="1">' + "".join(
                _inline(f"{column_letter(i)}{number}", value, XF_LABEL if i == 1 else XF_WRAP_LOCKED)
                for i, value in enumerate(values, start=1)) + "</row>")
        line("")
        disabled = [item["label"] for item in self.config.columns if not item.get("enabled", True)]
        if disabled:
            line("Columns the App Owner can switch on in Astra (Import > Template settings): " + ", ".join(disabled)
                 + ". The header row of a downloaded template always matches the current setting.", XF_SUBTLE, height=32)
        body = (
            f'<dimension ref="A1:E{number}"/>'
            '<sheetViews><sheetView showGridLines="0" workbookViewId="0"/></sheetViews><sheetFormatPr defaultRowHeight="15"/>'
            '<cols><col min="1" max="1" width="30" customWidth="1"/><col min="2" max="2" width="12" customWidth="1"/>'
            '<col min="3" max="3" width="70" customWidth="1"/><col min="4" max="4" width="34" customWidth="1"/>'
            '<col min="5" max="5" width="46" customWidth="1"/></cols>'
            f'<sheetData>{"".join(rows)}</sheetData>' + self.protect()
            + f'<mergeCells count="{len(merges)}">{"".join(merges)}</mergeCells>'
        )
        return _sheet(body, tab=TEAL)

    def simple_readme_sheet(self) -> str:
        lines = [
            ("Astra import - how to fill this workbook", XF_TITLE, 30),
            (f"Template {self.family} | column set {self.config.hash()} | dates show as dd-mm-yyyy", XF_SUBTLE, 22),
            ("1. Project sheet: type the project name (required); add the manager's email and timezone if you know them.", XF_WRAP_LOCKED, 34),
            ("2. Tasks sheet: one row per task or action item. Only the Title is required; the Import Key fills itself (T-001, T-002 ...). Leave it alone unless you have your own ids. Add new rows at the bottom; do not insert or delete rows in the middle - the pre-filled keys follow the row number, and a shifted key would update the wrong task.", XF_WRAP_LOCKED, 48),
            ("3. Dates: real dates only, shown dd-mm-yyyy. If your Excel reads dates month-first, type 2026-09-07 and it will show 07-09-2026. Never type TBD or 'Sept 7-10' in a date cell - write it in Notes and leave the date blank.", XF_WRAP_LOCKED, 34),
            ("4. Owner: one work email per row, of a person who already has access in Astra. Status and Criticality are dropdowns; blank Status = Draft, blank Criticality = Unrated.", XF_WRAP_LOCKED, 34),
            ("5. Steps: to make a row a step of another task, put that task's Import Key in 'Step of (Key)'.", XF_WRAP_LOCKED, 34),
            ("6. Do not change, add or delete columns and do not paste over the header - the sheet is protected for that reason. See the Example sheet for a filled task and step.", XF_WRAP_LOCKED, 34),
            ("7. Upload in Astra (Import). You get a preview of every row with warnings before anything is written. Nothing is deleted by an import.", XF_WRAP_LOCKED, 34),
            ("8. Need more columns (collaborators, % complete, predecessors, original due date ...)? The App Owner can switch them on in Import > Template settings and you download the template again.", XF_WRAP_LOCKED, 34),
        ]
        rows = "".join(
            f'<row r="{number}" ht="{height}" customHeight="1">{_inline(f"A{number}", text, style)}</row>'
            for number, (text, style, height) in enumerate(lines, start=1)
        )
        body = (
            f'<dimension ref="A1:A{len(lines)}"/>'
            '<sheetViews><sheetView showGridLines="0" workbookViewId="0"/></sheetViews><sheetFormatPr defaultRowHeight="15"/>'
            '<cols><col min="1" max="1" width="110" customWidth="1"/></cols>'
            f'<sheetData>{rows}</sheetData>' + self.protect()
        )
        return _sheet(body, tab=TEAL)

    # ---- package -----------------------------------------------------------
    def build(self) -> bytes:
        sheets = [
            (README_SHEET, self.readme_sheet(), ""),
            (PROJECT_SHEET, self.project_sheet(), ""),
            (TEMPLATE_SHEET, self.tasks_sheet(self.tasks, example=False), ""),
            (EXAMPLE_SHEET, self.tasks_sheet(self.example_rows, example=True), ""),
        ]
        if self.extended or self.people:
            sheets.append((PEOPLE_SHEET, self.people_sheet(), ""))
        sheets += [
            (LISTS_SHEET, self.lists_sheet(), ' state="hidden"'),
            (MARKER_SHEET, self.marker_sheet(), ' state="veryHidden"'),
        ]
        active = 2 if self.tasks else 0
        sheet_tags = "".join(
            f'<sheet name="{_xml(name)}" sheetId="{index}"{state} r:id="rId{index}"/>'
            for index, (name, _, state) in enumerate(sheets, start=1)
        )
        defined = (
            self.list_defined_names()
            + f'<definedName name="{MARKER_NAME}">{MARKER_SHEET}!$B$1</definedName>'
            + f'<definedName name="{FINGERPRINT_NAME}">{MARKER_SHEET}!$B$2</definedName>'
        )
        workbook = (
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<workbookPr/><bookViews><workbookView xWindow="0" yWindow="0" windowWidth="20000" windowHeight="12000" activeTab="{active}"/></bookViews>'
            f'<sheets>{sheet_tags}</sheets><definedNames>{defined}</definedNames>'
            '<calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>'
        )
        rels = "".join(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
            for index in range(1, len(sheets) + 1)
        )
        rels += (f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
                 'Target="styles.xml"/>')
        overrides = "".join(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index in range(1, len(sheets) + 1)
        )
        content_types = (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            + overrides + '</Types>'
        )
        root_rels = (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>'
        )
        core = (
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>Astra import template ({self.family})</dc:title><dc:creator>Astra</dc:creator></cp:coreProperties>'
        )
        declaration = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", declaration + content_types)
            archive.writestr("_rels/.rels", declaration + root_rels)
            archive.writestr("docProps/core.xml", declaration + core)
            archive.writestr("xl/workbook.xml", declaration + workbook)
            archive.writestr("xl/_rels/workbook.xml.rels", declaration
                             + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                             + rels + '</Relationships>')
            archive.writestr("xl/styles.xml", declaration + _styles_xml())
            for index, (_, xml, _) in enumerate(sheets, start=1):
                archive.writestr(f"xl/worksheets/sheet{index}.xml", declaration + xml)
        return buffer.getvalue()


def build_template_xlsx(config: TemplateConfig | None = None, *, tasks=None, project=None, people=None,
                        key_offset: int = 0) -> bytes:
    """Return the locked Astra template workbook for this configuration (zipfile, no dependencies).

    ``tasks`` (dicts keyed by column key), ``project`` (dict keyed by PROJECT_FIELD_KEYS
    values) and ``people`` (tuples Email, Full Name, Role, Notes) pre-fill the sheets;
    the blank template passes none of them. ``key_offset`` shifts the pre-filled key
    formula of the blank rows (see ``next_key_offset``).
    """
    return _TemplateWorkbook(config or TemplateConfig.default(), tasks=tasks, project=project, people=people,
                             key_offset=key_offset).build()


def build_template_csv(config: TemplateConfig | None = None, *, tasks=None) -> str:
    config = config or TemplateConfig.default()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(config.labels())
    for row in tasks or []:
        writer.writerow([normalize_text(row.get(column.key)) for column in config.active])
    return buffer.getvalue()


SEQUENCE_KEY = re.compile(r"^T-(\d{3,})$")


def next_sequence_number(keys) -> int:
    """The number after the highest pre-filled-style key (T-001, T-002 ...) among ``keys``."""
    highest = 0
    for key in keys:
        match = SEQUENCE_KEY.match(str(key or ""))
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def assign_sequence_keys(keys_in_use, count: int) -> list[str]:
    """``count`` fresh T-nnn keys continuing above the highest in use and skipping any taken."""
    used = set(keys_in_use)
    number = next_sequence_number(used)
    out = []
    while len(out) < count:
        key = f"T-{number:03d}"
        if key not in used:
            used.add(key)
            out.append(key)
        number += 1
    return out


def next_key_offset(keys_in_use, prefilled_rows: int) -> int:
    """Formula offset so the first blank row (row prefilled_rows + 2) yields the next free T-nnn."""
    return next_sequence_number(keys_in_use) - (prefilled_rows + 1)


# --------------------------------------------------------------------------- upload parsing

@dataclass
class ParsedRow:
    number: int
    cells: dict[str, object]                               # column key -> raw cell value
    aliased: dict[str, str] = field(default_factory=dict)  # column key -> header text matched by alias
    extra: list[str] = field(default_factory=list)         # letters of unheaded columns that carried data


@dataclass
class ParsedUpload:
    format: str                                            # xlsx | csv
    rows: list[ParsedRow]
    unknown_columns: list[str]
    file_warnings: list[str]
    sheet_name: str = ""
    project_header: dict = field(default_factory=dict)     # Project sheet: key -> value (dates as ISO)
    people: list = field(default_factory=list)             # People sheet rows: {row, email, name, role, notes}
    date1904: bool = False                                 # the workbook's date system, for bare serial cells


def detect_format(filename: str, data: bytes) -> str:
    name = (filename or "").casefold()
    if name.endswith((".xlsm", ".xlsb", ".xls", ".ods", ".numbers")):
        raise ImportFileError(
            f"'{filename}' is not supported. Save the workbook as .xlsx (or .csv) from the Astra template and try again."
        )
    if name.endswith(".xlsx") or data.startswith(b"PK\x03\x04"):
        return "xlsx"
    if name.endswith((".csv", ".txt")) or not name:
        return "csv"
    raise ImportFileError(f"'{filename}' is not supported. Upload the filled Astra template as .xlsx or .csv.")


def parse_upload(filename: str, data: bytes, config: TemplateConfig) -> ParsedUpload:
    if len(data) > MAX_FILE_BYTES:
        raise ImportTooLarge("The file is larger than 5 MB. Split it or remove unused sheets and try again.")
    if not data:
        raise ImportFileError("The uploaded file is empty.")
    fmt = detect_format(filename, data)
    if fmt == "xlsx":
        return _parse_xlsx(data, config)
    return _parse_csv(data, config)


def _template_hint() -> str:
    return "Download a fresh template (Import → Download template .xlsx) and paste your data into its Tasks sheet."


def _parse_xlsx(data: bytes, config: TemplateConfig) -> ParsedUpload:
    try:
        workbook = read_workbook(data)
    except XlsxTooLarge as exc:
        raise ImportTooLarge(str(exc)) from exc
    except XlsxError as exc:
        raise ImportFileError(str(exc)) from exc
    marker = workbook.sheet(MARKER_SHEET)
    version = marker.cell(1, 2) if marker is not None else None
    if version is None:
        raise ImportFileError(
            "This workbook was not made from the Astra import template (its version marker is missing). "
            + _template_hint()
        )
    if normalize_text(version) != config.hash():
        raise ImportFileError(
            "The import template has changed since this file was downloaded (the App Owner changed the column "
            "settings). Download the template again and move your rows into it."
        )
    sheet = workbook.sheet(TEMPLATE_SHEET)
    if sheet is None or not sheet.rows:
        raise ImportFileError(f"The workbook has no '{TEMPLATE_SHEET}' sheet with data. " + _template_hint())
    file_warnings: list[str] = []
    project_header = _read_project_sheet(workbook.sheet(PROJECT_SHEET), file_warnings, workbook.date1904)
    people = _read_people_sheet(workbook.sheet(PEOPLE_SHEET))
    header_row_number = min(sheet.rows)
    labels = config.labels()
    width = max(sheet.max_col, len(labels))
    if width > MAX_COLUMNS:
        raise ImportFileError(f"The sheet has more than {MAX_COLUMNS} columns. " + _template_hint())
    header = [normalize_text(value) for value in sheet.row_values(header_row_number, width)]
    while header and not header[-1]:
        header.pop()
    mismatches = []
    for index in range(max(len(header), len(labels))):
        expected = labels[index] if index < len(labels) else ""
        found = header[index] if index < len(header) else ""
        if expected != found:
            letters = column_letter(index + 1)
            if not expected:
                mismatches.append(f"{letters}: unexpected extra column '{found}'")
            elif not found:
                mismatches.append(f"{letters}: missing '{expected}'")
            else:
                mismatches.append(f"{letters}: expected '{expected}', found '{found}'")
    if mismatches:
        raise ImportFileError(
            "The header row does not match the Astra template: " + "; ".join(mismatches) + ". " + _template_hint()
        )
    rows = []
    for number, values in sheet.iter_rows(width):
        if number == header_row_number:
            continue
        cells = {}
        for column, value in zip(config.active, values):
            if isinstance(value, str):
                value = unicodedata.normalize("NFC", value).strip()
            if value is None or value == "":
                continue
            cells[column.key] = value
        # Data to the right of the last template column has no header and is never
        # imported; say so per row instead of dropping it silently (review probe P2d).
        extra = [column_letter(index) for index, value in enumerate(values, start=1)
                 if index > len(labels) and value not in (None, "") and normalize_text(value) != ""]
        if not cells or set(cells) == {"import_key"}:
            if extra:
                file_warnings.append(f"Row {number}: extra data ignored in column {', '.join(extra)} "
                                     "(no template header above it and no task data on the row).")
            continue  # blank row, or only the template's pre-filled key
        rows.append(ParsedRow(number=number, cells=cells, extra=extra))
    if len(rows) > MAX_ROWS:
        raise ImportFileError(f"The sheet has more than {MAX_ROWS} data rows. Split the file and import in parts.")
    return ParsedUpload(format="xlsx", rows=rows, unknown_columns=[], file_warnings=file_warnings, sheet_name=sheet.name,
                        project_header=project_header, people=people, date1904=workbook.date1904)


def _read_project_sheet(sheet, file_warnings: list[str], date1904: bool = False) -> dict:
    """Label / Value rows of the Project sheet -> {key: value}; dates become ISO text."""
    if sheet is None:
        return {}
    labels = {collapse(label): key for label, key in PROJECT_FIELD_KEYS.items()}
    date_keys = {"start_date", "target_date", "as_of_date"}
    header: dict = {}
    for number, values in sheet.iter_rows(2):
        label = normalize_text(values[0]).rstrip("*").strip() if values else ""
        key = labels.get(collapse(label))
        if not key:
            continue
        raw = values[1] if len(values) > 1 else None
        if raw is None or raw == "":
            continue
        if key in date_keys:
            parsed, error = parse_date_cell(raw, allow_serial=True, date1904=date1904)
            if error:
                file_warnings.append(f"Project sheet, {label}: {error} The value was ignored.")
                continue
            header[key] = parsed.isoformat()
        else:
            header[key] = normalize_text(raw)
    resolve_project_header(header, file_warnings)
    return header


def resolve_project_header(header: dict, file_warnings: list[str]) -> dict:
    """Validate the typed Project-sheet values Astra stores as project settings and put the
    resolved value back, naming the substituted default in a file warning (review DI-5).
    The preview therefore shows what a created project would get, not what was typed."""
    tz = header.get("timezone")
    if tz:
        known = next((label for label in TIMEZONE_LABELS if label.casefold() == tz.casefold()), None)
        if known:
            header["timezone"] = known
        else:
            try:
                ZoneInfo(tz)
            except (ZoneInfoNotFoundError, ValueError):
                file_warnings.append(f"Project sheet, Timezone: '{tz}' is not a known timezone (for example "
                                     f"{', '.join(TIMEZONE_LABELS[:3])}); Asia/Karachi will be used.")
                header["timezone"] = "Asia/Karachi"
    days = header.get("working_days")
    if days and days not in WORKING_DAY_LABELS:
        known = next((label for label in WORKING_DAY_LABELS if collapse(label) == collapse(days)), None)
        if known:
            header["working_days"] = known
        else:
            file_warnings.append(f"Project sheet, Working Days: '{days}' is not one of {', '.join(WORKING_DAY_LABELS)}; "
                                 "Every day will be used.")
            header["working_days"] = "Every day"
    return header


def _read_people_sheet(sheet) -> list[dict]:
    if sheet is None:
        return []
    people = []
    for number, values in sheet.iter_rows(4):
        if number == 1:
            continue
        email, name, role, notes = (normalize_text(value) for value in (values + [None] * 4)[:4])
        if not any((email, name, role, notes)):
            continue
        people.append({"row": number, "email": email, "name": name, "role": role, "notes": notes})
    return people


def _decode_csv(data: bytes) -> tuple[str, list[str]]:
    warnings = []
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise ImportFileError(
            "The CSV is UTF-16 encoded (Excel's 'Unicode Text' format). Save it as 'CSV UTF-8 (comma delimited)' "
            "and upload it again, or upload the .xlsx template."
        )
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    try:
        return data.decode("utf-8"), warnings
    except UnicodeDecodeError:
        warnings.append("The CSV was not UTF-8; it was read as Windows-1252. Check accented characters in the preview.")
        return data.decode("cp1252", errors="replace"), warnings


def _parse_csv(data: bytes, config: TemplateConfig) -> ParsedUpload:
    text, warnings = _decode_csv(data)
    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
    except csv.Error:
        delimiter = ","
    try:
        # newline='' lets the csv module see CR, LF and CRLF line endings itself.
        records = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
    except csv.Error as exc:
        raise ImportFileError(
            f"The CSV could not be read line by line ({exc}). Save it again from Excel as 'CSV UTF-8 (comma "
            "delimited)' with one task per line, or upload the .xlsx template instead."
        ) from exc
    header_index = None
    for index, record in enumerate(records[:30]):
        keys = {column.key for column in (config.match_header(cell)[0] for cell in record) if column}
        if "title" in keys and "import_key" in keys:
            header_index = index
            break
    if header_index is None:
        raise ImportFileError(
            "No header row with 'Import Key' and 'Title' was found in the first 30 lines. "
            "Use the CSV template (Import → Download template .csv)."
        )
    header = records[header_index]
    if len(header) > MAX_COLUMNS:
        raise ImportFileError(f"The CSV has more than {MAX_COLUMNS} columns.")
    mapping: list[tuple] = []
    unknown: list[str] = []
    seen: set[str] = set()
    for cell in header:
        column, by_alias = config.match_header(cell)
        if column is None or column.key in seen:
            if cell.strip():
                unknown.append(cell.strip())
            mapping.append((None, False, cell))
            continue
        seen.add(column.key)
        mapping.append((column, by_alias, cell))
    rows = []
    for offset, record in enumerate(records[header_index + 1:], start=header_index + 2):
        cells: dict[str, object] = {}
        aliased: dict[str, str] = {}
        for (column, by_alias, header_text), value in zip(mapping, record):
            if column is None:
                continue
            value = unicodedata.normalize("NFC", value).strip()
            if not value:
                continue
            cells[column.key] = value
            if by_alias:
                aliased[column.key] = header_text.strip()
        if cells:
            rows.append(ParsedRow(number=offset, cells=cells, aliased=aliased))
    if len(rows) > MAX_ROWS:
        raise ImportFileError(f"The CSV has more than {MAX_ROWS} data rows. Split the file and import in parts.")
    return ParsedUpload(format="csv", rows=rows, unknown_columns=unknown, file_warnings=warnings)


# --------------------------------------------------------------------------- cell coercion

def parse_date_cell(value, *, allow_serial: bool, date1904: bool = False):
    """Return (date|None, error_message|None). Prose is never guessed.

    A bare number is an Excel serial in the workbook's own date system (``date1904``
    follows the workbook's ``workbookPr``), exactly like a date-styled cell.
    """
    if value is None or value == "":
        return None, None
    if isinstance(value, CellError):
        return None, value.message
    if isinstance(value, date):
        parsed = value
    elif isinstance(value, bool):
        return None, f"'{value}' is not a date."
    elif isinstance(value, (int, float)):
        if not allow_serial:
            return None, f"'{value}' is not a date. Use dd-mm-yyyy."
        serial = float(value)
        if not math.isfinite(serial):
            return None, f"'{value}' is not a date; the cell holds an infinite or undefined number."
        if date1904:
            if serial < 0:
                return None, f"Excel date serial {value} is negative."
        elif serial <= 60:
            return None, f"Excel date serial {value} is before 01-03-1900 and cannot be interpreted safely."
        converted = serial_to_date(serial, date1904)   # range-checked: CellError beyond 31-12-9999
        if isinstance(converted, CellError):
            return None, converted.message + " Type the date as dd-mm-yyyy."
        parsed = converted
    else:
        text = normalize_text(value)
        match = DMY_DATE.match(text)
        parts = (match.group(3), match.group(2), match.group(1)) if match else None
        if parts is None:
            match = ISO_DATE.match(text)
            parts = (match.group(1), match.group(2), match.group(3)) if match else None
        if parts is None:
            return None, (
                f"'{text}' is not a date. Enter a real date (dd-mm-yyyy or an Excel date cell); "
                "put wording such as TBD or Immediate in Notes and leave the date blank."
            )
        try:
            parsed = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            return None, f"'{text}' is not a valid calendar date (dd-mm-yyyy)."
    if not DATE_MIN <= parsed <= DATE_MAX:
        return None, f"{display_date(parsed.isoformat())} is outside 01-01-2000 .. 31-12-2100."
    return parsed, None


def parse_integer(value, minimum: int, maximum: int):
    if value is None or value == "":
        return None, None
    if isinstance(value, bool):
        return None, f"'{value}' is not a whole number."
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = normalize_text(value).replace(",", "")
        try:
            number = float(text)
        except ValueError:
            return None, f"'{text}' is not a whole number."
    if not number.is_integer():
        return None, f"'{value}' is not a whole number."
    number = int(number)
    if not minimum <= number <= maximum:
        return None, f"{number} is outside {minimum}..{maximum}."
    return number, None


def parse_number(value):
    if value is None or value == "":
        return None, None
    if isinstance(value, bool):
        return None, f"'{value}' is not a number."
    if isinstance(value, (int, float)):
        # A percent-formatted cell arrives as the displayed percentage (xlsx_reader.Percent).
        number = float(value)
    else:
        text = normalize_text(value).replace(",", "")
        try:
            number = float(text)
        except ValueError:
            return None, f"'{text}' is not a number."
    if not math.isfinite(number) or abs(number) > NUMBER_LIMIT:
        # nan / inf are not JSON and would break every screen that reads the task.
        return None, f"'{normalize_text(value)}' is not a finite number within \u00b11e15."
    return (int(number) if number.is_integer() else number), None


def parse_progress(value):
    if value is None or value == "":
        return None, None
    if isinstance(value, Percent):
        # The reader already scaled a %-formatted cell to what Excel displays: 100% -> 100.
        value = float(value)
    elif isinstance(value, float) and 0 < value < 1:
        value = round(value * 100)
    elif isinstance(value, float) and value == 1.0:
        value = 100
    elif isinstance(value, str) and value.strip().endswith("%"):
        value = value.strip()[:-1].strip()
    return parse_integer(value, 0, 100)


def parse_boolean(value):
    if value is None or value == "":
        return None, None
    if isinstance(value, bool):
        return value, None
    text = normalize_text(value).casefold()
    if text in TRUE_WORDS:
        return True, None
    if text in FALSE_WORDS:
        return False, None
    return None, f"'{value}' is not Yes or No."


def resolve_status(value):
    """Return (status_code|'unstarted'|None, error_message|None)."""
    text = normalize_text(value)
    if not text:
        return None, None
    key = collapse(text)
    for candidate in (key, key.replace(" / ", "/"), key.replace("/", " / "), key.replace("_", " ")):
        if candidate in STATUS_SYNONYMS:
            return STATUS_SYNONYMS[candidate], None
    allowed = ", ".join(label for label, _ in STATUS_LABELS)
    return None, f"Unknown status '{text}'. Use one of: {allowed}."


def resolve_criticality(value):
    text = normalize_text(value)
    if not text:
        return None, None
    key = collapse(text)
    if key in CRITICALITY_SYNONYMS:
        return CRITICALITY_SYNONYMS[key], None
    return None, f"Unknown criticality '{text}'. Use Critical, High, Normal, Low or leave blank."


def _split_predecessor(text: str) -> tuple[str, str, str]:
    """Split "KEY [type] [lag]" into (key, type, lag), each "" when absent, scanning once from
    the right: an optional lag ``[+-] blanks digits blanks d|day|days`` at the very end, then
    blanks, then an optional two-letter type (FS, SS, FF, SF, any case), then blanks. The key
    is whatever is left; it is never empty, matching the former regex, whose lazy key group
    took the shortest key that left a parsable suffix. That regex
    (``^(?P<key>.+?)\\s*(TYPE)?\\s*(LAG)?$``) backtracked cubically on a run of blanks, so
    one crafted cell stalled the single-process server (regression review SECURITY-1);
    this scan is linear in the item length and accepts exactly the same syntax.
    """
    end = len(text)
    lag = ""
    unit_start = None
    for unit in ("DAYS", "DAY", "D"):
        if end >= len(unit) and text[end - len(unit):end].upper() == unit:
            unit_start = end - len(unit)
            break
    if unit_start is not None:
        i = unit_start
        while i > 0 and text[i - 1].isspace():
            i -= 1
        digits_end = i
        while i > 0 and text[i - 1].isdecimal():
            i -= 1
        if i < digits_end:
            while i > 0 and text[i - 1].isspace():
                i -= 1
            if i > 1 and text[i - 1] in "+-":   # i > 1: a key of at least one character stays
                i -= 1
                lag = text[i:end].replace(" ", "")
                end = i
    while end > 0 and text[end - 1].isspace():
        end -= 1
    dep_type = ""
    if end > 2 and text[end - 2:end].upper() in DEPENDENCY_TYPES:
        dep_type = text[end - 2:end].upper()
        end -= 2
        while end > 0 and text[end - 1].isspace():
            end -= 1
    return text[:end], dep_type, lag


def parse_predecessor(item: str, known_keys: set[str]):
    """Return (key, dependency_type, lag_text, error). A suffix (FS+2d) is only
    split off when the bare text is not itself a known key."""
    text = item.strip()
    if len(text) > MAX_PRED_ITEM_CHARS:
        shown = text[:MAX_KEY_CHARS] + "..."
        return None, None, None, f"'{shown}' is not a valid Import Key."
    if text.upper() in known_keys:   # Import Keys are canonical upper case
        return text.upper(), "FS", "", None
    key, dep_type, lag = _split_predecessor(text)
    if (dep_type or lag) and KEY_PATTERN.match(key):
        return key.upper(), dep_type or "FS", lag, None
    if KEY_PATTERN.match(text):
        return text.upper(), "FS", "", None
    return None, None, None, f"'{text}' is not a valid Import Key."


# --------------------------------------------------------------------------- validation engine

@dataclass
class RowResult:
    number: int
    key: str = ""
    findings: list = field(default_factory=list)
    action: str = "create"                 # create | update | unchanged | error
    values: dict = field(default_factory=dict)
    changes: dict = field(default_factory=dict)
    plan: dict = field(default_factory=dict)
    existing: dict | None = None

    def add(self, level: str, code: str, message: str, column: str = "") -> None:
        self.findings.append(Finding(level, code, message, column))

    @property
    def level(self) -> str:
        levels = {finding.level for finding in self.findings}
        if "error" in levels:
            return "error"
        if "warning" in levels:
            return "warning"
        return "ok"

    def as_dict(self) -> dict:
        return {
            "row": self.number, "import_key": self.key, "action": self.action, "level": self.level,
            "findings": [finding.as_dict() for finding in self.findings],
            "values": self.values, "changes": self.changes,
            "task_id": self.plan.get("task_id") or (self.existing["id"] if self.existing else None),
        }


@dataclass
class Finding:
    level: str
    code: str
    message: str
    column: str = ""

    def as_dict(self) -> dict:
        return {"level": self.level, "code": self.code, "column": self.column, "message": self.message}


REPORT_COLUMNS = ("row", "import_key", "action", "level", "title", "owner", "start_date", "due_date", "status",
                  "criticality", "task_id", "findings")


class ImportEngine:
    """Turns parsed rows into a validated plan and applies it inside the caller's transaction."""

    def __init__(self, db, config: TemplateConfig, *, actor: dict, is_owner: bool, project: dict | None,
                 new_project_name: str | None, filename: str, options: dict):
        self.db = db
        self.config = config
        self.actor = actor
        self.is_owner = is_owner
        self.project = project
        self.project_id = project["id"] if project else None
        self.new_project_name = new_project_name
        self.filename = os.path.basename(filename or "upload")
        self.options = options
        self.default_reason = str(options.get("default_reason") or "").strip()
        self.rows: list[RowResult] = []
        self.unknown_columns: list[str] = []
        self.file_warnings: list[str] = []
        self.file_format = ""
        self.project_header: dict = {}
        self.people: list[dict] = []
        self.date1904 = False
        # Owner creating a project from the file: active users named in the rows get
        # project access when the project is created (user id -> role), so the Owner
        # Emails are not dropped as "not eligible" for a project that does not exist yet.
        self.grants: dict[str, str] = {}
        self._load_context()

    # ---- context ---------------------------------------------------------
    def _load_context(self) -> None:
        if self.is_owner:
            users = self.db.execute("SELECT id,email,display_name,active,global_role FROM users").fetchall()
        else:
            # A Manager's file is matched only against the accounts the Manager can already
            # see: the list_assignable_users set (active members of the target project plus
            # the App Owner and chairman) and themselves. Matched against every account, the
            # preview's findings were an oracle for the whole directory the Manager is refused
            # at GET /api/users - existence, deactivation, membership and display name ->
            # email, 2,000 probes per upload (regression review SECURITY-4).
            users = self.db.execute(
                """SELECT id,email,display_name,active,global_role FROM users u
                   WHERE u.active=1 AND (
                       u.id=? OR u.global_role IN ('owner','chairman')
                       OR EXISTS(SELECT 1 FROM memberships m WHERE m.user_id=u.id AND m.project_id=?)
                   )""",
                (self.actor["id"], self.project_id),
            ).fetchall()
        self.users_by_email = {row["email"].casefold(): dict(row) for row in users}
        self.users_by_name: dict[str, list[dict]] = {}
        for row in users:
            if row["active"]:
                self.users_by_name.setdefault(collapse(row["display_name"]), []).append(dict(row))
        self.members: set[str] = set()
        self.existing_by_key: dict[str, dict] = {}
        self.existing_by_id: dict[str, dict] = {}
        self.existing_edges: set[tuple] = set()
        self.existing_attachments: dict[str, set] = {}
        self.existing_reviewers: set[tuple] = set()
        if self.project_id:
            self.members = {
                row["user_id"] for row in self.db.execute(
                    "SELECT user_id FROM memberships WHERE project_id=?", (self.project_id,)
                )
            }
            for row in self.db.execute("SELECT * FROM tasks WHERE project_id=?", (self.project_id,)):
                task = dict(row)
                self.existing_by_id[task["id"]] = task
                if task.get("import_key"):
                    # Keys are matched in canonical upper case: the template's own uniqueness
                    # rule (COUNTIF) is case-insensitive, so t-001 and T-001 are one task.
                    self.existing_by_key[task["import_key"].upper()] = task
            for row in self.db.execute(
                """SELECT d.predecessor_task_id p, d.successor_task_id s FROM task_dependencies d
                   JOIN tasks t ON t.id=d.successor_task_id WHERE t.project_id=?""", (self.project_id,)
            ):
                self.existing_edges.add((row["p"], row["s"]))
            for row in self.db.execute(
                "SELECT a.task_id, a.path FROM task_attachments a JOIN tasks t ON t.id=a.task_id WHERE t.project_id=?",
                (self.project_id,),
            ):
                self.existing_attachments.setdefault(row["task_id"], set()).add(row["path"])
            for row in self.db.execute(
                "SELECT r.task_id, r.user_id, r.role FROM task_reviewers r JOIN tasks t ON t.id=r.task_id WHERE t.project_id=?",
                (self.project_id,),
            ):
                self.existing_reviewers.add((row["task_id"], row["user_id"], row["role"]))
        self.entities = {collapse(row["name"]): dict(row) for row in self.db.execute("SELECT id,name,active FROM entities")}

    def _eligible(self, user: dict) -> bool:
        if not user.get("active"):
            return False
        if user.get("global_role") in ("owner", "chairman"):
            return True
        if self.project_id is None and self.is_owner:
            # The Owner is creating the project from this file: every active user named
            # in it is granted access when the project is created (see self.grants).
            return True
        return user["id"] in self.members

    def _grant_role_for(self, user: dict) -> str:
        manager_email = normalize_text(self.project_header.get("manager_email", "")).casefold()
        return "manager" if manager_email and user["email"].casefold() == manager_email else "member"

    def _note_grant(self, user: dict, result: RowResult, column: str) -> None:
        """Record that an active user named in a new-project import gets access at commit."""
        if self.project_id is not None or not self.is_owner or user.get("global_role") in ("owner", "chairman"):
            return
        role = self._grant_role_for(user)
        if user["id"] not in self.grants or role == "manager":
            self.grants[user["id"]] = role
        result.add("info", "I_ACCESS_GRANTED",
                   f"{user['email']} will be given {role} access to the new project.", column)

    def _resolve_person(self, text: str, result: RowResult, column: str):
        """Return a user dict or None, adding findings. Email first, then a unique display name.

        The App Owner, who may read the user directory, gets the precise reason for a miss.
        Anyone else matches only against the accounts they can already see (_load_context) and
        gets one neutral finding whatever the reason, so a preview cannot tell an unknown email
        from a deactivated or non-member account (regression review SECURITY-4).
        """
        text = text.strip()
        if "@" in text:
            user = self.users_by_email.get(text.casefold())
            if not user:
                return self._person_miss(text, result, column, "W_UNRESOLVED_PERSON",
                                         f"No Astra user has the email '{text}'.")
        else:
            matches = self.users_by_name.get(collapse(text), [])
            if len(matches) > 1:
                result.add("warning", "W_UNRESOLVED_PERSON", f"'{text}' matches several users; use the person's email.", column)
                return None
            if not matches:
                return self._person_miss(text, result, column, "W_UNRESOLVED_PERSON",
                                         f"'{text}' is not an Astra user; use the person's email.")
            user = matches[0]
            result.add("warning", "W_PERSON_BY_NAME", f"'{text}' was matched by name to {user['email']}.", column)
        if not self._eligible(user):
            where = "the new project" if not self.project_id else "this project"
            what = "is deactivated and cannot be granted access" if not user.get("active") else f"has no access to {where}; grant access, then re-import"
            return self._person_miss(text, result, column, "W_PERSON_NOT_ELIGIBLE", f"{user['email']} {what}.")
        self._note_grant(user, result, column)
        return user

    def _person_miss(self, text: str, result: RowResult, column: str, code: str, detail: str):
        """Record that ``text`` names nobody the row may be assigned to: the detailed finding
        for the App Owner, the one neutral text for everyone else."""
        if self.is_owner:
            result.add("warning", code, detail, column)
        else:
            result.add("warning", "W_PERSON_NOT_ELIGIBLE", NEUTRAL_PERSON_MESSAGE.format(text=text), column)
        return None

    def _default_reason(self, row: RowResult) -> str:
        return self.default_reason or f"Excel import {self.filename} row {row.number}"

    # ---- validation ------------------------------------------------------
    def validate(self, parsed: ParsedUpload) -> dict:
        self.unknown_columns = parsed.unknown_columns
        self.file_warnings = list(parsed.file_warnings)
        self.file_format = parsed.format
        self.project_header = dict(parsed.project_header)
        self.date1904 = parsed.date1904
        self.people = self._check_people(parsed.people)
        self.rows = [self._validate_row(row) for row in parsed.rows]
        self._check_duplicate_keys()
        self._check_project_column()
        self._check_project_header()
        self._wire_parents()
        self._wire_dependencies()
        self._propagate_invalid()
        for result in self.rows:
            self._finish_row(result)
        return self.preview()

    def _validate_row(self, row: ParsedRow) -> RowResult:
        result = RowResult(number=row.number)
        cells = dict(row.cells)
        # An Excel error value (#N/A, #REF!) or an unreadable cell is never imported as text
        # (review XI3-03). Date columns keep their own, more specific E_DATE_INVALID wording
        # for an out-of-range date serial.
        for key in list(cells):
            value = cells[key]
            if not isinstance(value, CellError):
                continue
            column = self.config.by_key.get(key)
            if value.code != "error_value" and column is not None and column.kind in ("date", "date_due"):
                continue
            result.add("error", "E_CELL_ERROR",
                       f"The cell cannot be read: {value.message.rstrip('.')}. Fix the formula or type the value.",
                       column.label if column else key)
            del cells[key]
        text = {key: normalize_text(value) for key, value in cells.items()}
        for key, value in text.items():
            if len(value) > MAX_CELL_CHARS:
                column = self.config.by_key.get(key)
                result.add("error", "E_CELL_TOO_LONG",
                           f"Cell has {len(value)} characters; the limit is {MAX_CELL_CHARS}.",
                           column.label if column else key)
        if row.aliased:
            pairs = "; ".join(f"{header} → {self.config.by_key[key].label}" for key, header in row.aliased.items()
                              if key in self.config.by_key)
            result.add("warning", "W_HEADER_ALIAS", f"Columns matched by alias: {pairs}.")

        key = text.get("import_key", "").upper()   # canonical form, see _load_context
        result.key = key
        if not key:
            result.add("error", "E_KEY_MISSING", "Import Key is required.", "Import Key")
        elif not KEY_PATTERN.match(key):
            result.add("error", "E_KEY_INVALID",
                       f"'{key}' is not a valid Import Key (letters, digits, . _ - up to {MAX_KEY_CHARS} characters).",
                       "Import Key")
        elif key.upper().startswith(EXAMPLE_KEY_PREFIXES):
            result.add("error", "E_EXAMPLE_ROW", "This is an example row (Import Key starts with EX-). Give it a real key.",
                       "Import Key")
        # Import Keys are unique per project only (idx_tasks_import_key); the Simple
        # template pre-fills T-001, T-002 ... for every project, so a key used in
        # another project is not a finding.
        existing = self.existing_by_key.get(key) if key else None
        result.existing = existing
        if row.extra:
            result.add("warning", "W_EXTRA_DATA",
                       f"Extra data ignored in column {', '.join(row.extra)} (no template header above it).")
        result.action = "update" if existing else "create"
        is_manager_import = not self.is_owner

        title = text.get("title", "")
        if not title:
            result.add("error", "E_TITLE_MISSING", "Title is required.", "Title")
        elif len(title) > MAX_TITLE_CHARS:
            result.add("error", "E_TITLE_TOO_LONG", f"Title has {len(title)} characters; the limit is {MAX_TITLE_CHARS}.", "Title")

        allow_serial = self.file_format == "xlsx"
        date1904 = self.date1904
        extras = {}
        for column in self.config.active:
            if not column.custom:
                continue
            raw = cells.get(column.key)
            if raw is None or raw == "":
                if column.required and result.action == "create":
                    result.add("error", "E_REQUIRED", f"'{column.label}' is required.", column.label)
                continue
            if column.kind == "date":
                parsed, error = parse_date_cell(raw, allow_serial=allow_serial, date1904=date1904)
                value = parsed.isoformat() if parsed else None
            elif column.kind == "number":
                value, error = parse_number(raw)
            elif column.kind == "list":
                value, error = None, None
                wanted = collapse(normalize_text(raw))
                for option in column.values:
                    if collapse(option) == wanted:
                        value = option
                if value is None:
                    error = f"'{normalize_text(raw)}' is not one of: {', '.join(column.values)}."
            else:
                value, error = normalize_text(raw), None
            if error:
                result.add("error", "E_CUSTOM_INVALID", error, column.label)
            elif value is not None:
                extras[column.key] = value


        owner = None
        if text.get("owner_email"):
            owner = self._resolve_person(text["owner_email"], result, "Owner Email")
        people_lists = {}
        for list_key, role in (("collaborators", "collaborator"), ("reviewers", "reviewer"), ("approvers", "approver")):
            ids = []
            for item in split_list(cells.get(list_key)):
                user = self._resolve_person(item, result, self.config.by_key[list_key].label if list_key in self.config.by_key else list_key)
                if user and user["id"] not in ids:
                    ids.append(user["id"])
            people_lists[role] = ids

        dates = {}
        for date_key, label in (("start_date", "Start Date"), ("due_date", "Due Date"), ("baseline_due_date", "Original Due Date")):
            parsed, error = parse_date_cell(cells.get(date_key), allow_serial=allow_serial, date1904=date1904)
            if error:
                result.add("error", "E_DATE_INVALID", error, label)
            dates[date_key] = parsed
        duration, error = parse_integer(cells.get("duration_days"), 1, 3660)
        if error:
            result.add("error", "E_DURATION_INVALID", error, "Duration (days)")
        start, due = dates["start_date"], dates["due_date"]
        if duration:
            if start and not due:
                due = date.fromordinal(start.toordinal() + duration - 1)
            elif due and not start:
                start = date.fromordinal(due.toordinal() - duration + 1)
            elif start and due and (due.toordinal() - start.toordinal() + 1) != duration:
                result.add("warning", "W_DURATION_IGNORED",
                           f"Duration {duration} disagrees with Start/Due and was ignored.", "Duration (days)")
        if start and due and due < start:
            result.add("error", "E_DATE_ORDER",
                       f"Due Date {display_date(due.isoformat())} is before Start Date {display_date(start.isoformat())}.",
                       "Due Date")
        milestone, error = parse_boolean(cells.get("milestone"))
        if error:
            result.add("error", "E_MILESTONE_INVALID", error, "Milestone")
        if milestone is None and TYPE_COLUMN_KEY in extras:
            # Type = Milestone is the v2 way of saying "zero-length event"; other types stay tasks.
            milestone = extras[TYPE_COLUMN_KEY] == "Milestone"
        if milestone and (start or due) and not (start and due):
            start = due = start or due
        if dates["baseline_due_date"] and is_manager_import:
            result.add("warning", "W_BASELINE_SKIPPED",
                       "Original Due Date is applied only by the App Owner; skipped.", "Original Due Date")
            dates["baseline_due_date"] = None

        status_value, error = resolve_status(cells.get("status"))
        if error:
            result.add("error", "E_STATUS_UNKNOWN", error, "Status")
        progress, error = parse_progress(cells.get("progress"))
        if error:
            result.add("error", "E_PROGRESS_INVALID", error, "% Complete")
        criticality, error = resolve_criticality(cells.get("criticality"))
        if error:
            result.add("error", "E_CRITICALITY_UNKNOWN", error, "Criticality")

        next_action = text.get("next_action", "")
        if len(next_action) > MAX_NOTE_CHARS:
            result.add("warning", "W_NEXT_ACTION_TRUNCATED",
                       f"Next Action was shortened to {MAX_NOTE_CHARS} characters.", "Next Action")
            next_action = next_action[:MAX_NOTE_CHARS]

        attachments = []
        if cells.get("attachment_links"):
            if is_manager_import:
                result.add("warning", "W_ATTACHMENTS_SKIPPED",
                           "Attachment links are Owner-only; skipped.", "Attachment Links")
            else:
                for item in split_list(cells.get("attachment_links")):
                    attachments.append((item, os.path.basename(item.rstrip("/\\")) or item))
        entity_ids = []
        if cells.get("entity"):
            if is_manager_import:
                result.add("warning", "W_ENTITY_SKIPPED", "Entity filing is Owner-only; skipped.", "Entity")
            else:
                for item in split_list(cells.get("entity")):
                    entity = self.entities.get(collapse(item))
                    if not entity or not entity["active"]:
                        result.add("error", "E_ENTITY_UNKNOWN",
                                   f"'{item}' is not an active entity; entities are never created by import.", "Entity")
                    else:
                        entity_ids.append(entity["id"])

        pred_items = split_list(cells.get("predecessors"))
        result.plan = {
            "title": title, "description": text.get("description", ""), "notes": text.get("notes", ""),
            "owner": owner, "people": people_lists, "start_date": start.isoformat() if start else None,
            "due_date": due.isoformat() if due else None,
            "baseline_due": dates["baseline_due_date"].isoformat() if dates["baseline_due_date"] else None,
            "status_value": status_value, "progress": progress, "criticality": criticality,
            "criticality_given": bool(text.get("criticality")), "milestone": milestone,
            "next_action": next_action, "reason": text.get("reason", ""), "attachments": attachments,
            "entities": entity_ids, "extras": extras, "parent_key": text.get("parent_key", "").upper(),
            "pred_items": pred_items, "project_text": text.get("project", ""), "extra_notes": [],
        }
        return result

    def _check_duplicate_keys(self) -> None:
        counts: dict[str, int] = {}
        for result in self.rows:
            if result.key:
                counts[result.key] = counts.get(result.key, 0) + 1
        for result in self.rows:
            if result.key and counts[result.key] > 1:
                result.add("error", "E_DUP_KEY", f"Import Key '{result.key}' appears {counts[result.key]} times in the file.",
                           "Import Key")

    def _check_project_column(self) -> None:
        target_name = (self.project or {}).get("name") or self.new_project_name or ""
        sheet_name = self.project_header.get("name", "")
        sheet_mismatch = bool(sheet_name and target_name and collapse(sheet_name) != collapse(target_name))
        for result in self.rows:
            text = result.plan.get("project_text", "")
            if text and target_name and collapse(text) != collapse(target_name):
                result.add("error", "E_PROJECT_MISMATCH",
                           f"Project '{text}' does not match the target project '{target_name}'. Leave the cell blank or fix it.",
                           "Project")
            if sheet_mismatch:
                result.add("error", "E_PROJECT_MISMATCH",
                           f"The Project sheet names '{sheet_name}' but the chosen target is '{target_name}'. "
                           "Pick the matching project on the Import screen or fix the Project sheet.", "Project sheet")

    def _check_project_header(self) -> None:
        """Planned Finish before Planned Start on the Project sheet (review DI-5): an error on
        every row when the sheet would create the project, a file warning otherwise (the
        sheet's dates are never applied to an existing project)."""
        start, target = self.project_header.get("start_date"), self.project_header.get("target_date")
        if not (start and target and target < start):
            return
        message = (f"The Project sheet's Planned Finish Date {display_date(target)} is before its Planned Start Date "
                   f"{display_date(start)}.")
        if self.project is None:
            for result in self.rows:
                result.add("error", "E_PROJECT_DATES",
                           message + " Fix the Project sheet; the project cannot be created with these dates.",
                           "Project sheet")
        else:
            self.file_warnings.append(message + " The Project sheet's dates are not applied to an existing project.")

    def _check_people(self, people: list[dict]) -> list[dict]:
        """Cross-check the People sheet: who the App Owner still has to add or grant."""
        report = []
        for person in people:
            entry = {**person, "status": "ok", "message": ""}
            email = person["email"]
            if not email:
                entry["status"] = "group" if person["name"] else "incomplete"
                entry["message"] = (f"'{person['name']}' has no email; a group cannot own a task - list its members."
                                    if person["name"] else "Row has no email.")
            else:
                user = self.users_by_email.get(email.casefold())
                if not self.is_owner:
                    # One status and one text for every miss (regression review SECURITY-4).
                    if not user or not self._eligible(user):
                        entry["status"] = "no_access"
                        entry["message"] = (f"People row {person['row']}: {email} is not an active member of this "
                                            "project; the App Owner adds the account or grants access.")
                elif not user:
                    entry["status"] = "unknown_user"
                    entry["message"] = f"People row {person['row']}: {email} is not an Astra user; the App Owner adds the account first."
                elif not user.get("active"):
                    entry["status"] = "inactive"
                    entry["message"] = f"People row {person['row']}: {email} is deactivated."
                elif not self._eligible(user):
                    entry["status"] = "no_access"
                    where = "the new project" if not self.project_id else "this project"
                    entry["message"] = f"People row {person['row']}: {email} has no access to {where}; the App Owner grants it."
            if entry["status"] not in ("ok",):
                self.file_warnings.append(entry["message"])
            report.append(entry)
        return report

    def _row_index(self) -> dict[str, RowResult]:
        return {result.key: result for result in self.rows if result.key}

    # Both graphs (parents, dependencies) are built over one node id per task: the
    # task id for a task that already exists in the project (whether or not its key
    # is in the file) and the Import Key for a task the file creates. Existing tasks
    # that are absent from the file therefore sit in the same graph as the rows, so
    # a cycle that runs through them is found (review probes P6a, P6c).
    def _node(self, key: str):
        task = self.existing_by_key.get(key)
        return task["id"] if task else key

    def _wire_parents(self) -> None:
        by_key = self._row_index()
        row_of_node = {self._node(key): row for key, row in by_key.items()}

        def parent_node(node):
            row = row_of_node.get(node)
            if row is not None:
                parent_key = row.plan.get("parent_key")
                if parent_key:
                    return self._node(parent_key)
                if row.existing:
                    return row.existing.get("parent_task_id") or None
                return None
            task = self.existing_by_id.get(node)
            return (task.get("parent_task_id") or None) if task else None

        for result in self.rows:
            parent_key = result.plan.get("parent_key")
            if not parent_key or result.level == "error":
                continue
            if parent_key == result.key:
                result.add("error", "E_PARENT_SELF", "A task cannot be its own parent.", "Parent Key")
            elif parent_key in by_key and by_key[parent_key].level == "error":
                result.add("error", "E_PARENT_INVALID", f"Parent '{parent_key}' has errors and will not import.",
                           "Parent Key")
            elif parent_key not in by_key and parent_key not in self.existing_by_key:
                result.add("error", "E_PARENT_UNKNOWN",
                           f"Parent Key '{parent_key}' is neither in this file nor an existing task of the project.",
                           "Parent Key")
            else:
                own = self._node(result.key)
                node, seen = self._node(parent_key), set()
                while node and node not in seen:
                    if node == own:
                        result.add("error", "E_PARENT_CYCLE", f"Parent '{parent_key}' would create a subtask cycle.",
                                   "Parent Key")
                        break
                    seen.add(node)
                    node = parent_node(node)
                else:
                    if len(seen) > 2:
                        result.add("warning", "W_PARENT_DEPTH",
                                   "This row is a step of a step: the Gantt shows it nested under its parent step. "
                                   "Keep hierarchies to task > step where you can.",
                                   "Parent Key")

    def _propagate_invalid(self) -> None:
        """A row whose parent or predecessor (in this file) has errors is an error too.

        Runs after every row-level and dependency check, and repeats until stable, so
        a parent that only fails in dependency wiring still takes its steps with it
        (review probe P5b) instead of importing them top-level.
        """
        by_key = self._row_index()
        changed = True
        while changed:
            changed = False
            for result in self.rows:
                if result.level == "error":
                    continue
                parent_key = result.plan.get("parent_key")
                if parent_key and parent_key != result.key and parent_key in by_key and by_key[parent_key].level == "error":
                    result.add("error", "E_PARENT_INVALID", f"Parent '{parent_key}' has errors and will not import.",
                               "Parent Key")
                    changed = True
                    continue
                for key in result.plan.get("predecessors", []):
                    if key in by_key and by_key[key].level == "error":
                        result.add("error", "E_PRED_INVALID", f"Predecessor '{key}' has errors and will not import.",
                                   "Predecessors")
                        changed = True
                        break

    def _wire_dependencies(self) -> None:
        by_key = self._row_index()
        known = set(by_key) | set(self.existing_by_key)
        graph: dict[str, set] = {}
        for pred_id, succ_id in self.existing_edges:
            graph.setdefault(pred_id, set()).add(succ_id)

        def reaches(start, target) -> bool:
            stack, seen = [start], set()
            while stack:
                node = stack.pop()
                if node == target:
                    return True
                if node in seen:
                    continue
                seen.add(node)
                stack.extend(graph.get(node, ()))
            return False

        for result in self.rows:
            edges = []
            for item in result.plan.get("pred_items", []):
                key, dep_type, lag, error = parse_predecessor(item, known)
                if error:
                    result.add("error", "E_PRED_INVALID", error, "Predecessors")
                    continue
                if dep_type != "FS" or lag:
                    result.add("warning", "W_LAG_IGNORED",
                               f"Dependency '{item}' is stored as finish-to-start without lag; the original is kept in Notes.",
                               "Predecessors")
                    result.plan["extra_notes"].append(f"Dependency as written: {item}")
                if key == result.key:
                    result.add("error", "E_PRED_SELF", "A task cannot depend on itself.", "Predecessors")
                    continue
                if key not in known:
                    result.add("error", "E_PRED_UNKNOWN",
                               f"Predecessor '{key}' is neither in this file nor an existing task of the project.",
                               "Predecessors")
                    continue
                if key in by_key and by_key[key].level == "error":
                    result.add("error", "E_PRED_INVALID", f"Predecessor '{key}' has errors and will not import.", "Predecessors")
                    continue
                if result.level == "error":
                    continue
                if reaches(self._node(result.key), self._node(key)):
                    result.add("error", "E_DEP_CYCLE", f"Depending on '{key}' would create a cycle.", "Predecessors")
                    continue
                if key not in edges:
                    edges.append(key)
                    graph.setdefault(self._node(key), set()).add(self._node(result.key))
            result.plan["predecessors"] = edges

    def _finish_row(self, result: RowResult) -> None:
        plan = result.plan
        existing = result.existing
        owner = plan.get("owner")
        owner_id = owner["id"] if owner else None
        status_value = plan.get("status_value")
        reason = plan.get("reason") or self._default_reason(result)
        plan["reason"] = reason
        display_status = None

        if existing is None:
            status = status_value
            if status in (None, "unstarted"):
                status = "assigned" if owner_id else "draft"
            if not self.is_owner and status not in MANAGER_ORDINARY:
                result.add("warning", "W_PROTECTED_STATUS",
                           f"Managers may create tasks only in an ordinary status; '{status}' was replaced by "
                           f"'{'assigned' if owner_id else 'draft'}'.", "Status")
                status = "assigned" if owner_id else "draft"
            elif status in NO_RECORD_ON_CREATE:
                result.add("warning", "W_STATUS_NO_RECORD",
                           f"Status '{status}' is recorded on creation without a submission or checkpoint record.", "Status")
            description = plan["description"]
            notes = [plan["notes"]] + plan["extra_notes"] if plan["notes"] else plan["extra_notes"]
            if notes:
                description = (description + "\n\n" if description else "") + "Notes:\n" + "\n".join(notes)
            plan["fields"] = {
                "title": plan["title"], "description": description, "owner_user_id": owner_id, "status": status,
                "criticality": plan["criticality"], "start_date": plan["start_date"], "due_date": plan["due_date"],
                "progress": plan["progress"], "is_milestone": 1 if plan.get("milestone") else 0,
                "next_action_note": plan["next_action"] or None,
                "import_extras": json.dumps(plan["extras"], ensure_ascii=False, sort_keys=True, allow_nan=False) if plan["extras"] else None,
            }
            display_status = status
        else:
            changes: dict[str, dict] = {}
            fields: dict = {}

            def change(name, new_value, label=None):
                old_value = existing.get(name)
                if new_value is not None and new_value != old_value:
                    fields[name] = new_value
                    changes[label or name] = {"from": old_value, "to": new_value}

            change("title", plan["title"] or None)
            if "title" in fields:
                result.add("warning", "W_TITLE_CHANGED",
                           f"Title changes from '{existing.get('title')}' to '{plan['title']}'. If you inserted or deleted "
                           "rows, the pre-filled keys below that point have shifted; check the Import Key column.", "Title")
            if plan["description"]:
                change("description", plan["description"])
            if owner_id and owner_id != existing.get("owner_user_id"):
                change("owner_user_id", owner_id)
            change("start_date", plan["start_date"])
            change("due_date", plan["due_date"])
            change("progress", plan["progress"])
            if plan.get("milestone") is not None:
                change("is_milestone", 1 if plan["milestone"] else 0)
            if plan["next_action"]:
                change("next_action_note", plan["next_action"])
            if status_value:
                target = status_value
                if target == "unstarted":
                    target = "assigned" if (owner_id or existing.get("owner_user_id")) else "draft"
                    if existing["status"] in ("draft", "assigned"):
                        target = existing["status"]
                if target != existing["status"]:
                    if existing["status"] in LOCKED_SOURCE:
                        # Leaving a governed / protected / closed status needs the lifecycle record
                        # (reopen, acceptance, hold release); the stored status stays (review AS-2).
                        if self.is_owner:
                            result.add("warning", "W_GOVERNED_STATUS",
                                       f"Leaving status '{existing['status']}' needs its lifecycle action in Astra (reopen, "
                                       f"accept or release the hold); the status was left as '{existing['status']}'.", "Status")
                        else:
                            result.add("warning", "W_PROTECTED_STATUS",
                                       f"Status '{existing['status']}' is an Owner decision; changing it is requested in Astra, "
                                       f"not by import. The status was left as '{existing['status']}'.", "Status")
                    elif self.is_owner and target in NO_IMPORT_ON_UPDATE:
                        result.add("warning", "W_GOVERNED_STATUS",
                                   f"Status '{target}' needs its lifecycle action in Astra; the status was left as "
                                   f"'{existing['status']}'.", "Status")
                    elif not self.is_owner and (target in PROTECTED or target in GOVERNED):
                        result.add("warning", "W_PROTECTED_STATUS",
                                   f"Status '{target}' is an Owner decision; the status was left as '{existing['status']}'.",
                                   "Status")
                    else:
                        change("status", target)
            if plan.get("criticality_given") and plan["criticality"] != (existing.get("criticality") or None):
                fields["criticality"] = plan["criticality"]
                changes["criticality"] = {"from": existing.get("criticality"), "to": plan["criticality"]}
                plan["criticality_change"] = (existing.get("criticality"), plan["criticality"])
            if plan["extras"]:
                current = {}
                if existing.get("import_extras"):
                    try:
                        current = json.loads(existing["import_extras"])
                    except ValueError:
                        current = {}
                merged = {**current, **plan["extras"]}
                if merged != current:
                    change("import_extras", json.dumps(merged, ensure_ascii=False, sort_keys=True, allow_nan=False))
            notes = ([plan["notes"]] if plan["notes"] else []) + plan["extra_notes"]
            base_description = fields.get("description", existing.get("description") or "")
            missing = [note for note in notes if note not in base_description]
            if missing:
                addition = ("\n\n" if base_description else "") + ("" if "Notes:" in base_description else "Notes:\n") + "\n".join(missing)
                fields["description"] = base_description + addition
                changes.setdefault("description", {"from": existing.get("description"), "to": fields["description"]})
            if plan["baseline_due"] and (existing.get("baseline_due_date") or existing.get("baseline_start_date")):
                result.add("info", "I_BASELINE_KEPT", "The task already has a baseline; Original Due Date was not applied.",
                           "Original Due Date")
                plan["baseline_due"] = None
            plan["fields"] = fields
            result.changes = {name: {"from": self._display(name, item["from"]), "to": self._display(name, item["to"])}
                              for name, item in changes.items()}
            display_status = fields.get("status", existing["status"])

        # list additions
        plan["new_people"] = []
        task_id = existing["id"] if existing else None
        for role, ids in plan["people"].items():
            for user_id in ids:
                if not task_id or (task_id, user_id, role) not in self.existing_reviewers:
                    plan["new_people"].append((user_id, role))
        plan["new_attachments"] = [
            item for item in plan["attachments"]
            if not task_id or item[0] not in self.existing_attachments.get(task_id, set())
        ]
        plan["new_predecessors"] = []
        for key in plan.get("predecessors", []):
            pred_id = self.existing_by_key.get(key, {}).get("id")
            if task_id and pred_id and (pred_id, task_id) in self.existing_edges:
                continue
            plan["new_predecessors"].append(key)
        parent_key = plan.get("parent_key")
        plan["parent_change"] = False
        if parent_key and result.level != "error":
            current_parent = existing.get("parent_task_id") if existing else None
            target_parent_id = self.existing_by_key.get(parent_key, {}).get("id")
            # A parent that is new in this file has no id yet: that is a change too, applied
            # after pass 1 has created it (review probe P6d).
            plan["parent_change"] = (not existing or target_parent_id is None or target_parent_id != current_parent)
            if existing and plan["parent_change"]:
                result.changes["parent_key"] = {"from": self._key_of_task(current_parent), "to": parent_key}
        if existing and result.level != "error":
            touched = bool(plan["fields"] or plan["new_people"] or plan["new_attachments"] or plan["new_predecessors"]
                           or plan["parent_change"] or plan["baseline_due"] or plan["entities"])
            result.action = "update" if touched else "unchanged"
        if result.level == "error":
            result.action = "error"

        result.values = {
            "import_key": result.key, "title": plan["title"] or (existing or {}).get("title", ""),
            "owner": owner["display_name"] if owner else ((existing or {}).get("owner_user_id") and self._owner_name(existing) or ""),
            "start_date": display_date(plan["start_date"] or (existing or {}).get("start_date")),
            "due_date": display_date(plan["due_date"] or (existing or {}).get("due_date")),
            "status": display_status or "", "criticality": (plan["criticality"] if plan.get("criticality_given") else (existing or {}).get("criticality")) or "Unrated",
            "parent_key": parent_key or "", "predecessors": plan.get("predecessors", []),
            "milestone": bool(plan.get("milestone") if plan.get("milestone") is not None else (existing or {}).get("is_milestone")),
            "next_action": plan["next_action"], "extras": plan["extras"],
        }

    def _owner_name(self, task: dict) -> str:
        row = self.db.execute("SELECT display_name FROM users WHERE id=?", (task.get("owner_user_id"),)).fetchone()
        return row["display_name"] if row else ""

    def _key_of_task(self, task_id: str | None) -> str:
        task = self.existing_by_id.get(task_id) if task_id else None
        if not task:
            return ""
        return task.get("import_key") or task.get("title") or task_id

    @staticmethod
    def _display(name: str, value):
        if name in ("start_date", "due_date"):
            return display_date(value)
        if name == "owner_user_id":
            return value or "Unassigned"
        if value is None:
            return ""
        return value

    # ---- outputs ---------------------------------------------------------
    def summary(self) -> dict:
        counts = {"rows": len(self.rows), "create": 0, "update": 0, "unchanged": 0, "errors": 0, "warnings": 0,
                  "dependencies": 0}
        for result in self.rows:
            counts[result.action if result.action != "error" else "errors"] += 1
            if result.level == "warning":
                counts["warnings"] += 1
            if result.action != "error":
                counts["dependencies"] += len(result.plan.get("new_predecessors", []))
        file_keys = {result.key for result in self.rows}
        counts["not_in_file"] = sum(1 for key in self.existing_by_key if key not in file_keys)
        counts["project"] = {
            "id": self.project_id, "name": (self.project or {}).get("name") or self.new_project_name,
            "create": self.project is None,
        }
        return counts

    def preview(self) -> dict:
        return {
            "summary": self.summary(),
            "rows": [result.as_dict() for result in self.rows],
            "unknown_columns": self.unknown_columns,
            "file_warnings": self.file_warnings,
            "format": self.file_format,
            "custom_columns": [{"key": c.key, "label": c.label} for c in self.config.active if c.custom],
            "project_header": self.project_header,
            "people": self.people,
        }

    def report_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(REPORT_COLUMNS)
        for result in self.rows:
            values = result.values
            writer.writerow([clean_text(cell) for cell in (
                result.number, result.key, result.action, result.level, values.get("title", ""), values.get("owner", ""),
                values.get("start_date", ""), values.get("due_date", ""), values.get("status", ""),
                values.get("criticality", ""), result.plan.get("task_id") or (result.existing["id"] if result.existing else ""),
                " | ".join(f"{f.level.upper()} {f.code}: {f.message}" for f in result.findings),
            )])
        return buffer.getvalue()

    # ---- commit ----------------------------------------------------------
    def apply(self, service, project_id: str, import_id: str, *, valid_rows_only: bool) -> dict:
        """Write the plan. Must run inside the caller's transaction."""
        from .service import new_id, now_text  # local import: service imports this module

        actor_id = self.actor["id"]
        timestamp = now_text()
        rows = [r for r in self.rows if r.action != "error"]
        if not valid_rows_only and any(r.action == "error" for r in self.rows):
            raise ValueError("The file has rows with errors. Fix them or tick 'Import valid rows only'.")
        id_of: dict[str, str] = {key: task["id"] for key, task in self.existing_by_key.items()}
        created: list[RowResult] = []
        updated: list[RowResult] = []
        for result in rows:  # pass 1: tasks
            plan = result.plan
            if result.existing is None:
                task_id = new_id()
                id_of[result.key] = task_id
                plan["task_id"] = task_id
                fields = plan["fields"]
                self.db.execute(
                    """INSERT INTO tasks(id,project_id,parent_task_id,title,description,owner_user_id,status,criticality,
                       start_date,due_date,progress,created_at,created_by,updated_at,import_key,is_milestone,
                       next_action_note,import_extras) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (task_id, project_id, None, fields["title"], fields["description"], fields["owner_user_id"],
                     fields["status"], fields["criticality"], fields["start_date"], fields["due_date"], fields["progress"],
                     timestamp, actor_id, timestamp, result.key, fields["is_milestone"], fields["next_action_note"],
                     fields["import_extras"]),
                )
                if plan["baseline_due"]:
                    self.db.execute("UPDATE tasks SET baseline_start_date=?, baseline_due_date=? WHERE id=?",
                                    (fields["start_date"], plan["baseline_due"], task_id))
                created.append(result)
            elif result.action == "update":
                task_id = result.existing["id"]
                fields = plan["fields"]
                if fields:
                    assignments = ", ".join(f"{name}=?" for name in fields)
                    self.db.execute(
                        f"UPDATE tasks SET {assignments}, updated_at=?, revision=revision+1 WHERE id=?",
                        (*fields.values(), timestamp, task_id),
                    )
                else:
                    # Only lists or the parent changed: the row still moved (review DI-6).
                    self.db.execute("UPDATE tasks SET updated_at=?, revision=revision+1 WHERE id=?", (timestamp, task_id))
                if plan["baseline_due"]:
                    self.db.execute(
                        "UPDATE tasks SET baseline_start_date=start_date, baseline_due_date=? WHERE id=?"
                        " AND baseline_start_date IS NULL AND baseline_due_date IS NULL",
                        (plan["baseline_due"], task_id),
                    )
                updated.append(result)
        for result in rows:  # pass 2: hierarchy, baseline, people, attachments, entities
            task_id = id_of.get(result.key)
            if not task_id:
                continue
            plan = result.plan
            if plan.get("parent_change"):
                parent_id = id_of.get(plan["parent_key"])
                if parent_id:
                    before = {"parent_task_id": result.existing.get("parent_task_id") if result.existing else None}
                    self.db.execute("UPDATE tasks SET parent_task_id=? WHERE id=?", (parent_id, task_id))
                    if result.existing is not None:
                        service._event(task_id, actor_id, "parent_changed", before, {"parent_task_id": parent_id}, plan["reason"])
            service._ensure_baseline(task_id)
            for user_id, role in plan["new_people"]:
                self.db.execute("INSERT OR IGNORE INTO task_reviewers VALUES(?,?,?,?,?)",
                                (task_id, user_id, role, timestamp, actor_id))
            for path, display_name in plan["new_attachments"]:
                self.db.execute(
                    "INSERT INTO task_attachments(id,task_id,path,display_name,note,added_by,added_at) VALUES(?,?,?,?,?,?,?)",
                    (new_id(), task_id, path, display_name, f"Imported from {self.filename}", actor_id, timestamp),
                )
                service._event(task_id, actor_id, "attachment_added", None, {"path": path, "display_name": display_name}, None)
            for entity_id in plan["entities"]:
                self.db.execute("INSERT OR IGNORE INTO project_entities VALUES(?,?)", (project_id, entity_id))
        for result in created:  # pass 3a: creation events
            task_id = id_of[result.key]
            after = dict(self.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
            service._event(task_id, actor_id, "task_created", None, after, result.plan["reason"])
        for result in updated:  # pass 3b: update events (list additions ride in after_json, review DI-6)
            task_id = result.existing["id"]
            plan = result.plan
            additions = {}
            if plan["new_people"]:
                additions["people_added"] = [{"user_id": user_id, "role": role} for user_id, role in plan["new_people"]]
            if plan["new_attachments"]:
                additions["attachments_added"] = [path for path, _ in plan["new_attachments"]]
            if plan["new_predecessors"]:
                additions["predecessors_added"] = list(plan["new_predecessors"])
            if plan["entities"]:
                additions["entities_added"] = list(plan["entities"])
            if plan["fields"] or plan["baseline_due"] or additions:
                after = dict(self.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
                if additions:
                    after["import_additions"] = additions
                service._event(task_id, actor_id, "task_updated", result.existing, after, plan["reason"])
            if result.plan.get("criticality_change"):
                old, new = result.plan["criticality_change"]
                service._event(task_id, actor_id, "criticality_changed", {"criticality": old}, {"criticality": new},
                               result.plan["reason"])
        dependency_count = 0
        for result in rows:  # pass 4: dependencies
            task_id = id_of.get(result.key)
            for key in result.plan.get("new_predecessors", []):
                pred_id = id_of.get(key)
                if not pred_id or not task_id or pred_id == task_id:
                    continue
                self.db.execute("INSERT OR IGNORE INTO task_dependencies VALUES(?,?,?)", (pred_id, task_id, "finish_to_start"))
                service._event(task_id, actor_id, "dependency_added", None,
                               {"predecessor_task_id": pred_id, "successor_task_id": task_id,
                                "dependency_type": "finish_to_start", "created": True}, result.plan["reason"])
                dependency_count += 1
        summary = self.summary()
        summary["dependencies"] = dependency_count
        summary["skipped_errors"] = sum(1 for r in self.rows if r.action == "error")
        summary["import_id"] = import_id
        return summary
