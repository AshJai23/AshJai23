"""Synthetic fixtures test edge cases; measured results use the separate EA capture."""
import copy,json,math,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
import numpy as np
import main as m
from unittest.mock import patch
from urllib.error import URLError

def fixture(n=220):
    t=datetime(2026,10,1,tzinfo=timezone.utc)
    return {'captured_at_utc':'2026-10-10T00:00:00Z','station':{'id':m.STATION,'name':'SYNTHETIC TEST ONLY'},'measure':{'notation':m.MEASURE,'period':900,'unitName':'mASD','qualifier':'Stage'},'readings':[{'dateTime':(t+timedelta(minutes=15*i)).isoformat(),'value':1+.02*math.sin(i/15),'measure':m.ROOT+'/id/measures/'+m.MEASURE} for i in range(n)]}

class RiverTests(unittest.TestCase):
    def test_live_outage_has_no_synthetic_or_replay_fallback(self):
        with patch.object(m,'fetch',side_effect=URLError('SYNTHETIC TEST OUTAGE')):
            with self.assertRaises(URLError):m.collect()
    def test_naive_dates_rejected(self):
        with self.assertRaises(ValueError):m.stamp('2026-10-01T00:00')
    def test_conflicting_duplicate_fails(self):
        s=fixture();s['readings'].append({**s['readings'][0],'value':99})
        with self.assertRaises(RuntimeError):m.clean(s)
    def test_exact_duplicate_not_double_counted(self):
        s=fixture();s['readings'].append(copy.deepcopy(s['readings'][0]));r,q=m.clean(s);self.assertEqual(len(r),220);self.assertEqual(q['duplicates'],1)
    def test_missing_slots_are_not_imputed_or_bridged(self):
        s=fixture();s['readings'].pop(100);r,q=m.clean(s);self.assertEqual(q['missing_15min_slots'],1);self.assertEqual(len(m.windows(r)[1]),211)
    def test_nonfinite_and_boolean_rejected(self):
        s=fixture();s['readings'][0]['value']=float('nan');s['readings'][1]['value']=True;r,q=m.clean(s);self.assertEqual(q['invalid'],2)
    def test_future_and_wrong_measure_excluded(self):
        s=fixture();s['readings'][0]['dateTime']='2027-01-01T00:00:00Z';s['readings'][1]['measure']='https://example.org/other';r,q=m.clean(s);self.assertEqual(q['future'],1);self.assertEqual(q['wrong_measure'],1)
    def test_negative_local_datum_is_valid(self):
        s=fixture();s['readings'][0]['value']=-.1;r,q=m.clean(s);self.assertEqual(q['invalid'],0);self.assertEqual(r[0][1],-.1)
    def test_incorrect_measure_unit_fails_replay(self):
        s=fixture();s['measure']['unitName']='cm'
        with self.assertRaises(ValueError):m.clean(s)
    def test_small_series_blocked(self):
        with self.assertRaises(ValueError):m.fit(m.clean(fixture(100))[0])
    def test_heldout_changes_cannot_change_model_or_thresholds(self):
        r=m.clean(fixture())[0];a,artifact,_=m.fit(r);changed=list(r)
        for i in range(195,len(changed)):changed[i]=(changed[i][0],changed[i][1]+10)
        b,other,_=m.fit(changed);self.assertEqual(artifact,other);self.assertNotEqual(a['ridge_mae_m'],b['ridge_mae_m'])
    def test_chronology_and_one_step_origin(self):
        metrics,artifact,rows=m.fit(m.clean(fixture())[0]);self.assertLessEqual(m.stamp(metrics['training_last_target']),m.stamp(metrics['calibration_first_origin']));self.assertLessEqual(m.stamp(metrics['calibration_last_target']),m.stamp(metrics['heldout_first_origin']))
        for r in rows:self.assertEqual(m.stamp(r['target_utc'])-m.stamp(r['origin_utc']),timedelta(minutes=15))
    def test_constant_series_has_zero_persistence_error(self):
        s=fixture()
        for r in s['readings']:r['value']=1.
        a,model,rows=m.fit(m.clean(s)[0]);self.assertEqual(a['persistence_mae_m'],0);self.assertEqual(a['baseline_test_flags'],0);self.assertGreater(model['residual_training_mad_scale_floor_1mm'],0)
    def test_export_is_finite_and_stale_is_visible(self):
        with tempfile.TemporaryDirectory() as d:
            result=m.run(fixture(),d);self.assertIn('STALE',result['freshness_status']);self.assertTrue((Path(d)/'report.html').exists());self.assertEqual(json.loads((Path(d)/'model.json').read_text())['ridge_alpha'],1.)

if __name__=='__main__':unittest.main()
