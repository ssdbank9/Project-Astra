# Astra handoff index

## Daily in-app summary — 2026-10-15

F9HBSJ now implements a primary-Owner-controlled daily Inbox summary with an
editable local delivery time and IANA time zone (default 09:00 Asia/Karachi).
The single-process scheduler sleeps until the next due time, deduplicates by
Owner-local date and catches up after restart; it does not poll every minute or
use a cloud job. A new primary Owner inherits the saved schedule. The summary
groups overdue, due-today and upcoming tasks, submitted reviews, open
checkpoints due soon or overdue, and next actions. The disposable Chrome check
verified saving the time zone and opening the linked Inbox summary. The full
suite passed **927 tests in 767.731s, OK (skipped=1)**; the independent read-only
diff review found no new issue. F9HBSJ is awaiting Aly's acceptance in the human
lane. This is local application evidence only; hosting and deployment remain
unverified.

## Current password-change gate — 2026-10-15

Read [A5 implementation and verification](FIRST_LOGIN_PASSWORD_CHANGE_2026-10-14.md).
App Owner-created and reset passwords require a change before protected app access;
signed-in users can change their own password. Schema 21 defaults existing
accounts to unchanged behavior. The 2026-10-15 full suite passed: **891 tests in
644.691s, OK (skipped=1)**. Isolated Chrome verified mismatch, too-short and
wrong-current-password refusals, required-field blocking, direct-route gating,
and successful forced and voluntary changes. Read-only checks confirmed one
secret-free password-change event per synthetic account, cleared forced-change
flags and retained active sessions. Independent implementation review passed
with no confirmed defect; the reviewer acknowledged the browser evidence but
did not repeat it. Aly accepted A5 on 2026-10-15; JRNDC8 is Done. No live account
or database was changed. Hosted readiness and deployment remain separate and
unverified.

Live Jaira snapshot on 2026-10-15: **92 tickets: 26 Done / 39 signoff / 13
human / 13 backlog / 1 in-progress**. Aly authorized TRPV3J for Codex; local
backup/restore CLI work is active. The CLI and operator guide do not prove
encryption-key setup, OCI upload, retention, desktop copy or hosted restore drills.
Backlog ticket 0RHNMG has the same title and core goal as accepted JRNDC8, but
its context and criteria differ. 0RHNMG is now in human review awaiting Aly's
duplicate-versus-separate decision; its provenance is unverified. The
real-device acceptance check is still pending; see [the A7 checklist](REAL_DEVICE_ACCESSIBILITY_CHECKLIST_2026-10-15.md).
2FREQ9 and WMW428 have Aly's acceptance recorded in chat but remain in the
human lane for Aly's board transition.

## Current independent-review guard repairs — 2026-10-14

Read [MJ5Q35's repair receipt](REVIEW_GUARD_REPAIRS_2026-10-14.md) first.
Closed-project template/dependency writes and stale write authority are
repaired; project reopening follows the dated App Owner-only rule. Aly
explicitly kept ordinary submitted edits allowed. Independent source review
and focused role/HTTP/guard checks pass. Final full suite: **881 tests in
830.547s, OK (skipped=1)**. Pin the published SHA supplied with this receipt.
MJ5Q35 awaits Aly's acceptance.
WMW428 remains accepted. Password/recovery/CI/hosted gates remain separate.
Current board: **89 tickets: 25 Done / 39 signoff / 11 human / 14 backlog**.
Validation: 89 checked, no errors, 44 warnings; generated AGENTS/CLAUDE note
drift remains disclosed. No existing protected lane was moved.

## Current frontend repair package — 2026-10-14

Read [the F1–F9 repair receipt](FRONTEND_REPAIRS_2026-10-14.md) first.
The nine confirmed October 13 defects and related picker/token/navigation
debt are repaired, with synthetic Chrome persistence checks, independent diff
review and a fresh **849 tests OK (skipped=1)**. Aly chose direct project-task
creation named **Add a task**. Aly accepted **WMW428** in chat on October 14
("Ticket accepted"). Its board lane remains human until Aly moves it; no prior
acceptance lane was closed by the agent. The board is not cleared.
Historical package board: **88 tickets: 25 Done / 39 signoff / 10 human / 14 backlog**.
Validation has no errors; 44 warnings and generated-note drift remain disclosed.

Pin the published package SHA supplied with the independent-review prompt.
The older app baseline and defect statements below are historical snapshots;
schema 21 includes A5 and package 0.1.0 is unchanged. Physical-device, assistive-technology,
whole-app usability and hosted launch gates remain separate and unverified.

## Critical built-work review — 2026-10-13

Read [the critical UI/UX review](CRITICAL_UI_UX_REVIEW_2026-10-13.md) and
[all-ticket criterion coverage](CRITICAL_REVIEW_COVERAGE_2026-10-13.md)
before declaring readiness. Two persisted synthetic browser failures can save
to the wrong task or silently remove its owner. Full832 tests pass despite
these defects. This review recommends repairs; it makes no product changes,
owner acceptance or deployment authorization. External reviewers must inspect
these findings as well as the plan below.

## Current pre-deployment review package — 2026-10-13

Start with [the detailed plan and handoff](PRE_DEPLOYMENT_REVIEW_2026-10-13.md),
[every-ticket audit](BOARD_AUDIT_2026-10-13.md), and
[the prompt for independent LLMs](INDEPENDENT_LLM_REVIEW_PROMPT.md).
These supersede historical status/count statements below. AGENTS.md remains
the authority for working rules; Aly alone accepts and authorizes deployment.

App-source baseline: `da1b3fd21ed0d4357669f0e727369fda02640672`, working branch
`codex/migration-safety-remediation`, schema 20, package 0.1.0. Source full receipt:
832 tests OK (one unavailable Windows symlink case). The fresh package receipt
is in the detailed plan and is reported with the final pushed SHA.

Existing board: **85 tickets, 25 done / 39 signoff / 7 human / 14 backlog**.
TV43F1 adds one coordination ticket; use the final 86-ticket audit for its lane.
The board is not cleared, and hosted readiness is unverified. First-login/self
password changes, backup/recovery, production checks and release work remain.

For Claude, Gemini, Codex or another reviewer: use the new independent prompt,
pin the supplied package SHA, read every handoff listed in the audit, and return
findings without edits. Other-LLM reviews have not been performed by writing a
prompt. The September AGENT_START_PROMPT remains historical startup context.

JM7CFP, W6ZSGA and 2FREQ9 have recorded chat acceptance; do not request repeat
acceptance. Native Excel/Chrome evidence from October 11 and later drag/zoom
receipts supersede older blanket 'browser unverified' wording only within their
documented scope. Owner-only board closure remains separate.

## Historical index notes — preserved for traceability

The notes below were accumulated from September 26 onward. Their test counts,
open-question statements and acceptance/board wording are dated snapshots,
not the current pre-deployment baseline. Follow the package above for current
planning, scope and review instructions.

Current local security review: [ZQQCJM B1 evidence](B1_SECURITY_2026-10-13.md). Request framing, response headers, workbook XML/archive budgets and write-time authority/assignee checks were repaired; Aly's closed-project and agreed-deadline decisions are applied. Hosted readiness is unverified. [Current free-hosting comparison](FREE_HOSTING_2026-10-13.md) recommends an eligible Oracle Always Free VM with DuckDNS and Caddy; no account or deployment action is authorized by that recommendation.

Current deadline-extension routing: [2FREQ9 verification](DEADLINE_NOTICES_2026-10-13.md). Active App Owners and Chairman receive in-app old/new-date notices for saved task deadlines, agreed targets and calculated project finish extensions. Existing approval rules remain in force. Aly accepted 2FREQ9 on 2026-10-13; hosted operation remains unverified.

Current server inactivity repair: [AY5EZ0 verification](HTTP_TIMEOUT_2026-10-13.md). Stalled connections now have a finite socket timeout; timed-out body reads return 408 and close their request database. Broader security review, owner acceptance and hosted operation remain separate.

Current phone-size and List scheduling repair: [827Q51 verification](TABLE_SCHEDULING_2026-10-12.md). Table rows now expose Move task and preserve filtered sibling ordering. Actual 200% Chrome zoom and save/reload checks passed on 2026-10-13; Aly accepted the repair. Physical-device and hosted checks remain separate.

Current automatic task movement and project scheduling: [SXAWHN implementation
and verification](AUTOMATIC_TIMELINE_SCHEDULING_2026-10-12.md). Above/Below now
create sequential relationships through the Move task UI; linked dates and
project forecasts update together. Explicit deadline revision is optional.
Owner acceptance and hosted operation remain separate.

This folder hands Project Astra to whoever works on it next: an AI coding
agent in any tool, or a human developer. The pack calls that reader "the
agent". It was written at branch `codex/migration-safety-remediation`, head
`0b90ceb` (schema v20, 676 tests OK, nothing deployed); the commits made since
are listed in `HANDOFF_2026-09-26.md` section 1.

Current owner Excel and task-row timeline work: [JM7CFP verification](OWNER_EXCEL_WORKPLAN.md).
Aly selected XLSX with four main columns and explicit named relationships.
Implementation and isolated sample checks are recorded there. Aly accepted
JM7CFP on October 9; later bounded native/browser evidence is in
[desktop verification](DESKTOP_VERIFICATION_2026-10-11.md) and the dated drag
repairs. This is not a launch-readiness claim.

Latest Windows baseline evidence: [A0 repair, 2026-10-04](A0_2026-10-04.md),
ticket SFAZD7. The default Windows command ran 684 tests, `OK (skipped=1)`;
the symlink skip and remaining launch gates are recorded there. A0 awaits
Aly's acceptance; this result does not establish hosted readiness.

Latest importer repair evidence: [2026-10-04 repairs](IMPORTER_REPAIRS_2026-10-04.md),
ticket WYM776. The default Windows suite ran 692 tests, `OK (skipped=1)`.
Parent 3NT40T remains in human for the sample-dependent CSV decision. The
mixed-save evidence is below; owner acceptance and hosted readiness remain separate.

Latest mixed-save evidence: [2026-10-04 repair](MIXED_SAVE_REPAIR_2026-10-04.md),
ticket 1G7Q4C. The default Windows suite ran 700 tests, `OK (skipped=1)`.
Manager combined edits and protected status requests are refused without partial
writes, and the actual browser retains the entered fields. Aly's acceptance and
the remaining development and hosting gates are still required.

Latest Q1 permission evidence: [2026-10-05 approver permissions](Q1_APPROVER_PERMISSIONS_2026-10-05.md),
ticket 2RPSWM. Designated approvers may request App Owner acceptance of submitted
work only; Manager authority and App Owner final decisions remain intact. The
default Windows suite ran 714 tests, `OK (skipped=1)`. Aly's signoff and hosted
readiness remain required.

Latest owner workplan feature: [one-project CSV, 2026-10-07](WORKPLAN_CSV_2026-10-07.md),
ticket W6ZSGA. Project download/fill/upload supports Shared and alternative plans,
logged task keys and independent critical paths. The final Windows suite ran
739 tests, `OK (skipped=1)`; independent review and synthetic desktop/phone
browser checks passed. Aly accepted W6ZSGA in this chat on 2026-10-07.
The human-only board transition, real sample population and hosting remain
separate.

Local data location on Aly's machine, 2026-10-07: `Documents/AstraTest` was
relocated to this checkout's `data/` directory at Aly's request. Use the root
`Start-Astra.ps1` launcher; see [local instructions](../../LOCAL_ASTRA.md).
The directory is ignored by Git. SQLite integrity, foreign keys and every table's
records matched a consistent backup after relocation. At relocation this database
contained one user and no projects or tasks; the earlier browser-session database remains
unverified. No server startup or schema migration was performed during the move.

Latest entity feature: [entity rename, 2026-10-07](ENTITY_RENAME_2026-10-07.md),
ticket 16JJ96. Aly selected a separate `Rupani group of Colleges` entity and the
existing school project was filed under it in the authenticated local browser.
Owners can rename entities with stable IDs/project links and Settings history.
The entity setup supersedes the empty-database relocation snapshot above.

## What is in the pack

| File | What it is for |
| --- | --- |
| `README.md` | This index, the reading order, and how to use the pack with a specific tool |
| `HANDOFF_2026-09-26.md` | The master handoff: status, setup on Windows and Linux, tests, working rules, architecture, feature history, permissions, board, gaps, risks, where the docs live |
| `NEXT_STEPS.md` | The plan from now to distribution: A close out development, B hardening, C release engineering, D deployment, E distribution, F operate |
| `DEPLOYMENT_RUNBOOK.md` | Command-level steps for the Oracle Cloud Always Free + DuckDNS + Caddy pilot, with Aly's steps marked, a check after every stage, update and rollback |
| `DECISIONS_LOG.md` | Every decision Aly has made that we found, with date and source, plus Claude's default calls that Aly has not overruled |
| `OPEN_QUESTIONS.md` | What Aly still has to decide, each with a recommended default |
| `AGENT_START_PROMPT.md` | The first message Aly pastes to the next agent |

The working rules themselves live in `AGENTS.md` in the repository root. That
file is the single source; `CLAUDE.md` repeats the same rules.

## Reading order for the agent

1. `AGENTS.md` in the repository root: the rules.
2. `AGENT_START_PROMPT.md`: the rules in short and the first task.
3. `HANDOFF_2026-09-26.md`: sections 1 (status), 4 (rules) and 6 (permissions)
   first, then the rest.
4. `NEXT_STEPS.md`, phase A in full; skim the later phases.
5. `OPEN_QUESTIONS.md` and `DECISIONS_LOG.md`, before you propose any change of
   behaviour.
6. `pending-global-mistakes.md` and `README.md` in the repository root.
7. `DEPLOYMENT_RUNBOOK.md` when the work reaches phase D.

## Using this with a specific tool

Nothing in the pack depends on one tool. Only the file a tool reads by itself
differs:

- **Codex** reads `AGENTS.md` automatically.
- **Claude Code** reads `CLAUDE.md` automatically. Its top part repeats the
  rules in `AGENTS.md`.
- **Any other tool** (Gemini, Cursor, another assistant) **or a human
  developer:** paste `AGENT_START_PROMPT.md` as the first message, or read it
  yourself, and follow `AGENTS.md`.

Wherever a step needs a decision, an account, a password or an acceptance, the
pack says "ask Aly".

## For Aly

- To test locally, follow section 2.1 of `HANDOFF_2026-09-26.md`.
- Your part of phase A is in `NEXT_STEPS.md` A1 (signoffs), A2 (questions),
  A7 (phone and screen-reader check) and A8 (the `tmp*` folders).
- The five questions that block the most work are at the top of
  `OPEN_QUESTIONS.md`.

## How this pack was checked

- Every SHA cited was checked with `git cat-file -t` in the repository, except
  three that the shallow container clone does not hold: `051db35` and
  `331f988` are remote branch heads confirmed with `git ls-remote`, and
  `c5ac1c0` is the first parent of `main`'s head `c841526`
  (`git cat-file -p c841526`).
- Every repository path cited exists at `0b90ceb`, apart from the files this
  pack proposes to create (`CHANGELOG.md`, `.github/workflows/tests.yml`) and
  the pack itself.
- Every `astra` command matches `src/astra/__main__.py`; every environment
  variable matches the code (`ASTRA_HOME`, `ASTRA_SECURE_COOKIES`,
  `ASTRA_ATTACHMENT_ROOTS`).
- Operating-system, Caddy, DuckDNS, OCI and encryption commands in the runbook
  were not run for this handoff; they are marked "verify".
- Facts taken from memory notes that could not be re-checked against the
  repository or Slack are marked "memory" or "unverified".
- An independent fact-check of the pack was applied before it was committed
  (`146a5b3`).
