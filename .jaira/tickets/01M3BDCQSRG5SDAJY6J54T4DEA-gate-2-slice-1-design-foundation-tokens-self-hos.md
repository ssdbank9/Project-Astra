---
id: 01M3BDCQSRG5SDAJY6J54T4DEA
title: "Gate 2 slice 1: design foundation (tokens, self-hosted Inter, focus rings, no inline styles, no sideways scroll)"
status: signoff
ready: true
creator: Claude
assignee: Claude
goal: "One visual foundation the Gate 2 shell can build on: named design tokens and a type scale, the Inter font served by Astra itself, a visible keyboard focus ring everywhere, reduced motion honoured, no styling silently dropped by the CSP, and no sideways scrolling at desktop or phone width."
context: |-
  What is wrong today (branch codex/migration-safety-remediation at f8f0f69):
  - style.css names Inter but Astra never ships it, so every browser falls back to Segoe UI or Arial. The CSP (web.py _static, style-src 'self') also blocks font CDNs.
  - app.js writes 13 inline style="..." attributes (portfolio note, templates, final results, search, schedule proposals, attachments, calendar note, filing note). style-src 'self' drops them and the console shows CSP errors.
  - At 1440px the page scrolls sideways: .toolbar is one flex row that never wraps (10 buttons plus 9 filters, about 2583px wide).
  - At 390px the header's brand, subtitle, name and both sign-out buttons overlap.
  - :focus-visible exists only on Gantt parts and the import dropzone; reduced motion covers only steps and bars.
  - There are no semantic tokens for surfaces, lines, muted text, spacing, radii, elevation or type sizes.
  Trigger: Aly chose option 7 (adopt the Gate 2 look) and granted exclusive lock #9 (Slack ts 1790310494.822249, 2026-09-25). Scout: session file gate2-scout.md, slice 1.
  Aly's decisions for Gate 2: self-host Inter; keep today's palette (style.css :root); plain HTML/CSS/JS, no framework, no build step, no new dependency, minimal diff ("a free app").
  Umbrella tickets: X8FNA5 (Aly, backlog) and JQY55P (Aly, human) stay Aly's; this ticket is related to both.
  Out of scope here: the left rail, router and task side panel (slices 2 and 3).
definition-of-done: "Inter is served by Astra from static/fonts with its OFL licence file: a strict file allowlist, the right content type, long caching for the versioned font files, and a CSP that names font-src 'self'; source and version recorded"
tags:
  - astra
blocked-by: []
related:
  - 01M2JHKHPFGHBYXK2FFDX8FNA5
  - 01M2WNN5PQXBBCD0XTZGJQY55P
commits: []
created-at: 2026-09-25T04:32:48Z
updated-at: 2026-09-25T07:13:02Z
updated-by: Claude
claimed-by: vm-2127
claimed-at: 2026-09-25T04:32:57Z
outcome-what: "Design foundation for the Gate 2 shell: Inter 4.001 self-hosted (latin + latin-ext variable woff2 from Google Fonts css2 v20, OFL file shipped) behind a strict static allowlist with font/woff2, one-year immutable caching and CSP font-src 'self'; semantic tokens (surfaces, lines, muted text, spacing, radii, elevation, motion) and a type scale (11/12/14/16/20/24) on :root with today's palette kept; a global :focus-visible ring; reduced motion switches off every transition and animation; the 13 CSP-blocked inline style attributes in app.js replaced by .fine and .muted; toolbar and header wrap, so no sideways scroll at 1440/1024/390 and no header overlap on phones. After review 9: Review 9 fixes: sign-out reloads the page; the task panel sits below the top bar and is 380px at 1024-1279px; a filter picked with the panel open survives closing; malformed or non-id links are ignored and a failed load is not a sign-out; no page-wide single-key shortcuts (j/k only in the panel); Esc in a panel field keeps focus in the panel; j/k follow the screen's order; 44px phone targets; each fact shown once, steps and dependencies before Lifecycle; More menu is a sheet on phones; one muted grey token; action toasts stay until used; Clear all beside the chips; page title Home."
outcome-why: "Astra named Inter but never shipped it, the CSP silently dropped 13 inline styles (console errors), the 1440px page scrolled sideways (toolbar 2583px wide), the phone header overlapped, and focus rings and reduced motion covered only the Gantt. Aly chose option 7 (Gate 2 look) with self-hosted Inter, plain HTML/CSS/JS and a minimal diff (lock #9, Slack ts 1790310494.822249). After review 9: Independent review 9 returned request changes (session file lock9-review.md): a High cross-account leak on sign-out, the panel covering the top bar, a lost filter, a malformed-link sign-in loop, single-key shortcuts against WCAG 2.1.4, and missing behaviour tests."
outcome-resolves: "All six DoD items ticked with proof; Ran 461 tests, OK; Chromium screenshots at 1440/1024/390 show no sideways scroll, no header overlap and no CSP errors. After review 9: All DoD items ticked with corrected proofs; Ran 482 tests, OK; Chromium at 1440/1024/390: owner signs out and a member signs in with none of the owner's Inbox or panel on screen, account menu and search usable with a task open, filters kept, no CSP errors, no sideways scroll."
review-summary: "Review 9 (2026-09-25) of 91bc390/08b926c/cf44fb6: request changes (H1 sign-out leak, M1-M5, L1-L10). Fixed in c47062be15677f357a4e25a8fafbd73e69f0ccf5. Focused re-review of c47062b (session file lock9-rereview.md): approve with follow-ups; H1 and M1-M5 fixed with behaviour tests, three small new defects N1 (action toast followed you across screens), N2 (copy-link fallback toast timed out), N3 (44px targets only on phones). N1-N3 fixed in 03acafcf3ffccca9cce65495a4045abf1a3cc2eb with tests; Ran 484 tests, OK."
review-verdict: "approve with follow-ups; review 9 request changes fixed in c47062be15677f357a4e25a8fafbd73e69f0ccf5, re-review approve with follow-ups, N1-N3 fixed in 03acafcf3ffccca9cce65495a4045abf1a3cc2eb, not re-reviewed"
review-gaps: "Left for later: L4 and L5 partial (1024px screen behind the 380px panel is still about 516px; the Gantt legend orphans an item); the pre-existing Gantt project-flag contrast (.proj-flag, white on #d1495b, 4.36:1); Open full page still shown on phones where the panel is already full screen; a Manage rail entry so Import and Templates are reachable outside Home (later slice); no favicon (404 in the console)."
review-check: "1. Windows, repo root: .venv\\Scripts\\python.exe tests\\run.py; expect 'Ran 484 tests' and 'OK'. 2. Start Astra and sign in as the primary owner: a left rail (Home, My Work, Inbox, Projects, Capture) and a top bar with search and your initials. 3. On Home pick Criticality: Low and Open work only: chips appear under the filters with 'Showing X of Y' and Clear all; reload the page: the filters are still set. 4. Click a task link in the Gantt: it opens in a panel on the right, the Gantt stays usable, the top bar is still visible; press Esc: the panel closes and focus is back on the link. 5. Open a task, click Copy link, paste the link in a new tab: the same task opens. 6. Open Inbox with a task open, then Sign out from the account menu and sign in as a member: none of your Inbox or the task is on screen. 7. Resize to phone width: the rail is a bottom bar and a task fills the screen."
---

# Gate 2 slice 1: design foundation (tokens, self-hosted Inter, focus rings, no inline styles, no sideways scroll)

## Definition of Done

- [x] Inter is served by Astra from static/fonts with its OFL licence file: a strict file allowlist, the right content type, long caching for the versioned font files, and a CSP that names font-src 'self'; source and version recorded
  proof: src/astra/static/fonts/ (inter-latin-4.001.woff2, inter-latin-ext-4.001.woff2, Inter-OFL.txt; Inter 4.001 from Google Fonts css2 v20); web.py CONTENT_SECURITY_POLICY, STATIC_FILES, FONT_FILES, _static; pyproject static/fonts/*; test_web AstraWebTests.test_inter_font_is_served_by_astra_with_strict_allowlist_and_caching, AstraFoundationStaticTests.test_font_faces_point_at_the_served_files_only
- [x] style.css has semantic tokens (surface, line, muted text, spacing, radii, elevation) and a type scale, keeping today's palette values; the step-token contrast tests still pass
  proof: style.css :root tokens (--canvas/--surface*/--line*/--muted/--space-*/--radius*/--shadow-*/--fs-*/--dur-*/--chip-*); palette unchanged; after review 9 L8 every muted grey uses var(--muted) (0 literal #667085 left) and the dead #inbox-dialog selector is gone (review 9 fix commit (lock #9)); test_web AstraFoundationStaticTests.test_tokens_type_scale_focus_and_reduced_motion, test_text_tokens_meet_contrast_on_their_backgrounds (--muted on four surfaces, every chip pair, rail text, badge, white on teal, all >= 4.5:1); step contrast tests pass
- [x] app.js writes no inline style attributes (replaced by classes) and a test pins that; no CSP errors in the browser console
  proof: app.js: 13 style= attributes replaced by .fine and .muted; test_web AstraFoundationStaticTests.test_no_inline_style_attributes_reach_the_page; Chromium console at 1440/1024/390 shows no CSP error (only the pre-login /api/me 403 and /favicon.ico 404, both pre-existing)
- [x] Every interactive element shows a :focus-visible ring and prefers-reduced-motion removes transitions and animation
  proof: style.css ':focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }' and reduced-motion block for *, *::before, *::after; Chromium: Tab to Sign out shows a 2px teal ring (lock9-shots/slice1-focus-*.png); test_tokens_type_scale_focus_and_reduced_motion
- [x] No sideways page scroll at 1440x900, 1024x768 or 390x844, and the phone header no longer overlaps; screenshots at all three sizes
  proof: Chromium: scrollWidth equals viewport at 1440, 1024 and 390 (was 2608 at 1440); no overlapping header items; lock9-shots/slice1-home-{1440,1024,390}.png; test_toolbar_wraps_instead_of_scrolling_sideways
- [x] Tests for the font route and headers and the static changes; full suite green; git diff --check, 0 CR bytes, node --check, jaira validate
  proof: tests/run.py Ran 461 tests, OK at 91bc390; Ran 482 tests, OK after the review 9 fix commit (lock #9); git diff --check clean; 0 CR bytes; node --check ok; jaira validate errors false

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Fetch Inter from an official source (Google Fonts css2 API, latin + latin-ext variable woff2, wght 400-700) and the OFL text; read the version from the font's name table
  proof: Google Fonts css2 (wght 400..700 request returns the full 100-900 variable file), name table 'Version 4.001;git-66647c0bb'; OFL.txt from google/fonts ofl/inter (one trailing space stripped for git diff --check)
- [x] web.py: _static serves fonts/<name> from a fixed allowlist with font/woff2 and text/plain types, public immutable caching for the versioned font names, CSP gains font-src 'self'; pyproject package-data includes static/fonts/*
- [x] style.css: @font-face with unicode-range, semantic tokens and type scale on :root, reuse tokens in the base rules; global :focus-visible ring; reduced motion for every transition
- [x] app.js: replace the 13 inline style attributes with two classes (.fine for small muted notes, reuse .muted); index.html untouched except where layout needs it
- [x] Layout: toolbar wraps (no sideways scroll at 1440/1024), header compacts and wraps at phone width; check 390/1024/1440 in Chromium with screenshots and a CSP-error check
- [x] Tests: font route (types, caching, CSP, allowlist 404s), no style= in app.js, focus-visible and reduced-motion rules present, toolbar wraps; full suite, diff checks; move to review; commit with the ticket
- [x] Review 9 fixes: one muted grey token (L8), token contrast test (M5)
  proof: review 9 fix commit (lock #9); AstraFoundationStaticTests.test_text_tokens_meet_contrast_on_their_backgrounds

## Progress
- **2026-09-25 04:33 · Claude** — Font choice (Claude, 2026-09-25): Google Fonts serves Inter 4.001 (name table 'Version 4.001;git-66647c0bb', css2 API revision v20) as variable woff2 split by unicode-range. latin is 48 KB and latin-ext 85 KB; the browser downloads latin-ext only when a name needs it. The rsms GitHub release (full InterVariable.woff2, about 350 KB) was not reachable from this container (github.com access to rsms/inter is not enabled). The Google subsets keep the tnum feature (checked in GSUB), which the tabular numerals rely on. Glyphs outside the subsets (arrows, check marks) fall back to the system font per glyph. Files are named with the version so they can be cached as immutable.
- **2026-09-25 04:43 · Claude** — Done in this pass (Claude, 2026-09-25): --muted is #5b6475 (5.3:1 on every surface; the older #667085 is kept where tests pin it, e.g. .owner-request p.muted). Labels no longer pass their bold weight into inputs (font: inherit made every select value bold). The header and toolbar only wrap here; slice 2 replaces them with the rail and top bar, so no more effort went into them. Left for later: /favicon.ico is still a 404 in the console (pre-existing).
- **2026-09-25 06:10 · Claude** — Review 9 (request changes) fixed in one commit (Claude, 2026-09-25): H1 sign-out now reloads the page (location.replace(location.pathname)) so the next person on the browser gets a fresh app; the first load after sign-in also re-fetches a linked task. M1 panel below the 60px top bar with the top bar above it. M2 syncFilters clears panelState.pushed. M3 parseRoute never throws; only a failed /api/me shows sign-in. M4 no page-wide single-key shortcuts; j/k only with focus in the panel; the key list is in the account menu. M5 behaviour tests in one shared node driver (SHELL_DRIVER) plus a token contrast test. L1-L10 as listed in the review. Not changed: Open full page still shows on phones (I1), a Manage rail entry (L7 second half) stays for a later slice.
