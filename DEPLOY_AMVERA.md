# Деплой Online School Messenger на Amvera

Монорепозиторий разворачивается как **два независимых приложения**: backend (FastAPI) и frontend (React/Vite). Общий `docker-compose.yml` не используется.

## Общая схема

1. Создайте **два проекта** в Amvera: один для API, один для SPA.
2. Привяжите оба проекта к **одному Git-репозиторию** (GitHub / GitLab / репозиторий Amvera).
3. Укажите **корневую папку** (path / root directory) для каждого проекта:
   - backend → `backend`
   - frontend → `frontend`
4. В каждой папке уже лежат `Dockerfile`, `.dockerignore` и `amvera.yml`.

Если в интерфейсе Amvera нет поля «корневая папка», создайте отдельные репозитории Amvera и копируйте содержимое соответствующей подпапки, либо положите в корень репозитория `amvera.yml` с путём к Dockerfile:

```yaml
# только для backend-проекта, если корень репозитория — корень монорепо
build:
  dockerfile: backend/Dockerfile
run:
  containerPort: 8000
  persistenceMount: /data
```

---

## Backend

### Файлы

| Файл | Назначение |
|------|------------|
| `backend/Dockerfile` | Образ Python 3.12, запуск `uvicorn app.main:app` |
| `backend/.dockerignore` | Исключает `.venv`, `.env`, SQLite, uploads из контекста сборки |
| `backend/amvera.yml` | Порт 8000, persistent storage в `/data` |

### Запуск

Контейнер стартует командой:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

- `host=0.0.0.0` — обязательно для Amvera (не `127.0.0.1`).
- `PORT` — переменная, которую задаёт Amvera; если её нет, используется `8000`.
- Режим `--reload` **не** используется.

### Persistent storage (SQLite)

Файл SQLite нужно хранить в постоянном томе Amvera (`/data` по умолчанию, см. `persistenceMount` в `amvera.yml`).

В переменных окружения backend-проекта задайте:

```env
DATABASE_PATH=/data/messenger.db
```

При старте приложение автоматически применяет миграции Alembic (`db.init_db()`). Ручной запуск из каталога `backend` (локально или в shell контейнера):

```bash
alembic upgrade head
```

URL БД берётся из `DATABASE_URL` или `DATABASE_PATH` через существующий `config.py` — логику менять не нужно.

### Переменные окружения (backend)

Задаются во вкладке **«Переменные»** проекта Amvera (не коммитьте секреты в Git). Полный список — в `backend/.env.example`.

**Обязательно для production** (`APP_ENV=production`):

| Переменная | Пример / описание |
|------------|-------------------|
| `APP_ENV` | `production` |
| `JWT_SECRET` | Длинный случайный ключ: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ENABLE_TEST_ENDPOINTS` | `false` |
| `CORS_ORIGINS` | Публичный URL фронтенда, напр. `https://your-frontend.amvera.io` |
| `FRONTEND_BASE_URL` | Тот же URL фронтенда (ссылки в письмах) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` | SMTP для verify/reset |
| `STORAGE_PROVIDER` | `yandex` (в production `local` запрещён) |
| `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Yandex Object Storage |
| `DATABASE_PATH` | `/data/messenger.db` |
| `TRUST_PROXY_HEADERS` | `true` (если Amvera/прокси передаёт `X-Forwarded-For`) |

**Рекомендуется:**

```env
PYTHONUNBUFFERED=1
```

### Проверка backend: `GET /health`

Эндпоинт уже реализован, **авторизация не требуется**.

```bash
curl -i https://<ваш-backend-домен>/health
```

Ожидаемый ответ:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"status":"ok"}
```

Локально (Docker):

```bash
# из корня монорепозитория (контекст сборки — корень, как на Amvera)
docker build -f backend/Dockerfile -t messenger-backend .
docker run --rm -p 8000:8000 -e APP_ENV=development messenger-backend
curl http://localhost:8000/health
```

### Первый администратор

После деплоя (один раз, с заданными production ENV):

```bash
python scripts/create_admin.py --nickname admin --email admin@school.ru
```

---

## Frontend

### Файлы

| Файл | Назначение |
|------|------------|
| `frontend/Dockerfile` | Multi-stage: `npm ci` → `npm run build` → nginx отдаёт `dist/` |
| `frontend/nginx.conf` | SPA fallback (`try_files` для React Router) |
| `frontend/.dockerignore` | Исключает `node_modules`, `dist`, `.env*` |
| `frontend/amvera.yml` | HTTP на порту 80 (nginx) |

### `VITE_API_BASE_URL` — только на этапе сборки

Значение вшивается в бандл при `npm run build`. Runtime-переменные для API **не** используются (см. `frontend/src/api/client.ts`).

**Формат:** публичный URL backend **с префиксом `/api/v1`**, без завершающего `/`:

```text
https://your-backend.amvera.io/api/v1
```

#### Как передать при сборке Docker

1. **Локально:**

   ```bash
   # из корня монорепозитория
   docker build -f frontend/Dockerfile \
     --build-arg VITE_API_BASE_URL=https://your-backend.amvera.io/api/v1 \
     -t messenger-frontend .
   docker run --rm -p 8080:80 messenger-frontend
   ```

2. **На Amvera:** переменные из вкладки «Переменные» **недоступны во время сборки** Docker-образа. Передайте build-arg одним из способов:
   - параметры сборки Docker в настройках проекта (если доступны в UI);
   - CI/CD шаг `docker build --build-arg VITE_API_BASE_URL=...` перед push;
   - временно задайте ARG при сборке в Amvera Code (не коммитьте секреты).

Без `VITE_API_BASE_URL` сборка frontend-образа завершится ошибкой (намеренная проверка в `Dockerfile`).

#### Альтернатива без Docker (нативное окружение Amvera Node Browser)

Можно использовать `meta.environment: node` / `toolchain.name: browser` и `artifacts: "dist/*": /` — тогда перед push создайте в каталоге `frontend` файл `.env.production` с `VITE_API_BASE_URL=...` (файл в `.gitignore`, добавляется только в репозиторий Amvera). Текущий репозиторий настроен на **Docker multi-stage**, как в требованиях.

### Переменные окружения (frontend)

Для Docker-сборки frontend **runtime ENV не нужны** (статический nginx). Единственный обязательный параметр — `VITE_API_BASE_URL` на этапе **build**.

---

## Порядок деплоя

1. Задеплойте **backend**, проверьте `GET /health`.
2. Скопируйте публичный URL backend.
3. Соберите **frontend** с `VITE_API_BASE_URL=https://<backend-host>/api/v1`.
4. Задеплойте frontend, откройте SPA в браузере.
5. Убедитесь, что в backend `CORS_ORIGINS` и `FRONTEND_BASE_URL` указывают на URL frontend.

---

## Stage / Prod

Создайте два проекта Amvera (backend + frontend) на ветки `stage` / `prod` или используйте отдельные переменные окружения — см. [документацию Amvera](https://docs.amvera.ru/general/examples/miniappex.html).

---

## Полезные ссылки

- [Docker на Amvera](https://docs.amvera.ru/applications/configuration/docker.html)
- [Persistent storage / SQLite](https://docs.amvera.ru/general/examples/miniappex.html)
- `backend/.env.example` — все ENV backend
- `frontend/.env.example` — описание `VITE_API_BASE_URL`
