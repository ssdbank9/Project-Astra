---
id: 01M33VD86SS216CCQEDVC9KPH6
title: Import tasks and Gantt from Excel/CSV
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Astra can load action items and Gantt rows from a locked, Owner-configurable Excel template or a CSV: the App Owner or a project Manager downloads the template, uploads a filled file, reviews per-row validation, and commits in one transaction that creates or updates tasks by Import Key with full audit, a downloadable report, and role-correct authorization."
context: |-
  What is wrong today: users keep action items and Gantt charts in Excel (example: the Rupani Academy Professional Executive Gantt workbook, 19 rows, header on row 6, prose dates such as TBD and Immediate) and Astra has no way to load them; every task must be typed by hand.
  Trigger: Aly Jafferani asked in #astra-builder on 2026-09-22 for a platform where users load an Excel based on Astra-provided columns and the Gantt and action items are populated.
  Scope change from Aly on 2026-09-22 05:59 UTC: import is not Owner-only; Managers may import into projects they manage; only the Owner may create a project from a file; the template must be locked (sheet protection, dropdowns, date validation, version marker) and uploads must match its header row exactly; real dates only, no grid-derived dates.
  Known: design in scratchpad excel-import/design-spec.md and template-columns.json; a stdlib zipfile+xml.etree parser was proven on the workbook (workbook-dump.md); Astra has no third-party dependencies and pyproject.toml must stay unchanged.
  Ruled out: openpyxl or any new dependency; silently guessing prose dates; deleting tasks on re-import; overwriting an existing baseline.
definition-of-done: |-
  Template download: GET /api/import/template.xlsx (Tasks sheet locked except data rows, dropdowns, date validation, frozen header, version marker, README sheet) and /api/import/template.csv
  Parser: stdlib-only xlsx reader (shared strings, inline strings, missing dimension, absolute rel targets, 1900/1904 dates, serial <= 60 rejected) plus CSV path (utf-8 BOM, utf-8, cp1252)
  Preview: per-row OK/warning/error with messages and resolved values; header row must match the template exactly (CSV aliases allowed with a warning); no database write
  Commit: one BEGIN IMMEDIATE transaction; upsert by Import Key; never deletes; never overwrites a baseline; finish-to-start dependencies by key with cycle check; task_event per created/updated task; project import_committed event; imports row
  Report: GET /api/imports/<id>/report.csv downloadable
  Authorization: Owner imports anywhere and may create a project; Manager imports only into managed projects with protected actions skipped by warning; Viewer/Chairman/non-manager get 403 and an Owner notification; all tested
  UI: Import button for eligible users; three-step dialog Upload/Review/Confirm; no inline style attributes; keyboard accessible; Escape closes; focus returns
  Tests: full suite green with the new parser, importer and HTTP tests, node --check app.js, git diff --check
  Browser evidence: screenshots of Upload, Review, Confirm, dashboard and Gantt after import plus a phone Review shot, recorded with a Manager uploading
  Docs: README bullet, CONTEXT.md, docs/design/excel-import.md including how the Owner adds users before a Manager imports
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-22T06:03:49Z
updated-at: 2026-09-22T07:07:28Z
claimed-by: vm-2112
claimed-at: 2026-09-22T06:04:02Z
updated-by: Claude
outcome-what: "Excel/CSV import for Astra: schema v13 (import_key, is_milestone, next_action_note, import_extras, imports, import_template_config); stdlib xlsx reader; importer with Owner-configurable template (Simple default / Full preset, custom columns), locked seven-sheet workbook generator, exact-header + hash validation, per-row findings, two-pass transactional upsert by Import Key; service authorization (Owner anywhere and may create a project from the Project sheet; Manager only into managed projects with Owner-only actions downgraded to warnings; others blocked, audited, Owner notified); HTTP routes incl. raw-body branch, 409/413, PUT template-config; three-step Import dialog with Template settings; 34 new tests (117 -> 151); docs; browser evidence in the scratchpad."
outcome-why: "Users keep action items and Gantt rows in Excel (Rupani Academy workbook) and Astra had no way to load them; Aly asked for a template-driven import on 2026-09-22 and refined it four times the same morning (Manager access, locked template, dd-mm-yyyy and configurable columns, researched v2 workbook, simple default)."
outcome-resolves: "DoD 1-13 ticked with proofs: template download (locked, validated, marked), stdlib parser, preview without writes, atomic commit with audit and report, role-correct authorization tested for Owner/Manager/Viewer/Chairman, CSP-safe keyboard-operable UI, full suite green, browser evidence with a Manager uploading, docs, template configuration, dd-mm-yyyy dates, workbook v2 parity with Simple/Full presets."
---

# Import tasks and Gantt from Excel/CSV

## Definition of Done

- [x] Template download: GET /api/import/template.xlsx (Tasks sheet locked except data rows, dropdowns, date validation, frozen header, version marker, README sheet) and /api/import/template.csv
  proof: src/astra/importer.py build_template_xlsx; tests/test_import.py test_template_workbook_is_locked_validated_and_marked, test_template_downloads_in_both_formats
- [x] Parser: stdlib-only xlsx reader (shared strings, inline strings, missing dimension, absolute rel targets, 1900/1904 dates, serial <= 60 rejected) plus CSV path (utf-8 BOM, utf-8, cp1252)
  proof: src/astra/xlsx_reader.py; tests/test_xlsx_reader.py (8 tests); CSV path tests/test_import.py test_csv_path_accepts_aliases_with_a_warning_and_bom
- [x] Preview: per-row OK/warning/error with messages and resolved values; header row must match the template exactly (CSV aliases allowed with a warning); no database write
  proof: AstraService.import_preview + ImportEngine.validate; tests test_preview_reports_rows_and_writes_nothing, test_header_mismatch_and_stale_marker_are_rejected, test_prose_dates_are_errors_never_guessed
- [x] Commit: one BEGIN IMMEDIATE transaction; upsert by Import Key; never deletes; never overwrites a baseline; finish-to-start dependencies by key with cycle check; task_event per created/updated task; project import_committed event; imports row
  proof: AstraService.import_commit + ImportEngine.apply; tests test_commit_creates_tasks_events_dependencies_and_import_record, test_reimport_updates_by_key_without_duplicates_or_deletes, test_commit_is_atomic, test_dependency_cycle_and_unknown_predecessor_are_errors
- [x] Report: GET /api/imports/<id>/report.csv downloadable
  proof: web.py GET /api/imports/<id>/report.csv -> AstraService.import_report; test_preview_commit_report_and_conflict_over_http
- [x] Authorization: Owner imports anywhere and may create a project; Manager imports only into managed projects with protected actions skipped by warning; Viewer/Chairman/non-manager get 403 and an Owner notification; all tested
  proof: AstraService._import_authorize/_import_blocked; tests test_manager_imports_into_own_project_with_protected_actions_downgraded, test_manager_into_unmanaged_project_viewer_and_chairman_are_blocked_and_owner_notified, test_manager_imports_own_project_and_others_get_403_with_owner_notification
- [x] UI: Import button for eligible users; three-step dialog Upload/Review/Confirm; no inline style attributes; keyboard accessible; Escape closes; focus returns
  proof: src/astra/static/index.html #import-btn + #import-dialog; app.js openImport/renderImportUpload/renderImportReview/renderImportConfirm/renderTemplateSettings; style.css .import-* classes (no inline style attributes); shoot.py: Tab reaches commit, Escape closes, focus returns to #import-btn
- [x] Tests: full suite green with the new parser, importer and HTTP tests, node --check app.js, git diff --check
  proof: .venv/bin/python tests/run.py: Ran 151 tests OK (117 before); node --check src/astra/static/app.js OK; git diff --check clean
- [x] Browser evidence: screenshots of Upload, Review, Confirm, dashboard and Gantt after import plus a phone Review shot, recorded with a Manager uploading
  proof: scratchpad/excel-import/shots/01..12 (Upload, raw workbook rejected, prose-date errors, Review, Confirm, dashboard, Gantt, detail, re-import, phone Review, Template settings incl. presets, Owner inbox) recorded with Waseem (Manager) uploading astra-import-sample-rupani-simple.xlsx; browser-evidence.md
- [x] Docs: README bullet, CONTEXT.md, docs/design/excel-import.md including how the Owner adds users before a Manager imports
  proof: README.md; CONTEXT.md Import section (presets); docs/design/excel-import.md (workbook v2 + Simple/Full presets, Project/People sheets, 'Before a Manager imports'); docs/design/authorization-matrix.md rows
- [x] Template configuration: Owner-only PUT /api/import/template-config (Managers may GET); enable/rename/reorder built-ins, core columns locked, custom text/number/date/list columns; template and upload validation follow the configuration; stale template rejected; custom values in tasks.import_extras shown read-only in task detail; tested
  proof: importer.TemplateConfig, AstraService.get_/set_import_template_config, web.py do_PUT; tests test_template_config_round_trip_custom_column_and_stale_template, test_template_config_validation_and_authorization, test_template_config_over_http_and_stale_template_rejected
- [x] Dates inside the import feature display as dd-mm-yyyy (template format, README, Review table, report) and the parser accepts dd-mm-yyyy text as well as ISO and Excel dates
  proof: importer.DISPLAY_DATE_FORMAT/display_date/parse_date_cell (DMY_DATE); tests assert '01-09-2026' in preview values and report; template styles formatCode dd-mm-yyyy
- [x] Workbook v2 parity: generated template has the 7 sheets (Lists hidden, _astra veryHidden), Tasks header equals config labels, _astra!B1 equals the config hash; Type=Milestone maps to is_milestone; Project sheet is the project header; People sheet cross-checked in preview; EXAMPLE-/EX- keys refused
  proof: tests test_simple_preset_is_the_default_and_full_is_one_call_away, test_template_workbook_is_locked_validated_and_marked (7 sheets under Full, header == labels, _astra!B1 == hash), test_commit_creates_tasks_events_dependencies_and_import_record (Type=Milestone -> is_milestone), test_owner_creates_project_from_the_project_sheet (Project + People sheets), test_template_download_round_trips_through_the_parser_and_example_keys_are_refused
Parser: stdlib-only xlsx reader (shared strings, inline strings, missing dimension, absolute rel targets, 1900/1904 dates, serial <= 60 rejected) plus CSV path (utf-8 BOM, utf-8, cp1252)
Preview: per-row OK/warning/error with messages and resolved values; header row must match the template exactly (CSV aliases allowed with a warning); no database write
Commit: one BEGIN IMMEDIATE transaction; upsert by Import Key; never deletes; never overwrites a baseline; finish-to-start dependencies by key with cycle check; task_event per created/updated task; project import_committed event; imports row
Report: GET /api/imports/<id>/report.csv downloadable
Authorization: Owner imports anywhere and may create a project; Manager imports only into managed projects with protected actions skipped by warning; Viewer/Chairman/non-manager get 403 and an Owner notification; all tested
UI: Import button for eligible users; three-step dialog Upload/Review/Confirm; no inline style attributes; keyboard accessible; Escape closes; focus returns
Tests: full suite green with the new parser, importer and HTTP tests, node --check app.js, git diff --check
Browser evidence: screenshots of Upload, Review, Confirm, dashboard and Gantt after import plus a phone Review shot, recorded with a Manager uploading
Docs: README bullet, CONTEXT.md, docs/design/excel-import.md including how the Owner adds users before a Manager imports

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Schema v13 in src/astra/db.py: tasks.import_key (unique per project), tasks.is_milestone, tasks.next_action_note, imports table
- [x] src/astra/xlsx_reader.py: stdlib zip+xml reader (sheets, rels, shared/inline strings, styles for date detection, 1900/1904, missing dimension, defined names, hidden sheets)
- [x] src/astra/importer.py: template column contract, locked template builder (xlsx via zipfile, csv), upload parser with exact-header check and CSV aliases, vocab tables, finding codes, row validator and commit plan
- [x] src/astra/service.py: import_targets, import_preview, import_commit, list_imports, import_report; authorization Owner/Manager with blocked-attempt audit + notification; next_action_note in _next_action
- [x] src/astra/web.py: raw-body branch (5 MB), template routes, targets, preview, commit (409 on sha mismatch, 413 oversize), imports report route
- [x] UI: Import button + three-step dialog in index.html/app.js/style.css, class-based styling, keyboard/focus handling
- [x] Tests: tests/test_xlsx_reader.py, tests/test_import.py (service + HTTP), keep delegation test green
- [x] Docs: README, CONTEXT.md, docs/design/excel-import.md
- [x] Browser evidence with fixture server (Waseem as Manager) and Playwright; kill server; verify clean git status
- [x] Push branch, open draft PR, move ticket to review
- [x] Rewrite template builder to the v2 seven-sheet structure with named-range dropdowns, CF rules, People formulas; make v2 config the default; parse Project/People sheets

## Progress
- **2026-09-22 06:12 · Claude** — Scope change 2 (Aly, 06:07 UTC): dates display dd-mm-yyyy within the import feature only (template number format, README, Review table, report; parser also accepts dd-mm-yyyy text). Owner-configurable template stored in import_template_config (enable/rename/reorder built-ins, add custom text/number/date/list columns, core columns locked); custom values land in tasks.import_extras JSON and show read-only in task detail; template hash marker replaces the fixed version number so stale templates are rejected. Endpoints GET/PUT /api/import/template-config. Schema v13 now also carries import_template_config and tasks.import_extras.
- **2026-09-22 06:32 · Claude** — Decisions while implementing: (1) dependency problems (unknown key, self, cycle) are row errors that block the row, not warnings that import the rest of the row - one rule 'errors block their row' is easier to explain than a per-column exception. (2) Managers' protected status changes are skipped with W_PROTECTED_STATUS rather than filed as owner_action_requests: the request path needs a task and a single action; a bulk import would create one request per row with no execution path yet (Gate 3). (3) The template example row uses key EXAMPLE-001 and the importer refuses it (E_EXAMPLE_ROW) so a half-filled template cannot import sample data. (4) Sheet protection uses the documented SHA-512 spin hash with a fixed documented password; it guards against accidents, not against a determined editor, and the docs say so. (5) Version marker = 16 hex chars of sha256 over the active column shape, written to hidden sheet _astra B1 and a defined name; exact header comparison is done in addition, so a renamed header is reported by column letter. (6) export CSV columns were left unchanged to avoid touching the export tests; import_key is already in the JSON export via t.*.
- **2026-09-22 06:36 · Claude** — Scope change 3 (Aly, via coordinator): adopt the researched 7-sheet workbook v2 (README, Project, Tasks, Example, People, Lists hidden, _astra veryHidden) as the default template; template-config-v2.json becomes the built-in default (18 of 25 columns on; custom x_type list and x_risk_dependency text). Importer maps Type=Milestone to is_milestone, reads the Project sheet as the project header (Owner may create from it; Manager's must match the chosen project), cross-checks the People sheet in preview, ignores Example and refuses keys starting EXAMPLE-/EX-. Stdlib limits vs build.py: header hover comments (VML part) are not emitted; guidance lives in input messages and README.
- **2026-09-22 07:07 · Claude** — Scope change 4 (Aly, 06:52 UTC): the default template is the Simple preset (nine columns: Import Key, Title, Step of (Key), Owner Email, Start Date, Due Date, Status, Criticality, Notes; hash 52cd3da7813769c1, equal to the design worker's template-config-simple.json); Full (v2, 18 columns, hash 53133bf237fe9b3c) is a one-click preset in Template settings. Title keeps its label (core columns are not renamed). Import Key cells carry =IF(B2="","","T-"&TEXT(ROW()-1,"000")) so untouched rows stay blank; the parser also skips rows whose only cell is a key. Simple workbook: 8-line README, 3-row Project sheet, 2-row Example, no People sheet; any column beyond the simple set switches the generator to the extended shape. Browser evidence redone with the simple sample. Pre-existing defects seen but not touched: Gantt bars use inline style attributes blocked by CSP; dashboard overflows horizontally at 1440px (Gate 2).
