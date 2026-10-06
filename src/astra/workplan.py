"""Small, project-bound CSV contract for owner workplans and alternative plans."""
from __future__ import annotations

import csv
import io
import json

MARKER = "Astra Workplan CSV"
VERSION = "1"
PLAN_KEY = "x_plan"
FIELDS = (
    ("import_key", "Task ID"), ("title", "Task"), ("parent_key", "Part of"),
    ("owner_email", "Assigned To"), ("start_date", "Start"), ("due_date", "Finish"),
    ("predecessors", "Predecessors"), ("x_type", "Type"), (PLAN_KEY, "Plan"),
)


def config():
    from . import importer
    columns = {c["key"]: dict(c) for c in importer.FULL_TEMPLATE_COLUMNS}
    columns[PLAN_KEY] = {"key": PLAN_KEY, "custom": True, "type": "text", "values": [], "required": False}
    return importer.TemplateConfig([{**columns[key], "label": label, "enabled": True} for key, label in FIELDS])


def plan(task):
    raw = task.get("import_extras")
    try:
        extras = json.loads(raw) if isinstance(raw, str) else (raw or {})
        return str(extras.get(PLAN_KEY) or "Shared").strip() or "Shared"
    except (ValueError, AttributeError):
        return "Shared"


def compatible(source, target):
    """A common prerequisite may feed a branch; a branch cannot feed Shared."""
    return source == "Shared" or source == target


def encode(value):
    text = "" if value is None else str(value)
    if text.startswith("'") or text.lstrip().startswith(("=", "+", "-", "@")) or text.lstrip(" ").startswith(("\t", "\r")):
        return "'" + text
    return text


def decode(value):
    return value[1:] if value.startswith("'") else value


def build(project, entities, tasks, *, blank_keys=()):
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    def line(values):
        writer.writerow([encode(v) for v in values] + [""] * (len(FIELDS) - len(values)))
    line([MARKER, VERSION, "apostrophe-v1"])
    line(["Project ID", project["id"]])
    line(["Project", project["name"]])
    line(["Entity IDs", json.dumps(sorted(e["id"] for e in entities))])
    line(["Entities", "; ".join(e["name"] for e in entities)])
    line([label for _, label in FIELDS])
    for task in tasks:
        values = dict(task)
        values.setdefault(PLAN_KEY, "Shared")
        line([values.get(key, "") for key, _ in FIELDS])
    for key in blank_keys:
        line([key])
    return output.getvalue()


def parse(data):
    from . import importer
    text, warnings = importer._decode_csv(data)
    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
    except csv.Error:
        delimiter = ","
    try:
        records = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
    except csv.Error as exc:
        raise importer.ImportFileError("The workplan CSV is malformed.") from exc
    if len(records) < 6 or records[0][:3] != [MARKER, VERSION, "apostrophe-v1"]:
        raise importer.ImportFileError("Unknown workplan CSV version. Download a fresh CSV from Astra.")
    records = [[decode(cell) for cell in row] for row in records]
    labels = [label for _, label in FIELDS]
    expected = ["Project ID", "Project", "Entity IDs", "Entities"]
    if [row[0] if row else "" for row in records[1:5]] != expected or records[5] != labels:
        raise importer.ImportFileError("The workplan identity or task headers changed. Download a fresh CSV.")
    metadata = {row[0]: row[1] for row in records[1:5] if len(row) >= 2}
    try:
        entity_ids = json.loads(metadata["Entity IDs"])
        if not isinstance(entity_ids, list) or any(not isinstance(v, str) for v in entity_ids):
            raise ValueError()
    except (KeyError, ValueError) as exc:
        raise importer.ImportFileError("The workplan entity identifiers are invalid.") from exc
    rows = []
    for number, record in enumerate(records[6:], start=7):
        if len(record) > len(FIELDS):
            raise importer.ImportFileError("A workplan row has more columns than its header.")
        cells = {key: value for (key, _), value in zip(FIELDS, record) if value != ""}
        if not any(value.strip() for key, value in cells.items() if key != "import_key"):
            continue  # Astra's prefilled spare keys are unused, not incomplete tasks.
        rows.append(importer.ParsedRow(number=number, cells=cells))
    if len(rows) > importer.MAX_ROWS:
        raise importer.ImportTooLarge("The workplan has too many task rows.")
    return importer.ParsedUpload(format="csv", rows=rows, unknown_columns=[], file_warnings=warnings,
                                 workplan={"project_id": metadata.get("Project ID", ""), "entity_ids": entity_ids})
