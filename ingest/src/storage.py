
import pymongo
from pymongo import MongoClient, UpdateOne, ASCENDING
from datetime import datetime
from typing import Dict, Any, List
from .config import AppConfig

class Storage:
    def __init__(self, config: AppConfig):
        self.config = config
        self.client = MongoClient(self.config.mongo_uri)
        self.db = self.client.get_database() # Db name inferred from URI
        self.messages_collection = self.db["messages"]
        self.checkpoints_collection = self.db["backfill_checkpoints"]
        self._ensure_indexes()

    def _ensure_indexes(self):
        # Unique index on (channel_id, message_id)
        self.messages_collection.create_index(
            [("channel_id", ASCENDING), ("message_id", ASCENDING)],
            unique=True
        )
        # Index on date to support interval queries (implicit requirement for potential future use)
        self.messages_collection.create_index([("date", ASCENDING)])
        
        # Checkpoints index
        self.checkpoints_collection.create_index("channel_id", unique=True)

    def save_message(self, message_data: Dict[str, Any]):
        """
        Save a single message to MongoDB. 
        Uses upsert to handle updates (e.g. edits).
        """
        channel_id = message_data["channel_id"]
        message_id = message_data["message_id"]

        self.messages_collection.update_one(
            {"channel_id": channel_id, "message_id": message_id},
            {"$set": message_data},
            upsert=True
        )

    def save_messages_batch(self, messages: List[Dict[str, Any]]):
        """
        Save a batch of messages.
        """
        if not messages:
            return

        operations = []
        for msg in messages:
            operations.append(
                UpdateOne(
                    {"channel_id": msg["channel_id"], "message_id": msg["message_id"]},
                    {"$set": msg},
                    upsert=True
                )
            )
        
        if operations:
            self.messages_collection.bulk_write(operations)

    def get_latest_message_id(self, channel_id: str) -> int:
        """
        Get the ID of the latest stored message for a channel.
        Returns 0 if no messages found.
        """
        latest = self.messages_collection.find_one(
            {"channel_id": channel_id},
            sort=[("message_id", pymongo.DESCENDING)]
        )
        return latest["message_id"] if latest else 0

    def get_checkpoint(self, channel_id: str) -> int:
        """
        Get the last backfilled message ID for a channel.
        Returns 0 if no checkpoint exists.
        """
        doc = self.checkpoints_collection.find_one({"channel_id": channel_id})
        return doc["last_backfilled_id"] if doc else 0

    def update_checkpoint(self, channel_id: str, message_id: int):
        """
        Update the backfill checkpoint for a channel.
        Only updates if the new message_id is greater than the stored one 
        (though logic typically dictates we move forward, safety check is good).
        """
        self.checkpoints_collection.update_one(
            {"channel_id": channel_id},
            {"$max": {"last_backfilled_id": message_id}},
            upsert=True
        )

    def delete_message(self, channel_id: str, message_id: int):
        """
        Delete a message from the database.
        """
        result = self.messages_collection.delete_one({
            "channel_id": channel_id,
            "message_id": message_id
        })
        return result.deleted_count > 0

