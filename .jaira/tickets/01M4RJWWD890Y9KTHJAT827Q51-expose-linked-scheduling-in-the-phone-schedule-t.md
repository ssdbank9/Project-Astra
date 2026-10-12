---
id: 01M4RJWWD890Y9KTHJAT827Q51
title: Expose linked scheduling in the phone schedule table
status: human
ready: true
creator: Codex
assignee: Codex
goal: Users can open the complete linked scheduling preview from schedule-table rows on small screens and desktop List views.
context: "Launch QA after SXAWHN acceptance found zero Move task controls at 390px. Astra switches from Gantt to the schedule table below its breakpoint, but only Gantt rows expose the task movement handle and its click handler. The same synthetic owner can manage the project at desktop width. Verify render omission versus hidden CSS or permissions, then add the accessible action to table rows and reuse the existing preview flow. Do not change owners, scheduling rules, real data or deployment."
definition-of-done: "Regression fails before fix and passes after; eligible task and subtask table rows expose one accessible Move task action; forbidden/closed project controls hidden; clicks reach the same linked preview; browser checks at 390px, 320px, desktop List and zoom plus cancel/save/reload pass; full suite and independent review pass; scoped handoff and publication recorded."
tags:
  - astra
blocked-by: []
related:
  - 01M4QZYS1YYTM0PNEG1NSXAWHN
commits: []
created-at: 2026-10-12T17:34:49Z
updated-at: 2026-10-12T18:25:12Z
updated-by: Codex
question: 827Q51 functional repair is published for owner review; actual 200 percent browser zoom remains unverified. No laptop action requested while Aly is away.
outcome-what: "Added one eligible Move task action per table task/step, shared the linked preview handler and captured filtered table order."
outcome-why: Small screens and List views omitted controls; the new table entry point exposed a Gantt-only order snapshot.
outcome-resolves: "Responsive save/cancel/reload, hidden-parent ordering, four focused tests, full 790-test suite and independent review pass. Actual browser zoom is unverified; combined DOD stays unticked."
---

# Expose linked scheduling in the phone schedule table

## Definition of Done

- [ ] Regression fails before fix and passes after; eligible task and subtask table rows expose one accessible Move task action; forbidden/closed project controls hidden; clicks reach the same linked preview; browser checks at 390px, 320px, desktop List and zoom plus cancel/save/reload pass; full suite and independent review pass; scoped handoff and publication recorded.
  proof: docs/handoff/TABLE_SCHEDULING_2026-10-12.md:7: focused four tests and independent review pass; final Ran 790 tests in 602.540s OK skipped1; responsive/table save/reload passes. Actual 200 percent browser zoom remains unverified, so criterion is not ticked.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Confirm omitted table rendering with the same owner and a failing actual-function regression.
  proof: tests/test_timeline_table_actions.py:34; pre-fix two failures; same owner browser zero table controls versus four Gantt controls.
- [x] Add eligible task/subtask table actions and share the existing accessible movement handler.
  proof: src/astra/static/app.js:306; shared renderer/helper/handler and table order capture; focused four tests OK, independent review passes.
- [ ] Verify small widths, desktop List, zoom and keyboard preview/save/cancel/reload; run full suite and independent review.

## Progress
- **2026-10-12 18:19 · Codex** — Same-account controls confirmed missing in 390px and desktop List. Actual-function regressions failed before fix, then passed; independent review caught filtered-table order omission, now corrected and regression-proven. Actual Chrome small-width keyboard save/cancel/reload and filtered-parent Above pass. Actual 200 percent zoom is unverified: shortcuts did not alter width/DPR; reduced viewport is separate evidence. Final full suite rerun includes third regression; earlier 789-test run OK skipped1 is not the final receipt.
