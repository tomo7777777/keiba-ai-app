"""当日の予想を作成して docs/data/days/YYYYMMDD.json に保存
python predict.py [YYYYMMDD] [--force] [--odds-only]
- 初回実行で印・買い目を固定（--force で作り直し）
- --odds-only はオッズ表示だけ更新（買い目は変えない）
"""
import os, sys, json, pickle, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import netkeiba as nk, features as F, strategy as S

ROOT = os.path.join(os.path.dirname(__file__), "..")
DAYS = os.path.join(ROOT, "docs", "data", "days")
os.makedirs(DAYS, exist_ok=True)
JST = dt.timezone(dt.timedelta(hours=9))

def now(): return dt.datetime.now(JST)

def predict_races(cards, date, odds_map):
    M = pickle.load(open(os.environ.get("MODEL", os.path.join(ROOT, "data", "model.pkl")), "rb"))
    base = F.build_base(F.load_history())
    hist, jock, trn = F.state_from_base(base, pd.Timestamp(date))
    out = []
    for card in cards:
        if not card or not card["horses"]: continue
        d = F.race_rows(card, lambda k: hist.horse.get(k), jock, trn, pd.Timestamp(date))
        od = odds_map.get(card["race_id"], {})
        d = F.add_market(d, [od.get(h["umaban"]) for h in card["horses"]])
        X = d.reindex(columns=M["feats"]).astype(float)
        pw = M["models"]["win"].predict(X); p3 = M["models"]["top3"].predict(X)
        pw = pw / pw.sum(); p3 = np.clip(p3 / p3.sum() * min(3, len(p3)), 0, 0.98)
        horses = []
        for h, a, b, (_, row) in zip(card["horses"], pw, p3, d.iterrows()):
            horses.append({"umaban": h["umaban"], "waku": h["waku"], "name": h["name"], "sex": h["sex"], "age": h["age"],
                           "kinryo": h["kinryo"], "jockey": h["jockey"], "trainer": h["trainer"], "weight": h["weight"], "wdiff": h["wdiff"],
                           "pw": round(float(a), 4), "p3": round(float(b), 4),
                           "runs": int(row.get("h_n") or 0),
                           "last": None if pd.isna(row.get("h_rn_last", np.nan)) else round(float(row["h_rn_last"]), 2)})
        out.append({k: card.get(k) for k in ["race_id", "place", "r", "name", "start", "surface", "distance", "going", "class", "n"]} | {"horses": horses})
    return out

def attach_odds(race, fix=False):
    odds, status = nk.get_odds(race["race_id"])
    for h in race["horses"]:
        o = odds.get(h["umaban"])
        h["odds"] = o
        h["ev"] = round(h["pw"] * o, 2) if o else None
    race["odds_time"] = now().strftime("%H:%M")
    return race

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    date = args[0] if args else now().strftime("%Y%m%d")
    path = f"{DAYS}/{date}.json"
    if os.path.exists(path) and "--force" not in sys.argv:
        day = json.load(open(path))
        if "--odds-only" in sys.argv:
            for r in day["races"]:
                if r.get("result"): continue
                attach_odds(r)
            day["updated"] = now().isoformat(timespec="minutes")
            json.dump(day, open(path, "w"), ensure_ascii=False, indent=1)
            print("odds updated", date)
        else:
            print("already fixed", date)
        return
    ids = nk.race_ids_on(date)
    if not ids:
        print("no JRA races", date); return
    cards = [nk.parse_card(i) for i in ids]
    if any(c and c["horses"] and c["horses"][0]["umaban"] is None for c in cards):
        print("枠順未確定のため保留", date); return
    odds_map = {}
    for c in cards:
        o, st = nk.get_odds(c["race_id"])
        odds_map[c["race_id"]] = o if st != "yoso" else {}
    have = sum(1 for c in cards if len(odds_map[c["race_id"]]) >= 0.8 * c["n"])
    if have < 0.8 * len(cards) and "--force" not in sys.argv:
        print("オッズ発売前のため保留", date, have, len(cards)); return
    races = predict_races(cards, date, odds_map)
    for r in races:
        attach_odds(r)
        m = S.marks(r["horses"])
        for h in r["horses"]: h["mark"] = m.get(h["umaban"], "")
        r["bets"] = S.make_bets(r["horses"])
        top = max(r["horses"], key=lambda h: h["pw"])
        r["confidence"] = round(top["pw"], 3)
    day = {"demo": bool(os.environ.get("DEMO")), "date": date, "fixed_at": now().isoformat(timespec="minutes"), "updated": now().isoformat(timespec="minutes"), "races": races}
    json.dump(day, open(path, "w"), ensure_ascii=False, indent=1)
    idx_path = os.path.join(ROOT, "docs", "data", "index.json")
    idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {"days": []}
    if date not in idx["days"]: idx["days"] = sorted(idx["days"] + [date], reverse=True)
    json.dump(idx, open(idx_path, "w"), ensure_ascii=False, indent=1)
    print("predicted", date, len(races))

if __name__ == "__main__":
    main()
