# Local installation and FastAPI verification — 2 November 2026

Base source: f19a7c1146056604c4136b8a50b3ea98412a9de7.

- Created an isolated Python 3.12.14 .venv in the assistant Linux workspace.
- Installed requirements.lock.txt and editable project 0.4.1 with --no-build-isolation --no-deps. Installation succeeded; pip check: no broken requirements.
- Full suite: 107 passed in 6.62s.
- scripts/smoke_fastapi.py: actual temporary loopback Uvicorn HTTP smoke passed for health, HTML, JavaScript, OpenAPI, single/batch scans and market research. Offer/batch inputs were labelled synthetic fixtures. Market input was attributed historical ECB replay: three assets, 1,751 observations each, latest 30 October 2026. Temporary smoke server stopped.
- Started a separate local Uvicorn process on 127.0.0.1:8000 in the assistant workspace; startup completed. This process is temporary and does not provision a public URL or run on the user's computer.
- Added VS Code pre-launch environment/dependency setup and F5 FastAPI debug configuration. All three JSON files parse successfully. Linux equivalent installation and Uvicorn launch were executed; Windows/macOS and graphical VS Code debugger interaction were not executed.
- No remote-control access to the user's VS Code, public Python hosting, stock-feed subscription, FCA lookup or new model training in this setup task.
