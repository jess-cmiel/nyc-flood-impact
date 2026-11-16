#!/usr/bin/env python3
"""Serve figures/product_map.html over HTTP so GeoJSON layers can fetch.

file:// opens fail browser fetch/CORS for local GeoJSON and show layer errors.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
from pathlib import Path

from nyc_flash_flood_case_study.config import FIGURES_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default 127.0.0.1; use 0.0.0.0 for LAN)",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=FIGURES_DIR,
        help="Directory containing product_map.html + product_assets/",
    )
    args = parser.parse_args()
    root = args.dir.resolve()
    if not (root / "product_map.html").exists():
        raise SystemExit(f"missing product_map.html under {root}")
    if not (root / "product_assets").is_dir():
        raise SystemExit(f"missing product_assets/ under {root}")
    vendor_js = root / "vendor" / "leaflet" / "1.9.4" / "leaflet.js"
    vendor_fonts = root / "vendor" / "fonts" / "fonts.css"
    if not vendor_js.exists() or not vendor_fonts.exists():
        raise SystemExit(
            "missing figures/vendor (Leaflet/fonts). Run: python scripts/vendor_static_assets.py"
        )

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.host, args.port), handler) as httpd:
        print(f"Serving {root}")
        print(f"Open http://127.0.0.1:{args.port}/product_map.html")
        if args.host not in ("127.0.0.1", "localhost"):
            print(f"Bound on {args.host}:{args.port}")
        print("Offline chrome: vendor/ Leaflet+fonts · paper basemap (uncheck Online streets if offline)")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
