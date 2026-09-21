# Astra Project Tracker — complete implementation handoff for Claude

> **⚠️ CURRENT STATUS lives in [`CODEX_HANDOFF_2026-09-19.md`](CODEX_HANDOFF_2026-09-19.md).**
> This document is the architectural/product baseline and is still authoritative for
> design, roles, and entities — but its status figures are stale (it says "14 tests";
> the suite is now **102 green**, DB schema **v9**). For the live board state, the jaira
> lanes, and what to do next, read the Codex handoff first. Board next-actions are also
> recorded inline as `jaira note`s on each in-flight ticket (`jaira resume` surfaces them).

Prepared: 2026-09-14  
Workspace: `C:\Users\Aly Jafferani\Documents\ChatGPT\New project\astra_project_tracker`  
Product-design baseline approved: 2026-09-08  
Current application version: `0.1.0`  
Current implementation status: early local vertical slice; not the complete approved product

## 1. Instruction to the next builder

You are continuing Astra, a private, owner-hosted, evidence-based project-management system. Read this document completely before changing code. Then read the authoritative files listed below, inspect the current source and tests, and preserve all existing user work.

Do not describe the current system as complete, production-ready, secure for shared deployment, or fully verified. Fourteen offline unit/HTTP tests pass, but live browser acceptance, private-source ingestion, OCR, notifications, deployment, backup restoration, and multi-user production security are not verified.

Work in bounded, reviewable slices. Before implementation, convert the selected slice into atomic requirements and map each one to code and tests. Before handoff, re-read the request and verify each requirement individually. Report missing, partial, assumed, blocked, and unverified items plainly.

Do not connect accounts, ingest private data, upload sources to an AI provider, send notifications or email, expose the server to a network, alter the existing Email Project Organizer, move archive files, or deploy Astra without explicit user authorization for that action.

The recommended next action is not a blind expansion of the current UI. First reconcile the approved integrated build sequence and existing Email Project Organizer state described in Sections 9 and 11. If the user wants to continue only the standalone tracker, obtain confirmation that this sequence is intentional and implement the bounded tracker slice in Section 12.

## 2. Source precedence and authoritative files

Apply sources in this order:

1. The user's newest explicit instruction.
2. Global instructions in `C:\Users\Aly Jafferani\.codex\AGENTS.md`.
3. The canonical mistakes log at `C:\Users\Aly Jafferani\.codex\mistakes.md`.
4. This handoff's factual record of the current Astra workspace.
5. The approved clean design at `C:\Users\Aly Jafferani\Documents\ChatGPT\New project\email_project_organizer\FINAL_DESIGN.md`.
6. The detailed decisions and phased plan at `C:\Users\Aly Jafferani\Documents\ChatGPT\New project\email_project_organizer\ASTRA_PLAN_AND_CONTEXT.md`.
7. The decision register at `C:\Users\Aly Jafferani\Documents\ChatGPT\New project\email_project_organizer\design-decisions.md`.
8. Pending global-log additions in this workspace's `pending-global-mistakes.md`.
9. Current code and tests as implementation evidence, not as authority to override the approved design.

The clean design says the baseline is approved; do not reopen settled product questions. Actual identities, credentials, source dates, role grants, calendars, deployment, data residency, provider processing, spending, backup targets, retention, and recovery objectives remain setup/deployment decisions and must not be guessed.

## 3. Product purpose

Astra is intended to become an evidence-based organizer and extensive project tracker that:

1. Collects only authorized Gmail, Microsoft 365, existing-document, and meeting evidence.
2. Suggests entity/project filing using local matching followed by the selected AI assessor.
3. Lets the owner review, approve, reject, or correct proposals.
4. Preserves original emails and attachment bytes as authoritative evidence.
5. Creates machine-readable derivatives with provenance and quality status.
6. Proposes tasks, owners, deadlines, submissions, approvals, changes, cancellations, and reopenings from locatable evidence.
7. Publishes only owner-approved task text, excerpts, and deliverables.
8. Tracks accountable work, dependencies, schedules, history, reviews, notifications, and recovery without silently inventing facts or commitments.

The initial pilot is local and owner-only. Future shared access requires authenticated, server-enforced authorization and protected storage.

## 4. Approved entities, sources, and storage model

### Entities

- Rupani Foundation USA
- Rupani Foundation Pakistan
- Rupani IB College
- Apex & Co
- Apex Amanat Microfinance
- Ibn Sina Medical College
- Ibn Sina Foundation
- RDI - Global
- RDI Pakistan

`Tax Exempt` remains standalone. `Director Mental Health & Well Being` belongs to RDI Pakistan. Preserve the detailed mappings in the approved context file.

### Approved email-domain allowlist

- `rupanifoundation.org`
- `ibnsinafoundation.org`
- `lowcostleader.com`
- `rupanifoundationpk.org`
- `apexnco.com`
- `rupaniacademy.org`
- `rupanifoundationusa.org`
- `amanataf.org`
- `gbtechive.com`

Domain matching must operate on the actual address domain. It must not use substring matching.

### Storage boundary

- User-selected archive root: `D:\DropBox\Self\Rupani`.
- Astra application code stays separate in this workspace.
- Human archive areas retain original `.eml` messages and original attachment bytes.
- Machine areas may contain thread/email Markdown, derivatives, manifests, catalogs, and evidence references.
- Do not move existing files merely to fit a new hierarchy.
- A cross-entity project has one stable project ID, not duplicated projects or totals.
- The owner chooses the primary filing location; additional scopes use references or approved derivatives.
- Do not use a Dropbox-synced live SQLite database as a shared multi-writer production backend.

## 5. Approved governance and permissions

### App owner

- Organization-wide visibility and final authority.
- Only person with default access to private originals and full derivatives.
- Grants, changes, and revokes follow-up access and delegated powers.
- Final authority for cross-project/entity conflicts and project-level cancellation/reopening.
- Can accept deliverables and close projects.
- Only person who can exceptionally close a project with outstanding work; residual work must remain truthful and visible.
- Only person who enables additional daily-summary recipients.

### Chairman

- Organization-wide project visibility comparable to the owner, but no private-source access.
- Can assign/reassign tasks, change deadlines, accept deliverables, and close an eligible project without outstanding work.
- Owner must receive an audit notification of Chairman actions.
- Cannot grant access, administer credentials, gain private sources, perform exceptional closure, or receive unrestricted cancellation/reopening powers by implication.

### Project manager

- Visibility and management only within explicitly granted scope.
- Can approve routine task plans, pause/resume work, and perform routine task cancellation within granted rules.
- Can accept deliverables when assigned as the authorized manager.
- Prepares project-closure package; does not gain organization-wide or private-source access.

### Representative/member/viewer

- Only the powers explicitly granted by the owner.
- No re-delegation.
- Delegation does not automatically subscribe a person to summaries or expose private sources.

### General authorization rules

- Actual actor and any `on behalf of` relationship remain distinct in history.
- Deactivation/revocation blocks future access and queued privileged actions but preserves history.
- Owner confirms aliases, identity merges, external contributors, and shared-mailbox treatment.
- Shared mailboxes are contacts, not assumed people.
- Never merge identities automatically from names.
- Outside the owner-only pilot, task-owner/approver overlap routes to the owner rather than silently allowing self-acceptance.
- Authorization must cover UI, API, exports, search, downloads, notifications, caches, and raw URLs—not only navigation visibility.

## 6. Approved task and project behavior

### Task ownership and relationships

- One primary accountable owner per task/subtask.
- Collaborators, reviewers, and approvers are separate.
- Parent/subtask and task dependencies must preserve stable identities and history.
- Default dependency type is finish-to-start.
- Detect cycles and show impacts before approved rescheduling.
- Never silently reschedule dependent tasks.

### Lifecycle

- Core work flow: `assigned` -> `in_progress` -> `submitted` -> `completed`.
- `changes_requested` returns work to progress with reason and prior submission history intact.
- Delivery or an attachment is not completion.
- AI may detect or propose a submission, but an authorized person accepts it.
- Acceptance records submitter, submission time, accepting person/time, accepted version or completion note, and applicable checklist.
- Later versions never silently replace an accepted version.
- Reopening requires a recorded reason and reviewed revised timeline. Prior deadlines, completion, and accepted version remain visible.
- New scope normally creates a linked new task rather than rewriting a completed task.
- Distinguish `cancelled`, `abandoned`, `delayed`, `on_hold`, `reopened`, and strategic-priority changes.
- Cancellation requires a confirmed reason; AI cannot invent one.
- On-hold work needs an owner, reason, and mandatory follow-up checkpoint.
- Project closure is a separate event, not inferred from completed subtasks.
- Owner-only exceptional closure preserves a residual-work snapshot and does not silently mark unfinished tasks complete or cancelled.

### Schedule and progress

- Preserve original baseline, current approved plan, and pending proposals separately.
- Every schedule change stores old/new values, actor/time, reason, evidence, and approval.
- Use an explicit governing project calendar and timezone.
- Date-only deadlines run through the end of the governing local day.
- Preserve original source instants and timezones.
- Configure real workweeks and holidays; never infer them from an email domain.
- Effort is estimated hours when known. Unknown effort/availability remains unknown.
- AI weekly plans and durations are proposals, not commitments.
- Report declared progress separately from accepted/total subtasks; do not invent percentages from tone.

### Criticality

- Levels: Critical, High, Normal, Low, plus visibly Unrated where evidence is insufficient.
- Criticality measures consequence, not merely date proximity.
- AI may propose a level with evidence; an authorized manager confirms it, with the owner doing so in the pilot.
- Sort confirmed levels descending, then overdue/nearest date; keep Unrated conspicuous.
- Preserve who changed criticality, old/new value, time, and reason.

## 7. Approved dashboard and notification behavior

### Dashboard

- One front dashboard across all authorized open projects.
- Combinable entity, project, criticality, status, date, and owner filters.
- Show task owner separately from the person whose next action is awaited.
- Include reviews, follow-up checkpoints, on-hold work, undated work, unrated work, closed history, and residual work.
- Do not duplicate totals for cross-entity or multi-project links.
- Rolling calendar-day bands: Overdue, Today, days 1–7, 8–14, and 15–30.
- Cumulative 7/14/30 filters must be labelled and not added together.
- Preserve an `as of` timestamp, display timezone, and source-freshness information.

### Daily summary

- Initially enabled only for the owner.
- Default time: 09:00 in the owner's saved timezone; owner-editable.
- Only owner may enable or disable other recipients.
- Includes overdue work, due today, upcoming bands, reviews, checkpoints, responsibility, criticality, and next action across authorized open projects.
- Disabling the digest does not remove dashboard or independently required event records.

### Event notifications

- Every saved authorized-user task change creates a durable audit/notification record for the owner.
- Actual submissions and material changes do not wait for the daily digest.
- Quiet hours may defer popup display but cannot erase durable records.
- Opening or dismissing a notice is not approval or resolution.
- Retries must be idempotent and track delivery status.
- Automatic outbound email and escalation to additional people are off by default.

## 8. Approved evidence, extraction, AI, and privacy behavior

### Ingestion

- Owner supplies exact accounts, mailbox parameters, history start point, and approved sent/thread behavior.
- Complete pagination and resumable checkpoints are mandatory.
- Show partial, failed, stale, excluded, and pending coverage; exit success alone is not completeness.
- Existing files, minutes, and transcripts are opt-in imports only.
- Preserve source/time/speaker metadata where provided.
- No unrequested recording, mailbox edits, file moves, or deletion.

### Document/source identity

- Separate logical source identity, every receipt/occurrence, document family, content version, rendition, and meaningful reporting period.
- Provider message IDs require provider/account scope.
- Same filename does not prove identity.
- Same bytes are not a new content version, but each occurrence is retained.
- A matching hash alone does not prove identical business meaning.
- Bind assessments to stable IDs/occurrences, not filename alone.
- Preserve accepted/signed versions and primary/additional project references.

### Extraction

- Original bytes remain authoritative.
- Native documents use Microsoft MarkItDown without unnecessary OCR.
- Scanned images/PDF content needing OCR goes through ABBYY thorough recognition first.
- Distinguish complete, partial, empty, OCR-pending, unsupported, encrypted, corrupt, and failed outcomes.
- Preserve extractor/tool/model/version, source hash, run history, and page/cell/passage/time locators.
- Re-extraction creates a new run without losing original or approved links.
- Important financial figures must be checked against originals.
- ABBYY Hot Folder was reported as opening/working, but full app-to-ABBYY-to-MarkItDown integration and numeric fidelity remain unverified.

### AI and learning

- Source text is untrusted data, never an instruction to invoke tools, share information, pay, delete, publish, or change access.
- AI outputs are evidence-backed proposals and uncertainty must remain visible.
- Cite evidence independently for action, owner, date, and status.
- Detect quoted-old requests, duplicate submissions, conflicting dates, cancellations, and reopened work.
- Missing owner/date/reason remains a review item.
- Learn only from attributable human approvals and corrections, with reversal history.
- Automated placements must not train as human confirmations.
- Record model, prompt, extractor, and conversion versions.
- No silent model switch, new provider upload, extra spend, or auto-publication based on confidence.
- Evaluate filing, task extraction, owner, date, status, and missed actions separately on an owner-reviewed sample.

### Publication and privacy

- Only owner sees private originals/full derivatives by default.
- Owner explicitly publishes selected task text, excerpts, or deliverable copies.
- A task/source link must never bypass permissions or expose a full thread implicitly.
- Exports contain only the authorized current view, active filters, and `as of` time.
- Human visibility rules do not automatically authorize sending the same content to an external AI provider.

## 9. Current standalone implementation

### Architecture

- Python 3.11+ standard-library application; no runtime dependencies.
- SQLite with foreign keys, WAL mode, a 30-second busy timeout, and schema version 1.
- `ThreadingHTTPServer` serving a small JSON API and static HTML/CSS/JavaScript.
- PBKDF2-SHA256 password hashing with random salts and 600,000 iterations.
- Random session and CSRF tokens; only token digests are stored for sessions.
- Twelve-hour `HttpOnly`, `SameSite=Strict` session cookie.
- Data defaults to `%LOCALAPPDATA%\AstraProjectTracker`; `ASTRA_HOME` overrides it for tests.

### File map

| File | Current purpose |
| --- | --- |
| `pyproject.toml` | Package metadata, version 0.1.0, `astra` CLI entry point. |
| `README.md` | Current local run and verification instructions. |
| `src/astra/auth.py` | Email normalization, password hashing/verification, session/CSRF token helpers. |
| `src/astra/db.py` | Data directory, SQLite connection, transaction helper, schema version 1. |
| `src/astra/service.py` | Owner/user/project/task permission and business operations; dependencies and audit events. |
| `src/astra/web.py` | HTTP handlers, sessions, CSRF checks, JSON/static responses. |
| `src/astra/__main__.py` | `init-owner` and `serve` commands. |
| `src/astra/static/index.html` | Login, portfolio summary, filters, Gantt, project/task dialogs. |
| `src/astra/static/app.js` | API client, authentication state, filters, dependency selector, Gantt rendering. |
| `src/astra/static/style.css` | Responsive visual styling and blocked-task presentation. |
| `tests/test_core.py` | Core authorization, audit, validation, dependency, and concurrency tests. |
| `tests/test_web.py` | Authentication, CSRF, project/task API, dependency API, and static-shell tests. |
| `tests/run.py` | Self-contained test discovery with the `src` path configured. |
| `tests/ui_fixture_server.py` | Synthetic loopback-only server for manual browser acceptance. |
| `pending-global-mistakes.md` | Astra findings that could not be merged into the canonical global log. |

### Current database tables

- `users`
- `sessions`
- `entities`
- `projects`
- `project_entities`
- `memberships`
- `tasks`
- `task_dependencies`
- `task_events`

Some tables are foundations only: `entities` and `project_entities` have no service/API/UI operations; `projects.manager_user_id` is not used by current business logic.

### Current routes

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/` | Static application shell. |
| GET | `/static/index.html`, `/static/app.js`, `/static/style.css` | Allowlisted static assets. |
| POST | `/api/login` | Authenticates active user and creates session/CSRF tokens. |
| GET | `/api/me` | Current authenticated user and CSRF token. |
| POST | `/api/logout` | Deletes current session and expires cookie. |
| GET | `/api/projects` | Lists role-authorized projects. |
| POST | `/api/projects` | Owner-only project creation. |
| GET | `/api/tasks[?project_id=...]` | Lists authorized tasks, due state, predecessors, and blocked state. |
| POST | `/api/tasks` | Creates a task, optionally with one initial finish-to-start predecessor. |
| POST | `/api/tasks/{id}` | Updates task fields; reasons required for schedule/status changes. |
| GET | `/api/tasks/{id}/events` | Returns append-only task events. |
| GET | `/api/task-dependencies?task_id=...` | Lists incoming/outgoing dependencies visible to the actor. |
| POST | `/api/task-dependencies` | Adds an idempotent project-local finish-to-start dependency. |
| DELETE | `/api/task-dependencies` | Removes a dependency with a mandatory reason. |

POST and DELETE state changes require the session CSRF token except login.

### Implemented and tested behavior

- Single initial owner bootstrap from CLI.
- Owner, Chairman, and member global roles in the database.
- Project-scoped manager/member/viewer memberships in service logic.
- Owner project creation.
- Project visibility isolation for ordinary members.
- Task creation and task updates for owner/Chairman or scoped project manager.
- Task title, date ordering, progress, status, and criticality validation on creation.
- Reasons required for schedule/status changes and special lifecycle statuses on update.
- Append-only task-created and task-updated events with before/after JSON.
- Project-local finish-to-start dependencies.
- Self-link, cross-project, and recursive-cycle prevention.
- Duplicate dependency requests are idempotent.
- Dependency insert/cycle check/audit event share an immediate write transaction.
- Dependency removal requires a reason and is audited.
- A task remains blocked until every predecessor status is `completed`.
- Dependency selection during new-task creation and blocked styling in Gantt.
- Portfolio/project/status/owner filtering in the browser.
- Overdue, today, soon, scheduled, closed, and undated due-state calculation at service level.
- Request-scoped SQLite connections for threaded HTTP handling.
- Login, session, CSRF, content-type, no-store, nosniff, frame, and CSP headers on JSON responses.

## 10. Verification record

Latest verified commands:

```powershell
python tests\run.py
node --check src\astra\static\app.js
```

Latest result: 14 tests passed and JavaScript syntax validation passed.

The test suite currently proves:

- salted password hashing and correct/incorrect verification;
- owner project/task workflow;
- append-only create/update audit snapshots;
- mandatory schedule-change reasons;
- project access isolation;
- viewer task-mutation denial;
- invalid date-range rejection;
- dependency blocking and unblocking;
- dependency add/remove audit records;
- cycle and cross-project dependency rejection;
- concurrent opposite-edge writes cannot create a cycle;
- authenticated HTTP project/task/Gantt-data workflow;
- CSRF rejection;
- dependency HTTP creation and cycle error;
- static application shell loading.

Verification boundaries:

- HTTP tests use synthetic temporary databases only.
- No live user database, private archive, mailbox, OCR tool, external AI service, or notification channel was exercised.
- No backup restore, corrupted database recovery, rate-limit test, session-expiry test, or broad concurrency/load test was performed.
- Browser automation was attempted against a synthetic loopback fixture, but no browser or in-app browser surface was available.
- Therefore the task dialog, dependency selector, responsive layout, Gantt dates, and blocked styling have not received live visual acceptance.
- The fixture server was stopped; `tmp_ui_accept` and generated cache directories were removed.

## 11. Requirement and gap matrix

Status meanings: **Proven** = implemented and covered by current offline tests; **Partial** = some structure/behavior exists; **Missing** = no operative implementation; **Unverified** = implementation may exist but the required live/manual evidence is absent.

| Area | Status | Current evidence or gap |
| --- | --- | --- |
| Owner bootstrap and local login | Proven | CLI, password hashing, sessions, HTTP tests. |
| Chairman global project visibility | Partial | Service rules allow it; no creation/admin UI/API or Chairman-specific action audit notification. |
| Project-scoped membership isolation | Partial | Core view/manage checks tested; no user/grant/revoke UI/API, deactivation flow, or exhaustive endpoint matrix. |
| Entity and cross-entity projects | Missing | Tables exist; no operations, entity filters, primary filing location, or workstream grants. |
| Task creation | Proven within slice | UI/API/service and tests; ownership and lifecycle evidence rules remain incomplete. |
| Task editing | Partial | Service/API exist; no edit interface; blank updated titles are not rejected. |
| Ownership integrity | Partial | User foreign key exists; assignment does not verify project membership or active status. |
| Task audit history | Partial | Events are stored/API-readable; no history UI, schedule-revision model, approval events, or immutable-database protection. |
| Dependencies | Proven within slice | Add/list/remove, cycle/cross-project checks, blocking, concurrency test; UI only adds one predecessor at creation and cannot manage existing links. |
| Parent/subtask behavior | Partial | `parent_task_id` exists and creation enforces same project; no UI, hierarchy view, roll-up, cycle/update policy, or acceptance flow. |
| Lifecycle governance | Partial | Status vocabulary and update reasons exist; no submission records, accepted versions, reviewer/approver separation, reopening cycles, holds/checkpoints, or project closure package. |
| Baseline/current/pending schedules | Missing | Only current start/due fields plus generic before/after events. |
| Project calendar/timezone | Partial | Project timezone column exists; due-state uses server-local `date.today()` and UI parses date strings without governing-calendar logic. |
| Criticality | Partial | Four values plus Unrated and UI filter/display; no evidence-backed proposals, confirmation workflow, change-specific audit UI, or correct approved sorting. |
| Dashboard | Partial | Counts, filters, Gantt shell; no entity filters, open/closed/residual views, review/next-action fields, rolling 7/14/30 bands, or deduplicated cross-links. |
| Gantt visual fidelity | Unverified | Static code and API tested; no live browser acceptance. |
| Daily summary | Missing | No scheduler, settings, recipient control, or 09:00 timezone handling. |
| Durable event notifications | Missing | Task events are not notification inbox/delivery records. |
| Evidence ingestion | Missing | No Gmail/Graph/document/minutes pipeline in this standalone repository. |
| Source/document identity | Missing here | Existing Email Project Organizer has a separate earlier implementation that must be reconciled, not copied blindly. |
| ABBYY/MarkItDown extraction | Missing here / live unverified | Approved routing exists only in design for this tracker. |
| AI task proposals and review | Missing | No model connection, proposal records, locators, confidence/uncertainty, or evaluation. |
| Publication/privacy boundary | Missing | No publication model or protected source-download service. |
| Exports/search | Missing | No export or search endpoints/UI. |
| Backups and recovery | Missing | SQLite WAL is not a tested backup/restore strategy. |
| Production security | Missing | Local development server only; no HTTPS, secure cookie, login throttling, production WSGI/ASGI server, hardened static headers, deployment secrets, or security review. |
| Deployment/persistence | Unverified and unauthorized | No hosting choice, Windows startup task, protected shared storage, or post-reboot verification. |

### Confirmed defects and integrity gaps to fix before staff access

1. `update_task` strips but does not reject a blank replacement title.
2. `owner_user_id` accepts an existing user without verifying that the user is active and belongs to the task's project.
3. Owner/Chairman management checks return true before verifying a project exists; malformed IDs can reach a foreign-key error and become HTTP 500 instead of a controlled 4xx response.
4. Due-state calculation uses the server's local date, not the project's approved governing timezone and end-of-day convention.
5. Static HTML/JS/CSS responses do not currently receive the same CSP and anti-framing headers as JSON responses.
6. There is no login throttling, session revocation interface, expired-session cleanup job, password reset, or secure-cookie mode for HTTPS.
7. Task completion/cancellation/reopening status changes do not yet implement the approved submission, evidence, authority, accepted-version, checkpoint, and schedule-revision records.

Do not broaden these observations into claims of exploitation or actual data leakage; they are source-confirmed implementation gaps in a pre-production local slice.

## 12. Build sequence and next bounded slice

### Approved integrated build sequence

The approved plan predates this standalone tracker and requires:

1. **Phase 0 — Existing I001/release reconciliation:** inspect the current Email Project Organizer, preserve config/backups, reconcile the missing Microsoft profile and schedule-source discrepancy, independently review migration/IDs/manual attribution, run isolated tests/package smoke, and only then reconcile launcher/scheduled executable/release after authorization.
2. **Phase 1 — Reliable source coverage:** Microsoft Graph pagination, bounded backfill/incremental checkpoints, UTC chronology, provider-neutral records, corruption reporting, restart recovery.
3. **Phase 2 — Source/occurrence/version identity:** stable IDs across threads, meaningful periods, versions/renditions, primary/additional references, non-destructive deduplication.
4. **Phase 3 — Trustworthy extraction:** ABBYY/MarkItDown routing, locators, partial/empty states, replayable extraction, numeric checks.
5. **Phase 4 — People and accountable learning:** confirmed aliases, contacts, scoped edits, human-only learning signals, reversals.
6. **Phase 5 — Evidence-backed task extraction pilot:** owner-reviewed task/update/submission/date/cancellation proposals with locatable evidence and measured misses.
7. **Phase 6 — Scoped users, weekly plans, and Gantt:** permissions, calendars, capacity, schedule revisions, My Work, subtasks/dependencies, unified dashboard.
8. **Phase 7 — Controlled automation:** idempotent jobs, notification policies, failure queues, backups/restores, pause/review/reversal, only after measured pilot evidence.

The current standalone tracker implemented an early portion of Phase 6 before Phases 0–5. Treat this as a disclosed sequence divergence, not permission to ignore the source/evidence foundation. Ask the user one focused question only if the next requested work genuinely depends on whether to return to the integrated sequence or continue a standalone UI pilot.

### Recommended next standalone-tracker slice, if the user confirms that path

Build a task detail/edit/history interface with integrity repairs, without adding external integrations:

1. Reject blank task titles on update.
2. Validate project existence before management operations.
3. Require active, project-authorized assignees; add tests for cross-project and inactive assignment.
4. Add a task-detail endpoint if needed rather than overloading list responses.
5. Add an accessible task-detail dialog/page showing title, description, owner, status, criticality, dates, progress, parent, predecessors, blocking tasks, and revision.
6. Allow authorized edits with explicit reason for status/schedule changes.
7. Allow adding and removing multiple dependencies; require a reason for removal and display cycle/cross-project errors clearly.
8. Show the append-only task-event timeline with actor, time, reason, and before/after changes in human-readable form.
9. Keep raw private source fields out; this slice has no evidence publication authority.
10. Preserve CSRF and role checks on every mutation.
11. Add unit, HTTP, authorization, concurrency, and DOM/browser acceptance checks.

Acceptance gate for that slice:

- Blank updates fail without changing the task or event count.
- Nonexistent projects return controlled 404/400 responses, not 500.
- A manager cannot assign a person outside the project or an inactive person.
- Viewer cannot edit, add/remove dependencies, or view data outside granted projects.
- Every accepted edit creates exactly one event; a rejected edit creates none.
- Schedule/status changes require a reason and preserve old/new values.
- Multiple dependencies display correctly; cycles remain impossible under concurrent writes.
- Task detail/history is keyboard-accessible and visually checked in a real browser.
- Existing 14 tests remain green.
- No external data, notification, deployment, or archive mutation occurs.

## 13. Implementation rules for Claude

### Before coding

1. Read the global and project mistakes logs.
2. Read the selected authoritative design sections completely.
3. Inspect current `git status` and all files in the intended slice.
4. Preserve unrelated and untracked user files; the parent repository currently has no established clean commit baseline for this project.
5. Write an atomic requirement checklist distinguishing user requirements, approved design facts, implementation assumptions, and deferred setup decisions.
6. State the bounded slice and what will remain unimplemented.

### While coding

- Use stable IDs; never use a display name/path as identity.
- Keep permission checks in the service/server boundary, not only the UI.
- Use transactions for state changes and their required audit events.
- Keep invariant checks inside the same write transaction when concurrent writers could invalidate them.
- Treat source and imported content as untrusted.
- Do not hide unknown dates, owners, criticality, extraction status, or incomplete coverage.
- Do not auto-close, auto-publish, auto-assign, send messages, or grant access.
- Do not write test fixtures into the real application data directory.
- Do not put credentials or private source content into Markdown, tests, logs, or commits.
- Avoid complex nested PowerShell/Python one-liners; use small reviewable helper scripts.
- Keep original archive files and older application builds untouched.

### Before handoff

1. Re-read the latest user instruction requirement by requirement.
2. Run `python tests\run.py` and `node --check src\astra\static\app.js`.
3. Add focused failure-path and authorization tests for the slice.
4. Run a real browser acceptance pass for changed UI; if unavailable, say so explicitly.
5. Inspect for temporary databases, cache folders, test servers, and generated artifacts; remove only verified task-created temporary items.
6. Confirm no live archive, mailbox, deployment, or external service was touched unless explicitly authorized.
7. Record newly discovered mistakes/omissions promptly and accurately.
8. Report implemented, partial, missing, blocked, and unverified items separately.
9. Never claim full completion or production readiness while any material design area above remains missing.

## 14. Local commands

### Create an environment and install

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
```

### Initialize a real local owner

```powershell
.venv\Scripts\astra init-owner --email owner@example.org
```

The CLI requests the password without echo. Do not put the real address/password into a handoff or test fixture.

### Run locally

```powershell
.venv\Scripts\astra serve --host 127.0.0.1 --port 8765
```

Keep the development server on loopback. Do not expose it to the public internet or Tailscale until deployment/security choices are approved and implemented.

### Verify

```powershell
python tests\run.py
node --check src\astra\static\app.js
```

### Optional synthetic browser fixture

```powershell
python tests\ui_fixture_server.py
```

Then open `http://127.0.0.1:8766` and use only the fixture credentials declared in that helper. Stop the server and delete only the verified `tmp_ui_accept` fixture directory afterward.

## 15. Decisions requiring explicit user input or approval

Do not guess these values or treat design approval as operational authorization:

- Whether the next build returns to integrated Phase 0 or intentionally continues the standalone tracker first.
- Intended Microsoft account profiles and scheduled-source selection in the existing organizer.
- Real people, aliases, external contributors, role grants, representatives, and project memberships.
- Actual entity calendars, working days, holidays, timezones, capacity, and folder mappings.
- Mailbox identities, credentials, source-history dates, sent/thread rules, and pause/resume choices.
- Existing-document, minutes, and transcript ingestion scope.
- Hosting, authentication provider, HTTPS termination, data residency, and protected storage.
- AI-provider data handling, selected model, prompt/version policy, and spending limits.
- Backup destination, retention, recovery-point objective, recovery-time objective, and restoration procedure.
- Notification channel, any additional recipients, external email delivery, and escalation rules.
- Numeric OCR/evidence tolerances and pilot acceptance thresholds.
- Any automatic publication, assignment, closure, outbound reminder, escalation, or other consequential action.

Ask only the one decision needed for the next bounded step. Do not reopen settled baseline design decisions.

## 16. Mistakes and prevention record

Read `pending-global-mistakes.md` for full evidence. Key Astra lessons are:

- The initial bootstrap patch was temporarily created in the archive workspace; verify exact target paths after every patch and never mix code with `D:\DropBox\Self\Rupani\_machine`.
- A threaded HTTP server cannot reuse a main-thread SQLite connection; current handlers use one connection per request.
- Test discovery in a `src` layout needs an installed package or explicit path; use `tests/run.py`.
- Do not describe a database table as delivered functionality without an operable service/API/UI path and tests.
- Dependency graph validation must share the immediate transaction with insertion to prevent concurrent invariant failure.
- Large combined reads truncate evidence; use targeted bounded reads.
- Nested shell/JavaScript/Python quoting produced repeated command errors; use helper files.
- One apparent character-encoding defect was only a display-path artifact; confirm stored source before claiming corruption.
- No browser surface was available for the latest visual check; retain the limitation until an actual browser pass succeeds.
- The handoff audit identified the sequence divergence and the open authorization, lifecycle, timezone, security, ingestion, and recovery gaps listed above.

The canonical global log is outside this workspace's current write boundary. Preserve `pending-global-mistakes.md` until a future authorized session can merge it narrowly without overwriting other projects' entries.

## 17. Definition of eventual product completion

Astra is not complete merely when the tracker UI looks polished or the current tests pass. A credible completion claim requires, at minimum:

- all approved roles and scope boundaries enforced across every interface;
- stable entity/project/person/source/version/task identities and history;
- complete, resumable, provider-neutral authorized ingestion with visible coverage;
- verified ABBYY/MarkItDown extraction, locators, and quality states;
- owner-reviewed evidence-backed task proposal workflow with measured misses and false positives;
- approved lifecycle, schedule-revision, dependency, calendar, capacity, dashboard, summary, and notification behavior;
- explicit publication/privacy controls and authorized exports;
- idempotent jobs, failure queues, pause/reversal, backup, and demonstrated restore;
- security review and approved production hosting/authentication/storage;
- unit, integration, authorization, concurrency, recovery, accessibility, and real-browser validation;
- setup/deployment decisions supplied and approved by the user;
- no unresolved hard failure hidden behind an average test or quality score.

Until those conditions are met, report progress by bounded slice and preserve the distinction between structural/offline evidence and live operational proof.
