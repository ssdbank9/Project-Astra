---
id: 01M4XH9DAS9JW45YQPZPJRNDC8
title: First-login and self-service password change
status: backlog
ready: true
creator: Codex
assignee: Codex
goal: "Require users with owner-set temporary or reset passwords to choose a new password before using Astra, and let signed-in users change their own password safely."
context: "Astra accepts owner-created accounts and owner password resets, but does not require users to replace temporary passwords at first sign-in. The handoff gate is docs/handoff/NEXT_STEPS.md A5. Implement a user flag for owner creation/reset, a change-only session state until changed, and self-service change after verifying the current password. Preserve the 8-character minimum and the recorded no-lockout rule. Audit changes in user_events and revoke the user's other sessions while retaining the active session. No account, credential, deployment or live database work is authorized."
definition-of-done: "Service, HTTP and browser checks prove owner-created/reset passwords are forced to change before protected app access; an authenticated user changes their own password only after the correct current password; minimum length remains 8; user_events records the change without storing either password; all other sessions are revoked while the active session remains usable; malformed and wrong-current-password requests do not alter hashes or sessions; the existing no-lockout behavior remains; migration, rollback and old-schema cases pass; independent review and full suite pass."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-10-14T15:42:55Z
updated-at: 2026-10-14T15:44:36Z
updated-by: Codex
claimed-by: X1CarbonPC-39188
claimed-at: 2026-10-14T15:44:36Z
---

# First-login and self-service password change

## Definition of Done

- [ ] Service, HTTP and browser checks prove owner-created/reset passwords are forced to change before protected app access; an authenticated user changes their own password only after the correct current password; minimum length remains 8; user_events records the change without storing either password; all other sessions are revoked while the active session remains usable; malformed and wrong-current-password requests do not alter hashes or sessions; the existing no-lockout behavior remains; migration, rollback and old-schema cases pass; independent review and full suite pass.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress

