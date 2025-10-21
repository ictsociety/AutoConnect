#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - Simple Credentials Helper

Lightweight helper to remember the last used student ID and birthday so users
aren't forced to retype details every single time. This stores plain values in
an app-specific config folder (see PathManager.get_config_dir()).

Notes (tiny, human-style):
- 2025-10-06: added quick save/load to reduce friction during setup
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

from src.utils.system_utils import PathManager


CREDENTIALS_FILE = "credentials.json"


def _get_credentials_path() -> Path:
    cfg = PathManager.get_config_dir()
    cfg.mkdir(parents=True, exist_ok=True)
    return cfg / CREDENTIALS_FILE


def save_credentials(student_id: str, birthday: str) -> bool:
    """Persist latest credentials.

    Both values are stored as-is. This is meant for convenience, not security.
    """
    try:
        path = _get_credentials_path()
        payload = {"student_id": student_id or "", "birthday": birthday or ""}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def load_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Load previously saved credentials if available.

    Returns (student_id, birthday) or (None, None) when absent.
    """
    try:
        path = _get_credentials_path()
        if not path.exists():
            return None, None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("student_id") or None, data.get("birthday") or None
    except Exception:
        return None, None


def remove_credentials() -> bool:
    """Remove saved credentials file.

    Returns True if successful or file didn't exist, False on error.
    """
    try:
        path = _get_credentials_path()
        if path.exists():
            path.unlink()
        return True
    except Exception:
        return False
