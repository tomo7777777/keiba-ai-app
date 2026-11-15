"""スマホ通知（ntfy）。環境変数 NTFY_TOPIC があるときだけ送る"""
import os, requests

APP = "https://tomo7777777.github.io/keiba-ai-app/"

def send(title, message, click=None, tags=None, priority=4):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic: return False
    try:
        r = requests.post("https://ntfy.sh/", json={"topic": topic, "title": title, "message": message,
                          "click": click or APP, "tags": tags or [], "priority": priority}, timeout=15)
        return r.ok
    except Exception as e:
        print("通知エラー", type(e).__name__, e); return False

def ev_pick(circuit, r, sel):
    """期待値AIの本命／穴が決まったときの通知"""
    nar = circuit == "nar"; kind = "本命" if sel["kind"] == "hon" else "穴"
    title = f"【検証中】{'地方' if nar else '中央'}{kind} {r['place']}{r['r']}R {r.get('start', '')}発走"
    lines = [f"軸 {sel['axis']}番 {sel.get('name', '')}（{sel.get('pop')}番人気 {sel.get('odds')}倍）"]
    tk = sel.get("tickets") or []
    if tk: lines.append("ワイド " + " ".join(t[1] for t in tk) + f"（{len(tk)}点）")
    tan = sel.get("tan") or []
    if tan:
        sub = []
        for t in tan:
            for u in t[1].split("-")[1:]:
                if u not in sub: sub.append(u)
        lines.append(f"3連単 1着{sel['axis']} → 2・3着 {','.join(sub)}（{len(tan)}点）")
    san = sel.get("san") or []
    if san: lines.append("3連複 " + " ".join(t[1] for t in san) + f"（{len(san)}点）")
    inv = 100 * (len(tk) + len(tan) + len(san))
    lines.append(f"合計 {inv:,}円（各100円）")
    return send(title, "\n".join(lines), click=APP + f"#/{circuit}/{sel['kind']}",
                tags=["horse_racing"] if sel["kind"] == "hon" else ["dart"], priority=4 if sel["kind"] == "hon" else 3)
