---
id: 01M3BVD71SMNH4E0M2CRFKVHH8
title: "Gate 2 slice 6: My Work groups and calendar month view, Inbox polish"
status: review
ready: true
creator: Claude
assignee: Claude
goal: "A person opens My Work and sees what to do by when (Overdue, Today, This week, Later, No date, with counts) or the same work on a month calendar; the Inbox shows what needs them first and what they have not read, and lets them mark it read."
context: |-
  What is wrong today (after slice 5, CR121Z):
  - My Work (app.js renderMyWork, WORK_GROUPS) groups open tasks you own, but the week group reads 'Next 7 days', empty groups vanish, and there is no calendar.
  - There is no month view anywhere. Dates can only be seen on the Gantt (#/portfolio) or a project's Timeline tab.
  - The Inbox (renderInbox) is two plain lists: owner requests, then every notification. Unread rows look almost the same as read ones, a row cannot open its task, and there is no way to see only unread items.
  Trigger: Aly's lock #10 (Slack ts 1790322792.679739, 2026-09-25) for Gate 2 slices 4-6.
  Aly's decisions: the Calendar month view is in scope and lives under My Work; Workload is dropped; front end only; no new dependencies.
  Spec: session file ux-research.md slice 6; design frames gate2-*.png; artifact FwmJpbSwLzoL3aZxFpQKr7.
  Already there: parseRoute accepts #/my-work/calendar (path 'my-work/calendar'); GET /api/notifications returns task_id and task_title per row; POST /api/notifications/<id>/read and /api/notifications/read-all exist.
  Wiring tests (tests/test_web.py WIRING_DRIVER) need #inbox-error, #read-all and data-request-decision buttons to stay inside #inbox-body.
  Not in this slice: drag and drop on the calendar, a week view, workload, notification settings.
definition-of-done: "My Work list groups open tasks into Overdue, Today, This week, Later and No date with counts, soonest first; each row opens the task panel; a good empty state"
tags:
  - astra
blocked-by: []
related:
  - 01M2JHKHPFGHBYXK2FFDX8FNA5
  - 01M2WNN5PQXBBCD0XTZGJQY55P
  - 01M3BSY3W3FH34MF87RACR121Z
commits: []
created-at: 2026-09-25T08:37:44Z
updated-at: 2026-09-25T08:53:48Z
updated-by: Claude
claimed-by: vm-10500
claimed-at: 2026-09-25T08:38:56Z
outcome-what: "My Work List tab with five due groups, counts and a filter box; a Calendar tab with a Monday-first month grid (prev/today/next, my or all tasks, +N more folding, phone agenda); Inbox tabs Needs action/Unread/All with unread styling, Open task (marks read), Mark read and Mark all read"
outcome-why: "Gate 2 slice 6 in Aly's lock #10: people need to see what is due by when, on a list or a month, and an inbox that puts decisions first and shows what is unread"
outcome-resolves: FKVHH8 definition of done 1-5; Gate 2 slice 6 for X8FNA5/JQY55P
---

# Gate 2 slice 6: My Work groups and calendar month view, Inbox polish

## Definition of Done

- [x] My Work list groups open tasks into Overdue, Today, This week, Later and No date with counts, soonest first; each row opens the task panel; a good empty state
  proof: src/astra/static/app.js:482 WORK_GROUPS, :512 renderMyWork; test_web.AstraMyWorkInboxTests.test_my_work_lists_five_groups_with_counts_and_only_my_open_work, test_filter_keeps_empty_groups_and_says_when_nothing_matches
- [x] My Work has List and Calendar tabs (#/my-work and #/my-work/calendar); the calendar is a Monday-first month grid with previous, next and today, shows due tasks on their day, collapses more than 3 per day into '+N more', and every item opens the task panel; month kept in the link
  proof: src/astra/static/app.js:534 calendarMonth; test_month_grid_starts_on_monday_marks_today_and_folds_busy_days, test_month_links_keep_scope_and_the_route_reads_month; shots slice6-owner-my-work-calendar-*.png, slice6-owner-calendar-day-expanded-*.png
- [x] On a phone the calendar becomes an agenda list of the month's days that have work; no page-level sideways scroll
  proof: src/astra/static/style.css:707 phone rule; test_phone_agenda_lists_only_days_with_work; slice6-*-my-work-calendar-390.png, page overflow 0 at 390/1024/1440
- [x] Inbox: tabs Needs action (owners only), Unread and All with counts; unread rows are styled distinctly; each row can open its task and be marked read; Mark all read; owners see requests first with live Approve/Reject
  proof: src/astra/static/app.js:1071 inboxTab, :1095 renderInbox; test_inbox_tabs_for_a_member, test_inbox_puts_owner_requests_first; wiring tests (inbox-decision-*) still pass
- [x] Behaviour tests (grouping, month grid, +N collapse, agenda, inbox tabs), full suite, git diff --check, 0 CR, node --check, jaira validate; Chromium 1440/1024/390 as owner and member, no CSP errors; README, handoff and CLAUDE.md test figure updated
  proof: tests/run.py: Ran 498 tests OK; git diff --check clean; 0 CR; node --check OK; jaira validate 0 errors (36 pre-existing warnings); 38 screenshots lock10-shots/slice6-* owner/member/empty, no CSP or page errors; README, CLAUDE_HANDOFF_2026-09-24.md and CLAUDE.md updated

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Decide the rules: This week = due in 1-7 days, the same rule Home uses; the calendar shows open tasks by due_date, mine by default with a scope select (mine / everything I can see); month and scope ride in the link (?month=YYYY-MM&scope=all)
- [x] app.js My Work: tabs List | Calendar; renderMyWork always shows the five groups with counts (an empty group says so in one line), soonest first, a search box that filters the groups without redrawing the box
- [x] app.js calendar: pure calendarMonth(tasks, year, month, todayKey, scope) returning a Monday-first grid of whole weeks (4 to 6 rows) plus an agenda list; more than 3 items in a day collapse to a '+N more' button that expands that day; prev/next/today links; items are data-detail buttons
- [x] app.js Inbox: tabs Needs action (owners) / Unread / All via ?tab=; requests first; notification rows grouped Today / Yesterday / Earlier with unread styling, Open task (marks read) and Mark read; keep #inbox-error, #read-all and per-button listeners for the wiring driver
- [x] style.css: my-work tabs reuse .tabs; calendar grid (7 columns, today ring, out-of-month days dimmed, due tone chips); phone rule swaps the grid for the agenda; inbox rows (unread bar and dot)
- [x] Tests: SHELL_DRIVER mode 'work' for grouping, the month grid (Monday start, today, +N, agenda, escaping, month links) and inbox tabs; README; full suite and checks; screenshots slice6-* at 1440/1024/390 as owner and member; handoff and CLAUDE.md figures

## Progress
- **2026-09-25 08:39 · Claude** — Plan choices: calendar and inbox tabs are links (route-driven, like the project tabs) rather than ARIA tablists, so Back works and a link can be shared. The phone agenda is rendered alongside the grid and CSS shows one of them, so there is no width detection in JS. 'Hide done' from research 6.1 and 'Undo mark read' from 6.3 are left out: My Work lists open work only, and Aly ruled Undo out of these slices.
- **2026-09-25 08:53 · Claude** — Found while building: app.js already had a function renderCalendar (the project working-days dialog, about line 1800). A second declaration with the same name is silently replaced by the later one, so the month view first drew nothing and threw in the browser. The month view's entry point is workCalendar. Screenshots used a copy of the lock #9 demo database (scratchpad l10cal, port 8797) with extra tasks due 2026-09-30 so the '+N more' fold shows; the shared demo on 8795 was not changed.
