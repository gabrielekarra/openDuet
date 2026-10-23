import {readiness} from '../cards/readiness.js';
import {api} from '../api.js';
import {state, escape, t} from '../state.js';
import {title, field, toast, safeLink} from '../ui.js';
export function render() {
  const bot = state.product.telegram || {};
  return title('Telegram',t('Your own bot. One conversation, wherever you are.','Il tuo bot. Un’unica conversazione, ovunque sei.')) +
    `<div class="two-up"><article class="card"><h2>${t('Create your bot','Crea il tuo bot')}</h2><ol class="steps"><li><a href="https://t.me/BotFather" target="_blank" rel="noopener">${t('Open @BotFather','Apri @BotFather')}</a> <button class="quiet" data-copy="/newbot">${t('Copy /newbot','Copia /newbot')}</button></li><li>${t('Choose a name, then a username ending in bot.','Scegli un nome e uno username che termina con bot.')}</li><li>${t('Copy the token from BotFather and paste it here.','Copia il token ricevuto da BotFather e incollalo qui.')}</li><li>${t('Optional: /setuserpic, then use the glasses avatar.','Facoltativo: /setuserpic, poi usa l’avatar con gli occhiali.')} <a href="/brand/telegram-avatar.png" download>${t('Download avatar','Scarica avatar')}</a></li></ol><p class="muted">${t('Messages and files pass through Telegram’s servers.','Messaggi e file passano dai server di Telegram.')}</p></article>
    <article class="card"><h2>${bot.connected ? '@'+escape(bot.username) : t('Connect the bot','Collega il bot')}</h2>${bot.paired ? `<p class="success">${t('Paired with','Associato a')} ${escape(bot.owner_name)}</p><div class="actions"><button data-bot="test">${t('Send test message','Invia un messaggio di prova')}</button><button data-bot="pair" class="secondary">${t('Pair another account','Associa un altro account')}</button><button data-bot="disconnect" class="quiet">${t('Disconnect','Disconnetti')}</button></div>` : `<p>${t('After connecting, open the private pairing link in your Telegram account. It expires after 10 minutes.','Dopo il collegamento, apri il link di associazione nel tuo account Telegram. Scade dopo 10 minuti.')}</p>`}
    ${state.pair && bot.pair_pending ? `<a class="button" href="${safeLink(state.pair.url)}" target="_blank" rel="noopener">${t('Pair my Telegram account','Associa il mio account Telegram')}</a>` : bot.connected && !bot.paired ? `<button data-bot="pair">${t('Create pairing link','Crea il link di associazione')}</button>` : ''}
    ${(bot.uncertain||[]).length?`<h3>${t('Delivery needs verification','Consegne da verificare')}</h3><p>${t('The connection ended before a receipt arrived. Check Telegram before deciding to send again.','La connessione si è interrotta prima della ricevuta. Controlla Telegram prima di decidere se reinviare.')}</p>${bot.uncertain.map(item=>`<article class="memory"><p>${escape(item.method)} · ${new Date(item.created*1000).toLocaleString()}</p><button class="secondary" data-outbox="${item.id}" data-delivery="sent">${t('Verified: received','Verificato: ricevuto')}</button><button class="secondary" data-outbox="${item.id}" data-delivery="retry">${t('Verified: send again','Verificato: reinvia')}</button></article>`).join('')}`:''}<form id="bot-form">${field(bot.connected ? t('Rotate token (after /revoke in BotFather)','Sostituisci il token (dopo /revoke in BotFather)') : t('BotFather token','Token di BotFather'),'token','','password','required autocomplete="off"')}<button>${t('Connect','Collega')}</button></form><small>${escape(bot.status || '')} · ${bot.rejected || 0} ${t('unauthorized updates ignored','messaggi non autorizzati ignorati')}</small></article></div>
    <article class="card"><h2>${t('Your Mac, by message','Il tuo Mac, con un messaggio')}</h2><p>${t('Enable Mac access in Settings on the Mac running OpenDuet. Ask it to open an installed app, read its controls, prepare an action, or send a screenshot. No screen-sharing server is required.','Abilita l’accesso Mac nelle Impostazioni sul Mac dove gira OpenDuet. Puoi chiedere di aprire un’app installata, leggere i controlli, preparare un’azione o inviare uno screenshot. Non serve un server di condivisione schermo.')}</p><code>/apps</code> <code>/screen</code><p>${t('The Mac must be awake and OpenDuet running.','Il Mac deve essere acceso e OpenDuet in esecuzione.')}</p></article>`;
}
export function bind(refresh) {
  document.querySelector('#bot-form').onsubmit = async event => {
    event.preventDefault(); const form = event.currentTarget;
    state.pair = await api('/api/telegram/token',{token:new FormData(form).get('token')}); form.reset(); await refresh();
  };
  document.querySelectorAll('[data-outbox]').forEach(button=>button.onclick=async()=>{await api('/api/telegram/outbox/'+button.dataset.outbox+'/resolve',{verified:true,action:button.dataset.delivery});await refresh();});
  document.querySelectorAll('[data-bot]').forEach(button => button.onclick = async () => {
    if (button.dataset.bot === 'disconnect') { await api('/api/telegram',undefined,'DELETE'); state.pair=null; }
    else if (button.dataset.bot === 'pair') state.pair = await api('/api/telegram/pair',{});
    else { await api('/api/telegram/test',{}); toast(t('Test queued.','Messaggio di prova in coda.')); }
    await refresh();
  });
}
