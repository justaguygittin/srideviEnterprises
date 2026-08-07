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

Author  : Srikar
=========================================================
"""

import json
import secrets
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "maintenance.json"

_DEFAULT_CONFIG: dict[str, Any] = {"enabled": False, "maintenance_key": ""}


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
    }


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
