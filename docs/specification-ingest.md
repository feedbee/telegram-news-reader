# Ingest Component Specification

This document describes the **Ingest** component in detail.

For overall project architecture and technical stack, see [specification.md](./specification.md).

## Purpose

The **Ingest** component is a Python-based service responsible for:

* Connecting to Telegram
* Reading messages from configured channels/groups
* Applying basic, synchronous, non-LLM filtering
* Persisting **all available message and author metadata**
* Ensuring no message loss via backfill mode

## Ingest Modes

The Ingest script works in **exactly one mode at a time**, explicitly selected via CLI.

### 1. Realtime Mode

**Purpose:**
Listen to Telegram channels in real time and ingest new messages, edits, and deletions as they occur.

**Characteristics:**

* Persistent connection to Telegram
* Can listen to **multiple channels simultaneously**
* Monitors three types of events:
  * **New messages**: Processed and stored immediately
  * **Message edits**: Reprocessed through filters and updated in database
  * **Message deletions**: Removed from database
* Minimal processing (no heavy logic)
* Messages are written to the database immediately

**Optional Catch-up Phase:**

Realtime mode supports an optional `--catch-up` flag that fetches missed messages before starting to listen:

```bash
python ingest/main.py --mode realtime --catch-up
```

**How catch-up works:**

1. For each channel, queries the database for the last stored message ID using `get_latest_message_id()`
2. Fetches all messages from that ID to the current latest message
3. Processes them in batches with throttling (similar to backfill mode)
4. After catch-up completes, starts listening for new events

**Edit and Delete Handling:**

* **Edits**: When a message is edited, it is reprocessed through the filter engine
  * If it now matches a drop filter, it is **deleted from the database** (retroactive filtering)
  * Otherwise, the database record is updated with the new content
* **Deletions**: When a message is deleted in Telegram, it is removed from the database
  * Handles cases where the channel cannot be determined from the delete event

### 2. Backfill Mode (Catch-up)

**Purpose:**
Reliably fill missing messages (gaps) and update existing ones (edits) by processing history starting from a dedicated checkpoint.

**How it works:**

*   Maintains a **dedicated backfill pointer** (checkpoint) for each channel, separate from the `messages` collection.
*   For each channel:
    *   Reads `last_backfilled_id` from the checkpoint storage (or 0 if none).
    *   Fetches messages starting from `last_backfilled_id` moving towards the **current latest message** (forward or reverse-chronological until checkpoint is hit).
    *   **Fills gaps**: Messages between the checkpoint and the current realtime head are fetched and stored.
    *   **Updates edits**: Messages that already exist in the DB but were edited are updated.
    *   Updates the `last_backfilled_id` checkpoint **only after successful processing**.
*   This ensures that even if Realtime mode is spotty, Backfill mode eventually ensures consistency up to the latest point.
*   Uses **throttling** to avoid Telegram rate limits.
* Throttling logic is reused from the existing PoC (`/poc` folder)

### 3. Interval Mode

**Purpose:**
Download messages for a specific time interval.

**CLI arguments:**

* `--from` (optional, flexible datetime format)
* `--to` (optional, flexible datetime format)

**Flexible Datetime Format:**

Both `--from` and `--to` accept partial datetime strings. Missing components are filled automatically:

* **For `--from`** (start dates): Missing parts default to the beginning of the period
  * `2026` → `2026-01-01T00:00:00`
  * `2026-01` → `2026-01-01T00:00:00`
  * `2026-01-05` → `2026-01-05T00:00:00`
  * `2026-01-05T10` → `2026-01-05T10:00:00`

* **For `--to`** (end dates): Missing parts default to the end of the period
  * `2026` → `2026-12-31T23:59:59.999999`
  * `2026-01` → `2026-01-31T23:59:59.999999`
  * `2026-01-05` → `2026-01-05T23:59:59.999999`
  * `2026-01-05T10` → `2026-01-05T10:59:59.999999`

**Rules:**

* If both `from` and `to` are omitted → last 24 hours
* If only `from` is provided → from `from` until now
* If only `to` is provided → last 24 hours before `to`

**Important:**

* Messages are fetched **in batches**
* Throttling is mandatory (same mechanism as backfill)

## Channel Selection

* `--channels` argument is accepted **in all modes**
* If `--channels` is NOT provided:

  * All channels from config where `is_active = true` are used
* Channels are always processed **per channel** (isolated ingestion state)

## CLI Arguments

The ingest component accepts the following command-line arguments:

**Required:**
* `--mode` - Operating mode: `realtime`, `backfill`, or `interval`

**Optional (all modes):**
* `--channels` - Comma-separated list of channel IDs to override configuration

**Optional (realtime mode):**
* `--catch-up` - Fetch missed messages before starting realtime listening

**Optional (interval mode):**
* `--from` - Start date (flexible format: `2026`, `2026-01`, `2026-01-05`, `2026-01-05T10`, etc.)
* `--to` - End date (flexible format: `2026`, `2026-01`, `2026-01-05`, `2026-01-05T10`, etc.)

**Examples:**

```bash
# Realtime mode with catch-up
python ingest/main.py --mode realtime --catch-up

# Backfill mode
python ingest/main.py --mode backfill

# Interval mode for last 24 hours
python ingest/main.py --mode interval

# Interval mode for specific date range
python ingest/main.py --mode interval --from 2024-01-01 --to 2024-01-31

# Interval mode with flexible datetime formats
python ingest/main.py --mode interval --from 2024-01 --to 2024-02
python ingest/main.py --mode interval --from 2024-01-15T10 --to 2024-01-15T14

# Override channels
python ingest/main.py --mode realtime --channels @channel1,@channel2
```

## Configuration

Configuration can be provided through **environment variables**, a **JSON configuration file**, or a combination of both.

### Environment Variables

The following environment variables are supported:

**Required:**
* `TELEGRAM_API_ID` - Your Telegram API ID (integer)
* `TELEGRAM_API_HASH` - Your Telegram API hash (string)

**Optional:**
* `TELEGRAM_PHONE` - Your phone number (for authentication)
* `MONGODB_URI` - MongoDB connection string (default: `mongodb://admin:password@mongodb:27017/telegram-news-reader?authSource=admin`)
* `CONFIG_PATH` - Path to JSON configuration file (default: `config.json`)
* `SESSION_FILE` - Path to Telegram session file (default: `anon.session`)
* `CHANNELS` - Comma-separated list of channel IDs (e.g., `@channel1,@channel2`)

**Configuration Priority:**

* Environment variables and JSON config are **merged**
* For channels: Both sources are combined, duplicates are removed
* Environment variables take precedence for scalar values (e.g., `MONGODB_URI`)

**Example `.env` file:**

```bash
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+1234567890
MONGODB_URI=mongodb://admin:password@mongodb:27017/telegram-news-reader?authSource=admin
CONFIG_PATH=config.json
SESSION_FILE=anon.session
CHANNELS=@example_channel,@another_channel
```

### Configuration (JSON)

### Channels

```json
{
  "channels": [
    {
      "channel_id": "@example_channel",
      "name": "Example Channel",
      "is_active": true
    }
  ]
}
```

### Filters

Filters are defined in a `filters` section.

Each filter rule explicitly defines:

* how it matches
* what it does
* whether it affects the whole message or just a fragment

#### Filter capabilities

For **both static strings and regex filters**, the following actions are supported:

1. **Drop entire message**
2. **Remove matched fragment**
3. **Replace matched fragment with another string** (optional)

### Filters configuration example

```json
{
  "filters": {
    "string": [
      {
        "match": "Subscribe now",
        "action": "remove_fragment"
      },
      {
        "match": "Buy premium",
        "action": "drop_message"
      }
    ],
    "regex": [
      {
        "pattern": "^\\[AD\\].*",
        "action": "drop_message"
      },
      {
        "pattern": "\\s+#promo\\s+",
        "action": "replace_fragment",
        "replacement": " "
      }
    ]
  }
}
```

### Filter Behavior

**Processing order:**

1. **Drop-message rules first**:
   * String match drop filters are checked first
   * Regex drop filters are checked second
   * If any drop rule matches, the message is discarded and `None` is returned
2. **Fragment removal/replacement rules**:
   * Applied only if the message was not dropped
   * String-based removals and replacements are applied first
   * Regex-based removals and replacements are applied second
3. **Persist cleaned message** if not dropped

**Retroactive filtering:**

When a message is **edited** and reprocessed:
* If the edited message now matches a drop filter, it is **deleted from the database**
* This ensures that previously stored messages that violate filter rules after editing are removed
* This behavior applies in both realtime mode (via edit events) and backfill mode (when refetching edited messages)

**Empty messages:**

* Messages with no text are passed to the filter engine with an empty string
* Currently, non-text messages are not stored (implementation assumes text-based filtering)

## Storage Implementation

### MongoDB Collections

The ingest component uses two MongoDB collections:

1. **`messages`** - Stores all message data
2. **`backfill_checkpoints`** - Tracks backfill progress per channel

### Indexes

**messages collection:**
* Unique compound index on `(channel_id, message_id)` - Ensures no duplicate messages
* Index on `date` - Supports interval queries and date-based filtering

**backfill_checkpoints collection:**
* Unique index on `channel_id` - One checkpoint per channel

### Storage Operations

**Message Operations:**

* `save_message(message_data)` - Upsert operation (insert or update)
  * Handles both new messages and edits
  * Uses `(channel_id, message_id)` as the unique key
* `delete_message(channel_id, message_id)` - Removes a message from the database
  * Used when messages are deleted in Telegram
  * Used when edited messages now match drop filters (retroactive filtering)
* `get_latest_message_id(channel_id)` - Returns the highest message ID stored for a channel
  * Used by catch-up feature to determine where to start fetching
  * Returns 0 if no messages exist

**Checkpoint Operations:**

* `get_checkpoint(channel_id)` - Returns the last backfilled message ID
  * Returns 0 if no checkpoint exists
* `update_checkpoint(channel_id, message_id)` - Updates the backfill progress
  * Uses `$max` operator to ensure checkpoint only moves forward

### Stored Data (Database)

For each message, **all available Telegram data is stored**, including:

### Message data

* `channel_id`
* `message_id`
* full original text
* cleaned text (after filters)
* timestamp
* edit timestamp (if edited)
* message type
* reply / forward metadata
* raw Telegram payload (optional, but recommended)

### Author data

* user ID
* username
* first name
* last name
* is_bot flag

### Indexing requirements

* Unique index on:

  ```
  (channel_id, message_id)
  ```
* Idempotent writes (safe for realtime + backfill overlap)

## Throttling Requirements

* Mandatory for:
  * Backfill mode
  * Interval mode
* Must be **batch-based**
* Implementation should reuse logic from the existing PoC (`/poc`)
* Throttling parameters must be configurable


## Error Handling

### Graceful Shutdown

The application handles shutdown signals cleanly:

* **KeyboardInterrupt** (Ctrl+C): Caught and handled without printing a traceback
* **asyncio.CancelledError**: Handled when Telethon's `run_until_disconnected()` is interrupted
* **Cleanup**: The `finally` block ensures `ingester.stop()` is always called

**Example shutdown:**
```
^C
Stopping...
```

### Current Error Handling

**Entity fetch failures:**
* Logged with error message
* Processing continues with the next channel
* No retry logic currently implemented

**Message processing errors:**
* Logged with message ID and error details
* Processing continues with the next message

**Database connection:**
* No automatic retry or reconnection logic
* Connection failures will cause the application to exit

### Future Improvements

The following error handling features are **not currently implemented** but are recommended for production:

* Exponential backoff retry logic for Telegram API calls
* Automatic reconnection in realtime mode on disconnect
* Database write retries with exponential backoff
* Circuit breaker pattern for repeated failures

## Deployment

### Running from Source

**Prerequisites:**
* Python 3.12
* MongoDB instance (local or remote)
* Telegram API credentials

**Installation:**
```bash
# Install dependencies
pip install -r ingest/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the application
python ingest/main.py --mode realtime --catch-up
```

### Docker Deployment

The ingest component includes production-ready Docker support with security best practices.

**Key Features:**
* Multi-stage build for optimized image size
* Non-root user (`appuser`) for security
* Virtual environment isolation
* Minimal attack surface

**Build and run locally:**
```bash
# Build
docker build -t telegram-news-ingest:latest -f ingest/Dockerfile ingest/

# Run with network and volume mounts
docker run --rm -it \
  --network telegram-news-network \
  --env-file .env \
  -v $(pwd)/session:/app/session \
  -e SESSION_FILE=session/acc2.anon.session \
  telegram-news-ingest:latest
```

**Default Docker command:**
The container runs with `--mode realtime --catch-up` by default.

**For detailed Docker instructions**, including multi-platform builds for ECR, see [`ingest/README.md`](../ingest/README.md).
