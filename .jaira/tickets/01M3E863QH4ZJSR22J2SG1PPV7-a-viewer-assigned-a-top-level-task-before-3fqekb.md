---
id: 01M3E863QH4ZJSR22J2SG1PPV7
title: A viewer assigned a top-level task before 3FQEKB can still submit it
status: review
ready: true
creator: Claude
assignee: Claude
goal: "A project viewer can submit only their own subtask. A viewer who is the legacy assignee of a top-level task (assigned before the 3FQEKB rules, or demoted to viewer later) cannot submit it on any path, sees no Submit button, and the task stays flagged 'Needs a new assignee' until someone reassigns it."
context: |-
  What is wrong today (at 146a5b3):
  - src/astra/service.py _may_submit returns True as soon as actor id == task owner_user_id, before any 3FQEKB role check.
  - So a project viewer who is the assignee of a TOP-LEVEL task can call submit_task and the task goes to submitted.
  - This happens for tasks assigned before the rules (old data) and for a member who is later demoted to viewer (grant_project_access changes the role and leaves the task as it is).
  - permissions.can_submit uses _may_submit, so the task panel also shows Submit to that viewer.
  Rule (Aly, Slack ts 1790386492.402489): no task is ever assigned to the Chairman; project viewers can be given subtasks only. A viewer submits only their own subtask.
  Found by: the independent fact-check of the handoff pack (H2), 2026-09-26. Logged as docs/handoff/NEXT_STEPS.md A3 item 8 (High). Aly asked for it fixed (Slack ts 1790405773.430749).
  Already known:
  - The Chairman is already refused in _may_submit (3FQEKB), and a flagged collaborator is refused (review 13a M1). Only the assignee branch is missing the check.
  - Other paths into submitted: update_task refuses status=submitted ('Use the dedicated submitted action'); board move to Submitted calls submit_task; board and bulk are owner/manager only; the importer refuses a viewer owner on a new top-level row (E_OWNER_VIEWER) and refuses status submitted on update (NO_IMPORT_ON_UPDATE); set_parent refuses promoting a viewer's subtask to top level.
  - Managers and owners may still submit any task in their project, including a flagged one. That is unchanged.
definition-of-done: "_may_submit refuses a project viewer who is the assignee of a top-level task (service.py), using the same _assignee_refusal rule as collaborators; submit_task refuses it before and inside the transaction"
tags:
  - astra
blocked-by: []
related:
  - 01M3DP7RSN7ZHDRR7SCC3FQEKB
commits: []
created-at: 2026-09-26T06:59:31Z
updated-at: 2026-09-26T07:08:44Z
updated-by: Claude
claimed-by: vm-797
claimed-at: 2026-09-26T06:59:43Z
outcome-what: "_may_submit (src/astra/service.py) now runs the 3FQEKB assignee rule for the task's assignee as well as for collaborators, so a project viewer who holds a top-level task (assigned before the rules, or kept after a demotion from member) cannot submit it; permissions.can_submit follows, so the panel hides Submit. Three service tests and one HTTP test; README, HANDOFF and NEXT_STEPS updated."
outcome-why: "The fact-check of the handoff pack (H2) found the assignee branch returned True before any role check. Aly's rule (Slack ts 1790386492.402489): viewers get subtasks only. Aly asked for the fix on 2026-09-26 (ts 1790405773.430749)."
outcome-resolves: "Every DoD item: refusal before and inside the submit transaction, own subtask and member and manager submits unchanged, demote/restore, can_submit false with the flag kept, all paths into submitted walked (note), tests failing before and passing after, full suite 680 OK, docs updated."
---

# A viewer assigned a top-level task before 3FQEKB can still submit it

## Definition of Done

- [x] _may_submit refuses a project viewer who is the assignee of a top-level task (service.py), using the same _assignee_refusal rule as collaborators; submit_task refuses it before and inside the transaction
  proof: src/astra/service.py _may_submit (assignee branch now through _assignee_refusal); test_assignment.test_a_viewer_demoted_inside_the_submit_is_refused_by_the_recheck
- [x] A viewer's own subtask still submits; a member assignee on a top-level task still submits; a manager or owner still submits a flagged task
  proof: test_assignment.test_a_viewer_never_submits_a_top_level_task_even_as_a_legacy_assignee (own subtask and manager submit); test_a_member_demoted_to_viewer_loses_submit_on_a_top_level_task_until_restored (member submits)
- [x] A member demoted to viewer loses Submit on their top-level task, and gets it back when restored to member
  proof: test_assignment.test_a_member_demoted_to_viewer_loses_submit_on_a_top_level_task_until_restored; test_web.AstraAssignmentWebTests.test_a_viewer_holding_a_top_level_task_gets_no_submit_over_http
- [x] permissions.can_submit is false for the viewer legacy assignee, so the task panel shows no Submit; the task keeps needs_new_assignee
  proof: service.py task_detail permissions.can_submit reads _may_submit; app.js:2167 hides Submit when can_submit is false; tests assert can_submit False and needs_new_assignee True (test_assignment, test_web)
- [x] Every path into submitted checked and recorded: submit_task, board move to Submitted, update_task, bulk, importer, set_parent promotion
  proof: jaira note on G1PPV7 (paths walked); board path covered by test_a_member_demoted_to_viewer_loses_submit_on_a_top_level_task_until_restored
- [x] Tests: service tests in tests/test_assignment.py (refused and stays draft; own subtask allowed; demote then restore) and an HTTP test in tests/test_web.py (can_submit false, POST submit 403); full suite green
  proof: tests/test_assignment.py ExistingAssignmentsTests (3 new tests, failing before the fix: scratchpad G1PPV7-failing-before.txt, failures=3); tests/test_web.py AstraAssignmentWebTests.test_a_viewer_holding_a_top_level_task_gets_no_submit_over_http (fails without the fix); full suite Ran 680 tests OK
- [x] Docs: HANDOFF_2026-09-26.md permissions table and note, NEXT_STEPS.md A3 item 8 and README permissions text updated to say it is fixed
  proof: docs/handoff/HANDOFF_2026-09-26.md section 6 table and notes; docs/handoff/NEXT_STEPS.md A3 item 8; README.md assignment paragraph

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] failing service tests first: viewer legacy assignee on a top-level task refused, task stays draft and flagged; demote then restore
- [x] fix _may_submit: after the manager check, the assignee and the collaborator both go through _assignee_refusal with the task's parent read from the database (the in-transaction row has no parent_task_id)
- [x] HTTP test: GET task as that viewer gives can_submit false and needs_new_assignee true; POST /submit is 403
- [x] walk the other paths into submitted and write the result as a note
- [x] docs: HANDOFF permissions row and note, NEXT_STEPS A3 item 8, README
- [x] full suite, then commit with the ticket

## Progress
- **2026-09-26 07:00 · Claude** — Plan reasoning: the fix sits in _may_submit because every submit goes through it: submit_task checks it before BEGIN IMMEDIATE and again on the re-read row, and task_detail's permissions.can_submit reads it, so the API, the board move to Submitted and the panel button all follow one rule. The role is read at submit time, so a member demoted to viewer is covered with no change to grant_project_access, and restoring them to member gives Submit back. The in-transaction row (SELECT id, project_id, owner_user_id, status, revision) has no parent_task_id, so the parent is read from the database, as the collaborator branch already does.
- **2026-09-26 07:03 · Claude** — Paths into submitted, walked at 146a5b3: (1) POST /api/tasks/<id>/submit -> submit_task, which checks _may_submit before the transaction and again on the re-read row (service.py submit_task). (2) Board move to Submitted -> _move_task, owner/manager only (can_manage_project), then submit_task. (3) update_task refuses status=submitted ('Use the dedicated submitted action', _validate_task_update). (4) Bulk changes are owner/manager only and have no submit kind. (5) Importer: owner or manager only; a new top-level row with a viewer owner is E_OWNER_VIEWER; status submitted on an existing task is refused (NO_IMPORT_ON_UPDATE). (6) set_parent refuses promoting a viewer's subtask to top level ('Reassign it first'). (7) Membership demotion (grant_project_access to viewer) changes nothing on the task; the flag appears and submit is now refused because the role is read at submit time. Only (1) and (2) could reach the viewer, and both go through _may_submit. Managers and owners still submit a flagged task: that is management, not the viewer receiving work. Dead end avoided: refusing the demotion itself would change existing data, which 3FQEKB rule e) forbids.
