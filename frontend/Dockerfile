# Контекст сборки — корень монорепозитория (Amvera: /workspace).
# Локально: docker build -f frontend/Dockerfile --build-arg VITE_API_BASE_URL=... -t messenger-frontend .
FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

# Vite подставляет VITE_* только на этапе сборки.
# Источник URL: --build-arg VITE_API_BASE_URL=... или frontend/.env.production в репозитории.
ARG VITE_API_BASE_URL=
RUN if [ -n "$VITE_API_BASE_URL" ]; then export VITE_API_BASE_URL="$VITE_API_BASE_URL"; \
    elif ! grep -qE '^VITE_API_BASE_URL=.+' .env.production 2>/dev/null; then \
      echo "VITE_API_BASE_URL: задайте --build-arg или frontend/.env.production" >&2; exit 1; \
    fi && npm run build

FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
