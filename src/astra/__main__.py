from __future__ import annotations

import argparse
import getpass
import socket
import sqlite3
import sys

from .db import SchemaMigrationRefused, connect, database_path
from .service import AstraService, Conflict, Forbidden
from .web import serve


def main(argv=None):
    parser = argparse.ArgumentParser(prog="astra")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init-owner", help="Create the one initial owner account")
    init.add_argument("--email", required=True)
    init.add_argument("--name", default="App Owner")
    run = commands.add_parser("serve", help="Run the private Astra hub")
    run.add_argument("--host", default="127.0.0.1")
    run.add_argument("--port", default=8765, type=int)
    # PDDS2D: recovery commands for whoever operates the server. Passwords are read only
    # from the terminal (getpass), never from arguments or the environment.
    transfer = commands.add_parser("transfer-primary", help="Make an active secondary owner the primary owner")
    transfer.add_argument("--to", required=True, metavar="EMAIL")
    transfer.add_argument("--yes", action="store_true", help="Skip typing the email to confirm")
    reset = commands.add_parser("reset-password", help="Set a new password for an active user")
    reset.add_argument("--email", required=True)
    reset.add_argument("--yes", action="store_true", help="Skip typing the email to confirm")
    args = parser.parse_args(argv)
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
    except (sqlite3.OperationalError, OSError) as exc:
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
    else:
        serve(args.host, args.port)


if __name__ == "__main__":
    main()
