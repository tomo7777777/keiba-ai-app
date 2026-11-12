"""過去レース結果を収集（学習用）。python collect_history.py 20240101 20261111"""
import sys, os, json, glob, datetime as dt
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import netkeiba as nk
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "races")
os.makedirs(OUT, exist_ok=True)
a, b = [dt.datetime.strptime(x, "%Y%m%d").date() for x in sys.argv[1:3]]
HOLI = {"0101","0102","0103","0104","0105","0106","0107","0108","0109","0110","0111","0112","0113","0211","0223","0320","0321","0429","0503","0504","0505","0506","0715","0716","0717","0718","0719","0720","0721","0811","0915","0916","0917","0918","0919","0920","0921","0922","0923","1009","1010","1011","1012","1013","1014","1103","1123","1228"}
dates = []
d = a
while d <= b:
    if d.weekday() in (0, 5, 6) or d.strftime("%m%d") in HOLI: dates.append(d.strftime("%Y%m%d"))
    d += dt.timedelta(days=1)
def ids_for(ds):
    return nk.race_ids_on(ds)
cache = os.path.join(OUT, "..", f"ids_{sys.argv[1]}_{sys.argv[2]}.json")
if os.path.exists(cache): ids = json.load(open(cache))
else:
    ids = []
    if True:
        for k, lst in enumerate(map(ids_for, dates)):
            ids += lst
            if k % 50 == 0: print("list", k, len(dates), len(ids), flush=True)
    json.dump(ids, open(cache, "w"))
print("races", len(ids), flush=True)
import features as F
have = {r["race_id"] for r in F.iter_races()} if glob.glob(f"{OUT}/../history/*.gz") else set()
todo = [i for i in ids if not os.path.exists(f"{OUT}/{i}.json") and i not in have]
if len(sys.argv) > 4:
    k, n = int(sys.argv[3]), int(sys.argv[4]); todo = todo[k::n]; print("shard", k, n, len(todo), flush=True)
def work(i):
    r = nk.parse_result(i)
    if r and r["horses"]:
        json.dump(r, open(f"{OUT}/{i}.json", "w"), ensure_ascii=False)
        return 1
    return 0
done = 0
if True:
    for k, v in enumerate(map(work, todo)):
        done += v
        if k % 200 == 0: print(k, len(todo), done, flush=True)
print("done", done)
