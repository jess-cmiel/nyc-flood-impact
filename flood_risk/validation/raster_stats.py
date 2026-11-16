"""Shared raster sampling and distribution helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject


def domain_stats(
    path: Path,
    *,
    max_samples: int = 80_000,
    valid_min: float | None = None,
    valid_max: float | None = None,
) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    with rasterio.open(path) as src:
        data = src.read(1, masked=True)
        vals = np.ma.compressed(data).astype(np.float64)
        if valid_min is not None:
            vals = vals[vals >= valid_min]
        if valid_max is not None:
            vals = vals[vals <= valid_max]
        if vals.size == 0:
            return {
                "exists": True,
                "path": str(path),
                "crs": str(src.crs),
                "shape": [src.height, src.width],
                "n": 0,
            }
        if vals.size > max_samples:
            rng = np.random.default_rng(42)
            vals = rng.choice(vals, size=max_samples, replace=False)
        return {
            "exists": True,
            "path": str(path),
            "crs": str(src.crs),
            "shape": [src.height, src.width],
            "n": int(vals.size),
            "min": float(np.min(vals)),
            "max": float(np.max(vals)),
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals)),
            "p10": float(np.percentile(vals, 10)),
            "p50": float(np.percentile(vals, 50)),
            "p90": float(np.percentile(vals, 90)),
            "p99": float(np.percentile(vals, 99)),
        }


def sample_points(
    path: Path,
    lons: np.ndarray,
    lats: np.ndarray,
    *,
    nodata_as_nan: bool = True,
) -> np.ndarray:
    out = np.full(len(lons), np.nan, dtype=np.float64)
    if not path.exists() or len(lons) == 0:
        return out
    with rasterio.open(path) as src:
        coords = list(zip(lons.astype(float), lats.astype(float)))
        for i, sample in enumerate(src.sample(coords)):
            v = float(sample[0])
            if src.nodata is not None and np.isclose(v, src.nodata):
                if nodata_as_nan:
                    continue
                v = 0.0
            if not np.isfinite(v):
                continue
            out[i] = v
    return out


def slope_from_dem(
    dem_path: Path,
    *,
    stride: int = 8,
    max_samples: int = 60_000,
) -> dict[str, Any]:
    """Derive slope (degrees) from DEM via local gradient — observed terrain."""
    if not dem_path.exists():
        return {"exists": False, "path": str(dem_path)}
    with rasterio.open(dem_path) as src:
        dem = src.read(1, masked=True)
        # Approximate meters per degree at NYC latitude
        transform = src.transform
        lat0 = (src.bounds.top + src.bounds.bottom) / 2.0
        m_per_deg_lat = 110_540.0
        m_per_deg_lon = 111_320.0 * float(np.cos(np.deg2rad(lat0)))
        dx = abs(transform.a) * m_per_deg_lon
        dy = abs(transform.e) * m_per_deg_lat
        z = np.ma.filled(dem, np.nan).astype(np.float64)
        gy, gx = np.gradient(z, dy, dx)
        slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))
        slope_deg = np.where(np.isfinite(slope_deg), slope_deg, np.nan)
        samp = slope_deg[::stride, ::stride].ravel()
        samp = samp[np.isfinite(samp)]
        if samp.size > max_samples:
            rng = np.random.default_rng(7)
            samp = rng.choice(samp, size=max_samples, replace=False)
        return {
            "exists": True,
            "path": str(dem_path),
            "method": "numpy_gradient_from_dem",
            "n": int(samp.size),
            "min": float(np.min(samp)) if samp.size else None,
            "max": float(np.max(samp)) if samp.size else None,
            "mean": float(np.mean(samp)) if samp.size else None,
            "p50": float(np.percentile(samp, 50)) if samp.size else None,
            "p90": float(np.percentile(samp, 90)) if samp.size else None,
            "p99": float(np.percentile(samp, 99)) if samp.size else None,
            "sample_values": samp[:5000].tolist(),
        }


def align_sample(
    src_path: Path,
    ref_path: Path,
    *,
    max_side: int = 200,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Reproject src onto a coarse version of ref grid; return (ref, src) flat finite pairs."""
    if not src_path.exists() or not ref_path.exists():
        return None
    with rasterio.open(ref_path) as ref, rasterio.open(src_path) as src:
        h = min(ref.height, max_side)
        w = min(ref.width, max_side)
        scale_y = ref.height / h
        scale_x = ref.width / w
        # Read ref downsampled
        ref_data = ref.read(
            1,
            out_shape=(h, w),
            resampling=Resampling.bilinear,
        ).astype(np.float64)
        if ref.nodata is not None:
            ref_data = np.where(ref_data == ref.nodata, np.nan, ref_data)

        dst = np.full((h, w), np.nan, dtype=np.float64)
        # Build destination transform for coarse grid
        transform = ref.transform @ rasterio.Affine.scale(scale_x, scale_y)
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=ref.crs,
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            dst_nodata=np.nan,
        )
        mask = np.isfinite(ref_data) & np.isfinite(dst)
        if not mask.any():
            return None
        return ref_data[mask], dst[mask]


def pearson_corr(a: np.ndarray, b: np.ndarray) -> float | None:
    if a.size < 10:
        return None
    if np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return None
    return float(np.corrcoef(a, b)[0, 1])
