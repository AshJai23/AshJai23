"""Frozen Qwen features + actually fitted classification head, JSON weights."""
import json
import hashlib
import os
import threading
import time
from pathlib import Path
from router import MODEL_ID, MODEL_REVISION

LABELS = ["graduate", "work", "housing", "tax", "scams", "other"]
ROOT = Path(__file__).parent


class Features:
    def __init__(self): self.model = None; self.tokenizer = None
    def load(self):
        import torch
        from transformers import AutoModel, AutoTokenizer
        torch.set_num_threads(2)
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION, trust_remote_code=False)
        self.model = AutoModel.from_pretrained(MODEL_ID, revision=MODEL_REVISION, trust_remote_code=False, use_safetensors=True, dtype="auto").eval()
        for p in self.model.parameters(): p.requires_grad_(False)
    def encode(self, texts):
        import torch
        if self.model is None: self.load()
        vectors = []
        for text in texts:
            tokens = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
            with torch.inference_mode():
                hidden = self.model(**tokens, use_cache=False).last_hidden_state.float()[0]
                vectors.append(torch.cat((hidden.mean(dim=0), hidden[-1])).clone())
        return torch.stack(vectors)


class TrainedRouter:
    trained = True
    def __init__(self, enabled=True, artifact=None):
        self.enabled = enabled; self.features = Features(); self.lock = threading.Lock()
        self.path = Path(artifact or ROOT / "artifacts/router-head.json")
        self.artifact = None; self.model = None
        self.pilot_gate_passed = False
    def load(self):
        import torch
        a = json.loads(self.path.read_text())
        if a["model_id"] != MODEL_ID or a["revision"] != MODEL_REVISION or a["labels"] != LABELS:
            raise ValueError("Artifact model identity mismatch")
        mean = torch.tensor(a["mean"], dtype=torch.float32)
        weight = torch.tensor(a["weight"], dtype=torch.float32)
        bias = torch.tensor(a["bias"], dtype=torch.float32)
        if weight.shape != (6, mean.numel()) or bias.shape != (6,) or not all(torch.isfinite(x).all() for x in (mean, weight, bias)):
            raise ValueError("Invalid classifier weights")
        if not 0 <= a["threshold"] <= 1.01: raise ValueError("Invalid confidence threshold")
        self.features.load(); self.model = self.features.model
        self.artifact = a; self.mean = mean; self.weight = weight; self.bias = bias
        report_path = ROOT / "examples/heldout-evaluation.json"
        if report_path.exists():
            report = json.loads(report_path.read_text())
            self.pilot_gate_passed = (report.get("local_pilot_gate") is True
                and report.get("artifact_sha256") == hashlib.sha256(self.path.read_bytes()).hexdigest()
                and os.getenv("ROUTING_POLICY", "trained_assist") == "trained_assist")
    def propose(self, question):
        if not self.enabled: return {"mode": "baseline", "topic": None, "accepted": False, "reason": "Trained model explicitly disabled"}
        start = time.perf_counter()
        with self.lock:
            try:
                import torch
                if self.artifact is None: self.load()
                x = self.features.encode([question]) - self.mean
                x = torch.nn.functional.normalize(x, dim=1)
                probabilities = torch.softmax(x @ self.weight.T + self.bias, dim=1)[0]
                index = int(probabilities.argmax()); confidence = float(probabilities[index])
                topic = LABELS[index]
                return {"mode": "trained_qwen_head", "model": MODEL_ID, "revision": MODEL_REVISION,
                        "serving_policy": "local_pilot_assist" if self.pilot_gate_passed else "keyword_guard",
                        "pilot_gate_passed": self.pilot_gate_passed,
                        "topic": topic, "accepted": topic != "other" and confidence >= self.artifact["threshold"],
                        "label_probability": round(confidence, 4), "threshold": self.artifact["threshold"],
                        "latency_ms": round((time.perf_counter()-start)*1000, 2)}
            except Exception as exc:
                return {"mode": "baseline_fallback", "topic": None, "accepted": False, "error_type": type(exc).__name__,
                        "latency_ms": round((time.perf_counter()-start)*1000, 2)}
