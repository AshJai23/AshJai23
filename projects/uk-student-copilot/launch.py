"""Preflight then launch the trained local pilot. Never opens a public listener."""
import argparse
import hashlib
import json
from trained_router import TrainedRouter, ROOT
from sources import SourceStore, CARDS
from app import create_app


def main():
    p = argparse.ArgumentParser(); p.add_argument("--mode", choices=["live", "replay"], default="live"); p.add_argument("--check-only", action="store_true")
    args = p.parse_args()
    artifact = ROOT / "artifacts/router-head.json"
    report = json.loads((ROOT / "examples/heldout-evaluation.json").read_text())
    sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if report.get("artifact_sha256") != sha or not report.get("local_pilot_gate"):
        raise RuntimeError("This artifact has not passed the saved local-pilot test gate")
    store = SourceStore(args.mode); sources = {k: store.get(k)["status"] for k in CARDS}
    if any(v != "verified" for v in sources.values()): raise RuntimeError("Source review/availability issue: " + json.dumps(sources))
    router = TrainedRouter(); probe = router.propose("Graduate visa")
    if probe["mode"] != "trained_qwen_head": raise RuntimeError("Trained model unavailable: " + json.dumps(probe))
    print(json.dumps({"ready_for": "local pilot only", "source_mode": args.mode, "sources": sources, "trained_model": probe["mode"], "artifact_sha256": sha, "public_deployment": False}, indent=2), flush=True)
    if not args.check_only:
        import uvicorn
        uvicorn.run(create_app(store, router), host="127.0.0.1", port=8000, access_log=False, limit_concurrency=8)


if __name__ == "__main__": main()
