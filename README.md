# Astra Project Tracker

Astra is a standalone private project-management hub designed to run on the owner's
computer. Source matching remains local. Ordinary users see only projects, tasks,
Gantt schedules, assignments, dates, and explicitly published files for scopes they
are allowed to access.

This first vertical slice provides:

- owner bootstrap and authenticated sessions;
- App Owner, Chairman (organization-wide read-only unless separately granted a project role),
  manager, and member roles;
- an owner-only People screen: create users, deactivate/reactivate them, and grant or
  revoke project access; task owners are chosen from users authorized on the project;
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
  protected actions — accept, request changes, reopen, hold, close, and schedule proposal
  decisions; an eligible project manager or designated approver may request them, which
  records one idempotent Owner request without changing live state; the Owner can approve,
  reject, or cancel that request from **Inbox — Needs action**, where each request shows the
  status it asks for (and the status it moves from, when recorded), the requester's reason, and
  an Open task link; an accepted version is immutable
  and can only be superseded after an explicit reopen with a revised timeline; on-hold work
  requires a reason plus a mandatory follow-up checkpoint; and project closure is a separate
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
subtask, since the closed task's own row does not change. The task dialog follows these
rules (ARZWV7): on a closed task it drops the forms the server refuses and says "Reopen this
task to change it", with a link to the reopen form (offered on completed, cancelled and
abandoned tasks); a Manager there can only request a move back into draft, assigned, in
progress or delayed; on a submitted task the Status field is locked and points to Accept or
Request changes. This is guidance only; the server stays the authority. Task titles cannot be blanked; task
assignees must be active and authorized on the task's project; and operations against a
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

Database migrations are applied one SQL statement at a time inside a single
`BEGIN IMMEDIATE` transaction per schema version. The schema changes and that step's
`PRAGMA user_version` update therefore commit together or roll back together; a failed
or interrupted step can be retried without retaining only its earlier tables, indexes,
or columns. The same holds when `COMMIT` itself fails (for example a deferred foreign
key or `SQLITE_BUSY`): `db.transaction()` rolls back and re-raises the commit error, so
the connection is never left inside an open transaction. Regression tests exercise fresh creation, legacy upgrades, injected DDL
failures, retry, and equivalence between upgraded and freshly created schemas.

Sign-in protection: repeated failed logins for an email are throttled (5 failures in
15 minutes returns HTTP 429 until the window passes); a successful login clears that
email's failure history and prunes expired sessions. "Sign out everywhere" revokes all
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
active user and needs an interactive terminal: the new password (12+ characters) is typed
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
