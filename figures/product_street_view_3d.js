/**
 * MapLibre GL street-level 3D hotspot view for Decision Desk.
 * Research HAND/MRMS lead-frame screening — NOT photogrammetry street-truth.
 * Lazy-loads product_assets/3d_scene.json (+ per-hotspot GeoJSON) on first open.
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
  };

  const DEFAULT_STYLE = "https://tiles.openfreemap.org/styles/liberty";

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

  function depthColor(cm) {
    if (cm >= 15) return "#08306b";
    if (cm >= 8) return "#4292c6";
    if (cm >= 3) return "#9ecae1";
    return "#dbeafe";
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
        id.indexOf("floodnet:") === 0
      );
    }
    return !!findHotspot(STATE.scene, id);
  }

  function setPanelOpen(open) {
    const panel = $("streetView3d");
    if (!panel) return;
    panel.hidden = !open;
    panel.setAttribute("aria-hidden", open ? "false" : "true");
    document.body.classList.toggle("street-view-open", open);
    STATE.open = open;
  }

  function updateReadout() {
    const leadEl = $("sv3dLead");
    const depthEl = $("sv3dDepth");
    const bandEl = $("sv3dBand");
    if (leadEl) leadEl.textContent = "+" + STATE.leadH + "h";
    if (depthEl) depthEl.textContent = STATE.depthCm.toFixed(1) + " cm";
    let band = "<3 cm";
    if (STATE.depthCm >= 15) band = "≥15 cm";
    else if (STATE.depthCm >= 8) band = "≥8 cm";
    else if (STATE.depthCm >= 3) band = "≥3 cm";
    if (bandEl) bandEl.textContent = band;
  }

  function applyDepthExtrusion(cm) {
    const map = STATE.map;
    if (!map || !map.getLayer("sv-depth-extrusion")) return;
    const h = Math.max(0.05, Math.min(4.5, (cm / 100) * 3.2)); // cm → modest metres visual
    const color = depthColor(cm);
    const opacity = cm < 0.5 ? 0.08 : Math.min(0.78, 0.22 + cm / 28);
    map.setPaintProperty("sv-depth-extrusion", "fill-extrusion-height", h);
    map.setPaintProperty("sv-depth-extrusion", "fill-extrusion-color", color);
    map.setPaintProperty("sv-depth-extrusion", "fill-extrusion-opacity", opacity);
  }

  function syncToLead(leadHours) {
    if (!STATE.open || !STATE.hotspot) return;
    const d = nearestLeadDepth(STATE.hotspot, leadHours);
    STATE.leadH = d.lead;
    STATE.depthCm = d.cm;
    updateReadout();
    applyDepthExtrusion(d.cm);
  }

  function destroyMap() {
    if (!STATE.map) return;
    try {
      STATE.map.remove();
    } catch (err) {
      console.warn("MapLibre remove:", err);
    }
    STATE.map = null;
    STATE.styleUrl = null;
  }

  async function ensureMap(hotspot) {
    if (typeof maplibregl === "undefined") {
      throw new Error("MapLibre GL not loaded (vendor/maplibre)");
    }
    const scene = STATE.scene;
    const styleUrl = desiredStyleUrl(scene);
    const cam = hotspot.camera || {
      center: [hotspot.lon, hotspot.lat],
      zoom: 17.2,
      pitch: 60,
      bearing: 0,
    };

    if (STATE.map && STATE.styleUrl === styleUrl) {
      STATE.map.jumpTo({
        center: cam.center,
        zoom: cam.zoom,
        pitch: cam.pitch,
        bearing: cam.bearing,
      });
      return STATE.map;
    }

    destroyMap();

    const map = new maplibregl.Map({
      container: "sv3dMap",
      style: styleUrl,
      center: cam.center,
      zoom: cam.zoom,
      pitch: cam.pitch,
      bearing: cam.bearing,
      maxPitch: 85,
      attributionControl: true,
      hash: false,
      // Avoid blank first frame when the panel was just un-hidden.
      preserveDrawingBuffer: false,
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
      // Safety timeout so UI never hangs forever offline.
      setTimeout(finish, 10000);
    });

    // Optional terrain only when explicitly enabled with a non-demotiles source.
    // demotiles terrain 404s over NYC and can blank the street view.
    try {
      const basemap = scene.basemap || {};
      const terrainUrl = basemap.terrain_source;
      const wantTerrain = !!basemap.terrain_enabled && terrainUrl &&
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

  async function loadHotspotLayers(hotspot) {
    const map = STATE.map;
    const base = assetsBase();

    // Remove prior hotspot layers/sources
    ["sv-depth-extrusion", "sv-buildings-extrusion", "sv-pin"].forEach((id) => {
      if (map.getLayer(id)) map.removeLayer(id);
    });
    ["sv-depth", "sv-buildings", "sv-pin"].forEach((id) => {
      if (map.getSource(id)) map.removeSource(id);
    });

    const [bRes, dRes] = await Promise.all([
      fetch(base + hotspot.buildings, { cache: "no-cache" }),
      fetch(base + hotspot.depth_polygon, { cache: "no-cache" }),
    ]);
    if (!bRes.ok) throw new Error("buildings geojson " + bRes.status);
    if (!dRes.ok) throw new Error("depth geojson " + dRes.status);
    const buildings = await bRes.json();
    const depth = await dRes.json();

    map.addSource("sv-buildings", { type: "geojson", data: buildings });
    map.addLayer({
      id: "sv-buildings-extrusion",
      type: "fill-extrusion",
      source: "sv-buildings",
      paint: {
        "fill-extrusion-color": "#c4c9d1",
        "fill-extrusion-height": [
          "coalesce",
          ["to-number", ["get", "extrusion_m"]],
          ["to-number", ["get", "height_roof"]],
          12,
        ],
        "fill-extrusion-base": 0,
        "fill-extrusion-opacity": 0.88,
      },
    });

    map.addSource("sv-depth", { type: "geojson", data: depth });
    map.addLayer({
      id: "sv-depth-extrusion",
      type: "fill-extrusion",
      source: "sv-depth",
      paint: {
        "fill-extrusion-color": depthColor(0),
        "fill-extrusion-height": 0.05,
        "fill-extrusion-base": 0,
        "fill-extrusion-opacity": 0.1,
      },
    });

    map.addSource("sv-pin", {
      type: "geojson",
      data: {
        type: "Feature",
        geometry: { type: "Point", coordinates: [hotspot.lon, hotspot.lat] },
        properties: { name: hotspot.name || hotspot.id },
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
      },
    });
  }

  function setChrome(hotspot) {
    const title = $("sv3dTitle");
    const sub = $("sv3dSub");
    const honesty = $("sv3dHonesty");
    if (title) title.textContent = hotspot.label || hotspot.name || hotspot.id;
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
      honesty.textContent =
        hotspot.honesty ||
        (STATE.scene && STATE.scene.honesty) ||
        "Research HAND cm · not photogrammetry street-truth.";
    }
  }

  async function openStreetView3d(hotspotHint) {
    const panel = $("streetView3d");
    if (!panel) return;
    const status = $("sv3dStatus");
    const id = resolveHotspotId(hotspotHint);
    if (!id) return;

    setPanelOpen(true);
    if (status) status.textContent = "Loading 3D scene…";
    STATE.loading = true;

    try {
      const scene = await ensureScene();
      let hotspot = findHotspot(scene, id);
      if (!hotspot && hotspotHint && typeof hotspotHint === "object") {
        // Fallback ephemeral hotspot from FloodNet/desk props (no buildings file).
        hotspot = {
          id: id,
          name: hotspotHint.name || hotspotHint.sensor_name || id,
          label: hotspotHint.name || hotspotHint.sensor_name || id,
          lon: hotspotHint.lon,
          lat: hotspotHint.lat,
          depth_series_leads_h: hotspotHint.depth_series_leads_h || (scene.timeline && scene.timeline.leads_h) || [],
          depth_series_cm: hotspotHint.depth_series_cm || [],
          camera: {
            center: [hotspotHint.lon, hotspotHint.lat],
            zoom: 17.2,
            pitch: 60,
            bearing: -20,
          },
          buildings: null,
          depth_polygon: null,
          honesty: scene.honesty,
        };
      }
      if (!hotspot || hotspot.lon == null || hotspot.lat == null) {
        throw new Error("No 3D scene for " + id);
      }

      STATE.hotspotId = hotspot.id;
      STATE.hotspot = hotspot;
      setChrome(hotspot);

      // Resize before style load so MapLibre gets a non-zero container.
      requestAnimationFrame(() => {
        const el = $("sv3dMap");
        if (el) {
          el.style.minHeight = "240px";
        }
      });

      await ensureMap(hotspot);

      if (hotspot.buildings && hotspot.depth_polygon) {
        await loadHotspotLayers(hotspot);
      }

      // Resize after panel becomes visible + layers attached.
      requestAnimationFrame(() => {
        if (STATE.map) {
          STATE.map.resize();
          const cam = hotspot.camera || {};
          STATE.map.easeTo({
            center: cam.center || [hotspot.lon, hotspot.lat],
            zoom: cam.zoom || 17.2,
            pitch: cam.pitch || 60,
            bearing: cam.bearing || 0,
            duration: 0,
          });
        }
      });

      syncToLead(currentLeadHours());
      if (status) {
        status.textContent =
          "Scrub the Decision Desk timeline — 3D depth follows HAND lead frames.";
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
    setPanelOpen(false);
    STATE.hotspotId = null;
    STATE.hotspot = null;
    // Keep map instance warm for next open (faster) unless style was bad.
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
        if (id) openStreetView3d(id);
      });
    }
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && STATE.open) {
        e.stopPropagation();
        e.preventDefault();
        closeStreetView3d();
      }
    });
    // Prefetch scene index quietly so canOpenId is accurate.
    ensureScene().then(() => {
      if (global.selectedId) maybeOfferButton(global.selectedId);
      if (global.selectedFloodnetId) maybeOfferButton(global.selectedFloodnetId);
    }).catch(() => {});
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
    state: STATE,
  };
})(window);
