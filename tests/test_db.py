import json
import os
import sqlite3
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from astra import db
from astra.service import AstraService


DENY_IMPORTS_TABLE = "imports"


def deny_create_table(name):
    """An authorizer that refuses CREATE TABLE <name>: a failure injected mid-migration."""
    def authorizer(action, arg1, arg2, db_name, trigger):
        if action == sqlite3.SQLITE_CREATE_TABLE and arg1 == name:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    return authorizer


def deny_create_index(name):
    """An authorizer that refuses CREATE INDEX <name>."""
    def authorizer(action, arg1, arg2, db_name, trigger):
        if action == sqlite3.SQLITE_CREATE_INDEX and arg1 == name:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    return authorizer


def new_task_columns(connection):
    names = [row[1] for row in connection.execute("PRAGMA table_info(tasks)").fetchall()]
    return [name for name in names if name in dict(db.V13_TASK_COLUMNS)]


def objects(connection):
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE name IN "
        "('imports','import_template_config','idx_tasks_import_key','idx_imports_project') ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def application_schema_objects(connection):
    rows = connection.execute(
        "SELECT type,name FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    return [(row[0], row[1]) for row in rows]


def table_columns(connection, table):
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]


def schema_signature(connection):
    rows = connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    return [tuple(row) for row in rows]


def full_catalog(connection):
    """Every sqlite_master row, SQLite's own automatic indexes included."""
    rows = connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
    ).fetchall()
    return [tuple(row) for row in rows]


LEGACY_STEPS = range(1, 13)   # v1-v12: the steps written inline in db.migrate()


class InjectedFault(Exception):
    """Raised by a test to abort a migration step part-way through."""


def deny_version_bump(version):
    """An authorizer that refuses ``PRAGMA user_version = <version>``.

    Every legacy step ends with that statement, so this fails step ``version`` after
    all of its other statements have run, and leaves every earlier step committed.
    """
    def authorizer(action, arg1, arg2, db_name, trigger):
        if action == sqlite3.SQLITE_PRAGMA and arg1 == "user_version" and arg2 == str(version):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    return authorizer


SCHEMA_WRITE_ACTIONS = frozenset({
    sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_ALTER_TABLE,
    sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
})


@contextmanager
def stopped_before_step(connection, version):
    """Let steps 1..version-1 commit on ``connection``, then refuse every write, so a
    migration stops at version-1 without any statement of step ``version`` running.

    Building the starting database this way does not rely on the atomicity under test,
    and it does not assume where in step version-1 its ``PRAGMA user_version`` bump sits
    or how that step commits. A trace callback watches for the bump and then for the
    next ``BEGIN IMMEDIATE``, which opens step ``version``; only from then on does the
    authorizer refuse writes. The BEGIN is seen through the trace callback, which fires
    on every executed statement, because sqlite3's statement cache reuses the identical
    ``BEGIN IMMEDIATE`` of every step without asking the authorizer again.
    """
    previous_bump_seen = False
    step_started = version == 1

    def trace(statement):
        nonlocal previous_bump_seen, step_started
        if statement == f"PRAGMA user_version = {version - 1}":
            previous_bump_seen = True
        elif previous_bump_seen and statement == "BEGIN IMMEDIATE":
            step_started = True

    def authorizer(action, arg1, arg2, db_name, trigger):
        if step_started and action in SCHEMA_WRITE_ACTIONS:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    connection.set_trace_callback(trace)
    connection.set_authorizer(authorizer)
    try:
        yield
    finally:
        connection.set_authorizer(None)
        connection.set_trace_callback(None)


def legacy_user(connection, user_id, role="member"):
    """A user row as a pre-v16 schema stores it (no is_primary_owner column), returned as
    the actor dict the service expects. Service calls that read users.is_primary_owner
    cannot run before v16, so old-schema fixtures write users directly (GTEYTG)."""
    user = {"id": user_id, "email": f"secret-{user_id}@example.org", "display_name": f"Private {user_id}",
            "global_role": role, "active": 1, "created_at": "2026-01-01T00:00:00Z", "is_primary_owner": 0}
    connection.execute(
        "INSERT INTO users(id,email,display_name,password_hash,global_role,created_at) VALUES(?,?,?,?,?,?)",
        (user_id, user["email"], user["display_name"], "x", role, user["created_at"]),
    )
    return user


def open_without_migrating(path):
    """``db.connect(path)`` with its exact settings (row_factory, foreign_keys, WAL,
    busy_timeout) but without the ``migrate()`` call, so a test can drive migrate()."""
    with patch.object(db, "migrate", lambda connection: None):
        return db.connect(path)


def first_statement_then_fail(connection, script):
    """Stand-in for ``db._execute_statements``: run the script's first statement, then fail."""
    buffer = ""
    for character in script:
        buffer += character
        if character == ";" and sqlite3.complete_statement(buffer):
            break
    connection.execute(buffer.strip())
    raise InjectedFault("injected after the first statement of the step")


class MigrationTests(unittest.TestCase):
    """Regression review MIGRATION-1 (2026-09-22/23).

    ``executescript`` commits the surrounding ``BEGIN IMMEDIATE`` before it runs. The
    original v1-v12 path could therefore persist only the statements before a failure;
    v13 had already been corrected after a reproduced partial-column failure. These
    tests enforce the same atomic and retry-safe contract across every schema version.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "astra.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def raw(self):
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def interrupted_at_v13(self):
        """A database whose v12 -> v13 step failed after the four ALTERs and the index."""
        connection = self.raw()
        connection.set_authorizer(deny_create_table(DENY_IMPORTS_TABLE))
        with self.assertRaises(sqlite3.DatabaseError):
            db.migrate(connection)
        connection.set_authorizer(None)
        return connection

    def test_user_version_pragma_is_transactional(self):
        connection = self.raw()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("PRAGMA user_version = 99")
        connection.rollback()
        self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 0)
        connection.close()

    def test_migration_step_registry_is_contiguous_from_one_to_schema_version(self):
        """Ticket 39DNZT: migrate() runs one ordered registry. A gap, a duplicate or a
        step out of order would silently skip or repeat a schema change."""
        versions = [version for version, _ in db.MIGRATION_STEPS]
        self.assertEqual(versions, list(range(1, db.SCHEMA_VERSION + 1)))
        for version, step in db.MIGRATION_STEPS:
            self.assertTrue(callable(step), f"step for v{version} is not callable")

    def test_migration_steps_leave_transaction_and_user_version_to_migrate(self):
        """Ticket 39DNZT: a step only applies statements. migrate() owns BEGIN IMMEDIATE,
        the user_version bump and the commit, so a step that opened its own transaction
        or bumped the version would break here. Applying the steps by hand this way
        yields the same catalog as db.connect()."""
        connection = self.raw()
        try:
            for version, step in db.MIGRATION_STEPS:
                connection.execute("BEGIN IMMEDIATE")
                step(connection)
                self.assertTrue(connection.in_transaction, f"v{version} step ended the transaction")
                self.assertEqual(
                    connection.execute("PRAGMA user_version").fetchone()[0],
                    version - 1,
                    f"v{version} step changed user_version itself",
                )
                connection.execute(f"PRAGMA user_version = {version}")
                connection.commit()
            fresh = db.connect(Path(self.temp.name) / "fresh.sqlite3")
            try:
                self.assertEqual(schema_signature(connection), schema_signature(fresh))
            finally:
                fresh.close()
        finally:
            connection.close()

    def test_atomic_statement_runner_handles_quoted_semicolons_and_rejects_incomplete_sql(self):
        connection = self.raw()
        try:
            with db.transaction(connection):
                db._execute_statements(
                    connection,
                    "CREATE TABLE parser_probe(value TEXT);"
                    "INSERT INTO parser_probe(value) VALUES ('inside;value');",
                )
            self.assertEqual(
                connection.execute("SELECT value FROM parser_probe").fetchone()[0],
                "inside;value",
            )

            with self.assertRaisesRegex(ValueError, "incomplete"):
                with db.transaction(connection):
                    db._execute_statements(connection, "CREATE TABLE incomplete(")
            names = {name for _, name in application_schema_objects(connection)}
            self.assertNotIn("incomplete", names)
        finally:
            connection.close()

    def test_failed_commit_rolls_back_and_leaves_the_connection_reusable(self):
        """MIG-7: a COMMIT that fails must not leave the connection in a transaction.

        A deferred foreign key is only checked at COMMIT, so violating one inside the
        block makes ``connection.commit()`` itself raise. Before the fix the open
        transaction (and its write lock) survived, and the next ``transaction()`` on
        the same connection failed with "cannot start a transaction within a
        transaction".
        """
        connection = self.raw()
        try:
            connection.execute("CREATE TABLE commit_parent(id INTEGER PRIMARY KEY)")
            connection.execute(
                "CREATE TABLE commit_child(id INTEGER PRIMARY KEY, parent_id INTEGER "
                "REFERENCES commit_parent(id) DEFERRABLE INITIALLY DEFERRED)"
            )
            with self.assertRaises(sqlite3.IntegrityError):
                with db.transaction(connection):
                    connection.execute(
                        "INSERT INTO commit_child(id, parent_id) VALUES (1, 404)"
                    )
            self.assertFalse(connection.in_transaction)
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM commit_child").fetchone()[0], 0
            )

            with db.transaction(connection):
                connection.execute("INSERT INTO commit_parent(id) VALUES (404)")
                connection.execute("INSERT INTO commit_child(id, parent_id) VALUES (1, 404)")
            self.assertFalse(connection.in_transaction)
            self.assertEqual(
                connection.execute("SELECT parent_id FROM commit_child").fetchone()[0], 404
            )
        finally:
            connection.close()

    def test_failure_midway_through_initial_schema_rolls_back_every_object_and_retries(self):
        connection = self.raw()
        try:
            connection.set_authorizer(deny_create_table("tasks"))
            with self.assertRaises(sqlite3.DatabaseError):
                db.migrate(connection)
            connection.set_authorizer(None)

            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(
                application_schema_objects(connection),
                [],
                "a failed initial migration must not leave its earlier tables or indexes behind",
            )
            self.assertFalse(connection.in_transaction)
        finally:
            connection.close()

        reopened = db.connect(self.path)
        self.assertEqual(reopened.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
        self.assertEqual(reopened.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        reopened.close()

    def test_failure_after_legacy_alters_rolls_back_to_v4_then_matches_fresh_schema(self):
        connection = self.raw()
        try:
            connection.set_authorizer(deny_create_table("task_schedule_proposals"))
            with self.assertRaises(sqlite3.DatabaseError):
                db.migrate(connection)
            connection.set_authorizer(None)

            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 4)
            self.assertNotIn("baseline_start_date", table_columns(connection, "tasks"))
            self.assertNotIn("baseline_due_date", table_columns(connection, "tasks"))
            self.assertNotIn(
                ("table", "task_schedule_proposals"), application_schema_objects(connection)
            )
            db.migrate(connection)
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)

            fresh_path = Path(self.temp.name) / "fresh.sqlite3"
            fresh = db.connect(fresh_path)
            try:
                self.assertEqual(schema_signature(connection), schema_signature(fresh))
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            finally:
                fresh.close()
        finally:
            connection.close()

    def test_failure_after_v12_table_creation_rolls_back_table_and_index_then_retries(self):
        connection = self.raw()
        try:
            connection.set_authorizer(deny_create_table("owner_action_requests"))
            with self.assertRaises(sqlite3.DatabaseError):
                db.migrate(connection)
            connection.set_authorizer(None)
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 11)

            connection.set_authorizer(deny_create_index("idx_owner_action_requests_status"))
            with self.assertRaises(sqlite3.DatabaseError):
                db.migrate(connection)
            connection.set_authorizer(None)
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 11)
            names = {name for _, name in application_schema_objects(connection)}
            self.assertNotIn("owner_action_requests", names)
            self.assertNotIn("idx_owner_action_requests_status", names)
            self.assertNotIn("idx_owner_action_requests_requester", names)

            db.migrate(connection)
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
            names = {name for _, name in application_schema_objects(connection)}
            self.assertIn("owner_action_requests", names)
            self.assertIn("idx_owner_action_requests_status", names)
            self.assertIn("idx_owner_action_requests_requester", names)
        finally:
            connection.close()

    def test_every_legacy_step_rolls_back_a_mid_step_failure_and_retries_to_the_fresh_schema(self):
        """67T315: each of v1-v12 is one transaction together with its user_version bump.

        For every step N, from a database at N-1: fail after the step's first statement,
        and separately fail at its ``PRAGMA user_version = N``, after all of its other
        statements. Either way user_version must still be N-1 and the catalog must be
        exactly as before; re-opening through db.connect() (WAL, as in production) must
        migrate to SCHEMA_VERSION with a catalog equal to a fresh database.
        Putting ``executescript()`` back into a step, or moving its bump outside the
        ``transaction()`` block, commits part of the step and fails here.
        """
        fresh = db.connect(Path(self.temp.name) / "fresh.sqlite3")
        try:
            fresh_catalog = full_catalog(fresh)
        finally:
            fresh.close()

        def inject_after_first_statement(connection, version):
            with patch.object(db, "_execute_statements", first_statement_then_fail):
                db.migrate(connection)

        def inject_at_version_bump(connection, version):
            connection.set_authorizer(deny_version_bump(version))
            try:
                db.migrate(connection)
            finally:
                connection.set_authorizer(None)

        faults = {
            "after the first statement": (inject_after_first_statement, InjectedFault),
            "at the user_version bump": (inject_at_version_bump, sqlite3.DatabaseError),
        }
        for version in LEGACY_STEPS:
            for fault_name, (inject, expected) in faults.items():
                with self.subTest(step=version, fault=fault_name):
                    path = Path(self.temp.name) / f"v{version}-{fault_name.replace(' ', '-')}.sqlite3"
                    connection = open_without_migrating(path)
                    try:
                        self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")

                        if version > 1:   # build the database at version - 1
                            with stopped_before_step(connection, version):
                                with self.assertRaises(sqlite3.DatabaseError):
                                    db.migrate(connection)
                        self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], version - 1)
                        before = full_catalog(connection)

                        with self.assertRaises(expected):
                            inject(connection, version)

                        self.assertFalse(connection.in_transaction)
                        self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], version - 1)
                        self.assertEqual(full_catalog(connection), before, f"step {version} left part of itself committed")

                        # the next start: re-open through db.connect(), which migrates
                        connection.close()
                        connection = db.connect(path)
                        self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
                        self.assertEqual(full_catalog(connection), fresh_catalog)
                        self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                    finally:
                        connection.close()

    def test_failure_after_the_first_statements_leaves_a_clean_v12_database_that_reopens(self):
        connection = self.interrupted_at_v13()
        self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 12)
        self.assertEqual(new_task_columns(connection), [], "the ALTERs must roll back with the failed step")
        self.assertEqual(objects(connection), [])
        self.assertFalse(connection.in_transaction)
        self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        connection.close()
        # the next start (connect() migrates) completes the step instead of failing forever
        reopened = db.connect(self.path)
        self.assertEqual(reopened.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
        self.assertEqual(new_task_columns(reopened), [name for name, _ in db.V13_TASK_COLUMNS])
        self.assertEqual(objects(reopened), ["idx_imports_project", "idx_tasks_import_key", "import_template_config", "imports"])
        reopened.close()
        again = db.connect(self.path)   # and re-running on a complete database is a no-op
        self.assertEqual(again.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
        again.close()

    def test_a_database_left_half_applied_by_the_earlier_code_completes_on_the_next_start(self):
        # The state the earlier executescript() form produced when killed at CREATE TABLE imports:
        # user_version 12, all four columns and the unique index already present.
        connection = self.interrupted_at_v13()
        for name, definition in db.V13_TASK_COLUMNS:
            connection.execute(f"ALTER TABLE tasks ADD COLUMN {name} {definition}")
        connection.execute("CREATE UNIQUE INDEX idx_tasks_import_key ON tasks(project_id, import_key) WHERE import_key IS NOT NULL")
        self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 12)
        connection.close()
        reopened = db.connect(self.path)
        self.assertEqual(reopened.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
        self.assertEqual(objects(reopened), ["idx_imports_project", "idx_tasks_import_key", "import_template_config", "imports"])
        self.assertEqual(new_task_columns(reopened), [name for name, _ in db.V13_TASK_COLUMNS])
        reopened.close()

    def test_fresh_database_migrates_to_the_current_schema(self):
        connection = db.connect(self.path)
        self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
        self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        connection.close()

    # 03G8EH: schema 14 makes (task_id, version) unique on task_submissions.
    def at_v13(self):
        """A complete v13 database: v14's CREATE UNIQUE INDEX is refused, so the v14
        step rolls back and leaves user_version at 13."""
        connection = self.raw()
        connection.set_authorizer(deny_create_index(db.V14_SUBMISSION_VERSION_INDEX))
        with self.assertRaises(sqlite3.DatabaseError):
            db.migrate(connection)
        connection.set_authorizer(None)
        self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 13)
        return connection

    def submitted_task(self, connection):
        """One real task with one version-1 submission, written by the service."""
        service = AstraService(connection)
        owner = legacy_user(connection, "legacy-owner", "owner")
        project = service.create_project(owner, "Migration")
        task = service.create_task(owner, {"project_id": project["id"], "title": "Deliverable"})
        service.submit_task(owner, task["id"], "first")
        return task["id"]

    def duplicate_submission(self, connection, task_id):
        """The row a pre-03G8EH concurrent submit left: same task, same version."""
        connection.execute(
            "INSERT INTO task_submissions(id,task_id,version,submitted_by,submitted_at,note,status)"
            " SELECT 'duplicate-row', task_id, version, submitted_by, submitted_at, 'second', 'submitted'"
            " FROM task_submissions WHERE task_id=?",
            (task_id,),
        )

    def submission_rows(self, connection):
        return [
            tuple(row) for row in connection.execute(
                "SELECT id,task_id,version,note FROM task_submissions ORDER BY id"
            ).fetchall()
        ]

    def unique_submission_index(self, connection):
        rows = connection.execute("PRAGMA index_list(task_submissions)").fetchall()
        return {row["name"]: row["unique"] for row in rows}.get(db.V14_SUBMISSION_VERSION_INDEX)

    def test_fresh_v14_database_refuses_a_second_submission_at_one_version(self):
        connection = db.connect(self.path)
        try:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
            self.assertEqual(self.unique_submission_index(connection), 1)
            task_id = self.submitted_task(connection)
            with self.assertRaisesRegex(sqlite3.IntegrityError, "UNIQUE"):
                self.duplicate_submission(connection, task_id)
        finally:
            connection.close()

    def test_v13_database_with_submissions_upgrades_to_v14_and_matches_fresh_schema(self):
        connection = self.at_v13()
        try:
            task_id = self.submitted_task(connection)
            before = self.submission_rows(connection)
            self.assertIsNone(self.unique_submission_index(connection))

            db.migrate(connection)

            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
            self.assertEqual(self.unique_submission_index(connection), 1)
            self.assertEqual(self.submission_rows(connection), before)
            self.assertEqual([row[1] for row in before], [task_id])
            fresh = db.connect(Path(self.temp.name) / "fresh.sqlite3")
            try:
                self.assertEqual(schema_signature(connection), schema_signature(fresh))
            finally:
                fresh.close()
        finally:
            connection.close()

    def test_v13_duplicate_submission_versions_refuse_the_upgrade_without_touching_data(self):
        connection = self.at_v13()
        try:
            task_id = self.submitted_task(connection)
            self.duplicate_submission(connection, task_id)
            accepted_id = connection.execute(
                "SELECT id FROM task_submissions WHERE task_id=? AND id<>'duplicate-row'", (task_id,)
            ).fetchone()[0]
            connection.execute("UPDATE task_submissions SET status='accepted' WHERE id=?", (accepted_id,))
            connection.execute("UPDATE tasks SET accepted_submission_id=? WHERE id=?", (accepted_id, task_id))
            before = self.submission_rows(connection)
            self.assertEqual(len(before), 2)

            with self.assertRaises(db.SchemaMigrationRefused) as refused:
                db.migrate(connection)
            message = str(refused.exception)
            self.assertIn("schema 14", message)
            self.assertIn(f"task {task_id} version 1:", message)
            self.assertIn(f"submission {accepted_id} (accepted, referenced by tasks.accepted_submission_id)", message)
            self.assertIn("submission duplicate-row (submitted)", message)
            self.assertIn("keep the accepted row", message)
            self.assertIn("PRAGMA foreign_keys=ON", message)
            self.assertNotIn("03G8EH", message)
            self.assertNotIn("first", message, "notes must not be echoed")
            self.assertNotIn("Deliverable", message, "titles must not be echoed")

            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 13)
            self.assertEqual(self.submission_rows(connection), before, "no submission may be deleted")
            self.assertIsNone(self.unique_submission_index(connection))
            self.assertFalse(connection.in_transaction)
        finally:
            connection.close()
        with self.assertRaises(db.SchemaMigrationRefused):   # connect() refuses the same way
            db.connect(self.path)

        repaired = self.raw()   # once the Owner resolves the pair, the next start upgrades
        try:
            repaired.execute("DELETE FROM task_submissions WHERE id='duplicate-row'")
        finally:
            repaired.close()
        reopened = db.connect(self.path)
        try:
            self.assertEqual(reopened.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
            self.assertEqual(self.unique_submission_index(reopened), 1)
        finally:
            reopened.close()

    def test_failure_creating_the_v14_index_rolls_back_to_v13_and_retries(self):
        connection = self.at_v13()
        try:
            self.submitted_task(connection)
            before = self.submission_rows(connection)
            connection.set_authorizer(deny_create_index(db.V14_SUBMISSION_VERSION_INDEX))
            with self.assertRaises(sqlite3.DatabaseError):
                db.migrate(connection)
            connection.set_authorizer(None)
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 13)
            self.assertIsNone(self.unique_submission_index(connection))
            self.assertFalse(connection.in_transaction)

            db.migrate(connection)

            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
            self.assertEqual(self.unique_submission_index(connection), 1)
            self.assertEqual(self.submission_rows(connection), before)
        finally:
            connection.close()


    def test_duplicates_in_an_older_database_refuse_before_any_step_runs(self):
        # Stop at v9 (v10 creates final_results), then add a pre-fix duplicate pair.
        connection = self.raw()
        try:
            connection.set_authorizer(deny_create_table("final_results"))
            with self.assertRaises(sqlite3.DatabaseError):
                db.migrate(connection)
            connection.set_authorizer(None)
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 9)
            connection.execute("PRAGMA foreign_keys = OFF")
            for row_id in ("pair-a", "pair-b"):
                connection.execute(
                    "INSERT INTO task_submissions(id,task_id,version,submitted_by,submitted_at,note,status)"
                    " VALUES(?,'task-1',1,'user-1','2026-01-01T00:00:00Z','private note','submitted')",
                    (row_id,),
                )
            connection.execute("PRAGMA foreign_keys = ON")
            schema_before = schema_signature(connection)
            rows_before = self.submission_rows(connection)

            with self.assertRaises(db.SchemaMigrationRefused) as refused:
                db.migrate(connection)

            message = str(refused.exception)
            self.assertIn("Nothing was changed", message)
            self.assertIn("task task-1 version 1: submission pair-a (submitted), submission pair-b (submitted)", message)
            self.assertNotIn("private note", message)
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 9)
            self.assertEqual(schema_signature(connection), schema_before, "no later step may have committed")
            self.assertEqual(self.submission_rows(connection), rows_before)
            self.assertFalse(connection.in_transaction)
        finally:
            connection.close()

    def test_serve_exits_with_the_refusal_message_instead_of_a_traceback(self):
        connection = self.at_v13()
        try:
            task_id = self.submitted_task(connection)
            self.duplicate_submission(connection, task_id)
        finally:
            connection.close()
        from astra import __main__ as entry
        with patch.dict(os.environ, {"ASTRA_HOME": self.temp.name}):
            with patch.object(entry, "serve", side_effect=lambda host, port: db.connect()):
                with self.assertRaises(SystemExit) as stopped:
                    entry.main(["serve", "--port", "0"])
        self.assertIsInstance(stopped.exception.code, str)
        self.assertIn("cannot upgrade this database to schema 14", stopped.exception.code)


class PendingRequestIntentKeyTests(unittest.TestCase):
    """WNXSDA: schema 15 stores an intent key on owner_action_requests and makes it
    unique among pending rows, so equivalent pending requests are enforced by the
    database and found by an index instead of by payload text compared per row."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "astra.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def raw(self):
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def version(self, connection):
        return connection.execute("PRAGMA user_version").fetchone()[0]

    def at_v14(self):
        """A complete v14 database: v15's unique index is refused, so the v15 step rolls
        back (its ALTERs and backfill included) and leaves user_version at 14."""
        connection = self.raw()
        connection.set_authorizer(deny_create_index(db.V15_PENDING_INTENT_INDEX))
        with self.assertRaises(sqlite3.DatabaseError):
            db.migrate(connection)
        connection.set_authorizer(None)
        self.assertEqual(self.version(connection), 14)
        return connection

    def fixture(self, connection):
        """Owner, project and task created by the service; the task's id and revision."""
        service = AstraService(connection)
        owner = legacy_user(connection, "legacy-owner", "owner")
        project = service.create_project(owner, "Intent key")
        task = service.create_task(owner, {"project_id": project["id"], "title": "Governed secret title"})
        return owner, project, task

    def legacy_request(self, connection, request_id, owner, project, task, status="pending", reason="private reason"):
        """A request row as the v12-v14 schema stores it, written without the service."""
        payload_json = json.dumps(
            {"expected_revision": task["revision"], "status": "cancelled"}, sort_keys=True
        )
        connection.execute(
            "INSERT INTO owner_action_requests"
            "(id,project_id,task_id,action,payload_json,reason,requested_by,requested_at,status)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (request_id, project["id"], task["id"], "update_task_status", payload_json, reason,
             owner["id"], f"2026-09-0{len(request_id) % 9 + 1}T00:00:00Z", status),
        )
        return payload_json

    def request_rows(self, connection):
        return [
            tuple(row) for row in connection.execute(
                "SELECT id,project_id,task_id,action,payload_json,reason,requested_by,status"
                " FROM owner_action_requests ORDER BY id"
            ).fetchall()
        ]

    def indexes(self, connection):
        rows = connection.execute("PRAGMA index_list(owner_action_requests)").fetchall()
        return {row["name"]: (row["unique"], row["partial"]) for row in rows}

    def test_fresh_database_has_the_intent_key_and_its_indexes(self):
        connection = db.connect(self.path)
        try:
            self.assertEqual(self.version(connection), db.SCHEMA_VERSION)
            self.assertGreaterEqual(db.SCHEMA_VERSION, 15)
            columns = table_columns(connection, "owner_action_requests")
            self.assertIn("intent_key", columns)
            self.assertIn("expected_revision", columns)
            indexes = self.indexes(connection)
            self.assertEqual(indexes.get(db.V15_PENDING_INTENT_INDEX), (1, 1))
            self.assertEqual(indexes.get(db.V15_PENDING_LOOKUP_INDEX), (0, 1))
        finally:
            connection.close()

    def test_schema_refuses_a_second_identical_pending_request(self):
        connection = db.connect(self.path)
        try:
            owner, project, task = self.fixture(connection)
            manager_request = {"status": "cancelled", "expected_revision": task["revision"]}
            payload_json = json.dumps(manager_request, sort_keys=True)
            key = db.owner_request_intent_key(
                project["id"], task["id"], "update_task_status", payload_json, "why", owner["id"]
            )
            insert = (
                "INSERT INTO owner_action_requests(id,project_id,task_id,action,payload_json,reason,"
                "requested_by,requested_at,status,intent_key) VALUES(?,?,?,?,?,?,?,?,?,?)"
            )
            values = (project["id"], task["id"], "update_task_status", payload_json, "why",
                      owner["id"], "2026-09-23T00:00:00Z")
            connection.execute(insert, ("first", *values, "pending", key))
            with self.assertRaisesRegex(sqlite3.IntegrityError, "UNIQUE"):
                connection.execute(insert, ("second", *values, "pending", key))
            # a decided request with the same intent is history, not a duplicate
            connection.execute(insert, ("decided", *values, "approved", key))
        finally:
            connection.close()

    def test_v14_database_upgrades_with_backfilled_keys_and_matches_fresh_schema(self):
        connection = self.at_v14()
        try:
            owner, project, task = self.fixture(connection)
            payload_json = self.legacy_request(connection, "legacy-pending", owner, project, task)
            self.legacy_request(connection, "legacy-approved", owner, project, task, status="approved")
            before = self.request_rows(connection)

            db.migrate(connection)

            self.assertEqual(self.version(connection), db.SCHEMA_VERSION)
            self.assertEqual(self.request_rows(connection), before, "the backfill changes no existing field")
            expected_key = db.owner_request_intent_key(
                project["id"], task["id"], "update_task_status", payload_json, "private reason", owner["id"]
            )
            keys = dict(connection.execute(
                "SELECT id,intent_key FROM owner_action_requests").fetchall())
            self.assertEqual(keys, {"legacy-pending": expected_key, "legacy-approved": expected_key})
            revisions = {row[0] for row in connection.execute(
                "SELECT expected_revision FROM owner_action_requests").fetchall()}
            self.assertEqual(revisions, {task["revision"]})
            fresh = db.connect(Path(self.temp.name) / "fresh.sqlite3")
            try:
                self.assertEqual(schema_signature(connection), schema_signature(fresh))
            finally:
                fresh.close()
        finally:
            connection.close()

    def test_v14_duplicate_pending_requests_refuse_the_upgrade_without_touching_data(self):
        connection = self.at_v14()
        try:
            owner, project, task = self.fixture(connection)
            self.legacy_request(connection, "twin-a", owner, project, task)
            self.legacy_request(connection, "twin-bb", owner, project, task)
            self.legacy_request(connection, "old-decided", owner, project, task, status="rejected")
            schema_before = schema_signature(connection)
            before = self.request_rows(connection)

            with self.assertRaises(db.SchemaMigrationRefused) as refused:
                db.migrate(connection)

            message = str(refused.exception)
            self.assertIn("schema 15", message)
            self.assertIn("Nothing was changed", message)
            self.assertIn("request twin-a", message)
            self.assertIn("request twin-bb", message)
            self.assertNotIn("old-decided", message, "decided requests are not duplicates")
            self.assertIn("update_task_status", message)
            self.assertIn(f"task {task['id']}", message)
            self.assertNotIn("private reason", message, "reasons must not be echoed")
            self.assertNotIn("Governed secret title", message, "titles must not be echoed")
            self.assertNotIn("WNXSDA", message)
            self.assertEqual(self.version(connection), 14)
            self.assertEqual(schema_signature(connection), schema_before)
            self.assertEqual(self.request_rows(connection), before)
            self.assertFalse(connection.in_transaction)
        finally:
            connection.close()
        with self.assertRaises(db.SchemaMigrationRefused):   # connect() refuses the same way
            db.connect(self.path)

        repaired = self.raw()   # once one twin is cancelled, the next start upgrades
        try:
            repaired.execute("UPDATE owner_action_requests SET status='cancelled' WHERE id='twin-bb'")
        finally:
            repaired.close()
        reopened = db.connect(self.path)
        try:
            self.assertEqual(self.version(reopened), db.SCHEMA_VERSION)
        finally:
            reopened.close()

    def test_duplicate_pending_requests_in_an_older_database_refuse_before_any_step_runs(self):
        connection = self.raw()
        try:
            connection.set_authorizer(deny_create_table(DENY_IMPORTS_TABLE))   # stop at v12
            with self.assertRaises(sqlite3.DatabaseError):
                db.migrate(connection)
            connection.set_authorizer(None)
            self.assertEqual(self.version(connection), 12)
            connection.execute("PRAGMA foreign_keys = OFF")
            for request_id in ("pair-a", "pair-b"):
                connection.execute(
                    "INSERT INTO owner_action_requests"
                    "(id,project_id,task_id,action,payload_json,reason,requested_by,requested_at,status)"
                    " VALUES(?,'project-1',NULL,'close_project','{}','private reason','user-1',"
                    "'2026-01-01T00:00:00Z','pending')",
                    (request_id,),
                )
            connection.execute("PRAGMA foreign_keys = ON")
            schema_before = schema_signature(connection)
            before = self.request_rows(connection)

            with self.assertRaises(db.SchemaMigrationRefused) as refused:
                db.migrate(connection)

            message = str(refused.exception)
            self.assertIn("project project-1 close_project: request pair-a, request pair-b", message)
            self.assertNotIn("private reason", message)
            self.assertEqual(self.version(connection), 12)
            self.assertEqual(schema_signature(connection), schema_before, "no later step may have committed")
            self.assertEqual(self.request_rows(connection), before)
            self.assertFalse(connection.in_transaction)
        finally:
            connection.close()

    def test_failure_late_in_the_v15_step_rolls_back_columns_and_backfill_then_retries(self):
        connection = self.at_v14()
        try:
            owner, project, task = self.fixture(connection)
            self.legacy_request(connection, "legacy-pending", owner, project, task)
            columns_before = table_columns(connection, "owner_action_requests")
            rows_before = self.request_rows(connection)
            catalog_before = full_catalog(connection)

            connection.set_authorizer(deny_create_index(db.V15_PENDING_INTENT_INDEX))
            with self.assertRaises(sqlite3.DatabaseError):
                db.migrate(connection)
            connection.set_authorizer(None)

            self.assertEqual(self.version(connection), 14)
            self.assertEqual(table_columns(connection, "owner_action_requests"), columns_before)
            self.assertNotIn("intent_key", columns_before)
            self.assertEqual(self.request_rows(connection), rows_before)
            self.assertEqual(full_catalog(connection), catalog_before)
            self.assertFalse(connection.in_transaction)

            db.migrate(connection)

            self.assertEqual(self.version(connection), db.SCHEMA_VERSION)
            self.assertIsNotNone(connection.execute(
                "SELECT intent_key FROM owner_action_requests WHERE id='legacy-pending'").fetchone()[0])
        finally:
            connection.close()

    def test_service_finds_a_backfilled_request_by_its_key(self):
        """A request filed before the upgrade is the one an identical retry returns."""
        connection = self.at_v14()
        try:
            owner, project, task = self.fixture(connection)
            service = AstraService(connection)
            manager = legacy_user(connection, "legacy-manager")
            connection.execute("INSERT INTO memberships VALUES(?,?,'manager','2026-01-01T00:00:00Z',?)",
                               (project["id"], manager["id"], owner["id"]))
            payload_json = json.dumps(
                {"expected_revision": task["revision"], "reason": "Manager recommendation", "status": "cancelled"},
                sort_keys=True,
            )
            connection.execute(
                "INSERT INTO owner_action_requests"
                "(id,project_id,task_id,action,payload_json,reason,requested_by,requested_at,status)"
                " VALUES('filed-before-upgrade',?,?,'update_task_status',?,'Manager recommendation',?,"
                "'2026-09-01T00:00:00Z','pending')",
                (project["id"], task["id"], payload_json, manager["id"]),
            )
            db.migrate(connection)

            retried = service.update_task(manager, task["id"], {
                "status": "cancelled", "reason": "Manager recommendation", "expected_revision": task["revision"],
            })
            self.assertEqual(retried["request"]["id"], "filed-before-upgrade")
            self.assertEqual(connection.execute(
                "SELECT COUNT(*) FROM owner_action_requests WHERE status='pending'").fetchone()[0], 1)
        finally:
            connection.close()


class PrimaryOwnerMigrationTests(unittest.TestCase):
    """GTEYTG: schema 16 marks the one existing owner as the primary owner, adds the
    user_events audit table, and refuses (changing nothing) a database with 2+ owners."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "astra.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def raw(self):
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def version(self, connection):
        return connection.execute("PRAGMA user_version").fetchone()[0]

    def at_v15(self):
        """A complete v15 database: v16's unique index is refused, so the step rolls back."""
        connection = self.raw()
        connection.set_authorizer(deny_create_index(db.V16_PRIMARY_OWNER_INDEX))
        with self.assertRaises(sqlite3.DatabaseError):
            db.migrate(connection)
        connection.set_authorizer(None)
        self.assertEqual(self.version(connection), 15)
        return connection

    def user_rows(self, connection):
        return [tuple(r) for r in connection.execute("SELECT * FROM users ORDER BY id").fetchall()]

    def test_fresh_database_has_the_primary_flag_its_index_and_user_events(self):
        connection = db.connect(self.path)
        try:
            self.assertGreaterEqual(db.SCHEMA_VERSION, 16)
            self.assertIn("is_primary_owner", table_columns(connection, "users"))
            indexes = {r["name"]: (r["unique"], r["partial"]) for r in connection.execute("PRAGMA index_list(users)")}
            self.assertEqual(indexes.get(db.V16_PRIMARY_OWNER_INDEX), (1, 1))
            self.assertEqual(table_columns(connection, "user_events"),
                             ["id", "target_user_id", "event_type", "actor_user_id", "occurred_at", "reason",
                              "detail_json"])
        finally:
            connection.close()

    def test_v15_single_owner_becomes_primary_and_matches_fresh_schema(self):
        connection = self.at_v15()
        try:
            legacy_user(connection, "owner-1", "owner")
            legacy_user(connection, "member-1", "member")
            db.migrate(connection)
            self.assertEqual(self.version(connection), db.SCHEMA_VERSION)
            flags = dict(connection.execute("SELECT id,is_primary_owner FROM users").fetchall())
            self.assertEqual(flags, {"owner-1": 1, "member-1": 0})
            fresh = db.connect(Path(self.temp.name) / "fresh.sqlite3")
            try:
                self.assertEqual(schema_signature(connection), schema_signature(fresh))
            finally:
                fresh.close()
        finally:
            connection.close()

    def test_v15_without_an_owner_migrates_and_the_first_owner_becomes_primary(self):
        connection = self.at_v15()
        try:
            db.migrate(connection)
            self.assertEqual(self.version(connection), db.SCHEMA_VERSION)
            owner = AstraService(connection).create_initial_owner("o@example.org", "Owner", "correct horse battery")
            self.assertEqual(owner["is_primary_owner"], 1)
        finally:
            connection.close()

    def test_v15_with_two_owners_refuses_the_upgrade_without_touching_data(self):
        connection = self.at_v15()
        try:
            legacy_user(connection, "owner-a", "owner")
            legacy_user(connection, "owner-b", "owner")
            schema_before, rows_before = schema_signature(connection), self.user_rows(connection)
            with self.assertRaises(db.SchemaMigrationRefused) as refused:
                db.migrate(connection)
            message = str(refused.exception)
            self.assertIn("schema 16", message)
            self.assertIn("Nothing was changed", message)
            self.assertIn("owner-a", message)
            self.assertIn("owner-b", message)
            self.assertNotIn("secret-", message, "emails must not be echoed")
            self.assertNotIn("Private", message, "names must not be echoed")
            self.assertEqual(self.version(connection), 15)
            self.assertEqual(schema_signature(connection), schema_before)
            self.assertEqual(self.user_rows(connection), rows_before)
            self.assertFalse(connection.in_transaction)
        finally:
            connection.close()
        with self.assertRaises(db.SchemaMigrationRefused):
            db.connect(self.path)
        repaired = self.raw()
        try:
            repaired.execute("UPDATE users SET global_role='member' WHERE id='owner-b'")
        finally:
            repaired.close()
        reopened = db.connect(self.path)
        try:
            self.assertEqual(self.version(reopened), db.SCHEMA_VERSION)
            self.assertEqual(reopened.execute("SELECT id FROM users WHERE is_primary_owner=1").fetchone()[0], "owner-a")
        finally:
            reopened.close()

    def test_two_owners_in_an_older_database_refuse_before_any_step_runs(self):
        connection = self.raw()
        try:
            connection.set_authorizer(deny_create_table(DENY_IMPORTS_TABLE))   # stop at v12
            with self.assertRaises(sqlite3.DatabaseError):
                db.migrate(connection)
            connection.set_authorizer(None)
            self.assertEqual(self.version(connection), 12)
            legacy_user(connection, "owner-a", "owner")
            legacy_user(connection, "owner-b", "owner")
            schema_before = schema_signature(connection)
            with self.assertRaises(db.SchemaMigrationRefused) as refused:
                db.migrate(connection)
            self.assertIn("owner-a", str(refused.exception))
            self.assertEqual(self.version(connection), 12)
            self.assertEqual(schema_signature(connection), schema_before, "no later step may have committed")
            self.assertFalse(connection.in_transaction)
        finally:
            connection.close()

    def test_second_owner_written_after_the_early_check_is_refused_inside_the_step(self):
        connection = self.at_v15()
        try:
            legacy_user(connection, "owner-a", "owner")
            real_refuse, calls = db._refuse_multiple_owners, []

            def refuse_then_race(conn):
                real_refuse(conn)
                calls.append(1)
                if len(calls) == 1:   # after migrate()'s early check, before the v16 step
                    legacy_user(conn, "owner-b", "owner")

            with patch.object(db, "_refuse_multiple_owners", refuse_then_race):
                with self.assertRaises(db.SchemaMigrationRefused) as refused:
                    db.migrate(connection)
            self.assertEqual(len(calls), 1, "the early check passed; the step's own check refused")
            self.assertIn("owner-b", str(refused.exception))
            self.assertEqual(self.version(connection), 15)
            self.assertNotIn("is_primary_owner", table_columns(connection, "users"))
            self.assertFalse(connection.in_transaction)
        finally:
            connection.close()

    def test_failure_late_in_the_v16_step_rolls_back_then_retries(self):
        connection = self.at_v15()
        try:
            legacy_user(connection, "owner-1", "owner")
            catalog_before, rows_before = full_catalog(connection), self.user_rows(connection)
            connection.set_authorizer(deny_create_index(db.V16_PRIMARY_OWNER_INDEX))
            with self.assertRaises(sqlite3.DatabaseError):
                db.migrate(connection)
            connection.set_authorizer(None)
            self.assertEqual(self.version(connection), 15)
            self.assertEqual(full_catalog(connection), catalog_before)
            self.assertEqual(self.user_rows(connection), rows_before)
            self.assertNotIn("is_primary_owner", table_columns(connection, "users"))
            self.assertFalse(connection.in_transaction)
            db.migrate(connection)
            self.assertEqual(self.version(connection), db.SCHEMA_VERSION)
            self.assertEqual(connection.execute("SELECT is_primary_owner FROM users").fetchone()[0], 1)
        finally:
            connection.close()

    def test_concurrent_initial_owner_creation_makes_exactly_one_owner(self):
        db.connect(self.path).close()
        barrier, outcomes = threading.Barrier(2), []

        def create(n):
            connection = db.connect(self.path)
            try:
                barrier.wait()
                AstraService(connection).create_initial_owner(f"o{n}@example.org", "Owner", "correct horse battery")
                outcomes.append("created")
            except ValueError:   # the check runs under the write lock, so no IntegrityError
                outcomes.append("refused")
            except sqlite3.IntegrityError:
                outcomes.append("integrity")
            finally:
                connection.close()

        threads = [threading.Thread(target=create, args=(n,)) for n in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(outcomes, ["created", "refused"])
        connection = db.connect(self.path)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM users WHERE global_role='owner'").fetchone()[0], 1)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
