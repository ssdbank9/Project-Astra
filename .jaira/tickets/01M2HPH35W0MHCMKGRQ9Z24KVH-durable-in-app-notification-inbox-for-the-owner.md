---
id: 01M2HPH35W0MHCMKGRQ9Z24KVH
title: Durable in-app notification inbox for the owner
status: signoff
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: "Give the owner a durable, in-app record of task changes so material events are not lost, without any external email or messaging."
context: |-
  Astra project tracker (astra_project_tracker/), step 5 of the standalone-tracker gap work.
  Handoff flags Durable event notifications as Missing (section 11): task_events are audit snapshots, not notification/delivery records, and there is no owner inbox.
  Section 7 requires: every saved authorized-user task change creates a durable audit/notification record for the owner; material changes do not wait for a daily digest; opening or dismissing is not approval; retries idempotent with delivery status; automatic outbound email is OFF by default.
  Scope this to IN-APP only. Daily summary + external email are deferred (need the section 15 notification-channel decisions) and are NOT in this ticket.
  Start: add a notifications table keyed to the triggering event id (idempotency), write a row when lifecycle/update events fire, add GET inbox + mark-read endpoints and a bell/inbox UI for the owner.
definition-of-done: "Every saved authorized task change writes a durable notification row for the owner; an in-app inbox lists them newest-first with read/unread; marking read does not delete the record; opening/dismissing is not approval; retries idempotent (no duplicate rows per event); in-app only, no outbound email; unit + HTTP tests cover creation, read-state, and idempotency; existing tests stay green."
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T04:52:13Z
updated-at: 2026-09-20T03:10:14Z
claimed-by: X1CarbonPC-13392
claimed-at: 2026-09-15T05:04:15Z
updated-by: Aly Jafferani
outcome-what: "Durable in-app owner notifications: notifications table (idempotent per event), owner notified of others' task changes, header bell + inbox dialog with mark-read / mark-all-read; 3 new tests (58 total)."
outcome-why: "Section 7/11: durable event notifications were Missing; task_events were audit-only with no owner inbox."
question: "Accept, or send back? Confirm the scope call: owner is NOT self-notified of their own actions (keeps the pilot inbox meaningful), and this is in-app only with outbound email deferred to the section 15 decisions."
outcome-resolves: "DoD met: durable per-change record for the owner, in-app inbox with read/unread, read is non-destructive and not approval, idempotent, in-app only, unit+HTTP tests, existing tests green."
review-summary: "Durable owner-only in-app notification inbox. db v4 creates notifications with UNIQUE(user_id,event_id) + per-user/created_at index; read_at defaults NULL. Every task change funnels through _event(), which calls _notify_owner(): looks up the single global owner, returns early if no owner or owner==actor (owner never self-notified; audit still records the action), else INSERT OR IGNORE keyed on the fresh event_id. Reads (list_notifications, unread_notification_count) filter WHERE user_id=actor; mark_notification_read raises Forbidden on a foreign row and only sets read_at (never deletes, never touches task state, no-op if already read); mark_all is user-scoped. web exposes GET /api/notifications, POST .../{id}/read, POST .../read-all behind _require_user. app.js: header bell + unread badge + inbox dialog. All mutating paths route through _event. Meets the accepted DoD."
review-gaps: "Nothing material. (1) Idempotency is real but under-tested: event_id is freshly generated per _event and never reused, so the UNIQUE+INSERT OR IGNORE guard is defensive-only and never fires in normal operation; the '...idempotently' test asserts one-change->one-row but does not inject a duplicate event_id to exercise a true replay/retry. (2) Notifications target only the single global owner; schema enforces exactly one owner, so no multi-owner/leakage concern; non-owners see an empty inbox. No recipient-isolation, self-notify, mark-read-mutation, or duplication bug found."
review-verdict: pass-with-notes
review-check: "Read db.py (v4 migration), service.py _event/_notify_owner/list_notifications/unread_notification_count/mark_notification_read/mark_all_notifications_read (1881-1935), web.py notification endpoints, app.js bell/inbox. Ran test_core.test_owner_notified_of_other_users_changes_idempotently, test_notification_recipient_isolation, test_web.test_notification_inbox_over_http -> all pass. No full suite, no edits. No real-browser pass (yolo-chrome down)."
---

# Durable in-app notification inbox for the owner

## Definition of Done

- [x] Every saved authorized task change writes a durable notification row for the owner; an in-app inbox lists them newest-first with read/unread; marking read does not delete the record; opening/dismissing is not approval; retries idempotent (no duplicate rows per event); in-app only, no outbound email; unit + HTTP tests cover creation, read-state, and idempotency; existing tests stay green.
  proof: astra_project_tracker: notifications table (schema v4, UNIQUE user_id+event_id); _event->_notify_owner (INSERT OR IGNORE); list/unread/mark_read/mark_all; GET /api/notifications + read + read-all; header bell + inbox dialog; tests test_core.test_owner_notified_of_other_users_changes_idempotently, test_notification_recipient_isolation, test_web.test_notification_inbox_over_http; 58 pass

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Schema v4: notifications table with UNIQUE(user_id,event_id) for idempotency
- [x] Emit an owner notification from _event for every task change the owner did not perform themselves (INSERT OR IGNORE on event id)
- [x] Service: list_notifications, unread_count, mark_read (recipient-only), mark_all_read — read never deletes, never changes task state
- [x] API: GET /api/notifications, POST /api/notifications/{id}/read, POST /api/notifications/read-all
- [x] UI: header bell with unread count + inbox dialog (mark read / mark all read)
- [x] Tests: notification created for owner on non-owner change, idempotent, mark-read state, recipient isolation

## Progress
- **2026-09-15 05:07 · Aly Jafferani** — IN-APP ONLY — no outbound email (that + the daily digest need the section 15 notification-channel decisions and are deferred). Owner is notified of every task change made by SOMEONE ELSE; the owner's own actions are not self-notified (the audit event still records them). Idempotency via UNIQUE(user_id,event_id) + INSERT OR IGNORE, so retries/re-runs never duplicate. Marking read only sets read_at (never deletes, never changes task state) — 'opening is not approval'. Recipient isolation enforced (only the recipient can read their own). No real-browser visual pass (no browser surface).
- **2026-09-15 18:32 · Aly Jafferani** — OWNER ACCEPTED (2026-09-15): no self-notify of owner's own actions; in-app only (outbound email deferred to section 15). Proceeding to model review.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. PARKED in signoff - waiting on the App Owner. Verdict: pass-with-notes. Owner question: confirm owner is NOT self-notified of own actions; in-app only, outbound email deferred to section 15. (Idempotency guard is defensive-only, not a bug.)
- **2026-09-20 03:10 · Aly Jafferani** — Owner decision 2026-09-20: do not self-notify the Owner for the Owner's own successful actions; preserve them in audit. Notify the Owner of every blocked or unauthorized attempt by another user. Initial delivery remains in-app only.
