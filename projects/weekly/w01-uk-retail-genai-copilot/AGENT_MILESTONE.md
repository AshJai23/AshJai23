# Bounded workflow and answer-gate milestone — 1 November 2026

Status: implementation prepared; CI verification pending. Do not count this
increment as tested or the weekly project as complete until the dated validation
report and workflow run are read back.

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
