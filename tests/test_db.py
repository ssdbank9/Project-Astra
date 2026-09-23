import os
import sqlite3
import tempfile
import unittest
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
        owner = service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")
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
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 14)
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

            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 14)
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
            self.assertEqual(reopened.execute("PRAGMA user_version").fetchone()[0], 14)
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

            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 14)
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


if __name__ == "__main__":
    unittest.main()
