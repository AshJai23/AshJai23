"""Synthetic edge-case fixtures; published model/metrics use actual ERA5 capture."""
import copy,json,math,tempfile,unittest
from datetime import date,datetime,timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
import numpy as np
import torch
import main as m

def fixture():
    start=int(datetime(2026,4,1,tzinfo=timezone.utc).timestamp());n=720
    data={'time':[start+i*3600 for i in range(n)],'temperature_2m':[15+5*math.sin(2*math.pi*i/24) for i in range(n)],'relative_humidity_2m':[65+10*math.cos(i/24) for i in range(n)],'wind_speed_10m':[3+math.sin(i/48) for i in range(n)],'surface_pressure':[1010+5*math.sin(i/200) for i in range(n)]}
    return {'captured_at_utc':'2026-05-10T00:00:00Z','request_parameters':{'start_date':'2026-04-01','end_date':'2026-04-30','models':'era5'},'mode':'SYNTHETIC TEST ONLY','response':{'latitude':51.5,'longitude':-.25,'utc_offset_seconds':0,'hourly_units':dict(zip(['time']+m.VARS,['unixtime']+m.UNITS)),'hourly':data}}

class DataTests(unittest.TestCase):
    def test_units_are_not_silently_converted(self):
        s=fixture();s['response']['hourly_units']['wind_speed_10m']='km/h'
        with self.assertRaises(ValueError):m.clean(s)
    def test_unequal_response_columns_fail(self):
        s=fixture();s['response']['hourly']['surface_pressure'].pop()
        with self.assertRaises(ValueError):m.clean(s)
    def test_exact_duplicates_collapse(self):
        s=fixture()
        for v in ['time']+m.VARS:s['response']['hourly'][v].append(s['response']['hourly'][v][0])
        rows,q=m.clean(s);self.assertEqual(len(rows),720);self.assertEqual(q['duplicates'],1)
    def test_conflicting_duplicate_fails(self):
        s=fixture()
        for v in ['time']+m.VARS:s['response']['hourly'][v].append(s['response']['hourly'][v][0])
        s['response']['hourly']['temperature_2m'][-1]=42
        with self.assertRaises(ValueError):m.clean(s)
    def test_missing_hour_breaks_25_row_windows(self):
        s=fixture();s['response']['hourly']['temperature_2m'][400]=None;d=m.prepare(s);self.assertEqual(sum(d['counts'].values()),671);self.assertEqual(d['quality']['missing_requested_hours'],1)
    def test_invalid_values_not_zero_filled(self):
        s=fixture();s['response']['hourly']['temperature_2m'][0]=float('nan');s['response']['hourly']['relative_humidity_2m'][1]=120;s['response']['hourly']['wind_speed_10m'][2]=-1
        rows,q=m.clean(s);self.assertEqual(q['invalid_or_missing_rows'],3)
    def test_temperature_zero_and_negative_are_valid(self):
        s=fixture();s['response']['hourly']['temperature_2m'][0]=0;s['response']['hourly']['temperature_2m'][1]=-5;rows,q=m.clean(s);self.assertEqual(q['invalid_or_missing_rows'],0)
    def test_misaligned_epochs_fail(self):
        s=fixture();s['response']['hourly']['time'][0]+=1
        with self.assertRaises(ValueError):m.clean(s)
    def test_grid_outside_london_fails(self):
        s=fixture();s['response']['latitude']=0
        with self.assertRaises(ValueError):m.clean(s)
    def test_future_holdout_values_do_not_change_scaler_or_splits(self):
        s=fixture();a=m.prepare(s);s['response']['hourly']['temperature_2m'][600:]=[40.]*120;b=m.prepare(s);np.testing.assert_array_equal(a['mean'],b['mean']);np.testing.assert_array_equal(a['scale'],b['scale']);np.testing.assert_array_equal(a['labels'],b['labels'])
    def test_target_not_in_its_input_sequence(self):
        s=fixture();a=m.prepare(s);k=int(np.where(a['labels']=='test')[0][0]);idx=(a['times'][k]-s['response']['hourly']['time'][0])//3600;s['response']['hourly']['temperature_2m'][idx]=40;b=m.prepare(s);np.testing.assert_array_equal(a['X'][k],b['X'][k]);self.assertNotEqual(a['y'][k],b['y'][k])
    def test_chronology_and_24_hour_context(self):
        d=m.prepare(fixture());self.assertEqual(d['X'].shape,(696,24,6));self.assertTrue(np.all(d['times'][d['labels']=='train']<d['train_end']));self.assertTrue(np.all(d['times'][d['labels']=='validation']>=d['train_end']));self.assertTrue(np.all(d['times'][d['labels']=='test']>=d['validation_end']))
    def test_source_failure_does_not_use_examples(self):
        with patch.object(m.urllib.request,'urlopen',side_effect=URLError('SYNTHETIC TEST OUTAGE')):
            with self.assertRaises(URLError):m.collect(date(2026,9,30),30)
    def test_recent_end_blocked_before_network(self):
        with patch.object(m.urllib.request,'urlopen') as network:
            with self.assertRaises(ValueError):m.collect(datetime.now(timezone.utc).date(),30)
            network.assert_not_called()

class NeuralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.source=fixture();cls.artifact,cls.curve=m.train(cls.source,max_epochs=3,patience=2)
    def test_neural_weights_really_changed(self):
        t=self.artifact['training'];self.assertTrue(t['weights_changed']);self.assertEqual(t['trainable_parameters'],1553);self.assertNotEqual(t['initial_parameter_sha256'],t['selected_parameter_sha256'])
    def test_epoch_selected_from_validation_only(self):
        best=min(self.curve,key=lambda r:r['validation_mae_c']);self.assertEqual(best['epoch'],self.artifact['training']['selected_epoch']);self.assertTrue(all('test' not in key for row in self.curve for key in row))
    def test_lstm_is_actual_trainable_recurrent_module(self):
        model=m.load_model(self.artifact);self.assertIsInstance(model.lstm,torch.nn.LSTM);self.assertEqual(tuple(model(torch.zeros(2,24,6)).shape),(2,))
    def test_json_roundtrip_preserves_exact_inference(self):
        a=m.load_model(self.artifact);b=m.load_model(json.loads(json.dumps(self.artifact)));x=torch.ones(3,24,6)
        with torch.inference_mode():torch.testing.assert_close(a(x),b(x),rtol=0,atol=0)
    def test_bad_weight_shapes_rejected(self):
        a=copy.deepcopy(self.artifact);a['state_dict']['head.bias']=[0,0]
        with self.assertRaises(ValueError):m.load_model(a)
    def test_changed_source_cannot_be_called_same_heldout_replay(self):
        s=copy.deepcopy(self.source);s['captured_at_utc']='2026-05-11T00:00:00Z'
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):m.evaluate(s,self.artifact,d)
    def test_tail_example_is_one_hour_after_source_not_current(self):
        r=m.tail_example(self.source,self.artifact);self.assertEqual(r['target_utc'],'2026-05-01T00:00:00+00:00');self.assertIsNone(r['target_actual_c']);self.assertIn('NOT a live forecast',r['mode'])
    def test_tail_missing_context_fails(self):
        s=copy.deepcopy(self.source);s['response']['hourly']['temperature_2m'][-2]=None
        with self.assertRaises(ValueError):m.tail_example(s,self.artifact)
    def test_replay_exports_real_predictions_for_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.evaluate(self.source,self.artifact,d);self.assertEqual(r['split_counts']['test'],144);self.assertEqual(set(r['heldout_metrics']),{'lstm','persistence','previous_day','ridge'});self.assertTrue((Path(d)/'test_predictions.csv').is_file());self.assertTrue(math.isfinite(r['heldout_metrics']['lstm']['mae_c']))

if __name__=='__main__':unittest.main()
