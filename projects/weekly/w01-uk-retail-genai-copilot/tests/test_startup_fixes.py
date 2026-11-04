"""Synthetic temporary files verify startup paths; no real source/model inference claimed."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import duckdb
from fastapi.testclient import TestClient
import platform_stats
import service
from api import create_app

class StartupFixes(unittest.TestCase):
    def test_missing_resource_is_optional(self):
        with patch.object(platform_stats,'_resource',None):
            self.assertIsNone(platform_stats.peak_rss_mib())
    def test_macos_bytes_and_linux_kib(self):
        fake=SimpleNamespace(RUSAGE_SELF=0,getrusage=lambda _:SimpleNamespace(ru_maxrss=1024*1024))
        with patch.object(platform_stats,'_resource',fake):
            with patch.object(platform_stats.sys,'platform','darwin'):
                self.assertEqual(platform_stats.peak_rss_mib(),1)
            with patch.object(platform_stats.sys,'platform','linux'):
                self.assertEqual(platform_stats.peak_rss_mib(),1024)
    def test_correct_metrics_even_median_and_nearest_rank_p95(self):
        from test_api import fixture
        runtime=fixture();runtime.latencies.extend(range(1,21))
        result=runtime.metrics()
        self.assertEqual(result['p50_seconds'],10.5)
        self.assertEqual(result['p95_seconds'],19)
    def test_empty_metrics_remain_null(self):
        from test_api import fixture
        m=fixture().metrics()
        self.assertIsNone(m['p50_seconds']);self.assertIsNone(m['p95_seconds'])
    def test_missing_setup_has_action_without_private_path(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(service,'ROOT',Path(directory)), TestClient(create_app()) as client:
                response=client.get('/v1/health')
                self.assertEqual(response.status_code,503)
                self.assertEqual(response.json()['setup']['code'],'warehouse_missing')
                self.assertIn('retail.py',response.json()['setup']['action'])
                self.assertNotIn(directory,response.text)
    def test_baseline_works_from_other_working_directory(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as elsewhere:
            root=Path(directory);(root/'data/raw').mkdir(parents=True)
            (root/'data/raw/source_manifest.json').write_text(json.dumps({'retrieved_at_utc':'2020-01-01T00:00:00Z','sha256':'synthetic-fixture','source':'synthetic unit fixture'}))
            (root/'data/corpus.json').write_text(json.dumps([{'id':'contract:fixture','kind':'project_contract','text':'Synthetic invoice field definition for unit testing.'}]))
            with duckdb.connect(str(root/'data/retail.duckdb')) as con:
                con.execute("CREATE TABLE transactions AS SELECT 'France' AS country,TIMESTAMP '2010-01-01' AS invoice_date")
                con.execute('CREATE TABLE raw_transactions AS SELECT * FROM transactions')
                con.execute('CREATE VIEW auditable_lines AS SELECT * FROM transactions')
            current=Path.cwd()
            try:
                os.chdir(elsewhere)
                with patch.object(service,'ROOT',root):
                    runtime=service.build_runtime(mode='bm25',with_generation=False)
                    result=runtime.ask('line_count for France')
                    self.assertEqual(result['answer']['answer'],'1')
                    self.assertFalse(result['generation']['enabled'])
            finally:os.chdir(current)

if __name__=='__main__':unittest.main(verbosity=2)
