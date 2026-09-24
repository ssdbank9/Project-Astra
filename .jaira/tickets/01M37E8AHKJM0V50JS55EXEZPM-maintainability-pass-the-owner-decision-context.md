---
id: 01M37E8AHKJM0V50JS55EXEZPM
title: "Maintainability: pass the Owner decision context explicitly instead of _active_owner_request_id"
status: done
ready: true
creator: Claude
assignee: Claude
goal: "The approval being executed travels through the call stack as an explicit argument or context object, not as mutable AstraService instance state."
context: |-
  Maintainability, not a demonstrated defect.
  src/astra/service.py decide_owner_action_request (~1398-1404) sets self._active_owner_request_id and self._active_owner_decision_reason, runs the action, then clears them in finally.
  _assert_active_request_revision (~1338), _resolve_pending_requests (~1286) and code near ~2375-2390 read them with getattr.
  Safe today because the HTTP layer builds a fresh AstraService per request. It breaks if one instance is shared by threads, a background worker, or re-entrant calls.
  Suggested in Codex's handoff CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md section 7.3 item 2; re-listed by the 2026-09-23 adversarial review of codex/migration-safety-remediation.
  Constraint: the six approve-vs-reject race tests in tests/test_state_integrity.py must keep failing when a guard is moved outside its transaction.
definition-of-done: No _active_owner_request_id or _active_owner_decision_reason attribute remains; governed actions receive the decision context explicitly
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:30:54Z
updated-at: 2026-09-23T19:51:06Z
updated-by: Aly Jafferani
claimed-by: vm-32730
claimed-at: 2026-09-23T17:11:29Z
outcome-what: "Independent review approved the explicit OwnerDecision refactor with three low findings recorded as gaps"
outcome-why: "Diff meets all three DoD items; full suite green at 289; 8 of 9 mutations caught"
outcome-resolves: EXEZPM
review-summary: "The AstraService instance flags _active_owner_request_id and _active_owner_decision_reason are removed. A frozen OwnerDecision(request_id, reason) dataclass (src/astra/service.py:96) is built in _execute_owner_action_request and passed as keyword-only owner_decision to the 8 governed actions (update_task, accept_submission, request_changes, reopen_task, set_on_hold, approve_schedule_proposal, reject_schedule_proposal, close_project), then into _assert_active_request_revision, _resolve_pending_requests and close_project's approval branch. decide_owner_action_request no longer sets or resets instance state. Two new tests (tests/test_state_integrity.py) run a nested call inside an approval: a nested direct Owner edit no longer inherits the outer approval (old code: Conflict 'the pending request changed'), and a nested approval no longer clears the outer context (old code recorded 'Manager reason A' instead of 'OWNER NOTE A'). Both confirmed failing on the old service.py and passing now. Full suite 289 tests OK."
review-gaps: "1. Low, coverage: mutation M5 survived. reopen_task's second _resolve_pending_requests call, which approves update_task_status twins of the reopen (src/astra/service.py:1723-1732), still passes test_state_integrity and test_core when owner_decision is replaced with None. The code is correct today, but no test covers it. Follow-up: approve a reopen_task request while a same-revision update_task_status reopen twin is pending, then assert the twin's decision_reason and approved_request_id. 2. Low: owner_decision is now a public keyword on the 8 governed actions; any in-process caller can pass OwnerDecision(request_id=X) and resolve request X as approved without decide_owner_action_request. HTTP cannot reach it (web.py forwards no kwargs). Roughly the same trust level as the old private attribute; worth a docstring note that only _execute_owner_action_request may pass it. 3. Low, stale doc: CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md:261 and :576-581 (remaining-risk item 2) still describe _active_owner_request_id as current; needs a one-line update at merge. 4. Info: test_failed_approval_clears_the_active_request_for_the_next_action (tests/test_state_integrity.py:1338-1340) now asserts the attributes are absent instead of None/empty; stricter, required by DoD item 1, not a weakening."
review-verdict: Approve — independent reviewer
review-check: "1. cd /workspace/project-astra && grep -rn _active_owner src/ — expect no output. 2. cd tests && PYTHONPATH=../src .venv/bin/python -m unittest -v test_state_integrity (use /workspace/project-astra/.venv/bin/python) — expect 'Ran 48 tests ... OK', including test_nested_direct_owner_action_does_not_inherit_the_outer_approval and test_nested_approval_does_not_replace_or_clear_the_outer_approval. 3. To see the old bug: copy the tree to a scratch dir, replace src/astra/service.py there with the parent commit's version (git show c143dbf^:src/astra/service.py), rerun those two tests — one errors with 'the pending request changed', the other fails with 'Manager reason A' != 'OWNER NOTE A'. 4. Full suite: /workspace/project-astra/.venv/bin/python tests/run.py from the repo root — expect all tests OK (289 at review time)."
---

# Maintainability: pass the Owner decision context explicitly instead of _active_owner_request_id

## Definition of Done

- [x] No _active_owner_request_id or _active_owner_decision_reason attribute remains; governed actions receive the decision context explicitly
  proof: src/astra/service.py:96 OwnerDecision (frozen dataclass); built in _execute_owner_action_request (service.py:1431) and passed as keyword-only owner_decision to the 8 governed actions; grep _active_owner src/ returns nothing
- [x] All test_state_integrity race and flag-reset tests pass unchanged (or with only signature updates); full suite green
  proof: tests/test_state_integrity.py: 48/48 OK; only change to existing tests is test_failed_approval_clears_the_active_request_for_the_next_action (line 1331) asserting the two attributes are absent instead of None/''; full suite tests/run.py Ran 289 OK
- [x] A nested or re-entrant decision cannot leak one request's decision context into another (regression test)
  proof: tests/test_state_integrity.py:1372 test_nested_direct_owner_action_does_not_inherit_the_outer_approval and :1389 test_nested_approval_does_not_replace_or_clear_the_outer_approval; both failed before the change (Conflict 'pending request changed'; decision_reason 'Manager reason A' != 'OWNER NOTE A')

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Map every reader of _active_owner_request_id/_active_owner_decision_reason (8 governed actions, 2 helpers, close_project)
- [x] Write failing re-entrancy test in tests/test_state_integrity.py
- [x] Add frozen OwnerDecision dataclass and keyword-only owner_decision parameter on the 8 governed actions
- [x] Thread owner_decision into _assert_active_request_revision, _resolve_pending_requests and close_project; remove instance flags
- [x] Update the flag-reset test's two attribute asserts to assert no instance state exists
- [x] Focused tests, full suite, node --check, compileall, diff --check

## Progress
- **2026-09-23 17:12 · Claude** — Plan reasoning: a contextvars.ContextVar would fix thread safety but keeps the dependency implicit, which is what the ticket objects to. An explicit keyword-only owner_decision parameter is chosen instead: 8 public actions (update_task, accept_submission, request_changes, reopen_task, set_on_hold, approve_schedule_proposal, reject_schedule_proposal, close_project) gain owner_decision=None; only _execute_owner_action_request passes it. web.py never forwards **kwargs, so HTTP callers cannot supply it. test_failed_approval_clears_the_active_request_for_the_next_action reads the two attributes directly; its two asserts must change to 'attribute absent' since the DoD removes the attributes.
- **2026-09-23 17:21 · Claude** — Findings: (1) with the old instance flags, a nested decide_owner_action_request cleared the outer approval's flag in its finally, so the outer action ran as a direct Owner action and recorded the Manager's request reason instead of the Owner's note - no error raised, silent audit drift. (2) a nested direct Owner action inherited the outer request id and was refused with 'the pending request changed'. Re-entrancy tests inject the nested call by patching the instance's _execute_owner_action_request, whose signature (actor, request, payload, reason) was kept on purpose so the wrapper stays valid. owner_decision is keyword-only with default None; web.py never forwards kwargs, so an HTTP caller cannot supply it. CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md lines 261/578 still describe the old flag; left alone because it is a dated handoff other tracks edit.
- **2026-09-23 19:12 · Claude** — Accepted by Aly Jafferani in Slack 2026-09-23 19:07 UTC (thread 1790160392.461299, ts 1790190457.194569). Awaiting Aly's local move to done; agents cannot leave signoff.
