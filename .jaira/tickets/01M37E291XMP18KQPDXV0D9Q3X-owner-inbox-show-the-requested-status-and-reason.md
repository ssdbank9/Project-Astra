---
id: 01M37E291XMP18KQPDXV0D9Q3X
title: "Owner inbox: show the requested status and reason, and reload the task after a 409"
status: backlog
ready: true
creator: Claude
assignee: Claude
goal: "The Owner can decide a request from the inbox without opening the task, and a 409 conflict anywhere in the task dialog reloads the current task so the user sees the new state."
context: |-
  What is wrong 1: src/astra/static/app.js renderInbox (~496-503) shows only the action name, requester, task title and time. For update_task_status the requested target status (payload status, from_status) and the Manager's reason are not shown, so the Owner approves blind.
  What is wrong 2: after a 409 the UI shows or alerts the message but keeps the stale form (submitDetailEdit ~886-896, request decision ~515). The user must close and reopen the task to see the change. Called SVC-5 in the 03G8EH review.
  Found again in the 2026-09-23 adversarial review of codex/migration-safety-remediation.
  Related: handoff 7.1 asks whether a terminal-source request should offer 'Review and reopen' instead of a generic Approve that returns an error.
  The API already returns payload_json and reason on each request (GET /api/owner-action-requests), so no server change is expected.
definition-of-done: "Each inbox request shows the target status (and from status when present) and the requester's reason, escaped"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:27:36Z
updated-at: 2026-09-23T15:28:04Z
updated-by: Claude
---

# Owner inbox: show the requested status and reason, and reload the task after a 409

## Definition of Done

- [ ] Each inbox request shows the target status (and from status when present) and the requester's reason, escaped
- [ ] A 409 from the task edit, submit or request decision reloads the task (and the inbox) and keeps the conflict message visible
- [ ] Static JS tests cover both; node --check clean; full suite green

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

