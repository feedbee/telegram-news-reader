
import os
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class ChannelConfig:
    channel_id: str
    name: str = ""
    is_active: bool = True

@dataclass
class FilterAction:
    action: str  # 'drop_message', 'remove_fragment', 'replace_fragment'
    match: Optional[str] = None
    pattern: Optional[str] = None
    replacement: str = ""

@dataclass
class FiltersConfig:
    string: List[FilterAction] = field(default_factory=list)
    regex: List[FilterAction] = field(default_factory=list)

@dataclass
class AppConfig:
    api_id: int
    api_hash: str
    phone: str
    mongo_uri: str
    session_file: str
    channels: List[ChannelConfig]
    filters: FiltersConfig

def load_config(config_path: Optional[str] = None) -> AppConfig:
    # 0. Determine config path
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "config.json")

    # Telegram Credentials
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("TELEGRAM_PHONE")

    if not api_id or not api_hash:
        raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment variables.")

    # MongoDB
    mongo_uri = os.getenv("MONGODB_URI") or "mongodb://localhost:27017/telegram-news-reader?authSource=admin"

    # Session file location
    session_file = os.getenv("SESSION_FILE", "anon.session")

    # Load Channels
    channels = []
    
    # 1. Load from env vars (comma separated list of channel IDs)
    env_channels = os.getenv("CHANNELS")
    if env_channels:
        for ch in env_channels.split(","):
            ch = ch.strip()
            if ch:
                channels.append(ChannelConfig(channel_id=ch, name=ch))

    # 2. Load from config file (if exists)
    filters_config = FiltersConfig()
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                
                # Merge channels from json
                if "channels" in data:
                    for ch_data in data["channels"]:
                        # Avoid duplicates if already added from env
                        if not any(c.channel_id == ch_data["channel_id"] for c in channels):
                            channels.append(ChannelConfig(
                                channel_id=ch_data["channel_id"],
                                name=ch_data.get("name", ch_data["channel_id"]),
                                is_active=ch_data.get("is_active", True)
                            ))
                
                # Load filters
                if "filters" in data:
                    if "string" in data["filters"]:
                        for f_data in data["filters"]["string"]:
                            filters_config.string.append(FilterAction(**f_data))
                    if "regex" in data["filters"]:
                         for f_data in data["filters"]["regex"]:
                            filters_config.regex.append(FilterAction(**f_data))

        except Exception as e:
            print(f"Warning: Error loading {config_path}: {e}")

    return AppConfig(
        api_id=int(api_id),
        api_hash=api_hash,
        phone=phone,
        mongo_uri=mongo_uri,
        session_file=session_file,
        channels=channels,
        filters=filters_config
    )
