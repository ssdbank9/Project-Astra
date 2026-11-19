"""Low-frequency in-process delivery for the App Owner's daily digest."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .db import connect
from .service import AstraService


_LOG = logging.getLogger("astra.daily_digest")


def seconds_until_next_digest(now: datetime, delivery_time: str, timezone_name: str) -> float:
    """Return the wait until the next local delivery time, never a polling interval.

    Times are compared as UTC instants. Python compares two datetimes that share a tzinfo by
    their wall-clock reading, so on the night clocks fall back a delivery time already passed
    in the repeated hour still looked ahead and the wait came out as 0, spinning the loop
    (F9HBSJ). Both readings of the delivery time (fold 0 and 1) are candidates: in the repeated
    hour that wakes the scheduler at the second 01:30 too, so a server that was down for the
    first one still sends that day's summary (an extra wake finds it "already_sent"); in the
    skipped spring hour the fold-1 reading falls before the jump (one "not_due" wake) and the
    fold-0 reading after it, at the delivery time plus the gap (02:30 in New York sends at
    03:30), when run_due_daily_digests finds the local time past the delivery time, as before
    this change. The result is always above zero.
    """
    if now.tzinfo is None:
        raise ValueError("Scheduler clock must include a timezone.")
    zone = ZoneInfo(timezone_name)
    now_utc = now.astimezone(timezone.utc)
    local_date = now_utc.astimezone(zone).date()
    hour, minute = (int(part) for part in delivery_time.split(":"))
    candidates = [
        datetime.combine(local_date + timedelta(days=offset), time(hour, minute, fold=fold),
                         tzinfo=zone).astimezone(timezone.utc)
        for offset in (0, 1, 2) for fold in (0, 1)
    ]
    target = min(candidate for candidate in candidates if candidate > now_utc)
    return (target - now_utc).total_seconds()


class DailyDigestScheduler:
    """Own one sleeping thread; daily delivery is idempotent in SQLite."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._stop = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._run, name="astra-daily-digest", daemon=True)
        self._thread.start()

    def wake(self) -> None:
        """Re-read settings after the primary owner changes the delivery policy."""
        self._wake.set()

    def stop(self) -> None:
        self._stop = True
        self._wake.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def _settings(self) -> dict:
        db = connect(self.db_path)
        try:
            row = db.execute("SELECT enabled,delivery_time,timezone FROM daily_digest_settings WHERE id=1").fetchone()
            if row:
                return {"enabled": bool(row["enabled"]), "delivery_time": row["delivery_time"],
                        "timezone": row["timezone"]}
            return {"enabled": True, "delivery_time": "09:00", "timezone": AstraService.DEFAULT_TIMEZONE}
        finally:
            db.close()

    def _deliver_if_due(self) -> None:
        db = connect(self.db_path)
        try:
            AstraService(db).run_due_daily_digests()
        finally:
            db.close()

    def _run(self) -> None:
        while not self._stop:
            try:
                self._deliver_if_due()
                settings = self._settings()
                delay = seconds_until_next_digest(datetime.now(timezone.utc),
                                                  settings["delivery_time"], settings["timezone"])
            except Exception:
                _LOG.exception("Daily summary check failed; it will retry in one hour.")
                delay = 3600
            self._wake.wait(timeout=delay)
            self._wake.clear()
