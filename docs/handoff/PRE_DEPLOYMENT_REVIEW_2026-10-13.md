# Astra pre-deployment plan and review handoff — 2026-10-13

## Status update — 2026-10-15

This section supersedes the dated source/test status in the original October 13
snapshot below; the original board audit and phase plan remain context, not a
current release-readiness claim.

- Aly selected Waitress for hosted use and kept Python's built-in server for
  local development. The hosted command is `astra serve --waitress`, using the
  WSGI adapter on IPv4 loopback behind Caddy. Astra ignores forwarded IP
  headers; Caddy's access log records the public client address.
- Local implementation and runbook fixes include startup-time database
  migration/refusal, Waitress request limits, WSGI header handling, secure
  dependency installation and refreshed deployment instructions.
- Current Windows full suite: **917 tests in 1005.884s, OK (skipped=1)**.
  An independent read-only review of this server/deployment diff found no
  remaining confirmed code defect.
- Caddy is not installed in this workspace, so `caddy validate` is
  **unverified**. Cloud provisioning, HTTPS/Secure-cookie operation, firewall,
  persistence after reboot, and hosted backup/restore are also unverified.
  Aly has not authorized staging or network exposure.
- The live board snapshot recorded in the handoff index on October 15 is 92
  tickets: 26 Done, 39 signoff, 13 human, 13 backlog and 1 in-progress.
  The review prompt is prepared, but other LLM reviews have not yet been run.

## Decision and scope

**Go for independent review and local preparation. No-go for deployment or real-user invitations.**
Aly requested a detailed plan, a committed review package for other LLMs, and a
complete board audit. This task is documentation and publication, not permission
to implement new features, merge a PR, create accounts, provision a server,
change credentials, import owner data, send messages or deploy.

The app source baseline is `da1b3fd21ed0d4357669f0e727369fda02640672` on
`codex/migration-safety-remediation`. This package adds documentation and
inspected existing board updates; it changes no application or test code.
Use the package commit SHA reported to Aly as the fixed review target. Record
both the package SHA and source baseline in every review.

## Current evidence and its limits

| Item | Verified state | Limit |
| --- | --- | --- |
| Architecture | Python standard-library server, SQLite, plain HTML/CSS/JS; package 0.1.0; schema 20 | Global availability, real-user capacity and hosted operation unverified |
| Dependencies | pyproject.toml declares Python >=3.11, setuptools >=75 for build, tzdata on Windows | Fresh Linux/Windows dependency audit still required |
| Last source test receipt | 832 tests in 976.020s, OK (skipped=1), at B1 source baseline | Windows symlink test unavailable; no deployment assurance |
| This package test receipt | Fresh Windows full run: 832 tests in 1011.192s, OK (skipped=1), exit 0; Node drivers ran | Unavailable Windows symlink case remains unverified; final SHA reported after push |
| B1 | Request framing, common headers, XML/ZIP guards, selected locked authority/assignee checks repaired and independently reviewed | Does not prove every endpoint/role/runtime race; ZQQCJM still human |
| Excel and timeline | Basic-Excel download/edit/upload checked in native Excel/Chrome on disposable data; later drag/order, linked scheduling and zoom repairs have dated browser evidence | Real project sample import, touch devices and screen readers not established by those checks |
| First-login / self-service password | Missing: CLI has init-owner, serve, transfer-primary and reset-password; owner reset exists, ordinary-user change/first-login gate does not | A5 required before invitations |
| Backup/restore/version CLI | No backup, restore or --version command in src/astra/__main__.py | Local relocation backup evidence is not a production backup system |
| CI and release | No .github workflow directory or release changelog in current tracked tree | Hosted CI, release candidate, integration and release tag unverified |
| Board | 85 existing tickets: 25 done, 39 signoff, 7 human, 14 backlog | Lane and ticked DoD are declared board state, not independent feature proof |
| Coordination | TV43F1 adds one review-package ticket | Final inventory has 86; it also requires Aly acceptance |

Evidence: [B1](B1_SECURITY_2026-10-13.md), [native Excel/Chrome](DESKTOP_VERIFICATION_2026-10-11.md),
[drag/order](TIMELINE_DRAG_REPAIR_2026-10-12.md), [linked scheduling](AUTOMATIC_TIMELINE_SCHEDULING_2026-10-12.md),
[phone/List and zoom](TABLE_SCHEDULING_2026-10-12.md), [deadline notices](DEADLINE_NOTICES_2026-10-13.md).
These are receipts to challenge against code/tests, not substitutes for a new review.

## Requirement checklist for this package

| Aly's requirement | Output / evidence |
| --- | --- |
| Plan first, detailed steps before deployment | Ordered gates below; implementation remains separate |
| Other LLMs review all handoff material before deployment | [Copyable review prompt](INDEPENDENT_LLM_REVIEW_PROMPT.md), complete handoff inventory in board audit |
| Commit locally and on GitHub for review | Explicit safe file list; normal push; exact package SHA in final receipt |
| Confirm all board tickets are knocked off | [Every-ticket audit](BOARD_AUDIT_2026-10-13.md): answer is no |
| Preserve Aly's decision authority and project rules | AGENTS.md governs acceptance, accounts, credentials, merges, branch and deployment |
| Report evidence honestly | Proven, Partial, Missing and Unverified; fresh full result and known skip |

## Ordered gates

The numbers are sequence, not automatic authorization. Work on Aly-assigned
tickets such as TRPV3J, 6BXYJZ, X8FNA5 and JQY55P needs Aly's specific takeover
approval. New implementation work goes into bounded agent tickets after Aly's go.

### 1. Freeze and independent review — before any server setup

1. Publish this package with all inspected safe tracked changes. Keep private
   workbooks, PDFs, data, keys, venvs, logs and screenshots outside public Git.
   Completion: local commit, matching remote SHA, full test receipt, scoped LF check.
2. Give the same frozen SHA and prompt independently to Claude, Gemini and/or
   another coding LLM with repository access. Reviewers inspect all tracked
   docs/handoff files, named accepted root handoffs, code, tests and every board
   ticket. They receive no other review's conclusions on their first pass.
   Completion: each returns its model, SHA, coverage checklist, evidence, test
   receipts, gaps and explicit deployment/invitation go/no-go.
3. Reconcile their reports into one finding register: unique ID, severity,
   reproduction, file/line, affected roles, required fix, test, owner and state.
   Reproduce disagreements locally. Voting or repeated claims do not prove a defect
   or a fix. Completion: every material finding is verified, refuted with evidence,
   or explicitly unverified; every blocker has a disposition.
4. Aly selects scope and authorizes fixes. Each fix gets regression tests and an
   independent review; reviewers check the new frozen SHA after changes.
   Completion: no unresolved release blocker, or a specific risk acceptance by Aly.

The other-LLM reviews have **not** been run by preparing this package. They remain
unverified until their actual reports are supplied and reconciled.

### 2. Reconcile board, decisions and release scope

5. Aly handles the protected human/signoff lanes. W6ZSGA, JM7CFP and 2FREQ9
   already have recorded chat acceptance; do not ask for repeat acceptance.
   Their board closure still belongs to Aly. JM7CFP and 3NT40T need criterion
   reconciliation: both have unticked DoD despite later child repairs/evidence.
   Completion: every open ticket has an explicit launch, deferred, superseded,
   acceptance or remaining-work disposition; no bulk automatic closure.
6. Resolve old questions using dated decisions before asking Aly again.
   The local checkbox artifact is draft/not submitted and grants no authority.
   Confirm only still-open values: region, hostname, backup access/encryption,
   proxy limits, workload, release version, support channel, privacy/data retention
   and first-user roster. Completion: decision register names source and date;
   recommendations remain recommendations until selected.
7. Decide first-release UI scope. Current source lacks Activity kind/person
   filters, Board entity swimlanes and a Manage rail entry. Owner/criticality
   lanes exist; lease renewal is not proof of cross-user Inbox/status refresh.
   Historical A6 recommendations and draft checkbox values do not settle scope.
   Completion: Aly names required items; build/review them or explicitly defer them.

### 3. Complete and prove local launch gates

8. **A5 passwords:** forced change for new/reset temporary passwords; ordinary
   signed-in users change their own using current password; retain the approved
   8-character minimum/no-lockout rule; audit and revoke other sessions.
   Completion: service, HTTP and browser tests prove restricted first-login
   navigation and each role's own-password flow; Aly accepts.
9. **Core acceptance:** use disposable projects to test create/file/rename entity,
   role access, tasks/subtasks/owners, approve/request/reject, locks, Undo, import
   preview/commit/replay, Shared/alternative plans, workdays/holidays and history.
   Above creates a predecessor; Below/After a successor; Concurrent is parallel.
   Check linked task dates, project scheduled bounds, independent critical paths,
   preserved assignees/durations/baselines, optional Owner-only agreed deadline
   revision and Owner/Chairman extension notices. Overlapping dates alone do not
   establish dependencies. Completion: saved/reloaded results and role refusals
   match accepted rules, including later-row/filtered-parent moves and cycle checks.
10. **B1 security completion:** independently check every route/role, session,
    CSRF, request/input/output type, authority-change window and workbook budget.
    Keep own historical import-report access after revocation (Aly chose it),
    closed-project reopen requirement and agreed deadlines restricted to App Owners.
    Completion: finding register closed; guard removals fail regressions; tests
    establish service checks, not merely hidden UI controls.
11. **B2 dependencies:** fresh disposable Linux and Windows environments; list
    installed/runtime/build packages, Python and Node versions, font licence and
    packaged assets. Completion: reproducible manifest; no unexplained dependencies
    or CDN; Linux compatibility and the symlink case checked where available.
12. **B3 local backup/recovery:** build the supported SQLite online-backup path,
    integrity check, encryption with Aly's public key, restore procedure and
    retention. Include WAL/concurrent-write, disk-full/failure and older-backup
    migration cases. Preserve previous database until restore is verified.
    Completion: local encrypted backup decrypts/restores in a fresh private folder;
    integrity, foreign keys, row counts and representative history reconcile.
    Cloud restore directions cannot be proven before a VM exists; see gate 21.
13. **B4 migrations/rollback:** rehearse upgrade against a disposable consistent
    copy, fault/retry/no-partial-step behavior and newer-schema refusal. An older
    executable is not a schema downgrade. Completion: pre-upgrade backup and
    compatible-code/database rollback tested; restoration does not silently discard
    post-backup writes without an explicit recovery decision.
14. **B5 load:** Aly confirms representative workload and response targets.
    Historical 20 projects/3,000 tasks/30 users/year of events is a proposal, not
    an accepted capacity claim. Measure key pages, imports, exports, linked moves,
    concurrent writers, lock waits, memory and response percentiles.
    Completion: recorded environment/data sizes, results within agreed limits,
    no unexplained lock failures or partial writes.
15. **B6 accessibility/devices:** approved target **WCAG 2.2 AA**; current
    candidate at 360/390/768/1024/1440 px,
    keyboard-only and actual 200% browser zoom; focus/dialog/drag alternatives,
    names, contrast, screen-reader announcements and reduced motion. Android Chrome,
    iPhone Safari/tablet and NVDA where available. Completion: findings fixed and
    real-device results recorded; missing device checks explicitly unverified,
    with Aly deciding whether they block launch. Emulation is not touch proof.
16. **B7 errors/logging:** safe request correlation, timestamp/status/duration,
    useful server-unreachable/500 experience, journal/log rotation and retention.
    Current generic 500/log_error path does not implement that full proposal.
    Completion: failure tests and logs help diagnosis without passwords, session
    tokens, request bodies, backup keys or unnecessarily private task details.

### 4. Release engineering — still before deployment

17. **CI:** add the approved Linux/Windows Python matrix and Node UI drivers,
    package/font/line-ending/private-file checks; verify actual hosted CI runs.
    Completion: exact candidate SHA green, with skips explicitly accounted for.
18. **Version and operator package:** align pyproject/__version__/server version,
    --version, changelog and schema notes. Prepare quick-start, Owner recovery guide,
    privacy note, support route and daily operating checklist. Include a tested
    incident checklist for outages, certificate trouble, database corruption/locks,
    lost/reclaimed VM and account compromise; Aly keeps an offline copy and handles
    user communications. Document Owner 'export everything' (consistent encrypted
    backup plus per-project CSV) and requester-scoped user export for privacy
    requests; test that exports cannot expose another user's/project's restricted data.
    Completion: commands tested locally; Aly selects release version and approves
    owner-facing privacy/support material. Version 0.2.0 is still a proposal here.
19. **Integration/release candidate:** inspect current remote main and PR #4;
    rehearse merge in an isolated full clone, including main-only tickets and
    regression evidence. Report conflicts without changing this checkout's branch.
    Aly alone chooses PR disposition/merges and any branch policy change.
    Completion: tested integration, approved immutable release tag/SHA and documented
    source, schema, dependencies, tests and rollback. Current merge/tag is unverified.

### 5. Authorized staging setup — requires a separate Aly go

20. Prepare and validate configuration templates first, then ask for concrete
    staging authorization. Aly chooses Oracle home region/available free shape,
    DuckDNS hostname, SSH and backup credentials, encryption tool and proxy policy.
    The selected design remains one Always Free VM, persistent SQLite, loopback Astra,
    Caddy HTTPS and Caddy logs for real IPs. Capacity/account eligibility and cost
    remain unverified; use [dated hosting evidence](FREE_HOSTING_2026-10-13.md) and
    refresh official limits before provisioning. If free capacity is unavailable,
    stop for Aly's fallback decision rather than choosing a paid resource.
    Completion: reviewed runbook/configs and explicit staging permission, no secrets
    in Git. Do not execute the historical runbook unchanged.
21. After permission, stage the pinned release with synthetic data: service user,
    ASTRA_HOME, OS/SSH firewall hardening, systemd restart/reboot, Caddy public-host
    routing, TLS/Secure cookies, request/time/resource controls and logging.
    Port 8765 stays inaccessible externally; SSH source restriction follows Aly's
    approved rule. Authentication IP bans/proxy policy require an explicit decision
    and a working recovery path; no account lockout is introduced.
    Completion: actual HTTPS/security/reboot/failure checks pass; simulated service
    and backup failure alerts work; multiple users cannot cross project boundaries.
22. Prove encrypted nightly off-VM backup and desktop copy, retention and recovery
    in both directions: Oracle to desktop and desktop to a fresh Oracle VM.
    Existing policy: RPO 24 hours, RTO 4 hours, 7 daily/4 weekly/3 monthly copies;
    only Aly holds recovery secrets. Timed drills must prove usable data, not merely
    successful uploads. Completion: both drills within policy, recovered contents
    reconciled, and cost/storage guardrails checked in the real account.
    A budget alert warns; it is not assumed to enforce a spending cap.

### 6. Real-user go-live — requires another explicit Aly approval

23. Freeze the tested candidate and assemble the signed gate register: open
    findings, cross-LLM reports, full/CI/browser/device/load/recovery receipts,
    approved residual risks, host configuration, cost and rollback.
    Completion: Aly approves the exact release, real data and first-user roster.
24. Aly creates accounts and handles passwords/invitations. Use minimum access,
    temporary password separation, tested first-login change, quick-start and support.
    A small pilot/two-week period is a recommendation until Aly selects it.
    Completion: invited users complete representative work with issues recorded;
    no blanket whole-app acceptance is inferred from a successful sign-in.
25. Operate and reassess: daily backup/alert review, patches, cost/disk checks,
    periodic restore drill, access reviews and release-by-release acceptance.
    Completion: a named operator and cadence; every update has a consistent backup,
    tested migration/rollback, new immutable release and fresh verification.
    Record weekly backup/desktop/uptime checks, monthly patch/storage/access review
    and quarterly timed recovery. The first quarterly drill and month of operating
    evidence follow launch; they cannot be claimed proven beforehand.

## Board closure is separate from launch readiness

See the complete [board audit](BOARD_AUDIT_2026-10-13.md). The 14 backlog tickets
include TRPV3J (launch recovery) and 6BXYJZ (deployment), five superseded/dropped
candidates that Aly must reconcile, and seven historically deferred features.
No ticket was automatically accepted, deleted, abandoned or moved out of a
protected lane in this task. Existing Done changes authored by Aly are being
published as supplied, not accepted again by an agent. 'Authored by Aly' here
refers to the existing updated-by metadata; this package does not independently
authenticate who operated that earlier board session.

All Done tickets would still not prove TLS, recoverability, real-user capacity
or completed other-LLM reviews. Conversely, deferred features can remain open
after a scoped release if Aly explicitly approves that scope.

## Known documentation drift to check

- September handoffs/test counts/PR facts are historical; current git and this
  dated package govern current state. The branch has a full history now.
- Q1 designation rules, settings/reopen, entity filing, mixed-save behavior,
  Excel choice, linked scheduling and deadline notifications have later decisions
  and repairs; OPEN_QUESTIONS recommendations are not fresh unanswered requests.
- Old blanket 'browser/desktop Excel unverified' is superseded only for the
  bounded native checks in DESKTOP_VERIFICATION and later drag/zoom receipts.
- JM7CFP/W6ZSGA/2FREQ9 chat acceptance does not automatically change their lanes.
- The runbook's missing backup/version tools, proxy controls and raw hosted
  commands are preparation, not tested deployed behavior. Refresh before use.
- Root CONTEXT.md/authorization documents and old feature notes require a
  consistency audit; this planning pass does not certify every old assertion.

## How to use the handoff with other LLMs

Send the exact published package SHA plus the contents of
[INDEPENDENT_LLM_REVIEW_PROMPT.md](INDEPENDENT_LLM_REVIEW_PROMPT.md).
Repository-enabled tools can read the files directly. A chat LLM without repo
access needs an export of tracked source/tests/docs/board at that SHA; GitHub
ZIP downloads exclude local untracked files. Never attach the private workbook,
database, credentials, screenshots or entire working folder by convenience.
If access fails, the reviewer must report coverage as unverified.

Return each model's report before authorizing remediation or deployment. Keep
the model, SHA and evidence attached to every finding, and repeat affected
reviews after fixes. A model's confidence score is not a launch acceptance.
