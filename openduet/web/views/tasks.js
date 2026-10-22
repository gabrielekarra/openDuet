import {state, escape, date, t} from '../state.js';
import {title, empty} from '../ui.js';
import {approval} from '../cards/approval.js';
export function render() {
  const tasks = state.data.tasks || [];
  const groups = [[t('Needs you','Richiedono attenzione'),['awaiting_approval','blocked','interrupted','failed']], [t('In progress','In corso'),['queued','running']], [t('Ready for review','Da rivedere'),['ready']], [t('Done','Concluse'),['completed','cancelled']]];
  return title(t('Tasks','Attività'),t('Review the work. You decide when it is complete.','Rivedi il lavoro. Decidi tu quando è completo.')) +
    `<div class="approval-grid">${(state.product.approvals || []).map(approval).join('')}</div>` +
    (tasks.length ? groups.map(([name,statuses]) => `<section><h2>${name}</h2><div class="task-list">${tasks.filter(task=>statuses.includes(task.status)).map(task=>`<article class="card"><div class="split"><span class="tag">${escape(task.status)}</span><small>${date(task.updated)}</small></div><h3>${escape(task.request.slice(0,240))}</h3>${task.error?`<p>${escape(task.error)}</p>`:''}<div class="actions">${task.status==='ready'?`<button data-task="complete" data-id="${task.id}">${t('Mark complete','Segna come completata')}</button>`:''}${['failed','interrupted','blocked'].includes(task.status)?`<button data-task="resume" data-id="${task.id}">${t('Resume after review','Riprendi dopo la verifica')}</button>`:''}${['queued','running','awaiting_approval'].includes(task.status)?`<button class="secondary" data-task="cancel" data-id="${task.id}">${t('Stop','Ferma')}</button>`:''}<button class="quiet" data-task-chat="${task.channel}">${t('Conversation','Conversazione')}</button></div></article>`).join('') || `<p class="muted">${t('Nothing here.','Nessuna attività.')}</p>`}</div></section>`).join('') : empty(t('A little room for the next task.','Spazio per la prossima attività.'),t('Send your first task on Telegram or in Chat.','Invia la prima richiesta su Telegram o nella Chat.')));
}
export function bind() {}
