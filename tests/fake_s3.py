"""A small S3-compatible server for the object storage tests (MXY7BG slice 4).

One private bucket held in memory, path-style addressing (``/<bucket>/<key>``), on a
loopback port. It checks every request the way the S3 specification describes, with its own
implementation of AWS Signature Version 4: the signature, the signed headers, the request
time and, for a PUT, that the body's SHA-256 is the one that was signed. A request without a
signature is refused unless the test has made the bucket public. Tests can inject faults.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_AUTH = re.compile(
    r"^AWS4-HMAC-SHA256 Credential=(?P<access>[^/]+)/(?P<date>\d{8})/(?P<region>[^/]+)/s3/aws4_request, "
    r"SignedHeaders=(?P<signed>[a-z0-9;-]+), Signature=(?P<signature>[0-9a-f]{64})$")
REQUIRED_SIGNED = {"host", "x-amz-date", "x-amz-content-sha256"}


def _hmac(key: bytes, text: str) -> bytes:
    return hmac.new(key, text.encode("utf-8"), hashlib.sha256).digest()


def signature_v4(secret: str, method: str, path: str, headers: dict, signed: list, payload_hash: str,
                 amz_date: str, region: str) -> str:
    canonical = "\n".join([
        method, path, "",
        "".join(f"{name}:{' '.join(headers[name].split())}\n" for name in signed),
        ";".join(signed), payload_hash])
    scope = f"{amz_date[:8]}/{region}/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode("utf-8")).hexdigest()])
    key = _hmac(("AWS4" + secret).encode("utf-8"), amz_date[:8])
    for part in (region, "s3", "aws4_request"):
        key = _hmac(key, part)
    return hmac.new(key, to_sign.encode("utf-8"), hashlib.sha256).hexdigest()


class FakeS3:
    """Start with ``with FakeS3() as s3:`` and point Astra at ``s3.env()``.

    ``fault`` may be set to a function ``(method, key) -> str | None`` returning one of:
    "500" or "403" (refuse with that status), "no-bucket" (404 NoSuchBucket, as a wrong
    bucket name or endpoint gives), "drop" (close without answering), "truncate" (a GET
    sends half the bytes it promised), "no-length" (a GET answers without saying how long
    the object is), "corrupt-read" (a GET sends altered bytes of the right length),
    "corrupt-store" (a PUT answers 200 but keeps altered bytes).
    """

    def __init__(self, bucket="astra-test", access_key="AKIDTESTKEY", secret_key="test+Secret/Key=0123456789",
                 region="me-jeddah-1"):
        self.bucket, self.access_key, self.secret_key, self.region = bucket, access_key, secret_key, region
        self.objects: dict[str, bytes] = {}
        self.public = False
        self.fault = None
        self.requests: list[tuple[str, str, int]] = []
        self.lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def _answer(self, status, body=b"", code=None, length=None):
                if code:
                    # A real S3 error repeats what was signed and the key id; Astra must not.
                    body = (f"<Error><Code>{code}</Code><Message>refused</Message>"
                            f"<AWSAccessKeyId>{outer.access_key}</AWSAccessKeyId>"
                            f"<StringToSign>string-to-sign-detail</StringToSign></Error>").encode("ascii")
                outer.requests.append((self.command, self.path, status))
                self.send_response(status)
                self.send_header("Content-Length", str(len(body) if length is None else length))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

            def _handle(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                prefix = f"/{outer.bucket}/"
                if "?" in self.path or not self.path.startswith(prefix):
                    return self._answer(400, code="InvalidRequest")
                key = self.path[len(prefix):]
                fault = outer.fault(self.command, key) if outer.fault else None
                if fault == "drop":
                    self.close_connection = True
                    self.connection.close()
                    return None
                if fault in ("500", "403"):
                    return self._answer(int(fault), code="InternalError" if fault == "500" else "AccessDenied")
                if fault == "no-bucket":
                    return self._answer(404, code="NoSuchBucket")
                authorization = self.headers.get("Authorization")
                if authorization is None:
                    if not (outer.public and self.command == "GET"):
                        return self._answer(403, code="AccessDenied")
                else:
                    refusal = self._check_signature(authorization, body)
                    if refusal:
                        return self._answer(*refusal)
                with outer.lock:
                    if self.command == "PUT":
                        outer.objects[key] = (bytes([body[0] ^ 0xFF]) + body[1:]) if fault == "corrupt-store" else body
                        return self._answer(200)
                    if self.command == "DELETE":
                        outer.objects.pop(key, None)
                        return self._answer(204)
                    data = outer.objects.get(key)
                if data is None:
                    return self._answer(404, code="NoSuchKey")
                if fault == "corrupt-read":
                    data = bytes([data[0] ^ 0xFF]) + data[1:]
                if fault == "no-length":
                    outer.requests.append((self.command, self.path, 200))
                    self.send_response(200)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(data)
                    self.close_connection = True
                    return None
                if fault == "truncate":
                    self._answer(200, data[: len(data) // 2], length=len(data))
                    self.close_connection = True
                    return None
                return self._answer(200, data)

            def _check_signature(self, authorization, body):
                found = _AUTH.match(authorization)
                if not found:
                    return 400, b"", "AuthorizationHeaderMalformed"
                headers = {name.lower(): value for name, value in self.headers.items()}
                signed = found["signed"].split(";")
                amz_date = headers.get("x-amz-date", "")
                payload_hash = headers.get("x-amz-content-sha256", "")
                if (found["access"] != outer.access_key or found["region"] != outer.region
                        or not REQUIRED_SIGNED <= set(signed) or signed != sorted(signed)
                        or any(name not in headers for name in signed) or found["date"] != amz_date[:8]):
                    return 403, b"", "InvalidAccessKeyId" if found["access"] != outer.access_key else "AccessDenied"
                try:
                    sent = datetime.strptime(amz_date, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                except ValueError:
                    return 403, b"", "AccessDenied"
                if abs(datetime.now(timezone.utc) - sent) > timedelta(minutes=15):
                    return 403, b"", "RequestTimeTooSkewed"
                expected = signature_v4(outer.secret_key, self.command, self.path, headers, signed, payload_hash,
                                        amz_date, outer.region)
                if not hmac.compare_digest(expected, found["signature"]):
                    return 403, b"", "SignatureDoesNotMatch"
                if hashlib.sha256(body).hexdigest() != payload_hash:
                    return 400, b"", "XAmzContentSHA256Mismatch"
                return None

            do_GET = do_PUT = do_DELETE = do_HEAD = do_POST = _handle

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def env(self) -> dict:
        return {"ASTRA_S3_ENDPOINT": self.endpoint, "ASTRA_S3_REGION": self.region, "ASTRA_S3_BUCKET": self.bucket,
                "ASTRA_S3_ACCESS_KEY_ID": self.access_key, "ASTRA_S3_SECRET_ACCESS_KEY": self.secret_key}

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc_info):
        self.server.shutdown()
        self.thread.join(5)
        self.server.server_close()
