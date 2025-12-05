"""Tests for version alignment between __init__.py and pyproject.toml."""

import tomllib
from pathlib import Path

import trellis_datamodel


def test_version_alignment():
    """Test that __version__ in __init__.py matches version in pyproject.toml."""
    # Get version from __init__.py
    init_version = trellis_datamodel.__version__

    # Get version from pyproject.toml
    project_root = Path(__file__).parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    pyproject_version = pyproject_data["project"]["version"]

    # Assert versions match
    assert (
        init_version == pyproject_version
    ), f"Version mismatch: __init__.py has '{init_version}' but pyproject.toml has '{pyproject_version}'"
