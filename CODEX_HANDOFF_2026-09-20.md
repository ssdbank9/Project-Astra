# Astra complete decisions, runtime and sharing handoff — 2026-09-20

- Prepared for: Aly Jafferani, Codex, Claude and the next implementation agent
- Workspace: `C:\Users\Aly Jafferani\Documents\ChatGPT\New project\astra_project_tracker`
- Parent Git repository: `C:\Users\Aly Jafferani\Documents\ChatGPT\New project`
- Application version: `0.1.0`
- Database schema: `v11`
- Verified commit before this handoff: `e04e712ba3a7d81cf926adfab65ca07f9105ab16`
- Handoff ticket: `MTEDTM`
- Verification date: 2026-09-20, Asia/Karachi
- Production status: not deployed and not approved for real-user access

## 1. Executive handoff

Astra will be a hosted, standalone project-management application used through a
web browser. The frontend remains native HTML, CSS and JavaScript. The backend is
Python with server-enforced authorization and a versioned database. Users will not
receive the source code or a copy of the database; they will receive an Astra
account and the approved application URL.

The Owner selected a zero-dollar public-HTTPS pilot on 2026-09-20:

1. **Oracle Always Free VM:** the shared Astra service runs in the owner's OCI
   tenancy within current Always Free limits.
2. **Free public hostname:** a selected `*.duckdns.org` name points to the VM.
3. **HTTPS:** Caddy terminates public HTTPS and proxies only to Astra on loopback.
4. **User access:** users open the HTTPS URL in a normal browser and sign in with
   separate Astra accounts. They do not install Tailscale and never use the
   Owner's Oracle, DuckDNS, Tailscale or Astra identity.
5. **Cost ceiling:** the pilot must remain at zero direct service cost. Capacity,
   storage and backup use must fail safely or alert before a free allowance is
   exceeded; nothing may silently upgrade to a paid resource.

A private server or always-on desktop remains a recovery/development host, not
the selected normal user-access route. A future host change must not change task
IDs, file permissions, audit history or user behavior. Private mailbox/document
collection and source processing stay on the owner's machine; only approved
structured tasks, excerpts and published outputs reach the shared server.

The current program is still a local development server. It has a substantial
tested tracker, but it is not safe to expose directly to the internet. Production
development must add a hardened service runtime, HTTPS, secrets/configuration,
backup and demonstrated restore, first-login/password recovery, monitoring and a
deployment security review before any real users are invited.

## 2. What this handoff controls

This is the current cumulative handoff. It adds the decisions made on 2026-09-19
and 2026-09-20 to the earlier product and implementation record. It does not erase
the detailed documents it points to.

Apply sources in this order:

1. The user's newest explicit instruction.
2. The active `AGENTS.md` instructions and Jaira lane rules.
3. `C:\Users\Aly Jafferani\.codex\mistakes.md` and the pending workspace additions.
4. This handoff for current implementation, decisions, runtime and sharing.
5. `docs/design/astra-product-ux-baseline.md` for product surfaces and UX rules.
6. `docs/design/governed-drag-drop-contract.md` for every drag, bulk, lock, file
   and schedule-mutation rule.
7. `docs/research/monday-trello-workflow-ux-research.md` and
   `docs/research/asana-ux-and-design-tools.md` for external research and its
   evidence limits.
8. `CLAUDE_HANDOFF.md` for the original evidence, lifecycle, entity and privacy
   baseline. Its 14-test implementation snapshot is obsolete.
9. `email_project_organizer/FINAL_DESIGN.md`, `ASTRA_PLAN_AND_CONTEXT.md` and
   `design-decisions.md` for the approved integrated evidence-organizer design.
10. Current code and tests as proof of what exists, not authority to override a
    later decision.

`CODEX_HANDOFF_2026-09-19.md` remains a historical queue snapshot. Its claims
about ticket counts, review order, claims and unverified browser availability must
be refreshed from Jaira before use.

## 3. Verified current baseline

### 3.1 Verification completed for this handoff

From `astra_project_tracker`:

```powershell
.venv\Scripts\python.exe tests\run.py
node --check src\astra\static\app.js
```

Result on 2026-09-20:

- 102 Python unit/HTTP integration tests passed in 49.502 seconds;
- JavaScript syntax validation passed;
- no live database, private archive, mailbox, external AI provider, email channel
  or deployment host was touched;
- this verification does not prove production security, real-browser behavior,
  backup restore, sustained multi-user load or every supported device.

### 3.2 Current application architecture

- Python 3.11+ package with one Windows-only runtime dependency on `tzdata`.
- Native HTML/CSS/JavaScript browser interface.
- `ThreadingHTTPServer` development HTTP service.
- SQLite database with foreign keys, WAL, busy timeout and migrations through
  schema version 11.
- PBKDF2-SHA256 password hashing, random sessions and CSRF tokens.
- Twelve-hour `HttpOnly`, `SameSite=Strict` session cookie; `Secure` is enabled
  only when `ASTRA_SECURE_COOKIES=1`.
- Application data defaults to `%LOCALAPPDATA%\AstraProjectTracker`; `ASTRA_HOME`
  overrides it for isolated tests and future deployment configuration.

The live SQLite database must stay on a local server disk or attached block
volume. It must not be used as a multi-writer database inside Dropbox, OneDrive or
another file-sync folder.

### 3.3 Implemented and covered by the current suite

- owner bootstrap and authenticated sessions;
- login throttling, session cleanup and sign-out-everywhere;
- Owner, Chairman and project-scoped Manager/Member/Viewer foundations;
- owner People panel, account activation/deactivation and project grants;
- projects, entities, cross-entity filing, budgets and portfolio roll-ups;
- tasks, accountable owner, dates, criticality, progress and next action;
- task details, parent/subtasks, direct-child roll-up and cycle protection;
- project-local finish-to-start dependencies, cycle prevention and blocking;
- critical-path calculation in the current dependency network;
- schedule baselines, current dates and proposed schedule revisions;
- submission, changes requested, acceptance, reopening and governed closure;
- project working days, holidays and governing timezone;
- task/project templates, suggested owners and structural reset rules;
- path/link attachment records, explicit final-result marking and authorization;
- append-only task/project events and durable in-app owner notifications;
- portfolio/project Gantt, task sorting, search and scoped exports;
- CSRF enforcement and representative scope-isolation checks.

### 3.4 Approved or prototyped, but not production-implemented

- the A-hybrid Command Center visual system;
- the complete List/Board/Timeline/Activity workspace shell;
- governed Kanban drag and reorder;
- Gantt drag/resize with downstream impact preview;
- four dependency types, lag/overlap editing and full interactive connectors;
- private What-if scheduling and apply/approval workflow;
- cross-project task/file Move, Copy and Link;
- bulk drag operations and renewable manipulation locks;
- managed file upload, folder queues, hashing, versions and storage adapters;
- Automation Center, rule drafts, test runs, health and kill switch;
- My Work, private Capture and the split Needs action/Activity inbox;
- capacity/effort Workload;
- final low-data/offline behavior and the mobile-specific interaction set;
- production hosting, HTTPS, service supervision, monitoring and restore.

### 3.5 Missing gates before real-user sharing

- reconcile two confirmed authorization mismatches with the latest decisions:
  current `can_manage_project` gives Chairman broad mutation/acceptance/closure
  powers, and current attachment/final-result methods still allow project managers
  to add attachment links or mark/unmark final results; the approved target makes
  protected lifecycle and every file/final-result mutation Owner-only;
- production-capable HTTP runtime or an explicit security justification for the
  chosen runtime;
- forced password change on first login and an owner-controlled recovery/reset
  process;
- HTTPS and secure-cookie deployment proof;
- secrets and environment configuration outside the repository;
- automated, encrypted, off-host backups and a demonstrated restoration;
- request/body/upload limits, security headers on every response and an endpoint
  authorization matrix;
- storage adapter and download authorization for actual managed files;
- health checks, logs, disk/backup monitoring and incident procedure;
- real-browser, mobile, accessibility and low-bandwidth acceptance;
- multi-user concurrency/load testing and deployment rollback;
- an approved host, domain, data location, backup destination and recovery goals.

## 4. Product and data-boundary decisions

### 4.1 Standalone application

- Astra has its own database, login, deployment lifecycle and authorization
  boundary.
- It is not a dashboard bolted onto the Email Project Organizer.
- The shared application contains authorized project/task information and
  published outputs, not unrestricted private source archives.
- A user sees only the projects and records authorized for that account.

### 4.2 Private-source boundary

- Mailbox collection, document matching, OCR and private-source assessment remain
  on the owner's machine by default.
- Original `.eml` files and original attachment bytes remain authoritative.
- Only Aly Jafferani sees private originals and full derivatives by default.
- The owner explicitly publishes selected task text, excerpts or deliverable
  copies to shared Astra.
- A task/source link must never bypass authorization or expose an entire thread.
- External AI processing requires a separately approved provider, scope, data
  handling policy, model/version and spending rule.

### 4.3 Identity and evidence

- Use stable IDs for people, projects, tasks, sources, occurrences, versions and
  renditions. Names, filenames and paths are display data, not identity.
- Preserve every receipt/occurrence even when bytes are identical.
- Same filename does not prove identity; matching hashes do not prove identical
  business meaning.
- Extraction states distinguish complete, partial, empty, OCR pending,
  unsupported, encrypted, corrupt and failed.
- AI outputs remain evidence-backed proposals. Unknown owner, date, reason,
  criticality or coverage remains visible as unknown.
- Automated placement never trains as human confirmation.
- External AI is disabled for the initial production release. A future assessor
  must be zero-cost, provider-swappable and preferably local on the Owner's
  desktop. No private content may be sent to any external provider without a
  separate explicit Owner authorization covering that provider and its terms.

## 5. Final authority and role decisions

The App Owner is **Aly Jafferani**.

| Capability | App Owner | Project Manager | Viewer/member |
| --- | --- | --- | --- |
| Organization-wide view | Yes | Granted projects | Granted projects |
| Configure workflows, statuses, WIP limits and completion rules | Yes | No | No |
| Move ordinary work through the configured project flow | Yes | Yes | No |
| Accept/reject review, complete, close, reopen or override requirements | Yes | Request only | No |
| Change ordinary project-local dependencies | Yes | Yes, when no protected impact | No |
| Affect critical path, milestone or project completion | Yes | Request only | No |
| Move, copy or link tasks/files across projects | Yes | No | No |
| Manage files, folders, links, versions and final-result publication | Yes | No | No |
| Open/download authorized files | Yes | Yes | Yes |
| Publish templates or automations | Yes | No | No |
| Force-unlock work | Yes | No | No |
| Grant/revoke access or administer credentials | Yes | No | No |

The older implementation includes a Chairman role with broader mutation powers.
The latest Owner-only protected-action decision is authoritative for the target
experience. Before deployment, reconcile Chairman behavior in code and tests so
it cannot bypass the table above. Until that reconciliation is complete, do not
grant a real Chairman account.

Authorization is enforced at the server/service boundary across UI, API, search,
exports, downloads, notifications, raw URLs, automation and offline replay. Hiding
a control is usability, not security.

Actual actor and any `on behalf of` relationship remain distinct in history.
Revocation blocks future access and privileged queued work while preserving
historical attribution.

## 6. Task, schedule and lifecycle decisions

### 6.1 Ownership and hierarchy

- One primary accountable owner per task/subtask.
- Collaborators, reviewers and approvers remain separate.
- Parent/subtask relationships preserve stable IDs and history.
- Roll-up reports accepted/completed direct children versus total separately from
  declared task progress; it does not invent a percentage.

### 6.2 Working flow

The approved visible workflow is configurable by the Owner, with the recommended
ordinary path:

`Draft → Ready → In progress → Blocked → Submitted for review`

Managers may operate within those ordinary stages. Acceptance/rejection,
completion, closure, reopening and requirement override remain protected Owner
actions. A Manager's protected attempt creates one visible request and leaves the
accepted live state unchanged.

The current code uses service states such as `assigned`, `in_progress`,
`submitted` and `completed`. Production implementation must create one tested
migration/presentation mapping; it must not leave parallel status meanings.

Delivery or attachment is not completion. Submission and acceptance are distinct.
Accepted versions are immutable; reopening records a reason and a revised
timeline while preserving prior deadlines, completion and accepted evidence.

Cancellation, abandonment, delay, on hold and reopening remain distinct. On-hold
work requires owner, reason and follow-up checkpoint. Project closure is a
separate event; exceptional closure is Owner-only and preserves residual work.

### 6.3 Dates, calendars and criticality

- Preserve original baseline, current approved plan and pending proposal.
- Schedule changes store old/new values, actor/time, reason, evidence and approval.
- Date-only deadlines end in the project's governing local day.
- Workweeks and holidays are configured, not inferred.
- Effort and availability stay unknown until supplied.
- Criticality is Critical, High, Normal, Low or visibly Unrated.
- Criticality means consequence, not merely urgency; changes record actor, old,
  new and reason.
- Users can sort by criticality or due date. Confirmed criticality order is
  Critical → High → Normal → Low, then nearest due date; Unrated stays visible.

### 6.4 Entity attribution and budgets

- A multi-entity project without a selected primary entity stays in a visible
  **Unassigned** bucket. Astra never attributes it to the first-listed entity.
- The production budget model includes planned, committed and actual/spent
  amounts with explicit variance. Currency amounts are never silently blended.
- Unassigned work remains visible in portfolio totals but is not attributed to a
  named entity until the Owner selects the primary entity.

## 7. UX and workflow direction

### 7.1 Visual direction

Astra uses the approved **A-hybrid Command Center**:

- Command Center operational density and persistent context;
- Focus Workspace typography and progressive disclosure;
- Executive Cockpit compact portfolio-health strip;
- native HTML/CSS/JavaScript UI;
- decisive, polished buttons, panels, dialogs and feedback without decorative
  clutter or distracting motion.

The app must feel immediately understandable like a strong Trello board and grow
into Monday-style multi-view planning without copying either product's branding,
trade dress, terminology or broad permission model.

### 7.2 Information architecture

Permanent navigation:

1. Home — portfolio Command Center.
2. My Work — assigned work and personal planning.
3. Inbox — Needs action and Activity.
4. Projects — authorized project workspaces.
5. Capture — private quick capture.

Owner administration sits under one Manage area: approvals/governance, people and
access, workflows/templates, Automation Center, managed files/storage, audit and
system health.

Project views share one task record:

- Overview;
- List;
- Board;
- Timeline;
- Activity.

A click opens a task drawer for routine work; a stable full-page URL supports deep
review, schedule, approvals, files and audit history.

### 7.3 Command Center and notifications

Home is exception-led. It prioritizes overdue, blocked, awaiting Owner, near due,
critical-path exposure, over-capacity people and failed automation/sync.

Keep these concepts separate:

- My Work — assigned work;
- Needs action — approvals, reviews, conflicts and failures;
- Activity — watched and subscribed updates;
- Capture — private intake not yet filed into a project.

Reading or dismissing a notification is never approval.

The Owner receives real-time alerts for critical-path/project-completion changes,
milestone moves, final-result effects, permanent-link changes, consequential
blocked/unauthorized attempts and large cross-project moves made or attempted by
other users. Every blocked or unauthorized attempt by another user, including
attachment removal, notifies the Owner.

The Owner is not self-notified for their own successful actions; those actions
remain fully audited. Routine ordering, small date moves and ordinary successful
operations appear in an in-app daily digest at 09:00 in the Owner's timezone.
The digest is Owner-only. Automatic outbound email, additional recipients and
escalation are off for the initial release.

## 8. Governed drag, bulk and concurrency decisions

All mutation surfaces use one server mutation seam equivalent to:

```text
preview(actor, intent, expected_versions) -> Preview
commit(actor, preview_token, confirmations) -> Outcome
cancel(actor, preview_token) -> Cancelled
restore(actor, audit_event_id) -> Preview | Outcome
```

Every operation follows Select → Begin → Preview → Confirm/Propose → Revalidate →
Atomic commit → Feedback/recovery.

### 8.1 Board

- Drag within a column changes priority/order.
- Drag across columns changes status only when the configured transition, role,
  dependency, WIP and evidence rules allow it.
- Invalid drops return with a precise reason.
- Protected drops create Owner requests and do not change live status.
- Ordinary successful drops have 15-second Undo plus permanent audited restore.
- Every action has a keyboard/menu equivalent.

### 8.2 Timeline, dependencies and critical path

- Ordinary authorized tasks may move/resize with ghost dates and Undo.
- Dependency, milestone, critical-path or completion effects open an impact panel.
- Managers propose protected impact; Owner may confirm.
- Dependency creation defaults to finish-to-start, followed by a selector for
  finish-to-start, start-to-start, finish-to-finish, start-to-finish and permitted
  lag/overlap.
- Reject cycles, impossible schedules and unauthorized cross-project links.
- Cross-project dependencies are Owner-only and connect only approved milestones,
  deliverables or interface tasks.
- Critical-path mode includes accessible text/icon/pattern cues and slack.
- Private What-if mode never changes live dates. It can be discarded, saved as a
  proposal or submitted for approval.

### 8.3 Cross-project and bulk

- Only the Owner may Move, Copy or Link a task or file across projects.
- Cross-project drops show impact on access, ownership, dates, dependencies,
  attachments, storage, notifications and portfolio timing.
- Bulk selection obtains all required renewable leases together; if any lock is
  unavailable, nothing starts.
- Bulk mutation is atomic with one parent audit event plus item details.
- Task selection alone does not lock work.
- Leases renew during active manipulation, expire after interruption and show the
  holder/expected expiry. Owner force-unlock is warned and audited.

## 9. File and final-result decisions

All file management is Owner-only. Managers and Viewers may open or download only
files authorized for their project.

- Default per-file maximum: 25MB.
- Owner-configurable per-file maximum: up to an absolute 250MB ceiling.
- Folder or multi-file batch: fixed 250MB total ceiling.
- Preserve hierarchy as Astra virtual folders; never expose original local paths.
- Validate each file's extension, MIME and signature.
- Hash content; identical content is reused rather than uploaded again.
- Same name with different bytes offers New version (default), Separate file or
  Cancel.
- Versions are immutable with uploader, date, size and verification metadata.
- A new version cannot silently replace a marked final result.
- Queue shows progress and supports pause, cancel, retry and per-file rejection.
- Cross-project file placement offers Move / Copy / Link, with Link as default,
  and remains Owner-only.
- Permanent direct links are off by default, Owner-created, revocable, audited and
  notified.
- Accepted submissions and attachments enter the Final Results repository only
  through an explicit manual Owner mark; acceptance alone does not auto-publish.

Production storage may be Oracle Object Storage or a protected private-server
filesystem. Use one managed-file interface so the storage backend can change
without changing permission semantics.

## 10. Mobile, accessibility and low-bandwidth decisions

### Mobile

- Desktop uses direct drag.
- Tablet uses deliberate long-press drag with highlighted targets and optional
  haptics.
- Small phones use action sheets and date controls rather than precision drag.
- Home becomes an exception list; Timeline becomes an agenda/schedule table; task
  detail becomes full-screen.
- Approve/reject always opens consequence/reason review; never bind it to swipe.

### Accessibility

- WCAG 2.2 AA is the production target.
- Every pointer action has keyboard, menu and structured-form alternatives.
- Board and Gantt always have List/schedule-table equivalents.
- Preserve focus after movement and drawer/dialog close.
- Provide visible focus, skip links, semantic landmarks and live announcements.
- Allow reduced motion and disabling single-key shortcuts.
- Status/risk/criticality never rely on color alone.

### Low-data mode

- Load shell, navigation, text records and actions first.
- Defer charts, avatars, images, previews and long history.
- Paginate/virtualize large lists without breaking accessible order.
- Explicitly show Offline, Syncing, Pending, Confirmed and Failed.
- Queue only safe drafts and ordinary edits offline.
- Protected transitions, permissions, files, cross-project actions and automation
  publication require an online server decision.
- Stream large files with bounded concurrency and resumable queue state.

## 11. How Astra runs today

Current local use is for development and owner-only testing:

```powershell
cd "C:\Users\Aly Jafferani\Documents\ChatGPT\New project\astra_project_tracker"
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\astra.exe init-owner --email owner@example.org
.venv\Scripts\astra.exe serve --host 127.0.0.1 --port 8765
```

The owner password is requested without echo. Open `http://127.0.0.1:8765` on the
same machine.

Current limitations:

- `127.0.0.1` is reachable only from that computer;
- this is plain HTTP and the current server is a development runtime;
- no automatic startup, health monitoring or restore exists;
- no forced first-login password change or password recovery exists;
- real users must not be added and the port must not be exposed publicly.

## 12. Recommended production runtime

The target request path is:

```text
User browser
    -> HTTPS gateway / reverse proxy
        -> Astra service on loopback or private interface
            -> versioned SQLite on local block storage (initial scale)
            -> managed file storage adapter
            -> append-only audit and notification records
```

The private evidence path stays separate:

```text
Owner desktop collector
    -> local mailbox/document/OCR/AI proposal pipeline
        -> owner review and publication decision
            -> approved structured task/excerpt/output only
                -> shared Astra service
```

Production requirements:

- run Astra as a supervised service account with the least filesystem access;
- bind the application service to loopback/private interface, not the public IP;
- terminate HTTPS at Caddy, Nginx or an equivalently reviewed gateway;
- set `ASTRA_SECURE_COOKIES=1` behind HTTPS;
- persist database, managed files, gateway state and logs on controlled storage;
- rotate logs and alert on downtime, disk pressure, repeated errors and backup
  failure;
- perform database-consistent encrypted backups and test a full restore;
- deploy updates through a reversible migration/rollback procedure;
- keep secrets out of Git, Markdown, logs and command history.

Caddy is a good default candidate because its official documentation supports
reverse proxying a loopback backend and automatic certificate acquisition/renewal
for a public DNS name. It is a recommendation, not an installed component.

Official references:

- `https://caddyserver.com/docs/quick-starts/reverse-proxy`
- `https://caddyserver.com/docs/automatic-https`

## 13. Hosting option A — Oracle Cloud VM

### User experience

- Users open the selected free address such as
  `https://astra-projects.duckdns.org` in any modern browser.
- No VPN client is required.
- Astra login and project permissions determine what each person sees.
- The VM stays available independently of the owner's desktop, subject to Oracle
  service, tenancy and resource conditions.

### Server layout

- Oracle Linux or Ubuntu VM in the owner's OCI tenancy.
- Only HTTPS 443 is publicly available; HTTP 80 may redirect/perform certificate
  validation.
- SSH is key-based and restricted to the owner's administrative source/network.
- Caddy/reverse proxy faces users; Astra listens only on loopback.
- SQLite sits on VM block storage for the initial small deployment.
- Managed files use OCI Object Storage or a protected server filesystem through
  the same authorization adapter.
- Encrypted backups go off the VM to a separately protected target.

### Current Oracle Free Tier facts and risk

Oracle currently documents Always Free compute resources in the tenancy's home
region, but it also warns that capacity can be unavailable and that idle Always
Free compute instances may be reclaimed. The documented idle criteria include
low CPU and network use over a seven-day period, plus low memory use for A1
shapes. Therefore:

- do not treat “free” as an uptime guarantee;
- monitor host health and tenancy notices;
- keep tested off-host backups;
- retain the private-server option as a recovery path;
- confirm the chosen shape/region and current tenancy limits at deployment time.

Official reference:
`https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm`

## 14. Hosting option B — private server or always-on desktop

This profile is retained only for local development and disaster recovery. It is
not the selected normal user-access route. Ordinary users will not be required to
install or sign into Tailscale. Publishing a desktop-hosted recovery instance to
users would require a separate security review and explicit Owner authorization.

### Historical private-access behavior — not selected

- Users install/sign into Tailscale or another approved private-access client.
- The owner invites them to the tailnet or shares only the Astra machine.
- They open the private Astra hostname in their browser and then sign into Astra.
- Tailscale controls network reachability; Astra still controls application data.

Tailscale's current documentation says a specific machine can be shared with an
external user without exposing it to the public internet; access remains subject
to access-control policies, and recipients accept the share using their own
Tailscale account. This reduces public attack surface but adds client onboarding.

Official references:

- `https://tailscale.com/kb/1084/sharing`
- `https://tailscale.com/docs/reference/inviting-vs-sharing`

### Host requirements

- always powered, awake and connected;
- automatic service restart after reboot;
- encrypted disk and restricted local login;
- Tailscale ACLs limited to the Astra service, not the entire home/office network;
- Astra service bound to loopback/private interface;
- HTTPS through an approved private certificate/Tailscale/Caddy arrangement;
- database and file storage on a non-synchronized local disk;
- encrypted off-machine backups and a tested restore.

If the host sleeps, loses power or loses internet, the app becomes unavailable.
The Owner's desktop is therefore a recovery/development host, not the normal
zero-dollar public pilot.

## 15. How to share Astra with other people

### 15.1 Owner onboarding workflow

1. Confirm the selected Oracle service and free DuckDNS HTTPS URL are healthy.
2. Create the person's individual Astra account in the Owner-only People panel.
3. Assign the minimum global role and explicit project memberships.
4. Supply a unique temporary password through a separate secure channel.
5. Send only the approved Astra HTTPS URL; no Tailscale invitation is required.
6. Require password change at first login once that feature is implemented.
7. Ask the user to verify their display name, projects and role before work.
8. Review the audit trail and access periodically.
9. Deactivate the account and revoke sessions/network access when access ends.

Each person receives a separate Astra account. The Owner's Oracle, DuckDNS and
Astra identities are never shared.

### 15.2 What the user can do

- sign in through a browser;
- see only authorized projects/tasks/files;
- use the actions permitted by Owner/Manager/Viewer role;
- receive in-app action requests and activity;
- open authorized published files;
- submit or propose protected work where permitted;
- never obtain server, database, archive or private-source access merely because
  they can use the web application.

### 15.3 What must be built before invitations

- forced first-login password change;
- owner password reset/recovery with audit and session revocation;
- production HTTPS, secure cookies and hardened response limits/headers;
- completed authority reconciliation, especially Chairman behavior;
- endpoint authorization regression suite;
- backup/restore and incident procedure;
- browser/mobile/accessibility acceptance;
- deployment health monitoring;
- privacy notice and owner-approved account/access roster.

The current Owner panel can create users with temporary passwords, but sharing is
not approved until these gates pass.

## 16. Backups, recovery and continuity

The Owner accepted this zero-dollar pilot policy on 2026-09-20:

- nightly encrypted, SQLite-consistent backup to OCI Object Storage while total
  use remains within the current free allowance;
- an encrypted recovery copy on the Owner's desktop, separate from the VM;
- recovery-point objective (RPO): no more than 24 hours of accepted work;
- recovery-time objective (RTO): target restoration within four hours;
- retention: 7 daily, 4 weekly and 3 monthly recovery points, automatically
  pruned without exceeding the free-storage ceiling;
- only the App Owner holds or controls restoration credentials;
- Oracle-to-desktop recovery and desktop-to-new-Oracle restoration must both be
  documented and exercised before real-user go-live.

Minimum technical design:

- quiesced/SQLite-consistent database snapshot rather than copying a live main
  file while ignoring WAL state;
- matching managed-file/object manifest;
- encryption in transit and at rest;
- daily automated backup plus a more frequent schedule if the chosen RPO requires;
- at least one off-host/off-account copy;
- checksum/inventory and restore logs;
- periodic full restore into an isolated environment;
- documented cutover and rollback with DNS/private-host changes.

No deployment is complete until a restoration has actually succeeded.

## 17. Open setup values — obtain when needed

The product and policy decisions above are settled. These operational values are
not product-design decisions and still require the Owner when they become
necessary:

- exact free DuckDNS hostname;
- OCI home region and an actually available Always Free VM shape;
- final Ubuntu LTS version and free storage allocation;
- data residency and geographic restrictions;
- real users, roles, project memberships and external contributors;
- real project timezones, workweeks, holidays, capacity and folder mappings;
- mailbox/source identities, history dates and ingestion scope;
- password reset delivery channel and identity-verification procedure;
- whether permanent attachment links will ever be enabled for external recipients.

Ask only the one decision required for the next bounded implementation step.

## 18. Implementation sequence from this handoff

### Gate 0 — close the design and board gates

- Owner accepts or sends back the three human-lane design tickets:
  `JQY55P`, `AX572Q` and `Z9JCZ6`.
- Refresh all review/signoff ticket states from Jaira; do not trust the older queue
  snapshot.
- Resolve/review the attachment, final-result, critical-path, template and schedule
  tickets that affect the new shell.
- Drive authorization-reconciliation ticket `HS3JRY` before any real-user access;
  it covers Chairman, Manager, protected lifecycle, files and final results.

### Gate 1 — production runtime and recovery foundation

- choose the first deployment profile only when its implementation is ready;
- add configuration/secrets boundary and service supervision;
- add first-login/password reset/recovery;
- add complete security headers, request limits and authorization tests;
- implement database/file backup and prove restore;
- document and test upgrade/rollback.

### Gate 2 — shared product shell

- semantic design tokens and A-hybrid shell;
- List as the dense accessible source-of-truth view;
- task drawer/full page and common loading/empty/error/offline states;
- Home exception strip and action-driven panels.

### Gate 3 — governed Board and approvals

- Owner workflow configuration and versioning;
- legal destination preview and Manager/Viewer policy;
- protected-drop request behavior;
- keyboard/touch Move alternatives;
- locks, audit and Undo.

### Gate 4 — Timeline, dependencies and What-if

- unscheduled tray and schedule table;
- drag/resize preview;
- dependency types/lag, critical path and slack;
- private What-if and Owner apply/approval;
- governed cross-project interfaces.

### Gate 5 — workload, automation, templates and notifications

- effort/capacity Workload;
- Automation Center with test/publish/health/disable;
- Owner-published template previews;
- My Work, Capture, Needs action and Activity;
- daily digest only after its channel/recipient/host decisions.

### Gate 6 — managed files

- storage adapter, upload queue, validation, hashing and versions;
- final-result safeguards and permanent-link policy;
- Owner-only mutation across every path;
- 25MB default / 250MB per-file ceiling / 250MB batch enforcement;
- authorized streaming downloads and backup manifest.

### Gate 7 — deployment pilot and acceptance

- deploy to the chosen pilot host;
- create synthetic users and projects, not real private data;
- run security, concurrency, migration, backup/restore, browser, mobile,
  accessibility and low-bandwidth acceptance;
- owner approves go-live roster and data migration;
- then invite the smallest real user group and monitor closely.

Private evidence ingestion/AI remains a separate owner-machine workstream and must
not be pulled onto the shared host merely because the UI is ready.

## 19. Production go-live gate

Do not call Astra production-ready until all are Proven:

- authority matrix enforced on UI, API, download, export, search, automation and
  offline paths;
- current database migrations and rollback verified on a copy;
- HTTPS, secure cookies, secrets, headers, request limits and login controls;
- account onboarding, forced password change, reset, deactivation and revocation;
- encrypted backup plus successful isolated restore;
- managed-file authorization and storage recovery;
- monitoring, log retention, disk alerts and incident contacts;
- real-browser desktop/tablet/phone acceptance;
- keyboard, screen-reader, zoom, reduced-motion and low-data acceptance;
- multi-user contention, leases and atomic mutation tests;
- no private archive/source material present on the shared host unless explicitly
  published;
- owner-approved host, domain, roster, roles, backup policy and go-live decision.

Passing 102 offline tests is necessary but is not this production gate.

## 20. Current Jaira snapshot

This snapshot is time-sensitive. Always run:

```powershell
jaira next --per-lane --json
jaira resume
```

At preparation time:

- human: shell direction `JQY55P`, governed drag prototype `AX572Q`, researched UX
  baseline `Z9JCZ6`, and this handoff ticket. The Owner accepted the recommended
  decision package in conversation on 2026-09-20; lane movement remains human;
- signoff: six implementation tickets awaiting the Owner;
- review: six implementation tickets awaiting an agent review pass;
- backlog: fourteen tickets after recording authorization reconciliation `HS3JRY`,
  including backup/restore `TRPV3J` and production security/deployment `6BXYJZ`;
- the policy gate on `F9HBSJ` is resolved: in-app 09:00 Owner-only digest,
  outbound email/additional recipients/escalation off. Implementation remains.

Human and signoff lanes are person-owned. An agent may move work into them but
cannot move it out.

## 21. Exact next-agent start instructions

Give Claude or the next Codex agent this instruction:

> Work in `C:\Users\Aly Jafferani\Documents\ChatGPT\New project\astra_project_tracker`.
> Read `CODEX_HANDOFF_2026-09-20.md` completely first, then `AGENTS.md`, the global
> mistakes log, `docs/design/astra-product-ux-baseline.md` and
> `docs/design/governed-drag-drop-contract.md`. Run
> `jaira next --per-lane --json` and `.venv\Scripts\python.exe tests\run.py` and
> report current board/test state before changing anything. Treat current code,
> approved target behavior and production gates as separate. Do not expose the
> server, create real users, ingest private sources, configure external providers,
> deploy, send messages or publish files without explicit owner authorization.
> Follow Jaira lane ownership; never move a human/signoff ticket out yourself.

## 22. Handoff acceptance checklist

- [x] Current 102-test and JavaScript baseline reverified.
- [x] Current implementation separated from approved/prototype behavior.
- [x] All settled governance, lifecycle, UX, drag, file, notification, mobile,
  accessibility and low-bandwidth decisions recorded or linked.
- [x] Zero-dollar Oracle Always Free + DuckDNS + Caddy pilot selected; private
  server/desktop retained only for development and recovery.
- [x] Browser sharing/account onboarding and pre-invite gates explained.
- [x] Private-source/shared-application boundary preserved.
- [x] Oracle Free Tier, Tailscale sharing and HTTPS proxy facts checked against
  current first-party documentation.
- [x] Backup, restore, monitoring, rollback and go-live gates stated.
- [x] Exact next-agent start instruction included.
- [x] No production implementation, deployment or real-user mutation performed.
