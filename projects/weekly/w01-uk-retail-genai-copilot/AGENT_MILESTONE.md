# Bounded workflow and answer-gate milestone — 1 November 2026

Status: bounded workflow tested in GitHub Actions on 1 November 2026. W01 remains
in progress: four frozen routing cases failed, and full RAG quality, interface
and n8n acceptance requirements are not complete.

The local execution environment is unavailable. The public repository's standard
GitHub Actions runner is used as a permitted free validation alternative. The
workflow has read-only repository permissions, a ten-minute timeout, no secrets,
no hosted model calls, no uploads of model weights and no paid/always-on service.

## Implementation
- A finite LangGraph workflow routes to one read-only SQL aggregate or one
  bounded retrieval call, then composes an answer or abstains. Routing is a
  deterministic allowlist, not an autonomous LLM planner.
- A numeric answer card comes from fixed SQL and includes source period, scope
  and citation. Generated prose cannot replace its number.
- The generated-answer gate permits only verbatim, cited evidence extracts.
  Missing/unknown citations, unsupported spans or extra free-form prose fail.
  Exact source support does not establish source truth, freshness or contextual
  relevance; this is not a general semantic factuality checker.
- Retrieval without a validated draft returns source evidence with no generated
  answer. The orchestration adapter currently uses BM25 explicitly; the separate
  dense/hybrid index and local model from 31 October remain available.
- One tool call per request, 500-character input bound, fixed graph topology and
  recursion limit 8. No free SQL, shell, file mutation, external messaging or
  agent-selected network action. Four fixed aggregate metrics only, full period,
  one known customer country or explicit overall totals. Unsupported filters
  abstain rather than being silently ignored.
- Optional local generation is supported by the existing Generator adapter.
  Today's CI uses actual saved 31 October drafts as labelled historical replay,
  not new model inference or training.

## Run
From this project directory in a clean Python 3.12 virtual environment:

```bash
python -m pip install -r requirements-agent.txt
python -m unittest discover -s tests -v
python retail.py fetch
python retail.py build
python catalogue.py
python bounded_agent.py --question 'signed_value for United Kingdom'
python ci_validate.py
```

Omit fetch if a capture exists. ci_validate.py expects a clean data/raw directory
for its fresh-source download; it intentionally does not overwrite captures.
For fresh local generation, separately follow AI_MILESTONE.md to install CPU
PyTorch/Transformers and download the pinned models, then add
`--with-local-model`. That optional path is not exercised by this CI.

The CI prints a machine-readable W01_EVIDENCE_JSON record to the job log.
After verification, copy the actual record into dated evidence through normal
Git history. It includes unit output, real-source checks, source checksum, versions,
first frozen deterministic routing/SQL results and rejected-draft replay.
The 40-question contract is AI-authored and is not independent human validation.
Only route selection and numerical oracle comparisons are measured here; no claim
of full held-out RAG answer grounding, retrieval relevance or LLM planning score.

Primary references:
- https://reference.langchain.com/python/langgraph/graph/state/StateGraph
- https://docs.github.com/en/actions/concepts/billing-and-usage

The agent/API/UI/n8n, broader safety/evaluation, final demo and weekly release
acceptance remain distinct. No production service or users are claimed.

## Actual CI results

[Run 41344533660](https://github.com/AshJai23/AshJai23/actions/runs/41344533660) completed successfully on
1 November 2026 against implementation commit
[96ba2d8](https://github.com/AshJai23/AshJai23/commit/96ba2d8178f031c4dd22c30f32b3e027c1587239).
The [saved report](evidence/2026-11-01/ci-validation.json) contains actual output,
per-case results, source checks, versions and timings.

- **26 unit tests passed**; **8 source/replay checks passed**.
- Fresh HTTP 200 source download: 45,622,418 bytes, SHA-256 matches prior capture.
  Rebuilt 1,067,371 raw / 1,033,036 deduplicated historical rows; totals unchanged.
- First frozen deterministic-route evaluation: **36/40 correct (90%)**.
- Numerical oracle comparisons: **24/24 correct**, using fresh read-only SQL.
  These are synthetic AI-authored question templates over four named metrics;
  they are not proof of broad natural-language or commercial performance.
- **3/3 saved bad LLM drafts rejected** by the extract gate. This replays the
  actual 31 October outputs; no new LLM inference or training ran in this CI.
- Mixed-route latency: n=40, p50 **4.880 ms**, p95 **16.215 ms** on the CI runner.
  No model loading/generation is included. It is not laptop end-to-end LLM latency.
- CI validation script took **49.232 seconds**, including unit suite and source
  rebuild. Parent-process peak RSS **162.03 MiB** excludes subprocess peak memory.

### Failures remain visible

T28 should have retrieved a source explanation but selected a metric and returned
a calculated count. T29, T30 and T31 should have retrieved source explanations
but abstained. A correct SQL value can still answer the wrong intent. Success of
the CI job means the unit/source/replay checks passed, not all quality cases.

No routing rules were adjusted after reading this evaluation. Preserve the first
result and frozen contract. Any future changes based on these failures turn the
affected families into development/regression material; use a newly frozen,
separate evaluation set before claiming an unseen improvement. Full retrieval
relevance and generated-answer grounding evaluation have not run.

The safe current behaviour is fixed, cited numerical cards or evidence-only
retrieval. Strict extract acceptance is deliberately narrow; it may reject useful
paraphrases and does not make a cited source true or contextually sufficient.
