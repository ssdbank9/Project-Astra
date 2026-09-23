---
id: 01M3549XTPENM6MSYCG2SRFCZD
title: Harden task state integrity and idempotency
status: review
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
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
updated-at: 2026-09-23T03:54:35Z
claimed-by: X1CarbonPC-37080
claimed-at: 2026-09-22T17:58:55Z
updated-by: Aly Jafferani
outcome-what: "Added revision-checked task writes, terminal-state immutability, transactional single-winner lifecycle decisions, idempotent Owner requests with decision/reconciliation controls, and idempotent final-result audit emission, with focused service and HTTP regressions."
outcome-why: "The adversarial review reproduced lost updates, mutable accepted state, duplicate lifecycle events, duplicate unresolved approvals, and duplicate audit events despite a green baseline suite."
outcome-resolves: "All six DoD items are evidenced: stale writes return 409 without mutation, terminal title/date/progress edits require reopen, synchronized acceptance has one winner, requests dedupe and can be decided/reconciled with stale checks, final-result retries are idempotent, and 216/216 plus static/diff gates pass."
executed-by: Codex
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
