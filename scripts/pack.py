"""data/races/*.json を年ごとの data/history/YYYY.jsonl.gz にまとめる（リポジトリを軽くするため）"""
import os, glob, json, gzip
from collections import defaultdict
B = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(f"{B}/history", exist_ok=True)
by = defaultdict(dict)
for f in glob.glob(f"{B}/history/*.jsonl.gz"):
    for line in gzip.open(f, "rt", encoding="utf-8"):
        r = json.loads(line); by[r["race_id"][:4]][r["race_id"]] = r
loose = glob.glob(f"{B}/races/*.json")
for f in loose:
    r = json.load(open(f)); by[r["race_id"][:4]][r["race_id"]] = r
for y, rs in by.items():
    with gzip.open(f"{B}/history/{y}.jsonl.gz", "wt", encoding="utf-8") as g:
        for k in sorted(rs): g.write(json.dumps(rs[k], ensure_ascii=False) + "\n")
for f in loose: os.remove(f)
print({y: len(v) for y, v in by.items()})
