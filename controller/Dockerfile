# Dev Controller — FastAPI + Vue SPA

# Stage 1: Frontend build (only re-runs when frontend/ files change)
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime
FROM python:3.11-alpine
WORKDIR /app

ARG BUILDER_UID=1000
ARG BUILDER_GID=1000
ARG DOCKER_GID=986

RUN apk add --no-cache docker-cli docker-cli-compose git shadow \
    && addgroup -g $DOCKER_GID docker_host \
    && addgroup -g $BUILDER_GID appgroup 2>/dev/null || true \
    && adduser -D -u $BUILDER_UID -G appgroup -s /bin/sh appuser \
    && addgroup appuser docker_host \
    && apk del shadow

# Python deps (changes rarely)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend assets (from build stage — cached unless frontend/ changed)
COPY --from=frontend-build /build/dist ./frontend/dist/

# Backend code (changes most often — last layer)
COPY backend/ ./backend/

ENV PROJECT_ROOT=/project

EXPOSE 8900

USER appuser
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8900"]
