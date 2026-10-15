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
- An isolated local Chrome smoke test on a temporary database showed the forced
  screen for a synthetic new account, the self-service dialog, and the normal
  app shell for an established synthetic account. The browser did not complete
  a password change; the transition after a successful change is verified by
  service and HTTP tests, but remains unverified in the browser. No real
  account was used; the main Astra database and local server on port 8766 were
  not changed.

## Review and limits

The independent Spec review found no confirmed functional defect. The Standards
review found one terminology issue, now corrected; final reviewer recheck is
pending. Successful password submission and the resulting transition in Chrome
remain unverified, as the isolated smoke did not change a password. Aly's
acceptance is pending. This evidence is for local source, tests and an isolated
browser instance only. Hosted operation,
real-user invitation, production recovery and deployment remain unverified and
unauthorized by this change.

The first full-suite attempt failed because legacy HTTP tests authenticated
newly created test users without completing the new required step. Test helpers
were corrected to model established fixture accounts; A5-specific tests retain
the forced-change state. The rerun above is the passing full-suite receipt.
