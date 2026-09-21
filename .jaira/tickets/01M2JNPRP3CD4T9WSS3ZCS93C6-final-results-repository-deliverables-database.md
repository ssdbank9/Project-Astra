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
updated-at: 2026-09-19T06:14:44Z
claimed-by: X1CarbonPC-34704
claimed-at: 2026-09-15T16:08:49Z
updated-by: Aly Jafferani
question: "One call to confirm: an accepted submission is auto-added to the repository (acceptance = a final result), and can be unmarked afterward by a task manager. Is auto-on-accept what you want, or should EVERY final result be an explicit manual mark? Also: attachments must be marked by hand (not auto) — confirm that's right."
outcome-what: "Removed auto-add of accepted submissions to the final-results repository; every final result is now an explicit manual mark (submission or attachment). Updated tests, code comment, and UI text; the manual submission-mark control already existed."
outcome-why: "Owner wanted every final result to be a deliberate manual mark, not auto-recorded on acceptance."
outcome-resolves: "Acceptance no longer records a result; manual mark path proven (core + HTTP); existing tests updated; full suite green."
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
