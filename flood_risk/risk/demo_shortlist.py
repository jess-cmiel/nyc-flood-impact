"""Single-source demo shortlist loader for Asset Decision Desk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SHORTLIST_PATH = REPO_ROOT / "config" / "demo_shortlist.yaml"


def load_demo_shortlist(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_SHORTLIST_PATH
    data = yaml.safe_load(p.read_text()) or {}
    assets = list(data.get("assets") or [])
    ids = [str(a["id"]) for a in assets if a.get("id")]
    if not ids:
        raise ValueError(f"demo shortlist empty: {p}")
    return {
        "path": str(p.relative_to(REPO_ROOT)) if p.is_relative_to(REPO_ROOT) else str(p),
        "event": data.get("event") or "ida-2021",
        "honesty": data.get("honesty") or "",
        "assets": assets,
        "ids": ids,
    }


def demo_shortlist_ids(path: Path | None = None) -> list[str]:
    return list(load_demo_shortlist(path)["ids"])
