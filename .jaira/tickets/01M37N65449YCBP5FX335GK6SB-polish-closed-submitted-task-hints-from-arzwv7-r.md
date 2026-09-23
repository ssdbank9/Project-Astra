---
id: 01M37N65449YCBP5FX335GK6SB
title: Polish closed/submitted task hints from ARZWV7 review
status: review
ready: true
creator: Claude
assignee: Claude
goal: "The task dialog's submitted-task hint names the buttons the viewer actually has, sits under the Status field it explains, the lifecycle code reuses one closed-status constant, and the test click driver matches the attribute it is told to."
context: |-
  What is wrong (low findings from the independent review of ARZWV7, already on codex/migration-safety-remediation):
  - A Manager on a submitted task reads 'Use Accept or Request changes under Lifecycle.' but their buttons say 'Request Owner acceptance' and 'Request Owner to return changes'. Hint: src/astra/static/app.js renderDetail (statusHint). Buttons: buildLifecycle.
  - The hint #status-locked-hint renders after the whole Status/Start/Due/Progress grid, not under the Status field. The select points at it with aria-describedby; keep that.
  - buildLifecycle checks a third copy of the closed list ['completed','cancelled','abandoned'] (const terminal) instead of CLOSED_STATUSES at the top of app.js.
  - tests/test_web.py WIRING_DRIVER picks the click target by ANY data-* value: ['data-remove-pred','t1'] also matches data-remove-succ="t1". On an open task t1 that is the wrong Remove button. Closed-task tests pass only because that button is hidden there.
  Scope: UX only. The server stays the authority. Reuse existing styles. No server change.
definition-of-done: "A Manager on a submitted task sees a hint naming 'Request Owner acceptance' and 'Request Owner to return changes'; an Owner sees 'Accept & complete' and 'Request changes' (tests/test_web.py)"
tags:
  - astra
blocked-by: []
related: []
follows: 01M37E16BEYFDWD0DP18ARZWV7
commits: []
created-at: 2026-09-23T17:32:03Z
updated-at: 2026-09-23T17:42:42Z
updated-by: Claude
claimed-by: vm-8047
claimed-at: 2026-09-23T17:32:33Z
outcome-what: "Submitted-task hint names the viewer's own decision buttons (shared decisionLabels helper) and sits in the Status grid cell; buildLifecycle and render() reuse CLOSED_STATUSES; WIRING_DRIVER matches the named data-* attribute, with an open-task unlink scenario"
outcome-why: Manager was told to use buttons they do not have; the hint was detached from the field it describes; a duplicated closed list could drift; the test driver could click the wrong Remove and pass or fail for the wrong reason
outcome-resolves: The four low findings from the ARZWV7 independent review
---

# Polish closed/submitted task hints from ARZWV7 review

## Definition of Done

- [x] A Manager on a submitted task sees a hint naming 'Request Owner acceptance' and 'Request Owner to return changes'; an Owner sees 'Accept & complete' and 'Request changes' (tests/test_web.py)
  proof: src/astra/static/app.js decisionLabels() shared by statusHint and buildLifecycle buttons; tests/test_web.py test_submitted_hint_names_the_buttons_this_viewer_has; Chromium after.json hint text per role
- [x] #status-locked-hint sits directly under the Status select, before the Start date field, and the select keeps aria-describedby="status-locked-hint"
  proof: app.js statusField wraps Status label + #status-locked-hint in one grid cell; test_submitted_hint_sits_under_the_status_field and test_submitted_task_locks_status_and_points_to_the_decision (aria-describedby); Chromium: hint 12px under select, before Start date in DOM
- [x] buildLifecycle reuses CLOSED_STATUSES; app.js has one closed-status list literal
  proof: buildLifecycle and render() use CLOSED_STATUSES; test_closed_statuses_are_listed_once
- [x] WIRING_DRIVER matches the named data-* attribute only; an open-task click on ['data-remove-pred','t1'] removes the t1->t2 link, and the affected wiring tests still fail against pre-ARZWV7 app.js for the right reason
  proof: tests/test_web.py WIRING_DRIVER matches n.dataset[key]===value; scenario unlink-successor-open in test_dependency_controls_on_an_open_task_still_work. Against pre-ARZWV7 app.js (fa82cc7^) the old driver failed the unlink tests by clicking the wrong Remove (t0->t1); new driver passes them (pre-ARZWV7 Remove worked). Against ARZWV7 round-1 app.js (fa82cc7) they fail with the TypeError round 2 fixed
- [x] Before/after Chromium screenshots (Manager and Owner on a submitted task, 127.0.0.1, synthetic data); full suite, node --check, compileall and git diff --check pass
  proof: ui-shots/polish-before-*.png and polish-after-*.png (manager/owner submitted edit+lifecycle); tests/run.py Ran 305 OK; node --check ok; compileall ok; git diff --check clean for changed files

## Options

- [ ] brainstorm
- [x] planning

## Plan

<Steps, in order — filled in by the pre-process step, or by you.>

- [x] failing tests: per-role hint text, hint position under Status, single closed-list literal, open-task named-attribute click
- [x] fix WIRING_DRIVER to match the named data-* attribute
- [x] check affected wiring tests against pre-ARZWV7 app.js (fa82cc7^) fail for the right reason
- [x] add decisionLabels helper shared by buildLifecycle buttons and statusHint
- [x] move hint into a grid cell with the Status label; reuse CLOSED_STATUSES in buildLifecycle
- [x] before/after Chromium screenshots, Manager and Owner, submitted task
- [x] full suite, node --check, compileall, git diff --check

## Progress
- **2026-09-23 17:32 · Claude** — Brainstorm. What the code shows: app.js renderDetail statusHint says 'Use Accept or Request changes under Lifecycle.' whenever can_decide_protected||can_request_protected; buildLifecycle labels are 'Accept & complete'/'Request changes' (Owner) vs 'Request Owner acceptance'/'Request Owner to return changes' (Manager). Hint <p> is emitted after </div> of .grid. buildLifecycle has const terminal=[...closed list...]. WIRING_DRIVER: find(n=>Object.values(n.dataset).includes(pick[1])) ignores pick[0] beyond the selector, and the selector [data-remove-pred] matches the Remove button that also carries data-remove-succ. Options for the hint: (a) branch the hint text by role with its own strings - cheap, but the strings can drift from the buttons again; (b) one small helper returning the two decision labels used by both the buttons and the hint - one source of truth, tiny; (c) drop button names from the hint and say 'see Lifecycle' - vague, loses the point of the hint. Choose (b). Placement: wrap the Status label and hint in one grid cell div (a hint inside the <label> would join the select's accessible name). Driver: match n.dataset[camel(attr)]===value.
- **2026-09-23 17:33 · Claude** — Plan rests on: the hint cannot go inside the Status <label> because label text becomes the select's accessible name; a <div> grid cell holding label+hint keeps the 2-column grid and aria-describedby. The driver's harness code runs via indirect eval in global scope, so the driver-local camel() is not visible there; the attribute-to-dataset key conversion is inlined in the harness.
- **2026-09-23 17:42 · Claude** — What the repo does not say: (1) Under the old WIRING_DRIVER, the closed-task unlink tests also failed against pre-ARZWV7 app.js, but for the wrong reason: that app rendered the incoming 'Depends on' Remove too, and the driver clicked it (it carries data-remove-succ="t1"), sending t0->t1. With the named-attribute match they pass there, which is right: removal worked before ARZWV7. They guard the ARZWV7 round-1 regression, and against fa82cc7's app.js they fail with 'TypeError: Cannot set properties of null (setting textContent)' - the missing #add-dep-error round 2 fixed. (2) render() at app.js line 22 had a second copy of the closed list; switched too. Safe: CLOSED_STATUSES is a top-level const read only when render() runs. (3) The hint sits 12px under the select because label{margin:12px 0}; no new CSS added, per 'reuse existing styles'. (4) The no-permission branch of the hint ('The App Owner will Accept or Request changes.') is unchanged; it names no button for that viewer. (5) git diff --check against origin shows EOF blank lines in other tracks' tickets (67T315, EXEZPM) because origin moved on; none in files this ticket touches.
