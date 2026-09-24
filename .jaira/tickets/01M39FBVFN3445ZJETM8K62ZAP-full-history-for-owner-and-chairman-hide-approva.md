---
id: 01M39FBVFN3445ZJETM8K62ZAP
title: "Full history for Owner and Chairman; hide approval details from other non-managers' task history"
status: signoff
ready: true
creator: Claude
assignee: Claude
goal: "The App Owner, the Chairman and project managers see full project history and full task history; everyone else who can view the project sees only ordinary event kinds plus rows they wrote themselves; non-members still get 403."
context: |-
  Chairman currently gets FILTERED Project history. ZSZ9T2 (commit 17b0bcd, in signoff) made AstraService.project_events filter anyone failing can_manage_project, and a Chairman is not a manager under that check.
  Task history leaks approval details. AstraService.task_events (src/astra/service.py:1113, route GET /api/tasks/{id}/events) returns every task event kind to anyone who can view the project, including protected_action_* payloads and reasons, *_blocked attempts and import_key_assigned.
  Aly decided in Slack thread 1790160392.461299 (ts 1790245384.787859 and 1790245584.314119, 2026-09-24): Owner, Chairman and project managers see FULL project and task history. Members, viewers and non-manager designated approvers see only ordinary task kinds plus their own rows, so an approver still sees the requests they filed.
  Ordinary task kinds (checked against every self._event call in service.py): task_created, task_updated, criticality_changed, parent_changed, dependency_added, dependency_removed, task_submitted, submission_accepted, changes_requested, task_reopened, task_on_hold, schedule_proposed, schedule_revised, schedule_proposal_rejected, attachment_added, attachment_removed, final_result_marked, final_result_unmarked.
  Hidden from them unless they wrote the row: protected_action_blocked/requested/approved/rejected/cancelled, attachment_add_blocked, attachment_removal_blocked, final_result_mark_blocked, final_result_unmark_blocked, import_key_assigned.
  Project history for them keeps the ZSZ9T2 allow-list (project_schedule_changed, project_closed); the own-rows rule applies there too so both endpoints use one predicate.
  Filter on the server with one helper shared by project_events and task_events. A secondary-owner feature from the same Slack message is a separate ticket.
definition-of-done: "Service test: Owner, Chairman and a project manager get every kind from task_events and project_events"
tags:
  - astra
blocked-by: []
related:
  - 01M39BH4WDNX4GQGFCWWZSZ9T2
commits: []
created-at: 2026-09-24T10:28:47Z
updated-at: 2026-09-24T11:07:41Z
updated-by: Claude
claimed-by: vm-13562
claimed-at: 2026-09-24T10:30:59Z
outcome-what: "Added _sees_full_history (Chairman or can_manage_project) and _history_rows in service.py, shared by task_events and project_events; non-full viewers get NON_MANAGER_TASK_EVENT_KINDS / NON_MANAGER_PROJECT_EVENT_KINDS plus rows they wrote; tests for both endpoints over service and HTTP; ZSZ9T2 Chairman subtests now expect full history; README and app.js comment updated"
outcome-why: "Aly decided 2026-09-24 (ts 1790245384.787859, 1790245584.314119): the Owner, the Chairman and managers see full history; other members must not see Owner-action requests/decisions, blocked attempts or import keys written by others, but an approver still sees their own requests"
outcome-resolves: "DoD 1-7: new service + HTTP tests fail before (failures=9) and pass after; mutations fail the tests; full suite Ran 374 tests OK; node, compileall, diff-check, validate clean"
review-summary: "task_events and project_events share _sees_full_history (Chairman or can_manage_project) and _history_rows, which filters everyone else to the allow-listed kinds plus rows they authored with a parameterised, parenthesised predicate; outsiders get 403 before filtering. Round 2 added a second project/task where filtered users author hidden rows; service and HTTP tests assert those rows stay out of the first history, so dropping the parentheses now fails 4 tests. The table-to-key map replaces the free-form key argument (unknown table raises KeyError). Focused tests, node --check and git diff --check pass; full suite 374 OK."
review-gaps: |-
  - Nit: test_web K62ZAP test calls service.get_user(owner_id) twice.
  - Info: tasks.import_key is still returned to members by get_task/list_tasks; only the import_key_assigned event is hidden (matches the rule).
  - Info: non-manager approvers don't see the Owner's approve/reject rows on their own requests (Owner is the author; matches the rule).
  - Round 1 send-back (missing cross-project own-row test; free-form table/key) fixed in round 2.
review-verdict: Approve — independent reviewer
review-check: "Copy the tree (git ls-files | tar) to a scratch dir; run the 6 focused tests (the 2 K62ZAP tests, 2 ZSZ9T2 tests, test_project_history_readable_by_members_not_outsiders, test_project_schedule_and_history_authorization_over_http) with PYTHONPATH=src: OK; node --check src/astra/static/app.js; drop the parentheses around (e.event_type IN (...) OR e.actor_user_id=?) in _history_rows and rerun: FAILED (failures=4); git diff --check."
---

# Full history for Owner and Chairman; hide approval details from other non-managers' task history

## Definition of Done

- [x] Service test: Owner, Chairman and a project manager get every kind from task_events and project_events
  proof: tests/test_core.py test_task_and_project_history_full_for_owner_chairman_manager_filtered_for_others (owner, chairman, manager subtests: every task and project kind)
- [x] Service test: a member, a viewer and a non-manager designated approver get only the ordinary task kinds plus their own rows from task_events, and only project_schedule_changed/project_closed plus their own rows from project_events; a non-member gets Forbidden
  proof: tests/test_core.py test_task_and_project_history_full_for_owner_chairman_manager_filtered_for_others (member, viewer, approver: ordinary kinds + own row, project_closed + own row, no secret-payload, no own rows from a second project/task); outsider Forbidden on both; M1 (dropped parentheses) fails it
- [x] HTTP test: GET /api/tasks/{id}/events and GET /api/projects/{id}/events return full lists to Owner, Chairman and manager, filtered lists (no hidden payload text) to member/viewer/approver, 403 to a non-member
  proof: tests/test_web.py test_task_history_hides_approval_rows_from_non_managers_over_http (incl. approver's row on a second task not leaking) and test_project_history_kinds_are_limited_for_non_managers_over_http (chairman now full)
- [x] ZSZ9T2 Chairman subtests updated to expect full project history
  proof: chairman moved to the full group in tests/test_core.py test_project_history_non_managers_see_only_schedule_changes_and_closure and tests/test_web.py test_project_history_kinds_are_limited_for_non_managers_over_http
- [x] Tests failed before the fix for the right reason; output saved to scratchpad/K62ZAP-failing-before.txt
  proof: /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/K62ZAP-failing-before.txt: START_SHA 17b0bcd src + new tests, FAILED (failures=9): chairman project-history subtests (3) and member/viewer/approver task-history subtests (6); owner/manager passed
- [x] One shared helper decides full vs filtered for both project_events and task_events; filter is server-side
  proof: src/astra/service.py _sees_full_history + _history_rows (table->key fixed allow-list), used by task_events and project_events; mutations incl. M1 in /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/K62ZAP-verify.txt all fail the focused tests
- [x] Full suite, node --check app.js, compileall, git diff --check and jaira validate pass
  proof: /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/K62ZAP-verify.txt round 2: tests/run.py Ran 374 tests OK; node --check exit 0; compileall exit 0; git diff --check exit 0; jaira validate errors false

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] failing service + HTTP tests; update ZSZ9T2 chairman expectations; save failing run
- [x] add _sees_full_history and ordinary-task-kinds allow-list; filter task_events and project_events with allow-list OR own rows
- [x] README note
- [x] full suite, node --check, compileall, git diff --check, jaira validate
  proof: /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/K62ZAP-verify.txt

## Progress
- **2026-09-24 10:32 · Claude** — Pre-work findings. Task kinds were checked against all 29 self._event calls in service.py; the 18 ordinary kinds are the ones Aly listed, and there are no others. Hidden kinds: protected_action_blocked/requested/approved/rejected/cancelled, attachment_add_blocked, attachment_removal_blocked, final_result_mark_blocked, final_result_unmark_blocked, import_key_assigned. task_events is the only reader of task_events (route web.py:215); task_detail does not embed events. A designated approver is a task_reviewers row with role approver; add_task_reviewer requires the person to be a project member (_validate_assignee), so an approver can always view the project. Choice: the own-rows rule (actor_user_id = the viewer) applies to project history as well, so both endpoints share one SQL predicate '(event_type IN allow-list OR actor_user_id=?)'. Today a non-manager's own project rows can only be their own protected_action_blocked attempts, which hold nothing they did not send. Brainstorm and pre-process were skipped: Aly settled the direction in Slack and the plan is on the ticket. Next: failing tests.
- **2026-09-24 10:43 · Claude** — Implemented. service.py: _sees_full_history (chairman, or can_manage_project) and _history_rows (one SQL predicate: allow-list OR actor_user_id = the viewer) are shared by task_events and project_events. NON_MANAGER_TASK_EVENT_KINDS sits next to NON_MANAGER_PROJECT_EVENT_KINDS. The table and column in _history_rows are fixed by the two callers, never user input. Mutations in a scratch copy each fail the focused tests: drop the chairman clause, drop own-rows, filter everyone, filter nobody, add protected_action_requested to the allow-list, bypass the get_task gate. Tests seed rows with _event(notify=False) and _project_event because no public path writes every kind. Not changed: _is_project_manager (task_detail permissions) versus can_manage_project; the Owner is covered by both. Out of scope: the secondary-owner request in the same Slack message (ts 1790245584.314119) is ticket 2.
- **2026-09-24 11:02 · Claude** — Review round 1 send-back addressed. Medium: added a second project and task that each filtered user can view, with a hidden row they wrote there. Tests assert it never appears in the first task's or project's history (service test, all 3 filtered users; HTTP test, approver). M1 (dropping the parentheses around 'event_type IN (...) OR actor_user_id=?') now fails: failures=4. Before this change it passed, because a precedence leak only shows when the same person has rows on another task or project. Low: _history_rows now derives the key column from a fixed {table: key} mapping, so an unknown table raises KeyError; callers pass only the table name. Full suite: 374 OK.
