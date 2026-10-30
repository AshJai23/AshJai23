# Evaluation contract frozen before agent implementation — 30 October 2026

The copilot is not implemented yet. `evaluation/tasks.json` fixes 40 test cases:
24 numerical, eight source/schema retrieval and eight unsupported/adversarial.
These are AI-authored engineering checks, not independent customer research or
an independently annotated benchmark. Numerical oracle SQL is deterministic;
retrieval/decline rubrics are reviewed source/metric contracts. No scores yet.

Keep these tasks out of few-shot prompts, router training and retrieval-ranking
tuning. Add separate development questions; do not adjust routing rules to pass
these test phrasings. If that separation is broken, create a fresh version and
report benchmark contamination rather than retaining a held-out claim. Group
paraphrases of the same task together. Future learned components must split by
task family/document group, not random paraphrase rows. Snapshot hashes bind the
test contract to this version; save subsequent revisions explicitly.

## Required evaluation

- Tool-choice accuracy; numeric answer correctness versus independent oracle
  results (exact counts, value tolerance GBP 0.01); evidence/filter coverage.
- Retrieval Recall@k/MRR against annotated relevant sources. Lexical baseline
  versus dense/hybrid ablation. Don't count a correct number as grounded prose.
- Citation support and unsupported statements in generated answers; abstention
  rate, false refusals and unsafe actions. Report sample counts and each failure.
- Separate source-date awareness: old transactions cannot answer live questions.
- p50/p95 full request latency, hardware/memory, timeouts and error behaviour;
  ingestion query timings do not equal agent/LLM latency.
- Actual free local LLM generation with model revision/licence/settings and
  saved outputs. A templated numerical response is not a GenAI result.

Acceptance requires all important failures visible and the functionality actually
run, not an invented pass threshold or claiming perfect performance on a tiny
test suite. Prompt injection in questions or retrieved text must not enable
writes, network actions or arbitrary code. Runtime SQL should use a separate
read-only connection, allowlisted tools/columns and bounded execution. Today's
ingestion connection is intentionally write-capable and is not exposed to users.
