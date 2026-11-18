(()=>{'use strict';
const $=id=>document.getElementById(id);
const state={data:null,manifest:null,category:'All',niche:'all',search:'',sort:'rank',savedOnly:false,active:null,saved:new Set()};
try{state.saved=new Set(JSON.parse(localStorage.getItem('format-radar-saved')||'[]'))}catch(_){state.saved=new Set()}
const tone={Visual:['#54362e','#1a1f25'],Storytelling:['#3c332e','#222626'],Education:['#213d38','#1a2226'],Engagement:['#432d42','#242032'],Entertainment:['#403a51','#252334'],Product:['#394045','#21252b'],Lifestyle:['#514633','#292923']};
const escapeHTML=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const compact=n=>{n=Number(n)||0;return n>=1e9?(n/1e9).toFixed(1).replace(/\.0$/,'')+'B':n>=1e6?(n/1e6).toFixed(1).replace(/\.0$/,'')+'M':n>=1e3?(n/1e3).toFixed(1).replace(/\.0$/,'')+'K':String(Math.round(n))};
const el= (id,v)=>{if($(id))$(id).textContent=v};
const demo=()=>state.data?.mode!=='live';
let timer;
function toast(message){let t=$('toast');t.textContent=message;t.classList.add('visible');clearTimeout(timer);timer=setTimeout(()=>t.classList.remove('visible'),2600)}
function persistSaved(){try{localStorage.setItem('format-radar-saved',JSON.stringify([...state.saved]))}catch(_){}}
function toggleSave(id){if(state.saved.has(id))state.saved.delete(id);else state.saved.add(id);persistSaved();renderCards();if(state.active?.id===id)renderDrawer(state.active);toast(state.saved.has(id)?'Saved to your library':'Removed from saved')}
async function getJSON(path){const res=await fetch(path,{cache:'no-store'});if(!res.ok)throw Error('HTTP '+res.status);return res.json()}
async function boot(){try{
  let data,manifest;
  if(window.FORMAT_RADAR_BOOTSTRAP){data=window.FORMAT_RADAR_BOOTSTRAP;manifest={latest:data.month,snapshots:[]}}
  else{[data,manifest]=await Promise.all([getJSON('data/latest.json'),getJSON('data/index.json')])}
  state.manifest=manifest;state.data=data;
  updateIssueSelect();updateUI();
}catch(err){console.error('Format Radar failed to load',err);$('cards').innerHTML='<div class="empty-state" style="display:block;grid-column:1/-1"><h3>Unable to load the issue</h3><p>Run this site through a local web server (for example <code>python -m http.server</code>) or open the standalone preview HTML.</p></div>';el('resultsCount','Issue unavailable');el('topStatus','Data unavailable')}}
function issueName(item){return item.period_label||item.month||'Issue'}
function updateIssueSelect(){const s=$('issueSelect');let opts=[{month:state.data.month,label:demo()?'Starter library':issueName(state.data)}];
  for(const d of (state.manifest?.snapshots||[])){if(!opts.some(o=>o.month===d.month))opts.push({month:d.month,label:d.period_label||d.month})}
  s.innerHTML=opts.map(o=>`<option value="${escapeHTML(o.month)}">${escapeHTML(o.label)}</option>`).join('');s.value=state.data.month}
async function onIssueChange(month){try{let dataset;if(month===state.manifest?.latest||month===state.data.month && month==='demo')dataset=await (window.FORMAT_RADAR_BOOTSTRAP?Promise.resolve(window.FORMAT_RADAR_BOOTSTRAP):getJSON('data/latest.json'));else dataset=await getJSON('data/archive/'+encodeURIComponent(month)+'.json');state.data=dataset;state.category='All';state.niche='all';state.search='';state.sort='rank';state.savedOnly=false;$('searchInput').value='';$('sortSelect').value='rank';$('savedOnly').checked=false;updateUI()}catch(e){console.error(e);toast('That issue could not be loaded');$('issueSelect').value=state.data.month}}
function updateUI(){const d=state.data;const isDemo=demo();$('demoBanner').hidden=!isDemo;$('topStatus').innerHTML='<span class="status-dot"></span> '+(isDemo?'STARTER PREVIEW':'MONTHLY FORMAT REPORT');el('statFormats',d.results.length);el('statFormatsFoot',isDemo?'Unranked example playbooks':'Evidence-backed formats ranked');el('statVideos',isDemo?'—':compact(d.sample_size));el('statNiches',isDemo?'—':d.niches_covered);el('statIssue',isDemo?'PREVIEW':(d.period_label||d.month));el('statIssueFoot',isDemo?'Live ranking not connected':'Published monthly');el('sourceCaption',isDemo?'A working library, ready for monthly video data.':`Based on ${compact(d.sample_size)} records from ${d.source_name||'the authorized feed'} during ${d.period_label}.`);el('librarySubhead',isDemo?'50 adaptable templates. Rankings activate after the first data refresh.':`Up to 50 formats, ranked from ${d.period_label} video evidence.`);el('footerUpdated',isDemo?'Starter playbooks · not live rankings':`Updated ${new Date(d.generated_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'})}`);renderSpotlight();renderFilters();renderCards()}
function renderSpotlight(){const d=state.data;const item=d.results[0];if(!item)return;el('spotlightOverline',demo()?'FEATURED PLAYBOOK':'HIGHEST RANKED FORMAT');el('spotlightHeading',item.name+'.');el('spotlightDescription',item.hook+' '+item.why);el('spotlightNumber',demo()?'01':String(item.rank||1).padStart(2,'0'));el('spotlightCategory',item.category.toUpperCase()+' / '+(demo()?'STARTER':'MONTHLY RANKING'));$('spotlightAction').onclick=()=>openDrawer(item.id)}
function renderFilters(){const cats=['All',...new Set(state.data.results.map(x=>x.category))];$('categoryPills').innerHTML=cats.map(c=>`<button class="pill${state.category===c?' active':''}" type="button" data-category="${escapeHTML(c)}" aria-pressed="${state.category===c}">${escapeHTML(c)}</button>`).join('');const niches=[...new Set(state.data.results.flatMap(x=>x.niches||[x.niche]).filter(x=>x&&x!=='All niches'))].sort();$('nicheSelect').innerHTML='<option value="all">All niches</option>'+niches.map(n=>`<option value="${escapeHTML(n)}">${escapeHTML(n)}</option>`).join('');$('nicheSelect').value=state.niche;nicheCount=niches.length}
let nicheCount=0;
function filteredResults(){let items=state.data.results.filter(item=>{
  const needles=[item.name,item.category,item.hook,item.why,item.remix,item.niche,...(item.niches||[])].join(' ').toLowerCase();
  return (state.category==='All'||item.category===state.category)&&(state.niche==='all'||(item.niches||[item.niche]).includes(state.niche))&&(!state.savedOnly||state.saved.has(item.id))&&needles.includes(state.search.toLowerCase())
});
  if(state.sort==='creators')items.sort((a,b)=>(b.stats?.creators||0)-(a.stats?.creators||0)||a.name.localeCompare(b.name));
  else if(state.sort==='views')items.sort((a,b)=>(b.stats?.views||0)-(a.stats?.views||0)||a.name.localeCompare(b.name));
  else if(state.sort==='az')items.sort((a,b)=>a.name.localeCompare(b.name));
  else items.sort((a,b)=>(a.rank??1000)-(b.rank??1000)||state.data.results.indexOf(a)-state.data.results.indexOf(b));
  return items}
function renderCards(){const items=filteredResults();const isDemo=demo();el('resultsCount',`${items.length} ${items.length===1?'format':'formats'} ${isDemo?'in the playbook library':'in this issue'}`);$('emptyState').hidden=items.length>0;$('cards').hidden=!items.length;
 $('cards').innerHTML=items.map((x,i)=>{
  const colors=tone[x.category]||tone.Education,stats=x.stats||{};
  const saved=state.saved.has(x.id);
  const fmtIndex=isDemo?'PLAYBOOK '+String(state.data.results.indexOf(x)+1).padStart(2,'0'):'#'+String(x.rank||i+1).padStart(2,'0');
  const stat1=isDemo?'—':compact(stats.avg_views);
  const stat2=isDemo?'—':String(stats.creators||0);
  return `<article class="format-card" style="--tone-a:${colors[0]};--tone-b:${colors[1]}">
    <div class="card-visual"><div class="card-ellipse"></div><div class="card-watermark">${escapeHTML(String(x.rank||state.data.results.indexOf(x)+1).padStart(2,'0'))}</div><span class="card-index">${escapeHTML(fmtIndex)}</span><button type="button" class="card-save ${saved?'saved':''}" data-save="${escapeHTML(x.id)}" aria-label="${saved?'Unsave':'Save'} ${escapeHTML(x.name)}" aria-pressed="${saved}">${saved?'♥':'♡'}</button></div>
    <div class="card-content"><div class="card-eyebrow">${escapeHTML(x.category)}</div><h3>${escapeHTML(x.name)}</h3><p class="card-summary">${escapeHTML(x.hook)}</p><div class="card-stats"><div><div class="card-stat-label">AVG. VIEWS</div><div class="card-stat-value">${stat1}</div></div><div><div class="card-stat-label">CREATORS</div><div class="card-stat-value">${stat2}</div></div></div></div>
    <div class="card-footer"><span>${isDemo?'PLAYBOOK · UNRANKED':'SIGNAL SCORE  ·  '+Math.round(x.score||0)+'/100'}</span><button class="card-action" type="button" data-open="${escapeHTML(x.id)}">View breakdown ↗</button></div>
  </article>`}).join('')}
function findItem(id){return state.data?.results.find(x=>x.id===id)}
function openDrawer(id){const x=findItem(id);if(!x)return;state.active=x;renderDrawer(x);const d=$('detailDialog');if(!d.open){d.showModal()} }
function renderDrawer(x){const isDemo=demo(),stats=x.stats||{},saved=state.saved.has(x.id);
 const videos=(x.sample_videos||[]).filter(v=>{const u=v.url||(/^[a-zA-Z0-9_-]{11}$/.test(v.id)?'https://www.youtube.com/watch?v='+v.id:'');return /^https:\/\//.test(u)}).slice(0,5);
 const statsMarkup=isDemo?'<div class="evidence-note">This is a starter template. Source videos and measured rankings appear when the first monthly refresh is completed.</div>':`<div class="drawer-metric-row"><div class="drawer-metric"><b>${compact(stats.views)}</b><small>Sample views</small></div><div class="drawer-metric"><b>${stats.creators||0}</b><small>Creators</small></div><div class="drawer-metric"><b>${Math.round(x.score||0)}<span style="color:#999;font-size:12px">/100</span></b><small>Signal score</small></div></div>`;
 const clips=videos.length?videos.map(v=>{
  const fallback='https://www.youtube.com/watch?v='+encodeURIComponent(v.id);
  const link=escapeHTML(v.url&&/^https:\/\//.test(v.url)?v.url:fallback);
  const isYouTube=v.platform==='YouTube'&&/^[a-zA-Z0-9_-]{11}$/.test(v.id);
  const thumb=isYouTube?`<img src="https://i.ytimg.com/vi/${encodeURIComponent(v.id)}/mqdefault.jpg" alt="Thumbnail for ${escapeHTML(v.title)}" loading="lazy">`:`<div class="video-placeholder">▶</div>`;
  return `<a class="sample-video" href="${link}" target="_blank" rel="noopener noreferrer">${thumb}<div><strong>${escapeHTML(v.title)}</strong><small>${escapeHTML(v.platform||'Video')} · ${escapeHTML(v.channel)} · ${compact(v.views)} views ↗</small></div></a>`
 }).join(''):'<div class="evidence-note">No linked example videos are available for this entry.</div>';
 $('drawerBody').innerHTML=`<div class="drawer-kicker">${isDemo?'STARTER PLAYBOOK':'RANK #'+String(x.rank||'—').padStart(2,'0')}  /  ${escapeHTML(x.category.toUpperCase())}</div><h2 class="drawer-title" id="detailTitle">${escapeHTML(x.name)}<span class="punct">.</span></h2><p class="drawer-lead">${escapeHTML(x.why)}</p><div class="drawer-tools"><button type="button" id="copyPlaybook">Copy playbook ↗</button><button type="button" id="drawerSave">${saved?'♥ Saved':'♡ Save format'}</button></div>${statsMarkup}<div class="drawer-section"><h3>01 / The hook</h3><div class="hook-box">“${escapeHTML(x.hook)}”</div></div><div class="drawer-section"><h3>02 / The structure</h3><ol class="steps-list">${(x.steps||[]).map(s=>`<li>${escapeHTML(s)}</li>`).join('')}</ol></div><div class="drawer-section"><h3>03 / Make it yours</h3><p>${escapeHTML(x.remix)}</p></div><div class="drawer-section"><h3>04 / Source examples ${isDemo?'(not available yet)':''}</h3><div class="sample-videos">${clips}</div></div><div class="drawer-section"><div class="evidence-note">${isDemo?'No ranking score is assigned in preview mode.':'Format labels come from the connected feed or permitted metadata tagging; always review the linked footage. View counts are snapshots, not views gained only within the month.'}</div></div>`;
 $('drawerSave').onclick=()=>toggleSave(x.id);$('copyPlaybook').onclick=()=>copyText(`${x.name}\nHook: ${x.hook}\nStructure:\n${(x.steps||[]).map((s,i)=>`${i+1}. ${s}`).join('\n')}\nWhy it works: ${x.why}\nAdaptation: ${x.remix}`)}
async function copyText(s){try{await navigator.clipboard.writeText(s);toast('Playbook copied')}catch(_){const tmp=document.createElement('textarea');tmp.value=s;document.body.appendChild(tmp);tmp.select();document.execCommand('copy');tmp.remove();toast('Playbook copied')}}
function exportSaved(){const selection=state.data.results.filter(x=>state.saved.has(x.id)).map(x=>({name:x.name,category:x.category,hook:x.hook,steps:x.steps,why:x.why,remix:x.remix}));if(!selection.length){toast('Save a format first');return}const blob=new Blob([JSON.stringify(selection,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='format-radar-saved.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(`Exported ${selection.length} formats`)}
function clearFilters(){state.search='';state.category='All';state.niche='all';state.savedOnly=false;state.sort='rank';$('searchInput').value='';$('nicheSelect').value='all';$('savedOnly').checked=false;$('sortSelect').value='rank';renderFilters();renderCards()}
$('categoryPills').addEventListener('click',e=>{let b=e.target.closest('[data-category]');if(!b)return;state.category=b.dataset.category;renderFilters();renderCards()});
$('cards').addEventListener('click',e=>{let b=e.target.closest('[data-save]');if(b){toggleSave(b.dataset.save);return}b=e.target.closest('[data-open]');if(b)openDrawer(b.dataset.open)});
$('searchInput').addEventListener('input',e=>{state.search=e.target.value;renderCards()});$('nicheSelect').addEventListener('change',e=>{state.niche=e.target.value;renderCards()});$('sortSelect').addEventListener('change',e=>{state.sort=e.target.value;renderCards()});$('savedOnly').addEventListener('change',e=>{state.savedOnly=e.target.checked;renderCards()});$('issueSelect').addEventListener('change',e=>onIssueChange(e.target.value));$('exportSaved').addEventListener('click',exportSaved);$('clearFilters').addEventListener('click',clearFilters);$('closeDialog').addEventListener('click',()=>$('detailDialog').close());$('detailDialog').addEventListener('click',e=>{if(e.target===$('detailDialog'))$('detailDialog').close()});document.addEventListener('keydown',e=>{if(e.key==='/'&&document.activeElement.tagName!=='INPUT'&&!$('detailDialog').open){e.preventDefault();$('searchInput').focus()}});
boot();
})();
