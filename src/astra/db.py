from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager, suppress
from pathlib import Path


SCHEMA_VERSION = 18


class SchemaMigrationRefused(RuntimeError):
    """A migration found existing data it cannot convert safely. The step was rolled
    back untouched; the message says what to fix before starting Astra again."""


def app_home() -> Path:
    override = os.environ.get("ASTRA_HOME")
    if override:
        return Path(override).expanduser().resolve()
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "AstraProjectTracker"


def database_path() -> Path:
    return app_home() / "astra.sqlite3"


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target, timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 30000")
    migrate(connection)
    return connection


@contextmanager
def transaction(connection: sqlite3.Connection):
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
    except Exception:
        connection.rollback()
        raise
    # COMMIT itself can fail (a deferred foreign key, SQLITE_BUSY, disk full). Without
    # a rollback the connection would stay inside the transaction, holding the write
    # lock, and the next BEGIN on it would fail. The COMMIT error is the one raised.
    try:
        connection.commit()
    except Exception:
        with suppress(sqlite3.Error):
            connection.rollback()
        raise


def _execute_statements(connection: sqlite3.Connection, script: str) -> None:
    """Execute a SQL script without ``sqlite3.executescript`` transaction escape.

    ``executescript`` commits an open transaction before running its input. Migration
    callers instead hold ``BEGIN IMMEDIATE`` and feed each complete statement through
    ``execute`` so every schema change and its ``user_version`` update share one commit.
    ``sqlite3.complete_statement`` keeps semicolons inside quoted values or compound SQL
    from being treated as boundaries.
    """
    buffer: list[str] = []
    for character in script:
        buffer.append(character)
        if character == ";" and sqlite3.complete_statement("".join(buffer)):
            statement = "".join(buffer).strip()
            if statement:
                connection.execute(statement)
            buffer.clear()
    if "".join(buffer).strip():
        raise ValueError("Migration SQL ended with an incomplete statement.")


def migrate(connection: sqlite3.Connection) -> None:
    """Bring the database up to SCHEMA_VERSION by running MIGRATION_STEPS in order.

    Each pending step runs in its own BEGIN IMMEDIATE transaction together with the
    ``PRAGMA user_version`` bump to that step's version, and both commit or roll back
    together. Steps only apply statements; this loop is the only place that opens a
    migration transaction or writes user_version (ticket 39DNZT).
    """
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise RuntimeError("Database was created by a newer Astra version.")
    if version < 14:
        # Before any step commits: a database that v14 would refuse is refused now, at
        # the version it started at, so the refusal really changes nothing.
        _refuse_duplicate_submission_versions(connection)
    if version < 15:
        # Likewise for v15: duplicate pending Owner requests are refused at the
        # starting version, before any step commits.
        _refuse_duplicate_pending_requests(connection)
    if version < 16:
        # Likewise for v16: more than one owner is refused before any step commits.
        _refuse_multiple_owners(connection)
    for step_version, step in MIGRATION_STEPS:
        if version < step_version:
            with transaction(connection):
                step(connection)
                connection.execute(f"PRAGMA user_version = {step_version}")


def _migrate_v1(connection: sqlite3.Connection) -> None:
    # SQL text is kept byte-for-byte: SQLite stores it in sqlite_master.
    _execute_statements(connection,
        """
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    global_role TEXT NOT NULL CHECK(global_role IN ('owner','chairman','member')),
                    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                    created_at TEXT NOT NULL,
                    created_by TEXT REFERENCES users(id)
                );
                CREATE TABLE sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    csrf_token TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL REFERENCES users(id)
                );
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    manager_user_id TEXT REFERENCES users(id),
                    timezone TEXT NOT NULL DEFAULT 'Asia/Karachi',
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','on_hold','closed')),
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL REFERENCES users(id)
                );
                CREATE TABLE project_entities (
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    PRIMARY KEY(project_id, entity_id)
                );
                CREATE TABLE memberships (
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('manager','member','viewer')),
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL REFERENCES users(id),
                    PRIMARY KEY(project_id, user_id)
                );
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    parent_task_id TEXT REFERENCES tasks(id),
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    owner_user_id TEXT REFERENCES users(id),
                    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN (
                        'draft','assigned','in_progress','submitted','changes_requested',
                        'completed','on_hold','delayed','cancelled','abandoned','reopened')),
                    criticality TEXT CHECK(criticality IN ('critical','high','normal','low')),
                    start_date TEXT,
                    due_date TEXT,
                    progress INTEGER CHECK(progress IS NULL OR (progress BETWEEN 0 AND 100)),
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL REFERENCES users(id),
                    updated_at TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE task_dependencies (
                    predecessor_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    successor_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    dependency_type TEXT NOT NULL DEFAULT 'finish_to_start',
                    PRIMARY KEY(predecessor_task_id, successor_task_id),
                    CHECK(predecessor_task_id <> successor_task_id)
                );
                CREATE TABLE task_events (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    actor_user_id TEXT NOT NULL REFERENCES users(id),
                    occurred_at TEXT NOT NULL,
                    reason TEXT,
                    before_json TEXT,
                    after_json TEXT
                );
                CREATE INDEX idx_tasks_project ON tasks(project_id);
                CREATE INDEX idx_tasks_owner ON tasks(owner_user_id);
                CREATE INDEX idx_tasks_due ON tasks(due_date);
                CREATE INDEX idx_events_task ON task_events(task_id, occurred_at);
                """
    )


def _migrate_v2(connection: sqlite3.Connection) -> None:
    _execute_statements(connection,
        """
                CREATE TABLE login_attempts (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    ip TEXT NOT NULL DEFAULT '',
                    attempted_at TEXT NOT NULL,
                    success INTEGER NOT NULL CHECK(success IN (0,1))
                );
                CREATE INDEX idx_login_attempts_email ON login_attempts(email, attempted_at);
                """
    )


def _migrate_v3(connection: sqlite3.Connection) -> None:
    _execute_statements(connection,
        """
                CREATE TABLE task_submissions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL,
                    submitted_by TEXT NOT NULL REFERENCES users(id),
                    submitted_at TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'submitted'
                        CHECK(status IN ('submitted','accepted','changes_requested')),
                    decided_by TEXT REFERENCES users(id),
                    decided_at TEXT,
                    decision_note TEXT,
                    checklist TEXT
                );
                CREATE TABLE task_reviewers (
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    role TEXT NOT NULL CHECK(role IN ('reviewer','approver','collaborator')),
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL REFERENCES users(id),
                    PRIMARY KEY(task_id, user_id, role)
                );
                CREATE TABLE task_checkpoints (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    checkpoint_date TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    owner_user_id TEXT REFERENCES users(id),
                    created_by TEXT NOT NULL REFERENCES users(id),
                    created_at TEXT NOT NULL,
                    resolved INTEGER NOT NULL DEFAULT 0 CHECK(resolved IN (0,1))
                );
                CREATE TABLE project_events (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    actor_user_id TEXT NOT NULL REFERENCES users(id),
                    occurred_at TEXT NOT NULL,
                    reason TEXT,
                    detail_json TEXT
                );
                ALTER TABLE tasks ADD COLUMN accepted_submission_id TEXT REFERENCES task_submissions(id);
                ALTER TABLE projects ADD COLUMN closed_at TEXT;
                ALTER TABLE projects ADD COLUMN closed_by TEXT REFERENCES users(id);
                ALTER TABLE projects ADD COLUMN closure_note TEXT;
                ALTER TABLE projects ADD COLUMN closure_is_exceptional INTEGER NOT NULL DEFAULT 0;
                CREATE INDEX idx_submissions_task ON task_submissions(task_id, version);
                CREATE INDEX idx_reviewers_task ON task_reviewers(task_id);
                CREATE INDEX idx_checkpoints_task ON task_checkpoints(task_id);
                CREATE INDEX idx_project_events ON project_events(project_id, occurred_at);
                """
    )


def _migrate_v4(connection: sqlite3.Connection) -> None:
    _execute_statements(connection,
        """
                CREATE TABLE notifications (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    event_id TEXT NOT NULL,
                    task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    read_at TEXT
                );
                CREATE UNIQUE INDEX idx_notifications_recipient_event ON notifications(user_id, event_id);
                CREATE INDEX idx_notifications_user ON notifications(user_id, created_at);
                """
    )


def _migrate_v5(connection: sqlite3.Connection) -> None:
    _execute_statements(connection,
        """
                ALTER TABLE tasks ADD COLUMN baseline_start_date TEXT;
                ALTER TABLE tasks ADD COLUMN baseline_due_date TEXT;
                CREATE TABLE task_schedule_proposals (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    start_date TEXT,
                    due_date TEXT,
                    reason TEXT NOT NULL,
                    proposed_by TEXT NOT NULL REFERENCES users(id),
                    proposed_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','approved','rejected')),
                    decided_by TEXT REFERENCES users(id),
                    decided_at TEXT,
                    decision_reason TEXT
                );
                CREATE INDEX idx_schedule_proposals_task ON task_schedule_proposals(task_id, status);
                """
    )


def _migrate_v6(connection: sqlite3.Connection) -> None:
    _execute_statements(connection,
        """
                ALTER TABLE projects ADD COLUMN working_days TEXT NOT NULL DEFAULT '0123456';
                CREATE TABLE project_holidays (
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    holiday_date TEXT NOT NULL,
                    label TEXT NOT NULL DEFAULT '',
                    created_by TEXT NOT NULL REFERENCES users(id),
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(project_id, holiday_date)
                );
                """
    )


def _migrate_v7(connection: sqlite3.Connection) -> None:
    _execute_statements(connection,
        """
                ALTER TABLE projects ADD COLUMN budget_amount REAL;
                ALTER TABLE projects ADD COLUMN budget_currency TEXT NOT NULL DEFAULT 'PKR';
                ALTER TABLE projects ADD COLUMN primary_entity_id TEXT REFERENCES entities(id);
                """
    )


def _migrate_v8(connection: sqlite3.Connection) -> None:
    _execute_statements(connection,
        """
                CREATE TABLE task_attachments (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    path TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    added_by TEXT NOT NULL REFERENCES users(id),
                    added_at TEXT NOT NULL
                );
                CREATE INDEX idx_attachments_task ON task_attachments(task_id, added_at);
                """
    )


def _migrate_v9(connection: sqlite3.Connection) -> None:
    _execute_statements(connection,
        """
                CREATE TABLE templates (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL CHECK(kind IN ('project','task')),
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    body_json TEXT NOT NULL,
                    created_by TEXT NOT NULL REFERENCES users(id),
                    created_at TEXT NOT NULL
                );
                CREATE INDEX idx_templates_kind ON templates(kind, name);
                """
    )


def _migrate_v10(connection: sqlite3.Connection) -> None:
    _execute_statements(connection,
        """
                CREATE TABLE final_results (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    source_type TEXT NOT NULL CHECK(source_type IN ('submission','attachment')),
                    submission_id TEXT REFERENCES task_submissions(id) ON DELETE CASCADE,
                    attachment_id TEXT REFERENCES task_attachments(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    marked_by TEXT NOT NULL REFERENCES users(id),
                    marked_at TEXT NOT NULL,
                    UNIQUE(submission_id),
                    UNIQUE(attachment_id)
                );
                CREATE INDEX idx_final_results_task ON final_results(task_id);
                CREATE INDEX idx_final_results_marked ON final_results(marked_at);
                """
    )


def _migrate_v11(connection: sqlite3.Connection) -> None:
    _execute_statements(connection,
        """
                ALTER TABLE projects ADD COLUMN start_date TEXT;
                ALTER TABLE projects ADD COLUMN target_date TEXT;
                """
    )


def _migrate_v12(connection: sqlite3.Connection) -> None:
    _execute_statements(connection,
        """
                CREATE TABLE owner_action_requests (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
                    action TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    reason TEXT NOT NULL DEFAULT '',
                    requested_by TEXT NOT NULL REFERENCES users(id),
                    requested_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','approved','rejected','cancelled')),
                    decided_by TEXT REFERENCES users(id),
                    decided_at TEXT,
                    decision_reason TEXT
                );
                CREATE INDEX idx_owner_action_requests_status
                    ON owner_action_requests(status, requested_at);
                CREATE INDEX idx_owner_action_requests_requester
                    ON owner_action_requests(requested_by, requested_at);
                """
    )


# Columns the v13 step adds to tasks, in order (name, definition).
V13_TASK_COLUMNS = (
    ("import_key", "TEXT"),
    ("is_milestone", "INTEGER NOT NULL DEFAULT 0 CHECK(is_milestone IN (0,1))"),
    ("next_action_note", "TEXT"),
    ("import_extras", "TEXT"),
)

V13_STATEMENTS = (
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_import_key
           ON tasks(project_id, import_key) WHERE import_key IS NOT NULL""",
    """CREATE TABLE IF NOT EXISTS imports (
           id TEXT PRIMARY KEY,
           project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
           actor_user_id TEXT NOT NULL REFERENCES users(id),
           filename TEXT NOT NULL,
           sha256 TEXT NOT NULL,
           created_at TEXT NOT NULL,
           summary_json TEXT NOT NULL,
           report_csv TEXT NOT NULL
       )""",
    "CREATE INDEX IF NOT EXISTS idx_imports_project ON imports(project_id, created_at)",
    """CREATE TABLE IF NOT EXISTS import_template_config (
           id INTEGER PRIMARY KEY CHECK(id = 1),
           version INTEGER NOT NULL,
           config_json TEXT NOT NULL,
           updated_at TEXT NOT NULL,
           updated_by TEXT REFERENCES users(id)
       )""",
)


def _migrate_v13(connection: sqlite3.Connection) -> None:
    """v12 -> v13: the Excel import feature's task columns, ``imports`` and
    ``import_template_config``.

    The statements run one at a time inside the single BEGIN IMMEDIATE transaction that
    ``migrate()`` opens for this step, and ``PRAGMA user_version = 13`` is the last
    statement of that same transaction.
    ``executescript()`` commits any open transaction before it starts, so the earlier
    form of this step ran in autocommit: a crash, kill or disk error between two of its
    statements left user_version at 12 with some columns already present, and every
    later ``connect()`` re-ran the step and died on "duplicate column name" (regression
    review MIGRATION-1). Now an interruption anywhere rolls the whole step back and the
    next start simply runs it again. Each statement is also guarded (table_info before an
    ALTER, IF NOT EXISTS on CREATE) so a database the earlier code left half-applied
    completes on the next start instead of needing hand SQL.
    """
    present = {row[1] for row in connection.execute("PRAGMA table_info(tasks)").fetchall()}
    for name, definition in V13_TASK_COLUMNS:
        if name not in present:
            connection.execute(f"ALTER TABLE tasks ADD COLUMN {name} {definition}")
    for statement in V13_STATEMENTS:
        connection.execute(statement)


V14_SUBMISSION_VERSION_INDEX = "idx_submissions_task_version"

V14_DUPLICATE_SUBMISSION_VERSIONS = """
    SELECT task_id, version FROM task_submissions
    GROUP BY task_id, version HAVING COUNT(*) > 1 ORDER BY task_id, version
"""


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _refuse_duplicate_submission_versions(connection: sqlite3.Connection) -> None:
    """Raise SchemaMigrationRefused if task_submissions (present from v3) holds more
    than one row for a (task_id, version). Lists submission ids and statuses only:
    notes and titles are user content and stay out of logs."""
    if not _table_exists(connection, "task_submissions"):
        return
    pairs = connection.execute(V14_DUPLICATE_SUBMISSION_VERSIONS).fetchall()
    if not pairs:
        return
    has_final_results = _table_exists(connection, "final_results")
    described = []
    for task_id, version in pairs[:10]:
        rows = connection.execute(
            "SELECT id, status FROM task_submissions WHERE task_id=? AND version=? ORDER BY submitted_at, id",
            (task_id, version),
        ).fetchall()
        parts = []
        for submission_id, status in rows:
            references = []
            if connection.execute(
                "SELECT 1 FROM tasks WHERE accepted_submission_id=?", (submission_id,)
            ).fetchone():
                references.append("tasks.accepted_submission_id")
            if has_final_results and connection.execute(
                "SELECT 1 FROM final_results WHERE submission_id=?", (submission_id,)
            ).fetchone():
                references.append("final_results")
            referenced = f", referenced by {' and '.join(references)}" if references else ""
            parts.append(f"submission {submission_id} ({status}{referenced})")
        described.append(f"task {task_id} version {version}: {', '.join(parts)}")
    more = f"; and {len(pairs) - 10} more" if len(pairs) > 10 else ""
    raise SchemaMigrationRefused(
        "Astra cannot upgrade this database to schema 14: task_submissions has "
        f"{len(pairs)} task version(s) with more than one submission, left by an earlier "
        "concurrent-submission defect. Nothing was changed. Affected: "
        f"{'; '.join(described)}{more}. To resolve: back up the database; for each task "
        "version keep the accepted row (the one tasks.accepted_submission_id or "
        "final_results refers to) and delete the others or renumber them to an unused "
        "version; run any DELETE with PRAGMA foreign_keys=ON so a referenced row cannot "
        "be removed; then start Astra again."
    )


def _migrate_v14(connection: sqlite3.Connection) -> None:
    """v13 -> v14: one submission per (task_id, version) (ticket 03G8EH).

    Before 03G8EH, two concurrent ``submit_task`` calls could both read the same
    ``MAX(version)`` and insert two rows at one version. The service now allocates the
    version under ``BEGIN IMMEDIATE``; this unique index makes the database refuse a
    duplicate too. A database that already holds duplicates is refused rather than
    repaired: which of two submissions is the real one is an Owner decision, so nothing
    is deleted or renumbered here. ``migrate()`` runs the same probe before its first
    step, so a database starting below v13 is refused at its starting version instead of
    being left at v13; the probe is repeated here, under the step's write lock, in case
    a duplicate was written in between. Either way nothing is committed.
    """
    _refuse_duplicate_submission_versions(connection)
    connection.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS {V14_SUBMISSION_VERSION_INDEX}"
        " ON task_submissions(task_id, version)"
    )


V15_PENDING_INTENT_INDEX = "idx_owner_action_requests_pending_intent"
V15_PENDING_LOOKUP_INDEX = "idx_owner_action_requests_pending_scope"

# How expected_revision is derived from a payload, in the backfill and in every INSERT.
# A payload that is not valid JSON yields NULL instead of failing the whole step.
V15_EXPECTED_REVISION_SQL = (
    "CASE WHEN json_valid({payload}) THEN json_extract({payload}, '$.expected_revision') END"
)

# Pending requests that are equivalent under the service's dedupe rule: same scope,
# action, payload text, reason and requester. GROUP BY treats NULL task_id values as
# equal, so project-level requests are grouped too. Needs no v15 column.
V15_DUPLICATE_PENDING_REQUESTS = """
    SELECT project_id, task_id, action, payload_json, reason, requested_by
    FROM owner_action_requests WHERE status='pending'
    GROUP BY project_id, task_id, action, payload_json, reason, requested_by
    HAVING COUNT(*) > 1 ORDER BY project_id, task_id, action
"""


def owner_request_intent_key(
    project_id: str, task_id: str | None, action: str, payload_json: str, reason: str, requested_by: str
) -> str:
    """The deterministic key two requests share exactly when the service treats the second
    as a retry of the first (ticket WNXSDA).

    It hashes the stored ``payload_json`` text as-is, not a re-serialised payload, so it
    matches precisely the ``payload_json=?`` comparison it replaces. ``requested_by`` and
    ``reason`` are part of it: a second Manager's equivalent request stays a row of its
    own, and approval resolves both through the intent match in the service.
    """
    material = json.dumps(
        [project_id, task_id, action, payload_json, reason, requested_by],
        ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _refuse_duplicate_pending_requests(connection: sqlite3.Connection) -> None:
    """Raise SchemaMigrationRefused if owner_action_requests (present from v12) holds more
    than one pending row with the same intent. Lists request ids, scope and action only:
    reasons and payloads are user content and stay out of logs."""
    if not _table_exists(connection, "owner_action_requests"):
        return
    groups = connection.execute(V15_DUPLICATE_PENDING_REQUESTS).fetchall()
    if not groups:
        return
    described = []
    for project_id, task_id, action, payload_json, reason, requested_by in groups[:10]:
        ids = [row[0] for row in connection.execute(
            """SELECT id FROM owner_action_requests
               WHERE status='pending' AND project_id=? AND task_id IS ? AND action=?
                 AND payload_json=? AND reason=? AND requested_by=?
               ORDER BY requested_at, id""",
            (project_id, task_id, action, payload_json, reason, requested_by),
        ).fetchall()]
        scope = f"task {task_id}" if task_id is not None else f"project {project_id}"
        described.append(f"{scope} {action}: {', '.join(f'request {i}' for i in ids)}")
    more = f"; and {len(groups) - 10} more" if len(groups) > 10 else ""
    raise SchemaMigrationRefused(
        "Astra cannot upgrade this database to schema 15: owner_action_requests has "
        f"{len(groups)} group(s) of identical pending Owner requests (same item, action, "
        "details, reason and requester). Nothing was changed. Affected: "
        f"{'; '.join(described)}{more}. To resolve: back up the database; in each group "
        "keep the earliest request pending and mark the others cancelled "
        "(UPDATE owner_action_requests SET status='cancelled' WHERE id=...); then start "
        "Astra again."
    )


def _migrate_v15(connection: sqlite3.Connection) -> None:
    """v14 -> v15: an intent key for pending Owner requests (ticket WNXSDA).

    Adds ``intent_key`` (see owner_request_intent_key) with a UNIQUE index over pending
    rows, so the database itself refuses a second identical pending request; until now
    only the service's BEGIN IMMEDIATE lookup-then-insert prevented it. Adds
    ``expected_revision``, copied from the payload by ``json_extract`` and declared
    without a type so no affinity converts it, and a partial index for the pending
    lookups the service makes by scope, action and revision. Existing rows are
    backfilled. A database already holding identical pending requests is refused, as in
    v14, before anything changes; the probe runs again here under the step's write lock.
    """
    _refuse_duplicate_pending_requests(connection)
    present = {
        row[1] for row in connection.execute("PRAGMA table_info(owner_action_requests)").fetchall()
    }
    if "intent_key" not in present:
        connection.execute("ALTER TABLE owner_action_requests ADD COLUMN intent_key TEXT")
    if "expected_revision" not in present:
        connection.execute("ALTER TABLE owner_action_requests ADD COLUMN expected_revision")
    rows = connection.execute(
        "SELECT id,project_id,task_id,action,payload_json,reason,requested_by FROM owner_action_requests"
    ).fetchall()
    for request_id, project_id, task_id, action, payload_json, reason, requested_by in rows:
        connection.execute(
            "UPDATE owner_action_requests SET intent_key=? WHERE id=?",
            (owner_request_intent_key(project_id, task_id, action, payload_json, reason, requested_by),
             request_id),
        )
    connection.execute(
        "UPDATE owner_action_requests SET expected_revision=" + V15_EXPECTED_REVISION_SQL.format(payload="payload_json")
    )
    connection.execute(
        f"CREATE INDEX IF NOT EXISTS {V15_PENDING_LOOKUP_INDEX}"
        " ON owner_action_requests(project_id, task_id, action, expected_revision)"
        " WHERE status='pending'"
    )
    connection.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS {V15_PENDING_INTENT_INDEX}"
        " ON owner_action_requests(intent_key) WHERE status='pending'"
    )


V16_PRIMARY_OWNER_INDEX = "idx_users_primary_owner"


def _refuse_multiple_owners(connection: sqlite3.Connection) -> None:
    """Raise SchemaMigrationRefused if users holds more than one owner: v16 cannot tell
    which of them is the primary owner. Lists user ids only (no emails or names). No
    owner at all is fine: a fresh database migrates before its owner is created."""
    if not _table_exists(connection, "users"):
        return
    ids = [row[0] for row in connection.execute(
        "SELECT id FROM users WHERE global_role='owner' ORDER BY created_at, id").fetchall()]
    if len(ids) < 2:
        return
    raise SchemaMigrationRefused(
        f"Astra cannot upgrade this database to schema 16: it has {len(ids)} owner accounts and "
        "schema 16 needs exactly one primary owner. Nothing was changed. Owner user ids: "
        f"{', '.join(ids)}. To resolve: back up the database; keep the primary owner and set the "
        "others to their earlier role (UPDATE users SET global_role='member' WHERE id=...); then "
        "start Astra again and make them secondary owners from the People screen."
    )


def _migrate_v16(connection: sqlite3.Connection) -> None:
    """v15 -> v16: primary and secondary owners (ticket GTEYTG).

    Every owner keeps global_role='owner'; ``is_primary_owner`` marks the one who alone
    may grant or remove owner access. The CHECK refuses a primary who is not an owner
    and the partial unique index refuses a second primary. ``user_events`` records who
    granted, removed or tried to change owner access. The single existing owner, if any,
    becomes the primary; 2+ owners are refused before anything changes (probe repeated
    here under the step's write lock). The unique index is created last.
    """
    _refuse_multiple_owners(connection)
    _execute_statements(connection, f"""
        ALTER TABLE users ADD COLUMN is_primary_owner INTEGER NOT NULL DEFAULT 0
            CHECK(is_primary_owner IN (0,1) AND (is_primary_owner=0 OR global_role='owner'));
        CREATE TABLE user_events (
            id TEXT PRIMARY KEY,
            target_user_id TEXT NOT NULL REFERENCES users(id),
            event_type TEXT NOT NULL,
            actor_user_id TEXT NOT NULL REFERENCES users(id),
            occurred_at TEXT NOT NULL,
            reason TEXT,
            detail_json TEXT
        );
        CREATE INDEX idx_user_events_target ON user_events(target_user_id, occurred_at);
        UPDATE users SET is_primary_owner=1 WHERE global_role='owner';
        CREATE UNIQUE INDEX {V16_PRIMARY_OWNER_INDEX} ON users(is_primary_owner) WHERE is_primary_owner=1;
    """)


V17_NOTIFICATION_ACTOR_INDEX = "idx_notifications_actor"


def _migrate_v17(connection: sqlite3.Connection) -> None:
    """v16 -> v17: who caused each notification (ticket KBWY86).

    ``actor_user_id`` lets the service cap blocked-attempt notices per recipient and actor
    in a rolling window. It is nullable and not backfilled: older notices keep NULL and
    fall outside any window.
    """
    _execute_statements(connection, f"""
        ALTER TABLE notifications ADD COLUMN actor_user_id TEXT REFERENCES users(id);
        CREATE INDEX {V17_NOTIFICATION_ACTOR_INDEX} ON notifications(user_id, actor_user_id, created_at);
    """)


V18_BOARD_RANK_INDEX = "idx_tasks_board_rank"


def _migrate_v18(connection: sqlite3.Connection) -> None:
    """v17 -> v18: a saved board order (ticket JN1QYG).

    ``board_rank`` orders cards inside a board column; dragging a card within a column
    rewrites the ranks of that column. NULL means "not ranked yet": those cards follow the
    ranked ones in the list order. Not backfilled.
    """
    _execute_statements(connection, f"""
        ALTER TABLE tasks ADD COLUMN board_rank REAL;
        CREATE INDEX {V18_BOARD_RANK_INDEX} ON tasks(project_id, board_rank);
    """)


# The ordered schema history: (version, step). migrate() runs every step whose version
# is above the database's user_version, each in its own transaction with its bump.
# Append new steps here and raise SCHEMA_VERSION; never edit or reorder a shipped step.
MIGRATION_STEPS = (
    (1, _migrate_v1),
    (2, _migrate_v2),
    (3, _migrate_v3),
    (4, _migrate_v4),
    (5, _migrate_v5),
    (6, _migrate_v6),
    (7, _migrate_v7),
    (8, _migrate_v8),
    (9, _migrate_v9),
    (10, _migrate_v10),
    (11, _migrate_v11),
    (12, _migrate_v12),
    (13, _migrate_v13),
    (14, _migrate_v14),
    (15, _migrate_v15),
    (16, _migrate_v16),
    (17, _migrate_v17),
    (18, _migrate_v18),
)
