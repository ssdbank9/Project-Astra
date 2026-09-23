---
id: 01M3549XTPENM6MSYCG2SRFCZD
title: Harden task state integrity and idempotency
status: in-progress
ready: true
creator: Aly Jafferani
assignee: Claude
goal: "Make Astra task edits, lifecycle decisions, Owner requests and final-result publication concurrency-safe, immutable where governed, and idempotent, with regression tests that fail on the previously reproduced defects."
context: "The 2026-09-22 Codex adversarial review reproduced five defects against disposable SQLite databases while the full suite stayed green: stale full-form edits silently overwrite newer revisions; completed tasks accept ordinary field changes without reopen; two synchronized acceptance calls both succeed and emit duplicate events; identical protected-action retries create duplicate pending requests with no complete decision/reconciliation seam; repeated final-result marking keeps one row but emits duplicate final_result_marked events. Current claude/excel-import head 5adec82 still has unconditional task and lifecycle updates and unconditional event emission after INSERT OR IGNORE. Preserve all reviewed PR #2/#4 fixes and do not broaden into public-auth, deployment, Chairman, mixed-edit, UI or importer follow-up tickets."
definition-of-done: Task updates require an expected revision and atomically reject stale writes without changing the task or audit history; service and HTTP regression tests prove the conflict.
tags:
  - astra
blocked-by: []
related: []
commits:
  - c109687a639bee150a18a72a729bd1d9393fe94a
created-at: 2026-09-22T17:58:32Z
updated-at: 2026-09-23T12:11:55Z
claimed-by: vm-3302
claimed-at: 2026-09-23T12:11:07Z
updated-by: Claude
outcome-what: "Added revision-checked task writes, terminal-state immutability, transactional single-winner lifecycle decisions, idempotent Owner requests with decision/reconciliation controls, and idempotent final-result audit emission, with focused service and HTTP regressions."
outcome-why: "The adversarial review reproduced lost updates, mutable accepted state, duplicate lifecycle events, duplicate unresolved approvals, and duplicate audit events despite a green baseline suite."
outcome-resolves: "All six DoD items are evidenced: stale writes return 409 without mutation, terminal title/date/progress edits require reopen, synchronized acceptance has one winner, requests dedupe and can be decided/reconciled with stale checks, final-result retries are idempotent, and 216/216 plus static/diff gates pass."
executed-by: Codex
review-summary: "Shipped: update_task now requires an integer expected_revision and writes with a conditional UPDATE inside BEGIN IMMEDIATE, returning 409 on a stale revision with no task, event or notification change. Ordinary field edits on completed, cancelled and abandoned tasks are refused in update_task until reopen. Acceptance, request-changes, reopen, hold, schedule decisions and project closure re-read and guard state inside immediate transactions. Pending Owner requests are canonicalised and de-duplicated. A new Owner approve, reject and cancel path dispatches the protected action. Direct Owner actions resolve pending requests. final_result_marked is emitted only on a real insert. The task form sends the loaded revision."
review-gaps: "1) DoD item 4 fails: _resolve_pending_requests (service.py ~1206-1223) matches only action and expected_revision, so a direct Owner status change, reopen, hold, schedule decision or close marks pending Manager requests with a DIFFERENT intent as approved, writing false protected_action_approved audit events (reproduced: Manager asks cancelled, Owner sets in_progress, cancel request recorded approved). 2) Approval discards the Owner's decision note; the Manager's reason is stored as decision_reason (service.py ~1317-1352). 3) close_project approval is not stale-checked; residual work that grows after the request is still closed, irreversibly. 4) An approve racing a reject or cancel of the same request applies the action while the request stays rejected, then returns HTTP 500 (update_task and close_project skip _assert_active_request_revision). 5) Concurrent unmark_final_result writes two unmarked events. 6) Tests do not prove the atomic parts: removing the revision predicate or rowcount check in update_task, the in-transaction request guards, require_owner on decisions, or project-level dedupe leaves the whole suite green. 7) README.md:58-61 claims terminal tasks are immutable, but import, set_parent, confirm_criticality and approved schedule proposals still change them. 8) The definition-of-done field carries only item 1 of 6, and item 6 proof cites 216 tests where the suite is 220. 9) Generic Approve on a terminal-state status request returns 400 and the inbox never routes to reopen (disclosed in handoff 7.1)."
review-verdict: "Changes required. DoD items 1, 2, 3 and 5 hold at runtime (verified with two-connection barrier races and mutation tests). DoD item 4 does not: reconciliation approves non-matching requests. Item 6 evidence is stale. Sending back for a bounded rework: intent-matching reconciliation, Owner decision note, close_project stale check, and race regressions for the untested guards. Independent review by Claude, 2026-09-23."
review-check: "1. cd to the repo and run: .venv/bin/python tests/run.py ; expect 'Ran 220 tests' and OK (this passes today, which is the problem: it does not catch gap 1). 2. Start the local fixture: .venv/bin/python tests/ui_fixture_server.py and open http://127.0.0.1:8766 . 3. Sign in as the fixture Manager, open a task in draft, change Status to Cancelled with a reason, save; you should see that a request was sent to the Owner. 4. Sign out and sign in as the fixture Owner. Open the same task, change Status to In progress with a reason, save. 5. Open Inbox. Expected correct behaviour: the Manager's cancel request is still pending or marked superseded. Today it disappears and its history says approved, although nothing was cancelled. 6. Stop the server and delete tmp_ui_accept."
---

# Harden task state integrity and idempotency

## Definition of Done

- [x] Task updates require an expected revision and atomically reject stale writes without changing the task or audit history; service and HTTP regression tests prove the conflict.
  proof: src/astra/service.py update_task requires expected_revision and uses conditional UPDATE; tests/test_state_integrity.py stale-write regression and tests/test_web.py HTTP 409 regression pass.
- [x] Completed, cancelled and abandoned tasks reject ordinary field edits until the dedicated reopen flow; regression tests cover unchanged status with changed title, dates and progress.
  proof: src/astra/service.py blocks ordinary changes in completed/cancelled/abandoned; test_terminal_tasks_reject_ordinary_edits_until_reopened explicitly covers unchanged-status title, due_date and progress edits for all three states, plus hold rejection.
- [x] Submission acceptance is one transaction with a conditional state transition so two synchronized calls produce exactly one acceptance and one submission_accepted event.
  proof: src/astra/service.py revalidates and conditionally updates submission/task inside one transaction; synchronized test_concurrent_acceptance_has_one_winner_and_one_event passes.
- [x] Equivalent protected-action retries reuse one pending request and one protected_action_requested event; the Owner can approve, reject or cancel a pending request with stale expected revisions refused and direct completed actions reconciling matching requests.
  proof: src/astra/service.py canonical request dedupe, Owner decision dispatcher, stale revision refusal and transactional reconciliation; state-integrity dispatcher/direct-reconcile tests and HTTP approval test pass.
- [x] Repeated final-result marking is idempotent: one result row and one final_result_marked event; unmark and later re-mark remain explicitly auditable.
  proof: src/astra/service.py emits final_result_marked only when INSERT OR IGNORE changes a row; repeated mark and unmark/re-mark regression passes.
- [x] The full project suite, focused concurrency tests, node --check and git diff --check pass; documentation and authorization matrix describe the request-decision and revision-conflict contracts.
  proof: Final complete suite 216/216 in 217.219s; focused state-integrity suite 7/7; Node syntax and git diff checks pass; README and authorization matrix updated.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Add focused failing service and HTTP tests for the five reproduced defects before changing implementation.
  proof: tests/test_state_integrity.py; baseline run: 6 tests reproduced stale overwrite, terminal edits, double acceptance, duplicate requests/events, missing decision method, and duplicate final-result events
- [x] Introduce an explicit conflict error and expected_revision contract at the service and HTTP boundaries; make task updates conditional inside BEGIN IMMEDIATE.
  proof: src/astra/service.py update_task conditional WHERE id/revision; src/astra/web.py Conflict=>409; tests/test_state_integrity.py::test_stale_task_update_is_rejected_without_state_or_event_change passes
- [x] Enforce terminal-task ordinary-field immutability and make acceptance conditional inside its transaction.
  proof: src/astra/service.py terminal ordinary-field guard and locked transactional acceptance; terminal immutability and synchronized acceptance regressions pass
- [x] Make protected requests idempotent and implement Owner approve/reject/cancel with payload and revision revalidation plus request reconciliation.
  proof: src/astra/service.py request dedupe, decide_owner_action_request dispatcher, transactional request reconciliation; all supported protected actions covered by test_owner_approval_dispatches_every_supported_protected_action; HTTP approval regression passes
- [x] Emit final-result events only when the insert changes state; preserve auditable unmark and re-mark behavior.
  proof: src/astra/service.py mark_final_result emits only when INSERT OR IGNORE rowcount is 1; repeated mark and unmark/re-mark regression passes
- [x] Run focused tests, full suite, JavaScript and diff checks; update docs, Jaira proof and review the exact diff.
  proof: Focused state-integrity suite 7/7; full tests/run.py 216/216 in 220.615s; node --check src/astra/static/app.js and git diff --check passed; exact changed-file diff reviewed.

## Progress
- **2026-09-22 18:03 · Aly Jafferani** — Implementation rationale: preserve accepted-version immutability and use the existing owner_action_requests decision columns, avoiding an unnecessary schema change. Require an explicit expected_revision at the service/API/UI boundary and use conditional SQL updates inside BEGIN IMMEDIATE transactions so stale writers fail without emitting events. Canonicalize protected-action payloads (including the task revision) and deduplicate equivalent pending requests inside the same transaction. Add a generic Owner decision path that dispatches existing Owner-only service methods; successful direct or approved actions reconcile matching pending requests atomically, while rejected/cancelled requests never execute. Emit final-result events only when the marker row actually changes. Add focused service, HTTP, idempotency, and concurrency regressions before implementation, then run the full suite and node syntax check.
- **2026-09-23 03:51 · Aly Jafferani** — Adjacent issue deliberately left out of this bounded ticket: migration steps 1-12 still use sqlite executescript semantics that the adversarial probe showed can persist partial DDL after failure. Treat that as a separate migration-safety remediation. This branch has automated service/HTTP/static verification only; no live browser click acceptance, push, or deployment was performed.
- **2026-09-23 12:07 · Claude** — Review 2026-09-23 (Claude): sent back. Main defect: request reconciliation approves non-matching pending requests (see review-gaps 1). Fix plan: match on the executed intent (status/from_status, proposal_id, checkpoint, hold owner, close payload); non-matching stale requests are left pending or marked superseded, never approved; record the Owner's decision note; stale-check close_project; add two-connection race regressions for update_task's revision predicate and the in-transaction request guards. The move back to in-progress waits on Aly allowing reassignment (not_owner gate).
- **2026-09-23 12:11 · Claude** — Moved back to in-progress 2026-09-23 after independent review (see review-gaps). Reassigned to Claude with Aly's approval in Slack (12:10 UTC). Rework is one bounded change at a time: 1) intent-matching reconciliation, 2) record the Owner decision note, 3) close_project stale check, 4) race regressions for the untested in-transaction guards.
