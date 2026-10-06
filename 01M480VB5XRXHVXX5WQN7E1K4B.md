---
id: 01M480VB5XRXHVXX5WQN7E1K4B
title: Finish Phase A3 literal search and CSV whitespace guards
status: review
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: Finish the two remaining Y3WC71 review fixes in Phase A3.
context: "web._csv_cell checks only the first stored character, so leading spaces hide formula prefixes. service.search uses unescaped LIKE terms, so percent and underscore match unrelated records. NEXT_STEPS.md Phase A3 item 3 explicitly requests both fixes; Aly authorized continued local development. Preserve CSV stored whitespace and project visibility."
definition-of-done: "Whitespace-prefixed formulas are escaped without trimming stored export text; percent, underscore and the escape character search literally for all authorized roles; focused regressions fail on old code and pass on fixed code; independent review and diff hygiene complete."
tags: []
blocked-by: []
related: []
commits: []
created-at: 2026-10-06T07:11:34Z
updated-at: 2026-10-06T07:32:38Z
updated-by: Aly Jafferani
outcome-what: Escape literal LIKE search characters and detect whitespace-prefixed CSV formulas while preserving stored text.
outcome-why: Resolve NEXT_STEPS Phase A3 item 3 confirmed defects.
outcome-resolves: "Regression failures reproduced on old code; fixed focused tests pass; independent read-only review passed."
review-summary: Independent a3_review inspected the four source and test diffs without editing. No confirmed defect or blocking gap.
review-verdict: Pass
review-gaps: Actual spreadsheet interpretation unverified. Optional description-only and inaccessible literal-match fixtures were not required; existing scope regression passes.
review-check: "Old-code red: 11 failing cases. Fixed focused run: Ran 4 tests, OK. Full suite pending. CSV whitespace retained; all LIKE predicates escaped; membership scope preserved."
---

# Finish Phase A3 literal search and CSV whitespace guards

## Definition of Done

- [x] Whitespace-prefixed formulas are escaped without trimming stored export text; percent, underscore and the escape character search literally for all authorized roles; focused regressions fail on old code and pass on fixed code; independent review and diff hygiene complete.
  proof: Old-code regressions failed 11 cases; four focused tests pass. Independent a3_review found no blocking defects. git diff --check passes.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-10-06 07:19 · Aly Jafferani** — Aly Jafferani took this ticket over from Codex
