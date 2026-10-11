# Astra desktop verification - 2026-10-11

Aly requested detailed verification using the available desktop tools and
continuation toward launch. Work used the canonical checkout and
`codex/migration-safety-remediation`, starting at
`2d22eae0cde5cc6811a634129bbc451466f3a6a4`; required pull was already up to date.
Existing owner data, unrelated dirty files and real browser tabs were preserved.

## Requirement and evidence record

| Requirement | Direct evidence | Result |
| --- | --- | --- |
| Verify through actual desktop apps | Native Chrome and installed Microsoft Excel, isolated loopback servers with synthetic users/tasks | Verified for the bounded checks below |
| Four main workbook fields | Excel displayed Task, Responsible person, Start, Finish; optional columns grouped/hidden | Verified |
| Eligible person dropdown | Native Excel Alt+Down listed the existing synthetic owner; selecting it populated the cell | Verified |
| Excel compatibility | Downloaded workbook opened without a repair prompt, saved in Excel, then uploaded in Chrome | Verified |
| Project/entity mapping | Workbook and browser showed the matching synthetic project and Example Colleges entity; full suite includes wrong-binding checks | Browser display and automated refusal checks |
| Upload preview and commit | Excel-saved file: three updates, zero errors; owner saved on Prepare site | Verified |
| Preserve existing dependencies | Build foundation remained blocked by Prepare site and on the critical path after the Excel upload | Verified |
| Explicit relationships | Move task / After another task finishes showed review dialog, saved dependency and recalculated critical path | Verified through native browser controls |
| New task and dependency | Second synthetic project import created Open classrooms with owner/dates and predecessor Build foundation; Created 1, Updated 3, Dependencies 1, zero skipped errors | Verified |
| Repeat upload | Native Chrome preview of the identical file: Create 0, Update 0, Unchanged 4, Warnings 0, Errors 0 | Verified preview; no duplicate or edit proposed |
| Correct owner change labels | VZ1ENJ preview displayed Unassigned to Synthetic browser owner, replacing raw UUID | Verified in native Chrome |
| Independent review | owner_preview_review read only scoped importer/test diff, passed focused regression, restored old behavior in memory and observed failure | Pass, no blocking findings |
| Preserve stored user IDs and blank-field behavior | Regression covers assignment, reassignment, persisted user IDs and blank owner preservation | Passed |
| Pointer drag | Native task-handle drag produced no review dialog; no date change observed | Unverified; tool gesture versus app behavior not established |
| Phone, touch and screen reader | No real-device session or screen reader run | Unverified |
| Accounts, real sample import and deployment | No real account creation, import into owner data or deployment | Separate owner gates preserved |

## Defect and correction

Chrome exposed a raw owner UUID in the change preview even though the assignment
saved correctly. `ImportEngine._display` now resolves the existing display name
only for preview text. Import plans and database writes retain IDs. Authorization,
eligible-user resolution and blank owner preservation are unchanged. The initial
test incorrectly expected a blank owner cell to clear an assignment; this was
corrected to preserve the existing product rule.

The original UUID behavior failed the new regression. Focused final run:
`Ran 21 tests in 23.312s`, `OK`. Independent reviewer run: `Ran 1 test`, `OK`;
restoring old display behavior in memory caused failure without modifying files.

## Test and publication receipt

Before the preview fix, the fresh Windows suite completed
`Ran 765 tests in 898.063s`, `OK (skipped=1)`.
Corrected Windows full suite completed `Ran 766 tests in 875.619s`,
`OK (skipped=1)`, exit 0. Publication is pending at document preparation;
the final SHA is reported in the chat receipt after a scoped commit and normal push.
The skip is the existing Windows attachment-symlink environment limitation.

Local ignored evidence: `Temp/verification-20261011-full.txt`,
`Temp/verification-20261011-focused-final.txt`,
`Temp/verification-20261011-fixed-final-full.txt`,
`Temp/verified-excel-dropdown-20261011.jpg`,
`Temp/verified-dependency-20261011.jpg`, and
`Temp/verified-owner-preview-fixed-20261011.jpg`, and
`Temp/verified-replay-20261011.jpg`.
Synthetic workbooks, session bootstrap and screenshots stay out of public Git.

## What follows toward launch

The dated evidence here supersedes older blanket claims that all desktop Excel
and browser work remains unverified. It does not supersede the owner approval
rules. Aly accepted JM7CFP on 2026-10-09; its human-only board transition stays
with Aly. VZ1ENJ is a separate follow-up defect ticket.

1. Finish pointer drop/reorder, concurrent moves, keyboard and real phone checks.
2. Complete phase A5: forced change of temporary passwords and self-service
   password change. Current source search found neither feature; historical
   ticket 7E1K4B covers literal search/CSV safety, not passwords.
3. Reconcile old plan/open-question statements against current code and accepted
   decisions; do not implement an old gap merely because a handoff lists it.
4. Security review, SQLite backup/restore drills, migration/performance checks
   and release packaging remain phase B/C gates.
5. Hosting, credentials, real accounts, invitations and deployment require Aly's
   separate involvement. Hosted readiness is unverified.

## Tool limitations

Remote Desktop Commander listed two online devices with the same name; no remote
mutation was made against an ambiguous device. Local native app tools supplied
the observed Excel/Chrome evidence. The Computer Use skill prohibits automating
ChatGPT's desktop UI; that restriction does not prevent native Excel/Chrome work.
Occasional captures combined the wrong foreground image with stale accessibility
text; rehydrating, activating and recapturing the exact window recovered the
target. Native file chooser coordinate/accessibility targeting failed; keyboard
filename entry succeeded. These are tool limits, not confirmed Astra defects.
