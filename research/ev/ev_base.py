"""組み合わせ馬券の期待値検証（地方）：AIの勝率×実際の確定オッズで割安な目だけ買う"""
import sys, json, gzip, itertools, numpy as np, pandas as pd, collections
sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts'); import features as F
d=pd.read_pickle('/tmp/ana_nar_base.pkl')
d=d[d.umaban.notna()].copy(); d['umaban']=d.umaban.astype(int); d['race_id']=d.race_id.astype(str)
CO={}
for l in open('/tmp/co/combo_nar.jsonl').readlines()+open('/tmp/co/combo_nar2.jsonl').readlines():
    try: r=json.loads(l)
    except Exception: continue
    if r['umaren'] and r['wide']: CO[r['race_id']]=r
PAY={}
for f in ['/home/user/workspace/keiba-ai-app/data/archive/nar/2024.jsonl.gz','/home/user/workspace/keiba-ai-app/data/archive/nar/2025H1.jsonl.gz','/home/user/workspace/keiba-ai-app/data/nar/history/2026.jsonl.gz']:
    for l in gzip.open(f,'rt'):
        r=json.loads(l)
        if r['race_id'] in CO: PAY[r['race_id']]=r['payout']
def probs(w,g2,g3):
    """Harville＋2着・3着の補正（Henery型）: 上位2頭/3頭に入る組の確率"""
    n=len(w); w2=w**g2; w2/=w2.sum(); w3=w**g3; w3/=w3.sum()
    P=w[:,None]*w2[None,:]/(1-w2[:,None]); np.fill_diagonal(P,0)
    T=P[:,:,None]*w3[None,None,:]/np.clip(1-w3[:,None,None]-w3[None,:,None],1e-9,None)
    I=np.arange(n); T[:,:,I]*=1; T[I,:,I]=0; T[:,I,I]=0
    T[I,I,:]=0
    W=T.sum(2)+T.sum(1)+T.sum(0)
    return P+P.T, W+W.T
rows=[]
for rid,g in d.groupby('race_id'):
    if rid not in CO or rid not in PAY: continue
    g=g.sort_values('umaban'); n=len(g)
    if n<6 or n>16: continue
    q=g.q.values; adj=(g.p3.values/g.m3.values); um=[int(x) for x in g.umaban]; co=CO[rid]; pay=PAY[rid]
    upay={k:v for k,v in pay.get('馬連',[])}; wpay={k:v for k,v in pay.get('ワイド',[])}
    Um,Wm=probs(q/q.sum(),0.85,0.75); wa=q*adj; wa/=wa.sum(); Ua,Wa=probs(wa,0.85,0.75)
    f=g.fold.iloc[0]; od=g.odds.values; p3=g.p3.values
    for i,j in itertools.combinations(range(n),2):
        k=f'{um[i]}-{um[j]}'
        for kind,Pm,Pa,O,PY in (('馬連',Um,Ua,co['umaren'],upay),('ワイド',Wm,Wa,co['wide'],wpay)):
            o=O.get(k)
            if not o: continue
            rows.append((rid,f,kind,k,n,Pm[i,j],Pa[i,j],adj[i]*adj[j],max(adj[i],adj[j]),min(adj[i],adj[j]),min(od[i],od[j]),max(od[i],od[j]),p3[i]*p3[j],o,PY.get(k,0)))
R=pd.DataFrame(rows,columns=['race_id','fold','kind','k','n','pm','pa','adjp','adjmax','adjmin','omin','omax','p3p','odds','pay'])
R.to_pickle('/tmp/co/ev_rows_base.pkl'); print(len(R), R.race_id.nunique())
