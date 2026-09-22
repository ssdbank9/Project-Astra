---
id: 01M348H8699HN86WY7AYGDPJD1
title: Portfolio toolbar and header never wrap; bar text fails contrast
status: todo
ready: true
creator: Claude
assignee: Claude
goal: "The Gantt page fits the viewport at 1440 px and 390 px with no horizontal page scroll, the timeline header stays visible while the rows scroll, and text on the amber and grey bars meets WCAG AA (4.5:1)."
context: |-
  At 1440 px wide the toolbar row is 2512 px wide on main (2608 px with the import branch merged), so Sort, Search and the action buttons sit off-screen with no horizontal scrollbar to reach them. With PR #4 merged the Import button (#import-btn, src/astra/static/index.html:49 on claude/excel-import) lands at x=2219-2301: the import feature's only entry point is invisible.
  Cause: .toolbar at src/astra/static/style.css:40 is display:flex without flex-wrap, and every label has min-width:180px (style.css:41).
  At 390 px the page header overflows its box (content 100 px in 66 px; header actions at style.css:32-33 do not wrap).
  .gantt-head (style.css:87) is position:sticky, but #gantt (style.css:65) is the overflow:auto scroll container, so the date axis scrolls away with the rows (top -225 px after scrolling 700 px).
  White text on the amber bar #d98d16 has 2.70:1 contrast and on the grey bar #8792a2 3.15:1 (style.css:72-78); AA needs 4.5:1. The amber border is 2.70:1 on white.
  Measured 2026-09-22 with a headless browser on main cd59438e, claude/gantt-steps 7858c7f and the merged tree. Pre-existing on main; not introduced by PR #2 or PR #4.
  From the 2026-09-22 adversarial review, findings GF-14 (medium) and MS-9 (low, same toolbar) (docs/reviews/2026-09-22-adversarial-review.md, section 2). Own ticket against main.
  Ruled out: the PR #2 step segment hues (GF-3) were fixed on claude/gantt-steps; this ticket covers only the plain bars and the page frame.
definition-of-done: ".toolbar and the header actions wrap (flex-wrap: wrap, or a separate actions row); at 1440 px and 1280 px document.scrollWidth equals the viewport width and #import-btn, when present, lies inside the viewport"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-22T09:53:12Z
updated-at: 2026-09-22T09:56:22Z
updated-by: Claude
---

# Portfolio toolbar and header never wrap; bar text fails contrast

## Definition of Done

- [ ] .toolbar and the header actions wrap (flex-wrap: wrap, or a separate actions row); at 1440 px and 1280 px document.scrollWidth equals the viewport width and #import-btn, when present, lies inside the viewport
- [ ] At 390 px the page header content fits its box and there is no horizontal page scroll
- [ ] The timeline header stays visible while the Gantt rows scroll (overflow:auto moved to an inner wrapper, or the sticky element re-anchored); checked in a browser
- [ ] Text on the amber and grey bars reaches 4.5:1 (dark text or darker fills) and the amber border is darkened; the measured ratios are recorded on the ticket
- [ ] Browser check at 1440 px and 390 px recorded with the roles and viewports exercised; full suite green (.venv/bin/python tests/run.py); git diff --check clean

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

