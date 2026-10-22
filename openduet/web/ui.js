import {glasses} from './brand/mark.js';
import {escape, t} from './state.js';
let markNumber=0;
export function mark(classes=''){
  const id='duet-mark-'+markNumber++,lens=id+'-lenses',mask=id+'-mask';
  const traced=glasses.match(/<g id="mark">[\s\S]*<\/g>/)[0].replace('id="mark"','id="'+id+'"');
  const circles='<circle cx="267.5" cy="275.5" r="142"/><circle cx="756.5" cy="275.5" r="142"/>';
  return `<span class="glasses ${classes}" aria-hidden="true"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 512" fill="currentColor"><defs>${traced}<clipPath id="${lens}">${circles}</clipPath><mask id="${mask}" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="512"><rect width="1024" height="512" fill="white"/><g fill="black">${circles}</g></mask></defs><use href="#${id}" mask="url(#${mask})"/><g clip-path="url(#${lens})"><g class="pupils"><g clip-path="url(#${lens})"><use href="#${id}"/></g></g></g></svg></span>`;
}
export const empty = (title, description='') => `<div class="empty">${mark()}<h2>${escape(title)}</h2><p>${escape(description)}</p></div>`;
export const title = (name, description='') => `<div class="page-title"><h1>${escape(name)}</h1><p>${escape(description)}</p></div>`;
export const button = (name, attributes='') => `<button type="button" ${attributes}>${name}</button>`;
export function toast(message) {
  const node = document.querySelector('#toast'); node.textContent = message; node.hidden = false;
  setTimeout(() => node.hidden = true, 7000);
}
export const safeLink = value => { try { const url = new URL(value); return ['http:','https:'].includes(url.protocol) ? escape(url.href) : '#'; } catch { return '#'; } };
export const source = item => item.url?`<a class="source" href="${safeLink(item.url)}" target="_blank" rel="noopener noreferrer">${escape(item.label || item.tool || item.id)}</a>`:`<details class="source-info"><summary class="source">${escape(item.label||item.tool||item.id)}</summary><pre>${escape(item.excerpt||item.id)}</pre></details>`;
export function field(label, name, value='', type='text', extra='') {
  return `<label>${escape(label)}<input name="${escape(name)}" type="${type}" value="${escape(value)}" ${extra}></label>`;
}
export const saved = () => toast(t('Saved.', 'Salvato.'));
