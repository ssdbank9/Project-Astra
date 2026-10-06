---
id: 01M480VB5XRXHVXX5WQN7E1K4B
title: Finish Phase A3 literal search and CSV whitespace guards
status: backlog
ready: true
creator: Aly Jafferani
assignee: Codex
goal: Finish the two remaining Y3WC71 review fixes in Phase A3.
context: "web._csv_cell checks only the first stored character, so leading spaces hide formula prefixes. service.search uses unescaped LIKE terms, so percent and underscore match unrelated records. NEXT_STEPS.md Phase A3 item 3 explicitly requests both fixes; Aly authorized continued local development. Preserve CSV stored whitespace and project visibility."
definition-of-done: "Whitespace-prefixed formulas are escaped without trimming stored export text; percent, underscore and the escape character search literally for all authorized roles; focused regressions fail on old code and pass on fixed code; independent review and diff hygiene complete."
tags: []
blocked-by: []
related: []
commits: []
created-at: 2026-10-06T07:11:34Z
updated-at: 2026-10-06T07:11:34Z
---

# Finish Phase A3 literal search and CSV whitespace guards

## Definition of Done

- [ ] Whitespace-prefixed formulas are escaped without trimming stored export text; percent, underscore and the escape character search literally for all authorized roles; focused regressions fail on old code and pass on fixed code; independent review and diff hygiene complete.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

