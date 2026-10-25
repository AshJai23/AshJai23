# Trained routing model and launch status

The app now loads a **trained classification head on frozen Qwen features**.
The base Qwen language-model weights were not changed. This is supervised
transfer learning for question routing, not full LLM fine-tuning, and it does not
teach a model immigration rules. Rules remain reviewed official source cards.

## Data and method

- 144 training questions, 36 validation questions, 48 held-out test questions.
- Six balanced labels: graduate, work, housing, tax, scams and other.
- All questions are AI-authored synthetic examples. No real student messages,
  private documents, passport records or user conversations were used.
- Each manually authored scenario family has two paraphrases. Both stay in the
  same preassigned split; exact duplicate text and family overlap are checked.
  Related vocabulary naturally occurs across splits. The same AI authored the
  data, so this is not an independent or representative student benchmark.
- Pinned Qwen2.5-0.5B-Instruct produces frozen token representations. Mean and
  last-token states are concatenated, centred using the training mean only and
  L2-normalised. A 6-class linear neural head has **10,758 fitted parameters**.
- Full-batch AdamW, seed 42, learning rate 0.03, weight decay 0.01, maximum 400
  epochs. Validation cross-entropy selects the checkpoint; patience is 40.
- The validation set selected epoch **400** and threshold **0.90**. Test results
  were examined only after weights and threshold were saved and hashed; no
  retraining or threshold change was made in response to test failures.
- A candidate threshold had to accept at least 12 validation questions, achieve
  at least 95% correct accepted proposals and falsely accept no validation
  out-of-scope questions. Coverage then determines the selected eligible value.

Source files are in `data/`, with fixed dataset construction in
`training/build_dataset.py`. The classifier artifact is plain JSON at
`artifacts/router-head.json`; its SHA-256 and dataset hashes are in the reports.
No downloaded base-model weights are committed to GitHub.

## Actual measurements

| Measurement | Result |
|---|---:|
| Frozen feature extraction, including initial model load | 26.00 seconds |
| Classification-head fitting | 0.345 seconds |
| Training accuracy | 144/144 (100%) |
| Validation accuracy | 32/36 (88.9%) |
| Held-out raw classifier result | 43/48 (89.6%) |
| Keyword baseline on the same test | 40/48 (83.3%) |
| Majority-class baseline on the same test | 8/48 (16.7%) |
| Correct confidence-accepted test proposals | 33/34 (97.1%) |
| Accepted coverage of in-scope test questions | 34/40 (85%) |
| False accepts among eight out-of-scope test questions | 0/8 |

These timings were measured on CPU with two PyTorch threads and cached public
base-model files. A first download is additional time. Fitting a small head is
fast because the language model's existing representations are reused; this is
not a claim that a 0.5-billion-parameter language model trained in 26 seconds.

The old prompt-only experiment used different development questions. Its 8/24
result is retained as historical evidence, not used as a controlled comparator
for this held-out test. The directly comparable baseline here is 40/48.

## Remaining failures and serving behaviour

The held-out classifier made five mistakes. One passed the confidence threshold:
“Who confirms vacation dates for a postgraduate who wants more shifts?” was
routed to Graduate rather than work guidance with confidence 0.9328. This error
was retained; the test was not used to patch a special case or raise a threshold.
Other errors included tutoring for cash and a lost deposit certificate; these
were below the model acceptance threshold. Full questions and predictions are
in `examples/heldout-evaluation.json`.

The default local-pilot policy allows a confidence-accepted trained proposal
only if the saved test report passes its predeclared local gate and matches the
artifact hash. It may select only one of five fixed official topics. Uncertain
or unavailable inference falls back to visible keyword navigation; unknown
questions without a keyword match abstain. Source identity, withdrawal, anchor
and reviewed-content hash checks still control whether a summary is displayed.
The classifier cannot generate legal advice, arbitrary URLs or external actions.

The gate requires accepted precision of at least 95%, in-scope coverage of at
least 75%, and no out-of-scope false accepts on this test. This artifact passed.
That is a **local engineering gate**, not proof about future questions or a
public-production certification. Accepted precision is a routing metric, not
legal accuracy and not the accuracy of every final fallback response.

## Run and reproduce

After the README dependency installation:

```bash
# Check artifact, actual model inference and five official live sources:
python launch.py --mode live --check-only
# Start the warmed local app:
python launch.py --mode live
# Open http://127.0.0.1:8000
```

For offline demonstration use `--mode replay`, which is labelled as saved data.
Set `ROUTING_POLICY=keyword_guard` to keep model proposals in shadow mode.
Set `LLM_ENABLED=0` with the direct Uvicorn command for baseline-only operation.

To reproduce fitting and the frozen-artifact test:

```bash
python train_router.py
python train_router.py --evaluate-test
python -m unittest discover -s tests -v
python smoke.py --mode live --output outputs/trained-live-smoke.json
```

Reproduction can vary across hardware/library versions. Every run writes actual
losses, timings and artifact hashes. Do not tune against the published test and
then call that same test unseen; reserve a new independent test for future
development. Synthetic test success is not a substitute for student feedback.

## What can be launched now?

The trained app is prepared for **local pilot testing**. No public URL or
real-user service was launched in this change. `launch.py` binds only to
127.0.0.1. All current safeguards, source labels and support references remain.

Public operation still needs an independently reviewed student-question test,
content review, hosting with TLS, private operations access, accessibility/load
testing and an agreed support/incident process. These were not established by
training a head. Docker configuration remains untested because Docker was not
available. See `OPERATIONS.md` for the deployment work that remains.

Technical basis: [Hugging Face model output documentation](https://huggingface.co/docs/transformers/main_classes/output)
and the [Qwen model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct).
