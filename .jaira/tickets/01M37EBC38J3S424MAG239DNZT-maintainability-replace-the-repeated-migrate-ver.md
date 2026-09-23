---
id: 01M37EBC38J3S424MAG239DNZT
title: "Maintainability: replace the repeated migrate() version blocks with a step registry"
status: backlog
ready: true
creator: Claude
assignee: Claude
goal: "Migration steps are declared once in an ordered registry and run by one loop that owns the transaction, the user_version bump and fault handling."
context: |-
  Maintainability, not a demonstrated defect.
  src/astra/db.py migrate() (~74-445) is fourteen hand-written 'if version < N: with transaction(connection): ... PRAGMA user_version = N' blocks; v13 and v14 are separate functions with their own guards.
  Every step repeats the same control flow, so a step can drift (for example a user_version bump outside its transaction) and per-step fault injection needs per-step test code.
  Suggested in Codex's handoff CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md section 7.3 item 1; re-listed by the 2026-09-23 adversarial review of codex/migration-safety-remediation.
  Do after the per-version migration fault tests ticket, so those tests guard the refactor. Keep the resulting schema byte-for-byte equal to today's (catalog comparison).
definition-of-done: "migrate() runs steps from one ordered registry; each step's statements and user_version bump share one transaction by construction"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:32:34Z
updated-at: 2026-09-23T15:33:08Z
updated-by: Claude
---

# Maintainability: replace the repeated migrate() version blocks with a step registry

## Definition of Done

- [ ] migrate() runs steps from one ordered registry; each step's statements and user_version bump share one transaction by construction
- [ ] Fresh and legacy-upgrade catalog equivalence tests and all migration fault tests pass unchanged; full suite green

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

