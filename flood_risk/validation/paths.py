"""Catalog of fixture paths with declared provenance for the Ida case study."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from flood_risk.risk.repo_paths import REPO_ROOT
from flood_risk.validation.provenance import ProvenanceTag

ROOT = REPO_ROOT
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
ASSETS = ROOT / "figures" / "product_assets"
OUTPUTS = ROOT / "outputs"


@dataclass(frozen=True)
class AssetRef:
    id: str
    path: Path
    provenance: ProvenanceTag
    role: str
    note: str

    @property
    def exists(self) -> bool:
        return self.path.exists()


def catalog() -> dict[str, AssetRef]:
    """Preferred real fixtures first; stubs are labeled synthetic."""
    return {
        "mrms_storm_total": AssetRef(
            "mrms_storm_total",
            PROCESSED / "earth2_precip" / "mrms_qpe_ida_precip_storm_total.tif",
            ProvenanceTag.OBSERVED,
            "precip_intensity_duration",
            "MRMS Multi-Sensor QPE storm total (~1 km) — observed radar+gauge QPE, not NEXRAD tiles.",
        ),
        "mrms_metro_1h_dir": AssetRef(
            "mrms_metro_1h_dir",
            PROCESSED / "mrms_qpe_metro",
            ProvenanceTag.OBSERVED,
            "precip_hourly",
            "Hourly metro MRMS QPE 1h accumulations for intensity / antecedent.",
        ),
        "earth2_storm_total": AssetRef(
            "earth2_storm_total",
            PROCESSED / "earth2_precip" / "precip_storm_total.tif",
            ProvenanceTag.MODELED,
            "weather_scenario",
            "Earth2 AI precip storm total — modeled scenario, not product primary viz.",
        ),
        "dem_metro": AssetRef(
            "dem_metro",
            RAW / "terrain" / "dem_usgs_metro_work30m.tif",
            ProvenanceTag.OBSERVED,
            "elevation",
            "USGS 3DEP metro DEM (~30 m work grid).",
        ),
        "slope_stub": AssetRef(
            "slope_stub",
            PROCESSED / "slope.tif",
            ProvenanceTag.SYNTHETIC,
            "slope_placeholder",
            "Tiny stub slope raster — synthetic prototype; max values are physically unrealistic.",
        ),
        "antecedent_stub": AssetRef(
            "antecedent_stub",
            PROCESSED / "antecedent_wetness.tif",
            ProvenanceTag.SYNTHETIC,
            "antecedent_placeholder",
            "Tiny stub antecedent wetness — synthetic prototype placeholder.",
        ),
        "impervious_nlcd": AssetRef(
            "impervious_nlcd",
            RAW / "landcover" / "nlcd_2021_impervious_citywide.tif",
            ProvenanceTag.OBSERVED,
            "impervious",
            "NLCD 2021 percent impervious (citywide).",
        ),
        "impervious_metro_frac": AssetRef(
            "impervious_metro_frac",
            PROCESSED / "drainage_capacity" / "impervious_fraction_metro.tif",
            ProvenanceTag.MODELED,
            "impervious_fraction",
            "NLCD-derived impervious fraction warped to metro DEM grid.",
        ),
        "drain_density": AssetRef(
            "drain_density",
            PROCESSED / "drainage_capacity" / "drain_density_norm_metro.tif",
            ProvenanceTag.MODELED,
            "drainage_indicator",
            "Open drain / catch-basin density proxy (not SWMM / not DEP capacity).",
        ),
        "drainage_capacity": AssetRef(
            "drainage_capacity",
            PROCESSED / "drainage_capacity" / "drainage_capacity_mm_hr.tif",
            ProvenanceTag.MODELED,
            "drainage_blockage_proxy",
            "Research drainage capacity proxy mm/hr — not calibrated sewer model.",
        ),
        "susceptibility_storm": AssetRef(
            "susceptibility_storm",
            PROCESSED / "susceptibility" / "mrms_qpe_ida_susc_lead_12h.tif",
            ProvenanceTag.MODELED,
            "flood_susceptibility",
            "Multi-factor susceptibility frame (screening index, not probability).",
        ),
        "susceptibility_stub": AssetRef(
            "susceptibility_stub",
            PROCESSED / "flash_flood_susceptibility.tif",
            ProvenanceTag.SYNTHETIC,
            "susceptibility_placeholder",
            "Tiny stub susceptibility — synthetic prototype.",
        ),
        "hand_depth": AssetRef(
            "hand_depth",
            PROCESSED / "inundation" / "depth_metro_mrms_qpe_ida_storm_total_m.tif",
            ProvenanceTag.MODELED,
            "product_primary_depth",
            "Primary HAND bathtub × MRMS excess (product primary).",
        ),
        "sfincs_depth": AssetRef(
            "sfincs_depth",
            PROCESSED / "inundation" / "depth_sfincs_metro_ida_m.tif",
            ProvenanceTag.MODELED,
            "physics_reference_depth",
            "SFINCS metro Advanced physics reference — non-peer with HAND.",
        ),
        "floodnet_stations": AssetRef(
            "floodnet_stations",
            ASSETS / "floodnet_ida_hotspot_stations.geojson",
            ProvenanceTag.OBSERVED,
            "obs_flood_depth",
            "FloodNet Ida hotspot street sensors (observed).",
        ),
        "floodnet_validation": AssetRef(
            "floodnet_validation",
            ASSETS / "floodnet_validation.json",
            ProvenanceTag.OBSERVED,
            "obs_model_compare",
            "FloodNet vs HAND magnitude card.",
        ),
        "sfincs_hand_overlap": AssetRef(
            "sfincs_hand_overlap",
            ASSETS / "sfincs_hand_overlap.json",
            ProvenanceTag.MODELED,
            "engine_compare",
            "Non-peer SFINCS vs HAND overlap stats.",
        ),
        "drainage_nodes": AssetRef(
            "drainage_nodes",
            ASSETS / "drainage_nodes.geojson",
            ProvenanceTag.SYNTHETIC,
            "drainage_network_demo",
            "Demo drainage nodes — synthetic / open-derived, not DEP sewer graph.",
        ),
    }
