from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA_VERSION = 13


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
    else:
        connection.commit()


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
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise RuntimeError("Database was created by a newer Astra version.")
    if version < 1:
        with transaction(connection):
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
            connection.execute("PRAGMA user_version = 1")
    if version < 2:
        with transaction(connection):
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
            connection.execute("PRAGMA user_version = 2")
    if version < 3:
        with transaction(connection):
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
            connection.execute("PRAGMA user_version = 3")
    if version < 4:
        with transaction(connection):
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
            connection.execute("PRAGMA user_version = 4")
    if version < 5:
        with transaction(connection):
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
            connection.execute("PRAGMA user_version = 5")
    if version < 6:
        with transaction(connection):
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
            connection.execute("PRAGMA user_version = 6")
    if version < 7:
        with transaction(connection):
            _execute_statements(connection,
                """
                ALTER TABLE projects ADD COLUMN budget_amount REAL;
                ALTER TABLE projects ADD COLUMN budget_currency TEXT NOT NULL DEFAULT 'PKR';
                ALTER TABLE projects ADD COLUMN primary_entity_id TEXT REFERENCES entities(id);
                """
            )
            connection.execute("PRAGMA user_version = 7")
    if version < 8:
        with transaction(connection):
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
            connection.execute("PRAGMA user_version = 8")
    if version < 9:
        with transaction(connection):
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
            connection.execute("PRAGMA user_version = 9")
    if version < 10:
        with transaction(connection):
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
            connection.execute("PRAGMA user_version = 10")
    if version < 11:
        with transaction(connection):
            _execute_statements(connection,
                """
                ALTER TABLE projects ADD COLUMN start_date TEXT;
                ALTER TABLE projects ADD COLUMN target_date TEXT;
                """
            )
            connection.execute("PRAGMA user_version = 11")
    if version < 12:
        with transaction(connection):
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
            connection.execute("PRAGMA user_version = 12")
    if version < 13:
        _migrate_v13(connection)


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

    The statements run one at a time inside a single BEGIN IMMEDIATE transaction and
    ``PRAGMA user_version = 13`` is the last statement of that same transaction.
    ``executescript()`` commits any open transaction before it starts, so the earlier
    form of this step ran in autocommit: a crash, kill or disk error between two of its
    statements left user_version at 12 with some columns already present, and every
    later ``connect()`` re-ran the step and died on "duplicate column name" (regression
    review MIGRATION-1). Now an interruption anywhere rolls the whole step back and the
    next start simply runs it again. Each statement is also guarded (table_info before an
    ALTER, IF NOT EXISTS on CREATE) so a database the earlier code left half-applied
    completes on the next start instead of needing hand SQL.
    """
    with transaction(connection):
        present = {row[1] for row in connection.execute("PRAGMA table_info(tasks)").fetchall()}
        for name, definition in V13_TASK_COLUMNS:
            if name not in present:
                connection.execute(f"ALTER TABLE tasks ADD COLUMN {name} {definition}")
        for statement in V13_STATEMENTS:
            connection.execute(statement)
        connection.execute("PRAGMA user_version = 13")
