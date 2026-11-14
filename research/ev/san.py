"""3連複の期待値検証：期待値AIの軸（旨味のある馬）を含む組の『来る確率×オッズ』"""
import sys, json, gzip, glob, itertools, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
TAG=sys.argv[1]
if TAG=='nar':
    sel=pd.read_pickle('/tmp/co/ev_rows_sel.pkl'); preds=['/tmp/ana_nar_all.pkl','/tmp/ana_nar_ext.pkl']
    SAN={}
    for f in glob.glob('/tmp/co/san_nar_*.jsonl'):
        for l in open(f):
            try: r=json.loads(l)
            except Exception: continue
            if r['san']: SAN[r['race_id']]=r['san']
    hist=['archive/nar/2024','archive/nar/2025H1','nar/history/2026']
else:
    sel=pd.read_pickle('/tmp/co/ev_rows_jra_sel.pkl'); preds=['/tmp/ana_jra_all.pkl','/tmp/ana_jra_ext.pkl']
    SAN={}
    for l in gzip.open('/tmp/co/ja/san_jra.jsonl.gz','rt'):
        r=json.loads(l)
        if r['san']: SAN[r['race_id']]=r['san']
    hist=['archive/jra/2022','archive/jra/2023','history/2025','history/2026']
PAY={}
ids=set(sel.race_id)
for h in hist:
    for l in gzip.open(f'/home/user/workspace/keiba-ai-app/data/{h}.jsonl.gz','rt'):
        r=json.loads(l)
        if r['race_id'] in ids: PAY[r['race_id']]={k:v for k,v in r['payout'].get('三連複',[])}
H=pd.concat([pd.read_pickle(p) for p in preds]); H=H[H.umaban.notna()].copy(); H['umaban']=H.umaban.astype(int); H['race_id']=H.race_id.astype(str)
G=dict(tuple(H.groupby('race_id')))
def tri(w,g2=0.85,g3=0.75):
    n=len(w); w2=w**g2; w2/=w2.sum(); w3=w**g3; w3/=w3.sum()
    P=w[:,None]*w2[None,:]/(1-w2[:,None]); np.fill_diagonal(P,0)
    T=P[:,:,None]*w3[None,None,:]/np.clip(1-w3[:,None,None]-w3[None,:,None],1e-9,None)
    I=np.arange(n); T[I,:,I]=0; T[:,I,I]=0; T[I,I,:]=0
    return T+T.transpose(0,2,1)+T.transpose(1,0,2)+T.transpose(1,2,0)+T.transpose(2,0,1)+T.transpose(2,1,0)
rows=[]
for rid,fold,cat,J in zip(sel.race_id,sel.fold,sel.cat,sel.axis):
    if rid not in SAN or rid not in PAY or rid not in G: continue
    g=G[rid].sort_values('umaban'); n=len(g)
    if n<6 or n>18: continue
    um=list(g.umaban); q=g.q.values; adj=g.p3.values/g.m3.values; od=g.odds.values
    if J not in um: continue
    wa=q*adj; wa/=wa.sum(); Pm=tri(q/q.sum()); Pa=tri(wa); j=um.index(J)
    for x,y in itertools.combinations([i for i in range(n) if i!=j],2):
        k='-'.join(map(str,sorted([um[j],um[x],um[y]]))); o=SAN[rid].get(k)
        if not o: continue
        rows.append((rid,fold,cat,k,n,Pm[j,x,y],Pa[j,x,y],adj[j],adj[x]*adj[y],od[j],min(od[x],od[y]),max(od[x],od[y]),o,PAY[rid].get(k,0)))
R=pd.DataFrame(rows,columns=['race_id','fold','cat','k','n','pm','pa','adjj','adjxy','oj','omin','omax','odds','pay'])
R['hit']=(R.pay>0).astype(int)
def X(g):
    lmc=np.log(1/g.odds)
    return np.c_[lmc,np.log(g.pm),np.log(g.pa),np.log(g.adjj),np.log(g.adjxy),np.log(g.oj),np.log(g.omin),np.log(g.omax),np.log(g.n),lmc*np.log(g.adjj*g.adjxy)]
folds=sorted(R.fold.unique()); R['ev']=np.nan
for f in folds:
    a=R[R.fold!=f]; m=LogisticRegression(max_iter=3000,C=1.0).fit(X(a),a.hit); ix=R.fold==f; R.loc[ix,'ev']=m.predict_proba(X(R[ix]))[:,1]*R.loc[ix,'odds']
R.to_pickle(f'/tmp/co/san_rows_{TAG}.pkl')
print(TAG,'レース',R.race_id.nunique(),'組',len(R),'全部買い',round(R.pay.sum()/len(R),1))
rng=np.random.default_rng(0)
for cat in ('本命','穴'):
    for th in (1.0,1.2,1.5,2.0):
        for N in (5,10):
            x=R[(R.cat==cat)&(R.ev>=th)].sort_values('ev',ascending=False).groupby('race_id').head(N)
            if x.empty: continue
            rr=x.groupby('race_id').agg(ret=('pay','sum'),pts=('pay','size'),hit=('hit','max'),fold=('fold','first'))
            v=rr[['ret','pts']].values; bs=[(lambda s:s[:,0].sum()/s[:,1].sum())(v[rng.integers(0,len(v),len(v))]) for _ in range(300)]
            per='/'.join(f"{rr[rr.fold==f].ret.sum()/max(rr[rr.fold==f].pts.sum(),1):.0f}" for f in folds)
            print(f"{cat} 期待値{th}以上 最大{N}点: {len(rr)}R 平均{rr.pts.mean():.1f}点 的中率{rr.hit.mean()*100:.1f}% 回収率{rr.ret.sum()/rr.pts.sum():.1f}% [{per}] 95%幅{np.percentile(bs,2.5):.0f}-{np.percentile(bs,97.5):.0f} 平均オッズ{x.odds.median():.0f}")
