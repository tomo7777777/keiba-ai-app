"""オッズを使わないAI（朝の時点で出せる予想）の検証"""
import sys, gzip, json, glob, itertools, numpy as np, pandas as pd, lightgbm as lgb
sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts'); import myomi as MY, strategy as S
d=pd.read_pickle('/home/user/workspace/keiba-ai-app/data/nar/train_cache.pkl'); d['race_id']=d.race_id.astype(str)
d=d[d.odds.notna()&(d.odds>0)].copy(); d['qm']=1/d.odds; d['qm']=d.qm/d.groupby('race_id').qm.transform('sum'); d['lqm']=np.log(d.qm)
d['top3']=(d['rank']<=3).astype(int); d['win']=(d['rank']==1).astype(int)
bad=MY.DROP|{'qm','lqm','lq','top3','win','top2','p3','m3','gap'}
feats=[c for c in d.columns if c not in bad and d[c].dtype!=object]
print(len(feats), [f for f in feats if 'odd' in f or 'pop' in f or 'q' in f][:20])
P={}
for f in glob.glob('/home/user/workspace/keiba-ai-app/data/nar/history/*.gz'):
    for l in gzip.open(f,'rt'):
        r=json.loads(l); P[r['race_id']]=r['payout']
folds=[('2025-12-01','2026-03-01'),('2026-03-01','2026-07-01'),('2026-07-01','2026-12-01')]
out=[]
for a,b in folds:
    tr=d[d.date<a]; te=d[(d.date>=a)&(d.date<b)].copy()
    prm=dict(objective='binary',learning_rate=0.05,num_leaves=31,min_data_in_leaf=100,feature_fraction=0.8,verbose=-1)
    m3=lgb.train(prm,lgb.Dataset(tr[feats].astype(float),tr.top3),400)
    m1=lgb.train(prm,lgb.Dataset(tr[feats].astype(float),tr.win),400)
    mq=lgb.train(dict(objective='regression',learning_rate=0.05,num_leaves=63,min_data_in_leaf=100,feature_fraction=0.8,verbose=-1),lgb.Dataset(tr[feats].astype(float),tr.lqm),600)
    te['qhat']=np.exp(mq.predict(te[feats].astype(float))); te['qhat']=te.qhat/te.groupby('race_id').qhat.transform('sum')
    te['p3n']=m3.predict(te[feats].astype(float)); te['p1n']=m1.predict(te[feats].astype(float)); te['fold']=a
    out.append(te[['race_id','date','umaban','odds','rank','p3n','p1n','fold','n','qhat']])
O=pd.concat(out); O.to_pickle('nood_pred.pkl')
O['pop']=O.groupby('race_id').odds.rank(method='first')
from sklearn.metrics import roc_auc_score
print('AUC 3着内', roc_auc_score(O['rank']<=3,O.p3n), ' 人気(参考)', roc_auc_score(O['rank']<=3,-O.odds))
