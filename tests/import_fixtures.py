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


def _cell(ref, value, *, date_style=1):
    if value is None or value == "":
        return ""
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
    '<cellXfs count="3"><xf numFmtId="0"/><xf numFmtId="164" applyNumberFormat="1"/><xf numFmtId="0"/></cellXfs>'
    '</styleSheet>'
)


def workbook_bytes(sheets, *, date1904=False, shared_strings=None, absolute_targets=False, hidden=(),
                   defined_names=None, styles=STYLES):
    """sheets: list of (name, sheet_xml). Returns .xlsx bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
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
