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
    """Return the wait until the next local delivery time, never a polling interval."""
    if now.tzinfo is None:
        raise ValueError("Scheduler clock must include a timezone.")
    zone = ZoneInfo(timezone_name)
    local_now = now.astimezone(zone)
    hour, minute = (int(part) for part in delivery_time.split(":"))
    target = datetime.combine(local_now.date(), time(hour, minute), tzinfo=zone)
    if target <= local_now:
        target = datetime.combine(local_now.date() + timedelta(days=1), time(hour, minute), tzinfo=zone)
    return max(0.0, (target.astimezone(timezone.utc) - now.astimezone(timezone.utc)).total_seconds())


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
