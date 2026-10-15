---
id: 01M4XH9DAS9JW45YQPZPJRNDC8
title: First-login and self-service password change
status: review
ready: true
creator: Codex
assignee: Codex
goal: "Require users with App Owner-set temporary or reset passwords to choose a new password before using Astra, and let signed-in users change their own password safely."
context: "Astra accepts accounts created by an App Owner and passwords reset by an App Owner or server administrator, but does not require users to replace temporary passwords at first sign-in. The handoff gate is docs/handoff/NEXT_STEPS.md A5. Implement a user flag for App Owner-created and reset passwords, a change-only session state until changed, and self-service change after verifying the current password. Preserve the 8-character minimum and the recorded no-lockout rule. Audit changes in user_events and revoke other sessions while retaining the active session. No account, credential, deployment or live database work is authorized."
definition-of-done: "Service, HTTP and browser checks prove accounts created by or passwords reset by an App Owner are forced to change before protected app access; an authenticated user changes their own password only after the correct current password; minimum length remains 8; user_events records the change without storing either password; all other sessions are revoked while the active session remains usable; malformed and wrong-current-password requests do not alter hashes or sessions; existing no-lockout sign-in behavior remains; migration, rollback and old-schema cases pass; independent review and full suite pass."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-10-14T15:42:55Z
updated-at: 2026-10-15T07:14:53Z
updated-by: Codex
claimed-by: X1CarbonPC-39188
claimed-at: 2026-10-14T15:44:36Z
outcome-what: "Verified A5 through the full 891-test suite, isolated Chrome success and failure flows, and independent source review; refreshed the handoff and recorded proof."
outcome-why: The first successful password-change browser transition and the full-suite rerun were the remaining A5 verification gaps.
outcome-resolves: "A5 acceptance criteria now have test, browser and independent-review evidence; hosted use remains unverified."
review-summary: "Schema v21 adds a must_change_password flag for App Owner-created and reset accounts. Server authorization restricts forced-change sessions to the password-change, self-profile and sign-out routes. The accessible UI supports first-login and signed-in password changes; successful changes audit without secrets, retain the active session and revoke other sessions."
review-gaps: "No confirmed source defect. The independent reviewer did not repeat the Chrome actions; the browser evidence is from the implementer's isolated synthetic-data run. The browser used one active session per account, so multi-session revocation is covered by service and HTTP tests rather than a multi-session browser run. Hosted behavior remains unverified."
review-verdict: "No confirmed defect in the implementation or test evidence reviewed. A5's local acceptance criteria are supported by the 891-test suite and isolated browser flows. Recommend Aly review the recorded evidence; hosted operation remains outside this verification."
review-check: "1. Read docs/handoff/FIRST_LOGIN_PASSWORD_CHANGE_2026-10-14.md, especially Follow-up browser verification — 2026-10-15. 2. Run .venv\\\\Scripts\\\\python.exe tests\\\\run.py and confirm 891 tests, OK, skipped=1. 3. For UI reproduction, use a disposable database and follow the documented forced-change and voluntary-change Chrome flows; do not use live Astra data."
---

# First-login and self-service password change

## Definition of Done

- [x] Service, HTTP and browser checks prove accounts created by or passwords reset by an App Owner are forced to change before protected app access; an authenticated user changes their own password only after the correct current password; minimum length remains 8; user_events records the change without storing either password; all other sessions are revoked while the active session remains usable; malformed and wrong-current-password requests do not alter hashes or sessions; existing no-lockout sign-in behavior remains; migration, rollback and old-schema cases pass; independent review and full suite pass.
  proof: docs/handoff/FIRST_LOGIN_PASSWORD_CHANGE_2026-10-14.md follow-up browser verification; .venv\\Scripts\\python.exe tests\\run.py (891 tests, OK, skipped=1); independent A5 implementation review

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Map every protected HTTP/API entry point and the existing App Owner create/reset, session, UI and migration paths; write the allowed change-only route list.
  proof: tests/test_password_change.py; src/astra/web.py:_require_user
- [x] Add schema v21 must_change_password default 0 and service-level failing cases for new/reset accounts, verified current-password change, audit, session revocation and legacy rows.
  proof: src/astra/db.py:_migrate_v21; tests/test_db.py:ForcedPasswordChangeMigrationTests; tests/test_password_change.py
- [x] Implement atomic service changes while preserving the initial-owner bootstrap and no-lockout sign-in rule.
  proof: src/astra/service.py:change_own_password; tests/test_password_change.py
- [x] Add HTTP change-only gating and self-change endpoint with CSRF, and failing HTTP cases for blocked APIs, allowed sign-out/change, wrong password and session behavior.
  proof: src/astra/web.py:_require_user; tests/test_web.py forced password change cases
- [x] Add accessible UI for forced first sign-in and voluntary self-change; test login, reload/session restoration and route bypass prevention.
  proof: src/astra/static/index.html; src/astra/static/app.js; tests/test_web.py UI checks; isolated Chrome smoke
- [x] Run migration compatibility, service/HTTP/UI/full suites, guard-removal check and local browser on synthetic data; get independent source review and update handoff.

## Progress
- **2026-10-14 15:47 · Codex** — Planning found schema20. Add nullable-free INTEGER must_change_password NOT NULL DEFAULT 0 in schema21 so existing users and the initial owner remain unaffected. Set it for accounts created by an App Owner and all App Owner/server password resets. A5 explicitly says a reset password is temporary; never set the flag for an ordinary successful self-change. Enforce forced state server-side in _require_user, not only by hiding navigation. Allow GET /api/me, POST /api/password/change, POST /api/logout only while flagged; logout-all should be blocked because it invalidates the only forced-change session. Self-change verifies current password, writes password_changed audit without secrets, clears the flag and keeps this session while revoking all others.
- **2026-10-14 18:46 · Codex** — The first full suite exposed 71 failures and 11 errors because unrelated HTTP tests logged in newly created users and then attempted protected APIs without changing the temporary password. The dedicated A5 cases were correct; only legacy fixtures needed to model established accounts. After updating those disposable fixtures, 30 focused tests passed and the full 891-test suite passed with one skip. Isolated Chrome exposed and verified the fix for password dialog markup appearing after app.js, which stopped initialization. Next: complete handoff, local fixed-point commit, independent Standards and Spec review; then leave the ticket awaiting Aly.
- **2026-10-14 18:49 · Codex** — Correction to the previous browser wording: Chrome showed the forced-change screen and the normal shell for an established synthetic account, but did not submit a password change. The successful transition is verified by service and HTTP tests only; the browser transition is unverified. Handoff receipt now states this accurately.
- **2026-10-15 04:23 · Codex** — Independent review found no confirmed functional defect. Standards found ambiguous owner wording, now corrected in docs, the migration comment, and JRNDC8 frontmatter and checklist via the CLI. Final reviewer recheck remains. The browser smoke showed the forced-change screen and the established-user shell but did not submit a password change; the successful transition is covered by service and HTTP tests only. Keep the ticket definition of done open until browser behavior is verified or Aly accepts that evidence limit. Next: commit the terminology correction with this ticket, request reviewer recheck, then rerun the suite and complete the authorized branch handoff.
- **2026-10-15 04:27 · Codex** — Standards recheck found an older progress note uses the phrase 'initial owner remains unaffected.' That historical note refers to the App Owner; current A5 handoff wording uses the qualified role name. The remaining NEXT_STEPS reference has now been corrected to 'App Owner.' Keep JRNDC8 in-progress: the completion criterion for a successful password-change transition in Chrome remains unverified.
