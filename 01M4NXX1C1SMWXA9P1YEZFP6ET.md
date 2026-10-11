---
id: 01M4NXX1C1SMWXA9P1YEZFP6ET
title: Preserve timeline row order and reliable later-row dragging
status: todo
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
updated-at: 2026-10-11T17:05:46Z
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

## Progress

