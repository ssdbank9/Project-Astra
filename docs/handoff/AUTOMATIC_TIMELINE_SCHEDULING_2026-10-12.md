# SXAWHN automatic linked timeline scheduling

Aly requested that moving tasks create dependencies and update the overall
project timeline. On 2026-10-12 Aly approved Above as predecessor, Below/After
as successor, Concurrent as parallel, affected-chain rescheduling with duration
preservation and one preview. Aly requested both project deadline choices.
On 2026-10-12 Aly explicitly stated "I accept SXAWHN" in this chat.
Implementation is accepted; the human-only board transition remains separate.
ZFP6ET stays accepted and done;
this is a new behavior change, not a reopening of that repair.

## User behavior

Use the task's Move task handle, or click it for the accessible action menu.
Every action opens one linked-schedule review with changed task dates, links to
add/remove, current/new project schedule and current/new agreed deadline.

| Action | Result after confirming |
| --- | --- |
| Above | Adds moved task → target, removes a direct reverse link if present, moves affected successors and updates sibling display order |
| Below / After | Adds target → moved task, removes a direct reverse link if present and moves its affected successors; Below also updates sibling display order |
| Concurrent | Removes the direct link in either direction, aligns the moved task's start with the target, and reschedules its successors |
| Date placement | Sets the moved task's dates and reschedules its existing successors; does not guess a new relationship from overlap |
| Cancel | Saves nothing |

Existing inclusive calendar-day durations and nonnegative finish-to-start gaps
are preserved for the affected chain. New links have no gap: the successor
starts the day after its prerequisite finishes. Joins wait for their latest
prerequisite. Moving earlier can bring successors earlier too. Independent tasks
retain their dates. Owners and existing approved task baselines stay unchanged.
The date dialog starts with the moved task's existing duration; explicitly
editing its finish changes that task's duration. Successor durations remain fixed.

Scheduled project bounds are calculated from current non-cancelled/non-abandoned
tasks and appear in Overview and the timeline. Alternative plans retain separate
forecasts. The all-plans display and deadline revision use the overall range;
the selected plan's timeline markers use that plan's forecast with Shared work.
Incomplete dates make the forecast provisional and prevent deadline revision.
Agreed start remains explicit. Agreed deadline remains unchanged by default;
the App Owner can tick Update agreed project deadline to the scheduled finish.
Revising it is recorded in project history; it does not replace task baselines.

## Authorization and consistency

The pure graph planner is in `src/astra/timeline_schedule.py`. The service
exposes read-only preview and atomic apply through the two HTTP endpoints
`/api/tasks/{id}/timeline-schedule-preview` and `/timeline-schedule`.
Apply recomputes a fingerprint binding the actor, source task, action, complete
project task snapshot, dependency graph, project metadata and saved row order.
It refuses stale previews rather than applying an unseen schedule.

Active App Owners (including secondary owners) may apply material chains and
revise deadlines. Project managers may preview material changes but cannot
apply them; ordinary single-task changes without protected impact remain
permitted. Members/viewers and a Chairman without project management cannot
use this scheduling path. Existing role and assignment policies remain.

Cross-project/invalid-plan links, indirect cycles, conflicting parallel chains,
foreign locks, fixed closed tasks and closed projects are refused. Required
dates must be complete before an affected chain can be scheduled. Dependencies,
dates, order, optional deadline, audit and in-app notices save in one transaction
or roll back together. Task owners receive in-app date-change notices; no
external message or notification delivery is enabled.

The earlier `/timeline-drop` API remains compatible for old callers. The
current Move task UI uses the new endpoints. Ordinary task-panel date edits
and legacy bar resizing retain their existing single-task behavior; automatic
propagation is implemented for the explicit task movement controls.

## Verification record

| Requirement | Evidence | Result |
| --- | --- | --- |
| Chain propagation, duration/gap retention, forks/joins and earlier movement | `TimelineScheduleTests` date-chain and fork/join cases | Pass |
| Owners/baselines and independent dates retained | Preview/read-only and owner/baseline assertions | Pass |
| Both deadline choices and alternatives | Default-retain, explicit-revise, independent-plan and Shared/latest-alternative tests | Pass |
| Snapshot identity/freshness | Cross-source, stale descendant/project/links/task-list and complete-order regressions | Pass |
| Atomic refusal and rollback | Cycle/parallel-chain, locked/closed, confirmation and audit-failure tests | Pass |
| HTTP roles and CSRF | Six-role preview/apply matrix, including secondary owner and material manager refusal | Pass |
| Independent review | Separate read-only reviewer; source-ID and fingerprint guard removals in memory made their regressions fail | Pass |
| Browser | Actual Below/Above/Concurrent/date gestures; After through accessible menu; both deadline choices, unchanged owner labels, critical-path changes, Overview dates, Cancel and reload | Pass in desktop Chrome |

Parent focused suite: Ran 17 tests in 7.611s, OK. Independent focused suite:
Ran 17 tests in 8.665s, OK. Full suite: Ran 787 tests in 561.770s,
OK (skipped=1). The skip is the existing attachment symlink test because
symlinks are unavailable. Node syntax check and diff hygiene passed.
Preview table/checkbox readability was refined during the full run and checked
in Chrome afterward; final static review is recorded separately before publication.

Chrome synthetic example: Below Build foundation under Open classrooms changed
Build to Oct15–17 and scheduled finish to Oct17 while agreed deadline remained
Oct16. Above then reversed that direct link, moved Open to Oct18–20 and Inspect
to Oct21–22. Explicit deadline revision changed the agreed deadline to Oct22.
Concurrent later brought Open and Inspect earlier, leaving the agreed deadline
unchanged; a date drop shifted the chain later again. All three task owners
remained Taylor Example. Cancel and reload preserved the final saved schedule.

Ignored screenshots `Temp/SXAWHN-linked-preview.png` and
`Temp/SXAWHN-project-schedule.png` show only synthetic data. Browser fixtures,
credentials and databases are excluded from Git. Touch/mobile gestures, the
owner's usual running server version and hosted operation remain unverified.
No owner records, accounts, deployment or external notifications changed.
Published normally on codex/migration-safety-remediation at
`d93139db7fa711daec3209a389490f507083552b`, confirmed against origin after push.
Acceptance does not authorize deployment or remove the unverified limits above.
