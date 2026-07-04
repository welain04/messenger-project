# Контекст сборки — корень монорепозитория (Amvera: /workspace).
# Локально: docker build -f frontend/Dockerfile --build-arg VITE_API_BASE_URL=... -t messenger-frontend .
FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
# Явно — на случай если .dockerignore отфильтровал .env.*
COPY frontend/.env.production .env.production

# Optional build-arg; без значения по умолчанию — иначе пустой ARG блокирует .env.production в Vite.
ARG VITE_API_BASE_URL
RUN set -e; \
    if [ "${VITE_API_BASE_URL:-}" != "" ]; then \
      export VITE_API_BASE_URL="$VITE_API_BASE_URL"; \
      echo "build: VITE_API_BASE_URL from build-arg=$VITE_API_BASE_URL"; \
    elif [ -f .env.production ]; then \
      unset VITE_API_BASE_URL 2>/dev/null || true; \
      set -a && . ./.env.production && set +a; \
      echo "build: VITE_API_BASE_URL from .env.production=$VITE_API_BASE_URL"; \
    else \
      echo "build: нужен frontend/.env.production или --build-arg VITE_API_BASE_URL" >&2; \
      ls -la; exit 1; \
    fi; \
    test -n "$VITE_API_BASE_URL" || (echo "build: VITE_API_BASE_URL пуст" >&2 && exit 1); \
    npm run build; \
    grep -rq "amvera.io" dist/assets/ || (echo "build: URL backend не попал в бандл" >&2 && exit 1); \
    echo "build: OK — API URL вшит в dist/"

FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
