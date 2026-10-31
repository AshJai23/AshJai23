"""Synthetic edge cases; full-source/model smoke is separate."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalogue import classify
from retrieval import Lexical,Retriever

class RetrievalTests(unittest.TestCase):
    def test_explicit_charge_and_ambiguous_codes(self):
        self.assertEqual(classify('POST'),'charge_adjustment_review')
        self.assertEqual(classify('gift_0001_10'),'charge_adjustment_review')
        self.assertEqual(classify('DCGS0003'),'ambiguous_code_review')
        self.assertEqual(classify(None),'missing_code')
    def test_product_shaped_is_only_candidate(self):
        self.assertEqual(classify('12345A'),'product_code_candidate')
        self.assertEqual(classify('123456'),'ambiguous_code_review')
    def test_bm25_relevance_and_no_overlap(self):
        lexical=Lexical([{'text':'red ceramic strawberry jar'},{'text':'blue cotton bag'}])
        scores=lexical.score('strawberry ceramic')
        self.assertGreater(scores[0],scores[1])
        self.assertTrue((lexical.score('unknownword')==0).all())
    def test_empty_lexical_corpus(self):
        self.assertEqual(len(Lexical([]).score('jar')),0)
    def test_invalid_requests_rejected_before_model(self):
        r=Retriever.__new__(Retriever)
        for value in ['', 'x'*501,None]:
            with self.assertRaises(ValueError):r.search(value)
        with self.assertRaises(ValueError):r.search('jar',mode='execute shell')
        with self.assertRaises(ValueError):r.search('jar',kind='secret files')
        with self.assertRaises(ValueError):r.search('jar',k=6)
    def test_corpus_index_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'corpus.json').write_text('[]');(p/'manifest.json').write_text(json.dumps({'corpus_sha256':'wrong'}))
            with self.assertRaisesRegex(ValueError,'mismatch'):Retriever(str(p/'corpus.json'),str(p))

if __name__=='__main__':unittest.main(verbosity=2)
