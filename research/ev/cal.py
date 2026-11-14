"""学習期間で『この組が来る確率』を実績から学び、残りの期間で 確率×オッズ が高い目だけ買う"""
import sys, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
R=pd.read_pickle(sys.argv[1] if len(sys.argv)>1 else '/tmp/co/ev_rows.pkl')
TR=sys.argv[2] if len(sys.argv)>2 else None
R['hit']=(R.pay>0).astype(int)
def X(g):
    lmc=np.log(1/g.odds)
    return np.c_[lmc, np.log(g.pm), np.log(g.pa), np.log(g.adjp), np.log(g.adjmax), np.log(g.adjmin), np.log(g.omin), np.log(g.omax), np.log(g.n), lmc*np.log(g.adjp)]
folds=sorted(R.fold.unique()); tr=TR or folds[0]
print('学習期間',tr,'検証',[f for f in folds if f!=tr])
for kind,g in R.groupby('kind'):
    a=g[g.fold==tr]; m=LogisticRegression(C=1.0,max_iter=2000).fit(X(a),a.hit)
    for withai in (False,):
        pass
    g=g.copy(); g['p']=m.predict_proba(X(g))[:,1]; g['ev']=g.p*g.odds
    # 比較: 市場だけのモデル
    cols=[0,1,6,7,8]; mm=LogisticRegression(max_iter=2000).fit(X(a)[:,cols],a.hit); g['evm']=mm.predict_proba(X(g)[:,cols])[:,1]*g.odds
    print('==',kind)
    for col in ('ev','evm'):
        for t in (1.0,1.1,1.2,1.3,1.5):
            s=[]
            for f in folds:
                x=g[(g.fold==f)&(g[col]>=t)]
                s.append(f'{f[:7]}:{x.pay.sum()/max(len(x),1):.0f}%({len(x)}点/{x.race_id.nunique()}R)')
            print(' ','AI込' if col=='ev' else '市場のみ',f'期待値{t}以上',' '.join(s))
