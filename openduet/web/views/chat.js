import {api} from '../api.js';
import {state, escape, t} from '../state.js';
import {title, mark, source} from '../ui.js';
const drafts=new Map();
let draftGeneration=0;
function draftFor(channel){
  if(!drafts.has(channel))drafts.set(channel,{text:'',attachment:'',filename:'',uploading:false,sending:false});
  return drafts.get(channel);
}
export function clearDrafts(){draftGeneration++;drafts.clear();}
function syncDraft(channel,draft,generation){
  const form=document.querySelector('#compose');
  if(generation!==draftGeneration||!form||form.dataset.channel!==channel)return;
  form.setAttribute('aria-busy',String(draft.uploading||draft.sending));
  const prompt=form.querySelector('#prompt');
  if(prompt.value!==draft.text)prompt.value=draft.text;
  prompt.disabled=draft.sending;
  const attachment=form.querySelector('#attachment');
  attachment.disabled=draft.uploading||draft.sending;
  if(!draft.attachment&&!draft.uploading&&!draft.sending)attachment.value='';
  form.querySelector('button[type=submit]').disabled=draft.uploading||draft.sending;
  form.querySelector('#attachment-status').textContent=draft.uploading?t('Uploading…','Caricamento…'):draft.filename;
  const remove=form.querySelector('#remove-attachment');
  remove.hidden=!draft.attachment;remove.disabled=draft.sending||draft.uploading;
}
export function render() {
  const draft=draftFor(state.channel);
  const sources = state.product.sources || [];
  return title('Chat',t('The same thread as Telegram.','La stessa conversazione di Telegram.')) + `<div class="channel-bar"><label>${t('Channel','Canale')}<select id="channel">${(state.data.channels||[]).map(channel=>`<option value="${channel.id}" ${channel.id===state.channel?'selected':''}>${escape(channel.name)}</option>`).join('')}</select></label><button id="new-channel" class="secondary">${t('New channel','Nuovo canale')}</button></div><div class="thread" aria-live="polite">${state.messages.map(message=>`<article class="message ${message.role}">${message.role==='assistant'?mark():''}<div><small>${message.role==='assistant'?'OpenDuet':t('You','Tu')}</small><p class="prose">${escape(message.content)}</p><div class="source-list">${sources.filter(item=>item.task===message.task && message.content.includes('[^'+item.id+']')).map(source).join('')}</div>${(state.product.suggestions||[]).filter(item=>item.task===message.task).map(item=>{const suggestion=JSON.parse(item.content);return `<aside class="card"><h2>${escape(suggestion.name)}</h2><p>${escape(suggestion.reason)}</p><button data-view="connections">${t('Open Connections','Apri Connessioni')}</button></aside>`;}).join('')}</div></article>`).join('') || `<p class="muted">${t('What can I help move forward?','Su cosa vuoi lavorare?')}</p>`}</div><form id="compose" data-channel="${escape(state.channel)}" aria-busy="${draft.uploading||draft.sending}"><label for="prompt" class="sr-only">${t('Your message','Il tuo messaggio')}</label><textarea id="prompt" name="content" rows="3" required maxlength="32000" placeholder="${escape(t('Ask for research, a draft, or work in an app…','Chiedi una ricerca, una bozza o un’attività in un’app…'))}">${escape(draft.text)}</textarea><div class="split"><label class="upload">${t('Attach file','Allega file')}<input id="attachment" type="file" accept=".txt,.md,.csv,.pdf,.docx,.xlsx,.png,.jpg,.ogg,.mp3,.wav"></label><div><button type="button" id="record" class="secondary" ${state.data.voice?'':'disabled'}>${t('Record','Registra')}</button><button type="submit">${t('Send','Invia')}</button></div></div><small id="attachment-status">${escape(draft.uploading?t('Uploading…','Caricamento…'):draft.filename)}</small><button id="remove-attachment" type="button" class="quiet" ${draft.attachment?'':'hidden'}>${t('Remove attachment','Rimuovi allegato')}</button></form>`;
}
export function bind(refresh) {
  document.querySelector('#channel').onchange = async event => {state.channel=event.target.value;await refresh();};
  document.querySelector('#new-channel').onclick = async () => {
    const name = prompt(t('Channel name','Nome del canale')); if(!name)return;
    const result=await api('/api/channels',{name});state.channel=result.id;await refresh();
  };
  const channel=state.channel,draft=draftFor(channel),generation=draftGeneration;
  document.querySelector('#prompt').oninput=event=>{draft.text=event.target.value;};
  document.querySelector('#remove-attachment').onclick=()=>{draft.attachment='';draft.filename='';document.querySelector('#attachment').value='';syncDraft(channel,draft,generation);};
  document.querySelector('#attachment').onchange=async event=>{
    const file=event.target.files[0];if(!file||draft.uploading||draft.sending)return;
    draft.uploading=true;draft.attachment='';draft.filename='';syncDraft(channel,draft,generation);
    try{
      const result=await api('/api/attachments?name='+encodeURIComponent(file.name),file);
      if(generation!==draftGeneration)return;
      draft.attachment=result.attachment;draft.filename=file.name;
    }finally{draft.uploading=false;syncDraft(channel,draft,generation);}
  };
  document.querySelector('#compose').onsubmit=async event=>{
    event.preventDefault();if(draft.uploading||draft.sending)return;
    draft.text=event.currentTarget.querySelector('#prompt').value;
    draft.sending=true;syncDraft(channel,draft,generation);
    try{
      await api('/api/messages',{content:draft.text,channel,attachments:draft.attachment?[draft.attachment]:[]});
      if(generation!==draftGeneration)return;
      draft.text='';draft.attachment='';draft.filename='';
    }finally{draft.sending=false;syncDraft(channel,draft,generation);}
    await refresh();
  };
  syncDraft(channel,draft,generation);
  let recorder, chunks=[];
  document.querySelector('#record').onclick=async event=>{
    if(recorder?.state==='recording'){recorder.stop();return;}
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];
    recorder=new MediaRecorder(stream);recorder.ondataavailable=e=>chunks.push(e.data);
    recorder.onstop=async()=>{stream.getTracks().forEach(track=>track.stop());const result=await api('/api/transcribe',new Blob(chunks,{type:recorder.mimeType}));if(generation!==draftGeneration)return;draft.text=result.text;syncDraft(channel,draft,generation);event.target.textContent=t('Record','Registra');};
    recorder.start();event.target.textContent=t('Stop recording','Ferma registrazione');
  };
}
