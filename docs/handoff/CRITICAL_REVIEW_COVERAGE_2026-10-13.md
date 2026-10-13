# Built-work review criterion coverage — 2026-10-13

Companion to [the critical review](CRITICAL_UI_UX_REVIEW_2026-10-13.md).

38 unaccepted built tickets / 139 numbered criteria; five contextual records / 12 criteria.
All 151 are enumerated below. Composite ticket criteria are preserved verbatim,
rather than marking a whole ticket complete because one subclause passed.

**Partial** means located source plus fresh suite and/or stated browser evidence support
part of the composite criterion; remaining visual, historical guard-removal, delivery,
independent review and acceptance clauses are unverified unless explicitly established.
**Contradicted** identifies a current observed failure of a clause, not failure of every
other clause. **Unverified** means only a historical/design claim or an unrerun operational
action supports it. No status here is owner acceptance.

Fresh suite: Ran832 in568.186s, OK(skipped=1); source baseline da1b3fd.
Named tests below are exact matches between names in declared ticket proof and
the fresh run log. A name match is not independent proof of every clause, and
no match does not mean the suite lacks tests. It means that criterion is not
mapped to a fresh named case by this mechanical cross-check.

Source locations below were independently inspected for the implementation family.
Historical proofs and screenshots were not all recreated. See the main report
for source-versus-browser evidence, superseding decisions and actual limitations.

## Built pending acceptance

### QY0WG2 — Criticality: approved sorting and confirmation workflow

[Ticket source](../../.jaira/tickets/01M2HPGB3Z4FE25004KHQY0WG2-criticality-approved-sorting-and-confirmation-wo.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py:4090; app.js:1992; test_core/test_web criticality tests`.

**Current review:** Confirmation/sort implementation inspected; current form visually present. Full mutation-removal/browser matrix not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Confirmed criticality sorts descending Critical>High>Normal>Low then by nearest due date; Unrated tasks stay conspicuous (not hidden or sorted away); changing criticality records actor, old value, new value, and reason as an audit event; unit + HTTP tests cover the sort order and the confirmation record; existing tests stay green. | Partial; see current review and main report limits | `test_confirm_criticality_event_records_actor_old_and_new_value`, `test_confirm_criticality_records_true_old_value_under_interleaving`, `test_confirm_criticality_refuses_null_reason_and_non_string_values`, `test_confirm_criticality_requires_project_manager`, `test_confirm_criticality_with_stale_expected_revision_is_a_conflict`, `test_criticality_sort_orders_normal_above_low`, `test_list_tasks_sorts_by_confirmed_criticality_then_due_date` |

### 9R7A87 — Parent/subtask hierarchy and roll-up

[Ticket source](../../.jaira/tickets/01M2HPGPQVKM6W59NTM99R7A87-parent-subtask-hierarchy-and-roll-up.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py:4024,4049; app.js buildSubtasks; test_core hierarchy tests`.

**Current review:** Subtask table and separate declared roll-up observed. Drawer exposed to F1.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Can create/view a task's subtasks in the UI; a hierarchy/roll-up view shows parent with its children; parent shows declared roll-up (accepted/total subtasks) separately from any manual progress, never invented; same-project enforced (already partial); subtask cycles prevented; unit + HTTP tests cover roll-up counts and cycle prevention; existing tests stay green. | Partial; see current review and main report limits | `test_parent_must_be_same_project`, `test_subtask_rollup_and_cycle_prevention` |

### Z24KVH — Durable in-app notification inbox for the owner

[Ticket source](../../.jaira/tickets/01M2HPH35W0MHCMKGRQ9Z24KVH-durable-in-app-notification-inbox-for-the-owner.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py:5344; app.js openInbox/renderInbox; test_web inbox tests`.

**Current review:** Fresh readable notices; F9 loses global badge on fetch failure. No proven durable-row loss.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Every saved authorized task change writes a durable notification row for the owner; an in-app inbox lists them newest-first with read/unread; marking read does not delete the record; opening/dismissing is not approval; retries idempotent (no duplicate rows per event); in-app only, no outbound email; unit + HTTP tests cover creation, read-state, and idempotency; existing tests stay green. | Partial; see current review and main report limits | `test_notification_recipient_isolation`, `test_owner_notified_of_other_users_changes_idempotently` |

### JZACMP — Schedule-revision model: baseline / current / pending

[Ticket source](../../.jaira/tickets/01M2HQJAZQMYMNSDMH2YJZACMP-schedule-revision-model-baseline-current-pending.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py:5035,5061; app.js buildSchedule; test_web proposal tests`.

**Current review:** Baseline/current/pending observed separately; related drawer actions exposed to F1.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Baseline captured at first schedule set and never silently overwritten; current plan and pending proposals stored separately; every schedule change records old/new, actor, time, reason, and approval; dependents never silently rescheduled (impacts shown first); unit + HTTP tests; existing tests green. | Partial; see current review and main report limits | `test_baseline_captured_on_first_schedule_and_immutable` |

### Y3WC71 — Exports and search

[Ticket source](../../.jaira/tickets/01M2HQJB5YP4VP6SMNSFY3WC71-exports-and-search.md) · lane signoff · declared DoD 4/4.

**Located evidence:** `service.py:1963,1995; app.js:1664; test_web search/export tests`.

**Current review:** Scoped suite passed; browser project search result is non-navigable (F8). Export download/re-upload not fresh browser-tested.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Export returns only the authorized current view with active filters and an as-of timestamp; search covers tasks/projects the actor may see and never leaks beyond scope; both enforced at the service boundary; unit + HTTP tests including a scope-isolation case; existing tests green. | Partial; see current review and main report limits | `test_export_echoes_as_of_and_filters_and_is_scoped`, `test_export_is_scope_limited_for_a_member`, `test_search_is_scope_limited` |
| 2 | Removing export authorization fails a test: a member's export (service, HTTP JSON and CSV) excludes another project's task and a hidden project_id is 403; anonymous search/export are 403. | Partial; see current review and main report limits | `test_export_is_scope_limited_for_a_member` |
| 3 | Both export CSV writers (tasks, final results) neutralise cells starting with = + - @ tab or CR with a leading single quote, the same rule as importer.csv_cell. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 4 | A downloaded CSV states its active filters without an in-band row: header stays first; the filename carries as-of and each active filter. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### XDA2JR — Project calendar: workweeks and holidays

[Ticket source](../../.jaira/tickets/01M2HQJBAWE4A76A0S6DXDA2JR-project-calendar-workweeks-and-holidays.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py:990,1012; app.js renderPeople; test_core/test_web calendars`.

**Current review:** Fresh synthetic fixture used calendar configuration; actual calendar admin form interaction not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Per-project workweek and holiday list are configurable; due/duration logic uses them on top of the existing governing timezone; working days never inferred from an email domain; unit tests cover a holiday and a non-working day; existing tests green. | Partial; see current review and main report limits | `test_calendar_management_is_owner_only`, `test_working_calendar_default_restrictions_and_holidays` |

### AYW0QC — Calendar Gantt + critical path

[Ticket source](../../.jaira/tickets/01M2HV23PQE4NJB06K8CAYW0QC-calendar-gantt-critical-path.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py list_tasks; app.js:157; test_core CPM tests`.

**Current review:** Fresh portfolio and linked move show recalculated critical path; all CPM cases supported by suite, all pointer cases not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | list_tasks returns is_critical_path per task, computed per project by full CPM (forward and backward pass over finish-to-start dependencies; every zero-slack task is critical, so several parallel critical paths can be marked; on one project this equals the union of all longest chains by duration); cancelled/abandoned tasks are excluded, and a task with no dependency in either direction is never flagged, even when it is longer than the chain; the Gantt renders a weekly calendar axis, a Today marker, and critical-path bars styled distinctly with a legend entry; each row shows its own owner; unit tests cover a linear chain, a branch where the longer chain wins, multiple parallel critical paths, one-day slack not flagged, a join following its longest predecessor, per-project scoping, a cancelled mid-node, and an isolated task longer than a chain in the same project not flagged; node --check clean; existing tests green. | Partial; see current review and main report limits | `test_critical_path_linear_chain` |

### 8B9NBH — Project & task templates

[Ticket source](../../.jaira/tickets/01M2JFER9P4JB4MD8QMH8B9NBH-project-task-templates.md) · lane signoff · declared DoD 3/3.

**Located evidence:** `service.py:4391,4406,4661; app.js:1527; test_core/test_web templates`.

**Current review:** Fresh fixture saved project/task templates. UI task application asks raw UUIDs (F7); completed browser apply unverified.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Save a project (or a task subtree) as a template; create a new project/task from a template copying structure only (never evidence or history); owner-only; unit + HTTP tests; existing tests green. | Partial; see current review and main report limits | `test_every_template_action_is_owner_only_for_every_non_owner_role`, `test_project_created_from_template_reapplies_offsets_and_resets_state`, `test_project_template_captures_structure_not_history`, `test_task_subtree_template_roundtrip`, `test_templates_are_owner_only` |
| 2 | Templates carry a role-based suggested owner (not a person); applying a template resolves each role to a person (picked, or the unique role holder), legacy name-based templates still load; tests cover it | Partial; see current review and main report limits | `test_legacy_name_based_templates_still_instantiate`, `test_project_from_template_resolves_each_role_to_the_picked_person`, `test_project_from_template_without_picks_leaves_project_roles_unassigned`, `test_role_assignments_are_validated_before_anything_is_written`, `test_task_template_resolves_role_to_the_unique_holder_in_the_target_project`, `test_template_stores_a_suggested_role_not_a_person` |
| 3 | A test fails if require_owner is removed from save_task_as_template or save_project_as_template | Partial; see current review and main report limits | `test_every_template_action_is_owner_only_for_every_non_owner_role` |

### 6G89SJ — Attachments on tasks

[Ticket source](../../.jaira/tickets/01M2JNPRGYD7TGGSHZV16G89SJ-attachments-on-tasks.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py:4195; app.js buildAttachments; test_core/test_web links`.

**Current review:** Synthetic linked file displayed with path/copy/final-result controls. Hosted uploads remain separate/deferred.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | The App Owner links a file inside an ASTRA_ATTACHMENT_ROOTS folder to a task (path, display name, note, added-by, time; no bytes stored); unsafe paths (UNC, device, URL, relative, '..', outside the roots) are refused before any filesystem check; authorized users see the link in task detail; add/remove are App Owner-only and audited; a link marked as a final result cannot be removed until it is explicitly unmarked (409, audited); unit + HTTP tests incl. authorization and CSRF denials; existing tests green. Upload, size cap, sha256 and download moved to MXY7BG. | Partial; see current review and main report limits | `test_add_attachment_rejects_unsafe_paths_and_writes_nothing`, `test_attachment_authorization`, `test_attachment_form_is_absent_for_a_viewer_and_unchecked_links_are_not_called_missing`, `test_attachment_marked_as_final_result_cannot_be_removed`, `test_attachment_path_validation_rejects_every_unsafe_shape`, `test_owner_import_skips_attachment_paths_that_fail_validation`, `test_stored_path_that_fails_validation_is_never_looked_up`, `test_task_attachment_link_lifecycle_and_audit`, `test_template_apply_skips_attachment_links_that_fail_validation` |

### CS93C6 — Final results repository (deliverables database)

[Ticket source](../../.jaira/tickets/01M2JNPRP3CD4T9WSS3ZCS93C6-final-results-repository-deliverables-database.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py:4687; app.js openFinalResults; test_core/test_web final results`.

**Current review:** Fixture explicitly marked accepted result; browser repository filter/export execution not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Accepted submissions and task attachments can be marked a 'final result' by hand and collect into a repository searchable and filterable by entity/project/type/date (API and UI); owner/authorized scope only; a list export (CSV) that honours the same filters; acceptance alone records nothing (owner decision 2026-09-15: every final result is an explicit manual mark); unit + HTTP tests for each filter and the export; existing tests green. | Partial; see current review and main report limits | `test_accepting_a_submission_does_not_auto_record_a_final_result`, `test_final_result_mutations_are_owner_only_for_every_non_owner_role`, `test_final_results_are_scoped_to_project_members`, `test_final_results_filter_by_marked_date_range`, `test_final_results_filter_by_project_and_entity`, `test_final_results_filter_by_type`, `test_final_results_search_matches_title_task_and_project` |

### 5WZ4A8 — Project schedule dates with change history

[Ticket source](../../.jaira/tickets/01M2JXM4NWFWH5J0BYJ35WZ4A8-project-schedule-dates-with-change-history.md) · lane signoff · declared DoD 3/3.

**Located evidence:** `service.py:1061; app.js renderFilingEntities; test_core/test_web project dates`.

**Current review:** Scheduled/agreed dates visibly separate; old Manager deadline acceptance superseded by Owner-only B1 decision.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Projects have an editable start_date and target/end date; changing either requires a reason and writes a project_events audit row capturing actor + old + new + reason; the change is visible in the project's history; task date-change logging is confirmed already working and cited (no regression); unit + HTTP tests cover the project date change + its audit row; existing tests green. | Partial; see current review and main report limits | `test_project_history_readable_by_members_not_outsiders`, `test_project_schedule_audit_row_records_actor_before_after_and_reason`, `test_project_schedule_change_is_logged`, `test_project_schedule_change_requires_manage_access`, `test_project_schedule_requires_reason`, `test_project_target_cannot_precede_start`, `test_task_date_change_is_logged_with_before_and_after` |
| 2 | Rework (review gaps 1-3): tests fail if the can_manage_project check is removed from set_project_schedule (service Forbidden + HTTP 403 for viewer and non-member, manager succeeds) and pin the audit row: actor_user_id, reason, parsed before/after for both changes, at service and HTTP level. | Partial; see current review and main report limits | `test_project_schedule_audit_row_records_actor_before_after_and_reason`, `test_project_schedule_change_requires_manage_access` |
| 3 | Rework (review gap 4): GET /api/projects/{id}/events serves the project's history to anyone who can view the project (403 for non-members), and the UI shows it (Project history dialog from the toolbar when one project is selected), with before-and-after screenshots. | Partial; see current review and main report limits | `test_project_history_readable_by_members_not_outsiders` |

### HS3JRY — Reconcile latest Owner-only authorization

[Ticket source](../../.jaira/tickets/01M2YBDV8NBKQ34273XKHS3JRY-reconcile-latest-owner-only-authorization.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py authorization helpers; app.js renderDetail/buildLifecycle; test_approver_permissions/test_web`.

**Current review:** Fresh Viewer create rejected by service. F1/F2 corrupt permitted UI writes without bypassing role guards.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Chairman behavior matches the current role matrix; Managers can perform only approved ordinary internal actions; protected lifecycle attempts create Owner requests and do not mutate accepted state; add/remove/open/publish/version/permanent-link/final-result file mutations are Owner-only except authorized read/download; blocked attachment-removal attempts notify the Owner; service/API/UI/automation/offline paths cannot bypass the rules; authorization matrix tests cover Owner, Chairman, Manager and Viewer; all existing tests remain green. | Partial; see current review and main report limits | `test_attachment_authorization`, `test_chairman_has_organization_visibility_without_implicit_mutation_power`, `test_every_mutation_route_delegates_to_the_service_layer`, `test_final_result_mutations_are_owner_only_for_every_non_owner_role`, `test_manager_can_edit_ordinary_work_but_protected_status_becomes_request`, `test_manager_protected_acceptance_creates_owner_request_without_mutation`, `test_manager_protected_lifecycle_attempts_queue_requests_without_mutation`, `test_manager_schedule_decision_is_an_owner_request`, `test_manager_schedule_rejection_is_an_owner_request`, `test_read_only_chairman_attachment_removal_is_blocked_and_notifies_owner`, `test_read_only_chairman_protected_attempts_are_blocked_audited_and_notified`, `test_templates_access_and_calendar_administration_are_owner_only_for_every_non_owner_role`, `test_viewer_protected_attempts_are_blocked_audited_and_notified` |

### D73AQW — Gantt: visible colour-coded task steps with hover and click detail

[Ticket source](../../.jaira/tickets/01M32AMMEW7SGBE4NRKTD73AQW-gantt-visible-colour-coded-task-steps-with-hover.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `app.js:157,308,331; service.py list_subtasks; test_web Gantt driver`.

**Current review:** Parent/step table, numbered segment and undated parent observed. Keyboard tooltip, overflow disclosure and every viewport not freshly exercised.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Dated subtasks render as numbered, coloured segments inside the parent task bar on the Gantt (one Okabe-Ito hue per step index, index label always visible, title when the segment is wide enough); hover and keyboard focus show a tooltip with step name, owner, start/due dates, duration, status and due state, dismissible with Escape; clicking or pressing Enter/Space on a step opens that step's detail dialog, which shows a Parent back-link to the parent task; a chevron expands/collapses the child rows under the parent and the choice is remembered per parent in the browser; undated steps are shown as an 'n steps need dates' chip and never given invented dates; colour is never the sole carrier: every segment carries its index and a legend lists index + colour; a Schedule table toggle shows the same data as a real table (Project, Task, Step #, Step, Owner, Start, Due, Status, Due state, Critical path) and is the default at phone width; prefers-reduced-motion disables the transitions; steps narrower than 8px fold into a +N overflow disclosure; service.list_subtasks returns start_date, criticality, progress, parent_task_id and owner_user_id with unit and HTTP tests for the shape; node --check on app.js and the full test suite pass; browser evidence captured for Owner and Viewer at 1440 and 390 widths. | Partial; see current review and main report limits | `test_list_subtasks_returns_step_schedule_shape` |

### C9KPH6 — Import tasks and Gantt from Excel/CSV

[Ticket source](../../.jaira/tickets/01M33VD86SS216CCQEDVC9KPH6-import-tasks-and-gantt-from-excel-csv.md) · lane signoff · declared DoD 13/13.

**Located evidence:** `importer.py/xlsx_reader.py; app.js:2720; test_import/test_xlsx_reader/test_web`.

**Current review:** Current project-bound XLSX supersedes original generic-seven-sheet workplan. Suite fresh; native Excel/browser upload evidence dated, not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Template download: GET /api/import/template.xlsx (Tasks sheet locked except data rows, dropdowns, date validation, frozen header, version marker, README sheet) and /api/import/template.csv | Partial; see current review and main report limits | `test_project_template_authorization_and_simple_preset`, `test_project_template_is_prefilled_assigns_keys_and_round_trips_unchanged` |
| 2 | Parser: stdlib-only xlsx reader (shared strings, inline strings, missing dimension, absolute rel targets, 1900/1904 dates, serial <= 60 rejected) plus CSV path (utf-8 BOM, utf-8, cp1252) | Partial; see current review and main report limits | `test_csv_path_accepts_aliases_with_a_warning_and_bom` |
| 3 | Preview: per-row OK/warning/error with messages and resolved values; header row must match the template exactly (CSV aliases allowed with a warning); no database write | Partial; see current review and main report limits | `test_child_of_a_parent_that_fails_in_dependency_wiring_is_an_error_too`, `test_data_in_an_unheaded_extra_column_is_reported`, `test_preview_reports_rows_and_writes_nothing`, `test_title_change_on_reimport_warns_and_readme_says_to_add_rows_at_the_bottom` |
| 4 | Commit: one BEGIN IMMEDIATE transaction; upsert by Import Key; never deletes; never overwrites a baseline; finish-to-start dependencies by key with cycle check; task_event per created/updated task; project import_committed event; imports row | Partial; see current review and main report limits | `test_dependency_cycle_through_an_existing_task_absent_from_the_file_is_refused`, `test_duplicate_key_race_during_commit_is_a_conflict_and_rolls_back`, `test_existing_task_reparented_under_a_row_that_is_new_in_the_same_file`, `test_owner_reimport_does_not_set_changes_requested_without_a_submission`, `test_parent_cycle_through_an_existing_task_absent_from_the_file_is_refused`, `test_same_import_key_is_allowed_in_two_projects` |
| 5 | Report: GET /api/imports/<id>/report.csv downloadable | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 6 | Authorization: Owner imports anywhere and may create a project; Manager imports only into managed projects with protected actions skipped by warning; Viewer/Chairman/non-manager get 403 and an Owner notification; all tested | Partial; see current review and main report limits | `test_manager_imports_into_own_project_with_protected_actions_downgraded`, `test_manager_into_unmanaged_project_viewer_and_chairman_are_blocked_and_owner_notified`, `test_owner_creates_project_from_the_project_sheet`, `test_project_template_authorization_and_simple_preset` |
| 7 | UI: Import button for eligible users; three-step dialog Upload/Review/Confirm; no inline style attributes; keyboard accessible; Escape closes; focus returns | Partial; see current review and main report limits | `test_preview_returns_project_sheet_values_verbatim_and_the_dialog_escapes_them` |
| 8 | Tests: full suite green with the new parser, importer and HTTP tests, node --check app.js, git diff --check | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 9 | Browser evidence: screenshots of Upload, Review, Confirm, dashboard and Gantt after import plus a phone Review shot, recorded with a Manager uploading | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 10 | Docs: README bullet, CONTEXT.md, docs/design/excel-import.md including how the Owner adds users before a Manager imports | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 11 | Template configuration: Owner-only PUT /api/import/template-config (Managers may GET); enable/rename/reorder built-ins, core columns locked, custom text/number/date/list columns; template and upload validation follow the configuration; stale template rejected; custom values in tasks.import_extras shown read-only in task detail; tested | Partial; see current review and main report limits | `test_template_config_round_trip_custom_column_and_stale_template`, `test_template_config_validation_and_authorization` |
| 12 | Dates inside the import feature display as dd-mm-yyyy (template format, README, Review table, report) and the parser accepts dd-mm-yyyy text as well as ISO and Excel dates | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 13 | Workbook v2 parity: generated template has the 7 sheets (Lists hidden, _astra veryHidden), Tasks header equals config labels, _astra!B1 equals the config hash; Type=Milestone maps to is_milestone; Project sheet is the project header; People sheet cross-checked in preview; EXAMPLE-/EX- keys refused | Partial; see current review and main report limits | `test_commit_creates_tasks_events_dependencies_and_import_record`, `test_owner_creates_project_from_the_project_sheet`, `test_simple_preset_is_the_default_and_full_is_one_call_away`, `test_template_download_round_trips_through_the_parser_and_example_keys_are_refused`, `test_template_workbook_is_locked_validated_and_marked` |

### ZSZ9T2 — Limit Project history event kinds for non-managers

[Ticket source](../../.jaira/tickets/01M39BH4WDNX4GQGFCWWZSZ9T2-limit-project-history-event-kinds-for-non-manage.md) · lane signoff · declared DoD 6/6.

**Located evidence:** `service.py:4940; app.js project Activity; test_core/test_web history filters`.

**Current review:** Later K62ZAP Chairman/full-history rule supersedes older filter wording. Browser activity-role matrix not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Service test: a viewer and a member without manage rights get only project_schedule_changed and project_closed from project_events | Partial; see current review and main report limits | `test_project_history_non_managers_see_only_schedule_changes_and_closure` |
| 2 | Service test: the App Owner and a project manager still see every event kind; a non-member still gets Forbidden | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 3 | HTTP test: GET /api/projects/{id}/events returns the filtered list to a viewer, the full list to owner and manager, and 403 to a non-member | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 4 | Tests failed before the fix for the right reason; output saved to scratchpad/ZSZ9T2-failing-before.txt | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 5 | Filter is server-side in AstraService.project_events and reuses can_manage_project; the Project history dialog still renders for viewer and manager (Playwright screenshots) | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 6 | Full suite, node --check app.js, compileall and git diff --check pass | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### K62ZAP — Full history for Owner and Chairman; hide approval details from other non-managers' task history

[Ticket source](../../.jaira/tickets/01M39FBVFN3445ZJETM8K62ZAP-full-history-for-owner-and-chairman-hide-approva.md) · lane signoff · declared DoD 7/7.

**Located evidence:** `service.py:2109,4940; app.js renderEvent; test_core/test_web`.

**Current review:** Filtering implementation inspected and suite passed; owner-only History misrendered (F3), without proven audit loss.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Service test: Owner, Chairman and a project manager get every kind from task_events and project_events | Partial; see current review and main report limits | `test_task_and_project_history_full_for_owner_chairman_manager_filtered_for_others` |
| 2 | Service test: a member, a viewer and a non-manager designated approver get only the ordinary task kinds plus their own rows from task_events, and only project_schedule_changed/project_closed plus their own rows from project_events; a non-member gets Forbidden | Partial; see current review and main report limits | `test_task_and_project_history_full_for_owner_chairman_manager_filtered_for_others` |
| 3 | HTTP test: GET /api/tasks/{id}/events and GET /api/projects/{id}/events return full lists to Owner, Chairman and manager, filtered lists (no hidden payload text) to member/viewer/approver, 403 to a non-member | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 4 | ZSZ9T2 Chairman subtests updated to expect full project history | Partial; see current review and main report limits | `test_project_history_non_managers_see_only_schedule_changes_and_closure` |
| 5 | Tests failed before the fix for the right reason; output saved to scratchpad/K62ZAP-failing-before.txt | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 6 | One shared helper decides full vs filtered for both project_events and task_events; filter is server-side | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 7 | Full suite, node --check app.js, compileall, git diff --check and jaira validate pass | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### GTEYTG — Secondary owners: primary owner can grant and remove full Owner access

[Ticket source](../../.jaira/tickets/01M39HQB2EFDXWXH92WYGTEYTG-secondary-owners-primary-owner-can-grant-and-rem.md) · lane signoff · declared DoD 11/11.

**Located evidence:** `service.py:565,591; app.js:2434; test_core SecondaryOwnerTests/test_db`.

**Current review:** Secondary created in disposable fixture. Every primary/secondary browser privilege and fresh removal probe not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Migration v16: 1 owner becomes primary and the schema matches a fresh database; 0 owners migrates and create_initial_owner then sets the flag; 2+ owners is refused before any change with user ids only, version unchanged; a failure late in v16 rolls back and a retry succeeds | Partial; see current review and main report limits | `test_failure_late_in_the_v16_step_rolls_back_then_retries`, `test_second_owner_written_after_the_early_check_is_refused_inside_the_step`, `test_two_owners_in_an_older_database_refuse_before_any_step_runs`, `test_v15_single_owner_becomes_primary_and_matches_fresh_schema`, `test_v15_with_two_owners_refuses_the_upgrade_without_touching_data`, `test_v15_without_an_owner_migrates_and_the_first_owner_becomes_primary` |
| 2 | Schema: the database refuses a second primary owner (unique index) and a primary who is not an owner (CHECK) | Partial; see current review and main report limits | `test_database_refuses_a_second_primary_and_a_primary_who_is_not_an_owner`, `test_fresh_database_has_the_primary_flag_its_index_and_user_events` |
| 3 | Primary grants and revokes: grant makes the user an owner (not primary) and records secondary_owner_granted with the prior role; revoke restores the prior role, revokes their sessions, keeps memberships and records secondary_owner_revoked; several secondaries allowed; a reason is required | Partial; see current review and main report limits | `test_grant_and_revoke_input_errors`, `test_primary_grants_and_revokes_a_secondary_owner`, `test_revoke_restores_a_chairman_and_several_secondaries_are_allowed` |
| 4 | Forbidden paths (403, nothing changed, owner_change_blocked recorded): a secondary grants, revokes a secondary, revokes the primary, deactivates the primary or another secondary, or changes project access of the primary or another owner; a Chairman or member calling grant/revoke; the primary cannot revoke themselves | Partial; see current review and main report limits | `test_non_owners_cannot_grant_or_revoke_owner_access`, `test_repeated_blocked_owner_changes_are_all_audited_and_notices_capped`, `test_secondary_owner_cannot_change_owner_access_or_target_other_owners`, `test_user_changes_read_the_target_under_the_write_lock` |
| 5 | Secondary owners use ordinary Owner powers (create project and user, decide an Owner request) and lose them on the next request after revoke | Partial; see current review and main report limits | `test_secondary_owner_has_ordinary_owner_powers_until_revoked` |
| 6 | An owner cannot approve or reject an Owner request they filed themselves; cancel still works | Partial; see current review and main report limits | `test_owner_request_decisions_by_several_owners` |
| 7 | Owner notifications go to every active owner except the actor; a template 'owner' task goes to the acting owner | Partial; see current review and main report limits | `test_owner_notifications_reach_every_other_active_owner`, `test_template_owner_role_goes_to_the_acting_owner` |
| 8 | HTTP: POST/DELETE /api/users/{id}/secondary-owner and GET /api/user-events with the same rules; /api/me and /api/users expose is_primary_owner | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 9 | People screen: Primary owner / Secondary owner badge; Make/Remove secondary owner only for the primary; Playwright screenshots as primary and as secondary | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 10 | Tests failed before the change; output saved to scratchpad/GTEYTG-failing-before.txt | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 11 | Full suite, node --check app.js, compileall, git diff --check and jaira validate pass | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### KBWY86 — Blocked-attempt notices: notify the acting owner for Item 2 events and cap repeats per person

[Ticket source](../../.jaira/tickets/01M3A64QKGH8B0F5SKYSKBWY86-blocked-attempt-notices-notify-the-acting-owner.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py:380,393; test_core blocked notices/test_db`.

**Current review:** Notice/cap tests in full suite. Fresh cap-window and blocked-history browser run not performed.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Acting owner is notified of attachment_removal_blocked, final_result_unmarked and attachment_removed (single-owner install covered); other kinds unchanged; schema v17 adds notifications.actor_user_id with index, fresh and upgraded databases equal; blocked-attempt notices are capped per recipient and actor per rolling 10 minutes in two buckets of 5 (owner_change_blocked on its own; the other blocked kinds pooled), the notice that reaches a cap says further attempts of that kind are in history only, the audit row is always written, a different actor still notifies, notices resume after the window; owner_change_blocked audits every repeat; a blocked import with no project is audited and listed separately from blocked owner changes; unit and migration tests; existing tests green. | Partial; see current review and main report limits | `test_blocked_import_without_a_project_is_audited_every_time_and_its_notice_capped`, `test_blocked_imports_do_not_push_owner_changes_out_of_the_history`, `test_blocked_notice_cap_is_per_actor`, `test_blocked_notice_window_edge_and_null_actor_rows`, `test_blocked_notices_are_capped_per_actor_and_every_attempt_is_audited`, `test_manager_into_unmanaged_project_viewer_and_chairman_are_blocked_and_owner_notified`, `test_owner_change_notices_have_their_own_cap_bucket`, `test_owner_self_notices_are_capped_too_and_ordinary_notices_are_not`, `test_repeated_blocked_owner_changes_are_all_audited_and_notices_capped`, `test_single_owner_is_notified_of_own_blocked_removal_unmark_and_removal`, `test_the_notice_that_reaches_the_cap_says_later_attempts_are_in_history_only` |

### PDDS2D — Server command to transfer the primary owner and reset a password

[Ticket source](../../.jaira/tickets/01M3A930RYSAXPWQVQP3PDDS2D-server-command-to-transfer-the-primary-owner-and.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `__main__.py:14; service.py:657,696; test_core ServerCommandTests/ServerCommandCliTests`.

**Current review:** Fresh CLI/service tests passed. No live credential/primary transfer performed; later 8-character policy supersedes old 12-character criterion.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | transfer-primary moves the primary flag to an active secondary owner in one transaction (exactly one primary always), keeps the old primary as a secondary owner, signs them out, audits and notifies the other active owners including the old primary, and refuses (changing nothing) an unknown, inactive, non-owner or already-primary target or a database with no primary; reset-password sets a 12+ character password read only from getpass twice for any active user, signs them out everywhere, clears failed sign-ins, audits and notifies the user (and other owners when the user is an owner); both ask for the target email unless --yes, exit 0/1/2 and never print a traceback; People screen labels both 'via server command'; README documents Windows and Linux use; service and CLI tests; existing tests green. | Partial; see current review and main report limits | `test_a_failure_part_way_through_a_transfer_changes_nothing`, `test_a_stale_old_primary_can_no_longer_change_owner_access`, `test_a_target_or_primary_that_changed_after_the_check_is_refused`, `test_database_errors_print_one_line`, `test_recovery_commands_refuse_a_missing_database_without_creating_one`, `test_refusals_exit_with_one_line_and_no_traceback`, `test_reset_password_for_any_active_user`, `test_reset_password_needs_an_interactive_terminal`, `test_reset_password_of_an_owner_tells_the_other_owners`, `test_reset_password_reads_the_password_twice_from_the_terminal_only`, `test_reset_password_refusals_change_nothing`, `test_serve_on_a_busy_port_prints_one_line`, `test_the_transfer_check_runs_under_the_write_lock`, `test_transfer_moves_the_primary_flag_and_keeps_the_old_primary_as_secondary`, `test_transfer_primary_needs_the_typed_email_unless_yes`, `test_transfer_refusals_change_nothing` |

### XX9RFM — Notify owners when a project is closed or its dates change

[Ticket source](../../.jaira/tickets/01M3ADA4DRPMWYVBJ2ZJXX9RFM-notify-owners-when-a-project-is-closed-or-its-da.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py:1061,4846,4961; test_core project notices`.

**Current review:** Fresh fixture closed synthetic project; Chairman linked extension notices observed. F9 badge reliability separate from stored notice delivery.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Closing a project (by any owner directly, or by an owner approving a Manager's close request) and changing its dates notify every other active owner and not the actor or non-owners, with a summary naming the project, closed (and whether with open work) or the dates old -> new, and who did it; secondary owners can still close a project with open work; no new audit rows and no schema change; tests for secondary and primary closes, approved close requests, date changes and a single-owner install; existing tests green. | Partial; see current review and main report limits | `test_a_secondary_owner_closes_a_project_with_open_work_and_the_primary_is_told`, `test_a_single_owner_gets_no_notice_of_their_own_project_changes`, `test_approving_a_managers_close_request_notifies_the_other_owners`, `test_project_date_changes_notify_the_other_owners_with_old_and_new_dates`, `test_project_notices_are_not_capped_skip_inactive_owners_and_show_cleared_dates`, `test_the_primary_closing_a_project_tells_the_secondary_owners` |

### 4T4DEA — Gate 2 slice 1: design foundation (tokens, self-hosted Inter, focus rings, no inline styles, no sideways scroll)

[Ticket source](../../.jaira/tickets/01M3BDCQSRG5SDAJY6J54T4DEA-gate-2-slice-1-design-foundation-tokens-self-hos.md) · lane signoff · declared DoD 6/6.

**Located evidence:** `style.css; static/fonts; test_web foundation`.

**Current review:** Observed phone route/table root has no horizontal overflow. Raw colours violate token rule; CSP/contrast/all-size audit not fully rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Inter is served by Astra from static/fonts with its OFL licence file: a strict file allowlist, the right content type, long caching for the versioned font files, and a CSP that names font-src 'self'; source and version recorded | Partial; see current review and main report limits | `test_font_faces_point_at_the_served_files_only` |
| 2 | style.css has semantic tokens (surface, line, muted text, spacing, radii, elevation) and a type scale, keeping today's palette values; the step-token contrast tests still pass | Partial; see current review and main report limits | `test_text_tokens_meet_contrast_on_their_backgrounds`, `test_tokens_type_scale_focus_and_reduced_motion` |
| 3 | app.js writes no inline style attributes (replaced by classes) and a test pins that; no CSP errors in the browser console | Partial; see current review and main report limits | `test_no_inline_style_attributes_reach_the_page` |
| 4 | Every interactive element shows a :focus-visible ring and prefers-reduced-motion removes transitions and animation | Partial; see current review and main report limits | `test_tokens_type_scale_focus_and_reduced_motion` |
| 5 | No sideways page scroll at 1440x900, 1024x768 or 390x844, and the phone header no longer overlaps; screenshots at all three sizes | Partial; see current review and main report limits | `test_toolbar_wraps_instead_of_scrolling_sideways` |
| 6 | Tests for the font route and headers and the static changes; full suite green; git diff --check, 0 CR bytes, node --check, jaira validate | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### PZTYC9 — Gate 2 slice 2: shell frame (left rail, top bar, hash router, filters in the URL, toolbar into menus)

[Ticket source](../../.jaira/tickets/01M3BE0B99E7TFPEA6MAPZTYC9-gate-2-slice-2-shell-frame-left-rail-top-bar-has.md) · lane signoff · declared DoD 6/6.

**Located evidence:** `index.html:22; app.js router:402; test_web shell`.

**Current review:** Fresh main routes/account/menu controls observed. F4/F5/F8/F9; private-capture design recommendation conflicts with delivered quick-add spec.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Left rail with Home, My Work, Inbox (unread badge), Projects and Capture; the current screen is marked (aria-current); on phones it becomes a bottom bar | Partial; see current review and main report limits | `test_shell_landmarks_rail_top_bar_and_menus` |
| 2 | Top bar with breadcrumb and page title, a search box (Ctrl K or Cmd K focuses it; Enter searches), and a user menu holding Keyboard shortcuts, Sign out, Sign out everywhere and People (owners only), usable while a task is open | Partial; see current review and main report limits | `test_a_failed_first_load_is_not_a_sign_out`, `test_menus_toggle_aria_expanded`, `test_no_page_wide_single_key_shortcuts`, `test_signing_out_reloads_the_page` |
| 3 | Hash router (#/home, #/my-work, #/inbox, #/projects) that needs no pushState; Home filters live in the URL, so reload and Back restore them; Node tests for the route parser and URL round trip | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 4 | The toolbar keeps only filters (plus Clear filters); its buttons move into a More menu (keyboard operable, Esc closes and returns focus) and New project moves to the Projects page | Partial; see current review and main report limits | `test_shell_landmarks_rail_top_bar_and_menus` |
| 5 | Home shows today's dashboard; My Work lists open tasks assigned to me grouped by due date; Inbox shows today's inbox as a page with Approve/Reject still working; Projects lists projects and opens one on Home; Capture quick-adds a task through POST /api/tasks | Partial; see current review and main report limits | `test_capture_reuses_the_create_form`, `test_chip_and_toast_text_is_escaped`, `test_owner_only_items_are_hidden_for_other_roles` |
| 6 | Pinned ids and tests kept or changed on purpose with coverage kept; full suite green; git diff --check, 0 CR bytes, node --check, jaira validate; Chromium screenshots at 1440/1024/390 with no sideways scroll and no CSP errors; README updated | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### DR3PKR — Gate 2 slice 3: docked task side panel with its own link

[Ticket source](../../.jaira/tickets/01M3BF5Z67ZKA6JJG020DR3PKR-gate-2-slice-3-docked-task-side-panel-with-its-o.md) · lane signoff · declared DoD 5/5.

**Located evidence:** `app.js:1845; test_web panel drivers`.

**Current review:** Fresh drawer swap/save gives persisted wrong-task write F1. Identity integrity is not ready despite passing driver tests.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Task detail opens in a right-side panel (about 460px, non-modal) while the current screen stays visible and scrollable; clicking another task swaps the panel | Contradicted by F1 | `test_opening_adds_the_task_to_the_link_and_swapping_replaces_it`, `test_panel_markup_order_and_layout` |
| 2 | The panel has its own link: ?task=<id> over the current screen and #/task/<id> as a full page; both survive reload and Back/Forward; Copy link copies it | Partial; see current review and main report limits | `test_a_filter_picked_while_the_panel_is_open_survives_closing_it`, `test_task_ids_from_a_link_are_checked_and_fetched_fresh`, `test_the_task_page_is_the_same_panel_and_closes_to_the_last_screen` |
| 3 | Esc and a close button close it; focus moves into the panel when it opens and returns to the control that opened it; a first Esc in a panel field keeps focus in the panel; everything in it is keyboard reachable; j/k move to the next or previous task while focus is in the panel | Partial; see current review and main report limits | `test_closing_goes_back_and_returns_focus_to_the_opener`, `test_keys_inside_and_outside_the_panel` |
| 4 | Header shows title, state chips (tint + dark text + glyph), a role line and a compact fact grid, then description, steps and dependencies, then one Lifecycle block with today's button names; each fact shown once; below 1024px the panel is full-screen | Partial; see current review and main report limits | `test_panel_markup_order_and_layout`, `test_state_chips_carry_a_glyph_or_word` |
| 5 | Pinned ids (#detail-dialog, #detail-body, #detail-edit, #add-dep-button) keep working and the Inbox refresh on close still works; tests for the new behaviour; full suite green; git diff --check, 0 CR bytes, node --check, jaira validate; Chromium screenshots 1440/1024/390 with no CSP errors; README, handoff and CLAUDE.md test count updated | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### VPYGY5 — Gate 2 slice 4: Command Center Home

[Ticket source](../../.jaira/tickets/01M3BS57ZY3F4GP2D6K1VPYGY5-gate-2-slice-4-command-center-home.md) · lane signoff · declared DoD 6/6.

**Located evidence:** `app.js:1299; test_web Home drivers`.

**Current review:** Fresh Owner/Member/Viewer defined metrics/role sections observed; F9 badge fallback and minor eighth-bucket wrap. All empty/viewport cases not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Home shows a health strip (Overdue, Blocked, Awaiting Owner for owners only, Due in 7 days, Critical path, Undated); each tile states its definition and time and opens the matching filtered list | Partial; see current review and main report limits | `test_home_command_center_for_owner_member_and_empty_install` |
| 2 | Needs Owner decision (owners only) lists pending requests with live Approve and Reject and a Review button that opens the task panel; hidden for everyone else | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 3 | At risk, My next actions (Today / This week / Later), a This week strip and Portfolio by entity; rows open the task panel | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 4 | The Portfolio Gantt and schedule table stay reachable at #/portfolio (linked from Home and Projects), old #/home filter links redirect there, and the new Risk filter and No due date option back the tiles | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 5 | A new install (no projects) and a member with no work get clear empty states; owner-only parts hidden for members | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 6 | Behaviour tests (node driver), full suite, git diff --check, 0 CR, node --check, jaira validate; Chromium 1440/1024/390 as owner and member with no CSP errors or sideways scroll; README | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### CR121Z — Gate 2 slice 5: project page with Overview, List, Board, Timeline and Activity tabs

[Ticket source](../../.jaira/tickets/01M3BSY3W3FH34MF87RACR121Z-gate-2-slice-5-project-page-with-overview-list-b.md) · lane signoff · declared DoD 5/5.

**Located evidence:** `app.js:733,678; test_web project drivers`.

**Current review:** Fresh project overview/list/timeline/tab links observed. Board/activity full browser matrix not rerun; F5 create affordance.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Route #/project/<id>/<tab> with tabs Overview, List, Board, Timeline and Activity (links, current tab marked); unknown or inaccessible projects show a clear empty state; Projects rows link into it | Partial; see current review and main report limits | `test_project_routes_tabs_and_actions` |
| 2 | Board: 7 read-only columns from the documented mapping with counts; cards show title, owner initials, due chip, state glyphs and steps done; Accepted and Closed start collapsed with 'Owner decides'; a Divide by control (none, owner, criticality) kept in the link; cards open the task panel | Partial; see current review and main report limits | `test_board_cards_columns_and_collapsed_owner_columns`, `test_divide_by_owner_and_criticality`, `test_statuses_map_into_seven_columns` |
| 3 | List reuses the schedule table and Timeline reuses the Gantt, both scoped to the project; Activity reuses the project history; Overview shows project facts, progress and dates; rows and bars open the task panel | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 4 | Project actions on the page: Capture into this project; Save as template and Close project for owners only | Partial; see current review and main report limits | `test_project_routes_tabs_and_actions` |
| 5 | Behaviour tests (column mapping, lanes, collapsed columns, escaping, route parse), full suite, git diff --check, 0 CR, node --check, jaira validate; Chromium 1440/1024/390 as owner and member, no CSP errors, no page-level sideways scroll; README with the column mapping | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### FKVHH8 — Gate 2 slice 6: My Work groups and calendar month view, Inbox polish

[Ticket source](../../.jaira/tickets/01M3BVD71SMNH4E0M2CRFKVHH8-gate-2-slice-6-my-work-groups-and-calendar-month.md) · lane signoff · declared DoD 5/5.

**Located evidence:** `app.js:539,1683; test_web My Work/calendar/Inbox`.

**Current review:** Fresh Member due groups and Chairman Inbox. Calendar month/phone agenda browser matrix not completed; F9 global unread fallback.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | My Work list groups open tasks into Overdue, Today, This week, Later and No date with counts, soonest first; each row opens the task panel; a good empty state | Partial; see current review and main report limits | `test_filter_keeps_empty_groups_and_says_when_nothing_matches`, `test_my_work_lists_five_groups_with_counts_and_only_my_open_work` |
| 2 | My Work has List and Calendar tabs (#/my-work and #/my-work/calendar); the calendar is a Monday-first month grid with previous, next and today, shows due tasks on their day, collapses more than 3 per day into '+N more', and every item opens the task panel; month kept in the link | Partial; see current review and main report limits | `test_month_grid_starts_on_monday_marks_today_and_folds_busy_days`, `test_month_links_keep_scope_and_the_route_reads_month` |
| 3 | On a phone the calendar becomes an agenda list of the month's days that have work; no page-level sideways scroll | Partial; see current review and main report limits | `test_phone_agenda_lists_only_days_with_work` |
| 4 | Inbox: tabs Needs action (owners only), Unread and All with counts; unread rows are styled distinctly; each row can open its task and be marked read; Mark all read; owners see requests first with live Approve/Reject | Partial; see current review and main report limits | `test_inbox_puts_owner_requests_first`, `test_inbox_tabs_for_a_member` |
| 5 | Behaviour tests (grouping, month grid, +N collapse, agenda, inbox tabs), full suite, git diff --check, 0 CR, node --check, jaira validate; Chromium 1440/1024/390 as owner and member, no CSP errors; README, handoff and CLAUDE.md test figure updated | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### 3C1Z74 — Gate 2 slice 7: phone and accessibility pass, plus the Gate 2 leftovers

[Ticket source](../../.jaira/tickets/01M3C0MZ2TASFSNYRN1E3C1Z74-gate-2-slice-7-phone-and-accessibility-pass-plus.md) · lane signoff · declared DoD 4/4.

**Located evidence:** `style.css responsive rules; index landmarks; test_web accessibility drivers`.

**Current review:** Fresh phone table/fallback; F6 unnamed selects contradict naming criterion; F4 Cancel. Screen readers/all contrasts/targets/widths unverified.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Phone and tablet pass: every route (Home, Portfolio, Projects, project tabs, Board, My Work, Calendar and agenda, Inbox, task panel, Capture, People, More menu, sign-in) at 360x740, 390x844, 768 and 1024 has no sideways page scroll, no clipped text, 44px tap targets below 1024px, 16px form fields, and the bottom bar never covers content (safe-area inset) | Partial; see current review and main report limits | `test_phone_agenda_lists_only_days_with_work`, `test_task_links_are_44px_targets_on_phones_and_tablets`, `test_touch_widths_get_44px_targets_16px_fields_and_room_for_the_bottom_bar` |
| 2 | Accessibility pass: one h1 per route, nav/main/aside landmarks, a skip link, every control has a name, aria-current on the rail and tabs, a visible focus ring on everything, route changes announce the new page, reduced motion honoured, all text at 4.5:1 or better (including the Gantt project flag); checked by a scratch Playwright audit (names, contrast, headings, landmarks, target sizes, field font size, sideways scroll, bottom-bar overlap) | Contradicted by F6 unnamed controls | `test_gantt_project_flags_meet_contrast`, `test_legend_keys_and_sign_in_landmark`, `test_what_is_behind_a_full_screen_panel_is_inert` |
| 3 | Leftovers: 'Open full page' hidden where the panel is already full screen; Divide by owner groups lanes by user id, so two people with the same name get separate lanes; the Gantt today line and the portfolio 'As of' use the server's today; an SVG favicon served from the static allowlist; Home shows a visible 'Portfolio Gantt' link, documented in the README | Partial; see current review and main report limits | `test_divide_by_owner_and_criticality`, `test_gantt_today_line_and_as_of_use_the_servers_today` |
| 4 | Behaviour tests where testable, full suite, git diff --check, 0 CR, node --check, jaira validate; Chromium screenshots at 1440/1024/768/390/360 as owner and member without CSP errors; README, handoff (lock #11 not yet pushed, test count) and the CLAUDE.md figure updated | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### JN1QYG — Board drag and drop with Move to and 15-second Undo

[Ticket source](../../.jaira/tickets/01M3CAJRFH9J4RJFVMSZJN1QYG-board-drag-and-drop-with-move-to-and-15-second-u.md) · lane signoff · declared DoD 4/4.

**Located evidence:** `app.js:778; test_board/test_web board driver`.

**Current review:** Current rules/driver suite support Move/Undo; mouse/trackpad/keyboard/phone Board and timed Undo not freshly executed here.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Server: a persisted board order (schema v18 tasks.board_rank, migration with tests) and board move/reorder/undo endpoints that reuse today's rules (role limits, reason rules, dedicated actions, Owner requests for managers' protected moves), refuse dependency-blocked forward moves (owner override with confirm), and audit every successful and blocked move | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 2 | Board UI: owners and managers drag cards with a mouse or trackpad (within a column to reorder, across columns to change status); invalid drops snap back with the server's reason; members and viewers cannot drag; every card has a Move to menu usable from the keyboard and on phones (where dragging is off) | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 3 | Undo: an ordinary move shows a 15-second toast with Undo; Undo is a new audited change through the same rules, refused if the task changed since; requests, submissions, acceptances and closes do not offer Undo | Partial; see current review and main report limits | `test_an_ordinary_move_posts_once_and_offers_undo_for_fifteen_seconds`, `test_undo_is_a_new_audited_change_and_refuses_after_a_later_change`, `test_undo_window_is_fifteen_seconds_plus_grace` |
| 4 | Behaviour tests (service, web, migration, node driver), full suite, git diff --check, 0 CR, node --check, jaira validate; Playwright evidence at 1440 and 390 (mouse drag, keyboard Move to, Undo) without CSP errors; README updated | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### X07XV4 — Task locks and Gantt date drag

[Ticket source](../../.jaira/tickets/01M3CCSS8AAJZS0MAY4BX07XV4-task-locks-and-gantt-date-drag.md) · lane signoff · declared DoD 4/4.

**Located evidence:** `app.js:1000,1070; test_board/test_web drag/lock drivers`.

**Current review:** Later row scheduling supersedes original bar-drag UX requirement. Fresh one phone linked move; multi-session conflict and all pointer paths not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Server: task_locks table (schema v19, migration with tests); acquire, renew (only a live lease) and release, and owner force-unlock (audited as task_lock_forced, holder notified); while someone else holds an unexpired lease, every task write refuses with 409 naming the holder and expiry, including reviewer changes (reviewer_added/reviewer_removed events), links from a locked predecessor and board reorders; leases expire after 60 s | Partial; see current review and main report limits | `test_every_write_path_revalidates_the_lock` |
| 2 | Gantt: owners and managers drag a bar to move it and drag its ends to change start or due, with a live date tip; members, viewers and phones cannot drag (the task panel date fields stay); invalid dates are refused with a reason; ordinary moves apply with a 15-second Undo; a move that breaks a dependency, touches the critical path or passes the project target opens an impact confirm, and the confirmed move notifies the other owners | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 3 | Lock UI: the task panel takes an edit lease while its form is in use and shows who holds a lease and until when; board cards show a lock chip; board and Gantt drags take a drag lease; owners get Force unlock | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 4 | Behaviour tests (service, web, migration, node driver), full suite, git diff --check, 0 CR, node --check, jaira validate; Playwright evidence at 1440 and 390 of a Gantt drag with Undo and a lock conflict between two sessions, without CSP errors; README updated | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### XV92JJ — Bulk select and WIP limits

[Ticket source](../../.jaira/tickets/01M3CEHBP9XNTK0SG1Q8XV92JJ-bulk-select-and-wip-limits.md) · lane signoff · declared DoD 4/4.

**Located evidence:** `app.js:1130; service.py:3858,3948; test_board/test_web`.

**Current review:** Bulk/WIP implementation and suite inspected. Fresh browser range selection, blocked removal and bulk Undo not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Server: preview and apply for bulk status (Draft/Ready/In progress), assignee and due-date offset; the preview lists counts and blocked items with reasons; apply is all-or-nothing in one transaction with bulk locks (any task in use by someone else names the holders and nothing starts), one bulk_change project event plus per-task task_updated events, and a bulk Undo that restores every task only if none changed since | Partial; see current review and main report limits | `test_a_failure_part_way_rolls_every_task_back`, `test_a_task_in_use_by_someone_else_stops_the_whole_change` |
| 2 | WIP limits: schema v20 wip_limits with migration tests; only an owner sets or clears limits per open board column per project (whole numbers, all columns in one transaction, audited as wip_limit_changed per changed column); every status-changing write a person makes (board, bulk and both Undos, panel status, hold, submit, reopen, request changes, create, promotion to top level) that would exceed a limit is refused with a clear reason, and an owner may override after a confirm (wip_limit_override in the same transaction); entry into Blocked caused by a dependency is not refused | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 3 | UI: checkboxes on board cards and schedule-list rows, Shift-click for a range, keyboard selection (Space toggles, Shift+Arrow extends on the list), a bulk bar with the three actions, a preview with counts and blocked items and a Remove blocked button, Undo toast; owners see WIP settings on the board, and column heads show n / limit | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 4 | Behaviour tests (service, web, migration, node driver), full suite, git diff --check, 0 CR, node --check, jaira validate; Playwright evidence at 1440 and 390 (bulk bar, preview, WIP refusal) without CSP errors; README updated | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### 3FQEKB — Assignment rules: Chairman assigns, never receives; viewers get subtasks only

[Ticket source](../../.jaira/tickets/01M3DP7RSN7ZHDRR7SCC3FQEKB-assignment-rules-chairman-assigns-never-receives.md) · lane signoff · declared DoD 5/5.

**Located evidence:** `app.js fillAssignees; test_assignment/test_web`.

**Current review:** Fresh eligibility choices exclude Chairman; Viewer subtask present. F2 silent unassignment and F3 misleading readable History.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Server: can_assign (owner, the project's manager, Chairman) gates the assignee in update_task and bulk Assign; the Chairman's other edits stay refused, and can_manage_project is unchanged | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 2 | Server: _validate_assignee refuses the Chairman everywhere (create, update, bulk, hold owner) and a viewer on a top-level task; set_parent(None) refuses a viewer-assigned subtask; the importer refuses those rows with a clear row error; templates never assign the Chairman or a viewer on a top-level task | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 3 | Existing assignments are kept and flagged needs_new_assignee (list, panel, card, row, Home count for owners and managers); the flag clears on reassignment | Partial; see current review and main report limits | `test_3fqekb_the_needs_a_new_assignee_chip_and_home_count` |
| 4 | Pickers never list the Chairman and list viewers only for subtasks, labelled (viewer); the Chairman sees only the panel assignee control and bulk Assign as new UI | Partial; see current review and main report limits | `test_3fqekb_pickers_label_viewers_and_keep_a_forbidden_current_owner`, `test_3fqekb_the_chairman_sees_the_assignee_control_and_the_chip`, `test_3fqekb_the_chairmans_bulk_bar_offers_assign_only` |
| 5 | Tests for each rule and role (service, importer, web and driver), README permissions table, handoff and CLAUDE.md updated, screenshots at 1440 and 390, full suite green | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### G1PPV7 — A viewer assigned a top-level task before 3FQEKB can still submit it

[Ticket source](../../.jaira/tickets/01M3E863QH4ZJSR22J2SG1PPV7-a-viewer-assigned-a-top-level-task-before-3fqekb.md) · lane signoff · declared DoD 7/7.

**Located evidence:** `service.py submit permissions; app.js buildLifecycle; test_assignment ExistingAssignmentsTests`.

**Current review:** Fresh suite supports legacy Viewer protection; every role/demotion browser transition not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | _may_submit refuses a project viewer who is the assignee of a top-level task (service.py), using the same _assignee_refusal rule as collaborators; submit_task refuses it before and inside the transaction | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 2 | A viewer's own subtask still submits; a member assignee on a top-level task still submits; a manager or owner still submits a flagged task | Partial; see current review and main report limits | `test_a_member_demoted_to_viewer_loses_submit_on_a_top_level_task_until_restored` |
| 3 | A member demoted to viewer loses Submit on their top-level task, and gets it back when restored to member | Partial; see current review and main report limits | `test_a_member_demoted_to_viewer_loses_submit_on_a_top_level_task_until_restored` |
| 4 | permissions.can_submit is false for the viewer legacy assignee, so the task panel shows no Submit; the task keeps needs_new_assignee | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 5 | Every path into submitted checked and recorded: submit_task, board move to Submitted, update_task, bulk, importer, set_parent promotion | Partial; see current review and main report limits | `test_a_member_demoted_to_viewer_loses_submit_on_a_top_level_task_until_restored` |
| 6 | Tests: service tests in tests/test_assignment.py (refused and stays draft; own subtask allowed; demote then restore) and an HTTP test in tests/test_web.py (can_submit false, POST submit 403); full suite green | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 7 | Docs: HANDOFF_2026-09-26.md permissions table and note, NEXT_STEPS.md A3 item 8 and README permissions text updated to say it is fixed | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### SFAZD7 — A0: restore the Windows test baseline

[Ticket source](../../.jaira/tickets/01M42BMWMFBR1WSTTCRJSFAZD7-a0-restore-the-windows-test-baseline.md) · lane signoff · declared DoD 5/5.

**Located evidence:** `db.py connection cleanup; Node encoding/test setup; test_db/test_web`.

**Current review:** Fresh Windows full832 passed; Node drivers ran. Historical guard removal and independent acceptance not repeated.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Node driver output is decoded explicitly as UTF-8 and the normal Windows run loads every intended UI class. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 2 | Failed database connection setup closes the connection without modifying refused migration data; a regression fails when cleanup is removed. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 3 | Secondary test connections close before temporary directory removal; the affected interleaving and refusal tests pass without WinError 32. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 4 | Recovery commands still refuse missing databases without creating files; path assertions use resolved identity. | Partial; see current review and main report limits | `test_recovery_commands_refuse_a_missing_database_without_creating_one` |
| 5 | The documented full suite passes with exact count and explained skips; independent review and LF/diff checks pass; Aly alone accepts the result. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### WYM776 — Repair independent importer defects before launch development

[Ticket source](../../.jaira/tickets/01M431S373JZGE26X4GPWYM776-repair-independent-importer-defects-before-launc.md) · lane signoff · declared DoD 6/6.

**Located evidence:** `importer.py/xlsx_reader.py; test_import/test_xlsx_reader; IMPORTER_REPAIRS_2026-10-04.md`.

**Current review:** Fresh parser/import tests pass. Import-key History browser proof and native spreadsheet evidence remain dated receipts.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Actual corrupt CRC and deflate XLSX members return XlsxError and HTTP 400 on preview and commit without task writes; all specified archive read exceptions are translated. | Partial; see current review and main report limits | `test_corrupt_zip_members_are_refused`, `test_truncated_or_unreadable_zip_members_are_refused` |
| 2 | Closed project filled-template downloads refuse Owner and Managers before any key or audit write; service and HTTP role tests pass. | Partial; see current review and main report limits | `test_closed_project_template_downloads_write_nothing`, `test_template_download_rechecks_project_before_key_assignment` |
| 3 | Parent cycle errors identify the closing file row in new, existing and mixed graphs; invalid related rows cannot commit. | Partial; see current review and main report limits | `test_parent_cycle_does_not_blame_a_later_unchanged_parent`, `test_parent_cycle_error_identifies_the_closing_changed_row` |
| 4 | Existing XML-illegal character protection passes, and numeric-versus-text progress and eligibility warnings are documented accurately. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 5 | Task history shows Import key assigned in a browser; JavaScript syntax passes. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 6 | CSV format remains unchanged; full Windows suite, removal checks, independent review, LF and diff checks pass; publication is prepared under the branch rules. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### 1G7Q4C — Prevent mixed Manager saves from silently dropping edits

[Ticket source](../../.jaira/tickets/01M433XJYSX1EK0C6VY81G7Q4C-prevent-mixed-manager-saves-from-silently-droppi.md) · lane signoff · declared DoD 4/4.

**Located evidence:** `service.py update contract; app.js:2372; test_update_task_contract/test_web`.

**Current review:** Atomic Manager guard tests passed. F1/F2 are distinct unresolved UI identity/owner errors; mixed-save browser refusal not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | A Manager save that combines an actual ordinary edit with a protected status request fails atomically with a clear error; task, revision, events, requests and notifications remain unchanged. | Partial; see current review and main report limits | `test_manager_mixed_status_request_refuses_without_any_database_write` |
| 2 | Service tests cover all persisted ordinary fields, entering and leaving protected statuses, normalized unchanged form values, ordinary Manager edits and direct App Owner edits; read-only roles remain refused. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 3 | HTTP tests prove status 400 and no partial writes or requests; browser verification proves the entered form values remain available after refusal. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 4 | Removing the service guard makes the regression fail; focused and full Windows suite, LF and diff hygiene and independent review pass before publication. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### WSA9FZ — Consolidate local Astra data under the main checkout

[Ticket source](../../.jaira/tickets/01M4A4DE3SDJJCMWC7B5WSA9FZ-consolidate-local-astra-data-under-the-main-chec.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `Start-Astra.ps1; LOCAL_ASTRA.md; ticket relocation proof`.

**Current review:** Operator/data-relocation receipt only; live data not moved or independently compared again. Current recovery/hosting proof unverified.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | SQLite backup, integrity and logical contents verified before and after relocation; old folder relocated with all companions; data directory ignored by Git; explicit loopback launcher and local instructions verified; independent read-only review passes. | Unverified current rerun; dated operational/design artifact | No exact named-proof match; family suite ran |

### 16JJ96 — Allow owners to rename an entity without breaking project links

[Ticket source](../../.jaira/tickets/01M4B3KKG954F3JQCZDN16JJ96-allow-owners-to-rename-an-entity-without-breakin.md) · lane signoff · declared DoD 1/1.

**Located evidence:** `service.py:850; app.js People rename; test_entity_rename`.

**Current review:** Fresh service/HTTP regressions pass; no live entity rename performed and full current browser rename not rerun.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Owner rename UI and HTTP/service path work; IDs and project filing stay unchanged; old/new/actor audit recorded; blanks, invalid names, duplicates and unauthorized roles refused without partial writes; browser, full suite, guard mutation and independent review pass. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

### ZQQCJM — B1 security review and verified HTTP hardening

[Ticket source](../../.jaira/tickets/01M4T6J8BQN8HRP5KZNGZQQCJM-b1-security-review-and-verified-http-hardening.md) · lane human · declared DoD 1/1.

**Located evidence:** `web.py framing/headers/login; xlsx_reader.py; test_http_security/test_http_timeout; B1_SECURITY_2026-10-13.md`.

**Current review:** Fresh real-socket/security regression suite passed. Earlier independent source proof dated; hosted and broader adversarial coverage unverified.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | Full suite, independent final diff review, LF/scoped hygiene and short security handoff pass; ticket waits for Aly acceptance. | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

## Context and follow-ups

### JQY55P — Explore Astra native-HTML UX shell

[Ticket source](../../.jaira/tickets/01M2WNN5PQXBBCD0XTZGJQY55P-explore-astra-native-html-ux-shell.md) · lane human · declared DoD 1/1.

**Located evidence:** `design/astra-shell-prototype.html; ticket proof; docs/design/astra-product-ux-baseline.md`.

**Current review:** Design artifact, not deployed functionality. Prototype visual/interaction acceptance not rerun; current product reviewed separately.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | A clearly marked standalone native-HTML prototype provides three structurally different shell/task-detail variants selectable by ?variant=A\|B\|C and a bottom switcher with keyboard arrows; uses realistic Astra data; demonstrates navigation, view switching, task drawer, role cues, polished controls/dialogs, external-link versus managed-file attachments, final-result removal block, owner permanent-link action, notification feedback, responsive behavior around 1440px and 1024px, visible focus/reduced-motion support, and no persistence or live API mutations; includes concise evaluation notes and an explicit recommended variant; syntax/structure checks pass and visual verification is performed if a browser is available, otherwise disclosed. | Unverified current rerun; dated operational/design artifact | No fresh artifact-test execution; dated proof only |

### AX572Q — Prototype governed Astra drag-and-drop

[Ticket source](../../.jaira/tickets/01M2X47YF0DA7QCQV4QGAX572Q-prototype-governed-astra-drag-and-drop.md) · lane human · declared DoD 1/1.

**Located evidence:** `design/astra-drag-drop-prototype.html; docs/design/governed-drag-drop-contract.md`.

**Current review:** Exploratory contract includes future boundaries; does not prove all operations exist. Current scheduling rules supersede illustrative prototype.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | A durable Markdown interaction contract enumerates the approved roles, invariants, operation lifecycle, file/batch limits, locks, audit/notification rules, accessibility fallbacks, and a small deep-module interface for later implementation; a self-contained native-HTML A-hybrid logic prototype visibly exposes state, supports free-play and guided happy/conflict/blocked/What-if scenarios across Kanban, Gantt, dependencies, files, cross-project actions, bulk locks, Undo/restoration, and critical-path recalculation without persistence or live mutations; HTML and JavaScript syntax checks pass; desktop and 1024px visual renders are inspected and material defects corrected; limitations and the separate production implementation boundary are explicit. | Unverified current rerun; dated operational/design artifact | No fresh artifact-test execution; dated proof only |

### Z9JCZ6 — Adopt Monday and Trello workflow UX lessons

[Ticket source](../../.jaira/tickets/01M2Y8V81ZMKDSPMFA3DZ9JCZ6-adopt-monday-and-trello-workflow-ux-lessons.md) · lane human · declared DoD 1/1.

**Located evidence:** `docs/research/monday-trello-workflow-ux-research.md; docs/design/astra-product-ux-baseline.md`.

**Current review:** Research/design baseline, not shipped behavior. Private Capture contract conflict identified; external product facts not revalidated here.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | A source-cited research report distinguishes verified official capabilities, Reddit methodology/themes, inferences and limitations; material links and time-sensitive claims are independently checked; a durable Astra product UX baseline explicitly adopts, adapts or rejects the strongest Monday/Trello patterns for Command Center, project views, Board, Timeline, task detail, Inbox/My Work/capture, dashboards/workload, automation, templates/onboarding, mobile/accessibility and low bandwidth; approved Astra authority/security decisions are unchanged; the report and baseline are internally consistent and no unsupported prevalence or product claims remain. | Unverified current rerun; dated operational/design artifact | No fresh artifact-test execution; dated proof only |

### MTEDTM — Consolidate Astra decisions and sharing handoff

[Ticket source](../../.jaira/tickets/01M2YAR4MB5SKTWG3RB3MTEDTM-consolidate-astra-decisions-and-sharing-handoff.md) · lane human · declared DoD 1/1.

**Located evidence:** `ticket handoff; docs/handoff/PRE_DEPLOYMENT_REVIEW_2026-10-13.md`.

**Current review:** Current release plan supersedes historical counts/readiness assumptions; no account/deployment authority inferred.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | A new dated Markdown handoff captures the complete current implementation status, all settled decisions by topic, unresolved human gates, authoritative source hierarchy, exact verified local run/test commands, recommended production runtime, Oracle/private-server/desktop hosting choices, safe user-sharing and onboarding flow, security/backup/monitoring requirements, implementation sequence, acceptance gates, Jaira state and exact next-agent start instructions; current versus planned behavior is unmistakable; existing docs are not silently superseded; source links and representative current hosting facts are checked; the handoff is internally cross-checked and committed with its ticket. | Unverified current rerun; dated operational/design artifact | No fresh artifact-test execution; dated proof only |

### 3NT40T — Excel import hardening follow-ups

[Ticket source](../../.jaira/tickets/01M343BZ654VN11E38293NT40T-excel-import-hardening-follow-ups.md) · lane human · declared DoD 0/8.

**Located evidence:** `WYM776; C9KPH6; ZQQCJM; test_import/test_xlsx_reader/test_workplan`.

**Current review:** All eight follow-up criteria read. Later XLSX decision and repairs need owner-only board reconciliation; 0/8 remains declared, no acceptance inferred.

| Criterion | Exact ticket requirement | Current assessment | Fresh named tests from declared proof |
| --- | --- | --- | --- |
| 1 | xlsx_reader.py: corrupt/truncated zip parts (BadZipFile, zlib.error, EOFError, OSError around archive.read) raise XlsxError and reach the client as 400, with a test for a bad-CRC part and a corrupt-deflate part | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 2 | service.py _template_project: template download for a closed project is refused for Managers exactly like an upload (as _import_authorize does) and assigns no Import Keys; tested | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 3 | importer.py _xml/_xml_text strip XML-illegal control characters so a task with \x0b or \x0c in title or notes yields a workbook read_workbook parses; tested | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 4 | docs/design/excel-import.md corrected at ~L116 (W_PERSON_NOT_ELIGIBLE on unedited re-upload) and ~L201 (only numeric 0.45 cells scale; text 0.45 is refused) | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 5 | app.js EVENT_LABELS gains import_key_assigned with a human label; node --check clean | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 6 | CSV template and CSV export neutralise cells starting with =, +, -, @ (leading apostrophe or space); tested; existing CSV re-upload still round-trips unchanged | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 7 | Mixed new/existing parent cycle is reported on the row whose parent closes the loop, consistently with the pure-existing case; probe R2b updated | Partial; see current review and main report limits | No exact named-proof match; family suite ran |
| 8 | Full suite green (.venv/bin/python tests/run.py), git diff --check clean, no behaviour change to anything in the C9KPH6 definition of done | Partial; see current review and main report limits | No exact named-proof match; family suite ran |

## Already accepted dependencies and excluded scope

W6ZSGA, JM7CFP and 2FREQ9 have recorded chat acceptance; none is awaiting a new
acceptance decision from this review. Their implementation still participates in
current workplan/scheduling/notification checks. JM7CFP declared DoD remains unticked.
The 25 Done tickets and 14 backlog records are inventoried in the board audit;
they are not newly unaccepted built tickets. Backlog/superseded/deferred features
and hosting gates remain separate from the defects in this report.

26ZF8D is the new review coordination ticket. Existing lanes were preserved.
Do not convert a Partial/Unverified criterion, a passing suite, or this inventory
into owner acceptance or hosted readiness.
