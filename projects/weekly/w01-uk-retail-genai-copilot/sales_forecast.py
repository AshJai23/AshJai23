"""Daily retail decision support: fitted causal Ridge versus last-week baseline.

Input is aggregate completed-day sales, not private customer records. This module
has no causal promotion model and makes no promise of commercial improvement.
"""
import csv
from datetime import date,timedelta
import io
import math
import statistics
import numpy as np

MAX_BYTES=2*1024*1024
MIN_DAYS=196

def parse_daily(data,as_of=None):
    as_of=as_of or date.today()
    if not isinstance(data,bytes) or not data or len(data)>MAX_BYTES:raise ValueError('Upload a non-empty UTF-8 CSV up to 2 MiB')
    try:
        reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig')),strict=True)
        if reader.fieldnames!=['date','sales']:raise ValueError('CSV columns must be exactly date,sales')
        rows={}
        for row in reader:
            if len(rows)>=5000:raise ValueError('Use at most 5,000 daily rows')
            if None in row or any(v is None for v in row.values()):raise ValueError('Malformed CSV row')
            try:day=date.fromisoformat(row['date']);value=float(row['sales'])
            except (ValueError,TypeError) as exc:raise ValueError('Use valid ISO dates and numeric daily sales') from exc
            if day.isoformat()!=row['date'] or day>=as_of:raise ValueError('Use YYYY-MM-DD dates for completed days before today')
            if day in rows:raise ValueError('Duplicate dates are not allowed')
            if not math.isfinite(value) or not 0<=value<=1e10:raise ValueError('Sales must be finite, non-negative amounts up to 10 billion')
            rows[day]=value
    except (UnicodeDecodeError,csv.Error) as exc:raise ValueError('CSV must be well-formed UTF-8') from exc
    if len(rows)<MIN_DAYS:raise ValueError('Provide at least 196 consecutive completed days (about 7 months) for train/calibration/test checks')
    dates=sorted(rows)
    if any(b-a!=timedelta(days=1) for a,b in zip(dates,dates[1:])):raise ValueError('Dates must be consecutive. Enter an explicit 0 only for a day you know had zero sales; do not fill unknown days with invented zeros.')
    return dates,[rows[d] for d in dates]

def features(days,values,i):
    prior=np.log1p(np.asarray(values[:i],dtype=float))
    return [float(days[i].weekday()==j) for j in range(7)]+[prior[-7],prior[-14],float(prior[-7:].mean()),float(prior[-28:].mean())]

def fit(days,values):
    x=np.asarray([features(days,values,i) for i in range(28,len(values))]);y=np.log1p(values[28:])
    means=x.mean(0);scales=x.std(0);scales[scales==0]=1;z=(x-means)/scales;intercept=float(y.mean())
    coefficients=np.linalg.solve(z.T@z+10*np.eye(x.shape[1]),z.T@(y-intercept))
    return {'means':means.tolist(),'scales':scales.tolist(),'coefficients':coefficients.tolist(),'intercept':intercept,'alpha':10,'training_rows':len(y)}

def predict_week(model,dates,values,start):
    # Features for later days use earlier predictions, never future actuals.
    history=list(values[:start]);days=list(dates[:start]);result=[]
    for offset in range(7):
        days.append(days[-1]+timedelta(days=1));x=np.asarray(features(days,history,len(history)))
        log_value=model['intercept']+float(np.dot((x-model['means'])/model['scales'],model['coefficients']))
        if not math.isfinite(log_value) or log_value>math.log1p(1e12):raise ValueError('Unstable forecast; no prediction returned')
        value=max(0.,math.expm1(log_value));history.append(value);result.append(value)
    return result

def score(actual,predicted):
    errors=[abs(a-p) for a,p in zip(actual,predicted)];total=sum(actual)
    return {'mae':statistics.mean(errors),'wape_pct':100*sum(errors)/total if total else None}

def analyse_daily(data,as_of=None):
    as_of=as_of or date.today();dates,values=parse_daily(data,as_of);n=len(values)
    train_end=n-84;test_start=n-56;model=fit(dates[:train_end],values[:train_end]);records=[]
    for split,start,end in [('calibration',train_end,test_start),('test',test_start,n)]:
        for origin in range(start,end,7):
            ridge=predict_week(model,dates,values,origin);baseline=values[origin-7:origin]
            for k in range(7):records.append({'split':split,'origin_date':dates[origin-1].isoformat(),'date':dates[origin+k].isoformat(),'actual':values[origin+k],'ridge':ridge[k],'last_week':baseline[k]})
    cal=[r for r in records if r['split']=='calibration'];test=[r for r in records if r['split']=='test']
    cal_scores={key:score([r['actual'] for r in cal],[r[key] for r in cal]) for key in ('ridge','last_week')}
    selected='ridge' if cal_scores['ridge']['mae']<cal_scores['last_week']['mae'] else 'last_week'
    test_scores={key:score([r['actual'] for r in test],[r[key] for r in test]) for key in ('ridge','last_week')}
    # Select on calibration only; hold-out test never selects the displayed model.
    residuals=sorted(abs(r['actual']-r[selected]) for r in cal);q=residuals[min(len(residuals)-1,math.ceil(.9*(len(residuals)+1))-1)]
    coverage=statistics.mean(abs(r['actual']-r[selected])<=q for r in test)
    # Refit the selected Ridge method on all known history only after evaluation.
    final_model=fit(dates,values) if selected=='ridge' else None
    predictions=predict_week(final_model,dates,values,n) if selected=='ridge' else values[-7:]
    forecast=[{'date':(dates[-1]+timedelta(days=k+1)).isoformat(),'weekday':(dates[-1]+timedelta(days=k+1)).strftime('%A'),'predicted_sales':v,'band_low':max(0.,v-q),'band_high':v+q} for k,v in enumerate(predictions)]
    weakest=min(forecast,key=lambda row:row['predicted_sales'])
    weekdays=[{'weekday':(date(2024,1,1)+timedelta(days=j)).strftime('%A'),'mean_last_8_weeks':statistics.mean(v for d,v in zip(dates[-56:],values[-56:]) if d.weekday()==j)} for j in range(7)]
    wtd=dates[-1].weekday()+1;current=sum(values[-wtd:]);previous=sum(values[-wtd-7:-7])
    age=(as_of-dates[-1]).days;stale=age>14
    return {'mode':'historical_simulation' if stale else ('current_history_forecast' if age==1 else 'recent_history_replay'),'complete_through_yesterday':age==1,'last_completed_date':dates[-1].isoformat(),'history_days':n,'observation_age_days':age,'stale_history':stale,
        'selected_method':selected,'selection_basis':'28 calibration days only; test results did not select the method','calibration_scores':cal_scores,'test_scores':test_scores,'selected_test_score':test_scores[selected],
        'training':{'initial_last_date':dates[train_end-1].isoformat(),'initial_rows':model['training_rows'],'calibration_days':28,'test_days':56,'test_first_date':dates[test_start].isoformat(),'causal_features':'weekday indicators, log lag 7/14, log rolling means 7/28; recursive weekly projection','final_refit_on_all_known_history':selected=='ridge','initial_model':model,'final_model':final_model},
        'forecast':forecast,'weakest_predicted_day':weakest,'weekday_history':weekdays,'week_to_date':{'reported_days':wtd,'sales':current,'same_days_previous_week_sales':previous,'change_pct':100*(current/previous-1) if previous else None},
        'uncertainty':{'method':'90th-percentile absolute calibration residual band; empirical, no guaranteed future coverage','test_coverage':coverage,'calibration_samples':len(cal)},'backtest_predictions':records,
        'action_ideas':[{'idea':'Check opening hours, footfall, stock availability and past promotions for the predicted weak day.','why':'The sales series alone cannot identify the cause.'},{'idea':'Test a small, margin-checked offer or local promotion on that weekday.','why':'Compare with similar untreated days or stores; no sales lift has been estimated.'},{'idea':'Review staffing and replenishment plans against the uncertainty range.','why':'A forecast is an estimate; confirm service levels and supplier constraints before changing operations.'}],
        'limitations':['Uploaded sales definition, currency and completeness are user-supplied and unverified.','Weak-day ranking may be unreliable when uncertainty bands overlap; calibration errors come from an earlier fit and may change after final refitting.','No weather, public holidays, advertising, stockouts, costs or promotion effects are included.','Action ideas are hypotheses to test; no causal improvement, profit or ROI is predicted.','Historical replay dates remain in the past; recent store data is required for a current operational forecast.']}
