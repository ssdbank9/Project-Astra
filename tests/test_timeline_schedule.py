import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra.db import connect
from astra.service import AstraService, Conflict, Forbidden, TaskLocked
import test_web as web_fixture


class TimelineScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect(Path(self.temp.name) / 'test.sqlite3')
        self.addCleanup(self.db.close)
        self.s = AstraService(self.db)
        self.owner = self.s.create_initial_owner('owner@example.org', 'Owner', 'synthetic password')
        self.p = self.s.create_project(self.owner, 'School')

    def task(self, title, start, finish, **extra):
        plan = extra.pop('plan_option', 'Shared')
        task = self.s.create_task(self.owner, dict(project_id=self.p['id'], title=title,
            start_date=start, due_date=finish, **extra))
        if plan != 'Shared':
            self.db.execute('UPDATE tasks SET import_extras=? WHERE id=?', (json.dumps({'x_plan':plan}),task['id']))
        return self.s.get_task(self.owner,task['id'])

    def payload(self, task, target=None, mode='date', **extra):
        return dict(mode=mode, expected_revision=task['revision'],
            **(dict(target_task_id=target['id'], target_revision=target['revision']) if target else {}), **extra)

    def preview(self, task, payload, actor=None):
        return self.s.timeline_schedule_preview(actor or self.owner, task['id'], payload)

    def apply(self, task, payload, actor=None):
        plan = self.preview(task, payload, actor)
        return self.s.timeline_schedule_apply(actor or self.owner, task['id'],
            dict(payload, fingerprint=plan['fingerprint'], confirmed=True))

    def test_preview_is_read_only_and_chain_preserves_gap_duration_owner_baseline(self):
        person = self.s.create_user(self.owner, 'person@example.org', 'Person', 'synthetic password')
        self.s.grant_project_access(self.owner, self.p['id'], person['id'], 'member')
        a = self.task('A', '2026-10-01', '2026-10-03')
        b = self.task('B', '2026-10-05', '2026-10-07', owner_user_id=person['id'])
        c = self.task('C', '2026-10-08', '2026-10-09')
        other = self.task('Independent', '2026-10-01', '2026-10-02')
        self.s.add_task_dependency(self.owner, a['id'], b['id'])
        self.s.add_task_dependency(self.owner, b['id'], c['id'])
        original = self.s.get_task(self.owner, b['id'])
        payload = self.payload(a, start_date='2026-10-04', due_date='2026-10-06')
        count = self.db.total_changes
        preview = self.preview(a, payload)
        self.assertEqual(self.db.total_changes, count)
        self.assertEqual(len(preview['changes']), 3)
        self.apply(a, payload)
        bnow = self.s.get_task(self.owner, b['id'])
        self.assertEqual((bnow['start_date'], bnow['due_date']), ('2026-10-08', '2026-10-10'))
        self.assertEqual(self.s.get_task(self.owner, c['id'])['due_date'], '2026-10-12')
        self.assertEqual(bnow['owner_user_id'], person['id'])
        for key in ('baseline_start_date', 'baseline_due_date'):
            self.assertEqual(bnow[key], original[key])
        self.assertEqual(self.s.get_task(self.owner, other['id'])['due_date'], '2026-10-02')
        self.assertEqual(self.s.get_project(self.owner, self.p['id'])['schedule_forecasts']['Shared']['finish_date'], '2026-10-12')

    def test_below_creates_link_moves_chain_and_deadline_is_explicit(self):
        a = self.task('A', '2026-10-01', '2026-10-03')
        b = self.task('B', '2026-10-01', '2026-10-02')
        c = self.task('C', '2026-10-03', '2026-10-04')
        self.s.add_task_dependency(self.owner, b['id'], c['id'])
        self.s.set_project_schedule(self.owner, self.p['id'], '2026-10-01', '2026-10-05', 'agreed')
        payload = self.payload(b, a, 'below', order_event_id=None,
            initial_task_order=[a['id'], b['id'], c['id']])
        self.apply(b, payload)
        self.assertEqual(self.s.get_task(self.owner, c['id'])['due_date'], '2026-10-07')
        self.assertEqual(self.s.get_project(self.owner, self.p['id'])['target_date'], '2026-10-05')
        a = self.s.get_task(self.owner, a['id'])
        self.apply(a, self.payload(a, start_date='2026-10-02', due_date='2026-10-04', update_deadline=True))
        self.assertEqual(self.s.get_project(self.owner, self.p['id'])['target_date'], '2026-10-08')

    def test_stale_descendant_or_project_refuses_entire_commit(self):
        a = self.task('A', '2026-10-01', '2026-10-03')
        b = self.task('B', '2026-10-04', '2026-10-05')
        self.s.add_task_dependency(self.owner, a['id'], b['id'])
        payload = self.payload(a, start_date='2026-10-02', due_date='2026-10-04')
        preview = self.preview(a, payload)
        self.s.update_task(self.owner, b['id'], {'title': 'Changed', 'expected_revision': b['revision']})
        with self.assertRaises(Conflict):
            self.s.timeline_schedule_apply(self.owner, a['id'], dict(payload, fingerprint=preview['fingerprint'], confirmed=True))
        self.assertEqual(self.s.get_task(self.owner, a['id'])['due_date'], '2026-10-03')

    def test_fork_join_uses_latest_predecessor_and_moves_earlier_too(self):
        a = self.task('A', '2026-10-01', '2026-10-03')
        b = self.task('B', '2026-10-04', '2026-10-06')
        c = self.task('C', '2026-10-04', '2026-10-05')
        d = self.task('Join', '2026-10-07', '2026-10-08')
        for pred, succ in ((a,b), (a,c), (b,d), (c,d)):
            self.s.add_task_dependency(self.owner, pred['id'], succ['id'])
        self.apply(a, self.payload(a, start_date='2026-10-04', due_date='2026-10-06'))
        self.assertEqual(self.s.get_task(self.owner, d['id'])['start_date'], '2026-10-10')
        a = self.s.get_task(self.owner, a['id'])
        self.apply(a, self.payload(a, start_date='2026-10-02', due_date='2026-10-04'))
        self.assertEqual(self.s.get_task(self.owner, d['id'])['due_date'], '2026-10-09')

    def test_above_reverses_direct_link_and_keeps_unrelated_order_slots(self):
        a = self.task('A', '2026-10-01', '2026-10-03')
        b = self.task('B', '2026-10-04', '2026-10-05')
        other = self.task('Other', '2026-10-01', '2026-10-01')
        self.s.add_task_dependency(self.owner, a['id'], b['id'])
        payload = self.payload(b, a, 'above', order_event_id=None,
            initial_task_order=[other['id'], a['id'], b['id']])
        preview = self.preview(b, payload)
        self.assertEqual(preview['remove_links'], [(a['id'],b['id'])])
        self.assertEqual(preview['add_links'], [(b['id'],a['id'])])
        self.apply(b, payload)
        self.assertEqual(self.s.get_task(self.owner, a['id'])['start_date'], '2026-10-06')
        ranks = {t['id']: t['timeline_order'] for t in self.s.list_tasks(self.owner, self.p['id'])}
        self.assertEqual((ranks[other['id']], ranks[b['id']], ranks[a['id']]), (0,1,2))

    def test_indirect_cycle_and_parallel_chain_refused_without_writes(self):
        a = self.task('A', '2026-10-01', '2026-10-02')
        b = self.task('B', '2026-10-03', '2026-10-04')
        c = self.task('C', '2026-10-05', '2026-10-06')
        self.s.add_task_dependency(self.owner,a['id'],b['id'])
        self.s.add_task_dependency(self.owner,b['id'],c['id'])
        count = self.db.total_changes
        for mode in ('above','concurrent'):
            payload = self.payload(c,a,mode, order_event_id=None,
                initial_task_order=[a['id'],b['id'],c['id']])
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.preview(c,payload)
        self.assertEqual(self.db.total_changes,count)

    def test_concurrent_removes_link_and_moves_its_descendants(self):
        a = self.task('A', '2026-10-01', '2026-10-03')
        b = self.task('B', '2026-10-04', '2026-10-06')
        c = self.task('C', '2026-10-07', '2026-10-08')
        self.s.add_task_dependency(self.owner,a['id'],b['id'])
        self.s.add_task_dependency(self.owner,b['id'],c['id'])
        self.apply(b,self.payload(b,a,'concurrent'))
        self.assertEqual(self.s.get_task(self.owner,b['id'])['start_date'],'2026-10-01')
        self.assertEqual(self.s.get_task(self.owner,c['id'])['due_date'],'2026-10-05')
        self.assertEqual([tuple(r) for r in self.db.execute('SELECT predecessor_task_id,successor_task_id FROM task_dependencies')],[(b['id'],c['id'])])

    def test_roles_material_schedule_and_deadline_option(self):
        a = self.task('A', '2026-10-01', '2026-10-03')
        b = self.task('B', '2026-10-04', '2026-10-05')
        self.s.add_task_dependency(self.owner,a['id'],b['id'])
        person = self.s.create_user(self.owner,'person@example.org','Person','synthetic password')
        payload = self.payload(a,start_date='2026-10-02',due_date='2026-10-04')
        for role in ('member','viewer'):
            self.s.grant_project_access(self.owner,self.p['id'],person['id'],role)
            with self.subTest(role=role), self.assertRaises(Forbidden):
                self.preview(a,payload,person)
        self.s.grant_project_access(self.owner,self.p['id'],person['id'],'manager')
        plan = self.preview(a,payload,person)
        self.assertTrue(plan['requires_owner'])
        with self.assertRaises(Forbidden):
            self.s.timeline_schedule_apply(person,a['id'],dict(payload,fingerprint=plan['fingerprint'],confirmed=True))
        with self.assertRaises(Forbidden):
            self.preview(a,dict(payload,update_deadline=True),person)
        with self.assertRaises(Forbidden):
            self.preview(a,payload,dict(self.owner,active=0))
        chair=self.s.create_user(self.owner,'chair@example.org','Chair','synthetic password','chairman')
        with self.assertRaises(Forbidden): self.preview(a,payload,chair)
        # An ordinary independent single task still permits project management.
        independent=self.task('Independent','2026-10-01','2026-10-02')
        self.apply(independent,self.payload(independent,start_date='2026-10-02',due_date='2026-10-03'),person)

    def test_affected_descendant_lock_closed_task_and_closed_project(self):
        a = self.task('A', '2026-10-01', '2026-10-03')
        b = self.task('B', '2026-10-04', '2026-10-05')
        self.s.add_task_dependency(self.owner,a['id'],b['id'])
        payload=self.payload(a,start_date='2026-10-02',due_date='2026-10-04')
        plan=self.preview(a,payload)
        manager=self.s.create_user(self.owner,'m@example.org','Manager','synthetic password')
        self.s.grant_project_access(self.owner,self.p['id'],manager['id'],'manager')
        lease=self.s.acquire_task_lock(manager,b['id'],'edit')
        with self.assertRaises(TaskLocked):
            self.s.timeline_schedule_apply(self.owner,a['id'],dict(payload,fingerprint=plan['fingerprint'],confirmed=True))
        self.s.release_task_lock(manager,b['id'],lease['token'])
        self.db.execute("UPDATE tasks SET status='completed',revision=revision+1 WHERE id=?",(b['id'],))
        with self.assertRaises(ValueError): self.preview(a,payload)
        self.db.execute("UPDATE projects SET status='closed' WHERE id=?",(self.p['id'],))
        with self.assertRaises(Forbidden): self.preview(a,payload)

    def test_stale_deadline_link_and_task_list_each_invalidate_preview(self):
        a = self.task('A', '2026-10-01', '2026-10-03')
        b = self.task('B', '2026-10-04', '2026-10-05')
        payload=self.payload(a,start_date='2026-10-02',due_date='2026-10-04')
        mutations=[lambda:self.s.set_project_schedule(self.owner,self.p['id'],None,'2026-10-20','changed'),
                   lambda:self.s.add_task_dependency(self.owner,a['id'],b['id']),
                   lambda:self.task('Added','2026-10-09','2026-10-10')]
        for mutation in mutations:
            plan=self.preview(a,payload)
            mutation()
            with self.assertRaises(Conflict):
                self.s.timeline_schedule_apply(self.owner,a['id'],dict(payload,fingerprint=plan['fingerprint'],confirmed=True))
        self.assertEqual(self.s.get_task(self.owner,a['id'])['due_date'],'2026-10-03')

    def test_audit_failure_rolls_back_dates_links_deadline_and_notifications(self):
        a = self.task('A', '2026-10-01', '2026-10-03')
        b = self.task('B', '2026-10-01', '2026-10-02')
        payload=self.payload(b,a,'after',update_deadline=True)
        plan=self.preview(b,payload)
        before=self.db.execute('SELECT COUNT(*) FROM notifications').fetchone()[0]
        with patch.object(self.s,'_project_event',side_effect=RuntimeError('audit failed')):
            with self.assertRaises(RuntimeError):
                self.s.timeline_schedule_apply(self.owner,b['id'],dict(payload,fingerprint=plan['fingerprint'],confirmed=True))
        self.assertEqual(self.s.get_task(self.owner,b['id'])['due_date'],'2026-10-02')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM task_dependencies').fetchone()[0],0)
        self.assertIsNone(self.s.get_project(self.owner,self.p['id'])['target_date'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM notifications').fetchone()[0],before)

    def test_undated_descendant_and_incomplete_deadline_refused(self):
        a = self.task('A', '2026-10-01', '2026-10-03')
        b = self.task('Undated',None,None)
        payload=self.payload(a,start_date='2026-10-02',due_date='2026-10-04')
        self.preview(a,payload)
        with self.assertRaises(ValueError): self.preview(a,dict(payload,update_deadline=True))
        self.s.add_task_dependency(self.owner,a['id'],b['id'])
        with self.assertRaises(ValueError): self.preview(a,payload)

    def test_alternative_plans_keep_independent_forecasts_and_authority(self):
        shared=self.task('Shared','2026-10-01','2026-10-03')
        a=self.task('Plan A','2026-10-04','2026-10-05',plan_option='A')
        b=self.task('Plan B','2026-10-04','2026-10-09',plan_option='B')
        self.s.add_task_dependency(self.owner,shared['id'],a['id'])
        self.s.add_task_dependency(self.owner,shared['id'],b['id'])
        self.apply(a,self.payload(a,start_date='2026-10-05',due_date='2026-10-06'))
        self.assertEqual(self.s.get_task(self.owner,b['id'])['due_date'],'2026-10-09')
        f=self.s.get_project(self.owner,self.p['id'])['schedule_forecasts']
        self.assertEqual((f['A']['finish_date'],f['B']['finish_date']),('2026-10-06','2026-10-09'))
        a=self.s.get_task(self.owner,a['id'])
        with self.assertRaises(ValueError): self.preview(a,self.payload(a,b,'after'))
        with self.assertRaises(ValueError): self.preview(a,self.payload(a,shared,'above',order_event_id=None,
            initial_task_order=[shared['id'],a['id'],b['id']]))

    def test_confirmation_and_complete_order_are_required(self):
        a=self.task('A','2026-10-01','2026-10-03')
        b=self.task('B','2026-10-04','2026-10-05')
        payload=self.payload(b,a,'below',order_event_id=None,initial_task_order=[a['id'],b['id']])
        plan=self.preview(b,payload)
        with self.assertRaises(ValueError):
            self.s.timeline_schedule_apply(self.owner,b['id'],dict(payload,fingerprint=plan['fingerprint']))
        for order in ([a['id']],[a['id'],a['id']],[a['id'],b['id'],'foreign']):
            with self.subTest(order=order),self.assertRaises(Conflict):
                self.preview(b,dict(payload,initial_task_order=order))

    def test_preview_cannot_be_applied_to_a_different_source_task(self):
        a=self.task('A','2026-10-01','2026-10-03')
        b=self.task('B','2026-10-01','2026-10-03')
        payload=self.payload(a,start_date='2026-10-02',due_date='2026-10-04')
        plan=self.preview(a,payload)
        with self.assertRaises(Conflict):
            self.s.timeline_schedule_apply(self.owner,b['id'],dict(payload,fingerprint=plan['fingerprint'],confirmed=True))
        self.assertEqual(self.s.get_task(self.owner,b['id'])['due_date'],'2026-10-03')

    def test_shared_move_deadline_covers_latest_alternative_finish(self):
        shared=self.task('Shared','2026-10-01','2026-10-03')
        a=self.task('Plan A','2026-10-04','2026-10-05',plan_option='A')
        b=self.task('Plan B','2026-10-04','2026-10-09',plan_option='B')
        self.s.add_task_dependency(self.owner,shared['id'],a['id'])
        self.s.add_task_dependency(self.owner,shared['id'],b['id'])
        payload=self.payload(shared,start_date='2026-10-02',due_date='2026-10-04',update_deadline=True)
        plan=self.preview(shared,payload)
        self.assertEqual(plan['project']['new_deadline'],'2026-10-10')
        self.assertEqual(plan['forecasts']['A']['finish_date'],'2026-10-06')
        self.apply(shared,payload)
        self.assertEqual(self.s.get_project(self.owner,self.p['id'])['target_date'],'2026-10-10')


class TimelineScheduleHttpTests(unittest.TestCase):
    setUp=web_fixture.AstraWebTests.setUp
    tearDown=web_fixture.AstraWebTests.tearDown
    request=web_fixture.AstraWebTests.request

    def test_preview_apply_csrf_and_role_matrix_for_material_chain(self):
        s=self.server.service
        owner=dict(s.db.execute("SELECT * FROM users WHERE email='owner@example.org'").fetchone())
        for role in ('owner','secondary','manager','member','viewer','chairman'):
            with self.subTest(role=role):
                project=s.create_project(owner,role)
                a=s.create_task(owner,dict(project_id=project['id'],title='A',start_date='2026-10-01',due_date='2026-10-03'))
                b=s.create_task(owner,dict(project_id=project['id'],title='B',start_date='2026-10-04',due_date='2026-10-05'))
                s.add_task_dependency(owner,a['id'],b['id'])
                if role=='owner': user=owner
                else:
                    user=s.create_user(owner,role+'@example.org',role,'correct horse battery','chairman' if role=='chairman' else 'member')
                    if role=='secondary': user=s.grant_secondary_owner(owner,user['id'],'Synthetic fixture')
                    elif role!='chairman': s.grant_project_access(owner,project['id'],user['id'],role)
                response,login=self.request('POST','/api/login',dict(email=user['email'],password='correct horse battery'))
                cookie=response.getheader('Set-Cookie').split(';',1)[0];csrf=login['csrf']
                payload=dict(mode='date',expected_revision=a['revision'],start_date='2026-10-02',due_date='2026-10-04')
                prefix='/api/tasks/'+a['id']
                for suffix in ('/timeline-schedule-preview','/timeline-schedule'):
                    response,_=self.request('POST',prefix+suffix,payload,cookie=cookie)
                    self.assertEqual(response.status,403)
                response,plan=self.request('POST',prefix+'/timeline-schedule-preview',payload,cookie=cookie,csrf=csrf)
                allowed=role in ('owner','secondary','manager')
                self.assertEqual(response.status,200 if allowed else 403)
                commit=dict(payload,fingerprint=plan.get('fingerprint'),confirmed=True)
                response,_=self.request('POST',prefix+'/timeline-schedule',commit,cookie=cookie,csrf=csrf)
                self.assertEqual(response.status,200 if role in ('owner','secondary') else 403)
                expected='2026-10-06' if role in ('owner','secondary') else '2026-10-05'
                self.assertEqual(s.get_task(owner,b['id'])['due_date'],expected)
