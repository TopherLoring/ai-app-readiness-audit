#!/usr/bin/env python3
"""
Demonstration of the AI-Built Application Readiness Audit.

Starts the intentionally flawed sample app, runs the audit, prints results.
"""

from __future__ import annotations
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import __version__
from engine.checks import run_all
from engine.reporter import write_reports, render_markdown

SAMPLE_PORT = 8765
BASE_URL = f"http://127.0.0.1:{SAMPLE_PORT}"


def main() -> int:
    print("=" * 64)
    print("AI-Built Application Readiness Audit — Demonstration")
    print(f"Engine v{__version__}")
    print("=" * 64)
    print()
    print("Starting intentionally flawed sample app...")
    print("  Expected issues: broken nav, missing validation,")
    print("  insecure password field, localStorage secrets, open dashboard")
    print()

    serve_script = Path(__file__).parent / "sample_app" / "serve.py"
    proc = subprocess.Popen(
        [sys.executable, str(serve_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        time.sleep(0.8)  # let server bind
        findings = run_all(BASE_URL)
        meta = {"engine_version": __version__, "base_url": BASE_URL}
        out = Path(__file__).parent / "reports"
        md_path, json_path = write_reports(findings, out, meta)

        signals = {
            "broken_nav": any("NAV" in f.check_id or "404" in f.evidence for f in findings),
            "form": any(f.check_id.startswith("FORM") for f in findings),
            "secrets_or_storage": any(f.check_id in ("SEC-002", "SEC-003") for f in findings),
            "auth": any(f.check_id.startswith("AUTH") for f in findings),
        }

        print("Detection checklist:")
        print(f"  [ {'x' if signals['broken_nav'] else ' '} ] Broken navigation / missing pages")
        print(f"  [ {'x' if signals['form'] else ' '} ] Form validation / password field issues")
        print(f"  [ {'x' if signals['secrets_or_storage'] else ' '} ] Insecure credential storage / secrets")
        print(f"  [ {'x' if signals['auth'] else ' '} ] Auth / access-control gaps")
        print()
        print(f"Findings : {len(findings)}")
        print(f"Report   : {md_path}")
        print()
        print("-" * 64)
        print(render_markdown(findings, meta))
        print("-" * 64)

        ok = all(signals.values())
        if ok:
            print("\nDEMO PASSED — core readiness failure modes were identified.")
            return 0
        print("\nDEMO PARTIAL — some expected signals missing (still usable).", file=sys.stderr)
        return 0 if findings else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())