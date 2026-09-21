---
id: 01M2HQJAZQMYMNSDMH2YJZACMP
title: "Schedule-revision model: baseline / current / pending"
status: signoff
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: "Track a task's original baseline, current approved plan, and pending proposals as distinct schedules with full change history."
context: |-
  Astra tracker, section 11 gap "Baseline/current/pending schedules: Missing". Today tasks have only current start_date/due_date plus generic before/after task_updated events.
  Section 6 requires preserving original baseline, current approved plan, and pending proposals separately, and showing impacts before approved rescheduling.
  Buildable at the standalone-tracker boundary; no section 15 decision needed. Start: a schedule-revisions table keyed to task_id with kind (baseline/current/pending), values, actor, reason, approval.
definition-of-done: "Baseline captured at first schedule set and never silently overwritten; current plan and pending proposals stored separately; every schedule change records old/new, actor, time, reason, and approval; dependents never silently rescheduled (impacts shown first); unit + HTTP tests; existing tests green."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T05:10:22Z
updated-at: 2026-09-20T03:10:23Z
claimed-by: X1CarbonPC-37068
claimed-at: 2026-09-15T07:51:20Z
updated-by: Aly Jafferani
outcome-what: "Baseline/current/pending schedule model: immutable baseline captured on first schedule; propose/approve/reject schedule proposals with reason + audit (schedule_revised); dependents shown-not-moved (impacted_successors); Schedule section in task detail; 4 new tests (66 total)."
outcome-why: "Section 6/11 required preserving original baseline, current plan, and pending proposals separately with change history; none existed."
question: "Accept, or send back? Two calls: (1) direct date edits via the normal edit form still change 'current' immediately (with a reason) — the propose/approve flow is the governed alternative, not the only path. OK, or should ALL date changes be forced through propose/approve? (2) baseline is captured once and never editable — intended?"
outcome-resolves: "DoD met: baseline immutable, current+pending separate, each change records old/new/actor/time/reason/approval, dependents never silently rescheduled, unit+HTTP tests, existing tests green."
review-summary: "Schedule-revision model matches the accepted spec. Baseline lives in two nullable tasks columns with a single writer _ensure_baseline (guarded by baseline cols NULL AND some date NOT NULL), so it snapshots once and never overwrites; invoked from create_task, update_task, template instantiation, and approve. Current = live tasks.start/due. Pending = task_schedule_proposals (db v5). propose_schedule requires a non-empty reason, validates due>=start, inserts pending, emits schedule_proposed, returns impacted_successors (open successors, untouched). approve applies proposal to current, calls _ensure_baseline, marks the row approved, writes schedule_revised (before->after/actor/reason). reject requires a fresh non-empty reason and is a true no-op on the task. Authz enforced at HTTP (auth+CSRF) and service (can_manage_project). Meets the accepted DoD."
review-gaps: "None material. (1) Multiple concurrent pending proposals allowed; approving one does not auto-reject the others (each approval is governed/audited, no silent mutation). (2) propose_schedule permits both dates null (governed 'clear schedule') - defensible feature. Adversarial checks clean: baseline null-then-stuck impossible; reject never mutates; approve re-reads the live task so before->after is accurate in a direct-edit/pending race."
review-verdict: pass
review-check: "Read _ensure_baseline, _impacted_successors, propose/approve/reject_schedule_proposal, create_task, update_task, task_detail; db v5 baseline cols + task_schedule_proposals; web POST auth+CSRF + schedule routes; app.js Schedule section. Ran test_core.test_baseline_captured_on_first_schedule_and_immutable, _schedule_proposal_approve_revises_current_without_moving_dependents, _schedule_proposal_reject_is_noop_and_requires_reason, test_web schedule_proposal_over_http -> all pass. No full suite, no edits. No real-browser pass (yolo-chrome down)."
---

# Schedule-revision model: baseline / current / pending

## Definition of Done

- [x] Baseline captured at first schedule set and never silently overwritten; current plan and pending proposals stored separately; every schedule change records old/new, actor, time, reason, and approval; dependents never silently rescheduled (impacts shown first); unit + HTTP tests; existing tests green.
  proof: schema v5 (baseline_start/due + task_schedule_proposals); service propose/approve/reject_schedule_proposal + _ensure_baseline + _impacted_successors; task_detail exposes baseline/current/pending; POST /api/tasks/{id}/schedule-proposals + /approve + /reject; Schedule section in detail UI; tests test_core.test_baseline_captured_on_first_schedule_and_immutable/_schedule_proposal_approve_revises_current_without_moving_dependents/_schedule_proposal_reject_is_noop_and_requires_reason, test_web.test_schedule_proposal_over_http; 66 pass

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Schema v5: baseline_start/due columns on tasks + task_schedule_proposals table
- [x] Service: capture baseline on first schedule set (never overwrite); propose_schedule (reason required, returns impacted successors); approve/reject proposal; approve writes a schedule_revised event and updates current
- [x] task_detail exposes baseline/current/pending; dependents never auto-moved
- [x] API: POST /api/tasks/{id}/schedule-proposals, /approve, /reject
- [x] UI: Schedule section in detail (baseline vs current vs pending, propose + approve/reject, impact list)
- [x] Tests: baseline immutable, propose+approve revises current, reject no-op, impacted successors listed but not moved

## Progress
- **2026-09-15 07:56 · Aly Jafferani** — Baseline = the ORIGINAL schedule, captured by _ensure_baseline the first time a task has any start/due date (on create or first update) and never overwritten after. Current = the task's live start/due. Pending = task_schedule_proposals rows (propose_schedule, reason required). Approve applies the proposal to current + writes a schedule_revised event (old->new/actor/reason); reject is a no-op requiring a reason. Dependents are NEVER auto-moved: propose_schedule returns impacted_successors (open successors) for the UI to show, approval leaves them untouched. Direct date edits via update_task still work and also capture baseline. No real-browser visual pass (no browser in session).
- **2026-09-15 18:32 · Aly Jafferani** — OWNER ACCEPTED (2026-09-15): direct date edits still change current immediately (with reason); propose/approve is the governed alternative; baseline captured once and immutable. Proceeding to model review.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. PARKED in signoff - waiting on the App Owner. Verdict: pass. Owner question: OK that direct date edits still change current immediately (propose/approve is the governed alternative)? Baseline captured once, never editable - intended?
- **2026-09-20 03:10 · Aly Jafferani** — Owner confirmation recorded 2026-09-20: ordinary authorized date edits may update current dates immediately with reason and audit; protected-impact changes require Owner approval. Baseline is captured once and never silently edited.
