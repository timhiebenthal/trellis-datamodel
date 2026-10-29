"""
Storage for business_events.yml.

Business events and processes share one YAML file under the "events" and
"processes" keys; this module loads and saves each section while preserving
the other.
"""
import logging
import os
from typing import List, Optional

import yaml

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import FileOperationError
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventsFile,
    BusinessEventProcess,
)
from trellis_datamodel.utils.structured_data import load_yaml_file, save_yaml_file

logger = logging.getLogger(__name__)


def _get_business_events_path() -> str:
    """
    Get the path to business_events.yml file.

    Returns BUSINESS_EVENTS_PATH if set, otherwise defaults to same directory
    as DATA_MODEL_PATH with filename 'business_events.yml'.
    """
    if cfg.BUSINESS_EVENTS_PATH:
        return cfg.BUSINESS_EVENTS_PATH

    # Default to same directory as data_model.yml
    if cfg.DATA_MODEL_PATH:
        data_model_dir = os.path.dirname(cfg.DATA_MODEL_PATH)
        return os.path.abspath(os.path.join(data_model_dir, "business_events.yml"))

    # Fallback to current directory
    return os.path.abspath("business_events.yml")


def _parse_events(data: dict) -> List[BusinessEvent]:
    if "events" not in data:
        raise ValueError("Missing 'events' key")
    return BusinessEventsFile(**data).events


def _parse_processes(data: dict) -> List[BusinessEventProcess]:
    processes = []
    for proc_data in data.get("processes", []) or []:
        # Handle resolved_at being None
        if "resolved_at" in proc_data and proc_data["resolved_at"] is None:
            proc_data = {k: v for k, v in proc_data.items() if k != "resolved_at"}
        processes.append(BusinessEventProcess(**proc_data))
    return processes


# The sections of business_events.yml and how each is parsed from the raw file.
_SECTION_PARSERS = {"events": _parse_events, "processes": _parse_processes}


def _load_section(key: str, path: Optional[str] = None) -> list:
    """
    Load one section ("events" or "processes") of the business events file.

    A missing file yields an empty list.

    Raises:
        FileOperationError: If the file exists but cannot be read, is not valid
            YAML, or the section does not have the expected structure.
    """
    if path is None:
        path = _get_business_events_path()

    if not os.path.exists(path):
        logger.info(f"Business events file not found at {path}, returning empty {key} list")
        return []

    try:
        data = load_yaml_file(path, {})
    except yaml.YAMLError as e:
        logger.error(f"YAML parse error in business events file {path}: {e}")
        raise FileOperationError("Invalid business events file format")
    except Exception as e:
        logger.error(f"Error reading business events file {path}: {e}")
        raise FileOperationError(f"Failed to read business events file: {e}")

    try:
        return _SECTION_PARSERS[key](data)
    except Exception as e:
        logger.error(f"Invalid {key} structure in business events file {path}: {e}")
        raise FileOperationError("Invalid business events file format")


def _save_section(key: str, items: list, path: Optional[str] = None) -> None:
    """
    Replace one section ("events" or "processes") of the business events file.

    The other section is preserved as it is on disk; if it cannot be loaded it
    is written empty.

    Raises:
        FileOperationError: If the file cannot be written.
    """
    if path is None:
        path = _get_business_events_path()

    sections = {}
    for section in _SECTION_PARSERS:
        if section == key:
            sections[section] = items
            continue
        try:
            sections[section] = _load_section(section, path)
        except Exception:
            sections[section] = []

    events_file = BusinessEventsFile(**sections)

    try:
        save_yaml_file(path, events_file.model_dump(mode="json"))
        logger.info(f"Saved {len(items)} business event {key} to {path}")
    except Exception as e:
        raise FileOperationError(f"Failed to write business events file: {e}")


def load_business_events(path: Optional[str] = None) -> List[BusinessEvent]:
    """
    Load business events from YAML file.

    Args:
        path: Optional path to business_events.yml. If not provided, uses
              configured BUSINESS_EVENTS_PATH or default location.

    Returns:
        List of BusinessEvent objects; empty if the file does not exist.

    Raises:
        FileOperationError: If file exists but cannot be read or parsed.
    """
    return _load_section("events", path)


def save_business_events(
    events: List[BusinessEvent], path: Optional[str] = None
) -> None:
    """
    Save business events to YAML file, preserving existing processes.

    Args:
        events: List of BusinessEvent objects to save.
        path: Optional path to business_events.yml. If not provided, uses
              configured BUSINESS_EVENTS_PATH or default location.

    Raises:
        FileOperationError: If file cannot be written.
    """
    _save_section("events", events, path)


def load_processes(path: Optional[str] = None) -> List[BusinessEventProcess]:
    """
    Load business event processes from YAML file.

    Processes are stored in the same file as events, under a 'processes' key.

    Args:
        path: Optional path to business_events.yml. If not provided, uses
              configured BUSINESS_EVENTS_PATH or default location.

    Returns:
        List of BusinessEventProcess objects; empty if the file does not exist.

    Raises:
        FileOperationError: If file exists but cannot be read or parsed.
    """
    return _load_section("processes", path)


def save_processes(
    processes: List[BusinessEventProcess], path: Optional[str] = None
) -> None:
    """
    Save business event processes to YAML file, preserving existing events.

    Args:
        processes: List of BusinessEventProcess objects to save.
        path: Optional path to business_events.yml. If not provided, uses
              configured BUSINESS_EVENTS_PATH or default location.

    Raises:
        FileOperationError: If file cannot be written.
    """
    _save_section("processes", processes, path)
