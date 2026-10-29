#!/usr/bin/env python3
"""Minimal static server for the deliberately flawed sample app."""

from __future__ import annotations
import http.server
import socketserver
from pathlib import Path

PORT = 8765
DIR = Path(__file__).parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIR), **kwargs)

    def do_GET(self):
        # Map clean paths
        if self.path in ("/", "/index.html"):
            self.path = "/index.html"
        elif self.path == "/dashboard":
            self.path = "/dashboard.html"
        # /settings and /admin intentionally 404
        return super().do_GET()

    def log_message(self, fmt, *args):
        print(f"[sample-app] {args[0]}")


if __name__ == "__main__":
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Sample app serving at http://127.0.0.1:{PORT}")
        print("Intentionally broken routes: /settings, /admin, /reports/export")
        httpd.serve_forever()