#!/usr/bin/env python3
"""Rewrite absolute machine paths in shipped product_assets JSON to repo-relative."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from flood_risk.risk.repo_paths import git_sha, relativize_obj  # noqa: E402
from nyc_flash_flood_case_study.config import FIGURES_DIR  # noqa: E402

ASSETS = FIGURES_DIR / "product_assets"
TARGETS = (
    "product_manifest.json",
    "manifest.json",
    "decision_desk_assets.json",
    "decision_desk_assets_henri.json",
)


def main() -> None:
    sha = git_sha()
    rewritten = []
    for name in TARGETS:
        path = ASSETS / name
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        data = relativize_obj(data)
        if isinstance(data, dict):
            data.setdefault("schema_version", "1.1.0")
            if sha:
                data["git_sha"] = sha
            if name.startswith("decision_desk"):
                eng = data.get("depth_engine") or {}
                if isinstance(eng.get("depth_tif"), str):
                    eng["depth_tif"] = relativize_obj(eng["depth_tif"])
                data["depth_engine"] = eng
        path.write_text(json.dumps(data, indent=2))
        rewritten.append(name)
    print(json.dumps({"rewritten": rewritten, "git_sha": sha}, indent=2))


if __name__ == "__main__":
    main()
