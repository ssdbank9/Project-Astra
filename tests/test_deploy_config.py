"""The host configuration in deploy/ keeps Astra loopback-only, least-privileged and secret-free."""
import inspect
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from astra import __main__ as cli
from astra import web
from astra.attachment_storage import DEFAULT_UPLOAD_LIMIT, HARD_UPLOAD_LIMIT, upload_ceiling

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy"
UNIT = DEPLOY / "systemd" / "astra.service"
CADDYFILE = DEPLOY / "caddy" / "Caddyfile"
SSHD = DEPLOY / "ssh" / "00-astra.conf"
VERIFY = DEPLOY / "verify-host.sh"
RUNBOOK = ROOT / "docs" / "handoff" / "DEPLOYMENT_RUNBOOK.md"


def unit_settings():
    """Every Key=value line of the unit, keeping repeated keys in order."""
    settings = {}
    for line in UNIT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "[")):
            continue
        key, _, value = line.partition("=")
        settings.setdefault(key, []).append(value)
    return settings


def caddy_text():
    """The Caddyfile without comment lines, so commented-out directives do not count."""
    return "\n".join(
        line for line in CADDYFILE.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("#")
    )


def caddy_bytes(size):
    number, unit = re.fullmatch(r"(\d+)\s*([KMG]i?B)", size).groups()
    scale = {"KB": 10**3, "MB": 10**6, "GB": 10**9, "KiB": 2**10, "MiB": 2**20, "GiB": 2**30}[unit]
    return int(number) * scale


class DeployServiceTests(unittest.TestCase):
    def test_service_listens_on_loopback_at_the_port_caddy_proxies_to(self):
        settings = unit_settings()
        self.assertEqual(len(settings["ExecStart"]), 1)
        args = settings["ExecStart"][0].split()
        self.assertEqual(args[:3], ["/opt/astra/app/.venv/bin/astra", "serve", "--waitress"])
        host = args[args.index("--host") + 1]
        port = args[args.index("--port") + 1]
        self.assertEqual(host, "127.0.0.1")
        # The CLI parses exactly these arguments and its loopback guard lets them through.
        with mock.patch.object(cli, "_run") as run:
            cli.main(args[1:])
        parsed = run.call_args.args[0]
        self.assertEqual((parsed.host, parsed.port, parsed.waitress), ("127.0.0.1", 8765, True))
        self.assertEqual(re.findall(r"^\s*reverse_proxy\s+(\S+)\s*$", caddy_text(), re.M), [f"{host}:{port}"])

    def test_service_runs_unprivileged_and_writes_only_the_database_folder(self):
        settings = unit_settings()
        self.assertEqual((settings["User"], settings["Group"]), (["astra"], ["astra"]))
        self.assertEqual(settings["ProtectSystem"], ["strict"])
        self.assertEqual(settings["ReadWritePaths"], ["/srv/astra/data"])
        self.assertIn("Environment", settings)
        env = dict(v.partition("=")[::2] for v in settings["Environment"])
        self.assertEqual(env["ASTRA_HOME"], "/srv/astra/data")
        self.assertEqual(env["ASTRA_SECURE_COOKIES"], "1")
        self.assertNotIn("ASTRA_ATTACHMENT_ROOTS", env)
        for key, value in {
            "NoNewPrivileges": "yes", "CapabilityBoundingSet": "", "AmbientCapabilities": "",
            "ProtectHome": "yes", "PrivateTmp": "yes", "PrivateDevices": "yes", "UMask": "0077",
            "RestrictSUIDSGID": "yes", "IPAddressDeny": "any", "IPAddressAllow": "localhost",
        }.items():
            self.assertEqual(settings.get(key), [value], key)
        self.assertNotIn("EnvironmentFile", settings)


class DeployCaddyTests(unittest.TestCase):
    def test_body_limit_sits_between_astra_import_limit_and_waitress_cap(self):
        text = caddy_text()
        limits = dict(re.findall(r"^\s*request_body\s+@(\w+)\s*\{\s*max_size\s+(\S+)\s*\}", text, re.M))
        self.assertEqual(set(limits), {"upload", "other"})
        self.assertEqual(len(re.findall(r"^\s*max_size\s", text, re.M)), 2)
        self.assertIn("max_request_body_size=upload_ceiling()", inspect.getsource(web.serve_waitress))
        with mock.patch.dict("os.environ", {"ASTRA_UPLOAD_CEILING_MB": ""}):
            waitress_cap = upload_ceiling()
        # Every other route: above the import limit, so Astra answers an oversized import.
        self.assertGreater(caddy_bytes(limits["other"]), web.IMPORT_MAX_BYTES)
        self.assertLess(caddy_bytes(limits["other"]), caddy_bytes(limits["upload"]))
        # MXY7BG: the upload route admits exactly the shipped server ceiling (the 25 MiB default
        # limit), which Waitress admits too; raising it is a runbook step for both at once.
        self.assertEqual(caddy_bytes(limits["upload"]), DEFAULT_UPLOAD_LIMIT)
        self.assertEqual(caddy_bytes(limits["upload"]), waitress_cap)
        self.assertLess(caddy_bytes(limits["upload"]), HARD_UPLOAD_LIMIT)
        # Raising it is documented as one step for Caddy and the unit together.
        runbook = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("ASTRA_UPLOAD_CEILING_MB", runbook)
        self.assertIn("ASTRA_UPLOAD_CEILING_MB", CADDYFILE.read_text(encoding="utf-8"))

    def test_the_larger_limit_applies_to_the_upload_route_only(self):
        text = caddy_text()
        upload = re.search(r"^\s*@upload\s+path_regexp\s+upload\s+(\S+)\s*$", text, re.M).group(1)
        other = re.search(r"^\s*@other\s+not\s+path_regexp\s+other\s+(\S+)\s*$", text, re.M).group(1)
        self.assertEqual(upload, other)
        pattern = re.compile(upload)
        self.assertTrue(pattern.search("/api/tasks/abc123/files"))
        for path in ("/api/tasks/abc/files/x", "/api/tasks/abc/links", "/api/import/preview",
                     "/api/tasks/a/b/files", "/x/api/tasks/abc/files"):
            self.assertIsNone(pattern.search(path), path)

    def test_security_headers_match_what_astra_sends(self):
        text = caddy_text()
        headers = dict(re.findall(r'^\s*([A-Za-z-]+)\s+"([^"]*)"\s*$', text, re.M))
        self.assertEqual(headers["Content-Security-Policy"], web.CONTENT_SECURITY_POLICY)
        # The other three are literals in web.py: read them from the source, so a change there shows here.
        sent = dict(re.findall(r"send_header\(['\"]([A-Za-z-]+)['\"],\s*['\"]([^'\"]+)['\"]\)", inspect.getsource(web)))
        for name in ("X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"):
            self.assertEqual(headers[name], sent[name], name)
        # HSTS stays off until HTTPS and renewal are proven on the host.
        self.assertNotIn("Strict-Transport-Security", text)

    def test_one_site_with_the_duckdns_placeholder_and_a_rolled_json_access_log(self):
        text = caddy_text()
        self.assertEqual(re.findall(r"^(\S+)\s*\{\s*$", text, re.M), ["<name>.duckdns.org"])
        self.assertRegex(text, r"output file /var/log/caddy/astra-access\.log")
        self.assertRegex(text, r"(?m)^\s*wrap json\s*$")
        # MXY7BG slice 3: a direct link's token never reaches the access log.
        filters = re.findall(r'(?m)^\s*request>uri regexp "([^"]+)" "([^"]+)"\s*$', text)
        # Twice, and the same: once for Caddy's own log (the global block, before the site),
        # which records the request of an error such as a 502, and once for the access log.
        own_log, site = text.split("\n<name>.duckdns.org {", 1)
        self.assertEqual((own_log.count("request>uri regexp"), site.count("request>uri regexp")), (1, 1))
        self.assertRegex(own_log, r"(?m)^\{\n(\t#[^\n]*\n)*\tlog \{\n\t\tformat filter \{\n\t\t\twrap json\n")
        self.assertEqual(filters[0], filters[1])
        pattern, replacement = filters[0]
        # Every spelling Waitress would decode to /files/<token>, and a token carried anywhere
        # else in the URI, is logged as /files/redacted and nothing more.
        for uri in ("/files/Abc-_123", "/files/Abc-_123?x=1", "/files//Abc-_123", "/files/x/Abc-_123/y",
                    "//files/Abc-_123", "/%66iles/Abc-_123", "/f%69les/Abc-_123", "/fi%6Ces/Abc-_123",
                    "/fil%65s/Abc-_123", "/file%73/Abc-_123", "/files%2FAbc-_123", "/files%2fAbc-_123",
                    "%2Ffiles/Abc-_123", "/%66%69%6c%65%73%2fAbc-_123", "/FILES/Abc-_123", "/%46%49%4C%45%53/Abc-_123",
                    "http://host/files/Abc-_123", "/x?next=/files/Abc-_123"):
            self.assertEqual(re.sub(pattern, replacement, uri), "/files/redacted", uri)
        for uri in ("/files/", "/api/login", "/api/tasks/abc/files", "/api/tasks/abc/files?x=1", "/static/app.js",
                    "/profiles/abc"):
            self.assertEqual(re.sub(pattern, replacement, uri), uri)
        for directive in ("roll_size", "roll_keep", "roll_keep_for"):
            self.assertRegex(text, rf"(?m)^\s*{directive}\s+\S+\s*$")


class DeployHostTests(unittest.TestCase):
    def test_ssh_refuses_passwords_and_root(self):
        lines = [l.split() for l in SSHD.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
        self.assertEqual(dict(lines), {
            "PasswordAuthentication": "no", "PermitRootLogin": "no", "KbdInteractiveAuthentication": "no",
        })

    def test_no_file_holds_a_secret_and_all_use_lf(self):
        # A value assigned to a secret-looking name, a private key, or a DuckDNS update URL
        # (which carries the account token). Comment lines are prose, not settings.
        secret = re.compile(
            r"[\w.-]*(password|passwd|secret|token|api[_-]?key)[\w.-]*\s*[=:]\s*\S"
            r"|BEGIN [A-Z ]*PRIVATE KEY|duckdns\.org/update\?",
            re.I | re.M,
        )
        files = [p for p in DEPLOY.rglob("*") if p.is_file()]
        self.assertGreaterEqual(len(files), 6)
        for path in files:
            data = path.read_bytes()
            self.assertNotIn(b"\r", data, path)
            text = data.decode("utf-8")
            settings = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
            self.assertIsNone(secret.search(settings), path)
            # A key or a DuckDNS update URL is a secret even inside a comment.
            self.assertIsNone(re.search(r"BEGIN [A-Z ]*PRIVATE KEY|duckdns\.org/update\?", text), path)

    def test_deploy_files_stay_lf_in_every_checkout(self):
        # core.autocrlf=true on Windows would otherwise write CRLF into these on the next checkout.
        rules = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
        self.assertIn("deploy/** text eol=lf", rules)

    def test_verify_script_is_valid_posix_shell_and_read_only(self):
        text = VERIFY.read_text(encoding="utf-8")
        for write in ("systemctl start", "systemctl restart", "systemctl reload", "systemctl enable",
                      "rm ", "chmod", "chown", "tee ", "> /", "iptables -I", "iptables -D"):
            self.assertNotIn(write, text)
        sh = shutil.which("sh")
        if sh is None:
            self.skipTest("no POSIX sh on PATH")
        result = subprocess.run([sh, "-n", str(VERIFY)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_object_storage_drop_in_is_an_example_that_opens_no_network_and_holds_no_key(self):
        # MXY7BG slice 4: optional, installed only on Aly's decision (runbook stage 11.5).
        text = (DEPLOY / "systemd" / "object-storage.conf.example").read_text(encoding="utf-8")
        active = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(active, ["[Service]", "EnvironmentFile=/etc/astra/storage.env"])
        self.assertNotIn("IPAddressAllow=any", text.replace(" ", ""))
        # The unit itself still reaches nothing but this machine.
        unit = (DEPLOY / "systemd" / "astra.service").read_text(encoding="utf-8")
        self.assertIn("\nIPAddressDeny=any\nIPAddressAllow=localhost\n", unit)
        self.assertNotIn("EnvironmentFile", unit)
        runbook = RUNBOOK.read_text(encoding="utf-8")
        for needed in ("deploy/systemd/object-storage.conf.example", "storage-check --backend s3",
                       "storage-migrate --to s3", "storage-migrate --to folder", "storage-prune", "storage-verify",
                       "storage-command.lock", "/etc/astra/storage.env"):
            self.assertIn(needed, runbook)
        # The key is read from the settings file or the environment: no command takes it.
        from astra import __main__ as entry
        import inspect
        self.assertNotIn("secret", inspect.getsource(entry).lower().replace("secrets", ""))

    def test_runbook_installs_these_files_instead_of_its_own_copies(self):
        runbook = RUNBOOK.read_text(encoding="utf-8")
        for path in ("deploy/systemd/astra.service", "deploy/caddy/Caddyfile",
                     "deploy/journald/astra.conf", "deploy/ssh/00-astra.conf", "deploy/verify-host.sh",
                     "deploy/backup/astra-backup", "deploy/systemd/astra-backup.service",
                     "deploy/systemd/astra-backup.timer"):
            self.assertIn(path, runbook)
        # The backup script is installed from deploy/, not pasted from an inline copy.
        self.assertNotIn("age -R /srv/astra/backup-recipient.txt -o", runbook)
        self.assertNotIn("astra serve --waitress", runbook.replace("`astra serve --waitress`", ""))
        self.assertNotIn("reverse_proxy 127.0.0.1", runbook)


BACKUP_SCRIPT = DEPLOY / "backup" / "astra-backup"
BACKUP_UNIT = DEPLOY / "systemd" / "astra-backup.service"
BACKUP_TIMER = DEPLOY / "systemd" / "astra-backup.timer"


def script_lines():
    """The backup script's commands, without comments or blank lines."""
    return [line.strip() for line in BACKUP_SCRIPT.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


class DeployBackupTests(unittest.TestCase):
    """Runbook stage 11: the nightly backup, its 7/4/3 retention and the off-site copy through
    Aly's write-only pre-authenticated request (Aly, 2026-11-19, Q10)."""

    def test_the_script_leaves_nothing_readable_even_when_stopped(self):
        lines = script_lines()
        self.assertEqual(BACKUP_SCRIPT.read_text(encoding="utf-8").splitlines()[0], "#!/bin/sh")
        self.assertIn("set -eu", lines)
        self.assertIn("umask 027", lines)
        # The plaintext snapshot and every unfinished file are removed however the run ends;
        # dash runs no EXIT trap when killed, so a signal is turned into an exit first.
        self.assertIn("""trap 'rm -f "$DB" "$DB.age.part" "$FILES.age.part" "$FILES.status"' EXIT""", lines)
        self.assertIn("trap 'exit 1' HUP INT TERM", lines)
        # What a power cut left behind is removed at the next run (under the lock).
        self.assertIn('rm -f "$DIR"/astra-*.sqlite3 "$DIR"/uploads-*.tar "$DIR"/*.part "$DIR"/*.status', lines)
        self.assertLess(lines.index('flock -n 9 || fail "another backup is running"'),
                        lines.index('rm -f "$DIR"/astra-*.sqlite3 "$DIR"/uploads-*.tar "$DIR"/*.part "$DIR"/*.status'))

    def test_an_unfinished_file_never_takes_a_backups_name(self):
        lines = script_lines()
        self.assertIn('age -R "$RECIPIENT" -o "$DB.age.part" "$DB"', lines)
        self.assertIn('mv "$DB.age.part" "$DB.age"', lines)
        self.assertIn('mv "$FILES.age.part" "$FILES.age"', lines)
        self.assertLess(lines.index('rm -f "$DB"'), lines.index('mv "$DB.age.part" "$DB.age"'))
        # tar's status is kept in a file (a pipeline reports only its last command); 0 or 1
        # (a file changed while it read) keeps the archive, anything else does not.
        self.assertIn('if { tar -C "$DATA" -cf - uploads/objects; echo $? > "$FILES.status"; } \\', lines)
        self.assertIn('if [ "$TAR_STATUS" = 0 ] || [ "$TAR_STATUS" = 1 ]; then', lines)
        for line in lines:
            self.assertNotIn('-o "$DB.age"', line.replace('-o "$DB.age.part"', ""))

    def test_the_off_site_copy_comes_first_and_a_failure_still_fails_the_run(self):
        lines = script_lines()
        offsite = "offsite || RESULT=1"
        prune = '"$ASTRA" backup-prune --dir "$DIR" || RESULT=1'
        self.assertIn(offsite, lines)
        self.assertIn(prune, lines)
        self.assertLess(lines.index('mv "$DB.age.part" "$DB.age"'), lines.index(offsite))
        self.assertLess(lines.index(offsite), lines.index('if { tar -C "$DATA" -cf - uploads/objects; '
                                                          'echo $? > "$FILES.status"; } \\'))
        self.assertLess(lines.index(offsite), lines.index(prune))
        self.assertEqual(lines[-1], 'exit "$RESULT"')
        # One run at a time.
        self.assertIn('exec 9> "$STATE/lock"', lines)
        self.assertIn('flock -n 9 || fail "another backup is running"', lines)
        # The CLI the script calls exists and keeps the approved counts.
        from astra import backup_retention
        self.assertEqual((backup_retention.KEEP_DAILY, backup_retention.KEEP_WEEKLY,
                          backup_retention.KEEP_MONTHLY), (7, 4, 3))
        self.assertIn('"backup-prune"', inspect.getsource(cli))

    def test_the_off_site_copy_is_required_and_its_url_never_reaches_a_command_line(self):
        text = BACKUP_SCRIPT.read_text(encoding="utf-8")
        lines = script_lines()
        commands = "\n".join(lines)
        self.assertIn("PAR_FILE=${ASTRA_BACKUP_PAR_FILE:-/srv/astra/backup-par-url}", lines)
        self.assertIn('test -s "$PAR_FILE" || { echo "astra-backup: NO OFF-SITE COPY: $PAR_FILE is missing or empty" '
                      '>&2; return 1; }', lines)
        # curl reads the URL from standard input (-K -), so `ps` never shows it; -q keeps a
        # .curlrc out and --globoff keeps [] and {} from being expanded (or echoed in an error).
        self.assertIn("""if printf 'url = "%s%s"\\n' "$PAR" "$1" \\""", lines)
        self.assertIn("| curl -q --globoff --fail --silent --show-error --retry 3 --max-time 900 \\", lines)
        self.assertIn('--upload-file "$DB.age" --config -; then', lines)
        self.assertEqual(commands.count("curl "), 1)
        self.assertNotRegex(commands, r'curl[^\n]*\$PAR')
        # Only https, one URL, nothing that could break out of curl's quoted config value.
        self.assertIn("*[[:space:]\\\"\\\\\\[\\]\\{\\}]*)", text)
        self.assertIn("https://*/) ;;", text)
        # Daily every night; weekly and monthly on the first good night of the ISO week and
        # the month, remembered in the state folder; all from one clock reading.
        self.assertIn("set -- $(date -u '+%Y%m%dT%H%M%SZ %G-W%V %Y-%m')", lines)
        self.assertEqual(commands.count("date "), 1)
        for line in ('upload "daily/$NAME" || return 1',
                     'if [ "$(cat "$STATE/last-weekly" 2>/dev/null || true)" != "$WEEK" ]; then',
                     'upload "weekly/$NAME" || return 1', 'echo "$WEEK" > "$STATE/last-weekly"',
                     'if [ "$(cat "$STATE/last-monthly" 2>/dev/null || true)" != "$MONTH" ]; then',
                     'upload "monthly/$NAME" || return 1', 'echo "$MONTH" > "$STATE/last-monthly"'):
            self.assertIn(line, lines)
        self.assertLess(lines.index('upload "weekly/$NAME" || return 1'),
                        lines.index('echo "$WEEK" > "$STATE/last-weekly"'))
        # Nothing on this server deletes or lists in the bucket.
        self.assertNotRegex(text, r"-X\s*DELETE|--request\s+DELETE|\boci\b")

    def test_the_script_is_valid_posix_shell(self):
        sh = shutil.which("sh")
        if sh is None:
            self.skipTest("no POSIX sh on PATH")
        result = subprocess.run([sh, "-n", str(BACKUP_SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_backup_unit_runs_unprivileged_and_writes_only_two_folders(self):
        settings = {}
        for line in BACKUP_UNIT.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "[")):
                key, _, value = line.partition("=")
                settings.setdefault(key, []).append(value)
        for key, value in (("Type", "oneshot"), ("User", "astra"), ("Group", "astra"),
                           ("StateDirectory", "astra-backup"), ("TimeoutStartSec", "2h"),
                           ("SystemCallFilter", "@system-service"),
                           ("ExecStart", "/usr/local/bin/astra-backup"), ("NoNewPrivileges", "yes"),
                           ("ProtectSystem", "strict"), ("ProtectHome", "yes"), ("PrivateTmp", "yes"),
                           ("CapabilityBoundingSet", ""),
                           ("ReadWritePaths", "/srv/astra/data /srv/astra/backups")):
            self.assertEqual(settings.get(key), [value], key)
        timer = BACKUP_TIMER.read_text(encoding="utf-8")
        self.assertIn("\nOnCalendar=*-*-* 21:30:00 UTC\nPersistent=true\n", timer)
        self.assertIn("\nWantedBy=timers.target\n", timer)

    def test_the_runbook_no_longer_holds_the_timer_back_for_missing_retention(self):
        runbook = RUNBOOK.read_text(encoding="utf-8")
        self.assertNotIn("Do not install or enable this timer yet", runbook)
        self.assertNotIn("Do not add age-based deletion here", runbook)
        for needed in ("astra backup-prune", "/srv/astra/backup-par-url", "daily/", "weekly/", "monthly/"):
            self.assertIn(needed, runbook)


if __name__ == "__main__":
    unittest.main()
