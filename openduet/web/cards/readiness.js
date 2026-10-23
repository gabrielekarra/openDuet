import {state, escape, t} from '../state.js';
export function readiness(){
  const check=state.product.readiness;if(!check||check.ready)return '';
  const rows=[{done:check.telegram.paired,label:t('Pair your private Telegram account','Associa il tuo account Telegram privato'),view:'telegram'},
    {done:check.model.tested,label:t('Connect and test a work model','Collega e verifica un modello per lavorare'),view:'settings'}];
  return `<section class="card" aria-label="${t('Setup checklist','Configurazione iniziale')}"><h2>${t('Finish setup','Completa la configurazione')}</h2><p>${t('Your bot needs a working model to complete assignments.','Il bot ha bisogno di un modello funzionante per completare le attività.')}</p>${rows.map(row=>`<p>${row.done?'✓':'○'} ${escape(row.label)} ${!row.done&&(check.telegram.paired||row.view==='telegram')?`<button type="button" class="secondary" data-view="${row.view}">${t('Configure','Configura')}</button>`:''}</p>`).join('')}${check.model.error?`<p>${escape(check.model.error)}</p>`:''}</section>`;
}
