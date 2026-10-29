# UK Public-Sector Research RAG Assistant

Status: planned; no implementation, data processing or training claimed.
Build: 2026-11-06 through 2026-11-12.

Can a policy researcher retrieve and summarise relevant UK parliamentary discussion with dated, verifiable citations across a substantial corpus?

## Tools

Python, LangGraph or LlamaIndex, BM25 + dense embeddings, FAISS or equivalent local index, Local open-weight LLM, FastAPI, Evaluation and structured monitoring.

## Data

- [UK Parliament Hansard](https://www.parliament.uk/about/how/publications/hansard/) — Published proceedings, refreshed on demand with publication lag; records statements, not verified policy facts. Official source/licence and GOV.UK Parlex source description checked 29 October. Swagger inaccessible through research reader; API pagination, rate limits and acquisition still require a real probe.
- [Official API / licence references](https://www.gov.uk/algorithmic-transparency-records/dsit-parlex) — Documentation; not acquired corpus. Candidate permitted corpus; do not assume API success.

## Deliverables

- Resumable cached ingestion, source registry, provenance, stable IDs and incremental refresh
- Deduplicated corpus with target 100,000 unique passages if permitted API access and laptop resources allow; publish actual achieved scale
- Hybrid retrieval plus citation-grounded local generation and bounded research workflow
- Held-out debate/group-separated retrieval and answer evaluation against BM25; ablation of dense/hybrid methods
- Runnable local API/UI, latency/memory benchmarks, freshness checks, prompt-injection tests and support runbook

## Acceptance

- Verify endpoint, pagination, rate limits, licence and reuse exclusions before bulk acquisition; no bypass of access controls
- Start with a genuine smaller corpus, benchmark, then scale; if 100k passages cannot be acquired/indexed, label scale target unmet and report blocker
- At least 50 held-out answerable and unanswerable questions; report Recall@k/MRR, citation support, abstention failures and p50/p95 latency with evaluation provenance
- Do not present parliamentary statements as established fact/current law; show speaker/date/source context and refresh age
- Actually run local LLM generation; no chat API wrapper or renamed Student Copilot, no personal profiling or automated external actions
- Distinguish embeddings/indexing from training an LLM; no claim of fine-tuning without fitted weights and held-out evidence

See [build guide](../BUILD_GUIDE.md) for publication, evaluation and daily reporting requirements.
