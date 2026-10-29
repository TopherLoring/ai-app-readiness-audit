"""Readiness checks: smoke routes, basic security hygiene, form issues, config smells."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urljoin, urlparse

import requests


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


@dataclass
class Finding:
    check_id: str
    title: str
    severity: Severity
    description: str
    evidence: str
    recommendation: str
    effort_minutes: int = 15
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "title": self.title,
            "severity": self.severity.value,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "effort_minutes": self.effort_minutes,
            "tags": self.tags,
        }


DEFAULT_TIMEOUT = 8


def run_smoke_suite(base_url: str, extra_paths: list[str] | None = None) -> list[Finding]:
    """Hit a standard set of routes and record accessibility / status issues."""
    findings: list[Finding] = []
    base = base_url.rstrip("/") + "/"
    session = requests.Session()
    session.headers.update({"User-Agent": "AI-App-Readiness-Audit/1.0"})

    paths = ["/", "/dashboard", "/settings", "/admin", "/login", "/signup", "/api/health"]
    if extra_paths:
        paths.extend(extra_paths)

    results = []
    for path in paths:
        url = urljoin(base, path.lstrip("/"))
        try:
            r = session.get(url, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
            results.append((path, r.status_code, r.url, len(r.content), r.headers))
        except requests.RequestException as e:
            results.append((path, None, url, 0, str(e)))
            findings.append(
                Finding(
                    check_id="SMOKE-001",
                    title=f"Route unreachable: {path}",
                    severity=Severity.HIGH,
                    description=f"Could not reach `{path}`. Network error or server down.",
                    evidence=str(e),
                    recommendation="Confirm the application is deployed and the URL is correct. Check DNS, TLS, and process health.",
                    effort_minutes=20,
                    tags=["availability", "smoke"],
                )
            )

    # Analyze status codes
    for path, status, final_url, size, headers in results:
        if status is None:
            continue
        if path in ("/settings", "/admin") and status == 404:
            findings.append(
                Finding(
                    check_id="NAV-001",
                    title=f"Broken navigation target: {path}",
                    severity=Severity.HIGH,
                    description=f"Linked or expected route `{path}` returns 404. Users hitting this path from navigation will see a dead end.",
                    evidence=f"GET {path} → {status}",
                    recommendation="Either implement the page or remove/hide the navigation link. Broken nav is a common AI-generated app issue.",
                    effort_minutes=15,
                    tags=["navigation", "ux"],
                )
            )
        elif status >= 500:
            findings.append(
                Finding(
                    check_id="SMOKE-002",
                    title=f"Server error on {path}",
                    severity=Severity.CRITICAL,
                    description=f"`{path}` returned HTTP {status}. Application errors on core routes block launch readiness.",
                    evidence=f"GET {path} → {status}",
                    recommendation="Inspect server logs for this route. Fix the underlying exception before any launch.",
                    effort_minutes=30,
                    tags=["availability", "stability"],
                )
            )
        elif path == "/" and status == 200 and size < 200:
            findings.append(
                Finding(
                    check_id="SMOKE-003",
                    title="Home page content suspiciously small",
                    severity=Severity.MEDIUM,
                    description="Root path returned a very small body. Possible blank page or misconfigured deploy.",
                    evidence=f"GET / → {status}, body_bytes={size}",
                    recommendation="Open the URL in a browser and confirm meaningful content renders.",
                    effort_minutes=10,
                    tags=["smoke"],
                )
            )

    # Basic security headers on home
    home = next((r for r in results if r[0] == "/"), None)
    if home and home[1] == 200 and isinstance(home[4], dict):
        headers = {k.lower(): v for k, v in home[4].items()}
        missing = []
        for h in ("x-frame-options", "content-security-policy", "x-content-type-options"):
            if h not in headers:
                missing.append(h)
        if missing:
            findings.append(
                Finding(
                    check_id="SEC-001",
                    title="Missing common security headers",
                    severity=Severity.MEDIUM,
                    description="Home response lacks one or more standard hardening headers.",
                    evidence=f"Missing: {', '.join(missing)}",
                    recommendation="Add at least X-Frame-Options, X-Content-Type-Options, and a basic Content-Security-Policy. Not a full security audit — basic hygiene only.",
                    effort_minutes=20,
                    tags=["security-hygiene"],
                )
            )

    return findings


def check_html_hygiene(base_url: str) -> list[Finding]:
    """Fetch home HTML and look for common AI-app failure patterns."""
    findings: list[Finding] = []
    try:
        r = requests.get(base_url.rstrip("/") + "/", timeout=DEFAULT_TIMEOUT)
        html = r.text.lower()
    except requests.RequestException as e:
        return [
            Finding(
                check_id="HTML-000",
                title="Could not fetch home HTML",
                severity=Severity.HIGH,
                description=str(e),
                evidence=str(e),
                recommendation="Ensure the app is reachable before running HTML hygiene checks.",
                tags=["availability"],
            )
        ]

    # Password field type=text (insecure / bad UX)
    if 'type="text"' in html and "password" in html:
        # crude but effective for demo
        if "name=\"password\"" in html or 'name="password"' in html:
            findings.append(
                Finding(
                    check_id="FORM-001",
                    title="Password input not using type=password",
                    severity=Severity.HIGH,
                    description="A password field appears to use type=text, so the value is visible while typing and may be cached/autocompleted insecurely.",
                    evidence="password field with type=text detected in home HTML",
                    recommendation="Change the input to type=\"password\". Add basic client-side required checks and never log passwords.",
                    effort_minutes=5,
                    tags=["forms", "security-hygiene"],
                )
            )

    # localStorage credential patterns
    if "localstorage" in html and ("password" in html or "token" in html or "sk_" in html):
        findings.append(
            Finding(
                check_id="SEC-002",
                title="Possible credentials stored in localStorage",
                severity=Severity.HIGH,
                description="Script references suggest secrets or passwords may be written to localStorage. This is a common AI-generated anti-pattern.",
                evidence="localStorage usage co-located with password/token-like strings",
                recommendation="Never store passwords or long-lived API keys in localStorage. Use httpOnly cookies or a proper session mechanism.",
                effort_minutes=25,
                tags=["security-hygiene", "auth"],
            )
        )

    # Missing form validation signals
    if "<form" in html and "required" not in html and "pattern=" not in html:
        findings.append(
            Finding(
                check_id="FORM-002",
                title="No obvious client-side form validation",
                severity=Severity.MEDIUM,
                description="Forms are present but no HTML5 required/pattern attributes were found. Invalid data may reach the server (or fake success handlers).",
                evidence="form tags present; no required/pattern attributes detected",
                recommendation="Add required fields, email type, and minimal length checks. Validate again on the server.",
                effort_minutes=15,
                tags=["forms", "data-quality"],
            )
        )

    # Hard-coded secret-looking strings
    for marker in ("sk_live_", "sk_test_", "api_key=", "apikey=", "secret="):
        if marker in html:
            findings.append(
                Finding(
                    check_id="SEC-003",
                    title="Possible hard-coded secret in client HTML/JS",
                    severity=Severity.CRITICAL,
                    description=f"Client-side code appears to contain a secret-like marker (`{marker}`). Secrets in the browser are fully exposed.",
                    evidence=f"marker `{marker}` found in home HTML/JS",
                    recommendation="Move secrets to server-side environment variables. Rotate any key that was committed or shipped to the browser.",
                    effort_minutes=30,
                    tags=["security-hygiene", "secrets"],
                )
            )
            break

    return findings


def check_auth_surface(base_url: str) -> list[Finding]:
    """Basic checks: protected-looking routes accessible without auth."""
    findings: list[Finding] = []
    session = requests.Session()
    for path in ("/dashboard", "/admin", "/settings", "/account", "/api/me"):
        url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
        try:
            r = session.get(url, timeout=DEFAULT_TIMEOUT, allow_redirects=False)
        except requests.RequestException:
            continue
        # If we get 200 on a path that sounds protected, flag it
        if r.status_code == 200 and path in ("/dashboard", "/admin", "/account", "/api/me"):
            findings.append(
                Finding(
                    check_id="AUTH-001",
                    title=f"Potentially protected route accessible without auth: {path}",
                    severity=Severity.HIGH,
                    description=(
                        f"`{path}` returned 200 without an obvious auth redirect. "
                        "If this page should require login, the auth gate is missing or broken."
                    ),
                    evidence=f"GET {path} → {r.status_code} (no redirect)",
                    recommendation="Enforce authentication server-side for all non-public routes. Do not rely only on client-side route guards.",
                    effort_minutes=25,
                    tags=["auth", "access-control"],
                )
            )
    return findings


def run_all(base_url: str, extra_paths: list[str] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(run_smoke_suite(base_url, extra_paths))
    findings.extend(check_html_hygiene(base_url))
    findings.extend(check_auth_surface(base_url))
    # Deduplicate by check_id + title roughly
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.check_id))
    return findings