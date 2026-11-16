"""Schema helpers for tagged validation exports."""

from __future__ import annotations

from typing import Any

from flood_risk.validation.provenance import ProvenanceTag

REQUIRED_TOP_KEYS = (
    "product",
    "official_nws",
    "decision_grade",
    "certified_skill",
    "updated_utc",
    "factors",
    "synthetic_sanity",
    "exports",
    "module_boundaries",
)

REQUIRED_FACTOR_KEYS = (
    "id",
    "label",
    "provenance",
    "status",
    "source",
    "honesty",
)


def assert_tagged(obj: dict[str, Any], *, path: str = "root") -> None:
    if "provenance" not in obj:
        raise AssertionError(f"{path}: missing provenance tag")
    ProvenanceTag(obj["provenance"])  # raises if invalid


def validate_export_schema(report: dict[str, Any]) -> list[str]:
    """Return list of schema errors (empty = ok)."""
    errors: list[str] = []
    for k in REQUIRED_TOP_KEYS:
        if k not in report:
            errors.append(f"missing top-level key: {k}")
    if report.get("official_nws") is not False:
        errors.append("official_nws must be false")
    if report.get("decision_grade") is not False:
        errors.append("decision_grade must be false")
    if report.get("certified_skill") is not False:
        errors.append("certified_skill must be false")

    factors = report.get("factors")
    if not isinstance(factors, dict):
        errors.append("factors must be a dict")
        return errors

    for fid, factor in factors.items():
        if not isinstance(factor, dict):
            errors.append(f"factor {fid}: not a dict")
            continue
        for k in REQUIRED_FACTOR_KEYS:
            if k not in factor:
                errors.append(f"factor {fid}: missing {k}")
        prov = factor.get("provenance")
        if prov is not None:
            try:
                ProvenanceTag(prov)
            except ValueError:
                errors.append(f"factor {fid}: invalid provenance {prov!r}")
    return errors
