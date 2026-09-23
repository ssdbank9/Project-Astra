# Excel / CSV import

Status: implemented for `C9KPH6` (2026-09-22). Requested by Aly Jafferani in
`#astra-builder` on 2026-09-22 after sharing the Rupani Academy executive Gantt
workbook; the two scope changes of the same day (Manager access, locked and
Owner-configurable template, dd-mm-yyyy dates) are folded in. The independent
review of the same day (probes P1c-P21e) and Aly's 07:18 UTC request for a
template that comes pre-filled with the project's tasks are addressed in the
follow-up commit `fix(C9KPH6)`; the behaviour below is the corrected one.

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
| Member / Viewer, Chairman without a project role | Blocked: `protected_action_blocked` project event and Owner notification, HTTP 403. An attempt with no target project (a Chairman or non-manager uploading without choosing a project) is notified to the Owner but not audited against a project, since there is none. The audit rows are written after the request's own transaction has rolled back, so they survive | No | No |

A Manager's import may only do what that Manager could do by hand. Owner-only
actions in a row are skipped with a warning, never silently applied:
`W_PROTECTED_STATUS` (a status that needs an Owner decision or a lifecycle record - as the
target of the change, and equally as the status the task would be moved *out of*: a
Manager's row cannot take a completed, on-hold, cancelled or submitted task back into work),
`W_BASELINE_SKIPPED` (Original Due Date), `W_ATTACHMENTS_SKIPPED`, `W_ENTITY_SKIPPED`.
For the Owner and a Manager alike, a row for a completed, cancelled or abandoned task is
skipped whole with `W_CLOSED_TASK` (see "Closed tasks").

## Before a Manager imports: users and access

People are matched by work email (a bare display name is accepted only when it
matches exactly one active user, with a `W_PERSON_BY_NAME` warning). A person who
is not an active Astra user, or has no access to the target project, leaves the
task unassigned with `W_UNRESOLVED_PERSON` / `W_PERSON_NOT_ELIGIBLE`. Who is
matched, and what a miss says, follows the actor's view of the directory
(regression review SECURITY-4, 2026-09-22): the App Owner, who may read
`/api/users`, is matched against every account and sees the precise reason (no
such email, deactivated, no access, name not found); a Manager's file is matched
only against the people the Manager can already see — the `list_assignable_users`
set: active members of the target project plus the App Owner and chairman — and
every miss, whatever its reason, is the one `W_PERSON_NOT_ELIGIBLE` text
`'<text>' is not an active member of this project; ask the App Owner to grant
access, then re-import.` The People sheet cross-check follows the same rule
(`unknown_user` / `inactive` / `no_access` for the Owner, always `no_access` with
one text for a Manager), so a preview cannot be used to enumerate accounts. The
App Owner therefore prepares the project first, in the **People** panel:

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

## The template (workbook v2)

`GET /api/import/template.xlsx` (and `.csv`) is generated at request time from the
current configuration with `zipfile`; nothing is stored on disk. The workbook has
six sheets in the Simple preset and seven in the Full preset, built by the stdlib
builder in `importer._TemplateWorkbook` (it reproduces the openpyxl reference design of
2026-09-22, which lives in the session scratchpad and not in this repository):

| Sheet | Read by the importer | Protection | Purpose |
| --- | --- | --- | --- |
| `README` | no | fully locked | Simple: eight short steps. Full: five steps, twelve rules, header-colour legend, a column dictionary generated from the same metadata as the sheet, and the list of columns the Owner can switch on |
| `Project` | **yes** (project header) | labels and guidance locked, Value column unlocked | Simple: Project Name (required), Project Manager Email, Timezone. Full: also Description, Filing Entity, Sponsor / Executive Owner Email, Working Days, Planned Start / Finish, Plan As-of Date, Source Document, Prepared By |
| `Tasks` | **yes** | header and structure locked; `A2:<last configured column>2001` unlocked (`A2:R2001` in Full, `A2:I2001` in Simple); rows may be inserted, deleted and filtered; columns may not | header row 1 = configured labels, frozen at `C2`, autofilter, 2,000 data rows with validation |
| `Example` | never | fully locked, grey tab, italic text | Simple: `EX-001` a task and `EX-001.1` its step. Full: three worked rows (`EX-001` a High task, `EX-001.1` a Delayed action-item step with Original Due Date, `EX-002` a Critical milestone waiting on `EX-001`) |
| `People` | **yes** (cross-check only) | header locked, `A2:D201` unlocked, column E computed | Full preset (or any column beyond the Simple set) only: Email, Full Name, Role on project, Notes, "Used in Tasks" (`COUNTIF` over Owner Email and Collaborators) |
| `Lists` | no | hidden, locked | named ranges `Lists_Status`, `Lists_Criticality`, `Lists_Type`, `Lists_YesNo`, `Lists_ProjectRole`, `Lists_Timezone`, `Lists_WorkingDays`, `Lists_Entity` and `Lists_<key>` for each custom list column |
| `_astra` | **yes** (marker) | veryHidden, locked | `B1` configuration hash (`52cd3da7813769c1` for the Simple default, `53133bf237fe9b3c` for Full), `B2` header fingerprint, `B3` family, `B4` build time; defined names `AstraTemplateVersion` and `AstraHeaderFingerprint` |

Tasks validation, per column kind: Import Key `LEN 1..40`, no spaces, `COUNTIF` uniqueness;
Title 1..200 characters; Parent Key must be another row's key (warning style, so keys
already in Astra pass); Owner Email has an `@` and a dot, no spaces or `;`; Collaborators,
Reviewers, Approvers contain `@` and no commas; Start Date and Original Due Date are dates
between 01-01-2000 and 31-12-2100; Due Date is a date in range and `>= Start Date`; Status,
Criticality, Milestone and custom list columns are dropdowns from the named ranges;
`% Complete` 0..100; Duration 1..3660; Next Action <= 200 characters; other text <= 4000.
Date cells carry the `dd-mm-yyyy` number format. Conditional formats mark a blank Import
Key or Title on a row that has content, a Due Date before its Start Date, and band even rows.
Header colours: navy = core, slate = optional built-in, teal = Owner-added.

Sheet protection (SHA-512 hash, password `astra-template`, a guard against accidental
edits and not a secret) is applied to every sheet. Column widths follow the reference
design. Header hover comments from the openpyxl reference are not emitted (they need a
VML part); the same text is in the input messages and the README dictionary.

### Project-scoped download: the template pre-filled with the project's tasks

`GET /api/import/template.xlsx?project_id=<id>` (and `.csv`) returns the current
template with the **Tasks** sheet already listing that project's tasks, so a project
manager who prefers Excel edits what Astra has instead of retyping it, and a re-upload
updates the same tasks (Aly, 2026-09-22 07:18 UTC). The Import dialog's download links
switch to "Download template (with this project's tasks)" as soon as a target project
is selected.

- Authorization: App Owner for any project, Manager for the projects they manage,
  everyone else HTTP 403; an unknown project is 404. The blank template
  (`project_id` absent or empty) is served to the App Owner and to anyone who manages
  at least one project - the same people who may read the template configuration
  (authorization matrix) - and is 403 for everyone else.
- Keys: a task that has no Import Key yet gets one at download time - `T-001`,
  `T-002` ... continuing above the highest `T-nnn` already in the project and skipping
  any key in use - stored in `tasks.import_key` with a `task_event`
  `import_key_assigned` (no Owner notification), all inside one transaction. A second
  download assigns nothing new. Hand-made tasks and imported tasks therefore share one
  key space and the file's rows carry **literal** keys; the blank rows below keep the
  pre-filled formula, offset so the first blank row yields the next free number
  (`=IF(B8="","","T-"&TEXT(ROW()-1+3,"000"))` when six tasks occupy rows 2-7 and
  `T-009` is the highest in use).
- Rows: parents come before their steps, each level ordered by Start, Due, Title.
  Every enabled column that maps to a task field is filled: Import Key, Title, Step of
  (Key) / Parent Key (the parent's key), Owner Email, Start Date, Due Date, Status
  (label), Criticality, % Complete, Next Action, Predecessors (keys), Collaborators /
  Reviewers / Approvers (emails), Attachment Links, Milestone (Yes/No), Description
  (the full stored description), Notes (the text of the description's "Notes:"
  section) and custom columns from `tasks.import_extras`. Original Due Date stays blank
  (a baseline is never overwritten) and Type repeats only a value the task already
  carries in `import_extras`, so re-uploading the file unedited previews every row as
  **unchanged** with no warnings; a single edited Title previews as one update (with
  `W_TITLE_CHANGED`).
- Project sheet: name, the first Manager's email (falling back to
  `projects.manager_user_id`), timezone and, in the Full shape, description, working
  days and planned dates. The People sheet (Full shape only) lists the project's active
  members with their role.
- The file name is `astra-import-<project-slug>.xlsx` / `.csv`.

### Presets: Simple (default) and Full

Two presets live in `importer.PRESETS`; the Owner applies either from Template settings
(`PUT /api/import/template-config` with `{"preset": "simple"|"full"}`) and may still
toggle, rename, reorder or add columns afterwards. All 25 columns stay defined in either
preset; a preset only changes the `enabled` flags.

- **Simple** (the built-in default; hash `52cd3da7813769c1`, family
  `astra-import-simple`): nine columns — Import Key, Title, Step of (Key) (= Parent Key),
  Owner Email, Start Date, Due Date, Status, Criticality, Notes. The template's Import Key
  cells carry the formula `=IF(B2="","","T-"&TEXT(ROW()-1,"000"))`, so a key such as
  `T-001` appears as soon as a Title is typed and untouched rows stay blank; the user may
  overwrite it. Because the formula follows the row number, both READMEs say: add new
  rows at the bottom, do not insert or delete rows in the middle (a deleted row would
  shift every key below it onto another task); the preview's `W_TITLE_CHANGED` warning
  is the visible symptom when that happens anyway. A row whose only cell is an Import
  Key is ignored by the importer. The
  workbook has six sheets: an eight-line README, a three-row Project sheet (Project Name
  required, Project Manager Email, Timezone dropdown defaulting to Asia/Karachi), Tasks,
  a two-row Example (a task and a step), hidden Lists and veryHidden `_astra`. No People
  sheet.
- **Full** (workbook v2; hash `53133bf237fe9b3c`, family `astra-import-v2`): 18 columns —
  Import Key, Title, Type, Parent Key, Owner Email, Collaborators, Start Date, Due Date,
  Original Due Date, Status, % Complete, Criticality, Predecessors, Next Action / Decision
  Needed, Reason (if delayed or changed), Risk / Dependency, Description, Notes. Off:
  Duration (days), Reviewers, Approvers, Attachment Links, Project, Entity, Milestone. The
  workbook adds the twelve-row Project sheet, the three-row Example and the People sheet
  described above; the same extended shape is generated whenever any column outside the
  Simple set is enabled.

`Type` (custom list Task / Milestone / Action item, key `x_type`) supersedes the Yes/No
Milestone column: `Milestone` sets `tasks.is_milestone` (and Start = Due when one date is
given); Task and Action item stay ordinary tasks with the label kept in `import_extras`.
`Risk / Dependency` (custom text, key `x_risk_dependency`) is kept read-only on the task
until a RAID register exists. The importer accepts a workbook with or without the Project
and People sheets.

### Project and People sheets on upload

- The `Project` sheet is the project header. When the Owner imports without choosing a
  target, its Project Name finds an existing project (case-insensitive) or creates one
  with the sheet's description (plus a "Sponsor / Executive Owner" line), timezone,
  working days (`Every day` / `Mon-Fri` / `Mon-Sat` / `Sun-Thu`), planned start and
  finish, manager (email of an active user; also granted the
  `manager` membership) and filing entity (existing active entity only). Every active
  user named in the rows (Owner Email, Collaborators, Reviewers, Approvers) is eligible
  for the new project and is granted access when it is created — `manager` for the
  Project sheet's manager email, `member` for everyone else, never downgrading — so the
  assignments are kept instead of being dropped as "not eligible" (`I_ACCESS_GRANTED`
  info per row; a deactivated user still gets `W_PERSON_NOT_ELIGIBLE`). When a target is
  chosen — always the case for a Manager — a Project Name that differs from the chosen
  project puts `E_PROJECT_MISMATCH` on every row. Plan As-of Date and Source Document are
  recorded in the import summary. Typed values are validated, not trusted: a Timezone that
  is not a known zone (case-insensitive against the template's list, then `ZoneInfo`) falls
  back to `Asia/Karachi` and a Working Days value outside the four labels to `Every day`,
  each with a file warning naming the substitution, and the preview's `project_header`
  carries the **resolved** values that a created project would get. A Planned Finish Date
  before the Planned Start Date is `E_PROJECT_DATES` on every row when the file would create
  the project (the same order `set_project_schedule` enforces) and a file warning when the
  target already exists, because the sheet's dates are never applied to an existing project.
- The `People` sheet is cross-checked in preview: each row is `ready`, `unknown_user`,
  `inactive`, `no_access` or `group` (a name without an email) with a message naming the
  People row, so the App Owner knows exactly which accounts to add or grant before the
  Manager uploads. Users are never created by import.
- The `Example` sheet is ignored, and any Import Key starting with `EXAMPLE-` or `EX-` is
  refused (`E_EXAMPLE_ROW`).
- Only the sheet named `Tasks` is read for rows; `Lists` is ignored.

### Built-in columns (default order)

| Column | Astra field | Rule |
| --- | --- | --- |
| Import Key (core) | `tasks.import_key`, unique per project | `[A-Za-z0-9][A-Za-z0-9._-]{0,39}`; drives create-or-update. Canonicalised to upper case on lookup and storage (`t-001` and `T-001` are one key, matching the template's case-insensitive `COUNTIF` rule); Parent Key and Predecessors are matched the same way. Keys already stored are compared case-insensitively; new rows are stored upper-case |
| Project | target project when none is chosen | Owner only; one project per file; created when it does not exist |
| Entity | `project_entities` | Owner only; names of active entities; never created |
| Parent Key | `tasks.parent_task_id` | Import Key in the file or an existing task; cycles rejected |
| Title (core) | `tasks.title` | required on every row, up to 200 characters. The exception to the empty-cell rule: a blank Title on an existing key is `E_TITLE_MISSING`, not "leave as is" |
| Description | `tasks.description` | on update, replaces only when non-empty |
| Owner Email (core) | `tasks.owner_user_id` | active user with access to the project |
| Collaborators / Reviewers / Approvers | `task_reviewers` | `;`-separated emails; import only adds |
| Start Date (core), Due Date (core) | `tasks.start_date` / `due_date` | real Excel date, `dd-mm-yyyy` or `yyyy-mm-dd` text; a bare serial number follows the workbook's date system (1900 or 1904); prose is an error |
| Duration (days) | derived | fills the missing one of Start/Due |
| Original Due Date | `tasks.baseline_due_date` | Owner only; never overwrites an existing baseline |
| Status (core) | `tasks.status` | labels or synonyms (Not Started, Done, Delayed/At Risk, Blocked ...); on update, Submitted, Completed, On hold, Reopened and Changes requested are never set by import (`W_GOVERNED_STATUS`), and a task is never moved *out of* Submitted, Completed, On hold, Reopened, Changes requested, Cancelled or Abandoned either (`W_GOVERNED_STATUS` for the Owner, `W_PROTECTED_STATUS` for a Manager; the stored status stays and the change is made in Astra through its lifecycle action). A row for an existing **Completed, Cancelled or Abandoned** task changes nothing at all, see "Closed tasks" below |
| % Complete | `tasks.progress` | 0..100, `45%` and `0.45` accepted; a %-formatted Excel cell is read as displayed (stored 1.0 shown as 100% -> 100) |
| Criticality | `tasks.criticality` | Critical, High, Normal, Low or blank |
| Predecessors | `task_dependencies` (finish-to-start) | `;`-separated Import Keys; `FS+2d` suffixes are recorded in Notes with `W_LAG_IGNORED` |
| Milestone (off by default) | `tasks.is_milestone` | Yes/No; superseded by the `Type` list column; with one date, start = due |
| Next Action / Decision Needed | `tasks.next_action_note` | shown as the task's next action while it is open |
| Reason (if delayed or changed) | `task_events.reason` | default `Excel import <file> row <n>` |
| Notes | `tasks.description` "Notes:" section | also receives anything that could not be stored exactly |
| Attachment Links | `task_attachments` | Owner only; links, never bytes |

### Closed tasks (`W_CLOSED_TASK`)

A completed, cancelled or abandoned task is a fixed record: only the governed reopen in
Astra (reason and revised due date) changes it (App Owner decision, 2026-09-23, ticket
T8WHJR). A row whose Import Key names such a task is therefore skipped as a whole, for the
Owner and for a Manager alike: no title, description, owner, dates, progress, criticality,
milestone, next action, custom value, parent, predecessor, person or attachment link from
the row is applied. When the row would have changed anything it carries the warning
`W_CLOSED_TASK` ("This task is completed, a fixed record, so none of this row's changes were
applied. Reopen the task in Astra first ..."), its action is `unchanged` and the preview
shows the stored values; an unedited row for a closed task stays quiet. Other rows may still
name a closed task as their predecessor or parent, since that changes only the open task.
The commit re-validates inside its write transaction, so a task closed between preview and
commit is caught there: the plan fingerprint then differs and the commit is refused with
HTTP 409.

### Owner configuration (`import_template_config`)

`PUT /api/import/template-config` (Owner) stores one JSON row: every built-in column
with `enabled`, `label` and position, plus custom columns (`label`, `type` in
`text | number | date | list`, `values` for lists, `required`). Core columns —
Import Key, Title, Start Date, Due Date, Status, Owner Email — cannot be disabled or
renamed. Validation: unique labels, known built-in keys, non-empty list values, at
most 40 enabled columns, and a client-supplied custom `key` must match
`x_[a-z0-9_]{1,40}` (it names a defined range in the workbook; keys derived from the
label always fit). A custom Number cell must be a finite number within ±1e15
(`E_CUSTOM_INVALID` otherwise: nan / inf are not JSON). Saving increments `version` and changes the hash, so a
template downloaded earlier is rejected on upload with "The import template has
changed since this file was downloaded". `{"reset": true}` restores the default.
Custom column values are stored in `tasks.import_extras` (JSON keyed by the column
key `x_<slug>`), merged on re-import, and shown read-only in the task detail under
**Imported fields**. `GET /api/import/template-config` is readable by the Owner and
by Managers.

## Upload rules

- `.xlsx` (from the template) or `.csv`; `.xlsm`, `.xlsb`, `.xls` are refused. 5 MB,
  2,000 rows, 40 columns, 4,000 characters per cell. Inside the zip, at most 200 parts,
  8 MB declared per part and 20 MB declared in total (judged on the central directory,
  so a forged size is refused before anything is inflated); any of these is HTTP 413
  (`ImportTooLarge`).
- `.xlsx`: the `_astra` marker must equal the current configuration hash and the
  `Tasks` header row must equal the configured labels in order; mismatches are listed by
  column letter. Data in a column to the right of the last header is never imported and
  is reported per row (`W_EXTRA_DATA`, "extra data ignored in column J"; a row with
  nothing else on it gets a file-level warning). The `Project` and `People` sheets are
  read by name when present. Dates may be real Excel date cells (1900 and 1904 systems;
  serials at or below 60 are refused as ambiguous, serials beyond 31-12-9999 - such as
  `20260904` typed as digits - and nan / inf are `E_DATE_INVALID` naming the column, never
  a server error), bare serial numbers in the workbook's own date system, or `dd-mm-yyyy` /
  `yyyy-mm-dd` text. Percent-formatted numeric cells arrive as the displayed percentage
  (`xlsx_reader.Percent`). An Excel error value (`#N/A`, `#REF!`, `#VALUE!` ...) in any
  column is `E_CELL_ERROR` naming the column; it is never imported as text.
- `.csv`: UTF-8 (BOM stripped) with a cp1252 fallback warning; a UTF-16 file (Excel's
  "Unicode Text") is refused with a hint to save as CSV UTF-8; CR, LF and CRLF line
  endings are all read, a malformed file is a 400 with the parser's reason, and a cell
  longer than 4,000 characters is `E_CELL_TOO_LONG` on its row rather than a parser error;
  delimiter sniffed (`,` `;` tab); headers match the configured labels, or the built-in default
  headers and aliases (`Task Name`, `Assignee`, `Finish`, `Depends On`, ...) with a
  per-row `W_HEADER_ALIAS` warning; unknown columns are listed and ignored.
- An empty cell means "leave as is" on update, never "clear" - except Title, which is
  required on every row (`E_TITLE_MISSING`).

## Preview and commit

`POST /api/import/preview` and `POST /api/import/commit` take the raw file bytes
(`Content-Type` other than JSON, own 5 MB limit, HTTP 413 above it) with headers
`X-Filename` (percent-encoded), `X-Project-Id` (blank = Owner creates or finds the
project named in the file), `X-Options` (percent-encoded JSON: `valid_rows_only`,
`default_reason`) and, for commit, `X-Sha256` of the previewed bytes and
`X-Plan-Fingerprint`, the preview's `plan_fingerprint` (HTTP 409 when either differs).
The fingerprint is the SHA-256 of the sorted (Import Key, action, existing task id)
triples the file produces against the project at that moment, so a plan that changed
underneath the same bytes - a hand-made task took the row's key through the pre-filled
download, a task was edited meanwhile - is refused instead of silently turning a create
into an update. The dialog always sends both headers; an API client that omits them
skips the check. CSRF and the session cookie apply as for every other mutation. Only
these two routes read the body as raw bytes; every other route keeps the 1 MB JSON
ceiling whatever `Content-Type` the client declares.

Preview writes nothing and returns per row: `action` (create / update / unchanged /
error), `level` (ok / warning / error), findings with stable codes, the resolved
values (dates as dd-mm-yyyy) and, for updates, `old → new` changes (including
`parent_key`). Errors block their own row and any row whose parent or predecessor
they are: the propagation runs after every row-level and dependency check and repeats
until stable, so a parent that only fails in dependency wiring takes its steps and
successors with it instead of importing them top-level (a three-row dependency cycle
therefore errors all three rows). Import Keys are unique per project only: the same
`T-001` may exist in every project. Parent and dependency cycles are checked on one
graph per kind whose nodes are task ids for tasks already in the project and file
keys for new rows, so a cycle that runs through an existing task absent from the file
is found too (`E_PARENT_CYCLE`, `E_DEP_CYCLE`). Re-parenting an existing task under a
row that is new in the same file is an update, applied after the new parent is
created. A Title that differs from the stored one is `W_TITLE_CHANGED` (the symptom of
shifted pre-filled keys). Commit is refused while errors exist unless
`valid_rows_only` is set.

Commit opens one `BEGIN IMMEDIATE` transaction and, inside it, re-parses and
re-validates the same bytes - so the parent and dependency cycle checks and the snapshot
of existing tasks see exactly the state the writes apply to, with no window for another
writer - then: create the project if needed (Owner), insert or update tasks by
`(project_id, import_key)`, wire parents, apply the explicit baseline (Owner, only
when none exists) and `_ensure_baseline`, add reviewers, attachment links and
entities (union, never removal), record `task_created` / `task_updated` (a row that only
added people, links, predecessors or a parent still bumps `updated_at` and `revision`,
and the additions appear as `import_additions` in the event's after snapshot) /
`criticality_changed` / `parent_changed` / `attachment_added` / `dependency_added`
events with the row's Reason, insert finish-to-start dependencies (cycle-checked in
preview against existing and new edges), write one `import_committed` project event
and one `imports` row (actor, filename, SHA-256, summary JSON, full CSV report).
Any exception rolls everything back; when the unique `(project_id, import_key)` index
fires because another writer took a key between preview and commit, the rollback is
reported as HTTP 409 with a "run the preview again" message, not 500. Import never
deletes a task, a link or a dependency, never overwrites a baseline, never moves a
task into `submitted`, `completed`, `on_hold`, `reopened` or `changes_requested` on
update (`W_GOVERNED_STATUS`; each needs the record its lifecycle action writes) and never
writes to a completed, cancelled or abandoned task (`W_CLOSED_TASK`).

`GET /api/imports` lists imports (Owner: all; Manager: their own and their managed
projects). `GET /api/imports/<id>/report.csv` downloads the stored report
(`row, import_key, action, level, title, owner, start_date, due_date, status,
criticality, task_id, findings`, dates dd-mm-yyyy).

## UI

An **Import** button appears beside **Templates** for the Owner and for anyone who
manages at least one project (`GET /api/import/targets`). The dialog has three
steps — Upload (template links, which become "Download template (with this project's
tasks)" and carry `?project_id=` once a target project is selected; target project,
drop zone or file picker, options),
Review (summary chips that filter the table, the Project-sheet header line, a People
panel listing who the Owner still has to add or grant, per-row badge and findings,
`old → new` cells, Back / Import N rows), Confirm (counts, project, report link). Every
server-provided string the dialog puts into `innerHTML` — row values, findings, the
Project-sheet header line including the manager email, People rows, file names,
template labels — goes through `escapeHtml`; the preview JSON itself is returned
verbatim (a test pins both). The Owner also
gets **Template settings** inside the dialog: Simple / Full preset buttons,
enable/disable, rename, reorder, add and remove custom columns, reset, save. Colouring is class-based with `data-level`
attributes (CSP `style-src 'self'`), every level is also a word, the dialog closes
on Escape and returns focus to the opener, and the table stacks into cards under
760 px.

## Not in this ticket

- Revert of an import (the stored before/after report is the input for a future
  ticket).
- Dependency types other than finish-to-start and lags (recorded in Notes).
- Grid-derived dates from period-column Gantt charts such as the Rupani workbook:
  rows with prose dates are errors the user fixes in the template.
