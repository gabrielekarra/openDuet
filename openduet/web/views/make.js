import {api} from '../api.js';
import {state, escape, date, t} from '../state.js';
import {title, empty, safeLink, source, mark} from '../ui.js';
export function render() {
  const artifacts=state.data.artifacts||[];
  return title('Make',t('Finished work, ready for your review.','Risultati pronti da rivedere.'))+(artifacts.length?`<div class="artifact-grid">${artifacts.map(item=>`<article class="card artifact"><div class="file-cover" aria-hidden="true">${escape(item.format.toUpperCase())}</div><small>${date(item.created)}</small><h2>${escape(item.title)}</h2><div class="actions"><button data-preview="${item.id}">${t('Open','Apri')}</button><a class="button secondary" href="/api/artifacts/${item.id}">${t('Download','Scarica')}</a><button class="quiet" data-revise="${item.id}">${t('Ask for changes','Chiedi modifiche')}</button></div></article>`).join('')}</div>`:empty(t('Good work will land here.','Il lavoro pronto arriverà qui.'),t('Ask for a research brief, a financial model, a deck or a dashboard.','Chiedi una ricerca, un modello finanziario, una presentazione o una dashboard.')));
}
function dashboard(spec, item) {
  const known=(state.product.sources||[]).filter(value=>value.task===item.task);
  const citation=value=>{const found=known.find(item=>item.id===value);return found?source(found):value?`<small>${t('Unverified source','Fonte non verificata')}: ${escape(value)}</small>`:'';};
  return `<div class="dashboard"><div class="metric-grid">${(spec.tiles||[]).map(tile=>`<article class="metric"><h3>${escape(tile.label)}</h3><strong>${escape(tile.value)}</strong><p>${escape(tile.trend||'')}</p>${citation(tile.source)}</article>`).join('')}</div>${(spec.tables||[]).map(table=>`<div class="table-scroll"><h3>${escape(table.title||'')}</h3><table><thead><tr>${(table.columns||[]).map(column=>`<th scope="col">${escape(column)}</th>`).join('')}</tr></thead><tbody>${(table.rows||[]).map(row=>`<tr>${row.map(value=>`<td>${escape(value)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`).join('')}${(spec.charts||[]).map(chart=>`<section><h3>${escape(chart.title||'')}</h3><ul class="chart">${(chart.values||[]).map((value,index)=>`<li><span>${escape((chart.labels||[])[index]||index+1)}</span><meter min="0" max="${Math.max(1,...chart.values.map(Number).filter(Number.isFinite))}" value="${Number(value)||0}">${escape(value)}</meter><b>${escape(value)}</b></li>`).join('')}</ul></section>`).join('')}<h3>${t('Where to look','Dove guardare')}</h3><ol>${(spec.where_to_look||[]).map(item=>`<li>${escape(typeof item==='string'?item:item.text||JSON.stringify(item))}</li>`).join('')}</ol><footer>${mark()} <span>OpenDuet</span></footer></div>`;
}
async function preview(ident) {
  const item=await api('/api/make/'+ident);
  const dialog=document.querySelector('#work-preview');
  let content='';
  if(item.format==='dashboard')content=dashboard(item.spec,item);
  else if(item.format==='webapp')content=`<p>${t('Prototype in an isolated sandbox.','Prototipo in un ambiente isolato.')}</p><iframe class="prototype" title="${escape(item.title)}" src="${safeLink(item.preview_url)}" sandbox="allow-scripts" referrerpolicy="no-referrer"></iframe>`;
  else if(item.metadata.slide_images?.length)content=`<div class="slide-grid">${item.metadata.slide_images.map((name,index)=>`<article><img class="slide-image" src="/api/make/${item.id}/slides/${encodeURIComponent(name)}" alt="${t('Slide','Diapositiva')} ${index+1}"><p>${escape(item.metadata.slides[index]?.notes||'')}</p>${item.metadata.slides[index]?.needs_review?`<span class="tag review">${t('Needs review','Da verificare')}</span>`:''}</article>`).join('')}</div>`;
  else if(item.metadata.slides)content=`<div class="slide-grid">${item.metadata.slides.map(slide=>`<article class="slide"><small>${slide.slide} · ${escape(slide.layout)}</small>${slide.needs_review?`<span class="tag review">${t('Needs review','Da verificare')}</span>`:''}<h3>${escape(slide.title)}</h3><p class="prose">${escape(slide.body)}</p><details><summary>${t('Speaker notes','Note del relatore')}</summary><p>${escape(slide.notes)}</p></details></article>`).join('')}</div>`;
  else if(item.spec && typeof item.spec==='object')content=`${item.spec.executive_summary?`<p class="summary">${escape(item.spec.executive_summary)}</p>`:''}${(item.spec.sections||[]).map(section=>`<section><h3>${escape(section.heading||'')}</h3><p class="prose">${escape(section.text||'')}</p></section>`).join('')}<pre>${escape(item.format==='xlsx'?JSON.stringify(item.spec,null,2):'')}</pre>`;
  else content=`<pre class="prose">${escape(item.content||t('Download this file to view it.','Scarica il file per visualizzarlo.'))}</pre>`;
  dialog.innerHTML=`<form method="dialog"><button class="quiet">${t('Close','Chiudi')} ×</button></form><h2>${escape(item.title)}</h2><small>${t('Updated','Aggiornato')} ${date(item.created)} · ${t('Version','Versione')} ${item.version}</small>${item.metadata.note?`<p>${escape(item.metadata.note)}</p>`:''}${content}<div class="actions"><a class="button" href="/api/artifacts/${item.id}">${t('Download','Scarica')}</a><button data-revise="${item.id}" class="secondary">${t('Ask for changes','Chiedi modifiche')}</button></div><h3>${t('Previous versions','Versioni precedenti')}</h3><div class="actions">${item.versions.map(version=>`<button class="secondary" data-preview="${version.id}">${version.version}</button><a href="/api/artifacts/${version.id}">${t('Download','Scarica')} ${version.version}</a>`).join('')}</div>${item.versions.length>1?`<button class="quiet" data-diff="${item.id}" data-other="${item.versions[1].id}">${t('Show changes','Mostra modifiche')}</button><pre id="version-diff"></pre>`:''}`;
  if(!dialog.open)dialog.showModal();
}
export function bind(refresh) {
}
export async function action(target, refresh) {
  if(target.dataset.preview)await preview(target.dataset.preview);
  if(target.dataset.revise){const changes=prompt(t('What should change?','Cosa vuoi modificare?'));if(changes){await api(`/api/artifacts/${target.dataset.revise}/revise`,{changes});await refresh();}}
  if(target.dataset.diff){const result=await api(`/api/make/${target.dataset.diff}/diff/${target.dataset.other}`);document.querySelector('#version-diff').textContent=result.diff;}
}
