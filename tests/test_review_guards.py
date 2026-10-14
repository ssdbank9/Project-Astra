"""Negative cases from the independent pre-deployment review."""
import http.client
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from astra.db import connect, transaction
from astra.service import AstraService, Conflict, Forbidden
from astra.web import AstraServer
from link_roots import allow_attachment_roots, link


class ReviewGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect(Path(self.temp.name) / 'review.sqlite3')
        self.addCleanup(self.db.close)
        self.s = AstraService(self.db)
        self.owner = self.s.create_initial_owner('review-owner@example.org', 'Owner', 'fixture password safe')
        self.secondary = self.s.create_user(self.owner, 'review-secondary@example.org', 'Secondary', 'fixture password safe')
        self.secondary = self.s.grant_secondary_owner(self.owner, self.secondary['id'], 'Fixture grant')
        self.chairman = self.s.create_user(self.owner, 'review-chair@example.org', 'Chairman', 'fixture password safe', 'chairman')
        self.manager = self.s.create_user(self.owner, 'review-manager@example.org', 'Manager', 'fixture password safe')
        self.project = self.s.create_project(self.owner, 'Review project')
        self.pid = self.project['id']
        self.s.grant_project_access(self.owner, self.pid, self.manager['id'], 'manager')
        self.task = self.s.create_task(self.owner, {'project_id': self.pid, 'title': 'Work', 'status': 'in_progress', 'owner_user_id': self.manager['id']})
        self.other = self.s.create_task(self.owner, {'project_id': self.pid, 'title': 'Other'})
        allow_attachment_roots(self)

    @contextmanager
    def before_write(self, callback):
        fired = False

        @contextmanager
        def interleaved(db):
            nonlocal fired
            if not fired and not db.in_transaction:
                fired = True
                callback()
            with transaction(db):
                yield

        with patch('astra.service.transaction', interleaved):
            yield
        self.assertTrue(fired, 'The probe must reach the actual write boundary')

    def close(self):
        self.s.close_project(self.owner, self.pid, 'Residual work documented', exceptional=True)

    def test_closed_project_templates_refuse_before_any_row_or_event(self):
        template = self.s.save_task_as_template(self.owner, self.task['id'], 'Work template')
        self.close()
        before = tuple(self.db.iterdump())
        for actor in (self.owner, self.secondary):
            with self.subTest(role=actor['display_name']), self.assertRaises(Forbidden):
                self.s.create_task_from_template(actor, template['id'], self.pid)
        self.assertEqual(tuple(self.db.iterdump()), before)

    def test_template_destination_closed_between_checks_and_write_refused(self):
        template = self.s.save_task_as_template(self.owner, self.task['id'], 'Work template')
        with self.before_write(self.close), self.assertRaises(Forbidden):
            self.s.create_task_from_template(self.owner, template['id'], self.pid)
        self.assertEqual(self.db.execute('SELECT count(*) FROM tasks').fetchone()[0], 2)

    def test_closed_project_dependency_add_and_remove_refused(self):
        self.s.add_task_dependency(self.owner, self.task['id'], self.other['id'])
        self.close()
        before = tuple(self.db.iterdump())
        for actor in (self.owner, self.manager):
            for action in ('add', 'remove'):
                with self.subTest(role=actor['display_name'], action=action), transaction(self.db), self.assertRaises(Forbidden):
                    if action == 'add':
                        self.s.add_task_dependency(actor, self.task['id'], self.other['id'])
                    else:
                        self.s.remove_task_dependency(actor, self.task['id'], self.other['id'], 'Changed sequence')
        self.assertEqual(tuple(self.db.iterdump()), before)

    def test_dependency_destination_closed_at_write_boundary_refused(self):
        with self.before_write(self.close), self.assertRaises(Forbidden):
            self.s.add_task_dependency(self.owner, self.task['id'], self.other['id'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM task_dependencies').fetchone()[0], 0)

    def test_only_active_app_owners_reopen(self):
        for actor in (self.owner, self.secondary):
            self.close()
            self.assertEqual(self.s.reopen_project(actor, self.pid, 'Correction')['status'], 'active')
        self.close()
        for actor in (self.chairman, self.manager):
            with self.subTest(role=actor['global_role']), self.assertRaises(Forbidden):
                self.s.reopen_project(actor, self.pid, 'Correction')

    def test_revoked_owner_cannot_close_or_submit_with_old_snapshot(self):
        snapshot = dict(self.secondary)
        self.s.revoke_secondary_owner(self.owner, self.secondary['id'], 'Access revoked')
        before = tuple(self.db.iterdump())
        with self.assertRaises(Forbidden):
            self.s.close_project(snapshot, self.pid, 'Residual', exceptional=True)
        with self.assertRaises(Forbidden):
            self.s.submit_task(snapshot, self.task['id'], 'Ready')
        self.assertEqual(tuple(self.db.iterdump()), before)

    def test_actor_revoked_between_early_checks_and_write_refused(self):
        with self.before_write(lambda: self.s.revoke_secondary_owner(self.owner, self.secondary['id'], 'Access revoked')):
            with self.assertRaises(Forbidden):
                self.s.close_project(self.secondary, self.pid, 'Residual', exceptional=True)
        self.assertEqual(self.s.get_project(self.owner, self.pid)['status'], 'active')

    def test_deactivated_actor_cannot_create_task_or_dependency(self):
        snapshot = dict(self.manager)
        self.s.set_user_active(self.owner, self.manager['id'], False)
        before = tuple(self.db.iterdump())
        with self.assertRaises(Forbidden):
            self.s.create_task(snapshot, {'project_id': self.pid, 'title': 'Invalid new task'})
        with self.assertRaises(Forbidden):
            self.s.add_task_dependency(snapshot, self.task['id'], self.other['id'])
        self.assertEqual(tuple(self.db.iterdump()), before)

    def test_manager_demotion_at_write_boundary_refuses_criticality(self):
        with self.before_write(lambda: self.s.grant_project_access(self.owner, self.pid, self.manager['id'], 'viewer')):
            with self.assertRaises(Forbidden):
                self.s.confirm_criticality(self.manager, self.task['id'], 'high', 'Risk increased')
        self.assertIsNone(self.s.get_task(self.owner, self.task['id'])['criticality'])

    def test_manager_demotion_at_write_boundary_refuses_project_request(self):
        with self.before_write(lambda: self.s.grant_project_access(self.owner, self.pid, self.manager['id'], 'viewer')):
            with self.assertRaises(Forbidden):
                self.s.close_project(self.manager, self.pid, 'Residual work')
        self.assertEqual(self.db.execute('SELECT count(*) FROM owner_action_requests').fetchone()[0], 0)

    def test_manager_demotion_at_write_boundary_refuses_dependency(self):
        with self.before_write(lambda: self.s.grant_project_access(self.owner, self.pid, self.manager['id'], 'viewer')):
            with self.assertRaises(Forbidden):
                self.s.add_task_dependency(self.manager, self.task['id'], self.other['id'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM task_dependencies').fetchone()[0], 0)

    def test_manager_demotion_at_write_boundary_refuses_proposal_and_lease(self):
        with self.before_write(lambda: self.s.grant_project_access(self.owner, self.pid, self.manager['id'], 'viewer')):
            with self.assertRaises(Forbidden):
                self.s.propose_schedule(self.manager, self.task['id'], None, '2027-03-01', 'Proposal')
        self.assertEqual(self.db.execute('SELECT count(*) FROM task_schedule_proposals').fetchone()[0], 0)
        self.s.grant_project_access(self.owner, self.pid, self.manager['id'], 'manager')
        with self.before_write(lambda: self.s.grant_project_access(self.owner, self.pid, self.manager['id'], 'viewer')):
            with self.assertRaises(Forbidden):
                self.s.acquire_task_lock(self.manager, self.task['id'], 'edit')
        self.assertEqual(self.db.execute('SELECT count(*) FROM task_locks').fetchone()[0], 0)

    def test_parent_promotion_rechecks_owner_eligibility_at_write_boundary(self):
        self.s.set_parent(self.owner, self.task['id'], self.other['id'])
        with self.before_write(lambda: self.s.grant_project_access(self.owner, self.pid, self.manager['id'], 'viewer')):
            with self.assertRaises(ValueError):
                self.s.set_parent(self.owner, self.task['id'], None)
        self.assertEqual(self.s.get_task(self.owner, self.task['id'])['parent_task_id'], self.other['id'])

    def test_submitted_ordinary_edits_remain_allowed(self):
        self.s.submit_task(self.manager, self.task['id'], 'Ready for review')
        task = self.s.get_task(self.manager, self.task['id'])
        updated = self.s.update_task(self.manager, task['id'], {'title': 'Clarified title', 'description': 'Clarified details', 'due_date': '2027-03-01', 'reason': 'Clarified plan', 'expected_revision': task['revision']})
        self.assertEqual((updated['status'], updated['title'], updated['description'], updated['due_date']), ('submitted', 'Clarified title', 'Clarified details', '2027-03-01'))

    def test_revoked_owner_cannot_mutate_settings_templates_files_or_download_keys(self):
        entity = self.s.create_entity(self.owner, 'Entity')
        template = self.s.save_task_as_template(self.owner, self.task['id'], 'Task template')
        project_template = self.s.save_project_as_template(self.owner, self.pid, 'Project template')
        closed = self.s.create_project(self.owner, 'Finished')
        self.s.close_project(self.owner, closed['id'], 'Finished')
        self.s.add_holiday(self.owner, self.pid, '2027-12-25', 'Holiday')
        attachment = self.s.add_task_attachment(self.owner, self.task['id'], link('refs', 'review.txt'), 'Review')
        result = self.s.mark_final_result(self.owner, self.task['id'], 'attachment', attachment['id'])
        self.s.acquire_task_lock(self.manager, self.task['id'], 'edit')
        actor = dict(self.secondary)
        self.s.revoke_secondary_owner(self.owner, actor['id'], 'Access revoked')
        actions = {
            'create entity': lambda: self.s.create_entity(actor, 'Other entity'),
            'rename entity': lambda: self.s.rename_entity(actor, entity['id'], 'Renamed'),
            'entity active': lambda: self.s.set_entity_active(actor, entity['id'], False),
            'seed entities': lambda: self.s.seed_default_entities(actor),
            'project entities': lambda: self.s.set_project_entities(actor, self.pid, [entity['id']]),
            'primary entity': lambda: self.s.set_primary_entity(actor, self.pid, entity['id']),
            'working days': lambda: self.s.set_working_days(actor, self.pid, '01234'),
            'add holiday': lambda: self.s.add_holiday(actor, self.pid, '2027-12-31', 'Other holiday'),
            'remove holiday': lambda: self.s.remove_holiday(actor, self.pid, '2027-12-25'),
            'budget': lambda: self.s.set_project_budget(actor, self.pid, 100, 'USD'),
            'project schedule': lambda: self.s.set_project_schedule(actor, self.pid, None, '2027-03-01', 'Changed target'),
            'create project': lambda: self.s.create_project(actor, 'Other project'),
            'save task template': lambda: self.s.save_task_as_template(actor, self.task['id'], 'Other task template'),
            'save project template': lambda: self.s.save_project_as_template(actor, self.pid, 'Other project template'),
            'delete template': lambda: self.s.delete_template(actor, template['id']),
            'create from task template': lambda: self.s.create_task_from_template(actor, template['id'], self.pid),
            'create from project template': lambda: self.s.create_project_from_template(actor, project_template['id'], 'Other project'),
            'add attachment': lambda: self.s.add_task_attachment(actor, self.other['id'], link('refs', 'other.txt'), 'Other'),
            'remove attachment': lambda: self.s.remove_task_attachment(actor, self.task['id'], attachment['id']),
            'publish final result': lambda: self.s.mark_final_result(actor, self.task['id'], 'attachment', attachment['id']),
            'unpublish final result': lambda: self.s.unmark_final_result(actor, result['id']),
            'reopen project': lambda: self.s.reopen_project(actor, closed['id'], 'Correction'),
            'force unlock': lambda: self.s.force_unlock_task(actor, self.task['id'], 'Correction'),
            'import settings': lambda: self.s.set_import_template_config(actor, {'preset': 'simple'}),
            'download key reservation': lambda: self.s.import_template(actor, 'xlsx', self.pid),
        }
        before = tuple(self.db.iterdump())
        for name, action in actions.items():
            with self.subTest(action=name), self.assertRaises(Forbidden):
                action()
            self.assertEqual(tuple(self.db.iterdump()), before, name)

    def test_target_deactivated_at_write_boundary_refuses_reviewer(self):
        with self.before_write(lambda: self.s.set_user_active(self.owner, self.manager['id'], False)):
            with self.assertRaises(ValueError):
                self.s.add_task_reviewer(self.owner, self.task['id'], self.manager['id'], 'reviewer')
        self.assertEqual(self.db.execute('SELECT count(*) FROM task_reviewers').fetchone()[0], 0)

    def test_template_role_target_deactivated_at_write_boundary_refused(self):
        template = self.s.save_task_as_template(self.owner, self.task['id'], 'Role template')
        with self.before_write(lambda: self.s.set_user_active(self.owner, self.manager['id'], False)):
            with self.assertRaises(ValueError):
                self.s.create_task_from_template(self.owner, template['id'], self.pid, role_assignments={'manager': self.manager['id']})
        self.assertEqual(self.db.execute('SELECT count(*) FROM tasks').fetchone()[0], 2)

    def test_closed_project_dependency_removal_race_refused(self):
        self.s.add_task_dependency(self.owner, self.task['id'], self.other['id'])
        with self.before_write(self.close), self.assertRaises(Forbidden):
            self.s.remove_task_dependency(self.owner, self.task['id'], self.other['id'], 'Changed sequence')
        self.assertEqual(self.db.execute('SELECT count(*) FROM task_dependencies').fetchone()[0], 1)

    def test_manager_demotion_at_write_boundary_refuses_reviewer(self):
        with self.before_write(lambda: self.s.grant_project_access(self.owner, self.pid, self.manager['id'], 'viewer')):
            with self.assertRaises(Forbidden):
                self.s.add_task_reviewer(self.manager, self.task['id'], self.owner['id'], 'reviewer')
        self.assertEqual(self.db.execute('SELECT count(*) FROM task_reviewers').fetchone()[0], 0)

    def test_history_template_capture_remains_allowed_and_uses_one_snapshot(self):
        self.close()
        original = self.s._snapshot_tasks

        def locked_snapshot(rows):
            self.assertTrue(self.db.in_transaction)
            return original(rows)

        with patch.object(self.s, '_snapshot_tasks', locked_snapshot):
            template = self.s.save_project_as_template(self.owner, self.pid, 'Historical project')
        self.assertEqual(len(template['body']['tasks']), 2)

    def test_bulk_cleanup_still_runs_after_actor_deactivated(self):
        self.s._take_bulk_leases(self.manager, [self.task['id']], 'fixture-bulk-token')
        self.s.set_user_active(self.owner, self.manager['id'], False)
        self.s._release_bulk_leases('fixture-bulk-token')
        self.assertEqual(self.db.execute('SELECT count(*) FROM task_locks').fetchone()[0], 0)

    def test_owner_transfer_invalidates_primary_powers_but_keeps_secondary_project_rights(self):
        actor = dict(self.owner)
        self.s.transfer_primary_owner(self.secondary['email'], {'via': 'fixture'})
        with self.assertRaises(Forbidden):
            self.s.grant_secondary_owner(actor, self.manager['id'], 'Old primary request')
        self.assertEqual(self.s.create_project(actor, 'Secondary project request')['name'], 'Secondary project request')

    def test_stale_owner_board_refusal_still_audited_after_rollback(self):
        actor = dict(self.secondary)
        self.s.revoke_secondary_owner(self.owner, actor['id'], 'Revoked')
        with self.assertRaises(Forbidden):
            self.s.move_task(actor, self.other['id'], {'to_column': 'ready', 'expected_revision': self.other['revision']})
        self.assertEqual(self.s.get_task(self.owner, self.other['id'])['status'], 'draft')
        self.assertEqual(self.db.execute("SELECT count(*) FROM task_events WHERE event_type='board_move_blocked'").fetchone()[0], 1)

    def test_old_primary_demotion_refuses_account_change_and_retains_audit(self):
        actor = dict(self.owner)
        self.s.transfer_primary_owner(self.secondary['email'], {'via': 'fixture'})
        primary = self.s.get_user(self.secondary['id'])
        self.s.revoke_secondary_owner(primary, actor['id'], 'Revoked')
        with self.assertRaises(Forbidden):
            self.s.grant_secondary_owner(actor, self.manager['id'], 'Old primary request')
        self.assertEqual(self.s.get_user(self.manager['id'])['global_role'], 'member')
        self.assertEqual(self.db.execute("SELECT count(*) FROM user_events WHERE event_type='owner_change_blocked'").fetchone()[0], 1)

    def test_board_rank_failure_rolls_back_move_and_history(self):
        self.db.execute(f"CREATE TEMP TRIGGER reject_rank BEFORE UPDATE OF board_rank ON tasks WHEN NEW.id='{self.other['id']}' BEGIN SELECT RAISE(ABORT, 'fixture rank failure'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'fixture rank failure'):
            self.s.move_task(self.owner, self.other['id'], {'to_column': 'ready', 'expected_revision': self.other['revision']})
        after = self.s.get_task(self.owner, self.other['id'])
        self.assertEqual((after['status'], after['revision']), ('draft', self.other['revision']))
        self.assertEqual(self.db.execute("SELECT count(*) FROM task_events WHERE event_type='task_updated' AND task_id=?", (self.other['id'],)).fetchone()[0], 0)

    def test_board_move_has_one_outer_write_boundary(self):
        outer = 0

        @contextmanager
        def counted(db):
            nonlocal outer
            outer += int(not db.in_transaction)
            with transaction(db):
                yield

        with patch('astra.service.transaction', counted):
            result = self.s.move_task(self.owner, self.other['id'], {'to_column': 'ready', 'expected_revision': self.other['revision']})
        self.assertEqual(result['task']['status'], 'assigned')
        self.assertEqual(outer, 1)


class ReviewGuardHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get('ASTRA_HOME')
        os.environ['ASTRA_HOME'] = self.temp.name
        self.server = AstraServer(('127.0.0.1', 0))
        self.s = self.server.service
        self.owner = self.s.create_initial_owner('http-owner@example.org', 'Owner', 'fixture password safe')
        self.project = self.s.create_project(self.owner, 'HTTP review')
        self.task = self.s.create_task(self.owner, {'project_id': self.project['id'], 'title': 'Task'})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=5)

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        if self.old_home is None:
            os.environ.pop('ASTRA_HOME', None)
        else:
            os.environ['ASTRA_HOME'] = self.old_home
        self.temp.cleanup()

    def request(self, method, path, payload, auth=None):
        headers = {'Content-Type': 'application/json'}
        if auth:
            headers.update({'Cookie': auth[0], 'X-CSRF-Token': auth[1]})
        self.connection.request(method, path, json.dumps(payload).encode(), headers)
        r = self.connection.getresponse()
        body = json.loads(r.read())
        return r, body

    def login(self, email):
        r, b = self.request('POST', '/api/login', {'email': email, 'password': 'fixture password safe'})
        self.assertEqual(r.status, 200)
        auth = (r.getheader('Set-Cookie').split(';', 1)[0], b['csrf'])
        if b['user'].get('must_change_password'):
            # These cases test review-guard routes for established users. A5's dedicated
            # tests retain real new-account behavior instead of normalizing it here.
            self.s.db.execute(
                'UPDATE users SET must_change_password=0 WHERE id=?', (b['user']['id'],)
            )
        return auth

    def test_closed_template_refused_over_http(self):
        template = self.s.save_task_as_template(self.owner, self.task['id'], 'Template')
        self.s.close_project(self.owner, self.project['id'], 'Residual', exceptional=True)
        r, _ = self.request('POST', f"/api/templates/{template['id']}/create-task", {'project_id': self.project['id']}, self.login(self.owner['email']))
        self.assertEqual(r.status, 403)
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM tasks').fetchone()[0], 1)

    def test_chairman_reopen_refused_over_http(self):
        chair = self.s.create_user(self.owner, 'http-chair@example.org', 'Chairman', 'fixture password safe', 'chairman')
        self.s.close_project(self.owner, self.project['id'], 'Residual', exceptional=True)
        r, _ = self.request('POST', f"/api/projects/{self.project['id']}/reopen", {'reason': 'Correction'}, self.login(chair['email']))
        self.assertEqual(r.status, 403)
        self.assertEqual(self.s.get_project(self.owner, self.project['id'])['status'], 'closed')

    def test_authenticated_snapshot_revoked_before_close_refused(self):
        secondary = self.s.create_user(self.owner, 'http-secondary@example.org', 'Secondary', 'fixture password safe')
        secondary = self.s.grant_secondary_owner(self.owner, secondary['id'], 'Grant')
        auth = self.login(secondary['email'])
        original = AstraService.close_project

        def revoke_then_close(service, actor, *args, **kwargs):
            service.revoke_secondary_owner(service.get_user(self.owner['id']), actor['id'], 'Revoked during request')
            return original(service, actor, *args, **kwargs)

        with patch.object(AstraService, 'close_project', revoke_then_close):
            r, _ = self.request('POST', f"/api/projects/{self.project['id']}/close", {'note': 'Residual', 'exceptional': True}, auth)
        self.assertEqual(r.status, 403)
        self.assertEqual(self.s.get_project(self.owner, self.project['id'])['status'], 'active')

    def test_authenticated_snapshot_revoked_before_submit_refused(self):
        secondary = self.s.create_user(self.owner, 'http-submit@example.org', 'Secondary', 'fixture password safe')
        secondary = self.s.grant_secondary_owner(self.owner, secondary['id'], 'Grant')
        auth = self.login(secondary['email'])
        original = AstraService.submit_task

        def revoke_then_submit(service, actor, *args, **kwargs):
            service.revoke_secondary_owner(service.get_user(self.owner['id']), actor['id'], 'Revoked during request')
            return original(service, actor, *args, **kwargs)

        with patch.object(AstraService, 'submit_task', revoke_then_submit):
            r, _ = self.request('POST', f"/api/tasks/{self.task['id']}/submit", {'note': 'Ready'}, auth)
        self.assertEqual(r.status, 403)
        self.assertEqual(self.s.get_task(self.owner, self.task['id'])['status'], 'draft')
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM task_submissions').fetchone()[0], 0)

    def test_closed_dependencies_refused_for_owner_and_manager_over_http(self):
        manager = self.s.create_user(self.owner, 'http-manager@example.org', 'Manager', 'fixture password safe')
        self.s.grant_project_access(self.owner, self.project['id'], manager['id'], 'manager')
        other = self.s.create_task(self.owner, {'project_id': self.project['id'], 'title': 'Other'})
        self.s.close_project(self.owner, self.project['id'], 'Residual', exceptional=True)
        for actor in (self.owner, manager):
            r, _ = self.request('POST', '/api/task-dependencies', {'predecessor_task_id': self.task['id'], 'successor_task_id': other['id']}, self.login(actor['email']))
            self.assertEqual(r.status, 403)
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM task_dependencies').fetchone()[0], 0)

    def test_primary_and_secondary_owner_reopen_over_http(self):
        secondary = self.s.create_user(self.owner, 'http-reopen@example.org', 'Secondary', 'fixture password safe')
        secondary = self.s.grant_secondary_owner(self.owner, secondary['id'], 'Grant')
        for actor in (self.owner, secondary):
            self.s.close_project(self.owner, self.project['id'], 'Residual', exceptional=True)
            r, b = self.request('POST', f"/api/projects/{self.project['id']}/reopen", {'reason': 'Correction'}, self.login(actor['email']))
            self.assertEqual(r.status, 200)
            self.assertEqual(b['project']['status'], 'active')


if __name__ == '__main__':
    unittest.main()
