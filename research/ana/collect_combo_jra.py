import sys, json, gzip, concurrent.futures as cf
sys.path.insert(0, 'scripts'); import netkeiba as nk
ids = open('research/ana/jra_combo_ids.txt').read().split()
def job(rid): return {'race_id': rid, 'umaren': nk.get_combo_odds(rid, '馬連'), 'wide': nk.get_combo_odds(rid, 'ワイド')}
with gzip.open('combo_jra.jsonl.gz', 'wt') as f, cf.ThreadPoolExecutor(8) as ex:
    for i, r in enumerate(ex.map(job, ids)):
        f.write(json.dumps(r) + '\n')
        if i % 1000 == 0: print(i, flush=True)
