# Excel / CSV import

Status: implemented for `C9KPH6` (2026-09-22). Requested by Aly Jafferani in
`#astra-builder` on 2026-09-22 after sharing the Rupani Academy executive Gantt
workbook; the two scope changes of the same day (Manager access, locked and
Owner-configurable template, dd-mm-yyyy dates) are folded in.

The service layer is the authorization boundary (`AstraService.import_preview`,
`import_commit`, `import_template`, `import_targets`, `get_/set_import_template_config`,
`list_imports`, `import_report`). Parsing, header matching, cell coercion, row
validation and the commit plan live in `src/astra/importer.py`; the workbook reader
in `src/astra/xlsx_reader.py`. Both use the standard library only.

## Who may import

| Actor | Import into a project | Create a project from the file | Change the template |
| --- | --- | --- | --- |
| App Owner | Any open project | Yes (from the `Project` column) | Yes |
| Project Manager | Projects where they hold the `manager` membership | No | No (may read the configuration) |
| Member / Viewer, Chairman without a project role | Blocked: `protected_action_blocked` project event and Owner notification, HTTP 403 | No | No |

A Manager's import may only do what that Manager could do by hand. Owner-only
actions in a row are skipped with a warning, never silently applied:
`W_PROTECTED_STATUS` (a status that needs an Owner decision or a lifecycle record),
`W_BASELINE_SKIPPED` (Original Due Date), `W_ATTACHMENTS_SKIPPED`, `W_ENTITY_SKIPPED`.

## Before a Manager imports: users and access

People are matched by work email (a bare display name is accepted only when it
matches exactly one active user, with a `W_PERSON_BY_NAME` warning). A person who
is not an active Astra user, or has no access to the target project, leaves the
task unassigned with `W_UNRESOLVED_PERSON` / `W_PERSON_NOT_ELIGIBLE`. The App Owner
therefore prepares the project first, in the **People** panel:

1. **Add user** for each person named in the sheet (email, display name, password,
   role `member`; `chairman` only for organization-wide read).
2. **Grant project access**: choose the project, the user and the role — `manager`
   for the person who will upload the file, `member` for Task Owners and
   collaborators, `viewer` for read-only.
3. Share the template with the Manager. The Manager signs in, opens **Import**,
   picks the project from the target list (only managed projects are offered) and
   uploads the filled template. Owner Emails in the file must be the emails created
   in step 1.

The Owner sees the Manager's import in the Inbox (`import committed: <file> into
<project>`) and in the project activity (`import_committed`), plus the usual
per-task change notifications.

## The template

`GET /api/import/template.xlsx` (and `.csv`) is generated at request time from the
current configuration with `zipfile`; nothing is stored on disk.

- Sheet `Tasks`: one header row (locked, bold, frozen), one example row with Import
  Key `EXAMPLE-001` (the importer refuses it, so it must be overwritten or deleted),
  2,000 unlocked data rows with data validation: dropdowns for Status, Criticality,
  Milestone and custom list columns; date validation `01-01-2000..31-12-2100` on
  Start Date, Due Date, Original Due Date and custom date columns, cells formatted
  `dd-mm-yyyy`; whole-number validation on `% Complete` (0..100) and
  `Duration (days)` (1..3660); text-length validation on Import Key (1..40) and
  Title (1..200). Sheet protection (SHA-512 hash, password `astra-template`, which
  is a guard against accidental edits and not a secret) allows formatting and
  inserting/deleting rows but forbids inserting, deleting or sorting columns.
- Sheet `README`: filling rules and the column list, fully locked.
- Sheet `_astra` (hidden): `AstraTemplateVersion` = hash of the active column
  configuration; `AstraHeaderFingerprint` = the header labels. Defined names of the
  same two names point at these cells.

### Built-in columns (default order)

| Column | Astra field | Rule |
| --- | --- | --- |
| Import Key (core) | `tasks.import_key`, unique per project | `[A-Za-z0-9][A-Za-z0-9._-]{0,39}`; drives create-or-update |
| Project | target project when none is chosen | Owner only; one project per file; created when it does not exist |
| Entity | `project_entities` | Owner only; names of active entities; never created |
| Parent Key | `tasks.parent_task_id` | Import Key in the file or an existing task; cycles rejected |
| Title (core) | `tasks.title` | required, up to 200 characters |
| Description | `tasks.description` | on update, replaces only when non-empty |
| Owner Email (core) | `tasks.owner_user_id` | active user with access to the project |
| Collaborators / Reviewers / Approvers | `task_reviewers` | `;`-separated emails; import only adds |
| Start Date (core), Due Date (core) | `tasks.start_date` / `due_date` | real Excel date, `dd-mm-yyyy` or `yyyy-mm-dd` text; prose is an error |
| Duration (days) | derived | fills the missing one of Start/Due |
| Original Due Date | `tasks.baseline_due_date` | Owner only; never overwrites an existing baseline |
| Status (core) | `tasks.status` | labels or synonyms (Not Started, Done, Delayed/At Risk, Blocked ...) |
| % Complete | `tasks.progress` | 0..100, `45%` and `0.45` accepted |
| Criticality | `tasks.criticality` | Critical, High, Normal, Low or blank |
| Predecessors | `task_dependencies` (finish-to-start) | `;`-separated Import Keys; `FS+2d` suffixes are recorded in Notes with `W_LAG_IGNORED` |
| Milestone | `tasks.is_milestone` | Yes/No; with one date, start = due |
| Next Action | `tasks.next_action_note` | shown as the task's next action while it is open |
| Reason | `task_events.reason` | default `Excel import <file> row <n>` |
| Notes | `tasks.description` "Notes:" section | also receives anything that could not be stored exactly |
| Attachment Links | `task_attachments` | Owner only; links, never bytes |

### Owner configuration (`import_template_config`)

`PUT /api/import/template-config` (Owner) stores one JSON row: every built-in column
with `enabled`, `label` and position, plus custom columns (`label`, `type` in
`text | number | date | list`, `values` for lists, `required`). Core columns —
Import Key, Title, Start Date, Due Date, Status, Owner Email — cannot be disabled or
renamed. Validation: unique labels, known built-in keys, non-empty list values, at
most 40 enabled columns. Saving increments `version` and changes the hash, so a
template downloaded earlier is rejected on upload with "The import template has
changed since this file was downloaded". `{"reset": true}` restores the default.
Custom column values are stored in `tasks.import_extras` (JSON keyed by the column
key `x_<slug>`), merged on re-import, and shown read-only in the task detail under
**Imported fields**. `GET /api/import/template-config` is readable by the Owner and
by Managers.

## Upload rules

- `.xlsx` (from the template) or `.csv`; `.xlsm`, `.xlsb`, `.xls` are refused. 5 MB,
  2,000 rows, 40 columns, 4,000 characters per cell.
- `.xlsx`: the `_astra` marker must equal the current configuration hash and the
  header row must equal the configured labels in order; mismatches are listed by
  column letter. Dates may be real Excel date cells (1900 and 1904 systems; serials
  at or below 60 are refused as ambiguous) or `dd-mm-yyyy` / `yyyy-mm-dd` text.
- `.csv`: UTF-8 (BOM stripped) with a cp1252 fallback warning; delimiter sniffed
  (`,` `;` tab); headers match the configured labels, or the built-in default
  headers and aliases (`Task Name`, `Assignee`, `Finish`, `Depends On`, ...) with a
  per-row `W_HEADER_ALIAS` warning; unknown columns are listed and ignored.
- An empty cell means "leave as is" on update, never "clear".

## Preview and commit

`POST /api/import/preview` and `POST /api/import/commit` take the raw file bytes
(`Content-Type` other than JSON, own 5 MB limit, HTTP 413 above it) with headers
`X-Filename` (percent-encoded), `X-Project-Id` (blank = Owner creates or finds the
project named in the file), `X-Options` (percent-encoded JSON: `valid_rows_only`,
`default_reason`) and, for commit, `X-Sha256` of the previewed bytes (HTTP 409 when
they differ). CSRF and the session cookie apply as for every other mutation.

Preview writes nothing and returns per row: `action` (create / update / unchanged /
error), `level` (ok / warning / error), findings with stable codes, the resolved
values (dates as dd-mm-yyyy) and, for updates, `old → new` changes. Errors block
their own row and any row whose parent or predecessor they are; commit is refused
while errors exist unless `valid_rows_only` is set.

Commit re-parses and re-validates the same bytes, then runs one `BEGIN IMMEDIATE`
transaction: create the project if needed (Owner), insert or update tasks by
`(project_id, import_key)`, wire parents, apply the explicit baseline (Owner, only
when none exists) and `_ensure_baseline`, add reviewers, attachment links and
entities (union, never removal), record `task_created` / `task_updated` /
`criticality_changed` / `parent_changed` / `attachment_added` / `dependency_added`
events with the row's Reason, insert finish-to-start dependencies (cycle-checked in
preview against existing and new edges), write one `import_committed` project event
and one `imports` row (actor, filename, SHA-256, summary JSON, full CSV report).
Any exception rolls everything back. Import never deletes a task, a link or a
dependency, never overwrites a baseline and never moves a task into
`submitted`, `completed`, `on_hold` or `reopened` on update (`W_GOVERNED_STATUS`).

`GET /api/imports` lists imports (Owner: all; Manager: their own and their managed
projects). `GET /api/imports/<id>/report.csv` downloads the stored report
(`row, import_key, action, level, title, owner, start_date, due_date, status,
criticality, task_id, findings`, dates dd-mm-yyyy).

## UI

An **Import** button appears beside **Templates** for the Owner and for anyone who
manages at least one project (`GET /api/import/targets`). The dialog has three
steps — Upload (template links, target project, drop zone or file picker, options),
Review (summary chips that filter the table, per-row badge and findings, `old → new`
cells, Back / Import N rows), Confirm (counts, project, report link). The Owner also
gets **Template settings** inside the dialog: enable/disable, rename, reorder, add
and remove custom columns, reset, save. Colouring is class-based with `data-level`
attributes (CSP `style-src 'self'`), every level is also a word, the dialog closes
on Escape and returns focus to the opener, and the table stacks into cards under
760 px.

## Not in this ticket

- Revert of an import (the stored before/after report is the input for a future
  ticket).
- Dependency types other than finish-to-start and lags (recorded in Notes).
- Grid-derived dates from period-column Gantt charts such as the Rupani workbook:
  rows with prose dates are errors the user fixes in the template.
