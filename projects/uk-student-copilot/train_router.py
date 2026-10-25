"""Train on train only; select epoch/threshold on validation; test is separate."""
import argparse
import copy
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import torch
from trained_router import Features, LABELS, ROOT
from router import MODEL_ID, MODEL_REVISION
from sources import lexical


def read(split): return [json.loads(line) for line in (ROOT / f"data/router_{split}.jsonl").read_text().splitlines() if line]
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def check_splits():
    splits = {s: read(s) for s in ("train", "validation", "test")}
    for a, b in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if {r["family"] for r in splits[a]} & {r["family"] for r in splits[b]}: raise ValueError("Scenario family leakage")
        if {r["text"].casefold().strip() for r in splits[a]} & {r["text"].casefold().strip() for r in splits[b]}: raise ValueError("Duplicate text leakage")
    return {k: len(v) for k, v in splits.items()}


def raw_predictions(x, head):
    with torch.no_grad(): return torch.softmax(head(x), dim=1)


def train():
    torch.manual_seed(42); torch.set_num_threads(2)
    counts = check_splits(); train_rows = read("train"); val_rows = read("validation")
    t = time.perf_counter(); features = Features()
    x = features.encode([r["text"] for r in train_rows]); v = features.encode([r["text"] for r in val_rows])
    feature_seconds = time.perf_counter() - t
    # Fit all centering/learned parameters on training rows only.
    mean = x.mean(dim=0); x = torch.nn.functional.normalize(x - mean, dim=1); v = torch.nn.functional.normalize(v - mean, dim=1)
    y = torch.tensor([LABELS.index(r["label"]) for r in train_rows]); vy = torch.tensor([LABELS.index(r["label"]) for r in val_rows])
    head = torch.nn.Linear(x.shape[1], 6); optimizer = torch.optim.AdamW(head.parameters(), lr=.03, weight_decay=.01)
    best = None; best_loss = float("inf"); best_epoch = 0; history = []; started = time.perf_counter()
    for epoch in range(1, 401):
        optimizer.zero_grad(); loss = torch.nn.functional.cross_entropy(head(x), y); loss.backward(); optimizer.step()
        with torch.no_grad(): val_loss = float(torch.nn.functional.cross_entropy(head(v), vy))
        history.append({"epoch": epoch, "training_loss": float(loss.detach()), "validation_loss": val_loss})
        if val_loss < best_loss - 1e-5: best = copy.deepcopy(head.state_dict()); best_loss = val_loss; best_epoch = epoch
        if epoch - best_epoch >= 40: break
    head.load_state_dict(best); fit_seconds = time.perf_counter() - started
    probabilities = raw_predictions(v, head); confidence, pred = probabilities.max(dim=1)
    selection = []
    for threshold in (.5, .6, .7, .8, .9, .95, 1.01):
        accepted = (pred != LABELS.index("other")) & (confidence >= threshold)
        n = int(accepted.sum()); correct = int(((pred == vy) & accepted).sum()); oos = int(((vy == LABELS.index("other")) & accepted).sum())
        selection.append({"threshold": threshold, "accepted": n, "correct": correct, "accepted_precision": correct/n if n else None, "out_of_scope_false_accepts": oos})
    eligible = [r for r in selection if r["accepted"] >= 12 and r["accepted_precision"] >= .95 and r["out_of_scope_false_accepts"] == 0]
    chosen = max(eligible, key=lambda r:(r["accepted"], r["threshold"])) if eligible else selection[-1]
    a = {"format_version": 1, "model_id": MODEL_ID, "revision": MODEL_REVISION, "labels": LABELS,
         "feature_method": "Concatenate mean and last token of frozen Qwen AutoModel states; subtract training mean; L2 normalise",
         "threshold": chosen["threshold"], "mean": mean.tolist(), "weight": head.weight.detach().tolist(), "bias": head.bias.detach().tolist()}
    (ROOT / "artifacts").mkdir(exist_ok=True)
    artifact = ROOT / "artifacts/router-head.json"; artifact.write_text(json.dumps(a, separators=(",", ":"), allow_nan=False) + "\n")
    report = {"trained_at_utc": datetime.now(timezone.utc).isoformat(), "seed": 42, "data": "AI-authored synthetic intent examples, not real student data", "split_counts": counts,
              "split_policy": "Scenario-family groups assigned before fit; no duplicate text or group across splits. Test labels/text not used for fitting or threshold selection; split checker reads them only to verify disjointness.",
              "trained_parameters": sum(p.numel() for p in head.parameters()), "base_model_parameters_updated": 0,
              "feature_extraction_seconds": feature_seconds, "classifier_fit_seconds": fit_seconds, "epochs_run": len(history), "selected_epoch": best_epoch,
              "train_accuracy": float((raw_predictions(x, head).argmax(1) == y).float().mean()), "validation_accuracy": float((pred == vy).float().mean()),
              "validation_thresholds": selection, "chosen_threshold": chosen, "artifact_sha256": digest(artifact),
              "dataset_sha256": {s: digest(ROOT / f"data/router_{s}.jsonl") for s in counts}, "loss_history": history,
              "training_scope": "Supervised classification head on frozen pretrained Qwen features. Not full Qwen fine-tuning and not learning visa rules."}
    (ROOT / "examples/training-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("loss_history", "validation_thresholds")}, indent=2))


def evaluate_test():
    from trained_router import TrainedRouter
    report = json.loads((ROOT / "examples/training-report.json").read_text()); path = ROOT / "artifacts/router-head.json"
    if digest(path) != report["artifact_sha256"]: raise ValueError("Artifact changed after validation")
    for split, sha in report["dataset_sha256"].items():
        if digest(ROOT / f"data/router_{split}.jsonl") != sha: raise ValueError("Dataset changed after fit")
    router = TrainedRouter(); rows = []; t = time.perf_counter()
    for row in read("test"):
        p = router.propose(row["text"])
        if p["mode"] != "trained_qwen_head": raise RuntimeError(p)
        base, _ = lexical(row["text"])
        rows.append({**row, "predicted": p["topic"], "accepted": p["accepted"], "confidence": p["label_probability"], "baseline": base[0] if base else "other"})
    n = len(rows); accepted = [r for r in rows if r["accepted"]]; correct = sum(r["predicted"] == r["label"] for r in rows)
    known = [r for r in rows if r["label"] != "other"]
    result = {"evaluated_at_utc": datetime.now(timezone.utc).isoformat(), "artifact_sha256": digest(path), "test_count": n,
              "test_accuracy": correct/n, "test_correct": correct, "lexical_baseline_correct": sum(r["baseline"] == r["label"] for r in rows), "majority_baseline_correct": 8,
              "accepted_count": len(accepted), "accepted_correct": sum(r["predicted"] == r["label"] for r in accepted),
              "accepted_precision": sum(r["predicted"] == r["label"] for r in accepted)/len(accepted) if accepted else None,
              "known_topic_coverage": sum(r["accepted"] for r in known)/len(known), "out_of_scope_false_accepts": sum(r["accepted"] for r in rows if r["label"] == "other"),
              "evaluation_seconds": time.perf_counter()-t, "limitations": "Single small synthetic held-out scenario-family test; authored by the same AI that built the training set. Not independent student feedback, legal accuracy, or a public-launch certification.", "rows": rows}
    # Predeclared conservative local-pilot gate; never means public readiness.
    result["local_pilot_gate"] = bool(result["accepted_precision"] is not None and result["accepted_precision"] >= .95 and result["known_topic_coverage"] >= .75 and result["out_of_scope_false_accepts"] == 0)
    (ROOT / "examples/heldout-evaluation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--evaluate-test", action="store_true")
    if parser.parse_args().evaluate_test: evaluate_test()
    else: train()
