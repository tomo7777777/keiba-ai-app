import numpy as np, pandas as pd
R=pd.read_pickle('wide_ev.pkl'); folds=sorted(R.fold.unique())
H=pd.concat([pd.read_pickle(p) for p in ['/tmp/ana_nar_all.pkl','/tmp/ana_nar_ext.pkl']]); H=H[H.umaban.notna()]; H['umaban']=H.umaban.astype(int); H['race_id']=H.race_id.astype(str)
H['pop']=H.groupby('race_id').odds.rank(method='first'); POP={(r,u):(p,o) for r,u,p,o in zip(H.race_id,H.umaban,H['pop'],H.odds)}
R['race_id']=R.race_id.astype(str)
C=R[R.ev>=1.0]; out=[]
for rid,g in C.groupby('race_id'):
    sc={}
    for a,b,e in zip(g.a,g.b,g.ev): sc[a]=sc.get(a,0)+e-1; sc[b]=sc.get(b,0)+e-1
    J=max(sc,key=sc.get); t=g[(g.a==J)|(g.b==J)].sort_values('ev',ascending=False).head(5)
    p,o=POP.get((rid,J),(99,0))
    if p<=3: continue
    out.append(dict(race_id=rid,fold=g.fold.iloc[0],pop=p,aodds=o,n=g.n.iloc[0],evs=t.ev.values,pays=t.pay.values,score=sc[J]))
O=pd.DataFrame(out); print('穴R',len(O))
def rep(name,mask,minev=1.0):
    pts=ret=hit=0; per={f:[0,0] for f in folds}; rets=[]; nR=0
    for _,r in O[mask].iterrows():
        k=r.evs>=minev
        if not k.any(): continue
        p=k.sum(); rr=r.pays[k].sum(); pts+=p; ret+=rr; hit+=rr>0; nR+=1; per[r.fold][0]+=p; per[r.fold][1]+=rr; rets.append(rr)
    rets=sorted(rets,reverse=True); ex=(ret-sum(rets[:3]))/pts if pts else 0
    print(f"{name:28s} {nR:5d}R 1日約{nR/ (len(folds)*91) :.1f}R 的中{hit/max(nR,1)*100:4.1f}% 回収{ret/max(pts,1):5.1f}% [{'/'.join(f'{v[1]/max(v[0],1):.0f}' for v in per.values())}] 上位3除く{ex:.0f}%")
O['mx']=O.evs.apply(max)
rep('現行(全穴)',O.mx>0)
for T in (1.1,1.2,1.3,1.4,1.5,1.7,2.0): rep(f'最高EV>={T} 買い目もEV>={T}',O.mx>=T,T)
for T in (1.2,1.3,1.5): rep(f'最高EV>={T} 買い目EV>=1.0',O.mx>=T,1.0)
for lo,hi in ((0,10),(10,20),(20,50),(50,999)): rep(f'軸オッズ{lo}-{hi}',(O.aodds>=lo)&(O.aodds<hi))
for lo,hi in ((0,10),(10,13),(13,99)): rep(f'頭数{lo}-{hi}',(O.n>=lo)&(O.n<hi))
for T in (0.5,1.0,1.5): rep(f'軸スコア>={T}',O.score>=T)
