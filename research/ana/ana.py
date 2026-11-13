"""穴馬AIの検証：市場の確率を出発点に、ズレを学習（基本特徴 vs 追加特徴）"""
import sys, os, numpy as np, pandas as pd, lightgbm as lgb
sys.path.insert(0, '/home/user/workspace/keiba-ai-app/scripts'); import features as F, myomi as MY
TAG, WARM, FOLDS, VAR = sys.argv[1], sys.argv[2], [tuple(x.split(':')) for x in sys.argv[3].split(',')], sys.argv[4]
d = pd.read_pickle(f"{F.BASE}/train_cache.pkl"); d = d[d.odds.notna() & (d.odds > 0)].copy()
d = F.add_market(d, d.odds.values); d = MY.add_market_places(d)
d['top3'] = (d['rank'] <= 3).astype(int)
base_feats = [c for c in d.columns if c not in MY.DROP]
feats = list(base_feats)
if VAR in ('ext', 'ped', 'all'):
    X = pd.read_pickle(f'/tmp/extra_{TAG}' + ('jx' if os.environ.get('JX') else '') + '.pkl')
    d = d.merge(X, on=['race_id', 'umaban'], how='left')
    d['x_front'] = (0.5 - d.h_fc_avg5) * (-d.d_rfb)
    d['x_inner'] = (0.5 - d.umaban_n) * (-d.d_rib)
    feats += [c for c in X.columns if c not in ('race_id', 'umaban')] + ['x_front', 'x_inner']
if VAR in ('ped', 'all'):
    import json
    ped = {r['id']: r for r in map(json.loads, open('/home/user/workspace/keiba-ai-app/data/ped.jsonl'))}
    for k in ['sire', 'bms', 'ss']:
        d[k] = d.horse_id.map(lambda h: (ped.get(h) or {}).get(k))
    # 種牡馬ごとの成績（その日より前のデータだけで、芝ダ・距離帯別）を目的変数リークなしで計算
    d = d.sort_values('date')
    d['dband'] = (d.distance // 400).clip(3, 7)
    d['res'] = d.top3 - d.m3   # 人気以上に走った分
    for k in ['sire', 'bms', 'ss']:
        for grp, nm in [([k], ''), ([k, 'surface'], '_s'), ([k, 'surface', 'dband'], '_sd'), ([k, 'surface', 'going'], '_sg')]:
            g = d.groupby(grp + ['date'], dropna=False).res.agg(['sum', 'count']).reset_index()
            g[['cs', 'cc']] = g.groupby(grp, dropna=False)[['sum', 'count']].cumsum().values
            g['cs'] -= g['sum']; g['cc'] -= g['count']
            g[f'{k}{nm}_res'] = g.cs / (g.cc + 30); g[f'{k}{nm}_n'] = g.cc
            d = d.merge(g[grp + ['date', f'{k}{nm}_res', f'{k}{nm}_n']], on=grp + ['date'], how='left')
            feats += [f'{k}{nm}_res', f'{k}{nm}_n']
lg = lambda p: np.log(p / (1 - p))
P = dict(objective="binary", learning_rate=0.02, num_leaves=31, min_data_in_leaf=200, feature_fraction=0.7,
         bagging_fraction=0.8, bagging_freq=1, lambda_l2=5, verbose=-1)
outs = []
for a, b in FOLDS:
    tr = d[(d.date >= WARM) & (d.date < a)]; te = d[(d.date >= a) & (d.date < b)].copy()
    m = lgb.train(P, lgb.Dataset(tr[feats].astype(float), tr.top3, init_score=lg(tr.m3)), 300)
    te['p3'] = 1 / (1 + np.exp(-(lg(te.m3) + m.predict(te[feats].astype(float), raw_score=True))))
    te['fold'] = a; outs.append(te[['race_id', 'date', 'umaban', 'odds', 'q', 'm3', 'p3', 'rank', 'fold']])
    if a == FOLDS[-1][0]:
        imp = pd.Series(m.feature_importance('gain'), feats).sort_values(ascending=False)
        print(imp.head(25).round(0).to_dict())
o = pd.concat(outs); o.to_pickle(f'/tmp/ana_{TAG}_{VAR}.pkl')
y = (o['rank'] <= 3).astype(int)
ll = lambda p, m: -np.mean(y[m] * np.log(p[m]) + (1 - y[m]) * np.log(1 - p[m]))
for lo, hi in [(1, 999), (10, 999), (10, 50)]:
    msk = (o.odds >= lo) & (o.odds < hi)
    print(TAG, VAR, f'{lo}-{hi}倍', 'n', msk.sum(), '市場', round(ll(o.m3, msk), 5), 'AI', round(ll(o.p3, msk), 5),
          '改善%', round((ll(o.m3, msk) - ll(o.p3, msk)) / ll(o.m3, msk) * 100, 2))
