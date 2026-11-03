# Quality evaluation freeze — 3 November 2026

This contract is published before 3 November routing/prompt changes or retrieval/generation evaluation. The same AI authored questions, source references and implementation; there is no independent human review. This is a portfolio evaluation, not a commercial performance guarantee.

- 64 tasks: 40 new product-topic retrieval questions and 8 new customer-country/metric groups (48 new-family holdouts), plus 8 observed contract questions and 8 observed unsupported/action cases (16 regressions).
- Source documents remain searchable; this is query/family holdout, not hiding the relevant documents from the retrieval index. No labels fit model weights.
- Product references are every actual source description matching predeclared regex predicates. These are noisy silver relevance labels, not complete semantic gold. Source may contain non-product or inaccurate text. Semantic alternatives can be absent from the reference set.
- Contract references are AI-selected paragraph IDs from the immutable DATA_CONTRACT.md corpus. The original 40-task file/hash is unchanged. Original first routing result remains 36/40; fixes based on observed failures can improve regression results only.
- All question/source IDs and independent direct-SQL numerical references were frozen before ranking inspection. No retrieval/model result was used to select product topics. No retuning is permitted after inspecting this set; future tuning consumes these families and needs another independently frozen set for unseen claims.
- Retrieval reports BM25/dense/hybrid Hit@3, Recall@3, Precision@3, MRR@3, reference-set sizes and latency. Recall@3 can be small for a broad product set; a hit is distinct from retrieving all relevant descriptions.
- Generated answers report actual drafts and strict cited-extract support, with relevance based on frozen source IDs. These measures are not general semantic correctness or independent factuality. Deterministic SQL remains a separate numerical baseline; evidence-only output is not a successful generated answer.
- Generation runs through the same bounded workflow with no arbitrary SQL, external actions or model-selected tools. Cold startup, warm request latency, sample count, CPU threads and peak memory are reported separately. No LLM training/fine-tuning or public service is implied.

Frozen SHA-256: `f5d1e06e69a6967a74ac97de0b9d2d59ee42452a75dec9fdfc35ca3da56527f0`.
Source corpus SHA-256: `6695c93c39af49347e120db619aec03f435b8caad37a84c69148cefe0117d07a`.

Model revisions and licences remain the pinned public Apache-2.0 models in AI_MILESTONE.md. Their current public metadata is checked by model_store.py before download. Raw data/models/index stay out of normal Git. Only contracts, code, manifests and actual validation evidence are published.

## Source-binding erratum — 3 November

CI run 41702778582 correctly failed the corpus/original-file byte checks. The assistant's file materialisation added one trailing newline to canonical inputs. V1's questions, regex labels, source IDs, numerical references and actual first evaluation are preserved; do not silently edit its frozen hash.

`quality_v2.json` corrects only source-byte bindings and records V1 ancestry. All 64 task objects are exactly equal. Every corpus ID/kind/text is identical, and rebuilding produced byte-identical float32 vectors. Ten contract-document metadata source hashes changed. Unchanged source modules were restored to exact GitHub bytes; their only difference was an extra EOF newline. Model, prompt, routing, gate and query parameters are unchanged. Canonical replay is the same test set, not a second independent holdout or extra completed project.

V2 SHA-256: `20127936228d03866b88db9e31d4421503068d72e81d8094dd0f1f941f9444d9`. The erratum and initial failed CI remain in dated evidence. V2 is recorded before canonical replay; no performance result selected its questions or labels.
