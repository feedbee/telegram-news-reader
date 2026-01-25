# Telegram News Reader

## Project Overview

This project is a **Telegram-based content processing and delivery platform**.

Its main purpose is to make information from Telegram channels **easier and more pleasant to consume** than reading it directly inside Telegram.

Telegram is a great source of information, but:

* content is fragmented across many channels
* important messages are mixed with noise
* it is hard to get a high-level view (what happened today / this week)
* summaries, comparisons, and conclusions are missing

This platform solves these problems by **transforming, aggregating, and reformatting** Telegram content.

### What This Platform Does

At a high level, the platform:

* Reads messages from selected Telegram channels
* Cleans and filters raw content
* Aggregates messages across time and channels
* Produces higher-level representations:
  * summaries
  * digests
  * structured views
  * extracted insights
* Delivers the result in formats that are **more convenient than raw Telegram chats**

In other words, this is **not just a reader**, but a system that **adds value on top of Telegram content**.

### Core Idea

> **Telegram is the source.
> This platform is the transformation layer.**

Instead of reading hundreds of raw messages, the user consumes:

* a short summary
* a daily or weekly digest
* a structured overview of topics
* aggregated conclusions

### Future Potential Extension

In the future, the platform may provide **semantic and meaning-based search** over the stored Telegram messages.

This includes:

* searching by **meaning**, not exact words
* finding relevant messages across multiple channels
* answering questions like:
  * "What was recommended most often last year?"
  * "What were people discussing about topic X?"
  * "Show similar discussions to this message"

This functionality will be based on:

* stored message archives
* semantic embeddings
* higher-level aggregation and analysis

**Important:**
Semantic and meaning-based search is **explicitly out of scope for the initial implementation** and will be added incrementally at a later stage.

### Incremental Development Strategy

The platform is developed **step by step**, starting from the simplest useful features.

### Phase 1 (current focus)

* Message ingestion from Telegram
* Basic filtering (deterministic, non-LLM)
* Storing messages in the database

This is the foundation: reliable, lossless data collection from Telegram channels.


## Key Principle

The goal is **not to replace Telegram**, but to:

* reduce noise
* save time
* improve understanding

Telegram remains the raw data source. This platform becomes the **thinking and formatting layer on top of it**.


## Overall Architecture

This project is a **Telegram-based information ingestion and delivery platform**.
All components live in a **single monorepo**, each in its own folder.

At the current stage, **only the Ingest component is implemented**.
Transform and Emit are defined architecturally but are **out of scope for now**.

**Tenant model:** This is a **single-tenant system**. One Telegram account is used for listening to channels. In the future, multiple delivery recipients may be supported, but the Telegram listener will always use a single set of credentials.

The system consists of three logical components:

1. **Ingest**
   Responsible for loading messages from Telegram channels and groups, applying basic synchronous filtering, and storing raw data in the database.
   → See [specification-ingest.md](./specification-ingest.md) for detailed specification.

2. **Transform** *(not implemented yet)*
   Will be responsible for asynchronous processing of stored messages (summaries, embeddings, clustering, analytics).

3. **Emit** *(not implemented yet)*
   Will be responsible for delivering processed content to users via different delivery (!= Telegram) channels (web, Telegram bot, mobile app, etc.), based on **delivery subscriptions**.

### Data Flow (three ingestion paths)

```
Realtime Flow:
Telegram → Ingest (realtime mode) → Database

Backfill Flow:
Telegram → Ingest (backfill mode, batched + throttled) → Database

Interval Flow:
Telegram → Ingest (interval mode, batched + throttled) → Database
```


## Key Design Principles

* Ingest is **simple, reliable, and lossless**
* No LLMs or heavy processing in Ingest
* Filtering is deterministic and configurable
* All Telegram data is preserved
* Realtime ingestion is backed by batch recovery
* Architecture is ready for future Transform and Emit layers


## Ingest Component

The **Ingest** component is responsible for:

* Connecting to Telegram as a client (not a bot)
* Reading messages from configured channels and groups
* Applying basic, synchronous, deterministic filtering
* Persisting all available message and author metadata
* Supporting three operational modes: realtime, backfill, and interval

→ See [specification-ingest.md](./specification-ingest.md) for detailed specification.


## Transform Component (Future)

**Not implemented yet**

Planned responsibilities:

* Embeddings generation
* Clustering
* Summaries
* Aggregations and analytics

Transform must work **asynchronously** and never block Ingest.


## Emit Component (Future)

**Not implemented yet**

Planned responsibilities:

* Deliver processed content to users
* Channels: web, Telegram bot, mobile app, etc.
* Subscriptions are based on **delivery channels**, not Telegram channels


## Technical Stack

The application is built using a modern Python-based stack, ensuring consistency across environments through Docker.

- **Language**: Python 3.12 (Latest stable version)
- **Containerization**:
  - **Development**: Docker using `python:3.12` (Debian-based, latest LTS) for a full-featured environment.
  - **Production**: Docker using `python:3.12-slim` to keep image size minimal.
- **Telegram Integration**: [Telethon](https://docs.telethon.dev/) - a Python 3 asyncio Telegram client library.
- **Databases**:
  - **MongoDB**: Primary database for storing raw and processed messages and user subscriptions.
  - **Qdrant** *(future)*: Vector database for semantic search. Not used in Phase 1.
- **Core Libraries (Phase 1)**:
  - `telethon`: Telegram client interaction.
  - `python-dotenv`: Environment configuration management.
  - `pymongo`: MongoDB client for Python.
- **Core Libraries (Future)**:
  - `anthropic`: High-quality summarization and analysis via Claude (Processor component).

- **Environment Management**:
  - Development is preferred via Docker (Dev Containers).
  - If Docker is not used, a standard Python virtual environment (`venv`) must be used to manage dependencies.

This stack minimizes local environment friction by relying on Docker for all component executions.


## Telegram Authentication

The system uses a **single Telegram user account** (not a bot) for all channel access.

- **API credentials**: `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are stored in `.env` file.
- **Session file**: `anon.session` is stored in the `session/` folder at the project root.
- The session file persists the authenticated state and must be preserved across container restarts.


## Secrets Management

All secrets (API keys, database credentials) are managed via:

- `.env` file for local development
- Environment variables passed to Docker containers

No secrets are committed to version control.


## Logging

Phase 1 requires **standard logging** for:

- Connection events (connect, disconnect, reconnect)
- Message ingestion events (count, errors)
- Filter actions (messages dropped, fragments removed)
- Errors and exceptions

Broader observability (metrics, tracing) will be addressed in later phases.


## Deployment

**Current scope:** Local machine and Docker image.

Cloud deployment and orchestration are out of scope for Phase 1.