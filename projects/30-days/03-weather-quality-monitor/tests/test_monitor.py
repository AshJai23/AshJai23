from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from main import audit, parse_stations, parse_time, render, write_outputs

NOW = datetime(2026, 10, 25, 9, 15, tzinfo=timezone.utc)


def record(**updates):
    row = {"icaoId": "EGLL", "obsTime": datetime(2026,10,25,9,tzinfo=timezone.utc).timestamp(),
           "temp": 12, "dewp": 10, "wspd": 8, "altim": 1012, "wdir": 240, "lat": 51.5, "lon": -.4}
    row.update(updates)
    return row


class MonitorTests(unittest.TestCase):
    def check(self, records, stations=None):
        return audit(records, stations or ["EGLL"], NOW)

    def test_real_observation_age_is_used_not_receipt_time(self):
        r = self.check([record(obsTime=NOW.timestamp()-120*60, receiptTime=NOW.isoformat())])
        self.assertEqual(r['stations'][0]['age_minutes'], 120)
        self.assertIn('stale_observation',r['stations'][0]['issues'])

    def test_missing_station_is_not_silently_ignored(self):
        r=self.check([record()],['EGLL','VIDP'])
        self.assertEqual(r['station_status_counts'],{'PASS':1,'WARN':0,'FAIL':1})
        self.assertEqual(r['stations'][1]['issues'],['missing_station'])

    def test_optional_gust_and_variable_or_calm_wind_are_valid(self):
        for direction,speed in [('VRB',3),(0,0)]:
            r=self.check([record(wdir=direction,wspd=speed)])
            self.assertEqual(r['stations'][0]['status'],'PASS')
            self.assertIsNone(r['stations'][0]['wgst'])

    def test_latest_bad_record_does_not_fall_back_to_older_good_record(self):
        old=record(obsTime=NOW.timestamp()-3600)
        new=record(temp=999)
        r=self.check([new,old])
        self.assertEqual(r['stations'][0]['status'],'FAIL')
        self.assertIn('invalid_temp',r['stations'][0]['issues'])

    def test_malformed_timestamp_is_quarantined_and_visible(self):
        r=self.check([record(obsTime='not-a-time')])
        self.assertEqual(r['quality']['rejected_timestamp_or_structure_records'],1)
        self.assertEqual(r['stations'][0]['status'],'FAIL')

    def test_future_timestamp_fails(self):
        r=self.check([record(obsTime=NOW.timestamp()+600)])
        self.assertIn('future_observation',r['stations'][0]['issues'])

    def test_nan_boolean_and_missing_core_field_are_distinguished(self):
        for value in [float('nan'),True]:
            self.assertIn('invalid_temp',self.check([record(temp=value)])['stations'][0]['issues'])
        missing=self.check([record(temp=None)])
        self.assertEqual(missing['stations'][0]['status'],'WARN')
        self.assertIn('missing_temp',missing['stations'][0]['issues'])

    def test_physical_relationship_checks(self):
        r=self.check([record(dewp=17,wgst=2)])
        self.assertIn('dewpoint_exceeds_temperature',r['stations'][0]['issues'])
        self.assertIn('gust_below_sustained_wind',r['stations'][0]['issues'])

    def test_duplicates_conflicts_and_history_are_different(self):
        r=self.check([record(),record(),record(temp=13),record(obsTime=NOW.timestamp()-3600)])
        self.assertEqual(r['quality']['duplicate_records'],2)
        self.assertEqual(r['quality']['unique_usable_timestamp_records'],2)
        self.assertIn('conflicting_duplicate',r['stations'][0]['issues'])

    def test_empty_valid_response_fails_all_expected_stations(self):
        self.assertEqual(self.check([])['station_status_counts']['FAIL'],1)
        with self.assertRaises(ValueError):self.check({'error':'source failure'})

    def test_input_timestamp_and_station_validation(self):
        with self.assertRaises(ValueError):parse_time('2026-10-25T09:00:00')
        with self.assertRaises(ValueError):parse_stations('EGLL;bad')
        self.assertEqual(parse_stations('egll,EGLL,VIDP'),['EGLL','VIDP'])

    def test_html_escapes_external_strings_and_exports_no_nan(self):
        r=self.check([record()]);r.update(mode='<script>bad</script>',source='fixture')
        self.assertIn('&lt;script&gt;',render(r));self.assertNotIn('<script>',render(r))
        with tempfile.TemporaryDirectory() as directory:
            write_outputs(r,Path(directory))
            saved=json.loads((Path(directory)/'quality.json').read_text())
            self.assertEqual(saved['station_status_counts']['PASS'],1)


if __name__=='__main__':unittest.main()
