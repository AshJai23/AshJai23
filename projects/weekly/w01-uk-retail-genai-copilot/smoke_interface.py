"""Labelled synthetic forecast and attributed historical replay through HTTP handlers."""
from datetime import date
import json
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from api import create_app
import sales_forecast

def unavailable(**_):raise FileNotFoundError('Optional warehouse unavailable for interface smoke')
root=Path(__file__).resolve().parent
with TestClient(create_app(loader=unavailable)) as client:
    checks={}
    for path,mime in [('/','text/html'),('/assets/app.js','text/javascript'),('/assets/styles.css','text/css')]:
        response=client.get(path)
        checks[path]={'status':response.status_code,'content_type':response.headers['content-type'],'bytes':len(response.content),'unicode_clean':'Â' not in response.text and 'â€' not in response.text}
        assert response.status_code==200 and mime in response.headers['content-type'] and checks[path]['unicode_clean']
    assert client.get('/v1/health').status_code==503
    original=sales_forecast.analyse_daily
    fixture=(root/'evidence/2026-11-04/interface-synthetic-fixture.csv').read_text(encoding='utf-8')
    # Fixed date keeps this recorded synthetic fixture reproducible on later runs.
    with patch('api.analyse_daily',lambda data:original(data,as_of=date(2026,11,4))):
        response=client.post('/v1/retail-forecast',json={'csv_text':fixture,'currency':'GBP'})
    assert response.status_code==200,response.text
    result=response.json()
    assert result['complete_through_yesterday'] and len(result['forecast'])==7
    synthetic={'label':'Synthetic fixture only; not actual shop/model-performance evidence','days':365,'forecast_dates':[d['date'] for d in result['forecast']],'weakest_day':result['weakest_predicted_day']['weekday'],'selected_method':result['selected_method']}
    historical=client.post('/v1/retail-forecast',json={'csv_text':(root/'examples/historical-daily-sales-proxy.csv').read_text(encoding='utf-8'),'currency':'GBP'})
    assert historical.status_code==200 and historical.json()['stale_history']
    result=historical.json()
    report={'date':'2026-11-04','passed':True,'transport':'FastAPI TestClient ASGI requests; not deployed or graphical browser','assets':checks,'forecast_works_without_optional_warehouse':True,'synthetic':synthetic,'historical_replay':{'source':'Chen / UCI Online Retail II, CC BY 4.0; previously attributed aggregate fixture','fresh_source_download':False,'mode':'historical_simulation','last_completed_date':result['last_completed_date'],'test_scores':result['test_scores']},'native_windows_run':False,'browser_review':False}
    (root/'evidence/2026-11-04/interface-http-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'synthetic_weak_day':synthetic['weakest_day'],'asset_count':len(checks),'historical_replay':True}))
