# Astra adversarial review and remediation handoff — 2026-09-23

## Current state after Claude remediation (2026-09-23)

This section supersedes the figures in the sections below it. Those sections are
Codex's original handoff, kept unchanged as history. Where they disagree with
this section (schema v13, 220 tests, 7/7 and 8/8 focused counts, tickets in
`review`, the Windows start sequence), this section is current.

### Branch and range

- Repository: `https://github.com/ssdbank9/Project-Astra`
- Branch: `codex/migration-safety-remediation`, pushed. This section was written in the commit directly on top of `d688a59`;
  `git log -1` shows the current head.
- Base branch: `claude/excel-import`. Merge base: `5adec82`.
- Codex's published work ends at `0ad122e`. Claude's work is `0ad122e..HEAD`.
- Schema target is now **v14** (`SCHEMA_VERSION = 14` in `src/astra/db.py`).
- Not deployed. Not approved for real users. No browser acceptance was done.

Commits after `0ad122e`, newest first (`git log --oneline 0ad122e..HEAD`):

- (this handoff commit, on top of `d688a59`) docs: durable remediation handoff after Claude review
- `d688a59` chore: file follow-up tickets from 2026-09-23 review
- `41797c8` chore(SRFCZD): review verdict, move to signoff
- `41dd6e2` fix(SRFCZD): R6 refuse unapprovable terminal-to-terminal Manager requests; pin guards at the lock
- `9357f10` chore(T8WHJR): record the independent review and move to signoff
- `754cae7` fix(T8WHJR): close the review's upheld gaps in the closed-task rule
- `fc2a35a` fix(T8WHJR): keep closed tasks immutable outside the governed reopen
- `9fb4328` fix(SRFCZD): R5 close re-review gaps: residual status in close matching, guard race tests, flag-reset test, governed generic requests refused
- `fc10595` chore(03G8EH): record the independent review and move to signoff
- `dfccb39` fix(03G8EH): re-check submit permission under the lock; refuse v14 before any step
- `4d18dcb` fix(03G8EH): serialize task submissions and refuse submits against a changed task
- `8723263` fix(SRFCZD): race regressions for in-transaction guards; guard update_task approvals and unmark
- `41deb62` fix(SRFCZD): refuse a close_project approval when the project's open work has changed
- `061a5f5` fix(SRFCZD): record the Owner's decision note when approving a request
- `85bcdcd` fix(SRFCZD): reconcile only pending Owner requests whose intent matches the direct action
- `f005bd1` chore(SRFCZD, A836XC): reassign to Claude; A836XC to signoff, SRFCZD back to in-progress
- `cba46d1` review(SRFCZD, A836XC): record independent review verdicts
- `f54520b` chore: normalize remediation files back to LF line endings

Key commits:

- `f54520b` normalises the files Codex's web upload wrote with CRLF back to LF.
  Because of it, a plain `git diff --stat 0ad122e..HEAD` shows the whole of
  `service.py`, `app.js`, `web.py`, `CLAUDE.md` and this file as changed. Use
  `--ignore-cr-at-eol` (below) to see the real change.
- `cba46d1`, `f005bd1`: first independent verdicts; Aly reassigned SRFCZD and
  A836XC to Claude; A836XC to signoff, SRFCZD back to in-progress.
- SRFCZD rework: R1 `85bcdcd`, R2 `061a5f5`, R3 `41deb62`, R4 `8723263`,
  R5 `9fb4328`, R6 `41dd6e2`, review verdict `41797c8`.
- 03G8EH: `4d18dcb`, `dfccb39`, `fc10595` (schema v14, unique submission
  version, refusal when duplicates already exist).
- T8WHJR: `fc2a35a`, `754cae7`, `9357f10` (closed tasks immutable outside reopen).
- Follow-up tickets: `d688a59`. This handoff: the commit that adds this section.

### Files changed

`git diff --stat --ignore-cr-at-eol 0ad122e..d688a59` (content changes; line-ending-only
files such as `src/astra/web.py` and `src/astra/static/app.js` drop out). The
handoff commit itself also changes this file, `CLAUDE.md` and `AGENTS.md`:

```text
 ...6MSYCG2SRFCZD-harden-task-state-integrity-and-idempotency.md |   51 +-
 ...R2A836XC-make-legacy-sqlite-migrations-atomic-and-retry-s.md |   14 +-
 ...MW03G8EH-serialize-task-submissions-and-refuse-submits-ag.md |   90 ++
 ...TQT8WHJR-keep-completed-cancelled-and-abandoned-tasks-imm.md |   99 +++
 ...PNDVS19Q-db-transaction-leaves-the-connection-inside-an-o.md |   46 +
 ...SFG9G9PX-approving-one-of-two-identical-pending-owner-req.md |   46 +
 ...18ARZWV7-hide-or-disable-task-edits-the-server-refuses-on.md |   47 +
 ...XV0D9Q3X-owner-inbox-show-the-requested-status-and-reason.md |   44 +
 ...TS1Z4PHZ-make-the-xlsx-test-fixture-deterministic-zip-tim.md |   45 +
 ...GS67T315-fault-and-retry-tests-for-every-legacy-migration.md |   46 +
 ...SSWNXSDA-maintainability-schema-level-idempotency-key-and.md |   45 +
 ...S55EXEZPM-maintainability-pass-the-owner-decision-context.md |   44 +
 ...1V9MK29X-maintainability-split-astraservice-update-task-i.md |   43 +
 ...G239DNZT-maintainability-replace-the-repeated-migrate-ver.md |   43 +
 README.md                                                       |   31 +-
 docs/design/authorization-matrix.md                             |   18 +-
 docs/design/excel-import.md                                     |   45 +-
 src/astra/__main__.py                                           |   14 +-
 src/astra/db.py                                                 |   92 +-
 src/astra/importer.py                                           |   69 +-
 src/astra/service.py                                            |  267 ++++--
 tests/test_core.py                                              |   16 +-
 tests/test_db.py                                                |  194 ++++
 tests/test_import.py                                            |  143 +++
 tests/test_state_integrity.py                                   | 1272 ++++++++++++++++++++++++++-
 tests/test_web.py                                               |   81 ++
 26 files changed, 2856 insertions(+), 89 deletions(-)
```

### Defects addressed, per ticket, with the tests that prove them

All test names below are in `tests/`.

**SRFCZD — task state integrity and idempotency** (signoff)

- Stale full-form edits overwrote newer revisions. Now `update_task` needs an
  integer `expected_revision` and a conditional UPDATE; stale is 409 with no
  change. Tests: `test_stale_task_update_is_rejected_without_state_or_event_change`,
  `test_concurrent_task_updates_at_one_revision_have_one_winner_and_one_event`,
  `test_task_update_refuses_when_task_is_cancelled_before_its_write`.
- Completed, cancelled and abandoned tasks accepted ordinary edits. Now refused
  until reopen. Test: `test_terminal_tasks_reject_ordinary_edits_until_reopened`.
- Two synchronized acceptances both succeeded. Now one winner and one event.
  Test: `test_concurrent_acceptance_has_one_winner_and_one_event`.
- Identical protected requests were duplicated and had no decision path. Now they
  dedupe and the Owner can approve, reject or cancel. Tests:
  `test_equivalent_protected_retries_reuse_one_pending_request_and_event`,
  `test_concurrent_equivalent_manager_requests_create_one_pending_request_and_event`,
  `test_concurrent_equivalent_close_requests_create_one_pending_request_and_event`,
  `test_owner_can_decide_requests_and_stale_approval_stays_pending`,
  `test_owner_approval_dispatches_every_supported_protected_action`,
  `test_non_owner_cannot_approve_or_reject_a_request`,
  `test_concurrent_rejections_have_one_winner_and_one_event`;
  HTTP `test_non_owner_decision_on_a_request_returns_403_and_leaves_it_pending`.
- R1: a direct Owner action marked requests with a different intent as approved.
  Now only same-intent requests resolve. Tests:
  `test_direct_status_change_leaves_request_for_another_status_pending`,
  `test_direct_reopen_resolves_only_matching_requests`,
  `test_direct_schedule_decision_resolves_only_the_same_proposal`,
  `test_direct_hold_resolves_only_the_same_checkpoint_and_hold_owner`,
  `test_direct_cancel_leaves_another_managers_abandon_request_pending`,
  `test_direct_close_resolves_only_the_same_residual_set_whatever_the_note`.
- R2: approval stored the Manager's reason as the Owner's note. Test:
  `test_owner_approval_records_owner_decision_note_not_manager_reason`.
- R3/R5: close approval was not stale-checked and close matching ignored residual
  status. Tests: `test_close_approval_refuses_when_open_work_changed_since_request`,
  `test_close_approval_succeeds_when_open_work_is_unchanged`,
  `test_direct_owner_close_with_changed_work_behaves_as_before`,
  `test_direct_close_leaves_request_pending_when_a_residual_status_changed`,
  `test_renamed_residual_work_still_resolves_or_approves_the_close_request`,
  `test_stale_hold_approval_is_refused_and_request_stays_pending`.
- R4/R5/R6: an approval racing a reject applied the action and returned 500.
  Now 409 with nothing changed, for every governed action, with the reject
  landing at the lock. Tests:
  `test_each_action_approval_racing_a_reject_is_refused_without_changing_the_task`,
  `test_status_approval_racing_a_reject_is_refused_without_changing_the_task`,
  `test_close_approval_racing_a_reject_rolls_back_without_closing`,
  `test_failed_approval_clears_the_active_request_for_the_next_action`.
- Repeated final-result marking and concurrent unmark wrote duplicate events.
  Tests: `test_repeated_final_result_marking_emits_only_real_state_changes`,
  `test_concurrent_unmark_final_result_emits_one_event`.
- R5/R6: a Manager could file requests the Owner could never approve (into
  on_hold/completed/reopened, out of submitted, and terminal to
  cancelled/abandoned/changes_requested). Now 400 with no request. Tests:
  `test_manager_generic_update_refuses_governed_targets_and_leaving_review`,
  `test_manager_generic_update_refuses_terminal_to_non_work_targets`; HTTP
  `test_manager_terminal_to_terminal_update_is_400_without_a_request`.

**A836XC — atomic, retry-safe legacy migrations** (signoff)

- Steps v1-v12 used `executescript()`, which commits the surrounding
  `BEGIN IMMEDIATE`; a mid-step failure left half-applied schema. Now each
  statement runs with `execute()` inside the step's transaction. Tests in
  `tests/test_db.py`: `test_user_version_pragma_is_transactional`,
  `test_atomic_statement_runner_handles_quoted_semicolons_and_rejects_incomplete_sql`,
  `test_failure_midway_through_initial_schema_rolls_back_every_object_and_retries`,
  `test_failure_after_legacy_alters_rolls_back_to_v4_then_matches_fresh_schema`,
  `test_failure_after_v12_table_creation_rolls_back_table_and_index_then_retries`,
  `test_fresh_database_migrates_to_the_current_schema`.
- Known limit: committed fault tests cover v1, v5 and v12 only (follow-up
  `67T315`).

**03G8EH — serialized task submissions** (signoff)

- Two simultaneous submits could both win with the same version (handoff 7.2
  below, now reproduced and fixed). `submit_task` re-reads and allocates the
  version under the lock; schema v14 adds a unique `(task_id, version)` index and
  refuses to upgrade when duplicates already exist. Tests:
  `test_concurrent_submissions_have_one_winner_one_row_and_one_event`,
  `test_submit_refuses_when_the_owner_cancels_before_its_write`,
  `test_submit_refuses_when_the_task_is_submitted_and_accepted_before_its_write`,
  `test_submit_refuses_when_the_task_is_reassigned_away_before_its_write`,
  `test_submit_refuses_when_the_collaborator_is_removed_before_its_write`,
  `test_submit_refuses_when_project_access_is_revoked_before_its_write`;
  `tests/test_db.py`: `test_fresh_v14_database_refuses_a_second_submission_at_one_version`,
  `test_v13_database_with_submissions_upgrades_to_v14_and_matches_fresh_schema`,
  `test_v13_duplicate_submission_versions_refuse_the_upgrade_without_touching_data`,
  `test_failure_creating_the_v14_index_rolls_back_to_v13_and_retries`,
  `test_duplicates_in_an_older_database_refuse_before_any_step_runs`,
  `test_serve_exits_with_the_refusal_message_instead_of_a_traceback`.

**T8WHJR — closed tasks immutable outside reopen** (signoff)

- Import, re-parenting, criticality, schedule proposals and approvals,
  dependencies and reviewers still changed closed tasks, and the README claimed
  otherwise. Now each is refused (400, or 409 when the task closes mid-write);
  import rows for closed tasks are skipped with `W_CLOSED_TASK`; README rewritten.
  Tests: `test_closed_task_refuses_structural_and_schedule_writes_until_reopened`,
  `test_writes_refuse_when_the_task_closes_before_their_write`,
  `test_schedule_approval_refuses_when_the_task_closes_before_its_write`,
  `test_closed_task_writes_work_again_after_the_governed_reopen`,
  `test_closed_task_may_be_a_predecessor_and_still_takes_evidence`,
  `test_update_task_on_a_closed_task_with_no_change_writes_nothing`;
  `tests/test_import.py`: `test_import_row_for_a_closed_task_is_skipped_for_either_role`,
  `test_closed_row_neither_forms_false_cycles_nor_poisons_other_rows`,
  `test_import_commit_refuses_when_the_task_closed_after_the_preview`.

### Test results measured on 2026-09-23 at `41dd6e2`

- Full suite `.venv/bin/python tests/run.py`: **Ran 269 tests, OK** (281.9 s).
- `test_state_integrity`: 45/45 OK. `test_web`: 45/45 OK.
- `node --check src/astra/static/app.js`: clean.
- `.venv/bin/python -m compileall -q src tests`: clean.
- `git diff --check origin/claude/excel-import...HEAD`: clean at `41dd6e2`. After
  `d688a59` it reports only "new blank line at EOF" in the ten new ticket files:
  that is the format `jaira create` writes (older backlog tickets such as
  `3NT40T` have it too), and ticket files are not hand-edited. Source, tests and
  docs are clean.
- Mutation check: moving `_assert_active_request_revision` in `accept_submission`
  to just before its `with transaction` makes
  `test_each_action_approval_racing_a_reject_is_refused_without_changing_the_task`
  fail; restored afterwards.
- Known flake: `test_import.test_commit_refuses_a_plan_that_changed_since_the_preview`
  fails about 1 run in 10 (fixture zip timestamps; follow-up `1Z4PHZ`). It
  passed in the run above.

### Jaira state

| Ticket | Title | Lane |
| --- | --- | --- |
| `SRFCZD` | Harden task state integrity and idempotency | signoff (waiting for Aly) |
| `A836XC` | Make legacy SQLite migrations atomic and retry-safe | signoff (waiting for Aly) |
| `03G8EH` | Serialize task submissions and refuse submits against a changed task | signoff (waiting for Aly) |
| `T8WHJR` | Keep completed, cancelled and abandoned tasks immutable outside reopen | signoff (waiting for Aly) |

Follow-up tickets filed from this review (backlog, assignee Claude, tag `astra`,
not started):

| Ticket | Title | Kind |
| --- | --- | --- |
| `DVS19Q` | db.transaction() leaves the connection inside an open transaction when COMMIT fails | confirmed defect (MIG-7), reproduced |
| `G9G9PX` | Approving one of two identical pending Owner requests leaves the other pending | confirmed defect (SEM-3), reproduced |
| `ARZWV7` | Hide or disable task edits the server refuses on closed and submitted tasks | UI follow-up |
| `0D9Q3X` | Owner inbox: show the requested status and reason, and reload the task after a 409 | UI follow-up (includes SVC-5) |
| `67T315` | Fault and retry tests for every legacy migration step v1-v12 | test gap (A836XC gap 1) |
| `1Z4PHZ` | Make the xlsx test fixture deterministic (zip timestamps flake an import test) | test flake (IMP-8), cause confirmed |
| `WNXSDA` | Maintainability: schema-level idempotency key and indexed lookup for pending Owner requests | maintainability |
| `EXEZPM` | Maintainability: pass the Owner decision context explicitly instead of _active_owner_request_id | maintainability |
| `9MK29X` | Maintainability: split AstraService.update_task into policy, validation and persistence helpers | maintainability |
| `39DNZT` | Maintainability: replace the repeated migrate() version blocks with a step registry | maintainability |

Related ticket not on this branch: `T81ZV6` on `claude/review-report-2026-09-22`
(migration atomicity, user_version re-read under the lock, concurrent-migration
test). Its atomicity part is done here by A836XC; reconcile it when that branch
is merged.

### Remaining gaps and unverified areas

Confirmed gaps (each has a follow-up ticket above):

- `db.transaction()` leaves the transaction open when COMMIT itself fails.
- Approving one of two identical pending requests leaves the other pending (SEM-3).
- The task dialog still offers edits and statuses the server refuses on closed
  and submitted tasks; the Owner inbox does not show the requested status or the
  reason; a 409 does not reload the task.
- Migration fault tests cover v1, v5 and v12 only.
- Import test fixture is time-dependent (one flaky test).
- Maintainability: no schema-level idempotency key; Python-side JSON filtering of
  requests; mutable `_active_owner_request_id`; long `update_task`; repeated
  `migrate()` blocks.

Not verified at all:

- No live browser acceptance (the checklist in section 10 below still applies).
- No deployment, HTTPS or security hardening, backup and restore, load testing,
  monitoring, multi-user or multi-process operation, password recovery, or
  disaster recovery.
- No private-source ingestion, notifications, real-file publication, or external AI.

### Decisions Aly made in this run

- SRFCZD and A836XC were reassigned to Claude.
- Closed tasks are immutable except attachments and final-result marking; any
  other change goes through the governed reopen.
- Import rows that target a closed task are skipped with a warning.
- Pushing reviewed ticket fixes to this branch was approved.

### Decisions Aly still has to make

1. Signoff on each of SRFCZD, A836XC, 03G8EH and T8WHJR: accept, or send back.
2. Whether and when to merge this branch.
3. Merge order: PRs #3, #2 and #4 on the base side (`claude/excel-import`) come
   first, then this branch.

### How the next agent continues

```bash
cd /workspace/project-astra            # or your clone
git fetch origin
git switch codex/migration-safety-remediation
git status --short --branch            # expect clean, up to date with origin
git log --oneline -5
.venv/bin/python tests/run.py          # expect 269 tests OK (about 5 minutes)
jaira validate --json
jaira resume
jaira list --actionable --json
```

On Windows use `.venv\Scripts\python.exe tests\run.py`.

Do not:

- move any ticket out of `human` or `signoff`, or mark anything done;
- force-push, rebase published commits, reset, clean or discard work;
- run `jaira init` or use `--force`; hand-edit `.jaira/tickets/`;
- deploy, or claim production readiness or browser acceptance;
- set `JAIRA_USER` to Aly.

Every Jaira write prints `gitref: expected 'acknowledgments', received 'packfile'`.
That is the refs/jaira push failing; it is known and harmless because ticket
files ride in normal commits.

Pick up the follow-up tickets in this order (highest severity first):

1. `DVS19Q` — a failed COMMIT leaves the connection holding the write lock.
2. `G9G9PX` — stale duplicate requests stay in the Owner inbox.
3. `ARZWV7` — UI offers edits the server now refuses.
4. `0D9Q3X` — Owner decides blind; no reload after 409.
5. `67T315` — migration regressions in v2-v4 and v6-v11 would pass the suite.
6. `1Z4PHZ` — one import test flakes about 1 run in 10.
7. `WNXSDA`, `EXEZPM`, `9MK29X`, then `39DNZT` (after `67T315`, so its tests
   guard the refactor). All four are maintainability, not defects.
8. The older `3NT40T` (Excel import hardening follow-ups, todo) is also open.

---

*Everything below is Codex's original handoff (history).*


Prepared for Aly Jafferani and the next Claude Code review session.

This is the current implementation handoff for the adversarial review and the
first two remediation packages. It supplements the older product and execution
handoffs; where a branch, commit, test count, ticket state, or remediation fact
conflicts with an older handoff, this document is newer.

## 1. Executive status

- GitHub repository: `https://github.com/ssdbank9/Project-Astra`
- Branch to review: `codex/migration-safety-remediation`
- Remote branch URL: `https://github.com/ssdbank9/Project-Astra/tree/codex/migration-safety-remediation`
- Whitespace-filtered review URL: `https://github.com/ssdbank9/Project-Astra/compare/claude/excel-import...codex/migration-safety-remediation?w=1`
- Branch point: `5adec82` from `origin/claude/excel-import`
- Remote review range: `origin/claude/excel-import...origin/codex/migration-safety-remediation`
- Application status: local development only; not deployed or approved for real users
- Database target schema: v13
- Full automated suite at the latest verification: **220/220 passed**
- State-integrity focused suite: **7/7 passed**
- Migration focused suite: **8/8 passed**
- Jaira ticket `SRFCZD`: state-integrity remediation, in `review`
- Jaira ticket `A836XC`: migration-safety remediation, in `review`
- No live browser acceptance, production deployment, private-source ingestion,
  external notification, or infrastructure change was performed.

The branch contains two bounded remediation packages:

1. State integrity and idempotency for task writes, governed lifecycle actions,
   Owner requests, and final-result marking.
2. Atomic and retry-safe SQLite migrations for schema versions 1 through 12.

Both packages have regression tests. They are ready for an independent Claude
review, but not for a production-readiness claim.

## 2. Mandatory start sequence for Claude

Read this file completely before editing. Then read `AGENTS.md`, `CLAUDE.md`,
`pending-global-mistakes.md`, `docs/design/authorization-matrix.md`, and the
relevant source/tests named below.

Run the following from the repository root:

```powershell
git fetch origin
git switch codex/migration-safety-remediation
git status --short --branch
git log --oneline --decorate -8
jaira validate --json
jaira show SRFCZD --for-lane review --json
jaira show A836XC --for-lane review --json
.\.venv\Scripts\python.exe tests\run.py
.\.venv\Scripts\python.exe -m unittest -v tests.test_state_integrity
.\.venv\Scripts\python.exe -m unittest -v tests.test_db
node --check src\astra\static\app.js
git diff --check origin/claude/excel-import...HEAD
git diff -w --stat origin/claude/excel-import...HEAD
```

On Linux/macOS, replace the Python executable with `.venv/bin/python` and use
forward slashes in paths. Do not use system Python on Aly's Windows checkout;
the project venv contains `tzdata`, and system Python can create a false due-state
failure.

Review the implementation in two bounded path groups. The README is shared by
both packages, so inspect its relevant hunks in each pass:

```powershell
git diff origin/claude/excel-import...HEAD -- README.md docs/design/authorization-matrix.md src/astra/service.py src/astra/static/app.js src/astra/web.py tests/test_core.py tests/test_state_integrity.py tests/test_web.py .jaira/tickets/01M3549XTPENM6MSYCG2SRFCZD-harden-task-state-integrity-and-idempotency.md
git diff origin/claude/excel-import...HEAD -- README.md src/astra/db.py tests/test_db.py .jaira/tickets/01M3675JP3ADPB1KQ5R2A836XC-make-legacy-sqlite-migrations-atomic-and-retry-s.md
```

## 3. Remote publication and local provenance

The remote branch is the source Claude should review. It was created from
`origin/claude/excel-import` and published through Aly's authenticated GitHub
browser session because Windows Git Credential Manager returned
`SEC_E_NO_CREDENTIALS` for command-line push and fetch. GitHub therefore records
grouped web-upload commits rather than the original local implementation commit
IDs. The final source, tests, documentation, handoff, and two Jaira ticket files
were all published to the named branch.

Publication hygiene note: the authenticated GitHub web uploader serialized touched
text files with CRLF line endings. The ordinary compare therefore includes
line-ending-only churn and materially inflates its raw addition/deletion totals.
Claude should review with the whitespace-filtered URL above or `git diff -w`. Before
merge, normalize the touched text-file blobs back to LF with an authenticated Git
client, then confirm the ordinary compare matches the whitespace-filtered semantic
scope. This is a publication artifact; it was not present in the locally tested
commit tree.

Use the remote branch comparison above. Do not require the local-only commit IDs
to resolve in a fresh clone. They remain useful provenance on Aly's remediation
worktree:

| Local-only commit | Scope |
| --- | --- |
| `c109687` | Harden task writes, lifecycle decisions, Owner requests, and final-result idempotency; add regressions and update contracts. |
| `dfdbc4f` | Record the state-integrity package and Jaira review handoff. |
| `3fd31ec` | Make v1-v12 SQLite migrations atomic/retry-safe; add rollback/retry/schema-equivalence regressions. |
| `7936824` | Record the migration package and Jaira review handoff. |
| `f3bda40` | Add this consolidated Claude handoff and link it from `CLAUDE.md`. |

No existing Claude Excel-import changes were rewritten or discarded. The branch
was created on top of `5adec82`, preserving the imported-data hardening already
present on `origin/claude/excel-import`.

## 4. Combined adversarial findings

This section amalgamates the earlier Claude work, the subsequent Codex
adversarial review, and what the regression tests proved. Severity describes the
pre-fix risk.

### 4.1 Confirmed defects fixed on this branch

| Severity | Finding | Adversarial evidence | Remediation and regression evidence | Status |
| --- | --- | --- | --- | --- |
| Critical | A stale full-form task edit could overwrite a newer task revision. | Two readers could submit updates from the same revision; the later write did not prove it still owned the expected state. | `AstraService.update_task` now requires an integer `expected_revision` and performs a revision-guarded update. HTTP conflict maps to 409. The task form sends the loaded revision. `test_stale_task_update_is_rejected_without_state_or_event_change` proves no task or audit mutation on conflict. | Fixed; automated proof present. |
| High | Ordinary title/date/progress edits could mutate completed or otherwise terminal tasks without reopening them. | The service validated permissions but did not make terminal records immutable. | Ordinary task updates reject completed, cancelled, and abandoned tasks until the governed reopen path is used. `test_terminal_tasks_reject_ordinary_edits_until_reopened` proves the boundary. | Fixed; automated proof present. |
| Critical | Concurrent acceptance could allow competing decisions or duplicate acceptance evidence. | State was checked outside the decisive write transaction, leaving a time-of-check/time-of-use gap. | Acceptance, request-changes, reopen, hold, schedule, closure, and related protected decisions re-read and validate inside `BEGIN IMMEDIATE`. `test_concurrent_acceptance_has_one_winner_and_one_event` proves one winning transition and one event. | Fixed; automated proof present. |
| High | Repeated equivalent protected-action attempts could create duplicate Owner requests and duplicate notifications/events. | Equivalent JSON payloads were not canonically matched within the serialized write. | Protected payloads are canonicalized, searched, and inserted inside one immediate transaction. Matching pending requests are reused. `test_equivalent_protected_retries_reuse_one_pending_request_and_event` covers the retry. | Fixed; automated proof present. |
| High | Owner requests were visible but did not have a complete approve/reject/cancel execution path or reliable reconciliation after the direct action occurred. | Queue visibility existed, while request decision and stale-state handling were incomplete. | Added Owner decision service/HTTP paths and UI controls. Approval dispatches each supported protected action; direct equivalent actions resolve matching pending requests; stale approval remains pending rather than applying against changed state. Covered by `test_owner_can_decide_requests_and_stale_approval_stays_pending` and `test_owner_approval_dispatches_every_supported_protected_action`. | Fixed for the implemented action set; see the terminal-status UX qualification below. |
| Medium | Re-marking the same attachment as the final result could emit duplicate audit events despite no state change. | The event was not conditioned tightly enough on an actual insert/change. | Final-result event emission now occurs only when the final-result row is newly inserted. `test_repeated_final_result_marking_emits_only_real_state_changes` proves idempotency. | Fixed; automated proof present. |
| Critical | Legacy migrations used `sqlite3.executescript` inside an outer transaction. Python's driver commits before `executescript`, so a mid-migration failure could persist partial DDL while `user_version` remained old. | Fault injection reproduced schema objects/ALTER effects surviving a failed migration. This makes retry behavior dependent on accidental partial state. | Every v1-v12 script is split only at complete SQLite statements and executed with `connection.execute` inside the existing `BEGIN IMMEDIATE`; DDL and `PRAGMA user_version` now commit or roll back together. Fault-injection tests cover v1, v5, and v12, followed by successful retries. | Fixed; automated proof present. |

### 4.2 Why Claude's earlier review had merit

Claude's prior branch work and adversarial observations were materially useful.
The existing Excel-import fixes at and before `5adec82` were preserved. The
review also correctly emphasized authorization and regression coverage rather
than treating a green baseline as proof of concurrency safety.

The additional Codex pass found that the existing suite could be green while
state transitions still had race, immutability, idempotency, and migration
atomicity gaps. The useful combined conclusion is therefore:

- Claude's imported-data and authorization hardening should remain.
- The later state-integrity and migration fixes close independently reproduced
  defects that were not disproved by the earlier green suite.
- A green suite is a necessary gate, not a substitute for adversarial
  transaction-boundary and stale-state tests.

## 5. What changed by file

### State-integrity package

- `src/astra/service.py`
  - Requires and validates `expected_revision` for task edits.
  - Uses conditional writes and raises a conflict for stale revisions.
  - Blocks ordinary edits of governed terminal states.
  - Revalidates protected lifecycle actions inside immediate transactions.
  - Canonicalizes and deduplicates equivalent pending Owner requests.
  - Adds Owner approve/reject/cancel decision execution.
  - Reconciles pending requests when the Owner performs the equivalent direct action.
  - Emits final-result audit evidence only for a real insert/state change.
- `src/astra/web.py`
  - Maps service conflicts to HTTP 409.
  - Exposes Owner request decision actions through the HTTP boundary.
- `src/astra/static/app.js`
  - Sends the loaded task revision with form updates.
  - Adds Owner request decision controls for the implemented queue flow.
- `tests/test_state_integrity.py`
  - Adds seven focused adversarial/regression tests for stale writes, terminal
    immutability, acceptance races, request dedupe/decisions/reconciliation,
    action dispatch, and final-result idempotency.
- `tests/test_core.py` and `tests/test_web.py`
  - Update existing callers for revision-aware writes and add service/HTTP
    conflict and request-decision coverage.
- `README.md` and `docs/design/authorization-matrix.md`
  - Document the implemented concurrency, immutability, and request-decision contract.
- `.jaira/tickets/...SRFCZD...md`
  - Records goal, plan, DoD evidence, outcome, and current `review` lane.

### Migration-safety package

- `src/astra/db.py`
  - Adds `_execute_statements`, which uses `sqlite3.complete_statement` and
    `connection.execute` without escaping the active transaction.
  - Replaces every executable v1-v12 migration `executescript` call.
  - Keeps each migration's DDL and `user_version` change in one transaction.
- `tests/test_db.py`
  - Adds v1 rollback/retry proof.
  - Adds v5 ALTER/CREATE rollback and retry from v4.
  - Adds v12 table/index rollback and retry from v11.
  - Compares representative legacy-upgrade and fresh-v13 catalogs.
  - Tests a semicolon inside a quoted literal and rejects incomplete SQL.
  - Retains the earlier v13 interrupted/recovery regressions.
- `README.md`
  - Documents the all-or-nothing migration contract.
- `.jaira/tickets/...A836XC...md`
  - Records goal, plan, DoD evidence, outcome, and current `review` lane.

## 6. Regression and verification record

The latest completed verification before this handoff reported:

| Check | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe tests\run.py` | 220/220 passed in 183.363 seconds on the final pre-commit run. |
| `.\.venv\Scripts\python.exe -m unittest -v tests.test_state_integrity` | 7/7 passed. |
| `.\.venv\Scripts\python.exe -m unittest -v tests.test_db` | 8/8 passed. |
| Python compilation check for changed Python modules/tests | Passed. |
| `node --check src\astra\static\app.js` | Passed. |
| `git diff --check` for each implementation package | Passed. |
| Search for executable `.executescript(` in migration code | No executable call remains; only explanatory text/comments mention it. |

These checks prove the exercised local code paths. They do not prove browser
interaction quality, deployment security, backup restoration, multi-process
behavior, or production load.

## 7. Remaining findings Claude should assess

### 7.1 Confirmed limitation: terminal-status request decision UX

A Manager can create a generic protected status request from a terminal state,
but an Owner cannot safely approve that as an ordinary status update because a
proper reopen requires a reason and revised due date. The direct governed Owner
reopen path now reconciles the matching pending request.

The data-integrity rule is deliberate and safer than silently reopening. The
remaining question is a medium-priority UX/contract issue: the inbox may still
offer a generic Approve action that returns an explanatory conflict instead of
routing the Owner into the dedicated reopen form. Claude should decide whether
to replace that control with `Review and reopen` when the request originates
from a terminal state.

### 7.2 Unverified adjacent concurrency risk: task submission versions

`AstraService.submit_task` calculates the next submission version using a
`MAX(version) + 1` pattern and performs task-state work nearby. This path was
observed during review but was not reproduced as a defect and was outside the
two completed tickets.

Before production, add a synchronized two-writer regression for simultaneous
submissions of the same task. The desired result must be defined explicitly:
one winner plus a stale/conflict response, or two uniquely serialized versions
if the product permits both. Do not label this fixed without that proof.

### 7.3 Maintainability and efficiency opportunities

These are not demonstrated correctness failures in the remediated paths:

1. `migrate()` remains a long sequence of repetitive version blocks. It is now
   transactionally safe, but a declarative migration registry could reduce
   duplication and make fault-injection coverage easier. Refactor only with
   catalog-equivalence tests intact.
2. Owner request reconciliation uses a service-instance
   `_active_owner_request_id` context. It is safe in the current HTTP design,
   where a fresh `AstraService` is created per request, but it is brittle if the
   service is later reused by background workers or multiple commands. Passing
   an explicit request-decision context through the call stack would be clearer.
3. `_resolve_pending_requests` filters candidates in Python and repeatedly
   parses `payload_json`. The current volume is expected to be low, but a durable
   idempotency fingerprint and indexed lookup would scale better.
4. Correctness of equivalent pending-request dedupe currently relies on
   `BEGIN IMMEDIATE` serializing lookup and insert. A schema-level idempotency
   key with a unique partial index for pending requests would provide a second
   enforcement layer and clearer operational diagnostics.
5. `update_task` combines payload merge, lifecycle policy, field validation,
   schedule checks, authorization, persistence, and event creation in one large
   method. Extracting small policy/normalization helpers would reduce future
   regression risk, but should not be mixed into the current correctness review.

### 7.4 Acceptance and operational gaps still open

- No live browser click test was performed for revision conflicts or Owner
  request decisions. Current evidence is service, HTTP, static markup/JS, and
  JavaScript syntax coverage.
- No keyboard-only, screen-reader, touch, small-screen, zoom, high-contrast, or
  low-bandwidth acceptance was performed for these changes.
- No multi-process or production-load concurrency run was performed; tests use
  controlled local SQLite connections/threads.
- No HTTPS, secure-cookie, reverse-proxy, account-recovery, backup/restore,
  monitoring, disk-limit, or incident-response proof was performed.
- No production deployment, Oracle/DuckDNS/Caddy provisioning, real-user
  creation, private-source ingestion, external AI processing, or external
  notification was authorized or performed.

## 8. Jaira state and review protocol

The tickets are intentionally in `review`, which requires an independent model
review. Do not accept the implementer's outcome text as the verdict; inspect the
diff and run the regressions.

For each ticket:

1. Read the lane prompt from `jaira show <handle> --for-lane review --json`.
2. Review only the bounded diff for that package.
3. Set `review-summary`, `review-gaps`, `review-verdict`, and a reproducible
   numbered `review-check` using Jaira.
4. If a gap requires code changes, add a Jaira note so the reason survives the
   next review-field update, then send the ticket back through the permitted lane.
5. If the package is sound, move it only to the next human-controlled lane.
6. Never move a ticket out of `human` or `signoff`; Aly makes that decision.

The Jaira ticket outcome fields preserve the original local implementation
commit provenance. In a fresh clone of the web-published branch those local-only
commit IDs may appear as `(not available locally)`. This is expected: judge the
actual remote branch diff and the ticket's goal/DoD evidence, not availability
of the transport-time local SHA. If the branch files or tests disagree with a
ticket claim, the branch and reproduced behavior control the verdict.

The final `jaira validate --json` checked 35 tickets and reported no errors,
departed tickets, or stranded tickets. It did report 19 pre-existing
`undeclared_dependency` warnings on older tickets `F9HBSJ`, `AYW0QC`, `8B9NBH`,
`6G89SJ`, `CS93C6`, `5WZ4A8`, `MTEDTM`, and `D73AQW`. These warnings do not name
`SRFCZD` or `A836XC` and were not changed as part of this remediation. The
validator also marked generated agent notes in `AGENTS.md` and `CLAUDE.md` as
stale; review/regenerate those notes through the repository's supported Jaira
workflow rather than hand-editing ticket files or generated instruction blocks.

## 9. Suggested adversarial checks for Claude

Do not stop at rerunning the existing tests. At minimum, inspect or add coverage
for the following if any implementation concern remains:

1. A stale write must not add even a failure-shaped audit event unless the
   product explicitly requires one; the accepted task data must remain unchanged.
2. A task becoming terminal between read and write must reject the ordinary edit
   inside the transaction, not only in a pre-check.
3. Two equivalent Manager protected requests started together must return one
   pending request identity and emit one creation event.
4. An Owner approval whose target changed after request creation must not consume
   the pending request or silently apply stale intent.
5. A direct Owner action must reconcile the intended pending request without
   resolving an unrelated request with different payload semantics.
6. A migration failure after at least one DDL statement must preserve both the
   prior catalog and prior `PRAGMA user_version` after reconnect.
7. A retry after that failure must produce the same tables, columns, indexes,
   and current version as a fresh v13 database.
8. Simultaneous task submissions must receive an explicit concurrency contract
   and regression before being called production-safe.

## 10. Human/browser review checklist

This is still required after Claude's code review:

1. Start Astra locally with a disposable database and test accounts only.
2. Open the same task in two browser windows.
3. Save a change in the first window.
4. Save the stale form in the second window.
5. Confirm the second window shows a clear conflict/reload path and does not
   overwrite the first change.
6. As a Manager, request a protected action twice and confirm the inbox shows
   one pending request.
7. As Owner, approve, reject, and cancel representative requests; confirm the
   task state, request state, activity, and alerts agree.
8. Exercise a terminal-state reopen request and confirm the UI routes the Owner
   to the governed reason/revised-date flow rather than implying generic approval
   can bypass it.
9. Verify keyboard focus, error announcement, touch controls, and narrow viewport
   behavior for all new controls.

Record roles, browser, viewport, database fixture, and observed results. Do not
convert source inspection into a browser-acceptance claim.

## 11. Scope and safety boundaries

- Preserve the repository's accepted product, privacy, authorization, and
  hosting decisions.
- Do not broadly refactor while reviewing these two correctness packages.
- Do not edit `.jaira/tickets` by hand; use the CLI.
- Do not reset, clean, discard, or overwrite unrelated work.
- Do not commit credentials, `.env` files, local databases, virtual environments,
  caches, screenshots with private data, or browser profiles.
- Do not deploy or expose the development server without Aly's explicit approval.
- Do not claim production readiness from these 220 local tests.

## 12. Handoff completion criteria

This remediation handoff is complete when Claude can:

- reproduce the 220-test baseline from the project venv;
- independently verify or challenge both bounded implementation diffs;
- record a review verdict and executable check for `SRFCZD` and `A836XC`;
- distinguish fixed defects from the submission-version risk and maintainability
  opportunities;
- either return concrete defects to implementation or place sound packages at
  the human gate without moving them out of it; and
- report browser/operational limitations without implying they were tested.
