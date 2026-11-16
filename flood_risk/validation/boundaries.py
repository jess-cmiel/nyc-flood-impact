"""Module boundary documentation: weather vs hydrologic / flood-impact.

Earth-2 (and optional MRMS QPE visualization) are weather inputs only.
Hydrologic screening and flood-impact calculations live downstream and must
not import Earth2Studio inside inundation / risk / validate modules.

Boundary map
------------
weather_inputs
  - Earth2Studio forecast scripts (``scripts/run_earth2_forecast.py``)
  - ``nyc_flash_flood_case_study.forecast`` normalize helpers
  - Optional MRMS QPE rasters for Ida visualization / forcing
  - MUST NOT call HAND / SFINCS / drainage capacity / desk ranking

hydrologic_flood_impact
  - ``flood_risk.inundation`` (HAND bathtub, drainage capacity, SFINCS nest)
  - ``flood_risk.risk`` (desk ranking, corridors, access)
  - ``flood_risk.validate`` + ``flood_risk.validation`` (this package)
  - Consumes precip GeoTIFFs / NetCDF as *forcing files*, never as live
    Earth2Studio model objects

product_primary
  - HAND + drainage-capacity excess remains the Decision Desk primary depth
  - SFINCS is Advanced / non-peer physics reference only
"""

from __future__ import annotations

from typing import Any

WEATHER_MODULES = (
    "nyc_flash_flood_case_study.forecast",
    "scripts/run_earth2_forecast.py",
    "scripts/run_live_pipeline.py",
    "scripts/build_earth2_radar_stack.py",
)

HYDRO_MODULES = (
    "flood_risk.inundation",
    "flood_risk.risk",
    "flood_risk.validate",
    "flood_risk.validation",
    "flood_risk.exposure",
    "flood_risk.hazard",
)

FORBIDDEN_EARTH2_IMPORTS_IN_HYDRO = (
    "earth2studio",
    "physicsnemo",
)


def boundary_report() -> dict[str, Any]:
    return {
        "weather_modules": list(WEATHER_MODULES),
        "hydrologic_flood_impact_modules": list(HYDRO_MODULES),
        "forbidden_earth2_imports_in_hydro": list(FORBIDDEN_EARTH2_IMPORTS_IN_HYDRO),
        "product_primary_depth": "pysheds_hand_bathtub + drainage_capacity_proxy",
        "sfincs_role": "advanced_research_hydro_non_peer",
        "honesty": (
            "Earth-2 / weather forcing is separated from hydrologic flood-impact "
            "calculations. SFINCS is Advanced-only; HAND stays product primary."
        ),
    }
