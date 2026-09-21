# Gantt steps contract

- Status: implemented in `D73AQW` (2026-09-21); defaults approved by Aly Jafferani, App Owner
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
- Hue means step identity, in date order, using the Okabe-Ito palette
  (`--step-1` … `--step-7`) as a 22% tint with a solid stripe and dark text. State never
  borrows a step hue: completed/cancelled steps desaturate and gain ✓ / ×, on-hold steps get
  diagonal stripes, critical-path steps get a dark-red ring. An eighth step repeats hue 1
  with hatching.
- Colour is never the only carrier: the index label is always on the segment, the legend
  pairs index with colour, and the Schedule table twin carries the same rows as text.
- Steps under 8px fold into a `+N` disclosure that lists them; overlapping steps use up to
  two lanes. Undated steps are never placed on the bar; an "n steps need dates" chip opens
  the parent. A parent without dates gets a dashed track derived from its steps and a
  "Dates from steps" chip.
- Owner is shown as an initials chip on wide segments and always in the tooltip.

## Interaction rules

- One shared `role="tooltip"` element shows after ~150ms hover and on keyboard focus,
  stays while hovered, closes on pointer leave, blur or Escape (WCAG 1.4.13). It is text
  only and never uses the `title` attribute. The same text is the step's `aria-label`.
- The parent track is one tab stop; Left/Right/Home/End move between its steps; Enter or
  Space opens the focused record; click does the same. A step opens its own task record with
  a "◂ Parent" back-link; the parent's Subtasks list shows the same swatch and index.
- `prefers-reduced-motion: reduce` removes the segment transitions.
- The Schedule table (Project, Task, Step #, Step, Owner, Start, Due, Status, Due state,
  Critical path) shares the Gantt's filters and is the default at phone width.
- Positions are applied through the CSSOM (`applyGeometry`), not inline `style`
  attributes, because the CSP is `style-src 'self'`.

## Out of scope for D73AQW

Zoom levels (Week/Month/Quarter), the right-hand task drawer, dependency connectors and
on-hold checkpoint markers. These remain in the baseline's Timeline backlog.
