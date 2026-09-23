# Astra authorization matrix

Status: implemented baseline for `HS3JRY` (2026-09-20); reconciled against the
service, HTTP routes, tests, `README.md` and `CONTEXT.md` on 2026-09-21; import rows
and the source-status protection added for `C9KPH6` on 2026-09-22 (adversarial
review AS-1, AS-2, DTJ-03); person resolution in import files scoped to the actor's
view of the directory the same day (regression review SECURITY-4); concurrency and
Owner-request decisions hardened under `SRFCZD` on 2026-09-22.

The service layer is the authorization boundary. HTTP and browser controls must
call the same `AstraService` methods; hiding a control is not an authorization
decision.

| Capability | App Owner | Project Manager | Viewer/member | Chairman without an explicit project role |
| --- | --- | --- | --- | --- |
| View authorized projects/tasks/files | All | Granted projects | Granted projects | Organization-wide read |
| Create/edit ordinary task work | Yes | Granted projects | No | No |
| Accept/return submissions, hold, reopen, close, or decide schedule proposals | Direct | Creates pending Owner request; live state unchanged | Blocked and audited | Blocked and audited |
| Add/remove attachment links | Yes | No | No | No |
| Mark/unmark final results | Yes | No | No | No |
| Read authorized attachment/final-result records | Yes | Yes | Yes | Yes |
| Publish templates, administer access, or configure calendars | Yes | No | No | No |
| Import tasks from Excel/CSV into an existing project (`import_preview` / `import_commit`) | Yes | Managed projects only; Owner-only row actions (Original Due Date, Entity, Attachment Links, protected statuses) are skipped with a per-row warning | Blocked, audited and Owner notified | Blocked, audited and Owner notified |
| Create a project from an import file, or change the import template configuration | Yes | No (may read the configuration) | No | No |
| Download the import template (blank, or pre-filled with a project's tasks) or read the template configuration (`import_template`, `get_import_template_config`) | Yes | Yes; the pre-filled download for managed projects only | No (403) | No (403) |
| Resolve the people an import file names (Owner Email, Collaborators, Reviewers, Approvers, People sheet) | Against every account, with the precise reason for a miss (`W_UNRESOLVED_PERSON` / `W_PERSON_NOT_ELIGIBLE`; People statuses `unknown_user`, `inactive`, `no_access`) | Against the `list_assignable_users` set only (active members of the target project, App Owner, chairman); every miss is the one neutral `W_PERSON_NOT_ELIGIBLE` text and People status `no_access`, so a preview cannot enumerate accounts | No import | No import |
| Move a task *out of* completed, cancelled, abandoned, submitted, on hold, changes requested or reopened (`update_task` with such a source status, or an import row that changes the status) | Completed, cancelled, abandoned: only through `reopen_task` (reason and revised due date, `task_reopened`); submitted: only through the submission decision; on hold, changes requested, reopened: `update_task` with a reason (no dedicated release action exists). An import row never changes it (`W_GOVERNED_STATUS`) | Creates a pending Owner request `update_task_status` whose payload names `from_status` (HTTP 202); live state unchanged. An import row keeps the stored status (`W_PROTECTED_STATUS`) | Blocked | Blocked |

`Chairman` is retained as an organization-wide read role for compatibility. It
no longer grants implicit mutation power through `can_manage_project`. A person
with that global role may receive an explicit project membership; any capability
then comes from that project role, not from the Chairman label.

## Protected action outcome

A permitted Manager or designated approver attempt creates one idempotent pending
`owner_action_requests` row, task/project audit event, and Owner notification.
The HTTP endpoint returns `202 Accepted` with a `request` object. The original
task, submission, schedule proposal, checkpoint, or project remains unchanged.
The Owner can list pending requests through `GET /api/owner-action-requests`, and
the browser Inbox shows them under **Needs action**. The Owner approves, rejects,
or cancels with `POST /api/owner-action-requests/{id}/decision`; stale task
revisions return HTTP 409 and leave the request pending. A successful approval and
the governed action commit together, while a direct equivalent Owner action
reconciles the matching pending request in the same transaction. A direct Owner
action resolves only pending requests with the same intent (for example the same
target status, submission, proposal, hold checkpoint and owner, or closure
residual set); every other request stays pending and untouched for an explicit decision.

An unauthorized Viewer/member or read-only Chairman attempt is rejected, audited,
and notified to the Owner when it targets a visible record. A blocked attachment
removal is always recorded as `attachment_removal_blocked` before the service
returns `403 Forbidden`.

## Current file boundary

The current application stores attachment link metadata, not managed file bytes.
The implemented mutation seams are add/remove attachment link and mark/unmark final
result; all are Owner-only. Project-authorized list/read remains available. Upload,
version, permanent-link, and streaming-download systems do not exist yet and cannot
be treated as implemented. When introduced, they must call the same Owner-only
service authorization boundary rather than adding route-only checks.

## Automation and offline replay

No automation runner or offline mutation replay subsystem exists in the current
codebase. There is therefore no alternate write seam today. Future implementations
must enter through the service authorization/request seam and carry the real actor,
expected revision, and audit attribution.

## Task update concurrency

`update_task` requires the caller's integer `expected_revision`. The service checks
it before validation and again in the conditional SQL update inside `BEGIN IMMEDIATE`.
Concurrent or replayed stale writes raise `Conflict` (HTTP 409), roll back, and emit
no task event. The browser includes the revision loaded with the detail form.

## Out of scope: production dashboard overflow

The legacy dashboard shows horizontal overflow and clipped toolbar content at a
1280 px wide viewport. This is a pre-existing shell layout issue tracked under
roadmap Gate 2 (responsive A-hybrid product shell). `HS3JRY` does not touch it and
must not be read as fixing or hiding it.
