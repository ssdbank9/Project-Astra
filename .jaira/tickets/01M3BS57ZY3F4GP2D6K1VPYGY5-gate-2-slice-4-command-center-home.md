---
id: 01M3BS57ZY3F4GP2D6K1VPYGY5
title: "Gate 2 slice 4: Command Center Home"
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Home answers 'what needs me now' at a glance: a health strip whose tiles open the matching filtered list, the Owner's pending decisions with working Approve/Reject, at-risk work, my next actions, this week's load and the portfolio by entity. The Portfolio Gantt and schedule table stay one click away."
context: |-
  What is wrong today (after lock #9, head 79d350d):
  - Home is the old dashboard: 4 counters, a 9-control filter bar and the Portfolio Gantt. Nothing says what needs a decision or what is at risk.
  - Owner decisions live only on the Inbox page. Portfolio by entity is a dialog in the More menu.
  Trigger: Aly granted exclusive lock #10 for Gate 2 slices 4-6 (Slack ts 1790322792.679739, 2026-09-25).
  Spec: session file ux-research.md slice 4 rows 4.1-4.4 and the empty-state row X.1; design frame gate2-f-home.png; design artifact FwmJpbSwLzoL3aZxFpQKr7.
  Aly's decisions: Approve/Reject stay live (not placeholders); plain HTML/CSS/JS, reuse existing endpoints and renderers, minimal diff, no new dependency.
  Plan decision: the old filtered dashboard (summary, filters, Portfolio Gantt, schedule table, More menu) moves to its own screen #/portfolio ('Portfolio timeline', under Projects). Old #/home?<filters> links redirect there. The tiles link into it.
  Known limits: the design's 'since Monday' deltas and consequence chips need history or impact data the server does not return; not built.
  Out of scope: project tabs and board (slice 5), My Work/Inbox/Calendar (slice 6), drag and drop, Undo, bulk select, WIP limits, workload (dropped by Aly).
definition-of-done: "Home shows a health strip (Overdue, Blocked, Awaiting Owner for owners only, Due in 7 days, Critical path, Undated); each tile states its definition and time and opens the matching filtered list"
tags:
  - astra
blocked-by: []
related:
  - 01M2JHKHPFGHBYXK2FFDX8FNA5
  - 01M2WNN5PQXBBCD0XTZGJQY55P
  - 01M3BF5Z67ZKA6JJG020DR3PKR
commits: []
created-at: 2026-09-25T07:58:25Z
updated-at: 2026-09-25T09:48:07Z
updated-by: Claude
claimed-by: vm-1430
claimed-at: 2026-09-25T07:58:42Z
outcome-what: "Home is the Command Center: six health tiles that each state their rule and time and open the matching filtered list (Awaiting Owner for owners only); Needs Owner decision with live Approve/Reject and Review; My next actions; At risk; a This week strip; Portfolio by entity; a clear empty state for a new install. The old dashboard (filters, Portfolio Gantt, schedule table, More menu) moved unchanged to #/portfolio under Projects, old #/home filter links redirect there, and a Risk filter plus 'No due date' back the tiles (also applied by Export CSV)."
outcome-why: "Home showed four counters and a long filter bar; nothing said what needed a decision or what was at risk. Aly granted lock #10 for Gate 2 slices 4-6 (Slack ts 1790322792.679739)."
outcome-resolves: "All six DoD items ticked with proof; Ran 486 tests, OK; Chromium 1440/1024/390 as owner, member and empty install without CSP errors or sideways scroll."
---

# Gate 2 slice 4: Command Center Home

## Definition of Done

- [x] Home shows a health strip (Overdue, Blocked, Awaiting Owner for owners only, Due in 7 days, Critical path, Undated); each tile states its definition and time and opens the matching filtered list
  proof: app.js homeTiles/renderHome: tiles link to #/portfolio?due=overdue&open=1, ?risk=blocked, #/inbox, ?due=7, ?risk=critical, ?due=undated, each with its definition, and one 'Counts as of HH:MM' for the row. Corrected after review 10: at 6e9d079 the This week card beside the tiles covered days 0-6 while its 'Due in 7 days' link and the tile covered 0-7 (M2); the fix commit makes the strip 8 bars (today + 7) that add up to the tile. Tests: test_home_command_center_for_owner_member_and_empty_install (counts, links, strip total = tile, day-7 task inside); lock10-fix-shots/slice-fix-owner-home-*.png
- [x] Needs Owner decision (owners only) lists pending requests with live Approve and Reject and a Review button that opens the task panel; hidden for everyone else
  proof: renderHome decisions from state.ownerRequests (cached by openInbox), data-home-decision buttons -> decideOwnerRequest(id,decision,'home-decision-error'), Review -> openDetail; hidden for non-owners; test_home_command_center... (buttons, click -> POST decision path and task fetch, escaping, member hidden)
- [x] At risk, My next actions (Today / This week / Later), a This week strip and Portfolio by entity; rows open the task panel
  proof: renderHome: My next actions (Today/This week/Later, This week = dueThisWeek, day 7 included), At risk (worst first), This week strip (today + next 7 days from the server's today), Portfolio by entity via portfolioCards, fetched once per Home visit; delegated click on #home-view opens the panel; test_home_command_center... (grouping, order, closed excluded, strip labels with the browser in Pacific/Pago_Pago, one /api/portfolio fetch)
- [x] The Portfolio Gantt and schedule table stay reachable at #/portfolio (linked from Home and Projects), old #/home filter links redirect there, and the new Risk filter and No due date option back the tiles
  proof: index.html data-view=portfolio holds the summary, filters, Portfolio Gantt, schedule table and More menu; Home and Projects link to it; applyRoute redirects #/home?<filters>; Risk filter + No due date (app.js matchesRisk/matchesBand; service.py export_tasks band=undated and risk; web.py risk key); test_filters_round_trip... (#/portfolio), test_home_command_center... (redirect), AstraWebTests.test_export_applies_the_home_tile_filters
- [x] A new install (no projects) and a member with no work get clear empty states; owner-only parts hidden for members
  proof: renderHome empty install: one 'No projects yet' card (Go to Projects for owners, a note for members); member: no Awaiting tile, no decisions; test_home_command_center... (emptyOwner, emptyMember, member); lock10-shots/slice4-empty-home-*.png, slice4-member-home-*.png
- [x] Behaviour tests (node driver), full suite, git diff --check, 0 CR, node --check, jaira validate; Chromium 1440/1024/390 as owner and member with no CSP errors or sideways scroll; README
  proof: Ran 486 tests, OK (484 before); git diff --check clean; 0 CR; node --check ok; Chromium 1440/1024/390 as owner, member and empty install: no CSP errors, no sideways scroll (lock10-shots/slice4-*); README Command Center bullet

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] index.html: Home becomes the Command Center (strip, decisions, next actions, at risk, this week, portfolio by entity); the old dashboard moves unchanged into a new #/portfolio view; add a Risk filter and a No due date option
- [x] app.js: renderHome from loaded tasks, cached owner requests (openInbox fetches them) and /api/portfolio; one delegated click handler; decisions reuse decideOwnerRequest with a Home error box
- [x] app.js router: portfolio view (filters, Gantt, More menu) on #/portfolio; #/home?<filters> redirects; rail marks Projects for the portfolio
- [x] style.css: tiles, cards, rows, week bars; tokens only
- [x] Tests: node driver renders Home for owner, member and an empty install; tile links; decision buttons; redirect; update filter-link tests to #/portfolio

## Progress
- **2026-09-25 07:58 · Claude** — Plan reasoning (Claude, 2026-09-25): (1) Home decisions use a different attribute (data-home-decision) and one delegated listener, so the wiring test stub (which finds buttons by attribute across bodies) never sees two sets of Approve buttons. (2) Owner requests are fetched once by openInbox (as today) and cached in state.ownerRequests; Home re-renders from the cache after openInbox, so Approve/Reject on Home and in the Inbox share one path and one reload. (3) Tile links carry open=1 so a count and its list agree. (4) The dashboard moves rather than being rebuilt: its ids, filters and tests stay.
- **2026-09-25 08:11 · Claude** — Found while building (Claude, 2026-09-25): Export CSV sends the dashboard filters to the server, which did not know band=undated or risk and would have exported everything; a tiny server change (service.py export_tasks, web.py filter keys) applies the same rules as app.js so the tile lists and their exports agree. Not built: 'since Monday' deltas and consequence chips (need history/impact data the server does not return).
- **2026-09-25 09:48 · Claude** — Review 10 follow-ups (fix commit): M2, the This week strip is now today + 7 days (8 bars that add up to the Due in 7 days tile), with one shared dueThisWeek rule in app.js; M1, strip labels come from the server's today (/api/tasks 'today', Asia/Karachi) instead of the browser's clock; L4, the export drops an unknown risk value (service.py EXPORT_RISKS), so it is not named in the filename either; L5, Home cards keep their own height and 'Counts as of' is shown once; L7, /api/portfolio is fetched once per Home visit and one renderer (portfolioCards) serves Home and the More-menu dialog.
