---
id: 01M2JNPRP3CD4T9WSS3ZCS93C6
title: Final results repository (deliverables database)
status: review
ready: true
creator: Aly Jafferani
assignee: Claude
goal: A searchable database of final results — accepted deliverables/outputs across tasks — for reuse and reference.
context: "From the owner: 'create a database of final results if needed.' Builds on Attachments on tasks + the existing submission/accepted-version lifecycle already in the app. Section 8: authorized access only, owner controls publication. A cross-project/entity index of finished deliverables."
definition-of-done: "Accepted submissions / task attachments can be marked a 'final result' and collect into a repository searchable and filterable by entity/project/type/date; owner/authorized scope only; a list export; wired to the accepted-version lifecycle (an accepted submission is a final result); unit + HTTP tests; existing tests green."
tags:
  - astra
  - asana
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T13:57:04Z
updated-at: 2026-09-24T06:17:17Z
claimed-by: vm-17792
claimed-at: 2026-09-24T06:09:32Z
updated-by: Claude
question: "One call to confirm: an accepted submission is auto-added to the repository (acceptance = a final result), and can be unmarked afterward by a task manager. Is auto-on-accept what you want, or should EVERY final result be an explicit manual mark? Also: attachments must be marked by hand (not auto) — confirm that's right."
outcome-what: "Reworded DoD 1 to the explicit-mark rule and re-proved it; added Marked from/to date inputs to the Final results dialog (Filter and Export CSV send them); made the 'to' bound include the whole day; added core tests for project/entity/date/q filters, an HTTP test for the date filter, CSV export (header, filters, filename, member scope), and node-driven dialog tests; README line for the repository."
outcome-why: "Review (54b6744) sent it back: DoD proof described removed auto-record, no UI date filter, filters and CSV export untested (an entity-filter mutation survived the suite). Aly approved the rework (Slack ts 1790228901.999149)."
outcome-resolves: "Review gaps 1-3 and 4a (end-of-day 'to' bound); gap 6 already fixed by Y3WC71 and covered by test_csv_exports_neutralise_formula_cells. Entity-filter mutation now fails test_final_results_filter_by_project_and_entity. Full suite 349 OK."
review-summary: "What the code on codex/migration-safety-remediation (1c45904) does:\n\n(1) Database. Schema v10 adds a final_results table (src/astra/db.py:382). source_type is 'submission' or 'attachment'. submission_id and attachment_id are each unique, and rows are deleted when their task is deleted. It is indexed on task and on marked_at.\n\n(2) Acceptance no longer records anything. accept_submission (service.py:1620-1683) only sets the submission to accepted and the task to completed. The CS93C6 comment at :1679 records the owner decision of 2026-09-15.\n\n(3) Marking and unmarking. mark_final_result (service.py:2324) first checks the actor can view the task, then allows the App Owner only. A non-owner gets Forbidden and a final_result_mark_blocked event is written. A submission must be on the task and be accepted, or the call raises ValueError. An attachment must belong to the task, or it raises KeyError. Marking uses INSERT OR IGNORE, and a final_result_marked event is written only when a row was actually inserted. unmark_final_result (:2367) follows the same pattern: view check, then owner only (with an audit event on refusal), then delete with a rowcount check.\n\n(4) Listing. list_final_results (:2397) is scoped like list_tasks: owner and chairman see everything, everyone else only projects they are a member of. It filters by project_id, entity_id, type, a from/to date on marked_at, and q (a LIKE search on the result title, task title or project name). Each row is joined with task, project, marker, attachment path, submission version and the entity names. export_final_results wraps the list with an as_of time. list_task_final_results feeds the task detail view.\n\n(5) HTTP (web.py). GET /api/final-results accepts the six filters, and ?format=csv returns a 9-column CSV named astra-final-results-<as_of>.csv. POST marks (201). DELETE unmarks. Errors are mapped: Forbidden 403, KeyError 404, ValueError 400.\n\n(6) UI (app.js:426-460, 819-899). A 'Final results' toolbar dialog has project, entity, type and search filters, a results table, Export CSV and links into each task. 'Mark as final result' / 'Unmark' controls appear on accepted submissions and attachments, only when can_manage_files is true.\n\n(7) Tests. test_core has 6 final-results tests: no auto-record on accept, attachment mark/unmark, only accepted submissions, member scoping, owner-only for manager/chairman/viewer, and type filter. test_web has test_final_results_over_http, the owner-only HTTP test and the closed-task test. test_state_integrity has 2 tests (idempotent mark, concurrent unmark).\n\nEvidence I ran:\n- The full suite: .venv/bin/python tests/run.py, 335 tests, OK.\n- A probe on a scratch copy. The project, entity, q, from and to filters all give correct results. A member cannot widen scope with project_id and gets Forbidden on another project's task list and on unmark. Marking twice is idempotent. Another task's attachment is refused with 404. A bad date gives HTTP 400. An anonymous GET gives 403. The CSV comes back with status 200 and the expected header row.\n- Three mutations:\n  - Putting auto-mark back into accept_submission fails 3 tests.\n  - Removing the member scope clause fails test_final_results_are_scoped_to_project_members.\n  - Removing the entity_id filter fails nothing.\n\nAuthorization is not weakened. Marking is stricter than the DoD's 'owner/authorized', in line with Section 8 ('owner controls publication'). Reads use the same membership scope as the task board."
review-gaps: |-
  Worst first:

  (1) MEDIUM. The DoD and its proof contradict what shipped. The one DoD item still reads 'wired to the accepted-version lifecycle (an accepted submission is a final result)'. It is ticked, and its proof says 'accept_submission AUTO-records the accepted submission as a final result', cites test_accepting_a_submission_auto_records_a_final_result and '92 pass'.
  - That test no longer exists. It is now test_accepting_a_submission_does_not_auto_record_a_final_result (tests/test_core.py:1282).
  - The code now does the opposite (service.py:1679-1682), per the owner decision of 2026-09-15 recorded in the ticket Progress.
  - Someone signing off from the ticket is shown a false proof.
  - Fix: Aly rewords the DoD to 'accepted submissions are eligible to be marked by hand; acceptance alone records nothing', and the proof is re-ticked with the current test names and the 335-test count.

  (2) MEDIUM. The UI cannot filter by date. The DoD says 'filterable by entity/project/type/date'. The API supports from/to (service.py:2408-2413), but the Final results dialog has no date inputs. collect() in src/astra/static/app.js:457 sends only project_id, entity_id, type and q, so Export CSV from the UI cannot be limited by date either.

  (3) LOW-MEDIUM. Tests are missing for most of the DoD's filters and for the list export.
  - No test covers the project_id, entity_id, from/to or q filters, or GET /api/final-results?format=csv. The only CSV test is for /api/export (test_web.py:620).
  - Proof: I removed the entity_id clause in a scratch copy and all 207 tests in test_core, test_web and test_state_integrity still passed.

  (4) LOW. Date-filter edge cases.
  - marked_at is a UTC isoformat string with microseconds (now_text, service.py:83). 'to' compares against '<date>T23:59:59', so a mark in the last second of the day is left out.
  - Dates are compared in UTC, not in the project timezone (Asia/Karachi is UTC+5). A mark made at 02:00 local time counts as the previous day.

  (5) LOW. q is used in a LIKE without escaping, so '%' or '_' act as wildcards. For example, q=% matched every row in my probe.

  (6) LOW, and the same pre-existing pattern as /api/export. It is already listed as a follow-up in ticket KPH6. _csv_final_results (web.py:590) writes cells that start with '=' as-is. I exported a task titled '=SUM(A1)' and an attachment named '=HYPERLINK(...)', and both came out raw. That allows CSV formula injection when the file is opened in Excel.

  (7) Traceability. No commit names CS93C6, and the ticket's commits list is []. The work sits inside the baseline import c25e1f6, so jaira's derived commit list will be empty. The claim (X1CarbonPC-34704, 2026-09-15) is stale.

  Outcome claims I checked and found supported:
  - Acceptance no longer records a result.
  - The manual submission and attachment mark path works in core and over HTTP.
  - The tests, the code comment and the UI text were updated (app.js:447 says 'Acceptance alone does not add one').
  - The full suite is green.
review-verdict: |-
  Send back. The behaviour works and is correctly authorized:
  - Every final result is a manual mark, made by the App Owner only.
  - Reads are scoped to project membership.
  - All five filters and the CSV export work, as the scratch-copy probe confirmed.
  - 335 tests pass.
  - Mutations of auto-record and of the member scope are caught by the tests.

  It does not yet meet its own definition of done, for three reasons:
  - The single ticked DoD item still claims 'an accepted submission is a final result', with a proof that names a test that no longer exists and describes the removed auto-record behaviour. Aly needs to reword that item to match the 2026-09-15 decision.
  - The Final results dialog has no date filter, although the DoD lists date and the API supports it.
  - The project, entity, date and q filters and the ?format=csv export have no tests. An entity-filter mutation survives the whole suite.

  The low items (end-of-day and UTC date edges, LIKE wildcards, CSV formula cells) can go to a follow-up ticket. I am confident that the core feature is correct. Whether a missing UI date filter blocks sign-off is Aly's call.
review-check: "1. cd /workspace/project-astra && git checkout codex/migration-safety-remediation (it should be at 1c45904 or later).\n2. .venv/bin/python tests/run.py. You should see 'Ran 335 tests' and then 'OK'.\n3. Start a throwaway server:\n   - ASTRA_HOME=$(mktemp -d) .venv/bin/astra init-owner --email owner@example.org (type a password when asked).\n   - Then, with the same ASTRA_HOME: .venv/bin/astra serve --host 127.0.0.1 --port 8765\n   - Open http://127.0.0.1:8765 and sign in.\n4. Create a project and a task. Submit the task, then accept the submission.\n5. Click 'Final results' in the toolbar. The table should say 'No final results yet', which shows acceptance adds nothing.\n6. Open the task. On the accepted submission line, click 'Mark as final result'. The line should change to '★ final result' with an Unmark button.\n7. Re-open 'Final results'. There is one row, '<task title> (v1)'.\n8. Link an attachment on the task and mark it too. In the dialog, pick Type = Attachments and click Filter. Only the attachment row should show.\n9. Look at the filter row. There are project, entity, type and search controls, but no date field. That is gap 2.\n10. Click Export CSV. A file astra-final-results-<timestamp>.csv downloads, with the header 'title,source_type,task_title,project_name,entities,attachment_path,submission_version,marked_by_name,marked_at'.\n11. Sign in as a project Manager and open the task. There should be no Mark or Unmark buttons. The detail view should say 'File and final-result management is App Owner-only'.\n12. Open .jaira/tickets/01M2JNPRP3CD4T9WSS3ZCS93C6-final-results-repository-deliverables-database.md. The ticked DoD proof still says 'accept_submission AUTO-records' and names test_accepting_a_submission_auto_records_a_final_result. grep -n that name in tests/test_core.py and it is not found. That is gap 1."
---

# Final results repository (deliverables database)

## Definition of Done

- [x] Accepted submissions and task attachments can be marked a 'final result' by hand and collect into a repository searchable and filterable by entity/project/type/date (API and UI); owner/authorized scope only; a list export (CSV) that honours the same filters; acceptance alone records nothing (owner decision 2026-09-15: every final result is an explicit manual mark); unit + HTTP tests for each filter and the export; existing tests green.
  proof: Manual mark only: service.mark_final_result/unmark_final_result (App Owner only; test_core.test_final_result_mutations_are_owner_only_for_every_non_owner_role); acceptance records nothing: test_core.test_accepting_a_submission_does_not_auto_record_a_final_result, test_web.test_final_results_over_http. Scope: test_core.test_final_results_are_scoped_to_project_members + member half of test_web.test_final_results_filters_and_csv_export_over_http. Filters (service.list_final_results; 'to' now inclusive of the whole day via marked_at < next day): test_core.test_final_results_filter_by_type, test_final_results_filter_by_project_and_entity, test_final_results_filter_by_marked_date_range, test_final_results_search_matches_title_task_and_project. UI date filter: app.js renderFinalResults fr-from/fr-to sent by Filter and Export CSV — test_web.AstraFinalResultsDialogTests (2). CSV export honours filters, header row, filter-named filename, scope: test_web.test_final_results_filters_and_csv_export_over_http; formula cells neutralised: test_web.test_csv_exports_neutralise_formula_cells. Full suite: Ran 349 tests OK.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Reassign to Claude (Aly approval, Slack ts 1790228901.999149) and send review -> in-progress
- [x] Write failing tests: project/entity/date/q filters (core), date filter + CSV export + scope over HTTP, dialog date inputs (node driver)
- [x] Fix inclusive 'to' bound in list_final_results; add Marked from/to date inputs to the Final results dialog and send them from Filter and Export CSV
- [x] Reword DoD 1 to explicit-mark behaviour and re-prove it; full suite, node --check, compileall, diff --check; before/after screenshots

## Progress
- **2026-09-15 16:09 · Aly Jafferani** — PLAN: (1) db v10 final_results(id, task_id FK CASCADE, source_type IN(submission,attachment), submission_id FK, attachment_id FK, title, note, marked_by, marked_at; UNIQUE(submission_id), UNIQUE(attachment_id) — NULLs distinct in sqlite so no false clash). (2) service: mark_final_result(actor,task_id,source_type,source_id,note) gated can_manage_project — submission source must be ACCEPTED, attachment source must belong to the task; INSERT OR IGNORE (idempotent) + task_event final_result_marked. AUTO-mark inside accept_submission (an accepted submission IS a final result, INSERT OR IGNORE). unmark_final_result(actor,result_id) gated can_manage_project + audited final_result_unmarked. list_final_results(actor,filters) SCOPED like list_tasks (owner/chairman all; else EXISTS memberships) + filter project_id/entity_id/type/from/to + q search title; joins task title, project name, entity, path/version. export_final_results -> {as_of, results} for CSV/JSON. (3) web: POST /api/final-results (mark), DELETE /api/final-results (unmark), GET /api/final-results(+filters,+format=csv). (4) UI: 'Final results' toolbar button + dialog (filters+list+Export CSV); 'Mark as final result' on accepted submission lines and attachment lines in task detail + unmark. (5) tests: core (accept auto-marks; mark attachment; member scope isolation; filter by project & type; unmark) + web roundtrip + CSV. Builds on 6G89SJ attachments + accepted-submission lifecycle.
- **2026-09-15 16:14 · Aly Jafferani** — No real-browser visual pass (yolo-chrome down). Verified: 92 tests green incl. HTTP roundtrip + CSV route; app.js node --check clean; migration v10 boots. Scope decision: repository is scoped exactly like the task board (owner/chairman see all; members see only their projects' final results). Completes the owner's 3-part request (attachments 6G89SJ, templates 8B9NBH, final-results repo CS93C6).
- **2026-09-15 18:31 · Aly Jafferani** — OWNER DECISION (2026-09-15): do NOT auto-add accepted submissions to the results repository. EVERY final result must be an explicit MANUAL mark (submissions and attachments both). Remove the auto-on-accept behavior.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. Rework DONE per owner decision (every final result is an explicit MANUAL mark; auto-add on acceptance removed; unmark works; attachments must be marked explicitly). In REVIEW awaiting the model review pass. Re-claim first (claim is stale ~90h). Baseline: python tests/run.py = 102 green. After review pass: jaira move --to signoff with review-summary/gaps/verdict/check, and commit the ticket file with the code in one commit whose message names the handle (board is unshared, so the handle is what makes the commit list derivable).
- **2026-09-24 05:32 · Claude** — Independent review verdict: send back. Recorded by Claude in review-summary/gaps/verdict/check. Why: ticked DoD item and proof still describe auto-record on accept (removed); UI has no date filter; project/entity/date/q filters and CSV export untested. Left in review because the assignee is Aly Jafferani; moving it to in-progress needs Aly to move it or approve reassignment. Any rework commit must name CS93C6.
- **2026-09-24 06:09 · Claude** — Reassigned from Aly Jafferani to Claude with Aly's approval in Slack (channel C0C43N1CE00, thread 1790160392.461299, message ts 1790228901.999149, 2026-09-24 05:48Z: 'Yes please fix them'). Rework scope: review gaps 1-3 recorded at 54b6744, plus CSV formula neutralisation (gap 6) since this export has its own writer.
- **2026-09-24 06:14 · Claude** — DoD 1 reworded (jaira dod --text) on 2026-09-24: the old text said 'wired to the accepted-version lifecycle (an accepted submission is a final result)' and its proof described accept_submission auto-recording plus a test that no longer exists. That behaviour was removed on purpose (owner decision 2026-09-15). The item now states the current rule: acceptance records nothing; every final result is an explicit manual mark. Proof re-ticked against current tests.
- **2026-09-24 06:14 · Claude** — Rework findings. (a) CSV formula neutralisation was already applied to this export by Y3WC71 (web._csv_final_results uses _csv_cell; test_web.test_csv_exports_neutralise_formula_cells covers a final-results row), so nothing new was needed there. (b) The 'to' date bound was '<day>T23:59:59' against a microsecond isoformat marked_at, so a mark in the last second of the day was dropped (review gap 4); now 'marked_at < next day'. The new core and HTTP date tests failed on exactly this before the fix. (c) Still open, not fixed here: dates are whole UTC days, not the project timezone (Asia/Karachi is UTC+5), so a mark at 02:00 local counts as the previous day; the 'Marked' column shows toLocaleDateString, which can differ from the filter's UTC day. q LIKE wildcards are not escaped (review gap 5). (d) The dialog body has no inner padding (content touches the dialog edge); that was already so before this change (see scratchpad/ui-shots/CS93C6-before-final-results.png). (e) Dialog tests use a small node driver (FINAL_RESULTS_DRIVER in tests/test_web.py), not the shared WIRING_DRIVER, because the wiring driver only knows #detail-body and #inbox-body.
