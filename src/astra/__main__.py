from __future__ import annotations

import argparse
import getpass

from .db import SchemaMigrationRefused, connect, database_path
from .service import AstraService
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


def _run(args):
    if args.command == "init-owner":
        password = getpass.getpass("New owner password: ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise SystemExit("Passwords did not match.")
        db = connect()
        try:
            user = AstraService(db).create_initial_owner(args.email, args.name, password)
            print(f"Created owner {user['email']} in {database_path()}")
        finally:
            db.close()
    else:
        serve(args.host, args.port)


if __name__ == "__main__":
    main()
