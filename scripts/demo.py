"""過去日の再現（デモ）。結果ページの出走情報と確定オッズで予想を作り、そのまま精算する"""
import os, sys, json, glob
os.environ["DEMO"] = "1"
sys.path.insert(0, os.path.dirname(__file__))
import predict as P, strategy as S, features as F, results as R
date = sys.argv[1]
races = [r for r in F.iter_races() if r.get("date") == date and r.get("surface") != "障"]
cards = []; odds_map = {}
for r in sorted(races, key=lambda x: x["race_id"]):
    hs = [h for h in r["horses"] if h.get("umaban")]
    cards.append({**r, "start": "", "horses": hs, "n": len(hs)})
    odds_map[r["race_id"]] = {h["umaban"]: h["odds"] for h in hs if h.get("odds")}
out = P.predict_races(cards, date, odds_map)
for r, c in zip(out, cards):
    for h in r["horses"]:
        o = odds_map[r["race_id"]].get(h["umaban"]); h["odds"] = o; h["ev"] = round(h["pw"] * o, 2) if o else None
    m = S.marks(r["horses"])
    for h in r["horses"]: h["mark"] = m.get(h["umaban"], "")
    r["bets"] = S.make_bets(r["horses"]); r["confidence"] = round(max(h["pw"] for h in r["horses"]), 3)
    r["odds_time"] = "確定"
    rk = {h["umaban"]: h["rank"] for h in c["horses"]}
    for h in r["horses"]: h["rank"] = rk.get(h["umaban"]); h["final_odds"] = h["odds"]
    order = sorted([h for h in c["horses"] if h["rank"]], key=lambda h: h["rank"])
    r["result"] = {"order": [h["umaban"] for h in order[:3]], "payout": c["payout"]}
    for k, b in r["bets"].items():
        inv, ret, hit = S.settle(b["tickets"], c["payout"]); b.update({"inv": inv, "ret": ret, "hit": hit})
day = {"demo": True, "date": date, "fixed_at": f"{date[:4]}-{date[4:6]}-{date[6:]}T00:00", "updated": "", "races": out}
json.dump(day, open(f"{P.DAYS}/{date}.json", "w"), ensure_ascii=False, indent=1)
idx_path = os.path.join(P.ROOT, "docs", "data", "index.json")
idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {"days": []}
if date not in idx["days"]: idx["days"] = sorted(idx["days"] + [date], reverse=True)
json.dump(idx, open(idx_path, "w"), ensure_ascii=False, indent=1)
print(date, len(out), {k: sum(1 for r in out if k in r["bets"]) for k in ["honmei", "nerai"]})
