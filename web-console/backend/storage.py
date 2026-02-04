import os
import logging
from pymongo import MongoClient
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self):
        # Connection
        self.mongo_uri = os.getenv("MONGODB_URI") or "mongodb://localhost:27017/telegram-news-reader?authSource=admin"
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client.get_database()
        
        # Collections
        self.users_collection = self.db.users

    def upsert_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a user record.
        On insert: sets created_at
        On update: sets last_login_at
        """
        uid = user_data["uid"]
        now = datetime.utcnow()
        
        update_doc = {
            "$set": {
                "last_login_at": now,
                "email": user_data.get("email"),
                "display_name": user_data.get("display_name"),
                "photo_url": user_data.get("photo_url"),
                "provider_id": user_data.get("provider_id", "google.com"),
            },
            "$setOnInsert": {
                "created_at": now,
                "metadata": {
                    "last_message_ids": {}
                }
            }
        }
        
        # Upsert
        self.users_collection.update_one({"uid": uid}, update_doc, upsert=True)
        
        # Return the full user document
        return self.users_collection.find_one({"uid": uid}, {"_id": 0})

    def update_user_metadata(self, uid: str, key: str, value: Any):
        """
        Update a specific field in the user's metadata.
        Example: key="last_message_ids.@channelname"
        """
        self.users_collection.update_one(
            {"uid": uid},
            {"$set": {f"metadata.{key}": value}}
        )

    def get_user_metadata(self, uid: str) -> Dict[str, Any]:
        """
        Retrieve user metadata.
        """
        user = self.users_collection.find_one({"uid": uid}, {"metadata": 1})
        if user and "metadata" in user:
            return user["metadata"]
        return {}
