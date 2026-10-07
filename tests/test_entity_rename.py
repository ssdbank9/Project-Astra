import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra.db import connect
from astra.service import AstraService, Forbidden
import test_web as web_fixture


class EntityRenameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect(Path(self.temp.name) / 'test.sqlite3')
        self.addCleanup(self.db.close)
        self.service = AstraService(self.db)
        self.owner = self.service.create_initial_owner('owner@example.org', 'Owner', 'synthetic password')
        self.entity = self.service.create_entity(self.owner, 'Original')

    def events(self):
        return [e for e in self.service.list_user_events(self.owner) if e['event_type'] == 'entity_renamed']

    def test_rename_preserves_links_primary_and_inactive_state_with_audit(self):
        project = self.service.create_project(self.owner, 'Example')
        self.service.set_project_entities(self.owner, project['id'], [self.entity['id']])
        self.service.set_primary_entity(self.owner, project['id'], self.entity['id'])
        self.service.set_entity_active(self.owner, self.entity['id'], False)
        renamed = self.service.rename_entity(self.owner, self.entity['id'], '  Colleges & Schools  ')
        self.assertEqual(renamed['id'], self.entity['id'])
        self.assertEqual(renamed['active'], 0)
        self.assertEqual(renamed['name'], 'Colleges & Schools')
        self.assertEqual(self.service.list_project_entities(self.owner, project['id'])[0]['id'], self.entity['id'])
        self.assertEqual(self.db.execute('SELECT primary_entity_id FROM projects WHERE id=?', (project['id'],)).fetchone()[0], self.entity['id'])
        event, = self.events()
        detail = json.loads(event['detail_json'])
        self.assertEqual(detail['before']['name'], 'Original')
        self.assertEqual(detail['after']['name'], 'Colleges & Schools')
        self.assertEqual(event['actor_user_id'], self.owner['id'])

    def test_invalid_and_duplicate_names_do_not_write(self):
        self.service.create_entity(self.owner, 'Another')
        for name in ['', '   ', None, 4, [], {}, 'bad\nname', 'bad\x00name', 'ANOTHER']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.service.rename_entity(self.owner, self.entity['id'], name)
        self.assertEqual(self.service.get_entity(self.entity['id'])['name'], 'Original')
        self.assertEqual(self.events(), [])
        with self.assertRaises(KeyError):
            self.service.rename_entity(self.owner, 'missing', 'New')

    def test_noop_does_not_audit_and_audit_failure_rolls_back(self):
        self.service.rename_entity(self.owner, self.entity['id'], 'Original')
        self.assertEqual(self.events(), [])
        with patch.object(self.service, '_app_setting_event', side_effect=RuntimeError('audit failed')):
            with self.assertRaises(RuntimeError):
                self.service.rename_entity(self.owner, self.entity['id'], 'Changed')
        self.assertEqual(self.service.get_entity(self.entity['id'])['name'], 'Original')

    def test_primary_secondary_only_and_inactive_owner_refused(self):
        project = self.service.create_project(self.owner, 'Example')
        member = self.service.create_user(self.owner, 'member@example.org', 'Member', 'synthetic password')
        chairman = self.service.create_user(self.owner, 'chair@example.org', 'Chair', 'synthetic password', 'chairman')
        for role in ['manager', 'member', 'viewer']:
            self.service.grant_project_access(self.owner, project['id'], member['id'], role)
            with self.subTest(role=role), self.assertRaises(Forbidden):
                self.service.rename_entity(member, self.entity['id'], 'Forbidden')
        with self.assertRaises(Forbidden):
            self.service.rename_entity(chairman, self.entity['id'], 'Forbidden')
        secondary = self.service.grant_secondary_owner(self.owner, member['id'], 'Synthetic owner test')
        self.service.rename_entity(secondary, self.entity['id'], 'Secondary edit')
        with self.assertRaises(Forbidden):
            self.service.rename_entity({**secondary, 'active': 0}, self.entity['id'], 'Forbidden')
        self.assertEqual(self.service.get_entity(self.entity['id'])['name'], 'Secondary edit')


class EntityRenameHttpTests(unittest.TestCase):
    setUp = web_fixture.AstraWebTests.setUp
    tearDown = web_fixture.AstraWebTests.tearDown
    request = web_fixture.AstraWebTests.request

    def login(self, email):
        response, data = self.request('POST', '/api/login', {'email':email, 'password':'correct horse battery'})
        self.assertEqual(response.status, 200)
        return response.getheader('Set-Cookie').split(';',1)[0], data['csrf']

    def test_http_owner_validation_csrf_and_stable_id(self):
        cookie, csrf = self.login('owner@example.org')
        response, data = self.request('POST','/api/entities',{'name':'Original'},cookie=cookie,csrf=csrf)
        self.assertEqual(response.status,201)
        entity_id = data['entity']['id']
        url = '/api/entities/'+entity_id+'/rename'
        response, _ = self.request('POST',url,{'name':'Unprotected'},cookie=cookie)
        self.assertEqual(response.status,403)
        for name in [None,[],{},' ','bad\nname']:
            response, _ = self.request('POST',url,{'name':name},cookie=cookie,csrf=csrf)
            self.assertEqual(response.status,400)
        response, _ = self.request('POST','/api/entities/missing/rename',{'name':'New'},cookie=cookie,csrf=csrf)
        self.assertEqual(response.status,404)
        response, data = self.request('POST',url,{'name':'<Colleges> & Schools'},cookie=cookie,csrf=csrf)
        self.assertEqual(response.status,200)
        self.assertEqual(data['entity']['id'],entity_id)
        self.assertEqual(data['entity']['name'],'<Colleges> & Schools')

    def test_http_role_matrix(self):
        cookie, csrf = self.login('owner@example.org')
        _, data = self.request('POST','/api/entities',{'name':'Original'},cookie=cookie,csrf=csrf)
        entity_id = data['entity']['id']
        service = self.server.service
        owner = dict(service.db.execute("SELECT * FROM users WHERE email='owner@example.org'").fetchone())
        project = service.create_project(owner,'Example')
        for role in ['chairman','manager','member','viewer','secondary']:
            user = service.create_user(owner,role+'@example.org',role,'correct horse battery','chairman' if role=='chairman' else 'member')
            if role in ['manager','member','viewer']:
                service.grant_project_access(owner,project['id'],user['id'],role)
            if role == 'secondary':
                service.grant_secondary_owner(owner,user['id'],'Synthetic test')
            user_cookie, user_csrf = self.login(user['email'])
            response, _ = self.request('POST','/api/entities/'+entity_id+'/rename',{'name':role},cookie=user_cookie,csrf=user_csrf)
            self.assertEqual(response.status,200 if role=='secondary' else 403,role)
        self.assertEqual(service.get_entity(entity_id)['name'],'secondary')
