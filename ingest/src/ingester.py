
import asyncio
from datetime import datetime, timezone
from telethon import events
from typing import Optional
from .config import AppConfig, ChannelConfig
from .telegram_client import TelegramClientWrapper
from .storage import Storage
from .filters import FilterEngine
from .utils import Throttler, serialize_message

class Ingester:
    def __init__(self, config: AppConfig):
        self.config = config
        self.client_wrapper = TelegramClientWrapper(config)
        self.storage = Storage(config)
        self.filter_engine = FilterEngine(config.filters)
        self.client = self.client_wrapper.get_client()

    async def start(self):
        await self.client_wrapper.start()

    async def stop(self):
        await self.client_wrapper.stop()

    async def _process_message(self, message, channel_id: str):
        """
        Common processing logic for a single message.
        
        Args:
            message: The Telegram message object
            channel_id: The channel identifier
        """
        # 1. Filter
        if not message.text:
             # Even if no text (media only), we might want to store it, but let's assume text-based for now
             # or just pass empty string to filter engine
             pass

        cleaned_text = self.filter_engine.process_message(message.text or "")
        
        if cleaned_text is None:
            print(f"Message {message.id} from {channel_id} dropped by filter.")
            # Try to delete the message if it exists (handles edited messages that are now filtered)
            deleted = self.storage.delete_message(channel_id, message.id)
            if deleted:
                print(f"Deleted previously stored message {message.id} from {channel_id} (now filtered out)")
            return

        # 2. Serialize and Enrich
        data = serialize_message(message)
        data["channel_id"] = channel_id
        data["cleaned_text"] = cleaned_text
        
        # 3. Store
        try:
            self.storage.save_message(data)
            print(f"Saved message {message.id} from {channel_id}")
        except Exception as e:
            print(f"Error saving message {message.id}: {e}")

    async def _catch_up(self):
        """
        Catch up on missed messages since the last run.
        For each channel, fetches messages from the last stored message to the current latest.
        """
        print("Starting catch-up phase...")
        throttler = Throttler()

        for channel in self.config.channels:
            print(f"Catching up on channel: {channel.channel_id}")
            
            try:
                entity = await self.client.get_entity(channel.channel_id)
            except Exception as e:
                print(f"Error getting entity for {channel.channel_id}: {e}")
                continue

            # Get the latest message ID we have stored
            last_stored_id = self.storage.get_latest_message_id(channel.channel_id)
            print(f"Last stored message ID: {last_stored_id}")

            count = 0
            
            # Fetch messages from last_stored_id to the latest
            # reverse=True gives chronological order (oldest to newest)
            async for message in self.client.iter_messages(entity, min_id=last_stored_id, reverse=True):
                await self._process_message(message, channel.channel_id)
                count += 1
                
                if count % 100 == 0:
                    await throttler.throttle(batch_size=100)
            
            print(f"Caught up {count} messages for {channel.channel_id}")
        
        print("Catch-up phase completed.")

    async def run_realtime(self, catch_up: bool = False):
        """
        Listen to new messages, edits, and deletions in real-time.
        
        Args:
            catch_up: If True, catch up on missed messages before starting realtime listening
        """
        print("Starting Realtime Mode...")
        
        # Catch up on missed messages if requested
        if catch_up:
            await self._catch_up()
        
        channel_ids = [ch.channel_id for ch in self.config.channels]
        
        @self.client.on(events.NewMessage(chats=channel_ids))
        async def new_message_handler(event):
            chat = await event.get_chat()
            channel_id = f"@{chat.username}" if chat.username else str(chat.id)
            await self._process_message(event.message, channel_id)

        @self.client.on(events.MessageEdited(chats=channel_ids))
        async def message_edited_handler(event):
            chat = await event.get_chat()
            channel_id = f"@{chat.username}" if chat.username else str(chat.id)
            print(f"Message {event.message.id} edited in {channel_id}")
            await self._process_message(event.message, channel_id)

        @self.client.on(events.MessageDeleted(chats=channel_ids))
        async def message_deleted_handler(event):
            # MessageDeleted event contains deleted_ids and chat information
            # We need to get the chat from the event's input_chat or chat_id
            try:
                # Try to get chat from event
                chat = None
                channel_id = None
                
                # MessageDeleted events have chat_id attribute
                if hasattr(event, 'chat_id') and event.chat_id:
                    chat = await self.client.get_entity(event.chat_id)
                    channel_id = f"@{chat.username}" if hasattr(chat, 'username') and chat.username else str(chat.id)
                
                if channel_id:
                    for msg_id in event.deleted_ids:
                        deleted = self.storage.delete_message(channel_id, msg_id)
                        if deleted:
                            print(f"Deleted message {msg_id} from {channel_id}")
                        else:
                            print(f"Message {msg_id} not found in database (already deleted or never stored)")
                else:
                    # If we can't determine the channel, log the deleted IDs for debugging
                    print(f"Received delete event for message IDs: {event.deleted_ids} (channel unknown)")
            except Exception as e:
                print(f"Error handling deleted message: {e}")

        print(f"Listening on {len(self.config.channels)} channels...")
        print("Monitoring: New messages, Edits, and Deletions")
        await self.client.run_until_disconnected()

    async def run_backfill(self):
        """
        Fetch history from the dedicated checkpoint up to the latest message.
        Fills gaps and updates edited messages.
        """
        print("Starting Backfill Mode...")
        throttler = Throttler()

        for channel in self.config.channels:
            print(f"Processing channel: {channel.channel_id}")
            
            try:
                entity = await self.client.get_entity(channel.channel_id)
            except Exception as e:
                print(f"Error getting entity for {channel.channel_id}: {e}")
                continue

            last_backfilled_id = self.storage.get_checkpoint(channel.channel_id)
            print(f"Last backfilled message ID (Checkpoint): {last_backfilled_id}")

            count = 0
            max_processed_id = last_backfilled_id
            
            # reverse=True fetches chronological order (Oldest -> Newest)
            # min_id ensures we only fetch what we haven't confirmed backfilled yet.
            async for message in self.client.iter_messages(entity, min_id=last_backfilled_id, reverse=True):
                 await self._process_message(message, channel.channel_id)
                 
                 # Keep track of the highest ID we've processed
                 if message.id > max_processed_id:
                     max_processed_id = message.id
                 
                 count += 1
                 if count % 100 == 0:
                     # Update checkpoint after a batch
                     self.storage.update_checkpoint(channel.channel_id, max_processed_id)
                     await throttler.throttle(batch_size=100)
            
            # Final checkpoint update
            if max_processed_id > last_backfilled_id:
                self.storage.update_checkpoint(channel.channel_id, max_processed_id)

            print(f"Finished backfill for {channel.channel_id}. Processed {count} messages. New Checkpoint: {max_processed_id}")

    async def run_interval(self, start_date: datetime, end_date: Optional[datetime] = None):
        """
        Fetch messages within a time range.
        """
        print(f"Starting Interval Mode: {start_date} to {end_date or 'Now'}")
        throttler = Throttler()

        for channel in self.config.channels:
            print(f"Processing channel: {channel.channel_id}")
            try:
                 entity = await self.client.get_entity(channel.channel_id)
            except Exception as e:
                print(f"Error getting entity {channel.channel_id}: {e}")
                continue
            
            count = 0
            # iter_messages with offset_date creates a starting point.
            # If we want [start, end], we can use reverse=True (oldest to newest) starting from start_date?
            # Or just iterate default (Newest first)
            
            # Common pattern: iterate from Newest (default).
            # If msg.date > end_date: continue (skip newer)
            # If msg.date < start_date: break (we went too far back)
            
            async for message in self.client.iter_messages(entity):
                if end_date and message.date > end_date:
                    continue
                if message.date < start_date:
                    break
                
                await self._process_message(message, channel.channel_id)
                count += 1
                if count % 100 == 0:
                     await throttler.throttle(batch_size=100)
            
            print(f"Finished interval for {channel.channel_id}. Processed {count} messages.")
