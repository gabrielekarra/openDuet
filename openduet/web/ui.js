import {glasses} from './brand/mark.js';
import {escape, t} from './state.js';
export const mark = (classes='') => `<span class="glasses ${classes}" aria-hidden="true">${glasses}</span>`;
export const empty = (title, description='') => `<div class="empty">${mark()}<h2>${escape(title)}</h2><p>${escape(description)}</p></div>`;
export const title = (name, description='') => `<div class="page-title"><h1>${escape(name)}</h1><p>${escape(description)}</p></div>`;
export const button = (name, attributes='') => `<button type="button" ${attributes}>${name}</button>`;
export function toast(message) {
  const node = document.querySelector('#toast'); node.textContent = message; node.hidden = false;
  setTimeout(() => node.hidden = true, 7000);
}
export const safeLink = value => { try { const url = new URL(value); return ['http:','https:'].includes(url.protocol) ? escape(url.href) : '#'; } catch { return '#'; } };
export const source = item => `<a class="source" href="${safeLink(item.url)}" target="_blank" rel="noopener noreferrer">${escape(item.label || item.tool || item.id)}</a>`;
export function field(label, name, value='', type='text', extra='') {
  return `<label>${escape(label)}<input name="${escape(name)}" type="${type}" value="${escape(value)}" ${extra}></label>`;
}
export const saved = () => toast(t('Saved.', 'Salvato.'));
