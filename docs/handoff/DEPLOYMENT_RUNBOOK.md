# Astra deployment runbook — Oracle Cloud Always Free, DuckDNS, Caddy

This runbook covers phase D of `NEXT_STEPS.md`. It turns a tagged Astra release
into a public HTTPS site on an Oracle Cloud Always Free VM, with a free DuckDNS
name and Caddy in front. Aly chose this setup on 2026-09-20: zero direct cost,
users open an HTTPS link in a normal browser and sign in with their own Astra
account, no Tailscale, and nothing may silently upgrade to a paid resource.

Read this first:

- **Nothing here may be run until Aly says to start the deployment.** Aly does
  every account, credential, DNS and payment step, and types every password.
- Steps marked **[ALY]** need Aly personally. Steps marked **[AGENT]** can be
  prepared or run by the agent (an AI coding agent or a human developer) once
  Aly has given it SSH access.
- Every `astra` command below matches `src/astra/__main__.py` at `0b90ceb`:
  `init-owner`, `serve`, `transfer-primary`, `reset-password`. There is no
  `astra backup` or `astra --version` yet; the runbook says where a stop-gap
  is used until those are built (`NEXT_STEPS.md` B3 and C2).
- Operating-system, Caddy, DuckDNS, OCI and encryption commands are standard
  commands for those tools, but they were not run for this handoff. They are
  marked "verify" where the exact flags or menu names should be checked against
  the vendor's current documentation at deployment time.
- Do not put any token, key or password in the repository. It is public.

Placeholders used below:

| Placeholder | Meaning | Who provides it |
| --- | --- | --- |
| `<name>` | The DuckDNS subdomain, so the site is `https://<name>.duckdns.org` | Aly |
| `<ip>` | The VM's public IP address | OCI, after stage 1 |
| `<tag>` | The release tag, for example `v0.2.0` (phase C) | The agent prepares, Aly approves |
| `<owner-email>` | Aly's sign-in email for Astra | Aly |

---

## Stage 0 — Before you start

Checklist:

- [ ] Phases A to C are done, or Aly has decided to run a trial deployment of a
  specific commit with synthetic data only.
- [ ] A release tag exists (`git ls-remote --tags origin` shows `<tag>`), or you
  have the exact commit SHA to deploy.
- [ ] Aly has chosen the DuckDNS name, the OCI home region, the Ubuntu version
  and the backup approach (`OPEN_QUESTIONS.md` Q7 and Q10).

**[ALY]** Create an SSH key on the Windows PC (PowerShell; OpenSSH ships with
Windows 10 and 11; verify):

```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\astra_oci"
```

Keep the private key file on the PC only. The `.pub` file is uploaded to OCI in
stage 1.

**[ALY]** Create an encryption key pair for backups, so the server can write
backups it cannot read. This runbook uses `age` (install it on Windows from its
official releases; verify):

```powershell
age-keygen -o "$env:USERPROFILE\Documents\AstraKeys\astra-backup-key.txt"
```

The command prints a public key starting with `age1...`. Only that public key
goes to the server. Keep the key file offline and backed up; without it no
backup can be restored. (`gpg` public-key encryption works the same way if Aly
prefers it.)

Verification: `ssh-keygen` created `astra_oci` and `astra_oci.pub`; the age key
file exists and its public key is written down.

---

## Stage 1 — Provision the VM **[ALY]**

In the OCI console (menu names may differ; verify):

1. Sign in to Aly's Oracle Cloud account. Use the tenancy's home region; the
   2026-09-20 handoff notes Always Free compute is offered there.
2. Create a compute instance:
   - Image: Canonical Ubuntu LTS. 24.04 is recommended because Astra needs
     Python 3.11 or newer (`requires-python = ">=3.11"`); verify the image's
     Python version in stage 4.
   - Shape: one marked "Always Free eligible" that is actually available in the
     region. If capacity is unavailable, try later or another availability
     domain; do not pick a paid shape.
   - Networking: a public IPv4 address.
   - SSH key: upload `astra_oci.pub`.
   - Boot volume: the default size within the Always Free allowance.
3. Note the public IP (`<ip>`) and the default user name shown for the image
   (usually `ubuntu` on Ubuntu images; verify).

Verification, from PowerShell:

```powershell
ssh -i "$env:USERPROFILE\.ssh\astra_oci" ubuntu@<ip> "uname -a; lsb_release -ds"
```

It prints the Ubuntu version. If it hangs, the network rules in stage 2 are the
likely cause.

Rollback: terminate the instance in the console. Nothing else exists yet.

---

## Stage 2 — Open the network **[ALY for the console, AGENT for the host]**

**[ALY]** In the OCI console, on the instance's subnet security list or network
security group, allow inbound TCP:

- 22 only from Aly's own public address or ISP range (`<aly-ip>/32`). This
  was decided on 2026-09-20. If Aly's address changes, update the rule in
  the console before connecting, or use the OCI Bastion service. Never open
  22 to `0.0.0.0/0` unless Aly decides it explicitly, and write that
  decision in `DECISIONS_LOG.md`;
- 80 from anywhere (Caddy needs it for certificates and redirects);
- 443 from anywhere.

A new network's default security list usually already has an ingress rule for
22 from `0.0.0.0/0` (verify in the console). Change that rule's source to
`<aly-ip>/32`, or delete it; adding a second, narrower rule next to it leaves
22 open to everyone.

Do not open 8765. Astra listens only on `127.0.0.1`.

Verification: the security list (and any network security group on the
instance) has no ingress rule for 22 whose source is `0.0.0.0/0`.

**[AGENT]** On the VM, check the host firewall. Oracle's Ubuntu images are
known to ship their own `iptables` rules (verify on the actual image):

```bash
sudo iptables -L INPUT -n --line-numbers
```

If there is a `REJECT` rule, insert ACCEPT rules for 80 and 443 above it, then
save. The line number `N` is the position of the `REJECT` rule in the output
above:

```bash
sudo iptables -I INPUT N -p tcp -m state --state NEW --dport 80 -j ACCEPT
sudo iptables -I INPUT N -p tcp -m state --state NEW --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

Verification: `sudo iptables -L INPUT -n --line-numbers` lists the two ACCEPT
rules above the REJECT. Ports 80 and 443 are tested end to end in stage 8.

Rollback: delete the two rules (`sudo iptables -D INPUT <line>`) and save.

---

## Stage 3 — Harden the operating system **[AGENT]**

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y unattended-upgrades fail2ban git python3-venv curl age
sudo dpkg-reconfigure -plow unattended-upgrades
```

(`age` is in Ubuntu's repositories on recent releases; verify, or install
`gnupg` instead if Aly chose gpg.)

Turn off SSH passwords and root login:

```bash
printf 'PasswordAuthentication no\nPermitRootLogin no\nKbdInteractiveAuthentication no\n' | sudo tee /etc/ssh/sshd_config.d/00-astra.conf
sudo sshd -t
sudo sshd -T | grep -Ei '^(passwordauthentication|permitrootlogin|kbdinteractiveauthentication) '
sudo systemctl reload ssh
```

The `sshd -T` line must print `no` for all three. sshd keeps the first value
it reads for each keyword and reads `sshd_config.d/*.conf` in name order, so
the file is `00-astra.conf`, ahead of any file the cloud image ships.

`fail2ban` protects SSH with its default `sshd` jail once installed (verify with
`sudo fail2ban-client status sshd`).

Keep the journal small so logs cannot fill the disk:

```bash
sudo mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nSystemMaxUse=200M\n' | sudo tee /etc/systemd/journald.conf.d/astra.conf
sudo systemctl restart systemd-journald
```

Verification:

- Open a second PowerShell window and SSH in again with the key before closing
  the first one. It works.
- `ssh -o PubkeyAuthentication=no ubuntu@<ip>` is refused.
- `sudo fail2ban-client status sshd` shows the jail.

Rollback: remove `/etc/ssh/sshd_config.d/00-astra.conf` and reload `ssh` (only
from a session that is still open).

---

## Stage 4 — Service user, folders and Python **[AGENT]**

Create a system user with no login shell, and the folders:

```bash
sudo useradd --system --home-dir /srv/astra --shell /usr/sbin/nologin astra
sudo mkdir -p /opt/astra /srv/astra/data /srv/astra/backups
sudo chown astra:astra /srv/astra /srv/astra/data /srv/astra/backups
sudo chmod 700 /srv/astra/data
sudo chmod 750 /srv/astra /srv/astra/backups
sudo usermod -aG astra ubuntu
```

- `/opt/astra/app` holds the code, owned by root, readable by everyone.
- `/srv/astra/data` is `ASTRA_HOME`: only `astra` can read it. It will hold
  `astra.sqlite3`, `astra.sqlite3-wal` and `astra.sqlite3-shm`.
- `/srv/astra/backups` holds encrypted backups; the `ubuntu` user can read them
  through the `astra` group, so Aly can copy them down with `scp`.

Check Python:

```bash
python3 --version
```

It must print 3.11 or newer.

Verification: `ls -ld /srv/astra/data` shows `drwx------ astra astra`.

---

## Stage 5 — Install Astra **[AGENT]**

The repository is public, so no credentials are needed to clone it.

```bash
sudo git clone https://github.com/ssdbank9/Project-Astra.git /opt/astra/app
cd /opt/astra/app
sudo git checkout <tag>
sudo python3 -m venv /opt/astra/app/.venv
sudo /opt/astra/app/.venv/bin/python -m pip install --no-deps /opt/astra/app
```

Before a tag exists, check out the exact commit SHA Aly approved instead of
`<tag>`. Never deploy a moving branch head.

`--no-deps` is safe because Astra has no runtime dependencies on Linux
(`tzdata` is Windows-only). The build step still downloads `setuptools` into an
isolated build environment.

Verification:

```bash
sudo git -C /opt/astra/app rev-parse HEAD
sudo -u astra env ASTRA_HOME=/srv/astra/data /opt/astra/app/.venv/bin/astra --help
/opt/astra/app/.venv/bin/python -c "import zoneinfo; print(zoneinfo.ZoneInfo('Asia/Karachi'))"
```

- The SHA matches the approved release.
- `astra --help` lists `init-owner`, `serve`, `transfer-primary`,
  `reset-password`.
- The timezone line prints `Asia/Karachi` (the app's "today" uses it).

Rollback: `sudo rm -rf /opt/astra/app` and repeat.

---

## Stage 6 — Create the first owner **[ALY types the password]**

Run over an interactive SSH session (`ssh -t`), because the password prompt
needs a terminal:

```bash
sudo -u astra env ASTRA_HOME=/srv/astra/data /opt/astra/app/.venv/bin/astra init-owner --email <owner-email> --name "Aly Jafferani"
```

It asks for the password twice without echo (at least 8 characters) and prints
`Created owner <owner-email> in /srv/astra/data/astra.sqlite3`. The first owner
is the primary owner.

Verification:

```bash
sudo ls -l /srv/astra/data
```

`astra.sqlite3` exists and belongs to `astra`. Running `init-owner` again
refuses with "An owner account already exists."

For a trial with synthetic data, use a test email here and create test users
from the People screen later. Start with synthetic projects, not real private
data (2026-09-20 plan, Gate 7).

Rollback: stop here and delete `/srv/astra/data/astra.sqlite3*` to start again.

---

## Stage 7 — Run Astra under systemd **[AGENT]**

Create `/etc/systemd/system/astra.service`:

```ini
[Unit]
Description=Astra project tracker
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=astra
Group=astra
Environment=ASTRA_HOME=/srv/astra/data
Environment=ASTRA_SECURE_COOKIES=1
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/astra/app/.venv/bin/astra serve --host 127.0.0.1 --port 8765
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=/srv/astra/data

[Install]
WantedBy=multi-user.target
```

Why each setting matters:

- `--host 127.0.0.1` keeps Astra off the public interface. Only Caddy talks to
  it. The README says never to expose the development server directly.
- `ASTRA_SECURE_COOKIES=1` marks the session cookie `Secure`, which is required
  behind HTTPS.
- `ASTRA_ATTACHMENT_ROOTS` is deliberately not set. Attachment links point at
  files on the server's own disk, which users cannot reach, so they stay off
  until hosted uploads (MXY7BG) exist.
- Migrations run automatically when the server starts (`AstraServer` opens the
  database through `connect()`, which calls `migrate()`).

Start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now astra
```

Verification:

```bash
systemctl status astra --no-pager
sudo ss -ltnp | grep 8765
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/
journalctl -u astra -n 20 --no-pager
```

- Status is `active (running)`.
- `ss` shows `127.0.0.1:8765` only, never `0.0.0.0:8765`.
- `curl` prints `200` (`GET /` serves the page without signing in; do not use
  `curl -I`, because Astra has no `HEAD` handler).
- The journal shows `Astra is running at http://127.0.0.1:8765`.

Rollback: `sudo systemctl disable --now astra`.

---

## Stage 8 — DuckDNS name **[ALY for the account, AGENT for the updater]**

**[ALY]** Sign in at duckdns.org, create `<name>`, point it at `<ip>`, and copy
the account token. Treat the token like a password.

**[AGENT]** Keep the IP current with a small root-only script. The update URL
format below is the one DuckDNS documents on its install page (verify there):

```bash
sudo install -d -m 700 /root/duckdns
sudo sh -c 'umask 077; cat > /root/duckdns/token'
```

Aly pastes the token, presses Enter, then Ctrl+D. Then create
`/root/duckdns/update.sh` (mode 700, owner root):

```sh
#!/bin/sh
TOKEN=$(cat /root/duckdns/token)
curl -fsS -o /root/duckdns/last.txt "https://www.duckdns.org/update?domains=<name>&token=${TOKEN}&ip="
```

Run it every 5 minutes from root's crontab:

```bash
sudo chmod 700 /root/duckdns/update.sh
( sudo crontab -l 2>/dev/null; echo '*/5 * * * * /root/duckdns/update.sh' ) | sudo crontab -
sudo /root/duckdns/update.sh
```

Verification:

```bash
sudo cat /root/duckdns/last.txt
getent hosts <name>.duckdns.org
```

`last.txt` says `OK`, and the name resolves to `<ip>`. The token never appears in
the repository, in shell history (it was pasted into `cat`) or in any log file.

Rollback: remove the cron line with `sudo crontab -e` and delete
`/root/duckdns`.

---

## Stage 9 — Caddy for HTTPS **[AGENT]**

Install Caddy from its official Debian/Ubuntu packages, following
https://caddyserver.com/docs/install (the 2026-09-20 handoff cites the Caddy
reverse-proxy and automatic-HTTPS docs). Do not use a third-party script.

Replace `/etc/caddy/Caddyfile` with:

```caddy
<name>.duckdns.org {
	encode gzip
	request_body {
		max_size 6MB
	}
	header Strict-Transport-Security "max-age=31536000"
	reverse_proxy 127.0.0.1:8765
	log {
		output file /var/log/caddy/astra-access.log
	}
}
```

- Caddy gets and renews the certificate itself and redirects HTTP to HTTPS.
- `max_size 6MB` sits just above Astra's own 5 MB import limit, so Astra gives
  the friendly "The file is larger than 5 MB." message.
- The access log is the only place real client addresses are recorded, because
  Astra sees every request as coming from `127.0.0.1`.
- Start without the HSTS header if you want an easy way back to HTTP during a
  trial; add it once HTTPS is confirmed.

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Verification, from Aly's PC:

```powershell
curl.exe -sS -o NUL -w "%{http_code}`n" https://<name>.duckdns.org/
curl.exe -sS -o NUL -w "%{http_code} %{redirect_url}`n" http://<name>.duckdns.org/
Test-NetConnection <ip> -Port 8765
```

- HTTPS prints `200` with a valid certificate (no warning in the browser).
- HTTP answers with a redirect to `https://`.
- Port 8765 is not reachable (`TcpTestSucceeded : False`).

**[ALY]** Sign in at `https://<name>.duckdns.org` in a browser. In the browser's
developer tools (Application, Cookies), `astra_session` shows `Secure`,
`HttpOnly` and `SameSite=Strict`. A wrong password shows "Incorrect email or
password.".

Rollback: restore the previous Caddyfile and reload, or
`sudo systemctl stop caddy` to take the site offline.

---

## Stage 10 — Sign-in rate limiting (only if Aly agrees, Q11) **[AGENT]**

Astra never locks anyone out and does not limit guessing (Aly, 2026-09-24).
The README says a hosted deployment should rate-limit in front of Astra, and
the 2026-09-24 handoff puts that on ticket 6BXYJZ. A gentle option that bans an
address for a few minutes, without locking any account, is fail2ban reading
Caddy's log. The filter below is a starting point; test it with `fail2ban-regex`
against real log lines before enabling it (Caddy's JSON field order may differ;
verify).

`/etc/fail2ban/filter.d/astra-login.conf`:

```ini
[Definition]
failregex = "remote_ip":"<HOST>".*"uri":"/api/login".*"status":401
datepattern = "ts":{EPOCH}
```

`/etc/fail2ban/jail.d/astra-login.conf`:

```ini
[astra-login]
enabled = true
port = http,https
filter = astra-login
logpath = /var/log/caddy/astra-access.log
maxretry = 20
findtime = 10m
bantime = 15m
```

```bash
sudo fail2ban-regex /var/log/caddy/astra-access.log /etc/fail2ban/filter.d/astra-login.conf
sudo systemctl restart fail2ban
sudo fail2ban-client status astra-login
```

Verification: 20 wrong passwords from one test address within 10 minutes get
that address banned for 15 minutes; the correct password still works from any
other address.

Rollback: set `enabled = false` and restart fail2ban.

---

## Stage 11 — Backups **[AGENT builds, ALY holds the keys]**

Policy (Aly, 2026-09-20): nightly, encrypted, SQLite-consistent, off the VM to
OCI Object Storage within the free allowance, plus a copy on Aly's desktop;
RPO 24 hours, RTO 4 hours; keep 7 daily, 4 weekly, 3 monthly; only Aly controls
restore credentials; prove restore in both directions before go-live.

### 11.1 The backup script

Until `astra backup` exists (`NEXT_STEPS.md` B3), use Python's standard library
online backup API. This exact approach was tried on a scratch database for this
handoff: the copy had schema v20 and `PRAGMA integrity_check` returned `ok`.
Never copy `astra.sqlite3` with `cp` while Astra runs, because recent writes may
still be in the `-wal` file.

**[ALY]** Put the age public key on the VM:

```bash
echo 'age1...' | sudo tee /srv/astra/backup-recipient.txt
sudo chown astra:astra /srv/astra/backup-recipient.txt
```

**[AGENT]** Create `/usr/local/bin/astra-backup` (owner root, mode 755):

```sh
#!/bin/sh
set -eu
umask 027
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
PLAIN=/srv/astra/backups/astra-$STAMP.sqlite3
trap 'rm -f "$PLAIN"' EXIT
/opt/astra/app/.venv/bin/python - "$PLAIN" <<'PY'
import sqlite3, sys
src = sqlite3.connect("file:/srv/astra/data/astra.sqlite3?mode=ro", uri=True)
dst = sqlite3.connect(sys.argv[1])
src.backup(dst)
result = dst.execute("PRAGMA integrity_check").fetchone()[0]
dst.close()
src.close()
if result != "ok":
    raise SystemExit("integrity_check failed: " + result)
PY
age -R /srv/astra/backup-recipient.txt -o "$PLAIN.age" "$PLAIN"
rm -f "$PLAIN"
find /srv/astra/backups -name 'astra-*.sqlite3.age' -mtime +14 -delete
echo "backup written: $PLAIN.age"
```

(`age -R` reads recipients from a file; verify the flag with `age --help`.)

Run it nightly with a systemd timer. `/etc/systemd/system/astra-backup.service`:

```ini
[Unit]
Description=Astra nightly backup

[Service]
Type=oneshot
User=astra
Group=astra
ExecStart=/usr/local/bin/astra-backup
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=/srv/astra/data /srv/astra/backups
```

`/etc/systemd/system/astra-backup.timer` (21:30 UTC is 02:30 in Aly's UTC+5):

```ini
[Unit]
Description=Run the Astra backup every night

[Timer]
OnCalendar=*-*-* 21:30:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now astra-backup.timer
sudo systemctl start astra-backup.service
journalctl -u astra-backup -n 20 --no-pager
ls -l /srv/astra/backups
```

Verification: the journal shows "backup written", one `.age` file exists, and no
plain `.sqlite3` file is left in `/srv/astra/backups`.

### 11.2 Off-box copy to OCI Object Storage **[ALY for the bucket and access]**

Two ways; Aly picks (Q10):

- **Write-only pre-authenticated request (simplest).** Aly creates a private
  bucket and a pre-authenticated request that only permits writing objects,
  with an expiry date Aly will renew. The URL is stored on the VM in
  `/srv/astra/backup-par-url` (owner astra, mode 600). Add to the end of
  `astra-backup`:

  ```sh
  PAR=$(cat /srv/astra/backup-par-url)
  curl -fsS -X PUT --data-binary @"$PLAIN.age" "${PAR}daily/astra-$STAMP.sqlite3.age"
  ```

  On Sundays also upload to `weekly/`, and on the 1st of the month to
  `monthly/`. Aly adds bucket lifecycle rules that delete `daily/` objects after
  7 days, `weekly/` after 28 days and `monthly/` after 92 days, which gives the
  7/4/3 retention without the VM ever deleting anything. (Pre-authenticated
  request and lifecycle rule options: verify in the OCI console.)
- **OCI CLI with instance principal.** More setup (dynamic group and policy),
  lets a script list and prune. Only if Aly prefers it.

Verification: the object appears in the bucket after the nightly run; its size
matches the local `.age` file.

### 11.3 Copy to Aly's desktop **[ALY, weekly]**

```powershell
scp -i "$env:USERPROFILE\.ssh\astra_oci" "ubuntu@<ip>:/srv/astra/backups/astra-*.sqlite3.age" "$env:USERPROFILE\Documents\AstraBackups\"
```

The files are encrypted, so a copy on the desktop reveals nothing without the
key.

### 11.4 Restore **[ALY decrypts, AGENT or ALY runs the steps]**

Decrypt on Aly's PC, never on the server, so the private key stays offline:

```powershell
age -d -i "$env:USERPROFILE\Documents\AstraKeys\astra-backup-key.txt" -o astra.sqlite3 astra-<stamp>.sqlite3.age
python -c "import sqlite3; c=sqlite3.connect('astra.sqlite3'); print(c.execute('PRAGMA integrity_check').fetchone()[0], c.execute('PRAGMA user_version').fetchone()[0])"
```

It prints `ok 20` (or whatever schema the backup has).

**Restore onto the desktop (Oracle to desktop drill):**

```powershell
$env:ASTRA_HOME = "$env:USERPROFILE\Documents\AstraRestoreTest"
New-Item -ItemType Directory -Force $env:ASTRA_HOME
Copy-Item astra.sqlite3 "$env:ASTRA_HOME\astra.sqlite3"
.venv\Scripts\astra serve --host 127.0.0.1 --port 8765
```

Sign in with the real owner account and check recent tasks are there.

**Restore onto the server (or a new VM, desktop to Oracle drill):**

```powershell
scp -i "$env:USERPROFILE\.ssh\astra_oci" astra.sqlite3 ubuntu@<ip>:/tmp/astra-restore.sqlite3
```

```bash
sudo systemctl stop astra
sudo mv /srv/astra/data /srv/astra/data.before-restore-$(date -u +%Y%m%dT%H%M%SZ)
sudo install -d -o astra -g astra -m 700 /srv/astra/data
sudo install -o astra -g astra -m 600 /tmp/astra-restore.sqlite3 /srv/astra/data/astra.sqlite3
sudo rm -f /tmp/astra-restore.sqlite3
sudo systemctl start astra
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/
```

- Do not copy an old `-wal` or `-shm` file next to a restored database.
- A backup from an older schema is upgraded automatically on start.
- A backup from a newer schema than the installed code is refused ("Database
  was created by a newer Astra version."); install the matching release first.
- Delete the plain `astra.sqlite3` from the PC once the drill is done.

Verification: time the whole drill. It must fit in the 4-hour RTO. Record the
date, the backup used and the time taken.

---

## Stage 12 — Monitoring and uptime **[ALY picks the services, AGENT configures]**

1. **External uptime check [ALY].** Use a free uptime-monitoring service of
   Aly's choice to request `https://<name>.duckdns.org/` every 5 minutes and
   alert Aly when it is not `200`. Use `GET`, not `HEAD`.
2. **Backup heartbeat (optional).** If the chosen service offers a heartbeat
   URL, add `curl -fsS <heartbeat-url>` as the last line of `astra-backup`, so a
   missed backup raises an alert.
3. **Disk space.** Check weekly with `df -h /` and `du -sh /srv/astra`. Keep
   the boot volume below 80%.
4. **Logs.** `journalctl -u astra`, `journalctl -u caddy`,
   `/var/log/caddy/astra-access.log` (Caddy rolls file logs itself; verify the
   default size and count).
5. **Oracle notices [ALY].** Read tenancy emails. Oracle documents that idle
   Always Free instances may be reclaimed and that capacity can be unavailable
   (per the 2026-09-20 handoff). Off-host backups are the protection.

Verification: stop Astra for 10 minutes (`sudo systemctl stop astra`) and
confirm the alert arrives; start it again.

---

## Stage 13 — Reboot test **[AGENT]**

Required by ticket 6BXYJZ ("post-reboot verification").

```bash
sudo reboot
```

After a minute, SSH in again and run:

```bash
systemctl is-active astra caddy
systemctl list-timers astra-backup.timer --no-pager
curl -sS -o /dev/null -w '%{http_code}\n' https://<name>.duckdns.org/
```

Verification: both services are `active`, the timer is listed, and the site
answers `200`.

---

## Stage 14 — Update procedure **[AGENT, with Aly's go-ahead per release]**

1. Tell users about a short maintenance window.
2. Take a backup now and check it:

   ```bash
   sudo systemctl start astra-backup.service
   journalctl -u astra-backup -n 5 --no-pager
   ```

3. Check whether the release changes the schema:

   ```bash
   cd /opt/astra/app
   sudo git fetch --tags
   sudo git diff <old-tag> <new-tag> -- src/astra/db.py | grep SCHEMA_VERSION
   ```

4. Install the new release and restart:

   ```bash
   sudo git checkout <new-tag>
   sudo /opt/astra/app/.venv/bin/python -m pip install --no-deps --force-reinstall /opt/astra/app
   sudo systemctl restart astra
   ```

5. Verify: `systemctl status astra`, `journalctl -u astra -n 50` (no errors, no
   "Astra cannot upgrade this database" message), the site answers `200`, Aly
   signs in and opens Home, a project board and a task.

If start-up stops with "Astra cannot upgrade this database to schema N", the
database is untouched. Follow the README's instructions for that schema, or roll
back.

## Stage 15 — Rollback

- **No schema change between the two tags:** check out the old tag, reinstall,
  restart.

  ```bash
  cd /opt/astra/app
  sudo git checkout <old-tag>
  sudo /opt/astra/app/.venv/bin/python -m pip install --no-deps --force-reinstall /opt/astra/app
  sudo systemctl restart astra
  ```

- **The schema changed:** the old code refuses the upgraded database. Stop
  Astra, restore the backup taken in stage 14 step 2 (stage 11.4, server
  steps), check out and reinstall the old tag, start Astra. Anything entered
  after the upgrade is lost, so keep the window short and tell users. The
  backup can be decrypted only on Aly's PC, so this rollback needs Aly
  present, and the 4-hour RTO counts from then.
- **Caddy change went wrong:** restore the previous Caddyfile,
  `sudo caddy validate --config /etc/caddy/Caddyfile`, `sudo systemctl reload caddy`.
- **Whole VM lost or reclaimed:** create a new VM (stages 1 to 9), restore the
  latest off-host backup (stage 11.4), point DuckDNS at the new IP (stage 8).
  Users keep the same URL.

---

## Stage 16 — Cost guardrails **[ALY]**

- Every resource in the console should show as Always Free. Do not accept any
  upgrade prompt.
- Create a budget with an alert at a very small amount so any charge is noticed
  the same day (Budgets are under the billing section of the console; verify).
- Monthly: check Object Storage use and the boot volume against the free
  allowance; delete nothing by hand that lifecycle rules manage.
- The ceiling is hard: capacity, storage and backup use must alert or fail safely
  before a free allowance is exceeded (2026-09-20 decision).

---

## Go-live checklist

- [ ] HTTPS works with a valid certificate; HTTP redirects to HTTPS.
- [ ] The session cookie is `Secure`, `HttpOnly`, `SameSite=Strict`.
- [ ] Port 8765 is not reachable from outside.
- [ ] Astra and Caddy come back after a reboot.
- [ ] A nightly encrypted backup exists on the VM and in Object Storage.
- [ ] A restore drill passed in both directions, within 4 hours.
- [ ] The uptime alert fires when Astra is stopped.
- [ ] The OCI budget alert is set and the cost is zero.
- [ ] Sign-in rate limiting is in place, or Aly has explicitly declined it.
- [ ] First-login password change is built (`NEXT_STEPS.md` A5).
- [ ] The privacy note and quick-start are ready (`NEXT_STEPS.md` phase E).
- [ ] Aly approves go-live and the first user roster.
