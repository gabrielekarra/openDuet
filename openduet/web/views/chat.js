import {api} from '../api.js';
import {state, escape, t} from '../state.js';
import {title, mark, source} from '../ui.js';
export function render() {
  const sources = state.product.sources || [];
  return title('Chat',t('The same thread as Telegram.','La stessa conversazione di Telegram.')) + `<div class="channel-bar"><label>${t('Channel','Canale')}<select id="channel">${(state.data.channels||[]).map(channel=>`<option value="${channel.id}" ${channel.id===state.channel?'selected':''}>${escape(channel.name)}</option>`).join('')}</select></label><button id="new-channel" class="secondary">${t('New channel','Nuovo canale')}</button></div><div class="thread" aria-live="polite">${state.messages.map(message=>`<article class="message ${message.role}">${message.role==='assistant'?mark():''}<div><small>${message.role==='assistant'?'OpenDuet':t('You','Tu')}</small><p class="prose">${escape(message.content)}</p><div class="source-list">${sources.filter(item=>item.task===message.task && message.content.includes('[^'+item.id+']')).map(source).join('')}</div>${(state.product.suggestions||[]).filter(item=>item.task===message.task).map(item=>{const suggestion=JSON.parse(item.content);return `<aside class="card"><h2>${escape(suggestion.name)}</h2><p>${escape(suggestion.reason)}</p><button data-view="connections">${t('Open Connections','Apri Connessioni')}</button></aside>`;}).join('')}</div></article>`).join('') || `<p class="muted">${t('What can I help move forward?','Su cosa vuoi lavorare?')}</p>`}</div><form id="compose"><label for="prompt" class="sr-only">${t('Your message','Il tuo messaggio')}</label><textarea id="prompt" name="content" rows="3" required maxlength="32000" placeholder="${escape(t('Ask for research, a draft, or work in an app…','Chiedi una ricerca, una bozza o un’attività in un’app…'))}"></textarea><div class="split"><label class="upload">${t('Attach file','Allega file')}<input id="attachment" type="file" accept=".txt,.md,.csv,.pdf,.docx,.xlsx,.png,.jpg,.ogg,.mp3,.wav"></label><div><button type="button" id="record" class="secondary" ${state.data.voice?'':'disabled'}>${t('Record','Registra')}</button><button type="submit">${t('Send','Invia')}</button></div></div><small id="attachment-status"></small></form>`;
}
export function bind(refresh) {
  document.querySelector('#channel').onchange = async event => {state.channel=event.target.value;await refresh();};
  document.querySelector('#new-channel').onclick = async () => {
    const name = prompt(t('Channel name','Nome del canale')); if(!name)return;
    const result=await api('/api/channels',{name});state.channel=result.id;await refresh();
  };
  let attachment='';
  document.querySelector('#attachment').onchange=async event=>{
    const file=event.target.files[0];if(!file)return;
    const result=await api('/api/attachments?name='+encodeURIComponent(file.name),file);
    attachment=result.attachment;
    document.querySelector('#attachment-status').textContent=file.name;
  };
  document.querySelector('#compose').onsubmit=async event=>{
    event.preventDefault();const form=event.currentTarget;const content=document.querySelector('#prompt').value;
    await api('/api/messages',{content,channel:state.channel,attachments:attachment?[attachment]:[]});attachment='';form.reset();await refresh();
  };
  let recorder, chunks=[];
  document.querySelector('#record').onclick=async event=>{
    if(recorder?.state==='recording'){recorder.stop();return;}
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];
    recorder=new MediaRecorder(stream);recorder.ondataavailable=e=>chunks.push(e.data);
    recorder.onstop=async()=>{stream.getTracks().forEach(track=>track.stop());const result=await api('/api/transcribe',new Blob(chunks,{type:recorder.mimeType}));document.querySelector('#prompt').value=result.text;event.target.textContent=t('Record','Registra');};
    recorder.start();event.target.textContent=t('Stop recording','Ferma registrazione');
  };
}
