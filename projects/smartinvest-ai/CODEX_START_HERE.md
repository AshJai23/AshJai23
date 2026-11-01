# Hand-off prompt for Codex

Open this project folder in the Codex desktop app, VS Code extension or Codex CLI, and paste:

> Continue my SmartInvest AI university/portfolio project. Read README.md and AGENTS.md first. Install dependencies, run all tests, and start the Streamlit app. Fix any failures. The current baseline is educational rule-based investment-offer screening, not real fraud verification. Review false positive/negative behaviour, strengthen test coverage, and propose a data collection and model evaluation plan for a TF-IDF + Logistic Regression baseline. Do not imply official FCA verification has happened unless a real, permitted integration exists. Do not convert this into a startup product yet. Report exact commands, test results, remaining limitations, and next steps.

To run locally without Codex:

```bash
python -m venv .venv
source .venv/bin/activate    # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
streamlit run app.py
```

API (optional, second terminal):

```bash
uvicorn smartinvest.api:app --reload
# Open http://127.0.0.1:8000/docs
```

Codex Cloud generally works with a connected GitHub repository and a published environment. For a local ZIP, unzip first and open the folder in Codex desktop/CLI; if using Cloud, commit the files to a repository and connect that repository.
