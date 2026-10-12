---
id: 01M4QZYS1YYTM0PNEG1NSXAWHN
title: Linked task movement and automatic project schedule
status: backlog
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
updated-at: 2026-10-12T12:05:20Z
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

## Progress

