"""Real model + API smoke check. Raises instead of counting a fallback as success."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient
from app import create_app
from router import LocalRouter
from sources import SourceStore


def main():
    p = argparse.ArgumentParser(); p.add_argument("--mode", choices=["live", "replay"], default="live"); p.add_argument("--output", default="outputs/smoke.json")
    args = p.parse_args()
    app = create_app(SourceStore(args.mode), LocalRouter(), db_path=":memory:")
    c = TestClient(app); rows = []
    for q, nation in [("What changes for the Graduate visa in 2027?", "England"), ("Can I freelance while studying?", "England"),
                      ("How do I protect my rental deposit?", "Scotland"), ("I got a Council Tax bill", "England"),
                      ("A Home Office caller demands a fine", "England")]:
        response = c.post("/api/ask", json={"question": q, "nation": nation}); response.raise_for_status()
        answer = response.json(); rows.append(answer)
        print(answer["status"], answer.get("routing", {}).get("mode"), [card["topic"] for card in answer["cards"]], flush=True)
    report = {"executed_at_utc": datetime.now(timezone.utc).isoformat(), "mode": args.mode,
              "description": "Real local CPU LLM; in-process HTTP API client; source mode explicitly selected; no model mocks.",
              "responses": rows, "metrics": c.get("/metrics").text, "health": c.get("/healthz").json()}
    target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")
    assert all(r.get("routing", {}).get("mode") == "local_llm" for r in rows), "Actual model inference failed; see saved evidence"
    assert all(r["status"] == "answered" for r in rows), "Source unavailable or changed; see saved evidence"


if __name__ == "__main__": main()
