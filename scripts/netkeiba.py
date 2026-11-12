"""netkeiba からデータを取得・解析する共通モジュール"""
import re, time, json, random
import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
S = requests.Session(); S.headers.update(UA)
PLACES = {"01":"札幌","02":"函館","03":"福島","04":"新潟","05":"東京","06":"中山","07":"中京","08":"京都","09":"阪神","10":"小倉"}

def get(url, tries=4, wait=0.35):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=(5, 15))
            if r.status_code == 200:
                time.sleep(wait + random.random()*0.3)
                raw = r.content
                try: return raw.decode("utf-8")
                except UnicodeDecodeError: return raw.decode("euc-jp", "ignore")
            if r.status_code in (400, 404): return None
            print("HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("ERR", type(e).__name__, url, flush=True)
        time.sleep(3 * (i + 1))
    return None

def race_ids_on(date):  # date: YYYYMMDD
    h = get(f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date}")
    if not h: return []
    ids = sorted(set(re.findall(r"race_id=(\d{12})", h)))
    return [i for i in ids if i[4:6] in PLACES]

def _num(x, f=float):
    try: return f(re.sub(r"[^\d.\-]", "", x))
    except Exception: return None

def _time_sec(t):
    m = re.match(r"(\d+):(\d+\.\d)", t or "")
    if m: return int(m.group(1))*60 + float(m.group(2))
    try: return float(t)
    except Exception: return None

def parse_cond(text):
    d = {}
    m = re.search(r"(芝|ダ|障)[^\d]*(\d{3,4})m", text)
    if m: d["surface"] = {"芝":"芝","ダ":"ダ","障":"障"}[m.group(1)]; d["distance"] = int(m.group(2))
    m = re.search(r"(良|稍重|稍|重|不良|不)", text.split("天候")[-1] if "天候" in text else text)
    for k, v in [("不良","不良"),("稍重","稍重"),("重","重"),("良","良")]:
        if re.search(r"(芝|ダート|馬場)\s*[:：]?\s*/?\s*" + k, text) or ("/ "+k) in text or (": "+k) in text:
            d["going"] = v; break
    m = re.search(r"天候\s*[:：]\s*(\S+?)\s*/", text)
    if m: d["weather"] = m.group(1)
    return d

def race_class(text):
    for k, v in [("G1",9),("GI)",9),("G2",8),("GII",8),("G3",7),("GIII",7),("オープン",6),("リステッド",6),("3勝",5),("1600万",5),("2勝",4),("1000万",4),("1勝",3),("500万",3),("未勝利",2),("新馬",1)]:
        if k in text: return v
    return 3

def parse_result(race_id):
    h = get(f"https://db.netkeiba.com/race/{race_id}/")
    if not h: return None
    s = BeautifulSoup(h, "lxml")
    t = s.select_one("table.race_table_01")
    if not t: return None
    intro = s.select_one(".data_intro")
    it = intro.get_text(" ", strip=True) if intro else ""
    race = {"race_id": race_id, "date": None, "place": PLACES.get(race_id[4:6]), "r": int(race_id[10:12])}
    m = re.search(r"(\d{4})年(\d{2})月(\d{2})日", it)
    if m: race["date"] = "".join(m.groups())
    h1 = s.select_one(".data_intro h1")
    race["name"] = h1.get_text(strip=True) if h1 else ""
    race.update(parse_cond(it)); race["class"] = race_class(it + race["name"])
    race["handicap"] = "ハンデ" in it
    rows = []
    for tr in t.select("tr")[1:]:
        c = [td.get_text(" ", strip=True) for td in tr.select("td")]
        if len(c) < 20: continue
        hid = jid = tid = None
        for a in tr.select("a"):
            href = a.get("href", "")
            if "/horse/" in href and not hid and "training" not in href and "kyusya" not in href: hid = re.findall(r"horse/(\w+)", href)[0]
            elif "/jockey/" in href: jid = re.findall(r"/(\w+)/?$", href.rstrip("/"))[0] if re.findall(r"/(\w+)/?$", href.rstrip("/")) else None
            elif "/trainer/" in href: tid = re.findall(r"/(\w+)/?$", href.rstrip("/"))[0] if re.findall(r"/(\w+)/?$", href.rstrip("/")) else None
        wt = re.match(r"(\d+)\(([-+]?\d+)\)", c[18] or "")
        rows.append({
            "rank": _num(c[0], int), "waku": _num(c[1], int), "umaban": _num(c[2], int), "name": c[3],
            "sex": c[4][:1], "age": _num(c[4][1:], int), "kinryo": _num(c[5]), "jockey": c[6],
            "time": _time_sec(c[7]), "passing": c[14], "last3f": _num(c[15]), "odds": _num(c[16]), "pop": _num(c[17], int),
            "weight": int(wt.group(1)) if wt else None, "wdiff": int(wt.group(2)) if wt else None,
            "trainer": c[22], "horse_id": hid, "jockey_id": jid, "trainer_id": tid,
        })
    race["n"] = len(rows); race["horses"] = rows
    pay = {}
    for pt in s.select("table.pay_table_01"):
        for tr in pt.select("tr"):
            th = tr.select_one("th"); tds = tr.select("td")
            if not th or len(tds) < 2: continue
            nums = tds[0].get_text("|", strip=True).split("|"); yen = tds[1].get_text("|", strip=True).split("|")
            pay[th.get_text(strip=True)] = [[n, _num(y, int)] for n, y in zip(nums, yen)]
    race["payout"] = pay
    return race

def parse_card(race_id):
    """出馬表（レース前）"""
    h = get(f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}")
    if not h: return None
    s = BeautifulSoup(h, "lxml")
    d1 = s.select_one(".RaceData01"); d2 = s.select_one(".RaceData02")
    t1 = d1.get_text(" ", strip=True) if d1 else ""; t2 = d2.get_text(" ", strip=True) if d2 else ""
    nm = s.select_one(".RaceName")
    race = {"race_id": race_id, "place": PLACES.get(race_id[4:6]), "r": int(race_id[10:12]), "name": nm.get_text(strip=True) if nm else ""}
    m = re.search(r"(\d{1,2}:\d{2})発走", t1); race["start"] = m.group(1) if m else ""
    m = re.search(r"(芝|ダ|障)(\d{3,4})m", t1)
    if m: race["surface"] = m.group(1); race["distance"] = int(m.group(2))
    for k in ["不良","稍重","稍","重","良"]:
        if "馬場:"+k in t1.replace(" ", ""): race["going"] = {"稍":"稍重"}.get(k, k); break
    race["class"] = race_class(t2 + race["name"] + (s.select_one(".RaceName").decode() if nm else ""))
    g = re.findall(r"Icon_GradeType(\d+)\b", str(nm.parent if nm else ""))
    gm = {"1": 9, "2": 8, "3": 7, "15": 6, "16": 6, "5": 6}
    for x in g:
        if x in gm: race["class"] = gm[x]; break
    race["handicap"] = "ハンデ" in t2
    rows = []
    for tr in s.select("tr.HorseList"):
        if "Cancel" in " ".join(tr.get("class", [])): continue
        tds = tr.select("td")
        c = [td.get_text(" ", strip=True) for td in tds]
        if len(c) < 8: continue
        a = tr.select_one(".HorseName a"); j = tr.select_one(".Jockey a"); tn = tr.select_one(".Trainer a")
        wk = tr.select_one("td[class^=Waku]"); ub = tr.select_one("td[class^=Umaban]")
        wt = re.match(r"(\d+)\s*\(([-+]?\d+)\)", (tr.select_one(".Weight").get_text(strip=True) if tr.select_one(".Weight") else ""))
        sexage = tr.select_one(".Barei").get_text(strip=True) if tr.select_one(".Barei") else c[4]
        rows.append({
            "waku": _num(wk.get_text(), int) if wk else None, "umaban": _num(ub.get_text(), int) if ub else None,
            "name": a.get_text(strip=True) if a else c[3], "sex": sexage[:1], "age": _num(sexage[1:], int),
            "kinryo": _num(c[5]), "jockey": j.get_text(strip=True) if j else "", "trainer": tn.get_text(strip=True) if tn else "",
            "horse_id": re.findall(r"horse/(\w+)", a["href"])[0] if a else None,
            "jockey_id": re.findall(r"/(\w+)/?$", j["href"].rstrip("/"))[0] if j else None,
            "trainer_id": re.findall(r"/(\w+)/?$", tn["href"].rstrip("/"))[0] if tn else None,
            "weight": int(wt.group(1)) if wt else None, "wdiff": int(wt.group(2)) if wt else None,
        })
    race["n"] = len(rows); race["horses"] = rows
    return race

def get_odds(race_id):
    try:
        r = S.get(f"https://race.netkeiba.com/api/api_get_jra_odds.html?race_id={race_id}&type=1&action=update", timeout=20)
        j = r.json(); o = j.get("data", {}).get("odds", {}).get("1", {}) if isinstance(j.get("data"), dict) else {}
        time.sleep(0.4)
        out = {}
        for k, v in o.items():
            try:
                if v and float(v[0]) > 0: out[int(k)] = float(v[0])
            except ValueError: pass
        return out, j.get("status")
    except Exception:
        return {}, None
