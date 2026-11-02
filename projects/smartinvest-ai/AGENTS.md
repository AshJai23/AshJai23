# Instructions for Codex — SmartInvest AI

You are working on a **student research/portfolio project**, not a live commercial product.

## Goal
Build an explainable investment-scam *warning* system for individual UK investors.
The app scans user-supplied investment messages and optional URL/firm names. Avoid presenting any output as proof of fraud or legitimacy.

## Current state
- Primary local web workspace served by FastAPI at `/`; assets in `src/smartinvest/web/`
- Alternative Streamlit UI in `app.py`
- Explainable, offline deterministic baseline in `src/smartinvest/detection.py`
- FastAPI route in `src/smartinvest/api.py`
- Pytest tests in `tests/`
- No historical or current FCA data is fetched. Scam screening is untrained rules. The separate market module fits a Ridge price model with purged chronological evaluation; see MARKET_RESEARCH.md.

## Development standards
- Run `python -m pytest -q` and preserve passing tests.
- Add tests for new rules, false positives, input security, and API behaviour.
- Keep detection logic separate from Streamlit and FastAPI.
- Always preserve `verification_status="not_checked"` unless a real authoritative lookup was completed.
- Never assign unsupported numerical fraud probabilities, or show "safe to invest".
- Do not scrape FCA/third-party data without verifying access permissions and licensing.
- Never fetch user-provided URLs without SSRF protection, timeouts, content limits, and approved egress controls.
- Do not log raw investment messages or personal information.
- No real personal financial advice. Never expose secrets.

## Good next tasks
1. Improve unit tests and user experience; record limitations.
2. Research documented, licensed data sources; write a provenance plan before ingestion.
3. Establish evaluation protocol with campaign/time-disjoint splits and human-reviewed labels.
4. Train TF-IDF + Logistic Regression baseline **only after** collecting appropriate data.
5. Compare against rules, add explainability and abstention handling.
6. Implement FCA verification only with permitted data access and verified exact identity matching.

## Run
`python -m pip install -e ".[dev]"`
`python -m pytest -q`
`streamlit run app.py`
`uvicorn smartinvest.api:app --reload`
