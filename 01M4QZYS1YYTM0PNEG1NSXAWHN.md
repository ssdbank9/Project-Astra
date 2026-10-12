---
id: 01M4QZYS1YYTM0PNEG1NSXAWHN
title: Linked task movement and automatic project schedule
status: human
ready: true
creator: Codex
assignee: Codex
goal: "Task movement updates dependencies, affected task dates, critical paths and project scheduled dates through one reviewable atomic change."
context: "Aly requested automatic dependencies and overall project dates after ZFP6ET. On 2026-10-12 Aly approved Above as predecessor, Below and After as successor, and Concurrent as parallel, followed by affected-chain scheduling with duration preservation and one preview. Aly requested both deadline choices: always calculate scheduled start/finish, retain agreed deadline by default, allow explicit deadline revision in the preview. Owners and accepted baselines stay unchanged. Existing Above/Below only orders rows; date moves do not shift successors. Use synthetic data and maintain project/plan, role, lock and stale-snapshot guards."
definition-of-done: "All drag modes show complete dependency/date/project forecast preview and apply atomically; affected successors preserve duration and respect all predecessors; project forecast dates refresh and explicit deadline revision preserves baselines; owners stay assigned; cycles, stale snapshots, roles, locks, closed tasks and alternative plans tested; meaningful regressions, Chrome verification, full suite and independent review pass; handoff and scoped publication recorded."
tags:
  - astra
blocked-by: []
related:
  - 01M4NXX1C1SMWXA9P1YEZFP6ET
commits: []
created-at: 2026-10-12T12:03:48Z
updated-at: 2026-10-12T16:49:51Z
updated-by: Codex
question: Please accept SXAWHN after reviewing the linked scheduling preview and publication receipt.
outcome-what: "Task movement previews and atomically saves dependencies, affected task dates, sibling order and optional agreed deadline. Project scheduled dates refresh separately from agreed dates and baselines."
outcome-why: Aly requested automatic linked scheduling after confirming the earlier ordering repair; old task movement did not reschedule successors or project bounds.
outcome-resolves: "17 focused tests and six-role HTTP matrix pass; full 787 tests OK; independent code and handoff review pass; actual Chrome modes, deadline choices, owner preservation, cancellation and reload verified. Touch, running owner server and hosting unverified. Scoped publication receipt follows."
---

# Linked task movement and automatic project schedule

## Definition of Done

- [x] All drag modes show complete dependency/date/project forecast preview and apply atomically; affected successors preserve duration and respect all predecessors; project forecast dates refresh and explicit deadline revision preserves baselines; owners stay assigned; cycles, stale snapshots, roles, locks, closed tasks and alternative plans tested; meaningful regressions, Chrome verification, full suite and independent review pass; handoff and scoped publication recorded.
  proof: AUTOMATIC_TIMELINE_SCHEDULING_2026-10-12.md; d93139db7fa711daec3209a389490f507083552b; 17 focused/787 full tests OK; independent and Chrome verification

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Build a pure affected-chain scheduler and calculated per-plan project forecasts.
  proof: timeline_schedule.py; affected-chain, gap and alternative-forecast tests
- [x] Add read-only preview and atomic snapshot-checked apply using existing service authorization, history and locks.
  proof: 17 focused tests incl HTTP role matrix; fingerprint guard removal fails regression
- [x] Show full change preview, dependency meaning and explicit deadline revision in the plain JS timeline.
  proof: Chrome Below/Above/date/Concurrent and accessible After; both deadline choices
- [x] Verify branching and role/refusal regressions, Chrome, full suite and independent review; document and publish.
  proof: Published d93139db7fa711daec3209a389490f507083552b; 787 tests OK; Chrome and independent review pass

## Progress
- **2026-10-12 12:26 · Codex** — Read-only preview and atomic apply now cover full-project scheduled bounds, separate alternative forecasts and optional owner deadline revision. Core graph/service tests pass (17 incl HTTP role matrix). Independent review caught source task ID missing from fingerprint; dedicated red regression and guard mutation now prove fix. Added bounds helper shadowed a local list once; corrected. Chrome Below saved link reversal, changed task dates and scheduled finish while retaining agreed deadline. Browser finishing Above+deadline, date-chain, concurrent, cancel and reload. Original full suite running; final UI readability pass will need final checks.
- **2026-10-12 13:17 · Codex** — Published normally and origin confirmed at d93139db7fa711daec3209a389490f507083552b. Full suite Ran 787 tests in 561.770s OK (skipped=1); existing symlink-unavailable skip. Independent final code/static/handoff review and actual desktop Chrome modes, both deadline choices, owner preservation, Cancel/reload pass. Source-ID fingerprint regression fails with binding removed. Global mistakes log synchronized. Aly implementation acceptance remains pending; touch/mobile, usual running server and hosted operation unverified.
- **2026-10-12 16:49 · Codex** — App Owner Aly explicitly stated I accept SXAWHN in this chat on 2026-10-12. This records the human decision, not agent acceptance. Published repair d93139db7fa711daec3209a389490f507083552b; full 787 tests OK (skipped=1), independent and desktop Chrome checks pass. Ticket remains human until Aly performs the human-only done transition. No deployment authorized; mobile gestures, usual running server and hosting remain unverified.
