"""Synthetic daily fixtures test forecasting boundaries; real-source validation is separate."""
from datetime import date,timedelta
import unittest
from fastapi.testclient import TestClient
from api import create_app
from sales_forecast import analyse_daily,parse_daily,fit,predict_week

def fixture(n=364):
    days=[date(2024,1,1)+timedelta(days=i) for i in range(n)]
    values=[100-10*d.weekday() for d in days]
    text='date,sales\n'+''.join(f'{d},{v}\n' for d,v in zip(days,values))
    return text.encode(),days,values

class Forecast(unittest.TestCase):
    def test_constant_zero_and_baseline(self):
        raw,days,values=fixture()
        raw=('date,sales\n'+''.join(f'{d},0\n' for d in days)).encode()
        r=analyse_daily(raw,date(2025,1,1))
        self.assertEqual(r['selected_method'],'last_week')
        self.assertEqual(r['selected_test_score']['mae'],0)
        self.assertIsNone(r['selected_test_score']['wape_pct'])
        self.assertTrue(all(row['predicted_sales']==0 for row in r['forecast']))
    def test_seasonality_weak_day_and_current_dates(self):
        raw,days,values=fixture();r=analyse_daily(raw,days[-1]+timedelta(days=1))
        self.assertEqual(r['weakest_predicted_day']['weekday'],'Sunday')
        self.assertEqual(r['mode'],'current_history_forecast')
        self.assertEqual(len(r['forecast']),7)
        self.assertEqual(r['test_scores']['last_week']['mae'],0)
        self.assertEqual(r['training']['test_days'],56)
        self.assertLess(r['training']['initial_last_date'],r['training']['test_first_date'])
    def test_week_projection_never_reads_future_actuals(self):
        _,days,values=fixture();origin=len(values)-56;model=fit(days[:origin-28],values[:origin-28])
        before=predict_week(model,days,values,origin)
        changed=list(values);changed[origin:origin+7]=[999999]*7
        self.assertEqual(before,predict_week(model,days,changed,origin))
    def test_recent_gap_is_not_labelled_current(self):
        raw,days,_=fixture();r=analyse_daily(raw,days[-1]+timedelta(days=4))
        self.assertFalse(r['complete_through_yesterday']);self.assertEqual(r['mode'],'recent_history_replay')
        self.assertEqual(analyse_daily(raw,date(2026,11,4))['mode'],'historical_simulation')
    def test_bad_csv_dates_values_and_gaps(self):
        raw,days,_=fixture()
        bad=[b'',b'date,sales\n2024-01-01,nan\n',b'date,sales\n2024-01-01,-1\n',b'date,sales\n2099-01-01,1\n',raw+f'{days[-1]},1\n'.encode(),raw.replace(b'2024-01-02,90\n',b''),raw.replace(b'date,sales',b'date,revenue')]
        for text in bad:
            with self.assertRaises(ValueError):parse_daily(text,date(2026,11,4))
    def test_forecast_endpoint_independent_of_optional_warehouse(self):
        def missing(**kwargs):raise FileNotFoundError('fixture unavailable SQL data')
        with TestClient(create_app(loader=missing)) as c:
            self.assertEqual(c.get('/v1/health').status_code,503)
            r=c.post('/v1/retail-forecast',json={'csv_text':fixture()[0].decode(),'currency':'GBP'})
            self.assertEqual(r.status_code,200);self.assertEqual(len(r.json()['forecast']),7)
            error=c.post('/v1/retail-forecast',json={'csv_text':'PRIVATE','currency':'BAD'})
            self.assertEqual(error.status_code,422);self.assertNotIn('PRIVATE',error.text)
if __name__=='__main__':unittest.main(verbosity=2)
