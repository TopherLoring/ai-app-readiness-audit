> **Work in progress:** Not ready for customer data or a paid pilot. See `docs/BASELINE_AUDIT.md` and `SERVICE_CONTRACT.md`. Existing sales materials contain unvalidated claims.

# AI-Built Application Readiness Audit

Launch-readiness assessment toolkit for applications built with AI coding tools.

**Commercial offer:** $500–$750 fixed-scope diagnostic (see original opportunity brief).

## What it checks

- Broken / missing routes (smoke suite)
- Form validation and password field hygiene
- Obvious client-side secret storage (localStorage, hard-coded keys)
- Auth surface (protected-looking routes reachable without login)
- Basic security headers

**Explicitly not:** a full security audit, penetration test, or “secure app” certification.

## Quick start (demo)

```bash
python demo.py
```

Starts the deliberately flawed sample app, runs the audit, prints the report.

## Audit a live URL

```bash
python -m engine.runner https://your-app.example.com --out reports/ --stdout
```

Optional extra paths:

```bash
python -m engine.runner https://your-app.example.com --path /onboarding --path /billing
```

## Client materials

- `CLIENT_INSTRUCTIONS.md` — one-page client intake
- `docs/service.html` — website service page (update CTA email before publishing)

## Project layout

```
ai-app-readiness-audit/
├── demo.py
├── engine/
│   ├── checks.py
│   ├── reporter.py
│   └── runner.py
├── sample_app/          # Intentionally flawed demo application
├── docs/service.html
├── CLIENT_INSTRUCTIONS.md
└── requirements.txt
```

## Stack

- Python + `requests` (Playwright optional for deeper browser checks later)
- No paid APIs
- Sample app is pure stdlib HTTP server

## Commercial notes

Limit the offer to readiness assessment. Do not market as a comprehensive security audit. Keep fulfillment ≤3 active hours for the standard package.