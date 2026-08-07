"""
=========================================================
Project : Sridevi Enterprises
File    : maintenance_service.py
Purpose : Maintenance Mode state.

          Reads config/maintenance.json - a lightweight, file-based
          on/off switch (no database table) used to take the customer
          website offline during deploys and database migrations,
          without exposing customers to a partially-deployed or broken
          site (see AI_CONTEXT.md "Maintenance Mode").

          Sprint 10 (Administration Tools) added the write side -
          set_maintenance_enabled() - so an Admin can flip this from the
          Employee Dashboard instead of hand-editing the file over SSH.

Author  : Srikar
=========================================================
"""

import json
import os
import secrets
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "maintenance.json"

_DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "maintenance_key": "",
    "last_changed": None,
    "changed_by": None,
}


def get_maintenance_config() -> dict[str, Any]:
    """
    Read config/maintenance.json fresh on every call - no caching, so an
    admin editing the file and restarting Passenger is all that's needed
    to flip Maintenance Mode, with no code change and no redeploy.

    Falls back to the disabled default if the file is missing or
    unreadable (e.g. a fresh checkout that hasn't copied
    config/maintenance.example.json yet), so the app never accidentally
    locks customers out because of a missing config file.
    """

    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
    except (OSError, ValueError):
        return dict(_DEFAULT_CONFIG)

    return {
        "enabled": bool(data.get("enabled", False)),
        "maintenance_key": str(data.get("maintenance_key", "")),
        # Added Sprint 10 - who last flipped the switch and when, surfaced
        # read-only on the Employee Dashboard. Both are None for a
        # maintenance.json that predates this sprint or was never toggled
        # through set_maintenance_enabled() (e.g. hand-edited on the
        # server) - that's a normal, expected state, not an error.
        "last_changed": data.get("last_changed"),
        "changed_by": data.get("changed_by"),
    }


def set_maintenance_enabled(enabled: bool, changed_by: str | None) -> None:
    """
    Flip Maintenance Mode on/off and record who changed it and when.

    This is the single choke point every write to maintenance.json goes
    through (currently only the Admin Dashboard toggle,
    routes/employee.py:update_maintenance()) - keeping it this way means a
    future audit-log feature only needs to add a call here, not touch the
    route or template.

    The configured maintenance_key is always read from disk and carried
    forward untouched, so toggling Enabled/Disabled can never reset or
    blank out the bypass key. Written atomically (temp file + os.replace)
    so a request that reads the file mid-write can never see a partially
    written/corrupt JSON document.
    """

    current = get_maintenance_config()

    updated = {
        "enabled": bool(enabled),
        "maintenance_key": current["maintenance_key"],
        "last_changed": datetime.now().isoformat(timespec="seconds"),
        "changed_by": changed_by,
    }

    config_dir = _CONFIG_PATH.parent
    fd, temp_path = tempfile.mkstemp(dir=config_dir, prefix=".maintenance.", suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(updated, temp_file, indent=4)
        os.replace(temp_path, _CONFIG_PATH)
    except BaseException:
        os.remove(temp_path)
        raise


def is_maintenance_enabled() -> bool:
    """Return whether Maintenance Mode is currently enabled."""

    return get_maintenance_config()["enabled"]


def verify_maintenance_key(candidate_key: str) -> bool:
    """
    Constant-time check of a submitted ?maintenance_key= value against the
    configured secret.

    An empty configured key never matches anything, so a maintenance.json
    that hasn't had a real key set yet can't be bypassed with an empty
    query string.
    """

    configured_key = get_maintenance_config()["maintenance_key"]

    if not configured_key or not candidate_key:
        return False

    return secrets.compare_digest(candidate_key, configured_key)
