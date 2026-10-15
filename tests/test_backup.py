from __future__ import annotations

import contextlib
import io
import os
import shutil
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from astra.db import connect, database_path
from astra.service import AstraService


class BackupCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {"ASTRA_HOME": self.temp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        db = connect()
        try:
            AstraService(db).create_initial_owner(
                "owner@example.org", "Owner", "correct horse battery"
            )
        finally:
            db.close()

    def run_cli(self, argv):
        from astra.__main__ import main

        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                main(argv)
                exit_code = 0
            except SystemExit as stopped:
                exit_code = stopped.code
        self.assertEqual(exit_code, 0, stderr.getvalue() or str(exit_code))
        return stdout.getvalue()

    def run_cli_result(self, argv):
        from astra.__main__ import main

        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                main(argv)
                exit_code = 0
            except SystemExit as stopped:
                exit_code = stopped.code
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_backup_command_writes_an_integral_sqlite_snapshot(self):
        destination = Path(self.temp.name) / "backups" / "astra-copy.sqlite3"

        output = self.run_cli(["backup", "--to", str(destination)])

        self.assertIn("Backup written", output)
        backup = sqlite3.connect(destination)
        try:
            self.assertEqual(backup.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(backup.execute("SELECT email FROM users").fetchone()[0], "owner@example.org")
        finally:
            backup.close()

    def test_restore_command_reopens_a_valid_copy_at_a_new_target(self):
        backup_path = Path(self.temp.name) / "astra-copy.sqlite3"
        restored_path = Path(self.temp.name) / "recovery" / "astra.sqlite3"
        self.run_cli(["backup", "--to", str(backup_path)])

        output = self.run_cli(["restore", "--from", str(backup_path), "--to", str(restored_path)])

        self.assertIn("Database restored", output)
        restored = connect(restored_path)
        try:
            self.assertEqual(
                restored.execute("SELECT email FROM users").fetchone()[0],
                "owner@example.org",
            )
        finally:
            restored.close()
        self.assertTrue(backup_path.exists())
        self.assertTrue(database_path().exists())

    def test_backup_refuses_to_replace_an_existing_file(self):
        destination = Path(self.temp.name) / "existing.sqlite3"
        destination.write_bytes(b"keep this file")

        code, _, stderr = self.run_cli_result(["backup", "--to", str(destination)])

        self.assertNotEqual(code, 0)
        self.assertIn("already exists", str(code) + stderr)
        self.assertEqual(destination.read_bytes(), b"keep this file")

    def test_restore_refuses_a_corrupt_backup_without_creating_target(self):
        corrupt = Path(self.temp.name) / "corrupt.sqlite3"
        destination = Path(self.temp.name) / "recovery.sqlite3"
        corrupt.write_bytes(b"not an SQLite database")

        code, _, stderr = self.run_cli_result(
            ["restore", "--from", str(corrupt), "--to", str(destination)]
        )

        self.assertNotEqual(code, 0)
        self.assertIn("Could not validate Backup database", str(code))
        self.assertFalse(destination.exists())
        self.assertTrue(corrupt.exists())

    def test_restore_refuses_to_replace_an_existing_database(self):
        backup_path = Path(self.temp.name) / "valid.sqlite3"
        destination = Path(self.temp.name) / "existing.sqlite3"
        self.run_cli(["backup", "--to", str(backup_path)])
        destination.write_bytes(b"keep this database")

        code, _, _ = self.run_cli_result(
            ["restore", "--from", str(backup_path), "--to", str(destination)]
        )

        self.assertNotEqual(code, 0)
        self.assertIn("already exists", str(code))
        self.assertEqual(destination.read_bytes(), b"keep this database")

    def test_restore_refuses_a_backup_from_a_newer_schema(self):
        newer = Path(self.temp.name) / "astra-vfuture.sqlite3"
        self.run_cli(["backup", "--to", str(newer)])
        connection = sqlite3.connect(newer)
        try:
            connection.execute("PRAGMA user_version=22")
        finally:
            connection.close()
        destination = Path(self.temp.name) / "future-recovery" / "astra.sqlite3"

        code, _, stderr = self.run_cli_result(
            ["restore", "--from", str(newer), "--to", str(destination)]
        )

        self.assertNotEqual(code, 0)
        self.assertIn("newer than this Astra version", str(code) + stderr)
        self.assertFalse(destination.exists())

    def test_restore_refuses_a_current_version_file_missing_required_tables(self):
        incomplete = Path(self.temp.name) / "incomplete.sqlite3"
        connection = sqlite3.connect(incomplete)
        try:
            connection.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
            connection.execute("PRAGMA user_version=21")
        finally:
            connection.close()
        destination = Path(self.temp.name) / "incomplete-recovery" / "astra.sqlite3"

        code, _, stderr = self.run_cli_result(
            ["restore", "--from", str(incomplete), "--to", str(destination)]
        )

        self.assertNotEqual(code, 0)
        self.assertIn("missing required tables", str(code) + stderr)
        self.assertFalse(destination.exists())

    def test_restore_removes_partial_target_and_sidecars_on_copy_failure(self):
        from astra.backup import restore_backup

        backup_path = Path(self.temp.name) / "valid-for-failure.sqlite3"
        destination = Path(self.temp.name) / "failed-recovery" / "astra.sqlite3"
        self.run_cli(["backup", "--to", str(backup_path)])

        with patch("astra.backup._online_copy", side_effect=RuntimeError("simulated copy failure")):
            with self.assertRaisesRegex(RuntimeError, "simulated copy failure"):
                restore_backup(backup_path, destination)

        self.assertFalse(destination.exists())
        self.assertFalse(Path(f"{destination}-wal").exists())
        self.assertFalse(Path(f"{destination}-shm").exists())

    def test_backup_refuses_the_live_database_as_its_destination(self):
        source = database_path()
        before = source.read_bytes()

        code, _, _ = self.run_cli_result(["backup", "--to", str(source)])

        self.assertNotEqual(code, 0)
        self.assertIn("must be different files", str(code))
        self.assertEqual(source.read_bytes(), before)

    def test_restore_of_an_older_schema_reopens_after_migration(self):
        older = Path(self.temp.name) / "astra-v20.sqlite3"
        shutil.copy2(database_path(), older)
        old_db = sqlite3.connect(older)
        try:
            old_db.execute("ALTER TABLE users DROP COLUMN must_change_password")
            old_db.execute("PRAGMA user_version=20")
        finally:
            old_db.close()
        restored_path = Path(self.temp.name) / "old-recovery" / "astra.sqlite3"

        self.run_cli(["restore", "--from", str(older), "--to", str(restored_path)])

        restored = connect(restored_path)
        try:
            self.assertEqual(restored.execute("PRAGMA user_version").fetchone()[0], 21)
            self.assertEqual(
                tuple(restored.execute(
                    "SELECT email, must_change_password FROM users"
                ).fetchone()),
                ("owner@example.org", 0),
            )
        finally:
            restored.close()

    def test_backup_remains_consistent_when_a_write_commits_during_snapshot(self):
        db = connect()
        try:
            db.execute("CREATE TABLE backup_probe (seq INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
            db.executemany(
                "INSERT INTO backup_probe(seq, payload) VALUES (?, ?)",
                ((seq, "x" * 2048) for seq in range(4000)),
            )
        finally:
            db.close()

        snapshot_copy_started = threading.Event()
        writer_committed = threading.Event()
        writer_errors = []

        def write_transaction():
            writer = sqlite3.connect(database_path(), timeout=30, isolation_level=None)
            try:
                writer.execute("PRAGMA busy_timeout = 30000")
                writer.execute("BEGIN IMMEDIATE")
                writer.executemany(
                    "INSERT INTO backup_probe(seq, payload) VALUES (?, ?)",
                    ((seq, "y" * 2048) for seq in range(4000, 5000)),
                )
                if not snapshot_copy_started.wait(5):
                    raise TimeoutError("backup did not begin copying")
                writer.commit()
                writer_committed.set()
            except Exception as exc:  # surfaced in the test thread below
                writer_errors.append(exc)
                if writer.in_transaction:
                    writer.rollback()
            finally:
                writer.close()

        writer_thread = threading.Thread(target=write_transaction)
        writer_thread.start()
        destination = Path(self.temp.name) / "concurrent.sqlite3"
        from astra.backup import _online_copy

        def progress(_status, _remaining, _total):
            if not snapshot_copy_started.is_set():
                snapshot_copy_started.set()
                if not writer_committed.wait(5):
                    raise TimeoutError("writer did not commit during the snapshot")

        def synchronized_copy(source, target, label):
            return _online_copy(
                source, target, label,
                progress=progress if label == "Backup" else None,
            )

        try:
            with patch("astra.backup._online_copy", side_effect=synchronized_copy):
                self.run_cli(["backup", "--to", str(destination)])
        finally:
            snapshot_copy_started.set()
            writer_thread.join(timeout=5)

        self.assertFalse(writer_thread.is_alive())
        self.assertEqual(writer_errors, [])
        self.assertTrue(writer_committed.is_set())
        backup = sqlite3.connect(destination)
        try:
            self.assertEqual(backup.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            count = backup.execute("SELECT COUNT(*) FROM backup_probe").fetchone()[0]
            self.assertIn(count, (4000, 5000))
            self.assertEqual(
                backup.execute("SELECT COUNT(DISTINCT seq) FROM backup_probe").fetchone()[0],
                count,
            )
        finally:
            backup.close()


if __name__ == "__main__":
    unittest.main()
