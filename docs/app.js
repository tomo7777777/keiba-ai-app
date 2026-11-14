const $ = (s, el = document) => el.querySelector(s);
const app = $('#app'), sel = $('#dateSel');
const state = { index: null, day: null, record: null, backtest: null, place: null };
const yen = n => (n ?? 0).toLocaleString('ja-JP');
const pct = (a, b) => b ? (a / b * 100).toFixed(1) + '%' : '-';
const fmtDate = d => `${+d.slice(4, 6)}/${+d.slice(6, 8)}(${'日月火水木金土'[new Date(+d.slice(0,4), +d.slice(4,6)-1, +d.slice(6,8)).getDay()]})`;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const CLS = {1:'新馬',2:'未勝利',3:'1勝C',4:'2勝C',5:'3勝C',6:'OP',7:'G3',8:'G2',9:'G1'};

async function j(url) { const r = await fetch(url + '?t=' + Date.now()); if (!r.ok) throw new Error(url); return r.json(); }

async function init() {
  try { state.index = await j('data/index.json'); } catch { state.index = { days: [] }; }
  const days = state.index.days || [];
  sel.innerHTML = days.map(d => `<option value="${d}">${fmtDate(d)}</option>`).join('') || '<option>予想なし</option>';
  sel.onchange = () => loadDay(sel.value);
  if (days.length) await loadDay(days[0]); else route();
}
async function loadDay(d) {
  try { state.day = await j(`data/days/${d}.json`); } catch { state.day = null; }
  state.place = null; route();
}
window.addEventListener('hashchange', route);

function route() {
  const h = location.hash.replace('#/', '') || 'today';
  document.querySelectorAll('.tabs a').forEach(a => a.classList.toggle('on', a.dataset.tab === h));
  sel.style.visibility = (h === 'today' || h === 'pick') ? 'visible' : 'hidden';
  ({ today: viewToday, pick: viewPick, myomi: viewMyomi, record: viewRecord, about: viewAbout }[h] || viewToday)();
  window.scrollTo(0, 0);
}

function raceSummary(r, open = false) {
  const hon = r.bets?.honmei, ner = r.bets?.nerai;
  const hitB = (hon?.hit || ner?.hit) ? '<span class="b hit">的中</span>' : '';
  const top = [...r.horses].sort((a, b) => b.pw - a.pw).slice(0, 3);
  const res = r.result ? `<div class="top3">◎${top[0].umaban}（${top[0].rank ?? '-'}着）　結果 <b>${r.result.order.join('-')}</b></div>` :
    `<div class="top3">◎${top[0].umaban} ${esc(top[0].name)}</div>`;
  return `<details class="race" ${open ? 'open' : ''}><summary>
    <span class="rno">${r.place?.slice(0,2) ?? ''}<br>${r.r}R</span>
    <span class="rname">${esc(r.name)}${r.class >= 6 ? ` <span class="b conf">${CLS[r.class]}</span>` : ''}</span>
    <span class="badges">${hon ? '<span class="b hon">本命</span>' : ''}${ner ? '<span class="b ner">狙い</span>' : ''}${hitB}<span class="b conf">自信 ${Math.round(r.confidence * 100)}</span></span>
    <span class="rsub">${esc(r.start)} ${esc(r.surface ?? '')}${r.distance ?? ''}m ${r.n}頭${r.going ? ' ' + esc(r.going) : ''}</span>
    ${res}
  </summary><div class="body">${betsHtml(r)}${tableHtml(r)}</div></details>`;
}

function betsHtml(r) {
  const out = [];
  for (const [k, b] of Object.entries(r.bets || {})) {
    const winSet = new Set();
    if (r.result) for (const [kind, combo] of b.tickets) if (isWin(kind, combo, r.result.payout)) winSet.add(kind + combo);
    const tks = b.tickets.map(([kind, combo]) => `<span class="${winSet.has(kind + combo) ? 'win' : ''}">${kind} ${combo}</span>`).join('');
    const res = b.inv !== undefined ? `<div class="res">投資 ${yen(b.inv)}円 → 払戻 <b>${yen(b.ret)}円</b>（回収率 ${pct(b.ret, b.inv)}）</div>` : `<div class="res">各100円・計${yen(b.tickets.length * 100)}円</div>`;
    const note = k === 'nerai' ? (() => { const h = r.horses.find(x => x.umaban === b.horse); return h ? `期待値 ${h.ev ?? '-'}` : ''; })() : `◎勝率 ${Math.round(r.confidence * 100)}%`;
    out.push(`<div class="bet ${k}"><h4><span>${b.label}</span><span class="legend">${note}</span></h4><div class="tk">${tks}</div>${res}</div>`);
  }
  return out.length ? `<div class="bets">${out.join('')}</div>` : '<p class="legend" style="margin:10px 2px">このレースは買い目なし（印のみ）</p>';
}
function isWin(kind, combo, payout) {
  const un = ['馬連','ワイド','三連複','枠連'].includes(kind);
  const key = s => { const v = String(s).split('-').map(Number); return (un ? v.sort((a,b)=>a-b) : v).join('-'); };
  return (payout[kind] || []).some(([n]) => key(n) === key(combo));
}
function tableHtml(r) {
  const hs = [...r.horses].sort((a, b) => a.umaban - b.umaban);
  const mx = Math.max(...hs.map(h => h.pw));
  const rows = hs.map(h => {
    const mi = ['◎','○','▲'].indexOf(h.mark);
    const odds = h.final_odds ?? h.odds;
    return `<tr>
      <td class="mk m${mi}">${h.mark || ''}</td>
      <td><span class="uma w${h.waku}">${h.umaban}</span></td>
      <td><div class="hn">${esc(h.name)}</div><div class="hs">${esc(h.sex)}${h.age ?? ''} ${h.kinryo ?? ''} ${esc(h.jockey)}${h.weight ? ` ${h.weight}(${h.wdiff > 0 ? '+' : ''}${h.wdiff})` : ''}</div></td>
      <td class="num">${(h.pw * 100).toFixed(1)}<div class="bar"><i style="width:${h.pw / mx * 100}%"></i></div></td>
      <td class="num">${Math.round(h.p3 * 100)}</td>
      <td class="num">${odds ?? '-'}</td>
      <td class="num ${h.ev >= 1.3 ? 'ev-hi' : ''}">${h.ev ?? '-'}</td>
      ${r.result ? `<td class="num rk ${h.rank === 1 ? 'rk1' : ''}">${h.rank ?? '-'}</td>` : ''}
    </tr>`;
  }).join('');
  return `<table class="tbl"><thead><tr><th></th><th>馬</th><th>馬名・騎手</th><th class="num">勝率%</th><th class="num">3着内%</th><th class="num">単勝</th><th class="num">期待値</th>${r.result ? '<th class="num">着</th>' : ''}</tr></thead><tbody>${rows}</tbody></table>
  <p class="legend">オッズ ${r.result ? '確定' : (r.odds_time ? r.odds_time + '時点' : '')}／期待値＝AI勝率×単勝オッズ（1.0超で理論上プラス）</p>`;
}

function demoNote(d) { return d.demo ? '<div class="demo">これは過去の開催日を、その日より前のデータだけで学習したAIで再現したデモです（確定オッズ使用）。実際の成績には含めません。</div>' : ''; }
function noDay() { app.innerHTML = '<div class="notice">予想データがまだありません。<br>中央競馬の開催日（主に土日）の朝に自動で更新されます。</div>'; }

function viewToday() {
  const d = state.day; if (!d) return noDay();
  const places = [...new Set(d.races.map(r => r.place))];
  const p = state.place || places[0];
  const races = d.races.filter(r => r.place === p).sort((a, b) => a.r - b.r);
  app.innerHTML = `${demoNote(d)}<p class="meta">${d.demo ? fmtDate(d.date) + ' の再現' : `${fmtDate(d.date)} の予想（${d.fixed_at.slice(11, 16)} 確定・${(d.updated || '').slice(11, 16)} 更新）`}</p>
    <div class="place-chips">${places.map(x => `<button class="chip ${x === p ? 'on' : ''}" data-p="${x}">${x}</button>`).join('')}</div>
    ${races.map(r => raceSummary(r)).join('')}`;
  app.querySelectorAll('.chip').forEach(b => b.onclick = () => { state.place = b.dataset.p; viewToday(); });
}

function viewPick() {
  const d = state.day; if (!d) return noDay();
  const picks = d.races.filter(r => r.bets && Object.keys(r.bets).length).sort((a, b) => (a.start || '').localeCompare(b.start || '') || a.race_id.localeCompare(b.race_id));
  let inv = 0, ret = 0, settled = 0;
  picks.forEach(r => Object.values(r.bets).forEach(b => { if (b.inv !== undefined) { inv += b.inv; ret += b.ret; settled++; } }));
  const hon = picks.filter(r => r.bets.honmei).length, ner = picks.filter(r => r.bets.nerai).length;
  app.innerHTML = `${demoNote(d)}<div class="kpis">
    <div class="kpi"><div class="l">本命レース</div><div class="v">${hon}</div><div class="s">◎の勝率40%以上</div></div>
    <div class="kpi"><div class="l">狙いレース</div><div class="v">${ner}</div><div class="s">単勝10〜80倍・期待値1.3以上</div></div>
    <div class="kpi"><div class="l">この日の収支</div><div class="v ${ret - inv >= 0 ? 'plus' : 'minus'}">${settled ? (ret - inv >= 0 ? '+' : '') + yen(ret - inv) : '-'}</div><div class="s">円（各100円）</div></div>
    <div class="kpi"><div class="l">回収率</div><div class="v">${settled ? pct(ret, inv) : '-'}</div><div class="s">確定分のみ</div></div></div>
    ${picks.length ? picks.map(r => raceSummary(r)).join('') : '<div class="notice">この日は条件に合うレースがありません。</div>'}`;
}

async function viewRecord() {
  app.innerHTML = '<div class="skeleton"></div>';
  try { state.record = await j('data/record.json'); } catch { state.record = null; }
  try { state.backtest = await j('data/backtest.json'); } catch { state.backtest = null; }
  const rec = state.record, bt = state.backtest;
  const st = rec?.strategies || {};
  const k = (name, s, sub) => s && s.races ? `<div class="kpi"><div class="l">${name} 回収率</div><div class="v ${s.ret >= s.inv ? 'plus' : 'minus'}">${pct(s.ret, s.inv)}</div><div class="s">${sub} ${s.hit_races}/${s.races}R的中</div></div>` :
    `<div class="kpi"><div class="l">${name} 回収率</div><div class="v">-</div><div class="s">記録待ち</div></div>`;
  const m = rec?.marks || {};
  let html = `<h2 class="sec">実際の成績（公開後）</h2><div class="kpis">${k('本命', st.honmei, '')}${k('狙い', st.nerai, '')}
    <div class="kpi"><div class="l">◎の勝率</div><div class="v">${m.races ? pct(m.honmei_win, m.races) : '-'}</div><div class="s">${m.races || 0}レース</div></div>
    <div class="kpi"><div class="l">◎の3着内率</div><div class="v">${m.races ? pct(m.honmei_top3, m.races) : '-'}</div><div class="s"></div></div></div>`;
  if (rec?.days?.length) {
    html += `<div class="card"><h3>日別</h3><table class="tbl"><thead><tr><th>日付</th><th class="num">本命</th><th class="num">狙い</th></tr></thead><tbody>${
      [...rec.days].reverse().map(d => `<tr><td>${fmtDate(d.date)}</td><td class="num">${d.honmei ? pct(d.honmei.ret, d.honmei.inv) : '-'}</td><td class="num">${d.nerai ? pct(d.nerai.ret, d.nerai.inv) : '-'}</td></tr>`).join('')}</tbody></table></div>`;
  }
  if (bt) {
    html += `<h2 class="sec">過去データでの検証（${esc(bt.period)}）</h2>
    <div class="card"><p class="legend" style="margin-top:0">学習に使っていない期間のレースで、同じ条件の買い方を試した結果です。確定オッズで計算しているため、実際とは差が出ます。「狙い」の回収率は少数の高配当に支えられた数字で、まだ実力とは言い切れません。公開後の実績で確かめます。</p>
    <table class="tbl"><thead><tr><th>買い方</th><th class="num">レース</th><th class="num">的中率</th><th class="num">回収率</th></tr></thead><tbody>
    ${bt.rows.map(r => `<tr><td>${esc(r.name)}</td><td class="num">${r.races}</td><td class="num">${r.hit}</td><td class="num">${r.roi}</td></tr>`).join('')}</tbody></table></div>`;
  }
  app.innerHTML = html;
}

function viewAbout() {
  app.innerHTML = `<div class="card"><h3>見方</h3><ul>
  <li><b>勝率%</b>：AIが計算した1着になる確率。レース内の合計が100%です。</li>
  <li><b>3着内%</b>：3着以内に入る確率。</li>
  <li><b>期待値</b>：勝率×単勝オッズ。1.0を超えると「オッズが割安」の目安です。</li>
  <li><b>印</b>：勝率の高い順に ◎○▲△△。</li></ul></div>
  <div class="card"><h3>勝負レースの条件</h3><ul>
  <li><b>本命</b>：◎の勝率が40%以上のレース。単勝◎、馬連◎-○、ワイド◎-○、ワイド◎-▲ の計4点。</li>
  <li><b>狙い</b>：単勝10〜80倍で、期待値1.3以上の馬（1レース1頭）。単勝1点。当たりは少なく、外れが続くこともあります。</li>
  <li>印と買い目は当日朝に固定し、後から変えません。オッズの表示だけ更新されます。</li></ul></div>
  <div class="card"><h3>AIの中身</h3><p>2024年以降の中央競馬約1万レースの結果から、馬の近走成績・走破タイムの速さ・上がり3F・距離や馬場の適性・騎手と調教師の成績・枠順・斤量・馬体重、そして単勝オッズ（世間の評価）を合わせて学習しています。毎週火曜に最新の結果で学習し直します。</p>
  <p>印と買い目は、当日朝に単勝オッズが出そろった時点で固定します。</p></div>
  <div class="card"><h3>妙味軸とは（試験運用）</h3>
  <p>1番人気ではなく、<b>単勝3〜10倍の中から「人気から見た3着以内の確率」よりAIの確率が1.3倍以上高い馬</b>を1頭選び、軸にします。</p>
  <p>買い方は各100円で、複勝（軸）・ワイド（軸-相手3頭）・馬連（軸-相手5頭）・3連複（軸-相手4頭の6点）。相手はAIの3着内確率が高い順です。</p>
  <p>各レースの発走40分前ごろのオッズで判定し、それ以降は変えません。条件に合う馬がいないレースは見送ります（1日に数レース程度）。</p>
  <p>過去データでは回収率100%超えの買い方もありましたが、件数が少なく偶然の可能性があります。実際の成績で確かめていきます。</p></div>`;
}

/* ===== 妙味軸（中央・地方） ===== */
const MY = { circuit: 'nar', idx: {}, date: {}, day: null, rec: {}, bt: null };
const BET_ORDER = ['fuku', 'wide', 'umaren', 'sanfuku'];
async function viewMyomi() {
  const c = MY.circuit;
  app.innerHTML = '<div class="skeleton"></div>';
  if (!MY.idx[c]) { try { MY.idx[c] = await j(`data/myomi/${c}/index.json`); } catch { MY.idx[c] = { days: [] }; } }
  try { MY.rec[c] = await j(`data/myomi/${c}/record.json`); } catch { MY.rec[c] = null; }
  if (!MY.bt) { try { MY.bt = await j('data/myomi/backtest.json'); } catch { MY.bt = {}; } }
  const days = MY.idx[c].days || [];
  const d = MY.date[c] || days[0];
  MY.day = null;
  if (d) { try { MY.day = await j(`data/myomi/${c}/days/${d}.json`); } catch {} }
  const day = MY.day;
  const races = day ? [...day.races].sort((a, b) => (a.start || '').localeCompare(b.start || '') || a.race_id.localeCompare(b.race_id)) : [];
  const picks = races.filter(r => r.pick), skip = races.filter(r => r.status === 'locked' && !r.pick);
  const wait = races.filter(r => r.status === 'wait');
  let inv = 0, ret = 0, settled = 0;
  picks.forEach(r => Object.values(r.pick.bets).forEach(b => { if (b.inv !== undefined) { inv += b.inv; ret += b.ret; settled++; } }));
  const head = `<div class="place-chips">
      <button class="chip ${c === 'nar' ? 'on' : ''}" data-c="nar">地方</button>
      <button class="chip ${c === 'jra' ? 'on' : ''}" data-c="jra">中央</button>
      ${days.length ? `<select class="msel" aria-label="日付">${days.map(x => `<option value="${x}" ${x === d ? 'selected' : ''}>${fmtDate(x)}</option>`).join('')}</select>` : ''}
    </div>
    <div class="demo myomi-note">試験運用中：1番人気以外から、人気より実力が上とAIが見た馬を軸にします。最近のデータでは100%超えでしたが、古い期間では届かず（地方の複勝で97%）、まだ儲かる方法とは言えません。記録用として続けています。</div>`;
  let body = '';
  if (!day) body = `<div class="notice">${c === 'nar' ? '地方競馬' : '中央競馬'}の妙味軸はまだありません。<br>開催日に、各レースの発走40分前ごろ自動で判定します。</div>`;
  else {
    body = `<div class="kpis">
      <div class="kpi"><div class="l">軸レース</div><div class="v">${picks.length}</div><div class="s">判定済み ${picks.length + skip.length} / ${races.length}R</div></div>
      <div class="kpi"><div class="l">この日の収支</div><div class="v ${ret - inv >= 0 ? 'plus' : 'minus'}">${settled ? (ret - inv >= 0 ? '+' : '') + yen(ret - inv) : '-'}</div><div class="s">円（各100円・全券種）</div></div></div>
      ${picks.length ? picks.map(myomiCard).join('') : `<div class="notice">${wait.length ? 'まだ判定前です。発走40分前ごろに判定します。' : 'この日は条件に合う軸がありませんでした。'}</div>`}
      ${wait.length ? `<p class="legend">判定待ち ${wait.length}R（次は ${esc(wait[0].place)}${wait[0].r}R ${esc(wait[0].start)}発走）</p>` : ''}
      ${skip.length ? `<details class="race"><summary><span class="rname">見送り ${skip.length}R</span><span class="rsub">条件（単勝3〜10倍・ズレ1.3倍以上）に合う馬なし</span></summary><div class="body"><p class="legend">${skip.map(r => `${esc(r.place)}${r.r}R`).join('・')}</p></div></details>` : ''}`;
  }
  app.innerHTML = head + body + myomiRecord(c);
  app.querySelectorAll('.chip[data-c]').forEach(b => b.onclick = () => { MY.circuit = b.dataset.c; viewMyomi(); });
  const ms = app.querySelector('.msel'); if (ms) ms.onchange = () => { MY.date[c] = ms.value; viewMyomi(); };
}
function myomiCard(r) {
  const p = r.pick, ax = r.horses.find(h => h.umaban === p.axis) || {};
  const name = u => (r.horses.find(h => h.umaban === u) || {}).name || '';
  const bets = BET_ORDER.filter(k => p.bets[k]).map(k => {
    const b = p.bets[k];
    const tks = b.tickets.map(t => { const w = r.result && isWin(t[0], t[1], r.result.payout); return `<span class="${w ? 'win' : ''}">${t[1]}${t[3] && t[0] !== '複勝' ? `<small> ${t[3]}倍${t[0] === 'ワイド' ? '〜' : ''}</small>` : ''}</span>`; }).join('');
    const res = b.inv !== undefined ? `<div class="res">${yen(b.inv)}円 → <b>${yen(b.ret)}円</b></div>` : `<div class="res">${b.tickets.length}点・${yen(b.tickets.length * 100)}円</div>`;
    return `<div class="bet myomi"><h4><span>${b.label}</span></h4><div class="tk">${tks}</div>${res}</div>`;
  }).join('');
  const hit = p.bets && Object.values(p.bets).some(b => b.hit > 0);
  const res = r.result ? `<div class="top3">軸 ${ax.rank ?? '-'}着　結果 <b>${r.result.order.join('-')}</b></div>` : '';
  return `<details class="race" open><summary>
    <span class="rno">${esc((r.place || '').slice(0, 2))}<br>${r.r}R</span>
    <span class="rname">${esc(r.name)}</span>
    <span class="badges">${hit ? '<span class="b hit">的中</span>' : ''}<span class="b ner">ズレ ${p.gap}倍</span></span>
    <span class="rsub">${esc(r.start)}発走 ${esc(r.surface ?? '')}${r.distance ?? ''}m ${r.n}頭・${esc(r.locked_at)}判定</span>${res}
  </summary><div class="body">
    <div class="axis"><span class="uma w${ax.waku}">${ax.umaban}</span><div><div class="hn">${esc(ax.name)}</div>
      <div class="hs">${esc(ax.jockey)}・単勝 ${ax.odds}倍（${ax.pop}番人気）</div>
      <div class="hs">3着以内の確率：AI <b>${Math.round(ax.p3 * 100)}%</b> ／ 人気から見ると ${Math.round(ax.m3 * 100)}%</div></div></div>
    <p class="legend">相手（AIの3着内確率順）：${p.partners.map(u => `${u} ${esc(name(u))}`).join('、')}</p>
    <div class="bets">${bets}</div></div></details>`;
}
function btTable(rows) {
  return `<table class="tbl"><thead><tr><th>買い方</th><th class="num">R</th><th class="num">回収率</th><th class="num">期間別</th></tr></thead><tbody>${rows.map(r => `<tr><td>${esc(r[0])}</td><td class="num">${r[1]}</td><td class="num ${r[2] >= 100 ? 'ev-hi' : ''}">${r[2]}%</td><td class="num">${esc(r[3])}</td></tr>`).join('')}</tbody></table>`;
}
function myomiRecord(c) {
  const rec = MY.rec[c], bt = (MY.bt || {})[c];
  let h = `<h2 class="sec">${c === 'nar' ? '地方' : '中央'}の妙味軸 実績</h2>`;
  if (rec && rec.axis_n) {
    h += `<div class="card"><p class="legend" style="margin-top:0">軸の3着内率 ${pct(rec.axis_top3, rec.axis_n)}（${rec.axis_n}R）</p><table class="tbl"><thead><tr><th>買い方</th><th class="num">R</th><th class="num">的中率</th><th class="num">回収率</th></tr></thead><tbody>${
      BET_ORDER.filter(k => rec.bets[k]).map(k => { const s = rec.bets[k]; return `<tr><td>${esc(s.label)}</td><td class="num">${s.races}</td><td class="num">${pct(s.hit_races, s.races)}</td><td class="num ${s.ret >= s.inv ? 'ev-hi' : ''}">${pct(s.ret, s.inv)}</td></tr>`; }).join('')}</tbody></table></div>`;
  } else h += '<div class="notice">実績はまだありません。結果が出しだい自動で集計します。</div>';
  if (bt) h += `<div class="card"><h3>過去データでの検証</h3><p class="legend" style="margin-top:0">${esc(bt.period)}・学習に使っていない期間。確定オッズで計算しているため実際とは差が出ます。</p>
    ${btTable(bt.rows)}${bt.old ? `<h3 style="margin-top:14px">古い期間での確認</h3><p class="legend" style="margin-top:0">${esc(bt.old.period)}。この期間では100%を超えませんでした。</p>${btTable(bt.old.rows)}` : ''}</div>`;
  return h;
}
init();
