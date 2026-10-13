import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra.db import connect, transaction
from astra.service import AstraService, Conflict, Forbidden
from import_fixtures import filled_template
import test_web


class DeadlineNotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect(Path(self.temp.name) / 'test.sqlite3')
        self.addCleanup(self.db.close)
        self.s = AstraService(self.db)
        self.owner = self.s.create_initial_owner('owner@example.org', 'Primary', 'synthetic password')
        deputy = self.s.create_user(self.owner, 'deputy@example.org', 'Deputy', 'synthetic password')
        self.deputy = self.s.grant_secondary_owner(self.owner, deputy['id'], 'Cover')
        self.chair = self.s.create_user(self.owner, 'chair@example.org', 'Chairman', 'synthetic password', 'chairman')
        self.member = self.s.create_user(self.owner, 'member@example.org', 'Member', 'synthetic password')
        self.p = self.s.create_project(self.owner, 'School')
        self.s.grant_project_access(self.owner, self.p['id'], self.member['id'], 'manager')

    def task(self, title='Prepare', finish='2026-10-10', **extra):
        payload = dict(project_id=self.p['id'], title=title, start_date='2026-10-01', due_date=finish)
        payload.update(extra)
        return self.s.create_task(self.owner, payload)

    def clear(self):
        self.db.execute('DELETE FROM notifications')

    def notices(self, actor, kind=None):
        return [n for n in self.s.list_notifications(actor) if kind is None or n['kind'] == kind]

    def assertRecipients(self, kind, old, new, count=1):
        for actor in (self.owner, self.deputy, self.chair):
            notes = self.notices(actor, kind)
            self.assertEqual(len(notes), count, actor['display_name'])
            for note in notes:
                for text in (old, new, 'School'):
                    self.assertIn(text, note['summary'])
        self.assertEqual(self.notices(self.member), [])

    def edit(self, task, finish, actor=None):
        return self.s.update_task(actor or self.owner, task['id'], dict(
            due_date=finish, expected_revision=task['revision'], confirmed=True, reason='Reviewed extension'))

    def test_saved_task_extension_includes_acting_owner_and_one_complete_project_notice(self):
        task = self.task()
        self.clear()
        self.edit(task, '2026-10-14')
        self.assertRecipients('task_updated', '2026-10-10', '2026-10-14')
        self.assertRecipients('project_finish_extended', '2026-10-10', '2026-10-14')
        self.assertIsNone(self.s.get_project(self.owner, self.p['id'])['target_date'])
        # Retrying the same event is idempotent, including the acting Owner.
        note = self.notices(self.chair, 'task_updated')[0]
        self.s._notify_deadline_recipients(self.owner['id'], note['event_id'], task['id'],
                                          note['kind'], note['summary'])
        self.assertRecipients('task_updated', '2026-10-10', '2026-10-14')

    def test_task_extension_inside_existing_project_finish_and_inactive_recipients(self):
        task = self.task()
        self.task('Later task', '2026-10-30')
        inactive = self.s.create_user(self.owner, 'inactive@example.org', 'Inactive', 'synthetic password', 'chairman')
        self.db.execute('UPDATE users SET active=0 WHERE id=?', (inactive['id'],))
        self.clear()
        self.edit(task, '2026-10-14', self.deputy)
        self.assertRecipients('task_updated', '2026-10-10', '2026-10-14')
        self.assertEqual(self.notices(inactive), [])
        self.assertEqual(self.notices(self.chair, 'project_finish_extended'), [])

    def test_initial_earlier_unchanged_and_unrelated_changes_do_not_notify_chairman(self):
        task = self.task(finish=None, start_date=None)
        self.clear()
        task = self.edit(task, '2026-10-10')
        task = self.edit(task, '2026-10-09')
        self.edit(task, '2026-10-09')
        self.s.set_project_schedule(self.owner, self.p['id'], None, '2026-10-30', 'Initial target')
        self.s.set_project_schedule(self.owner, self.p['id'], None, '2026-10-29', 'Earlier target')
        self.assertEqual(self.notices(self.chair), [])
        self.assertEqual(self.notices(self.owner, 'project_finish_extended'), [])

    def test_agreed_target_extension_notifies_chairman_without_management_authority(self):
        self.s.set_project_schedule(self.owner, self.p['id'], None, '2026-10-10', 'Initial target')
        self.clear()
        self.s.set_project_schedule(self.owner, self.p['id'], None, '2026-10-14', 'Agreed extension')
        self.assertRecipients('project_schedule_changed', '2026-10-10', '2026-10-14')
        with self.assertRaises(Forbidden):
            self.s.set_project_schedule(self.chair, self.p['id'], None, '2026-10-20', 'Not authorized')
        # Reading does not confer permission to mark another recipient's copy read.
        note = self.notices(self.owner)[0]
        with self.assertRaises(Forbidden):
            self.s.mark_notification_read(self.chair, note['id'])
        self.s.mark_notification_read(self.chair, self.notices(self.chair)[0]['id'])
        self.assertEqual(self.s.unread_notification_count(self.chair), 0)
        self.assertEqual(self.s.unread_notification_count(self.owner), 1)

    def test_linked_preview_and_stale_commit_create_no_notices_then_one_final_range(self):
        a = self.task('A', '2026-10-03')
        b = self.s.create_task(self.owner, dict(project_id=self.p['id'], title='B',
            start_date='2026-10-04', due_date='2026-10-06'))
        self.s.add_task_dependency(self.owner, a['id'], b['id'])
        payload = dict(mode='date', expected_revision=a['revision'], start_date='2026-10-04', due_date='2026-10-06')
        self.clear()
        plan = self.s.timeline_schedule_preview(self.owner, a['id'], payload)
        self.assertEqual(self.notices(self.chair), [])
        with self.assertRaises(Conflict):
            self.s.timeline_schedule_apply(self.owner, a['id'], dict(payload, fingerprint='stale', confirmed=True))
        self.assertEqual(self.notices(self.chair), [])
        self.s.timeline_schedule_apply(self.owner, a['id'], dict(payload, fingerprint=plan['fingerprint'], confirmed=True))
        self.assertRecipients('project_finish_extended', '2026-10-06', '2026-10-09')
        self.assertEqual(len(self.notices(self.chair, 'task_updated')), 2)

    def test_audit_failure_and_outer_rollback_remove_all_deadline_notices(self):
        task = self.task()
        self.clear()
        with patch.object(self.s, '_write_audit_events', side_effect=RuntimeError('Synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.edit(task, '2026-10-14')
        self.assertEqual(self.notices(self.chair), [])
        with self.assertRaises(RuntimeError):
            with transaction(self.db):
                self.edit(task, '2026-10-14')
                raise RuntimeError('Outer transaction failed')
        self.assertEqual(self.notices(self.chair), [])
        self.assertEqual(self.s.get_task(self.owner, task['id'])['due_date'], '2026-10-10')
        self.edit(task, '2026-10-14')
        self.assertRecipients('project_finish_extended', '2026-10-10', '2026-10-14')

    def test_schedule_proposal_notifies_only_when_approved_and_reopening_notifies(self):
        task = self.task(status='cancelled')
        self.clear()
        task = self.s.reopen_task(self.owner, task['id'], 'Resume', '2026-10-14', confirmed=True)
        self.assertRecipients('task_reopened', '2026-10-10', '2026-10-14')
        self.clear()
        proposal = self.s.propose_schedule(self.member, task['id'], '2026-10-01', '2026-10-18', 'More time')
        self.assertEqual(self.notices(self.chair), [])
        with self.assertRaises(Forbidden):
            self.s.approve_schedule_proposal(self.chair, proposal['id'], 'Cannot approve')
        self.s.approve_schedule_proposal(self.owner, proposal['id'], 'Reviewed', confirmed=True)
        self.assertRecipients('schedule_revised', '2026-10-14', '2026-10-18')
        self.assertRecipients('project_finish_extended', '2026-10-14', '2026-10-18')

    def test_multirow_reimport_uses_original_complete_project_finish(self):
        self.s.set_import_template_config(self.owner, {'preset': 'full'})
        rows = [dict(import_key='A', title='A', due_date='2026-10-10'),
                dict(import_key='B', title='B', due_date='2026-10-12')]
        self.s.import_commit(self.owner, self.p['id'], 'synthetic.xlsx', filled_template(rows))
        self.clear()
        rows[0]['due_date'], rows[1]['due_date'] = '2026-10-18', '2026-10-20'
        data = filled_template(rows)
        self.s.import_preview(self.owner, self.p['id'], 'synthetic.xlsx', data)
        self.assertEqual(self.notices(self.chair), [])
        self.s.import_commit(self.owner, self.p['id'], 'synthetic.xlsx', data)
        self.assertRecipients('project_finish_extended', '2026-10-12', '2026-10-20')
        self.assertEqual(len(self.notices(self.chair, 'task_updated')), 2)
        self.clear()
        self.s.import_commit(self.owner, self.p['id'], 'synthetic.xlsx', data)
        self.assertEqual(self.notices(self.chair), [])

    def test_new_task_and_undated_finish_fallback_extend_existing_project_range(self):
        self.task()
        self.clear()
        task = self.task('New work', '2026-10-14')
        self.assertRecipients('project_finish_extended', '2026-10-10', '2026-10-14')
        self.clear()
        self.s.update_task(self.owner, task['id'], dict(start_date='2026-10-18', due_date=None,
            expected_revision=task['revision'], reason='No finish yet', confirmed=True))
        self.assertRecipients('project_finish_extended', '2026-10-14', '2026-10-18')
        self.assertEqual(self.notices(self.chair, 'task_updated'), [])


class DeadlineNotificationHttpTests(unittest.TestCase):
    setUp = test_web.AstraWebTests.setUp
    tearDown = test_web.AstraWebTests.tearDown
    request = test_web.AstraWebTests.request

    def login(self, email, password):
        response, data = self.request('POST', '/api/login', dict(email=email, password=password))
        self.assertEqual(response.status, 200)
        return response.getheader('Set-Cookie').split(';', 1)[0], data['csrf']

    def test_http_inboxes_are_private_and_chairman_cannot_change_deadlines(self):
        s = self.server.service
        owner = s.user_by_email('owner@example.org')
        chair = s.create_user(owner, 'chair@example.org', 'Chairman', 'synthetic password', 'chairman')
        member = s.create_user(owner, 'member@example.org', 'Member', 'synthetic password')
        deputy = s.create_user(owner, 'deputy@example.org', 'Deputy', 'synthetic password')
        deputy = s.grant_secondary_owner(owner, deputy['id'], 'Cover')
        p = s.create_project(owner, 'School')
        task = s.create_task(owner, dict(project_id=p['id'], title='Prepare', due_date='2026-10-10'))
        s.db.execute('DELETE FROM notifications')
        owner_cookie, owner_csrf = self.login('owner@example.org', 'correct horse battery')
        response, _ = self.request('POST', '/api/tasks/' + task['id'], dict(due_date='2026-10-14',
            expected_revision=task['revision'], confirmed=True, reason='Extend'), cookie=owner_cookie, csrf=owner_csrf)
        self.assertEqual(response.status, 200)
        for actor in (chair, deputy, member):
            cookie, csrf = self.login(actor['email'], 'synthetic password')
            response, data = self.request('GET', '/api/notifications', cookie=cookie)
            self.assertEqual(response.status, 200)
            notes = data['notifications']
            self.assertEqual(len(notes), 0 if actor == member else 2)
            self.assertTrue(all(n['user_id'] == actor['id'] for n in notes))
            response, _ = self.request('POST', '/api/notifications/' + s.list_notifications(owner)[0]['id'] + '/read', {}, cookie=cookie, csrf=csrf)
            self.assertEqual(response.status, 403)
        cookie, csrf = self.login(chair['email'], 'synthetic password')
        response, _ = self.request('POST', '/api/tasks/' + task['id'], dict(due_date='2026-10-20',
            expected_revision=1, reason='Not authorized'), cookie=cookie, csrf=csrf)
        self.assertEqual(response.status, 403)


if __name__ == '__main__':
    unittest.main()
