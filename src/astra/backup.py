"""Safe, SQLite-consistent backup and restore primitives for the Astra CLI."""

from __future__ import annotations

import os
import sqlite3
from contextlib import suppress
from pathlib import Path

from .db import SCHEMA_VERSION, connect


class BackupError(ValueError):
    """A backup or restore was refused or could not be completed safely."""


_CURRENT_REQUIRED_TABLES = frozenset({
    "users", "sessions", "entities", "projects", "project_entities", "memberships",
    "tasks", "task_dependencies", "task_events", "login_attempts", "task_submissions",
    "task_reviewers", "task_checkpoints", "project_events", "notifications",
    "task_schedule_proposals", "project_holidays", "task_attachments", "templates",
    "final_results", "owner_action_requests", "imports", "import_template_config",
    "user_events", "task_locks", "wip_limits",
})


def _sqlite_uri(path: Path) -> str:
    return path.resolve().as_uri() + "?mode=ro"


def _resolve_path(path: Path, label: str) -> Path:
    try:
        return Path(path).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise BackupError(f"Could not resolve {label} path {path}: {exc}") from None


def _readonly_database(path: Path, label: str) -> sqlite3.Connection:
    if not path.is_file():
        raise BackupError(f"{label} database does not exist: {path}")
    connection = None
    try:
        connection = sqlite3.connect(_sqlite_uri(path), uri=True, timeout=30)
        connection.execute("PRAGMA busy_timeout = 30000")
        _validate_astra_database(connection, label)
        return connection
    except BackupError:
        if connection is not None:
            connection.close()
        raise
    except sqlite3.Error as exc:
        if connection is not None:
            connection.close()
        raise BackupError(f"Could not read {label} database {path}: {exc}") from None


def _validate_astra_database(connection: sqlite3.Connection, label: str) -> None:
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        has_users = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        version = connection.execute("PRAGMA user_version").fetchone()[0]
    except sqlite3.Error as exc:
        raise BackupError(f"Could not validate {label} database: {exc}") from None
    integrity_messages = [str(row[0]) for row in integrity]
    if integrity_messages != ["ok"]:
        detail = "; ".join(integrity_messages[:5]) or "no integrity result"
        raise BackupError(f"{label} database failed integrity_check: {detail}")
    if not has_users or version < 1:
        raise BackupError(f"{label} file is not an Astra database.")
    if version > SCHEMA_VERSION:
        raise BackupError(
            f"{label} database uses schema {version}, newer than this Astra version "
            f"(schema {SCHEMA_VERSION}). Install the matching Astra version first."
        )
    if version == SCHEMA_VERSION:
        missing = sorted(_CURRENT_REQUIRED_TABLES - tables)
        if missing:
            raise BackupError(
                f"{label} database claims schema {SCHEMA_VERSION} but is missing required "
                f"tables: {', '.join(missing)}."
            )


def _distinct_paths(source: Path, destination: Path) -> None:
    if source.resolve() == destination.resolve():
        raise BackupError("Source and destination must be different files.")
    if destination.exists():
        try:
            if os.path.samefile(source, destination):
                raise BackupError("Source and destination must be different files.")
        except OSError:
            pass


def _create_exclusive_database(path: Path) -> sqlite3.Connection:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BackupError(f"Could not create destination folder {path.parent}: {exc}") from None
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise BackupError(f"Destination already exists; it was left unchanged: {path}") from None
    except OSError as exc:
        raise BackupError(f"Could not create destination {path}: {exc}") from None
    os.close(descriptor)
    try:
        return sqlite3.connect(path, timeout=30)
    except sqlite3.Error as exc:
        path.unlink(missing_ok=True)
        raise BackupError(f"Could not open destination {path}: {exc}") from None


def _online_copy(
    source: sqlite3.Connection,
    destination: sqlite3.Connection,
    label: str,
    progress=None,
) -> None:
    try:
        source.backup(destination, pages=256, progress=progress, sleep=0.05)
        _validate_astra_database(destination, label)
    except BackupError:
        raise
    except sqlite3.Error as exc:
        raise BackupError(f"Could not create {label} database: {exc}") from None


def _remove_database_files(path: Path) -> None:
    """Remove a failed new database and SQLite sidecars without masking its error."""
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        with suppress(OSError):
            candidate.unlink(missing_ok=True)


def create_backup(source_path: Path, destination_path: Path) -> Path:
    """Write one verified, standalone snapshot without copying SQLite sidecars."""
    source_path = _resolve_path(source_path, "source")
    destination_path = _resolve_path(destination_path, "destination")
    _distinct_paths(source_path, destination_path)
    source = _readonly_database(source_path, "Source")
    destination = None
    try:
        destination = _create_exclusive_database(destination_path)
        _online_copy(source, destination, "Backup")
    except Exception:
        if destination is not None:
            with suppress(sqlite3.Error):
                destination.close()
            _remove_database_files(destination_path)
        raise
    finally:
        source.close()
        if destination is not None:
            destination.close()
    return destination_path


def restore_backup(backup_path: Path, destination_path: Path) -> Path:
    """Restore a verified snapshot to a new database file, never over the active DB."""
    backup_path = _resolve_path(backup_path, "backup")
    destination_path = _resolve_path(destination_path, "destination")
    _distinct_paths(backup_path, destination_path)
    source = _readonly_database(backup_path, "Backup")
    destination = None
    destination_created = False
    try:
        destination = _create_exclusive_database(destination_path)
        destination_created = True
        _online_copy(source, destination, "Restored")
        destination.close()
        destination = None
        # Open through Astra so supported older schemas are migrated before the CLI
        # reports success. The target is always new, so migration failure is reversible.
        restored = connect(destination_path)
        try:
            _validate_astra_database(restored, "Restored")
        finally:
            restored.close()
    except Exception:
        if destination is not None:
            with suppress(sqlite3.Error):
                destination.close()
        if destination_created:
            _remove_database_files(destination_path)
        raise
    finally:
        source.close()
        if destination is not None:
            destination.close()
    return destination_path
