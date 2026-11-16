"""HAND↔SFINCS disagreement chips — non-peer, never blended."""

from __future__ import annotations

import json
from pathlib import Path

from flood_risk.risk.demo_shortlist import demo_shortlist_ids

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "figures" / "product_assets"
DIS = ASSETS / "engine_disagreement_ida.json"
SHORT = ASSETS / "decision_desk_shortlist.json"


def test_disagreement_payload_honesty():
    assert DIS.exists()
    data = json.loads(DIS.read_text())
    assert data.get("official_nws") is False
    honesty = str(data.get("honesty") or "").lower()
    assert "not peer" in honesty or "non-peer" in honesty or "never blended" in honesty or "not blended" in honesty
    assert data.get("n", 0) >= 4
    assert "blend" not in honesty or "never" in honesty


def test_shortlist_has_engine_compare_and_at_least_one_disagree():
    desk = json.loads(SHORT.read_text())
    by = {a["id"]: a for a in desk.get("assets") or []}
    disagrees = 0
    for aid in demo_shortlist_ids():
        a = by[aid]
        ec = a.get("engine_compare") or {}
        assert ec.get("chip")
        assert ec.get("non_peer") is True
        assert "sfincs_m" in ec or ec.get("sfincs_m") is None or isinstance(ec.get("sfincs_m"), (int, float))
        if ec.get("disagree"):
            disagrees += 1
    assert disagrees >= 1


def test_shortlist_bundle_exists_for_lazy_load():
    assert SHORT.exists()
    data = json.loads(SHORT.read_text())
    assert data.get("bundle") == "shortlist_top100"
    assert data.get("full_desk_json") == "decision_desk_assets.json"
    assert len(data.get("assets") or []) >= 4
    geo = ASSETS / "decision_desk_shortlist.geojson"
    assert geo.exists()
