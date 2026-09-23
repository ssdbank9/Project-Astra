---
id: 01M37E0G4VCVXKJPKSSFG9G9PX
title: Approving one of two identical pending Owner requests leaves the other pending
status: backlog
ready: true
creator: Claude
assignee: Claude
goal: "When the Owner approves a pending request, every other pending request with the same task, action and intent is resolved in the same transaction, so no stale duplicate is left in the Owner inbox."
context: |-
  What is wrong: two Managers (or one Manager with two different reasons) can each file the same protected request, for example 'cancel task T'. Dedupe in src/astra/service.py _request_protected_action (~1119-1127) matches requested_by and reason too, so both rows are kept.
  When the Owner approves one, _resolve_pending_requests (~1266-1316) takes the active-approval branch (~1287-1292) and resolves only that request id. The twin stays pending.
  Its expected_revision is now stale, so approving it later is a 409; it sits in the inbox until someone rejects or cancels it by hand.
  Reproduced 2026-09-23 on codex/migration-safety-remediation at 41dd6e2: two Managers request cancelled at the same revision, Owner approves the first: task cancelled, first request approved, second still pending.
  Called SEM-3 in the SRFCZD review; left out of SRFCZD on purpose.
  Related maintainability ticket: a schema-level idempotency key for equivalent pending requests would also prevent the twin at filing time; decide whether to fix here or there.
  Ruled out: the direct-action path (no active approval) already resolves every same-intent request via _request_intent_matches.
definition-of-done: "Approving a request also resolves (approved, with a protected_action_approved event naming the approval) every other pending request on the same task and action whose intent fields match per OWNER_REQUEST_INTENT_FIELDS, inside the approval's transaction"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:26:38Z
updated-at: 2026-09-23T15:26:54Z
updated-by: Claude
---

# Approving one of two identical pending Owner requests leaves the other pending

## Definition of Done

- [ ] Approving a request also resolves (approved, with a protected_action_approved event naming the approval) every other pending request on the same task and action whose intent fields match per OWNER_REQUEST_INTENT_FIELDS, inside the approval's transaction
- [ ] Regression test in tests/test_state_integrity.py: two Managers file the same cancel request; approving one leaves zero pending requests for that task, and a request with a different intent stays pending
- [ ] Full suite green and git diff --check clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

