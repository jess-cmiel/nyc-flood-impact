"""Provenance tags: observed / modeled / synthetic.

Every validation artifact, plot title, and export field must carry one of
these tags. Never present synthetic placeholders as observations.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ProvenanceTag(str, Enum):
    OBSERVED = "observed"
    MODELED = "modeled"
    SYNTHETIC = "synthetic"


PROVENANCE = ProvenanceTag


def tag_block(
    tag: ProvenanceTag | str,
    *,
    source: str,
    honesty: str,
    assumptions: list[str] | None = None,
) -> dict[str, Any]:
    t = ProvenanceTag(tag)
    return {
        "provenance": t.value,
        "source": source,
        "honesty": honesty,
        "assumptions": list(assumptions or []),
        "official_nws": False,
        "decision_grade": False,
        "certified_skill": False,
    }


def plot_provenance_banner(tag: ProvenanceTag | str, label: str) -> str:
    """Short banner string for matplotlib titles / figure text.

    Accepts ProvenanceTag values or free-form panel tags like ``mixed``.
    """
    raw = tag.value if isinstance(tag, ProvenanceTag) else str(tag)
    return f"[{raw.upper()}] {label}"
