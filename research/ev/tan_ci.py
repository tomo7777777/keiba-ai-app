import sys,gzip,json,glob,itertools,numpy as np,pandas as pd
sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts'); import strategy as S
D='/home/user/workspace/keiba-ai-app/data'
sel=pd.read_pickle('ev_rows_sel.pkl'); sel['race_id']=sel.race_id.astype(str); need=set(sel.race_id); R={}
for f in glob.glob(f'{D}/archive/nar/*.gz')+glob.glob(f'{D}/nar/history/*.gz'):
    for l in gzip.open(f,'rt'):
        r=json.loads(l)
        if r['race_id'] in need: R[r['race_id']]=r
H=pd.concat([pd.read_pickle('/tmp/ana_nar_all.pkl'),pd.read_pickle('/tmp/ana_nar_ext.pkl')]); H=H[H.umaban.notna()]
H['umaban']=H.umaban.astype(int); H['race_id']=H.race_id.astype(str); HG=dict(list(H.groupby('race_id')))
out={}
for cat,k in [('本命',4),('本命',3),('穴',3)]:
    v=[];pays=[]
    for row in sel[sel.cat==cat].itertuples():
        r=R.get(row.race_id); g=HG.get(row.race_id)
        if r is None or g is None or '三連単' not in r['payout']: continue
        J=int(row.axis); ai=[int(u) for u in g.sort_values('p3',ascending=False).umaban if u!=J]
        t=[['三連単',f'{J}-{a}-{b}',100] for a,b in itertools.permutations(ai[:k],2)]
        inv,ret,_=S.settle(t,r['payout']); v.append((inv,ret))
        if ret: pays.append(ret)
    a=np.array(v); rng=np.random.default_rng(0); bs=[]
    for _ in range(4000):
        i=rng.integers(0,len(a),len(a)); bs.append(a[i,1].sum()/a[i,0].sum()*100)
    print(cat,k,len(a),round(a[:,1].sum()/a[:,0].sum()*100,1),np.percentile(bs,[2.5,97.5]).round(0),'配当中央値',np.median(pays),'最大',max(pays), '1日あたりR', round(len(a)/ (sel[sel.cat==cat].race_id.str[:8].nunique()),1))
