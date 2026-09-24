---
id: 01M37E0G4VCVXKJPKSSFG9G9PX
title: Approving one of two identical pending Owner requests leaves the other pending
status: done
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
updated-at: 2026-09-23T19:50:53Z
updated-by: Aly Jafferani
claimed-by: vm-5858
claimed-at: 2026-09-23T16:01:57Z
outcome-what: "Independent review approved the SEM-3 twin-request reconciliation; review fields recorded"
outcome-why: "Reviewer found the DoD met with only low-severity gaps; a person must accept it in signoff"
outcome-resolves: "SEM-3 review complete"
review-summary: "Before this change, approving an Owner request resolved only that one request. Now _resolve_pending_requests (src/astra/service.py) also approves every other pending request on the same task (or project) and action, filed at the same expected_revision, that passes the existing _request_intent_matches test - the same filter a direct Owner action already uses. It runs inside the action's own transaction, so a failed action rolls the twins back too. Each twin gets the Owner's decision note and a protected_action_approved event recording approved_request_id and resolution=same_intent_as_approved_request. Different-intent requests and requests on other tasks stay pending. One new regression test (test_approval_resolves_same_intent_twin_and_leaves_other_intent_pending) fails on the old code and passes now; docs/design/authorization-matrix.md gained one paragraph."
review-gaps: |-
  Low 1: nothing tests the expected_revision filter; replacing it with 'if True' still passes test_state_integrity and test_core. Suggested test: twin at revision N, bump task to N+1, file and approve at N+1, assert the N twin stays pending.
  Low 2: a twin filed at an older revision is still left in the Owner inbox after an approval; approving it later gives a controlled 409 revision conflict, so the Owner rejects it by hand. The goal 'no stale duplicate left in the Owner inbox' holds only for same-revision twins.
  Low 3: approving a reopen_task request now also approves pending update_task_status requests whose target is in REOPEN_EQUIVALENT_STATUSES (second reconciliation call in reopen_task, service.py ~1692). This matches a direct reopen but docs/design/authorization-matrix.md does not mention the cross-action case.
  Low 4: test helper _approved_event_count (tests/test_state_integrity.py:522) matches the request id anywhere in event detail, so it double-counts once twins carry approved_request_id. Project-level twins (close_project) have no regression test; checked by hand only.
  No live human browser acceptance of the Owner inbox was performed.
review-verdict: Approve — independent reviewer
review-check: "1. cd /workspace/project-astra (branch codex/migration-safety-remediation)  2. cd tests && PYTHONPATH=../src ../.venv/bin/python -m unittest -v test_state_integrity.AstraStateIntegrityTests.test_approval_resolves_same_intent_twin_and_leaves_other_intent_pending  - it reports ok  3. Optional regression proof: in a scratch copy of the tree, replace src/astra/service.py with 'git show 8c6721d:src/astra/service.py' and run the same test - it FAILS with twin 'pending' != 'approved'  4. From the repo root run .venv/bin/python tests/run.py - it ends with OK (271 tests at review time, about 5 minutes)  5. git diff --check 8c6721d..a09a1b5 prints nothing  6. By hand: start the app on 127.0.0.1, have two Managers file the same status-change request on one task at the same revision, approve one as Owner - both leave the Owner inbox; a request with a different target status stays pending."
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
- **2026-09-23 19:10 · Claude** — Accepted by Aly Jafferani in Slack 2026-09-23 19:07 UTC (thread 1790160392.461299, ts 1790190457.194569). Awaiting Aly's local move to done; agents cannot leave signoff.
