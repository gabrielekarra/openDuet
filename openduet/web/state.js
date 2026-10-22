export const state = {view: 'telegram', channel: 'main', data: {}, product: {}, messages: [], pair: null};
export const t = (en, it) => (localStorage.getItem('language') || navigator.language).startsWith('it') ? it : en;
export const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const date = value => new Date(value * 1000).toLocaleString();
