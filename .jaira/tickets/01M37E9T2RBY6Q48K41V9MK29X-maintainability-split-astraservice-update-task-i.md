---
id: 01M37E9T2RBY6Q48K41V9MK29X
title: "Maintainability: split AstraService.update_task into policy, validation and persistence helpers"
status: signoff
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
updated-at: 2026-09-23T19:13:15Z
updated-by: Claude
claimed-by: vm-18061
claimed-at: 2026-09-23T18:14:41Z
outcome-what: "Independent review recorded: approve, no behaviour change, five low gaps plus no live browser acceptance"
outcome-why: "The review lane requires a second model's judgement before a person signs off"
outcome-resolves: "Review of the update_task split for 9MK29X"
review-summary: "Independent reviewer recommends approve. The change splits AstraService.update_task (src/astra/service.py) into four private helpers called in the original order: _authorize_task_update, _validate_task_update, _route_protected_status_update, _write_task_update. It adds 19 characterization tests in tests/test_update_task_contract.py. No behaviour change found: line-by-line comparison, the 19 new tests pass on the OLD code, and an old-vs-new differential fuzz (seeds 3 and 17, 4861 trace lines) showed 0 differences. The single transaction, the in-transaction request re-check, the revision predicate, messages, exception types and events are unchanged. Full suite 335 tests OK (316 baseline + 19). The new approval test closes a real gap: moving the request re-check outside the transaction was previously undetected and now fails."
review-gaps: "All low severity. 1) Mutation M4 survives: moving _resolve_pending_requests out of the write transaction in _write_task_update (runs after commit) leaves all tests green; the gap predates this change, but the outcome-why claim that the contract tests stop a check being moved silently is only partly true. 2) CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md:261 and :589 (item 5) still list the long update_task as an open maintainability risk. 3) The 2600-call old-vs-new fuzz cited in outcome-resolves and the DoD1 proof is not committed, so it cannot be re-run from the repo; the reviewer's own fuzz rarely reached the Manager-request and locked-source branches. 4) Helpers pass an untyped 10-key dict; a misspelt key fails only at runtime as KeyError (style). 5) test_unknown_assignee_is_refused checks only ValueError, not the message 'Assigned owner is not a known user.'. 6) No live human browser acceptance was done; evidence is automated tests, fuzz and code reading only."
review-verdict: Approve — independent reviewer
review-check: "1. cd to the repo root on branch codex/migration-safety-remediation. 2. Run: cd tests && PYTHONPATH=../src ../.venv/bin/python -m unittest -v test_update_task_contract  -> expect 19 tests, OK. 3. Run from repo root: .venv/bin/python tests/run.py  -> expect 335 tests, OK, exit 0 (about 5 minutes). 4. Open src/astra/service.py and find update_task: it should only call _authorize_task_update, _validate_task_update, _route_protected_status_update, _write_task_update in that order. 5. Optional mutation check: in _write_task_update move the pending-request re-check outside the 'with transaction' block and re-run step 2 -> test_approval_refused_when_its_request_is_decided_under_the_write should fail. Reviewer results: 19/19 new tests also pass on the old code; differential fuzz 0 differences; mutations M1, M2, M3 caught, M4 (reconciliation after commit) not caught."
---

# Maintainability: split AstraService.update_task into policy, validation and persistence helpers

## Definition of Done

- [x] update_task delegates to small private helpers with the same check order; error messages and HTTP statuses unchanged
  proof: src/astra/service.py:642 update_task -> _authorize_task_update:652, _validate_task_update:666, _route_protected_status_update:720, _write_task_update:768 (single transaction:774); messages/types pinned by tests/test_update_task_contract.py (19 tests, green on old and new code); old-vs-new fuzz 2600 cases 0 diffs
- [x] No test file changes other than additions; full suite green with the same count plus any new tests
  proof: git diff --stat tests: only tests/test_update_task_contract.py added; tests/run.py 335 OK (baseline 316 OK + 19 new)

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] record baseline full-suite count and result
- [x] characterization tests for update_task messages, events and conflict paths not already pinned
- [x] old-vs-new equivalence run on a scratch copy
- [x] extract _authorize_update (load, manage check, revision precheck)
- [x] extract _validate_update_fields (status/criticality, lifecycle refusals, reason, dates, title, assignee)
- [x] extract _route_protected_status_update (locked-source and protected-target routing)
- [x] extract _write_task_update (transaction: request re-check, guarded UPDATE, baseline, event, reconciliation)
- [x] run state_integrity/core/web after each step, then full suite, node --check, compileall, git diff --check
- [x] mutation: move re-check outside the transaction in the helper, confirm a race test fails, restore

## Progress
- **2026-09-23 18:15 · Claude** — Brainstorm: what is wrong. update_task (src/astra/service.py:638-753) is ~115 lines doing, in order: load+manage check, expected_revision type/value check, merge, status/criticality validation, governed/submitted refusals, closed-task immutability (T8WHJR), criticality refusal, reason rules, date order, title, assignee, locked-source routing (submitted refusal, R6 reopen refusal, Manager request, Owner reopen refusal), protected-target Manager request, then the transaction (active-request re-check, revision-predicated UPDATE, baseline, task_updated event, pending-request reconciliation). No defect; the risk is that each remediation round inserts a branch and ordering is load-bearing (R6 refusal before a request is filed; closed check before reason check). Options: (A) extract 4 private helpers in place (_check_update_preconditions / _validate_update_fields returning a small dict / _route_protected_status_update returning a request or None / _write_task_update) - cheap, keeps order visibly linear, no new types. (B) introduce a TaskUpdatePlan dataclass and a policy table - clearer but larger diff and more room for ordering drift. (C) leave it, add comments - zero risk, no gain. Choose A: smallest behaviour-preserving diff; helpers are called in the original sequence so check order is readable from update_task itself.
- **2026-09-23 18:15 · Claude** — Plan rationale: helpers return values rather than mutate state so update_task keeps the exact sequence visible: authorize -> validate -> route (may return a request dict early) -> write. The Manager-request early returns stay in update_task via 'if request is not None: return request' because returning from a helper cannot end the caller. expected_revision from the payload (not before['revision']) stays the UPDATE predicate and the reconcile argument; they are equal after the precheck, but the in-transaction predicate must use the caller's value.
- **2026-09-23 18:29 · Claude** — Findings: (1) Before this ticket NO test caught moving _assert_active_request_revision outside the update_task transaction (mutation M1: all of test_state_integrity stayed green). Under M1 an approval whose request is rejected between pre-check and write still cancels the task, then decide_owner_action_request raises RuntimeError 'Approved action completed without resolving its Owner request.' after commit. New test test_update_task_contract.test_approval_refused_when_its_request_is_decided_under_the_write now fails under M1. (2) Mutation M2 (revision predicate made a tautology so only the pre-transaction revision check remains) is caught by test_concurrent_task_updates_at_one_revision_have_one_winner_and_one_event, test_task_update_refuses_when_task_is_cancelled_before_its_write and the new predicate-conflict test. (3) Strictness choices: _write_task_update takes the caller's task_id (not before['id']) and keeps _progress() and description strip() inside the transaction after the request re-check, exactly where the old code evaluated them, so a stale approval with bad progress still reports the Conflict first. (4) Equivalence harness (scratch, not committed): same random payloads/actors/source statuses against old and new service.py, comparing result or exception type+message, final task row, events and requests with uuids/timestamps canonicalised; seeds 7 (600) and 11 (2000), 0 diffs. Other sibling methods (reopen_task, set_on_hold, etc.) have the same _assert_active_request_revision placement and are likewise only as well covered as their own tests; not examined here, out of scope.
- **2026-09-23 19:13 · Claude** — Accepted by Aly Jafferani in Slack 2026-09-23 19:07 UTC (thread 1790160392.461299, ts 1790190457.194569). Awaiting Aly's local move to done; agents cannot leave signoff.
