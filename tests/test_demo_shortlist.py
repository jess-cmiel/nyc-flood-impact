"""Golden checks for demo shortlist SSOT + decision-class helpers."""

from __future__ import annotations

import json
from pathlib import Path

from flood_risk.risk.decision_classes import (
    is_decision_class_asset,
    is_unnamed_asset,
    typed_action_hint,
)
from flood_risk.risk.demo_shortlist import demo_shortlist_ids, load_demo_shortlist

ROOT = Path(__file__).resolve().parents[1]
DESK = ROOT / "figures" / "product_assets" / "decision_desk_assets.json"


def test_shortlist_yaml_loads_four_ids():
    meta = load_demo_shortlist()
    ids = meta["ids"]
    assert len(ids) == 4
    assert ids[0] == "stations:gtfs:F22"
    assert "facilities:uid:a464e8e63eb8b2c92ab1995735cfd284" in ids
    assert "Staten Island University" not in json.dumps(meta)


def test_shortlist_ids_exist_in_ida_desk():
    ids = demo_shortlist_ids()
    assert DESK.exists(), "decision_desk_assets.json missing — build desk first"
    desk = json.loads(DESK.read_text())
    by_id = {a["id"]: a for a in desk.get("assets") or []}
    for aid in ids:
        assert aid in by_id, f"shortlist id missing from Ida desk: {aid}"
        a = by_id[aid]
        assert float(a.get("max_depth_cm") or 0) >= 8.0
        assert a.get("band") in ("deep_ponding", "hazard")


def test_typed_hints_differ_by_class():
    station = {
        "asset_type": "station",
        "band": "deep_ponding",
        "structure": "Viaduct",
        "name": "Smith-9 Sts",
    }
    hospital = {
        "asset_type": "facility",
        "facility_type": "hospital",
        "band": "deep_ponding",
        "name": "Brooklyn Hospital",
    }
    road = {
        "asset_type": "road",
        "highway": "motorway",
        "band": "deep_ponding",
        "name": "Van Wyck Expressway",
    }
    hs = typed_action_hint(station)
    hh = typed_action_hint(hospital)
    hr = typed_action_hint(road)
    assert hs != hh != hr
    assert "viaduct" in hs.lower() or "Viaduct" in hs or "Elevated" in hs
    assert "Hospital" in hh or "hospital" in hh.lower()
    assert "roadway" in hr.lower() or "ramp" in hr.lower()
    assert "NWS" not in hs and "NWS" not in hh


def test_decision_class_filters_schools_and_unnamed():
    school = {"asset_type": "facility", "facility_type": "school", "name": "PS 1"}
    hospital = {"asset_type": "facility", "facility_type": "hospital", "name": "Hospital X"}
    unnamed = {"asset_type": "road", "highway": "motorway", "name": "unnamed motorway (1)"}
    station = {"asset_type": "station", "name": "Smith-9 Sts"}
    assert not is_decision_class_asset(school)
    assert is_decision_class_asset(hospital)
    assert not is_decision_class_asset(unnamed)
    assert is_unnamed_asset(unnamed)
    assert is_decision_class_asset(station)
