"""事前に決めた条件だけを、まだ見ていない古い期間で検証する（後から条件を選ばない）"""
import sys, itertools, collections, pandas as pd
sys.path.insert(0, '/home/user/workspace/keiba-ai-app/scripts'); import features as F, strategy as S
TAG, VAR = sys.argv[1], sys.argv[2]
te = pd.read_pickle(f'/tmp/ana_{TAG}_{VAR}.pkl'); te = te[te.umaban.notna()].copy(); te['umaban'] = te.umaban.astype(int)
te['gap'] = te.p3 / te.m3; te['ork'] = te.groupby('race_id').odds.rank(method='first')
s = lambda *x: "-".join(map(str, sorted(x)))
# (名前, 最少頭数, オッズ下限, 上限, ズレ基準, 1番人気除外, 買い方)
C = {'myomi': [  # 妙味軸（いま本番で使っている条件）
        ('妙味軸 複勝', 7, 3, 10, 1.3, True, 'fuku'), ('妙味軸 ワイド軸-相手3', 7, 3, 10, 1.3, True, 'wideai3'),
        ('妙味軸 馬連軸-相手5', 7, 3, 10, 1.3, True, 'umaai5'), ('妙味軸 3連複軸-相手4', 7, 3, 10, 1.3, True, 'sanai4')],
     'ana': [  # 穴馬（前回 有望・偶然かもと伝えた条件）
        ('中央候補 単勝 10-30倍 ズレ1.2', 8, 10, 30, 1.2, False, 'tan'),
        ('地方候補 3連複 穴-人気上位3頭 10-50倍 ズレ1.5', 8, 10, 50, 1.5, False, 'sanpop3'),
        ('地方候補 ワイド 穴-人気上位3頭 10-50倍 ズレ1.5', 8, 10, 50, 1.5, False, 'widepop3'),
        ('偶然? 地方 単勝 10-30倍 ズレ1.8 (147.7%)', 8, 10, 30, 1.8, False, 'tan'),
        ('偶然? 地方 3連複6点 20-100倍 ズレ2.2 (196.8%)', 8, 20, 100, 2.2, False, 'sanpop4'),
        ('偶然? 中央 3連複3点 20-100倍 ズレ1.8 (118.6%)', 8, 20, 100, 1.8, False, 'sanpop3'),
        ('偶然? 地方 ワイド 穴-人気上位3頭 10-50倍 ズレ1.8 (105.2%)', 8, 10, 50, 1.8, False, 'widepop3'),
        ('偶然? 中央 単勝 10-30倍 ズレ1.8 (116.3%)', 8, 10, 30, 1.8, False, 'tan')]}
conds = C['myomi'] if VAR == 'base' else C['ana']
res = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0])); wins = collections.defaultdict(list)
for rid, g in te.groupby('race_id'):
    r = F.get_race(rid)
    if not r: continue
    pay = r['payout']; f = g.fold.iloc[0]
    pop = [int(u) for u in g.sort_values('odds').umaban]; ai = [int(u) for u in g.sort_values('p3', ascending=False).umaban]
    for name, mn, lo, hi, th, nofav, kind in conds:
        if len(g) < mn: continue
        c = g[(g.odds >= lo) & (g.odds < hi)]
        if nofav: c = c[c.ork >= 2]
        if c.empty: continue
        j = c.loc[c.gap.idxmax()]
        if j.gap < th: continue
        J = int(j.umaban); pp = [x for x in pop if x != J]; aa = [x for x in ai if x != J]
        T = {'fuku': [["複勝", str(J), 100]], 'tan': [["単勝", str(J), 100]],
             'wideai3': [["ワイド", s(J, x), 100] for x in aa[:3]], 'umaai5': [["馬連", s(J, x), 100] for x in aa[:5]],
             'sanai4': [["三連複", s(J, x, y), 100] for x, y in itertools.combinations(aa[:4], 2)],
             'widepop3': [["ワイド", s(J, x), 100] for x in pp[:3]],
             'sanpop3': [["三連複", s(J, x, y), 100] for x, y in itertools.combinations(pp[:3], 2)],
             'sanpop4': [["三連複", s(J, x, y), 100] for x, y in itertools.combinations(pp[:4], 2)]}[kind]
        inv, ret, _ = S.settle(T, pay); a = res[name][f]; a[0] += 1; a[1] += inv; a[2] += ret; a[3] += int(ret > 0)
        if ret: wins[name].append(ret)
FS = sorted(te.fold.unique()); rows = []
for name, *_ in conds:
    fd = res[name]; n = sum(fd[x][0] for x in FS); inv = sum(fd[x][1] for x in FS); ret = sum(fd[x][2] for x in FS); hit = sum(fd[x][3] for x in FS)
    if not n: rows.append([name, 0]); continue
    w = sorted(wins[name], reverse=True)
    rows.append([name, n, round(hit / n * 100, 1), round(ret / inv * 100, 1), '/'.join(str(round(fd[x][2] / fd[x][1] * 100)) if fd[x][1] else '-' for x in FS),
                 round((ret - sum(w[:3])) / inv * 100, 1)])
O = pd.DataFrame(rows, columns=['条件', 'R', '的中率', '回収率', '期間別', '上位3除く'][:max(len(r) for r in rows)])
O.to_pickle(f'/tmp/fixed_{TAG}_{VAR}.pkl'); pd.set_option('display.width', 250); print(TAG, VAR); print(O.to_string(index=False))
