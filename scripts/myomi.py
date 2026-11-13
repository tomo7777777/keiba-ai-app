"""妙味軸AI（共通部品）
単勝オッズから「人気から見た3着内確率」を計算し、AIがそれより高く評価する馬
＝過小評価されている馬を、1番人気以外から軸に選ぶ。
"""
import os, numpy as np, pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
# 軸の条件（過去検証で決めた値。変えるときは検証し直す）
AXIS_ODDS = (3.0, 10.0)   # 軸の単勝オッズ
AXIS_MIN_GAP = 1.3        # AIの3着内確率 ÷ 人気から見た3着内確率
MIN_RUNNERS = 7
DROP = {"race_id", "umaban", "horse_id", "name", "date", "rank", "odds", "pop", "win", "top3", "top2",
        "q", "m2", "m3", "lq", "q_rk"}

def model_path(circuit):
    return os.path.join(ROOT, "data", "myomi_jra.pkl" if circuit == "jra" else "nar/myomi_nar.pkl")

def harville(q):
    """勝率 q から 2着内・3着内の確率（Harville式）"""
    q = np.asarray(q, float); n = len(q); p2 = q.copy(); p3 = q.copy()
    for j in range(n):
        if q[j] >= 1: continue
        r = q * q[j] / (1 - q[j]); r[j] = 0; p2 = p2 + r; p3 = p3 + r
        for k in range(n):
            if k == j: continue
            den = 1 - q[j] - q[k]
            if den <= 0: continue
            r = q[j] * q[k] / (1 - q[j]) * q / den; r[j] = 0; r[k] = 0; p3 = p3 + r
    return np.clip(p2, 1e-4, 0.995), np.clip(p3, 1e-4, 0.995)

def add_market_places(d):
    """d に q（市場の勝率）・m2・m3 を追加（lq がある前提）"""
    d["q"] = np.exp(d["lq"])
    m2 = np.zeros(len(d)); m3 = np.zeros(len(d))
    for _, ix in d.groupby("race_id").indices.items():
        a, b = harville(d["q"].values[ix]); m2[ix] = a; m3[ix] = b
    d["m2"] = m2; d["m3"] = m3
    return d

def logit(p): return np.log(p / (1 - p))

def predict(M, d):
    """学習済みモデルで p3（AIの3着内確率）・p2 を計算"""
    X = d.reindex(columns=M["feats"]).astype(float)
    d["p3"] = 1 / (1 + np.exp(-(logit(d["m3"]) + M["p3"].predict(X, raw_score=True))))
    d["p2"] = 1 / (1 + np.exp(-(logit(d["m2"]) + M["p2"].predict(X, raw_score=True))))
    d["gap"] = d["p3"] / d["m3"]
    return d

def pick(horses):
    """horses: [{umaban, odds, p3, m3, gap}] -> 軸と買い目（なければ None）"""
    hs = [h for h in horses if h.get("odds")]
    if len(hs) < MIN_RUNNERS: return None
    fav = min(hs, key=lambda h: h["odds"])["umaban"]
    cand = [h for h in hs if h["umaban"] != fav and AXIS_ODDS[0] <= h["odds"] < AXIS_ODDS[1]]
    if not cand: return None
    ax = max(cand, key=lambda h: h["gap"])
    if ax["gap"] < AXIS_MIN_GAP: return None
    J = ax["umaban"]
    part = [h["umaban"] for h in sorted(hs, key=lambda h: -h["p3"]) if h["umaban"] != J]
    srt = lambda *x: "-".join(map(str, sorted(x)))
    from itertools import combinations
    bets = {
        "fuku":   {"label": "複勝 軸", "tickets": [["複勝", str(J), 100]]},
        "wide":   {"label": "ワイド 軸-相手3頭", "tickets": [["ワイド", srt(J, x), 100] for x in part[:3]]},
        "umaren": {"label": "馬連 軸-相手5頭", "tickets": [["馬連", srt(J, x), 100] for x in part[:5]]},
        "sanfuku": {"label": "3連複 軸1頭-相手4頭", "tickets": [["三連複", srt(J, x, y), 100] for x, y in combinations(part[:4], 2)]},
    }
    return {"axis": J, "gap": round(float(ax["gap"]), 2), "partners": part[:5], "bets": bets}

BET_ORDER = ["fuku", "wide", "umaren", "sanfuku"]
