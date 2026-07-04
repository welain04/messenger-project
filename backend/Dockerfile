# Контекст сборки — корень монорепозитория (Amvera: /workspace).
# Локально: docker build -f backend/Dockerfile -t messenger-backend .
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/scripts ./scripts

EXPOSE 8000

# При наличии ADMIN_PASSWORD — один раз создаёт admin (если ещё нет), затем uvicorn.
# После успешного входа ADMIN_PASSWORD можно удалить из переменных Amvera.
CMD ["sh", "-c", "if [ -n \"${ADMIN_PASSWORD:-}\" ]; then python scripts/create_admin.py --nickname \"${ADMIN_NICKNAME:-admin}\" --email \"${ADMIN_EMAIL:-admin@school.ru}\" || true; fi; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
