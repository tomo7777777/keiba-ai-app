"""期待値ワイド（地方・試験記録）
AIの3着内確率と実際のワイドオッズから「その組が来る確率×オッズ」を計算し、
期待値が基準以上の組だけを買う。確率の計算式は過去の確定オッズ（約2万4千レース）で学習したもの。
"""
import os, json, itertools, numpy as np

PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nar", "ev_wide.json")
TIERS = [("ev13", "期待値1.3以上", 1.3), ("ev10", "期待値1.0以上", 1.0)]

def probs(w, g2=0.85, g3=0.75):
    """勝率 w から、各2頭が上位2頭（馬連）・上位3頭（ワイド）に入る確率（Harville＋補正）"""
    n = len(w); w2 = w ** g2; w2 /= w2.sum(); w3 = w ** g3; w3 /= w3.sum()
    P = w[:, None] * w2[None, :] / (1 - w2[:, None]); np.fill_diagonal(P, 0)
    T = P[:, :, None] * w3[None, None, :] / np.clip(1 - w3[:, None, None] - w3[None, :, None], 1e-9, None)
    I = np.arange(n); T[I, :, I] = 0; T[:, I, I] = 0; T[I, I, :] = 0
    W = T.sum(2) + T.sum(1) + T.sum(0)
    return P + P.T, W + W.T

def features(odds_pair, n, pm, pa, a1, a2, o1, o2):
    lmc = np.log(1 / odds_pair); adjp = a1 * a2
    return np.array([lmc, np.log(pm), np.log(pa), np.log(adjp), np.log(max(a1, a2)), np.log(min(a1, a2)),
                     np.log(min(o1, o2)), np.log(max(o1, o2)), np.log(n), lmc * np.log(adjp)])

def pick(horses, wide_odds, M=None):
    """horses: [{umaban, odds, p3, m3}]、wide_odds: {"1-2": 下限オッズ} -> 期待値1.0以上の組（期待値順）"""
    M = M or json.load(open(PATH))
    hs = sorted([h for h in horses if h.get("odds") and h.get("m3")], key=lambda h: h["umaban"])
    n = len(hs)
    if n < 6 or n > 16 or not wide_odds: return []
    q = np.array([1 / h["odds"] for h in hs]); q /= q.sum()
    adj = np.array([h["p3"] / h["m3"] for h in hs])
    _, Wm = probs(q, M["g2"], M["g3"]); wa = q * adj; wa /= wa.sum(); _, Wa = probs(wa, M["g2"], M["g3"])
    coef = np.array(M["coef"]); out = []
    for i, j in itertools.combinations(range(n), 2):
        k = f"{hs[i]['umaban']}-{hs[j]['umaban']}"; o = wide_odds.get(k)
        if not o or o <= 1: continue
        x = features(o, n, Wm[i, j], Wa[i, j], adj[i], adj[j], hs[i]["odds"], hs[j]["odds"])
        p = 1 / (1 + np.exp(-(M["intercept"] + coef @ x))); ev = p * o
        if ev >= 1.0: out.append(["ワイド", k, 100, o, round(float(ev), 2)])
    return sorted(out, key=lambda t: -t[4])
