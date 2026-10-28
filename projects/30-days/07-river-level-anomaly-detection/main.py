"""Causal river innovation scoring with a trained Ridge and persistence baseline."""
import argparse,csv,hashlib,html,json,math,os,time,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
os.environ.setdefault('OMP_NUM_THREADS','2')
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

STATION='1491TH'
MEASURE='1491TH-level-stage-i-15_min-mASD'
ROOT='https://environment.data.gov.uk/flood-monitoring'

def stamp(s):
    d=datetime.fromisoformat(s.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('Timezone required')
    return d.astimezone(timezone.utc)
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AshJai23-river-portfolio/1.0'}),timeout=30) as r:
        b=r.read(2000001)
        if len(b)>2000000:raise ValueError('Response too large')
        return json.loads(b),{'url':url,'status':r.status,'raw_sha256':hashlib.sha256(b).hexdigest()}
def collect():
    station,sp=fetch(f'{ROOT}/id/stations/{STATION}')
    metadata=station['items'];measure=next(m for m in metadata['measures'] if m.get('notation')==MEASURE)
    if measure.get('period')!=900 or measure.get('parameter')!='level' or measure.get('unitName')!='mASD' or measure.get('qualifier')!='Stage':raise ValueError('Unexpected station measure/unit/datum')
    data,rp=fetch(f'{ROOT}/id/measures/{MEASURE}/readings?_sorted&_limit=1500')
    if len(data['items'])>=1500:truncated=True
    else:truncated=False
    return {'captured_at_utc':datetime.now(timezone.utc).isoformat(),'station':{'id':STATION,'name':metadata['label'],'river':metadata.get('riverName'),'latitude':metadata.get('lat'),'longitude':metadata.get('long')},'measure':{k:measure[k] for k in ['@id','notation','parameter','period','qualifier','unitName']},'readings':data['items'],'requests':[sp,rp],'limit_reached':truncated,'mode':'Real-source recent-history download; observation freshness determined from readings, not request time'}
def clean(s):
    m=s['measure']
    if m.get('notation')!=MEASURE or m.get('period')!=900 or m.get('unitName')!='mASD' or m.get('qualifier')!='Stage':raise ValueError('Unexpected measure identity, cadence or unit')
    seen={};q={'input_rows':len(s['readings']),'duplicates':0,'invalid':0,'future':0,'wrong_measure':0}
    cutoff=stamp(s['captured_at_utc'])
    for r in s['readings']:
        try:
            t=stamp(r['dateTime']);v=r['value']
            if r.get('measure','').rstrip('/').split('/')[-1]!=MEASURE:q['wrong_measure']+=1;continue
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError('Nonfinite value')
            if t.minute%15 or t.second:raise ValueError('Unaligned time')
            if t>cutoff:q['future']+=1;continue
            # Local datum heights can legitimately be negative. No invented universal height range.
            if t in seen:
                if seen[t]!=float(v):raise RuntimeError('Conflicting duplicate at '+t.isoformat())
                q['duplicates']+=1
            seen[t]=float(v)
        except (ValueError,KeyError,TypeError,AttributeError):q['invalid']+=1
    rows=sorted(seen.items())
    if not rows:raise ValueError('No valid readings')
    q['missing_15min_slots']=int((rows[-1][0]-rows[0][0]).total_seconds()/900)+1-len(rows)
    return rows,q
def windows(rows):
    X=[];Y=[];times=[];past=[];origins=[]
    for i in range(4,len(rows)):
        chunk=rows[i-4:i+1]
        if any(chunk[j+1][0]-chunk[j][0]!=timedelta(minutes=15) for j in range(4)):continue
        v=[x[1] for x in chunk[:4]]
        X.append([v[-1],v[-2],v[0],v[-1]-v[-2],float(np.mean(v))]);Y.append(chunk[-1][1]);past.append(v[-1]);times.append(chunk[-1][0]);origins.append(chunk[-2][0])
    return np.asarray(X),np.asarray(Y),times,np.asarray(past),origins
def split_sizes(n):
    a=int(n*.6);b=int(n*.8)
    if min(a,b-a,n-b)<30:raise ValueError('Need at least 150 complete windows for train/calibration/test')
    return a,b
def fit(rows):
    X,y,t,past,origins=windows(rows);a,b=split_sizes(len(y));started=time.perf_counter()
    scaler=StandardScaler().fit(X[:a]);model=Ridge(alpha=1.0).fit(scaler.transform(X[:a]),y[:a]);elapsed=time.perf_counter()-started;pred=model.predict(scaler.transform(X))
    # Both thresholds use calibration only, not the held-out test period.
    def detector(residual):
        center=float(np.median(residual[:a]));scale=max(float(np.median(np.abs(residual[:a]-center)))*1.4826,.001)
        score=np.abs(residual-center)/scale
        threshold=max(3.0,float(np.quantile(score[a:b],.99)))
        return score,threshold,center,scale
    score,threshold,center,scale=detector(y-pred);bs,bt,bc,bscale=detector(y-past)
    test=slice(b,None)
    mae=float(np.mean(np.abs(y[test]-pred[test])));baseline=float(np.mean(np.abs(y[test]-past[test])))
    result={'complete_windows':len(y),'training_rows':a,'calibration_rows':b-a,'heldout_rows':len(y)-b,'training_first_target':t[0].isoformat(),'training_last_target':t[a-1].isoformat(),'calibration_first_origin':origins[a].isoformat(),'calibration_last_target':t[b-1].isoformat(),'heldout_first_origin':origins[b].isoformat(),'heldout_first_target':t[b].isoformat(),'heldout_last_target':t[-1].isoformat(),'ridge_mae_m':mae,'persistence_mae_m':baseline,'ridge_beats_persistence':mae<baseline,'ridge_rmse_m':float(np.sqrt(np.mean((y[test]-pred[test])**2))),'persistence_rmse_m':float(np.sqrt(np.mean((y[test]-past[test])**2))),'ridge_test_flags':int(sum(score[test]>threshold)),'baseline_test_flags':int(sum(bs[test]>bt)),'overlap_flags':int(sum((score[test]>threshold)&(bs[test]>bt))),'fit_seconds':elapsed,'labels':'No verified anomalies/flood labels: flags are not true positives and precision/recall cannot be measured.'}
    artifact={'features':['previous_level','lag2_level','lag4_level','last_change','previous4_mean'],'ridge_alpha':1.0,'scaler_mean':scaler.mean_.tolist(),'scaler_scale':scaler.scale_.tolist(),'ridge_coef':model.coef_.tolist(),'ridge_intercept':float(model.intercept_),'residual_training_median':center,'residual_training_mad_scale_floor_1mm':scale,'calibration_99pct_score_threshold_min3':threshold,'baseline_residual_median':bc,'baseline_mad_scale':bscale,'baseline_calibration_threshold':bt}
    records=[]
    for i in range(len(y)):
        records.append({'target_utc':t[i].isoformat(),'origin_utc':origins[i].isoformat(),'split':'train' if i<a else 'calibration' if i<b else 'test','observed_m':float(y[i]),'ridge_prediction_m':float(pred[i]),'persistence_m':float(past[i]),'ridge_absolute_error_m':float(abs(y[i]-pred[i])),'ridge_robust_score':float(score[i]),'ridge_flag':bool(score[i]>threshold),'baseline_score':float(bs[i]),'baseline_flag':bool(bs[i]>bt)})
    return result,artifact,records

def run(s,out):
    rows,q=clean(s);metrics,artifact,records=fit(rows);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    age=(stamp(s['captured_at_utc'])-rows[-1][0]).total_seconds()/3600
    metrics.update({'data_mode':'Historical replay/backtest of actually downloaded EA observations; no real-time warning service','captured_at_utc':s['captured_at_utc'],'station':s['station'],'units':'metres above station datum (mASD); not sea-level elevation','quality':q,'latest_observation_utc':rows[-1][0].isoformat(),'observation_age_hours_at_capture':age,'freshness_status':'STALE over 24 hours' if age>24 else 'Within 24 hours; may still be delayed','source_snapshot_sha256':hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()})
    for name,value in [('metrics.json',metrics),('model.json',artifact)]:
        (out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    with (out/'scored_observations.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
    inspected=sorted([r for r in records if r['split']=='test'],key=lambda x:x['ridge_robust_score'],reverse=True)[:8]
    inspection={'review_type':'AI-assisted numerical inspection; not human/domain-verified anomaly labels','selection':'Eight largest held-out robust innovation scores, selected after evaluation for descriptive inspection only. No tuning on these cases.','cases':inspected,'interpretation':'Large innovation may reflect real hydrological change, sensor issues, datum problems or normal dynamics. This snapshot cannot distinguish these. Small scores do not establish safety.'}
    (out/'inspection.json').write_text(json.dumps(inspection,indent=2)+'\n')
    (out/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>River innovation audit</title><style>body{font:16px system-ui;max-width:1000px;margin:30px auto;background:#112535;color:#ecf3f9}pre{white-space:pre-wrap}</style><h1>Kings Mill river innovation audit</h1><p>Historical prototype: no verified anomaly labels, no flood warning or safety use. Source age is explicit.</p><pre>'+html.escape(json.dumps(metrics,indent=2))+'</pre><h2>Inspected held-out cases</h2><pre>'+html.escape(json.dumps(inspection,indent=2))+'</pre></html>')
    return metrics

def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--input',default='examples/source_snapshot.json');p.add_argument('--output',default='outputs');a=p.parse_args()
    s=collect() if a.live else json.loads(Path(a.input).read_text());metrics=run(s,a.output)
    if a.live:(Path(a.output)/'source_snapshot.json').write_text(json.dumps(s,indent=2)+'\n')
    print(json.dumps(metrics,indent=2))
if __name__=='__main__':main()
