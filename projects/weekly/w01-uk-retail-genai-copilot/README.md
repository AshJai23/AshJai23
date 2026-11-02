# UK Retail GenAI Analytics Copilot — W01

**In progress; not a released weekly flagship or public website.** Target: 5 November 2026. This is a local retail research prototype over actual **2009–2011 historical** UCI transactions, not current UK shop activity.

On **2 November** the bounded graph, hybrid retrieval, local generator, FastAPI and web interface ran together. **35 unit tests passed**. Fresh model output still failed **all 3 development answer checks** and was withheld. The earlier frozen routing result remains **36/40**, with **24/24** numerical oracle matches; known routing failures and full quality evaluation remain open.

Start with **[the current API/interface milestone and exact commands](UI_API_MILESTONE.md)**. After starting Uvicorn on your computer, open http://127.0.0.1:8000/; /docs offers API documentation. These local addresses do not represent a deployed site. No public Python host is provisioned.

## What works

- Full source acquisition, typed streaming ingestion, auditable deduplication, DuckDB/Parquet and independent numerical controls.
- Finite LangGraph with one allowlisted SQL aggregate or one bounded evidence lookup. No arbitrary SQL/actions or autonomous LLM tools.
- BM25/dense/hybrid retrieval over distinct descriptions and source-contract paragraphs.
- Actual pinned public Hugging Face CPU generation, with strict cited-extract validation and unsupported-draft withholding.
- Local web workspace showing interpreted scope, deterministic facts, source dates, evidence, generation status, tool trace and readiness.
- Strict JSON/input/body limits, per-process serial inference, coarse errors and prompt-free in-memory request metrics.

## Actual scale and provenance

| Measure | Observed |
| --- | --- |
| Raw / deduplicated invoice rows | 1,067,371 / 1,033,036 |
| Duplicate rows removed | 34,335; policy assumption, not proof every repetition is erroneous |
| Missing customer IDs retained | 235,151 deduplicated lines |
| Observation period | 1 December 2009–9 December 2011 |
| Latest acquisition | 2 November 2026, HTTP 200; checksum unchanged |
| Distinct indexed documents | 5,655 descriptions + 10 contract paragraphs |
| Corpus / vector index bytes | 2,213,419 / 8,701,568 |
| Fresh API development generations | 3; zero accepted answers |
| Warm generation request latency | n=3, p50 4.996 s, p95 6.289 s; small development smoke only |

Transactions are SQL rows, not vector documents. No costs, profit, inventory or current demand exists in this source. Charges/adjustments can be included in line-value metrics; read [DATA_CONTRACT.md](DATA_CONTRACT.md). Deduplication may remove genuinely repeated identical lines. Missing IDs restrict customer-level inference but are retained in aggregate totals.

Source: Chen, D. (2012), **Online Retail II**, UCI, DOI [10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). [Official source](https://archive.ics.uci.edu/dataset/502/online+retail+ii). Full raw data, pseudonymous customer IDs, corpus/index and model weights remain local ignored outputs. [Dated evidence](evidence/2026-11-02/) records capture hashes, parameters, outputs, resources and limitations.

## Evidence and honest limits

- [Current API/interface milestone](UI_API_MILESTONE.md): fresh local generation, actual HTTP replay, independent SQL, setup/runbook and failures.
- [1 November workflow milestone](AGENT_MILESTONE.md): original frozen routing/SQL results and 3 bad-draft replays. No routing tuning has been made in this API increment.
- [31 October AI milestone](AI_MILESTONE.md): initial index and actual CPU model smoke; pretrained inference is not training or fine-tuning.
- [Evaluation contract](EVALUATION.md): AI-authored, not independent human validation. Forty original tasks remain frozen. New integration probes are development material, not an unseen quality score.
- [Source validation](evidence/real-source-validation.json): prior full-source controls; new dated profile and API reconciliation are separate captures.

The small generator invents unsupported material and omits citations. The gate keeps those drafts out of the UI, but exact source extraction is not broad semantic grounding or source-relevance validation. Evidence-only output is labelled as retrieval, not a successful generated answer. Four known intent errors remain, so inspect interpreted scope even when arithmetic is correct.

**Unfinished:** full held-out relevance/answer evaluation, routing remediation with fresh evaluation, graphical UI review, n8n runtime smoke, final reproducibility, monitoring and case study. ONS monthly context has not been ingested. No training, public deployment, production users, commercial impact, Docker/Power BI execution or independent human review is claimed.

Weekly releases complete: **0/3**. The nine earlier prototypes are preserved separately.
