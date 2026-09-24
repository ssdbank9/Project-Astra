---
id: 01M2HQJB5YP4VP6SMNSFY3WC71
title: Exports and search
status: signoff
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
updated-at: 2026-09-24T06:02:06Z
claimed-by: vm-1022
claimed-at: 2026-09-24T05:49:42Z
updated-by: Claude
outcome-what: "Independent review approved the export scope, CSV formula neutralisation and filter-named filename rework"
outcome-why: "Review found no medium-or-higher issues; 339 tests green and all mutants killed"
question: "Accept, or send back? The CSV has a leading '# Astra export — as of ...' comment line before the header row (Excel shows it as a row) — keep it, or drop it for a clean header-first CSV?"
outcome-resolves: "Ready for a person to accept in signoff; low gaps recorded in review-gaps"
review-summary: "Adds export scope tests at service and HTTP level: a member never sees another project's task, a hidden project_id returns 403, and anonymous search and export return 403; the auth-removal mutant now fails both. Task and final-results CSV writers prefix a single quote on any cell starting with = + - @, tab or CR (web._csv_cell with the shared importer.FORMULA_PREFIXES). Both CSVs still start with their header row. Filenames list the active filters (e.g. __status=in_progress__open-only) after the as-of stamp, sanitised so no quote, slash or CR/LF reaches the header, per the owner's 2026-09-15 decision against an in-band row. Export buttons use the server filename; README documents it."
review-gaps: "Low only: (1) web._csv_cell does not trim leading whitespace before checking the first character, unlike importer.csv_cell, so '  =x' stays unquoted; service trims titles so risk is small. (2) _filter_slug names filters the service ignored (e.g. type=foo, band=abc). (3) Final-results member scope is tested only at service level (test_core), not over HTTP. (4) Ticket question field is stale (comment-row question decided 2026-09-15). (5) No real browser confirmed a.download=\"\" in app.js:459/:468 takes the Content-Disposition name. Info: search does not escape LIKE wildcards % and _; stays within scope, nothing leaks."
review-verdict: "Approve — independent reviewer"
review-check: "Scratch copies via git archive (worktree clean at 8e87151). Full suite tests/run.py: 339 tests OK in 184s; compileall, node --check app.js, git diff --check clean. New tests vs old code: formula and filename tests fail, scope tests pass (guards). Mutants all killed: export_tasks as owner; _csv_cell removed from _csv and from _csv_final_results; FORMULA_PREFIXES[:4]; quote/slash/backslash allowed in _filter_slug; _filter_slug removed from final-results filename; list_final_results membership removed (test_core catches); list_tasks membership removed. Test diff only adds tests. d295d78 already on base; commit carries id, trailers, and ticket file."
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
