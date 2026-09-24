---
id: 01M3ADCB413BRFJTKCEXZ72D79
title: Record settings changes and let owners reopen a closed project
status: backlog
ready: true
creator: Claude
assignee: Aly Jafferani
goal: "Every change to a project's or the app's settings leaves an audit record (who, when, old and new value), and an owner can reopen a closed project with a recorded reason."
context: "What is wrong today (branch codex/migration-safety-remediation at 39f4faf; line numbers from the option-4 scout at that commit):\n- These settings changes write no audit row and notify nobody (src/astra/service.py):\n  - project working days (set_working_days, ~749)\n  - project holidays add/remove (~767, ~780)\n  - project budget (set_project_budget, ~788)\n  - project entities and primary entity (~669, ~834)\n  - app-wide: entity active flag (~652) and the import template configuration (~3549; only the last updated_by and version are kept)\n- A closed project cannot be reopened: close_project (~2984) has no reverse path, so a mistaken close is permanent.\n- Project closes and date changes are already audited and, since XX9RFM, notified to the other owners.\nTriggered by: Aly asked for this as a separate ticket (Slack thread ts 1790256175.671249, ts 1790276936.363329: 'A record of settings changes and a way to reopen projects will go on a separate ticket. Okay').\nOpen questions for Aly before building:\n- Who may reopen a closed project (any owner, like close, or the primary only)?\n- Should settings changes also notify the other owners, or only be recorded in history?\n- Where the app-wide changes are shown (People screen history, or a new settings history)."
definition-of-done: "Each listed settings change writes an audit row with actor, time and before/after values, shown in the relevant history; an owner (as Aly decides) can reopen a closed project with a required reason, recorded and notified; tests for each change and for reopen; existing tests green."
tags:
  - astra
blocked-by: []
related:
  - 01M3ADA4DRPMWYVBJ2ZJXX9RFM
  - 01M39HQB2EFDXWXH92WYGTEYTG
commits: []
created-at: 2026-09-24T19:13:21Z
updated-at: 2026-09-24T19:18:35Z
updated-by: Claude
---

# Record settings changes and let owners reopen a closed project

## Definition of Done

- [ ] Each listed settings change writes an audit row with actor, time and before/after values, shown in the relevant history; an owner (as Aly decides) can reopen a closed project with a required reason, recorded and notified; tests for each change and for reopen; existing tests green.

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

## Progress
- **2026-09-24 19:18 · Claude** — Filed by Claude 2026-09-24 under write lock #7 at Aly's request (ts 1790276936.363329). Nothing started; waits in backlog for Aly's answers to the open questions in the context.
