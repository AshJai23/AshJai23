# SmartInvest AI: FastAPI application

Release 0.4.1 makes FastAPI the primary local backend and serves a simple same-origin web workspace at `/`. Existing detection and price-analysis logic are reused unchanged. The alternative Streamlit app and private Pyodide demo are preserved.

## Start

From `projects/smartinvest-ai`, with Python 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
python -m pip install --no-build-isolation --no-deps -e .
python -m uvicorn smartinvest.api:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open http://127.0.0.1:8000/ on the same computer; API docs: http://127.0.0.1:8000/docs. If port 8000 is occupied, choose `--port 8001` and open http://127.0.0.1:8001/. These are loopback addresses, not publicly deployed websites. Stop with Ctrl+C. No public FastAPI hosting has been provisioned.

The UI handles offer screening, batch CSV review and market research. Price CSV columns must be exactly `date,symbol,price,currency`; see [MARKET_RESEARCH.md](MARKET_RESEARCH.md). Download the example CSV from GitHub using its Raw/Download control, then upload it. Source: ECB historical daily reference snapshot ending 30 October 2026. It is not a live stock feed, stock selection or investment recommendation.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | / | FastAPI-served HTML workspace |
| GET | /assets/app.js | Fixed packaged browser client |
| GET | /docs | Interactive OpenAPI documentation |
| GET | /v1/health | Process health |
| POST | /v1/scans | Explainable warning indicators |
| POST | /v1/batch-scans | Offer CSV review |
| POST | /v1/market-research | Fitted price research and held-out comparisons |

The web assets are included as Python package data. No user-controlled filesystem route is exposed. The UI makes relative same-origin JSON requests; Python runs in the FastAPI process rather than the visitor's browser. UI requests have a 90-second client timeout, which does not cancel server-side work. Buttons are disabled during a request. Inputs clear from the page with Clear; exported files remain wherever the user saves them.

No credentials, database, scan persistence, external notifications or arbitrary URL fetching are added. No personal best investment, FCA verification, fraud classifier, buy/sell order or guaranteed return is provided. The default localhost binding and `--no-access-log` reduce exposure. UI output uses text nodes, and the workspace has no-store, nosniff, no-referrer and restrictive CSP headers. The optional Swagger docs use their upstream default CDN assets. This remains a research prototype without authentication, public abuse controls, production operations or professional suitability review.

## Verification

```bash
python -m pytest -q
python scripts/smoke_fastapi.py
node --check src/smartinvest/web/app.js
```

The smoke script launches a temporary Uvicorn process on a random loopback port, exercises HTML, JavaScript, health, OpenAPI and all three POST routes, then stops the process. Scam/batch smoke inputs are labelled synthetic; market smoke uses the real attributed ECB replay. No permanent server is left running. Tests also check packaged resources, non-exposure of arbitrary files, OpenAPI route compatibility and validation-error privacy.

The authoring session's local execution runtime was unavailable on 2 November 2026. GitHub Actions is the execution environment for this increment; its actual logs, rather than a prewritten pass claim, are authoritative. Full graphical browser interaction and a public FastAPI deployment are not verified. Existing historical evidence for 0.4.0 remains separate.

Implementation reference: [FastAPI custom responses](https://fastapi.tiangolo.com/advanced/custom-response/).
