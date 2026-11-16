"""Decision-class filters and typed unofficial SOP hints for the desk."""

from __future__ import annotations

from typing import Any

# Facility types that belong in default All-mode (not schools).
DECISION_FACILITY_TYPES = frozenset({"hospital", "fire", "police"})

# Road highway classes kept in default All-mode.
DECISION_HIGHWAYS = frozenset(
    {"motorway", "trunk", "primary", "secondary", "motorway_link", "trunk_link"}
)

BAND_ACTION_HINTS = {
    "ponding": "Screen corridor / facility for ponding; research ≥3 cm — not an SOP trigger.",
    "deep_ponding": "Elevated research depth ≥8 cm — review access / staging (unofficial).",
    "hazard": "Research depth ≥15 cm — flag for follow-up; NOT agency closure criteria.",
}


def is_unnamed_asset(asset: dict[str, Any]) -> bool:
    name = str(asset.get("name") or "").strip().lower()
    return name.startswith("unnamed ") or name in ("", "nan", "none")


def is_decision_class_asset(asset: dict[str, Any]) -> bool:
    """Default All-mode: hospitals/fire/police, named primary roads, MTA stations, tunnels."""
    if is_unnamed_asset(asset):
        return False
    at = str(asset.get("asset_type") or "")
    if at == "station":
        return True
    if at == "road":
        if asset.get("near_lion_tunnel") or asset.get("limited_access_flag"):
            # Tunnel flag alone is not enough without a name; already filtered unnamed.
            pass
        hwy = str(asset.get("highway") or "").lower()
        name = str(asset.get("name") or "").lower()
        if hwy in DECISION_HIGHWAYS:
            return True
        if any(k in name for k in ("tunnel", "expressway", "parkway", "boulevard", "bridge")):
            return True
        return bool(asset.get("near_lion_tunnel"))
    if at == "facility":
        ft = str(asset.get("facility_type") or "").lower()
        return ft in DECISION_FACILITY_TYPES
    return False


def decision_class_sort_key(asset: dict[str, Any]) -> tuple:
    """Prefer decision classes, demote unnamed / schools, then depth."""
    demoted_geo = 1 if asset.get("demo_demoted") else 0
    unnamed = 1 if is_unnamed_asset(asset) else 0
    decision = 0 if is_decision_class_asset(asset) else 1
    school = 1 if str(asset.get("facility_type") or "").lower() == "school" else 0
    depth = -float(asset.get("max_depth_m") or 0.0)
    name = str(asset.get("name") or "")
    return (demoted_geo, unnamed, decision, school, depth, name)


def apply_decision_class_ranks(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(assets, key=decision_class_sort_key)
    for i, a in enumerate(ranked, start=1):
        a["rank"] = i
        a["decision_class"] = is_decision_class_asset(a)
        a["name_quality"] = "unnamed" if is_unnamed_asset(a) else "named"
    return ranked


def typed_action_hint(asset: dict[str, Any]) -> str:
    """Unofficial research SOP placeholder — never NWS-named."""
    band = str(asset.get("band") or "ponding")
    base = BAND_ACTION_HINTS.get(band, BAND_ACTION_HINTS["ponding"])
    at = str(asset.get("asset_type") or "")
    ft = str(asset.get("facility_type") or "").lower()
    structure = str(asset.get("structure") or "").strip()
    name = str(asset.get("name") or "").lower()
    tunnel = bool(asset.get("near_lion_tunnel")) or "tunnel" in name

    if at == "station":
        if structure and structure.lower() in ("viaduct", "elevated", "open cut"):
            return (
                f"Elevated/viaduct station ({structure}) — research ≥8 cm: "
                "review stair/entrance ponding & bus bridging (unofficial / not MTA SOP)."
            )
        if structure and structure.lower() in ("subway", "underground", "tube"):
            return (
                f"Underground station ({structure}) — research depth: "
                "flag entrance/vent inundation risk for follow-up (unofficial / not MTA SOP)."
            )
        return (
            "Wet station — research depth: review entrance access & customer messaging "
            "(unofficial / not MTA SOP)."
        )
    if at == "facility":
        if ft == "hospital":
            return (
                "Hospital campus — research ≥8 cm: review ambulance approach & loading docks "
                "(unofficial staging note · not agency guidance)."
            )
        if ft == "fire":
            return (
                "Firehouse — research depth: check apparatus egress routes "
                "(unofficial · not FDNY SOP)."
            )
        if ft == "police":
            return (
                "Police facility — research depth: review precinct access corridors "
                "(unofficial · not NYPD SOP)."
            )
        if ft == "school":
            return (
                "School (opt-in inventory) — research ponding screen only; "
                "not a dismissal / shelter SOP."
            )
        return base
    if at == "road":
        if tunnel:
            return (
                "Tunnel / underpass corridor — research ≥8 cm: treat as limited-access "
                "screening candidate (unofficial · not DOT closure)."
            )
        hwy = str(asset.get("highway") or "")
        if hwy in ("motorway", "trunk") or "expressway" in name or "parkway" in name:
            return (
                "Limited-access roadway — research ≥8 cm: review mainline / ramp ponding "
                "for staging (unofficial · not DOT closure)."
            )
        return (
            "Named arterial — research depth: screen curb/underpass ponding "
            "(unofficial · not DOT closure)."
        )
    return base


def apply_typed_action_hints(assets: list[dict[str, Any]]) -> None:
    for a in assets:
        a["action_hint"] = typed_action_hint(a)
        a["action_hint_source"] = "typed_unofficial_sop_v1"
