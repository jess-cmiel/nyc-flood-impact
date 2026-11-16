#!/usr/bin/env python3
"""Build citywide curb/street flood GeoJSON for Decision Desk 2D.

Buffers LION × HAND wet edges into core/mid/fringe bands so street flooding
appears at all modeled wet locations (not only a few 3D hotspot clips).

Research screening geometry — NOT hydraulic free surface / NOT NWS.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from shapely.geometry import LineString, MultiLineString, mapping, shape
from shapely.ops import linemerge, unary_union

from nyc_flash_flood_case_study.config import FIGURES_DIR

ASSETS = FIGURES_DIR / "product_assets"
BAND_HALF_WIDTH_M = {"core": 3.8, "mid": 7.5, "fringe": 12.0}
HEIGHT_SCALE = {"core": 1.0, "mid": 0.62, "fringe": 0.3}


def _local_scale(lat: float) -> tuple[float, float]:
    mx = 111320.0 * math.cos(math.radians(lat))
    my = 110540.0
    return mx, my


def _buffer_line_ll(geom, half_w_m: float, lat0: float):
    mx, my = _local_scale(lat0)
    # Equirectangular local metres → buffer → back to lon/lat.
    def to_m(x, y, z=None):
        return (x * mx, y * my)

    def to_ll(x, y, z=None):
        return (x / mx, y / my)

    from shapely.ops import transform

    local = transform(to_m, geom)
    buf = local.buffer(half_w_m, cap_style=2, join_style=2)
    return transform(to_ll, buf)


def _parts(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return [g for g in geom.geoms if not g.is_empty]
    return []


def main() -> Path:
    wet = json.loads((ASSETS / "corridor_wet_edges.geojson").read_text())
    feats_out: list[dict] = []
    line_out: list[dict] = []
    n_synth = 0
    n_real = 0

    # Group by coarse depth bins so we can dissolve nearby segments cheaply.
    # Process segment-wise (3773) — keep polygons lightweight by simplifying.
    for f in wet.get("features") or []:
        props = dict(f.get("properties") or {})
        depth_cm = float(props.get("depth_cm") or 0.0)
        if depth_cm < 0.4:
            continue
        try:
            g = shape(f.get("geometry") or {})
        except Exception:
            continue
        if g.is_empty:
            continue
        if g.geom_type == "MultiLineString":
            g = linemerge(g) if not g.is_empty else g
        if g.geom_type not in ("LineString", "MultiLineString"):
            continue

        # Representative latitude for local scale.
        c = g.centroid
        lat0 = float(c.y)
        road_source = "lion_wet_edges"
        n_real += 1

        # Centrelines for line-style rendering (always).
        line_out.append(
            {
                "type": "Feature",
                "geometry": mapping(g.simplify(0.00002, preserve_topology=True)),
                "properties": {
                    "role": "street_flood_centerline",
                    "depth_cm": round(depth_cm, 2),
                    "name": props.get("name"),
                    "id": props.get("id"),
                    "impassable_deep": bool(props.get("impassable_deep")),
                    "impassable_pond": bool(props.get("impassable_pond")),
                    "road_source": road_source,
                    "honesty": (
                        "Citywide curb/street HAND wet-edge centreline — research "
                        "screening, not street-truth / not NWS."
                    ),
                },
            }
        )

        # Polygon bands only for deeper / impassable ponding to keep file size down.
        if depth_cm < 2.5 and not props.get("impassable_pond") and not props.get("impassable_deep"):
            continue

        for ring, half_w in BAND_HALF_WIDTH_M.items():
            try:
                poly = _buffer_line_ll(g, half_w, lat0).simplify(0.000025, preserve_topology=True)
            except Exception:
                continue
            for part in _parts(poly):
                if part.area <= 0:
                    continue
                feats_out.append(
                    {
                        "type": "Feature",
                        "geometry": mapping(part),
                        "properties": {
                            "role": "hand_street_flood",
                            "ring": ring,
                            "band": {
                                "core": "street_center",
                                "mid": "street_lane",
                                "fringe": "curb",
                            }[ring],
                            "height_scale": HEIGHT_SCALE[ring],
                            "depth_cm": round(depth_cm, 2),
                            "name": props.get("name"),
                            "id": props.get("id"),
                            "road_source": road_source,
                            "model": "road_buffer_citywide",
                            "honesty": (
                                "Citywide curb/street flood proxy: LION wet-edge buffer "
                                "× HAND depth_cm — research screening, not hydraulic "
                                "free surface / not NWS."
                            ),
                        },
                    }
                )

    # If wet edges were missing, emit a labeled synthetic stub corridor set.
    if not line_out:
        n_synth = 1
        stub = LineString([(-73.99, 40.68), (-73.98, 40.685), (-73.97, 40.69)])
        for ring, half_w in BAND_HALF_WIDTH_M.items():
            poly = _buffer_line_ll(stub, half_w, 40.685)
            for part in _parts(poly):
                feats_out.append(
                    {
                        "type": "Feature",
                        "geometry": mapping(part),
                        "properties": {
                            "role": "hand_street_flood",
                            "ring": ring,
                            "depth_cm": 8.0,
                            "road_source": "synthetic_street_axes",
                            "model": "synthetic_fallback",
                            "synthetic": True,
                            "honesty": "SYNTHETIC labeled stub — wet edges missing.",
                        },
                    }
                )
        line_out.append(
            {
                "type": "Feature",
                "geometry": mapping(stub),
                "properties": {
                    "role": "street_flood_centerline",
                    "depth_cm": 8.0,
                    "synthetic": True,
                    "honesty": "SYNTHETIC labeled stub — wet edges missing.",
                },
            }
        )

    polys = {
        "type": "FeatureCollection",
        "properties": {
            "product": "street_flood_citywide",
            "schema_version": "1.0.0",
            "n_polygon_features": len(feats_out),
            "n_line_features": len(line_out),
            "n_real_segments": n_real,
            "n_synthetic": n_synth,
            "official_nws": False,
            "decision_grade": False,
            "honesty": (
                "Citywide curb/street HAND × LION wet-edge buffers for Decision Desk. "
                "Research screening — NOT NWS / NOT street-truth photogrammetry."
            ),
        },
        "features": feats_out,
    }
    lines = {
        "type": "FeatureCollection",
        "properties": dict(polys["properties"]),
        "features": line_out,
    }

    out_poly = ASSETS / "street_flood_citywide.geojson"
    out_line = ASSETS / "street_flood_citywide_lines.geojson"
    out_poly.write_text(json.dumps(polys))
    out_line.write_text(json.dumps(lines))
    meta = {
        "product": "street_flood_citywide",
        "polygon": out_poly.name,
        "lines": out_line.name,
        "n_polygon_features": len(feats_out),
        "n_line_features": len(line_out),
        "n_real_segments": n_real,
        "n_synthetic": n_synth,
        "band_half_width_m": BAND_HALF_WIDTH_M,
        "honesty": polys["properties"]["honesty"],
    }
    meta_path = ASSETS / "street_flood_citywide_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Wrote {out_poly} ({len(feats_out)} polys)")
    print(f"Wrote {out_line} ({len(line_out)} lines)")
    print(f"Wrote {meta_path}")
    return out_poly


if __name__ == "__main__":
    main()
