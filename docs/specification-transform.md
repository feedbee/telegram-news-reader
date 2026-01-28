# Transform Component Specification

This document describes the **Transform** component in detail.

For overall project architecture and technical stack, see [specification.md](./specification.md).

## Purpose

The **Transform** component is responsible for processing raw messages stored by the Ingest component. Its core function is to generate high-quality summaries and insights using Large Language Models (Claude).

It provides two interfaces:
1. **CLI:** For manual execution, cron jobs, and scripting.
2. **REST API:** For integration with the future Delivery component or other internal services.

## Interfaces

### 1. CLI Interface

The CLI is designed for batch processing and direct interaction.

**Usage:**
```bash
python transform/main.py summarize --channel-id <id> [options]
```

**Commands:**
* `summarize`: Generate a summary of messages based on time or ID range.

**Arguments for `summarize`:**
* `--channel-id` (Required): Target Telegram channel ID.
* `--format`: Output format, either `MD` (Markdown text) or `JSON`. Default: `MD`.
* `--from`: Start date/time (inclusive). Supports flexible formats (e.g., `2024-01`, `2024-01-25T10`).
* `--to`: End date/time (inclusive). Supports flexible formats.
* `--last-message-id`: Process messages strictly *after* this ID.

**Behavior:**
* **Defaults:** If no filters are provided, defaults to the last **24 hours**.
* **Limits:** Processes a maximum of **100 messages** per execution.
* **Output (MD):** Prints the Markdown summary to `STDOUT`. Prints metadata to `STDERR`:
  * `Messages Total`
  * `Messages Processed`
  * `Last Message ID`
  * `Last Message Timestamp`
* **Output (JSON):** Prints a full JSON object to `STDOUT`.

### 2. REST API

The REST API provides a simple endpoint for on-demand summarization.

* **Protocol:** HTTP/1.1
* **Framework:** FastAPI
* **Port:** 8000 (Internal Docker network only)

#### Endpoint: `GET /summarize`

**Parameters (Query String):**
* `channel_id` (Required)
* `format` (Optional, `MD` or `JSON`, default `MD`)
* `from` (Optional)
* `to` (Optional)
* `last_message_id` (Optional)

**Response (JSON format):**
```json
{
  "summary": "Markdown text...",
  "last_message_id": 12345,
  "last_message_timestamp": "2026-01-25T10:30:00Z",
  "messages": {
      "total": 150,
      "processed": 100
  },
  "request": { ... }
}
```

**Response (MD format):**
Returns the summary as plain text (Content-Type: `text/markdown`). Metadata headers are included:
* `X-META-MESSAGES-TOTAL`
* `X-META-MESSAGES-PROCESSED`
* `X-META-LAST-MESSAGE-ID`
* `X-META-LAST-MESSAGE-TIMESTAMP`

## Summarization Logic

The component uses **Anthropic's Claude** models to generate summaries.

1. **Fetching**: Retrieves messages from MongoDB based on filters.
2. **Buffering**: Detailed messages (date, text, links) are formatted into a prompt.
3. **Prompting**: A predefined prompt instructs Claude to:
   * Highlight key events
   * Mention secondary events briefly
   * Maintain structure and readability
   * Ensure links are preserved and formatted
4. **Empty State**: If no messages are found, returns "Nothing new" instead of an error.

## Configuration

Configuration is managed via environment variables (shared `.env` file):

* `MONGODB_URI`: Connection string for message storage.
* `ANTHROPIC_API_KEY`: API key for Claude.
* `CLAUDE_MODEL`: Model version (default: `claude-sonnet-4-20250514`).
* `MAX_TOKENS`: Max generation tokens (default: `4000`).

## Deployment

The component is containerized using Docker.

* **Base Image:** `python:3.12-slim`
* **Port:** 8000 (exposed but typically mapped only within internal network)
* **Command:** Runs the API server by default. CLI can be run via `docker run ... python main.py`.
