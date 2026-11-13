"""地方の馬に、中央での過去成績を足す"""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/workspace/keiba-ai-app/scripts')
os.environ['KEIBA_DATA'] = '/home/user/workspace/keiba-ai-app/data'
import features as F
jb = F.build_base(F.load_history()); jb = jb[jb['rank'].notna()][['horse_id', 'date', 'rnorm', 'top3', 'class', 'popn', 'si', 'l3rel']]
n = pd.read_pickle('/home/user/workspace/keiba-ai-app/data/nar/train_cache.pkl')[['race_id', 'umaban', 'horse_id', 'date']]
n = n[n.horse_id.isin(set(jb.horse_id))]
jb = jb.sort_values('date'); G = {k: g for k, g in jb.groupby('horse_id')}
rows = []
for r in n.itertuples():
    h = G[r.horse_id]; h = h[h.date < r.date]
    if not len(h): continue
    t = h.tail(5)
    rows.append((r.race_id, r.umaban, len(h), h.top3.mean(), h.rnorm.iloc[-1], t.rnorm.min(), t.rnorm.mean(), h['class'].iloc[-1],
                 h['class'].max(), (r.date - h.date.iloc[-1]).days, t.popn.mean(), t.si.max(), t.l3rel.mean()))
X = pd.DataFrame(rows, columns=['race_id', 'umaban', 'jr_n', 'jr_top3', 'jr_rn_last', 'jr_rn_best5', 'jr_rn_avg5', 'jr_class_last',
                                'jr_class_max', 'jr_days', 'jr_pop5', 'jr_si_max5', 'jr_l3_5'])
E = pd.read_pickle('/tmp/extra_nar.pkl').merge(X, on=['race_id', 'umaban'], how='left')
E.to_pickle('/tmp/extra_narjx.pkl'); print(len(X), E.shape)
