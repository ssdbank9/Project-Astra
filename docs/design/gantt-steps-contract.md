# Gantt steps contract

- Status: the chart was rebuilt on 2026-11-16 as a replica of the shadcnstudio block
  `gantt-chart-04` (dashboard and application, "Gantt chart with dependencies"), on Aly
  Jafferani's instruction of 2026-11-09 ("Lets replicate the exact same thing"; "Lets keep our
  JS for now if everything functions as shadcn ui"). It is plain HTML, CSS and JavaScript: no
  framework, no build step, no CDN. The first version (`D73AQW`, 2026-09-21: step segments
  inside a parent track, a `+N` list, a shared tooltip, project flags, fit / week / month /
  quarter zoom) is gone; this note replaces its rules.
- Source: `src/astra/static/app.js` (the `gx*` functions), `style.css` (the `.gx-*` rules and
  the `--gx-*` tokens), `index.html` (`#gantt-host`, `#step-sheet`).
- Precedence: below `astra-product-ux-baseline.md`; this note only fixes how the chart is
  drawn and what it does.

## What a step is

A step is a task. A task whose `parent_task_id` points at another task is a step of that
task. No new entity and no new endpoint: `GET /api/tasks` returns every task flat, and the
client groups them by `parent_task_id`. A phase is a row that has steps under it: every
project is a phase, and so is every task that has sub-tasks. A phase's code is the project's
initials (`REL`), and for a task that has steps that code and its number by date within the
project (`REL-01`).

## Layout

- One card: a toolbar, then a Step pane on the left (Step, Owner, Status, Dates, Length) that
  stays put while the day grid on the right scrolls sideways; both headers stay at the top
  while the rows scroll. Rows are 48px tall. The pane is 560px wide in a card of 1024px or
  more, 288px from 640px, and 192px below that, where it shows the step name only.
- The header has two rows: ISO 8601 weeks with their date range (`W24 · Jun 8 – 14`) over one
  cell per day. Saturday and Sunday are shaded. Today is a dark pill in the header and a
  marked column in the grid, and it follows the project's own today on a project page.
- A phase row shows a chevron, the name, the code, `done/total` steps and the average
  progress, and in the grid a thin summary bar over the dates of its steps. A click on the
  row folds or unfolds it; the choice is remembered in `localStorage`
  (`astra.gantt.collapsed`) and phases start open. A phase that is a task also has a button
  that opens the task.
- A step row shows a status icon, the name (a button that opens the task panel), how many
  steps it depends on, the owner's initials, a status badge, the dates and the length in
  days. Its bar starts on its start day and is as wide as its days; it carries the status
  icon, the name, the progress as a darker fill and a percentage, and the owner's initials.
  A bar that runs past the shown period is cut square at that end.
- A milestone (`is_milestone`) is a flag on its due date with its name beside it.
- An undated step keeps its row and has no bar.

## Periods and zoom

- Month (the default) shows one calendar month; Week shows Monday to Sunday. The previous and
  next buttons step one period, Today comes back to today. The choice of Week or Month is
  remembered (`astra.gantt.period`).
- The chart opens on today's period when any work falls in it, otherwise on the period of
  the dated work nearest today. It keeps the period the user moved to until the page shows
  other projects.
- Zoom in and zoom out step the day width of the month view through 32, 40, 48, 64, 88 and
  120 pixels, as the block does (re-observed 2026-11-17), kept as pixels
  (`astra.gantt.daywidth`); the button at an end is disabled. A week always fills the
  width it has (at least 48px a day), so zoom is off in the week view.

## Status

Astra's task statuses and flags fold into the block's five, each with its own icon and
colour token. The first rule that matches wins:

| Shown as | When | Token |
| --- | --- | --- |
| Completed | status `completed` | `--gx-green` |
| Blocked | waiting on an unfinished predecessor (`is_blocked`), or status `on_hold` | `--gx-destructive` |
| Queued | status `cancelled` or `abandoned` | `--gx-zinc` |
| At Risk | overdue, or status `delayed` | `--gx-amber` |
| In Progress | status `in_progress`, `submitted`, `reopened` or `changes_requested` | `--gx-sky` |
| Queued | anything else (`draft`, `assigned`) | `--gx-zinc` |

Colour is never the only carrier: the badge and the bar's accessible name say the status in
words, and the badge's `title` keeps Astra's own status name.

## Dependencies

- A dependency is finish to start. One arrow runs from the right edge of the predecessor's
  bar to the left edge of the step that waits for it, with 6px rounded corners; when the
  step starts too close or earlier, the line goes round between the rows and comes in from
  the left. An arrow is drawn only when both ends are drawn: a step hidden by a filter, by
  a folded phase or by the edge of the period takes its arrows with it.
- An arrow is muted when idle, dark while the pointer or the keyboard focus is on either
  end, and red when it is a conflict: the step starts on or before the day its predecessor
  ends. A conflict stays red under the pointer.
- The Dependencies switch turns the arrows off and on (`astra.gantt.deps`).
- Dependencies are created and removed through `POST` and `DELETE /api/task-dependencies`
  (the task panel) and at creation through `POST /api/tasks`; all three are for the App
  Owner and the project's manager only.

## Changing the schedule

- An open, dated bar of a project the user manages (App Owner or the project's manager) can
  be dragged with a mouse: the body moves both dates, the grips at its ends move one. The
  bar snaps to whole days and is placed from the dates it would get, cut to the shown
  period like any other bar; while the pointer is down the row's Dates and Length, a tip
  beside the pointer and the arrows follow it, so a conflict shows before the drop. Escape
  puts everything back.
- The drop is sent to `POST /api/tasks/{id}/reschedule` under a drag lease, with the
  revision the browser had. `service.py` decides: a member, a viewer and anyone outside the
  project are refused there whatever the page shows, a stale revision is refused, a move
  with consequences asks first, and an ordinary move is in the task's history with an Undo.
- Touch and phone widths never drag; they use the task panel's date fields.
- New Step (shown to someone who may add a task to an open project) opens a sheet from the
  right: Name, Phase (a project or a task that has steps), Type (Task or Milestone), Owner,
  Status, Start and End (both today to begin with), Progress, Depends on, Note, and a Close
  button. Create posts one `POST /api/tasks` with
  `predecessor_task_ids`, `is_milestone` and `progress`; a milestone sends its one date as
  the due date. A step cannot depend on the phase it sits in. Enter creates; a double click
  posts once. A refusal is shown in the sheet, which stays open.
- Edit Step (added 2026-11-17, as in the block): a click on a bar, or Enter or Space on it,
  opens the same sheet filled from the step, for a step the user may manage that is not
  closed or in review; anyone else, or such a step, gets the task panel. It sends only what
  changed, through the calls the task panel uses: `POST /api/tasks/{id}/parent` first (so
  the owner is checked where the step will sit), then `POST /api/tasks/{id}` with the
  revision and a reason when the dates or the status change, then `POST` / `DELETE
  /api/task-dependencies` (a removal carries the reason). Confirmations are the panel's.
  Depends on leaves out the step, steps inside it and steps that wait on it. Type cannot
  change (the service has no such change). "Open task" opens the task panel. The block's
  Delete is "Cancel step" (Aly, 2026-11-17): a question with a reason, then the status
  Cancelled through the ordinary update; a manager's becomes an Owner request. Typing takes
  the panel's edit lease; closing lets it go.
- Filter hides steps by status and by owner in the browser only; counts sit beside each
  box, and the button is marked while anything is hidden. A phase with no step left is
  hidden with them; phase totals do not change.

## Kept from Astra

- The Schedule table (Project, Task, Step #, Step, Owner, Start, Due, Status, Due state,
  Critical path) is the same rows as text, shares the page's filters, carries the Move task
  dialog, and is the default at phone width. Its step swatches keep the Okabe-Ito hues
  (`--step-1` … `--step-7`) with a darker edge token each (`--step-1-edge` …
  `--step-7-edge`) that meets 3:1 against its tint and white (WCAG 1.4.11); an eighth step
  repeats hue 1 with a doubled stripe.
- The Plan select (alternative work plans) and the due-date bands above the chart.
- Positions travel as `data-l`, `data-w` and `data-pc` attributes and are applied through
  the CSSOM (`gxPlace`), because the Content-Security-Policy is `style-src 'self'`.
- Focus never drops to `body` (WCAG 2.4.3): a re-render gives focus back to the same bar,
  step name or phase toggle; Escape in the Filter popover gives it back to the Filter
  button. A bar is a focus stop that names itself ("Title · Status · 70%"); as in the block
  it opens Edit Step, and the step name in the pane opens the task. Focus rings are Astra's
  teal `--focus` ring (3:1 or better), not the block's faint grey halo.
- `prefers-reduced-motion: reduce` removes the sheet's slide-in.

## Not in the chart any more

Step segments inside a parent bar, the `+N` list, the "n steps need dates" chip, the shared
tooltip, project start and target flags, critical-path colouring, the state and step
legends, the chart's drop zones for reordering (the Schedule table's Move task dialog
remains), fit and quarter zoom, and dragging a parent task's own bar.

## Tests

`tests/test_gantt_zoom.py` (layout, bars, status, week and month, zoom, filter, toolbar),
`tests/test_gantt_dependencies.py` (arrows), `tests/test_gantt_range.py` (periods and
navigation), `tests/test_frontend_gaps_views.py` `GanttExpandAndOverflowTests` (folding,
phone default), `tests/test_web.py` `AstraGanttDragDriverTests` (drag, resize, leases),
`tests/test_gantt_new_step.py` (the sheet; and who may create a step, move a bar or change
a dependency, in the service and over HTTP, role by role).
