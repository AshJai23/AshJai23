"""Synthetic fixtures test behaviour only; measured benchmark uses attributed ECB data."""
from datetime import date,timedelta
import math
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from smartinvest.api import app
from smartinvest.market import analyse_prices, parse_prices, forecast_series, _fit, _features

def fixture(n=300):
    return ('date,symbol,price,currency\n'+''.join(f'{date(2020,1,1)+timedelta(days=i)},TEST,{100+math.sin(i/10)},GBP\n' for i in range(n))).encode()

def test_purged_temporal_splits_and_train_only_fit():
    r=analyse_prices(fixture(),5)['assets'][0]['forecast']
    assert r['train_last_target']<r['calibration_first_origin']
    assert r['calibration_last_target']<r['test_first_origin']
    d,p=parse_prices(fixture()); prices=list(d['TEST'].values())
    model=_fit([_features(prices,i) for i in range(20,175)], [math.log(prices[i+5]/prices[i]) for i in range(20,175)])
    assert r['parameters']['means']==pytest.approx(model['means'])
    assert len(r['held_out_predictions'])==55

@pytest.mark.parametrize('horizon',[1,5,20])
def test_constant_price_baseline(horizon):
    dates=[date(2020,1,1)+timedelta(days=i) for i in range(300)]
    f=forecast_series(dates,[100.]*300,horizon)
    assert f['projection']==100
    assert f['ridge_mae']==f['persistence_mae']==0
    assert not f['model_beat_baseline']

@pytest.mark.parametrize('bad',[
 b'date,symbol,price,currency\n2020-01-01,A,nan,GBP',
 b'date,symbol,price,currency\n2020-01-01,A,-1,GBP',
 b'date,symbol,price,currency\n2099-01-01,A,1,GBP',
 b'date,symbol,price,currency\n2020-01-01,A,1,GBP\n2020-01-01,A,2,GBP',
 b'date,symbol,price,currency\n2020-01-01,A,1,GBP\n2020-01-02,A,2,USD',
 b'date,symbol,price,currency\n2020-01-01,<script>,1,GBP',
 b'date,symbol,price,currency\n2020-01-01,A,1,GBP,extra', b'\xff', b'', b'\x00',
])
def test_invalid_prices(bad):
    with pytest.raises(ValueError): parse_prices(bad)

@pytest.mark.parametrize('horizon',[0,True,7,'5'])
def test_invalid_horizon(horizon):
    with pytest.raises(ValueError): analyse_prices(fixture(),horizon)

def test_insufficient_history():
    with pytest.raises(ValueError): analyse_prices(fixture(100))

def test_stale_flag_and_common_dates():
    r=analyse_prices(fixture(),as_of=date(2026,11,1))
    assert r['stale_after_7_calendar_days']
    assert r['mode']=='price_history_research_not_recommendations'

def test_api_market_and_private_error():
    c=TestClient(app)
    r=c.post('/v1/market-research',json={'csv_text':fixture().decode(),'horizon':5})
    assert r.status_code==200 and r.json()['assets'][0]['forecast']['test_rows']==55
    r=c.post('/v1/market-research',json={'csv_text':'secret-personal-content','horizon':4})
    assert r.status_code==422 and 'secret-personal-content' not in r.text

def test_attributed_real_snapshot():
    root=Path(__file__).resolve().parents[1]
    r=analyse_prices((root/'examples/market/ecb-fx-gbp.csv').read_bytes())
    assert len(r['assets'])==3
    assert all(a['observations']>=1751 for a in r['assets'])
