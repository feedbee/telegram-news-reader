import asyncio
import argparse
import sys
from datetime import datetime
from src.config import load_config
from src.ingester import Ingester

async def main():
    parser = argparse.ArgumentParser(description="Telegram Ingest Component")
    parser.add_argument("--mode", choices=["realtime", "backfill", "interval"], required=True, help="Ingest mode")
    parser.add_argument("--from", dest="from_date", help="Start date for interval mode (flexible format: 2026, 2026-01, 2026-01-05, 2026-01-05T10, etc.)")
    parser.add_argument("--to", dest="to_date", help="End date for interval mode (flexible format: 2026, 2026-01, 2026-01-05, 2026-01-05T10, etc.)")
    parser.add_argument("--channels", help="Comma-separated list of channels to override config")
    parser.add_argument("--catch-up", action="store_true", help="Catch up on missed messages before starting realtime mode")

    args = parser.parse_args()

    # Load Config
    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    # Override channels if provided
    if args.channels:
         from src.config import ChannelConfig
         config.channels = [ChannelConfig(channel_id=ch.strip(), name=ch.strip()) for ch in args.channels.split(",")]

    if not config.channels:
        print("Error: No channels configured. Please set CHANNELS env var or config.json.")
        sys.exit(1)

    ingester = Ingester(config)

    try:
        await ingester.start()

        if args.mode == "realtime":
            await ingester.run_realtime(catch_up=args.catch_up)
        elif args.mode == "backfill":
            await ingester.run_backfill()
        elif args.mode == "interval":
            from datetime import timedelta, timezone
            from src.datetime_utils import parse_partial_datetime
            
            # Ensure dates are timezone-aware (UTC)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(hours=24)

            if args.to_date:
                end_date = parse_partial_datetime(args.to_date, is_end=True)
                # If only to is provided -> last 24 hours before to
                start_date = end_date - timedelta(hours=24)

            if args.from_date:
                start_date = parse_partial_datetime(args.from_date, is_end=False)
                # If only from is provided -> from..now (which is default end_date unless overridden above)
                if not args.to_date:
                    end_date = datetime.now(timezone.utc)
            
            await ingester.run_interval(start_date, end_date)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nStopping...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        await ingester.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Already handled in main()

