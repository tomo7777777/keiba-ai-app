"""買い目の作り方（バックテストで決めた条件）。predict.py / backtest.py / results.py で共通利用"""
import itertools

# 本命: AIの1番手の勝率が高いレース
HONMEI_MIN_P = 0.40
# 狙い: 単勝の期待値（AI勝率×オッズ）が高い馬
NERAI_MIN_EV = 1.30
NERAI_ODDS = (10.0, 80.0)
NERAI_MIN_P = 0.02

def marks(horses):
    """horses: [{umaban, pw}] -> 印"""
    order = sorted(horses, key=lambda h: -h["pw"])
    sym = ["◎", "○", "▲", "△", "△"]
    return {h["umaban"]: sym[i] for i, h in enumerate(order[:5])}

def make_bets(horses):
    """レースごとの買い目。horses: [{umaban, pw, odds}]"""
    order = sorted(horses, key=lambda h: -h["pw"])
    if len(order) < 5: return {}
    a, b, c, d, e = [h["umaban"] for h in order[:5]]
    bets = {}
    top = order[0]
    if top["pw"] >= HONMEI_MIN_P:
        bets["honmei"] = {
            "label": "本命",
            "tickets": [["単勝", str(a), 100], ["馬連", f"{min(a,b)}-{max(a,b)}", 100]]
                       + [["ワイド", "-".join(map(str, sorted([a, x]))), 100] for x in (b, c)],
        }
    ner = [h for h in horses if h.get("odds") and NERAI_ODDS[0] <= h["odds"] <= NERAI_ODDS[1]
           and h["pw"] >= NERAI_MIN_P and h["pw"] * h["odds"] >= NERAI_MIN_EV]
    if ner:
        best = max(ner, key=lambda h: h["pw"] * h["odds"])
        u = best["umaban"]
        bets["nerai"] = {"label": "狙い", "horse": u,
                         "tickets": [["単勝", str(u), 100]]}
    return bets

UNORDERED = {"馬連", "ワイド", "三連複", "枠連"}

def _key(kind, s):
    v = [int(x) for x in str(s).split("-")]
    return sorted(v) if kind in UNORDERED else v

def settle(tickets, payout):
    """tickets を払戻表で精算 -> (投資, 回収, 的中数)"""
    inv = ret = hit = 0
    for kind, combo, yen in tickets:
        inv += yen
        for num, pay in payout.get(kind, []):
            if pay is None: continue
            try:
                if _key(kind, num) == _key(kind, combo):
                    ret += pay * yen // 100; hit += 1
            except ValueError:
                pass
    return inv, ret, hit
