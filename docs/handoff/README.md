# Astra handoff index

## 2026-11-09 — jaira retired; this file is the record of work

Aly retired the jaira board on 2026-11-09 (see `DECISIONS_LOG.md`). Nothing
below that mentions tickets, lanes or board counts is to be acted on through
jaira any more; `.jaira/` is read-only history. From now on this file carries
status and open work, updated in the same commit as the work.

Status at `7bf2f1a` (plus this commit):

- MXY7BG hosted attachments: slice 1 (`18c4e54`) and slice 2 (`8fdd9d5`) are
  pushed and reviewed. Slice 3 (App Owner-only audited permanent direct
  links, Owner Items 15-16, `5220018`) and slice 4 (OCI Object Storage backend
  and a verified backend migration with rollback, Items 6-7, `877bde1`) were
  accepted by Aly on 2026-11-16 ("Accept both"). Both are in "MXY7BG slices 3
  and 4" below. Acceptance is of the built work only: nothing is provisioned
  or deployed. Aly went through the eleven questions of that section on
  2026-11-17 (under each question there, and in `DECISIONS_LOG.md`). Nine
  are answered; the outbound network rule and the bucket backup are left
  open until a bucket is taken up. The last five storage answers are
  Claude's recommendations, which Aly took. Uploads stay in the server
  folder for now. The one change the answers ask for now, a download
  through a direct link showing no person in the task history, is built in
  `7bf2f1a` (step 3.6) and was accepted by Aly on 2026-11-17 ("Accept").
  Open work: each file's row is to record its bucket before the first real
  use of a bucket. Nits left: two owners saving the attachment settings at
  once overwrite each other (both audited);
  `attachment_settings` and `attachment_links` are not in the backup
  required-table list.
- Gantt chart replica of the shadcnstudio.com Gantt with dependencies, in
  plain JS: built, tested, reviewed and pushed on 2026-11-16; it waits for
  Aly's acceptance. Status, the ticked feature checklist and the judgment
  calls for Aly are in "Gantt chart replica — 2026-11-16" below.
- Waiting for Aly's acceptance from before the board was retired: B3Y1XY
  (password reset fixes), Z9JCZ6, MTEDTM, AX572Q and the six tested tickets
  recorded in `DECISIONS_LOG.md` on 2026-11-08; 0RHNMG is a duplicate of
  JRNDC8 once B3Y1XY is accepted. Acceptance is now a line from Aly in chat,
  recorded here.

## Gantt chart replica — 2026-11-16

Aly's instruction (2026-11-09): "review shadcnstudio.com see the gantt chart and dependencies
they have developed using react, tailwind css and shadcn/ui. Lets replicate the exact same
thing", in plain JavaScript ("Lets keep our JS for now if everything functions as shadcn ui";
`DECISIONS_LOG.md`). The block replicated is `gantt-chart-04` (the one with dependency arrows).

Status: built, tested, reviewed, pushed in this commit. It waits for Aly's acceptance in chat.
Nothing on the checklist needed React. The contract is
`docs/design/gantt-steps-contract.md`.

What was checked, and how:

- Tests: the full suite, result in the commit message. New and rewritten Gantt tests:
  `tests/test_gantt_zoom.py`, `tests/test_gantt_dependencies.py`, `tests/test_gantt_range.py`,
  `tests/test_gantt_new_step.py`, `GanttExpandAndOverflowTests` in
  `tests/test_frontend_gaps_views.py`, `AstraGanttDragDriverTests` in `tests/test_web.py`.
- Authorization stays in `service.py`. A drag still goes through
  `POST /api/tasks/{id}/reschedule` (unchanged: lease, revision, impact confirmation, Undo,
  audit). New Step goes through the existing `POST /api/tasks`; `create_task` now also takes
  `predecessor_task_ids` and `is_milestone` (it already took `progress`), behind the same
  `can_manage_project` check. Service and HTTP tests cover App Owner, manager, member, viewer
  and outsider for creating a step (`NewStepServiceTests`, `NewStepHttpTests`) and, on the
  endpoints the chart already used, for moving a bar and for adding or removing a
  dependency (`ScheduleRoleServiceTests`, `ScheduleRoleHttpTests`): a member, a viewer and
  an outsider are refused and nothing is written.
- Guard removal: 36 guards were removed one at a time in throwaway copies (23 before the
  review, 16 after it, three of them repeated); each removal made at least one test fail.
- Independent review: a second agent read the whole diff without editing it. It found no
  high-severity defect and nine smaller ones; all nine were fixed, each with a test:
  1. Enter in the New Step sheet pressed Discard (the first submit button). Discard is now a
     plain button; Create is the sheet's only submit button.
  2. The chart's focus rings were a faint grey (about 1.5:1). They are now Astra's teal
     `--focus` ring with a white gap, tested at 3:1 or better on white and on muted rows.
  3. The old focus-ring test could not fail; the new one checks the colour and the contrast.
  4. Dragging a bar that runs past the month edge drew one thing and saved another. A dragged
     bar is now placed from the dates it would get, cut to the month as the chart cuts it.
  5. An arrow kinked when the gap between bars was 12 to 24px; it now always runs one way.
  6. A step could be made to depend on its own phase (always a conflict). The sheet no longer
     offers it and `create_task` refuses it.
  7. `create_task` linked to a predecessor someone else had locked; it now refuses, as
     `add_task_dependency` does.
  8. A double click on Create posted twice, and a failed reload after creating wrote its error
     into the closed sheet. One request at a time; a failed reload is a toast.
  9. Filter choices survived a change of page with no box left to untick; focus in the Filter
     popover was lost on a redraw; the owner and the dependency count were not spoken. All fixed.
- Browser: checked in the in-app browser against `tests/ui_fixture_server.py` at 1440, 768
  and 375 px wide: month and week, previous / next / Today, zoom, fold and unfold, Filter,
  Dependencies switch, hover highlight, drag with the Undo toast, and a milestone created
  through New Step under a phase with a predecessor. Not checked in a browser: a signed-in
  viewer or member (one test owner exists in the fixture; those roles are covered by tests).

### Feature checklist (from the catalogue of the block, every item ticked)

References are `file:line` at this commit, then the test that fails without it. `app.js`,
`style.css` and `index.html` are in `src/astra/static/`; `zoom`, `deps`, `range`, `step`,
`views` and `web` stand for `tests/test_gantt_zoom.py`, `test_gantt_dependencies.py`,
`test_gantt_range.py`, `test_gantt_new_step.py`, `test_frontend_gaps_views.py` and
`test_web.py`.

1. Layout
   - [x] Card with border and 10px radius; the chart scrolls inside it. `style.css:807`,
     `style.css:849`. Test: zoom `test_the_chart_scrolls_inside_its_card_in_both_directions`.
     Adapted: the block fills the viewport; Astra's card sits under the page's filters, so
     its height is `max(360px, 100dvh - 15rem)`.
   - [x] Toolbar: title, previous / next group, Today, Week | Month select, Dependencies
     switch, Filter, New Step. `index.html:127`, `app.js:374`.
     Tests: zoom `test_the_toolbar_has_the_controls_of_the_block_and_astras_own`, range
     `test_previous_and_next_are_grouped_and_today_is_its_own_button`.
   - [x] One scroller, both directions, hidden scrollbars, with the pinned pane and the
     timeline side by side. `style.css:849`, `style.css:851`.
     Test: zoom `test_the_step_pane_stays_put_while_the_days_scroll_sideways`.
   - [x] Left pane 192 / 288 / 560 px with columns Step, Owner, Status, Dates, Length that
     drop out when narrow. `app.js:136` (`GX_PANE`), `style.css:852`.
     Tests: zoom `test_the_pane_width_follows_the_width_of_the_card`,
     `test_the_pane_has_the_five_columns_of_the_block`. Adapted: the width follows the
     card's width through `data-pane`, not CSS container queries.
   - [x] Phase row: chevron, name, code badge, `done/total · %`, the whole row folds.
     `app.js:271`, `app.js:349`. Tests: zoom
     `test_a_project_is_the_top_phase_and_a_task_with_steps_is_a_phase_under_it`, views
     `GanttExpandAndOverflowTests` (13 tests).
   - [x] Step row: indent guide, status icon, name, link count, avatar, status badge, dates,
     length. `app.js:281`. Tests: zoom
     `test_the_pane_row_shows_the_owner_the_status_the_dates_and_the_length`,
     `test_a_step_that_waits_for_others_shows_how_many`.
   - [x] Timeline header: ISO week groups over day cells, weekends shaded, today as a pill,
     "Mon 9" cells in the week view. `app.js:258`. Tests: zoom
     `test_the_header_groups_days_into_iso_weeks_with_their_date_range`,
     `test_today_is_a_pill_in_the_header_and_a_marked_column`,
     `test_saturday_and_sunday_are_marked_in_the_header_and_the_grid`,
     `test_the_week_view_shows_monday_to_sunday_of_todays_week`.
   - [x] Timeline body: column layer, arrow layer that takes no clicks, 48px rows with bars.
     `app.js:301`, `style.css:908`. Tests: deps
     `test_the_layer_covers_every_day_and_every_row`,
     `test_the_arrow_layer_never_takes_a_click_from_a_bar`, zoom
     `test_a_row_is_48_pixels_tall_like_the_arrow_geometry_assumes`.
   - [x] Phase summary bar with its percentage. `app.js:277`. Test: zoom
     `test_a_phase_draws_a_summary_bar_over_the_dates_of_its_steps`.
   - [x] Zoom in / zoom out buttons at the bottom right. `index.html:150`,
     `style.css:942`. Test: zoom `test_zoom_steps_through_five_day_widths_and_stops_at_each_end`.
2. Scale, zoom, navigation
   - [x] Month view, 48px days, zoom 32 / 48 / 64 / 88 / 120, bars cut to the month.
     `app.js:159`, `app.js:266`. Tests: zoom
     `test_the_month_view_draws_one_cell_per_day_at_the_default_width`,
     `test_the_zoom_button_at_an_end_is_disabled`,
     `test_a_bar_that_starts_before_or_ends_after_the_period_is_cut_and_loses_that_grip`.
   - [x] Week view: seven columns that fill the width, "Week of Nov 9, 2026".
     `app.js:162`. Tests: zoom `test_the_week_view_shows_monday_to_sunday_of_todays_week`,
     `test_a_week_day_never_gets_narrower_than_48_pixels`, range `test_a_week_runs_from_monday_to_sunday`.
   - [x] Previous / next by one period, Today, scroll position kept. `app.js:168`,
     `app.js:505`. Tests: range `test_next_and_previous_step_one_month_and_today_comes_back`,
     `test_in_the_week_view_the_buttons_step_one_week`,
     `test_the_chosen_period_is_kept_across_redraws_of_the_same_projects`.
   - [x] Bar and milestone geometry. `app.js:266`, `app.js:284`.
     Tests: zoom `test_a_bar_sits_on_its_start_day_and_is_as_wide_as_its_days`,
     `test_a_milestone_is_a_flag_centred_on_its_day`.
3. Bars
   - [x] Task bar: `role=button`, focus stop, "Name · Status · 70%", status tint, progress
     fill, icon, name, percentage, avatar, grab cursor, focus ring. `app.js:290`,
     `style.css:919`. Tests: zoom `test_a_bar_names_its_step_status_and_progress`,
     `test_a_draggable_bar_shows_the_grab_cursor_and_its_grips_resize`,
     `test_the_bars_focus_ring_is_visible`.
   - [x] Resize grips at both ends, whole days, Dates and Length live. `app.js:1285`,
     `app.js:333`. Tests: web `test_the_end_grip_changes_the_due_date_and_never_passes_the_start`,
     `test_the_start_grip_changes_the_start_date_and_never_passes_the_due_date`, deps
     `test_a_resized_bar_updates_its_dates_and_length_while_the_pointer_is_down`.
   - [x] Drag to move by whole days; successors are not pushed. Same code. Tests: web
     `test_a_drag_starts_after_5px_and_snaps_to_whole_days`,
     `test_dropping_a_bar_posts_the_new_dates_under_a_drag_lease_and_lets_the_server_redraw`.
   - [x] Milestone: 28px circle with a flag and a label, draggable, no grips.
     `app.js:284`, `style.css:938`. Tests: zoom
     `test_a_milestone_is_a_flag_centred_on_its_day`,
     `test_only_open_dated_bars_of_a_project_the_user_manages_can_be_dragged`.
   - [x] A click on a bar does nothing; the tooltip is the `title`. `app.js:2051`.
     Test: views `test_a_click_on_a_bar_opens_nothing_and_folds_nothing`.
   - [x] Bars are in the tab order with a focus ring; arrow keys do not move them. Tests:
     deps `test_keyboard_focus_on_a_bar_highlights_its_arrows_like_the_pointer_does`,
     `test_space_on_a_bar_does_not_scroll_the_page`.
4. Status model
   - [x] Five statuses with their icons and colours. `app.js:180`,
     `style.css:802`. Tests: zoom `test_astras_statuses_fold_into_the_five_colours_of_the_block`,
     `test_each_status_sets_one_colour_variable_from_a_root_token`.
   - [x] Phase progress "0/5 · 40%". Test: zoom `test_a_phase_counts_its_finished_steps_and_averages_their_progress`.
5. Dependencies
   - [x] Finish-to-start predecessors, shown as a count with a link icon. Data:
     `task_dependencies` through `GET /api/tasks`. Test: zoom `test_a_step_that_waits_for_others_shows_how_many`.
   - [x] Dependencies switch, on by default. `index.html:140`, `app.js:322`.
     Tests: deps `test_the_switch_clears_the_arrows_and_remembers_the_choice`,
     `test_the_switch_is_a_real_checkbox_with_the_switch_role_and_starts_on`.
   - [x] SVG arrows with three states and their arrowheads. `app.js:298`,
     `style.css:909`. Tests: deps `test_there_is_an_arrowhead_for_each_of_the_three_states`,
     `test_each_state_takes_its_colour_from_a_token`.
   - [x] Orthogonal routing with 6px corners, forward and round-the-row. `app.js:308`.
     Tests: deps `test_a_forward_arrow_leaves_the_right_edge_turns_12px_out_and_enters_the_left_edge`,
     `test_with_less_room_the_line_goes_round_between_the_rows_and_comes_in_from_the_left`,
     `test_a_successor_that_starts_earlier_is_reached_round_the_predecessors_row`.
   - [x] Active while hovered or dragged; conflict wins. Tests: deps
     `test_hovering_a_bar_turns_the_arrows_at_both_its_ends_active`,
     `test_a_conflict_stays_red_under_the_pointer`.
   - [x] Conflict when the successor starts on or before the day the predecessor ends,
     live while dragging. Tests: deps
     `test_a_step_that_starts_on_or_before_the_day_its_prerequisite_ends_is_a_conflict`,
     `test_a_dragged_bar_takes_its_arrows_along_and_shows_the_conflict_it_would_cause`.
   - [x] Folding a phase hides the arrows of its steps. Test: deps
     `test_collapsing_a_phase_drops_the_arrows_of_the_steps_inside_it`.
   - [x] Links are created in the New Step sheet's "Depends on" list; existing links are
     edited in the task panel as before. `app.js:394`, `service.py:1455`.
     Tests: step `test_create_posts_one_task_with_its_predecessors`,
     `test_each_predecessor_is_one_finish_to_start_row_and_one_audit_event`.
6. Filter and New Step
   - [x] Filter popover by status and owner with counts. `app.js:358`.
     Tests: zoom `test_the_popover_lists_the_five_statuses_and_the_owners_with_counts`,
     `test_unticking_a_status_hides_its_steps_and_marks_the_button`,
     `test_unticking_an_owner_hides_that_persons_steps`.
   - [x] New Step sheet from the right with the block's fields. `index.html:223`,
     `app.js:420`. Tests: step `NewStepSheetTests` (13 tests),
     `NewStepMarkupTests`, `NewStepServiceTests`, `NewStepHttpTests`.
7. Visual tokens
   - [x] The block's neutral palette and status hues as `--gx-*` tokens in `:root`.
     `style.css:98`. Tests: zoom `test_each_status_sets_one_colour_variable_from_a_root_token`,
     `tests/test_frontend_integrity.py` `test_colours_outside_root_use_tokens`.
   - [x] 12px secondary text, 14px names, tabular numerals. Astra keeps its Inter typeface
     (the block uses Geist).
   - [x] Dark mode: not applicable. Astra has no dark mode; the catalogue's line about
     "existing dark tokens" was wrong.
8. Not in the block, and not built: day or quarter zoom, drag-to-connect handles, keyboard
   nudging of bars, critical path colouring, baselines, auto-pushing successors, bar menus.

### Judgment calls for Aly to confirm or reverse

Removed from the chart, because the block has no such thing:

- step segments inside a parent bar, the `+N` list and the "n steps need dates" chip;
- project start and target flags, the rich tooltip, critical-path colouring, both legends;
- drop zones and row handles for reordering in the chart (the Move task dialog stays in the
  Schedule table);
- fit, week, month and quarter zoom levels (replaced by Week | Month and the day-width zoom);
- dragging a parent task's own bar (a parent is now a phase with a summary bar);
- a click on a bar opening the task (the step name in the pane opens it).

Kept from Astra although the block has no such thing:

- the Schedule table switch (still the default at phone width), the Plan select and the
  due-date bands above the chart;
- the drag tip beside the pointer, the Undo toast and the impact confirmation;
- an "open" button on a phase that is a task, screen-reader status text, and arrows that
  highlight on keyboard focus as well as on hover;
- Astra's 44px touch targets below 1024px, also on the chart's toolbar.

Choices where the block gives no answer:

- A project is always the top phase; a task with sub-tasks is a phase under it.
- Astra's statuses map onto the five colours as the contract's table says; "Blocked" also
  means waiting on an unfinished predecessor, so a plan with many links shows many red
  badges.
- The chart opens on the month of the work nearest today when today's month is empty.
- The sheet's Status offers the four statuses a manager may create (Draft, Assigned, In
  progress, Delayed); a milestone's one date is stored as its due date.
- Zoom is off in the week view (unverified against the block).
- Unverified against the block, taken from the observed DOM: the 32px toolbar buttons, the
  line between the two header rows, the alpha of a milestone's border.
- One colour differs from the block on purpose: the grey of secondary text is a step
  darker (`--gx-muted-fg`, lightness 0.52 instead of 0.556), so 12px text reaches 4.5:1 on
  the muted rows as well as on white.
- Focus rings in the chart are Astra's teal ring, not the block's soft grey halo (which was
  about 1.5:1 on white). The idle arrow keeps the block's soft grey; it is decoration, and an
  arrow turns dark when its bar has focus.
- Bars keep `role="button"` with nothing on Enter, as in the block; the step name in the pane
  opens the task.

Follow-up for Aly to decide, outside this change: the task form and the project form have the
same "Enter presses Cancel" order of buttons that the New Step sheet had (`index.html`,
`#task-form` and `#project-form`).

## MXY7BG slices 3 and 4 — 2026-11-16

Aly, 2026-11-09: "Do not create jaira this time. create small actionable steps
to get to the desired results. also work on slices 3 and 4". The steps are
below; a step is ticked in the commit that pushes it.

### Slice 3: App Owner-only permanent direct links (Owner Items 15-16)

Status: accepted by Aly on 2026-11-16 ("Accept both"). Built, tested, reviewed
and pushed in `5220018` (on the branch since the merge `575f2fa`; full suite
there: 1299 tests, OK, 2 skipped on Windows). Nothing is deployed. Aly
answered the questions below on 2026-11-17; the one change they ask for
(question 4) is built in step 3.6 (`7bf2f1a`) and was accepted by Aly on
2026-11-17.

- [x] 3.1 Schema v25 `attachment_links`: one active link per uploaded file,
  the token stored only as a SHA-256 hash, who created and who revoked it,
  when and why.
- [x] 3.2 Service: create (App Owner only, after an explicit confirmation that
  the link bypasses task access), revoke with a reason, resolve a token to a
  file. Creation, revocation and every download through a link are recorded on
  the task; every App Owner is told of creation and revocation.
- [x] 3.3 Web: `GET /files/<token>` streams the file with no session
  (`no-store`, download only); owner routes create and revoke.
- [x] 3.4 UI: "Create direct link" shows the warning first, then the link
  once with a copy button; "Revoke direct link" asks for a reason.
- [x] 3.5 Tests at service, HTTP and UI level, every guard removed fails a
  test, independent review, browser check, full suite.
- [x] 3.6 Question 4 (Aly, 2026-11-17, "Show no person"): a download through
  a direct link shows no person in the task history. Pushed in `7bf2f1a`
  (full suite: 1381 tests, OK, 2 skipped on Windows); accepted by Aly on
  2026-11-17 ("Accept"). The row is still stored
  under the owner who created the link, because a history row needs a
  person, and the task history API and the page leave the person out. The
  creator stays named on the "Direct link created" row and, while the link
  is active, in the attachment list. Checked: service, HTTP and UI tests; 10
  guards removed in a complete copy that passed untouched, each failing a
  test; an independent read with no blocking finding; in a browser, the
  existing link downloads of a local test task showed the date and reason
  only, and other rows kept their names. Left as it was: a creator who is no
  longer a manager still sees the link's history rows on a task they can
  open (the rows count as theirs); the rows now name nobody.

What an owner gets:

- A direct link downloads one uploaded file without signing in, so it does
  not check task access. Only an App Owner can create one, and only after a
  warning that says so. A file has at most one active link.
- The link is shown once. Astra keeps only a fingerprint of it, so a lost
  link is replaced by revoking it and creating a new one.
- Any App Owner can revoke a link, with a reason of up to 500 characters.
  Removing the file ends its link.
- The task history shows when a link was created, revoked and used. A use
  names no person (step 3.6).
- The link never reaches a log. Astra's request log, Waitress's own log,
  Caddy's access log and Caddy's own log write `/files/[redacted]` or
  `/files/redacted`. Only the exact path `/files/<token>` is served, so no
  other spelling of it can both work and be logged.

How it was checked:

- Tests: full suite at the merge `575f2fa`: `Ran 1299 tests`,
  `OK (skipped=2)`. New tests are
  `DirectLinkTests`, `WaitressLogTests` (a real Waitress server) and the direct
  link tests in `HttpTests`, `WsgiStreamingTests` and `GuardUnitTests`
  (`tests/test_hosted_attachments.py`), `tests/test_hosted_attachments_ui.py`,
  `DirectLinkMigrationTests` (`tests/test_db.py`) and the log filter checks in
  `tests/test_deploy_config.py`.
- Roles: the service and HTTP tests refuse a manager, a member, a viewer, a
  chairman, the task's assignee and an outsider for both creating and
  revoking, and allow a secondary owner.
- Guard removal: 147 guards were removed one at a time in a complete
  throwaway copy of the final code, after the untouched copy had passed. Each
  removal made at least one test fail. Two guards in the browser code were
  found untested on the way and got tests.
- Independent review: an agent that did not write the code read the diff
  without editing it, three times. Round 1 found one blocker (Waitress wrote
  the link to its own log) and ten smaller items. Round 2 found no blocker and
  three items: a tab or line break inside the path was still served, Caddy's
  own log had no filter, and a second click while a request was on its way
  could replace the panel showing the link. All were fixed with tests.
  Round 3 read those fixes, confirmed all three and found no blocker; it
  asked for one more check in the runbook step, which was added.
- Browser: checked on a local server as an App Owner: the warning, cancel,
  confirm, the link shown once, copy, a redraw that keeps the link, Done,
  revoke with a reason, keyboard focus, the buttons switched off while a link
  waits, the history labels, and the server log showing `/files/[redacted]`.
  Not checked in a browser: any role other than App Owner (covered by tests).
- Unverified: the Caddy log filters have not run inside a real Caddy. The
  pattern is tested with Python's regular expressions only. Stage 9 of
  `DEPLOYMENT_RUNBOOK.md` has the check to run on the server before any direct
  link is created there.

Questions for Aly, answered on 2026-11-17 (today's behaviour is stated first):

1. A link has no expiry and no download limit, and every download adds a
   history row. A chat app that previews links counts as a download. Should a
   link expire, or have a cap?
   Answer: keep permanent. No expiry and no cap; a link ends when an App
   Owner revokes it.
2. Caddy logs every direct link request as `/files/redacted`, so the access
   log cannot say which link was used, and the task history has no client
   address. Should the history record the address?
   Answer: keep as is. No address is recorded. Claude had recommended
   recording it for App Owners only; Aly chose not to.
3. A link keeps working after the owner who created it is demoted or
   deactivated, and after its project is closed. Should any of those end it?
   Answer: none of them ends it.
4. A download through a link is recorded under the owner who created the
   link, because nobody is signed in. Is that the right name to show?
   Answer: show no person. The row is to say only that the file was
   downloaded through a direct link, with the creator named in the link's
   own details. Built in step 3.6 (`7bf2f1a`); accepted by Aly on
   2026-11-17.
5. Restoring an older backup brings back a link that was revoked after that
   backup. Accept this, or add "revoke every link" to the restore steps?
   Answer: accept as is.

Small items left as they are: a reason made only of invisible characters is
accepted; after Done or a revoke the keyboard focus returns to the top of the
page; while one link request is on its way, a click on a link button of
another task does nothing and says nothing; a refused request with a
misspelt path (a 404) can still put the token it carried into the
development server's log; a JSON body nested about 100,000 levels deep gives
a 500 on any JSON route (older than this slice).

A correction to earlier guard checks: the throwaway copy used for them lacked
the repository's root files, so one test in `tests/test_deploy_config.py`
always failed there and a "caught" result from that module proved nothing.
The copy is now complete and is tested untouched first. The three slice 2
guards this affected (the default server ceiling, Waitress's cap, the
Caddyfile's shipped limit) were checked again and each still fails a test
when removed.

### Slice 4: object storage backend and verified migration (Owner Items 6-7)

Status: accepted by Aly on 2026-11-16 ("Accept both"). Built, tested, reviewed
and pushed in `877bde1` (full suite: 1379 tests, OK, 2 skipped on Windows).
Aly went through the decisions below on 2026-11-17: uploads stay in the
server folder for now, and decisions 2 and 3 are left open until a bucket is
taken up. Nothing is provisioned or deployed: no bucket, no key, no change on
any server. The code has never talked to a real OCI tenancy.

- [x] 4.1 `object_storage.S3Storage`: OCI Object Storage through its
  S3-compatible API, signed with the standard library (no new dependency),
  behind the same methods as the folder backend. `ASTRA_STORAGE_BACKEND`
  (`folder` or `s3`) chooses the one active backend; the bucket, region,
  endpoint and Customer Secret Key are settings Aly places on the server.
- [x] 4.2 A test bucket (`tests/fake_s3.py`) that checks every signature
  itself; the storage tests run against both backends.
- [x] 4.3 Each upload's row records the backend holding it (schema v26).
  `astra storage-migrate --to <backend>` copies each file, checks size and
  SHA-256, reads the copy back, and only then switches the row. The old copy
  is kept, so the same command toward the old backend is the rollback.
  `astra storage-prune` deletes old copies after verifying the current ones;
  `astra storage-check` proves a backend first; `astra storage-status` shows
  where the files are; `astra storage-verify` reads every file back and
  checks it, on either backend (the check to run after a restore).
- [x] 4.4 Runbook stage 11.5 and `deploy/systemd/object-storage.conf.example`.
- [x] 4.5 Tests, guards, independent review, full suite.

What it does:

- The server folder stays the default. Nothing changes for an installation
  that does not set `ASTRA_STORAGE_BACKEND=s3`.
- Every upload goes to the active backend. A file is read, linked and deleted
  through the backend its row names, so files uploaded before a switch keep
  working until they are moved. Who may upload or download, the size limit,
  the blocked types, the SHA-256, the history and the notices are decided in
  the service and are the same for both backends.
- The bucket stays private. Astra signs every request, never makes an object
  public and never hands out a bucket address: a download still streams
  through Astra after its access check. The key is read from the server's
  environment (or a settings file for the commands), and is never stored in
  the database, written to a log or an error, or taken as an argument.
- A move is verified file by file. A file that fails any check stays where it
  was, keeps working, and is listed; the command then exits with status 1 and
  can be run again. Only one storage command runs at a time.
- Each move and each prune is recorded in the owner history as a server
  command, with where the files went and how many, and every App Owner gets
  a notice. A command stopped with Ctrl-C records what it had already done;
  if the record cannot be written the command says so and exits with status
  1.
- If the storage cannot be reached, an upload or download answers "File
  storage is not available right now" (503), the cause goes to the server
  log, and nothing is stored. A wrong bucket name is reported as storage not
  available, never as a missing file. A download that breaks part-way ends
  short; no error text is appended to the file.
- Astra refuses to start with a wrong or incomplete configuration of the
  active backend, and says in its log at start when files are recorded on a
  backend whose settings are missing or incomplete. It does not contact the
  bucket at start.

How it was checked:

- Tests: full suite on the code of `877bde1`: `Ran 1379 tests`,
  `OK (skipped=2)`. New:
  `tests/test_object_storage.py` (request signing against the two worked
  examples in the Amazon S3 reference, settings, both backends, the service
  and both web servers on object storage, the migration, rollback, prune, the
  commands), `StorageBackendMigrationTests` (`tests/test_db.py`), the example
  drop-in check in `tests/test_deploy_config.py`.
- Guard removal: 138 guards were removed one at a time in a complete
  throwaway copy of the final code, after the untouched copy had passed. Each
  removal made at least one test fail. Guards found untested on the way
  (by this check and by the reviewers) got tests or were removed as needless.
- Independent review: an agent that did not write the code read the diff
  without editing it, four times, with its own probes each time. Round 1
  found no blocker and eight items: an interrupted move left no history
  entry; a download cut short on the development server carried an error
  page; a removal racing a move left bytes in the bucket; a wrong bucket name
  read as a missing file; `storage-check` could lose its verdict; four guards
  had no test; the bucket had no restore procedure. Round 2 found that the
  first fix for interrupts was itself wrong: a Ctrl-C landing just as a
  file's row was committed discarded the copy the row named (no bytes lost,
  but the file read as missing until rolled back). That part was reworked so
  that the database decides. Round 3 confirmed the rework and found four
  smaller items, one of which could overwrite a good kept copy with a damaged
  one under a double fault; all four were fixed with tests. Round 4 confirmed those fixes and that no path destroys a good copy. It found one new small defect (a Ctrl-C at one moment was swallowed) and that an interrupted run did not print what it had done; both were fixed with tests. Those two last fixes were not read again by a reviewer.
- Browser: on a local server, the uploads of a disposable database were moved
  to a test bucket and back through the service code. The owner history then
  showed both moves with where the files went and how many, and an
  interrupted one marked as such; every owner had a notice; the files still
  downloaded; no answer named where the bytes are kept. No other screen
  changed.
- Unverified, for Aly's drill (runbook stage 11.5): everything about a real
  OCI bucket. That covers OCI's handling of the signed requests, the address
  used to confirm the bucket refuses unsigned reads, the policy wording, and
  the service's outbound rule.

Decisions for Aly, gone through on 2026-11-17; 2 and 3 are left open until a
bucket is taken up. Aly chose the answer to 1 himself.
For 2 to 6 he asked for Claude's recommendation and then said "continue as
per your recommendation"; the answers there are that recommendation.

1. Whether uploads move to object storage at all. The folder stays the
   default until Aly says otherwise.
   Answer: the folder for now. Object storage is decided later, after a
   bucket drill and a chosen bucket backup.
2. Outbound network for the Astra service: only Oracle's Object Storage
   address ranges, or all outbound traffic (runbook stage 11.5).
   Answer: left open until a bucket is taken up; the recommendation for
   then is Oracle's Object Storage address ranges only.
3. How the bucket's contents are protected, since the server backup does not
   hold files kept in the bucket. Until Aly chooses and a restore has been
   tried once, files in the bucket have no tested backup, so Item 6's "same
   backup and recovery" is met for the folder and only documented for the
   bucket (runbook stage 11.5, with `storage-verify` as the check).
   Answer: left open until a bucket is taken up; the recommendation for
   then is versioning on the bucket and one tried restore before any real
   file depends on it. Versioning on OCI is unverified here.
4. Between switching the setting and finishing `storage-migrate`, new uploads
   are in the bucket and older ones still in the folder. No user or project
   chooses a destination, and `storage-status` shows the split. Is that
   window acceptable under Item 7?
   Answer: accepted.
5. Old copies stay until `storage-prune` is run by hand. After a prune, a
   rollback copies the files back from the bucket instead of switching to a
   kept copy.
   Answer: keep as is. Old copies go only when `storage-prune` is run.
6. Astra records that a file is in object storage, not in which bucket.
   Settings changed to another bucket the key can use are not detected
   (files read as not found until the settings are put back). Should each
   file's row also record its bucket, so that a wrong bucket is refused?
   Answer: yes, built just before the first real use of a bucket, not now.

Known limits, left as they are: a download that breaks before its first byte
under Waitress answers a plain 500; a download is written to the history
when it starts, also if it then breaks; a hung bucket holds a request for up
to a minute; a command killed outright (not Ctrl-C) records nothing, and
`storage-status` then shows where things stand.

## Current handover — 2026-10-24 (start here)

Read [HANDOFF_2026-10-24.md](HANDOFF_2026-10-24.md). It supersedes every
status, count and next-step statement below, which are dated history. The
pick-up prompt for the next agent is its section 11, also in
[AGENT_START_PROMPT.md](AGENT_START_PROMPT.md).

In short, at `a8be8d2`:
- The 41 signoff tickets are done.
- 6BXYJZ step 4 shipped tested host configuration in `deploy/`; nothing is
  deployed.
- Six human-lane tickets were tested by Claude and Codex and wait for Aly's
  board move.
- F9HBSJ has a DST scheduler defect and stays open.
- Board: 93 tickets, 67 done, 15 human, 11 backlog.

## Daily in-app summary — 2026-10-15

F9HBSJ now implements a primary-Owner-controlled daily Inbox summary with an
editable local delivery time and IANA time zone (default 09:00 Asia/Karachi).
The single-process scheduler sleeps until the next due time, deduplicates by
Owner-local date and catches up after restart; it does not poll every minute or
use a cloud job. A new primary Owner inherits the saved schedule. The summary
groups overdue, due-today and upcoming tasks, submitted reviews, open
checkpoints due soon or overdue, and next actions. The disposable Chrome check
verified saving the time zone and opening the linked Inbox summary. The full
suite passed **927 tests in 767.731s, OK (skipped=1)**; the independent read-only
diff review found no new issue. F9HBSJ is awaiting Aly's acceptance in the human
lane. This is local application evidence only; hosting and deployment remain
unverified.

## Current password-change gate — 2026-10-15

Read [A5 implementation and verification](FIRST_LOGIN_PASSWORD_CHANGE_2026-10-14.md).
App Owner-created and reset passwords require a change before protected app access;
signed-in users can change their own password. Schema 21 defaults existing
accounts to unchanged behavior. The 2026-10-15 full suite passed: **891 tests in
644.691s, OK (skipped=1)**. Isolated Chrome verified mismatch, too-short and
wrong-current-password refusals, required-field blocking, direct-route gating,
and successful forced and voluntary changes. Read-only checks confirmed one
secret-free password-change event per synthetic account, cleared forced-change
flags and retained active sessions. Independent implementation review passed
with no confirmed defect; the reviewer acknowledged the browser evidence but
did not repeat it. Aly accepted A5 on 2026-10-15; JRNDC8 is Done. No live account
or database was changed. Hosted readiness and deployment remain separate and
unverified.

Live Jaira snapshot on 2026-10-15: **92 tickets: 26 Done / 39 signoff / 13
human / 13 backlog / 1 in-progress**. Aly authorized TRPV3J for Codex; local
backup/restore CLI work is active. The CLI and operator guide do not prove
encryption-key setup, OCI upload, retention, desktop copy or hosted restore drills.
Backlog ticket 0RHNMG has the same title and core goal as accepted JRNDC8, but
its context and criteria differ. 0RHNMG is now in human review awaiting Aly's
duplicate-versus-separate decision; its provenance is unverified. The
real-device acceptance check is still pending; see [the A7 checklist](REAL_DEVICE_ACCESSIBILITY_CHECKLIST_2026-10-15.md).
2FREQ9 and WMW428 have Aly's acceptance recorded in chat but remain in the
human lane for Aly's board transition.

## Current independent-review guard repairs — 2026-10-14

Read [MJ5Q35's repair receipt](REVIEW_GUARD_REPAIRS_2026-10-14.md) first.
Closed-project template/dependency writes and stale write authority are
repaired; project reopening follows the dated App Owner-only rule. Aly
explicitly kept ordinary submitted edits allowed. Independent source review
and focused role/HTTP/guard checks pass. Final full suite: **881 tests in
830.547s, OK (skipped=1)**. Pin the published SHA supplied with this receipt.
MJ5Q35 awaits Aly's acceptance.
WMW428 remains accepted. Password/recovery/CI/hosted gates remain separate.
Current board: **89 tickets: 25 Done / 39 signoff / 11 human / 14 backlog**.
Validation: 89 checked, no errors, 44 warnings; generated AGENTS/CLAUDE note
drift remains disclosed. No existing protected lane was moved.

## Current frontend repair package — 2026-10-14

Read [the F1–F9 repair receipt](FRONTEND_REPAIRS_2026-10-14.md) first.
The nine confirmed October 13 defects and related picker/token/navigation
debt are repaired, with synthetic Chrome persistence checks, independent diff
review and a fresh **849 tests OK (skipped=1)**. Aly chose direct project-task
creation named **Add a task**. Aly accepted **WMW428** in chat on October 14
("Ticket accepted"). Its board lane remains human until Aly moves it; no prior
acceptance lane was closed by the agent. The board is not cleared.
Historical package board: **88 tickets: 25 Done / 39 signoff / 10 human / 14 backlog**.
Validation has no errors; 44 warnings and generated-note drift remain disclosed.

Pin the published package SHA supplied with the independent-review prompt.
The older app baseline and defect statements below are historical snapshots;
schema 21 includes A5 and package 0.1.0 is unchanged. Physical-device, assistive-technology,
whole-app usability and hosted launch gates remain separate and unverified.

## Critical built-work review — 2026-10-13

Read [the critical UI/UX review](CRITICAL_UI_UX_REVIEW_2026-10-13.md) and
[all-ticket criterion coverage](CRITICAL_REVIEW_COVERAGE_2026-10-13.md)
before declaring readiness. Two persisted synthetic browser failures can save
to the wrong task or silently remove its owner. Full832 tests pass despite
these defects. This review recommends repairs; it makes no product changes,
owner acceptance or deployment authorization. External reviewers must inspect
these findings as well as the plan below.

## Current pre-deployment review package — 2026-10-13

Start with [the detailed plan and handoff](PRE_DEPLOYMENT_REVIEW_2026-10-13.md),
[every-ticket audit](BOARD_AUDIT_2026-10-13.md), and
[the prompt for independent LLMs](INDEPENDENT_LLM_REVIEW_PROMPT.md).
These supersede historical status/count statements below. AGENTS.md remains
the authority for working rules; Aly alone accepts and authorizes deployment.

App-source baseline: `da1b3fd21ed0d4357669f0e727369fda02640672`, working branch
`codex/migration-safety-remediation`, schema 20, package 0.1.0. Source full receipt:
832 tests OK (one unavailable Windows symlink case). The fresh package receipt
is in the detailed plan and is reported with the final pushed SHA.

Existing board: **85 tickets, 25 done / 39 signoff / 7 human / 14 backlog**.
TV43F1 adds one coordination ticket; use the final 86-ticket audit for its lane.
The board is not cleared, and hosted readiness is unverified. First-login/self
password changes, backup/recovery, production checks and release work remain.

For Claude, Gemini, Codex or another reviewer: use the new independent prompt,
pin the supplied package SHA, read every handoff listed in the audit, and return
findings without edits. Other-LLM reviews have not been performed by writing a
prompt. The September AGENT_START_PROMPT remains historical startup context.

JM7CFP, W6ZSGA and 2FREQ9 have recorded chat acceptance; do not request repeat
acceptance. Native Excel/Chrome evidence from October 11 and later drag/zoom
receipts supersede older blanket 'browser unverified' wording only within their
documented scope. Owner-only board closure remains separate.

## Historical index notes — preserved for traceability

The notes below were accumulated from September 26 onward. Their test counts,
open-question statements and acceptance/board wording are dated snapshots,
not the current pre-deployment baseline. Follow the package above for current
planning, scope and review instructions.

Current local security review: [ZQQCJM B1 evidence](B1_SECURITY_2026-10-13.md). Request framing, response headers, workbook XML/archive budgets and write-time authority/assignee checks were repaired; Aly's closed-project and agreed-deadline decisions are applied. Hosted readiness is unverified. [Current free-hosting comparison](FREE_HOSTING_2026-10-13.md) recommends an eligible Oracle Always Free VM with DuckDNS and Caddy; no account or deployment action is authorized by that recommendation.

Current deadline-extension routing: [2FREQ9 verification](DEADLINE_NOTICES_2026-10-13.md). Active App Owners and Chairman receive in-app old/new-date notices for saved task deadlines, agreed targets and calculated project finish extensions. Existing approval rules remain in force. Aly accepted 2FREQ9 on 2026-10-13; hosted operation remains unverified.

Current server inactivity repair: [AY5EZ0 verification](HTTP_TIMEOUT_2026-10-13.md). Stalled connections now have a finite socket timeout; timed-out body reads return 408 and close their request database. Broader security review, owner acceptance and hosted operation remain separate.

Current phone-size and List scheduling repair: [827Q51 verification](TABLE_SCHEDULING_2026-10-12.md). Table rows now expose Move task and preserve filtered sibling ordering. Actual 200% Chrome zoom and save/reload checks passed on 2026-10-13; Aly accepted the repair. Physical-device and hosted checks remain separate.

Current automatic task movement and project scheduling: [SXAWHN implementation
and verification](AUTOMATIC_TIMELINE_SCHEDULING_2026-10-12.md). Above/Below now
create sequential relationships through the Move task UI; linked dates and
project forecasts update together. Explicit deadline revision is optional.
Owner acceptance and hosted operation remain separate.

This folder hands Project Astra to whoever works on it next: an AI coding
agent in any tool, or a human developer. The pack calls that reader "the
agent". It was written at branch `codex/migration-safety-remediation`, head
`0b90ceb` (schema v20, 676 tests OK, nothing deployed); the commits made since
are listed in `HANDOFF_2026-09-26.md` section 1.

Current owner Excel and task-row timeline work: [JM7CFP verification](OWNER_EXCEL_WORKPLAN.md).
Aly selected XLSX with four main columns and explicit named relationships.
Implementation and isolated sample checks are recorded there. Aly accepted
JM7CFP on October 9; later bounded native/browser evidence is in
[desktop verification](DESKTOP_VERIFICATION_2026-10-11.md) and the dated drag
repairs. This is not a launch-readiness claim.

Latest Windows baseline evidence: [A0 repair, 2026-10-04](A0_2026-10-04.md),
ticket SFAZD7. The default Windows command ran 684 tests, `OK (skipped=1)`;
the symlink skip and remaining launch gates are recorded there. A0 awaits
Aly's acceptance; this result does not establish hosted readiness.

Latest importer repair evidence: [2026-10-04 repairs](IMPORTER_REPAIRS_2026-10-04.md),
ticket WYM776. The default Windows suite ran 692 tests, `OK (skipped=1)`.
Parent 3NT40T remains in human for the sample-dependent CSV decision. The
mixed-save evidence is below; owner acceptance and hosted readiness remain separate.

Latest mixed-save evidence: [2026-10-04 repair](MIXED_SAVE_REPAIR_2026-10-04.md),
ticket 1G7Q4C. The default Windows suite ran 700 tests, `OK (skipped=1)`.
Manager combined edits and protected status requests are refused without partial
writes, and the actual browser retains the entered fields. Aly's acceptance and
the remaining development and hosting gates are still required.

Latest Q1 permission evidence: [2026-10-05 approver permissions](Q1_APPROVER_PERMISSIONS_2026-10-05.md),
ticket 2RPSWM. Designated approvers may request App Owner acceptance of submitted
work only; Manager authority and App Owner final decisions remain intact. The
default Windows suite ran 714 tests, `OK (skipped=1)`. Aly's signoff and hosted
readiness remain required.

Latest owner workplan feature: [one-project CSV, 2026-10-07](WORKPLAN_CSV_2026-10-07.md),
ticket W6ZSGA. Project download/fill/upload supports Shared and alternative plans,
logged task keys and independent critical paths. The final Windows suite ran
739 tests, `OK (skipped=1)`; independent review and synthetic desktop/phone
browser checks passed. Aly accepted W6ZSGA in this chat on 2026-10-07.
The human-only board transition, real sample population and hosting remain
separate.

Local data location on Aly's machine, 2026-10-07: `Documents/AstraTest` was
relocated to this checkout's `data/` directory at Aly's request. Use the root
`Start-Astra.ps1` launcher; see [local instructions](../../LOCAL_ASTRA.md).
The directory is ignored by Git. SQLite integrity, foreign keys and every table's
records matched a consistent backup after relocation. At relocation this database
contained one user and no projects or tasks; the earlier browser-session database remains
unverified. No server startup or schema migration was performed during the move.

Latest entity feature: [entity rename, 2026-10-07](ENTITY_RENAME_2026-10-07.md),
ticket 16JJ96. Aly selected a separate `Rupani group of Colleges` entity and the
existing school project was filed under it in the authenticated local browser.
Owners can rename entities with stable IDs/project links and Settings history.
The entity setup supersedes the empty-database relocation snapshot above.

## What is in the pack

| File | What it is for |
| --- | --- |
| `README.md` | This index, the reading order, and how to use the pack with a specific tool |
| `HANDOFF_2026-09-26.md` | The master handoff: status, setup on Windows and Linux, tests, working rules, architecture, feature history, permissions, board, gaps, risks, where the docs live |
| `NEXT_STEPS.md` | The plan from now to distribution: A close out development, B hardening, C release engineering, D deployment, E distribution, F operate |
| `DEPLOYMENT_RUNBOOK.md` | Command-level steps for the Oracle Cloud Always Free + DuckDNS + Caddy pilot, with Aly's steps marked, a check after every stage, update and rollback |
| `DECISIONS_LOG.md` | Every decision Aly has made that we found, with date and source, plus Claude's default calls that Aly has not overruled |
| `OPEN_QUESTIONS.md` | What Aly still has to decide, each with a recommended default |
| `AGENT_START_PROMPT.md` | The first message Aly pastes to the next agent |

The working rules themselves live in `AGENTS.md` in the repository root. That
file is the single source; `CLAUDE.md` repeats the same rules.

## Reading order for the agent

1. `AGENTS.md` in the repository root: the rules.
2. `AGENT_START_PROMPT.md`: the rules in short and the first task.
3. `HANDOFF_2026-09-26.md`: sections 1 (status), 4 (rules) and 6 (permissions)
   first, then the rest.
4. `NEXT_STEPS.md`, phase A in full; skim the later phases.
5. `OPEN_QUESTIONS.md` and `DECISIONS_LOG.md`, before you propose any change of
   behaviour.
6. `pending-global-mistakes.md` and `README.md` in the repository root.
7. `DEPLOYMENT_RUNBOOK.md` when the work reaches phase D.

## Using this with a specific tool

Nothing in the pack depends on one tool. Only the file a tool reads by itself
differs:

- **Codex** reads `AGENTS.md` automatically.
- **Claude Code** reads `CLAUDE.md` automatically. Its top part repeats the
  rules in `AGENTS.md`.
- **Any other tool** (Gemini, Cursor, another assistant) **or a human
  developer:** paste `AGENT_START_PROMPT.md` as the first message, or read it
  yourself, and follow `AGENTS.md`.

Wherever a step needs a decision, an account, a password or an acceptance, the
pack says "ask Aly".

## For Aly

- To test locally, follow section 2.1 of `HANDOFF_2026-09-26.md`.
- Your part of phase A is in `NEXT_STEPS.md` A1 (signoffs), A2 (questions),
  A7 (phone and screen-reader check) and A8 (the `tmp*` folders).
- The five questions that block the most work are at the top of
  `OPEN_QUESTIONS.md`.

## How this pack was checked

- Every SHA cited was checked with `git cat-file -t` in the repository, except
  three that the shallow container clone does not hold: `051db35` and
  `331f988` are remote branch heads confirmed with `git ls-remote`, and
  `c5ac1c0` is the first parent of `main`'s head `c841526`
  (`git cat-file -p c841526`).
- Every repository path cited exists at `0b90ceb`, apart from the files this
  pack proposes to create (`CHANGELOG.md`, `.github/workflows/tests.yml`) and
  the pack itself.
- Every `astra` command matches `src/astra/__main__.py`; every environment
  variable matches the code (`ASTRA_HOME`, `ASTRA_SECURE_COOKIES`,
  `ASTRA_ATTACHMENT_ROOTS`).
- Operating-system, Caddy, DuckDNS, OCI and encryption commands in the runbook
  were not run for this handoff; they are marked "verify".
- Facts taken from memory notes that could not be re-checked against the
  repository or Slack are marked "memory" or "unverified".
- An independent fact-check of the pack was applied before it was committed
  (`146a5b3`).
