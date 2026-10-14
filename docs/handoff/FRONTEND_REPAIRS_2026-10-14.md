# Critical frontend repairs — 2026-10-14

The nine confirmed findings F1–F9 from the October 13 critical review are
repaired and locally verified. This is a bounded repair receipt, not whole-app
acceptance, a top-tier UX certification or permission to deploy. Aly alone
accepts the work. Ticket **WMW428** records these repairs.

## Scope and decision

- Starting commit: `9a509ed2ec0b48767f67e446803ce8b2afa58bfb`, branch
  `codex/migration-safety-remediation`; the initial pull was already up to date.
  Use the published package SHA supplied with this document to freeze review.
- Schema remains 20 and package remains 0.1.0. No service, database-schema or
  package changes. All browser writes were confined to disposable synthetic
  loopback fixtures; no real owner records, accounts or credentials changed.
- Aly authorized “Fix all the issues”, then chose the recommended direct
  project-task flow and the name **Add a task** on October 14. The task is
  immediately visible within the selected project's existing permissions.
  Private drafts are separate future scope; the conflicting design proposal
  is superseded in the design baseline and DECISIONS_LOG.

## Requirement-to-evidence record

| Finding | Repair | Fresh evidence and boundary |
| --- | --- | --- |
| F1: delayed detail response could save to the wrong task | Versioned detail loads; ignore stale/closed responses; form and async mutations retain immutable task IDs; refreshing a completed action preserves the current selection | Actual-JS regressions cover A/B, same-ID revisions, close, async confirmation and final-result completion. Chrome delayed A/immediate B saved B; read-only SQLite confirmed A unchanged at revision 1 and B updated at revision 2. |
| F2: failed owner lookup could silently unassign | Preserve stored selection; disable unfinished/failed pickers; show Retry; refuse assignment-only and bulk actions without a ready picker | Chrome title-only save after HTTP 500 retained Jordan as owner in SQLite. Actual-JS tests cover pending/failure, preserved selection and bulk refusal. |
| F3: owner-only history said No field changes | Render readable old/new owner names with stable IDs | Chrome Jordan-to-Taylor assignment displayed the ownership change in History; actual-function regression passes. |
| F4: required fields blocked Cancel | Every submit-based Cancel bypasses validation with formnovalidate | Browser blank New project, Add a task and project-close reason dialogs all cancelled. Source regression covers the controls. |
| F5: unavailable creation controls wasted work | Creation choices include authorized open projects only; hide entry where no eligible project exists | Fresh Viewer browser check hides Add a task; Owner can open it. Existing service/HTTP authorization remains unchanged and the full affected-role suites pass. |
| F6: reviewer selects lacked names | Explicit Reviewer person and Reviewer role accessible names | Regression checks the actual generated controls. Assistive-technology operation remains unverified. |
| F7: templates required internal IDs | Named project, parent-task and eligible-person form; retryable loading; optional date anchor; no UUID prompts | Chrome selected a named empty project and created Prepare site survey. Read-only SQLite confirmed the task and no invented owner/start/due values. |
| F8: project search could not open results | Project hits are route links and close Search when followed | Chrome searched Campus and opened the matching project Overview. |
| F9: notification failure looked like zero | Retain the last known snapshot; mark badge stale/unknown; explicit Inbox failure and Retry | Viewer Chrome showed ! and unavailable status after HTTP 500; restoring fixture responses and clicking Retry cleared the failure and displayed the true empty Inbox. Regression also checks retained known counts. |

Related review debt is addressed: duplicate person names include an email/ID
disambiguator; all CSS colours are root tokens; feedback colours use classes;
Home's eight daily buckets have eight desktop columns; administration and task
panels have section shortcuts. The template picker excludes inactive numeric-0
accounts. Independent review also caught and prompted repairs to detail focus,
bulk picker readiness, final-result refresh and stale feedback tones.

## Test and independent-review receipts

- Before repairs, the original 13 new regressions failed: **Ran 13,
  FAILED (failures=13)**. Four additional cases cover subsequent review findings;
  do not describe those four as part of the original red run.
- An intermediate web run was **Ran 187 in 175.629s, FAILED (failures=3,
  errors=2)**. A colour conversion had altered white-space property names;
  this was restored before final checks. DOM stubs needed real select readiness
  and option-clearing behavior, contrast checks needed root-token resolution,
  and a stale Member creation assertion contradicted existing service authority.
  These corrections retain the role and numerical contrast checks.
- Final focused web receipt: **Ran 221 in 156.706s, OK**. Final frontend
  integrity receipt: **Ran 17, OK**. JavaScript syntax check passes.
- Five guards were independently removed in disposable source copies: stale
  detail response, disabled owner picker, bulk readiness, immutable request
  target and selection-preserving final-result refresh. Each removal was
  detected by its regression; the reviewed source was preserved.
- Final full receipt on the published application/test content:
  `.venv\Scripts\python.exe tests\run.py` — **Ran 849 tests in 583.910s,
  OK (skipped=1)**, exit 0. Node UI drivers ran. The unavailable Windows
  filesystem-symlink case remains unverified.
- A separate read-only reviewer inspected the source/test diff and Aly's
  decision, requested the adjacent fixes above, then returned **PASS, no
  blocker** on the final delta. That reviewer independently ran the 17 focused
  tests and syntax check; the 221/full-suite and Chrome receipts are the
  implementing agent's checks, not independent reruns of the full suite.

## Browser evidence and limits

Actual Chrome checks used synthetic Owner and Viewer sessions. The principal
wrong-task and owner-preservation checks include persisted SQLite evidence,
not screenshots alone. A 390×844 viewport override produced a 375-pixel content
width with its scrollbar, without page-level horizontal overflow. The final
Add a task form has readable fields and visible Cancel/Add task actions. The
override was reset and the owned test tab closed afterward.

Local evidence is ignored and excluded from Git: full output in
`Temp/frontend-repair-final-full.log`, mutation runner
`Temp/check_frontend_mutations.py`, disposable fixture
`Temp/critical_ux_fixture.py`, and screenshots
`Temp/frontend-repair-correct-task.png`, `frontend-repair-owner-kept.png`,
`frontend-repair-owner-history.png` and
`frontend-repair-add-task-dialog-phone.png` (all under Temp). External reviewers
must build their own disposable reproductions; these local files are not a
published evidence bundle. Screenshots immediately after UI changes sometimes
showed an earlier frame; the final task-dialog image was inspected separately.

Physical phones, screen readers, exhaustive keyboard/touch operation, broad
large-project usability and hosted behavior remain unverified. The outstanding
release work in PRE_DEPLOYMENT_REVIEW_2026-10-13.md remains: password flows,
recovery/backup drills, release/CI checks, accessibility/device coverage and
authorized hosting proof. Passing these repairs does not clear every board
ticket or grant acceptance to earlier signoff work.

## Next action

Review the supplied published SHA with INDEPENDENT_LLM_REVIEW_PROMPT.md. Aly
may accept WMW428 after reviewing this bounded receipt. The agent may put it
in human, but may not move it out or accept it. Deployment, account and
credential decisions remain Aly's. Preserve the earlier review as a historical
record; its original defect statements refer to its frozen pre-repair source.

Final board snapshot: **88 tickets: 25 Done / 39 signoff / 10 human /
14 backlog**, with WMW428 in human. `jaira validate --json` checked 88,
errors=false, 44 warnings and existing AGENTS/CLAUDE generated-note drift.
Those warnings are disclosed, not silently resolved by changing other tickets
or regenerating repository rules. The independent final documentation review
passed; no extra browser actions or full-suite run are attributed to it.
