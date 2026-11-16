"""Who may change the schedule from the Gantt, and the New Step sheet end to end.

The sheet posts to the same POST /api/tasks as every other task, with three fields the older forms did
not send: a list of predecessors, the milestone flag and the progress. So:

- service tests: who may create a step with predecessors (App Owner and the project's manager; never a
  member, a viewer or someone outside the project), what is stored and audited, and what is refused;
- HTTP tests: the same roles over the real server, with the session cookie and the CSRF token;
- UI tests: Node runs the real src/astra/static/app.js (same DOM stub as test_gantt_zoom.py) and checks
  what the sheet offers and exactly what it sends.

The chart's two other writes use endpoints that existed before it was rebuilt: moving or resizing a bar
(POST /api/tasks/{id}/reschedule) and adding or removing a dependency (POST / DELETE
/api/task-dependencies). ScheduleRoleServiceTests and ScheduleRoleHttpTests pin who may use them, role by
role, because the page only hides the controls; service.py is the check.
"""
import http.client
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from astra.db import connect
from astra.service import AstraService, Conflict, Forbidden, TaskLocked
from astra.web import AstraServer
from test_frontend_gaps_views import run_probe   # a function only: no test class is imported
from test_gantt_zoom import SETUP                # the shared probe prelude: no test class is imported
from test_web import STATIC

PASSWORD = 'fixture password safe'
P2, P4 = '22222222-2222-4222-8222-222222222222', '44444444-4444-4444-8444-444444444444'   # project ids for the sheet probe: a project route needs a real id


def people(service, owner, project_id):
    """One user per project role, plus someone with no access to the project."""
    made = {}
    for role in ('manager', 'member', 'viewer', 'outsider'):
        user = service.create_user(owner, f'step-{role}@example.org', role.title(), PASSWORD)
        if role != 'outsider':
            service.grant_project_access(owner, project_id, user['id'], role)
        made[role] = service.get_user(user['id'])
    return made


class _ServiceFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect(Path(self.temp.name) / 'steps.sqlite3')
        self.addCleanup(self.db.close)
        self.s = AstraService(self.db)
        self.owner = self.s.create_initial_owner('step-owner@example.org', 'Owner', PASSWORD)
        self.project = self.s.create_project(self.owner, 'Release plan')
        self.pid = self.project['id']
        self.people = people(self.s, self.owner, self.pid)
        self.a = self.s.create_task(self.owner, {'project_id': self.pid, 'title': 'Alpha', 'start_date': '2026-06-01', 'due_date': '2026-06-05'})
        self.b = self.s.create_task(self.owner, {'project_id': self.pid, 'title': 'Beta', 'start_date': '2026-06-08', 'due_date': '2026-06-12'})

    def step(self, **extra):
        return {'project_id': self.pid, 'title': 'Gamma', 'status': 'assigned', 'start_date': '2026-06-15', 'due_date': '2026-06-19', **extra}

    def edges(self):
        return sorted((r['predecessor_task_id'], r['successor_task_id'], r['dependency_type'])
                      for r in self.db.execute('SELECT * FROM task_dependencies'))

    def events(self, task_id, kind):
        return [json.loads(r['after_json']) for r in self.db.execute(
            'SELECT after_json FROM task_events WHERE task_id=? AND event_type=? ORDER BY rowid', (task_id, kind))]

    def snapshot(self):
        return tuple(self.db.iterdump())


class NewStepServiceTests(_ServiceFixture, unittest.TestCase):
    # ---- who may ---------------------------------------------------------------------------------
    def test_the_app_owner_and_the_projects_manager_create_a_step_with_its_predecessors(self):
        for actor in (self.owner, self.people['manager']):
            with self.subTest(role=actor['display_name']):
                task = self.s.create_task(actor, self.step(predecessor_task_ids=[self.a['id'], self.b['id']], progress=40))
                self.assertEqual((task['title'], task['status'], task['progress'], task['start_date'], task['due_date']),
                                 ('Gamma', 'assigned', 40, '2026-06-15', '2026-06-19'))
                self.assertEqual(sorted(e for e in self.edges() if e[1] == task['id']),
                                 sorted([(self.a['id'], task['id'], 'finish_to_start'), (self.b['id'], task['id'], 'finish_to_start')]))
                self.assertEqual(sorted(d['predecessor_task_id'] for d in self.s.get_task_dependencies(actor, task['id'])),
                                 sorted([self.a['id'], self.b['id']]))

    def test_a_member_a_viewer_and_an_outsider_are_refused_and_nothing_is_written(self):
        before = self.snapshot()
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role), self.assertRaises(Forbidden):
                self.s.create_task(self.people[role], self.step(predecessor_task_ids=[self.a['id']], is_milestone=True, progress=10))
        self.assertEqual(self.snapshot(), before)

    def test_a_member_is_refused_even_with_no_predecessor(self):
        before = self.snapshot()
        with self.assertRaises(Forbidden):
            self.s.create_task(self.people['member'], self.step())
        self.assertEqual(self.snapshot(), before)

    def test_a_manager_of_another_project_cannot_add_a_step_here_or_link_to_a_task_here(self):
        other = self.s.create_project(self.owner, 'Other plan')
        elsewhere = self.s.create_user(self.owner, 'step-elsewhere@example.org', 'Elsewhere', PASSWORD)
        self.s.grant_project_access(self.owner, other['id'], elsewhere['id'], 'manager')
        elsewhere = self.s.get_user(elsewhere['id'])
        before = self.snapshot()
        with self.assertRaises(Forbidden):
            self.s.create_task(elsewhere, self.step())
        # In their own project, a predecessor they may not see is refused as access (a missing one is "not found").
        with self.assertRaises(Forbidden):
            self.s.create_task(elsewhere, {'project_id': other['id'], 'title': 'Reach', 'predecessor_task_ids': [self.a['id']]})
        self.assertEqual(self.snapshot(), before)

    def test_a_closed_project_takes_no_new_step(self):
        self.s.close_project(self.owner, self.pid, 'Residual work documented', exceptional=True)
        before = self.snapshot()
        for actor in (self.owner, self.people['manager']):
            with self.subTest(role=actor['display_name']), self.assertRaises(Forbidden):
                self.s.create_task(actor, self.step(predecessor_task_ids=[self.a['id']]))
        self.assertEqual(self.snapshot(), before)

    # ---- what is stored and audited --------------------------------------------------------------
    def test_each_predecessor_is_one_finish_to_start_row_and_one_audit_event(self):
        task = self.s.create_task(self.people['manager'], self.step(predecessor_task_ids=[self.a['id'], self.b['id']]))
        self.assertEqual(self.events(task['id'], 'dependency_added'),
                         [{'predecessor_task_id': self.a['id'], 'dependency_type': 'finish_to_start'},
                          {'predecessor_task_id': self.b['id'], 'dependency_type': 'finish_to_start'}])
        self.assertEqual(len(self.events(task['id'], 'task_created')), 1)
        actors = {r['actor_user_id'] for r in self.db.execute('SELECT actor_user_id FROM task_events WHERE task_id=?', (task['id'],))}
        self.assertEqual(actors, {self.people['manager']['id']})

    def test_the_returned_task_already_lists_its_predecessors(self):
        task = self.s.create_task(self.owner, self.step(predecessor_task_ids=[self.a['id'], self.b['id']]))
        listed = next(t for t in self.s.list_tasks(self.owner) if t['id'] == task['id'])
        self.assertEqual(sorted(p['task_id'] for p in listed['predecessors']), sorted([self.a['id'], self.b['id']]))
        self.assertTrue(listed['is_blocked'])      # Alpha and Beta are not finished

    def test_the_single_predecessor_field_still_works_and_duplicates_collapse(self):
        task = self.s.create_task(self.owner, self.step(predecessor_task_id=self.a['id'],
                                                         predecessor_task_ids=[self.a['id'], self.b['id'], self.b['id']]))
        self.assertEqual([e[0] for e in self.edges() if e[1] == task['id']], sorted([self.a['id'], self.b['id']]))
        only = self.s.create_task(self.owner, self.step(title='Delta', predecessor_task_id=self.b['id']))
        self.assertEqual([e[0] for e in self.edges() if e[1] == only['id']], [self.b['id']])
        none = self.s.create_task(self.owner, self.step(title='Echo', predecessor_task_ids=[]))
        self.assertEqual([e for e in self.edges() if e[1] == none['id']], [])

    def test_a_milestone_is_stored_as_one_and_an_ordinary_step_is_not(self):
        flag = self.s.create_task(self.owner, {'project_id': self.pid, 'title': 'Launch', 'due_date': '2026-06-20', 'is_milestone': True})
        plain = self.s.create_task(self.owner, self.step(is_milestone=False))
        default = self.s.create_task(self.owner, self.step(title='Default'))
        rows = {r['id']: r['is_milestone'] for r in self.db.execute('SELECT id, is_milestone FROM tasks')}
        self.assertEqual((rows[flag['id']], rows[plain['id']], rows[default['id']]), (1, 0, 0))
        listed = {t['id']: t for t in self.s.list_tasks(self.owner)}
        self.assertTrue(listed[flag['id']]['is_milestone'])
        self.assertFalse(listed[plain['id']]['is_milestone'])

    def test_progress_is_stored_when_given_and_left_empty_when_not(self):
        given = self.s.create_task(self.owner, self.step(progress=65))
        blank = self.s.create_task(self.owner, self.step(title='Blank'))
        zero = self.s.create_task(self.owner, self.step(title='Zero', progress=0))
        self.assertEqual((given['progress'], blank['progress'], zero['progress']), (65, None, 0))

    def test_a_step_under_a_parent_task_keeps_its_parent_and_its_predecessors(self):
        child = self.s.create_task(self.people['manager'], self.step(parent_task_id=self.a['id'], predecessor_task_ids=[self.b['id']],
                                                                     start_date='2026-06-02', due_date='2026-06-03'))
        self.assertEqual(child['parent_task_id'], self.a['id'])
        self.assertEqual([e[0] for e in self.edges() if e[1] == child['id']], [self.b['id']])

    # ---- what is refused -------------------------------------------------------------------------
    def test_predecessors_must_be_a_list_of_task_ids(self):
        before = self.snapshot()
        for bad in (self.a['id'], [1], [''], [None], {'id': self.a['id']}, [[self.a['id']]], 7):
            with self.subTest(value=bad), self.assertRaisesRegex(ValueError, 'Predecessors must be a list of task ids'):
                self.s.create_task(self.owner, self.step(predecessor_task_ids=bad))
        self.assertEqual(self.snapshot(), before)

    def test_the_milestone_flag_must_be_true_or_false(self):
        before = self.snapshot()
        for bad in ('yes', 1, 0, 'true', None, []):
            with self.subTest(value=bad), self.assertRaisesRegex(ValueError, 'Milestone must be true or false'):
                self.s.create_task(self.owner, self.step(is_milestone=bad))
        self.assertEqual(self.snapshot(), before)

    def test_progress_outside_0_to_100_is_refused(self):
        before = self.snapshot()
        for bad in (-1, 101, 'lots'):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                self.s.create_task(self.owner, self.step(progress=bad))
        self.assertEqual(self.snapshot(), before)

    def test_a_predecessor_from_another_project_or_one_that_does_not_exist_is_refused(self):
        other = self.s.create_project(self.owner, 'Other plan')
        foreign = self.s.create_task(self.owner, {'project_id': other['id'], 'title': 'Foreign'})
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'A predecessor task must belong to the same project'):
            self.s.create_task(self.owner, self.step(predecessor_task_ids=[self.a['id'], foreign['id']]))
        with self.assertRaises(KeyError):
            self.s.create_task(self.owner, self.step(predecessor_task_ids=[self.a['id'], 'no-such-task']))
        self.assertEqual(self.snapshot(), before)    # the good first predecessor was not half written

    def test_a_step_cannot_depend_on_the_task_it_belongs_to_or_one_above_it(self):
        child = self.s.create_task(self.owner, self.step(title='Child', parent_task_id=self.a['id'], start_date='2026-06-02', due_date='2026-06-03'))
        before = self.snapshot()
        for parent, predecessors in ((self.a['id'], [self.a['id']]), (child['id'], [self.b['id'], child['id']]), (child['id'], [self.a['id']])):
            with self.subTest(parent=parent, predecessors=predecessors), self.assertRaisesRegex(ValueError, 'cannot depend on the task it belongs to'):
                self.s.create_task(self.people['manager'], self.step(title='Grandchild', parent_task_id=parent, predecessor_task_ids=predecessors))
        self.assertEqual(self.snapshot(), before)
        # A sibling under the same parent is fine.
        ok = self.s.create_task(self.owner, self.step(title='Sibling', parent_task_id=self.a['id'], predecessor_task_ids=[child['id']]))
        self.assertEqual([e[0] for e in self.edges() if e[1] == ok['id']], [child['id']])

    def test_a_predecessor_locked_by_someone_else_refuses_the_new_link(self):
        self.s.acquire_task_lock(self.owner, self.a['id'], 'edit')
        before = self.snapshot()
        with self.assertRaises(TaskLocked):
            self.s.create_task(self.people['manager'], self.step(predecessor_task_ids=[self.a['id']]))
        self.assertEqual(self.snapshot(), before)
        mine = self.s.create_task(self.owner, self.step(title='Holder', predecessor_task_ids=[self.a['id']]))   # the holder may
        self.assertEqual([e[0] for e in self.edges() if e[1] == mine['id']], [self.a['id']])

    def test_a_manager_still_cannot_create_a_step_in_a_status_reserved_for_owners(self):
        before = self.snapshot()
        with self.assertRaises(Forbidden):
            self.s.create_task(self.people['manager'], self.step(status='completed', predecessor_task_ids=[self.a['id']]))
        self.assertEqual(self.snapshot(), before)


class _HttpFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get('ASTRA_HOME')
        os.environ['ASTRA_HOME'] = self.temp.name
        self.server = AstraServer(('127.0.0.1', 0))
        self.s = self.server.service
        self.owner = self.s.create_initial_owner('step-owner@example.org', 'Owner', PASSWORD)
        self.project = self.s.create_project(self.owner, 'Release plan')
        self.pid = self.project['id']
        self.people = people(self.s, self.owner, self.pid)
        self.a = self.s.create_task(self.owner, {'project_id': self.pid, 'title': 'Alpha', 'due_date': '2026-06-05'})
        self.b = self.s.create_task(self.owner, {'project_id': self.pid, 'title': 'Beta', 'due_date': '2026-06-12'})
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

    def request(self, method, path, payload, auth=None, csrf=True):
        headers = {'Content-Type': 'application/json'}
        if auth:
            headers['Cookie'] = auth[0]
            if csrf:
                headers['X-CSRF-Token'] = auth[1]
        self.connection.request(method, path, json.dumps(payload).encode(), headers)
        response = self.connection.getresponse()
        return response, json.loads(response.read())

    def login(self, email):
        response, body = self.request('POST', '/api/login', {'email': email, 'password': PASSWORD})
        self.assertEqual(response.status, 200)
        if body['user'].get('must_change_password'):
            # New accounts must change their password first; these cases are about an established user.
            self.s.db.execute('UPDATE users SET must_change_password=0 WHERE id=?', (body['user']['id'],))
        return response.getheader('Set-Cookie').split(';', 1)[0], body['csrf']

    def step(self, **extra):
        return {'project_id': self.pid, 'title': 'Gamma', 'status': 'assigned', 'start_date': '2026-06-15', 'due_date': '2026-06-19',
                'predecessor_task_ids': [self.a['id'], self.b['id']], 'is_milestone': False, 'progress': 30, **extra}

    def counts(self):
        return (self.s.db.execute('SELECT count(*) FROM tasks').fetchone()[0],
                self.s.db.execute('SELECT count(*) FROM task_dependencies').fetchone()[0])


class NewStepHttpTests(_HttpFixture, unittest.TestCase):
    def test_the_owner_and_the_manager_create_a_step_with_predecessors_over_http(self):
        for email in ('step-owner@example.org', 'step-manager@example.org'):
            with self.subTest(email=email):
                tasks, edges = self.counts()
                response, body = self.request('POST', '/api/tasks', self.step(), self.login(email))
                self.assertEqual(response.status, 201, body)
                self.assertEqual((body['task']['title'], body['task']['progress']), ('Gamma', 30))
                self.assertEqual(self.counts(), (tasks + 1, edges + 2))
                rows = self.s.db.execute('SELECT predecessor_task_id FROM task_dependencies WHERE successor_task_id=?', (body['task']['id'],))
                self.assertEqual(sorted(r[0] for r in rows), sorted([self.a['id'], self.b['id']]))

    def test_a_milestone_created_over_http_comes_back_as_one_in_the_task_list(self):
        auth = self.login('step-manager@example.org')
        response, body = self.request('POST', '/api/tasks', {'project_id': self.pid, 'title': 'Launch', 'status': 'assigned', 'due_date': '2026-06-20',
                                                             'is_milestone': True, 'predecessor_task_ids': [self.b['id']]}, auth)
        self.assertEqual(response.status, 201, body)
        response, listing = self.request('GET', '/api/tasks', {}, auth)
        self.assertEqual(response.status, 200)
        launch = next(t for t in listing['tasks'] if t['id'] == body['task']['id'])
        self.assertTrue(launch['is_milestone'])
        self.assertEqual([p['task_id'] for p in launch['predecessors']], [self.b['id']])

    def test_a_member_a_viewer_and_an_outsider_get_403_and_nothing_is_written(self):
        before = self.counts()
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role):
                response, body = self.request('POST', '/api/tasks', self.step(), self.login(f'step-{role}@example.org'))
                self.assertEqual(response.status, 403, body)
        self.assertEqual(self.counts(), before)

    def test_no_session_or_no_csrf_token_is_refused(self):
        before = self.counts()
        response, _ = self.request('POST', '/api/tasks', self.step())
        self.assertIn(response.status, (401, 403))
        response, _ = self.request('POST', '/api/tasks', self.step(), self.login('step-manager@example.org'), csrf=False)
        self.assertEqual(response.status, 403)
        self.assertEqual(self.counts(), before)

    def test_bad_predecessors_or_a_bad_milestone_flag_get_400_and_nothing_is_written(self):
        auth = self.login('step-manager@example.org')
        before = self.counts()
        for extra in ({'predecessor_task_ids': self.a['id']}, {'predecessor_task_ids': [5]}, {'is_milestone': 'yes'}, {'progress': 400}):
            with self.subTest(extra=extra):
                response, body = self.request('POST', '/api/tasks', self.step(**extra), auth)
                self.assertEqual(response.status, 400, body)
        self.assertEqual(self.counts(), before)

    def test_a_predecessor_in_another_project_gets_400_and_nothing_is_written(self):
        other = self.s.create_project(self.owner, 'Other plan')
        foreign = self.s.create_task(self.owner, {'project_id': other['id'], 'title': 'Foreign'})
        before = self.counts()
        response, body = self.request('POST', '/api/tasks', self.step(predecessor_task_ids=[foreign['id']]), self.login('step-owner@example.org'))
        self.assertEqual(response.status, 400, body)
        self.assertEqual(self.counts(), before)


class ScheduleRoleServiceTests(_ServiceFixture, unittest.TestCase):
    """Moving a bar and changing a dependency: App Owner and the project's manager only."""

    def dates(self, task_id):
        row = self.db.execute('SELECT start_date, due_date FROM tasks WHERE id=?', (task_id,)).fetchone()
        return row['start_date'], row['due_date']

    def move(self, actor, task_id, start, due):
        revision = self.db.execute('SELECT revision FROM tasks WHERE id=?', (task_id,)).fetchone()[0]
        return self.s.reschedule_task(actor, task_id, {'start_date': start, 'due_date': due, 'expected_revision': revision})

    def test_the_owner_and_the_manager_move_a_bar(self):
        self.move(self.owner, self.a['id'], '2026-06-02', '2026-06-06')
        self.assertEqual(self.dates(self.a['id']), ('2026-06-02', '2026-06-06'))
        self.move(self.people['manager'], self.b['id'], '2026-06-09', '2026-06-12')    # the start grip
        self.assertEqual(self.dates(self.b['id']), ('2026-06-09', '2026-06-12'))

    def test_a_member_a_viewer_and_an_outsider_cannot_move_a_bar(self):
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role), self.assertRaises(Forbidden):
                self.move(self.people[role], self.a['id'], '2026-06-02', '2026-06-06')
        self.assertEqual(self.dates(self.a['id']), ('2026-06-01', '2026-06-05'))
        self.assertEqual(self.db.execute("SELECT count(*) FROM task_events WHERE event_type='task_updated' AND task_id=?",
                                         (self.a['id'],)).fetchone()[0], 0)

    def test_a_move_from_a_stale_page_is_refused(self):
        with self.assertRaises(Conflict):
            self.s.reschedule_task(self.people['manager'], self.a['id'],
                                   {'start_date': '2026-06-02', 'due_date': '2026-06-06', 'expected_revision': 99})
        self.assertEqual(self.dates(self.a['id']), ('2026-06-01', '2026-06-05'))

    def test_the_owner_and_the_manager_add_and_remove_a_dependency(self):
        self.s.add_task_dependency(self.owner, self.a['id'], self.b['id'], 'finish_to_start')
        self.assertEqual(self.edges(), [(self.a['id'], self.b['id'], 'finish_to_start')])
        self.s.remove_task_dependency(self.people['manager'], self.a['id'], self.b['id'], 'Not needed any more')
        self.assertEqual(self.edges(), [])
        self.s.add_task_dependency(self.people['manager'], self.a['id'], self.b['id'], 'finish_to_start')
        self.assertEqual(self.edges(), [(self.a['id'], self.b['id'], 'finish_to_start')])

    def test_a_member_a_viewer_and_an_outsider_cannot_add_or_remove_a_dependency(self):
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role, action='add'), self.assertRaises(Forbidden):
                self.s.add_task_dependency(self.people[role], self.a['id'], self.b['id'], 'finish_to_start')
        self.assertEqual(self.edges(), [])
        self.s.add_task_dependency(self.owner, self.a['id'], self.b['id'], 'finish_to_start')
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role, action='remove'), self.assertRaises(Forbidden):
                self.s.remove_task_dependency(self.people[role], self.a['id'], self.b['id'], 'Trying')
        self.assertEqual(self.edges(), [(self.a['id'], self.b['id'], 'finish_to_start')])


class ScheduleRoleHttpTests(_HttpFixture, unittest.TestCase):
    """The same rules over the real server."""

    def dates(self, task_id):
        row = self.s.db.execute('SELECT start_date, due_date FROM tasks WHERE id=?', (task_id,)).fetchone()
        return row['start_date'], row['due_date']

    def move(self, email, task_id):
        revision = self.s.db.execute('SELECT revision FROM tasks WHERE id=?', (task_id,)).fetchone()[0]
        return self.request('POST', f'/api/tasks/{task_id}/reschedule',
                            {'start_date': '2026-06-02', 'due_date': '2026-06-06', 'expected_revision': revision}, self.login(email))

    def test_the_manager_moves_a_bar_over_http_and_the_others_get_403(self):
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role):
                response, body = self.move(f'step-{role}@example.org', self.a['id'])
                self.assertEqual(response.status, 403, body)
        self.assertEqual(self.dates(self.a['id']), (None, '2026-06-05'))
        response, body = self.move('step-manager@example.org', self.a['id'])
        self.assertEqual(response.status, 200, body)
        self.assertEqual(self.dates(self.a['id']), ('2026-06-02', '2026-06-06'))

    def test_the_manager_changes_a_dependency_over_http_and_the_others_get_403(self):
        link = {'predecessor_task_id': self.a['id'], 'successor_task_id': self.b['id']}
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role, action='add'):
                response, body = self.request('POST', '/api/task-dependencies', link, self.login(f'step-{role}@example.org'))
                self.assertEqual(response.status, 403, body)
        self.assertEqual(self.counts()[1], 0)
        response, body = self.request('POST', '/api/task-dependencies', link, self.login('step-manager@example.org'))
        self.assertIn(response.status, (200, 201), body)
        self.assertEqual(self.counts()[1], 1)
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role, action='remove'):
                response, body = self.request('DELETE', '/api/task-dependencies', {**link, 'reason': 'Trying'}, self.login(f'step-{role}@example.org'))
                self.assertEqual(response.status, 403, body)
        self.assertEqual(self.counts()[1], 1)
        response, body = self.request('DELETE', '/api/task-dependencies', {**link, 'reason': 'Not needed'}, self.login('step-manager@example.org'))
        self.assertEqual(response.status, 200, body)
        self.assertEqual(self.counts()[1], 0)


SHEET_PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={};
''' + SETUP + r'''
  const sheet=document.querySelector("#step-sheet"),form=document.querySelector("#step-form");
  form.closest=s=>s==="dialog"?sheet:null;sheet.close=()=>{sheet.open=false};
  const F=n=>document.querySelector(`#step-form [name="${n}"]`);
  const calls=[],toasts=[],people=[];let reply=p=>({task:{id:"new1",title:p.title}});
  api=async(path,opt)=>{
    if(path.startsWith("/api/assignable-users")){people.push(path.split("?")[1]);return {users:[{id:"u1",display_name:"Olive Owner"},{id:"u2",display_name:"Mo Member"}]}}
    const body=JSON.parse(opt.body);calls.push([path,opt.method,body]);return reply(body)};
  let loads=0;load=async()=>{loads++};
  showToast=(...a)=>{toasts.push(a[0])};
  const tasks=()=>[
    T("a","Alpha","2026-06-01","2026-06-05",{status:"completed",timeline_order:1}),
    T("par","Design","2026-06-08","2026-06-19",{timeline_order:2}),
    T("k1","Kid one","2026-06-08","2026-06-09",{parent_task_id:"par"}),
    T("old","Old phase","2026-05-01","2026-05-09",{status:"completed",timeline_order:3}),
    T("ok","Old kid","2026-05-01","2026-05-02",{parent_task_id:"old",status:"completed"}),
    T("x","Dropped","2026-06-10","2026-06-11",{status:"cancelled",timeline_order:4}),
    T("y","Other project task","2026-06-10","2026-06-11",{project_id:P2,project_name:"Second plan"}),
  ];
  // Project routes need real ids, so the two projects that get their own page have them.
  const P2="22222222-2222-4222-8222-222222222222",P4="44444444-4444-4444-8444-444444444444";
  const two=[{id:"pr1",name:"Release Plan",status:"active",can_manage:true},{id:P2,name:"Second plan",status:"active",can_manage:true},
    {id:"pr3",name:"Closed plan",status:"closed",can_manage:true},{id:P4,name:"Read only",status:"active",can_manage:false}];
  const options=()=>[...F("phase").innerHTML.matchAll(/<option value="([^"]*)">([^<]*)<\/option>/g)].map(m=>[m[1],m[2]]);
  const deps=()=>[...H.store["#step-deps"].innerHTML.matchAll(/name="dep" value="([^"]*)"><span class="gx-dep-name">([^<]*)<\/span><span class="gx-code">([^<]*)</g)].map(m=>[m[1],m[2],m[3]]);
  const tick=()=>new Promise(r=>setTimeout(r,60));
  const fill=v=>{for(const k of ["title","status","type","owner_user_id","progress","start_date","due_date","description"])F(k).value=v[k]??({status:"draft",type:"task"}[k]||"")};
  const check=ids=>{document.querySelectorAll('[name="dep"]').forEach(n=>{n.value=n.getAttribute("value");n.checked=ids.includes(n.value)})};
  const submit=async(value="default")=>{for(const f of form._l.submit||[])await f({preventDefault(){},target:form,submitter:{value}});await tick()};
  const change=name=>{for(const f of form._l.change||[])f({target:{name}})};

  // ---- opening ----
  boot(tasks(),{projects:two});
  H.store["#gantt-new-step"].onclick();
  out.open={shown:!!sheet.open,options:options(),toasts:toasts.slice()};
  F("phase").value="p:pr1";change("phase");await tick();
  out.project={deps:deps(),people:people.slice(-1)[0]};
  F("phase").value="t:par";change("phase");await tick();
  out.parent={deps:deps(),people:people.slice(-1)[0]};
  F("phase").value="p:"+P2;change("phase");await tick();
  out.second={deps:deps()};out.secondPeople=people.slice(-1)[0];
  F("type").value="milestone";change("type");
  out.milestone={endHidden:document.querySelector("#step-form [data-end-field]").hidden,label:document.querySelector("#step-form [data-start-label]").textContent};
  F("type").value="task";change("type");
  out.task={endHidden:document.querySelector("#step-form [data-end-field]").hidden,label:document.querySelector("#step-form [data-start-label]").textContent};

  // ---- creating a task under the project ----
  F("phase").value="p:pr1";change("phase");await tick();
  fill({title:"  Build it  ",status:"assigned",type:"task",owner_user_id:"u2",progress:"25",start_date:"2026-06-15",due_date:"2026-06-19",description:"Why"});
  check(["a","par"]);
  await submit();
  out.created={calls:calls.splice(0),open:!!sheet.open,loads,said:H.store["#gantt-live"].textContent,error:document.querySelector(".error").textContent};

  // ---- a double click on Create posts once ----
  sheet.open=true;let release;reply=p=>new Promise(r=>{release=()=>r({task:{id:"new3",title:p.title}})});
  fill({title:"Twice"});const first=submit(),second=submit();await tick();
  out.double={during:calls.length};release();await first;await second;await tick();
  out.double.total=calls.splice(0).length;out.double.open=!!sheet.open;
  // once it has settled, the next Create works again
  sheet.open=true;reply=p=>({task:{id:"new4",title:p.title}});fill({title:"After"});await submit();out.double.next=calls.splice(0).length;

  // ---- a reload that fails after the step was created is not shown in the closed sheet ----
  sheet.open=true;const realLoad=load;load=async()=>{throw new Error("offline")};toasts.length=0;
  fill({title:"Offline"});await submit();
  out.reloadFails={open:!!sheet.open,error:document.querySelector(".error").textContent,toasts:toasts.slice()};
  load=realLoad;calls.splice(0);

  // ---- a milestone under a parent task: one date, sent as the due date ----
  sheet.open=true;F("phase").value="t:par";change("phase");await tick();
  fill({title:"Sign-off",status:"draft",type:"milestone",progress:"",start_date:"2026-06-19",due_date:"2026-06-30"});
  check(["k1"]);
  await submit();
  out.flag={calls:calls.splice(0),open:!!sheet.open};

  // ---- nothing optional filled in ----
  sheet.open=true;F("phase").value="p:"+P2;change("phase");await tick();
  fill({title:"Bare"});check([]);
  await submit();
  out.bare={calls:calls.splice(0)};

  // ---- the server says no ----
  sheet.open=true;const before=loads;
  reply=()=>{throw Object.assign(new Error("Task-management access denied."),{status:403})};
  fill({title:"Refused"});await submit();
  out.refused={calls:calls.splice(0).length,open:!!sheet.open,error:document.querySelector(".error").textContent,loads:loads-before};
  reply=p=>({task:{id:"new2",title:p.title}});

  // ---- Discard ----
  fill({title:"Never mind"});document.querySelector("#step-discard").onclick();await tick();
  out.discard={calls:calls.splice(0).length,open:!!sheet.open};

  // ---- on a project page only that project is offered ----
  location.hash="#/project/"+P2+"/timeline";
  renderGantt(state.tasks);gxOpenSheet();out.projectPage={options:options(),newHidden:H.store["#gantt-new-step"].hidden};
  location.hash="#/project/"+P4+"/timeline";
  renderGantt(state.tasks);sheet.open=false;toasts.length=0;gxOpenSheet();
  out.readOnlyPage={newHidden:H.store["#gantt-new-step"].hidden,open:!!sheet.open,toasts:toasts.slice()};
  location.hash="";
  return out;
};
'''


@unittest.skipUnless(shutil.which('node'), 'Node required for actual frontend driver')
class NewStepSheetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(SHEET_PROBE, static=STATIC)

    def test_the_sheet_opens_and_offers_every_open_project_the_user_manages_and_its_open_phases(self):
        opened = self.out['open']
        self.assertTrue(opened['shown'])
        self.assertEqual(opened['toasts'], [])
        # Phases are numbered by date within the project: the finished "Old phase" of May is RP-01, "Design" RP-02.
        self.assertEqual(opened['options'], [['p:pr1', 'Release Plan'], ['t:par', 'Release Plan › Design (RP-02)'], ['p:' + P2, 'Second plan']])

    def test_a_closed_project_a_read_only_project_and_a_finished_phase_are_not_offered(self):
        values = [v for v, _ in self.out['open']['options']]
        self.assertNotIn('p:pr3', values)
        self.assertNotIn('p:' + P4, values)
        self.assertNotIn('t:old', values)

    def test_depends_on_lists_the_other_steps_of_the_chosen_project(self):
        self.assertEqual(self.out['project']['deps'], [['a', 'Alpha', 'RP'], ['par', 'Design', 'RP'], ['old', 'Old phase', 'RP'],
                                                       ['ok', 'Old kid', 'RP-01'], ['k1', 'Kid one', 'RP-02']])
        # Under a phase, the phase itself (and any phase above it) is not offered.
        self.assertEqual(self.out['parent']['deps'], [d for d in self.out['project']['deps'] if d[0] != 'par'])
        self.assertEqual(self.out['second']['deps'], [['y', 'Other project task', 'SP']])

    def test_a_cancelled_task_is_not_offered_as_a_predecessor(self):
        self.assertNotIn('x', [d[0] for d in self.out['project']['deps']])

    def test_the_owner_list_is_asked_for_the_chosen_project_and_for_a_task_or_a_sub_task(self):
        self.assertEqual(self.out['project']['people'], 'project_id=pr1&for=task')
        self.assertEqual(self.out['secondPeople'], f'project_id={P2}&for=task')
        self.assertEqual(self.out['parent']['people'], 'project_id=pr1&for=subtask')

    def test_a_milestone_has_one_date(self):
        self.assertEqual(self.out['milestone'], {'endHidden': True, 'label': 'Date'})
        self.assertEqual(self.out['task'], {'endHidden': False, 'label': 'Start'})

    def test_create_posts_one_task_with_its_predecessors(self):
        created = self.out['created']
        self.assertEqual(created['calls'], [['/api/tasks', 'POST', {
            'title': 'Build it', 'project_id': 'pr1', 'status': 'assigned', 'is_milestone': False, 'description': 'Why',
            'predecessor_task_ids': ['a', 'par'], 'owner_user_id': 'u2', 'start_date': '2026-06-15', 'due_date': '2026-06-19', 'progress': 25}]])
        self.assertFalse(created['open'])
        self.assertEqual(created['loads'], 1)
        self.assertEqual(created['said'], '“Build it” was added.')
        self.assertEqual(created['error'], '')

    def test_a_milestone_under_a_phase_sends_its_date_as_the_due_date_and_names_its_parent(self):
        self.assertEqual(self.out['flag']['calls'], [['/api/tasks', 'POST', {
            'title': 'Sign-off', 'project_id': 'pr1', 'status': 'draft', 'is_milestone': True, 'description': '',
            'predecessor_task_ids': ['k1'], 'parent_task_id': 'par', 'due_date': '2026-06-19'}]])

    def test_empty_optional_fields_are_left_out_of_the_request(self):
        self.assertEqual(self.out['bare']['calls'], [['/api/tasks', 'POST', {
            'title': 'Bare', 'project_id': P2, 'status': 'draft', 'is_milestone': False, 'description': '', 'predecessor_task_ids': []}]])

    def test_a_refusal_from_the_server_is_shown_in_the_sheet_which_stays_open(self):
        refused = self.out['refused']
        self.assertEqual((refused['calls'], refused['open'], refused['loads']), (1, True, 0))
        self.assertEqual(refused['error'], 'Task-management access denied.')

    def test_a_double_click_on_create_posts_once(self):
        self.assertEqual(self.out['double'], {'during': 1, 'total': 1, 'open': False, 'next': 1})

    def test_a_failed_reload_after_creating_is_a_toast_not_an_error_in_the_closed_sheet(self):
        failed = self.out['reloadFails']
        self.assertEqual((failed['open'], failed['error']), (False, ''))
        self.assertEqual(failed['toasts'], ['“Offline” was added, but the page could not reload: offline'])

    def test_discard_closes_the_sheet_and_sends_nothing(self):
        self.assertEqual(self.out['discard'], {'calls': 0, 'open': False})

    def test_on_a_project_page_only_that_project_is_offered(self):
        self.assertEqual(self.out['projectPage'], {'options': [['p:' + P2, 'Second plan']], 'newHidden': False})

    def test_someone_who_cannot_add_tasks_gets_no_button_and_no_sheet(self):
        page = self.out['readOnlyPage']
        self.assertTrue(page['newHidden'])
        self.assertFalse(page['open'])
        self.assertEqual(page['toasts'], ['You can add steps only to an open project you manage.'])


class NewStepMarkupTests(unittest.TestCase):
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    js = (STATIC / 'app.js').read_text(encoding='utf-8')

    def test_the_sheet_is_a_modal_dialog_named_by_its_heading(self):
        tag = __import__('re').search(r'<dialog id="step-sheet"[^>]*>', self.html).group(0)
        self.assertIn('aria-labelledby="step-sheet-title"', tag)
        self.assertIn('<h2 id="step-sheet-title">New Step</h2>', self.html)
        self.assertIn('document.querySelector("#step-sheet").showModal();', self.js)

    def test_the_sheet_has_the_fields_of_the_block(self):
        sheet = self.html[self.html.index('<dialog id="step-sheet"'):]
        sheet = sheet[:sheet.index('</dialog>')]
        for name in ('title', 'phase', 'type', 'owner_user_id', 'status', 'progress', 'start_date', 'due_date', 'description'):
            self.assertIn(f'name="{name}"', sheet)
        self.assertIn('<legend>Depends on</legend>', sheet)
        self.assertIn('<button type="button" class="quiet" id="step-discard">Discard</button><button value="default">Create</button>', sheet)
        # Enter in a field submits with the form's first submit button: that must be Create, never Discard.
        buttons = __import__('re').findall(r'<button[^>]*>', sheet)
        self.assertEqual([b for b in buttons if 'type="button"' not in b], ['<button value="default">'])
        self.assertIn('<div class="error" role="alert"></div>', sheet)
        self.assertNotIn('style=', sheet)

    def test_only_statuses_a_manager_may_create_are_offered(self):
        sheet = self.html[self.html.index('<dialog id="step-sheet"'):]
        select = sheet[sheet.index('name="status"'):]
        select = select[:select.index('</select>')]
        self.assertEqual(__import__('re').findall(r'<option value="(\w+)">', select), ['draft', 'assigned', 'in_progress', 'delayed'])

    def test_the_step_is_created_through_the_same_endpoint_as_every_other_task(self):
        self.assertIn('more=>api("/api/tasks",{method:"POST",body:JSON.stringify({...payload,...more})})', self.js)


if __name__ == '__main__':
    unittest.main()
