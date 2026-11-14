import sys, os; sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts'); import features as F
base=F.build_base(F.load_history()); d,_,_=F.build_training(base); d=d[d['rank'].notna()]; d.to_pickle(f"{F.BASE}/train_cache.pkl"); print(F.BASE, d.shape, d.date.min())
