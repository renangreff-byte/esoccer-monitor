const cfg = window.ES_CONFIG || {};
const state = { league: null };
const $ = s => document.querySelector(s);
const fmt = n => Number(n ?? 0).toLocaleString('pt-BR', {maximumFractionDigits:2});
const pct = n => `${fmt(n)}%`;

async function rest(path, params={}){
  if(!cfg.SUPABASE_URL || !cfg.SUPABASE_ANON_KEY) throw new Error('Configuração do Supabase ausente em web/config.js');
  const u = new URL(`${cfg.SUPABASE_URL}/rest/v1/${path}`);
  Object.entries(params).forEach(([k,v]) => v!==null && v!==undefined && u.searchParams.set(k,v));
  const r = await fetch(u, {headers:{apikey:cfg.SUPABASE_ANON_KEY,Authorization:`Bearer ${cfg.SUPABASE_ANON_KEY}`}});
  if(!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}
async function rpc(name, body={}){
  const r=await fetch(`${cfg.SUPABASE_URL}/rest/v1/rpc/${name}`,{method:'POST',headers:{apikey:cfg.SUPABASE_ANON_KEY,Authorization:`Bearer ${cfg.SUPABASE_ANON_KEY}`,'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!r.ok) throw new Error(`${r.status} ${await r.text()}`); return r.json();
}
async function loadHealth(){
  const h=await rpc('get_health'); const last=h.last_run; const ok=last&&['success','partial'].includes(last.status);
  $('#healthDot').style.background=ok?'var(--good)':'var(--bad)';
  $('#healthText').textContent=last?`Última coleta: ${new Date(last.started_at).toLocaleString('pt-BR')} · ${last.status}`:'Sem coleta ainda';
}
async function loadSummary(){
  const filter=state.league?`eq.${state.league}`:undefined;
  const rows=await rest('matches',{select:'id,league,played_at,home_player,away_player,home_score,away_score,total_goals',league:filter,order:'played_at.desc',limit:'2000'});
  const players=new Set();let goals=0,btts=0,o25=0,o35=0;
  rows.forEach(m=>{players.add(m.home_player.toLowerCase());players.add(m.away_player.toLowerCase());goals+=m.total_goals;btts+=(m.home_score>0&&m.away_score>0);o25+=m.total_goals>2;o35+=m.total_goals>3});
  $('#mMatches').textContent=fmt(rows.length);$('#mPlayers').textContent=fmt(players.size);$('#mGoals').textContent=rows.length?fmt(goals/rows.length):'0';$('#mBtts').textContent=rows.length?pct(100*btts/rows.length):'0%';$('#mO25').textContent=rows.length?pct(100*o25/rows.length):'0%';$('#mO35').textContent=rows.length?pct(100*o35/rows.length):'0%';renderRecent(rows.slice(0,60));
}
async function loadPlayers(){
  const params={select:'*',order:'win_pct.desc',limit:'500'};if(state.league)params.league=`eq.${state.league}`;
  const rows=await rest('v_player_stats',params);const tbody=$('#playersBody');tbody.innerHTML='';
  rows.slice(0,100).forEach(x=>{const tr=document.createElement('tr');tr.innerHTML=`<td><b>${x.player}</b></td><td>${x.matches}</td><td class="w">${pct(x.win_pct)}</td><td>${fmt(x.avg_goals_for)}</td><td>${fmt(x.avg_goals_against)}</td><td>${pct(x.over_2_5_pct)}</td><td>${pct(x.btts_pct)}</td>`;tbody.appendChild(tr)});
  const names=[...new Set(rows.map(x=>x.player))].sort((a,b)=>a.localeCompare(b));['playerA','playerB'].forEach(id=>{const s=$(`#${id}`);const old=s.value;s.innerHTML='<option value="">Selecione</option>'+names.map(n=>`<option>${n}</option>`).join('');s.value=old;});
}
function renderRecent(rows){const body=$('#recentBody');body.innerHTML='';rows.forEach(m=>{const tr=document.createElement('tr');tr.innerHTML=`<td><span class="pill">${m.league} min</span></td><td>${new Date(m.played_at).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}</td><td>${m.home_player}</td><td><b>${m.home_score} × ${m.away_score}</b></td><td>${m.away_player}</td>`;body.appendChild(tr)});}
async function loadH2H(){
  const a=$('#playerA').value,b=$('#playerB').value;if(!a||!b||a===b){$('#h2h').innerHTML='<div class="empty">Escolha dois jogadores diferentes.</div>';return}
  const h=await rpc('get_h2h',{p_player_a:a,p_player_b:b,p_league:state.league,p_limit:20});if(!h||!h.total){$('#h2h').innerHTML='<div class="empty">Nenhum confronto encontrado.</div>';return}
  $('#h2h').innerHTML=`<div class="metric-grid"><div class="metric"><small>Confrontos</small><strong>${h.total}</strong></div><div class="metric"><small>${a} venceu</small><strong class="w">${h.a_wins} · ${pct(h.a_win_pct)}</strong></div><div class="metric"><small>Empates</small><strong class="d">${h.draws} · ${pct(h.draw_pct)}</strong></div><div class="metric"><small>${b} venceu</small><strong class="l">${h.b_wins} · ${pct(h.b_win_pct)}</strong></div><div class="metric"><small>Média de gols</small><strong>${fmt(h.avg_total_goals)}</strong></div><div class="metric"><small>Over 2.5</small><strong>${pct(h.over_2_5_pct)}</strong></div><div class="metric"><small>Over 3.5</small><strong>${pct(h.over_3_5_pct)}</strong></div><div class="metric"><small>Ambas marcam</small><strong>${pct(h.btts_pct)}</strong></div></div><div class="scroll" style="margin-top:14px"><table><thead><tr><th>Data</th><th>Casa</th><th>Placar</th><th>Fora</th></tr></thead><tbody>${h.recent.map(m=>`<tr><td>${new Date(m.played_at).toLocaleString('pt-BR')}</td><td>${m.home_player}</td><td><b>${m.home_score} × ${m.away_score}</b></td><td>${m.away_player}</td></tr>`).join('')}</tbody></table></div>`;
}
async function refresh(){try{await Promise.all([loadHealth(),loadSummary(),loadPlayers()]);if($('#playerA').value&&$('#playerB').value)await loadH2H();$('#error').textContent='';}catch(e){console.error(e);$('#error').textContent=`Erro: ${e.message}`;}}
$('#league').addEventListener('change',async e=>{state.league=e.target.value||null;await refresh()});$('#h2hBtn').addEventListener('click',loadH2H);refresh();setInterval(loadHealth,60000);
