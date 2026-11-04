"""Client behavior, including offline language selection and persistence."""
SCRIPT = r"""
(()=>{'use strict';
const $=id=>document.getElementById(id),keys=['cpu','gpu','ram','disk','network'];
const storageKey='pasadhi-language';let state=null,rotated=false,failed=false;
let preference='auto';try{preference=localStorage.getItem(storageKey)||'auto';}catch{}
if(preference!=='auto'&&!Object.hasOwn(I18N.languages,preference))preference='auto';
function normalize(value){return String(value||'').toLowerCase().replace('_','-').split('-')[0];}
function resolve(){if(Object.hasOwn(I18N.languages,preference))return preference;for(const value of navigator.languages||[navigator.language]){const code=normalize(value);if(Object.hasOwn(I18N.languages,code))return code;}return 'en';}
let language=resolve();
const t=key=>I18N.catalog[language][key]??I18N.catalog.en[key]??key;
const number=(value,digits=0)=>new Intl.NumberFormat(language,{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(value);
const select=$('language');
for(const [code,name] of [['auto','Automatic'],...Object.entries(I18N.languages)]){const option=document.createElement('option');option.value=code;option.textContent=name;select.append(option);}
function paint(s){state=s;const sh=s.share,e=s.earnings,b=e.breakdown,l=s.limits,h=s.hardware;
 $('role').textContent=`${t('role')}: ${t(s.role)} · ${t('score')} ${number(s.score)}`;
 keys.forEach(k=>{$(k).value=sh[k+'_pct'];$(k+'_o').textContent=number(sh[k+'_pct'])+'%';});
 $('autostart').checked=!!s.autostart;
 $('monthly').textContent=number(e.monthly_thb);$('daily').textContent=number(e.daily_thb,1);$('hourly').textContent=number(e.hourly_thb,2);
 for(const k of ['cpu','gpu','ram','disk'])$('b_'+k).textContent=number(b[k],['ram','disk'].includes(k)?3:2)+' '+t('hour');
 $('limits').textContent=`${number(l.cpu_cores,2)} ${t('cores')} · ${number(l.ram_gb,2)} GB RAM · ${number(l.disk_gb,1)} GB ${t('disk')}`;
 $('device').textContent=t('device')+'  '+s.identity.device_id;$('token').textContent=t('token')+'  '+s.identity.token_masked;
 $('hardware').textContent=`${h.os} · ${h.cpu_model} · ${number(h.cores_logical)} ${t('threads')} · ${number(h.ram_gb,1)} GB RAM · `+(h.has_gpu?`${h.gpu_name} ${number(h.gpu_vram_gb,1)} GB`:t('noGpu'))+` · ${t('uptime')} ${number(h.uptime_hours)} ${t('hours')} · ${t('probe')} ${number(h.probe_ms)} ms`;
}
function translate(){language=resolve();document.documentElement.lang=language;select.value=preference;
 document.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=t(el.dataset.i18n);});
 select.options[0].textContent=t('auto');$('rotated').textContent=rotated?t('rotated'):'';$('status').textContent=failed?t('error'):'';if(state)paint(state);
}
select.addEventListener('change',()=>{preference=select.value;try{localStorage.setItem(storageKey,preference);}catch{}translate();});
window.addEventListener('languagechange',()=>{if(preference==='auto')translate();});
async function request(url,body){try{const response=await fetch(url,body);if(!response.ok)throw Error('HTTP '+response.status);const next=await response.json();failed=false;$('status').textContent='';paint(next);return true;}catch{failed=true;$('status').textContent=t('error');return false;}}
const post=(url,body={})=>request(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
keys.forEach(k=>{$(k).addEventListener('input',()=>{$(k+'_o').textContent=number(+$(k).value)+'%';});$(k).addEventListener('change',()=>post('/api/share',Object.fromEntries(keys.map(key=>[key+'_pct',+$(key).value]))));});
$('autostart').addEventListener('change',event=>post('/api/autostart',{enabled:event.target.checked}));
$('rotate').addEventListener('click',async()=>{if(await post('/api/rotate')){rotated=true;$('rotated').textContent=t('rotated');}});
translate();request('/api/state');setInterval(()=>request('/api/state'),5000);
})();
"""
