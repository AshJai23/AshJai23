import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from agent import build_agent
from sources import SourceStore
from trained_router import TrainedRouter, LABELS, ROOT
from train_router import check_splits, read


class TrainingTests(unittest.TestCase):
    def test_preassigned_family_splits_are_disjoint(self):
        self.assertEqual(check_splits(), {"train": 144, "validation": 36, "test": 48})
    def test_each_split_is_balanced_and_explicitly_synthetic(self):
        for split in ("train", "validation", "test"):
            rows = read(split)
            self.assertEqual(len({sum(r["label"] == label for r in rows) for label in LABELS}), 1)
            self.assertTrue(all("synthetic" in r["provenance"] for r in rows))
    def test_trained_artifact_matches_saved_fit_and_test(self):
        sha = hashlib.sha256((ROOT / "artifacts/router-head.json").read_bytes()).hexdigest()
        fit = json.loads((ROOT / "examples/training-report.json").read_text())
        test = json.loads((ROOT / "examples/heldout-evaluation.json").read_text())
        self.assertEqual(sha, fit["artifact_sha256"]); self.assertEqual(sha, test["artifact_sha256"])
        self.assertEqual(fit["base_model_parameters_updated"], 0)
        self.assertGreater(fit["trained_parameters"], 0)
    def test_confidence_threshold_comes_from_validation(self):
        a = json.loads((ROOT / "artifacts/router-head.json").read_text())
        fit = json.loads((ROOT / "examples/training-report.json").read_text())
        self.assertEqual(a["threshold"], fit["chosen_threshold"]["threshold"])
    def test_missing_trained_weights_never_claim_inference_success(self):
        router = TrainedRouter(artifact="/nonexistent/router-head.json")
        self.assertEqual(router.propose("work")["mode"], "baseline_fallback")
    def test_trained_proposal_does_not_bypass_source_guard(self):
        router = TrainedRouter(False)
        with patch.object(router, "propose", return_value={"mode":"trained_qwen_head", "topic":"work", "accepted":True}):
            graph = build_agent(SourceStore("replay"), router)
            result = graph.invoke({"question":"Explain quantum gravity", "nation":"England"})["answer"]
        self.assertEqual(result["status"], "out_of_scope"); self.assertEqual(result["cards"], [])
    def test_low_confidence_proposal_keeps_reviewed_source_path(self):
        router = TrainedRouter(False)
        with patch.object(router, "propose", return_value={"mode":"trained_qwen_head", "topic":"other", "accepted":False}):
            result = build_agent(SourceStore("replay"), router).invoke({"question":"My rental deposit", "nation":"England"})["answer"]
        self.assertEqual(result["cards"][0]["topic"], "housing")
    def test_passed_gate_allows_semantic_routing_to_fixed_source(self):
        router = TrainedRouter(False)
        with patch.object(router, "propose", return_value={"mode":"trained_qwen_head", "topic":"tax", "accepted":True, "pilot_gate_passed":True}):
            result = build_agent(SourceStore("replay"), router).invoke({"question":"Can I get relief from the city levy?", "nation":"England"})["answer"]
        self.assertEqual(result["cards"][0]["topic"], "tax")
        self.assertEqual(result["routing"]["routing_decision"], "trained_assist")
    def test_even_passed_gate_cannot_introduce_an_arbitrary_tool_url(self):
        router = TrainedRouter(False)
        with patch.object(router, "propose", return_value={"mode":"trained_qwen_head", "topic":"http://127.0.0.1/secrets", "accepted":True, "pilot_gate_passed":True}):
            result = build_agent(SourceStore("replay"), router).invoke({"question":"Access internal credentials", "nation":"England"})["answer"]
        self.assertEqual(result["cards"], [])


if __name__ == "__main__": unittest.main()
