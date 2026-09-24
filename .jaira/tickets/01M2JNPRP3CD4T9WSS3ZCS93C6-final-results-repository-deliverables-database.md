---
id: 01M2JNPRP3CD4T9WSS3ZCS93C6
title: Final results repository (deliverables database)
status: review
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
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
updated-at: 2026-09-24T05:32:43Z
claimed-by: X1CarbonPC-34704
claimed-at: 2026-09-15T16:08:49Z
updated-by: Claude
question: "One call to confirm: an accepted submission is auto-added to the repository (acceptance = a final result), and can be unmarked afterward by a task manager. Is auto-on-accept what you want, or should EVERY final result be an explicit manual mark? Also: attachments must be marked by hand (not auto) — confirm that's right."
outcome-what: "Removed auto-add of accepted submissions to the final-results repository; every final result is now an explicit manual mark (submission or attachment). Updated tests, code comment, and UI text; the manual submission-mark control already existed."
outcome-why: "Owner wanted every final result to be a deliberate manual mark, not auto-recorded on acceptance."
outcome-resolves: "Acceptance no longer records a result; manual mark path proven (core + HTTP); existing tests updated; full suite green."
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

- [x] Accepted submissions / task attachments can be marked a 'final result' and collect into a repository searchable and filterable by entity/project/type/date; owner/authorized scope only; a list export; wired to the accepted-version lifecycle (an accepted submission is a final result); unit + HTTP tests; existing tests green.
  proof: db v10 final_results (source_type submission|attachment, unique per source). accept_submission AUTO-records the accepted submission as a final result (idempotent INSERT OR IGNORE). Service: mark_final_result (accepted-submission or attachment; can_manage_project; audited), unmark_final_result (can_manage_project; audited), list_final_results (scoped like list_tasks: owner/chairman all else EXISTS memberships; filters project/entity/type/from-to + q search; joins task/project/entity/path/version), export_final_results, list_task_final_results (feeds task_detail). web: POST/DELETE/GET /api/final-results (+ ?format=csv). UI: Final results toolbar dialog (filters+table+Export CSV, task drill-in); Mark/Unmark on accepted submissions + attachments in task detail. Tests: test_core.test_accepting_a_submission_auto_records_a_final_result, test_attachment_can_be_marked_and_unmarked_as_final_result, test_only_an_accepted_submission_can_be_a_final_result, test_final_results_are_scoped_to_project_members, test_final_results_filter_by_type; test_web.test_final_results_over_http. 92 pass (was 86).

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-15 16:09 · Aly Jafferani** — PLAN: (1) db v10 final_results(id, task_id FK CASCADE, source_type IN(submission,attachment), submission_id FK, attachment_id FK, title, note, marked_by, marked_at; UNIQUE(submission_id), UNIQUE(attachment_id) — NULLs distinct in sqlite so no false clash). (2) service: mark_final_result(actor,task_id,source_type,source_id,note) gated can_manage_project — submission source must be ACCEPTED, attachment source must belong to the task; INSERT OR IGNORE (idempotent) + task_event final_result_marked. AUTO-mark inside accept_submission (an accepted submission IS a final result, INSERT OR IGNORE). unmark_final_result(actor,result_id) gated can_manage_project + audited final_result_unmarked. list_final_results(actor,filters) SCOPED like list_tasks (owner/chairman all; else EXISTS memberships) + filter project_id/entity_id/type/from/to + q search title; joins task title, project name, entity, path/version. export_final_results -> {as_of, results} for CSV/JSON. (3) web: POST /api/final-results (mark), DELETE /api/final-results (unmark), GET /api/final-results(+filters,+format=csv). (4) UI: 'Final results' toolbar button + dialog (filters+list+Export CSV); 'Mark as final result' on accepted submission lines and attachment lines in task detail + unmark. (5) tests: core (accept auto-marks; mark attachment; member scope isolation; filter by project & type; unmark) + web roundtrip + CSV. Builds on 6G89SJ attachments + accepted-submission lifecycle.
- **2026-09-15 16:14 · Aly Jafferani** — No real-browser visual pass (yolo-chrome down). Verified: 92 tests green incl. HTTP roundtrip + CSV route; app.js node --check clean; migration v10 boots. Scope decision: repository is scoped exactly like the task board (owner/chairman see all; members see only their projects' final results). Completes the owner's 3-part request (attachments 6G89SJ, templates 8B9NBH, final-results repo CS93C6).
- **2026-09-15 18:31 · Aly Jafferani** — OWNER DECISION (2026-09-15): do NOT auto-add accepted submissions to the results repository. EVERY final result must be an explicit MANUAL mark (submissions and attachments both). Remove the auto-on-accept behavior.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. Rework DONE per owner decision (every final result is an explicit MANUAL mark; auto-add on acceptance removed; unmark works; attachments must be marked explicitly). In REVIEW awaiting the model review pass. Re-claim first (claim is stale ~90h). Baseline: python tests/run.py = 102 green. After review pass: jaira move --to signoff with review-summary/gaps/verdict/check, and commit the ticket file with the code in one commit whose message names the handle (board is unshared, so the handle is what makes the commit list derivable).
- **2026-09-24 05:32 · Claude** — Independent review verdict: send back. Recorded by Claude in review-summary/gaps/verdict/check. Why: ticked DoD item and proof still describe auto-record on accept (removed); UI has no date filter; project/entity/date/q filters and CSV export untested. Left in review because the assignee is Aly Jafferani; moving it to in-progress needs Aly to move it or approve reassignment. Any rework commit must name CS93C6.
