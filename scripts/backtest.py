"""学習に使っていない期間で買い方を検証し docs/data/backtest.json を出力"""
import os, sys, json, itertools
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import features as F, strategy as S
te = pd.read_pickle(f"{F.BASE}/test_pred.pkl")
pay = {}
for rid in te.race_id.unique():
    pay[rid] = F.get_race(rid)["payout"]

def run(grid=False):
    agg = {}
    def add(name, inv, ret, hit):
        a = agg.setdefault(name, [0, 0, 0, 0]); a[0] += 1; a[1] += int(hit > 0); a[2] += inv; a[3] += ret
    for rid, g in te.groupby("race_id"):
        hs = [{"umaban": int(r.umaban), "pw": r.pw, "odds": r.odds} for r in g.itertuples() if pd.notna(r.umaban)]
        if len(hs) < 5: continue
        order = sorted(hs, key=lambda h: -h["pw"]); a = order[0]
        fav = min(hs, key=lambda h: h["odds"] if h["odds"] == h["odds"] and h["odds"] else 9999)
        add("参考：1番人気の単勝", *S.settle([["単勝", str(fav["umaban"]), 100]], pay[rid]))
        add("◎単勝（全レース）", *S.settle([["単勝", str(a["umaban"]), 100]], pay[rid]))
        add("◎複勝（全レース）", *S.settle([["複勝", str(a["umaban"]), 100]], pay[rid]))
        b = S.make_bets(hs)
        if "honmei" in b:
            add("本命（4点）", *S.settle(b["honmei"]["tickets"], pay[rid]))
            for kind in ["単勝", "馬連", "ワイド"]:
                add(f"本命の{kind}", *S.settle([t for t in b["honmei"]["tickets"] if t[0] == kind], pay[rid]))
        if "nerai" in b:
            add("狙い（単勝1点）", *S.settle(b["nerai"]["tickets"], pay[rid]))
    return agg

if __name__ == "__main__":
    if "--grid" in sys.argv:
        for hp in [0.25, 0.3, 0.35, 0.4]:
            S.HONMEI_MIN_P = hp; a = run()
            print("HONMEI", hp, {k: (v[0], round(v[3]/v[2]*100, 1)) for k, v in a.items() if k.startswith("本命")})
        for ev in [1.0, 1.2, 1.3, 1.5, 1.8]:
            for lo, hi in [(3, 20), (6, 40), (10, 80)]:
                S.NERAI_MIN_EV = ev; S.NERAI_ODDS = (lo, hi); a = run()
                v = a.get("狙いの単勝", [0, 0, 1, 0]); w = a.get("狙いの複勝", [0, 0, 1, 0])
                print("NERAI", ev, lo, hi, v[0], "単", round(v[3]/v[2]*100, 1), "複", round(w[3]/w[2]*100, 1))
        sys.exit()
    a = run()
    rows = [{"name": k, "races": v[0], "hit": f"{v[1]/v[0]*100:.1f}%", "roi": f"{v[3]/v[2]*100:.1f}%"} for k, v in a.items()]
    d0, d1 = te.date.min(), te.date.max()
    out = {"period": f"{d0:%Y/%m/%d}〜{d1:%Y/%m/%d}・{te.race_id.nunique()}レース", "rows": rows}
    json.dump(out, open(os.path.join(F.BASE, "..", "docs", "data", "backtest.json"), "w"), ensure_ascii=False, indent=1)
    for r in rows: print(r)
