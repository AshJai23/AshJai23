## Run the FastAPI application (0.4.1)

FastAPI is now the primary local backend and serves its own web interface. From `projects/smartinvest-ai`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m pip install --no-build-isolation --no-deps -e .
python -m uvicorn smartinvest.api:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open **http://127.0.0.1:8000/** for the web workspace or **http://127.0.0.1:8000/docs** for interactive API documentation. The loopback URL works only on the computer running that command. Keep the default local binding; no public FastAPI host, authentication or production service is provisioned. The earlier private hosted demo remains a separate browser-local Pyodide version, not this Python server.

- `POST /v1/scans`: investment-offer warning indicators.
- `POST /v1/batch-scans`: CSV offer review.
- `POST /v1/market-research`: price comparisons, fitted forecasts and held-out baseline evaluation.
- `GET /v1/health`: process health.

The browser sends inputs to this FastAPI process. No scan database or raw-message logging is configured; run with `--no-access-log`. Data remains in request/server memory until released, and in the page until cleared. Do not enter secrets. The bundled UI uses same-origin requests, external text rendered with `textContent`, fixed packaged assets and a restrictive content-security policy. It adds no arbitrary URL fetching or FCA lookup. Streamlit remains available as an alternative.

See [FASTAPI_GUIDE.md](FASTAPI_GUIDE.md) for commands, smoke tests, architecture and verification limits.

## Price research and fitted forecasts (0.4.0)

**[Open the private interactive demo](https://smartinvest-ai-lab-ashjai23.denickesolomon2462.chatgpt.site)** using the same ChatGPT account that owns it. Choose **Market research → Try ECB FX example**, or run the full Streamlit application below. This browser interface uses the same Python core through Pyodide; it is separate from the Streamlit UI. Inputs remain in tab memory.

Upload permitted share/ETF price CSVs, compare historical risk, and evaluate 1/5/20-observation Ridge forecasts against persistence. The built-in example is a dated ECB FX snapshot, not a live stock feed. The model loses two of three default held-out comparisons. See [MARKET_RESEARCH.md](MARKET_RESEARCH.md) for exact commands, attribution, measured results and limitations. No best-buy, personal allocation or return guarantee is offered. Scam screening remains offline rules; no trained fraud classifier or FCA lookup.

# SmartInvest AI — Investment Scam Detection (Research Prototype)

A local, **educational** app that highlights some investment-scam warning signs in pasted messages and manually supplied URLs. Scam-engine release: **0.3.0**. Focus: individual UK investors. This is a **portfolio/data science project**, not a startup launch.

**Important:** Scam screening does not train an ML classifier, does not access FCA live data, does not visit websites, does not persist scans to disk or a database, and cannot determine whether any investment is fraudulent or legitimate. Finding zero indicators is **not** a safety assessment.

## What works today

- Streamlit app with text, URL and optional firm inputs.
- Explainable rules for guaranteed returns, risk-free claims, pressure language, private messaging mentions, unusual recurring returns, direct IP/HTTP/shortened/punycode URLs and deceptive user-info URLs.
- Download a JSON screening report; link to official FCA verification resources.
- FastAPI endpoint `/v1/scans` for local API experiments.
- Context-aware rule regressions, API validation and real Streamlit AppTest tests.
- Session-only report persistence, a clear-report control and credential-redacted URL evidence.
- A metadata-only campaign/time split audit for future dataset evaluation.
- Batch CSV review for up to 500 rows / 2 MiB, a review dashboard and privacy-minimised CSV summaries.
- Shared `/v1/batch-scans` API and sanitised request-validation errors.

## Quick start

The package declares Python 3.11+. This release was validated on **Python 3.12.14**; use Python 3.12 for the tested lockfile commands below.

```bash
cd smartinvest-ai-scam-codex
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
python -m pip install --no-deps -e ".[dev]"
python -m pytest -q
python -m streamlit run app.py
```

Streamlit will print a local address (usually http://localhost:8501).

Optional API:

```bash
uvicorn smartinvest.api:app --reload
```

Then visit http://127.0.0.1:8000/docs and try:

```json
{
  "offer_text": "Guaranteed 20% monthly profits. Act now!",
  "website_url": "",
  "claimed_firm": "Example Firm"
}
```

## Architecture

- `src/smartinvest/detection.py`: offline detection core, typed result objects, URL-parsing heuristics.
- `src/smartinvest/api.py`: FastAPI interface.
- `app.py`: Streamlit presentation and JSON report export.
- `tests/`: regression and API tests.
- `AGENTS.md`: instructions Codex should follow.
- `CODEX_START_HERE.md`: copyable Codex starter prompt.

## Honest baseline and research direction

Next research phase: assess usable, licensed real-world investment scam and non-scam datasets; define label quality/provenance; establish time-disjoint and campaign-disjoint test sets; train TF-IDF + Logistic Regression; compare against rules using recall, precision, F1, false-positive rates, calibration if probabilities are reported, and qualitative failure analysis. An FCA verification module is an **unimplemented future task**.

## Data privacy and safety

The screening engine processes text locally and makes no outbound network calls. Inputs and results remain in Streamlit session memory until cleared/session ends; there is no scan database or raw-message file logging. Usage telemetry is disabled in the supplied local configuration. Avoid submitting secrets or personal financial identifiers. For eventual public deployment, implement abuse protection, secure data handling, human review and appropriate UK privacy/regulatory assessment. This repository is not suitable for public production deployment as-is.

## Official resources

- FCA Firm Checker: https://www.fca.org.uk/consumers/fca-firm-checker
- FCA Warning List: https://www.fca.org.uk/consumers/warning-list-unauthorised-firms


## Development evidence and advanced research path

Read [VALIDATION.md](VALIDATION.md) for actual installation, test, application-start
and API evidence. Read [CHANGELOG.md](CHANGELOG.md) for the fixes.

The implemented split auditor can be run with:

```bash
python -m smartinvest.evaluation split-manifest.json
```

See [data provenance/access plan](DATA_PROVENANCE.md) and
[evaluation protocol](EVALUATION_PROTOCOL.md) before collecting data or fitting a
model. Future TF-IDF/Logistic Regression, deep models, calibrated probabilities
and FCA verification remain unimplemented; these documents do not count them
as trained or validated. Do not infer real-world scam accuracy from passing
synthetic rule regressions. The engine's context handling remains heuristic.

## Batch CSV review

Read [BATCH_GUIDE.md](BATCH_GUIDE.md). The downloadable template is synthetic;
screening outcomes are not verified fraud labels or training ground truth.
Batch summaries exclude input messages, firms, URLs and supplied identifiers.
Version 0.3.0 passed 78 tests; actual checks are in validation/v0.3.0/.
