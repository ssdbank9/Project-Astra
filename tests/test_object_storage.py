"""MXY7BG slice 4 (Owner Items 6-7 on 6G89SJ): the second storage backend (private object
storage through the S3-compatible API), one active backend per installation, and the
controlled migration: copy, verify size and SHA-256, update metadata only after
verification, keep the old copy for a rollback. The bucket is tests/fake_s3.py, which checks
every signature itself; behaviour against a live OCI tenancy is not tested here."""
import contextlib
import hashlib
import http.client
import io
import json
import os
import socket
import sqlite3
import ssl
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from astra import __main__ as entry
from astra import attachment_storage as storage_module
from astra import object_storage, web
from astra.attachment_storage import (
    BACKENDS, STORAGE_BACKEND_ENV, FolderStorage, StorageError, StorageNotConfigured, active_backend,
    active_storage, storage_named, stream_size, valid_key,
)
from astra.db import connect
from astra.object_storage import S3Storage, authorization_v4, oci_native_object_url, settings_from_env
from astra import service as service_module
from astra.service import AstraService, Conflict, Forbidden
from astra.web import AstraServer, create_wsgi_app
from fake_s3 import FakeS3, signature_v4

PDF = b"%PDF-1.7\n" + b"x" * 1000
VIA = {"via": "cli", "os_user": "tester", "host": "testhost"}
EMPTY = hashlib.sha256(b"").hexdigest()
S3_NAMES = object_storage.SETTING_NAMES


def clean_environment(test, **values):
    """This test's own environment: no storage setting leaks in from the machine or out."""
    patcher = patch.dict(os.environ, values)
    patcher.start()
    test.addCleanup(patcher.stop)
    for name in (STORAGE_BACKEND_ENV, *S3_NAMES):
        if name not in values:
            os.environ.pop(name, None)


class SignatureTests(unittest.TestCase):
    """AWS Signature Version 4 against the two worked examples in the Amazon S3 API
    reference ("Signature Calculations for the Authorization Header", single chunk)."""

    ACCESS, SECRET = "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    HOST, DATE = "examplebucket.s3.amazonaws.com", "20130524T000000Z"

    def sign(self, method, path, headers, payload_hash):
        return authorization_v4(method, path, headers, payload_hash, access_key=self.ACCESS,
                                secret_key=self.SECRET, region="us-east-1")

    def test_get_object_example(self):
        headers = {"Host": self.HOST, "Range": "bytes=0-9", "x-amz-content-sha256": EMPTY, "x-amz-date": self.DATE}
        signature = "f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"
        self.assertEqual(
            self.sign("GET", "/test.txt", headers, EMPTY),
            "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request, "
            "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date, Signature=" + signature)
        # The test bucket's own implementation agrees, so it is a fair judge of Astra's requests.
        lowered = {name.lower(): value for name, value in headers.items()}
        self.assertEqual(signature_v4(self.SECRET, "GET", "/test.txt", lowered, sorted(lowered), EMPTY, self.DATE,
                                      "us-east-1"), signature)

    def test_put_object_example(self):
        payload_hash = hashlib.sha256(b"Welcome to Amazon S3.").hexdigest()
        self.assertEqual(payload_hash, "44ce7dd67c959e0d3524ffac1771dfbba87d2b6b4b4e99e42034a8b803f8b072")
        headers = {"Host": self.HOST, "Date": "Fri, 24 May 2013 00:00:00 GMT", "x-amz-date": self.DATE,
                   "x-amz-storage-class": "REDUCED_REDUNDANCY", "x-amz-content-sha256": payload_hash}
        signature = "98ad721746da40c64f1a55b78f14c238d841ea1380cd77a1b5971af0ece108bd"
        self.assertTrue(self.sign("PUT", "/test%24file.text", headers, payload_hash).endswith(
            "SignedHeaders=date;host;x-amz-content-sha256;x-amz-date;x-amz-storage-class, Signature=" + signature))
        lowered = {name.lower(): value for name, value in headers.items()}
        self.assertEqual(signature_v4(self.SECRET, "PUT", "/test%24file.text", lowered, sorted(lowered),
                                      payload_hash, self.DATE, "us-east-1"), signature)

    def test_a_different_key_path_or_payload_changes_the_signature(self):
        headers = {"Host": self.HOST, "x-amz-content-sha256": EMPTY, "x-amz-date": self.DATE}
        base = self.sign("GET", "/a", headers, EMPTY)
        self.assertNotEqual(base, self.sign("GET", "/b", headers, EMPTY))
        self.assertNotEqual(base, self.sign("DELETE", "/a", headers, EMPTY))
        self.assertNotEqual(base, self.sign("GET", "/a", headers, "0" * 64))
        self.assertNotEqual(base, authorization_v4("GET", "/a", headers, EMPTY, access_key=self.ACCESS,
                                                   secret_key=self.SECRET + "x", region="us-east-1"))


class SettingsTests(unittest.TestCase):
    GOOD = {"ASTRA_S3_ENDPOINT": "https://axabc123.compat.objectstorage.me-jeddah-1.oraclecloud.com",
            "ASTRA_S3_REGION": "me-jeddah-1", "ASTRA_S3_BUCKET": "astra-uploads",
            "ASTRA_S3_ACCESS_KEY_ID": "0123456789abcdef0123456789abcdef01234567",
            "ASTRA_S3_SECRET_ACCESS_KEY": "s3cr3t+Value/ThatMustNeverShow="}

    def test_complete_settings_are_read_and_the_secret_is_never_shown(self):
        settings = settings_from_env(self.GOOD)
        self.assertEqual((settings.secure, settings.host, settings.port, settings.region, settings.bucket),
                         (True, "axabc123.compat.objectstorage.me-jeddah-1.oraclecloud.com", None, "me-jeddah-1",
                          "astra-uploads"))
        self.assertEqual(settings.secret_key, self.GOOD["ASTRA_S3_SECRET_ACCESS_KEY"])
        self.assertNotIn("s3cr3t", repr(settings))
        self.assertNotIn("s3cr3t", repr(S3Storage(settings, Path("spool")).settings))

    def test_what_is_missing_is_named(self):
        with self.assertRaises(StorageNotConfigured) as caught:
            settings_from_env({})
        for name in S3_NAMES:
            self.assertIn(name, str(caught.exception))
        partial = {**self.GOOD, "ASTRA_S3_BUCKET": " "}
        with self.assertRaisesRegex(StorageNotConfigured, "set ASTRA_S3_BUCKET\\.$"):
            settings_from_env(partial)

    def test_a_wrong_setting_is_refused_without_repeating_any_value(self):
        wrong = {
            "ASTRA_S3_ENDPOINT": ("http://objectstorage.example.com", "ftp://x.example.com", "https://", "not a url",
                                  "https://user:pw@x.example.com", "https://x.example.com/bucket",
                                  "https://x.example.com?a=1", "https://x.example.com:99999",
                                  "https://b\u00fccket.example.com"),
            "ASTRA_S3_REGION": ("Me Jeddah", "x/y", "a" * 41),
            "ASTRA_S3_BUCKET": ("a/b", "..", "a b", "x" * 257),
            "ASTRA_S3_ACCESS_KEY_ID": ("has space", "new\nline"),
            "ASTRA_S3_SECRET_ACCESS_KEY": ("has space", "tab\there"),
        }
        for name, values in wrong.items():
            for value in values:
                with self.subTest(name=name, value=value):
                    with self.assertRaises(StorageNotConfigured) as caught:
                        settings_from_env({**self.GOOD, name: value})
                    message = str(caught.exception)
                    self.assertIn(name, message)
                    self.assertNotIn("s3cr3t", message)
                    self.assertNotIn(self.GOOD["ASTRA_S3_ACCESS_KEY_ID"], message)

    def test_plain_http_is_for_this_machine_only(self):
        for endpoint in ("http://127.0.0.1:9000", "http://localhost:9000", "http://[::1]:9000"):
            self.assertFalse(settings_from_env({**self.GOOD, "ASTRA_S3_ENDPOINT": endpoint}).secure)

    def test_the_native_oci_address_of_an_object_is_derived_for_the_public_check(self):
        self.assertEqual(
            oci_native_object_url("axabc123.compat.objectstorage.me-jeddah-1.oraclecloud.com", "astra uploads", "k"),
            ("objectstorage.me-jeddah-1.oraclecloud.com", "/n/axabc123/b/astra%20uploads/o/k"))
        self.assertIsNone(oci_native_object_url("127.0.0.1", "b", "k"))
        self.assertIsNone(oci_native_object_url("s3.amazonaws.com", "b", "k"))


class BackendChoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        clean_environment(self, ASTRA_UPLOAD_ROOT=self.temp.name)

    def test_the_folder_is_the_backend_unless_object_storage_is_chosen(self):
        self.assertEqual(BACKENDS, ("folder", "s3"))
        self.assertEqual(active_backend(), "folder")
        self.assertIsInstance(active_storage(), FolderStorage)
        for chosen in ("s3", " S3 "):
            os.environ[STORAGE_BACKEND_ENV] = chosen
            self.assertEqual(active_backend(), "s3")
        for wrong in ("ftp", "folder,s3", "oci"):
            os.environ[STORAGE_BACKEND_ENV] = wrong
            with self.subTest(wrong=wrong), self.assertRaisesRegex(StorageNotConfigured, STORAGE_BACKEND_ENV):
                active_backend()
            with self.assertRaises(StorageNotConfigured):
                active_storage()

    def test_object_storage_without_its_settings_is_not_configured(self):
        os.environ[STORAGE_BACKEND_ENV] = "s3"
        with self.assertRaisesRegex(StorageNotConfigured, "ASTRA_S3_SECRET_ACCESS_KEY"):
            active_storage()
        with self.assertRaises(StorageNotConfigured):
            storage_named("tape")

    def test_a_wrong_configuration_stops_the_server_before_it_listens(self):
        for chosen in ("ftp", "s3"):
            os.environ[STORAGE_BACKEND_ENV] = chosen
            with patch("astra.web.AstraServer") as server, patch("astra.web.create_wsgi_app") as app, \
                    patch("waitress.serve"), patch("astra.web.DailyDigestScheduler"):
                with self.subTest(chosen=chosen, server="development"), self.assertRaises(StorageNotConfigured):
                    web.serve("127.0.0.1", 0)
                with self.subTest(chosen=chosen, server="waitress"), self.assertRaises(StorageNotConfigured):
                    web.serve_waitress("127.0.0.1", 0)
            server.assert_not_called()
            app.assert_not_called()
            with self.assertRaises(SystemExit) as caught:
                entry.main(["serve"])
            self.assertTrue(str(caught.exception).startswith("File storage: "), caught.exception)

    def test_only_32_hex_characters_are_a_storage_key(self):
        self.assertTrue(valid_key("0123456789abcdef0123456789abcdef"))
        for bad in ("", "0123456789abcdef0123456789abcde", "0123456789ABCDEF0123456789ABCDEF",
                    "0123456789abcdef0123456789abcdef\n", "../" + "a" * 29, "a" * 33, None, 5, b"a" * 32):
            with self.subTest(bad=bad):
                self.assertFalse(valid_key(bad))


class S3Fixture(unittest.TestCase):
    """An owner, a project, a task, a private upload folder and a private test bucket."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.uploads = Path(self.temp.name) / "uploads"
        clean_environment(self, ASTRA_UPLOAD_ROOT=str(self.uploads), ASTRA_HOME=self.temp.name)
        self.fake = FakeS3().__enter__()
        self.addCleanup(self.fake.__exit__, None, None, None)
        self.db = connect(Path(self.temp.name) / "astra.sqlite3")
        self.addCleanup(self.db.close)
        self.service = AstraService(self.db)
        self.owner = self.service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")
        self.project = self.service.create_project(self.owner, "Hosted")
        self.task = self.service.create_task(self.owner, {"project_id": self.project["id"], "title": "Deliver"})

    def use(self, backend):
        os.environ[STORAGE_BACKEND_ENV] = backend
        if backend == "s3":
            os.environ.update(self.fake.env())

    def upload(self, name="report.pdf", data=PDF):
        return self.service.add_task_file(self.owner, self.task["id"], name, "application/pdf", io.BytesIO(data),
                                          len(data))

    def download(self, attachment):
        _, handle = self.service.open_task_file(self.owner, self.task["id"], attachment["id"])
        with handle:
            return handle.read()

    def key(self, attachment):
        return self.db.execute("SELECT storage_key FROM task_attachments WHERE id=?", (attachment["id"],)).fetchone()[0]

    def where(self):
        return {row["display_name"]: (row["storage_backend"], row["storage_previous"]) for row in self.db.execute(
            "SELECT display_name, storage_backend, storage_previous FROM task_attachments")}

    def in_folder(self):
        objects = self.uploads / "objects"
        return sorted(p.name for p in objects.iterdir()) if objects.is_dir() else []

    def leftovers(self):
        """Anything under the upload folder that is not a finished object."""
        return sorted(str(p.relative_to(self.uploads)) for p in self.uploads.rglob("*")
                      if p.is_file() and p.parent.name != "objects")

    def user_events(self, kind):
        return [json.loads(row["detail_json"]) for row in self.db.execute(
            "SELECT detail_json FROM user_events WHERE event_type=? ORDER BY rowid", (kind,))]


class StorageContractTests(S3Fixture):
    """Item 6: both backends behind one interface behave the same."""

    def backends(self):
        self.use("s3")
        yield FolderStorage(self.uploads)
        yield storage_named("s3")

    def test_save_open_put_and_delete(self):
        for storage in self.backends():
            with self.subTest(backend=storage.name):
                data = os.urandom(3 * storage_module.CHUNK_BYTES + 17)
                stored = storage.save(iter([data[:100], data[100:]]))
                self.assertTrue(valid_key(stored.key))
                self.assertEqual((stored.size, stored.sha256), (len(data), hashlib.sha256(data).hexdigest()))
                handle = storage.open(stored.key)
                with handle:
                    self.assertEqual(stream_size(handle), len(data))
                    self.assertEqual(b"".join(iter(lambda: handle.read(storage_module.CHUNK_BYTES), b"")), data)
                other = "0123456789abcdef0123456789abcdef"
                again = storage.put(other, [b"second ", b"object"])
                self.assertEqual((again.key, again.size), (other, 13))
                storage.put(other, [b"replaced"])  # a rerun of a migration writes the same key again
                with storage.open(other) as handle:
                    self.assertEqual(handle.read(), b"replaced")
                storage.delete(stored.key)
                storage.delete(stored.key)  # deleting what is not there is not an error
                with self.assertRaises(KeyError):
                    storage.open(stored.key)
                storage.delete(other)
                self.assertEqual(self.leftovers(), [])

    def test_only_a_storage_key_reaches_the_backend(self):
        for storage in self.backends():
            for bad in ("", "../../etc/passwd", "0123456789abcdef0123456789abcdef\n", "a" * 31, None):
                with self.subTest(backend=storage.name, bad=bad):
                    self.fake.requests.clear()
                    with self.assertRaises(KeyError):
                        storage.open(bad)
                    with self.assertRaises(KeyError):
                        storage.delete(bad)
                    with self.assertRaises(ValueError):
                        storage.put(bad, [b"x"])
                    self.assertEqual(self.fake.requests, [])

    def test_a_failed_save_leaves_nothing_behind(self):
        def broken():
            yield b"first part"
            raise RuntimeError("the upload stopped")
        for storage in self.backends():
            with self.subTest(backend=storage.name), self.assertRaises(RuntimeError):
                storage.save(broken())
        self.assertEqual((self.in_folder(), self.leftovers(), self.fake.objects), ([], [], {}))


class ObjectStorageTests(S3Fixture):
    def setUp(self):
        super().setUp()
        self.use("s3")
        self.storage = storage_named("s3")

    def test_every_request_is_signed_and_the_bucket_checks_it(self):
        stored = self.storage.save([b"hello"])
        self.assertEqual(self.fake.objects, {stored.key: b"hello"})
        self.assertEqual(self.fake.requests, [("PUT", f"/astra-test/{stored.key}", 200)])
        # A wrong key is refused by the bucket; the error names the refusal and nothing secret.
        os.environ["ASTRA_S3_SECRET_ACCESS_KEY"] = "a-wrong-secret"
        wrong = storage_named("s3")
        for attempt in (lambda: wrong.save([b"x"]), lambda: wrong.open(stored.key), lambda: wrong.delete(stored.key)):
            with self.assertRaises(StorageError) as caught:
                attempt()
            message = str(caught.exception)
            self.assertIn("HTTP 403 SignatureDoesNotMatch", message)
            for secret in ("a-wrong-secret", self.fake.access_key, "string-to-sign-detail"):
                self.assertNotIn(secret, message)
        self.assertEqual(self.fake.objects, {stored.key: b"hello"})

    def test_the_bucket_refuses_a_request_without_the_key_unless_it_is_public(self):
        stored = self.storage.save([b"private"])
        [(where, status)] = self.storage.anonymous_reads(stored.key)
        self.assertEqual((status, where.endswith(f"/astra-test/{stored.key}")), (403, True))
        self.fake.public = True
        self.assertEqual(self.storage.anonymous_reads(stored.key)[0][1], 200)

    def test_an_unreachable_or_failing_bucket_is_a_storage_error(self):
        stored = self.storage.save([b"kept"])
        for fault in ("500", "drop"):
            self.fake.fault = lambda method, key, fault=fault: fault
            for attempt in (lambda: self.storage.save([b"x"]), lambda: self.storage.open(stored.key),
                            lambda: self.storage.delete(stored.key)):
                with self.subTest(fault=fault), self.assertRaises(StorageError) as caught:
                    attempt()
                self.assertNotIn(self.fake.secret_key, str(caught.exception))
        self.fake.fault = None
        with socket.socket() as taken:  # a port that was free a moment ago: nothing listens there
            taken.bind(("127.0.0.1", 0))
            closed_port = taken.getsockname()[1]
        os.environ["ASTRA_S3_ENDPOINT"] = f"http://127.0.0.1:{closed_port}"
        with self.assertRaisesRegex(StorageError, "could not be reached"):
            storage_named("s3").open(stored.key)
        self.assertEqual(self.leftovers(), [])

    def test_a_download_that_ends_early_is_an_error_not_a_short_file(self):
        stored = self.storage.save([b"0123456789" * 50])
        self.fake.fault = lambda method, key: "truncate" if method == "GET" else None
        handle = self.storage.open(stored.key)
        self.assertEqual(handle.size, 500)
        with handle, self.assertRaises(StorageError):
            while handle.read(64):
                pass

    def test_a_missing_object_is_not_found(self):
        with self.assertRaises(KeyError):
            self.storage.open("0123456789abcdef0123456789abcdef")

    def test_a_missing_bucket_is_a_storage_error_not_a_missing_file(self):
        # A wrong bucket name or endpoint answers 404 for everything. That must never read as
        # "this file is gone" or "this file is deleted": Item 7, nothing stranded silently.
        stored = self.storage.save([b"kept"])
        attachment = self.upload()
        self.fake.fault = lambda method, key: "no-bucket"
        for attempt in (lambda: self.storage.open(stored.key), lambda: self.storage.delete(stored.key),
                        lambda: self.storage.save([b"x"]), lambda: self.download(attachment)):
            with self.assertRaises(StorageError) as caught:
                attempt()
            self.assertIn("HTTP 404 NoSuchBucket", str(caught.exception))
        self.assertEqual(self.service.verify_storage()["verified"], 0)
        self.fake.fault = None
        self.assertEqual(self.service.verify_storage(), {"verified": 1, "failed": []})

    def test_an_answer_that_does_not_say_its_length_is_refused(self):
        stored = self.storage.save([b"0123456789"])
        self.fake.fault = lambda method, key: "no-length" if method == "GET" else None
        with self.assertRaisesRegex(StorageError, "did not say how long"):
            self.storage.open(stored.key)

    def test_a_connection_that_breaks_while_reading_is_a_storage_error(self):
        broken = Mock()
        broken.read.side_effect = ConnectionResetError("reset by peer")
        body = object_storage._Body(Mock(), broken, 10)
        with self.assertRaisesRegex(StorageError, "stopped answering during the download"):
            body.read(4)
        with self.assertRaisesRegex(StorageError, "stopped answering"):
            S3Storage._finish(broken)
        broken.read.side_effect = http.client.IncompleteRead(b"")
        with self.assertRaises(StorageError):
            object_storage._Body(Mock(), broken, 10).read()
        with self.assertRaises(StorageError):
            S3Storage._finish(broken)

    def test_an_https_endpoint_is_verified(self):
        os.environ["ASTRA_S3_ENDPOINT"] = "https://bucket.example.com"
        storage = storage_named("s3")
        with patch("astra.object_storage.http.client.HTTPSConnection") as connect_https:
            storage._connect()
            storage._connect("objectstorage.example.com")
        for call in connect_https.call_args_list:
            context = call.kwargs["context"]
            self.assertEqual((context.verify_mode, context.check_hostname), (ssl.CERT_REQUIRED, True))
            self.assertEqual(call.kwargs["timeout"], object_storage.TIMEOUT_SECONDS)
        self.assertEqual([call.args[0] for call in connect_https.call_args_list],
                         ["bucket.example.com", "objectstorage.example.com"])


class ServiceOnObjectStorageTests(S3Fixture):
    """Item 6: authorization, metadata, integrity, audit and deletion are the service's and
    do not change with the backend."""

    def setUp(self):
        super().setUp()
        self.use("s3")

    def test_an_upload_goes_to_the_bucket_and_downloads_through_astra(self):
        attachment = self.upload()
        key = self.key(attachment)
        self.assertEqual(self.fake.objects, {key: PDF})
        self.assertEqual((self.in_folder(), self.leftovers()), ([], []))
        self.assertEqual(self.where(), {"report.pdf": ("s3", None)})
        row = self.db.execute("SELECT size_bytes, sha256 FROM task_attachments").fetchone()
        self.assertEqual((row["size_bytes"], row["sha256"]), (len(PDF), hashlib.sha256(PDF).hexdigest()))
        self.assertEqual(self.download(attachment), PDF)
        events = [row["event_type"] for row in self.db.execute("SELECT event_type FROM task_events ORDER BY rowid")]
        self.assertEqual(events[-2:], ["attachment_added", "attachment_downloaded"])
        # Where the bytes are kept never leaves the server.
        shown = json.dumps(self.service.task_detail(self.owner, self.task["id"]), default=str)
        for internal in ("storage_backend", "storage_previous", "storage_key", key):
            self.assertNotIn(internal, shown)

    def test_a_viewer_downloads_and_an_outsider_does_not(self):
        attachment = self.upload()
        viewer = self.service.create_user(self.owner, "viewer@example.org", "Viewer", "viewer password")
        self.service.grant_project_access(self.owner, self.project["id"], viewer["id"], "viewer")
        outsider = self.service.create_user(self.owner, "outsider@example.org", "Outsider", "outsider password")
        _, handle = self.service.open_task_file(viewer, self.task["id"], attachment["id"])
        with handle:
            self.assertEqual(handle.read(), PDF)
        self.fake.requests.clear()
        with self.assertRaises((KeyError, Forbidden)):
            self.service.open_task_file(outsider, self.task["id"], attachment["id"])
        self.assertEqual(self.fake.requests, [])  # refused before the bucket is asked

    def test_a_direct_link_serves_from_the_bucket(self):
        attachment = self.upload()
        link = self.service.create_direct_link(self.owner, self.task["id"], attachment["id"], confirm="direct_link")
        meta, handle = self.service.open_direct_link(link["url"].removeprefix("/files/"))
        with handle:
            self.assertEqual((handle.read(), meta["size_bytes"]), (PDF, len(PDF)))

    def test_removing_the_attachment_deletes_the_object(self):
        attachment = self.upload()
        self.service.remove_task_attachment(self.owner, self.task["id"], attachment["id"])
        self.assertEqual(self.fake.objects, {})

    def test_a_refused_file_never_reaches_the_bucket(self):
        with self.assertRaises(ValueError):
            self.upload(name="program.pdf", data=b"MZ" + b"x" * 100)
        self.assertEqual((self.fake.requests, self.leftovers()), ([], []))

    def test_storage_that_is_down_stores_no_row(self):
        self.fake.fault = lambda method, key: "500"
        with self.assertRaises(StorageError):
            self.upload()
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM task_attachments").fetchone()[0], 0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM task_events WHERE event_type='attachment_added'").fetchone()[0], 0)
        self.assertEqual(self.leftovers(), [])

    def test_a_database_failure_after_storing_removes_the_object(self):
        with patch.object(self.service, "_event", side_effect=RuntimeError("audit down")):
            with self.assertRaises(RuntimeError):
                self.upload()
        self.assertEqual(self.fake.objects, {})


class MigrationTests(S3Fixture):
    """Item 7: a change of backend copies, verifies size and SHA-256, updates metadata only
    after verification, supports rollback and never strands a file."""

    def migrate(self, target):
        return self.service.migrate_storage(target, VIA)

    def counts(self, result):
        return result["moved"], result["restored"], result["skipped"], len(result["failed"])

    def test_files_move_to_the_bucket_verified_and_the_old_copies_are_kept(self):
        first, second = self.upload("a.pdf"), self.upload("b.pdf", PDF + b"two")
        link = self.service.create_direct_link(self.owner, self.task["id"], first["id"], confirm="direct_link")
        self.use("s3")
        third = self.upload("c.pdf", PDF + b"three")  # every new upload goes to the active backend
        self.assertEqual(self.where(), {"a.pdf": ("folder", None), "b.pdf": ("folder", None), "c.pdf": ("s3", None)})
        self.assertEqual(self.download(first), PDF)  # a file not moved yet is read from where it is
        _, handle = self.service.open_direct_link(link["url"].removeprefix("/files/"))
        with handle:
            self.assertEqual(handle.read(), PDF)  # and so is its direct link
        self.assertEqual(self.service.storage_status(), {"active": "s3", "backends": [
            {"backend": "folder", "files": 2, "bytes": 2 * len(PDF) + 3, "old_copies_kept": 0},
            {"backend": "s3", "files": 1, "bytes": len(PDF) + 5, "old_copies_kept": 0}]})
        result = self.migrate("s3")
        self.assertEqual((result["target"], self.counts(result)), ("s3", (2, 0, 0, 0)))
        self.assertEqual(self.where(), {"a.pdf": ("s3", "folder"), "b.pdf": ("s3", "folder"), "c.pdf": ("s3", None)})
        self.assertEqual(self.fake.objects, {self.key(first): PDF, self.key(second): PDF + b"two",
                                             self.key(third): PDF + b"three"})
        self.assertEqual(self.in_folder(), sorted([self.key(first), self.key(second)]))  # kept for a rollback
        self.assertEqual([self.download(a) for a in (first, second, third)], [PDF, PDF + b"two", PDF + b"three"])
        self.assertEqual(self.service.storage_status()["backends"], [
            {"backend": "s3", "files": 3, "bytes": 3 * len(PDF) + 8, "old_copies_kept": 2}])
        self.assertEqual(self.leftovers(), [])  # the command's lock is gone
        # Audited on the primary owner's record, as a server command, and every owner is told.
        [detail] = self.user_events("storage_migrated")
        self.assertEqual(detail, {**VIA, "scope": "app", "target": "s3", "moved": 2, "restored": 0, "skipped": 0,
                                  "failed": 0, "failed_files": [], "interrupted": False})
        event = self.db.execute("SELECT * FROM user_events WHERE event_type='storage_migrated'").fetchone()
        self.assertEqual((event["target_user_id"], event["actor_user_id"], event["reason"]),
                         (self.owner["id"], self.owner["id"], "server command"))
        [notice] = self.db.execute("SELECT user_id, summary FROM notifications WHERE kind='storage_migrated'").fetchall()
        self.assertEqual(notice["user_id"], self.owner["id"])
        self.assertIn("2 copied and verified", notice["summary"])
        # Running it again finds nothing to do and records nothing.
        self.assertEqual(self.counts(self.migrate("s3")), (0, 0, 0, 0))
        self.assertEqual(len(self.user_events("storage_migrated")), 1)

    def test_rollback_returns_to_the_kept_copies_without_copying_them(self):
        old = self.upload("old.pdf")
        self.use("s3")
        self.migrate("s3")
        new = self.upload("new.pdf", PDF + b"new")  # uploaded after the switch: only in the bucket
        self.use("folder")
        self.fake.requests.clear()
        result = self.migrate("folder")
        self.assertEqual(self.counts(result), (1, 1, 0, 0))
        self.assertEqual(self.where(), {"old.pdf": ("folder", "s3"), "new.pdf": ("folder", "s3")})
        # The kept copy was verified where it lay; only the newer file was fetched from the bucket.
        self.assertEqual([(method, path) for method, path, _ in self.fake.requests],
                         [("GET", f"/astra-test/{self.key(new)}")])
        self.assertEqual((self.download(old), self.download(new)), (PDF, PDF + b"new"))
        self.assertEqual(self.in_folder(), sorted([self.key(old), self.key(new)]))
        self.assertEqual(len(self.fake.objects), 2)  # and the bucket's copies are kept in turn
        # Forward again: both kept copies in the bucket verify, nothing is uploaded.
        self.use("s3")
        self.fake.requests.clear()
        self.assertEqual(self.counts(self.migrate("s3")), (0, 2, 0, 0))
        self.assertEqual([method for method, _, _ in self.fake.requests], ["GET", "GET"])

    def test_a_kept_copy_that_no_longer_verifies_is_copied_again(self):
        attachment = self.upload()
        self.use("s3")
        self.migrate("s3")
        kept = self.uploads / "objects" / self.key(attachment)
        for damage in (lambda: kept.write_bytes(b"not the file"), kept.unlink):
            damage()
            self.use("folder")
            self.assertEqual(self.counts(self.migrate("folder")), (1, 0, 0, 0))
            self.assertEqual(kept.read_bytes(), PDF)
            self.use("s3")
            self.assertEqual(self.counts(self.migrate("s3")), (0, 1, 0, 0))

    def test_a_copy_that_cannot_be_verified_changes_nothing_and_is_removed(self):
        attachment = self.upload()
        key = self.key(attachment)
        self.use("s3")
        faults = (("PUT", "corrupt-store", "does not match"), ("PUT", "500", "HTTP 500"), ("PUT", "drop", "reached"),
                  ("GET", "corrupt-read", "does not match"), ("GET", "truncate", "download"),
                  ("GET", "500", "HTTP 500"))
        for method, fault, said in faults:
            self.fake.fault = lambda m, k, method=method, fault=fault: fault if m == method else None
            with self.subTest(method=method, fault=fault):
                result = self.migrate("s3")
                self.assertEqual(self.counts(result), (0, 0, 0, 1))
                [failure] = result["failed"]
                self.assertEqual((failure["attachment_id"], failure["display_name"]), (attachment["id"], "report.pdf"))
                self.assertIn(said, failure["error"])
                self.assertNotIn(self.fake.secret_key, failure["error"])
                self.assertEqual(self.where(), {"report.pdf": ("folder", None)})  # metadata untouched
                self.assertNotIn(key, self.fake.objects)  # the unverified copy is gone
                self.assertEqual(self.download(attachment), PDF)
        self.assertEqual([detail["failed"] for detail in self.user_events("storage_migrated")], [1] * len(faults))
        self.assertEqual(self.user_events("storage_migrated")[0]["failed_files"][0]["attachment_id"], attachment["id"])
        self.fake.fault = None
        self.assertEqual(self.counts(self.migrate("s3")), (1, 0, 0, 0))  # the same command, run again, finishes
        self.assertEqual(self.where(), {"report.pdf": ("s3", "folder")})

    def test_a_source_that_is_missing_altered_or_unrecorded_is_reported_and_never_moved(self):
        missing, altered, shorter, unrecorded, good = (self.upload(f"{name}.pdf", PDF + name.encode())
                                                       for name in ("missing", "altered", "shorter", "unrecorded", "good"))
        objects = self.uploads / "objects"
        (objects / self.key(missing)).unlink()
        (objects / self.key(altered)).write_bytes(PDF + b"ALTERED")
        (objects / self.key(shorter)).write_bytes(PDF)
        self.db.execute("UPDATE task_attachments SET sha256=NULL WHERE id=?", (unrecorded["id"],))
        self.use("s3")
        result = self.migrate("s3")
        self.assertEqual(self.counts(result), (1, 0, 0, 4))
        said = {failure["display_name"]: failure["error"] for failure in result["failed"]}
        self.assertIn("missing from the folder backend", said["missing.pdf"])
        # The message names the copy that is wrong: the source, before the bucket is even read back.
        for name in ("altered.pdf", "shorter.pdf"):
            self.assertIn("the copy on the folder backend does not match the recorded size and SHA-256", said[name])
        self.assertIn("no size and SHA-256 were recorded", said["unrecorded.pdf"])
        where = self.where()
        self.assertEqual(where.pop("good.pdf"), ("s3", "folder"))
        self.assertEqual(set(where.values()), {("folder", None)})
        self.assertEqual(self.fake.objects, {self.key(good): PDF + b"good"})

    def test_the_target_is_the_active_backend_and_nothing_else(self):
        self.upload()
        with self.assertRaisesRegex(ValueError, "ASTRA_STORAGE_BACKEND=s3 and restart Astra first"):
            self.migrate("s3")  # the installation is still set to the folder
        for wrong in ("tape", "", None):
            with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                self.migrate(wrong)
        self.assertEqual(self.where(), {"report.pdf": ("folder", None)})
        self.assertEqual((self.user_events("storage_migrated"), self.leftovers(), self.fake.requests), ([], [], []))

    def test_a_file_removed_while_it_is_copied_leaves_no_orphan(self):
        attachment = self.upload()
        self.use("s3")

        def verify_then_remove(storage, row):
            # The copy is in the bucket and verified; the owner removes the attachment just
            # before the row would be switched over.
            AstraService._verify_stored(storage, row)
            self.service.remove_task_attachment(self.owner, self.task["id"], attachment["id"])
        with patch.object(self.service, "_verify_stored", verify_then_remove):
            result = self.migrate("s3")
        self.assertEqual(self.counts(result), (0, 0, 1, 0))
        self.assertEqual((self.fake.objects, self.in_folder(), self.where()), ({}, [], {}))
        self.assertEqual(self.user_events("storage_migrated"), [])

    def test_an_interrupted_move_is_recorded_and_can_be_finished(self):
        first, second = self.upload("a.pdf"), self.upload("b.pdf", PDF + b"b")
        self.use("s3")
        real_move = self.service._move_upload

        def move_then_stop(row, destination):
            if row["id"] == second["id"]:
                raise KeyboardInterrupt
            return real_move(row, destination)
        with patch.object(self.service, "_move_upload", move_then_stop):
            with self.assertRaises(KeyboardInterrupt):
                self.migrate("s3")
        self.assertEqual(self.where(), {"a.pdf": ("s3", "folder"), "b.pdf": ("folder", None)})
        [detail] = self.user_events("storage_migrated")
        self.assertEqual((detail["moved"], detail["failed"], detail["interrupted"]), (1, 0, True))
        [notice] = self.db.execute("SELECT summary FROM notifications WHERE kind='storage_migrated'").fetchall()
        self.assertIn("interrupted before it finished", notice["summary"])
        self.assertEqual(self.leftovers(), [])  # the lock is released
        self.assertEqual(self.counts(self.migrate("s3")), (1, 0, 0, 0))
        self.assertEqual([d["interrupted"] for d in self.user_events("storage_migrated")], [True, False])
        # An interruption before anything was done leaves nothing to record.
        self.use("folder")
        with patch.object(self.service, "_move_upload", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.migrate("folder")
        self.assertEqual(len(self.user_events("storage_migrated")), 2)

    def once(self, wrapper):
        """Patch the service's transaction() so that its first use goes through ``wrapper``."""
        real, used = service_module.transaction, []

        @contextlib.contextmanager
        def first_time_only(db):
            used.append(db)
            with (wrapper(real, db) if len(used) == 1 else real(db)):
                yield
        return patch("astra.service.transaction", first_time_only)

    def other_connection(self, query):
        """What another connection sees: only what was really committed."""
        other = connect(Path(self.temp.name) / "astra.sqlite3")
        try:
            return [tuple(row) for row in other.execute(query)]
        finally:
            other.close()

    def test_an_interrupt_just_after_a_row_is_committed_keeps_the_copy_the_row_names(self):
        attachment = self.upload()
        self.use("s3")

        @contextlib.contextmanager
        def commit_then_interrupt(real, db):
            with real(db):
                yield
            raise KeyboardInterrupt  # the commit has happened; Ctrl-C lands right after it
        with self.once(commit_then_interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.migrate("s3")
        self.assertEqual(self.where(), {"report.pdf": ("s3", "folder")})
        self.assertEqual(self.fake.objects, {self.key(attachment): PDF})  # the row names it: it is kept
        self.assertEqual(self.download(attachment), PDF)
        self.assertEqual(self.service.verify_storage(), {"verified": 1, "failed": []})
        # And the file the interrupt landed on is counted in what is recorded.
        self.assertEqual(self.other_connection(
            "SELECT json_extract(detail_json,'$.moved'), json_extract(detail_json,'$.interrupted')"
            " FROM user_events WHERE event_type='storage_migrated'"), [(1, 1)])
        self.assertEqual(self.leftovers(), [])

    def test_an_interrupt_inside_a_rows_transaction_changes_nothing_and_loses_no_record(self):
        first, second = self.upload("a.pdf"), self.upload("b.pdf", PDF + b"b")
        self.use("s3")
        real, used = service_module.transaction, []

        @contextlib.contextmanager
        def interrupt_the_second(db):
            used.append(db)
            with real(db):
                yield
                if len(used) == 2:
                    raise KeyboardInterrupt  # the UPDATE ran; the commit never does
        with patch("astra.service.transaction", interrupt_the_second):
            with self.assertRaises(KeyboardInterrupt):
                self.migrate("s3")
        self.assertFalse(self.db.in_transaction)
        committed = dict(self.other_connection("SELECT display_name, storage_backend FROM task_attachments"))
        self.assertEqual(committed, {"a.pdf": "s3", "b.pdf": "folder"})
        self.assertEqual(self.fake.objects, {self.key(first): PDF})  # b's copy, named by no row, is gone
        self.assertEqual((self.download(first), self.download(second)), (PDF, PDF + b"b"))
        # The first file's move is in the history as another connection sees it: really committed.
        self.assertEqual(self.other_connection(
            "SELECT json_extract(detail_json,'$.moved'), json_extract(detail_json,'$.interrupted')"
            " FROM user_events WHERE event_type='storage_migrated'"), [(1, 1)])
        self.assertEqual(self.counts(self.migrate("s3")), (1, 0, 0, 0))

    def test_an_interrupted_prune_counts_the_file_it_had_finished(self):
        attachment = self.upload()
        self.use("s3")
        self.migrate("s3")

        @contextlib.contextmanager
        def commit_then_interrupt(real, db):
            with real(db):
                yield
            raise KeyboardInterrupt
        with self.once(commit_then_interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.service.prune_storage(VIA)
        self.assertEqual((self.where(), self.in_folder()), ({"report.pdf": ("s3", None)}, []))
        [detail] = self.user_events("storage_pruned")
        self.assertEqual((detail["pruned"], detail["interrupted"]), (1, True))
        self.assertEqual(self.download(attachment), PDF)

    def test_an_interrupt_inside_a_prunes_transaction_loses_no_record(self):
        first, second = self.upload("a.pdf"), self.upload("b.pdf", PDF + b"b")
        self.use("s3")
        self.migrate("s3")
        real, used = service_module.transaction, []

        @contextlib.contextmanager
        def interrupt_the_second(db):
            used.append(db)
            with real(db):
                yield
                if len(used) == 2:
                    raise KeyboardInterrupt  # the row was updated; the commit never happens
        with patch("astra.service.transaction", interrupt_the_second):
            with self.assertRaises(KeyboardInterrupt):
                self.service.prune_storage(VIA)
        self.assertFalse(self.db.in_transaction)
        # As committed: a's old copy is forgotten, b's is still named (its bytes are gone, so a
        # rollback would copy b back from the bucket), and a's prune is in the history.
        self.assertEqual(dict(self.other_connection("SELECT display_name, storage_previous FROM task_attachments")),
                         {"a.pdf": None, "b.pdf": "folder"})
        self.assertEqual(self.other_connection(
            "SELECT json_extract(detail_json,'$.pruned'), json_extract(detail_json,'$.interrupted')"
            " FROM user_events WHERE event_type='storage_pruned'"), [(1, 1)])
        self.assertEqual((self.download(first), self.download(second)), (PDF, PDF + b"b"))
        self.assertEqual(self.service.prune_storage(VIA)["pruned"], 1)  # the same command finishes it
        self.use("folder")
        self.assertEqual(self.counts(self.migrate("folder")), (2, 0, 0, 0))

    def test_a_kept_copy_is_never_overwritten_by_a_source_that_does_not_verify(self):
        attachment = self.upload()
        self.use("s3")
        self.migrate("s3")
        self.use("folder")
        self.migrate("folder")  # now in the folder, with the bucket copy kept
        self.assertEqual(self.where(), {"report.pdf": ("folder", "s3")})
        key = self.key(attachment)
        (self.uploads / "objects" / key).write_bytes(b"the folder copy went bad")
        self.use("s3")
        # The kept bucket copy is good but reads wrongly once, so it does not count as restored.
        reads = []

        def one_bad_read(method, k):
            reads.append(method)
            return "corrupt-read" if reads == ["GET"] else None
        self.fake.fault = one_bad_read
        result = self.migrate("s3")
        self.assertEqual(self.counts(result), (0, 0, 0, 1))
        self.assertIn("the copy on the folder backend does not match", result["failed"][0]["error"])
        self.assertEqual(self.fake.objects, {key: PDF})  # the one good copy was neither overwritten nor deleted
        self.assertNotIn("PUT", reads)
        self.assertEqual(self.counts(self.migrate("s3")), (0, 1, 0, 0))  # and it serves the file again
        self.assertEqual(self.download(attachment), PDF)

    def test_an_interrupt_while_a_file_is_copied_or_read_back_leaves_no_copy_behind(self):
        attachment = self.upload()
        self.use("s3")
        real_put, real_verify = S3Storage.put, AstraService._verify_stored

        def put_then_interrupt(storage, key, chunks):
            real_put(storage, key, chunks)
            raise KeyboardInterrupt  # the object is in the bucket; Ctrl-C lands before it is checked

        def verify_then_interrupt(storage, row):
            real_verify(storage, row)
            raise KeyboardInterrupt
        for patched in (patch.object(S3Storage, "put", put_then_interrupt),
                        patch.object(self.service, "_verify_stored", verify_then_interrupt)):
            with patched, self.assertRaises(KeyboardInterrupt) as stopped:
                self.migrate("s3")
            self.assertEqual((self.fake.objects, self.where()), ({}, {"report.pdf": ("folder", None)}))
            self.assertEqual(self.counts(stopped.exception.storage_result), (0, 0, 0, 0))
        self.assertEqual(self.user_events("storage_migrated"), [])
        # A bucket that is merely down is not asked to delete what it never took.
        self.fake.fault = lambda method, key: "500"
        with self.assertNoLogs("astra.attachments", level="ERROR"):
            self.assertEqual(self.counts(self.migrate("s3")), (0, 0, 0, 1))
        self.fake.fault = None
        self.assertEqual(self.counts(self.migrate("s3")), (1, 0, 0, 0))
        self.assertEqual(self.download(attachment), PDF)

    def test_a_second_interrupt_while_finishing_does_not_lose_the_record_of_earlier_files(self):
        self.upload("a.pdf"), self.upload("b.pdf", PDF + b"b")
        self.use("s3")
        real_move = self.service._move_upload

        def move_then_stop(row, destination):
            if row["display_name"] == "b.pdf":
                raise KeyboardInterrupt
            return real_move(row, destination)
        with patch.object(self.service, "_move_upload", move_then_stop), \
                patch.object(self.service, "_upload_is_on", side_effect=KeyboardInterrupt), \
                self.assertLogs("astra.attachments", level="ERROR"):
            with self.assertRaises(KeyboardInterrupt):
                self.migrate("s3")
        [detail] = self.user_events("storage_migrated")
        self.assertEqual((detail["moved"], detail["interrupted"]), (1, True))
        # A second Ctrl-C inside the history entry itself: the caller is told it is not recorded.
        self.assertEqual(self.counts(self.migrate("s3")), (1, 0, 0, 0))  # b follows; both now have a kept copy
        self.use("folder")
        with patch.object(self.service, "_move_upload", move_then_stop), \
                patch.object(self.service, "_storage_event", side_effect=KeyboardInterrupt), \
                self.assertLogs("astra.attachments", level="ERROR"):
            with self.assertRaises(KeyboardInterrupt) as stopped:
                self.migrate("folder")
        self.assertEqual((stopped.exception.storage_result["restored"], stopped.exception.storage_result["unrecorded"]),
                         (1, "KeyboardInterrupt"))
        # And after a run that finished: reported, not raised.
        with patch.object(self.service, "_storage_event", side_effect=KeyboardInterrupt), \
                self.assertLogs("astra.attachments", level="ERROR"):
            result = self.migrate("folder")
        self.assertEqual((result["restored"], result["unrecorded"]), (1, "KeyboardInterrupt"))

    def test_an_interrupt_while_a_failed_file_is_looked_up_stops_the_command(self):
        self.upload("a.pdf"), self.upload("b.pdf", PDF + b"b")
        self.use("s3")
        real_move = self.service._move_upload

        def fail_the_first(row, destination):
            if row["display_name"] == "a.pdf":
                raise ValueError("it could not be verified")
            return real_move(row, destination)
        with patch.object(self.service, "_move_upload", fail_the_first), \
                patch.object(self.service, "_upload_is_on", side_effect=KeyboardInterrupt), \
                self.assertLogs("astra.attachments", level="ERROR"):
            with self.assertRaises(KeyboardInterrupt):  # not swallowed: the command does not carry on to b
                self.migrate("s3")
        self.assertEqual(self.where(), {"a.pdf": ("folder", None), "b.pdf": ("folder", None)})
        self.assertEqual((self.fake.requests, self.leftovers()), ([], []))

    def test_an_error_raised_after_a_rows_commit_counts_the_file_as_moved(self):
        self.upload()
        self.use("s3")

        @contextlib.contextmanager
        def commit_then_error(real, db):
            with real(db):
                yield
            raise sqlite3.OperationalError("disk I/O error")  # after the commit went through
        with self.once(commit_then_error):
            result = self.migrate("s3")
        self.assertEqual(self.counts(result), (1, 0, 0, 0))
        self.assertEqual(self.where(), {"report.pdf": ("s3", "folder")})
        self.assertEqual(len(self.fake.objects), 1)

    def test_a_storage_command_refuses_to_run_inside_a_callers_transaction(self):
        self.upload()
        self.use("s3")
        self.db.execute("BEGIN IMMEDIATE")
        self.db.execute("UPDATE task_attachments SET note='the caller is in the middle of something'")
        for command in (lambda: self.migrate("s3"), lambda: self.service.prune_storage(VIA)):
            with self.assertRaisesRegex(RuntimeError, "inside an open database transaction"):
                command()
        self.assertTrue(self.db.in_transaction)  # the caller's work is not rolled back
        self.db.execute("COMMIT")
        self.assertEqual((self.where(), self.fake.requests, self.leftovers()),
                         ({"report.pdf": ("folder", None)}, [], []))

    def test_a_history_entry_that_cannot_be_written_does_not_hide_what_was_done(self):
        attachment = self.upload()
        self.use("s3")
        with patch.object(self.service, "_storage_event", side_effect=sqlite3.OperationalError("database is locked")):
            with self.assertLogs("astra.attachments", level="ERROR"):
                result = self.migrate("s3")
        self.assertEqual(self.counts(result), (1, 0, 0, 0))
        self.assertEqual(result["unrecorded"], "OperationalError: database is locked")
        self.assertEqual((self.where(), self.download(attachment)), ({"report.pdf": ("s3", "folder")}, PDF))
        self.assertEqual(self.leftovers(), [])
        # With no active owner at all there is nobody to record it on: the same answer.
        self.db.execute("UPDATE users SET active=0")
        with self.assertLogs("astra.attachments", level="ERROR"):
            result = self.service.prune_storage(VIA)
        self.assertEqual((result["pruned"], "no active owner" in result["unrecorded"]), (1, True))

    def test_a_lock_that_cannot_be_removed_does_not_hide_what_was_done(self):
        self.upload()
        self.use("s3")
        real_unlink = Path.unlink

        def unlink(target, *args, **kwargs):
            if target.name == "storage-command.lock":
                raise PermissionError("held by another program")
            return real_unlink(target, *args, **kwargs)
        with patch.object(Path, "unlink", unlink), self.assertLogs("astra.attachments", level="ERROR") as logs:
            result = self.migrate("s3")
        self.assertEqual(self.counts(result), (1, 0, 0, 0))
        self.assertNotIn("unrecorded", result)
        self.assertEqual(len(self.user_events("storage_migrated")), 1)
        self.assertIn("storage-command.lock could not be removed", logs.output[0])
        (self.uploads / "storage-command.lock").unlink()

    def test_the_record_sits_on_the_primary_owner_or_failing_that_on_an_active_owner(self):
        second = self.service.create_user(self.owner, "second@example.org", "Second", "second password")
        self.service.grant_secondary_owner(self.owner, second["id"], "backup owner")
        self.upload("a.pdf")
        self.use("s3")
        self.migrate("s3")
        self.db.execute("UPDATE users SET active=0 WHERE id=?", (self.owner["id"],))  # the primary is deactivated
        self.use("folder")
        self.migrate("folder")
        targets = [row["target_user_id"] for row in self.db.execute(
            "SELECT target_user_id FROM user_events WHERE event_type='storage_migrated' ORDER BY rowid")]
        self.assertEqual(targets, [self.owner["id"], second["id"]])

    def test_a_busy_database_fails_that_file_only_and_leaves_no_copy(self):
        attachment = self.upload()
        self.use("s3")
        real, calls = service_module.transaction, []

        @contextlib.contextmanager
        def busy_once(db):
            calls.append(db)
            if len(calls) == 1:
                raise sqlite3.OperationalError("database is locked")
            with real(db):
                yield
        with patch("astra.service.transaction", busy_once):
            result = self.migrate("s3")
        self.assertEqual(self.counts(result), (0, 0, 0, 1))
        self.assertIn("database is locked", result["failed"][0]["error"])
        self.assertEqual((self.where(), self.fake.objects), ({"report.pdf": ("folder", None)}, {}))
        self.assertEqual(self.user_events("storage_migrated")[0]["failed"], 1)
        self.assertEqual(self.counts(self.migrate("s3")), (1, 0, 0, 0))
        self.assertEqual(self.download(attachment), PDF)

    def test_a_row_that_changed_while_its_file_was_copied_is_left_as_it_is(self):
        attachment = self.upload()
        self.use("s3")

        def verify_then_change(storage, row):
            AstraService._verify_stored(storage, row)
            # As if something else had already finished this file, keeping no old copy.
            self.db.execute("UPDATE task_attachments SET storage_backend='s3', storage_previous=NULL WHERE id=?",
                            (attachment["id"],))
        with patch.object(self.service, "_verify_stored", verify_then_change):
            result = self.migrate("s3")
        self.assertEqual(self.counts(result), (0, 0, 1, 0))
        self.assertEqual(self.where(), {"report.pdf": ("s3", None)})  # not overwritten with a stale "previous"
        self.assertEqual(self.fake.objects, {self.key(attachment): PDF})  # and its bytes are not discarded

    def test_prune_deletes_nothing_when_the_row_changed_after_it_was_verified(self):
        attachment = self.upload()
        self.use("s3")
        self.migrate("s3")

        def verify_then_roll_back(storage, row):
            AstraService._verify_stored(storage, row)
            # As if a rollback had just made the folder copy the current one.
            self.db.execute("UPDATE task_attachments SET storage_backend='folder', storage_previous='s3' WHERE id=?",
                            (attachment["id"],))
        with patch.object(self.service, "_verify_stored", verify_then_roll_back):
            result = self.service.prune_storage(VIA)
        self.assertEqual((result["pruned"], result["skipped"], result["failed"]), (0, 1, []))
        self.assertEqual(self.in_folder(), [self.key(attachment)])  # the copy now in use was not deleted
        self.assertEqual(self.fake.objects, {self.key(attachment): PDF})
        self.assertEqual(self.where(), {"report.pdf": ("folder", "s3")})
        self.assertEqual(self.user_events("storage_pruned"), [])

    def test_a_removal_that_races_a_move_deletes_the_moved_copy_too(self):
        attachment = self.upload()
        self.use("s3")
        real = self.service._actor_transaction

        def move_first(actor, **kwargs):
            # The move commits after the removal read the row and before its transaction.
            with patch.object(self.service, "_actor_transaction", real):
                self.assertEqual(self.counts(self.migrate("s3")), (1, 0, 0, 0))
            return real(actor, **kwargs)
        with patch.object(self.service, "_actor_transaction", move_first):
            self.service.remove_task_attachment(self.owner, self.task["id"], attachment["id"])
        self.assertEqual((self.where(), self.fake.objects, self.in_folder()), ({}, {}, []))

    def test_every_file_can_be_read_back_and_checked_on_either_backend(self):
        good, altered, missing = self.upload("good.pdf"), self.upload("altered.pdf", PDF + b"a"), self.upload("gone.pdf")
        self.use("s3")
        in_bucket = self.upload("bucket.pdf", PDF + b"s3")
        self.assertEqual(self.service.verify_storage(), {"verified": 4, "failed": []})
        objects = self.uploads / "objects"
        (objects / self.key(altered)).write_bytes(b"something else")
        (objects / self.key(missing)).unlink()
        self.fake.objects[self.key(in_bucket)] = b"altered in the bucket"
        before = self.where()
        result = self.service.verify_storage()
        self.assertEqual(result["verified"], 1)
        said = {failure["display_name"]: failure["error"] for failure in result["failed"]}
        self.assertEqual(set(said), {"altered.pdf", "gone.pdf", "bucket.pdf"})
        self.assertIn("the copy on the folder backend does not match", said["altered.pdf"])
        self.assertIn("missing from the folder backend", said["gone.pdf"])
        self.assertIn("the copy on the s3 backend does not match", said["bucket.pdf"])
        self.assertEqual(self.where(), before)  # a check only: nothing is changed or recorded
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM user_events WHERE event_type LIKE 'storage%'")
                         .fetchone()[0], 0)

    def test_one_storage_command_runs_at_a_time(self):
        self.upload()
        self.use("s3")
        lock = self.uploads / "storage-command.lock"
        lock.write_text("held", encoding="utf-8")
        for command in (lambda: self.migrate("s3"), lambda: self.service.prune_storage(VIA)):
            with self.assertRaisesRegex(Conflict, "storage-command.lock"):
                command()
        self.assertEqual((self.where(), self.fake.requests), ({"report.pdf": ("folder", None)}, []))
        lock.unlink()
        # A command that dies part-way still lets the next one run.
        with patch.object(self.service, "_move_upload", side_effect=RuntimeError("power cut")):
            with self.assertRaises(RuntimeError):
                self.migrate("s3")
        self.assertFalse(lock.exists())
        self.assertEqual(self.counts(self.migrate("s3")), (1, 0, 0, 0))
        with patch.object(self.service, "_verify_stored", side_effect=RuntimeError("power cut")):
            with self.assertRaises(RuntimeError):
                self.service.prune_storage(VIA)
        self.assertFalse(lock.exists())

    def test_prune_deletes_an_old_copy_only_after_the_current_one_verifies(self):
        sound, damaged = self.upload("sound.pdf"), self.upload("damaged.pdf", PDF + b"d")
        self.use("s3")
        self.migrate("s3")
        self.fake.objects[self.key(damaged)] = b"damaged in the bucket"
        result = self.service.prune_storage(VIA)
        self.assertEqual((result["pruned"], result["skipped"], len(result["failed"])), (1, 0, 1))
        self.assertEqual(result["failed"][0]["display_name"], "damaged.pdf")
        self.assertEqual(self.where(), {"sound.pdf": ("s3", None), "damaged.pdf": ("s3", "folder")})
        self.assertEqual(self.in_folder(), [self.key(damaged)])  # the only good copy of it is still here
        [detail] = self.user_events("storage_pruned")
        self.assertEqual((detail["pruned"], detail["failed"], detail["scope"], detail["via"]), (1, 1, "app", "cli"))
        # So the damaged file is not lost: the rollback takes it from the kept copy.
        self.use("folder")
        self.assertEqual(self.counts(self.migrate("folder")), (1, 1, 0, 0))
        self.assertEqual((self.download(sound), self.download(damaged)), (PDF, PDF + b"d"))
        # With nothing kept, prune has nothing to do and records nothing more.
        self.use("s3")
        self.migrate("s3")
        self.service.prune_storage(VIA)
        self.assertEqual(self.in_folder(), [])
        before = len(self.user_events("storage_pruned"))
        self.assertEqual(self.service.prune_storage(VIA), {"pruned": 0, "skipped": 0, "failed": []})
        self.assertEqual(len(self.user_events("storage_pruned")), before)

    def test_prune_keeps_the_old_copy_when_the_bucket_cannot_be_read(self):
        attachment = self.upload()
        self.use("s3")
        self.migrate("s3")
        self.fake.fault = lambda method, key: "500" if method == "GET" else None
        result = self.service.prune_storage(VIA)
        self.assertEqual((result["pruned"], len(result["failed"])), (0, 1))
        self.assertEqual((self.in_folder(), self.where()), ([self.key(attachment)], {"report.pdf": ("s3", "folder")}))

    def test_removing_a_migrated_file_deletes_both_copies(self):
        attachment = self.upload()
        self.use("s3")
        self.migrate("s3")
        self.service.remove_task_attachment(self.owner, self.task["id"], attachment["id"])
        self.assertEqual((self.fake.objects, self.in_folder()), ({}, []))

    def test_every_owner_is_told_of_a_migration(self):
        second = self.service.create_user(self.owner, "second@example.org", "Second", "second password")
        self.service.grant_secondary_owner(self.owner, second["id"], "backup owner")
        self.upload()
        self.use("s3")
        self.migrate("s3")
        told = sorted(row["user_id"] for row in self.db.execute(
            "SELECT user_id FROM notifications WHERE kind='storage_migrated'"))
        self.assertEqual(told, sorted([self.owner["id"], second["id"]]))


class HttpOnObjectStorageTests(S3Fixture):
    """Both servers stream an object storage download and answer 503 when storage is down."""

    def setUp(self):
        super().setUp()
        self.use("s3")
        self.db.execute("UPDATE users SET must_change_password=0")
        self.server = AstraServer(("127.0.0.1", 0))
        self.addCleanup(self.server.server_close)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(self.server.shutdown)
        self.app = create_wsgi_app(Path(self.temp.name) / "astra.sqlite3")

    def http(self, method, path, body=b"", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def wsgi(self, method, path, body=b"", headers=None):
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "", "SERVER_PROTOCOL": "HTTP/1.1",
                   "wsgi.input": io.BytesIO(body), "CONTENT_LENGTH": str(len(body)), "REMOTE_ADDR": "127.0.0.1"}
        for name, value in (headers or {}).items():
            environ["HTTP_" + name.upper().replace("-", "_")] = value
        captured = {}
        chunks = self.app(environ, lambda status, hdrs: captured.update(status=int(status[:3]), headers=dict(hdrs)))
        try:
            return captured["status"], captured["headers"], b"".join(chunks)
        finally:
            getattr(chunks, "close", lambda: None)()

    def test_upload_and_download_round_trip_and_a_storage_outage_on_both_servers(self):
        data = b"%PDF-" + os.urandom(3 * storage_module.CHUNK_BYTES)
        login = json.dumps({"email": "owner@example.org", "password": "correct horse battery"}).encode()
        for name, call in (("development", self.http), ("waitress adapter", self.wsgi)):
            with self.subTest(server=name), contextlib.redirect_stderr(io.StringIO()):
                self.fake.fault = None
                status, headers, body = call("POST", "/api/login", login, {"Content-Type": "application/json"})
                self.assertEqual(status, 200)
                session = {"Cookie": headers["Set-Cookie"].split(";", 1)[0], "X-CSRF-Token": json.loads(body)["csrf"]}
                upload = {**session, "Content-Type": "application/pdf", "X-Filename": "big.pdf"}
                files = f"/api/tasks/{self.task['id']}/files"
                status, _, body = call("POST", files, data, upload)
                self.assertEqual(status, 201, body)
                attachment = json.loads(body)["attachment"]
                self.assertNotIn("storage_backend", attachment)
                self.assertIn(data, self.fake.objects.values())
                download = f"/api/tasks/{self.task['id']}/attachments/{attachment['id']}/download"
                status, headers, body = call("GET", download, headers=session)
                self.assertEqual((status, body), (200, data))
                self.assertEqual(headers["Content-Length"], str(len(data)))
                self.assertEqual(headers["Cache-Control"], "private, no-store")
                # Storage down: a plain 503, the detail only in the operator's log, nothing stored.
                rows = self.db.execute("SELECT COUNT(*) FROM task_attachments").fetchone()[0]
                self.fake.fault = lambda method, key: "500"
                for method, path, sent, sent_headers in (("GET", download, b"", session), ("POST", files, data, upload)):
                    with self.assertLogs("astra.attachments", level="ERROR") as logs:
                        status, _, body = call(method, path, sent, sent_headers)
                    self.assertEqual(status, 503, body)
                    self.assertEqual(json.loads(body), {"error": "File storage is not available right now. Try again later."})
                    self.assertIn("HTTP 500 InternalError", logs.output[0])
                self.assertEqual(self.db.execute("SELECT COUNT(*) FROM task_attachments").fetchone()[0], rows)


    def test_a_download_the_bucket_cuts_short_is_never_padded_with_an_error_page(self):
        data = b"%PDF-" + os.urandom(3 * storage_module.CHUNK_BYTES)
        attachment = self.service.add_task_file(self.owner, self.task["id"], "big.pdf", "", io.BytesIO(data), len(data))
        login = json.dumps({"email": "owner@example.org", "password": "correct horse battery"}).encode()
        download = f"/api/tasks/{self.task['id']}/attachments/{attachment['id']}/download"
        self.fake.fault = lambda method, key: "truncate" if method == "GET" else None
        # Development server: the connection ends short of the promised length.
        with contextlib.redirect_stderr(io.StringIO()):
            _, headers, _ = self.http("POST", "/api/login", login, {"Content-Type": "application/json"})
            connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
            try:
                with self.assertLogs("astra.attachments", level="ERROR") as logs:
                    connection.request("GET", download, headers={"Cookie": headers["Set-Cookie"].split(";", 1)[0]})
                    response = connection.getresponse()
                    self.assertEqual((response.status, response.getheader("Content-Length")), (200, str(len(data))))
                    try:
                        received = response.read()
                    except http.client.IncompleteRead as short:
                        received = short.partial
            finally:
                connection.close()
        self.assertLess(len(received), len(data))
        self.assertEqual(received, data[:len(received)])  # only bytes of the file, no error text after them
        self.assertNotIn(b"503", received[-200:])
        self.assertIn("a download stopped part-way", logs.output[0])
        # Waitress adapter: the failure reaches the server, which cuts the connection.
        environ = {"REQUEST_METHOD": "GET", "PATH_INFO": download, "QUERY_STRING": "", "SERVER_PROTOCOL": "HTTP/1.1",
                   "wsgi.input": io.BytesIO(), "CONTENT_LENGTH": "0", "REMOTE_ADDR": "127.0.0.1",
                   "HTTP_COOKIE": headers["Set-Cookie"].split(";", 1)[0]}
        chunks = self.app(environ, lambda status, hdrs: None)
        try:
            with self.assertRaises(StorageError):
                b"".join(chunks)
        finally:
            chunks.close()

    def test_the_server_says_at_start_when_recorded_files_cannot_be_reached(self):
        self.upload()  # in the bucket
        path = Path(self.temp.name) / "astra.sqlite3"
        with self.assertNoLogs("astra.attachments", level="ERROR"):
            web._warn_unreadable_storage(path)
        for name in S3_NAMES:  # the installation goes back to the folder and the bucket settings are removed
            os.environ.pop(name)
        os.environ[STORAGE_BACKEND_ENV] = "folder"
        with self.assertLogs("astra.attachments", level="ERROR") as logs:
            web._warn_unreadable_storage(path)
        self.assertIn("1 uploaded files are recorded on the s3 backend, which cannot be used", logs.output[0])
        self.assertIn("ASTRA_S3_ENDPOINT", logs.output[0])
        # A failure of the look itself is logged, and the server starts all the same.
        with patch("astra.web.connect", side_effect=sqlite3.OperationalError("database is locked")):
            with self.assertLogs("astra.attachments", level="ERROR") as logs:
                web._warn_unreadable_storage(path)
        self.assertIn("could not look up where uploaded files are recorded", logs.output[0])
        # Both servers make the check when they start.
        with patch("astra.web._warn_unreadable_storage") as warned, patch("astra.web.AstraServer") as server, \
                patch("astra.web.create_wsgi_app") as app, patch("waitress.serve"), \
                patch("astra.web.DailyDigestScheduler"), contextlib.redirect_stdout(io.StringIO()):
            web.serve("127.0.0.1", 0)
            web.serve_waitress("127.0.0.1", 0)
        self.assertEqual([call.args[0] for call in warned.call_args_list],
                         [server.return_value.db_path, app.return_value.db_path])


class CommandTests(S3Fixture):
    """The operator's commands. The object storage key comes from the environment or a
    settings file, never from an argument, and is never printed."""

    def setUp(self):
        super().setUp()
        self.settings = Path(self.temp.name) / "storage.env"
        lines = ["# object storage for uploads", "", f"{STORAGE_BACKEND_ENV}=s3"]
        lines += [f'{name}="{value}"' if name.endswith("BUCKET") else f"{name}={value}"
                  for name, value in self.fake.env().items()]
        self.settings.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run_command(self, *argv):
        """(printed text, exit) where exit is None, a message or a status."""
        printed = io.StringIO()
        try:
            with contextlib.redirect_stdout(printed), patch.dict(os.environ):
                entry.main(list(argv))
        except SystemExit as stopped:
            return printed.getvalue(), stopped.code
        return printed.getvalue(), None

    def test_status_says_where_the_files_are(self):
        printed, stopped = self.run_command("storage-status")
        self.assertEqual((stopped, "Active backend: folder" in printed, "No uploaded files." in printed),
                         (None, True, True))
        self.upload()
        printed, _ = self.run_command("storage-status", "--settings-file", str(self.settings))
        self.assertIn("Active backend: s3", printed)
        self.assertIn(f"folder: 1 files, {len(PDF)} bytes  (not the active backend: run storage-migrate)", printed)

    def test_check_proves_a_backend_and_cleans_up(self):
        printed, stopped = self.run_command("storage-check")
        self.assertEqual((stopped, "folder: the test object was deleted. The backend is ready." in printed), (None, True))
        self.assertEqual((self.in_folder(), self.leftovers()), ([], []))
        printed, stopped = self.run_command("storage-check", "--settings-file", str(self.settings))
        self.assertIsNone(stopped, printed)
        self.assertIn("s3: a read without the key is refused (HTTP 403)", printed)
        self.assertIn("s3: the test object was deleted. The backend is ready.", printed)
        self.assertEqual(self.fake.objects, {})
        self.assertEqual([method for method, _, _ in self.fake.requests], ["PUT", "GET", "GET", "DELETE"])
        self.assertNotIn(self.fake.secret_key, printed)
        self.assertEqual(os.environ.get(STORAGE_BACKEND_ENV), None)  # the file's settings did not leak out

    def test_check_refuses_a_public_bucket(self):
        self.fake.public = True
        printed, stopped = self.run_command("storage-check", "--backend", "s3", "--settings-file", str(self.settings))
        self.assertIn("the bucket is PUBLIC", str(stopped))
        self.assertNotIn("ready", printed)
        self.assertEqual(self.fake.objects, {})  # the test object is removed all the same

    def test_check_keeps_its_verdict_when_the_test_object_cannot_be_deleted(self):
        self.fake.fault = lambda method, key: "403" if method == "DELETE" else None
        printed, stopped = self.run_command("storage-check", "--settings-file", str(self.settings))
        self.assertIn("cannot delete objects", str(stopped))
        self.assertIn("could not be deleted (Object storage refused the request (HTTP 403 AccessDenied).)", printed)
        self.assertNotIn("ready", printed)
        self.fake.public = True  # a public bucket whose key cannot delete: PUBLIC is still the verdict
        printed, stopped = self.run_command("storage-check", "--settings-file", str(self.settings))
        self.assertIn("the bucket is PUBLIC", str(stopped))
        self.assertIn("could not be deleted", printed)

    def test_verify_reads_every_file_back(self):
        kept, damaged = self.upload("kept.pdf"), self.upload("damaged.pdf", PDF + b"d")
        printed, stopped = self.run_command("storage-verify")
        self.assertEqual((stopped, "Verified 2 uploaded files; 0 failed." in printed), (None, True))
        (self.uploads / "objects" / self.key(damaged)).write_bytes(b"not it")
        printed, stopped = self.run_command("storage-verify", "--settings-file", str(self.settings))
        self.assertEqual(stopped, 1)
        self.assertIn("Verified 1 uploaded files; 1 failed.", printed)
        self.assertIn(f"  FAILED damaged.pdf ({damaged['id']}): the copy on the folder backend does not match", printed)

    def test_an_interrupted_command_says_what_is_true(self):
        self.upload()
        with patch.object(AstraService, "migrate_storage", side_effect=KeyboardInterrupt):
            _, stopped = self.run_command("storage-migrate", "--to", "s3", "--settings-file", str(self.settings))
        self.assertTrue(str(stopped).startswith("Interrupted. Files already handled stay as they are"), stopped)
        for nothing_started in (EOFError, KeyboardInterrupt):  # stopped at the prompt
            with patch("builtins.input", side_effect=nothing_started):
                _, stopped = self.run_command("storage-prune")
            self.assertEqual(str(stopped), "Aborted; nothing was changed.")
        with patch.object(AstraService, "prune_storage", side_effect=KeyboardInterrupt):
            _, stopped = self.run_command("storage-prune", "--yes")
        self.assertTrue(str(stopped).startswith("Interrupted. Files already handled stay as they are"), stopped)
        self.assertTrue(str(stopped).endswith("The owner history shows what was recorded."), stopped)
        # Interrupted, and the history entry could not be written either: the command says so,
        # and lists the files that had failed before it was stopped.
        self.upload("b.pdf", PDF + b"b")

        def fail_then_stop(service, row, destination):
            if row["display_name"] == "report.pdf":
                raise ValueError("it could not be verified")
            raise KeyboardInterrupt
        with patch.object(AstraService, "_move_upload", fail_then_stop), \
                patch.object(AstraService, "_storage_event", side_effect=sqlite3.OperationalError("database is locked")), \
                self.assertLogs("astra.attachments", level="ERROR"):
            printed, stopped = self.run_command("storage-migrate", "--to", "s3", "--settings-file", str(self.settings))
        self.assertIn("  FAILED report.pdf", printed)
        self.assertIn("Before it was stopped: 0 moved, 0 restored, 0 skipped, 1 failed.", printed)
        self.assertIn("It could NOT be RECORDED in the owner history (OperationalError: database is locked)", str(stopped))
        # With one file done before the interrupt, the count says so.
        real_move = AstraService._move_upload

        def move_then_stop(service, row, destination):
            if row["display_name"] == "b.pdf":
                raise KeyboardInterrupt
            return real_move(service, row, destination)
        with patch.object(AstraService, "_move_upload", move_then_stop):
            printed, stopped = self.run_command("storage-migrate", "--to", "s3", "--settings-file", str(self.settings))
        self.assertIn("Before it was stopped: 1 moved, 0 restored, 0 skipped, 0 failed.", printed)
        self.assertTrue(str(stopped).endswith("The owner history shows what was recorded."), stopped)

    def test_a_run_that_could_not_be_recorded_says_so_and_exits_1(self):
        self.upload()
        with patch.object(AstraService, "_storage_event", side_effect=sqlite3.OperationalError("database is locked")), \
                self.assertLogs("astra.attachments", level="ERROR"):
            printed, stopped = self.run_command("storage-migrate", "--to", "s3", "--settings-file", str(self.settings))
        self.assertEqual(stopped, 1)
        self.assertIn("Moved to s3: 1 copied and verified", printed)
        self.assertIn("NOT RECORDED in the owner history (OperationalError: database is locked)", printed)

    def test_check_reports_a_bucket_that_cannot_be_used(self):
        self.fake.fault = lambda method, key: "corrupt-read" if method == "GET" else None
        printed, stopped = self.run_command("storage-check", "--settings-file", str(self.settings))
        self.assertEqual(str(stopped), "File storage: the s3 backend returned different bytes than were written.")
        self.assertEqual(self.fake.objects, {})
        self.fake.fault = lambda method, key: "403"
        printed, stopped = self.run_command("storage-check", "--settings-file", str(self.settings))
        self.assertEqual(str(stopped), "File storage: Object storage refused the request (HTTP 403 AccessDenied).")
        printed, stopped = self.run_command("storage-check", "--backend", "s3")  # no settings at all
        self.assertTrue(str(stopped).startswith("File storage: Object storage is not configured: set ASTRA_S3_"))

    def test_a_settings_file_line_is_never_echoed(self):
        for text, line in (("ASTRA_S3_SECRET_ACCESS_KEY topsecretvalue\n", 1), ("# ok\nPATH=topsecretvalue\n", 2),
                           ("ASTRA_OK=1\nastra_lower=topsecretvalue\n", 2),
                           ("ASTRA_OK=1\n\nASTRA_STORAGE_BACKEND\n", 3)):  # a name with no value
            self.settings.write_text(text, encoding="utf-8")
            printed, stopped = self.run_command("storage-status", "--settings-file", str(self.settings))
            with self.subTest(text=text):
                self.assertEqual(str(stopped), f"{self.settings}, line {line}: expected ASTRA_NAME=value.")
                self.assertNotIn("topsecretvalue", printed + str(stopped))
        _, stopped = self.run_command("storage-status", "--settings-file", str(self.settings) + ".missing")
        self.assertTrue(str(stopped).startswith("Could not read the settings file "))

    def test_migrate_then_prune_from_the_command_line(self):
        attachment = self.upload()
        printed, stopped = self.run_command("storage-migrate", "--to", "s3")  # the folder is still active
        self.assertIn("ASTRA_STORAGE_BACKEND=s3", str(stopped))
        printed, stopped = self.run_command("storage-migrate", "--to", "s3", "--settings-file", str(self.settings))
        self.assertIsNone(stopped, printed)
        self.assertIn("Moved to s3: 1 copied and verified, 0 switched back to a kept copy, 0 skipped, 0 failed.", printed)
        self.assertIn("The old copies are kept.", printed)
        self.assertEqual(self.where(), {"report.pdf": ("s3", "folder")})
        [detail] = self.user_events("storage_migrated")
        self.assertEqual((detail["via"], detail["moved"]), ("cli", 1))
        self.assertTrue(detail["host"])
        with patch("builtins.input", return_value="no"):
            _, stopped = self.run_command("storage-prune", "--settings-file", str(self.settings))
        self.assertEqual((str(stopped), self.in_folder()), ("Confirmation did not match; nothing was changed.",
                                                           [self.key(attachment)]))
        with patch("builtins.input", return_value="prune"):
            printed, stopped = self.run_command("storage-prune", "--settings-file", str(self.settings))
        self.assertEqual((stopped, self.in_folder()), (None, []))
        self.assertIn("Old copies removed: 1; 0 skipped; 0 failed.", printed)

    def test_a_failed_file_is_listed_and_the_command_exits_1(self):
        attachment = self.upload()
        self.fake.fault = lambda method, key: "corrupt-store" if method == "PUT" else None
        printed, stopped = self.run_command("storage-migrate", "--to", "s3", "--settings-file", str(self.settings))
        self.assertEqual(stopped, 1)
        self.assertIn("0 copied and verified, 0 switched back to a kept copy, 0 skipped, 1 failed.", printed)
        self.assertIn(f"  FAILED report.pdf ({attachment['id']}): the copy on the s3 backend does not match", printed)
        self.assertNotIn("The old copies are kept.", printed)
        self.assertEqual(self.where(), {"report.pdf": ("folder", None)})

    def test_the_commands_need_an_existing_database(self):
        with patch.dict(os.environ, {"ASTRA_HOME": str(Path(self.temp.name) / "elsewhere")}):
            for command in (["storage-status"], ["storage-migrate", "--to", "folder"], ["storage-prune", "--yes"]):
                _, stopped = self.run_command(*command)
                with self.subTest(command=command):
                    self.assertIn("No Astra database at", str(stopped))


if __name__ == "__main__":
    unittest.main()
