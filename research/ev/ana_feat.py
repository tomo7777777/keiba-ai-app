import sys, gzip, json, glob, itertools, collections, pandas as pd, numpy as np
sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts'); import strategy as S
D='/home/user/workspace/keiba-ai-app/data'
files=sorted(glob.glob(f'{D}/archive/nar/*.gz')+glob.glob(f'{D}/nar/history/*.gz'))
races={}
for f in files:
    for l in gzip.open(f,'rt'):
        r=json.loads(l); races[r['race_id']]=r
RS=sorted(races.values(),key=lambda r:(r['date'],r['race_id']))
# expanding jockey stats (before date)
js=collections.defaultdict(lambda:[0,0,0,0]); JST={}  # n, top3, win, tanret
day=None; buf=[]
def flush():
    for jid,t3,w,tr in buf:
        a=js[jid]; a[0]+=1;a[1]+=t3;a[2]+=w;a[3]+=tr
    buf.clear()
for r in RS:
    if r['date']!=day: flush(); day=r['date']
    tan=dict((int(k),v) for k,v in r['payout'].get('単勝',[]) if str(k).isdigit())
    for h in r['horses']:
        jid=h.get('jockey_id'); 
        if not jid: continue
        JST[(r['race_id'],int(h['umaban']))]=tuple(js[jid])
        rk=h.get('rank') or 99
        buf.append((jid,int(rk<=3),int(rk==1),tan.get(int(h['umaban']),0)))
flush()
sel=pd.read_pickle('ev_rows_sel.pkl'); sel['race_id']=sel.race_id.astype(str); sel=sel[sel.cat=='穴']
H=pd.concat([pd.read_pickle(f'/tmp/ana_nar_{t}.pkl') for t in ('all','ext')]); H=H[H.umaban.notna()]
H['umaban']=H.umaban.astype(int); H['race_id']=H.race_id.astype(str); HG=dict(list(H.groupby('race_id')))
rows=[]
for row in sel.itertuples():
    r=races.get(row.race_id); g=HG.get(row.race_id)
    if r is None or g is None: continue
    pay=r['payout']; J=int(row.axis); jq=g[g.umaban==J]
    if not len(jq): continue
    ai=[int(u) for u in g.sort_values('p3',ascending=False).umaban if u!=J]
    s=lambda *x:'-'.join(map(str,x))
    t6=[['三連単',s(J,a,b),100] for a,b in itertools.permutations(ai[:3],2)]
    i6,r6,_=S.settle(t6,pay) if '三連単' in pay else (600,0,0)
    it,rt,_=S.settle([['単勝',str(J),100]],pay)
    hh={int(h['umaban']):h for h in r['horses']}; h=hh.get(J,{})
    st=JST.get((row.race_id,J),(0,0,0,0))
    # jockey rank within race by top3 rate
    rates={u:(lambda a:(a[1]+3)/(a[0]+10))(JST.get((row.race_id,u),(0,0,0,0))) for u in hh}
    jr=sorted(rates.values(),reverse=True).index(rates[J])+1
    q=float(jq.q.iloc[0]); o=float(jq.odds.iloc[0])
    rows.append(dict(race_id=row.race_id,fold=row.fold,place=r['place'],n=r['n'],dist=r['distance'],cls=r.get('class'),going=r.get('going'),
        pop=row.pop,aodds=o,winev=q*o,ratio=float(jq.p3.iloc[0]/jq.m3.iloc[0]),airank=int(jq['rank'].iloc[0]) if jq['rank'].iloc[0]==jq['rank'].iloc[0] else 99,
        jn=st[0],j3=(st[1]+3)/(st[0]+10),jwin=(st[2]+1)/(st[0]+10),jroi=st[3]/max(st[0]*100,1) if st[0]>=30 else np.nan,jrank=jr,
        wage=h.get('age'),wd=h.get('wdiff'),
        w_pts=row.pts,w_ret=row.ret,t_ret=r6,t_pts=i6/100,s_ret=rt))
O=pd.DataFrame(rows); O.to_pickle('ana_feat.pkl'); print(len(O)); print(O.describe().T)
