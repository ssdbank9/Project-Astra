import unittest
from datetime import date

from astra.xlsx_reader import CellError, XlsxError, column_letter, read_workbook, serial_to_date

from import_fixtures import DECL, NS, sheet_xml, workbook_bytes


class XlsxReaderTests(unittest.TestCase):
    def test_column_letters_round_trip(self):
        self.assertEqual(column_letter(1), "A")
        self.assertEqual(column_letter(26), "Z")
        self.assertEqual(column_letter(27), "AA")
        self.assertEqual(column_letter(52), "AZ")

    def test_inline_strings_numbers_booleans_and_missing_dimension(self):
        xml = (
            f'{DECL}<worksheet {NS}><sheetData>'
            '<row r="3"><c r="A3" t="inlineStr"><is><t>Title</t></is></c><c r="B3" t="str"><v>formula text</v></c>'
            '<c r="C3"><v>42</v></c><c r="D3" t="b"><v>1</v></c><c r="E3" t="s"></c><c r="F3"><v>2.5</v></c></row>'
            '</sheetData></worksheet>'
        )
        workbook = read_workbook(workbook_bytes([("Data", xml)]))
        sheet = workbook.sheets[0]
        self.assertEqual(sheet.max_row, 3)
        self.assertEqual(sheet.row_values(3), ["Title", "formula text", 42, True, None, 2.5])

    def test_shared_strings_with_rich_text_runs(self):
        shared = (
            f'{DECL}<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="2" uniqueCount="2">'
            '<si><t>plain</t></si><si><r><t>rich </t></r><r><rPr><b/></rPr><t>text</t></r></si></sst>'
        )
        xml = (
            f'{DECL}<worksheet {NS}><dimension ref="A1:B1"/><sheetData>'
            '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row></sheetData></worksheet>'
        )
        workbook = read_workbook(workbook_bytes([("Data", xml)], shared_strings=shared))
        self.assertEqual(workbook.sheets[0].row_values(1), ["plain", "rich text"])

    def test_date_styled_serials_in_1900_and_1904_systems(self):
        xml = sheet_xml([[date(2026, 9, 7), 46272]])  # A1 styled date, B1 plain number
        workbook = read_workbook(workbook_bytes([("Data", xml)]))
        self.assertEqual(workbook.sheets[0].row_values(1), [date(2026, 9, 7), 46272])
        xml_1904 = f'{DECL}<worksheet {NS}><sheetData><row r="1"><c r="A1" s="1"><v>44807</v></c></row></sheetData></worksheet>'
        workbook = read_workbook(workbook_bytes([("Data", xml_1904)], date1904=True))
        self.assertTrue(workbook.date1904)
        self.assertEqual(workbook.sheets[0].cell(1, 1), date(1904, 1, 1).fromordinal(date(1904, 1, 1).toordinal() + 44807))

    def test_serial_at_or_below_60_is_rejected_as_ambiguous(self):
        self.assertIsInstance(serial_to_date(60), CellError)
        self.assertIsInstance(serial_to_date(1), CellError)
        self.assertEqual(serial_to_date(61), date(1900, 3, 1))
        xml = f'{DECL}<worksheet {NS}><sheetData><row r="1"><c r="A1" s="1"><v>45</v></c></row></sheetData></worksheet>'
        workbook = read_workbook(workbook_bytes([("Data", xml)]))
        self.assertIsInstance(workbook.sheets[0].cell(1, 1), CellError)

    def test_absolute_relationship_targets_hidden_sheets_and_defined_names(self):
        first = sheet_xml([["a"]])
        second = sheet_xml([["marker", "abc123"]])
        data = workbook_bytes(
            [("Tasks", first), ("_astra", second)], absolute_targets=True, hidden=("_astra",),
            defined_names={"AstraTemplateVersion": "_astra!$B$1"},
        )
        workbook = read_workbook(data)
        self.assertEqual([s.name for s in workbook.sheets], ["Tasks", "_astra"])
        self.assertTrue(workbook.sheets[1].hidden)
        self.assertFalse(workbook.sheets[0].hidden)
        self.assertEqual(workbook.defined_names["AstraTemplateVersion"], "_astra!$B$1")
        self.assertEqual(workbook.sheet("_ASTRA").cell(1, 2), "abc123")

    def test_non_zip_and_macro_workbooks_are_refused(self):
        with self.assertRaises(XlsxError):
            read_workbook(b"Import Key,Title\nA,B\n")
        import io
        import zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("xl/workbook.xml", "<workbook/>")
            archive.writestr("xl/vbaProject.bin", b"macro")
        with self.assertRaisesRegex(XlsxError, "Macro-enabled"):
            read_workbook(buffer.getvalue())

    def test_oversized_member_declaration_is_refused(self):
        import io
        import zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            info = zipfile.ZipInfo("xl/workbook.xml")
            archive.writestr(info, "<workbook/>")
        data = bytearray(buffer.getvalue())
        # Forge the declared uncompressed size in the central directory (offset 24 of the CD header).
        cd_start = data.rfind(b"PK\x01\x02")
        data[cd_start + 24:cd_start + 28] = (60 * 1024 * 1024).to_bytes(4, "little")
        with self.assertRaisesRegex(XlsxError, "50 MB"):
            read_workbook(bytes(data))
