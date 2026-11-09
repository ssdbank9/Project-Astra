"""MXY7BG slice 1: HTTPS links, managed uploads to the private folder, audited streamed
downloads, and no local path shown where path links are off (Owner Items 5-14 on 6G89SJ;
Aly's 2026-11-08 choices on MXY7BG)."""
import hashlib
import http.client
import io
import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

from astra import attachment_storage as storage_module
from astra.attachment_storage import (
    DEFAULT_UPLOAD_LIMIT, FolderStorage, UploadTooLarge, check_upload, clean_filename, validate_https_url,
)
from astra.db import connect
from astra.service import AstraService, Conflict, Forbidden
from astra.web import AstraServer, RequestBodyTimeout, _TimedReader, _content_disposition, create_wsgi_app
from link_roots import allow_attachment_roots

PDF = b"%PDF-1.7\n" + b"x" * 1000
ROOTS_ENV = "ASTRA_ATTACHMENT_ROOTS"


class RefusingStream:
    """A request body that must never be read."""

    def read(self, size):
        raise AssertionError("the body was read")


def no_path_links(test):
    patcher = patch.dict(os.environ)
    patcher.start()
    test.addCleanup(patcher.stop)
    os.environ.pop(ROOTS_ENV, None)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.uploads = Path(self.temp.name) / "uploads"
        patcher = patch.dict(os.environ, {"ASTRA_UPLOAD_ROOT": str(self.uploads)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.db = connect(Path(self.temp.name) / "astra.sqlite3")
        self.addCleanup(self.db.close)
        self.service = AstraService(self.db)
        self.owner = self.service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")
        self.project = self.service.create_project(self.owner, "Hosted")
        self.task = self.service.create_task(self.owner, {"project_id": self.project["id"], "title": "Deliver"})

    def user(self, key, project_role=None, role="member"):
        created = self.service.create_user(self.owner, f"{key}@example.org", key.title(), f"{key} password", role)
        if project_role:
            self.service.grant_project_access(self.owner, self.project["id"], created["id"], project_role)
        return created

    def upload(self, actor, name="report.pdf", data=PDF, declared="application/pdf", **kw):
        return self.service.add_task_file(actor, self.task["id"], name, declared, io.BytesIO(data), len(data), **kw)

    def events(self, kind):
        return self.db.execute(
            "SELECT * FROM task_events WHERE task_id=? AND event_type=? ORDER BY rowid", (self.task["id"], kind)
        ).fetchall()

    def stored_files(self):
        return sorted(p.name for p in self.uploads.rglob("*") if p.is_file())


class LinkTests(Fixture):
    def test_owner_attaches_an_https_link_that_is_never_fetched(self):
        def refuse(*args, **kwargs):
            raise AssertionError("Astra tried to reach the link")
        with patch.object(urllib.request, "urlopen", refuse), patch.object(socket, "create_connection", refuse), \
                patch.object(socket, "getaddrinfo", refuse):
            link = self.service.add_task_link(self.owner, self.task["id"], " https://example.org/doc?id=7#p2 ",
                                              "Spec", "v2")
        self.assertEqual((link["kind"], link["url"], link["display_name"], link["path"]),
                         ("link", "https://example.org/doc?id=7#p2", "Spec", ""))
        self.assertIsNone(link["exists"])
        [event] = self.events("attachment_added")
        self.assertEqual(json.loads(event["after_json"])["url"], "https://example.org/doc?id=7#p2")

    def test_every_unsafe_or_malformed_link_is_refused(self):
        for url in ("http://example.org/a", "ftp://example.org/a", "javascript:alert(1)", "file:///etc/passwd",
                    "data:text/html,x", "https://user:pw@example.org/", "https://user@example.org/", "https://",
                    "https:///path", "https://exa mple.org/", "https://example.org/\u202e", "https://ex\x00.org",
                    "https://example.org:99999/", "https://.example.org/", "https://a..b/", "//example.org/x",
                    "https://example.org/" + "a" * 2048, "", None, 7):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_https_url(url)
        self.assertEqual(validate_https_url("HTTPS://Example.org:8443/x"), "HTTPS://Example.org:8443/x")

    def test_only_the_app_owner_attaches_links_and_attempts_are_audited(self):
        manager = self.user("manager", "manager")
        with self.assertRaises(Forbidden):
            self.service.add_task_link(manager, self.task["id"], "https://example.org/")
        [blocked] = self.events("attachment_add_blocked")
        self.assertEqual(json.loads(blocked["after_json"])["kind"], "link")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM task_attachments").fetchone()[0], 0)


class UploadTests(Fixture):
    def test_owner_upload_is_stored_privately_with_size_and_sha256(self):
        attachment = self.upload(self.owner)
        self.assertEqual((attachment["kind"], attachment["display_name"], attachment["size_bytes"]),
                         ("file", "report.pdf", len(PDF)))
        self.assertEqual(attachment["sha256"], hashlib.sha256(PDF).hexdigest())
        self.assertNotIn("storage_key", attachment)
        key = self.db.execute("SELECT storage_key FROM task_attachments").fetchone()[0]
        self.assertEqual((self.uploads / "objects" / key).read_bytes(), PDF)
        self.assertEqual(list((self.uploads / "incoming").iterdir()), [])

    def test_a_large_upload_is_written_in_chunks_not_held_in_memory(self):
        data = b"%PDF-" + os.urandom(3 * storage_module.CHUNK_BYTES)
        writes = []
        real_open = open

        def spying_open(path, mode="r", *args, **kwargs):
            handle = real_open(path, mode, *args, **kwargs)
            if "x" in mode:
                original = handle.write
                handle.write = lambda chunk: (writes.append(len(chunk)), original(chunk))[1]
            return handle
        with patch("builtins.open", spying_open):
            self.upload(self.owner, data=data)
        self.assertGreater(len(writes), 1)
        self.assertLessEqual(max(writes), storage_module.HEAD_BYTES)

    def test_an_oversized_upload_is_refused_before_its_body_is_read(self):
        with self.assertRaises(UploadTooLarge):
            self.service.add_task_file(self.owner, self.task["id"], "big.pdf", "application/pdf",
                                       RefusingStream(), DEFAULT_UPLOAD_LIMIT + 1)
        self.assertEqual(self.stored_files(), [])

    def test_a_body_that_does_not_match_its_length_is_refused_and_partials_are_removed(self):
        class Overlong(io.BytesIO):  # hands back more than was asked for
            def read(self, size=-1):
                return super().read(-1)
        data = PDF + b"z" * (2 * storage_module.HEAD_BYTES)
        with self.assertRaisesRegex(ValueError, "longer than it said"):
            self.service.add_task_file(self.owner, self.task["id"], "a.pdf", "", Overlong(data), len(PDF))
        with self.assertRaises(ValueError):  # a short body
            self.service.add_task_file(self.owner, self.task["id"], "a.pdf", "", io.BytesIO(PDF[:10]), len(PDF))
        self.assertEqual(self.stored_files(), [])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM task_attachments").fetchone()[0], 0)

    def test_a_failure_after_the_head_removes_the_partial_file(self):
        class Breaks(io.BytesIO):
            def read(self, size=-1):
                if self.tell() >= storage_module.HEAD_BYTES:
                    raise OSError("connection dropped")
                return super().read(size)
        data = b"%PDF-" + b"y" * (storage_module.HEAD_BYTES * 2)
        with self.assertRaises(OSError):
            self.service.add_task_file(self.owner, self.task["id"], "a.pdf", "", Breaks(data), len(data))
        self.assertEqual(self.stored_files(), [])

    def test_dangerous_or_mismatched_files_are_refused_and_nothing_is_kept(self):
        iso = b"\0" * 0x8001 + b"CD001" + b"\0" * 10
        cases = {
            "setup.exe": (b"anything", ""),
            "addin.xll": (b"anything", ""),
            "component.sct": (b"<scriptlet/>", "text/plain"),
            "menu.desktop": (b"[Desktop Entry]", "text/plain"),
            "invoice.pdf.exe": (PDF, "application/pdf"),
            "run.exe.": (b"anything", ""),
            "notes.txt": (b"MZ\x90\x00 program", "text/plain"),
            "tool.txt": (b"\x7fELF binary", ""),
            "mac.dat": (b"\xcf\xfa\xed\xfe....", ""),
            "script.txt": (b"#!/bin/sh\nrm -rf /", "text/plain"),
            "fake.pdf": (b"not a pdf at all", "application/pdf"),
            "photo.png": (b"GIF89a....", "image/png"),
            "report.docx": (b"MZ....", ""),
            "disk.dat": (iso, ""),
            "macro.txt": (b"plain text", "application/x-msdownload"),
            "page.txt": (b"plain", "text/javascript; charset=utf-8"),
        }
        for name, (data, declared) in cases.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.upload(self.owner, name=name, data=data, declared=declared)
        self.assertEqual(self.stored_files(), [])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM task_attachments").fetchone()[0], 0)

    def test_ordinary_documents_are_accepted(self):
        for name, data in (("minutes.txt", b"Agreed: ship Friday."), ("budget.xlsx", b"PK\x03\x04rest"),
                           ("scan.jpg", b"\xff\xd8\xff\xe0rest"), ("data.csv", b"a,b\n1,2\n")):
            with self.subTest(name=name):
                self.assertEqual(self.upload(self.owner, name=name, data=data, declared="")["kind"], "file")

    def test_file_names_lose_folders_and_control_characters(self):
        self.assertEqual(clean_filename("C:\\Users\\aly\\..\\report.pdf"), "report.pdf")
        self.assertEqual(clean_filename("../../etc/pass\x00wd"), "passwd")
        self.assertEqual(clean_filename("a\u202egnp.exe"), "agnp.exe")
        for bad in ("", "..", "///", "\x00"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                clean_filename(bad)
        self.assertLessEqual(len(clean_filename("x" * 500 + ".pdf")), storage_module.MAX_FILENAME_LENGTH)
        self.assertTrue(clean_filename("x" * 500 + ".pdf").endswith(".pdf"))

    def test_only_the_app_owner_uploads_and_the_body_is_never_read_otherwise(self):
        for key, role in (("manager", "manager"), ("member", "member"), ("viewer", "viewer"), ("outsider", None)):
            actor = self.user(key, role)
            with self.subTest(role=key), self.assertRaises((Forbidden, KeyError)):
                self.service.add_task_file(actor, self.task["id"], "a.pdf", "", RefusingStream(), 10)
        self.assertEqual(len(self.events("attachment_add_blocked")), 3)  # the outsider cannot see the task
        self.assertEqual(self.stored_files(), [])

    def test_a_database_failure_after_storing_removes_the_stored_file(self):
        with patch.object(self.service, "_event", side_effect=RuntimeError("audit failed")):
            with self.assertRaises(RuntimeError):
                self.upload(self.owner)
        self.assertEqual(self.stored_files(), [])


class DownloadTests(Fixture):
    def test_a_viewer_downloads_and_each_download_is_audited(self):
        attachment = self.upload(self.owner)
        viewer = self.user("viewer", "viewer")
        meta, handle = self.service.open_task_file(viewer, self.task["id"], attachment["id"])
        with handle:
            self.assertEqual(handle.read(), PDF)
        self.assertEqual(meta["display_name"], "report.pdf")
        [event] = self.events("attachment_downloaded")
        self.assertEqual(event["actor_user_id"], viewer["id"])

    def test_an_outsider_is_refused_and_the_refusal_is_audited(self):
        attachment = self.upload(self.owner)
        outsider = self.user("outsider")
        with self.assertRaises((Forbidden, KeyError)):
            self.service.open_task_file(outsider, self.task["id"], attachment["id"])
        [event] = self.events("attachment_download_blocked")
        self.assertEqual(event["actor_user_id"], outsider["id"])
        self.assertEqual(self.events("attachment_downloaded"), [])

    def test_access_is_rechecked_on_every_download(self):
        attachment = self.upload(self.owner)
        viewer = self.user("viewer", "viewer")
        self.service.open_task_file(viewer, self.task["id"], attachment["id"])[1].close()
        self.db.execute("DELETE FROM memberships WHERE user_id=?", (viewer["id"],))
        with self.assertRaises((Forbidden, KeyError)):
            self.service.open_task_file(viewer, self.task["id"], attachment["id"])

    def test_links_paths_and_unknown_ids_have_nothing_to_download(self):
        link = self.service.add_task_link(self.owner, self.task["id"], "https://example.org/")
        # Storage must never be asked for a non-file attachment: the service refuses by kind,
        # not because the storage layer happens to reject an empty key.
        with patch("astra.service.active_storage", side_effect=AssertionError("storage consulted")):
            for attachment_id in (link["id"], "missing"):
                with self.subTest(attachment_id=attachment_id), self.assertRaises(KeyError):
                    self.service.open_task_file(self.owner, self.task["id"], attachment_id)
        self.assertEqual(self.events("attachment_downloaded"), [])

    def test_removing_a_file_attachment_deletes_its_bytes_unless_it_is_a_final_result(self):
        kept = self.upload(self.owner, name="kept.pdf")
        self.service.mark_final_result(self.owner, self.task["id"], "attachment", kept["id"], "")
        with self.assertRaises(Conflict):
            self.service.remove_task_attachment(self.owner, self.task["id"], kept["id"])
        gone = self.upload(self.owner, name="gone.pdf")
        self.assertEqual(len(self.stored_files()), 2)
        self.service.remove_task_attachment(self.owner, self.task["id"], gone["id"])
        self.assertEqual(len(self.stored_files()), 1)
        [removed] = self.events("attachment_removed")
        self.assertEqual(json.loads(removed["before_json"]), {"kind": "file", "display_name": "gone.pdf"})


    def test_final_results_name_a_file_and_carry_a_link(self):
        uploaded = self.upload(self.owner, name="deliverable.pdf")
        link = self.service.add_task_link(self.owner, self.task["id"], "https://example.org/report")
        self.service.mark_final_result(self.owner, self.task["id"], "attachment", uploaded["id"], "")
        self.service.mark_final_result(self.owner, self.task["id"], "attachment", link["id"], "")
        results = self.service.export_final_results(self.owner)["results"]
        shown = {r["attachment_kind"]: r["attachment_path"] for r in results}
        self.assertEqual(shown, {"file": "deliverable.pdf", "link": "https://example.org/report"})
        self.assertTrue(all(r["attachment_id"] for r in results))

    def test_the_import_template_carries_no_links_or_files(self):
        self.service.add_task_link(self.owner, self.task["id"], "https://example.org/")
        self.upload(self.owner)
        template, _, _ = self.service.import_template(self.owner, "csv", self.project["id"])
        self.assertNotIn("example.org", template.decode("utf-8"))
        tasks, *_ = self.service._template_prefill(
            self.owner, self.service._template_project(self.owner, self.project["id"]), self.service._import_config())
        self.assertEqual([task["attachment_links"] for task in tasks], [""])

    def test_a_failed_download_audit_closes_the_file(self):
        attachment = self.upload(self.owner)
        handles, real_open = [], FolderStorage.open

        def spy(storage, key):
            handles.append(real_open(storage, key))
            return handles[-1]
        with patch.object(FolderStorage, "open", spy), \
                patch.object(self.service, "_event", side_effect=RuntimeError("audit down")):
            with self.assertRaises(RuntimeError):
                self.service.open_task_file(self.owner, self.task["id"], attachment["id"])
        [handle] = handles  # held here, so only an explicit close() can have closed it
        self.assertTrue(handle.closed)

    def test_a_storage_error_after_removal_is_logged_not_raised(self):
        attachment = self.upload(self.owner)
        real = self.service.db.execute  # the row must still be deleted
        with patch.object(FolderStorage, "delete", side_effect=PermissionError("locked")):
            with self.assertLogs("astra.attachments", level="ERROR") as logs:
                self.service.remove_task_attachment(self.owner, self.task["id"], attachment["id"])
        self.assertIn("was not deleted", logs.output[0])
        self.assertEqual(real("SELECT COUNT(*) FROM task_attachments").fetchone()[0], 0)
        self.assertEqual(len(self.stored_files()), 1)


class GuardUnitTests(unittest.TestCase):
    def test_storage_keys_are_32_hex_characters_only(self):
        with tempfile.TemporaryDirectory() as root:
            store = FolderStorage(Path(root))
            for key in ("../astra.sqlite3", "objects/x", "A" * 32, "0" * 31, "", None):
                with self.subTest(key=key), self.assertRaises(KeyError):
                    store.open(key)
            with self.assertRaises(KeyError):
                store.open("0" * 32)  # well-formed but absent

    def test_a_stalled_upload_read_becomes_a_request_timeout(self):
        class Stalled:
            def read(self, size):
                raise TimeoutError("timed out")
        with self.assertRaises(RequestBodyTimeout):
            _TimedReader(Stalled()).read(10)
        self.assertEqual(_TimedReader(io.BytesIO(b"abc")).read(2), b"ab")

    def test_content_disposition_keeps_quotes_and_newlines_out_of_the_header(self):
        header = _content_disposition('a"b;c\\d\r\n.pdf')
        self.assertEqual(header.split("; filename*=")[0], 'attachment; filename="a_b_c_d__.pdf"')
        self.assertNotIn("\r", header)
        self.assertNotIn("\n", header)
        self.assertIn("filename*=UTF-8''a%22b%3Bc%5Cd%0D%0A.pdf", header)
        self.assertEqual(_content_disposition("").split(";")[1].strip(), 'filename="download"')

    def test_a_spanned_zip_matches_its_name(self):
        check_upload("parts.zip", "application/zip", b"PK\x07\x08" + b"\0" * 20)
        with self.assertRaisesRegex(ValueError, "do not match"):
            check_upload("parts.zip", "application/zip", b"not a zip")


class PathLinkHidingTests(Fixture):
    def setUp(self):
        super().setUp()
        allow_attachment_roots(self)
        self.linked_path = os.path.join(tempfile.gettempdir(), "astra-hidden.pdf")
        self.path_link = self.service.add_task_attachment(self.owner, self.task["id"], self.linked_path)

    def test_path_links_are_shown_on_a_desktop_install(self):
        [row] = self.service.list_task_attachments(self.owner, self.task["id"])
        self.assertEqual(row["path"], self.linked_path)

    def test_without_path_links_no_local_path_is_shown_or_exported(self):
        no_path_links(self)
        [row] = self.service.list_task_attachments(self.owner, self.task["id"])
        self.assertEqual((row["path"], row["path_hidden"], row["exists"]), ("", True, None))
        self.service.mark_final_result(self.owner, self.task["id"], "attachment", self.path_link["id"], "")
        [result] = self.service.export_final_results(self.owner)["results"]
        self.assertEqual(result["attachment_path"], "")
        task = self.service.get_task(self.owner, self.task["id"])
        self.assertNotIn(self.linked_path, json.dumps(task))
        # The stored row is untouched, so a desktop install still has it.
        self.assertEqual(self.db.execute("SELECT path FROM task_attachments").fetchone()[0], self.linked_path)

    def test_templates_carry_path_links_only(self):
        self.service.add_task_link(self.owner, self.task["id"], "https://example.org/")
        self.upload(self.owner)
        self.service.save_task_as_template(self.owner, self.task["id"], "T")
        [body] = self.db.execute("SELECT body_json FROM templates").fetchone()
        [task] = json.loads(body)["tasks"]
        self.assertEqual([a["path"] for a in task["attachments"]], [self.linked_path])


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.dict(os.environ, {"ASTRA_HOME": self.temp.name,
                                          "ASTRA_UPLOAD_ROOT": os.path.join(self.temp.name, "up")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.server = AstraServer(("127.0.0.1", 0))
        self.addCleanup(self.server.server_close)
        service = self.server.service
        self.owner = service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")
        self.project = service.create_project(self.owner, "Hosted")
        self.task = service.create_task(self.owner, {"project_id": self.project["id"], "title": "Deliver"})
        viewer = service.create_user(self.owner, "viewer@example.org", "Viewer", "viewer password")
        service.grant_project_access(self.owner, self.project["id"], viewer["id"], "viewer")
        service.create_user(self.owner, "outsider@example.org", "Outsider", "outsider password")
        self.db = service.db
        self.db.execute("UPDATE users SET must_change_password=0")
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(self.server.shutdown)

    def call(self, method, path, body=b"", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            return response, response.read()
        finally:
            connection.close()

    def login(self, email, password):
        response, body = self.call("POST", "/api/login", json.dumps({"email": email, "password": password}).encode(),
                                   {"Content-Type": "application/json"})
        self.assertEqual(response.status, 200)
        return response.getheader("Set-Cookie").split(";", 1)[0], json.loads(body)["csrf"]

    def post_file(self, session, data=PDF, name="Rapport été.pdf", csrf=True, extra=None):
        cookie, token = session
        headers = {"Cookie": cookie, "Content-Type": "application/pdf", "X-Filename": quote(name)}
        if csrf:
            headers["X-CSRF-Token"] = token if csrf is True else csrf
        headers.update(extra or {})
        return self.call("POST", f"/api/tasks/{self.task['id']}/files", data, headers)

    def test_upload_and_download_round_trip(self):
        owner = self.login("owner@example.org", "correct horse battery")
        response, body = self.post_file(owner)
        self.assertEqual(response.status, 201, body)
        attachment = json.loads(body)["attachment"]
        viewer = self.login("viewer@example.org", "viewer password")
        response, data = self.call("GET", f"/api/tasks/{self.task['id']}/attachments/{attachment['id']}/download",
                                   headers={"Cookie": viewer[0]})
        self.assertEqual((response.status, data), (200, PDF))
        self.assertEqual(response.getheader("Content-Type"), "application/octet-stream")
        self.assertEqual(response.getheader("Cache-Control"), "private, no-store")
        self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
        disposition = response.getheader("Content-Disposition")
        self.assertTrue(disposition.startswith("attachment;"))
        self.assertIn("filename*=UTF-8''Rapport%20%C3%A9t%C3%A9.pdf", disposition)

    def test_upload_needs_csrf_and_the_owner_and_stores_nothing_otherwise(self):
        owner = self.login("owner@example.org", "correct horse battery")
        for csrf in (False, "wrong"):
            response, _ = self.post_file(owner, csrf=csrf)
            self.assertEqual(response.status, 403)
        viewer = self.login("viewer@example.org", "viewer password")
        self.assertEqual(self.post_file(viewer)[0].status, 403)
        response, _ = self.call("POST", f"/api/tasks/{self.task['id']}/files", PDF,
                                {"Content-Type": "application/pdf", "X-Filename": "a.pdf"})
        self.assertEqual(response.status, 403)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM task_attachments").fetchone()[0], 0)

    def test_upload_rejections_answer_cleanly(self):
        owner = self.login("owner@example.org", "correct horse battery")
        response, body = self.post_file(owner, data=b"MZ program", name="a.txt")
        self.assertEqual(response.status, 400)
        self.assertIn("cannot be uploaded", json.loads(body)["error"])
        response, body = self.post_file(owner, extra={"Content-Length": str(DEFAULT_UPLOAD_LIMIT + 1)}, data=b"")
        self.assertEqual(response.status, 413)
        response, _ = self.post_file(owner, data=b"", name="empty.pdf")
        self.assertEqual(response.status, 400)

    def test_download_refusals(self):
        owner = self.login("owner@example.org", "correct horse battery")
        attachment = json.loads(self.post_file(owner)[1])["attachment"]
        url = f"/api/tasks/{self.task['id']}/attachments/{attachment['id']}/download"
        self.assertEqual(self.call("GET", url)[0].status, 403)  # signed out
        outsider = self.login("outsider@example.org", "outsider password")
        self.assertIn(self.call("GET", url, headers={"Cookie": outsider[0]})[0].status, (403, 404))
        missing = f"/api/tasks/{self.task['id']}/attachments/nope/download"
        self.assertEqual(self.call("GET", missing, headers={"Cookie": owner[0]})[0].status, 404)

    def test_links_over_http(self):
        owner = self.login("owner@example.org", "correct horse battery")
        headers = {"Cookie": owner[0], "X-CSRF-Token": owner[1], "Content-Type": "application/json"}
        path = f"/api/tasks/{self.task['id']}/links"
        response, body = self.call("POST", path, json.dumps({"url": "https://example.org/x"}).encode(), headers)
        self.assertEqual(response.status, 201)
        self.assertEqual(json.loads(body)["attachment"]["kind"], "link")
        response, _ = self.call("POST", path, json.dumps({"url": "http://example.org/x"}).encode(), headers)
        self.assertEqual(response.status, 400)
        no_csrf = {k: v for k, v in headers.items() if k != "X-CSRF-Token"}
        response, _ = self.call("POST", path, json.dumps({"url": "https://example.org/y"}).encode(), no_csrf)
        self.assertEqual(response.status, 403)


class WsgiStreamingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.dict(os.environ, {"ASTRA_HOME": self.temp.name,
                                          "ASTRA_UPLOAD_ROOT": os.path.join(self.temp.name, "up")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.db_path = Path(self.temp.name) / "astra.sqlite3"
        self.app = create_wsgi_app(self.db_path)
        db = connect(self.db_path)
        self.addCleanup(db.close)
        service = AstraService(db)
        owner = service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")
        project = service.create_project(owner, "Hosted")
        self.task = service.create_task(owner, {"project_id": project["id"], "title": "Deliver"})
        self.data = b"%PDF-" + os.urandom(5 * storage_module.CHUNK_BYTES)
        self.attachment = service.add_task_file(owner, self.task["id"], "big.pdf", "", io.BytesIO(self.data),
                                                len(self.data))

    def call(self, method, path, body=b"", headers=None):
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "",
                   "SERVER_PROTOCOL": "HTTP/1.1", "wsgi.input": io.BytesIO(body),
                   "CONTENT_LENGTH": str(len(body)), "REMOTE_ADDR": "127.0.0.1"}
        for name, value in (headers or {}).items():
            environ["HTTP_" + name.upper().replace("-", "_")] = value
        captured = {}
        body_iter = self.app(environ, lambda status, hdrs: captured.update(status=status, headers=dict(hdrs)))
        return captured, body_iter

    def login(self):
        status, body = self.call("POST", "/api/login", json.dumps(
            {"email": "owner@example.org", "password": "correct horse battery"}).encode(),
            {"Content-Type": "application/json"})
        return status["headers"]["Set-Cookie"].split(";", 1)[0], json.loads(b"".join(body))["csrf"]

    def test_an_upload_arrives_through_the_wsgi_adapter(self):
        cookie, csrf = self.login()
        data = b"%PDF-1.7 wsgi"
        environ_headers = {"Cookie": cookie, "X-CSRF-Token": csrf, "X-Filename": quote("Été.pdf"),
                           "X-Note": quote("via wsgi")}
        captured, body = self.call("POST", f"/api/tasks/{self.task['id']}/files", data, environ_headers)
        self.assertTrue(captured["status"].startswith("201"), b"".join(body))
        attachment = json.loads(b"".join(body))["attachment"]
        self.assertEqual((attachment["display_name"], attachment["note"], attachment["size_bytes"]),
                         ("Été.pdf", "via wsgi", len(data)))
        captured, _ = self.call("POST", f"/api/tasks/{self.task['id']}/files", b"MZ program", environ_headers)
        self.assertTrue(captured["status"].startswith("400"))

    def test_hosted_download_is_streamed_in_chunks(self):
        cookie, _ = self.login()
        captured, body_iter = self.call(
            "GET", f"/api/tasks/{self.task['id']}/attachments/{self.attachment['id']}/download", headers={"Cookie": cookie})
        self.assertTrue(captured["status"].startswith("200"))
        self.assertNotIsInstance(body_iter, list)
        chunks = list(body_iter)
        body_iter.close()
        self.assertGreater(len(chunks), 1)
        self.assertEqual(b"".join(chunks), self.data)
        self.assertEqual(captured["headers"]["Content-Length"], str(len(self.data)))


if __name__ == "__main__":
    unittest.main()
