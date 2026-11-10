"""Backup retention for save files."""
from __future__ import annotations

from pathlib import Path

MAX_BACKUPS = 5


def prune_backups(path: Path, keep: int = MAX_BACKUPS) -> list[Path]:
    """Keep the newest ``keep`` ``<save>.<timestamp>.bak`` files.

    Returns the backup files that were deleted.
    """
    prefix = f"{path.name}."
    try:
        backups = [
            p
            for p in path.parent.iterdir()
            if p.is_file() and p.name.startswith(prefix) and p.name.endswith(".bak")
        ]
    except OSError:
        return []
    backups.sort(key=lambda p: p.name, reverse=True)
    removed: list[Path] = []
    for old in backups[keep:]:
        try:
            old.unlink()
            removed.append(old)
        except OSError:
            pass
    return removed
