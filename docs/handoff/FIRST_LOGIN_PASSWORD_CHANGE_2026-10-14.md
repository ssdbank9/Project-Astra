# A5 — First sign-in and self-service password change

Date: 2026-10-14
Ticket: JRNDC8 (active); Aly's acceptance is pending.
Branch: `codex/migration-safety-remediation`
Starting commit: `c13c7de801c387a52c744d01623f787927330a3f`

## Outcome

New accounts created by an App Owner and passwords reset by an App Owner or
server administrator are marked for a required change. Until that change,
server-side authorization permits only the account check, password change and
sign-out routes. This remains enforced if a user bypasses the UI.

Any signed-in user can change their password by entering the current password
and a new password. The existing minimum length of eight characters remains.
On success, Astra records a `password_changed` user event without password
values, keeps the active session, revokes other sessions, and clears the forced
change flag. Wrong-current-password and invalid requests do not update the
password or sessions. The initial App Owner bootstrap is unaffected, and
existing accounts migrate with the flag off. Existing sign-in lockout behavior
was not changed.

The sign-in flow presents a dedicated forced-change screen. The account menu
also provides a voluntary change dialog. After a forced change, Astra loads the
normal app; sign-out remains available before changing.

## Evidence

- Schema migration 21 adds `users.must_change_password` with `NOT NULL DEFAULT
  0`; migration compatibility and failure rollback are covered by
  `ForcedPasswordChangeMigrationTests` in `tests/test_db.py`.
- Service behavior is covered in `tests/test_password_change.py`, including
  App Owner-created/reset accounts, password verification, audit redaction, session
  retention/revocation and refusal without mutation.
- HTTP behavior is covered in `tests/test_web.py`: protected routes and
  logout-all are refused until change; current-user read, change and sign-out
  remain allowed; successful change restores protected access.
- Static UI checks in `tests/test_web.py` verify the forced screen and that the
  dialog markup loads before its JavaScript bindings.
- Focused verification passed: **30 tests in 58.555s, OK** across password,
  migration, HTTP security, reset, deadline-notification, entity-rename and
  timeline scheduling coverage. `node --check src/astra/static/app.js` passed.
- Full Windows suite passed: **Ran 891 tests in 698.337s, OK (skipped=1)**.
- Guard-removal check behaved as expected: temporarily disabling the
  `must_change_password` check made the dedicated HTTP test fail because the
  protected projects endpoint returned 200 instead of 403; after restoring
  the guard, that test passed (**1 test in 1.204s, OK**).
- The initial isolated local Chrome smoke test on a temporary database showed
  the forced screen for a synthetic new account, the self-service dialog, and
  the normal app shell for an established synthetic account. That initial run
  did not submit a password change. The later successful forced and voluntary
  browser flows are recorded in the 2026-10-15 follow-up below. No real account
  was used; the main Astra database and local server on port 8766 were not
  changed.

## Review and limits

The independent implementation review found no confirmed functional or security
defect. The reviewer acknowledged the follow-up Chrome evidence as closing the
browser gap, but did not independently repeat the browser actions. Aly's
acceptance is pending. This evidence is for local source, tests and isolated
synthetic data only. Hosted operation, real-user invitation, production recovery
and deployment remain unverified and unauthorized by this change.

The first full-suite attempt failed because legacy HTTP tests authenticated
newly created test users without completing the new required step. Test helpers
were corrected to model established fixture accounts; A5-specific tests retain
the forced-change state. The initial passing rerun was **891 tests in 698.337s,
OK (skipped=1)**. After the 2026-10-15 browser continuation, a fresh full run
passed **891 tests in 644.691s, OK (skipped=1)**.

## Follow-up browser verification — 2026-10-15

Using Chrome against an isolated local server and disposable SQLite database,
the forced-change form rejected mismatched and too-short passwords and a blank
current-password field; a wrong current password was rejected without leaving
the forced-change screen. The signed-in password dialog likewise rejected
mismatched, too-short and wrong-current-password submissions. Direct navigation
to `#/projects` while the synthetic member still required a change left the
forced-change screen in place.

The synthetic member then completed a forced change and reached the protected
Projects page. A synthetic App Owner completed the voluntary change and saw the
success notification. Read-only SQLite checks confirmed the new passwords
verify, both forced-change flags are clear, each account has one
`password_changed` event without the new password value, and each active session
remains usable. The browser exercised one active session per account; revocation
of other sessions is covered by service and HTTP tests, not a multi-session
browser run. The disposable server was stopped. No live accounts, primary Astra
database or production service were used or changed.
