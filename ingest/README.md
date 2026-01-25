# Ingest Component - Docker Guide

This guide covers how to build, run, and deploy the Ingest component using Docker.

## 1. Local Development & Testing

### Build the Image
From the **project root** folder, run:
```bash
docker build -t telegram-news-reader-ingest -f ingest/Dockerfile ingest/
```

### Run the Container
To run the container locally while connecting to a MongoDB instance on a specific network:

```bash
docker run --rm -it \
  --network telegram-news-network \
  --env-file .env \
  -v $(pwd)/session:/app/session \
  -e MONGODB_URI="mongodb://admin:password@mongodb:27017/telegram-news-reader?authSource=admin" \
  -e SESSION_FILE=session/acc2.anon.session \
  telegram-news-reader-ingest
```

**Parameters explained:**
- `--network`: Connects the container to an existing Docker network (where your MongoDB is likely running).
- `--env-file`: Loads environment variables (like `TELEGRAM_API_ID`).
- `-v`: Mounts your local `session` folder into the container to persist Telegram authentication.
- `-e MONGODB_URI`: Overrides the database URI to use the container name (`mongodb`) instead of `localhost`.

---

## 2. Production Build (Multi-platform DockerHub)

For production, we use multi-stage builds and `buildx` to support both `amd64` (servers) and `arm64` (Graviton/M1/M2 chips).

### Authenticate with DockerHub
```bash
docker login
```

### Build and Push
This command builds for both platforms and pushes a single manifest to DockerHub.

```bash
# Set variables
DOCKER_USER=your_username
REPO_NAME=telegram-news-reader-ingest
GIT_HASH=$(git rev-parse --short HEAD)
REPO_URL=${DOCKER_USER}/${REPO_NAME}

# Multi-platform build & push
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t $REPO_URL:latest \
  -t $REPO_URL:$GIT_HASH \
  -f ingest/Dockerfile \
  ingest/ \
  --push
```

## Security Design
The `Dockerfile` is optimized for production:
- **Multi-stage build**: Separates build tools from the final runtime image.
- **Non-root user**: The container runs under `appuser` for improved security.
- **Venv integration**: Uses a virtual environment to keep the system Python clean.
