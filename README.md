# Astra Project Tracker

Astra is a standalone private project-management hub designed to run on the owner's
computer. Source matching remains local. Ordinary users see only projects, tasks,
Gantt schedules, assignments, dates, and explicitly published files for scopes they
are allowed to access.

This first vertical slice provides:

- owner bootstrap and authenticated sessions;
- App Owner, Chairman (organization-wide read-only unless separately granted a project role),
  manager, and member roles;
- an owner-only People panel: create users, deactivate/reactivate them, and grant or
  revoke project access; task owners are chosen from users authorized on the project;
- project-scoped access;
- projects, tasks, responsible people, dates, criticality, progress, and dependencies;
- finish-to-start dependency creation, cycle prevention, blocking visibility, and audited removal;
- append-only task audit events;
- a task detail view with authorized inline editing (reason required for status/schedule
  changes), add/remove of multiple dependencies, and a human-readable event history;
- a governed work lifecycle: submissions are recorded and only the App Owner decides the
  protected actions — accept, request changes, reopen, hold, close, and schedule proposal
  decisions; an eligible project manager or designated approver may request them, which
  records one idempotent Owner request without changing live state; the Owner can approve,
  reject, or cancel that request from **Inbox — Needs action**; an accepted version is immutable
  and can only be superseded after an explicit reopen with a revised timeline; on-hold work
  requires a reason plus a mandatory follow-up checkpoint; and project closure is a separate
  App Owner-only event, with exceptional closure preserving a residual-work snapshot rather
  than silently completing unfinished tasks;
- attachment-link and final-result mutations (add/remove, mark/unmark) are App Owner-only,
  while every user authorized on the project may still read and list them;
- reviewers, approvers, and collaborators recorded separately from the accountable owner;
- entities and cross-entity project filing: a project keeps one stable id with links to one
  or more entities (the approved baseline entity list can be seeded on owner request);
- a portfolio dashboard with rolling due-bands (Overdue, Today, 1–7, 8–14, 15–30), combinable
  entity/project/status/criticality/owner and cumulative due-within filters, an "open work
  only" toggle, and a per-task "next action" shown separately from the accountable owner;
- criticality governance: task lists sort criticality-first (Critical→Low, Unrated last but
  visible) then by nearest due date, and criticality changes are confirmed with a reason and
  recorded as a dedicated audit event;
- parent/subtask hierarchy with a completed/total roll-up shown separately from a task's own
  declared progress, cycle-safe re-parenting, and clickable subtasks;
- a durable in-app notification inbox: the owner gets an idempotent record of every task change
  made by someone else (in-app only; marking read never deletes or approves anything);
- portfolio and per-project Gantt views with overdue and upcoming highlighting;
- task steps (subtasks) drawn as numbered, colour-coded segments inside the parent's Gantt
  bar: a shared tooltip on hover and keyboard focus, a chevron that expands the step rows,
  a `+N` disclosure for steps not drawn at this scale, an "n steps need dates" chip, a dashed
  extension where a step runs past its parent's dates, and a Schedule table twin with the
  same rows as text, which is the default at phone width; and
- Excel/CSV import of tasks and Gantt rows from a locked, Owner-configurable template
  (dropdowns, date validation, version marker): the App Owner imports anywhere and may create
  a project from the file, a project Manager imports into the projects they manage with
  Owner-only actions downgraded to warnings, every upload is previewed row by row before one
  transactional commit that creates or updates tasks by Import Key, never deletes, records
  audit events and stores a downloadable report (see `docs/design/excel-import.md`).

Integrity rules enforced at the service boundary: ordinary task updates must carry the
task's current `expected_revision` and stale writes return HTTP 409 without changing state
or audit history; completed, cancelled, and abandoned tasks are fixed records until the
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
