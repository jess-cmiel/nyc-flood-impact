"""P2.5 denser open drain inventory checks (not SWMM).

Default CI uses tracked sample + meta only. The full regenerable
``osm_drains_metro.geojson`` is gitignored and is not required for PR CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "figures" / "product_assets"
INFRA = ROOT / "data" / "raw" / "infrastructure"
FULL_INVENTORY = INFRA / "osm_drains_metro.geojson"
FETCH_META = INFRA / "osm_drains_metro_fetch_meta.json"
DENSE_SAMPLE = ASSETS / "dep_catch_basins_dense_sample.geojson"
DENSE_META = ASSETS / "denser_drain_inventory_meta.json"


def test_open_drain_inventory_is_dense():
    """Schema / density invariants from tracked fixtures (default CI).

    Asserts the last-built inventory claimed ≥100k open catch basins via
    tracked meta + fetch meta, and that the shipped dense sample carries
    NYC Open Data catch-basin provenance. Does not require the gitignored
    full GeoJSON.
    """
    assert DENSE_SAMPLE.exists(), "tracked dense sample missing"
    assert DENSE_META.exists(), "tracked denser_drain_inventory_meta.json missing"
    assert FETCH_META.exists(), "tracked osm_drains_metro_fetch_meta.json missing"

    sample = json.loads(DENSE_SAMPLE.read_text())
    feats = sample.get("features") or []
    assert len(feats) >= 2000
    assert sample.get("type") == "FeatureCollection"
    sources = {(f.get("properties") or {}).get("source") for f in feats[:2000]}
    assert any("catch_basin" in str(s) or "nyc_open" in str(s) for s in sources)

    meta = json.loads(DENSE_META.read_text())
    assert meta.get("not_swmm") is True
    assert meta.get("not_dep_sewer") is True
    n_meta = int((meta.get("drain_points") or {}).get("n") or 0)
    n_sample_full = int((meta.get("product_sample") or {}).get("n_full") or 0)
    assert n_meta >= 100_000, f"meta drain_points.n expected dense inventory, got {n_meta}"
    assert n_sample_full >= 100_000, f"product_sample.n_full expected dense, got {n_sample_full}"

    fetch = json.loads(FETCH_META.read_text())
    n_merged = int(fetch.get("n_features_merged") or 0)
    n_dep = int(fetch.get("n_dep") or 0)
    assert n_merged >= 100_000, f"fetch meta n_features_merged expected dense, got {n_merged}"
    assert n_dep >= 100_000, f"fetch meta n_dep expected dense DEP catch basins, got {n_dep}"
    honesty = str(fetch.get("honesty") or meta.get("honesty") or "")
    assert "NOT" in honesty.upper() and ("SWMM" in honesty.upper() or "sewer" in honesty.lower())


@pytest.mark.skipif(
    not FULL_INVENTORY.exists(),
    reason="optional local check: regenerable osm_drains_metro.geojson absent (gitignored)",
)
def test_full_open_drain_inventory_file_when_present():
    """Integration-only: when the regenerable full inventory is on disk, count it."""
    geo = json.loads(FULL_INVENTORY.read_text())
    n = len(geo.get("features") or [])
    assert n >= 100_000, f"expected dense open catch-basin inventory, got {n}"
    sources = {(f.get("properties") or {}).get("source") for f in geo["features"][:2000]}
    assert any("catch_basin" in str(s) or "nyc_open" in str(s) for s in sources)


def test_dense_product_sample_and_meta():
    sample = ASSETS / "dep_catch_basins_dense_sample.geojson"
    assert sample.exists(), "run scripts/build_denser_drain_inventory.py"
    geo = json.loads(sample.read_text())
    assert len(geo.get("features") or []) >= 2000
    meta = json.loads((ASSETS / "denser_drain_inventory_meta.json").read_text())
    assert meta.get("not_swmm") is True
    assert meta.get("not_dep_sewer") is True
    cov = (meta.get("drain_points") or {}).get("coverage") or {}
    legacy = (meta.get("drain_points") or {}).get("coverage_legacy_buffer") or {}
    assert cov.get("fraction_with_drain_credit", 0) >= legacy.get("fraction_with_drain_credit", 0)
    assert meta.get("drain_points", {}).get("n", 0) >= 100_000


def test_manifest_points_at_dense_sample():
    m = json.loads((ASSETS / "product_manifest.json").read_text())
    d = m.get("drainage_capacity_proxy") or {}
    assert d.get("not_swmm") is True
    assert "dense" in str(d.get("dense_sample_geojson") or "")
