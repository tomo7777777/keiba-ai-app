"""結果取得と成績集計  python results.py [YYYYMMDD ...]（省略時は未確定の日をすべて）"""
import os, sys, json, glob
sys.path.insert(0, os.path.dirname(__file__))
import netkeiba as nk, strategy as S
ROOT = os.path.join(os.path.dirname(__file__), "..")
DAYS = os.path.join(ROOT, "docs", "data", "days")
RACES = os.path.join(ROOT, "data", "races")

def update_day(path):
    day = json.load(open(path)); changed = False
    for r in day["races"]:
        if r.get("result"): continue
        res = nk.parse_result(r["race_id"])
        if not res or not res["horses"] or not res.get("payout"): continue
        os.makedirs(RACES, exist_ok=True); json.dump(res, open(f"{RACES}/{r['race_id']}.json", "w"), ensure_ascii=False)
        rk = {h["umaban"]: h["rank"] for h in res["horses"]}
        fo = {h["umaban"]: h["odds"] for h in res["horses"]}
        for h in r["horses"]:
            h["rank"] = rk.get(h["umaban"]); h["final_odds"] = fo.get(h["umaban"])
        order = sorted([h for h in res["horses"] if h["rank"]], key=lambda h: h["rank"])
        r["result"] = {"order": [h["umaban"] for h in order[:3]], "payout": res["payout"]}
        for k, b in r.get("bets", {}).items():
            inv, ret, hit = S.settle(b["tickets"], res["payout"])
            b.update({"inv": inv, "ret": ret, "hit": hit})
        changed = True
    if changed: json.dump(day, open(path, "w"), ensure_ascii=False, indent=1)
    return changed

def summarize():
    rec = {"strategies": {}, "days": [], "marks": {"races": 0, "honmei_win": 0, "honmei_top3": 0}}
    for path in sorted(glob.glob(f"{DAYS}/*.json")):
        day = json.load(open(path)); dsum = {"date": day["date"]}
        if day.get("demo"): continue
        for r in day["races"]:
            if not r.get("result"): continue
            top = max(r["horses"], key=lambda h: h["pw"])
            rec["marks"]["races"] += 1
            rec["marks"]["honmei_win"] += int(top.get("rank") == 1); rec["marks"]["honmei_top3"] += int((top.get("rank") or 99) <= 3)
            for k, b in r.get("bets", {}).items():
                if "inv" not in b: continue
                for tgt in (rec["strategies"].setdefault(k, {"races": 0, "hit_races": 0, "inv": 0, "ret": 0}), dsum.setdefault(k, {"races": 0, "hit_races": 0, "inv": 0, "ret": 0})):
                    tgt["races"] += 1; tgt["hit_races"] += int(b["hit"] > 0); tgt["inv"] += b["inv"]; tgt["ret"] += b["ret"]
        if len(dsum) > 1: rec["days"].append(dsum)
    json.dump(rec, open(os.path.join(ROOT, "docs", "data", "record.json"), "w"), ensure_ascii=False, indent=1)
    return rec

if __name__ == "__main__":
    targets = [f"{DAYS}/{d}.json" for d in sys.argv[1:]] or sorted(glob.glob(f"{DAYS}/*.json"))
    for p in targets:
        if os.path.exists(p): print(p, update_day(p))
    print(summarize())
