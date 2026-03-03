"""Shared path resolution utilities.

Goals:
- Machine-agnostic resolution of runtime/governance directories via env vars
- Single source of truth to prevent drift across doctor/gates/executor
- Optional redaction of user-specific prefixes (HOME / OneDrive) in diagnostic output

These helpers must not change determinism guarantees; they only resolve paths.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


def resolve_dir_env(env_var: str, default: Path) -> Path:
    """Resolve a directory env var to an absolute Path.

    - Expands environment variables and ~
    - Resolves to an absolute path
    - Falls back to `default` when unset/blank
    """
    raw = os.getenv(env_var)
    if raw and raw.strip():
        expanded = os.path.expandvars(raw.strip())
        return Path(expanded).expanduser().resolve()
    return Path(default).resolve()


def resolve_bootstrap_governance_dir(bootstrap_root: Path) -> Path:
    bootstrap_root = Path(bootstrap_root).resolve()
    return resolve_dir_env("BOOTSTRAP_GOVERNANCE_DIR", bootstrap_root / ".governance")


def resolve_worker_runtime_dir(worker_root: Path) -> Path:
    worker_root = Path(worker_root).resolve()
    return resolve_dir_env("WORKER_RUNTIME_DIR", worker_root)


def get_onedrive_roots() -> List[Path]:
    """Best-effort OneDrive root detection.

    Uses the common environment variables on Windows plus a simple HOME/OneDrive
    heuristic when present.
    """
    roots: List[Path] = []

    for key in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
        value = os.getenv(key)
        if value and value.strip():
            try:
                roots.append(Path(value).expanduser().resolve())
            except Exception:
                continue

    try:
        candidate = Path.home() / "OneDrive"
        if candidate.exists():
            roots.append(candidate.resolve())
    except Exception:
        pass

    # Deduplicate (case-insensitive on Windows)
    seen = set()
    unique: List[Path] = []
    for root in roots:
        key = str(root).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(root)

    return unique


def is_under_any_root(path: Path, roots: Sequence[Path]) -> bool:
    """Return True if `path` is under any of `roots` (case-insensitive best-effort)."""
    try:
        path_resolved = Path(path).resolve()
    except Exception:
        return False

    path_str = str(path_resolved).lower()

    for root in roots:
        try:
            root_str = str(Path(root).resolve()).lower().rstrip("\\/")
        except Exception:
            continue

        if path_str == root_str:
            return True

        # Ensure boundary match (so C:\OneDriveX doesn't match C:\OneDrive)
        boundary = root_str + os.sep.lower()
        if path_str.startswith(boundary):
            return True

    return False


def _as_posix(path: Path) -> str:
    # Use forward slashes for stable display.
    try:
        return path.as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def redact_path(
    path: Path,
    *,
    home_dir: Optional[Path] = None,
    onedrive_roots: Optional[Sequence[Path]] = None,
) -> str:
    """Redact user-specific path prefixes for deterministic, shareable output.

    - Replaces any detected OneDrive root prefix with <ONEDRIVE>
    - Replaces HOME prefix with <HOME>

    Returns a display string using forward slashes.
    """
    try:
        p = Path(path).resolve()
    except Exception:
        # Fall back to string form
        return str(path)

    display = _as_posix(p)

    # Prefer OneDrive redaction if applicable
    if onedrive_roots:
        for root in onedrive_roots:
            try:
                r = Path(root).resolve()
            except Exception:
                continue
            r_display = _as_posix(r).rstrip("/")
            if display == r_display:
                return "<ONEDRIVE>"
            if display.startswith(r_display + "/"):
                return "<ONEDRIVE>" + display[len(r_display) :]

    if home_dir is not None:
        try:
            h = Path(home_dir).resolve()
            h_display = _as_posix(h).rstrip("/")
            if display == h_display:
                return "<HOME>"
            if display.startswith(h_display + "/"):
                return "<HOME>" + display[len(h_display) :]
        except Exception:
            pass

    return display
