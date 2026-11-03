# Retail Evidence Lab — working case study

**Draft, not a completed weekly release.** Intended portfolio audience: junior applied-AI/ML engineering reviewers. No production users, commercial return, job eligibility or independent validation is claimed.

## Business problem

A retail analyst needs to distinguish a calculation from an explanation. Adding up a million invoice lines with a language model risks invented totals; retrieving a product description cannot establish profit, inventory or current demand. This project tests a safer separation: fixed SQL for numbers, retrieval for source context, and a bounded local model whose unsupported draft is withheld.

## What a row and a document mean

One transaction row is an old invoice line with a quantity and GBP unit price. The full public UCI workbook contains 1,067,371 rows across two sheets. Exact normalised-field deduplication yields 1,033,036 rows, but repeated identical lines might be legitimate; both counts stay visible. Missing customer IDs stay in aggregate totals and restrict customer-level analysis.

A retrieval document is different: one of 5,655 distinct descriptions or 10 project-contract paragraphs. The system does not claim a million RAG documents. Capture time does not change the source observation period: December 2009–December 2011. There is no private/live merchant connection.

## Engineering decisions

- DuckDB decimal aggregates, parameterised country filters and independent controls reconcile numerical answers. No arbitrary SQL is accepted.
- A finite LangGraph permits one metric/retrieval tool call, not autonomous actions. The LLM has no shell, write, email or network tools.
- BM25, exact dense cosine and hybrid retrieval are compared, rather than assuming a more complex approach wins.
- Public pinned CPU models run locally with safetensors and remote code disabled. Inference and index construction are not training or fine-tuning.
- A strict cited-extract gate rejects invented/uncited text. Deterministic numerical facts are never rewritten by the model.
- FastAPI and a local web workspace show interpreted scope, source dates, evidence and failures. Input/body/concurrency limits and no-fabrication source errors are tested.
- Frozen reference contracts, per-case checkpoints, package/model manifests and actual resource/latency evidence make limitations reviewable.

## What went wrong and why it matters

The initial small-model drafts invented details or omitted/altered citations. The interface therefore showed evidence-only results. Four source-definition questions were also misrouted; arithmetic can be correct while intent is wrong. Those observed cases became regression tests, while the original first score remains visible.

CI later found a byte-level reproducibility error in the assistant's file materialisation. It was preserved and corrected with an explicit source-binding erratum and canonical replay, without changing the questions, source text or model/prompt parameters. A successful result on one computer is insufficient if source bindings cannot be reproduced from Git.

## Current release boundary

The useful current outputs are auditable historical SQL and inspectable retrieved evidence. Passing unit tests is not evidence that generated explanations are reliable. See [quality evaluation](QUALITY_EVALUATION.md) for actual measured successes and failures. Remaining release work includes generator quality, human relevance review, local n8n execution, graphical interface review and reproducible final demonstration.

This is a research portfolio, not an investment tool, current retail feed, trained foundation model or production operations claim. Source attribution: Chen, D. (2012), UCI Online Retail II, DOI 10.24432/C5CG6D, CC BY 4.0.

## Measured finding for reviewers

On 40 frozen AI-authored product paraphrases with source-derived silver references, dense Hit@3 was 25/40, hybrid 17/40 and BM25 3/40. This shows why a more complex retrieval stack should be compared with simple baselines. All 48 retrieval generations failed the strict answer gate; 8/8 new SQL answers reconciled. No useful generated-answer improvement, commercial return or release completion is claimed.
