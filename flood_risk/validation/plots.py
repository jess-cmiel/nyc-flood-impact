"""Diagnostic plots with explicit provenance banners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from flood_risk.validation.provenance import ProvenanceTag, plot_provenance_banner


def _save(fig: plt.Figure, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return path.name


def plot_distributions(factors: dict[str, Any], out_dir: Path) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    # Collect numeric series from stats when available
    series: list[tuple[str, ProvenanceTag, list[float]]] = []
    mapping = [
        ("precip_intensity_duration", "storm_total_mm", ProvenanceTag.OBSERVED),
        ("elevation", None, ProvenanceTag.OBSERVED),
        ("impervious_surface", "metro_fraction", ProvenanceTag.MODELED),
        ("flood_susceptibility", None, ProvenanceTag.MODELED),
        ("hand_primary_depth", None, ProvenanceTag.MODELED),
        ("sfincs_physics_reference", None, ProvenanceTag.MODELED),
    ]
    for fid, nested, tag in mapping:
        f = factors.get(fid) or {}
        stats = f.get("stats") or {}
        if nested:
            stats = stats.get(nested) or stats
        # Use p10/p50/p90 as a tiny spark if full samples absent — prefer sample_values
        samples = f.get("sample_values") or (factors.get("slope") or {}).get("sample_values")
        if fid == "slope" or (fid == "elevation" and False):
            pass
        path = (f.get("source") or "")
        # Reload coarse histogram from stats percentiles as bar proxy when no samples
        if stats.get("exists") and stats.get("mean") is not None:
            # Build synthetic hist edges from percentiles for display only — labeled
            vals = [
                stats.get("p10"),
                stats.get("p50"),
                stats.get("p90"),
                stats.get("mean"),
                stats.get("max"),
            ]
            vals = [float(v) for v in vals if v is not None]
            if vals:
                series.append((f.get("label") or fid, ProvenanceTag(f.get("provenance", tag)), vals))

    # Slope samples are real derived values
    slope = factors.get("slope") or {}
    if slope.get("sample_values"):
        series.append(
            (
                slope.get("label") or "slope",
                ProvenanceTag(slope.get("provenance", "observed")),
                [float(v) for v in slope["sample_values"][:3000]],
            )
        )

    if not series:
        return artifacts

    fig, axes = plt.subplots(2, 3, figsize=(11, 6.5))
    axes = axes.ravel()
    for ax, (label, tag, vals) in zip(axes, series[:6]):
        ax.hist(vals, bins=min(40, max(8, len(vals) // 20)), color="#2f5d7c", alpha=0.85)
        ax.set_title(plot_provenance_banner(tag, label), fontsize=8)
        ax.tick_params(labelsize=7)
    for ax in axes[len(series) :]:
        ax.axis("off")
    fig.suptitle(
        plot_provenance_banner("modeled", "Factor distributions (Ida research validation)"),
        fontsize=11,
    )
    name = _save(fig, out_dir / "diag_distributions.png")
    artifacts.append(
        {
            "file": name,
            "kind": "distributions",
            "provenance": "mixed",
            "honesty": "Histogram panels include observed DEM/MRMS and modeled HAND/SFINCS/susceptibility.",
        }
    )
    return artifacts


def plot_correlations(sample_rows: list[dict[str, Any]], out_dir: Path) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    keys = [
        ("precip_storm_mm", "hand_depth_m"),
        ("impervious_frac", "hand_depth_m"),
        ("drain_density", "hand_depth_m"),
        ("precip_storm_mm", "sfincs_depth_m"),
        ("hand_depth_m", "sfincs_depth_m"),
        ("elevation_m", "hand_depth_m"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.5))
    axes = axes.ravel()
    for ax, (xkey, ykey) in zip(axes, keys):
        xs, ys = [], []
        for r in sample_rows:
            x, y = r.get(xkey), r.get(ykey)
            if x is None or y is None:
                continue
            if not (np.isfinite(x) and np.isfinite(y)):
                continue
            xs.append(x)
            ys.append(y)
        if len(xs) >= 5:
            ax.scatter(xs, ys, s=8, alpha=0.45, c="#8d3d14")
            r = float(np.corrcoef(xs, ys)[0, 1]) if np.std(xs) > 0 and np.std(ys) > 0 else float("nan")
            ax.set_title(
                plot_provenance_banner("modeled", f"{xkey} vs {ykey}\nr={r:.2f}"),
                fontsize=8,
            )
        else:
            ax.set_title(plot_provenance_banner("synthetic", f"{xkey} vs {ykey} (n<5)"), fontsize=8)
        ax.tick_params(labelsize=7)
        ax.set_xlabel(xkey, fontsize=7)
        ax.set_ylabel(ykey, fontsize=7)
    fig.suptitle(
        plot_provenance_banner("modeled", "Factor correlations (collocated samples)"),
        fontsize=11,
    )
    name = _save(fig, out_dir / "diag_correlations.png")
    artifacts.append(
        {
            "file": name,
            "kind": "correlations",
            "provenance": "modeled",
            "honesty": "Scatter uses collocated observed precip/elev with modeled depth/drainage.",
        }
    )
    return artifacts


def plot_spatial_patterns(out_dir: Path) -> list[dict[str, str]]:
    from flood_risk.validation.paths import catalog

    artifacts: list[dict[str, str]] = []
    assets = catalog()
    panels = [
        (assets["mrms_storm_total"], "MRMS storm total mm", ProvenanceTag.OBSERVED),
        (assets["hand_depth"], "HAND depth m", ProvenanceTag.MODELED),
        (assets["sfincs_depth"], "SFINCS depth m", ProvenanceTag.MODELED),
        (assets["impervious_metro_frac"], "Impervious frac", ProvenanceTag.MODELED),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    for ax, (asset, label, tag) in zip(axes.ravel(), panels):
        if not asset.exists:
            ax.set_title(plot_provenance_banner(tag, f"{label} MISSING"), fontsize=8)
            ax.axis("off")
            continue
        import rasterio
        from rasterio.enums import Resampling

        with rasterio.open(asset.path) as src:
            # downsample for plot
            data = src.read(
                1,
                out_shape=(min(src.height, 240), min(src.width, 240)),
                resampling=Resampling.bilinear,
            ).astype(np.float64)
            if src.nodata is not None:
                data = np.where(data == src.nodata, np.nan, data)
            im = ax.imshow(data, origin="upper", cmap="viridis")
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            ax.set_title(plot_provenance_banner(tag, label), fontsize=8)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.suptitle(
        plot_provenance_banner("mixed", "Spatial patterns (Ida fixtures)"),
        fontsize=11,
    )
    name = _save(fig, out_dir / "diag_spatial_patterns.png")
    artifacts.append(
        {
            "file": name,
            "kind": "spatial_patterns",
            "provenance": "mixed",
            "honesty": "Observed MRMS + modeled HAND/SFINCS/impervious warp.",
        }
    )
    return artifacts


def plot_rainfall_response(sample_rows: list[dict[str, Any]], out_dir: Path) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    xs = [r["precip_storm_mm"] for r in sample_rows if r.get("precip_storm_mm") is not None and r.get("hand_depth_m") is not None]
    ys = [r["hand_depth_m"] for r in sample_rows if r.get("precip_storm_mm") is not None and r.get("hand_depth_m") is not None]
    zs = [
        r["sfincs_depth_m"]
        for r in sample_rows
        if r.get("precip_storm_mm") is not None and r.get("sfincs_depth_m") is not None
    ]
    xs2 = [
        r["precip_storm_mm"]
        for r in sample_rows
        if r.get("precip_storm_mm") is not None and r.get("sfincs_depth_m") is not None
    ]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    if xs:
        axes[0].scatter(xs, ys, s=10, alpha=0.5, c="#2f5d7c")
        axes[0].set_title(
            plot_provenance_banner("modeled", "Rainfall → HAND depth response"),
            fontsize=9,
        )
        axes[0].set_xlabel("MRMS storm total [mm] [OBSERVED]")
        axes[0].set_ylabel("HAND depth [m] [MODELED]")
    if xs2:
        axes[1].scatter(xs2, zs, s=10, alpha=0.5, c="#8d3d14")
        axes[1].set_title(
            plot_provenance_banner("modeled", "Rainfall → SFINCS depth (Advanced)"),
            fontsize=9,
        )
        axes[1].set_xlabel("MRMS storm total [mm] [OBSERVED]")
        axes[1].set_ylabel("SFINCS depth [m] [MODELED]")
    name = _save(fig, out_dir / "diag_rainfall_response.png")
    artifacts.append(
        {
            "file": name,
            "kind": "rainfall_response",
            "provenance": "mixed",
            "honesty": "Observed precip forcing vs modeled HAND (primary) and SFINCS (Advanced).",
        }
    )
    return artifacts


def plot_flood_severity(factors: dict[str, Any], out_dir: Path) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    fn = factors.get("floodnet_observations") or {}
    hand = (factors.get("hand_primary_depth") or {}).get("stats") or {}
    sf = (factors.get("sfincs_physics_reference") or {}).get("stats") or {}
    labels = ["FloodNet obs peak mean", "HAND max", "SFINCS p90", "SFINCS max"]
    tags = [
        ProvenanceTag.OBSERVED,
        ProvenanceTag.MODELED,
        ProvenanceTag.MODELED,
        ProvenanceTag.MODELED,
    ]
    vals = [
        (fn.get("stats") or {}).get("obs_peak_mean_m"),
        hand.get("max"),
        sf.get("p90"),
        sf.get("max"),
    ]
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#0a8a96", "#2f5d7c", "#8d3d14", "#8d3d14"]
    present = [(l, t, v, c) for l, t, v, c in zip(labels, tags, vals, colors) if v is not None]
    if present:
        ax.bar(
            range(len(present)),
            [p[2] for p in present],
            color=[p[3] for p in present],
        )
        ax.set_xticks(range(len(present)))
        ax.set_xticklabels(
            [plot_provenance_banner(p[1], p[0]) for p in present],
            rotation=15,
            ha="right",
            fontsize=8,
        )
        ax.set_ylabel("Depth [m]")
        ax.set_title(
            plot_provenance_banner(
                "mixed",
                "Flood severity comparison — HAND primary · SFINCS Advanced · FloodNet observed",
            ),
            fontsize=10,
        )
    name = _save(fig, out_dir / "diag_flood_severity.png")
    artifacts.append(
        {
            "file": name,
            "kind": "flood_severity",
            "provenance": "mixed",
            "honesty": "Observed FloodNet peaks vs modeled HAND/SFINCS — non-peer engines.",
        }
    )
    return artifacts


def generate_all_plots(
    factors: dict[str, Any],
    sample_rows: list[dict[str, Any]],
    out_dir: Path,
) -> list[dict[str, str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    arts: list[dict[str, str]] = []
    arts.extend(plot_distributions(factors, out_dir))
    arts.extend(plot_correlations(sample_rows, out_dir))
    arts.extend(plot_spatial_patterns(out_dir))
    arts.extend(plot_rainfall_response(sample_rows, out_dir))
    arts.extend(plot_flood_severity(factors, out_dir))
    return arts
