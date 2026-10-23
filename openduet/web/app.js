import {api} from './api.js';
import {state, escape, t} from './state.js';
import {mark, toast} from './ui.js';
import * as telegram from './views/telegram.js';
import * as tasks from './views/tasks.js';
import * as make from './views/make.js';
import * as proactivity from './views/proactivity.js';
import * as connections from './views/connections.js';
import * as settings from './views/settings.js';
import * as chat from './views/chat.js';
const views={telegram,tasks,make,proactivity,connections,settings,chat};
let source,loading=false,editingCall='';
const requestedView=new URLSearchParams(location.search).get('view');
if(views[requestedView])state.view=requestedView;
const labels=()=>({telegram:'Telegram',tasks:t('Tasks','Attività'),make:'Make',proactivity:t('Proactivity','Proattività'),connections:t('Connections','Connessioni'),settings:t('Settings','Impostazioni'),chat:'Chat'});
document.documentElement.dataset.theme=localStorage.getItem('theme')||'system';
document.querySelector('#login-mark').innerHTML=mark();
document.querySelector('#brand-mark').innerHTML=mark();
document.querySelector('#mobile-mark').innerHTML=mark();
window.addEventListener('unhandledrejection',event=>{event.preventDefault();toast(event.reason?.message||t('Something needs attention.','Qualcosa richiede attenzione.'));});
function navigation(){
  const primary=miniapp?['tasks','make']:['telegram','tasks','make','proactivity'];
  const button=([key,label])=>`<button type="button" data-view="${key}" class="${primary.includes(key)?'primary-view':'extra-view'}" aria-current="${key===state.view?'page':'false'}"><span class="nav-dot" aria-hidden="true"></span>${escape(label)}</button>`;
  document.querySelector('#navigation').innerHTML=Object.entries(labels()).filter(([key])=>!miniapp||primary.includes(key)).map(button).join('')+`<button id="more-button" type="button" aria-label="${t('More views','Altre viste')}" aria-haspopup="dialog">•••<span>${t('More','Altro')}</span></button>`;
  document.querySelector('#more-links').innerHTML=Object.entries(labels()).filter(([key])=>!primary.includes(key)).map(button).join('');
}

export async function refresh(force=true){
  if(loading)return;loading=true;
  try {
    const [data,product,messages]=await Promise.all([api('/api/state'),api('/api/product'),api('/api/messages?channel='+encodeURIComponent(state.channel))]);
    state.data=data;state.product=product;state.messages=messages;
    document.documentElement.dataset.onboarding=String(!product.telegram.paired&&!miniapp);
    if(!product.telegram.paired&&!miniapp)state.view='telegram';
    if(!miniapp&&!product.proactivity.configured){await api('/api/proactivity',{timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,language:navigator.language.startsWith('it')?'it':'en'});}
    document.documentElement.lang=localStorage.getItem('language')||(navigator.language.startsWith('it')?'it':'en');
    document.querySelectorAll('.brand .glasses,.mobile-brand .glasses').forEach(mark=>mark.classList.toggle('working',data.tasks.some(task=>task.status==='running')));
    document.querySelector('#login').hidden=true;document.querySelector('#workspace').hidden=false;
    if(!force && (document.activeElement?.closest('form') || document.querySelector('dialog[open]') || document.querySelector('[aria-busy="true"]')))return;
    navigation();document.querySelector('#content').innerHTML=views[state.view].render();views[state.view].bind(()=>refresh(true));
    document.title=labels()[state.view]+' · OpenDuet';
    if(!source){source=new EventSource('/api/stream');source.addEventListener('change',()=>refresh(false));}
  } catch(error){
    if(error.status===401){source?.close();source=null;document.querySelector('#workspace').hidden=true;document.querySelector('#login').hidden=false;}
    else toast(error.message);
  } finally {loading=false;}
}
document.querySelector('#login-form').onsubmit=async event=>{event.preventDefault();const form=event.currentTarget;await api('/api/login',{token:document.querySelector('#token').value});form.reset();state.view='telegram';await refresh();};
document.addEventListener('click',async event=>{
  const target=event.target.closest('button,a');if(!target)return;
  try {
    if(target.id==='more-button')document.querySelector('#more-navigation').showModal();
    if(target.dataset.view){document.querySelector('#more-navigation').close();state.view=target.dataset.view;await refresh();document.querySelector('#content').focus();}
    if(target.dataset.copy){await navigator.clipboard.writeText(target.dataset.copy);toast(t('Copied.','Copiato.'));}
    if(target.dataset.task){await api(`/api/tasks/${target.dataset.id}/${target.dataset.task}`,{});await refresh();}
    if(target.dataset.taskChat){state.channel=target.dataset.taskChat;state.view='chat';await refresh();}
    if(target.dataset.review){await api('/api/reviews/'+target.dataset.call,{action:target.dataset.review});await refresh();}
    if(target.dataset.editCall){const card=state.product.approvals.find(card=>card.id===target.dataset.editCall);editingCall=card.id;document.querySelector('#review-payload').value=JSON.stringify(card.payload,null,2);document.querySelector('#review-editor').showModal();}
    if(target.dataset.resolve){const receipt=prompt(t('What did you verify at the service?','Cosa hai verificato nel servizio?'));if(receipt){await api('/api/calls/'+target.dataset.resolve+'/resolve',{happened:target.dataset.happened==='yes',receipt});await refresh();}}
    if(target.dataset.close)document.getElementById(target.dataset.close).close();
    if(target.id==='logout'){await api('/api/logout',{});source?.close();source=null;await refresh();}
    if(target.dataset.preview || target.dataset.revise || target.dataset.diff)await make.action(target,()=>refresh());
  } catch(error){toast(error.message);}
});
document.querySelector('#review-form').onsubmit=async event=>{event.preventDefault();await api('/api/reviews/'+editingCall,{action:'edit',edited:JSON.parse(document.querySelector('#review-payload').value)});document.querySelector('#review-editor').close();await refresh();};
const telegramHash=new URLSearchParams(location.hash.slice(1));
const miniapp=telegramHash.get('tgWebAppData');
document.documentElement.dataset.miniapp=String(Boolean(miniapp));
if(miniapp){try{const colors=JSON.parse(telegramHash.get('tgWebAppThemeParams')||'{}');for(const [field,variable] of Object.entries({bg_color:'--bg',secondary_bg_color:'--surface',text_color:'--ink',hint_color:'--muted',button_color:'--accent',button_text_color:'--accent-text'})){if(/^#[0-9a-f]{6}$/i.test(colors[field]||''))document.documentElement.style.setProperty(variable,colors[field]);}}catch{}}

const setupCode=telegramHash.get('setup');
if(setupCode){history.replaceState(null,'',location.pathname+location.search);try{await api('/api/local-session',{code:setupCode});}catch(error){toast(error.message);}}
if(miniapp){try{await api('/api/telegram/session',{init_data:miniapp});state.view=new URLSearchParams(location.search).get('view')==='make'?'make':'tasks';}catch(error){toast(error.message);}}
await refresh();
