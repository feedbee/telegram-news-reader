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

**Current Phase:** Phase 1 - Ingest Component

The project is being developed incrementally. Currently implemented:
- Message ingestion from Telegram
- Basic filtering (deterministic, non-LLM)
- Storing messages in MongoDB

**Future phases** will add:
- Processor component (summaries, embeddings, clustering, analytics)
- Delivery component (web, Telegram bot, mobile app)
- Semantic and meaning-based search

## Architecture

The system consists of three logical components in a single monorepo:

1. **Ingest** *(implemented)* - Loads messages from Telegram, applies filtering, stores in database
2. **Processor** *(planned)* - Asynchronous processing, summaries, embeddings, analytics
3. **Delivery** *(planned)* - Delivers processed content via various channels

See [`docs/specification.md`](docs/specification.md) for detailed architecture.

## Technical Stack

- **Language:** Python 3.12
- **Telegram Client:** [Telethon](https://docs.telethon.dev/)
- **Database:** MongoDB
- **Containerization:** Docker (development and production)
- **Development Environment:** Dev Containers (VS Code/Cursor)

## Usage

### Prerequisites

- Docker and Docker Compose installed
- VS Code or Cursor IDE (recommended for Dev Containers)
- Telegram API credentials (`TELEGRAM_API_ID` and `TELEGRAM_API_HASH`)

### Getting Telegram API Credentials

To interact with the Telegram API, you need to obtain an `API_ID` and `API_HASH`:

1.  Log in to the [Telegram Core](https://my.telegram.org/) website using your phone number.
2.  Go to **API development tools**.
3.  If this is your first time, you will be prompted to create a new application. Fill in the required details (App title and Short name can be anything).
4.  Once created, you will see your `App api_id` and `App api_hash`.
5.  Copy these values and paste them into your `.env` file as `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`.

### Quick Start with Dev Containers (Recommended)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd telegram-news-reader
   ```

2. **Open in VS Code/Cursor:**
   ```bash
   code .
   ```

3. **Reopen in Container:**
   - Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
   - Select `Dev Containers: Reopen in Container`
   - Wait for the container to build (first time only)

4. **Install dependencies:**
   ```bash
   pip install -r ingest/requirements.txt
   ```

5. **Configure Telegram credentials:**
   ```bash
   # Create .env from example
   cp .env.example .env
   # Edit .env and add your Telegram API credentials
   ```

6. **Run the ingest component (from root):**
   ```bash
   python ingest/main.py --mode realtime
   ```

- Python 3.12 with all dependencies pre-installed
- MongoDB 7 running automatically
- VS Code extension for Python development (ms-python.python)
- Pre-configured environment variables

### Manual Setup (Without Dev Containers)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd telegram-news-reader
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r ingest/requirements.txt
   ```

4. **Start MongoDB:**
   ```bash
   docker run -d \
     --name telegram-news-mongodb \
     -p 27017:27017 \
     -e MONGO_INITDB_ROOT_USERNAME=admin \
     -e MONGO_INITDB_ROOT_PASSWORD=password \
     -e MONGO_INITDB_DATABASE=telegram-news-reader \
     mongo:7
   ```

5. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

6. **Run the application (from root):**
   ```bash
   python ingest/main.py --mode realtime
   ```

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Telegram API Credentials (required)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

# MongoDB Connection (default for Dev Container)
MONGODB_URI=mongodb://admin:password@mongodb:27017/telegram-news-reader?authSource=admin

# Application Paths (optional, defaults shown)
# CONFIG_PATH=config.json
# SESSION_FILE=anon.session
```

### Development Commands

Inside the Dev Container or virtual environment:

```bash
# Run the ingest component
python ingest/main.py --mode realtime

# Run tests (with test dependencies installed)
cd ingest
pip install -r requirements-test.txt
PYTHONPATH=. pytest tests/
```

### MongoDB Access

**From Dev Container:**
- MongoDB is available at `mongodb:27017`
- Connection string: `mongodb://admin:password@mongodb:27017/telegram-news-reader?authSource=admin`

**From Host Machine:**
- MongoDB is forwarded to `localhost:27017`
- Use any MongoDB client (MongoDB Compass, mongosh, etc.)

### Session Management

Telegram authentication creates a session file at `session/anon.session`. This file:
- Persists your authenticated state
- Must be preserved across container restarts
- Should **not** be committed to version control (already in `.gitignore`)

## Documentation

- [`docs/specification.md`](docs/specification.md) - Overall architecture and design
- [`docs/specification-ingest.md`](docs/specification-ingest.md) - Ingest component specification
- [`docs/devcontainers.md`](docs/devcontainers.md) - Dev Containers setup guide

## Project Structure

```
telegram-news-reader/
├── .devcontainer/          # Dev Container configuration
├── docs/                   # Documentation
├── ingest/                 # Main Python service (Ingest component)
├── poc/                    # Proof of concept scripts
├── session/                # Telegram session files (gitignored)
└── README.md              # This file
```

## Contributing

This is currently a single-tenant system in active development. Contributions and feedback are welcome as the project evolves.

## License

[Add your license here]
