---
id: 01M3AFJ8EQKFNHGY528E3M2AYA
title: Sign-in never locks anyone out; owners reset passwords in the app; 8-character minimum
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Nobody, including the primary owner, is ever locked out by failed sign-ins; a wrong password just says so. Owners can reset a forgotten password from the People screen, and passwords need at least 8 characters."
context: |-
  What is wrong today (branch codex/migration-safety-remediation at caf261a):
  - 5 wrong passwords for one email in 15 minutes makes /api/login return 429 for that email (service.py login_is_throttled, web.py _login). It blocks the right password too, so anyone who knows an email can lock that person out, the primary owner included (handoff open ask 5).
  - A forgotten password can only be reset on the server with 'astra reset-password' (PDDS2D). There is no reset in the app.
  - Passwords need 12+ characters (auth.hash_password).
  Aly's decisions (Slack thread ts 1790256175.671249):
  - ts 1790279102.044719: sign-in must not sign anyone out or lock anyone out; keep it simple, just say the password is incorrect; an owner can reset the password for anyone who forgets it.
  - ts 1790279285.796099: secondary owners may reset other owners' passwords, except the primary owner's.
  - ts 1790279350.477049: the minimum password length is 8 characters.
  Rejected: the per-IP throttle plan in the session scout file throttle-scout.md. Do not build it.
  Trade-off Aly accepted: unlimited online password guessing. Only the 8-character minimum and the slow PBKDF2 check (600,000 iterations) protect an account. Rate limiting for the hosted deployment belongs on 6BXYJZ.
  Kept: failed and successful attempts are still written to login_attempts as history (pruned after 90 days); the server command stays as a backup.
definition-of-done: "No lockout: 20+ wrong passwords never block the right one; wrong password or unknown email returns 401 'Incorrect email or password.'; attempts still recorded and pruned after 90 days; no 429 path left"
tags:
  - astra
blocked-by: []
related:
  - 01M39HQB2EFDXWXH92WYGTEYTG
  - 01M3A930RYSAXPWQVQP3PDDS2D
  - 01M2HQJZ6KSPH67PP6746BXYJZ
commits: []
created-at: 2026-09-24T19:51:32Z
updated-at: 2026-09-24T20:28:14Z
updated-by: Claude
claimed-by: vm-12405
claimed-at: 2026-09-24T20:27:50Z
outcome-what: "Sign-in no longer locks anyone out: the per-email throttle and its 429 are gone, a wrong password or unknown email returns 401 'Incorrect email or password.', and attempts stay in login_attempts as history (pruned after 90 days). Passwords need 8 characters (was 12) everywhere. Owners reset passwords in the app: POST /api/users/<id>/password and a 'Reset a password' form plus a 'Reset password' action on the People screen. Any active owner may reset any active user's password except the primary owner's, which only the primary may reset (refused 403, audited as owner_change_blocked, capped notice). The reset signs the user out (keeping the actor's own current session when they reset their own), clears failed sign-ins, writes a password_reset user event 'in app', and notifies the user, plus the other owners when the user is an owner. The CLI reset shares the same code."
outcome-why: "Five wrong passwords locked any account for 15 minutes, the primary included, even with the right password, and only the server command could reset a password. Aly decided: no lockout, just say the password is incorrect, owners reset forgotten passwords (secondaries not the primary's), 8-character minimum (Slack ts 1790279102.044719, 1790279285.796099, 1790279350.477049); a per-IP throttle was rejected."
outcome-resolves: "All five DoD items are ticked with test proof; review 8 follow-ups (M1, L1-L5, I1) fixed with tests; Ran 456 tests, OK."
---

# Sign-in never locks anyone out; owners reset passwords in the app; 8-character minimum

## Definition of Done

- [x] No lockout: 20+ wrong passwords never block the right one; wrong password or unknown email returns 401 'Incorrect email or password.'; attempts still recorded and pruned after 90 days; no 429 path left
  proof: web.py _login; service.py record_login_attempt; tests: test_web test_repeated_failures_never_lock_anyone_out (21 wrong then correct = 200; unknown email 401), test_core test_login_attempts_are_history_only_and_pruned_after_90_days; review 8 fixes: test_core test_the_login_history_prune_runs_at_most_once_an_hour (hourly prune, 320-char email cap), test_web test_unknown_and_long_emails_are_checked_against_a_dummy_hash (dummy PBKDF2 check, >320-char email and non-string password still 401)
- [x] 8-character minimum everywhere (hash_password, add-user form, reset form, CLI, README); existing hashes unaffected
  proof: auth.py MIN_PASSWORD_LENGTH; tests: test_core test_passwords_need_eight_characters, test_non_owners_and_inactive_targets_are_refused (7 chars), test_reset_password_refusals_change_nothing, ServerCommandCliTests test_refusals_exit_with_one_line_and_no_traceback; test_web test_owner_resets_a_password_over_http (7 chars 400)
- [x] In-app reset: POST /api/users/<id>/password for active owners; primary resets anyone; secondary resets anyone except the primary (403, audited as owner_change_blocked, capped notice); inactive target refused; stale ex-primary safe; target sessions revoked (own reset keeps the current session); failed sign-ins cleared; password_reset user event 'in app'; target notified, other owners notified when the target is an owner
  proof: service.py reset_user_password + _apply_password_reset; web.py route. Tests (test_core ServerCommandTests): test_an_owner_resets_a_members_password_in_the_app, test_a_secondary_resets_another_secondary_and_their_own_password, test_a_secondary_cannot_reset_the_primarys_password, test_the_primary_resets_a_secondary_and_their_own_password, test_a_stale_ex_primary_cannot_reset_the_new_primarys_password, test_non_owners_and_inactive_targets_are_refused; test_web test_owner_resets_a_password_over_http (CSRF, member 403, sessions, own session kept); review 8 fixes: test_a_demoted_or_deactivated_secondary_with_a_live_session_cannot_reset, test_a_non_string_password_is_refused (service) and 400 'Password must be text.' in test_owner_resets_a_password_over_http; blocked notice 'blocked password reset of the primary owner by <actor>'
- [x] People screen: Reset password on each active user row (hidden on the primary's row unless the viewer is the primary), inline form with confirm and 8-character check, clear success and error messages
  proof: app.js renderPeople: 'Reset password' row action (canResetPassword hides it on the primary's row unless viewer is primary), 'Reset a password' form with confirm, 8-char and match checks, teal success message; test_web static asserts; node --check ok; review 8 fixes: own reset says 'Your password has been changed.', history re-renders after a reset, row actions grouped on one line (browser screenshots in the lock 8 scratch folder), static rule test for canResetPassword (node-evaluated)
- [x] Tests for every clause above and existing tests updated; docs (README, handoff, CLAUDE.md); existing tests green
  proof: Ran 456 tests, OK; README sign-in, People screen, CLI length; handoff and CLAUDE.md 456

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] web.py _login: drop the throttle and 429; message 'Incorrect email or password.'; service: remove login_is_throttled + LOGIN_* ; prune login_attempts older than 90 days
  proof: web.py _login (throttle and 429 removed, 'Incorrect email or password.'); service.py record_login_attempt prunes >90 days; login_is_throttled and LOGIN_* removed
- [x] auth.py 8-character minimum; UI/CLI/README texts
  proof: auth.py MIN_PASSWORD_LENGTH=8; app.js MIN_PASSWORD; README
- [x] service.py: shared _apply_password_reset used by reset_password (CLI) and reset_user_password (in app) with the primary check inside the transaction
  proof: service.py _apply_password_reset shared by reset_password and reset_user_password
- [x] web.py POST /api/users/<id>/password; app.js People screen reset form + row action; style.css success message
  proof: web.py POST /api/users/<id>/password; app.js reset-password-form, data-reset-password, canResetPassword, submitResetPassword; style.css #people-body .is-info/.form-hint
- [x] Tests (core, web) replacing the throttle tests; docs; full suite and checks; move to review; commit locally
  proof: tests/run.py Ran 452 tests OK (was 444)

## Progress
- **2026-09-24 19:59 · Claude** — Choices (Claude, 2026-09-24): (1) a successful sign-in still deletes that email's failed rows and a reset clears them (as before); everything else is kept 90 days. (2) Own in-app reset keeps the session that made the request (token hash from the cookie) and signs out the others; no self-notice for your own reset, other owners told when you are an owner. (3) A secondary's attempt on the primary goes through _owner_change_blocked with action 'reset the primary owner's password' and message 'Only the primary owner can change the primary owner's password.' (primary notice capped per KBWY86). (4) The actor is re-read as an active owner inside the transaction, and the target's primary flag is read fresh there too (_require_primary_now), so a stale ex-primary is refused. (5) People screen: the row action fills a 'Reset a password' form (same inline-form pattern as 'Add a user') instead of a prompt(); the success line uses the existing teal is-info style. (6) user_events reason 'in app' vs 'server command' drives the history label ('by <owner> · in app' vs 'via server command'). Not built: per-IP throttle (rejected by Aly).
- **2026-09-24 20:27 · Claude** — Review 8 fixes (Claude, 2026-09-24): M1 the 90-day prune now runs at most once an hour per server process (module-level monotonic timestamp: the web handler makes a new AstraService per request, so an instance attribute would prune on every request); typed emails stored at most 320 chars. Follow-up for the next schema bump: an index on login_attempts(attempted_at) so the prune stops scanning. L1 unknown/inactive email verified against a fixed dummy hash (auth.dummy_password_hash, same PBKDF2 cost). L2 stale demoted/deactivated secondary test; canResetPassword rule pinned and node-evaluated. L3 own-reset message, history refresh after reset, People user rows now put their actions in one right-aligned group so links never wrap mid-row. L4 blocked notice 'blocked password reset of the primary owner by <actor>' and history label 'Blocked password reset of the primary owner'. L5 non-string password -> 400 'Password must be text.' (endpoint and service); login treats one as wrong. I1 comment fixed.
