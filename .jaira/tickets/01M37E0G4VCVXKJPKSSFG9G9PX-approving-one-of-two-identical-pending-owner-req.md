---
id: 01M37E0G4VCVXKJPKSSFG9G9PX
title: Approving one of two identical pending Owner requests leaves the other pending
status: review
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
updated-at: 2026-09-23T16:12:16Z
updated-by: Claude
claimed-by: vm-5858
claimed-at: 2026-09-23T16:01:57Z
outcome-what: "Approving an Owner request now also approves every other pending request on the same task/project and action, filed at the same revision, whose intent matches per OWNER_REQUEST_INTENT_FIELDS; the twin's protected_action_approved detail records approved_request_id and resolution=same_intent_as_approved_request"
outcome-why: "Approval mode ignored the intent and revision the callers already passed, so an identical twin stayed pending with a stale revision and could only 409; reusing the direct-action filter gives both paths one reconciliation rule"
outcome-resolves: "SEM-3: no stale duplicate left in the Owner inbox after an approval; different-intent requests stay pending"
---

# Approving one of two identical pending Owner requests leaves the other pending

## Definition of Done

- [x] Approving a request also resolves (approved, with a protected_action_approved event naming the approval) every other pending request on the same task and action whose intent fields match per OWNER_REQUEST_INTENT_FIELDS, inside the approval's transaction
  proof: src/astra/service.py:1315 (approval reuses the direct-path expected_revision + _request_intent_matches filter) and :1332 (twin detail approved_request_id/resolution), inside the caller's transaction
- [x] Regression test in tests/test_state_integrity.py: two Managers file the same cancel request; approving one leaves zero pending requests for that task, and a request with a different intent stays pending
  proof: tests/test_state_integrity.py:1285 test_approval_resolves_same_intent_twin_and_leaves_other_intent_pending (fails before: twin 'pending' != 'approved')
- [x] Full suite green and git diff --check clean
  proof: tests/run.py: Ran 271 tests OK; git diff --check origin/codex/migration-safety-remediation clean; node --check and compileall clean

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] read _resolve_pending_requests active-approval branch and every caller's intent in approval mode
- [x] failing regression test in tests/test_state_integrity.py: twin cancel requests plus a different-intent request
- [x] in approval mode, also resolve pending same task/action requests that pass the existing expected_revision and _request_intent_matches filters; record approved_request_id and resolution reason on the twin's event
- [x] focused tests, full suite, node --check, compileall, git diff --check
- [x] docs note on the behaviour

## Progress
- **2026-09-23 16:03 · Claude** — Plan reasoning: every caller already passes the executed intent and the pre-action revision to _resolve_pending_requests in approval mode too (it only ignored them). So the fix reuses the direct-path filter unchanged and prepends the active row; no new status, no new matching rule. Twins filed at an older revision are left pending, as the direct path does (they would 409 on approval anyway). A schema-level idempotency key was not chosen here: it would change filing semantics and need a migration; the related ticket owns that.
- **2026-09-23 16:12 · Claude** — Found while fixing: _approved_event_count in tests/test_state_integrity.py counts events whose detail contains the request id as a substring, so once a twin's detail carries approved_request_id the approved request is counted twice. The new test compares request_id fields directly instead; existing tests are unaffected because they never create twins. Approval mode still resolves the active row even when its intent does not match (unchanged); twins filed at an older revision stay pending, as on the direct path. The reopen approval's secondary update_task_status call now also resolves REOPEN_EQUIVALENT_STATUSES requests, matching what a direct reopen already did.
