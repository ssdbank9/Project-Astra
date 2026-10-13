---
id: 01M4984M493GAEKAN10HW6ZSGA
title: Project plan options and minimal bound workplan CSV
status: signoff
ready: true
creator: Codex
assignee: Codex
goal: "One project can contain Shared and alternative plans; users download one CSV, enter tasks and upload to populate the Gantt."
context: "Aly approved single-project plan options on 2026-10-06. Current CSV lacks verified project/entity binding, requires manual new-row keys and has no plan isolation. Preserve legacy imports and role authorization. Use project-level entities; do not create real users or populate live data."
definition-of-done: Bound minimal CSV round-trips exact text and stable keys; blank new keys are generated safely; wrong project/entities and incompatible plan links are refused; Shared plus selected plan has independently calculated critical paths; UI download/upload and plan selection verified; full tests and independent review pass.
tags: []
blocked-by: []
related: []
commits: []
created-at: 2026-10-06T18:38:12Z
updated-at: 2026-10-07T13:56:29Z
updated-by: Codex
outcome-what: "Added project-bound nine-column CSV download-fill-upload, logged spare task keys, Shared/alternative plan filtering and independent critical paths."
outcome-why: Owners need one simple file per project without manual project IDs or repeated uploads.
outcome-resolves: "Stable task updates, exact project/entity binding and compatible complete graphs verified by 739 tests, browser checks and independent review."
review-summary: "Independent read-only review passed: project-bound minimal CSV, stable logged spare keys, Shared and alternative critical paths, complete graph checks including partial imports and unkeyed tasks, compatible legacy CSV parsing."
review-gaps: "none within the approved feature scope; real workbook population, Microsoft Excel desktop saving and hosted deployment remain unverified."
review-verdict: "Independent source review passed, sixteen focused tests and HTTP role test passed independently; parent final suite Ran 739 tests in 812.249s OK (skipped=1), eleven guard-removal checks and desktop/phone Chrome workflow passed. Ready for Aly acceptance within this feature scope."
review-check: "1. Run .venv\\Scripts\\python.exe tests\\run.py and expect OK. 2. Open an existing project and click Import workplan. 3. Download its CSV and fill spare keyed task rows, keeping project metadata. 4. Upload, preview and confirm; expect the tasks without duplicates. 5. Choose a named plan in Timeline; expect Shared plus that plan and its critical path. 6. Re-download for later edits."
---

# Project plan options and minimal bound workplan CSV

## Definition of Done

- [x] Bound minimal CSV round-trips exact text and stable keys; blank new keys are generated safely; wrong project/entities and incompatible plan links are refused; Shared plus selected plan has independently calculated critical paths; UI download/upload and plan selection verified; full tests and independent review pass.
  proof: tests/test_workplan.py:16 tests OK; test_import.ImportHttpTests.test_project_bound_workplan_download_role_matrix OK; tests/run.py Ran 739 tests in 812.249s OK (skipped=1); independent workplan_review passed; synthetic Chrome download-fill-upload-preview-commit and desktop/phone plan selection passed; eleven guard-removal regressions failed as expected.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-10-06 19:19 · Codex** — Implemented project-bound nine-column CSV, separately calculated Shared/alternative critical paths, native/import graph guards and logged spare WP key reservations. Independent read-only review passed after correcting partial-import retained plans, unkeyed nodes and CSV serialization regressions. Sixteen focused tests and HTTP role test passed; synthetic Chrome workflow passed desktop/phone. Final full suite running. Real workbook population and hosted deployment remain unverified.
- **2026-10-07 02:13 · Codex** — Aly Jafferani explicitly accepted W6ZSGA in this chat on 2026-10-07: W6ZSGA signed off. Acceptance applies to feature commit 606bf5423f71f001fad53102914918a3cf0886e8, verified by 739 tests OK (skipped=1). Agent has recorded the decision without leaving the human signoff lane. Real sample population, Microsoft Excel desktop saving and hosted deployment remain unverified.
- **2026-10-07 13:56 · Codex** — 2026-10-07: Prepared separate private Rupani owner CSV against verified real project/entity IDs; 239 source tasks and 11 spare Astra-issued IDs, nine columns. Five ordinary template downloads reserve 250 keys with a pre-reservation database backup. Dates/assignees/predecessors blank pending owner decisions. Isolated import and identical replay pass; wrong bindings refused; live project remains 0 tasks. No application source changes or owner acceptance inferred. Browser control and Excel desktop operation remain unverified. Private artifacts kept outside Git.
