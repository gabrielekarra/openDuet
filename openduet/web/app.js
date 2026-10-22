const $ = s => document.querySelector(s);
const escape = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state, view = 'home', channel = 'main', provider = '', draft = '', editorItem, lastEvent = 0, snapshot = '';
const pendingStates = new Set(['queued','running','awaiting_approval','blocked','interrupted']);
const dates = timestamp => new Date(timestamp * 1000).toLocaleString([], {dateStyle:'medium',timeStyle:'short'});
function toast(message) { $('#toast').textContent = message; $('#toast').hidden = false; setTimeout(() => $('#toast').hidden = true, 6000); }
async function api(path, options = {}) {
  const response = await fetch('/api/' + path, { ...options, headers: {'Content-Type':'application/json', ...options.headers}});
  if (response.status === 401) { $('#login').hidden = false; $('#workspace').hidden = true; throw new Error('Sign in to your workspace.'); }
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Please check the form values.');
  return result;
}
const post = (path, body = {}) => api(path, {method:'POST',body:JSON.stringify(body)});
const del = path => api(path, {method:'DELETE'});
function bind(selector, action) { $(selector)?.addEventListener('click', event => { Promise.resolve(action(event)).catch(error => toast(error.message)); }); }
const button = (label, action, id, style = 'quiet') => `<button class="${style}" data-action="${action}" data-id="${escape(id)}">${label}</button>`;
function taskCard(task) {
  const action = task.status === 'ready' ? button('Mark complete ✓','complete',task.id) : '';
  const resume = ['failed','blocked','interrupted','awaiting_approval'].includes(task.status) ? button('Resume','resume',task.id) : '';
  const cancel = pendingStates.has(task.status) ? button('Stop','cancel',task.id) : '';
  return `<article class="card"><div class="meta"><span class="status-pill">${escape(task.status.replaceAll('_',' '))}</span><span>${escape(task.provider)} · ${dates(task.created)}</span></div><h3>${escape(task.request.slice(0,170))}</h3>${task.error ? `<p>${escape(task.error)}</p>` : ''}<div class="actions">${action}${resume}${cancel}</div></article>`;
}
function approvals() {
  return state.approvals.map(call => `<article class="card approval"><div class="meta">${call.status === 'uncertain' ? 'VERIFY OUTCOME' : 'YOUR APPROVAL NEEDED'}</div><h3>${escape(call.name)}</h3><pre>${escape(JSON.stringify(JSON.parse(call.arguments),null,2))}</pre><p>${call.status === 'uncertain' ? 'The connection ended without a receipt. Check the service before deciding what happened.' : 'Review the exact action and arguments. Approval applies once to this action.'}</p><div class="actions">${call.status === 'uncertain' ? button('Verify result','resolve',call.id) : button('Approve once','approve',call.id,'') + button('Reject','reject',call.id)}</div></article>`).join('');
}
const empty = (title, text) => `<div class="empty"><strong>${title}</strong>${text}</div>`;
function heading(title, subtitle) { return `<div class="heading"><div><div class="eyebrow">YOUR WORK, MOVING FORWARD</div><h1>${title}</h1><p class="subtitle">${subtitle}</p></div></div>`; }
function providerOptions() { return Object.entries(state.providers).map(([name,p]) => `<option value="${escape(name)}" ${name === (provider || state.default_provider) ? 'selected' : ''}>${escape(name)} · ${escape(p.model)}</option>`).join(''); }
function home() {
  const name = state.channels.find(c => c.id === channel)?.name || 'Home';
  const hour = new Date().getHours();
  const greeting = channel === 'main' ? hour < 12 ? 'A little room for your day.' : 'Keep the good work moving.' : escape(name);
  const active = state.tasks.filter(t => t.channel === channel && pendingStates.has(t.status));
  return `<div class="date">${new Date().toLocaleDateString([], {weekday:'long',day:'numeric',month:'long'}).toUpperCase()}</div>
    <div class="heading"><div><h1>${greeting}</h1><p class="subtitle">Hand over a task. Make space for what needs you.</p></div><span class="status-pill">${active.length ? active.length + ' task' + (active.length > 1 ? 's' : '') + ' in progress' : 'Ready when you are'}</span></div>
    ${approvals()}
    <form id="compose" class="composer"><textarea id="prompt" aria-label="Message OpenDuet" placeholder="What can I take off your plate?" required maxlength="32000">${escape(draft)}</textarea><div class="composer-bottom"><select id="provider" aria-label="Language model">${providerOptions()}</select><div><button type="button" id="voice" class="quiet" ${state.voice ? '' : 'disabled'} title="${state.voice ? 'Record a voice message; transcription stays on your server' : 'Configure a local voice_model on your server'}">◉ Voice</button> <button type="submit">Send <span class="arrow" aria-hidden="true"></span></button></div></div></form>
    <div class="suggestions"><button data-prompt="Prepare my morning brief from my connected inbox and calendar. Cite sources and draft next steps for review.">☀ Prepare my day</button><button data-prompt="Find unpaid invoices in my connected accounts. Prepare reminder drafts for me to approve; cite each invoice."><span class="arrow" aria-hidden="true"></span> Follow up on invoices</button><button data-prompt="Research the company for my next meeting using connected sources. Create a brief with citations.">▧ Get meeting-ready</button></div>
    ${active.length ? '<div class="section-heading"><h2>Moving forward</h2><small>Work continues on your server</small></div>' + active.slice(0,3).map(taskCard).join('') : ''}
    <div class="section-heading"><h2>Your conversation</h2><small>${escape(name)} · shared memory across channels</small></div><div id="messages"><div class="loading">Loading conversation…</div></div>`;
}
function make() {
  return heading('From idea to something real.', 'Documents, spreadsheets, decks and dashboards. Review, download and make them yours.') +
    (state.artifacts.length ? `<div class="grid">${state.artifacts.map(a => `<article class="card"><div class="artifact-icon">${escape(a.format.toUpperCase())}</div><h3>${escape(a.title)}</h3><small>${dates(a.created)}</small><div class="actions"><a href="/api/artifacts/${a.id}" download>Download <span class="arrow" aria-hidden="true"></span></a>${['md','txt','html','csv'].includes(a.format) ? button('Edit','edit',a.id) : ''}</div></article>`).join('')}</div>` : empty('Your next idea can live here.', 'Ask OpenDuet to create a document, deck, spreadsheet or dashboard in your conversation.'));
}
function routines() {
  return heading('A rhythm that works for you.', 'Morning briefs, regular check-ins and follow-ups. Runs on your server, even when this app is closed.') +
    `<form id="routine-form" class="card"><h3>Set up a routine</h3><label for="routine-name">Name</label><input id="routine-name" required placeholder="My morning brief"><label for="routine-prompt">What should OpenDuet do?</label><textarea id="routine-prompt" rows="3" required placeholder="Review my inbox and calendar. Flag new urgent items and draft next steps. Say NO_UPDATE if nothing needs me."></textarea><div class="grid"><div><label for="routine-start">First run (your local time)</label><input id="routine-start" type="datetime-local" required></div><div><label for="routine-interval">Repeat</label><select id="routine-interval"><option value="86400">Every day</option><option value="10800">Every three hours</option><option value="604800">Every week</option><option value="3600">Every hour</option></select></div></div><label for="routine-provider">Model</label><select id="routine-provider">${providerOptions()}</select><div class="actions"><button>Create routine <span class="arrow" aria-hidden="true"></span></button></div><p class="hint">Intervals use elapsed time. Adjust the first run after daylight saving changes. Connected accounts are needed for inbox and calendar work.</p></form>` +
    state.schedules.map(s => `<article class="card"><div class="split"><h3>${escape(s.name)}</h3>${button('Remove','unschedule',s.id)}</div><p>${escape(s.prompt)}</p><small>Next: ${dates(s.next_run)} · every ${s.interval/3600} hours · ${escape(s.provider)}</small></article>`).join('');
}
function memories() {
  return heading('A little context goes a long way.', 'What you choose to remember travels across your channels. You can review, export or forget it.') +
    `<form id="memory-form" class="card"><label for="new-memory">Something useful to remember</label><textarea id="new-memory" rows="2" required placeholder="My workday starts at 9. I prefer brief, friendly email drafts."></textarea><div class="actions"><button>Remember this</button> <a href="/api/export" download>Export my data <span class="arrow" aria-hidden="true"></span></a></div></form>
    <form id="search-form" class="search-row"><input id="search-query" placeholder="Search past conversations" aria-label="Search conversations"><button class="quiet">Search</button></form><div id="search-results"></div>` +
    state.memories.map(m => `<article class="card"><p>${escape(m.content)}</p><div class="actions">${button('Forget','forget',m.id)}</div></article>`).join('') +
    `<form id="import-form" class="card"><h3>Bring your context</h3><p>Paste a memory summary from another assistant. Review it before importing.</p><textarea id="import-memory" rows="3" required></textarea><div class="actions"><button class="quiet">Import as memory</button></div></form>`;
}
function connections() {
  return heading('Bring your tools together.', 'Use your own MCP servers for mail, calendars, files and business tools. You choose what gets access.') +
    `<div class="card"><div class="split"><h3>Configured connectors</h3><button id="refresh-connectors" class="quiet">Refresh tools ↻</button></div><p>Configure HTTP or stdio MCP servers in openduet.toml on your server, with credentials bound from environment variables. Tool calls ask for approval unless you explicitly allow a tool in the server configuration.</p></div>` +
    (Object.entries(state.connectors).map(([n,c]) => `<article class="card"><div class="split"><div><h3>${escape(n)}</h3><small>${c.enabled ? c.error ? escape(c.error) : 'Enabled' : 'Disconnected'}</small></div>${button(c.enabled ? 'Disconnect' : 'Enable','connector',n)}</div></article>`).join('') || empty('Connect your first tool.', 'Gmail, Calendar, Drive, Slack, Stripe and other services can be added through compatible MCP servers. Each service requires your own authorization.')) +
    `<div class="section-heading"><h2>Your browser</h2></div><div class="card"><h3>${state.browser.enabled ? 'Dedicated browser enabled' : 'Browser is optional'}</h3><p>${state.browser.enabled ? 'Allowed sites: ' + escape(state.browser.hosts.join(', ')) + '\nCurrent page: ' + escape(state.browser.url || 'No page open') : 'Install the browser extra and configure browser_hosts to let OpenDuet use websites without a connector.'}</p>${state.browser.enabled ? '<form id="browser-login"><label for="login-selector">Login field CSS selector</label><input id="login-selector" required placeholder="input[type=password]"><label for="login-value">Private login value</label><input id="login-value" type="password" required autocomplete="off"><div class="actions"><button>Enter directly in browser</button></div><p class="hint">Sent to the browser only. Never stored in conversation or sent to the language model. Pause browser work before using this form.</p></form>' : ''}</div>`;
}
function computers() {
  return heading('Your computer, within reach.', 'See and control your desktop from another device while OpenDuet is running.') +
    (state.remote_desktop_active ? '<div class="card approval"><h3>Remote session active</h3><p>Agent work is paused while the remote desktop is open.</p><button id="disconnect-desktop" class="quiet">Disconnect remote session</button></div>' : '') +
    (Object.entries(state.computers).map(([key,c]) => `<article class="card"><div class="split"><div><h3>${escape(c.name)}</h3><small>${c.enabled ? 'Screen sharing configured' : 'Disabled'}</small></div>${c.enabled ? `<a class="desktop-link" href="/desktop.html?computer=${encodeURIComponent(key)}" target="_blank" rel="noopener">Open desktop <span class="arrow" aria-hidden="true"></span></a>` : ''}</div><p>Start in view mode, then take control when you need it. Disconnect to return the computer to OpenDuet.</p></article>`).join('') || empty('Connect your computer.', 'Enable screen sharing on the computer and add it under computers in openduet.toml. On Mac, enable Remote access in the native app settings.')) +
    '<div class="card"><h3>Reach it from your phone or another computer</h3><p>Open this workspace through your private network or HTTPS address and sign in. The computer must be awake and OpenDuet must be running.</p><p class="hint">Your screen and remote input stay outside model context. The remote session uses the computer’s own screen-sharing authentication.</p></div>';
}
function settings() {
  const usage = state.usage.input + state.usage.output;
  return heading('Make it your own.', 'Your models, your instructions and your boundaries.') +
    `<div class="card"><h3>Model providers</h3>${Object.entries(state.providers).map(([n,p]) => `<p><strong>${escape(n)}</strong> · ${escape(p.model)}<br><small>${escape(p.base_url)} · ${p.tools ? 'Native tools' : 'Text tool protocol'}</small></p>`).join('')}<p class="hint">Add any OpenAI-compatible endpoint, Ollama or Anthropic in openduet.toml. Local endpoints do not need an API key. Remote models receive the context used by their tasks.</p></div>
    <div class="card"><h3>Today's usage</h3><progress value="${usage}" max="${state.daily_token_budget}"></progress><small>${usage.toLocaleString()} / ${state.daily_token_budget.toLocaleString()} tokens · includes background tasks · estimates used when a provider omits counts</small></div>
    <form id="settings-form" class="card"><h3>Memory & skills</h3><label class="toggle"><input id="search-chats" type="checkbox" ${state.settings.search_chats ? 'checked' : ''}> Allow searching past conversations</label><label for="skill-name">Skill name</label><input id="skill-name" placeholder="Small business"><label for="skill-content">Reusable instructions</label><textarea id="skill-content" rows="4" placeholder="For unpaid invoices, cite the invoice id and due date. Prepare a courteous reminder for approval. Never send automatically."></textarea><p class="hint">Skills guide task preparation. They cannot approve actions or grant access.</p><div class="actions"><button>Save settings</button></div></form>` +
    Object.entries(state.settings.skills).map(([n,s]) => `<div class="card"><h3>${escape(n)}</h3><p>${escape(s)}</p>${button('Remove skill','remove-skill',n)}</div>`).join('') +
    `<div class="card"><h3>Your workspace</h3><p>OpenDuet is independent from Anthropic. This preview has no proprietary Claude account access, payment wallet or native mobile app. Use your phone's Add to Home Screen for this web app.</p><div class="actions"><a href="https://github.com/gabrielekarra/openDuet" rel="noreferrer" target="_blank">Source & documentation <span class="arrow" aria-hidden="true"></span></a><button id="logout" class="quiet">Sign out</button>${button('Delete current channel & history','delete-channel',channel)}</div></div>`;
}
async function render() {
  $('#breadcrumb').textContent = `Workspace / ${view[0].toUpperCase() + view.slice(1)}`;
  document.querySelectorAll('nav button').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  $('#task-count').textContent = state.tasks.filter(t => pendingStates.has(t.status)).length || '';
  $('#channels').innerHTML = state.channels.map(c => `<button data-channel="${c.id}" class="${c.id === channel ? 'selected' : ''}"># ${escape(c.name)}</button>`).join('');
  $('#content').innerHTML = ({home, tasks: () => heading('Good things, in motion.', 'Review progress, approve the important steps and mark work complete when you are satisfied.') + approvals() + (state.tasks.map(taskCard).join('') || empty('A clear space.', 'Give OpenDuet a task to get started.')), make, routines, memory:memories, connections, computers, settings})[view]();
  document.querySelectorAll('[data-channel]').forEach(b => b.onclick = () => { channel = b.dataset.channel; view = 'home'; render(); });
  $('#prompt')?.addEventListener('input', e => draft = e.target.value);
  $('#provider')?.addEventListener('change', e => provider = e.target.value);
  $('#compose')?.addEventListener('submit', async e => { e.preventDefault(); try { await post('messages',{content:$('#prompt').value,channel,provider:$('#provider').value}); draft = ''; await refresh(true); } catch(e) { toast(e.message); } });
  bind('#voice', recordVoice);
  $('#routine-form')?.addEventListener('submit', async e => { e.preventDefault(); try { await post('schedules',{name:$('#routine-name').value,prompt:$('#routine-prompt').value,channel,provider:$('#routine-provider').value,interval:Number($('#routine-interval').value),next_run:new Date($('#routine-start').value).getTime()/1000}); await refresh(true); toast('Routine scheduled.'); } catch(e) { toast(e.message); } });
  $('#memory-form')?.addEventListener('submit', async e => { e.preventDefault(); try { await post('memories',{content:$('#new-memory').value}); await refresh(true); } catch(e) { toast(e.message); } });
  $('#import-form')?.addEventListener('submit', async e => { e.preventDefault(); try { await post('import',{memories:[{content:$('#import-memory').value}]}); await refresh(true); } catch(e) { toast(e.message); } });
  $('#search-form')?.addEventListener('submit', async e => { e.preventDefault(); try { const found = await api('search?q=' + encodeURIComponent($('#search-query').value)); $('#search-results').innerHTML = found.map(m => `<div class="card"><small>${escape(m.id)}</small><p>${escape(m.content)}</p></div>`).join('') || empty('No matches.', 'Search another phrase, or enable chat search in Settings.'); } catch(e) { toast(e.message); } });
  $('#settings-form')?.addEventListener('submit', async e => { e.preventDefault(); try { const skills = {...state.settings.skills}; if ($('#skill-name').value && $('#skill-content').value) skills[$('#skill-name').value] = $('#skill-content').value; await post('settings',{...state.settings,search_chats:$('#search-chats').checked,skills}); await refresh(true); toast('Settings saved.'); } catch(e) { toast(e.message); } });
  $('#browser-login')?.addEventListener('submit', async e => { e.preventDefault(); try { await post('browser/login',{selector:$('#login-selector').value,value:$('#login-value').value,expected_url:state.browser.url}); $('#login-value').value = ''; toast('Value entered directly in browser.'); } catch(e) { toast(e.message); } });
  bind('#refresh-connectors', async () => { await post('connectors/refresh'); await refresh(true); toast('Tool discovery refreshed.'); });
  bind('#logout', async () => { await post('logout'); location.reload(); });
  bind('#disconnect-desktop', async () => { await post('computers/disconnect'); await refresh(true); });
  if (view === 'home') {
    const messages = await api('messages?channel=' + channel);
    if (!$('#messages')) return;
    $('#messages').innerHTML = messages.length ? messages.map(m => `<article class="message ${escape(m.role)}"><div class="role">${m.role === 'assistant' ? 'OPENDUET' : 'YOU'}<time>${dates(m.created)}</time></div><div class="text">${escape(m.content)}</div>${m.role === 'assistant' ? button('Read aloud','speak',m.id) : ''}</article>`).join('') : empty('One conversation. Plenty of possibilities.', 'Ask a question, hand over a task, or start with a morning brief.');
    window.currentMessages = messages;
  }
}
async function handleContent(event) {
  const prompt = event.target.closest('[data-prompt]');
  if (prompt) { $('#prompt').value = prompt.dataset.prompt; draft = prompt.dataset.prompt; $('#prompt').focus(); return; }
  const target = event.target.closest('[data-action]');
  if (!target) return;
  const {action,id} = target.dataset;
  try {
    if (['complete','cancel','resume'].includes(action)) await post(`tasks/${id}/${action}`);
    if (['approve','reject'].includes(action)) await post('approvals/' + id,{approve:action === 'approve'});
    if (action === 'resolve') { const happened = confirm('After checking the service: did this action happen? OK = yes, Cancel = no.'); const receipt = window.prompt('Describe what you verified (required).'); if (!receipt) return; await post(`calls/${id}/resolve`,{happened,receipt}); toast('Verification saved. You can resume the task.'); }
    if (action === 'unschedule') await del('schedules/' + id);
    if (action === 'forget' && confirm('Forget this memory? Stop active tasks first.')) await del('memories/' + id);
    if (action === 'delete-channel' && confirm('Delete this channel, its conversations, tasks and generated files?')) { await del('channels/' + id); channel = 'main'; }
    if (action === 'connector') { const disabled = new Set(state.settings.disabled_connectors); disabled.has(id) ? disabled.delete(id) : disabled.add(id); await post('settings',{...state.settings,disabled_connectors:[...disabled]}); }
    if (action === 'remove-skill') { const skills = {...state.settings.skills}; delete skills[id]; await post('settings',{...state.settings,skills}); }
    if (action === 'edit') { editorItem = state.artifacts.find(a => a.id === id); const data = await api('artifact-text/' + id); $('#editor-title').textContent = editorItem.title; $('#editor-content').value = data.content; $('#editor').showModal(); return; }
    if (action === 'speak') { const voice = window.speechSynthesis?.getVoices().find(v => v.localService); if (!voice) { toast('No local speech voice available. Use the native Mac app for offline voice.'); return; } const utterance = new SpeechSynthesisUtterance(window.currentMessages.find(m => m.id === id).content); utterance.voice = voice; speechSynthesis.speak(utterance); return; }
    await refresh(true);
  } catch(e) { toast(e.message); }
}
let recorder, recordingStream, recordingTimer;
async function recordVoice() {
  if (recorder?.state === 'recording') { recorder.stop(); return; }
  recordingStream = await navigator.mediaDevices.getUserMedia({audio:true});
  recorder = new MediaRecorder(recordingStream);
  const chunks = [];
  recorder.ondataavailable = e => chunks.push(e.data);
  recorder.onstop = async () => {
    clearTimeout(recordingTimer); recordingStream.getTracks().forEach(t => t.stop());
    try { const result = await api('transcribe',{method:'POST',body:new Blob(chunks,{type:recorder.mimeType}),headers:{'Content-Type':recorder.mimeType}}); draft = (draft + ' ' + result.text).trim(); await render(); } catch(e) { toast(e.message); }
  };
  recorder.start(); $('#voice').textContent = '■ Stop recording'; recordingTimer = setTimeout(() => { if (recorder.state === 'recording') recorder.stop(); }, 90000);
}
async function refresh(force = false) {
  const next = await api('state');
  state = next; $('#login').hidden = true; $('#workspace').hidden = false;
  const stamp = JSON.stringify(next);
  const editing = ['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName) || $('#editor').open || recorder?.state === 'recording';
  if (force || (stamp !== snapshot && !editing)) { snapshot = stamp; await render(); }
}
document.querySelectorAll('nav button').forEach(b => b.onclick = () => { view = b.dataset.view; render().catch(e => toast(e.message)); });
$('#content').addEventListener('click', handleContent);
bind('#new-channel', async () => { const name = window.prompt('Name this channel'); if (name) { const result = await post('channels',{name}); channel = result.id; view = 'home'; await refresh(true); } });
bind('#save-artifact', async () => { await post(`artifacts/${editorItem.id}/versions`,{title:editorItem.title,format:editorItem.format,content:$('#editor-content').value}); $('#editor').close(); await refresh(true); toast('New version saved.'); });
bind('#notifications', async () => { if (!('Notification' in window)) return toast('Notifications are unavailable in this browser. Configure a notification relay for background alerts.'); const permission = await Notification.requestPermission(); toast(permission === 'granted' ? 'Notifications enabled while this app is open. For alerts when closed, configure notify_url on the server.' : 'Notification permission was not granted.'); });
$('#login-form').addEventListener('submit', async e => { e.preventDefault(); try { await post('login',{token:$('#token').value}); $('#token').value = ''; await refresh(true); } catch(e) { toast(e.message); } });
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
try { await refresh(true); } catch(e) { if ($('#login').hidden) toast(e.message); }
setInterval(async () => {
  if ($('#workspace').hidden) return;
  try {
    await refresh(); const events = await api('events?after=' + lastEvent);
    for (const event of events) { if (lastEvent && document.hidden && 'Notification' in window && Notification.permission === 'granted') new Notification('OpenDuet',{body:event.content,tag:event.task}); lastEvent = event.id; }
  } catch(e) { if ($('#login').hidden) toast(e.message); }
}, 4000);
