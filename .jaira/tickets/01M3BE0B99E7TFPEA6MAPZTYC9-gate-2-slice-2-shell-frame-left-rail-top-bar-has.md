---
id: 01M3BE0B99E7TFPEA6MAPZTYC9
title: "Gate 2 slice 2: shell frame (left rail, top bar, hash router, filters in the URL, toolbar into menus)"
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Astra gets the Gate 2 frame: a left rail (Home, My Work, Inbox, Projects, Capture), a top bar with the page title, search and a user menu, and one link per screen so reload, Back and a pasted link land on the same screen with the same filters. The long button toolbar is gone; its actions live in short menus."
context: |-
  What is wrong today (after slice 1, 4T4DEA):
  - Every screen is a modal dialog over one dashboard page. There is no navigation, and no screen has its own link.
  - The dashboard toolbar mixes 9 filters with 11 buttons in one card. Filters live only in the page, so reload or a shared link loses them.
  - Sign out, Sign out everywhere and the bell sit in the header next to the name; on phones they crowd each other.
  - The inbox is a dialog, so it cannot stay open as a page.
  Aly's decisions (lock #9, Slack thread ts 1790256175.671249):
  - Navigation is the production spec Aly accepted on 2026-09-20 (docs/design/astra-product-ux-baseline.md): rail Home, My Work, Inbox, Projects, Capture. It replaces X8FNA5's older view list. Portfolio becomes a Home row later; Calendar later.
  - Capture = quick-add a task with the existing create endpoint and permissions (POST /api/tasks). No new server code.
  - Keep Approve/Reject live in the inbox. Plain HTML/CSS/JS, no framework, no build step, minimal diff.
  Constraints from tests/test_web.py: keep ids #detail-dialog, #detail-body, #detail-edit, #inbox-body, #project-filter, #project-history-btn, #add-dep-button and the text 'Portfolio Gantt'; the exact render() line for #project-history-btn is pinned; the Node DOM stubs only provide location.hash and history.replaceState, so the router must not need pushState. #inbox-dialog is only used by the wiring test's close-task scenario; if the inbox becomes a page, change that test on purpose and keep its two cases.
  UX sources: session files ux-research.md (slice 2 rows) and gate2-scout.md (slice 2).
  Out of scope: task side panel (slice 3), Command Center Home (slice 4), project tabs and board (slice 5).
definition-of-done: "Left rail with Home, My Work, Inbox (unread badge), Projects and Capture; the current screen is marked (aria-current); on phones it becomes a bottom bar"
tags:
  - astra
blocked-by: []
related:
  - 01M2JHKHPFGHBYXK2FFDX8FNA5
  - 01M2WNN5PQXBBCD0XTZGJQY55P
  - 01M3BDCQSRG5SDAJY6J54T4DEA
commits: []
created-at: 2026-09-25T04:43:30Z
updated-at: 2026-09-25T05:01:42Z
updated-by: Claude
claimed-by: vm-5586
claimed-at: 2026-09-25T04:43:42Z
outcome-what: "Gate 2 shell frame: a left rail (Home, My Work, Inbox with unread badge, Projects, Capture; a bottom bar on phones), a sticky top bar (breadcrumb and title, search with Ctrl K or /, ? shortcut list, account menu with People for owners, Sign out, Sign out everywhere), a hash router (#/home, #/my-work, #/inbox, #/projects) using location.hash and history.replaceState only, Home filters in the link with removable chips, 'Showing X of Y' and Clear all; the toolbar keeps only filters and its buttons live in a keyboard-operable More menu; My Work groups my open tasks by due date; the Inbox is a page with Approve/Reject; Projects lists projects and opens one on Home; Capture reuses the task form with optional fields folded and a 'Show it' toast when filters hide the new task; amber and gray no longer used as text."
outcome-why: "Every screen was a dialog over one dashboard with no links, 20 controls in one toolbar, sign-out buttons crowding the phone header, and an inbox that could not stay open. Aly accepted the rail Home/My Work/Inbox/Projects/Capture as the production spec, with Capture as quick-add through the existing endpoint (lock #9)."
outcome-resolves: "All six DoD items ticked with proof; Ran 466 tests, OK; Chromium checks at 1440/1024/390: no sideways scroll, no CSP errors, filters survive reload and Back."
---

# Gate 2 slice 2: shell frame (left rail, top bar, hash router, filters in the URL, toolbar into menus)

## Definition of Done

- [x] Left rail with Home, My Work, Inbox (unread badge), Projects and Capture; the current screen is marked (aria-current); on phones it becomes a bottom bar
  proof: index.html nav.rail (Home, My Work, Inbox with #unread-count badge, Projects, Capture #new-task); applyRoute sets aria-current=page; style.css phone media turns .rail into a bottom bar; test_web AstraShellRouterTests.test_shell_landmarks_rail_top_bar_and_menus; lock9-shots/slice2-*-390.png
- [x] Top bar with breadcrumb and page title, a search box (Ctrl K or / focuses it; Enter searches), and a user menu holding Sign out, Sign out everywhere and People (owners only)
  proof: index.html header.topbar (#crumb, h1#page-title, #search-box with aria-keyshortcuts, #user-menu with #people/#logout/#logout-all); app.js focusSearch on Ctrl/Cmd+K and /, ? opens #keys-dialog; Chromium: Ctrl+K and / focus search, user menu items listed, outside click closes (lock9-shots/slice2-user-menu-*.png, slice2-keys-1440.png)
- [x] Hash router (#/home, #/my-work, #/inbox, #/projects) that needs no pushState; Home filters live in the URL, so reload and Back restore them; Node tests for the route parser and URL round trip
  proof: app.js parseRoute/currentRoute/applyRoute/filtersFromUrl/homeQuery/syncFilters (location.hash + history.replaceState only); test_web AstraShellRouterTests (routes, URL round trip, no pushState); Chromium: #/home?due=7&open=1 survives reload, Back walks projects->inbox->my-work->filtered Home
- [x] The toolbar keeps only filters (plus Clear filters); its buttons move into a More menu (keyboard operable, Esc closes and returns focus) and New project moves to the Projects page
  proof: index.html .toolbar holds only filters + #clear-filters (Clear all); #more-menu holds Portfolio, Final results, Templates, Import, Export CSV, Project history, Save project as template, Close project (project actions only with one project selected); wireMenu (arrows, Esc returns focus, outside click); #new-project on the Projects page; test_shell_landmarks_rail_top_bar_and_menus; Chromium moreClosedFocus [true, more-btn]
- [x] Home shows today's dashboard; My Work lists open tasks assigned to me grouped by due date; Inbox shows today's inbox as a page with Approve/Reject still working; Projects lists projects and opens one on Home; Capture quick-adds a task through POST /api/tasks
  proof: app.js renderMyWork, renderProjects, openInbox renders the Inbox view (Approve/Reject kept), openCapture + showToast 'Show it' when filters hide a new task, removable filter chips; test_views_capture_and_menu_behaviour_are_wired; wiring tests pass with the Inbox route; Chromium screenshots slice2-{my-work,inbox,projects,capture,toast}-*.png
- [x] Pinned ids and tests kept or changed on purpose with coverage kept; full suite green; git diff --check, 0 CR bytes, node --check, jaira validate; Chromium screenshots at 1440/1024/390 with no sideways scroll and no CSP errors; README updated
  proof: tests/run.py Ran 466 tests, OK (461 before); wiring close-task scenario moved from #inbox-dialog to location.hash=#/inbox with both cases kept; git diff --check clean; 0 CR bytes; node --check ok; jaira validate errors false; Chromium 1440/1024/390 no sideways scroll on any view and no CSP errors; README navigation shell bullet

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] index.html: skip link, nav.rail (inline SVG icons, #inbox link with #unread-count badge, Capture button #new-task), header.topbar (crumb, h1#page-title, #search-box, avatar button + user menu with #people, #logout, #logout-all), main with four view sections; Home keeps summary, filter bar and the Portfolio Gantt panel; toolbar buttons move into a More menu in the Gantt panel header; #new-project moves to the Projects page; the inbox dialog is replaced by the Inbox view holding #inbox-body
- [x] app.js router: parseRoute(hash) -> {name,id,params}; applyRoute on hashchange and after load; filters read from and written to the URL with history.replaceState (no pushState); the rail Home link keeps the last Home query; focus moves to the page title on navigation
- [x] app.js views: renderMyWork (open tasks owned by me, grouped overdue/today/next 7 days/later/no date), renderProjects (rows with open/overdue counts, click -> #/home?project=id), openInbox renders the page (no dialog), Capture opens the task dialog trimmed to title/project/due with the rest under More fields, project preselected from the Home filter
- [x] app.js menus: one small menu helper (toggle, Esc closes and refocuses, arrow keys, outside click closes) for the More menu and the user menu; Ctrl/Cmd+K focuses search (no single-key shortcut, per the baseline's accessibility contract)
- [x] style.css: [hidden] reset, shell grid (72px rail, 60px top bar), rail and top bar styles, menu, view pages, My Work and Projects rows, phone bottom bar; reuse slice 1 tokens
- [x] Tests: Node router test (parse, filter URL round trip, guarded without pushState), static asserts for the shell landmarks and ids, wiring test close-task scenario moved from #inbox-dialog to the Inbox route; full suite, checks, screenshots; README; move to review; commit with the ticket

## Progress
- **2026-09-25 04:44 · Claude** — Plan reasoning (Claude, 2026-09-25): (1) Navigation uses location.hash assignment, which adds a history entry and fires hashchange by itself, and history.replaceState for filter edits, so there is no pushState at all and the Node stubs (location.hash, history.replaceState only) keep working. (2) Filter edits replace the URL instead of pushing, so Back leaves the screen instead of undoing one filter at a time. (3) Capture reuses the existing task dialog and POST /api/tasks rather than a second form: optional fields fold under More fields. That keeps one create path (ux-research rule 4) and the server's permission checks. (4) No single-key shortcuts: the UX baseline's accessibility contract says users must be able to disable them, so only Ctrl/Cmd+K is bound. (5) People stays a dialog opened from the user menu; Manage as a rail entry is later.
- **2026-09-25 05:01 · Claude** — Changes after the coordinator relayed the finished ux-research.md and the design reference (2026-09-25): the rail marks the current page with a lighter navy fill and a 3px teal bar (top edge on phones); amber and gray are fills only (the Gantt's amber and gray bars now use dark ink, the Gantt header caption uses --muted); chips use tint + dark text tokens (--chip-*) and the overdue chip carries a triangle glyph; active filters are removable chips beside 'Showing X of Y' with Clear all; a hidden new task gets a toast with 'Show it'; '/' and '?' were added on request. Decision for Aly: '/' and '?' are single-key shortcuts; the UX baseline's accessibility contract says people must be able to turn those off. They fire only outside text fields and when no dialog is open, but there is no off switch yet. Not built: an Owner-only Manage rail entry (the More menu covers it), counts per filter option, j/k (slice 3).
