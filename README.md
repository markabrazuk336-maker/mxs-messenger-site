# MXS Messenger v7 Deploy Edition

MXS v7 — версия, которую можно запускать локально одной кнопкой и готовить к публикации как сайт.

## Локальный запуск на Windows

1. Открой папку `MXS_v7_deploy`.
2. Запусти `start_mxs.bat` двойным кликом.
3. Открой сайт: `http://127.0.0.1:8000`.

## Где хранятся данные

База данных:

```text
data/mxs.db
```

Картинки:

```text
data/uploads/
```

Не удаляй папку `data`, если хочешь сохранить аккаунты, чаты, сообщения и изображения.

## Запуск на Render

1. Создай репозиторий на GitHub.
2. Загрузи содержимое папки `MXS_v7_deploy` в репозиторий.
3. Открой Render.
4. Создай новый Web Service из этого репозитория.
5. Render может сам прочитать `render.yaml`.

Если Render просит команды вручную:

Build Command:

```text
pip install -r backend/requirements.txt
```

Start Command:

```text
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Environment Variables:

```text
SECRET_KEY=your_long_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=10080
FRONTEND_ORIGIN=*
DATABASE_URL=sqlite:///../data/mxs.db
```

## Важно про базу на хостинге

SQLite подходит для тестового сайта. Для настоящего мессенджера лучше перейти на PostgreSQL, потому что локальные файлы на некоторых бесплатных хостингах могут сбрасываться при пересборке или перезапуске сервиса.
