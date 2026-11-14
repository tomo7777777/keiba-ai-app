import pandas as pd, numpy as np
exec(open('ana_split2.py').read().split("ndays=")[0])
H=pd.concat([pd.read_pickle(f'/tmp/ana_nar_{t}.pkl') for t in ('all','ext')]); H=H[H.umaban.notna()]; H['race_id']=H.race_id.astype(str)
fav=H.groupby('race_id').odds.min(); sec=H.groupby('race_id').odds.apply(lambda s:s.nsmallest(2).iloc[-1])
O['fav']=O.race_id.map(fav); O['sec']=O.race_id.map(sec)
print(O[['fav','winev']].corr())
for lo,hi in [(1,1.5),(1.5,2),(2,2.5),(2.5,3),(3,4),(4,99)]:
    g=O[(O.fav>=lo)&(O.fav<hi)]; print(line(f'1番人気{lo}-{hi}倍',g),f" 除3 ワ{ex(g,'w_ret','w_pts'):.0f} 3単{ex(g,'t_ret','t_pts'):.0f} 1日{len(g)/364:.1f}R")
for fv in [2.0,2.5,3.0]:
  for nn in [0,10,11,12]:
    g=O[(O.fav>=fv)&(O.n>=nn)]; print(line(f'1人気{fv}倍以上&{nn}頭以上',g),f" 除3 ワ{ex(g,'w_ret','w_pts'):.0f} 3単{ex(g,'t_ret','t_pts'):.0f} 1日{len(g)/364:.1f}R")
rng=np.random.default_rng(0)
for nm,m in [('2.5&12',(O.fav>=2.5)&(O.n>=12)),('2.5&全',(O.fav>=2.5)),('現行',O.fav>0)]:
    g=O[m]; 
    for r,p in [('w_ret','w_pts'),('t_ret','t_pts')]:
        R=g[r].values; P=g[p].values*100; bs=[]
        for _ in range(2000):
            i=rng.integers(0,len(g),len(g)); bs.append(R[i].sum()/P[i].sum()*100)
        hit=(g[r]>0).mean()*100
        print(nm,r,len(g),f"的中{hit:.1f}% 回収{R.sum()/P.sum()*100:.0f} 95%幅{np.percentile(bs,2.5):.0f}-{np.percentile(bs,97.5):.0f} 100超の確率{np.mean(np.array(bs)>100)*100:.0f}%")
