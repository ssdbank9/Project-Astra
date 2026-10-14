# Independent-review guard repairs — 2026-10-14

Ticket **MJ5Q35** repairs the confirmed backend findings from the supplied
Claude review and the implementing agent's independent reconciliation at
`566990346b22e056aa650865e2fc354a384a477b`. Aly authorized "fix these".
Use the final published package SHA supplied with this receipt for review.
Schema 20 and package 0.1.0 are unchanged. No deployment, real user, credential,
main data-folder mutation or existing protected board transition was performed.

## Decisions and requirement coverage

| Item | Final behavior and evidence |
| --- | --- |
| F-01: template creation bypassed closed-project rules | Task-template instantiation rechecks the destination under the write lock before any task/event insertion. A destination closed between the early check and write is refused. Service and HTTP negative cases pass. Historical project/task templates can still be saved; their source snapshot and storage are now atomic. |
| F-02: Chairman reopening conflicted with the dated owner rule | Reopening is restricted to active App Owners, primary or secondary, with a reason, history and notices. This aligns with Z72D79's October 5 owner note. The contradictory Chairman test/control was corrected. Service/HTTP cover both Owner variants and Chairman refusal; Chrome confirms the role-specific control and successful Owner reopening. |
| F-03: submitted ordinary edits | Aly explicitly selected **Keep ordinary edits allowed during review** on October 14. Title, details, responsible person and task dates remain editable under existing role/reason/revision rules, with history. Acceptance and request-changes actions remain App Owner decisions. The submitted-edit regression and a separate actual-service responsible-person change pass; no freeze was added. |
| F-04: stale authority at writes | Actor-driven writes verify current active/global role after acquiring their write lock. Revoked secondary-owner snapshots cannot close projects, submit tasks, change settings/templates/files/final results or reserve import keys. HTTP tests revoke authority after authentication and prove refusal without partial business writes. Existing primary-specific guards retain their current-row checks and audited sentinels; a former primary retains secondary project rights. |
| F-04 related membership/target drift | Management/view authority is queried under lock where needed. Manager-to-viewer changes at transaction entry refuse criticality, reviewer/dependency/project requests, proposals and leases. Reviewer/template-role/parent eligibility is checked against current rows. Template capture is atomic. Bulk cleanup remains independent of revoked actor authority. |
| F-05: dependency changes in closed projects | Adding and removing dependencies recheck project status under the same lock as the write. Owner and Manager service refusals and closure-before-write cases pass, preserving links/events on refusal. HTTP coverage verifies addition; HTTP removal was not separately exercised in this repair. |
| Review-discovered board coherence gaps | A rejected move retains its blocked-attempt audit. Lifecycle mutation, rank bookkeeping and response now share one outer transaction. Injected rank-storage failure rolls back the status, revision and history. This avoids an error response after a committed move. |

Authorization remains in `src/astra/service.py`; the UI change in
`static/app.js` only aligns the reopening control. Existing authorization and
negative-case suites remain part of the full verification.

## Verification record

- Initial meaningful new regression run: **Ran 15 in 23.751s,
  FAILED (failures=19)**, no errors; multiple role/action subcases explain the
  larger failure count. The earlier 15-test run had 17 failures/3 fixture
  errors, corrected before the final red run; those were not extra app defects.
- Final focused new tests: **Ran 32 in 54.087s, OK**. The intermediate
  32-test run passed in 52.677s. Includes service and
  real loopback HTTP cases, 25 revoked-Owner action subcases, membership/target
  changes at the write boundary, both Owner variants, board atomicity/audit,
  historical templates and submitted edits.
- Broader intermediate receipts: core **181 in 159.949s, OK (skipped=1)**;
  assignment **26 in 42.283s, OK**. An earlier core run failed 4/errors1:
  blanket primary-flag comparison broke retained secondary rights and refusal
  auditing. Specialized account guards and role-specific semantics were
  preserved instead of weakening those tests.
- Historical-schema compatibility: the first database run failed with eight
  errors because the new authority check read a user-directory column absent
  from older migration fixtures. It now reads only id, global role and active
  status. Database tests: **48 in 12.729s, OK**.
- Independent read-only source/test reviewer found the two board regressions,
  independently reproduced their correction, and returned **PASS**. Their
  focused receipt: **32 in 50.304s, OK**. The final Board message compatibility
  correction preserves the previous denial wording. Independent review of
  that correction and the historical-schema query returned **PASS**.
- Six distinct guard removals in memory each failed the relevant regression:
  current actor, closed destination, current project membership, reviewer
  eligibility, parent eligibility and atomic board move. Source files were
  preserved. The independent reviewer also checked actor, destination and
  board-transaction removals.
- JavaScript syntax and diff hygiene pass. Final full-suite receipt:
  **Ran 881 tests in 830.547s, OK (skipped=1)**, exit 0. Node/UI drivers ran;
  the unavailable Windows symlink case remains unverified.
  Two attempted full runs were stopped for the Board denial-message and
  historical-schema compatibility corrections. Their partial logs are
  retained; neither counts as a pass.

## Browser evidence and boundaries

Actual Chrome verification used synthetic Chairman and App Owner sessions on
an isolated loopback fixture. The Chairman's closed project shows no reopening
control. The App Owner sees it, submits a reason, observes Active and sees
Project reopened with the actor, reason and closed-to-active change in Activity.
The same data was not imported into Aly's main database.

Local ignored screenshots: `Temp/review-chairman-closed.png` and
`Temp/review-owner-reopen-activity.png`, both visually inspected. Logs,
`Temp/check_review_guard_mutations.py` and the fixture are local reproduction
aids, excluded from Git. External reviewers should recreate disposable cases.
The browser tab was closed; the owned fixture is stopped before handoff.
No fresh exhaustive UI, physical-device, screen-reader or hosted test is
inferred from these checks. Aly's main running server was not restarted;
its loaded backend version remains unverified.

## Remaining release work

This receipt addresses the confirmed review defects and records the submitted
edit decision. Cross-project Move/Copy/Link remains a feature/release-scope gap.
First-login/self-service passwords, supported backup/restore, CI, version and
operator packaging, representative load/device checks and authorized staging
proof remain the gates in PRE_DEPLOYMENT_REVIEW_2026-10-13.md.
They are not completed by these repairs. Hosted and real-user launch remain
unverified and are not authorized.

The supplied report's board counts reconcile, but its "60 not Done" arithmetic
was incorrect: at 88 total/25 Done it was **63 not Done**. Open lanes include
already accepted work and deferred tickets, so that figure is not the number
of unaccepted launch blockers. MJ5Q35 adds one ticket; final lane counts are
**89 tickets: 25 Done / 39 signoff / 11 human / 14 backlog** after its CLI
transition to human. Validation checked 89 with no errors, 44 warnings and
existing generated AGENTS/CLAUDE note drift. Aly alone accepts MJ5Q35.
