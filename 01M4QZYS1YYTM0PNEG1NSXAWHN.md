---
id: 01M4QZYS1YYTM0PNEG1NSXAWHN
title: Linked task movement and automatic project schedule
status: in-progress
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
updated-at: 2026-10-12T12:50:20Z
updated-by: Codex
---

# Linked task movement and automatic project schedule

## Definition of Done

- [ ] All drag modes show complete dependency/date/project forecast preview and apply atomically; affected successors preserve duration and respect all predecessors; project forecast dates refresh and explicit deadline revision preserves baselines; owners stay assigned; cycles, stale snapshots, roles, locks, closed tasks and alternative plans tested; meaningful regressions, Chrome verification, full suite and independent review pass; handoff and scoped publication recorded.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Build a pure affected-chain scheduler and calculated per-plan project forecasts.
  proof: timeline_schedule.py; affected-chain, gap and alternative-forecast tests
- [ ] Add read-only preview and atomic snapshot-checked apply using existing service authorization, history and locks.
- [ ] Show full change preview, dependency meaning and explicit deadline revision in the plain JS timeline.
- [ ] Verify branching and role/refusal regressions, Chrome, full suite and independent review; document and publish.

## Progress
- **2026-10-12 12:26 · Codex** — Read-only preview and atomic apply now cover full-project scheduled bounds, separate alternative forecasts and optional owner deadline revision. Core graph/service tests pass (17 incl HTTP role matrix). Independent review caught source task ID missing from fingerprint; dedicated red regression and guard mutation now prove fix. Added bounds helper shadowed a local list once; corrected. Chrome Below saved link reversal, changed task dates and scheduled finish while retaining agreed deadline. Browser finishing Above+deadline, date-chain, concurrent, cancel and reload. Original full suite running; final UI readability pass will need final checks.
