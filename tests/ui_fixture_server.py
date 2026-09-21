from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True
os.environ["ASTRA_HOME"] = str(ROOT / "tmp_ui_accept")

from astra.db import connect  # noqa: E402
from astra.service import AstraService  # noqa: E402
from astra.web import serve  # noqa: E402


def prepare_fixture() -> None:
    db = connect()
    try:
        service = AstraService(db)
        if service.owner_exists():
            return
        owner = service.create_initial_owner(
            "owner@example.org", "Astra Test Owner", "correct horse battery"
        )
        project = service.create_project(owner, "Browser Acceptance")
        first = service.create_task(owner, {
            "project_id": project["id"],
            "title": "Approve foundation plan",
            "status": "in_progress",
            "due_date": "2026-09-18",
            "criticality": "high",
        })
        service.create_task(owner, {
            "project_id": project["id"],
            "title": "Begin implementation",
            "due_date": "2026-09-25",
            "criticality": "normal",
            "predecessor_task_id": first["id"],
        })
    finally:
        db.close()


if __name__ == "__main__":
    prepare_fixture()
    serve("127.0.0.1", 8766)
