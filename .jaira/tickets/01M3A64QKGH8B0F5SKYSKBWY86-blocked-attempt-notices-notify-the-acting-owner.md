---
id: 01M3A64QKGH8B0F5SKYSKBWY86
title: "Blocked-attempt notices: notify the acting owner for Item 2 events and cap repeats per person"
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Every Owner decision Item 2 outcome on an attachment reaches an owner even on a single-owner install, and no one person can flood an owner's inbox with blocked-attempt notices, while every blocked attempt is still audited."
context: |-
  What is wrong today (branch codex/migration-safety-remediation at 2e2e728):
  - Owner notices skip the actor (service.py _notify_owners, 'id<>?'). Only App Owners can remove an attachment link or unmark a final result, so on a single-owner install nobody is told about attachment_removal_blocked (final-result guard), final_result_unmarked or attachment_removed. Owner decision Item 2 on 6G89SJ says notify the App Owner on ALL of these.
  - Blocked-attempt notices (*_blocked kinds) are unlimited: one person retrying can fill the inbox (GTEYTG review gap: cap blocked notices per actor per 10 minutes).
  - owner_change_blocked has a same-key 10-minute dedupe that also drops the AUDIT row, so repeats are not audited.
  - A blocked import with no target project writes no audit row at all; the notice is the only record.
  Triggered by: independent review 4 of 6G89SJ (gap 1) and the GTEYTG follow-up. Aly approved the plan in Slack thread ts 1790256175.671249: 'yes update as per your recommendation, and move on' (ts 1790268694.030539), plan ts 1790269196.282199, write lock #5 ts 1790269492.403129.
  Decided scope:
  - Self-notice only for attachment_removal_blocked, final_result_unmarked, attachment_removed. Ordinary owner actions stay un-self-notified (Z24KVH).
  - Cap: at most 5 blocked-kind notices per (recipient, actor) per rolling 10 minutes, pooled across kinds and targets; past the cap only the notice is skipped, never the audit row. Self-notices are not exempt.
  - Needs schema v17: notifications.actor_user_id (nullable, no backfill) + index (user_id, actor_user_id, created_at).
  Not in scope: daily digests (F9HBSJ), hosted attachments (MXY7BG).
definition-of-done: "Acting owner is notified of attachment_removal_blocked, final_result_unmarked and attachment_removed (single-owner install covered); other kinds unchanged; schema v17 adds notifications.actor_user_id with index, fresh and upgraded databases equal; at most 5 blocked-kind notices per recipient and actor per 10 minutes, audit row always written, a different actor still notifies, notices resume after the window; owner_change_blocked audits every repeat; a blocked import with no project is audited; unit and migration tests; existing tests green."
tags:
  - astra
blocked-by: []
related:
  - 01M2JNPRGYD7TGGSHZV16G89SJ
  - 01M39HQB2EFDXWXH92WYGTEYTG
  - 01M2HPH35W0MHCMKGRQ9Z24KVH
commits: []
created-at: 2026-09-24T17:06:51Z
updated-at: 2026-09-24T17:28:53Z
updated-by: Claude
claimed-by: vm-6361
claimed-at: 2026-09-24T17:07:27Z
outcome-what: "Owner notices: attachment_removal_blocked, final_result_unmarked and attachment_removed now also reach the owner who acted, with a summary naming the task, the attachment or final result, and the actor. Schema v17 adds notifications.actor_user_id (nullable, no backfill) and idx_notifications_actor; every notice stores its actor. Blocked-attempt notices (attachment add/removal, final-result mark/unmark, protected action, owner change) are capped at 5 per recipient and actor per rolling 10 minutes, pooled across kinds and targets; the audit row is always written. owner_change_blocked no longer skips the audit row for same-key repeats. A blocked import with no target project is audited as a user_events import_blocked row about the actor, shown with the blocked attempts on the People screen."
outcome-why: "Review 4 of 6G89SJ (gap 1): only owners can remove or unmark, and owners were never self-notified, so a single-owner install heard nothing of Owner decision Item 2 outcomes. GTEYTG review gap: one person could flood the inbox with blocked notices. The old dedupe dropped audit rows and the no-project import had no audit at all. Aly approved (Slack ts 1790268694.030539, plan ts 1790269196.282199)."
outcome-resolves: "Every DoD clause: self-notice for the three kinds with single-owner test; other kinds unchanged (ordinary notices uncapped test, Z24KVH tests green); v17 fresh equals upgraded and step rollback tested; cap per recipient and actor with audit always written, different actor still notified, resume after window; owner_change_blocked audits every repeat; no-project import audited; 416 tests OK."
---

# Blocked-attempt notices: notify the acting owner for Item 2 events and cap repeats per person

## Definition of Done

- [x] Acting owner is notified of attachment_removal_blocked, final_result_unmarked and attachment_removed (single-owner install covered); other kinds unchanged; schema v17 adds notifications.actor_user_id with index, fresh and upgraded databases equal; at most 5 blocked-kind notices per recipient and actor per 10 minutes, audit row always written, a different actor still notifies, notices resume after the window; owner_change_blocked audits every repeat; a blocked import with no project is audited; unit and migration tests; existing tests green.
  proof: service.py SELF_NOTICE_KINDS/_notify_owners; BLOCKED_NOTICE_* + _blocked_notices_capped; _owner_change_blocked; _audit_import_blocked; db.py _migrate_v17. Tests: test_core test_single_owner_is_notified_of_own_blocked_removal_unmark_and_removal, test_blocked_notices_are_capped_per_actor_and_every_attempt_is_audited, test_blocked_notice_cap_is_per_actor, test_owner_self_notices_are_capped_too_and_ordinary_notices_are_not, test_repeated_blocked_owner_changes_are_all_audited_and_notices_capped; test_import test_manager_into_unmanaged_project_viewer_and_chairman_are_blocked_and_owner_notified; test_db NotificationActorMigrationTests (3). Ran 416 tests, OK.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Schema v17 in db.py: notifications.actor_user_id (nullable, FK users) + idx_notifications_actor(user_id, actor_user_id, created_at); bump SCHEMA_VERSION
  proof: src/astra/db.py _migrate_v17, V17_NOTIFICATION_ACTOR_INDEX, SCHEMA_VERSION=17; test_db NotificationActorMigrationTests
- [x] service.py: _notify takes actor_id and stores it; BLOCKED_NOTICE_KINDS cap (5 per recipient+actor per 600 s) checked in _notify; constants next to the login throttle
  proof: service.py BLOCKED_NOTICE_* constants after LOGIN_MAX_FAILURES; _notify actor_id + _blocked_notices_capped
- [x] service.py: SELF_NOTICE_KINDS include the actor in _notify_owners for attachment_removal_blocked, final_result_unmarked, attachment_removed; summary names actor and attachment
  proof: service.py SELF_NOTICE_KINDS; _notify_owners; _event/_notify_owner summary names item and actor
- [x] service.py: owner_change_blocked audits every attempt (drop same-key dedupe); blocked no-project import audited in user_events (target = actor); list_user_events and People view group it with blocked rows
  proof: service.py _owner_change_blocked (dedupe removed); _audit_import_blocked import_blocked user event; list_user_events; app.js renderPeople blocked filter + label
- [x] Tests: update test_core 1453/2344/2377; add self-notice, cap, per-actor, window reset, no-project import audit, v17 migration tests
  proof: test_core: test_single_owner_is_notified_of_own_blocked_removal_unmark_and_removal, test_blocked_notices_are_capped_per_actor_and_every_attempt_is_audited, test_blocked_notice_cap_is_per_actor, test_owner_self_notices_are_capped_too_and_ordinary_notices_are_not, test_repeated_blocked_owner_changes_are_all_audited_and_notices_capped; updated test_attachment_marked_as_final_result_cannot_be_removed, test_secondary_owner_cannot_change_owner_access_or_target_other_owners; test_import no-project audit; test_db v17 x3
- [x] Handoff/README figures; full suite, diff --check, jaira validate, adversarial re-read; move to review; commit locally
  proof: tests/run.py Ran 416 tests OK (was 409); git diff --check clean; node --check app.js ok; CLAUDE_HANDOFF_2026-09-24.md and CLAUDE.md figures v17/416

## Progress
- **2026-09-24 17:12 · Claude** — Choices (Claude, 2026-09-24): (1) A blocked import with no target project is audited as a user_events row, event_type import_blocked, target_user_id = actor_user_id = the actor (user_events is the established table for audit rows with no project or task, GTEYTG; project_events needs a project). list_user_events and the People screen group it with the blocked attempts, so it never pushes a grant out of view. The notice kind stays protected_action_blocked. (2) The cap is checked in _notify with a COUNT on notifications; two concurrent requests could both pass at 4, so the cap is soft by at most the number of simultaneous requests. (3) The cap counts notices, not attempts: the window slides on notices sent. (4) Self-notice summary: '<kind>: <task> · <attachment or final-result title> · by <actor>'; time is created_at. (5) Every notification now stores actor_user_id where an actor exists (all _notify callers pass it).
- **2026-09-24 17:28 · Claude** — Review 5 (approve-with-follow-ups) fixed in commit C: owner_change_blocked has its own cap bucket; the notice that reaches the cap says further attempts are in history only; list_user_events limits owner changes and blocked imports separately (50 each) and the People screen shows them as two lists; window edge, NULL-actor rows and the no-project import cap are pinned by tests; test_db v17 tests moved above the main guard. Documented follow-ups, not done: gap 5 the cap is soft under concurrency (COUNT and INSERT can race; overshoot at most concurrent requests minus 1); gap 6 every scripted owner-change attempt and no-project import preview adds a user_events row with no rate limit (rate-limit at the HTTP layer for the hosted deployment); gap 9 the handoff's v16 bullet reads as current until the v17 bullet below it.
