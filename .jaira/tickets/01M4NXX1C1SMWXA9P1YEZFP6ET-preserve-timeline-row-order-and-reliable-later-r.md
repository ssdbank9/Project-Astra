---
id: 01M4NXX1C1SMWXA9P1YEZFP6ET
title: Preserve timeline row order and reliable later-row dragging
status: human
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
updated-at: 2026-10-12T07:52:55Z
updated-by: Codex
question: "Aly accepted 2026-10-12; awaiting the human-only board transition to done."
outcome-what: Preserved complete visible timeline order and made later-row drop targets stable. Backend and actual-function regressions pass; all desktop Chrome drop modes and filtered-parent reorder persist.
outcome-why: First reorder changed unrelated rows; in-flow drop controls cancelled later-row drag starts.
outcome-resolves: Independent review and Chrome cases passed; 24 focused and 770 full tests OK. Repair published at bf4ea3eaf5d07ef7f7efbfc80e458e88d8871457. Aly accepted on 2026-10-12. Touch/narrow-screen and running owner server version unverified.
---

# Preserve timeline row order and reliable later-row dragging

## Definition of Done

- [x] First and subsequent Above/Below moves preserve all unrelated visible row positions, including filtered/grouped cases; later-row date and relationship dragging works in Chrome without moving targets; cancellation and persistence work; regression tests fail on original behavior and pass after correction; authorization and conflict guards remain; focused/full tests, independent review, browser evidence and scoped publication receipt recorded.
  proof: docs/handoff/TIMELINE_DRAG_REPAIR_2026-10-12.md; published bf4ea3eaf5d07ef7f7efbfc80e458e88d8871457; 770 tests OK; Chrome and independent review pass; Aly accepted 2026-10-12

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
- [x] Verify actual later-row date/order/relationship drops, guards, full suite and independent review; publish scoped receipt.
  proof: TIMELINE_DRAG_REPAIR_2026-10-12.md; final 770 tests OK; independent review pass

## Progress
- **2026-10-12 07:31 · Codex** — Independent implementation review passed; parent and reviewer focused suite Ran 24 tests OK. Final full suite Ran 770 tests in 508.309s OK (skipped=1), exit 0. Chrome verified all later-row modes, stable geometry, cancel/reload and additional filtered-parent actual reorder. App Owner acceptance pending. No owner data or deployment changed.
- **2026-10-12 07:50 · Codex** — App Owner Aly explicitly stated I accept ZFP6ET in this chat on 2026-10-12. Repair published and origin verified at bf4ea3eaf5d07ef7f7efbfc80e458e88d8871457; full suite Ran 770 tests in 508.309s OK (skipped=1). This records the human decision, not agent acceptance. Ticket stays human until Aly performs the human-only board transition. No deployment authorized; touch/narrow-screen and running owner server version remain unverified.
