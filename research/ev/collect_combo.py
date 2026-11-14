import sys, json, os, pandas as pd, concurrent.futures as cf
sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts'); import netkeiba as nk
ids=set()
for t in ['nar_all','nar_ext']: ids|=set(pd.read_pickle(f'/tmp/ana_{t}.pkl').race_id.astype(str))
out='/tmp/co/combo_nar.jsonl'
done=set()
if os.path.exists(out):
    for l in open(out):
        try: done.add(json.loads(l)['race_id'])
        except: pass
todo=sorted(ids-done); print('todo',len(todo),flush=True)
def job(rid):
    return {'race_id':rid,'umaren':nk.get_combo_odds(rid,'馬連',nar=True),'wide':nk.get_combo_odds(rid,'ワイド',nar=True)}
with open(out,'a') as f, cf.ThreadPoolExecutor(int(sys.argv[1]) if len(sys.argv)>1 else 12) as ex:
    for i,r in enumerate(ex.map(job,todo)):
        f.write(json.dumps(r)+'\n')
        if i%500==0: f.flush(); print(i,flush=True)
print('done',flush=True)
