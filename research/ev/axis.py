"""期待値のある組の中から『旨味のある馬（軸）』を選び、軸の人気で本命レース／穴レースに分けて検証"""
import sys, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
rows, preds, kind = sys.argv[1], sys.argv[2].split(','), sys.argv[3] if len(sys.argv)>3 else 'ワイド'
R=pd.read_pickle(rows); R=R[R.kind==kind].copy(); R['hit']=(R.pay>0).astype(int)
def X(g):
    lmc=np.log(1/g.odds)
    return np.c_[lmc, np.log(g.pm), np.log(g.pa), np.log(g.adjp), np.log(g.adjmax), np.log(g.adjmin), np.log(g.omin), np.log(g.omax), np.log(g.n), lmc*np.log(g.adjp)]
folds=sorted(R.fold.unique()); R['ev']=np.nan
for f in folds:  # その期間を除いた全期間で学習（学習に使っていない期間の予測）
    a=R[R.fold!=f]; m=LogisticRegression(max_iter=3000).fit(X(a),a.hit)
    ix=R.fold==f; R.loc[ix,'ev']=m.predict_proba(X(R[ix]))[:,1]*R.loc[ix,'odds']
H=pd.concat([pd.read_pickle(p) for p in preds]); H=H[H.umaban.notna()]; H['umaban']=H.umaban.astype(int); H['race_id']=H.race_id.astype(str)
H['pop']=H.groupby('race_id').odds.rank(method='first'); POP={(r,u):(p,o) for r,u,p,o in zip(H.race_id,H.umaban,H['pop'],H.odds)}
R[['a','b']]=R.k.str.split('-',expand=True).astype(int)
out=[]
for TH in (1.0,1.1,1.2,1.3):
    C=R[R.ev>=TH]
    for rid,g in C.groupby('race_id'):
        sc={}
        for a,b,e in zip(g.a,g.b,g.ev): sc[a]=sc.get(a,0)+e-1; sc[b]=sc.get(b,0)+e-1
        J=max(sc,key=sc.get); t=g[(g.a==J)|(g.b==J)].sort_values('ev',ascending=False).head(5)
        p,o=POP.get((rid,J),(99,0))
        out.append((TH,rid,g.fold.iloc[0],J,p,o,len(t),t.pay.sum(),int((t.pay>0).any()),t.ev.mean()))
O=pd.DataFrame(out,columns=['th','race_id','fold','axis','pop','odds','pts','ret','hit','ev'])
O['cat']=np.where(O['pop']<=3,'本命（1〜3番人気）',np.where(O.odds>=10,'穴（10倍以上）','中穴（4番人気以下・10倍未満）'))
pd.set_option('display.width',250)
for (th,cat),g in O.groupby(['th','cat']):
    per='/'.join(f"{g[g.fold==f].ret.sum()/max(g[g.fold==f].pts.sum(),1):.0f}" for f in folds)
    top=g.ret.sort_values(ascending=False); ex=(g.ret.sum()-top.iloc[:max(1,len(g)//100)].sum())/g.pts.sum()*100
    print(f"期待値{th}以上 {cat}: {len(g)}R 平均{g.pts.mean():.1f}点 的中率{g.hit.mean()*100:.1f}% 回収率{g.ret.sum()/g.pts.sum():.1f}% [{per}] 上位1%除く{ex/100:.0f}% 軸平均オッズ{g.odds.median():.1f}")
O.to_pickle(rows.replace('.pkl','_axis.pkl'))
