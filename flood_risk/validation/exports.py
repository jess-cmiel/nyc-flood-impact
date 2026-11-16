"""Export validated results for Decision Desk consumption."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flood_risk.risk.repo_paths import relativize_obj, repo_rel
from flood_risk.validation.paths import ASSETS, OUTPUTS, ROOT
from flood_risk.validation.provenance import ProvenanceTag, tag_block
from flood_risk.validation.schema import validate_export_schema


def points_to_geojson(rows: list[dict[str, Any]]) -> dict[str, Any]:
    features = []
    for r in rows:
        props = {k: v for k, v in r.items() if k not in ("lon", "lat")}
        props.setdefault("provenance", r.get("sample_provenance", ProvenanceTag.MODELED.value))
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                "properties": props,
            }
        )
    return {
        "type": "FeatureCollection",
        "name": "science_validation_points",
        **tag_block(
            ProvenanceTag.MODELED,
            source="flood_risk.validation.exports",
            honesty=(
                "Collocated validation samples. FloodNet points are observed; "
                "grid samples carry modeled factor fields. NOT NWS verification."
            ),
        ),
        "features": features,
    }


def write_exports(
    report: dict[str, Any],
    sample_rows: list[dict[str, Any]],
    plot_artifacts: list[dict[str, str]],
    *,
    sync_store_assets: Path | None = None,
) -> dict[str, str]:
    """Write JSON/GeoJSON/PNG into product_assets + outputs; optional store sync."""
    out_assets = ASSETS
    diag_dir = out_assets / "validation_diags"
    diag_dir.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    (OUTPUTS / "validation").mkdir(parents=True, exist_ok=True)

    geo = points_to_geojson(sample_rows)
    paths = {
        "summary_json": "science_validation_summary.json",
        "points_geojson": "science_validation_points.geojson",
        "diags_dir": "validation_diags",
    }

    # Attach export manifest
    report = dict(report)
    report["exports"] = {
        **paths,
        "plot_artifacts": plot_artifacts,
        "product_assets_dir": repo_rel(out_assets),
    }
    report["schema_errors"] = validate_export_schema(report)
    report = relativize_obj(report)

    summary_path = out_assets / paths["summary_json"]
    points_path = out_assets / paths["points_geojson"]
    summary_path.write_text(json.dumps(report, indent=2))
    points_path.write_text(json.dumps(geo, indent=2))

    # Mirror to outputs/
    (OUTPUTS / "validation" / paths["summary_json"]).write_text(summary_path.read_text())
    (OUTPUTS / "validation" / paths["points_geojson"]).write_text(points_path.read_text())
    (OUTPUTS / paths["summary_json"]).write_text(summary_path.read_text())

    # Copy diags already written into diag_dir by plots module
    for art in plot_artifacts:
        src = diag_dir / art["file"]
        if src.exists():
            shutil.copy2(src, OUTPUTS / "validation" / art["file"])

    # Patch product manifests (additive science_validation key)
    for name in ("product_manifest.json", "manifest.json"):
        mp = out_assets / name
        if not mp.exists():
            continue
        m = json.loads(mp.read_text())
        m["science_validation"] = {
            "summary": paths["summary_json"],
            "points_geojson": paths["points_geojson"],
            "diags": paths["diags_dir"],
            "plot_artifacts": [a["file"] for a in plot_artifacts],
            "official": False,
            "certified_skill": False,
            "decision_grade": False,
            "hand_primary": True,
            "sfincs_role": "advanced_research_hydro_non_peer",
            "honesty": (
                "Additive science validation contract — observed/modeled/synthetic tagged. "
                "Does not redesign UI; Advanced panel may optionally summarize."
            ),
            "updated_utc": report.get("updated_utc"),
        }
        # Also surface under validation_dashboard for discoverability
        vd = m.get("validation_dashboard") or {}
        vd["science_validation"] = paths["summary_json"]
        vd["science_validation_points"] = paths["points_geojson"]
        m["validation_dashboard"] = vd
        mp.write_text(json.dumps(m, indent=2))

    if sync_store_assets is not None:
        sync_store_assets.mkdir(parents=True, exist_ok=True)
        shutil.copy2(summary_path, sync_store_assets / paths["summary_json"])
        shutil.copy2(points_path, sync_store_assets / paths["points_geojson"])
        store_diags = sync_store_assets / "validation_diags"
        store_diags.mkdir(parents=True, exist_ok=True)
        for art in plot_artifacts:
            src = diag_dir / art["file"]
            if src.exists():
                shutil.copy2(src, store_diags / art["file"])

    return {
        "summary": str(summary_path),
        "points": str(points_path),
        "diags": str(diag_dir),
    }
