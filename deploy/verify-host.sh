#!/bin/sh
# Read-only checks for a host set up from this folder. Run as root
# (sudo sh verify-host.sh) after runbook stages 3, 4, 7 and 9. It changes
# nothing and prints one PASS or FAIL line per check; the exit status is the
# number of failures.
set -u

failures=0
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; failures=$((failures + 1)); }
check() {
	label=$1
	shift
	if "$@" >/dev/null 2>&1; then pass "$label"; else fail "$label"; fi
}

check "astra service is running" systemctl is-active --quiet astra

listeners=$(ss -ltnH 'sport = :8765' 2>/dev/null | awk '{print $4}')
if [ -z "$listeners" ]; then
	fail "something listens on port 8765"
elif printf '%s\n' "$listeners" | grep -qv '^127\.0\.0\.1:8765$'; then
	fail "port 8765 listens on loopback only (found: $(echo $listeners))"
else
	pass "port 8765 listens on loopback only"
fi

status=$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null)
if [ "$status" = "200" ]; then pass "Astra answers on 127.0.0.1:8765"; else fail "Astra answers on 127.0.0.1:8765 (got ${status:-nothing})"; fi

mode=$(stat -c '%a %U %G' /srv/astra/data 2>/dev/null)
if [ "$mode" = "700 astra astra" ]; then pass "/srv/astra/data is 700 astra:astra"; else fail "/srv/astra/data is 700 astra:astra (found: ${mode:-missing})"; fi

for keyword in passwordauthentication permitrootlogin kbdinteractiveauthentication; do
	value=$(sshd -T 2>/dev/null | awk -v k="$keyword" '$1 == k {print $2}')
	if [ "$value" = "no" ]; then pass "sshd $keyword no"; else fail "sshd $keyword no (found: ${value:-unknown})"; fi
done

version=$(caddy version 2>/dev/null | awk '{print $1}' | sed 's/^v//')
# A pre-release such as 2.10.0-beta.3 is older than 2.10.0, so refuse any suffix.
if [ -n "$version" ] && ! printf '%s' "$version" | grep -q -- '-' && [ "$(printf '2.10.0\n%s\n' "$version" | sort -V | head -n1)" = "2.10.0" ]; then
	pass "caddy $version is 2.10.0 or newer"
else
	fail "caddy is 2.10.0 or newer (found: ${version:-not installed})"
fi
# As the caddy user: validating as root could create the access log owned by root.
check "Caddyfile validates" sudo -u caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
if grep -Eq '<name>|YOUR-DUCKDNS-NAME' /etc/caddy/Caddyfile 2>/dev/null; then
	fail "Caddyfile has the real DuckDNS name (still a placeholder)"
else
	pass "Caddyfile has the real DuckDNS name"
fi

exit "$failures"
