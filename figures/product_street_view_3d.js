/**
 * MapLibre GL street-level 3D hotspot view for Decision Desk.
 * Research HAND/MRMS lead-frame screening — NOT photogrammetry street-truth.
 * Lazy-loads product_assets/3d_scene.json (+ per-hotspot GeoJSON) on first open.
 *
 * - Curb/street HAND flood: road buffers − building footprints (core/mid/fringe bands)
 * - Lead scrub animates water height/opacity + risk color ramp
 * - Shortlist / FloodNet select fly/ease the camera when already in 3D (or on open)
 * - Leaflet 2D path unchanged when 3D is closed
 */
(function (global) {
  "use strict";

  const STATE = {
    scene: null,
    map: null,
    styleUrl: null,
    open: false,
    hotspotId: null,
    hotspot: null,
    loading: false,
    depthCm: 0,
    leadH: 0,
    animRaf: null,
    pulseRaf: null,
    displayCm: 0,
    labelMarker: null,
  };

  const DEFAULT_STYLE = "https://tiles.openfreemap.org/styles/liberty";
  // Street-center / lane / curb height scales (matches build_3d_scene_assets.py).
  const RING_SCALES = { core: 1.0, mid: 0.65, fringe: 0.32 };
  const FLY_MS = 1400;
  const OPEN_EASE_MS = 950;

  function assetsBase() {
    if (typeof global.assets === "string" && global.assets) return global.assets;
    try {
      return new URL("product_assets/", global.location.href).href;
    } catch (e) {
      return "product_assets/";
    }
  }

  function $(id) {
    return document.getElementById(id);
  }

  /** Decision Desk HAND cm risk ramp (matches 2D briefing). */
  function depthColor(cm) {
    if (cm >= 15) return "#08306b";
    if (cm >= 8) return "#4292c6";
    if (cm >= 3) return "#9ecae1";
    if (cm >= 0.5) return "#bfdbfe";
    return "#dbeafe";
  }

  function depthBandLabel(cm) {
    if (cm >= 15) return "≥15 cm";
    if (cm >= 8) return "≥8 cm";
    if (cm >= 3) return "≥3 cm";
    return "<3 cm";
  }

  function nearestLeadDepth(hotspot, leadHours) {
    const leads = (hotspot && hotspot.depth_series_leads_h) || [];
    const vals = (hotspot && hotspot.depth_series_cm) || [];
    if (!leads.length || vals.length !== leads.length) {
      return { lead: leadHours || 0, cm: 0, idx: -1 };
    }
    let best = 0;
    let bestAbs = Infinity;
    leads.forEach((h, i) => {
      const d = Math.abs((h || 0) - (leadHours || 0));
      if (d < bestAbs) {
        bestAbs = d;
        best = i;
      }
    });
    return { lead: leads[best], cm: Number(vals[best]) || 0, idx: best };
  }

  function currentLeadHours() {
    const frames = global.frames || [];
    const li = global.leadIndex != null ? global.leadIndex : 0;
    if (frames[li] && frames[li].lead_hours != null) return frames[li].lead_hours;
    const scrub = $("hudScrub");
    return scrub ? Number(scrub.value) || 0 : 0;
  }

  function desiredStyleUrl(scene) {
    const raw = scene && scene.basemap && scene.basemap.style;
    // demotiles is a countries demo (not streets) — never use it for street-level 3D.
    if (!raw || /demotiles\.maplibre\.org/i.test(raw)) return DEFAULT_STYLE;
    return raw;
  }

  async function ensureScene() {
    if (STATE.scene) return STATE.scene;
    const url = assetsBase() + "3d_scene.json";
    const r = await fetch(url, { cache: "no-cache" });
    if (!r.ok) throw new Error("3d_scene.json missing (" + r.status + ")");
    STATE.scene = await r.json();
    return STATE.scene;
  }

  function findHotspot(scene, id) {
    const list = (scene && scene.hotspots) || [];
    return list.find((h) => h.id === id) || null;
  }

  function resolveHotspotId(hint) {
    if (!hint) return null;
    if (typeof hint === "string") return hint;
    if (hint.id) return hint.id;
    if (hint.sensor_id) return hint.sensor_id;
    return null;
  }

  function canOpenId(id) {
    if (!id) return false;
    if (!STATE.scene) {
      // Optimistic allow for known demo ids before index loads.
      return (
        id === "stations:gtfs:F22" ||
        id.indexOf("BK-") === 0 ||
        id.indexOf("Q-") === 0 ||
        id.indexOf("floodnet:") === 0 ||
        id.indexOf("stations:") === 0 ||
        id.indexOf("road:") === 0 ||
        id.indexOf("facilities:") === 0
      );
    }
    if (findHotspot(STATE.scene, id)) return true;
    // Shortlist / FloodNet select may pass ids not yet in the scene index —
    // still allow open when the caller supplies lat/lon on the hint object.
    return (
      id.indexOf("BK-") === 0 ||
      id.indexOf("Q-") === 0 ||
      id.indexOf("floodnet:") === 0 ||
      id.indexOf("stations:") === 0 ||
      id.indexOf("road:") === 0 ||
      id.indexOf("facilities:") === 0
    );
  }

  function coordsFromHint(hint) {
    if (!hint || typeof hint !== "object") return null;
    let lon = hint.lon != null ? Number(hint.lon) : null;
    let lat = hint.lat != null ? Number(hint.lat) : null;
    if ((lon == null || lat == null) && Array.isArray(hint.coordinates) && hint.coordinates.length >= 2) {
      lon = Number(hint.coordinates[0]);
      lat = Number(hint.coordinates[1]);
    }
    if (
      (lon == null || lat == null) &&
      hint.geometry &&
      Array.isArray(hint.geometry.coordinates) &&
      hint.geometry.coordinates.length >= 2
    ) {
      lon = Number(hint.geometry.coordinates[0]);
      lat = Number(hint.geometry.coordinates[1]);
    }
    if (lon == null || lat == null || !Number.isFinite(lon) || !Number.isFinite(lat)) return null;
    return { lon: lon, lat: lat };
  }

  function setPanelOpen(open) {
    const panel = $("streetView3d");
    if (!panel) return;
    const wasOpen = STATE.open;
    panel.hidden = !open;
    panel.setAttribute("aria-hidden", open ? "false" : "true");
    document.body.classList.toggle("street-view-open", open);
    STATE.open = open;
    if (wasOpen && !open && typeof global.onStreetViewClosed === "function") {
      try {
        global.onStreetViewClosed();
      } catch (err) {
        console.warn("onStreetViewClosed", err);
      }
    }
  }

  function updateReadout() {
    const leadEl = $("sv3dLead");
    const depthEl = $("sv3dDepth");
    const bandEl = $("sv3dBand");
    const hudDepth = $("sv3dHudDepth");
    const hudBand = $("sv3dHudBand");
    if (leadEl) leadEl.textContent = "+" + STATE.leadH + "h";
    if (depthEl) depthEl.textContent = STATE.depthCm.toFixed(1) + " cm";
    const band = depthBandLabel(STATE.depthCm);
    if (bandEl) bandEl.textContent = band;
    if (hudDepth) hudDepth.textContent = STATE.depthCm.toFixed(1) + " cm HAND";
    if (hudBand) {
      hudBand.textContent = band;
      hudBand.style.background = depthColor(STATE.depthCm);
      hudBand.style.color = STATE.depthCm >= 8 ? "#f8fafc" : "#0f172a";
    }
    const ramp = $("sv3dRampFill");
    if (ramp) {
      const pct = Math.max(4, Math.min(100, (STATE.depthCm / 18) * 100));
      ramp.style.width = pct.toFixed(0) + "%";
      ramp.style.background = depthColor(STATE.depthCm);
    }
  }

  function visualHeightM(cm, ringScale) {
    // Exaggerate cm → street-readable metres so ponding is visible at pitch.
    const base = Math.max(0.04, Math.min(5.2, (cm / 100) * 4.6));
    return Math.max(0.03, base * (ringScale || 1));
  }

  function applyDepthPaint(cm) {
    const map = STATE.map;
    if (!map) return;
    const color = depthColor(cm);
    const wet = cm >= 0.45;
    // Curb (fringe) lighter / shallower; street center (core) deepest.
    const fringeOp = wet ? Math.min(0.48, 0.14 + cm / 38) : 0.04;
    const midOp = wet ? Math.min(0.68, 0.22 + cm / 30) : 0.06;
    const coreOp = wet ? Math.min(0.9, 0.36 + cm / 20) : 0.08;

    const paint = [
      ["sv-depth-fringe", RING_SCALES.fringe, fringeOp, color],
      ["sv-depth-mid", RING_SCALES.mid, midOp, color],
      ["sv-depth-core", RING_SCALES.core, coreOp, color],
    ];
    paint.forEach(([id, scale, opacity, col]) => {
      if (!map.getLayer(id)) return;
      map.setPaintProperty(id, "fill-extrusion-height", visualHeightM(cm, scale));
      map.setPaintProperty(id, "fill-extrusion-color", col);
      map.setPaintProperty(id, "fill-extrusion-opacity", opacity);
    });

    // Flat pavement sheen on curb band — wet street reading without adding height.
    if (map.getLayer("sv-depth-sheen")) {
      map.setPaintProperty(
        "sv-depth-sheen",
        "fill-opacity",
        wet ? Math.min(0.58, 0.2 + cm / 24) : 0.04
      );
      map.setPaintProperty("sv-depth-sheen", "fill-color", color);
    }
    if (map.getLayer("sv-roads-line")) {
      map.setPaintProperty(
        "sv-roads-line",
        "line-opacity",
        wet ? Math.min(0.85, 0.35 + cm / 28) : 0.2
      );
      map.setPaintProperty("sv-roads-line", "line-color", wet ? color : "#94a3b8");
    }
  }

  function stopAnim() {
    if (STATE.animRaf) {
      cancelAnimationFrame(STATE.animRaf);
      STATE.animRaf = null;
    }
  }

  function stopPulse() {
    if (STATE.pulseRaf) {
      cancelAnimationFrame(STATE.pulseRaf);
      STATE.pulseRaf = null;
    }
  }

  function animateDepthTo(targetCm, durationMs) {
    stopAnim();
    const from = STATE.displayCm;
    const to = targetCm;
    if (Math.abs(to - from) < 0.02) {
      STATE.displayCm = to;
      applyDepthPaint(to);
      return;
    }
    const t0 = performance.now();
    const dur = Math.max(180, durationMs || 520);
    function step(now) {
      const t = Math.min(1, (now - t0) / dur);
      const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      STATE.displayCm = from + (to - from) * ease;
      applyDepthPaint(STATE.displayCm);
      if (t < 1) {
        STATE.animRaf = requestAnimationFrame(step);
      } else {
        STATE.animRaf = null;
        STATE.displayCm = to;
        applyDepthPaint(to);
      }
    }
    STATE.animRaf = requestAnimationFrame(step);
  }

  function startWaterPulse() {
    stopPulse();
    const map = STATE.map;
    if (!map || !map.getLayer("sv-depth-core")) return;
    const tick = (now) => {
      if (!STATE.open || !STATE.map) {
        STATE.pulseRaf = null;
        return;
      }
      const cm = STATE.displayCm;
      if (cm >= 0.5 && STATE.map.getLayer("sv-depth-core")) {
        const wave = 0.5 + 0.5 * Math.sin(now / 900);
        const base = Math.min(0.86, 0.32 + cm / 22);
        const op = Math.max(0.28, Math.min(0.92, base + wave * 0.06));
        try {
          STATE.map.setPaintProperty("sv-depth-core", "fill-extrusion-opacity", op);
        } catch (err) {
          /* style may be swapping */
        }
      }
      STATE.pulseRaf = requestAnimationFrame(tick);
    };
    STATE.pulseRaf = requestAnimationFrame(tick);
  }

  function syncToLead(leadHours) {
    if (!STATE.open || !STATE.hotspot) return;
    const d = nearestLeadDepth(STATE.hotspot, leadHours);
    STATE.leadH = d.lead;
    STATE.depthCm = d.cm;
    updateReadout();
    animateDepthTo(d.cm, 560);
    updateLabelMarker();
  }

  function destroyMap() {
    stopAnim();
    stopPulse();
    if (STATE.labelMarker) {
      try {
        STATE.labelMarker.remove();
      } catch (err) {
        /* ignore */
      }
      STATE.labelMarker = null;
    }
    if (!STATE.map) return;
    try {
      STATE.map.remove();
    } catch (err) {
      console.warn("MapLibre remove:", err);
    }
    STATE.map = null;
    STATE.styleUrl = null;
  }

  function cameraFromHotspot(hotspot) {
    const cam = hotspot.camera || {};
    return {
      center: cam.center || [hotspot.lon, hotspot.lat],
      zoom: cam.zoom != null ? cam.zoom : 17.35,
      pitch: cam.pitch != null ? cam.pitch : 62,
      bearing: cam.bearing != null ? cam.bearing : -20,
    };
  }

  function resolveCameraMethod(opts) {
    const raw = opts && opts.method != null ? String(opts.method) : "flyTo";
    if (raw === "ease" || raw === "easeTo") return "easeTo";
    if (raw === "jump" || raw === "jumpTo") return "jumpTo";
    return "flyTo";
  }

  function flyCamera(hotspot, opts) {
    const map = STATE.map;
    if (!map || !hotspot) return;
    const cam = cameraFromHotspot(hotspot);
    const animate = !opts || opts.animate !== false;
    const duration = opts && opts.duration != null ? opts.duration : FLY_MS;
    const method = resolveCameraMethod(opts);
    const jump = {
      center: cam.center,
      zoom: cam.zoom,
      pitch: cam.pitch,
      bearing: cam.bearing,
    };
    try {
      if (typeof map.stop === "function") map.stop();
      if (!animate || duration <= 0 || method === "jumpTo") {
        map.jumpTo(jump);
        return;
      }
      if (method === "easeTo") {
        map.easeTo(Object.assign({}, jump, { duration: duration, essential: true }));
        return;
      }
      map.flyTo(
        Object.assign({}, jump, {
          duration: duration,
          essential: true,
          curve: 1.35,
          speed: 0.9,
        })
      );
    } catch (err) {
      console.warn("camera move", err);
      try {
        map.jumpTo(jump);
      } catch (err2) {
        console.warn("camera jump", err2);
      }
    }
  }

  /** Resize then fly/ease so MapLibre does not cancel the camera move. */
  function scheduleCameraMove(hotspot, opts) {
    if (!STATE.map || !hotspot) return;
    const run = () => {
      if (!STATE.map) return;
      try {
        STATE.map.resize();
      } catch (err) {}
      // Second frame: layout settled after resize / panel unhide.
      requestAnimationFrame(() => flyCamera(hotspot, opts));
    };
    requestAnimationFrame(run);
  }

  function applyAtmosphere(map, scene) {
    try {
      const light =
        (scene && scene.basemap && scene.basemap.light) || {
          anchor: "viewport",
          color: "#f2f0ea",
          intensity: 0.42,
          position: [1.15, 210, 35],
        };
      map.setLight({
        anchor: light.anchor || "viewport",
        color: light.color || "#f2f0ea",
        intensity: light.intensity != null ? light.intensity : 0.42,
        position: light.position || [1.15, 210, 35],
      });
    } catch (err) {
      console.warn("setLight unavailable", err);
    }
    // Soft dusk tint via a full-map fill is brittle; prefer light + building tones.
  }

  async function ensureMap(hotspot, opts) {
    if (typeof maplibregl === "undefined") {
      throw new Error("MapLibre GL not loaded (vendor/maplibre)");
    }
    const scene = STATE.scene;
    const styleUrl = desiredStyleUrl(scene);
    // Reuse map instance; camera fly happens after layers load in openStreetView3d.
    if (STATE.map && STATE.styleUrl === styleUrl) {
      return STATE.map;
    }

    destroyMap();

    const cam = cameraFromHotspot(hotspot);
    const map = new maplibregl.Map({
      container: "sv3dMap",
      style: styleUrl,
      center: cam.center,
      zoom: Math.max(14.5, cam.zoom - 1.2),
      pitch: Math.max(35, cam.pitch - 18),
      bearing: cam.bearing,
      maxPitch: 85,
      attributionControl: true,
      hash: false,
      preserveDrawingBuffer: false,
      antialias: true,
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    STATE.map = map;
    STATE.styleUrl = styleUrl;

    await new Promise((resolve) => {
      let done = false;
      const finish = () => {
        if (done) return;
        done = true;
        resolve();
      };
      map.on("load", finish);
      map.on("error", (e) => {
        if (e && e.error) console.warn("MapLibre:", e.error);
      });
      setTimeout(finish, 10000);
    });

    applyAtmosphere(map, scene);

    try {
      const basemap = scene.basemap || {};
      const terrainUrl = basemap.terrain_source;
      const wantTerrain =
        !!basemap.terrain_enabled &&
        terrainUrl &&
        !/demotiles\.maplibre\.org/i.test(terrainUrl);
      if (wantTerrain) {
        if (!map.getSource("sv-terrain")) {
          map.addSource("sv-terrain", {
            type: "raster-dem",
            url: terrainUrl,
            tileSize: 256,
          });
        }
        map.setTerrain({
          source: "sv-terrain",
          exaggeration: basemap.terrain_exaggeration || 1.1,
        });
      }
    } catch (err) {
      console.warn("Terrain unavailable — flat 3D buildings only.", err);
    }

    return map;
  }

  function updateLabelMarker() {
    if (!STATE.map || !STATE.hotspot || typeof maplibregl === "undefined") return;
    const h = STATE.hotspot;
    const label =
      (h.label || h.name || h.id) +
      " · +" +
      STATE.leadH +
      "h · " +
      STATE.depthCm.toFixed(1) +
      " cm HAND";
    if (!STATE.labelMarker) {
      const el = document.createElement("div");
      el.className = "sv-map-label";
      el.textContent = label;
      STATE.labelMarker = new maplibregl.Marker({ element: el, anchor: "bottom" })
        .setLngLat([h.lon, h.lat])
        .addTo(STATE.map);
    } else {
      STATE.labelMarker.setLngLat([h.lon, h.lat]);
      const el = STATE.labelMarker.getElement();
      if (el) el.textContent = label;
    }
  }

  async function loadHotspotLayers(hotspot) {
    const map = STATE.map;
    const base = assetsBase();

    [
      "sv-depth-core",
      "sv-depth-mid",
      "sv-depth-fringe",
      "sv-depth-sheen",
      "sv-roads-line",
      "sv-roads-casing",
      "sv-buildings-extrusion",
      "sv-buildings-outline",
      "sv-pin",
      "sv-pin-halo",
    ].forEach((id) => {
      if (map.getLayer(id)) map.removeLayer(id);
    });
    ["sv-depth", "sv-buildings", "sv-roads", "sv-pin"].forEach((id) => {
      if (map.getSource(id)) map.removeSource(id);
    });

    const fetches = [
      fetch(base + hotspot.buildings, { cache: "no-cache" }),
      fetch(base + hotspot.depth_polygon, { cache: "no-cache" }),
    ];
    if (hotspot.roads) {
      fetches.push(fetch(base + hotspot.roads, { cache: "no-cache" }));
    }
    const results = await Promise.all(fetches);
    const bRes = results[0];
    const dRes = results[1];
    const rRes = results[2] || null;
    if (!bRes.ok) throw new Error("buildings geojson " + bRes.status);
    if (!dRes.ok) throw new Error("depth geojson " + dRes.status);
    const buildings = await bRes.json();
    const depth = await dRes.json();
    let roads = null;
    if (rRes && rRes.ok) {
      try {
        roads = await rRes.json();
      } catch (err) {
        roads = null;
      }
    }

    map.addSource("sv-buildings", { type: "geojson", data: buildings });
    map.addLayer({
      id: "sv-buildings-extrusion",
      type: "fill-extrusion",
      source: "sv-buildings",
      paint: {
        "fill-extrusion-color": [
          "interpolate",
          ["linear"],
          ["coalesce", ["to-number", ["get", "extrusion_m"]], 12],
          6,
          "#b9c0c9",
          18,
          "#9aa3ae",
          36,
          "#7d8794",
        ],
        "fill-extrusion-height": [
          "coalesce",
          ["to-number", ["get", "extrusion_m"]],
          ["to-number", ["get", "height_roof"]],
          12,
        ],
        "fill-extrusion-base": 0,
        "fill-extrusion-opacity": 0.92,
        "fill-extrusion-vertical-gradient": true,
      },
    });

    map.addSource("sv-depth", { type: "geojson", data: depth });

    // Curb sheen — flat fill of outermost street band (pavement wetness).
    map.addLayer({
      id: "sv-depth-sheen",
      type: "fill",
      source: "sv-depth",
      filter: ["==", ["get", "ring"], "fringe"],
      paint: {
        "fill-color": depthColor(0),
        "fill-opacity": 0.04,
      },
    });

    // Curb → lane → street-center so taller water draws on top.
    ["fringe", "mid", "core"].forEach((ring) => {
      map.addLayer({
        id: "sv-depth-" + ring,
        type: "fill-extrusion",
        source: "sv-depth",
        filter: ["==", ["get", "ring"], ring],
        paint: {
          "fill-extrusion-color": depthColor(0),
          "fill-extrusion-height": 0.04,
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": 0.08,
          "fill-extrusion-vertical-gradient": true,
        },
      });
    });

    // Fallback: single-polygon legacy assets without ring property.
    const hasRings = (depth.features || []).some(
      (f) => f.properties && f.properties.ring
    );
    if (!hasRings && map.getLayer("sv-depth-core")) {
      map.setFilter("sv-depth-core", null);
      if (map.getLayer("sv-depth-mid")) map.removeLayer("sv-depth-mid");
      if (map.getLayer("sv-depth-fringe")) map.removeLayer("sv-depth-fringe");
      if (map.getLayer("sv-depth-sheen")) map.removeLayer("sv-depth-sheen");
    }

    // Road centreline cue under/over water so curb flood reads as street, not a disc.
    if (roads && (roads.features || []).length) {
      map.addSource("sv-roads", { type: "geojson", data: roads });
      map.addLayer({
        id: "sv-roads-casing",
        type: "line",
        source: "sv-roads",
        paint: {
          "line-color": "#0f172a",
          "line-width": 3.2,
          "line-opacity": 0.35,
        },
        layout: {
          "line-cap": "round",
          "line-join": "round",
        },
      });
      map.addLayer({
        id: "sv-roads-line",
        type: "line",
        source: "sv-roads",
        paint: {
          "line-color": "#94a3b8",
          "line-width": 1.4,
          "line-opacity": 0.55,
        },
        layout: {
          "line-cap": "round",
          "line-join": "round",
        },
      });
    }

    map.addSource("sv-pin", {
      type: "geojson",
      data: {
        type: "Feature",
        geometry: { type: "Point", coordinates: [hotspot.lon, hotspot.lat] },
        properties: { name: hotspot.name || hotspot.id },
      },
    });
    map.addLayer({
      id: "sv-pin-halo",
      type: "circle",
      source: "sv-pin",
      paint: {
        "circle-radius": 14,
        "circle-color": "#c2410c",
        "circle-opacity": 0.22,
        "circle-pitch-alignment": "map",
      },
    });
    map.addLayer({
      id: "sv-pin",
      type: "circle",
      source: "sv-pin",
      paint: {
        "circle-radius": 7,
        "circle-color": "#c2410c",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#14161a",
        "circle-pitch-alignment": "map",
      },
    });
  }

  function setChrome(hotspot) {
    const title = $("sv3dTitle");
    const sub = $("sv3dSub");
    const honesty = $("sv3dHonesty");
    const hudName = $("sv3dHudName");
    if (title) title.textContent = hotspot.label || hotspot.name || hotspot.id;
    if (hudName) hudName.textContent = hotspot.label || hotspot.name || hotspot.id;
    if (sub) {
      const kind =
        hotspot.kind === "floodnet_post"
          ? "FloodNet post · street sensor"
          : "Shortlist station · HAND screening";
      const fn =
        hotspot.floodnet_obs_peak_cm != null
          ? " · FloodNet obs peak " + hotspot.floodnet_obs_peak_cm + " cm (not blended)"
          : "";
      sub.textContent = kind + fn;
    }
    if (honesty) {
      const fm = hotspot.flood_model || (STATE.scene && STATE.scene.flood_model) || {};
      const modelNote =
        fm.kind || fm.model
          ? " Curb/street = road buffer − footprints × HAND lead."
          : "";
      honesty.textContent =
        (hotspot.honesty ||
          (STATE.scene && STATE.scene.honesty) ||
          "Research HAND cm · not photogrammetry street-truth.") + modelNote;
    }
    const hudNote = document.querySelector("#streetView3d .sv-hud-note");
    if (hudNote) {
      const src =
        hotspot.flood_model && hotspot.flood_model.road_source
          ? hotspot.flood_model.road_source
          : "road buffers";
      hudNote.textContent =
        "Curb/street HAND · " +
        src.replace(/_/g, " ") +
        " − footprints · not hydraulic free surface";
    }
  }

  async function openStreetView3d(hotspotHint, opts) {
    const panel = $("streetView3d");
    if (!panel) return;
    const status = $("sv3dStatus");
    const id = resolveHotspotId(hotspotHint);
    if (!id) return;
    opts = opts || {};

    const alreadyOpen = STATE.open;
    const sameHotspot = alreadyOpen && STATE.hotspotId === id;
    const forceFly = opts.forceFly !== false; // default: always move camera on select/open
    setPanelOpen(true);
    if (status) {
      status.textContent =
        alreadyOpen && !sameHotspot
          ? "Flying to hotspot…"
          : alreadyOpen && sameHotspot && forceFly
            ? "Re-centering hotspot…"
            : sameHotspot
              ? "Scrub the Decision Desk timeline — 3D depth follows HAND lead frames."
              : "Loading 3D scene…";
    }
    STATE.loading = true;

    try {
      const scene = await ensureScene();
      let hotspot = findHotspot(scene, id);
      const hintCoords = coordsFromHint(hotspotHint);
      if (!hotspot && hotspotHint && typeof hotspotHint === "object" && hintCoords) {
        hotspot = {
          id: id,
          kind: hotspotHint.kind || (hotspotHint.sensor_id ? "floodnet_post" : "shortlist_station"),
          name: hotspotHint.name || hotspotHint.sensor_name || id,
          label: hotspotHint.label || hotspotHint.name || hotspotHint.sensor_name || id,
          lon: hintCoords.lon,
          lat: hintCoords.lat,
          floodnet_obs_peak_cm:
            hotspotHint.floodnet_obs_peak_cm != null
              ? hotspotHint.floodnet_obs_peak_cm
              : hotspotHint.obs_peak_m != null
                ? Number(hotspotHint.obs_peak_m) * 100
                : null,
          depth_series_leads_h:
            hotspotHint.depth_series_leads_h ||
            (scene.timeline && scene.timeline.leads_h) ||
            [],
          depth_series_cm: hotspotHint.depth_series_cm || [],
          camera: {
            center: [hintCoords.lon, hintCoords.lat],
            zoom: 17.2,
            pitch: 60,
            bearing: -20,
          },
          buildings: hotspotHint.buildings || null,
          depth_polygon: hotspotHint.depth_polygon || null,
          honesty: hotspotHint.honesty || scene.honesty,
        };
      }
      // Scene hotspot with stale/missing coords — prefer live select hint.
      if (hotspot && hintCoords && (hotspot.lon == null || hotspot.lat == null)) {
        hotspot = Object.assign({}, hotspot, {
          lon: hintCoords.lon,
          lat: hintCoords.lat,
          camera: Object.assign({}, hotspot.camera || {}, {
            center: [hintCoords.lon, hintCoords.lat],
          }),
        });
      }
      if (!hotspot || hotspot.lon == null || hotspot.lat == null) {
        throw new Error("No 3D scene for " + id);
      }

      const switchingHotspot = !!(STATE.hotspotId && STATE.hotspotId !== hotspot.id);
      // Prefer scene index roads / flood_model (street flood centreline + honesty).
      if (STATE.scene) {
        const indexed = findHotspot(STATE.scene, hotspot.id);
        if (indexed) {
          if (!hotspot.roads && indexed.roads) hotspot.roads = indexed.roads;
          if (!hotspot.buildings && indexed.buildings) hotspot.buildings = indexed.buildings;
          if (!hotspot.depth_polygon && indexed.depth_polygon) {
            hotspot.depth_polygon = indexed.depth_polygon;
          }
          if (indexed.flood_model) hotspot.flood_model = indexed.flood_model;
        }
      }
      STATE.hotspotId = hotspot.id;
      STATE.hotspot = hotspot;
      setChrome(hotspot);

      requestAnimationFrame(() => {
        const el = $("sv3dMap");
        if (el) el.style.minHeight = "240px";
      });

      await ensureMap(hotspot, {
        animate: opts.animate === false ? false : true,
        flyMs: switchingHotspot || alreadyOpen ? FLY_MS : OPEN_EASE_MS,
      });

      if (hotspot.buildings && hotspot.depth_polygon) {
        await loadHotspotLayers(hotspot);
      }

      const animate = opts.animate !== false;
      const shouldMove = forceFly || !sameHotspot || !alreadyOpen;
      if (shouldMove) {
        const useFly = switchingHotspot || alreadyOpen || opts.method === "flyTo";
        scheduleCameraMove(hotspot, {
          animate: animate,
          duration: useFly ? FLY_MS : OPEN_EASE_MS,
          method: useFly ? "flyTo" : "easeTo",
        });
      } else if (STATE.map) {
        try {
          STATE.map.resize();
        } catch (err) {}
      }

      syncToLead(currentLeadHours());
      startWaterPulse();
      updateLabelMarker();
      if (status) {
        status.textContent =
          "Scrub timeline for curb/street HAND water · select shortlist/FloodNet to flyTo.";
      }
    } catch (err) {
      console.error(err);
      if (status) {
        status.textContent =
          "3D view unavailable: " + (err && err.message ? err.message : String(err));
      }
    } finally {
      STATE.loading = false;
    }
  }

  function closeStreetView3d() {
    stopAnim();
    stopPulse();
    setPanelOpen(false);
    STATE.hotspotId = null;
    STATE.hotspot = null;
  }

  function maybeOfferButton(id) {
    const btn = $("sv3dOpenBtn");
    if (!btn) return;
    const ok = canOpenId(id);
    btn.hidden = !ok;
    btn.disabled = !ok;
    if (ok) btn.dataset.hotspotId = id;
  }

  function wireUi() {
    const close = $("sv3dClose");
    if (close) close.addEventListener("click", closeStreetView3d);
    const btn = $("sv3dOpenBtn");
    if (btn) {
      btn.addEventListener("click", () => {
        const id = btn.dataset.hotspotId || STATE.hotspotId;
        if (!id) return;
        if (typeof global.setViewMode === "function") {
          try {
            global.__streetViewOpenHint = id;
            global.setViewMode("3d");
            return;
          } catch (err) {
            console.warn(err);
          }
        }
        openStreetView3d(id);
      });
    }
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && STATE.open) {
        e.stopPropagation();
        e.preventDefault();
        closeStreetView3d();
      }
    });
    ensureScene()
      .then(() => {
        if (global.selectedId) maybeOfferButton(global.selectedId);
        if (global.selectedFloodnetId) maybeOfferButton(global.selectedFloodnetId);
      })
      .catch(() => {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireUi);
  } else {
    wireUi();
  }

  global.StreetView3D = {
    open: openStreetView3d,
    close: closeStreetView3d,
    syncToLead: syncToLead,
    maybeOfferButton: maybeOfferButton,
    canOpenId: canOpenId,
    flyToHotspot: function (hint, opts) {
      const id = resolveHotspotId(hint);
      if (!id) return;
      const openOpts = Object.assign({ animate: true, forceFly: true, method: "flyTo" }, opts || {});
      // Prefer the full hint object so lat/lon survive when id is not in 3d_scene.json.
      const payload = hint && typeof hint === "object" ? hint : id;
      if (STATE.open || (global.document && document.body.classList.contains("view-3d"))) {
        openStreetView3d(payload, openOpts);
      } else if (typeof global.setViewMode === "function") {
        global.__streetViewOpenHint = payload;
        global.setViewMode("3d");
      } else {
        openStreetView3d(payload, openOpts);
      }
    },
    state: STATE,
  };
})(window);
