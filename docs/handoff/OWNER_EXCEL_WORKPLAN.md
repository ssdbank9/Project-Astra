# Owner Excel workplan and task-row timeline controls

Aly selected XLSX on 2026-10-08 after rejecting the dense owner CSV. Ticket
JM7CFP implements this decision on codex/migration-safety-remediation.
Aly accepted this feature in chat on 2026-10-09: "Approved JM7CFP".
Browser and desktop Excel behavior remain unverified.

## Owner workflow

Select an existing project and download its Excel workplan. The Tasks sheet
shows Task, Responsible person, Start and Finish. Responsible person uses
existing eligible users; the file never creates accounts. Dates use yyyy-mm-dd.
Optional columns are grouped: Timing relationship, Related task, Part of,
Plan and Type. Task IDs and project/entity binding are hidden and maintained
by Astra. A new download reserves new spare keys. Upload to the same project,
review the preview and confirm. Repeated keyed uploads update the same tasks.
Imports never delete tasks or replace accepted baselines.

Relationships are explicit named selections. After another task finishes adds
a finish-to-start dependency and requires consistent dates. Can run concurrently
requires a distinct, compatible named task with no dependency path connecting
the tasks. There is no Decide in Astra option. Dates alone never imply a link.
Part of groups steps; Plan separates alternatives and Shared work.

## Timeline behavior

Move task is the draggable task-row control. A date drop previews scheduling
with the existing duration, or asks for a finish date for an undated task.
Above/Below reorders siblings without changing dates or dependencies.
After this task explicitly adds a dependency. Run concurrently removes the
direct predecessor link to the target, if present, and refuses any remaining
dependency chain. Relationship/date changes apply atomically. Keyboard/touch
use the same review dialog and service actions.

Existing project-management authority, closed-project checks, task leases,
revision checks, protected date rules and impact confirmation remain enforced
on the server. Critical path recalculates from saved dependencies and dates.
Only Aly accepts this feature.

## Verification and private sample

- Nineteen focused service/workbook/HTTP tests pass as of this note.
- Ten disposable guard removals caused regressions to fail.
- The final reviewed-code full run passed 764 tests in 388.663s,
  OK (skipped=1). The existing Windows symlink limitation remains skipped.
- Independent review found and prompted those corrections; final verdict pending.
- Browser discovery recovered after resetting the CUA kernel. Its inventory
  exposes Chrome, but opening the requested Codex browser returns
  `Browser is not available: iab`. Aly was asked to open the right-hand browser
  in this chat. Actual dragging, dialogs, Excel desktop behavior and owner
  acceptance remain unverified.
- The private Rupani sample is in ignored data/workplans. It preserves 239
  source tasks, hierarchy and Private/Charter separation with four visible
  columns. Isolated import creates 239 and repeat upload leaves 239 unchanged.
  Live project tasks remain untouched. Source month targets are not accepted
  exact dates; owners, dates, dependency links and 15 summary milestones still
  need review. Private bindings and source workbook must never enter public Git.

Independent static review and final automated tests passed. Aly accepted
JM7CFP on 2026-10-09. Keep browser and desktop Excel checks explicitly
unverified; the acceptance is an owner decision, not evidence those checks ran.
The agent records acceptance and places the board ticket in signoff; leaving
that human lane remains Aly's step. Hosting and a live-data release remain
separate owner-authorized launch steps.

Continuation evidence: [2026-10-09 verification](JM7CFP_VERIFICATION_2026-10-09.md).
Independent review found a whitespace mismatch between generated relationship
labels and parser lookup keys. The repair normalizes reference matching and its
new regression verifies both saved grouping and dependency IDs. Twenty focused
tests passed and independent static review passed. See the continuation record
for the outstanding browser/desktop checks and recorded owner acceptance. The corrected-code full suite ran
765 tests in 557.349s, OK (skipped=1); the attachment-symlink environment
limitation remains the single skip.
