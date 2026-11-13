"""妙味軸AIの当日運用  python myomi_live.py jra|nar [YYYYMMDD]
15分ごとに実行。各レースの発走40分前を切ったら、その時点のオッズで軸と買い目を固定し、
レース後に結果と収支を記録する。地方は KEIBA_DATA=data/nar を付けて実行。
出力: docs/data/myomi/<jra|nar>/days/YYYYMMDD.json, index.json, record.json
"""
import os, sys, json, glob, pickle, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import netkeiba as nk, features as F, strategy as S, myomi as MY

circuit = sys.argv[1] if len(sys.argv) > 1 else "jra"
NAR = circuit == "nar"
if NAR: assert "nar" in F.BASE, "地方は KEIBA_DATA=data/nar を指定"
JST = dt.timezone(dt.timedelta(hours=9))
LOCK_MIN = 40      # 発走何分前から固定するか
RESULT_MIN = 15    # 発走何分後から結果を取りに行くか
OUT = os.path.join(MY.ROOT, "docs", "data", "myomi", circuit)
DAYS = os.path.join(OUT, "days"); os.makedirs(DAYS, exist_ok=True)
RACES = os.path.join(F.BASE, "races"); os.makedirs(RACES, exist_ok=True)

def now(): return dt.datetime.now(JST)
def save(path, obj): json.dump(obj, open(path, "w"), ensure_ascii=False, indent=1)

def start_dt(date, hhmm):
    try: h, m = map(int, hhmm.split(":")); return dt.datetime(int(date[:4]), int(date[4:6]), int(date[6:]), h, m, tzinfo=JST)
    except Exception: return None

def new_day(date):
    ids = nk.nar_race_list(date) if NAR else nk.race_ids_on(date)
    if not ids: return None
    races = []
    for rid in ids:
        c = nk.parse_card(rid, nar=NAR)
        if not c or not c.get("horses"): continue
        if c.get("surface") == "障": continue
        races.append({k: c.get(k) for k in ["race_id", "place", "r", "name", "start", "surface", "distance", "n"]} | {"status": "wait"})
    return {"circuit": circuit, "date": date, "races": races}

_STATE = {}
def model_state(date):
    if not _STATE:
        base = F.build_base(F.load_history())
        _STATE["s"] = F.state_from_base(base, pd.Timestamp(date))
        _STATE["M"] = pickle.load(open(MY.model_path(circuit), "rb"))
    return _STATE["s"], _STATE["M"]

def lock_race(r, date):
    card = nk.parse_card(r["race_id"], nar=NAR)
    if not card or not card.get("horses"): return False
    if any(h["umaban"] is None for h in card["horses"]): return False
    odds, st = nk.get_odds_nar(r["race_id"]) if NAR else nk.get_odds(r["race_id"])
    if st == "yoso" or len(odds) < 0.8 * len(card["horses"]): return False
    if NAR: card["class"] = F.nar_class(card.get("name"))
    (hist, jock, trn), M = model_state(date)
    card["horses"] = [h for h in card["horses"] if odds.get(h["umaban"])]   # 取消・除外を除く
    card["n"] = len(card["horses"])
    d = F.race_rows(card, lambda k: hist.horse.get(k), jock, trn, pd.Timestamp(date))
    d = F.add_market(d, [odds.get(h["umaban"]) for h in card["horses"]])
    d = MY.add_market_places(d); d = MY.predict(M, d)
    fav = min(card["horses"], key=lambda h: odds[h["umaban"]])["umaban"]
    horses = []
    for h, (_, x) in zip(card["horses"], d.iterrows()):
        horses.append({"umaban": h["umaban"], "waku": h["waku"], "name": h["name"], "jockey": h["jockey"],
                       "odds": odds.get(h["umaban"]), "pop": None,
                       "p3": round(float(x["p3"]), 4), "m3": round(float(x["m3"]), 4), "gap": round(float(x["gap"]), 2)})
    for i, h in enumerate(sorted(horses, key=lambda h: h["odds"])): h["pop"] = i + 1
    r.update({"horses": horses, "n": len(horses), "start": card.get("start") or r.get("start"),
              "locked_at": now().strftime("%H:%M"), "status": "locked"})
    p = MY.pick(horses)
    # オッズ記録（今後の期待値分析用）
    def combo(kind, **kw):
        try: return nk.get_combo_odds(r["race_id"], kind, nar=NAR, **kw) or {}
        except Exception as e: print("オッズ取得失敗", kind, r["race_id"], type(e).__name__, e); return {}
    snap = {"馬連": combo("馬連"), "ワイド": combo("ワイド")}
    if p:
        sf = combo("三連複", jiku=p["axis"])
        snap["三連複"] = {k: v for k, v in sf.items() if str(p["axis"]) in k.split("-")}
        for b in p["bets"].values():
            for t in b["tickets"]:
                o = odds.get(int(t[1])) if t[0] == "複勝" else snap.get(t[0], {}).get(t[1])
                if len(t) < 4: t.append(o)
        r["pick"] = p
    r["odds_snap"] = snap
    return True

def settle_race(r):
    res = nk.parse_result(r["race_id"])
    if not res or not res.get("horses") or not res.get("payout"): return False
    if NAR: res["place"] = r.get("place")
    json.dump(res, open(f"{RACES}/{r['race_id']}.json", "w"), ensure_ascii=False)
    rk = {h["umaban"]: h["rank"] for h in res["horses"]}; fo = {h["umaban"]: h["odds"] for h in res["horses"]}
    for h in r.get("horses", []): h["rank"] = rk.get(h["umaban"]); h["final_odds"] = fo.get(h["umaban"])
    order = sorted([h for h in res["horses"] if h["rank"]], key=lambda h: h["rank"])
    r["result"] = {"order": [h["umaban"] for h in order[:3]], "payout": res["payout"]}
    if r.get("pick"):
        for b in r["pick"]["bets"].values():
            inv, ret, hit = S.settle([t[:3] for t in b["tickets"]], res["payout"])
            b.update({"inv": inv, "ret": ret, "hit": hit})
    return True

def summarize():
    rec = {"bets": {}, "days": [], "races": 0, "axis_top3": 0, "axis_n": 0}
    for path in sorted(glob.glob(f"{DAYS}/*.json")):
        day = json.load(open(path)); ds = {"date": day["date"], "bets": {}}
        for r in day["races"]:
            if not r.get("result"): continue
            rec["races"] += 1
            p = r.get("pick")
            if not p: continue
            ax = next((h for h in r["horses"] if h["umaban"] == p["axis"]), {})
            rec["axis_n"] += 1; rec["axis_top3"] += int((ax.get("rank") or 99) <= 3)
            for k, b in p["bets"].items():
                if "inv" not in b: continue
                for tgt in (rec["bets"].setdefault(k, {"label": b["label"], "races": 0, "hit_races": 0, "inv": 0, "ret": 0}),
                            ds["bets"].setdefault(k, {"races": 0, "hit_races": 0, "inv": 0, "ret": 0})):
                    tgt["races"] += 1; tgt["hit_races"] += int(b["hit"] > 0); tgt["inv"] += b["inv"]; tgt["ret"] += b["ret"]
        if ds["bets"]: rec["days"].append(ds)
    rec["updated"] = now().isoformat(timespec="minutes")
    save(os.path.join(OUT, "record.json"), rec)

def main():
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    date = args[0] if args else now().strftime("%Y%m%d")
    path = f"{DAYS}/{date}.json"
    day = json.load(open(path)) if os.path.exists(path) else new_day(date)
    if not day:
        print("開催なし", circuit, date); return
    t = now(); changed = not os.path.exists(path)
    for r in day["races"]:
        sd = start_dt(date, r.get("start") or "")
        if not sd: continue
        mins = (sd - t).total_seconds() / 60
        if r["status"] == "wait":
            if mins < 0: r["status"] = "missed"; changed = True
            elif mins <= LOCK_MIN:
                try:
                    if lock_race(r, date): changed = True; print("固定", r["race_id"], "軸" if r.get("pick") else "見送り")
                except Exception as e:
                    print("固定エラー", r["race_id"], type(e).__name__, e)
        if r["status"] in ("locked", "missed") and not r.get("result") and mins < -RESULT_MIN:
            if settle_race(r): changed = True; print("結果", r["race_id"])
    day["updated"] = t.isoformat(timespec="minutes")
    if changed:
        save(path, day)
        ip = os.path.join(OUT, "index.json")
        idx = json.load(open(ip)) if os.path.exists(ip) else {"days": []}
        if date not in idx["days"]: idx["days"] = sorted(idx["days"] + [date], reverse=True)
        save(ip, idx)
    # 前日以前で結果未取得のレースも拾う
    for p in sorted(glob.glob(f"{DAYS}/*.json"))[-4:]:
        if p == path: continue
        dd = json.load(open(p)); ch = False
        for r in dd["races"]:
            if r["status"] in ("locked", "missed") and not r.get("result"):
                ch |= settle_race(r)
        if ch: save(p, dd)
    summarize()
    print(circuit, date, sum(r["status"] == "locked" for r in day["races"]), "固定済み /", len(day["races"]))

if __name__ == "__main__":
    main()
