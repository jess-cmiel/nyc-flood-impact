#!/usr/bin/env python3
"""Build Decision Desk MapLibre 3D hotspot scene index + GeoJSON clips.

Street-level flood polygons = LION wet-edge road buffers − building footprints,
extruded by HAND lead cm in the client. Falls back to schematic rings when
roads/footprints are sparse (e.g. Queens sample).

Writes figures/product_assets/3d_scene.json and 3d_scenes/*.geojson.
Research HAND/MRMS lead-frame screening — NOT photogrammetry street-truth.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path

from shapely.geometry import LineString, MultiLineString, Point, mapping, shape
from shapely.ops import unary_union

from nyc_flash_flood_case_study.config import FIGURES_DIR

ASSETS = FIGURES_DIR / "product_assets"
OUT = ASSETS / "3d_scenes"

FN_PRIORITY = [
    "BK-9th-st-smith-st-0etvg0",
    "BK-carroll-st-4th-av-0ery00",
    "BK-hoyt-st-5th-st-007sk0",
    "Q-russell-st-2-07zt40",
]

# Local street flood radii (metres).
ROAD_SEARCH_M = 520.0
BUILDING_SEARCH_M = 900.0
CLIP_RADIUS_M = 230.0
# Half-widths for nested roadway bands (centre → curb).
BAND_HALF_WIDTH_M = {
    "core": 4.5,  # street centre / deepest gutter proxy
    "mid": 9.0,  # travel lane
    "fringe": 14.0,  # curb / gutter fringe
}
HEIGHT_SCALE = {"core": 1.0, "mid": 0.65, "fringe": 0.32}
BAND_LABEL = {
    "core": "street_center",
    "mid": "street_lane",
    "fringe": "curb",
}


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


def _local_scale(lat: float) -> tuple[float, float]:
    """Metres per degree lon/lat at hotspot latitude (local equirectangular)."""
    mx = 111320.0 * math.cos(math.radians(lat))
    my = 110540.0
    return mx, my


def _to_local(geom, lon0: float, lat0: float):
    mx, my = _local_scale(lat0)

    def _proj(x: float, y: float, z: float | None = None):
        return ((x - lon0) * mx, (y - lat0) * my)

    return transform_xy(geom, _proj)


def _to_wgs(geom, lon0: float, lat0: float):
    mx, my = _local_scale(lat0)

    def _proj(x: float, y: float, z: float | None = None):
        return (x / mx + lon0, y / my + lat0)

    return transform_xy(geom, _proj)


def transform_xy(geom, func):
    """Apply 2D coordinate transform without shapely.ops.transform deprecation."""
    from shapely.ops import transform as _transform

    return _transform(lambda x, y, z=None: func(x, y, z), geom)


def _buildings_near(
    buildings: dict, lon: float, lat: float, radius_m: float = BUILDING_SEARCH_M, max_n: int = 90
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
        wobble = 1.0 + 0.06 * math.sin(3.0 * t)
        ring.append(
            [
                lon + half_lon * wobble * math.cos(t),
                lat + half_lat * wobble * math.sin(t),
            ]
        )
    ring.append(ring[0][:])
    return ring


def _ring_fallback_features(lon: float, lat: float) -> list[dict]:
    """Concentric HAND ponding rings when street buffers cannot be carved."""
    rings = [
        (0.00028, 0.00020, "core", 1.0),
        (0.00048, 0.00034, "mid", 0.62),
        (0.00072, 0.00050, "fringe", 0.28),
    ]
    feats: list[dict] = []
    for half_lon, half_lat, ring_id, height_scale in rings:
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
                    "band": BAND_LABEL[ring_id],
                    "height_scale": height_scale,
                    "units": "cm",
                    "model": "concentric_fallback",
                    "honesty": (
                        "Schematic HAND ponding ring fallback — not a hydraulic "
                        "water surface / not street-truth."
                    ),
                },
            }
        )
    return feats


def _synthetic_street_axes(lon: float, lat: float, half_len_m: float = 180.0) -> MultiLineString:
    """Local E–W / N–S axes through the hotspot when LION edges are missing."""
    mx, my = _local_scale(lat)
    dx = half_len_m / mx
    dy = half_len_m / my
    return MultiLineString(
        [
            LineString([(lon - dx, lat), (lon + dx, lat)]),
            LineString([(lon, lat - dy), (lon, lat + dy)]),
        ]
    )


def _roads_near(wet_edges: dict, lon: float, lat: float, radius_m: float = ROAD_SEARCH_M):
    pt = Point(lon, lat)
    mx, my = _local_scale(lat)
    # Cheap degree threshold then precise metre filter.
    deg = radius_m / max(my, 1.0)
    hits = []
    for f in wet_edges.get("features") or []:
        g = shape(f.get("geometry") or {})
        if g.is_empty:
            continue
        if g.distance(pt) > deg:
            continue
        # Approximate metres via local scale on bounding distance.
        d_m = g.distance(pt) * ((mx + my) / 2.0)
        if d_m <= radius_m:
            hits.append((d_m, g, f))
    hits.sort(key=lambda x: x[0])
    return hits


def _geom_to_features(
    geom,
    *,
    ring: str,
    road_source: str,
    n_segments: int,
) -> list[dict]:
    if geom is None or geom.is_empty:
        return []
    parts = []
    if geom.geom_type == "Polygon":
        parts = [geom]
    elif geom.geom_type == "MultiPolygon":
        parts = [p for p in geom.geoms if not p.is_empty and p.area > 0]
    else:
        return []
    out: list[dict] = []
    for poly in parts:
        if poly.area <= 0:
            continue
        out.append(
            {
                "type": "Feature",
                "geometry": mapping(poly),
                "properties": {
                    "role": "hand_street_flood",
                    "ring": ring,
                    "band": BAND_LABEL[ring],
                    "height_scale": HEIGHT_SCALE[ring],
                    "units": "cm",
                    "model": "road_buffer_minus_buildings",
                    "road_source": road_source,
                    "n_road_segments": n_segments,
                    "honesty": (
                        "Curb/street flood proxy: LION (or synthetic) road buffer "
                        "minus building footprints × HAND lead cm — research "
                        "screening, not a hydraulic free surface / not street-truth."
                    ),
                },
            }
        )
    return out


def _street_flood_features(
    lon: float,
    lat: float,
    building_feats: list[dict],
    wet_edges: dict,
) -> tuple[list[dict], list[dict], dict]:
    """Carve curb/street flood polygons from road buffers − footprints.

    Returns (depth_features, road_centerline_features, meta).
    """
    road_hits = _roads_near(wet_edges, lon, lat)
    clip_m = Point(0.0, 0.0).buffer(CLIP_RADIUS_M)
    road_union = None
    road_source = "synthetic_street_axes"
    n_segments = 2

    if road_hits:
        candidate = unary_union([g for _, g, _ in road_hits]) if len(road_hits) > 1 else road_hits[0][1]
        cand_m = _to_local(candidate, lon, lat)
        # Prefer LION only when the roadway actually enters the street-view clip.
        if not cand_m.intersection(clip_m).is_empty:
            road_union = candidate
            road_source = "lion_wet_edges"
            n_segments = len(road_hits)

    if road_union is None:
        road_union = _synthetic_street_axes(lon, lat)
        road_source = "synthetic_street_axes"
        n_segments = 2

    roads_m = _to_local(road_union, lon, lat)

    # Building occlusion — keep water in the roadway, not through footprints.
    b_geoms = []
    for f in building_feats:
        try:
            g = shape(f.get("geometry") or {})
        except Exception:
            continue
        if g.is_empty:
            continue
        b_geoms.append(g)
    if b_geoms:
        buildings_m = _to_local(unary_union(b_geoms), lon, lat).buffer(1.2)
    else:
        buildings_m = None

    depth_feats: list[dict] = []
    for ring, half_w in BAND_HALF_WIDTH_M.items():
        band_m = roads_m.buffer(half_w, cap_style=2, join_style=2)
        flooded_m = band_m.intersection(clip_m)
        if buildings_m is not None and not buildings_m.is_empty:
            flooded_m = flooded_m.difference(buildings_m)
        flooded = _to_wgs(flooded_m, lon, lat)
        depth_feats.extend(
            _geom_to_features(
                flooded,
                ring=ring,
                road_source=road_source,
                n_segments=n_segments,
            )
        )

    meta = {
        "model": "road_buffer_minus_buildings",
        "road_source": road_source,
        "n_road_segments": n_segments,
        "n_buildings_subtracted": len(b_geoms),
        "clip_radius_m": CLIP_RADIUS_M,
        "band_half_width_m": BAND_HALF_WIDTH_M,
    }

    # If carving failed (empty), fall back to concentric rings.
    if not depth_feats:
        return _ring_fallback_features(lon, lat), [], {
            **meta,
            "model": "concentric_fallback",
            "reason": "empty_after_difference",
        }

    # Road centreline for MapLibre line layer (visual street cue).
    roads_clip_m = roads_m.intersection(clip_m)
    roads_ll = _to_wgs(roads_clip_m, lon, lat)
    road_feats: list[dict] = []
    line_parts = []
    if roads_ll.geom_type == "LineString":
        line_parts = [roads_ll]
    elif roads_ll.geom_type == "MultiLineString":
        line_parts = list(roads_ll.geoms)
    elif roads_ll.geom_type == "GeometryCollection":
        line_parts = [g for g in roads_ll.geoms if g.geom_type in ("LineString", "MultiLineString")]
        expanded = []
        for g in line_parts:
            if g.geom_type == "MultiLineString":
                expanded.extend(list(g.geoms))
            else:
                expanded.append(g)
        line_parts = expanded
    for i, line in enumerate(line_parts):
        if line.is_empty:
            continue
        road_feats.append(
            {
                "type": "Feature",
                "geometry": mapping(line),
                "properties": {
                    "role": "street_centerline",
                    "road_source": road_source,
                    "seg": i,
                    "honesty": (
                        "Research roadway centreline cue for curb flood viz — "
                        "not official DOT geometry."
                    ),
                },
            }
        )

    return depth_feats, road_feats, meta


def main() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    desk = json.loads((ASSETS / "decision_desk_shortlist.json").read_text())
    fn = json.loads((ASSETS / "floodnet_ida_hotspot_stations.geojson").read_text())
    buildings = json.loads((ASSETS / "building_footprints_sample.geojson").read_text())
    wet_path = ASSETS / "corridor_wet_edges.geojson"
    wet_edges = json.loads(wet_path.read_text()) if wet_path.exists() else {"type": "FeatureCollection", "features": []}

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
            "roads": "3d_scenes/smith9_roads.geojson",
            "honesty": (
                "HAND cm research screening along curb/street buffers − building "
                "footprints — not photogrammetry street-truth; FloodNet metres "
                "are a separate sensor product."
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
                "roads": f"3d_scenes/{slug}_roads.geojson",
                "honesty": (
                    "FloodNet street peak is sensor metres; 3D curb/street water "
                    "follows HAND/MRMS lead-frame cm along road buffers − "
                    "footprints — not the same scale, not photogrammetry."
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

        depth_feats, road_feats, flood_meta = _street_flood_features(
            lon, lat, feats, wet_edges
        )
        h["flood_model"] = flood_meta

        dpath = ASSETS / h["depth_polygon"]
        dpath.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "properties": {
                        "hotspot_id": h["id"],
                        "role": "hand_street_flood",
                        "rings": ["core", "mid", "fringe"],
                        "bands": ["street_center", "street_lane", "curb"],
                        **flood_meta,
                        "honesty": (
                            "Curb/street HAND flood proxy for fill-extrusion by lead — "
                            "road buffer minus footprints; not a hydraulic water surface."
                        ),
                    },
                    "features": depth_feats,
                }
            )
        )

        rpath = ASSETS / h["roads"]
        rpath.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "properties": {
                        "hotspot_id": h["id"],
                        "role": "street_centerlines",
                        "road_source": flood_meta.get("road_source"),
                        "n_features": len(road_feats),
                        "honesty": (
                            "Research roadway centreline cue — LION wet edges or "
                            "synthetic axes; not official DOT."
                        ),
                    },
                    "features": road_feats,
                }
            )
        )

    scene = {
        "product": "decision_desk_street_view_3d",
        "schema_version": "1.2.0",
        "engine": "maplibre_gl",
        "inspired_by_pattern": "street-level 3D hotspot drill-down from 2D map (research UI pattern)",
        "flood_model": {
            "kind": "hand_lead_x_road_buffer_minus_buildings",
            "description": (
                "At each hotspot, buffer nearby LION wet-edge (or synthetic) road "
                "segments into curb/lane/center bands, subtract building footprints, "
                "and extrude by Decision Desk HAND lead cm. Not a 2D SWE free surface."
            ),
            "inputs": [
                "corridor_wet_edges.geojson (LION × HAND)",
                "building_footprints_sample.geojson (or synthetic blocks)",
                "decision_desk HAND depth_series_cm by lead",
            ],
            "honesty": (
                "Research curb/street screening geometry — NOT photogrammetry, "
                "NOT hydraulic routing, NOT NWS."
            ),
        },
        "honesty": (
            "Research HAND/MRMS lead-frame screening in MapLibre 3D curb/street "
            "buffers. NOT photogrammetry street-truth. NOT official guidance. "
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
            "2D|3D toggle → 3D (flyTo selected hotspot)",
        ],
    }
    out = ASSETS / "3d_scene.json"
    out.write_text(json.dumps(scene, indent=2) + "\n")
    print(f"Wrote {out} ({len(hotspots)} hotspots)")
    for h in hotspots:
        fm = h.get("flood_model") or {}
        print(
            f"  {h['id']}: model={fm.get('model')} roads={fm.get('n_road_segments')} "
            f"bldgs={fm.get('n_buildings_subtracted')} src={fm.get('road_source')}"
        )
    return out


if __name__ == "__main__":
    main()
