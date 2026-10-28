const $ = id => document.getElementById(id);
const fmt = n => n == null ? 'Unavailable' : n.toLocaleString('en-US');
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data, current = [];
const lookup = new Map();
const key = (m,l,c) => JSON.stringify([m,l,c]);
function options(id, values, selected) {
  $(id).replaceChildren(...values.map(value => new Option(value,value)));
  $(id).value = selected;
}
function availability(r) { return r.absent ? 'No published row' : r.count == null ? (r.annotation || 'Count unavailable') : 'Published'; }
function render() {
  const month = $('month').value, language = $('language').value;
  current = data.counties.map(county => lookup.get(key(month,language,county)) || {county,month,language,count:null,status:'',code:'',annotation:'',absent:true});
  current.sort((a,b) => (a.count == null)-(b.count == null) || (b.count ?? 0)-(a.count ?? 0) || a.county.localeCompare(b.county));
  let previous, rank;
  current.forEach((r,i) => {if (r.count != null) {if (r.count !== previous) rank=i+1; previous=r.count; r.rank=rank;} else r.rank=null;});
  const published = current.filter(r=>r.count!=null), subtotal=published.reduce((s,r)=>s+r.count,0);
  const suppressed = current.filter(r=>r.count==null&&!r.absent).length;
  $('metrics').innerHTML = [
    ['Observed county subtotal',published.length ? fmt(subtotal) : 'Unavailable','Published counts only; not a complete statewide total.'],
    ['Count coverage',`${published.length} / ${data.counties.length}`,'Counties with a published count in this selection.'],
    ['Exact county language share','Unavailable','A verified county-total denominator is needed.']
  ].map(([label,value,note])=>`<article class="metric">${label}<strong>${value}</strong><span>${note}</span></article>`).join('');
  $('notice').textContent=`${month} · ${language} · ${suppressed} unavailable-count records · ${current.filter(r=>r.absent).length} absent county records. Status code(s): ${[...new Set(current.map(r=>r.status).filter(Boolean))].join(', ') || 'none'}.`;
  const max=published[0]?.count || 1;
  $('bars').innerHTML=published.length ? published.slice(0,12).map(r=>`<div class="bar-row"><span>${esc(r.county)}</span><div class="bar-track"><div class="bar-fill" style="width:${r.count/max*100}%"></div></div><b>${fmt(r.count)}</b></div>`).join('') : '<p>No published counts for this selection.</p>';
  renderTable(); renderTrend();
}
function renderTable() {
  const query=$('search').value.toLowerCase();
  const rows=current.filter(r=>r.county.toLowerCase().includes(query));
  $('rows').innerHTML=rows.length ? rows.map(r=>`<tr><td>${r.rank??'—'}</td><td>${esc(r.county)}</td><td class="${r.count==null?'muted':''}">${fmt(r.count)}</td><td>${esc(availability(r))}</td><td>${esc(r.status||'—')}</td></tr>`).join('') : '<tr><td colspan="5">No matching counties.</td></tr>';
}
function renderTrend() {
  const county=$('county').value, language=$('language').value;
  const series=data.months.map(month=>lookup.get(key(month,language,county)));
  const values=series.filter(r=>r?.count!=null);
  const max=Math.max(1,...values.map(r=>r.count)), x=i=>55+i/(series.length-1||1)*450, y=n=>175-n/max*140;
  let path='', connected=false;
  series.forEach((r,i)=>{if(r?.count==null){connected=false;return;} path+=`${connected?'L':'M'}${x(i)},${y(r.count)} `;connected=true;});
  const points=series.map((r,i)=>r?.count!=null ? `<circle cx="${x(i)}" cy="${y(r.count)}" r="2" fill="#438273"><title>${esc(r.month)}: ${fmt(r.count)}</title></circle>` : '').join('');
  $('trend').innerHTML=values.length ? `<svg viewBox="0 0 530 215" role="img" aria-label="${esc(county)} monthly ${esc(language)} counts, gaps for unavailable data"><text x="0" y="30" font-size="11" fill="#61786d">${fmt(max)}</text><text x="30" y="179" font-size="11" fill="#61786d">0</text><path d="M55 35V175H510" fill="none" stroke="#dce5dc"/><path d="${path}" fill="none" stroke="#438273" stroke-width="2"/>${points}<text x="55" y="202" font-size="11">${data.months[0]}</text><text x="455" y="202" font-size="11">${data.months.at(-1)}</text></svg>` : '<p>No published counts for this county and language.</p>';
  const selected=lookup.get(key($('month').value,language,county));
  $('point').textContent=`${$('month').value} · ${county}: ${fmt(selected?.count)}${selected?.count==null ? ' · '+(selected ? availability(selected) : 'No published row') : ''}`;
}
$('search').addEventListener('input',renderTable);
['month','language'].forEach(id=>$(id).addEventListener('change',render));
$('county').addEventListener('change',renderTrend);
$('download').addEventListener('click',()=>{
  const fields=['month','language','county','rank','count','availability','code','status','data_date'];
  const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';
  const csv=[fields,...current.map(r=>fields.map(f=>f==='availability'?availability(r):r[f]))].map(row=>row.map(quote).join(',')).join('\r\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a'); a.href=url;a.download=`medi-cal-${$('month').value}-${$('language').value}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
fetch('/api/data').then(r=>{if(!r.ok)throw Error('Data request failed');return r.json();}).then(result=>{
  data=result; data.records.forEach(r=>lookup.set(key(r.month,r.language,r.county),r));
  options('month',[...data.months].reverse(),data.months.at(-1));
  options('language',data.languages,data.languages.includes('Spanish')?'Spanish':data.languages[0]);
  options('county',data.counties,'Los Angeles');
  $('download').disabled=false;render();
}).catch(error=>{$('notice').textContent=`Unable to load dashboard data: ${error.message}. Restart the Python server and reload.`;});
