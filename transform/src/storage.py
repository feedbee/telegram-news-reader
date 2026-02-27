
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pymongo import MongoClient, DESCENDING, ASCENDING
from bson import ObjectId
from .config import config

class Storage:
    def __init__(self):
        self.client = MongoClient(config.mongo_uri)
        self.db = self.client.get_database() # Db name inferred from URI
        self.messages_collection = self.db["messages"]

    def get_messages_by_interval(self, channel_id: str, from_date: datetime, to_date: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch messages for a specific channel within a time interval.
        Results are limited to `limit` messages (newest first within the range, or logical order).
        Typically we want chronological order for summarization.
        """
        # Ensure dates are timezone aware (UTC)
        if from_date.tzinfo is None:
            from_date = from_date.replace(tzinfo=timezone.utc)
        if to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=timezone.utc)

        # Basic query
        query = {"channel_id": channel_id}
        
        # Add date range filter (MongoDB Date)
        query["date"] = {
            "$gte": from_date,
            "$lte": to_date
        }
        
        # We fetch chronological order for better summarization flow
        cursor = self.messages_collection.find(query).sort("date", ASCENDING).limit(limit)
        return list(cursor)

    def get_messages_from_id(self, channel_id: str, last_message_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch messages for a channel starting strictly AFTER the given message_id.
        """
        query = {
            "channel_id": channel_id,
            "message_id": {"$gt": last_message_id}
        }
        
        cursor = self.messages_collection.find(query).sort("message_id", ASCENDING).limit(limit)
        return list(cursor)

    def get_total_message_count(self, channel_id: str, from_date: datetime, to_date: datetime) -> int:
        """
        Count total messages in interval without fetching them.
        """
        # Ensure dates are timezone aware (UTC)
        if from_date.tzinfo is None:
            from_date = from_date.replace(tzinfo=timezone.utc)
        if to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=timezone.utc)

        query = {
            "channel_id": channel_id,
            "date": {
                "$gte": from_date,
                "$lte": to_date
            }
        }
        return self.messages_collection.count_documents(query)

    def get_total_message_count_from_id(self, channel_id: str, last_message_id: int) -> int:
        """
        Count total messages after ID without fetching them.
        """
        query = {
            "channel_id": channel_id,
            "message_id": {"$gt": last_message_id}
        }
        return self.messages_collection.count_documents(query)

    def get_latest_message(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the absolute latest message for a channel to return current head metadata.
        """
        return self.messages_collection.find_one(
            {"channel_id": channel_id},
            sort=[("message_id", DESCENDING)]
        )
