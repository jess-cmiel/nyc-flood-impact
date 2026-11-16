"""Repo-relative path helpers for portable manifests / desk JSON."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
_ABS_RE = re.compile(r"^/home/[^/]+/projects/nyc-flood-impact/")


def repo_rel(path: Path | str, root: Path | None = None) -> str:
    p = Path(path)
    base = root or REPO_ROOT
    try:
        return str(p.resolve().relative_to(base.resolve()))
    except Exception:  # noqa: BLE001
        s = str(path)
        if _ABS_RE.match(s):
            return _ABS_RE.sub("", s)
        return s


def relativize_obj(obj: Any, root: Path | None = None) -> Any:
    """Recursively rewrite absolute nyc-flood-impact paths to repo-relative strings."""
    base = root or REPO_ROOT
    if isinstance(obj, dict):
        return {k: relativize_obj(v, base) for k, v in obj.items()}
    if isinstance(obj, list):
        return [relativize_obj(v, base) for v in obj]
    if isinstance(obj, str) and ("/nyc-flood-impact/" in obj or obj.startswith(str(base))):
        try:
            return repo_rel(obj, base)
        except Exception:  # noqa: BLE001
            return _ABS_RE.sub("", obj) if _ABS_RE.match(obj) else obj
    return obj


def git_sha(root: Path | None = None) -> str | None:
    base = root or REPO_ROOT
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=base,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip() or None
    except Exception:  # noqa: BLE001
        return None
