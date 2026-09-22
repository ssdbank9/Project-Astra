---
id: 01M33VD86SS216CCQEDVC9KPH6
title: Import tasks and Gantt from Excel/CSV
status: in-progress
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
updated-at: 2026-09-22T06:32:38Z
claimed-by: vm-2112
claimed-at: 2026-09-22T06:04:02Z
updated-by: Claude
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
- [ ] UI: Import button for eligible users; three-step dialog Upload/Review/Confirm; no inline style attributes; keyboard accessible; Escape closes; focus returns
- [ ] Tests: full suite green with the new parser, importer and HTTP tests, node --check app.js, git diff --check
- [ ] Browser evidence: screenshots of Upload, Review, Confirm, dashboard and Gantt after import plus a phone Review shot, recorded with a Manager uploading
- [x] Docs: README bullet, CONTEXT.md, docs/design/excel-import.md including how the Owner adds users before a Manager imports
  proof: README.md import bullet; CONTEXT.md Import section; docs/design/excel-import.md (incl. 'Before a Manager imports'); docs/design/authorization-matrix.md rows
- [x] Template configuration: Owner-only PUT /api/import/template-config (Managers may GET); enable/rename/reorder built-ins, core columns locked, custom text/number/date/list columns; template and upload validation follow the configuration; stale template rejected; custom values in tasks.import_extras shown read-only in task detail; tested
  proof: importer.TemplateConfig, AstraService.get_/set_import_template_config, web.py do_PUT; tests test_template_config_round_trip_custom_column_and_stale_template, test_template_config_validation_and_authorization, test_template_config_over_http_and_stale_template_rejected
- [x] Dates inside the import feature display as dd-mm-yyyy (template format, README, Review table, report) and the parser accepts dd-mm-yyyy text as well as ISO and Excel dates
  proof: importer.DISPLAY_DATE_FORMAT/display_date/parse_date_cell (DMY_DATE); tests assert '01-09-2026' in preview values and report; template styles formatCode dd-mm-yyyy
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
- [ ] UI: Import button + three-step dialog in index.html/app.js/style.css, class-based styling, keyboard/focus handling
- [x] Tests: tests/test_xlsx_reader.py, tests/test_import.py (service + HTTP), keep delegation test green
- [x] Docs: README, CONTEXT.md, docs/design/excel-import.md
- [ ] Browser evidence with fixture server (Waseem as Manager) and Playwright; kill server; verify clean git status
- [ ] Push branch, open draft PR, move ticket to review

## Progress
- **2026-09-22 06:12 · Claude** — Scope change 2 (Aly, 06:07 UTC): dates display dd-mm-yyyy within the import feature only (template number format, README, Review table, report; parser also accepts dd-mm-yyyy text). Owner-configurable template stored in import_template_config (enable/rename/reorder built-ins, add custom text/number/date/list columns, core columns locked); custom values land in tasks.import_extras JSON and show read-only in task detail; template hash marker replaces the fixed version number so stale templates are rejected. Endpoints GET/PUT /api/import/template-config. Schema v13 now also carries import_template_config and tasks.import_extras.
- **2026-09-22 06:32 · Claude** — Decisions while implementing: (1) dependency problems (unknown key, self, cycle) are row errors that block the row, not warnings that import the rest of the row - one rule 'errors block their row' is easier to explain than a per-column exception. (2) Managers' protected status changes are skipped with W_PROTECTED_STATUS rather than filed as owner_action_requests: the request path needs a task and a single action; a bulk import would create one request per row with no execution path yet (Gate 3). (3) The template example row uses key EXAMPLE-001 and the importer refuses it (E_EXAMPLE_ROW) so a half-filled template cannot import sample data. (4) Sheet protection uses the documented SHA-512 spin hash with a fixed documented password; it guards against accidents, not against a determined editor, and the docs say so. (5) Version marker = 16 hex chars of sha256 over the active column shape, written to hidden sheet _astra B1 and a defined name; exact header comparison is done in addition, so a renamed header is reported by column letter. (6) export CSV columns were left unchanged to avoid touching the export tests; import_key is already in the JSON export via t.*.
