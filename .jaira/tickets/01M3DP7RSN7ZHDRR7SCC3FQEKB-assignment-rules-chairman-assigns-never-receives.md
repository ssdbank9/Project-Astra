---
id: 01M3DP7RSN7ZHDRR7SCC3FQEKB
title: "Assignment rules: Chairman assigns, never receives; viewers get subtasks only"
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Aly's assignment rules hold on every path: the Chairman may assign tasks and subtasks but is never an assignee, project viewers receive subtasks only, and older assignments that break the rules are flagged for reassignment rather than changed."
context: |-
  What is wrong today (at d082faf):
  - Only an owner or a project manager can set a task's assignee (service.py can_manage_project). The Chairman cannot assign anyone.
  - Anyone with project access can be made a task's assignee, including the Chairman and project viewers (service.py _validate_assignee lets owner/chairman through and any membership role).
  - The same gap is in create, the task panel, bulk Assign, the Excel importer, the on-hold "responsible person" and templates (TEMPLATE_ROLES includes "chairman").
  Trigger: review 12c I3 asked whether viewers should be assignable. Aly answered in Slack (thread 1790256175.671249):
  - ts 1790386228.535829: the Chairman may assign tasks and subtasks to others.
  - ts 1790386492.402489: "No task should be assigned to chairman. but other project viewers can be given sub tasks".
  - Lock #13 granted at ts 1790386688.768309.
  Rules to build:
  - a) can_assign(actor, project) = owner, the project's manager, or the Chairman. The Chairman gains the assignee (panel and bulk Assign) and nothing else; can_manage_project is not widened.
  - b) Nobody is ever assigned to the Chairman: create, update, bulk, importer, hold owner, templates.
  - c) A project viewer gets subtasks only (parent set), never a top-level task; promoting a viewer's subtask is refused ("reassign it first").
  - d) A viewer assigned a subtask can do what a member assignee can on their own task (today: submit it) and nothing else. Per-task check, not a role change.
  - e) Existing data is not changed: tasks already assigned to the Chairman, or top-level tasks assigned to a viewer, keep the owner and are flagged "Needs a new assignee" (card, row, panel; a count on Home for owners and managers). The flag clears on reassignment.
  - f) Pickers: the Chairman is never listed; a viewer only for a subtask, labelled "(viewer)".
  Known: a member assignee today can only submit (can_edit_ordinary and files are owner/manager only), so d) needs no new write path.
definition-of-done: "Server: can_assign (owner, the project's manager, Chairman) gates the assignee in update_task and bulk Assign; the Chairman's other edits stay refused, and can_manage_project is unchanged"
tags:
  - astra
blocked-by: []
related:
  - 01M3CAJRFH9J4RJFVMSZJN1QYG
  - 01M3CEHBP9XNTK0SG1Q8XV92JJ
commits: []
created-at: 2026-09-26T01:45:51Z
updated-at: 2026-09-26T04:20:40Z
updated-by: Claude
claimed-by: vm-1352
claimed-at: 2026-09-26T01:45:58Z
outcome-what: "Added can_assign (owner, the project's manager, Chairman) and an assign-only update path for the Chairman (panel Assign form, bulk Assign and its Undo); _validate_assignee now refuses the Chairman everywhere and a project viewer on a top-level task (create, update, bulk, hold owner, set_parent promotion, importer E_OWNER_CHAIRMAN/E_OWNER_VIEWER, templates). Existing assignments are kept and flagged needs_new_assignee (card, List row, panel, Home tile, risk=reassign). Pickers take a purpose (task, subtask, reviewer): no Chairman, viewers only for subtasks marked (viewer), and a now-forbidden current owner stays selected and marked. README table, handoff and CLAUDE.md; 22 new tests (16 service in test_assignment.py, 6 HTTP and driver in test_web.py) and one updated importer test."
outcome-why: "Aly's answers to review 12c I3 (Slack ts 1790386228.535829 and 1790386492.402489): the Chairman assigns but is never assigned; viewers get subtasks only. Before this, only owners and managers could assign, and anyone with project access, including the Chairman and viewers, could be made an assignee on every path."
outcome-resolves: "Each DoD item is ticked with its proof: the rules hold on every write path in the server, existing data is flagged rather than changed, the UI follows the server, and the full suite runs 663 tests OK with screenshots at 1440 and 390."
---

# Assignment rules: Chairman assigns, never receives; viewers get subtasks only

## Definition of Done

- [x] Server: can_assign (owner, the project's manager, Chairman) gates the assignee in update_task and bulk Assign; the Chairman's other edits stay refused, and can_manage_project is unchanged
  proof: service.py can_assign, _authorize_task_update/_assert_assign_only, _bulk_plan; test_assignment ChairmanAssignsTests (who_may_assign, changes_nothing_but_the_assignee, meets_someone_elses_lock, bulk_assign_and_its_undo)
- [x] Server: _validate_assignee refuses the Chairman everywhere (create, update, bulk, hold owner) and a viewer on a top-level task; set_parent(None) refuses a viewer-assigned subtask; the importer refuses those rows with a clear row error; templates never assign the Chairman or a viewer on a top-level task
  proof: service.py _validate_assignee/_assignee_refusal, set_parent, _suggested_owner/_check_role_assignments; importer.py _check_owner_rules; test_assignment NobodyAssignsTheChairmanTests, ViewersGetSubtasksTests, ImporterAndTemplateTests
- [x] Existing assignments are kept and flagged needs_new_assignee (list, panel, card, row, Home count for owners and managers); the flag clears on reassignment
  proof: service.py _needs_new_assignee (list_tasks, task_detail, export risk=reassign); app.js reassignChip, reassignTile; test_assignment ExistingAssignmentsTests; test_web AstraBulkDriverTests.test_3fqekb_the_needs_a_new_assignee_chip_and_home_count
- [x] Pickers never list the Chairman and list viewers only for subtasks, labelled (viewer); the Chairman sees only the panel assignee control and bulk Assign as new UI
  proof: service.py list_assignable_users(purpose); app.js fillAssignees, assignForm, bulk bar; test_assignment PickerTests; test_web AstraAssignmentWebTests, test_3fqekb_pickers_label_viewers_and_keep_a_forbidden_current_owner, test_3fqekb_the_chairmans_bulk_bar_offers_assign_only, test_3fqekb_the_chairman_sees_the_assignee_control_and_the_chip
- [x] Tests for each rule and role (service, importer, web and driver), README permissions table, handoff and CLAUDE.md updated, screenshots at 1440 and 390, full suite green
  proof: tests/run.py: Ran 674 tests, OK (after review 13a); README assignment table incl. collaborators; CLAUDE_HANDOFF_2026-09-24.md lock #13 entry; CLAUDE.md count; scratchpad lock13-shots m01-m06 at 1440 and 390

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-26 02:08 · Claude** — Choices made (lock #13): (1) Only a CHANGED assignee meets the rules in update_task; an unchanged one still gets the old active/access check. So a flagged task (Chairman or top-level viewer owner) keeps its owner while other fields are edited, and nothing forces a change (rule e). (2) Reviewers/approvers are not assignment: add_task_reviewer uses _validate_project_user (old check), and the reviewer picker (?for=reviewer) still lists the Chairman and viewers. (3) The on-hold responsible person IS the assignee (set_on_hold writes owner_user_id), so it follows the rules; holding a flagged task needs a new responsible person. (4) Templates: TEMPLATE_ROLES keeps 'chairman' so old templates still load; saving a template maps a Chairman-owned task to no suggested role; _template_roles never offers 'chairman'; a 'chairman' pick is refused with a message; an old template's chairman role, or a viewer role on a top-level task, is created unassigned instead of refusing the whole template. (5) Bulk undo of an assign that restores a Chairman owner is refused (restoring would assign the Chairman again). (6) Rule d needed no new write path: a member assignee can only submit today (_may_submit checks owner_user_id); a viewer assignee gets exactly that. (7) The Chairman takes no edit lease (acquire needs manage) but meets others' leases through the _event guard.
- **2026-09-26 02:08 · Claude** — UI: the Chairman's panel replaces the Edit form with an Assign form (#detail-assign: assignee, optional reason, Save assignee); roleLine says so. The other panel sections the Chairman saw before (dependencies, schedule proposal form, criticality) are unchanged and still refused by the server, as before this ticket. The Chairman gets pick boxes in the project List (not the board: cards stay not draggable) and a bulk bar with Assign only. A picker keeps a now-forbidden current owner as a marked '(needs a new assignee)' option so saving other fields never silently unassigns. The Home tile shows only when the count is above zero, for owners (all projects) and managers (their projects).
- **2026-09-26 04:20 · Claude** — Review 13a fixes (approve with follow-ups; 0 High, 1 Medium, 2 Low). M1: a collaborator may submit, so add_task_reviewer and the importer's Collaborators column refuse the Chairman as a collaborator and a viewer as a collaborator on a top-level task (E_COLLABORATOR_CHAIRMAN / E_COLLABORATOR_VIEWER); reviewer and approver stay open (call 3). Older collaborator rows stay: _may_submit ignores them, list_task_reviewers marks them not_allowed, and the task carries needs_new_collaborator (chip 'Collaborator not allowed', same Home tile renamed 'Needs reassigning', risk=reassign). Templates carry no collaborators and bulk has no collaborator action, so nothing to change there. A viewer collaborator also blocks set_parent(None), for the same reason as a viewer assignee. L1: the panel hides the parent, criticality, proposal, dependency, reviewer and Edit forms and the template link when can_edit_ordinary is false, and Submit when permissions.can_submit is false (new). bulkScope admits an assign-only user on the List tab only. L1b (older bug): _validate_task_update treats '' dates as None before the change check, and the panel sends null for empty dates. L2: tests for an explicit unassign and the Chairman collaborator submit.
