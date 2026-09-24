---
id: 01M3A930RYSAXPWQVQP3PDDS2D
title: Server command to transfer the primary owner and reset a password
status: review
ready: true
creator: Claude
assignee: Claude
goal: "Whoever runs the Astra server can hand the primary-owner role to a secondary owner and reset any active user's password from the command line, safely, audited and without a traceback, so a locked-out or departing primary is never a dead end."
context: |-
  What is wrong today (branch codex/migration-safety-remediation at 719ccbb):
  - There is no way to change who the primary owner is. Only the primary grants or removes owner access (service.py grant_secondary_owner / revoke_secondary_owner), and nobody can demote the primary.
  - There is no password reset or change anywhere: no API, no UI, no CLI. A user who forgets a password, including the primary owner, is locked out for good.
  - The only CLI commands are 'astra init-owner' and 'astra serve' (src/astra/__main__.py). A service ValueError there prints a Python traceback.
  Triggered by: option 3 in the 2026-09-24 handoff (CLAUDE_HANDOFF_2026-09-24.md section 5). Aly approved the plan in Slack thread ts 1790256175.671249 (plan approval ts 1790272579.421269, write lock #6 ts 1790272638.185789).
  Decided (recommended defaults; Aly did not pick 'owners only' for reset, so reset works for ANY active user, behind one clearly named check):
  - 'astra transfer-primary --to EMAIL [--yes]': the target must be an active secondary owner; the old primary stays a secondary owner and is signed out everywhere.
  - 'astra reset-password --email EMAIL [--yes]': password typed twice with getpass, never from argv or env; 12+ characters; signs the user out everywhere and clears their failed sign-ins.
  - Unless --yes, the operator types the target's email to confirm. Exit 0 done, 1 refused or aborted, 2 usage.
  - Audit: user_events rows primary_owner_transferred and password_reset, actor = the target user (user_events.actor_user_id is NOT NULL), detail via=cli plus OS user and host; the People screen shows 'via server command'.
  - No schema change (still v17).
  Trust boundary: anyone who can run the CLI can already write the SQLite file; the command adds correctness and an audit row, not power.
  Not in scope: in-app 'change my password' or owner-initiated resets.
definition-of-done: "transfer-primary moves the primary flag to an active secondary owner in one transaction (exactly one primary always), keeps the old primary as a secondary owner, signs them out, audits and notifies the other active owners including the old primary, and refuses (changing nothing) an unknown, inactive, non-owner or already-primary target or a database with no primary; reset-password sets a 12+ character password read only from getpass twice for any active user, signs them out everywhere, clears failed sign-ins, audits and notifies the user (and other owners when the user is an owner); both ask for the target email unless --yes, exit 0/1/2 and never print a traceback; People screen labels both 'via server command'; README documents Windows and Linux use; service and CLI tests; existing tests green."
tags:
  - astra
blocked-by: []
related:
  - 01M39HQB2EFDXWXH92WYGTEYTG
commits: []
created-at: 2026-09-24T17:58:21Z
updated-at: 2026-09-24T18:37:17Z
updated-by: Claude
claimed-by: vm-13753
claimed-at: 2026-09-24T17:58:31Z
outcome-what: "New server commands: 'astra transfer-primary --to EMAIL [--yes]' moves the primary flag to an active secondary owner in one transaction (old primary stays a secondary owner, is signed out everywhere); 'astra reset-password --email EMAIL [--yes]' sets a 12+ character password read twice with getpass (interactive terminal required) for any active user, signs them out everywhere and clears failed sign-ins. Both print the database first and refuse a missing one, ask for the target email unless --yes, record user_events primary_owner_transferred / password_reset (actor = target, detail via=cli with OS user and host), and exit 0/1/2 with one-line errors (init-owner and serve bind errors too). A transfer notifies every active owner; a reset notifies the user, and the other owners only when the user is an owner. Owner-access writes re-check the actor is still the active primary inside the transaction. People screen labels them 'via server command'. README documents Windows and Linux use."
outcome-why: "There was no way to change the primary owner or reset any password; a locked-out or departing primary was a dead end (handoff option 3). Aly approved the plan (Slack ts 1790272579.421269; lock #6 ts 1790272638.185789)."
outcome-resolves: "Every DoD clause is covered by the ServerCommandTests, ServerCommandCliTests and test_web server-command tests: single transaction and one primary (rowcount guards and write-lock check pinned), refusals change nothing, missing database refused without creating one, sessions revoked, throttle cleared, audit rows, notification recipients, typed confirmation and --yes, interactive terminal required, no traceback, no argv password; stale primary actors re-checked inside owner-access writes; 438 tests OK."
---

# Server command to transfer the primary owner and reset a password

## Definition of Done

- [x] transfer-primary moves the primary flag to an active secondary owner in one transaction (exactly one primary always), keeps the old primary as a secondary owner, signs them out, audits and notifies the other active owners including the old primary, and refuses (changing nothing) an unknown, inactive, non-owner or already-primary target or a database with no primary; reset-password sets a 12+ character password read only from getpass twice for any active user, signs them out everywhere, clears failed sign-ins, audits and notifies the user (and other owners when the user is an owner); both ask for the target email unless --yes, exit 0/1/2 and never print a traceback; People screen labels both 'via server command'; README documents Windows and Linux use; service and CLI tests; existing tests green.
  proof: service.py transfer_primary_owner/reset_password (+checks), __main__.py commands; tests: test_core ServerCommandTests test_transfer_moves_the_primary_flag_and_keeps_the_old_primary_as_secondary, test_transfer_refusals_change_nothing, test_a_failure_part_way_through_a_transfer_changes_nothing, test_reset_password_for_any_active_user, test_reset_password_of_an_owner_tells_the_other_owners, test_reset_password_refusals_change_nothing; ServerCommandCliTests test_transfer_primary_needs_the_typed_email_unless_yes, test_refusals_exit_with_one_line_and_no_traceback, test_reset_password_reads_the_password_twice_from_the_terminal_only; test_web test_server_command_transfer_applies_on_the_next_request. Review 6 fixes: test_a_target_or_primary_that_changed_after_the_check_is_refused, test_the_transfer_check_runs_under_the_write_lock, test_a_stale_old_primary_can_no_longer_change_owner_access, test_recovery_commands_refuse_a_missing_database_without_creating_one, test_reset_password_needs_an_interactive_terminal, test_database_errors_print_one_line. test_serve_on_a_busy_port_prints_one_line. Ran 438 tests, OK.

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] service.py: transfer_primary_owner(to_email, via) and reset_password(email, password, via) next to the GTEYTG block; can_reset_password check (any active user); audit + notices; one transaction each
  proof: service.py server-command block before list_user_events: user_by_email, current_primary_owner, check_primary_transfer, transfer_primary_owner, can_reset_password, check_password_reset, reset_password
- [x] __main__.py: transfer-primary and reset-password subcommands, email confirmation unless --yes, getpass twice, clean one-line errors (init-owner too), exit 0/1/2
  proof: src/astra/__main__.py transfer-primary/reset-password, _confirm, _read_new_password, _via, clean SystemExit for ValueError/KeyError/Conflict/Forbidden and Ctrl-C
- [x] app.js: labels for primary_owner_transferred and password_reset, 'via server command'
  proof: app.js OWNER_EVENT_LABELS + SERVER_COMMAND_EVENTS in renderPeople ownerEventRow
- [x] Tests: service (happy, refusals, atomicity, sessions, throttle, audit, notices) and CLI (confirmation, --yes, no traceback, no argv password); web People label if a pattern exists
  proof: test_core ServerCommandTests (6), ServerCommandCliTests (3); test_web test_server_command_transfer_applies_on_the_next_request + static label assertions
- [x] README usage (Windows and Linux ASTRA_HOME); handoff v16 bullet as history, figures
  proof: README Run locally recovery commands; CLAUDE_HANDOFF_2026-09-24.md v16 bullet marked history, 431 tests; CLAUDE.md 431
- [x] Full suite, diff --check, node --check, jaira validate, adversarial re-read; move to review; commit locally
  proof: tests/run.py Ran 431 tests OK (was 421); git diff --check clean; node --check ok

## Progress
- **2026-09-24 18:06 · Claude** — Choices (Claude, 2026-09-24): (1) reset targets any active user, behind AstraService.can_reset_password (one place to narrow to owners). (2) Audit actor = target user (user_events.actor_user_id is NOT NULL); detail carries via=cli, os_user, host; People screen shows 'via server command' and hides the reason ('server command'). (3) Transfer notifies the new primary and every other active owner including the old primary; a reset notifies the user and, for an owner, the other active owners. (4) The eligibility check runs before the confirmation and again inside the write transaction. (5) The confirmation compares the typed email case-insensitively after trimming. (6) The CLI turns ValueError/KeyError/Conflict/Forbidden into a one-line SystemExit (status 1); this also fixes init-owner's traceback. Ctrl-C/EOF at a prompt prints 'Aborted; nothing was changed.' (7) No in-app password change: out of scope.
- **2026-09-24 18:23 · Claude** — Review 6 (approve-with-follow-ups) fixed in the next commit: recovery commands print the database first and refuse a missing file without creating one; transfer guards (both rowcount checks, check inside the write lock) pinned by tests that fail when reverted; grant/revoke and owner-target user changes re-check the actor is still the active primary inside the write transaction (stale old-primary actor now Forbidden and audited); reset-password needs an interactive terminal; sqlite OperationalError and OSError print one line (exit 1). Follow-up, not done (review 6 gap 6): the CLI's broad catch of ValueError/KeyError also wraps serve and init-owner, so a programming error raising those at startup shows one line instead of a traceback.
