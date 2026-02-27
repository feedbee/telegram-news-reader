# Telegram News Reader

A Telegram-based content processing and delivery platform that transforms raw Telegram channel messages into structured, digestible information.

## Overview

This platform makes information from Telegram channels **easier and more pleasant to consume** than reading it directly inside Telegram. It addresses common problems with Telegram as an information source:

- Content is fragmented across many channels
- Important messages are mixed with noise
- Hard to get a high-level view of what happened
- Summaries, comparisons, and conclusions are missing

### What This Platform Does

- Reads messages from selected Telegram channels
- Cleans and filters raw content
- Aggregates messages across time and channels
- Produces higher-level representations (summaries, digests, structured views)
- Delivers results in formats more convenient than raw Telegram chats

> **Telegram is the source. This platform is the transformation layer.**

## Project Status

**Current Phase:** Phase 2 - Transform & Web Console

The platform is now functional with basic ingestion, AI-powered summarization, and a web interface:
- **Ingest**: Continuous message retrieval from Telegram to MongoDB.
- **Transform**: On-demand AI summarization using Anthropic's Claude.
- **Web Console**: A premium React dashboard for reading summaries.

## Architecture

The system consists of three logical layers in a single monorepo:

1. **Ingest** *(Implemented)* - Telethon-based service that monitors Telegram channels.
2. **Transform** *(Implemented)* - FastAPI service that processes messages into AI summaries.
3. **Web Console** *(Under Development)* - React SPA with a backend proxy for easy content consumption.

See [`docs/specification.md`](docs/specification.md) for detailed architecture.

## Technical Stack

- **Backend:** Python 3.12 (FastAPI, Telethon, PyMongo)
- **AI Engine:** Anthropic Claude (via API)
- **Frontend:** React + Vite + Tailwind CSS
- **Database:** MongoDB
- **Containerization:** Docker & Docker Compose

## Usage

### Prerequisites

- Docker and Docker Compose installed
- Telegram API credentials (`TELEGRAM_API_ID` and `TELEGRAM_API_HASH`)
- Anthropic API Key (`ANTHROPIC_API_KEY`)

### Quick Start (Full Platform)

1. **Clone and Configure:**
   ```bash
   git clone <repository-url>
   cd telegram-news-reader
   cp .env.example .env
   # Edit .env and add your various API keys
   ```

2. **Launch with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

3. **Access the Console:**
   Open **http://localhost** in your browser.

## Environment Variables

Create a `.env` file in the project root (see `.env.example` for a template):

```bash
# Telegram (Required)
TELEGRAM_API_ID=your_id
TELEGRAM_API_HASH=your_hash

# Anthropic AI (Required for Transform)
ANTHROPIC_API_KEY=sk-ant-xxx

# MongoDB (Default)
MONGODB_URI=mongodb://admin:password@mongodb:27017/telegram-news-reader?authSource=admin

# Application 
CONFIG_PATH=config.json
```

## Development Commands

For local development within the Dev Container:

```bash
# Source the environment variables
source .env

# Start the Ingest service (Realtime)
python ingest/main.py --mode realtime --catch-up

# Start the Transform API
python transform/server.py

# Start the Web Console Backend
python web-console/backend/main.py

# Start the Web Console Frontend (React)
npm run dev --prefix web-console/frontend
```

Or:

```bash
set -a; source .env; set +a; concurrently "make console-backend" "make console-frontend" "make transform-run" "make ingest-run"
```

## Data Migrations

Date migration #001 converts message dates from ISO strings to MongoDB Date.

```bash
# Dry run
docker compose run --rm --no-deps ingest \
  python migrations/001_migrate_message_dates.py --dry-run

# Apply migration
docker compose run --rm --no-deps ingest \
  python migrations/001_migrate_message_dates.py
```


## CI/CD

The project includes a GitHub Actions workflow for building and pushing Docker images to Docker Hub.

### Build Workflow

The workflow (`.github/workflows/build.yml`) supports:
- **Manual triggering** via GitHub UI or CLI
- **Component selection** (build ingest, transform, web-console, or all)
- **Multi-platform builds** (linux/amd64, linux/arm64)
- **Automated tagging** with `latest` and git hash tags

### Setup Required

1. Add GitHub repository secrets:
   - `DOCKERHUB_USERNAME` - Your Docker Hub username
   - `DOCKERHUB_TOKEN` - Docker Hub access token

2. Trigger builds:
   ```bash
   # Via GitHub CLI
   gh workflow run build.yml -f component=all
   gh workflow run build.yml -f component=ingest
   gh workflow run build.yml -f component=transform
   gh workflow run build.yml -f component=web-console

   
   # Via GitHub UI
   # Go to Actions → Build and Push Docker Images → Run workflow
   ```

The workflow is designed to easily support tag-based or branch-based automation. See the walkthrough artifact for examples.


## Documentation

- [`docs/specification.md`](docs/specification.md) - Overall architecture
- [`docs/specification-ingest.md`](docs/specification-ingest.md) - Ingest details
- [`docs/specification-transform.md`](docs/specification-transform.md) - AI Transform details
- [`docs/specification-web-console.md`](docs/specification-web-console.md) - Web UI details
- [`docs/specification-users.md`](docs/specification-users.md) - Users details

## Project Structure

```
telegram-news-reader/
├── docs/                   # Full system specifications
├── ingest/                 # Telegram message listener
├── transform/              # AI processing & API
├── web-console/            # React frontend & proxy
├── session/                # Telegram session tokens (gitignored)
└── docker-compose.yml      # Orchestration
```

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).
