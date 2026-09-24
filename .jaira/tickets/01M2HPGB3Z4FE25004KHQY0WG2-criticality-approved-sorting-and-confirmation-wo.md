---
id: 01M2HPGB3Z4FE25004KHQY0WG2
title: "Criticality: approved sorting and confirmation workflow"
status: signoff
ready: true
creator: Aly Jafferani
assignee: Claude
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
updated-at: 2026-09-24T06:11:36Z
claimed-by: vm-809
claimed-at: 2026-09-24T05:49:40Z
updated-by: Claude
outcome-what: "Independent review recorded: approve with low gaps"
outcome-why: "Reviewer verified 343-test suite green, new tests fail on old code, 10/10 mutants caught"
question: "Please accept, or send back: (1) OK that criticality is now criticality-PRIMARY over due-date in the task list order? (2) Any real-browser check needed before sign-off? No browser surface here so it's unverified visually."
outcome-resolves: "Criticality sort order, Unrated visibility and audited confirmation per the definition of done"
review-summary: "Independent review of 2baaf71 (on 54b6744). confirm_criticality (src/astra/service.py) now re-reads the task's criticality and revision inside its BEGIN IMMEDIATE write transaction, fixing the race where two interleaved confirmations recorded a false old value. It takes an optional expected_revision and returns 409 when stale; web.py passes it through and the app.js detail form sends the revision it rendered with. A non-string level returns 400 instead of 500; a null, non-string or blank reason is refused instead of being stored as 'None'. A new critLabel() helper shows the existing amber Unrated badge in the Gantt meta column, a new Criticality column in the schedule table, and the detail dialog. 10 new tests (7 core, 3 web) pin the audit record (actor, old, new, reason), the manager-only 403, Normal-above-Low order, the export sort parameter, the 400s and the two-connection race."
review-gaps: "Low gaps: (1) On phones the schedule table is the default view and the new Criticality column is 9th of 11 in a sideways-scrolling table, so the Unrated badge is off-screen until you scroll right (builder's own mobile screenshot shows no badge). Suggested follow-up: place the column right after Task. (2) The ticket was not moved review -> in-progress before rework and still carried the 54b6744 review fields; these four fields are now overwritten with this review. (3) Unrated still sorts below every Low task, including overdue ones (_CRITICALITY_RANK ELSE 4, service.py:836-837), as the ticket specified; whether a badge alone counts as 'not sorted away' is Aly's call. Info: expected_revision is optional on POST /api/tasks/{id}/criticality (documented as deliberate; the audit event still records the true old value); rated levels still show as raw lowercase text next to the upper-case UNRATED badge (predates this change)."
review-verdict: Approve — independent reviewer
review-check: "Full suite in a git-archive scratch copy of HEAD: tests/run.py ran 343 tests, OK, 0 skipped. New test_core.py/test_web.py run against the base code: 9 failures, 3 errors (race old value, stale expected_revision, null/42/list reasons, list/dict levels). Ten mutants (auth check removed, pre-transaction old value, Normal/Low swapped, revision check off, before={}, reason=None, str(reason) restored, web.py drops expected_revision, Unrated ranked first, level type check removed): all ten caught by test_core and test_web. Race tests are deterministic (two connections, monkeypatched get_task): 20/20 passes each. Test diff is additions only (170+, 0-)."
---

# Criticality: approved sorting and confirmation workflow

## Definition of Done

- [x] Confirmed criticality sorts descending Critical>High>Normal>Low then by nearest due date; Unrated tasks stay conspicuous (not hidden or sorted away); changing criticality records actor, old value, new value, and reason as an audit event; unit + HTTP tests cover the sort order and the confirmation record; existing tests stay green.
  proof: service.confirm_criticality (src/astra/service.py, re-reads old level + revision inside BEGIN IMMEDIATE, optional expected_revision -> 409) + list_tasks rank; Unrated badge via critLabel() in app.js (Gantt meta, schedule table, detail). Tests: test_core test_list_tasks_sorts_by_confirmed_criticality_then_due_date, test_criticality_sort_orders_normal_above_low, test_confirm_criticality_event_records_actor_old_and_new_value, test_confirm_criticality_requires_project_manager, test_confirm_criticality_refuses_null_reason_and_non_string_values, test_confirm_criticality_records_true_old_value_under_interleaving, test_confirm_criticality_with_stale_expected_revision_is_a_conflict; test_web test_confirm_criticality_over_http, test_confirm_criticality_over_http_refuses_member_and_bad_input, test_export_honours_sort_parameter. Full suite 343 tests OK (2026-09-24).

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Add criticality rank ordering in list_tasks: confirmed Critical>High>Normal>Low, Unrated last but conspicuous, then nearest/overdue due date
- [x] Add confirm_criticality service method writing a dedicated criticality_changed audit event (actor, old, new, reason)
- [x] Add API route + wire detail UI to the confirmation path
- [x] Tests: sort order, Unrated placement, confirmation audit record
- [x] Rework: re-read old criticality inside the write transaction + expected_revision check; two-connection race test
- [x] Rework: tests pinning the confirmation record (403 member over HTTP, event before/actor, Normal/Low order, 400 missing reason, export sort)
- [x] Rework: refuse JSON-null reason and non-string level with 400
- [x] Rework: conspicuous Unrated badge in list and detail using existing badge classes; before/after screenshots
- [x] Rework: refresh stale test counts in proof/outcome

## Progress
- **2026-09-15 04:57 · Aly Jafferani** — Criticality changes are now blocked from update_task and routed through confirm_criticality (dedicated criticality_changed audit event with old/new/reason). Sort is criticality-PRIMARY then nearest due date, per section 6 (consequence over date proximity) — a Critical task due in 60 days outranks a Low task due tomorrow. Unrated sorts last but stays labeled/visible (not hidden). Detail dialog now has a dedicated Confirm-criticality control; removed criticality from the plain edit form. No real-browser visual pass (no browser surface).
- **2026-09-15 18:31 · Aly Jafferani** — OWNER DECISION (2026-09-15): do NOT hard-code criticality-primary sorting. Provide BOTH sort options in the app, user-selectable: sort by due date AND sort by criticality. Sent back to add a sort toggle (default choice TBD; keep criticality option present).
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. Rework DONE per owner decision (both sort modes, user-selectable; confirm_criticality writes criticality_changed audit). In REVIEW awaiting the model review pass. Re-claim first (claim is stale ~90h). Baseline: python tests/run.py = 102 green. After review pass: jaira move --to signoff with review-summary/gaps/verdict/check, and commit the ticket file with the code in one commit whose message names the handle (board is unshared, so the handle is what makes the commit list derivable).
- **2026-09-24 05:29 · Claude** — Independent review verdict: send back. Recorded by Claude in review-summary/gaps/verdict/check. Why: old criticality read outside the write transaction (reproduced race), and mutants removing the auth check / dropping the old value / swapping Normal-Low all pass the suite. Left in review because the assignee is Aly Jafferani; moving it to in-progress needs Aly to move it or approve reassignment. Any rework commit must name QY0WG2.
- **2026-09-24 05:49 · Claude** — Reassigned from Aly Jafferani to Claude with Aly's approval: Slack thread C0C43N1CE00 ts 1790160392.461299, message ts 1790228901.999149 (2026-09-24 05:48 UTC), Aly: 'Yes please fix them' (the review gaps recorded at 54b6744).
- **2026-09-24 06:02 · Claude** — Rework notes (2026-09-24): (a) expected_revision on confirm_criticality is OPTIONAL on purpose: the re-read under BEGIN IMMEDIATE alone fixes the false old value for any caller; the UI now sends task.revision (data-revision on #crit-form) so a person who confirmed from a stale dialog gets a 409 instead of silently overwriting. Making it mandatory would break test_state_integrity callers and the API contract for no extra safety on the audit. (b) The no-op check ('already set') moved inside the transaction so it compares against the fresh value. (c) Mutation check, 5 mutants in scratch copies, all killed by test_core+test_web: removed can_manage_project, before=None, Normal/Low swapped, str(reason) null path, actor dropped. (d) On narrow screens the task list is the schedule table, which had no criticality column at all; added one (after Status) so the Unrated badge shows on mobile too. Reused global .badge[data-level=warning] (amber #8a5a00 on #fdf1d9), no new CSS. (e) Not fixed, out of scope: at 1280px the toolbar overflows to the right of the filter card (visible in QY0WG2-before/after-task-list.png); pre-existing. (f) Screenshots: scratchpad/ui-shots/QY0WG2-{before,after}-{task-list,detail-criticality,mobile-*,detail-after-confirm}.png, synthetic data on 127.0.0.1.
