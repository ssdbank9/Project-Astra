---
id: 01M4NXX1C1SMWXA9P1YEZFP6ET
title: Preserve timeline row order and reliable later-row dragging
status: in-progress
ready: true
creator: Aly Jafferani
assignee: Codex
goal: Move only the selected timeline task and keep drag targets stable for every row.
context: "Chrome verification on 2026-10-11 showed the first Below drop also moved unrelated rows. Service initializes order by creation while the visible timeline uses task-list order. Later-row drags emitted dragstart then immediate dragend twice; exposing drop controls moves rows. Diagnose the cancellation before claiming it fixed. Use disposable data; preserve owners, dates, dependencies, grouping and revision guards."
definition-of-done: "First and subsequent Above/Below moves preserve all unrelated visible row positions, including filtered/grouped cases; later-row date and relationship dragging works in Chrome without moving targets; cancellation and persistence work; regression tests fail on original behavior and pass after correction; authorization and conflict guards remain; focused/full tests, independent review, browser evidence and scoped publication receipt recorded."
tags: []
blocked-by: []
related:
  - 01M4BY5B6YP69JMFMVCQJM7CFP
commits: []
created-at: 2026-10-11T16:49:25Z
updated-at: 2026-10-12T07:31:30Z
updated-by: Codex
---

# Preserve timeline row order and reliable later-row dragging

## Definition of Done

- [ ] First and subsequent Above/Below moves preserve all unrelated visible row positions, including filtered/grouped cases; later-row date and relationship dragging works in Chrome without moving targets; cancellation and persistence work; regression tests fail on original behavior and pass after correction; authorization and conflict guards remain; focused/full tests, independent review, browser evidence and scoped publication receipt recorded.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Reproduce first reorder and later-row cancellation with failing regression and Chrome probes.
  proof: tests/test_owner_excel_timeline.py and TIMELINE_DRAG_VERIFICATION_2026-10-11.md
- [x] Preserve full unfiltered project order on first reorder; validate IDs and move siblings only.
  proof: timelineTaskOrder and AstraService.timeline_drop; 24 focused tests OK
- [x] Show relationship drop controls as stable timeline overlays without changing row geometry.
  proof: Chrome unchanged handle/timeline rectangles; all later-row drops saved
- [ ] Verify actual later-row date/order/relationship drops, guards, full suite and independent review; publish scoped receipt.

## Progress
- **2026-10-12 07:31 · Codex** — Independent implementation review passed; parent and reviewer focused suite Ran 24 tests OK. Final full suite Ran 770 tests in 508.309s OK (skipped=1), exit 0. Chrome verified all later-row modes, stable geometry, cancel/reload and additional filtered-parent actual reorder. App Owner acceptance pending. No owner data or deployment changed.
