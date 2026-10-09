---
id: 01M4BY5B6YP69JMFMVCQJM7CFP
title: Simple project-bound Excel workplans and task-row timeline scheduling
status: in-progress
ready: true
creator: Codex
assignee: Codex
goal: "Owners download one readable XLSX, fill tasks and relationships, upload with stable project/entity binding, and schedule task rows visually with automatic critical-path recalculation."
context: "Aly rejected the nine-column CSV as unusable for basic Excel users and selected XLSX. IDs must be maintained by Astra, not typed. Excel must not offer Decide in Astra. Overlaps do not imply dependencies. Existing UI drags bars but lacks task-row timeline drops. Aly approved proceeding on 2026-10-08. Preserve standard-library runtime, owner authorization and existing CSV compatibility. Live Rupani tasks remain untouched during development."
definition-of-done: Readable XLSX with managed IDs and owner/task dropdowns; project/entity identity verified on preview and commit; explicit concurrent/after relationships resolve unambiguously and conflicts reported; task-row date and relationship drops preserve duration and use server authorization/revision/cycle checks; critical path recalculates and vertical ordering persists; service HTTP and UI checks plus independent review recorded; full suite before push with LF hygiene and owner signoff only.
tags: []
blocked-by: []
related: []
commits: []
created-at: 2026-10-07T19:41:33Z
updated-at: 2026-10-09T18:28:53Z
updated-by: Codex
claimed-by: X1CarbonPC-32528
claimed-at: 2026-10-07T19:44:46Z
outcome-what: Plan recorded
outcome-why: Aly approved XLSX and task-row timeline drops; existing interfaces inspected
outcome-resolves: Implementation boundaries specified
---

# Simple project-bound Excel workplans and task-row timeline scheduling

- [x] Add standard-library XLSX workbook with four core fields, grouped optional relationships, hidden stable IDs and project/entity marker; resolve named selections in existing importer.
  proof: src/astra/workplan_excel.py; tests/test_owner_excel_timeline.py OwnerExcelTests; private isolated sample239/replay239
- [x] Add governed task-row date/relation/order drops using atomic service validation and existing scheduling authority; refresh critical path.
  proof: src/astra/service.py timeline_drop; tests/test_owner_excel_timeline.py TimelineTaskDropTests; critical path and reorder persistence regressions
- [ ] Exercise parser/service/HTTP roles and guard-removal regressions, isolated browser scenarios and independent review; run full suite and scoped LF-safe push.

## Definition of Done

- [ ] Readable XLSX with managed IDs and owner/task dropdowns; project/entity identity verified on preview and commit; explicit concurrent/after relationships resolve unambiguously and conflicts reported; task-row date and relationship drops preserve duration and use server authorization/revision/cycle checks; critical path recalculates and vertical ordering persists; service HTTP and UI checks plus independent review recorded; full suite before push with LF hygiene and owner signoff only.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-10-07 19:46 · Codex** — Inspection: current Gantt implements bar move/resize only; Kanban has its own card drag. Named Excel references must reject ambiguous/renamed targets. Task row ordering will be recorded per project, separate from dependencies. Excel code must use existing standard-library OOXML facilities; artifact-tool is authoring/verification only, never a runtime dependency. No inferred links from date overlap.
- **2026-10-08 02:26 · Codex** — Excel owner workplan and explicit task-row timeline actions implemented. Seventeen focused tests pass; eight disposable guard removals fail their regressions. Private source sample creates 239 tasks in an isolated copy and repeat upload changes none; live tasks remain untouched. Full suite rerun and independent review are running. Browser control fails before initialization, so browser acceptance is unverified.
- **2026-10-08 02:37 · Codex** — Independent review found and corrected accidental Unicode changes and missing Excel concurrent target/self/plan/dependency-chain checks. Nineteen focused tests pass; ten disposable guard removals fail. Core and optional sample previews inspected. Final full suite after review corrections is running. Codex browser retry requested by Aly still exits before reading UI; browser verification remains unverified.
- **2026-10-08 02:41 · Codex** — Final source regression result: Ran 764 tests in 388.663s, OK (skipped=1). Focused19 OK and ten guard-removal regressions verified. Source LF/diff check clean. Localroot HTTP200 verified; browser tool still exits before inspection. Final independent code verdict pending; browser and owner acceptance unverified. Do not mark ready or infer acceptance.
- **2026-10-08 02:46 · Codex** — Browser tool discovery recovered after explicit CUA kernel reset. Inventory exposes Chrome, but requested Codex browser create returns Browser is not available: iab. Asked Aly to open local8765 in this chat right-hand browser. Current browser checks still unverified; do not conflate recovered tool discovery with successful UI verification.
- **2026-10-09 18:19 · Aly Jafferani** — 2026-10-09 continuation: recovered terminal execution and independent review. Review proved raw-dropdown versus normalized-parser whitespace mismatch; new grouping/dependency regression failed before correction. Shared reference normalization now passes all 20 focused tests; independent static review passed. Corrected-code full suite running with ignored log Temp/jm7cfp-full-suite-20261009.txt. Browser and desktop Excel verification remain unverified per Aly instruction to proceed apart from Chrome; no owner acceptance, deployment or live-task import inferred. Full requirement/evidence record: docs/handoff/JM7CFP_VERIFICATION_2026-10-09.md.
- **2026-10-09 18:28 · Codex** — Correction: the previous 2026-10-09 continuation progress note was generated by Codex while the installed CLI inherited the Aly Jafferani identity; it was not an owner decision or acceptance. Final corrected-code verification: Ran 765 tests in 557.349s, OK (skipped=1), exit 0; focused20 OK; independent static review of the whitespace repair and root Temp ignore passed. The saved log confirms the attachment-symlink environment skip. Browser and desktop Excel checks remain unverified, owner acceptance pending, ticket stays in-progress. No commit, push, deployment, server restart or live-task import. Evidence: docs/handoff/JM7CFP_VERIFICATION_2026-10-09.md.
