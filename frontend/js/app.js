const API = window.location.origin;
const WS = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws';

const Auth = {
  token() { return localStorage.getItem('mxs_token'); },
  user() {
    try { return JSON.parse(localStorage.getItem('mxs_user') || 'null'); }
    catch { return null; }
  },
  save(token, user) {
    localStorage.setItem('mxs_token', token);
    localStorage.setItem('mxs_user', JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem('mxs_token');
    localStorage.removeItem('mxs_user');
  },
  headers(json = true) {
    const h = { 'Authorization': 'Bearer ' + Auth.token() };
    if (json) h['Content-Type'] = 'application/json';
    return h;
  }
};

function prettyError(data) {
  if (!data) return 'Сервер не ответил';
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map(x => {
      const where = Array.isArray(x.loc) ? x.loc.filter(v => v !== 'body').join('.') : '';
      return where ? `${where}: ${x.msg}` : x.msg;
    }).join('\n');
  }
  return JSON.stringify(data);
}

async function api(path, options = {}) {
  const res = await fetch(API + path, options);
  let data = null;
  try { data = await res.json(); } catch {}
  if (!res.ok) throw new Error(prettyError(data));
  return data;
}

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
}

function absoluteUrl(url) {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  return API + url;
}
