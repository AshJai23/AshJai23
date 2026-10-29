# Weekly UK AI and ML portfolio

**One substantial project per week, with daily progress and user feedback.**
Updated 29 October 2026: prioritise **GenAI, LLM applications, RAG, agents and ML**
for applied AI / junior ML engineering roles. SQL and data quality support these
systems. The nine earlier prototypes remain [archived](../30-days/) and are not
recounted. No weekly flagship has been built or trained yet.

| Build week | Project | Main evidence |
|---|---|---|
| 30 Oct–5 Nov | [UK Retail GenAI Analytics Copilot](w01-uk-retail-genai-copilot/BRIEF.md) | LangGraph, local LLM, evidence-backed SQL tools, RAG and evaluation |
| 6–12 Nov | [UK Public-Sector Research RAG Assistant](w02-uk-public-sector-rag/BRIEF.md) | Larger document corpus, hybrid retrieval, cited generation and incremental refresh |
| 13–19 Nov | [UK Retail Demand ML and MLOps Service](w03-uk-retail-demand-mlops/BRIEF.md) | Fitted ML/neural models, temporal baselines, serving, tracking and monitoring |
| 20–22 Nov | Review and polish | Reproducible demos, fixes, portfolio case studies, CV and interview explanations |

## Dataset scale and freshness

UCI lists **1,067,371 historical transaction rows** for Online Retail II
(2009–2011). That is a source catalogue count, not rows processed in this update.
Full-source ingestion is the target. Numerical questions use SQL; a million
transaction rows are not a million RAG documents.

W02 targets **100,000 unique passages**, subject to permitted acquisition and
measured laptop resources. This is a target, not an achieved corpus. Verify API
behaviour and licence before ingestion; report any shortfall. Record unique
documents/chunks, bytes, index size, ingestion time, memory and retrieval latency.
Refresh published UK sources on demand with capture/publication dates; historical
data never becomes a live retail feed. There is no fabricated live-data fallback.

## Quality and daily reporting

Run the actual local LLM for GenAI requirements; retrieval and embeddings alone
do not count as generation or LLM training. Fit and evaluate ML/neural models
against simple baselines. Report unsuccessful approaches honestly. Each release
needs a runnable interface, tests, real-source/replay smoke evidence, measured
evaluation, source attribution, limitations and a beginner-friendly case study.
No paid services or new credentials.

Daily updates around 7pm UK time describe actual work, commit links, tests,
results, blockers, the next milestone and choices the user can change. They do
not claim continuous all-day work. Current scope preserves the 22 November end
boundary: three full build weeks and three review days. Previous NHS and council
analytics ideas are unscheduled backlog. These are portfolio demonstrations, not
a guarantee of a job or claims of production users.

[Plan](plan.json) · [Progress](progress.json) · [Build guide](BUILD_GUIDE.md) ·
[Feedback](FEEDBACK.md) · [Daily logs](logs/) · [Dated hiring evidence](UK_MARKET_EVIDENCE.md)
