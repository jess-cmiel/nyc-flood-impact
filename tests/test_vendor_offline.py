"""Vendored Leaflet/fonts present for offline demo serve."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "figures" / "vendor"


def test_leaflet_vendor_files_exist():
    base = VENDOR / "leaflet" / "1.9.4"
    assert (base / "leaflet.js").exists()
    assert (base / "leaflet.css").exists()
    assert (base / "images" / "marker-icon.png").exists()


def test_fonts_vendor_files_exist():
    assert (VENDOR / "fonts" / "fonts.css").exists()
    woff = list((VENDOR / "fonts" / "woff2").glob("*.woff2"))
    assert len(woff) >= 3
    css = (VENDOR / "fonts" / "fonts.css").read_text()
    assert "fonts.googleapis.com" not in css
    assert "fonts.gstatic.com" not in css


def test_product_html_uses_vendor_not_cdn():
    html = (ROOT / "figures" / "product_map.html").read_text()
    assert "vendor/leaflet/1.9.4/leaflet.js" in html
    assert "vendor/fonts/fonts.css" in html
    assert "unpkg.com/leaflet" not in html
    assert "fonts.googleapis.com" not in html
    assert "PaperBasemap" in html or "paperBasemap" in html


def test_vendor_checksums_file():
    assert (VENDOR / "SHA256SUMS").exists()
    assert len((VENDOR / "SHA256SUMS").read_text().strip().splitlines()) >= 5
