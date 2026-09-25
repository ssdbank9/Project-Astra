---
id: 01M3BDCQSRG5SDAJY6J54T4DEA
title: "Gate 2 slice 1: design foundation (tokens, self-hosted Inter, focus rings, no inline styles, no sideways scroll)"
status: review
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
updated-at: 2026-09-25T04:43:03Z
updated-by: Claude
claimed-by: vm-2127
claimed-at: 2026-09-25T04:32:57Z
outcome-what: "Design foundation for the Gate 2 shell: Inter 4.001 self-hosted (latin + latin-ext variable woff2 from Google Fonts css2 v20, OFL file shipped) behind a strict static allowlist with font/woff2, one-year immutable caching and CSP font-src 'self'; semantic tokens (surfaces, lines, muted text, spacing, radii, elevation, motion) and a type scale (11/12/14/16/20/24) on :root with today's palette kept; a global :focus-visible ring; reduced motion switches off every transition and animation; the 13 CSP-blocked inline style attributes in app.js replaced by .fine and .muted; toolbar and header wrap, so no sideways scroll at 1440/1024/390 and no header overlap on phones."
outcome-why: "Astra named Inter but never shipped it, the CSP silently dropped 13 inline styles (console errors), the 1440px page scrolled sideways (toolbar 2583px wide), the phone header overlapped, and focus rings and reduced motion covered only the Gantt. Aly chose option 7 (Gate 2 look) with self-hosted Inter, plain HTML/CSS/JS and a minimal diff (lock #9, Slack ts 1790310494.822249)."
outcome-resolves: "All six DoD items ticked with proof; Ran 461 tests, OK; Chromium screenshots at 1440/1024/390 show no sideways scroll, no header overlap and no CSP errors."
---

# Gate 2 slice 1: design foundation (tokens, self-hosted Inter, focus rings, no inline styles, no sideways scroll)

## Definition of Done

- [x] Inter is served by Astra from static/fonts with its OFL licence file: a strict file allowlist, the right content type, long caching for the versioned font files, and a CSP that names font-src 'self'; source and version recorded
  proof: src/astra/static/fonts/ (inter-latin-4.001.woff2, inter-latin-ext-4.001.woff2, Inter-OFL.txt; Inter 4.001 from Google Fonts css2 v20); web.py CONTENT_SECURITY_POLICY, STATIC_FILES, FONT_FILES, _static; pyproject static/fonts/*; test_web AstraWebTests.test_inter_font_is_served_by_astra_with_strict_allowlist_and_caching, AstraFoundationStaticTests.test_font_faces_point_at_the_served_files_only
- [x] style.css has semantic tokens (surface, line, muted text, spacing, radii, elevation) and a type scale, keeping today's palette values; the step-token contrast tests still pass
  proof: style.css :root tokens (--canvas/--surface*/--line*/--muted/--space-*/--radius*/--shadow-*/--fs-*/--dur-*); palette unchanged; test_web AstraFoundationStaticTests.test_tokens_type_scale_focus_and_reduced_motion; AstraStaticAssetTests step contrast tests pass
- [x] app.js writes no inline style attributes (replaced by classes) and a test pins that; no CSP errors in the browser console
  proof: app.js: 13 style= attributes replaced by .fine and .muted; test_web AstraFoundationStaticTests.test_no_inline_style_attributes_reach_the_page; Chromium console at 1440/1024/390 shows no CSP error (only the pre-login /api/me 403 and /favicon.ico 404, both pre-existing)
- [x] Every interactive element shows a :focus-visible ring and prefers-reduced-motion removes transitions and animation
  proof: style.css ':focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }' and reduced-motion block for *, *::before, *::after; Chromium: Tab to Sign out shows a 2px teal ring (lock9-shots/slice1-focus-*.png); test_tokens_type_scale_focus_and_reduced_motion
- [x] No sideways page scroll at 1440x900, 1024x768 or 390x844, and the phone header no longer overlaps; screenshots at all three sizes
  proof: Chromium: scrollWidth equals viewport at 1440, 1024 and 390 (was 2608 at 1440); no overlapping header items; lock9-shots/slice1-home-{1440,1024,390}.png; test_toolbar_wraps_instead_of_scrolling_sideways
- [x] Tests for the font route and headers and the static changes; full suite green; git diff --check, 0 CR bytes, node --check, jaira validate
  proof: tests/run.py Ran 461 tests, OK (was 456); git diff --check clean; 0 CR bytes in text files; node --check app.js ok; jaira validate errors false

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

## Progress
- **2026-09-25 04:33 · Claude** — Font choice (Claude, 2026-09-25): Google Fonts serves Inter 4.001 (name table 'Version 4.001;git-66647c0bb', css2 API revision v20) as variable woff2 split by unicode-range. latin is 48 KB and latin-ext 85 KB; the browser downloads latin-ext only when a name needs it. The rsms GitHub release (full InterVariable.woff2, about 350 KB) was not reachable from this container (github.com access to rsms/inter is not enabled). The Google subsets keep the tnum feature (checked in GSUB), which the tabular numerals rely on. Glyphs outside the subsets (arrows, check marks) fall back to the system font per glyph. Files are named with the version so they can be cached as immutable.
- **2026-09-25 04:43 · Claude** — Done in this pass (Claude, 2026-09-25): --muted is #5b6475 (5.3:1 on every surface; the older #667085 is kept where tests pin it, e.g. .owner-request p.muted). Labels no longer pass their bold weight into inputs (font: inherit made every select value bold). The header and toolbar only wrap here; slice 2 replaces them with the rail and top bar, so no more effort went into them. Left for later: /favicon.ico is still a 404 in the console (pre-existing).
