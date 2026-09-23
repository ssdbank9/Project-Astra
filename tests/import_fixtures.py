"""Helpers shared by the import tests: build small .xlsx files with zipfile only.

Nothing binary is committed; every workbook is generated inside the test run.
"""
from __future__ import annotations

import io
import zipfile
from datetime import date
from xml.sax.saxutils import escape

from astra.importer import EXCEL_EPOCH, MARKER_NAME, MARKER_SHEET, PROJECT_FIELDS, TEMPLATE_SHEET, TemplateConfig
from astra.xlsx_reader import column_letter

NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'


class Styled:
    """A numeric cell written with an explicit cellXfs index (e.g. PERCENT_STYLE)."""

    def __init__(self, value, style):
        self.value, self.style = value, style


PERCENT_STYLE = 2   # cellXfs index 2 in STYLES below: built-in numFmtId 9 = "0%"


class ErrorValue:
    """An Excel error cell (t="e"), for example ErrorValue("#N/A")."""

    def __init__(self, code):
        self.code = code


def _cell(ref, value, *, date_style=1):
    if value is None or value == "":
        return ""
    if isinstance(value, Styled):
        return f'<c r="{ref}" s="{value.style}"><v>{value.value}</v></c>'
    if isinstance(value, ErrorValue):
        return f'<c r="{ref}" t="e"><v>{escape(value.code)}</v></c>'
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, date):
        return f'<c r="{ref}" s="{date_style}"><v>{(value - EXCEL_EPOCH).days}</v></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>'


def sheet_xml(rows, *, dimension=True, first_row=1):
    body = []
    for offset, row in enumerate(rows):
        number = first_row + offset
        cells = "".join(_cell(f"{column_letter(index)}{number}", value) for index, value in enumerate(row, start=1))
        body.append(f'<row r="{number}">{cells}</row>')
    last = column_letter(max((len(r) for r in rows), default=1))
    dim = f'<dimension ref="A{first_row}:{last}{first_row + len(rows) - 1}"/>' if dimension and rows else ""
    return f"{DECL}<worksheet {NS}>{dim}<sheetData>{''.join(body)}</sheetData></worksheet>"


STYLES = (
    f'{DECL}<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<numFmts count="1"><numFmt numFmtId="164" formatCode="dd-mm-yyyy"/></numFmts>'
    '<fonts count="1"><font><sz val="11"/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
    '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0"/></cellStyleXfs>'
    '<cellXfs count="3"><xf numFmtId="0"/><xf numFmtId="164" applyNumberFormat="1"/><xf numFmtId="9" applyNumberFormat="1"/></cellXfs>'
    '</styleSheet>'
)


# Every part carries this timestamp so identical input gives identical bytes (and sha256).
# writestr() with a bare name stamps the wall clock instead; 1980-01-01 is the earliest DOS date.
FIXED_ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)


class _DeterministicZip(zipfile.ZipFile):
    def writestr(self, name, data, *args, **kwargs):
        if isinstance(name, str):
            name = zipfile.ZipInfo(name, date_time=FIXED_ZIP_DATE_TIME)
            name.compress_type = zipfile.ZIP_DEFLATED   # a ZipInfo does not inherit the archive's default
        super().writestr(name, data, *args, **kwargs)


def workbook_bytes(sheets, *, date1904=False, shared_strings=None, absolute_targets=False, hidden=(),
                   defined_names=None, styles=STYLES):
    """sheets: list of (name, sheet_xml). Returns .xlsx bytes, byte-identical for identical input."""
    buffer = io.BytesIO()
    with _DeterministicZip(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        overrides = "".join(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(1, len(sheets) + 1)
        )
        archive.writestr("[Content_Types].xml", (
            f'{DECL}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            + overrides + '</Types>'
        ))
        archive.writestr("_rels/.rels", (
            f'{DECL}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        ))
        sheet_tags = ""
        for i, (name, _) in enumerate(sheets, start=1):
            state = ' state="hidden"' if name in hidden else ""
            sheet_tags += f'<sheet name="{escape(name)}" sheetId="{i}"{state} r:id="rId{i}"/>'

        names = "".join(f'<definedName name="{k}">{escape(v)}</definedName>' for k, v in (defined_names or {}).items())
        pr = '<workbookPr date1904="1"/>' if date1904 else "<workbookPr/>"
        archive.writestr("xl/workbook.xml", (
            f'{DECL}<workbook {NS}>{pr}<sheets>{sheet_tags}</sheets>'
            + (f"<definedNames>{names}</definedNames>" if names else "") + '</workbook>'
        ))
        prefix = "/xl/worksheets/" if absolute_targets else "worksheets/"
        rels = "".join(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="{prefix}sheet{i}.xml"/>'
            for i in range(1, len(sheets) + 1)
        )
        rels += f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        if shared_strings is not None:
            rels += f'<Relationship Id="rId{len(sheets) + 2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
            archive.writestr("xl/sharedStrings.xml", shared_strings)
        archive.writestr("xl/_rels/workbook.xml.rels", (
            f'{DECL}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>'
        ))
        archive.writestr("xl/styles.xml", styles)
        for i, (_, xml) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{i}.xml", xml)
    return buffer.getvalue()


def forge_declared_size(data: bytes, name: str, size: int) -> bytes:
    """Return the zip with member ``name``'s uncompressed size in the central directory set to ``size``.

    The reader trusts the central directory for its inflation caps, so this is how a
    hostile workbook would lie about its size (offset 24 of the CD header is the
    uncompressed size; the file name follows the 46-byte fixed part).
    """
    out = bytearray(data)
    wanted = name.encode("utf-8")
    start = 0
    while True:
        index = out.find(b"PK\x01\x02", start)
        if index < 0:
            raise AssertionError(f"{name} not found in the central directory")
        name_length = int.from_bytes(out[index + 28:index + 30], "little")
        if bytes(out[index + 46:index + 46 + name_length]) == wanted:
            out[index + 24:index + 28] = size.to_bytes(4, "little")
            return bytes(out)
        start = index + 4


def filled_template(rows, config=None, *, marker=None, headers=None, project=None, people=None):
    """A workbook shaped like the Astra template: Tasks sheet with the configured
    header row plus ``rows`` (dicts keyed by column key), the hidden marker sheet
    and, when given, a Project sheet (``{label: value}``) and a People sheet
    (tuples of Email, Full Name, Role, Notes).

    Dates given as ``datetime.date`` become real Excel date cells; strings are kept
    as typed so prose dates can be exercised.
    """
    # Tests exercise every column, so the fixture defaults to the Full preset (the
    # service tests switch the Owner's configuration to Full in setUp).
    config = config or TemplateConfig.preset("full")
    labels = list(headers) if headers is not None else list(config.labels())
    keys = [column.key for column in config.active]
    matrix = [labels]
    for row in rows:
        matrix.append([row.get(key, "") for key in keys])
    tasks = sheet_xml(matrix)
    marker_value = marker if marker is not None else config.hash()
    marker_sheet = sheet_xml([[MARKER_NAME, marker_value]])
    sheets = [("README", sheet_xml([["notes"]]))]
    if project is not None:
        project_rows = [["Field", "Value (fill in)", "Guidance"]]
        for label, _, required, _, _ in PROJECT_FIELDS:
            project_rows.append([label + (" *" if required else ""), project.get(label, ""), ""])
        sheets.append(("Project", sheet_xml(project_rows)))
    sheets.append((TEMPLATE_SHEET, tasks))
    sheets.append(("Example", sheet_xml([labels, ["EX-001", "Example task"] + [""] * (len(labels) - 2)])))
    if people is not None:
        sheets.append(("People", sheet_xml([["Email", "Full Name", "Role on project", "Notes"], *[list(row) for row in people]])))
    sheets.append((MARKER_SHEET, marker_sheet))
    return workbook_bytes(sheets, hidden=(MARKER_SHEET,), defined_names={MARKER_NAME: f"{MARKER_SHEET}!$B$1"})
