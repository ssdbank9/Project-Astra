---
id: 01M63QZSGT5NWYX9H5BDB3Y1XY
title: "Password change: refuse reusing the current password; fix own-reset screen"
status: backlog
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
updated-at: 2026-10-29T11:51:08Z
---

# Password change: refuse reusing the current password; fix own-reset screen

## Definition of Done

- [ ] Service and HTTP tests prove a change to the same password is refused with nothing changed (hash, flag, sessions, user_events), for forced and unforced users, and a wrong current password is still reported first; a frontend driver test proves an own reset shows the forced-change screen with an info note and makes no further data calls, while resetting someone else still refreshes People; each guard's removal fails a test; checked in a browser; full suite passes; independent review approves.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

