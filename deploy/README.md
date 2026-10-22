# Astra host configuration

The files the deployment runbook installs on the server, kept here so they are
reviewed and tested instead of copied out of a document. Nothing in this folder
has been deployed: staging and real-user deployment still need Aly's separate
go-ahead ([DEPLOYMENT_RUNBOOK.md](../docs/handoff/DEPLOYMENT_RUNBOOK.md)).

None of these files holds a secret, and none may: the repository is public.
The only value to fill in is the DuckDNS name in the Caddyfile.

| File | Installed as | Runbook stage |
| --- | --- | --- |
| `systemd/astra.service` | `/etc/systemd/system/astra.service` | 7 |
| `caddy/Caddyfile` (replace `<name>`) | `/etc/caddy/Caddyfile` | 9 |
| `journald/astra.conf` | `/etc/systemd/journald.conf.d/astra.conf` | 3 |
| `ssh/00-astra.conf` | `/etc/ssh/sshd_config.d/00-astra.conf` | 3 |
| `verify-host.sh` | run in place, `sudo sh verify-host.sh` | after 9 |

What the files guarantee, each pinned by `tests/test_deploy_config.py`:

- Astra listens on `127.0.0.1:8765` only, and Caddy proxies to that address.
- The service runs as the `astra` user and can write only `/srv/astra/data`
  (the SQLite database, mode 700). It has no capabilities and can reach
  nothing beyond the machine itself (loopback only).
- Session cookies are marked `Secure` (`ASTRA_SECURE_COOKIES=1`).
- Caddy's body limit sits between Astra's 5 MB import limit and Waitress's
  6,000,000-byte cap, and its security headers match the ones Astra sends.
- Caddy writes the only record of real client addresses, as JSON, rolled at
  10 MiB and kept for up to 30 days (at most 10 old files).
- SSH accepts keys only and refuses root.

The cloud firewall (OCI security list: 22 from Aly's address only, 80 and 443
from anywhere, never 8765) and the host's `iptables` rules are set by hand in
runbook stage 2; `verify-host.sh` confirms 8765 is not exposed.

Open follow-up: Caddy's admin API listens on `localhost:2019`, which the Astra
service can still reach. Binding it to a unix socket (`admin unix//run/caddy/admin.sock`)
would close that, but it changes how `systemctl reload caddy` talks to Caddy and
has not been tried, so it waits for the first staging host.
