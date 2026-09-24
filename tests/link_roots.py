"""6G89SJ: attachment links must sit inside the installation's ASTRA_ATTACHMENT_ROOTS.

Tests that link files name their allowed folders explicitly and restore the variable
afterwards. LINK_ROOT is a native absolute folder that need not exist
(C:\\astra-test-links on Windows, /astra-test-links elsewhere), so fixtures run the
same on either platform.
"""
from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

ROOTS_ENV = "ASTRA_ATTACHMENT_ROOTS"
LINK_ROOT = os.path.abspath(os.sep + "astra-test-links")


def link(*parts: str) -> str:
    """A path inside LINK_ROOT."""
    return os.path.join(LINK_ROOT, *parts)


def allow_attachment_roots(test, *roots: str, include_defaults: bool = True) -> None:
    """Set ASTRA_ATTACHMENT_ROOTS for the rest of ``test`` and restore it on cleanup.

    By default LINK_ROOT and the system temp folder are allowed, plus ``roots``.
    """
    folders = (LINK_ROOT, tempfile.gettempdir(), *roots) if include_defaults else roots
    patcher = patch.dict(os.environ, {ROOTS_ENV: ";".join(folders)})
    patcher.start()
    test.addCleanup(patcher.stop)
