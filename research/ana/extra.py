"""穴馬探し用の追加特徴（無料データ＝既存の結果データから）
1) 当日の馬場バイアス（同じ日・同じ場・同じ馬場の、それより前のレース）
2) 前走の内容（着差・上がり順位・展開/馬場バイアスとの逆行・前走メンバーの強さ）
3) 展開（逃げ馬の数・単騎逃げ）"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/workspace/keiba-ai-app/scripts'); import features as F
TAG = sys.argv[1]
base = F.build_base(F.load_history())
b = base[base['rank'].notna()].copy()
b['R'] = b.race_id.str[-2:].astype(int)
b['un'] = b.umaban / b.n
b['ltr'] = b.groupby('race_id').last3f.rank(pct=True)
b['margin'] = (b.time - b.groupby('race_id').time.transform('min')).clip(0, 5)
# レースごとのバイアス：3着内馬の平均位置 − 全体平均（マイナス＝前/内が有利）
g = b.groupby('race_id')
rs = pd.DataFrame({'date': g.date.first(), 'place': g.place.first(), 'surface': g.surface.first(), 'R': g.R.first()})
t3 = b[b['rank'] <= 3].groupby('race_id')
rs['rfb'] = t3.fc.mean() - g.fc.mean()
rs['rib'] = t3.un.mean() - g.un.mean()
rs = rs.sort_values(['date', 'place', 'surface', 'R'])
k = ['date', 'place', 'surface']
for c in ['rfb', 'rib']:
    cs = rs.groupby(k)[c].cumsum() - rs[c].fillna(0)
    cnt = rs.groupby(k).cumcount()
    rs['d_' + c] = (cs / cnt.replace(0, np.nan))          # その日の前のレースまで
    rs['dall_' + c] = rs.groupby(k)[c].transform('mean')  # その日全体（前走用）
rs['d_k'] = rs.groupby(k).cumcount()
b = b.merge(rs[['rfb', 'rib', 'd_rfb', 'd_rib', 'dall_rfb', 'dall_rib', 'd_k']], left_on='race_id', right_index=True, how='left')
# 前走メンバーの強さ（そのレース時点での各馬の過去指数平均の平均）
d = pd.read_pickle(f"{F.BASE}/train_cache.pkl")
fs = d.groupby('race_id').h_si_avg3.mean().rename('fstr')
b = b.merge(fs, left_on='race_id', right_index=True, how='left')
b = b.sort_values(['horse_id', 'date'])
b['fcc'] = b.fc - 0.5; b['unc'] = b.un - 0.5
b['ag_day'] = b.fcc * (-b.dall_rfb)      # プラス＝その日の有利な位置と逆にいた
b['ag_race'] = b.fcc * (-b.rfb)
b['ag_in'] = b.unc * (-b.dall_rib)
gh = b.groupby('horse_id')
prev = {}
for c in ['margin', 'ltr', 'fc', 'ag_day', 'ag_race', 'ag_in', 'fstr', 'rnorm']:
    prev['p1_' + c] = gh[c].shift(1)
for c in ['margin', 'ag_day', 'ag_race', 'fstr']:
    s = gh[c].shift(1)
    prev['p3m_' + c] = s.groupby(b.horse_id).transform(lambda x: x.rolling(3, min_periods=1).mean())
prev['p3min_margin'] = gh['margin'].shift(1).groupby(b.horse_id).transform(lambda x: x.rolling(3, min_periods=1).min())
P = pd.DataFrame(prev, index=b.index)
P['p1_margin_x_str'] = P.p1_margin - P.p1_fstr     # 強い相手に僅差＝プラス評価になりうる
out = pd.concat([b[['race_id', 'umaban', 'd_rfb', 'd_rib', 'd_k']], P], axis=1)
# 展開：今回のメンバーの先行力
x = d[['race_id', 'umaban', 'h_fc_avg5', 'h_si_avg3']].copy()
x['n_front'] = x.groupby('race_id').h_fc_avg5.transform(lambda s: (s < 0.25).sum())
x['fc_rank'] = x.groupby('race_id').h_fc_avg5.rank(method='min')
srt = x.groupby('race_id').h_fc_avg5.transform(lambda s: s.nsmallest(2).iloc[-1] if s.notna().sum() > 1 else np.nan)
x['lone'] = ((x.fc_rank == 1) & (srt - x.h_fc_avg5 > 0.12)).astype(int)
x['cur_fstr'] = x.groupby('race_id').h_si_avg3.transform('mean')
out = out.merge(x[['race_id', 'umaban', 'n_front', 'fc_rank', 'lone', 'cur_fstr']], on=['race_id', 'umaban'], how='right')
out['str_drop'] = out.p1_fstr - out.cur_fstr
out.to_pickle(f'/tmp/extra_{TAG}.pkl'); print(TAG, out.shape, out.notna().mean().round(2).to_dict())
