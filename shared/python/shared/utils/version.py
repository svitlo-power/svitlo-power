"""Version helper for reading version from embedded VERSION file."""

import os
from pathlib import Path


def get_version() -> str:
    """
    Read version from /app/VERSION file.
    Falls back to "0000.00.00" if file doesn not exist, is unreadable, or contains only whitespace.
    """
    version_file = Path("/app/VERSION")
    try:
        if version_file.exists():
            version = version_file.read_text().strip()
            if version:
                return version
    except Exception:
        pass
    return "0000.00.00"