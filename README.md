# Astra Project Tracker

Astra is a standalone private project-management hub designed to run on the owner's
computer. Source matching remains local. Ordinary users see only projects, tasks,
Gantt schedules, assignments, dates, and explicitly published files for scopes they
are allowed to access.

This first vertical slice provides:

- owner bootstrap and authenticated sessions;
- App Owner, Chairman (organization-wide read-only unless separately granted a project role,
  except that the Chairman may assign work; see below), manager, and member roles;
- assignment rules (3FQEKB, Aly 2026-09-26, Slack ts 1790386228.535829 and
  1790386492.402489). Who may set or change a task's assignee, and who may be one:

  | Role | May assign tasks and subtasks | May be assigned (or collaborate on) a top-level task | May be assigned (or collaborate on) a subtask | Reviewer or approver |
  |---|---|---|---|---|
  | App Owner | Yes | Yes | Yes | Yes |
  | Project manager | Yes, on their project | Yes | Yes | Yes |
  | Chairman | Yes, in any project: the assignee only (panel and bulk Assign) | No, never | No, never | Yes |
  | Project member | No | Yes | Yes | Yes |
  | Project viewer | No | No | Yes | Yes |

  A collaborator may submit the task, so collaborators follow the assignee columns (review
  13a): `add_task_reviewer` refuses the Chairman as a collaborator anywhere and a viewer as a
  collaborator on a top-level task, and so does the importer's Collaborators column
  (`E_COLLABORATOR_CHAIRMAN`, `E_COLLABORATOR_VIEWER`). An older collaborator row that breaks
  this stays, is marked in the panel's reviewer list, flags the task "Collaborator not
  allowed" (`needs_new_collaborator`, counted in the same Home tile, "Needs reassigning"),
  and no longer lets that person submit. A viewer collaborator also blocks promoting a
  subtask to top level until removed.

  The Chairman's right adds the assignee and nothing else: creating tasks, status, dates,
  holds, criticality and other bulk changes stay refused (403), and someone else's lock
  refuses the Chairman as it does anyone. Every path follows the table: create, the task
  panel, bulk Assign, the Excel importer (`E_OWNER_CHAIRMAN`, `E_OWNER_VIEWER` row errors),
  the on-hold responsible person and templates. Promoting a viewer's subtask to top level is
  refused until it is reassigned. A viewer assigned a subtask may do on it what a member
  assignee may do on their own task (submit it) and nothing else. Templates never offer the
  Chairman role: a task last owned by the Chairman is saved with no suggested owner, an older
  template's Chairman role creates the task unassigned, and a viewer role fills subtasks
  only. Assignee pickers never list the Chairman and list viewers only for a subtask,
  marked "(viewer)"; the reviewer picker is unchanged. Tasks assigned before these rules to
  the Chairman, or top-level tasks assigned to a viewer, keep their owner and show a "Needs a
  new assignee" chip (card, List row, task panel) with a count on Home for owners and
  managers (`needs_new_assignee`; `?risk=reassign` on the portfolio); the flag clears when
  someone reassigns the task. `GET /api/assignable-users?project_id=…&for=task|subtask|reviewer`.
  The task panel offers only what the server would accept: someone who cannot edit (the
  Chairman, a member, a viewer) sees the lists without the parent, criticality, schedule
  proposal, dependency, reviewer and Edit forms, and sees Submit only when allowed
  (`permissions.can_submit`). The Chairman selects tasks for bulk Assign in the List only.
  An empty date field counts as no date, so a title-only save on an undated task needs no reason;
- an owner-only People screen: create users, deactivate/reactivate them, grant or revoke
  project access, and reset a forgotten password (`POST /api/users/{id}/password`): any
  owner resets any active user's password, except that only the primary owner resets the
  primary's (a secondary owner's attempt is refused, recorded and notified); the user is
  signed out everywhere else, and the owners are told when the user is an owner; task
  owners are chosen from users authorized on the project;
- primary and secondary owners: the first owner (`init-owner`) is the primary owner and
  alone may make an active user a secondary owner, or remove that access, with a reason
  (`POST`/`DELETE /api/users/{id}/secondary-owner`). A secondary owner has every other
  Owner power but cannot change the owner access, active status or project access of any
  owner, their own included (403, every attempt recorded and notified to the primary,
  subject to the blocked-attempt notice cap below). To deactivate a secondary owner the primary first removes
  their secondary owner access. Removing access restores the user's earlier role, signs
  them out and keeps their project roles. The People screen shows the latest 20 grants and
  removals under **Owner access history**, then the latest 10 blocked owner-access attempts
  and, separately, the latest 10 imports blocked for lack of a target project, so no list
  hides another (`GET /api/user-events`, owners only). An owner
  cannot approve or reject an Owner request they filed;
- project-scoped access;
- projects, tasks, responsible people, dates, criticality, progress, and dependencies;
- finish-to-start dependency creation, cycle prevention, blocking visibility, and audited removal;
- append-only task audit events;
- project start and target dates (informational, never a constraint on task dates): only the
  owner or a project manager may change them, a reason is required, and each change writes a
  `project_schedule_changed` project event (actor, before, after, reason). Anyone who can view
  the project reads its history through **Project history** (shown when one project is
  selected), served by `GET /api/projects/{id}/events` (403 for non-members). The owner, the
  Chairman and project managers see every project event; anyone else who can view the project
  sees only `project_schedule_changed`, `project_closed` and events they caused themselves;
- a task detail view with authorized inline editing (reason required for status/schedule
  changes), add/remove of multiple dependencies, and a human-readable event history. The
  owner, the Chairman and project managers see every task event; other project members see
  ordinary task changes and their own events, but not Owner-action requests or decisions,
  blocked attempts or import keys written by others;
- a governed work lifecycle: submissions are recorded and only the App Owner decides the
  protected actions — accept, request changes, reopen, close, taking work off hold, and
  schedule proposal decisions. A project manager puts work on hold directly (owner decision,
  2026-09-25), with the same reason, checkpoint and responsible owner, audited as `task_on_hold`
  and notified to the other owners; anyone else who is not an owner or a manager of the project
  cannot. An eligible project manager or designated approver may request the protected actions (a
  designated approver who is not a manager still requests a hold), which
  records one idempotent Owner request without changing live state; the Owner can approve,
  reject, or cancel that request from **Inbox — Needs action**, where each request shows the
  status it asks for (and the status it moves from, when recorded), the requester's reason, and
  an Open task link; an accepted version is immutable
  and can only be superseded after an explicit reopen with a revised timeline; on-hold work
  requires a reason plus a mandatory follow-up checkpoint; a task that waits on an unfinished
  predecessor cannot move to In progress, be submitted or be accepted on any path (board, task
  panel or API): anyone but an owner is refused with "waits on …", and an owner confirms an
  override, recorded as `dependency_override` in the same transaction and noticed to the other
  owners. Approving a request meets the same rules at decision time: each pending request in
  the Inbox and on Home says what approving it would override ("Waits on …", "In progress is
  at 3 of 3", a date past the project target), and Approve asks the owner to confirm each
  one the server names, recording the override in the deciding owner's name
  (`override_dependencies`, `override_wip` and `confirmed` on
  `POST /api/owner-action-requests/<id>/decision`); and project closure is a separate
  App Owner-only event, with exceptional closure preserving a residual-work snapshot rather
  than silently completing unfinished tasks;
- attachment-link and final-result mutations (add/remove, mark/unmark) are App Owner-only,
  while every user authorized on the project may still read and list them; a link must be a
  full local path inside a folder the installation allows (`ASTRA_ATTACHMENT_ROOTS`, see Run
  locally), never a URL, network (UNC) or device path, and a link marked as a final result
  cannot be removed until the final result is unmarked (HTTP 409);
- reviewers, approvers, and collaborators recorded separately from the accountable owner;
- entities and cross-entity project filing: a project keeps one stable id with links to one
  or more entities (the approved baseline entity list can be seeded on owner request);
- a portfolio dashboard with rolling due-bands (Overdue, Today, 1–7, 8–14, 15–30), combinable
  entity/project/status/criticality/owner and cumulative due-within filters, an "open work
  only" toggle, and a per-task "next action" shown separately from the accountable owner;
- criticality governance: a "Sort by" choice orders tasks criticality-first (Critical→Low,
  Unrated last) or by nearest due date; Unrated tasks carry an amber "Unrated" badge in the
  task list, schedule table and detail so they stay conspicuous. Only a project manager or the
  owner confirms a level, with a reason; the old value is re-read under the write lock and an
  optional `expected_revision` refuses a stale confirmation (409). Each change is recorded as a
  dedicated `criticality_changed` audit event (actor, old value, new value, reason);
- parent/subtask hierarchy with a completed/total roll-up shown separately from a task's own
  declared progress, cycle-safe re-parenting, and clickable subtasks;
- a durable in-app notification inbox: every owner gets an idempotent record of every task change,
  project close and project date change made by someone else (in-app only; marking read never
  deletes or approves anything); a
  blocked attachment removal, a final-result unmark and an attachment removal are also sent
  to the owner who did them, so a single-owner install hears of them; blocked-attempt notices
  are capped at 5 per recipient and per person in any 10 minutes, with blocked owner-access
  attempts counted separately, and the 5th notice in each says further attempts of that
  kind are in history only for now (every attempt is still audited, including an import refused for lack of a target project);
- portfolio and per-project Gantt views with overdue and upcoming highlighting;
- task steps (subtasks) drawn as numbered, colour-coded segments inside the parent's Gantt
  bar: a shared tooltip on hover and keyboard focus, a chevron that expands the step rows,
  a `+N` disclosure for steps not drawn at this scale, an "n steps need dates" chip, a dashed
  extension where a step runs past its parent's dates, and a Schedule table twin with the
  same rows as text, which is the default at phone width;
- one visual system: the Inter typeface (4.001, SIL Open Font License) is served by Astra
  itself from `src/astra/static/fonts`, so the page makes no third-party requests and the
  Content-Security-Policy allows fonts from Astra only; every control shows a keyboard focus
  ring, a reduced-motion setting switches animation off, and the page fits phone (360px) to
  desktop (1440px) widths without sideways scrolling. Below 1024px (phones and tablets) every
  stand-alone button, link and field is at least 44px tall (a link inside a sentence, small
  print or a table cell stays inline at 24px or more, so rows are not inflated) and fields use
  16px text, so iOS does not zoom in; the phone bottom bar leaves room for the device's safe
  area and never covers content. There the task panel fills the screen: "Open full page" is
  hidden, and everything behind the panel is inert while it is open, so Tab stays in the panel
  until it is closed (the same happens at 200% zoom on a laptop). Each screen has
  one heading 1 (the page title, which takes focus when the screen changes, so screen readers
  announce it), a "Skip to content" link, navigation, main and panel landmarks, a name on
  every control, and text contrast of 4.5:1 or better, including the Gantt project flags.
  The browser tab shows a small Astra icon (`static/favicon.svg`);
- a navigation shell: a left rail (Home, My Work, Inbox, Projects, Capture; a bottom bar on
  phones) and a top bar with the page title, search (`Ctrl K`, or `Cmd K` on a Mac) and an
  account menu (People and access for owners, Keyboard shortcuts, Sign out, Sign out
  everywhere; signing out reloads the page, so nothing of the last person's session stays on
  screen). There are no page-wide single-key shortcuts. Each
  screen has its own link (`#/home`, `#/portfolio`, `#/my-work`, `#/inbox`, `#/projects`).
  The portfolio timeline (`#/portfolio`, under Projects) holds the filters, the Portfolio
  Gantt and the schedule table; its filters live in the link, so reload, Back and a shared
  link keep them (older `#/home?...` filter links are sent there), and active filters show as
  removable chips beside "Showing X of Y", with Clear all. Its Risk filter (at risk, blocked,
  critical path) and "No due date" option also narrow Export CSV. My Work and the Inbox are
  described below; Projects lists the
  projects you can see; Capture adds a task with a title and project (the other fields fold
  under More fields) and says so if the current filters hide it. Portfolio by entity, Final
  results, Templates, Import, Export CSV and, with one project selected, Project history,
  Save project as template and Close project are in the portfolio timeline's "More" menu;
- a Command Center Home, with a "Portfolio Gantt ›" button at the top that opens the
  portfolio timeline (`#/portfolio`, the filters, Portfolio Gantt and schedule table): six health tiles (Overdue, Blocked, Awaiting Owner for owners, Due in
  7 days, Critical path, Undated), each stating what it counts (one "Counts as of" time for
  the row), and each opening the matching filtered list; for owners, "Needs Owner decision" with working Approve and Reject
  and a Review button that opens the task; "My next actions" (Today, This week, Later); "At
  risk" (overdue, blocked, critical path or delayed, worst first); a "This week" strip of open
  items due today and on each of the next 7 days (8 bars that add up to the "Due in 7 days"
  tile); and "Portfolio by entity". A new install shows one "No projects yet"
  card instead;
- a page per project (`#/project/<id>/<tab>`, opened from Projects) with tabs Overview
  (status, dates, progress, open, overdue, blocked and critical-path counts, next due), List
  (the schedule table), Board, Timeline (the Gantt) and Activity (the project history), and
  Add a task, plus Save as template and Close project for owners. The Board
  maps the 11 statuses into 7 columns — Draft = draft; Ready = assigned; In progress =
  in_progress, reopened, changes_requested, delayed; Blocked = on_hold, or any open task
  waiting on an unfinished predecessor; Submitted = submitted; Accepted = completed; Closed =
  cancelled, abandoned (closed statuses win over everything, Submitted over Blocked).
  Accepted and Closed are Owner-decided and start collapsed. Cards show the title, owner
  initials, due date, criticality when it is set (the task panel flags unrated work), "Waits on …", on hold, delayed, critical path and "Steps n
  of m done" (steps are counted on their parent, not drawn as cards). "Divide by" splits the
  board into swimlanes by owner or criticality and is kept in the link; owner lanes are
  one per person (by user id), so two people with the same name get separate lanes, marked
  "(1 of 2)" and "(2 of 2)". Every column keeps the same width in the
  header and in every swimlane; a wide board scrolls sideways inside its own frame;
- board drag and drop for owners and the project's managers (members, viewers and the
  Chairman see the board read-only). Dragging a card within a column saves its place in that
  column (`tasks.board_rank`, schema v18; recorded in project history as `board_reordered`, no
  notice). Dragging it to another column changes its status through the same server rules as the
  task panel: Draft, Ready and In progress set draft, assigned and in_progress; Blocked puts it
  on hold (reason, checkpoint and responsible owner); Submitted submits it; Accepted accepts
  the pending submission; Closed cancels or abandons it (with a reason); dragging a closed or
  accepted card back into work reopens it (reason and revised due date). A manager's protected
  drop files the existing Owner request instead (HTTP 202). A card moved to another column is
  appended there unless it is dropped before a card; a reorder renumbers the whole column. A
  refused drop snaps back with the server's reason. Permission refusals and rule refusals (a
  dependency, a work-in-progress limit) are recorded as `board_move_blocked` and noticed to the
  owners (under the blocked-notice cap); plain slips ("already in Ready") go back to the person
  only. An ordinary move among Draft, Ready and In progress, and a reorder, shows Undo for 15
  seconds: Undo is a new audited change ("Undo of Draft → Ready (event …)"), refused once the
  task has changed again or 20 seconds have passed, and never rewrites history; only moves the
  board itself marked as undoable qualify, whatever a reason says. Every card also has a
  "Move to…" menu (keyboard: Enter opens it, arrows move, Escape closes and returns focus; up
  and down move the card in its column; a card in Blocked only because it waits on a
  predecessor also offers "Put on hold…"). With swimlanes, dropping into another lane changes
  status, not owner. Phones never drag: a swipe scrolls and the menu moves work. The API is
  `POST /api/tasks/<id>/board-move`, `POST /api/tasks/<id>/undo-move` and
  `POST /api/projects/<id>/board-order`;
- task locks (schema v19, `task_locks`). Only one person changes a task at a time. A board or
  Gantt drag takes a drag lock, and typing in the task panel's Edit form takes an edit lock. A
  lock is a 60-second lease, renewed every 20 seconds while the drag or the form is in use (an
  idle form lets go after a minute) and released on drop, cancel, save or close. While someone
  else holds one, every write to that task (edit, board move, hold, submit, decisions,
  dependencies, criticality, files, dates) is refused with HTTP 409 naming the holder and the
  time the lease runs out (shown in local time); the check sits inside the write transaction,
  so the final write always revalidates. Reviewer and approver changes (`reviewer_added`,
  `reviewer_removed`, now task events) and links from a locked predecessor are refused too.
  A lease that has run out cannot be renewed; the browser takes a new one, or says so and
  reloads. A drag of a task whose Edit form you are using borrows that lease and leaves it. A board reorder that includes a task someone else holds is refused the same
  way, and nothing is written. Board cards show a lock chip and the task panel a banner with who and
  until when (as of the last load). Any active owner may Force unlock, which is recorded as
  `task_lock_forced` and noticed to the holder and the other owners. API:
  `POST /api/tasks/<id>/lock` (`kind` drag|edit|bulk), `/lock/renew` and `/lock/release`
  (`token`), and `/lock/force` (owners, optional `reason`);
- Gantt date drag for owners and the project's managers: drag a bar to move both dates, or its
  left or right end to change the start or the due date, with a live tip of the new dates. The
  task panel's date fields remain the keyboard and phone route (phones and touch never drag
  bars). The server validates the dates (real dates, start not after due) and refuses with the
  reason; a refused permission is recorded as `gantt_move_blocked`. An ordinary move applies at once with a
  system reason ("Gantt drag: start … → …, due … → …") and a 15-second Undo. A move that
  breaks a finish-to-start link either way, touches a task on the critical path, or puts the due
  date past the project target (there are no milestones; the target stands in) first shows what
  it affects and applies only when confirmed; the confirmation is recorded as
  `schedule_impact_confirmed` in the same transaction as the move and the other owners are
  told. The same rule applies when dates change in the task panel or through the API, when a
  task is reopened with a revised due date, and when a schedule proposal is approved
  (`confirmed` on `/reopen` and `/schedule-proposals/<id>/approve`). A
  finish-to-start link is broken only when the successor starts before the predecessor's
  due day, so a task due 12 Oct followed by one starting 12 Oct does not ask. Tasks that
  follow are not moved. Only an ordinary move (no consequences) offers Undo.
  API: `POST /api/tasks/<id>/reschedule` (`start_date`, `due_date`, `expected_revision`,
  `confirmed`);
- bulk changes on a project's Board and List for owners and the project's managers: tick
  tasks (Shift-click takes a range; in the List, Space toggles and Shift+Arrow extends), then
  choose Status (Draft, Ready or In progress), Assignee, or a due-date offset in days (the start
  moves with it). **Review change** previews how many tasks change and names every blocked task
  with its reason (already there, submitted/on hold/closed so it changes on its own, waiting on a
  predecessor, no due date, in use by someone else), plus any schedule consequences. Nothing
  applies until the blocked ones are removed ("Remove blocked from selection"). Apply is all or
  nothing: bulk locks are taken for every task first (if anyone else holds one, nothing starts
  and the holders are named), then every write, one `bulk_change` project event listing the
  tasks and a `task_updated` event per task share one transaction, and the other owners get one
  notice. The plan is rebuilt inside the write, after the locks are held, and anything that
  drifted since the preview (a task now blocked, a limit now reached) refuses the whole change.
  A bulk never replaces your own lock on a task you are already editing. A due-date shift
  with schedule consequences applies only with `confirmed` (the reviewed preview sends it).
  Undo (15 seconds) restores every task, or none if any changed since
  (`bulk_change_undone`). The write reads the board once before and once after the task
  writes, so a 200-task change in a 1000-task project holds the database for well under a
  second. API: `POST /api/projects/<id>/bulk/preview`, `/bulk/apply`
  (`expected_revisions` from the preview) and `/bulk/undo`;
- work-in-progress limits (schema v20, `wip_limits`): an owner sets an optional limit per open
  board column per project (Limits… on the board; Draft, Ready, In progress, Blocked,
  Submitted), recorded as `wip_limit_changed` in the project history (one row per changed
  column; the dialog saves every column in one request, whole numbers 1 to 999 only). Column
  heads show "n / limit". The limit is a rule of every status-changing write a person makes:
  a board move, a bulk change or its Undo, a board Undo, the task panel's status, hold,
  submit, reopen and request-changes actions, creating a task and promoting a step to top
  level. Whatever would put more top-level open tasks in a column than its limit is refused
  with the reason for anyone but an owner; an owner may go over it after a confirm, including
  when approving a request (the request card shows the limit first). Going over is recorded as
  `wip_limit_override` in the same transaction and noticed to the other owners. Leaving a
  column is never limited. A card that enters Blocked because of a dependency (a link added,
  a predecessor reopened) is not refused, since nobody moved it: the column simply shows
  over its limit. API: `POST /api/projects/<id>/wip-limits` (`limits`: column to number or
  empty, or `column` and `max_tasks`);
- My Work with two tabs. List (`#/my-work`) groups the open tasks you own into Overdue,
  Today, This week (due within the next 7 days, day 7 included, as on Home), Later and No date, each with a
  count, soonest first, with a filter box. Calendar (`#/my-work/calendar?month=YYYY-MM`) is a
  Monday-first month grid of open tasks on their due day, with Previous, Today and Next and a
  "Show" choice (my tasks, or all tasks you can see; `&scope=all`); a day with more than 3
  tasks shows 3 and "+N more", which opens the rest in place. Below 1024px (phones and
  tablets) the month is an agenda of the days that have work. Every row and calendar item opens the task panel.
  "Today" on Home, in My Work, on the calendar and on the Gantt's today line is the server's
  date in the app's timezone (Asia/Karachi, sent with `/api/tasks`; each project also carries
  its own `today`), and each task's days until due are counted in its project's timezone, so
  a browser in another timezone never moves work to another day. The portfolio timeline says
  "Due dates as of <date> (Asia/Karachi)";
- an Inbox with tabs: Needs action (owners only: the requests waiting for a decision, with
  working Approve and Reject), Unread and All, each with a count; `?tab=` keeps the choice.
  Owners land on Needs action while a request waits, everyone else on Unread while anything
  is unread. Notifications are grouped Today, Yesterday and Earlier; unread ones are
  highlighted and have Mark read; Open task opens the task and marks that notification read;
  Mark all read clears the rest. Marking read never approves or changes anything;
- a task panel docked on the right: a task opens beside the current screen, which stays
  visible and usable, and has a link of its own (`?task=<id>` on that screen, or
  `#/task/<id>` as a full page) that survives reload and Back/Forward and can be copied with
  Copy link; a link with anything but a task id opens nothing. It sits below the top bar, so
  search and the account menu stay usable (380px wide up to 1279px, 460px above). Esc or ×
  closes it and puts focus back where you were (in a panel field the first Esc only leaves
  the field), `j`/`k` step to the next or previous task on the screen behind while focus is
  in the panel, and below 1024px it fills the screen. It opens on the title, state chips (with
  a glyph or word, never colour alone), a line saying what you may do and six facts (owner,
  start, due, criticality, progress, steps), then the description, steps and dependencies,
  and then the one Lifecycle block;
- a final-results repository: the App Owner marks an accepted submission or an attachment
  by hand (acceptance alone adds nothing), and the Final results dialog filters by project,
  entity, type, marked date (from/to, whole days in UTC, both ends inclusive) and a search,
  with Export CSV using the same filters;
- scoped search and CSV/JSON export of the current dashboard view and of final results: rows
  are limited to the projects the user may see, the CSV starts with its header row, the
  download filename carries the as-of time and the active filters
  (`astra-export-<as-of>__status=in_progress__open-only.csv`), and a cell starting with
  `=` `+` `-` `@`, tab or CR is prefixed with `'` so a spreadsheet shows it as text; and
- Excel/CSV import of tasks and Gantt rows from a locked, Owner-configurable template
  (dropdowns, date validation, version marker): the App Owner imports anywhere and may create
  a project from the file, a project Manager imports into the projects they manage with
  Owner-only actions downgraded to warnings, every upload is previewed row by row before one
  transactional commit that creates or updates tasks by Import Key, never deletes, records
  audit events and stores a downloadable report (see `docs/design/excel-import.md`).

Integrity rules enforced at the service boundary: ordinary task updates must carry the
task's current `expected_revision` and stale writes return HTTP 409 without changing state
or audit history (the browser then reloads the task, or the inbox for an Owner decision, and
says it changed since it was opened, with the server's reason under that line, so nobody keeps
editing a stale revision; an inbox request that can no longer be approved says to reject or cancel it); completed, cancelled, and abandoned tasks are fixed records until the
dedicated reopen action records a reason and a revised timeline: field edits (including a
reason-only save), re-parenting the task, confirming its criticality, proposing or approving
a schedule change for it, adding or removing its predecessors, and adding or removing its
collaborators, reviewers or approvers return HTTP 400 ("reopen the task first"), a task that
closes while such a write (or a Manager's request for one) is in flight is refused with 409,
and an import row for a closed task is skipped with `W_CLOSED_TASK`. Attachment links and
final-result marking stay available on closed tasks, and a closed task may still be added
as a predecessor of an open one, or have an open task moved under or out of it as a
subtask, since the closed task's own row does not change. The task panel follows these
rules (ARZWV7): on a closed task it drops the forms the server refuses and says "Reopen this
task to change it", with a link to the reopen form (offered on completed, cancelled and
abandoned tasks); a Manager there can only request a move back into draft, assigned, in
progress or delayed; on a submitted task the Status field is locked and points to Accept or
Request changes. This is guidance only; the server stays the authority. Task titles cannot be blanked; task
assignees must be active and authorized on the task's project (and follow the assignment
rules above); and operations against a
non-existent project return a controlled 404 rather than a 500. Submission acceptance is
transactionally single-winner, and retrying an identical protected request or final-result
mark does not create duplicate queue rows or audit events. Submitting work is also
single-winner: the version is allocated under the write lock, and a submit whose task
was changed in the meantime (a second submit, an Owner cancel or acceptance, a
reassignment, or the submitter losing collaborator or project access) returns HTTP 409
instead of overwriting it. Schema 14 makes `(task_id, version)` unique on
`task_submissions`. A database that already holds duplicate submission versions is
refused before any migration step runs, whatever version it starts at, so it stays
exactly as it was until the duplicates are resolved.

If `astra serve` (or `init-owner`) stops at start-up with "Astra cannot upgrade this
database to schema 14", the server has not started and the database is untouched. The
message lists each affected task version with its submission ids and statuses; it
comes from an earlier defect in which two simultaneous submissions could both get the
same version number. To resolve it, back up `astra.sqlite3`, then for each listed task
version keep the accepted row (the one `tasks.accepted_submission_id` or
`final_results` refers to, marked "referenced by" in the message) and delete the other
rows or renumber them to an unused version. Run any `DELETE` with
`PRAGMA foreign_keys=ON` so a referenced row cannot be removed, then start Astra again.

Schema 15 gives each Owner-action request an intent key: a hash of its item, action,
details, reason and requester. At most one pending request may hold a given key, so an
identical retry returns the existing request and the database itself refuses a second
pending copy. A second Manager's equivalent request still gets its own row. If start-up
stops with "Astra cannot upgrade this database to schema 15", the database is untouched;
the message lists each group of identical pending requests by id. Back up
`astra.sqlite3`, keep the earliest request of each group pending, set the others to
`status='cancelled'`, then start Astra again.

Schema 16 adds `users.is_primary_owner` (the database refuses a second primary owner, or a
primary who is not an owner) and the `user_events` audit table; the existing owner becomes
the primary owner. If start-up stops with "Astra cannot upgrade this database to schema 16",
the database is untouched: it has more than one owner and the message lists their user ids.
Back up `astra.sqlite3`, set every owner except the primary back to their earlier role
(`UPDATE users SET global_role='member' WHERE id=...`), start Astra again, and make them
secondary owners from the People screen.

Schema 20 adds `wip_limits` (one optional limit per project and open board column, 1 to 999).
Schema 19 adds `task_locks` (one lease per task: holder, kind, token, acquired and expiry
times; an expired row is no lock and is replaced on the next acquire). Schema 18 adds `tasks.board_rank` (a nullable
number; a task without one sorts after the ranked cards of its column) and the index
`idx_tasks_board_rank` on `(project_id, board_rank)`. Nothing existing is rewritten.

Database migrations are applied one SQL statement at a time inside a single
`BEGIN IMMEDIATE` transaction per schema version. The schema changes and that step's
`PRAGMA user_version` update therefore commit together or roll back together; a failed
or interrupted step can be retried without retaining only its earlier tables, indexes,
or columns. The same holds when `COMMIT` itself fails (for example a deferred foreign
key or `SQLITE_BUSY`): `db.transaction()` rolls back and re-raises the commit error, so
the connection is never left inside an open transaction. Regression tests exercise fresh creation, legacy upgrades, injected DDL
failures, retry, and equivalence between upgraded and freshly created schemas.

Sign-in: a wrong password or an unknown email returns HTTP 401 "Incorrect email or
password." and nothing else happens: failed attempts never lock anyone out or sign anyone
out (Aly, 2026-09-24). Attempts are kept in `login_attempts` as history for 90 days; a
successful login clears that email's failures and prunes expired sessions. Passwords need
at least 8 characters, and each check is a slow PBKDF2 hash (600,000 iterations); there is
no limit on online guessing, so a hosted deployment should rate-limit in front of Astra.
Forgotten passwords are reset by an owner on the People screen (or with
`astra reset-password` below). "Sign out everywhere" revokes all
of the current user's sessions. Set `ASTRA_SECURE_COOKIES=1` when serving over HTTPS to
mark the session cookie `Secure`; it is left off by default so local HTTP works.
Due-date state is evaluated in each project's governing timezone (the `tzdata` package
supplies the IANA database on Windows).

It does **not** yet ingest private evidence, publish files, send notifications, or
perform AI matching. Those capabilities will be added behind the same access boundary.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\astra init-owner --email owner@example.org
.venv\Scripts\astra serve --host 127.0.0.1 --port 8765
```

The owner password is requested without echo. Application data defaults to
`%LOCALAPPDATA%\AstraProjectTracker`; override it for testing with `ASTRA_HOME`.

Recovery commands for whoever runs the server (PDDS2D). Each first prints the database it
will change and stops if that file does not exist (it never creates one; set `ASTRA_HOME`),
then asks you to type the target's email to confirm (`--yes` skips that, for scripts); it
exits 0 when done, 1 when refused, aborted or the database cannot be used, and 2 for a
usage error:

```powershell
.venv\Scripts\astra transfer-primary --to deputy@example.org
.venv\Scripts\astra reset-password --email someone@example.org
```

`transfer-primary` makes an active secondary owner the primary owner; the old primary
stays a secondary owner and is signed out everywhere. `reset-password` works for any
active user and needs an interactive terminal: the new password (8+ characters) is typed
twice and is never taken from the command line, the environment or piped input; the user is
signed out everywhere and their failed sign-ins are cleared. Both are recorded in the
owner-access history as "via server command". A transfer notifies every active owner; a
reset notifies the user, and the other owners only when the user is an owner. For another
data folder set `$env:ASTRA_HOME = "D:\Astra Data"` first. On Linux (for example the planned Oracle
Cloud VM) always set `ASTRA_HOME`, because the default is a Windows folder:
`ASTRA_HOME=/srv/astra .venv/bin/astra reset-password --email someone@example.org`,
run as the user the server runs as.

Attachment links are off until the installation names the folders they may point into:
set `ASTRA_ATTACHMENT_ROOTS` to one or more absolute folders separated by `;` (for example
`$env:ASTRA_ATTACHMENT_ROOTS = "D:\Shared\Astra"`) before `astra serve`. Only paths inside
those folders can be linked or imported, and only those are checked for "file not found".

Do not expose the development HTTP server directly to the public internet. Private
network/Tailscale access and HTTPS termination will be configured during deployment.

## Verify locally

The repository test runner supplies the `src` import path itself, so it works before
an editable install:

```powershell
python tests\run.py
node --check src\astra\static\app.js
```

These are offline structural and HTTP integration checks. They do not prove live
deployment, browser compatibility on every device, or multi-user production safety.

For an optional visual check, run `python tests\ui_fixture_server.py`, open
`http://127.0.0.1:8766`, and sign in with the fixture-only credentials declared in
that helper. Stop the server afterward and remove `tmp_ui_accept`. Never expose this
synthetic fixture server beyond the local computer.
