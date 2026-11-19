"""Which of the server's encrypted backups to keep: 7 daily, 4 weekly, 3 monthly.

Policy (Aly, 2026-09-20; runbook stage 11). The nightly script (deploy/backup/astra-backup)
writes `astra-<stamp>.sqlite3.age` and, when there are uploaded files,
`uploads-<stamp>.tar.age`, with stamp YYYYMMDDTHHMMSSZ in UTC. A stamp is kept when its
database backup is the newest of one of the 7 most recent days, 4 most recent ISO weeks or
3 most recent months that have a backup. Counting days that have a backup, not calendar
days, means nights the backup failed never cost a good copy, and the newest backup is
always kept. As in restic's --keep-daily/--keep-weekly/--keep-monthly, the current week and
month count among the 4 and the 3, so the oldest copy kept is the last one of the month
before last (on 4 February, the one of 31 December). The uploads archive of a stamp goes with its database backup.

Only files with exactly those names, regular files directly in the folder, are ever
deleted. Anything else (an unfinished `.part`, a plaintext copy, an uploads archive with no
database backup of its stamp, a symlink) is reported and left alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

KEEP_DAILY = 7
KEEP_WEEKLY = 4
KEEP_MONTHLY = 3

_NAME = re.compile(r"(?P<kind>astra|uploads)-(?P<stamp>[0-9]{8}T[0-9]{6}Z)\.(?P<ext>sqlite3|tar)\.age")
_EXTENSION = {"astra": "sqlite3", "uploads": "tar"}


@dataclass
class RetentionPlan:
    keep: list[str] = field(default_factory=list)
    delete: list[str] = field(default_factory=list)
    left_alone: list[tuple[str, str]] = field(default_factory=list)  # (name, why)


def _stamp(text: str) -> datetime | None:
    try:
        return datetime.strptime(text, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _newest_per_period(stamps: list[datetime], period, count: int) -> set[datetime]:
    """The newest stamp of each of the `count` most recent periods that have one."""
    kept: dict[object, datetime] = {}
    for stamp in sorted(stamps, reverse=True):
        key = period(stamp)
        if key not in kept:
            if len(kept) == count:
                break
            kept[key] = stamp
    return set(kept.values())


def plan_retention(names: list[str], now: datetime | None = None) -> RetentionPlan:
    """A backup stamped more than a day after `now` (a clock that was wrong when it was
    taken) is left alone and holds no place, so it can never push a real backup out."""
    plan = RetentionPlan()
    latest = (now or datetime.now(timezone.utc)) + timedelta(days=1)
    databases: dict[datetime, str] = {}
    archives: dict[datetime, str] = {}
    for name in sorted(names):
        match = _NAME.fullmatch(name)
        stamp = _stamp(match["stamp"]) if match else None
        if not match or match["ext"] != _EXTENSION[match["kind"]] or stamp is None:
            plan.left_alone.append((name, "not a backup name this job writes"))
            continue
        if stamp > latest:
            plan.left_alone.append((name, "dated in the future; check the server's clock"))
            continue
        (databases if match["kind"] == "astra" else archives)[stamp] = name
    stamps = list(databases)
    kept = (_newest_per_period(stamps, lambda s: s.date(), KEEP_DAILY)
            | _newest_per_period(stamps, lambda s: s.isocalendar()[:2], KEEP_WEEKLY)
            | _newest_per_period(stamps, lambda s: (s.year, s.month), KEEP_MONTHLY))
    for stamp, name in sorted(databases.items()):
        (plan.keep if stamp in kept else plan.delete).append(name)
    for stamp, name in sorted(archives.items()):
        if stamp not in databases:
            plan.left_alone.append((name, "no database backup with the same stamp"))
        else:
            (plan.keep if stamp in kept else plan.delete).append(name)
    return plan


def prune_backups(folder: Path, *, dry_run: bool = False, now: datetime | None = None) -> tuple[RetentionPlan, list[tuple[str, str]]]:
    """Apply the plan to a folder. Returns the plan and the deletions that failed."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"No backup folder at {folder}.")
    regular, others = [], []
    for entry in folder.iterdir():
        (regular if entry.is_file() and not entry.is_symlink() else others).append(entry.name)
    plan = plan_retention(regular, now)
    plan.left_alone.extend((name, "not a regular file") for name in sorted(others))
    failed: list[tuple[str, str]] = []
    if not dry_run:
        for name in plan.delete:
            try:
                (folder / name).unlink()
            except OSError as exc:
                failed.append((name, exc.strerror or type(exc).__name__))
    return plan, failed
