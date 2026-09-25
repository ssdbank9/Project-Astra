---
id: 01M3C0MZ2TASFSNYRN1E3C1Z74
title: "Gate 2 slice 7: phone and accessibility pass, plus the Gate 2 leftovers"
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Every Gate 2 screen works on phones (360, 390), tablets (768, 1024) and desktop, with a keyboard and with a screen reader, and the small leftovers from reviews 9 and 10 are closed, so Gate 2 is finished."
context: |-
  What is wrong today (after slices 1-6, pushed at 46ec9f4):
  - No one has checked every route at 360, 768 and 1024 px. Slices 4-6 were checked at 1440, 1024 and 390 only.
  - Some touch targets are still under 44px, and some inputs may be under 16px (iOS zooms the page when you type in them).
  - The Gantt project flag is white on #d1495b, 4.36:1 contrast; WCAG needs 4.5:1 (review 9 gap).
  - The task panel shows 'Open full page' on phones, where the panel is already full screen (review 9 gap).
  - Divide by owner groups board lanes by display name, so two people with the same name share a lane (review 10, I2).
  - The Gantt today line and the portfolio 'As of' still read the browser clock (review 10 gap; Home, My Work and the calendar already use the server's today from /api/tasks).
  - There is no favicon; the browser logs a 404 (review 9 gap).
  - Home links to the Portfolio page only through small card links; it should be visible and documented.
  Trigger: Aly's lock #11 (Slack ts 1790330196.902179, 2026-09-25): Gate 2 slice 7.
  Spec: session file ux-research.md slice 7 rows 7.1-7.4 and 'Keep it lean' (plain HTML/CSS/JS, tokens first, no new dependency; axe-core is not allowed).
  Already there: skip link to #main, one h1 (#page-title) focused on route change, nav/header/main landmarks, a bottom bar below 760px, 44px panel close and avatar below 1024px, reduced-motion rule.
  Not in this slice: new features, drag and drop, themes.
definition-of-done: "Phone and tablet pass: every route (Home, Portfolio, Projects, project tabs, Board, My Work, Calendar and agenda, Inbox, task panel, Capture, People, More menu, sign-in) at 360x740, 390x844, 768 and 1024 has no sideways page scroll, no clipped text, 44px tap targets below 1024px, 16px form fields, and the bottom bar never covers content (safe-area inset)"
tags:
  - astra
blocked-by: []
related:
  - 01M2JHKHPFGHBYXK2FFDX8FNA5
  - 01M2WNN5PQXBBCD0XTZGJQY55P
  - 01M3BVD71SMNH4E0M2CRFKVHH8
commits: []
created-at: 2026-09-25T10:09:20Z
updated-at: 2026-09-25T10:49:34Z
updated-by: Claude
claimed-by: vm-14196
claimed-at: 2026-09-25T10:09:31Z
outcome-what: "Phone/tablet and accessibility pass across every Gate 2 route (one touch-width CSS block: 44px targets, 16px fields, safe-area room, wrapping titles and People rows; sign-in main landmark; legend keys kept whole; Gantt project flag and brand contrast), plus the leftovers: Open full page hidden on touch widths, owner lanes by user id, Gantt today line and portfolio As of from the server's today, an SVG favicon, a visible Portfolio Gantt button on Home"
outcome-why: "Gate 2 slice 7 in Aly's lock #11: finish Gate 2 so it works on phones, tablets, keyboards and screen readers, and close the review 9/10 gaps"
outcome-resolves: 3C1Z74 definition of done 1-4; Gate 2 slice 7 for X8FNA5/JQY55P
---

# Gate 2 slice 7: phone and accessibility pass, plus the Gate 2 leftovers

## Definition of Done

- [x] Phone and tablet pass: every route (Home, Portfolio, Projects, project tabs, Board, My Work, Calendar and agenda, Inbox, task panel, Capture, People, More menu, sign-in) at 360x740, 390x844, 768 and 1024 has no sideways page scroll, no clipped text, 44px tap targets below 1024px, 16px form fields, and the bottom bar never covers content (safe-area inset)
  proof: style.css:736 touch-width block (44px targets, 16px fields, safe-area bottom padding, wrapping page title and People rows); scratch audit $S/l11audit.js over every route, Capture, People, the menus and sign-in at 1440/1024/768/390/360 as owner and member: 0 findings (no sideways scroll, nothing past the screen or dialog edge, no target under 44px below 1024px, no field under 16px, no bottom-bar overlap); test_touch_widths_get_44px_targets_16px_fields_and_room_for_the_bottom_bar; lock11-shots/*.png (160)
- [x] Accessibility pass: one h1 per route, nav/main/aside landmarks, a skip link, every control has a name, aria-current on the rail and tabs, a visible focus ring on everything, route changes announce the new page, reduced motion honoured, all text at 4.5:1 or better (including the Gantt project flag); checked by a scratch Playwright audit (names, contrast, headings, landmarks, target sizes, field font size, sideways scroll, bottom-bar overlap)
  proof: Same audit: exactly one visible h1 per route, main and nav landmarks everywhere (the sign-in card is now a main with a labelled h1), every control named, every text pair at 4.5:1 or better (3:1 for large text); $S/l11kbd.js: first Tab is the skip link, Enter moves focus to #main, focus rings on every stop, a route change focuses #page-title, aria-current on the rail and tabs, panel animation off under reduced motion; test_gantt_project_flags_meet_contrast (white on --red 5.2:1, brand text --teal-dark)
- [x] Leftovers: 'Open full page' hidden where the panel is already full screen; Divide by owner groups lanes by user id, so two people with the same name get separate lanes; the Gantt today line and the portfolio 'As of' use the server's today; an SVG favicon served from the static allowlist; Home shows a visible 'Portfolio Gantt' link, documented in the README
  proof: #detail-full hidden in the touch block; renderBoard keys owner lanes by owner_user_id with '(1 of 2)' labels (test_divide_by_owner_and_criticality sameName); renderGantt today line and asOfText from appToday()/state.timezone (test_gantt_today_line_and_as_of_use_the_servers_today, browser in Pacific/Pago_Pago); favicon.svg in web.py STATIC_FILES plus a link tag (test_favicon_is_a_small_svg_on_the_static_allowlist); Home 'Portfolio Gantt ›' button #home-gantt-link (index.html, README)
- [x] Behaviour tests where testable, full suite, git diff --check, 0 CR, node --check, jaira validate; Chromium screenshots at 1440/1024/768/390/360 as owner and member without CSP errors; README, handoff (lock #11 not yet pushed, test count) and the CLAUDE.md figure updated
  proof: tests/run.py: Ran 507 tests, OK (503 before); git diff --check clean; 0 CR; node --check ok; jaira validate 0 errors (pre-existing warnings only); lock11-shots at 1440/1024/768/390/360 as owner and member, no CSP errors or page errors; README, CLAUDE_HANDOFF_2026-09-24.md (lock #11 not yet pushed, 507) and CLAUDE.md updated

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Write a scratch Playwright audit ($S/l11audit.js, not in the repo): every route and dialog at 360/390/768/1024/1440 as owner and member; report sideways scroll, h1 count, landmarks, unnamed controls, targets under 44px below 1024px, fields under 16px, text contrast under 4.5:1, clipped text, bottom-bar overlap, CSP errors
- [x] Run it on 46ec9f4 for a baseline and fix what it finds with the smallest CSS/JS changes (tokens first; one touch-width block rather than per-screen rules)
- [x] Contrast: darken the Gantt project flag through a token; check every other text pair the audit reports
- [x] Leftovers: hide Open full page below 1024px; lanes keyed by owner_user_id and labelled by name; Gantt today line and portfolio As of from appToday(); favicon.svg in STATIC_FILES with a link tag; a visible Portfolio Gantt link on Home
- [x] Tests: static CSS asserts for touch targets, 16px fields, safe-area inset, the project-flag contrast pair; behaviour tests for same-name lanes, the favicon route and allowlist, Open full page hidden, server today on the Gantt/As of
- [x] Re-run the audit to zero findings (or documented exceptions), screenshots into $S/lock11-shots/, README, handoff, CLAUDE.md, full suite and checks

## Progress
- **2026-09-25 10:33 · Claude** — Audit (scratch $S/l11audit.js, Playwright, no axe-core): every route plus Capture, People, the More and account menus and sign-in, at 1440/1024/768/390/360 as owner and member. Baseline at 46ec9f4: no sideways scroll, one h1 everywhere, landmarks and names fine; the findings were about 1000 controls under 44px on touch widths (buttons 31-38px, button.link 18-36px, tabs 42px, fields 39-42px), 89 fields at 14px (iOS zoom), the Gantt target flag at 4.36:1 and the sign-in brand text at 2.32:1. Fixed with one touch-width block (max-width 1023px) instead of per-screen rules. Exceptions kept on purpose: Gantt bars at 768 (each repeats the task link in its row's name column, which is 44px), checkboxes (their label is the 44px target), the skip link (off screen until focused; 44px when focused). False positives fixed in the script: the hidden rail on the sign-in page, the task panel covering the bar on phones. Also found by looking at the shots: the Gantt legend could strand a swatch away from its label (review 9 gap), and the page title was cut with an ellipsis at 768; both fixed. The sign-in card is now a main landmark with a labelled h1.
