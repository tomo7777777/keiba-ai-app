import sys, json, gzip, itertools, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts')
import evwide as EVW, myomi as MY
from sklearn.linear_model import LogisticRegression
A='/home/user/workspace/keiba-ai-app/data/archive/nar/'
H=pd.read_pickle('/tmp/ana_jra_all.pkl'); H=H[H.umaban.notna()].copy(); H['umaban']=H.umaban.astype(int); H['race_id']=H.race_id.astype(str)
R=pd.read_pickle('/tmp/co/ev_rows_jra.pkl'); R=R[R.kind=='ワイド']
def X(g):
    lmc=np.log(1/g.odds)
    return np.c_[lmc,np.log(g.pm),np.log(g.pa),np.log(g.adjp),np.log(g.adjmax),np.log(g.adjmin),np.log(g.omin),np.log(g.omax),np.log(g.n),lmc*np.log(g.adjp)]
COEF={}
for f in R.fold.unique():
    a=R[R.fold!=f]; m=LogisticRegression(max_iter=3000).fit(X(a),(a.pay>0).astype(int)); COEF[f]=(m.intercept_[0],m.coef_[0])
R=R[R.race_id.isin(set(H.race_id))]
WO={rid:dict(zip(g.k,g.odds)) for rid,g in R.groupby('race_id')}
PAY={}
for fn in ['/home/user/workspace/keiba-ai-app/data/archive/jra/2022.jsonl.gz']+([A] if False else []):
    for l in gzip.open(fn,'rt'):
        r=json.loads(l)
        if r['race_id'] in WO: PAY[r['race_id']]=r['payout']
races=[]
for rid,g in H.groupby('race_id'):
    if rid not in WO or rid not in PAY: continue
    g=g.sort_values('umaban')
    if not (6<=len(g)<=18) or g.odds.isna().any(): continue
    lg=lambda p: np.log(p/(1-p))
    races.append((rid,g.fold.iloc[0],g.umaban.values,g.odds.values.astype(float),lg(np.clip(g.p3.values,1e-6,1-1e-6))-lg(np.clip(g.m3.values,1e-6,1-1e-6))))
import pickle; pickle.dump((races,WO,PAY,COEF),open('/tmp/sim/base_jra.pkl','wb')); print(len(races))
