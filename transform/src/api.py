
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from .storage import Storage
from .summarizer import Summarizer
from .config import config
from .cli import parse_partial_datetime # Reusing for consistency

import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Transform API", version="0.1.0")

storage = Storage()
summarizer = Summarizer()

class MessagesMetadata(BaseModel):
    total: int
    processed: int

class SummarizeRequestInfo(BaseModel):
    channel_id: str
    from_date: Optional[str] = None # 'from' is reserved in python
    to_date: Optional[str] = None   # 'to' is reserved in python (not really but clearer)
    last_message_id: Optional[int] = None
    format: str

class SummarizeResponse(BaseModel):
    summary: str
    last_message_id: int
    last_message_timestamp: str
    messages: MessagesMetadata
    request: Dict[str, Any]

@app.get("/summarize")
async def summarize(
    response: Response,
    channel_id: str = Query(..., description="Telegram Channel ID"),
    from_date: Optional[str] = Query(None, alias="from", description="Start date (flexible format)"),
    to_date: Optional[str] = Query(None, alias="to", description="End date (flexible format)"),
    last_message_id: Optional[int] = Query(None, alias="last_message_id", description="Start after this message ID"),
    format: str = Query("MD", regex="^(MD|JSON)$", description="Output format: MD or JSON")
):
    try:
        # Determine filters
        messages = []
        msg_metadata = {"total": 0, "processed": 0}
        
        if last_message_id:
            total = storage.get_total_message_count_from_id(channel_id, last_message_id)
            messages = storage.get_messages_from_id(
                channel_id, 
                last_message_id, 
                limit=config.max_messages_per_request
            )
        elif from_date:
            from_dt = parse_partial_datetime(from_date, is_end=False)
            to_dt = parse_partial_datetime(to_date, is_end=True) if to_date else datetime.now(timezone.utc)
            
            total = storage.get_total_message_count(channel_id, from_dt, to_dt)
            messages = storage.get_messages_by_interval(
                channel_id, 
                from_dt, 
                to_dt, 
                limit=config.max_messages_per_request
            )
        else:
            # Default: Last 24h
            to_dt = datetime.now(timezone.utc)
            from_dt = to_dt - timedelta(hours=config.default_lookback_hours)
            
            total = storage.get_total_message_count(channel_id, from_dt, to_dt)
            messages = storage.get_messages_by_interval(
                channel_id, 
                from_dt, 
                to_dt, 
                limit=config.max_messages_per_request
            )

        msg_metadata["total"] = total
        msg_metadata["processed"] = len(messages)

        # Prepare Metadata info for consistent use
        last_id = None
        last_ts_str = None
        
        if messages:
            last_msg = messages[-1]
            last_id = last_msg.get("message_id")
            last_ts = last_msg.get("date")
            # Handle date string vs object for timestamp
            last_ts_str = last_ts.isoformat() if hasattr(last_ts, 'isoformat') else str(last_ts)

        # Set Standardized Headers X-META-xxx
        response.headers["X-META-MESSAGES-TOTAL"] = str(total)
        response.headers["X-META-MESSAGES-PROCESSED"] = str(len(messages))
        response.headers["X-META-LAST-MESSAGE-ID"] = str(last_id) if last_id is not None else "N/A"
        response.headers["X-META-LAST-MESSAGE-TIMESTAMP"] = last_ts_str if last_ts_str is not None else "N/A"

        # Summarize
        summary_text = summarizer.summarize(messages, channel_id=channel_id)
        
        if format == "JSON":
            return {
                "summary": summary_text,
                "last_message_id": last_id,
                "last_message_timestamp": last_ts_str,
                "messages": msg_metadata,
                "request": {
                    "channel_id": channel_id,
                    "from": from_date,
                    "to": to_date,
                    "last_message_id": last_message_id,
                    "format": format
                }
            }
        else:
            # MD output
            return Response(
                content=summary_text, 
                media_type="text/markdown",
                headers={
                    "X-META-MESSAGES-TOTAL": str(total),
                    "X-META-MESSAGES-PROCESSED": str(len(messages)),
                    "X-META-LAST-MESSAGE-ID": str(last_id) if last_id is not None else "N/A",
                    "X-META-LAST-MESSAGE-TIMESTAMP": last_ts_str if last_ts_str is not None else "N/A"
                }
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Internal Server Error")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
