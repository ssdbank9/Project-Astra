"""MXY7BG slice 4, Owner Items 6-7 on 6G89SJ: Backend A, private OCI Object Storage.

Astra reaches the bucket through OCI's Amazon S3 Compatibility API using the standard
library only. Every request is signed with AWS Signature Version 4 and a Customer Secret
Key that the App Owner creates and places in the server's environment; the key never
enters the database, a log line or an error message. The bucket stays private: Astra never
makes an object public and never issues a pre-signed URL, so every download still streams
through Astra after its access check, exactly as with the folder backend.

The same methods as FolderStorage: save, put, open, delete. Tests run against
tests/fake_s3.py, which checks each signature and payload hash the way the S3
specification describes; behaviour against a live OCI tenancy is unverified until the App
Owner's drill (DEPLOYMENT_RUNBOOK stage 11.5).
"""
from __future__ import annotations

import hashlib
import hmac
import http.client
import os
import re
import secrets
import ssl
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping
from urllib.parse import quote, urlsplit

from .attachment_storage import CHUNK_BYTES, StorageError, StorageNotConfigured, StoredObject, valid_key

ENDPOINT_ENV = "ASTRA_S3_ENDPOINT"
REGION_ENV = "ASTRA_S3_REGION"
BUCKET_ENV = "ASTRA_S3_BUCKET"
ACCESS_KEY_ENV = "ASTRA_S3_ACCESS_KEY_ID"
SECRET_KEY_ENV = "ASTRA_S3_SECRET_ACCESS_KEY"
SETTING_NAMES = (ENDPOINT_ENV, REGION_ENV, BUCKET_ENV, ACCESS_KEY_ENV, SECRET_KEY_ENV)

TIMEOUT_SECONDS = 60
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_REGION = re.compile(r"^[a-z0-9-]{1,40}$")
_BUCKET = re.compile(r"^[A-Za-z0-9._-]{1,256}$")
_ACCESS_KEY = re.compile(r"^[A-Za-z0-9+/=_.-]{1,256}$")
_ERROR_CODE = re.compile(rb"<Code>([A-Za-z0-9]{1,64})</Code>")
# <namespace>.compat.objectstorage.<region>.oraclecloud.com, and the newer dedicated form.
_OCI_COMPAT_HOST = re.compile(
    r"^(?P<namespace>[a-z0-9]+)\.compat\.objectstorage\.(?P<region>[a-z0-9-]+)\."
    r"(?P<domain>oraclecloud\.com|oci\.customer-oci\.com)$")


@dataclass(frozen=True)
class S3Settings:
    secure: bool
    host: str
    port: int | None
    region: str
    bucket: str
    access_key: str
    secret_key: str = field(repr=False)  # never printed, logged or put in an error

    @property
    def host_header(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return host if self.port is None else f"{host}:{self.port}"


def settings_from_env(environ: Mapping[str, str] | None = None) -> S3Settings:
    """The object storage settings, or StorageNotConfigured naming what is missing or wrong.
    A setting's value never appears in the message: one of them is the secret key."""
    environ = os.environ if environ is None else environ
    values = {name: str(environ.get(name, "")).strip() for name in SETTING_NAMES}
    missing = [name for name in SETTING_NAMES if not values[name]]
    if missing:
        raise StorageNotConfigured("Object storage is not configured: set " + ", ".join(missing) + ".")
    try:
        parts = urlsplit(values[ENDPOINT_ENV])
        port = parts.port
    except ValueError:
        raise StorageNotConfigured(f"{ENDPOINT_ENV} is not a valid address.") from None
    host = (parts.hostname or "").lower()
    if (not host or not host.isascii() or parts.username is not None or parts.password is not None
            or parts.path not in ("", "/")
            or parts.query or parts.fragment):
        raise StorageNotConfigured(
            f"{ENDPOINT_ENV} must be the endpoint alone, such as https://<namespace>.compat.objectstorage."
            "<region>.oraclecloud.com, with no path, user name or query.")
    if parts.scheme not in ("https", "http") or (parts.scheme == "http" and host not in _LOOPBACK_HOSTS):
        # Plain http is for the test double on this machine only: the key and the files
        # must never cross a network unencrypted.
        raise StorageNotConfigured(f"{ENDPOINT_ENV} must start with https://.")
    if not _REGION.fullmatch(values[REGION_ENV]):
        raise StorageNotConfigured(f"{REGION_ENV} must be a region identifier such as me-jeddah-1.")
    if not _BUCKET.fullmatch(values[BUCKET_ENV]) or values[BUCKET_ENV] in (".", ".."):
        raise StorageNotConfigured(f"{BUCKET_ENV} must be the bucket's name: letters, digits, '.', '-' and '_'.")
    if not _ACCESS_KEY.fullmatch(values[ACCESS_KEY_ENV]):
        raise StorageNotConfigured(f"{ACCESS_KEY_ENV} is not an access key.")
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in values[SECRET_KEY_ENV]):
        raise StorageNotConfigured(f"{SECRET_KEY_ENV} cannot contain spaces or control characters.")
    return S3Settings(parts.scheme == "https", host, port, values[REGION_ENV], values[BUCKET_ENV],
                      values[ACCESS_KEY_ENV], values[SECRET_KEY_ENV])


def _hmac(key: bytes, text: str) -> bytes:
    return hmac.new(key, text.encode("utf-8"), hashlib.sha256).digest()


def authorization_v4(method: str, path: str, headers: Mapping[str, str], payload_hash: str, *,
                     access_key: str, secret_key: str, region: str, service: str = "s3") -> str:
    """The AWS Signature Version 4 Authorization header for a request without a query string.

    ``path`` is the URI-encoded path as sent. Every header in ``headers`` is signed; they
    must include host and x-amz-date, and for S3 x-amz-content-sha256 equal to
    ``payload_hash``.
    """
    signed = sorted((name.lower(), " ".join(str(value).split())) for name, value in headers.items())
    names = ";".join(name for name, _ in signed)
    amz_date = dict(signed)["x-amz-date"]
    scope = f"{amz_date[:8]}/{region}/{service}/aws4_request"
    canonical = "\n".join([method, path, "", "".join(f"{name}:{value}\n" for name, value in signed), names,
                           payload_hash])
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope,
                         hashlib.sha256(canonical.encode("utf-8")).hexdigest()])
    key = ("AWS4" + secret_key).encode("utf-8")
    for part in (amz_date[:8], region, service, "aws4_request"):
        key = _hmac(key, part)
    signature = hmac.new(key, to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, SignedHeaders={names}, Signature={signature}"


def oci_native_object_url(host: str, bucket: str, key: str) -> tuple[str, str] | None:
    """(host, path) of the same object on OCI's native API, where a public bucket answers
    without a signature; None when the endpoint is not an OCI compatibility endpoint."""
    found = _OCI_COMPAT_HOST.fullmatch(host)
    if not found:
        return None
    namespace, region = found["namespace"], found["region"]
    native = (f"objectstorage.{region}.oraclecloud.com" if found["domain"] == "oraclecloud.com"
              else f"{namespace}.objectstorage.{region}.oci.customer-oci.com")
    return native, f"/n/{namespace}/b/{quote(bucket, safe='-_.~')}/o/{key}"


class _Body:
    """A download in progress: read() and close(), like the file FolderStorage returns.
    ``size`` is what the bucket said it will send; ending short of it is an error, never a
    quietly truncated file."""

    def __init__(self, connection, response, size: int):
        self._connection, self._response, self.size, self._left = connection, response, size, size

    def read(self, amount: int = -1) -> bytes:
        if not self._left:
            return b""
        want = self._left if amount is None or amount < 0 else min(amount, self._left)
        try:
            data = self._response.read(want)
        except (OSError, http.client.HTTPException) as exc:
            raise StorageError(f"Object storage stopped answering during the download ({type(exc).__name__}).") from None
        if not data:
            raise StorageError("Object storage ended the download early.")
        self._left -= len(data)
        return data

    def close(self) -> None:
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


class S3Storage:
    """Item 6 Backend A: one private bucket, reached with signed requests only."""

    name = "s3"

    def __init__(self, settings: S3Settings, spool: Path):
        self.settings, self.spool = settings, Path(spool)

    @classmethod
    def from_env(cls, spool: Path, environ: Mapping[str, str] | None = None) -> "S3Storage":
        return cls(settings_from_env(environ), spool)

    # --- requests ---

    def _connect(self, host: str | None = None):
        settings = self.settings
        if host is not None:
            return http.client.HTTPSConnection(host, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context())
        if settings.secure:
            return http.client.HTTPSConnection(settings.host, settings.port, timeout=TIMEOUT_SECONDS,
                                               context=ssl.create_default_context())
        return http.client.HTTPConnection(settings.host, settings.port, timeout=TIMEOUT_SECONDS)

    def _path(self, key: str) -> str:
        return f"/{quote(self.settings.bucket, safe='-_.~')}/{key}"

    def _send(self, method: str, key: str, *, body=None, length: int = 0, payload_hash: str = EMPTY_SHA256,
              signed: bool = True):
        """(connection, response) with the response's headers read. The caller closes the
        connection. Raises StorageError when the bucket cannot be reached."""
        settings, path = self.settings, self._path(key)
        headers = {"Host": settings.host_header}
        if signed:
            headers["x-amz-date"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            headers["x-amz-content-sha256"] = payload_hash
            headers["Authorization"] = authorization_v4(
                method, path, headers, payload_hash, access_key=settings.access_key,
                secret_key=settings.secret_key, region=settings.region)
        if body is not None:
            headers["Content-Length"] = str(length)
        connection = self._connect()
        try:
            connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for name, value in headers.items():
                connection.putheader(name, value)
            connection.endheaders()
            if body is not None:
                while chunk := body.read(CHUNK_BYTES):
                    connection.send(chunk)
            return connection, connection.getresponse()
        except (OSError, http.client.HTTPException) as exc:
            connection.close()
            # The exception text may name the host; it never holds a header or the key.
            raise StorageError(f"Object storage could not be reached ({type(exc).__name__}: {exc}).") from None

    @staticmethod
    def _error_code(response) -> str:
        """The short S3 error code of a refusal, or ''. Only the code is ever repeated: the
        rest of an S3 error body can quote the access key id and the string that was signed."""
        try:
            found = _ERROR_CODE.search(response.read(4096))
        except (OSError, http.client.HTTPException):
            found = None
        return found.group(1).decode("ascii") if found else ""

    @staticmethod
    def _refused(status: int, code: str) -> StorageError:
        return StorageError(f"Object storage refused the request (HTTP {status}{' ' + code if code else ''}).")

    @staticmethod
    def _finish(response) -> None:
        """Read the rest of an accepted answer; a connection that breaks here is a storage error."""
        try:
            response.read()
        except (OSError, http.client.HTTPException) as exc:
            raise StorageError(f"Object storage stopped answering ({type(exc).__name__}).") from None

    # --- the storage interface ---

    def put(self, key: str, chunks: Iterable[bytes]) -> StoredObject:
        """Store the chunks under ``key``. The body is spooled to a temporary file first:
        the signature covers the size and SHA-256 of the whole payload, so both must be
        known before the first byte is sent, and a refused upload never reaches the bucket."""
        if not valid_key(key):
            raise ValueError("Not a storage key.")
        self.spool.mkdir(parents=True, exist_ok=True)
        digest, size = hashlib.sha256(), 0
        with tempfile.TemporaryFile(dir=self.spool) as spooled:
            for chunk in chunks:
                spooled.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            spooled.seek(0)
            connection, response = self._send("PUT", key, body=spooled, length=size,
                                              payload_hash=digest.hexdigest())
            try:
                if response.status not in (200, 201, 204):
                    raise self._refused(response.status, self._error_code(response))
                self._finish(response)
            finally:
                connection.close()
        return StoredObject(key, size, digest.hexdigest())

    def save(self, chunks: Iterable[bytes]) -> StoredObject:
        return self.put(secrets.token_hex(16), chunks)

    def open(self, key: str) -> _Body:
        if not valid_key(key):
            raise KeyError("File not found.")
        connection, response = self._send("GET", key)
        try:
            if response.status != 200:
                code = self._error_code(response)
                # Only the object itself being absent is "not found". A 404 for the bucket
                # (a wrong name or endpoint) must not pass for a missing file.
                if response.status == 404 and code == "NoSuchKey":
                    raise KeyError("File not found.")
                raise self._refused(response.status, code)
            length = response.getheader("Content-Length", "")
            if not length.isdigit():
                raise StorageError("Object storage did not say how long the file is.")
        except BaseException:
            connection.close()
            raise
        return _Body(connection, response, int(length))

    def delete(self, key: str) -> None:
        if not valid_key(key):
            raise KeyError("File not found.")
        connection, response = self._send("DELETE", key)
        try:
            if response.status not in (200, 204):
                code = self._error_code(response)
                if not (response.status == 404 and code == "NoSuchKey"):  # already gone is done
                    raise self._refused(response.status, code)
            else:
                self._finish(response)
        finally:
            connection.close()

    # --- storage-check: the bucket must refuse anyone without the key ---

    def anonymous_reads(self, key: str) -> list[tuple[str, int | None]]:
        """(where, HTTP status) for each attempt to read ``key`` with no signature. A 2xx
        anywhere means the bucket is public. None means that address could not be tried."""
        results: list[tuple[str, int | None]] = []
        connection, response = self._send("GET", key, signed=False)
        try:
            results.append((f"{self.settings.host_header}{self._path(key)}", response.status))
        finally:
            connection.close()
        native = oci_native_object_url(self.settings.host, self.settings.bucket, key)
        if native:
            host, path = native
            connection = self._connect(host)
            try:
                connection.request("GET", path)
                status: int | None = connection.getresponse().status
            except (OSError, http.client.HTTPException):
                status = None
            finally:
                connection.close()
            results.append((f"{host}{path}", status))
        return results
