# UK Retail GenAI Analytics Copilot

Status: in progress. Full-source ingestion, profiling, DuckDB/Parquet warehouse and read-only SQL baseline ran on 30 October. LLM/RAG/agent/UI/n8n work remains; no model training claimed.
Build: 2026-10-30 through 2026-11-05.

Can a retail manager ask plain-English questions and receive reconciled numerical answers and evidence-backed explanations?

## Tools

Python, LangGraph, DuckDB / SQL, Parquet, Local open-weight LLM, Embeddings / hybrid retrieval, FastAPI, Streamlit, GitHub Actions.

## Data

- [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) — Actual historical UK retailer transactions, December 2009–December 2011; NOT real-time. Full archive retrieved 30 October: 1,067,371 rows ingested. See [actual evidence](evidence/).
- [ONS Retail Sales Index](https://www.ons.gov.uk/businessindustryandtrade/retailindustry/datasets/retailsales) — Regularly published monthly GB macro context, separately labelled; not current merchant transactions. Verify download/API at build time; do not join unrelated periods or businesses.

## Deliverables

- Full-source ingestion, deduplication audit and reproducible DuckDB/Parquet warehouse
- LangGraph bounded tool workflow: validated read-only SQL for numbers, RAG for schema/product/source context, local LLM explanations
- Runnable API/UI showing query evidence, source dates and abstention
- Held-out task evaluation against deterministic SQL/lexical baselines, with accuracy, grounding, failure and latency results
- CI, replay fixtures, source register, model licence/version, monitoring and beginner/interview case study

## Acceptance

- Target full 1,067,371 source rows; report actual raw/clean counts and exclusions, missing customers and cancellation handling
- Do not describe transaction rows as vector documents; report actual distinct indexed descriptions/docs/chunks
- No unrestricted SQL writes or arbitrary agent execution; bound query cost, tool calls and input size
- At least 40 held-out numerical/retrieval/unsupported tasks with saved references; keep tuning tasks separate and label AI-authored evaluation
- Actually run free local LLM inference and show generated outputs; if unavailable, mark GenAI requirement blocked rather than substituting templates as an LLM
- Reconcile numeric answers to independent SQL controls; do not invent costs, profit, stock, ROI or live sales

See [build guide](../BUILD_GUIDE.md) for publication, evaluation and daily reporting requirements.
