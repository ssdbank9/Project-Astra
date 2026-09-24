---
id: 01M3ADA4DRPMWYVBJ2ZJXX9RFM
title: Notify owners when a project is closed or its dates change
status: signoff
ready: true
creator: Claude
assignee: Claude
goal: "Every other active owner gets an inbox notice when an owner closes a project or anyone changes a project's dates, naming the project, what changed and who did it, so no project-level change happens silently."
context: |-
  What is wrong today (branch codex/migration-safety-remediation at 39f4faf):
  - Closing a project (service.py close_project) and changing its dates (service.py set_project_schedule) write a project_events row but notify nobody: _project_event never notifies.
  - Task changes already notify every other active owner (_event -> _notify_owner -> _notify_owners), so project-level changes are the silent exception.
  - A closed project cannot be reopened, so a silent close is the most consequential gap.
  Triggered by: handoff option 4 (task-level actions against the primary owner), scouted in the session scratch file primary-task-guard-scout.md.
  Aly's decisions (Slack thread ts 1790256175.671249, ts 1790276936.363329 and 1790277044.283429):
  - YES: owners are notified when a project is closed or its dates change.
  - NOT wanted: an audit or notice change for reviewer/approver/collaborator changes.
  - NOT wanted: a template-deletion record or notice.
  - NOT wanted: any guard on reassigning or editing the primary owner's tasks (stays allowed for secondary owners).
  - NOT wanted: a close guard. Secondary owners keep the same right as the primary to close a project, including with open work. Project managers still only request a close (unchanged).
  - Separate backlog ticket: record settings changes and reopen a closed project.
  Design: reuse _notify_owners (actor excluded; ordinary notices are not capped, KBWY86). No new audit rows (the events are already recorded). No schema change.
definition-of-done: "Closing a project (by any owner directly, or by an owner approving a Manager's close request) and changing its dates notify every other active owner and not the actor or non-owners, with a summary naming the project, closed (and whether with open work) or the dates old -> new, and who did it; secondary owners can still close a project with open work; no new audit rows and no schema change; tests for secondary and primary closes, approved close requests, date changes and a single-owner install; existing tests green."
tags:
  - astra
blocked-by: []
related:
  - 01M39HQB2EFDXWXH92WYGTEYTG
  - 01M3A64QKGH8B0F5SKYSKBWY86
  - 01M3ADCB413BRFJTKCEXZ72D79
commits: []
created-at: 2026-09-24T19:12:08Z
updated-at: 2026-09-24T19:37:38Z
updated-by: Claude
claimed-by: vm-593
claimed-at: 2026-09-24T19:12:09Z
outcome-what: "Project closes (an owner closing directly, or approving a Manager's close request) and project date changes now send an inbox notice to every other active owner through _notify_owners (actor excluded; ordinary, uncapped). The summary names the project, whether it closed with open work (or the start/target dates old → new) and who did it. Secondary owners keep the right to close, including with open work. No new audit rows, no schema change. Also filed Z72D79 (backlog, Aly): record settings changes and reopen a closed project."
outcome-why: "_project_event never notified, so project closes and date changes were the only owner-relevant changes that reached nobody, and a close cannot be undone. Aly approved notices for these and nothing else (Slack ts 1790276936.363329, 1790277044.283429)."
outcome-resolves: "DoD covered by the five new SecondaryOwnerTests: secondary close with open work (allowed, primary and other secondary told, actor and member not, one audit row), primary close, approved close request, date changes with old/new dates, single owner no self-notice; 443 tests OK."
review-summary: "Independent review 7 (d6012de on 39f4faf), 2026-09-24. _project_event gains an optional notice= that calls _notify_owners with the same event id inside the same write transaction: every other active owner gets one inbox notice, the actor is excluded, actor_user_id is stored, and the notice is not capped. The only two code paths that write project dates or close state (set_project_schedule and close_project) now pass a notice: 'project dates changed: <name> · start A → B, target C → D · by <actor>' (changed fields only, cleared date shown as none) and 'project closed[ with N open task(s)]: <name>[ (approving a close request)] · by <actor>', covering a direct owner close and an owner approving a Manager's request. No close guard (secondary owners still close with open work), no new audit rows, no schema change; app.js, web.py, reviewer and template code untouched. 5 new tests; Z72D79 filed in backlog for Aly."
review-gaps: "Review 7 gaps 1-3 (low) were then pinned in commit 106aea5 by test_project_notices_are_not_capped_skip_inactive_owners_and_show_cleared_dates (six date changes by one owner all notify; an inactive owner gets no project notice; a cleared date reads '→ none'); that commit passed the full suite (Ran 444 tests, OK) but was not re-reviewed. Info only (4-7): (4) notices show ISO dates while the project screen shows '1 Oct 2026' and import screens dd-mm-yyyy (cosmetic). (5) No HTTP-level test; the schedule and close routes call the same service methods and did not change. (6) Existing behaviour: an owner closing directly while a Manager's close request is pending marks that request approved, and the notice (accurately) has no '(approving a close request)'; changing the dates of a closed project is still allowed and now notifies (Z72D79 may consider it). (7) Ticket upkeep: plan step wording (notice=None) and related Z72D79 fixed in 106aea5; handoff section 4 is still the dated 6e52df8 board snapshot."
review-verdict: "approve-with-follow-ups (independent review 7, 2026-09-24). The diff meets the definition of done within Aly's approved scope with no behaviour change beyond the notices; no defects found. The optional follow-up tests (gaps 1-3) were added afterwards in 106aea5."
review-check: "1. Windows, repo root: .venv\\Scripts\\python.exe tests\\run.py; expect 'Ran 444 tests' and 'OK'. 2. .venv\\Scripts\\astra init-owner --email owner@example.org, then .venv\\Scripts\\astra serve --host 127.0.0.1 --port 8765; sign in as the owner (Primary). 3. People: add user 'Deputy' and click 'Make secondary owner'. 4. New project 'Check XX9RFM' with one open task. 5. Sign in as Deputy; set a start and target date for the project with a reason and save. 6. As Deputy close the project (exceptional close with a note): it is allowed even with open work. 7. Deputy's bell shows neither notice. 8. Sign in as Primary; the bell shows 'project dates changed: Check XX9RFM · start none → <date>, target none → <date> · by Deputy' and 'project closed with 1 open task: Check XX9RFM · by Deputy'. 9. Project history shows one 'project closed' row."
---

# Notify owners when a project is closed or its dates change

## Definition of Done

- [x] Closing a project (by any owner directly, or by an owner approving a Manager's close request) and changing its dates notify every other active owner and not the actor or non-owners, with a summary naming the project, closed (and whether with open work) or the dates old -> new, and who did it; secondary owners can still close a project with open work; no new audit rows and no schema change; tests for secondary and primary closes, approved close requests, date changes and a single-owner install; existing tests green.
  proof: service.py _project_event notice -> _notify_owners (actor excluded, uncapped); close_project (direct and approved request) and set_project_schedule. Tests: test_core SecondaryOwnerTests test_a_secondary_owner_closes_a_project_with_open_work_and_the_primary_is_told, test_the_primary_closing_a_project_tells_the_secondary_owners, test_approving_a_managers_close_request_notifies_the_other_owners, test_project_date_changes_notify_the_other_owners_with_old_and_new_dates, test_a_single_owner_gets_no_notice_of_their_own_project_changes. test_project_notices_are_not_capped_skip_inactive_owners_and_show_cleared_dates (review 7 gaps 1-3). Ran 444 tests, OK.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] service.py: _project_event(..., notice=None) notifies the other owners when a notice is given; close_project and set_project_schedule pass a summary to _notify_owners
  proof: service.py _project_event(..., notice=) -> _notify_owners; close_project and set_project_schedule pass summaries; _actor_name
- [x] Tests in test_core: secondary/primary close, approved manager close request, date change, non-owners and single owner
  proof: test_core SecondaryOwnerTests: 5 new tests
- [x] Backlog ticket for settings audit + project reopen (Aly)
  proof: Z72D79 filed in backlog, assignee Aly Jafferani
- [x] README one-liner, handoff/CLAUDE.md counts; full suite and checks; move to review; commit locally
  proof: README inbox bullet; handoff and CLAUDE.md 443; tests/run.py Ran 443 tests OK

## Progress
- **2026-09-24 19:18 · Claude** — Choices (Claude, 2026-09-24): notices use the event kind (project_closed / project_schedule_changed) with task_id NULL; the inbox renders the summary as-is, so app.js needs no change. Summaries: 'project closed[ with N open task(s)]: <project>[ (approving a close request)] · by <actor>' and 'project dates changed: <project> · start A → B, target C → D · by <actor>' (only changed fields; 'none' for a cleared date). Project dates are set only by set_project_schedule: import sets dates only when it creates a project (and never changes an existing project's dates), template apply likewise creates, so neither is a 'change'. No new audit rows, no schema change, no close guard (Aly: secondary owners keep the primary's right to close).
- **2026-09-24 19:37 · Claude** — Review 7 recorded (approve-with-follow-ups, no defects). Gaps 1-3 pinned by a test in 106aea5 (not re-reviewed); gaps 4-7 are info.
