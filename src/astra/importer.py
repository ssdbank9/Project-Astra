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
import os
import re
import struct
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import date
from xml.sax.saxutils import escape

from .xlsx_reader import CellError, XlsxError, column_letter, read_workbook

TEMPLATE_SHEET = "Tasks"
README_SHEET = "README"
MARKER_SHEET = "_astra"
MARKER_NAME = "AstraTemplateVersion"
FINGERPRINT_NAME = "AstraHeaderFingerprint"
# Sheet protection guards against accidental edits; it is not a secret. The
# password is documented so the App Owner can unlock a sheet deliberately.
TEMPLATE_SHEET_PASSWORD = "astra-template"
EXAMPLE_KEY = "EXAMPLE-001"

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
DATE_MIN = date(2000, 1, 1)
DATE_MAX = date(2100, 12, 31)
EXCEL_EPOCH = date(1899, 12, 30)
DISPLAY_DATE_FORMAT = "dd-mm-yyyy"

KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
ISO_DATE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T].*)?$")
DMY_DATE = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$")
PRED_SUFFIX = re.compile(r"^(?P<key>.+?)\s*(?P<type>FS|SS|FF|SF)?\s*(?P<lag>[+-]\s*\d+\s*d(?:ays?)?)?$", re.IGNORECASE)
LIST_SEPARATOR = ";"
CUSTOM_PREFIX = "x_"
CUSTOM_TYPES = ("text", "number", "date", "list")
CORE_KEYS = ("import_key", "title", "start_date", "due_date", "status", "owner_email")


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


STATUS_LABELS = (
    ("Draft", "draft"), ("Assigned", "assigned"), ("In progress", "in_progress"),
    ("Submitted", "submitted"), ("Changes requested", "changes_requested"),
    ("Completed", "completed"), ("On hold", "on_hold"), ("Delayed", "delayed"),
    ("Cancelled", "cancelled"), ("Abandoned", "abandoned"), ("Reopened", "reopened"),
)
CRITICALITY_LABELS = ("Critical", "High", "Normal", "Low")

COLUMNS: tuple[Column, ...] = (
    Column("Import Key", "import_key", "string", required=True,
           aliases=("Key", "ID", "UID", "Task ID", "External ID", "#"), width=14, example="RA-001",
           prompt="Stable id for this row. Re-importing the same key updates the task instead of duplicating it."),
    Column("Project", "project", "string", aliases=("Project Name",), width=30,
           example="Rupani Academy — DP & CP Implementation Roadmap",
           prompt="Leave blank when you pick the project on the Import screen. App Owner only."),
    Column("Entity", "entity", "string_list", aliases=("Entities", "Filing Entity"), width=20, example="",
           prompt="Existing entity names, separated by ';'. App Owner only."),
    Column("Parent Key", "parent_key", "string",
           aliases=("Parent", "Subtask Of", "Parent ID", "Parent Import Key"), width=12, example="",
           prompt="Import Key of the task this row is a step of."),
    Column("Title", "title", "string", required=True,
           aliases=("Task", "Task Name", "Name", "Action Item / Deliverable", "Action / Deliverable"), width=48,
           example="Submit CP application and upload evidence receipt", prompt="Required. Up to 200 characters."),
    Column("Description", "description", "text", aliases=("Details", "Notes/Description"), width=36,
           example="Application to the IB for Career-related Programme candidacy."),
    Column("Owner Email", "owner_email", "email",
           aliases=("Owner", "Task Owner", "Assignee", "Responsible", "Assigned To"), width=26,
           example="jamal@example.org", prompt="One work email of a user who already has access to the project."),
    Column("Collaborators", "collaborators", "email_list", aliases=("Collaborator Emails", "Contributors"), width=26,
           example="", prompt="Emails separated by ';'."),
    Column("Reviewers", "reviewers", "email_list", aliases=("Reviewer Emails",), width=22, example="",
           prompt="Emails separated by ';'."),
    Column("Approvers", "approvers", "email_list", aliases=("Approver Emails",), width=22, example="",
           prompt="Emails separated by ';'."),
    Column("Start Date", "start_date", "date", aliases=("Start", "Planned Start"), width=13, example="01-09-2026",
           prompt="A real date (dd-mm-yyyy). Never type TBD here; use Notes."),
    Column("Due Date", "due_date", "date",
           aliases=("Due", "Finish", "End Date", "Deadline", "Due / Milestone", "Revised Due Date"), width=13,
           example="07-09-2026", prompt="A real date (dd-mm-yyyy). Never type TBD here; use Notes."),
    Column("Duration (days)", "duration_days", "integer", aliases=("Duration", "Days"), width=10, example="",
           prompt="Whole days, used only when one of Start/Due is blank."),
    Column("Original Due Date", "baseline_due_date", "date",
           aliases=("Baseline Due", "Baseline Finish", "Original Deadline"), width=13, example="",
           prompt="Only when the sheet already carries a revised date. App Owner only."),
    Column("Status", "status", "enum", allowed=tuple(label for label, _ in STATUS_LABELS), width=16,
           example="Draft", prompt="Pick from the list. Delayed / On hold / Cancelled need a Reason."),
    Column("% Complete", "progress", "integer", aliases=("Percent Complete", "Progress", "PercentComplete", "Complete %"),
           width=10, example="", prompt="Whole number 0-100."),
    Column("Criticality", "criticality", "enum", allowed=CRITICALITY_LABELS, width=12, example="High",
           prompt="Critical, High, Normal, Low or blank (Unrated)."),
    Column("Predecessors", "predecessors", "string_list", aliases=("Depends On", "Predecessor Keys", "Blocked By"),
           width=18, example="", prompt="Import Keys this row waits for (finish-to-start), separated by ';'."),
    Column("Milestone", "milestone", "boolean", allowed=("Yes", "No"), width=10, example="No",
           prompt="Yes or No."),
    Column("Next Action", "next_action", "string", aliases=("Next Step", "Decision / Support Required", "Decision / Support"),
           width=32, example="Confirm vendor/approach", prompt="Up to 200 characters."),
    Column("Reason", "reason", "string", aliases=("Reason if Delayed / At Risk", "Change Reason"), width=26, example="",
           prompt="Why the status or dates changed. Required by Astra for Delayed / On hold / Cancelled."),
    Column("Notes", "notes", "text", aliases=("Comments", "Risk / Dependency", "Remarks"), width=36,
           example="Due as written in the source: Immediate", prompt="Free text, appended to the description."),
    Column("Attachment Links", "attachment_links", "string_list", aliases=("Attachments", "Links", "Evidence Links"),
           width=30, example="", prompt="Paths or URLs separated by ';'. App Owner only."),
)
COLUMN_BY_KEY = {column.key: column for column in COLUMNS}

_STATUS_BY_LABEL = {label.casefold(): code for label, code in STATUS_LABELS}
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
MANAGER_ORDINARY = {"draft", "assigned", "in_progress", "delayed"}
NO_RECORD_ON_CREATE = {"submitted", "changes_requested", "completed", "on_hold", "reopened"}
CLOSED = {"completed", "cancelled", "abandoned"}


class ImportFileError(ValueError):
    """The whole file is unusable (format, headers, limits)."""


class ImportConflict(ValueError):
    """The bytes sent to commit differ from the previewed bytes."""


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
    return unicodedata.normalize("NFC", str(value)).strip()


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def split_list(value) -> list[str]:
    text = normalize_text(value)
    if not text:
        return []
    return [item.strip() for item in text.split(LIST_SEPARATOR) if item.strip()]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def _xml(text: str) -> str:
    """Escape for attribute values (quotes included)."""
    return escape(str(text), {'"': "&quot;"})


def _xml_text(text: str) -> str:
    """Escape for element text, where quotes may stay literal."""
    return escape(str(text))


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
        if self.kind == "list":
            return "Pick from the list: " + ", ".join(self.values)
        if self.kind == "date":
            return "A real date (dd-mm-yyyy)."
        if self.kind == "number":
            return "A number."
        return "Free text."

    @property
    def width(self) -> int:
        return self.builtin.width if self.builtin else 18

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
        return cls([{"key": column.key, "label": column.header, "enabled": True, "custom": False} for column in COLUMNS])

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
                base, suffix = key, 2
                while key in seen_keys or key in COLUMN_BY_KEY:
                    key = f"{base}_{suffix}"
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


# --------------------------------------------------------------------------- template workbook

def _inline(ref: str, text: str, style: int) -> str:
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{_xml_text(text)}</t></is></c>'


def _number(ref: str, value, style: int) -> str:
    return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'


def _protection_xml(hash_value: str, salt_value: str, spin: int, *, allow_edit_rows: bool) -> str:
    # In <sheetProtection> a "1" LOCKS the action. Widening columns and adding or
    # removing data rows stay allowed on the Tasks sheet; inserting or deleting
    # columns and sorting are locked so the header contract survives.
    rows = "0" if allow_edit_rows else "1"
    return (
        f'<sheetProtection algorithmName="SHA-512" hashValue="{hash_value}" saltValue="{salt_value}" '
        f'spinCount="{spin}" sheet="1" objects="1" scenarios="1" formatCells="1" formatColumns="0" '
        f'formatRows="{rows}" insertColumns="1" insertRows="{rows}" insertHyperlinks="1" deleteColumns="1" '
        f'deleteRows="{rows}" sort="1" autoFilter="1" pivotTables="1" selectLockedCells="0" selectUnlockedCells="0"/>'
    )


def _validation(kind: str, sqref: str, prompt_title: str, prompt: str, error: str, **attrs) -> str:
    formulas = ""
    if "formula1" in attrs:
        formulas += f"<formula1>{_xml_text(attrs.pop('formula1'))}</formula1>"
    if "formula2" in attrs:
        formulas += f"<formula2>{_xml_text(attrs.pop('formula2'))}</formula2>"
    extra = "".join(f' {name}="{_xml(value)}"' for name, value in attrs.items())
    return (
        f'<dataValidation type="{kind}"{extra} allowBlank="1" showInputMessage="1" showErrorMessage="1" '
        f'errorStyle="stop" errorTitle="Astra import template" error="{_xml(error[:255])}" '
        f'promptTitle="{_xml(prompt_title[:32])}" prompt="{_xml(prompt[:255])}" sqref="{sqref}">{formulas}</dataValidation>'
    )


def readme_lines(config: TemplateConfig) -> list[str]:
    status_list = ", ".join(label for label, _ in STATUS_LABELS)
    lines = [
        "Astra import template — how to fill the Tasks sheet",
        f"Template version {config.hash()}. Keep the header row exactly as it is: Astra checks it on upload, "
        "and rejects a template downloaded before the App Owner changed the column settings.",
        "",
        "1. One row per task or step. Keep Import Key stable forever — it is how a re-import updates a task instead of duplicating it.",
        f"2. Delete or overwrite the example row (Import Key {EXAMPLE_KEY}); Astra refuses to import it.",
        "3. Dates must be real dates, shown as dd-mm-yyyy (for example 07-09-2026). Never type TBD, Immediate or 'Sept 7-10' in a date column — put that text in Notes and leave the date blank.",
        "4. People by work email. The person must already exist in Astra and have access to the project (the App Owner adds users and grants access in the People panel).",
        "5. A step (subtask) is a row whose Parent Key is another row's Import Key or the key of a task already in the project.",
        "6. Predecessors = the Import Keys this row waits for (finish-to-start), separated by ';'.",
        f"7. Status values: {status_list}. Synonyms such as Not Started, Done, Delayed/At Risk, Blocked are accepted.",
        "   Delayed, On hold, Cancelled, Abandoned and Reopened need a Reason. Completed, Submitted, On hold and Reopened are recorded on first import only and are skipped on re-import because they need their lifecycle action in Astra.",
        "8. Criticality: Critical, High, Normal, Low or blank (Unrated). Milestone: Yes or No. % Complete: 0-100.",
        "9. Project, Entity, Original Due Date and Attachment Links are applied only when the App Owner imports; a project Manager's import skips them with a warning.",
        "10. Anything Astra cannot store exactly is written to the task's Notes and listed in the import report. Nothing is deleted by an import and an existing baseline is never overwritten.",
        "11. Preview first: the Import screen shows every row with its warnings and errors before anything is written.",
        f"12. The Tasks and README sheets are protected against accidental edits (password: {TEMPLATE_SHEET_PASSWORD}). Data rows are editable; the header is not.",
        "",
        "Columns:",
    ]
    for column in config.active:
        flags = " (required)" if column.required else ""
        lines.append(f"{column.label}{flags}: {column.prompt}")
    return lines


def build_template_xlsx(config: TemplateConfig | None = None) -> bytes:
    """Return the locked Astra template workbook for this configuration (zipfile, no dependencies)."""
    config = config or TemplateConfig.default()
    salt = os.urandom(16)
    spin = 100000
    hash_value = _protection_hash(TEMPLATE_SHEET_PASSWORD, salt, spin)
    salt_value = base64.b64encode(salt).decode("ascii")
    last_row = TEMPLATE_DATA_ROWS + 1
    columns = config.active
    last_col = column_letter(len(columns))

    # ---- styles: 0 default locked, 1 header, 2 unlocked text, 3 unlocked date, 4 wrapped text, 5 unlocked integer, 6 unlocked number
    styles = (
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<numFmts count="1"><numFmt numFmtId="164" formatCode="{DISPLAY_DATE_FORMAT}"/></numFmts>'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>'
        '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF172A46"/><bgColor indexed="64"/></patternFill></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="7">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">'
        '<alignment vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyProtection="1"><protection locked="0"/></xf>'
        '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyProtection="1">'
        '<protection locked="0"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
        '<xf numFmtId="1" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyProtection="1">'
        '<protection locked="0"/></xf>'
        '<xf numFmtId="2" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyProtection="1">'
        '<protection locked="0"/></xf>'
        '</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'
    )

    def data_style(column: ActiveColumn) -> int:
        if column.kind == "date":
            return 3
        if column.kind == "integer":
            return 5
        if column.kind == "number":
            return 6
        return 2

    cols = "".join(
        f'<col min="{index}" max="{index}" width="{column.width}" customWidth="1" style="{data_style(column)}"/>'
        for index, column in enumerate(columns, start=1)
    )
    header_cells = "".join(
        _inline(f"{column_letter(index)}1", column.label, 1) for index, column in enumerate(columns, start=1)
    )
    example_cells = []
    for index, column in enumerate(columns, start=1):
        ref = f"{column_letter(index)}2"
        value = EXAMPLE_KEY if column.key == "import_key" else column.example
        if not value:
            continue
        if column.kind == "date":
            parsed, _ = parse_date_cell(value, allow_serial=False)
            example_cells.append(_number(ref, excel_serial(parsed), 3))
        else:
            example_cells.append(_inline(ref, value, data_style(column)))
    validations = []
    for index, column in enumerate(columns, start=1):
        letters = column_letter(index)
        sqref = f"{letters}2:{letters}{last_row}"
        if column.kind in ("enum", "boolean", "list"):
            validations.append(_validation(
                "list", sqref, column.label, column.prompt, "Choose a value from the list.",
                formula1='"' + ",".join(column.values) + '"',
            ))
        elif column.kind == "date":
            validations.append(_validation(
                "date", sqref, column.label, "A real date between 01-01-2000 and 31-12-2100 (dd-mm-yyyy).",
                "Enter a real date between 01-01-2000 and 31-12-2100. Put TBD or prose in Notes instead.",
                operator="between", formula1=str(excel_serial(DATE_MIN)), formula2=str(excel_serial(DATE_MAX)),
            ))
        elif column.key == "progress":
            validations.append(_validation(
                "whole", sqref, column.label, column.prompt, "Enter a whole number from 0 to 100.",
                operator="between", formula1="0", formula2="100",
            ))
        elif column.key == "duration_days":
            validations.append(_validation(
                "whole", sqref, column.label, column.prompt, "Enter a whole number of days (1 to 3660).",
                operator="between", formula1="1", formula2="3660",
            ))
        elif column.kind == "number":
            validations.append(_validation(
                "decimal", sqref, column.label, column.prompt, "Enter a number.",
                operator="between", formula1="-1000000000000", formula2="1000000000000",
            ))
        elif column.key == "import_key":
            validations.append(_validation(
                "textLength", sqref, column.label, column.prompt, f"Import Key must be 1 to {MAX_KEY_CHARS} characters.",
                operator="between", formula1="1", formula2=str(MAX_KEY_CHARS),
            ))
        elif column.key == "title":
            validations.append(_validation(
                "textLength", sqref, column.label, column.prompt, f"Title must be 1 to {MAX_TITLE_CHARS} characters.",
                operator="between", formula1="1", formula2=str(MAX_TITLE_CHARS),
            ))
        else:
            validations.append(_validation("custom", sqref, column.label, column.prompt, column.prompt, formula1="TRUE"))
    tasks_sheet = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:{last_col}2"/>'
        '<sheetViews><sheetView tabSelected="1" workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/></sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f'<cols>{cols}</cols>'
        f'<sheetData><row r="1" ht="30" customHeight="1">{header_cells}</row><row r="2">{"".join(example_cells)}</row></sheetData>'
        + _protection_xml(hash_value, salt_value, spin, allow_edit_rows=True)
        + f'<dataValidations count="{len(validations)}">{"".join(validations)}</dataValidations>'
        '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        '</worksheet>'
    )

    lines = readme_lines(config)
    readme_rows = "".join(
        f'<row r="{index}">{_inline(f"A{index}", line, 4)}</row>' for index, line in enumerate(lines, start=1) if line
    )
    readme_sheet = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:A{len(lines)}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews><sheetFormatPr defaultRowHeight="15"/>'
        '<cols><col min="1" max="1" width="120" customWidth="1" style="4"/></cols>'
        f'<sheetData>{readme_rows}</sheetData>'
        + _protection_xml(hash_value, salt_value, spin, allow_edit_rows=False)
        + '</worksheet>'
    )
    marker_sheet = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<dimension ref="A1:B2"/><sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/><sheetData>'
        f'<row r="1">{_inline("A1", MARKER_NAME, 0)}{_inline("B1", config.hash(), 0)}</row>'
        f'<row r="2">{_inline("A2", FINGERPRINT_NAME, 0)}{_inline("B2", "|".join(config.labels()), 0)}</row>'
        '</sheetData>' + _protection_xml(hash_value, salt_value, spin, allow_edit_rows=False) + '</worksheet>'
    )
    workbook = (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<workbookPr/><bookViews><workbookView xWindow="0" yWindow="0" windowWidth="20000" windowHeight="12000"/></bookViews>'
        f'<sheets><sheet name="{TEMPLATE_SHEET}" sheetId="1" r:id="rId1"/>'
        f'<sheet name="{README_SHEET}" sheetId="2" r:id="rId2"/>'
        f'<sheet name="{MARKER_SHEET}" sheetId="3" state="hidden" r:id="rId3"/></sheets>'
        f'<definedNames><definedName name="{MARKER_NAME}">{MARKER_SHEET}!$B$1</definedName>'
        f'<definedName name="{FINGERPRINT_NAME}">{MARKER_SHEET}!$B$2</definedName></definedNames>'
        '</workbook>'
    )
    workbook_rels = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>'
        '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>'
    )
    root_rels = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    content_types = (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'
    )
    declaration = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", declaration + content_types)
        archive.writestr("_rels/.rels", declaration + root_rels)
        archive.writestr("xl/workbook.xml", declaration + workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", declaration + workbook_rels)
        archive.writestr("xl/styles.xml", declaration + styles)
        archive.writestr("xl/worksheets/sheet1.xml", declaration + tasks_sheet)
        archive.writestr("xl/worksheets/sheet2.xml", declaration + readme_sheet)
        archive.writestr("xl/worksheets/sheet3.xml", declaration + marker_sheet)
    return buffer.getvalue()


def build_template_csv(config: TemplateConfig | None = None) -> str:
    config = config or TemplateConfig.default()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(config.labels())
    writer.writerow([EXAMPLE_KEY if column.key == "import_key" else column.example for column in config.active])
    return buffer.getvalue()


# --------------------------------------------------------------------------- upload parsing

@dataclass
class ParsedRow:
    number: int
    cells: dict[str, object]                               # column key -> raw cell value
    aliased: dict[str, str] = field(default_factory=dict)  # column key -> header text matched by alias


@dataclass
class ParsedUpload:
    format: str                                            # xlsx | csv
    rows: list[ParsedRow]
    unknown_columns: list[str]
    file_warnings: list[str]
    sheet_name: str = ""


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
        raise ImportFileError("The file is larger than 5 MB. Split it or remove unused sheets and try again.")
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
    if sheet is None:
        candidates = [s for s in workbook.sheets if not s.hidden and s.name not in (README_SHEET, MARKER_SHEET)]
        sheet = candidates[0] if candidates else None
    if sheet is None or not sheet.rows:
        raise ImportFileError(f"The workbook has no '{TEMPLATE_SHEET}' sheet with data. " + _template_hint())
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
    for number, values in sheet.iter_rows(len(labels)):
        if number == header_row_number:
            continue
        cells = {}
        for column, value in zip(config.active, values):
            if isinstance(value, str):
                value = unicodedata.normalize("NFC", value).strip()
            if value is None or value == "":
                continue
            cells[column.key] = value
        if cells:
            rows.append(ParsedRow(number=number, cells=cells))
    if len(rows) > MAX_ROWS:
        raise ImportFileError(f"The sheet has more than {MAX_ROWS} data rows. Split the file and import in parts.")
    return ParsedUpload(format="xlsx", rows=rows, unknown_columns=[], file_warnings=[], sheet_name=sheet.name)


def _decode_csv(data: bytes) -> tuple[str, list[str]]:
    warnings = []
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
    records = list(csv.reader(io.StringIO(text), delimiter=delimiter))
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

def parse_date_cell(value, *, allow_serial: bool):
    """Return (date|None, error_message|None). Prose is never guessed."""
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
        if float(value) <= 60:
            return None, f"Excel date serial {value} is before 01-03-1900 and cannot be interpreted safely."
        parsed = date.fromordinal(EXCEL_EPOCH.toordinal() + int(value))
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
        return value, None
    text = normalize_text(value).replace(",", "")
    try:
        number = float(text)
    except ValueError:
        return None, f"'{text}' is not a number."
    return (int(number) if number.is_integer() else number), None


def parse_progress(value):
    if value is None or value == "":
        return None, None
    if isinstance(value, float) and 0 < value < 1:
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


def parse_predecessor(item: str, known_keys: set[str]):
    """Return (key, dependency_type, lag_text, error). A suffix (FS+2d) is only
    split off when the bare text is not itself a known key."""
    text = item.strip()
    if text in known_keys:
        return text, "FS", "", None
    match = PRED_SUFFIX.match(text)
    if match and (match.group("type") or match.group("lag")):
        key = match.group("key").strip()
        if KEY_PATTERN.match(key):
            return key, (match.group("type") or "FS").upper(), (match.group("lag") or "").replace(" ", ""), None
    if KEY_PATTERN.match(text):
        return text, "FS", "", None
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
        self._load_context()

    # ---- context ---------------------------------------------------------
    def _load_context(self) -> None:
        users = self.db.execute("SELECT id,email,display_name,active,global_role FROM users").fetchall()
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
                    self.existing_by_key[task["import_key"]] = task
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
        return user["id"] in self.members

    def _resolve_person(self, text: str, result: RowResult, column: str):
        """Return a user dict or None, adding findings. Email first, then a unique display name."""
        text = text.strip()
        if "@" in text:
            user = self.users_by_email.get(text.casefold())
            if not user:
                result.add("warning", "W_UNRESOLVED_PERSON", f"No Astra user has the email '{text}'.", column)
                return None
        else:
            matches = self.users_by_name.get(collapse(text), [])
            if len(matches) != 1:
                reason = "matches several users" if matches else "is not an Astra user"
                result.add("warning", "W_UNRESOLVED_PERSON",
                           f"'{text}' {reason}; use the person's email.", column)
                return None
            user = matches[0]
            result.add("warning", "W_PERSON_BY_NAME", f"'{text}' was matched by name to {user['email']}.", column)
        if not self._eligible(user):
            where = "the new project" if not self.project_id else "this project"
            result.add("warning", "W_PERSON_NOT_ELIGIBLE",
                       f"{user['email']} is inactive or has no access to {where}; grant access, then re-import.", column)
            return None
        return user

    def _default_reason(self, row: RowResult) -> str:
        return self.default_reason or f"Excel import {self.filename} row {row.number}"

    # ---- validation ------------------------------------------------------
    def validate(self, parsed: ParsedUpload) -> dict:
        self.unknown_columns = parsed.unknown_columns
        self.file_warnings = list(parsed.file_warnings)
        self.file_format = parsed.format
        self.rows = [self._validate_row(row) for row in parsed.rows]
        self._check_duplicate_keys()
        self._check_project_column()
        self._wire_parents()
        self._wire_dependencies()
        for result in self.rows:
            self._finish_row(result)
        return self.preview()

    def _validate_row(self, row: ParsedRow) -> RowResult:
        result = RowResult(number=row.number)
        cells = row.cells
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

        key = text.get("import_key", "")
        result.key = key
        if not key:
            result.add("error", "E_KEY_MISSING", "Import Key is required.", "Import Key")
        elif not KEY_PATTERN.match(key):
            result.add("error", "E_KEY_INVALID",
                       f"'{key}' is not a valid Import Key (letters, digits, . _ - up to {MAX_KEY_CHARS} characters).",
                       "Import Key")
        elif key == EXAMPLE_KEY:
            result.add("error", "E_EXAMPLE_ROW", "This is the template's example row. Delete it or give it a real key.",
                       "Import Key")
        existing = self.existing_by_key.get(key) if key else None
        if key and not existing:
            other = self.db.execute(
                "SELECT p.name FROM tasks t JOIN projects p ON p.id=t.project_id WHERE t.import_key=? AND t.project_id<>? LIMIT 1",
                (key, self.project_id or ""),
            ).fetchone()
            if other:
                result.add("error", "E_KEY_OTHER_PROJECT",
                           f"Import Key '{key}' already belongs to a task in project '{other['name']}'. "
                           "Cross-project moves are manual Owner actions.", "Import Key")
        result.existing = existing
        result.action = "update" if existing else "create"
        is_manager_import = not self.is_owner

        title = text.get("title", "")
        if not title:
            result.add("error", "E_TITLE_MISSING", "Title is required.", "Title")
        elif len(title) > MAX_TITLE_CHARS:
            result.add("error", "E_TITLE_TOO_LONG", f"Title has {len(title)} characters; the limit is {MAX_TITLE_CHARS}.", "Title")

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

        allow_serial = self.file_format == "xlsx"
        dates = {}
        for date_key, label in (("start_date", "Start Date"), ("due_date", "Due Date"), ("baseline_due_date", "Original Due Date")):
            parsed, error = parse_date_cell(cells.get(date_key), allow_serial=allow_serial)
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
                parsed, error = parse_date_cell(raw, allow_serial=allow_serial)
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

        pred_items = split_list(cells.get("predecessors"))
        result.plan = {
            "title": title, "description": text.get("description", ""), "notes": text.get("notes", ""),
            "owner": owner, "people": people_lists, "start_date": start.isoformat() if start else None,
            "due_date": due.isoformat() if due else None,
            "baseline_due": dates["baseline_due_date"].isoformat() if dates["baseline_due_date"] else None,
            "status_value": status_value, "progress": progress, "criticality": criticality,
            "criticality_given": bool(text.get("criticality")), "milestone": milestone,
            "next_action": next_action, "reason": text.get("reason", ""), "attachments": attachments,
            "entities": entity_ids, "extras": extras, "parent_key": text.get("parent_key", ""),
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
        for result in self.rows:
            text = result.plan.get("project_text", "")
            if text and target_name and collapse(text) != collapse(target_name):
                result.add("error", "E_PROJECT_MISMATCH",
                           f"Project '{text}' does not match the target project '{target_name}'. Leave the cell blank or fix it.",
                           "Project")

    def _row_index(self) -> dict[str, RowResult]:
        return {result.key: result for result in self.rows if result.key}

    def _wire_parents(self) -> None:
        by_key = self._row_index()

        def parent_node(node):
            """node is an import key (file row) or a task id (DB-only task)."""
            if node in by_key:
                row = by_key[node]
                parent_key = row.plan.get("parent_key")
                if parent_key:
                    return parent_key
                if row.existing:
                    parent_id = row.existing.get("parent_task_id")
                    return self._node_for_task(parent_id) if parent_id else None
                return None
            task = self.existing_by_id.get(node)
            parent_id = task.get("parent_task_id") if task else None
            return self._node_for_task(parent_id) if parent_id else None

        changed = True
        while changed:
            changed = False
            invalid = {result.key for result in self.rows if result.key and result.level == "error"}
            for result in self.rows:
                parent_key = result.plan.get("parent_key")
                if not parent_key or result.level == "error" or result.plan.get("parent_checked"):
                    continue
                if parent_key == result.key:
                    result.add("error", "E_PARENT_SELF", "A task cannot be its own parent.", "Parent Key")
                elif parent_key in invalid:
                    result.add("error", "E_PARENT_INVALID", f"Parent '{parent_key}' has errors and will not import.",
                               "Parent Key")
                elif parent_key not in by_key and parent_key not in self.existing_by_key:
                    result.add("error", "E_PARENT_UNKNOWN",
                               f"Parent Key '{parent_key}' is neither in this file nor an existing task of the project.",
                               "Parent Key")
                else:
                    node, seen = parent_key, set()
                    while node and node not in seen:
                        if node == result.key:
                            result.add("error", "E_PARENT_CYCLE", f"Parent '{parent_key}' would create a subtask cycle.",
                                       "Parent Key")
                            break
                        seen.add(node)
                        node = parent_node(node)
                    else:
                        depth = len(seen)
                        if depth > 2:
                            result.add("warning", "W_PARENT_DEPTH",
                                       "Steps nested more than two levels deep render as one level in the Gantt.",
                                       "Parent Key")
                        result.plan["parent_checked"] = True
                if result.level == "error":
                    changed = True

    def _node_for_task(self, task_id: str | None):
        task = self.existing_by_id.get(task_id) if task_id else None
        if task and task.get("import_key") and task["import_key"] in {r.key for r in self.rows}:
            return task["import_key"]
        return task_id

    def _wire_dependencies(self) -> None:
        by_key = self._row_index()
        known = set(by_key) | set(self.existing_by_key)
        graph: dict[str, set] = {}
        for pred_id, succ_id in self.existing_edges:
            graph.setdefault(self._node_for_task(pred_id), set()).add(self._node_for_task(succ_id))

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
                if reaches(result.key, key):
                    result.add("error", "E_DEP_CYCLE", f"Depending on '{key}' would create a cycle.", "Predecessors")
                    continue
                if key not in edges:
                    edges.append(key)
                    graph.setdefault(key, set()).add(result.key)
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
                "import_extras": json.dumps(plan["extras"], ensure_ascii=False, sort_keys=True) if plan["extras"] else None,
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
                    if self.is_owner and target in GOVERNED:
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
                    change("import_extras", json.dumps(merged, ensure_ascii=False, sort_keys=True))
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
            plan["parent_change"] = not existing or target_parent_id != current_parent
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
        }

    def report_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(REPORT_COLUMNS)
        for result in self.rows:
            values = result.values
            writer.writerow([
                result.number, result.key, result.action, result.level, values.get("title", ""), values.get("owner", ""),
                values.get("start_date", ""), values.get("due_date", ""), values.get("status", ""),
                values.get("criticality", ""), result.plan.get("task_id") or (result.existing["id"] if result.existing else ""),
                " | ".join(f"{f.level.upper()} {f.code}: {f.message}" for f in result.findings),
            ])
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
        for result in updated:  # pass 3b: update events
            task_id = result.existing["id"]
            if result.plan["fields"] or result.plan["baseline_due"]:
                after = dict(self.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
                service._event(task_id, actor_id, "task_updated", result.existing, after, result.plan["reason"])
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
