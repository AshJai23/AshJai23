# 0.4.0 validation — 1 November 2026

- Full local suite: **102 passed in 3.29s**, including real-source Streamlit example, CSV upload, API, invalid inputs, constant baseline and train-only scaling/purged boundaries. `pip check`: no broken requirements.
- Actual three-series ECB model fit and held-out predictions saved in `validation/v0.4.0/ecb-held-out.json`. Model beats persistence on one of three five-observation forecasts, loses on two. No claim of reliable investment timing.
- Pyodide 0.29.0 runs the identical market module and matches CPython metrics/projections within 1e-8; `browser-market-runtime.json`. Existing six scam-engine parity cases and three-row synthetic batch smoke still pass.
- JavaScript syntax check passes. Full authenticated browser UI QA remains blocked by the existing private-site sign-in / unavailable managed preview service. Audience unchanged. Streamlit AppTest actually exercised new UI branches.
- No stock feed, prospective trading, LLM, neural model, personal recommendation, FCA lookup or fraud-classifier training. See MARKET_RESEARCH.md for method and limitations.

## Prior releases (historical evidence)

# Latest validation — 0.3.0, 1 November 2026

- **78 tests passed, zero warnings**, including real Streamlit CSV upload, dashboard
  rendering/clearing, schema/size/row limits, API behaviour and output privacy.
- Dependency check: no broken requirements. Package and engine both 0.3.0.
- Actual Streamlit health and page checks: HTTP 200 on the local launch process.
- Actual API health and batch POST: HTTP 200 using the explicitly synthetic
  three-row template. Two rows had configured indicators; this is not accuracy.
- Validation JSON and test output: `validation/v0.3.0/`. API smoke process stopped
  after checking; Streamlit launch retained. This is not a public hosted URL.
- API validation errors omit submitted values. Batch summaries contain generated
  row numbers/status/codes and generic errors, not messages/firms/URLs/input IDs.
- No real dataset acquisition, model training, FCA lookup or production deployment.

Previous release evidence is preserved below and under validation/.

---

# Validation — 1 November 2026

## Result

Installed all runtime and development dependencies in an isolated Python 3.12.14
virtual environment. Original suite: **14 passing tests**. Updated suite:
**60 passing tests, zero warnings** (0.98 seconds in the saved final run).
`python -m pip check`: no broken requirements. See `validation/summary.json`,
`validation/final-tests.txt` and `requirements.lock.txt` for actual evidence.

## Commands actually exercised

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502 --server.headless true --browser.gatherUsageStats false
.venv/bin/python -m uvicorn smartinvest.api:app --host 127.0.0.1 --port 8001
```

The initial dependency resolver emitted a Starlette TestClient deprecation; the
supported httpx2 development dependency was added and the suite reran cleanly.
The locked dependencies capture the tested environment. For normal local use,
follow README.md; Streamlit's default port is 8501.

## Application checks

- Real Streamlit process started on port 8502. Health returned `200 / ok`; its
  application page returned HTTP 200 (6,467 bytes). Usage telemetry disabled.
- Streamlit AppTest exercised initial render, blank validation, flagged/neutral
  submissions, literal input rendering, report persistence across reruns and
  clearing. No application exceptions in these tests.
- A real local Uvicorn process served API health and an actual HTTP scan POST,
  both HTTP 200. The submitted message was an explicit synthetic fixture;
  response version 0.2.0 and verification status not_checked. API server stopped
  after smoke testing.
- The first cross-execution-session HTTP probe could not reach a server launched
  in another isolated session. A launch-and-probe check in the same session
  succeeded; this is not a public hosted URL or a deployment claim.

## Fixed issues and remaining limits

Negated guaranteed/risk-free claims, hidden later high-return claims, decimal
commas, very large percentages, malformed ports/host syntax and Unicode host
normalisation now have regression tests. URL credentials are redacted from
reports; URL scanning makes no DNS or fetch calls. Core/API limits and session
clearing are tested. A metadata-only time/campaign split guard is implemented.

No FCA records were ingested, no model was trained, no data-science performance
was estimated and no public service was launched. Rule thresholds and negation
remain heuristic. See DATA_PROVENANCE.md and EVALUATION_PROTOCOL.md for the next
research steps and evidence gates.
