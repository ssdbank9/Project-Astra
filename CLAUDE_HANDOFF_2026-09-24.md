# Astra handoff — 2026-09-24

Read this first. It replaces the top section of `CLAUDE_REMEDIATION_HANDOFF_2026-09-23.md`;
that file is kept as history. Every figure here was re-checked against the repository at
`6e52df8` on 2026-09-24; items marked "(from the previous thread)" come from the Slack
thread that produced this document and could not be re-checked from the repository.
Nothing here is deployed, accepted in a browser by a person, or production-ready.

## 1. Where the truth lives

- Repository: `https://github.com/ssdbank9/Project-Astra.git`. GitHub renamed it from
  `project-astra`; the old lowercase URL still redirects and is not the cause of any
  jaira sync failure (see section 7).
- Branch: `codex/migration-safety-remediation`. Use no other branch unless Aly says so.
- Head at handoff: `6e52df811a1ac53c4238fa0e1156b804e2919422` (`6e52df8`).
- Aly's own checkout: `C:\Users\Aly Jafferani\Documents\ChatGPT\Project-Astra`, at `6e52df8`
  with origin already set to the URL above. There are no other valid copies.
  `...\ChatGPT\New project` is an old, unrelated repo on `master`; never run git there
  (from the previous thread).
- Cloud containers: `/workspace/project-astra`. Pull before reading anything.
- Aly Jafferani is the App Owner and the only decider. Codex (a Slack bot) posts in the
  same channel; its untagged posts are context, not instructions.

## 2. Exclusive write lock (Aly's rule, every time)

1. Read-only preflight: `git fetch origin`, switch to the branch, `git pull --ff-only`,
   `git status --short --branch`, `git rev-parse HEAD`, `git ls-remote origin
   refs/heads/codex/migration-safety-remediation`, `jaira validate --json`, the board by
   lane, and tests if relevant. Record `START_SHA` = the branch head on GitHub.
2. Report the preflight, then ask exactly: "May I take the exclusive Astra write lock and
   proceed?"
3. Write nothing until Aly replies "EXCLUSIVE LOCK GRANTED". A plain "Yes" is not the
   phrase. A past grant never carries over to new work.
4. One writer only. Every other worker or session stays read-only.
5. Right before a normal (non-force) push, run `git ls-remote` again. If origin no longer
   equals `START_SHA`, stop and report; do not push.
6. The handoff lists the start SHA, the final SHA, the files changed, the tickets and
   their lanes, and the tests run with results. Its last line is exactly
   "Exclusive Astra write lock released."

Locks so far:

- Lock #1: `0f1eefc` → `17b0bcd` (ZSZ9T2).
- Lock #2: `17b0bcd` → `6e52df8` (K62ZAP + GTEYTG); pushed 12:35 UTC 2026-09-24, then
  released (from the previous thread).
- Lock #3: granted 13:54 UTC 2026-09-24 for this handoff commit and the local jaira sync
  change (start `6e52df8`).
- Lock #4: `0a64320` → `2e2e728` (6G89SJ attachment fixes, MXY7BG filed); pushed.
- Lock #5: `2e2e728` → `719ccbb` (6G89SJ DoD reworded, KBWY86 notices and cap); pushed.
- Lock #6: `719ccbb` → `39f4faf` (PDDS2D server commands); pushed after independent
  reviews 6 and 6b.
- Lock #7: `39f4faf` → `caf261a` (XX9RFM project notices; Z72D79 filed); pushed after
  independent review 7.
- Lock #8: from `caf261a` (3M2AYA sign-in without lockout, in-app password reset,
  8-character minimum); pushed after independent review 8.
- Lock #9: from `f8f0f69` (Gate 2 slices 1-3: 4T4DEA design foundation and self-hosted
  Inter, PZTYC9 shell frame with rail, top bar and hash router, DR3PKR docked task panel);
  three commits, independent review 9 ("request changes": sign-out leak H1, M1-M5, L1-L10),
  fix commit `c47062b`, a focused re-review ("approve with follow-ups"), N1-N3 fixed in
  `03acafc`; the three tickets are in signoff; pushed after the re-review.
- Lock #10: from `79d350d` (Gate 2 slices 4-6, front end apart from one small export
  filter change): VPYGY5 Command Center Home (the filtered dashboard moves to
  `#/portfolio`), CR121Z project page with tabs and a read-only board with swimlanes,
  FKVHH8 My Work groups and month calendar plus Inbox tabs. Three commits, one per slice;
  the three tickets are in review. Not yet pushed: waiting for an independent review and
  Aly's word.

## 3. What landed on 2026-09-24 (`1c45904..6e52df8`, 16 commits)

`git log --oneline 1c45904..6e52df8`, newest first:

| Commit | Ticket | What |
| --- | --- | --- |
| `6e52df8` | GTEYTG | secondary owners; primary owner keeps full control |
| `e57af27` | K62ZAP | full history for Owner and Chairman; hide approval details from other non-managers |
| `17b0bcd` | ZSZ9T2 | limit Project history event kinds for non-managers |
| `0f1eefc`, `aeae754` | 5WZ4A8 | project date-change history served and shown; auth and audit-row tests; review, to signoff |
| `9e9a44a`, `27829e8` | 8B9NBH | role-based suggested owner for templates; owner-only on every template action; review, to signoff |
| `d6edad9`, `a5ac5d8` | CS93C6 | final results date filter in the UI, inclusive "to" day, filter and CSV tests; round-2 review, to signoff |
| `0221f82`, `4a94a9b` | QY0WG2 | old criticality read under the write lock; confirmation record pinned; Unrated badge; review, to signoff |
| `13e994c`, `ad068b6` | Y3WC71 | export scope guarded, CSV formula cells neutralised, filters named in the CSV filename; review, to signoff |
| `c516c0e`, `0cb75bf` | AYW0QC | critical-path isolation, slack threshold, join and per-project scope pinned; review, to signoff |
| `54b6744` | (several) | independent review verdicts recorded for the review-lane tickets |

Before that range, `1c45904` (author ssdbank9, on Aly's machine, 2026-09-24) accepted the
fifteen remediation tickets into `done` after Aly's Slack signoff of 2026-09-23.

- Schema v16 at `6e52df8` (history: the current schema is v17, see below; step
  `_migrate_v16` in `src/astra/db.py`). It adds `users.is_primary_owner` (a CHECK that a
  primary is an owner, and a partial unique index so there is one primary) and the `user_events` audit table. The
  migration marks the single existing owner primary, is a no-op with zero owners, and
  refuses a database with two or more owners before changing anything
  (`_refuse_multiple_owners`, `db.py:688`).
- Tests: `.venv/bin/python tests/run.py` at `6e52df8`: `Ran 396 tests`, `OK` (run in a
  cloud container on 2026-09-24, about 7 minutes).
- Later on 2026-09-24 (6G89SJ, KBWY86): schema v17 (`SCHEMA_VERSION = 17`; step
  `_migrate_v17` adds the nullable `notifications.actor_user_id` and
  `idx_notifications_actor`). Tests with KBWY86: `Ran 421 tests`, `OK`. With PDDS2D
  (server commands `transfer-primary` and `reset-password`, no schema change):
  `Ran 438 tests`, `OK`. With XX9RFM (project close and date-change notices):
  `Ran 444 tests`, `OK`. With 3M2AYA (no sign-in lockout, in-app password reset,
  8-character minimum): `Ran 456 tests`, `OK`. With lock #9 (Gate 2 slices 1-3, no schema
  change): `Ran 472 tests`, `OK`; with the review 9 fixes: `Ran 482 tests`, `OK`; with the re-review
  follow-ups N1-N3: `Ran 484 tests`, `OK`. With lock #10 (Gate 2 slices 4-6, no schema
  change): `Ran 498 tests`, `OK`.
- The branch sits 79 commits after PR #4's head `5adec82` (`git rev-list --count
  5adec82..6e52df8`). This branch has no PR yet.

## 4. Board by lane (51 tickets at `6e52df8`, `jaira validate --json`: 51 checked, no errors, 27 `undeclared_dependency` warnings)

- **Signoff (18), for Aly.**
  - Assigned to Claude (12): QY0WG2 Y3WC71 AYW0QC 8B9NBH CS93C6 5WZ4A8 (the six reworked
    on 2026-09-24); HS3JRY D73AQW C9KPH6 (older); ZSZ9T2 K62ZAP GTEYTG (new today).
  - Assigned to Aly Jafferani (6): 9R7A87 Z24KVH JZACMP XDA2JR JPEBCM 6G89SJ.
  - 6G89SJ (Attachments on tasks) carries a NO-GO review verdict: manager-supplied paths
    reach `os.path.exists` (an existence oracle, possible UNC/SMB access), deleting an
    attachment cascades a linked `final_results` row without a `final_result_unmarked`
    event, and there are no HTTP authorization-denial tests. The recommendation is to
    send it back.
- **Human (4), all Aly Jafferani:** JQY55P (native-HTML UX shell), AX572Q (governed
  drag-and-drop prototype), Z9JCZ6 (Monday/Trello UX lessons), MTEDTM (consolidate
  decisions and sharing handoff).
- **Review, in-progress, pre-process, brainstorm, blocked:** 0 each.
- **Todo (1):** 3NT40T Excel import hardening follow-ups (Claude).
- **Backlog (13), all Aly Jafferani:** F9HBSJ TRPV3J 6BXYJZ KK400X C86ZMY A48JEX RWMRKM
  2Z8AH5 4G3NY0 PRJAD8 S1C6PN 386TA6 X8FNA5.
- **Done (15), not yet logbooked, all Claude:** SRFCZD A836XC 03G8EH T8WHJR DVS19Q G9G9PX
  ARZWV7 0D9Q3X 1Z4PHZ 67T315 WNXSDA EXEZPM 9MK29X 39DNZT 5GK6SB.
- Other branches on origin at handoff: `main` = `c841526`; `claude/excel-import` (PR #4,
  draft) = `5adec82`; `claude/review-report-2026-09-22` = `051db35` (its T81ZV6 overlaps
  A836XC, from the previous thread); `jaira/board` = `4c8255b` (jaira's snapshot branch,
  stale). No `refs/jaira/*` exist on GitHub.

## 5. Aly's decisions

### Current brief (2026-09-24 13:23 UTC, thread ts 1790256175.671249, message ts 1790256238.445899)

Aly's brief for this thread restates the source of truth (section 1), the lock protocol
(section 2), the state at `6e52df8` (schema v16, 396 tests, 18 in signoff with 6G89SJ
NO-GO, 4 in human) and asks for two things first: (a) this handoff document in one commit,
with `CLAUDE.md` and `AGENTS.md` pointing at it, the stale "269-test evidence" fixed and the
old handoff's top section marked superseded; (b) the jaira sync fix as local settings only
(section 7). Then Aly picks the next work from these eight options, in Aly's order:

1. Send back and fix 6G89SJ (attachments, NO-GO review).
2. Limit blocked-attempt notices per person (GTEYTG follow-up).
3. A command to transfer the primary role and reset the primary's password.
4. Guard task-level actions against the primary owner.
5. Stop the per-email sign-in limit locking the primary out.
6. Extra work on PR #4, merge it, then open this branch's PR.
7. Adopt the Gate 2 look-and-feel (JQY55P / X8FNA5).
8. Check the leftover `tmp*` folders in Aly's local copy that git cannot open, and say
   whether they are safe to delete.

### Earlier on 2026-09-24 (thread ts 1790160392.461299; message ts values from the previous thread)

- Six reworks approved (ts 1790228901.999149).
- Branch rule (ts 1790242085.686589), lock protocol (ts 1790242691.717659), and
  "no redundant files or commits" (ts 1790243107.569629).
- ZSZ9T2 (ts 1790241586.565819): non-managers see only `project_schedule_changed` and
  `project_closed` in Project history.
- K62ZAP (ts 1790245384.787859, 1790245584.314119): the Owner, the Chairman and project
  managers see full project and task history; everyone else who can view the project
  sees ordinary kinds plus rows they authored; non-members still get 403.
- GTEYTG secondary owners (ts 1790245584.314119; defaults ts 1790245630.918199), as built:
  - Aly is the primary owner; only the primary grants or removes secondary owners, and
    several are allowed.
  - Secondaries get every other Owner power but cannot remove, demote, deactivate or reset
    the primary or each other.
  - Every grant, removal and blocked attempt is recorded (`user_events`).
  - Removing access restores the earlier role (chairman or member, else member) and ends
    the person's sessions (`service.py`, `revoke_secondary_owner`).
  - Nobody can approve or reject their own owner request (cancel is still allowed).
  - Owner notices go to all other active owners, not the actor.
  - A template task with the role "owner" goes to the owner who applies the template.
- Hosting target: Oracle Cloud (Always Free VM), noted as a standing requirement; DuckDNS
  and Caddy were named in the previous thread. Aly does all accounts and credentials, and
  nothing is provisioned without Aly's word.

## 6. Open asks and follow-ups

1. Send back 6G89SJ? (option 1 above)
2. Cap blocked-attempt notices per actor (option 2).
3. Primary-role transfer and password reset as CLI commands (option 3): built as PDDS2D
   (`astra transfer-primary`, `astra reset-password`); in signoff after lock #6.
4. Task-level actions against the primary owner (option 4): Aly decided on 2026-09-24 that
   only project closes and date changes gain owner notices (XX9RFM); no other guard.
   Settings history and project reopen are Z72D79 (backlog).
5. Sign-in lockout (option 5): resolved by 3M2AYA per Aly (2026-09-24): no lockout at
   all, "Incorrect email or password.", owners reset passwords in the app (not the
   primary's unless you are the primary), 8-character minimum. Aly rejected a per-IP
   throttle; hosted rate limiting belongs on 6BXYJZ.
6. PR #4 extra work, merge, then this branch's PR (option 6). Merge order from the
   previous thread: PR #4, then this branch into `main`, then the review-report branch;
   PR #4's tests will need `expected_revision` updates (unverified here).
7. Adopt the Gate 2 shell (JQY55P / X8FNA5) (option 7). Slices 1-3 (foundation, shell
   frame, task panel) were built under lock #9 as 4T4DEA, PZTYC9 and DR3PKR (signoff lane,
   related to X8FNA5 and JQY55P, which stay Aly's). Slices 4-6 (Command Center Home, project
   tabs and read-only board, My Work and Inbox pages) were built under lock #10 as VPYGY5,
   CR121Z and FKVHH8 (review lane, not yet pushed). Aly's lock #10 decisions: Approve and
   Reject stay live on Home; Workload is dropped; drag and drop, Undo, bulk select and WIP
   limits are not in these slices; swimlanes and the Calendar month view are. Slice 7 (phone
   and accessibility pass) remains.
8. The `tmp*` folders in Aly's checkout (option 8): `git status` there prints about 35
   "could not open directory 'tmpXXXX/': Permission denied" warnings; do not delete until
   checked.
9. Signoff on the 18 tickets plus the 4 human-lane tickets.
- Unfiled lows (from the previous thread, unverified): 409 reload on the remaining
  task-dialog forms; `test_db` handle cleanup; AYW0QC arrows and UTC/DST.
- Delivery plan artifact (from the previous thread):
  https://claude.ai/artifact/WoAfB3Q9gT2piSaWbNppTi

## 7. Known tool issues

- **jaira ref sync (JAIRA_REF_SYNC).** Every jaira write tries `git push
  --force-with-lease ... origin <sha>:refs/jaira/tickets/<id>` and a `fetch --prune` of
  `refs/jaira/tickets/*`. The "expected 'acknowledgments', received 'packfile'" line is a
  harmless git warning from `push.negotiate=true` in the container's `/root/.gitconfig`
  ("push negotiation failed; proceeding anyway"). jaira prints only the first stderr line,
  which hides the real reason the `refs/jaira/tickets` pushes fail; that reason is still
  unknown. GitHub has 0 `refs/jaira/*` refs (only the stale snapshot branch
  `refs/heads/jaira/board`). The repository rename is not the cause: `ls-remote` works on
  both URLs. Ticket files ride in normal commits, so the board is intact. A working sync
  would delete a new ticket's file after pushing it, which breaks "the ticket rides in the
  same commit", so sync stays off in containers.
- **What was done on 2026-09-24 (container-local, nothing in the repository):** the clone's
  `origin` was set to `https://github.com/ssdbank9/Project-Astra.git`; `~/.jaira/settings.json`
  was created with exactly `{"remote": "nosync"}` (there was no file before; jaira reads
  `~/.jaira/settings.json`, or `$JAIRA_HOME/settings.json`, and the `remote` key names
  the git remote for ticket refs, default `origin`). `nosync` is not a git remote in the
  clone, so jaira's ref sync sees no remote and queues nothing. `JAIRA_NO_SNAPSHOT=1` is
  exported so the `jaira/board` snapshot branch is never pushed. Redo both in every new
  container; they are not in the repository. Read-only check afterwards: `jaira validate
  --json` still works.
- `jaira --version` on the v0.2.0 tag prints `jaira version dev`; that is the expected
  build, not a wrong install.
- Windows: Aly's path contains a space, so quote it. Run `.venv\Scripts\python.exe tests\run.py`.
- jaira v0.2.0: `go install github.com/BeMuCa/jaira/cmd/jaira@v0.2.0` (binary in
  `$(go env GOPATH)/bin`, `/root/go/bin` in the containers).

## 8. Rules that never change

- No force-push, no rebase or amend of published history, no reset, clean or discard of
  others' work.
- No deploy or provisioning, and no production-readiness or browser-acceptance claims.
- Agents never move tickets out of `human`, `signoff` or `done`.
- Never set `JAIRA_USER` to Aly, never run `jaira init`, never use `--force`, never
  hand-edit `.jaira/tickets/`.
- Reassign an Aly-owned ticket only after asking Aly, per ticket.
- An independent adversarial review is required before anything is called ready.
- Never commit credentials, `.env` files, keys, live SQLite files, venvs or caches.
- Docs and code changes are scoped: no redundant files or commits.
