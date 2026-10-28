"""Synthetic fixtures only: DST, fact grain, missingness and SQL integrity."""
import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
import main as m
from unittest.mock import patch
from urllib.error import URLError

def fixture():
    return {'captured_at_utc':'2026-10-28T10:00:00Z','window_start':'2026-10-27T00:00Z','window_end':'2026-10-27T01:00Z','regional_start':'2026-10-27T00:00Z','mode':'SYNTHETIC TEST ONLY','national':[{'from':'2026-10-27T00:00Z','to':'2026-10-27T00:30Z','intensity':{'actual':0,'forecast':10}},{'from':'2026-10-27T00:30Z','to':'2026-10-27T01:00Z','intensity':{'actual':None,'forecast':20}}],'regional':[{'from':'2026-10-27T00:00Z','to':'2026-10-27T00:30Z','regions':[{'regionid':13,'intensity':{'forecast':12}}]}]}

class BITests(unittest.TestCase):
    def test_collection_spring_window_uses_local_midnights(self):
        with patch.object(m,'fetch',return_value=({'data':[]},{})) as f:
            s=m.collect(m.stamp('2026-03-29T23:00Z'));self.assertEqual(s['window_start'],'2026-03-27T00:00Z');self.assertEqual(s['regional_start'],'2026-03-29T00:00Z');self.assertEqual(f.call_count,2)
    def test_collection_autumn_window_includes_25_hour_regional_day(self):
        with patch.object(m,'fetch',return_value=({'data':[]},{})):
            s=m.collect(m.stamp('2026-10-26T00:00Z'));self.assertEqual(s['regional_start'],'2026-10-24T23:00Z')
    def test_live_outage_has_no_synthetic_or_replay_fallback(self):
        with patch.object(m,'fetch',side_effect=URLError('SYNTHETIC TEST OUTAGE')):
            with self.assertRaises(URLError):m.collect(m.stamp('2026-10-28T00:00Z'))
    def test_autumn_has_50_slots(self):self.assertEqual(m.expected_slots('2026-10-25'),50)
    def test_spring_has_46_slots(self):self.assertEqual(m.expected_slots('2026-03-29'),46)
    def test_ordinary_day_has_48_slots(self):self.assertEqual(m.expected_slots('2026-10-27'),48)
    def test_repeated_local_hour_has_distinct_utc_fold_and_period(self):
        a=m.time_row('2026-10-25T00:30Z','2026-10-25T01:00Z');b=m.time_row('2026-10-25T01:30Z','2026-10-25T02:00Z');self.assertNotEqual(a[0],b[0]);self.assertEqual(a[3][11:16],b[3][11:16]);self.assertEqual((a[4],b[4]),(0,1));self.assertNotEqual(a[5],b[5])
    def test_non_aligned_or_wrong_duration_rejected(self):
        with self.assertRaises(ValueError):m.time_row('2026-10-25T00:15Z','2026-10-25T00:45Z')
        with self.assertRaises(ValueError):m.time_row('2026-10-25T00:00Z','2026-10-25T01:00Z')
    def test_negative_nan_bool_and_strings_rejected(self):
        for value in [-1,float('nan'),True,'20']:
            with self.assertRaises(ValueError):m.number(value)
    def test_zero_is_counted_null_is_not(self):
        with tempfile.TemporaryDirectory() as d:
            s=m.build(fixture(),d);self.assertEqual(s['quality']['missing_actual'],1);self.assertEqual(s['national_daily'][0]['actual_count'],1);self.assertEqual(s['national_daily'][0]['mean_actual_g'],0);self.assertEqual(s['national_daily'][0]['paired_mae_g'],10)
    def test_exact_duplicates_idempotent(self):
        s=fixture();s['national'].append(copy.deepcopy(s['national'][0]))
        with tempfile.TemporaryDirectory() as d:
            a=m.build(s,d);b=m.build(s,d);self.assertEqual(a,b);self.assertEqual(a['national_fact_rows'],2);self.assertEqual(a['quality']['exact_duplicates'],1)
    def test_conflicting_duplicate_fails(self):
        s=fixture();s['national'].append({**s['national'][0],'intensity':{'actual':99,'forecast':10}})
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):m.build(s,d)
    def test_api_extra_boundary_row_excluded(self):
        s=fixture();s['national'].append({'from':'2026-10-26T23:30Z','to':'2026-10-27T00:00Z','intensity':{'actual':100,'forecast':100}})
        with tempfile.TemporaryDirectory() as d:r=m.build(s,d);self.assertEqual(r['national_fact_rows'],2);self.assertEqual(r['quality']['outside_window_rows'],1)
    def test_forecast_grain_does_not_multiply_national_facts(self):
        s=fixture();s['regional'][0]['regions']+=[{'regionid':1,'intensity':{'forecast':0}}]
        with tempfile.TemporaryDirectory() as d:
            a=m.build(s,d);self.assertEqual(a['national_fact_rows'],2);self.assertEqual(a['regional_fact_rows'],2);self.assertEqual(a['national_daily'][0]['mean_actual_g'],0)
    def test_unknown_region_rejected(self):
        s=fixture();s['regional'][0]['regions'][0]['regionid']=15
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):m.build(s,d)
    def test_sql_foreign_key_and_unique_constraints(self):
        db=sqlite3.connect(':memory:');db.executescript(m.SCHEMA.read_text())
        with self.assertRaises(sqlite3.IntegrityError):db.execute("INSERT INTO fact_national VALUES ('missing',1,2)")
        db.close()
    def test_sql_dump_restores_all_facts_and_view(self):
        with tempfile.TemporaryDirectory() as d:
            a=m.build(fixture(),d);db=sqlite3.connect(':memory:');db.executescript((Path(d)/'warehouse.sql').read_text());self.assertEqual(db.execute('SELECT COUNT(*) FROM fact_national').fetchone()[0],2);self.assertEqual(db.execute('SELECT mean_actual_g FROM v_national_daily').fetchone()[0],0);self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall());db.close()
    def test_missing_fact_interval_remains_on_time_axis(self):
        s=fixture();s['national'].pop()
        with tempfile.TemporaryDirectory() as d:
            a=m.build(s,d);db=sqlite3.connect(Path(d)/'carbon.sqlite');self.assertEqual(db.execute('SELECT COUNT(*) FROM dim_time').fetchone()[0],2);self.assertEqual(a['missing_national_intervals'],1);db.close()
    def test_future_window_is_not_historical_data(self):
        s=fixture();s['window_end']='2027-01-01T00:00Z'
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):m.build(s,d)
    def test_partial_day_denominator_stays_full_day(self):
        with tempfile.TemporaryDirectory() as d:
            a=m.build(fixture(),d);self.assertEqual(a['national_daily'][0]['actual_coverage'],1/48);self.assertFalse(a['national_daily'][0]['complete_intervals']);self.assertEqual(a['missing_regional_intervals'],5)

if __name__=='__main__':unittest.main()
