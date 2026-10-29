---
id: 01M63QZSGT5NWYX9H5BDB3Y1XY
title: "Password change: refuse reusing the current password; fix own-reset screen"
status: in-progress
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
updated-at: 2026-10-29T12:20:39Z
updated-by: Claude
claimed-by: X1CarbonPC-13024
claimed-at: 2026-10-29T11:51:22Z
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

- [ ] Write failing service, HTTP and frontend-driver tests for both defects
- [ ] Refuse new==current in change_own_password after the current-password check
- [ ] On own reset, update state.user and show the forced-change screen with an info note instead of reopening People
- [ ] Focused tests, browser check, full suite, independent review

## Progress
- **2026-10-29 11:52 · Claude** — Same-password check compares the submitted strings after verify_password, not hashes: current is already verified, and doing it after keeps 'Current password is incorrect' as the answer to a wrong guess (no oracle on the stored password). reset_user_password (owner setting someone's temporary password) is deliberately unchanged: an owner may reissue the same temporary password. UI: the old own-reset success message ('Your password has been changed') could never show, so it was removed. Probe tests that found both bugs were written by an independent agent in a throwaway copy (34 tests, not committed).
