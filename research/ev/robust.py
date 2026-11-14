import sys, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
exec(open('/tmp/co/cal.py').read().split("folds=sorted")[0].split("R=pd.read_pickle")[0])
R=pd.read_pickle(sys.argv[1]); R['hit']=(R.pay>0).astype(int)
def X(g):
    lmc=np.log(1/g.odds)
    return np.c_[lmc, np.log(g.pm), np.log(g.pa), np.log(g.adjp), np.log(g.adjmax), np.log(g.adjmin), np.log(g.omin), np.log(g.omax), np.log(g.n), lmc*np.log(g.adjp)]
folds=sorted(R.fold.unique()); rng=np.random.default_rng(0)
for kind in sys.argv[2].split(','):
  g0=R[R.kind==kind]
  for tr in folds:
    a=g0[g0.fold==tr]; m=LogisticRegression(max_iter=2000).fit(X(a),a.hit)
    g=g0[g0.fold!=tr].copy(); g['ev']=m.predict_proba(X(g))[:,1]*g.odds
    for t in (1.0,1.1,1.2,1.3):
        x=g[g.ev>=t]; roi=x.pay.sum()/len(x)
        per=' '.join(f'{f[:7]}:{x[x.fold==f].pay.sum()/max((x.fold==f).sum(),1):.0f}' for f in folds if f!=tr)
        top=x.pay.sort_values(ascending=False); ex=(x.pay.sum()-top.iloc[:max(1,len(x)//100)].sum())/len(x)
        rs=x.groupby('race_id').pay.agg(['sum','count']).values
        bs=[ (lambda s: s[:,0].sum()/s[:,1].sum())(rs[rng.integers(0,len(rs),len(rs))]) for _ in range(300)]
        print(f'{kind} 学習{tr[:7]} 期待値{t}以上: {len(x)}点 {x.race_id.nunique()}R 回収率{roi:.1f}% [{per}] 上位1%除く{ex:.0f}% 95%幅{np.percentile(bs,2.5):.0f}-{np.percentile(bs,97.5):.0f} 的中率{x.hit.mean()*100:.1f}% 平均オッズ{x.odds.median():.1f}')
