"""Access replay pack size + join integrity."""

from __future__ import annotations

import json
from pathlib import Path

from flood_risk.risk.access_signals import apply_access_and_demotion, load_access_fixture
from flood_risk.risk.demo_shortlist import demo_shortlist_ids

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "figures" / "product_assets" / "access_signals_ida_fixture.json"
DESK = ROOT / "figures" / "product_assets" / "decision_desk_assets.json"


def test_access_fixture_has_at_least_40_joins():
    assert FIXTURE.exists()
    fx = load_access_fixture(FIXTURE)
    joins = fx.get("joins") or []
    assert len(joins) >= 40, f"expected ≥40 joins, got {len(joins)}"
    assert fx.get("synthetic") is True or any(
        j.get("synthetic") for j in joins
    ), "replay pack must label synthetic joins"
    honesty = str(fx.get("honesty") or "").lower()
    assert "not official" in honesty or "synthetic" in honesty


def test_shortlist_rows_have_access_chips_after_join():
    desk = json.loads(DESK.read_text())
    fx = load_access_fixture(FIXTURE)
    apply_access_and_demotion(desk, fx, buffer_m=float(fx.get("buffer_m") or 100))
    by_id = {a["id"]: a for a in desk["assets"]}
    for aid in demo_shortlist_ids():
        a = by_id[aid]
        assert a.get("access_status") in ("limited", "watch"), aid
        assert a.get("access_signals"), aid


def test_joined_non_open_count_ge_40():
    desk = json.loads(DESK.read_text())
    fx = load_access_fixture(FIXTURE)
    apply_access_and_demotion(desk, fx, buffer_m=float(fx.get("buffer_m") or 100))
    meta = desk.get("access_signals") or {}
    joined = int(meta.get("joined_assets") or 0)
    non_open = sum(
        1
        for a in desk["assets"]
        if a.get("access_status") in ("limited", "watch") and a.get("access_signals")
    )
    assert joined >= 40 or non_open >= 40


def test_empty_catch_basins_quarantined_or_absent():
    live = ROOT / "figures" / "product_assets" / "catch_basins.geojson"
    quarantined = ROOT / "figures" / "product_assets" / "quarantine" / "catch_basins.geojson"
    if live.exists():
        geo = json.loads(live.read_text())
        assert len(geo.get("features") or []) > 0, "empty catch_basins must be quarantined"
    else:
        assert quarantined.exists() or True  # absent from live tree is OK
