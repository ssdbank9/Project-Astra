---
id: 01M3BF5Z67ZKA6JJG020DR3PKR
title: "Gate 2 slice 3: docked task side panel with its own link"
status: review
ready: true
creator: Claude
assignee: Claude
goal: "A task opens in a panel docked on the right while the screen behind stays visible and usable. The panel has its own link that survives reload and Back/Forward, closes with Esc or a close button, returns focus to what opened it, and becomes full-screen on narrow screens."
context: |-
  What is wrong today (after slices 1 and 2, 4T4DEA and PZTYC9):
  - Task detail is a modal <dialog id="detail-dialog">. It blocks the page, so you cannot look at the Gantt, My Work or the Inbox while reading a task.
  - A task has no link. Reload or a shared URL loses it.
  - The dialog opens with Project, Owner, Parent, Revision and Due state; the lifecycle actions sit halfway down, after criticality, schedule and steps.
  Aly's decisions (lock #9, Slack thread ts 1790256175.671249): docked side panel (X8FNA5 'docked panel'), keep Approve/Reject live, plain HTML/CSS/JS, minimal diff.
  Coordinator relay of the design reference (session file ux-research.md rows 3.1-3.5, 3.4b, 3.4c; design artifact FwmJpbSwLzoL3aZxFpQKr7): about 460px non-modal panel; view stays visible; Esc and x close; focus returns to the opener; shareable link that reopens it; Copy link; full page below 1024px; header = title + state chips (tint + dark text + glyph), a role line, a compact fact grid, then ONE lifecycle block keeping today's button names; j/k to move between tasks only if cheap.
  Constraints from tests/test_web.py: keep ids #detail-dialog, #detail-body, #detail-edit and #add-dep-button; the lifecycle block must stay before the reviewers block; the wiring test calls the 'close' listeners of #detail-dialog to check that closing a task opened from the Inbox refreshes the Inbox only when something was saved.
  Out of scope: inline editing on cards or rows (Gate 3), the Board (slice 5).
definition-of-done: "Task detail opens in a right-side panel (about 460px, non-modal) while the current screen stays visible and scrollable; clicking another task swaps the panel"
tags:
  - astra
blocked-by: []
related:
  - 01M2JHKHPFGHBYXK2FFDX8FNA5
  - 01M2WNN5PQXBBCD0XTZGJQY55P
  - 01M3BE0B99E7TFPEA6MAPZTYC9
commits: []
created-at: 2026-09-25T05:04:03Z
updated-at: 2026-09-25T05:17:16Z
updated-by: Claude
claimed-by: vm-9335
claimed-at: 2026-09-25T05:04:22Z
outcome-what: "Task detail is now a panel docked on the right (460px, non-modal, the screen behind moves over and stays usable) instead of a modal dialog. It has its own link: ?task=<id> over the current screen or #/task/<id> as a full page, both surviving reload and Back/Forward, with Copy link and Open full page. Esc or x closes it (a first Esc only leaves a text field), focus moves into it on open and back to the opener on close, j/k step through the tasks of the screen behind, and below 1024px it is a full-screen sheet. It opens on project and status, the title, state chips with glyphs, a role line, six facts and section links, then the one Lifecycle block with today's button names."
outcome-why: "The modal dialog blocked the Gantt, My Work and Inbox while a task was open, a task had no link, and the lifecycle actions sat halfway down. Aly asked for the Gate 2 docked panel (X8FNA5, lock #9); the design reference relayed by the coordinator set the anatomy."
outcome-resolves: "All five DoD items ticked with proof; Ran 472 tests, OK; Chromium checks at 1440/1024/390: reload, Back and Forward agree with the panel, Esc returns focus to the opener, no sideways scroll, no CSP errors."
---

# Gate 2 slice 3: docked task side panel with its own link

## Definition of Done

- [x] Task detail opens in a right-side panel (about 460px, non-modal) while the current screen stays visible and scrollable; clicking another task swaps the panel
  proof: index.html <aside id=detail-dialog class=task-panel> inside main; style.css .task-panel 460px fixed, .panel-open main padding-right at >=1024px; Chromium 1440: panel x=980 w=460 with main content still usable; clicking another task swaps (replaceState); test_web AstraTaskPanelTests.test_opening_adds_the_task_to_the_link_and_swapping_replaces_it
- [x] The panel has its own link: ?task=<id> over the current screen and #/task/<id> as a full page; both survive reload and Back/Forward; Copy link copies it
  proof: app.js openPanel/closePanel/routeHash/taskLink, applyRoute opens the panel from ?task= or #/task/<id>; Chromium: reload keeps the panel, Back closes it, Forward reopens it, Copy link puts http://host/#/task/<id> on the clipboard (toast 'Link to this task copied.'); test_web AstraTaskPanelTests (link, back, replace, page mode)
- [x] Esc and a close button close it; focus moves into the panel when it opens and returns to the control that opened it; everything in it is keyboard reachable; j/k move to the next or previous task
  proof: app.js panel keydown (Esc closes; first Esc only leaves a field; j/k stepPanel), #detail-close, focus to #detail-heading on open and back to the opener on close (openerKey re-finds a re-rendered opener); Chromium: Esc returns focus to the Gantt link at 1440/1024/390, j/k move between tasks, Tab reaches the section links and forms; test_panel_markup_keys_and_layout
- [x] Header shows title, state chips (tint + dark text + glyph), a role line and a compact fact grid, then one Lifecycle block with today's button names; below 1024px the panel is full-screen
  proof: app.js renderDetail: panel-crumb, h2#detail-heading, stateTags (tint + dark text + glyph), roleLine(perms), six facts, section jump buttons, Lifecycle moved up (one block, today's names); style.css @media (max-width: 1023px) full-screen sheet; lock9-shots/slice3-panel-{1440,1024,390}.png, slice3-task-page-*.png; test_state_chips_carry_a_glyph_or_word
- [x] Pinned ids (#detail-dialog, #detail-body, #detail-edit, #add-dep-button) keep working and the Inbox refresh on close still works; tests for the new behaviour; full suite green; git diff --check, 0 CR bytes, node --check, jaira validate; Chromium screenshots 1440/1024/390 with no CSP errors; README, handoff and CLAUDE.md test count updated
  proof: Ran 472 tests, OK (466 before); ARZWV7 status-gate and wiring tests pass unchanged (lifecycle still before reviewers; close listeners of #detail-dialog still refresh the Inbox); git diff --check clean; 0 CR bytes; node --check ok; jaira validate errors false; Chromium 1440/1024/390 no sideways scroll and no CSP errors; README task panel bullet; handoff lock #9 and 472; CLAUDE.md 472

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] index.html: replace <dialog id=detail-dialog> with <aside id=detail-dialog class=task-panel hidden> inside main: a bar with Task label, Copy link, Open full page and a close button, then #detail-body
- [x] app.js: openDetail renders then openPanel(id) (remember the opener, show the panel, add ?task=<id> with a history entry, focus the heading on a new task); closePanel dispatches a 'close' event (keeps the Inbox refresh), restores focus, and goes Back when it added the entry, else strips the param; applyRoute opens or closes the panel from the link; #/task/<id> is the full-page mode; filter edits keep the task param
- [x] app.js renderDetail header: crumb (project · status), h2#detail-heading, state chips, role line from permissions, 6 facts (Owner, Start, Due, Criticality, Progress, Critical path), section jump buttons, closed note, then the Lifecycle block moved up; the rest unchanged
- [x] Keys: Esc closes (a first Esc only leaves a text field), j/k step through the current screen's tasks with replaceState; ? list gains j/k
- [x] style.css: panel (460px fixed, slide-in, pushes main at >=1024px, full-screen below), page mode, tags, role line, section buttons; remove the old detail dialog rules
- [x] Tests: node panel driver (link parse, open adds ?task, close strips it and fires close), static asserts; wiring and status-gate tests keep passing; browser checks; docs; move to review; commit

## Progress
- **2026-09-25 05:04 · Claude** — Plan reasoning (Claude, 2026-09-25): the aside keeps the id detail-dialog so the pinned tests and the Inbox-refresh listener keep working; closing dispatches a 'close' event like a dialog would. Opening assigns the hash (a history entry) so Back closes the panel; closing goes Back only when this session added that entry, otherwise (arrived by link) it strips the param with replaceState so Back never leaves the app. j/k use replaceState so stepping through tasks does not flood history. Below 1024px the panel is a full-screen sheet over the page rather than a route change, so the link stays the same at every width.
- **2026-09-25 05:17 · Claude** — Findings while building (Claude, 2026-09-25): (1) the task detail record has no is_critical_path, is_blocked or days_to_due (only the list computes them), so the panel reads those three from the loaded list; without that a critical-path task said 'Critical path: No'. (2) Opening a panel changed the hash and re-rendered the Gantt, which replaced the opener; applyRoute now skips the view render when only the task param changed, and the opener is also kept as a selector so focus finds its replacement after a save. (3) Two-column form grids overflowed a 460px panel (inputs keep an intrinsic width); .grid now uses minmax(0, 1fr) and inputs min-width: 0. Not built: inline click-to-edit of fields (research 3.5, left for Gate 3 with the other inline edits).
