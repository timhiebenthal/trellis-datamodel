import os
import stat
from pathlib import Path

import pytest

from trellis_datamodel.utils.atomic_write import atomic_write


def _mode(path: Path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def _umask() -> int:
    current = os.umask(0)
    os.umask(current)
    return current


def test_replaces_content_and_creates_parents(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "file.yml"

    atomic_write(path, "one\n")
    atomic_write(path, "two\n")

    assert path.read_text() == "two\n"
    assert os.listdir(path.parent) == ["file.yml"]


def test_default_mode_follows_umask_like_open(tmp_path: Path) -> None:
    path = tmp_path / "file.yml"

    atomic_write(path, "x")

    assert _mode(path) == 0o666 & ~_umask()


def test_explicit_mode_is_applied(tmp_path: Path) -> None:
    path = tmp_path / "file.yml"
    path.write_text("old")

    atomic_write(path, "x", mode=0o600)

    assert _mode(path) == 0o600


def test_failure_keeps_original_and_leaves_no_temp_file(tmp_path: Path) -> None:
    path = tmp_path / "file.yml"
    path.write_text("original")

    with pytest.raises(UnicodeEncodeError):
        atomic_write(path, "☃", encoding="ascii")

    assert path.read_text() == "original"
    assert os.listdir(tmp_path) == ["file.yml"]
