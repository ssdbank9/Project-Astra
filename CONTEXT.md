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
An organizational role with org-wide project visibility comparable to the App
Owner but no access to private sources, and no power to grant access or perform
exceptional closure.

**Collaborator / Reviewer / Approver**:
Supporting people on a task, tracked separately from its Task Owner. An Approver may
accept a submission; a Reviewer may request changes; a Collaborator contributes to
the work. A person in these roles is never the accountable party by virtue of it.
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

## Portfolio & budget

**Budget**:
A project's planned budget — one amount in one currency. It rolls up into exactly one
entity (the project's Primary entity) so a project shared across entities is never
counted twice. Planned only; actual/spent is not tracked yet.
_Avoid_: cost, spend, actual (those are a separate future concept).

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
