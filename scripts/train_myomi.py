"""妙味軸AIの学習  python train_myomi.py jra|nar
中央: data/myomi_jra.pkl / 地方: data/nar/myomi_nar.pkl（地方は KEIBA_DATA=data/nar で実行）"""
import os, sys, pickle
import numpy as np, pandas as pd, lightgbm as lgb
sys.path.insert(0, os.path.dirname(__file__))
import features as F, myomi as MY

circuit = sys.argv[1] if len(sys.argv) > 1 else "jra"
if circuit == "nar": assert "nar" in F.BASE, "地方は KEIBA_DATA=data/nar を指定"
cache = f"{F.BASE}/train_cache.pkl"
base = F.build_base(F.load_history())
if os.path.exists(cache) and pd.read_pickle(cache).race_id.nunique() == base.race_id.nunique():
    d = pd.read_pickle(cache)
else:
    d, _, _ = F.build_training(base); d = d[d["rank"].notna()]; d.to_pickle(cache)
d = d[d["odds"].notna() & (d["odds"] > 0)].copy()
d = F.add_market(d, d["odds"].values); d = MY.add_market_places(d)
d["top3"] = (d["rank"] <= 3).astype(int); d["top2"] = (d["rank"] <= 2).astype(int)
# 最初の3か月は過去成績がたまっていないので除く
d = d[d["date"] >= d["date"].min() + pd.DateOffset(months=3)]
feats = [c for c in d.columns if c not in MY.DROP]
P = dict(objective="binary", learning_rate=0.02, num_leaves=31, min_data_in_leaf=200, feature_fraction=0.7,
         bagging_fraction=0.8, bagging_freq=1, lambda_l2=5, verbose=-1)
M = {"feats": feats, "trained_until": str(d["date"].max().date()), "rows": len(d)}
for t, mk in [("p3", "m3"), ("p2", "m2")]:
    y = d["top3"] if t == "p3" else d["top2"]
    M[t] = lgb.train(P, lgb.Dataset(d[feats], y, init_score=MY.logit(d[mk])), 300)
os.makedirs(os.path.dirname(MY.model_path(circuit)), exist_ok=True)
pickle.dump(M, open(MY.model_path(circuit), "wb"))
print("saved", MY.model_path(circuit), M["trained_until"], len(d))
