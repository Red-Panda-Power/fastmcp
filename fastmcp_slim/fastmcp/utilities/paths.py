"""Small path helpers shared by filesystem integrations."""

from pathlib import Path


def is_relative_to(path: Path, base: Path) -> bool:
    """Return whether `path` is inside `base` using pathlib's path semantics."""
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True
