# Demo release — `demo-ida-v1`

Annotated tag for a cold-machine Asset Decision Desk replay (research only · NOT NWS).

## What’s frozen

| Path | Role |
| --- | --- |
| `fixtures/ida_v1/` | Access pack + shortlist bundle + engine disagreement + `SHA256SUMS` |
| `figures/vendor/` | Leaflet 1.9.4 + Syne/Figtree/IBM Plex Mono (offline UI chrome) |
| `figures/product_map.html` | Generated desk UI (vendored asset hrefs) |
| `figures/product_assets/decision_desk_shortlist.json` | Default light desk |
| `config/demo_shortlist.yaml` | Shortlist SSOT |

Full wet inventory (`decision_desk_assets.json`) and precip/depth PNGs stay in `figures/product_assets/` for the served demo; checksums for the **fixture pack** live under `fixtures/ida_v1/SHA256SUMS`. Vendor checksums: `figures/vendor/SHA256SUMS`.

## Cold start (offline fixtures)

```bash
git clone https://github.com/jesscmiel/nyc-flood-impact.git
cd nyc-flood-impact
git checkout demo-ida-v1   # after tag exists on remote
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
# optional verify
(cd fixtures/ida_v1 && sha256sum -c SHA256SUMS)
(cd figures/vendor && sha256sum -c SHA256SUMS)
python scripts/serve_product.py
# → http://127.0.0.1:8765/product_map.html
```

Uncheck **Storm layers → Online streets** (or go offline) to drop ArcGIS tiles. Paper basemap + Leaflet/fonts + fixture JSON/GeoJSON work without CDN.

## Create / push the tag (maintainers)

Do **not** use GitHub Release UI unless you want notes/assets there — an annotated git tag is enough.

```bash
# From a clean commit on the ship branch / main:
make demo-tag                 # creates annotated tag demo-ida-v1 locally
git push origin demo-ida-v1   # only when ready to publish the tag
```

Or manually:

```bash
git tag -a demo-ida-v1 -m "Ida Decision Desk demo pack v1 (research fixtures + vendored UI)"
git push origin demo-ida-v1
```

Re-tagging: delete local+remote tag only if intentional (`git tag -d demo-ida-v1 && git push origin :refs/tags/demo-ida-v1`).

## Honesty

Research prototype. NOT official NWS / NOT decision-grade / NOT DEP sewer / synthetic access labeled.
