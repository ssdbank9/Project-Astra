# Astra Claude Code execution handoff — 2026-09-21

Prepared for Aly Jafferani and the next Claude Code implementation session.

- GitHub repository: `https://github.com/ssdbank9/Project-Astra`
- Repository visibility: public by Aly Jafferani's explicit 2026-09-21 decision; do not change visibility without a new explicit instruction
- Clean imported baseline branch: `main`
- Transferred implementation branch: `hs3jry-handoff`
- Historical Windows source workspace: `C:\Users\Aly Jafferani\Documents\ChatGPT\New project\astra_project_tracker`
- Historical parent-repository HEAD at export: `3e81380bc93b0763ae0813fe943e40997637538c`
- Application version: `0.1.0`
- Committed database schema: v11
- Database schema on `hs3jry-handoff`: v12
- Current production status: local development only; not deployed or approved for real users
- App Owner and only final decision authority: Aly Jafferani

## 1. Paste this exact prompt into Claude Code

```text
You are taking over the Astra project tracker from the private GitHub repository:
https://github.com/ssdbank9/Project-Astra

Work from the repository root on branch `hs3jry-handoff`. The Windows path in historical records is provenance, not a cloud-container requirement.

Read CLAUDE_CODE_HANDOFF_2026-09-21.md completely and follow it as the current execution handoff. Then read the active AGENTS.md instructions, CODEX_HANDOFF_2026-09-20.md, docs/design/astra-product-ux-baseline.md, docs/design/governed-drag-drop-contract.md, docs/design/authorization-matrix.md, and pending-global-mistakes.md. If running on Aly's Windows machine, also read the project-relevant entries in C:\Users\Aly Jafferani\.codex\mistakes.md; that machine-local file is not expected in a cloud container.

Before editing, run and report:
1. jaira next --per-lane --json
2. jaira resume --json
3. jaira show HS3JRY --for-lane in-progress --json
4. git status --short from this standalone repository
5. git diff for the exact HS3JRY files listed in the handoff
6. the platform-appropriate project-venv test command: `.venv/bin/python tests/run.py` on Linux/macOS or `.venv\Scripts\python.exe tests\run.py` on Windows
7. node --check src\astra\static\app.js

Preserve every existing user change and every settled decision. Do not reset, clean, discard, overwrite, or broadly reformat the worktree. Continue HS3JRY test-first from the implementation committed on `hs3jry-handoff`; it was uncommitted only in the historical parent worktree before transfer. First reconcile the stale README.md and CONTEXT.md authorization wording, rerun the full suite, complete the Jaira plan and DoD evidence, and move the ticket only as far as the lane rules permit. Do not move any ticket out of human or signoff. Do not deploy, expose the development server, create real users, ingest private sources, configure external AI, send external notifications, publish files, or provision Oracle/DuckDNS/Caddy without Aly Jafferani's explicit authorization.

After HS3JRY is safely handed to review/human according to Jaira, follow the ordered roadmap in this handoff. The design decisions are closed; use the approved defaults instead of reopening the design questionnaire. Ask Aly only when a genuinely new choice, credential, external action, or production-risk acceptance is required. Report facts, limitations, tests, and the exact files changed before claiming completion.
```

## 2. What is authoritative

Apply sources in this order:

1. Aly Jafferani's newest explicit instruction.
2. The active `AGENTS.md` instructions, including the exact-compliance and Jaira rules.
3. `pending-global-mistakes.md`, plus `C:\Users\Aly Jafferani\.codex\mistakes.md` when working on Aly's Windows machine.
4. This handoff for the transferred development branch and exact continuation sequence.
5. `CODEX_HANDOFF_2026-09-20.md` for the complete settled product, hosting, sharing, backup, security and implementation decisions.
6. `docs/design/astra-product-ux-baseline.md` for the production UI/UX contract.
7. `docs/design/governed-drag-drop-contract.md` for drag, schedule, lock, bulk, file and recovery behavior.
8. `docs/design/authorization-matrix.md` for the latest implemented authorization boundary.
9. `docs/research/asana-ux-and-design-tools.md` and `docs/research/monday-trello-workflow-ux-research.md` for evidence and transferable patterns. Research supports the design; it does not override Astra's authority model.
10. `CLAUDE_HANDOFF.md` only for the older evidence/lifecycle/privacy baseline. Its 14-test implementation snapshot is obsolete.
11. Current code and tests as evidence of what exists, not permission to override a later Owner decision.

`CODEX_HANDOFF_2026-09-19.md` is a historical snapshot. Refresh all ticket, claim, test and worktree facts before relying on it.

## 3. Non-negotiable working rules

- Work only inside the cloned Astra repository unless Aly explicitly expands the scope.
- Read `pending-global-mistakes.md` at the beginning, before implementation and before handoff. Also read the Windows global mistakes log when it is available locally.
- Convert each task into a requirement checklist and trace every requirement to code, test, documentation or an explicit limitation.
- Use `.venv/bin/python tests/run.py` on Linux/macOS or `.venv\Scripts\python.exe tests\run.py` on Windows. If `.venv` is absent, create it and run `python -m pip install -e .` through that environment. System Python can produce a false `ZoneInfoNotFoundError` because it may lack `tzdata`.
- Use `apply_patch` for edits. Preserve unrelated and user-owned changes.
- Use `rg`/`rg --files` for searching.
- Run Jaira lane by lane. Claim before work, obtain the lane prompt, record plan/DoD proof and pause notes, move the ticket before committing, and commit the ticket file with its implementation.
- An agent may move a ticket into `human` or `signoff`; an agent must never move a ticket out of either human lane.
- Never edit `.jaira/tickets` manually. Use the Jaira CLI.
- Keep one source of truth for each rule. Update stale public documentation when behavior changes.
- Do not call code production-ready merely because unit/HTTP tests pass.
- Do not claim a browser acceptance test when only source/tests were checked.
- Never expose the development HTTP server directly to the internet.
- Never place a live SQLite database in Dropbox, OneDrive or another file-sync directory.
- Do not create real Chairman or Manager accounts until HS3JRY is reviewed and accepted.

## 4. Git transfer and branch snapshot

The original Windows parent repository was deliberately dirty and was not pushed. A sanitized standalone repository was created so unrelated parent files, local data and runtime artifacts cannot enter Project Astra.

`main` contains the clean committed Astra baseline plus the repository-level Jaira/agent instructions needed to work independently. `hs3jry-handoff` contains the transferred in-progress authorization slice and its handoff documents. Work from `hs3jry-handoff`; do not reconstruct the change from `main`.

Files transferred for the current visual/authorization work:

```text
.jaira/tickets/01M2X47YF0DA7QCQV4QGAX572Q-prototype-governed-astra-drag-and-drop.md
.jaira/tickets/01M2YBDV8NBKQ34273XKHS3JRY-reconcile-latest-owner-only-authorization.md
CONTEXT.md
src/astra/db.py
src/astra/service.py
src/astra/static/app.js
src/astra/web.py
tests/test_core.py
tests/test_web.py
pending-global-mistakes.md
```

New files/directories in this slice:

```text
docs/design/authorization-matrix.md
CLAUDE_CODE_HANDOFF_2026-09-21.md
CLAUDE_CODE_START_PROMPT.md
```

The local-only `tmp_ui_accept/`, `.venv/`, databases, caches and credentials were deliberately excluded. Continue to stage only intended paths, inspect the staged diff, and do not use destructive shortcuts such as `git clean`, `git reset --hard` or `git checkout --`.

The authorization change is committed only to preserve it during transfer; it is not reviewed, accepted or complete. Compare `hs3jry-handoff` with `main` and review the real diff; do not assume this summary replaces review.

## 5. Visual acceptance completed before this handoff

### 5.1 Governed drag prototype

The self-contained prototype is `design/astra-drag-drop-prototype.html` and its contract is `docs/design/governed-drag-drop-contract.md`.

The prototype was rendered in the Codex in-app Chromium browser and exercised end-to-end:

1. Ordinary Kanban move followed by Undo.
2. Protected completion attempt followed by Owner approval.
3. Atomic bulk lock conflict with no partial mutation.
4. Critical-dependency change routed to Owner approval.
5. Owner-only file flow: 180 MB accepted; 280 MB rejected against the fixed 250 MB hard ceiling.
6. Private What-if scheduling followed by submission.

Verified observations:

- role, mode, phase, locks, approvals, notices and audit entries visibly changed as expected;
- production boundary remained visible;
- desktop and temporary 1024x900 responsive layouts were readable;
- the 1024px layout moved the inspector below the main workspace without clipping controls;
- the browser console had no warnings or errors;
- a full-page capture showed a browser stitching artifact, but the live page dimensions were normal after resetting the viewport;
- Jaira ticket `AX572Q` contains the detailed visual evidence and remains in the human lane for Aly's acceptance.

### 5.2 Current production shell

The synthetic local fixture server `tests/ui_fixture_server.py` was used on loopback only. The fixture Owner signed in, the dashboard rendered, and a task detail dialog was opened.

Verified observations:

- Owner-only lifecycle, file-link and final-result controls rendered in task detail;
- the Owner request inbox integration rendered without browser-console warnings/errors;
- the task detail dialog was functional and visually coherent;
- the Manager experience was verified through service/HTTP tests and source inspection, but was not visually exercised through a separate Manager login;
- the legacy dashboard has horizontal overflow/clipped toolbar content at a 1280x720 viewport. This is a real pre-existing visual issue. It belongs to the planned A-hybrid shell work and is not fixed by HS3JRY;
- the browser tab was closed and no listener remained on port 8766 when this handoff was prepared;
- `tmp_ui_accept/` was synthetic local test output and was deliberately excluded from Git. Recreate isolated fixtures locally when repeating browser acceptance.

## 6. Current development slice: HS3JRY

Ticket: `HS3JRY — Reconcile latest Owner-only authorization`

Current lane: `in-progress`.

Goal: every application path must enforce the latest rule that protected lifecycle and every file/final-result mutation are App Owner-only, while Managers retain approved ordinary project operations.

### 6.1 Implemented on the transferred branch, pending review

#### Database

- `SCHEMA_VERSION` changed from 11 to 12.
- Append-only migration creates `owner_action_requests`.
- Each request records project, optional task, action, JSON payload, reason, requester, request time, status and optional decision metadata.
- Indexes support status/time and requester/time lookups.

#### Service authorization

- `can_manage_project` no longer grants mutation authority merely because a user is Chairman.
- Chairman retains organization-wide project visibility through the read path.
- A Chairman receives Manager powers only if the Owner separately grants that user an explicit Manager membership on that project; the power then comes from the membership, not the Chairman label.
- Managers may create and directly edit ordinary work only in ordinary statuses.
- Managers/designated approvers attempting protected actions create an Owner request, audit event and Owner notification; the live accepted state is unchanged.
- Unauthorized Viewer/member or read-only Chairman attempts are rejected, audited and notified to the Owner.
- Task detail now returns explicit permissions:
  - `can_edit_ordinary`
  - `can_request_protected`
  - `can_decide_protected`
  - `can_manage_files`
  - `can_read_files`
- Owner-only direct actions now include submission acceptance, changes requested, reopen, on hold, schedule proposal approval/rejection and project closure.
- Manager/designated-approver versions of supported protected actions return a durable request instead of mutating the task/project.
- Attachment link add/remove and final-result mark/unmark are Owner-only.
- Project-authorized users retain attachment/final-result list/read access.
- Blocked attachment removal emits the specific `attachment_removal_blocked` Owner notification.
- Obsolete `_require_decider` and `_block_self_decision` helpers were removed after their behavior moved into the new request seam.

#### HTTP API

- Added Owner-only `GET /api/owner-action-requests`.
- Protected Manager attempts return HTTP 202 with a `request` object.
- Owner direct actions retain their normal success responses.
- Updated protected paths include task update, reopen, hold, schedule approve/reject, submission accept/request-changes and project close.

#### Browser UI

- Project close control is App Owner-only.
- Owner Inbox fetches the Owner action-request queue.
- Pending protected requests render under `Needs action`; ordinary notifications remain under `Activity`.
- Lifecycle controls use server-provided permissions.
- Owner buttons act directly.
- Manager buttons are labeled as requests to the Owner.
- Viewer/read-only Chairman sees an Owner-decision notice and no mutation control.
- Schedule decision controls follow the same direct-versus-request behavior.
- Attachment/final-result mutation controls render only for `can_manage_files`.
- Non-Owners receive a read/download-only explanation.
- Manager request feedback explicitly says that an Owner request was created and live accepted state was unchanged.

#### Tests

Added or revised service tests for:

- Chairman organization-wide visibility without implicit mutation power;
- Manager ordinary edits and protected status requests;
- Manager self-acceptance routing to the Owner;
- designated Approver routing acceptance to the Owner;
- acceptance requests leaving task/submission unchanged;
- Owner notification and request-queue visibility;
- request-changes, reopen and hold requests leaving live state unchanged;
- schedule decision requests;
- project closure: Chairman blocked, Manager request, Owner direct closure;
- attachment authorization and blocked removal notification;
- final-result authorization across Owner, Chairman, Manager and Viewer.

Added HTTP tests for:

- Manager acceptance returning 202;
- live status remaining unchanged;
- Owner request queue visibility;
- Owner-only attachment and final-result mutations;
- permitted Manager reads;
- blocked removal notification.

### 6.2 Verification already obtained

The final complete run after the last code edit produced on 2026-09-21:

```text
Ran 110 tests in 75.217s
OK
```

`node --check src\astra\static\app.js` also passed with no output.

Claude must still rerun both checks after any further edit and report its own live
baseline before continuing.

### 6.3 Remaining HS3JRY work

Complete these in order:

1. Read the exact diff and confirm no existing lifecycle or read scope regressed.
2. Update stale authorization wording in `README.md`:
   - it still says Manager, Chairman or designated Approver may directly accept;
   - it must say only the App Owner decides protected actions, while an eligible Manager/Approver may request.
3. Update stale domain wording in `CONTEXT.md`:
   - it still says an Approver may accept a submission;
   - it must say an Approver recommends/requests acceptance and the App Owner decides.
4. Check the implementation against every row of `docs/design/authorization-matrix.md`.
5. Confirm every current HTTP/UI mutation enters the service boundary. There is no automation/offline subsystem yet; document this absence rather than pretending it was tested.
6. Run the full Python suite and JavaScript syntax check after all edits.
7. Optionally add a targeted test proving a read-only Chairman's blocked protected attempt produces audit/Owner notification if current coverage does not already prove it clearly.
8. Decide whether the request inbox needs decision buttons in this ticket. The current queue is visible, but generic approve/reject execution of an `owner_action_requests` row is not implemented. Direct Owner actions remain available from the underlying task/project screen. Treat this as an explicit reviewed scope decision, not an accidental omission.
9. Record the production-shell 1280px overflow as a separate shell issue or an existing Gate 2 note; do not hide it inside authorization work.
10. Update all six Jaira plan items with proof. The board currently shows plan step 3 as `doing` and the others unticked even though most implementation exists.
11. Mark the single DoD item done only if every clause is proven or explicitly scoped to a non-existent future subsystem.
12. Add a concise Jaira pause/outcome note describing exact tests, browser evidence, gaps and non-implemented systems.
13. Move HS3JRY according to the lane sequence. Do not skip the required review lane. Do not move it out of a human lane.
14. Commit the ticket file with the code and include `HS3JRY` in the commit message so Jaira can derive the commit list.

Suggested commit after review-ready completion:

```text
feat(HS3JRY): enforce owner-only protected actions
```

Do not combine unrelated repository files into that commit.

## 7. Accepted product decisions — do not reopen them

### 7.1 Product and privacy boundary

- Astra is a standalone application with its own database, login, deployment and authorization boundary.
- Ordinary users see only authorized shared project/task records and explicitly published outputs.
- Mailbox collection, document matching, OCR, private evidence assessment and originals remain on Aly's machine by default.
- Original `.eml` and attachment bytes remain authoritative.
- Only Aly sees private originals and full derivatives by default.
- A task/source link must never expose a full private thread or bypass authorization.
- Stable IDs define identity; names, filenames and paths are display data.
- Identical bytes do not prove identical business meaning, and identical filenames do not prove identity.
- Evidence extraction status remains explicit: complete, partial, empty, OCR pending, unsupported, encrypted, corrupt or failed.
- AI output is an evidence-backed Proposal and never mutates the board by itself.

### 7.2 Final role matrix

| Capability | App Owner | Project Manager | Viewer/member | Chairman without project Manager membership |
| --- | --- | --- | --- | --- |
| Organization-wide read | Yes | Granted projects | Granted projects | Yes |
| Ordinary project-local edits | Yes | Yes | No | No |
| Protected lifecycle decision | Yes | Request only | No | No |
| Critical path/milestone/completion impact | Yes | Request only | No | No |
| Cross-project task/file move, copy or link | Yes | No | No | No |
| File/folder/link/version/final-result mutation | Yes | No | No | No |
| Authorized file open/download | Yes | Yes | Yes | Yes where project is visible |
| Workflow/template/automation publish | Yes | No | No | No |
| Force unlock | Yes | No | No | No |
| Access/credential administration | Yes | No | No | No |

Every blocked or unauthorized attempt by another user is audited and notifies Aly. Aly's own successful actions are audited without a redundant self-notification.

### 7.3 Task, lifecycle and schedule

- One primary accountable Task Owner per task/subtask.
- Collaborators, Reviewers and Approvers are separate supporting roles.
- Different subtasks may have different Task Owners.
- Direct-child accepted/completed count rolls up separately from declared progress; Astra never invents a percentage.
- Visible ordinary flow: Draft → Ready → In progress → Blocked → Submitted for review.
- Managers operate ordinary stages; acceptance/rejection/completion/closure/reopen/override are protected.
- Manager protected attempt creates exactly one visible Owner request and does not change accepted state.
- Delivery/attachment is not completion. Submission and acceptance are distinct.
- Accepted versions are immutable. Reopen records a reason and revised timeline while preserving earlier evidence and dates.
- Cancellation, abandonment, delay, on hold and reopen remain distinct.
- On hold requires owner, reason and follow-up checkpoint.
- Project closure is separate from task completion; exceptional closure is Owner-only and preserves residual work.
- Preserve baseline, current approved schedule and pending proposal separately.
- Baseline is captured once and never silently overwritten.
- Ordinary authorized date edits may update current dates with reason/audit.
- Protected-impact changes require Owner approval.
- Date-only deadlines end in the project's governing local day.
- Project workweek and holidays are explicit; do not infer them.
- Criticality is Critical, High, Normal, Low or visibly Unrated.
- Users can sort by criticality or due date.
- Full CPM supports multiple parallel zero-slack critical paths. Isolated tasks are not marked critical.
- Dependencies are currently finish-to-start only; the accepted future design adds all four standard dependency types plus lag/overlap.

### 7.4 Portfolio and budget

- A cross-entity project has one stable project ID.
- Each project rolls up to exactly one Primary entity.
- A multi-entity project without a Primary entity stays visibly Unassigned; never default to the first entity.
- Budget production model: planned, committed and actual/spent plus explicit variance.
- Currency totals remain separate and are never silently blended.
- Current implementation stores planned amount only; committed/actual/variance remains a known gap.

### 7.5 Visual and interaction direction

Use the accepted A-hybrid Command Center:

- Command Center density and persistent context;
- Focus Workspace typography and progressive disclosure;
- Executive Cockpit compact health strip;
- native HTML/CSS/JavaScript;
- polished, decisive buttons, panels, windows, dialogs and feedback;
- strong visual impact without decorative clutter or distracting motion.

Permanent navigation:

1. Home — portfolio Command Center.
2. My Work — assigned work and personal planning.
3. Inbox — Needs action and Activity.
4. Projects — authorized project workspaces.
5. Capture — private quick capture.

Owner administration sits under Manage: governance, people/access, workflows/templates, Automation Center, managed files/storage, audit and system health.

Each project uses the same task record across Overview, List, Board, Timeline and Activity. Routine clicks open a task drawer; stable full-page URLs support deep review, schedule, approvals, files and audit.

Home is exception-led: overdue, blocked, awaiting Owner, near due, critical-path exposure, capacity problems and failed automation/sync.

Keep these separate:

- My Work = assigned work.
- Needs action = approvals, reviews, conflicts and failures.
- Activity = watched/subscribed updates.
- Capture = private intake not yet filed.

Reading/dismissing a notification never approves anything.

### 7.6 Board, drag, Gantt and What-if

- Full Kanban drag/drop is required.
- Cards show only decision-grade information: task, owner, due risk, blocker, criticality, selected custom fields and protected state.
- Drag is a proposal to one server-authorized mutation seam, not a local truth change.
- Owner and Manager may perform ordinary moves; Viewer cannot mutate.
- Protected destination creates an Owner request and leaves accepted live state unchanged.
- Every drag has keyboard and touch Move alternatives using the same destinations and permission explanations.
- Gantt supports drag/resize with preview of downstream effects before commit.
- Critical-path, milestone, project-completion and cross-project effects are Owner-protected.
- What-if edits remain private until submitted. Submission creates an approval request; it does not apply the scenario.
- Bulk operations are atomic: one authorization/lock failure rejects the whole batch.
- Manipulation locks are renewable leases, not permanent ownership.
- Disconnection releases/expires safely; stale clients cannot silently overwrite newer state.
- Undo is a compensating, audited restoration, not history deletion.
- No warning-only bypass for prohibited moves. Illegal actions are blocked or routed to a request.

### 7.7 Files and final results

- Every file/folder/link/upload/version/permanent-link/final-result mutation is Owner-only.
- Authorized users may open/download/read files permitted for their project.
- Managed file and external link are visibly distinct.
- Final-result marking is explicit; acceptance never automatically publishes a final result.
- Removing a link never deletes the source file.
- Final results and accepted evidence remain immutable/versioned.
- Folder drop is recursive in future managed storage.
- Each batch has a hard 250 MB ceiling with no warning grace range.
- Invalid/unauthorized/oversize batches fail atomically.
- Cross-project file/task operations are Owner-only.
- Permanent links are Owner-only and audited.
- Actual upload/download/version/permanent-link storage is not implemented yet. Current production code stores attachment paths/links only.

### 7.8 Notifications

- Initial delivery is in-app only.
- Aly receives real-time in-app alerts for protected requests, critical-path/project-completion changes, milestone moves, final-result effects, permanent-link changes, consequential blocked/unauthorized attempts and large cross-project actions by others.
- Every unauthorized attempt by another user notifies Aly, including attachment removal.
- Aly's own successful actions are audited but not self-notified.
- Daily digest defaults to 09:00 in Aly's timezone, in-app only, Owner recipient only.
- External email/SMS/Teams/Slack notifications remain off until separately authorized and configured.

### 7.9 Mobile, accessibility and bandwidth

- Core use must work from a hosted HTTPS URL in ordinary browsers; users install no Tailscale and never share Aly's identities.
- Small-screen Board becomes a single-column lane/stage view with explicit Move action.
- Gantt is read-only/summary-first on small screens; complex edits route through forms and impact previews.
- Low-data mode loads compact task lists first and defers charts, large history and media.
- Target WCAG 2.2 AA.
- Semantic controls, visible focus, reduced motion, color-plus-text/icon, logical focus return and ARIA live status are required.
- Every Gantt has a structured table alternative; every dashboard metric lists/drills into contributing authorized records.
- Validate keyboard-only, NVDA, touch, 200–400% zoom, high contrast and constrained network before go-live.

### 7.10 Automation and AI

- Automation Center requires registry, drafts, test runs, health, run logs and kill switch before a broad rule builder.
- Automation may create a request where policy permits; it may never self-approve or directly execute protected/cross-project work.
- External AI is disabled for the initial release.
- Future Assessor must be provider-swappable, zero-direct-cost by default and preferably local on Aly's desktop.
- No private content goes to an external AI provider without a separate explicit authorization covering provider, scope, terms, model/version and spending rule.

## 8. Runtime and sharing decision

Astra will be a hosted standalone browser application. Users get individual Astra accounts and an HTTPS URL; they do not receive source code or the database.

Selected zero-direct-cost pilot:

1. Oracle Cloud Always Free VM in Aly's tenancy.
2. Free DuckDNS hostname.
3. Caddy terminates HTTPS and reverse-proxies only to Astra on loopback.
4. Individual Astra accounts for each user.
5. No Tailscale requirement for normal users.
6. A private server/always-on desktop remains a recovery/development option.
7. Host changes must preserve IDs, permissions, audit history and behavior.

The zero-dollar ceiling is hard: capacity, storage and backup must alert or fail safely before a free allowance is exceeded. Nothing may silently upgrade to a paid resource.

This is a selected architecture, not a completed deployment. Before real users:

- production-capable service runtime or explicit reviewed justification;
- HTTPS and `Secure` cookie proof;
- first-login forced password change and Owner-controlled recovery;
- secrets/environment configuration outside Git;
- request/body/upload limits and security headers;
- encrypted automated off-host backups and demonstrated restore;
- health, disk, backup and incident monitoring;
- endpoint authorization review;
- managed storage/download authorization;
- real-browser/mobile/accessibility/low-bandwidth tests;
- multi-user concurrency/load test and rollback;
- deployment security review and Aly's go-live approval.

Do not provision Oracle, DuckDNS, Caddy, firewall rules, system services, accounts or credentials until Aly explicitly starts the deployment gate. Those actions require human credentials and should use a step-by-step wizard/runbook.

## 9. Backup and continuity decisions

- Database stays on local VM/block storage, not a synced folder.
- Automated encrypted off-host backup is mandatory.
- Backup destination must remain zero-direct-cost and must be selected at deployment time.
- Restore must be demonstrated, not assumed.
- Preserve database, managed files, configuration required to reconstruct service, audit history and stable IDs.
- Record recovery point objective and recovery time objective before pilot.
- The desktop/private server option must be able to restore the same application state if Oracle becomes unavailable.

## 10. Current Jaira state relevant to continuation

Always refresh with `jaira next --per-lane --json` and `jaira resume --json`; this section is a snapshot, not a substitute for the board.

- `HS3JRY` — in-progress. This is the current implementation priority.
- `AX572Q` — human. Governed drag prototype visually checked; Aly must accept/send back.
- `JQY55P` — human. A-hybrid shell choice was already accepted in conversation; record only through the human lane.
- `T4MSJW` — human. Monday/Trello research recommendations accepted.
- `MTEDTM` — human. Cumulative decision/hosting handoff accepted in conversation.
- `9R7A87`, `Z24KVH`, `JZACMP`, `XDA2JR`, `JPEBCM` and other reviewed tickets may be waiting in signoff. Only Aly moves them out.
- Review-lane tickets still require an independent model review before signoff.
- Claims may show abandoned/stale because earlier sessions ended. Re-claim any agentic ticket before working it.

No design questionnaire remains open. Remaining human actions are acceptance/signoff gates and later deployment values/credentials, not product-design re-litigation.

## 11. Ordered development roadmap after HS3JRY

Follow the live Jaira priority, but the accepted production sequence is:

### Gate 0 — close board and documentation gates

- Finish/review HS3JRY.
- Record Aly's accepted human-lane decisions without the agent moving tickets out of human/signoff.
- Reconcile stale docs and current code.

### Gate 1 — production runtime and recovery foundation

- production service wrapper/supervision;
- configuration and secrets boundary;
- first-login/password recovery;
- security headers and body limits;
- health/logging/monitoring;
- backup and restore proof.

### Gate 2 — shared A-hybrid product shell

- permanent navigation;
- Command Center;
- project Overview/List/Board/Timeline/Activity;
- task drawer and stable task URL;
- responsive layout, including fixing the observed 1280px overflow;
- accessibility and low-data foundations.

### Gate 3 — governed Board and approvals

- shared task model and compact cards;
- legal destination policy;
- drag plus keyboard/touch Move;
- protected request behavior;
- Needs action versus Activity;
- request approval/rejection execution and audit.

### Gate 4 — Timeline, dependencies and What-if

- dependency rendering/editing;
- four dependency types and lag/overlap;
- unscheduled tray;
- schedule preview and structured table alternative;
- private What-if and governed apply.

### Gate 5 — workload, automation, templates and notifications

- effort/capacity definitions before Workload claims;
- Automation Center registry/run log/kill switch;
- safe draft/test/publish;
- templates only after policies stabilize;
- daily in-app digest.

### Gate 6 — managed files

- storage adapter;
- Owner-only upload/folder/version/permanent-link/final-result mutation;
- authorized download;
- hashing, resumable transfer, folder recursion, versions and 250 MB atomic batch limit;
- backup and restore including file bytes.

### Gate 7 — zero-dollar deployment pilot

- Oracle VM, DuckDNS and Caddy only after explicit authorization;
- secure cookies and TLS proof;
- restore/load/security/device acceptance;
- create users only after go-live approval;
- monitor free-tier ceilings.

## 12. Verification and acceptance standards

For every implementation ticket:

1. Prove the requested behavior goes red before implementation where practical.
2. Keep authorization at the service boundary; UI visibility is only a usability layer.
3. Add service and HTTP tests for every role affected.
4. Run the full suite using the project venv.
5. Run JavaScript syntax checks for UI changes.
6. Perform a real browser check for visible UI changes and report exactly which roles/viewports were exercised.
7. Check keyboard/focus, empty/loading/error/forbidden/conflict/offline states proportional to the change.
8. Update the authoritative design/domain/readme text if behavior changed.
9. Record Jaira plan/DoD proof before moving.
10. Inspect the exact staged diff and commit only intended files.

Production go-live is a separate decision. Unit tests do not prove TLS, restore, multi-user load, device behavior, accessibility, security headers, actual storage or zero-cost hosting limits.

## 13. What Aly should expect from Claude's next report

Claude should report:

- exact live Jaira state and claim result;
- exact Git status and which changes were already present;
- baseline and post-change test counts;
- what it changed and why;
- authorization matrix proof for Owner, Chairman, Manager and Viewer;
- browser scenarios and viewports actually exercised;
- unresolved gaps, especially request execution, missing future subsystems and dashboard overflow;
- ticket lane and any human acceptance question;
- exact commit hash if a commit was created;
- a clear statement that no deployment/private-source/external-message action occurred.

## 14. Human-only and separately authorized actions

Claude may prepare code, tests and runbooks, but Aly must explicitly authorize or personally perform the steps involving:

- Oracle tenancy/resource creation;
- DuckDNS account/token/hostname;
- DNS/TLS/firewall exposure;
- system service installation on the production host;
- production secrets;
- first real user creation and invitation;
- backup destination credentials;
- sending external notifications;
- publishing real files or private evidence;
- enabling any external AI provider;
- go-live approval;
- moving Jaira tickets out of human/signoff.

## 15. Handoff completion condition

This handoff is successful when Claude can start with no repeated design interview, preserve the current worktree, verify and finish HS3JRY safely, keep all accepted authority/privacy/hosting decisions intact, and report the next human gate without claiming production readiness prematurely.
