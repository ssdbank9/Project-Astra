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
  independent review 10 ("approve with follow-ups", no High: M1 browser-clock "today", M2
  the This week strip against its tile, L1-L8), all fixed in `7bfa045` (not re-reviewed);
  the three tickets are in signoff; pushed after review 10.
- Lock #11: from `46ec9f4` (Gate 2 slice 7, 3C1Z74: the phone and accessibility pass at
  360/390/768/1024/1440 with a scratch Playwright audit, and the leftovers: Open full page
  hidden on touch widths, board lanes by user id, the Gantt today line and portfolio As of
  from the server's today, an SVG favicon, a visible Portfolio Gantt link on Home) in
  `febb3b9`; independent review 11 ("approve with follow-ups", no High: M1 focus could reach
  what the full-screen panel hides, M2 clipped calendar items at tablet widths, L1-L5), all
  fixed in `5d39d19` (not re-reviewed); the ticket is in signoff; pushed after review 11.
  With it Gate 2 is complete (slices 1-7), apart from Aly's signoff.
- Lock #12 (granted 12:56 UTC 2026-09-25, Slack ts 1790341004.453539): from `77fcfce`, the
  post-Gate-2 batch under the JQY55P 2026-09-19 owner decisions, pushed after review 12e.
  Six commits:
  - `a2161a0` JN1QYG board drag and drop, Move to and 15-second Undo (schema v18,
    `tasks.board_rank`), with Aly's on-hold decision (ts 1790342529.695749: a project manager
    puts work on hold directly; leaving hold is still an Owner request).
  - `34eeca1` X07XV4 task locks as 60-second leases and Gantt date drag (schema v19,
    `task_locks`).
  - `50e139d` XV92JJ bulk select with preview and Undo, and work-in-progress limits (schema
    v20, `wip_limits`).
  - One fix commit for independent reviews 12a, 12b and 12c (each "approve with
    follow-ups", no High; one Medium each, all fixed). The dependency rule, the Gantt impact
    confirm and the WIP limit now hold on every path (board, panel, API, bulk, Undo), inside
    the write transaction. That is `55ddf3c`.
  - One fix commit for re-review 12d of `55ddf3c` ("approve with follow-ups": 0 High, 2
    Medium, 2 Low, all fixed). A bulk change reads the board once before and once after its
    writes (a 200-task change in a 1000-task project took 33 s under the write lock, now
    about 0.2 s). Approving a request re-runs the dependency, WIP and date rules at decision
    time and asks the owner to confirm each one; the Inbox and Home request cards show what
    approving would override. Reopen with a new due date and approving a schedule proposal
    ask about date consequences too. That is `89e9229`.
  - A chore commit recording reviews 12a-12e ("chore(JN1QYG, X07XV4, XV92JJ): record reviews
    12a-12e (approve with follow-ups) and move to signoff"). Review 12e of `89e9229` approves:
    0 High, 0 Medium, 1 Low (three revert experiments no test catches, left as follow-ups;
    see section 6, item 10).
  - The three tickets are in signoff, waiting for Aly. Tests: `Ran 639 tests`, `OK`.
    Evidence (screenshots and a short video) lives in the session scratchpad,
    `lock12-shots/`.
- Lock #13 (granted 01:38 UTC 2026-09-26, Slack ts 1790386688.768309): from `d082faf`
  (baseline `Ran 639 tests`, `OK`), **not pushed** at the time of writing. Ticket 3FQEKB,
  assignment rules from Aly's answers to review 12c I3 (ts 1790386228.535829 and
  1790386492.402489): the Chairman may assign tasks and subtasks in any project (the
  assignee only: panel and bulk Assign; `can_assign`, `can_manage_project` unchanged) and is
  never an assignee; a project viewer may be given subtasks only; older assignments that
  break the rules are kept and flagged "Needs a new assignee" (card, List row, panel, Home
  count). Every path follows it: create, panel, bulk, importer (`E_OWNER_CHAIRMAN`,
  `E_OWNER_VIEWER`), hold owner, promotion of a viewer's subtask, templates (the Chairman
  role is no longer offered or filled). No schema change. Three commits: a test-only commit
  closing the three review 12e test gaps (`5e6e593`), the 3FQEKB feature commit (`da414e1`),
  and the review 13a fix commit. Review 13a approved with follow-ups (0 High, 1 Medium, 2
  Low), all fixed: collaborators follow the assignee rules (the Chairman is never one, a
  viewer only on a subtask; older rows are flagged and lose the submit right), the panel
  hides the forms the server refuses for the Chairman and viewers, the Chairman selects in
  the List only, and an empty date no longer demands a reason (an older bug). The ticket
  stays in review. Tests: `Ran 674 tests`, `OK`. Screenshots in the session scratchpad,
  `lock13-shots/`.

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
  change): `Ran 498 tests`, `OK`; with the review 10 fixes: `Ran 503 tests`, `OK`. With lock #11
  (Gate 2 slice 7, no schema change): `Ran 507 tests`, `OK`; with the review 11 fixes:
  `Ran 510 tests`, `OK`. With lock #12 (schema v18 to v20): `Ran 540`, `564` and `586`
  tests after each feature commit, `Ran 619 tests`, `OK` with the review 12a-12c fixes, and
  `Ran 639 tests`, `OK` with the re-review 12d fixes. With lock #13 (3FQEKB and the review
  12e test gaps, no schema change): `Ran 663 tests`, `OK`; with the review 13a fixes:
  `Ran 674 tests`, `OK`.
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
   CR121Z and FKVHH8 (signoff lane, pushed after review 10). Aly's lock #10 decisions: Approve and
   Reject stay live on Home; Workload is dropped; drag and drop, Undo, bulk select and WIP
   limits are not in these slices; swimlanes and the Calendar month view are. Slice 7 (phone
   and accessibility pass, plus the review 9/10 leftovers) was built under lock #11 as
   3C1Z74 (signoff lane, pushed after review 11); Gate 2 (slices 1-7) is complete apart from
   Aly's signoff.
8. The `tmp*` folders in Aly's checkout (option 8): `git status` there prints about 35
   "could not open directory 'tmpXXXX/': Permission denied" warnings; do not delete until
   checked.
9. Signoff on the 18 tickets plus the 4 human-lane tickets.
10. Lock #12 (JN1QYG, X07XV4, XV92JJ in signoff) follow-ups, not built:
    - Closed in lock #13: the three revert experiments review 12e reported as uncaught
      (the undo source-status check, the per-row revision check in `_write_bulk`, member
      checkbox hiding) now have tests. The undo one was already caught: the review's revert
      experiment left a dangling line continuation, so the module failed to import.
    - Not tried on a real touch device (tablet long press), no screen-reader run, and no
      live refresh: lock chips, banners and the Inbox "Approving overrides" lines show the
      last load (the server rechecks at write and decision time).
    - Review 12c I3 answered by Aly on 2026-09-26 and built as 3FQEKB under lock #13.
    - The Blocked WIP exemption: a card that enters Blocked because of a dependency is not
      refused, so a Blocked limit can be exceeded by an added link or a reopened
      predecessor (documented in the README).
    - A manager's accept request on a waiting task is filed, and the owner is asked at
      decision time (not refused at filing). An owner's own board Undo passes the
      dependency override itself (12d I1). The importer and templates bypass the WIP and
      dependency gates (owner-only, 12d I2).
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
