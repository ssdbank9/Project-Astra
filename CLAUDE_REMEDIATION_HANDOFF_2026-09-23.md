# Astra adversarial review and remediation handoff — 2026-09-23

Prepared for Aly Jafferani and the next Claude Code review session.

This is the current implementation handoff for the adversarial review and the
first two remediation packages. It supplements the older product and execution
handoffs; where a branch, commit, test count, ticket state, or remediation fact
conflicts with an older handoff, this document is newer.

## 1. Executive status

- GitHub repository: `https://github.com/ssdbank9/Project-Astra`
- Branch to review: `codex/migration-safety-remediation`
- Branch point: `5adec82` from `origin/claude/excel-import`
- Current handoff branch code head before this document: `7936824`
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
git diff --check 5adec82..3fd31ec
git diff --stat 5adec82..3fd31ec
```

On Linux/macOS, replace the Python executable with `.venv/bin/python` and use
forward slashes in paths. Do not use system Python on Aly's Windows checkout;
the project venv contains `tzdata`, and system Python can create a false due-state
failure.

Review the implementation diff in two packages:

```powershell
git diff 5adec82..c109687
git diff dfdbc4f..3fd31ec
```

The two `Record ... review handoff` commits contain Jaira ticket state/evidence;
the two implementation commits contain the code and regression changes.

## 3. Commit chain and scope

| Commit | Scope |
| --- | --- |
| `c109687` | Harden task writes, lifecycle decisions, Owner requests, and final-result idempotency; add regressions and update contracts. |
| `dfdbc4f` | Record the state-integrity package and Jaira review handoff. |
| `3fd31ec` | Make v1-v12 SQLite migrations atomic/retry-safe; add rollback/retry/schema-equivalence regressions. |
| `7936824` | Record the migration package and Jaira review handoff. |

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

### State-integrity package (`c109687`)

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

### Migration-safety package (`3fd31ec`)

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

The Jaira review preview may print a commit as `(not available locally)` even
when normal Git can show it. That occurred in this sandbox because the Jaira
adapter did not inherit Git's safe-directory override. Confirm commits with
`git show c109687` and `git show 3fd31ec`; treat the preview wording as an
environment/tooling artifact unless ordinary Git also cannot resolve them.

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
