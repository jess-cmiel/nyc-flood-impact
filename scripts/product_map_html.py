#!/usr/bin/env python3
"""Asset Decision Desk — Ida research replay map HTML.

Demo-locked defaults: assets first, MRMS awareness locked, screening collapsed.
Storm (MRMS) is background awareness. NOT NWS / NOT decision-grade.
"""

from __future__ import annotations

import json
from pathlib import Path

from flood_risk.risk.demo_shortlist import demo_shortlist_ids, load_demo_shortlist
from nyc_flash_flood_case_study.config import FIGURES_DIR
from nyc_flash_flood_case_study.extents import DEFAULT_MAP_EXTENT, EVENTS, EXTENTS

# Backward-compatible alias — canonical source is config/demo_shortlist.yaml
DEMO_SHORTLIST_IDS = tuple(demo_shortlist_ids())


def write_product_html(manifest: dict, pluvial: dict, validation: dict) -> Path:
    precip = manifest.get("precip", {})
    frames = precip.get("frames", [])
    n = max(len(frames), 1)
    shortlist_meta = load_demo_shortlist()
    demo_ids_json = json.dumps(list(shortlist_meta["ids"]))
    shortlist_path_json = json.dumps(shortlist_meta["path"])
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Asset Decision Desk · Ida research replay</title>
<meta name="description" content="Research Asset Decision Desk for Hurricane Ida. Ranked wet assets from metro pysheds × MRMS. NOT official NWS. NOT decision-grade.">
<link rel="stylesheet" href="vendor/fonts/fonts.css">
<link rel="stylesheet" href="vendor/leaflet/1.9.4/leaflet.css">
<link rel="stylesheet" href="vendor/maplibre/3.6.2/maplibre-gl.css">
<style>
:root {{
  --ink:#14161a; --ink-soft:#2c3138; --muted:#6b7280; --paper:#eef0f3;
  --rail:#f7f8fa; --line:rgba(20,22,26,.11); --line-soft:rgba(20,22,26,.06);
  --accent:#c2410c; --accent-deep:#9a3412; --accent-soft:rgba(194,65,12,.10);
  --brand:#16181c; --brand-fg:#eef0f2; --brand-muted:rgba(238,240,242,.68);
  --warn:#9a3412; --warn-bg:rgba(154,52,18,.06); --warn-line:rgba(154,52,18,.22);
  --band-3:#8a6a12; --band-8:#b45309; --band-15:#a31b2e;
  --risk-0:#f7fbff; --risk-3:#9ecae1; --risk-8:#4292c6; --risk-15:#08306b;
  --hud:rgba(18,20,24,.94); --ease:cubic-bezier(.22,.8,.28,1);
  --sans:"DM Sans",ui-sans-serif,sans-serif;
  --serif:"Source Serif 4","Iowan Old Style",Georgia,serif;
  --mono:"IBM Plex Mono",ui-monospace,monospace;
  --radius:4px;
  --rail-w:268px;
  --dock-w:320px;
}}
* {{ box-sizing:border-box; }}
html,body {{
  margin:0; height:100%; font-family:var(--sans); color:var(--ink);
  background:#1a1c20;
  -webkit-font-smoothing:antialiased;
}}
body {{
  display:grid; grid-template-columns:var(--rail-w) minmax(0,1fr);
  min-height:100%; height:100vh; overflow:hidden;
}}
body.has-selection {{ --dock-open:1; }}
@media (max-width:980px) {{
  body {{ grid-template-columns:1fr; grid-template-rows:minmax(42vh,48vh) minmax(0,1fr); height:100dvh; }}
  aside.command-rail {{ max-height:48vh; border-right:0 !important; border-bottom:1px solid var(--line); }}
  .inspector-dock {{ width:min(100%, var(--dock-w)); }}
  .brand {{ padding:14px 14px 12px; }}
  .brand-mark {{ font-size:1.28rem; }}
}}
aside.command-rail {{
  position:relative; z-index:20; display:flex; flex-direction:column;
  min-height:0; overflow:hidden; background:var(--rail);
  border-right:1px solid var(--line);
}}
.rail-scroll {{ flex:1 1 auto; min-height:0; overflow:auto; padding:0 0 16px; }}
.brand {{
  flex:0 0 auto; margin:0; padding:16px 14px 14px;
  background:var(--brand); color:var(--brand-fg);
  border-bottom:1px solid rgba(255,255,255,.06);
}}
@keyframes dockIn {{
  from {{ opacity:0; transform:translateX(12px); }}
  to {{ opacity:1; transform:none; }}
}}
@keyframes cardIn {{
  from {{ opacity:0; transform:translateY(3px); }}
  to {{ opacity:1; transform:none; }}
}}
@keyframes pulseLoad {{
  0%,100% {{ opacity:.45; }} 50% {{ opacity:.9; }}
}}
@media (prefers-reduced-motion: reduce) {{
  .inspector-dock, .briefing-card, .timeline-hud .play, .compare-handle, .risk-ramp-fill {{ transition:none !important; animation:none !important; }}
  * {{ scroll-behavior:auto !important; }}
}}
.coach-overlay {{
  position:fixed; inset:0; z-index:2000; pointer-events:none;
  background:rgba(20,22,26,.18);
}}
.coach-card {{
  pointer-events:auto; position:absolute; left:calc(var(--rail-w) + 16px); top:56px; width:min(300px,84vw);
  padding:12px 12px 10px; border-radius:var(--radius);
  background:#1c1f24; color:var(--brand-fg); border:1px solid rgba(255,255,255,.08);
  font:500 .76rem/1.45 var(--sans);
}}
.coach-card strong {{ font:600 .68rem var(--sans); letter-spacing:.04em; text-transform:uppercase; display:block; margin-bottom:5px; color:#c4c9d0; }}
.coach-card kbd {{
  display:inline-block; padding:0 4px; border-radius:2px; border:1px solid rgba(255,255,255,.18);
  font:600 .62rem var(--mono); color:#d7dbe0;
}}
.coach-card button {{
  margin-top:8px; border:0; border-radius:var(--radius); padding:6px 10px; cursor:pointer;
  background:rgba(255,255,255,.1); color:var(--brand-fg); font:600 .7rem var(--sans);
}}
.coach-card button:hover {{ background:rgba(255,255,255,.16); }}
.sel-chip.disagree {{ background:var(--warn-bg); color:var(--warn); border:1px solid var(--warn-line); }}
.sel-chip.agree {{ background:var(--accent-soft); color:var(--accent-deep); }}
.consequence-cap {{
  font:600 .58rem var(--sans); letter-spacing:.08em; text-transform:uppercase;
  color:var(--muted); margin:8px 0 3px;
}}
.consequence-line {{ font:500 .7rem/1.35 var(--sans); color:var(--ink-soft); }}
.brand-kicker {{
  font:600 .56rem var(--sans); letter-spacing:.12em;
  text-transform:uppercase; color:var(--brand-muted); margin-bottom:6px;
}}
.brand-mark {{
  font:700 clamp(1.2rem,2.2vw,1.42rem)/1.08 var(--serif);
  letter-spacing:-.02em;
}}
.brand-tag {{
  margin-top:6px; font-size:.72rem; line-height:1.35;
  max-width:28ch; color:var(--brand-muted); font-weight:500;
}}
.honesty-line {{
  position:sticky; top:0; z-index:5; margin:0; padding:7px 12px;
  background:rgba(255,250,246,.97); border-bottom:1px solid var(--warn-line);
  color:var(--warn); font:600 .64rem/1.35 var(--sans);
}}
.magnitude-chip {{
  margin:8px 12px 0; padding:5px 8px; border-radius:var(--radius);
  background:transparent; border:1px solid var(--warn-line);
  color:var(--warn); font:500 .64rem/1.35 var(--sans);
}}
.magnitude-chip b {{ font:600 .64rem var(--mono); color:var(--accent-deep); }}
.access-fixture-badge {{
  margin:6px 12px 0; padding:5px 8px; border-radius:var(--radius); display:none;
  background:transparent; border:1px solid var(--line-soft);
  color:var(--muted); font:500 .62rem/1.35 var(--sans);
}}
#assetBanner {{
  margin:8px 12px 0; padding:8px 10px; border-radius:var(--radius); display:none;
  background:#3b0d0d; border:1px solid #7f1d1d; color:#fecaca; font-size:.72rem;
}}
.sfincs-peer-banner {{
  position:absolute; left:12px; right:12px; top:44px; z-index:650;
  display:none; padding:7px 10px; border-radius:var(--radius);
  background:rgba(59,13,13,.92); border:1px solid #7f1d1d; color:#fecaca;
  font:600 .7rem/1.35 var(--sans); pointer-events:none;
}}
body.has-selection .sfincs-peer-banner {{ right:calc(var(--dock-w) + 16px); }}
.hand-dimmed .leaflet-image-layer {{ filter:saturate(.35) opacity(.45); }}
.section {{ padding:10px 12px 2px; }}
.section + .section {{ border-top:1px solid var(--line-soft); }}
.section h2 {{
  display:flex; align-items:baseline; justify-content:space-between; gap:8px;
  font:600 .6rem var(--sans); margin:0 0 8px;
  text-transform:uppercase; letter-spacing:.1em; color:var(--muted);
}}
.section h2 .hint {{ font:500 .62rem var(--sans); letter-spacing:0; text-transform:none; color:#9aa1ab; }}
.metric {{
  display:flex; justify-content:space-between; align-items:baseline; gap:10px;
  font-size:.72rem; padding:0 0 7px; margin:0 0 6px; border-bottom:1px solid var(--line-soft);
}}
.metric b, .readout {{ font:600 .74rem var(--mono); color:var(--accent-deep); }}
label.caption {{ display:block; font-size:.62rem; color:var(--muted); font-weight:600; margin-bottom:3px; letter-spacing:.02em; }}
select, input[type=search] {{
  width:100%; appearance:none; padding:6px 8px; border-radius:var(--radius);
  border:1px solid var(--line); background:#fff;
  font:500 .76rem var(--sans); color:var(--ink);
  transition:border-color .15s, box-shadow .15s;
}}
select:focus, input[type=search]:focus, .briefing-card:focus-visible, .seg:focus-visible, .timeline-hud .play:focus-visible {{
  outline:none; border-color:var(--accent); box-shadow:0 0 0 2px var(--accent-soft);
}}
.command-toolbar {{
  display:flex; flex-direction:column; gap:6px; margin:0 0 8px;
}}
.seg-row {{
  display:grid; grid-auto-flow:column; grid-auto-columns:1fr; gap:0;
  border:1px solid var(--line); border-radius:var(--radius); overflow:hidden; background:#fff;
}}
.seg {{
  border:0; border-right:1px solid var(--line); background:transparent;
  padding:6px 4px; font:600 .62rem var(--sans); color:var(--muted); cursor:pointer;
  transition:background .14s, color .14s;
}}
.seg:last-child {{ border-right:0; }}
.seg:hover {{ color:var(--ink-soft); background:rgba(20,22,26,.03); }}
.seg.active {{ background:var(--accent-soft); color:var(--accent-deep); }}
.filters {{ display:grid; grid-template-columns:1fr 1fr; gap:6px; margin:0; }}
.chip-row {{ display:none; }}
.chip {{ display:none; }}
.asset-list, .floodnet-list {{ display:flex; flex-direction:column; gap:6px; overflow:auto; padding-right:2px; }}
.asset-list {{ max-height:none; flex:1; min-height:120px; }}
.assets-section {{ display:flex; flex-direction:column; min-height:0; flex:1; }}
.floodnet-list {{ max-height:min(28vh,220px); margin-top:8px; }}
.briefing-card {{
  position:relative; text-align:left; width:100%; border:1px solid transparent;
  border-radius:var(--radius); background:#fff; padding:9px 10px 8px;
  cursor:pointer; box-shadow:0 0 0 1px var(--line-soft);
  transition:background .14s var(--ease), border-color .14s, box-shadow .14s, transform .14s;
  animation:cardIn .18s var(--ease);
}}
.briefing-card:hover {{
  border-color:rgba(20,22,26,.14); background:#fff; box-shadow:0 1px 0 rgba(20,22,26,.04);
}}
.briefing-card:focus-visible {{ border-color:var(--accent); }}
.briefing-card.is-hover {{ border-color:rgba(194,65,12,.28); }}
.briefing-card.top-hit {{ box-shadow:inset 2px 0 0 var(--accent); }}
.briefing-card.selected, .briefing-card[aria-selected="true"] {{
  border-color:rgba(194,65,12,.45); background:rgba(194,65,12,.06);
  box-shadow:inset 2px 0 0 var(--accent);
}}
.briefing-card .card-top {{
  display:grid; grid-template-columns:auto 1fr auto; gap:8px; align-items:start;
}}
.briefing-card .rank {{
  font:600 .62rem var(--mono); color:var(--muted); min-width:1.6em; padding-top:2px;
}}
.briefing-card .name {{
  font:600 .8rem/1.25 var(--sans); letter-spacing:-.01em; color:var(--ink);
}}
.briefing-card .depth {{
  font:600 .78rem var(--mono); color:var(--accent-deep); white-space:nowrap;
}}
.briefing-card .card-meta {{
  margin:5px 0 0 1.6em; display:flex; flex-wrap:wrap; gap:4px; align-items:center;
  font-size:.62rem; color:var(--muted);
}}
.briefing-card .lead-bit {{ font:500 .62rem var(--mono); color:var(--ink-soft); }}
.band {{ display:inline-flex; align-items:center; padding:1px 5px; border-radius:2px; font:600 .58rem var(--sans); }}
.band.ponding {{ background:#f5f0dc; color:var(--band-3); }}
.band.deep_ponding {{ background:#f3e6d8; color:var(--band-8); }}
.band.hazard {{ background:#f3dde2; color:var(--band-15); }}
.band.oom-ok {{ background:var(--accent-soft); color:var(--accent-deep); }}
.band.oom-miss {{ background:#f3e6d8; color:var(--band-8); }}
.type-pill {{ display:inline-flex; padding:1px 5px; border-radius:2px; background:rgba(20,22,26,.05); font-weight:600; }}
.legend-swatch {{ height:4px; border-radius:1px; margin:2px 0 8px; opacity:.9; }}
.legend-swatch.precip {{ background:linear-gradient(90deg,#0b1d2a,#1a6f7a,#1ae4b6,#a2fc3c,#f9ba38,#e8332b); }}
.legend-swatch.susc {{ background:linear-gradient(90deg,#fff7bc,#fec44f,#d95f0e,#7f2704); }}
.legend-swatch.depth {{ background:linear-gradient(90deg,#f7fbff,#9ecae1,#4292c6,#08519c,#08306b); }}
.risk-ramp-card {{
  margin:8px 12px 0; padding:8px 9px; border-radius:var(--radius);
  border:1px solid var(--line-soft); background:#fff;
}}
.risk-ramp-card .cap {{
  font:600 .56rem var(--sans); letter-spacing:.08em; text-transform:uppercase; color:#8b929c; margin:0 0 5px;
}}
.risk-ramp-track {{
  height:8px; border-radius:2px;
  background:linear-gradient(90deg,var(--risk-0) 0%,var(--risk-3) 22%,var(--risk-8) 55%,#08519c 78%,var(--risk-15) 100%);
  border:1px solid rgba(20,22,26,.08);
}}
.risk-ramp-labels {{
  display:flex; justify-content:space-between; margin-top:4px;
  font:600 .56rem var(--mono); color:var(--muted);
}}
.risk-ramp-note {{ margin:4px 0 0; font-size:.6rem; line-height:1.35; color:var(--muted); }}
.opacity-row {{ display:grid; grid-template-columns:64px 1fr 34px; gap:8px; align-items:center; font-size:.7rem; margin:4px 0; color:var(--muted); }}
.opacity-row input[type=range] {{ width:100%; accent-color:var(--accent); }}
.layer-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:5px; }}
.group-label {{ grid-column:1 / -1; margin:6px 0 0; font:600 .58rem var(--sans); letter-spacing:.08em; text-transform:uppercase; color:#8b929c; }}
.layer-btn {{
  position:relative; display:flex; align-items:center; gap:6px; min-height:30px;
  padding:5px 7px 5px 26px; border-radius:var(--radius); border:1px solid transparent;
  background:transparent; cursor:pointer; font-size:.7rem; font-weight:600;
  transition:background .14s, border-color .14s, color .14s;
}}
.layer-btn input {{ position:absolute; left:7px; top:50%; transform:translateY(-50%); margin:0; accent-color:var(--accent); }}
.layer-btn:hover {{ background:rgba(20,22,26,.04); }}
.layer-btn:has(input:checked) {{ background:var(--accent-soft); border-color:rgba(194,65,12,.28); color:var(--accent-deep); }}
.storm-toggles {{ display:grid; grid-template-columns:1fr 1fr; gap:5px; margin:0 0 6px; }}
details.drawer {{ font-size:.74rem; color:var(--muted); }}
details.drawer > summary {{
  cursor:pointer; list-style:none; font:600 .6rem var(--sans); letter-spacing:.08em;
  text-transform:uppercase; color:var(--ink-soft); padding:2px 0 7px;
  display:flex; align-items:center; justify-content:space-between;
}}
details.drawer > summary::-webkit-details-marker {{ display:none; }}
details.drawer > summary::after {{ content:"+"; font:600 .85rem var(--mono); color:var(--muted); }}
details.drawer[open] > summary::after {{ content:"–"; }}
.drawer-note {{ margin:0 0 7px; font-size:.66rem; line-height:1.35; color:var(--muted); }}
.map-stage {{
  position:relative; min-width:0; min-height:0; height:100%;
  background:#1a1c20; overflow:hidden;
}}
.map-el {{
  position:absolute; inset:0; right:0; background:#d8dce2;
  transition:right .22s var(--ease);
}}
body.has-selection .map-el {{ right:var(--dock-w); }}
@media (max-width:980px) {{
  body.has-selection .map-el {{ right:0; }}
}}
.pane-label {{
  position:absolute; z-index:1000; top:12px; left:50px; padding:5px 9px; border-radius:var(--radius);
  background:rgba(22,24,28,.86); color:#e8eaed; border:1px solid rgba(255,255,255,.06);
  font:600 .66rem var(--sans); letter-spacing:.02em;
  transition:opacity .18s var(--ease);
}}
.kbd-hint {{
  position:absolute; z-index:1000; top:12px; right:12px; padding:5px 8px; border-radius:var(--radius);
  background:rgba(22,24,28,.72); color:#c4c9d0; border:1px solid rgba(255,255,255,.06);
  font:500 .6rem/1.3 var(--sans); pointer-events:none;
  transition:right .22s var(--ease), opacity .18s;
}}
body.has-selection .kbd-hint {{ right:calc(var(--dock-w) + 12px); opacity:.55; }}
.kbd-hint kbd {{
  display:inline-block; padding:0 3px; margin:0 1px; border-radius:2px;
  border:1px solid rgba(255,255,255,.16); font:600 .56rem var(--mono);
}}
.timeline-hud {{
  position:absolute; z-index:1100; left:50%; bottom:12px; transform:translateX(-50%);
  width:min(760px, calc(100% - 24px));
  display:grid; grid-template-columns:auto 1fr auto; gap:8px 12px; align-items:center;
  padding:10px 12px 8px; border-radius:var(--radius);
  background:var(--hud); color:#eef0f2; border:1px solid rgba(255,255,255,.08);
  box-shadow:0 8px 24px rgba(0,0,0,.22);
  transition:width .22s var(--ease), transform .22s var(--ease);
}}
body.has-selection .timeline-hud {{
  width:min(560px, calc(100% - var(--dock-w) - 28px));
  transform:translateX(calc(-50% - var(--dock-w) / 2));
}}
@media (max-width:980px) {{
  body.has-selection .timeline-hud {{ width:min(760px, calc(100% - 24px)); transform:translateX(-50%); }}
}}
.timeline-hud.playing .play {{ background:#9a3412; }}
.timeline-hud .play {{
  width:38px; height:38px; border-radius:var(--radius); border:0; cursor:pointer;
  background:var(--accent); color:#fff; font:600 .85rem var(--sans);
  transition:background .15s, transform .15s;
}}
.timeline-hud .play:hover {{ filter:brightness(1.05); }}
.timeline-hud .clock {{ font:600 .9rem var(--serif); letter-spacing:-.01em; }}
.timeline-hud .sub {{ font-size:.62rem; opacity:.72; margin-top:1px; font-weight:500; }}
.timeline-hud .legend {{ display:flex; flex-direction:column; gap:3px; align-items:flex-end; font-size:.6rem; opacity:.85; }}
.timeline-hud .bar {{ width:96px; height:4px; border-radius:1px; background:linear-gradient(90deg,#0b1d2a,#1a6f7a,#1ae4b6,#a2fc3c,#f9ba38,#e8332b); }}
.timeline-hud .bar.susc {{ background:linear-gradient(90deg,#fff7bc,#fec44f,#d95f0e,#7f2704); }}
.timeline-track {{
  grid-column:1 / -1; position:relative; padding:2px 0 0;
}}
.timeline-ticks {{
  display:flex; justify-content:space-between; pointer-events:none;
  margin:0 2px 2px; font:500 .52rem var(--mono); color:rgba(238,240,242,.55);
}}
.timeline-hud .scrub {{
  width:100%; accent-color:var(--accent); height:16px; cursor:pointer; margin:0;
}}
.inspector-dock {{
  position:absolute; z-index:1050; top:0; right:0; bottom:0;
  width:var(--dock-w); max-width:100%;
  display:flex; flex-direction:column;
  background:rgba(250,250,251,.98); border-left:1px solid var(--line);
  box-shadow:-8px 0 24px rgba(0,0,0,.12);
  transform:translateX(104%);
  transition:transform .22s var(--ease);
  pointer-events:none;
}}
.inspector-dock.open {{
  transform:none; pointer-events:auto;
  animation:dockIn .22s var(--ease);
}}
.inspector-dock .dock-head {{
  flex:0 0 auto; padding:14px 14px 10px; border-bottom:1px solid var(--line-soft);
  position:relative;
}}
.inspector-dock .sel-kicker {{ font:600 .56rem var(--sans); letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:4px; }}
.inspector-dock h3 {{ margin:0; font:700 1.05rem/1.15 var(--serif); letter-spacing:-.015em; padding-right:28px; }}
.inspector-dock .dock-body {{
  flex:1 1 auto; min-height:0; overflow:auto; padding:4px 14px 16px;
}}
.inspector-dock .sel-close {{
  position:absolute; top:10px; right:10px; width:28px; height:28px; border:0; border-radius:var(--radius);
  background:rgba(20,22,26,.05); color:var(--ink-soft); cursor:pointer; font:600 .85rem var(--sans);
}}
.inspector-dock .sel-close:hover {{ background:rgba(20,22,26,.1); }}
.inspector-empty {{
  display:none; flex:1; align-items:center; justify-content:center; text-align:center;
  padding:24px; color:var(--muted); font:500 .78rem/1.45 var(--sans);
}}
.inspector-dock:not(.open) .inspector-empty {{ display:flex; }}
.inspector-dock:not(.open) .dock-head,
.inspector-dock:not(.open) .dock-body {{ display:none; }}
.sel-block {{ margin-top:10px; padding-top:10px; border-top:1px solid var(--line-soft); }}
.sel-block:first-of-type {{ margin-top:8px; }}
.sel-block-label {{
  font:600 .56rem var(--sans); letter-spacing:.1em; text-transform:uppercase;
  color:var(--muted); margin-bottom:5px;
}}
.sel-depth-hero {{
  font:700 1.35rem/1 var(--mono); color:var(--accent-deep); letter-spacing:-.02em;
}}
.sel-depth-meta {{ margin-top:4px; font:500 .74rem/1.35 var(--sans); color:var(--muted); }}
.inspector-dock .sel-chips {{ display:flex; flex-wrap:wrap; gap:4px; margin:0; }}
.inspector-dock .sel-chip {{
  font:600 .6rem var(--mono); padding:3px 7px; border-radius:2px;
  border:1px solid var(--line); background:rgba(20,22,26,.03); color:var(--ink-soft);
}}
.inspector-dock .sel-chip.access-open {{ border-color:rgba(194,65,12,.28); color:var(--accent-deep); }}
.inspector-dock .sel-chip.access-watch {{ border-color:rgba(154,52,18,.3); color:var(--warn); background:var(--warn-bg); }}
.inspector-dock .sel-chip.access-limited {{ border-color:rgba(163,27,46,.35); color:#9f1239; background:rgba(163,27,46,.06); }}
.inspector-dock .sel-hint {{
  margin-top:10px; padding:8px 9px; border-radius:var(--radius);
  background:rgba(20,22,26,.03); border:1px solid var(--line-soft);
  font-size:.72rem; color:var(--ink-soft); line-height:1.4; font-weight:600;
}}
.inspector-dock .sel-access-note {{ margin-top:4px; font-size:.64rem; color:var(--muted); line-height:1.35; }}
.sel-street3d-btn {{
  display:inline-flex; align-items:center; gap:6px; margin-top:10px;
  border:1px solid rgba(194,65,12,.35); background:rgba(194,65,12,.08);
  color:var(--accent-deep); border-radius:var(--radius);
  padding:7px 10px; font:600 .7rem var(--sans); cursor:pointer; width:100%;
  justify-content:center;
}}
.sel-street3d-btn:hover {{ background:rgba(194,65,12,.14); }}
.sel-street3d-btn[hidden] {{ display:none !important; }}
.street-view-3d {{
  /* Above inspector-dock (1050) / map chrome so 3D is actually visible + closable */
  position:absolute; inset:0; z-index:1200; display:flex; flex-direction:column;
  background:#121418; color:#eef0f2;
}}
.street-view-3d[hidden] {{ display:none !important; }}
.street-view-3d .sv-head {{
  flex:0 0 auto; display:flex; align-items:flex-start; justify-content:space-between;
  gap:12px; padding:12px 14px 10px; border-bottom:1px solid rgba(238,240,242,.12);
  position:relative; z-index:2;
}}
.street-view-3d .sv-kicker {{
  font:600 .56rem var(--sans); letter-spacing:.1em; text-transform:uppercase;
  color:rgba(238,240,242,.62); margin-bottom:4px;
}}
.street-view-3d h2 {{
  margin:0; font:700 1.15rem/1.15 var(--serif); letter-spacing:-.015em; color:#fff;
}}
.street-view-3d .sv-sub {{ margin-top:4px; font:500 .72rem/1.35 var(--sans); color:rgba(238,240,242,.72); }}
.street-view-3d .sv-close {{
  border:0; background:rgba(238,240,242,.1); color:#fff; width:32px; height:32px;
  border-radius:var(--radius); font-size:1.1rem; cursor:pointer; flex:0 0 auto;
}}
.street-view-3d .sv-close:hover {{ background:rgba(238,240,242,.18); }}
.street-view-3d .sv-stats {{
  flex:0 0 auto; display:flex; flex-wrap:wrap; gap:10px 16px; padding:8px 14px;
  border-bottom:1px solid rgba(238,240,242,.08); font:600 .68rem var(--mono);
  position:relative; z-index:2;
}}
.street-view-3d .sv-stats span {{ color:rgba(238,240,242,.55); font-weight:500; margin-right:4px; }}
.street-view-3d .sv-map {{ flex:1 1 auto; min-height:0; position:relative; background:#1a1d22; }}
.street-view-3d .sv-map .maplibregl-map {{ position:absolute; inset:0; }}
.street-view-3d .sv-foot {{
  flex:0 0 auto; padding:8px 14px 12px; font:500 .66rem/1.4 var(--sans);
  color:rgba(238,240,242,.7); border-top:1px solid rgba(238,240,242,.08);
  position:relative; z-index:2;
}}
.street-view-3d .sv-status {{ margin-top:2px; color:rgba(238,240,242,.55); font-size:.62rem; }}
/* Timeline + view toggle stay above 3D so lead scrub still drives HAND extrusion */
body.street-view-open .timeline-hud {{ z-index:1300; }}
body.street-view-open .view-mode-toggle {{ z-index:1310; }}
body.street-view-open .kbd-hint,
body.street-view-open .pane-label,
body.street-view-open .map-key-float,
body.street-view-open .sfincs-peer-banner {{ display:none !important; }}
.view-mode-toggle {{
  position:absolute; z-index:660; top:10px; right:10px;
  display:inline-flex; gap:0; border-radius:var(--radius);
  border:1px solid rgba(255,255,255,.12); background:rgba(18,20,24,.9);
  backdrop-filter:blur(6px); overflow:hidden;
}}
.view-mode-toggle button {{
  border:0; background:transparent; color:#9aa3ae; cursor:pointer;
  font:700 .68rem/1 var(--sans); letter-spacing:.06em; text-transform:uppercase;
  padding:8px 12px; min-width:44px;
}}
.view-mode-toggle button[aria-pressed="true"] {{
  background:rgba(194,65,12,.92); color:#fff;
}}
.view-mode-toggle button:hover:not([aria-pressed="true"]) {{
  background:rgba(255,255,255,.06); color:#e8eaed;
}}
body.view-3d .compare-shell,
body.view-3d .compare-toggle {{ pointer-events:none; opacity:.45; }}
.sel-access-line {{ font:600 .74rem var(--sans); color:var(--ink-soft); }}
.briefing-card .access-pill {{
  font:600 .56rem var(--mono); padding:1px 4px; border-radius:2px;
  border:1px solid var(--line-soft); color:var(--muted);
}}
.briefing-card .access-pill.limited {{ color:#9f1239; border-color:rgba(185,28,28,.3); }}
.briefing-card .access-pill.watch {{ color:var(--warn); border-color:rgba(154,74,18,.28); }}
.empty {{
  padding:18px 10px; text-align:center; color:var(--muted); font-size:.74rem; line-height:1.4;
  border:1px dashed var(--line); border-radius:var(--radius); background:rgba(255,255,255,.55);
}}
.empty.loading {{ animation:pulseLoad 1.2s ease-in-out infinite; border-style:solid; }}
.leaflet-image-layer.precip-radar,
.leaflet-image-layer.depth-radar,
.leaflet-image-layer.susc-radar {{
  -webkit-mask-image: radial-gradient(ellipse 96% 92% at 50% 50%, #000 68%, transparent 100%);
  mask-image: radial-gradient(ellipse 96% 92% at 50% 50%, #000 68%, transparent 100%);
  image-rendering: auto;
  filter: saturate(1.02) contrast(1.02);
  transition:opacity .2s ease;
}}
.leaflet-image-layer.precip-radar {{
  mix-blend-mode: multiply;
  filter: saturate(1.05) contrast(1.04);
}}
.leaflet-image-layer.depth-radar {{
  mix-blend-mode: multiply;
  filter: saturate(1.04) contrast(1.05);
}}
.leaflet-image-layer.susc-radar {{ mix-blend-mode: multiply; filter: saturate(1.05) contrast(1.04); }}
.sparkline-wrap {{ margin-top:8px; }}
.sparkline-wrap .spark-cap {{
  font:600 .56rem var(--sans); letter-spacing:.08em; text-transform:uppercase;
  color:var(--muted); margin-bottom:3px;
}}
.sparkline-wrap svg {{ display:block; width:100%; height:44px; }}
.sparkline-wrap .spark-readout {{
  margin-top:2px; font:600 .62rem var(--mono); color:var(--accent-deep);
}}
.shortlist-actions {{
  display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 0; align-items:center;
}}
.shortlist-actions button {{
  border:0; background:transparent; color:var(--muted);
  border-radius:0; padding:2px 0; font:600 .64rem var(--sans); cursor:pointer;
  text-decoration:underline; text-underline-offset:2px;
}}
.shortlist-actions button:hover {{ color:var(--accent-deep); }}
.shortlist-actions .status {{
  flex:1 1 100%; font-size:.6rem; color:var(--muted); min-height:1em;
}}
.drawer .drawer {{
  margin:8px 0 0; border:1px solid var(--line-soft); border-radius:var(--radius); padding:0 8px 6px;
  background:rgba(20,22,26,.02);
}}
.drawer .drawer > summary {{
  font:600 .58rem var(--sans); letter-spacing:.06em; text-transform:uppercase;
  color:#8b929c; padding:7px 2px;
}}
@media print {{
  body {{ display:block; background:#fff; height:auto; overflow:visible; }}
  aside.command-rail {{ max-height:none !important; border:0 !important; }}
  .map-stage, .timeline-hud, .map-key-float, .honesty-line, .inspector-dock, .kbd-hint {{ display:none !important; }}
  .print-snapshot {{ display:block !important; }}
}}
.print-snapshot {{ display:none; padding:16px; font:500 .85rem var(--sans); }}
.print-snapshot h1 {{ font:700 1.2rem var(--serif); margin:0 0 8px; }}
.print-snapshot pre {{ white-space:pre-wrap; background:#f4f5f7; padding:12px; border-radius:var(--radius); }}
.leaflet-control-zoom a {{ border-radius:var(--radius) !important; }}
.marker-key {{ margin:4px 0 0; }}
.map-dot-toggles {{ display:grid; grid-template-columns:1fr 1fr; gap:4px; margin:0 0 8px; }}
.map-dot-toggles .layer-btn {{ font-size:.68rem; padding:6px 7px 6px 24px; }}
.map-legend-rows {{ display:flex; flex-direction:column; gap:5px; }}
.map-legend-row {{ display:flex; align-items:center; gap:7px; color:var(--ink-soft); font-size:.66rem; }}
.map-legend-row span {{ color:var(--muted); }}
.leg-sw {{ flex:0 0 auto; width:14px; height:14px; position:relative; }}
.leg-sw svg {{ display:block; width:14px; height:14px; }}
.access-legend {{
  margin-top:6px; padding-top:6px; border-top:1px solid var(--line-soft);
  display:flex; flex-direction:column; gap:4px;
}}
.access-legend .cap {{
  font:600 .56rem var(--sans); letter-spacing:.08em; text-transform:uppercase; color:#8b929c;
}}
.map-key-float {{
  position:absolute; z-index:650; left:10px; bottom:84px; max-width:min(188px, calc(100% - 20px));
  padding:6px 8px; border-radius:var(--radius); background:rgba(18,20,24,.88); color:#e4e7eb;
  border:1px solid rgba(255,255,255,.07); font-size:.6rem; line-height:1.3;
  transition:bottom .22s var(--ease);
  backdrop-filter:blur(6px);
}}
body.compare-on .map-key-float {{ bottom:118px; }}
.map-key-float.collapsed .map-key-float-body {{ display:none; }}
.map-key-float-head {{
  display:flex; align-items:center; justify-content:space-between; gap:8px;
  font:600 .54rem var(--sans); letter-spacing:.09em; text-transform:uppercase; color:#9aa3ae;
}}
.map-key-float-head button {{
  border:0; background:rgba(255,255,255,.05); color:#d7dbe0; border-radius:2px;
  width:18px; height:18px; cursor:pointer; font:600 .65rem var(--sans);
}}
.map-key-float-head button:hover {{ background:rgba(255,255,255,.12); }}
.map-key-float-body {{ margin-top:5px; display:flex; flex-direction:column; gap:4px; }}
.map-key-float .map-legend-row {{ color:#e8eaed; gap:6px; font-size:.6rem; }}
.map-key-float .map-legend-row span {{ color:#9aa3ae; }}
.map-key-float .key-corridor {{ display:none; }}
.map-key-float.show-corridor .key-corridor {{ display:flex; }}
.map-key-float .key-risk-ramp {{
  margin-top:2px; padding-top:5px; border-top:1px solid rgba(255,255,255,.08);
}}
.map-key-float .key-risk-track {{
  height:6px; border-radius:1px; margin:3px 0 3px;
  background:linear-gradient(90deg,#f7fbff 0%,#9ecae1 22%,#4292c6 55%,#08519c 78%,#08306b 100%);
}}
.map-key-float .key-risk-labels {{
  display:flex; justify-content:space-between; font:600 .5rem var(--mono); color:#9aa3ae;
}}
.compare-shell {{
  position:absolute; inset:0; z-index:620; pointer-events:none;
  display:none;
}}
body.compare-on .compare-shell {{ display:block; }}
.compare-divider {{
  position:absolute; top:0; bottom:0; width:0; left:50%;
  pointer-events:none;
}}
.compare-divider::before {{
  content:""; position:absolute; top:0; bottom:0; left:-1px; width:2px;
  background:rgba(255,255,255,.92); box-shadow:0 0 0 1px rgba(20,22,26,.35);
}}
.compare-handle {{
  position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
  width:34px; height:34px; border-radius:50%;
  background:rgba(18,20,24,.92); color:#eef0f2;
  border:1.5px solid rgba(255,255,255,.55);
  display:flex; align-items:center; justify-content:center;
  font:700 .7rem var(--mono); letter-spacing:-.04em;
  pointer-events:auto; cursor:ew-resize; user-select:none;
  box-shadow:0 4px 14px rgba(0,0,0,.28);
  transition:transform .14s var(--ease), background .14s;
}}
.compare-handle:hover {{ background:#c2410c; transform:translate(-50%,-50%) scale(1.04); }}
.compare-handle:active {{ cursor:grabbing; }}
.compare-chip {{
  position:absolute; top:48px; padding:5px 8px; border-radius:var(--radius);
  background:rgba(18,20,24,.88); color:#e8eaed; border:1px solid rgba(255,255,255,.08);
  font:600 .62rem/1.25 var(--sans); pointer-events:none; max-width:42%;
  backdrop-filter:blur(6px);
}}
.compare-chip.left {{ left:12px; }}
.compare-chip.right {{ right:12px; text-align:right; }}
.compare-chip .sub {{ display:block; margin-top:1px; font:500 .56rem var(--sans); color:#9aa3ae; }}
body.compare-on .timeline-hud {{ grid-template-columns:auto 1fr auto auto; }}
.compare-toggle {{
  border:1px solid rgba(255,255,255,.14); background:rgba(255,255,255,.06);
  color:#e8eaed; border-radius:var(--radius); padding:6px 9px;
  font:600 .62rem var(--sans); cursor:pointer; white-space:nowrap;
}}
.compare-toggle[aria-pressed="true"] {{
  background:#c2410c; border-color:rgba(255,255,255,.2); color:#fff;
}}
.compare-toggle:hover {{ filter:brightness(1.06); }}
.compare-controls {{
  display:none; grid-column:1 / -1; gap:8px; align-items:center;
  padding-top:4px; border-top:1px solid rgba(255,255,255,.08); margin-top:2px;
}}
body.compare-on .compare-controls {{ display:flex; flex-wrap:wrap; }}
.compare-controls label {{
  display:flex; align-items:center; gap:5px; font:500 .6rem var(--sans); color:#b8c0c8;
}}
.compare-controls select {{
  background:rgba(255,255,255,.08); color:#eef0f2; border:1px solid rgba(255,255,255,.14);
  border-radius:2px; font:600 .6rem var(--mono); padding:3px 5px;
}}
.compare-controls .preset-btn {{
  border:1px solid rgba(255,255,255,.14); background:transparent; color:#cfd4da;
  border-radius:2px; padding:3px 7px; font:600 .56rem var(--sans); cursor:pointer;
}}
.compare-controls .preset-btn.active {{ background:rgba(194,65,12,.35); border-color:rgba(255,180,140,.35); color:#fff; }}
.compare-controls .hint {{ font:500 .56rem var(--sans); color:#8b929c; margin-left:auto; }}
.leaflet-image-layer.compare-clip {{ will-change: clip; }}
.sel-severity {{
  display:grid; grid-template-columns:1fr auto; gap:6px 10px; align-items:end;
  margin-top:6px;
}}
.sel-severity .meter {{
  height:7px; border-radius:2px; background:rgba(20,22,26,.06); overflow:hidden;
  border:1px solid var(--line-soft);
}}
.sel-severity .meter > i {{
  display:block; height:100%; border-radius:1px;
  background:linear-gradient(90deg,var(--risk-3),var(--risk-8),var(--risk-15));
  transition:width .22s var(--ease);
}}
.sel-severity .meter-label {{
  font:600 .58rem var(--mono); color:var(--muted); text-align:right;
}}
.sel-tag-row {{
  display:flex; flex-wrap:wrap; gap:4px; margin-top:6px;
}}
.sel-tag {{
  display:inline-flex; align-items:center; gap:3px; padding:2px 6px;
  border-radius:2px; border:1px solid var(--line-soft);
  font:600 .56rem var(--sans); color:var(--ink-soft); background:#fff;
}}
.sel-tag.warn {{ border-color:var(--warn-line); color:var(--warn); background:var(--warn-bg); }}
.sel-tag.ok {{ border-color:rgba(15,118,110,.28); color:#0f766e; background:rgba(15,118,110,.06); }}
.sel-tag.muted {{ color:var(--muted); }}
.sel-lead-grid {{
  display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:6px;
}}
.sel-stat {{
  padding:6px 7px; border-radius:var(--radius); border:1px solid var(--line-soft);
  background:rgba(20,22,26,.02);
}}
.sel-stat .k {{ font:600 .52rem var(--sans); letter-spacing:.06em; text-transform:uppercase; color:#8b929c; }}
.sel-stat .v {{ margin-top:2px; font:700 .78rem/1.2 var(--mono); color:var(--ink); }}
.sel-stat .s {{ margin-top:1px; font:500 .58rem var(--sans); color:var(--muted); }}
.leaflet-div-icon.access-div {{
  background:transparent; border:0; width:16px !important; height:16px !important;
}}
.access-marker {{
  width:14px; height:14px; display:flex; align-items:center; justify-content:center;
  font:600 .4rem var(--sans); letter-spacing:.02em; color:#fff;
  border:1px solid; line-height:1; opacity:.92;
}}
.access-marker.dot {{ border-radius:2px; background:rgba(154,74,18,.88); border-color:#7c2d12; border-style:dashed; }}
.access-marker.dot.limited {{ background:rgba(136,19,55,.9); border-color:#7f1d1d; }}
.access-marker.ev511 {{
  clip-path:polygon(50% 8%, 92% 88%, 8% 88%); border:0; border-radius:0;
  background:#9a4a12; box-shadow:none; font-size:.32rem; padding-top:4px;
}}
.access-marker.ev511.limited {{ background:#881337; }}
.access-marker.mta {{ border-radius:50%; background:rgba(30,48,72,.9); border-color:#1a2a3d; border-style:solid; }}
.access-marker.mta.limited {{ background:rgba(136,19,55,.9); border-color:#7f1d1d; border-style:dashed; }}
.access-marker.mta.watch {{ border-style:dashed; border-color:#9a4a12; background:rgba(154,74,18,.86); }}
.corridor-pairs {{ display:flex; flex-direction:column; gap:5px; margin:0 0 8px; }}
.corridor-pair {{
  display:grid; grid-template-columns:auto 1fr auto; gap:7px; align-items:center;
  padding:6px 7px; border-radius:var(--radius); border:1px solid var(--line-soft);
  background:rgba(255,255,255,.65); cursor:pointer; font-size:.66rem;
  transition:border-color .14s, background .14s;
}}
.corridor-pair:hover {{ border-color:rgba(20,22,26,.16); }}
.corridor-pair input {{ margin:0; accent-color:var(--accent); }}
.corridor-pair .pair-names {{
  font:600 .66rem/1.25 var(--sans); color:var(--ink-soft); letter-spacing:-.01em;
}}
.corridor-pair .pair-status {{
  font:600 .58rem var(--mono); white-space:nowrap;
}}
.corridor-pair .pair-status.cut {{ color:#9f1239; }}
.corridor-pair .pair-status.open {{ color:#0f766e; }}
.corridor-pair .pair-swatch {{
  width:14px; height:3px; border-radius:1px; flex:0 0 auto;
}}
.corridor-pair .pair-swatch.cut {{ background:transparent; border-top:2px dashed; }}
.corridor-pair .pair-swatch.open {{ background:currentColor; border:0; height:2.5px; }}
.corridor-landmarks-note {{ margin:0 0 6px; font-size:.62rem; color:var(--muted); }}
.compare-strip {{
  margin:6px 0 0; padding:6px 8px; border-radius:var(--radius);
  background:rgba(20,22,26,.03); border:1px solid var(--line-soft);
  font:500 .68rem/1.35 var(--sans); color:var(--muted);
}}
.compare-strip b {{ color:var(--ink); font-weight:700; }}
.compare-strip .compare-kicker {{
  font:600 .56rem var(--sans); letter-spacing:.05em; text-transform:uppercase;
  color:var(--accent-deep); margin-bottom:3px;
}}
.rail-compact details.drawer > summary {{ padding-bottom:6px; }}
.leaflet-interactive.is-hover {{ filter:brightness(1.06); }}
.floodnet-list .asset-row {{
  text-align:left; width:100%; border:1px solid var(--line-soft); border-radius:var(--radius);
  background:#fff; padding:7px 8px; cursor:pointer; font:500 .7rem var(--sans);
  transition:border-color .14s, background .14s;
}}
.floodnet-list .asset-row:hover {{ border-color:rgba(20,22,26,.18); }}
.floodnet-list .asset-row.selected {{ border-color:rgba(194,65,12,.4); background:rgba(194,65,12,.06); }}
.floodnet-list .asset-row .top {{ display:flex; justify-content:space-between; gap:8px; }}
.floodnet-list .asset-row .name {{ font-weight:600; }}
.floodnet-list .asset-row .depth {{ font:600 .7rem var(--mono); color:var(--accent-deep); }}
.floodnet-list .asset-row .meta {{ margin-top:2px; display:flex; flex-wrap:wrap; gap:4px; font-size:.62rem; color:var(--muted); }}
</style>
</head>
<body>
<aside class="command-rail" aria-label="Decision Desk command rail">
  <div class="brand">
    <div class="brand-kicker">Ida research replay</div>
    <div class="brand-mark">Asset Decision Desk</div>
    <div class="brand-tag">Select a briefing card → inspect on the map.</div>
  </div>
  <div class="rail-scroll">
  <p class="honesty-line">Research only · NOT NWS · cm-scale HAND ranking, not street-truth depths.</p>
  <div class="magnitude-chip" id="magnitudeChip" role="status">
    HAND screening <b>~cm</b> · FloodNet street peaks up to <b>~0.9 m</b> (n=5) — not the same scale.
  </div>
  <div class="risk-ramp-card" aria-label="Research depth severity ramp">
    <div class="cap">Risk ramp · HAND cm bands</div>
    <div class="risk-ramp-track" title="Research severity gradient"></div>
    <div class="risk-ramp-labels"><span>&lt;3</span><span>≥3</span><span>≥8</span><span>≥15</span></div>
    <p class="risk-ramp-note">Screening severity — not First Street / FEMA scores · not street-truth depths.</p>
  </div>
  <div class="access-fixture-badge" id="accessFixtureBadge" role="status"></div>
  <div id="assetBanner"></div>

  <section class="section assets-section" id="assetsSection">
    <h2>Briefing shortlist <span class="hint">j/k · enter</span></h2>
    <div id="deskSummary" class="metric"><span class="loading">Loading desk…</span><b>—</b></div>
    <div class="command-toolbar">
      <div class="seg-row" id="listModeChips" role="group" aria-label="List mode">
        <button type="button" class="seg active" data-mode="shortlist">Shortlist</button>
        <button type="button" class="seg" data-mode="all">All wet</button>
      </div>
      <div class="seg-row" id="typeChips" role="group" aria-label="Asset type">
        <button type="button" class="seg active" data-type="all">All</button>
        <button type="button" class="seg" data-type="road">Roads</button>
        <button type="button" class="seg" data-type="station">Sta</button>
        <button type="button" class="seg" data-type="facility">Fac</button>
      </div>
      <div class="filters">
        <div>
          <label class="caption" for="bandFilter">Depth band</label>
          <select id="bandFilter">
            <option value="all">All wet (≥3 cm)</option>
            <option value="ponding">≥3 cm</option>
            <option value="deep_ponding" selected>≥8 cm</option>
            <option value="hazard">≥15 cm</option>
          </select>
        </div>
        <div>
          <label class="caption" for="assetSearch">Search</label>
          <input id="assetSearch" type="search" placeholder="Name / id…" autocomplete="off">
        </div>
      </div>
    </div>
    <div class="asset-list" id="assetList" role="listbox" aria-label="Ranked wet assets" aria-busy="true"><div class="empty loading">Loading briefing cards…</div></div>
    <div class="shortlist-actions" role="group" aria-label="Shortlist snapshot">
      <button type="button" id="btnShareSnapshot">Copy decision log</button>
      <button type="button" id="btnPrintSnapshot">Print / share</button>
      <div class="status" id="snapshotStatus" aria-live="polite"></div>
    </div>
    <details class="drawer rail-compact" id="mapLayersDrawer">
      <summary>Map layers</summary>
      <div class="map-dot-toggles" role="group" aria-label="Map layer toggles">
        <label class="layer-btn"><input id="lyWet" type="checkbox" checked>Shortlist markers</label>
        <label class="layer-btn"><input id="lyTopHits" type="checkbox">Top-hit rings</label>
        <label class="layer-btn"><input id="lyFloodNet" type="checkbox">FloodNet</label>
        <label class="layer-btn"><input id="lyAccess" type="checkbox">DOT / access</label>
      </div>
      <label class="layer-btn"><input id="lyIncludeSchools" type="checkbox">All-mode: include schools / full inventory</label>
      <p class="drawer-note" style="margin-top:6px">Default map: depth + faint precip + shortlist. Access / FloodNet / corridors stay off until opted in.</p>
    </details>
  </section>

  <section class="section" id="floodnetPeaksPanel">
    <details class="drawer" id="floodnetDrawer">
      <summary>FloodNet peaks · all 5 Ida posts</summary>
      <p class="drawer-note">Post-level Ida OOM check — does not rescale citywide HAND. All five 2021 posts listed.</p>
      <div id="floodnetSummary" class="metric"><span>Loading…</span><b>—</b></div>
      <div id="floodnetMeta" class="metric" style="display:none"><span>Primary HAND @ posts</span><b>—</b></div>
      <label class="layer-btn"><input id="lyModelWrong" type="checkbox">Where model is wrong (FloodNet residuals)</label>
      <p class="drawer-note">Residual mode highlights posts where HAND≪street peak — trust-building, not a rescaled depth product.</p>
      <div class="floodnet-list" id="floodnetList" aria-label="FloodNet Ida peak comparison"><div class="empty">Loading sensor peaks…</div></div>
      <details class="drawer" id="floodnetLaterDrawer">
        <summary>Later FloodNet events</summary>
        <p class="drawer-note">Post-Ida Open Data archive (optional map layer). Research only.</p>
        <div id="floodnetLaterSummary" class="metric"><span>Loading…</span><b>—</b></div>
        <label class="layer-btn"><input id="lyFloodNetLater" type="checkbox">Show later FloodNet peaks</label>
      </details>
    </details>
  </section>

  <section class="section">
    <details class="drawer">
      <summary>Storm layers</summary>
      <div class="metric"><span>Path</span><b style="font-size:.66rem">MRMS QPE Ida</b></div>
      <div class="metric" id="timeWindowMetric"><span>Window</span><b style="font-size:.6rem" id="timeWindowVal">+0…+36h</b></div>
      <div class="storm-toggles">
        <label class="layer-btn"><input id="lyDepthTot" type="checkbox" checked>Depth</label>
        <label class="layer-btn"><input id="lyE2" type="checkbox" checked>Precip</label>
        <label class="layer-btn"><input id="lyStreets" type="checkbox" checked>Online streets</label>
      </div>
      <p class="drawer-note">Streets need network. Paper basemap + vendored Leaflet/fonts work offline for fixtures.</p>
      <div class="opacity-row"><span>Precip</span><input id="opPrecip" type="range" min="10" max="92" value="34"><span id="opPrecipVal">34%</span></div>
      <div class="opacity-row"><span>Depth</span><input id="opDepth" type="range" min="15" max="92" value="70"><span id="opDepthVal">70%</span></div>
      <div class="legend-swatch precip" title="Precip"></div>
      <div class="legend-swatch depth" title="Depth"></div>
      <span id="depthTimelineNote" hidden></span>
      <span id="pathHonesty" hidden></span>
    </details>
  </section>

  <section class="section">
    <details class="drawer" id="screeningDetails">
      <summary>Screening</summary>
      <p class="drawer-note">Real MRMS×terrain susceptibility frames (37). Uncalibrated — not probability or depth. Draws above Depth when on. Demo default: closed / off.</p>
      <div class="opacity-row"><span>Susc.</span><input id="opSusc" type="range" min="10" max="90" value="62"><span id="opSuscVal">62%</span></div>
      <div class="legend-swatch susc"></div>
      <label class="layer-btn"><input id="lySusc" type="checkbox">Show screening</label>
    </details>
  </section>

  <section class="section">
    <details class="drawer">
      <summary>Advanced · research only</summary>
      <p class="drawer-note">Research lab — not for 60s demo. Default stays shortlist + scrubber.</p>
      <details class="drawer">
        <summary>Event / path</summary>
        <div class="filters" style="grid-template-columns:1fr 1fr">
          <div><label class="caption" for="extentSelect">Extent</label><select id="extentSelect"></select></div>
          <div><label class="caption" for="eventSelect">Event</label><select id="eventSelect" title="Ida primary · Henri research second storm when parity is built"></select></div>
        </div>
        <p class="drawer-note" id="eventPickerNote">Henri Event switch enabled when parity is built (radar + official inventory + shortlist).</p>
        <label class="caption" for="stormPathSelect" style="margin-top:6px">Scenario path</label>
        <select id="stormPathSelect" aria-label="Scenario path"></select>
        <p class="drawer-note" id="liveMrmsNote">MRMS desk loops are fixture replay by default.</p>
      </details>
      <details class="drawer" id="corridorDetails">
        <summary>Corridor impassability (research)</summary>
        <p class="drawer-note">Three landmark <b>pairs</b> as distinct paths (not one loop). LION × HAND wet edges. <b>Not official DOT closures.</b></p>
        <p class="corridor-landmarks-note" id="corridorLandmarksNote"></p>
        <div id="corridorPairs" class="corridor-pairs" role="group" aria-label="Corridor landmark pairs"></div>
        <label class="layer-btn"><input id="lyCorridorWet" type="checkbox">Wet road edges (≥3 cm)</label>
        <label class="layer-btn"><input id="lyCorridorPath" type="checkbox" checked>Show all pair paths</label>
        <label class="layer-btn"><input id="lyCorridorLandmarks" type="checkbox" checked>Landmark endpoints</label>
        <p class="drawer-note" id="corridorHonesty"></p>
      </details>
      <details class="drawer">
        <summary>Advanced research hydro</summary>
        <p class="drawer-note">HAND stays primary — never blended. SFINCS = Advanced research 2D SWE with feathered nest↔coarse exchange + non-peer HAND overlap calib. <b>No SWMM</b> / no fake DEP pipes.</p>
        <p class="drawer-note" id="sfincsExchangeNote"></p>
        <div class="layer-grid">
          <label class="layer-btn"><input id="lySfincsNested" type="checkbox">Metro nested SFINCS</label>
          <label class="layer-btn"><input id="lySfincs" type="checkbox">SFINCS Queens nest</label>
          <label class="layer-btn"><input id="lyE2Tot" type="checkbox">Storm-total</label>
        </div>
      </details>
      <details class="drawer">
        <summary>Access feeds</summary>
        <p class="drawer-note">DOT / 511 / MTA overlay defaults <b>off</b> — enable under Map layers. Replay fixture joins are labeled synthetic.</p>
        <label class="layer-btn"><input id="lyAccessLive" type="checkbox">Prefer live DOT / 511 / MTA feeds</label>
        <div id="accessFeedStatus" class="drawer-note" style="margin-top:4px">Fixture default · Ida replay</div>
      </details>
      <details class="drawer">
        <summary>Official inventory overlays</summary>
        <p class="drawer-note">Open city inventory / planning layers — off by default. Stormwater ≠ Ida HAND depth.</p>
        <label class="layer-btn"><input id="lyStormwater" type="checkbox">Stormwater deep (moderate)</label>
        <label class="layer-btn"><input id="lyLionTun" type="checkbox">LION tunnels</label>
        <label class="layer-btn"><input id="lyBes" type="checkbox">BES elev / subgrade (sample)</label>
        <div id="inventoryLayersStatus" class="drawer-note" style="margin-top:4px">Load on toggle…</div>
      </details>
      <details class="drawer">
        <summary>Archived open layers</summary>
        <p class="drawer-note">Optional Open Data samples — off by default. Not sewer performance / not official closures.</p>
        <label class="layer-btn"><input id="lyArchive511" type="checkbox">Archived 511-style</label>
        <label class="layer-btn"><input id="lyDepBasins" type="checkbox">Open catch basins (dense sample)</label>
        <label class="layer-btn"><input id="lyBuildings" type="checkbox">Building footprints (sample)</label>
        <div id="archiveLayersStatus" class="drawer-note" style="margin-top:4px">Load on toggle…</div>
      </details>
      <details class="drawer">
        <summary>Exposure inventory</summary>
        <p class="drawer-note">Facilities DB + MTA stations replace demo stubs / OSM stops.</p>
        <div class="layer-grid">
          <label class="layer-btn"><input id="lySta" type="checkbox">Stations (MTA)</label>
          <label class="layer-btn"><input id="lyRoads" type="checkbox">Roads</label>
          <label class="layer-btn"><input id="lyFac" type="checkbox">Facilities (city DB)</label>
          <label class="layer-btn"><input id="ly311" type="checkbox">311</label>
        </div>
      </details>
      <details class="drawer">
        <summary>Context GIS</summary>
        <div class="layer-grid">
          <label class="layer-btn"><input id="lyFema" type="checkbox">FEMA NFHL</label>
          <label class="layer-btn"><input id="lyNwm" type="checkbox">NWM</label>
          <label class="layer-btn"><input id="lyGauges" type="checkbox">AHPS</label>
          <label class="layer-btn"><input id="lyBuilt" type="checkbox">Built</label>
        </div>
      </details>
      <div id="validationPanel" class="drawer-note" style="margin-top:8px">Limitations-first · exploratory only.</div>
    </details>
  </section>
  <div class="print-snapshot" id="printSnapshot" aria-hidden="true">
    <h1>Asset Decision Desk · shortlist snapshot</h1>
    <pre id="printSnapshotBody"></pre>
  </div>
  </div>
</aside>

<div class="map-stage" id="mapStage">
  <div class="pane-label" id="leftLabel">Decision Desk · Ida</div>
  <div class="view-mode-toggle" role="group" aria-label="Map view mode">
    <button type="button" id="viewMode2d" aria-pressed="true" title="Leaflet 2D map with precip and depth">2D</button>
    <button type="button" id="viewMode3d" aria-pressed="false" title="Street-level research 3D for selected hotspot">3D</button>
  </div>
  <div class="kbd-hint" aria-hidden="true"><kbd>c</kbd> compare · <kbd>←</kbd><kbd>→</kbd> scrub · <kbd>space</kbd> play · <kbd>esc</kbd> clear · <kbd>2</kbd>/<kbd>3</kbd> view</div>
  <div class="sfincs-peer-banner" id="sfincsPeerBanner">SFINCS on — non-peer metres vs HAND cm. HAND auto-dimmed. No SWMM.</div>
  <div id="mapLeft" class="map-el"></div>
  <aside class="inspector-dock" id="selectedCard" aria-label="Selected asset inspector" aria-hidden="true">
    <div class="inspector-empty" id="inspectorEmpty">
      Select a briefing card to open the inspector.<br>
      <span style="opacity:.75">Depth · Access · Context stay here — not a chip dump on the map.</span>
    </div>
    <div class="dock-head">
      <button type="button" class="sel-close" id="selClose" aria-label="Close inspector">×</button>
      <div class="sel-kicker" id="selKicker">Selected asset</div>
      <h3 id="selName">—</h3>
    </div>
    <div class="dock-body">
      <div class="sel-block">
        <div class="sel-block-label">Severity · depth</div>
        <div class="sel-depth-hero" id="selDepthHero">—</div>
        <div class="sel-depth-meta" id="selBody">—</div>
        <div class="sel-severity" id="selSeverity" aria-hidden="true">
          <div class="meter" title="Research band position"><i id="selSeverityFill" style="width:0%"></i></div>
          <div class="meter-label" id="selSeverityLabel">—</div>
        </div>
        <div class="sel-lead-grid">
          <div class="sel-stat">
            <div class="k">Lead</div>
            <div class="v" id="selLeadVal">—</div>
            <div class="s" id="selLeadSub">first band exceedance</div>
          </div>
          <div class="sel-stat">
            <div class="k">Access</div>
            <div class="v" id="selAccessVal">—</div>
            <div class="s" id="selAccessSub">research signal</div>
          </div>
        </div>
        <div class="sparkline-wrap" id="selSparkWrap" hidden>
          <div class="spark-cap">Depth vs lead (HAND cm)</div>
          <svg id="selSpark" viewBox="0 0 220 44" role="img" aria-label="Asset depth sparkline synced to timeline"></svg>
          <div class="spark-readout" id="selSparkReadout">—</div>
        </div>
      </div>
      <div class="sel-block">
        <div class="sel-block-label">Access · signals</div>
        <div class="sel-access-line" id="selAccessLine">—</div>
        <div class="sel-access-note" id="selAccessNote"></div>
      </div>
      <div class="sel-block">
        <div class="sel-block-label">Briefing · validation</div>
        <div class="sel-tag-row" id="selTags"></div>
        <div class="sel-chips" id="selChips"></div>
        <div class="compare-strip" id="selCompareStrip" hidden role="status"></div>
        <div class="consequence-cap">Consequence timeline (research)</div>
        <div class="consequence-line" id="selConsequence">—</div>
      </div>
      <button type="button" class="sel-street3d-btn" id="sv3dOpenBtn" hidden>
        Street view 3D · lead scrub
      </button>
      <div class="sel-hint" id="selHint"></div>
    </div>
  </aside>
  <div class="street-view-3d" id="streetView3d" hidden aria-hidden="true" role="dialog" aria-label="Street-level 3D hotspot view">
    <div class="sv-head">
      <div>
        <div class="sv-kicker">Street-level · research 3D</div>
        <h2 id="sv3dTitle">—</h2>
        <div class="sv-sub" id="sv3dSub">HAND/MRMS lead frames · not photogrammetry</div>
      </div>
      <button type="button" class="sv-close" id="sv3dClose" aria-label="Close 3D street view">×</button>
    </div>
    <div class="sv-stats" aria-live="polite">
      <div><span>Lead</span><b id="sv3dLead">+0h</b></div>
      <div><span>HAND depth</span><b id="sv3dDepth">0.0 cm</b></div>
      <div><span>Band</span><b id="sv3dBand">&lt;3 cm</b></div>
    </div>
    <div class="sv-map" id="sv3dMap" role="presentation"></div>
    <div class="sv-foot">
      <div id="sv3dHonesty">Research HAND cm screening in extruded context — NOT street-truth photogrammetry. FloodNet metres stay separate. SFINCS optional Advanced.</div>
      <div class="sv-status" id="sv3dStatus">Lazy-loads 3d_scene.json on open.</div>
    </div>
  </div>
  <div class="coach-overlay" id="coachOverlay" hidden>
    <div class="coach-card" role="dialog" aria-label="Decision Desk quick start">
      <strong>15s start</strong>
      Briefing card → inspector. <b>Compare</b> drag-line for lead hours. Risk ramp ≥3/≥8/≥15 cm. HAND cm ≠ FloodNet metres.
      <button type="button" id="coachDismiss">Got it</button>
    </div>
  </div>
  <div class="compare-shell" id="compareShell" aria-hidden="true">
    <div class="compare-chip left" id="compareChipL"><b id="compareLeadL">+6h</b><span class="sub">Earlier HAND cum</span></div>
    <div class="compare-chip right" id="compareChipR"><b id="compareLeadR">+18h</b><span class="sub">Later HAND cum</span></div>
    <div class="compare-divider" id="compareDivider" style="left:50%">
      <button type="button" class="compare-handle" id="compareHandle" aria-label="Drag to compare lead hours" title="Drag to compare">⟷</button>
    </div>
  </div>
  <div class="map-key-float collapsed" id="mapKeyFloat">
    <div class="map-key-float-head">
      <span>Key</span>
      <button type="button" id="mapKeyFloatToggle" aria-label="Expand map key" aria-expanded="false">+</button>
    </div>
    <div class="map-key-float-body">
      <div class="key-risk-ramp" aria-label="Depth severity ramp">
        <div class="map-legend-row"><span>HAND risk ramp</span></div>
        <div class="key-risk-track"></div>
        <div class="key-risk-labels"><span>&lt;3</span><span>≥3</span><span>≥8</span><span>≥15 cm</span></div>
      </div>
      <div class="map-legend-row">
        <span class="leg-sw" aria-hidden="true"><svg viewBox="0 0 14 14"><circle cx="7" cy="7" r="3.2" fill="#9a5a2a" stroke="rgba(255,255,255,.85)" stroke-width="1"/></svg></span>
        <span>Asset dot</span>
      </div>
      <div class="map-legend-row">
        <span class="leg-sw" aria-hidden="true"><svg viewBox="0 0 14 14"><circle cx="7" cy="7" r="5.2" fill="rgba(194,65,12,.06)" stroke="#c2410c" stroke-width="1.1" stroke-dasharray="2.4 2"/></svg></span>
        <span>Top hit</span>
      </div>
      <div class="map-legend-row">
        <span class="leg-sw" aria-hidden="true"><svg viewBox="0 0 14 14"><circle cx="7" cy="7" r="4.2" fill="#c2410c" stroke="#14161a" stroke-width="1.2"/></svg></span>
        <span>Selected</span>
      </div>
      <div class="map-legend-row key-corridor">
        <span class="leg-sw" aria-hidden="true"><svg viewBox="0 0 14 14"><line x1="1" y1="7" x2="13" y2="7" stroke="#0f766e" stroke-width="2" stroke-linecap="round"/></svg></span>
        <span>Corridor open</span>
      </div>
      <div class="map-legend-row key-corridor">
        <span class="leg-sw" aria-hidden="true"><svg viewBox="0 0 14 14"><line x1="1" y1="7" x2="13" y2="7" stroke="#9f1239" stroke-width="2" stroke-dasharray="2.5 2" stroke-linecap="round"/></svg></span>
        <span>Corridor cut</span>
      </div>
    </div>
  </div>
  <div class="timeline-hud" id="radarHud" role="region" aria-label="Storm timeline">
    <button type="button" class="play" id="hudPlay" aria-label="Play or pause storm loop">▶</button>
    <div>
      <div class="clock" id="hudClock">—</div>
      <div class="sub" id="hudSub">MRMS soft metro · +0…+36h · not NEXRAD</div>
    </div>
    <div class="legend">
      <span id="hudLegendLabel">Precip · context</span>
      <div class="bar" id="hudLegendBar"></div>
    </div>
    <button type="button" class="compare-toggle" id="compareToggle" aria-pressed="false" title="Drag-line lead compare">Compare</button>
    <div class="timeline-track">
      <div class="timeline-ticks" id="timelineTicks" aria-hidden="true"></div>
      <input class="scrub" id="hudScrub" type="range" min="0" max="{n - 1}" value="0" aria-label="Storm lead timeline">
    </div>
    <div class="compare-controls" id="compareControls" aria-label="Compare lead selectors">
      <label>A <select id="compareLeadA" aria-label="Earlier compare lead"></select></label>
      <label>B <select id="compareLeadB" aria-label="Later compare lead"></select></label>
      <button type="button" class="preset-btn" data-preset="buildup_peak">+6→+18</button>
      <button type="button" class="preset-btn" data-preset="early_late">+3→+24</button>
      <button type="button" class="preset-btn" data-preset="peak_recession">+18→+30</button>
      <span class="hint">Drag the line · HAND cum · research only</span>
    </div>
  </div>
</div>

<script src="vendor/leaflet/1.9.4/leaflet.js"></script>
<script src="vendor/maplibre/3.6.2/maplibre-gl.js"></script>
<script src="product_street_view_3d.js"></script>
<script>
const EVENTS = {json.dumps(EVENTS)};
const EXTENTS = {json.dumps(EXTENTS)};
const manifest = {json.dumps(manifest)};
const pluvial = {json.dumps(pluvial)};
const validation = {json.dumps(validation)};

function resolveAssetBase() {{
  const here = window.location.href;
  if (here.startsWith("file:")) {{
    const b = document.getElementById("assetBanner");
    if (b) {{
      b.style.display = "block";
      b.innerHTML = "<b>Open via local HTTP</b> — from repo: <code>python scripts/serve_product.py</code> then open the printed URL.";
    }}
  }}
  try {{ return new URL("product_assets/", here).href; }}
  catch (e) {{ return "product_assets/"; }}
}}
const assets = resolveAssetBase();

const mapLeft = L.map("mapLeft", {{ zoomControl: true }});
window.mapLeft = mapLeft;
mapLeft.createPane("rasterPane"); mapLeft.getPane("rasterPane").style.zIndex = 350;
mapLeft.createPane("depthPane"); mapLeft.getPane("depthPane").style.zIndex = 400;
// Screening above depth so "Show screening" is actually visible (was buried under Depth).
mapLeft.createPane("suscPane"); mapLeft.getPane("suscPane").style.zIndex = 450;
mapLeft.createPane("vectorPane"); mapLeft.getPane("vectorPane").style.zIndex = 650;
mapLeft.createPane("pointPane"); mapLeft.getPane("pointPane").style.zIndex = 670;
mapLeft.createPane("selectPane"); mapLeft.getPane("selectPane").style.zIndex = 700;
// Offline-safe paper basemap (no CDN tiles required for fixture demo).
const PaperBasemap = L.GridLayer.extend({{
  createTile: function () {{
    const tile = document.createElement("canvas");
    tile.width = tile.height = 256;
    const ctx = tile.getContext("2d");
    ctx.fillStyle = "#d9e3e8";
    ctx.fillRect(0, 0, 256, 256);
    ctx.strokeStyle = "rgba(8,40,52,.03)";
    for (let i = 0; i < 256; i += 32) {{
      ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, 256); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(256, i); ctx.stroke();
    }}
    return tile;
  }}
}});
const paperBasemap = new PaperBasemap({{ attribution: "Local paper basemap · offline fixtures" }});
paperBasemap.addTo(mapLeft);
const streetsBasemap = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}",
  {{ maxZoom: 19, attribution: "Tiles © Esri · optional online", opacity: 0.72 }}
);
// Online streets are optional; default on only when the browser reports online.
if (typeof navigator === "undefined" || navigator.onLine !== false) {{
  streetsBasemap.addTo(mapLeft);
}}

const DEMO_SHORTLIST = {demo_ids_json};
const DEMO_SHORTLIST_PATH = {shortlist_path_json};
const MAP_PAINT_TOP_N = 40;
const DECISION_FACILITY_TYPES = new Set(["hospital", "fire", "police"]);
const DECISION_HIGHWAYS = new Set(["motorway", "trunk", "primary", "secondary", "motorway_link", "trunk_link"]);
const AUTO_HIGHLIGHT_N = (manifest.asset_decision_desk && manifest.asset_decision_desk.auto_highlight_top_n) || 3;
const secondStorm = manifest.second_storm || {{}};
const henriParity = !!(secondStorm.parity || (manifest.asset_decision_desk && manifest.asset_decision_desk.henri_parity));
if (EVENTS["henri-2021"]) {{
  if (henriParity && secondStorm.available) {{
    EVENTS["henri-2021"].available = true;
    EVENTS["henri-2021"].label = "Henri remnants (2021-08-21) · research";
  }} else {{
    EVENTS["henri-2021"].available = false;
    EVENTS["henri-2021"].label = "Henri (hidden until parity)";
  }}
}}
const eventSel = document.getElementById("eventSelect");
Object.values(EVENTS).forEach(ev => {{
  if (!ev.available && ev.id !== "ida-2021") return;
  const opt = document.createElement("option");
  opt.value = ev.id; opt.textContent = ev.label;
  eventSel.appendChild(opt);
}});
eventSel.value = "ida-2021";
eventSel.disabled = !(henriParity && secondStorm.available);
if (!eventSel.disabled) {{
  eventSel.title = "Switch Ida ↔ Henri research replay (radar + desk + shortlist)";
}}
const extentSel = document.getElementById("extentSelect");
Object.values(EXTENTS).forEach(ex => {{
  const opt = document.createElement("option"); opt.value = ex.id; opt.textContent = ex.label; extentSel.appendChild(opt);
}});
extentSel.value = (manifest.layer_bounds && manifest.layer_bounds.map_extent_default) || "{DEFAULT_MAP_EXTENT}";

const stormPaths = manifest.storm_paths || [{{
  id: "mrms_qpe_ida", label: "MRMS QPE Ida", primary: true,
  precip: manifest.precip, susceptibility: manifest.susceptibility
}}];
const pathSel = document.getElementById("stormPathSelect");
stormPaths.forEach(p => {{
  const opt = document.createElement("option");
  const isIdaMrms = p.id === "mrms_qpe_ida" || p.ida_primary_viz;
  const isHenri = p.id === "mrms_qpe_henri" || p.henri_event_viz;
  opt.value = p.id;
  opt.textContent = p.label + (isIdaMrms ? " · Ida primary" : (isHenri ? " · Henri research" : " · AI scenario"));
  if (isHenri) opt.hidden = true; // selected via Event switch, not Advanced path menu
  pathSel.appendChild(opt);
}});
// Demo-locked default: Ida MRMS; Earth2 only via Advanced scenario path
pathSel.value = "mrms_qpe_ida";

function currentBounds() {{
  const b = (EXTENTS[extentSel.value] || EXTENTS.metro || EXTENTS.citywide).bounds;
  return [[b.ymin, b.xmin],[b.ymax, b.xmax]];
}}
/** Normalize overlay georef to Leaflet [[south,west],[north,east]]. */
function normalizeLeafletBounds(raw) {{
  if (!raw) return null;
  if (Array.isArray(raw) && raw.length === 2 && Array.isArray(raw[0]) && Array.isArray(raw[1])) {{
    const a = raw[0], b = raw[1];
    // Already [[lat,lon],[lat,lon]]
    if (a.length >= 2 && b.length >= 2) {{
      const south = Math.min(a[0], b[0]), north = Math.max(a[0], b[0]);
      const west = Math.min(a[1], b[1]), east = Math.max(a[1], b[1]);
      return [[south, west], [north, east]];
    }}
  }}
  if (typeof raw === "object") {{
    const xmin = raw.xmin ?? raw.west ?? raw.left;
    const xmax = raw.xmax ?? raw.east ?? raw.right;
    const ymin = raw.ymin ?? raw.south ?? raw.bottom;
    const ymax = raw.ymax ?? raw.north ?? raw.top;
    if ([xmin, xmax, ymin, ymax].every(v => v != null && Number.isFinite(Number(v)))) {{
      return [[Number(ymin), Number(xmin)], [Number(ymax), Number(xmax)]];
    }}
  }}
  return null;
}}
/** Native georef for data overlays — metro after DEM/MRMS rebuild; soft land mask (no painted box). */
function dataDomainBounds() {{
  const lb = manifest.layer_bounds || {{}};
  const fromMeta = normalizeLeafletBounds(lb.inundation)
    || normalizeLeafletBounds(lb.data_domain_bounds)
    || normalizeLeafletBounds(lb.precip)
    || normalizeLeafletBounds(manifest.inundation && manifest.inundation.bounds)
    || normalizeLeafletBounds(manifest.inundation_citywide && manifest.inundation_citywide.bounds);
  if (fromMeta) return fromMeta;
  const b = (EXTENTS.metro || EXTENTS.citywide).bounds;
  return [[b.ymin, b.xmin],[b.ymax, b.xmax]];
}}
function fitMapFrame() {{
  mapLeft.fitBounds(currentBounds(), {{ padding: [28, 28], maxZoom: 11, animate: false }});
}}
function precipOpacity() {{ return (+document.getElementById("opPrecip").value) / 100; }}
function suscOpacity() {{ return (+document.getElementById("opSusc").value) / 100; }}
function depthOpacity() {{ return (+document.getElementById("opDepth").value) / 100; }}

let activePath = stormPaths.find(p => p.id === pathSel.value) || stormPaths[0];
let frames = [], suscFrames = [], depthCumFrames = [], e2Layers = [], suscLayers = [], depthLayers = [];
let activeE2 = null, activeSusc = null, activeDepth = null, e2Total = null, depthTotal = null, sfincsLayer = null, sfincsNestedLayer = null;
let fadeE2 = null, fadeDepth = null, fadeSusc = null, fadeTimer = null;
let playing = false, playTimer = null, leadIndex = 0;
let viewMode = "2d"; // "2d" | "3d" — explicit toggle; 3D must not permanently kill precip
let activeOverlayBounds = null; // shared precip/depth/compare georef
let compareScrubSyncing = false;
let desk = null, deskGeoSource = null, wetLayer = null, selectedLayer = null, selectedId = null;
let highlightLayer = null, highlightIds = [];
let floodnetLayer = null, floodnetStations = [], selectedFloodnetId = null;
let floodnetLaterLayer = null;
let accessFixture = null, accessLayer = null, accessFeedMode = "fixture";
let archive511Layer = null, depBasinsLayer = null, buildingsLayer = null;
let stormwaterLayer = null, lionTunLayer = null, besLayer = null;
let corridorWetLayer = null, corridorPathLayer = null, corridorLandmarkLayer = null, corridorData = null;
let corridorPathGeo = null;
let corridorPairLayers = {{}}; // pairKey -> LayerGroup
const CORRIDOR_PAIR_PALETTE = [
  {{ cut: "#9f1239", open: "#0f766e", soft: "#7f1d1d" }},
  {{ cut: "#b45309", open: "#0e7490", soft: "#9a3412" }},
  {{ cut: "#7c2d12", open: "#115e59", soft: "#78350f" }},
];
let typeFilter = "all";
let deskLoadedMode = "none"; // shortlist | full
let fullDeskPromise = null;
let decisionLog = [];
let residualMode = false;
let listMode = "shortlist";
let activeEventId = "ida-2021";
let compareStrip = null;
let compareFramesMeta = null;
let compareOn = false;
let comparePct = 0.5;
let compareLeftLead = 6;
let compareRightLead = 18;
let compareLeftLayer = null;
let compareRightLayer = null;
let compareDragging = false;
let focusedAssetId = null;
let hoverAssetId = null;
const PLAY_MS = 380;
const FADE_MS = 220;
const RISK_BAND_CM = {{ ponding: 3, deep_ponding: 8, hazard: 15 }};

function setSelectionChrome(on) {{
  document.body.classList.toggle("has-selection", !!on);
  const dock = document.getElementById("selectedCard");
  if (!dock) return;
  dock.classList.toggle("open", !!on);
  dock.setAttribute("aria-hidden", on ? "false" : "true");
}}
function renderTimelineTicks() {{
  const el = document.getElementById("timelineTicks");
  if (!el) return;
  if (!frames.length) {{ el.innerHTML = ""; return; }}
  const leads = frames.map(f => f.lead_hours).filter(h => h != null);
  if (!leads.length) {{ el.innerHTML = ""; return; }}
  const minL = leads[0], maxL = leads[leads.length - 1];
  const marks = [minL];
  const mid = Math.round((minL + maxL) / 2);
  if (mid !== minL && mid !== maxL) marks.push(mid);
  if (maxL !== minL) marks.push(maxL);
  el.innerHTML = marks.map(h => "<span>+" + h + "h</span>").join("");
}}

function depthSetForPath(pathId) {{
  const inundation = manifest.inundation || null;
  if (!inundation) return null;
  const by = inundation.by_path || {{}};
  if (pathId && by[pathId]) return by[pathId];
  if (pathId && String(pathId).startsWith("earth2") && by.earth2_control) return by.earth2_control;
  if (by[inundation.default_depth_path]) return by[inundation.default_depth_path];
  return inundation;
}}

function overlayBoundsPreferMetro(explicit) {{
  const n = normalizeLeafletBounds(explicit);
  if (n) return n;
  return dataDomainBounds();
}}
/** Prefer metro PNG when storm_total lists both citywide + metro (same georef domain). */
function stormTotalPng(ds) {{
  if (!ds || !ds.storm_total) return null;
  const st = ds.storm_total;
  if (typeof st === "string") return st;
  return st.metro_png || st.png || null;
}}
function sharedOverlayBounds(pathObj, ds) {{
  const lb = manifest.layer_bounds || {{}};
  return overlayBoundsPreferMetro(
    (ds && ds.bounds)
    || (pathObj && pathObj.precip && pathObj.precip.bounds)
    || lb.inundation
    || lb.precip
    || lb.data_domain_bounds
  );
}}

function nearestDepthIndex(leadHours) {{
  if (!depthCumFrames.length) return -1;
  let best = 0, bestAbs = Infinity;
  depthCumFrames.forEach((fr, idx) => {{
    const d = Math.abs((fr.lead_hours || 0) - leadHours);
    if (d < bestAbs) {{ bestAbs = d; best = idx; }}
  }});
  return best;
}}
function precipIndexForLead(leadHours) {{
  if (!frames.length) return 0;
  let best = 0, bestAbs = Infinity;
  frames.forEach((fr, idx) => {{
    const d = Math.abs((fr.lead_hours || 0) - leadHours);
    if (d < bestAbs) {{ bestAbs = d; best = idx; }}
  }});
  return best;
}}
function exactDepthPngForLead(leadH) {{
  const di = nearestDepthIndex(leadH);
  if (di < 0 || !depthCumFrames[di]) return null;
  // Require the snapped lead to be the intended asset (no silent storm-total swap).
  return depthCumFrames[di].png || null;
}}
function snappedDepthLead(leadH) {{
  const di = nearestDepthIndex(leadH);
  if (di < 0 || !depthCumFrames[di]) return leadH;
  return Number(depthCumFrames[di].lead_hours);
}}

function syncTimeWindowLabel() {{
  const tw = (activePath.precip && activePath.precip.time_window)
    || manifest.time_window
    || null;
  const el = document.getElementById("timeWindowVal");
  if (!el) return;
  if (tw && tw.first_valid_time_utc && tw.last_valid_time_utc) {{
    el.textContent = "+" + tw.lead_hours_min + "…" + tw.lead_hours_max + "h · " +
      String(tw.first_valid_time_utc).replace("T"," ") + "→" + String(tw.last_valid_time_utc).slice(11);
  }} else if (frames.length) {{
    el.textContent = "+" + frames[0].lead_hours + "…" + frames[frames.length-1].lead_hours + "h";
  }} else {{
    el.textContent = "+6…+24h";
  }}
}}

function rebuildPathLayers() {{
  clearCompareLayers();
  [activeE2, fadeE2, activeSusc, fadeSusc, activeDepth, fadeDepth].forEach(l => {{
    if (l && mapLeft.hasLayer(l)) mapLeft.removeLayer(l);
  }});
  activeE2 = fadeE2 = activeSusc = fadeSusc = activeDepth = fadeDepth = null;
  e2Layers.forEach(l => mapLeft.removeLayer(l));
  suscLayers.forEach(l => mapLeft.removeLayer(l));
  depthLayers.forEach(l => mapLeft.removeLayer(l));
  if (e2Total) mapLeft.removeLayer(e2Total);
  if (depthTotal && mapLeft.hasLayer(depthTotal)) mapLeft.removeLayer(depthTotal);
  frames = activePath.precip?.frames || [];
  renderTimelineTicks();
  suscFrames = activePath.susceptibility?.frames || [];
  const ds = depthSetForPath(activePath.id);
  const overlayBounds = sharedOverlayBounds(activePath, ds);
  activeOverlayBounds = overlayBounds;
  const precipBounds = overlayBounds;
  const suscBounds = overlayBoundsPreferMetro(
    (activePath.susceptibility && activePath.susceptibility.bounds) || overlayBounds
  );
  e2Layers = frames.map(f => L.imageOverlay(assets + f.png, precipBounds, {{
    opacity: 0, interactive:false, pane:"rasterPane", className:"precip-radar"
  }}));
  suscLayers = suscFrames.map(f => L.imageOverlay(assets + f.png, suscBounds, {{
    opacity: 0, interactive:false, pane:"suscPane", className:"susc-radar"
  }}));
  // Prefetch a few radar frames so crossfades are less stuttery.
  frames.slice(0, 8).forEach(f => {{ const im = new Image(); im.src = assets + f.png; }});
  suscFrames.slice(0, 4).forEach(f => {{ const im = new Image(); im.src = assets + f.png; }});
  e2Total = activePath.precip?.storm_total_png
    ? L.imageOverlay(assets + activePath.precip.storm_total_png, precipBounds, {{
        opacity: precipOpacity(), pane:"rasterPane", interactive:false, className:"precip-radar"
      }})
    : null;
  const depthBounds = overlayBounds;
  depthCumFrames = (ds && ds.cumulative_frames) ? ds.cumulative_frames.slice() : [];
  depthLayers = depthCumFrames.map(fr => L.imageOverlay(assets + fr.png, depthBounds, {{
    opacity: 0, interactive:false, pane:"depthPane", className:"depth-radar"
  }}));
  const depthStormPng = stormTotalPng(ds)
    || (manifest.inundation_citywide && manifest.inundation_citywide.png)
    || null;
  depthTotal = depthStormPng
    ? L.imageOverlay(assets + depthStormPng, depthBounds, {{
        opacity: 0, interactive:false, pane:"depthPane", className:"depth-radar"
      }})
    : null;
  if (manifest.inundation_sfincs_nested && manifest.inundation_sfincs_nested.png) {{
    const nb = normalizeLeafletBounds(manifest.inundation_sfincs_nested.bounds)
      || overlayBounds;
    sfincsNestedLayer = L.imageOverlay(assets + manifest.inundation_sfincs_nested.png, nb, {{
      opacity: Math.min(depthOpacity(), 0.50), interactive:false, pane:"depthPane"
    }});
  }}
  if (manifest.inundation_sfincs && manifest.inundation_sfincs.png) {{
    const b = EXTENTS.south_queens?.bounds || EXTENTS.citywide.bounds;
    sfincsLayer = L.imageOverlay(assets + manifest.inundation_sfincs.png, [[b.ymin,b.xmin],[b.ymax,b.xmax]], {{
      opacity: Math.min(depthOpacity(), 0.55), interactive:false, pane:"depthPane"
    }});
  }}
  const pathHonestyEl = document.getElementById("pathHonesty");
  if (pathHonestyEl) {{
    if (activePath.primary || activePath.ida_primary_viz) {{
      pathHonestyEl.textContent = "Primary Ida awareness: soft-edge metro MRMS MultiSensor QPE (~1 km), native hourly 0–36h — not NEXRAD tiles.";
    }} else if (activePath.henri_event_viz || activePath.id === "mrms_qpe_henri") {{
      pathHonestyEl.textContent = activePath.honesty
        || "Henri MRMS MultiSensor QPE research replay (~1 km), native hourly 0–24h — not NEXRAD / not NWS.";
      pathHonestyEl.hidden = false;
    }} else {{
      pathHonestyEl.textContent = activePath.honesty || "Labeled AI / alternate scenario — coarse cells; not the decision surface.";
    }}
  }}
  const note = document.getElementById("depthTimelineNote");
  if (note) {{
    note.textContent = depthCumFrames.length
      ? ("Depth follows nearest cum lead (" + depthCumFrames.map(f => "+" + f.lead_hours + "h").join("/") +
         ") — buildup then post-peak recession. HAND puddles are heuristic, not street-truth.")
      : "Depth is storm-total only on this path (no cum frames) — label as static if it does not change with the loop.";
  }}
  syncTimeWindowLabel();
  populateCompareLeadSelects();
  // Prefer bilinear-ish for MRMS awareness; keep Earth2 pixelated if selected
  const nearest = !(
    activePath.ida_primary_viz
    || activePath.henri_event_viz
    || activePath.id === "mrms_qpe_ida"
    || activePath.id === "mrms_qpe_henri"
  );
  document.querySelectorAll(".leaflet-image-layer").forEach(el => {{
    el.style.imageRendering = nearest ? "pixelated" : "auto";
  }});
  if (compareOn) applyCompareLayers();
}}

function screeningOn() {{ return !!document.getElementById("lySusc").checked; }}
function effectiveDepthOpacity() {{
  const base = depthOpacity();
  return screeningOn() ? Math.min(base, 0.32) : base;
}}
function swapOverlay(prev, next, getOpacity, onDone) {{
  if (!next) {{
    if (prev && mapLeft.hasLayer(prev)) mapLeft.removeLayer(prev);
    onDone(null, null);
    return;
  }}
  if (prev === next) {{
    next.setOpacity(getOpacity());
    if (!mapLeft.hasLayer(next)) next.addTo(mapLeft);
    onDone(next, null);
    return;
  }}
  next.setOpacity(0);
  next.addTo(mapLeft);
  requestAnimationFrame(() => {{
    next.setOpacity(getOpacity());
    if (prev && mapLeft.hasLayer(prev)) prev.setOpacity(0);
  }});
  setTimeout(() => {{
    if (prev && mapLeft.hasLayer(prev) && prev !== next) mapLeft.removeLayer(prev);
  }}, FADE_MS);
  onDone(next, prev);
}}

function setLead(i) {{
  if (!frames.length) return;
  i = Math.max(0, Math.min(frames.length - 1, i));
  const f = frames[i];
  [i + 1, i + 2].forEach(j => {{
    const fr = frames[j % frames.length];
    if (fr) {{ const im = new Image(); im.src = assets + fr.png; }}
  }});

  const wantPrecip = document.getElementById("lyE2").checked;
  swapOverlay(activeE2, wantPrecip ? e2Layers[i] : null, precipOpacity, (a, fprev) => {{
    activeE2 = a; fadeE2 = fprev;
  }});

  const wantSusc = screeningOn() && !!suscLayers[i];
  swapOverlay(activeSusc, wantSusc ? suscLayers[i] : null, suscOpacity, (a, fprev) => {{
    activeSusc = a; fadeSusc = fprev;
  }});

  const di = nearestDepthIndex(f.lead_hours);
  const nextDepth = (di >= 0 && depthLayers[di]) ? depthLayers[di] : depthTotal;
  const wantDepth = document.getElementById("lyDepthTot").checked && !compareOn;
  swapOverlay(activeDepth, wantDepth ? nextDepth : null, effectiveDepthOpacity, (a, fprev) => {{
    activeDepth = a; fadeDepth = fprev;
  }});

  if (document.getElementById("lySfincsNested")?.checked && sfincsNestedLayer) {{
    if (!mapLeft.hasLayer(sfincsNestedLayer)) sfincsNestedLayer.addTo(mapLeft);
  }}
  if (document.getElementById("lySfincs").checked && sfincsLayer) {{
    if (!mapLeft.hasLayer(sfincsLayer)) sfincsLayer.addTo(mapLeft);
  }}
  if (document.getElementById("lyE2Tot").checked && e2Total) {{
    e2Total.setOpacity(precipOpacity());
    if (!mapLeft.hasLayer(e2Total)) e2Total.addTo(mapLeft);
  }}
  leadIndex = i;
  try {{ window.leadIndex = leadIndex; window.frames = frames; }} catch (err) {{}}
  const scrub = document.getElementById("hudScrub");
  if (scrub) {{ scrub.max = Math.max(frames.length - 1, 0); scrub.value = String(i); }}
  const clock = (f.valid_time || "").replace("T", " ");
  document.getElementById("hudClock").textContent = clock + " UTC";
  const depthLead = (di >= 0 && depthCumFrames[di]) ? depthCumFrames[di].lead_hours : null;
  const depthBit = depthLead != null ? (" · depth +" + depthLead + "h") : "";
  const suscBit = wantSusc ? " · screening on" : "";
  if (compareOn) {{
    // Keep Compare B (right) locked to the same HAND cum asset as the scrubbed flood depth.
    if (!compareScrubSyncing && !compareDragging) {{
      const snapped = snappedDepthLead(f.lead_hours);
      if (snapped !== compareRightLead && snapped >= compareLeftLead) {{
        compareScrubSyncing = true;
        compareRightLead = snapped;
        const bSel = document.getElementById("compareLeadB");
        if (bSel) bSel.value = String(compareRightLead);
        applyCompareLayers();
        compareScrubSyncing = false;
      }} else {{
        refreshCompareClip();
      }}
    }} else {{
      refreshCompareClip();
    }}
    document.getElementById("hudSub").textContent =
      "Compare +" + compareLeftLead + "h ↔ +" + compareRightLead + "h · HAND cum · research only";
  }} else {{
    document.getElementById("hudSub").textContent =
      "+" + f.lead_hours + "h · 3h cum screening frames · " + (f.temporal_blend ? "blend" : "native") + depthBit + suscBit;
  }}
  document.getElementById("leftLabel").textContent = "Decision Desk · " + (activePath.label || "Ida");
  syncSparklineToScrubber();
  if (window.StreetView3D) {{
    try {{ window.StreetView3D.syncToLead(f.lead_hours); }} catch (err) {{}}
  }}
}}

function setPlaying(on) {{
  playing = on;
  const btn = document.getElementById("hudPlay");
  if (btn) {{
    btn.textContent = on ? "❚❚" : "▶";
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  }}
  const hud = document.getElementById("radarHud");
  if (hud) hud.classList.toggle("playing", !!on);
  if (playTimer) {{ clearInterval(playTimer); playTimer = null; }}
  if (!on || !frames.length) return;
  playTimer = setInterval(() => {{
    leadIndex = (leadIndex + 1) % frames.length;
    setLead(leadIndex);
  }}, PLAY_MS);
}}

function bandClass(band) {{ return band || "ponding"; }}
function leadLabel(a) {{
  if (a.first_exceedance_lead_h != null) return "band @ +" + a.first_exceedance_lead_h + "h";
  if (a.first_exceedance_note) return "storm-total / late";
  return "lead n/a";
}}
function typeLabel(t) {{
  if (t === "road") return "Road";
  if (t === "station") return "Station";
  if (t === "facility") return "Facility";
  return t;
}}
function accessStatus(a) {{
  return (a && a.access_status) ? a.access_status : "open";
}}
function accessChipLabel(status) {{
  if (status === "limited") return "access: limited (research)";
  if (status === "watch") return "access: watch (research)";
  return "access: open (research)";
}}
function isUnnamedAsset(a) {{
  const name = String(a.name || "").trim().toLowerCase();
  return name.startsWith("unnamed ") || !name;
}}
function isDecisionClassAsset(a) {{
  if (!a || isUnnamedAsset(a)) return false;
  if (a.decision_class === true) return true;
  if (a.decision_class === false) return false;
  if (a.asset_type === "station") return true;
  if (a.asset_type === "facility") return DECISION_FACILITY_TYPES.has(String(a.facility_type || "").toLowerCase());
  if (a.asset_type === "road") {{
    const hwy = String(a.highway || "").toLowerCase();
    const name = String(a.name || "").toLowerCase();
    if (DECISION_HIGHWAYS.has(hwy)) return true;
    if (a.near_lion_tunnel) return true;
    return ["tunnel", "expressway", "parkway", "boulevard", "bridge"].some(k => name.includes(k));
  }}
  return false;
}}
function includeSchools() {{
  const el = document.getElementById("lyIncludeSchools");
  return !!(el && el.checked);
}}
function filteredAssets() {{
  if (!desk || !desk.assets) return [];
  const q = (document.getElementById("assetSearch").value || "").trim().toLowerCase();
  const band = document.getElementById("bandFilter").value;
  let rows = desk.assets.filter(a => {{
    if (typeFilter !== "all" && a.asset_type !== typeFilter) return false;
    if (band !== "all" && a.band !== band) return false;
    if (q && !(String(a.name).toLowerCase().includes(q) || String(a.id).toLowerCase().includes(q))) return false;
    return true;
  }});
  if (listMode === "shortlist" && !q) {{
    const byId = Object.fromEntries((desk.assets || []).map(a => [a.id, a]));
    const curated = DEMO_SHORTLIST.map(id => byId[id]).filter(Boolean);
    // Shortlist ignores band filter so demo rows always appear; numbers still honest.
    if (curated.length) return curated;
  }}
  if (listMode === "all" && !includeSchools() && !q) {{
    rows = rows.filter(isDecisionClassAsset);
  }}
  return rows;
}}
function mapPaintAssets() {{
  const byId = Object.fromEntries((desk.assets || []).map(a => [a.id, a]));
  const shortlist = DEMO_SHORTLIST.map(id => byId[id]).filter(Boolean);
  const seen = new Set();
  const out = [];
  // Default: shortlist markers only. Top-hit rings also unlock ranked wet top-N.
  shortlist.forEach(a => {{
    if (!a || seen.has(a.id)) return;
    seen.add(a.id);
    out.push(a);
  }});
  if (topHitsEnabled()) {{
    (desk.assets || []).filter(isDecisionClassAsset).slice(0, MAP_PAINT_TOP_N).forEach(a => {{
      if (!a || seen.has(a.id)) return;
      seen.add(a.id);
      out.push(a);
    }});
  }}
  if (selectedId && byId[selectedId] && !seen.has(selectedId)) out.push(byId[selectedId]);
  return out;
}}
function visibleBriefingRows() {{
  return filteredAssets().slice(0, listMode === "shortlist" ? 12 : 120);
}}
function syncBriefingHover(id) {{
  hoverAssetId = id || null;
  document.querySelectorAll(".briefing-card").forEach(btn => {{
    btn.classList.toggle("is-hover", !!id && btn.dataset.id === id);
  }});
  if (!wetLayer) return;
  wetLayer.eachLayer(layer => {{
    const lid = layer.feature && layer.feature.properties && layer.feature.properties.id;
    const el = layer.getElement && layer.getElement();
    if (el) el.classList.toggle("is-hover", !!id && lid === id);
    if (typeof layer.setStyle !== "function") return;
    if (layer instanceof L.CircleMarker) {{
      const base = (lid === selectedId) ? 7 : 3.4;
      layer.setRadius(!!id && lid === id ? base + 1.6 : base);
    }}
  }});
}}
function focusBriefing(id, opts) {{
  const scroll = !opts || opts.scroll !== false;
  focusedAssetId = id || null;
  const cards = [...document.querySelectorAll(".briefing-card")];
  cards.forEach(btn => {{
    const on = btn.dataset.id === id;
    btn.classList.toggle("is-focused", on);
    if (on) btn.setAttribute("aria-selected", selectedId === id ? "true" : "false");
    else if (btn.dataset.id !== selectedId) btn.removeAttribute("aria-selected");
  }});
  if (scroll && id) {{
    const el = cards.find(c => c.dataset.id === id);
    if (el && el.scrollIntoView) el.scrollIntoView({{ block: "nearest", behavior: "smooth" }});
  }}
}}
function moveBriefingFocus(delta) {{
  const rows = visibleBriefingRows();
  if (!rows.length) return;
  const ids = rows.map(a => a.id);
  let idx = focusedAssetId ? ids.indexOf(focusedAssetId) : -1;
  if (idx < 0 && selectedId) idx = ids.indexOf(selectedId);
  if (idx < 0) idx = delta > 0 ? -1 : 0;
  idx = Math.max(0, Math.min(ids.length - 1, idx + delta));
  focusBriefing(ids[idx]);
  syncBriefingHover(ids[idx]);
}}
function renderAssetList() {{
  const list = document.getElementById("assetList");
  const rows = visibleBriefingRows();
  list.setAttribute("aria-busy", "false");
  if (!rows.length) {{
    const loading = !desk;
    list.innerHTML = loading
      ? '<div class="empty loading">Loading briefing cards…</div>'
      : '<div class="empty">No wet assets match.<br>Clear band filter, switch to Shortlist, or enable schools / full inventory.</div>';
    return;
  }}
  list.innerHTML = rows.map(a => {{
    const acc = accessStatus(a);
    const accPill = (acc === "limited" || acc === "watch")
      ? `<span class="access-pill ${{acc}}">${{acc}}</span>` : "";
    const topHit = highlightIds.includes(a.id) ? " top-hit" : "";
    const selected = selectedId === a.id ? " selected" : "";
    const hovered = hoverAssetId === a.id ? " is-hover" : "";
    const focused = focusedAssetId === a.id ? " is-focused" : "";
    return `
    <button type="button" role="option" class="briefing-card${{selected}}${{topHit}}${{hovered}}${{focused}}" data-id="${{a.id}}" aria-selected="${{selectedId === a.id ? "true" : "false"}}">
      <div class="card-top">
        <span class="rank">#${{a.rank != null ? a.rank : "—"}}</span>
        <span class="name">${{a.name}}</span>
        <span class="depth">${{Number(a.max_depth_cm || 0).toFixed(1)}} cm</span>
      </div>
      <div class="card-meta">
        <span class="type-pill">${{typeLabel(a.asset_type)}}</span>
        <span class="band ${{bandClass(a.band)}}">${{a.band_label}}</span>
        <span class="lead-bit">${{leadLabel(a)}}</span>
        ${{accPill}}
      </div>
    </button>`;
  }}).join("");
  list.querySelectorAll(".briefing-card").forEach(btn => {{
    btn.addEventListener("click", () => selectAsset(btn.dataset.id));
    btn.addEventListener("mouseenter", () => {{ focusBriefing(btn.dataset.id, {{ scroll: false }}); syncBriefingHover(btn.dataset.id); }});
    btn.addEventListener("mouseleave", () => {{ if (hoverAssetId === btn.dataset.id) syncBriefingHover(null); }});
    btn.addEventListener("focus", () => focusBriefing(btn.dataset.id, {{ scroll: false }}));
  }});
  if (focusedAssetId && !rows.some(a => a.id === focusedAssetId)) focusedAssetId = null;
  if (selectedId) focusBriefing(selectedId, {{ scroll: false }});
}}
function depthSeriesForAsset(a) {{
  if (!a) return {{ leads: [], vals: [] }};
  const leads = (a.depth_series_leads_h && a.depth_series_leads_h.length)
    ? a.depth_series_leads_h.slice()
    : ((desk && desk.lead_frames_h) || []).slice();
  const vals = (a.depth_series_cm && a.depth_series_cm.length)
    ? a.depth_series_cm.slice()
    : [];
  return {{ leads, vals }};
}}
function nearestSeriesIndex(leads, leadHours) {{
  if (!leads.length) return -1;
  let best = 0, bestAbs = Infinity;
  leads.forEach((h, idx) => {{
    const d = Math.abs((h || 0) - leadHours);
    if (d < bestAbs) {{ bestAbs = d; best = idx; }}
  }});
  return best;
}}
function renderSparkline(a) {{
  const wrap = document.getElementById("selSparkWrap");
  const svg = document.getElementById("selSpark");
  const readout = document.getElementById("selSparkReadout");
  if (!wrap || !svg || !readout) return;
  const {{ leads, vals }} = depthSeriesForAsset(a);
  if (!leads.length || vals.length !== leads.length) {{
    wrap.hidden = true;
    svg.innerHTML = "";
    readout.textContent = "—";
    return;
  }}
  wrap.hidden = false;
  const w = 220, h = 44, pad = 4;
  const maxV = Math.max(1, ...vals, a.max_depth_cm || 0);
  const xs = leads.map((_, i) => pad + (i / Math.max(leads.length - 1, 1)) * (w - pad * 2));
  const ys = vals.map(v => h - pad - (v / maxV) * (h - pad * 2));
  const poly = xs.map((x, i) => x.toFixed(1) + "," + ys[i].toFixed(1)).join(" ");
  // Band thresholds as faint guides (3 / 8 / 15 cm)
  const guides = [3, 8, 15].filter(t => t < maxV).map(t => {{
    const y = h - pad - (t / maxV) * (h - pad * 2);
    return `<line x1="${{pad}}" y1="${{y.toFixed(1)}}" x2="${{w - pad}}" y2="${{y.toFixed(1)}}" stroke="rgba(8,40,52,.1)" stroke-width="1"/>`;
  }}).join("");
  svg.innerHTML = guides +
    `<polyline fill="none" stroke="#c2410c" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" points="${{poly}}"/>` +
    `<circle id="sparkCursor" cx="${{xs[0]}}" cy="${{ys[0]}}" r="3.2" fill="#b45309" stroke="#fff" stroke-width="1.2"/>`;
  syncSparklineToScrubber();
}}
function syncSparklineToScrubber() {{
  const a = selectedId && desk ? (desk.assets || []).find(x => x.id === selectedId) : null;
  const svg = document.getElementById("selSpark");
  const readout = document.getElementById("selSparkReadout");
  const cursor = document.getElementById("sparkCursor");
  if (!a || !svg || !readout || !cursor) return;
  const {{ leads, vals }} = depthSeriesForAsset(a);
  if (!leads.length || vals.length !== leads.length) return;
  const leadHours = (frames[leadIndex] && frames[leadIndex].lead_hours != null)
    ? frames[leadIndex].lead_hours
    : 0;
  const idx = nearestSeriesIndex(leads, leadHours);
  if (idx < 0) return;
  const w = 220, h = 44, pad = 4;
  const maxV = Math.max(1, ...vals, a.max_depth_cm || 0);
  const x = pad + (idx / Math.max(leads.length - 1, 1)) * (w - pad * 2);
  const y = h - pad - (vals[idx] / maxV) * (h - pad * 2);
  cursor.setAttribute("cx", x.toFixed(1));
  cursor.setAttribute("cy", y.toFixed(1));
  readout.textContent = "+" + leads[idx] + "h · " + Number(vals[idx]).toFixed(1) + " cm (scrubber)";
}}

function selectAsset(id) {{
  selectedId = id;
  focusedAssetId = id;
  const a = (desk.assets || []).find(x => x.id === id);
  if (!a) return;
  renderAssetList();
  if (selectedLayer) {{ mapLeft.removeLayer(selectedLayer); selectedLayer = null; }}
  const ll = [a.lat, a.lon];
  mapLeft.flyTo(ll, Math.max(mapLeft.getZoom(), 14), {{ duration: 0.75 }});
  // Prefer geometry from wet layer if present
  let geomLayer = null;
  if (wetLayer) {{
    wetLayer.eachLayer(l => {{
      if (l.feature && l.feature.properties && l.feature.properties.id === id) geomLayer = l;
    }});
  }}
  if (geomLayer && geomLayer.feature && geomLayer.feature.geometry && geomLayer.feature.geometry.type !== "Point") {{
    // Quiet line-through selection: dark underlay + accent stroke.
    selectedLayer = L.layerGroup([
      L.geoJSON(geomLayer.feature, {{
        pane: "selectPane",
        style: {{ color:"#14161a", weight:6.5, opacity:0.28, lineCap:"round", lineJoin:"round" }}
      }}),
      L.geoJSON(geomLayer.feature, {{
        pane: "selectPane",
        style: {{ color:"#c2410c", weight:2.8, opacity:0.95, lineCap:"round", lineJoin:"round", dashArray:"6 4" }}
      }}),
    ]).addTo(mapLeft);
  }} else {{
    selectedLayer = L.circleMarker(ll, {{
      pane: "selectPane", radius: 7, color:"#14161a", weight:1.5,
      fillColor:"#c2410c", fillOpacity:0.94
    }}).addTo(mapLeft);
  }}
  const acc = accessStatus(a);
  // Access overlay stays opt-in (Map layers) — dock still shows access status.
  document.getElementById("selKicker").textContent = typeLabel(a.asset_type) + " · #" + (a.rank != null ? a.rank : "—");
  document.getElementById("selName").textContent = a.name;
  const depthCm = Number(a.max_depth_cm || 0);
  const depthHero = document.getElementById("selDepthHero");
  if (depthHero) depthHero.textContent = depthCm.toFixed(1) + " cm";
  document.getElementById("selBody").textContent =
    (a.band_full_label || a.band_label || a.band || "—") + " · HAND primary · research only";
  renderSeverityMeter(a);
  const leadVal = document.getElementById("selLeadVal");
  const leadSub = document.getElementById("selLeadSub");
  if (leadVal) {{
    leadVal.textContent = a.first_exceedance_lead_h != null
      ? ("+" + a.first_exceedance_lead_h + "h")
      : "late / n/a";
  }}
  if (leadSub) {{
    leadSub.textContent = a.first_exceedance_note
      ? String(a.first_exceedance_note).slice(0, 42)
      : "first band exceedance";
  }}
  const accVal = document.getElementById("selAccessVal");
  const accSub = document.getElementById("selAccessSub");
  if (accVal) accVal.textContent = acc;
  if (accSub) accSub.textContent = accessChipLabel(acc).replace("access: ", "");
  const accessLine = document.getElementById("selAccessLine");
  if (accessLine) {{
    accessLine.innerHTML = `<span class="sel-chip access-${{acc}}">${{accessChipLabel(acc)}}</span>`;
  }}
  renderValidationTags(a);
  const extraChips = [];
  if (a.structure) extraChips.push(`<span class="sel-chip">Structure · ${{a.structure}}</span>`);
  if (a.stormwater_chip) extraChips.push(`<span class="sel-chip">${{a.stormwater_chip}}</span>`);
  if (a.lion_chip) extraChips.push(`<span class="sel-chip">${{a.lion_chip}}</span>`);
  if (a.bes_chip) extraChips.push(`<span class="sel-chip">${{a.bes_chip}}</span>`);
  if (a.near_lion_tunnel) extraChips.push(`<span class="sel-chip">Near tunnel inventory</span>`);
  if (a.facility_type) extraChips.push(`<span class="sel-chip">${{a.facility_type}}</span>`);
  const ec = a.engine_compare || null;
  if (ec) {{
    const cls = ec.disagree ? "disagree" : "agree";
    extraChips.push(`<span class="sel-chip ${{cls}}" title="${{(ec.hover || "").replace(/"/g, "&quot;")}}">${{ec.chip}}</span>`);
  }}
  document.getElementById("selChips").innerHTML = extraChips.length
    ? extraChips.join("")
    : `<span class="sel-chip">${{a.band_label || "HAND context"}}</span>`;
  document.getElementById("selHint").textContent = a.action_hint ||
    "Research depth only — not an SOP trigger.";
  const sigs = (a.access_signals || []).map(s => s.label || s.source).filter(Boolean);
  document.getElementById("selAccessNote").textContent = sigs.length
    ? ("Signals: " + sigs.slice(0, 2).join(" · ") + " — not official closures.")
    : "Access overlay optional under Map layers — not official closures.";
  renderSparkline(a);
  renderConsequenceTimeline(a);
  renderCompareStrip(a);
  appendDecisionLog(a, "select");
  setSelectionChrome(true);
  if (window.StreetView3D) {{
    try {{
      window.selectedId = selectedId;
      window.StreetView3D.maybeOfferButton(id);
      // Do not auto-open 3D — use the explicit 2D|3D toggle (or inspector button).
      if (viewMode === "3d" && window.StreetView3D.canOpenId(id)) {{
        window.StreetView3D.open(id);
      }}
    }} catch (err) {{}}
  }}
  requestAnimationFrame(() => {{
    try {{ mapLeft.invalidateSize({{ animate: false }}); }} catch (err) {{}}
    if (compareOn) refreshCompareClip();
  }});
}}
function severityPct(a) {{
  const cm = Number(a && a.max_depth_cm != null ? a.max_depth_cm : 0);
  // Map 0–18 cm onto the research ramp so ≥15 sits near the end.
  return Math.max(4, Math.min(100, (cm / 18) * 100));
}}
function renderSeverityMeter(a) {{
  const fill = document.getElementById("selSeverityFill");
  const label = document.getElementById("selSeverityLabel");
  const wrap = document.getElementById("selSeverity");
  if (!fill || !label || !wrap) return;
  wrap.setAttribute("aria-hidden", "false");
  fill.style.width = severityPct(a).toFixed(0) + "%";
  label.textContent = a.band_label || ("≥" + (RISK_BAND_CM[a.band] || 3) + " cm");
}}
function renderValidationTags(a) {{
  const el = document.getElementById("selTags");
  if (!el || !a) return;
  const tags = [];
  tags.push('<span class="sel-tag muted">HAND primary</span>');
  tags.push('<span class="sel-tag muted">research · not NWS</span>');
  if (a.band_label) tags.push(`<span class="sel-tag">${{a.band_label}}</span>`);
  if (a.demo_demoted) tags.push('<span class="sel-tag warn">demo-demoted rank</span>');
  if (a.decision_class) tags.push('<span class="sel-tag ok">decision-class asset</span>');
  const ec = a.engine_compare;
  if (ec) {{
    tags.push(ec.disagree
      ? '<span class="sel-tag warn">engines disagree · non-peer</span>'
      : '<span class="sel-tag ok">engines agree · non-peer</span>');
  }} else {{
    tags.push('<span class="sel-tag muted">SFINCS Advanced only</span>');
  }}
  if (a.sample_method) tags.push(`<span class="sel-tag muted">${{a.sample_method}}</span>`);
  el.innerHTML = tags.join("");
}}
function renderConsequenceTimeline(a) {{
  const el = document.getElementById("selConsequence");
  if (!el || !a) return;
  const lead = a.first_exceedance_lead_h != null ? ("band first @" + a.first_exceedance_lead_h + "h") : "lead n/a";
  const acc = accessStatus(a);
  const ec = a.engine_compare;
  const eng = ec
    ? (ec.disagree
      ? ("HAND " + (ec.hand_cm != null ? ec.hand_cm + " cm" : "cm") + " vs SFINCS " + (ec.sfincs_m != null ? ec.sfincs_m + " m" : "n/a") + " · non-peer")
      : "engines agree on wetness · non-peer magnitudes")
    : "engine compare n/a";
  const nearestFn = () => {{
    if (!floodnetStations.length) return "FloodNet nearest n/a";
    let best = null, bestD = Infinity;
    floodnetStations.forEach(s => {{
      const lon = s.lon != null ? s.lon : (s.geometry && s.geometry.coordinates && s.geometry.coordinates[0]);
      const lat = s.lat != null ? s.lat : (s.geometry && s.geometry.coordinates && s.geometry.coordinates[1]);
      if (lon == null || lat == null) return;
      const d = Math.hypot(Number(lon) - Number(a.lon), Number(lat) - Number(a.lat));
      if (d < bestD) {{ bestD = d; best = s; }}
    }});
    if (!best) return "FloodNet nearest n/a";
    const obs = best.obs_peak_m != null ? Number(best.obs_peak_m).toFixed(2) + " m" : "—";
    const hand = best.primary_hand_m != null ? Number(best.primary_hand_m).toFixed(2) + " m"
      : (best.model_peak_m != null ? Number(best.model_peak_m).toFixed(2) + " m" : "HAND —");
    return "nearest FloodNet obs " + obs + " / HAND " + hand + " (not blended)";
  }};
  el.textContent = lead + " · access " + acc + " · " + eng + " · " + nearestFn();
}}

function clearSelection() {{
  selectedId = null;
  if (selectedLayer) {{ mapLeft.removeLayer(selectedLayer); selectedLayer = null; }}
  setSelectionChrome(false);
  const wrap = document.getElementById("selSparkWrap");
  if (wrap) wrap.hidden = true;
  const cmp = document.getElementById("selCompareStrip");
  if (cmp) {{ cmp.hidden = true; cmp.innerHTML = ""; }}
  const hero = document.getElementById("selDepthHero");
  if (hero) hero.textContent = "—";
  const tags = document.getElementById("selTags");
  if (tags) tags.innerHTML = "";
  const fill = document.getElementById("selSeverityFill");
  if (fill) fill.style.width = "0%";
  ["selLeadVal", "selAccessVal", "selSeverityLabel"].forEach(id => {{
    const el = document.getElementById(id);
    if (el) el.textContent = "—";
  }});
  renderAssetList();
  requestAnimationFrame(() => {{
    try {{ mapLeft.invalidateSize({{ animate: false }}); }} catch (err) {{}}
    if (compareOn) refreshCompareClip();
  }});
}}

function buildShortlistSnapshotText() {{
  const rows = filteredAssets().slice(0, listMode === "shortlist" ? 12 : 12);
  const f = frames[leadIndex] || {{}};
  const lead = f.lead_hours != null ? f.lead_hours : "—";
  const clock = (f.valid_time || "").replace("T", " ") || "—";
  const sel = selectedId && desk ? (desk.assets || []).find(x => x.id === selectedId) : null;
  const lines = [
    "Asset Decision Desk · research decision log",
    "Research only · NOT NWS · NOT decision-grade · fixture ida_v1",
    "Event: " + activeEventId + " · scrubber +" + lead + "h · " + clock + " UTC",
    "Band filter: " + (document.getElementById("bandFilter").value || "—") +
      " · list: " + listMode + " · desk: " + deskLoadedMode,
    "",
    "Visible shortlist / rows (" + rows.length + "):",
  ];
  rows.forEach(a => {{
    const ec = a.engine_compare ? (" · " + a.engine_compare.chip) : "";
    lines.push(
      "#" + a.rank + " · " + a.name + " · " + a.max_depth_cm.toFixed(1) + " cm · " +
      a.band_label + " · " + leadLabel(a) + " · access " + accessStatus(a) + ec
    );
  }});
  if (sel) {{
    const {{ leads, vals }} = depthSeriesForAsset(sel);
    const idx = nearestSeriesIndex(leads, Number(lead) || 0);
    const at = (idx >= 0 && vals[idx] != null) ? (Number(vals[idx]).toFixed(1) + " cm @" + leads[idx] + "h") : "n/a";
    lines.push("");
    lines.push("Selected: " + sel.name + " · storm-total " + sel.max_depth_cm.toFixed(1) + " cm · at scrubber " + at);
    lines.push("Hint: " + (sel.action_hint || "research only"));
    if (sel.engine_compare) lines.push("Engine: " + sel.engine_compare.chip + " — " + (sel.engine_compare.hover || "non-peer"));
  }}
  lines.push("");
  lines.push("Inspect log (" + decisionLog.length + "):");
  decisionLog.slice(-12).forEach(e => {{
    lines.push(
      e.t + " · " + e.reason + " · " + e.name + " · " + Number(e.depth_cm).toFixed(1) + " cm · access " +
      e.access + (e.engine_chip ? (" · " + e.engine_chip) : "")
    );
  }});
  lines.push("");
  lines.push("FloodNet Ida posts: " + (floodnetStations.length || 0) + " surfaced in panel.");
  return lines.join("\\n");
}}
function setSnapshotStatus(msg) {{
  const el = document.getElementById("snapshotStatus");
  if (el) el.textContent = msg || "";
}}
async function copyShortlistSnapshot() {{
  const text = buildShortlistSnapshotText();
  try {{
    await navigator.clipboard.writeText(text);
    setSnapshotStatus("Snapshot copied.");
  }} catch (err) {{
    setSnapshotStatus("Copy blocked — use Print / share.");
  }}
  const body = document.getElementById("printSnapshotBody");
  if (body) body.textContent = text;
}}
function printShortlistSnapshot() {{
  const text = buildShortlistSnapshotText();
  const body = document.getElementById("printSnapshotBody");
  if (body) body.textContent = text;
  window.print();
}}

function deskPathsForEvent(eventId, mode) {{
  const deskCfg = manifest.asset_decision_desk || {{}};
  const events = deskCfg.events || {{}};
  const want = mode || "shortlist";
  const ev = (eventId && events[eventId]) ? events[eventId] : null;
  if (ev) {{
    if (want === "shortlist") {{
      return {{
        assets_json: ev.shortlist_json || ev.assets_json,
        assets_geojson: ev.shortlist_geojson || ev.assets_geojson,
        mode: "shortlist",
        full_json: ev.assets_json,
        full_geojson: ev.assets_geojson,
        storm_path_id: ev.storm_path_id,
      }};
    }}
    return {{
      assets_json: ev.assets_json,
      assets_geojson: ev.assets_geojson,
      mode: "full",
      storm_path_id: ev.storm_path_id,
    }};
  }}
  if (eventId === "henri-2021" && secondStorm && secondStorm.desk) {{
    const d = secondStorm.desk;
    if (want === "shortlist") {{
      return {{
        assets_json: d.shortlist_json || "decision_desk_shortlist_henri.json",
        assets_geojson: d.shortlist_geojson || "decision_desk_shortlist_henri.geojson",
        mode: "shortlist",
        full_json: d.assets_json || "decision_desk_assets_henri.json",
        full_geojson: d.assets_geojson || "decision_desk_assets_henri.geojson",
        storm_path_id: secondStorm.storm_path_id || "mrms_qpe_henri",
      }};
    }}
    return {{
      assets_json: d.assets_json || "decision_desk_assets_henri.json",
      assets_geojson: d.assets_geojson || "decision_desk_assets_henri.geojson",
      mode: "full",
      storm_path_id: secondStorm.storm_path_id || "mrms_qpe_henri",
    }};
  }}
  if (want === "shortlist") {{
    return {{
      assets_json: deskCfg.shortlist_json || "decision_desk_shortlist.json",
      assets_geojson: deskCfg.shortlist_geojson || "decision_desk_shortlist.geojson",
      mode: "shortlist",
      full_json: deskCfg.assets_json || "decision_desk_assets.json",
      full_geojson: deskCfg.assets_geojson || "decision_desk_assets.geojson",
      storm_path_id: "mrms_qpe_ida",
    }};
  }}
  return {{
    assets_json: deskCfg.assets_json || "decision_desk_assets.json",
    assets_geojson: deskCfg.assets_geojson || "decision_desk_assets.geojson",
    mode: "full",
    storm_path_id: "mrms_qpe_ida",
  }};
}}
function stormPathIdForEvent(eventId) {{
  const paths = deskPathsForEvent(eventId, "shortlist");
  return paths.storm_path_id || (eventId === "henri-2021" ? "mrms_qpe_henri" : "mrms_qpe_ida");
}}
function applyStormPathForEvent(eventId) {{
  const want = stormPathIdForEvent(eventId);
  const next = stormPaths.find(p => p.id === want) || stormPaths.find(p => p.primary) || stormPaths[0];
  activePath = next;
  // Keep Advanced path select in sync for Ida/Earth2; Henri path stays hidden there.
  if (pathSel && next && (next.id === "mrms_qpe_ida" || String(next.id || "").startsWith("earth2"))) {{
    pathSel.value = next.id;
  }}
  rebuildPathLayers();
  setLead(0);
}}
async function loadCompareStrip() {{
  const name = (manifest.ida_henri_compare && manifest.ida_henri_compare.json)
    || (manifest.asset_decision_desk && manifest.asset_decision_desk.compare_strip_json)
    || "ida_henri_compare_strip.json";
  try {{
    const r = await fetch(assets + name, {{ cache: "no-cache" }});
    compareStrip = r.ok ? await r.json() : null;
  }} catch (e) {{
    compareStrip = null;
  }}
}}
function renderCompareStrip(a) {{
  const el = document.getElementById("selCompareStrip");
  if (!el) return;
  if (!a || !compareStrip || !compareStrip.shortlist) {{
    el.hidden = true;
    el.innerHTML = "";
    return;
  }}
  const row = (compareStrip.shortlist || []).find(r => r.id === a.id)
    || (compareStrip.shared_wet_sample || []).find(r => r.id === a.id);
  if (!row || row.present_in === "neither") {{
    el.hidden = true;
    el.innerHTML = "";
    return;
  }}
  const idaBit = (row.ida_cm != null && row.ida_cm !== "")
    ? ("<b>" + row.ida_cm + " cm</b> Ida") : "Ida dry / n/a";
  const henriBit = (row.henri_cm != null && row.henri_cm !== "")
    ? ("<b>" + row.henri_cm + " cm</b> Henri") : "Henri dry / n/a";
  el.hidden = false;
  el.innerHTML = "<div class=\\"compare-kicker\\">Ida ↔ Henri compare</div>"
    + idaBit + " · " + henriBit
    + "<div style=\\"margin-top:4px;opacity:.85\\">Same official ID · research HAND — not peer-calibrated · not NWS.</div>";
}}

async function loadCompareFramesMeta() {{
  const name = (manifest.lead_compare && manifest.lead_compare.json)
    || "ida_lead_compare_frames.json";
  try {{
    const r = await fetch(assets + name, {{ cache: "no-cache" }});
    compareFramesMeta = r.ok ? await r.json() : null;
  }} catch (e) {{
    compareFramesMeta = null;
  }}
  if (compareFramesMeta) {{
    if (compareFramesMeta.default_left_lead_h != null) compareLeftLead = compareFramesMeta.default_left_lead_h;
    if (compareFramesMeta.default_right_lead_h != null) compareRightLead = compareFramesMeta.default_right_lead_h;
  }}
  populateCompareLeadSelects();
}}
function depthLeadOptions() {{
  if (depthCumFrames.length) {{
    return depthCumFrames.map(fr => Number(fr.lead_hours));
  }}
  return [0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36];
}}
function populateCompareLeadSelects() {{
  const a = document.getElementById("compareLeadA");
  const b = document.getElementById("compareLeadB");
  if (!a || !b) return;
  const leads = depthLeadOptions();
  const opts = leads.map(h => `<option value="${{h}}">+${{h}}h</option>`).join("");
  a.innerHTML = opts;
  b.innerHTML = opts;
  const snap = (sel, want) => {{
    const nums = leads.slice();
    let best = nums[0], bestAbs = Infinity;
    nums.forEach(h => {{
      const d = Math.abs(h - want);
      if (d < bestAbs) {{ bestAbs = d; best = h; }}
    }});
    sel.value = String(best);
    return best;
  }};
  compareLeftLead = snap(a, compareLeftLead);
  compareRightLead = snap(b, compareRightLead);
}}
function clearCompareLayers() {{
  [compareLeftLayer, compareRightLayer].forEach(l => {{
    if (l && mapLeft.hasLayer(l)) mapLeft.removeLayer(l);
  }});
  compareLeftLayer = compareRightLayer = null;
}}
function depthOverlayForLead(leadH) {{
  const di = nearestDepthIndex(leadH);
  if (di >= 0 && depthLayers[di]) return depthLayers[di];
  return depthTotal;
}}
function refreshCompareClip() {{
  if (!compareOn) return;
  const divider = document.getElementById("compareDivider");
  if (divider) divider.style.left = (comparePct * 100).toFixed(2) + "%";
  const mapRect = mapLeft.getContainer().getBoundingClientRect();
  const nx = mapRect.left + comparePct * mapRect.width;
  const clipLayer = (layer, side) => {{
    if (!layer) return;
    const img = layer.getElement ? layer.getElement() : null;
    if (!img) return;
    img.classList.add("compare-clip");
    const r = img.getBoundingClientRect();
    if (!r.width || !r.height) {{
      // Image may not be laid out yet — retry once after load.
      if (!img.dataset.compareClipBound) {{
        img.dataset.compareClipBound = "1";
        img.addEventListener("load", () => refreshCompareClip(), {{ once: true }});
      }}
      return;
    }}
    if (side === "left") {{
      const right = Math.max(0, Math.min(r.width, nx - r.left));
      img.style.clip = "rect(0px," + right + "px," + r.height + "px,0px)";
      img.style.clipPath = "inset(0 " + Math.max(0, r.width - right) + "px 0 0)";
    }} else {{
      const left = Math.max(0, Math.min(r.width, nx - r.left));
      img.style.clip = "rect(0px," + r.width + "px," + r.height + "px," + left + "px)";
      img.style.clipPath = "inset(0 0 0 " + left + "px)";
    }}
  }};
  clipLayer(compareLeftLayer, "left");
  clipLayer(compareRightLayer, "right");
}}
function syncCompareChips() {{
  const l = document.getElementById("compareLeadL");
  const r = document.getElementById("compareLeadR");
  if (l) l.textContent = "+" + compareLeftLead + "h";
  if (r) r.textContent = "+" + compareRightLead + "h";
}}
function syncScrubToCompareRight() {{
  if (!frames.length) return;
  compareScrubSyncing = true;
  const idx = precipIndexForLead(compareRightLead);
  setLead(idx);
  compareScrubSyncing = false;
}}
function applyCompareLayers() {{
  if (!compareOn) return;
  clearCompareLayers();
  // Snap L/R to actual HAND cum frame leads so chips match the flood depth assets.
  compareLeftLead = snappedDepthLead(compareLeftLead);
  compareRightLead = snappedDepthLead(compareRightLead);
  if (compareRightLead < compareLeftLead) {{
    const tmp = compareLeftLead;
    compareLeftLead = compareRightLead;
    compareRightLead = tmp;
  }}
  const aSel = document.getElementById("compareLeadA");
  const bSel = document.getElementById("compareLeadB");
  if (aSel) aSel.value = String(compareLeftLead);
  if (bSel) bSel.value = String(compareRightLead);
  const ds = depthSetForPath(activePath.id);
  const depthBounds = activeOverlayBounds
    || sharedOverlayBounds(activePath, ds);
  // Same lead assets as the normal depth timeline (depthCumFrames), never a mismatched total.
  const leftPng = exactDepthPngForLead(compareLeftLead) || stormTotalPng(ds);
  const rightPng = exactDepthPngForLead(compareRightLead) || stormTotalPng(ds);
  const op = Math.max(effectiveDepthOpacity(), 0.55);
  const mk = (png) => L.imageOverlay(assets + png, depthBounds, {{
    opacity: op, interactive: false, pane: "depthPane", className: "depth-radar compare-clip"
  }});
  if (leftPng) {{
    compareLeftLayer = mk(leftPng).addTo(mapLeft);
    compareLeftLayer.once("load", () => refreshCompareClip());
  }}
  if (rightPng) {{
    compareRightLayer = mk(rightPng).addTo(mapLeft);
    compareRightLayer.once("load", () => refreshCompareClip());
  }}
  syncCompareChips();
  requestAnimationFrame(() => {{
    refreshCompareClip();
    requestAnimationFrame(() => refreshCompareClip());
  }});
}}
function setCompareMode(on) {{
  compareOn = !!on;
  document.body.classList.toggle("compare-on", compareOn);
  const btn = document.getElementById("compareToggle");
  if (btn) btn.setAttribute("aria-pressed", compareOn ? "true" : "false");
  const shell = document.getElementById("compareShell");
  if (shell) shell.setAttribute("aria-hidden", compareOn ? "false" : "true");
  if (compareOn) {{
    if (viewMode === "3d") setViewMode("2d");
    setPlaying(false);
    // Keep precip checked — compare must not strip storm radar.
    const lyP = document.getElementById("lyE2");
    if (lyP) lyP.checked = true;
    // Hide the looping depth overlay so A/B frames own the depth pane.
    if (activeDepth && mapLeft.hasLayer(activeDepth)) {{
      activeDepth.setOpacity(0);
    }}
    document.getElementById("lyDepthTot").checked = true;
    populateCompareLeadSelects();
    applyCompareLayers();
    syncScrubToCompareRight();
    const key = document.getElementById("mapKeyFloat");
    if (key && key.classList.contains("collapsed")) {{
      key.classList.remove("collapsed");
      const t = document.getElementById("mapKeyFloatToggle");
      if (t) {{ t.textContent = "–"; t.setAttribute("aria-expanded", "true"); }}
    }}
    document.getElementById("hudSub").textContent =
      "Compare +" + compareLeftLead + "h ↔ +" + compareRightLead + "h · HAND cum · research only";
  }} else {{
    clearCompareLayers();
    document.querySelectorAll(".leaflet-image-layer.compare-clip").forEach(el => {{
      el.style.clip = "";
      el.style.clipPath = "";
      delete el.dataset.compareClipBound;
    }});
    setLead(leadIndex);
  }}
}}
function applyComparePreset(id) {{
  const presets = (compareFramesMeta && compareFramesMeta.presets) || [
    {{ id: "buildup_peak", left_lead_h: 6, right_lead_h: 18 }},
    {{ id: "early_late", left_lead_h: 3, right_lead_h: 24 }},
    {{ id: "peak_recession", left_lead_h: 18, right_lead_h: 30 }},
  ];
  const p = presets.find(x => x.id === id) || presets[0];
  if (!p) return;
  compareLeftLead = p.left_lead_h;
  compareRightLead = p.right_lead_h;
  populateCompareLeadSelects();
  document.querySelectorAll(".compare-controls .preset-btn").forEach(btn => {{
    btn.classList.toggle("active", btn.dataset.preset === id);
  }});
  if (compareOn) {{
    applyCompareLayers();
    syncScrubToCompareRight();
  }}
}}
function wireCompareUi() {{
  const toggle = document.getElementById("compareToggle");
  if (toggle) {{
    toggle.addEventListener("click", () => setCompareMode(!compareOn));
  }}
  const a = document.getElementById("compareLeadA");
  const b = document.getElementById("compareLeadB");
  if (a) a.addEventListener("change", () => {{
    compareLeftLead = Number(a.value);
    if (compareOn) {{
      applyCompareLayers();
      syncScrubToCompareRight();
    }}
  }});
  if (b) b.addEventListener("change", () => {{
    compareRightLead = Number(b.value);
    if (compareOn) {{
      applyCompareLayers();
      syncScrubToCompareRight();
    }}
  }});
  document.querySelectorAll(".compare-controls .preset-btn").forEach(btn => {{
    btn.addEventListener("click", () => applyComparePreset(btn.dataset.preset));
  }});
  const handle = document.getElementById("compareHandle");
  const stage = document.getElementById("mapStage");
  if (!handle || !stage) return;
  const onMove = (clientX) => {{
    const rect = mapLeft.getContainer().getBoundingClientRect();
    if (!rect.width) return;
    comparePct = Math.max(0.04, Math.min(0.96, (clientX - rect.left) / rect.width));
    refreshCompareClip();
  }};
  const stopDrag = () => {{
    compareDragging = false;
    window.removeEventListener("pointermove", onPtrMove);
    window.removeEventListener("pointerup", stopDrag);
  }};
  const onPtrMove = (e) => {{
    if (!compareDragging) return;
    onMove(e.clientX);
  }};
  handle.addEventListener("pointerdown", (e) => {{
    if (!compareOn || viewMode === "3d") return;
    e.preventDefault();
    compareDragging = true;
    handle.setPointerCapture?.(e.pointerId);
    onMove(e.clientX);
    window.addEventListener("pointermove", onPtrMove);
    window.addEventListener("pointerup", stopDrag);
  }});
  mapLeft.on("move zoom moveend zoomend resize", () => {{
    if (compareOn) refreshCompareClip();
  }});
  window.addEventListener("resize", () => {{ if (compareOn) refreshCompareClip(); }});
}}
function defaultHotspotIdFor3d() {{
  const hint = window.__streetViewOpenHint;
  if (hint) {{
    window.__streetViewOpenHint = null;
    if (!window.StreetView3D || window.StreetView3D.canOpenId(hint)) return hint;
  }}
  if (selectedId && window.StreetView3D && window.StreetView3D.canOpenId(selectedId)) return selectedId;
  if (selectedFloodnetId && window.StreetView3D && window.StreetView3D.canOpenId(selectedFloodnetId)) {{
    return selectedFloodnetId;
  }}
  // Smith–9 GTFS F22 is the demo hotspot when nothing is selected yet.
  return "stations:gtfs:F22";
}}
function syncViewModeButtons() {{
  const b2 = document.getElementById("viewMode2d");
  const b3 = document.getElementById("viewMode3d");
  if (b2) b2.setAttribute("aria-pressed", viewMode === "2d" ? "true" : "false");
  if (b3) b3.setAttribute("aria-pressed", viewMode === "3d" ? "true" : "false");
  document.body.classList.toggle("view-3d", viewMode === "3d");
}}
function restoreLeaflet2dAfter3d() {{
  // Re-assert precip/radar defaults and Leaflet timeline after leaving 3D.
  const lyP = document.getElementById("lyE2");
  if (lyP && !lyP.checked) lyP.checked = true;
  try {{ mapLeft.invalidateSize({{ animate: false }}); }} catch (err) {{}}
  if (frames.length) setLead(leadIndex);
  requestAnimationFrame(() => {{
    try {{ mapLeft.invalidateSize({{ animate: false }}); }} catch (err) {{}}
    if (compareOn) refreshCompareClip();
  }});
}}
function setViewMode(mode) {{
  const next = mode === "3d" ? "3d" : "2d";
  if (next === viewMode && next === "2d" && !(window.StreetView3D && window.StreetView3D.state && window.StreetView3D.state.open)) {{
    syncViewModeButtons();
    return;
  }}
  viewMode = next;
  syncViewModeButtons();
  if (viewMode === "3d") {{
    if (compareOn) setCompareMode(false);
    const hid = defaultHotspotIdFor3d();
    if (window.StreetView3D) {{
      try {{
        window.StreetView3D.open(hid);
      }} catch (err) {{
        console.warn("3D open failed", err);
        viewMode = "2d";
        syncViewModeButtons();
        restoreLeaflet2dAfter3d();
      }}
    }}
  }} else {{
    if (window.StreetView3D && window.StreetView3D.state && window.StreetView3D.state.open) {{
      try {{
        // close() fires onStreetViewClosed → restore; skip double restore below.
        window.__skipStreetViewRestore = true;
        window.StreetView3D.close();
        window.__skipStreetViewRestore = false;
      }} catch (err) {{
        window.__skipStreetViewRestore = false;
      }}
    }}
    restoreLeaflet2dAfter3d();
  }}
}}
window.setViewMode = setViewMode;
function wireViewModeToggle() {{
  const b2 = document.getElementById("viewMode2d");
  const b3 = document.getElementById("viewMode3d");
  if (b2) b2.addEventListener("click", () => setViewMode("2d"));
  if (b3) b3.addEventListener("click", () => setViewMode("3d"));
  document.addEventListener("keydown", (e) => {{
    if (e.target && /input|textarea|select/i.test(e.target.tagName)) return;
    if (e.key === "2" && !e.metaKey && !e.ctrlKey && !e.altKey) setViewMode("2d");
    if (e.key === "3" && !e.metaKey && !e.ctrlKey && !e.altKey) setViewMode("3d");
  }});
  // When 3D panel closes via × / Esc, snap toggle back to 2D and restore precip loop.
  window.onStreetViewClosed = function onStreetViewClosed() {{
    if (viewMode !== "2d") {{
      viewMode = "2d";
      syncViewModeButtons();
    }}
    if (window.__skipStreetViewRestore) return;
    restoreLeaflet2dAfter3d();
  }};
  syncViewModeButtons();
}}
function needsFullDesk() {{
  const q = (document.getElementById("assetSearch").value || "").trim();
  return listMode === "all" || includeSchools() || !!q;
}}
async function ensureFullDesk() {{
  if (deskLoadedMode === "full") return desk;
  if (fullDeskPromise) return fullDeskPromise;
  const paths = deskPathsForEvent(activeEventId, "full");
  fullDeskPromise = Promise.all([
    fetch(assets + paths.assets_json, {{ cache:"no-cache" }}).then(r => r.ok ? r.json() : null),
    fetch(assets + paths.assets_geojson, {{ cache:"no-cache" }}).then(r => r.ok ? r.json() : null),
  ]).then(([json, geo]) => {{
    if (!json) throw new Error("full desk missing");
    const keepId = selectedId;
    applyDeskPayload(json, geo, "full");
    if (keepId) selectAsset(keepId);
    return desk;
  }}).finally(() => {{ fullDeskPromise = null; }});
  return fullDeskPromise;
}}
function appendDecisionLog(a, reason) {{
  if (!a) return;
  const f = frames[leadIndex] || {{}};
  decisionLog.push({{
    t: new Date().toISOString(),
    reason: reason || "select",
    id: a.id,
    name: a.name,
    depth_cm: a.max_depth_cm,
    band: a.band,
    access: accessStatus(a),
    lead_h: a.first_exceedance_lead_h,
    scrubber_h: f.lead_hours,
    engine_chip: (a.engine_compare && a.engine_compare.chip) || null,
    hint: a.action_hint || null,
  }});
  if (decisionLog.length > 40) decisionLog = decisionLog.slice(-40);
}}

function topHighlightTargets() {{
  const byId = Object.fromEntries((desk.assets || []).map(a => [a.id, a]));
  const curated = DEMO_SHORTLIST.map(id => byId[id]).filter(Boolean);
  if (curated.length) return curated.slice(0, AUTO_HIGHLIGHT_N);
  // Henri / non-Ida: deepest NYC-preferred wet assets
  return (desk.assets || []).filter(a => a.nyc_demo_geography !== false).slice(0, AUTO_HIGHLIGHT_N);
}}

function topHitsEnabled() {{
  const el = document.getElementById("lyTopHits");
  return !el || el.checked;
}}
function wetAssetsEnabled() {{
  const el = document.getElementById("lyWet");
  return !el || el.checked;
}}
function syncWetLayerVisibility() {{
  if (!wetLayer) return;
  if (wetAssetsEnabled()) {{
    if (!mapLeft.hasLayer(wetLayer)) wetLayer.addTo(mapLeft);
  }} else if (mapLeft.hasLayer(wetLayer)) {{
    mapLeft.removeLayer(wetLayer);
  }}
}}
function applyAutoHighlight(selectFirst) {{
  if (highlightLayer) {{ mapLeft.removeLayer(highlightLayer); highlightLayer = null; }}
  const tops = topHighlightTargets();
  highlightIds = tops.map(a => a.id);
  if (!tops.length) {{
    renderAssetList();
    return;
  }}
  const feats = tops.map(a => ({{
    type: "Feature",
    properties: {{ id: a.id, name: a.name, band: a.band }},
    geometry: {{ type: "Point", coordinates: [a.lon, a.lat] }}
  }}));
  highlightLayer = L.geoJSON({{ type: "FeatureCollection", features: feats }}, {{
    pane: "selectPane",
    pointToLayer: (f, ll) => L.circleMarker(ll, {{
      radius: 8.5, color: "#c2410c", weight: 1.25, dashArray: "2.5 2.2",
      fillColor: "#c2410c", fillOpacity: 0.04, pane: "selectPane", opacity: 0.85
    }}),
    onEachFeature: (f, layer) => {{
      layer.bindTooltip("Top hit · " + (f.properties.name || ""));
      layer.on("click", () => selectAsset(f.properties.id));
    }}
  }});
  if (topHitsEnabled()) highlightLayer.addTo(mapLeft);
  renderAssetList();
  if (selectFirst) selectAsset(tops[0].id);
}}

function applyDeskPayload(json, geo, mode) {{
  desk = json;
  deskLoadedMode = mode || (json.bundle ? "shortlist" : "full");
  const c = json.counts || {{}};
  const label = activeEventId === "henri-2021" ? "Wet · Henri HAND" : "Wet · metro HAND";
  const bundleBit = deskLoadedMode === "shortlist" ? " · shortlist bundle" : "";
  const modeNote = listMode === "all" && !includeSchools() ? " · decision classes" : "";
  document.getElementById("deskSummary").innerHTML =
    `<span>${{label}}${{bundleBit}}${{modeNote}}</span><b>${{c.wet_total||0}} · R${{c.roads||0}} S${{c.stations||0}} F${{c.facilities||0}}</b>`;
  const leftLabel = document.getElementById("leftLabel");
  if (leftLabel) leftLabel.textContent = activeEventId === "henri-2021"
    ? "Decision Desk · Henri" : "Decision Desk · Ida";
  const accMeta = json.access_signals || {{}};
  const badge = document.getElementById("accessFixtureBadge");
  if (badge) {{
    const nJoin = accMeta.joined_assets != null ? accMeta.joined_assets : "—";
    badge.dataset.fullText = "Replay fixture (synthetic joins labeled) · ida_v1 · joined " + nJoin +
      (accMeta.fixture_pack ? (" · " + accMeta.fixture_pack) : "");
    badge.textContent = badge.dataset.fullText;
    syncAccessFixtureBadge();
  }}
  deskGeoSource = geo || null;
  renderAssetList();
  rebuildWetLayer();
  rebuildAccessOverlay();
}}
function syncAccessFixtureBadge() {{
  const badge = document.getElementById("accessFixtureBadge");
  if (!badge) return;
  const on = document.getElementById("lyAccess") && document.getElementById("lyAccess").checked;
  if (on && badge.dataset.fullText) {{
    badge.style.display = "block";
    badge.textContent = badge.dataset.fullText;
  }} else {{
    badge.style.display = "none";
  }}
}}
function rebuildWetLayer() {{
  if (!desk) return;
  if (wetLayer) {{ mapLeft.removeLayer(wetLayer); wetLayer = null; }}
  const sourceFeats = (deskGeoSource && deskGeoSource.features) ? deskGeoSource.features
    : (desk.assets || []).map(a => ({{
        type: "Feature",
        properties: a,
        geometry: {{ type: "Point", coordinates: [a.lon, a.lat] }}
      }}));
  const paintIds = new Set(mapPaintAssets().map(a => a.id));
  const filteredGeo = {{
    type: "FeatureCollection",
    features: sourceFeats.filter(f => paintIds.has((f.properties || {{}}).id))
  }};
  wetLayer = L.geoJSON(filteredGeo, {{
    pane: "vectorPane",
    style: f => {{
      const band = f.properties && f.properties.band;
      const color = band === "hazard" ? "#8f3a3a" : band === "deep_ponding" ? "#9a5a2a" : "#7a6a2e";
      return {{ color, weight: 3, opacity: 0.72 }};
    }},
    pointToLayer: (f, ll) => {{
      const band = f.properties && f.properties.band;
      const ft = (f.properties && f.properties.facility_type) || "";
      const color = (ft === "school") ? "#94a3b8"
        : band === "hazard" ? "#8f3a3a" : band === "deep_ponding" ? "#9a5a2a" : "#7a6a2e";
      return L.circleMarker(ll, {{
        radius: 3.4, color: "rgba(255,255,255,.92)", weight: 1,
        fillColor: color, fillOpacity: 0.9, pane: "pointPane", opacity: 0.95
      }});
    }},
    onEachFeature: (f, layer) => {{
      const id = f.properties && f.properties.id;
      layer.on("click", () => selectAsset(id));
      layer.on("mouseover", () => {{ syncBriefingHover(id); focusBriefing(id, {{ scroll: true }}); }});
      layer.on("mouseout", () => {{ if (hoverAssetId === id) syncBriefingHover(null); }});
      layer.bindTooltip((f.properties.name || "") + " · " + (f.properties.band_label || ""));
    }}
  }});
  syncWetLayerVisibility();
}}
function loadDecisionDesk() {{
  const mode = needsFullDesk() ? "full" : "shortlist";
  const paths = deskPathsForEvent(activeEventId, mode);
  if (highlightLayer) {{ mapLeft.removeLayer(highlightLayer); highlightLayer = null; }}
  highlightIds = [];
  clearSelection();
  Promise.all([
    fetch(assets + paths.assets_json, {{ cache:"no-cache" }}).then(r => r.ok ? r.json() : null),
    fetch(assets + paths.assets_geojson, {{ cache:"no-cache" }}).then(r => r.ok ? r.json() : null),
  ]).then(([json, geo]) => {{
    if (!json) {{
      // Fall back to full desk if shortlist bundle missing
      if (mode === "shortlist") {{
        return loadDecisionDeskFullFallback();
      }}
      document.getElementById("assetList").innerHTML = '<div class="empty">Desk assets missing for ' + activeEventId + ' — run build scripts.</div>';
      return;
    }}
    applyDeskPayload(json, geo, paths.mode || mode);
    applyAutoHighlight(true);
  }}).catch(err => {{
    document.getElementById("assetList").innerHTML = '<div class="empty">Failed to load desk assets.</div>';
    const b = document.getElementById("assetBanner");
    if (b) {{ b.style.display="block"; b.textContent = String(err); }}
  }});
}}
function loadDecisionDeskFullFallback() {{
  const paths = deskPathsForEvent(activeEventId, "full");
  return Promise.all([
    fetch(assets + paths.assets_json, {{ cache:"no-cache" }}).then(r => r.ok ? r.json() : null),
    fetch(assets + paths.assets_geojson, {{ cache:"no-cache" }}).then(r => r.ok ? r.json() : null),
  ]).then(([json, geo]) => {{
    if (!json) {{
      document.getElementById("assetList").innerHTML = '<div class="empty">Desk assets missing — run build scripts.</div>';
      return;
    }}
    applyDeskPayload(json, geo, "full");
    applyAutoHighlight(true);
  }});
}}

async function fetchGeoJSON(path) {{
  const r = await fetch(assets + path, {{ cache:"no-cache" }});
  if (!r.ok) throw new Error(path + " HTTP " + r.status);
  return r.json();
}}
function accessKindClass(kind) {{
  if (kind === "limited" || kind === "closure") return "limited";
  if (kind === "watch" || kind === "slow") return "watch";
  return "open";
}}
function accessSourceLabel(source) {{
  if (source === "nyc_dot_speeds") return "NYC DOT speed";
  if (source === "nysdot_511_events" || source === "nyc_street_closures") return "511-style event";
  if (source === "mta_alerts") return "MTA alert";
  return source || "Access signal";
}}
function accessDivIcon(source, kind) {{
  const k = accessKindClass(kind);
  let cls = "access-marker ";
  let label = "";
  if (source === "nyc_dot_speeds") {{
    cls += "dot" + (k === "limited" ? " limited" : "");
    label = "DOT";
  }} else if (source === "nysdot_511_events" || source === "nyc_street_closures") {{
    cls += "ev511" + (k === "limited" ? " limited" : "");
    label = "511";
  }} else {{
    cls += "mta" + (k === "limited" ? " limited" : k === "watch" ? " watch" : "");
    label = "MTA";
  }}
  return L.divIcon({{
    className: "access-div",
    html: `<div class="${{cls}}" title="${{accessSourceLabel(source)}}">${{label}}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  }});
}}
function rebuildAccessOverlay() {{
  if (accessLayer) {{ mapLeft.removeLayer(accessLayer); accessLayer = null; }}
  const on = document.getElementById("lyAccess") && document.getElementById("lyAccess").checked;
  if (!on || !accessFixture) return;
  const feats = [];
  (accessFixture.dot_speeds || []).forEach(sp => {{
    if (sp.lon == null || sp.lat == null) return;
    const limited = sp.speed_ratio != null && Number(sp.speed_ratio) < 0.35;
    const ratio = sp.speed_ratio != null ? (" · " + Math.round(Number(sp.speed_ratio) * 100) + "% free-flow") : "";
    feats.push({{
      type: "Feature",
      properties: {{
        kind: limited ? "limited" : "watch",
        label: (sp.label || "DOT speed") + ratio,
        source: "nyc_dot_speeds",
      }},
      geometry: {{ type: "Point", coordinates: [sp.lon, sp.lat] }}
    }});
  }});
  (accessFixture.events_511 || []).forEach(ev => {{
    if (ev.lon == null || ev.lat == null) return;
    feats.push({{
      type: "Feature",
      properties: {{
        kind: ev.closure ? "limited" : "watch",
        label: ev.label || "511 event",
        source: ev.source || "nysdot_511_events",
      }},
      geometry: {{ type: "Point", coordinates: [ev.lon, ev.lat] }}
    }});
  }});
  (accessFixture.mta_alerts || []).forEach(al => {{
    const ids = al.asset_ids || [];
    ids.forEach(aid => {{
      const a = (desk && desk.assets || []).find(x => x.id === aid);
      if (!a) return;
      feats.push({{
        type: "Feature",
        properties: {{ kind: al.access || "watch", label: al.label || "MTA alert", source: "mta_alerts" }},
        geometry: {{ type: "Point", coordinates: [a.lon, a.lat] }}
      }});
    }});
  }});
  if (!feats.length) return;
  accessLayer = L.geoJSON({{ type: "FeatureCollection", features: feats }}, {{
    pane: "selectPane",
    pointToLayer: (f, ll) => L.marker(ll, {{
      icon: accessDivIcon(f.properties.source, f.properties.kind),
      pane: "selectPane",
      keyboard: false,
    }}),
    onEachFeature: (f, layer) => {{
      const src = accessSourceLabel(f.properties.source);
      const kind = accessKindClass(f.properties.kind);
      layer.bindTooltip(src + " · " + kind + " · " + (f.properties.label || ""));
    }}
  }}).addTo(mapLeft);
}}
function setAccessFeedStatus(text) {{
  const el = document.getElementById("accessFeedStatus");
  if (el) el.textContent = text;
}}
function loadAccessSignals() {{
  const deskCfg = manifest.asset_decision_desk || {{}};
  const fixtureName = deskCfg.access_signals_fixture || "access_signals_ida_fixture.json";
  const liveName = deskCfg.access_signals_live || "access_signals_live.json";
  const preferLive = document.getElementById("lyAccessLive") && document.getElementById("lyAccessLive").checked;
  const primary = preferLive ? liveName : fixtureName;
  const fallback = preferLive ? fixtureName : null;
  fetch(assets + primary, {{ cache: "no-cache" }}).then(r => r.ok ? r.json() : null).then(fx => {{
    if (fx) {{
      accessFixture = fx;
      accessFeedMode = preferLive ? ((fx.live_status && fx.live_status.mode) || fx.mode || "live") : "fixture";
      const nDot = (fx.dot_speeds || []).length;
      const n511 = (fx.events_511 || []).length;
      const nMta = (fx.mta_alerts || []).length;
      if (preferLive) {{
        setAccessFeedStatus(
          accessFeedMode === "fixture_fallback"
            ? "Live failed · fixture fallback"
            : ("Live · " + nDot + " speeds · " + n511 + " closures · " + nMta + " alerts")
        );
      }} else {{
        setAccessFeedStatus(
          "Fixture · Ida · " + nDot + " DOT · " + n511 + " closures · " + nMta + " MTA (shapes on map)"
        );
      }}
      rebuildAccessOverlay();
      return;
    }}
    if (!fallback) {{ accessFixture = null; setAccessFeedStatus("No access fixture"); return; }}
    return fetch(assets + fallback, {{ cache: "no-cache" }}).then(r => r.ok ? r.json() : null).then(fb => {{
      accessFixture = fb;
      accessFeedMode = "fixture_fallback";
      setAccessFeedStatus("Live missing · fixture fallback");
      rebuildAccessOverlay();
    }});
  }}).catch(() => {{
    if (!fallback) {{ accessFixture = null; return; }}
    fetch(assets + fallback, {{ cache: "no-cache" }}).then(r => r.ok ? r.json() : null).then(fb => {{
      accessFixture = fb;
      accessFeedMode = "fixture_fallback";
      setAccessFeedStatus("Live error · fixture fallback");
      rebuildAccessOverlay();
    }});
  }});
}}
function bindToggle(id, layer) {{
  const el = document.getElementById(id);
  if (!el || !layer) return;
  const sync = () => {{
    if (el.checked) layer.addTo(mapLeft); else if (mapLeft.hasLayer(layer)) mapLeft.removeLayer(layer);
  }};
  el.addEventListener("change", sync);
  if (el.checked) sync();
}}
function loadOptionalLayers() {{
  const built = pluvial?.built_surface_png
    ? L.imageOverlay(assets + pluvial.built_surface_png, currentBounds(), {{ opacity:0.45, pane:"rasterPane", interactive:false }})
    : null;
  bindToggle("lyBuilt", built);

  fetchGeoJSON(manifest.infra?.roads_geojson || "roads.geojson").then(geo => {{
    bindToggle("lyRoads", L.geoJSON(geo, {{ pane:"vectorPane", style: {{ color:"#ff6b00", weight:2.5, opacity:0.7 }} }}));
  }}).catch(()=>{{}});
  fetchGeoJSON(manifest.infra?.stations_geojson || "subway_stations.geojson").then(geo => {{
    bindToggle("lySta", L.geoJSON(geo, {{
      pointToLayer: (f,ll) => L.circleMarker(ll, {{ radius:5, fillColor:"#00e5a8", color:"#004d40", weight:1, fillOpacity:0.9, pane:"pointPane" }})
    }}));
  }}).catch(()=>{{}});
  fetchGeoJSON("critical_facilities.geojson").then(geo => {{
    bindToggle("lyFac", L.geoJSON(geo, {{
      pointToLayer: (f,ll) => L.circleMarker(ll, {{ radius:6, fillColor:"#c45c26", color:"#7c2d12", weight:1, fillOpacity:0.95, pane:"pointPane" }})
    }}));
  }}).catch(()=>{{}});
  fetchGeoJSON(manifest.reports?.geojson || "observed_311.geojson").then(geo => {{
    bindToggle("ly311", L.geoJSON(geo, {{
      pointToLayer: (f,ll) => L.circleMarker(ll, {{ radius:4, fillColor:"#ff3b5c", color:"#7f0020", weight:1, fillOpacity:0.85, pane:"pointPane" }})
    }}));
  }}).catch(()=>{{}});
  fetchGeoJSON("fema_nfhl.geojson").then(geo => {{
    bindToggle("lyFema", L.geoJSON(geo, {{ style: {{ color:"#1d4ed8", weight:1, fillOpacity:0.15 }} }}));
  }}).catch(()=>{{}});
  fetchGeoJSON("nwm_high_flow.geojson").then(geo => {{
    bindToggle("lyNwm", L.geoJSON(geo, {{ style: {{ color:"#00c2ff", weight:3, opacity:0.8 }} }}));
  }}).catch(()=>{{}});
  fetchGeoJSON("nwm_ahps_gauges.geojson").then(geo => {{
    bindToggle("lyGauges", L.geoJSON(geo, {{
      pointToLayer: (f,ll) => L.circleMarker(ll, {{ radius:6, fillColor:"#37d6ff", color:"#003d5c", weight:2, fillOpacity:1, pane:"pointPane" }})
    }}));
  }}).catch(()=>{{}});

  const scoresName = (manifest.validation_dashboard && manifest.validation_dashboard.scores) || "validation_scores.json";
  fetch(assets + scoresName, {{ cache:"no-cache" }}).then(r => r.ok ? r.json() : null).catch(() => null).then(scores => {{
    const el = document.getElementById("validationPanel");
    if (!el || !scores) return;
    // Desk FloodNet panel owns the primary reproduction story; Advanced keeps limitations-only fallback.
    if (el.dataset.floodnetWired === "1") return;
    const conf = scores.confidence ? scores.confidence.level : "low";
    const note = (scores.confidence && scores.confidence.note) || "Exploratory collocation only.";
    el.innerHTML = `Exploratory (${{conf}}) · ${{note}}`;
  }});
}}

function fmtM(x) {{
  return (x == null || Number.isNaN(Number(x))) ? "—" : Number(x).toFixed(3);
}}

function floodnetPopupHtml(p) {{
  return `<b>${{p.sensor_name || p.sensor_id || "FloodNet"}}</b><br>` +
    `obs ${{fmtM(p.obs_peak_m)}} m · cal ${{fmtM(p.hotspot_cal_m)}} m · resid ${{fmtM(p.residual_m)}} m` +
    `<br><span style="opacity:.75">Post OOM check · not citywide HAND</span>`;
}}

function selectFloodnetStation(sensorId) {{
  selectedFloodnetId = sensorId;
  try {{ window.selectedFloodnetId = sensorId; }} catch (err) {{}}
  document.querySelectorAll("#floodnetList .asset-row").forEach(btn => {{
    btn.classList.toggle("selected", btn.dataset.id === sensorId);
  }});
  if (floodnetLayer) {{
    floodnetLayer.eachLayer(layer => {{
      const p = layer.feature && layer.feature.properties;
      if (!p || p.sensor_id !== sensorId) return;
      const ll = layer.getLatLng();
      mapLeft.flyTo(ll, Math.max(mapLeft.getZoom(), 14), {{ duration: 0.65 }});
      layer.openPopup();
    }});
  }}
  if (window.StreetView3D) {{
    try {{
      window.StreetView3D.maybeOfferButton(sensorId);
      if (viewMode === "3d" && window.StreetView3D.canOpenId(sensorId)) {{
        window.StreetView3D.open(sensorId);
      }}
    }} catch (err) {{}}
  }}
}}

function renderFloodnetList(stations) {{
  const list = document.getElementById("floodnetList");
  if (!list) return;
  if (!stations.length) {{
    list.innerHTML = '<div class="empty">No FloodNet Ida peaks loaded.</div>';
    return;
  }}
  const ranked = stations.slice().sort((a, b) => (b.obs_peak_m || 0) - (a.obs_peak_m || 0));
  list.innerHTML = ranked.map(p => {{
    const ok = !!p.oom_ok;
    const obsCm = p.obs_peak_m == null ? "—" : (Number(p.obs_peak_m) * 100).toFixed(1);
    const calCm = p.hotspot_cal_m == null ? "—" : (Number(p.hotspot_cal_m) * 100).toFixed(1);
    const resCm = p.residual_m == null ? "—" : ((Number(p.residual_m) >= 0 ? "+" : "") + (Number(p.residual_m) * 100).toFixed(1));
    return `<button type="button" class="asset-row${{selectedFloodnetId === p.sensor_id ? " selected" : ""}}" data-id="${{p.sensor_id}}">` +
      `<div class="top"><span class="name">${{p.sensor_name || p.sensor_id}}</span>` +
      `<span class="depth">${{obsCm}} cm</span></div>` +
      `<div class="meta"><span class="type-pill">${{p.borough || "NYC"}}</span>` +
      `<span class="band ${{ok ? "oom-ok" : "oom-miss"}}">${{ok ? "OOM" : "miss"}}</span>` +
      `<span>cal ${{calCm}}</span><span>${{resCm}}</span></div></button>`;
  }}).join("");
  list.querySelectorAll(".asset-row").forEach(btn => {{
    btn.onclick = () => selectFloodnetStation(btn.dataset.id);
  }});
}}

function loadFloodNetLaterEvents() {{
  const laterSummary = document.getElementById("floodnetLaterSummary");
  fetchGeoJSON("floodnet_later_events.geojson").then(geo => {{
    const nSens = (geo.properties && geo.properties.n_sensors) || (geo.features || []).length;
    const nEv = (geo.properties && geo.properties.n_events) || 0;
    if (laterSummary) {{
      laterSummary.innerHTML = `<span>Post-Ida archive</span><b>${{nSens}} sensors · ${{nEv}} events</b>`;
    }}
    if (!geo.features || !geo.features.length) return;
    floodnetLaterLayer = L.geoJSON(geo, {{
      pointToLayer: (f, ll) => L.circleMarker(ll, {{
        radius: 5,
        fillColor: "#5b8def",
        color: "#0b1d2a",
        weight: 1.5,
        fillOpacity: 0.75,
        pane: "pointPane",
      }}),
      onEachFeature: (f, layer) => {{
        const p = f.properties || {{}};
        const cm = p.max_depth_m != null ? (Number(p.max_depth_m) * 100).toFixed(1) : "—";
        layer.bindPopup(
          `<b>${{p.sensor_name || p.sensor_id || "FloodNet"}}</b><br>` +
          `later peak ~${{cm}} cm · n=${{p.n_events_post_ida || "—"}}<br>` +
          `<span style="opacity:.75">Post-Ida archive · research only</span>`
        );
        layer.bindTooltip((p.sensor_name || "FloodNet") + " · later " + cm + " cm");
      }},
    }});
    bindToggle("lyFloodNetLater", floodnetLaterLayer);
  }}).catch(() => {{
    if (laterSummary) laterSummary.innerHTML = `<span>Later FloodNet</span><b>unavailable</b>`;
  }});
}}

function loadScienceValidation() {{
  // Additive data contract — no UI redesign. Optional Advanced-panel footnote.
  const cfg = manifest.science_validation || {{}};
  const name = cfg.summary
    || (manifest.validation_dashboard && manifest.validation_dashboard.science_validation)
    || "science_validation_summary.json";
  fetch(assets + name, {{ cache:"no-cache" }}).then(r => r.ok ? r.json() : null).catch(() => null).then(sv => {{
    const el = document.getElementById("validationPanel");
    if (!el || !sv) return;
    const mix = sv.provenance_mix || {{}};
    const nObs = (mix.observed || []).length;
    const nMod = (mix.modeled || []).length;
    const nSyn = (mix.synthetic || []).length;
    const nFail = (sv.synthetic_sanity && sv.synthetic_sanity.n_fail != null) ? sv.synthetic_sanity.n_fail : "—";
    const line = `Science factors · obs ${{nObs}} / modeled ${{nMod}} / synthetic ${{nSyn}} · stub sanity fails ${{nFail}} · HAND primary · SFINCS Advanced.`;
    if (el.dataset.floodnetWired === "1") {{
      if (!el.dataset.scienceWired) {{
        el.innerHTML = (el.innerHTML || "") + `<div style="margin-top:6px;opacity:.9">${{line}}</div>`;
        el.dataset.scienceWired = "1";
      }}
    }} else if (!el.dataset.scienceWired) {{
      el.innerHTML = line;
      el.dataset.scienceWired = "1";
    }}
  }});
}}

function loadFloodNetProduct() {{
  const fnName = (manifest.validation_dashboard && manifest.validation_dashboard.floodnet)
    || (manifest.validation_floodnet && manifest.validation_floodnet.scores)
    || "floodnet_validation.json";
  const reproName = (manifest.validation_dashboard && manifest.validation_dashboard.ida_reproduction)
    || (manifest.ida_event_reproduction && manifest.ida_event_reproduction.scores)
    || "ida_floodnet_reproduction.json";
  const hotspotGeo = (manifest.ida_event_reproduction && manifest.ida_event_reproduction.stations_geojson)
    || "floodnet_ida_hotspot_stations.geojson";

  Promise.all([
    fetchGeoJSON(hotspotGeo).catch(() => null),
    fetch(assets + reproName, {{ cache:"no-cache" }}).then(r => r.ok ? r.json() : null).catch(() => null),
    fetch(assets + fnName, {{ cache:"no-cache" }}).then(r => r.ok ? r.json() : null).catch(() => null),
  ]).then(([geo, repro, fn]) => {{
    const summaryEl = document.getElementById("floodnetSummary");
    const metaEl = document.getElementById("floodnetMeta");
    const advEl = document.getElementById("validationPanel");

    if (geo && geo.features) {{
      floodnetStations = geo.features.map(f => Object.assign({{}}, f.properties || {{}}, {{
        lon: f.geometry && f.geometry.coordinates ? f.geometry.coordinates[0] : null,
        lat: f.geometry && f.geometry.coordinates ? f.geometry.coordinates[1] : null,
      }}));
      floodnetLayer = L.geoJSON(geo, {{
        pointToLayer: (f, ll) => {{
          const p = f.properties || {{}};
          const ok = !!p.oom_ok;
          return L.circleMarker(ll, {{
            radius: 8,
            fillColor: ok ? "#0a8a96" : "#8d3d14",
            color: "#071018",
            weight: 2,
            fillOpacity: 0.95,
            pane: "pointPane",
          }});
        }},
        onEachFeature: (f, layer) => {{
          const p = f.properties || {{}};
          layer.bindPopup(floodnetPopupHtml(p));
          layer.bindTooltip((p.sensor_name || p.sensor_id || "FloodNet") + " · obs " + fmtM(p.obs_peak_m) + " m");
          layer.on("click", () => {{ selectFloodnetStation(p.sensor_id); }});
        }},
      }});
      bindToggle("lyFloodNet", floodnetLayer);
      renderFloodnetList(floodnetStations);
      if (summaryEl && floodnetStations.length) {{
        // Keep a posts count visible even before repro summary lands.
        if (!summaryEl.dataset.locked) {{
          summaryEl.innerHTML = `<span>Ida posts surfaced</span><b>${{floodnetStations.length}}/5</b>`;
        }}
      }}
    }} else {{
      document.getElementById("floodnetList").innerHTML = '<div class="empty">floodnet_ida_hotspot_stations.geojson missing — run scripts/calibrate_ida_floodnet_hotspot.py</div>';
    }}

    if (repro && repro.summary && repro.summary.hotspot_calibrated) {{
      const h = repro.summary.hotspot_calibrated;
      const cal = repro.calibration || {{}};
      const loo = repro.leave_one_out || {{}};
      const deep = (repro.summary && repro.summary.magnitude_deepen) || {{}};
      const henriN = deep.henri_holdout_n;
      const henriRmse = deep.henri_holdout_rmse_m;
      const pooledN = deep.pooled_n;
      const pooledBeyond = !!deep.pooled_beyond_ida_5;
      if (summaryEl) {{
        summaryEl.dataset.locked = "1";
        summaryEl.innerHTML =
          `<span>Hotspot cal · ${{floodnetStations.length || h.n || 0}}/5 Ida</span>` +
          `<b>RMSE ${{fmtM(h.rmse_m)}} m · OOM ${{h.oom_ok_n || 0}}/${{h.n || 0}}</b>`;
      }}
      if (metaEl) {{
        metaEl.style.display = "flex";
        if (henriN != null && henriRmse != null) {{
          metaEl.innerHTML =
            `<span>Henri holdout n=${{henriN}} · RMSE ${{fmtM(henriRmse)}} m</span>` +
            `<b>${{pooledBeyond ? ("pooled n=" + pooledN) : ("LOO " + fmtM(loo.rmse_m) + " m")}}</b>`;
        }} else {{
          metaEl.innerHTML =
            `<span>HAND dry/cm · LOO ${{fmtM(loo.rmse_m)}} m</span>` +
            `<b>bias ${{fmtM(h.bias_m)}} · scale ${{fmtM(cal.scale)}}</b>`;
        }}
      }}
      if (advEl) {{
        advEl.dataset.floodnetWired = "1";
        let adv = `FloodNet hotspot RMSE ${{fmtM(h.rmse_m)}} m · OOM ${{h.oom_ok_n || 0}}/${{h.n || 0}} · LOO ${{fmtM(loo.rmse_m)}} m · HAND unchanged.`;
        if (henriN != null && henriRmse != null) {{
          adv += ` Henri holdout transfer RMSE ${{fmtM(henriRmse)}} m (n=${{henriN}}).`;
          if (pooledBeyond) adv += ` Pooled unique sensors n=${{pooledN}}.`;
        }}
        advEl.innerHTML = adv;
      }}
      if ((!geo || !geo.features) && Array.isArray(repro.stations)) {{
        floodnetStations = repro.stations;
        renderFloodnetList(floodnetStations);
      }}
      loadFloodNetLaterEvents();
      return;
    }}

    if (fn && fn.summary) {{
      const rmse = fn.summary.peak_rmse_m;
      const bias = fn.summary.peak_bias_m && fn.summary.peak_bias_m.mean;
      const n = fn.summary.n_sensors;
      if (summaryEl) {{
        summaryEl.dataset.locked = "1";
        summaryEl.innerHTML = `<span>FloodNet vs primary HAND</span><b>RMSE ${{fmtM(rmse)}} m · n=${{n}}</b>`;
      }}
      if (advEl) {{
        advEl.dataset.floodnetWired = "1";
        advEl.innerHTML = `FloodNet vs HAND · n=${{n}} · RMSE ${{fmtM(rmse)}} m · bias ${{fmtM(bias)}} m.`;
      }}
      loadFloodNetLaterEvents();
      return;
    }}

    if (summaryEl) {{
      summaryEl.innerHTML = `<span>FloodNet reproduction</span><b>unavailable</b>`;
    }}
    loadFloodNetLaterEvents();
  }}).catch(err => {{
    const summaryEl = document.getElementById("floodnetSummary");
    if (summaryEl) summaryEl.innerHTML = `<span>FloodNet load failed</span><b>—</b>`;
    document.getElementById("floodnetList").innerHTML = '<div class="empty">Failed to load FloodNet reproduction assets.</div>';
    console.warn(err);
  }});
}}

function setArchiveStatus(msg) {{
  const el = document.getElementById("archiveLayersStatus");
  if (el) el.textContent = msg;
}}
function setInventoryStatus(msg) {{
  const el = document.getElementById("inventoryLayersStatus");
  if (el) el.textContent = msg;
}}
function corridorStatusLabel(status) {{
  const map = {{
    cut_at_deep_ponding: "cut ≥8 cm",
    cut_at_ponding: "cut ≥3 cm",
    detour_around_deep: "detour ≥8 cm",
    open_research: "open",
    no_network_path: "no path",
    unsnapped: "unsnapped",
  }};
  return map[status] || status || "—";
}}
function corridorPairKey(p) {{
  return String(p.from_id || "") + "__" + String(p.to_id || "");
}}
function corridorIsCut(status) {{
  const s = String(status || "");
  return s.startsWith("cut_") || s === "no_network_path" || s === "unsnapped";
}}
function corridorPairMeta(pairKey) {{
  const pairs = (corridorData && corridorData.pairs) || [];
  const idx = pairs.findIndex(p => corridorPairKey(p) === pairKey);
  if (idx < 0) return {{ index: 0, status: "open_research", pair: null }};
  return {{ index: idx, status: pairs[idx].status, pair: pairs[idx] }};
}}
function corridorPathStyleFor(pairKey, feature) {{
  const meta = corridorPairMeta(pairKey);
  const pal = CORRIDOR_PAIR_PALETTE[meta.index % CORRIDOR_PAIR_PALETTE.length];
  const cut = corridorIsCut(meta.status);
  const deep = feature && feature.properties && feature.properties.impassable_deep;
  // Distinct pair hue + open/cut language: solid open vs dashed cut.
  return {{
    color: cut ? (deep ? pal.cut : pal.soft) : pal.open,
    weight: cut ? (deep ? 2.8 : 2.2) : 2.6,
    opacity: cut ? 0.88 : 0.92,
    dashArray: cut ? "5 4" : null,
    lineCap: "round",
    lineJoin: "round",
  }};
}}
function syncMapKeyCorridor() {{
  const box = document.getElementById("mapKeyFloat");
  if (!box) return;
  const drawer = document.getElementById("corridorDetails");
  const pathsOn = document.getElementById("lyCorridorPath");
  const anyPair = Object.keys(corridorPairLayers).some(k => {{
    const ly = corridorPairLayers[k];
    return ly && mapLeft.hasLayer(ly);
  }});
  const show = !!(drawer && drawer.open) || !!(pathsOn && pathsOn.checked) || anyPair;
  box.classList.toggle("show-corridor", show);
}}
function clearCorridorPairLayers() {{
  Object.keys(corridorPairLayers).forEach(k => {{
    const ly = corridorPairLayers[k];
    if (ly && mapLeft.hasLayer(ly)) mapLeft.removeLayer(ly);
  }});
  corridorPairLayers = {{}};
  if (corridorPathLayer && mapLeft.hasLayer(corridorPathLayer)) mapLeft.removeLayer(corridorPathLayer);
  corridorPathLayer = null;
}}
function rebuildCorridorPairLayers() {{
  clearCorridorPairLayers();
  if (!corridorPathGeo) return;
  const feats = corridorPathGeo.features || [];
  const byPair = {{}};
  feats.forEach(f => {{
    const key = (f.properties && f.properties.pair) || "_";
    if (!byPair[key]) byPair[key] = [];
    byPair[key].push(f);
  }});
  const master = document.getElementById("lyCorridorPath");
  const masterOn = !master || master.checked;
  Object.keys(byPair).forEach(key => {{
    const meta = corridorPairMeta(key);
    const label = meta.pair
      ? ((meta.pair.from_name || "?") + " → " + (meta.pair.to_name || "?"))
      : "research path";
    const status = meta.status || "";
    const group = L.layerGroup();
    const gj = L.geoJSON({{ type: "FeatureCollection", features: byPair[key] }}, {{
      pane: "selectPane",
      style: f => corridorPathStyleFor(key, f),
      onEachFeature: (f, layer) => {{
        const p = f.properties || {{}};
        layer.bindTooltip(
          label + " · " + corridorStatusLabel(status) +
          (p.name ? (" · " + p.name) : "") +
          " · research (not DOT)"
        );
      }},
    }});
    group.addLayer(gj);
    corridorPairLayers[key] = group;
    const cb = document.getElementById("corridorPair_" + key.replace(/[^a-zA-Z0-9_-]/g, "_"));
    const pairOn = cb ? cb.checked : true;
    if (masterOn && pairOn) group.addTo(mapLeft);
  }});
  // Parent layer used only for master toggle bookkeeping (empty).
  corridorPathLayer = L.layerGroup(Object.values(corridorPairLayers));
  syncMapKeyCorridor();
}}
function rebuildCorridorLandmarks() {{
  if (corridorLandmarkLayer && mapLeft.hasLayer(corridorLandmarkLayer)) {{
    mapLeft.removeLayer(corridorLandmarkLayer);
  }}
  corridorLandmarkLayer = null;
  const lms = (corridorData && corridorData.landmarks) || [];
  if (!lms.length) return;
  const feats = lms.map(lm => ({{
    type: "Feature",
    properties: {{ id: lm.id, name: lm.name, kind: lm.kind }},
    geometry: {{ type: "Point", coordinates: [lm.lon, lm.lat] }},
  }}));
  corridorLandmarkLayer = L.geoJSON({{ type: "FeatureCollection", features: feats }}, {{
    pane: "selectPane",
    pointToLayer: (f, ll) => L.circleMarker(ll, {{
      radius: 5, color: "#14161a", weight: 1.25,
      fillColor: "#fafafb", fillOpacity: 0.95, pane: "selectPane",
    }}),
    onEachFeature: (f, layer) => {{
      const p = f.properties || {{}};
      layer.bindTooltip((p.name || "landmark") + " · corridor endpoint · research");
    }},
  }});
  const ly = document.getElementById("lyCorridorLandmarks");
  if (ly && ly.checked) corridorLandmarkLayer.addTo(mapLeft);
}}
function syncCorridorPairVisibility() {{
  const master = document.getElementById("lyCorridorPath");
  const masterOn = !master || master.checked;
  Object.keys(corridorPairLayers).forEach(key => {{
    const ly = corridorPairLayers[key];
    if (!ly) return;
    const cb = document.getElementById("corridorPair_" + key.replace(/[^a-zA-Z0-9_-]/g, "_"));
    const on = masterOn && (!cb || cb.checked);
    if (on) {{
      if (!mapLeft.hasLayer(ly)) ly.addTo(mapLeft);
    }} else if (mapLeft.hasLayer(ly)) {{
      mapLeft.removeLayer(ly);
    }}
  }});
  syncMapKeyCorridor();
}}
function enableCorridorMultiPairDefault() {{
  const path = document.getElementById("lyCorridorPath");
  const lm = document.getElementById("lyCorridorLandmarks");
  if (path && !path.checked) {{
    path.checked = true;
  }}
  if (lm && !lm.checked) lm.checked = true;
  document.querySelectorAll("#corridorPairs input[type=checkbox]").forEach(cb => {{
    cb.checked = true;
  }});
  syncCorridorPairVisibility();
  if (corridorLandmarkLayer) {{
    if (!mapLeft.hasLayer(corridorLandmarkLayer)) corridorLandmarkLayer.addTo(mapLeft);
  }}
  syncMapKeyCorridor();
}}
function renderCorridorPairs() {{
  const el = document.getElementById("corridorPairs");
  const honesty = document.getElementById("corridorHonesty");
  const lmNote = document.getElementById("corridorLandmarksNote");
  if (!el) return;
  if (!corridorData || !(corridorData.pairs || []).length) {{
    el.innerHTML = '<div class="empty">Corridor graph unavailable</div>';
    if (honesty) honesty.textContent = "";
    if (lmNote) lmNote.textContent = "";
    return;
  }}
  if (honesty) honesty.textContent = corridorData.honesty || "Research only — not official closures.";
  if (lmNote) {{
    const names = ((corridorData.landmarks) || []).map(l => l.name).filter(Boolean);
    lmNote.textContent = names.length
      ? ("Endpoints: " + names.join(" · ") + " — each pair is its own path.")
      : "";
  }}
  el.innerHTML = (corridorData.pairs || []).map((p, idx) => {{
    const key = corridorPairKey(p);
    const safe = key.replace(/[^a-zA-Z0-9_-]/g, "_");
    const cut = corridorIsCut(p.status);
    const pal = CORRIDOR_PAIR_PALETTE[idx % CORRIDOR_PAIR_PALETTE.length];
    const swColor = cut ? pal.cut : pal.open;
    const delta = p.delta_m_vs_open != null ? (" · +" + p.delta_m_vs_open + " m") : "";
    return `<label class="corridor-pair" for="corridorPair_${{safe}}">
      <input id="corridorPair_${{safe}}" type="checkbox" checked data-pair="${{key}}">
      <span class="pair-names">${{p.from_name || "?"}} → ${{p.to_name || "?"}}</span>
      <span class="pair-status ${{cut ? "cut" : "open"}}" title="${{p.honesty || ""}}">
        <span class="pair-swatch ${{cut ? "cut" : "open"}}" style="color:${{swColor}};border-color:${{swColor}};display:inline-block;vertical-align:middle;margin-right:4px"></span>
        ${{corridorStatusLabel(p.status)}}${{delta}}
      </span>
    </label>`;
  }}).join("");
  el.querySelectorAll("input[type=checkbox]").forEach(cb => {{
    cb.addEventListener("change", syncCorridorPairVisibility);
  }});
}}
function loadCorridorImpassability() {{
  const cfg = manifest.corridor_impassability || {{}};
  if (!cfg.available && !cfg.json) {{
    renderCorridorPairs();
    return;
  }}
  const jsonName = cfg.json || "corridor_impassability.json";
  Promise.all([
    fetch(assets + jsonName, {{ cache: "no-cache" }}).then(r => r.ok ? r.json() : null),
    fetchGeoJSON(cfg.wet_edges_geojson || "corridor_wet_edges.geojson").catch(() => null),
    fetchGeoJSON(cfg.paths_geojson || "corridor_research_paths.geojson").catch(() => null),
  ]).then(([json, wet, paths]) => {{
    corridorData = json;
    corridorPathGeo = paths;
    // Stamp status onto features for tooltip honesty / offline inspection.
    if (corridorPathGeo && corridorData) {{
      const statusByPair = {{}};
      (corridorData.pairs || []).forEach(p => {{ statusByPair[corridorPairKey(p)] = p.status; }});
      (corridorPathGeo.features || []).forEach(f => {{
        const props = f.properties || (f.properties = {{}});
        if (props.pair && statusByPair[props.pair]) props.status = statusByPair[props.pair];
      }});
    }}
    renderCorridorPairs();
    rebuildCorridorPairLayers();
    rebuildCorridorLandmarks();
    if (wet) {{
      corridorWetLayer = L.geoJSON(wet, {{
        pane: "vectorPane",
        style: f => ({{
          color: (f.properties && f.properties.impassable_deep) ? "#9f1239" : "#b45309",
          weight: (f.properties && f.properties.impassable_deep) ? 2.2 : 1.4,
          opacity: 0.55,
          dashArray: "3 4",
        }}),
        onEachFeature: (f, layer) => {{
          const p = f.properties || {{}};
          layer.bindTooltip(
            (p.name || "wet edge") + " · " + (p.depth_cm != null ? p.depth_cm + " cm" : "") +
            " · research impassability (not DOT)"
          );
        }},
      }});
      bindToggle("lyCorridorWet", corridorWetLayer);
    }}
    const lyPath = document.getElementById("lyCorridorPath");
    if (lyPath) {{
      lyPath.addEventListener("change", () => {{
        if (lyPath.checked) {{
          document.querySelectorAll("#corridorPairs input[type=checkbox]").forEach(cb => {{ cb.checked = true; }});
        }}
        syncCorridorPairVisibility();
      }});
    }}
    const lyLm = document.getElementById("lyCorridorLandmarks");
    if (lyLm) {{
      lyLm.addEventListener("change", () => {{
        if (!corridorLandmarkLayer) return;
        if (lyLm.checked) corridorLandmarkLayer.addTo(mapLeft);
        else if (mapLeft.hasLayer(corridorLandmarkLayer)) mapLeft.removeLayer(corridorLandmarkLayer);
      }});
    }}
    const drawer = document.getElementById("corridorDetails");
    if (drawer) {{
      drawer.addEventListener("toggle", () => {{
        if (drawer.open) enableCorridorMultiPairDefault();
        syncMapKeyCorridor();
      }});
    }}
    syncMapKeyCorridor();
  }}).catch(err => {{
    console.warn(err);
    renderCorridorPairs();
  }});
}}
function loadOfficialInventoryOverlays() {{
  const bits = [];
  const inv = (manifest.official_inventory_layers) || {{}};
  fetchGeoJSON(inv.stormwater_geojson || "stormwater_deep_moderate_current.geojson").then(geo => {{
    stormwaterLayer = L.geoJSON(geo, {{
      pane: "vectorPane",
      style: {{ color:"#0e7490", weight:1, fillColor:"#22d3ee", fillOpacity:0.22 }},
      onEachFeature: (f, layer) => {{
        const p = f.properties || {{}};
        layer.bindPopup(
          `<b>City stormwater deep zone</b><br>${{p.scenario || "moderate / current SLR"}}` +
          `<br><span style="opacity:.75">Planning polygon · NOT Ida HAND depth</span>`
        );
      }},
    }});
    bindToggle("lyStormwater", stormwaterLayer);
    bits.push("SW×" + ((geo.features || []).length));
    setInventoryStatus(bits.join(" · ") + " ready");
  }}).catch(() => {{ bits.push("SW missing"); setInventoryStatus(bits.join(" · ")); }});

  fetchGeoJSON(inv.lion_tunnels_geojson || "lion_tunnels.geojson").then(geo => {{
    lionTunLayer = L.geoJSON(geo, {{
      pane: "vectorPane",
      style: {{ color:"#7c3aed", weight:3.5, opacity:0.85 }},
      onEachFeature: (f, layer) => {{
        const p = f.properties || {{}};
        layer.bindTooltip((p.name || "LION tunnel") + " · inventory");
      }},
    }});
    bindToggle("lyLionTun", lionTunLayer);
    bits.push("LION×" + ((geo.features || []).length));
    setInventoryStatus(bits.join(" · ") + " ready");
  }}).catch(() => {{ bits.push("LION missing"); setInventoryStatus(bits.join(" · ")); }});

  fetchGeoJSON(inv.bes_geojson || "bes_near_wet_facilities.geojson").then(geo => {{
    besLayer = L.geoJSON(geo, {{
      pointToLayer: (f, ll) => {{
        const sub = f.properties && String(f.properties.subgrade || "").toUpperCase() === "Y";
        return L.circleMarker(ll, {{
          radius: 4,
          fillColor: sub ? "#b45309" : "#a8a29e",
          color: "#1c1917",
          weight: 1,
          fillOpacity: 0.85,
          pane: "pointPane",
        }});
      }},
      onEachFeature: (f, layer) => {{
        const p = f.properties || {{}};
        const floor = p.z_floor_ft_navd88 != null ? Number(p.z_floor_ft_navd88).toFixed(1) + " ft floor" : "BES";
        const sub = p.subgrade_present ? " · subgrade Y" : "";
        layer.bindTooltip((p.address || "BES") + " · " + floor + sub);
      }},
    }});
    bindToggle("lyBes", besLayer);
    bits.push("BES×" + ((geo.features || []).length));
    setInventoryStatus(bits.join(" · ") + " ready");
  }}).catch(() => {{ bits.push("BES missing"); setInventoryStatus(bits.join(" · ")); }});
}}
function loadArchiveOpenLayers() {{
  const statusBits = [];
  fetchGeoJSON("archived_511_events.geojson").then(geo => {{
    archive511Layer = L.geoJSON(geo, {{
      pointToLayer: (f, ll) => {{
        const kind = f.properties && (f.properties.closure || f.properties.kind === "limited") ? "limited" : "watch";
        return L.marker(ll, {{ icon: accessDivIcon("nysdot_511_events", kind), pane: "pointPane" }});
      }},
      onEachFeature: (f, layer) => {{
        const p = f.properties || {{}};
        layer.bindPopup(`<b>${{p.label || "Archived 511-style"}}</b><br>Research archive · not official closures`);
      }},
    }});
    bindToggle("lyArchive511", archive511Layer);
    statusBits.push("511×" + ((geo.features || []).length));
    setArchiveStatus(statusBits.join(" · ") + " ready");
  }}).catch(() => statusBits.push("511 missing"));

  const basinsName = (manifest.drainage_capacity_proxy && manifest.drainage_capacity_proxy.dense_sample_geojson)
    || "dep_catch_basins_dense_sample.geojson";
  fetchGeoJSON(basinsName).catch(() => fetchGeoJSON("dep_catch_basins_sample.geojson")).then(geo => {{
    if (!geo) throw new Error("basins missing");
    depBasinsLayer = L.geoJSON(geo, {{
      pointToLayer: (f, ll) => L.circleMarker(ll, {{
        radius: 2.2, fillColor: "#6b7280", color: "#111827", weight: 0.7, fillOpacity: 0.65, pane: "pointPane"
      }}),
      onEachFeature: (f, layer) => {{
        const p = f.properties || {{}};
        layer.bindTooltip((p.unitid || p.node_id || "catch basin") + " · open inventory (not SWMM)");
      }},
    }});
    bindToggle("lyDepBasins", depBasinsLayer);
    statusBits.push("basins×" + ((geo.features || []).length));
    setArchiveStatus(statusBits.join(" · ") + " ready");
  }}).catch(() => {{
    statusBits.push("basins missing");
    setArchiveStatus(statusBits.join(" · "));
  }});

  fetchGeoJSON("building_footprints_sample.geojson").then(geo => {{
    buildingsLayer = L.geoJSON(geo, {{
      style: {{ color: "#334155", weight: 1, fillColor: "#94a3b8", fillOpacity: 0.25 }},
      onEachFeature: (f, layer) => {{
        const p = f.properties || {{}};
        const h = p.height_roof != null ? (Number(p.height_roof).toFixed(0) + " ft roof") : "footprint";
        layer.bindTooltip(h + " · open sample");
      }},
    }});
    bindToggle("lyBuildings", buildingsLayer);
    statusBits.push("bldgs×" + ((geo.features || []).length));
    setArchiveStatus(statusBits.join(" · ") + " ready");
  }}).catch(() => {{
    statusBits.push("buildings missing");
    setArchiveStatus(statusBits.join(" · "));
  }});
}}

document.getElementById("listModeChips").addEventListener("click", e => {{
  const btn = e.target.closest(".seg");
  if (!btn) return;
  listMode = btn.dataset.mode || "shortlist";
  document.querySelectorAll("#listModeChips .seg").forEach(c => c.classList.toggle("active", c === btn));
  const after = () => {{
    if (listMode === "all" && !includeSchools()) {{
      const summary = document.getElementById("deskSummary");
      if (summary && desk) {{
        const c = desk.counts || {{}};
        summary.innerHTML =
          `<span>Wet · metro HAND · decision classes</span><b>${{c.wet_total||0}} · R${{c.roads||0}} S${{c.stations||0}} F${{c.facilities||0}}</b>`;
      }}
    }}
    renderAssetList();
  }};
  if (needsFullDesk()) ensureFullDesk().then(after).catch(() => after());
  else after();
}});
document.getElementById("typeChips").addEventListener("click", e => {{
  const btn = e.target.closest(".seg");
  if (!btn) return;
  typeFilter = btn.dataset.type;
  document.querySelectorAll("#typeChips .seg").forEach(c => c.classList.toggle("active", c === btn));
  // Stations/facilities are sparse at ≥8 cm — open All wet + full list so the chip is usable.
  if (typeFilter === "station" || typeFilter === "facility") {{
    listMode = "all";
    document.querySelectorAll("#listModeChips .seg").forEach(c => c.classList.toggle("active", c.dataset.mode === "all"));
    const band = document.getElementById("bandFilter");
    if (band && band.value === "deep_ponding") {{
      band.value = "all";
    }}
  }}
  if (needsFullDesk()) {{ ensureFullDesk().then(() => renderAssetList()); return; }}
  renderAssetList();
}});
document.getElementById("bandFilter").onchange = renderAssetList;
document.getElementById("assetSearch").oninput = () => {{
  if ((document.getElementById("assetSearch").value || "").trim()) {{
    listMode = "all";
    document.querySelectorAll("#listModeChips .seg").forEach(c => c.classList.toggle("active", c.dataset.mode === "all"));
  }}
  if (needsFullDesk()) ensureFullDesk().then(() => renderAssetList()).catch(() => renderAssetList());
  else renderAssetList();
}};
document.getElementById("hudPlay").onclick = () => setPlaying(!playing);
document.getElementById("hudScrub").oninput = (e) => {{
  setPlaying(false);
  setLead(+e.target.value);
}};
document.getElementById("selClose").onclick = clearSelection;
document.addEventListener("keydown", (e) => {{
  const tag = e.target && e.target.tagName;
  const typing = tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA";
  if (e.key === "Escape") {{
    clearSelection();
    return;
  }}
  if (typing) return;
  if (e.key === "ArrowRight" || e.key === "ArrowLeft") {{
    e.preventDefault();
    setPlaying(false);
    const step = e.key === "ArrowRight" ? 1 : -1;
    if (!frames.length) return;
    setLead((leadIndex + step + frames.length) % frames.length);
    return;
  }}
  if (e.key === "j" || e.key === "J" || e.key === "ArrowDown") {{
    e.preventDefault();
    moveBriefingFocus(1);
    return;
  }}
  if (e.key === "k" || e.key === "K" || e.key === "ArrowUp") {{
    e.preventDefault();
    moveBriefingFocus(-1);
    return;
  }}
  if (e.key === "Enter" && focusedAssetId) {{
    e.preventDefault();
    selectAsset(focusedAssetId);
    return;
  }}
  if (e.key === " " || e.code === "Space") {{
    e.preventDefault();
    if (compareOn) return;
    setPlaying(!playing);
    return;
  }}
  if (e.key === "c" || e.key === "C") {{
    e.preventDefault();
    setCompareMode(!compareOn);
  }}
}});
document.getElementById("extentSelect").onchange = () => fitMapFrame();
document.getElementById("eventSelect").onchange = () => {{
  const ev = EVENTS[eventSel.value];
  if (!ev || !ev.available) {{
    alert("That event is not loaded yet.");
    eventSel.value = activeEventId;
    return;
  }}
  activeEventId = ev.id;
  listMode = "shortlist";
  document.querySelectorAll("#listModeChips .seg").forEach(c => c.classList.toggle("active", c.dataset.mode === "shortlist"));
  const band = document.getElementById("bandFilter");
  if (band) band.value = "all";
  clearSelection();
  deskLoadedMode = "none";
  desk = null;
  fullDeskPromise = null;
  applyStormPathForEvent(activeEventId);
  const brandKicker = document.querySelector(".brand-kicker");
  if (brandKicker) {{
    brandKicker.textContent = activeEventId === "henri-2021"
      ? "Henri research replay"
      : "Ida research replay";
  }}
  loadDecisionDesk();
}};
document.getElementById("stormPathSelect").onchange = () => {{
  activePath = stormPaths.find(p => p.id === pathSel.value) || stormPaths[0];
  rebuildPathLayers();
  setLead(0);
}};
document.getElementById("opPrecip").oninput = () => {{
  document.getElementById("opPrecipVal").textContent = document.getElementById("opPrecip").value + "%";
  if (activeE2) activeE2.setOpacity(precipOpacity());
  if (e2Total) e2Total.setOpacity(precipOpacity());
}};
document.getElementById("opSusc").oninput = () => {{
  document.getElementById("opSuscVal").textContent = document.getElementById("opSusc").value + "%";
  if (activeSusc) activeSusc.setOpacity(suscOpacity());
}};
document.getElementById("opDepth").oninput = () => {{
  document.getElementById("opDepthVal").textContent = document.getElementById("opDepth").value + "%";
  if (activeDepth) activeDepth.setOpacity(effectiveDepthOpacity());
  else if (depthTotal) depthTotal.setOpacity(effectiveDepthOpacity());
}};
document.getElementById("lyStreets").onchange = () => {{
  const on = document.getElementById("lyStreets").checked;
  if (on) {{
    if (!mapLeft.hasLayer(streetsBasemap)) streetsBasemap.addTo(mapLeft);
  }} else if (mapLeft.hasLayer(streetsBasemap)) {{
    mapLeft.removeLayer(streetsBasemap);
  }}
}};
// Sync streets checkbox with actual online default
(function syncStreetsDefault() {{
  const el = document.getElementById("lyStreets");
  if (!el) return;
  const online = typeof navigator === "undefined" || navigator.onLine !== false;
  el.checked = online && mapLeft.hasLayer(streetsBasemap);
  if (!online && mapLeft.hasLayer(streetsBasemap)) mapLeft.removeLayer(streetsBasemap);
}})();
document.getElementById("lyE2").onchange = () => setLead(leadIndex);
document.getElementById("lySusc").onchange = () => {{
  // Dim depth under screening so the amber index reads; keep current lead.
  setLead(leadIndex);
}};
document.getElementById("lyDepthTot").onchange = () => {{
  if (activeDepth && mapLeft.hasLayer(activeDepth)) mapLeft.removeLayer(activeDepth);
  if (depthTotal && mapLeft.hasLayer(depthTotal)) mapLeft.removeLayer(depthTotal);
  activeDepth = null;
  if (document.getElementById("lyDepthTot").checked) setLead(leadIndex);
}};
function syncSfincsPeerMode() {{
  const nestedOn = !!(document.getElementById("lySfincsNested") && document.getElementById("lySfincsNested").checked && sfincsNestedLayer);
  const queensOn = !!(document.getElementById("lySfincs") && document.getElementById("lySfincs").checked && sfincsLayer);
  const on = nestedOn || queensOn;
  const banner = document.getElementById("sfincsPeerBanner");
  const stage = document.getElementById("mapStage");
  if (banner) banner.style.display = on ? "block" : "none";
  if (stage) stage.classList.toggle("hand-dimmed", on);
  const b = document.getElementById("assetBanner");
  if (on && b) {{
    b.style.display = "block";
    b.innerHTML = nestedOn
      ? "<b>Metro nested SFINCS</b> — non-peer metres vs HAND cm (auto-dimmed). No SWMM. Research only."
      : "<b>SFINCS Queens nest</b> — non-peer metres vs HAND cm (auto-dimmed). No SWMM. Research only.";
  }} else if (b && !on) {{
    b.style.display = "none";
    b.textContent = "";
  }}
  // Dim HAND depth overlay while SFINCS is authoritative-looking.
  if (on) {{
    if (activeDepth) activeDepth.setOpacity(Math.min(effectiveDepthOpacity(), 0.28));
    else if (depthTotal) depthTotal.setOpacity(0.28);
  }} else {{
    setLead(leadIndex);
  }}
}}
(function fillSfincsExchangeNote() {{
  const el = document.getElementById("sfincsExchangeNote");
  if (!el) return;
  const ex = manifest.sfincs_nest_exchange || {{}};
  if (!ex.available) {{ el.textContent = ""; return; }}
  const rmse = ex.hand_rmse_m != null ? (" · non-peer HAND overlap RMSE " + Number(ex.hand_rmse_m).toFixed(2) + " m") : "";
  el.textContent = "Exchange: " + (ex.mode || "feathered") + rmse + " — research only, never blended into HAND ranks.";
}})();
(function fillLiveMrmsNote() {{
  const el = document.getElementById("liveMrmsNote");
  if (!el) return;
  const live = manifest.live_mrms || {{}};
  if (live.available && live.valid_time_utc) {{
    el.textContent = "Live MRMS QPE probe reachable @ " + String(live.valid_time_utc).replace("T", " ") +
      " — desk loops stay Ida/Henri fixtures (ops latency probe only, not NWS).";
  }} else {{
    el.textContent = "Live MRMS probe unavailable — desk uses labeled Ida/Henri fixture replay. See docs/live-mrms-qpf-path.md.";
  }}
}})();
document.getElementById("lySfincsNested").onchange = () => {{
  if (!sfincsNestedLayer) return;
  if (document.getElementById("lySfincsNested").checked) sfincsNestedLayer.addTo(mapLeft);
  else mapLeft.removeLayer(sfincsNestedLayer);
  syncSfincsPeerMode();
}};
document.getElementById("lySfincs").onchange = () => {{
  if (!sfincsLayer) return;
  if (document.getElementById("lySfincs").checked) sfincsLayer.addTo(mapLeft);
  else mapLeft.removeLayer(sfincsLayer);
  syncSfincsPeerMode();
}};
document.getElementById("lyE2Tot").onchange = () => {{
  if (!e2Total) return;
  if (document.getElementById("lyE2Tot").checked) {{ e2Total.setOpacity(precipOpacity()); e2Total.addTo(mapLeft); }}
  else mapLeft.removeLayer(e2Total);
}};
document.getElementById("lyAccess").onchange = () => {{
  rebuildAccessOverlay();
  syncAccessFixtureBadge();
}};
document.getElementById("lyWet").onchange = () => syncWetLayerVisibility();
document.getElementById("lyTopHits").onchange = () => {{
  rebuildWetLayer();
  if (!highlightLayer) return;
  if (topHitsEnabled()) {{
    if (!mapLeft.hasLayer(highlightLayer)) highlightLayer.addTo(mapLeft);
  }} else if (mapLeft.hasLayer(highlightLayer)) {{
    mapLeft.removeLayer(highlightLayer);
  }}
}};
const lySchools = document.getElementById("lyIncludeSchools");
if (lySchools) lySchools.onchange = () => {{
  const refresh = () => {{
    const c = (desk && desk.counts) || {{}};
    const modeNote = listMode === "all" && !includeSchools() ? " · decision classes" : "";
    const summary = document.getElementById("deskSummary");
    if (summary) summary.innerHTML =
      `<span>Wet · metro HAND${{modeNote}}</span><b>${{c.wet_total||0}} · R${{c.roads||0}} S${{c.stations||0}} F${{c.facilities||0}}</b>`;
    renderAssetList();
  }};
  if (needsFullDesk()) ensureFullDesk().then(refresh).catch(refresh);
  else refresh();
}};
function restyleFloodNetResiduals() {{
  residualMode = !!(document.getElementById("lyModelWrong") && document.getElementById("lyModelWrong").checked);
  if (residualMode) {{
    const ly = document.getElementById("lyFloodNet");
    if (ly && !ly.checked) {{ ly.checked = true; if (floodnetLayer && !mapLeft.hasLayer(floodnetLayer)) floodnetLayer.addTo(mapLeft); }}
  }}
  if (!floodnetLayer) return;
  floodnetLayer.eachLayer(layer => {{
    const p = (layer.feature && layer.feature.properties) || {{}};
    const obs = Number(p.obs_peak_m);
    const hand = Number(p.primary_hand_m != null ? p.primary_hand_m : (p.model_peak_m != null ? p.model_peak_m : 0));
    const resid = (Number.isFinite(obs) ? obs : 0) - (Number.isFinite(hand) ? hand : 0);
    if (!residualMode) {{
      const ok = !!p.oom_ok;
      layer.setStyle({{
        radius: 8,
        fillColor: ok ? "#0a8a96" : "#8d3d14",
        color: "#071018",
        weight: 2,
        fillOpacity: 0.95,
      }});
      return;
    }}
    // Residual mode: larger / warmer = HAND more wrong (underestimate)
    const r = Math.max(7, Math.min(16, 7 + resid * 10));
    layer.setStyle({{
      radius: r,
      fillColor: resid >= 0.4 ? "#b91c1c" : resid >= 0.15 ? "#c2410c" : "#a16207",
      color: "#042227",
      weight: 2,
      fillOpacity: 0.95,
    }});
    layer.bindTooltip(
      (p.sensor_name || p.sensor_id || "FloodNet") +
      " · residual ~" + (Number.isFinite(resid) ? resid.toFixed(2) : "—") + " m (obs−HAND) · not blended"
    );
  }});
}}
const lyModelWrong = document.getElementById("lyModelWrong");
if (lyModelWrong) lyModelWrong.onchange = restyleFloodNetResiduals;
(function initCoach() {{
  const overlay = document.getElementById("coachOverlay");
  const btn = document.getElementById("coachDismiss");
  if (!overlay || !btn) return;
  try {{
    if (localStorage.getItem("nyc_flood_desk_coach_v2") === "1") return;
  }} catch (err) {{}}
  overlay.hidden = false;
  btn.onclick = () => {{
    overlay.hidden = true;
    try {{ localStorage.setItem("nyc_flood_desk_coach_v2", "1"); }} catch (err) {{}}
  }};
}})();
document.getElementById("lyAccessLive").onchange = () => {{
  loadAccessSignals();
  // Live overlay does not rebuild desk ranks in-browser; run fetch_live_access_feeds.py --apply-desk for joined chips.
}};
const btnShare = document.getElementById("btnShareSnapshot");
const btnPrint = document.getElementById("btnPrintSnapshot");
if (btnShare) btnShare.onclick = () => copyShortlistSnapshot();
if (btnPrint) btnPrint.onclick = () => printShortlistSnapshot();
(function wireMapKeyFloat() {{
  const box = document.getElementById("mapKeyFloat");
  const btn = document.getElementById("mapKeyFloatToggle");
  if (!box || !btn) return;
  btn.addEventListener("click", () => {{
    const collapsed = box.classList.toggle("collapsed");
    btn.textContent = collapsed ? "+" : "–";
    btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
    btn.setAttribute("aria-label", collapsed ? "Expand map key" : "Collapse map key");
  }});
}})();

wireCompareUi();
wireViewModeToggle();
rebuildPathLayers();
fitMapFrame();
setLead(0);
loadCompareStrip();
loadCompareFramesMeta();
loadDecisionDesk();
loadAccessSignals();
loadFloodNetProduct();
loadScienceValidation();
loadOptionalLayers();
loadOfficialInventoryOverlays();
loadCorridorImpassability();
loadArchiveOpenLayers();
setPlaying(true);
</script>
</body>
</html>
"""
    out = FIGURES_DIR / "product_map.html"
    out.write_text(html)
    return out
