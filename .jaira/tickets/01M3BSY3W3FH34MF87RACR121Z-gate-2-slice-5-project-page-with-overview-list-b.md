---
id: 01M3BSY3W3FH34MF87RACR121Z
title: "Gate 2 slice 5: project page with Overview, List, Board, Timeline and Activity tabs"
status: signoff
ready: true
creator: Claude
assignee: Claude
goal: "Each project has its own page with tabs Overview, List, Board, Timeline and Activity, one link per tab, so a project can be read as facts, a list, a status board, a Gantt or its history. The board is read-only and can be divided into swimlanes."
context: |-
  What is wrong today (after slice 4, VPYGY5):
  - A project has no page. The Projects list opens the portfolio timeline filtered to one project.
  - There is no board. The Gantt and schedule table exist only portfolio-wide (#/portfolio). Project history is a dialog in the More menu.
  Trigger: Aly's lock #10 (Slack ts 1790322792.679739, 2026-09-25) for Gate 2 slices 4-6.
  Aly's decisions for the board: read-only; today's 11 statuses (service.py STATUSES, about lines 25-28) mapped into 7 columns; swimlanes ('divide by') are in scope; no drag and drop, Undo, bulk select or WIP limits.
  Column mapping (also in README): Draft = draft; Ready = assigned; In progress = in_progress, reopened, changes_requested, delayed; Blocked = on_hold, or any open task waiting on an unfinished predecessor (is_blocked); Submitted = submitted; Accepted = completed; Closed = cancelled, abandoned. Submitted wins over blocked; closed statuses win over everything. Accepted and Closed are Owner-decided and start collapsed.
  Spec: session file ux-research.md slice 5 rows 5.1-5.8; design frame gate2-f-board.png; artifact FwmJpbSwLzoL3aZxFpQKr7.
  Reuse: List = the schedule table renderer, Timeline = the Gantt renderer, Activity = the project events renderer (GET /api/projects/<id>/events). No server change.
  Divide by: none, owner or criticality. Entity is not offered on a project page: every task of one project shares that project's entities.
definition-of-done: "Route #/project/<id>/<tab> with tabs Overview, List, Board, Timeline and Activity (links, current tab marked); unknown or inaccessible projects show a clear empty state; Projects rows link into it"
tags:
  - astra
blocked-by: []
related:
  - 01M2JHKHPFGHBYXK2FFDX8FNA5
  - 01M2WNN5PQXBBCD0XTZGJQY55P
  - 01M3BS57ZY3F4GP2D6K1VPYGY5
commits: []
created-at: 2026-09-25T08:12:00Z
updated-at: 2026-09-25T09:52:59Z
updated-by: Claude
claimed-by: vm-4417
claimed-at: 2026-09-25T08:12:20Z
outcome-what: "Each project has a page at #/project/<id>/<tab>: Overview (facts, progress, next due), List (the schedule table), Board (read-only, 11 statuses in 7 columns, Accepted/Closed collapsed as Owner-decided, Divide by owner or criticality kept in the link), Timeline (the Gantt) and Activity (project history), with Add a task and owner-only Save as template and Close project. Cards, rows and bars open the task panel; Projects rows link to the page. The Gantt nodes move between the portfolio and the project page instead of being duplicated."
outcome-why: "A project had no page, no board and no scoped Gantt; project history was a dialog. Aly decided the board is read-only with the 11 statuses mapped into 7 columns and swimlanes in scope (lock #10)."
outcome-resolves: "All five DoD items ticked with proof; Ran 490 tests, OK; Chromium 1440/1024/390 as owner and member without CSP errors or page-level sideways scroll."
review-summary: "Review 10 (2026-09-25, session file lock10-review.md) of 15562d8/90c650f/6e9d079 on 79d350d: approve with follow-ups, no High. Security held (owner-only items hidden and refused server-side for member, manager and chairman; every new text sink escaped; CSV formula guard), tile counts matched their lists and the export, all 11 statuses map to a column, board columns line up at every width. Two Mediums: M1 'today' on the Home strip and the calendar came from the browser's clock while due states use the project's timezone; M2 the This week strip covered days 0-6 while its link and the tile cover 0-7. Lows L1-L8 (unread-row link contrast, phone tap targets, 5 missed test experiments, unknown export risk named in the filename, stretched Home cards and repeated 'as of', UNRATED on every card, double portfolio fetch, an unused variable and an un-normalised project tab). All fixed in 7bfa045ea033dd3001c6e083d0fa9b01cbad9276 with behaviour tests where testable; Ran 503 tests, OK."
review-gaps: "Left for later: I2 Divide by owner groups by display name, so two people with the same name share a lane (group by owner_user_id); the Home strip counts use each project's own timezone while its labels use the app timezone (Asia/Karachi), so a project in a far timezone can differ by a day at the edges; Divide by entity, a project Activity filter and 'since Monday' tile deltas are not built; the Gantt 'today' line and the portfolio 'As of' still read the browser clock (outside these slices); slice 7 (phone and accessibility pass) remains. The fix commit was not re-reviewed."
review-verdict: "approve with follow-ups; M1-M2 and L1-L8 fixed in 7bfa045ea033dd3001c6e083d0fa9b01cbad9276, not re-reviewed"
review-check: "1. Windows, repo root: .venv\\Scripts\\python.exe tests\\run.py; expect 'Ran 503 tests' and 'OK'. 2. Sign in as the owner, open Projects and click a project: its page opens on Overview with tabs Overview, List, Board, Timeline, Activity. 3. Click Board: 7 columns (Draft, Ready, In progress, Blocked, Submitted, Accepted, Closed); Accepted and Closed are narrow and show a lock. 4. Set Divide by to Owner: each person gets a lane, and every lane's columns sit exactly under the column headers; scroll the board sideways: the lane names stay at the left. 5. A card without a criticality shows no 'Unrated' badge. 6. Click a card title: the task opens in the side panel. 7. Edit the address to end in /nope and press Enter: Overview opens and the address changes to /overview. 8. Sign in as a member: Save as template and Close project are not shown."
---

# Gate 2 slice 5: project page with Overview, List, Board, Timeline and Activity tabs

## Definition of Done

- [x] Route #/project/<id>/<tab> with tabs Overview, List, Board, Timeline and Activity (links, current tab marked); unknown or inaccessible projects show a clear empty state; Projects rows link into it
  proof: app.js parseRoute (PROJECT_TABS, UUID id, tab defaults to overview), renderProject tab links with aria-current, 'This project is not available' state; renderProjects rows link to #/project/<id>/overview; test_web AstraProjectPageTests.test_project_routes_tabs_and_actions
- [x] Board: 7 read-only columns from the documented mapping with counts; cards show title, owner initials, due chip, state glyphs and steps done; Accepted and Closed start collapsed with 'Owner decides'; a Divide by control (none, owner, criticality) kept in the link; cards open the task panel
  proof: app.js boardColumn (mapping in the ticket context and README), renderBoard (7 columns with counts, top-level cards, steps counted on the parent, Accepted/Closed collapsed with toggle and 'Owner decides', Divide by none/owner/criticality kept as ?divide=), delegated clicks open the panel; test_statuses_map_into_seven_columns, test_board_cards_columns_and_collapsed_owner_columns, test_divide_by_owner_and_criticality; lock10-shots/slice5-*-board*.png
- [x] List reuses the schedule table and Timeline reuses the Gantt, both scoped to the project; Activity reuses the project history; Overview shows project facts, progress and dates; rows and bars open the task panel
  proof: renderProject: list/timeline mountGantt(#project-gantt-slot) with the table or chart forced and the project's tasks; activity from /api/projects/<id>/events via renderProjectEvent; projectOverview (facts, progress, next due); portfolio render() takes #gantt-host back (Chromium: portfolio Gantt rows after visiting the project); lock10-shots/slice5-owner-{list,timeline,activity,overview}-*.png
- [x] Project actions on the page: Capture into this project; Save as template and Close project for owners only
  proof: #project-capture -> openCapture(id); #project-save-template -> saveProjectAsTemplate(id) and #project-close -> closeProject(id) owner-only (shared with the More menu); test_project_routes_tabs_and_actions (member [False, True, True], owner all shown)
- [x] Behaviour tests (column mapping, lanes, collapsed columns, escaping, route parse), full suite, git diff --check, 0 CR, node --check, jaira validate; Chromium 1440/1024/390 as owner and member, no CSP errors, no page-level sideways scroll; README with the column mapping
  proof: Ran 490 tests, OK (486 before); git diff --check clean; 0 CR; node --check ok; Chromium 1440/1024/390 as owner and member: no CSP errors, no page-level sideways scroll (the board scrolls inside itself); README project page and column mapping

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Router: parseRoute returns a tab; project routes need a UUID id; NAV_OF marks Projects; applyRoute renders renderProject
- [x] index.html: project view with a header (name, facts line, actions) and tab links, a body and a slot; the Gantt controls, bands, chart and table sit in one #gantt-host that moves between the portfolio panel and the project slot (listeners stay on the nodes)
- [x] app.js: renderProject (overview, board, activity, list/timeline via mountGantt with a view override); boardColumn mapping; renderBoard with lanes and collapsed columns; refreshGantt so resize and the view toggle re-render the right screen
- [x] Refactor closeProject(pid) and saveProjectAsTemplate(pid) so the page and the More menu share them; openCapture(pid)
- [x] style.css board (flex columns, fixed widths, scroll inside the board, scroll-snap on phones), tabs, overview
- [x] Tests: node driver for boardColumn and renderBoard (lanes, collapsed, escaping), parseRoute project cases; README; screenshots

## Progress
- **2026-09-25 08:12 · Claude** — Plan reasoning (Claude, 2026-09-25): (1) The Gantt renderer and its listeners are bound to #gantt/#schedule-table, so the project page moves the same nodes (one #gantt-host) into its slot instead of copying the renderer; the portfolio moves them back when it renders. (2) The board lists top-level tasks only; steps show as 'Steps n of m' on their parent card, so a card never appears twice. (3) Columns are flex items with fixed widths (no inline styles under the CSP), so collapsed columns line up across swimlanes. (4) Divide by lives in the link (?divide=owner) like the portfolio filters.
- **2026-09-25 08:27 · Claude** — Found while building (Claude, 2026-09-25): (1) the cards' sr-only owner text is position:absolute; inside the horizontally scrolling board it escaped the scroller and made the whole page 997px wide on phones; .board is now position:relative. (2) Collapsed columns are 128px so name, count and lock fit on one line and the header row stays short. (3) Members see 'Add a task' like the rail Capture; the server decides whether they may create. Not built: an Activity filter by person or type (research 5.8), Divide by entity (one project shares its entities).
- **2026-09-25 08:32 · Claude** — Coordinator review: with Divide by = Owner the lane cells drifted out from under the column headers. Cause: .board-cols had min-width:max-content, so each lane row sized itself to its own unwrapped card titles and its fr tracks grew differently from the header's. Fix: one template for header and every lane, repeat(7, minmax(180px,1fr)) with a fixed row min-width (1332px; 1280/1228 with Accepted/Closed collapsed to 128px), the board scrolls sideways inside its own container. Measured with Playwright at 1440/1024/390: every row's column left+width identical, no page overflow. Also: lane names stick to the left edge while scrolling, and long 'Waits on' tags wrap inside the card.
- **2026-09-25 09:48 · Claude** — Review 10 follow-ups (fix commit): L6, unrated cards no longer carry an UNRATED badge (the panel still flags it); L3, lane names are tested for escaping and the sticky lane rule is asserted; L2, card titles are 44px targets below 1024px; L8, an unknown tab (#/project/<id>/nope) is rewritten to /overview with replaceState.
