"""Optional scientific figures from actual saved training and held-out outputs."""
import argparse,csv
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',default='examples');a=p.parse_args();out=Path(a.output)
 with (out/'learning_curve.csv').open() as f:curve=list(csv.DictReader(f))
 with (out/'test_predictions.csv').open() as f:rows=list(csv.DictReader(f))
 plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','font.size':10})
 fig,axes=plt.subplots(1,2,figsize=(10,3.5),constrained_layout=True)
 axes[0].plot([int(r['epoch']) for r in curve],[float(r['training_normalized_delta_mse']) for r in curve],color='#187d9a');axes[0].set(xlabel='Epoch',ylabel='Normalised delta MSE',title='Training objective')
 axes[1].plot([int(r['epoch']) for r in curve],[float(r['validation_mae_c']) for r in curve],color='#aa5a16');axes[1].set(xlabel='Epoch',ylabel='Validation MAE (°C)',title='Checkpoint selection, no test tuning')
 for ax in axes:ax.grid(alpha=.2)
 fig.savefig(out/'learning_curve.svg',metadata={'Date':None});plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,3.7),constrained_layout=True)
 show=rows[:48];times=[datetime.fromisoformat(r['target_utc']) for r in show]
 for key,label,color in [('actual_c','ERA5 target','#162c44'),('lstm_c','LSTM','#187d9a'),('ridge_c','Ridge baseline','#aa5a16')]:ax.plot(times,[float(r[key]) for r in show],label=label,color=color,linewidth=1.7)
 ax.set(title='First 48 held-out hours — retrospective reanalysis experiment',ylabel='Temperature (°C)',xlabel='UTC target time');ax.legend(loc='best');ax.grid(alpha=.2);fig.autofmt_xdate();fig.savefig(out/'heldout_example.svg',metadata={'Date':None});plt.close(fig)
if __name__=='__main__':main()
