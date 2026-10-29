---
id: 01M63QZSGT5NWYX9H5BDB3Y1XY
title: "Password change: refuse reusing the current password; fix own-reset screen"
status: review
ready: true
creator: Claude
assignee: Claude
goal: "A forced password change can only be met with a genuinely new password, and an owner who resets their own password from People lands on the change-password screen instead of a broken People dialog."
context: |-
  Found on 2026-10-25 while testing 0RHNMG (a proposed duplicate of done ticket JRNDC8) before Aly accepts it. Aly said: fix both first.
  1. change_own_password (src/astra/service.py) did not check that the new password differs from the current one. Re-entering the temporary password as the new one returned 200 and cleared must_change_password, so 'forced to change' could be met without changing anything.
  2. submitResetPassword (src/astra/static/app.js): when an owner resets their OWN password, the server forces a change but keeps the session (intended; test_web test_owner_resets_a_password_over_http). The page then called openPeople(), whose /api/users, /api/memberships and /api/user-events calls got 403. The owner saw 'Change your temporary password before using Astra.' as an error on a half-working app until a reload.
  Neither bug let anyone reach protected data; the server gate at web.py:708 was always enforced.
  Not in scope: whether an owner resetting their own password should be forced at all (current behaviour kept).
definition-of-done: "Service and HTTP tests prove a change to the same password is refused with nothing changed (hash, flag, sessions, user_events), for forced and unforced users, and a wrong current password is still reported first; a frontend driver test proves an own reset shows the forced-change screen with an info note and makes no further data calls, while resetting someone else still refreshes People; each guard's removal fails a test; checked in a browser; full suite passes; independent review approves."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-10-29T11:51:08Z
updated-at: 2026-10-29T12:21:40Z
updated-by: Claude
claimed-by: X1CarbonPC-13024
claimed-at: 2026-10-29T11:51:22Z
outcome-what: "change_own_password refuses a new password equal to the current one (after the current-password check). An owner's own reset from People now updates state.user, clears the form, closes People and shows the forced-change screen with an info note, instead of reopening People into 403s. One stale test phrase updated to the new note."
outcome-why: "Testing 0RHNMG found that re-entering a temporary password satisfied the forced change, and that an owner's own reset left a half-working app with an error until reload. Aly said fix both before accepting."
outcome-resolves: "Forced changes now need a genuinely new password for every role (service + HTTP tests, forced and unforced), and the own-reset path lands on the change screen with no refused calls (frontend driver tests, browser check). Each guard's removal fails a test; full suite 1121 OK."
executed-by: claude-opus-5-5
review-summary: "Two small changes. Server: change_own_password now refuses a new password identical to the current one, checked after the current password is verified, so a forced user must pick a genuinely new password and a wrong guess still only says 'Current password is incorrect'. Browser: when an owner resets their own password from People, the page no longer reopens People (whose data calls the server now refuses); it clears the reset form, closes People and shows the 'Choose a new password' screen with a teal note. Resetting someone else is unchanged."
review-gaps: "Independent reviewer (separate agent, did not write the code) found no correctness or security defects; three nits were raised and fixed before commit (info styling, dialog close and form clear now tested; unforced HTTP case added). Not covered: the reviewer noted a lone UTF-16 surrogate in a password may raise UnicodeEncodeError (500) inside hash_password; this is existing behaviour, outside this ticket, and an earlier probe reported a clean 400 for invalid Unicode, so it is unverified either way. Whether an owner resetting their own password should be forced at all was left as-is (existing, tested behaviour)."
review-verdict: "Approve. Diff matches every DoD item; guard removals each fail a test; full suite Ran 1121 tests OK (skipped=1); browser-checked with synthetic accounts. Reviewer verdict was approve with nits, all addressed."
review-check: "1. In PowerShell in the project folder: .venv\\Scripts\\python.exe tests\\run.py — expect 'Ran 1121 tests' and 'OK (skipped=1)'.  2. Start Astra locally and sign in as a test member whose account you just created; on 'Choose a new password', type the temporary password in all three boxes and press Change password — you should see 'Choose a new password that is different from your current password.' and stay on that screen.  3. Enter a different new password — Astra opens.  4. Sign in as an owner, open account menu > People and access > Reset a password, pick YOURSELF, set a new password and press Reset password — People closes and the 'Choose a new password' screen appears with a teal note 'Your password was reset…'; no red error.  5. Use the reset password as current and pick a new one — Astra opens normally."
---

# Password change: refuse reusing the current password; fix own-reset screen

## Definition of Done

- [x] Service and HTTP tests prove a change to the same password is refused with nothing changed (hash, flag, sessions, user_events), for forced and unforced users, and a wrong current password is still reported first; a frontend driver test proves an own reset shows the forced-change screen with an info note and makes no further data calls, while resetting someone else still refreshes People; each guard's removal fails a test; checked in a browser; full suite passes; independent review approves.
  proof: tests/test_password_change.py test_reusing_the_temporary_password_does_not_meet_the_forced_change, test_reuse_is_refused_for_a_signed_in_user_who_is_not_forced, test_wrong_current_password_is_reported_before_reuse; tests/test_web.py test_forced_change_refuses_the_temporary_password_as_the_new_one, test_signed_in_owner_cannot_change_to_the_same_password; tests/test_own_password_reset_ui.py (4 tests); guard removals: service guard -> 3 fail, guard moved before verify -> 1 fails, if(own) branch -> 2 fail, is-info add/remove and dialog close -> 1 fails each; browser check on 127.0.0.1:8793 with synthetic accounts; full suite Ran 1121 tests OK (skipped=1); independent review: approve with nits, nits 1-3 addressed

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Write failing service, HTTP and frontend-driver tests for both defects
- [x] Refuse new==current in change_own_password after the current-password check
- [x] On own reset, update state.user and show the forced-change screen with an info note instead of reopening People
- [x] Focused tests, browser check, full suite, independent review

## Progress
- **2026-10-29 11:52 · Claude** — Same-password check compares the submitted strings after verify_password, not hashes: current is already verified, and doing it after keeps 'Current password is incorrect' as the answer to a wrong guess (no oracle on the stored password). reset_user_password (owner setting someone's temporary password) is deliberately unchanged: an owner may reissue the same temporary password. UI: the old own-reset success message ('Your password has been changed') could never show, so it was removed. Probe tests that found both bugs were written by an independent agent in a throwaway copy (34 tests, not committed).
