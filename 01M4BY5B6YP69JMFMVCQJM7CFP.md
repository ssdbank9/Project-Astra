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
updated-at: 2026-10-08T02:26:23Z
updated-by: Codex
claimed-by: X1CarbonPC-32528
claimed-at: 2026-10-07T19:44:46Z
outcome-what: Plan recorded
outcome-why: Aly approved XLSX and task-row timeline drops; existing interfaces inspected
outcome-resolves: Implementation boundaries specified
---

# Simple project-bound Excel workplans and task-row timeline scheduling

- [ ] Add standard-library XLSX workbook with four core fields, grouped optional relationships, hidden stable IDs and project/entity marker; resolve named selections in existing importer.
- [ ] Add governed task-row date/relation/order drops using atomic service validation and existing scheduling authority; refresh critical path.
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
