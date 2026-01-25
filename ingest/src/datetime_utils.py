from datetime import datetime, timezone, timedelta
from typing import Optional
import calendar


def parse_partial_datetime(date_str: str, is_end: bool = False) -> datetime:
    """
    Parse a partial datetime string and fill in missing components.
    
    For start dates (is_end=False): Missing components default to the beginning (01, 00:00:00)
    For end dates (is_end=True): Missing components default to the end (last day, 23:59:59.999)
    
    Examples:
        parse_partial_datetime("2026-01", is_end=False) -> 2026-01-01T00:00:00
        parse_partial_datetime("2026-01", is_end=True) -> 2026-01-31T23:59:59.999
        parse_partial_datetime("2026-01-05T10", is_end=True) -> 2026-01-05T10:59:59.999
    
    Args:
        date_str: Partial datetime string
        is_end: If True, fill missing components with end-of-period values
    
    Returns:
        datetime object with timezone UTC
    """
    # Try to parse different formats in order of specificity
    formats = [
        "%Y-%m-%dT%H:%M:%S",  # Full datetime
        "%Y-%m-%dT%H:%M",     # Date + hour + minute
        "%Y-%m-%dT%H",        # Date + hour
        "%Y-%m-%d",           # Date only
        "%Y-%m",              # Year + month
        "%Y",                 # Year only
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
    
    if parsed is None:
        raise ValueError(f"Invalid date format: {date_str}. Use formats like: 2026, 2026-01, 2026-01-05, 2026-01-05T10, etc.")
    
    # Fill in missing components based on whether this is a start or end date
    year = parsed.year
    month = parsed.month if matched_format != "%Y" else (12 if is_end else 1)
    
    # Determine the day
    if matched_format in ["%Y", "%Y-%m"]:
        if is_end:
            # Last day of the month
            day = calendar.monthrange(year, month)[1]
        else:
            day = 1
    else:
        day = parsed.day
    
    # Determine time components
    if matched_format in ["%Y", "%Y-%m", "%Y-%m-%d"]:
        # No time specified
        hour = 23 if is_end else 0
        minute = 59 if is_end else 0
        second = 59 if is_end else 0
        microsecond = 999999 if is_end else 0
    elif matched_format == "%Y-%m-%dT%H":
        # Hour specified, but not minute/second
        hour = parsed.hour
        minute = 59 if is_end else 0
        second = 59 if is_end else 0
        microsecond = 999999 if is_end else 0
    elif matched_format == "%Y-%m-%dT%H:%M":
        # Hour and minute specified, but not second
        hour = parsed.hour
        minute = parsed.minute
        second = 59 if is_end else 0
        microsecond = 999000 if is_end else 0
    else:
        # Full datetime specified
        hour = parsed.hour
        minute = parsed.minute
        second = parsed.second
        microsecond = parsed.microsecond
    
    return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc)
