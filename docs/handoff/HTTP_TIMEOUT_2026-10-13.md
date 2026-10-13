# HTTP inactivity timeout — AY5EZ0

The server now applies a **30-second socket inactivity timeout** to each
accepted connection. This addresses the stalled-client item in
`NEXT_STEPS.md` B1. It does not complete the broader security review.

Idle connections and stalled header reads close without opening a request
database. A stalled JSON or raw upload body produces a JSON **408 Request
Timeout**, with `Connection: close` and the existing security headers.
The existing request `finally` block closes its SQLite connection.

## Requirements and evidence

| Requirement | Evidence / result |
| --- | --- |
| Reproduce the stall | Real loopback sockets with idle connections, incomplete headers, partial JSON and partial raw upload bodies. Pre-fix: Ran 7 tests in 8.872s, failures=5, with no harness cleanup errors. |
| Apply timeout before header parsing | `AstraHandler.timeout = 30`; installed Python's `StreamRequestHandler.setup` applies it to the accepted socket before reads. Tests observe the real socket setting. |
| Distinguish request timeout from application failure | Timeout-only change released sockets but three body tests returned 500. `_read_request_bytes` now wraps only body-read timeouts in `RequestBodyTimeout`; `_error` returns 408. Other error contracts remain unchanged. |
| Avoid work after stalled bodies | Login and authorization spies remain uncalled for timed-out login, mutation and raw-import requests. |
| Close resources | Test waits for handler completion, verifies request SQLite connections reject further execution, and checks unexpected handler failures are absent. |
| Preserve valid requests | Static request retains security headers. A body delivered in separate socket writes within the timeout succeeds. This is not HTTP chunked transfer encoding. |
| Focused checks | Parent: Ran 7 tests in 4.026s, OK. Independent: Ran 7 tests in 4.192s, OK. |
| Guard-removal checks | Independent in-memory timeout=None mutation fails idle release. Removing body-timeout classification fails with 500 instead of 408. No production files changed for mutations. |
| Independent source review | Pass, no blocking findings. |
| Unmodified production policy | Separate real-socket probe, no timeout shortening: idle and headers closed at 30.007s; JSON returned 408 at 30.007s; raw returned 408 at 30.023s. Normal static response remained 200. |
| Full suite | Ran 797 tests in 419.228s, OK (skipped=1), exit 0. The existing attachment-symlink test is skipped because symlinks are unavailable here. |
| Owner acceptance | Aly explicitly accepted AY5EZ0 in chat on 2026-10-13 after the publication report. Accepted implementation SHA: `6010ca6401aff36e7822e26fb00d626a8daf7440`. Acceptance is recorded through the Jaira CLI; its human lane remains unchanged under `AGENTS.md`. The prior 827Q51 acceptance record was also published with this implementation. |
| Deployment / current owner server | **Unverified.** No deployment, account creation, real-data change or owner-server restart occurred. A running Python process must restart to load the handler change. |

Tests use disposable databases outside the checkout and new loopback servers.
They shorten an existing valid positive timeout to 0.2 seconds for fast
verification; a removed policy stays removed, rather than being supplied by
the test harness. No database or browser artifacts are included in Git.

Local ignored receipts: `Temp/AY5EZ0-red.txt`,
`Temp/AY5EZ0-timeout-only.txt`, `Temp/verification-AY5EZ0-full.txt`,
`Temp/AY5EZ0-default-timeout.txt`.

## Limits and next work

This is an inactivity timeout, not a maximum total request duration. Clients
continuously sending bytes can still hold connections; proxy request deadlines,
concurrency controls and rate limiting remain separate launch gates. Writes
are also subject to the socket timeout; a disconnected client may not receive
the error response, while request database cleanup still runs.

Authorization, CSRF, session policy and the JSON/raw upload size limits were
not changed. Broader B1 authentication, route authorization, input framing,
download headers and proxy review remain outstanding. No claim of complete
internet-facing security or hosted readiness follows from this repair.

827Q51's actual 200% browser zoom passed on 2026-10-13; see
`TABLE_SCHEDULING_2026-10-12.md`. Physical-device checks remain **unverified**.
Aly's acceptance is already recorded; do not repeat the acceptance request.
