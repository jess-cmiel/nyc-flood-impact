"""Scientific factor validation pipeline for the Decision Desk.

Weather / Earth-2 inputs stay in ``hazard`` + forecast paths; this package
validates hydrologic and landscape factors used for flood-impact screening.
NOT NWS verification · NOT decision-grade skill certification.
"""

from flood_risk.validation.pipeline import run_validation_pipeline
from flood_risk.validation.provenance import PROVENANCE, ProvenanceTag
from flood_risk.validation.schema import assert_tagged, validate_export_schema

__all__ = [
    "ProvenanceTag",
    "PROVENANCE",
    "assert_tagged",
    "validate_export_schema",
    "run_validation_pipeline",
]
