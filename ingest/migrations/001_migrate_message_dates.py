#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from pymongo import MongoClient, UpdateOne


def parse_iso_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None

    # Handle trailing Z (UTC) which fromisoformat does not accept
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def build_updates(doc: Dict[str, Any]) -> Optional[UpdateOne]:
    updates: Dict[str, Any] = {}

    date_val = doc.get("date")
    if isinstance(date_val, str):
        parsed = parse_iso_datetime(date_val)
        if parsed is not None:
            updates["date"] = parsed

    edit_val = doc.get("edit_date")
    if isinstance(edit_val, str):
        parsed = parse_iso_datetime(edit_val)
        if parsed is not None:
            updates["edit_date"] = parsed

    if not updates:
        return None

    return UpdateOne({"_id": doc["_id"]}, {"$set": updates})


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate message date fields from ISO strings to MongoDB Date")
    parser.add_argument("--uri", default=None, help="MongoDB URI (defaults to MONGODB_URI env)")
    parser.add_argument("--batch-size", type=int, default=1000, help="Bulk update batch size")
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes, only report counts")
    args = parser.parse_args()

    mongo_uri = args.uri
    if not mongo_uri:
        import os
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/telegram-news-reader?authSource=admin")

    client = MongoClient(mongo_uri)
    db = client.get_database()
    collection = db["messages"]

    query = {
        "$or": [
            {"date": {"$type": "string"}},
            {"edit_date": {"$type": "string"}},
        ]
    }

    cursor = collection.find(query, projection={"date": 1, "edit_date": 1})

    ops: List[UpdateOne] = []
    processed = 0
    updated = 0

    for doc in cursor:
        processed += 1
        op = build_updates(doc)
        if op is None:
            continue
        ops.append(op)

        if len(ops) >= args.batch_size:
            if not args.dry_run:
                result = collection.bulk_write(ops, ordered=False)
                updated += result.modified_count
            else:
                updated += len(ops)
            ops = []

    if ops:
        if not args.dry_run:
            result = collection.bulk_write(ops, ordered=False)
            updated += result.modified_count
        else:
            updated += len(ops)

    print(f"Processed: {processed}")
    print(f"Updated:   {updated}")
    if args.dry_run:
        print("Dry run: no changes written.")


if __name__ == "__main__":
    main()
