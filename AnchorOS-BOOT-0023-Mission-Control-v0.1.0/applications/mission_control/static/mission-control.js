let lastSequence=0;
const $=id=>document.getElementById(id);
const safe=value=>String(value??'—');
function list(id,items){$(id).innerHTML=(items||[]).map(x=>`<li>${safe(typeof x==='string'?x:x.name)}</li>`).join('')||'<li>None</li>'}
function render(data){
 const m=data.manifest||{}, p=data.pipeline||{}, h=data.health||{};
 $('identity').textContent=`${safe(m.product)} ${safe(m.version)} · ${safe(m.codename)} · ${safe(m.stage)}`;
 $('platform-status').textContent=safe(data.platform_status||'UNKNOWN');
 $('service-count').textContent=(data.services||[]).length;
 $('framework-count').textContent=(data.frameworks||[]).length;
 $('application-count').textContent=(data.applications||[]).length;
 $('audit-count').textContent=(data.audit||[]).length;
 $('boot-id').textContent=`BOOT ${safe(m.boot)}`;
 list('services',data.services);list('frameworks',data.frameworks);list('applications',data.applications);
 $('pipeline-chip').textContent=p.verified?'VERIFIED':'PENDING';
 $('pipeline-score').textContent=`${safe(p.passed)} / ${safe(p.total)}`;
 const modules=h.modules||[];
 $('health-chip').textContent=safe(h.status||'UNKNOWN');
 $('health-list').innerHTML=modules.slice(0,10).map(x=>`<div class="health-row"><span>${safe(x.name)}</span><b>${safe(x.status).toUpperCase()}</b></div>`).join('');
 const events=(data.recent_events||data.audit||[]).slice().reverse();
 $('events').innerHTML=events.map(e=>`<div class="event"><time>${safe(e.timestamp).replace('T',' ').slice(0,19)}</time><b>${safe(e.event_type)}</b><span>${safe(e.source)} — ${safe(e.message)}</span></div>`).join('')||'<p>No events recorded.</p>';
 events.forEach(e=>{lastSequence=Math.max(lastSequence,Number(e.sequence||0))});
}
async function refresh(){try{const r=await fetch('/api/v1/status',{cache:'no-store'});render(await r.json());$('connection').textContent='LIVE'}catch(e){$('connection').textContent='RECONNECTING'}}
refresh();setInterval(refresh,2000);setInterval(()=>$('clock').textContent=new Date().toLocaleString(),1000);
