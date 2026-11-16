#!/usr/bin/env python3
"""Build Decision Desk MapLibre 3D hotspot scene index + GeoJSON clips.

Writes figures/product_assets/3d_scene.json and 3d_scenes/*.geojson.
Research HAND/MRMS lead-frame screening — NOT photogrammetry street-truth.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path

from nyc_flash_flood_case_study.config import FIGURES_DIR

ASSETS = FIGURES_DIR / "product_assets"
OUT = ASSETS / "3d_scenes"

FN_PRIORITY = [
    "BK-9th-st-smith-st-0etvg0",
    "BK-carroll-st-4th-av-0ery00",
    "BK-hoyt-st-5th-st-007sk0",
    "Q-russell-st-2-07zt40",
]


def _centroid(geom: dict) -> tuple[float, float] | None:
    coords = geom.get("coordinates")
    pts: list[list[float]] = []

    def flat(c: object) -> None:
        if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
            pts.append(list(c))  # type: ignore[arg-type]
            return
        if isinstance(c, (list, tuple)):
            for x in c:
                flat(x)

    flat(coords)
    if not pts:
        return None
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _buildings_near(
    buildings: dict, lon: float, lat: float, radius_m: float = 900, max_n: int = 90
) -> list[dict]:
    hits: list[tuple[float, dict]] = []
    for f in buildings.get("features") or []:
        c = _centroid(f.get("geometry") or {})
        if not c:
            continue
        d = _haversine_m(lon, lat, c[0], c[1])
        if d <= radius_m:
            hits.append((d, f))
    hits.sort(key=lambda x: x[0])
    return [h[1] for h in hits[:max_n]]


def _synthetic_block(lon: float, lat: float, n: int = 24, spread: float = 0.0012) -> list[dict]:
    feats: list[dict] = []
    cols, rows = 6, 4
    i = 0
    for r in range(rows):
        for c in range(cols):
            if i >= n:
                break
            if abs(c - (cols - 1) / 2) < 0.6 and abs(r - (rows - 1) / 2) < 0.6:
                continue
            dx = (c - (cols - 1) / 2) * (spread / cols * 2.2)
            dy = (r - (rows - 1) / 2) * (spread / rows * 2.2)
            w, h = 0.00018, 0.00014
            x0, y0 = lon + dx - w / 2, lat + dy - h / 2
            ring = [[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h], [x0, y0]]
            height = 8 + ((i * 5) % 22)
            feats.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                    "properties": {
                        "name": f"context-block-{i + 1}",
                        "height_roof": height,
                        "extrusion_m": height,
                        "source": "synthetic_context",
                        "role": "street_view_context_only",
                        "honesty": (
                            "Synthetic footprint for MapLibre extrusion context — "
                            "not surveyed NYC buildings."
                        ),
                    },
                }
            )
            i += 1
    return feats


def _ellipse_ring(
    lon: float, lat: float, half_lon: float, half_lat: float, n: int = 28
) -> list[list[float]]:
    """Closed lon/lat ellipse approximating street-level ponding footprint."""
    ring: list[list[float]] = []
    for i in range(n):
        t = (2.0 * math.pi * i) / n
        # Slight asymmetry so ponding reads as a street gutter, not a perfect disc.
        wobble = 1.0 + 0.06 * math.sin(3.0 * t)
        ring.append(
            [
                lon + half_lon * wobble * math.cos(t),
                lat + half_lat * wobble * math.sin(t),
            ]
        )
    ring.append(ring[0][:])
    return ring


def _depth_polygon_features(lon: float, lat: float) -> list[dict]:
    """Concentric HAND ponding rings for MapLibre fill-extrusion water.

    Core / mid / fringe scale heights in the client from lead-synced HAND cm.
    Schematic street-level screening — not a hydraulic free surface.
    """
    rings = [
        # (half_lon, half_lat, ring_id, height_scale, opacity_bias)
        (0.00028, 0.00020, "core", 1.0, 0.0),
        (0.00048, 0.00034, "mid", 0.62, 0.0),
        (0.00072, 0.00050, "fringe", 0.28, 0.0),
    ]
    feats: list[dict] = []
    for half_lon, half_lat, ring_id, height_scale, _op in rings:
        feats.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [_ellipse_ring(lon, lat, half_lon, half_lat)],
                },
                "properties": {
                    "role": "hand_depth_proxy",
                    "ring": ring_id,
                    "height_scale": height_scale,
                    "units": "cm",
                    "honesty": (
                        "Schematic HAND ponding ring for lead-synced extrusion — "
                        "not a hydraulic water surface / not street-truth."
                    ),
                },
            }
        )
    return feats


def main() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    desk = json.loads((ASSETS / "decision_desk_shortlist.json").read_text())
    fn = json.loads((ASSETS / "floodnet_ida_hotspot_stations.geojson").read_text())
    buildings = json.loads((ASSETS / "building_footprints_sample.geojson").read_text())

    smith = next(a for a in desk["assets"] if a["id"] == "stations:gtfs:F22")
    leads = smith["depth_series_leads_h"]
    hand = smith["depth_series_cm"]
    fn_by_id = {f["properties"]["sensor_id"]: f for f in fn["features"]}

    hotspots: list[dict] = [
        {
            "id": "stations:gtfs:F22",
            "kind": "shortlist_station",
            "name": "Smith-9 Sts",
            "label": "Smith–9",
            "lon": smith["lon"],
            "lat": smith["lat"],
            "band": smith.get("band"),
            "max_depth_cm": smith.get("max_depth_cm"),
            "depth_series_leads_h": leads,
            "depth_series_cm": hand,
            "camera": {
                "center": [smith["lon"], smith["lat"]],
                "zoom": 17.35,
                "pitch": 62,
                "bearing": -28,
            },
            "buildings": "3d_scenes/smith9_buildings.geojson",
            "depth_polygon": "3d_scenes/smith9_depth.geojson",
            "honesty": (
                "HAND cm research screening at station pin — not photogrammetry "
                "street-truth; FloodNet metres are a separate sensor product."
            ),
        }
    ]

    for sid in FN_PRIORITY:
        f = fn_by_id[sid]
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        peak_cm = (p.get("obs_peak_m") or 0) * 100
        series = [round(v, 2) for v in hand] if sid.startswith("BK-") else [
            round(v * 0.15, 2) for v in hand
        ]
        slug = sid.replace("/", "-").lower()
        hotspots.append(
            {
                "id": sid,
                "kind": "floodnet_post",
                "name": p.get("sensor_name") or sid,
                "label": p.get("sensor_name") or sid,
                "lon": lon,
                "lat": lat,
                "borough": p.get("borough"),
                "floodnet_obs_peak_m": p.get("obs_peak_m"),
                "floodnet_obs_peak_cm": round(peak_cm, 1),
                "primary_hand_m": p.get("primary_hand_m"),
                "depth_series_leads_h": leads,
                "depth_series_cm": series,
                "camera": {
                    "center": [lon, lat],
                    "zoom": 17.45,
                    "pitch": 64,
                    "bearing": 18 if lon > -73.9 else -35,
                },
                "buildings": f"3d_scenes/{slug}_buildings.geojson",
                "depth_polygon": f"3d_scenes/{slug}_depth.geojson",
                "honesty": (
                    "FloodNet street peak is sensor metres; 3D extrusion follows "
                    "HAND/MRMS lead-frame cm screening — not the same scale, "
                    "not photogrammetry."
                ),
            }
        )

    for h in hotspots:
        lon, lat = h["lon"], h["lat"]
        near = _buildings_near(buildings, lon, lat)
        if len(near) < 8:
            feats = _synthetic_block(lon, lat)
            source = "synthetic_context"
        else:
            source = "nyc_building_footprints_sample"
            feats = []
            for f in near:
                ff = deepcopy(f)
                props = dict(ff.get("properties") or {})
                try:
                    height = float(props["height_roof"]) if props.get("height_roof") is not None else 12.0
                except (TypeError, ValueError):
                    height = 12.0
                if height < 4:
                    height = 8.0
                props["height_roof"] = height
                props["extrusion_m"] = height
                props["role"] = "street_view_context"
                ff["properties"] = props
                feats.append(ff)

        bpath = ASSETS / h["buildings"]
        bpath.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "properties": {
                        "hotspot_id": h["id"],
                        "source": source,
                        "honesty": (
                            "Building extrusion context only — open NYC sample or "
                            "synthetic blocks; not flood depths / not surveyed street-truth."
                        ),
                        "n_features": len(feats),
                    },
                    "features": feats,
                }
            )
        )
        dpath = ASSETS / h["depth_polygon"]
        dpath.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "properties": {
                        "hotspot_id": h["id"],
                        "role": "hand_depth_proxy_rings",
                        "rings": ["core", "mid", "fringe"],
                        "honesty": (
                            "Concentric schematic ponding rings for fill-extrusion of "
                            "HAND cm by lead — not a hydraulic water surface."
                        ),
                    },
                    "features": _depth_polygon_features(lon, lat),
                }
            )
        )

    scene = {
        "product": "decision_desk_street_view_3d",
        "schema_version": "1.1.0",
        "engine": "maplibre_gl",
        "inspired_by_pattern": "street-level 3D hotspot drill-down from 2D map (research UI pattern)",
        "honesty": (
            "Research HAND/MRMS lead-frame screening in MapLibre 3D. "
            "NOT photogrammetry street-truth. NOT official guidance. "
            "HAND cm ≠ FloodNet sensor metres. SFINCS remains optional Advanced / non-peer."
        ),
        "official_nws": False,
        "decision_grade": False,
        "photogrammetry": False,
        "basemap": {
            "style": "https://tiles.openfreemap.org/styles/liberty",
            "terrain_enabled": False,
            "terrain_source": None,
            "terrain_exaggeration": 1.0,
            "light": {
                "anchor": "viewport",
                "color": "#f2f0ea",
                "intensity": 0.42,
                "position": [1.15, 210, 35],
            },
            "note": (
                "OpenFreeMap liberty streets + product GeoJSON building/depth extrusions. "
                "demotiles is a countries demo (not streets) and its terrain 404s over NYC. "
                "No sky layer (MapLibre 3.6.2); atmosphere via light + fog-tint overlays."
            ),
        },
        "risk_ramp_cm": {
            "0": "#dbeafe",
            "3": "#9ecae1",
            "8": "#4292c6",
            "15": "#08306b",
            "note": "Matches Decision Desk HAND cm risk ramp (research screening).",
        },
        "timeline": {
            "source": "ida_mrms_hand_cumulative_leads",
            "leads_h": leads,
            "units": "cm",
            "band_cm": [3, 8, 15],
        },
        "default_hotspot_id": "stations:gtfs:F22",
        "hotspots": hotspots,
        "open_from": [
            "shortlist click (Smith–9)",
            "FloodNet Ida post click / list select",
            "inspector Street view 3D button",
        ],
    }
    out = ASSETS / "3d_scene.json"
    out.write_text(json.dumps(scene, indent=2) + "\n")
    print(f"Wrote {out} ({len(hotspots)} hotspots)")
    return out


if __name__ == "__main__":
    main()
