const $ = id => document.getElementById(id);
const fmt = value => value == null ? 'Unavailable' : Number(value).toLocaleString('en-US', {maximumFractionDigits: 0});
const percent = value => value == null ? 'Unavailable' : value > 0 && value < .001 ? '<0.1%' : `${(value * 100).toFixed(1)}%`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const reason = row => row.selected_language_count == null ? 'Language count unavailable (suppressed or absent).' : row.language_share == null ? ({incomplete_county_total:'County total is incomplete; share unavailable.',missing_county_total:'County total unavailable; share unavailable.',nonpositive_county_total:'County total is not positive; share unavailable.'}[row.language_share_unavailable_reason] || 'Share unavailable.') : 'Observed count and complete county denominator.';
const statusLabel = value => ({P:'Preliminary — may be revised', F:'Final'}[value] || 'Status unavailable');
const state = {month:'', language:'', county:'', sort:'count', search:''};
let metadata, geometry, comparison, detail, requestId = 0, controller;
const mapPaths = new Map();
const regions = () => [$('metrics'), $('statewide'), document.querySelector('.map-detail-grid'), document.querySelector('[aria-labelledby="comparison-heading"]'), document.querySelector('.demographic-section')];
function visibility(show) { regions().forEach(region => {region.hidden = !show;}); }
function showError(error) { $('error').textContent = `${error.message} Check the local server, then change a filter to retry or reload the page.`; $('error').hidden = false; $('notice').textContent = 'View unavailable. Reload or change a filter to retry.'; visibility(false); }
async function fetchJSON(url, signal) {
  const response = await fetch(url, {signal});
  const value = await response.json();
  if (!response.ok) throw Error(value.error || 'The dashboard request failed.');
  return value;
}
function query(values) {return new URLSearchParams(values).toString();}
function options(id, values, selected) {
  $(id).replaceChildren(...values.map(value => new Option(value.label ?? value, value.id ?? value)));
  $(id).value = selected;
}
function languageLabel() {return metadata.languages.find(item => item.id === state.language)?.label || state.language;}
function chooseCounty(county) {
  if (!metadata.counties.includes(county)) return;
  state.county = county; $('county').value = county; update();
}
async function update() {
  const token = ++requestId;
  controller?.abort(); controller = new AbortController();
  const filters = {month: state.month, language: state.language};
  const county = state.county;
  $('error').hidden = true; $('notice').textContent = `Updating ${state.month} · ${languageLabel()} · ${county}…`;
  $('county-detail').setAttribute('aria-busy', 'true'); document.querySelector('main').classList.add('updating'); $('download').disabled = true;
  try {
    const sameComparison = comparison?.month === filters.month && comparison?.language === filters.language;
    const [nextComparison, nextDetail] = await Promise.all([
      sameComparison ? comparison : fetchJSON(`/api/comparison?${query(filters)}`, controller.signal),
      fetchJSON(`/api/county?${query({...filters, county})}`, controller.signal),
    ]);
    if (token !== requestId) return;
    if ([nextComparison, nextDetail].some(value => value.source_sha256 !== metadata.source.sha256)) throw Error('The source snapshot changed. Reload to keep all views on the same version.');
    comparison = nextComparison; detail = nextDetail;
    render(); visibility(true); $('download').disabled = false;
    $('notice').textContent = `${state.month} · ${languageLabel()} · ${state.county} selected. All views use the same validated snapshot.`;
  } catch (error) { if (token === requestId && error.name !== 'AbortError') showError(error); }
  finally {if (token === requestId) {document.querySelector('main').classList.remove('updating'); $('county-detail').setAttribute('aria-busy','false');}}
}
function render() {
  const overview = comparison.overview;
  $('metrics').innerHTML = [
    ['Observed county subtotal', fmt(overview.observed_language_count), 'Published language counts only; coverage shown alongside.'],
    ['Count coverage', `${overview.language_count_available_counties} / 58`, 'Counties with an observed selected-language count.'],
    ['Share coverage', `${overview.language_share_available_counties} / 58`, 'Counties with an observed count and valid denominator.'],
  ].map(([label,value,note]) => `<article class="metric"><span>${label}</span><strong>${value}</strong><small>${note}</small></article>`).join('');
  $('statewide').textContent = `Complete statewide language count: ${fmt(overview.selected_language_count)} · Complete statewide language share: ${percent(overview.language_share)}. ${overview.selected_language_count_is_complete ? 'All 58 county language counts are observed.' : 'The observed subtotal is not a complete statewide count.'}`;
  renderMap(); renderTable(); renderDetail(); renderBars();
}
function buildMap() {
  const coordinates = [];
  function collect(value) {if (typeof value[0] === 'number') coordinates.push(value); else value.forEach(collect);}
  geometry.features.forEach(feature => collect(feature.geometry.coordinates));
  const cosine = Math.cos(37 * Math.PI / 180);
  const xs = coordinates.map(point => point[0] * cosine), ys = coordinates.map(point => -point[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const scale = Math.min(510 / (maxX-minX), 520 / (maxY-minY));
  const left = (550 - (maxX-minX)*scale)/2, top = (560 - (maxY-minY)*scale)/2;
  const ringPath = ring => ring.map((point,index) => `${index ? 'L' : 'M'}${(left+(point[0]*cosine-minX)*scale).toFixed(2)},${(top+(-point[1]-minY)*scale).toFixed(2)}`).join(' ') + 'Z';
  for (const feature of geometry.features) {
    const path = document.createElementNS('http://www.w3.org/2000/svg','path');
    const polygons = feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates] : feature.geometry.coordinates;
    path.setAttribute('d', polygons.flatMap(polygon => polygon.map(ringPath)).join(' '));
    path.setAttribute('fill-rule','evenodd'); path.setAttribute('role','button'); path.setAttribute('tabindex','0');
    path.setAttribute('class','county-shape'); path.dataset.county = feature.properties.county;
    path.appendChild(document.createElementNS('http://www.w3.org/2000/svg','title'));
    $('county-map').appendChild(path); mapPaths.set(feature.properties.county,path);
  }
}
function renderMap() {
  const max = Math.max(0, ...comparison.counties.map(row => row.selected_language_count ?? 0));
  for (const row of comparison.counties) {
    const path = mapPaths.get(row.county), count = row.selected_language_count;
    const selected = row.county === state.county;
    const intensity = Math.sqrt(max ? (count ?? 0)/max : 0);
    path.setAttribute('fill', count == null ? '#d8dedc' : `rgb(${Math.round(234-216*intensity)},${Math.round(242-173*intensity)},${Math.round(251-140*intensity)})`);
    path.classList.toggle('selected',selected); path.setAttribute('aria-pressed',String(selected));
    const description = `${row.county}. ${languageLabel()} count: ${fmt(count)}. County total: ${fmt(row.county_total_eligibles)}. Share: ${percent(row.language_share)}. ${reason(row)}`;
    path.setAttribute('aria-label', `Select ${description}`); path.querySelector('title').textContent = description;
    path.dataset.description = description;
  }
  $('legend-max').textContent = fmt(max);
  $('map-empty').textContent = comparison.overview.language_count_available_counties === 0 ? 'No observed counts can be ranked for this selection. All 58 counties remain selectable.' : `Language counts · ${state.month} · ${languageLabel()}. Square-root color scale keeps smaller populations visible. Observed zero is light blue; unavailable is gray.`;
}
function sortedRows() {
  const key = state.sort === 'share' ? 'language_share' : 'selected_language_count';
  return [...comparison.counties].sort((a,b) => state.sort === 'county' ? a.county.localeCompare(b.county) : (a[key] == null)-(b[key] == null) || (b[key] ?? 0)-(a[key] ?? 0) || a.county.localeCompare(b.county));
}
function renderTable() {
  const focusedCounty = document.activeElement?.closest('#rows button[data-county]')?.dataset.county;
  const rows = sortedRows().filter(row => row.county.toLowerCase().includes(state.search.toLowerCase()));
  $('table-status').textContent = `${rows.length} of 58 counties shown · Selected: ${state.county}`;
  $('rows').innerHTML = rows.length ? rows.map(row => `<tr class="${row.county===state.county?'selected-row':''}" ${row.county===state.county?'aria-current="true"':''}><td>${row.rank ?? '—'}</td><th scope="row"><button class="county-link" data-county="${esc(row.county)}" aria-pressed="${row.county===state.county}">${esc(row.county)}</button></th><td>${fmt(row.selected_language_count)}</td><td>${fmt(row.county_total_eligibles)}</td><td>${esc(percent(row.language_share))}</td><td class="availability-cell">${esc(reason(row))}</td></tr>`).join('') : '<tr><td colspan="6">No matching counties. Clear the search to see all counties.</td></tr>';
  if (focusedCounty) Array.from($('rows').querySelectorAll('button')).find(button => button.dataset.county === focusedCounty)?.focus({preventScroll:true});
}
function renderBars() {
  const rows = comparison.counties.filter(row => row.selected_language_count != null).slice(0,12), max = rows[0]?.selected_language_count || 1;
  $('bars').innerHTML = rows.length ? rows.map(row => `<button class="bar-row ${row.county===state.county?'selected-bar':''}" data-county="${esc(row.county)}" aria-pressed="${row.county===state.county}"><span>${esc(row.county)}</span><span class="bar-track" aria-hidden="true"><span class="bar-fill" style="width:${row.selected_language_count/max*100}%"></span></span><b>${fmt(row.selected_language_count)}</b></button>`).join('') : '<p>No observed language counts for this selection.</p>';
}
function renderDetail() {
  const row = detail.county;
  $('detail-heading').textContent = `${state.county} County`;
  $('detail-selection').textContent = `${state.month} · ${languageLabel()}`;
  $('county-metrics').innerHTML = [['Language count',fmt(row.selected_language_count)],['County total',fmt(row.county_total_eligibles)],['Language share',percent(row.language_share)]].map(([label,value])=>`<div><span>${label}</span><strong>${esc(value)}</strong></div>`).join('');
  $('availability').textContent = reason(row);
  $('publication').textContent = `${statusLabel(row.status)} · Source date: ${row.date_of_data || 'Unavailable'}`;
  $('point').textContent = `Selected month ${state.month}: ${fmt(row.selected_language_count)} ${languageLabel()} eligibles.`;
  $('demographic-selection').textContent = `${state.county} County · ${state.month}`;
  renderTrend(); renderDemographics();
}
function renderTrend() {
  const series = detail.trend, observed = series.filter(row => row.selected_language_count != null), max = Math.max(1,...observed.map(row => row.selected_language_count));
  if (!observed.length) {$('trend').innerHTML = '<p class="empty">No observed language counts for this county across the snapshot.</p>'; return;}
  const x = index => 54+index/(series.length-1||1)*440, y = value => 150-value/max*115;
  let path = '', connected = false;
  series.forEach((row,index) => {if (row.selected_language_count == null) {connected=false;return;} path+=`${connected?'L':'M'}${x(index)},${y(row.selected_language_count)} `;connected=true;});
  const selectedIndex = series.findIndex(row => row.month_of_eligibility===state.month), selected = series[selectedIndex];
  const marker = selected ? `<path d="M${x(selectedIndex)} 28V150" stroke="#bd793e" stroke-dasharray="3 4"/>${selected.selected_language_count == null?'':`<circle cx="${x(selectedIndex)}" cy="${y(selected.selected_language_count)}" r="4.5" fill="#b86626"/>`}` : '';
  const points = series.map((row,index) => row.selected_language_count==null ? '' : `<circle cx="${x(index)}" cy="${y(row.selected_language_count)}" r="3" fill="transparent" stroke="transparent"><title>${row.month_of_eligibility}: ${fmt(row.selected_language_count)}</title></circle>`).join('');
  $('trend').innerHTML = `<svg viewBox="0 0 530 190" role="img" aria-label="${esc(state.county)} ${esc(languageLabel())} monthly language counts, ${series[0].month_of_eligibility} to ${series.at(-1).month_of_eligibility}. Gaps mean unavailable. Selected month ${state.month}."><text x="2" y="22">${fmt(max)}</text><text x="35" y="154">0</text><path d="M54 30V150H500" fill="none" stroke="#dce5dc"/>${marker}<path d="${path}" fill="none" stroke="#397d80" stroke-width="2.5"/>${points}<text x="54" y="178">${series[0].month_of_eligibility}</text><text x="448" y="178">${series.at(-1).month_of_eligibility}</text></svg>`;
}
function renderDemographics() {
  const ages = {age_00_18:'0–18',age_19_44:'19–44',age_45_64:'45–64',age_65_plus:'65+'};
  const maxAge = Math.max(1,...detail.age_sex.map(row=>row.eligible_count??0));
  $('age-sex').innerHTML = Object.entries(ages).map(([age,label]) => `<div class="age-group"><h4>${label} years</h4>${['female','male'].map(sex => {
    const row = detail.age_sex.find(item=>item.age_group===age && item.sex===sex);
    return `<div class="demo-row"><span>${sex==='female'?'Female':'Male'}</span><span class="bar-track" aria-hidden="true">${row?.eligible_count==null?'':`<span class="bar-fill ${sex}" style="width:${row.eligible_count/maxAge*100}%"></span>`}</span><b>${fmt(row?.eligible_count)}</b></div>`;
  }).join('')}</div>`).join('');
  const races = {ai_an:'American Indian/Alaska Native',asian:'Asian',black:'Black',hispanic:'Hispanic',not_reported:'Not reported',white:'White'};
  const maxRace = Math.max(1,...detail.race_ethnicity.map(row=>row.eligible_count??0));
  $('race').innerHTML = detail.race_ethnicity.map(row=>`<div class="race-group"><div class="race-label"><span>${races[row.race_ethnicity] || esc(row.race_ethnicity)}</span><b>${fmt(row.eligible_count)}</b></div><div class="bar-track" aria-hidden="true">${row.eligible_count==null?'':`<span class="bar-fill" style="width:${row.eligible_count/maxRace*100}%"></span>`}</div>${row.eligible_count==null?'<small>One or more required age-group counts unavailable.</small>':''}</div>`).join('');
}
function countyEvent(event) {const target=event.target.closest('[data-county]'); if (target) chooseCounty(target.dataset.county);}
$('county-map').addEventListener('click',countyEvent);
$('county-map').addEventListener('keydown',event => {if (event.key==='Enter'||event.key===' ') {event.preventDefault();countyEvent(event);}});
for (const id of ['rows','bars']) $(id).addEventListener('click',countyEvent);
function tooltip(event) {
  const path = event.target.closest('.county-shape'); if (!path) return;
  $('map-tooltip').textContent = path.dataset.description; $('map-tooltip').hidden = false;
}
$('county-map').addEventListener('pointerover',tooltip); $('county-map').addEventListener('focusin',tooltip);
for (const event of ['pointerleave','focusout']) $('county-map').addEventListener(event,()=>{$('map-tooltip').hidden=true;});
for (const id of ['month','language','county']) $(id).addEventListener('change',() => {state[id]=$(id).value; $('map-tooltip').hidden=true; update();});
$('sort').addEventListener('change',()=>{state.sort=$('sort').value;if(comparison)renderTable();});
$('search').addEventListener('input',()=>{state.search=$('search').value;if(comparison)renderTable();});
$('reset').addEventListener('click',()=>{Object.assign(state, metadata.defaults, {sort:'count',search:''});for(const id of ['month','language','county','sort','search']) $(id).value=state[id];update();});
$('download').addEventListener('click',async()=>{
  const filters={month:state.month,language:state.language}; $('download').disabled=true;
  try {
    const response=await fetch(`/api/export.csv?${query(filters)}`);
    if(!response.ok) throw Error('Could not export county comparison.');
    const url=URL.createObjectURL(await response.blob()), anchor=document.createElement('a');
    anchor.href=url; anchor.download=`medi-cal-${filters.month}-${filters.language}.csv`;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  } catch(error) {$('error').textContent=error.message;$('error').hidden=false;}
  finally {$('download').disabled=false;}
});
async function start() {
  visibility(false);
  try {
    [metadata, geometry]=await Promise.all([fetchJSON('/api/metadata'),fetchJSON('/api/geometry')]);
    const names=geometry.features.map(feature=>feature.properties.county);
    if(names.length!==58 || new Set(names).size!==58 || metadata.counties.some(county=>!names.includes(county))) throw Error('The county map does not match the validated data.');
    Object.assign(state,metadata.defaults);
    options('month',[...metadata.months].reverse(),state.month);options('language',metadata.languages,state.language);options('county',metadata.counties,state.county);
    for(const id of ['month','language','county','reset']) $(id).disabled=false;
    buildMap();
    $('source').textContent=`Source: DHCS canonical county-month snapshot · ${metadata.source.first_month} through ${metadata.source.last_month} · ${metadata.source.rows.toLocaleString()} county-month rows. Snapshot SHA-256: ${metadata.source.sha256}.`;
    await update();
  } catch(error) {$('notice').textContent='Dashboard unavailable.';showError(error);}
}
start();
