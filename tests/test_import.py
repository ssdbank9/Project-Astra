import http.client
import inspect
import json
import os
import re
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import quote

from astra import importer
from astra.db import connect
from astra.service import AstraService, Forbidden
from astra.web import AstraHandler, AstraServer
from astra.xlsx_reader import Percent, read_workbook

from import_fixtures import ErrorValue, PERCENT_STYLE, Styled, filled_template, forge_declared_size, sheet_xml, workbook_bytes


class ImportServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / "test.sqlite3")
        self.service = AstraService(self.db)
        self.owner = self.service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")
        self.jamal = self.service.create_user(self.owner, "jamal@example.org", "Jamal", "jamal password safe", "member")
        self.waseem = self.service.create_user(self.owner, "waseem@example.org", "Waseem", "waseem password safe", "member")
        self.viewer = self.service.create_user(self.owner, "viewer@example.org", "Viewer", "viewer password safe", "member")
        self.chair = self.service.create_user(self.owner, "chair@example.org", "Chair", "chair password safe", "chairman")
        self.project = self.service.create_project(self.owner, "Rupani Academy")
        self.other = self.service.create_project(self.owner, "Other project")
        self.service.grant_project_access(self.owner, self.project["id"], self.jamal["id"], "manager")
        self.service.grant_project_access(self.owner, self.project["id"], self.waseem["id"], "manager")
        self.service.grant_project_access(self.owner, self.project["id"], self.viewer["id"], "viewer")
        # Most tests exercise every column: switch the Owner's template to the Full preset.
        self.service.set_import_template_config(self.owner, {"preset": "full"})

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    # -- helpers --------------------------------------------------------
    def rows(self):
        return [
            {"import_key": "RA-001", "title": "Submit CP application", "owner_email": "jamal@example.org",
             "start_date": date(2026, 9, 1), "due_date": "07-09-2026", "status": "Not Started",
             "next_action": "Confirm vendor", "notes": "Due as written: Immediate"},
            {"import_key": "RA-002", "title": "Awareness sessions", "owner_email": "waseem@example.org",
             "start_date": "2026-09-07", "due_date": date(2026, 9, 10), "status": "In Progress", "predecessors": "RA-001",
             "criticality": "High"},
            {"import_key": "RA-003", "title": "Prepare handouts", "parent_key": "RA-002", "x_type": "Milestone",
             "due_date": "09-09-2026", "x_risk_dependency": "Printer capacity"},
        ]

    def enable_all_columns(self):
        """Owner switches every built-in column on (Entity, Attachment Links, Project, Milestone...)."""
        config = self.service.get_import_template_config(self.owner)
        for item in config["columns"]:
            item["enabled"] = True
        self.service.set_import_template_config(self.owner, {"columns": config["columns"]})
        return self.service._import_config()

    def preview(self, actor, rows, project_id=None, **options):
        data = filled_template(rows)
        return data, self.service.import_preview(actor, project_id or self.project["id"], "demo.xlsx", data, options)

    def commit(self, actor, rows, project_id=None, sha=None, **options):
        data = filled_template(rows)
        return self.service.import_commit(actor, project_id or self.project["id"], "demo.xlsx", data, options, sha)

    def task_by_key(self, key):
        return next(t for t in self.service.list_tasks(self.owner, self.project["id"]) if t["import_key"] == key)

    def codes(self, row):
        return [f["code"] for f in row["findings"]]

    # -- template -------------------------------------------------------
    def test_template_workbook_is_locked_validated_and_marked(self):
        payload, filename, content_type = self.service.import_template(self.owner, "xlsx")
        self.assertEqual(filename, "astra-import-template.xlsx")
        self.assertIn("spreadsheetml", content_type)
        workbook = read_workbook(payload)
        self.assertEqual([s.name for s in workbook.sheets],
                         ["README", "Project", "Tasks", "Example", "People", "Lists", "_astra"])
        self.assertEqual([s.hidden for s in workbook.sheets], [False, False, False, False, False, True, True])
        config = self.service._import_config()
        self.assertEqual(config.hash(), "53133bf237fe9b3c")  # the v2 column set
        self.assertEqual(len(config.active), 18)
        self.assertEqual(workbook.sheet("Tasks").row_values(1), list(config.labels()))
        self.assertEqual(workbook.sheet("Tasks").max_row, 1)  # no example row on Tasks
        self.assertEqual(workbook.sheet("Example").row_values(1), list(config.labels()))
        self.assertEqual(workbook.sheet("Example").cell(2, 1), "EX-001")
        self.assertEqual(workbook.sheet("Example").max_row, 4)
        self.assertEqual(workbook.sheet("_astra").cell(1, 2), config.hash())
        self.assertEqual(workbook.sheet("_astra").cell(2, 2), config.fingerprint())
        self.assertEqual(workbook.sheet("_astra").cell(3, 2), importer.TEMPLATE_FAMILY)
        self.assertEqual(workbook.defined_names["AstraTemplateVersion"], "_astra!$B$1")
        self.assertEqual(workbook.defined_names["Lists_Status"], "Lists!$A$2:$A$12")
        self.assertEqual(workbook.sheet("Project").cell(2, 1), "Project Name *")
        self.assertEqual(workbook.sheet("People").row_values(1)[:3], ["Email", "Full Name", "Role on project"])
        import zipfile
        import io
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            tasks_xml = archive.read("xl/worksheets/sheet3.xml").decode()
            readme_xml = archive.read("xl/worksheets/sheet1.xml").decode()
            project_xml = archive.read("xl/worksheets/sheet2.xml").decode()
            styles_xml = archive.read("xl/styles.xml").decode()
            workbook_xml = archive.read("xl/workbook.xml").decode()
        self.assertIn('state="veryHidden"', workbook_xml)
        self.assertIn('<autoFilter ref="A1:R2001"/>', tasks_xml)
        self.assertIn('autoFilter="0"', tasks_xml)
        self.assertIn('<sheetProtection', project_xml)
        self.assertIn('<c r="B2" s="4"/>', project_xml)  # Value column unlocked
        self.assertIn('<sheetProtection algorithmName="SHA-512"', tasks_xml)
        self.assertIn('insertColumns="1"', tasks_xml)
        self.assertIn('deleteColumns="1"', tasks_xml)
        self.assertIn('sort="1"', tasks_xml)
        self.assertIn('formatColumns="0"', tasks_xml)
        self.assertIn('insertRows="0"', tasks_xml)
        self.assertIn('state="frozen"', tasks_xml)
        self.assertIn('<sheetProtection', readme_xml)
        self.assertIn('formatCode="dd-mm-yyyy"', styles_xml)
        self.assertIn('<protection locked="0"/>', styles_xml)
        # dropdowns from named ranges, date validation on Start / Original, Due >= Start rule, key uniqueness rule
        labels = list(config.labels())
        status_col = importer.column_letter(labels.index("Status") + 1)
        self.assertIn(f'sqref="{status_col}2:{status_col}2001"><formula1>Lists_Status</formula1>', tasks_xml)
        self.assertIn("<formula1>Lists_Criticality</formula1>", tasks_xml)
        self.assertIn("<formula1>Lists_x_type</formula1>", tasks_xml)
        self.assertEqual(tasks_xml.count('type="date" operator="between"'), 2)
        self.assertIn(f"<formula1>{importer.excel_serial(importer.DATE_MIN)}</formula1>", tasks_xml)
        self.assertIn("COUNTIF($A$2:$A$2001,A2)=1", tasks_xml)
        due_col = importer.column_letter(labels.index("Due Date") + 1)
        start_col = importer.column_letter(labels.index("Start Date") + 1)
        self.assertIn(f'OR({start_col}2="",{due_col}2&gt;={start_col}2)', tasks_xml)  # >= is XML-escaped
        self.assertIn('ISNUMBER(FIND("@",', tasks_xml)
        self.assertEqual(tasks_xml.count("<conditionalFormatting"), 4)
        csv_payload, csv_name, _ = self.service.import_template(self.owner, "csv")
        self.assertEqual(csv_name, "astra-import-template.csv")
        self.assertEqual(csv_payload.decode("utf-8-sig").splitlines(), [",".join(f'"{l}"' if "," in l else l for l in labels)])

    def test_simple_preset_is_the_default_and_full_is_one_call_away(self):
        self.service.set_import_template_config(self.owner, {"reset": True})
        config = self.service.get_import_template_config(self.owner)
        self.assertEqual(config["hash"], "52cd3da7813769c1")  # template-config-simple.json
        self.assertEqual(config["labels"], ["Import Key", "Title", "Step of (Key)", "Owner Email", "Start Date", "Due Date",
                                            "Status", "Criticality", "Notes"])
        self.assertFalse(config["extended"])
        self.assertEqual(len(config["presets"]["simple"]), 9)
        self.assertEqual(len(config["presets"]["full"]), 18)
        self.assertEqual(len(config["columns"]), 25)  # everything stays defined, just off
        payload, _, _ = self.service.import_template(self.owner, "xlsx")
        workbook = read_workbook(payload)
        self.assertEqual([s.name for s in workbook.sheets], ["README", "Project", "Tasks", "Example", "Lists", "_astra"])
        self.assertEqual(workbook.sheet("_astra").cell(1, 2), "52cd3da7813769c1")
        self.assertEqual(workbook.sheet("_astra").cell(3, 2), importer.SIMPLE_FAMILY)
        self.assertEqual(workbook.sheet("Project").max_row, 4)   # name, manager email, timezone
        self.assertEqual(workbook.sheet("Example").max_row, 3)   # a task and a step
        self.assertLessEqual(workbook.sheet("README").max_row, 10)
        import io
        import zipfile
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            tasks_xml = archive.read("xl/worksheets/sheet3.xml").decode()
        self.assertIn('<c r="A2" s="8" t="str"><f>IF(B2="","","T-"&amp;TEXT(ROW()-1,"000"))</f></c>', tasks_xml)
        self.assertIn('<c r="A2001" s="8" t="str"><f>IF(B2001=', tasks_xml)
        # the blank template (formula cells without cached values) has nothing to import
        preview = self.service.import_preview(self.owner, self.project["id"], "template.xlsx", payload)
        self.assertEqual(preview["summary"]["rows"], 0)
        # a row carrying only a (pre-filled) key is ignored; a filled row imports with the simple columns
        simple = self.service._import_config()
        rows = [{"import_key": "T-001"}, {"import_key": "T-002", "title": "Only nine columns", "parent_key": "",
                 "owner_email": "jamal@example.org", "due_date": "07-09-2026", "status": "Not started", "notes": "Fine"}]
        preview = self.service.import_preview(self.owner, self.project["id"], "simple.xlsx", filled_template(rows, simple))
        self.assertEqual(preview["summary"]["rows"], 1)
        self.assertEqual(preview["rows"][0]["import_key"], "T-002")
        self.assertEqual(preview["rows"][0]["level"], "ok")
        full = self.service.set_import_template_config(self.owner, {"preset": "full"})
        self.assertEqual(full["hash"], "53133bf237fe9b3c")
        self.assertTrue(full["extended"])
        self.assertIn("People", [s.name for s in read_workbook(self.service.import_template(self.owner, "xlsx")[0]).sheets])
        with self.assertRaisesRegex(ValueError, "Unknown preset"):
            self.service.set_import_template_config(self.owner, {"preset": "huge"})

    def test_template_download_round_trips_through_the_parser_and_example_keys_are_refused(self):
        payload, _, _ = self.service.import_template(self.owner, "xlsx")
        preview = self.service.import_preview(self.owner, self.project["id"], "template.xlsx", payload)
        self.assertEqual(preview["summary"]["rows"], 0)  # the Example sheet is never read
        self.assertEqual(preview["people"], [])
        rows = [{"import_key": "EX-001", "title": "Copied from Example"}, {"import_key": "example-7", "title": "Also example"},
                {"import_key": "EXTRA-1", "title": "A real key that merely starts with EX"}]
        _, preview = self.preview(self.owner, rows)
        self.assertIn("E_EXAMPLE_ROW", self.codes(preview["rows"][0]))
        self.assertIn("E_EXAMPLE_ROW", self.codes(preview["rows"][1]))
        self.assertEqual(preview["rows"][2]["level"], "ok")

    def test_filled_template_built_by_astra_round_trips(self):
        # build_template_xlsx can pre-fill Tasks, Project and People: the result must parse like an upload.
        rows = [{"import_key": "P-1", "title": "Pre-filled", "x_type": "Milestone", "due_date": date(2026, 10, 1)}]
        payload = importer.build_template_xlsx(
            self.service._import_config(), tasks=rows,
            project={"name": "Rupani Academy", "timezone": "Asia/Karachi"},
            people=[("jamal@example.org", "Jamal", "Manager", "")],
        )
        preview = self.service.import_preview(self.owner, self.project["id"], "prefilled.xlsx", payload)
        self.assertEqual(preview["summary"]["create"], 1)
        self.assertTrue(preview["rows"][0]["values"]["milestone"])
        self.assertEqual(preview["project_header"]["name"], "Rupani Academy")
        self.assertEqual(preview["people"][0]["status"], "ok")

    # -- parsing and validation ----------------------------------------
    def test_preview_reports_rows_and_writes_nothing(self):
        before = self.db.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"]
        data, preview = self.preview(self.owner, self.rows())
        self.assertEqual(before, self.db.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"])
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM imports").fetchone()["c"], 0)
        summary = preview["summary"]
        self.assertEqual((summary["create"], summary["update"], summary["errors"]), (3, 0, 0))
        self.assertTrue(preview["can_commit"])
        first = preview["rows"][0]
        self.assertEqual(first["values"]["start_date"], "01-09-2026")
        self.assertEqual(first["values"]["due_date"], "07-09-2026")
        self.assertEqual(first["values"]["status"], "assigned")
        self.assertEqual(preview["rows"][1]["values"]["start_date"], "07-09-2026")
        self.assertEqual(preview["rows"][2]["values"]["start_date"], "09-09-2026")  # milestone: start = due
        self.assertEqual(preview["sha256"], importer.sha256_hex(data))

    def test_prose_dates_are_errors_never_guessed(self):
        rows = self.rows()
        rows[0]["due_date"] = "Sept. 7–10"
        rows[1]["start_date"] = "TBD"
        rows[2]["due_date"] = "Immediate"
        _, preview = self.preview(self.owner, rows)
        self.assertEqual(preview["summary"]["errors"], 3)
        for row in preview["rows"]:
            self.assertIn("E_DATE_INVALID", self.codes(row))
            self.assertEqual(row["action"], "error")
        self.assertFalse(preview["can_commit"])
        with self.assertRaisesRegex(ValueError, "errors"):
            self.commit(self.owner, rows)

    def test_header_mismatch_and_stale_marker_are_rejected(self):
        config = self.service._import_config()
        headers = list(config.labels())
        headers[1], headers[2] = headers[2], headers[1]
        with self.assertRaisesRegex(ValueError, "B: expected 'Title', found 'Type'"):
            self.service.import_preview(self.owner, self.project["id"], "x.xlsx", filled_template(self.rows(), headers=headers))
        with self.assertRaisesRegex(ValueError, "template has changed"):
            self.service.import_preview(self.owner, self.project["id"], "x.xlsx", filled_template(self.rows(), marker="stale"))
        with self.assertRaisesRegex(ValueError, "version marker is missing"):
            from import_fixtures import sheet_xml, workbook_bytes
            plain = workbook_bytes([("Tasks", sheet_xml([headers, ["A", "", "", "", "Title"]]))])
            self.service.import_preview(self.owner, self.project["id"], "x.xlsx", plain)
        with self.assertRaisesRegex(ValueError, "not supported"):
            self.service.import_preview(self.owner, self.project["id"], "x.xlsm", filled_template(self.rows()))

    def test_csv_path_accepts_aliases_with_a_warning_and_bom(self):
        csv_text = (
            "﻿Task ID,Task Name,Assignee,Start,Finish,Status,Depends On\n"
            "RA-001,First task,jamal@example.org,01-09-2026,2026-09-07,Done,\n"
            "RA-002,Second task,,,,Not Started,RA-001\n"
        )
        preview = self.service.import_preview(self.owner, self.project["id"], "tasks.csv", csv_text.encode("utf-8"))
        self.assertEqual(preview["format"], "csv")
        self.assertEqual(preview["summary"]["create"], 2)
        self.assertIn("W_HEADER_ALIAS", self.codes(preview["rows"][0]))
        self.assertEqual(preview["rows"][0]["values"]["due_date"], "07-09-2026")
        self.assertEqual(preview["rows"][0]["values"]["status"], "completed")
        self.assertIn("W_STATUS_NO_RECORD", self.codes(preview["rows"][0]))
        self.assertEqual(preview["rows"][1]["values"]["predecessors"], ["RA-001"])
        latin = "Import Key;Title\nRA-009;Caf\xe9 plan\n".encode("cp1252")
        preview = self.service.import_preview(self.owner, self.project["id"], "tasks.csv", latin)
        self.assertEqual(preview["rows"][0]["values"]["title"], "Café plan")
        self.assertTrue(any("Windows-1252" in w for w in preview["file_warnings"]))

    def test_vocabulary_people_and_structural_findings(self):
        rows = self.rows()
        rows[0]["status"] = "Sort of done"
        rows[0]["criticality"] = "Enormous"
        rows[0]["owner_email"] = "nobody@example.org"
        rows[1]["owner_email"] = "Waseem"          # by name, unique
        rows[1]["progress"] = "45%"
        rows[2]["import_key"] = "RA-001"           # duplicate key
        rows.append({"import_key": "RA-004", "title": "Cycle A", "parent_key": "RA-005"})
        rows.append({"import_key": "RA-005", "title": "Cycle B", "parent_key": "RA-004"})
        rows.append({"import_key": "RA-006", "title": "Bad parent", "parent_key": "NOPE"})
        rows.append({"import_key": "RA-007", "title": "", "owner_email": "viewer@example.org"})
        rows.append({"import_key": importer.EXAMPLE_KEY, "title": "Example"})
        _, preview = self.preview(self.owner, rows)
        by_key = {r["row"]: r for r in preview["rows"]}
        self.assertIn("E_STATUS_UNKNOWN", self.codes(by_key[2]))
        self.assertIn("E_CRITICALITY_UNKNOWN", self.codes(by_key[2]))
        self.assertIn("W_UNRESOLVED_PERSON", self.codes(by_key[2]))
        self.assertIn("E_DUP_KEY", self.codes(by_key[2]))
        self.assertIn("E_DUP_KEY", self.codes(by_key[4]))
        self.assertIn("W_PERSON_BY_NAME", self.codes(by_key[3]))
        self.assertEqual(by_key[3]["values"]["owner"], "Waseem")
        self.assertIn("E_PARENT_CYCLE", self.codes(by_key[5]) + self.codes(by_key[6]))
        self.assertIn("E_PARENT_UNKNOWN", self.codes(by_key[7]))
        self.assertIn("E_TITLE_MISSING", self.codes(by_key[8]))
        self.assertIn("E_EXAMPLE_ROW", self.codes(by_key[9]))

    def test_dependency_cycle_and_unknown_predecessor_are_errors(self):
        rows = [
            {"import_key": "A", "title": "A", "predecessors": "C"},
            {"import_key": "B", "title": "B", "predecessors": "A"},
            {"import_key": "C", "title": "C", "predecessors": "B"},
            {"import_key": "D", "title": "D", "predecessors": "ZZZ; A"},
            {"import_key": "E", "title": "E", "predecessors": "E"},
        ]
        _, preview = self.preview(self.owner, rows)
        by_key = {r["import_key"]: r for r in preview["rows"]}
        self.assertIn("E_DEP_CYCLE", self.codes(by_key["C"]))
        # Errors block the row and every row whose parent or predecessor it is: A waits for C
        # and B waits for A, so the whole cycle is refused rather than imported without its edges.
        self.assertIn("E_PRED_INVALID", self.codes(by_key["A"]))
        self.assertIn("E_PRED_INVALID", self.codes(by_key["B"]))
        self.assertIn("E_PRED_UNKNOWN", self.codes(by_key["D"]))
        self.assertIn("E_PRED_SELF", self.codes(by_key["E"]))
        with self.assertRaisesRegex(ValueError, "Nothing to import"):
            self.commit(self.owner, rows, valid_rows_only=True)
        rows.append({"import_key": "F", "title": "F", "predecessors": ""})
        rows.append({"import_key": "G", "title": "G", "predecessors": "F"})
        result = self.commit(self.owner, rows, valid_rows_only=True)
        self.assertEqual((result["create"], result["skipped_errors"], result["dependencies"]), (2, 5, 1))
        self.assertTrue(self.task_by_key("G")["is_blocked"])

    # -- commit and re-import -------------------------------------------
    def test_commit_creates_tasks_events_dependencies_and_import_record(self):
        data = filled_template(self.rows())
        preview = self.service.import_preview(self.owner, self.project["id"], "roadmap.xlsx", data)
        result = self.service.import_commit(self.owner, self.project["id"], "roadmap.xlsx", data, {}, preview["sha256"])
        self.assertEqual((result["create"], result["update"], result["dependencies"]), (3, 0, 1))
        first, second, third = (self.task_by_key(k) for k in ("RA-001", "RA-002", "RA-003"))
        self.assertEqual(first["status"], "assigned")
        self.assertEqual(first["owner_name"], "Jamal")
        self.assertEqual((first["start_date"], first["due_date"]), ("2026-09-01", "2026-09-07"))
        self.assertEqual((first["baseline_start_date"], first["baseline_due_date"]), ("2026-09-01", "2026-09-07"))
        self.assertEqual(first["next_action"], "Confirm vendor")
        self.assertIn("Notes:\nDue as written: Immediate", first["description"])
        self.assertEqual(second["criticality"], "high")
        self.assertTrue(second["is_blocked"])
        self.assertEqual(third["parent_task_id"], second["id"])
        self.assertEqual(third["is_milestone"], 1)  # Type = Milestone
        self.assertEqual(second["is_milestone"], 0)
        third_detail = self.service.task_detail(self.owner, third["id"])
        self.assertEqual(third_detail["imported_fields"], [
            {"key": "x_risk_dependency", "label": "Risk / Dependency", "value": "Printer capacity"},
            {"key": "x_type", "label": "Type", "value": "Milestone"},
        ])
        self.assertEqual((third["start_date"], third["due_date"]), ("2026-09-09", "2026-09-09"))
        events = self.service.task_events(self.owner, second["id"])
        self.assertEqual([e["event_type"] for e in events], ["task_created", "dependency_added"])
        self.assertEqual(events[0]["reason"], "Excel import roadmap.xlsx row 3")
        project_events = self.service.project_events(self.owner, self.project["id"])
        self.assertEqual(project_events[-1]["event_type"], "import_committed")
        detail = json.loads(project_events[-1]["detail_json"])
        self.assertEqual(detail["counts"]["create"], 3)
        imports = self.service.list_imports(self.owner)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0]["filename"], "roadmap.xlsx")
        report = self.service.import_report(self.owner, imports[0]["id"])
        lines = report["csv"].splitlines()
        self.assertEqual(lines[0].split(",")[:4], ["row", "import_key", "action", "level"])
        self.assertIn("RA-001,create,ok", lines[1])
        self.assertIn("01-09-2026,07-09-2026", lines[1])
        # the created task ids are in the report
        self.assertIn(first["id"], report["csv"])
        self.assertEqual(self.service.list_notifications(self.owner), [])  # owner's own import is not self-notified

    def test_reimport_updates_by_key_without_duplicates_or_deletes(self):
        rows = self.rows()
        self.commit(self.owner, rows)
        first_before = self.task_by_key("RA-001")
        rows[0]["due_date"] = "10-09-2026"
        rows[0]["reason"] = "Committee moved"
        rows[1]["title"] = ""                      # blank cell = leave as is (row still needs a title -> error? no: existing)
        rows[1]["title"] = "Awareness sessions"    # unchanged
        rows[1]["status"] = "Completed"            # governed on update -> skipped
        rows[2]["collaborators"] = "jamal@example.org"
        del rows[2]["due_date"]
        _, preview = self.preview(self.owner, rows)
        by_key = {r["import_key"]: r for r in preview["rows"]}
        self.assertEqual(by_key["RA-001"]["action"], "update")
        self.assertEqual(by_key["RA-001"]["changes"]["due_date"], {"from": "07-09-2026", "to": "10-09-2026"})
        self.assertIn("W_GOVERNED_STATUS", self.codes(by_key["RA-002"]))
        self.assertEqual(by_key["RA-002"]["action"], "unchanged")
        self.assertEqual(by_key["RA-003"]["action"], "update")  # collaborator added
        result = self.commit(self.owner, rows)
        self.assertEqual((result["create"], result["update"], result["unchanged"]), (0, 2, 1))
        tasks = self.service.list_tasks(self.owner, self.project["id"])
        self.assertEqual(len(tasks), 3)
        first = self.task_by_key("RA-001")
        self.assertEqual(first["due_date"], "2026-09-10")
        self.assertEqual(first["baseline_due_date"], "2026-09-07")  # baseline never overwritten
        self.assertEqual(first["revision"], first_before["revision"] + 1)
        events = self.service.task_events(self.owner, first["id"])
        self.assertEqual([e["event_type"] for e in events], ["task_created", "task_updated"])
        self.assertEqual(events[-1]["reason"], "Committee moved")
        self.assertEqual(self.task_by_key("RA-002")["status"], "in_progress")
        third = self.task_by_key("RA-003")
        self.assertEqual(third["due_date"], "2026-09-09")  # empty cell leaves the date alone
        self.assertEqual([r["role"] for r in self.service.list_task_reviewers(self.owner, third["id"])], ["collaborator"])
        self.assertEqual(len(self.service.list_imports(self.owner)), 2)

    # -- adversarial review fixes (2026-09-22) ---------------------------
    def test_import_cannot_move_a_task_out_of_a_protected_status_for_either_role(self):
        # AS-2: the status guard read only the target status, so a Manager's row with "In progress"
        # on a completed or on-hold task previewed as a plain update and commit wrote it.
        seed = [{"import_key": "P-1", "title": "Done", "status": "Completed"},
                {"import_key": "P-2", "title": "Held", "status": "On hold"},
                {"import_key": "P-3", "title": "Dropped", "status": "Cancelled"}]
        self.commit(self.owner, seed)
        stored = lambda: [self.task_by_key(key)["status"] for key in ("P-1", "P-2", "P-3")]  # noqa: E731
        self.assertEqual(stored(), ["completed", "on_hold", "cancelled"])
        edit = [dict(row, status="In progress") for row in seed]
        for actor, code in ((self.waseem, "W_PROTECTED_STATUS"), (self.owner, "W_GOVERNED_STATUS")):
            with self.subTest(actor=actor["email"]):
                _, preview = self.preview(actor, edit)
                for row in preview["rows"]:
                    self.assertEqual(self.codes(row), [code])
                    self.assertEqual(row["action"], "unchanged")
                    self.assertNotIn("status", row["changes"])
                    self.assertIn("left as", row["findings"][0]["message"])
                result = self.commit(actor, edit)
                self.assertEqual((result["update"], result["unchanged"]), (0, 3))
                self.assertEqual(stored(), ["completed", "on_hold", "cancelled"])

    def test_non_finite_or_huge_numbers_in_a_custom_number_column_are_errors(self):
        # DI-4 / XI3-02: nan / inf reached import_extras and the JSON bodies as NaN / Infinity.
        config = self.service.get_import_template_config(self.owner)
        config["columns"].append({"key": "x_budget", "label": "Budget", "type": "number", "custom": True, "enabled": True})
        self.service.set_import_template_config(self.owner, {"columns": config["columns"]})
        active = self.service._import_config()
        values = ("nan", "inf", "-Infinity", "1e999", "1e16", float("inf"), 1e300, float("nan"), "12.5", 1200)
        rows = [{"import_key": f"N-{i}", "title": f"n {i}", "x_budget": value} for i, value in enumerate(values)]
        data = filled_template(rows, active)
        preview = self.service.import_preview(self.owner, self.project["id"], "n.xlsx", data)
        seen = [(r["values"]["extras"].get("x_budget"), self.codes(r), r["findings"][0]["column"] if r["findings"] else "")
                for r in preview["rows"]]
        self.assertEqual(seen[-2:], [(12.5, [], ""), (1200, [], "")])
        for value, codes, column in seen[:-2]:
            self.assertEqual((value, codes, column), (None, ["E_CUSTOM_INVALID"], "Budget"))
        json.loads(json.dumps(preview, allow_nan=False))   # what web._json sends must be strict JSON
        self.assertIn("allow_nan=False", inspect.getsource(AstraHandler._json))
        result = self.service.import_commit(self.owner, self.project["id"], "n.xlsx", data, {"valid_rows_only": True})
        self.assertEqual(result["create"], 2)
        self.assertEqual([r["v"] for r in self.db.execute("SELECT json_valid(import_extras) v FROM tasks")], [1, 1])

    def test_date_serials_out_of_range_or_non_finite_are_findings_not_crashes(self):
        # XI3-01 / AS-7: 20260904 typed as digits in a date cell raised OverflowError -> HTTP 500.
        from astra.xlsx_reader import CellError, serial_to_date
        self.assertEqual(serial_to_date(2958465), date(9999, 12, 31))
        self.assertEqual(serial_to_date(2957003, True), date(9999, 12, 31))
        for value, date1904 in ((2958466, False), (2957004, True), (20260904, False), (1e300, False),
                                (float("inf"), False), (float("nan"), True), (60, False), (-1, True)):
            self.assertIsInstance(serial_to_date(value, date1904), CellError, value)
        cases = {"styled 20260904": Styled(20260904, 1), "styled 2958466": Styled(2958466, 1),
                 "styled 1e300": Styled("1e300", 1), "styled inf": Styled("inf", 1), "bare 20260904": 20260904,
                 "bare 1e300": 1e300, "bare inf": float("inf"), "bare nan": float("nan")}
        rows = [{"import_key": f"D-{i}", "title": label, "due_date": value} for i, (label, value) in enumerate(cases.items())]
        rows.append({"import_key": "D-ok", "title": "fine", "due_date": Styled(importer.excel_serial(date(2026, 9, 4)), 1)})
        _, preview = self.preview(self.owner, rows)
        for row in preview["rows"][:-1]:
            self.assertEqual(self.codes(row), ["E_DATE_INVALID"], row["values"]["title"])
            self.assertEqual(row["findings"][0]["column"], "Due Date")
        self.assertEqual((preview["rows"][-1]["level"], preview["rows"][-1]["values"]["due_date"]), ("ok", "04-09-2026"))

    def test_csv_line_endings_oversized_fields_and_utf16_are_handled(self):
        # XI3-05 / AS-7: csv.Error is not a ValueError and escaped as HTTP 500.
        import csv
        import io
        config = self.service._import_config()

        def csv_bytes(rows, terminator="\n"):
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator=terminator)
            writer.writerow([column.label for column in config.active])
            for row in rows:
                writer.writerow([row.get(column.key, "") for column in config.active])
            return buffer.getvalue().encode()

        preview = self.service.import_preview(self.owner, self.project["id"], "cr.csv",
                                              csv_bytes([{"import_key": "C-1", "title": "Alpha"}], "\r"))
        self.assertEqual([(r["import_key"], r["level"]) for r in preview["rows"]], [("C-1", "ok")])
        header = csv_bytes([]).decode().rstrip("\n")
        width = len(config.active)
        stray = (header + "\n" + ",".join(["C-2", "Al\rpha"] + [""] * (width - 2)) + "\n").encode()
        preview = self.service.import_preview(self.owner, self.project["id"], "stray.csv", stray)   # no 500
        self.assertEqual([r["import_key"] for r in preview["rows"]], ["C-2", "PHA"])
        huge = csv_bytes([{"import_key": "C-3", "title": "Long", "notes": "x" * 200_000}])
        preview = self.service.import_preview(self.owner, self.project["id"], "huge.csv", huge)
        self.assertEqual([(f["code"], f["column"]) for f in preview["rows"][0]["findings"]], [("E_CELL_TOO_LONG", "Notes")])
        wide = ("﻿" + csv_bytes([{"import_key": "C-4", "title": "Wide"}]).decode()).encode("utf-16")
        with self.assertRaisesRegex(importer.ImportFileError, "UTF-16"):
            self.service.import_preview(self.owner, self.project["id"], "wide.csv", wide)

    def test_commit_validates_inside_the_write_transaction_so_a_cycle_added_after_preview_is_refused(self):
        # DI-2: validation used to run in autocommit and only apply took the lock.
        alpha = self.service.create_task(self.owner, {"project_id": self.project["id"], "title": "Alpha"})
        beta = self.service.create_task(self.owner, {"project_id": self.project["id"], "title": "Beta"})
        self.service.import_template(self.owner, "csv", self.project["id"])          # assigns T-001 / T-002
        keys = {t["title"]: t["import_key"] for t in self.service.list_tasks(self.owner, self.project["id"])}
        rows = [{"import_key": keys["Alpha"], "title": "Alpha"},
                {"import_key": keys["Beta"], "title": "Beta", "predecessors": keys["Alpha"]}]
        data, preview = self.preview(self.owner, rows)
        self.assertEqual(preview["summary"]["errors"], 0)
        seen = []
        original = importer.ImportEngine.validate

        def recording(engine, parsed):
            seen.append(engine.db.in_transaction)
            return original(engine, parsed)

        importer.ImportEngine.validate = recording
        try:
            self.service.import_preview(self.owner, self.project["id"], "demo.xlsx", data)
            self.service.add_task_dependency(self.owner, beta["id"], alpha["id"])   # Beta -> Alpha by hand, after the preview
            with self.assertRaisesRegex(ValueError, "rows with errors"):
                self.service.import_commit(self.owner, self.project["id"], "demo.xlsx", data, {}, preview["sha256"])
        finally:
            importer.ImportEngine.validate = original
        self.assertEqual(seen, [False, True])   # preview validates in autocommit, commit inside BEGIN IMMEDIATE
        edges = {(r["predecessor_task_id"], r["successor_task_id"])
                 for r in self.db.execute("SELECT predecessor_task_id, successor_task_id FROM task_dependencies")}
        self.assertEqual(edges, {(beta["id"], alpha["id"])})
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM imports").fetchone()["c"], 0)
        self.assertFalse(self.db.in_transaction)

    def test_commit_refuses_a_plan_that_changed_since_the_preview(self):
        # DI-3: a row previewed as "create" became an update of a hand-made task that took the
        # same key through the pre-filled download in between, overwriting its title and dates.
        rows = [{"import_key": "T-001", "title": "Manager's new row", "start_date": "01-09-2026", "due_date": "05-09-2026"}]
        data, preview = self.preview(self.waseem, rows)
        self.assertEqual(preview["rows"][0]["action"], "create")
        self.assertRegex(preview["plan_fingerprint"], r"^[0-9a-f]{64}$")
        hand_made = self.service.create_task(self.owner, {"project_id": self.project["id"], "title": "Typed by the Owner",
                                                          "due_date": "2026-10-20"})
        self.service.import_template(self.owner, "xlsx", self.project["id"])   # assigns T-001 to the hand-made task
        self.assertEqual(self.service.get_task(self.owner, hand_made["id"])["import_key"], "T-001")
        with self.assertRaisesRegex(importer.ImportConflict, "changed since the preview"):
            self.service.import_commit(self.waseem, self.project["id"], "demo.xlsx", data, {}, preview["sha256"],
                                       preview["plan_fingerprint"])
        task = self.service.get_task(self.owner, hand_made["id"])
        self.assertEqual((task["title"], task["due_date"]), ("Typed by the Owner", "2026-10-20"))
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM imports").fetchone()["c"], 0)
        # a fresh preview shows the row as an update of the Owner's task; committing that plan is allowed
        _, again = self.preview(self.waseem, rows)
        self.assertEqual(again["rows"][0]["action"], "update")
        self.assertNotEqual(again["plan_fingerprint"], preview["plan_fingerprint"])
        result = self.service.import_commit(self.waseem, self.project["id"], "demo.xlsx", data, {}, again["sha256"],
                                            again["plan_fingerprint"])
        self.assertEqual(result["update"], 1)

    def test_project_sheet_timezone_working_days_and_date_order_are_validated(self):
        # DI-5: typed Timezone / Working Days fell back silently; start > target was stored.
        rows = [{"import_key": "NP-1", "title": "First"}]
        sheet = {"Project Name": "New From File", "Timezone": "Karachi/Asia", "Working Days": "Mon to Fri",
                 "Planned Start Date": "31-12-2026", "Planned Finish Date": "01-01-2026"}
        data = filled_template(rows, project=sheet)
        preview = self.service.import_preview(self.owner, None, "new.xlsx", data)
        header = preview["project_header"]
        self.assertEqual((header["timezone"], header["working_days"]), ("Asia/Karachi", "Every day"))
        self.assertTrue(any("'Karachi/Asia'" in w and "Asia/Karachi will be used" in w for w in preview["file_warnings"]))
        self.assertTrue(any("'Mon to Fri'" in w and "Every day will be used" in w for w in preview["file_warnings"]))
        self.assertEqual(self.codes(preview["rows"][0]), ["E_PROJECT_DATES"])
        self.assertIn("01-01-2026 is before its Planned Start Date 31-12-2026", preview["rows"][0]["findings"][0]["message"])
        with self.assertRaisesRegex(ValueError, "rows with errors"):
            self.service.import_commit(self.owner, None, "new.xlsx", data)
        self.assertIsNone(self.db.execute("SELECT id FROM projects WHERE name='New From File'").fetchone())
        # typed but acceptable values resolve without a warning and the project is created as resolved
        sheet.update({"Timezone": "asia/dubai", "Working Days": "mon-fri", "Planned Finish Date": "31-12-2027"})
        data = filled_template(rows, project=sheet)
        preview = self.service.import_preview(self.owner, None, "new.xlsx", data)
        self.assertEqual((preview["project_header"]["timezone"], preview["project_header"]["working_days"]), ("Asia/Dubai", "Mon-Fri"))
        self.assertEqual(preview["file_warnings"], [])
        self.service.import_commit(self.owner, None, "new.xlsx", data)
        project = self.db.execute("SELECT timezone, working_days, start_date, target_date FROM projects WHERE name='New From File'").fetchone()
        self.assertEqual(tuple(project), ("Asia/Dubai", "01234", "2026-12-31", "2027-12-31"))
        # for an existing target the sheet's dates are never applied: a file warning, not a blocked file
        bad = filled_template(rows, project={"Project Name": "Rupani Academy", "Planned Start Date": "31-12-2026",
                                             "Planned Finish Date": "01-01-2026"})
        preview = self.service.import_preview(self.owner, self.project["id"], "x.xlsx", bad)
        self.assertEqual(preview["summary"]["errors"], 0)
        self.assertTrue(any("not applied to an existing project" in w for w in preview["file_warnings"]))

    def test_excel_error_values_are_errors_in_every_column(self):
        # XI3-03: #N/A in a free-text column imported a task titled "Excel error value #N/A." with level ok.
        rows = [{"import_key": "E-1", "title": ErrorValue("#N/A"), "notes": ErrorValue("#REF!")},
                {"import_key": "E-2", "title": "Fine", "x_risk_dependency": ErrorValue("#DIV/0!"), "start_date": ErrorValue("#VALUE!")},
                {"import_key": "E-3", "title": "Good row", "notes": "kept"}]
        _, preview = self.preview(self.owner, rows)
        first, second, third = preview["rows"]
        self.assertEqual(sorted((f["code"], f["column"]) for f in first["findings"] if f["code"] == "E_CELL_ERROR"),
                         [("E_CELL_ERROR", "Notes"), ("E_CELL_ERROR", "Title")])
        self.assertIn("#N/A", first["findings"][0]["message"])
        self.assertEqual(sorted((f["code"], f["column"]) for f in second["findings"]),
                         [("E_CELL_ERROR", "Risk / Dependency"), ("E_CELL_ERROR", "Start Date")])
        self.assertEqual(third["level"], "ok")
        result = self.commit(self.owner, rows, valid_rows_only=True)
        self.assertEqual(result["create"], 1)
        self.assertEqual([t["title"] for t in self.service.list_tasks(self.owner, self.project["id"])], ["Good row"])

    def test_import_keys_are_canonicalised_to_upper_case(self):
        # XI3-09: the template's COUNTIF uniqueness rule is case-insensitive; the importer was byte-exact.
        self.commit(self.owner, [{"import_key": "T-001", "title": "One"}])
        rows = [{"import_key": "t-001", "title": "One"},
                {"import_key": "t-002", "title": "Two", "parent_key": "t-001", "predecessors": "t-001"},
                {"import_key": "T-002", "title": "Two again"}]
        _, preview = self.preview(self.owner, rows)
        self.assertEqual((preview["rows"][0]["import_key"], preview["rows"][0]["action"]), ("T-001", "unchanged"))
        self.assertIn("E_DUP_KEY", self.codes(preview["rows"][1]))
        self.assertIn("E_DUP_KEY", self.codes(preview["rows"][2]))
        rows.pop()
        result = self.commit(self.owner, rows)
        self.assertEqual((result["create"], result["unchanged"], result["dependencies"]), (1, 1, 1))
        tasks = self.service.list_tasks(self.owner, self.project["id"])
        self.assertEqual(sorted(t["import_key"] for t in tasks), ["T-001", "T-002"])
        self.assertEqual(self.task_by_key("T-002")["parent_task_id"], self.task_by_key("T-001")["id"])

    def test_custom_column_keys_must_be_safe_identifiers(self):
        # XI3-07: a client-supplied key such as x_a b"c< broke xl/workbook.xml for every download.
        base = self.service.get_import_template_config(self.owner)["columns"]
        for bad in ('x_a b"c<', "x_../etc", "x_UPPER", "x_" + "a" * 41):
            with self.subTest(key=bad), self.assertRaisesRegex(ValueError, "must be x_"):
                self.service.set_import_template_config(self.owner, {"columns": base + [
                    {"key": bad, "label": "Bad", "type": "text", "custom": True, "enabled": True}]})
        label = "Budget " + "x" * 53
        saved = self.service.set_import_template_config(self.owner, {"columns": base + [
            {"key": "", "label": label, "type": "text", "custom": True, "enabled": True},
            {"key": "", "label": label[:-1] + "y", "type": "text", "custom": True, "enabled": True}]})
        keys = [c["key"] for c in saved["columns"] if c.get("custom") and c["label"].startswith("Budget")]
        self.assertEqual(len(keys), 2)
        for key in keys:
            self.assertRegex(key, importer.CUSTOM_KEY_PATTERN)
        self.assertTrue(keys[1].endswith("_2"))
        importer.TemplateConfig.from_json(self.service._import_config().to_json())   # stored keys re-normalise
        read_workbook(self.service.import_template(self.owner, "xlsx")[0])            # and the workbook builds

    def test_list_only_and_reparent_updates_bump_revision_and_are_audited(self):
        # DI-6: a row that only added a collaborator counted as "update" but left updated_at and wrote no event.
        self.commit(self.owner, [{"import_key": "G-1", "title": "Gamma"}, {"import_key": "G-2", "title": "Delta"}])
        before = self.task_by_key("G-1")
        result = self.commit(self.owner, [{"import_key": "G-1", "title": "Gamma", "collaborators": "jamal@example.org"}])
        self.assertEqual(result["update"], 1)
        after = self.task_by_key("G-1")
        self.assertEqual(after["revision"], before["revision"] + 1)
        self.assertGreater(after["updated_at"], before["updated_at"])
        events = self.service.task_events(self.owner, after["id"])
        self.assertEqual(events[-1]["event_type"], "task_updated")
        self.assertEqual(json.loads(events[-1]["after_json"])["import_additions"],
                         {"people_added": [{"user_id": self.jamal["id"], "role": "collaborator"}]})
        self.commit(self.owner, [{"import_key": "G-1", "title": "Gamma", "parent_key": "G-2"}])
        moved = self.task_by_key("G-1")
        self.assertEqual((moved["parent_task_id"], moved["revision"]), (self.task_by_key("G-2")["id"], after["revision"] + 1))
        self.assertIn("parent_changed", [e["event_type"] for e in self.service.task_events(self.owner, moved["id"])])

    def test_parent_depth_warning_describes_the_gantt_rendering(self):
        # MS-7: the merged Gantt draws nested steps; the warning used to claim one level.
        rows = [{"import_key": "L-1", "title": "a"}, {"import_key": "L-2", "title": "b", "parent_key": "L-1"},
                {"import_key": "L-3", "title": "c", "parent_key": "L-2"}, {"import_key": "L-4", "title": "d", "parent_key": "L-3"}]
        _, preview = self.preview(self.owner, rows)
        self.assertEqual([self.codes(r) for r in preview["rows"]], [[], [], [], ["W_PARENT_DEPTH"]])
        self.assertIn("step of a step", preview["rows"][3]["findings"][0]["message"])

    def test_blank_template_is_for_the_owner_and_managers_only(self):
        # DTJ-03: the matrix row says Owner / Manager; the blank template carries labels, list values and hash.
        for actor in (self.owner, self.waseem):
            self.service.import_template(actor, "csv")
        for actor in (self.viewer, self.chair):
            with self.subTest(actor=actor["email"]), self.assertRaises(Forbidden):
                self.service.import_template(actor, "xlsx")

    def test_blank_title_on_reimport_is_an_error_not_leave_as_is(self):
        # DTJ-10: Title is the exception to "an empty cell leaves the field as is".
        self.commit(self.owner, [{"import_key": "B-1", "title": "Keep me", "due_date": "10-09-2026"}])
        _, preview = self.preview(self.owner, [{"import_key": "B-1", "title": "", "due_date": "12-09-2026"}])
        self.assertEqual((preview["rows"][0]["action"], self.codes(preview["rows"][0])), ("error", ["E_TITLE_MISSING"]))
        with self.assertRaisesRegex(ValueError, "rows with errors"):
            self.commit(self.owner, [{"import_key": "B-1", "title": "", "due_date": "12-09-2026"}])
        self.assertEqual((self.task_by_key("B-1")["title"], self.task_by_key("B-1")["due_date"]), ("Keep me", "2026-09-10"))

    def test_commit_is_atomic(self):
        rows = self.rows()
        data = filled_template(rows)
        engine_apply = importer.ImportEngine.apply

        def failing_apply(self_engine, *args, **kwargs):
            engine_apply(self_engine, *args, **kwargs)
            raise RuntimeError("boom after writes")

        importer.ImportEngine.apply = failing_apply
        try:
            with self.assertRaises(RuntimeError):
                self.service.import_commit(self.owner, self.project["id"], "demo.xlsx", data, {}, None)
        finally:
            importer.ImportEngine.apply = engine_apply
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM imports").fetchone()["c"], 0)

    def test_sha_mismatch_is_a_conflict(self):
        with self.assertRaises(importer.ImportConflict):
            self.commit(self.owner, self.rows(), sha="0" * 64)

    def test_owner_creates_project_from_the_project_sheet(self):
        self.service.seed_default_entities(self.owner)
        rows = self.rows()
        # RA-001 is owned by jamal (the Project sheet's manager), RA-002 by waseem, RA-003 by nobody.
        rows[2].pop("owner_email", None)
        rows[1]["collaborators"] = "viewer@example.org"
        header = {
            "Project Name": "Brand New Roadmap", "Description": "Roll-out plan", "Filing Entity": "Rupani IB College",
            "Project Manager Email": "jamal@example.org", "Sponsor / Executive Owner Email": "aly@example.org",
            "Timezone": "Europe/London", "Working Days": "Mon-Fri", "Planned Start Date": date(2026, 9, 1),
            "Planned Finish Date": "31-08-2028", "Plan As-of Date": "28-08-2026", "Source Document": "v001 workbook",
        }
        people = [("jamal@example.org", "Jamal", "Manager", ""), ("nobody@example.org", "Nobody", "Member", ""),
                  ("", "Academic Team", "", "group")]
        data = filled_template(rows, project=header, people=people)
        preview = self.service.import_preview(self.owner, None, "new.xlsx", data)
        self.assertTrue(preview["summary"]["project"]["create"])
        self.assertEqual(preview["summary"]["project"]["name"], "Brand New Roadmap")
        self.assertEqual(preview["project_header"]["start_date"], "2026-09-01")
        self.assertEqual(preview["project_header"]["target_date"], "2028-08-31")
        statuses = {p["email"] or p["name"]: p["status"] for p in preview["people"]}
        # jamal is "ok": active users named in a new-project import get access when the project is created
        self.assertEqual(statuses, {"jamal@example.org": "ok", "nobody@example.org": "unknown_user", "Academic Team": "group"})
        self.assertTrue(any("People row 3: nobody@example.org is not an Astra user" in w for w in preview["file_warnings"]))
        by_key = {r["import_key"]: r for r in preview["rows"]}
        self.assertEqual(by_key["RA-001"]["values"]["owner"], "Jamal")
        self.assertIn("I_ACCESS_GRANTED", self.codes(by_key["RA-001"]))
        self.assertIn("will be given manager access", by_key["RA-001"]["findings"][0]["message"])
        self.assertIn("will be given member access", by_key["RA-002"]["findings"][0]["message"])
        self.assertNotIn("W_PERSON_NOT_ELIGIBLE", self.codes(by_key["RA-001"]) + self.codes(by_key["RA-002"]))
        self.assertEqual(preview["summary"]["warnings"], 0)
        result = self.service.import_commit(self.owner, None, "new.xlsx", data, {}, None)
        self.assertTrue(result["project"]["create"])
        self.assertEqual(result["plan_as_of"], "2026-08-28")
        self.assertEqual(result["source_document"], "v001 workbook")
        project = self.service.get_project(self.owner, result["project"]["id"])
        self.assertEqual(project["name"], "Brand New Roadmap")
        self.assertEqual(project["timezone"], "Europe/London")
        self.assertEqual(project["working_days"], "01234")
        self.assertEqual((project["start_date"], project["target_date"]), ("2026-09-01", "2028-08-31"))
        self.assertEqual(project["manager_user_id"], self.jamal["id"])
        self.assertIn("Sponsor / Executive Owner: aly@example.org", project["description"])
        self.assertEqual([e["name"] for e in project["entities"]], ["Rupani IB College"])
        roles = {m["user_id"]: m["role"] for m in self.service.list_memberships(self.owner, project["id"])}
        self.assertEqual(roles, {self.jamal["id"]: "manager", self.waseem["id"]: "member", self.viewer["id"]: "member"})
        tasks = {t["import_key"]: t for t in self.service.list_tasks(self.owner, result["project"]["id"])}
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks["RA-001"]["owner_user_id"], self.jamal["id"])
        self.assertEqual(tasks["RA-002"]["owner_user_id"], self.waseem["id"])
        self.assertIsNone(tasks["RA-003"]["owner_user_id"])
        # an existing project named in the sheet is reused, not duplicated
        preview = self.service.import_preview(self.owner, None, "again.xlsx", data)
        self.assertFalse(preview["summary"]["project"]["create"])
        self.assertEqual(preview["summary"]["update"] + preview["summary"]["unchanged"], 3)

    # -- authorization ---------------------------------------------------
    def test_manager_imports_into_own_project_with_protected_actions_downgraded(self):
        config = self.enable_all_columns()
        rows = self.rows()
        rows[0]["status"] = "Completed"
        rows[0]["baseline_due_date"] = "01-09-2026"
        rows[0]["attachment_links"] = "\\\\server\\file.pdf"
        rows[0]["entity"] = "Rupani IB College"
        data = filled_template(rows, config)
        preview = self.service.import_preview(self.waseem, self.project["id"], "demo.xlsx", data)
        codes = self.codes(preview["rows"][0])
        for code in ("W_PROTECTED_STATUS", "W_BASELINE_SKIPPED", "W_ATTACHMENTS_SKIPPED", "W_ENTITY_SKIPPED"):
            self.assertIn(code, codes)
        self.assertEqual(preview["rows"][0]["values"]["status"], "assigned")
        result = self.service.import_commit(self.waseem, self.project["id"], "demo.xlsx", data, {}, None)
        self.assertEqual(result["create"], 3)
        first = self.task_by_key("RA-001")
        self.assertEqual(first["status"], "assigned")
        self.assertEqual(first["baseline_due_date"], "2026-09-07")  # implicit baseline from the dates, not the column
        self.assertEqual(self.service.list_task_attachments(self.owner, first["id"]), [])
        kinds = {n["kind"] for n in self.service.list_notifications(self.owner)}
        self.assertIn("import_committed", kinds)
        self.assertIn("task_created", kinds)
        # a Manager cannot create a project from the file
        with self.assertRaisesRegex(ValueError, "only the App Owner"):
            self.service.import_preview(self.waseem, None, "x.xlsx",
                                        filled_template(rows, config, project={"Project Name": "Managers cannot create"}))
        # the Project sheet must name the chosen project
        mismatch = filled_template(self.rows(), config, project={"Project Name": "Some other plan"})
        preview = self.service.import_preview(self.waseem, self.project["id"], "x.xlsx", mismatch)
        self.assertTrue(all("E_PROJECT_MISMATCH" in self.codes(r) for r in preview["rows"]))
        self.assertIn("Project sheet names 'Some other plan'", preview["rows"][0]["findings"][-1]["message"])

    def test_manager_into_unmanaged_project_viewer_and_chairman_are_blocked_and_owner_notified(self):
        data = filled_template(self.rows())
        for actor, project_id in ((self.waseem, self.other["id"]), (self.viewer, self.project["id"]),
                                  (self.chair, self.project["id"]), (self.chair, None)):
            with self.subTest(actor=actor["email"], project=project_id):
                with self.assertRaises(Forbidden):
                    self.service.import_preview(actor, project_id, "x.xlsx", data)
                with self.assertRaises(Forbidden):
                    self.service.import_commit(actor, project_id, "x.xlsx", data, {}, None)
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"], 0)
        blocked = [n for n in self.service.list_notifications(self.owner) if n["kind"] == "protected_action_blocked"]
        self.assertEqual(len(blocked), 8)
        events = self.service.project_events(self.owner, self.project["id"])
        self.assertTrue(all(e["event_type"] == "protected_action_blocked" for e in events))
        self.assertEqual(len(events), 4)
        result = self.commit(self.owner, self.rows())
        with self.assertRaises(Forbidden):
            self.service.import_report(self.viewer, result["import_id"])
        self.assertEqual(self.service.list_imports(self.viewer), [])
        self.assertEqual(len(self.service.list_imports(self.waseem)), 1)  # manager of the project may see it

    def test_import_targets_follow_roles(self):
        self.assertTrue(self.service.import_targets(self.owner)["can_create_project"])
        manager_targets = self.service.import_targets(self.waseem)
        self.assertEqual([p["name"] for p in manager_targets["projects"]], ["Rupani Academy"])
        self.assertFalse(manager_targets["can_create_project"])
        self.assertEqual(self.service.import_targets(self.viewer)["projects"], [])
        self.assertEqual(self.service.import_targets(self.chair)["projects"], [])

    # -- template configuration -----------------------------------------
    def test_template_config_round_trip_custom_column_and_stale_template(self):
        config = self.service.get_import_template_config(self.owner)
        version = config["version"]
        self.assertEqual(config["labels"][0], "Import Key")
        old_hash = config["hash"]
        columns = config["columns"]
        # disable % Complete, rename Notes, move Title to the front, add a list column and a date column
        for item in columns:
            if item["key"] == "progress":
                item["enabled"] = False
            if item["key"] == "notes":
                item["label"] = "Remarks"
        title = next(i for i in columns if i["key"] == "title")
        columns.remove(title)
        columns.insert(0, title)
        columns.append({"label": "Budget line", "type": "list", "values": ["Capex", "Opex"], "required": True, "custom": True})
        columns.append({"label": "Review date", "type": "date", "custom": True})
        saved = self.service.set_import_template_config(self.owner, {"columns": columns})
        self.assertEqual(saved["version"], version + 1)
        self.assertNotEqual(saved["hash"], old_hash)
        self.assertEqual(saved["labels"][0], "Title")
        self.assertNotIn("% Complete", saved["labels"])
        self.assertIn("Remarks", saved["labels"])
        self.assertIn("Budget line", saved["labels"])
        custom = [c for c in saved["columns"] if c.get("custom")]
        self.assertEqual([c["key"] for c in custom], ["x_type", "x_risk_dependency", "x_budget_line", "x_review_date"])
        # the template reflects the configuration
        payload, _, _ = self.service.import_template(self.owner, "xlsx")
        workbook = read_workbook(payload)
        self.assertEqual(workbook.sheet("Tasks").row_values(1), saved["labels"])
        import io
        import zipfile
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            tasks_xml = archive.read("xl/worksheets/sheet3.xml").decode()
            lists_xml = archive.read("xl/worksheets/sheet6.xml").decode()
            workbook_xml = archive.read("xl/workbook.xml").decode()
        budget_col = importer.column_letter(saved["labels"].index("Budget line") + 1)
        self.assertIn(f'sqref="{budget_col}2:{budget_col}2001"><formula1>Lists_x_budget_line</formula1>', tasks_xml)
        self.assertIn('<definedName name="Lists_x_budget_line">Lists!$', workbook_xml)
        self.assertIn(">Capex<", lists_xml)
        self.assertEqual(tasks_xml.count('type="date" operator="between"'), 3)
        # a template downloaded before the change is rejected
        stale = filled_template(self.rows(), config=importer.TemplateConfig.preset("full"))
        with self.assertRaisesRegex(ValueError, "template has changed"):
            self.service.import_preview(self.owner, self.project["id"], "stale.xlsx", stale)
        # custom values import into import_extras and show in task detail
        current = self.service._import_config()
        rows = self.rows()
        rows[0]["x_budget_line"] = "opex"
        rows[0]["x_review_date"] = "15-09-2026"
        rows[1]["x_budget_line"] = "Capex"
        rows[2]["x_budget_line"] = "Neither"
        preview = self.service.import_preview(self.owner, self.project["id"], "custom.xlsx", filled_template(rows, current))
        by_key = {r["import_key"]: r for r in preview["rows"]}
        self.assertIn("E_CUSTOM_INVALID", self.codes(by_key["RA-003"]))
        self.assertEqual(by_key["RA-001"]["values"]["extras"], {"x_budget_line": "Opex", "x_review_date": "2026-09-15"})
        rows[2]["x_budget_line"] = "Opex"
        self.service.import_commit(self.owner, self.project["id"], "custom.xlsx", filled_template(rows, current), {}, None)
        detail = self.service.task_detail(self.owner, self.task_by_key("RA-001")["id"])
        self.assertEqual(detail["imported_fields"], [
            {"key": "x_budget_line", "label": "Budget line", "value": "Opex"},
            {"key": "x_review_date", "label": "Review date", "value": "15-09-2026"},
        ])
        self.assertEqual(preview["rows"][0]["values"]["extras"], {"x_budget_line": "Opex", "x_review_date": "2026-09-15"})
        # re-import updates the value; required custom column blank on create is an error
        rows[0]["x_budget_line"] = "Capex"
        rows.append({"import_key": "RA-010", "title": "Needs budget"})
        preview = self.service.import_preview(self.owner, self.project["id"], "custom.xlsx", filled_template(rows, current))
        by_key = {r["import_key"]: r for r in preview["rows"]}
        self.assertEqual(by_key["RA-001"]["action"], "update")
        self.assertIn("E_REQUIRED", self.codes(by_key["RA-010"]))
        self.service.import_commit(self.owner, self.project["id"], "custom.xlsx", filled_template(rows, current),
                                   {"valid_rows_only": True}, None)
        detail = self.service.task_detail(self.owner, self.task_by_key("RA-001")["id"])
        self.assertEqual(detail["imported_fields"][0]["value"], "Capex")
        # reset returns to the Simple default
        reset = self.service.set_import_template_config(self.owner, {"reset": True})
        self.assertEqual(reset["hash"], importer.TemplateConfig.default().hash())
        self.assertNotEqual(reset["hash"], old_hash)
        self.assertEqual(reset["version"], version + 2)

    def test_template_config_validation_and_authorization(self):
        default = self.service.get_import_template_config(self.owner)["columns"]
        broken = [dict(c) for c in default]
        next(c for c in broken if c["key"] == "title")["enabled"] = False
        with self.assertRaisesRegex(ValueError, "core column"):
            self.service.set_import_template_config(self.owner, {"columns": broken})
        broken = [dict(c) for c in default]
        next(c for c in broken if c["key"] == "status")["label"] = "State"
        with self.assertRaisesRegex(ValueError, "cannot be renamed"):
            self.service.set_import_template_config(self.owner, {"columns": broken})
        broken = [dict(c) for c in default] + [{"label": "Notes", "type": "text", "custom": True}]
        with self.assertRaisesRegex(ValueError, "share the label"):
            self.service.set_import_template_config(self.owner, {"columns": broken})
        broken = [dict(c) for c in default] + [{"label": "Empty list", "type": "list", "values": [], "custom": True}]
        with self.assertRaisesRegex(ValueError, "at least one allowed value"):
            self.service.set_import_template_config(self.owner, {"columns": broken})
        too_many = [dict(c) for c in default] + [{"label": f"Extra {i}", "type": "text", "custom": True} for i in range(25)]
        with self.assertRaisesRegex(ValueError, "at most 40"):
            self.service.set_import_template_config(self.owner, {"columns": too_many})
        with self.assertRaises(Forbidden):
            self.service.set_import_template_config(self.waseem, {"columns": default})
        self.assertFalse(self.service.get_import_template_config(self.waseem)["can_edit"])
        with self.assertRaises(Forbidden):
            self.service.get_import_template_config(self.viewer)
        self.assertEqual(self.service.get_import_template_config(self.owner)["version"], 1)  # setUp's preset only

    # -- fixes from the 2026-09-22 independent review (probe ids in comments) ----
    def test_same_import_key_is_allowed_in_two_projects(self):
        # P17: keys are unique per project; the Simple template pre-fills T-001 for every project.
        self.service.grant_project_access(self.owner, self.other["id"], self.waseem["id"], "manager")
        first = self.commit(self.owner, [{"import_key": "T-001", "title": "Project A first task"}])
        second = self.commit(self.waseem, [{"import_key": "T-001", "title": "Project B first task"}], project_id=self.other["id"])
        self.assertEqual((first["create"], second["create"]), (1, 1))
        _, preview = self.preview(self.owner, [{"import_key": "T-001", "title": "Project B first task"}], project_id=self.other["id"])
        self.assertEqual((preview["rows"][0]["action"], preview["rows"][0]["level"]), ("unchanged", "ok"))
        self.assertEqual({t["import_key"] for t in self.service.list_tasks(self.owner, self.other["id"])}, {"T-001"})

    def test_dependency_cycle_through_an_existing_task_absent_from_the_file_is_refused(self):
        # P6a: existing B waits for A; a file that makes A wait for B closes the cycle through B.
        self.commit(self.owner, [{"import_key": "A", "title": "A"}, {"import_key": "B", "title": "B", "predecessors": "A"}])
        edges_before = self.db.execute("SELECT COUNT(*) c FROM task_dependencies").fetchone()["c"]
        rows = [{"import_key": "A", "title": "A", "predecessors": "B"}]
        _, preview = self.preview(self.owner, rows)
        self.assertIn("E_DEP_CYCLE", self.codes(preview["rows"][0]))
        self.assertFalse(preview["can_commit"])
        with self.assertRaisesRegex(ValueError, "errors"):
            self.commit(self.owner, rows)
        with self.assertRaisesRegex(ValueError, "Nothing to import"):
            self.commit(self.owner, rows, valid_rows_only=True)
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM task_dependencies").fetchone()["c"], edges_before)
        self.assertFalse(self.task_by_key("A")["is_blocked"])
        self.assertTrue(self.task_by_key("B")["is_blocked"])
        rows.append({"import_key": "C", "title": "C"})   # an independent row still imports alone
        result = self.commit(self.owner, rows, valid_rows_only=True)
        self.assertEqual((result["create"], result["skipped_errors"], result["dependencies"]), (1, 1, 0))
        # a longer cycle through two existing tasks: C waits for B (existing edge B <- A), then A waits for C
        self.commit(self.owner, [{"import_key": "C", "title": "C", "predecessors": "B"}])
        _, preview = self.preview(self.owner, [{"import_key": "A", "title": "A", "predecessors": "C"}])
        self.assertIn("E_DEP_CYCLE", self.codes(preview["rows"][0]))

    def test_parent_cycle_through_an_existing_task_absent_from_the_file_is_refused(self):
        # P6c: existing Y is a step of X; a file that makes X a step of Y closes the cycle through Y.
        self.commit(self.owner, [{"import_key": "X", "title": "X"}, {"import_key": "Y", "title": "Y", "parent_key": "X"}])
        rows = [{"import_key": "X", "title": "X", "parent_key": "Y"}]
        _, preview = self.preview(self.owner, rows)
        self.assertIn("E_PARENT_CYCLE", self.codes(preview["rows"][0]))
        with self.assertRaisesRegex(ValueError, "Nothing to import"):
            self.commit(self.owner, rows, valid_rows_only=True)
        x, y = self.task_by_key("X"), self.task_by_key("Y")
        self.assertIsNone(x["parent_task_id"])
        self.assertEqual(y["parent_task_id"], x["id"])
        self.commit(self.owner, [{"import_key": "Z", "title": "Z", "parent_key": "Y"}])   # X > Y > Z
        _, preview = self.preview(self.owner, [{"import_key": "X", "title": "X", "parent_key": "Z"}])
        self.assertIn("E_PARENT_CYCLE", self.codes(preview["rows"][0]))
        _, preview = self.preview(self.owner, [{"import_key": "W", "title": "W", "parent_key": "Z"}])   # a real 4th level
        self.assertEqual(self.codes(preview["rows"][0]), ["W_PARENT_DEPTH"])

    def test_existing_task_reparented_under_a_row_that_is_new_in_the_same_file(self):
        # P6d
        self.commit(self.owner, [{"import_key": "E", "title": "E"}])
        rows = [{"import_key": "N", "title": "New parent"}, {"import_key": "E", "title": "E", "parent_key": "N"}]
        _, preview = self.preview(self.owner, rows)
        by_key = {r["import_key"]: r for r in preview["rows"]}
        self.assertEqual(by_key["E"]["action"], "update")
        self.assertEqual(by_key["E"]["changes"]["parent_key"], {"from": "", "to": "N"})
        result = self.commit(self.owner, rows)
        self.assertEqual((result["create"], result["update"]), (1, 1))
        e, n = self.task_by_key("E"), self.task_by_key("N")
        self.assertEqual(e["parent_task_id"], n["id"])
        self.assertIn("parent_changed", [ev["event_type"] for ev in self.service.task_events(self.owner, e["id"])])
        _, preview = self.preview(self.owner, rows)
        self.assertEqual({r["action"] for r in preview["rows"]}, {"unchanged"})

    def test_child_of_a_parent_that_fails_in_dependency_wiring_is_an_error_too(self):
        # P5b: Q-2 fails only when the dependency cycle is found; its step and successor must fail with it.
        rows = [{"import_key": "Q-1", "title": "a", "predecessors": "Q-2"},
                {"import_key": "Q-2", "title": "b", "predecessors": "Q-1"},
                {"import_key": "Q-3", "title": "child of Q-2", "parent_key": "Q-2"},
                {"import_key": "Q-4", "title": "waits for Q-3", "predecessors": "Q-3"},
                {"import_key": "Q-5", "title": "independent"}]
        _, preview = self.preview(self.owner, rows, valid_rows_only=True)
        by_key = {r["import_key"]: r for r in preview["rows"]}
        self.assertIn("E_DEP_CYCLE", self.codes(by_key["Q-2"]))
        self.assertIn("E_PRED_INVALID", self.codes(by_key["Q-1"]))
        self.assertIn("E_PARENT_INVALID", self.codes(by_key["Q-3"]))
        self.assertIn("E_PRED_INVALID", self.codes(by_key["Q-4"]))
        self.assertEqual(by_key["Q-5"]["level"], "ok")
        result = self.commit(self.owner, rows, valid_rows_only=True)
        self.assertEqual((result["create"], result["skipped_errors"]), (1, 4))
        self.assertEqual([t["import_key"] for t in self.service.list_tasks(self.owner, self.project["id"])], ["Q-5"])

    def test_preview_returns_project_sheet_values_verbatim_and_the_dialog_escapes_them(self):
        # P15c/P15d: the JSON is data; the client escapes every server-provided string before innerHTML.
        xss = "<img src=x onerror=alert(1)>"
        data = filled_template([{"import_key": "X-1", "title": xss, "notes": xss}],
                               project={"Project Name": "Rupani Academy", "Project Manager Email": xss})
        preview = self.service.import_preview(self.owner, self.project["id"], "x.xlsx", data)
        self.assertEqual(preview["project_header"]["manager_email"], xss)
        self.assertEqual(preview["rows"][0]["values"]["title"], xss)
        source = (Path(importer.__file__).parent / "static" / "app.js").read_text(encoding="utf-8")
        review = source[source.index("function renderImportReview"):source.index("function applyImportFilter")]
        self.assertIn("manager ${escapeHtml(header.manager_email)}", review)
        # No server-provided value reaches innerHTML bare: the only unwrapped member interpolation is a count.
        self.assertEqual(re.findall(r"\$\{(?:header|v|r|x|f|project|p|s|c|col)\.[a-zA-Z_]+\}", review), ["${s.not_in_file}"])
        for name, start, end in (("upload", "function renderImportUpload", "function importHeaders"),
                                 ("confirm", "function renderImportConfirm", "// ---- Owner-only template settings"),
                                 ("settings", "async function renderTemplateSettings", "function buildImportedFields")):
            section = source[source.index(start):source.index(end)]
            bare = re.findall(r"\$\{(?:r|p|cfg|col|targets|project|x)\.[a-zA-Z_]+\}", section)
            self.assertEqual(bare, ["${col.type}"] if name == "settings" else [], name)  # col.type is escaped as part of `kind`

    def test_percent_formatted_cells_are_read_as_displayed(self):
        # P18: Excel stores 100% as 1.0 with a "0%" format; the reader returns what Excel shows.
        data = filled_template([{"import_key": "PC-1", "title": "t", "progress": Styled(1.0, PERCENT_STYLE)}])
        sheet = read_workbook(data).sheet("Tasks")
        labels = list(self.service._import_config().labels())
        cell = sheet.cell(2, labels.index("% Complete") + 1)
        self.assertIsInstance(cell, Percent)
        self.assertEqual(cell, 100)
        rows = [{"import_key": "PC-1", "title": "t", "progress": Styled(1.0, PERCENT_STYLE)},
                {"import_key": "PC-2", "title": "t", "progress": Styled(0.5, PERCENT_STYLE)},
                {"import_key": "PC-3", "title": "t", "progress": "100%"},
                {"import_key": "PC-4", "title": "t", "progress": 0.25},
                {"import_key": "PC-5", "title": "t", "progress": Styled(0.005, PERCENT_STYLE)}]
        _, preview = self.preview(self.owner, rows)
        by_key = {r["import_key"]: r for r in preview["rows"]}
        self.assertIn("E_PROGRESS_INVALID", self.codes(by_key["PC-5"]))   # 0.5% is not a whole number
        self.commit(self.owner, rows[:4])
        self.assertEqual({k: self.task_by_key(k)["progress"] for k in ("PC-1", "PC-2", "PC-3", "PC-4")},
                         {"PC-1": 100, "PC-2": 50, "PC-3": 100, "PC-4": 25})

    def test_workbook_declared_size_limits_are_per_part_and_in_total(self):
        # P1c: 8 MB per part, 20 MB per workbook, judged on the declared (inflated) sizes.
        data = filled_template(self.rows())
        forged = forge_declared_size(data, "xl/worksheets/sheet2.xml", 9 * 1024 * 1024)
        with self.assertRaisesRegex(importer.ImportTooLarge, "8 MB"):
            self.service.import_preview(self.owner, self.project["id"], "big.xlsx", forged)
        forged = data
        for index in (1, 2, 3):
            forged = forge_declared_size(forged, f"xl/worksheets/sheet{index}.xml", 7 * 1024 * 1024)
        with self.assertRaisesRegex(importer.ImportTooLarge, "20 MB in total"):
            self.service.import_preview(self.owner, self.project["id"], "big.xlsx", forged)
        self.assertTrue(issubclass(importer.ImportTooLarge, ValueError))
        self.assertEqual(self.service.import_preview(self.owner, self.project["id"], "ok.xlsx", data)["summary"]["rows"], 3)

    def test_bare_serial_dates_follow_the_workbook_date_system(self):
        # P12: a 1904-system workbook; the styled cell and the bare serial must agree.
        config = self.service._import_config()
        labels, keys = list(config.labels()), [c.key for c in config.active]
        row = [""] * len(labels)
        row[keys.index("import_key")], row[keys.index("title")] = "K", "t"
        row[keys.index("start_date")] = Styled(44807, 1)   # date style
        row[keys.index("due_date")] = 44807                # bare number
        sheets = [("Tasks", sheet_xml([labels, row])), ("_astra", sheet_xml([[importer.MARKER_NAME, config.hash()]]))]
        for date1904, expected in ((True, "04-09-2026"), (False, "03-09-2022")):
            with self.subTest(date1904=date1904):
                data = workbook_bytes(sheets, hidden=("_astra",), date1904=date1904)
                preview = self.service.import_preview(self.owner, self.project["id"], "d.xlsx", data)
                values = preview["rows"][0]["values"]
                self.assertEqual((values["start_date"], values["due_date"]), (expected, expected))
                self.assertEqual(preview["rows"][0]["level"], "ok")

    def test_data_in_an_unheaded_extra_column_is_reported(self):
        # P2d
        config = self.service._import_config()
        labels = list(config.labels())
        letter = importer.column_letter(len(labels) + 1)
        matrix = [labels, ["A", "x"] + [""] * (len(labels) - 2) + ["orphan value"], [""] * len(labels) + ["lonely"]]
        sheets = [("Tasks", sheet_xml(matrix)), ("_astra", sheet_xml([[importer.MARKER_NAME, config.hash()]]))]
        preview = self.service.import_preview(self.owner, self.project["id"], "x.xlsx", workbook_bytes(sheets, hidden=("_astra",)))
        self.assertEqual(preview["summary"]["rows"], 1)
        self.assertEqual(self.codes(preview["rows"][0]), ["W_EXTRA_DATA"])
        self.assertIn(f"column {letter}", preview["rows"][0]["findings"][0]["message"])
        self.assertTrue(any(f"Row 3: extra data ignored in column {letter}" in w for w in preview["file_warnings"]))

    def test_duplicate_key_race_during_commit_is_a_conflict_and_rolls_back(self):
        # P16b: someone inserts the same key between preview and apply.
        rows = [{"import_key": "A-1", "title": "a"}, {"import_key": "A-2", "title": "b"}]
        original = importer.ImportEngine.apply

        def racy(engine, service, project_id, import_id, **kwargs):
            engine.db.execute(
                "INSERT INTO tasks(id,project_id,title,status,created_at,created_by,updated_at,import_key)"
                " VALUES('racer',?,'racer','draft','2026-01-01',?,'2026-01-01','A-1')", (project_id, engine.actor["id"]))
            return original(engine, service, project_id, import_id, **kwargs)

        importer.ImportEngine.apply = racy
        try:
            with self.assertRaisesRegex(importer.ImportConflict, "Import Keys"):
                self.commit(self.owner, rows)
        finally:
            importer.ImportEngine.apply = original
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM imports").fetchone()["c"], 0)

    def test_owner_reimport_does_not_set_changes_requested_without_a_submission(self):
        # P7e
        self.commit(self.owner, [{"import_key": "S-2", "title": "work", "status": "In progress"}])
        _, preview = self.preview(self.owner, [{"import_key": "S-2", "title": "work", "status": "Changes requested"}])
        self.assertIn("W_GOVERNED_STATUS", self.codes(preview["rows"][0]))
        self.assertEqual((preview["rows"][0]["action"], preview["rows"][0]["values"]["status"]), ("unchanged", "in_progress"))
        self.commit(self.owner, [{"import_key": "S-2", "title": "work", "status": "Changes requested"}])
        self.assertEqual(self.task_by_key("S-2")["status"], "in_progress")

    def test_title_change_on_reimport_warns_and_readme_says_to_add_rows_at_the_bottom(self):
        # P11b: a deleted row shifts every pre-filled key below it; the title change is the visible symptom.
        self.commit(self.owner, [{"import_key": "T-001", "title": "Alpha"}, {"import_key": "T-002", "title": "Beta"}])
        _, preview = self.preview(self.owner, [{"import_key": "T-001", "title": "Alpha"}, {"import_key": "T-002", "title": "Gamma"}])
        by_key = {r["import_key"]: r for r in preview["rows"]}
        self.assertEqual(self.codes(by_key["T-001"]), [])
        self.assertEqual(self.codes(by_key["T-002"]), ["W_TITLE_CHANGED"])
        self.assertIn("'Beta' to 'Gamma'", by_key["T-002"]["findings"][0]["message"])
        self.assertEqual(by_key["T-002"]["action"], "update")
        for preset in ("simple", "full"):
            self.service.set_import_template_config(self.owner, {"preset": preset})
            payload, _, _ = self.service.import_template(self.owner, "xlsx")
            text = " ".join(str(v) for _, values in read_workbook(payload).sheet("README").iter_rows() for v in values if v)
            self.assertIn("do not insert or delete rows in the middle", text, preset)

    # -- project-scoped template download (Aly, 2026-09-22 07:18 UTC) ----------
    def add_manual_task(self, title, **fields):
        from uuid import uuid4
        task_id = uuid4().hex
        columns = {"id": task_id, "project_id": self.project["id"], "title": title, "status": "draft",
                   "created_at": "2026-09-01T00:00:00Z", "created_by": self.owner["id"], "updated_at": "2026-09-01T00:00:00Z", **fields}
        self.db.execute(f"INSERT INTO tasks({','.join(columns)}) VALUES({','.join('?' * len(columns))})", tuple(columns.values()))
        self.db.commit()
        return task_id

    def test_project_template_is_prefilled_assigns_keys_and_round_trips_unchanged(self):
        self.commit(self.owner, self.rows())        # RA-001..RA-003 (RA-003 is a milestone step of RA-002, RA-002 waits for RA-001)
        first = self.add_manual_task("Typed by hand", owner_user_id=self.jamal["id"], start_date="2026-10-01", due_date="2026-10-05",
                                     criticality="low", progress=40, description="Body\n\nNotes:\nfrom a meeting")
        second = self.add_manual_task("Another manual", created_at="2026-09-02T00:00:00Z", parent_task_id=first)
        self.add_manual_task("Already keyed", import_key="T-007", created_at="2026-09-03T00:00:00Z")
        events_before = self.db.execute("SELECT COUNT(*) c FROM task_events").fetchone()["c"]
        payload, filename, content_type = self.service.import_template(self.owner, "xlsx", self.project["id"])
        self.assertEqual(filename, "astra-import-rupani-academy.xlsx")
        self.assertIn("spreadsheetml", content_type)
        # keys assigned, persisted, audited, and continuing above the highest T-nnn in use
        keyed = {t["title"]: t["import_key"] for t in self.service.list_tasks(self.owner, self.project["id"])}
        self.assertEqual((keyed["Typed by hand"], keyed["Another manual"], keyed["Already keyed"]), ("T-008", "T-009", "T-007"))
        events = self.service.task_events(self.owner, first)
        self.assertEqual([e["event_type"] for e in events], ["import_key_assigned"])
        self.assertEqual(json.loads(events[0]["after_json"]), {"import_key": "T-008"})
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM task_events").fetchone()["c"], events_before + 2)
        self.assertEqual(self.service.list_notifications(self.owner), [])
        # the Tasks sheet holds the six tasks, parents before their steps
        config = self.service._import_config()
        labels = list(config.labels())
        sheet = read_workbook(payload).sheet("Tasks")
        col = {label: index for index, label in enumerate(labels)}
        rows = {row[col["Import Key"]]: row for row in (sheet.row_values(n, len(labels)) for n in range(2, 8))}
        self.assertEqual(sheet.max_row, 7)
        order = [sheet.cell(n, 1) for n in range(2, 8)]
        self.assertLess(order.index("RA-002"), order.index("RA-003"))
        self.assertLess(order.index("T-008"), order.index("T-009"))
        self.assertEqual(rows["RA-003"][col["Parent Key"]], "RA-002")
        self.assertEqual(rows["RA-003"][col["Type"]], "Milestone")
        self.assertEqual(rows["RA-003"][col["Risk / Dependency"]], "Printer capacity")
        self.assertEqual(rows["RA-003"][col["Start Date"]], date(2026, 9, 9))
        self.assertEqual(rows["RA-002"][col["Predecessors"]], "RA-001")
        self.assertEqual(rows["RA-002"][col["Owner Email"]], "waseem@example.org")
        self.assertEqual((rows["RA-002"][col["Status"]], rows["RA-002"][col["Criticality"]]), ("In progress", "High"))
        self.assertEqual(rows["RA-001"][col["Next Action / Decision Needed"]], "Confirm vendor")
        self.assertEqual(rows["RA-001"][col["Notes"]], "Due as written: Immediate")
        self.assertEqual(rows["T-008"][col["Notes"]], "from a meeting")
        self.assertEqual(rows["T-008"][col["Description"]], "Body\n\nNotes:\nfrom a meeting")
        self.assertEqual((rows["T-008"][col["% Complete"]], rows["T-008"][col["Criticality"]]), (40, "Low"))
        self.assertEqual(rows["T-009"][col["Parent Key"]], "T-008")
        self.assertIsNone(rows["RA-001"][col["Original Due Date"]])
        # Project and People sheets
        project_sheet = read_workbook(payload).sheet("Project")
        values = {str(project_sheet.cell(n, 1)).rstrip("* "): project_sheet.cell(n, 2) for n in range(2, project_sheet.max_row + 1)}
        self.assertEqual(values["Project Name"], "Rupani Academy")
        self.assertEqual(values["Project Manager Email"], "jamal@example.org")
        self.assertEqual(values["Timezone"], "Asia/Karachi")
        people = read_workbook(payload).sheet("People")
        self.assertEqual({people.cell(n, 1): people.cell(n, 3) for n in range(2, 5)},
                         {"jamal@example.org": "Manager", "waseem@example.org": "Manager", "viewer@example.org": "Viewer"})
        # the blank rows continue the pre-filled key formula from T-010 (row 8 -> ROW()-1+offset = 10)
        import io
        import zipfile
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            tasks_xml = archive.read("xl/worksheets/sheet3.xml").decode()
        self.assertIn('<c r="A8" s="8" t="str"><f>IF(B8="","","T-"&amp;TEXT(ROW()-1+3,"000"))</f></c>', tasks_xml)
        self.assertNotIn('<c r="A2" s="8" t="str"><f>', tasks_xml)
        # re-upload unedited: nothing to create, nothing to update, no warnings
        preview = self.service.import_preview(self.owner, self.project["id"], filename, payload)
        summary = preview["summary"]
        self.assertEqual((summary["create"], summary["update"], summary["unchanged"], summary["warnings"]), (0, 0, 6, 0))
        self.assertEqual(preview["project_header"]["name"], "Rupani Academy")
        # ... also through the CSV twin
        csv_payload, csv_name, _ = self.service.import_template(self.owner, "csv", self.project["id"])
        self.assertEqual(csv_name, "astra-import-rupani-academy.csv")
        import csv as csv_module
        import io as io_module
        csv_rows = list(csv_module.reader(io_module.StringIO(csv_payload.decode("utf-8-sig"))))
        self.assertEqual(len(csv_rows), 7)   # header + six tasks (multi-line descriptions stay quoted)
        self.assertEqual(csv_rows[0], labels)
        csv_by_key = {row[0]: row for row in csv_rows[1:]}
        self.assertEqual(csv_by_key["RA-003"][col["Start Date"]], "09-09-2026")
        csv_preview = self.service.import_preview(self.owner, self.project["id"], csv_name, csv_payload)
        self.assertEqual((csv_preview["summary"]["create"], csv_preview["summary"]["unchanged"]), (0, 6))
        # a title edit previews as exactly one update
        keys = [c.key for c in config.active]
        edited = [dict(zip(keys, sheet.row_values(n, len(labels)))) for n in range(2, 8)]
        for row in edited:
            for key in list(row):
                if row[key] is None:
                    del row[key]
        next(row for row in edited if row["import_key"] == "RA-001")["title"] = "Submit CP application (revised)"
        preview = self.service.import_preview(self.owner, self.project["id"], "edited.xlsx", filled_template(edited, config))
        self.assertEqual((preview["summary"]["update"], preview["summary"]["unchanged"]), (1, 5))
        by_key = {r["import_key"]: r for r in preview["rows"]}
        self.assertEqual(list(by_key["RA-001"]["changes"]), ["title"])
        self.assertIn("W_TITLE_CHANGED", self.codes(by_key["RA-001"]))
        # a second download assigns nothing new
        self.service.import_template(self.owner, "xlsx", self.project["id"])
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM task_events").fetchone()["c"], events_before + 2)

    def test_project_template_authorization_and_simple_preset(self):
        self.commit(self.owner, [{"import_key": "RA-001", "title": "One", "owner_email": "jamal@example.org"}])
        self.add_manual_task("Manual")
        payload, _, _ = self.service.import_template(self.waseem, "xlsx", self.project["id"])   # Manager of the project
        self.assertEqual(read_workbook(payload).sheet("Tasks").max_row, 3)
        with self.assertRaises(Forbidden):
            self.service.import_template(self.waseem, "xlsx", self.other["id"])                 # not managed
        with self.assertRaises(Forbidden):
            self.service.import_template(self.viewer, "xlsx", self.project["id"])
        with self.assertRaises(Forbidden):
            self.service.import_template(self.chair, "csv", self.project["id"])
        with self.assertRaises(KeyError):
            self.service.import_template(self.owner, "xlsx", "no-such-project")
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM tasks WHERE import_key IS NULL").fetchone()["c"], 0)
        # Simple preset: nine columns, no People sheet, literal keys then the shifted formula
        self.service.set_import_template_config(self.owner, {"preset": "simple"})
        payload, _, _ = self.service.import_template(self.owner, "xlsx", self.project["id"])
        workbook = read_workbook(payload)
        self.assertEqual([s.name for s in workbook.sheets], ["README", "Project", "Tasks", "Example", "Lists", "_astra"])
        by_key = {workbook.sheet("Tasks").cell(n, 1): workbook.sheet("Tasks").row_values(n, 9) for n in (2, 3)}
        self.assertEqual(by_key["RA-001"][:4], ["RA-001", "One", None, "jamal@example.org"])
        self.assertEqual(by_key["T-001"][:2], ["T-001", "Manual"])
        preview = self.service.import_preview(self.waseem, self.project["id"], "again.xlsx", payload)
        self.assertEqual((preview["summary"]["create"], preview["summary"]["unchanged"]), (0, 2))
        self.assertEqual(importer.assign_sequence_keys(["T-001", "T-003", "T-0004", "RA-9"], 2), ["T-005", "T-006"])
        self.assertEqual(importer.assign_sequence_keys([], 1), ["T-001"])
        self.assertEqual(importer.next_key_offset(["T-001", "T-002"], 2), 0)      # row 4 -> T-003
        self.assertEqual(importer.next_key_offset(["RA-001"], 1), -1)            # row 3 -> T-001

    def test_hostile_predecessor_cell_is_rejected_without_stalling_the_preview(self):
        # Regression review SECURITY-1 (2026-09-22): the former PRED_SUFFIX regex backtracked
        # cubically on 'a' + blanks + 'x', so a Manager's 1,200-character cell froze the whole
        # single-process server for ten seconds and a 4,000-character one for minutes.
        import time
        hostile = "a" + " " * 4998 + "x"
        rows = [{"import_key": "RD-001", "title": "redos", "predecessors": hostile},
                {"import_key": "RD-002", "title": "many", "predecessors": ";".join(["b" + " " * 300 + "y"] * 12)}]
        started = time.perf_counter()
        _, preview = self.preview(self.jamal, rows)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 5.0, f"preview took {elapsed:.1f}s")
        by_key = {r["import_key"]: r for r in preview["rows"]}
        self.assertIn("E_PRED_INVALID", self.codes(by_key["RD-001"]))
        self.assertIn("E_PRED_INVALID", self.codes(by_key["RD-002"]))
        self.assertEqual(by_key["RD-001"]["level"], "error")


class PredecessorSyntaxTests(unittest.TestCase):
    """parse_predecessor is a hand-written linear split (regression review SECURITY-1); these
    pin the syntax the former regex accepted so the rewrite changes nothing a template says."""

    KNOWN = {"RA-001", "T-1", "FS", "ABFS"}

    def test_a_5000_character_hostile_item_parses_in_under_50_ms(self):
        import time
        for item in ("a" + " " * 4998 + "x", "a" + " " * 4998 + "+1d", "RA-001" + " " * 4990 + "FS", " 1" * 2500 + "d"):
            started = time.perf_counter()
            result = importer.parse_predecessor(item, self.KNOWN)
            elapsed = time.perf_counter() - started
            self.assertLess(elapsed, 0.05, f"{len(item)} characters took {elapsed:.3f}s")
            self.assertIsNotNone(result[3], item[:20])
        # a long but plausible item under the ceiling still parses linearly
        started = time.perf_counter()
        self.assertEqual(importer.parse_predecessor("RA-001" + " " * 150 + "SS" + " " * 20 + "+ 2 days", self.KNOWN),
                         ("RA-001", "SS", "+2days", None))
        self.assertLess(time.perf_counter() - started, 0.05)

    def test_accepted_syntax_is_unchanged(self):
        # Expected values were recorded from the regex implementation (69f36a2) before the rewrite.
        cases = {
            "RA-001": ("RA-001", "FS", ""), "ra-001": ("RA-001", "FS", ""), "RA-001FS": ("RA-001", "FS", ""),
            "RA-001 FS": ("RA-001", "FS", ""), "RA-001SS+2d": ("RA-001", "SS", "+2d"), "RA-001 SS +2d": ("RA-001", "SS", "+2d"),
            "RA-001 ss -3 days": ("RA-001", "SS", "-3days"), "RA-001+2d": ("RA-001", "FS", "+2d"),
            "RA-001 +2 day": ("RA-001", "FS", "+2day"), "RA-001-2d": ("RA-001", "FS", "-2d"), "A-1-2d": ("A-1", "FS", "-2d"),
            "A-3D-3d": ("A-3D", "FS", "-3d"), "AB-3d": ("AB", "FS", "-3d"), "SSFS": ("SS", "FS", ""), "FSS": ("F", "SS", ""),
            "FFS": ("F", "FS", ""), "FS": ("FS", "FS", ""), "FS+2d": ("FS", "FS", "+2d"), "SSFS+2d": ("SS", "FS", "+2d"),
            "ABFS": ("ABFS", "FS", ""), "ABFS+1d": ("AB", "FS", "+1d"), "TASKSS": ("TASK", "SS", ""),
            "RA-001\tFS\t+2d": ("RA-001", "FS", "+2d"), "RA-001 FS+2days": ("RA-001", "FS", "+2days"), "T-1": ("T-1", "FS", ""),
            "t-1ff": ("T-1", "FF", ""), "RA-001 fs": ("RA-001", "FS", ""), "RA-001 Fs +0d": ("RA-001", "FS", "+0d"),
            "x" * 40 + " FS": ("X" * 40, "FS", ""), "RA_001.2-3": ("RA_001.2-3", "FS", ""),
            "RA-001 FS  +  12   DAYS": ("RA-001", "FS", "+12DAYS"), "9": ("9", "FS", ""), "9SF": ("9", "SF", ""),
            "  RA-001 SS  ": ("RA-001", "SS", ""),
        }
        for item, expected in cases.items():
            with self.subTest(item=item):
                self.assertEqual(importer.parse_predecessor(item, self.KNOWN), expected + (None,))
        invalid = ["RA 001 FS", "RA-001 FSX", "RA-001 FS 2d", "RA-001 FS +2", "RA-001 FS +2 da", "+2d", "-2d", "A+1d+2d", "",
                   "RA-001 XX", "x" * 41, ".RA", "RA-001 FSFS", "RA-001 FS FS", "A +2dd", "a" * 201]
        for item in invalid:
            with self.subTest(item=item):
                key, dep_type, lag, error = importer.parse_predecessor(item, self.KNOWN)
                self.assertEqual((key, dep_type, lag), (None, None, None))
                self.assertIn("is not a valid Import Key", error)
        self.assertNotIn("a" * 100, importer.parse_predecessor("a" * 201, self.KNOWN)[3])  # error text stays short


class ImportHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("ASTRA_HOME")
        os.environ["ASTRA_HOME"] = self.temp.name
        self.server = AstraServer(("127.0.0.1", 0))
        service = self.server.service
        self.owner = service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")
        self.manager = service.create_user(self.owner, "waseem@example.org", "Waseem", "waseem password safe", "member")
        self.viewer = service.create_user(self.owner, "viewer@example.org", "Viewer", "viewer password safe", "member")
        service.create_user(self.owner, "chair@example.org", "Chair", "chair password safe", "chairman")
        self.project = service.create_project(self.owner, "HTTP import")
        service.grant_project_access(self.owner, self.project["id"], self.manager["id"], "manager")
        service.grant_project_access(self.owner, self.project["id"], self.viewer["id"], "viewer")
        service.set_import_template_config(self.owner, {"preset": "full"})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)

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

    def request(self, method, path, body=None, *, cookie=None, csrf=None, raw=None, headers=None):
        request_headers = {"Content-Type": "application/octet-stream" if raw is not None else "application/json"}
        if cookie:
            request_headers["Cookie"] = cookie
        if csrf:
            request_headers["X-CSRF-Token"] = csrf
        request_headers.update(headers or {})
        payload = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        self.connection.request(method, path, payload, request_headers)
        response = self.connection.getresponse()
        content_type = response.getheader("Content-Type", "")
        data = response.read()
        parsed = json.loads(data) if content_type.startswith("application/json") else data
        return response, parsed

    def login(self, email, password):
        response, login = self.request("POST", "/api/login", {"email": email, "password": password})
        self.assertEqual(response.status, 200)
        return response.getheader("Set-Cookie").split(";", 1)[0], login["csrf"]

    def rows(self):
        return [
            {"import_key": "H-001", "title": "First", "owner_email": "waseem@example.org", "start_date": date(2026, 9, 1),
             "due_date": "07-09-2026", "status": "Not Started"},
            {"import_key": "H-002", "title": "Second", "due_date": "10-09-2026", "predecessors": "H-001"},
        ]

    def upload_headers(self, project_id, filename="rows.xlsx", sha=None, options=None, plan=None):
        headers = {"X-Filename": quote(filename), "X-Project-Id": project_id or ""}
        if sha:
            headers["X-Sha256"] = sha
        if plan:
            headers["X-Plan-Fingerprint"] = plan
        if options:
            headers["X-Options"] = quote(json.dumps(options))
        return headers

    def previewed_headers(self, cookie, csrf, data, project_id, **extra):
        """Preview first, as the dialog does: a commit over HTTP must carry the preview's plan fingerprint."""
        response, payload = self.request("POST", "/api/import/preview", cookie=cookie, csrf=csrf, raw=data,
                                         headers=self.upload_headers(project_id))
        self.assertEqual(response.status, 200)
        preview = payload["preview"]
        return self.upload_headers(project_id, sha=preview["sha256"], plan=preview["plan_fingerprint"], **extra)

    def test_template_downloads_in_both_formats(self):
        cookie, _ = self.login("waseem@example.org", "waseem password safe")
        response, payload = self.request("GET", "/api/import/template.xlsx", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertIn("spreadsheetml", response.getheader("Content-Type"))
        self.assertIn('filename="astra-import-template.xlsx"', response.getheader("Content-Disposition"))
        labels = read_workbook(payload).sheet("Tasks").row_values(1)
        self.assertEqual(labels[0], "Import Key")
        response, payload = self.request("GET", "/api/import/template.csv", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertTrue(payload.decode("utf-8-sig").startswith("Import Key,"))
        response, _ = self.request("GET", "/api/import/template.xlsx")
        self.assertEqual(response.status, 403)

    def test_preview_commit_report_and_conflict_over_http(self):
        cookie, csrf = self.login("owner@example.org", "correct horse battery")
        data = filled_template(self.rows())
        before, _ = self.request("GET", "/api/tasks", cookie=cookie)
        response, payload = self.request("POST", "/api/import/preview", cookie=cookie, csrf=csrf, raw=data,
                                         headers=self.upload_headers(self.project["id"], "Rupani Gantt — v1.xlsx"))
        self.assertEqual(response.status, 200)
        preview = payload["preview"]
        self.assertEqual(preview["filename"], "Rupani Gantt — v1.xlsx")
        self.assertEqual(preview["summary"]["create"], 2)
        _, after = self.request("GET", "/api/tasks", cookie=cookie)
        self.assertEqual(len(after["tasks"]), 0)
        response, payload = self.request("POST", "/api/import/commit", cookie=cookie, csrf=csrf, raw=data,
                                         headers=self.upload_headers(self.project["id"], sha="f" * 64,
                                                                     plan=preview["plan_fingerprint"]))
        self.assertEqual(response.status, 409)
        response, payload = self.request("POST", "/api/import/commit", cookie=cookie, csrf=csrf, raw=data,
                                         headers=self.upload_headers(self.project["id"], sha=preview["sha256"]))
        self.assertEqual(response.status, 400)   # a commit over HTTP must follow a preview (X-Plan-Fingerprint)
        self.assertIn("preview first", payload["error"])
        response, payload = self.request("POST", "/api/import/commit", cookie=cookie, csrf=csrf, raw=data,
                                         headers=self.upload_headers(self.project["id"], sha=preview["sha256"],
                                                                     plan=preview["plan_fingerprint"],
                                                                     options={"default_reason": "Board pack"}))
        self.assertEqual(response.status, 201)
        result = payload["result"]
        self.assertEqual(result["create"], 2)
        _, tasks = self.request("GET", "/api/tasks", cookie=cookie)
        self.assertEqual(sorted(t["import_key"] for t in tasks["tasks"]), ["H-001", "H-002"])
        second = next(t for t in tasks["tasks"] if t["import_key"] == "H-002")
        self.assertTrue(second["is_blocked"])
        response, report = self.request("GET", result["report_url"], cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertTrue(report.decode("utf-8-sig").startswith("row,import_key,action,level"))
        response, listing = self.request("GET", "/api/imports", cookie=cookie)
        self.assertEqual(len(listing["imports"]), 1)
        self.assertEqual(listing["imports"][0]["summary"]["create"], 2)
        response, _ = self.request("POST", "/api/import/preview", cookie=cookie, raw=data,
                                   headers=self.upload_headers(self.project["id"]))
        self.assertEqual(response.status, 403)  # CSRF still required for raw uploads

    def test_raw_upload_size_limit_returns_413_and_json_limit_is_unchanged(self):
        cookie, csrf = self.login("owner@example.org", "correct horse battery")
        headers = {"Content-Type": "application/octet-stream", "Cookie": cookie, "X-CSRF-Token": csrf,
                   "Content-Length": str(5 * 1024 * 1024 + 1)}
        self.connection.request("POST", "/api/import/preview", None, headers)
        response = self.connection.getresponse()
        self.assertEqual(response.status, 413)
        response.read()
        self.connection.close()
        self.connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        headers = {"Content-Type": "application/json", "Cookie": cookie, "X-CSRF-Token": csrf,
                   "Content-Length": str(1_000_001)}
        self.connection.request("POST", "/api/projects", None, headers)
        response = self.connection.getresponse()
        self.assertEqual(response.status, 400)
        response.read()

    def test_manager_imports_own_project_and_others_get_403_with_owner_notification(self):
        owner_cookie, owner_csrf = self.login("owner@example.org", "correct horse battery")
        _, other = self.request("POST", "/api/projects", {"name": "Not managed"}, cookie=owner_cookie, csrf=owner_csrf)
        data = filled_template(self.rows())
        cookie, csrf = self.login("waseem@example.org", "waseem password safe")
        response, payload = self.request("GET", "/api/import/targets", cookie=cookie)
        self.assertEqual([p["name"] for p in payload["targets"]["projects"]], ["HTTP import"])
        response, payload = self.request("POST", "/api/import/commit", cookie=cookie, csrf=csrf, raw=data,
                                         headers=self.previewed_headers(cookie, csrf, data, self.project["id"]))
        self.assertEqual(response.status, 201)
        self.assertEqual(payload["result"]["create"], 2)
        response, _ = self.request("POST", "/api/import/preview", cookie=cookie, csrf=csrf, raw=data,
                                   headers=self.upload_headers(other["project"]["id"]))
        self.assertEqual(response.status, 403)
        response, _ = self.request("PUT", "/api/import/template-config", {"columns": []}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 403)
        response, _ = self.request("GET", "/api/import/template-config", cookie=cookie)
        self.assertEqual(response.status, 200)
        for email, password in (("viewer@example.org", "viewer password safe"), ("chair@example.org", "chair password safe")):
            cookie, csrf = self.login(email, password)
            with self.subTest(actor=email):
                response, _ = self.request("POST", "/api/import/preview", cookie=cookie, csrf=csrf, raw=data,
                                           headers=self.upload_headers(self.project["id"]))
                self.assertEqual(response.status, 403)
                response, _ = self.request("POST", "/api/import/commit", cookie=cookie, csrf=csrf, raw=data,
                                           headers=self.upload_headers(self.project["id"]))
                self.assertEqual(response.status, 403)
                response, payload = self.request("GET", "/api/import/targets", cookie=cookie)
                self.assertEqual(payload["targets"]["projects"], [])
        _, inbox = self.request("GET", "/api/notifications", cookie=owner_cookie)
        blocked = [n for n in inbox["notifications"] if n["kind"] == "protected_action_blocked"]
        self.assertEqual(len(blocked), 5)
        self.assertTrue(any(n["kind"] == "import_committed" for n in inbox["notifications"]))
        _, tasks = self.request("GET", "/api/tasks", cookie=owner_cookie)
        self.assertEqual(len(tasks["tasks"]), 2)

    def test_template_config_over_http_and_stale_template_rejected(self):
        cookie, csrf = self.login("owner@example.org", "correct horse battery")
        stale = filled_template(self.rows())  # built against the default configuration
        response, payload = self.request("GET", "/api/import/template-config", cookie=cookie)
        columns = payload["config"]["columns"]
        columns.append({"label": "Cost centre", "type": "text", "custom": True})
        response, payload = self.request("PUT", "/api/import/template-config", {"columns": columns}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        self.assertIn("Cost centre", payload["config"]["labels"])
        self.assertEqual(payload["config"]["version"], 2)
        response, payload = self.request("POST", "/api/import/preview", cookie=cookie, csrf=csrf, raw=stale,
                                         headers=self.upload_headers(self.project["id"]))
        self.assertEqual(response.status, 400)
        self.assertIn("template has changed", payload["error"])
        response, _ = self.request("PUT", "/api/import/template-config", {"columns": columns}, cookie=cookie)
        self.assertEqual(response.status, 403)
        # presets over HTTP
        response, payload = self.request("PUT", "/api/import/template-config", {"preset": "simple"}, cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 200)
        self.assertEqual(len(payload["config"]["labels"]), 9)
        response, payload = self.request("PUT", "/api/import/template-config", {"preset": "full"}, cookie=cookie, csrf=csrf)
        self.assertEqual(len(payload["config"]["labels"]), 18)
        response, payload = self.request("POST", "/api/import/preview", cookie=cookie, csrf=csrf, raw=stale,
                                         headers=self.upload_headers(self.project["id"]))
        self.assertEqual(response.status, 200)  # the Full preset is the shape the file was built against

    def test_project_template_download_over_http_follows_roles(self):
        owner_cookie, owner_csrf = self.login("owner@example.org", "correct horse battery")
        data = filled_template(self.rows())
        response, _ = self.request("POST", "/api/import/commit", cookie=owner_cookie, csrf=owner_csrf, raw=data,
                                   headers=self.previewed_headers(owner_cookie, owner_csrf, data, self.project["id"]))
        self.assertEqual(response.status, 201)
        cookie, _ = self.login("waseem@example.org", "waseem password safe")
        response, payload = self.request("GET", f"/api/import/template.xlsx?project_id={self.project['id']}", cookie=cookie)
        self.assertEqual(response.status, 200)
        self.assertIn('filename="astra-import-http-import.xlsx"', response.getheader("Content-Disposition"))
        sheet = read_workbook(payload).sheet("Tasks")
        self.assertEqual([sheet.cell(2, 1), sheet.cell(3, 1)], ["H-001", "H-002"])
        _, other = self.request("POST", "/api/projects", {"name": "Not managed"}, cookie=owner_cookie, csrf=owner_csrf)
        response, _ = self.request("GET", f"/api/import/template.xlsx?project_id={other['project']['id']}", cookie=cookie)
        self.assertEqual(response.status, 403)
        response, _ = self.request("GET", "/api/import/template.csv?project_id=missing", cookie=owner_cookie)
        self.assertEqual(response.status, 404)
        viewer_cookie, _ = self.login("viewer@example.org", "viewer password safe")
        response, _ = self.request("GET", f"/api/import/template.csv?project_id={self.project['id']}", cookie=viewer_cookie)
        self.assertEqual(response.status, 403)
        response, _ = self.request("GET", "/api/import/template.xlsx?project_id=", cookie=viewer_cookie)
        self.assertEqual(response.status, 403)   # the blank template too is Owner / Manager only (DTJ-03)
        response, _ = self.request("GET", "/api/import/template.csv", cookie=viewer_cookie)
        self.assertEqual(response.status, 403)
        # the dialog switches its download links and copy when a project is selected
        source = (Path(importer.__file__).parent / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("Download template (with this project's tasks)", source)
        self.assertIn("?project_id=${encodeURIComponent(pid)}", source)

    def test_commit_returns_409_when_the_plan_fingerprint_no_longer_matches(self):
        # DI-3 over HTTP: the dialog sends the preview's fingerprint; a stale one is refused.
        cookie, csrf = self.login("owner@example.org", "correct horse battery")
        data = filled_template(self.rows())
        _, payload = self.request("POST", "/api/import/preview", cookie=cookie, csrf=csrf, raw=data,
                                  headers=self.upload_headers(self.project["id"]))
        preview = payload["preview"]
        self.assertRegex(preview["plan_fingerprint"], r"^[0-9a-f]{64}$")
        response, payload = self.request("POST", "/api/import/commit", cookie=cookie, csrf=csrf, raw=data,
                                         headers={**self.upload_headers(self.project["id"], sha=preview["sha256"]),
                                                  "X-Plan-Fingerprint": "0" * 64})
        self.assertEqual(response.status, 409)
        self.assertIn("changed since the preview", payload["error"])
        _, tasks = self.request("GET", "/api/tasks", cookie=cookie)
        self.assertEqual(tasks["tasks"], [])
        response, _ = self.request("POST", "/api/import/commit", cookie=cookie, csrf=csrf, raw=data,
                                   headers={**self.upload_headers(self.project["id"], sha=preview["sha256"]),
                                            "X-Plan-Fingerprint": preview["plan_fingerprint"]})
        self.assertEqual(response.status, 201)
        source = (Path(importer.__file__).parent / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('"X-Plan-Fingerprint":importState.preview.plan_fingerprint', source)

    def test_forged_workbook_sizes_return_413_and_json_ceiling_ignores_content_type(self):
        cookie, csrf = self.login("owner@example.org", "correct horse battery")
        forged = forge_declared_size(filled_template(self.rows()), "xl/worksheets/sheet2.xml", 9 * 1024 * 1024)
        response, payload = self.request("POST", "/api/import/preview", cookie=cookie, csrf=csrf, raw=forged,
                                         headers=self.upload_headers(self.project["id"]))
        self.assertEqual(response.status, 413)
        self.assertIn("8 MB", payload["error"])
        # a 2 MB body declared as octet-stream still hits the 1 MB JSON ceiling on a JSON route
        headers = {"Content-Type": "application/octet-stream", "Cookie": cookie, "X-CSRF-Token": csrf,
                   "Content-Length": str(2_000_000)}
        self.connection.request("POST", "/api/projects", None, headers)
        response = self.connection.getresponse()
        self.assertEqual(response.status, 400)
        response.read()
        self.connection.close()
        self.connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        _, tasks = self.request("GET", "/api/tasks", cookie=cookie)
        self.assertEqual(tasks["tasks"], [])

    def test_put_routes_delegate_to_the_service_layer(self):
        source = inspect.getsource(AstraHandler.do_PUT)
        self.assertNotIn("self.db.execute", source)
        branches = [line.strip() for line in source.splitlines() if line.strip().startswith("if path")]
        self.assertTrue(branches)
        for header in branches:
            index = source.index(header)
            body = source[index:].split("if path", 2)[1]
            self.assertIn("self.service.", body, header)
        route_pattern = re.compile(r'if path == "([^"]+)"')
        self.assertEqual([route_pattern.search(h).group(1) for h in branches], ["/api/import/template-config"])
