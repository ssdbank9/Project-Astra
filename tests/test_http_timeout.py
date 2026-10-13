"""Exercise stalled clients on real sockets without opening an owner database."""
import http.client
import json
import math
import os
import socket
import sqlite3
import tempfile
import threading
import unittest
from unittest import mock

from astra.web import AstraHandler, AstraServer, connect


class HttpTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='astra-http-timeout-')
        self.addCleanup(self.temp.cleanup)
        self.home = mock.patch.dict(os.environ, {'ASTRA_HOME': self.temp.name})
        self.home.start()
        self.addCleanup(self.home.stop)
        self.finished = threading.Event()
        self.opened = threading.Event()
        self.connections = []
        self.socket_timeouts = []
        self.errors = []
        case = self

        class ObservedHandler(AstraHandler):
            def setup(self):
                super().setup()
                case.socket_timeouts.append(self.connection.gettimeout())

            def finish(self):
                try:
                    super().finish()
                finally:
                    case.finished.set()

            def log_message(self, *args):
                pass

        class ObservedServer(AstraServer):
            def handle_error(self, request, client_address):
                # Retain unexpected handler failures without noisy tracebacks.
                import sys
                case.errors.append(sys.exception())

        self.server = ObservedServer(('127.0.0.1', 0))
        self.server.RequestHandlerClass = ObservedHandler
        policy = getattr(AstraHandler, 'timeout', None)
        valid = isinstance(policy, (int, float)) and math.isfinite(policy) and policy > 0
        # Shorten a real production policy; a removed/missing guard remains missing.
        self.policy = mock.patch.object(AstraHandler, 'timeout', min(policy, .2) if valid else policy)
        self.policy.start()
        self.addCleanup(self.policy.stop)

        def tracking_connect(path):
            db = connect(path)
            self.connections.append(db)
            self.opened.set()
            return db

        self.connection_patch = mock.patch('astra.web.connect', side_effect=tracking_connect)
        self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.address = self.server.server_address
        self.clients = []

    def stop_server(self):
        for client in self.clients:
            client.close()
        # Even before the fix, closing a stalled client releases its handler.
        # Join that cleanup before removing SQLite files on Windows.
        if self.clients:
            self.finished.wait(2)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def client(self):
        client = socket.create_connection(self.address, timeout=1)
        self.clients.append(client)
        return client

    def response_bytes(self, client):
        chunks = []
        try:
            while chunk := client.recv(4096):
                chunks.append(chunk)
        except TimeoutError:
            self.fail('Stalled client connection was not released within the test deadline.')
        return b''.join(chunks)

    def assert_closed(self):
        self.assertTrue(self.finished.wait(1), 'Request handler did not finish.')
        for db in self.connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                db.execute('SELECT 1')
        self.assertEqual(self.errors, [])

    def test_incomplete_headers_release_socket_before_opening_database(self):
        client = self.client()
        client.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\nX-Stalled: ')
        self.assertEqual(self.response_bytes(client), b'')
        self.assert_closed()
        self.assertEqual(self.connections, [])
        self.assertGreater(self.socket_timeouts[0], 0)

    def test_idle_connection_is_released(self):
        client = self.client()
        self.assertEqual(self.response_bytes(client), b'')
        self.assert_closed()
        self.assertEqual(self.connections, [])

    def stalled_body(self, path, content_type):
        with mock.patch.object(AstraHandler, '_login') as login, \
                mock.patch.object(AstraHandler, '_require_user') as authorization:
            client = self.client()
            client.sendall((f'POST {path} HTTP/1.1\r\nHost: localhost\r\n'
                            f'Content-Type: {content_type}\r\nContent-Length: 100\r\n\r\n{{').encode())
            self.assertTrue(self.opened.wait(1), 'Request did not reach the body reader.')
            response = self.response_bytes(client)
            self.assertIn(b' 408 ', response.split(b'\r\n', 1)[0])
            self.assertIn(b'Connection: close\r\n', response)
            payload = json.loads(response.split(b'\r\n\r\n', 1)[1])
            self.assertEqual(payload['error'], 'Request body timed out. Send the request again.')
            login.assert_not_called()
            authorization.assert_not_called()
            self.assert_closed()

    def test_stalled_login_body_returns_408_and_closes_database(self):
        self.stalled_body('/api/login', 'application/json')

    def test_stalled_mutation_body_does_not_reach_authorization(self):
        self.stalled_body('/api/projects', 'application/json')

    def test_stalled_raw_import_body_returns_408_and_closes_database(self):
        self.stalled_body('/api/import/preview', 'application/octet-stream')

    def test_body_completed_in_separate_chunks_within_timeout_succeeds(self):
        def login(handler, payload):
            self.assertEqual(payload, {'example': True})
            return handler._json({'ok': True})

        with mock.patch.object(AstraHandler, '_login', login):
            client = self.client()
            body = b'{"example":true}'
            client.sendall((f'POST /api/login HTTP/1.1\r\nHost: localhost\r\n'
                            f'Content-Length: {len(body)}\r\n\r\n').encode() + body[:3])
            self.assertTrue(self.opened.wait(1))
            client.sendall(body[3:])
            response = self.response_bytes(client)
            self.assertIn(b' 200 ', response.split(b'\r\n', 1)[0])
            self.assertEqual(json.loads(response.split(b'\r\n\r\n', 1)[1]), {'ok': True})
            self.assert_closed()

    def test_normal_static_request_retains_security_headers(self):
        connection = http.client.HTTPConnection(*self.address, timeout=2)
        self.addCleanup(connection.close)
        connection.request('GET', '/')
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn("default-src 'self'", response.getheader('Content-Security-Policy'))
        self.assertIn(b'ASTRA', response.read())
        self.assert_closed()
