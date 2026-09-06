"""Reproducible chronological model/calibration/evaluation; no fitted binary pickle."""
import argparse
import hashlib
import json
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss,log_loss,roc_auc_score,average_precision_score
from .data import ROOT,load_flights
from .engine import FEATURE_NAMES,connections,features,predict,split

def metrics(y,p):
    y=np.asarray(y);p=np.asarray(p)
    bins=[];ece=0.
    for i in range(10):
        mask=(p>=i/10)&(p<(i+1)/10 if i<9 else p<=1)
        if mask.any():
            pred=float(p[mask].mean());obs=float(y[mask].mean());n=int(mask.sum())
            bins.append({'predicted':pred,'observed':obs,'n':n});ece+=n/len(y)*abs(pred-obs)
    return {'n':len(y),'prevalence':float(y.mean()),'brier':float(brier_score_loss(y,p)),
      'log_loss':float(log_loss(y,p,labels=[0,1])),
      'roc_auc':float(roc_auc_score(y,p)) if len(set(y))==2 else None,
      'average_precision':float(average_precision_score(y,p)), 'ece_10':float(ece),'calibration_bins':bins}

def fit(train,cal,target,layover_only=False):
    x=np.array([features(r) for r in train]);cx=np.array([features(r) for r in cal])
    if layover_only:x=x[:,:2];cx=cx[:,:2]
    raw=LogisticRegression(C=1.,solver='lbfgs',max_iter=3000,random_state=17).fit(x,[r[target] for r in train])
    calibrator=LogisticRegression(C=1000000.,solver='lbfgs',max_iter=3000,random_state=17).fit(raw.decision_function(cx).reshape(-1,1),[r[target] for r in cal])
    coeff=raw.coef_[0].tolist()
    if layover_only:coeff += [0.]*(len(FEATURE_NAMES)-len(coeff))
    return {'intercept':float(raw.intercept_[0]),'coef':coeff,'cal_coef':float(calibrator.coef_[0,0]),
      'cal_intercept':float(calibrator.intercept_[0]),'features':FEATURE_NAMES,
      'train_period':['2025-01-01','2025-01-31'],'calibration_period':['2025-02-03','2025-02-28'],
      'target':target,'calibration':'sigmoid on separate chronological calibration set'}

def comparison(rows):
    groups=defaultdict(list)
    for r in rows:groups[r['group']].append(r)
    groups=[g for g in groups.values() if len(g)>1]
    results={}
    for name,key in [('shortest',lambda r:(r['duration'],r['id'])),('lowest_failure_risk',lambda r:(r['risk'],r['duration'],r['id'])),('lowest_disruption_risk',lambda r:(r['disruption_risk'],r['duration'],r['id']))]:
        chosen=[min(g,key=key) for g in groups]
        results[name]={'groups':len(chosen),'failure_rate':float(np.mean([r['failure'] for r in chosen])),
          'disruption_rate':float(np.mean([r['disruption'] for r in chosen])),
          'mean_scheduled_minutes':float(np.mean([r['duration'] for r in chosen]))}
    return results

def run(output):
    flights=load_flights();rows=connections(flights)
    parts={s:[r for r in rows if split(r)==s] for s in ['train','calibration','test','embargo']}
    train,cal,test=[parts[s] for s in ['train','calibration','test']]
    models={t:fit(train,cal,t) for t in ['failure','disruption']}
    base=fit(train,cal,'failure',True)
    for r in rows:
        r['split']=split(r);r['risk']=predict(r,models['failure']);r['disruption_risk']=predict(r,models['disruption'])
    y=np.array([r['failure'] for r in test]);p=np.array([r['risk'] for r in test]);bp=np.array([predict(r,base) for r in test])
    # Paired cluster bootstrap of daily mean Brier differences. Days, not independent itineraries.
    days=sorted(set(r['date'] for r in test));delta=[]
    for day in days:
        m=np.array([r['date']==day for r in test]);delta.append(float(np.mean((p[m]-y[m])**2-(bp[m]-y[m])**2)))
    rng=np.random.default_rng(17);boot=np.mean(rng.choice(delta,(1000,len(days))),axis=1)
    evaluation={'source_flights':len(flights),'connections_by_split':{s:len(rs) for s,rs in parts.items()},
      'failure':metrics(y,p),'disruption':metrics([r['disruption'] for r in test],[r['disruption_risk'] for r in test]),
      'layover_baseline':metrics(y,bp),'constant_calibration_prevalence':metrics(y,np.full(len(y),np.mean([r['failure'] for r in cal]))),
      'daily_brier_difference_model_minus_layover':{'mean':float(np.mean(delta)),'bootstrap_95':np.quantile(boot,[.025,.975]).tolist(),'seed':17,'replicates':1000,'cluster':'inbound local date; equal weight per day'},
      'policy_comparison':comparison(test),'test_reasons':dict(Counter(r['reason'] for r in test)),
      'interpretation':'Synthetic itinerary labels from real BTS flights; not observed passenger outcomes. Policy comparison is retrospective and not a causal estimate. Shared flights and days induce dependence.',
      'model_selection':'Feature set and regularization fixed before inspecting March evaluation; no March tuning.'}
    output.mkdir(parents=True,exist_ok=True)
    bundle={'models':models,'baseline':base,'airports':['BOS','DEN','LAX','ORD','SEA'],
      'scope':'Delta-operated flights via ATL, Jan–Mar 2025; historical research only',
      'transfer_minutes':30,'boarding_cutoff_minutes':15,'trained_on_csv_sha256':hashlib.sha256((ROOT/'data/flights.csv').read_bytes()).hexdigest()}
    for name,obj in [('model.json',bundle),('evaluation.json',evaluation),('replay.json',test)]:
        (output/name).write_text(json.dumps(obj,separators=(',',':'),allow_nan=False)+'\n')
    print(json.dumps(evaluation,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'web');run(parser.parse_args().output)
