"""Small author-written routing smoke set, not a representative user benchmark."""
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from agent import build_agent
from router import LocalRouter, MODEL_ID, MODEL_REVISION
from sources import CARDS, SourceStore, lexical

CASES = [
    ("What happens to the Graduate visa in 2027?", "graduate"),
    ("I finish my course this year. What next?", "graduate"),
    ("How long can a PhD graduate stay?", "graduate"),
    ("Tell me about post-study options", "graduate"),
    ("How many hours can I work?", "work"),
    ("Can I freelance while studying?", "work"),
    ("Is dissertation time a holiday for employment?", "work"),
    ("Can I take a job with Uber?", "work"),
    ("How do I protect my rental deposit?", "housing"),
    ("My landlord wants a deposit", "housing"),
    ("I need accommodation", "housing"),
    ("How do I find a room?", "housing"),
    ("Do students pay Council Tax?", "tax"),
    ("My household got a council bill", "tax"),
    ("Where is the tax bill exemption?", "tax"),
    ("Do I get a student discount on Council Tax?", "tax"),
    ("A caller demands a Home Office fine", "scams"),
    ("Is a guaranteed visa a scam?", "scams"),
    ("They threatened to deport me unless I pay immediately", "scams"),
    ("I received a suspicious MoneyGram request", "scams"),
    ("Write a chocolate cake recipe", "other"),
    ("What is the capital of Japan?", "other"),
    ("Explain quantum gravity", "other"),
    ("Give me football scores", "other"),
]


def main():
    router = LocalRouter(); rows = []; latencies = []
    store = SourceStore("replay"); agent = build_agent(store, router)
    for q, expected in CASES:
        proposed = router.propose(q)
        if proposed["mode"] != "local_llm": raise RuntimeError("Real model evaluation blocked: " + json.dumps(proposed))
        baseline, _ = lexical(q); baseline = baseline[0] if baseline else "other"
        answer = agent.invoke({"question": q, "nation": "England"})["answer"]
        selected = answer.get("routing", {}).get("selected_topics", [])
        hybrid = selected[0] if selected else "other"
        rows.append({"question": q, "expected": expected, "llm_topic": proposed["topic"], "baseline_topic": baseline, "guarded_topic": hybrid, "llm_latency_ms": proposed["latency_ms"]})
        latencies.append(proposed["latency_ms"])
    report = {"evaluated_at_utc": datetime.now(timezone.utc).isoformat(), "model": MODEL_ID, "revision": MODEL_REVISION, "training": "Pretrained model inference only; no local training or fine-tuning.", "evaluation": "24 small author-written routing cases created during implementation; development smoke set, NOT held-out/generalisation evidence.", "device": "CPU, 2 torch threads", "python": platform.python_version(), "cases": len(rows),
              "prompt_examples": "Six fixed few-shot examples in router.py; this smoke set was used during prompt development.", "baseline_correct": sum(r["baseline_topic"] == r["expected"] for r in rows), "llm_correct": sum(r["llm_topic"] == r["expected"] for r in rows), "guarded_correct": sum(r["guarded_topic"] == r["expected"] for r in rows), "llm_median_ms": statistics.median(latencies), "llm_cold_first_ms": latencies[0], "rows": rows}
    Path("examples/routing-evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k:v for k,v in report.items() if k != "rows"}, indent=2))


if __name__ == "__main__": main()
