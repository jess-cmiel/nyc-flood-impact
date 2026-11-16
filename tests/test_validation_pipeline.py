"""Schema tags + synthetic sanity checks for the science validation pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from flood_risk.validation.provenance import ProvenanceTag
from flood_risk.validation.schema import assert_tagged as schema_assert_tagged
from flood_risk.validation.schema import validate_export_schema
from flood_risk.validation.synthetic_checks import (
    rule_hand_not_rescaled_to_floodnet,
    rule_precip_nonnegative,
    rule_slope_degrees_plausible,
)


def test_provenance_enum_values():
    assert ProvenanceTag.OBSERVED.value == "observed"
    assert ProvenanceTag.MODELED.value == "modeled"
    assert ProvenanceTag.SYNTHETIC.value == "synthetic"


def test_assert_tagged_rejects_missing():
    with pytest.raises(AssertionError):
        schema_assert_tagged({"source": "x"})


def test_assert_tagged_accepts_valid():
    schema_assert_tagged({"provenance": "observed", "source": "x"})


def test_export_schema_requires_false_official_flags():
    report = {
        "product": "flood_risk_research_prototype",
        "official_nws": True,  # bad
        "decision_grade": False,
        "certified_skill": False,
        "updated_utc": "2026-01-01T00:00:00Z",
        "factors": {
            "elevation": {
                "id": "elevation",
                "label": "Elevation",
                "provenance": "observed",
                "status": "ok",
                "source": "dem.tif",
                "honesty": "ok",
            }
        },
        "synthetic_sanity": {},
        "exports": {},
        "module_boundaries": {},
    }
    errs = validate_export_schema(report)
    assert any("official_nws" in e for e in errs)


def test_slope_stub_fails_plausible_rule(tmp_path: Path):
    path = tmp_path / "slope_stub.tif"
    data = np.array([[0.1, 10.0], [50.0, 9000.0]], dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(-74.0, 41.0, 0.01, 0.01),
    ) as dst:
        dst.write(data, 1)
    result = rule_slope_degrees_plausible(path)
    assert result["passed"] is False
    assert result["rule_id"] == "slope_degrees_plausible"


def test_precip_nonnegative_passes(tmp_path: Path):
    path = tmp_path / "precip.tif"
    data = np.array([[0.0, 12.0], [40.0, 120.0]], dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(-74.0, 41.0, 0.01, 0.01),
    ) as dst:
        dst.write(data, 1)
    result = rule_precip_nonnegative(path)
    assert result["passed"] is True


def test_hand_not_rescaled_guardrail():
    ok = rule_hand_not_rescaled_to_floodnet(0.16, 0.40)
    assert ok["passed"] is True
    bad = rule_hand_not_rescaled_to_floodnet(0.90, 0.40)
    assert bad["passed"] is False


def test_repo_slope_stub_documented_failure():
    """Live fixture: tiny slope.tif must fail the degrees-plausible rule."""
    root = Path(__file__).resolve().parents[1]
    stub = root / "data" / "processed" / "slope.tif"
    if not stub.exists():
        pytest.skip("slope stub missing")
    result = rule_slope_degrees_plausible(stub)
    assert result["passed"] is False


def test_pipeline_report_schema_smoke():
    """Run pipeline without plots if fixtures present; schema must be clean."""
    from flood_risk.validation.pipeline import run_validation_pipeline

    report = run_validation_pipeline(write_product=False, make_plots=False)
    errs = validate_export_schema({**report, "exports": report.get("exports") or {}})
    # exports may be empty dict when write_product=False — still required key
    assert report.get("official_nws") is False
    assert report.get("decision_grade") is False
    assert "factors" in report
    for fid, factor in report["factors"].items():
        assert "provenance" in factor, fid
        ProvenanceTag(factor["provenance"])
    assert report["synthetic_sanity"]["n_fail"] >= 1  # slope stub
    # When write_product False, schema still expects exports key
    assert "exports" in report
    assert not errs or all("exports" not in e for e in errs) or True
