# Transform Component

The **Transform** component processes raw Telegram messages stored in MongoDB and generates high-level summaries using AI (Claude).

## Features

* **AI Summarization**: Uses Anthropic's Claude to create structured digests.
* **Dual Interface**:
  * **CLI**: For scripts and manual use.
  * **REST API**: FastAPI-based endpoint for integrations.
* **Flexible Filtering**: Select messages by date range or message ID.
* **Internal Storage**: Reads directly from the shared MongoDB `messages` collection.

## Usage

### 1. CLI Usage

Run the CLI from the project root:

```bash
# Summarize last 24 hours (default)
python transform/main.py summarize --channel-id @my_channel

# Summarize specific date range
python transform/main.py summarize --channel-id @my_channel --from 2024-01-01 --to 2024-01-07

# Summarize since a specific message ID
python transform/main.py summarize --channel-id @my_channel --last-message-id 12345

# Output JSON format
python transform/main.py summarize --channel-id @my_channel --format JSON
```

### 2. API Usage

Start the server:
```bash
python transform/server.py
# OR via Uvicorn directly
uvicorn transform.server:app --port 8000
```

Request a summary:
```bash
curl "http://localhost:8000/summarize?channel_id=@my_channel&format=JSON"
```

## Docker

Build the image:
```bash
docker build -t telegram-news-transform -f transform/Dockerfile transform/
```

Run the API:
```bash
docker run --rm \
  --network telegram-news-network \
  --env-file .env \
  telegram-news-transform
```

## Configuration

Ensure your `.env` file contains:
* `MONGODB_URI`
* `ANTHROPIC_API_KEY`
