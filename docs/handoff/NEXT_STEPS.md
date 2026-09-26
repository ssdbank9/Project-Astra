# Astra next steps — from today to distribution

This plan runs from the current state (branch head `0b90ceb`, schema v20,
676 tests, 33 tickets in signoff) to Astra being online for real users and
operated safely. It follows the order Aly set on 2026-09-25: finish the UI and
the whole app first, then move it to the server and put it online for everyone
(Slack ts 1790310312.798809). Hosting stays Oracle Cloud Always Free with a
DuckDNS name and Caddy for HTTPS, as decided on 2026-09-20.

How to read each phase:

- **Scope** says what the phase is for. **In** and **Out** draw the line.
- **Tasks** are concrete and roughly ordered. Each code task becomes one jaira
  ticket and goes through the usual lanes, an independent review and signoff.
- **Done when** is the definition of done for the phase.
- **Depends on** lists what must be finished first.
- **Who** says whether Aly or Codex does it.
- **Risks** lists what could go wrong.

The phases map onto the Delivery Plan artifact
(https://claude.ai/artifact/WoAfB3Q9gT2piSaWbNppTi): its A Consolidate and
B Finish core are phase A here, C Production readiness is phases B and C,
D Deployment pilot is phase D, and E Operate is phases E and F.

---

## Phase A — Close out development

**Scope.** Get every finished piece accepted, answer the open questions, merge
the work into `main`, and build the few remaining app features that belong in
the first release.

**In.** Aly's signoffs; the open questions; option 6 (PR #4, then this branch's
pull request); option 8 (the `tmp*` folders); Z72D79; the Gate 2 leftovers and
review follow-ups; the two features the 2026-09-20 decisions require before
invitations (password change at first sign-in and a self-service password
change); doc drift.

**Out.** Hosted file uploads (MXY7BG), the daily digest (F9HBSJ), AI first pass
(KK400X), custom fields, sections, goals, status updates, workload (dropped),
What-if mode, dependency types other than finish-to-start. These wait until
after the pilot unless Aly pulls one in.

### A1. Aly's signoffs (Aly)

1. Pull the branch and run the local test sequence (`HANDOFF_2026-09-26.md`
   section 2.1).
2. Work through the 33 signoff tickets. Each ticket's `review-check` field has a
   short manual check list. Suggested order, newest first, because newer work
   builds on older work:
   - Lock #13: 3FQEKB.
   - Lock #12: JN1QYG, X07XV4, XV92JJ.
   - Gate 2: 3C1Z74, VPYGY5, CR121Z, FKVHH8, 4T4DEA, PZTYC9, DR3PKR.
   - 2026-09-24: 3M2AYA, XX9RFM, PDDS2D, KBWY86, 6G89SJ, GTEYTG, K62ZAP, ZSZ9T2.
   - Reworks: QY0WG2, Y3WC71, AYW0QC, 8B9NBH, CS93C6, 5WZ4A8.
   - Older: HS3JRY, D73AQW, C9KPH6, 9R7A87, Z24KVH, JZACMP, XDA2JR, JPEBCM.
3. Accept a ticket from the board TUI sign-off screen (key `a`), or with
   `jaira move <id> --to done --force`, which the jaira notes say is the human
   CLI route out of signoff. Send one back by moving it to the lane it should
   return to, with a note saying why.
4. Move the four human-lane tickets (JQY55P, AX572Q, Z9JCZ6, MTEDTM). Their
   notes already record Aly's decisions from 2026-09-19 and 2026-09-20.
5. Decide what to do with backlog tickets the build has overtaken: RWMRKM
   (My Work) and 4G3NY0 (month calendar) were built by FKVHH8; S1C6PN
   (workload) was dropped; X8FNA5 (shell) was built by Gate 2 slices 1-7;
   A48JEX (board by sections) was built as a status board instead.
6. Commit and push the ticket moves (git user and email are already set on
   Aly's machine). Tell Codex the new head SHA.

Done when: signoff and human are empty or hold only tickets Aly sent back with a
reason, and the moves are pushed.

### A2. Answer the open questions (Aly)

Answer `OPEN_QUESTIONS.md`. Every question has a recommended default; "go with
your defaults" is a valid answer. The ones that change code in phase A are Q1
(reviewers and approvers), Q2 (PR #4 extra work), Q3 to Q5 (Z72D79), Q6
(JPEBCM fix) and Q8 (password change).

### A3. Small fixes from the reviews (Codex)

One ticket each, or one grouped ticket if Aly prefers fewer:

1. Reviewers and approvers, per Aly's answer to Q1. If the Chairman and viewers
   are removed, apply the rule on every path (panel, importer Reviewers and
   Approvers columns, templates) and flag older rows, as 3FQEKB did.
2. JPEBCM Medium: make `set_project_entities` clear or reconcile
   `primary_entity_id` when the primary is no longer linked, with a test.
3. Y3WC71 Lows: trim leading whitespace in `web._csv_cell` before the formula
   check, as `importer.csv_cell` does; escape `%` and `_` in search.
4. 8B9NBH Lows: the template picker text; pin the Chairman-only role check.
5. AYW0QC Lows: pin the abandoned-status exclusion and the `+1` in
   `_duration_days`.
6. PDDS2D Low: narrow the CLI's broad exception catch to the recovery commands.
7. Doc drift: update `docs/design/authorization-matrix.md` and `CONTEXT.md` to
   the current Chairman, viewer and collaborator rules, and correct the
   older handoff bullets that still read as current.
8. **Done (G1PPV7).** Block submit for a viewer who is the legacy assignee of
   a top-level task. `_may_submit` in `src/astra/service.py` used to return
   True for the task's assignee before any 3FQEKB refusal (found by the
   fact-check, 2026-09-26). It now applies the same rule as for
   collaborators, so a viewer submits only their own subtask (Aly, Slack ts
   1790386492.402489). Tests are in `tests/test_assignment.py` and
   `tests/test_web.py`. Left for Aly: accept G1PPV7 in signoff.

Done when: each fix has a test that fails without it, the suite is green, and
the tickets are in signoff.

### A4. Z72D79: settings history and reopening a closed project (Codex, after Aly answers)

Today these changes write no audit row: working days, holidays, budget, project
entities and primary entity, entity active flag, import template settings. A
closed project cannot be reopened. The ticket's open questions are Q3 to Q5 in
`OPEN_QUESTIONS.md`.

Tasks: an audit row with actor, time, before and after for each listed change;
show it in the project Activity tab (project settings) and wherever Aly chooses
for app-wide settings; a reopen action with a required reason, audited and
notified like close; tests for each change and for reopen. The schema may need a
new step (v21) if a new table is chosen for app-wide history.

Done when: the ticket's definition of done is met and reviewed.

### A5. Password change at first sign-in, and changing your own password (Codex)

The 2026-09-20 sharing plan lists "forced first-login password change" as a
gate before invitations (`CODEX_HANDOFF_2026-09-20.md` section 15.3). Today
only owners can set passwords, and nobody is asked to change a temporary one.

Tasks: a flag on users set when an owner creates the account or resets the
password; after sign-in, a user with the flag sees only a "choose a new
password" screen until they change it; any signed-in user can change their own
password by typing the current one; keep the 8-character minimum; audit in
`user_events`; sign out the user's other sessions on change. This needs a
schema step (v21 or v22) and tests at service, HTTP and UI level. Keep Aly's
rule that sign-in never locks anyone out.

Done when: an account created by an owner cannot reach any screen before the
password is changed, and a member can change their own password.

### A6. Gate 2 leftovers (Codex, Aly picks which ones before launch)

1. "Divide by" entity swimlanes on the Board (owner and criticality exist).
2. A filter on the project Activity tab (by kind and by person).
3. "Since Monday" deltas on the Home tiles (the UX research lists these as
   "later"; recommended after launch).
4. Live refresh of lock badges, lock banners and Inbox gate lines, for example
   a light poll of the open project while the Board is visible. Keep it lean:
   the server already refuses stale writes.
5. A Manage entry in the left rail so Import and Templates are reachable
   outside the portfolio "More" menu.

### A7. Real device and screen-reader checks (Aly, with a Codex checklist)

Codex writes a 20-minute checklist; Aly runs it:

- one Android phone in Chrome and one iPhone in Safari if available: sign in,
  open Home, open a task, use "Move to" on the Board, add a task with Capture;
- one tablet: a long press drag on the Board;
- Windows with NVDA (free): sign in, reach the Board, open a task, hear the
  page title announced on each screen;
- desktop browser zoom at 200%.

Codex fixes what the run finds, one ticket per problem.

### A8. Option 8: the `tmp*` folders in Aly's checkout (Aly, Codex advises)

`git status` in Aly's checkout prints about 35 warnings "could not open
directory 'tmpXXXX/': Permission denied". Where they came from is unverified.
Nothing in the tests creates folders in the repository root, apart from
`tmp_ui_accept` from the fixture server, which is gitignored.

Steps for Aly in PowerShell from the checkout (commands unverified on Aly's
machine):

```powershell
Get-ChildItem -Force -Directory -Filter "tmp*" | Select-Object Name, CreationTime, LastWriteTime
icacls .\tmpXXXX
```

If a folder's owner is another account (for example a sandbox user), take
ownership only after deciding to remove it:

```powershell
takeown /f .\tmpXXXX /r /d y
icacls .\tmpXXXX /grant "${env:USERNAME}:(OI)(CI)F" /t
```

Then look inside. If they hold only temporary test data, zip them to a folder
outside the repository, delete them, and run `git status` again to confirm the
warnings are gone. Do not delete anything before looking. Codex should not
touch Aly's disk without Aly's go-ahead.

### A9. Option 6: PR #4, then this branch into `main` (Aly decides, Codex prepares)

Facts:

- PR #4 (`claude/excel-import`, draft, head `5adec82`) is contained in this
  branch. This branch is 124 commits ahead of it.
- Aly held PR #4 for "more work" on 2026-09-23 and skipped the topic on
  2026-09-25 ("skip this for now ... we will come back to it later",
  ts 1790303433.881399). The extra work was never specified.
- `main` is `c841526` and has two ticket files this branch lacks (WT5TCK,
  0RSY5C, from PR #3).
- PR #4's own tests would need `expected_revision` updates if it were changed
  on its own branch (from the 2026-09-23 notes, unverified).

Recommended path (Q2 in `OPEN_QUESTIONS.md`):

1. Aly names the extra import work, or accepts 3NT40T (Excel import hardening
   follow-ups, already in todo) as that work. Codex does it on this branch, not
   on `claude/excel-import`, so nothing has to be merged back. Check each of
   3NT40T's seven items first: item 3 (XML-illegal characters) looks fixed by
   `c295bb7`, and item 6 (formula-prefixed CSV cells) by `d295d78` for the
   template and report CSVs and `ad068b6` for the task export (unverified
   item by item).
2. Codex runs a trial merge of this branch into `main` in a scratch clone
   (a full, non-shallow clone), reports any conflicts, and runs the full
   suite on the merge result.
3. Aly merges PR #4 as it is (it is a strict ancestor of this branch), or
   closes it as superseded. Either way, the order Aly set (PR #4 first) holds.
4. Codex opens a pull request from `codex/migration-safety-remediation` into
   `main` with a description listing the tickets, schema v20, the test count
   and the review history. Codex runs an adversarial review of the merge
   result before marking it ready.
5. Aly merges it. Codex does not merge unless Aly says so for that pull
   request.
6. After the merge, Aly decides the branch for the next work (Q18).

Done when: `main` contains this branch, the suite is green on `main`, and PR #4
is merged or closed.

### A10. Leftover remote branches (Aly decides, optional)

`claude/hs3jry-complete` can go now that PR #1 is merged. `claude/gantt-steps`
and `claude/hs3jry-followup-tickets` are merged. `claude/review-report-2026-09-22`
has tickets (EBSJ4J, N4KQBB, T81ZV6, GDPJD1, VTEM1V, JE5W89) that are partly
overtaken: N4KQBB and EBSJ4J by 3M2AYA, T81ZV6 by A836XC (from the memory
notes; unverified). Bring what is still relevant onto the main board, then
delete the branch. Nothing is deleted without Aly's word.

**Phase A done when:** signoff is cleared, the open questions are answered, the
small fixes and chosen leftovers are in, first-login password change works, the
real-device check has run, and `main` holds everything.

**Depends on:** Aly's time for signoffs and answers. Phase A is mostly waiting
on Aly, so Codex should prepare the trial merge and the checklists early.

**Risks:** signoff finds problems that send tickets back; the merge into `main`
conflicts; scope creep from new feature ideas. Hold new features for after the
pilot unless Aly says otherwise.

---

## Phase B — Hardening

**Scope.** Make the app safe to put on the internet.

**In.** Security review, dependency audit, backup and restore of SQLite,
migration safety, performance at realistic sizes, accessibility, error
handling and logging.

**Out.** New features. A production WSGI or ASGI server is out unless the
hardening review decides the standard library server cannot be made safe
enough behind Caddy (Q22).

### B1. Security review (Codex, independent reviewer)

Run the same adversarial review shape used for locks #9 to #13 against the whole
app, not just a diff:

- Authentication: sessions (12 hours, token digest stored), CSRF header check on
  every write, cookie flags with `ASTRA_SECURE_COOKIES=1`, logout and logout-all,
  password reset paths, the dummy-hash timing check.
- Authorization: walk every route in `web.py` against the permissions table in
  `HANDOFF_2026-09-26.md` section 6 for each role, including a signed-out
  request.
- Input: the 1 MB JSON limit, the 5 MB import limit, the xlsx reader (zip and
  XML handling), CSV formula neutralisation, `Content-Length` handling.
- Output: CSP and headers on every response type, including errors and
  downloads. `_download` and `_csv` set `nosniff` and `no-store` but not the
  CSP or `X-Frame-Options`; check whether that matters.
- Server: `ThreadingHTTPServer` has no request timeout. Add a socket timeout on
  the handler (a class attribute `timeout` on the request handler is the usual
  way; verify) so a slow client cannot hold a thread forever.
- Proxy: decide how the app should see the real client address behind Caddy.
  Today `login_attempts.ip` will always be `127.0.0.1`. Either read
  `X-Forwarded-For` only when the peer is `127.0.0.1`, and take the rightmost
  entry (the one Caddy appended), never the leftmost; or accept that Caddy's
  access log is the record of client addresses.
- Rate limiting: the app has none by Aly's choice. Plan it at the proxy
  (phase D, 6BXYJZ).
- Secrets: the app has none today (no API keys); keep it that way.

Done when: findings are fixed or accepted by Aly, and a short security note is
added to the repository.

### B2. Dependency audit (Codex)

Astra has no runtime dependencies on Linux and `tzdata` on Windows. The build
needs `setuptools>=75`. Tasks: confirm with `pip list` in a fresh venv; record
the Python version used (3.11 or newer); confirm the self-hosted Inter font
licence file ships (`static/fonts/Inter-OFL.txt`); note that Node is used only
by the tests. Re-run whenever a dependency is added.

### B3. Backup and restore of SQLite (Codex, ticket TRPV3J; Aly's policy is settled)

Aly's policy (2026-09-20): nightly encrypted, SQLite-consistent backup to OCI
Object Storage within the free allowance, plus an encrypted copy on Aly's
desktop; RPO 24 hours; RTO 4 hours; keep 7 daily, 4 weekly and 3 monthly; only
Aly controls restore credentials; prove both restore directions (Oracle to
desktop, desktop to a new Oracle VM) before go-live.

Tasks:

1. Add an `astra backup --to <file>` command that uses SQLite's online backup
   API (`sqlite3.Connection.backup` in the standard library) and then runs
   `PRAGMA integrity_check` on the copy. This was tried on a scratch database in
   this handoff and produced a copy at schema v20 with integrity "ok". Never
   copy the live `.sqlite3` file with `cp`, because the WAL file may hold
   recent writes.
2. Add `astra restore --from <file>` or document a manual restore: stop the
   service, move the old database aside, copy the backup in as
   `astra.sqlite3`, start the service, and let migrations run if the backup is
   older.
3. Encryption: encrypt to Aly's public key (with `age`, or gpg if Aly
   prefers, Q10) so the server can write backups but not read them. Aly keeps
   the private key.
4. Retention: date-stamped names plus Object Storage lifecycle rules, or a
   pruning script (see `DEPLOYMENT_RUNBOOK.md` stage 11).
5. Tests: backup of a database under concurrent writes; restore into a fresh
   `ASTRA_HOME`; a restored older backup migrates forward.
6. A restore drill, written down with times, in both directions.

Done when: a restore from an encrypted off-host backup has been done and timed.

### B4. Migration safety (Codex)

The migration registry is already atomic per step, and every step has fault and
retry tests. Remaining tasks: a rehearsal script that copies a production
backup, runs the new code against the copy and compares row counts per table;
a rule in the release checklist that every upgrade starts with a backup,
because a newer schema refuses older code (`db.py`: "Database was created by a
newer Astra version."); keep the README's refusal instructions for v14, v15
and v16 current.

### B5. Performance at realistic sizes (Codex)

Known numbers: a 200-task bulk change in a 1000-task project took 33 s under
the write lock before `89e9229` and about 0.2 s after it. Tasks: seed a
database with the pilot's expected size and some headroom (for example 20
projects, 3,000 tasks, 30 users, a year of events; Aly to confirm the numbers,
Q20); time the Home, portfolio, Board, My Work and Inbox loads and the export;
run several writers at once and check that nobody gets "database is locked"
within the 30 s busy timeout; add indexes where a query scans (the
`login_attempts.attempted_at` index is already a known follow-up); record the
results in the repository.

### B6. Accessibility (Codex, with Aly's device run from A7)

Target WCAG 2.2 AA (decided 2026-09-20). Tasks: fix what the A7 run found;
re-run the scratch Playwright audit used in lock #11 at 360, 390, 768, 1024 and
1440 px; check keyboard-only use of every screen; check the colour contrast of
any new UI.

### B7. Error handling and logging (Codex)

Today unhandled errors return 500 "Internal server error." and write one
`log_error` line to stderr; the access log is the standard library's line per
request. Tasks: a log line format that includes time, method, path, status and
duration but never passwords, tokens or request bodies; a request id in the 500
response and the log line so Aly can report it; make sure systemd's journal
keeps enough and rotates (phase D); a friendly page in the front end for 500s
and for "server unreachable".

**Phase B done when:** the security review is closed, backup and restore are
proven, the performance and accessibility results are recorded, and logs are
useful without leaking anything.

**Depends on:** phase A merged into `main` (or at least frozen on this branch).

**Risks:** the review finds that the standard library server needs replacing,
which adds a dependency and work; backup to Object Storage needs OCI credentials
on the VM, which Aly must set up.

---

## Phase C — Release engineering

**Scope.** Make releases repeatable and checkable.

**In.** CI, versioning and a changelog, the release tag flow, the merge to
`main`.

**Out.** Automatic deployment to the server. Deployment stays a manual,
runbook-driven step that Aly starts.

### C1. Continuous integration (Codex)

Add `.github/workflows/tests.yml` that runs on pushes and pull requests:

- `actions/checkout`, `actions/setup-python` with Python 3.11 and the newest
  supported version, and Node for the driver tests (the runner image usually
  has Node; pin it with `actions/setup-node` to be sure);
- `python -m pip install -e .`;
- `python tests/run.py`;
- `node --check src/astra/static/app.js`;
- a check that no tracked file has CR line endings and that no `.sqlite3`,
  `.env` or key file is tracked.

The full suite takes about 11 minutes, so a timeout of 30 minutes is safe.
GitHub Actions minutes for a public repository are free as far as we know
(unverified; check the repository's Actions settings). Aly may need to enable
Actions for the repository.

### C2. Versioning and a changelog (Codex)

- The package is `0.1.0` in `pyproject.toml`, and the server says
  `Astra/0.1`. Recommended: `0.2.0` for the first pilot release (Q12 in
  `OPEN_QUESTIONS.md`), then semantic versions: patch for fixes, minor for features
  or a schema step.
- Add `CHANGELOG.md` with one section per release: features by ticket, the
  schema version, migration notes, and the test count.
- Add `astra --version` (argparse `version` action) reading the package
  version, so the server can report what it runs.

### C3. Release flow (Codex prepares, Aly approves)

1. Work lands on `main` through pull requests Aly merges.
2. When `main` is ready for a release: CI green, changelog updated, version
   bumped in one commit.
3. Tag the commit `v0.2.0` (annotated tag) and push the tag. No force-push of
   tags.
4. The server deploys a tag, never a branch head (`DEPLOYMENT_RUNBOOK.md`).
5. A fix for production goes to `main` first, then a new patch tag.

### C4. The merge to `main`

This is task A9. After it, `main` becomes the release branch and feature work
happens on short branches merged by pull request, if Aly agrees (Q18). Until
Aly says otherwise, the branch rule stays: only
`codex/migration-safety-remediation`.

**Phase C done when:** CI runs on every pull request, `v0.2.0` is tagged on
`main`, and the changelog describes it.

**Depends on:** A9 (merge) and phase B fixes.

**Risks:** CI time; flaky UI driver tests under a different Node version. Pin
versions.

---

## Phase D — Deployment to Oracle Cloud Always Free

**Scope.** Put the tagged release on an Oracle Always Free VM behind Caddy with a
DuckDNS name, with backups and monitoring, at zero cost. The step-by-step
commands are in `DEPLOYMENT_RUNBOOK.md`.

**In.** Provisioning, OS hardening, a service user, Python, systemd, Caddy HTTPS
reverse proxy, how the app binds, `ASTRA_HOME`, first-owner init, backups with
an off-box copy, monitoring and uptime, the update and rollback procedure, cost
guardrails.

**Out.** Hosted file uploads, email, a second server, a paid domain.

### What the app supports today, and what it does not

| Need | Today | Task if missing |
| --- | --- | --- |
| Bind to loopback only | `astra serve --host 127.0.0.1 --port 8765` | none |
| Secure cookie over HTTPS | `ASTRA_SECURE_COOKIES=1` | none |
| CSRF protection | `X-CSRF-Token` header plus `SameSite=Strict` cookie | none |
| Data folder | `ASTRA_HOME` | none; always set it on Linux |
| Real client IP behind a proxy | Not supported; the app sees `127.0.0.1` | B1 decision; Caddy logs the real IP |
| Rate limiting of sign-in | Not supported by design | Caddy or fail2ban (D6) |
| Request timeouts | Not set | B1 |
| Health check | No endpoint; `GET /` returns 200 without sign-in | Optional `/healthz` later |
| `HEAD` requests | Not handled (the standard library answers 501) | Use `GET` in monitors |
| Backup | No command | B3 |
| Version report | No command | C2 |
| Attachment links | Off unless `ASTRA_ATTACHMENT_ROOTS` is set | Leave off on the server until MXY7BG |
| Trusted host check | None | Caddy only forwards the DuckDNS name |

### Tasks

D1. Provisioning (Aly does the account steps; Codex guides): OCI account and
home region; an Always Free shape that is actually available; Ubuntu LTS (24.04
recommended because Astra needs Python 3.11 or newer; verify the image's Python
version); a public IP; SSH key only.

D2. Network: OCI security list or network security group open for 22 (Aly's
address only, per the 2026-09-20 decision), 80 and 443. Check the host firewall on the image as
well.

D3. OS hardening: updates, unattended security upgrades, SSH without passwords
or root login, a firewall, fail2ban for SSH.

D4. Service user and folders: a system user `astra` with no login shell;
`/srv/astra/data` for `ASTRA_HOME` (owned by `astra`, mode 700);
`/srv/astra/backups` (owned by `astra`, mode 750, group-readable by the admin
user for `scp` of encrypted files); `/opt/astra/app` owned by root,
world-readable.

D5. Python and the app: `python3-venv`; clone the repository at the release tag
into `/opt/astra/app`; a venv; `pip install .`; `astra --help` works.

D6. systemd: a unit that runs
`/opt/astra/app/.venv/bin/astra serve --host 127.0.0.1 --port 8765` as `astra`
with `ASTRA_HOME=/srv/astra/data`, `ASTRA_SECURE_COOKIES=1` and
`PYTHONUNBUFFERED=1` (so the start line reaches the journal),
`Restart=on-failure`, and sandboxing (`NoNewPrivileges`, `ProtectSystem=strict`,
`ReadWritePaths=/srv/astra/data`, `PrivateTmp`, `ProtectHome`).

D7. DuckDNS: Aly creates the subdomain and keeps the token; a small cron job on
the VM keeps the IP current (the token lives only in a root-owned file on the
VM).

D8. Caddy: installed from the official packages; a Caddyfile with the DuckDNS
name and `reverse_proxy 127.0.0.1:8765`; automatic HTTPS; an access log;
request body limits a little above Astra's own (5 MB imports); rate limiting on
`/api/login` if Aly agrees (Q11), through fail2ban on Caddy's log or a Caddy
module (verify what the installed Caddy supports).

D9. First owner: `astra init-owner` on the VM as the `astra` user with
`ASTRA_HOME` set, run by Aly (Aly types the password).

D10. Backups: the `astra backup` command from B3 on a nightly timer; encrypt to
Aly's public key; upload to OCI Object Storage; weekly copy down to Aly's
desktop; retention; a first restore drill.

D11. Monitoring: an external uptime check of `https://<name>.duckdns.org/`
(expects 200); a disk-space check; `journalctl` retention; a weekly look at
OCI tenancy notices (idle reclamation, capacity).

D12. Update and rollback: back up, check out the new tag, reinstall, restart,
smoke-test; roll back by checking out the old tag and restoring the pre-upgrade
backup when the schema changed.

D13. Cost guardrails: only Always Free resources; an OCI budget with an alert
at a very small amount; no paid upgrade; storage use checked monthly against the
free allowance.

**Phase D done when:** the site answers over HTTPS with a valid certificate, the
cookie is `Secure`, the service survives a reboot, a backup has been restored
into a fresh instance, the uptime check alerts, and the monthly cost is zero.

**Depends on:** phases A to C; Aly's OCI account, DuckDNS name and token, and
the answers to Q7, Q10, Q11 and Q19 to Q21.

**Who:** Aly for every account, credential, DNS and payment screen, and for
typing passwords. Codex for scripts, config files, the runbook and verification.
Nothing is provisioned until Aly says so.

**Risks:** Always Free capacity may not be available in the home region; an idle
instance may be reclaimed; the DuckDNS token leaking; Caddy failing to get a
certificate if ports 80 and 443 are closed; filling the boot volume with logs or
backups.

---

## Phase E — Distribution and onboarding

**Scope.** Get the first real users in, safely, and give them what they need.

**In.** Inviting users, an owner and admin guide, a user quick-start, a support
and feedback channel, a privacy note, the free-app positioning, the announcement.

**Out.** Self sign-up, email invitations, single sign-on, a public marketing
site.

### Tasks

E1. Pilot roster (Aly): the first small group, their global roles and project
memberships, following the minimum-access rule. Start with test projects, not
real private data, then real projects once Aly is happy.

E2. Inviting a user (Aly, in the People screen), per the 2026-09-20 sharing
plan: create the account with a unique temporary password; give the minimum
role and project memberships; send the temporary password through a separate
channel from the URL; the user signs in and is made to change the password
(A5); the user checks their name, projects and role.

E3. Owner and admin guide (Codex writes, Aly reviews): creating users and
project access; secondary owners; resetting passwords (in the app, and
`astra reset-password` on the server); approving requests in the Inbox; WIP
limits; templates; Excel import; closing a project; what the audit history
shows; `astra transfer-primary`; backups and restore in plain words.

E4. User quick-start (Codex writes, Aly reviews): one page with screenshots:
signing in, Home, My Work, opening a task, submitting work, the Board and
"Move to", what "Needs a new assignee" means, who to ask for help.
Serve it as a static page from Astra so it needs no other site, or keep it
as a PDF Aly sends. Keep it short.

E5. Support and feedback channel (Aly decides, Q9): one place for questions and
bug reports; a "Help" link in the account menu pointing there.

E6. Privacy note (Codex drafts, Aly approves): what Astra stores (name, email,
password hash, the tasks and history users create, sign-in attempts for 90
days), where (Aly's Oracle tenancy, home region), who can see what, how long,
backups, how to ask for an account to be removed. No tracking and no
third-party requests (the font is self-hosted). Link it from the sign-in page.

E7. Free-app positioning (Aly): Astra is free for the invited group; no paid
tier; lean by design; no guarantee of uptime on a free host. Put one line on the
sign-in page if Aly wants.

E8. Announcement (Aly): a short message to the pilot group with the URL, how the
password arrives, the quick-start, the support channel, and what to expect in
the first weeks.

**Phase E done when:** the pilot group has signed in, changed their passwords,
and used Astra for real work for two weeks with issues tracked.

**Depends on:** phase D live and A5 (password change) built.

**Risks:** passwords sent insecurely; users confused by governed flows (requests
instead of direct changes); support load on Aly. Keep the group small at first.

---

## Phase F — Operate

**Scope.** Keep Astra running and recoverable.

**In.** An incident checklist, routine maintenance, data export.

### F1. Incident checklist (Codex writes into the repository; Aly keeps a copy offline)

1. Is it down for everyone? Check the uptime monitor and open the URL.
2. SSH in. `systemctl status astra caddy`; `journalctl -u astra -n 200`;
   `journalctl -u caddy -n 200`; `df -h`.
3. Restart what is down: `sudo systemctl restart astra` (or `caddy`).
4. Certificate trouble: check that ports 80 and 443 are open and the DuckDNS IP
   is current.
5. "Database is locked" or a corrupt database: stop the service, take a copy of
   the files, run `PRAGMA integrity_check` on the copy, restore the latest good
   backup if needed.
6. Instance reclaimed or lost: create a new VM from the runbook, restore the
   latest off-host backup, point DuckDNS at the new IP.
7. Suspected account compromise: reset the password (`astra reset-password`
   signs the user out everywhere), check the task and user history, deactivate
   the account if needed.
8. Write down what happened, when, and what was done; tell the users.

### F2. Routine maintenance

- Weekly (Aly, 10 minutes): uptime history, disk use, last backup date, copy the
  latest backup to the desktop, OCI notices.
- Monthly: apply OS updates and reboot in a quiet hour; check storage against
  the free allowance; review user accounts and deactivate leavers.
- Quarterly: a full restore drill into a scratch folder or VM, timed against the
  4-hour RTO.
- Every release: backup, upgrade, smoke test, changelog.

### F3. Data export

Today: tasks as CSV or JSON through `GET /api/export` (the portfolio "Export
CSV"), final results as CSV, import reports as CSV. The whole database is the
backup file. Tasks: a documented "export everything" for Aly (the encrypted
backup plus a CSV per project); a way to export one user's data if someone asks
(privacy note); keep exports scoped to what the requester may see, as today.

**Phase F done when:** the checklist is in the repository, the first quarterly
drill has passed, and maintenance has run for a month without surprises.
