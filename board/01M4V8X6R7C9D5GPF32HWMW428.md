---
id: 01M4V8X6R7C9D5GPF32HWMW428
title: Repair critical frontend integrity and usability findings
status: human
ready: true
creator: Codex
assignee: Codex
goal: "Fix the nine confirmed critical-review findings and related duplicate-name, colour-token and navigation usability debt without changing approved authorization or real data."
context: "Critical review 26ZF8D reproduced wrong-task saves and silent owner loss, plus seven usability/recovery failures. Aly authorized fixing all findings and chose direct project-task creation named Add a task on October14. Repair all nine and related picker/token/navigation debt; preserve existing acceptance lanes and hosted launch gates."
definition-of-done: Regression tests fail before fixes and pass after; task identity and owners survive delayed/failed requests; all nine findings and duplicate-name/token/navigation debt addressed with actual browser evidence; service guards unchanged or affected-role tests added; full suite and independent diff review pass; handoff records remaining decision/verification limits and Aly alone accepts.
tags: []
blocked-by: []
related: []
commits: []
created-at: 2026-10-13T18:37:57Z
updated-at: 2026-10-22T16:32:46Z
updated-by: Claude
claimed-by: X1CarbonPC-20408
claimed-at: 2026-10-13T18:45:11Z
outcome-what: Repaired F1-F9 and related picker/token/navigation gaps; direct Add a task flow and final evidence handoff prepared.
outcome-why: Aly authorized all fixes and selected the launch task-creation behavior. Independent code and documentation reviews passed.
outcome-resolves: "Immutable task saves, preserved owners, recoverable status, named accessible workflows;849 full tests OK(skip1), bounded browser persistence evidence. Owner acceptance and deployment remain separate."
review-summary: Independent read-only source and final handoff review PASS; adjacent gaps repaired and final delta rechecked.
review-gaps: "Physical devices, assistive technology, exhaustive UX and hosted launch checks remain unverified."
review-verdict: pass
review-check: Independent 17 frontend integrity tests and syntax check passed; parent full849 OK(skip1) and synthetic Chrome/SQLite evidence documented.
question: Please review FRONTEND_REPAIRS_2026-10-14.md and accept WMW428 if the bounded repairs meet your requirements; this does not authorize deployment.
---

# Repair critical frontend integrity and usability findings

## Definition of Done

- [x] Regression tests fail before fixes and pass after; task identity and owners survive delayed/failed requests; all nine findings and duplicate-name/token/navigation debt addressed with actual browser evidence; service guards unchanged or affected-role tests added; full suite and independent diff review pass; handoff records remaining decision/verification limits and Aly alone accepts.
  proof: tests/test_frontend_integrity.py; docs/handoff/FRONTEND_REPAIRS_2026-10-14.md:13 original red,17 green,221 web, five guard-removal checks, synthetic Chrome/SQLite proof; full849 in583.910s OK(skip1); independent source/document PASS. Aly accepts only.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Turn recorded failures into deterministic current-code regressions, then repair immutable task identity and safe assignee loading.
- [x] Repair history, Cancel, role-aware capture, accessible labels, named templates, search, unread recovery, duplicate labels and token/navigation debt.
- [x] Complete focused, mutation, browser, full and independent checks; prepare the scoped Git publication and handoff; hand to Aly for acceptance. Verify and report final SHA after publication.

## Progress
- **2026-10-14 05:02 · Codex** — All nine review findings and related debt are repaired. Initial13 red and intermediate web187 failures are retained in the receipt; final17/221 and full849 OK(skip1), five guard removals detected, independent source and document PASS. Aly selected Add a task; private drafts remain future scope. Only synthetic records changed. Existing human/signoff/Done untouched; final scoped publication SHA must be verified after push.
- **2026-10-14 06:09 · Codex** — Aly accepted WMW428 in chat on2026-10-14 by saying Ticket accepted after the repair handoff and published SHA4d92bbddac8305b78e3ec26dde411219c57b230c. This records owner acceptance of the bounded repair scope; do not request repeat acceptance. The human lane is preserved because only Aly may close it. Other tickets, hosting and deployment remain separate.
- **2026-10-22 16:17 · Claude** — 2026-10-22 close review: Claude and Codex both recommend closing (Codex read-only review of a per-ticket packet). Cited tests and documents exist at bdbf795 and the full suite passes (1112 OK, skipped=1 at 6f61d74). Waiting for Aly's board move to done.
- **2026-10-22 16:32 · Claude** — 2026-10-22 tested before closing (Aly: do not close on his okay alone). Claude, temp copy of bdbf795: focused tests pass; guard removal: removing formnovalidate from the 11 Cancel buttons fails the F4 test; restored copy passes. Codex, its own temp copy: PASS; bypassing the stale-detail check fails a test; probe: newer owner lookup survives an older failure. Both recommend closing.
