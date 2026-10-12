# ZFP6ET timeline task-drag repair

Aly authorized fixing the first-reorder mismatch and investigating later-row
dragging before calling the feature ready. This repair supersedes the open
implementation findings in TIMELINE_DRAG_VERIFICATION_2026-10-11.md.
Only disposable synthetic data was used. App Owner acceptance remains pending.

## Behavior and cause

The first Above/Below operation previously initialized project order from task
creation order. It now starts from the complete timeline hierarchy, merges the
drawn sibling sequences into their corresponding slots, and moves only siblings
of the selected task. Other groups keep their slots. Hidden siblings remain in
the complete order; they can change rank when a sibling moves across them.
Exact-ID validation rejects missing, duplicate or unknown snapshot IDs without
writing an event. Existing saved order, event/revision conflicts, project role,
same-parent, closed-project and task-lock guards remain.

Drop controls previously expanded the task-name rows during dragstart. Chrome
reproduced dragstart followed immediately by dragend for a later row. A targeted
CSS probe hiding the controls restored dragstart; an absolute overlay probe also
restored it. The final controls sit below each timeline as absolute overlays.
Before/after handle and timeline rectangles were identical during the final
Chrome gesture. Temporary browser probes were removed by reload.

## Requirement and evidence record

| Requirement | Evidence | Result |
| --- | --- | --- |
| First reorder preserves unrelated rows | New service regression failed before repair; actual Chrome Open classrooms above Build foundation preserved Prepare site and Inspect foundation | Pass |
| Subsequent reorder and reload persist | Chrome Below returned the original displayed sequence; reload retained saved order | Pass |
| Filtered/grouped complete order | Service grouped/filtered regression; actual-function Node test for hidden parent, hidden sibling slots, collapsed rows and foreign projects; actual filtered-parent Chrome drop and reload | Pass |
| Later-row dragging has stable targets | Third-row handle and every timeline rectangle unchanged during dragstart; actual drop opened review dialog | Pass in Chrome |
| Dates and dependencies | Later-row date placement saved duration; Concurrent removed direct predecessor; After recreated link and critical-path labels | Pass in Chrome |
| Cancellation | Cancelled later-row Above preview, then reloaded; order, dates and link unchanged | Pass in Chrome |
| Authorization/conflict protection | Focused service and HTTP role matrix, revision/order and lock cases; independent removal of ID guard made regression fail | Pass |
| Independent review | Separate read-only reviewer identified filtered-parent omission, then passed corrected scoped implementation | Pass |
| Final full suite | Ran 770 tests in 508.309s, OK (skipped=1), exit 0 | Pass |

The filtered-parent Node regression was red before the DOM merge. The three
initial ordering/snapshot service regressions ran as three tests with four
failures before the backend fix. Parent focused suite: Ran 24 tests in 11.178s,
OK. Independent focused suite: Ran 24 tests in 11.401s, OK. Node syntax check
passed. An earlier intermediate full run passed 769 tests in 871.152s,
OK (skipped=1); it predates the additional Node regression and is not the final
receipt. Final full suite after the additional regression: Ran 770 tests in
508.309s, OK (skipped=1), exit 0. The existing attachment symlink rejection test
was skipped because symlinks are unavailable here; Node UI tests ran.

## Limits and follow-up

Chrome temporarily became unavailable after compaction. Documented inventory
recovery found a reconnected Chrome instance and restored control. With the
parent and one sibling hidden by the Criticality filter, Chrome displayed
Filtered other, A, C, B. An actual later-row drop of C above A saved
Filtered other, C, A, B; reload retained that sequence and original dates.
Touch dragging and narrow-screen overlay behavior are unverified.

Ignored screenshots `Temp/ZFP6ET-stable-drag-targets.png` and
`Temp/ZFP6ET-filtered-order.png` show synthetic tasks, stable drop controls and
the saved filtered sequence. Disposable loopback fixtures, credentials,
databases and browser artifacts are excluded from Git. No production restart,
deployment, real import or account operation was performed. The owner's usual
server may need a normal restart to load the Python repair; its running version
is unverified here.

Publication: the scoped repair is to be committed with ZFP6ET and pushed
normally on codex/migration-safety-remediation after the origin check; final SHA
is reported to Aly after the push. ZFP6ET must remain pending Aly's
acceptance; do not infer acceptance from tests or the earlier JM7CFP sign-off.
