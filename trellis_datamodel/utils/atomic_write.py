"""Atomic file writes: the only way the backend replaces a file on disk."""

from __future__ import annotations

import os
import uuid
from pathlib import Path


def atomic_write(
    path: str | Path,
    content: str,
    *,
    encoding: str | None = None,
    mode: int = 0o666,
) -> None:
    """Replace *path* with *content* so readers never see a partial file.

    The text goes to a temp file next to *path* (same filesystem), which is then
    moved over *path* with ``os.replace``. Missing parent directories are
    created. On failure the temp file is removed, *path* is left as it was and
    the original exception propagates; callers translate it into their own
    error type.

    Args:
        path: The file to write.
        content: The full new text of the file.
        encoding: Text encoding; ``None`` uses the platform default, like ``open``.
        mode: Permission bits for the new file, filtered by the umask like
            ``open``. The written file replaces the old one, so it does not keep
            the old file's mode.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as tmp_file:
            tmp_file.write(content)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
