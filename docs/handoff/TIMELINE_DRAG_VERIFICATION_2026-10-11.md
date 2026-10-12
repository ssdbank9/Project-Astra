# Timeline task dragging verification - 2026-10-11

Historical findings below are superseded by the verified
[ZFP6ET repair](TIMELINE_DRAG_REPAIR_2026-10-12.md), accepted by Aly on 2026-10-12.

Aly requested verification after compaction and confirmed that VZ1ENJ was
already done. The board independently reports VZ1ENJ done. This check used
Chrome's connected browser tab and ordinary mouse input through its CDP
capability against disposable, synthetic loopback data. No owner data changed.
The working branch was pulled with `git pull --ff-only` before this check.

## Results

| Check | Observed result | Status |
| --- | --- | --- |
| Drag the Move task handle onto a date | Prepare site previewed October 12-14, preserving its three-day duration; saving updated the timeline | Pass |
| Drop below another task | Build foundation dropped below Open classrooms; review said dates and links would remain; saved order survived reload and the dependency remained | Partial: unrelated rows also moved on this first reorder |
| Drop above another task | Prepare site dropped above Inspect foundation; correct review opened; Cancel preserved the existing order | Preview and cancellation pass; this above move was not saved |
| Drop After this task | Prepare site dropped after Open classrooms, previewing October 15-17; impact confirmation appeared; saved predecessor and critical-path labels appeared | Pass |
| Drop Run concurrently | Prepare site dropped onto Open classrooms' concurrent target; preview explained link removal; saved October 12-14 and removed the direct link | Pass |
| Critical-path recalculation | After saving the sequential move, Build foundation, Open classrooms and Prepare site showed critical-path labels; concurrency removed Prepare site's label while preserving the foundation/classrooms chain | Pass for this synthetic graph |
| Persistence | Reload retained the resulting dates, concurrency and stored order | Pass |
| Starting a drag from a later row | Two attempts from Open classrooms emitted dragstart then immediate dragend, without a review; starting from the first row succeeded | Reproduced failure; cause remains unverified |
| Phone/touch/screen reader | No real device or screen reader used | Unverified |

## Confirmed ordering defect

Immediately before the first reorder the displayed order was Build foundation,
Open classrooms, Prepare site, Inspect foundation. Moving Build foundation
below Open classrooms should leave the other rows in place. Instead the saved
order became Prepare site, Inspect foundation, Open classrooms, Build foundation.
Dates and the existing foundation/classrooms dependency were preserved.

`AstraService.timeline_drop` starts the first persisted order from
`ORDER BY created_at,id` when no order event exists. The visible timeline uses
the task list's existing order before any explicit ranks exist. These different
starting orders explain the observed movement of unrelated rows. Correcting
this requires a regression covering first reorder from the actual visible order,
including filtered/grouped views and existing revision/order conflict guards.

## Drag reliability finding

Adding `task-row-dragging` exposes drop controls and expands every task row.
The measured first timeline target moved from y=394.125 to y=457.21875 during
one drag, a shift of about 63 pixels. Later-row starts failed twice as described
above. The layout shift is confirmed; its causal role in those cancellations
has not been isolated from Chrome/tool timing. Do not describe it as repaired.

The initial high-level tool gesture produced no drop. Chrome mouse input with
a second movement inside the live target produced real dragover and drop events
and opened the dialog. This supersedes the earlier blanket pointer-unverified
entry in DESKTOP_VERIFICATION_2026-10-11.md, within the bounds listed here.
Temporary event tracing was removed by reloading the page.

## Evidence and limits

Ignored screenshots: `Temp/verified-drag-critical-path-20261011.png` and
`Temp/verified-drag-concurrent-20261011.png`. They contain only synthetic data.
Browser fixtures and screenshots are not for public Git.

No application source changed and no push or deployment was performed in this
verification task. The preceding source change's full-suite receipt remains
`Ran 766 tests in 875.619s`, `OK (skipped=1)`; that result predates these browser
checks and does not prove absence of the newly observed ordering defect.
Task dragging is partially verified and should not be called fully ready until
the first-order defect and later-row failure are resolved and checked again.
