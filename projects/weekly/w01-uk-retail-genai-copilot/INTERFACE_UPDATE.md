# Sales planner interface update — 4 November 2026

The forecast workspace now uses a navy sidebar, responsive CSS layout, focused upload card, accessible seven-point SVG chart, empirical ranges, daily table, next-week total, weakest-day and week-to-date cards. Historical SQL/source-search remains a separate optional panel. Numerical methods, data history and existing model-quality results are unchanged.

## Fix for stray characters on Windows

The HTML and JavaScript were UTF-8 files, but `Path.read_text()` previously used the host default encoding. On Windows configurations using cp1252, UTF-8 characters such as `£`, `·` and `…` can become mojibake (`Â£`, `Â·`, etc.). The server now reads HTML, JavaScript and CSS with `encoding='utf-8'` and serves UTF-8 content types. A regression test requires explicit UTF-8 for each web-file read and checks the returned text. This addresses the encoding path; native Windows graphical execution was unavailable.

CSS is a separate `/assets/styles.css` asset. The content security policy allows scripts/styles from this server only. No external fonts, CDN, analytics or JavaScript framework is needed. No uploaded values are inserted as HTML.

## Update and run in PowerShell

From your `w01-uk-retail-genai-copilot` project folder:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r requirements-api.txt
.\.venv\Scripts\python.exe serve.py --baseline
```

Stop the old server with Ctrl+C before restarting. Open the printed `http://127.0.0.1:8000/` on the same computer. Press Ctrl+F5 to refresh. A localhost address works only while your local server is running. This update has not deployed a public website or changed your computer.

Upload a `date,sales` CSV with 196 or more complete consecutive days, choose the currency and select **Forecast next 7 days**. Or select **Try fictional sample data**. The sample generates 365 seeded fictional daily GBP values ending yesterday according to the browser's calendar, with deliberately lower Tuesday factors. Its chart, scores and exported CSV are explicitly labelled synthetic. They do not establish real-store accuracy or business impact. A date mismatch near midnight between browser/server time zones can require refreshing or using your own completed dates.

Changing the file/currency clears old results. Requests disable relevant controls, suppress duplicate submits, have a timeout and restore controls after errors. The CSV export includes currency and source labels. Downloaded forecasts are outputs, not the `date,sales` input format. Forecast ranges are empirical, may overlap, and do not guarantee coverage. Action ideas are experiments, not proven causes or promotion effects.

## Actual checks

- **61 Python unit tests passed**, including the explicit-encoding regression and earlier safety, source, temporal model and API checks.
- Node simulated-DOM checks passed for upload/currency payloads, file guards, failures, restored controls, duplicate requests, source-labelled export, historical warnings, seven chart points and rows, and a forecast while optional SQL setup is missing.
- Actual HTML/JS was exercised through Linkedom: all JavaScript IDs resolve among 30 unique markup IDs; chart/table/cards render into the DOM; navigation opens the research panel. This is not a layout engine.
- FastAPI TestClient ASGI requests returned UTF-8 HTML, JavaScript and CSS, a seven-date forecast from an explicitly labelled synthetic fixture, and a historical replay using the previously attributed UCI aggregate fixture. No fresh source acquisition or LLM inference was performed for this interface increment.
- Historical replay still reports Ridge MAE £26,846.17 vs last-week £11,250.17. The update does not improve those model scores. Synthetic Tuesday detection is a fixture behaviour check only.

Reproduce from the project folder:

```bash
python -m unittest discover -s tests -v
node test_web.cjs
python smoke_interface.py
```

Evidence: `evidence/2026-11-04/interface-*-validation.json` and the labelled `interface-synthetic-fixture.csv`. Native Windows execution and graphical desktop/mobile review remain unverified: `sites-preview start` and `status` both reported the managed preview relay unavailable. No alternate browser route was used. CSS contains desktop/mobile breakpoints, but DOM tests do not prove visual fit.

W01 remains in progress. LLM answer quality, independent review, n8n execution and release acceptance are still unfinished. This is a reviewable interface increment, not a new project or weekly release.
