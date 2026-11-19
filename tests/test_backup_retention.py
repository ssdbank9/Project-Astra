"""The server keeps 7 daily, 4 weekly and 3 monthly encrypted backups (runbook stage 11)."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from astra.backup_retention import plan_retention, prune_backups


def stamp(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%SZ")


def database(moment: datetime) -> str:
    return f"astra-{stamp(moment)}.sqlite3.age"


def archive(moment: datetime) -> str:
    return f"uploads-{stamp(moment)}.tar.age"


def nightly(start: datetime, nights: int, every: int = 1) -> list[datetime]:
    return [start + timedelta(days=day) for day in range(0, nights, every)]


START = datetime(2025, 1, 1, 21, 30, 5, tzinfo=timezone.utc)


class RetentionPlanTests(unittest.TestCase):
    def kept_moments(self, moments):
        plan = plan_retention([database(m) for m in moments])
        return sorted(m for m in moments if database(m) in plan.keep), plan

    def test_a_year_of_nights_keeps_7_daily_4_weekly_3_monthly(self):
        moments = nightly(START, 365)  # 2025-01-01 .. 2025-12-31
        kept, plan = self.kept_moments(moments)
        newest = moments[-1]
        # The 7 newest nights are all kept.
        self.assertEqual(kept[-7:], moments[-7:])
        # One per ISO week for the 4 newest weeks: the newest night of each.
        weeks = {m.isocalendar()[:2] for m in kept}
        for week_start in range(4):
            self.assertIn((newest - timedelta(weeks=week_start)).isocalendar()[:2], weeks)
        # The newest night of each of the 3 newest months: Oct 31, Nov 30, Dec 31.
        for month, day in ((10, 31), (11, 30), (12, 31)):
            self.assertIn(START.replace(month=month, day=day), kept)
        self.assertLessEqual(len(kept), 7 + 4 + 3)
        self.assertEqual(min(kept), START.replace(month=10, day=31))
        self.assertEqual(len(plan.keep) + len(plan.delete), 365)
        self.assertEqual(plan.left_alone, [])

    def test_nights_without_a_backup_never_cost_a_good_copy(self):
        # A backup only every third night: the 7 newest backups are still all kept,
        # because days with a backup are counted, not calendar days.
        moments = nightly(START, 90, every=3)
        kept, _ = self.kept_moments(moments)
        self.assertEqual(kept[-7:], moments[-7:])
        # After a long outage nothing is deleted just for being old.
        kept, plan = self.kept_moments(nightly(START, 5))
        self.assertEqual(len(kept), 5)
        self.assertEqual(plan.delete, [])

    def test_the_newest_backup_of_a_day_is_the_one_kept(self):
        early, late = START.replace(hour=1), START.replace(hour=23)
        kept, plan = self.kept_moments([early, late])
        self.assertEqual(kept, [late])
        self.assertEqual(plan.delete, [database(early)])

    def test_an_uploads_archive_goes_with_its_database_backup(self):
        moments = nightly(START, 120)
        names = [database(m) for m in moments] + [archive(m) for m in moments]
        plan = plan_retention(names)
        kept_databases = {n[len("astra-"):-len(".sqlite3.age")] for n in plan.keep if n.startswith("astra-")}
        kept_archives = {n[len("uploads-"):-len(".tar.age")] for n in plan.keep if n.startswith("uploads-")}
        self.assertEqual(kept_databases, kept_archives)
        self.assertEqual(len(plan.keep) + len(plan.delete), 240)

    def test_anything_else_is_left_alone(self):
        good = database(START)
        others = [
            f"astra-{stamp(START)}.sqlite3",           # a plaintext copy
            f"astra-{stamp(START)}.sqlite3.age.part",  # an unfinished file
            f"uploads-{stamp(START)}.tar.age.part",
            "astra-20271301T000000Z.sqlite3.age",      # month 13
            f"astra-{stamp(START)}.tar.age",           # wrong kind of file for the name
            f"uploads-{stamp(START)}.sqlite3.age",
            archive(START - timedelta(days=400)),     # no database backup of its stamp
            "notes.txt", ".astra-20270101T000000Z.sqlite3.age",
            database(START + timedelta(days=3)),      # dated in the future (a wrong clock)
            archive(START + timedelta(days=3)),
        ]
        # "now" is START: a stamp more than a day later is left alone.
        plan = plan_retention([good, *others], now=START)
        self.assertEqual(plan.keep, [good])
        self.assertEqual(plan.delete, [])
        self.assertEqual(sorted(name for name, _ in plan.left_alone), sorted(others))
        self.assertIn((database(START + timedelta(days=3)), "dated in the future; check the server's clock"),
                      plan.left_alone)

    def test_a_backup_from_a_wrong_clock_never_pushes_a_real_one_out(self):
        moments = nightly(START, 30)
        future = START + timedelta(days=36500)
        plan = plan_retention([database(m) for m in moments] + [database(future)], now=moments[-1])
        kept = [m for m in moments if database(m) in plan.keep]
        self.assertEqual(kept[-7:], moments[-7:])
        self.assertNotIn(database(future), plan.keep + plan.delete)


class PruneFolderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.moments = nightly(START, 60)
        for moment in self.moments:
            (self.folder / database(moment)).write_bytes(b"encrypted database")
            (self.folder / archive(moment)).write_bytes(b"encrypted files")
        (self.folder / "astra-20250101T000000Z.sqlite3.age.part").write_bytes(b"unfinished")
        (self.folder / "subfolder").mkdir()

    def names(self):
        return sorted(entry.name for entry in self.folder.iterdir())

    def test_prune_deletes_exactly_the_planned_files(self):
        before = self.names()
        plan, failed = prune_backups(self.folder)
        self.assertEqual(failed, [])
        self.assertTrue(plan.delete)
        self.assertEqual(self.names(), sorted(set(before) - set(plan.delete)))
        self.assertIn(database(self.moments[-1]), self.names())
        self.assertIn("astra-20250101T000000Z.sqlite3.age.part", self.names())
        self.assertIn("subfolder", self.names())
        self.assertIn(("subfolder", "not a regular file"), plan.left_alone)
        # A second run has nothing more to delete.
        again, _ = prune_backups(self.folder)
        self.assertEqual(again.delete, [])

    def test_a_dry_run_deletes_nothing(self):
        before = self.names()
        plan, failed = prune_backups(self.folder, dry_run=True)
        self.assertTrue(plan.delete)
        self.assertEqual((self.names(), failed), (before, []))

    def test_a_symlink_is_never_followed_or_deleted(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        target = Path(outside.name) / database(START - timedelta(days=900))
        target.write_bytes(b"not ours")
        link = self.folder / database(START - timedelta(days=800))
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are not available here")
        plan, _ = prune_backups(self.folder)
        self.assertNotIn(link.name, plan.delete)
        self.assertTrue(link.is_symlink() and target.exists())

    def test_a_failed_deletion_is_reported_and_the_rest_go_ahead(self):
        plan, _ = prune_backups(self.folder, dry_run=True)
        stuck = plan.delete[0]
        real_unlink = Path.unlink

        def unlink(path, *args, **kwargs):
            if path.name == stuck:
                raise PermissionError(13, "Permission denied")
            return real_unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", unlink):
            _, failed = prune_backups(self.folder)
        self.assertEqual(failed, [(stuck, "Permission denied")])
        self.assertEqual(set(self.names()) & set(plan.delete), {stuck})

    def test_the_cli_prunes_reports_and_fails_on_a_missing_folder(self):
        from astra.__main__ import main

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(["backup-prune", "--dir", str(self.folder), "--dry-run"])
        self.assertIn("Would delete " + database(self.moments[0]), out.getvalue())
        self.assertIn("Left alone: astra-20250101T000000Z.sqlite3.age.part", out.getvalue())
        self.assertIn("policy: 7 daily, 4 weekly, 3 monthly", out.getvalue())
        self.assertIn(database(self.moments[0]), self.names())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(["backup-prune", "--dir", str(self.folder)])
        self.assertIn("Deleted " + database(self.moments[0]), out.getvalue())
        self.assertNotIn(database(self.moments[0]), self.names())
        with self.assertRaises(SystemExit) as stopped:
            main(["backup-prune", "--dir", str(self.folder / "missing")])
        self.assertIn("No backup folder", str(stopped.exception.code))

    def test_the_cli_exits_1_when_a_file_could_not_be_deleted(self):
        from astra.__main__ import main

        plan, _ = prune_backups(self.folder, dry_run=True)
        real_unlink = Path.unlink

        def unlink(path, *args, **kwargs):
            if path.name == plan.delete[0]:
                raise PermissionError(13, "Permission denied")
            return real_unlink(path, *args, **kwargs)

        out = io.StringIO()
        with patch.object(Path, "unlink", unlink), contextlib.redirect_stdout(out), \
                self.assertRaises(SystemExit) as stopped:
            main(["backup-prune", "--dir", str(self.folder)])
        self.assertEqual(stopped.exception.code, 1)
        self.assertIn(f"FAILED to delete {plan.delete[0]}: Permission denied", out.getvalue())
        self.assertNotIn(f"Deleted {plan.delete[0]}", out.getvalue())

    def test_a_year_of_nightly_runs_never_keeps_more_than_14_or_loses_the_newest_week(self):
        folder = Path(tempfile.mkdtemp(dir=self.temp.name))
        for night, moment in enumerate(nightly(START, 400)):
            (folder / database(moment)).write_bytes(b"x")
            prune_backups(folder, now=moment)
            kept = sorted(entry.name for entry in folder.iterdir())
            self.assertLessEqual(len(kept), 14)
            for recent in nightly(START, night + 1)[-7:]:
                self.assertIn(database(recent), kept)
        # The last night is 2026-02-04. The current month counts as one of the three (as in
        # restic's --keep-monthly), so the oldest copy is the last one of December 2025.
        self.assertEqual(nightly(START, 400)[-1].date().isoformat(), "2026-02-04")
        self.assertEqual(min(kept), database(datetime(2025, 12, 31, 21, 30, 5, tzinfo=timezone.utc)))
        self.assertIn(database(datetime(2026, 1, 31, 21, 30, 5, tzinfo=timezone.utc)), kept)


if __name__ == "__main__":
    unittest.main()
