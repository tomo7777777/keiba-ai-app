import pandas as pd, numpy as np
O=pd.read_pickle('ana_feat.pkl'); F=sorted(O.fold.unique())
def roi(g,r,p): return g[r].sum()/max(g[p].sum()*100 if p!='one' else len(g)*100,1)*100
def line(name,g):
    w=roi(g,'w_ret','w_pts'); t=roi(g,'t_ret','t_pts'); s=roi(g,'s_ret','one')
    pf=lambda r,p:'/'.join(f"{roi(g[g.fold==f],r,p):.0f}" for f in F)
    return f"{name:22s} {len(g):5d}R  ワイド{w:5.0f}[{pf('w_ret','w_pts')}]  3単{t:5.0f}[{pf('t_ret','t_pts')}]  単{s:4.0f}[{pf('s_ret','one')}]"
print(line('全体',O))
for c in ['place']:
    for k,g in O.groupby(c):
        if len(g)>=300: print(line(f'{c}={k}',g))
for c in ['n','dist','pop','aodds','winev','ratio','airank','j3','jwin','jroi','jrank','cls','wd']:
    try: q=pd.qcut(O[c],5,duplicates='drop')
    except Exception as e: continue
    for k,g in O.groupby(q,observed=True): print(line(f'{c} {k}',g))
