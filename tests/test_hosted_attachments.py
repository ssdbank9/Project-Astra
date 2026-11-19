"""MXY7BG slice 1: HTTPS links, managed uploads to the private folder, audited streamed
downloads, and no local path shown where path links are off (Owner Items 5-14 on 6G89SJ;
Aly's 2026-11-08 choices on MXY7BG). Slice 2: the App Owner's upload limit and denylist
additions (Items 8-9). Slice 3: App Owner-only audited permanent direct links
(Items 15-16)."""
import contextlib
import hashlib
import http.client
import io
import json
import logging
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

from astra import attachment_storage as storage_module
from astra.attachment_storage import (
    DEFAULT_POLICY, DEFAULT_UPLOAD_LIMIT, HARD_UPLOAD_LIMIT, MB, FolderStorage, UploadPolicy, UploadTooLarge,
    check_upload, clean_filename, normalize_extension, normalize_mime_type, upload_ceiling, validate_https_url,
)
from astra.db import connect
from astra.service import AstraService, Conflict, Forbidden, NeedsConfirmation
from astra.web import (
    AstraServer, RequestBodyTimeout, _FileChunks, _TimedReader, _WSGIHandler, _content_disposition,
    _without_link_tokens, create_wsgi_app,
)
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
        with patch("astra.service.storage_named", side_effect=AssertionError("storage consulted")):
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


class DirectLinkTests(Fixture):
    """Slice 3 (Owner Items 15-16): App Owner-only, confirmed, audited permanent direct links."""

    def link(self, attachment=None, actor=None):
        attachment = attachment or self.upload(self.owner)
        created = self.service.create_direct_link(actor or self.owner, self.task["id"], attachment["id"],
                                                  confirm="direct_link")
        return attachment, created, created["url"].removeprefix("/files/")

    def link_rows(self):
        return self.db.execute("SELECT * FROM attachment_links ORDER BY rowid").fetchall()

    def second_owner(self):
        second = self.user("second")
        self.service.grant_secondary_owner(self.owner, second["id"], "backup owner")
        return dict(self.db.execute("SELECT * FROM users WHERE id=?", (second["id"],)).fetchone())

    def shown(self, actor, attachment):
        detail = self.service.task_detail(actor, self.task["id"])
        [row] = [a for a in detail["attachments"] if a["id"] == attachment["id"]]
        return row, json.dumps(detail, default=str)

    def test_creation_needs_confirmation_and_only_the_hash_is_stored(self):
        attachment = self.upload(self.owner)
        for confirm in (None, "", "yes", True, "DIRECT_LINK"):
            with self.subTest(confirm=confirm):
                with self.assertRaises(NeedsConfirmation) as caught:
                    self.service.create_direct_link(self.owner, self.task["id"], attachment["id"], confirm=confirm)
                self.assertEqual((caught.exception.confirm, len(caught.exception.impact)), ("direct_link", 3))
                self.assertIn("without signing in", str(caught.exception))
        self.assertEqual(self.link_rows(), [])
        self.assertEqual(self.events("direct_link_created"), [])
        _, link, token = self.link(attachment)
        self.assertEqual(link["url"], "/files/" + token)
        self.assertGreaterEqual(len(token), 43)  # 32 random bytes
        self.assertEqual((link["attachment_id"], link["display_name"]), (attachment["id"], "report.pdf"))
        [row] = self.link_rows()
        self.assertEqual(row["token_hash"], hashlib.sha256(token.encode("utf-8")).hexdigest())
        self.assertEqual((row["id"], row["created_by"], row["revoked_at"]), (link["id"], self.owner["id"], None))
        # The link is shown once: nothing in the database holds the token.
        self.assertNotIn(token, chr(10).join(self.db.iterdump()))
        [event] = self.events("direct_link_created")
        self.assertEqual(event["actor_user_id"], self.owner["id"])
        self.assertEqual(json.loads(event["after_json"]),
                         {"attachment_id": attachment["id"], "display_name": "report.pdf", "link_id": link["id"]})
        with self.assertRaises(Conflict) as caught:  # one active link per file
            self.link(attachment)
        self.assertNotIsInstance(caught.exception, NeedsConfirmation)
        self.assertEqual(len(self.link_rows()), 1)
        self.assertEqual(len(self.events("direct_link_created")), 1)

    def test_two_links_never_share_a_token(self):
        first = self.link()[2]
        second = self.link(self.upload(self.owner, name="other.pdf"))[2]
        self.assertNotEqual(first, second)
        self.assertEqual(len({row["token_hash"] for row in self.link_rows()}), 2)

    def test_the_task_shows_that_a_link_exists_but_never_the_link(self):
        attachment, link, token = self.link()
        viewer = self.user("viewer", "viewer")
        token_hash = self.link_rows()[0]["token_hash"]
        for actor in (self.owner, viewer):
            row, raw = self.shown(actor, attachment)
            with self.subTest(actor=actor["email"]):
                self.assertEqual(set(row["direct_link"]), {"id", "created_at", "created_by_name"})
                self.assertEqual((row["direct_link"]["id"], row["direct_link"]["created_by_name"]),
                                 (link["id"], "Owner"))
                self.assertNotIn(token, raw)
                self.assertNotIn(token_hash, raw)

    def test_only_the_app_owner_creates_or_revokes_and_attempts_are_audited(self):
        _, link, token = self.link()
        other = self.upload(self.owner, name="other.pdf")
        assignee = self.user("assignee", "member")  # the person the task is assigned to
        self.db.execute("UPDATE tasks SET owner_user_id=? WHERE id=?", (assignee["id"], self.task["id"]))
        actors = [self.user("manager", "manager"), self.user("member", "member"), self.user("viewer", "viewer"),
                  self.user("chairman", None, "chairman"), assignee]
        for actor in actors:
            with self.subTest(actor=actor["email"], action="create"):
                with self.assertRaises(Forbidden):
                    self.service.create_direct_link(actor, self.task["id"], other["id"], confirm="direct_link")
            with self.subTest(actor=actor["email"], action="revoke"):
                with self.assertRaises(Forbidden):
                    self.service.revoke_direct_link(actor, self.task["id"], link["id"], "not mine to revoke")
        blocked = self.events("attachment_add_blocked")
        self.assertEqual([json.loads(event["after_json"])["kind"] for event in blocked],
                         ["direct_link", "direct_link_revoke"] * len(actors))
        self.assertEqual([event["actor_user_id"] for event in blocked],
                         [actor["id"] for actor in actors for _ in range(2)])
        outsider = self.user("outsider")  # cannot see the task at all
        with self.assertRaises((Forbidden, KeyError)):
            self.service.create_direct_link(outsider, self.task["id"], other["id"], confirm="direct_link")
        with self.assertRaises((Forbidden, KeyError)):
            self.service.revoke_direct_link(outsider, self.task["id"], link["id"], "not mine to revoke")
        [row] = self.link_rows()
        self.assertIsNone(row["revoked_at"])
        self.assertEqual(len(self.events("direct_link_created")), 1)
        self.assertEqual(self.events("direct_link_revoked"), [])
        self.service.open_direct_link(token)[1].close()
        # Any App Owner revokes another owner's link.
        second = self.second_owner()
        self.service.revoke_direct_link(second, self.task["id"], link["id"], "no longer needed")
        [row] = self.link_rows()
        self.assertEqual((row["revoked_by"], row["revoke_reason"]), (second["id"], "no longer needed"))

    def test_anyone_holding_the_link_downloads_and_each_download_is_audited(self):
        self.second_owner()  # would be told of the first owner's actions; a download is not one
        _, link, token = self.link()
        notices = self.db.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
        for _ in range(2):
            meta, handle = self.service.open_direct_link(token)
            with handle:
                self.assertEqual(handle.read(), PDF)
            self.assertEqual(meta, {"display_name": "report.pdf", "size_bytes": len(PDF)})
        events = self.events("attachment_direct_download")
        self.assertEqual([(event["actor_user_id"], event["reason"]) for event in events],
                         [(self.owner["id"], "via direct link")] * 2)
        self.assertEqual(json.loads(events[0]["after_json"]), {"display_name": "report.pdf", "link_id": link["id"]})
        self.assertEqual(self.events("attachment_downloaded"), [])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM notifications").fetchone()[0], notices)

    def test_the_history_shows_a_download_through_a_link_with_no_person(self):
        # Aly, 2026-11-17 (question 4): nobody is signed in, so the row names nobody. The
        # creator stays named in the link's own details and on the "Direct link created" row.
        attachment, _, token = self.link()
        self.service.open_direct_link(token)[1].close()
        self.service.open_task_file(self.owner, self.task["id"], attachment["id"])[1].close()
        manager = self.user("manager", "manager")
        chairman = self.user("chairman", None, "chairman")
        for actor in (self.owner, manager, chairman):
            with self.subTest(actor=actor["email"]):
                events = {event["event_type"]: event for event in self.service.task_events(actor, self.task["id"])}
                download = events["attachment_direct_download"]
                self.assertEqual((download["actor_user_id"], download["actor_name"], download["reason"]),
                                 (None, None, "via direct link"))
                for kind in ("direct_link_created", "attachment_downloaded"):
                    self.assertEqual((events[kind]["actor_user_id"], events[kind]["actor_name"]),
                                     (self.owner["id"], "Owner"))
                self.assertEqual(self.shown(actor, attachment)[0]["direct_link"]["created_by_name"], "Owner")
        # The stored row keeps the creator: a history row needs a person, and the audit keeps it.
        [stored] = self.events("attachment_direct_download")
        self.assertEqual(stored["actor_user_id"], self.owner["id"])

    def test_a_wrong_or_malformed_token_finds_nothing_and_storage_is_never_asked(self):
        _, link, token = self.link()
        stored_hash = self.link_rows()[0]["token_hash"]
        wrong = ("", None, 5, token.encode("ascii"), [token], "x" * 19, "x" * 129, "x" * 43, token[:-1],
                 token + "x", " " + token, stored_hash, link["id"] * 2)
        with patch("astra.service.storage_named", side_effect=AssertionError("storage consulted")):
            for bad in wrong:
                with self.subTest(token=bad):
                    with self.assertRaises(KeyError):
                        self.service.open_direct_link(bad)
            # Too short or too long is refused before anything is hashed or looked up.
            with patch.object(AstraService, "_direct_link_hash", side_effect=AssertionError("hashed")):
                for bad in ("x" * 19, "x" * 129, "x" * 100000):
                    with self.subTest(length=len(bad)):
                        with self.assertRaises(KeyError):
                            self.service.open_direct_link(bad)
        self.assertEqual(self.events("attachment_direct_download"), [])
        self.service.open_direct_link(token)[1].close()

    def test_revoking_needs_a_reason_is_recorded_and_stops_downloads(self):
        attachment, link, token = self.link()
        for reason in ("", "   ", None, ["a reason"], {"a": 1}, 5, True, b"bytes", "x" * 501):
            with self.subTest(reason=reason):
                with self.assertRaises(ValueError):
                    self.service.revoke_direct_link(self.owner, self.task["id"], link["id"], reason)
        # Ids that are not text find nothing, and are not mistaken for a refused attempt.
        for task_id, link_id in (([self.task["id"]], link["id"]), (None, link["id"]), (self.task["id"], [link["id"]]),
                                 (self.task["id"], {"id": link["id"]}), (self.task["id"], None), (self.task["id"], 7)):
            with self.subTest(task_id=task_id, link_id=link_id):
                with self.assertRaises(KeyError):
                    self.service.revoke_direct_link(self.owner, task_id, link_id, "wrong shape")
        self.assertEqual(self.events("attachment_add_blocked"), [])
        elsewhere = self.service.create_task(self.owner, {"project_id": self.project["id"], "title": "Elsewhere"})
        for task_id, link_id in ((elsewhere["id"], link["id"]), (self.task["id"], "missing"),
                                 (self.task["id"], attachment["id"])):
            with self.subTest(task_id=task_id, link_id=link_id):
                with self.assertRaises(KeyError):
                    self.service.revoke_direct_link(self.owner, task_id, link_id, "wrong place")
        self.assertIsNone(self.link_rows()[0]["revoked_at"])
        self.assertEqual(self.events("direct_link_revoked"), [])
        self.service.open_direct_link(token)[1].close()
        self.service.revoke_direct_link(self.owner, self.task["id"], link["id"], "  sent to the wrong person ")
        [row] = self.link_rows()
        self.assertEqual((row["revoked_by"], row["revoke_reason"]), (self.owner["id"], "sent to the wrong person"))
        self.assertIsNotNone(row["revoked_at"])
        [event] = self.events("direct_link_revoked")
        self.assertEqual((event["actor_user_id"], event["reason"]), (self.owner["id"], "sent to the wrong person"))
        self.assertEqual(json.loads(event["after_json"]),
                         {"attachment_id": attachment["id"], "display_name": "report.pdf", "link_id": link["id"]})
        with patch("astra.service.storage_named", side_effect=AssertionError("storage consulted")):
            with self.assertRaises(KeyError):
                self.service.open_direct_link(token)
        with self.assertRaises(KeyError):  # already revoked
            self.service.revoke_direct_link(self.owner, self.task["id"], link["id"], "again")
        self.assertEqual(len(self.events("direct_link_revoked")), 1)
        self.assertIsNone(self.shown(self.owner, attachment)[0]["direct_link"])
        # A new link is a new token; the revoked one stays dead and stays on record.
        _, _, renewed = self.link(attachment)
        self.assertNotEqual(renewed, token)
        self.assertEqual(len(self.link_rows()), 2)
        with self.assertRaises(KeyError):
            self.service.open_direct_link(token)
        self.service.open_direct_link(renewed)[1].close()
        # The longest reason allowed is kept whole.
        self.service.revoke_direct_link(self.owner, self.task["id"], self.link_rows()[1]["id"],
                                        "  " + "x" * 500 + " ")
        self.assertEqual(self.link_rows()[1]["revoke_reason"], "x" * 500)

    def test_every_app_owner_is_told_of_creation_and_revocation_including_the_one_who_acted(self):
        second = self.second_owner()
        self.user("manager", "manager")
        _, link, _ = self.link()
        self.service.revoke_direct_link(second, self.task["id"], link["id"], "review finished")
        for kind, actor in (("direct_link_created", "Owner"), ("direct_link_revoked", "Second")):
            rows = self.db.execute("SELECT user_id, summary FROM notifications WHERE kind=?", (kind,)).fetchall()
            with self.subTest(kind=kind):
                self.assertEqual(sorted(row["user_id"] for row in rows), sorted([self.owner["id"], second["id"]]))
                for row in rows:
                    self.assertIn("report.pdf", row["summary"])
                    self.assertIn("by " + actor, row["summary"])

    def test_removing_the_file_ends_its_link_and_says_so(self):
        attachment, link, token = self.link()
        self.service.remove_task_attachment(self.owner, self.task["id"], attachment["id"])
        [event] = self.events("direct_link_revoked")
        self.assertEqual((event["actor_user_id"], event["reason"]), (self.owner["id"], "attachment removed"))
        self.assertEqual(json.loads(event["after_json"]),
                         {"attachment_id": attachment["id"], "display_name": "report.pdf", "link_id": link["id"]})
        self.assertEqual(self.link_rows(), [])
        with self.assertRaises(KeyError):
            self.service.open_direct_link(token)
        # A file with no link, or whose link was already revoked, records no second ending.
        plain = self.upload(self.owner, name="plain.pdf")
        self.service.remove_task_attachment(self.owner, self.task["id"], plain["id"])
        revoked, revoked_link, _ = self.link(self.upload(self.owner, name="revoked.pdf"))
        self.service.revoke_direct_link(self.owner, self.task["id"], revoked_link["id"], "done with it")
        self.service.remove_task_attachment(self.owner, self.task["id"], revoked["id"])
        self.assertEqual([event["reason"] for event in self.events("direct_link_revoked")],
                         ["attachment removed", "done with it"])

    def test_a_final_result_keeps_its_file_and_its_link(self):
        attachment, _, token = self.link()
        self.service.mark_final_result(self.owner, self.task["id"], "attachment", attachment["id"], "")
        with self.assertRaises(Conflict):
            self.service.remove_task_attachment(self.owner, self.task["id"], attachment["id"])
        self.assertEqual(self.events("direct_link_revoked"), [])
        self.assertIsNone(self.link_rows()[0]["revoked_at"])
        self.service.open_direct_link(token)[1].close()

    def test_only_a_managed_upload_on_this_task_gets_a_direct_link(self):
        web = self.service.add_task_link(self.owner, self.task["id"], "https://example.org/")
        uploaded = self.upload(self.owner)
        elsewhere = self.service.create_task(self.owner, {"project_id": self.project["id"], "title": "Elsewhere"})
        for task_id, attachment_id in ((self.task["id"], web["id"]), (self.task["id"], "missing"),
                                       (elsewhere["id"], uploaded["id"])):
            for confirm in (None, "direct_link"):
                with self.subTest(task_id=task_id, attachment_id=attachment_id, confirm=confirm):
                    with self.assertRaises(KeyError):
                        self.service.create_direct_link(self.owner, task_id, attachment_id, confirm=confirm)
        self.assertEqual(self.link_rows(), [])
        self.assertEqual(self.events("direct_link_created"), [])
        shown = {a["kind"]: a for a in self.service.task_detail(self.owner, self.task["id"])["attachments"]}
        self.assertNotIn("direct_link", shown["link"])
        self.assertIsNone(shown["file"]["direct_link"])

    def test_a_failed_direct_download_audit_closes_the_file(self):
        _, _, token = self.link()
        handles, real_open = [], FolderStorage.open

        def spy(storage, key):
            handles.append(real_open(storage, key))
            return handles[-1]
        with patch.object(FolderStorage, "open", spy):
            with patch.object(self.service, "_event", side_effect=RuntimeError("audit down")):
                with self.assertRaises(RuntimeError):
                    self.service.open_direct_link(token)
        [handle] = handles  # held here, so only an explicit close() can have closed it
        self.assertTrue(handle.closed)

    def test_a_file_that_already_has_a_link_is_refused_before_the_warning(self):
        attachment, _, _ = self.link()
        for confirm in (None, "direct_link"):
            with self.subTest(confirm=confirm):
                with self.assertRaises(Conflict) as caught:
                    self.service.create_direct_link(self.owner, self.task["id"], attachment["id"], confirm=confirm)
                self.assertNotIsInstance(caught.exception, NeedsConfirmation)
                self.assertIn("already has a direct link", str(caught.exception))
        self.assertEqual(len(self.link_rows()), 1)
        self.assertEqual(len(self.events("direct_link_created")), 1)

    def racing(self, between):
        """Run `between` once, right after create_direct_link first looks for an active link."""
        real, seen = self.service._active_direct_link, []

        def look(attachment_id):
            found = real(attachment_id)
            seen.append(attachment_id)
            if len(seen) == 1:
                between()
            return found
        return patch.object(self.service, "_active_direct_link", look)

    def test_a_link_another_owner_creates_meanwhile_is_a_conflict_not_a_second_link(self):
        attachment = self.upload(self.owner)
        second = self.second_owner()
        with self.racing(lambda: self.link(attachment, second)):
            with self.assertRaises(Conflict) as caught:
                self.service.create_direct_link(self.owner, self.task["id"], attachment["id"], confirm="direct_link")
        self.assertNotIsInstance(caught.exception, NeedsConfirmation)
        self.assertIn("already has a direct link", str(caught.exception))
        [row] = self.link_rows()
        self.assertEqual(row["created_by"], second["id"])
        self.assertEqual(len(self.events("direct_link_created")), 1)

    def test_a_file_removed_meanwhile_gets_no_link(self):
        attachment = self.upload(self.owner)
        with self.racing(lambda: self.service.remove_task_attachment(self.owner, self.task["id"], attachment["id"])):
            with self.assertRaises(KeyError):
                self.service.create_direct_link(self.owner, self.task["id"], attachment["id"], confirm="direct_link")
        self.assertEqual(self.link_rows(), [])
        self.assertEqual(self.events("direct_link_created"), [])


class SettingsTests(Fixture):
    """Slice 2, Owner Items 8-9: the App Owner raises the limit up to the ceiling and adds to
    the denylist; the built-in list cannot be reduced."""

    def setUp(self):
        super().setUp()
        self.ceiling("")  # the machine's own ASTRA_UPLOAD_CEILING_MB must not leak into these tests

    def save(self, **fields):
        payload = {"upload_limit_mb": 25, "blocked_extensions": [], "blocked_mime_types": []}
        payload.update(fields)
        return self.service.update_attachment_settings(self.owner, **payload)

    def ceiling(self, mb):
        patcher = patch.dict(os.environ, {"ASTRA_UPLOAD_CEILING_MB": str(mb)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def setting_events(self):
        return self.db.execute(
            "SELECT * FROM user_events WHERE event_type='attachment_settings_changed' ORDER BY rowid"
        ).fetchall()

    def test_the_defaults_apply_until_the_owner_saves_something(self):
        settings = self.service.get_attachment_settings(self.owner)
        self.assertEqual((settings["upload_limit_mb"], settings["default_limit_mb"], settings["hard_limit_mb"],
                          settings["server_ceiling_mb"]), (25, 25, 250, 25))
        self.assertEqual((settings["blocked_extensions"], settings["blocked_mime_types"]), ([], []))
        self.assertIn(".exe", settings["builtin_extensions"])
        self.assertIn("application/x-msdownload", settings["builtin_mime_types"])
        self.assertIsNone(settings["updated_at"])
        self.assertEqual(self.service.upload_policy(), DEFAULT_POLICY)
        self.assertEqual(DEFAULT_POLICY.limit, 25 * MB)
        self.assertEqual(self.service.task_detail(self.owner, self.task["id"])["upload_limit_bytes"], 25 * MB)

    def test_the_limit_is_the_owners_setting_up_to_the_ceiling_and_is_applied_before_reading(self):
        self.ceiling(250)
        self.save(upload_limit_mb="1")
        with self.assertRaisesRegex(UploadTooLarge, "larger than 1 MB"):
            self.service.add_task_file(self.owner, self.task["id"], "big.pdf", "application/pdf",
                                       RefusingStream(), MB + 1)
        exact = b"%PDF-" + b"x" * (MB - 5)
        self.assertEqual(self.upload(self.owner, data=exact)["size_bytes"], MB)
        self.assertEqual(self.service.task_detail(self.owner, self.task["id"])["upload_limit_bytes"], MB)
        self.save(upload_limit_mb=250)
        with self.assertRaises(UploadTooLarge):
            self.service.add_task_file(self.owner, self.task["id"], "big.pdf", "application/pdf",
                                       RefusingStream(), HARD_UPLOAD_LIMIT + 1)

        class Drops(io.BytesIO):
            def read(self, size=-1):
                raise OSError("connection dropped")
        with self.assertRaises(OSError):  # the ceiling itself passes the size check and is read
            self.service.add_task_file(self.owner, self.task["id"], "big.pdf", "application/pdf",
                                       Drops(), HARD_UPLOAD_LIMIT)
        for bad in (0, 251, -1, "big", "", None, True, 2.5, [25], "25.0", "\uff12\uff15"):
            with self.subTest(limit=bad), self.assertRaisesRegex(ValueError, "whole number of MB from 1 to 250"):
                self.save(upload_limit_mb=bad)
        self.assertEqual(self.service.upload_policy().limit, HARD_UPLOAD_LIMIT)
        with self.assertRaises(ValueError):
            UploadPolicy(HARD_UPLOAD_LIMIT + 1)
        with self.assertRaises(ValueError):
            UploadPolicy(MB - 1)

    def test_the_server_ceiling_bounds_the_owners_limit_and_the_policy(self):
        # Waitress spools a whole body before Astra runs, so the ceiling it admits is set on the
        # server (ASTRA_UPLOAD_CEILING_MB, matched by Caddy), never from the app.
        self.assertEqual(upload_ceiling(), DEFAULT_UPLOAD_LIMIT)
        with self.assertRaisesRegex(ValueError, "admits uploads up to 25 MB"):
            self.save(upload_limit_mb=26)
        self.ceiling(40)
        self.assertEqual(self.save(upload_limit_mb=40)["upload_limit_mb"], 40)
        self.assertEqual(self.service.get_attachment_settings(self.owner)["server_ceiling_mb"], 40)
        with self.assertRaisesRegex(ValueError, "admits uploads up to 40 MB"):
            self.save(upload_limit_mb=41)
        self.assertEqual(self.service.upload_policy().limit, 40 * MB)
        self.ceiling(1)  # lowered on the server after the owner saved 40: the policy follows the server
        self.assertEqual(self.service.upload_policy().limit, MB)
        shown = self.service.get_attachment_settings(self.owner)
        self.assertEqual((shown["upload_limit_mb"], shown["saved_limit_mb"], shown["server_ceiling_mb"]), (1, 40, 1))
        self.assertEqual(self.service.task_detail(self.owner, self.task["id"])["upload_limit_bytes"], MB)
        # Re-saving what the form shows is a real change from the saved 40, and is audited as one.
        self.save(upload_limit_mb=1)
        [event] = self.db.execute("SELECT detail_json FROM user_events WHERE event_type='attachment_settings_changed'"
                                  " ORDER BY rowid DESC LIMIT 1").fetchall()
        detail = json.loads(event["detail_json"])
        self.assertEqual((detail["before"]["upload_limit_mb"], detail["after"]["upload_limit_mb"]), (40, 1))
        self.ceiling(250)
        self.assertEqual(self.service.upload_policy().limit, MB)  # the row now says 1, not 40
        # A ceiling under the default with no row saved yet: the default is clamped too.
        self.db.execute("DELETE FROM attachment_settings")
        self.ceiling(10)
        self.assertEqual(self.service.upload_policy().limit, 10 * MB)
        shown = self.service.get_attachment_settings(self.owner)
        self.assertEqual((shown["upload_limit_mb"], shown["saved_limit_mb"]), (10, None))
        self.assertEqual(self.service.task_detail(self.owner, self.task["id"])["upload_limit_bytes"], 10 * MB)
        for bad in ("abc", "0", "251", "-5", "25.0", "2５"):
            with self.subTest(env=bad), patch.dict(os.environ, {"ASTRA_UPLOAD_CEILING_MB": bad}), \
                    self.assertRaises(ValueError):
                upload_ceiling()
        with patch.dict(os.environ, {"ASTRA_UPLOAD_CEILING_MB": " 250 "}):
            self.assertEqual(upload_ceiling(), HARD_UPLOAD_LIMIT)

    def test_a_row_no_code_wrote_refuses_uploads_until_it_is_saved_again(self):
        # Fail closed: the owner's blocked list is never silently dropped.
        self.save(blocked_extensions=[".xyz"])
        for broken in ("not json", "[7]", "{}"):
            with self.subTest(broken=broken):
                self.db.execute("UPDATE attachment_settings SET blocked_extensions=?", (broken,))
                with self.assertLogs("astra.attachments", "ERROR"), self.assertRaises(Conflict):
                    self.service.upload_policy()
                with self.assertLogs("astra.attachments", "ERROR"), self.assertRaises(Conflict):
                    self.upload(self.owner, name="minutes.txt", data=b"text", declared="")
        self.assertEqual(self.stored_files(), [])
        with self.assertRaises(Exception):  # the schema keeps the limit between 1 MB and 250 MB
            self.db.execute("UPDATE attachment_settings SET upload_limit_bytes=5")
        # The owner can still open the settings, is told, and saving again restores uploads.
        with self.assertLogs("astra.attachments", "ERROR"):
            shown = self.service.get_attachment_settings(self.owner)
        self.assertIn("could not be read", shown["unusable"])
        self.assertEqual((shown["upload_limit_mb"], shown["blocked_extensions"], shown["saved_limit_mb"]),
                         (25, [], None))
        with self.assertLogs("astra.attachments", "ERROR"):
            self.assertEqual(self.service.task_detail(self.owner, self.task["id"])["upload_limit_bytes"], 25 * MB)
        # Saving back exactly what the page showed is enough: the bad row is replaced and audited.
        saved = self.service.update_attachment_settings(
            self.owner, upload_limit_mb=shown["upload_limit_mb"], blocked_extensions=shown["blocked_extensions"],
            blocked_mime_types=shown["blocked_mime_types"])
        self.assertIsNone(saved["unusable"])
        self.assertEqual(json.loads(self.setting_events()[-1]["detail_json"])["before"], {"unreadable": True})
        self.assertEqual(self.upload(self.owner, name="minutes.txt", data=b"text", declared="")["kind"], "file")
        saved = self.save(blocked_extensions=[".xyz"])
        self.assertIsNone(saved["unusable"])
        with self.assertRaises(ValueError):
            self.upload(self.owner, name="a.xyz", data=b"x", declared="")

    def test_owner_additions_block_uploads_and_the_builtin_list_cannot_be_reduced(self):
        settings = self.save(blocked_extensions=[" .XYZ ", "abc", "*.Abc", ".exe", "", "xyz"],
                             blocked_mime_types="application/x-foo, Text/Plain; charset=utf-8\n\ntext/javascript")
        self.assertEqual(settings["blocked_extensions"], [".abc", ".xyz"])  # .exe is built in already
        self.assertEqual(settings["blocked_mime_types"], ["application/x-foo", "text/plain"])
        for name, declared in (("notes.XYZ", ""), ("a.abc", ""), ("plain.txt", "text/plain"),
                               ("plain.txt", "APPLICATION/X-FOO; v=1"), ("setup.exe", "")):
            with self.subTest(name=name, declared=declared), self.assertRaises(ValueError):
                self.upload(self.owner, name=name, data=b"hello", declared=declared)
        self.assertEqual(self.upload(self.owner, name="report.pdf")["kind"], "file")
        self.assertEqual(len(self.stored_files()), 1)
        # Saving empty lists removes the additions and nothing else.
        self.save()
        self.assertEqual(self.upload(self.owner, name="notes.xyz", data=b"hello", declared="")["kind"], "file")
        with self.assertRaises(ValueError):
            self.upload(self.owner, name="setup.exe", data=b"hello", declared="")
        # The policy is read from the database, so another service instance sees the same.
        self.save(blocked_extensions=["q"])
        self.assertEqual(AstraService(self.db).upload_policy(), UploadPolicy(25 * MB, (".q",), ()))

    def test_malformed_additions_are_refused_and_nothing_changes(self):
        self.save(blocked_extensions=[".ok"])
        for ext in ("../x", ".", "a b", "x" * 40, "a/b", "-a", "é", "a.b", "ſh"):  # long s folds to .sh
            with self.subTest(ext=ext), self.assertRaises(ValueError):
                self.save(blocked_extensions=[ext])
        for mime in ("text", "text/", "/x", "a b/c", "text/plain/x", "text/é"):
            with self.subTest(mime=mime), self.assertRaises(ValueError):
                self.save(blocked_mime_types=[mime])
        for bad in (7, None, [7], {"a": 1}, [None]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.save(blocked_extensions=bad)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.save(blocked_mime_types=bad)
        with self.assertRaises(ValueError):
            self.save(blocked_extensions=[f".e{n}" for n in range(201)])
        self.assertEqual(self.service.get_attachment_settings(self.owner)["blocked_extensions"], [".ok"])
        self.assertEqual(normalize_extension("*.PDF"), ".pdf")
        self.assertEqual(normalize_mime_type(" Application/PDF ; q=1"), "application/pdf")

    def test_only_the_app_owner_reads_or_changes_the_settings_and_changes_are_audited(self):
        manager = self.user("manager", "manager")
        chairman = self.user("chairman", None, "chairman")
        for actor in (manager, chairman):
            with self.subTest(actor=actor["email"]), self.assertRaises(Forbidden):
                self.service.get_attachment_settings(actor)
            with self.subTest(actor=actor["email"]), self.assertRaises(Forbidden):
                self.service.update_attachment_settings(actor, upload_limit_mb=1, blocked_extensions=[],
                                                        blocked_mime_types=[])
        self.assertIsNone(self.db.execute("SELECT 1 FROM attachment_settings").fetchone())
        self.assertEqual(self.setting_events(), [])
        settings = self.save(upload_limit_mb=20, blocked_extensions=[".xyz"])
        self.assertEqual(settings["updated_by_name"], "Owner")
        self.assertIsNotNone(settings["updated_at"])
        [event] = self.setting_events()
        detail = json.loads(event["detail_json"])
        self.assertEqual(detail["before"], {"upload_limit_mb": 25, "blocked_extensions": [], "blocked_mime_types": []})
        self.assertEqual(detail["after"], {"upload_limit_mb": 20, "blocked_extensions": [".xyz"],
                                           "blocked_mime_types": []})
        # The same policy saved again by someone else: no event, and the row is not rewritten.
        second = self.user("second")
        self.service.grant_secondary_owner(self.owner, second["id"], "backup owner")
        second = dict(self.db.execute("SELECT * FROM users WHERE id=?", (second["id"],)).fetchone())
        again = self.service.update_attachment_settings(second, upload_limit_mb="20", blocked_extensions="XYZ",
                                                        blocked_mime_types=[])
        self.assertEqual((again["updated_at"], again["updated_by_name"]), (settings["updated_at"], "Owner"))
        self.assertEqual(len(self.setting_events()), 1)
        # Any App Owner may change it (as for the import template settings), and that is audited.
        changed = self.service.update_attachment_settings(second, upload_limit_mb=21, blocked_extensions=["XYZ"],
                                                          blocked_mime_types=[])
        self.assertEqual(changed["updated_by_name"], "Second")
        self.assertEqual(len(self.setting_events()), 2)
        self.assertEqual(self.setting_events()[-1]["actor_user_id"], second["id"])

    def test_a_save_from_a_page_loaded_before_another_owners_save_is_refused(self):
        second = self.user("second")
        self.service.grant_secondary_owner(self.owner, second["id"], "backup owner")
        second = dict(self.db.execute("SELECT * FROM users WHERE id=?", (second["id"],)).fetchone())
        # Both pages were loaded with the defaults (no saved row: null).
        first = self.service.update_attachment_settings(
            self.owner, upload_limit_mb=20, blocked_extensions=[".aaa"], blocked_mime_types=[],
            expected_updated_at=None)
        for stale in (None, "2026-01-01T00:00:00+00:00"):
            with self.subTest(expected=stale), self.assertRaisesRegex(Conflict, "Another App Owner saved"):
                self.service.update_attachment_settings(
                    second, upload_limit_mb=5, blocked_extensions=[".bbb"], blocked_mime_types=[],
                    expected_updated_at=stale)
        row = self.db.execute("SELECT upload_limit_bytes, blocked_extensions, updated_by FROM attachment_settings")
        self.assertEqual(tuple(row.fetchone()), (20 * MB, '[".aaa"]', self.owner["id"]))
        self.assertEqual(len(self.setting_events()), 1)
        # After a reload the second owner's page carries the first owner's save, and its save goes in.
        saved = self.service.update_attachment_settings(
            second, upload_limit_mb=5, blocked_extensions=[".aaa", ".bbb"], blocked_mime_types=[],
            expected_updated_at=first["updated_at"])
        self.assertEqual((saved["upload_limit_mb"], saved["updated_by_name"]), (5, "Second"))
        self.assertEqual(len(self.setting_events()), 2)
        with self.assertRaises(Conflict):
            self.service.update_attachment_settings(
                self.owner, upload_limit_mb=7, blocked_extensions=[], blocked_mime_types=[],
                expected_updated_at=first["updated_at"])
        # A role check still comes first: a manager learns nothing about the saved version.
        manager = self.user("manager", "manager")
        with self.assertRaises(Forbidden):
            self.service.update_attachment_settings(
                manager, upload_limit_mb=7, blocked_extensions=[], blocked_mime_types=[],
                expected_updated_at=None)


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

    def test_a_direct_link_token_is_redacted_in_every_spelling_a_server_decodes(self):
        token = "Abc-_1234567890abcdefghij"
        for spelled in ("/files/", "//files/", "/%66iles/", "/files%2F", "/files%2f", "%2Ffiles%2F",
                        "/%66%69%6C%65%73/", "/FILES/", "/%46%49%4c%45%53/", "http://host/files/"):
            with self.subTest(spelled=spelled):
                self.assertEqual(_without_link_tokens(f'"GET {spelled}{token}?x=1 HTTP/1.1" 200'),
                                 f'"GET {spelled}[redacted] HTTP/1.1" 200')
        self.assertEqual(_without_link_tokens(f"/files//{token}/x and /files/{token}"),
                         "/files/[redacted] and /files/[redacted]")
        # A tab or a line break a client put in the path hides no part of the token in a log
        # line; in a traceback the token ends at the line's end and the next line is kept.
        for inside in ("\t", "\r", "\n", "\r\n", "\x0b"):
            for path in (f"/files/{inside}{token}", f"/files/{token[:10]}{inside}{token[10:]}"):
                with self.subTest(path=path):
                    self.assertEqual(_without_link_tokens(f"Exception while serving {path}"),
                                     "Exception while serving /files/[redacted]")
                    self.assertEqual(_without_link_tokens(f'"GET {path} HTTP/1.1" 200'),
                                     '"GET /files/[redacted] HTTP/1.1" 200')
        self.assertEqual(_without_link_tokens(f"OSError: /files/{token}\n  File x.py, line 1", many_lines=True),
                         "OSError: /files/[redacted]\n  File x.py, line 1")
        for kept in ('"GET /api/tasks/abc/files HTTP/1.1" 200', '"GET /static/app.js HTTP/1.1" 200',
                     '"GET /files/ HTTP/1.1" 404', "profiles/abc and files", "/file/abc", "/files"):
            with self.subTest(kept=kept):
                self.assertEqual(_without_link_tokens(kept), kept)


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

    def test_attachment_settings_are_owner_only_over_http_and_the_saved_limit_answers_413(self):
        viewer = self.login("viewer@example.org", "viewer password")
        headers = {"Cookie": viewer[0], "X-CSRF-Token": viewer[1], "Content-Type": "application/json"}
        self.assertEqual(self.call("GET", "/api/attachment-settings", headers=headers)[0].status, 403)
        body = json.dumps({"upload_limit_mb": 1, "blocked_extensions": [], "blocked_mime_types": [],
                           "expected_updated_at": None}).encode()
        self.assertEqual(self.call("PUT", "/api/attachment-settings", body, headers)[0].status, 403)
        owner = self.login("owner@example.org", "correct horse battery")
        headers = {"Cookie": owner[0], "X-CSRF-Token": owner[1], "Content-Type": "application/json"}
        response, raw = self.call("GET", "/api/attachment-settings", headers=headers)
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(raw)["settings"]["upload_limit_mb"], 25)
        response, raw = self.call("PUT", "/api/attachment-settings", body, headers)
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(raw)["settings"]["upload_limit_mb"], 1)
        saved_at = json.loads(raw)["settings"]["updated_at"]
        # A save from a page loaded before that one (null: the defaults) is refused with 409, a
        # body that does not say which save it was loaded from with 400; neither changes the row.
        stale = json.dumps({"upload_limit_mb": 2, "blocked_extensions": [], "blocked_mime_types": [],
                            "expected_updated_at": None}).encode()
        response, raw = self.call("PUT", "/api/attachment-settings", stale, headers)
        self.assertEqual(response.status, 409)
        self.assertIn("Another App Owner saved", json.loads(raw)["error"])
        for unsaid, message in (
                ({"upload_limit_mb": 2, "blocked_extensions": [], "blocked_mime_types": []},
                 "Missing expected_updated_at"),
                ({"upload_limit_mb": 2, "blocked_extensions": [], "blocked_mime_types": [],
                  "expected_updated_at": 5}, "expected_updated_at must be")):
            with self.subTest(body=unsaid):
                response, raw = self.call("PUT", "/api/attachment-settings", json.dumps(unsaid).encode(), headers)
                self.assertEqual(response.status, 400)
                self.assertIn(message, json.loads(raw)["error"])
        self.assertEqual(self.db.execute("SELECT upload_limit_bytes FROM attachment_settings").fetchone()[0], MB)
        response, raw = self.call("PUT", "/api/attachment-settings", b'{"upload_limit_mb": 251}', headers)
        self.assertEqual(response.status, 400)
        self.assertIn("Missing blocked_extensions, blocked_mime_types", json.loads(raw)["error"])
        self.assertEqual(json.loads(self.call("GET", "/api/attachment-settings", headers=headers)[1])
                         ["settings"]["upload_limit_mb"], 1)
        full = {"upload_limit_mb": 251, "blocked_extensions": [], "blocked_mime_types": [],
                "expected_updated_at": saved_at}
        response, raw = self.call("PUT", "/api/attachment-settings", json.dumps(full).encode(), headers)
        self.assertEqual(response.status, 400)
        self.assertIn("1 to 250", json.loads(raw)["error"])
        no_csrf = {"Cookie": owner[0], "Content-Type": "application/json"}
        self.assertEqual(self.call("PUT", "/api/attachment-settings", body, no_csrf)[0].status, 403)
        response, raw = self.post_file(owner, extra={"Content-Length": str(MB + 1)}, data=b"")
        self.assertEqual(response.status, 413)
        self.assertIn("larger than 1 MB", json.loads(raw)["error"])
        self.assertEqual(self.db.execute("SELECT upload_limit_bytes FROM attachment_settings").fetchone()[0], MB)

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


    def direct_link(self, session, attachment, confirm=True, csrf=True):
        headers = {"Content-Type": "application/json"}
        if session:
            headers["Cookie"] = session[0]
            if csrf:
                headers["X-CSRF-Token"] = session[1]
        body = json.dumps({"confirm": "direct_link"} if confirm else {}).encode()
        return self.call("POST", f"/api/tasks/{self.task['id']}/attachments/{attachment['id']}/direct-link", body,
                         headers)

    def revoke(self, session, payload, csrf=True):
        headers = {"Cookie": session[0], "Content-Type": "application/json"}
        if csrf:
            headers["X-CSRF-Token"] = session[1]
        return self.call("DELETE", "/api/direct-links", json.dumps(payload).encode(), headers)

    def active_links(self):
        return self.db.execute("SELECT COUNT(*) FROM attachment_links WHERE revoked_at IS NULL").fetchone()[0]

    def test_a_direct_link_is_confirmed_owner_only_and_downloads_without_a_session(self):
        owner = self.login("owner@example.org", "correct horse battery")
        viewer = self.login("viewer@example.org", "viewer password")
        attachment = json.loads(self.post_file(owner)[1])["attachment"]
        response, body = self.direct_link(owner, attachment, confirm=False)
        self.assertEqual(response.status, 409)
        answer = json.loads(body)
        self.assertEqual((answer["confirm"], len(answer["impact"])), ("direct_link", 3))
        self.assertEqual(self.direct_link(None, attachment)[0].status, 403)  # signed out
        self.assertEqual(self.direct_link(owner, attachment, csrf=False)[0].status, 403)
        self.assertEqual(self.direct_link(viewer, attachment)[0].status, 403)
        self.assertEqual(self.active_links(), 0)
        request_log = io.StringIO()
        with contextlib.redirect_stderr(request_log):
            response, body = self.direct_link(owner, attachment)
            self.assertEqual(response.status, 201, body)
            link = json.loads(body)["link"]
            token = link["url"].removeprefix("/files/")
            self.assertEqual(self.direct_link(owner, attachment)[0].status, 409)  # one active link per file
            response, data = self.call("GET", link["url"])  # no cookie at all
            self.assertEqual((response.status, data), (200, PDF))
            self.assertEqual(response.getheader("Content-Type"), "application/octet-stream")
            self.assertEqual(response.getheader("Content-Length"), str(len(PDF)))
            self.assertEqual(response.getheader("Cache-Control"), "private, no-store")
            self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
            self.assertEqual(response.getheader("Referrer-Policy"), "no-referrer")
            self.assertTrue(response.getheader("Content-Disposition").startswith("attachment;"))
            self.assertEqual(self.call("GET", "/files/" + "x" * 43)[0].status, 404)
            for path in ("/files/", f"/files/{token}/", f"/files/{token}/x", f"/api/files/{token}",
                         f"/static/files/{token}", f"/files//{token}"):
                response, data = self.call("GET", path)
                with self.subTest(path=path):
                    self.assertNotEqual(data, PDF)
        logged = request_log.getvalue()
        self.assertIn('"GET /files/[redacted] HTTP/1.1" 200', logged)
        self.assertNotIn(token, logged)  # in no shape of path, a doubled slash included
        downloads = self.db.execute(
            "SELECT COUNT(*) FROM task_events WHERE event_type='attachment_direct_download'").fetchone()[0]
        self.assertEqual(downloads, 1)
        # The task history over HTTP names nobody for that download (Aly, 2026-11-17).
        response, body = self.call("GET", f"/api/tasks/{self.task['id']}/events", headers={"Cookie": owner[0]})
        self.assertEqual(response.status, 200, body)
        [shown] = [event for event in json.loads(body)["events"]
                   if event["event_type"] == "attachment_direct_download"]
        self.assertEqual((shown["actor_user_id"], shown["actor_name"]), (None, None))
        payload = {"task_id": self.task["id"], "link_id": link["id"], "reason": "sent to the wrong person"}
        self.assertEqual(self.revoke(owner, payload, csrf=False)[0].status, 403)
        self.assertEqual(self.revoke(viewer, payload)[0].status, 403)
        self.assertEqual(self.revoke(owner, {**payload, "reason": " "})[0].status, 400)
        self.assertEqual(self.revoke(owner, {"task_id": self.task["id"]})[0].status, 400)
        self.assertEqual(self.revoke(owner, {**payload, "link_id": "missing"})[0].status, 404)
        self.assertEqual(self.call("GET", link["url"])[0].status, 200)
        self.assertEqual(self.revoke(owner, payload)[0].status, 200)
        self.assertEqual(self.call("GET", link["url"])[0].status, 404)
        self.assertEqual(self.revoke(owner, payload)[0].status, 404)
        self.assertEqual(self.active_links(), 0)

    def test_direct_links_are_owner_only_for_every_role_and_malformed_requests_answer_cleanly(self):
        service = self.server.service
        people = {}
        for key, role, project_role in (("second", "member", None), ("manager", "member", "manager"),
                                        ("member", "member", "member"), ("chairman", "chairman", None)):
            people[key] = service.create_user(self.owner, f"{key}@example.org", key.title(), f"{key} password", role)
            if project_role:
                service.grant_project_access(self.owner, self.project["id"], people[key]["id"], project_role)
        service.grant_secondary_owner(self.owner, people["second"]["id"], "backup owner")
        self.db.execute("UPDATE users SET must_change_password=0")
        owner = self.login("owner@example.org", "correct horse battery")
        attachment = json.loads(self.post_file(owner)[1])["attachment"]
        other = json.loads(self.post_file(owner, name="other.pdf")[1])["attachment"]
        request_log = io.StringIO()
        with contextlib.redirect_stderr(request_log):
            response, body = self.direct_link(owner, attachment)
            self.assertEqual(response.status, 201, body)
            link = json.loads(body)["link"]
            payload = {"task_id": self.task["id"], "link_id": link["id"], "reason": "not mine to revoke"}
            for key in ("manager", "member", "chairman", "viewer"):
                session = self.login(f"{key}@example.org", f"{key} password")
                with self.subTest(role=key):
                    self.assertEqual(self.direct_link(session, other)[0].status, 403)
                    self.assertEqual(self.revoke(session, payload)[0].status, 403)
            outsider = self.login("outsider@example.org", "outsider password")
            self.assertIn(self.direct_link(outsider, other)[0].status, (403, 404))
            self.assertIn(self.revoke(outsider, payload)[0].status, (403, 404))
            self.assertEqual(self.active_links(), 1)
            # A file that already has a link is refused outright: there is no warning to confirm.
            response, body = self.direct_link(owner, attachment, confirm=False)
            self.assertEqual(response.status, 409)
            self.assertNotIn("confirm", json.loads(body))
            # Only GET serves a direct link.
            for method in ("POST", "HEAD", "PUT", "DELETE"):
                response, data = self.call(method, link["url"])
                with self.subTest(method=method):
                    self.assertNotEqual(response.status, 200)
                    self.assertNotEqual(data, PDF)
            downloads = self.db.execute(
                "SELECT COUNT(*) FROM task_events WHERE event_type='attachment_direct_download'").fetchone()[0]
            self.assertEqual(downloads, 0)
            # Any App Owner creates a link, and revokes another owner's.
            second = self.login("second@example.org", "second password")
            response, body = self.direct_link(second, other)
            self.assertEqual(response.status, 201, body)
            kept = json.loads(body)["link"]
            self.assertEqual(self.revoke(second, payload)[0].status, 200)
            # Ids or a reason that are not text, or a reason too long to keep, change nothing.
            good = {"task_id": self.task["id"], "link_id": kept["id"], "reason": "tidying up"}
            for change, status in (({"link_id": [kept["id"]]}, 404), ({"link_id": {"id": kept["id"]}}, 404),
                                   ({"task_id": [self.task["id"]]}, 404), ({"reason": ["tidying up"]}, 400),
                                   ({"reason": {"a": 1}}, 400), ({"reason": "x" * 501}, 400)):
                with self.subTest(change=str(change)[:40]):
                    self.assertEqual(self.revoke(owner, {**good, **change})[0].status, status)
            self.assertEqual(self.active_links(), 1)
            self.assertEqual(self.call("GET", kept["url"])[0].status, 200)
            self.assertEqual(self.revoke(owner, {**good, "reason": "x" * 500})[0].status, 200)
        self.assertEqual(self.active_links(), 0)
        for created in (link, kept):
            self.assertNotIn(created["url"].removeprefix("/files/"), request_log.getvalue())


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


    def test_the_wsgi_request_log_never_carries_a_direct_link_token(self):
        with self.assertLogs("astra.http", level="INFO") as logs:
            _WSGIHandler.log_message(None, '"%s" %s', "GET /files/Abc-_1234567890abcdefghij HTTP/1.1", "200")
        self.assertEqual(logs.output, ['INFO:astra.http:"GET /files/[redacted] HTTP/1.1" 200'])

    def test_waitress_own_log_lines_never_carry_a_direct_link_token(self):
        token = "Abc-_1234567890abcdefghij"
        for name in ("waitress", "waitress.queue"):
            for path in ("/files/" + token, "//files/" + token, "/files//" + token, "/%66iles/" + token):
                with self.subTest(logger=name, path=path):
                    logger = logging.getLogger(name)
                    with self.assertLogs(name, level="INFO") as logs:
                        logger.info("Client disconnected while serving %s" % path)
                        logger.warning("Task queue depth is %d for %s", 3, path)
                        logger.info("Serving on %s", "http://127.0.0.1:8765")
                        try:
                            raise OSError("could not send " + path)
                        except OSError:
                            logger.exception("Exception while serving %s" % path)
                    logged = chr(10).join(logs.output)
                    self.assertNotIn(token, logged)
                    self.assertEqual(logged.count("[redacted]"), 4)  # three messages and the traceback
                    self.assertIn("Task queue depth is 3 for ", logged)
                    self.assertIn("Serving on http://127.0.0.1:8765", logged)
                    self.assertIn("OSError: could not send ", logged)

    def test_only_the_exact_path_serves_a_direct_link(self):
        # Waitress hands Astra the decoded path, so a percent-encoded tab or line break arrives
        # as the character itself. urlparse would drop it and find /files/<token> again; the
        # adapter does not serve such a path, so none can be logged unredacted by a request
        # that also got the file. (A raw control byte never gets this far: Waitress strips it.)
        cookie, csrf = self.login()
        captured, body = self.call(
            "POST", f"/api/tasks/{self.task['id']}/attachments/{self.attachment['id']}/direct-link",
            json.dumps({"confirm": "direct_link"}).encode(),
            {"Cookie": cookie, "X-CSRF-Token": csrf, "Content-Type": "application/json"})
        token = json.loads(b"".join(body))["link"]["url"].removeprefix("/files/")
        spellings = [f"/files/{inside}{token}" for inside in ("\t", "\n", "\r", " ", "\x0b")]
        spellings += [f"/files/{token[:10]}\t{token[10:]}", f"/files/{token}\n", f"/files/{token}\t", f"/fi\nles/{token}",
                      f"/f\tiles/{token}", f"/files\r/{token}", f"/\nfiles/{token}", f"\t/files/{token}",
                      f"/files/{token};p=1", f"/files/{token}/", f"//files/{token}", f"/files//{token}",
                      f"/Files/{token}", f"/files/{token}#x"]
        for path in spellings:
            captured, body_iter = self.call("GET", path)
            with self.subTest(path=path):
                self.assertFalse(captured["status"].startswith("200"), captured["status"])
                self.assertNotEqual(b"".join(body_iter), self.data)
        captured, body_iter = self.call("GET", f"/files/{token}")  # the link itself still works
        self.assertEqual((captured["status"][:3], b"".join(body_iter)), ("200", self.data))
        body_iter.close()
        db = connect(self.db_path)
        try:
            downloads = db.execute(
                "SELECT COUNT(*) FROM task_events WHERE event_type='attachment_direct_download'").fetchone()[0]
        finally:
            db.close()
        self.assertEqual(downloads, 1)

    def test_a_direct_link_is_streamed_through_the_wsgi_adapter_without_a_session(self):
        cookie, csrf = self.login()
        captured, body = self.call(
            "POST", f"/api/tasks/{self.task['id']}/attachments/{self.attachment['id']}/direct-link",
            json.dumps({"confirm": "direct_link"}).encode(),
            {"Cookie": cookie, "X-CSRF-Token": csrf, "Content-Type": "application/json"})
        self.assertTrue(captured["status"].startswith("201"), b"".join(body))
        url = json.loads(b"".join(body))["link"]["url"]
        captured, body_iter = self.call("GET", url)
        self.assertTrue(captured["status"].startswith("200"))
        self.assertNotIsInstance(body_iter, list)
        chunks = list(body_iter)
        body_iter.close()
        self.assertGreater(len(chunks), 1)
        self.assertEqual(b"".join(chunks), self.data)
        self.assertEqual(captured["headers"]["Content-Length"], str(len(self.data)))
        self.assertEqual(captured["headers"]["Cache-Control"], "private, no-store")
        captured, _ = self.call("GET", url + "x")
        self.assertTrue(captured["status"].startswith("404"))
        # A failure while serving a direct link is logged without the token.
        with patch.object(AstraService, "open_direct_link", side_effect=RuntimeError("could not serve " + url)):
            with self.assertLogs("astra.http", level="ERROR") as logs:
                captured, _ = self.call("GET", url)
        self.assertTrue(captured["status"].startswith("500"))
        logged = chr(10).join(logs.output)
        self.assertIn("/files/[redacted]", logged)
        self.assertNotIn(url.removeprefix("/files/"), logged)


class WaitressLogTests(unittest.TestCase):
    """Real Waitress: a direct download that fails part-way is logged by Waitress itself, with
    the request path in the message and the failure's own text in the traceback."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.dict(os.environ, {"ASTRA_HOME": self.temp.name,
                                          "ASTRA_UPLOAD_ROOT": os.path.join(self.temp.name, "up")})
        patcher.start()
        self.addCleanup(patcher.stop)
        db_path = Path(self.temp.name) / "astra.sqlite3"
        app = create_wsgi_app(db_path)
        db = connect(db_path)
        self.addCleanup(db.close)
        service = AstraService(db)
        owner = service.create_initial_owner("owner@example.org", "Owner", "correct horse battery")
        project = service.create_project(owner, "Hosted")
        task = service.create_task(owner, {"project_id": project["id"], "title": "Deliver"})
        data = b"%PDF-" + os.urandom(5 * storage_module.CHUNK_BYTES)
        attachment = service.add_task_file(owner, task["id"], "big.pdf", "", io.BytesIO(data), len(data))
        self.url = service.create_direct_link(owner, task["id"], attachment["id"], confirm="direct_link")["url"]
        from waitress import create_server, wasyncore

        before = set(threading.enumerate())
        server = create_server(app, host="127.0.0.1", port=0, ident="Astra", channel_timeout=30,
                               expose_tracebacks=False)
        workers = [t for t in set(threading.enumerate()) - before if t.name.startswith("waitress-")]
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        self.port = server.effective_port

        def stop():
            # Close every socket from inside the loop thread; the emptied map ends server.run().
            server.trigger.pull_trigger(lambda: wasyncore.close_all(server._map))
            thread.join(timeout=5)
            server.task_dispatcher.shutdown()
            for worker in workers:
                worker.join(timeout=5)
        self.addCleanup(stop)

    def test_a_download_that_fails_part_way_is_logged_without_the_token(self):
        url = self.url

        def failing(chunks):
            yield chunks._handle.read(1024)
            raise OSError("disk went away while sending " + url)
        with patch.object(_FileChunks, "__iter__", failing):
            with self.assertLogs("waitress", level="INFO") as logs:
                connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
                try:
                    connection.request("GET", url)
                    with contextlib.suppress(http.client.HTTPException, OSError):
                        connection.getresponse().read()
                finally:
                    connection.close()
                deadline = time.monotonic() + 5
                while not logs.records and time.monotonic() < deadline:
                    time.sleep(0.05)
                time.sleep(0.2)  # anything Waitress logs straight after the first line
        logged = chr(10).join(logs.output)
        self.assertIn("Exception while serving /files/[redacted]", logged)
        self.assertIn("disk went away while sending /files/[redacted]", logged)
        self.assertNotIn(url.removeprefix("/files/"), logged)


if __name__ == "__main__":
    unittest.main()
