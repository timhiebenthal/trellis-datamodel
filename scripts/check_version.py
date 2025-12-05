#!/usr/bin/env python3
"""Check that pyproject.toml version matches the GitHub Release tag."""

import re
import sys
import os


def get_version_from_pyproject():
    """Extract version from pyproject.toml."""
    pyproject_path = "pyproject.toml"
    if not os.path.exists(pyproject_path):
        print(f"Error: {pyproject_path} not found")
        sys.exit(1)

    with open(pyproject_path, "r") as f:
        content = f.read()

    # Match version = "x.y.z" pattern
    match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        print("Error: Could not find version in pyproject.toml")
        sys.exit(1)

    return match.group(1)


def normalize_version(version):
    """Remove 'v' prefix if present."""
    return version.lstrip("v")


def main():
    # Get version from pyproject.toml
    pyproject_version = get_version_from_pyproject()

    # Get release tag from environment variable or GitHub event
    release_tag = os.environ.get("GITHUB_REF_NAME") or os.environ.get("RELEASE_TAG", "")

    # For release events, try to get from GITHUB_REF
    if not release_tag and os.environ.get("GITHUB_EVENT_NAME") == "release":
        # Try to extract from GITHUB_REF (format: refs/tags/v1.2.3)
        github_ref = os.environ.get("GITHUB_REF", "")
        if github_ref.startswith("refs/tags/"):
            release_tag = github_ref.replace("refs/tags/", "")

    if not release_tag:
        print("Warning: Could not determine release tag. Skipping version check.")
        print(f"PyProject version: {pyproject_version}")
        sys.exit(0)

    release_version = normalize_version(release_tag)
    pyproject_version_normalized = normalize_version(pyproject_version)

    print(f"PyProject version: {pyproject_version_normalized}")
    print(f"Release tag version: {release_version}")

    if pyproject_version_normalized != release_version:
        print(
            f"Error: Version mismatch! "
            f"pyproject.toml has version {pyproject_version_normalized} "
            f"but release tag is {release_version}"
        )
        sys.exit(1)

    print(f"Version check passed: {pyproject_version_normalized}")
    sys.exit(0)


if __name__ == "__main__":
    main()
