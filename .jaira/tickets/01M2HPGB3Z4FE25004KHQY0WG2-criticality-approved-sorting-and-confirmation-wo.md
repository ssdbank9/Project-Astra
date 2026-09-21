---
id: 01M2HPGB3Z4FE25004KHQY0WG2
title: "Criticality: approved sorting and confirmation workflow"
status: review
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: "Make task criticality behave per the approved design so consequence, not just date proximity, drives ordering, and changes are governed."
context: |-
  Astra project tracker (astra_project_tracker/), step 3 of the standalone-tracker gap work.
  Handoff flags Criticality as Partial (section 11): four levels + Unrated + a UI filter exist, but there is no approved sorting, no confirmation workflow, and no change-specific audit.
  Today tasks list-sort by due date only (service.list_tasks ORDER BY due_date). Section 6 requires: confirmed levels sort descending then by nearest/overdue date, Unrated stays visibly separate, and an authorized person confirms a level with recorded old/new/reason.
  Criticality is already a column on tasks and editable via the detail dialog, but a change is just a generic task_updated event.
  Start: add an ordering rank for criticality in list_tasks and a confirmation path that writes a dedicated audit record.
definition-of-done: "Confirmed criticality sorts descending Critical>High>Normal>Low then by nearest due date; Unrated tasks stay conspicuous (not hidden or sorted away); changing criticality records actor, old value, new value, and reason as an audit event; unit + HTTP tests cover the sort order and the confirmation record; existing tests stay green."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T04:51:48Z
updated-at: 2026-09-19T06:14:43Z
claimed-by: X1CarbonPC-18840
claimed-at: 2026-09-15T04:52:45Z
updated-by: Aly Jafferani
outcome-what: "Added a user-selectable sort toggle to the task list: list_tasks(sort='criticality'|'due_date') with two ORDER BY branches; /api/tasks?sort= and an Export CSV sort param; a 'Sort by' dropdown in the toolbar that re-fetches. Default stays criticality."
outcome-why: "Owner wanted BOTH orderings available in the app, not a single hard-coded criticality-primary sort."
question: "Please accept, or send back: (1) OK that criticality is now criticality-PRIMARY over due-date in the task list order? (2) Any real-browser check needed before sign-off? No browser surface here so it's unverified visually."
outcome-resolves: "Both sort modes reachable and correct; unit tests for both orders + unknown-mode fallback, HTTP test for ?sort=; full suite green (102)."
---

# Criticality: approved sorting and confirmation workflow

## Definition of Done

- [x] Confirmed criticality sorts descending Critical>High>Normal>Low then by nearest due date; Unrated tasks stay conspicuous (not hidden or sorted away); changing criticality records actor, old value, new value, and reason as an audit event; unit + HTTP tests cover the sort order and the confirmation record; existing tests stay green.
  proof: astra_project_tracker: service.confirm_criticality + list_tasks ORDER BY criticality rank; tests test_core.test_list_tasks_sorts_by_confirmed_criticality_then_due_date, test_confirm_criticality_records_event_and_requires_reason, test_update_task_cannot_change_criticality_directly, test_web.test_confirm_criticality_over_http; 52 pass

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Add criticality rank ordering in list_tasks: confirmed Critical>High>Normal>Low, Unrated last but conspicuous, then nearest/overdue due date
- [x] Add confirm_criticality service method writing a dedicated criticality_changed audit event (actor, old, new, reason)
- [x] Add API route + wire detail UI to the confirmation path
- [x] Tests: sort order, Unrated placement, confirmation audit record

## Progress
- **2026-09-15 04:57 · Aly Jafferani** — Criticality changes are now blocked from update_task and routed through confirm_criticality (dedicated criticality_changed audit event with old/new/reason). Sort is criticality-PRIMARY then nearest due date, per section 6 (consequence over date proximity) — a Critical task due in 60 days outranks a Low task due tomorrow. Unrated sorts last but stays labeled/visible (not hidden). Detail dialog now has a dedicated Confirm-criticality control; removed criticality from the plain edit form. No real-browser visual pass (no browser surface).
- **2026-09-15 18:31 · Aly Jafferani** — OWNER DECISION (2026-09-15): do NOT hard-code criticality-primary sorting. Provide BOTH sort options in the app, user-selectable: sort by due date AND sort by criticality. Sent back to add a sort toggle (default choice TBD; keep criticality option present).
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. Rework DONE per owner decision (both sort modes, user-selectable; confirm_criticality writes criticality_changed audit). In REVIEW awaiting the model review pass. Re-claim first (claim is stale ~90h). Baseline: python tests/run.py = 102 green. After review pass: jaira move --to signoff with review-summary/gaps/verdict/check, and commit the ticket file with the code in one commit whose message names the handle (board is unshared, so the handle is what makes the commit list derivable).
