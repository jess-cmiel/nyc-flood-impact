"""Factor-level validators: precip, antecedent, terrain, impervious, drainage, susceptibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from flood_risk.validation.paths import ASSETS, PROCESSED, catalog
from flood_risk.validation.provenance import ProvenanceTag, tag_block
from flood_risk.validation.raster_stats import (
    align_sample,
    domain_stats,
    pearson_corr,
    sample_points,
    slope_from_dem,
)


def _factor(
    *,
    fid: str,
    label: str,
    provenance: ProvenanceTag,
    source: str,
    honesty: str,
    status: str,
    stats: dict[str, Any],
    assumptions: list[str] | None = None,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = {
        "id": fid,
        "label": label,
        "status": status,
        **tag_block(provenance, source=source, honesty=honesty, assumptions=assumptions),
        "stats": stats,
    }
    if extras:
        out.update(extras)
    return out


def validate_precip_intensity_duration() -> dict[str, Any]:
    assets = catalog()
    storm = assets["mrms_storm_total"]
    hourly_dir = assets["mrms_metro_1h_dir"].path
    stats = domain_stats(storm.path, valid_min=0.0)
    peak_1h = None
    duration_hours = 0
    hourly_maxima: list[float] = []
    if hourly_dir.exists():
        frames = sorted(hourly_dir.glob("mrms_qpe_metro_1h_lead_*h.tif"))
        duration_hours = len(frames)
        for fp in frames:
            st = domain_stats(fp, max_samples=40_000, valid_min=0.0)
            if st.get("max") is not None:
                hourly_maxima.append(float(st["max"]))
        if hourly_maxima:
            peak_1h = float(np.max(hourly_maxima))
    status = "ok" if stats.get("exists") else "missing"
    return _factor(
        fid="precip_intensity_duration",
        label="Precipitation intensity / duration (MRMS QPE)",
        provenance=ProvenanceTag.OBSERVED,
        source=str(storm.path),
        honesty=(
            "Observed MRMS Multi-Sensor QPE — research visualization / forcing. "
            "NOT NEXRAD reflectivity tiles; NOT an official NWS product."
        ),
        status=status,
        stats={
            "storm_total_mm": stats,
            "n_hourly_frames": duration_hours,
            "peak_1h_mm": peak_1h,
            "hourly_max_mm_series_p50": float(np.median(hourly_maxima)) if hourly_maxima else None,
            "hourly_max_mm_series_p90": float(np.percentile(hourly_maxima, 90)) if hourly_maxima else None,
        },
        assumptions=["Ida window uses metro hourly MRMS 0–36 h when available."],
        extras={
            "earth2_scenario": {
                **tag_block(
                    ProvenanceTag.MODELED,
                    source=str(assets["earth2_storm_total"].path),
                    honesty="Earth2 AI storm total is a modeled scenario track — separate from hydro calc modules.",
                ),
                "stats": domain_stats(assets["earth2_storm_total"].path, valid_min=0.0),
            }
        },
    )


def validate_antecedent_rainfall() -> dict[str, Any]:
    """Prefer early-window MRMS sum (observed); fall back to labeled synthetic stub."""
    assets = catalog()
    hourly_dir = assets["mrms_metro_1h_dir"].path
    early_leads = list(range(0, 6))  # first 6 h as pre-peak wetness proxy
    if hourly_dir.exists():
        frames = []
        for h in early_leads:
            fp = hourly_dir / f"mrms_qpe_metro_1h_lead_{h:02d}h.tif"
            if fp.exists():
                frames.append(fp)
        if frames:
            # Accumulate on first frame grid
            with rasterio.open(frames[0]) as src0:
                acc = np.zeros((src0.height, src0.width), dtype=np.float64)
                profile = src0.profile
                nodata = src0.nodata
                for fp in frames:
                    with rasterio.open(fp) as src:
                        band = src.read(1).astype(np.float64)
                        if src.nodata is not None:
                            band = np.where(band == src.nodata, 0.0, band)
                        acc += np.where(np.isfinite(band), band, 0.0)
                finite = acc[np.isfinite(acc)]
                stats = {
                    "exists": True,
                    "method": "sum_mrms_1h_leads_0_to_5",
                    "n_frames": len(frames),
                    "n": int(finite.size),
                    "min": float(np.min(finite)) if finite.size else None,
                    "max": float(np.max(finite)) if finite.size else None,
                    "mean": float(np.mean(finite)) if finite.size else None,
                    "p50": float(np.percentile(finite, 50)) if finite.size else None,
                    "p90": float(np.percentile(finite, 90)) if finite.size else None,
                    "shape": list(acc.shape),
                    "crs": str(profile.get("crs")),
                    "nodata_ref": nodata,
                }
            return _factor(
                fid="antecedent_rainfall",
                label="Antecedent rainfall (early-window MRMS sum)",
                provenance=ProvenanceTag.OBSERVED,
                source=str(hourly_dir),
                honesty=(
                    "Observed early-window MRMS QPE sum (leads 0–5 h) as antecedent wetness proxy. "
                    "Not soil-moisture assimilation; research only."
                ),
                status="ok",
                stats=stats,
                assumptions=[
                    "Antecedent ≈ first 6 hourly MRMS accumulations in the Ida product clock.",
                    "Does not use the synthetic data/processed/antecedent_wetness.tif stub.",
                ],
                extras={
                    "synthetic_stub_avoided": tag_block(
                        ProvenanceTag.SYNTHETIC,
                        source=str(assets["antecedent_stub"].path),
                        honesty=assets["antecedent_stub"].note,
                    )
                },
            )

    stub = assets["antecedent_stub"]
    return _factor(
        fid="antecedent_rainfall",
        label="Antecedent rainfall (SYNTHETIC stub fallback)",
        provenance=ProvenanceTag.SYNTHETIC,
        source=str(stub.path),
        honesty="SYNTHETIC prototype stub — hourly MRMS missing; do not treat as observations.",
        status="synthetic_fallback" if stub.exists else "missing",
        stats=domain_stats(stub.path),
        assumptions=["Stub only; regenerate with MRMS hourly when available."],
    )


def validate_elevation() -> dict[str, Any]:
    assets = catalog()
    dem = assets["dem_metro"]
    stats = domain_stats(dem.path, max_samples=80_000)
    return _factor(
        fid="elevation",
        label="Elevation (USGS 3DEP metro DEM)",
        provenance=ProvenanceTag.OBSERVED,
        source=str(dem.path),
        honesty="Observed USGS 3DEP elevation — terrain input for HAND / screening.",
        status="ok" if stats.get("exists") else "missing",
        stats=stats,
    )


def validate_slope() -> dict[str, Any]:
    assets = catalog()
    dem = assets["dem_metro"]
    derived = slope_from_dem(dem.path)
    stub_stats = domain_stats(assets["slope_stub"].path)
    return _factor(
        fid="slope",
        label="Slope (degrees from USGS DEM gradient)",
        provenance=ProvenanceTag.OBSERVED,
        source=str(dem.path),
        honesty=(
            "Observed terrain slope derived from USGS DEM gradient (degrees). "
            "Legacy data/processed/slope.tif is a SYNTHETIC stub with unrealistic maxima — not used here."
        ),
        status="ok" if derived.get("exists") else "missing",
        stats={k: v for k, v in derived.items() if k != "sample_values"},
        assumptions=["Slope from local finite differences; not a lidar bare-earth product."],
        extras={
            "synthetic_stub": {
                **tag_block(
                    ProvenanceTag.SYNTHETIC,
                    source=str(assets["slope_stub"].path),
                    honesty=assets["slope_stub"].note,
                ),
                "stats": stub_stats,
            },
            "sample_values": derived.get("sample_values", [])[:2000],
        },
    )


def validate_impervious() -> dict[str, Any]:
    assets = catalog()
    nlcd = assets["impervious_nlcd"]
    metro = assets["impervious_metro_frac"]
    return _factor(
        fid="impervious_surface",
        label="Impervious surface (NLCD 2021)",
        provenance=ProvenanceTag.OBSERVED,
        source=str(nlcd.path),
        honesty="Observed NLCD 2021 percent impervious; metro fraction is a modeled warp of NLCD.",
        status="ok" if nlcd.exists else "missing",
        stats={
            "nlcd_percent": domain_stats(nlcd.path, valid_min=0.0, valid_max=100.0),
            "metro_fraction": {
                **tag_block(
                    ProvenanceTag.MODELED,
                    source=str(metro.path),
                    honesty="NLCD warped to metro DEM grid as fraction [0,1].",
                ),
                **domain_stats(metro.path, valid_min=0.0, valid_max=1.0),
            },
        },
    )


def validate_drainage_blockage() -> dict[str, Any]:
    assets = catalog()
    dens = assets["drain_density"]
    cap = assets["drainage_capacity"]
    nodes = assets["drainage_nodes"]
    meta_path = ASSETS / "drainage_capacity_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    return _factor(
        fid="drainage_blockage_indicators",
        label="Drainage / blockage indicators (open proxy)",
        provenance=ProvenanceTag.MODELED,
        source=str(cap.path),
        honesty=(
            "Modeled research drainage-capacity proxy from open drain density — "
            "NOT SWMM, NOT DEP sewer capacity, NOT blockage sensor network."
        ),
        status="ok" if dens.exists and cap.exists else "partial",
        stats={
            "drain_density_norm": domain_stats(dens.path, valid_min=0.0, valid_max=1.0),
            "drainage_capacity_mm_hr": domain_stats(cap.path, valid_min=0.0),
            "capacity_meta_keys": sorted(meta.keys())[:20],
            "demo_nodes": {
                **tag_block(
                    ProvenanceTag.SYNTHETIC,
                    source=str(nodes.path),
                    honesty=nodes.note,
                ),
                "exists": nodes.exists,
            },
        },
        assumptions=[
            "Low drain density → higher blockage / capacity-deficit proxy.",
            "No fake SWMM continuous simulation.",
        ],
    )


def validate_susceptibility() -> dict[str, Any]:
    assets = catalog()
    storm = assets["susceptibility_storm"]
    stub = assets["susceptibility_stub"]
    if storm.exists:
        path, prov, honesty = storm.path, ProvenanceTag.MODELED, storm.note
        status = "ok"
    else:
        path, prov, honesty = stub.path, ProvenanceTag.SYNTHETIC, stub.note
        status = "synthetic_fallback" if stub.exists else "missing"
    factors_meta = PROCESSED / "susceptibility_factors" / "factors_meta.json"
    meta = json.loads(factors_meta.read_text()) if factors_meta.exists() else {}
    return _factor(
        fid="flood_susceptibility",
        label="Flood susceptibility screening index",
        provenance=prov,
        source=str(path),
        honesty=honesty + " Screening only — not inundation depth or calibrated probability.",
        status=status,
        stats=domain_stats(path, valid_min=0.0, valid_max=1.05),
        assumptions=[meta.get("formula")] if meta.get("formula") else None,
        extras={"factors_meta_formula": meta.get("formula"), "weights": meta.get("weights")},
    )


def validate_hand_primary() -> dict[str, Any]:
    assets = catalog()
    hand = assets["hand_depth"]
    return _factor(
        fid="hand_primary_depth",
        label="HAND bathtub depth (product primary)",
        provenance=ProvenanceTag.MODELED,
        source=str(hand.path),
        honesty=(
            "Modeled pysheds HAND × MRMS excess after drainage-capacity proxy — "
            "product primary depth. NOT rescaled to FloodNet; cm-scale screening."
        ),
        status="ok" if hand.exists else "missing",
        stats=domain_stats(hand.path, valid_min=0.0),
    )


def validate_sfincs_reference() -> dict[str, Any]:
    assets = catalog()
    sf = assets["sfincs_depth"]
    overlap_path = assets["sfincs_hand_overlap"].path
    overlap = json.loads(overlap_path.read_text()) if overlap_path.exists() else {}
    pair = align_sample(sf.path, assets["hand_depth"].path, max_side=160)
    corr = pearson_corr(pair[0], pair[1]) if pair else None
    return _factor(
        fid="sfincs_physics_reference",
        label="SFINCS depth (Advanced physics reference)",
        provenance=ProvenanceTag.MODELED,
        source=str(sf.path),
        honesty=(
            "SFINCS Advanced research hydro — physics-based reference only. "
            "NOT peer-authoritative with HAND; HAND remains product primary."
        ),
        status="ok" if sf.exists else "missing",
        stats=domain_stats(sf.path, valid_min=0.0),
        assumptions=[
            "Non-peer comparison with HAND; magnitude disagreement expected.",
            "No SWMM; Docker SFINCS run when available.",
        ],
        extras={
            "role": "advanced_research_hydro_non_peer",
            "hand_sfincs_pearson_r": corr,
            "overlap_summary": {
                "wet_dry": overlap.get("wet_dry"),
                "magnitude_on_both_wet": overlap.get("magnitude_on_both_wet"),
                "honesty": overlap.get("honesty")
                or overlap.get("note")
                or "Non-peer HAND vs SFINCS.",
            },
        },
    )


def validate_floodnet_obs() -> dict[str, Any]:
    assets = catalog()
    geo_path = assets["floodnet_stations"].path
    card_path = assets["floodnet_validation"].path
    card = json.loads(card_path.read_text()) if card_path.exists() else {}
    n_stations = 0
    if geo_path.exists():
        geo = json.loads(geo_path.read_text())
        n_stations = len(geo.get("features") or [])
    summary = card.get("summary") or {}
    return _factor(
        fid="floodnet_observations",
        label="FloodNet street-sensor peaks (Ida)",
        provenance=ProvenanceTag.OBSERVED,
        source=str(geo_path),
        honesty=(
            "Observed FloodNet street flooding peaks — sparse 2021 network. "
            "Primary comparison target for magnitude honesty vs HAND."
        ),
        status="ok" if n_stations or summary else "missing",
        stats={
            "n_stations_geojson": n_stations,
            "peak_rmse_m": summary.get("peak_rmse_m"),
            "peak_bias_mean_m": (summary.get("peak_bias_m") or {}).get("mean"),
            "obs_peak_mean_m": summary.get("obs_peak_mean_m"),
            "obs_peak_max_m": summary.get("obs_peak_max_m"),
            "model_peak_mean_m": summary.get("model_peak_mean_m"),
            "n_model_dry_at_sensor": summary.get("n_model_dry_at_sensor"),
        },
        extras={"card": "floodnet_validation.json"},
    )


def precip_depth_correlation() -> float | None:
    assets = catalog()
    pair = align_sample(assets["mrms_storm_total"].path, assets["hand_depth"].path, max_side=160)
    if not pair:
        return None
    return pearson_corr(pair[0], pair[1])


def build_sample_points_table(max_floodnet: int = 50, grid_n: int = 40) -> list[dict[str, Any]]:
    """Collocate factors at FloodNet stations + coarse grid for GeoJSON export."""
    assets = catalog()
    rows: list[dict[str, Any]] = []

    # FloodNet observed points
    if assets["floodnet_stations"].exists:
        geo = json.loads(assets["floodnet_stations"].path.read_text())
        for feat in (geo.get("features") or [])[:max_floodnet]:
            geom = feat.get("geometry") or {}
            props = feat.get("properties") or {}
            if geom.get("type") != "Point":
                continue
            lon, lat = geom["coordinates"][:2]
            rows.append(
                {
                    "lon": float(lon),
                    "lat": float(lat),
                    "sample_kind": "floodnet_station",
                    "sample_provenance": ProvenanceTag.OBSERVED.value,
                    "sensor_id": props.get("sensor_id") or props.get("sensor_name"),
                    "obs_peak_m": props.get("obs_peak_m"),
                }
            )

    # Coarse grid over HAND domain
    hand = assets["hand_depth"].path
    if hand.exists():
        with rasterio.open(hand) as src:
            xs = np.linspace(src.bounds.left + 0.01, src.bounds.right - 0.01, grid_n)
            ys = np.linspace(src.bounds.bottom + 0.01, src.bounds.top - 0.01, grid_n)
            xx, yy = np.meshgrid(xs, ys)
            # subsample
            lons = xx.ravel()[:: max(1, (grid_n * grid_n) // 200)]
            lats = yy.ravel()[:: max(1, (grid_n * grid_n) // 200)]
            for lon, lat in zip(lons, lats):
                rows.append(
                    {
                        "lon": float(lon),
                        "lat": float(lat),
                        "sample_kind": "grid",
                        "sample_provenance": ProvenanceTag.MODELED.value,
                    }
                )

    if not rows:
        return rows

    lons = np.array([r["lon"] for r in rows])
    lats = np.array([r["lat"] for r in rows])

    def add(name: str, path: Path, provenance: str) -> None:
        vals = sample_points(path, lons, lats)
        for r, v in zip(rows, vals):
            r[name] = None if not np.isfinite(v) else float(v)
            r[f"{name}_provenance"] = provenance

    add("precip_storm_mm", assets["mrms_storm_total"].path, ProvenanceTag.OBSERVED.value)
    add("elevation_m", assets["dem_metro"].path, ProvenanceTag.OBSERVED.value)
    add("impervious_frac", assets["impervious_metro_frac"].path, ProvenanceTag.MODELED.value)
    add("drain_density", assets["drain_density"].path, ProvenanceTag.MODELED.value)
    add("hand_depth_m", assets["hand_depth"].path, ProvenanceTag.MODELED.value)
    add("sfincs_depth_m", assets["sfincs_depth"].path, ProvenanceTag.MODELED.value)
    if assets["susceptibility_storm"].exists:
        add("susceptibility", assets["susceptibility_storm"].path, ProvenanceTag.MODELED.value)
    return rows
