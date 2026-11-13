import sys, pandas as pd, collections
sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts'); import features as F, strategy as S
TAG=sys.argv[1]; te=pd.read_pickle(f'/tmp/ana_{TAG}_base.pkl'); te=te[te.umaban.notna()]
r=collections.defaultdict(lambda:[0,0])
for rid,g in te.groupby('race_id'):
    if len(g)<8: continue
    pay=F.get_race(rid)['payout']
    for row in g.itertuples():
        for lo,hi in [(1,3),(3,10),(10,30),(30,100),(100,9999)]:
            if lo<=row.odds<hi:
                for k in ['単勝','複勝']:
                    inv,ret,_=S.settle([[k,str(int(row.umaban)),100]],pay); x=r[(f'{lo}-{hi}',k)]; x[0]+=inv; x[1]+=ret
for k,v in sorted(r.items()): print(TAG,k,round(v[1]/v[0]*100,1))
