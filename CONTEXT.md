# Astra Project Tracker

Astra is a private, evidence-based project-management tracker. This glossary fixes
the language of the domain so the code and the docs stop conflating terms.

## People & roles

**App Owner**:
The single organization-wide authority who hosts and runs Astra (currently one
person). Only the App Owner sees private originals and full derivatives, grants and
revokes access, and can exceptionally close a project with outstanding work.
_Avoid_: owner (unqualified), admin, superuser.

**Task Owner**:
The one organizational person accountable for a single task or subtask. Each
subtask has its own Task Owner, who may differ from the parent task's — this is how
work is distributed across several people along a chain. There is exactly one per
task/subtask.
_Avoid_: owner (unqualified), assignee (reserved sense), responsible.

**Project Owner**:
The organizational person accountable for a whole project's delivery (holds the
project-manager membership on it). Distinct from the App Owner and from the Task
Owners of the project's individual tasks.
_Avoid_: owner (unqualified), manager (bare), lead.

**Chairman**:
An organizational role with org-wide project visibility and the narrow right to assign
task/subtask owners, without private-source access or being assigned work as a Task
Owner or Collaborator. Designation as an Approver permits acceptance recommendations;
other project powers require an explicit project role, and the global role cannot
decide protected actions, close projects, grant access or manage files.

**Approver**:
A supporting person designated to recommend acceptance of submitted work to the App
Owner, who makes the final decision; the Chairman and project viewers may be Approvers.
Designation grants no other protected-action power or Task Owner accountability.
_Avoid_: assignee, member (for this specific task role).

**Reviewer**:
A supporting person recorded as reviewing work, including the Chairman or a project
viewer, without request/decision power or Task Owner accountability by designation.
_Avoid_: assignee, member (for this specific task role).

**Collaborator**:
A supporting person who contributes to work without request/decision power or Task
Owner accountability by designation.
_Avoid_: assignee, member (for these specific task roles).

## AI assessment

**Assessor**:
The selected AI that reads Evidence and produces Proposals for the App Owner to
review. Provider-swappable, and each provider is reached by its own transport:
**Gemini** via its API key (as EPO already does); **Claude** and **Codex** via their
subscription CLIs (`claude -p`, `codex exec`) because the user holds subscriptions,
not API keys, for those two. The Assessor interface hides this difference — a caller
asks for Proposals and never learns which transport ran. It never changes the board
itself.
_Avoid_: model, AI (bare), bot, agent.

**Evidence**:
A normalized source record the Assessor reads — a thread, message, or attachment
under the machine boundary (`_machine`) — cited by its `manifest` path. Read-only;
authoritative originals live outside `_machine` and are not read by default.
_Avoid_: document (ambiguous), source (bare), input.

## Import

**Import template**:
The locked Excel workbook (or its CSV twin) that Astra generates from the App Owner's
current column configuration: `README`, `Project` (the project header), `Tasks` (a
protected header row, dropdowns from a hidden `Lists` sheet, dd-mm-yyyy date validation,
pre-filled Import Keys), a locked `Example`, a `People` sheet in the Full preset, and a
very-hidden `_astra` sheet whose version marker is a hash of the configuration. Two
presets exist: Simple (nine columns, the default) and Full (eighteen). Uploads must match the header row of
the current configuration exactly; a template downloaded before the App Owner changed
the columns is rejected. _Avoid_: spreadsheet (bare), sheet (bare), upload format.

**Import Key**:
The stable per-project identifier a user gives each row of the template. Re-importing a
file updates the task that carries the same Import Key instead of creating a duplicate;
Parent Key and Predecessors refer to it. It is stored on `tasks.import_key`.
_Avoid_: task id (that is Astra's internal id), row number, external id.

**Import (preview / commit)**:
The two-step load of a filled template. Preview parses and validates every row (OK /
warning / error) and writes nothing; commit re-validates the same bytes and applies the
plan in one transaction. The App Owner may import into any project and is the only one
who may create a project from a file; a project Manager may import into projects they
manage, with Owner-only actions skipped per row as warnings.
_Avoid_: upload (bare), sync, bulk edit.

## Project & task templates

**Suggested role**:
What a project or task template carries in place of a Task Owner: the role the
task's owner held when the template was saved — App Owner, Chairman, or their project
role (manager, member, viewer). Never a named person. When the template is used the
App Owner picks a person per role (on a new project that person is given the role);
a role left on automatic goes to its only active holder on the target project, and
otherwise the task starts unassigned. Templates saved before roles held a display
name; those still load (an App Owner or Chairman name maps to that role, anyone else
is pre-filled only while still assignable).
_Avoid_: suggested owner, default assignee.

## Portfolio & budget

**Budget**:
A project's planned, committed and actual/spent amounts in one explicit currency,
with variance derived from those amounts. It rolls up into exactly one entity (the
project's Primary entity) so a project shared across entities is never counted twice.
The current implementation stores planned amount only; committed, actual/spent and
variance are an accepted production requirement that remains to be implemented.
_Avoid_: silently blending currencies or presenting planned amount as actual spend.

**Primary entity**:
The single entity a project's Budget and portfolio figures count toward. For a
single-entity project it is that entity; for a project spanning several entities the
App Owner chooses it. Prevents double-counting across entities.
_Avoid_: main entity, owner entity.

**Portfolio roll-up**:
A per-entity summary of its projects: task health (open / overdue / critical counts)
and Budget totals shown per currency (never blended across currencies), with each
project counted once via its Primary entity.
_Avoid_: dashboard (that is the task board), report.

**Proposal**:
An Assessor-suggested board change, cited to its Evidence. A Proposal either **creates**
a Task (with suggested Task Owner, dates, dependencies, criticality, and project/entity
filing) or **updates** an existing one (a moved deadline, a cancellation, a reopening,
a status change). Either way it is a review item that changes nothing on its own — the
App Owner's approval, not the Assessor, applies it, and the App Owner may edit or refile
it first.
_Avoid_: suggestion, draft, recommendation (bare).

**Assessment run**:
One pass of the Assessor over Evidence that is **newer than the last run** (by the
record `date` in the catalog). A run never re-reads unchanged Evidence; it emits
Proposals (creates and updates) for the App Owner to review. Re-running is idempotent
— a Proposal is keyed to its Evidence, so the same record never yields a duplicate.
_Avoid_: scan, sync, batch (bare).
