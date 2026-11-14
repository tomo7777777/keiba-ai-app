import sys, re, json, datetime as dt
sys.path.insert(0,'.'); import netkeiba as nk
from concurrent.futures import ThreadPoolExecutor
A=dt.date(2021,1,1); B=dt.date(2025,6,30)
dates=[(A+dt.timedelta(days=k)).strftime("%Y%m%d") for k in range((B-A).days+1)]
def f(d):
    h=nk.get(f'https://db.netkeiba.com/race/list/{d}/', wait=0)
    return d, sorted(set(re.findall(r'/race/(\d{12})/', h or '')))
with ThreadPoolExecutor(10) as ex: L=list(ex.map(f,dates))
NARP={"30","35","36","42","43","44","45","46","47","48","50","51","54","55"}
jra=[i for d,l in L if d<="20231231" for i in l if i[4:6] in {f"{k:02d}" for k in range(1,11)}]
nar=[i for d,l in L if d>="20230701" for i in l if i[4:6] in NARP]
json.dump(jra,open('../data/ids_20210101_20231231.json','w')); json.dump(nar,open('../data/nar/ids_20230701_20250630.json','w'))
print('jra',len(jra),'nar',len(nar), 'empty days', sum(1 for d,l in L if not l))
