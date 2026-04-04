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

RUN apk add --no-cache docker-cli docker-cli-compose git

# Python deps (changes rarely)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend assets (from build stage — cached unless frontend/ changed)
COPY --from=frontend-build /build/dist ./frontend/dist/

# Backend code (changes most often — last layer)
COPY backend/ ./backend/

ENV PROJECT_ROOT=/project

EXPOSE 8900

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8900"]
