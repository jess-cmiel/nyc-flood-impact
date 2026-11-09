# NYC Flood Impact

Standalone prototype for an Earth-2–powered NYC flood-impact map, starting from the
**Hurricane Ida remnants** event (2021-09-01) over South Queens / Jamaica Bay.

**Earth2Studio is a dependency only** — this repository is an application, not an
upstream contribution to [NVIDIA/earth2studio](https://github.com/NVIDIA/earth2studio).

## What this is / is not

| Is | Is not |
| --- | --- |
| Deterministic FCN + PrecipitationAFNO precip → map layers | Operational flood guidance |
| Terrain screening, roads/stations, 311 compare | Calibrated inundation depth |
| Optional MRMS **QPE** QA (not BREF) | A PR into NVIDIA/earth2studio |

## Layout

```
src/nyc_flash_flood_case_study/   # Python package
scripts/                          # forecast, map build, demos
figures/ida_v0_event_map.html     # interactive map
figures/ida_v0_assets/            # map layers
data/forecasts/                   # clipped forcing NetCDF (small)
tests/
```

## Install

```bash
cd nyc-flood-impact
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .

# Optional SWMM path
pip install -e '.[swmm]'
```

### Earth2Studio (required for running forecasts)

Install Earth2Studio in the **same** environment (or a sibling GPU env used only for
`scripts/run_earth2_forecast.py`):

```bash
# Preferred during development: editable install from a local checkout
pip install -e /path/to/earth2studio

# Or from PyPI / documented install when you do not need a local checkout
# pip install "earth2studio[...]"   # see Earth2Studio docs for extras
```

Typical local layout on this machine:

```text
~/projects/earth2studio/     # NVIDIA Earth2Studio checkout (framework)
~/projects/nyc-flood-impact/ # this app
```

Forecast generation (GPU / Earth2Studio env):

```bash
python scripts/run_earth2_forecast.py \
  --init-time 2021-09-01T12:00:00 --steps 4 --members 1 \
  --output data/forecasts/earth2_precip_ida_20210901T12.nc
```

Map + optional MRMS QPE QA (app env):

```bash
python scripts/build_ida_v0_map.py \
  --global-forecast data/forecasts/earth2_precip_ida_20210901T12.nc \
  --clipped-forecast data/forecasts/nyc_precip_ida_20210901T12.nc \
  --with-mrms-qa
```

Open the map:

```bash
cd figures
python3 -m http.server 8765 --bind 127.0.0.1
# http://127.0.0.1:8765/ida_v0_event_map.html
```

See [`figures/IDA_V0_DEMO_README.md`](figures/IDA_V0_DEMO_README.md) for layer disclaimers.

## License / attribution

Application code in this repo is intended for research prototyping. Earth2Studio is
separately licensed (Apache-2.0 upstream). OpenStreetMap, NYC Open Data, and NOAA MRMS
have their own terms — retain attributions in the map UI.
