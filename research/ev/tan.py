"""穴馬（期待値AIの軸）を1着固定した3連単の回収率"""
import sys, gzip, json, glob, itertools, collections, pandas as pd, numpy as np
sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts'); import strategy as S
TAG=sys.argv[1]; D='/home/user/workspace/keiba-ai-app/data'
files = glob.glob(f'{D}/archive/nar/*.gz')+glob.glob(f'{D}/nar/history/*.gz') if TAG=='nar' else glob.glob(f'{D}/archive/jra/*.gz')+glob.glob(f'{D}/history/*.gz')
sel = pd.read_pickle('/tmp/co/ev_rows_sel.pkl' if TAG=='nar' else '/tmp/co/ev_rows_jra_sel.pkl'); sel['race_id']=sel.race_id.astype(str)
need=set(sel.race_id); R={}
for f in files:
    for l in gzip.open(f,'rt'):
        r=json.loads(l)
        if r['race_id'] in need: R[r['race_id']]=r
H=pd.concat([pd.read_pickle(f'/tmp/ana_{TAG}_all.pkl'),pd.read_pickle(f'/tmp/ana_{TAG}_ext.pkl')]); H=H[H.umaban.notna()]
H['umaban']=H.umaban.astype(int); H['race_id']=H.race_id.astype(str); HG=dict(list(H.groupby('race_id')))
res=collections.defaultdict(lambda: collections.defaultdict(lambda:[0,0,0,0])); wins=collections.defaultdict(list)
for row in sel.itertuples():
    r=R.get(row.race_id); g=HG.get(row.race_id)
    if r is None or g is None or '三連単' not in r['payout']: continue
    pay=r['payout']; J=int(row.axis); pop=int(row.pop) if row.pop==row.pop else 99
    po=[int(h['umaban']) for h in sorted(r['horses'],key=lambda h:(h.get('odds') or 999)) if int(h['umaban'])!=J]
    ai=[int(u) for u in g.sort_values('p3',ascending=False).umaban if u!=J]
    jq=g[g.umaban==J]; tev=float(jq.q.iloc[0]*jq.odds.iloc[0]) if len(jq) else 0
    s=lambda *x:'-'.join(map(str,x)); ss=lambda *x:'-'.join(map(str,sorted(x)))
    T={'単勝（穴馬）':[['単勝',str(J),100]],
       '3連複 穴-AI上位4頭（6点）':[['三連複',ss(J,a,b),100] for a,b in itertools.combinations(ai[:4],2)],
       '3連単 穴1着固定-AI上位3頭（6点）':[['三連単',s(J,a,b),100] for a,b in itertools.permutations(ai[:3],2)],
       '3連単 穴1着固定-AI上位4頭（12点）':[['三連単',s(J,a,b),100] for a,b in itertools.permutations(ai[:4],2)],
       '3連単 穴1着固定-AI上位5頭（20点）':[['三連単',s(J,a,b),100] for a,b in itertools.permutations(ai[:5],2)],
       '3連単 穴1着固定-人気上位3頭（6点）':[['三連単',s(J,a,b),100] for a,b in itertools.permutations(po[:3],2)],
       '3連単 穴1着固定-人気上位4頭（12点）':[['三連単',s(J,a,b),100] for a,b in itertools.permutations(po[:4],2)],
       '3連単 穴1・2着-AI上位4頭（24点）':[['三連単',s(*p),100] for a,b in itertools.permutations(ai[:4],2) for p in [(J,a,b),(a,J,b)]],
    }
    cats=[row.cat]
    if row.cat=='穴' and tev>=1.0: cats.append('穴（単勝期待値1.0以上）')
    if row.cat=='穴' and tev>=1.3: cats.append('穴（単勝期待値1.3以上）')
    if row.cat=='穴' and 4<=pop<=6: cats.append('穴（4〜6番人気）')
    for c in cats:
        for k,t in T.items():
            inv,ret,_=S.settle(t,pay); a=res[(c,k)][row.fold]; a[0]+=1;a[1]+=inv;a[2]+=ret;a[3]+=int(ret>0)
            if ret: wins[(c,k)].append(ret)
F=sorted(sel.fold.unique()); rows=[]
for (c,k),fd in res.items():
    n=sum(v[0] for v in fd.values()); inv=sum(v[1] for v in fd.values()); ret=sum(v[2] for v in fd.values()); hit=sum(v[3] for v in fd.values())
    w=sorted(wins[(c,k)],reverse=True)
    rows.append([c,k,n,round(hit/n*100,1),round(ret/inv*100,1),round((ret-sum(w[:3]))/inv*100,1),' / '.join(str(round(fd[f][2]/fd[f][1]*100)) if fd[f][1] else '-' for f in F)])
O=pd.DataFrame(rows,columns=['区分','買い方','R','的中率','回収率','上位3回除く','期間別']); O.to_pickle(f'/tmp/co/tan_{TAG}.pkl')
pd.set_option('display.width',250); print(O.sort_values(['区分','回収率'],ascending=[True,False]).to_string(index=False))
