# Переход на PostgreSQL — план и чек-лист (Этап 6B)

Документ описывает, что уже сделано в рамках подготовки (Этап 6A) и что остаётся
сделать при фактическом переезде на PostgreSQL (Этап 6B).

## Что уже сделано (Этап 6A)

- **Единый источник URL подключения.** `DATABASE_URL` в `app/config.py`
  (по умолчанию пусто -> SQLite по `DATABASE_PATH`/`backend/messenger.db`).
  Хелпер `app/db.py::database_url()` отдаёт URL для Alembic/SQLAlchemy.
- **Определение диалекта.** `app/dialect.py`: `current_dialect()`, `is_sqlite()`,
  `is_postgres()`, плюс хелперы `like_operator()`, `to_db_bool()`, `from_db_bool()`.
- **Alembic как механизм миграций.** `backend/alembic.ini`, `backend/alembic/env.py`,
  baseline `backend/alembic/versions/0001_initial.py` (снимок `schema.sql`).
  `db.init_db()` теперь вызывает `alembic upgrade head`.
- **`schema.sql` заморожен как снимок v1.** Новые изменения схемы оформляются
  НОВЫМИ ревизиями Alembic, а не правкой `schema.sql`.
- **Слой данных изолирован** в `app/db.py` + `app/storage.py` (роутеры не пишут SQL).

## Как устроены миграции сейчас

```bash
cd backend
# применить миграции (то же делает init_db при старте приложения)
alembic upgrade head
# создать новую ревизию (пишем SQL вручную через op.execute / exec_driver_sql)
alembic revision -m "add table xyz"
```

`env.py` берёт URL из `DATABASE_URL` приложения; для ручного запуска можно
переопределить через переменную окружения `DATABASE_URL`.

## Чек-лист фактического переезда (6B)

### 1. Инфраструктура
- [ ] Поднять PostgreSQL (локально через Docker или managed: Neon/Supabase/RDS).
- [ ] Установить драйвер: `psycopg[binary]` (добавить в `requirements.txt`).
- [ ] Задать `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/messenger`.

### 2. Baseline-схема под Postgres
- [ ] Создать PG-вариант baseline-миграции (текущий 0001 — только SQLite).
      Перевести типы и конструкции:
  - `TEXT` под UUID -> `uuid` (или оставить `text`, генерируя UUID в Python).
  - `TEXT` под время -> `timestamptz`.
  - `INTEGER` 0/1 под boolean -> `boolean`.
  - `TEXT + CHECK (... IN ...)` под enum -> оставить как `text + CHECK` или ввести `ENUM`-типы.
  - `COLLATE NOCASE` -> `citext` (расширение) ИЛИ функциональные индексы `lower(col)`.
  - partial-индексы (`... WHERE ... IS NULL`) — поддерживаются в PG как есть.

### 3. Слой доступа к данным (`app/storage.py`, `app/db.py`)
- [ ] **Плейсхолдеры.** SQLite использует `?` (qmart), psycopg — `%s`.
      Это основной портируемый блокер: ввести единый стиль (например, перейти на
      именованные параметры SQLAlchemy `text()` или адаптировать `db.execute/query_*`).
- [ ] **Регистронезависимый поиск.** Уже через `dialect.like_operator()`
      (`LIKE`/`ILIKE`); проверить `search_users`.
- [ ] **`ORDER BY ... COLLATE NOCASE`** в `search_users` — заменить на
      `lower(nickname)` / `citext`.
- [ ] **Boolean.** Везде, где пишутся `0/1` и читается `bool(...)`,
      перейти на `dialect.to_db_bool()` / `from_db_bool()`.
- [ ] **`PRAGMA foreign_keys`** в `reset_storage` — уже под `dialect.is_sqlite()`.
- [ ] **`sqlite3.Row`** в сигнатурах list-функций (`list_active_sessions`,
      `list_audit_logs`, `list_role_upgrade_requests`) — заменить на нейтральный тип.

### 4. Подключение и конкурентность
- [ ] Заменить единый `sqlite3`-коннект + `RLock` (`app/db.py`) на пул соединений
      SQLAlchemy/psycopg.
- [ ] Рассмотреть переход sync -> async (asyncpg) для эндпоинтов под нагрузкой.

### 5. Сопутствующее (по необходимости)
- [ ] Перенести rate-limit / brute-force из памяти процесса в Redis (для нескольких воркеров).
- [ ] Перенос данных из SQLite (если к моменту переезда уже есть прод-данные).

## Триггеры начинать 6B
- Готовится боевой деплой с реальными пользователями.
- Нужно больше одного воркера/инстанса (in-memory rate-limit и единый коннект не масштабируются).
- Появляется конкурентная запись и упор в single-writer SQLite.
- Нужен WebSocket с горизонтальным масштабированием.
