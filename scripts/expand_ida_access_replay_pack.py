#!/usr/bin/env python3
"""Expand labeled synthetic Ida access replay pack to ≥40 joins.

Synthetic DOT / 511 / MTA signals are explicitly labeled. NOT official closures.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from flood_risk.risk.access_signals import apply_access_and_demotion, load_access_fixture  # noqa: E402
from flood_risk.risk.decision_classes import is_decision_class_asset  # noqa: E402
from flood_risk.risk.demo_shortlist import demo_shortlist_ids  # noqa: E402
from nyc_flash_flood_case_study.config import FIGURES_DIR, OUTPUTS_DIR  # noqa: E402

ASSETS = FIGURES_DIR / "product_assets"
FIXTURE = ASSETS / "access_signals_ida_fixture.json"
MIN_JOINS = 40


def _status_for_depth(cm: float) -> str:
    if cm >= 10.0:
        return "limited"
    if cm >= 8.0:
        return "limited"
    return "watch"


def build_expanded_fixture(desk: dict) -> dict:
    shortlist = set(demo_shortlist_ids())
    existing = load_access_fixture(FIXTURE) if FIXTURE.exists() else {
        "id": "ida_access_signals_v2",
        "dot_speeds": [],
        "events_511": [],
        "mta_alerts": [],
        "joins": [],
    }
    by_join = {str(j["asset_id"]): j for j in (existing.get("joins") or []) if j.get("asset_id")}

    candidates = [
        a
        for a in (desk.get("assets") or [])
        if a.get("band") in ("deep_ponding", "hazard")
        and a.get("nyc_demo_geography", True)
        and is_decision_class_asset(a)
    ]
    # Prefer shortlist first, then deepest decision-class.
    candidates.sort(
        key=lambda a: (
            0 if a["id"] in shortlist else 1,
            -float(a.get("max_depth_m") or 0.0),
        )
    )

    dot_speeds = list(existing.get("dot_speeds") or [])
    events_511 = list(existing.get("events_511") or [])
    mta_alerts = list(existing.get("mta_alerts") or [])
    joins = list(by_join.values())
    seen = set(by_join)

    for a in candidates:
        aid = str(a["id"])
        if aid in seen:
            continue
        if len(seen) >= max(MIN_JOINS, 50):
            break
        cm = float(a.get("max_depth_cm") or 0.0)
        status = _status_for_depth(cm)
        lon, lat = float(a["lon"]), float(a["lat"])
        name = str(a.get("name") or aid)
        at = a.get("asset_type")
        signals: list[dict] = []

        if at == "road":
            sid = f"dot:synth:{aid.replace(':', '_')}"
            ratio = 0.18 if status == "limited" else 0.42
            dot_speeds.append(
                {
                    "id": sid,
                    "label": f"{name} · synthetic Ida speed stress (research replay)",
                    "lon": lon,
                    "lat": lat,
                    "speed_mph": round(45 * ratio, 1),
                    "free_flow_mph": 45,
                    "speed_ratio": ratio,
                    "link_name": name,
                    "synthetic": True,
                }
            )
            eid = f"511:synth:{aid.replace(':', '_')}"
            events_511.append(
                {
                    "id": eid,
                    "label": f"511-style · synthetic ponding near {name} (research replay)",
                    "lon": lon,
                    "lat": lat,
                    "closure": status == "limited",
                    "event_type": "incident" if status == "limited" else "alert",
                    "road": name,
                    "synthetic": True,
                }
            )
            signals = [
                {
                    "source": "nyc_dot_speeds",
                    "id": sid,
                    "label": f"{name} · synthetic Ida speed stress (research replay)",
                    "speed_ratio": ratio,
                    "access": status,
                    "synthetic": True,
                },
                {
                    "source": "nysdot_511_events",
                    "id": eid,
                    "label": f"511-style · synthetic ponding near {name} (research replay)",
                    "access": status,
                    "synthetic": True,
                },
            ]
        elif at == "station":
            mid = f"mta:synth:{aid.replace(':', '_')}"
            mta_alerts.append(
                {
                    "id": mid,
                    "label": f"MTA alert · synthetic access stress at {name} (research replay)",
                    "access": status,
                    "station_names": [name],
                    "asset_ids": [aid],
                    "effect": "station_access_limited" if status == "limited" else "watch",
                    "synthetic": True,
                }
            )
            signals = [
                {
                    "source": "mta_alerts",
                    "id": mid,
                    "label": f"MTA alert · synthetic access stress at {name} (research replay)",
                    "access": status,
                    "synthetic": True,
                }
            ]
        else:
            eid = f"511:synth:{aid.replace(':', '_')}"
            events_511.append(
                {
                    "id": eid,
                    "label": f"511-style · synthetic access watch near {name} (research replay)",
                    "lon": lon,
                    "lat": lat,
                    "closure": False,
                    "event_type": "alert",
                    "road": name,
                    "synthetic": True,
                }
            )
            signals = [
                {
                    "source": "nysdot_511_events",
                    "id": eid,
                    "label": f"511-style · synthetic access watch near {name} (research replay)",
                    "access": "watch" if status != "limited" else "limited",
                    "synthetic": True,
                }
            ]
            status = signals[0]["access"]

        joins.append(
            {
                "asset_id": aid,
                "access": status,
                "synthetic": True,
                "signals": signals,
            }
        )
        seen.add(aid)

    # Ensure shortlist always joined
    for sid in shortlist:
        if sid in seen:
            continue
        a = next((x for x in desk.get("assets") or [] if x["id"] == sid), None)
        if not a:
            continue
        joins.append(
            {
                "asset_id": sid,
                "access": "limited" if float(a.get("max_depth_cm") or 0) >= 9 else "watch",
                "synthetic": True,
                "signals": [
                    {
                        "source": "nysdot_511_events",
                        "id": f"511:shortlist:{sid.replace(':', '_')}",
                        "label": f"511-style · shortlist access chip for {a.get('name')} (research)",
                        "access": "watch",
                        "synthetic": True,
                    }
                ],
            }
        )
        seen.add(sid)

    return {
        "id": "ida_access_signals_v2",
        "fixture_pack": "ida_v1",
        "replay": "Hurricane Ida remnants 2021-09-01 (research fixture)",
        "synthetic": True,
        "honesty": (
            "Labeled synthetic Ida replay pack (DOT / 511-style / MTA) + research HAND depth — "
            "NOT official closures. Synthetic timestamps / joins marked synthetic:true."
        ),
        "sources": ["nyc_dot_speeds", "nysdot_511_events", "mta_alerts"],
        "buffer_m": 100,
        "min_joins_target": MIN_JOINS,
        "dot_speeds": dot_speeds,
        "events_511": events_511,
        "mta_alerts": mta_alerts,
        "joins": joins,
    }


def main() -> None:
    desk_json = ASSETS / "decision_desk_assets.json"
    desk_geo = ASSETS / "decision_desk_assets.geojson"
    desk = json.loads(desk_json.read_text())
    fixture = build_expanded_fixture(desk)
    FIXTURE.write_text(json.dumps(fixture, indent=2))
    pack_dir = ROOT / "fixtures" / "ida_v1"
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "access_signals.json").write_text(json.dumps(fixture, indent=2))
    (pack_dir / "README.md").write_text(
        "# Ida fixture pack v1\n\nLabeled synthetic access replay for Decision Desk demos.\n"
        "NOT official closures. Checksums: run `sha256sum access_signals.json`.\n"
    )

    apply_access_and_demotion(desk, fixture, buffer_m=float(fixture.get("buffer_m") or 100))
    desk["listed_n"] = len(desk.get("assets") or [])
    desk_json.write_text(json.dumps(desk, indent=2))
    (OUTPUTS_DIR / "decision_desk_assets.json").write_text(desk_json.read_text())
    if desk_geo.exists():
        geo = json.loads(desk_geo.read_text())
        by_id = {a["id"]: a for a in desk.get("assets") or []}
        for ft in geo.get("features") or []:
            props = ft.get("properties") or {}
            aid = props.get("id")
            if aid in by_id:
                ft["properties"] = dict(by_id[aid])
        desk_geo.write_text(json.dumps(geo))

    joined = sum(
        1
        for a in desk.get("assets") or []
        if a.get("access_status") in ("limited", "watch") and a.get("access_signals")
    )
    print(
        json.dumps(
            {
                "fixture": str(FIXTURE),
                "joins": len(fixture.get("joins") or []),
                "joined_non_open": joined,
                "access_meta": desk.get("access_signals"),
                "shortlist": [
                    {
                        "id": a["id"],
                        "access": a.get("access_status"),
                        "hint": a.get("action_hint"),
                    }
                    for a in desk.get("assets") or []
                    if a["id"] in set(demo_shortlist_ids())
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
