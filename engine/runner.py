#!/usr/bin/env python3
"""CLI for AI-Built Application Readiness Audit."""

from __future__ import annotations
import argparse
import sys

from . import __version__
from .checks import run_all
from .reporter import write_reports, render_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI-Built Application Readiness Audit")
    parser.add_argument("url", help="Base URL of the application (e.g. http://127.0.0.1:8765)")
    parser.add_argument("--path", action="append", default=[], help="Extra path to smoke-test (repeatable)")
    parser.add_argument("--out", default="reports", help="Output directory")
    parser.add_argument("--stdout", action="store_true", help="Print Markdown report")
    args = parser.parse_args(argv)

    findings = run_all(args.url, extra_paths=args.path or None)
    meta = {"engine_version": __version__, "base_url": args.url}
    md_path, json_path = write_reports(findings, args.out, meta)

    print(f"Target   : {args.url}")
    print(f"Findings : {len(findings)}")
    print(f"Markdown : {md_path}")
    print(f"JSON     : {json_path}")

    if args.stdout:
        print("\n" + render_markdown(findings, meta))

    has_blocking = any(f.severity.value in ("critical", "high") for f in findings)
    return 2 if has_blocking else 0


if __name__ == "__main__":
    sys.exit(main())