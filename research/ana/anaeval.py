"""穴馬の買い方別 回収率（各レース、条件内でズレ最大の穴馬1頭）"""
import sys, itertools, collections, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/workspace/keiba-ai-app/scripts'); import features as F, strategy as S
TAG, VAR = sys.argv[1], sys.argv[2]
te = pd.read_pickle(f'/tmp/ana_{TAG}_{VAR}.pkl'); te = te[te.umaban.notna()].copy(); te['umaban'] = te.umaban.astype(int)
te['gap'] = te.p3 / te.m3; te['ork'] = te.groupby('race_id').odds.rank(method='first')
te['month'] = te.date.dt.to_period('M')
res = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0]))
mon = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
wins = collections.defaultdict(list)
TH = [1.2, 1.3, 1.5, 1.8, 2.2]; BANDS = [(10, 30), (10, 50), (20, 100)]
for rid, g in te.groupby('race_id'):
    if len(g) < 8: continue
    pay = F.get_race(rid)['payout']; f = g.fold.iloc[0]; mo = g.month.iloc[0]
    pop = [int(u) for u in g.sort_values('odds').umaban]
    ai = [int(u) for u in g.sort_values('p3', ascending=False).umaban]
    for lo, hi in BANDS:
        c = g[(g.odds >= lo) & (g.odds < hi)]
        if c.empty: continue
        j = c.loc[c.gap.idxmax()]
        for th in TH:
            if j.gap < th: continue
            J = int(j.umaban); s = lambda *x: "-".join(map(str, sorted(x)))
            pp = [x for x in pop if x != J]; aa = [x for x in ai if x != J]
            T = {'単勝': [["単勝", str(J), 100]], '複勝': [["複勝", str(J), 100]],
                 'ワイド 穴-人気上位3頭': [["ワイド", s(J, x), 100] for x in pp[:3]],
                 'ワイド 穴-AI上位3頭': [["ワイド", s(J, x), 100] for x in aa[:3]],
                 '馬連 穴-人気上位3頭': [["馬連", s(J, x), 100] for x in pp[:3]],
                 '3連複 穴-人気上位3頭(3点)': [["三連複", s(J, x, y), 100] for x, y in itertools.combinations(pp[:3], 2)],
                 '3連複 穴-人気上位4頭(6点)': [["三連複", s(J, x, y), 100] for x, y in itertools.combinations(pp[:4], 2)]}
            for k, t in T.items():
                inv, ret, _ = S.settle(t, pay); key = (f"{lo}-{hi}倍", th, k); a = res[key][f]
                a[0] += 1; a[1] += inv; a[2] += ret; a[3] += int(ret > 0)
                m = mon[key][mo]; m[0] += inv; m[1] += ret
                if ret: wins[key].append(ret)
ALLF = sorted(te.fold.unique())
rows = []
for key, fd in res.items():
    fs = ALLF; n = sum(fd[x][0] for x in fs); inv = sum(fd[x][1] for x in fs); ret = sum(fd[x][2] for x in fs)
    hit = sum(fd[x][3] for x in fs); w = sorted(wins[key], reverse=True)
    mm = mon[key]; mup = sum(v[1] >= v[0] for v in mm.values())
    rows.append([*key, n, round(hit / n * 100, 1), round(ret / inv * 100, 1)] + [round(fd[x][2] / max(fd[x][1], 1) * 100) for x in fs]
                + [round((ret - sum(w[:3])) / inv * 100, 1), f"{mup}/{len(mm)}"])
cols = ['オッズ帯', 'ズレ', '買い方', 'R', '的中率', '回収率'] + [f"期{i+1}" for i in range(len(ALLF))] + ['上位3除く', '月+']
O = pd.DataFrame(rows, columns=cols); O.to_pickle(f'/tmp/anaeval_{TAG}_{VAR}.pkl')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
print(O[O.R >= 60].sort_values('回収率', ascending=False).head(25).to_string(index=False))
