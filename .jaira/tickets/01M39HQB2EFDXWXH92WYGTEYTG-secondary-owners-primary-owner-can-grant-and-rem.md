---
id: 01M39HQB2EFDXWXH92WYGTEYTG
title: "Secondary owners: primary owner can grant and remove full Owner access"
status: signoff
ready: true
creator: Claude
assignee: Claude
goal: "The primary App Owner can give other users full Owner access (secondary owners) and take it away; secondary owners have every other Owner power but cannot remove, demote or deactivate the primary or each other; every grant, removal and blocked attempt is recorded."
context: |-
  Today Astra has exactly one App Owner and no way to add another. users.global_role='owner' is the only marker (src/astra/db.py users table); create_user refuses role owner; set_user_active refuses any owner target.
  Aly asked in Slack thread 1790160392.461299 (ts 1790245584.314119, 2026-09-24): "as an owner I can create another secondary owner with full access as mine, and take it away, but as a primary owner i retain full control. they cant remove me but i can remove them."
  Approved defaults (ts 1790245630.918199): Aly is primary; only the primary grants or revokes secondary owners; several allowed; secondaries get every other Owner power; they cannot remove, demote, deactivate or reset the primary or each other; every grant and removal is recorded.
  Code that assumes one owner: five notification sites do SELECT id FROM users WHERE global_role='owner' + fetchone (service.py _request_protected_project_action x2, _notify_owner, _audit_import_blocked, import commit), so with two owners the recipient is arbitrary; _resolve_role('owner') needs exactly one owner, so template 'owner' tasks would go unassigned; create_user uses a positional INSERT INTO users VALUES(...) that breaks when a column is added.
  There is no API today to change a role, email or password, or to revoke another user's sessions; set_user_active is the only user-admin path.
  Design (scout plan scratchpad/secondary-owner-plan.md): schema v16 keeps global_role='owner' for all owners, adds users.is_primary_owner (CHECK primary implies owner, partial unique index) and a user_events audit table. Migration marks the one existing owner primary, refuses before any change if there are 2+ owners, and is a no-op with 0 owners (fresh installs migrate before init-owner).
  Risk found by the scout: a Manager later made secondary owner could approve their own pending Owner request; approve/reject by the request's own requester is refused (cancel still allowed).
definition-of-done: "Migration v16: 1 owner becomes primary and the schema matches a fresh database; 0 owners migrates and create_initial_owner then sets the flag; 2+ owners is refused before any change with user ids only, version unchanged; a failure late in v16 rolls back and a retry succeeds"
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-24T11:10:01Z
updated-at: 2026-09-24T12:33:38Z
updated-by: Claude
claimed-by: vm-26532
claimed-at: 2026-09-24T11:12:14Z
outcome-what: "Schema v16 (users.is_primary_owner + CHECK + partial unique index, user_events); primary-only grant/revoke of secondary owners with audit and notifications; shared _guard_user_target on user-changing calls; owner notices to all other active owners; owners cannot approve/reject their own requests; template 'owner' = acting owner; routes POST/DELETE /api/users/{id}/secondary-owner, GET /api/user-events; People screen badges, buttons and Owner access history; README"
outcome-why: "Aly asked 2026-09-24 (ts 1790245584.314119) for secondary owners with full access that only the primary can grant and remove, and who cannot remove the primary; defaults approved at ts 1790245630.918199"
outcome-resolves: "DoD 1-11: 19 new tests fail before (3 failures, 16 errors) and pass after; mutations of the guard, grant/revoke gate, self-decision, fan-out, template owner, session revoke and early refusal fail the tests; full suite Ran 393 tests OK; screenshots as primary and secondary"
review-summary: "Two independent reviews (authorization lens, migration/UI lens), then an authorization re-check of round 2. No path found for a secondary owner or non-owner to become primary, grant or remove owner access, or deactivate, demote or change the access or sessions of the primary or another owner, in the service or over HTTP; the server enforces it and the database backs it (CHECK primary implies owner; partial unique index for one primary). Revoke never restores 'owner' even with a forged prior role. v16 refuses 2+ owners before any step and inside the step, is atomic, idempotent and matches a fresh schema across v12/v15 fixtures with 0/1/2/inactive owners. Round 2 serialised user-target changes under one write lock (_guarded_user_change), deduped blocked attempts per actor+target+action for 10 minutes, listed grants/removals separately from blocked attempts, hid owner-targeted controls from non-primary owners, and added the missing tests. 22 focused tests and the full suite (396) pass."
review-gaps: |-
  - Low (follow-up): a user can still fill the primary's notifications by attempting against many different targets (dedupe key includes target); grants/removals stay visible. Fix: cap blocked notices per actor per 10 minutes.
  - Info: dedupe check and insert are not atomic; concurrent identical attempts may write an extra row, nothing is lost.
  - Info: task-level actions against the primary (removing as approver, reassigning tasks) and import-created memberships are not guarded; out of scope, they cannot remove or demote anyone.
  - Info (pre-existing): the per-email sign-in throttle lets anyone lock the primary out of sign-in for 15 minutes.
  - Info: surviving mutants are race-only or equivalent (init-owner lock; the unique index is the guarantee).
  - Product note for Aly: a template task with the 'owner' role now goes to whichever owner applies the template.
review-verdict: Approve — independent reviewer
review-check: "Copy the tree (git ls-files | tar) to a scratch dir; PYTHONPATH=src run tests.test_core.SecondaryOwnerTests tests.test_db.PrimaryOwnerMigrationTests tests.test_web.AstraWebTests.test_secondary_owner_routes_enforce_primary_control_over_http (22 OK); run the exploit files scratchpad/gte-authz-exploit-tests.py and -r2.py; node --check src/astra/static/app.js; full tests/run.py (396 OK); git diff --check."
---

# Secondary owners: primary owner can grant and remove full Owner access

## Definition of Done

- [x] Migration v16: 1 owner becomes primary and the schema matches a fresh database; 0 owners migrates and create_initial_owner then sets the flag; 2+ owners is refused before any change with user ids only, version unchanged; a failure late in v16 rolls back and a retry succeeds
  proof: tests/test_db.py PrimaryOwnerMigrationTests: test_v15_single_owner_becomes_primary_and_matches_fresh_schema, test_v15_without_an_owner_migrates_and_the_first_owner_becomes_primary, test_v15_with_two_owners_refuses_the_upgrade_without_touching_data, test_two_owners_in_an_older_database_refuse_before_any_step_runs, test_second_owner_written_after_the_early_check_is_refused_inside_the_step, test_failure_late_in_the_v16_step_rolls_back_then_retries
- [x] Schema: the database refuses a second primary owner (unique index) and a primary who is not an owner (CHECK)
  proof: tests/test_core.py SecondaryOwnerTests.test_database_refuses_a_second_primary_and_a_primary_who_is_not_an_owner; tests/test_db.py test_fresh_database_has_the_primary_flag_its_index_and_user_events
- [x] Primary grants and revokes: grant makes the user an owner (not primary) and records secondary_owner_granted with the prior role; revoke restores the prior role, revokes their sessions, keeps memberships and records secondary_owner_revoked; several secondaries allowed; a reason is required
  proof: tests/test_core.py SecondaryOwnerTests.test_primary_grants_and_revokes_a_secondary_owner, test_revoke_restores_a_chairman_and_several_secondaries_are_allowed, test_grant_and_revoke_input_errors (incl. blank revoke reason, deactivate-a-secondary message)
- [x] Forbidden paths (403, nothing changed, owner_change_blocked recorded): a secondary grants, revokes a secondary, revokes the primary, deactivates the primary or another secondary, or changes project access of the primary or another owner; a Chairman or member calling grant/revoke; the primary cannot revoke themselves
  proof: tests/test_core.py SecondaryOwnerTests.test_secondary_owner_cannot_change_owner_access_or_target_other_owners (8 attempts incl. own project access), test_repeated_blocked_attempts_record_one_row_and_one_notice, test_user_changes_read_the_target_under_the_write_lock, test_non_owners_cannot_grant_or_revoke_owner_access
- [x] Secondary owners use ordinary Owner powers (create project and user, decide an Owner request) and lose them on the next request after revoke
  proof: tests/test_core.py SecondaryOwnerTests.test_secondary_owner_has_ordinary_owner_powers_until_revoked
- [x] An owner cannot approve or reject an Owner request they filed themselves; cancel still works
  proof: tests/test_core.py SecondaryOwnerTests.test_owner_request_decisions_by_several_owners (secondary decides, 409 on second decision, self approve/reject Forbidden, self cancel OK)
- [x] Owner notifications go to every active owner except the actor; a template 'owner' task goes to the acting owner
  proof: tests/test_core.py SecondaryOwnerTests.test_owner_notifications_reach_every_other_active_owner, test_template_owner_role_goes_to_the_acting_owner
- [x] HTTP: POST/DELETE /api/users/{id}/secondary-owner and GET /api/user-events with the same rules; /api/me and /api/users expose is_primary_owner
  proof: tests/test_web.py test_secondary_owner_routes_enforce_primary_control_over_http (incl. GET /api/users is_primary_owner)
- [x] People screen: Primary owner / Secondary owner badge; Make/Remove secondary owner only for the primary; Playwright screenshots as primary and as secondary
  proof: src/astra/static/app.js renderPeople/changeOwnerAccess; /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/ui-shots/GTEYTG-before-people-primary.png and GTEYTG-after-people-{primary,secondary,primary-granted}{,-access}.png
- [x] Tests failed before the change; output saved to scratchpad/GTEYTG-failing-before.txt
  proof: /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/GTEYTG-failing-before.txt: HEAD e57af27 src + new tests, Ran 19 tests FAILED (failures=3, errors=16)
- [x] Full suite, node --check app.js, compileall, git diff --check and jaira validate pass
  proof: /tmp/claude-0/-workspace/6ce9994f-b952-5e8c-b3bf-df4d83545f57/scratchpad/GTEYTG-verify.txt round 2: tests/run.py Ran 396 tests OK after the last edit; focused 22 OK; node --check, compileall, git diff --check exit 0; jaira validate errors false

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] failing tests: test_db migration v16, test_core service rules, test_web HTTP routes; save failing run
- [x] db.py v16 step + refusal probe; SCHEMA_VERSION 16
- [x] service: primary flag in create_initial_owner/get_user/list_users; named-column INSERT; require_primary_owner, grant/revoke, _guard_user_target, blocked audit, list_user_events; owner fan-out; self-decision refusal; template owner = acting owner
- [x] web: routes and is_primary_owner in _require_user
- [x] app.js People screen badges and buttons; README
- [x] screenshots before/after as primary and secondary
- [x] full suite, node --check, compileall, git diff --check, jaira validate

## Progress
- **2026-09-24 11:14 · Claude** — Plan reasoning, checked against code at e57af27. The scout plan (scratchpad/secondary-owner-plan.md) holds except for three points. (1) The mid-step fault test in test_db.py covers LEGACY_STEPS v1-v12 only, not v16, so v16 gets its own rollback test, modelled on the v15 one: deny the new index, check rollback, then retry. (2) set_user_active on an owner target raises ValueError (400); the new guard runs first, so a secondary targeting an owner gets 403 while the primary keeps the old 400 (revoke first, then deactivate). (3) The template 'owner' role is fixed in _instantiate_tasks by adding picks['owner']=actor['id']. _check_role_assignments already forbids an 'owner' pick, so user input cannot collide, and with one owner nothing changes. Guard scope: set_user_active, grant/revoke_project_access, grant/revoke_secondary_owner. Not guarded: task assignment and reviewers, which are work assignment, not account admin, and cannot demote anyone. user-events reads: all owners (secondaries need the audit to see what the primary did); writes: primary only.
- **2026-09-24 11:43 · Claude** — Build findings the repo does not say. (1) Old-schema fixtures in test_db.py (at_v13/at_v14 and the backfilled-request test) used create_initial_owner/create_user; those now read or write users.is_primary_owner, which a v13-v15 database does not have. They now insert users through a legacy_user helper, and the migration tests that seed users use the same helper. (2) create_initial_owner hashes the password before BEGIN IMMEDIATE, so the check-and-insert window holds no slow work. At e57af27 the slow hash sat between the check and the insert, and two concurrent init-owner runs both succeeded; that test failed before. With the lock, a mutant that drops it now survives, because the window is microseconds and the partial unique index refuses a second primary anyway. It is kept for a clean ValueError instead of an IntegrityError. (3) _guard_user_target runs in set_user_active, grant_project_access and revoke_project_access. Task assignment and reviewers are not guarded: they assign work and cannot remove or demote anyone. (4) The primary deactivating a secondary still gets the old 400 'owner account cannot be deactivated'; revoke first. (5) user_events reads: all owners; writes: primary only. (6) owner_change_blocked for an unknown target id writes no audit row (FK) but still notifies the primary and returns 403. (7) The template 'owner' role resolves to the acting owner through picks; _check_role_assignments still refuses an explicit 'owner' pick. (8) Screenshots come from scratchpad/seed_gte.py and shoot_gte.js on 127.0.0.1 with synthetic data. Before: HEAD shows 'owner' as plain text with no owner controls. After as primary: badges plus Make/Remove buttons, and a grant done through the button records the reason. After as secondary: badges, no owner buttons, Owner access history visible. (9) Out of scope, follow-ups for Aly: transferring the primary role and a primary password reset (both need a CLI), and auditing app-wide settings changes.
- **2026-09-24 12:14 · Claude** — Review round 1 fixes (both reviews approved; Low items). (1) Races: set_user_active, grant_project_access and revoke_project_access now go through _guarded_user_change, which reads the target, applies the owner check and writes under one BEGIN IMMEDIATE. A blocked attempt raises the internal _OwnerTargetBlocked, which rolls back; the audit and notice are then written with no transaction open. Test test_user_changes_read_the_target_under_the_write_lock uses a patched get_user that tries to promote the target from a second connection mid-call: it must be locked out. Reading outside the lock fails 3 subtests. (2) Flood: _owner_change_blocked writes no new row or notice when the same actor, target and action has a blocked row in the last 10 minutes. An unknown target now records nothing (no row, no notice), only 403. list_user_events returns the latest 200 grants and removals, then the latest 50 blocked, with separate limits. (3) UI: a non-primary sees no Revoke on an owner's project-access row and no owners in the grant form; blocked attempts are listed separately (20 grants and removals, 10 blocked). (4) New tests: blank revoke reason; the in-step _refuse_multiple_owners (a second owner inserted after migrate's early check; without the in-step call, the unique index raises IntegrityError instead); GET /api/users is_primary_owner; a secondary changing their own project access. (5) _insert_user_event has an explicit column list. (6) _resolve_role's 'owner' branch was dead: its only caller, _instantiate_tasks, always sets picks['owner']. It is now chairman-only. (7) The primary deactivating a secondary gets 'Remove their secondary owner access first.' (8) README says so, plus the 20/10 history limits. It uses 'People screen' throughout, including the one older 'People panel' line. (9) Extra blank lines before the two test classes are removed.
