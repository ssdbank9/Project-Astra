---
id: 01M4984M493GAEKAN10HW6ZSGA
title: Project plan options and minimal bound workplan CSV
status: in-progress
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
updated-at: 2026-10-06T19:25:40Z
updated-by: Codex
outcome-what: Implement minimal project-bound workplan CSV and single-project Shared/alternative plans.
outcome-why: Aly authorized the download-fill-upload feature.
outcome-resolves: "Add regression coverage, independent review and browser verification."
review-summary: "Independent read-only review passed: project-bound minimal CSV, stable logged spare keys, Shared and alternative critical paths, complete graph checks including partial imports and unkeyed tasks, compatible legacy CSV parsing."
review-gaps: "none within the approved feature scope; real workbook population, Microsoft Excel desktop saving and hosted deployment remain unverified."
review-verdict: Source review passed; final full-suite verification is being completed before owner signoff.
review-check: "1. Run .venv\\Scripts\\python.exe tests\\run.py and expect OK. 2. Open an existing project and click Import workplan. 3. Download its CSV and fill spare keyed task rows, keeping project metadata. 4. Upload, preview and confirm; expect the tasks without duplicates. 5. Choose a named plan in Timeline; expect Shared plus that plan and its critical path. 6. Re-download for later edits."
---

# Project plan options and minimal bound workplan CSV

## Definition of Done

- [ ] Bound minimal CSV round-trips exact text and stable keys; blank new keys are generated safely; wrong project/entities and incompatible plan links are refused; Shared plus selected plan has independently calculated critical paths; UI download/upload and plan selection verified; full tests and independent review pass.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-10-06 19:19 · Codex** — Implemented project-bound nine-column CSV, separately calculated Shared/alternative critical paths, native/import graph guards and logged spare WP key reservations. Independent read-only review passed after correcting partial-import retained plans, unkeyed nodes and CSV serialization regressions. Sixteen focused tests and HTTP role test passed; synthetic Chrome workflow passed desktop/phone. Final full suite running. Real workbook population and hosted deployment remain unverified.
