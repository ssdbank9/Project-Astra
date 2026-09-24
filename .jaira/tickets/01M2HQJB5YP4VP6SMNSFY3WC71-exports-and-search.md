---
id: 01M2HQJB5YP4VP6SMNSFY3WC71
title: Exports and search
status: review
ready: true
creator: Aly Jafferani
assignee: Claude
goal: Let an authorized user export the current dashboard view and search tasks/projects within their authorized scope.
context: |-
  Astra tracker, section 11 gap "Exports/search: Missing". No export or search endpoints/UI exist.
  Section 7/8 require exports to contain only the authorized current view + active filters + as-of time, and authorization to cover exports/search/downloads, not just navigation.
  Buildable now; no section 15 decision needed. Start: GET /api/export (current filtered view, CSV/JSON) and GET /api/search?q= scoped by can_view_project.
definition-of-done: Export returns only the authorized current view with active filters and an as-of timestamp; search covers tasks/projects the actor may see and never leaks beyond scope; both enforced at the service boundary; unit + HTTP tests including a scope-isolation case; existing tests green.
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T05:10:22Z
updated-at: 2026-09-24T05:56:25Z
claimed-by: vm-1022
claimed-at: 2026-09-24T05:49:42Z
updated-by: Claude
outcome-what: "Export scope tests at service and HTTP level (member excludes other project, hidden project_id 403, anonymous 403); both export CSV writers quote formula-leading cells via web._csv_cell (importer.FORMULA_PREFIXES); CSV filenames now carry active filters (__status=..., __open-only) after the as-of stamp; export buttons defer to the server filename; README exports bullet."
outcome-why: "Review send-back: removing export authorization passed every test; =1+1 titles were exported live into Excel; the header-first CSV had dropped the active filters instead of moving them to the filename as the owner decided."
question: "Accept, or send back? The CSV has a leading '# Astra export — as of ...' comment line before the header row (Excel shows it as a row) — keep it, or drop it for a clean header-first CSV?"
outcome-resolves: "DoD 2-4 ticked with proof; reviewer's auth-removal mutant now fails test_export_is_scope_limited_for_a_member and test_export_scope_isolation_over_http; full suite 339 tests OK; node --check, compileall, git diff --check clean."
review-summary: |-
  Search: AstraService.search (src/astra/service.py:992) matches task title/description and project name with LIKE. Owner and chairman see everything, capped at 50 rows. Everyone else sees only projects where they have a row in memberships, which is the same rule as can_view_project and list_tasks.

  Export: AstraService.export_tasks (service.py:1021) gets its rows from list_tasks, so authorization and the project_id 403 come from there. It then applies the dashboard filters (status, entity, criticality, owner, band, open_only), which match render() in static/app.js line for line, and returns {as_of, filters, tasks}.

  HTTP: GET /api/search?q= and GET /api/export (web.py:120 and :143) both call _require_user. /api/export returns JSON, or CSV when format=csv. The UI has a search box with a results dialog, and an Export CSV button that sends the current toolbar filters.

  The rework named in the outcome is in web.py:569-613. _csv and _csv_final_results now write the header row first, with no '# Astra export' comment line. The as-of timestamp moved into the Content-Disposition filename through _as_of_slug (web.py:31), for example astra-export-2026-09-24T05-17-21-808986-00-00.csv.

  Tests: test_core.test_search_is_scope_limited checks that a member's search stays inside their project. test_core.test_export_echoes_as_of_and_filters_and_is_scoped checks as_of and filters, but only runs as the owner. test_web.test_search_and_export_over_http runs as the owner and checks that the CSV starts with the header and has a dated filename.
review-gaps: |-
  1. (Medium) Nothing tests export's scope. test_export_echoes_as_of_and_filters_and_is_scoped only calls export_tasks as the owner, even though its name says it checks scope, and no other test uses export_tasks or /api/export. I checked by mutation in a scratch copy: I changed export_tasks to call list_tasks({**actor, "global_role": "owner"}, ...), which removes export authorization completely. All 164 tests in test_core and test_web still passed. A probe then showed a viewer getting the hidden project's "Secret hidden task" in their export, and exporting a hidden project_id without an error. The DoD says both features must never leak and that tests must include a scope-isolation case, so the export half is unguarded. The current code is correct: unmutated, a member gets only their own project, and a hidden project_id raises Forbidden.

  2. (Medium) CSV formula injection. _csv and _csv_final_results write cell values unchanged. A task titled =1+1 is exported as the row "P,=1+1,,draft,...". Titles, project names and final-result titles come from users and from imported sheets. The owner's reason for the rework was clean Excel import, so a planted =HYPERLINK(...) or DDE-style formula would run on the machine of whoever opens the export. Neither CSV writer neutralises cells that start with = + - @, tab or CR.

  3. (Low-medium) The CSV no longer shows which filters were applied. The owner's decision (progress note 2026-09-15 18:31) was to put "as-of/filters in the filename or a separate metadata channel". Only the as-of timestamp made it into the filename. The DoD's "with active filters" now holds for the JSON export only, and a downloaded CSV does not show what filters produced it.

  4. (Low) No HTTP test checks scope isolation, since the only HTTP test runs as the owner. No test checks that /api/search and /api/export reject unauthenticated calls; they do return 403 when probed. The outcome says both CSVs were changed, but no test covers the final-results CSV for header-first or the dated filename. Probing shows it behaves correctly.

  5. (Low) search does not escape LIKE wildcards. q=% returns every task in the actor's scope and q=_ matches everything. This stays inside scope, so nothing leaks, but the results are wrong.

  6. (Low) The as-of filename depends on the browser preferring Content-Disposition over the button's a.download="astra-export.csv". The HTML spec says it should, but nobody has checked in a browser; the progress note says there was no browser pass.

  7. (Bookkeeping) The DoD proof says "69 pass", which is stale; the full suite is now 335 tests and all pass. The ticket's commits list is empty and no commit names Y3WC71, so a move out of review needs a commit that names the handle.
review-verdict: "Send back. Both features work, and search and export use the same rule as can_view_project. Unauthenticated calls get 403, a hidden project_id is refused with Forbidden, and the header-first CSV with the dated filename works as described. Two medium items stop an approval. First, removing export authorization entirely still passes every test, so the DoD's scope-isolation requirement is only met for search. Second, both CSV exports allow formula injection into the Excel files the owner asked for. The CSV also dropped the active filters instead of moving them somewhere, as the owner's decision asked. Fix: add export scope tests at unit and HTTP level (a member's export excludes another project, and a hidden project_id gets 403), neutralise formula-leading cells in both CSV writers, and put the filters in the filename or a metadata channel, or get the owner to waive that."
review-check: "1. cd /workspace/project-astra && .venv/bin/python tests/run.py\n   You should see \"Ran 335 tests ... OK\".\n2. .venv/bin/python -m unittest tests.test_core.AstraCoreTests.test_search_is_scope_limited tests.test_web.AstraWebTests.test_search_and_export_over_http -v\n   Both should pass. If the class name differs, run: grep -n '^class' tests/test_core.py\n3. Show the export scope gap: in a scratch copy, edit src/astra/service.py export_tasks so it calls self.list_tasks({**actor, \"global_role\": \"owner\"}, ...). Then run .venv/bin/python -m unittest tests.test_core tests.test_web\n   You should see \"OK\", which means no test caught the removed authorization.\n4. Show the formula cell: start the app (.venv/bin/python -m astra) and log in as owner. Create a task titled =1+1 and click Export CSV.\n   The downloaded file's first line is the header, and the file name contains the date. The task row holds =1+1 unescaped, and Excel shows 2 in that cell.\n5. In the same app, set a Status filter and export again.\n   Neither the CSV contents nor the file name show the filter."
---

# Exports and search

## Definition of Done

- [x] Export returns only the authorized current view with active filters and an as-of timestamp; search covers tasks/projects the actor may see and never leaks beyond scope; both enforced at the service boundary; unit + HTTP tests including a scope-isolation case; existing tests green.
  proof: service.export_tasks (list_tasks authz); tests test_core.test_search_is_scope_limited, test_export_echoes_as_of_and_filters_and_is_scoped, test_export_is_scope_limited_for_a_member; test_web.test_search_and_export_over_http, test_export_scope_isolation_over_http; full suite 339 tests OK (2026-09-24)
- [x] Removing export authorization fails a test: a member's export (service, HTTP JSON and CSV) excludes another project's task and a hidden project_id is 403; anonymous search/export are 403.
  proof: tests/test_core.py test_export_is_scope_limited_for_a_member + tests/test_web.py test_export_scope_isolation_over_http; both fail with mutant list_tasks({**actor,'global_role':'owner'}) in export_tasks ('Secret hidden task' leaks)
- [x] Both export CSV writers (tasks, final results) neutralise cells starting with = + - @ tab or CR with a leading single quote, the same rule as importer.csv_cell.
  proof: src/astra/web.py _csv_cell (reuses importer.FORMULA_PREFIXES) used in _csv and _csv_final_results; test_web.test_csv_exports_neutralise_formula_cells; template/import-report CSVs already use importer.csv_cell (test_import SECURITY-2 test)
- [x] A downloaded CSV states its active filters without an in-band row: header stays first; the filename carries as-of and each active filter.
  proof: src/astra/web.py _filter_slug in both CSV filenames; test_web.test_csv_export_filename_names_the_active_filters; app.js export buttons use a.download="" so the server filename is the one saved; README.md exports bullet

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Service: search(actor,q) -> tasks+projects scoped to actor; export_tasks(actor,filters) reusing list_tasks authz + cosmetic filters + as_of
- [x] API: GET /api/search?q=; GET /api/export (JSON, or CSV via format=csv) with Content-Disposition
- [x] UI: search box -> results dialog (tasks clickable); Export CSV button honoring current filters
- [x] Tests: search scope isolation (member can't see other projects), export echoes as_of+filters, export scope-limited
- [x] Rework: regression tests first for export scope (unit + HTTP, mutant-checked), CSV formula cells, filters in CSV filename
- [x] Rework: _csv_cell (importer.FORMULA_PREFIXES) in both export CSV writers; _filter_slug in both CSV filenames; README

## Progress
- **2026-09-15 08:02 · Aly Jafferani** — Search and export authorization both inherit the project-scope rules: search runs an EXISTS(memberships) clause for non-owner/chairman; export_tasks calls list_tasks (already authz) then applies cosmetic filters (status/entity/criticality/owner/band/open_only) mirroring the dashboard render(). Export carries as_of + the active filters. CSV variant (?format=csv) returns text/csv with Content-Disposition; the front-end Export CSV button builds the query from the current toolbar filters. Scope-isolation proven: a member's search returns only their granted project's task/project. No real-browser visual pass (no browser in session).
- **2026-09-15 18:31 · Aly Jafferani** — OWNER DECISION (2026-09-15): drop the leading '# Astra export - as of ...' comment line from CSV. Header row must be first for clean Excel/parser import. Put as-of/filters in the filename or a separate metadata channel, not an in-band comment row.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. Rework DONE per owner decision (CSV header-first; leading comment row dropped; as-of moved into filename via _as_of_slug). In REVIEW awaiting the model review pass. Re-claim first (claim is stale ~90h). Baseline: python tests/run.py = 102 green. After review pass: jaira move --to signoff with review-summary/gaps/verdict/check, and commit the ticket file with the code in one commit whose message names the handle (board is unshared, so the handle is what makes the commit list derivable).
- **2026-09-24 05:30 · Claude** — Independent review verdict: send back. Recorded by Claude in review-summary/gaps/verdict/check. Why: no test guards export scope (auth-removal mutant passes), CSV formula injection in both CSV writers, and CSV no longer carries active filters. Left in review because the assignee is Aly Jafferani; moving it to in-progress needs Aly to move it or approve reassignment. Any rework commit must name Y3WC71.
- **2026-09-24 05:49 · Claude** — Reassigned to Claude with owner approval: Aly Jafferani replied 'Yes please fix them' in Slack (ts 1790228901.999149, 2026-09-24T05:48Z) to the send-back verdict. Reworking review gaps 1-4 and 7 (export scope tests, CSV formula injection, filters in CSV output, stale proof).
- **2026-09-24 05:56 · Claude** — Rework notes (not in the repo): (a) importer.csv_cell was NOT reused directly for exports: it normalises (trims, bool->Yes/No, date display) which would change exported values; web._csv_cell shares importer.FORMULA_PREFIXES and the quote rule only. PR #4 (C9KPH6, d295d78) is already on this branch and covers the template + import-report CSVs. (b) The service trims titles, so tab/CR-led titles never reach the export via HTTP; those two prefixes are covered by a direct _csv_cell unit assertion inside test_csv_exports_neutralise_formula_cells. (c) Filters go in the filename, not a comment row, per Aly's 2026-09-15 decision; format __key=value, values sanitised to [A-Za-z0-9._-], 40 chars each, 160 total then '__more'; sort is not a filter and is omitted. Filename shows raw project/entity ids, not names — resolving names would need a service change; the JSON export carries full filters. (d) app.js now sets a.download="" so the browser keeps the server's Content-Disposition name (review gap 6); still no real-browser check in this session. (e) Not fixed, out of scope: review gap 5 (search does not escape LIKE % and _; in-scope only, no leak).
