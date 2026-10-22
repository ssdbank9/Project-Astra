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
        sizes = re.findall(r"^\s*max_size\s+(\S+)\s*$", caddy_text(), re.M)
        self.assertEqual(len(sizes), 1)
        waitress_cap = int(re.search(r"max_request_body_size=([\d_]+)", inspect.getsource(web.serve_waitress)).group(1))
        self.assertGreater(caddy_bytes(sizes[0]), web.IMPORT_MAX_BYTES)
        self.assertLessEqual(caddy_bytes(sizes[0]), waitress_cap)

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
        self.assertRegex(text, r"(?m)^\s*format json\s*$")
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

    def test_runbook_installs_these_files_instead_of_its_own_copies(self):
        runbook = RUNBOOK.read_text(encoding="utf-8")
        for path in ("deploy/systemd/astra.service", "deploy/caddy/Caddyfile",
                     "deploy/journald/astra.conf", "deploy/ssh/00-astra.conf", "deploy/verify-host.sh"):
            self.assertIn(path, runbook)
        self.assertNotIn("astra serve --waitress", runbook.replace("`astra serve --waitress`", ""))
        self.assertNotIn("reverse_proxy 127.0.0.1", runbook)


if __name__ == "__main__":
    unittest.main()
