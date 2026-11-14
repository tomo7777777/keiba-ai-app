import sys, json, os, pandas as pd, concurrent.futures as cf
sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts'); import netkeiba as nk
part, nparts = int(sys.argv[1]), int(sys.argv[2])
S=pd.read_csv('/tmp/co/sel_nar.csv',dtype={'race_id':str}); S=S.iloc[part::nparts]
out=f'/tmp/co/san_nar_{part}.jsonl'; done=set()
if os.path.exists(out): done={json.loads(l)['race_id'] for l in open(out) if l.strip().endswith('}')}
todo=[(r,a) for r,a in zip(S.race_id,S.axis) if r not in done]; print('todo',len(todo),flush=True)
def job(x): return {'race_id':x[0],'axis':int(x[1]),'san':nk.get_combo_odds(x[0],'三連複',nar=True,jiku=int(x[1]))}
with open(out,'a') as f, cf.ThreadPoolExecutor(10) as ex:
    for i,r in enumerate(ex.map(job,todo)):
        f.write(json.dumps(r)+'\n')
        if i%500==0: f.flush(); print(i,flush=True)
print('done',flush=True)
