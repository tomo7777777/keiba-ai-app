import json,glob,numpy as np,collections
def load(c,base):
    S=collections.defaultdict(dict)
    for f in glob.glob(f'{base}/snap/*.jsonl'):
        for l in open(f):
            d=json.loads(l); S[d['race_id']].setdefault(d['tag'],d)
    return S
out={}
for c,base in [('nar','data/nar'),('jra','data')]:
    S=load(c,base); W=[];WD=[]
    for rid,s in S.items():
        if 'ev' in s and 'final' in s:
            e,f=s['ev'],s['final']
            for k,v in e['win'].items():
                if v and f['win'].get(k): W.append((v,f['win'][k]))
            for k,v in e['wide'].items():
                fv=f['wide'].get(k)
                if v and fv:
                    a,b=k.split('-'); WD.append((v,fv,e['win'].get(a),e['win'].get(b),f['win'].get(a),f['win'].get(b)))
    # lock(-40) vs final win
    L=[]
    for fn in glob.glob(f'docs/data/myomi/{c}/days/*.json'):
        for r in json.load(open(fn))['races']:
            for h in r.get('horses',[]):
                if h.get('odds') and h.get('final_odds'): L.append((h['odds'],h['final_odds']))
    W=np.array(W);L=np.array(L)
    print(c,'snap races',sum(1 for s in S.values() if 'ev' in s and 'final' in s),'win pairs',len(W),'wide pairs',len(WD),'lock pairs',len(L))
    for nm,A in (('-15',W),('-40',L)):
        if len(A)==0: continue
        r=np.log(A[:,1]/A[:,0])
        for lo,hi in ((1,3),(3,8),(8,20),(20,60),(60,1e4)):
            m=(A[:,0]>=lo)&(A[:,0]<hi)
            if m.sum()>3: print(f'  {nm} win {lo}-{hi}: n={m.sum()} mean={r[m].mean():+.3f} sd={r[m].std():.3f}')
    if WD:
        A=np.array([w for w in WD if None not in w],float); r=np.log(A[:,1]/A[:,0]); ew=(np.log(A[:,4]/A[:,2])+np.log(A[:,5]/A[:,3]))/2
        b=np.polyfit(ew,r,1); res=r-np.polyval(b,ew)
        print(f'  wide: sd={r.std():.3f} mean={r.mean():+.3f}  slope on win drift={b[0]:.2f} resid sd={res.std():.3f}')
        for lo,hi in ((1,3),(3,8),(8,20),(20,60),(60,1e4)):
            m=(A[:,0]>=lo)&(A[:,0]<hi)
            if m.sum()>3: print(f'    wide {lo}-{hi}: n={m.sum()} mean={r[m].mean():+.3f} sd={r[m].std():.3f} resid={res[m].std():.3f}')
