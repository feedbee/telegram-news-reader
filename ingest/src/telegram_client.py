
import os
import asyncio
from telethon import TelegramClient
from .config import AppConfig

class TelegramClientWrapper:
    def __init__(self, config: AppConfig):
        self.config = config
        # Use a custom session path if needed, but per spec it's in /session/anon.session
        # Telethon expects just the path to the session file
        self.client = TelegramClient(
            self.config.session_file, 
            self.config.api_id, 
            self.config.api_hash
        )

    async def start(self):
        print(f"Connecting to Telegram with session: {self.config.session_file}...")
        # Start the client. If phone is needed it will ask (interactive), 
        # but in this env we assume session is valid or we pass phone.
        await self.client.start(phone=self.config.phone)
        
        if not await self.client.is_user_authorized():
             print("Client is not authorized. Please check your session file or credentials.")
             # In a real scenario we might want to fail hard here
             raise Exception("Telegram client not authorized")

        me = await self.client.get_me()
        print(f"Connected as {me.username}")

    async def stop(self):
        await self.client.disconnect()

    def get_client(self):
        return self.client
