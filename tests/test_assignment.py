"""3FQEKB (Aly 2026-09-26, Slack ts 1790386228.535829 and 1790386492.402489): the Chairman may
assign tasks and subtasks but is never assigned one; a project viewer may be given subtasks
only. Older assignments that break the rules are kept and flagged. Service level; the HTTP
and UI sides are in test_web.py."""
import json
import tempfile
import unittest
from pathlib import Path

from astra.db import connect
from astra.service import AstraService, Conflict, Forbidden, TaskLocked


class AssignmentFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / "assign.sqlite3")
        self.service = s = AstraService(self.db)
        self.owner = s.create_initial_owner("owner@example.org", "Owner", "owner password safe")
        self.chair = s.create_user(self.owner, "chair@example.org", "Chair Person", "chair password safe", "chairman")
        self.manager = s.create_user(self.owner, "manager@example.org", "Manager", "manager password safe")
        self.member = s.create_user(self.owner, "member@example.org", "Member", "member password safe")
        self.viewer = s.create_user(self.owner, "viewer@example.org", "Viewer", "viewer password safe")
        self.project = s.create_project(self.owner, "Assignments")
        self.pid = self.project["id"]
        for user, role in ((self.manager, "manager"), (self.member, "member"), (self.viewer, "viewer")):
            s.grant_project_access(self.owner, self.pid, user["id"], role)
        self.parent = s.create_task(self.owner, {"project_id": self.pid, "title": "Parent"})
        self.step = s.create_task(self.owner, {"project_id": self.pid, "title": "Step", "parent_task_id": self.parent["id"]})

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def fresh(self, task_id):
        return self.service.get_task(self.owner, task_id)

    def assign(self, actor, task_id, user_id, **extra):
        return self.service.update_task(actor, task_id, {"owner_user_id": user_id,
                                                         "expected_revision": self.fresh(task_id)["revision"], **extra})

    def listed(self, task_id):
        return next(t for t in self.service.list_tasks(self.owner, self.pid) if t["id"] == task_id)

    def legacy_owner(self, task_id, user_id):
        """An assignment made before the rules existed (written directly, as old data is)."""
        self.db.execute("UPDATE tasks SET owner_user_id=? WHERE id=?", (user_id, task_id))


class ChairmanAssignsTests(AssignmentFixture):
    def test_who_may_assign(self):
        s = self.service
        for actor, expected in ((self.owner, True), (self.manager, True), (self.chair, True),
                                (self.member, False), (self.viewer, False)):
            with self.subTest(role=actor["display_name"]):
                self.assertEqual(s.can_assign(actor, self.pid), expected)
        self.assertFalse(s.can_manage_project(self.chair, self.pid))  # not widened

    def test_the_chairman_assigns_from_the_panel_and_it_is_recorded(self):
        task = self.assign(self.chair, self.parent["id"], self.member["id"], reason="Member leads it")
        self.assertEqual(task["owner_user_id"], self.member["id"])
        event = self.service.task_events(self.owner, self.parent["id"])[-1]
        self.assertEqual((event["event_type"], event["actor_user_id"]), ("task_updated", self.chair["id"]))
        # A subtask too, and unassigning.
        self.assertEqual(self.assign(self.chair, self.step["id"], self.viewer["id"])["owner_user_id"], self.viewer["id"])
        self.assertIsNone(self.assign(self.chair, self.step["id"], None)["owner_user_id"])
        detail = self.service.task_detail(self.chair, self.parent["id"])["permissions"]
        self.assertEqual((detail["can_assign"], detail["assign_only"], detail["can_edit_ordinary"]), (True, True, False))
        self.assertFalse(self.service.task_detail(self.member, self.parent["id"])["permissions"]["can_assign"])

    def test_the_chairman_changes_nothing_but_the_assignee(self):
        s, tid = self.service, self.parent["id"]
        rev = self.fresh(tid)["revision"]
        for label, body in (
            ("title", {"title": "Renamed"}),
            ("title with an assignee", {"title": "Renamed", "owner_user_id": self.member["id"]}),
            ("status", {"status": "in_progress", "reason": "go", "owner_user_id": self.member["id"]}),
            ("dates", {"due_date": "2026-12-01", "reason": "later", "owner_user_id": self.member["id"]}),
            ("no assignee at all", {"reason": "hello"}),
        ):
            with self.subTest(label), self.assertRaises(Forbidden):
                s.update_task(self.chair, tid, {**body, "expected_revision": rev})
        self.assertEqual(self.fresh(tid)["revision"], rev)
        # Unchanged fields echoed back by a form are fine.
        s.update_task(self.chair, tid, {"owner_user_id": self.member["id"], "title": "Parent", "expected_revision": rev})
        for write in (
            lambda: s.create_task(self.chair, {"project_id": self.pid, "title": "No"}),
            lambda: s.set_on_hold(self.chair, tid, "wait", "2027-01-01", self.member["id"]),
            lambda: s.set_parent(self.chair, self.step["id"], None),
            lambda: s.confirm_criticality(self.chair, tid, "high", "evidence"),
            lambda: s.acquire_task_lock(self.chair, tid, "edit"),
            lambda: s.bulk_preview(self.chair, self.pid, {"task_ids": [tid], "action": "status", "value": "ready"}),
        ):
            with self.subTest(write=write), self.assertRaises(Forbidden):
                write()

    def test_the_chairman_meets_someone_elses_lock(self):
        s = self.service
        s.acquire_task_lock(self.manager, self.parent["id"], "edit")
        with self.assertRaises(TaskLocked):
            self.assign(self.chair, self.parent["id"], self.member["id"])
        self.assertIsNone(self.fresh(self.parent["id"])["owner_user_id"])

    def test_the_chairman_uses_bulk_assign_and_its_undo(self):
        s = self.service
        other = s.create_task(self.owner, {"project_id": self.pid, "title": "Other"})
        body = {"task_ids": [self.parent["id"], other["id"]], "action": "assignee", "value": self.member["id"]}
        plan = s.bulk_preview(self.chair, self.pid, body)
        done = s.bulk_apply(self.chair, self.pid, {**body, "expected_revisions": {i["id"]: i["revision"] for i in plan["ok"]}})
        self.assertEqual({self.fresh(i)["owner_user_id"] for i in body["task_ids"]}, {self.member["id"]})
        s.bulk_undo(self.chair, self.pid, {"bulk_id": done["bulk_id"]})
        self.assertEqual({self.fresh(i)["owner_user_id"] for i in body["task_ids"]}, {None})
        for action, value in (("status", "ready"), ("due_shift", 3)):
            with self.subTest(action=action), self.assertRaises(Forbidden):
                s.bulk_preview(self.chair, self.pid, {"task_ids": [self.parent["id"]], "action": action, "value": value})
        # The Chairman's Undo reverses assignments only: a recorded change of any other kind is refused.
        again = s.bulk_apply(self.chair, self.pid, {**body, "expected_revisions": {
            i: self.fresh(i)["revision"] for i in body["task_ids"]}})
        row = self.db.execute("SELECT id, detail_json FROM project_events WHERE event_type='bulk_change' AND actor_user_id=?"
                              " ORDER BY occurred_at DESC, rowid DESC LIMIT 1", (self.chair["id"],)).fetchone()
        self.db.execute("UPDATE project_events SET detail_json=? WHERE id=?",
                        (json.dumps({**json.loads(row["detail_json"]), "action": "status"}), row["id"]))
        with self.assertRaises(Forbidden):
            s.bulk_undo(self.chair, self.pid, {"bulk_id": again["bulk_id"]})
        self.assertEqual({self.fresh(i)["owner_user_id"] for i in body["task_ids"]}, {self.member["id"]})


class NobodyAssignsTheChairmanTests(AssignmentFixture):
    def test_every_path_refuses_the_chairman(self):
        s, chair = self.service, self.chair["id"]
        writes = {
            "create": lambda: s.create_task(self.owner, {"project_id": self.pid, "title": "X", "owner_user_id": chair}),
            "create a subtask": lambda: s.create_task(self.manager, {"project_id": self.pid, "title": "X", "owner_user_id": chair,
                                                                    "parent_task_id": self.parent["id"]}),
            "panel": lambda: self.assign(self.owner, self.parent["id"], chair),
            "panel on a subtask": lambda: self.assign(self.manager, self.step["id"], chair),
            "the Chairman's own panel": lambda: self.assign(self.chair, self.parent["id"], chair),
            "bulk": lambda: s.bulk_preview(self.owner, self.pid, {"task_ids": [self.parent["id"]], "action": "assignee",
                                                                  "value": chair}),
            "hold owner": lambda: s.set_on_hold(self.owner, self.parent["id"], "wait", "2027-01-01", chair),
        }
        for name, write in writes.items():
            with self.subTest(path=name), self.assertRaisesRegex(ValueError, "is the Chairman"):
                write()
        self.assertIsNone(self.fresh(self.parent["id"])["owner_user_id"])
        self.assertEqual(self.fresh(self.parent["id"])["status"], "draft")

    def test_the_chairman_may_still_review(self):
        # Reviewing and approving are not assignment; the reviewer list is unchanged.
        self.service.add_task_reviewer(self.owner, self.parent["id"], self.chair["id"], "reviewer")
        self.assertIn(self.chair["id"], {r["user_id"] for r in self.service.list_task_reviewers(self.owner, self.parent["id"])})


class ViewersGetSubtasksTests(AssignmentFixture):
    def test_a_viewer_gets_subtasks_only(self):
        s, viewer = self.service, self.viewer["id"]
        refused = {
            "create": lambda: s.create_task(self.manager, {"project_id": self.pid, "title": "X", "owner_user_id": viewer}),
            "panel": lambda: self.assign(self.manager, self.parent["id"], viewer),
            "hold owner": lambda: s.set_on_hold(self.manager, self.parent["id"], "wait", "2027-01-01", viewer),
        }
        for name, write in refused.items():
            with self.subTest(path=name), self.assertRaisesRegex(ValueError, "viewer can be given subtasks only"):
                write()
        made = s.create_task(self.manager, {"project_id": self.pid, "title": "Viewer step", "owner_user_id": viewer,
                                            "parent_task_id": self.parent["id"]})
        self.assertEqual(made["owner_user_id"], viewer)
        self.assertEqual(self.assign(self.manager, self.step["id"], viewer)["owner_user_id"], viewer)
        s.set_on_hold(self.manager, self.step["id"], "wait", "2027-01-01", viewer)  # a subtask's hold owner
        self.assertEqual(self.fresh(self.step["id"])["owner_user_id"], viewer)

    def test_bulk_names_each_top_level_task_as_blocked(self):
        plan = self.service.bulk_preview(self.manager, self.pid, {"task_ids": [self.parent["id"]], "action": "assignee",
                                                                  "value": self.viewer["id"]})
        self.assertEqual(plan["ok"], [])
        self.assertIn("viewer can be given subtasks only", plan["blocked"][0]["reason"])

    def test_promoting_a_viewers_subtask_is_refused_until_reassigned(self):
        s = self.service
        self.assign(self.manager, self.step["id"], self.viewer["id"])
        with self.assertRaisesRegex(ValueError, "Reassign it first"):
            s.set_parent(self.manager, self.step["id"], None)
        self.assertEqual(self.fresh(self.step["id"])["parent_task_id"], self.parent["id"])
        other = s.create_task(self.owner, {"project_id": self.pid, "title": "Other parent"})
        s.set_parent(self.manager, self.step["id"], other["id"])  # still a subtask: fine
        self.assign(self.manager, self.step["id"], self.member["id"])
        self.assertIsNone(s.set_parent(self.manager, self.step["id"], None)["parent_task_id"])

    def test_a_viewer_assignee_submits_their_subtask_and_nothing_more(self):
        s = self.service
        self.assign(self.manager, self.step["id"], self.viewer["id"])
        submission = s.submit_task(self.viewer, self.step["id"], "done")
        self.assertEqual(submission["status"], "submitted")
        for label, write in (
            ("edit their subtask", lambda: s.update_task(self.viewer, self.step["id"], {
                "title": "Mine now", "expected_revision": self.fresh(self.step["id"])["revision"]})),
            ("submit someone else's task", lambda: s.submit_task(self.viewer, self.parent["id"], "done")),
            ("assign", lambda: self.assign(self.viewer, self.parent["id"], self.member["id"])),
            ("attach a file", lambda: s.add_task_attachment(self.viewer, self.step["id"], "C:/evidence.pdf")),
        ):
            with self.subTest(label), self.assertRaises(Forbidden):
                write()
        # The same as a member assignee: submit only.
        member_step = s.create_task(self.owner, {"project_id": self.pid, "title": "Member step",
                                                 "parent_task_id": self.parent["id"], "owner_user_id": self.member["id"]})
        s.submit_task(self.member, member_step["id"], "done")
        with self.assertRaises(Forbidden):
            s.update_task(self.member, member_step["id"], {"title": "x", "expected_revision": self.fresh(member_step["id"])["revision"]})


class ExistingAssignmentsTests(AssignmentFixture):
    def test_old_assignments_are_kept_and_flagged_until_reassigned(self):
        s = self.service
        self.legacy_owner(self.parent["id"], self.chair["id"])
        top_viewer = s.create_task(self.owner, {"project_id": self.pid, "title": "Viewer top"})
        self.legacy_owner(top_viewer["id"], self.viewer["id"])
        self.legacy_owner(self.step["id"], self.viewer["id"])
        self.assertTrue(self.listed(self.parent["id"])["needs_new_assignee"])
        self.assertTrue(self.listed(top_viewer["id"])["needs_new_assignee"])
        self.assertFalse(self.listed(self.step["id"])["needs_new_assignee"])  # a viewer's subtask is allowed
        self.assertTrue(s.task_detail(self.owner, self.parent["id"])["needs_new_assignee"])
        self.assertNotIn("owner_global_role", self.listed(self.parent["id"]))
        # Nothing forces a change: other fields still save and the owner stays.
        s.update_task(self.manager, self.parent["id"], {"title": "Parent (renamed)", "owner_user_id": self.chair["id"],
                                                        "expected_revision": self.fresh(self.parent["id"])["revision"]})
        self.assertEqual(self.fresh(self.parent["id"])["owner_user_id"], self.chair["id"])
        # Reassigning clears the flag.
        self.assign(self.chair, self.parent["id"], self.member["id"])
        self.assertFalse(self.listed(self.parent["id"])["needs_new_assignee"])
        # A viewer's top-level task shows in the Home tile's filter.
        exported = s.export_tasks(self.owner, {"project_id": self.pid, "risk": "reassign"})
        self.assertEqual([t["title"] for t in exported["tasks"]], ["Viewer top"])

    def test_the_chairman_never_submits_even_as_a_legacy_assignee(self):
        s = self.service
        self.legacy_owner(self.parent["id"], self.chair["id"])
        self.assertFalse(s.task_detail(self.chair, self.parent["id"])["permissions"]["can_submit"])
        with self.assertRaises(Forbidden):
            s.submit_task(self.chair, self.parent["id"], "done")
        self.assertEqual(self.fresh(self.parent["id"])["status"], "draft")
        self.assertTrue(self.listed(self.parent["id"])["needs_new_assignee"])  # still flagged for someone to reassign
        self.assertEqual(s.submit_task(self.manager, self.parent["id"], "done")["status"], "submitted")

    def test_a_viewer_never_submits_a_top_level_task_even_as_a_legacy_assignee(self):
        """G1PPV7: the assignee check used to return True before the 3FQEKB rules, so a viewer
        who held a top-level task from before them could still submit it."""
        s = self.service
        top = s.create_task(self.owner, {"project_id": self.pid, "title": "Viewer top"})
        self.legacy_owner(top["id"], self.viewer["id"])
        self.assertFalse(s.task_detail(self.viewer, top["id"])["permissions"]["can_submit"])
        with self.assertRaises(Forbidden):
            s.submit_task(self.viewer, top["id"], "done")
        self.assertEqual(self.fresh(top["id"])["status"], "draft")
        self.assertEqual(s.list_task_submissions(self.owner, top["id"]), [])
        self.assertTrue(self.listed(top["id"])["needs_new_assignee"])  # still flagged for someone to reassign
        # Their own subtask still submits, and a manager still submits the flagged task.
        self.legacy_owner(self.step["id"], self.viewer["id"])
        self.assertTrue(s.task_detail(self.viewer, self.step["id"])["permissions"]["can_submit"])
        self.assertEqual(s.submit_task(self.viewer, self.step["id"], "done")["status"], "submitted")
        self.assertEqual(s.submit_task(self.manager, top["id"], "done")["status"], "submitted")

    def test_a_member_demoted_to_viewer_loses_submit_on_a_top_level_task_until_restored(self):
        s = self.service
        top = s.create_task(self.owner, {"project_id": self.pid, "title": "Member top",
                                         "owner_user_id": self.member["id"]})
        self.assertTrue(s.task_detail(self.member, top["id"])["permissions"]["can_submit"])
        s.grant_project_access(self.owner, self.pid, self.member["id"], "viewer")
        self.assertFalse(s.task_detail(self.member, top["id"])["permissions"]["can_submit"])
        self.assertTrue(self.listed(top["id"])["needs_new_assignee"])
        with self.assertRaises(Forbidden):
            s.submit_task(self.member, top["id"], "done")
        # A board move into Submitted is a manager's, and goes through the same submit.
        with self.assertRaises(Forbidden):
            s.move_task(self.member, top["id"], {"to_column": "submitted", "confirmed": True,
                                                 "expected_revision": self.fresh(top["id"])["revision"]})
        self.assertEqual(self.fresh(top["id"])["status"], "draft")
        s.grant_project_access(self.owner, self.pid, self.member["id"], "member")
        self.assertFalse(self.listed(top["id"])["needs_new_assignee"])
        self.assertEqual(s.submit_task(self.member, top["id"], "done")["status"], "submitted")

    def test_a_viewer_demoted_inside_the_submit_is_refused_by_the_recheck(self):
        """The permission is evaluated again on the row re-read under the write lock; that row
        carries no parent_task_id, so the rule reads the parent itself."""
        s = self.service
        top = s.create_task(self.owner, {"project_id": self.pid, "title": "Race",
                                         "owner_user_id": self.member["id"]})
        real = s._dependency_gate

        def demote_then_gate(*args, **kwargs):
            s._dependency_gate = real
            s.grant_project_access(self.owner, self.pid, self.member["id"], "viewer")  # lands before BEGIN IMMEDIATE
            return real(*args, **kwargs)
        s._dependency_gate = demote_then_gate
        try:
            with self.assertRaises(Conflict) as caught:
                s.submit_task(self.member, top["id"], "done")
        finally:
            s._dependency_gate = real
        self.assertIn("access to this task changed", str(caught.exception))
        self.assertEqual(self.fresh(top["id"])["status"], "draft")

    def test_a_closed_task_is_not_flagged(self):
        s = self.service
        task = s.create_task(self.owner, {"project_id": self.pid, "title": "Done"})
        s.submit_task(self.owner, task["id"], "done")
        s.accept_submission(self.owner, s.list_task_submissions(self.owner, task["id"])[0]["id"], "ok")
        self.legacy_owner(task["id"], self.chair["id"])
        self.assertFalse(self.listed(task["id"])["needs_new_assignee"])


class CollaboratorTests(AssignmentFixture):
    """Review 13a M1: a collaborator may submit the task, so the Chairman is never one, and a viewer
    collaborates on subtasks only. Reviewers and approvers stay open to everyone."""

    def add(self, task_id, user_id, role="collaborator"):
        return self.service.add_task_reviewer(self.owner, task_id, user_id, role)

    def legacy_collaborator(self, task_id, user_id):
        self.db.execute("INSERT INTO task_reviewers VALUES(?,?,?,?,?)",
                        (task_id, user_id, "collaborator", "2026-09-01T00:00:00Z", self.owner["id"]))

    def test_the_chairman_is_never_a_collaborator(self):
        with self.assertRaisesRegex(ValueError, "cannot be a collaborator"):
            self.add(self.parent["id"], self.chair["id"])
        with self.assertRaisesRegex(ValueError, "cannot be a collaborator"):
            self.add(self.step["id"], self.chair["id"])
        self.add(self.parent["id"], self.chair["id"], "reviewer")  # reviewing is not receiving work
        self.add(self.parent["id"], self.chair["id"], "approver")
        roles = {(r["user_id"], r["role"]) for r in self.service.list_task_reviewers(self.owner, self.parent["id"])}
        self.assertEqual(roles, {(self.chair["id"], "reviewer"), (self.chair["id"], "approver")})

    def test_an_existing_chairman_collaborator_cannot_submit_and_is_flagged(self):
        s = self.service
        self.legacy_collaborator(self.parent["id"], self.chair["id"])
        with self.assertRaises(Forbidden):
            s.submit_task(self.chair, self.parent["id"], "done")
        self.assertEqual(self.fresh(self.parent["id"])["status"], "draft")
        self.assertTrue(self.listed(self.parent["id"])["needs_new_collaborator"])
        self.assertFalse(self.listed(self.parent["id"])["needs_new_assignee"])
        self.assertTrue(s.task_detail(self.owner, self.parent["id"])["needs_new_collaborator"])
        self.assertFalse(s.task_detail(self.chair, self.parent["id"])["permissions"]["can_submit"])
        row = s.list_task_reviewers(self.owner, self.parent["id"])[0]
        self.assertEqual((row["role"], row["not_allowed"]), ("collaborator", True))
        exported = s.export_tasks(self.owner, {"project_id": self.pid, "risk": "reassign"})
        self.assertEqual([t["title"] for t in exported["tasks"]], ["Parent"])
        s.remove_task_reviewer(self.owner, self.parent["id"], self.chair["id"], "collaborator")
        self.assertFalse(self.listed(self.parent["id"])["needs_new_collaborator"])

    def test_a_viewer_collaborates_on_subtasks_only(self):
        s = self.service
        with self.assertRaisesRegex(ValueError, "viewer can collaborate on subtasks only"):
            self.add(self.parent["id"], self.viewer["id"])
        self.add(self.parent["id"], self.viewer["id"], "reviewer")  # still fine as a reviewer
        self.add(self.step["id"], self.viewer["id"])
        self.assertTrue(s.task_detail(self.viewer, self.step["id"])["permissions"]["can_submit"])
        self.assertEqual(s.submit_task(self.viewer, self.step["id"], "done")["status"], "submitted")
        self.assertFalse(self.listed(self.step["id"])["needs_new_collaborator"])
        # Promoting the subtask would put the viewer on a top-level task.
        other = s.create_task(self.owner, {"project_id": self.pid, "title": "Other"})
        v_step = s.create_task(self.owner, {"project_id": self.pid, "title": "V step", "parent_task_id": other["id"]})
        self.add(v_step["id"], self.viewer["id"])
        with self.assertRaisesRegex(ValueError, "Remove them first"):
            s.set_parent(self.manager, v_step["id"], None)

    def test_an_existing_viewer_collaborator_on_a_top_level_task_cannot_submit(self):
        s = self.service
        self.legacy_collaborator(self.parent["id"], self.viewer["id"])
        with self.assertRaises(Forbidden):
            s.submit_task(self.viewer, self.parent["id"], "done")
        self.assertTrue(self.listed(self.parent["id"])["needs_new_collaborator"])
        self.assertFalse(s.task_detail(self.viewer, self.parent["id"])["permissions"]["can_submit"])
        # A member collaborator still submits.
        self.add(self.parent["id"], self.member["id"])
        self.assertEqual(s.submit_task(self.member, self.parent["id"], "done")["status"], "submitted")


class PanelSaveTests(AssignmentFixture):
    def test_a_title_only_save_on_an_undated_task_needs_no_reason(self):
        # Review 13a L1 (older than lock #13): the panel sends "" for an empty date field.
        task = self.service.update_task(self.manager, self.parent["id"], {
            "title": "Parent renamed", "start_date": "", "due_date": "", "owner_user_id": "", "progress": "",
            "description": "", "reason": "", "expected_revision": self.fresh(self.parent["id"])["revision"]})
        self.assertEqual((task["title"], task["start_date"], task["due_date"]), ("Parent renamed", None, None))
        # A real date change still asks for a reason.
        with self.assertRaisesRegex(ValueError, "reason is required"):
            self.service.update_task(self.manager, self.parent["id"], {
                "due_date": "2026-12-01", "expected_revision": self.fresh(self.parent["id"])["revision"]})

    def test_an_explicit_unassign_clears_a_flagged_owner(self):
        # Review 13a L2: sending no one ("") clears the owner, and with it the flag.
        self.legacy_owner(self.parent["id"], self.chair["id"])
        self.assertTrue(self.listed(self.parent["id"])["needs_new_assignee"])
        task = self.service.update_task(self.manager, self.parent["id"], {
            "owner_user_id": "", "expected_revision": self.fresh(self.parent["id"])["revision"]})
        self.assertIsNone(task["owner_user_id"])
        self.assertFalse(self.listed(self.parent["id"])["needs_new_assignee"])


class PickerTests(AssignmentFixture):
    def ids(self, actor, purpose="task"):
        return {u["id"]: u["project_role"] for u in self.service.list_assignable_users(actor, self.pid, purpose)}

    def test_pickers_follow_the_rules(self):
        task = self.ids(self.manager)
        self.assertNotIn(self.chair["id"], task)
        self.assertNotIn(self.viewer["id"], task)
        self.assertEqual(task[self.member["id"]], "member")
        self.assertIsNone(task[self.owner["id"]])
        subtask = self.ids(self.manager, "subtask")
        self.assertEqual(subtask[self.viewer["id"]], "viewer")
        self.assertNotIn(self.chair["id"], subtask)
        reviewer = self.ids(self.manager, "reviewer")  # unchanged: everyone with access
        self.assertIn(self.chair["id"], reviewer)
        self.assertIn(self.viewer["id"], reviewer)
        self.assertEqual(self.ids(self.chair, "subtask"), subtask)  # the Chairman may assign
        with self.assertRaises(Forbidden):
            self.ids(self.chair, "reviewer")
        with self.assertRaises(Forbidden):
            self.ids(self.member)
        with self.assertRaises(ValueError):
            self.ids(self.manager, "everyone")


class ImporterAndTemplateTests(AssignmentFixture):
    def setUp(self):
        super().setUp()
        from link_roots import allow_attachment_roots
        allow_attachment_roots(self)
        self.service.set_import_template_config(self.owner, {"preset": "full"})

    def preview(self, rows):
        from test_import import filled_template
        return self.service.import_preview(self.owner, self.pid, "demo.xlsx", filled_template(rows), {})

    def test_the_importer_refuses_those_rows_by_name(self):
        rows = [
            {"import_key": "A-1", "title": "For the chairman", "owner_email": "chair@example.org"},
            {"import_key": "A-2", "title": "Viewer top", "owner_email": "viewer@example.org"},
            {"import_key": "A-3", "title": "Viewer step", "owner_email": "viewer@example.org", "parent_key": "A-4"},
            {"import_key": "A-4", "title": "Member task", "owner_email": "member@example.org"},
            # Review 13a M1: the Collaborators column meets the same rules.
            {"import_key": "A-5", "title": "Chair helps", "owner_email": "member@example.org",
             "collaborators": "chair@example.org"},
            {"import_key": "A-6", "title": "Viewer helps top", "owner_email": "member@example.org",
             "collaborators": "viewer@example.org"},
            {"import_key": "A-7", "title": "Viewer helps step", "owner_email": "member@example.org",
             "collaborators": "viewer@example.org", "parent_key": "A-4"},
        ]
        by_key = {r["import_key"]: r for r in self.preview(rows)["rows"]}
        codes = lambda key: [f["code"] for f in by_key[key]["findings"] if f["level"] == "error"]
        self.assertEqual(codes("A-1"), ["E_OWNER_CHAIRMAN"])
        self.assertIn("is the Chairman", by_key["A-1"]["findings"][0]["message"])
        self.assertEqual(codes("A-2"), ["E_OWNER_VIEWER"])
        self.assertIn("give the row a Parent Key", [f for f in by_key["A-2"]["findings"] if f["level"] == "error"][0]["message"])
        self.assertEqual(codes("A-3"), [])
        self.assertEqual(by_key["A-3"]["values"]["owner"], "Viewer")
        self.assertEqual(codes("A-4"), [])
        self.assertEqual(codes("A-5"), ["E_COLLABORATOR_CHAIRMAN"])
        self.assertEqual(codes("A-6"), ["E_COLLABORATOR_VIEWER"])
        self.assertEqual(codes("A-7"), [])

    def test_templates_never_assign_the_chairman_or_a_viewer_at_top_level(self):
        s = self.service
        self.legacy_owner(self.parent["id"], self.chair["id"])
        self.legacy_owner(self.step["id"], self.viewer["id"])
        template = s.save_project_as_template(self.owner, self.pid, "Roles")
        by_title = {t["title"]: t for t in template["body"]["tasks"]}
        self.assertIsNone(by_title["Parent"]["suggested_role"])  # a Chairman-owned task carries no suggestion
        self.assertEqual(by_title["Step"]["suggested_role"], "viewer")
        self.assertNotIn("chairman", s.list_templates(self.owner)[0]["roles"])
        with self.assertRaisesRegex(ValueError, "never assigned"):
            s.create_project_from_template(self.owner, template["id"], "New", role_assignments={"chairman": self.chair["id"]})
        # An older template that still names the 'chairman' role creates the task unassigned.
        body = {"kind": "task", "anchor": None, "dependencies": [], "tasks": [
            {"local_id": 0, "title": "Chair task", "suggested_role": "chairman", "parent_local_id": None, "attachments": []},
            {"local_id": 1, "title": "Viewer top", "suggested_role": "viewer", "parent_local_id": None, "attachments": []},
            {"local_id": 2, "title": "Viewer step", "suggested_role": "viewer", "parent_local_id": 1, "attachments": []}]}
        self.db.execute("INSERT INTO templates(id,kind,name,description,body_json,created_by,created_at) VALUES(?,?,?,?,?,?,?)",
                        ("old-1", "task", "Old", "", json.dumps(body), self.owner["id"], "2026-09-19T00:00:00Z"))
        s.create_task_from_template(self.owner, "old-1", self.pid)
        made = {t["title"]: t for t in s.list_tasks(self.owner, self.pid)}
        self.assertIsNone(made["Chair task"]["owner_user_id"])
        self.assertIsNone(made["Viewer top"]["owner_user_id"])  # a viewer never gets a top-level task
        self.assertEqual(made["Viewer step"]["owner_user_id"], self.viewer["id"])


if __name__ == "__main__":
    unittest.main()
