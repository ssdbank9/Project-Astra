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
from astra.xlsx_reader import read_workbook

from import_fixtures import filled_template


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
            {"import_key": "RA-003", "title": "Prepare handouts", "parent_key": "RA-002", "milestone": "Yes",
             "due_date": "09-09-2026"},
        ]

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
        self.assertEqual([s.name for s in workbook.sheets], ["Tasks", "README", "_astra"])
        self.assertTrue(workbook.sheets[2].hidden)
        config = self.service._import_config()
        self.assertEqual(workbook.sheet("Tasks").row_values(1), list(config.labels()))
        self.assertEqual(workbook.sheet("Tasks").cell(2, 1), importer.EXAMPLE_KEY)
        self.assertEqual(workbook.sheet("_astra").cell(1, 2), config.hash())
        self.assertEqual(workbook.defined_names["AstraTemplateVersion"], "_astra!$B$1")
        import zipfile
        import io
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            tasks_xml = archive.read("xl/worksheets/sheet1.xml").decode()
            readme_xml = archive.read("xl/worksheets/sheet2.xml").decode()
            styles_xml = archive.read("xl/styles.xml").decode()
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
        # dropdowns for Status, Criticality, Milestone and date validation on the three date columns
        status_col = importer.column_letter(list(config.labels()).index("Status") + 1)
        self.assertIn(f'sqref="{status_col}2:{status_col}2001"><formula1>"Draft,Assigned,In progress', tasks_xml)
        self.assertIn('<formula1>"Critical,High,Normal,Low"</formula1>', tasks_xml)
        self.assertIn('<formula1>"Yes,No"</formula1>', tasks_xml)
        self.assertEqual(tasks_xml.count('type="date" operator="between"'), 3)
        self.assertIn(f"<formula1>{importer.excel_serial(importer.DATE_MIN)}</formula1>", tasks_xml)
        csv_payload, csv_name, _ = self.service.import_template(self.owner, "csv")
        self.assertEqual(csv_name, "astra-import-template.csv")
        self.assertEqual(csv_payload.decode("utf-8-sig").splitlines()[0], ",".join(config.labels()).replace("Duration (days)", "Duration (days)"))

    def test_template_download_round_trips_through_the_parser(self):
        payload, _, _ = self.service.import_template(self.owner, "xlsx")
        data, preview = payload, self.service.import_preview(self.owner, self.project["id"], "template.xlsx", payload)
        self.assertEqual(preview["summary"]["rows"], 1)
        self.assertIn("E_EXAMPLE_ROW", self.codes(preview["rows"][0]))

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
        with self.assertRaisesRegex(ValueError, "B: expected 'Project', found 'Entity'"):
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
        self.assertNotIn("E_DEP_CYCLE", self.codes(by_key["A"]) + self.codes(by_key["B"]))
        self.assertIn("E_PRED_UNKNOWN", self.codes(by_key["D"]))
        self.assertIn("E_PRED_SELF", self.codes(by_key["E"]))
        result = self.commit(self.owner, rows, valid_rows_only=True)
        self.assertEqual((result["create"], result["skipped_errors"], result["dependencies"]), (2, 3, 1))
        b = self.task_by_key("B")
        self.assertTrue(b["is_blocked"])

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
        self.assertEqual(third["is_milestone"], 1)
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

    def test_owner_creates_project_from_project_column(self):
        rows = self.rows()
        for row in rows:
            row["project"] = "Brand New Roadmap"
            row.pop("owner_email", None)
        data = filled_template(rows)
        preview = self.service.import_preview(self.owner, None, "new.xlsx", data)
        self.assertTrue(preview["summary"]["project"]["create"])
        self.assertEqual(preview["summary"]["project"]["name"], "Brand New Roadmap")
        result = self.service.import_commit(self.owner, None, "new.xlsx", data, {}, None)
        self.assertTrue(result["project"]["create"])
        names = [p["name"] for p in self.service.list_projects(self.owner)]
        self.assertIn("Brand New Roadmap", names)
        self.assertEqual(len(self.service.list_tasks(self.owner, result["project"]["id"])), 3)
        rows[0]["project"] = "Somewhere else"
        _, preview = self.preview(self.owner, rows)
        self.assertIn("E_PROJECT_MISMATCH", self.codes(preview["rows"][0]))

    # -- authorization ---------------------------------------------------
    def test_manager_imports_into_own_project_with_protected_actions_downgraded(self):
        rows = self.rows()
        rows[0]["status"] = "Completed"
        rows[0]["baseline_due_date"] = "01-09-2026"
        rows[0]["attachment_links"] = "\\\\server\\file.pdf"
        rows[0]["entity"] = "Rupani IB College"
        _, preview = self.preview(self.waseem, rows)
        codes = self.codes(preview["rows"][0])
        for code in ("W_PROTECTED_STATUS", "W_BASELINE_SKIPPED", "W_ATTACHMENTS_SKIPPED", "W_ENTITY_SKIPPED"):
            self.assertIn(code, codes)
        self.assertEqual(preview["rows"][0]["values"]["status"], "assigned")
        result = self.commit(self.waseem, rows)
        self.assertEqual(result["create"], 3)
        first = self.task_by_key("RA-001")
        self.assertEqual(first["status"], "assigned")
        self.assertEqual(first["baseline_due_date"], "2026-09-07")  # implicit baseline from the dates, not the column
        self.assertEqual(self.service.list_task_attachments(self.owner, first["id"]), [])
        kinds = {n["kind"] for n in self.service.list_notifications(self.owner)}
        self.assertIn("import_committed", kinds)
        self.assertIn("task_created", kinds)
        # a Manager cannot create a project from the file
        for row in rows:
            row["project"] = "Managers cannot create"
        with self.assertRaisesRegex(ValueError, "only the App Owner"):
            self.service.import_preview(self.waseem, None, "x.xlsx", filled_template(rows))

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
        self.assertEqual(config["version"], 0)
        self.assertEqual(config["labels"][0], "Import Key")
        old_hash = config["hash"]
        columns = config["columns"]
        # disable Entity, rename Notes, move Title to the front, add a list column and a date column
        for item in columns:
            if item["key"] == "entity":
                item["enabled"] = False
            if item["key"] == "notes":
                item["label"] = "Remarks"
        title = next(i for i in columns if i["key"] == "title")
        columns.remove(title)
        columns.insert(0, title)
        columns.append({"label": "Budget line", "type": "list", "values": ["Capex", "Opex"], "required": True, "custom": True})
        columns.append({"label": "Review date", "type": "date", "custom": True})
        saved = self.service.set_import_template_config(self.owner, {"columns": columns})
        self.assertEqual(saved["version"], 1)
        self.assertNotEqual(saved["hash"], old_hash)
        self.assertEqual(saved["labels"][0], "Title")
        self.assertNotIn("Entity", saved["labels"])
        self.assertIn("Remarks", saved["labels"])
        self.assertIn("Budget line", saved["labels"])
        custom = [c for c in saved["columns"] if c.get("custom")]
        self.assertEqual([c["key"] for c in custom], ["x_budget_line", "x_review_date"])
        # the template reflects the configuration
        payload, _, _ = self.service.import_template(self.owner, "xlsx")
        workbook = read_workbook(payload)
        self.assertEqual(workbook.sheet("Tasks").row_values(1), saved["labels"])
        import io
        import zipfile
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            tasks_xml = archive.read("xl/worksheets/sheet1.xml").decode()
        budget_col = importer.column_letter(saved["labels"].index("Budget line") + 1)
        self.assertIn(f'sqref="{budget_col}2:{budget_col}2001"><formula1>"Capex,Opex"</formula1>', tasks_xml)
        self.assertEqual(tasks_xml.count('type="date" operator="between"'), 4)
        # a template downloaded before the change is rejected
        stale = filled_template(self.rows(), config=importer.TemplateConfig.default())
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
        # reset
        reset = self.service.set_import_template_config(self.owner, {"reset": True})
        self.assertEqual(reset["hash"], old_hash)
        self.assertEqual(reset["version"], 2)

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
        too_many = [dict(c) for c in default] + [{"label": f"Extra {i}", "type": "text", "custom": True} for i in range(20)]
        with self.assertRaisesRegex(ValueError, "at most 40"):
            self.service.set_import_template_config(self.owner, {"columns": too_many})
        with self.assertRaises(Forbidden):
            self.service.set_import_template_config(self.waseem, {"columns": default})
        self.assertFalse(self.service.get_import_template_config(self.waseem)["can_edit"])
        with self.assertRaises(Forbidden):
            self.service.get_import_template_config(self.viewer)
        self.assertEqual(self.service.get_import_template_config(self.owner)["version"], 0)


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

    def upload_headers(self, project_id, filename="rows.xlsx", sha=None, options=None):
        headers = {"X-Filename": quote(filename), "X-Project-Id": project_id or ""}
        if sha:
            headers["X-Sha256"] = sha
        if options:
            headers["X-Options"] = quote(json.dumps(options))
        return headers

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
                                         headers=self.upload_headers(self.project["id"], sha="f" * 64))
        self.assertEqual(response.status, 409)
        response, payload = self.request("POST", "/api/import/commit", cookie=cookie, csrf=csrf, raw=data,
                                         headers=self.upload_headers(self.project["id"], sha=preview["sha256"],
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
                                         headers=self.upload_headers(self.project["id"]))
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
        self.assertEqual(payload["config"]["version"], 1)
        response, payload = self.request("POST", "/api/import/preview", cookie=cookie, csrf=csrf, raw=stale,
                                         headers=self.upload_headers(self.project["id"]))
        self.assertEqual(response.status, 400)
        self.assertIn("template has changed", payload["error"])
        response, _ = self.request("PUT", "/api/import/template-config", {"columns": columns}, cookie=cookie)
        self.assertEqual(response.status, 403)

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
