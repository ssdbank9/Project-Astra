# Critical built-work and UI/UX review — 2026-10-13

**Historical review:** F1–F9 and the related picker/token/navigation debt were
repaired in [the October 14 repair package](FRONTEND_REPAIRS_2026-10-14.md).
The findings below remain the record of the frozen pre-repair source, not
claims that the same defects persist in the supplied repaired package.
Whole-app acceptance and deployment gates remain separate.

**Verdict: do not deploy or call this top-tier UI/UX yet.** Two confirmed
frontend defects can save to the wrong task or silently remove its owner.
Passing tests and polished screenshots do not override those failures.
The recommendation is to repair integrity and error handling first, then
complete accessibility/usability checks and the existing launch gates.

This is a review, not product acceptance or implementation authorization.
Aly alone accepts work. No application/test source, real data, credentials,
accounts, hosting or external notifications were changed by this review.
Synthetic loopback fixture writes were used to reproduce defects.

## Frozen scope and evidence

- Reviewed checkout: `5f379c9031abafe417716c35e93558e8d7adfacc`.
  Application source remains `da1b3fd21ed0d4357669f0e727369fda02640672`.
  Branch `codex/migration-safety-remediation`; pull was already up to date.
- Board at review start: 86 tickets, 25 Done / 39 signoff / 8 human / 14 backlog.
  New coordination ticket **26ZF8D** adds one. Existing acceptance lanes were
  not changed. W6ZSGA, JM7CFP and 2FREQ9 already have chat acceptance.
- Primary scope: **37 unaccepted built signoff tickets plus B1 ZQQCJM**.
  All **139 numbered criteria** were read, including historical requirements
  superseded by later decisions. Four human design/handoff artifacts and the
  eight 3NT40T follow-ups were also screened: **43 records / 151 criteria**.
- [Criterion coverage](CRITICAL_REVIEW_COVERAGE_2026-10-13.md) maps each record
  and criterion to evidence or an explicit limitation. Located code and
  ticket proof are distinguished from fresh execution. A criterion can be
  partly supported while its broad visual/acceptance claim remains unverified.
- Fresh `.venv\Scripts\python.exe tests\run.py`: **Ran 832 tests in 568.186s;
  OK (skipped=1)**, exit 0. Node UI drivers ran. The skipped Windows symlink
  case remains unverified. The suite passed while the defects below existed.
- Independent source/spec reviewer read the frontend and relevant service/test
  locations and executed four actual-function JavaScript probes. Parent
  separately reproduced the principal defects in Chrome and checked persisted
  synthetic SQLite rows. A requested independent backend reviewer could not
  complete because of workspace credit availability; no backend review pass
  is inferred. The full suite and parent source inspection still completed.
- Chrome synthetic fixture: Owner, Member, Viewer and Chairman sessions;
  25 tasks, multiple entities, duplicate display names, dependencies, a subtask,
  an accepted result, a linked file, empty/closed projects and templates.
  Controlled latency/failure changed fixture HTTP responses, not app source.
  Desktop and a 390×844 viewport override were used. DOM client width was
  375 CSS pixels with the scrollbar; this is not physical-device verification.
- Independent report review checked all 43 records / 151 verbatim requirements,
  links, the fresh test receipt, source-change boundary and evidence wording.
  Two appendix corrections were applied: actual prototype paths and no implied
  fresh prototype/research test execution. The bounded report passed review;
  that does not convert the product or backend completeness into a pass.

Local-only proof is under ignored `Temp/`: `critical_ux_fixture.py`,
`critical-ux-binding.json`, `critical-ux-fixture.log`,
`critical-ui-ux-full.log` and the screenshots named below. They are not
published because browser artifacts/live databases must not enter Git.
External reviewers should independently reproduce these cases rather than
infer a pass from this report.

## Confirmed defects, ordered by consequence

### F1 — P1: task detail race writes to the wrong task

`src/astra/static/app.js:1845–1854` sets global `detailTaskId` before asynchronous
task/event loading. A late response renders without checking that it still
belongs to the selected task. `submitDetailEdit` at 2372 and `submitAssign` at
2391 use the global target rather than an immutable identity for that form.

Reproduction: with two editable tasks at revision 1, delay task A's detail
response by five seconds. Click A and immediately B from Home. B opens first;
the delayed response then replaces it with A's title, owner, dates and full-page
link. Edit that visible A form and save. The HTTP log records POST to B.
Read-only SQLite verification showed A remained "Approve scope and budget",
revision 1; B became "Synthetic wrong-target race proof", revision 2. The
post-save drawer then displayed B. This is a persisted wrong-record write,
not merely a stale heading. No owner data was involved.

Proof: `critical-ux-race-before-save.png`, `critical-ux-race-after-save.png`.
Independent probe: `displayed=A; panelTask=A; saveTarget=B`.
Related tickets: DR3PKR, 9R7A87, JZACMP, HS3JRY, 1G7Q4C and any drawer mutation.
Required repair outcome: stale responses cannot replace another task; every
mutation targets the identity/revision of the rendered form. Also test closing
the panel while loading, deep links, keyboard navigation and delayed errors.

### F2 — P1: owner lookup failure silently unassigns a task

`app.js:1809–1818` replaces assignee options with Unassigned before loading
eligible people and swallows failure. Detail initialization at 2087 does not
await it; serialization at 2374 sends the empty owner selection.

Reproduction: return HTTP 500 for `/api/assignable-users`, open an assigned
task, change only its title and save. The facts still said Jordan Project
Manager while the editable Owner control contained only Unassigned. The save
succeeded. SQLite showed `owner_user_id=NULL`, revision 2; the refreshed drawer
said Unassigned although status remained Assigned. This also risks a quick save
before a successful lookup finishes; that timing variant was independently
identified but not separately reproduced in Chrome.

Proof: `critical-ux-owner-before.png`, `critical-ux-owner-after.png`.
Related: 3FQEKB, HS3JRY, DR3PKR, 1G7Q4C. Preserve the stored owner while loading;
make lookup failure visible; block assignment submission or omit unchanged
assignment until options are valid. Do not broaden assignee eligibility.

### F3 — P2: ownership history falsely says no fields changed

`app.js:1828,2334–2343` omits `owner_user_id` from rendered generic field diffs.
After restoring the lookup, changing only the synthetic task's Owner from
Unassigned to Jordan saved successfully, but its newest History row said
**"No field changes."** The underlying before/after event remains available;
the defect is the readable presentation, not proven loss of the audit record.

Proof: `critical-ux-owner-audit.png`. Related: K62ZAP, 3FQEKB, DR3PKR.
Render old/new assignees using stable identity with readable names, including
duplicate names, removed accounts and unassignment.

### F4 — P2: Cancel is blocked by required-field validation

`src/astra/static/index.html:164–166` and `app.js:1819–1820` rely on form submission
for Cancel. Browser validation runs first. In New project with blank required
Name, Cancel left the dialog open and reported "Please fill out this field."
Capture behaved the same with blank Task title. Escape closed both dialogs.

Proof: `critical-ux-cancel-blocked.png`. Related: PZTYC9, CR121Z, 3C1Z74.
Cancel should be independent of validation; recheck focus restoration and
other dialog forms. Other blank forms were not exhaustively tested here.

### F5 — P2: permission-inappropriate Capture wastes users' work

Viewer Home exposes Capture and allows completing the add-task form for a
visible project. Submitting then displays "Task-management access denied."
The server correctly rejects it; this is a misleading UI affordance, not
an authorization bypass. Source: `app.js:736,1410`, create guard in
`service.py:1349–1390`.

Proof: `critical-ux-viewer-capture.png`. Related: PZTYC9, CR121Z, 3C1Z74.
Offer only permitted actions or explain the restriction before data entry.
Member/Chairman creation affordances were inspected in source but not each
submitted in this browser pass.

### F6 — P2: reviewer controls have no accessible names

The task panel's person and role selectors under Reviewers & approvers appear
as two unnamed comboboxes in Chrome's DOM snapshot. `app.js:2239–2240` provides
neither associated labels nor an accessible name. This contradicts 3C1Z74's
"every control has a name" criterion. A screen-reader session and full WCAG
audit remain unverified; do not infer them from static landmarks/focus rules.

### F7 — P2 usability gap: task templates require internal IDs

`app.js:1564–1565` asks for target project ID and optional parent task ID using
native prompts. Clicking Use on the synthetic task template opened a prompt;
the extension's dialog/focus operations then encountered timeouts. The prompt
was dismissed through the documented API. Exact prompt wording is verified
from source; no completed template application is claimed for this pass.
Related: 8B9NBH. A user with basic Excel knowledge needs named project/task
selection and a readable summary, not copied UUIDs.

### F8 — P2 usability gap: project search results cannot open the project

Searching "Campus" returned a working task button but the matching project
was a plain list item, with no link/button. `app.js:1669` confirms that rendering.
Proof: `critical-ux-search.png`. Related: Y3WC71, PZTYC9. Make a project result
an accessible link to its project page, preserving scoped search rules.

### F9 — P2 status reliability: failed global notification fetch looks like zero

`app.js:5` catches the notification request and substitutes an empty array and
unread 0. The fixture went from Inbox 6 unread to an unbadged Inbox when that
request failed. **Correction/limit:** opening Inbox itself showed "Synthetic
inbox lookup failure"; it did not present a proven empty-success page. Durable
rows were not lost. The problem is silent cache/badge reset without an unknown
or stale indicator. Related: Z24KVH, FKVHH8, VPYGY5, XX9RFM. Keep the last known
count marked stale or show a recoverable failure state; do not substitute zero.

## Standards debt and design judgments

- Duplicate "Alex Lee" options in assignment/Capture controls have distinct
  IDs but identical visible labels. Board lane separation by ID is already
  implemented; person selection still needs a safe disambiguator.
- CSS contains literal colours outside `:root`, e.g. `style.css:659,675,704,731`.
  This violates AGENTS.md's token rule. It is confirmed standards debt,
  not evidence by itself that those colours fail contrast.
- The baseline `docs/design/astra-product-ux-baseline.md:71,93,270` recommends
  private intake before filing. The delivered shell criterion PZTYC9 #5
  explicitly specifies quick creation via POST `/api/tasks`. Current Capture
  requires a project and creates project work. Treat this as **conflicting
  scope/documentation to reconcile with Aly**, not a discovered access bypass
  or authorization to implement a private inbox without approval.
- Final results, templates and owner configuration are spread across Portfolio
  More and Account → People. A task panel puts many administrative sections
  in a long scroll. Progressive sections and clearer administration navigation
  are recommendations, not confirmed data-integrity defects.
- Home's Today plus next-seven-days strip has eight buckets; at the observed
  desktop size its last bucket wrapped onto a second row. This is minor layout
  polish, not a wrong-count finding. Broader zoom/low-bandwidth/large-project
  UX should be measured after integrity repairs.

The assessment uses visibility of status, user control, error prevention,
recognition and recovery from [Nielsen's usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)
and the named [WCAG 2.2](https://www.w3.org/TR/WCAG22/) launch target. It is an
engineering judgment, not a certification or a real-user usability study.

## What worked in fresh verification

- Home gives defined overdue/blocked/critical/undated metrics and drill-through
  links. Owner-only decision sections were absent for Member and Viewer.
  Projects links opened a real Overview; its scheduled and agreed dates were
  separated, and incomplete-date forecasts were labelled provisional.
- Member My Work grouped five own open tasks into due groups with clear empty
  messages. Viewer Home surfaced the assigned subtask. Not every role/workflow
  combination or month-calendar state was freshly inspected.
- Phone-size Timeline defaulted to a real schedule table. Root scroll width
  equalled client width (375); the 862.53-pixel table stayed inside an overflow
  container. An accessible Move task action was reachable on later row 12.
- Using After on row 12 previewed Open classrooms → row 12, Oct 25–27 →
  Oct 29–31, project Oct 5–28 → Oct 5–31. Apply saved; reload retained the new
  finish. Agreed deadline stayed Nov 3 with the optional revision unchecked.
  The new task became blocked/on critical path in the subsequent portfolio.
  This proves one current linked-movement path, not every mouse/touch drag.
- Chairman Inbox displayed both task extension Oct 27 → Oct 31 and project
  scheduled finish Oct 28 → Oct 31, with readable old/new dates. Owner unread
  count also increased. Existing 2FREQ9 acceptance was not repeated.
- Full current service, HTTP, migration, importer, scheduling, assignment,
  security and Node driver suites passed. They support the implemented rules;
  they do not prove graceful partial failure, all physical interactions or
  production operation. Browser races expose holes in the current coverage.

## Limits and remaining launch gates

The review covers every listed record/criterion; it **does not independently
certify every clause or historical screenshot**. Fresh browser cases are
specified above. Native Excel uploads, pointer drags/Undo across every view,
secondary-owner sessions, CLI password/owner transfers, all role combinations,
real screen readers, physical phones, performance/scale, low bandwidth and
simultaneous real users are unverified in this pass. October 11–13 receipts
remain dated evidence in their stated scope, not new executions.

Chrome prompt/focus timeouts limited the last template/admin exploration.
Some screenshots returned the previous frame immediately after navigation or
resize; settled DOM/screenshot rechecks were used where available. Screenshots
are supplementary; saved rows, HTTP logs and observed DOM support the key
findings. Do not use an unsettled frame to infer a visual pass.

The existing launch plan still requires password self-service/first login,
backup/restore/version tooling, CI/release preparation, authorized staging,
HTTPS/Caddy configuration, security/load/recovery drills and Aly's launch
acceptance. Hosted attachments, workload, AI and other deferred scope remain
distinct. Source tests do not establish hosted readiness or global performance.

## Recommended sequence, for Aly's decision

1. Repair F1/F2 with meaningful regression tests for out-of-order responses,
   closing during load and failed/delayed assignee loading. Verify wrong-record
   and silent-unassignment reproductions fail safely in actual Chrome.
2. Repair F3/F4/F5/F6/F8/F9; replace template UUID prompts (F7) with named
   selections. Confirm role guards remain intact and every failed operation
   preserves entered data and reports a useful next action.
3. Resolve scope conflicts, improve duplicate-name selection, section/navigation
   density and token compliance. Do not reopen settled owner decisions by
   treating recommendations as approved behavior.
4. Complete the declared viewport/keyboard/contrast/screen-reader matrix and
   representative real Excel, phone, multi-user and network-failure workflows.
   Obtain independent review of each repair; only Aly accepts the tickets.
5. Resume the 25-gate pre-deployment plan and independent external-LLM review.
   Hosting/account/deployment steps still require Aly's authorization.

This review recommends repairs; 26ZF8D records the review handoff. It does not
move any existing ticket out of human/signoff/Done, certify the entire product,
or authorize deployment.
