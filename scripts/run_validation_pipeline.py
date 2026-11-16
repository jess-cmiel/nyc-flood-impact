#!/usr/bin/env python3
"""CLI: regenerate scientific validation exports for the Decision Desk.

Usage:
  python scripts/run_validation_pipeline.py
  python scripts/run_validation_pipeline.py --no-plots
  make validation
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from flood_risk.validation.pipeline import main_summary, run_validation_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-plots", action="store_true", help="Skip diagnostic PNGs")
    parser.add_argument(
        "--no-product-write",
        action="store_true",
        help="Compute report only (no product_assets / manifest patch)",
    )
    parser.add_argument(
        "--sync-store",
        type=Path,
        default=None,
        help="Optional Agent Store docs/product_assets directory to mirror exports",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write full report JSON",
    )
    args = parser.parse_args()

    report = run_validation_pipeline(
        write_product=not args.no_product_write,
        make_plots=not args.no_plots,
        sync_store_assets=args.sync_store,
    )
    summary = main_summary(report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2))
    print(json.dumps(summary, indent=2))
    # Non-zero if schema errors present
    errs = report.get("schema_errors") or []
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
