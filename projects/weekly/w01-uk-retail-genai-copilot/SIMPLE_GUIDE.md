# Start with your next-seven-days forecast

Open the main forecast panel, upload a daily `date,sales` CSV covering at least 196 consecutive completed days, and select its currency. Data through yesterday gives current forecast dates. You can run this panel with `serve.py --baseline` without setting up the optional old UCI SQL warehouse. See [the forecasting guide](DAILY_SALES_FORECAST.md).

The SQL/source-search tools below are optional research tools.

# What this project does

Retail Evidence Lab is a historical retail analytics assistant. A retail analyst chooses a measure and customer country to see a database calculation, or searches the source definitions and product descriptions.

## Start here

After completing the dataset/database setup, start `python serve.py --baseline` in the project environment. Open the local address it prints. The server terminal must stay running.

The page first checks setup and loads the countries actually present in your database. If something is missing, follow the instruction shown above the question form, restart the server after setup, and select Recheck setup.

Choose **Calculate a number**, select **Signed invoice-line value (£)** and **United Kingdom**, then Calculate. The answer covers the full available historical period. Expand the calculation details to inspect the exact decimal value, scope and source.

Choose **Search or ask about the source** and try **Explain the fields** or **Find product descriptions**. Baseline mode returns original source passages without an LLM-written explanation. That is a normal result, not a generation error.

## Words on the page

| Term | Meaning |
| --- | --- |
| Invoice line | One row from an old invoice, with quantity and unit price |
| Signed invoice-line value | Quantity × unit price, including negative lines/adjustments; it is not audited revenue or profit |
| Customer country | The customer-country field recorded in the dataset |
| Deduplication | Removing rows identical across all normalised source fields; genuine repeat lines may also exist |
| Baseline mode | SQL calculations plus keyword search; LLM off |
| Source passage | Original description or project data-definition text supporting the result |

## Project status

Working: real historical source ingestion, auditable database calculations, source search, FastAPI backend and local interface.

Under development: reliable generated explanations. The evaluated small pretrained LLM failed its citation checks, so unsupported drafts are withheld. This interface update does not improve or retrain that model.

Pending: local n8n execution, independently reviewed answer quality, graphical review and release testing. No production release is claimed.

The source is UCI Online Retail II, dated December 2009–December 2011. A fresh download does not make the observations current. Profit, today's stock and future demand are outside this prototype's supported scope. The future W03 forecast project has a separate objective.

## Update an existing copy

Stop the server with Ctrl+C. From your Git-enabled project copy:

```text
git pull --ff-only
```

Then, in Windows PowerShell using the existing project environment:

```powershell
.\.venv\Scripts\python.exe serve.py --baseline
```

Open http://127.0.0.1:8000/ on the same computer and press Ctrl+F5 to refresh the page. If port 8000 is occupied, add `--port 8001` and use that port. A local address only works while your own server is running.

If an error remains, save its exact wording and the server terminal traceback. A screenshot can identify a visual problem. Do not include account credentials or private financial data.
