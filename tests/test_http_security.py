"""B1 security regressions using disposable data and real loopback sockets."""
import io
import json
import socket
import struct
import unittest
import zipfile
from contextlib import contextmanager
from unittest.mock import patch

from astra.db import connect
from astra.service import AstraService, Forbidden
from astra.web import AstraHandler, CONTENT_SECURITY_POLICY
from astra.xlsx_reader import XlsxError, read_workbook
from import_fixtures import NS, sheet_xml, workbook_bytes
import test_http_timeout
import test_web


def replace_part(data, name, payload):
    target = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(target, 'w') as out:
        for info in source.infolist():
            out.writestr(info, payload if info.filename == name else source.read(info))
    return target.getvalue()


def forged_zip_property(data, offset, value):
    # Modify the first central-directory part; no real encrypted/archive data.
    result = bytearray(data)
    position = result.index(b'PK\x01\x02')
    struct.pack_into('<H', result, position + offset, value)
    return bytes(result)


class RequestFramingTests(unittest.TestCase):
    setUp = test_http_timeout.HttpTimeoutTests.setUp
    stop_server = test_http_timeout.HttpTimeoutTests.stop_server
    client = test_http_timeout.HttpTimeoutTests.client
    response_bytes = test_http_timeout.HttpTimeoutTests.response_bytes
    assert_closed = test_http_timeout.HttpTimeoutTests.assert_closed

    def refused(self, headers, body=b'{}', path='/api/login', *, eof=False, method='POST'):
        def unexpected_login(handler, payload):
            return handler._json({'unexpected': True})
        with patch.object(AstraHandler, '_login', side_effect=unexpected_login, autospec=True) as login, \
                patch.object(AstraHandler, '_require_user', side_effect=RuntimeError('Dispatch must not happen')) as auth:
            client = self.client()
            client.sendall((f'{method} {path} HTTP/1.1\r\nHost: localhost\r\n{headers}\r\n').encode() + body)
            if eof:
                client.shutdown(socket.SHUT_WR)
            response = self.response_bytes(client)
            self.assertIn(b' 400 ', response.split(b'\r\n', 1)[0])
            self.assertIn(b'Connection: close\r\n', response)
            login.assert_not_called()
            auth.assert_not_called()
            self.assert_closed()

    def test_negative_body_length_is_refused_before_reading(self):
        self.refused('Content-Length: -1\r\n')

    def test_duplicate_body_lengths_are_refused_even_when_identical(self):
        for second in ('2', '20'):
            with self.subTest(second=second):
                self.finished.clear()
                self.refused(f'Content-Length: 2\r\nContent-Length: {second}\r\n')

    def test_invalid_length_syntax_and_transfer_encoding_are_refused(self):
        for headers in ('Content-Length: +2\r\n', 'Content-Length: 2,2\r\n',
                        'Content-Length: nope\r\n', 'Transfer-Encoding: chunked\r\n',
                        'Content-Length: 2\r\nTransfer-Encoding: identity\r\n'):
            with self.subTest(headers=headers):
                self.finished.clear()
                self.refused(headers)

    def test_eof_short_body_is_not_dispatched_even_when_prefix_is_valid_json(self):
        self.refused('Content-Length: 20\r\n', eof=True)

    def test_eof_short_raw_upload_is_refused_before_authentication(self):
        self.refused('Content-Length: 20\r\n', b'PK', '/api/import/preview', eof=True)

    def test_non_object_json_is_refused_before_dispatch_for_all_write_methods(self):
        for method in ('POST', 'PUT', 'DELETE'):
            for body in (b'[]', b'null', b'1', b'"text"'):
                with self.subTest(method=method, body=body):
                    self.finished.clear()
                    self.refused(f'Content-Length: {len(body)}\r\n', body, method=method)


class ResponseSecurityTests(unittest.TestCase):
    setUp = test_web.AstraWebTests.setUp
    tearDown = test_web.AstraWebTests.tearDown
    request = test_web.AstraWebTests.request

    def assert_headers(self, response):
        self.assertEqual(response.getheader('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.getheader('X-Frame-Options'), 'DENY')
        self.assertEqual(response.getheader('Content-Security-Policy'), CONTENT_SECURITY_POLICY)
        self.assertEqual(response.getheader('Referrer-Policy'), 'no-referrer')
        self.assertEqual(len([h for h, _ in response.getheaders() if h.lower() == 'content-security-policy']), 1)

    def login(self):
        response, data = self.request('POST', '/api/login', dict(email='owner@example.org', password='correct horse battery'))
        self.assertEqual(response.status, 200)
        return response.getheader('Set-Cookie').split(';', 1)[0], data['csrf']

    def test_static_json_and_framework_errors_have_consistent_protection(self):
        for method, path in (('GET', '/'), ('GET', '/api/me'), ('GET', '/static/missing.html'),
                             ('GET', '/missing'), ('PATCH', '/api/projects')):
            with self.subTest(method=method, path=path):
                response, _ = self.request(method, path)
                self.assert_headers(response)
                if response.status >= 400:
                    self.assertEqual(response.getheader('Cache-Control'), 'no-store')

    def test_all_download_serializers_have_security_headers(self):
        cookie, _ = self.login()
        for path in ('/api/import/template.xlsx', '/api/import/template.csv',
                     '/api/export?format=csv', '/api/final-results?format=csv'):
            with self.subTest(path=path):
                self.connection.request('GET', path, headers={'Cookie': cookie})
                response = self.connection.getresponse()
                data = response.read()
                self.assertEqual(response.status, 200)
                self.assertTrue(data)
                self.assert_headers(response)
                self.assertEqual(response.getheader('Cache-Control'), 'no-store')

    def test_xlsx_dtd_and_archive_errors_are_400_without_writes_over_http(self):
        cookie, csrf = self.login()
        s = self.server.service
        owner = s.user_by_email('owner@example.org')
        project = s.create_project(owner, 'Synthetic security project')
        ordinary = workbook_bytes([('Tasks', sheet_xml([['title'], ['Task']]))])
        xml = f'<!DOCTYPE worksheet [<!ENTITY title "expanded">]><worksheet {NS}><sheetData/></worksheet>'.encode()
        variants = (replace_part(ordinary, 'xl/worksheets/sheet1.xml', xml),
                    forged_zip_property(ordinary, 8, 1), forged_zip_property(ordinary, 10, 99))
        for data in variants:
            with self.subTest(size=len(data)):
                self.connection.request('POST', '/api/import/preview', data, headers={
                    'Cookie': cookie, 'X-CSRF-Token': csrf, 'Content-Type': 'application/octet-stream',
                    'X-Project-Id': project['id'], 'X-Filename': 'synthetic.xlsx'})
                response = self.connection.getresponse()
                payload = json.loads(response.read())
                self.assertEqual(response.status, 400, payload)
                self.assert_headers(response)
        self.assertEqual(s.db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0], 0)
        self.assertEqual(s.db.execute('SELECT COUNT(*) FROM imports').fetchone()[0], 0)

    def test_cross_origin_and_form_type_login_do_not_issue_sessions(self):
        body = json.dumps(dict(email='owner@example.org', password='correct horse battery')).encode()
        for origin, content_type, status in (('https://untrusted.example', 'application/json', 403),
                                             (None, 'text/plain', 400)):
            with self.subTest(origin=origin):
                headers = {'Content-Type': content_type}
                if origin:
                    headers['Origin'] = origin
                self.connection.request('POST', '/api/login', body, headers)
                response = self.connection.getresponse()
                response.read()
                self.assertEqual(response.status, status)
                self.assertIsNone(response.getheader('Set-Cookie'))
        self.assertEqual(self.server.db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 0)

    def test_same_origin_json_login_is_allowed(self):
        body = json.dumps(dict(email='owner@example.org', password='correct horse battery')).encode()
        self.connection.request('POST', '/api/login', body, headers={'Content-Type': 'application/json',
            'Origin': f'http://127.0.0.1:{self.server.server_address[1]}'})
        response = self.connection.getresponse()
        response.read()
        self.assertEqual(response.status, 200)
        self.assertIsNotNone(response.getheader('Set-Cookie'))


class XlsxSecurityTests(unittest.TestCase):
    def ordinary(self):
        return workbook_bytes([('Data', sheet_xml([['ordinary text']]))])

    def test_dtd_is_refused_before_entity_expansion_in_all_xml_encodings(self):
        for encoding in ('UTF-8', 'UTF-16', 'UTF-16BE'):
            for subset in ('<!ENTITY text "expanded">', ''):
                with self.subTest(encoding=encoding, subset=subset):
                    xml = (f'<?xml version="1.0" encoding="{encoding}"?>'
                           f'<!DOCTYPE worksheet [{subset}]><worksheet {NS}><sheetData>'
                           '<row r="1"><c r="A1" t="inlineStr"><is><t>ordinary</t></is></c></row>'
                           '</sheetData></worksheet>').encode(encoding)
                    data = replace_part(self.ordinary(), 'xl/worksheets/sheet1.xml', xml)
                    with self.assertRaisesRegex(XlsxError, 'DTD|DOCTYPE'):
                        read_workbook(data)

    def test_internal_and_external_entity_workbooks_are_refused(self):
        for declaration in ('<!ENTITY text "expanded">', '<!ENTITY text SYSTEM "file:///nonexistent-synthetic">'):
            with self.subTest(declaration=declaration):
                xml = (f'<!DOCTYPE worksheet [{declaration}]><worksheet {NS}><sheetData>'
                       '<row r="1"><c r="A1" t="inlineStr"><is><t>&text;</t></is></c></row>'
                       '</sheetData></worksheet>').encode()
                with self.assertRaisesRegex(XlsxError, 'DTD|DOCTYPE'):
                    read_workbook(replace_part(self.ordinary(), 'xl/worksheets/sheet1.xml', xml))

    def test_repeated_sheet_target_is_refused_instead_of_parsed_repeatedly(self):
        data = self.ordinary()
        with zipfile.ZipFile(io.BytesIO(data)) as source:
            xml = source.read('xl/workbook.xml')
        xml = xml.replace(b'</sheets>', b'<sheet name="Other" sheetId="2" r:id="rId1"/></sheets>')
        with self.assertRaisesRegex(XlsxError, 'repeated|duplicate'):
            read_workbook(replace_part(data, 'xl/workbook.xml', xml))

    def test_encrypted_and_unsupported_archives_use_workbook_error(self):
        for offset, value in ((8, 1), (10, 99)):
            with self.subTest(offset=offset):
                with self.assertRaises(XlsxError):
                    read_workbook(forged_zip_property(self.ordinary(), offset, value))

    def test_ordinary_utf16_xml_and_literal_dtd_text_remain_readable(self):
        data = workbook_bytes([('Data', sheet_xml([['<!DOCTYPE is literal text', '&entity;']]))])
        with zipfile.ZipFile(io.BytesIO(data)) as source:
            xml = source.read('xl/worksheets/sheet1.xml').decode('utf-8').replace('encoding="UTF-8"', 'encoding="UTF-16"')
        result = read_workbook(replace_part(data, 'xl/worksheets/sheet1.xml', xml.encode('utf-16')))
        self.assertEqual(result.sheets[0].row_values(1), ['<!DOCTYPE is literal text', '&entity;'])


class RevokedOwnerTests(unittest.TestCase):
    setUp = test_web.AstraWebTests.setUp
    tearDown = test_web.AstraWebTests.tearDown
    request = test_web.AstraWebTests.request

    def deputy(self):
        s = self.server.service
        self.primary = s.user_by_email('owner@example.org')
        person = s.create_user(self.primary, 'deputy@example.org', 'Deputy', 'synthetic password')
        return s.grant_secondary_owner(self.primary, person['id'], 'Cover')

    def revoke(self, deputy, inactive):
        s = self.server.service
        s.revoke_secondary_owner(self.primary, deputy['id'], 'End cover')
        if inactive:
            s.set_user_active(self.primary, deputy['id'], False)

    def test_stale_owner_snapshot_cannot_create_users_or_change_activity(self):
        for inactive in (False, True):
            with self.subTest(inactive=inactive):
                s = self.server.service
                if inactive:
                    s.set_user_active(self.primary, deputy['id'], True)
                    deputy = s.grant_secondary_owner(self.primary, deputy['id'], 'Cover again')
                else:
                    deputy = self.deputy()
                victim = s.create_user(self.primary, f'victim{inactive}@example.org', 'Victim', 'synthetic password')
                self.revoke(deputy, inactive)
                with self.assertRaises(Forbidden):
                    s.create_user(deputy, f'forbidden{inactive}@example.org', 'No access', 'synthetic password')
                with self.assertRaises(Forbidden):
                    s.set_user_active(deputy, victim['id'], False)
                self.assertEqual(s.get_user(victim['id'])['active'], 1)

    def test_revocation_after_precheck_before_user_insert_is_refused(self):
        deputy = self.deputy()
        original = __import__('astra.service', fromlist=['hash_password']).hash_password
        def hash_then_revoke(password):
            value = original(password)
            self.revoke(deputy, False)
            return value
        with patch('astra.service.hash_password', side_effect=hash_then_revoke):
            with self.assertRaises(Forbidden):
                self.server.service.create_user(deputy, 'forbidden@example.org', 'No access', 'synthetic password')
        self.assertIsNone(self.server.service.user_by_email('forbidden@example.org'))

    def test_http_inflight_revocation_blocks_account_and_activity_changes(self):
        deputy = self.deputy()
        s = self.server.service
        victim = s.create_user(self.primary, 'victim@example.org', 'Victim', 'synthetic password')
        response, login = self.request('POST', '/api/login', dict(email=deputy['email'], password='synthetic password'))
        cookie = response.getheader('Set-Cookie').split(';', 1)[0]
        original = AstraHandler._require_user
        def authenticated_then_revoked(handler):
            actor, csrf = original(handler)
            with_db = connect(self.server.db_path)
            try:
                service = AstraService(with_db)
                service.revoke_secondary_owner(service.get_user(self.primary['id']), deputy['id'], 'End cover')
            finally:
                with_db.close()
            return actor, csrf
        for action in ('create', 'deactivate'):
            if action == 'deactivate':
                deputy = s.grant_secondary_owner(self.primary, deputy['id'], 'Cover again')
                response, login = self.request('POST', '/api/login', dict(email=deputy['email'], password='synthetic password'))
                cookie = response.getheader('Set-Cookie').split(';', 1)[0]
            with patch.object(AstraHandler, '_require_user', authenticated_then_revoked):
                path, body = ('/api/users', dict(email='forbidden@example.org', display_name='No access', password='synthetic password')) \
                    if action == 'create' else ('/api/users/' + victim['id'] + '/active', {'active': False})
                response, _ = self.request('POST', path, body, cookie=cookie, csrf=login['csrf'])
                self.assertEqual(response.status, 403)
        self.assertIsNone(s.user_by_email('forbidden@example.org'))
        self.assertEqual(s.get_user(victim['id'])['active'], 1)


class TaskPermissionDriftTests(unittest.TestCase):
    setUp = test_web.AstraWebTests.setUp
    tearDown = test_web.AstraWebTests.tearDown

    def test_manager_demotion_at_write_lock_refuses_create_and_update(self):
        s = self.server.service
        owner = s.user_by_email('owner@example.org')
        manager = s.create_user(owner, 'manager@example.org', 'Manager', 'synthetic password')
        project = s.create_project(owner, 'Permission drift')
        s.grant_project_access(owner, project['id'], manager['id'], 'manager')
        task = s.create_task(owner, dict(project_id=project['id'], title='Original'))
        original = s._schedule_transaction
        @contextmanager
        def demote_before_lock(actor, project_id):
            s.grant_project_access(owner, project_id, manager['id'], 'viewer')
            with original(actor, project_id):
                yield
        for action in ('create', 'update'):
            with self.subTest(action=action):
                s.grant_project_access(owner, project['id'], manager['id'], 'manager')
                with patch.object(s, '_schedule_transaction', demote_before_lock):
                    with self.assertRaises(Forbidden):
                        if action == 'create':
                            s.create_task(manager, dict(project_id=project['id'], title='Forbidden'))
                        else:
                            s.update_task(manager, task['id'], dict(title='Forbidden', expected_revision=task['revision']))
                self.assertEqual(s.get_task(owner, task['id'])['title'], 'Original')
                self.assertEqual(s.db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0], 1)

    def test_owner_role_revoked_after_task_precheck_cannot_use_snapshot_to_edit(self):
        s = self.server.service
        owner = s.user_by_email('owner@example.org')
        deputy = s.create_user(owner, 'deputy@example.org', 'Deputy', 'synthetic password')
        project = s.create_project(owner, 'Permission drift')
        s.grant_project_access(owner, project['id'], deputy['id'], 'viewer')
        deputy = s.grant_secondary_owner(owner, deputy['id'], 'Cover')
        task = s.create_task(owner, dict(project_id=project['id'], title='Original'))
        original = s._schedule_transaction
        @contextmanager
        def revoke_before_lock(actor, project_id):
            s.revoke_secondary_owner(owner, deputy['id'], 'End cover')
            with original(actor, project_id):
                yield
        with patch.object(s, '_schedule_transaction', revoke_before_lock):
            with self.assertRaises(Forbidden):
                s.update_task(deputy, task['id'], dict(title='Forbidden', expected_revision=task['revision']))
        self.assertEqual(s.get_task(owner, task['id'])['title'], 'Original')

    def test_new_assignee_deactivation_or_access_loss_at_lock_refuses_create_and_update(self):
        s = self.server.service
        owner = s.user_by_email('owner@example.org')
        project = s.create_project(owner, 'Assignee eligibility')
        original = s._schedule_transaction
        for action in ('create', 'update'):
            for removal in ('inactive', 'membership'):
                with self.subTest(action=action, removal=removal):
                    task = s.create_task(owner, dict(project_id=project['id'], title='Original'))
                    before_count = s.db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
                    target = s.create_user(owner, f'{action}-{removal}@example.org', 'Target', 'synthetic password')
                    s.grant_project_access(owner, project['id'], target['id'], 'member')
                    @contextmanager
                    def remove_before_lock(actor, project_id):
                        if removal == 'inactive':
                            s.set_user_active(owner, target['id'], False)
                        else:
                            s.revoke_project_access(owner, project_id, target['id'])
                        with original(actor, project_id):
                            yield
                    with patch.object(s, '_schedule_transaction', remove_before_lock):
                        with self.assertRaises((ValueError, Forbidden)):
                            if action == 'create':
                                s.create_task(owner, dict(project_id=project['id'], title='Forbidden', owner_user_id=target['id']))
                            else:
                                s.update_task(owner, task['id'], dict(owner_user_id=target['id'], expected_revision=task['revision']))
                    self.assertIsNone(s.get_task(owner, task['id'])['owner_user_id'])
                    self.assertEqual(s.db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0], before_count)


class ProjectPolicyTests(unittest.TestCase):
    setUp = test_web.AstraWebTests.setUp
    tearDown = test_web.AstraWebTests.tearDown
    request = test_web.AstraWebTests.request

    def fixture(self):
        s = self.server.service
        owner = s.user_by_email('owner@example.org')
        manager = s.create_user(owner, 'manager@example.org', 'Manager', 'synthetic password')
        deputy = s.create_user(owner, 'deputy@example.org', 'Deputy', 'synthetic password')
        deputy = s.grant_secondary_owner(owner, deputy['id'], 'Cover')
        project = s.create_project(owner, 'Policy check')
        s.grant_project_access(owner, project['id'], manager['id'], 'manager')
        return s, owner, manager, deputy, project

    def test_closed_projects_require_reopening_before_task_creation(self):
        s, owner, manager, deputy, project = self.fixture()
        s.close_project(owner, project['id'], 'Finished')
        for actor in (owner, deputy, manager):
            with self.subTest(actor=actor['display_name']), self.assertRaises(Forbidden):
                s.create_task(actor, dict(project_id=project['id'], title='Must reopen'))
        self.assertEqual(s.db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0], 0)
        s.reopen_project(owner, project['id'], 'New work approved')
        self.assertEqual(s.create_task(manager, dict(project_id=project['id'], title='New work'))['title'], 'New work')

    def test_owner_only_targets_preserve_manager_start_date_and_owner_notices(self):
        s, owner, manager, deputy, project = self.fixture()
        s.set_project_schedule(owner, project['id'], '2026-10-01', '2026-10-10', 'Agreed')
        for target in ('2026-10-20', '2026-10-09', None):
            with self.subTest(target=target), self.assertRaises(Forbidden):
                s.set_project_schedule(manager, project['id'], '2026-10-01', target, 'Not allowed')
        s.set_project_schedule(manager, project['id'], '2026-10-02', '2026-10-10', 'Start revised')
        self.assertEqual(s.get_project(owner, project['id'])['start_date'], '2026-10-02')
        s.set_project_schedule(deputy, project['id'], '2026-10-02', '2026-10-20', 'Approved later target')
        self.assertEqual(s.get_project(owner, project['id'])['target_date'], '2026-10-20')

    def test_http_rejects_manager_deadline_revision_and_closed_creation(self):
        s, owner, manager, _, project = self.fixture()
        s.set_project_schedule(owner, project['id'], None, '2026-10-10', 'Agreed')
        response, login = self.request('POST', '/api/login', dict(email=manager['email'], password='synthetic password'))
        cookie = response.getheader('Set-Cookie').split(';', 1)[0]
        response, _ = self.request('POST', '/api/projects/' + project['id'] + '/schedule',
            dict(target_date='2026-10-20', reason='No authority'), cookie=cookie, csrf=login['csrf'])
        self.assertEqual(response.status, 403)
        s.close_project(owner, project['id'], 'Finished')
        response, _ = self.request('POST', '/api/tasks', dict(project_id=project['id'], title='No authority'),
            cookie=cookie, csrf=login['csrf'])
        self.assertEqual(response.status, 403)
        self.assertEqual(s.db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
