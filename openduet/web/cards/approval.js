import {date, escape, t} from '../state.js';
export function approval(card) {
  const payload = card.payload || JSON.parse(card.arguments || '{}');
  const important = ['to','cc','subject','body','text','merchant','amount','currency','payee','document','items','old_time','new_time','bundle_id','action','element'];
  const fields = important.filter(key => payload[key] !== undefined);
  const expired = card.expires && card.expires < Date.now()/1000;
  return `<article class="card approval" aria-label="${escape(t('Approval', 'Approvazione'))}"><div class="split"><span class="tag">${escape(card.kind || 'action')}</span><small>${escape(expired ? t('Expired','Scaduta') : date(card.expires || card.created + 86400))}</small></div>
    <h2>${escape(card.name)}</h2><dl>${fields.map(key => `<dt>${escape(key)}</dt><dd>${escape(typeof payload[key] === 'object' ? JSON.stringify(payload[key]) : payload[key])}</dd>`).join('')}</dl>
    <details><summary>${t('Exact payload', 'Dati esatti dell’azione')}</summary><pre>${escape(JSON.stringify(payload,null,2))}</pre></details>
    <div class="actions">${card.status === 'uncertain' ? `<p>${t('Verify the outcome at the service before continuing.', 'Verifica l’esito nel servizio prima di continuare.')}</p><button data-resolve="${card.id}" data-happened="yes">${t('It happened','È avvenuta')}</button><button data-resolve="${card.id}" data-happened="no">${t('It did not happen','Non è avvenuta')}</button>` : `<button data-review="approve" data-call="${card.id}" ${expired?'disabled':''}>${t('Approve','Approva')}</button><button data-edit-call="${card.id}" class="secondary">${t('Edit','Modifica')}</button><button data-review="defer" data-call="${card.id}" class="secondary">${t('Not now','Non ora')}</button><button data-review="reject" data-call="${card.id}" class="quiet">${t('Reject','Rifiuta')}</button>`}</div></article>`;
}
