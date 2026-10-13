# Deadline extension notices — 2FREQ9

Aly selected in-app notification on 2026-10-13: when a deadline moves later,
notify the active primary/secondary App Owners and Chairman. Existing approval
rules remain in force. This decision does not grant Chairman authority to apply
protected changes or enable external delivery.

## Behavior

- A committed task due-date extension names the task, project and old/new dates.
  Edits, linked timeline moves, approved schedule revisions, reopening, bulk date
  changes and re-import share the same saved-event routing.
- A committed agreed project target extension names the project, old/new dates
  and actor. Initial targets and earlier targets retain ordinary Owner notices.
- A later calculated project finish produces one project notice for the complete
  saved operation, even when the agreed target remains unchanged. Linked chains,
  multirow imports and bulk changes compare the original and final project
  range, suppressing intermediate nested snapshots.
- New work can extend an existing project range. Cancelled/abandoned tasks are
  excluded; an undated finish uses its start date, matching Astra's forecast.
  A first date with no prior range/deadline is not an extension.
- Each active recipient gets one copy per event, including an acting App Owner.
  A task extension and a project finish extension are separate events. Ordinary
  private Owner notices retain their existing recipients.
- Preview, unchanged/earlier dates, rejected attempts and failed transactions
  do not create extension notices. History and notices roll back with the dates.
- Inbox read/unread status is per recipient. Receiving a notice does not grant
  task/project editing or protected-change approval authority.

## Verification

- New focused suite: Ran 10 tests in 11.164s, OK. The initial implementation-free
  run exposed eight missing-routing failures. Fixture errors (guessed auth API,
  HTTP verb and initial-date fallback) were corrected separately.
- Independent source review: pass, no blocking findings. Independent focused
  run: Ran 10 tests in 8.469s, OK. Disabling extension detection in memory makes
  the new regression fail.
- Actual Chrome, disposable loopback fixture: Owner saved a task extension
  2026-10-10 to 2026-10-14 through the existing consequence confirmation. Acting
  Owner and Chairman each saw task and calculated-finish notices. Chairman could
  mark one copy read; reload retained one unread and two total. Screenshot is
  local/ignored at `Temp/2FREQ9-chairman-inbox.png`; no browser artifacts published.
- Service/HTTP tests verify primary/secondary/Chairman recipient isolation,
  inactive recipients, unchanged authority, same-event deduplication, rollback,
  initial/earlier/unchanged dates, stale linked previews, approved revisions,
  reopening, multirow re-import and calculated-finish fallback.
- Full Windows suite: Ran 807 tests in 525.988s, OK (skipped=1), exit 0.
  Existing unavailable-symlink skip; Node UI tests ran.
- Independent supplemental bulk/Undo check: +3 days produced one complete
  project finish notice (12 to 15 October) and two task notices per recipient;
  Undo moving dates earlier produced none. A -3-day change produced none for
  Chairman; Undo restoring later dates produced one finish notice (9 to 12
  October) and two task notices per recipient. The manager received none.
- Independent handoff and screenshot review: pass. The screenshot captures the
  initial two-unread state; the later one-unread/reload result was observed in
  the browser and is separate evidence.

## Release boundary

Only disposable records were used. No real users, owner records, accounts,
credentials, deployment or external delivery changed. Hosted behavior is
unverified. App Owner acceptance is separate from test/review evidence.

Implementation: `src/astra/service.py`; regressions:
`tests/test_deadline_notifications.py`. No schema migration or new dependency.
