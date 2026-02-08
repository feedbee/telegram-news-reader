
# Stage 1: Build Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app

# Copy backend code
COPY backend/*.py ./
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend build from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./static

# Environment variables
ENV TRANSFORM_URL=http://transform:8000
ENV CONFIG_PATH=/app/config.json
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
