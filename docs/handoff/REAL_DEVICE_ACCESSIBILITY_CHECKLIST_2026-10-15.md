# Astra real-device and accessibility acceptance checklist

**Purpose:** Aly's short, hands-on check of the current Astra interface before
launch. This is an acceptance aid, not a WCAG conformance audit.

**Time:** About 20 minutes if all listed devices are available. Skip an
unavailable device and mark it **Not run**; do not claim it passed. The iPhone
check is optional. Use an authorized test account and a non-sensitive demo
project with clearly marked test tasks. Do not move, edit or delete real project
work. If no safe demo project is available, mark the data-changing checks
**Blocked** and stop those steps.

## Before you begin — 1 minute

- Record the date, Astra URL (local or hosted), browser versions and test-account
  role. Do not write down passwords or copy private task details into this form.
- Confirm that the demo project and its tasks can be changed safely. Have two
  clearly named test tasks available for timeline movement.
- For movement checks, use the **task rows on the project timeline**. Do not drag
  task bars. A movement preview should appear before saving; cancel it unless
  you are deliberately checking a saved change in the demo project.

## Checks

| Time | Device and steps | Pass when | Result / evidence |
| --- | --- | --- | --- |
| 4 min | **Android phone, Chrome.** Sign in. Open **Home**, then a demo project's **Board** and a task card. Open that card's **Move to…** control, inspect the choices and cancel. Open **Add a task**, check that the required title and project controls are usable, then cancel without saving. | Text and controls fit the phone screen; the project and task can be opened; both dialogs are understandable and can be cancelled; no accidental task or move is saved. | Status: ____ Evidence/notes: ____ |
| 3 min | **iPhone, Safari (optional).** Repeat the Home, Board task-card **Move to…** and **Add a task** checks above. | Same result as Android, with no clipped action or dialog. If no iPhone is available, mark **Not run**. | Status: ____ Evidence/notes: ____ |
| 5 min | **Tablet, browser.** Open the demo project's timeline. Long-press and move a test task row above or below another test row. Above should make the moved task precede the target; below should make it follow. Inspect the preview's dependency and changed dates. Cancel the preview; if a saved move is needed to verify the result, save only in the demo project and record the before/after dates and dependency. | The intended row is selected (not its task bar), and the preview clearly identifies the affected tasks, relationship and date changes. Cancel leaves demo data unchanged; a deliberately saved demo move updates the expected rows. | Status: ____ Evidence/notes: ____ |
| 4 min | **Windows desktop, NVDA.** Start NVDA, sign in, open **Home**, navigate to the project **Board**, then open a task. Use the keyboard to reach the page title and main actions. | NVDA announces the new page title after navigation; task and action names make sense; keyboard focus remains visible and can reach the task actions. | Status: ____ Evidence/notes: ____ |
| 2 min | **Desktop browser at 200% zoom.** Open Home, the project timeline and a task dialog. | Main headings and controls remain readable; dialogs and primary actions stay reachable; no text or control overlap prevents the checks. Horizontal scrolling within a wide timeline is acceptable if its controls remain usable. | Status: ____ Evidence/notes: ____ |
| 1 min | **Record the result.** Mark every row Pass, Fail, Blocked or Not run. Add the exact screen, device and action for each failure. | Every check has a result. Missing devices and hosted checks are clearly left unverified. | Overall: ____ Date: ____ |

## Outcome

- **Pass:** all available checks passed in the safe demo project.
- **Fail:** a repeatable issue prevented a stated pass condition; record the
  device, page, action and what happened.
- **Blocked:** a safe demo project, account permission or required tool was not
  available. State what prevented the check.
- **Not run:** the device or tool was unavailable. This is not a pass.

This checklist does not verify hosted behavior when run against a local Astra
server. Repeat the applicable checks against the hosted site after deployment
has been separately authorized and completed.
