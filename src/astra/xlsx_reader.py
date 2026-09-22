"""Minimal .xlsx reader built on the standard library only (zipfile + xml.etree).

Astra deliberately carries no third-party dependency, so the import feature reads
Office Open XML workbooks directly. The reader covers what a task list needs:

- the sheet list from ``xl/workbook.xml`` and its relationship targets (absolute
  ``/xl/worksheets/sheet1.xml`` or relative ``worksheets/sheet1.xml``);
- shared strings (plain and rich-text runs) and inline strings (``t="str"`` and
  ``t="inlineStr"``);
- number formats from ``xl/styles.xml`` so that a numeric cell styled as a date is
  returned as a :class:`datetime.date`;
- the 1900 and 1904 date systems (epoch 1899-12-30 or 1904-01-01); serials at or
  below 60 under the 1900 system fall before the Lotus leap-year bug and are
  rejected as ambiguous rather than guessed;
- sheets without a ``<dimension>`` element (the used range is computed from the
  cell references that are present);
- hidden sheets and defined names (used for the template's version marker).

Cells are returned as ``str``, ``int``, ``float``, ``bool``, ``datetime.date``,
``None`` (empty) or :class:`CellError` (a value that exists but cannot be
interpreted safely, with the reason).
"""
from __future__ import annotations

import io
import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from xml.etree import ElementTree as ET

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

MAX_ZIP_MEMBERS = 200
MAX_MEMBER_BYTES = 50 * 1024 * 1024

# Built-in number formats that render as dates (ECMA-376 18.8.30). Ids 27-36 and
# 50-58 are the East-Asian locale date formats.
BUILTIN_DATE_FORMATS = set(range(14, 23)) | set(range(27, 37)) | {45, 46, 47} | set(range(50, 59))

_CELL_REF = re.compile(r"^([A-Z]+)(\d+)$")


class XlsxError(ValueError):
    """The bytes are not a workbook this reader can use."""


@dataclass(frozen=True)
class CellError:
    """A cell whose value exists but cannot be interpreted safely."""

    message: str

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.message


@dataclass
class Sheet:
    name: str
    index: int
    hidden: bool
    rows: dict[int, dict[int, object]] = field(default_factory=dict)

    @property
    def max_row(self) -> int:
        return max(self.rows) if self.rows else 0

    @property
    def max_col(self) -> int:
        return max((max(cells) for cells in self.rows.values() if cells), default=0)

    def row_values(self, row_number: int, width: int | None = None) -> list:
        cells = self.rows.get(row_number, {})
        width = width or (max(cells) if cells else 0)
        return [cells.get(col) for col in range(1, width + 1)]

    def iter_rows(self, width: int | None = None):
        for number in sorted(self.rows):
            yield number, self.row_values(number, width)

    def cell(self, row_number: int, col_number: int):
        return self.rows.get(row_number, {}).get(col_number)


@dataclass
class Workbook:
    sheets: list[Sheet]
    date1904: bool = False
    defined_names: dict[str, str] = field(default_factory=dict)

    def sheet(self, name: str) -> Sheet | None:
        wanted = name.strip().casefold()
        for sheet in self.sheets:
            if sheet.name.strip().casefold() == wanted:
                return sheet
        return None


def column_letter(index: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA."""
    if index < 1:
        raise ValueError("Column index starts at 1.")
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def column_index(letters: str) -> int:
    value = 0
    for char in letters.upper():
        value = value * 26 + (ord(char) - 64)
    return value


def split_ref(ref: str) -> tuple[int, int]:
    match = _CELL_REF.match(ref.upper())
    if not match:
        raise XlsxError(f"Bad cell reference {ref!r}.")
    return int(match.group(2)), column_index(match.group(1))


def serial_to_date(serial: float, date1904: bool = False):
    """Convert an Excel serial to a date, or return a CellError when unsafe."""
    if date1904:
        if serial < 0:
            return CellError(f"Excel date serial {serial:g} is negative.")
        return date(1904, 1, 1) + timedelta(days=int(serial))
    if serial <= 60:
        return CellError(
            f"Excel date serial {serial:g} falls before 1900-03-01, where Excel's calendar is ambiguous."
        )
    return date(1899, 12, 30) + timedelta(days=int(serial))


def _tag(local: str) -> str:
    return f"{{{NS_MAIN}}}{local}"


def _text_of(element) -> str:
    """Concatenate the <t> runs of a string item, skipping phonetic runs."""
    parts = []
    for child in element:
        if child.tag == _tag("t"):
            parts.append(child.text or "")
        elif child.tag == _tag("r"):
            for run_child in child:
                if run_child.tag == _tag("t"):
                    parts.append(run_child.text or "")
    return "".join(parts)


def _format_is_date(code: str) -> bool:
    stripped = re.sub(r'"[^"]*"', "", code)          # literal text
    stripped = re.sub(r"\[[^\]]*\]", "", stripped)   # [Red], [$-409], [h]
    stripped = re.sub(r"\\.", "", stripped)          # escaped characters
    if stripped.strip().casefold() == "general":
        return False
    if re.search(r"[0#?]", stripped):
        return False
    return bool(re.search(r"[ymdhs]", stripped, re.IGNORECASE))


def _resolve_target(target: str) -> str:
    if target.startswith("/"):
        return posixpath.normpath(target.lstrip("/"))
    return posixpath.normpath(posixpath.join("xl", target))


def read_workbook(data: bytes) -> Workbook:
    if not data.startswith(b"PK\x03\x04"):
        raise XlsxError("This is not an .xlsx workbook (expected a zip container).")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise XlsxError("This is not an .xlsx workbook (corrupt zip container).") from exc
    with archive:
        members = archive.infolist()
        if len(members) > MAX_ZIP_MEMBERS:
            raise XlsxError("Workbook refused: it contains too many parts.")
        for member in members:
            if member.file_size > MAX_MEMBER_BYTES:
                raise XlsxError("Workbook refused: a part declares more than 50 MB.")
        names = set(archive.namelist())
        if "xl/workbook.xml" not in names:
            raise XlsxError("This is not an .xlsx workbook (xl/workbook.xml is missing).")
        if any(name.startswith("xl/vbaProject") for name in names):
            raise XlsxError("Macro-enabled workbooks are refused. Save as .xlsx or .csv and try again.")
        return _read(archive, names)


def _read(archive: zipfile.ZipFile, names: set[str]) -> Workbook:
    def parse(name: str):
        try:
            return ET.fromstring(archive.read(name))
        except ET.ParseError as exc:
            raise XlsxError(f"Workbook part {name} is not well-formed XML.") from exc

    workbook_xml = parse("xl/workbook.xml")
    rels = {}
    if "xl/_rels/workbook.xml.rels" in names:
        for rel in parse("xl/_rels/workbook.xml.rels"):
            rels[rel.get("Id")] = (rel.get("Type", ""), _resolve_target(rel.get("Target", "")))

    workbook_pr = workbook_xml.find(_tag("workbookPr"))
    date1904 = bool(workbook_pr is not None and workbook_pr.get("date1904", "0") in ("1", "true"))

    defined_names = {}
    defined = workbook_xml.find(_tag("definedNames"))
    if defined is not None:
        for item in defined:
            if item.get("name"):
                defined_names[item.get("name")] = (item.text or "").strip()

    shared_strings = _shared_strings(parse, rels, names)
    date_styles = _date_styles(parse, names)

    sheets: list[Sheet] = []
    sheets_element = workbook_xml.find(_tag("sheets"))
    if sheets_element is None:
        raise XlsxError("The workbook lists no sheets.")
    for index, sheet_element in enumerate(sheets_element):
        rel_id = sheet_element.get(f"{{{NS_REL}}}id")
        target = rels.get(rel_id, ("", ""))[1] if rel_id else ""
        if not target:
            target = f"xl/worksheets/sheet{index + 1}.xml"
        if target not in names:
            raise XlsxError(f"Sheet part {target} is missing from the workbook.")
        sheet = Sheet(
            name=sheet_element.get("name", f"Sheet{index + 1}"),
            index=index,
            hidden=sheet_element.get("state", "visible") in ("hidden", "veryHidden"),
        )
        _read_sheet(parse(target), sheet, shared_strings, date_styles, date1904)
        sheets.append(sheet)
    return Workbook(sheets=sheets, date1904=date1904, defined_names=defined_names)


def _shared_strings(parse, rels, names) -> list[str]:
    target = None
    for rel_type, rel_target in rels.values():
        if rel_type.endswith("/sharedStrings"):
            target = rel_target
    if target is None and "xl/sharedStrings.xml" in names:
        target = "xl/sharedStrings.xml"
    if target is None or target not in names:
        return []
    return [_text_of(item) for item in parse(target) if item.tag == _tag("si")]


def _date_styles(parse, names) -> set[int]:
    """Indices into cellXfs whose number format renders a date."""
    if "xl/styles.xml" not in names:
        return set()
    styles = parse("xl/styles.xml")
    custom_dates = set()
    num_fmts = styles.find(_tag("numFmts"))
    if num_fmts is not None:
        for fmt in num_fmts:
            try:
                fmt_id = int(fmt.get("numFmtId", "-1"))
            except ValueError:
                continue
            if _format_is_date(fmt.get("formatCode", "")):
                custom_dates.add(fmt_id)
    result = set()
    cell_xfs = styles.find(_tag("cellXfs"))
    if cell_xfs is None:
        return result
    for index, xf in enumerate(cell_xfs):
        try:
            fmt_id = int(xf.get("numFmtId", "0"))
        except ValueError:
            continue
        if fmt_id in BUILTIN_DATE_FORMATS or fmt_id in custom_dates:
            result.add(index)
    return result


def _read_sheet(root, sheet: Sheet, shared_strings: list[str], date_styles: set[int], date1904: bool) -> None:
    sheet_data = root.find(_tag("sheetData"))
    if sheet_data is None:
        return
    next_row = 0
    for row in sheet_data:
        if row.tag != _tag("row"):
            continue
        try:
            row_number = int(row.get("r", "0")) or next_row + 1
        except ValueError:
            row_number = next_row + 1
        next_row = row_number
        next_col = 0
        cells: dict[int, object] = {}
        for cell in row:
            if cell.tag != _tag("c"):
                continue
            ref = cell.get("r")
            if ref:
                _, col_number = split_ref(ref)
            else:
                col_number = next_col + 1
            next_col = col_number
            value = _cell_value(cell, shared_strings, date_styles, date1904)
            if value is not None:
                cells[col_number] = value
        if cells:
            sheet.rows[row_number] = cells


def _cell_value(cell, shared_strings: list[str], date_styles: set[int], date1904: bool):
    cell_type = cell.get("t", "n")
    value_element = cell.find(_tag("v"))
    raw = value_element.text if value_element is not None else None
    if cell_type == "inlineStr":
        inline = cell.find(_tag("is"))
        text = _text_of(inline) if inline is not None else ""
        return text if text != "" else None
    if raw is None:
        return None
    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return CellError("Shared string index out of range.")
    if cell_type == "str":
        return raw
    if cell_type == "b":
        return raw.strip() in ("1", "true", "TRUE")
    if cell_type == "e":
        return CellError(f"Excel error value {raw}.")
    # numeric (t="n" or absent)
    try:
        number = float(raw)
    except ValueError:
        return raw
    try:
        style = int(cell.get("s", "0"))
    except ValueError:
        style = 0
    if style in date_styles:
        return serial_to_date(number, date1904)
    if number.is_integer() and abs(number) < 1e15:
        return int(number)
    return number
