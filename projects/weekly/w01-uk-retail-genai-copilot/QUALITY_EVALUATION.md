# Retrieval and answer evaluation — 3 November 2026

**W01 remains in progress.** This increment adds a frozen, source-bound quality contract, measured retrieval ablations, fresh CPU generation, regression fixes and reproducibility guards. It does not turn unsupported generations into validated answers or claim a launched service.

## Before reading scores

- Original first routing score remains **36/40**, measured on 1 November. Four known definition-versus-calculation failures became development/regression cases. Their later improvement is not an unseen benchmark improvement.
- [V1 contract freeze](evaluation/quality_v1.json) was committed before 3 November routing/prompt changes and ranking/generation evaluation. It has **64 unique tasks**: 40 new product-topic paraphrases, eight new country/metric groups, eight already-inspected source-definition questions and eight already-inspected safety/unsupported requests.
- New-family questions and previously observed regressions are scored separately. The same AI authored questions, silver relevance references and code; there is **no independent human review**. These are selected portfolio tasks, not a representative survey of retail users or a job-performance guarantee.
- Product labels are all actual descriptions matching predeclared regex predicates, not independent semantic gold. A relevant alternative can be missing; a regex hit can be noisy. Contract relevance is an AI-selected paragraph ID. Literal citation support does not prove semantic sufficiency or source truth.
- Model weights, prompt, routing and gate were frozen for the evaluation. No parameters were retuned after viewing scores. A future change based on these cases consumes them as development material and requires another separately frozen set for unseen claims.

## Reproducibility correction, preserved rather than hidden

The first CI run correctly failed two source-binding controls. The assistant's materialisation had added one EOF newline to local canonical files. The original 40-task file and source-contract file therefore had different byte hashes, although parsed questions and source text were identical. The initial V1 freeze and all actual first-capture results remain in dated evidence.

[V2](evaluation/quality_v2.json) corrects only source-byte bindings. All 64 task objects, references and values are identical. Every corpus ID/kind/text is identical; ten contract-document metadata source hashes changed. Rebuilding produced **byte-identical vectors**. Unchanged code/doc files were restored to exact GitHub bytes; their differences were extra EOF newlines only. Models, prompt, routing, gate and retrieval settings were not tuned as part of this fix.

The canonical replay is the **same 64 cases**, not another independent holdout and not another project. [Source-binding erratum](evidence/2026-11-03/source-binding-erratum.json) records hashes and equality checks. CI now verifies both canonical bindings and unchanged labels. See [protocol](evaluation/QUALITY_PROTOCOL.md).

## Metric definitions

For each retrieval query, top three unique IDs are compared with the frozen reference set:

- **Hit@3:** at least one reference ID appears in the first three.
- **Recall@3:** matching IDs / every ID in that query's reference set. A broad topic can have many references, so this can be low even when useful results appear.
- **Precision@3:** matching IDs / three; missing result slots count against precision.
- **MRR@3:** reciprocal rank of the first reference, or zero if absent from top three.

BM25 is the lexical baseline; dense uses normalised MiniLM cosine; hybrid uses the existing reciprocal-rank fusion (k=60, top-50 candidates). The evaluator runs all modes over the same corpus/filter, without supplying reference labels to the searcher. Generation runs through the bounded service's unchanged hybrid adapter, not through a gold-selected source.

Numerical references are direct SQL over the deduplicated base table and frozen before evaluation. They are compared with the service's fixed read-only metrics. Safety requests must abstain with zero tool calls. Source-only and numerical cards are not counted as successful generated prose.

The strict extract gate accepts only one or more `[source_id] verbatim source span` lines. Accepted output must cite frozen relevant IDs to count as a silver-relevant extract. This is not a general semantic judge; the metric does not certify source truth, completeness or suitability. Rejected drafts stay outside the API/UI.

## Reproduce safely

From Linux/WSL2, Python 3.12, after the full source/model/index setup in [UI_API_MILESTONE.md](UI_API_MILESTONE.md):

```bash
python -m unittest discover -s tests -v
python validate_quality_contract.py
python run_quality_eval.py --check-only
python run_quality_eval.py --out data/quality-run-1
# Only for an interrupted run, unchanged code/models/packages/index:
python run_quality_eval.py --out data/quality-run-1 --resume
```

The wrapper hashes actual model assets, packages, source/index and evaluation inputs. Default output is ignored `data/quality-evaluation`, preserving published captures. A completed checkpoint cannot be resumed as if it were fresh inference; choose a new output directory for a new run. Partial resumes record prior versus new case counts and make clear that process wall time covers only the current segment. The underlying evaluator also leaves completed capture files unchanged instead of stamping old results as new work.

The initial 3 November direct run predates the wrapper; the canonical replay explicitly selects V2 and a new output path. Actual model outputs, ranking IDs/scores, code hashes, manifests, settings, per-case latencies and resource measurements are saved. Model files/full corpus/index/raw workbook remain local ignored artifacts, not ordinary Git blobs.

The local generator remains pretrained SmolLM2-135M-Instruct; embeddings remain all-MiniLM-L6-v2, with the same pinned Apache-2.0 revisions. No model training, fine-tuning, paid API calls or public hosting occurred. Source capture is actual historical UCI replay, not live retail transactions or ingested ONS context. n8n execution and graphical UI review remain unfinished.

## Measured results

The verified table below uses the canonical capture. First-capture outputs remain separate so the provenance error and replay cannot be mistaken for additional unique evaluation tasks.

## Verified canonical results

The canonical replay completed all **64 unique cases** and reproduced every first-capture route, ranked-ID list, raw model draft and quality flag. It adds **zero independent holdouts**. See [comparison](evidence/2026-11-03/capture-comparison.json).

| Retrieval on 40 new product paraphrases | Hit@3 | Recall@3 | Precision@3 | MRR@3 | Query p50 / p95 |
| --- | ---: | ---: | ---: | ---: | --- |
| bm25 | 7.5% (3/40) | 2.61% | 3.33% | 0.050 | 22.37 / 27.81 ms |
| dense | 62.5% (25/40) | 6.51% | 47.50% | 0.542 | 35.28 / 46.17 ms |
| hybrid | 42.5% (17/40) | 4.29% | 23.33% | 0.342 | 35.50 / 47.53 ms |

Dense retrieval outperformed the existing hybrid on this selected paraphrase set. No default, fusion weight, stopword rule or model was changed after seeing these results. The reference sets are regex-derived silver labels, so this is not overall retail-search accuracy. A plausible hypothesis is that lexical matches in equal-weight fusion distract from semantic matches; no ablation establishing that cause has been run.

Routing: **48/48 new-family cases** and **16/16 observed regressions**. These are explicit AI-authored templates and paraphrases, not broad language-understanding validation. The separate original 40-question routing regression is now 40/40; its first unseen result remains 36/40. New independent direct-SQL numerical references: **8/8 correct**. Observed unsupported/action cases: **8/8 abstained with zero tool calls**.

Actual generation: **56 fresh CPU generations** in each capture, over the same unique queries. Retrieval generations passing the strict gate: **0/48**; silver-relevant cited answers: **0/48**. Failures: {'citation_or_extract_format': 28, 'unknown_citation': 20}. The raw drafts remain evidence; they were not repaired or presented as validated answers. Numerical answer cards still come from SQL.

Warm workflow requests with generation: **n=56, p50 5.999 s, nearest-rank p95 7.009 s**. Cold runtime startup: 3.162 s. Peak process RSS: **1217.18 MiB**, including an extra embedding Retriever for ablations. Linux/Python 3.12.14, 9 visible CPUs, two inference threads; CPU model unavailable. This is a sequential development-host benchmark, not a production SLA or guaranteed laptop result.

The original/canonical captures ran sequentially, not concurrently. Model loading is separate; independent retrieval ablations add work outside each measured workflow request. Recorded times/resource peaks differ between captures while rankings and drafts remain identical.

Fresh source: **3 November 2026, 19:17:17 UTC**, HTTP 200, 45,622,418-byte UCI archive; checksum unchanged. Rebuild: **1,067,371 raw / 1,033,036 deduplicated rows**, independent Decimal reconciliation passed, 44.410 s ingestion and 384.91 MiB peak ingestion RSS. Historical observation dates remain 2009–2011. Corpus: 5,665 documents / 2,213,419 bytes; float32 index: 8,701,568 bytes. No live merchant/ONS feed or model training.

Local validation: **46 tests passed**, dependency check and JavaScript syntax passed. Corrected CI run [41703716127](https://github.com/AshJai23/AshJai23/actions/runs/41703716127) passed the 46-test suite, eight source/replay controls, eight frozen-reference controls, explicit BM25/no-generation HTTP smoke and JavaScript syntax. Fresh-model evaluation was local, not this CI. A separate actual Uvicorn HTTP request with local generation completed and returned evidence-only after rejection; the temporary server stopped.

Captured evaluation implementation: [2e2f6d6](https://github.com/AshJai23/AshJai23/commit/2e2f6d6e46aaaf7f90ba6285d1fbcc1cadd992f1). A later API/UI wording-only edit describes the observed routing fixes as regressions; it does not change routing, model, prompt or gate.

**Release blockers:** no supported generated retrieval answers; silver references lack independent human semantic review; n8n has not executed; graphical UI QA and final case study/demo remain unfinished. Keep W01 in progress. Next tests must use development data for changes and another separately frozen set for unseen claims.
