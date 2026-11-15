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
  let [h, sub] = (location.hash.replace('#/', '') || 'today').split('/');
  if (h === 'myomi') h = MY.circuit;
  if (h === 'nar' || h === 'jra') MY.circuit = h;
  state.sub = sub || '';
  document.querySelectorAll('.tabs a').forEach(a => a.classList.toggle('on', a.dataset.tab === h));
  sel.style.visibility = (h === 'today' || h === 'pick') ? 'visible' : 'hidden';
  ({ today: viewToday, pick: viewPick, nar: viewMyomi, jra: viewMyomi, record: viewRecord, about: viewAbout }[h] || viewToday)();
  window.scrollTo(0, 0);
}
// 2段目のタブ
function subTabs(base, items, cur) {
  return `<nav class="subtabs">${items.map(([k, label, n]) => `<a href="#/${base}/${k}" class="${k === cur ? 'on' : ''}">${label}${n !== undefined ? `<span class="cnt">${n}</span>` : ''}</a>`).join('')}</nav>`;
}

function raceSummary(r, open = false) {
  const hon = r.bets?.honmei, ner = r.bets?.nerai;
  const bs = [hon, ner].filter(b => b && b.inv !== undefined), bi = bs.reduce((a, b) => a + b.inv, 0), br = bs.reduce((a, b) => a + b.ret, 0);
  const hitB = !bs.length ? '' : br === 0 ? `<span class="b pl-b lose">−${yen(bi)}円</span>` : br < bi ? `<span class="b pl-b gami">ガミ −${yen(bi - br)}円</span>` : `<span class="b hit">的中 +${yen(br - bi)}円</span>`;
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
  const fin = picks.filter(r => r.result), up = picks.filter(r => !r.result);
  const hon = up.filter(r => r.bets.honmei), ner = up.filter(r => r.bets.nerai);
  const cur = ['hon', 'ner', 'done'].includes(state.sub) ? state.sub : 'hon';
  let body = '';
  if (cur === 'hon') body = `<p class="legend sub-note">◎の勝率40%以上のレース。発走前のレースだけを表示します。</p>` + (hon.length ? hon.map(r => raceSummary(r)).join('') : '<div class="notice">発走前の本命レースはありません。<br>終わったレースは「終了」タブにあります。</div>');
  if (cur === 'ner') body = `<p class="legend sub-note">単勝10〜80倍・期待値1.3以上の馬がいるレース。発走前のレースだけを表示します。</p>` + (ner.length ? ner.map(r => raceSummary(r)).join('') : '<div class="notice">発走前の狙いレースはありません。<br>終わったレースは「終了」タブにあります。</div>');
  if (cur === 'done') body = `<div class="ev-day"><div><span class="l">この日の収支（結果が出た${fin.length}R）</span><span class="v ${ret - inv >= 0 ? 'plus' : 'minus'}">${settled ? (ret - inv >= 0 ? '+' : '−') + yen(Math.abs(ret - inv)) + '円' : '-'}</span></div><div class="s">${settled ? `購入 ${yen(inv)}円 → 払戻 ${yen(ret)}円（回収率 ${pct(ret, inv)}）` : 'まだ結果が出たレースはありません'}</div></div>`
    + (fin.length ? (() => { const fh = [...fin].reverse().filter(r => r.bets.honmei), fn = [...fin].reverse().filter(r => r.bets.nerai && !r.bets.honmei);
        return `<h3 class="ev-h">本命レース <small>${fh.length}R</small></h3>${fh.map(r => raceSummary(r)).join('') || '<p class="legend">なし</p>'}<h3 class="ev-h">狙いレース <small>${fn.length}R</small></h3>${fn.map(r => raceSummary(r)).join('') || '<p class="legend">なし</p>'}`; })() : '<div class="notice">まだ終わったレースはありません。</div>');
  app.innerHTML = demoNote(d) + subTabs('pick', [['hon', '本命', hon.length], ['ner', '狙い', ner.length], ['done', '終了', fin.length]], cur) + body;
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
  let html = `<div class="notice" style="text-align:left">このページは「勝負」タブ（中央AIの本命・狙い）の成績です。地方・中央の期待値AI（本命・穴）の成績は、<a href="#/nar/rec">地方の成績</a>・<a href="#/jra/rec">中央の成績</a>にあります。${st.honmei && st.honmei.races ? '' : '<br>実際の記録はまだありません。中央の開催日（土日）に予想が出ると、そのレースから記録が始まります。'}</div><h2 class="sec">勝負（中央AI）の実際の成績</h2><div class="kpis">${k('本命', st.honmei, '')}${k('狙い', st.nerai, '')}
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
  const head = `<div class="circ-band ${c}"><div class="circ-t">${c === 'nar' ? '地方競馬' : '中央競馬'}</div>
      ${days.length ? `<select class="msel" aria-label="日付">${days.map(x => `<option value="${x}" ${x === d ? 'selected' : ''}>${fmtDate(x)}</option>`).join('')}</select>` : ''}</div>`;
  const myNote = `<h2 class="sec">妙味軸（試験記録）</h2><div class="demo myomi-note">1番人気以外から、人気より実力が上とAIが見た馬を軸にします。古い期間では100%に届かず（地方の複勝で97%）、記録用として続けています。</div>`;
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
  const evs = races.filter(r => r.ev && r.ev.sel), fin = evs.filter(r => r.result), up = evs.filter(r => !r.result);
  const hon = up.filter(r => r.ev.sel.kind === 'hon'), ana = up.filter(r => r.ev.sel.kind === 'ana');
  const cands = races.filter(r => !r.ev && !r.result && r.cand && r.cand.kind && !evStarted(r)).sort((a, b) => (a.start || '').localeCompare(b.start || ''));
  const chon = cands.filter(r => r.cand.kind === 'hon'), cana = cands.filter(r => r.cand.kind === 'ana');
  const unchecked = races.filter(r => !r.ev && !r.result && !r.cand && !evStarted(r)).length;
  const candBlock = (list, k) => `<h3 class="ev-h">${k}の候補 <small>${list.length}R・予想は発走10分前ごろに確定して通知</small></h3>`
    + (list.length ? list.map(candCard).join('') : `<p class="legend">今のオッズでは${k}の候補はありません。</p>`)
    + (unchecked ? `<p class="legend">まだオッズを見ていないレース ${unchecked}R（発走4時間前から順に確認します）</p>` : '');
  const judged = races.filter(r => r.ev).length, nextW = races.filter(r => !r.ev && !r.result && !evStarted(r)).sort((a, b) => (a.start || '').localeCompare(b.start || ''))[0];
  const cur = ['hon', 'ana', 'done', 'rec', 'myomi'].includes(state.sub) ? state.sub : 'hon';
  const none = k => `<div class="notice">発走前の${k}レースはありません。<br>${nextW ? `各レースの発走10分前ごろに判定します（次は ${esc(nextW.place)}${nextW.r}R ${esc(nextW.start)}発走）。` : 'この日の判定は終わりました。'}<br>終わったレースは「終了」タブにあります。</div>`;
  let main = '';
  if (cur === 'hon') main = `<p class="legend sub-note">旨味のある馬が1〜3番人気で、期待値の条件を満たしたレースだけ（発走が近い順）。期待値1.5以上の組がある場合だけ出します。出ない日もあります。</p>` + (hon.length ? hon.map(evCard).join('') : none('本命')) + candBlock(chon, '本命');
  if (cur === 'ana') main = `<div class="notice"><b>穴は「混戦レース」だけに絞っています。</b>1番人気が3.0倍以上で、AIが人気より高く見ている4番人気以下の馬がいて、期待値1.5以上の組があるレースだけを出します。買い目はワイドだけです（3連単は停止中）。</div><p class="legend sub-note">旨味のある馬が4番人気以下のレース（発走が近い順）</p>` + (ana.length ? ana.map(evCard).join('') : none('穴')) + candBlock(cana, '穴');
  if (cur === 'done') {
    const fh = [...fin].reverse().filter(r => r.ev.sel.kind === 'hon'), fa = [...fin].reverse().filter(r => r.ev.sel.kind === 'ana');
    main = evDaySummary(fin) + (fin.length ? `<h3 class="ev-h">本命レース <small>${fh.length}R</small></h3>${fh.map(evCard).join('') || '<p class="legend">なし</p>'}<h3 class="ev-h">穴レース <small>${fa.length}R</small></h3>${fa.map(evCard).join('') || '<p class="legend">なし</p>'}` : '<div class="notice">まだ終わったレースはありません。</div>')
      + (judged ? `<p class="legend">判定済み ${judged}R（うち見送り ${judged - evs.length}R）</p>` : '');
  }
  if (cur === 'rec') main = evRecord(c);
  if (cur === 'myomi') main = myNote + body + myomiRecord(c);
  const warn = `<div class="demo"><b>検証中です。実際の購入はおすすめしません。</b>以前の検証は、レース後に決まる確定オッズで計算していました。発走前のオッズのずれを入れて計算し直すと、旧設定の回収率は91〜94%でした。11/15に設定を見直し、期待値1.5以上・ワイドのみ・発走10分前の判定にしました。それでも勝てると確かめられたわけではないので、記録して確かめている段階です。</div>`;
  app.innerHTML = head + warn + subTabs(c, [['hon', '本命', hon.length + chon.length], ['ana', '穴', ana.length + cana.length], ['done', '終了', fin.length], ['rec', '成績'], ['myomi', '妙味軸']], cur) + main;
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
// 期待値AI：券種ごとの1行（投資→払戻→収支と、的中／ガミ／ハズレ）
function evStat(inv, ret, settled) {
  if (!settled) return { cls: 'wait', label: '発走前', pl: '' };
  const d = ret - inv;
  const label = ret === 0 ? 'ハズレ' : d < 0 ? 'ガミ' : '的中';
  const cls = ret === 0 ? 'lose' : d < 0 ? 'gami' : 'win';
  return { cls, label, pl: (d > 0 ? '+' : d < 0 ? '−' : '±') + yen(Math.abs(d)) + '円' };
}
function evLine(r, name, tks, chips, res) {
  const settled = !!res, inv = res ? res.inv : tks.length * 100, ret = res ? res.ret : 0, st = evStat(inv, ret, settled);
  if (!settled && evStarted(r)) st.label = '結果待ち';
  return `<div class="evl ${st.cls}"><div class="evl-h"><b>${name}</b><span class="evb ${st.cls}">${st.label}</span>
    <span class="evl-m">${settled ? `${yen(inv)} → <b>${yen(ret)}円</b>` : `${tks.length}点 ${yen(inv)}円`}</span>
    ${settled ? `<span class="evl-pl">${st.pl}</span>` : ''}</div><div class="evl-t">${chips}</div></div>`;
}
function evStarted(r) {
  if (!r.start || !/^\d{8}$/.test(String(MY.date[MY.circuit] || (MY.day && MY.day.date) || ''))) return false;
  const d = String(MY.date[MY.circuit] || MY.day.date), [hh, mm] = r.start.split(':').map(Number);
  const t = new Date(`${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}T${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:00+09:00`);
  return Date.now() > t.getTime();
}
function candCard(r) {
  const c = r.cand, sd = (r.start || '').split(':').map(Number);
  const due = sd.length === 2 ? (() => { const m = sd[0] * 60 + sd[1] - 10; return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}`; })() : '';
  return `<div class="card cand"><div class="cand-h"><span class="tag cand-tag">候補</span><b>${esc(r.place)}${r.r}R</b><span class="rsub">${esc(r.start || '')}発走${due ? `・${due}ごろ確定` : ''}</span></div>
    <p class="cand-b">今のオッズなら軸 <b>${c.axis}番 ${esc(c.name || '')}</b>（${c.pop}番人気 ${c.odds}倍）</p>
    <p class="legend">${esc(c.at)}時点のオッズで計算。オッズが動くと、確定時に見送りや本命・穴の入れ替わりになることがあります。</p></div>`;
}
function evCard(r) {
  const s = r.ev.sel, pay = r.result && r.result.payout, win = t => pay && isWin(t[0], t[1], pay);
  const lines = [];
  lines.push(evLine(r, 'ワイド', s.tickets, s.tickets.map(t => `<span class="${win(t) ? 'win' : ''}">${t[1]}<small>${t[3]}倍</small></span>`).join(''), s.inv !== undefined ? { inv: s.inv, ret: s.ret } : null));
  if (s.san && s.san.length) lines.push(evLine(r, '3連複', s.san, s.san.map(t => `<span class="${win(t) ? 'win' : ''}">${t[1]}<small>${t[3]}倍</small></span>`).join(''), s.san_res));
  else if (s.san) lines.push(`<div class="evl skip"><div class="evl-h"><b>3連複</b><span class="evl-m">期待値のある組がなく見送り</span></div></div>`);
  if (s.tan && s.tan.length) {
    const second = [...new Set(s.tan.map(t => t[1].split('-')[1]))];
    const hit = s.tan.find(win);
    lines.push(evLine(r, '3連単 1着固定', s.tan, `<span class="form">1着 <b>${s.axis}</b> → 2・3着 ${second.join('・')}</span>${hit ? `<span class="win">${hit[1]}</span>` : ''}`, s.tan_res));
  }
  const parts = [[s.inv !== undefined, s.inv, s.ret, s.tickets.length], [!!s.san_res, s.san_res && s.san_res.inv, s.san_res && s.san_res.ret, (s.san || []).length], [!!s.tan_res, s.tan_res && s.tan_res.inv, s.tan_res && s.tan_res.ret, (s.tan || []).length]];
  const settled = !!r.result && s.inv !== undefined;
  const inv = parts.reduce((a, p) => a + (settled ? (p[1] || 0) : p[3] * 100), 0), ret = settled ? parts.reduce((a, p) => a + (p[2] || 0), 0) : 0;
  const st = evStat(inv, ret, settled);
  return `<div class="card ev-card ${st.cls}">
    <div class="evc-h"><b class="evc-r">${esc(r.place)} ${r.r}R</b>${r.ev.v ? '' : '<span class="tag old-tag">旧設定</span>'}<span class="evc-t">${esc(r.start)}発走</span>${r.result ? `<span class="evc-res">結果 <b>${r.result.order.join('-')}</b></span>` : evStarted(r) ? '<span class="evc-res hs">発走済み・結果待ち</span>' : ''}</div>
    <div class="evc-ax"><span class="uma">${s.axis}</span><div><b>${esc(s.name || '')}</b> <span class="hs">${s.pop}番人気・単勝${s.odds}倍・${esc(s.jockey || '')}</span>
      <div class="hs">3着内の確率 AI <b>${Math.round(s.p3 * 100)}%</b>（人気から見ると${Math.round(s.m3 * 100)}%）</div></div></div>
    ${lines.join('')}
    <div class="evc-sum ${st.cls}"><span>合計</span>${settled ? `<span class="evb ${st.cls}">${ret > 0 && ret < inv ? 'ガミ（損）' : ret >= inv ? 'プラス' : 'ハズレ'}</span>` : ''}<span>${settled ? `${yen(inv)} → <b>${yen(ret)}円</b>` : `購入 ${yen(inv)}円`}</span>${settled ? `<b class="evc-pl">${st.pl}</b>` : `<span class="hs">${esc(r.ev.at)}判定</span>`}</div></div>`;
}
function evDaySummary(fin) {
  let inv = 0, ret = 0;
  for (const r of fin) { const s = r.ev.sel; for (const x of [{ inv: s.inv, ret: s.ret }, s.san_res, s.tan_res]) if (x) { inv += x.inv; ret += x.ret; } }
  const d = ret - inv;
  return `<div class="ev-day"><div><span class="l">この日の収支（結果が出た${fin.length}R）</span><span class="v ${fin.length ? (d >= 0 ? 'plus' : 'minus') : ''}">${fin.length ? (d >= 0 ? '+' : '−') + yen(Math.abs(d)) + '円' : '-'}</span></div><div class="s">${fin.length ? `購入 ${yen(inv)}円 → 払戻 ${yen(ret)}円（回収率 ${pct(ret, inv)}）` : 'まだ結果が出たレースはありません'}</div></div>`;
}
function evRecord(c) {
  const rec = (MY.rec[c] || {}).ev || {}, bt = ((MY.bt || {})[c] || {}).ev;
  let h = '';
  const keys = ['hon', 'hon_san', 'hon_tan', 'ana', 'ana_san', 'ana_tan'].filter(k => rec[k]);
  h += `<div class="card"><h3>新設定の通算成績 <small class="hs">11/15夜から</small></h3>` + (keys.length ? `<p class="legend" style="margin-top:0">的中率は「払戻があったレース」の割合です（ガミも含む）。損得は回収率と収支で見てください。</p><table class="tbl"><thead><tr><th>種類</th><th class="num">R</th><th class="num">的中率</th><th class="num">回収率</th><th class="num">収支</th></tr></thead><tbody>${keys.map(k => { const x = rec[k], d = x.ret - x.inv; return `<tr><td>${esc(x.label.replace('レース', ''))}</td><td class="num">${x.races}</td><td class="num">${pct(x.hit_races, x.races)}</td><td class="num ${x.ret >= x.inv ? 'ev-hi' : ''}">${pct(x.ret, x.inv)}</td><td class="num ${d >= 0 ? 'pl-plus' : 'pl-minus'}">${d >= 0 ? '+' : '−'}${yen(Math.abs(d))}円</td></tr>`; }).join('')}</tbody></table>` : '<p class="legend">まだ記録がありません。結果が出しだい自動で集計します。</p>') + '</div>';
  const old = (MY.rec[c] || {}).ev_old;
  if (old) { let oi = 0, orr = 0; for (const x of Object.values(old)) { oi += x.inv; orr += x.ret; } const od = orr - oi;
    h += `<details class="card"><summary><b>旧設定の成績（11/15まで）</b> <span class="hs">${od >= 0 ? '+' : '−'}${yen(Math.abs(od))}円</span></summary><p class="legend">発走15分前の判定・期待値1.2/1.0・3連単ありの旧設定の結果です。上の通算成績には含めていません。</p><table class="tbl"><thead><tr><th>種類</th><th class="num">R</th><th class="num">回収率</th><th class="num">収支</th></tr></thead><tbody>${Object.values(old).map(x => { const d = x.ret - x.inv; return `<tr><td>${esc(x.label.replace('レース', ''))}</td><td class="num">${x.races}</td><td class="num">${pct(x.ret, x.inv)}</td><td class="num ${d >= 0 ? 'pl-plus' : 'pl-minus'}">${d >= 0 ? '+' : '−'}${yen(Math.abs(d))}円</td></tr>`; }).join('')}</tbody></table></details>`; }
  if (bt) h += `<div class="card"><h3>過去データでの検証</h3><p class="legend" style="margin-top:0">${esc(bt.period)}</p><table class="tbl"><thead><tr><th>種類</th><th class="num">R</th><th class="num">的中率</th><th class="num">回収率</th><th class="num">期間別</th></tr></thead><tbody>${bt.rows.map(r => `<tr><td>${esc(r[0])}</td><td class="num">${r[1]}</td><td class="num">${r[2]}%</td><td class="num ${r[3] >= 100 ? 'ev-hi' : ''}">${r[3]}%</td><td class="num">${esc(r[4])}</td></tr>`).join('')}</tbody></table><p class="legend">${esc(bt.note)}</p></div>`;
  h += `<details class="card"><summary><b>期待値AIのしくみ</b></summary><p class="legend">発走10分前ごろの最新オッズで、ワイドの全組み合わせの「来る確率×オッズ」を計算します。AIの評価が人気より高い馬のうち、期待値のある組に一番多く絡む馬を「旨味のある馬」として軸にし、軸が1〜3番人気なら本命レース、4番人気以下なら穴レースに分けます。${c === 'jra' ? '中央は過去検証で結果が大きくぶれたため、地方より信頼度は低めです。' : ''}「ガミ」は当たったのに払戻が購入額より少ない（損した）ことです。</p></details>`;
  return h;
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
