const errorBox = document.getElementById('errorBox');

function normalizePhoneFront(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  if (/[a-zA-Zа-яА-Я]/.test(raw)) return null;
  let digits = raw.replace(/\D/g, '');
  if (digits.length === 10) digits = '7' + digits;
  if (digits.length === 11 && digits.startsWith('8')) digits = '7' + digits.slice(1);
  if (digits.length < 10 || digits.length > 15) return null;
  return '+' + digits;
}

function validateRegisterPayload(payload) {
  const usernameRe = /^[a-zA-Z0-9_.]{3,32}$/;
  if (!usernameRe.test(payload.username)) return 'Username: 3–32 символа, только латиница, цифры, точка или _';
  if (payload.username.startsWith('.') || payload.username.endsWith('.') || payload.username.includes('..')) return 'Username не должен начинаться/заканчиваться точкой или содержать две точки подряд';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(payload.email)) return 'Введите корректный email. Например: name@gmail.com';
  const phone = normalizePhoneFront(payload.phone);
  if (!phone) return 'Введите корректный телефон: +79991234567, 89991234567 или 9991234567';
  payload.phone = phone;
  if (payload.display_name.length < 2) return 'Имя должно быть минимум 2 символа';
  if (payload.password.length < 8) return 'Пароль должен быть минимум 8 символов';
  if (new TextEncoder().encode(payload.password).length > 72) return 'Пароль слишком длинный. Максимум 72 байта';
  return '';
}

const registerForm = document.getElementById('registerForm');
if (registerForm) {
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.textContent = '';
    const fd = new FormData(registerForm);
    const payload = {
      username: String(fd.get('username') || '').trim().toLowerCase(),
      email: String(fd.get('email') || '').trim().toLowerCase(),
      phone: String(fd.get('phone') || '').trim(),
      display_name: String(fd.get('display_name') || '').trim(),
      password: String(fd.get('password') || '')
    };
    const validationError = validateRegisterPayload(payload);
    if (validationError) { errorBox.textContent = validationError; return; }
    try {
      const data = await api('/api/users/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      Auth.save(data.access_token, data.user);
      location.href = 'chat.html';
    } catch (err) { errorBox.textContent = err.message; }
  });
}

const loginForm = document.getElementById('loginForm');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.textContent = '';
    const fd = new FormData(loginForm);
    const payload = { login: String(fd.get('login') || '').trim(), password: String(fd.get('password') || '') };
    if (!payload.login || !payload.password) { errorBox.textContent = 'Введите логин и пароль'; return; }
    try {
      const data = await api('/api/users/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      Auth.save(data.access_token, data.user);
      location.href = 'chat.html';
    } catch (err) { errorBox.textContent = err.message; }
  });
}
