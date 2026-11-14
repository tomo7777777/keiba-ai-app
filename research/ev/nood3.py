import sys, gzip, json, glob, itertools, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts'); import strategy as S, myomi as MY
O=pd.read_pickle('nood_pred.pkl')
P={}
for f in glob.glob('/home/user/workspace/keiba-ai-app/data/nar/history/*.gz'):
    for l in gzip.open(f,'rt'):
        r=json.loads(l); P[r['race_id']]=r['payout']
F=sorted(O.fold.unique()); res={}; rets={}
def add(key,fold,inv,ret):
    a=res.setdefault(key,{f:[0,0,0,0] for f in F}); x=a[fold]; x[0]+=1;x[1]+=inv;x[2]+=ret;x[3]+=ret>0; rets.setdefault(key,[]).append(ret)
for rid,g in O.groupby('race_id'):
    pay=P.get(rid)
    if not pay or len(g)<7: continue
    g=g.sort_values('umaban').copy(); _,m3=MY.harville(g.qhat.values); g['m3h']=m3; g['ratio']=g.p3n/g.m3h
    g['ppop']=g.qhat.rank(ascending=False,method='first'); fold=g.fold.iloc[0]; fav=g.odds.min(); qmax=g.qhat.max()
    ai=[int(u) for u in g.sort_values('p3n',ascending=False).umaban]
    s=lambda *x:'-'.join(map(str,sorted(x))); st=lambda *x:'-'.join(map(str,x))
    for kind,mask in (('本命',g.ppop<=3),('穴',g.ppop>=4)):
        c=g[mask&(g.ratio>=1.0)]
        if not len(c): continue
        ax=c.loc[c.ratio.idxmax()]; J=int(ax.umaban); oth=[u for u in ai if u!=J]
        Tw=[['ワイド',s(J,b),100] for b in oth[:3]]; Tt=[['三連単',st(J,a,b),100] for a,b in itertools.permutations(oth[:(4 if kind=='本命' else 3)],2)]
        conds=[('全',True),('ズレ1.3以上',ax.ratio>=1.3),('ズレ1.5以上',ax.ratio>=1.5)]
        if kind=='穴': conds+= [('予想で混戦',qmax<=0.32),('予想で混戦&ズレ1.3',(qmax<=0.32)&(ax.ratio>=1.3)),('予想で混戦&12頭',(qmax<=0.32)&(len(g)>=12)),('参考:実際の1番人気2.5倍以上',fav>=2.5)]
        else: conds+= [('AI3着内60%以上',ax.p3n>=0.6),('AI3着内60%&ズレ1.2',(ax.p3n>=0.6)&(ax.ratio>=1.2))]
        for nm,cd in conds:
            if not cd: continue
            inv,ret,_=S.settle(Tw,pay); add(f'{kind} {nm} ワイド3点',fold,inv,ret)
            if '三連単' in pay: inv,ret,_=S.settle(Tt,pay); add(f'{kind} {nm} 3連単{len(Tt)}点',fold,inv,ret)
for k,a in res.items():
    n=sum(v[0] for v in a.values()); inv=sum(v[1] for v in a.values()); ret=sum(v[2] for v in a.values()); h=sum(v[3] for v in a.values())
    w=sorted(rets[k],reverse=True)
    print(f"{k:34s} {n:6d}R 的中{h/n*100:5.1f}% 回収{ret/inv*100:6.1f}% [{'/'.join(f'{v[2]/max(v[1],1)*100:.0f}' for v in a.values())}] 上位3除く{(ret-sum(w[:3]))/inv*100:.0f}%")
