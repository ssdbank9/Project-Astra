from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from astra import __main__ as cli
from astra.daily_digest import seconds_until_next_digest
from astra.db import connect
from astra.service import AstraService, Forbidden


class DailyDigestServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect(Path(self.temp.name) / "digest.sqlite3")
        self.addCleanup(self.db.close)
        self.service = AstraService(self.db)
        self.owner = self.service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")

    def project(self, name="Digest project"):
        return self.service.create_project(self.owner, name, timezone_name="Asia/Karachi")

    def task(self, project, title, due_date=None, status="assigned", **extra):
        return self.service.create_task(self.owner, {
            "project_id": project["id"], "title": title, "due_date": due_date,
            "status": status, **extra,
        })

    def test_settings_are_primary_owner_only_and_default_to_daily_at_nine(self):
        settings = self.service.get_daily_digest_settings(self.owner)
        self.assertEqual(settings["delivery_time"], "09:00")
        self.assertTrue(settings["enabled"])
        self.assertEqual(settings["timezone"], "Asia/Karachi")

        secondary = self.service.create_user(
            self.owner, "secondary@example.org", "Secondary", "secondary password safe", "member"
        )
        secondary = self.service.grant_secondary_owner(self.owner, secondary["id"], "Digest permission check")
        with self.assertRaises(Forbidden):
            self.service.update_daily_digest_settings(secondary, enabled=False, delivery_time="10:15", timezone_name="America/Chicago")
        with self.assertRaises(Forbidden):
            self.service.get_daily_digest_settings(secondary)

        saved = self.service.update_daily_digest_settings(self.owner, enabled=False, delivery_time="10:15", timezone_name="America/Chicago")
        self.assertEqual((saved["enabled"], saved["delivery_time"]), (False, "10:15"))
        self.assertEqual(saved["timezone"], "America/Chicago")
        with self.assertRaisesRegex(ValueError, "valid time zone"):
            self.service.update_daily_digest_settings(self.owner, enabled=True, delivery_time="10:15", timezone_name="not/a-zone")

    def test_digest_groups_dates_reviews_checkpoints_and_next_actions(self):
        project = self.project()
        overdue = self.task(project, "Overdue task", "2026-10-14", next_action_note="Call the supplier")
        self.db.execute("UPDATE tasks SET next_action_note=? WHERE id=?", ("Call the supplier", overdue["id"]))
        today = self.task(project, "Due today", "2026-10-15")
        soon = self.task(project, "Due this week", "2026-10-20")
        later = self.task(project, "Due this month", "2026-11-05")
        review = self.task(project, "Awaiting review", "2026-10-22", status="in_progress")
        self.service.submit_task(self.owner, review["id"], "Ready for review")
        held = self.task(project, "Checkpoint task", "2026-10-31", status="in_progress")
        self.service.set_on_hold(self.owner, held["id"], "Waiting for approval", "2026-10-18", self.owner["id"])

        digest = self.service.build_daily_digest(
            self.owner, digest_date="2026-10-15",
            now=datetime(2026, 10, 15, 4, 0, tzinfo=timezone.utc),  # 09:00 in Asia/Karachi
        )
        self.assertEqual(digest["date"], "2026-10-15")
        self.assertEqual({item["id"] for item in digest["sections"]["overdue"]}, {overdue["id"]})
        self.assertEqual({item["id"] for item in digest["sections"]["today"]}, {today["id"]})
        self.assertEqual({item["id"] for item in digest["sections"]["next_7_days"]}, {soon["id"], review["id"]})
        self.assertEqual({item["id"] for item in digest["sections"]["next_30_days"]}, {later["id"], held["id"]})
        self.assertEqual([item["id"] for item in digest["sections"]["reviews"]], [review["id"]])
        self.assertEqual([item["task_id"] for item in digest["sections"]["checkpoints"]], [held["id"]])
        self.assertEqual(digest["sections"]["overdue"][0]["next_action"], "Call the supplier")

    def test_digest_is_not_due_before_owner_time_and_is_idempotent_after_due(self):
        project = self.project()
        self.task(project, "Today's item", "2026-10-15")
        before = datetime(2026, 10, 15, 3, 59, tzinfo=timezone.utc)  # 08:59 in Asia/Karachi
        due = datetime(2026, 10, 15, 4, 0, tzinfo=timezone.utc)  # 09:00 in Asia/Karachi

        self.assertEqual(self.service.run_due_daily_digests(before)["created"], 0)
        self.assertEqual(self.service.run_due_daily_digests(due)["created"], 1)
        self.assertEqual(self.service.run_due_daily_digests(due)["created"], 0)
        runs = self.db.execute("SELECT COUNT(*) n FROM daily_digest_runs").fetchone()["n"]
        notes = self.db.execute(
            "SELECT COUNT(*) n FROM notifications WHERE kind='daily_digest'"
        ).fetchone()["n"]
        self.assertEqual((runs, notes), (1, 1))
        run = self.db.execute("SELECT payload_json FROM daily_digest_runs").fetchone()
        self.assertIn("Today's item", json.loads(run["payload_json"])["sections"]["today"][0]["title"])
        self.assertEqual(self.service.get_daily_digest(self.owner, "2026-10-15")["date"], "2026-10-15")

    def test_delivery_clock_follows_the_owner_selected_time_zone(self):
        self.service.update_daily_digest_settings(
            self.owner, enabled=True, delivery_time="09:00", timezone_name="America/Chicago",
        )
        before = datetime(2026, 10, 15, 13, 59, tzinfo=timezone.utc)  # 08:59 CDT
        due = datetime(2026, 10, 15, 14, 0, tzinfo=timezone.utc)  # 09:00 CDT
        self.assertEqual(self.service.run_due_daily_digests(before)["created"], 0)
        self.assertEqual(self.service.run_due_daily_digests(due)["created"], 1)
        run = self.db.execute("SELECT payload_json FROM daily_digest_runs").fetchone()
        self.assertEqual(json.loads(run["payload_json"])["timezone"], "America/Chicago")

    def test_new_primary_owner_inherits_the_app_daily_summary_schedule(self):
        successor = self.service.create_user(
            self.owner, "successor@example.org", "Successor", "successor password safe", "member",
        )
        self.service.grant_secondary_owner(self.owner, successor["id"], "Transfer behavior test")
        self.service.update_daily_digest_settings(
            self.owner, enabled=True, delivery_time="08:45", timezone_name="America/Chicago",
        )

        self.service.transfer_primary_owner("successor@example.org", {"via": "test"})
        current_owner = dict(self.db.execute(
            "SELECT * FROM users WHERE email='successor@example.org'"
        ).fetchone())
        settings = self.service.get_daily_digest_settings(current_owner)
        self.assertEqual((settings["delivery_time"], settings["timezone"]), ("08:45", "America/Chicago"))

    def test_disabled_digest_skips_delivery_without_changing_tasks_or_events(self):
        project = self.project()
        task = self.task(project, "Keep this task", "2026-10-15")
        before_events = self.db.execute("SELECT COUNT(*) n FROM task_events").fetchone()["n"]
        self.service.update_daily_digest_settings(self.owner, enabled=False, delivery_time="09:00", timezone_name="Asia/Karachi")

        result = self.service.run_due_daily_digests(datetime(2026, 10, 15, 5, 0, tzinfo=timezone.utc))

        self.assertEqual(result["created"], 0)
        self.assertEqual(self.service.get_task(self.owner, task["id"])["title"], "Keep this task")
        self.assertEqual(self.db.execute("SELECT COUNT(*) n FROM task_events").fetchone()["n"], before_events)
        self.assertEqual(self.db.execute("SELECT COUNT(*) n FROM daily_digest_runs").fetchone()["n"], 0)

    def test_scheduler_sleeps_until_next_daily_delivery_instead_of_polling(self):
        before = datetime(2026, 10, 15, 3, 59, tzinfo=timezone.utc)
        due = datetime(2026, 10, 15, 4, 0, tzinfo=timezone.utc)
        self.assertEqual(seconds_until_next_digest(before, "09:00", "Asia/Karachi"), 60)
        self.assertEqual(seconds_until_next_digest(due, "09:00", "Asia/Karachi"), 24 * 60 * 60)

    def test_the_wait_is_never_zero_in_the_repeated_hour_when_clocks_fall_back(self):
        # F9HBSJ: New York falls back on 2026-11-01 at 06:00 UTC, so 01:00-02:00 local happens
        # twice. 01:30 first happens at 05:30 UTC (EDT) and again at 06:30 UTC (EST).
        zone = "America/New_York"
        self.assertEqual(seconds_until_next_digest(
            datetime(2026, 11, 1, 6, 10, tzinfo=timezone.utc), "01:30", zone), 20 * 60)
        self.assertEqual(seconds_until_next_digest(
            datetime(2026, 11, 1, 5, 10, tzinfo=timezone.utc), "01:30", zone), 20 * 60)
        # After the second 01:30 the next one is the next day's (01:30 EST = 06:30 UTC).
        self.assertEqual(seconds_until_next_digest(
            datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc), "01:30", zone), 24 * 60 * 60)
        start = datetime(2026, 11, 1, 3, 0, tzinfo=timezone.utc)
        for minute in range(0, 6 * 60):
            now = start + timedelta(minutes=minute)
            for delivery in ("00:30", "01:00", "01:30", "01:59", "02:00", "02:30"):
                with self.subTest(now=now.isoformat(), delivery=delivery):
                    self.assertGreater(seconds_until_next_digest(now, delivery, zone), 0)

    def test_the_wait_is_never_zero_around_the_skipped_spring_hour(self):
        # New York springs forward on 2026-03-08 at 07:00 UTC: 02:00-03:00 local never happens.
        zone = "America/New_York"
        start = datetime(2026, 3, 8, 4, 0, tzinfo=timezone.utc)
        for minute in range(0, 6 * 60):
            now = start + timedelta(minutes=minute)
            for delivery in ("01:30", "02:00", "02:30", "03:00", "03:30"):
                with self.subTest(now=now.isoformat(), delivery=delivery):
                    wait = seconds_until_next_digest(now, delivery, zone)
                    self.assertGreater(wait, 0)
                    self.assertLessEqual(wait, 25 * 60 * 60)

    def run_scheduler(self, start, hours, delivery, zone):
        """Drive the scheduler loop's two calls on a simulated clock; return the wake times."""
        self.service.update_daily_digest_settings(self.owner, enabled=True, delivery_time=delivery,
                                                  timezone_name=zone)
        now, end, wakes = start, start + timedelta(hours=hours), []
        while now < end:
            wakes.append(now)
            self.assertLess(len(wakes), 20, "the scheduler loop is spinning")
            self.service.run_due_daily_digests(now)
            now = now + timedelta(seconds=seconds_until_next_digest(now, delivery, zone))
        return wakes

    def sent_dates(self):
        return [row["digest_date"] for row in self.db.execute(
            "SELECT digest_date FROM daily_digest_runs ORDER BY digest_date").fetchall()]

    def test_the_scheduler_sends_one_summary_a_day_across_the_fall_back_night(self):
        self.run_scheduler(datetime(2026, 10, 31, 4, 0, tzinfo=timezone.utc), 72, "01:30",
                           "America/New_York")
        self.assertEqual(self.sent_dates(), ["2026-10-31", "2026-11-01", "2026-11-02"])

    def test_a_server_down_for_the_first_repeated_hour_still_sends_that_days_summary(self):
        # Started at 01:10 EST (06:10 UTC), after the first 01:30 (05:30 UTC) went by unseen.
        self.run_scheduler(datetime(2026, 11, 1, 6, 10, tzinfo=timezone.utc), 2, "01:30",
                           "America/New_York")
        self.assertEqual(self.sent_dates(), ["2026-11-01"])

    def test_the_scheduler_sends_one_summary_a_day_across_the_skipped_spring_hour(self):
        self.run_scheduler(datetime(2026, 3, 7, 5, 0, tzinfo=timezone.utc), 72, "02:30",
                           "America/New_York")
        self.assertEqual(self.sent_dates(), ["2026-03-07", "2026-03-08", "2026-03-09"])

    def test_cli_digest_command_uses_the_saved_database_and_reports_outcome(self):
        output = StringIO()
        cli_home = Path(self.temp.name) / "cli-home"
        cli_db = connect(cli_home / "astra.sqlite3")
        try:
            AstraService(cli_db).create_initial_owner("cli@example.org", "CLI owner", "cli owner password")
        finally:
            cli_db.close()
        with patch.dict(os.environ, {"ASTRA_HOME": str(cli_home)}), \
                patch.object(AstraService, "run_due_daily_digests", return_value={
                    "created": 1, "date": "2026-10-15", "reason": "sent",
                }) as run_due, redirect_stdout(output):
            cli.main(["digest"])
        run_due.assert_called_once()
        self.assertIn("Daily summary: sent (2026-10-15)", output.getvalue())
