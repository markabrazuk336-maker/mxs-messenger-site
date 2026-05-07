# Как выложить MXS на Render

## Шаг 1. Проверить локально

Запусти `start_mxs.bat`. Если сайт работает на `http://127.0.0.1:8000`, можно выкладывать.

## Шаг 2. Загрузить на GitHub

Создай репозиторий `mxs-messenger` и загрузи туда содержимое папки `MXS_v7_deploy`.

Нужно, чтобы в корне репозитория лежали:

```text
backend/
frontend/
data/
render.yaml
Procfile
run_server.sh
start_mxs.bat
README.md
```

## Шаг 3. Создать сайт на Render

1. Открой Render.
2. New → Web Service.
3. Выбери GitHub-репозиторий.
4. Если Render увидел `render.yaml`, подтверди создание.

Если нужно вручную:

Build Command:

```text
pip install -r backend/requirements.txt
```

Start Command:

```text
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Шаг 4. Проверить ссылку

После деплоя Render даст адрес вида:

```text
https://mxs-messenger.onrender.com
```

Открой его, зарегистрируй 2 аккаунта и проверь чат.
