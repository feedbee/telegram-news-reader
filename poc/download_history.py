#!/usr/bin/env python3
"""
Download Telegram chat/group history gradually while respecting rate limits.
Outputs JSON with all available metadata to STDOUT.
"""
import os
import sys
import json
import asyncio
import argparse
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
PHONE = os.getenv('TELEGRAM_PHONE')

# Telegram rate limits (conservative values to avoid bans)
MESSAGES_PER_REQUEST = 100  # Telegram allows up to 100 messages per request
DELAY_BETWEEN_REQUESTS = 1.0  # 1 second delay between requests (conservative)
MAX_REQUESTS_PER_MINUTE = 20  # Conservative limit


def log(message):
    """Log to stderr so it doesn't interfere with JSON output to stdout"""
    print(message, file=sys.stderr)


def parse_partial_date(date_str, to_date=False):
    """
    Parses a partial date string like '2026', '2026-01', '2026-01-03', '2026-01-03T15:30'
    If to_date is True, it fills missing components to the end of the period
    """
    formats = [
        ("%Y", "year"),
        ("%Y-%m", "month"),
        ("%Y-%m-%d", "day"),
        ("%Y-%m-%dT%H", "hour"),
        ("%Y-%m-%dT%H:%M", "minute"),
        ("%Y-%m-%dT%H:%M:%S", "second"),
    ]
    
    for fmt, precision in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if not to_date:
                return dt.replace(tzinfo=timezone.utc)
            else:
                if precision == "year":
                    return datetime(dt.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                elif precision == "month":
                    next_month = dt.month % 12 + 1
                    next_year = dt.year + (dt.month // 12)
                    last_day = (datetime(next_year, next_month, 1) - timedelta(days=1)).day
                    return datetime(dt.year, dt.month, last_day, 23, 59, 59, tzinfo=timezone.utc)
                elif precision == "day":
                    return datetime(dt.year, dt.month, dt.day, 23, 59, 59, tzinfo=timezone.utc)
                elif precision == "hour":
                    return datetime(dt.year, dt.month, dt.day, dt.hour, 59, 59, tzinfo=timezone.utc)
                elif precision == "minute":
                    return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, 59, tzinfo=timezone.utc)
                else:
                    return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_str}")


def serialize_user(user):
    """Convert a Telegram user object to a JSON-serializable dictionary"""
    if not user:
        return None
    
    return {
        "id": user.id,
        "is_bot": getattr(user, 'bot', False),
        "first_name": getattr(user, 'first_name', None),
        "last_name": getattr(user, 'last_name', None),
        "username": getattr(user, 'username', None),
        "phone": getattr(user, 'phone', None),
        "photo_id": user.photo.photo_id if hasattr(user, 'photo') and user.photo else None,
        "status": user.status.__class__.__name__ if hasattr(user, 'status') and user.status else None,
        "verified": getattr(user, 'verified', False),
        "restricted": getattr(user, 'restricted', False),
        "scam": getattr(user, 'scam', False),
        "fake": getattr(user, 'fake', False),
        "premium": getattr(user, 'premium', False),
    }


def serialize_message(message, user_cache=None):
    """Convert a Telegram message to a JSON-serializable dictionary with all metadata"""
    data = {
        "id": message.id,
        "date": message.date.isoformat() if message.date else None,
        "edit_date": message.edit_date.isoformat() if message.edit_date else None,
        "text": message.text,
        "raw_text": message.raw_text,
        "message": message.message,
        "from_id": None,
        "peer_id": None,
        "fwd_from": None,
        "via_bot_id": message.via_bot_id,
        "reply_to": None,
        "media": None,
        "entities": [],
        "views": message.views,
        "forwards": message.forwards,
        "replies": None,
        "edit_hide": message.edit_hide,
        "pinned": message.pinned,
        "post": message.post,
        "from_scheduled": message.from_scheduled,
        "legacy": message.legacy,
        "mentioned": message.mentioned,
        "media_unread": message.media_unread,
        "silent": message.silent,
        "post_author": message.post_author,
        "grouped_id": message.grouped_id,
        "reactions": None,
        "restriction_reason": [],
        "ttl_period": message.ttl_period,
    }
    
    # Serialize from_id
    if message.from_id:
        user_id = getattr(message.from_id, 'user_id', None) or getattr(message.from_id, 'channel_id', None)
        data["from_id"] = {
            "type": message.from_id.__class__.__name__,
            "id": user_id
        }
        # Add user data if available in cache
        if user_cache and user_id and user_id in user_cache:
            data["from_id"]["user"] = user_cache[user_id]
    
    # Serialize peer_id
    if message.peer_id:
        data["peer_id"] = {
            "type": message.peer_id.__class__.__name__,
            "id": getattr(message.peer_id, 'user_id', None) or getattr(message.peer_id, 'channel_id', None) or getattr(message.peer_id, 'chat_id', None)
        }
    
    # Serialize forward info
    if message.fwd_from:
        data["fwd_from"] = {
            "date": message.fwd_from.date.isoformat() if message.fwd_from.date else None,
            "from_id": None,
            "from_name": message.fwd_from.from_name,
            "channel_post": message.fwd_from.channel_post,
            "post_author": message.fwd_from.post_author,
        }
        if message.fwd_from.from_id:
            fwd_user_id = getattr(message.fwd_from.from_id, 'user_id', None) or getattr(message.fwd_from.from_id, 'channel_id', None)
            data["fwd_from"]["from_id"] = {
                "type": message.fwd_from.from_id.__class__.__name__,
                "id": fwd_user_id
            }
            # Add user data if available in cache
            if user_cache and fwd_user_id and fwd_user_id in user_cache:
                data["fwd_from"]["from_id"]["user"] = user_cache[fwd_user_id]
    
    # Serialize reply info
    if message.reply_to:
        data["reply_to"] = {
            "reply_to_msg_id": message.reply_to.reply_to_msg_id,
            "reply_to_peer_id": None,
            "reply_to_top_id": message.reply_to.reply_to_top_id,
        }
        if hasattr(message.reply_to, 'reply_to_peer_id') and message.reply_to.reply_to_peer_id:
            reply_user_id = getattr(message.reply_to.reply_to_peer_id, 'user_id', None) or getattr(message.reply_to.reply_to_peer_id, 'channel_id', None) or getattr(message.reply_to.reply_to_peer_id, 'chat_id', None)
            data["reply_to"]["reply_to_peer_id"] = {
                "type": message.reply_to.reply_to_peer_id.__class__.__name__,
                "id": reply_user_id
            }
            # Add user data if available in cache
            if user_cache and reply_user_id and reply_user_id in user_cache:
                data["reply_to"]["reply_to_peer_id"]["user"] = user_cache[reply_user_id]
    
    # Serialize media
    if message.media:
        media_type = message.media.__class__.__name__
        data["media"] = {"type": media_type}
        
        if isinstance(message.media, MessageMediaPhoto):
            data["media"]["photo_id"] = message.media.photo.id if message.media.photo else None
            data["media"]["ttl_seconds"] = message.media.ttl_seconds
        elif isinstance(message.media, MessageMediaDocument):
            if message.media.document:
                data["media"]["document_id"] = message.media.document.id
                data["media"]["mime_type"] = message.media.document.mime_type
                data["media"]["size"] = message.media.document.size
                data["media"]["attributes"] = [attr.__class__.__name__ for attr in message.media.document.attributes]
            data["media"]["ttl_seconds"] = message.media.ttl_seconds
        elif isinstance(message.media, MessageMediaWebPage):
            if message.media.webpage and hasattr(message.media.webpage, 'url'):
                data["media"]["url"] = message.media.webpage.url
                if hasattr(message.media.webpage, 'display_url'):
                    data["media"]["display_url"] = message.media.webpage.display_url
                if hasattr(message.media.webpage, 'title'):
                    data["media"]["title"] = message.media.webpage.title
                if hasattr(message.media.webpage, 'description'):
                    data["media"]["description"] = message.media.webpage.description

    
    # Serialize entities (mentions, hashtags, URLs, etc.)
    if message.entities:
        for entity in message.entities:
            entity_data = {
                "type": entity.__class__.__name__,
                "offset": entity.offset,
                "length": entity.length,
            }
            # Add type-specific data
            if hasattr(entity, 'url'):
                entity_data["url"] = entity.url
            if hasattr(entity, 'user_id'):
                entity_data["user_id"] = entity.user_id
                # Add user data if available in cache
                if user_cache and entity.user_id in user_cache:
                    entity_data["user"] = user_cache[entity.user_id]
            if hasattr(entity, 'language'):
                entity_data["language"] = entity.language
            data["entities"].append(entity_data)
    
    # Serialize replies info
    if message.replies:
        data["replies"] = {
            "replies": message.replies.replies,
            "replies_pts": message.replies.replies_pts,
            "comments": message.replies.comments,
            "recent_repliers": [],
            "channel_id": message.replies.channel_id,
            "max_id": message.replies.max_id,
            "read_max_id": message.replies.read_max_id,
        }
    
    # Serialize reactions
    if message.reactions:
        data["reactions"] = {
            "results": [],
            "recent_reactions": [],
        }
        if message.reactions.results:
            for reaction in message.reactions.results:
                reaction_data = {
                    "count": reaction.count,
                }
                # 'chosen' attribute may not exist on all reaction types
                if hasattr(reaction, 'chosen'):
                    reaction_data["chosen"] = reaction.chosen
                # Add reaction emoji/emoticon if available
                if hasattr(reaction, 'reaction'):
                    if hasattr(reaction.reaction, 'emoticon'):
                        reaction_data["emoticon"] = reaction.reaction.emoticon
                    elif hasattr(reaction.reaction, 'document_id'):
                        reaction_data["document_id"] = reaction.reaction.document_id
                data["reactions"]["results"].append(reaction_data)
    
    # Serialize restriction reasons
    if message.restriction_reason:
        for reason in message.restriction_reason:
            data["restriction_reason"].append({
                "platform": reason.platform,
                "reason": reason.reason,
                "text": reason.text,
            })
    
    return data


async def download_history(chat_identifier, from_date=None, to_date=None, enrich_users=False):
    """
    Download chat history gradually while respecting rate limits.
    
    Args:
        chat_identifier: Username, phone number, or chat ID
        from_date: Start date (datetime object)
        to_date: End date (datetime object)
        enrich_users: If True, fetch and include full user information
    """
    if not API_ID or not API_HASH:
        log("Error: API_ID and API_HASH must be set in .env file")
        sys.exit(1)
    
    # Initialize the client
    client = TelegramClient('anon', int(API_ID), API_HASH)
    
    try:
        await client.start(phone=PHONE)
        log("Successfully connected to Telegram!")
        
        # Get the chat entity
        try:
            entity = await client.get_entity(chat_identifier)
            log(f"Found chat: {getattr(entity, 'title', None) or getattr(entity, 'username', chat_identifier)}")
        except Exception as e:
            log(f"Error: Could not find chat '{chat_identifier}': {e}")
            sys.exit(1)
        
        # Prepare output structure
        output = {
            "chat": {
                "id": entity.id,
                "title": getattr(entity, 'title', None),
                "username": getattr(entity, 'username', None),
                "type": entity.__class__.__name__,
            },
            "download_info": {
                "from_date": from_date.isoformat() if from_date else None,
                "to_date": to_date.isoformat() if to_date else None,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "enrich_users": enrich_users,
            },
            "messages": []
        }
        
        # User cache to avoid duplicate requests
        user_cache = {} if enrich_users else None
        
        # Download messages
        total_messages = 0
        request_count = 0
        start_time = time.time()
        
        log(f"Starting download from {from_date or 'beginning'} to {to_date or 'now'}...")
        
        async for message in client.iter_messages(
            entity,
            offset_date=to_date,
            limit=None,  # No limit, we'll fetch everything
            reverse=False  # Start from newest
        ):
            # Check if we've reached the from_date boundary
            if from_date and message.date < from_date:
                break
            
            # Enrich with user data if requested
            if enrich_users:
                # Collect user IDs from this message
                user_ids = set()
                
                # From sender
                if message.from_id and hasattr(message.from_id, 'user_id'):
                    user_ids.add(message.from_id.user_id)
                
                # From forward
                if message.fwd_from and message.fwd_from.from_id and hasattr(message.fwd_from.from_id, 'user_id'):
                    user_ids.add(message.fwd_from.from_id.user_id)
                
                # From reply
                if message.reply_to and hasattr(message.reply_to, 'reply_to_peer_id'):
                    reply_peer = message.reply_to.reply_to_peer_id
                    if reply_peer and hasattr(reply_peer, 'user_id'):
                        user_ids.add(reply_peer.user_id)
                
                # From mentions in entities
                if message.entities:
                    for entity in message.entities:
                        if hasattr(entity, 'user_id'):
                            user_ids.add(entity.user_id)
                
                # Fetch user data for any new users
                for user_id in user_ids:
                    if user_id not in user_cache:
                        try:
                            user = await client.get_entity(user_id)
                            user_cache[user_id] = serialize_user(user)
                            # Small delay to respect rate limits
                            await asyncio.sleep(0.1)
                        except Exception as e:
                            log(f"Warning: Could not fetch user {user_id}: {e}")
                            user_cache[user_id] = None
            
            # Serialize and add message
            output["messages"].append(serialize_message(message, user_cache))
            total_messages += 1
            
            # Rate limiting
            if total_messages % MESSAGES_PER_REQUEST == 0:
                request_count += 1
                
                # Log progress
                if total_messages % 500 == 0:
                    log(f"Downloaded {total_messages} messages...")
                
                # Delay between requests
                await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
                
                # Additional delay every MAX_REQUESTS_PER_MINUTE requests
                if request_count % MAX_REQUESTS_PER_MINUTE == 0:
                    elapsed = time.time() - start_time
                    if elapsed < 60:
                        sleep_time = 60 - elapsed
                        log(f"Rate limit: sleeping for {sleep_time:.1f} seconds...")
                        await asyncio.sleep(sleep_time)
                    start_time = time.time()
        
        output["download_info"]["total_messages"] = total_messages
        log(f"Download complete! Total messages: {total_messages}")
        
        # Output JSON to stdout
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        
    finally:
        await client.disconnect()


async def main():
    parser = argparse.ArgumentParser(
        description='Download Telegram chat/group history with rate limiting.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download last 24 hours from a channel
  python download_history.py @channelname --from 2026-01-03
  
  # Download specific time range
  python download_history.py @channelname --from 2025-01-01 --to 2025-12-31
  
  # Download all history (be patient, this respects rate limits!)
  python download_history.py @channelname
  
  # Save to file
  python download_history.py @channelname > history.json
        """
    )
    parser.add_argument('chat', help='Chat username, phone number, or ID (e.g., @channelname)')
    parser.add_argument('--from', dest='from_date', help='Start date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)')
    parser.add_argument('--to', dest='to_date', help='End date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)')
    parser.add_argument('--enrich-users', action='store_true', help='Fetch and include full user information (slower but more detailed)')
    
    args = parser.parse_args()
    
    # Parse dates
    from_dt = None
    to_dt = None
    
    if args.from_date:
        from_dt = parse_partial_date(args.from_date, to_date=False)
        log(f"From date: {from_dt}")
    
    if args.to_date:
        to_dt = parse_partial_date(args.to_date, to_date=True)
        log(f"To date: {to_dt}")
    
    # Download history
    await download_history(args.chat, from_dt, to_dt, args.enrich_users)


if __name__ == '__main__':
    asyncio.run(main())
