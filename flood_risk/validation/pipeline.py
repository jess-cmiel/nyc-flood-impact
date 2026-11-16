"""Orchestrate the Ida scientific validation pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flood_risk.validation.boundaries import boundary_report
from flood_risk.validation.exports import write_exports
from flood_risk.validation.factors import (
    build_sample_points_table,
    precip_depth_correlation,
    validate_antecedent_rainfall,
    validate_drainage_blockage,
    validate_elevation,
    validate_floodnet_obs,
    validate_hand_primary,
    validate_impervious,
    validate_precip_intensity_duration,
    validate_sfincs_reference,
    validate_slope,
    validate_susceptibility,
)
from flood_risk.validation.paths import ASSETS
from flood_risk.validation.plots import generate_all_plots
from flood_risk.validation.provenance import ProvenanceTag
from flood_risk.validation.synthetic_checks import run_synthetic_sanity


def _real_vs_synthetic(factors: dict[str, Any]) -> dict[str, list[str]]:
    buckets = {
        "observed": [],
        "modeled": [],
        "synthetic": [],
        "missing": [],
    }
    for fid, f in factors.items():
        if f.get("status") == "missing":
            buckets["missing"].append(fid)
            continue
        prov = f.get("provenance")
        if prov in buckets:
            buckets[prov].append(fid)
        else:
            buckets.setdefault(str(prov), []).append(fid)
    return buckets


def run_validation_pipeline(
    *,
    write_product: bool = True,
    make_plots: bool = True,
    sync_store_assets: Path | None = None,
) -> dict[str, Any]:
    factors = {
        "precip_intensity_duration": validate_precip_intensity_duration(),
        "antecedent_rainfall": validate_antecedent_rainfall(),
        "elevation": validate_elevation(),
        "slope": validate_slope(),
        "impervious_surface": validate_impervious(),
        "drainage_blockage_indicators": validate_drainage_blockage(),
        "flood_susceptibility": validate_susceptibility(),
        "hand_primary_depth": validate_hand_primary(),
        "sfincs_physics_reference": validate_sfincs_reference(),
        "floodnet_observations": validate_floodnet_obs(),
    }

    # Drop bulky sample_values from factor bodies after plots (kept temporarily)
    sample_rows = build_sample_points_table()
    corr = precip_depth_correlation()

    hand_stats = (factors["hand_primary_depth"].get("stats") or {})
    fn_stats = (factors["floodnet_observations"].get("stats") or {})
    sanity = run_synthetic_sanity(
        hand_max_m=hand_stats.get("max"),
        floodnet_peak_mean_m=fn_stats.get("obs_peak_mean_m"),
        precip_depth_corr=corr,
    )

    diag_dir = ASSETS / "validation_diags"
    plot_artifacts: list[dict[str, str]] = []
    if make_plots:
        plot_artifacts = generate_all_plots(factors, sample_rows, diag_dir)

    # Strip sample arrays from exported factor JSON (keep plots only)
    slope = dict(factors["slope"])
    slope.pop("sample_values", None)
    factors["slope"] = slope

    provenance_mix = _real_vs_synthetic(factors)
    report: dict[str, Any] = {
        "product": "flood_risk_research_prototype",
        "pipeline": "flood_risk.validation.pipeline",
        "event": "ida-2021",
        "official_nws": False,
        "decision_grade": False,
        "certified_skill": False,
        "enterprise": False,
        "hens": False,
        "not_swmm": True,
        "hand_primary": True,
        "sfincs_role": "advanced_research_hydro_non_peer",
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "honesty": (
            "Scientific factor validation for the Decision Desk. "
            "Every factor is tagged observed / modeled / synthetic. "
            "NOT NWS verification · NOT decision-grade · HAND stays primary · "
            "SFINCS is Advanced non-peer reference."
        ),
        "factors": factors,
        "correlations": {
            "precip_vs_hand_pearson_r": corr,
            "hand_vs_sfincs_pearson_r": factors["sfincs_physics_reference"].get(
                "hand_sfincs_pearson_r"
            ),
        },
        "synthetic_sanity": sanity,
        "provenance_mix": provenance_mix,
        "module_boundaries": boundary_report(),
        "sample_point_count": len(sample_rows),
        "exports": {},
        "limitations": [
            "FloodNet Ida network is sparse (≈5 posts) — magnitude honesty, not citywide skill.",
            "HAND is cm-scale screening and is intentionally not rescaled to FloodNet.",
            "SFINCS is Advanced / non-peer; disagreement with HAND is expected.",
            "Legacy stub rasters (slope.tif, antecedent_wetness.tif) remain labeled synthetic.",
            "Drainage indicators are open-data proxies — not SWMM / not DEP.",
            "Earth-2 weather inputs are validated separately from hydrologic modules.",
        ],
    }

    paths: dict[str, str] = {}
    if write_product:
        paths = write_exports(
            report,
            sample_rows,
            plot_artifacts,
            sync_store_assets=sync_store_assets,
        )
        report["exports"] = {
            "summary_json": "science_validation_summary.json",
            "points_geojson": "science_validation_points.geojson",
            "diags_dir": "validation_diags",
            "plot_artifacts": plot_artifacts,
            "written": paths,
        }

    return report


def main_summary(report: dict[str, Any]) -> dict[str, Any]:
    mix = report.get("provenance_mix") or {}
    sanity = report.get("synthetic_sanity") or {}
    return {
        "updated_utc": report.get("updated_utc"),
        "observed_factors": mix.get("observed"),
        "modeled_factors": mix.get("modeled"),
        "synthetic_factors": mix.get("synthetic"),
        "synthetic_sanity_n_fail": sanity.get("n_fail"),
        "failing_rules": [r.get("rule_id") for r in sanity.get("failing_cases") or []],
        "exports": (report.get("exports") or {}).get("written")
        or {
            "summary": str(ASSETS / "science_validation_summary.json"),
        },
    }
