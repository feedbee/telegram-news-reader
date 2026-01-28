# ----------------------
# Builder
# ----------------------
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt


# ----------------------
# Tester
# ----------------------
FROM builder AS tester

COPY requirements-test.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements-test.txt

COPY . .

# Run tests. If this fails, the build fails.
# PYTHONPATH=. is needed because of how imports are structured relative to root
RUN . /venv/bin/activate && PYTHONPATH=. pytest tests/


# ----------------------
# Runtime
# ----------------------
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH"

RUN useradd -m -s /bin/bash appuser

COPY --from=builder /venv /venv
COPY --chown=appuser:appuser . .

USER appuser

# Expose API port
EXPOSE 8000

# Default command: Run the API Server
CMD ["python", "server.py"]
