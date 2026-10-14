from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from astra.auth import verify_password
from astra.db import connect
from astra.service import AstraService, now_text


class PasswordChangeServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect(Path(self.temp.name) / "astra.sqlite3")
        self.addCleanup(self.db.close)
        self.service = AstraService(self.db)
        self.primary = self.service.create_initial_owner(
            "owner@example.org", "Primary", "correct horse battery"
        )
        self.member = self.service.create_user(
            self.primary, "member@example.org", "Member", "temporary member password"
        )

    def add_session(self, user_id: str, token_hash: str) -> None:
        self.db.execute(
            "INSERT INTO sessions VALUES(?,?,?,?,?)",
            (token_hash, user_id, "csrf-" + token_hash, now_text(), "2999-01-01T00:00:00+00:00"),
        )

    def session_hashes(self, user_id: str) -> set[str]:
        return {row[0] for row in self.db.execute(
            "SELECT token_hash FROM sessions WHERE user_id=?", (user_id,)
        )}

    def test_new_accounts_require_a_change_but_initial_owner_is_unchanged(self):
        self.assertFalse(self.primary.get("must_change_password", 0))
        self.assertTrue(self.member["must_change_password"])

    def test_owner_reset_marks_the_temporary_password_for_change(self):
        reset = self.service.reset_user_password(
            self.primary, self.member["id"], "new temporary password"
        )
        self.assertTrue(reset["must_change_password"])

    def test_self_change_clears_flag_audits_and_keeps_only_current_session(self):
        self.add_session(self.member["id"], "current-session")
        self.add_session(self.member["id"], "other-session")

        changed = self.service.change_own_password(
            self.member, "temporary member password", "permanent member password",
            keep_session="current-session",
        )

        self.assertFalse(changed["must_change_password"])
        self.assertEqual(self.session_hashes(self.member["id"]), {"current-session"})
        stored = self.db.execute(
            "SELECT password_hash FROM users WHERE id=?", (self.member["id"],)
        ).fetchone()[0]
        self.assertTrue(verify_password("permanent member password", stored))
        [event] = self.db.execute(
            "SELECT event_type,detail_json FROM user_events WHERE target_user_id=?",
            (self.member["id"],),
        ).fetchall()
        self.assertEqual(event["event_type"], "password_changed")
        detail = json.loads(event["detail_json"])
        self.assertEqual(detail["sessions_revoked"], 1)
        self.assertNotIn("temporary member password", event["detail_json"])
        self.assertNotIn("permanent member password", event["detail_json"])

    def test_wrong_current_or_short_new_password_changes_nothing(self):
        self.add_session(self.member["id"], "current-session")
        before_hash = self.db.execute(
            "SELECT password_hash FROM users WHERE id=?", (self.member["id"],)
        ).fetchone()[0]
        before_events = self.db.execute("SELECT COUNT(*) FROM user_events").fetchone()[0]
        before_sessions = self.session_hashes(self.member["id"])

        for current, new in (
            ("wrong current password", "permanent member password"),
            ("temporary member password", "short"),
        ):
            with self.subTest(current=current, new=new):
                with self.assertRaises(ValueError):
                    self.service.change_own_password(
                        self.member, current, new, keep_session="current-session"
                    )
                self.assertEqual(self.db.execute(
                    "SELECT password_hash FROM users WHERE id=?", (self.member["id"],)
                ).fetchone()[0], before_hash)
                self.assertEqual(self.db.execute(
                    "SELECT COUNT(*) FROM user_events"
                ).fetchone()[0], before_events)
                self.assertEqual(self.session_hashes(self.member["id"]), before_sessions)


if __name__ == "__main__":
    unittest.main()
