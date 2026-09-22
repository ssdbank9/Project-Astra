# Gantt steps contract

- Status: implemented in `D73AQW` (2026-09-21); defaults approved by Aly Jafferani, App Owner;
  amended 2026-09-22 after the adversarial review (GF-1/2/3/6/7/8/10/16, DTJ-06)
- Research basis: Gantt steps research (Asana, monday, Smartsheet, MS Project, TeamGantt,
  ClickUp, Wrike, Notion, DHTMLX, Bryntum, Frappe); DHTMLX split mode is the model
- Precedence: below `astra-product-ux-baseline.md`; this note only fixes the step rendering

## What a step is

A step is a subtask: a task whose `parent_task_id` points at the parent. No new entity,
endpoint or schema. `GET /api/tasks` already returns children flat, so the client groups
them by `parent_task_id`. `service.list_subtasks` returns `id, title, status, start_date,
due_date, criticality, progress, parent_task_id, owner_user_id, owner_name` so the detail
dialog and the Gantt share one shape.

## Rendering rules

- Steps are collapsed inline by default: the parent bar becomes a light track tinted by
  state (overdue, due soon, scheduled, blocked, closed, critical path) and each dated step is
  a `<button class="step">` segment positioned as a percentage of the track. A chevron with
  `aria-expanded` / `aria-controls` reveals the child rows; the choice is remembered per
  parent in `localStorage` (a per-viewer convenience only).
- The track is sized and tinted from the parent's **own** dates (GF-2). A step that starts
  before or ends after them does not stretch the track: it overhangs onto a dashed neutral
  extension (`.track-ext`), and the parent's tooltip and meta column say "Step N ends M days
  after the parent" (or "starts M days before"). Only a parent without dates takes its
  extent from its steps (the dashed "derived" track with a "Dates from steps" chip).
- Hue means step identity, in date order, using the Okabe-Ito palette (`--step-1` …
  `--step-7`) as a tint (22%; 35% for hues 5-7) with dark text. Each hue has a darker edge
  token (`--step-1-edge` … `--step-7-edge`: same hue and saturation, lower lightness) that
  draws the segment's 1px border and bottom stripe; the edge meets 3:1 against its tint,
  every track tint and white (WCAG 1.4.11), which `tests/test_web.py`
  `AstraStaticAssetTests` recomputes from the tokens (GF-3). State never borrows a step hue:
  completed/cancelled steps desaturate and gain ✓ / ×, on-hold steps get diagonal hatching,
  critical-path steps get a dark-red ring. An eighth step repeats hue 1 with a doubled
  bottom stripe, distinct from the on-hold hatching so both can show at once (GF-10).
- Colour is never the only carrier: the index label is always on the segment, the legend
  pairs index with colour, and the Schedule table twin carries the same rows as text.
- Steps that would draw under 8px, or have no free lane (overlapping steps use up to two
  lanes), fold into a `+N` disclosure that lists them: "+N not drawn at this scale (too small
  or overlapping)". `+N` sits just outside the track's right edge, or its left edge when the
  track ends near the end of the timeline, or in the meta column (with its list) when the
  track spans the whole timeline, so it never covers a drawn step; it has the same 44px hit
  area as a step (GF-1, GF-7).
- Undated steps are never placed on the bar. The "n steps need dates" chip lives in the meta
  column, whether or not the parent itself has dates, and opens the parent (GF-1, GF-16).
- Owner is shown as an initials chip on wide segments and always in the tooltip.
- Today and project marker lines are decorative and never intercept pointer events.

## Interaction rules

- One shared `role="tooltip"` element shows after ~150ms hover and on keyboard focus,
  stays while hovered, closes on pointer leave, blur or Escape (WCAG 1.4.13). It is text
  only and never uses the `title` attribute. A step's `aria-label` is short ("Step i of n,
  title"; a track's is "title, n steps"); the tooltip is linked with `aria-describedby` only
  while it is visible and only on the element that has focus or hover, and both clear when
  that element loses focus. Hovering or focusing `+N` never raises the track's tooltip
  (GF-8).
- The parent track is one tab stop; Left/Right/Home/End move between its steps; Enter or
  Space opens the focused record; click does the same. A step opens its own task record with
  a "◂ Parent" back-link; the parent's Subtasks list shows the same swatch and index.
- Focus never drops to `body` (WCAG 2.4.3): Escape in an open `+N` list returns focus to
  its button, a link inside the list focuses the button before the dialog opens so closing
  the dialog lands there, and a re-render (resize, filter or view change) refocuses the
  equivalent control by its `data-detail` / `data-more` / `data-expand` id (GF-6).
- `prefers-reduced-motion: reduce` removes the segment transitions.
- The Schedule table (Project, Task, Step #, Step, Owner, Start, Due, Status, Due state,
  Critical path) shares the Gantt's filters and is the default at phone width.
- Positions are applied through the CSSOM (`applyGeometry`), not inline `style`
  attributes, because the CSP is `style-src 'self'`.

## Out of scope for D73AQW

Zoom levels (Week/Month/Quarter), the right-hand task drawer, dependency connectors and
on-hold checkpoint markers. These remain in the baseline's Timeline backlog.
