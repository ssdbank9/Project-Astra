---
id: 01M2HQJB5YP4VP6SMNSFY3WC71
title: Exports and search
status: review
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
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
updated-at: 2026-09-19T06:14:43Z
claimed-by: X1CarbonPC-32260
claimed-at: 2026-09-15T07:58:27Z
updated-by: Aly Jafferani
outcome-what: "Dropped the leading '# Astra export' comment row from both CSV exports (tasks + final results); header row is now first; the as-of date moved into the download filename via _as_of_slug."
outcome-why: "Owner wanted a clean header-first CSV; the in-band comment row broke Excel/parser import."
question: "Accept, or send back? The CSV has a leading '# Astra export — as of ...' comment line before the header row (Excel shows it as a row) — keep it, or drop it for a clean header-first CSV?"
outcome-resolves: "CSV starts with the header; filename carries the as-of date; export HTTP test asserts header-first + dated filename; full suite green."
---

# Exports and search

## Definition of Done

- [x] Export returns only the authorized current view with active filters and an as-of timestamp; search covers tasks/projects the actor may see and never leaks beyond scope; both enforced at the service boundary; unit + HTTP tests including a scope-isolation case; existing tests green.
  proof: service.search (scoped) + export_tasks (list_tasks authz + filters + as_of); GET /api/search, GET /api/export (JSON + CSV via _csv); search box + results dialog + Export CSV button; tests test_core.test_search_is_scope_limited/test_export_echoes_as_of_and_filters_and_is_scoped, test_web.test_search_and_export_over_http; 69 pass

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Service: search(actor,q) -> tasks+projects scoped to actor; export_tasks(actor,filters) reusing list_tasks authz + cosmetic filters + as_of
- [x] API: GET /api/search?q=; GET /api/export (JSON, or CSV via format=csv) with Content-Disposition
- [x] UI: search box -> results dialog (tasks clickable); Export CSV button honoring current filters
- [x] Tests: search scope isolation (member can't see other projects), export echoes as_of+filters, export scope-limited

## Progress
- **2026-09-15 08:02 · Aly Jafferani** — Search and export authorization both inherit the project-scope rules: search runs an EXISTS(memberships) clause for non-owner/chairman; export_tasks calls list_tasks (already authz) then applies cosmetic filters (status/entity/criticality/owner/band/open_only) mirroring the dashboard render(). Export carries as_of + the active filters. CSV variant (?format=csv) returns text/csv with Content-Disposition; the front-end Export CSV button builds the query from the current toolbar filters. Scope-isolation proven: a member's search returns only their granted project's task/project. No real-browser visual pass (no browser in session).
- **2026-09-15 18:31 · Aly Jafferani** — OWNER DECISION (2026-09-15): drop the leading '# Astra export - as of ...' comment line from CSV. Header row must be first for clean Excel/parser import. Put as-of/filters in the filename or a separate metadata channel, not an in-band comment row.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. Rework DONE per owner decision (CSV header-first; leading comment row dropped; as-of moved into filename via _as_of_slug). In REVIEW awaiting the model review pass. Re-claim first (claim is stale ~90h). Baseline: python tests/run.py = 102 green. After review pass: jaira move --to signoff with review-summary/gaps/verdict/check, and commit the ticket file with the code in one commit whose message names the handle (board is unshared, so the handle is what makes the commit list derivable).
