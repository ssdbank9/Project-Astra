---
id: 01M32CQTG5CPFZMTSPPXWT5TCK
title: Chairman can be assigned as Task Owner without project membership and then submit
status: backlog
ready: true
creator: Claude
assignee: Claude
goal: "A Chairman without an explicit project role can neither be assigned as a task's owner nor submit work; assignment and submission require project membership."
context: |-
  A global Chairman with no project membership can be set as a task's Owner and can then submit that task.
  src/astra/service.py _validate_assignee (~line 510) treats a global Chairman like the project Owner, so the Chairman passes the assignee check without a project role.
  src/astra/service.py list_assignable_users (~line 155) does the same, so the Chairman shows up in the assignable list.
  src/astra/service.py submit_task (~line 1100) then lets that Chairman submit the task.
  Found by the HS3JRY independent review on 2026-09-21 (PR #1).
  docs/design/authorization-matrix.md row "Create/edit ordinary task work: Chairman No" does not mention this exception.
  Decide: either require project membership in code (preferred, matches the matrix) or document the exception in the matrix.
  Add service-level and HTTP-level tests for Chairman assignment and Chairman submission.
definition-of-done: "A Chairman without project membership cannot be listed as assignable, cannot be set as Task Owner, and cannot submit; tests at service and HTTP level cover it; authorization-matrix.md states the rule; existing tests stay green."
tags:
  - astra
blocked-by: []
related:
  - 01M2YBDV8NBKQ34273XKHS3JRY
commits: []
created-at: 2026-09-21T16:28:13Z
updated-at: 2026-09-21T16:28:13Z
---

# Chairman can be assigned as Task Owner without project membership and then submit

## Definition of Done

- [ ] A Chairman without project membership cannot be listed as assignable, cannot be set as Task Owner, and cannot submit; tests at service and HTTP level cover it; authorization-matrix.md states the rule; existing tests stay green.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

