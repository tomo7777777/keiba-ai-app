import sys, numpy as np, pandas as pd
from run import run, races
from multiprocessing import Pool
N=len(races)
CF=[('基準',{}),('本命EV1.5',dict(hon_th=1.5)),('本命EV2.0',dict(hon_th=2.0)),('穴EV1.2',dict(ana_th=1.2)),('穴EV1.5',dict(ana_th=1.5)),('穴EV2.0',dict(ana_th=2.0)),('穴 1人気3.0',dict(fav_min=3.0)),('穴 1人気3.5',dict(fav_min=3.5)),('穴EV1.5+1人気3.0',dict(ana_th=1.5,fav_min=3.0))]
def job(a):
    sc,name,kw,seed=a
    O=pd.DataFrame(run(sc,seed,**kw),columns=['race_id','fold','kind','pts','wret','tpts','tret']); O['scale']=sc;O['cfg']=name;O['seed']=seed; return O
if __name__=='__main__':
    scales=[float(x) for x in sys.argv[1].split(',')]; seeds=range(int(sys.argv[2]))
    jobs=[(sc,n,k,s) for sc in scales for n,k in CF for s in seeds]
    with Pool(2) as p: O=pd.concat(p.map(job,jobs))
    O.to_pickle('/tmp/sim/sweep.pkl')
    for (sc,cfg,kind),g in O.groupby(['scale','cfg','kind'],sort=False):
        per=g.groupby('seed').apply(lambda x:x.wret.sum()/x.pts.sum()); tt=g[g.tpts>0]; pt=tt.groupby('seed').apply(lambda x:x.tret.sum()/max(x.tpts.sum(),1))
        fo='/'.join(f"{x.wret.sum()/x.pts.sum():.0f}" for _,x in g.groupby('fold'))
        print(f"{sc} {cfg:14s} {kind}: {len(g)/len(seeds)/N*100:4.1f}%/R  ワイド {g.wret.sum()/g.pts.sum():5.1f}% (seed幅 {per.min():.0f}-{per.max():.0f}, 期間 {fo})  3連単 {tt.tret.sum()/max(tt.tpts.sum(),1):5.1f}% ({pt.min():.0f}-{pt.max():.0f})")
