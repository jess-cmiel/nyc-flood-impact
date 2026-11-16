# Scientific validation pipeline

Reproducible **Python + Jupyter** factor validation behind the Decision Desk UI.
Does **not** redesign the map. Does **not** fabricate skill — every factor is tagged
`observed` / `modeled` / `synthetic`.

NOT NWS verification · NOT decision-grade · HAND stays product primary ·
SFINCS is Advanced non-peer physics reference · no fake SWMM · no HAND rescale to FloodNet.

## How to run

```bash
# from repo root (venv with project deps)
make validation
# or
python scripts/run_validation_pipeline.py
# optional: mirror exports into an Agent Store product_assets folder
python scripts/run_validation_pipeline.py --sync-store /path/to/docs/product_assets
```

Notebook: `notebooks/validation/ida_factor_validation.ipynb`

Tests: `pytest tests/test_validation_pipeline.py`

## What was validated (Ida fixtures)

| Factor | Provenance | Source used |
| --- | --- | --- |
| Precip intensity / duration | **observed** | Metro/hourly MRMS QPE + storm total |
| Antecedent rainfall | **observed** | Sum of MRMS 1h leads 0–5 (early window) |
| Elevation | **observed** | USGS 3DEP metro DEM |
| Slope | **observed** | Degrees from DEM gradient (not stub) |
| Impervious surface | **observed** (+ modeled warp) | NLCD 2021 → metro fraction |
| Drainage / blockage indicators | **modeled** | Open drain-density capacity proxy (not SWMM) |
| Flood susceptibility | **modeled** | Multi-factor screening index |
| HAND primary depth | **modeled** | Product primary HAND × MRMS excess |
| SFINCS depth | **modeled** | Advanced physics reference (non-peer) |
| FloodNet peaks | **observed** | Ida hotspot street sensors |

### Synthetic / stub (labeled, not truth)

| Asset | Note |
| --- | --- |
| `data/processed/slope.tif` | 18×40 stub; **fails** `slope_degrees_plausible` (max ≫ 60°) |
| `data/processed/antecedent_wetness.tif` | Stub; pipeline prefers MRMS early-window sum |
| `data/processed/flash_flood_susceptibility.tif` | Stub fallback only if real susc frame missing |
| Demo drainage nodes GeoJSON | Synthetic / open-derived demo network |

## Exports (HTML contract)

Written under `figures/product_assets/`:

| File | Role |
| --- | --- |
| `science_validation_summary.json` | Full tagged report + synthetic sanity |
| `science_validation_points.geojson` | Collocated FloodNet + grid samples |
| `validation_diags/diag_*.png` | Distributions, correlations, spatial, rainfall-response, severity |
| `product_manifest.json` → `science_validation` | Additive pointer (also under `validation_dashboard`) |

The Decision Desk HTML optionally loads the summary into the existing Advanced
`#validationPanel` (one footnote line). No layout redesign.

Regenerate HTML after manifest changes:

```bash
make html
```

## Module boundaries

- **Weather / Earth-2:** forecast scripts + `nyc_flash_flood_case_study.forecast` only.
  Hydrologic modules must not import `earth2studio`.
- **Hydrologic / flood-impact:** `flood_risk.inundation`, `risk`, `validate`, `validation`.
  Consume precip GeoTIFFs as forcing files.
- See `flood_risk/validation/boundaries.py`.

## Package layout

```
flood_risk/validation/     # library
scripts/run_validation_pipeline.py
notebooks/validation/ida_factor_validation.ipynb
tests/test_validation_pipeline.py
```

Legacy Earth2-vs-311 card remains at `make validation-legacy`.
