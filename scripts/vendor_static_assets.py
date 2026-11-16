#!/usr/bin/env python3
"""Vendor Leaflet + brand fonts into figures/vendor for offline demo serve.

Downloads once into the tree; regenerate HTML after. Research demo only.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "figures" / "vendor"
LEAFLET_VER = "1.9.4"
UA = "nyc-flood-impact-vendor/1.0 (+research demo)"


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def vendor_leaflet() -> dict:
    base = f"https://unpkg.com/leaflet@{LEAFLET_VER}/dist"
    out = VENDOR / "leaflet" / LEAFLET_VER
    files = {
        "leaflet.css": f"{base}/leaflet.css",
        "leaflet.js": f"{base}/leaflet.js",
        "images/marker-icon.png": f"{base}/images/marker-icon.png",
        "images/marker-icon-2x.png": f"{base}/images/marker-icon-2x.png",
        "images/marker-shadow.png": f"{base}/images/marker-shadow.png",
        "images/layers.png": f"{base}/images/layers.png",
        "images/layers-2x.png": f"{base}/images/layers-2x.png",
    }
    meta = {"version": LEAFLET_VER, "files": {}}
    for rel, url in files.items():
        data = _fetch(url)
        _write(out / rel, data)
        meta["files"][rel] = {
            "url": url,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
    # Leaflet CSS uses url(images/...) relative — already correct under out/
    (out / "VENDOR.json").write_text(json.dumps(meta, indent=2))
    return meta


def vendor_fonts() -> dict:
    """Download Syne / Figtree / IBM Plex Mono woff2 via Google Fonts CSS API."""
    css_url = (
        "https://fonts.googleapis.com/css2?"
        "family=Syne:wght@600;700;800&"
        "family=Figtree:wght@400;500;600;700&"
        "family=IBM+Plex+Mono:wght@500;600&display=swap"
    )
    # Request woff2-capable CSS
    req = urllib.request.Request(
        css_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/css,*/*;q=0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        css = resp.read().decode("utf-8")

    out = VENDOR / "fonts"
    out.mkdir(parents=True, exist_ok=True)
    urls = sorted(set(re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)))
    meta = {"css_url": css_url, "files": {}, "n_faces": len(urls)}
    rewritten = css
    for i, url in enumerate(urls):
        data = _fetch(url)
        # Keep stable names from path tail
        name = url.split("/")[-1].split("?")[0]
        if not name.endswith(".woff2"):
            name = f"face_{i}.woff2"
        rel = f"woff2/{name}"
        _write(out / rel, data)
        local = f"./woff2/{name}"
        rewritten = rewritten.replace(url, local)
        meta["files"][rel] = {
            "url": url,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
    (out / "fonts.css").write_text(rewritten)
    (out / "VENDOR.json").write_text(json.dumps(meta, indent=2))
    return meta


def write_checksums() -> Path:
    lines = []
    for p in sorted(VENDOR.rglob("*")):
        if not p.is_file() or p.name in ("SHA256SUMS",):
            continue
        if p.suffix == ".json" and p.name == "VENDOR.json":
            pass
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        rel = p.relative_to(VENDOR).as_posix()
        lines.append(f"{h}  {rel}")
    out = VENDOR / "SHA256SUMS"
    out.write_text("\n".join(lines) + "\n")
    return out


def main() -> None:
    VENDOR.mkdir(parents=True, exist_ok=True)
    leaflet = vendor_leaflet()
    fonts = vendor_fonts()
    sums = write_checksums()
    print(
        json.dumps(
            {
                "vendor": str(VENDOR.relative_to(ROOT)),
                "leaflet_files": len(leaflet["files"]),
                "font_faces": fonts["n_faces"],
                "checksums": str(sums.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"vendor failed: {exc}", file=sys.stderr)
        raise
