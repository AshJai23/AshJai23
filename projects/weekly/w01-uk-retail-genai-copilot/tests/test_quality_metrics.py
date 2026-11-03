"""Synthetic ranked-ID fixtures validate arithmetic, not real retrieval quality."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from quality_metrics import retrieval_metrics,percentile_nearest_rank

class Measures(unittest.TestCase):
    def test_recall_precision_and_mrr(self):
        r=retrieval_metrics(['a','c','d','e'],['x','c','a'])
        self.assertEqual(r['recall_at_3'],.5)
        self.assertAlmostEqual(r['precision_at_3'],2/3)
        self.assertEqual(r['mrr_at_3'],.5)
        self.assertTrue(r['hit_at_3'])
    def test_no_result_or_no_relevant_result(self):
        for ranked in [[],['x','y','z']]:
            r=retrieval_metrics(['a'],ranked)
            self.assertEqual(r['mrr_at_3'],0)
            self.assertEqual(r['recall_at_3'],0)
    def test_invalid_reference_or_duplicates_rejected(self):
        with self.assertRaises(ValueError):retrieval_metrics([],['a'])
        with self.assertRaises(ValueError):retrieval_metrics(['a'],['a','a'])
    def test_nearest_rank_latency(self):
        self.assertEqual(percentile_nearest_rank([5,2,1,3,4],.95),5)
        self.assertEqual(percentile_nearest_rank([5,2,1,3,4],.5),3)
        self.assertIsNone(percentile_nearest_rank([],.95))
if __name__=='__main__':unittest.main(verbosity=2)
