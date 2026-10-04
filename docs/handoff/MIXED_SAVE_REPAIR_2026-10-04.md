# Mixed Manager save repair — 2026-10-04

Aly selected R1: refuse a combined ordinary edit and protected status request
atomically, retaining the form values. Aly authorized fixes followed by
development and then said go. Work remains on `codex/migration-safety-remediation`.
Starting SHA: `dd5284c0004319bb6fea53f325224f6265980cd2`.
Ticket: **1G7Q4C**, in signoff. Aly alone accepts work.

## Requirements and evidence

| Requirement | Evidence |
| --- | --- |
| Refuse mixed Manager saves without partial writes | The service compares all six ordinary persisted fields before either protected-request route. Fifty-four field/transition cases and both protected-status routing paths over HTTP leave the entire SQLite dump unchanged, including tasks, revisions, events, requests and notifications. The HTTP response is 400 with: Save task edits separately from a status request. Nothing was saved or requested. |
| Accept unchanged full-form values | Tests cover whitespace-normalized title/description, unchanged assignment/dates, blank dates, and progress None, 0 and 45 echoed as form strings. Pure status requests still succeed. |
| Preserve other role and lifecycle behavior | Ordinary Manager edits and direct App Owner mixed saves still persist. Viewer and Chairman attempts remain forbidden through service and HTTP. Existing submitted, governed-target, terminal-reopen, stale-revision and reason-check precedence tests pass. |
| Retain the entered form | A synthetic Manager's actual browser save displayed the refusal and retained title, description, selected owner/status, both dates, progress and reason. The task list still showed the original deliverable. Existing submitDetailEdit handles HTTP 400 without rebuilding the form; no UI source change was needed. |
| Refuse unsupported progress safely | Independent review found that lists, objects and infinity raised TypeError/OverflowError at the new normalization boundary. Two new regressions reproduced the defect. The boundary now translates these to ValueError; service and HTTP refusal snapshots remain unchanged. |

## Verification

- Original red run: **Ran 25 tests in 19.380s, FAILED (failures=56)**.
  Fifty-four service cases and two HTTP 202-versus-400 cases exposed the defect.
- Focused repair run: **Ran 25 tests in 16.799s, OK**.
- Progress-boundary red run: **Ran 2 tests in 1.435s,
  FAILED (failures=4, errors=6)**. Corrected run: **Ran 2 tests in 1.421s, OK**.
- Removing either guard in a disposable copy fails the service regression:
  locked-source route 36 failures; protected-target route 18 failures.
- Independent code review and correction rereview: **PASS**.
- Browser retention verification: **PASS**, with a local screenshot kept outside
  the repository. No live data or original account was used.
- Default Windows command: `.venv\Scripts\python.exe tests\run.py`.
  **Ran 700 tests in 368.566s, OK (skipped=1)**, without PYTHONUTF8 override.
  The source/test hashes stayed unchanged, no ResourceWarnings occurred and no
  new tmp directories remained. The existing symlink skip is still **unverified**.
  The seven staged files match the exact scope, their blobs and diff contain no
  CR characters, and working/staged diff checks pass. Hashes match the full run.
  Normal publication follows these checks; no owner acceptance is implied.

## Remaining owner gates

The importer repair was pushed as `dd5284c0004319bb6fea53f325224f6265980cd2`;
its suite ran 692 tests, OK (skipped=1). A0/SFAZD7 and WYM776 remain in signoff
for Aly. Parent 3NT40T remains in human for the sample-dependent CSV decision R2.
The recommendation remains XLSX for people with basic Excel skills; the sample
workplan has not been received and no new CSV format is approved.

This repair does not establish hosted readiness. The skipped Windows symlink
check, Linux execution, real-device acceptance, hosting and the real-user pilot
remain **unverified**. Original account credentials are also **unverified**;
only temporary synthetic preview credentials were supplied. No password reset,
deployment, account provisioning, real-user creation, merge or release occurred.
