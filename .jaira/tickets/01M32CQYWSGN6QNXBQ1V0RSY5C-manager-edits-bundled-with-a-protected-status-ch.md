---
id: 01M32CQYWSGN6QNXBQ1V0RSY5C
title: Manager edits bundled with a protected status change are silently dropped
status: backlog
ready: true
creator: Claude
assignee: Claude
goal: "When a Manager's task update includes both ordinary field edits and a protected status change, either the ordinary edits are applied (or captured in the Owner request) or the UI tells the Manager they were not saved."
context: |-
  A Manager who edits title, dates or owner and a protected status in one save loses the ordinary edits without warning.
  src/astra/service.py update_task (~lines 608-615): only the status change becomes an owner_action_request.
  The other edits are neither applied to the task nor stored in the request payload.
  src/astra/static/app.js shows only "Owner request created; accepted live state is unchanged", so the Manager is not told the other edits were dropped.
  Found by the HS3JRY independent review on 2026-09-21 (PR #1).
  Decide the behaviour: apply the ordinary edits and then request the status change, or reject the mixed save with a clear message.
  Add tests for the chosen behaviour.
definition-of-done: "Mixed Manager saves have a defined, tested behaviour; the UI message states exactly what was saved and what became a request; existing tests stay green."
tags:
  - astra
blocked-by: []
related:
  - 01M2YBDV8NBKQ34273XKHS3JRY
commits: []
created-at: 2026-09-21T16:28:17Z
updated-at: 2026-09-21T16:28:17Z
---

# Manager edits bundled with a protected status change are silently dropped

## Definition of Done

- [ ] Mixed Manager saves have a defined, tested behaviour; the UI message states exactly what was saved and what became a request; existing tests stay green.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

