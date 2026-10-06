import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from astra import importer, workplan
from astra.db import connect
from astra.service import AstraService, Forbidden


class WorkplanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / 'test.sqlite3')
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.db.close)
        self.service = AstraService(self.db)
        self.owner = self.service.create_initial_owner('owner@example.org', 'Owner', 'synthetic password')
        self.project = self.service.create_project(self.owner, 'Example academy')

    def template(self):
        return self.service.import_template(self.owner, 'csv', self.project['id'], workplan_csv=True)[0]

    def file(self, rows):
        records = list(csv.reader(io.StringIO(self.template().decode('utf-8-sig'))))[:6]
        records.extend([[workplan.encode(row.get(key, '')) for key, _ in workplan.FIELDS] for row in rows])
        stream = io.StringIO()
        csv.writer(stream, lineterminator='\n').writerows(records)
        return stream.getvalue().encode('utf-8-sig')

    def preview(self, data):
        return self.service.import_preview(self.owner, self.project['id'], 'workplan.csv', data)

    def commit(self, data):
        preview = self.preview(data)
        return self.service.import_commit(self.owner, self.project['id'], 'workplan.csv', data, {}, preview['sha256'], preview['plan_fingerprint'])

    def tasks(self):
        return {t['import_key']: t for t in self.service.list_tasks(self.owner, self.project['id'])}

    def test_template_is_minimal_bound_and_spare_keys_are_ignored(self):
        data = self.template()
        records = list(csv.reader(io.StringIO(data.decode('utf-8-sig'))))
        self.assertEqual(records[1][1], self.project['id'])
        self.assertEqual(len(records[5]), 9)
        self.assertEqual(len(records), 56)
        self.assertEqual(len(workplan.parse(data).rows), 0)
        self.assertEqual(self.preview(data)['rows'], [])

    def test_fill_import_and_redownload_is_stable(self):
        data = self.file([
            {'import_key': 'T-001', 'title': '=Example', 'start_date': '2026-10-01', 'due_date': '2026-10-02'},
            {'import_key': 'T-002', 'title': "'Quoted", 'predecessors': 'T-001', 'x_plan': 'Private'},
            {'import_key': 'T-003', 'title': 'Charter work', 'parent_key': 'T-001', 'x_plan': 'Charter'},
        ])
        self.assertEqual(self.commit(data)['create'], 3)
        tasks = self.tasks()
        self.assertEqual(tasks['T-001']['title'], '=Example')
        self.assertEqual(tasks['T-002']['title'], "'Quoted")
        self.assertEqual(tasks['T-003']['plan_option'], 'Charter')
        self.assertEqual(self.commit(self.template())['create'], 0)
        self.assertEqual(len(self.tasks()), 3)

    def test_blank_key_generated_and_original_replay_refused(self):
        data = self.file([{'title': 'New work'}])
        self.assertEqual(self.commit(data)['create'], 1)
        self.assertTrue(next(iter(self.tasks())))
        with self.assertRaisesRegex(ValueError, 'fresh|updated|download'):
            self.commit(data)
        self.assertEqual(self.commit(self.template())['create'], 0)

    def test_wrong_project_rejected(self):
        other = self.service.create_project(self.owner, 'Other')
        with self.assertRaisesRegex(ValueError, 'another project'):
            self.service.import_preview(self.owner, other['id'], 'workplan.csv', self.template())

    def test_cross_plan_links_rejected_in_upload_and_native_actions(self):
        self.commit(self.file([{'import_key': 'P', 'title': 'Private', 'x_plan': 'Private'}, {'import_key': 'C', 'title': 'Charter', 'x_plan': 'Charter'}]))
        tasks = self.tasks()
        preview = self.preview(self.file([{'import_key': 'C', 'title': 'Charter', 'x_plan': 'Charter', 'predecessors': 'P'}]))
        self.assertIn('E_PLAN_LINK', [f['code'] for f in preview['rows'][0]['findings']])
        with self.assertRaises(ValueError):
            self.service.add_task_dependency(self.owner, tasks['P']['id'], tasks['C']['id'])
        with self.assertRaises(ValueError):
            self.service.set_parent(self.owner, tasks['C']['id'], tasks['P']['id'])
        with self.assertRaises(ValueError):
            self.service.create_task(self.owner, {'project_id': self.project['id'], 'title': 'Shared', 'parent_task_id': tasks['P']['id']})

    def test_plan_edit_checks_existing_outgoing_links(self):
        self.commit(self.file([{'import_key': 'S', 'title': 'Shared'}, {'import_key': 'C', 'title': 'Charter', 'x_plan': 'Charter', 'predecessors': 'S'}]))
        preview = self.preview(self.file([{'import_key': 'S', 'title': 'Shared', 'x_plan': 'Private'}]))
        self.assertIn('E_PLAN_LINK', [f['code'] for f in preview['rows'][0]['findings']])

    def test_critical_paths_calculated_for_each_alternative(self):
        rows = [
            {'import_key': 'S', 'title': 'Shared', 'start_date': '2026-10-01', 'due_date': '2026-10-02'},
            {'import_key': 'P', 'title': 'Private', 'x_plan': 'Private', 'predecessors': 'S', 'start_date': '2026-10-03', 'due_date': '2026-10-20'},
            {'import_key': 'C', 'title': 'Charter', 'x_plan': 'Charter', 'predecessors': 'S', 'start_date': '2026-10-03', 'due_date': '2026-10-04'},
        ]
        self.commit(self.file(rows))
        tasks = self.tasks()
        self.assertIn('Private', tasks['P']['critical_for_plans'])
        self.assertNotIn('Charter', tasks['P']['critical_for_plans'])
        self.assertIn('Charter', tasks['C']['critical_for_plans'])
        self.assertIn('Private', tasks['S']['critical_for_plans'])
        self.assertIn('Charter', tasks['S']['critical_for_plans'])

    def test_download_permissions(self):
        user = self.service.create_user(self.owner, 'member@example.org', 'Member', 'synthetic password', 'member')
        self.service.grant_project_access(self.owner, self.project['id'], user['id'], 'viewer')
        with self.assertRaises(Forbidden):
            self.service.import_template(user, 'csv', self.project['id'], workplan_csv=True)
        self.service.grant_project_access(self.owner, self.project['id'], user['id'], 'manager')
        self.assertTrue(self.service.import_template(user, 'csv', self.project['id'], workplan_csv=True)[0])

    def test_partial_import_rechecks_skipped_plan_changes(self):
        self.commit(self.file([
            {'import_key': 'S', 'title': 'Shared'},
            {'import_key': 'X', 'title': 'Charter prerequisite', 'x_plan': 'Charter'},
            {'import_key': 'C', 'title': 'Charter successor', 'x_plan': 'Charter', 'predecessors': 'S;X'},
        ]))
        data = self.file([{'import_key': 'S', 'title': 'Shared', 'x_plan': 'Private'}, {'import_key': 'C', 'title': 'Charter successor', 'x_plan': 'Private'}])
        preview = self.preview(data)
        self.assertEqual([row['action'] for row in preview['rows']], ['error', 'error'])
        with self.assertRaises(ValueError):
            self.service.import_commit(self.owner, self.project['id'], 'workplan.csv', data, {'valid_rows_only': True})
        self.assertEqual(self.tasks()['S']['plan_option'], 'Shared')
        self.assertEqual(self.tasks()['C']['plan_option'], 'Charter')

    def test_removed_identity_and_unknown_version_rejected(self):
        data = self.template().decode('utf-8-sig')
        with self.assertRaises(ValueError):
            self.preview(data.split('\n', 1)[1].encode('utf-8'))
        with self.assertRaises(ValueError):
            self.preview(data.replace('Astra Workplan CSV,1,', 'Astra Workplan CSV,2,').encode('utf-8'))

    def test_formula_guards_are_reversible(self):
        for value in ('=1', '+1', '-1', '@text', "'literal", ' \ttext', '\rtext', '  =1', 'normal'):
            self.assertEqual(workplan.decode(workplan.encode(value)), value)
        self.assertTrue(workplan.encode(' \ttext').startswith("'"))

    def test_plan_change_checks_unkeyed_successor_and_child(self):
        for link in ('predecessor_task_id', 'parent_task_id'):
            with self.subTest(link=link):
                key = 'PRED' if link == 'predecessor_task_id' else 'PARENT'
                self.commit(self.file([{'import_key': key, 'title': 'Shared'}]))
                data = self.file([{'import_key': key, 'title': 'Shared', 'x_plan': 'Private'}])
                task = self.tasks()[key]
                self.service.create_task(self.owner, {'project_id': self.project['id'], 'title': 'Native Shared task', link: task['id']})
                preview = self.preview(data)
                self.assertIn('E_PLAN_LINK', [f['code'] for f in preview['rows'][0]['findings']])

    def test_stripped_identity_rejected_for_excel_delimiters(self):
        records = list(csv.reader(io.StringIO(self.template().decode('utf-8-sig'))))[5:]
        for delimiter in (',', ';', '\t'):
            stream = io.StringIO()
            csv.writer(stream, delimiter=delimiter, quoting=csv.QUOTE_ALL).writerows(records)
            with self.assertRaises(ValueError):
                self.preview(stream.getvalue().encode('utf-8'))

    def test_quoted_intact_identity_and_legacy_line_endings(self):
        records = list(csv.reader(io.StringIO(self.template().decode('utf-8-sig'))))
        for delimiter in (',', ';', '\t'):
            stream = io.StringIO()
            csv.writer(stream, delimiter=delimiter, quoting=csv.QUOTE_ALL).writerows(records)
            self.assertEqual(self.preview(stream.getvalue().encode('utf-8'))['rows'], [])
        for newline in ('\r', '\n', '\r\n'):
            data = newline.join(['Import Key,Title', 'A,Normal', '']).encode('utf-8')
            self.assertEqual(importer.parse_upload('legacy.csv', data, self.service._import_config()).rows[0].cells['title'], 'Normal')

    def test_entity_binding_checked_at_preview_and_commit(self):
        entity = self.service.create_entity(self.owner, 'Entity one')
        self.service.set_project_entities(self.owner, self.project['id'], [entity['id']])
        data = self.file([{'import_key': 'E', 'title': 'Entity work'}])
        preview = self.preview(data)
        self.service.set_project_entities(self.owner, self.project['id'], [])
        with self.assertRaisesRegex(ValueError, 'entities changed'):
            self.preview(data)
        with self.assertRaisesRegex(ValueError, 'entities changed'):
            self.service.import_commit(self.owner, self.project['id'], 'workplan.csv', data, {}, preview['sha256'], preview['plan_fingerprint'])
        self.assertEqual(len(self.tasks()), 0)

    def test_separate_downloads_have_distinct_logged_new_keys(self):
        first = list(csv.reader(io.StringIO(self.template().decode('utf-8-sig'))))
        second = list(csv.reader(io.StringIO(self.template().decode('utf-8-sig'))))
        first_keys = {row[0] for row in first[6:]}
        second_keys = {row[0] for row in second[6:]}
        self.assertFalse(first_keys & second_keys)
        events = self.db.execute("SELECT detail_json FROM project_events WHERE event_type='workplan_keys_issued'").fetchall()
        self.assertEqual(len(events), 2)
        self.assertEqual(set(json.loads(events[0]['detail_json'])['keys']), first_keys)
