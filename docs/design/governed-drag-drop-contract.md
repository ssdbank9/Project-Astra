# Astra Governed Drag-and-Drop Contract

Status: approved design baseline; board, Gantt, locks, bulk and WIP limits built in lock #12\
Decision owner: Aly Jafferani, App Owner  
Decision source: Jaira tickets `JQY55P` and `AX572Q`  
Prototype: `design/astra-drag-drop-prototype.html`

## Purpose

Define one understandable interaction model for Kanban, Gantt, dependencies,
critical-path planning, files, cross-project movement and bulk operations. A
drop is never merely a visual rearrangement: Astra must authorize it, explain
its consequences, preserve schedule and evidence invariants, record the result,
and provide the appropriate recovery path.

This document is the production contract. The HTML prototype is throwaway,
in-memory demonstration code and must not be promoted directly into the live
application.

## Chosen product direction

Astra uses the **A-hybrid Command Center**:

- Command Center structure for operational density and simultaneous project,
  task and detail visibility.
- Focus Workspace typography and progressive disclosure for sustained reading.
- Executive Cockpit's compact portfolio-health strip for leadership scanning.
- Native HTML, CSS and JavaScript interactions with no framework dependency in
  the prototype. Production may reuse the interaction contract, not the
  prototype shell.

## Roles and fixed authority

| Capability | App Owner | Project Manager | Viewer |
| --- | --- | --- | --- |
| Configure Kanban columns, transitions, WIP limits and workflow templates | Yes | No | No |
| Move tasks through ordinary project stages | Yes | Yes | No |
| Accept, reject, complete, close, reopen or override requirements | Yes | Approval request only | No |
| Change ordinary internal dependencies | Yes | Yes, if no protected impact | No |
| Change critical path, protected milestone or project completion | Yes | Approval request only | No |
| Move, copy or link tasks across projects | Yes | No | No |
| Create controlled cross-project dependencies | Yes | No | No |
| Upload, version, organize, link, publish or remove files | Yes | No | No |
| View or download authorized files | Yes | Yes | Yes |
| Force-unlock work | Yes | No | No |

The App Owner is Aly Jafferani. Role checks are server-enforced; hiding a control
is usability, not authorization.

## One deep module at the mutation seam

All screens use one deep `DragCoordinator` module. Callers describe intent and
render returned results. They do not reproduce authorization, graph, storage,
locking, audit or notification rules.

```text
DragCoordinator.preview(actor, intent, expected_versions) -> Preview
DragCoordinator.commit(actor, preview_token, confirmations) -> Outcome
DragCoordinator.cancel(actor, preview_token) -> Cancelled
DragCoordinator.restore(actor, audit_event_id) -> Preview | Outcome
```

`Intent` contains the operation kind, source references, destination, requested
relationship or date delta, and client interaction mode. It never contains a
trusted permission or calculated critical-path flag.

`Preview` contains:

- allowed, blocked or approval-required status;
- exact reasons and remediation;
- locks required and existing lock holders;
- tasks, files, dates, dependencies and users affected;
- current versus proposed schedule and critical path;
- access, storage and final-result consequences;
- notifications and audit events that will be produced;
- a short-lived server token bound to actor, inputs and object versions.

`Outcome` contains committed changes, approval-request identifiers, audit-event
identifiers, notification disposition, and a recoverability descriptor. The
interface returns results; presentation adapters create dialogs, toasts and
announcements.

## Operation lifecycle

1. **Select** — choosing cards never locks them.
2. **Begin** — dragging or invoking a bulk command requests renewable leases.
3. **Preview** — valid targets illuminate; invalid targets explain why. Gantt
   shows ghost dates and downstream effects.
4. **Confirm or propose** — routine authorized work can commit immediately;
   high-impact or protected work shows an impact panel or creates an Owner
   approval request.
5. **Revalidate** — inside the write transaction, recheck actor, membership,
   workflow, object versions, dates, graph cycles, locks and storage limits.
6. **Commit atomically** — mutation and audit records succeed together. Bulk
   work is all-or-nothing.
7. **Notify** — the actor gets immediate feedback; consequential events alert
   the Owner; routine work enters the daily digest.
8. **Recover** — ordinary changes expose a 15-second Undo action and later
   audited restoration where permitted.
9. **Release** — drop, cancellation, rejection or lease expiry releases every
   acquired lock.

No client preview is authority. Every commit recalculates against current data.

## Kanban behavior

- The App Owner alone creates, reorders, renames, publishes, versions or
  migrates columns, transitions, WIP limits and completion requirements.
- Drag within a column changes priority.
- Drag between ordinary columns changes status when role, transition, WIP,
  dependency and evidence rules permit it.
- Managers may use Draft, Ready, In progress, Blocked and Submitted for review.
- Manager drops on protected review/accepted/completed/closed targets create an
  approval request; they do not change live status.
- Only the App Owner accepts/rejects review, completes/closes/reopens work or
  overrides dependency/evidence requirements.
- An invalid drop returns the card to its source and displays a specific reason.
- Filters, swimlanes, grouping and saved views never change the underlying task.
- `Move to...` provides the same operation without dragging.

## Gantt and schedule behavior

- Owners and Managers may move or resize ordinary authorized tasks.
- The client renders proposed dates as a ghost bar while the server preview is
  pending.
- Users choose whether downstream tasks move or remain fixed when an impact is
  present; the preview shows the result before confirmation.
- Changes affecting dependencies, protected milestones, the critical path,
  downstream commitments or project completion require an impact panel.
- Managers confirm impact moves themselves, and the Owners are notified (Aly's later
  Gantt decision on JQY55P, which supersedes the earlier "Owner approval request" rule).
  Astra records the confirmation as `schedule_impact_confirmed` with the move, and does
  so on every path that changes dates (Gantt, task panel, API). Downstream tasks stay
  fixed in this version; offering to move them is not built.
- A finish-to-start link is broken only when the successor starts before the day the
  predecessor is due. A successor starting on the predecessor's due day is allowed.
- Invalid dates, locked baselines, missing permission and graph cycles block the
  drop with an explanation.
- Critical tasks, milestones and connectors have an accessible visual treatment;
  near-critical tasks can show slack.

## Dependencies and critical path

- Connector dragging creates finish-to-start by default.
- The follow-up control supports finish-to-start, start-to-start,
  finish-to-finish and start-to-finish, plus permitted lag or overlap.
- Graph validation rejects self-links, duplicates where inappropriate, cycles,
  impossible schedules and unauthorized cross-project links.
- Adding, changing and reasoned removal recalculate schedule and critical path.
- Managers may change project-local dependencies only when protected milestones,
  critical path and project completion are unaffected. Otherwise they propose.
- Cross-project links are Owner-only and may use only published milestones,
  approved deliverables or explicitly designated interface tasks.
- If access later changes, a restricted placeholder preserves schedule integrity
  without revealing private task details.
- Cross-project links appear in the portfolio view; removal requires a reason.

## What-if scheduling

- What-if mode is private and unmistakably labelled as a simulation.
- Dates, durations and dependencies can be changed without mutating live data.
- Astra recalculates simulated completion, critical path and slack.
- A simulation can be discarded, saved as a proposed revision or submitted for
  approval.
- Applying it returns through `DragCoordinator.preview` and the normal lock,
  confirmation, transaction, audit and notification lifecycle.

## Cross-project task behavior

- Only the App Owner can move, copy or link a task across projects.
- A cross-project drop opens Move / Copy / Link with an impact preview.
- The preview covers owner, assignee, dates, dependencies, attachments, access,
  notifications and portfolio schedule.
- Invalid choices remain visible but disabled with a reason.
- Link preserves one authoritative task with project-specific visibility; Copy
  creates an independent task; Move transfers ownership after invariant checks.

## Files, folders and versions

- All file management is App Owner-only. Managers and Viewers may open or
  download files their project authorization permits.
- External references must be syntactically valid HTTPS URLs. Astra does not
  server-fetch them.
- Managed uploads stream to the installation's selected private storage adapter:
  OCI Object Storage or protected private-server filesystem.
- Default per-file maximum is 25MB; the App Owner may configure it up to the
  absolute 250MB ceiling.
- Every folder or multi-file batch has a fixed 250MB total ceiling.
- Folder hierarchy becomes Astra virtual folders; original local filesystem
  paths are never stored or exposed.
- Each file is validated independently for extension, MIME type and signature
  consistency against the dangerous-type denylist. No malware scanner is part
  of the approved design; this accepted risk belongs in administrator guidance.
- A queue shows progress and supports pause, cancel and retry. Valid files may
  continue while rejected items remain clearly isolated.
- Hash-identical content is reused rather than uploaded again.
- Same-name/different-content drops offer New version (default), Separate file
  or Cancel. Versions are immutable and retain uploader, date, size and
  verification metadata.
- New versions never silently replace final results. Final-result unmarking and
  protected removal remain explicit Owner actions.
- Cross-project file drops are Owner-only and offer Move / Copy / Link, with Link
  as default. One immutable object may have separately authorized references.
- Permanent direct links are Owner-generated per attachment, off by default,
  revocable and audited; their creation/revocation notifies the Owner.
- All blocked attachment-removal attempts notify the Owner.

## Bulk operations

- Checkbox, Shift-click and keyboard selection activate bulk actions.
- Selection alone acquires no locks.
- At operation start, all required locks are acquired together. One conflict
  prevents the operation from starting and identifies the affected holder.
- Invalid or unauthorized items must be removed before execution.
- Supported governed operations include status, assignee, project placement,
  common date offset, tags and eligible archive state.
- The commit is atomic and writes one parent audit event plus item details.
- Bulk Undo/restoration follows the same atomicity and impact-preview rules.

## Lock leases and concurrency

- Beginning an authorized drag or edit acquires a renewable activity lease.
- Other users see the holder, reason and expected expiry and cannot mutate the
  locked object.
- Drag locks release on drop or cancellation; edit locks renew only while active.
- Interrupted clients expire after a short grace period.
- The App Owner can force-unlock; Astra warns the holder when possible and audits
  the override.
- Lock possession does not bypass final transactional validation.

## Undo and restoration

- Ordinary committed operations show a 15-second Undo action describing the
  exact change.
- Later `Restore this state` creates a new audited mutation; history is never
  rewritten or deleted.
- Conflicting later changes produce a new impact preview rather than blind
  reversal.
- File deletion, permanent-link changes and final-result actions retain their
  stricter safeguards and are not made safe merely by an Undo toast.

## Notifications

- Every actor receives immediate success, rejection or approval-request feedback.
- The Owner receives real-time alerts for critical-path or completion changes,
  milestone moves, final-result effects, permanent-link changes, unauthorized or
  blocked consequential attempts, and large cross-project moves.
- Routine reordering, small date adjustments and ordinary uploads enter a daily
  digest while remaining immediately searchable in audit history.
- Project sensitivity settings may increase notifications but may not suppress
  mandatory Owner alerts.

## Accessibility, touch and low bandwidth

- Every drag has a keyboard/menu equivalent using the same coordinator intent.
- Focus remains visible and status changes are announced through a polite live
  region; errors use assertive announcements when needed.
- Desktop supports mouse/trackpad drag; tablet uses deliberate long-press with
  supported haptics; small phones use action sheets and date controls rather
  than precision timeline dragging.
- Normal scrolling cannot start a drag. Reduced-motion preferences remove
  nonessential movement.
- Previews exchange compact intent and consequence data, not full board reloads.
- Large file transfers are streamed with bounded concurrency and resumable queue
  state. The 250MB batch ceiling protects desktop/private-server hosting.

## Audit requirements

Audit events must identify actor, role, source, destination, intent, preview
token, before/after values, object versions, reason where required, approvals,
lock outcome, notification disposition and restoration ancestry.

Record successful consequential operations, approval proposals/decisions,
blocked unauthorized attempts, lock conflicts, Owner force-unlocks, dependency
removals, file version promotion/restoration, permanent-link actions and all
blocked attachment-removal attempts. Routine hover/cancel interactions are not
audit events unless they attempted a protected or unauthorized action.

## Prototype scenarios

The standalone prototype must demonstrate:

1. Manager moves an ordinary Kanban task and uses Undo.
2. Manager attempts a protected completion and creates an Owner request.
3. Owner changes a Gantt date and sees critical-path/downstream consequences.
4. Manager creates an ordinary dependency, then proposes a critical change.
5. Viewer attempts a mutation and receives a precise rejection.
6. Owner performs a controlled cross-project task action.
7. Manager attempts file upload and is blocked; Owner processes an allowed batch
   and an over-250MB batch rejection.
8. Bulk action cannot begin because one selected task is locked; after release,
   the selection commits atomically.
9. What-if changes remain private until submitted.
10. A committed action is restored without erasing its original audit event.

## Production boundary and gates

The prototype proves interaction comprehension only. It does **not** prove live
authorization, concurrency, persistence, storage, uploads, notifications,
critical-path correctness, browser compatibility or deployment safety.

Production requires separate, test-first work for schema migrations; generalized
dependency types; schedule/critical-path calculation; request-scoped database
connections; lock leases; server preview tokens; workflow configuration;
approval requests; storage adapters; resumable streaming uploads; notifications;
audit event extensions; keyboard/touch adapters; and HTTP authorization/CSRF
coverage. Graph validation, mutation and audit logging must share the same
`BEGIN IMMEDIATE` transaction where SQLite invariants require serialization.

Monday.com and Trello research is a follow-on input. Its patterns may refine
presentation and workflow defaults, but may not override the fixed authority,
security, evidence or audit decisions in this contract without an explicit
Owner decision.
