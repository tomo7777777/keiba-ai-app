"""地方競馬の過去レース結果を収集。python collect_nar.py 20250701 20261112
保存先 data/nar/races/（ばんえい=帯広65は除外）"""
import sys, os, json, re, datetime as dt, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import netkeiba as nk
ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "nar")
OUT = os.path.join(ROOT, "races"); os.makedirs(OUT, exist_ok=True)
NAR_PLACE = {"30":"門別","35":"盛岡","36":"水沢","42":"浦和","43":"船橋","44":"大井","45":"川崎","46":"金沢","47":"笠松","48":"名古屋","50":"園田","51":"姫路","54":"高知","55":"佐賀"}
def ids_on(date):
    h = nk.get(f"https://nar.netkeiba.com/top/race_list_sub.html?kaisai_date={date}")
    return sorted({i for i in re.findall(r"race_id=(\d{12})", h or "") if i[4:6] in NAR_PLACE})
if __name__ == "__main__":
    a, b = [dt.datetime.strptime(x, "%Y%m%d").date() for x in sys.argv[1:3]]
    dates = [(a + dt.timedelta(days=k)).strftime("%Y%m%d") for k in range((b - a).days + 1)]
    cache = os.path.join(ROOT, f"ids_{sys.argv[1]}_{sys.argv[2]}.json")
    if os.path.exists(cache): ids = json.load(open(cache))
    else:
        with ThreadPoolExecutor(4) as ex: lists = list(ex.map(ids_on, dates))
        ids = [i for l in lists for i in l]; json.dump(ids, open(cache, "w"))
    print("races", len(ids), flush=True)
    todo = [i for i in ids if not os.path.exists(f"{OUT}/{i}.json")]
    def work(i):
        try:
            r = nk.parse_result(i)
        except Exception:
            return 0
        if r and r["horses"]:
            r["place"] = NAR_PLACE[i[4:6]]
            json.dump(r, open(f"{OUT}/{i}.json", "w"), ensure_ascii=False); return 1
        return 0
    done = 0; t = time.time()
    with ThreadPoolExecutor(int(os.environ.get("TH", 5))) as ex:
        for k, v in enumerate(ex.map(work, todo)):
            done += v
            if k % 500 == 0: print(k, len(todo), done, int(time.time() - t), flush=True)
    print("done", done)
