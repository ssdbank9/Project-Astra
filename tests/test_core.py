import json
import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from astra.auth import hash_password, verify_password
from astra.db import connect
from astra.service import AstraService, Conflict, Forbidden


class AstraCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "test.sqlite3"
        self.db = connect(self.db_path)
        self.service = AstraService(self.db)
        self.owner = self.service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def update_task(self, actor, task_id, payload):
        payload = dict(payload)
        payload.setdefault("expected_revision", self.service.get_task(actor, task_id)["revision"])
        return self.service.update_task(actor, task_id, payload)

    def test_password_hash_is_salted_and_verifiable(self):
        one = hash_password("correct horse battery")
        two = hash_password("correct horse battery")
        self.assertNotEqual(one, two)
        self.assertTrue(verify_password("correct horse battery", one))
        self.assertFalse(verify_password("wrong password here", one))

    def test_owner_project_task_and_append_only_events(self):
        project = self.service.create_project(self.owner, "AIOU")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Approve revised plan",
            "start_date": "2026-09-14", "due_date": "2026-09-20", "criticality": "high",
        })
        updated = self.update_task(self.owner, task["id"], {
            "due_date": "2026-09-22", "reason": "Committee meeting moved",
        })
        self.assertEqual(updated["revision"], 2)
        events = self.service.task_events(self.owner, task["id"])
        self.assertEqual([e["event_type"] for e in events], ["task_created", "task_updated"])
        self.assertIn("2026-09-20", events[1]["before_json"])
        self.assertIn("2026-09-22", events[1]["after_json"])

    def test_schedule_change_requires_reason(self):
        project = self.service.create_project(self.owner, "School")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Review design"})
        with self.assertRaisesRegex(ValueError, "reason"):
            self.update_task(self.owner, task["id"], {"due_date": "2026-10-01"})

    def test_member_only_sees_granted_project(self):
        visible = self.service.create_project(self.owner, "Visible")
        hidden = self.service.create_project(self.owner, "Hidden")
        member = self.service.create_user(self.owner, "member@example.org", "Member", "member password safe", "member")
        self.service.grant_project_access(self.owner, visible["id"], member["id"], "viewer")
        self.assertEqual([p["name"] for p in self.service.list_projects(member)], ["Visible"])
        with self.assertRaises(Forbidden):
            self.service.get_project(member, hidden["id"])

    def test_viewer_cannot_create_task(self):
        project = self.service.create_project(self.owner, "Controlled")
        member = self.service.create_user(self.owner, "viewer@example.org", "Viewer", "viewer password safe", "member")
        self.service.grant_project_access(self.owner, project["id"], member["id"], "viewer")
        with self.assertRaises(Forbidden):
            self.service.create_task(member, {"project_id": project["id"], "title": "Forbidden"})

    def test_manager_can_edit_ordinary_work_but_protected_status_becomes_request(self):
        project = self.service.create_project(self.owner, "Manager scope")
        manager = self.service.create_user(
            self.owner, "ordinary-manager@example.org", "Manager", "manager password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        with self.assertRaises(Forbidden):
            self.service.create_task(manager, {
                "project_id": project["id"], "title": "Pre-completed", "status": "completed",
            })
        task = self.service.create_task(manager, {
            "project_id": project["id"], "title": "Ordinary", "status": "draft",
        })
        updated = self.update_task(manager, task["id"], {
            "title": "Ordinary updated", "status": "in_progress", "reason": "Work started",
        })
        self.assertEqual((updated["title"], updated["status"]), ("Ordinary updated", "in_progress"))

        outcome = self.update_task(manager, task["id"], {
            "status": "cancelled", "reason": "Manager recommends cancellation",
        })

        self.assertEqual(outcome["request"]["action"], "update_task_status")
        current = self.service.get_task(self.owner, task["id"])
        self.assertEqual((current["title"], current["status"]), ("Ordinary updated", "in_progress"))

    def test_chairman_has_organization_visibility_without_implicit_mutation_power(self):
        project = self.service.create_project(self.owner, "Visible to Chairman")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Owner task"})
        chairman = self.service.create_user(
            self.owner, "chairman@example.org", "Chairman", "chairman password safe", "chairman"
        )

        self.assertEqual([p["id"] for p in self.service.list_projects(chairman)], [project["id"]])
        self.assertEqual(self.service.get_task(chairman, task["id"])["id"], task["id"])
        permissions = self.service.task_detail(chairman, task["id"])["permissions"]
        self.assertFalse(permissions["can_edit_ordinary"])
        self.assertFalse(permissions["can_request_protected"])
        self.assertFalse(permissions["can_manage_files"])
        self.assertTrue(permissions["can_read_files"])
        with self.assertRaises(Forbidden):
            self.service.create_task(chairman, {"project_id": project["id"], "title": "Not authorized"})
        with self.assertRaises(Forbidden):
            self.update_task(chairman, task["id"], {"title": "Not authorized"})

    def test_due_date_cannot_precede_start(self):
        project = self.service.create_project(self.owner, "Dates")
        with self.assertRaisesRegex(ValueError, "earlier"):
            self.service.create_task(self.owner, {
                "project_id": project["id"], "title": "Impossible",
                "start_date": "2026-10-02", "due_date": "2026-10-01",
            })

    def test_finish_to_start_dependency_blocks_until_predecessor_completed(self):
        project = self.service.create_project(self.owner, "Dependencies")
        first = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Approve concept", "status": "in_progress",
        })
        second = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Start delivery",
            "predecessor_task_id": first["id"],
        })
        listed = {task["id"]: task for task in self.service.list_tasks(self.owner, project["id"])}
        self.assertTrue(listed[second["id"]]["is_blocked"])
        self.assertEqual(listed[second["id"]]["blocked_by"][0]["title"], "Approve concept")
        submission = self.service.submit_task(self.owner, first["id"], "Concept ready")
        self.service.accept_submission(self.owner, submission["id"], "Approved by owner")
        listed = {task["id"]: task for task in self.service.list_tasks(self.owner, project["id"])}
        self.assertFalse(listed[second["id"]]["is_blocked"])
        events = self.service.task_events(self.owner, second["id"])
        self.assertEqual([event["event_type"] for event in events], ["task_created", "dependency_added"])

    def test_dependency_cycle_and_cross_project_links_are_rejected(self):
        project = self.service.create_project(self.owner, "One")
        other_project = self.service.create_project(self.owner, "Two")
        one = self.service.create_task(self.owner, {"project_id": project["id"], "title": "One"})
        two = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Two"})
        other = self.service.create_task(self.owner, {"project_id": other_project["id"], "title": "Other"})
        self.service.add_task_dependency(self.owner, one["id"], two["id"])
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.service.add_task_dependency(self.owner, two["id"], one["id"])
        with self.assertRaisesRegex(ValueError, "one project"):
            self.service.add_task_dependency(self.owner, one["id"], other["id"])

    def test_dependency_removal_requires_reason_and_is_audited(self):
        project = self.service.create_project(self.owner, "Removal")
        first = self.service.create_task(self.owner, {"project_id": project["id"], "title": "First"})
        second = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Second"})
        self.service.add_task_dependency(self.owner, first["id"], second["id"])
        with self.assertRaisesRegex(ValueError, "reason"):
            self.service.remove_task_dependency(self.owner, first["id"], second["id"], "")
        self.service.remove_task_dependency(
            self.owner, first["id"], second["id"], "Workstreams can now proceed in parallel"
        )
        self.assertEqual(self.service.get_task_dependencies(self.owner, second["id"]), [])
        events = self.service.task_events(self.owner, second["id"])
        self.assertEqual(events[-1]["event_type"], "dependency_removed")
        self.assertEqual(events[-1]["reason"], "Workstreams can now proceed in parallel")

    def test_update_task_rejects_blank_title_without_side_effects(self):
        project = self.service.create_project(self.owner, "Titles")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Keep me"})
        before_events = len(self.service.task_events(self.owner, task["id"]))
        with self.assertRaisesRegex(ValueError, "title"):
            self.update_task(self.owner, task["id"], {"title": "   "})
        reread = self.service.get_task(self.owner, task["id"])
        self.assertEqual(reread["title"], "Keep me")
        self.assertEqual(reread["revision"], 1)
        self.assertEqual(len(self.service.task_events(self.owner, task["id"])), before_events)

    def test_assignee_must_be_active_and_project_authorized(self):
        project = self.service.create_project(self.owner, "Assignment")
        other = self.service.create_project(self.owner, "Elsewhere")
        member = self.service.create_user(self.owner, "m@example.org", "Member", "member password safe", "member")
        # Not a member of the project yet -> rejected.
        with self.assertRaisesRegex(ValueError, "access to this project"):
            self.service.create_task(self.owner, {
                "project_id": project["id"], "title": "Assign", "owner_user_id": member["id"],
            })
        # Granting access on a different project does not authorize this one.
        self.service.grant_project_access(self.owner, other["id"], member["id"], "member")
        with self.assertRaisesRegex(ValueError, "access to this project"):
            self.service.create_task(self.owner, {
                "project_id": project["id"], "title": "Assign", "owner_user_id": member["id"],
            })
        # Grant access on the correct project -> accepted.
        self.service.grant_project_access(self.owner, project["id"], member["id"], "member")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Assign", "owner_user_id": member["id"],
        })
        self.assertEqual(task["owner_user_id"], member["id"])
        # Deactivated user cannot be assigned on update.
        self.db.execute("UPDATE users SET active=0 WHERE id=?", (member["id"],))
        with self.assertRaisesRegex(ValueError, "active"):
            self.update_task(self.owner, task["id"], {"owner_user_id": member["id"]})

    def test_missing_project_on_create_is_not_found(self):
        with self.assertRaises(KeyError):
            self.service.create_task(self.owner, {"project_id": "no-such-project", "title": "Ghost"})

    def test_due_state_uses_project_governing_timezone(self):
        # Two zones 26 hours apart: the eastern zone's calendar date is always at
        # least one day ahead of the western zone's, at every instant.
        ahead = self.service.create_project(self.owner, "Ahead", timezone_name="Etc/GMT-14")   # UTC+14
        behind = self.service.create_project(self.owner, "Behind", timezone_name="Etc/GMT+12")  # UTC-12
        today_behind = AstraService._today_in_timezone("Etc/GMT+12")
        # A task due on the western zone's "today" is still current there but already
        # past in the eastern zone.
        due_today_there = self.service.create_task(self.owner, {
            "project_id": behind["id"], "title": "Due in western zone", "due_date": today_behind,
        })
        overdue_here = self.service.create_task(self.owner, {
            "project_id": ahead["id"], "title": "Same date, eastern zone", "due_date": today_behind,
        })
        states = {t["id"]: t["due_state"] for t in self.service.list_tasks(self.owner)}
        self.assertEqual(states[due_today_there["id"]], "today")
        self.assertEqual(states[overdue_here["id"]], "overdue")

    def test_today_in_timezone_falls_back_on_unknown_zone(self):
        from datetime import date
        self.assertEqual(AstraService._today_in_timezone("Not/ARealZone"), date.today().isoformat())
        self.assertEqual(AstraService._today_in_timezone(None), date.today().isoformat())

    def test_task_detail_includes_dependencies_and_due_state(self):
        project = self.service.create_project(self.owner, "Detail")
        first = self.service.create_task(self.owner, {"project_id": project["id"], "title": "First"})
        second = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Second", "predecessor_task_id": first["id"],
        })
        detail = self.service.task_detail(self.owner, second["id"])
        self.assertIn("due_state", detail)
        directions = {dep["direction"] for dep in detail["dependencies"]}
        self.assertIn("incoming", directions)
        self.assertTrue(any(dep["blocking"] for dep in detail["dependencies"]))

    def test_user_directory_and_assignment_lifecycle(self):
        project = self.service.create_project(self.owner, "Team")
        member = self.service.create_user(self.owner, "t@example.org", "Teammate", "teammate password", "member")
        emails = {u["email"] for u in self.service.list_users(self.owner)}
        self.assertIn("t@example.org", emails)
        with self.assertRaises(Forbidden):
            self.service.list_users(member)
        assignable = {u["id"] for u in self.service.list_assignable_users(self.owner, project["id"])}
        self.assertIn(self.owner["id"], assignable)
        self.assertNotIn(member["id"], assignable)
        self.service.grant_project_access(self.owner, project["id"], member["id"], "member")
        assignable = {u["id"] for u in self.service.list_assignable_users(self.owner, project["id"])}
        self.assertIn(member["id"], assignable)
        self.service.set_user_active(self.owner, member["id"], False)
        assignable = {u["id"] for u in self.service.list_assignable_users(self.owner, project["id"])}
        self.assertNotIn(member["id"], assignable)

    def test_owner_cannot_deactivate_self(self):
        with self.assertRaisesRegex(ValueError, "your own"):
            self.service.set_user_active(self.owner, self.owner["id"], False)

    def test_duplicate_email_is_rejected(self):
        self.service.create_user(self.owner, "dup@example.org", "One", "password one two")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.service.create_user(self.owner, "dup@example.org", "Two", "password three four")

    def test_revoke_project_access_removes_membership(self):
        project = self.service.create_project(self.owner, "Revoke")
        member = self.service.create_user(self.owner, "r@example.org", "R", "password aaaa bbbb")
        self.service.grant_project_access(self.owner, project["id"], member["id"], "viewer")
        self.assertTrue(self.service.can_view_project(member, project["id"]))
        self.service.revoke_project_access(self.owner, project["id"], member["id"])
        self.assertFalse(self.service.can_view_project(member, project["id"]))

    def test_list_tasks_reports_days_to_due_and_next_action(self):
        from datetime import date, timedelta
        project = self.service.create_project(self.owner, "Dashboard", timezone_name="UTC")
        base = date.fromisoformat(AstraService._today_in_timezone("UTC"))
        soon = (base + timedelta(days=3)).isoformat()
        assigned = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Do it", "due_date": soon,
            "owner_user_id": self.owner["id"], "status": "in_progress",
        })
        undated = self.service.create_task(self.owner, {"project_id": project["id"], "title": "No date"})
        by_id = {t["id"]: t for t in self.service.list_tasks(self.owner, project["id"])}
        self.assertEqual(by_id[assigned["id"]]["days_to_due"], 3)
        self.assertEqual(by_id[assigned["id"]]["next_action"], "In progress by owner")
        self.assertIsNone(by_id[undated["id"]]["days_to_due"])
        self.assertEqual(by_id[undated["id"]]["next_action"], "Assign an owner")

    def test_subtask_rollup_and_cycle_prevention(self):
        project = self.service.create_project(self.owner, "Hierarchy")
        parent = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Parent"})
        child_a = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Child A", "parent_task_id": parent["id"]})
        child_b = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Child B"})
        self.service.set_parent(self.owner, child_b["id"], parent["id"])
        # Complete child A through the lifecycle so the roll-up counts it.
        sub = self.service.submit_task(self.owner, child_a["id"], "done")
        self.service.accept_submission(self.owner, sub["id"], "ok")
        detail = self.service.task_detail(self.owner, parent["id"])
        self.assertEqual(detail["subtask_rollup"], {"total": 2, "completed": 1})
        self.assertEqual({s["id"] for s in detail["subtasks"]}, {child_a["id"], child_b["id"]})
        # Cycle prevention: parent cannot become a child of its own descendant.
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.service.set_parent(self.owner, parent["id"], child_b["id"])
        # A task cannot be its own parent.
        with self.assertRaisesRegex(ValueError, "its own parent"):
            self.service.set_parent(self.owner, parent["id"], parent["id"])

    def test_parent_must_be_same_project(self):
        project = self.service.create_project(self.owner, "P1")
        other = self.service.create_project(self.owner, "P2")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "T"})
        outsider = self.service.create_task(self.owner, {"project_id": other["id"], "title": "O"})
        with self.assertRaisesRegex(ValueError, "same project"):
            self.service.set_parent(self.owner, task["id"], outsider["id"])

    def test_list_tasks_sorts_by_confirmed_criticality_then_due_date(self):
        from datetime import date, timedelta
        project = self.service.create_project(self.owner, "Sorting", timezone_name="UTC")
        base = date.fromisoformat(AstraService._today_in_timezone("UTC"))
        low_soon = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Low soon", "criticality": "low",
            "due_date": (base + timedelta(days=1)).isoformat()})
        crit_late = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Critical late", "criticality": "critical",
            "due_date": (base + timedelta(days=60)).isoformat()})
        unrated = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Unrated"})
        high_far = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "High far", "criticality": "high",
            "due_date": (base + timedelta(days=10)).isoformat()})
        high_near = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "High near", "criticality": "high",
            "due_date": (base + timedelta(days=5)).isoformat()})
        order = [t["id"] for t in self.service.list_tasks(self.owner, project["id"])]
        self.assertEqual(order, [crit_late["id"], high_near["id"], high_far["id"], low_soon["id"], unrated["id"]])
        # QY0WG2: the default is the criticality order.
        default_order = [t["id"] for t in self.service.list_tasks(self.owner, project["id"], "criticality")]
        self.assertEqual(default_order, order)

    def test_list_tasks_sort_by_due_date_toggle(self):
        # QY0WG2: the app can also sort by nearest/overdue due date; undated last.
        from datetime import date, timedelta
        project = self.service.create_project(self.owner, "SortDue", timezone_name="UTC")
        base = date.fromisoformat(AstraService._today_in_timezone("UTC"))
        low_soon = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Low soon", "criticality": "low",
            "due_date": (base + timedelta(days=1)).isoformat()})
        crit_late = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Critical late", "criticality": "critical",
            "due_date": (base + timedelta(days=60)).isoformat()})
        unrated = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Unrated"})
        high_near = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "High near", "criticality": "high",
            "due_date": (base + timedelta(days=5)).isoformat()})
        order = [t["id"] for t in self.service.list_tasks(self.owner, project["id"], "due_date")]
        # Nearest due date first regardless of criticality; the undated task sorts last.
        self.assertEqual(order, [low_soon["id"], high_near["id"], crit_late["id"], unrated["id"]])
        # An unknown sort mode falls back to the criticality order (crit_late first).
        fallback = [t["id"] for t in self.service.list_tasks(self.owner, project["id"], "bogus")]
        self.assertEqual(fallback[0], crit_late["id"])

    def test_confirm_criticality_records_event_and_requires_reason(self):
        project = self.service.create_project(self.owner, "Crit")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "T"})
        with self.assertRaisesRegex(ValueError, "reason"):
            self.service.confirm_criticality(self.owner, task["id"], "high", "")
        updated = self.service.confirm_criticality(self.owner, task["id"], "high", "Board escalation")
        self.assertEqual(updated["criticality"], "high")
        events = self.service.task_events(self.owner, task["id"])
        self.assertEqual(events[-1]["event_type"], "criticality_changed")
        self.assertIn("high", events[-1]["after_json"])
        self.assertEqual(events[-1]["reason"], "Board escalation")
        with self.assertRaisesRegex(ValueError, "already set"):
            self.service.confirm_criticality(self.owner, task["id"], "high", "again")

    def test_criticality_sort_orders_normal_above_low(self):
        # QY0WG2 review gap 2: Normal must rank above Low in the criticality order even
        # when the Low task is due sooner; Unrated stays last.
        from datetime import date, timedelta
        project = self.service.create_project(self.owner, "NormalLow", timezone_name="UTC")
        base = date.fromisoformat(AstraService._today_in_timezone("UTC"))
        low = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Low", "criticality": "low",
            "due_date": (base + timedelta(days=1)).isoformat()})
        normal = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Normal", "criticality": "normal",
            "due_date": (base + timedelta(days=9)).isoformat()})
        unrated = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Unrated", "due_date": base.isoformat()})
        order = [t["id"] for t in self.service.list_tasks(self.owner, project["id"], "criticality")]
        self.assertEqual(order, [normal["id"], low["id"], unrated["id"]])

    def test_confirm_criticality_event_records_actor_old_and_new_value(self):
        # QY0WG2 review gap 2: the audit record must carry who changed it and from what.
        import json
        project = self.service.create_project(self.owner, "CritAudit")
        manager = self.service.create_user(self.owner, "crit-mgr@example.org", "Crit Manager",
                                           "manager password safe", "member")
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "T"})
        self.service.confirm_criticality(manager, task["id"], "low", "Initial rating")
        self.service.confirm_criticality(manager, task["id"], "critical", "Board escalation")
        changes = [e for e in self.service.task_events(self.owner, task["id"])
                   if e["event_type"] == "criticality_changed"]
        self.assertEqual(len(changes), 2)
        self.assertEqual([e["actor_user_id"] for e in changes], [manager["id"], manager["id"]])
        self.assertEqual(json.loads(changes[0]["before_json"]), {"criticality": None})
        self.assertEqual(json.loads(changes[0]["after_json"]), {"criticality": "low"})
        self.assertEqual(json.loads(changes[1]["before_json"]), {"criticality": "low"})
        self.assertEqual(json.loads(changes[1]["after_json"]), {"criticality": "critical"})
        self.assertEqual(changes[1]["reason"], "Board escalation")

    def test_confirm_criticality_requires_project_manager(self):
        project = self.service.create_project(self.owner, "CritAuth")
        member = self.service.create_user(self.owner, "crit-member@example.org", "Crit Member",
                                          "member password safe", "member")
        self.service.grant_project_access(self.owner, project["id"], member["id"], "member")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "T"})
        with self.assertRaises(Forbidden):
            self.service.confirm_criticality(member, task["id"], "critical", "I think so")
        self.assertIsNone(self.service.get_task(self.owner, task["id"])["criticality"])

    def test_confirm_criticality_refuses_null_reason_and_non_string_values(self):
        # QY0WG2 review gaps 3-4: JSON null must not become the reason "None", and a
        # non-string level is a validation error (400), not a TypeError (500).
        project = self.service.create_project(self.owner, "CritTypes")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "T"})
        for reason in (None, 42, ["x"], "   "):
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, "reason"):
                self.service.confirm_criticality(self.owner, task["id"], "high", reason)
        for level in (["high"], {"high": 1}, 3, True):
            with self.subTest(level=level), self.assertRaisesRegex(ValueError, "Invalid criticality"):
                self.service.confirm_criticality(self.owner, task["id"], level, "evidence")
        self.assertFalse([e for e in self.service.task_events(self.owner, task["id"])
                          if e["event_type"] == "criticality_changed"])

    def _race_confirmations(self, **first_kwargs):
        """A reads the task, then B confirms low->critical on its own connection, then A writes high."""
        a = AstraService(connect(self.db_path))
        b = AstraService(connect(self.db_path))
        self.addCleanup(a.db.close)
        self.addCleanup(b.db.close)
        project = self.service.create_project(self.owner, "CritRace")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "T", "criticality": "low"})
        if "expected_revision" in first_kwargs:
            first_kwargs["expected_revision"] = self.service.get_task(self.owner, task["id"])["revision"]
        original = a.get_task
        calls = {"n": 0}

        def racing_get_task(actor, task_id):
            row = original(actor, task_id)
            calls["n"] += 1
            if calls["n"] == 1:
                b.confirm_criticality(self.owner, task_id, "critical", "B: board escalation")
            return row

        a.get_task = racing_get_task
        return a, task, lambda: a.confirm_criticality(self.owner, task["id"], "high", "A: evidence", **first_kwargs)

    def test_confirm_criticality_records_true_old_value_under_interleaving(self):
        # QY0WG2 review gap 1: the old value is re-read under the write lock, so A's event
        # says critical->high (what it really replaced), not a stale low->high.
        import json
        _, task, confirm_a = self._race_confirmations()
        confirm_a()
        changes = [e for e in self.service.task_events(self.owner, task["id"])
                   if e["event_type"] == "criticality_changed"]
        self.assertEqual([json.loads(e["before_json"])["criticality"] for e in changes], ["low", "critical"])
        self.assertEqual([json.loads(e["after_json"])["criticality"] for e in changes], ["critical", "high"])

    def test_confirm_criticality_with_stale_expected_revision_is_a_conflict(self):
        # QY0WG2 review gap 1: a caller that says which revision it saw is refused if the
        # task moved on, so B's confirmed Critical is not silently overwritten.
        from astra.service import Conflict
        _, task, confirm_a = self._race_confirmations(expected_revision=None)
        with self.assertRaisesRegex(Conflict, "revision"):
            confirm_a()
        self.assertEqual(self.service.get_task(self.owner, task["id"])["criticality"], "critical")
        changes = [e for e in self.service.task_events(self.owner, task["id"])
                   if e["event_type"] == "criticality_changed"]
        self.assertEqual(len(changes), 1)

    def test_update_task_cannot_change_criticality_directly(self):
        project = self.service.create_project(self.owner, "Guard2")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "T", "criticality": "low"})
        with self.assertRaisesRegex(ValueError, "confirm criticality"):
            self.update_task(self.owner, task["id"], {"criticality": "critical", "reason": "x"})

    def test_entities_seed_are_idempotent_and_owner_only(self):
        member = self.service.create_user(self.owner, "e@example.org", "E", "member password safe")
        with self.assertRaises(Forbidden):
            self.service.create_entity(member, "Sneaky Entity")
        created = self.service.seed_default_entities(self.owner)
        self.assertIn("Tax Exempt", created)
        again = self.service.seed_default_entities(self.owner)
        self.assertEqual(again, [])  # idempotent
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.service.create_entity(self.owner, "Tax Exempt")

    def test_cross_entity_project_keeps_one_id_with_multiple_entities(self):
        self.service.seed_default_entities(self.owner)
        entities = {e["name"]: e["id"] for e in self.service.list_entities(self.owner)}
        project = self.service.create_project(self.owner, "Shared initiative")
        linked = self.service.set_project_entities(
            self.owner, project["id"], [entities["RDI - Global"], entities["RDI Pakistan"]]
        )
        self.assertEqual({e["name"] for e in linked}, {"RDI - Global", "RDI Pakistan"})
        # The project itself carries its entity links; there is only one project row.
        reread = self.service.get_project(self.owner, project["id"])
        self.assertEqual(len(reread["entities"]), 2)
        self.assertEqual(len(self.service.list_projects(self.owner)), 1)
        # Re-filing replaces links without duplicating.
        self.service.set_project_entities(self.owner, project["id"], [entities["RDI Pakistan"]])
        self.assertEqual([e["name"] for e in self.service.list_project_entities(self.owner, project["id"])], ["RDI Pakistan"])

    def test_owner_notified_of_other_users_changes_idempotently(self):
        project = self.service.create_project(self.owner, "Notify")
        manager = self.service.create_user(self.owner, "n@example.org", "Manager", "manager password ok")
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        # Manager creates a task -> owner gets one notification; owner sees none for their own acts.
        task = self.service.create_task(manager, {"project_id": project["id"], "title": "From manager"})
        owner_notes = self.service.list_notifications(self.owner)
        self.assertEqual(len(owner_notes), 1)
        self.assertIn("From manager", owner_notes[0]["summary"])
        self.assertEqual(self.service.unread_notification_count(self.owner), 1)
        # The manager (not a recipient) has an empty inbox.
        self.assertEqual(self.service.list_notifications(manager), [])
        # Marking read is not deletion and does not change the task.
        self.service.mark_notification_read(self.owner, owner_notes[0]["id"])
        self.assertEqual(self.service.unread_notification_count(self.owner), 0)
        self.assertEqual(len(self.service.list_notifications(self.owner)), 1)
        self.assertEqual(self.service.get_task(self.owner, task["id"])["status"], "draft")
        # Owner's own change creates no self-notification.
        self.service.confirm_criticality(self.owner, task["id"], "high", "escalate")
        self.assertEqual(self.service.unread_notification_count(self.owner), 0)

    def test_notification_recipient_isolation(self):
        project = self.service.create_project(self.owner, "Isolation")
        manager = self.service.create_user(self.owner, "iso@example.org", "Mgr", "manager password ok")
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        self.service.create_task(manager, {"project_id": project["id"], "title": "X"})
        note = self.service.list_notifications(self.owner)[0]
        with self.assertRaises(Forbidden):
            self.service.mark_notification_read(manager, note["id"])

    def test_login_throttle_counts_failures_and_success_clears_them(self):
        for _ in range(4):
            self.service.record_login_attempt("owner@example.org", "127.0.0.1", False)
        self.assertFalse(self.service.login_is_throttled("owner@example.org"))
        self.service.record_login_attempt("owner@example.org", "127.0.0.1", False)
        self.assertTrue(self.service.login_is_throttled("owner@example.org"))
        self.service.record_login_attempt("owner@example.org", "127.0.0.1", True)
        self.assertFalse(self.service.login_is_throttled("owner@example.org"))

    def test_cleanup_expired_sessions_removes_only_expired(self):
        from astra.service import now_text
        self.db.execute("INSERT INTO sessions VALUES(?,?,?,?,?)",
                        ("h_expired", self.owner["id"], "c1", now_text(), "2000-01-01T00:00:00+00:00"))
        self.db.execute("INSERT INTO sessions VALUES(?,?,?,?,?)",
                        ("h_active", self.owner["id"], "c2", now_text(), "2999-01-01T00:00:00+00:00"))
        self.service.cleanup_expired_sessions()
        remaining = [r["token_hash"] for r in self.db.execute("SELECT token_hash FROM sessions").fetchall()]
        self.assertEqual(remaining, ["h_active"])

    def test_revoke_user_sessions_removes_all_of_them(self):
        from astra.service import now_text
        for token in ("s1", "s2"):
            self.db.execute("INSERT INTO sessions VALUES(?,?,?,?,?)",
                            (token, self.owner["id"], token, now_text(), "2999-01-01T00:00:00+00:00"))
        self.assertEqual(self.service.revoke_user_sessions(self.owner["id"]), 2)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)

    def test_manager_submitter_cannot_self_accept_and_routes_to_owner(self):
        project = self.service.create_project(self.owner, "Review")
        manager = self.service.create_user(self.owner, "mgr@example.org", "Manager", "manager password ok")
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Deliverable", "owner_user_id": manager["id"],
        })
        submission = self.service.submit_task(manager, task["id"], "Draft one")
        outcome = self.service.accept_submission(manager, submission["id"])
        self.assertEqual(outcome["request"]["action"], "accept_submission")
        self.assertEqual(self.service.get_submission(self.owner, submission["id"])["status"], "submitted")
        accepted = self.service.accept_submission(self.owner, submission["id"], "Looks good")
        self.assertEqual(accepted["status"], "accepted")
        completed = self.service.get_task(self.owner, task["id"])
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["accepted_submission_id"], submission["id"])

    def test_completed_task_is_immutable_until_reopened_with_revised_timeline(self):
        project = self.service.create_project(self.owner, "Immutable")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "One"})
        first = self.service.submit_task(self.owner, task["id"], "v1")
        self.service.accept_submission(self.owner, first["id"], "ok")
        with self.assertRaisesRegex(ValueError, "reopen"):
            self.service.submit_task(self.owner, task["id"], "v2")
        with self.assertRaisesRegex(ValueError, "reason"):
            self.service.reopen_task(self.owner, task["id"], "", "2027-01-15")
        with self.assertRaisesRegex(ValueError, "timeline"):
            self.service.reopen_task(self.owner, task["id"], "Scope changed", None)
        self.service.reopen_task(self.owner, task["id"], "Client changed scope", "2027-01-15")
        reopened = self.service.get_task(self.owner, task["id"])
        self.assertEqual(reopened["status"], "reopened")
        self.assertEqual(reopened["due_date"], "2027-01-15")
        self.assertEqual(reopened["accepted_submission_id"], first["id"])  # prior accepted version preserved
        second = self.service.submit_task(self.owner, task["id"], "v2")
        self.assertEqual(second["version"], 2)
        subs = self.service.list_task_submissions(self.owner, task["id"])
        self.assertEqual([s["status"] for s in subs], ["accepted", "submitted"])

    def test_request_changes_returns_to_progress_with_reason(self):
        project = self.service.create_project(self.owner, "Changes")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Doc"})
        submission = self.service.submit_task(self.owner, task["id"], "draft")
        with self.assertRaisesRegex(ValueError, "reason"):
            self.service.request_changes(self.owner, submission["id"], "")
        self.service.request_changes(self.owner, submission["id"], "Fix section 2")
        self.assertEqual(self.service.get_task(self.owner, task["id"])["status"], "changes_requested")

    def test_on_hold_requires_reason_checkpoint_and_creates_record(self):
        project = self.service.create_project(self.owner, "Hold")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Paused", "owner_user_id": self.owner["id"],
        })
        with self.assertRaisesRegex(ValueError, "reason"):
            self.service.set_on_hold(self.owner, task["id"], "", "2027-02-01", self.owner["id"])
        with self.assertRaisesRegex(ValueError, "checkpoint"):
            self.service.set_on_hold(self.owner, task["id"], "waiting", "", self.owner["id"])
        held = self.service.set_on_hold(self.owner, task["id"], "waiting for vendor", "2027-02-01", self.owner["id"])
        self.assertEqual(held["status"], "on_hold")
        checkpoint = self.db.execute(
            "SELECT reason, checkpoint_date FROM task_checkpoints WHERE task_id=?", (task["id"],)
        ).fetchone()
        self.assertEqual(checkpoint["checkpoint_date"], "2027-02-01")

    def test_designated_approver_requests_owner_acceptance(self):
        project = self.service.create_project(self.owner, "Approvers")
        submitter = self.service.create_user(self.owner, "sub@example.org", "Sub", "submitter password")
        approver = self.service.create_user(self.owner, "app@example.org", "App", "approver password")
        self.service.grant_project_access(self.owner, project["id"], submitter["id"], "member")
        self.service.grant_project_access(self.owner, project["id"], approver["id"], "member")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "T", "owner_user_id": submitter["id"],
        })
        self.service.add_task_reviewer(self.owner, task["id"], approver["id"], "approver")
        submission = self.service.submit_task(submitter, task["id"], "done")
        outcome = self.service.accept_submission(approver, submission["id"], "recommend approval")
        self.assertEqual(outcome["request"]["action"], "accept_submission")
        self.assertEqual(self.service.get_submission(self.owner, submission["id"])["status"], "submitted")

    def test_manager_protected_acceptance_creates_owner_request_without_mutation(self):
        project = self.service.create_project(self.owner, "Governed review")
        submitter = self.service.create_user(
            self.owner, "submit@example.org", "Submitter", "submitter password safe"
        )
        manager = self.service.create_user(
            self.owner, "manager@example.org", "Manager", "manager password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], submitter["id"], "member")
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Board paper", "owner_user_id": submitter["id"],
        })
        submission = self.service.submit_task(submitter, task["id"], "Ready for decision")

        outcome = self.service.accept_submission(manager, submission["id"], "Manager recommends acceptance")

        self.assertEqual(outcome["request"]["action"], "accept_submission")
        self.assertEqual(outcome["request"]["status"], "pending")
        self.assertEqual(self.service.get_task(self.owner, task["id"])["status"], "submitted")
        self.assertEqual(self.service.get_submission(self.owner, submission["id"])["status"], "submitted")
        permissions = self.service.task_detail(manager, task["id"])["permissions"]
        self.assertTrue(permissions["can_edit_ordinary"])
        self.assertTrue(permissions["can_request_protected"])
        self.assertFalse(permissions["can_manage_files"])
        owner_notifications = self.service.list_notifications(self.owner)
        self.assertEqual(owner_notifications[0]["kind"], "protected_action_requested")
        pending = self.service.list_owner_action_requests(self.owner)
        self.assertEqual(pending[0]["requested_by_name"], "Manager")
        self.assertEqual(pending[0]["task_title"], "Board paper")
        with self.assertRaises(Forbidden):
            self.service.list_owner_action_requests(manager)

    def test_manager_protected_lifecycle_attempts_queue_requests_without_mutation(self):
        project = self.service.create_project(self.owner, "Protected lifecycle")
        manager = self.service.create_user(
            self.owner, "lifecycle-manager@example.org", "Manager", "manager password safe"
        )
        submitter = self.service.create_user(
            self.owner, "lifecycle-submitter@example.org", "Submitter", "submitter password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        self.service.grant_project_access(self.owner, project["id"], submitter["id"], "member")

        review_task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Review", "owner_user_id": submitter["id"],
        })
        submission = self.service.submit_task(submitter, review_task["id"], "Review me")
        changes = self.service.request_changes(manager, submission["id"], "Manager recommends revision")
        self.assertEqual(changes["request"]["action"], "request_changes")
        self.assertEqual(self.service.get_task(self.owner, review_task["id"])["status"], "submitted")

        self.service.accept_submission(self.owner, submission["id"], "Owner accepts")
        reopen = self.service.reopen_task(manager, review_task["id"], "New information", "2027-03-01")
        self.assertEqual(reopen["request"]["action"], "reopen_task")
        self.assertEqual(self.service.get_task(self.owner, review_task["id"])["status"], "completed")

        ordinary_task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Ordinary", "owner_user_id": manager["id"],
        })
        hold = self.service.set_on_hold(
            manager, ordinary_task["id"], "Waiting for vendor", "2027-03-02", manager["id"]
        )
        self.assertEqual(hold["request"]["action"], "set_on_hold")
        self.assertEqual(self.service.get_task(self.owner, ordinary_task["id"])["status"], "draft")
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM task_checkpoints WHERE task_id=?", (ordinary_task["id"],)).fetchone()[0],
            0,
        )

    def test_read_only_chairman_protected_attempts_are_blocked_audited_and_notified(self):
        project = self.service.create_project(self.owner, "Chairman blocked")
        chairman = self.service.create_user(
            self.owner, "blocked-chair@example.org", "Chairman", "chairman password safe", "chairman"
        )
        submitter = self.service.create_user(
            self.owner, "blocked-submitter@example.org", "Submitter", "submitter password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], submitter["id"], "member")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Board minutes", "owner_user_id": submitter["id"],
        })
        submission = self.service.submit_task(submitter, task["id"], "Ready")

        with self.assertRaises(Forbidden):
            self.service.accept_submission(chairman, submission["id"], "Chairman approves")
        with self.assertRaises(Forbidden):
            self.service.set_on_hold(chairman, task["id"], "Pause it", "2027-04-01", submitter["id"])
        with self.assertRaises(Forbidden):
            self.service.close_project(chairman, project["id"], "Chairman closes")

        self.assertEqual(self.service.get_submission(self.owner, submission["id"])["status"], "submitted")
        self.assertEqual(self.service.get_task(self.owner, task["id"])["status"], "submitted")
        self.assertEqual(self.service.get_project(self.owner, project["id"])["status"], "active")
        task_blocked = [e for e in self.service.task_events(self.owner, task["id"])
                        if e["event_type"] == "protected_action_blocked"]
        self.assertEqual([e["actor_user_id"] for e in task_blocked], [chairman["id"]] * 2)
        self.assertIn('"action": "accept_submission"', task_blocked[0]["after_json"])
        self.assertIn('"action": "set_on_hold"', task_blocked[1]["after_json"])
        project_blocked = [e for e in self.service.project_events(self.owner, project["id"])
                           if e["event_type"] == "protected_action_blocked"]
        self.assertEqual(len(project_blocked), 1)
        self.assertEqual(project_blocked[0]["actor_user_id"], chairman["id"])
        self.assertIn('"action": "close_project"', project_blocked[0]["detail_json"])
        blocked_notes = [n for n in self.service.list_notifications(self.owner)
                         if n["kind"] == "protected_action_blocked"]
        self.assertEqual(len(blocked_notes), 3)
        self.assertEqual(self.service.list_owner_action_requests(self.owner), [])

    def test_viewer_protected_attempts_are_blocked_audited_and_notified(self):
        project = self.service.create_project(self.owner, "Viewer blocked")
        viewer = self.service.create_user(
            self.owner, "blocked-viewer@example.org", "Viewer", "viewer password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], viewer["id"], "viewer")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Read-only deliverable", "owner_user_id": self.owner["id"],
        })
        attachment = self.service.add_task_attachment(self.owner, task["id"], "/data/viewer-cannot.pdf")
        submission = self.service.submit_task(self.owner, task["id"], "Owner submitted")

        with self.assertRaises(Forbidden):
            self.update_task(viewer, task["id"], {"title": "Renamed by viewer"})
        with self.assertRaises(Forbidden):
            self.service.accept_submission(viewer, submission["id"], "Viewer approves")
        with self.assertRaises(Forbidden):
            self.service.request_changes(viewer, submission["id"], "Viewer wants changes")
        with self.assertRaises(Forbidden):
            self.service.close_project(viewer, project["id"], "Viewer closes")
        with self.assertRaises(Forbidden):
            self.service.remove_task_attachment(viewer, task["id"], attachment["id"])

        self.assertEqual(self.service.get_task(self.owner, task["id"])["title"], "Read-only deliverable")
        self.assertEqual(self.service.get_submission(self.owner, submission["id"])["status"], "submitted")
        self.assertEqual(self.service.get_project(self.owner, project["id"])["status"], "active")
        self.assertEqual(len(self.service.list_task_attachments(self.owner, task["id"])), 1)
        task_kinds = [e["event_type"] for e in self.service.task_events(self.owner, task["id"])]
        self.assertEqual(task_kinds.count("protected_action_blocked"), 2)
        self.assertIn("attachment_removal_blocked", task_kinds)
        project_kinds = [e["event_type"] for e in self.service.project_events(self.owner, project["id"])]
        self.assertEqual(project_kinds.count("protected_action_blocked"), 1)
        owner_kinds = [n["kind"] for n in self.service.list_notifications(self.owner)]
        self.assertEqual(owner_kinds.count("protected_action_blocked"), 3)
        self.assertIn("attachment_removal_blocked", owner_kinds)
        self.assertEqual(self.service.list_owner_action_requests(self.owner), [])
        permissions = self.service.task_detail(viewer, task["id"])["permissions"]
        self.assertFalse(permissions["can_edit_ordinary"])
        self.assertFalse(permissions["can_request_protected"])
        self.assertFalse(permissions["can_decide_protected"])
        self.assertFalse(permissions["can_manage_files"])
        self.assertTrue(permissions["can_read_files"])

    def test_update_task_protects_the_source_status_for_managers_and_points_the_owner_at_the_lifecycle_action(self):
        # Adversarial review AS-1 (2026-09-22): the guard read only the target status, so a Manager
        # could edit completed -> in_progress with 200 and no Owner request, and the Owner could
        # leave completed without the reopen record handoff 7.3 requires.
        import json as json_module
        project = self.service.create_project(self.owner, "Source guard")
        manager = self.service.create_user(self.owner, "source-manager@example.org", "Manager", "manager password safe")
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")

        def make(status):
            task = self.service.create_task(self.owner, {
                "project_id": project["id"], "title": f"Leaving {status}", "owner_user_id": manager["id"],
            })
            if status == "completed":
                submission = self.service.submit_task(manager, task["id"], "done")
                self.service.accept_submission(self.owner, submission["id"], "ok")
            elif status == "submitted":
                self.service.submit_task(manager, task["id"], "v1")
            elif status == "on_hold":
                self.service.set_on_hold(self.owner, task["id"], "hold", "2026-12-01")
            elif status == "reopened":
                submission = self.service.submit_task(manager, task["id"], "done")
                self.service.accept_submission(self.owner, submission["id"], "ok")
                self.service.reopen_task(self.owner, task["id"], "second look", "2027-01-15")
            elif status == "changes_requested":
                submission = self.service.submit_task(manager, task["id"], "v1")
                self.service.request_changes(self.owner, submission["id"], "not yet")
            else:
                self.update_task(self.owner, task["id"], {"status": status, "reason": "x"})
            return self.service.get_task(self.owner, task["id"])

        # Regression review TESTS-1 (2026-09-22): reopened and changes_requested are locked sources
        # too (authorization matrix row 24); until they were listed here a change in either
        # direction passed the suite.
        # SRFCZD R5 (SEM-2): leaving submitted is refused for a Manager too (below), since the
        # Owner could never approve that generic request; only the submission decision leaves review.
        for source, target in (("completed", "in_progress"), ("cancelled", "assigned"), ("on_hold", "in_progress"),
                               ("abandoned", "in_progress"),
                               ("reopened", "in_progress"), ("changes_requested", "in_progress")):
            with self.subTest(source=source, actor="manager"):
                task = make(source)
                outcome = self.update_task(manager, task["id"], {"status": target, "reason": "back to work"})
                self.assertEqual(outcome["request"]["action"], "update_task_status")
                self.assertEqual(json_module.loads(outcome["request"]["payload_json"])["from_status"], source)
                current = self.service.get_task(self.owner, task["id"])
                self.assertEqual((current["status"], current["revision"]), (source, task["revision"]))
        for source in ("completed", "cancelled", "abandoned"):
            with self.subTest(source=source, actor="owner"):
                task = make(source)
                with self.assertRaisesRegex(ValueError, "reopen"):
                    self.update_task(self.owner, task["id"], {"status": "in_progress", "reason": "shortcut"})
                self.assertEqual(self.service.get_task(self.owner, task["id"])["status"], source)
        task = make("submitted")
        for label, actor in (("owner", self.owner), ("manager", manager)):
            with self.subTest(source="submitted", actor=label):
                with self.assertRaisesRegex(ValueError, "accept"):
                    self.update_task(actor, task["id"], {"status": "in_progress", "reason": "undo"})
                self.assertEqual(self.service.get_task(self.owner, task["id"])["status"], "submitted")
        self.assertEqual(
            [r for r in self.service.list_owner_action_requests(self.owner, status=None) if r["task_id"] == task["id"]],
            [],
        )
        # the recorded way back: reopen with a reason and a revised due date
        done = make("completed")
        reopened = self.service.reopen_task(self.owner, done["id"], "second round", "2027-01-15")
        self.assertEqual(reopened["status"], "reopened")
        self.assertIn("task_reopened", [e["event_type"] for e in self.service.task_events(self.owner, done["id"])])
        # on hold has no dedicated release action: the Owner's update with a reason is the recorded path out
        held = make("on_hold")
        released = self.update_task(self.owner, held["id"], {"status": "in_progress", "reason": "checkpoint met"})
        self.assertEqual(released["status"], "in_progress")

    def test_update_task_cannot_shortcut_governed_status(self):
        project = self.service.create_project(self.owner, "Guard")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "G"})
        for status in ("submitted", "completed", "on_hold", "reopened"):
            with self.assertRaisesRegex(ValueError, "dedicated"):
                self.update_task(self.owner, task["id"], {"status": status, "reason": "x"})

    def test_project_closure_authority_and_residual_snapshot(self):
        chairman = self.service.create_user(self.owner, "chair@example.org", "Chair", "chairman password", "chairman")
        project = self.service.create_project(self.owner, "Closing")
        open_task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Unfinished", "status": "in_progress",
        })
        with self.assertRaises(Forbidden):
            self.service.close_project(chairman, project["id"], "x", exceptional=True)
        with self.assertRaisesRegex(ValueError, "outstanding"):
            self.service.close_project(self.owner, project["id"], "note")
        closed = self.service.close_project(self.owner, project["id"], "Wrapping up despite residual", exceptional=True)
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["closure_is_exceptional"], 1)
        self.assertEqual(self.service.get_task(self.owner, open_task["id"])["status"], "in_progress")
        events = self.service.project_events(self.owner, project["id"])
        self.assertIn("Unfinished", events[-1]["detail_json"])
        clean = self.service.create_project(self.owner, "Clean")
        done = self.service.create_task(self.owner, {"project_id": clean["id"], "title": "Done"})
        submission = self.service.submit_task(self.owner, done["id"], "d")
        self.service.accept_submission(self.owner, submission["id"], "ok")
        with self.assertRaises(Forbidden):
            self.service.close_project(chairman, clean["id"])
        manager = self.service.create_user(
            self.owner, "close-manager@example.org", "Manager", "manager password safe"
        )
        self.service.grant_project_access(self.owner, clean["id"], manager["id"], "manager")
        close_request = self.service.close_project(manager, clean["id"], "Manager recommends closure")
        self.assertEqual(close_request["request"]["action"], "close_project")
        self.assertEqual(self.service.get_project(self.owner, clean["id"])["status"], "active")
        closed_clean = self.service.close_project(self.owner, clean["id"], "Owner closes")
        self.assertEqual(closed_clean["closure_is_exceptional"], 0)

    def test_critical_path_linear_chain(self):
        p = self.service.create_project(self.owner, "CP linear")
        a = self.service.create_task(self.owner, {"project_id": p["id"], "title": "A", "start_date": "2026-09-01", "due_date": "2026-09-05"})
        b = self.service.create_task(self.owner, {"project_id": p["id"], "title": "B", "start_date": "2026-09-06", "due_date": "2026-09-08"})
        c = self.service.create_task(self.owner, {"project_id": p["id"], "title": "C", "start_date": "2026-09-09", "due_date": "2026-09-12"})
        self.service.add_task_dependency(self.owner, a["id"], b["id"])
        self.service.add_task_dependency(self.owner, b["id"], c["id"])
        cp = {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner, p["id"])}
        self.assertTrue(cp[a["id"]] and cp[b["id"]] and cp[c["id"]])

    def test_critical_path_longer_branch_wins(self):
        p = self.service.create_project(self.owner, "CP branch")
        a = self.service.create_task(self.owner, {"project_id": p["id"], "title": "A", "start_date": "2026-09-01", "due_date": "2026-09-02"})
        b = self.service.create_task(self.owner, {"project_id": p["id"], "title": "B", "start_date": "2026-09-03", "due_date": "2026-09-05"})
        c = self.service.create_task(self.owner, {"project_id": p["id"], "title": "C", "start_date": "2026-09-03", "due_date": "2026-09-06"})
        d = self.service.create_task(self.owner, {"project_id": p["id"], "title": "D", "start_date": "2026-09-07", "due_date": "2026-09-12"})
        self.service.add_task_dependency(self.owner, a["id"], b["id"])
        self.service.add_task_dependency(self.owner, a["id"], c["id"])
        self.service.add_task_dependency(self.owner, c["id"], d["id"])
        cp = {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner, p["id"])}
        self.assertTrue(cp[a["id"]] and cp[c["id"]] and cp[d["id"]])
        self.assertFalse(cp[b["id"]])

    def test_critical_path_ignores_isolated_tasks(self):
        p = self.service.create_project(self.owner, "CP isolated")
        a = self.service.create_task(self.owner, {"project_id": p["id"], "title": "A", "start_date": "2026-09-01", "due_date": "2026-09-20"})
        b = self.service.create_task(self.owner, {"project_id": p["id"], "title": "B", "start_date": "2026-09-01", "due_date": "2026-09-10"})
        cp = {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner, p["id"])}
        self.assertFalse(cp[a["id"]] or cp[b["id"]])

    def test_critical_path_isolated_task_longer_than_chain_is_not_flagged(self):
        # AYW0QC review gap: the test above has no edges, so it returns before the
        # isolation rule runs. Here a chain exists AND an unlinked task outlasts it;
        # the chain must stay critical and neither isolated task may be flagged.
        p = self.service.create_project(self.owner, "CP isolated beside chain")
        a = self.service.create_task(self.owner, {"project_id": p["id"], "title": "A", "start_date": "2026-09-01", "due_date": "2026-09-02"})
        b = self.service.create_task(self.owner, {"project_id": p["id"], "title": "B", "start_date": "2026-09-03", "due_date": "2026-09-04"})
        long_x = self.service.create_task(self.owner, {"project_id": p["id"], "title": "X long", "start_date": "2026-09-01", "due_date": "2026-10-30"})
        short_y = self.service.create_task(self.owner, {"project_id": p["id"], "title": "Y short", "start_date": "2026-09-01", "due_date": "2026-09-01"})
        self.service.add_task_dependency(self.owner, a["id"], b["id"])
        cp = {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner, p["id"])}
        self.assertTrue(cp[a["id"]] and cp[b["id"]])
        self.assertFalse(cp[long_x["id"]])
        self.assertFalse(cp[short_y["id"]])
        # The same holds on the unscoped list (all projects), where tasks from
        # other projects are present too.
        cp_all = {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner)}
        self.assertTrue(cp_all[a["id"]] and cp_all[b["id"]])
        self.assertFalse(cp_all[long_x["id"]] or cp_all[short_y["id"]])

    def test_critical_path_one_day_slack_is_not_critical(self):
        # Pins the zero-slack threshold: C finishes one day before B, so C has
        # exactly one day of slack and must not be flagged.
        p = self.service.create_project(self.owner, "CP one-day slack")
        a = self.service.create_task(self.owner, {"project_id": p["id"], "title": "A", "start_date": "2026-09-01", "due_date": "2026-09-01"})
        b = self.service.create_task(self.owner, {"project_id": p["id"], "title": "B", "start_date": "2026-09-02", "due_date": "2026-09-04"})
        c = self.service.create_task(self.owner, {"project_id": p["id"], "title": "C", "start_date": "2026-09-02", "due_date": "2026-09-03"})
        self.service.add_task_dependency(self.owner, a["id"], b["id"])
        self.service.add_task_dependency(self.owner, a["id"], c["id"])
        cp = {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner, p["id"])}
        self.assertTrue(cp[a["id"]] and cp[b["id"]])
        self.assertFalse(cp[c["id"]])

    def test_critical_path_join_follows_longest_predecessor(self):
        # Two branches merge into J. The forward pass must take the LATEST
        # predecessor finish and the backward pass must propagate slack back
        # through the short branch, including its own predecessor S.
        p = self.service.create_project(self.owner, "CP join")
        long_l = self.service.create_task(self.owner, {"project_id": p["id"], "title": "L", "start_date": "2026-09-01", "due_date": "2026-09-10"})
        s = self.service.create_task(self.owner, {"project_id": p["id"], "title": "S", "start_date": "2026-09-01", "due_date": "2026-09-02"})
        s2 = self.service.create_task(self.owner, {"project_id": p["id"], "title": "S2", "start_date": "2026-09-03", "due_date": "2026-09-04"})
        j = self.service.create_task(self.owner, {"project_id": p["id"], "title": "J", "start_date": "2026-09-11", "due_date": "2026-09-12"})
        self.service.add_task_dependency(self.owner, long_l["id"], j["id"])
        self.service.add_task_dependency(self.owner, s["id"], s2["id"])
        self.service.add_task_dependency(self.owner, s2["id"], j["id"])
        cp = {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner, p["id"])}
        self.assertTrue(cp[long_l["id"]] and cp[j["id"]])
        self.assertFalse(cp[s["id"]] or cp[s2["id"]])

    def test_critical_path_is_computed_per_project(self):
        # A much longer chain in another project must not take the critical path
        # away from this project's chain when both appear in one list.
        p = self.service.create_project(self.owner, "CP short project")
        q = self.service.create_project(self.owner, "CP long project")
        a = self.service.create_task(self.owner, {"project_id": p["id"], "title": "A", "start_date": "2026-09-01", "due_date": "2026-09-01"})
        b = self.service.create_task(self.owner, {"project_id": p["id"], "title": "B", "start_date": "2026-09-02", "due_date": "2026-09-02"})
        c = self.service.create_task(self.owner, {"project_id": q["id"], "title": "C", "start_date": "2026-09-01", "due_date": "2026-10-01"})
        d = self.service.create_task(self.owner, {"project_id": q["id"], "title": "D", "start_date": "2026-10-02", "due_date": "2026-11-01"})
        self.service.add_task_dependency(self.owner, a["id"], b["id"])
        self.service.add_task_dependency(self.owner, c["id"], d["id"])
        cp = {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner)}
        self.assertTrue(cp[a["id"]] and cp[b["id"]])
        self.assertTrue(cp[c["id"]] and cp[d["id"]])

    def test_critical_path_marks_multiple_parallel_paths(self):
        # AYW0QC: full CPM marks EVERY zero-slack activity, so two equal-length
        # parallel chains are both critical (the old longest-single-chain heuristic
        # would have marked only one).
        p = self.service.create_project(self.owner, "CP parallel")
        a = self.service.create_task(self.owner, {"project_id": p["id"], "title": "A", "start_date": "2026-09-01", "due_date": "2026-09-01"})
        b = self.service.create_task(self.owner, {"project_id": p["id"], "title": "B", "start_date": "2026-09-02", "due_date": "2026-09-04"})
        c = self.service.create_task(self.owner, {"project_id": p["id"], "title": "C", "start_date": "2026-09-02", "due_date": "2026-09-04"})
        self.service.add_task_dependency(self.owner, a["id"], b["id"])
        self.service.add_task_dependency(self.owner, a["id"], c["id"])
        cp = {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner, p["id"])}
        self.assertTrue(cp[a["id"]] and cp[b["id"]] and cp[c["id"]])
        # A shorter parallel branch, by contrast, carries slack and is not critical.
        d = self.service.create_task(self.owner, {"project_id": p["id"], "title": "D", "start_date": "2026-09-02", "due_date": "2026-09-02"})
        self.service.add_task_dependency(self.owner, a["id"], d["id"])
        cp2 = {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner, p["id"])}
        self.assertTrue(cp2[b["id"]] and cp2[c["id"]])
        self.assertFalse(cp2[d["id"]])

    def test_critical_path_excludes_cancelled_node(self):
        p = self.service.create_project(self.owner, "CP cancelled")
        a = self.service.create_task(self.owner, {"project_id": p["id"], "title": "A", "start_date": "2026-09-01", "due_date": "2026-09-05"})
        b = self.service.create_task(self.owner, {"project_id": p["id"], "title": "B", "start_date": "2026-09-06", "due_date": "2026-09-08"})
        c = self.service.create_task(self.owner, {"project_id": p["id"], "title": "C", "start_date": "2026-09-09", "due_date": "2026-09-12"})
        self.service.add_task_dependency(self.owner, a["id"], b["id"])
        self.service.add_task_dependency(self.owner, b["id"], c["id"])
        self.update_task(self.owner, b["id"], {"status": "cancelled", "reason": "dropped"})
        cp = {t["id"]: t["is_critical_path"] for t in self.service.list_tasks(self.owner, p["id"])}
        self.assertFalse(cp[a["id"]] or cp[b["id"]] or cp[c["id"]])

    def test_baseline_captured_on_first_schedule_and_immutable(self):
        p = self.service.create_project(self.owner, "Baseline")
        t = self.service.create_task(self.owner, {"project_id": p["id"], "title": "T"})
        self.assertIsNone(self.service.task_detail(self.owner, t["id"])["baseline"]["due_date"])
        self.update_task(self.owner, t["id"], {"start_date": "2026-10-01", "due_date": "2026-10-05", "reason": "plan"})
        base = self.service.task_detail(self.owner, t["id"])["baseline"]
        self.assertEqual((base["start_date"], base["due_date"]), ("2026-10-01", "2026-10-05"))
        self.update_task(self.owner, t["id"], {"due_date": "2026-10-20", "reason": "slip"})
        detail = self.service.task_detail(self.owner, t["id"])
        self.assertEqual(detail["baseline"]["due_date"], "2026-10-05")  # baseline unchanged
        self.assertEqual(detail["due_date"], "2026-10-20")  # current changed

    def test_schedule_proposal_approve_revises_current_without_moving_dependents(self):
        p = self.service.create_project(self.owner, "Sched")
        a = self.service.create_task(self.owner, {"project_id": p["id"], "title": "A", "start_date": "2026-10-01", "due_date": "2026-10-05"})
        b = self.service.create_task(self.owner, {"project_id": p["id"], "title": "B", "start_date": "2026-10-06", "due_date": "2026-10-10", "predecessor_task_id": a["id"]})
        with self.assertRaisesRegex(ValueError, "reason"):
            self.service.propose_schedule(self.owner, a["id"], "2026-10-01", "2026-10-12", "")
        prop = self.service.propose_schedule(self.owner, a["id"], "2026-10-01", "2026-10-12", "client delay")
        self.assertEqual(self.service.get_task(self.owner, a["id"])["due_date"], "2026-10-05")  # not applied yet
        self.assertIn(b["id"], [s["id"] for s in prop["impacted_successors"]])
        self.service.approve_schedule_proposal(self.owner, prop["id"], "ok")
        self.assertEqual(self.service.get_task(self.owner, a["id"])["due_date"], "2026-10-12")  # current revised
        self.assertEqual(self.service.get_task(self.owner, b["id"])["due_date"], "2026-10-10")  # dependent NOT moved
        self.assertIn("schedule_revised", [e["event_type"] for e in self.service.task_events(self.owner, a["id"])])

    def test_manager_schedule_decision_is_an_owner_request(self):
        project = self.service.create_project(self.owner, "Governed schedule")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Milestone", "due_date": "2026-10-05",
        })
        manager = self.service.create_user(
            self.owner, "schedule-manager@example.org", "Manager", "manager password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        proposal = self.service.propose_schedule(
            manager, task["id"], None, "2026-10-20", "Manager proposes a new date"
        )

        outcome = self.service.approve_schedule_proposal(manager, proposal["id"], "Manager recommendation")

        self.assertEqual(outcome["request"]["action"], "approve_schedule_proposal")
        self.assertEqual(self.service.get_task(self.owner, task["id"])["due_date"], "2026-10-05")
        self.assertEqual(self.service.get_schedule_proposal(self.owner, proposal["id"])["status"], "pending")
        self.service.approve_schedule_proposal(self.owner, proposal["id"], "Owner approves")
        self.assertEqual(self.service.get_task(self.owner, task["id"])["due_date"], "2026-10-20")

    def test_manager_schedule_rejection_is_an_owner_request(self):
        project = self.service.create_project(self.owner, "Governed rejection")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Milestone", "due_date": "2026-10-05",
        })
        manager = self.service.create_user(
            self.owner, "reject-manager@example.org", "Manager", "manager password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        proposal = self.service.propose_schedule(manager, task["id"], None, "2026-10-20", "Slip requested")

        outcome = self.service.reject_schedule_proposal(manager, proposal["id"], "Manager recommends rejection")

        self.assertEqual(outcome["request"]["action"], "reject_schedule_proposal")
        self.assertEqual(self.service.get_schedule_proposal(self.owner, proposal["id"])["status"], "pending")
        self.assertEqual(self.service.get_task(self.owner, task["id"])["due_date"], "2026-10-05")
        rejected = self.service.reject_schedule_proposal(self.owner, proposal["id"], "Owner rejects")
        self.assertEqual(rejected["status"], "rejected")

    def test_schedule_proposal_reject_is_noop_and_requires_reason(self):
        p = self.service.create_project(self.owner, "RejectSched")
        t = self.service.create_task(self.owner, {"project_id": p["id"], "title": "T", "due_date": "2026-10-05"})
        prop = self.service.propose_schedule(self.owner, t["id"], None, "2026-10-20", "maybe")
        with self.assertRaisesRegex(ValueError, "reason"):
            self.service.reject_schedule_proposal(self.owner, prop["id"], "")
        self.service.reject_schedule_proposal(self.owner, prop["id"], "not needed")
        self.assertEqual(self.service.get_task(self.owner, t["id"])["due_date"], "2026-10-05")  # unchanged
        self.assertEqual(self.service.list_schedule_proposals(self.owner, t["id"])[0]["status"], "rejected")

    def test_search_is_scope_limited(self):
        visible = self.service.create_project(self.owner, "Visible Alpha")
        hidden = self.service.create_project(self.owner, "Hidden Alpha")
        self.service.create_task(self.owner, {"project_id": visible["id"], "title": "Alpha task one"})
        self.service.create_task(self.owner, {"project_id": hidden["id"], "title": "Alpha task two"})
        member = self.service.create_user(self.owner, "s@example.org", "S", "member password safe")
        self.service.grant_project_access(self.owner, visible["id"], member["id"], "viewer")
        owner_res = self.service.search(self.owner, "Alpha")
        self.assertEqual(len(owner_res["tasks"]), 2)
        self.assertEqual(len(owner_res["projects"]), 2)
        member_res = self.service.search(member, "Alpha")
        self.assertEqual([t["title"] for t in member_res["tasks"]], ["Alpha task one"])
        self.assertEqual([p["name"] for p in member_res["projects"]], ["Visible Alpha"])

    def test_export_echoes_as_of_and_filters_and_is_scoped(self):
        p = self.service.create_project(self.owner, "Export")
        self.service.create_task(self.owner, {"project_id": p["id"], "title": "Keep", "status": "in_progress"})
        self.service.create_task(self.owner, {"project_id": p["id"], "title": "Other"})
        export = self.service.export_tasks(self.owner, {"project_id": p["id"], "status": "in_progress"})
        self.assertIn("as_of", export)
        self.assertEqual(export["filters"]["status"], "in_progress")
        self.assertEqual([t["title"] for t in export["tasks"]], ["Keep"])

    def test_export_is_scope_limited_for_a_member(self):
        # Y3WC71 review gap 1: export authorization must be guarded by a non-owner case.
        visible = self.service.create_project(self.owner, "Export visible")
        hidden = self.service.create_project(self.owner, "Export hidden")
        self.service.create_task(self.owner, {"project_id": visible["id"], "title": "Visible export task"})
        self.service.create_task(self.owner, {"project_id": hidden["id"], "title": "Secret hidden task"})
        member = self.service.create_user(self.owner, "exp@example.org", "Exp", "member password safe")
        self.service.grant_project_access(self.owner, visible["id"], member["id"], "viewer")
        export = self.service.export_tasks(member, {})
        self.assertEqual([t["title"] for t in export["tasks"]], ["Visible export task"])
        with self.assertRaises(Forbidden):
            self.service.export_tasks(member, {"project_id": hidden["id"]})

    def test_working_calendar_default_restrictions_and_holidays(self):
        from datetime import date, timedelta
        p = self.service.create_project(self.owner, "Cal")
        span = ("2026-09-14", "2026-09-20")  # any 7 consecutive days = one of each weekday
        self.assertEqual(self.service.working_days_between(p["id"], *span), 7)  # permissive default
        self.service.set_working_days(self.owner, p["id"], "01234")  # Mon–Fri
        self.assertEqual(self.service.working_days_between(p["id"], *span), 5)  # Sat + Sun excluded
        start = date.fromisoformat(span[0])
        weekday_offset = next(x for x in range(7) if (start + timedelta(days=x)).weekday() < 5)
        holiday = (start + timedelta(days=weekday_offset)).isoformat()
        self.service.add_holiday(self.owner, p["id"], holiday, "Test holiday")
        self.assertFalse(self.service.is_working_day(p["id"], holiday))
        self.assertEqual(self.service.working_days_between(p["id"], *span), 4)  # one more working day gone
        with self.assertRaisesRegex(ValueError, "working day"):
            self.service.set_working_days(self.owner, p["id"], "")

    def test_calendar_management_is_owner_only(self):
        p = self.service.create_project(self.owner, "CalOwner")
        member = self.service.create_user(self.owner, "c@example.org", "C", "member password safe")
        with self.assertRaises(Forbidden):
            self.service.set_working_days(member, p["id"], "01234")
        with self.assertRaises(Forbidden):
            self.service.add_holiday(member, p["id"], "2026-12-25", "Xmas")

    def test_budget_rollup_counts_cross_entity_once_and_sums_per_currency(self):
        self.service.seed_default_entities(self.owner)
        ents = {e["name"]: e["id"] for e in self.service.list_entities(self.owner)}
        a = self.service.create_project(self.owner, "A")
        self.service.set_project_entities(self.owner, a["id"], [ents["RDI Pakistan"]])
        self.service.set_project_budget(self.owner, a["id"], 1000000, "PKR")
        b = self.service.create_project(self.owner, "B")  # cross-entity, primary = RDI - Global
        self.service.set_project_entities(self.owner, b["id"], [ents["RDI Pakistan"], ents["RDI - Global"]])
        self.service.set_project_budget(self.owner, b["id"], 500000, "PKR")
        self.service.set_primary_entity(self.owner, b["id"], ents["RDI - Global"])
        c = self.service.create_project(self.owner, "C")
        self.service.set_project_entities(self.owner, c["id"], [ents["Rupani Foundation USA"]])
        self.service.set_project_budget(self.owner, c["id"], 30000, "USD")
        roll = {r["entity_name"]: r for r in self.service.portfolio_rollup(self.owner)}
        self.assertEqual(roll["RDI Pakistan"]["budgets"], {"PKR": 1000000})   # B not double-counted here
        self.assertEqual(roll["RDI - Global"]["budgets"], {"PKR": 500000})    # B counted once, toward primary
        self.assertEqual(roll["Rupani Foundation USA"]["budgets"], {"USD": 30000})  # separate currency

    def test_primary_entity_must_be_a_linked_entity(self):
        self.service.seed_default_entities(self.owner)
        ents = {e["name"]: e["id"] for e in self.service.list_entities(self.owner)}
        p = self.service.create_project(self.owner, "P")
        self.service.set_project_entities(self.owner, p["id"], [ents["RDI Pakistan"]])
        with self.assertRaisesRegex(ValueError, "primary entity"):
            self.service.set_primary_entity(self.owner, p["id"], ents["Rupani Foundation USA"])
        self.service.set_primary_entity(self.owner, p["id"], ents["RDI Pakistan"])  # linked one is fine

    def test_portfolio_is_scope_limited(self):
        self.service.seed_default_entities(self.owner)
        ents = {e["name"]: e["id"] for e in self.service.list_entities(self.owner)}
        visible = self.service.create_project(self.owner, "Visible")
        self.service.set_project_entities(self.owner, visible["id"], [ents["RDI Pakistan"]])
        hidden = self.service.create_project(self.owner, "Hidden")
        self.service.set_project_entities(self.owner, hidden["id"], [ents["RDI - Global"]])
        member = self.service.create_user(self.owner, "pf@example.org", "PF", "member password safe")
        self.service.grant_project_access(self.owner, visible["id"], member["id"], "viewer")
        names = {r["entity_name"] for r in self.service.portfolio_rollup(member)}
        self.assertIn("RDI Pakistan", names)
        self.assertNotIn("RDI - Global", names)

    def test_concurrent_opposite_dependencies_cannot_create_a_cycle(self):
        project = self.service.create_project(self.owner, "Concurrent dependencies")
        one = self.service.create_task(self.owner, {"project_id": project["id"], "title": "One"})
        two = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Two"})
        barrier = threading.Barrier(2)
        results = []
        result_lock = threading.Lock()

        def add(predecessor_id, successor_id):
            db = connect(self.db_path)
            try:
                barrier.wait(timeout=5)
                try:
                    AstraService(db).add_task_dependency(
                        self.owner, predecessor_id, successor_id
                    )
                    outcome = "added"
                except ValueError as exc:
                    outcome = "cycle" if "cycle" in str(exc) else f"error:{exc}"
                with result_lock:
                    results.append(outcome)
            finally:
                db.close()

        threads = [
            threading.Thread(target=add, args=(one["id"], two["id"])),
            threading.Thread(target=add, args=(two["id"], one["id"])),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertCountEqual(results, ["added", "cycle"])
        count = self.db.execute("SELECT COUNT(*) FROM task_dependencies").fetchone()[0]
        self.assertEqual(count, 1)

    def test_task_attachment_link_lifecycle_and_audit(self):
        project = self.service.create_project(self.owner, "Audit 2026")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Draft report"})
        real = Path(self.temp.name) / "deliverable.pdf"
        real.write_text("final")
        added = self.service.add_task_attachment(self.owner, task["id"], str(real), note="Signed copy")
        # Display name defaults to the file's basename; the link resolves on disk.
        self.assertEqual(added["display_name"], "deliverable.pdf")
        self.assertTrue(added["exists"])
        self.assertEqual(added["note"], "Signed copy")
        listed = self.service.list_task_attachments(self.owner, task["id"])
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["added_by_name"], "Owner")
        detail = self.service.task_detail(self.owner, task["id"])
        self.assertEqual(len(detail["attachments"]), 1)
        events = [e["event_type"] for e in self.service.task_events(self.owner, task["id"])]
        self.assertIn("attachment_added", events)
        self.service.remove_task_attachment(self.owner, task["id"], added["id"])
        self.assertEqual(self.service.list_task_attachments(self.owner, task["id"]), [])
        # Removing the link never touches the file on disk.
        self.assertTrue(real.exists())
        events = [e["event_type"] for e in self.service.task_events(self.owner, task["id"])]
        self.assertIn("attachment_removed", events)

    def test_attachment_requires_a_path(self):
        project = self.service.create_project(self.owner, "P")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "T"})
        with self.assertRaisesRegex(ValueError, "path"):
            self.service.add_task_attachment(self.owner, task["id"], "   ")

    def test_attachment_flags_a_missing_file(self):
        project = self.service.create_project(self.owner, "P")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "T"})
        attachment = self.service.add_task_attachment(
            self.owner, task["id"], str(Path(self.temp.name) / "nope.pdf"), display_name="Missing"
        )
        self.assertFalse(attachment["exists"])

    def test_attachment_authorization(self):
        project = self.service.create_project(self.owner, "Restricted")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Secret"})
        self.service.add_task_attachment(self.owner, task["id"], "/data/secret.pdf")
        outsider = self.service.create_user(self.owner, "out@example.org", "Outsider", "password outsider ok", "member")
        # No project access: cannot even see the link records.
        with self.assertRaises(Forbidden):
            self.service.list_task_attachments(outsider, task["id"])
        viewer = self.service.create_user(self.owner, "view@example.org", "Viewer", "password viewer okay", "member")
        self.service.grant_project_access(self.owner, project["id"], viewer["id"], "viewer")
        # A viewer sees the link but cannot add — adding is management-gated.
        self.assertEqual(len(self.service.list_task_attachments(viewer, task["id"])), 1)
        with self.assertRaises(Forbidden):
            self.service.add_task_attachment(viewer, task["id"], "/data/x.pdf")
        # HS3JRY (owner decision 2026-09-20): every attachment mutation is
        # App-Owner-only. Authorized project users retain read access.
        manager = self.service.create_user(self.owner, "mgr@example.org", "Manager", "password manager okay", "member")
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        self.assertEqual(len(self.service.list_task_attachments(manager, task["id"])), 1)
        with self.assertRaises(Forbidden):
            self.service.add_task_attachment(manager, task["id"], "/data/mgr.pdf")
        chairman = self.service.create_user(
            self.owner, "chair@example.org", "Chairman", "password chairman okay", "chairman"
        )
        self.assertEqual(len(self.service.list_task_attachments(chairman, task["id"])), 1)
        with self.assertRaises(Forbidden):
            self.service.add_task_attachment(chairman, task["id"], "/data/chair.pdf")
        owner_added = self.service.add_task_attachment(self.owner, task["id"], "/data/owner.pdf")
        with self.assertRaises(Forbidden):
            self.service.remove_task_attachment(manager, task["id"], owner_added["id"])
        self.assertEqual(self.service.list_notifications(self.owner)[0]["kind"], "attachment_removal_blocked")
        # The App Owner can remove.
        self.service.remove_task_attachment(self.owner, task["id"], owner_added["id"])
        remaining = {a["path"] for a in self.service.list_task_attachments(self.owner, task["id"])}
        self.assertNotIn("/data/owner.pdf", remaining)

    def _seed_template_project(self):
        project = self.service.create_project(self.owner, "Annual Audit 2026")
        kickoff = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Kickoff",
            "start_date": "2026-01-05", "due_date": "2026-01-09", "criticality": "high",
        })
        fieldwork = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Fieldwork",
            "start_date": "2026-01-12", "due_date": "2026-01-23", "criticality": "critical",
            "predecessor_task_id": kickoff["id"],
        })
        self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Sampling",
            "start_date": "2026-01-12", "due_date": "2026-01-16", "parent_task_id": fieldwork["id"],
        })
        self.service.add_task_attachment(self.owner, fieldwork["id"], "/refs/audit-checklist.xlsx")
        # Give Kickoff real history so we can prove it is NOT carried into the template.
        submission = self.service.submit_task(self.owner, kickoff["id"])
        self.service.accept_submission(self.owner, submission["id"])
        return project, kickoff, fieldwork

    def test_project_template_captures_structure_not_history(self):
        self._seed_template_project()
        template = self.service.save_project_as_template(
            self.owner, self.service.list_projects(self.owner)[0]["id"], "Annual Audit"
        )
        body = template["body"]
        self.assertEqual(body["kind"], "project")
        self.assertEqual(len(body["tasks"]), 3)
        by_title = {t["title"]: t for t in body["tasks"]}
        # Dates are stored as day-offsets from the earliest date (Kickoff start, 2026-01-05).
        self.assertEqual((by_title["Kickoff"]["start_offset"], by_title["Kickoff"]["due_offset"]), (0, 4))
        self.assertEqual((by_title["Fieldwork"]["start_offset"], by_title["Fieldwork"]["due_offset"]), (7, 18))
        # Structure is captured; live state and history are not.
        self.assertNotIn("status", by_title["Kickoff"])
        self.assertNotIn("owner_user_id", by_title["Kickoff"])
        self.assertEqual(len(body["dependencies"]), 1)
        self.assertEqual(len(by_title["Fieldwork"]["attachments"]), 1)
        self.assertIsNotNone(by_title["Sampling"]["parent_local_id"])

    def test_project_created_from_template_reapplies_offsets_and_resets_state(self):
        self._seed_template_project()
        template = self.service.save_project_as_template(
            self.owner, self.service.list_projects(self.owner)[0]["id"], "Annual Audit"
        )
        project = self.service.create_project_from_template(
            self.owner, template["id"], "Annual Audit 2027", anchor_date="2027-02-01"
        )
        tasks = {t["title"]: t for t in self.service.list_tasks(self.owner, project["id"])}
        self.assertEqual(set(tasks), {"Kickoff", "Fieldwork", "Sampling"})
        # Offsets re-applied to the new anchor, preserving the original spacing.
        self.assertEqual((tasks["Kickoff"]["start_date"], tasks["Kickoff"]["due_date"]), ("2027-02-01", "2027-02-05"))
        self.assertEqual((tasks["Fieldwork"]["start_date"], tasks["Fieldwork"]["due_date"]), ("2027-02-08", "2027-02-19"))
        # Every task starts fresh: draft, unassigned, no progress.
        for task in tasks.values():
            self.assertEqual(task["status"], "draft")
            self.assertIsNone(task["owner_user_id"])
        # Hierarchy, dependency and attachment link are recreated.
        self.assertEqual(tasks["Sampling"]["parent_task_id"], tasks["Fieldwork"]["id"])
        deps = self.db.execute(
            "SELECT COUNT(*) c FROM task_dependencies d JOIN tasks t ON t.id=d.successor_task_id WHERE t.project_id=?",
            (project["id"],),
        ).fetchone()["c"]
        self.assertEqual(deps, 1)
        links = self.service.list_task_attachments(self.owner, tasks["Fieldwork"]["id"])
        self.assertEqual([a["path"] for a in links], ["/refs/audit-checklist.xlsx"])
        # No history rode along: the new Kickoff has only its creation event and no submissions.
        events = [e["event_type"] for e in self.service.task_events(self.owner, tasks["Kickoff"]["id"])]
        self.assertEqual(events, ["task_created"])
        self.assertEqual(self.service.list_task_submissions(self.owner, tasks["Kickoff"]["id"]), [])
        self.assertIsNone(tasks["Kickoff"]["accepted_submission_id"])

    def _seed_role_project(self):
        """A project whose tasks are owned by the App Owner, a project manager and a member."""
        project = self.service.create_project(self.owner, "Recurring")
        manager = self.service.create_user(self.owner, "pm@example.org", "Pat Manager", "member password safe", "member")
        member = self.service.create_user(self.owner, "lead@example.org", "Lead Person", "member password safe", "member")
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        self.service.grant_project_access(self.owner, project["id"], member["id"], "member")
        self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Owner review", "owner_user_id": self.owner["id"]})
        self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Plan", "owner_user_id": manager["id"]})
        self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Member task", "owner_user_id": member["id"]})
        self.service.create_task(self.owner, {"project_id": project["id"], "title": "Nobody's"})
        return project, manager, member

    def test_template_stores_a_suggested_role_not_a_person(self):
        # 8B9NBH (owner decision 2026-09-15): the suggested owner is ROLE-based.
        project, _, _ = self._seed_role_project()
        template = self.service.save_project_as_template(self.owner, project["id"], "Recurring tmpl")
        by_title = {t["title"]: t for t in template["body"]["tasks"]}
        self.assertEqual(by_title["Owner review"]["suggested_role"], "owner")
        self.assertEqual(by_title["Plan"]["suggested_role"], "manager")
        self.assertEqual(by_title["Member task"]["suggested_role"], "member")
        self.assertIsNone(by_title["Nobody's"]["suggested_role"])
        for task in by_title.values():  # no person rides along: no name, no user id
            self.assertNotIn("suggested_owner", task)
            self.assertNotIn("owner_user_id", task)
        listed = self.service.list_templates(self.owner)[0]
        self.assertEqual(listed["roles"], ["owner", "manager", "member"])

    def test_project_from_template_resolves_each_role_to_the_picked_person(self):
        project, _, _ = self._seed_role_project()
        template = self.service.save_project_as_template(self.owner, project["id"], "Recurring tmpl")
        new_pm = self.service.create_user(self.owner, "pm2@example.org", "New PM", "member password safe", "member")
        new_lead = self.service.create_user(self.owner, "lead2@example.org", "New Lead", "member password safe", "member")
        new_project = self.service.create_project_from_template(
            self.owner, template["id"], "Recurring 2",
            role_assignments={"manager": new_pm["id"], "member": new_lead["id"]},
        )
        tasks = {t["title"]: t for t in self.service.list_tasks(self.owner, new_project["id"])}
        self.assertEqual(tasks["Owner review"]["owner_user_id"], self.owner["id"])  # 'owner' resolves itself
        self.assertEqual(tasks["Plan"]["owner_user_id"], new_pm["id"])
        self.assertEqual(tasks["Member task"]["owner_user_id"], new_lead["id"])
        self.assertIsNone(tasks["Nobody's"]["owner_user_id"])
        # The picked people get that role on the new project, so they can see and work their tasks.
        roles = {row["user_id"]: row["role"] for row in self.db.execute(
            "SELECT user_id, role FROM memberships WHERE project_id=?", (new_project["id"],))}
        self.assertEqual(roles, {new_pm["id"]: "manager", new_lead["id"]: "member"})
        self.assertIn(new_project["id"], {p["id"] for p in self.service.list_projects(new_lead)})
        # The pre-fill is on the record: who got the task, from which role.
        created = self.service.task_events(self.owner, tasks["Plan"]["id"])[0]
        self.assertEqual(created["event_type"], "task_created")
        after = json.loads(created["after_json"])
        self.assertEqual((after["owner_user_id"], after["suggested_role"]), (new_pm["id"], "manager"))

    def test_project_from_template_without_picks_leaves_project_roles_unassigned(self):
        project, _, _ = self._seed_role_project()
        template = self.service.save_project_as_template(self.owner, project["id"], "Recurring tmpl")
        new_project = self.service.create_project_from_template(self.owner, template["id"], "Recurring 2")
        tasks = {t["title"]: t for t in self.service.list_tasks(self.owner, new_project["id"])}
        self.assertEqual(tasks["Owner review"]["owner_user_id"], self.owner["id"])
        self.assertIsNone(tasks["Plan"]["owner_user_id"])  # a new project has no manager yet
        self.assertIsNone(tasks["Member task"]["owner_user_id"])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) c FROM memberships WHERE project_id=?", (new_project["id"],)).fetchone()["c"], 0)

    def test_role_assignments_are_validated_before_anything_is_written(self):
        project, manager, _ = self._seed_role_project()
        template = self.service.save_project_as_template(self.owner, project["id"], "Recurring tmpl")
        projects_before = len(self.service.list_projects(self.owner))
        inactive = self.service.create_user(self.owner, "gone@example.org", "Gone", "member password safe", "member")
        self.service.set_user_active(self.owner, inactive["id"], False)
        chairman = self.service.create_user(self.owner, "c@example.org", "Chair", "member password safe", "chairman")
        for label, picks in (
            ("unknown role", {"auditor": manager["id"]}),
            ("unknown user", {"manager": "no-such-user"}),
            ("inactive user", {"manager": inactive["id"]}),
            ("owner role is fixed", {"owner": manager["id"]}),
            ("chairman as project manager", {"manager": chairman["id"]}),
            ("not a mapping", ["manager"]),
            ("one person, two project roles", {"manager": manager["id"], "member": manager["id"]}),
        ):
            with self.subTest(label):
                with self.assertRaises(ValueError):
                    self.service.create_project_from_template(
                        self.owner, template["id"], "Bad picks", role_assignments=picks)
        self.assertEqual(len(self.service.list_projects(self.owner)), projects_before)

    def test_task_template_resolves_role_to_the_unique_holder_in_the_target_project(self):
        project, manager, member = self._seed_role_project()
        plan = next(t for t in self.service.list_tasks(self.owner, project["id"]) if t["title"] == "Plan")
        template = self.service.save_task_as_template(self.owner, plan["id"], "Plan block")
        self.assertEqual(template["body"]["tasks"][0]["suggested_role"], "manager")
        # Same project: exactly one manager -> pre-filled.
        self.service.create_task_from_template(self.owner, template["id"], project["id"])
        plans = [t for t in self.service.list_tasks(self.owner, project["id"]) if t["title"] == "Plan"]
        self.assertEqual([t["owner_user_id"] for t in plans], [manager["id"], manager["id"]])
        # A second manager makes the role ambiguous -> unassigned, never a guess.
        second = self.service.create_user(self.owner, "pm3@example.org", "Second PM", "member password safe", "member")
        self.service.grant_project_access(self.owner, project["id"], second["id"], "manager")
        self.service.create_task_from_template(self.owner, template["id"], project["id"])
        plans = [t for t in self.service.list_tasks(self.owner, project["id"]) if t["title"] == "Plan"]
        self.assertEqual(sorted(t["owner_user_id"] or "" for t in plans), sorted(["", manager["id"], manager["id"]]))
        # An explicit pick settles it, but must already hold that role on the target project.
        self.service.create_task_from_template(
            self.owner, template["id"], project["id"], role_assignments={"manager": second["id"]})
        self.assertIn(second["id"], {t["owner_user_id"] for t in self.service.list_tasks(self.owner, project["id"])})
        with self.assertRaises(ValueError):
            self.service.create_task_from_template(
                self.owner, template["id"], project["id"], role_assignments={"manager": member["id"]})

    def test_legacy_name_based_templates_still_instantiate(self):
        # Templates saved before 8B9NBH's role rework hold a display name in
        # 'suggested_owner'. They load read-compatibly: owner/chairman names map
        # to that role; anyone else is pre-filled only if still assignable.
        project, _, member = self._seed_role_project()
        body = {"kind": "project", "anchor": None, "dependencies": [], "project": {},
                "tasks": [
                    {"local_id": 0, "title": "Owner review", "suggested_owner": self.owner["display_name"],
                     "parent_local_id": None, "attachments": []},
                    {"local_id": 1, "title": "Member task", "suggested_owner": "Lead Person",
                     "parent_local_id": None, "attachments": []},
                    {"local_id": 2, "title": "Ghost task", "suggested_owner": "Nobody Known",
                     "parent_local_id": None, "attachments": []},
                ]}
        self.db.execute(
            "INSERT INTO templates(id,kind,name,description,body_json,created_by,created_at) VALUES(?,?,?,?,?,?,?)",
            ("legacy-1", "project", "Legacy", "", json.dumps(body), self.owner["id"], "2026-09-19T00:00:00Z"))
        self.assertEqual(self.service.list_templates(self.owner)[0]["roles"], ["owner"])
        new_project = self.service.create_project_from_template(self.owner, "legacy-1", "From legacy")
        tasks = {t["title"]: t for t in self.service.list_tasks(self.owner, new_project["id"])}
        self.assertEqual(tasks["Owner review"]["owner_user_id"], self.owner["id"])
        self.assertIsNone(tasks["Member task"]["owner_user_id"])  # not on the new project
        self.assertIsNone(tasks["Ghost task"]["owner_user_id"])
        body["kind"] = "task"
        self.db.execute("INSERT INTO templates(id,kind,name,description,body_json,created_by,created_at)"
                        " VALUES(?,?,?,?,?,?,?)", ("legacy-2", "task", "Legacy task", "", json.dumps(body),
                                                   self.owner["id"], "2026-09-19T00:00:00Z"))
        self.service.create_task_from_template(self.owner, "legacy-2", project["id"])
        members = [t for t in self.service.list_tasks(self.owner, project["id"]) if t["title"] == "Member task"]
        self.assertEqual(sorted(t["owner_user_id"] for t in members), [member["id"], member["id"]])

    def test_every_template_action_is_owner_only_for_every_non_owner_role(self):
        # Pins require_owner on each template method separately. The non-owners
        # can all view the project and its tasks, so without require_owner the
        # save methods would succeed; the count check proves nothing was written.
        project, manager, member = self._seed_role_project()
        viewer = self.service.create_user(self.owner, "v@example.org", "Viewer", "member password safe", "member")
        self.service.grant_project_access(self.owner, project["id"], viewer["id"], "viewer")
        chairman = self.service.create_user(self.owner, "ch@example.org", "Chair", "member password safe", "chairman")
        task = self.service.list_tasks(self.owner, project["id"])[0]
        project_tmpl = self.service.save_project_as_template(self.owner, project["id"], "P")
        task_tmpl = self.service.save_task_as_template(self.owner, task["id"], "T")
        actions = {
            "save_project_as_template": lambda a: self.service.save_project_as_template(a, project["id"], "x"),
            "save_task_as_template": lambda a: self.service.save_task_as_template(a, task["id"], "x"),
            "list_templates": lambda a: self.service.list_templates(a),
            "get_template": lambda a: self.service.get_template(a, task_tmpl["id"]),
            "delete_template": lambda a: self.service.delete_template(a, task_tmpl["id"]),
            "create_project_from_template": lambda a: self.service.create_project_from_template(
                a, project_tmpl["id"], "x"),
            "create_task_from_template": lambda a: self.service.create_task_from_template(
                a, task_tmpl["id"], project["id"]),
        }
        tasks_before = len(self.service.list_tasks(self.owner, project["id"]))
        for label, actor in (("manager", manager), ("member", member), ("viewer", viewer), ("chairman", chairman)):
            for name, call in actions.items():
                with self.subTest(role=label, action=name):
                    with self.assertRaises(Forbidden):
                        call(actor)
        self.assertEqual(self.db.execute("SELECT COUNT(*) c FROM templates").fetchone()["c"], 2)
        self.assertEqual(len(self.service.list_projects(self.owner)), 1)
        self.assertEqual(len(self.service.list_tasks(self.owner, project["id"])), tasks_before)

    def test_task_subtree_template_roundtrip(self):
        _, _, fieldwork = self._seed_template_project()
        template = self.service.save_task_as_template(self.owner, fieldwork["id"], "Fieldwork block")
        self.assertEqual(template["kind"], "task")
        self.assertEqual(len(template["body"]["tasks"]), 2)  # Fieldwork + Sampling
        target = self.service.create_project(self.owner, "Second engagement")
        result = self.service.create_task_from_template(
            self.owner, template["id"], target["id"], anchor_date="2027-03-01"
        )
        self.assertEqual(result["created"], 2)
        titles = {t["title"] for t in self.service.list_tasks(self.owner, target["id"])}
        self.assertEqual(titles, {"Fieldwork", "Sampling"})

    def test_templates_are_owner_only(self):
        project, _, fieldwork = self._seed_template_project()
        member = self.service.create_user(self.owner, "m@example.org", "Member", "member password safe", "member")
        self.service.grant_project_access(self.owner, project["id"], member["id"], "manager")
        with self.assertRaises(Forbidden):
            self.service.save_project_as_template(member, project["id"], "Sneaky")
        with self.assertRaises(Forbidden):
            self.service.list_templates(member)
        template = self.service.save_project_as_template(self.owner, project["id"], "Owner only")
        with self.assertRaises(Forbidden):
            self.service.create_project_from_template(member, template["id"], "Nope")
        with self.assertRaises(Forbidden):
            self.service.delete_template(member, template["id"])

    def _accepted_task(self, project_id, title="Deliverable"):
        task = self.service.create_task(self.owner, {"project_id": project_id, "title": title})
        submission = self.service.submit_task(self.owner, task["id"], "done")
        self.service.accept_submission(self.owner, submission["id"])
        task["submission_id"] = submission["id"]  # for tests that then mark it a final result
        return task

    def test_accepting_a_submission_does_not_auto_record_a_final_result(self):
        # CS93C6 (owner decision 2026-09-15): acceptance is NOT an auto final result;
        # every final result must be an explicit manual mark.
        project = self.service.create_project(self.owner, "Deliverables")
        task = self._accepted_task(project["id"], "Signed report")
        self.assertEqual(self.service.list_final_results(self.owner), [])
        # It becomes eligible to be marked by hand, and only then appears.
        marked = self.service.mark_final_result(self.owner, task["id"], "submission", task["submission_id"])
        results = self.service.list_final_results(self.owner)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_type"], "submission")
        self.assertIn("Signed report", results[0]["title"])
        self.assertEqual(results[0]["project_name"], "Deliverables")
        self.assertEqual(results[0]["id"], marked["id"])

    def test_attachment_can_be_marked_and_unmarked_as_final_result(self):
        project = self.service.create_project(self.owner, "Outputs")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Model"})
        attachment = self.service.add_task_attachment(self.owner, task["id"], "/out/model.xlsx")
        marked = self.service.mark_final_result(self.owner, task["id"], "attachment", attachment["id"])
        self.assertEqual([r["source_type"] for r in self.service.list_final_results(self.owner)], ["attachment"])
        self.service.unmark_final_result(self.owner, marked["id"])
        self.assertEqual(self.service.list_final_results(self.owner), [])

    def test_only_an_accepted_submission_can_be_a_final_result(self):
        project = self.service.create_project(self.owner, "Pending")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "WIP"})
        submission = self.service.submit_task(self.owner, task["id"])
        with self.assertRaisesRegex(ValueError, "accepted"):
            self.service.mark_final_result(self.owner, task["id"], "submission", submission["id"])

    def test_final_results_are_scoped_to_project_members(self):
        project_a = self.service.create_project(self.owner, "Alpha")
        project_b = self.service.create_project(self.owner, "Beta")
        alpha = self._accepted_task(project_a["id"], "Alpha output")
        self.service.mark_final_result(self.owner, alpha["id"], "submission", alpha["submission_id"])
        member = self.service.create_user(self.owner, "fr@example.org", "Member", "member password safe", "member")
        self.service.grant_project_access(self.owner, project_b["id"], member["id"], "viewer")
        self.assertEqual(self.service.list_final_results(member), [])
        self.service.grant_project_access(self.owner, project_a["id"], member["id"], "viewer")
        self.assertEqual(len(self.service.list_final_results(member)), 1)

    def test_final_result_mutations_are_owner_only_for_every_non_owner_role(self):
        project = self.service.create_project(self.owner, "Governed results")
        task = self._accepted_task(project["id"], "Approved report")
        manager = self.service.create_user(
            self.owner, "fr-manager@example.org", "Manager", "manager password safe"
        )
        viewer = self.service.create_user(
            self.owner, "fr-viewer@example.org", "Viewer", "viewer password safe"
        )
        chairman = self.service.create_user(
            self.owner, "fr-chair@example.org", "Chairman", "chairman password safe", "chairman"
        )
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        self.service.grant_project_access(self.owner, project["id"], viewer["id"], "viewer")

        for actor in (manager, chairman, viewer):
            with self.subTest(role=actor["global_role"], action="mark"):
                with self.assertRaises(Forbidden):
                    self.service.mark_final_result(
                        actor, task["id"], "submission", task["submission_id"], "Unauthorized attempt"
                    )
        marked = self.service.mark_final_result(
            self.owner, task["id"], "submission", task["submission_id"], "Owner publication"
        )
        for actor in (manager, chairman, viewer):
            self.assertEqual(len(self.service.list_final_results(actor)), 1)
            with self.subTest(role=actor["global_role"], action="unmark"):
                with self.assertRaises(Forbidden):
                    self.service.unmark_final_result(actor, marked["id"])
        self.assertEqual(len(self.service.list_final_results(self.owner)), 1)

    def test_read_only_chairman_attachment_removal_is_blocked_and_notifies_owner(self):
        project = self.service.create_project(self.owner, "Chairman file boundary")
        chairman = self.service.create_user(
            self.owner, "file-chair@example.org", "Chairman", "chairman password safe", "chairman"
        )
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Board pack"})
        attachment = self.service.add_task_attachment(self.owner, task["id"], "/data/board-pack.pdf")

        # Organization-wide read: the Chairman sees the link record without any membership.
        self.assertEqual(len(self.service.list_task_attachments(chairman, task["id"])), 1)
        with self.assertRaises(Forbidden):
            self.service.remove_task_attachment(chairman, task["id"], attachment["id"])

        # Same outcome the Manager and Viewer cases assert: link kept, attempt audited, Owner told.
        self.assertEqual(len(self.service.list_task_attachments(self.owner, task["id"])), 1)
        blocked = [e for e in self.service.task_events(self.owner, task["id"])
                   if e["event_type"] == "attachment_removal_blocked"]
        self.assertEqual([e["actor_user_id"] for e in blocked], [chairman["id"]])
        self.assertIn(attachment["id"], blocked[0]["after_json"])
        owner_notes = [n for n in self.service.list_notifications(self.owner)
                       if n["kind"] == "attachment_removal_blocked"]
        self.assertEqual(len(owner_notes), 1)
        self.assertEqual(owner_notes[0]["task_id"], task["id"])
        self.assertEqual(self.service.list_owner_action_requests(self.owner), [])

    def test_templates_access_and_calendar_administration_are_owner_only_for_every_non_owner_role(self):
        project = self.service.create_project(self.owner, "Administered")
        self.service.create_task(self.owner, {"project_id": project["id"], "title": "Kick-off"})
        manager = self.service.create_user(
            self.owner, "admin-manager@example.org", "Manager", "manager password safe"
        )
        viewer = self.service.create_user(
            self.owner, "admin-viewer@example.org", "Viewer", "viewer password safe"
        )
        chairman = self.service.create_user(
            self.owner, "admin-chair@example.org", "Chairman", "chairman password safe", "chairman"
        )
        newcomer = self.service.create_user(
            self.owner, "admin-newcomer@example.org", "Newcomer", "newcomer password safe"
        )
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        self.service.grant_project_access(self.owner, project["id"], viewer["id"], "viewer")

        for label, actor in (("manager", manager), ("viewer", viewer), ("chairman", chairman)):
            with self.subTest(role=label, action="save_project_as_template"):
                with self.assertRaises(Forbidden):
                    self.service.save_project_as_template(actor, project["id"], f"{label} template")
            with self.subTest(role=label, action="grant_project_access"):
                with self.assertRaises(Forbidden):
                    self.service.grant_project_access(actor, project["id"], newcomer["id"], "manager")
            with self.subTest(role=label, action="set_working_days"):
                with self.assertRaises(Forbidden):
                    self.service.set_working_days(actor, project["id"], "01234")
            with self.subTest(role=label, action="add_holiday"):
                with self.assertRaises(Forbidden):
                    self.service.add_holiday(actor, project["id"], "2026-12-25", "Holiday")

        # Nothing leaked through: no template, no new membership, calendar untouched.
        self.assertEqual(self.service.list_templates(self.owner), [])
        self.assertEqual(self.service.list_projects(newcomer), [])
        calendar = self.service.get_project_calendar(self.owner, project["id"])
        self.assertEqual(calendar["working_days"], "0123456")
        self.assertEqual(calendar["holidays"], [])

    def test_final_results_filter_by_type(self):
        project = self.service.create_project(self.owner, "Mixed")
        task = self._accepted_task(project["id"], "Report")
        self.service.mark_final_result(self.owner, task["id"], "submission", task["submission_id"])
        attachment = self.service.add_task_attachment(self.owner, task["id"], "/out/appendix.pdf")
        self.service.mark_final_result(self.owner, task["id"], "attachment", attachment["id"])
        self.assertEqual(len(self.service.list_final_results(self.owner)), 2)
        only_attachments = self.service.list_final_results(self.owner, {"type": "attachment"})
        self.assertEqual([r["source_type"] for r in only_attachments], ["attachment"])

    def _final_results_fixture(self):
        # CS93C6 review gap 3: two projects in different entities, one mark each, on known dates.
        self.service.seed_default_entities(self.owner)
        ents = {e["name"]: e["id"] for e in self.service.list_entities(self.owner)}
        alpha = self.service.create_project(self.owner, "Alpha programme")
        beta = self.service.create_project(self.owner, "Beta survey")
        self.service.set_project_entities(self.owner, alpha["id"], [ents["RDI Pakistan"]])
        self.service.set_project_entities(self.owner, beta["id"], [ents["RDI - Global"]])
        report = self._accepted_task(alpha["id"], "Annual report")
        dataset = self._accepted_task(beta["id"], "Clean dataset")
        early = self.service.mark_final_result(self.owner, report["id"], "submission", report["submission_id"])
        late = self.service.mark_final_result(self.owner, dataset["id"], "submission", dataset["submission_id"])
        # marked_at is a UTC isoformat with microseconds; pin both to known instants.
        self.db.execute("UPDATE final_results SET marked_at=? WHERE id=?", ("2026-03-10T08:00:00.000000+00:00", early["id"]))
        self.db.execute("UPDATE final_results SET marked_at=? WHERE id=?", ("2026-03-20T23:59:59.900000+00:00", late["id"]))
        self.db.commit()
        return alpha, beta, ents

    def _fr_titles(self, filters):
        return sorted(r["task_title"] for r in self.service.list_final_results(self.owner, filters))

    def test_final_results_filter_by_project_and_entity(self):
        alpha, beta, ents = self._final_results_fixture()
        self.assertEqual(self._fr_titles({}), ["Annual report", "Clean dataset"])
        self.assertEqual(self._fr_titles({"project_id": alpha["id"]}), ["Annual report"])
        self.assertEqual(self._fr_titles({"project_id": beta["id"]}), ["Clean dataset"])
        self.assertEqual(self._fr_titles({"entity_id": ents["RDI Pakistan"]}), ["Annual report"])
        self.assertEqual(self._fr_titles({"entity_id": ents["RDI - Global"]}), ["Clean dataset"])
        self.assertEqual(self._fr_titles({"entity_id": ents["RDI - Global"], "project_id": alpha["id"]}), [])

    def test_final_results_filter_by_marked_date_range(self):
        self._final_results_fixture()
        self.assertEqual(self._fr_titles({"from": "2026-03-10"}), ["Annual report", "Clean dataset"])
        self.assertEqual(self._fr_titles({"from": "2026-03-11"}), ["Clean dataset"])
        self.assertEqual(self._fr_titles({"to": "2026-03-10"}), ["Annual report"])
        self.assertEqual(self._fr_titles({"to": "2026-03-09"}), [])
        # 'to' includes the whole day, including its last fraction of a second.
        self.assertEqual(self._fr_titles({"from": "2026-03-20", "to": "2026-03-20"}), ["Clean dataset"])
        self.assertEqual(self._fr_titles({"from": "2026-03-21"}), [])
        with self.assertRaises(ValueError):
            self.service.list_final_results(self.owner, {"from": "10/03/2026"})

    def test_final_results_search_matches_title_task_and_project(self):
        self._final_results_fixture()
        self.assertEqual(self._fr_titles({"q": "annual"}), ["Annual report"])
        self.assertEqual(self._fr_titles({"q": "Beta"}), ["Clean dataset"])
        self.assertEqual(self._fr_titles({"q": "  dataset  "}), ["Clean dataset"])
        self.assertEqual(self._fr_titles({"q": "nothing like this"}), [])

    def test_project_schedule_change_is_logged(self):
        project = self.service.create_project(self.owner, "Scheduled")
        updated = self.service.set_project_schedule(
            self.owner, project["id"], "2026-03-01", "2026-06-30", "Board approved the plan"
        )
        self.assertEqual((updated["start_date"], updated["target_date"]), ("2026-03-01", "2026-06-30"))
        events = self.service.project_events(self.owner, project["id"])
        change = [e for e in events if e["event_type"] == "project_schedule_changed"]
        self.assertEqual(len(change), 1)
        self.assertEqual(change[0]["reason"], "Board approved the plan")
        self.assertIn("2026-06-30", change[0]["detail_json"])
        # A later change records the previous values as 'before'.
        self.service.set_project_schedule(self.owner, project["id"], "2026-03-01", "2026-07-31", "Slipped one month")
        events = self.service.project_events(self.owner, project["id"])
        change = [e for e in events if e["event_type"] == "project_schedule_changed"]
        self.assertEqual(len(change), 2)

    def test_project_schedule_audit_row_records_actor_before_after_and_reason(self):
        # 5WZ4A8 review gap 2: pin every field of the audit row, not just a substring.
        project = self.service.create_project(self.owner, "Audited")
        manager = self.service.create_user(self.owner, "pm@example.org", "PM", "manager password safe", "member")
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        self.service.set_project_schedule(self.owner, project["id"], "2026-03-01", "2026-06-30", "Board approved the plan")
        self.service.set_project_schedule(manager, project["id"], "2026-03-01", "2026-07-31", "Vendor slipped")
        rows = [e for e in self.service.project_events(self.owner, project["id"])
                if e["event_type"] == "project_schedule_changed"]
        self.assertEqual(len(rows), 2)
        first, second = rows
        self.assertEqual(first["actor_user_id"], self.owner["id"])
        self.assertEqual(first["reason"], "Board approved the plan")
        self.assertEqual(json.loads(first["detail_json"]), {
            "before": {"start_date": None, "target_date": None},
            "after": {"start_date": "2026-03-01", "target_date": "2026-06-30"},
        })
        self.assertEqual(second["actor_user_id"], manager["id"])
        self.assertEqual(second["actor_name"], "PM")
        self.assertEqual(second["reason"], "Vendor slipped")
        self.assertEqual(json.loads(second["detail_json"]), {
            "before": {"start_date": "2026-03-01", "target_date": "2026-06-30"},
            "after": {"start_date": "2026-03-01", "target_date": "2026-07-31"},
        })

    def test_project_schedule_change_requires_manage_access(self):
        # 5WZ4A8 review gap 1: only the owner or a project manager may change project dates;
        # a viewer and a non-member are refused and nothing is written.
        project = self.service.create_project(self.owner, "Guarded")
        viewer = self.service.create_user(self.owner, "v@example.org", "Viewer", "viewer password safe", "member")
        outsider = self.service.create_user(self.owner, "o@example.org", "Outsider", "outsider password safe", "member")
        manager = self.service.create_user(self.owner, "m@example.org", "Manager", "manager password safe", "member")
        self.service.grant_project_access(self.owner, project["id"], viewer["id"], "viewer")
        self.service.grant_project_access(self.owner, project["id"], manager["id"], "manager")
        for actor in (viewer, outsider):
            with self.subTest(actor=actor["email"]), self.assertRaises(Forbidden):
                self.service.set_project_schedule(actor, project["id"], "2026-03-01", "2026-06-30", "try")
        unchanged = self.service.get_project(self.owner, project["id"])
        self.assertEqual((unchanged["start_date"], unchanged["target_date"]), (None, None))
        self.assertEqual([e for e in self.service.project_events(self.owner, project["id"])
                          if e["event_type"] == "project_schedule_changed"], [])
        updated = self.service.set_project_schedule(manager, project["id"], "2026-03-01", "2026-06-30", "PM set it")
        self.assertEqual(updated["target_date"], "2026-06-30")

    def test_project_history_readable_by_members_not_outsiders(self):
        # 5WZ4A8 review gap 4: anyone who can view the project can read its history.
        project = self.service.create_project(self.owner, "Readable")
        viewer = self.service.create_user(self.owner, "rv@example.org", "Viewer", "viewer password safe", "member")
        outsider = self.service.create_user(self.owner, "ro@example.org", "Outsider", "outsider password safe", "member")
        self.service.grant_project_access(self.owner, project["id"], viewer["id"], "viewer")
        self.service.set_project_schedule(self.owner, project["id"], "2026-03-01", "2026-06-30", "Plan set")
        seen = self.service.project_events(viewer, project["id"])
        self.assertEqual([e["event_type"] for e in seen], ["project_schedule_changed"])
        with self.assertRaises(Forbidden):
            self.service.project_events(outsider, project["id"])

    def test_project_history_non_managers_see_only_schedule_changes_and_closure(self):
        # ZSZ9T2: Aly decided (Slack 2026-09-24) that anyone who can view but not manage
        # the project sees only project_schedule_changed and project_closed. K62ZAP: a
        # Chairman sees the full history like the Owner (Aly, ts 1790245584.314119).
        project = self.service.create_project(self.owner, "Filtered")
        people = {}
        for key, global_role, role in (("chairman", "chairman", None), ("viewer", "member", "viewer"),
                                       ("member", "member", "member"), ("manager", "member", "manager"),
                                       ("outsider", "member", None)):
            people[key] = self.service.create_user(
                self.owner, f"zs-{key}@example.org", key.title(), f"{key} password safe", global_role)
            if role:
                self.service.grant_project_access(self.owner, project["id"], people[key]["id"], role)
        every = ("project_schedule_changed", "import_committed", "protected_action_blocked",
                 "protected_action_requested", "protected_action_approved", "protected_action_rejected",
                 "protected_action_cancelled", "project_closed")
        # Synthetic rows, one per kind the service writes, with the payloads a
        # non-manager must not see (owner-request reasons, import file metadata).
        for kind in every:
            detail = {"filename": "secret-plan.xlsx", "sha256": "ab" * 32} if kind == "import_committed" \
                else {"action": "delete_task", "payload": {"note": "private"}}
            self.service._project_event(project["id"], self.owner["id"], kind, detail, f"reason for {kind}")
        # Order-independent: back-to-back rows can share a timestamp on coarse clocks.
        for key in ("viewer", "member"):
            with self.subTest(actor=key):
                self.assertFalse(self.service.can_manage_project(people[key], project["id"]))
                kinds = [e["event_type"] for e in self.service.project_events(people[key], project["id"])]
                self.assertCountEqual(kinds, ["project_schedule_changed", "project_closed"])
        for key, actor in (("owner", self.owner), ("chairman", people["chairman"]), ("manager", people["manager"])):
            with self.subTest(actor=key):
                kinds = [e["event_type"] for e in self.service.project_events(actor, project["id"])]
                self.assertCountEqual(kinds, every)
        with self.assertRaises(Forbidden):
            self.service.project_events(people["outsider"], project["id"])

    def test_task_and_project_history_full_for_owner_chairman_manager_filtered_for_others(self):
        # K62ZAP (Aly, ts 1790245384.787859 and 1790245584.314119): Owner, Chairman and
        # project managers see every kind; members, viewers and non-manager approvers see
        # ordinary kinds plus rows they wrote themselves; non-members get Forbidden.
        ordinary = (
            "task_created", "task_updated", "criticality_changed", "parent_changed", "dependency_added",
            "dependency_removed", "task_submitted", "submission_accepted", "changes_requested", "task_reopened",
            "task_on_hold", "schedule_proposed", "schedule_revised", "schedule_proposal_rejected",
            "attachment_added", "attachment_removed", "final_result_marked", "final_result_unmarked",
        )
        hidden = (
            "protected_action_blocked", "protected_action_requested", "protected_action_approved",
            "protected_action_rejected", "protected_action_cancelled", "attachment_add_blocked",
            "attachment_removal_blocked", "final_result_mark_blocked", "final_result_unmark_blocked",
            "import_key_assigned",
        )
        project = self.service.create_project(self.owner, "History split")
        task = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Audited"})
        people = {}
        for key, global_role, role in (("chairman", "chairman", None), ("manager", "member", "manager"),
                                       ("member", "member", "member"), ("viewer", "member", "viewer"),
                                       ("approver", "member", "member"), ("outsider", "member", None)):
            people[key] = self.service.create_user(
                self.owner, f"k6-{key}@example.org", key.title(), f"{key} password safe", global_role)
            if role:
                self.service.grant_project_access(self.owner, project["id"], people[key]["id"], role)
        self.service.add_task_reviewer(self.owner, task["id"], people["approver"]["id"], "approver")
        # Synthetic rows: every kind written by the Owner (hidden ones carry a secret),
        # plus one hidden row written by each filtered person, which they must still see.
        for kind in ordinary[1:] + hidden:
            secret = {"payload": "secret-payload"} if kind in hidden else None
            self.service._event(task["id"], self.owner["id"], kind, None, secret, None, notify=False)
        own = {"member": "attachment_add_blocked", "viewer": "protected_action_blocked",
               "approver": "protected_action_requested"}
        other_project = self.service.create_project(self.owner, "History split B")
        other_task = self.service.create_task(self.owner, {"project_id": other_project["id"], "title": "Elsewhere"})
        for key, kind in own.items():
            self.service._event(task["id"], people[key]["id"], kind, None, {"note": "own"}, None, notify=False)
            self.service._project_event(project["id"], people[key]["id"], "protected_action_blocked",
                                        {"note": "own"}, None)
            # A hidden row the same person wrote on a second project/task they can also view
            # must not leak into the first one's history.
            self.service.grant_project_access(self.owner, other_project["id"], people[key]["id"], "member")
            self.service._event(other_task["id"], people[key]["id"], kind, None, {"note": "elsewhere"}, None,
                                notify=False)
            self.service._project_event(other_project["id"], people[key]["id"], "protected_action_blocked",
                                        {"note": "elsewhere"}, None)
        self.service._project_event(project["id"], self.owner["id"], "import_committed",
                                    {"filename": "secret-payload.xlsx"}, None)
        self.service._project_event(project["id"], self.owner["id"], "project_closed", None, None)
        all_task = list(ordinary + hidden) + list(own.values())
        all_project = ["import_committed", "project_closed"] + ["protected_action_blocked"] * len(own)
        # Order-independent: back-to-back rows can share a timestamp on coarse clocks.
        for key, actor in (("owner", self.owner), ("chairman", people["chairman"]), ("manager", people["manager"])):
            with self.subTest(actor=key):
                self.assertCountEqual([e["event_type"] for e in self.service.task_events(actor, task["id"])], all_task)
                self.assertCountEqual([e["event_type"] for e in self.service.project_events(actor, project["id"])],
                                      all_project)
        for key, kind in own.items():
            with self.subTest(actor=key):
                actor = people[key]
                task_rows = self.service.task_events(actor, task["id"])
                self.assertCountEqual([e["event_type"] for e in task_rows], list(ordinary) + [kind])
                self.assertEqual([e["actor_user_id"] for e in task_rows if e["event_type"] == kind], [actor["id"]])
                project_rows = self.service.project_events(actor, project["id"])
                self.assertCountEqual([(e["event_type"], e["actor_user_id"]) for e in project_rows],
                                      [("project_closed", self.owner["id"]), ("protected_action_blocked", actor["id"])])
                self.assertNotIn("secret-payload", json.dumps(task_rows + project_rows))
                self.assertNotIn("elsewhere", json.dumps(task_rows + project_rows))
        with self.assertRaises(Forbidden):
            self.service.task_events(people["outsider"], task["id"])
        with self.assertRaises(Forbidden):
            self.service.project_events(people["outsider"], project["id"])

    def test_list_projects_exposes_schedule_dates_for_gantt_markers(self):
        # 5WZ4A8: the Gantt draws project start/target markers from list_projects,
        # so those fields must be present on the listed project.
        project = self.service.create_project(self.owner, "Marked")
        self.service.set_project_schedule(self.owner, project["id"], "2026-03-01", "2026-06-30", "Plan set")
        listed = {p["id"]: p for p in self.service.list_projects(self.owner)}[project["id"]]
        self.assertEqual((listed["start_date"], listed["target_date"]), ("2026-03-01", "2026-06-30"))

    def test_project_schedule_requires_reason(self):
        project = self.service.create_project(self.owner, "NoReason")
        with self.assertRaisesRegex(ValueError, "reason"):
            self.service.set_project_schedule(self.owner, project["id"], "2026-03-01", "2026-06-30", "")

    def test_project_target_cannot_precede_start(self):
        project = self.service.create_project(self.owner, "Backwards")
        with self.assertRaisesRegex(ValueError, "earlier"):
            self.service.set_project_schedule(self.owner, project["id"], "2026-06-30", "2026-03-01", "typo")

    def test_task_date_change_is_logged_with_before_and_after(self):
        # The task half of the date-history requirement — confirm it already works.
        project = self.service.create_project(self.owner, "Task dates")
        task = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Milestone", "due_date": "2026-04-01",
        })
        self.update_task(self.owner, task["id"], {"due_date": "2026-04-15", "reason": "Client moved the date"})
        events = self.service.task_events(self.owner, task["id"])
        updated = [e for e in events if e["event_type"] == "task_updated"][-1]
        self.assertIn("2026-04-01", updated["before_json"])
        self.assertIn("2026-04-15", updated["after_json"])
        self.assertEqual(updated["reason"], "Client moved the date")

    def test_list_subtasks_returns_step_schedule_shape(self):
        # D73AQW: the Gantt step segments and the detail dialog share one subtask
        # shape, so list_subtasks must carry the schedule and ownership fields.
        project = self.service.create_project(self.owner, "Steps")
        parent = self.service.create_task(self.owner, {"project_id": project["id"], "title": "Board pack"})
        step = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Draft pack", "parent_task_id": parent["id"],
            "owner_user_id": self.owner["id"], "start_date": "2026-10-05", "due_date": "2026-10-09",
            "criticality": "high", "progress": 40,
        })
        undated = self.service.create_task(self.owner, {
            "project_id": project["id"], "title": "Circulate", "parent_task_id": parent["id"],
        })
        by_id = {s["id"]: s for s in self.service.list_subtasks(self.owner, parent["id"])}
        self.assertEqual(set(by_id), {step["id"], undated["id"]})
        dated = by_id[step["id"]]
        self.assertEqual(dated["start_date"], "2026-10-05")
        self.assertEqual(dated["due_date"], "2026-10-09")
        self.assertEqual(dated["criticality"], "high")
        self.assertEqual(dated["progress"], 40)
        self.assertEqual(dated["parent_task_id"], parent["id"])
        self.assertEqual(dated["owner_user_id"], self.owner["id"])
        self.assertEqual(dated["owner_name"], "Owner")
        # Undated steps stay in the list with explicit nulls; nothing invents dates.
        self.assertIsNone(by_id[undated["id"]]["start_date"])
        self.assertIsNone(by_id[undated["id"]]["due_date"])
        self.assertIsNone(by_id[undated["id"]]["owner_user_id"])
        detail = self.service.task_detail(self.owner, parent["id"])
        self.assertEqual({s["id"] for s in detail["subtasks"]}, {step["id"], undated["id"]})
        self.assertTrue(all("start_date" in s and "criticality" in s for s in detail["subtasks"]))


class SecondaryOwnerTests(unittest.TestCase):
    """GTEYTG (Aly, Slack ts 1790245584.314119 and 1790245630.918199): the primary owner
    grants and removes full Owner access; secondary owners cannot remove, demote or
    deactivate the primary or each other; every change and blocked attempt is recorded."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / "test.sqlite3")
        self.service = AstraService(self.db)
        self.primary = self.service.create_initial_owner("owner@example.org", "Primary", "correct horse battery")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def user(self, key, role="member"):
        return self.service.create_user(self.primary, f"{key}@example.org", key.title(), f"{key} password safe", role)

    def secondary(self, key):
        created = self.user(key)
        return self.service.grant_secondary_owner(self.primary, created["id"], f"cover for {key}")

    def user_events(self, event_type=None):
        rows = [dict(r) for r in self.db.execute("SELECT * FROM user_events ORDER BY occurred_at, id")]
        return [r for r in rows if event_type in (None, r["event_type"])]

    def notified(self, user):
        return [n["kind"] for n in self.service.list_notifications(user)]

    def test_initial_owner_is_primary_and_exposed(self):
        self.assertEqual(self.primary["is_primary_owner"], 1)
        listed = {u["id"]: u for u in self.service.list_users(self.primary)}
        self.assertEqual(listed[self.primary["id"]]["is_primary_owner"], 1)
        member = self.user("plain")
        self.assertEqual(member["is_primary_owner"], 0)

    def test_primary_grants_and_revokes_a_secondary_owner(self):
        member = self.user("deputy")
        project = self.service.create_project(self.primary, "Kept access")
        self.service.grant_project_access(self.primary, project["id"], member["id"], "manager")
        granted = self.service.grant_secondary_owner(self.primary, member["id"], "Covers while I travel")
        self.assertEqual((granted["global_role"], granted["is_primary_owner"]), ("owner", 0))
        [event] = self.user_events("secondary_owner_granted")
        self.assertEqual((event["target_user_id"], event["actor_user_id"], event["reason"]),
                         (member["id"], self.primary["id"], "Covers while I travel"))
        self.assertEqual(json.loads(event["detail_json"])["prior_role"], "member")
        self.assertIn("secondary_owner_granted", self.notified(granted))
        # Their sessions go when access is removed; their project roles stay.
        self.db.execute("INSERT INTO sessions VALUES('tok',?,'csrf','2026-01-01T00:00:00Z','2999-01-01T00:00:00Z')",
                        (member["id"],))
        revoked = self.service.revoke_secondary_owner(self.primary, member["id"], "Back from travel")
        self.assertEqual((revoked["global_role"], revoked["is_primary_owner"]), ("member", 0))
        [event] = self.user_events("secondary_owner_revoked")
        detail = json.loads(event["detail_json"])
        self.assertEqual((detail["restored_role"], detail["sessions_revoked"]), ("member", 1))
        self.assertEqual(event["reason"], "Back from travel")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (member["id"],)).fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT role FROM memberships WHERE user_id=?", (member["id"],)).fetchone()[0],
                         "manager")
        self.assertIn("secondary_owner_revoked", self.notified(revoked))
        self.assertEqual(len(self.service.list_user_events(self.primary)), 2)

    def test_revoke_restores_a_chairman_and_several_secondaries_are_allowed(self):
        chairman = self.user("chair", "chairman")
        self.service.grant_secondary_owner(self.primary, chairman["id"], "Board cover")
        other = self.secondary("second")
        owners = self.db.execute("SELECT COUNT(*) FROM users WHERE global_role='owner'").fetchone()[0]
        self.assertEqual(owners, 3)
        self.assertEqual(self.service.revoke_secondary_owner(self.primary, chairman["id"], "Done")["global_role"],
                         "chairman")
        self.assertEqual(self.service.get_user(other["id"])["global_role"], "owner")

    def test_grant_and_revoke_input_errors(self):
        member = self.user("target")
        with self.assertRaises(ValueError):
            self.service.grant_secondary_owner(self.primary, member["id"], "   ")
        with self.assertRaises(KeyError):
            self.service.grant_secondary_owner(self.primary, "no-such-user", "why")
        secondary = self.secondary("already")
        with self.assertRaises(ValueError):
            self.service.grant_secondary_owner(self.primary, secondary["id"], "again")
        with self.assertRaises(ValueError):
            self.service.revoke_secondary_owner(self.primary, member["id"], "not an owner")
        with self.assertRaises(ValueError):
            self.service.revoke_secondary_owner(self.primary, self.primary["id"], "myself")
        with self.assertRaises(ValueError):
            self.service.revoke_secondary_owner(self.primary, secondary["id"], "  ")
        with self.assertRaisesRegex(ValueError, "Remove their secondary owner access first"):
            self.service.set_user_active(self.primary, secondary["id"], False)
        inactive = self.user("gone")
        self.service.set_user_active(self.primary, inactive["id"], False)
        with self.assertRaises(ValueError):
            self.service.grant_secondary_owner(self.primary, inactive["id"], "why")
        self.assertEqual(self.user_events("secondary_owner_granted")[-1]["target_user_id"], secondary["id"])

    def test_database_refuses_a_second_primary_and_a_primary_who_is_not_an_owner(self):
        secondary = self.secondary("dup")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE users SET is_primary_owner=1 WHERE id=?", (secondary["id"],))
        member = self.user("notowner")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE users SET is_primary_owner=1 WHERE id=?", (member["id"],))
        self.db.execute("UPDATE users SET is_primary_owner=0 WHERE id=?", (self.primary["id"],))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE users SET is_primary_owner=1 WHERE id=?", (member["id"],))

    def test_secondary_owner_cannot_change_owner_access_or_target_other_owners(self):
        first, second = self.secondary("first"), self.secondary("second")
        third = self.user("third")
        project = self.service.create_project(self.primary, "Guarded")
        attempts = {
            "grant a third user": lambda: self.service.grant_secondary_owner(first, third["id"], "promote"),
            "revoke another secondary": lambda: self.service.revoke_secondary_owner(first, second["id"], "demote"),
            "revoke the primary": lambda: self.service.revoke_secondary_owner(first, self.primary["id"], "coup"),
            "deactivate the primary": lambda: self.service.set_user_active(first, self.primary["id"], False),
            "deactivate another secondary": lambda: self.service.set_user_active(first, second["id"], False),
            "give the primary project access": lambda: self.service.grant_project_access(
                first, project["id"], self.primary["id"], "viewer"),
            "remove another secondary's project access": lambda: self.service.revoke_project_access(
                first, project["id"], second["id"]),
            "change their own project access": lambda: self.service.grant_project_access(
                first, project["id"], first["id"], "manager"),
        }
        users_before = [tuple(r) for r in self.db.execute("SELECT * FROM users ORDER BY id")]
        for name, attempt in attempts.items():
            with self.subTest(attempt=name):
                before = len(self.user_events("owner_change_blocked"))
                with self.assertRaises(Forbidden):
                    attempt()
                blocked = self.user_events("owner_change_blocked")
                self.assertEqual(len(blocked), before + 1)
                self.assertEqual(blocked[-1]["actor_user_id"], first["id"])
        self.assertEqual([tuple(r) for r in self.db.execute("SELECT * FROM users ORDER BY id")], users_before)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM memberships").fetchone()[0], 0)
        self.assertEqual(self.notified(self.primary).count("owner_change_blocked"), len(attempts))
        # The secondary still manages ordinary users.
        self.assertEqual(self.service.set_user_active(first, third["id"], False)["active"], 0)
        self.service.grant_project_access(first, project["id"], third["id"], "member")

    def test_repeated_blocked_attempts_record_one_row_and_one_notice(self):
        first, second = self.secondary("first"), self.secondary("second")
        for _ in range(3):
            with self.assertRaises(Forbidden):
                self.service.set_user_active(first, second["id"], False)
        self.assertEqual(len(self.user_events("owner_change_blocked")), 1)
        self.assertEqual(self.notified(self.primary).count("owner_change_blocked"), 1)
        with self.assertRaises(Forbidden):   # a different action is a new record
            self.service.revoke_secondary_owner(first, second["id"], "demote")
        self.assertEqual(len(self.user_events("owner_change_blocked")), 2)
        # Blocked rows never push grants out of the owner-access history.
        self.db.executemany(
            "INSERT INTO user_events(id,target_user_id,event_type,actor_user_id,occurred_at,reason,detail_json)"
            " VALUES(?,?,'owner_change_blocked',?,'2999-01-01T00:00:00Z',NULL,'{}')",
            [(f"flood-{n}", second["id"], first["id"]) for n in range(300)],
        )
        kinds = [e["event_type"] for e in self.service.list_user_events(self.primary)]
        self.assertEqual(kinds.count("secondary_owner_granted"), 2)
        self.assertEqual(kinds.count("owner_change_blocked"), 50)

    def test_user_changes_read_the_target_under_the_write_lock(self):
        # A target must not become an owner between the guard's read and the write.
        project = self.service.create_project(self.primary, "Raced")
        calls = {
            "set_user_active": lambda uid: self.service.set_user_active(self.primary, uid, False),
            "grant_project_access": lambda uid: self.service.grant_project_access(
                self.primary, project["id"], uid, "member"),
            "revoke_project_access": lambda uid: self.service.revoke_project_access(self.primary, project["id"], uid),
        }
        real_get_user = self.service.get_user
        for name, call in calls.items():
            with self.subTest(call=name):
                target = self.user(f"race-{name.replace('_', '-')}")
                other = sqlite3.connect(Path(self.temp.name) / "test.sqlite3", timeout=0.1, isolation_level=None)
                outcome = []

                def racing_get_user(user_id):
                    found = real_get_user(user_id)
                    if user_id == target["id"] and not outcome:
                        try:
                            other.execute("UPDATE users SET global_role='owner' WHERE id=?", (user_id,))
                            outcome.append("promoted in between")
                        except sqlite3.OperationalError:
                            outcome.append("locked out")
                    return found

                try:
                    with patch.object(self.service, "get_user", racing_get_user):
                        call(target["id"])
                finally:
                    other.close()
                self.assertEqual(outcome, ["locked out"])
                self.assertEqual(self.service.get_user(target["id"])["global_role"], "member")

    def test_non_owners_cannot_grant_or_revoke_owner_access(self):
        chairman, member = self.user("chair", "chairman"), self.user("member")
        secondary = self.secondary("sec")
        for actor in (chairman, member):
            with self.subTest(actor=actor["email"]):
                with self.assertRaises(Forbidden):
                    self.service.grant_secondary_owner(actor, member["id"], "promote")
                with self.assertRaises(Forbidden):
                    self.service.revoke_secondary_owner(actor, secondary["id"], "demote")
                with self.assertRaises(Forbidden):
                    self.service.list_user_events(actor)
        self.assertEqual(len(self.user_events("owner_change_blocked")), 4)
        self.assertEqual(len(self.service.list_user_events(secondary)), len(self.user_events()))

    def test_secondary_owner_has_ordinary_owner_powers_until_revoked(self):
        secondary = self.secondary("deputy")
        project = self.service.create_project(secondary, "Deputy's project")
        created = self.service.create_user(secondary, "new@example.org", "New", "new person password", "member")
        task = self.service.create_task(secondary, {"project_id": project["id"], "title": "Deliver"})
        submission = self.service.submit_task(secondary, task["id"], "done")
        self.service.accept_submission(secondary, submission["id"], "accepted")
        self.service.close_project(secondary, project["id"], "finished")
        self.service.grant_project_access(secondary, project["id"], created["id"], "viewer")
        self.service.revoke_secondary_owner(self.primary, secondary["id"], "done")
        demoted = self.service.get_user(secondary["id"])
        with self.assertRaises(Forbidden):
            self.service.create_project(demoted, "No longer allowed")

    def test_owner_request_decisions_by_several_owners(self):
        manager = self.user("pm")
        project = self.service.create_project(self.primary, "Governed")
        self.service.grant_project_access(self.primary, project["id"], manager["id"], "manager")
        task = self.service.create_task(self.primary, {"project_id": project["id"], "title": "Protected"})

        def file_request(actor, status):
            current = self.service.get_task(self.primary, task["id"])
            return self.service.update_task(actor, task["id"], {
                "status": status, "reason": f"please {status}", "expected_revision": current["revision"],
            })["request"]

        # A secondary decides a Manager's request; a second decision is a conflict.
        secondary = self.secondary("deputy")
        request = file_request(manager, "cancelled")
        self.service.decide_owner_action_request(secondary, request["id"], "rejected", "not now")
        with self.assertRaises(Conflict):
            self.service.decide_owner_action_request(self.primary, request["id"], "rejected", "also no")
        # A Manager later made owner cannot approve or reject their own request; cancel is fine.
        own = file_request(manager, "cancelled")
        promoted = self.service.grant_secondary_owner(self.primary, manager["id"], "promoted")
        for decision in ("approved", "rejected"):
            with self.subTest(decision=decision), self.assertRaises(Forbidden):
                self.service.decide_owner_action_request(promoted, own["id"], decision, "self")
        self.assertEqual(self.service.decide_owner_action_request(promoted, own["id"], "cancelled", "withdrawn")
                         ["request"]["status"], "cancelled")

    def test_owner_notifications_reach_every_other_active_owner(self):
        secondary = self.secondary("deputy")
        manager = self.user("pm")
        project = self.service.create_project(self.primary, "Noticed")
        self.service.grant_project_access(self.primary, project["id"], manager["id"], "manager")
        task = self.service.create_task(self.primary, {"project_id": project["id"], "title": "Watched"})

        def task_changes(user):
            return [n for n in self.service.list_notifications(user) if n["task_id"] == task["id"]]

        # The primary's own creation notifies the secondary, not the primary.
        self.assertEqual(len(task_changes(secondary)), 1)
        self.assertEqual(task_changes(self.primary), [])
        current = self.service.get_task(manager, task["id"])
        self.service.update_task(manager, task["id"], {"title": "Watched 2", "expected_revision": current["revision"]})
        self.assertEqual((len(task_changes(self.primary)), len(task_changes(secondary))), (1, 2))
        current = self.service.get_task(secondary, task["id"])
        self.service.update_task(secondary, task["id"], {"title": "Watched 3", "expected_revision": current["revision"]})
        self.assertEqual((len(task_changes(self.primary)), len(task_changes(secondary))), (2, 2))

    def test_template_owner_role_goes_to_the_acting_owner(self):
        project = self.service.create_project(self.primary, "Recurring")
        self.service.create_task(self.primary, {
            "project_id": project["id"], "title": "Owner review", "owner_user_id": self.primary["id"]})
        template = self.service.save_project_as_template(self.primary, project["id"], "Owner tmpl")
        secondary = self.secondary("deputy")
        created = self.service.create_project_from_template(secondary, template["id"], "Deputy's copy")
        [task] = self.service.list_tasks(secondary, created["id"])
        self.assertEqual(task["owner_user_id"], secondary["id"])


if __name__ == "__main__":
    unittest.main()
