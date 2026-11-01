# 0.4.0 — market research extension (1 November 2026)

- Separate price-history research module with fitted Ridge forecasts, purged temporal evaluation, baseline comparisons and residual bands.
- Attributed real ECB daily-reference snapshot; latest observation 30 October. Stock/ETF CSV upload supported, no live stock feed claimed.
- Streamlit, FastAPI and private browser-demo integration. 102 tests and CPython/Pyodide numerical parity checks.
- Scam engine remains 0.3.0 offline rules; no trained fraud classifier or FCA verification.

# Changes

## 0.3.0 — 1 November 2026

- Added offline CSV screening with 2 MiB / 500-row bounds, strict schema and
  per-row validation, without silently returning partial oversized batches.
- Added a Streamlit review dashboard, synthetic template, generated-metadata-only
  CSV export and a batch clear/upload-reset control.
- Added the shared `/v1/batch-scans` API and sanitised request-validation errors
  so submitted messages/tokens are not echoed in error responses.
- Added CSV parsing, limits/privacy, API and actual Streamlit upload regressions.
- Full suite: 78 passing tests. No new dataset, trained model or FCA lookup.

## 0.2.0 — 1 November 2026

- Preserved offline-only screening and `verification_status=not_checked`.
- Added narrow explicit-negation handling and evaluation of all recurring-return
  matches, including decimal commas and percentages above three digits.
- Validate URL ports, whitespace/control characters, backslashes and host labels;
  normalise Unicode hostnames for the existing punycode indicator. No URL fetches.
- Redact URL user-info from reports/excerpts and render matched text literally.
- Keep Streamlit reports across reruns; add a session/input clearing control.
- Version reports and API; resolve current Starlette TestClient deprecation by
  installing its supported httpx2 dependency. Include a tested dependency lock.
- Add API/security/UI regressions and a metadata-only campaign/time split guard.
- Document permitted-data gates, label quality, leakage-safe modelling and limits.
- No ML training, new FCA integration, data scraping or public deployment.
