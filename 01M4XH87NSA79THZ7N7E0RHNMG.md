---
id: 01M4XH87NSA79THZ7N7E0RHNMG
title: First-login and self-service password change
status: human
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
created-at: 2026-10-14T15:42:16Z
updated-at: 2026-10-15T09:49:49Z
question: "Should 0RHNMG be archived as a duplicate of accepted JRNDC8, or kept as separate work for its broader 'owner-created/reset' wording? I recommend treating it as superseded; confirm whether any scope is missing first."
outcome-what: "Compared the backlog item with accepted A5 ticket JRNDC8: same title and core behavior, created 39 seconds earlier, with slightly different owner wording."
outcome-why: The repository contains two tickets for first-login and self-service password change; JRNDC8 is Done while 0RHNMG remains in backlog.
outcome-resolves: "No code work is needed unless Aly identifies distinct scope; 0RHNMG is held for the App Owner's duplicate-versus-separate decision."
updated-by: Codex
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
- **2026-10-15 09:49 · Codex** — Comparison on 2026-10-15: 0RHNMG and accepted/done JRNDC8 have the same title and core first-login/self-service password-change goal. JRNDC8 implements App Owner-created and reset accounts; 0RHNMG uses broader owner-created/reset wording. The untracked ticket origin is unverified. Leave it in human review until Aly decides whether it is superseded or has separate scope.
