"""血統（父・母父・父の父）を集める。python collect_ped.py
対象：中央・地方の結果データに出てくる全馬。保存先 data/ped.jsonl（追記・途中再開可）"""
import os, sys, json, glob, gzip, threading
from concurrent.futures import ThreadPoolExecutor
import bs4
sys.path.insert(0, os.path.dirname(__file__))
import netkeiba as nk
ROOT = os.path.join(os.path.dirname(__file__), "..", "data")
OUT = os.path.join(ROOT, "ped.jsonl")

def name(td):
    a = td.find("a")
    return (a.get_text(strip=True) if a else td.get_text(" ", strip=True).split(" ")[0]) or None

def fetch(hid):
    h = nk.get(f"https://db.netkeiba.com/horse/ped/{hid}/", wait=0.0)
    if not h: return None
    t = bs4.BeautifulSoup(h, "lxml").select_one("table.blood_table")
    if not t: return None
    r16 = t.select('td[rowspan="16"]'); r8 = t.select('td[rowspan="8"]')
    if len(r16) < 2 or len(r8) < 3: return None
    return {"id": hid, "sire": name(r16[0]), "ss": name(r8[0]), "dam": name(r16[1]), "bms": name(r8[2])}

def all_ids():
    ids = set()
    for f in glob.glob(f"{ROOT}/history/*.jsonl.gz") + glob.glob(f"{ROOT}/nar/history/*.jsonl.gz"):
        for line in gzip.open(f, "rt", encoding="utf-8"):
            for h in json.loads(line)["horses"]:
                if h.get("horse_id"): ids.add(h["horse_id"])
    for f in glob.glob(f"{ROOT}/races/*.json") + glob.glob(f"{ROOT}/nar/races/*.json"):
        for h in json.load(open(f))["horses"]:
            if h.get("horse_id"): ids.add(h["horse_id"])
    return ids

def load():
    if not os.path.exists(OUT): return {}
    return {r["id"]: r for r in map(json.loads, open(OUT))}

if __name__ == "__main__":
    have = load(); ids = sorted(set(sys.argv[1:]) or all_ids()); todo = [i for i in ids if i not in have]
    print("全", len(ids), "残り", len(todo), flush=True)
    lock = threading.Lock(); done = [0]
    f = open(OUT, "a")
    def work(i):
        try: r = fetch(i)
        except Exception: r = None
        with lock:
            if r: f.write(json.dumps(r, ensure_ascii=False) + "\n")
            done[0] += 1
            if done[0] % 500 == 0: f.flush(); print(done[0], flush=True)
    with ThreadPoolExecutor(14) as ex: list(ex.map(work, todo))
    f.close(); print("完了", len(load()))
