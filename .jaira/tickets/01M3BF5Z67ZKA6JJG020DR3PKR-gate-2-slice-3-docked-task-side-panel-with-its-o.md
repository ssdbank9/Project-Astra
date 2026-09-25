---
id: 01M3BF5Z67ZKA6JJG020DR3PKR
title: "Gate 2 slice 3: docked task side panel with its own link"
status: signoff
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
updated-at: 2026-09-25T07:13:06Z
updated-by: Claude
claimed-by: vm-9335
claimed-at: 2026-09-25T05:04:22Z
outcome-what: "Task detail is now a panel docked on the right (460px, non-modal, the screen behind moves over and stays usable) instead of a modal dialog. It has its own link: ?task=<id> over the current screen or #/task/<id> as a full page, both surviving reload and Back/Forward, with Copy link and Open full page. Esc or x closes it (a first Esc only leaves a text field), focus moves into it on open and back to the opener on close, j/k step through the tasks of the screen behind, and below 1024px it is a full-screen sheet. It opens on project and status, the title, state chips with glyphs, a role line, six facts and section links, then the one Lifecycle block with today's button names. After review 9: Review 9 fixes: sign-out reloads the page; the task panel sits below the top bar and is 380px at 1024-1279px; a filter picked with the panel open survives closing; malformed or non-id links are ignored and a failed load is not a sign-out; no page-wide single-key shortcuts (j/k only in the panel); Esc in a panel field keeps focus in the panel; j/k follow the screen's order; 44px phone targets; each fact shown once, steps and dependencies before Lifecycle; More menu is a sheet on phones; one muted grey token; action toasts stay until used; Clear all beside the chips; page title Home."
outcome-why: "The modal dialog blocked the Gantt, My Work and Inbox while a task was open, a task had no link, and the lifecycle actions sat halfway down. Aly asked for the Gate 2 docked panel (X8FNA5, lock #9); the design reference relayed by the coordinator set the anatomy. After review 9: Independent review 9 returned request changes (session file lock9-review.md): a High cross-account leak on sign-out, the panel covering the top bar, a lost filter, a malformed-link sign-in loop, single-key shortcuts against WCAG 2.1.4, and missing behaviour tests."
outcome-resolves: "All five DoD items ticked with proof; Ran 472 tests, OK; Chromium checks at 1440/1024/390: reload, Back and Forward agree with the panel, Esc returns focus to the opener, no sideways scroll, no CSP errors. After review 9: All DoD items ticked with corrected proofs; Ran 482 tests, OK; Chromium at 1440/1024/390: owner signs out and a member signs in with none of the owner's Inbox or panel on screen, account menu and search usable with a task open, filters kept, no CSP errors, no sideways scroll."
review-summary: "Review 9 (2026-09-25) of 91bc390/08b926c/cf44fb6: request changes (H1 sign-out leak, M1-M5, L1-L10). Fixed in c47062be15677f357a4e25a8fafbd73e69f0ccf5. Focused re-review of c47062b (session file lock9-rereview.md): approve with follow-ups; H1 and M1-M5 fixed with behaviour tests, three small new defects N1 (action toast followed you across screens), N2 (copy-link fallback toast timed out), N3 (44px targets only on phones). N1-N3 fixed in 03acafcf3ffccca9cce65495a4045abf1a3cc2eb with tests; Ran 484 tests, OK."
review-verdict: "approve with follow-ups; review 9 request changes fixed in c47062be15677f357a4e25a8fafbd73e69f0ccf5, re-review approve with follow-ups, N1-N3 fixed in 03acafcf3ffccca9cce65495a4045abf1a3cc2eb, not re-reviewed"
review-gaps: "Left for later: L4 and L5 partial (1024px screen behind the 380px panel is still about 516px; the Gantt legend orphans an item); the pre-existing Gantt project-flag contrast (.proj-flag, white on #d1495b, 4.36:1); Open full page still shown on phones where the panel is already full screen; a Manage rail entry so Import and Templates are reachable outside Home (later slice); no favicon (404 in the console)."
review-check: "1. Windows, repo root: .venv\\Scripts\\python.exe tests\\run.py; expect 'Ran 484 tests' and 'OK'. 2. Start Astra and sign in as the primary owner: a left rail (Home, My Work, Inbox, Projects, Capture) and a top bar with search and your initials. 3. On Home pick Criticality: Low and Open work only: chips appear under the filters with 'Showing X of Y' and Clear all; reload the page: the filters are still set. 4. Click a task link in the Gantt: it opens in a panel on the right, the Gantt stays usable, the top bar is still visible; press Esc: the panel closes and focus is back on the link. 5. Open a task, click Copy link, paste the link in a new tab: the same task opens. 6. Open Inbox with a task open, then Sign out from the account menu and sign in as a member: none of your Inbox or the task is on screen. 7. Resize to phone width: the rail is a bottom bar and a task fills the screen."
---

# Gate 2 slice 3: docked task side panel with its own link

## Definition of Done

- [x] Task detail opens in a right-side panel (about 460px, non-modal) while the current screen stays visible and scrollable; clicking another task swaps the panel
  proof: index.html <aside id=detail-dialog class=task-panel>; style.css: at >=1024px the panel sits below the 60px top bar (top: var(--topbar-h), top bar z-index above the panel) and main is padded, so search and the account menu stay usable (review 9 M1, fixed in the review 9 fix commit (lock #9)); 380px wide at 1024-1279px (L5). Chromium: at 1440 and 1024 elementFromPoint on the avatar hits the avatar with a task open and the account menu opens over the panel (lock9-fix-shots/panel-account-menu-*.png). test_web AstraTaskPanelTests.test_panel_markup_order_and_layout, test_opening_adds_the_task_to_the_link_and_swapping_replaces_it
- [x] The panel has its own link: ?task=<id> over the current screen and #/task/<id> as a full page; both survive reload and Back/Forward; Copy link copies it
  proof: app.js openPanel/closePanel/routeHash/taskLink/taskApi; a filter picked while the panel is open now survives closing it (syncFilters clears panelState.pushed; review 9 M2, fixed in the review 9 fix commit (lock #9)); malformed or non-id task links open nothing (M3, L1). Chromium: reload keeps the panel, Back closes it, Forward reopens it; crit=critical kept after close at 1440 and 1024. test_web AstraTaskPanelTests.test_a_filter_picked_while_the_panel_is_open_survives_closing_it, test_task_ids_from_a_link_are_checked_and_fetched_fresh, test_the_task_page_is_the_same_panel_and_closes_to_the_last_screen
- [x] Esc and a close button close it; focus moves into the panel when it opens and returns to the control that opened it; a first Esc in a panel field keeps focus in the panel; everything in it is keyboard reachable; j/k move to the next or previous task while focus is in the panel
  proof: app.js panel keydown; Chromium: Esc in a field focuses #detail-heading, a second Esc closes and focus returns to the Gantt link; j inside the panel steps to the next task on the screen (DOM order). test_web AstraTaskPanelTests.test_closing_goes_back_and_returns_focus_to_the_opener (opener and re-rendered opener), test_keys_inside_and_outside_the_panel
- [x] Header shows title, state chips (tint + dark text + glyph), a role line and a compact fact grid, then description, steps and dependencies, then one Lifecycle block with today's button names; each fact shown once; below 1024px the panel is full-screen
  proof: app.js renderDetail (review 9 L6: status once as a chip, criticality once as a fact, critical path once as a chip, Steps fact; order desc, steps, deps, lifecycle, reviewers); style.css @media (max-width: 1023px); lock9-fix-shots/panel-*.png; test_panel_markup_order_and_layout, test_state_chips_carry_a_glyph_or_word
- [x] Pinned ids (#detail-dialog, #detail-body, #detail-edit, #add-dep-button) keep working and the Inbox refresh on close still works; tests for the new behaviour; full suite green; git diff --check, 0 CR bytes, node --check, jaira validate; Chromium screenshots 1440/1024/390 with no CSP errors; README, handoff and CLAUDE.md test count updated
  proof: Ran 482 tests, OK after the review 9 fix commit (lock #9) (472 before it); wiring and status-gate tests unchanged and passing; git diff --check clean; 0 CR bytes; node --check ok; jaira validate errors false; Chromium 1440/1024/390 no CSP errors, no sideways scroll (lock9-fix-shots/); README, handoff 482, CLAUDE.md 482

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] index.html: replace <dialog id=detail-dialog> with <aside id=detail-dialog class=task-panel hidden> inside main: a bar with Task label, Copy link, Open full page and a close button, then #detail-body
- [x] app.js: openDetail renders then openPanel(id) (remember the opener, show the panel, add ?task=<id> with a history entry, focus the heading on a new task); closePanel dispatches a 'close' event (keeps the Inbox refresh), restores focus, and goes Back when it added the entry, else strips the param; applyRoute opens or closes the panel from the link; #/task/<id> is the full-page mode; filter edits keep the task param
- [x] app.js renderDetail header: crumb (project), h2#detail-heading, state chips, role line from permissions, 6 facts (Owner, Start, Due, Criticality, Progress, Steps), section jump buttons, closed note, then description, steps, dependencies and the Lifecycle block (reordered after review 9 L6)
- [x] Keys: Esc closes (a first Esc only leaves a text field), j/k step through the current screen's tasks with replaceState; ? list gains j/k
- [x] style.css: panel (460px fixed, slide-in, pushes main at >=1024px, full-screen below), page mode, tags, role line, section buttons; remove the old detail dialog rules
- [x] Tests: node panel driver (link parse, open adds ?task, close strips it and fires close), static asserts; wiring and status-gate tests keep passing; browser checks; docs; move to review; commit
- [x] Review 9 fixes: sign-out reload (H1), panel below the top bar (M1), filter kept on close (M2), malformed/non-id links (M3, L1), j/k only in the panel (M4), Esc in a field (L2), j/k in screen order (L3), 44px phone targets (L4), 380px at 1024-1279 (L5), no duplicated facts (L6); behaviour tests in the shared node driver
  proof: review 9 fix commit (lock #9); test_web AstraTaskPanelTests (9 tests)

## Progress
- **2026-09-25 05:04 · Claude** — Plan reasoning (Claude, 2026-09-25): the aside keeps the id detail-dialog so the pinned tests and the Inbox-refresh listener keep working; closing dispatches a 'close' event like a dialog would. Opening assigns the hash (a history entry) so Back closes the panel; closing goes Back only when this session added that entry, otherwise (arrived by link) it strips the param with replaceState so Back never leaves the app. j/k use replaceState so stepping through tasks does not flood history. Below 1024px the panel is a full-screen sheet over the page rather than a route change, so the link stays the same at every width.
- **2026-09-25 05:17 · Claude** — Findings while building (Claude, 2026-09-25): (1) the task detail record has no is_critical_path, is_blocked or days_to_due (only the list computes them), so the panel reads those three from the loaded list; without that a critical-path task said 'Critical path: No'. (2) Opening a panel changed the hash and re-rendered the Gantt, which replaced the opener; applyRoute now skips the view render when only the task param changed, and the opener is also kept as a selector so focus finds its replacement after a save. (3) Two-column form grids overflowed a 460px panel (inputs keep an intrinsic width); .grid now uses minmax(0, 1fr) and inputs min-width: 0. Not built: inline click-to-edit of fields (research 3.5, left for Gate 3 with the other inline edits).
- **2026-09-25 06:10 · Claude** — Review 9 (request changes) fixed in one commit (Claude, 2026-09-25): H1 sign-out now reloads the page (location.replace(location.pathname)) so the next person on the browser gets a fresh app; the first load after sign-in also re-fetches a linked task. M1 panel below the 60px top bar with the top bar above it. M2 syncFilters clears panelState.pushed. M3 parseRoute never throws; only a failed /api/me shows sign-in. M4 no page-wide single-key shortcuts; j/k only with focus in the panel; the key list is in the account menu. M5 behaviour tests in one shared node driver (SHELL_DRIVER) plus a token contrast test. L1-L10 as listed in the review. Not changed: Open full page still shows on phones (I1), a Manage rail entry (L7 second half) stays for a later slice.
