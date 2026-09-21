---
id: 01M32AMMEW7SGBE4NRKTD73AQW
title: "Gantt: visible colour-coded task steps with hover and click detail"
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Make a task's steps (its subtasks) visible inside the parent task bar on the Portfolio Gantt, each step with its own colour and index, with hover/keyboard tooltip and click-through to the step's own record, plus a schedule-table twin, without adding libraries or changing authorization."
context: |-
  What is wrong today: a task's steps are invisible inside its Gantt bar. Subtasks (tasks with parent_task_id) render as separate full rows in src/astra/static/app.js renderGantt (lines 83-96), and the parent bar is one plain span.
  The bar is not interactive: no tooltip, no hover, no focus; the only click target is the 'Details & history' link in the name column (app.js:305 delegated [data-detail] handler).
  Trigger: Aly (App Owner) asked on 2026-09-21 in Slack for steps to be visible in the Gantt, a separate colour for each small step, and hover or click to see the step's details and owner.
  Steps = subtasks. The data already exists: tasks.parent_task_id, owner_user_id, status, criticality, start_date, due_date, progress (src/astra/db.py:103-121). GET /api/tasks returns all tasks flat with parent_task_id, so the client can group with no new endpoint.
  Gap: service.list_subtasks (src/astra/service.py ~1248) returns only id, title, status, due_date, owner_name; no start_date, so the detail dialog cannot show step dates.
  Research: scratchpad gantt-steps-research.md compared Asana, monday, Smartsheet, MS Project, TeamGantt, ClickUp, Wrike, Notion, DHTMLX, Bryntum, Frappe. Only DHTMLX split-mode draws steps inline in the parent bar when collapsed and as rows when expanded; that hybrid is the model.
  Approved defaults (Aly, 2026-09-21): (1) steps collapsed inline in the parent bar by default, chevron expands to child rows; (2) colour = step identity in index order using the Okabe-Ito colour-blind-safe palette, owner shown as initials chip and in the tooltip; (3) click opens the step's own task record with a Parent back-link.
  Constraints from docs/design/astra-product-ux-baseline.md: native HTML/CSS/JS only, colour never the sole carrier of meaning, WCAG 2.2 AA, hover AND keyboard focus, reduced motion respected, structured schedule-table alternative, 44px targets, no precision Gantt on phones.
  Known: the CSP header (src/astra/web.py:465) is style-src 'self', so inline style attributes are blocked; positions must be set through the CSSOM from JS.
  Ruled out: a new endpoint for rendering; colour = owner (conflicts with colour = step); the title attribute for tooltips.
definition-of-done: "Dated subtasks render as numbered, coloured segments inside the parent task bar on the Gantt (one Okabe-Ito hue per step index, index label always visible, title when the segment is wide enough); hover and keyboard focus show a tooltip with step name, owner, start/due dates, duration, status and due state, dismissible with Escape; clicking or pressing Enter/Space on a step opens that step's detail dialog, which shows a Parent back-link to the parent task; a chevron expands/collapses the child rows under the parent and the choice is remembered per parent in the browser; undated steps are shown as an 'n steps need dates' chip and never given invented dates; colour is never the sole carrier: every segment carries its index and a legend lists index + colour; a Schedule table toggle shows the same data as a real table (Project, Task, Step #, Step, Owner, Start, Due, Status, Due state, Critical path) and is the default at phone width; prefers-reduced-motion disables the transitions; steps narrower than 8px fold into a +N overflow disclosure; service.list_subtasks returns start_date, criticality, progress, parent_task_id and owner_user_id with unit and HTTP tests for the shape; node --check on app.js and the full test suite pass; browser evidence captured for Owner and Viewer at 1440 and 390 widths."
tags:
  - astra
blocked-by: []
related: []
commits:
  - 33d237f8fc11c712722c48e9d8834f63ed4dc0eb
created-at: 2026-09-21T15:51:31Z
updated-at: 2026-09-21T16:10:45Z
updated-by: Claude
claimed-by: vm-8214
claimed-at: 2026-09-21T15:52:35Z
outcome-what: "Portfolio Gantt groups tasks by parent_task_id and draws each dated subtask as a numbered Okabe-Ito coloured segment inside the parent bar, with collapsed child rows behind an aria-expanded chevron (remembered per parent), one shared hover+focus tooltip (step n of m, owner, dates, status, due state, criticality; Escape closes), roving keyboard focus per bar, click/Enter opening the step's own record with a Parent back-link, +N overflow disclosure, 'n steps need dates' chip, dashed derived track, state glyphs/stripes, a Schedule table twin (phone default) and reduced-motion support. list_subtasks returns start_date, criticality, progress, parent_task_id, owner_user_id. Gantt positions now go through the CSSOM because the CSP dropped inline styles."
outcome-why: "Aly asked on 2026-09-21 for steps to be visible inside the Gantt bar, one colour per step, with hover or click showing each step's details and owner; subtasks rendered as separate rows and the bar was not interactive."
outcome-resolves: "Every DoD clause is evidenced: segments with index + colour, tooltip on hover and focus with Escape, click/Enter to the step record with Parent link, expand/collapse remembered, undated chip, legend, Schedule table with the ten columns and phone default, reduced motion, +N overflow, list_subtasks shape with unit and HTTP tests; node --check clean; 119 tests pass; browser evidence for Owner and Viewer at 1440x900 and 390x844 with no new console errors."
---

# Gantt: visible colour-coded task steps with hover and click detail

- [x] Extend service.list_subtasks to return start_date, criticality, progress, parent_task_id, owner_user_id; write the unit test (tests/test_core.py) and HTTP test (tests/test_web.py) first, run red, then make them green
  proof: src/astra/service.py:1248 list_subtasks; tests/test_core.py:1400 test_list_subtasks_returns_step_schedule_shape; tests/test_web.py:680 test_task_detail_subtasks_carry_step_schedule_fields_over_http (both red on KeyError start_date before, green after)
- [x] app.js renderGantt: group state.tasks by parent_task_id; render parent as a tinted state-coloured track with one button.step per dated child positioned via the CSSOM (CSP blocks inline style attributes); index label always, title when wide; <8px steps fold into a +N overflow disclosure; undated children become an 'n steps need dates' chip; chevron expand/collapse to child rows remembered per parent in localStorage
  proof: src/astra/static/app.js:85 groupSteps, :108 applyGeometry (CSSOM, not inline style), :109 renderGantt (track, stepButton, +N overflow, undated chip, derived track, expand rows), :243 toggleSteps (localStorage astra.gantt.expanded)
- [x] Shared #step-tip role=tooltip shown on mouseenter (150ms) and focus, hidden on mouseleave/blur/Escape, hoverable, text-only, aria-describedby while visible; roving tabindex inside each parent bar (Left/Right/Home/End, Enter/Space opens detail through the existing [data-detail] handler)
  proof: src/astra/static/app.js:239 showTip/hideTip + wireGantt mouseover/mouseout/focusin/focusout, :263 roving keydown (ArrowLeft/Right/Home/End, Enter/Space); index.html #step-tip role=tooltip; browser evidence kbd section
- [x] Detail dialog: Parent back-link button when task.parent_title exists; buildSubtasks shows step swatch + index; step dates from the extended list_subtasks shape
  proof: src/astra/static/app.js:544 parentLink in renderDetail, :651 buildSubtasks swatch + index + dates
- [x] style.css: --step-1..--step-7 Okabe-Ito tokens, 22% tint fill + solid bottom stripe + dark text, completed/cancelled desaturated with glyph, on_hold stripes, prefers-reduced-motion, 44px hit area, visible focus ring, legend row with index + colour
  proof: src/astra/static/style.css:16 --step-1..7 + tints, :175 .bar.track, :187 .step::before 44px hit area, .step.done/.hold/.crit/.wrap, :242 prefers-reduced-motion, index.html #step-legend
- [x] Schedule table toggle beside the legend swapping #gantt for a real <table> (Project, Task, Step #, Step, Owner, Start, Due, Status, Due state, Critical path) with caption and scope=col headers, same filtered data, default at max-width 760px
  proof: src/astra/static/app.js:217 renderScheduleTable (caption, scope=col, 10 columns); index.html #view-table + #schedule-table; currentView() defaults to table under (max-width: 760px)
- [x] Verify: node --check app.js, full suite, git diff --check; Playwright evidence for Owner and Viewer at 1440x900 and 390x844 (collapsed, tooltip, expanded, step dialog with Parent link, table, phone, keyboard path, console errors); tick DoD with proofs, note, move to review
  proof: node --check clean; tests/run.py 119 pass (117 before); git diff --check clean; scratchpad/gantt/browser-evidence.md + 20 PNGs (Owner and Viewer, 1440x900 and 390x844), no new console errors

## Definition of Done

- [x] Dated subtasks render as numbered, coloured segments inside the parent task bar on the Gantt (one Okabe-Ito hue per step index, index label always visible, title when the segment is wide enough); hover and keyboard focus show a tooltip with step name, owner, start/due dates, duration, status and due state, dismissible with Escape; clicking or pressing Enter/Space on a step opens that step's detail dialog, which shows a Parent back-link to the parent task; a chevron expands/collapses the child rows under the parent and the choice is remembered per parent in the browser; undated steps are shown as an 'n steps need dates' chip and never given invented dates; colour is never the sole carrier: every segment carries its index and a legend lists index + colour; a Schedule table toggle shows the same data as a real table (Project, Task, Step #, Step, Owner, Start, Due, Status, Due state, Critical path) and is the default at phone width; prefers-reduced-motion disables the transitions; steps narrower than 8px fold into a +N overflow disclosure; service.list_subtasks returns start_date, criticality, progress, parent_task_id and owner_user_id with unit and HTTP tests for the shape; node --check on app.js and the full test suite pass; browser evidence captured for Owner and Viewer at 1440 and 390 widths.
  proof: Segments: app.js:109 renderGantt stepButton (index label always, title >=72px, owner chip >=110px, Okabe-Ito hue = stepHue(idx)); tooltip on hover+focus, Escape: app.js:239 showTip + wireGantt; click/Enter/Space -> openDetail with Parent back-link app.js:544; expand/collapse remembered: app.js:243 toggleSteps; undated chip and derived track: renderGantt; legend: index.html #step-legend; Schedule table: app.js:217 + currentView() phone default; reduced motion: style.css:242; +N overflow: renderGantt overflow list; list_subtasks shape: service.py:1248 with test_core.py:1400 and test_web.py:680; node --check clean; 119 tests pass; browser evidence: scratchpad/gantt/browser-evidence.md (Owner+Viewer, 1440 and 390)

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-21 16:10 · Claude** — Implemented the steps feature on branch claude/gantt-steps (stacked on claude/hs3jry-complete 6a82463); code commit 33d237f.
Found: the CSP header (web.py:465) is style-src 'self', so every inline style attribute in the Gantt was being dropped; all bars sat at left 0 in the HS3JRY screenshots. Fixed as part of this work by emitting data-x/data-w and applying positions through the CSSOM (applyGeometry). No CSP console errors remain for the Gantt.
Found: .bar.undated is position:static/inline-block, so a parent with no dates of its own broke the track (steps escaped). Parents with dated steps now get class 'derived' (dashed track) instead of 'undated'.
Decision: step index and hue come from ALL children in state.tasks (stable across filters); only the drawn set follows the filters. Same ordering (start||due, then title) in buildSubtasks so dialog and bar agree.
Decision: plain bars (no steps) also became buttons with the same tooltip so hover works on every bar, not only steps.
Decision: zoom (Week/Month/Quarter) was skipped - optional in the brief and the rest already touches renderGantt heavily; the +N overflow disclosure covers small steps at the current scale. Follow-up ticket if Aly wants it.
Dead end: Playwright wait_for_selector('#detail-dialog:not([open])') never resolves because a closed dialog is not visible; use wait_for_function on .open.
Dead end: pkill -f <script name> also kills the invoking shell when the name is in the command line; check with pgrep first.
Noise: every jaira write prints 'HS3JRY/D73AQW could not be sent: gitref: fatal: expected acknowledgments, received packfile' - a jaira sync/transport error in this container, not a gate refusal; the ticket file on disk updated each time.
Refusal read and satisfied: backlog->brainstorm was refused because the brainstorm option is not ticked; the ticket already had a goal so it moved backlog->todo->pre-process->in-progress instead.
Evidence: scratchpad gantt/browser-evidence.md (not committed); fixture server extended in scratchpad only, stopped, no listener on 8768.
