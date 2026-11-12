"""学習と過去検証（バックテスト）"""
import os, sys, json, pickle
import numpy as np, pandas as pd, lightgbm as lgb
sys.path.insert(0, os.path.dirname(__file__))
import features as F
BASE = F.BASE
FINAL = "--final" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
TEST_FROM = pd.Timestamp(args[0] if args else "2026-05-01")

base = F.build_base(F.load_history())
print("rows", len(base), "races", base.race_id.nunique(), flush=True)
cache = f"{BASE}/train_cache.pkl"
if os.path.exists(cache) and os.path.getmtime(cache) > max(os.path.getmtime(p) for p in [__file__.replace("train.py","features.py")]) and pd.read_pickle(cache).race_id.nunique() == base.race_id.nunique():
    data = pd.read_pickle(cache)
else:
    data, jock, trn = F.build_training(base)
    data = data[data["rank"].notna()]
    data.to_pickle(cache)
data = data[data["odds"].notna() & (data["odds"] > 0)].copy()
data = F.add_market(data, data["odds"].values)
drop = {"race_id","umaban","horse_id","name","date","rank","odds","pop"}
feats = [c for c in data.columns if c not in drop]
data["win"] = (data["rank"] == 1).astype(int); data["top3"] = (data["rank"] <= 3).astype(int)
warm = data["date"] >= pd.Timestamp("2024-07-01")
tr = data[warm & (data["date"] < TEST_FROM)]; te = data[data["date"] >= TEST_FROM].copy()
if FINAL: tr = data[warm]
P = dict(objective="binary", learning_rate=0.03, num_leaves=31, min_data_in_leaf=100, feature_fraction=0.7, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5, verbose=-1)
models = {}
for tgt in ["win", "top3"]:
    m = lgb.train(P, lgb.Dataset(tr[feats], tr[tgt]), num_boost_round=600)
    models[tgt] = m
    te["p_" + tgt] = m.predict(te[feats])
# レース内で合計1(勝率)・合計3(3着内率)に正規化
te["pw"] = te["p_win"] / te.groupby("race_id")["p_win"].transform("sum")
te["p3"] = (te["p_top3"] / te.groupby("race_id")["p_top3"].transform("sum") * 3).clip(upper=0.98)
if not FINAL: te.to_pickle(f"{BASE}/test_pred.pkl")
imp = sorted(zip(models["win"].feature_importance("gain"), feats), reverse=True)[:15]
print("importance", [f for _, f in imp])
if FINAL or not os.path.exists(f"{BASE}/model.pkl"):
    pickle.dump({"models": models, "feats": feats, "trained_until": str(data["date"].max().date())}, open(f"{BASE}/model.pkl", "wb"))
    print("model saved")
