import RFB from './vendor/novnc/core/rfb.js';

const $ = s => document.querySelector(s);
const key = new URLSearchParams(location.search).get('computer');
let rfb;
let credentialTypes = [];
function status(text) { $('#remote-status').textContent = text; }
function disconnect() { rfb?.disconnect(); $('#control').disabled = true; $('#keyboard').disabled = true; status('Disconnected. Agent work can continue.'); }

try {
  const response = await fetch('/api/state');
  if (response.status === 401) throw new Error('Sign in to the workspace first, then open this computer again.');
  if (!response.ok) throw new Error('Workspace unavailable.');
  const state = await response.json();
  const computer = state.computers[key];
  if (!computer?.enabled) throw new Error('This computer is not configured or is disabled.');
  $('#computer-name').textContent = computer.name;
  const url = new URL(`/api/computers/${encodeURIComponent(key)}/desktop`, location.href);
  url.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  rfb = new RFB($('#remote-screen'), url.href, {shared:true});
  rfb.viewOnly = true;
  rfb.scaleViewport = true;
  rfb.resizeSession = false;
  rfb.addEventListener('connect', () => { status('View mode · agent paused'); $('#control').disabled = false; });
  rfb.addEventListener('disconnect', event => { status(event.detail.clean ? 'Disconnected. Agent work can continue.' : 'Connection closed. Check screen sharing, session expiry and active desktop tasks.'); $('#control').disabled = true; $('#keyboard').disabled = true; });
  rfb.addEventListener('securityfailure', () => status('Screen-sharing authentication failed. Check the computer credentials.'));
  rfb.addEventListener('credentialsrequired', event => {
    credentialTypes = event.detail.types;
    const fields = $('#credential-fields');
    fields.replaceChildren();
    for (const type of credentialTypes) {
      if (!['username','password','target'].includes(type)) { disconnect(); status('Unsupported screen-sharing authentication.'); return; }
      const label = document.createElement('label'); label.textContent = type[0].toUpperCase() + type.slice(1); label.htmlFor = 'credential-' + type;
      const input = document.createElement('input'); input.id = label.htmlFor; input.type = type === 'password' ? 'password' : 'text'; input.autocomplete = 'off'; input.required = true;
      fields.append(label,input);
    }
    $('#credentials').showModal();
  });
  rfb.addEventListener('serververification', event => {
    $('#server-key').textContent = event.detail.type + ': ' + Array.from(new Uint8Array(event.detail.publickey || [])).map(v => v.toString(16).padStart(2,'0')).join(':');
    $('#server-identity').showModal();
  });
} catch (error) { status(error.message); }

$('#credentials-form').addEventListener('submit', event => {
  event.preventDefault();
  const credentials = {};
  for (const type of credentialTypes) { const input = $('#credential-' + type); credentials[type] = input.value; input.value = ''; }
  rfb.sendCredentials(credentials); $('#credentials').close();
});
$('#cancel-login').onclick = () => { $('#credentials').close(); disconnect(); };
$('#credentials').addEventListener('cancel', disconnect);
$('#server-identity').addEventListener('cancel', disconnect);
$('#trust-server').onclick = () => { rfb.approveServer(); $('#server-identity').close(); };
$('#reject-server').onclick = () => { $('#server-identity').close(); disconnect(); };
$('#control').onclick = () => {
  rfb.viewOnly = !rfb.viewOnly;
  $('#control').textContent = rfb.viewOnly ? 'Take control' : 'View only';
  $('#keyboard').disabled = rfb.viewOnly;
  status(rfb.viewOnly ? 'View mode · agent paused' : 'You have control · agent paused');
  if (!rfb.viewOnly) rfb.focus();
};
$('#keyboard').onclick = () => $('#mobile-keyboard').focus();
$('#mobile-keyboard').addEventListener('input', event => {
  if (!rfb || rfb.viewOnly) return;
  for (const char of event.target.value) {
    const point = char.codePointAt(0);
    rfb.sendKey(point < 256 ? point : point | 0x01000000, null);
  }
  event.target.value = '';
});
$('#mobile-keyboard').addEventListener('keydown', event => {
  if (!rfb || rfb.viewOnly) return;
  const keys = {Enter:0xff0d,Backspace:0xff08,Tab:0xff09,Escape:0xff1b};
  if (keys[event.key]) { event.preventDefault(); rfb.sendKey(keys[event.key], null); }
});
$('#fullscreen').onclick = async () => {
  try { document.fullscreenElement ? await document.exitFullscreen() : await document.documentElement.requestFullscreen(); }
  catch { status('Full screen is unavailable in this browser.'); }
};
$('#disconnect').onclick = disconnect;
window.addEventListener('pagehide', disconnect);
