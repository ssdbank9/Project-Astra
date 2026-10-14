---
id: 01M4XH9DAS9JW45YQPZPJRNDC8
title: First-login and self-service password change
status: in-progress
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
updated-at: 2026-10-14T18:21:59Z
updated-by: Codex
claimed-by: X1CarbonPC-39188
claimed-at: 2026-10-14T15:44:36Z
outcome-what: "Mapped owner create/reset, session validation, API route gating, frontend login/resume and the schema20 migration chain; recorded the v21 compatibility plan."
outcome-why: The A5 gate needs server-enforced forced-change access and must preserve existing accounts and no-lockout behavior.
outcome-resolves: "Begin implementing v21 flag, atomic password changes, HTTP restrictions and accessible UI in vertical slices."
---

# First-login and self-service password change

## Definition of Done

- [ ] Service, HTTP and browser checks prove owner-created/reset passwords are forced to change before protected app access; an authenticated user changes their own password only after the correct current password; minimum length remains 8; user_events records the change without storing either password; all other sessions are revoked while the active session remains usable; malformed and wrong-current-password requests do not alter hashes or sessions; the existing no-lockout behavior remains; migration, rollback and old-schema cases pass; independent review and full suite pass.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Map every protected HTTP/API entry point and the existing owner create/reset, session, UI and migration paths; write the allowed change-only route list.
  proof: tests/test_password_change.py; src/astra/web.py:_require_user
- [ ] Add schema v21 must_change_password default 0 and service-level failing cases for new/reset accounts, verified current-password change, audit, session revocation and legacy rows.
- [ ] Implement atomic service changes while preserving the initial-owner bootstrap and no-lockout sign-in rule.
- [ ] Add HTTP change-only gating and self-change endpoint with CSRF, and failing HTTP cases for blocked APIs, allowed sign-out/change, wrong password and session behavior.
- [ ] Add accessible UI for forced first sign-in and voluntary self-change; test login, reload/session restoration and route bypass prevention.
- [ ] Run migration compatibility, service/HTTP/UI/full suites, guard-removal check and local browser on synthetic data; get independent source review and update handoff.

## Progress
- **2026-10-14 15:47 · Codex** — Planning found schema20. Add nullable-free INTEGER must_change_password NOT NULL DEFAULT 0 in schema21 so existing users and the initial owner remain unaffected. Set it for accounts created by an App Owner and all App Owner/server password resets. A5 explicitly says a reset password is temporary; never set the flag for an ordinary successful self-change. Enforce forced state server-side in _require_user, not only by hiding navigation. Allow GET /api/me, POST /api/password/change, POST /api/logout only while flagged; logout-all should be blocked because it invalidates the only forced-change session. Self-change verifies current password, writes password_changed audit without secrets, clears the flag and keeps this session while revoking all others.
