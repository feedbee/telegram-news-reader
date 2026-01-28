
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from .storage import Storage
from .summarizer import Summarizer
from .config import config
# Reuse partial datetime parsing from ingest (assuming we can import or copy it)
# To avoid complex cross-component imports in this specific structure (monorepo but separate containers/envs usually)
# I will replicate the utility for self-containment of this component, or import if path allows.
# Given they are in separate folders but same repo, PYTHONPATH adjustment might be needed. 
# For robustness in Docker/Phase 2, I'll copy the logic or assume shared lib in future.
# For now, I'll implement a simplified parser here.

def parse_partial_datetime(date_str: str, is_end: bool = False) -> datetime:
    """
    Simplified partial date parsing relative to UTC.
    """
    # ... (simplified version of ingest's util)
    # Using basic fromisoformat as fallback or flexible parser
    # Implementation similar to ingest's logic for consistency
    import calendar
    
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H",
        "%Y-%m-%d",
        "%Y-%m",
        "%Y",
    ]
    parsed = None
    matched_format = None
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            matched_format = fmt
            break
        except ValueError:
            continue
            
    if not parsed:
        raise ValueError(f"Invalid date format: {date_str}")

    year = parsed.year
    month = parsed.month if matched_format != "%Y" else (12 if is_end else 1)
    
    if matched_format in ["%Y", "%Y-%m"]:
        day = calendar.monthrange(year, month)[1] if is_end else 1
    else:
        day = parsed.day

    if matched_format in ["%Y", "%Y-%m", "%Y-%m-%d"]:
        hour, minute, second, microsecond = (23, 59, 59, 999999) if is_end else (0, 0, 0, 0)
    elif matched_format == "%Y-%m-%dT%H":
        hour = parsed.hour
        minute, second, microsecond = (59, 59, 999999) if is_end else (0, 0, 0)
    elif matched_format == "%Y-%m-%dT%H:%M":
        hour, minute = parsed.hour, parsed.minute
        second, microsecond = (59, 999999) if is_end else (0, 0)
    else:
        hour, minute, second = parsed.hour, parsed.minute, parsed.second
        microsecond = parsed.microsecond

    return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc)


class CLI:
    def __init__(self):
        self.storage = Storage()
        self.summarizer = Summarizer()

    def run(self):
        parser = argparse.ArgumentParser(description="Transform Component - CLI")
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Summarize command
        summarize_parser = subparsers.add_parser("summarize", help="Generate a summary of messages")
        summarize_parser.add_argument("--channel-id", required=True, help="Telegram Channel ID (e.g. @channel)")
        summarize_parser.add_argument("--from", dest="from_date", help="Start date (flexible format)")
        summarize_parser.add_argument("--to", dest="to_date", help="End date (flexible format)")
        summarize_parser.add_argument("--last-message-id", type=int, help="Start from after this message ID")
        summarize_parser.add_argument("--format", choices=["MD", "JSON"], default="MD", help="Output format")
        summarize_parser.set_defaults(func=self.handle_summarize)
        
        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            sys.exit(1)

        try:
            args.func(args)
        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)

    def handle_summarize(self, args):
        # Determine filters
        messages = []
        msg_metadata = {"total": 0, "processed": 0}
        
        if args.last_message_id:
            # Based on ID
            total = self.storage.get_total_message_count_from_id(args.channel_id, args.last_message_id)
            messages = self.storage.get_messages_from_id(
                args.channel_id, 
                args.last_message_id, 
                limit=config.max_messages_per_request
            )
        elif args.from_date:
            # Based on Interval
            from_dt = parse_partial_datetime(args.from_date, is_end=False)
            to_dt = parse_partial_datetime(args.to_date, is_end=True) if args.to_date else datetime.now(timezone.utc)
            
            total = self.storage.get_total_message_count(args.channel_id, from_dt, to_dt)
            messages = self.storage.get_messages_by_interval(
                args.channel_id, 
                from_dt, 
                to_dt, 
                limit=config.max_messages_per_request
            )
        else:
            # Default behavior: Last 24 hours
            to_dt = datetime.now(timezone.utc)
            from_dt = to_dt - timedelta(hours=config.default_lookback_hours)
            
            total = self.storage.get_total_message_count(args.channel_id, from_dt, to_dt)
            messages = self.storage.get_messages_by_interval(
                args.channel_id, 
                from_dt, 
                to_dt, 
                limit=config.max_messages_per_request
            )
        
        msg_metadata["total"] = total
        msg_metadata["processed"] = len(messages)

        # Summarize
        summary_text = self.summarizer.summarize(messages, channel_id=args.channel_id)
        
        # Prepare Metadata info for consistent use
        last_id = None
        last_ts_str = None
        
        if messages:
            last_msg = messages[-1]
            last_id = last_msg.get("message_id")
            last_ts = last_msg.get("date")
            # Handle date string vs object for timestamp
            last_ts_str = last_ts.isoformat() if hasattr(last_ts, 'isoformat') else str(last_ts)

        # JSON Output
        if args.format == "JSON":
            output = {
                "summary": summary_text,
                "last_message_id": last_id,
                "last_message_timestamp": last_ts_str,
                "messages": msg_metadata,
                "request": {
                    "channel_id": args.channel_id,
                    "from": args.from_date,
                    "to": args.to_date,
                    "last_message_id": args.last_message_id,
                    "format": args.format
                }
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        
        # MD Output
        else:
            # Metadata to STDERR (standardizing on all meta info)
            print(f"Messages Total: {msg_metadata['total']}", file=sys.stderr)
            print(f"Messages Processed: {msg_metadata['processed']}", file=sys.stderr)
            print(f"Last Message ID: {last_id if last_id is not None else 'N/A'}", file=sys.stderr)
            print(f"Last Message Timestamp: {last_ts_str if last_ts_str is not None else 'N/A'}", file=sys.stderr)
            
            # Summary to STDOUT
            print(summary_text)

def main():
    cli = CLI()
    cli.run()

if __name__ == "__main__":
    main()
