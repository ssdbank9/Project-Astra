# Q1 approver permissions — 2026-10-05

Ticket `2RPSWM` records Aly's selected Q1 policy: Chairman and project viewers
remain eligible as task reviewers and approvers, but an approver designation
permits only a recommendation to the App Owner to accept pending submitted work.
The App Owner makes the final decision. A designation does not permit returning
work for changes, putting work on hold, reopening tasks, deciding schedule
proposals, or filing any other protected request. Project Manager authority is
independent of designation.

The service now exposes a separate `can_request_accept_submission` capability.
The general `can_request_protected` capability is Manager-only. The service checks
the active account, project visibility and action before creating a request, then
rechecks authority, task revision and pending-submission state inside the write
transaction. Removing designation or project access, deactivating the account,
or changing the Manager role before the write produces 403 and no request,
event, notification or business-state change. Existing historical pending
requests remain append-only records.

The task dialog exposes only the acceptance recommendation to a designated
approver and says that the submission still awaits an App Owner decision after
the request is filed. Chairman assignment and collaborator restrictions remain
unchanged. Import and filled-template paths continue to accept Chairman and
viewer Reviewer/Approver rows.

Evidence:

- Full Windows suite: `Ran 714 tests in 375.183s`, `OK (skipped=1)`; no new
  temporary directories or ResourceWarnings; source hashes stayed unchanged
  during the run. The Windows symlink test remains unverified because symlink
  creation is unavailable in this environment.
- Focused Q1/extended run: 78 tests, `OK`; two additional review regressions,
  `OK`.
- Three disposable guard removals fail as required: action scope (15 failures),
  write-lock authority (4 failures), and pending-submission state (1 failure).
- Actual synthetic browser verification: viewer sees only `Request Owner
  acceptance`, the request returns a visible notice that the submission still
  awaits the App Owner, and task status remains Submitted. Chairman sees the
  same acceptance action plus the existing assignee-only control, with no hold,
  reopen, changes or schedule-decision controls.

This is local implementation evidence only. Aly's ticket acceptance, hosted
deployment, credentials, real users, load/backup/device checks and merge remain
separate gates. The ticket is in `signoff`; only Aly may accept it.
