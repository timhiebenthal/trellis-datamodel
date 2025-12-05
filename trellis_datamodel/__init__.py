"""Trellis Data - Visual data model editor for dbt projects."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("trellis-datamodel")
except PackageNotFoundError:
    __version__ = "0.0.0"
