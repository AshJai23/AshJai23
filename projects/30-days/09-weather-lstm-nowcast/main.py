"""Small trained LSTM for retrospective London temperature extrapolation."""
import argparse,copy,csv,hashlib,html,json,math,os,time,urllib.parse,urllib.request
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('MKL_NUM_THREADS','2')
import numpy as np
import torch
from torch import nn
from sklearn.linear_model import Ridge

VARS=['temperature_2m','relative_humidity_2m','wind_speed_10m','surface_pressure']
UNITS=['°C','%','m/s','hPa']
FEATURES=VARS+['utc_hour_sin','utc_hour_cos']
LOOKBACK=24

def utc(t):return datetime.fromtimestamp(int(t),timezone.utc).isoformat()
def canonical_hash(s):return hashlib.sha256(json.dumps(s,sort_keys=True,allow_nan=False).encode()).hexdigest()
def collect(end=None,days=180):
    end=end or (datetime.now(timezone.utc).date()-timedelta(days=7))
    if not 30<=days<=366 or end>datetime.now(timezone.utc).date()-timedelta(days=7):raise ValueError('Require 30–366 historical days, ending at least 7 days ago')
    start=end-timedelta(days=days-1)
    params={'latitude':51.5074,'longitude':-.1278,'start_date':str(start),'end_date':str(end),'hourly':','.join(VARS),'models':'era5','timezone':'GMT','timeformat':'unixtime','wind_speed_unit':'ms'}
    url='https://archive-api.open-meteo.com/v1/archive?'+urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AshJai23-educational-weather-LSTM/1.0'}),timeout=40) as r:
        raw=r.read(2000001)
        if len(raw)>2000000:raise ValueError('Response too large')
        data=json.loads(raw)
        return {'captured_at_utc':datetime.now(timezone.utc).isoformat(),'request_url':url,'request_parameters':params,'http_status':r.status,'raw_response_sha256':hashlib.sha256(raw).hexdigest(),'mode':'Historical ERA5 reanalysis downloaded from a regularly refreshed public API; retrospective replay, not live observations or as-issued forecasts','response':data}
def bounds(s):
    p=s['request_parameters']
    a=int(datetime.combine(date.fromisoformat(p['start_date']),datetime.min.time(),timezone.utc).timestamp())
    z=int(datetime.combine(date.fromisoformat(p['end_date'])+timedelta(days=1),datetime.min.time(),timezone.utc).timestamp())
    if not 30*86400<=z-a<=366*86400:raise ValueError('Invalid requested historical window')
    n=(z-a)//3600
    return a,z,a+int(n*.6)*3600,a+int(n*.8)*3600

def clean(s):
    p=s['request_parameters'];d=s['response'];a,z,_,_=bounds(s)
    if p.get('models')!='era5' or d.get('utc_offset_seconds')!=0:raise ValueError('Expected explicit ERA5 with UTC times')
    if abs(float(d['latitude'])-51.5074)>.5 or abs(float(d['longitude'])+.1278)>.5:raise ValueError('Unexpected grid outside London area')
    if [d['hourly_units'].get(v) for v in VARS]!=UNITS or d['hourly_units'].get('time')!='unixtime':raise ValueError('Unexpected units')
    h=d['hourly'];n=len(h['time'])
    if any(len(h[v])!=n for v in VARS):raise ValueError('Unequal response columns')
    cap=datetime.fromisoformat(s['captured_at_utc'].replace('Z','+00:00'))
    if cap.tzinfo is None:raise ValueError('Capture timezone required')
    q={'input_rows':n,'duplicates':0,'invalid_or_missing_rows':0,'outside_window_or_future':0};seen={}
    limits=[(-100,70),(0,100),(0,100),(800,1100)]
    for i,t in enumerate(h['time']):
        if isinstance(t,bool) or not isinstance(t,int) or t%3600:raise ValueError('Expected aligned integer UTC epochs')
        if not a<=t<z or t>cap.timestamp():q['outside_window_or_future']+=1;continue
        values=[h[v][i] for v in VARS]
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi for v,(lo,hi) in zip(values,limits)):
            q['invalid_or_missing_rows']+=1;continue
        values=[float(x) for x in values]
        if t in seen:
            if seen[t]!=values:raise ValueError('Conflicting timestamp duplicate')
            q['duplicates']+=1
        seen[t]=values
    if not seen:raise ValueError('No usable records')
    q['missing_requested_hours']=(z-a)//3600-len(seen)
    return seen,q

def prepare(s):
    seen,q=clean(s);a,z,train_end,val_end=bounds(s)
    def feature(t):
        hour=(t//3600)%24;return seen[t]+[math.sin(2*math.pi*hour/24),math.cos(2*math.pi*hour/24)]
    # Unique hourly rows in the training period only, not repeated overlapping windows.
    raw=np.array([feature(t) for t in sorted(seen) if t<train_end],dtype=np.float64)
    if len(raw)<100:raise ValueError('Insufficient training weather')
    mean=raw.mean(axis=0);scale=np.maximum(raw.std(axis=0),1e-6)
    X=[];Y=[];last=[];seasonal=[];linear=[];times=[];labels=[]
    for target in sorted(seen):
        ts=[target-k*3600 for k in range(LOOKBACK,0,-1)]
        if not all(t in seen for t in ts):continue
        values=np.array([feature(t) for t in ts],dtype=np.float64)
        X.append(values);Y.append(seen[target][0]);last.append(values[-1,0]);seasonal.append(values[0,0]);times.append(target)
        # These features are all observed before target; target hour is not needed.
        linear.append(values[-1].tolist()+[values[-1,0]-values[-2,0],values[0,0]])
        labels.append('train' if target<train_end else 'validation' if target<val_end else 'test')
    labels=np.array(labels);counts={k:int(sum(labels==k)) for k in ['train','validation','test']}
    if min(counts.values())<30:raise ValueError('Insufficient complete windows in a chronological split')
    return {'X':np.array(X,dtype=np.float64),'y':np.array(Y),'last':np.array(last),'seasonal':np.array(seasonal),'linear':np.array(linear),'times':np.array(times),'labels':labels,'mean':mean,'scale':scale,'quality':q,'counts':counts,'train_end':train_end,'validation_end':val_end,'window_start':a,'window_end':z,'training_scaler_unique_hours':len(raw)}

class WeatherLSTM(nn.Module):
    def __init__(self):
        super().__init__();self.lstm=nn.LSTM(len(FEATURES),16,batch_first=True);self.head=nn.Linear(16,1)
    def forward(self,x):
        y,_=self.lstm(x);return self.head(y[:,-1]).squeeze(-1)

def configure(seed=42):
    torch.set_num_threads(2);torch.manual_seed(seed);np.random.seed(seed);torch.use_deterministic_algorithms(True)
    # Deterministic native CPU kernels; avoid platform-specific oneDNN choices.
    torch.backends.mkldnn.enabled=False

def state_digest(state):
    h=hashlib.sha256()
    for k,v in state.items():h.update(k.encode());h.update(v.detach().cpu().numpy().tobytes())
    return h.hexdigest()
def errors(y,p):return {'mae_c':float(np.mean(np.abs(y-p))),'rmse_c':float(np.sqrt(np.mean((y-p)**2)))}
def infer_model(model,x,delta_mean,delta_scale,last):
    model.eval();values=[]
    with torch.inference_mode():
        for chunk in torch.split(x,256):values.append(model(chunk).cpu().numpy())
    return last+delta_mean+delta_scale*np.concatenate(values)

def train(s,max_epochs=40,patience=6):
    configure();d=prepare(s);tr=d['labels']=='train';va=d['labels']=='validation';delta=d['y']-d['last']
    dm=float(delta[tr].mean());ds=max(float(delta[tr].std()),1e-6)
    x=torch.tensor((d['X']-d['mean'])/d['scale'],dtype=torch.float32);y=torch.tensor((delta-dm)/ds,dtype=torch.float32)
    model=WeatherLSTM();initial=state_digest(model.state_dict());optimizer=torch.optim.Adam(model.parameters(),lr=.003)
    train_ids=torch.tensor(np.where(tr)[0]);history=[];best=None;best_mae=float('inf');best_epoch=0
    started=time.perf_counter()
    for epoch in range(1,max_epochs+1):
        model.train();total=0.;n=0
        for ids in torch.split(train_ids[torch.randperm(len(train_ids))],256):
            optimizer.zero_grad();pred=model(x[ids]);loss=nn.functional.mse_loss(pred,y[ids]);loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.0);optimizer.step();total+=float(loss.detach())*len(ids);n+=len(ids)
        v=infer_model(model,x[va],dm,ds,d['last'][va]);mae=errors(d['y'][va],v)['mae_c']
        history.append({'epoch':epoch,'training_normalized_delta_mse':total/n,'validation_mae_c':mae})
        if mae<best_mae-1e-6:best_mae=mae;best=copy.deepcopy(model.state_dict());best_epoch=epoch
        if epoch-best_epoch>=patience:break
    seconds=time.perf_counter()-started
    if best is None:raise ValueError('Nonfinite training/validation result')
    model.load_state_dict(best)
    # Simple linear comparator fits the same training targets only.
    lm=d['linear'][tr].mean(axis=0);ls=np.maximum(d['linear'][tr].std(axis=0),1e-6)
    ridge=Ridge(alpha=1.0).fit((d['linear'][tr]-lm)/ls,delta[tr])
    artifact={'format_version':1,'architecture':'one-layer LSTM(6,16) + Linear(16,1), next-hour residual temperature','features':FEATURES,'lookback_hours':LOOKBACK,'hidden_size':16,'source_snapshot_sha256':canonical_hash(s),'source_window_start':utc(d['window_start']),'source_window_end_exclusive':utc(d['window_end']),'train_end_exclusive':utc(d['train_end']),'validation_end_exclusive':utc(d['validation_end']),'input_mean':d['mean'].tolist(),'input_scale':d['scale'].tolist(),'delta_mean':dm,'delta_scale':ds,'state_dict':{k:v.tolist() for k,v in best.items()},'ridge':{'mean':lm.tolist(),'scale':ls.tolist(),'coef':ridge.coef_.tolist(),'intercept':float(ridge.intercept_)},'training':{'seed':42,'max_epochs':max_epochs,'patience':patience,'epochs_run':len(history),'selected_epoch':best_epoch,'selection':'lowest validation MAE; no held-out test evaluation during selection','training_loop_seconds':seconds,'trainable_parameters':sum(p.numel() for p in model.parameters()),'initial_parameter_sha256':initial,'selected_parameter_sha256':state_digest(best),'weights_changed':initial!=state_digest(best),'torch_version':torch.__version__,'numpy_version':np.__version__,'device':'CPU','threads':2}}
    return artifact,history

def load_model(a):
    if a.get('format_version')!=1 or a.get('features')!=FEATURES or a.get('lookback_hours')!=24 or a.get('hidden_size')!=16:raise ValueError('Incompatible model artifact')
    model=WeatherLSTM();expected=model.state_dict();state={}
    if set(a['state_dict'])!=set(expected):raise ValueError('Wrong parameter keys')
    for k,v in expected.items():
        tensor=torch.tensor(a['state_dict'][k],dtype=torch.float32)
        if tensor.shape!=v.shape or not torch.isfinite(tensor).all():raise ValueError('Invalid parameter tensor')
        state[k]=tensor
    model.load_state_dict(state);model.eval();return model

def tail_example(s,a):
    """Extrapolate once after the last archived record; never label it current."""
    seen,_=clean(s);last=max(seen);ts=[last-k*3600 for k in range(23,-1,-1)]
    if not all(t in seen for t in ts):raise ValueError('Latest 24-hour context is incomplete')
    values=[]
    for t in ts:
        hour=(t//3600)%24;values.append(seen[t]+[math.sin(2*math.pi*hour/24),math.cos(2*math.pi*hour/24)])
    x=torch.tensor((np.array(values)-np.array(a['input_mean']))/np.array(a['input_scale']),dtype=torch.float32).unsqueeze(0)
    prediction=infer_model(load_model(a),x,a['delta_mean'],a['delta_scale'],np.array([seen[last][0]]))[0]
    return {'mode':'Historical next-hour extrapolation example, NOT a live forecast','origin_utc':utc(last),'target_utc':utc(last+3600),'predicted_temperature_c':float(prediction),'persistence_c':seen[last][0],'target_actual_c':None,'known_target_error':None,'captured_at_utc':s['captured_at_utc'],'note':'No target observation is included in the archived input; accuracy for this one example is unknown. The target date is historical relative to capture.'}

def evaluate(s,a,out):
    configure()
    if canonical_hash(s)!=a['source_snapshot_sha256']:raise ValueError('Replay source differs from trained experiment; retrain explicitly for a new source window')
    d=prepare(s);test=d['labels']=='test'
    # Saved scalers, never refitted for inference; prepare's scaler is only checked.
    mean=np.array(a['input_mean']);scale=np.array(a['input_scale'])
    if mean.shape!=(6,) or scale.shape!=(6,) or np.any(scale<=0) or not np.isfinite(scale).all() or not np.isfinite(mean).all():raise ValueError('Invalid scaler')
    if not np.array_equal(mean,d['mean']) or not np.array_equal(scale,d['scale']):raise ValueError('Preprocessing differs from experiment')
    model=load_model(a);x=torch.tensor((d['X'][test]-mean)/scale,dtype=torch.float32)
    pred=infer_model(model,x,a['delta_mean'],a['delta_scale'],d['last'][test])
    r=a['ridge'];linear=d['last'][test]+((d['linear'][test]-np.array(r['mean']))/np.array(r['scale']))@np.array(r['coef'])+r['intercept']
    predictions={'lstm':pred,'persistence':d['last'][test],'previous_day':d['seasonal'][test],'ridge':linear};actual=d['y'][test]
    metrics={k:errors(actual,v) for k,v in predictions.items()}
    t=d['times'][test];cap=datetime.fromisoformat(s['captured_at_utc'].replace('Z','+00:00'));last_seen=max(clean(s)[0])
    result={'mode':'Retrospective one-hour reanalysis extrapolation; no live nowcast or retail-sales prediction','captured_at_utc':s['captured_at_utc'],'requested_coordinates':[51.5074,-.1278],'returned_grid_coordinates':[s['response']['latitude'],s['response']['longitude']],'source_model_requested':'ERA5','first_source_utc':utc(min(clean(s)[0])),'last_source_utc':utc(last_seen),'source_age_hours_at_capture':(cap.timestamp()-last_seen)/3600,'quality':d['quality'],'split_counts':d['counts'],'training_scaler_unique_hours':d['training_scaler_unique_hours'],'train_end_exclusive':utc(d['train_end']),'validation_end_exclusive':utc(d['validation_end']),'heldout_first_origin':utc(t[0]-3600),'heldout_first_target':utc(t[0]),'heldout_last_target':utc(t[-1]),'heldout_metrics':metrics,'lstm_beats_persistence_mae':metrics['lstm']['mae_c']<metrics['persistence']['mae_c'],'lstm_beats_ridge_mae':metrics['lstm']['mae_c']<metrics['ridge']['mae_c'],'training':a['training'],'source_snapshot_sha256':canonical_hash(s),'limitations':['One gridded London-area point and one warm-to-autumn 180-day period; no measured store sales or footfall.','ERA5 is delayed retrospective reanalysis and can incorporate later information; this chronological statistical split does not simulate operational as-issued data availability.','One fixed seed and small model; no independent regional/year validation, uncertainty calibration or public deployment.']}
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'next_hour_example.json').write_text(json.dumps(tail_example(s,a),indent=2,allow_nan=False)+'\n')
    (out/'metrics.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    rows=[]
    for i,when in enumerate(t):rows.append({'origin_utc':utc(when-3600),'target_utc':utc(when),'actual_c':float(actual[i]),**{k+'_c':float(v[i]) for k,v in predictions.items()}})
    with (out/'test_predictions.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    table='<table><tr><th>Method</th><th>Held-out MAE °C</th><th>RMSE °C</th></tr>'+''.join(f'<tr><td>{html.escape(k)}</td><td>{v["mae_c"]:.4f}</td><td>{v["rmse_c"]:.4f}</td></tr>' for k,v in metrics.items())+'</table>'
    (out/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>London weather LSTM experiment</title><style>body{font:16px system-ui;background:#102535;color:#edf4f9;max-width:1000px;margin:35px auto}td,th{padding:10px;border-bottom:1px solid #789}pre{white-space:pre-wrap}</style><h1>London weather LSTM experiment</h1><p>Historical ERA5 reanalysis; not a live retail sales or weather service. Read source dates and limitations.</p>'+table+'<h2>Measured evidence</h2><pre>'+html.escape(json.dumps(result,indent=2))+'</pre></html>')
    return result

def main():
    p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--train',action='store_true');mode.add_argument('--predict',action='store_true');p.add_argument('--live',action='store_true',help='Download delayed historical reanalysis, not live station data');p.add_argument('--end',type=date.fromisoformat);p.add_argument('--days',type=int,default=180);p.add_argument('--input',default='examples/source_snapshot.json');p.add_argument('--model',default='examples/model.json');p.add_argument('--output',default='outputs');a=p.parse_args()
    if a.live and not a.train:p.error('--live requires --train; replay prediction uses an exact trained source snapshot')
    s=collect(a.end,a.days) if a.live else json.loads(Path(a.input).read_text());out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    if a.train:
        artifact,curve=train(s);(out/'model.json').write_text(json.dumps(artifact,indent=2,allow_nan=False)+'\n')
        with (out/'learning_curve.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=curve[0]);w.writeheader();w.writerows(curve)
    else:artifact=json.loads(Path(a.model).read_text())
    result=evaluate(s,artifact,out)
    if a.live:(out/'source_snapshot.json').write_text(json.dumps(s,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
