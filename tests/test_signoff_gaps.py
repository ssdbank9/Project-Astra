"""Service-level tests that close the coverage gaps an independent review found on the
tickets sitting in signoff. Each test names its ticket in the docstring and fails if the
behaviour it pins is removed. No HTTP: the web side is covered in test_web.py.

Run on its own with:
    .venv\\Scripts\\python.exe -X utf8 -c "import sys,unittest;sys.path[:0]=['src','tests'];unittest.main(module='test_signoff_gaps',verbosity=2)"
"""
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import astra
from astra import service as service_module
from astra.db import connect
from astra.service import AstraService, Forbidden

APP_JS = Path(astra.__file__).resolve().parent / "static" / "app.js"  # the package under test


class SignoffFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect(Path(self.temp.name) / "signoff.sqlite3")
        self.addCleanup(self.db.close)
        self.service = AstraService(self.db)
        self.owner = self.service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")

    def user(self, key, role="member", project_id=None, project_role=None):
        created = self.service.create_user(
            self.owner, f"{key}@example.org", key.title(), f"{key} password safe", role)
        if project_id and project_role:
            self.service.grant_project_access(self.owner, project_id, created["id"], project_role)
        return created

    def update_task(self, actor, task_id, payload):
        payload = dict(payload)
        payload.setdefault("expected_revision", self.service.get_task(actor, task_id)["revision"])
        return self.service.update_task(actor, task_id, payload)

    def count(self, table, where="", params=()):
        sql = f"SELECT COUNT(*) c FROM {table}" + (f" WHERE {where}" if where else "")
        return self.db.execute(sql, params).fetchone()["c"]


class NotificationInboxGapTests(SignoffFixture):
    """Z24KVH: the durable owner inbox."""

    def test_replaying_the_same_event_id_creates_one_notification_per_owner(self):
        """Z24KVH: _notify_owners with the same event id twice leaves exactly one row per
        recipient (INSERT OR IGNORE on the unique (user_id, event_id) index), and a new
        event id still adds one."""
        deputy = self.user("deputy")
        self.service.grant_secondary_owner(self.owner, deputy["id"], "cover")
        manager = self.user("manager")
        for _ in range(2):
            self.service._notify_owners(manager["id"], "replayed-event", None, "task_updated", "task updated: A")
        rows = self.db.execute(
            "SELECT user_id FROM notifications WHERE event_id='replayed-event' ORDER BY user_id").fetchall()
        self.assertEqual(sorted(r["user_id"] for r in rows), sorted([self.owner["id"], deputy["id"]]))
        self.service._notify_owners(manager["id"], "another-event", None, "task_updated", "task updated: B")
        for who in (self.owner, deputy):
            kinds = [n["summary"] for n in self.service.list_notifications(who) if n["kind"] == "task_updated"]
            self.assertCountEqual(kinds, ["task updated: A", "task updated: B"])

    def test_a_retried_owner_request_notifies_the_owner_once(self):
        """Z24KVH: a Manager who asks for the same Owner action twice (a retry) leaves one
        request and one notice, not two."""
        project = self.service.create_project(self.owner, "Retried")
        manager = self.user("manager", project_id=project["id"], project_role="manager")
        first = self.service.close_project(manager, project["id"], "Done")
        second = self.service.close_project(manager, project["id"], "Done")
        self.assertEqual(first["request"]["id"], second["request"]["id"])
        self.assertEqual(self.count("owner_action_requests", "project_id=?", (project["id"],)), 1)
        notices = [n for n in self.service.list_notifications(self.owner)
                   if n["kind"] == "protected_action_requested"]
        self.assertEqual(len(notices), 1)
        self.assertEqual(self.count("notifications", "kind='protected_action_requested'"), 1)

    def test_list_notifications_returns_newest_first(self):
        """Z24KVH: the inbox lists the newest notification first, whatever order the rows
        were written in."""
        stamps = {"middle": "2026-03-02T09:00:00+00:00", "oldest": "2026-03-01T09:00:00+00:00",
                  "newest": "2026-03-03T09:00:00+00:00"}
        for label, stamp in stamps.items():  # written middle, oldest, newest
            self.service._notify(self.owner["id"], f"event-{label}", None, "task_updated", label, created_at=stamp)
        listed = self.service.list_notifications(self.owner)
        self.assertEqual([n["summary"] for n in listed], ["newest", "middle", "oldest"])
        self.assertEqual([n["created_at"] for n in listed], sorted(stamps.values(), reverse=True))
        unread = self.service.list_notifications(self.owner, unread_only=True)
        self.assertEqual([n["summary"] for n in unread], ["newest", "middle", "oldest"])


class WorkingDaysToDueGapTests(SignoffFixture):
    """XDA2JR: working_days_to_due honours the project's working calendar."""

    TODAY = "2026-09-14"  # a Monday
    DUE = "2026-09-20"    # the Sunday after: seven calendar days, Monday to Sunday inclusive

    def detail(self, task_id):
        with patch.object(AstraService, "_today_in_timezone", staticmethod(lambda tz: self.TODAY)):
            return self.service.task_detail(self.owner, task_id)

    def setUp(self):
        super().setUp()
        self.project = self.service.create_project(self.owner, "Calendar", timezone_name="UTC")
        self.task = self.service.create_task(self.owner, {
            "project_id": self.project["id"], "title": "Due Sunday", "due_date": self.DUE})

    def test_default_calendar_counts_every_day(self):
        """XDA2JR: with the permissive default calendar every day to the due date counts; a
        task with no due date has no count."""
        self.assertEqual(self.detail(self.task["id"])["working_days_to_due"], 7)
        undated = self.service.create_task(self.owner, {"project_id": self.project["id"], "title": "No date"})
        self.assertIsNone(self.detail(undated["id"])["working_days_to_due"])

    def test_non_working_weekdays_are_excluded(self):
        """XDA2JR: a Monday to Friday project drops Saturday and Sunday from the count."""
        self.service.set_working_days(self.owner, self.project["id"], "01234")
        self.assertEqual(self.detail(self.task["id"])["working_days_to_due"], 5)

    def test_a_holiday_is_excluded_on_top_of_the_weekdays(self):
        """XDA2JR: a holiday on a working weekday removes one more day, and a holiday on a
        non-working day removes nothing."""
        self.service.set_working_days(self.owner, self.project["id"], "01234")
        self.service.add_holiday(self.owner, self.project["id"], "2026-09-16", "Wednesday holiday")
        self.assertEqual(self.detail(self.task["id"])["working_days_to_due"], 4)
        self.service.add_holiday(self.owner, self.project["id"], "2026-09-19", "Saturday holiday")
        self.assertEqual(self.detail(self.task["id"])["working_days_to_due"], 4)

    def test_a_holiday_alone_is_excluded_from_the_default_calendar(self):
        """XDA2JR: on the default calendar a holiday still takes a day off the count."""
        self.service.add_holiday(self.owner, self.project["id"], "2026-09-16", "Wednesday holiday")
        self.assertEqual(self.detail(self.task["id"])["working_days_to_due"], 6)


class ScheduleRevisionRecordGapTests(SignoffFixture):
    """JZACMP: an approved schedule proposal leaves a complete record."""

    def test_approved_proposal_records_old_new_actor_and_reason(self):
        """JZACMP: schedule_revised carries the old dates, the new dates, the approving
        actor and the reason; the proposal row records who proposed and decided and why."""
        project = self.service.create_project(self.owner, "Revisions")
        manager = self.user("pm", project_id=project["id"], project_role="manager")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "A", "start_date": "2026-10-01", "due_date": "2026-10-05"})
        proposal = self.service.propose_schedule(manager, task["id"], "2026-10-02", "2026-10-12", "client delay")
        self.service.approve_schedule_proposal(self.owner, proposal["id"], "agreed with the client")

        events = self.service.task_events(self.owner, task["id"])
        proposed = [e for e in events if e["event_type"] == "schedule_proposed"]
        revised = [e for e in events if e["event_type"] == "schedule_revised"]
        self.assertEqual((len(proposed), len(revised)), (1, 1))
        self.assertEqual(proposed[0]["actor_user_id"], manager["id"])
        self.assertEqual(json.loads(proposed[0]["after_json"]), {"start_date": "2026-10-02", "due_date": "2026-10-12"})
        event = revised[0]
        self.assertEqual(event["actor_user_id"], self.owner["id"])
        self.assertEqual(event["actor_name"], "Owner")
        self.assertEqual(event["reason"], "client delay")
        self.assertEqual(json.loads(event["before_json"]), {"start_date": "2026-10-01", "due_date": "2026-10-05"})
        self.assertEqual(json.loads(event["after_json"]), {"start_date": "2026-10-02", "due_date": "2026-10-12"})

        row = self.service.get_schedule_proposal(self.owner, proposal["id"])
        self.assertEqual(row["status"], "approved")
        self.assertEqual((row["start_date"], row["due_date"]), ("2026-10-02", "2026-10-12"))
        self.assertEqual(row["reason"], "client delay")
        self.assertEqual(row["proposed_by"], manager["id"])
        self.assertEqual(row["decided_by"], self.owner["id"])
        self.assertEqual(row["decision_reason"], "agreed with the client")
        self.assertTrue(row["decided_at"])
        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual((current["start_date"], current["due_date"]), ("2026-10-02", "2026-10-12"))


class SubtaskRollupProgressGapTests(SignoffFixture):
    """9R7A87: the sub-task roll-up is a count, never a write to the parent's progress."""

    def test_rollup_counts_do_not_change_a_manual_progress_value(self):
        """9R7A87: re-parenting and completing sub-tasks changes the roll-up counts but
        leaves the parent's manual progress, and a sub-task's own, exactly as set; a parent
        with no progress stays blank."""
        project = self.service.create_project(self.owner, "Progress")
        pid = project["id"]
        manual = self.service.create_task(self.owner, {"project_id": pid, "title": "Manual parent", "progress": 40})
        blank = self.service.create_task(self.owner, {"project_id": pid, "title": "Blank parent"})
        child_a = self.service.create_task(self.owner, {
            "project_id": pid, "title": "A", "parent_task_id": manual["id"], "progress": 10})
        child_b = self.service.create_task(self.owner, {"project_id": pid, "title": "B", "progress": 25})
        child_c = self.service.create_task(self.owner, {"project_id": pid, "title": "C", "parent_task_id": blank["id"]})

        def progress(task_id):
            return self.service.get_task(self.owner, task_id)["progress"]

        before = {t["id"]: progress(t["id"]) for t in (manual, blank, child_a, child_b, child_c)}
        self.assertEqual((before[manual["id"]], before[blank["id"]], before[child_b["id"]]), (40, None, 25))

        self.service.set_parent(self.owner, child_b["id"], manual["id"])
        for child in (child_a, child_b, child_c):
            sub = self.service.submit_task(self.owner, child["id"], "done")
            self.service.accept_submission(self.owner, sub["id"], "ok")

        detail = self.service.task_detail(self.owner, manual["id"])
        self.assertEqual(detail["subtask_rollup"], {"total": 2, "completed": 2})
        self.assertEqual(self.service.task_detail(self.owner, blank["id"])["subtask_rollup"],
                         {"total": 1, "completed": 1})
        after = {t["id"]: progress(t["id"]) for t in (manual, blank, child_a, child_b, child_c)}
        self.assertEqual(after, before)
        listed = {t["id"]: t["progress"] for t in self.service.list_tasks(self.owner, pid)}
        self.assertEqual((listed[manual["id"]], listed[blank["id"]]), (40, None))


class CriticalPathAbandonedGapTests(SignoffFixture):
    """AYW0QC: the critical path leaves out abandoned work as it does cancelled work."""

    def test_critical_path_excludes_abandoned_node(self):
        """AYW0QC: abandoning the middle task of a chain removes it, and the chain it
        carried, from the critical path; before that all three are critical."""
        p = self.service.create_project(self.owner, "CP abandoned")
        a = self.service.create_task(self.owner, {"project_id": p["id"], "title": "A", "start_date": "2026-09-01", "due_date": "2026-09-05"})
        b = self.service.create_task(self.owner, {"project_id": p["id"], "title": "B", "start_date": "2026-09-06", "due_date": "2026-09-08"})
        c = self.service.create_task(self.owner, {"project_id": p["id"], "title": "C", "start_date": "2026-09-09", "due_date": "2026-09-12"})
        self.service.add_task_dependency(self.owner, a["id"], b["id"])
        self.service.add_task_dependency(self.owner, b["id"], c["id"])

        def flags():
            return {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner, p["id"])}

        self.assertTrue(all(flags()[t["id"]] for t in (a, b, c)))
        self.update_task(self.owner, b["id"], {"status": "abandoned", "reason": "dropped"})
        self.assertEqual(self.service.get_task(self.owner, b["id"])["status"], "abandoned")
        cp = flags()
        self.assertFalse(cp[a["id"]] or cp[b["id"]] or cp[c["id"]])


class ProjectHistoryGapTests(SignoffFixture):
    """ZSZ9T2 and 5WZ4A8: what project history shows, and in what order."""

    def test_non_managers_see_the_reopen_but_not_manager_only_kinds(self):
        """ZSZ9T2: after the App Owner reopens a closed project with a reason, a member and a
        viewer see project_reopened (with project_closed), and still not the manager-only kinds."""
        project = self.service.create_project(self.owner, "Reopened")
        pid = project["id"]
        viewer = self.user("viewer", project_id=pid, project_role="viewer")
        member = self.user("member", project_id=pid, project_role="member")
        manager = self.user("manager", project_id=pid, project_role="manager")
        self.service.close_project(self.owner, pid, "Finished")
        self.service.reopen_project(self.owner, pid, "Correction required")
        manager_only = ("import_committed", "protected_action_blocked", "protected_action_requested",
                        "protected_action_approved", "project_budget_changed")
        for kind in manager_only:
            self.service._project_event(pid, self.owner["id"], kind, {"note": "private"}, f"reason for {kind}")
        for key, actor in (("viewer", viewer), ("member", member)):
            with self.subTest(actor=key):
                self.assertFalse(self.service.can_manage_project(actor, pid))
                events = self.service.project_events(actor, pid)
                self.assertCountEqual([e["event_type"] for e in events], ["project_closed", "project_reopened"])
                reopened = next(e for e in events if e["event_type"] == "project_reopened")
                self.assertEqual(reopened["reason"], "Correction required")
                self.assertEqual(reopened["actor_user_id"], self.owner["id"])
        kinds = [e["event_type"] for e in self.service.project_events(manager, pid)]
        for kind in ("project_closed", "project_reopened", *manager_only):
            self.assertIn(kind, kinds)

    def test_project_history_is_ordered_by_time_not_by_insertion(self):
        """5WZ4A8: the service returns project history in time order, oldest first, from the
        occurred_at stamp (the History dialog then shows it newest first, see the next
        test). The changes are written latest first, so neither insertion order, nor id
        order, nor a reversed sort passes."""
        project = self.service.create_project(self.owner, "Ordered")
        pid = project["id"]
        clock = {"now": None}
        with patch.object(service_module, "now_text", lambda: clock["now"]):
            for month in (6, 5, 4, 3, 2, 1):  # written June first, January last
                clock["now"] = f"2026-{month:02d}-01T09:00:00+00:00"
                self.service.set_project_schedule(
                    self.owner, pid, "2026-03-01", f"2026-12-{month:02d}", f"change {month}")
        events = [e for e in self.service.project_events(self.owner, pid)
                  if e["event_type"] == "project_schedule_changed"]
        self.assertEqual([e["reason"] for e in events], [f"change {m}" for m in (1, 2, 3, 4, 5, 6)])
        self.assertEqual([e["occurred_at"] for e in events],
                         [f"2026-{m:02d}-01T09:00:00+00:00" for m in (1, 2, 3, 4, 5, 6)])

    def test_project_history_dialog_shows_newest_first(self):
        """5WZ4A8: the service hands history over oldest first, so the dialog must reverse it
        to list newest first. Removing the reversal fails this."""
        script = APP_JS.read_text(encoding="utf-8")
        start = script.index("async function openProjectHistory")
        body = script[start:script.index("function renderProjectEvent", start)]
        self.assertRegex(body, r"events\.slice\(\)\.reverse\(\)\.map\(renderProjectEvent\)")
        self.assertIn("Newest first", body)


class ChairmanAssignmentScopeGapTests(SignoffFixture):
    """3FQEKB: the Chairman's right to assign is narrow."""

    def test_chairman_assigns_only_and_can_manage_project_is_unchanged(self):
        """3FQEKB: every other edit by the Chairman is refused and changes nothing, an
        assignee change is allowed, and can_manage_project stays False before and after."""
        chair = self.user("chair", role="chairman")
        project = self.service.create_project(self.owner, "Chair scope")
        pid = project["id"]
        member = self.user("member", project_id=pid, project_role="member")
        task = self.service.create_task(self.owner, {"project_id": pid, "title": "Plan"})
        self.assertFalse(self.service.can_manage_project(chair, pid))
        self.assertTrue(self.service.can_assign(chair, pid))
        revision = self.service.get_task(self.owner, task["id"])["revision"]
        for label, body in (
            ("title", {"title": "Renamed"}),
            ("status", {"status": "in_progress", "reason": "go"}),
            ("dates", {"due_date": "2026-12-01", "reason": "later"}),
            ("title beside an assignee", {"title": "Renamed", "owner_user_id": member["id"]}),
            ("no assignee at all", {"reason": "hello"}),
        ):
            with self.subTest(label), self.assertRaises(Forbidden):
                self.service.update_task(chair, task["id"], {**body, "expected_revision": revision})
        with self.assertRaises(Forbidden):
            self.service.confirm_criticality(chair, task["id"], "high", "evidence")
        with self.assertRaises(Forbidden):
            self.service.create_task(chair, {"project_id": pid, "title": "Not allowed"})
        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual((current["revision"], current["title"], current["status"], current["owner_user_id"]),
                         (revision, "Plan", "draft", None))

        assigned = self.service.update_task(chair, task["id"], {
            "owner_user_id": member["id"], "expected_revision": revision, "reason": "Member leads it"})
        self.assertEqual(assigned["owner_user_id"], member["id"])
        self.assertEqual((assigned["title"], assigned["status"]), ("Plan", "draft"))
        self.assertFalse(self.service.can_manage_project(chair, pid))
        permissions = self.service.task_detail(chair, task["id"])["permissions"]
        self.assertEqual((permissions["can_assign"], permissions["assign_only"], permissions["can_edit_ordinary"]),
                         (True, True, False))


class CliUsageErrorGapTests(SignoffFixture):
    """PDDS2D: the astra command line."""

    def test_usage_errors_exit_with_code_two_and_a_usage_line(self):
        """PDDS2D: no command, an unknown option, a missing required option and an unknown
        command all exit with status 2 (argparse's usage-error code, an int), print a usage
        line, and open no database."""
        from astra import __main__ as entry
        home = Path(self.temp.name) / "cli-home"
        cases = ([], ["serve", "--bogus"], ["transfer-primary"], ["reset-password", "--yes"], ["no-such-command"])
        with patch.dict(os.environ, {"ASTRA_HOME": str(home)}):
            for argv in cases:
                with self.subTest(argv=argv):
                    err = io.StringIO()
                    with patch("sys.stderr", err), patch("sys.stdout", new_callable=io.StringIO), \
                            patch.object(entry, "_run") as run, self.assertRaises(SystemExit) as stopped:
                        entry.main(argv)
                    self.assertIs(type(stopped.exception.code), int)
                    self.assertEqual(stopped.exception.code, 2)
                    self.assertRegex(err.getvalue(), r"usage: astra")
                    run.assert_not_called()
        self.assertFalse(home.exists())


class ProjectDateChangeNoticeGapTests(SignoffFixture):
    """XX9RFM: a project date change reaches the other active owners and adds nothing else."""

    def snapshot(self):
        return {
            "project_events": self.count("project_events"),
            "task_events": self.count("task_events"),
            "user_events": self.count("user_events"),
            "owner_action_requests": self.count("owner_action_requests"),
        }

    def inbox(self, user):
        return [n for n in self.service.list_notifications(user) if n["kind"] == "project_schedule_changed"]

    def setUp(self):
        super().setUp()
        self.deputy = self.user("deputy")
        self.service.grant_secondary_owner(self.owner, self.deputy["id"], "cover")
        self.retired = self.user("retired")
        self.service.grant_secondary_owner(self.owner, self.retired["id"], "cover")
        # An owner who has since been deactivated (set directly: the API makes you revoke
        # owner access first, which would make them a non-owner).
        self.db.execute("UPDATE users SET active=0 WHERE id=?", (self.retired["id"],))
        self.chair = self.user("chair", role="chairman")
        self.project = self.service.create_project(self.owner, "Dated")
        self.pid = self.project["id"]
        self.manager = self.user("manager", project_id=self.pid, project_role="manager")

    def test_owner_date_change_notifies_the_other_active_owner_only(self):
        """XX9RFM: the acting owner, the Chairman and a deactivated owner get no notice; the
        other active owner gets exactly one; the only new history row is the existing
        project_schedule_changed event."""
        before = self.snapshot()
        self.service.set_project_schedule(self.owner, self.pid, "2026-03-01", "2026-06-30", "Board approved")
        after = self.snapshot()
        self.assertEqual({k: after[k] - before[k] for k in after},
                         {"project_events": 1, "task_events": 0, "user_events": 0, "owner_action_requests": 0})
        new_row = self.db.execute(
            "SELECT event_type FROM project_events WHERE project_id=? ORDER BY occurred_at DESC, id DESC",
            (self.pid,)).fetchone()
        self.assertEqual(new_row["event_type"], "project_schedule_changed")
        notices = self.inbox(self.deputy)
        self.assertEqual(len(notices), 1)
        self.assertIn("Dated", notices[0]["summary"])
        self.assertIn("2026-06-30", notices[0]["summary"])
        self.assertEqual(notices[0]["actor_user_id"], self.owner["id"])
        for who in (self.owner, self.chair, self.retired, self.manager):
            with self.subTest(who=who["display_name"]):
                self.assertEqual(self.inbox(who), [])
        self.assertEqual(self.count("notifications", "kind='project_schedule_changed'"), 1)

    def test_manager_date_change_notifies_every_active_owner(self):
        """XX9RFM: when a Manager changes the start date, both active owners are told, still
        with one project_schedule_changed row and no other history."""
        self.service.set_project_schedule(self.owner, self.pid, "2026-03-01", "2026-06-30", "Board approved")
        before, owner_notes, deputy_notes = self.snapshot(), len(self.inbox(self.owner)), len(self.inbox(self.deputy))
        self.service.set_project_schedule(self.manager, self.pid, "2026-03-15", "2026-06-30", "Start moved")
        after = self.snapshot()
        self.assertEqual({k: after[k] - before[k] for k in after},
                         {"project_events": 1, "task_events": 0, "user_events": 0, "owner_action_requests": 0})
        self.assertEqual(len(self.inbox(self.owner)), owner_notes + 1)
        self.assertEqual(len(self.inbox(self.deputy)), deputy_notes + 1)
        self.assertEqual(self.inbox(self.retired), [])
        self.assertEqual(self.inbox(self.manager), [])


if __name__ == "__main__":
    unittest.main()
