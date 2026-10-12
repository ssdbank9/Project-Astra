# Schedule-table movement — 827Q51

Small-screen schedule tables and desktop List views now expose **Move task**
for eligible tasks and steps. They open the same linked scheduling preview as
Gantt. This closes a launch QA gap found after Aly accepted SXAWHN.

## Scope and evidence

| Requirement | Evidence / result |
| --- | --- |
| Reproduce the missing control | The same synthetic owner had four Gantt controls, none at 390px and none in desktop List before repair. The table renderer and click registration omitted them. |
| One action per task or step | Actual renderer regression checks parent and child rows, labels and IDs. |
| Respect eligibility | Shared helper hides controls for non-managers, closed projects and completed/cancelled/abandoned tasks; click handler rechecks eligibility. Service authorization is unchanged. |
| Reuse linked preview | Both views register the same handler; actual event-dispatch regression reaches `reviewTaskDrop`. |
| Preserve filtered ordering | Table rows now carry their task IDs. The complete snapshot merges the displayed sibling sequence into its existing slots, preserving hidden siblings. |
| Test before repair | First two regressions failed before the table controls/handler. The third failed before table order capture: B,A,hidden,C instead of A,C,hidden,B. |
| Focused verification | Parent: Ran 4 tests in 0.230s, OK. Independent: Ran 4 in 0.251s, OK. Node syntax check passes. |
| Independent review | No blocking findings after correction. Removing the closed-project guard or table-order capture in memory makes the respective regression fail. |
| Browser verification | Actual desktop Chrome, synthetic loopback fixtures: 390px, 320px, desktop List and a 625x430 reduced viewport. See scenarios below. |
| Actual 200% browser zoom | **Unverified.** Automation shortcuts left viewport width and device pixel ratio unchanged. Reduced-viewport testing is not proof of browser zoom. |
| Final full suite | Ran 790 tests in 602.540s, OK (skipped=1), exit 0. Existing attachment-symlink rejection skip: symlinks are unavailable here. Earlier 789-test run is superseded. |
| Owner acceptance | Aly explicitly accepted 827Q51 in chat after the publication report, with the zoom limitation disclosed. Accepted implementation SHA: `2c514cdf31a7adf5b0fd14d106c12c29359718a5`. Acceptance is recorded through the Jaira CLI; the human lane remains unchanged under `AGENTS.md`. SXAWHN was also accepted by Aly in chat. |
| Hosted operation / physical devices | **Unverified.** No deployment or physical phone/touch acceptance occurred. |

## Browser scenarios

- At 390px, Open classrooms → After Inspect foundation opened the complete
  preview. Cancel left dates unchanged.
- At 320px, Enter on Move task opened the form; keyboard review/apply saved
  Open classrooms at 23–25 October. Reload retained the dates and Taylor
  Example's ownership. Scheduled finish became 25 October; the unchecked
  deadline option retained 22 October. Inspect foundation's critical-path
  indicator changed from Yes to No.
- Desktop List exposed four controls. Its movement form opened normally.
  At 625x430, a date placement showed the two linked date changes, project
  range and deadline checkbox; keyboard Cancel exited without saving.
- A fresh filtered-parent fixture showed Other,A,C,B with parent and one
  sibling hidden. Table Move above placed C before A, added C → A, changed
  A to 7–9 October, and reload retained Other,C,A,B. The Node regression
  additionally verifies the complete hidden sibling slot.
- All browser mutations used disposable data. No owner database, users,
  passwords or external notifications were changed. Temporary viewport
  overrides were reset.

Screenshots are local, ignored verification artifacts under `Temp/`:
`827Q51-reduced-preview.png`, `827Q51-filtered-saved.png` and
`827Q51-saved-list.png`. Final receipt: `Temp/verification-827Q51-final.txt`.

## Remaining gates and next work

827Q51's functional repair is accepted by Aly. The zoom criterion remains
explicitly outstanding; do not tick the combined definition of done or call
overall launch QA complete. Chat acceptance does not waive unperformed checks.
Actual 200% browser zoom and physical phone checks remain required for broader
accessibility/device acceptance. Aly need not repeat 827Q51 or SXAWHN acceptance.

Continue Phase A in `NEXT_STEPS.md`, using the current board rather than its
historical ticket counts. Keep App Owner signoffs, merges, accounts,
credentials and deployment with Aly. `AGENTS.md` wins over older handoff
instructions, including any historical suggestion to use `--force`.
