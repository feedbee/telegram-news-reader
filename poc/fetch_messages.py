import os
import asyncio
import argparse
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
PHONE = os.getenv('TELEGRAM_PHONE')
CHANNELS = os.getenv('CHANNELS', 'telegram').split(',')

def parse_partial_date(date_str, default_hour=0, default_minute=0, default_second=0, to_date=False):
    """
    Parses a partial date string like '2026', '2026-01', '2026-01-03', '2026-01-03T15:30'
    If to_date is True, it fills missing components to the end of the period (e.g. '2026' -> '2026-12-31T23:59:59')
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
                # For 'from' date, keep it as is (already 0-filled for missing parts)
                return dt.replace(tzinfo=timezone.utc)
            else:
                # For 'to' date, fill upward
                if precision == "year":
                    return datetime(dt.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                elif precision == "month":
                    # Last day of month
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
    raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DDTHH:MM:SS (partial allowed)")

async def main():
    parser = argparse.ArgumentParser(description='Fetch messages from Telegram channels.')
    parser.add_argument('--from', dest='from_date', help='Start date (YYYY-MM-DDTHH:MM:SS partial)')
    parser.add_argument('--to', dest='to_date', help='End date (YYYY-MM-DDTHH:MM:SS partial)')
    args = parser.parse_args()

    if not API_ID or not API_HASH:
        print("Error: API_ID and API_HASH must be set in .env file")
        return

    # Calculate time range
    now = datetime.now(timezone.utc)
    from_dt = parse_partial_date(args.from_date) if args.from_date else now - timedelta(days=1)
    to_dt = parse_partial_date(args.to_date, to_date=True) if args.to_date else now

    print(f"Fetching messages from {from_dt} to {to_dt}")

    # Initialize the client
    client = TelegramClient('anon', int(API_ID), API_HASH)

    await client.start(phone=PHONE)
    
    print("Successfully connected to Telegram!")

    for channel_id in CHANNELS:
        channel_id = channel_id.strip()
        print(f"\nFetching messages from channel: {channel_id}")
        
        try:
            entity = await client.get_entity(channel_id)
            
            # Use offset_date to start fetching from the 'to_dt' (backwards in time)
            # We stop when we reach 'from_dt'
            async for message in client.iter_messages(entity, offset_date=to_dt):
                if message.date < from_dt:
                    break
                
                if message.text:
                    print("-" * 20)
                    print(f"Date: {message.date}")
                    print(f"Message: {message.text}")
        
        except Exception as e:
            print(f"Error fetching messages from {channel_id}: {e}")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
