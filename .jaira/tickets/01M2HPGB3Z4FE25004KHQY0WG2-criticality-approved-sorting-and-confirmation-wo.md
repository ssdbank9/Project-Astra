---
id: 01M2HPGB3Z4FE25004KHQY0WG2
title: "Criticality: approved sorting and confirmation workflow"
status: review
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
updated-at: 2026-09-24T06:02:53Z
claimed-by: vm-809
claimed-at: 2026-09-24T05:49:40Z
updated-by: Claude
outcome-what: "Rework of the review send-back: confirm_criticality now re-reads the old level and revision inside its BEGIN IMMEDIATE transaction and takes an optional expected_revision (stale -> 409); rejects a non-string level and a null/non-string/blank reason with 400; web passes expected_revision and the detail form sends task.revision. Unrated tasks show the shared amber .badge 'Unrated' in the Gantt meta, the schedule table (new Criticality column; the mobile list) and the detail dialog. 8 new tests (6 core, 2 web) plus event assertions in test_confirm_criticality_over_http. README criticality bullet updated."
outcome-why: "Review at 54b6744 found a reproduced race that recorded a false old value and silently overwrote a concurrent confirmation, mutants (no auth check, before dropped, Normal/Low swapped) surviving the suite, JSON null reason stored as 'None', a list level returning 500, and Unrated only as plain text. Aly approved reassignment and fix (Slack ts 1790228901.999149)."
question: "Please accept, or send back: (1) OK that criticality is now criticality-PRIMARY over due-date in the task list order? (2) Any real-browser check needed before sign-off? No browser surface here so it's unverified visually."
outcome-resolves: "DoD: old value now correct under interleaving (test_confirm_criticality_records_true_old_value_under_interleaving, test_confirm_criticality_with_stale_expected_revision_is_a_conflict); actor/old/new/reason pinned in unit and HTTP tests; sort order Critical>High>Normal>Low>Unrated pinned incl. Normal/Low and export sort; member 403 and missing/null reason 400 over HTTP; Unrated conspicuous via badge while sort stays as specified. Five injected mutants all caught. Full suite 343 tests OK (replaces stale 52/102 counts)."
review-summary: |-
  What the code does (it came in with baseline import c25e1f6, so there is no QY0WG2 diff to read):
  - src/astra/service.py:835-855: list_tasks(actor, project_id, sort) takes one of two modes. "criticality" is the default. It orders Critical, High, Normal, Low, then Unrated (rank 4), then by due date with undated tasks last, then by title. "due_date" orders by due date first (undated last), then by criticality, then by title. An unknown mode falls back to "criticality".
  - src/astra/service.py:1904-1928: confirm_criticality requires a manager or the owner (can_manage_project), refuses closed tasks, validates the level, and requires a non-empty reason. It refuses a no-op change. It writes the new level and a dedicated criticality_changed task_event holding actor_user_id, before {criticality: old}, after {criticality: new} and the reason.
  - src/astra/service.py:689: update_task now refuses any criticality change ("Use the confirm criticality action..."). The generic edit form can no longer bypass the audit.
  - Re-import (src/astra/importer.py:2679 and 2942) also writes criticality_changed.
  - Web layer: POST /api/tasks/{id}/criticality (web.py:295), GET /api/tasks?sort= (web.py:68), and a sort parameter on /api/export (web.py:146).
  - UI: a "Sort by" dropdown (index.html:40, app.js:347) re-fetches the list and feeds the Export CSV link. The detail dialog has a "Confirm criticality" form with a reason field (app.js:647-651, 806). Unrated tasks show the text "Unrated".
  - Checks run: full suite `.venv/bin/python tests/run.py` on a scratch copy of HEAD gives 335 tests, OK. Probes confirmed that a plain project member gets Forbidden (HTTP 403), a manager and the owner can confirm, and overdue tasks sort ahead of undated ones within a level.
review-gaps: "1. MEDIUM, confirmed: the recorded old value can be wrong. confirm_criticality reads the old level (service.py:1915) before its BEGIN IMMEDIATE transaction. Its UPDATE (1922) has no revision check, unlike update_task.\n   - Reproduction: scratchpad/rl-QY0WG2/probe_race.py uses two connections on one database file. That is how the ThreadingHTTPServer works, with one connection per request.\n   - A reads \"low\". B then confirms low->critical. A then writes high.\n   - Result: two events both record before = \"low\". B's Critical is silently overwritten, and A's event carries a false old value.\n   - The definition of done requires the old value to be recorded correctly. The fix is to re-read the old value inside the transaction, or to take an expected_revision.\n2. MEDIUM: the tests do not cover the confirmation record as the definition of done requires. I ran the full suite against three mutants in scratch copies (rl-QY0WG2/mutants), and all three survived. The only failure in each run was an unrelated missing README.md in the scratch copy.\n   - qA: deleting the can_manage_project check, so any project member can change criticality. No test fails.\n   - qB: writing before=None, which drops the old value. No test fails. test_confirm_criticality_records_event_and_requires_reason never checks actor_user_id or before_json.\n   - qC: swapping Normal and Low in the sort order. No test fails, because no test creates a Normal task.\n   - test_web.test_confirm_criticality_over_http checks only the returned level. It does not check the audit event, a 403 for a member, or a 400 for a missing reason.\n   - No test covers the export's sort parameter, although the outcome claims it.\n3. LOW: the required reason can be skipped by sending JSON null. str(None).strip() gives \"None\", so {\"reason\": null} is accepted, and the audit row stores the reason \"None\" (reproduced with probe_qy.py). The same pattern is used elsewhere in service.py.\n4. LOW: a non-string level returns HTTP 500 instead of 400. Sending {\"criticality\": [\"high\"]} raises TypeError (unhashable list) and returns the generic \"Internal server error.\" Nothing leaks, but it should be a 400.\n5. JUDGEMENT for Aly: whether Unrated is \"conspicuous\". In the default order Unrated sorts to the very bottom. A task 5 days overdue and Unrated sits below a Low task. Its only marker is the plain text \"Unrated\", with no badge, separate group or styling. That may or may not count as \"sorted away\" under the definition of done.\n6. Stale claims on the ticket: the outcome says \"full suite green (102)\" and the proof line says \"52 pass\". The branch now runs 335 tests, all passing."
review-verdict: |-
  Send back. Both sort modes work as specified. The confirmation path records actor, old value, new value and reason, and the full suite passes (335 tests). Two things fall short of the definition of done:
  - The recorded old value can be wrong when two confirmations interleave. It is read outside the write transaction and there is no revision check. I reproduced this.
  - "Unit + HTTP tests cover the confirmation record" is only partly met. Mutants that remove the authorization check, drop the old value, or swap Normal and Low all pass the suite.
  Smaller fixes: a JSON-null reason gets past the reason requirement, and a non-string level returns 500. Aly also needs to decide whether an Unrated task sitting at the bottom of the default order counts as conspicuous.
review-check: |-
  1. cd /workspace/project-astra && .venv/bin/python tests/run.py 2>&1 | tail -3. Expect "Ran 335 tests" and "OK".
  2. .venv/bin/python -m astra (or however you normally start the server), then log in as the owner.
  3. Create four tasks in one project: Critical due in 60 days, Low due tomorrow, Normal due in 5 days, and one with no criticality.
  4. On the task list, "Sort by" = Criticality. Expect the order Critical, Normal, Low, Unrated. The last row's meta says "Unrated".
  5. Switch "Sort by" to Due date. Expect Low (tomorrow) first, then Normal, then Critical, with the undated task last.
  6. Open the Low task and use "Confirm criticality": choose High and leave the reason blank. Expect an error saying a reason is required.
  7. Enter reason "test" and confirm. The history should show a criticality change from low to high, with your name and "test".
  8. Log in as a project member (not a manager), open the same task and try Confirm criticality. Expect an "access denied" error (HTTP 403).
  9. To see the stale-old-value defect, run .venv/bin/python /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/rl-QY0WG2/probe_race.py. Today it prints two criticality_changed rows that both start from "low", with final "high". After a fix, the second row should start from "critical", or the second write should be refused.
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
