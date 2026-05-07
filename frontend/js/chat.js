if (!Auth.token()) location.href = 'login.html';

let me = Auth.user();
let chats = [];
let currentChat = null;
let socket = null;
let typingTimer = null;
let filterText = '';

const body = document.body;
const chatList = document.getElementById('chatList');
const messagesBox = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const chatTitle = document.getElementById('chatTitle');
const chatSub = document.getElementById('chatSub');
const chatAvatar = document.getElementById('chatAvatar');
const myNumber = document.getElementById('myNumber');
const newChatBox = document.getElementById('newChatBox');
const newGroupBox = document.getElementById('newGroupBox');
const chatError = document.getElementById('chatError');
const typingLine = document.getElementById('typingLine');
const imageInput = document.getElementById('imageInput');

function letter(name) { return (name || 'M')[0].toUpperCase(); }
function timeText(dateStr) { return new Date(dateStr).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }); }
function dayText(dateStr) { return new Date(dateStr).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }); }
function avatarHtml(title, url) { return url ? `<img src="${escapeHtml(absoluteUrl(url))}" alt="">` : escapeHtml(letter(title)); }

async function loadMe() {
  try {
    me = await api('/api/users/me', { headers: Auth.headers() });
    Auth.save(Auth.token(), me);
    myNumber.textContent = '@' + me.username + ' · ' + me.phone;
    document.getElementById('profileName').value = me.display_name || '';
    document.getElementById('profileStatus').value = me.status || '';
    document.getElementById('profileBio').value = me.bio || '';
    document.getElementById('profileAvatarUrl').value = me.avatar_url || '';
    document.getElementById('profileNumber').value = me.mxs_number || '';
    document.getElementById('profileAvatar').innerHTML = avatarHtml(me.display_name, me.avatar_url);
  } catch {
    Auth.clear();
    location.href = 'login.html';
  }
}

async function loadChats() {
  chats = await api('/api/chats', { headers: Auth.headers() });
  renderChats();
}

function renderChats() {
  chatList.innerHTML = '';
  const visible = chats.filter(c => (c.title || '').toLowerCase().includes(filterText) || (c.other_user?.username || '').includes(filterText));
  if (!visible.length) {
    chatList.innerHTML = '<div class="empty">Чатов пока нет. Нажми + и добавь пользователя.</div>';
    return;
  }
  for (const chat of visible) {
    const item = document.createElement('div');
    item.className = 'chat-item' + (currentChat?.id === chat.id ? ' active' : '');
    const title = chat.title || 'Чат';
    const sub = chat.last_message || (chat.type === 'group' ? `${chat.members_count} участников` : 'Нет сообщений');
    item.innerHTML = `
      <div class="avatar">${avatarHtml(title, chat.avatar_url)}</div>
      <div class="chat-meta">
        <div class="chat-row"><h4>${escapeHtml(title)}</h4><span>${chat.last_message_at ? dayText(chat.last_message_at) : ''}</span></div>
        <p>${escapeHtml(sub)}</p>
      </div>
      ${chat.unread_count ? `<div class="unread">${chat.unread_count}</div>` : ''}
    `;
    item.onclick = () => openChat(chat);
    chatList.appendChild(item);
  }
}

async function openChat(chat) {
  currentChat = chat;
  body.classList.add('open-chat');
  chatTitle.textContent = chat.title || 'Чат';
  chatSub.textContent = chat.type === 'private' && chat.other_user ? '@' + chat.other_user.username + ' · ' + chat.other_user.phone + ' · ' + (chat.other_user.status || 'offline') : `${chat.members_count} участников`;
  chatAvatar.innerHTML = avatarHtml(chat.title, chat.avatar_url);
  typingLine.textContent = '';
  renderChats();
  await loadMessages(chat.id);
  await loadChats();
}

async function loadMessages(chatId) {
  const messages = await api('/api/messages/' + chatId, { headers: Auth.headers() });
  messagesBox.innerHTML = '';
  if (!messages.length) messagesBox.innerHTML = '<div class="empty">Сообщений пока нет. Напиши первым.</div>';
  messages.forEach(addMessage);
  scrollBottom();
}

function messageBody(msg) {
  if (msg.is_deleted) return `<div class="deleted">Сообщение удалено</div>`;
  if (msg.message_type === 'image') {
    const url = absoluteUrl(msg.file_url);
    return `<img class="chat-image" src="${escapeHtml(url)}" alt="${escapeHtml(msg.file_name || 'image')}" data-url="${escapeHtml(url)}" data-name="${escapeHtml(msg.file_name || 'image')}">`;
  }
  return `<div>${escapeHtml(msg.text)}</div>`;
}

function addMessage(msg) {
  const old = document.getElementById('msg-' + msg.id);
  if (old) old.remove();
  const oldEmpty = messagesBox.querySelector('.empty');
  if (oldEmpty) oldEmpty.remove();
  const div = document.createElement('div');
  div.id = 'msg-' + msg.id;
  div.className = 'bubble ' + (msg.sender_id === me.id ? 'me' : 'other');
  div.innerHTML = `${messageBody(msg)}<div class="time">${timeText(msg.created_at)}${msg.edited_at ? ' · изменено' : ''}</div>${msg.sender_id === me.id && !msg.is_deleted && msg.message_type === 'text' ? '<div class="msg-actions"><button data-edit>изменить</button><button data-del>удалить</button></div>' : ''}`;
  const img = div.querySelector('.chat-image');
  if (img) img.onclick = () => openImage(img.dataset.url, img.dataset.name);
  const edit = div.querySelector('[data-edit]');
  if (edit) edit.onclick = () => editMessage(msg);
  const del = div.querySelector('[data-del]');
  if (del) del.onclick = () => deleteMessage(msg);
  messagesBox.appendChild(div);
  scrollBottom();
}

async function sendMessage() {
  if (!currentChat) return;
  const text = messageInput.value.trim();
  if (!text) return;
  messageInput.value = '';
  try {
    await api('/api/messages/' + currentChat.id, { method: 'POST', headers: Auth.headers(), body: JSON.stringify({ text }) });
    await loadChats();
  } catch (err) { alert(err.message); }
}

async function uploadImage(file) {
  if (!currentChat) return alert('Сначала выбери чат');
  if (!file) return;
  if (file.size > 8 * 1024 * 1024) return alert('Картинка слишком большая. Максимум 8 МБ');
  const ok = ['image/jpeg','image/png','image/webp','image/gif','image/heic','image/heif'].includes(file.type) || /\.(jpg|jpeg|png|webp|gif|heic|heif)$/i.test(file.name);
  if (!ok) return alert('Можно JPG, PNG, WEBP, GIF, HEIC/HEIF');
  const fd = new FormData();
  fd.append('file', file);
  try {
    await api('/api/messages/' + currentChat.id + '/image', { method: 'POST', headers: Auth.headers(false), body: fd });
    await loadChats();
  } catch (err) { alert(err.message); }
}

async function editMessage(msg) {
  const text = prompt('Изменить сообщение:', msg.text || '');
  if (text === null || !text.trim()) return;
  await api('/api/messages/' + msg.id, { method: 'PATCH', headers: Auth.headers(), body: JSON.stringify({ text: text.trim() }) });
}

async function deleteMessage(msg) {
  if (!confirm('Удалить сообщение?')) return;
  await api('/api/messages/' + msg.id, { method: 'DELETE', headers: Auth.headers() });
}

function connectWs() {
  socket = new WebSocket(WS + '?token=' + encodeURIComponent(Auth.token()));
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'message') {
      if (currentChat && data.message.chat_id === currentChat.id) addMessage(data.message);
      loadChats().catch(() => {});
    }
    if (data.type === 'message_updated') {
      if (currentChat && data.message.chat_id === currentChat.id) addMessage(data.message);
      loadChats().catch(() => {});
    }
    if (data.type === 'typing' && currentChat && data.chat_id === currentChat.id && data.user_id !== me.id) {
      typingLine.textContent = 'печатает...';
      clearTimeout(typingTimer);
      typingTimer = setTimeout(() => typingLine.textContent = '', 1400);
    }
  };
  socket.onclose = () => setTimeout(connectWs, 1500);
}

function scrollBottom() { messagesBox.scrollTop = messagesBox.scrollHeight; }
function openImage(url, name) {
  document.getElementById('modalImage').src = url;
  const a = document.getElementById('modalDownload');
  a.href = url;
  a.download = name || 'mxs-image';
  document.getElementById('imageModal').classList.add('show');
}

sendBtn.onclick = sendMessage;
messageInput.addEventListener('keydown', e => {
  if (socket && currentChat) socket.send('typing:' + currentChat.id);
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
document.getElementById('attachBtn').onclick = () => imageInput.click();
imageInput.onchange = () => uploadImage(imageInput.files[0]);
document.getElementById('modalClose').onclick = () => document.getElementById('imageModal').classList.remove('show');
document.getElementById('imageModal').onclick = e => { if (e.target.id === 'imageModal') e.currentTarget.classList.remove('show'); };

document.getElementById('logoutBtn').onclick = async () => { try { await api('/api/users/logout', { method: 'POST', headers: Auth.headers() }); } catch {} Auth.clear(); location.href = 'login.html'; };
document.getElementById('newChatBtn').onclick = () => { newChatBox.classList.toggle('show'); newGroupBox.classList.remove('show'); };
document.getElementById('newGroupBtn').onclick = () => { newGroupBox.classList.toggle('show'); newChatBox.classList.remove('show'); };
document.getElementById('backBtn').onclick = () => body.classList.remove('open-chat');
document.getElementById('chatSearch').oninput = e => { filterText = e.target.value.trim().toLowerCase(); renderChats(); };

document.getElementById('createChatBtn').onclick = async () => {
  chatError.textContent = '';
  const target = document.getElementById('targetInput').value.trim();
  if (!target) return;
  try {
    const chat = await api('/api/chats', { method: 'POST', headers: Auth.headers(), body: JSON.stringify({ target }) });
    document.getElementById('targetInput').value = '';
    newChatBox.classList.remove('show');
    await loadChats(); await openChat(chat);
  } catch (err) { chatError.textContent = err.message; }
};

document.getElementById('createGroupBtn').onclick = async () => {
  const box = document.getElementById('groupError');
  box.textContent = '';
  const title = document.getElementById('groupTitleInput').value.trim();
  const members = document.getElementById('groupMembersInput').value.split(',').map(x => x.trim()).filter(Boolean);
  try {
    const chat = await api('/api/chats/groups', { method: 'POST', headers: Auth.headers(), body: JSON.stringify({ title, members }) });
    newGroupBox.classList.remove('show');
    await loadChats(); await openChat(chat);
  } catch (err) { box.textContent = err.message; }
};

document.getElementById('profileBtn').onclick = () => document.getElementById('profilePanel').classList.toggle('show');
document.getElementById('saveProfileBtn').onclick = async () => {
  const box = document.getElementById('profileError');
  box.style.color = '#fb7185'; box.textContent = '';
  try {
    me = await api('/api/users/me', { method: 'PATCH', headers: Auth.headers(), body: JSON.stringify({
      display_name: document.getElementById('profileName').value.trim(),
      status: document.getElementById('profileStatus').value.trim(),
      bio: document.getElementById('profileBio').value.trim(),
      avatar_url: document.getElementById('profileAvatarUrl').value.trim()
    }) });
    Auth.save(Auth.token(), me);
    box.style.color = '#22c55e'; box.textContent = 'Сохранено';
    await loadMe(); await loadChats();
  } catch (err) { box.textContent = err.message; }
};

(async function init() { await loadMe(); await loadChats(); connectWs(); })();
