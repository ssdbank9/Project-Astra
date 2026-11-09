"""MXY7BG: hosted attachments: HTTPS link checks, the dangerous-type policy and file storage.

Owner decisions Items 5-16 on 6G89SJ (Aly, 2026-09-19/20):
- a link is any syntactically valid HTTPS URL; Astra never fetches, probes or previews it
  (Items 12-13);
- a managed upload is checked against a dangerous-type denylist by extension, declared
  MIME type and file signature, and a known extension whose signature does not match is
  refused (Item 9). Nothing is scanned and nothing is ever called safe (Items 10-11);
- uploads stream to storage with the size limit enforced while reading, and a partial
  file is removed on any failure (Item 8). Slice 2: the App Owner sets the limit up to a
  250 MB ceiling and adds extensions and media types to the denylist (UploadPolicy); the
  built-in list and the signature checks always apply;
- one storage interface (Item 6). The protected private-server folder is the first
  backend (Aly, 2026-11-08); OCI Object Storage comes later behind the same methods.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable, Iterator
from urllib.parse import urlsplit

from .db import app_home

MAX_LINK_LENGTH = 2048
MAX_FILENAME_LENGTH = 200
DEFAULT_UPLOAD_LIMIT = 25 * 1024 * 1024  # Item 8 default
HARD_UPLOAD_LIMIT = 250 * 1024 * 1024  # Item 8 ceiling no setting may exceed
CHUNK_BYTES = 64 * 1024
# Enough to reach the ISO 9660 descriptor at 0x9001 as well as every leading signature.
HEAD_BYTES = 64 * 1024
UPLOAD_ROOT_ENV = "ASTRA_UPLOAD_ROOT"
UPLOAD_CEILING_ENV = "ASTRA_UPLOAD_CEILING_MB"

# Item 9 secure defaults: executables, installers, scripts, commands, libraries, disk images
# and shortcuts. The App Owner may add to this list (UploadPolicy), never take from it.
DANGEROUS_EXTENSIONS = frozenset({
    ".exe", ".com", ".scr", ".pif", ".cpl", ".msc", ".msi", ".msp", ".mst", ".appx", ".appxbundle",
    ".msix", ".msixbundle", ".bat", ".cmd", ".ps1", ".psm1", ".psd1", ".vbs", ".vbe", ".js", ".jse",
    ".wsf", ".wsh", ".hta", ".dll", ".sys", ".drv", ".ocx", ".so", ".dylib", ".sh", ".bash", ".zsh",
    ".csh", ".ksh", ".command", ".app", ".pkg", ".dmg", ".iso", ".img", ".vhd", ".vhdx", ".vmdk",
    ".jar", ".class", ".apk", ".aab", ".ipa", ".deb", ".rpm", ".run", ".bin", ".elf", ".lnk", ".url",
    ".scf", ".reg", ".inf", ".gadget", ".application", ".appref-ms", ".py", ".pyw", ".pl", ".rb",
    ".php", ".action", ".workflow", ".xbap", ".chm", ".iqy", ".settingcontent-ms", ".xll", ".sct",
    ".wsc", ".ws", ".ps1xml", ".psc1", ".msh", ".msh1", ".msh2", ".mshxml", ".vb", ".desktop",
    ".library-ms", ".search-ms", ".diagcab",
})
DANGEROUS_MIME_TYPES = frozenset({
    "application/x-msdownload", "application/x-msdos-program", "application/x-dosexec",
    "application/x-ms-installer", "application/x-msi", "application/x-ms-shortcut",
    "application/vnd.microsoft.portable-executable", "application/x-executable",
    "application/x-elf", "application/x-mach-binary", "application/x-sharedlib",
    "application/x-sh", "application/x-shellscript", "text/x-shellscript", "application/x-csh",
    "application/x-bat", "application/bat", "application/x-msbatch", "text/x-msdos-batch",
    "application/x-powershell", "application/java-archive", "application/x-java-archive",
    "application/x-java-applet", "application/vnd.android.package-archive",
    "application/x-apple-diskimage", "application/x-iso9660-image", "application/x-raw-disk-image",
    "application/x-debian-package", "application/x-rpm", "application/hta", "text/javascript",
    "application/javascript", "application/x-javascript", "text/vbscript", "application/x-python-code",
})
# (offset, magic, what it is). Any match refuses the upload whatever its name says.
DANGEROUS_SIGNATURES = (
    (0, b"MZ", "a Windows program"),
    (0, b"\x7fELF", "a Linux program"),
    (0, b"\xfe\xed\xfa\xce", "a macOS program"),
    (0, b"\xfe\xed\xfa\xcf", "a macOS program"),
    (0, b"\xce\xfa\xed\xfe", "a macOS program"),
    (0, b"\xcf\xfa\xed\xfe", "a macOS program"),
    (0, b"\xca\xfe\xba\xbe", "a macOS or Java program"),
    (0, b"#!", "a script"),
    (0, b"dex\n", "an Android program"),
    (0x8001, b"CD001", "a disk image"),
    (0x8801, b"CD001", "a disk image"),
    (0x9001, b"CD001", "a disk image"),
)
# A file named as one of these must start like one; a mismatch is refused (Item 9).
EXPECTED_SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
    ".pptx": (b"PK\x03\x04",),
    ".odt": (b"PK\x03\x04",),
    ".ods": (b"PK\x03\x04",),
    ".odp": (b"PK\x03\x04",),
}

_HOST_CHARS = re.compile(r"^[^\s/\\?#@]+$")

MB = 1024 * 1024
MAX_POLICY_ENTRIES = 200
_EXTENSION = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_MIME_TYPE = re.compile(r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,126}/[a-z0-9][a-z0-9!#$&^_.+-]{0,126}$")


def upload_ceiling() -> int:
    """The bytes the server admits on the upload route: Waitress's cap, which the Caddyfile's
    max_size matches. The default limit unless ASTRA_UPLOAD_CEILING_MB raises it, never above
    HARD_UPLOAD_LIMIT. A body up to this size reaches the server and is spooled before Astra's
    own checks run, so the ceiling is raised only together with the proxy (runbook stage 9),
    never from the app; the App Owner's limit can go up to it and no further.
    """
    text = os.environ.get(UPLOAD_CEILING_ENV, "").strip()
    if not text:
        return DEFAULT_UPLOAD_LIMIT
    if not re.fullmatch(r"[0-9]{1,3}", text) or not 1 <= int(text) <= HARD_UPLOAD_LIMIT // MB:
        raise ValueError(f"{UPLOAD_CEILING_ENV} must be a whole number of MB from 1 to {HARD_UPLOAD_LIMIT // MB}.")
    return int(text) * MB


def normalize_extension(value) -> str:
    """'.xyz' in lower case: 'XYZ', '.xyz' and '*.xyz' all mean the same. ValueError otherwise."""
    shown = str(value or "").strip()
    text = shown.lower()
    if text.startswith("*"):
        text = text[1:]
    if text.startswith("."):
        text = text[1:]
    if not _EXTENSION.fullmatch(text):
        raise ValueError(f"'{shown}' is not a file extension. Use letters, digits, - and _, such as .xyz.")
    return "." + text


def normalize_mime_type(value) -> str:
    """'type/subtype' in lower case without parameters, or ValueError."""
    shown = str(value or "").strip()
    text = shown.lower().split(";", 1)[0].strip()
    if not _MIME_TYPE.fullmatch(text):
        raise ValueError(f"'{shown}' is not a media type. Use the type/subtype form, such as application/x-foo.")
    return text


def normalize_policy_list(values, normalize, what: str, builtin: frozenset = frozenset()) -> tuple[str, ...]:
    """The App Owner's additions as a sorted tuple. Text holds one entry per line or comma;
    blanks are dropped; duplicates and built-in entries fold away."""
    if isinstance(values, str):
        values = re.split(r"[\r\n,]+", values)
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"The {what} must be a list.")
    kept: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError(f"The {what} must be text.")
        if not value.strip():
            continue
        item = normalize(value)
        if item not in builtin and item not in kept:
            kept.append(item)
    if len(kept) > MAX_POLICY_ENTRIES:
        raise ValueError(f"At most {MAX_POLICY_ENTRIES} {what} can be added.")
    return tuple(sorted(kept))


@dataclass(frozen=True)
class UploadPolicy:
    """Items 8-9: the installation's upload limit and the App Owner's additions to the
    denylist. The built-in extensions, media types and signatures always apply."""

    limit: int = DEFAULT_UPLOAD_LIMIT
    extra_extensions: tuple[str, ...] = ()
    extra_mime_types: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.limit) is not int or not MB <= self.limit <= HARD_UPLOAD_LIMIT:
            raise ValueError(f"The upload limit must be between 1 and {HARD_UPLOAD_LIMIT // MB} MB.")

    def blocks_extension(self, ext: str) -> bool:
        return ext in DANGEROUS_EXTENSIONS or ext in self.extra_extensions

    def blocks_mime_type(self, declared: str) -> bool:
        return declared in DANGEROUS_MIME_TYPES or declared in self.extra_mime_types


DEFAULT_POLICY = UploadPolicy()


class UploadTooLarge(ValueError):
    """The upload is bigger than the installation's limit."""


def _has_control(text: str) -> bool:
    return any(unicodedata.category(ch) in ("Cc", "Cf", "Zl", "Zp") for ch in text)


def validate_https_url(value) -> str:
    """The link to store, or ValueError. Syntax only: nothing is ever fetched (Item 13)."""
    if not isinstance(value, str):
        raise ValueError("A link must be text.")
    url = value.strip()
    if not url:
        raise ValueError("Enter an https:// link.")
    if len(url) > MAX_LINK_LENGTH:
        raise ValueError(f"A link is limited to {MAX_LINK_LENGTH} characters.")
    if _has_control(url) or any(ch.isspace() for ch in url):
        raise ValueError("A link cannot contain spaces or control characters.")
    try:
        parts = urlsplit(url)
        parts.port  # raises ValueError for a malformed or out-of-range port
    except ValueError:
        raise ValueError("This is not a valid link.") from None
    if parts.scheme.casefold() != "https":
        raise ValueError("Only https:// links can be attached.")
    if "@" in parts.netloc:
        raise ValueError("A link cannot contain a user name or password.")
    host = parts.hostname or ""
    if not host or not _HOST_CHARS.match(host) or host.startswith(".") or ".." in host:
        raise ValueError("This is not a valid link.")
    return url


def clean_filename(value) -> str:
    """The name to show and download under: no folders, no control characters."""
    name = str(value or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(ch for ch in name if not _has_control(ch)).strip()
    name = name.rstrip(". ")  # Windows ignores trailing dots and spaces: "a.exe." runs as a.exe
    if name in ("", ".", ".."):
        raise ValueError("The file needs a name.")
    if len(name) > MAX_FILENAME_LENGTH:
        stem, dot, ext = name.rpartition(".")
        keep = MAX_FILENAME_LENGTH - len(dot + ext)
        name = (stem[:keep] + dot + ext) if dot and 0 < keep else name[:MAX_FILENAME_LENGTH]
    return name


def file_extension(name: str) -> str:
    _, dot, ext = name.rpartition(".")
    return f".{ext.casefold()}" if dot and ext else ""


def check_upload(filename: str, declared_type: str, head: bytes,
                 policy: UploadPolicy = DEFAULT_POLICY) -> None:
    """Refuse a known-dangerous or mismatched file (Item 9). Never a statement of safety."""
    ext = file_extension(filename)
    if policy.blocks_extension(ext):
        raise ValueError(f"Files of type {ext} cannot be uploaded.")
    declared = (declared_type or "").split(";", 1)[0].strip().casefold()
    if policy.blocks_mime_type(declared):
        raise ValueError("This kind of file cannot be uploaded.")
    for offset, magic, what in DANGEROUS_SIGNATURES:
        if head[offset:offset + len(magic)] == magic:
            raise ValueError(f"This file looks like {what} and cannot be uploaded.")
    expected = EXPECTED_SIGNATURES.get(ext)
    if expected and not head.startswith(expected):
        raise ValueError(f"This file's contents do not match its {ext} name.")


def checked_chunks(stream: BinaryIO, length: int, policy: UploadPolicy, filename: str,
                   declared_type: str) -> Iterator[bytes]:
    """Read exactly ``length`` bytes in chunks, refusing an oversized, short or dangerous body.

    The size is refused before a byte is read when the declared length is over the
    policy's limit,
    and no read ever asks for more than the declared length, so the limit holds while
    streaming too. The type check runs on the first HEAD_BYTES, before anything is handed
    on, so a refused file is never written past its first chunk.
    """
    if length <= 0:
        raise ValueError("The file is empty.")
    if length > policy.limit:
        raise UploadTooLarge(f"The file is larger than {policy.limit / MB:g} MB.")
    remaining, head, checked = length, b"", False
    while remaining:
        chunk = stream.read(min(CHUNK_BYTES, remaining))
        if not chunk:
            raise ValueError("The upload is incomplete. Send the file again.")
        if len(chunk) > remaining:
            raise ValueError("The upload is longer than it said. Send the file again.")
        remaining -= len(chunk)
        if checked:
            yield chunk
            continue
        head += chunk
        if len(head) >= HEAD_BYTES or not remaining:
            check_upload(filename, declared_type, head, policy)
            checked = True
            yield head
            head = b""


@dataclass(frozen=True)
class StoredObject:
    key: str
    size: int
    sha256: str


_KEY = re.compile(r"^[0-9a-f]{32}$")


class FolderStorage:
    """Item 6 Backend B: a protected folder on the server, never served as static files.

    Finished files live in <root>/objects/<key>. An upload is written to
    <root>/incoming/<key>.part and renamed into place only once complete, so a refused or
    failed upload never leaves a usable object behind.
    """

    name = "folder"

    def __init__(self, root: Path):
        self.root = Path(root)

    def _dirs(self) -> tuple[Path, Path]:
        incoming, objects = self.root / "incoming", self.root / "objects"
        incoming.mkdir(parents=True, exist_ok=True)
        objects.mkdir(parents=True, exist_ok=True)
        return incoming, objects

    def _object(self, key: str) -> Path:
        if not isinstance(key, str) or not _KEY.match(key):
            raise KeyError("File not found.")
        return self.root / "objects" / key

    def save(self, chunks: Iterable[bytes]) -> StoredObject:
        incoming, objects = self._dirs()
        key = secrets.token_hex(16)
        partial = incoming / f"{key}.part"
        digest, size = hashlib.sha256(), 0
        try:
            with open(partial, "xb") as handle:
                for chunk in chunks:
                    handle.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(partial, objects / key)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        return StoredObject(key, size, digest.hexdigest())

    def open(self, key: str) -> BinaryIO:
        try:
            return open(self._object(key), "rb")
        except FileNotFoundError:
            raise KeyError("File not found.") from None

    def delete(self, key: str) -> None:
        self._object(key).unlink(missing_ok=True)


def upload_root() -> Path:
    override = os.environ.get(UPLOAD_ROOT_ENV, "").strip()
    return Path(override).expanduser().resolve() if override else app_home() / "uploads"


def active_storage() -> FolderStorage:
    """The installation's one storage backend (Item 7)."""
    return FolderStorage(upload_root())
