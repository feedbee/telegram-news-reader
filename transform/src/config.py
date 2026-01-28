
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # MongoDB
    mongo_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/telegram-news-reader?authSource=admin")
    
    # Anthropic
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    max_tokens: int = int(os.getenv("MAX_TOKENS", "4000"))
    
    # Summarization Defaults
    max_messages_per_request: int = 100
    default_lookback_hours: int = 24
    # Config File
    config_path: str = os.getenv("CONFIG_PATH", "config.json")
    
    def get_channel_prompt(self, channel_id: str) -> Optional[str]:
        """
        Loads the config file and returns the summarization_prompt for the given channel_id.
        """
        if not os.path.exists(self.config_path):
            return None
        
        try:
            import json
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                channels = data.get("channels", [])
                for ch in channels:
                    if ch.get("channel_id") == channel_id:
                        return ch.get("summarization_prompt")
        except Exception as e:
            print(f"Error loading prompt from {self.config_path}: {e}")
        
        return None

config = Config()
