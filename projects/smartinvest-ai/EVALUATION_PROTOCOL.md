# Evaluation and modelling protocol

## Current measured claim

The shipped engine is deterministic rules, with manually chosen recurring-return
thresholds (1% daily, 2% weekly, 5% monthly). These are indicators, not fraud
probabilities or statistically learned cut-offs. Regression/API/Streamlit tests
validate code behaviour only. There is no real labelled corpus, model fit,
cross-validation score or measured real-world scam precision/recall yet.

Negation handling is a narrow heuristic. Complex quotations, sarcasm, conditional
claims, misspellings, unicode obfuscation and multi-clause text can still fail.
Punycode, HTTP, a private messenger or a payment instruction can be legitimate;
their presence is not a verdict. Zero findings is not a safety decision.

## Next modelling experiment, after the data gate

1. Approve sources, reuse rights, privacy process and an operational target using
   DATA_PROVENANCE.md. Collect genuine examples and preserve source/label evidence.
2. Annotate independently, adjudicate disagreements and leave uncertain outcomes
   unlabelled. Version the rubric and snapshot. Inspect imbalance and selection
   bias; do not invent a sample count to justify training.
3. Cluster duplicate/near-duplicate messages, entities, domains and campaigns
   before splitting. Use earlier campaign groups for training, later unseen
   groups for validation and a final later unseen-campaign test set. Embargo
   overlapping periods if needed. Do not guess dates or substitute random rows
   when the metadata is unavailable.
4. Fit a TF-IDF word/character n-gram + Logistic Regression baseline. Fit the
   vectoriser, imputation, resampling and threshold selection on training/folds
   only. Compare with the frozen rules and simple majority/class-prior baseline.
5. Measure precision, recall, F1, PR-AUC, false-positive rate and confusion counts
   with campaign-level confidence intervals. Report uncertainty and subgroup
   errors, including neutral disclosures and legitimate promotional language.
6. Choose review thresholds on validation, freeze them and run the held-out test
   once. If probabilities are ever exposed, assess calibration/Brier score and
   recalibration without test leakage; do not label arbitrary rule scores as
   probabilities. Evaluate abstention and review workload as well as accuracy.
7. Only then compare an appropriately sized encoder/deep model. Save actual
   weights, training examples/counts, epochs, seed, wall time, hardware, licences
   and negative results. RAG can explain permitted source documents; it is not a
   substitute for case labels or firm verification. Any LLM must abstain when its
   cited evidence is missing or unsupported.

## Implemented split guard

`smartinvest.evaluation.audit_split_manifest` checks metadata-only train,
validation and test lists for disjoint sample IDs/campaigns and strict temporal
order. Optional normalised-text SHA-256 fingerprints detect exact duplication.
It prints aggregate dates/counts, never raw messages. This is groundwork, not a
trained model or full governance/near-duplicate audit.

```json
{
  "train": [{"sample_id":"example-train", "campaign_id":"campaign-a", "observed_at":"2024-01-01T00:00:00Z"}],
  "validation": [{"sample_id":"example-validation", "campaign_id":"campaign-b", "observed_at":"2024-06-01T00:00:00Z"}],
  "test": [{"sample_id":"example-test", "campaign_id":"campaign-c", "observed_at":"2025-01-01T00:00:00Z"}]
}
```

This example is **synthetic metadata only**, not a claim of real collected data.
Run `python -m smartinvest.evaluation split-manifest.json`. Passing this guard
does not validate labels, source rights, consent, correct campaign grouping or
near duplicates. Human review and the separate data gate remain required.

## Progression to an advanced research portfolio

Deliver an evidence-backed dataset card, reproducible experiment scripts, frozen
splits, trained baseline/model card, error-analysis notebook and comparative
results. Then assess robust URL/identity features with approved source access,
model drift, input abuse, request-size limits, retention and human review. Public
deployment requires further work; this release remains a local student prototype.
