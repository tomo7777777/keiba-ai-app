import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
R=pd.read_pickle('ev_rows.pkl'); R=R[R.kind=='ワイド'].copy(); R['hit']=(R.pay>0).astype(int)
def X(g):
    lmc=np.log(1/g.odds)
    return np.c_[lmc, np.log(g.pm), np.log(g.pa), np.log(g.adjp), np.log(g.adjmax), np.log(g.adjmin), np.log(g.omin), np.log(g.omax), np.log(g.n), lmc*np.log(g.adjp)]
folds=sorted(R.fold.unique()); R['ev']=np.nan
for f in folds:
    a=R[R.fold!=f]; m=LogisticRegression(max_iter=3000).fit(X(a),a.hit)
    ix=R.fold==f; R.loc[ix,'ev']=m.predict_proba(X(R[ix]))[:,1]*R.loc[ix,'odds']
R[['a','b']]=R.k.str.split('-',expand=True).astype(int)
R[R.ev>=0.9].to_pickle('wide_ev.pkl'); print(len(R))
