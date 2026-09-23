---
id: 01M37E9T2RBY6Q48K41V9MK29X
title: "Maintainability: split AstraService.update_task into policy, validation and persistence helpers"
status: backlog
ready: true
creator: Claude
assignee: Claude
goal: "update_task reads as a short sequence of named steps (lifecycle policy, field validation, request routing, conditional write and events) with no behaviour change."
context: |-
  Maintainability, not a demonstrated defect.
  src/astra/service.py update_task (~616-734, about 120 lines) mixes payload merge, lifecycle policy (governed, locked-source, reopen-only statuses), closed-task immutability, reason and date validation, assignee checks, Manager request routing, the revision-checked UPDATE and event and request reconciliation.
  Each remediation round (SRFCZD R1-R6, T8WHJR) added another branch here; ordering matters (for example the R6 refusal must run before a request is filed).
  Suggested in Codex's handoff CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md section 7.3 item 5; re-listed by the 2026-09-23 adversarial review of codex/migration-safety-remediation.
  Do not mix into a correctness fix; land separately with the suite unchanged.
definition-of-done: update_task delegates to small private helpers with the same check order; error messages and HTTP statuses unchanged
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:31:43Z
updated-at: 2026-09-23T15:32:18Z
updated-by: Claude
---

# Maintainability: split AstraService.update_task into policy, validation and persistence helpers

## Definition of Done

- [ ] update_task delegates to small private helpers with the same check order; error messages and HTTP statuses unchanged
- [ ] No test file changes other than additions; full suite green with the same count plus any new tests

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

