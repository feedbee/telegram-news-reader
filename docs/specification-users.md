# Specification: User Management System

## Overview
This feature introduces first-class user management to the `telegram-news-reader`. It validates logged-in users against a native MongoDB collection (`users`), stores auth metadata, and persists user preferences (Last Message ID).

## Data Model (MongoDB)

### Collection: `users`
| Field | Type | Description |
| :--- | :--- | :--- |
| `uid` | String (Index, Unique) | Firebase User ID (Primary Key) |
| `email` | String | User's email address |
| `display_name` | String | User's full name |
| `photo_url` | String | Avatar URL |
| `created_at` | DateTime | Timestamp of first login |
| `last_login_at` | DateTime | Timestamp of most recent login |
| `metadata` | Object | User-specific metadata |
| `metadata.last_message_ids` | Map<String, Int> | Key: `channel_id`, Value: `message_id` |

## Authentication Flow

1.  **Frontend Login**:
    *   User signs in via Google SSO.
    *   Frontend obtains ID Token.
2.  **User Synchronization** (Triggered by frontend):
    *   Frontend calls `POST /api/users/sync` immediately after login.
    *   Backend validates token, creates/updates user record (`last_login_at`).
    *   **Response**: Returns the user's `metadata` (specifically `last_message_ids`).
3.  **Frontend State Update**:
    *   Frontend uses the returned `last_message_ids` to pre-fill the state for each channel, overriding local storage defaults if present.

## API Changes

### Backend (`web-console/backend`)
*   **New Endpoint**: `POST /api/users/sync`
    *   **Action**: Upsert user record.
    *   **Response**: `{ "status": "ok", "metadata": { "last_message_ids": { ... } } }`

*   **Modified Endpoint**: `GET /api/summarize`
    *   **Action**: When a summary is successfully generated, **update** the `last_message_ids` for that channel in the user's `metadata` in MongoDB.
    *   **Note**: The input `last_message_id` still comes from the UI (query param), but the successful action triggers the DB save used for *next* session.

*   **No Changes**: `/api/channels` remains as is.

## Storage Layer (`storage.py`)
*   Use `pymongo` (Synchronous) instead of `motor`.
*   Implement `Storage` class (similar to other components) to handle:
    *   `upsert_user(user_data)`
    *   `update_user_metadata(uid, key, value)`
