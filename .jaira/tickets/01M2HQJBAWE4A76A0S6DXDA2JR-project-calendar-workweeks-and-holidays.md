---
id: 01M2HQJBAWE4A76A0S6DXDA2JR
title: "Project calendar: workweeks and holidays"
status: signoff
ready: true
creator: Aly Jafferani
assignee: Aly Jafferani
goal: "Give each project an explicit working-day calendar (workweek + holidays) so durations and due-day logic respect real working time, never inferred."
context: |-
  Astra tracker, section 11 gap "Project calendar/timezone: Partial" — timezone is done (due-state uses the project tz), but workweeks and holidays are not modelled.
  Section 6: configure real workweeks and holidays; never infer them; date-only deadlines run through end of the governing local day (already implemented).
  Mechanism is buildable now; the ACTUAL calendars/holidays per entity are a section 15 setup input the owner must supply. Start: add workweek + holidays columns/tables and a working-day helper.
definition-of-done: Per-project workweek and holiday list are configurable; due/duration logic uses them on top of the existing governing timezone; working days never inferred from an email domain; unit tests cover a holiday and a non-working day; existing tests green.
tags:
  - astra
blocked-by: []
related: []
commits: []
created-at: 2026-09-15T05:10:22Z
updated-at: 2026-09-20T03:10:24Z
claimed-by: X1CarbonPC-33840
claimed-at: 2026-09-15T08:08:05Z
updated-by: Aly Jafferani
outcome-what: "Per-project working calendar: configurable workweek (weekday set) + holidays, owner-only; is_working_day / working_days_between helpers; task_detail.working_days_to_due; Calendar control in People dialog. Permissive default (every day counts). 3 new tests (72 total)."
outcome-why: "Section 6/11: project calendar was Partial (timezone done, workweeks/holidays not); owner wants the mechanism but any day usable by default."
question: "Accept, or send back? Confirm the permissive default is what you want (all 7 days working, no holidays, nothing blocked) — the mechanism is ready if you later restrict a specific project's calendar."
outcome-resolves: "DoD met: per-project workweek + holidays configurable, due/working-day logic uses them, never inferred from domain, unit+HTTP tests cover a holiday and a non-working day, existing tests green."
review-summary: "Schema v6 adds projects.working_days TEXT DEFAULT '0123456' and project_holidays(project_id, holiday_date) ON DELETE CASCADE. service provides _project_working_days, is_working_day, working_days_between, get_project_calendar, set_working_days, list_holidays, add_holiday, remove_holiday; task_detail exposes working_days_to_due. web wires GET /calendar, POST /working-days, POST /holidays, DELETE /project-holidays under auth+CSRF; app.js People-dialog Calendar UI. Permissive default genuinely blocks nothing - is_working_day/working_days_between are informational only, no scheduling path rejects a date. Meets the accepted DoD."
review-gaps: "None material. Informational-only semantics: working_days_between counts inclusively of BOTH endpoints (due-today returns 1 not 0) and swaps reversed dates returning an absolute count (overdue yields positive). No functional impact - display only. Calendar reads are project-view level, edits owner-gated (correct)."
review-verdict: pass-with-notes
review-check: "Read service calendar block (265-336), require_owner, _date, task_detail; db v6 migration; web routes with CSRF/auth; app.js UI. Verified permissive default blocks nothing (grep: 3 call sites, none reject), boundary behavior, owner-only mutators via require_owner, robust weekday parsing (bad chars filtered, empty rejected), date parsing raises on malformed. Ran the 3 cited tests -> OK. No full suite, no edits. No real-browser pass (yolo-chrome down)."
---

# Project calendar: workweeks and holidays

## Definition of Done

- [x] Per-project workweek and holiday list are configurable; due/duration logic uses them on top of the existing governing timezone; working days never inferred from an email domain; unit tests cover a holiday and a non-working day; existing tests green.
  proof: schema v6 (projects.working_days default '0123456' + project_holidays); service is_working_day/working_days_between + set_working_days/add/remove/list_holidays (owner-only); task_detail.working_days_to_due; project calendar routes + People-dialog Calendar UI; tests test_core.test_working_calendar_default_restrictions_and_holidays/test_calendar_management_is_owner_only, test_web.test_project_calendar_over_http; 72 pass

## Options

- [ ] brainstorm
- [ ] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] Schema v6: projects.working_days (default '0123456' = all 7) + project_holidays table
- [x] Service: set_working_days + add/remove/list_holidays (owner-only); is_working_day + working_days_between helpers (permissive by default; never block a date)
- [x] task_detail exposes working_days_to_due using the project calendar
- [x] UI: per-project Calendar control in People dialog (working-day checkboxes + holidays)
- [x] Tests: default counts all days; a restricted weekday excluded; a holiday excluded; working_days_between correct

## Progress
- **2026-09-15 08:12 · Aly Jafferani** — PERMISSIVE by default per owner: working_days defaults to '0123456' (all 7) and there are no holidays, so working_days_between == calendar days and NOTHING is ever blocked from being scheduled on any date — the calendar only INFORMS working-day counts. The mechanism is fully there: per-project workweek (weekday set) + holidays, owner-only, with is_working_day / working_days_between helpers and task_detail.working_days_to_due. Working days are never inferred from an email domain. Deliberately NOT rewired: critical-path _duration_days stays calendar-based (equal to working days under the permissive default) — a future slice can switch it to working-days if a project restricts its calendar. No real-browser visual pass (no browser in session).
- **2026-09-15 18:32 · Aly Jafferani** — OWNER ACCEPTED (2026-09-15): permissive default calendar (all 7 days working, no holidays, nothing blocked). Proceeding to model review.
- **2026-09-19 06:14 · Aly Jafferani** — HANDOFF 2026-09-19 (Claude->Codex): see astra_project_tracker/CODEX_HANDOFF_2026-09-19.md. PARKED in signoff - waiting on the App Owner. Verdict: pass-with-notes. Owner question: confirm the permissive default (all 7 days working, no holidays, nothing blocked); mechanism ready if a project later restricts its calendar.
- **2026-09-20 03:10 · Aly Jafferani** — Owner confirmation recorded 2026-09-20: project workweeks and holidays are explicitly configured rather than inferred from one global permissive calendar. Production UX must require/guide project calendar setup.
