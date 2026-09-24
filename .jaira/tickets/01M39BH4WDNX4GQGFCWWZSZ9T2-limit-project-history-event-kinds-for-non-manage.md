---
id: 01M39BH4WDNX4GQGFCWWZSZ9T2
title: Limit Project history event kinds for non-managers
status: signoff
ready: true
creator: Claude
assignee: Claude
goal: A project viewer or member who cannot manage the project sees only project_schedule_changed and project_closed events in Project history; the App Owner and project managers still see every kind.
context: |-
  GET /api/projects/{id}/events returns every project event kind to anyone who can_view_project.
  That includes owner-request payloads and reasons (protected_action_*) and import metadata (import_committed: filename, sha256, counts).
  The endpoint and the Project history dialog were added by ticket 5WZ4A8 (now in signoff).
  Code: AstraService.project_events in src/astra/service.py; route in src/astra/web.py; dialog openProjectHistory in src/astra/static/app.js.
  Aly decided in Slack on 2026-09-24 (thread 1790160392.461299, message ts 1790241586.565819, "yes these decisions are okay proceed now"): non-managers see only project_schedule_changed and project_closed.
  "Manager" means the existing AstraService.can_manage_project check: App Owner, or membership role manager.
  A Chairman is not a manager under that check, so a Chairman also gets the filtered list.
  Filter on the server, not in the UI. A non-member must still get 403.
definition-of-done: "Service test: a viewer and a member without manage rights get only project_schedule_changed and project_closed from project_events"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-24T09:21:46Z
updated-at: 2026-09-24T10:12:15Z
updated-by: Claude
claimed-by: vm-684
claimed-at: 2026-09-24T09:22:00Z
outcome-what: "AstraService.project_events filters rows with an allow-list (NON_MANAGER_PROJECT_EVENT_KINDS = project_schedule_changed, project_closed) when can_manage_project is false; service + HTTP tests cover chairman, viewer, member (filtered), owner, manager (all kinds) and outsider (403); README and an app.js comment document it"
outcome-why: Aly decided 2026-09-24 (ts 1790241586.565819) that non-managers must not see owner-request payloads/reasons or import metadata in Project history; Chairman confirmed filtered (ts 1790243107.569629). Allow-list so a new kind stays hidden by default
outcome-resolves: "DoD 1-6: tests/test_core.py:1886 and tests/test_web.py:1276 fail before (failures=6) and pass after; full suite Ran 372 tests OK; node --check, compileall, git diff --check clean"
review-summary: "project_events (service.py:2668-2682) calls get_project first, so non-members get 403 before filtering. For anyone failing can_manage_project it adds a parameterised event_type IN (?,?) from the fixed allow-list NON_MANAGER_PROJECT_EVENT_KINDS (project_schedule_changed, project_closed); App Owner and project managers see every kind; a Chairman without manager membership gets the filtered list, per Aly (ts 1790241586.565819, 1790243107.569629). GET /api/projects/{id}/events is the only reader of project events; imports and owner-action-request routes were already restricted. Tests: test_core test_project_history_non_managers_see_only_schedule_changes_and_closure and test_web test_project_history_kinds_are_limited_for_non_managers_over_http."
review-gaps: |-
  - Low, follow-up for Aly: GET /api/tasks/{id}/events (task_events, service.py:1113) still returns task-level protected_action_* rows with payloads/reasons to anyone who can view the task.
  - Low, fixed before commit: order-sensitive assertions switched to order-independent to avoid clock-resolution flakes.
  - Info: DoD 4-6 proof files (failing-before, verify log, screenshots) live in the session scratchpad, not the repo.
  - Info: protected_action_requested has no label in PROJECT_EVENT_LABELS (pre-existing).
review-verdict: Approve — independent reviewer
review-check: "git diff 0f1eefc -- src README.md tests .jaira && git diff --check; grep -n project_events src/astra/*.py; run the two focused tests; node --check src/astra/static/app.js; mutations: disable the can_manage_project branch, exempt chairman, filter everyone, ignore manager role, drop the get_project gate, widen the allow-list: each fails the focused tests."
---

# Limit Project history event kinds for non-managers

## Definition of Done

- [x] Service test: a viewer and a member without manage rights get only project_schedule_changed and project_closed from project_events
  proof: tests/test_core.py:1886 test_project_history_non_managers_see_only_schedule_changes_and_closure (chairman, viewer, member subtests)
- [x] Service test: the App Owner and a project manager still see every event kind; a non-member still gets Forbidden
  proof: tests/test_core.py:1886 same test: owner and manager subtests assert all 8 kinds; outsider assertRaises(Forbidden)
- [x] HTTP test: GET /api/projects/{id}/events returns the filtered list to a viewer, the full list to owner and manager, and 403 to a non-member
  proof: tests/test_web.py:1276 test_project_history_kinds_are_limited_for_non_managers_over_http (chairman/viewer/member filtered, owner/manager full, outsider 403)
- [x] Tests failed before the fix for the right reason; output saved to scratchpad/ZSZ9T2-failing-before.txt
  proof: /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/ZSZ9T2-failing-before.txt: START_SHA 0f1eefc6 src + new tests, FAILED (failures=6): chairman/viewer/member subtests of both tests got import_committed/protected_action_* rows; owner/manager passed
- [x] Filter is server-side in AstraService.project_events and reuses can_manage_project; the Project history dialog still renders for viewer and manager (Playwright screenshots)
  proof: src/astra/service.py:2670-2682 project_events filters with can_manage_project + NON_MANAGER_PROJECT_EVENT_KINDS; /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/ui-shots/ZSZ9T2-after-viewer-history.png and ZSZ9T2-after-manager-history.png
- [x] Full suite, node --check app.js, compileall and git diff --check pass
  proof: /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/ZSZ9T2-verify.txt: tests/run.py Ran 372 tests OK; node --check app.js exit 0; compileall -q src tests exit 0; git diff --check exit 0

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] failing service test: viewer/member get only the two kinds; owner/manager get all; outsider Forbidden
- [x] failing HTTP test for the same over GET /api/projects/{id}/events
- [x] save failing run to scratchpad/ZSZ9T2-failing-before.txt
- [x] filter in AstraService.project_events with can_manage_project and an allow-list constant
- [x] update app.js dialog comment/intro text if it overstates what a viewer sees
- [x] Playwright before/after screenshots of the viewer and manager dialog
- [x] full suite, node --check, compileall, git diff --check
  proof: /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/ZSZ9T2-verify.txt
- [x] notes on 5WZ4A8 and 8B9NBH

## Progress
- **2026-09-24 09:22 · Claude** — Brainstorm. What the code does: AstraService.project_events (service.py) calls get_project (view check) then returns every row of project_events. Kinds written today: project_schedule_changed, project_closed, import_committed (filename, sha256, counts), protected_action_blocked/requested/approved/rejected/cancelled (action payloads, reasons). Options: (1) filter in project_events with can_manage_project and an allow-list of two kinds - smallest, one place, both HTTP and service callers get it; cost: a new kind is hidden from non-managers until added to the allow-list (safe default). (2) deny-list the sensitive kinds - smaller diff but a new kind leaks by default. (3) filter in app.js - rejected, the JSON still leaks. Choice: (1), as Aly decided. Chairman: can_view_project allows chairman but can_manage_project does not, so chairman is filtered too; this follows "non-managers" literally, flagged for Aly in review.
- **2026-09-24 09:28 · Claude** — In-progress. Screenshots: scratchpad/ui-shots/ZSZ9T2-{before,after}-{viewer,manager}-{toolbar,history}.png, from scratchpad/seed_zsz.py (synthetic data, 127.0.0.1). Before: the viewer saw "Owner request rejected" with its reason, "Owner action blocked", and "Import committed". After: the viewer sees 2 date changes and the closure; the manager still sees all 6. app.js needed no logic change; renderProjectEvent already handles any subset of events. Only a comment changed. The tests seed rows with _project_event directly because no simple public path writes every kind. protected_action_requested has no label in PROJECT_EVENT_LABELS (the raw kind is shown to managers); that is out of scope here. Open question for Aly: a Chairman can view every project but is not a manager under can_manage_project, so a Chairman now sees the filtered list too.
- **2026-09-24 09:49 · Claude** — Chairman decided: Aly confirmed in Slack on 2026-09-24 09:45 UTC (thread 1790160392.461299, message ts 1790243107.569629, 'yes chairman can get filtered history') that a Chairman who is not a manager of the project gets the filtered history (only project_schedule_changed and project_closed). No code change was needed: can_manage_project already returns False for a Chairman without a manager membership. Now pinned by a 'chairman' subtest in test_project_history_non_managers_see_only_schedule_changes_and_closure (tests/test_core.py) and test_project_history_kinds_are_limited_for_non_managers_over_http (tests/test_web.py). Ported from worktree /workspace/wt-new into the main clone; the single-use _seed_every_project_event_kind helper and ALL_PROJECT_EVENT_KINDS class constant were inlined into the one test that used them. Failing-before (START_SHA 0f1eefc6 src + new tests): FAILED (failures=6), the chairman/viewer/member subtests of both tests.
