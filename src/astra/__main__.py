from __future__ import annotations

import argparse
import getpass
import hashlib
import ipaddress
import os
import re
import secrets
import socket
import sqlite3
import sys
from pathlib import Path

from .attachment_storage import BACKENDS, StorageError, active_backend, storage_named
from .backup import create_backup, restore_backup
from .db import SchemaMigrationRefused, connect, database_path
from .service import AstraService, Conflict, Forbidden
from .web import serve, serve_waitress


def main(argv=None):
    parser = argparse.ArgumentParser(prog="astra")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init-owner", help="Create the one initial owner account")
    init.add_argument("--email", required=True)
    init.add_argument("--name", default="App Owner")
    run = commands.add_parser("serve", help="Run Astra locally or with the hosted Waitress server")
    run.add_argument("--host", default="127.0.0.1", help="IPv4 loopback address only (default: 127.0.0.1)")
    run.add_argument("--port", default=8765, type=int)
    run.add_argument("--waitress", action="store_true", help="Use Waitress for the hosted WSGI application")
    # PDDS2D: recovery commands for whoever operates the server. Passwords are read only
    # from the terminal (getpass), never from arguments or the environment.
    transfer = commands.add_parser("transfer-primary", help="Make an active secondary owner the primary owner")
    transfer.add_argument("--to", required=True, metavar="EMAIL")
    transfer.add_argument("--yes", action="store_true", help="Skip typing the email to confirm")
    reset = commands.add_parser("reset-password", help="Set a new password for an active user")
    reset.add_argument("--email", required=True)
    reset.add_argument("--yes", action="store_true", help="Skip typing the email to confirm")
    backup = commands.add_parser("backup", help="Write a verified, SQLite-consistent database snapshot")
    backup.add_argument(
        "--to", required=True, metavar="FILE",
        help="New backup file; existing files are never replaced",
    )
    restore = commands.add_parser("restore", help="Restore a backup to a new database file")
    restore.add_argument(
        "--from", dest="source", required=True, metavar="FILE", help="Verified Astra backup"
    )
    restore.add_argument(
        "--to", required=True, metavar="FILE",
        help="New database file; existing files are never replaced",
    )
    commands.add_parser("digest", help="Create today's App Owner summary if it is enabled and due")
    # MXY7BG slice 4 (Owner Items 6-7): the upload storage backend and its controlled migration.
    # The object storage key is read from the environment or --settings-file, never an argument.
    storage_status = commands.add_parser("storage-status", help="Show where uploaded files are stored")
    storage_check = commands.add_parser(
        "storage-check", help="Write, read back and delete a test object on a storage backend")
    storage_check.add_argument("--backend", choices=BACKENDS, help="Default: the active backend")
    storage_migrate = commands.add_parser(
        "storage-migrate", help="Copy uploaded files to the active backend, verify each, then switch it over")
    storage_migrate.add_argument("--to", required=True, choices=BACKENDS, help="Must be the active backend")
    storage_prune = commands.add_parser(
        "storage-prune", help="Delete the old copies a migration kept, after verifying the current ones")
    storage_prune.add_argument("--yes", action="store_true", help="Skip typing 'prune' to confirm")
    storage_verify = commands.add_parser(
        "storage-verify", help="Read every uploaded file back and check its size and SHA-256 (after a restore)")
    for storage_command in (storage_status, storage_check, storage_migrate, storage_prune, storage_verify):
        storage_command.add_argument(
            "--settings-file", metavar="FILE",
            help="Read ASTRA_* settings from KEY=VALUE lines, as the service does (for example /etc/astra/storage.env)")
    args = parser.parse_args(argv)
    if args.command == "serve":
        try:
            host_address = ipaddress.ip_address(args.host)
        except ValueError:
            host_address = None
        if not isinstance(host_address, ipaddress.IPv4Address) or not host_address.is_loopback:
            raise SystemExit(
                "Astra only listens on IPv4 loopback; place the approved reverse proxy in front of it."
            )
    try:
        _run(args)
    except SchemaMigrationRefused as exc:
        # The database cannot be upgraded as it stands; the message says what to fix.
        raise SystemExit(str(exc)) from None
    except RuntimeError as exc:
        if "newer Astra version" not in str(exc):
            raise
        raise SystemExit(f"{exc} Upgrade Astra before opening {database_path()}.") from None
    except (ValueError, KeyError, Conflict, Forbidden) as exc:
        # A refusal from the service: one clean line, exit status 1, no traceback.
        raise SystemExit(str(exc).strip("'")) from None
    except (KeyboardInterrupt, EOFError):
        raise SystemExit("Aborted; nothing was changed.") from None
    except StorageError as exc:
        raise SystemExit(f"File storage: {exc}") from None
    except (sqlite3.OperationalError, OSError) as exc:
        if args.command == "serve" and not isinstance(exc, sqlite3.OperationalError):
            # For example the port is in use or the host name does not resolve.
            raise SystemExit(f"Could not start the server on {args.host}:{args.port}: {exc}") from None
        # For example "database is locked" after the busy timeout, or a read-only folder.
        raise SystemExit(f"Could not use the database at {database_path()}: {exc}") from None


def _read_new_password(prompt: str) -> str:
    password = getpass.getpass(prompt)
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords did not match.")
    return password


def _confirm(email: str, skip: bool) -> None:
    if skip:
        return
    typed = input(f"Type {email} to confirm: ")
    if typed.strip().casefold() != email.casefold():
        raise SystemExit("Confirmation did not match; nothing was changed.")


def _interactive() -> bool:
    return sys.stdin.isatty()


def _existing_database():
    """Open the database a recovery command changes, refusing to create one: a missing
    file almost always means ASTRA_HOME is unset or mistyped (review 6)."""
    path = database_path()
    print(f"Database: {path}")
    if not path.is_file():
        raise SystemExit(f"No Astra database at {path}; set ASTRA_HOME.")
    return connect(path)


def _via() -> dict:
    """Where a server command ran, for the audit row."""
    try:
        os_user = getpass.getuser()
    except Exception:  # getuser raises when no login name can be found
        os_user = ""
    return {"via": "cli", "os_user": os_user, "host": socket.gethostname()}


def _load_settings_file(path: str) -> None:
    """Put a settings file's ASTRA_* lines into this process's environment, as systemd's
    EnvironmentFile does for the service, so the object storage key never has to be typed
    on a command line. A line is never echoed back: it may hold the key."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise SystemExit(f"Could not read the settings file {path}: {getattr(exc, 'strerror', None) or type(exc).__name__}") from None
    for number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        name, equals, value = line.partition("=")
        name, value = name.strip(), value.strip()
        if not equals or not re.fullmatch(r"ASTRA_[A-Z0-9_]+", name):
            raise SystemExit(f"{path}, line {number}: expected ASTRA_NAME=value.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[name] = value


def _storage_check(name: str) -> None:
    """Prove a backend works before any real file depends on it: write a small random
    object, read it back, make sure nobody can read it without the key, delete it."""
    storage = storage_named(name)
    data = secrets.token_bytes(1024)
    stored = storage.save([data])
    deleted = False
    try:
        handle = storage.open(stored.key)
        try:
            back = handle.read()
        finally:
            handle.close()
        if (back, stored.size, stored.sha256) != (data, len(data), hashlib.sha256(data).hexdigest()):
            raise SystemExit(f"File storage: the {name} backend returned different bytes than were written.")
        print(f"{name}: wrote a {len(data)}-byte test object, read it back and it matched.")
        for where, status in getattr(storage, "anonymous_reads", lambda key: [])(stored.key):
            if status is None:
                print(f"{name}: could not try a read without the key at {where}; "
                      "check in the OCI console that the bucket is private.")
            elif 200 <= status < 300:
                raise SystemExit(f"File storage: the bucket is PUBLIC: {where} answered a request without the key "
                                 f"(HTTP {status}). Make the bucket private before Astra uses it.")
            else:
                print(f"{name}: a read without the key is refused (HTTP {status}) at {where}.")
    finally:
        # A verdict reached above must survive a delete that fails (a key that may write but
        # not delete): say so on its own line and let the verdict through.
        try:
            storage.delete(stored.key)
            deleted = True
        except OSError as exc:
            print(f"{name}: the test object {stored.key} could not be deleted ({exc}). Delete it by hand.")
    if not deleted:
        raise SystemExit(f"File storage: the {name} backend cannot delete objects, so Astra could not remove a "
                         "file kept there.")
    print(f"{name}: the test object was deleted. The backend is ready.")


def _print_storage_failures(result: dict) -> None:
    for failure in result["failed"]:
        print(f"  FAILED {failure['display_name']} ({failure['attachment_id']}): {failure['error']}")


def _uninterrupted(command):
    """Run a storage command that had begun its work. Ctrl-C then does not mean "nothing was
    changed": the files it had finished stay finished."""
    try:
        return command()
    except KeyboardInterrupt as stop:
        done = getattr(stop, "storage_result", None) or {"failed": []}
        counts = [f"{value} {name}" for name, value in done.items() if type(value) is int]
        if counts:
            print(f"Before it was stopped: {', '.join(counts)}, {len(done['failed'])} failed.")
        _print_storage_failures(done)
        recorded = (f"It could NOT be RECORDED in the owner history ({done['unrecorded']}); note this run by hand."
                    if done.get("unrecorded") else "The owner history shows what was recorded.")
        raise SystemExit("Interrupted. Files already handled stay as they are. Run storage-status to see where "
                         f"things stand, then the same command again to finish. {recorded}") from None


def _run(args):
    if args.command == "init-owner":
        password = _read_new_password("New owner password: ")
        db = connect()
        try:
            user = AstraService(db).create_initial_owner(args.email, args.name, password)
            print(f"Created owner {user['email']} in {database_path()}")
        finally:
            db.close()
    elif args.command == "transfer-primary":
        db = _existing_database()
        try:
            service = AstraService(db)
            old, new = service.check_primary_transfer(args.to)
            print(f"Make {new['display_name']} <{new['email']}> the primary owner.")
            print(f"{old['display_name']} <{old['email']}> stays a secondary owner and is signed out everywhere.")
            _confirm(new["email"], args.yes)
            service.transfer_primary_owner(new["email"], _via())
            print(f"Primary owner is now {new['email']}; {old['email']} remains a secondary owner.")
        finally:
            db.close()
    elif args.command == "reset-password":
        if not _interactive():
            # getpass would fall back to reading (and echoing) stdin, so a password could be piped in.
            raise SystemExit("reset-password needs an interactive terminal.")
        db = _existing_database()
        try:
            service = AstraService(db)
            user = service.check_password_reset(args.email)
            print(f"Reset the password of {user['display_name']} <{user['email']}> ({user['global_role']}); "
                  "they are signed out everywhere.")
            _confirm(user["email"], args.yes)
            password = _read_new_password(f"New password for {user['email']}: ")
            service.reset_password(user["email"], password, _via())
            print(f"Password reset for {user['email']}.")
        finally:
            db.close()
    elif args.command == "backup":
        destination = create_backup(database_path(), Path(args.to))
        print(f"Backup written: {destination} (integrity_check: ok)")
    elif args.command == "restore":
        destination = restore_backup(Path(args.source), Path(args.to))
        print(f"Database restored: {destination} (integrity_check: ok)")
    elif args.command == "digest":
        db = _existing_database()
        try:
            result = AstraService(db).run_due_daily_digests()
            print(f"Daily summary: {result['reason']}" + (f" ({result['date']})" if result.get("date") else ""))
        finally:
            db.close()
    elif args.command in ("storage-status", "storage-check", "storage-migrate", "storage-prune", "storage-verify"):
        if args.settings_file:
            _load_settings_file(args.settings_file)
        if args.command == "storage-check":
            _storage_check(args.backend or active_backend())
            return
        db = _existing_database()
        try:
            service = AstraService(db)
            if args.command == "storage-status":
                status = service.storage_status()
                print(f"Active backend: {status['active']}")
                for row in status["backends"]:
                    kept = f", {row['old_copies_kept']} with an old copy kept" if row["old_copies_kept"] else ""
                    note = "" if row["backend"] == status["active"] else "  (not the active backend: run storage-migrate)"
                    print(f"  {row['backend']}: {row['files']} files, {row['bytes']} bytes{kept}{note}")
                if not status["backends"]:
                    print("  No uploaded files.")
                return
            if args.command == "storage-verify":
                result = service.verify_storage()
                print(f"Verified {result['verified']} uploaded files; {len(result['failed'])} failed.")
                _print_storage_failures(result)
            elif args.command == "storage-migrate":
                result = _uninterrupted(lambda: service.migrate_storage(args.to, _via()))
                print(f"Moved to {args.to}: {result['moved']} copied and verified, {result['restored']} switched back "
                      f"to a kept copy, {result['skipped']} skipped, {len(result['failed'])} failed.")
                _print_storage_failures(result)
                if result["moved"] or result["restored"]:
                    print("The old copies are kept. Check the app, then run storage-prune to delete them.")
            else:
                if not args.yes and input("Type prune to delete the old copies: ").strip() != "prune":
                    raise SystemExit("Confirmation did not match; nothing was changed.")
                result = _uninterrupted(lambda: service.prune_storage(_via()))
                print(f"Old copies removed: {result['pruned']}; {result['skipped']} skipped; "
                      f"{len(result['failed'])} failed.")
                _print_storage_failures(result)
            if result.get("unrecorded"):
                print(f"  NOT RECORDED in the owner history ({result['unrecorded']}). The files are as shown "
                      "above; note this run by hand.")
            if result["failed"] or result.get("unrecorded"):
                raise SystemExit(1)  # nothing was lost: a failed file's row is unchanged
        finally:
            db.close()
    elif args.command == "serve" and args.waitress:
        serve_waitress(args.host, args.port)
    else:
        serve(args.host, args.port)


if __name__ == "__main__":
    main()
