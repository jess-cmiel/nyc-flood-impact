#!/usr/bin/env python3
"""Precompute HAND vs SFINCS wet/dry disagreement for shortlist + top-100.

Non-peer magnitudes — never blended. Research chips only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from flood_risk.risk.decision_classes import is_decision_class_asset  # noqa: E402
from flood_risk.risk.demo_shortlist import demo_shortlist_ids  # noqa: E402
from flood_risk.risk.repo_paths import git_sha, repo_rel  # noqa: E402
from nyc_flash_flood_case_study.config import FIGURES_DIR, PROJECT_ROOT  # noqa: E402

ASSETS = FIGURES_DIR / "product_assets"
HAND_WET_M = 0.03
SFINCS_WET_M = 0.05  # SFINCS often wet everywhere; still sample honestly


def _sample(ds: rasterio.io.DatasetReader, lon: float, lat: float) -> float | None:
    try:
        vals = list(ds.sample([(lon, lat)]))
        if not vals:
            return None
        v = float(vals[0][0])
        if not np.isfinite(v) or v < 0:
            return None
        return v
    except Exception:  # noqa: BLE001
        return None


def _band(depth_m: float | None, wet_m: float) -> str:
    if depth_m is None or depth_m < wet_m:
        return "dry"
    if depth_m >= 0.15:
        return "hazard"
    if depth_m >= 0.08:
        return "deep_ponding"
    return "ponding"


def _status(hand_m: float, sfincs_m: float | None) -> str:
    hand_wet = hand_m >= HAND_WET_M
    sf_wet = sfincs_m is not None and sfincs_m >= SFINCS_WET_M
    if hand_wet == sf_wet:
        # Both wet but non-peer magnitudes still "agree" on wetness class only
        return "engines agree (wetness)" if hand_wet else "engines agree (dry)"
    if hand_wet and not sf_wet:
        return "disagree (HAND wet · SFINCS dry)"
    return "disagree (HAND dry · SFINCS wet)"


def main() -> None:
    desk = json.loads((ASSETS / "decision_desk_assets.json").read_text())
    shortlist = set(demo_shortlist_ids())
    assets = list(desk.get("assets") or [])
    decision = [a for a in assets if is_decision_class_asset(a)]
    targets = []
    seen = set()
    for a in assets:
        if a["id"] in shortlist and a["id"] not in seen:
            targets.append(a)
            seen.add(a["id"])
    for a in decision:
        if a["id"] in seen:
            continue
        targets.append(a)
        seen.add(a["id"])
        if len(targets) >= 104:  # shortlist + ~100
            break

    sfincs_tif = PROJECT_ROOT / "data/processed/inundation/depth_sfincs_metro_nested_ida_m.tif"
    if not sfincs_tif.exists():
        # fall back to meta pointer
        meta = json.loads((ASSETS / "depth_sfincs_metro_nested_ida_meta.json").read_text())
        cand = Path(str(meta.get("tif") or ""))
        if not cand.is_absolute():
            cand = PROJECT_ROOT / cand
        if cand.exists():
            sfincs_tif = cand

    rows = []
    with rasterio.open(sfincs_tif) as ds:
        for a in targets:
            hand_m = float(a.get("max_depth_m") or 0.0)
            sf_m = _sample(ds, float(a["lon"]), float(a["lat"]))
            status = _status(hand_m, sf_m)
            disagree = status.startswith("disagree")
            row = {
                "asset_id": a["id"],
                "name": a.get("name"),
                "hand_depth_m": round(hand_m, 4),
                "hand_depth_cm": round(hand_m * 100.0, 1),
                "hand_band": a.get("band") or _band(hand_m, HAND_WET_M),
                "sfincs_depth_m": None if sf_m is None else round(float(sf_m), 4),
                "sfincs_band": _band(sf_m, SFINCS_WET_M),
                "status": status,
                "disagree": disagree,
                "chip": "engines disagree (research)" if disagree else "engines agree (research)",
                "hover": (
                    f"HAND {hand_m*100:.1f} cm screening vs SFINCS "
                    f"{'n/a' if sf_m is None else f'{sf_m:.2f} m'} nested sample — "
                    "non-peer magnitudes; never blended. Research only · not NWS."
                ),
            }
            rows.append(row)

    payload = {
        "id": "ida_engine_disagreement_v1",
        "schema_version": "1.1.0",
        "git_sha": git_sha(),
        "product": "asset_decision_desk",
        "honesty": (
            "HAND screening cm vs SFINCS nested metres are NOT peer products. "
            "Chip compares wet/dry / band class only — depths never blended. "
            "SFINCS wet fraction is high citywide; disagreement is research signal only."
        ),
        "official_nws": False,
        "decision_grade": False,
        "hand_wet_m": HAND_WET_M,
        "sfincs_wet_m": SFINCS_WET_M,
        "sfincs_tif": repo_rel(sfincs_tif),
        "n": len(rows),
        "n_disagree": sum(1 for r in rows if r["disagree"]),
        "assets": rows,
    }
    out = ASSETS / "engine_disagreement_ida.json"
    out.write_text(json.dumps(payload, indent=2))
    (ROOT / "fixtures" / "ida_v1" / "engine_disagreement.json").write_text(out.read_text())

    # Merge onto desk + shortlist bundle
    by_id = {r["asset_id"]: r for r in rows}
    for a in assets:
        r = by_id.get(a["id"])
        if not r:
            continue
        a["engine_compare"] = {
            "status": r["status"],
            "chip": r["chip"],
            "hover": r["hover"],
            "disagree": r["disagree"],
            "hand_cm": r["hand_depth_cm"],
            "sfincs_m": r["sfincs_depth_m"],
            "non_peer": True,
        }
    desk["engine_disagreement"] = {
        "file": out.name,
        "n": payload["n"],
        "n_disagree": payload["n_disagree"],
        "honesty": payload["honesty"],
    }
    (ASSETS / "decision_desk_assets.json").write_text(json.dumps(desk, indent=2))

    # Refresh shortlist bundle
    short_assets = [a for a in assets if a["id"] in shortlist]
    tops = [a for a in assets if is_decision_class_asset(a)][:100]
    seen2: set[str] = set()
    bundled = []
    for a in short_assets + tops:
        if a["id"] in seen2:
            continue
        seen2.add(a["id"])
        bundled.append(a)
    bundle = {
        "product": desk.get("product"),
        "schema_version": desk.get("schema_version") or "1.1.0",
        "git_sha": git_sha(),
        "bundle": "shortlist_top100",
        "honesty": desk.get("honesty"),
        "official_nws": False,
        "decision_grade": False,
        "shortlist_ids": list(shortlist),
        "counts": desk.get("counts"),
        "band_action_hints": desk.get("band_action_hints"),
        "access_signals": desk.get("access_signals"),
        "decision_class_filter": desk.get("decision_class_filter"),
        "engine_disagreement": desk.get("engine_disagreement"),
        "assets": bundled,
        "listed_n": len(bundled),
        "full_desk_json": "decision_desk_assets.json",
        "note": "Default lighter desk bundle — full inventory lazy via decision_desk_assets.json",
    }
    (ASSETS / "decision_desk_shortlist.json").write_text(json.dumps(bundle, indent=2))

    print(
        json.dumps(
            {
                "out": str(out),
                "n": payload["n"],
                "n_disagree": payload["n_disagree"],
                "shortlist": [
                    {
                        "id": a["id"],
                        "chip": (a.get("engine_compare") or {}).get("chip"),
                        "sfincs_m": (a.get("engine_compare") or {}).get("sfincs_m"),
                    }
                    for a in assets
                    if a["id"] in shortlist
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
