/**
 * Decision Desk UX extensions (command-center pass):
 * - Citywide curb/street flood layer (depth tint + lead opacity)
 * - ImageOverlay zoom georef reassert
 * - Multi-frame preload / progressive loop reveal
 * - 311 flood reports + optional extent
 * - Underlay Reveal (subsurface / "x-ray") mode
 * - Hotspot compact diagnostic (2D inspector + 3D HUD)
 *
 * Research prototype — NOT NWS / NOT decision-grade.
 */
(function (global) {
  "use strict";

  const UX = {
    streetFloodLines: null,
    streetFloodPolys: null,
    reports311: null,
    reports311Extent: null,
    underlayOn: false,
    underlayLayers: {},
    framesPrefetched: false,
    loadBar: null,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function assetsBase() {
    if (typeof global.assets === "string" && global.assets) return global.assets;
    return "product_assets/";
  }

  function fetchGeoJSON(name) {
    return fetch(assetsBase() + name, { cache: "no-cache" }).then((r) => {
      if (!r.ok) throw new Error(name + " " + r.status);
      return r.json();
    });
  }

  function depthColor(cm) {
    if (cm >= 15) return "#08306b";
    if (cm >= 8) return "#2171b5";
    if (cm >= 3) return "#6baed6";
    if (cm >= 1) return "#9ecae1";
    return "#c6dbef";
  }

  function foamColor(cm) {
    return cm >= 8 ? "rgba(226,240,255,.92)" : "rgba(210,230,245,.75)";
  }

  /* ---------- Hotspot compact diagnostic ---------- */
  function failureMechanism(a) {
    const depth = Number(a && (a.max_depth_cm ?? a.depth_cm)) || 0;
    const band = (a && a.band) || "";
    const access = (a && a.access_status) || "open";
    const type = (a && (a.asset_type || a.type)) || "";
    if (depth >= 15 || band === "hazard") {
      return "Rapid runoff accumulates in low-lying terrain faster than modeled drainage can remove it.";
    }
    if (depth >= 8 || band === "deep_ponding") {
      return "Curb/gutter ponding builds as antecedent wetness and constrained outlets slow drawdown.";
    }
    if (access === "limited") {
      return "Access pinch points coincide with wet edges — corridor continuity is the primary risk.";
    }
    if (type === "station" || String(a && a.id || "").indexOf("stations:") === 0) {
      return "Station approaches sit in a local HAND depression where street flow collects first.";
    }
    if (type === "facility") {
      return "Facility grade sits near wet-edge HAND ponding; screening depth rises with storm leads.";
    }
    if (depth >= 3 || band === "ponding") {
      return "Shallow ponding forms where road grade and drainage capacity are locally mismatched.";
    }
    return "Screening signal is weak — monitor rainfall intensity and drainage constraint before acting.";
  }

  function diagnosticFromAsset(a) {
    const depth = Number(a && (a.max_depth_cm ?? a.depth_cm)) || 0;
    const series = (a && a.depth_series_cm) || [];
    const leads = (a && a.depth_series_leads_h) || [];
    let rise = 0;
    if (series.length >= 2) {
      const mid = Math.floor(series.length / 2);
      rise = Math.max(0, (series[mid] || 0) - (series[0] || 0));
    }
    // Research proxies — labeled, not sensor measurements.
    const rainfall = Math.min(100, Math.round(28 + depth * 3.2 + rise * 1.4));
    const drainage = Math.max(8, Math.min(96, Math.round(88 - depth * 3.6 - (a && a.impassable_deep ? 12 : 0))));
    const antecedent = Math.min(100, Math.round(22 + rise * 4.5 + (leads.length ? 8 : 0)));
    const terrain = Math.min(100, Math.round(18 + depth * 4.1));
    return {
      rainfall_intensity: rainfall,
      drainage_constraint: 100 - drainage,
      drainage_capacity: drainage,
      antecedent_wetness: antecedent,
      terrain_depression: terrain,
      failure_mechanism: failureMechanism(a),
      synthetic: true,
      honesty: "Compact diagnostic uses research proxies from HAND leads — not gauges / not NWS.",
    };
  }

  function renderDiagnosticHtml(diag, opts) {
    opts = opts || {};
    const bar = (label, val, tone) => {
      const v = Math.max(0, Math.min(100, Number(val) || 0));
      return (
        '<div class="diag-row">' +
        '<span class="diag-k">' +
        label +
        '</span><span class="diag-meter" data-tone="' +
        tone +
        '"><i style="width:' +
        v +
        '%"></i></span><span class="diag-v">' +
        v +
        "</span></div>"
      );
    };
    return (
      '<div class="hotspot-diag' +
      (opts.compact ? " compact" : "") +
      '">' +
      '<div class="diag-title">Compact diagnostic' +
      (diag.synthetic ? ' <em>· research proxy</em>' : "") +
      "</div>" +
      bar("Rainfall intensity", diag.rainfall_intensity, "rain") +
      bar("Drainage constraint", diag.drainage_constraint, "drain") +
      bar("Antecedent wetness", diag.antecedent_wetness, "wet") +
      bar("Terrain depression", diag.terrain_depression, "terrain") +
      '<p class="diag-fail"><strong>Failure mechanism.</strong> ' +
      (diag.failure_mechanism || "—") +
      "</p>" +
      '<p class="diag-note">' +
      (diag.honesty || "") +
      "</p></div>"
    );
  }

  function updateInspectorDiagnostic(asset) {
    const host = $("selDiagnostic");
    if (!host) return;
    if (!asset) {
      host.innerHTML = "";
      host.hidden = true;
      return;
    }
    const diag = diagnosticFromAsset(asset);
    host.innerHTML = renderDiagnosticHtml(diag);
    host.hidden = false;
    try {
      global.__lastHotspotDiagnostic = diag;
    } catch (err) {}
  }

  function update3dDiagnostic(hotspot) {
    const host = $("sv3dDiagnostic");
    if (!host) return;
    if (!hotspot) {
      host.innerHTML = "";
      return;
    }
    const proxy = {
      id: hotspot.id,
      name: hotspot.name,
      max_depth_cm: hotspot.max_depth_cm != null ? hotspot.max_depth_cm : hotspot.depth_series_cm
        ? Math.max.apply(null, hotspot.depth_series_cm.map(Number) || [0])
        : 0,
      depth_series_cm: hotspot.depth_series_cm,
      depth_series_leads_h: hotspot.depth_series_leads_h,
      band: hotspot.band,
      asset_type: hotspot.kind,
    };
    host.innerHTML = renderDiagnosticHtml(diagnosticFromAsset(proxy), { compact: true });
  }

  /* ---------- Citywide street flood ---------- */
  function streetFloodStyle(feature) {
    const p = feature.properties || {};
    const cm = Number(p.depth_cm) || 0;
    const ring = p.ring || "mid";
    const op =
      ring === "core" ? Math.min(0.72, 0.28 + cm / 28) :
      ring === "mid" ? Math.min(0.55, 0.18 + cm / 36) :
      Math.min(0.38, 0.1 + cm / 48);
    return {
      color: foamColor(cm),
      weight: ring === "fringe" ? 1.2 : 0.6,
      opacity: ring === "fringe" ? 0.55 : 0.25,
      fillColor: depthColor(cm),
      fillOpacity: op,
      pane: "streetFloodPane",
      className: "street-flood-poly ring-" + ring,
    };
  }

  function streetLineStyle(feature) {
    const cm = Number((feature.properties || {}).depth_cm) || 0;
    return {
      color: depthColor(cm),
      weight: Math.max(2.2, Math.min(7.5, 2 + cm / 3.2)),
      opacity: Math.min(0.92, 0.35 + cm / 22),
      lineCap: "round",
      lineJoin: "round",
      pane: "streetFloodPane",
      className: "street-flood-line",
    };
  }

  function ensureStreetFloodPane(map) {
    if (!map.getPane("streetFloodPane")) {
      map.createPane("streetFloodPane");
      map.getPane("streetFloodPane").style.zIndex = 455;
      map.getPane("streetFloodPane").style.pointerEvents = "none";
    }
  }

  function syncStreetFloodToLead(leadHours) {
    // Opacity progression with storm leads (temporal reveal).
    const lead = Number(leadHours) || 0;
    const t = Math.max(0.18, Math.min(1, 0.22 + lead / 28));
    const apply = (layer, isLine) => {
      if (!layer) return;
      layer.eachLayer((l) => {
        const f = l.feature;
        if (!f) return;
        if (isLine) {
          const s = streetLineStyle(f);
          l.setStyle({ opacity: s.opacity * t, weight: s.weight });
        } else {
          const s = streetFloodStyle(f);
          l.setStyle({ fillOpacity: s.fillOpacity * t, opacity: s.opacity * t });
        }
      });
    };
    apply(UX.streetFloodLines, true);
    apply(UX.streetFloodPolys, false);
  }

  function loadStreetFloodLayer(map) {
    if (!map || typeof L === "undefined") return;
    ensureStreetFloodPane(map);
    const on = $("lyStreetFlood");
    const want = !on || on.checked;

    Promise.all([
      fetchGeoJSON("street_flood_citywide_lines.geojson").catch(() => null),
      fetchGeoJSON("street_flood_citywide.geojson").catch(() => null),
    ]).then(([lines, polys]) => {
      if (UX.streetFloodLines && map.hasLayer(UX.streetFloodLines)) map.removeLayer(UX.streetFloodLines);
      if (UX.streetFloodPolys && map.hasLayer(UX.streetFloodPolys)) map.removeLayer(UX.streetFloodPolys);
      if (lines) {
        UX.streetFloodLines = L.geoJSON(lines, {
          style: streetLineStyle,
          onEachFeature: (f, layer) => {
            const p = f.properties || {};
            layer.bindTooltip(
              (p.name || "Wet street") +
                " · " +
                (p.depth_cm != null ? p.depth_cm + " cm HAND" : "HAND") +
                " · research curb flood"
            );
          },
        });
      }
      if (polys) {
        UX.streetFloodPolys = L.geoJSON(polys, { style: streetFloodStyle });
      }
      const add = () => {
        if (UX.streetFloodPolys) UX.streetFloodPolys.addTo(map);
        if (UX.streetFloodLines) UX.streetFloodLines.addTo(map);
        const lead =
          global.frames && global.frames[global.leadIndex]
            ? global.frames[global.leadIndex].lead_hours
            : 12;
        syncStreetFloodToLead(lead);
      };
      if (want) add();
      if (on && !on._streetFloodWired) {
        on._streetFloodWired = true;
        on.addEventListener("change", () => {
          if (on.checked) add();
          else {
            if (UX.streetFloodLines && map.hasLayer(UX.streetFloodLines)) map.removeLayer(UX.streetFloodLines);
            if (UX.streetFloodPolys && map.hasLayer(UX.streetFloodPolys)) map.removeLayer(UX.streetFloodPolys);
          }
        });
      }
    });
  }

  /* ---------- Overlay zoom georef ---------- */
  function hardenOverlayGeoref(map) {
    if (!map || map._deskGeorefHardened) return;
    map._deskGeorefHardened = true;

    const reassert = () => {
      if (typeof global.reassertOverlayBounds === "function") {
        try {
          global.reassertOverlayBounds();
        } catch (err) {}
      }
      // Force Leaflet ImageOverlay to recompute CSS transform from LatLngBounds.
      const layers = []
        .concat(global.e2Layers || [])
        .concat(global.suscLayers || [])
        .concat(global.depthLayers || [])
        .concat([
          global.activeE2,
          global.activeSusc,
          global.activeDepth,
          global.fadeE2,
          global.fadeSusc,
          global.fadeDepth,
          global.e2Total,
          global.depthTotal,
          global.compareLeftLayer,
          global.compareRightLayer,
        ]);
      const b =
        global.activeOverlayBounds ||
        (typeof global.dataDomainBounds === "function" ? global.dataDomainBounds() : null);
      layers.forEach((layer) => {
        if (!layer) return;
        try {
          if (b && typeof layer.setBounds === "function") layer.setBounds(b);
          if (typeof layer._reset === "function") layer._reset();
          if (typeof layer.redraw === "function") layer.redraw();
        } catch (err) {}
      });
    };

    map.on("zoom zoomend move moveend resize viewreset", reassert);
    // Also after animation frames (Leaflet zoom anim can desync blend panes).
    map.on("zoomanim", () => {
      requestAnimationFrame(reassert);
    });
    // Expose for setLead / rebuildPathLayers.
    global.__deskReassertOverlays = reassert;
  }

  /* ---------- Multi-frame preload ---------- */
  function ensureLoadBar() {
    let el = $("stormLoadBar");
    if (el) return el;
    el = document.createElement("div");
    el.id = "stormLoadBar";
    el.className = "storm-load-bar";
    el.innerHTML =
      '<div class="storm-load-inner"><span class="storm-load-label">Loading storm progression…</span>' +
      '<div class="storm-load-track"><i id="stormLoadFill"></i></div>' +
      '<span class="storm-load-meta" id="stormLoadMeta">0%</span></div>';
    const stage = $("mapStage") || document.body;
    stage.appendChild(el);
    UX.loadBar = el;
    return el;
  }

  function setLoadProgress(pct, meta) {
    const bar = ensureLoadBar();
    const fill = $("stormLoadFill");
    const metaEl = $("stormLoadMeta");
    if (fill) fill.style.width = Math.max(0, Math.min(100, pct)) + "%";
    if (metaEl) metaEl.textContent = meta || Math.round(pct) + "%";
    if (pct >= 100) {
      bar.classList.add("done");
      setTimeout(() => {
        bar.classList.add("hidden");
      }, 480);
    } else {
      bar.classList.remove("done", "hidden");
    }
  }

  function preloadStormFrames() {
    const frames = global.frames || [];
    if (!frames.length) {
      setLoadProgress(100, "ready");
      return Promise.resolve();
    }
    ensureLoadBar();
    setLoadProgress(2, "prefetch 0/" + frames.length);
    // Prefetch precip + a slice of depth so first paint is a multi-frame loop, not a single still.
    const urls = [];
    frames.forEach((f) => {
      if (f && f.png) urls.push(assetsBase() + f.png);
    });
    const depthFrames = global.depthCumFrames || [];
    depthFrames.forEach((f) => {
      if (f && f.png) urls.push(assetsBase() + f.png);
    });
    // Unique
    const uniq = Array.from(new Set(urls));
    let done = 0;
    const total = uniq.length || 1;
    return Promise.all(
      uniq.map(
        (src) =>
          new Promise((resolve) => {
            const im = new Image();
            im.onload = im.onerror = () => {
              done += 1;
              const pct = (done / total) * 100;
              setLoadProgress(pct, done + "/" + total + " frames");
              resolve();
            };
            im.src = src;
          })
      )
    ).then(() => {
      UX.framesPrefetched = true;
      setLoadProgress(100, "loop ready");
      // Progressive reveal: jump a few leads quickly so load never looks like one still.
      if (typeof global.setLead === "function" && frames.length > 1) {
        const steps = [0, Math.min(2, frames.length - 1), Math.min(4, frames.length - 1), 0];
        let i = 0;
        const tick = () => {
          if (i >= steps.length) {
            if (typeof global.setPlaying === "function") global.setPlaying(true);
            return;
          }
          global.setLead(steps[i]);
          i += 1;
          setTimeout(tick, 160);
        };
        tick();
      } else if (typeof global.setPlaying === "function") {
        global.setPlaying(true);
      }
    });
  }

  /* ---------- 311 reports + extent ---------- */
  function load311Enhanced(map) {
    if (!map) return;
    fetchGeoJSON("observed_311.geojson")
      .catch(() =>
        // Labeled synthetic fallback if fixture missing.
        Promise.resolve({
          type: "FeatureCollection",
          properties: { synthetic: true },
          features: [
            {
              type: "Feature",
              geometry: { type: "Point", coordinates: [-73.989, 40.675] },
              properties: {
                descriptor: "SYNTHETIC Street Flooding",
                complaint_type: "Street Flooding",
                created_date: "2021-09-02T01:00:00",
                synthetic: true,
              },
            },
          ],
        })
      )
      .then((geo) => {
        const synthetic = !!(geo.properties && geo.properties.synthetic);
        if (!map.getPane("reports311Pane")) {
          map.createPane("reports311Pane");
          map.getPane("reports311Pane").style.zIndex = 620;
        }
        const pts = L.geoJSON(geo, {
          pane: "reports311Pane",
          pointToLayer: (f, ll) =>
            L.circleMarker(ll, {
              radius: 5,
              fillColor: synthetic ? "#fb7185" : "#e11d48",
              color: "#7f1d1d",
              weight: 1.2,
              fillOpacity: 0.88,
              pane: "reports311Pane",
              className: "rpt-311",
            }),
          onEachFeature: (f, layer) => {
            const p = f.properties || {};
            layer.bindPopup(
              "<b>" +
                (p.descriptor || p.complaint_type || "311 flood-related") +
                "</b><br>" +
                (p.created_date || "") +
                (p.synthetic || synthetic
                  ? "<br><em>SYNTHETIC labeled fallback</em>"
                  : "<br><span style='opacity:.75'>311 complaint ≠ surveyed flood extent</span>")
            );
          },
        });
        // Optional extent: ~90 m research buffers (not surveyed inundation).
        const extentFeats = (geo.features || [])
          .filter((f) => f.geometry && f.geometry.type === "Point")
          .map((f) => {
            const [lon, lat] = f.geometry.coordinates;
            const r = 0.00085; // ~90 m
            const ring = [];
            for (let i = 0; i <= 24; i++) {
              const t = (i / 24) * Math.PI * 2;
              ring.push([lon + r * Math.cos(t) * 1.15, lat + r * Math.sin(t)]);
            }
            return {
              type: "Feature",
              geometry: { type: "Polygon", coordinates: [ring] },
              properties: Object.assign({}, f.properties || {}, {
                role: "report_extent_proxy",
                honesty: "Optional ~90 m research buffer around 311 point — not surveyed extent.",
              }),
            };
          });
        const extent = L.geoJSON(
          { type: "FeatureCollection", features: extentFeats },
          {
            pane: "reports311Pane",
            style: {
              color: "#be123c",
              weight: 0.8,
              fillColor: "#fb7185",
              fillOpacity: 0.12,
              opacity: 0.45,
            },
          }
        );
        UX.reports311 = pts;
        UX.reports311Extent = extent;

        const bind = (id, layer) => {
          const el = $(id);
          if (!el) return;
          const sync = () => {
            if (el.checked) {
              if (!map.hasLayer(layer)) layer.addTo(map);
            } else if (map.hasLayer(layer)) {
              map.removeLayer(layer);
            }
          };
          el.addEventListener("change", sync);
          sync();
        };
        // Replace naive 311 toggle wiring if present: uncheck then rebind.
        bind("ly311", pts);
        bind("ly311Extent", extent);
      });
  }

  /* ---------- Underlay Reveal (subsurface / x-ray) ---------- */
  function setUnderlayReveal(on) {
    UX.underlayOn = !!on;
    document.body.classList.toggle("underlay-reveal", UX.underlayOn);
    const btn = $("btnUnderlayReveal");
    if (btn) {
      btn.setAttribute("aria-pressed", UX.underlayOn ? "true" : "false");
      btn.classList.toggle("active", UX.underlayOn);
    }
    const map = global.mapLeft;
    if (!map) return;

    const show = (key, layer) => {
      if (!layer) return;
      if (UX.underlayOn) {
        if (!map.hasLayer(layer)) layer.addTo(map);
      } else if (map.hasLayer(layer) && !layer._userPinned) {
        map.removeLayer(layer);
      }
    };

    Object.keys(UX.underlayLayers).forEach((k) => show(k, UX.underlayLayers[k]));

    // Fade surface: dim precip/streets slightly when revealing underlay.
    try {
      const streetsOn = $("lyStreets");
      if (streetsOn && !UX.underlayOn && streetsOn.checked) {
        /* leave user choice */
      }
      document.documentElement.style.setProperty(
        "--underlay-surface-fade",
        UX.underlayOn ? "0.42" : "1"
      );
    } catch (err) {}
  }

  function loadUnderlayLayers(map) {
    if (!map) return;
    if (!map.getPane("underlayPane")) {
      map.createPane("underlayPane");
      map.getPane("underlayPane").style.zIndex = 380;
    }
    if (!map.getPane("underlayPointPane")) {
      map.createPane("underlayPointPane");
      map.getPane("underlayPointPane").style.zIndex = 390;
    }

    const jobs = [
      ["basins", "dep_catch_basins_dense_sample.geojson", (geo) =>
        L.geoJSON(geo, {
          pane: "underlayPointPane",
          pointToLayer: (f, ll) =>
            L.circleMarker(ll, {
              radius: 2.4,
              fillColor: "#0d9488",
              color: "#115e59",
              weight: 0.8,
              fillOpacity: 0.85,
              pane: "underlayPointPane",
            }),
        })
      ],
      ["nodes", "drainage_nodes.geojson", (geo) =>
        L.geoJSON(geo, {
          pane: "underlayPointPane",
          pointToLayer: (f, ll) =>
            L.circleMarker(ll, {
              radius: 3,
              fillColor: "#14b8a6",
              color: "#0f766e",
              weight: 1,
              fillOpacity: 0.9,
              pane: "underlayPointPane",
            }),
        })
      ],
      ["conduits", "drainage_conduits.geojson", (geo) =>
        L.geoJSON(geo, {
          pane: "underlayPane",
          style: { color: "#0f766e", weight: 1.4, opacity: 0.7, className: "underlay-conduit" },
        })
      ],
      ["subway", "subway_stations.geojson", (geo) =>
        L.geoJSON(geo, {
          pane: "underlayPointPane",
          pointToLayer: (f, ll) =>
            L.circleMarker(ll, {
              radius: 4,
              fillColor: "#f59e0b",
              color: "#92400e",
              weight: 1,
              fillOpacity: 0.9,
              pane: "underlayPointPane",
            }),
        })
      ],
      ["flow", "street_flood_citywide_lines.geojson", (geo) =>
        L.geoJSON(geo, {
          pane: "underlayPane",
          style: (f) => ({
            color: "#38bdf8",
            weight: Math.max(1.2, Math.min(4, (Number(f.properties?.depth_cm) || 1) / 4)),
            opacity: 0.55,
            dashArray: "2 6",
            className: "underlay-flow",
          }),
        })
      ],
    ];

    // Synthetic elevation gradient contours if no DEM contours exist.
    const synthElev = {
      type: "FeatureCollection",
      properties: { synthetic: true },
      features: [
        {
          type: "Feature",
          properties: { role: "elev_gradient", synthetic: true, label: "Lower HAND depression (synthetic)" },
          geometry: {
            type: "Polygon",
            coordinates: [[
              [-74.02, 40.66], [-73.96, 40.66], [-73.96, 40.70], [-74.02, 40.70], [-74.02, 40.66],
            ]],
          },
        },
      ],
    };

    jobs.push([
      "elev",
      null,
      () =>
        L.geoJSON(synthElev, {
          pane: "underlayPane",
          style: {
            color: "#a8a29e",
            weight: 1,
            fillColor: "#78716c",
            fillOpacity: 0.14,
            dashArray: "4 4",
            className: "underlay-elev",
          },
        }),
    ]);

    jobs.forEach(([key, name, factory]) => {
      const run = (geo) => {
        try {
          UX.underlayLayers[key] = name ? factory(geo) : factory();
        } catch (err) {
          console.warn("underlay", key, err);
        }
      };
      if (!name) {
        run(null);
        return;
      }
      fetchGeoJSON(name)
        .then(run)
        .catch(() => {
          // Labeled empty stub.
          UX.underlayLayers[key] = L.layerGroup();
        });
    });
  }

  /* ---------- Boot ---------- */
  function patchSetLead() {
    if (global.__deskSetLeadPatched) return;
    if (typeof global.setLead !== "function") return;
    global.__deskSetLeadPatched = true;
    const orig = global.setLead;
    global.setLead = function (i) {
      const out = orig.apply(this, arguments);
      try {
        const f = (global.frames || [])[global.leadIndex];
        if (f) syncStreetFloodToLead(f.lead_hours);
        if (typeof global.__deskReassertOverlays === "function") global.__deskReassertOverlays();
      } catch (err) {}
      return out;
    };
  }

  function patchSelectAsset() {
    // Hook common selection paths via MutationObserver on inspector name + desk select.
    const tryHook = () => {
      if (typeof global.selectAsset === "function" && !global.selectAsset._deskDiag) {
        const orig = global.selectAsset;
        const wrapped = function (id) {
          const out = orig.apply(this, arguments);
          try {
            const desk = global.desk;
            const a = desk && (desk.assets || []).find((x) => x.id === id);
            updateInspectorDiagnostic(a || null);
            if (global.StreetView3D && global.StreetView3D.state && global.StreetView3D.state.open) {
              update3dDiagnostic(a || global.StreetView3D.state.hotspot);
            }
          } catch (err) {}
          return out;
        };
        wrapped._deskDiag = true;
        global.selectAsset = wrapped;
      }
    };
    tryHook();
    setTimeout(tryHook, 800);
    setTimeout(tryHook, 2000);
  }

  function wireUi() {
    const map = global.mapLeft;
    if (!map) {
      setTimeout(wireUi, 200);
      return;
    }
    hardenOverlayGeoref(map);
    loadStreetFloodLayer(map);
    load311Enhanced(map);
    loadUnderlayLayers(map);
    patchSetLead();
    patchSelectAsset();

    const underBtn = $("btnUnderlayReveal");
    if (underBtn && !underBtn._wired) {
      underBtn._wired = true;
      underBtn.addEventListener("click", () => setUnderlayReveal(!UX.underlayOn));
    }

    // Prefetch after path layers exist.
    const waitFrames = () => {
      if ((global.frames || []).length) {
        preloadStormFrames();
      } else {
        setTimeout(waitFrames, 250);
      }
    };
    waitFrames();

    // Keep diagnostic in sync when 3D opens.
    const sv = global.StreetView3D;
    if (sv && !sv._deskDiagHook) {
      sv._deskDiagHook = true;
      const origOpen = sv.open;
      sv.open = function (hint, opts) {
        const p = origOpen.apply(this, arguments);
        Promise.resolve(p).then(() => {
          try {
            update3dDiagnostic(sv.state && sv.state.hotspot);
          } catch (err) {}
        });
        return p;
      };
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => setTimeout(wireUi, 0));
  } else {
    setTimeout(wireUi, 0);
  }

  global.DeskUX = {
    diagnosticFromAsset,
    failureMechanism,
    renderDiagnosticHtml,
    updateInspectorDiagnostic,
    update3dDiagnostic,
    syncStreetFloodToLead,
    setUnderlayReveal,
    preloadStormFrames,
    state: UX,
  };
})(window);
