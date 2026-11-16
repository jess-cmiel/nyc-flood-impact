# Asset Decision Desk — product one-pager

**Research replay** for Hurricane Ida (NYC). Not NWS. Not decision-grade.

## Cold start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
python scripts/serve_product.py   # → http://127.0.0.1:8765/product_map.html
```

Fixtures under `fixtures/ida_v1/` + `figures/product_assets/` power the offline demo (CDN Leaflet/fonts still need network unless vendored later).

## Defaults (60s demo)

- Shortlist from `config/demo_shortlist.yaml` (Smith-9 · Van Wyck · Brooklyn Hospital Downtown · Myrtle)
- FloodNet drawer closed; access overlay off; single map key
- HAND screening cm vs FloodNet street peaks honesty chip
- All-mode = decision classes (hospitals / fire / police / stations / named primaries); schools opt-in
- SFINCS Advanced only — non-peer banner + HAND auto-dim
- Henri event picker hidden until radar + inventory parity

## Rebuild DAG (Decision Desk)

```
DEM → MRMS → drainage proxy → HAND depth → exposure GPKG
  → build_decision_desk_assets → expand_ida_access_replay_pack
  → apply_desk_demo_curation → relativize_product_paths → html (make html)
```

`make desk` / `make html` / `make test` / `make access-pack`.
