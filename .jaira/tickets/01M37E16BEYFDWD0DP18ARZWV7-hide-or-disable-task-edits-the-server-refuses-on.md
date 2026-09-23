---
id: 01M37E16BEYFDWD0DP18ARZWV7
title: Hide or disable task edits the server refuses on closed and submitted tasks
status: signoff
ready: true
creator: Claude
assignee: Claude
goal: "The task detail dialog only offers edits the server will accept for the task's current status, and tells the user to reopen first on a closed task; the server stays the authority."
context: |-
  What is wrong: src/astra/static/app.js renderDetail (~567-570) builds the Status select from STATUSES minus GOVERNED. On a completed/cancelled/abandoned task it still offers cancelled, abandoned and changes_requested, which the server now refuses with 400 (SRFCZD R6).
  On a submitted task it offers in_progress and others; the server refuses leaving review outside accept/request changes (SRFCZD R5).
  The Edit form (#detail-edit ~614), the criticality form, add-predecessor and reviewer forms are still shown on closed tasks; T8WHJR made the server refuse all of those with 400 'reopen the task first'.
  So the user fills a form and only then sees an error.
  Found in the 2026-09-23 adversarial review of codex/migration-safety-remediation (SRFCZD and T8WHJR review gaps).
  Allowed on a closed task: attachments and final-result marking, and the reopen action.
  Ruled out: changing server rules. Keep the server checks exactly as they are; this is UI only.
definition-of-done: "On completed, cancelled and abandoned tasks renderDetail hides or disables the Edit, criticality, dependency and reviewer forms and shows a line saying to reopen the task first; attachments, final-result marking and reopen stay available"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-23T15:27:00Z
updated-at: 2026-09-23T19:11:06Z
updated-by: Claude
claimed-by: vm-28497
claimed-at: 2026-09-23T15:40:31Z
outcome-what: "Independent review approved ARZWV7 with five low findings; review fields recorded"
outcome-why: "Every DoD item holds; nothing medium or higher; server authority unchanged"
outcome-resolves: "ARZWV7 review lane"
review-summary: "Independent review approves ARZWV7. Diff touches only src/astra/static/app.js, style.css, README.md, tests/test_web.py and the ticket; service.py and web.py unchanged, so no authorization was weakened and server refusals still return a controlled 400. Closed tasks (completed, cancelled, abandoned) show one 'Reopen this task to change it' note linking to the reopen form, which is now offered on all three; forms the server refuses are removed (edit, criticality, parent, schedule propose/approve, reviewer add/remove, add predecessor, incoming-dependency remove); attachments, final-result marking, proposal rejection and successor unlinking stay. Managers get a status-request form limited to draft/assigned/in_progress/delayed. Submitted tasks lock Status with an aria-describedby hint and save omits status. Dependency errors share one error line, so Remove on Blocks works on a closed task."
review-gaps: "1. Manager on a submitted task sees hint 'Use Accept or Request changes' but the buttons read 'Request Owner acceptance' / 'Request Owner to return changes' (app.js:607 vs 784-785). 2. #status-locked-hint renders after the whole Status/Start/Due/Progress grid, not under Status (visual only; aria-describedby links it). 3. Client mirrors server lists (BACK_TO_WORK vs MANAGER_ORDINARY_STATUSES, CLOSED_STATUSES and buildLifecycle 'terminal' literal vs REOPEN_ONLY_STATUSES); drift would surface the server 400 again; buildLifecycle could reuse CLOSED_STATUSES. 4. WIRING_DRIVER test selector matches any data-* value, so ['data-remove-pred','t1'] also matches data-remove-succ; passes on new code but should match the named attribute. 5. Manager status-request select shows readable labels while the ordinary Edit status select still shows raw values. 6. No live human browser acceptance yet; only the reviewer's scripted Chromium run on synthetic data."
review-verdict: Approve — independent reviewer
review-check: "13 new tests against base app.js: 19 failures, 3 errors (regression confirmed). 8 mutations M1-M8 in a scratch copy: all caught. node --check src/astra/static/app.js: clean. git diff --check: clean. tests/run.py on scratch copy of HEAD d879391: Ran 282 tests OK. Chromium Playwright on 127.0.0.1:8791 with synthetic fixture: closed-task note and Reopen link, focus to reason field, reopen of cancelled task restores Edit, Manager status request shows 'Owner request created; accepted live state is unchanged.', submitted hint renders, no page errors."
---

# Hide or disable task edits the server refuses on closed and submitted tasks

## Definition of Done

- [x] On completed, cancelled and abandoned tasks renderDetail hides or disables the Edit, criticality, dependency and reviewer forms and shows a line saying to reopen the task first; attachments, final-result marking and reopen stay available
  proof: src/astra/static/app.js:607 (closedNote, 'Reopen task…'), :611 (statusRequest in Lifecycle), :664 (#dep-error kept on closed tasks), :789 (reopen on all closed); tests/test_web.py test_closed_task_hides_refused_forms_and_says_reopen_first, test_closed_task_keeps_attachments_and_final_result_marking_for_the_owner, :1377 AstraDetailDialogWiringTests (unlink successor / reject proposal on a closed task fire the real handlers)
- [x] On a submitted task the Status select is locked; the dialog points to accept / request changes
  proof: src/astra/static/app.js:610 (aria-disabled + aria-describedby status-locked-hint, focusable), :667/:919 (submit leaves locked status out); tests/test_web.py test_submitted_task_locks_status_and_points_to_the_decision, :1439 test_saving_a_submitted_task_leaves_the_locked_status_out
- [x] On a terminal task a Manager's Status select offers only statuses that can become a request (back to ordinary work), never cancelled, abandoned or changes_requested
  proof: src/astra/static/app.js:539 BACK_TO_WORK, :611 statusRequest under the reopen form; tests/test_web.py test_manager_on_a_closed_task_may_only_request_ordinary_work, :1324 test_manager_status_request_sits_under_reopen_as_the_alternative, test_manager_status_request_on_a_closed_task_sends_the_status
- [x] Static JS test in tests/ covers the rendered markup for each case; node --check src/astra/static/app.js clean; full suite green
  proof: tests/test_web.py AstraDetailDialogStatusGateTests (markup, 7 tests) + AstraDetailDialogWiringTests (strict DOM stub, fires real listeners, 6 tests); node --check clean; git diff --check clean; tests/run.py Ran 282 tests OK

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Capture BEFORE screenshots (Owner: completed, cancelled, submitted; Manager: completed) from tests/ui_fixture_server.py on 127.0.0.1
- [x] Failing node-driven test in tests/test_web.py that renders buildDetail sections for closed, submitted and Manager-closed tasks
- [x] Add detailGate(task) and status options helper in app.js; closed notice with jump-to-reopen; hide refused forms (edit, criticality, parent, schedule propose/approve, reviewers add/remove, add predecessor, incoming dependency remove)
- [x] Offer the reopen form on cancelled and abandoned, not only completed (server reopen_task already accepts them)
- [x] Submitted: Status select disabled with a visible hint pointing at Accept / Request changes
- [x] Manager on a closed task: status-request form limited to draft/assigned/in_progress/delayed
- [x] Small CSS rule for the notice using existing tokens; AFTER screenshots
- [x] Focused tests, full suite, node --check, compileall, git diff --check; README note

## Progress
- **2026-09-23 15:41 · Claude** — Brainstorm. What the code shows: renderDetail builds the Status select from STATUSES minus GOVERNED, so a completed task offers cancelled/abandoned/changes_requested; service.update_task refuses those (REOPEN_ONLY_STATUSES + REOPEN_EQUIVALENT_STATUSES check) and refuses any same-status save on a closed task. On a closed task the server also refuses set_parent, confirm_criticality, add/remove reviewer, propose/approve schedule, and add/remove a dependency where this task is the successor (_refuse_closed). It still allows attachments, final results, reject schedule proposal, removing a dependency where this task is the predecessor, and reopen_task for completed, cancelled AND abandoned (the UI only offers reopen on completed). A submitted task refuses any status change; other fields still save. Options: (A) disable every refused control in place with aria-disabled + a reason each: honest but noisy, ~8 disabled forms. (B) one plain notice at the top of a closed task ('Reopen this task to change it' + a button that jumps to the reopen form), refused forms not rendered, read-only lists kept: calm, one path, costs a little discoverability of what exists. (C) collapse the whole dialog to read-only on closed: too blunt, hides attachments and final results that must stay. Pick B, plus for a submitted task keep the Edit form but render the Status select disabled with a visible hint pointing at Accept / Request changes (A-style, because the other fields still work). Manager on a closed task: a short status-request form limited to draft/assigned/in_progress/delayed (the only targets the server turns into a request), per DoD 3.
- **2026-09-23 15:42 · Claude** — Plan rests on: the server lists (REOPEN_ONLY_STATUSES, REOPEN_EQUIVALENT_STATUSES, MANAGER_ORDINARY_STATUSES in service.py) are mirrored in app.js as UI hints only; if they drift the server still refuses, the user just sees the 400 again. Test approach: tests read app.js as text today (AstraStaticAssetTests); to assert real rendered markup, the new test extracts the needed top-level functions from app.js and runs them under node (skipped only if node is absent).
- **2026-09-23 15:53 · Claude** — What the repo does not say: (1) the CSP is style-src 'self', so style="..." attributes in innerHTML are ignored; new visual rules had to be classes in style.css (.state-note, .field-hint, #detail-body select:disabled). (2) reopen_task already accepted cancelled and abandoned tasks but the dialog only offered it on completed; now every closed status gets it, so 'Reopen this task to change it' always has a path. (3) Kept on a closed task because the server allows them: rejecting a pending schedule proposal and removing a dependency where this task is the predecessor (Blocks). Hidden: approve/propose schedule, parent, criticality form, reviewer add/remove, add predecessor, removing an incoming dependency. (4) A Manager on a closed task has two request paths (Request Owner reopening in Lifecycle, and the status-request form DoD 3 asked for); both are real server paths, reopen is the recommended one and the top notice links to it. (5) Test harness: tests/test_web.py DETAIL_DRIVER evaluates the whole app.js under node against a Proxy DOM stub; if a new top-level statement needs a browser API the stub lacks, add it to the stub rather than skipping. Playwright check in a real Chromium: jump link focuses #reopen-form reason; Manager status request returns 'Owner request created'.
- **2026-09-23 16:16 · Claude** — Review round 2 (medium): on a closed task the add-dep block was dropped and took #add-dep-error with it, so the kept 'Blocks: X  Remove' threw a TypeError in removeDependency before any request. Fix: one #dep-error (role=alert) lives in .deps on every task; addDependency and removeDependency both write there. Test first: new WIRING_DRIVER in tests/test_web.py resolves an id only if it is in index.html or in the markup renderDetail just wrote (returns null otherwise, like a browser), parses data-* buttons out of the markup, and fires the listeners renderDetail registered; it failed 3/6 before the fix (TypeError x2, locked status sent). The old lenient Proxy stub is kept for the markup tests only. Lows fixed: Manager status-request form moved into Lifecycle directly under the reopen form with 'Or, instead of reopening, ask to move it straight back into work.' and button 'Request status change'; jump link now 'Reopen task…' / 'Request reopening…'; empty .error lines in .schedule/.lifecycle/.deps collapse (min-height 0, margin 0, still in the a11y tree) so no gap under 'No pending proposals'; submitted Status select is aria-disabled (keyboard reaches it and its hint is announced) and submitDetailEdit drops status via {statusLocked} passed from the wiring, since aria-disabled fields are submitted. Chromium on 127.0.0.1 with synthetic fixture: Remove works with no page error, empty reason shows the server message, jump focuses reopen reason, Manager request returns 'Owner request created'. Server rules unchanged.
- **2026-09-23 19:11 · Claude** — Accepted by Aly Jafferani in Slack 2026-09-23 19:07 UTC (thread 1790160392.461299, ts 1790190457.194569). Awaiting Aly's local move to done; agents cannot leave signoff.
