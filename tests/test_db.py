import sqlite3
import tempfile
import unittest
from pathlib import Path

from astra import db


DENY_IMPORTS_TABLE = "imports"


def deny_create_table(name):
    """An authorizer that refuses CREATE TABLE <name>: a failure injected mid-migration."""
    def authorizer(action, arg1, arg2, db_name, trigger):
        if action == sqlite3.SQLITE_CREATE_TABLE and arg1 == name:
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


class MigrationTests(unittest.TestCase):
    """Regression review MIGRATION-1 (2026-09-22): the v12 -> v13 step ran through
    executescript(), which commits the surrounding BEGIN IMMEDIATE, so an interruption
    between two of its statements left user_version at 12 with some columns present and
    every later connect() died on 'duplicate column name: import_key'."""

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


if __name__ == "__main__":
    unittest.main()
