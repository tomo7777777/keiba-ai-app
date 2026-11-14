import sys, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
rows, preds = sys.argv[1], sys.argv[2].split(',')
HON_TH, ANA_TH = 1.2, 1.0
R=pd.read_pickle(rows); R=R[R.kind=='ワイド'].copy(); R['hit']=(R.pay>0).astype(int)
def X(g):
    lmc=np.log(1/g.odds)
    return np.c_[lmc, np.log(g.pm), np.log(g.pa), np.log(g.adjp), np.log(g.adjmax), np.log(g.adjmin), np.log(g.omin), np.log(g.omax), np.log(g.n), lmc*np.log(g.adjp)]
folds=sorted(R.fold.unique()); R['ev']=np.nan
for f in folds:
    a=R[R.fold!=f]; m=LogisticRegression(max_iter=3000).fit(X(a),a.hit); ix=R.fold==f; R.loc[ix,'ev']=m.predict_proba(X(R[ix]))[:,1]*R.loc[ix,'odds']
H=pd.concat([pd.read_pickle(p) for p in preds]); H=H[H.umaban.notna()]; H['umaban']=H.umaban.astype(int); H['race_id']=H.race_id.astype(str)
H['pop']=H.groupby('race_id').odds.rank(method='first'); POP={(r,u):p for r,u,p in zip(H.race_id,H.umaban,H['pop'])}; ADJ={(r,u):a for r,u,a in zip(H.race_id,H.umaban,H.p3/H.m3)}
MINADJ=float(sys.argv[3]) if len(sys.argv)>3 else 0
R[['a','b']]=R.k.str.split('-',expand=True).astype(int)
out=[]
for rid,g in R[R.ev>=1.0].groupby('race_id'):
    sc={}
    for a,b,e in zip(g.a,g.b,g.ev): sc[a]=sc.get(a,0)+e-1; sc[b]=sc.get(b,0)+e-1
    sc={u:v for u,v in sc.items() if ADJ.get((rid,u),0)>=MINADJ}
    if not sc: continue
    J=max(sc,key=sc.get); p=POP.get((rid,J),99); cat='本命' if p<=3 else '穴'
    t=g[((g.a==J)|(g.b==J))&(g.ev>=(HON_TH if cat=='本命' else ANA_TH))].sort_values('ev',ascending=False).head(5)
    if t.empty: continue
    out.append((rid,g.fold.iloc[0],cat,len(t),t.pay.sum(),int((t.pay>0).any())))
O=pd.DataFrame(out,columns=['race_id','fold','cat','pts','ret','hit']); rng=np.random.default_rng(0)
nr=R.race_id.nunique()
for c,g in list(O.groupby('cat'))+[('合計',O)]:
    v=g[['ret','pts']].values; bs=[(lambda s:s[:,0].sum()/s[:,1].sum())(v[rng.integers(0,len(v),len(v))]) for _ in range(500)]
    per='/'.join(f"{g[g.fold==f].ret.sum()/max(g[g.fold==f].pts.sum(),1):.0f}" for f in folds)
    print(f"{c}: {len(g)}R（全{nr}Rの{len(g)/nr*100:.0f}%） 平均{g.pts.mean():.1f}点 的中率{g.hit.mean()*100:.1f}% 回収率{g.ret.sum()/g.pts.sum():.1f}% [{per}] 95%幅{np.percentile(bs,2.5):.0f}-{np.percentile(bs,97.5):.0f}")
