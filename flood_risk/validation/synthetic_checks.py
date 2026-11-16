"""Physical realism checks for synthetic / stub fixtures.

Documented rules + failing cases. Synthetic data must not invent skill.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np
import rasterio

from flood_risk.validation.paths import catalog
from flood_risk.validation.provenance import ProvenanceTag, tag_block

RuleFn = Callable[[], dict[str, Any]]


def _raster_rule(
    *,
    rule_id: str,
    description: str,
    path: Path,
    check: Callable[[np.ndarray], tuple[bool, str]],
) -> dict[str, Any]:
    if not path.exists():
        return {
            "rule_id": rule_id,
            "description": description,
            "path": str(path),
            "status": "skipped",
            "passed": None,
            "detail": "asset_missing",
        }
    with rasterio.open(path) as src:
        data = src.read(1, masked=True)
        vals = np.ma.compressed(data).astype(np.float64)
    if vals.size == 0:
        return {
            "rule_id": rule_id,
            "description": description,
            "path": str(path),
            "status": "fail",
            "passed": False,
            "detail": "empty_raster",
        }
    ok, detail = check(vals)
    return {
        "rule_id": rule_id,
        "description": description,
        "path": str(path),
        "status": "pass" if ok else "fail",
        "passed": bool(ok),
        "detail": detail,
        "n": int(vals.size),
        "min": float(np.min(vals)),
        "max": float(np.max(vals)),
        "mean": float(np.mean(vals)),
    }


def rule_slope_degrees_plausible(path: Path, *, max_deg: float = 60.0) -> dict[str, Any]:
    """Urban DEM-derived slope should rarely exceed ~60°; stub max≫60 fails."""

    def check(vals: np.ndarray) -> tuple[bool, str]:
        mx = float(np.max(vals))
        if mx > max_deg:
            return False, f"max_slope_deg={mx:.1f} exceeds plausible {max_deg} (likely unscaled rise/run stub)"
        frac = float(np.mean(vals > max_deg))
        if frac > 0.01:
            return False, f"fraction_above_{max_deg}deg={frac:.3f}"
        return True, f"max_slope_deg={mx:.2f}"

    return _raster_rule(
        rule_id="slope_degrees_plausible",
        description=f"Slope values must be in degrees with max ≤ {max_deg}° for NYC DEM context.",
        path=path,
        check=check,
    )


def rule_impervious_fraction_unit_interval(path: Path) -> dict[str, Any]:
    def check(vals: np.ndarray) -> tuple[bool, str]:
        mn, mx = float(np.min(vals)), float(np.max(vals))
        # Allow 0–100 (percent) or 0–1 (fraction)
        if mn < -1e-3:
            return False, f"negative_impervious min={mn}"
        if mx <= 1.0 + 1e-3:
            return True, f"fraction_range=[{mn:.3f},{mx:.3f}]"
        if mx <= 100.0 + 1e-3:
            return True, f"percent_range=[{mn:.1f},{mx:.1f}]"
        return False, f"impervious_out_of_range max={mx}"

    return _raster_rule(
        rule_id="impervious_unit_interval",
        description="Impervious must be fraction [0,1] or percent [0,100].",
        path=path,
        check=check,
    )


def rule_precip_nonnegative(path: Path, *, max_storm_mm: float = 500.0) -> dict[str, Any]:
    def check(vals: np.ndarray) -> tuple[bool, str]:
        mn, mx = float(np.min(vals)), float(np.max(vals))
        if mn < -1e-3:
            return False, f"negative_precip min={mn}"
        if mx > max_storm_mm:
            return False, f"storm_total_mm={mx:.1f} exceeds {max_storm_mm} (unrealistic for Ida metro)"
        return True, f"range_mm=[{mn:.2f},{mx:.2f}]"

    return _raster_rule(
        rule_id="precip_nonnegative_bounded",
        description=f"Precip ≥ 0 and storm total ≤ {max_storm_mm} mm.",
        path=path,
        check=check,
    )


def rule_depth_nonnegative(path: Path, *, max_m: float = 15.0) -> dict[str, Any]:
    def check(vals: np.ndarray) -> tuple[bool, str]:
        # Ignore large negative nodata sentinels already masked; still catch leaks
        if float(np.min(vals)) < -0.05:
            return False, f"negative_depth min={float(np.min(vals))}"
        if float(np.max(vals)) > max_m:
            return False, f"depth_max_m={float(np.max(vals)):.2f} exceeds {max_m}"
        return True, f"range_m=[{float(np.min(vals)):.4f},{float(np.max(vals)):.4f}]"

    return _raster_rule(
        rule_id="depth_nonnegative_bounded",
        description=f"Flood depth ≥ 0 and ≤ {max_m} m.",
        path=path,
        check=check,
    )


def rule_susceptibility_unit_interval(path: Path) -> dict[str, Any]:
    def check(vals: np.ndarray) -> tuple[bool, str]:
        mn, mx = float(np.min(vals)), float(np.max(vals))
        if mn < -0.05 or mx > 1.05:
            return False, f"susceptibility_out_of_[0,1] range=[{mn},{mx}]"
        return True, f"range=[{mn:.4f},{mx:.4f}]"

    return _raster_rule(
        rule_id="susceptibility_unit_interval",
        description="Susceptibility screening index must lie in [0, 1].",
        path=path,
        check=check,
    )


def rule_hand_not_rescaled_to_floodnet(
    hand_max_m: float | None,
    floodnet_peak_mean_m: float | None,
    *,
    ratio_cap: float = 0.5,
) -> dict[str, Any]:
    """Guardrail: do not claim HAND was scaled to match FloodNet peaks."""
    detail = {
        "hand_max_m": hand_max_m,
        "floodnet_peak_mean_m": floodnet_peak_mean_m,
        "policy": "no_hand_rescale_to_floodnet",
    }
    if hand_max_m is None or floodnet_peak_mean_m is None or floodnet_peak_mean_m <= 0:
        return {
            "rule_id": "hand_not_rescaled_to_floodnet",
            "description": "HAND must remain cm-scale screening; never rescale to FloodNet metres.",
            "status": "skipped",
            "passed": None,
            "detail": detail,
        }
    # If HAND max approaches FloodNet mean peaks, flag possible illicit rescale
    ratio = hand_max_m / floodnet_peak_mean_m
    ok = ratio < ratio_cap or hand_max_m < 0.25
    return {
        "rule_id": "hand_not_rescaled_to_floodnet",
        "description": "HAND must remain cm-scale screening; never rescale to FloodNet metres.",
        "status": "pass" if ok else "fail",
        "passed": bool(ok),
        "detail": {**detail, "hand_over_floodnet_mean": ratio},
    }


def rule_negative_corr_precip_depth_forbidden(
    corr: float | None,
    *,
    min_allowed: float = -0.15,
) -> dict[str, Any]:
    """Strongly negative precip↔depth correlation is physically suspect for pluvial forcing."""
    if corr is None:
        return {
            "rule_id": "precip_depth_not_strongly_negative",
            "description": "Precip vs depth correlation should not be strongly negative under pluvial forcing.",
            "status": "skipped",
            "passed": None,
            "detail": "corr_unavailable",
        }
    ok = corr >= min_allowed
    return {
        "rule_id": "precip_depth_not_strongly_negative",
        "description": "Precip vs depth correlation should not be strongly negative under pluvial forcing.",
        "status": "pass" if ok else "fail",
        "passed": bool(ok),
        "detail": {"pearson_r": corr, "min_allowed": min_allowed},
    }


def run_synthetic_sanity(
    *,
    hand_max_m: float | None = None,
    floodnet_peak_mean_m: float | None = None,
    precip_depth_corr: float | None = None,
) -> dict[str, Any]:
    assets = catalog()
    rules = [
        rule_slope_degrees_plausible(assets["slope_stub"].path),
        rule_impervious_fraction_unit_interval(assets["impervious_nlcd"].path),
        rule_precip_nonnegative(assets["mrms_storm_total"].path),
        rule_depth_nonnegative(assets["hand_depth"].path, max_m=2.0),
        rule_depth_nonnegative(assets["sfincs_depth"].path, max_m=15.0),
        rule_susceptibility_unit_interval(assets["susceptibility_storm"].path)
        if assets["susceptibility_storm"].exists
        else rule_susceptibility_unit_interval(assets["susceptibility_stub"].path),
        rule_hand_not_rescaled_to_floodnet(hand_max_m, floodnet_peak_mean_m),
        rule_negative_corr_precip_depth_forbidden(precip_depth_corr),
    ]
    # Also flag antecedent stub as synthetic-only
    ant = assets["antecedent_stub"]
    rules.append(
        {
            "rule_id": "antecedent_stub_labeled_synthetic",
            "description": "Legacy antecedent_wetness.tif is a tiny stub and must stay labeled synthetic.",
            "path": str(ant.path),
            "status": "pass" if ant.provenance == ProvenanceTag.SYNTHETIC else "fail",
            "passed": ant.provenance == ProvenanceTag.SYNTHETIC,
            "detail": tag_block(
                ant.provenance,
                source=str(ant.path),
                honesty=ant.note,
            ),
        }
    )

    n_fail = sum(1 for r in rules if r.get("passed") is False)
    n_pass = sum(1 for r in rules if r.get("passed") is True)
    n_skip = sum(1 for r in rules if r.get("passed") is None)
    failing = [r for r in rules if r.get("passed") is False]
    return {
        **tag_block(
            ProvenanceTag.SYNTHETIC,
            source="flood_risk.validation.synthetic_checks",
            honesty=(
                "Synthetic/stub realism audit. Failures document known placeholder defects "
                "(e.g. slope.tif) — they are not product skill scores."
            ),
            assumptions=[
                "NYC metro slopes from DEM are typically ≪ 60°.",
                "HAND primary depth remains cm-scale and is never rescaled to FloodNet.",
                "No fake SWMM; drainage indicators are open-data proxies only.",
            ],
        ),
        "n_rules": len(rules),
        "n_pass": n_pass,
        "n_fail": n_fail,
        "n_skip": n_skip,
        "rules": rules,
        "failing_cases": failing,
        "documented_known_failures": [
            {
                "asset": "data/processed/slope.tif",
                "reason": "18×40 stub with max ≫ 60° — fails slope_degrees_plausible; use DEM-derived slope instead.",
            },
            {
                "asset": "data/processed/antecedent_wetness.tif",
                "reason": "18×40 stub placeholder; prefer early-window MRMS antecedent proxy.",
            },
        ],
    }
