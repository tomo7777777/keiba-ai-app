"""特徴量の作成。過去レースのみを使い、当日の情報は出馬表で分かるものだけ使う"""
import os, json, glob, re
import numpy as np, pandas as pd
from collections import defaultdict

BASE = os.environ.get("KEIBA_DATA") or os.path.join(os.path.dirname(__file__), "..", "data")
GOING = {"良": 0, "稍重": 1, "重": 2, "不良": 3}
SURF = {"芝": 0, "ダ": 1, "障": 2}
PLACE = {"札幌":1,"函館":2,"福島":3,"新潟":4,"東京":5,"中山":6,"中京":7,"京都":8,"阪神":9,"小倉":10,
         "門別":30,"盛岡":35,"水沢":36,"浦和":42,"船橋":43,"大井":44,"川崎":45,"金沢":46,"笠松":47,"名古屋":48,"園田":50,"姫路":51,"高知":54,"佐賀":55}
NAR = {k for k, v in PLACE.items() if v >= 30}
def jra_grade(name, cur):
    """中央の重賞をレース名から判定（G3=7, G2=8, G1=9）"""
    for k, v in [("GIII)", 7), ("GII)", 8), ("GI)", 9)]:
        if k in name: return v
    return cur
def nar_class(name):
    """地方のレース名からクラスを数値化（大きいほど上）"""
    n = (name or "").upper().translate(str.maketrans("ＡＢＣ１２３", "ABC123")).replace("JRA", "")
    for k, v in [("JPNIII",7),("JPNII",8),("JPNI",9),("JPN1",9),("JPN2",8),("JPN3",7),("重賞",6),("OP",6),("オープン",6),("A1",5.5),("A2",5),("A",5),("B1",4.5),("B2",4),("B3",3.8),("B",4),("C1",3.5),("C2",3),("C3",2.5),("C4",2.2),("C",3),("新馬",1),("未勝利",1.5),("2歳",2)]:
        if k in n: return v
    return 3
SEX = {"牡": 0, "牝": 1, "セ": 2}

def iter_races():
    import gzip
    seen = set()
    for f in glob.glob(f"{BASE}/races/*.json"):
        r = json.load(open(f)); seen.add(r["race_id"]); yield r
    for f in glob.glob(f"{BASE}/history/*.jsonl.gz"):
        for line in gzip.open(f, "rt", encoding="utf-8"):
            r = json.loads(line)
            if r["race_id"] not in seen: yield r

def get_race(race_id):
    p = f"{BASE}/races/{race_id}.json"
    if os.path.exists(p): return json.load(open(p))
    if "all" not in _RACE_CACHE:
        _RACE_CACHE["all"] = {r["race_id"]: r for r in iter_races()}
    return _RACE_CACHE["all"].get(race_id)
_RACE_CACHE = {}

def load_history():
    rows = []
    for r in iter_races():
        if not r.get("date") or r.get("surface") == "障": continue
        if r.get("place") in NAR: r["class"] = nar_class(r.get("name"))
        elif "G" in (r.get("name") or ""): r["class"] = jra_grade(r["name"], r.get("class"))
        for h in r["horses"]:
            rows.append({**{k: r.get(k) for k in ["race_id","date","place","r","surface","distance","going","class","n","handicap"]}, **h})
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["date", "race_id", "umaban"]).reset_index(drop=True)

def first_corner(p):
    try: return int(str(p).split("-")[0])
    except Exception: return np.nan

def build_base(df):
    """結果データに過去成績の集計列を追加（各行はその時点より前の情報のみ）"""
    df = df.copy()
    ok = df["time"].notna() & df["rank"].notna()
    key = ["place", "surface", "distance"]
    st = df[ok].groupby(key)["time"].agg(["mean", "std"]).reset_index()
    df = df.merge(st, on=key, how="left")
    df["si"] = -(df["time"] - df["mean"]) / df["std"].replace(0, np.nan)
    # 馬場差補正: クラス別の平均的な速さを除いた「その日のその馬場」の偏りを引く
    df["si"] = df["si"].clip(-5, 5)
    exp = df.groupby(["surface", "class"])["si"].transform("mean")
    df["_res"] = df["si"] - exp
    var = df.groupby(["date", "place", "surface"])["_res"].transform("mean")
    df["si"] = df["si"] - var.fillna(0)
    df["l3rel"] = (df["last3f"] - df.groupby("race_id")["last3f"].transform("median")).clip(-4, 4)
    df["rnorm"] = (df["rank"] - 1) / (df["n"] - 1).clip(lower=1)
    df["fc"] = df["passing"].map(first_corner) / df["n"]
    df["popn"] = df["pop"] / df["n"]
    df["win"] = (df["rank"] == 1).astype(int); df["top3"] = (df["rank"] <= 3).astype(int)
    return df.drop(columns=["mean", "std", "_res"])

HIST_COLS = ["date","race_id","surface","distance","class","rank","rnorm","si","l3rel","fc","popn","win","top3","going"]

class Hist:
    """馬・騎手・調教師の過去成績（結果確定分）"""
    def __init__(self, base):
        b = base[base["rank"].notna()]
        self.horse = {k: g[HIST_COLS].sort_values("date") for k, g in b.groupby("horse_id")}
        self.base = b

def horse_feats(h, date, surface, distance, klass):
    f = {}
    if h is None: h = pd.DataFrame(columns=HIST_COLS)
    h = h[h["date"] < date]
    f["h_n"] = len(h)
    if len(h) == 0:
        return f
    last = h.iloc[-1]
    t5 = h.tail(5); t3 = h.tail(3)
    f["h_win"] = h["win"].mean(); f["h_top3"] = h["top3"].mean()
    f["h_rn_avg5"] = t5["rnorm"].mean(); f["h_rn_last"] = last["rnorm"]
    f["h_rn_last2"] = h.iloc[-2]["rnorm"] if len(h) > 1 else np.nan
    f["h_si_avg3"] = t3["si"].mean(); f["h_si_max5"] = t5["si"].max(); f["h_si_last"] = last["si"]
    f["h_l3_avg3"] = t3["l3rel"].mean(); f["h_fc_avg5"] = t5["fc"].mean()
    f["h_pop_avg3"] = t3["popn"].mean()
    f["h_days"] = (date - last["date"]).days
    f["h_dist_diff"] = distance - last["distance"]
    f["h_class_diff"] = klass - last["class"]
    same = h[h["surface"] == surface]
    f["h_surf_n"] = len(same); f["h_surf_top3"] = same["top3"].mean() if len(same) else np.nan
    f["h_surf_si"] = same.tail(5)["si"].mean() if len(same) else np.nan
    near = h[(h["distance"] - distance).abs() <= 200]
    f["h_dist_top3"] = near["top3"].mean() if len(near) else np.nan
    f["h_dist_si"] = near.tail(5)["si"].mean() if len(near) else np.nan
    return f

class Rolling:
    """騎手・調教師の通算成績を日付順に更新"""
    def __init__(self): self.s = defaultdict(lambda: [0, 0, 0])
    def get(self, k):
        n, w, t = self.s[k]; return (w + 0.5) / (n + 7), (t + 1.5) / (n + 7), n
    def add(self, k, win, top3):
        x = self.s[k]; x[0] += 1; x[1] += win; x[2] += top3

def race_rows(race, hist_lookup, jock, trn, date):
    out = []
    for h in race["horses"]:
        f = {"race_id": race["race_id"], "umaban": h.get("umaban"), "horse_id": h.get("horse_id"), "name": h.get("name")}
        f.update({"distance": race.get("distance"), "surface": SURF.get(race.get("surface"), 0), "going": GOING.get(race.get("going"), 0),
                  "class": race.get("class"), "n": race.get("n"), "place": PLACE.get(race.get("place"), 0), "handicap": int(bool(race.get("handicap"))),
                  "waku": h.get("waku"), "kinryo": h.get("kinryo"), "age": h.get("age"), "sex": SEX.get(h.get("sex"), 0),
                  "weight": h.get("weight"), "wdiff": h.get("wdiff")})
        f["umaban_n"] = (h.get("umaban") or 0) / max(race.get("n") or 1, 1)
        f.update(horse_feats(hist_lookup(h.get("horse_id")), date, race.get("surface"), race.get("distance") or 0, race.get("class") or 3))
        jw, jt, jn = jock.get(h.get("jockey_id")); tw, tt, tn = trn.get(h.get("trainer_id"))
        f.update({"j_win": jw, "j_top3": jt, "j_n": jn, "t_win": tw, "t_top3": tt, "t_n": tn})
        out.append(f)
    d = pd.DataFrame(out)
    # レース内での相対値
    for c in ["h_si_avg3", "h_si_max5", "h_rn_avg5", "j_win", "h_dist_si", "kinryo"]:
        if c in d:
            d[c + "_rk"] = d[c].rank(ascending=(c in ["h_rn_avg5"]), pct=True)
            d[c + "_z"] = d[c] - d[c].mean()
    return d

FEATS = None

def build_training(base):
    """全レースを日付順に処理して学習用データを作成"""
    hist = Hist(base)
    jock, trn = Rolling(), Rolling()
    parts = []
    for date, day in base.groupby("date", sort=True):
        for rid, g in day.groupby("race_id"):
            race = {"race_id": rid, **g.iloc[0][["place","surface","distance","going","class","n","handicap"]].to_dict(),
                    "horses": g.to_dict("records")}
            d = race_rows(race, lambda k: hist.horse.get(k), jock, trn, date)
            d["date"] = date; d["rank"] = g["rank"].values; d["odds"] = g["odds"].values; d["pop"] = g["pop"].values
            parts.append(d)
        for _, r in day.iterrows():
            if pd.notna(r["rank"]):
                jock.add(r["jockey_id"], r["rank"] == 1, r["rank"] <= 3); trn.add(r["trainer_id"], r["rank"] == 1, r["rank"] <= 3)
    return pd.concat(parts, ignore_index=True), jock, trn

def state_from_base(base, before):
    """指定日より前の結果から 馬履歴・騎手・調教師 の状態を作る"""
    b = base[(base["date"] < before) & base["rank"].notna()]
    hist = Hist(b)
    jock, trn = Rolling(), Rolling()
    for k, g in b.groupby("jockey_id"):
        jock.s[k] = [len(g), int((g["rank"] == 1).sum()), int((g["rank"] <= 3).sum())]
    for k, g in b.groupby("trainer_id"):
        trn.s[k] = [len(g), int((g["rank"] == 1).sum()), int((g["rank"] <= 3).sum())]
    return hist, jock, trn

def add_market(d, odds):
    """単勝オッズから市場の勝率（控除分を除いた確率）を追加"""
    o = pd.Series(odds, index=d.index, dtype=float)
    q = 1 / o.where(o > 0)
    q = q.fillna(q.min() / 2 if q.notna().any() else 1 / len(d))
    q = q / q.groupby(d["race_id"]).transform("sum")
    d["lq"] = np.log(q); d["q_rk"] = q.groupby(d["race_id"]).rank(ascending=False)
    return d
