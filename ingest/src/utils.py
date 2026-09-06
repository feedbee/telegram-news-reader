
import asyncio
import time
from datetime import timezone
from typing import Dict, Any

class Throttler:
    def __init__(self, messages_per_request: int = 100, delay_between_requests: float = 1.0, max_requests_per_minute: int = 20):
        self.messages_per_request = messages_per_request
        self.delay_between_requests = delay_between_requests
        self.max_requests_per_minute = max_requests_per_minute
        self.request_count = 0
        self.start_time = time.time()
        self.total_messages = 0

    async def throttle(self, batch_size: int = 0):
        """
        Call this after processing a batch of messages.
        """
        self.total_messages += batch_size
        self.request_count += 1

        # Basic delay
        await asyncio.sleep(self.delay_between_requests)

        # Minute-based rate limit
        if self.request_count % self.max_requests_per_minute == 0:
            elapsed = time.time() - self.start_time
            if elapsed < 60:
                sleep_time = 60 - elapsed
                print(f"Rate limit: sleeping for {sleep_time:.1f} seconds...")
                await asyncio.sleep(sleep_time)
            self.start_time = time.time()

def serialize_message(message) -> Dict[str, Any]:
    """
    Convert the Telegram message fields used by the application to a dictionary.
    """
    # Basic fields
    msg_date = message.date
    if msg_date and msg_date.tzinfo is None:
        msg_date = msg_date.replace(tzinfo=timezone.utc)

    edit_date = message.edit_date
    if edit_date and edit_date.tzinfo is None:
        edit_date = edit_date.replace(tzinfo=timezone.utc)

    data = {
        "message_id": message.id,
        "date": msg_date,
        "edit_date": edit_date,
        "text": message.text,
        "raw_text": message.raw_text,
        "views": getattr(message, "views", None),
        "forwards": getattr(message, "forwards", None),
        "grouped_id": getattr(message, "grouped_id", None),
    }

    # Sender info
    if message.sender:
         data["sender_id"] = message.sender_id
         if hasattr(message.sender, "username"):
             data["sender_username"] = message.sender.username
    
    return data
