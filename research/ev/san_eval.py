import sys, numpy as np, pandas as pd
R=pd.read_pickle(f'/tmp/co/san_rows_{sys.argv[1]}.pkl'); R['p']=R.ev/R.odds
folds=sorted(R.fold.unique()); rng=np.random.default_rng(0)
def rep(name,x):
    if x.empty: return
    rr=x.groupby('race_id').agg(ret=('pay','sum'),pts=('pay','size'),hit=('hit','max'),fold=('fold','first'))
    v=rr[['ret','pts']].values; bs=[(lambda s:s[:,0].sum()/s[:,1].sum())(v[rng.integers(0,len(v),len(v))]) for _ in range(300)]
    per='/'.join(f"{rr[rr.fold==f].ret.sum()/max(rr[rr.fold==f].pts.sum(),1):.0f}" for f in folds)
    print(f"{name}: {len(rr)}R 平均{rr.pts.mean():.1f}点 的中率{rr.hit.mean()*100:.1f}% 回収率{rr.ret.sum()/rr.pts.sum():.1f}% [{per}] 95%幅{np.percentile(bs,2.5):.0f}-{np.percentile(bs,97.5):.0f} 中央オッズ{x.odds.median():.0f}")
for cat in ('本命','穴'):
    g=R[R.cat==cat]
    rep(f'{cat} 全部買い',g)
    for th in (0.8,1.0,1.2):
        for N in (3,6):
            rep(f'{cat} 期待値{th}以上から確率の高い順{N}点',g[g.ev>=th].sort_values('p',ascending=False).groupby('race_id').head(N))
    rep(f'{cat} 確率の高い順6点（期待値見ない）',g.sort_values('p',ascending=False).groupby('race_id').head(6))
