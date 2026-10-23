"""
rate_limit_service.py — Per-user rate limiting for Leila IT Help Desk Agent.

Window: 60 queries per 5-minute rolling window.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session as DBSession

from models import RateLimitTracking

RATE_LIMIT_QUERIES = 60
RATE_LIMIT_WINDOW_MINUTES = 5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def check_rate_limit(user_id: str, db: DBSession) -> tuple[bool, str]:
    """
    Check whether the user is within rate limit.

    Returns:
        (allowed: bool, message: str)
        allowed=True means the query may proceed.
        allowed=False means the user has exceeded the limit.
    """
    now = _utcnow()
    window_start_cutoff = now - timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)

    record = db.query(RateLimitTracking).filter(
        RateLimitTracking.user_id == user_id
    ).first()

    if record is None:
        # First query from this user — create tracking record
        record = RateLimitTracking(
            user_id=user_id,
            query_count=1,
            window_start_time=now,
            last_query_time=now,
        )
        db.add(record)
        db.commit()
        return True, ""

    # Check if the current window has expired
    if record.window_start_time < window_start_cutoff:
        # Reset window
        record.query_count = 1
        record.window_start_time = now
        record.last_query_time = now
        db.commit()
        return True, ""

    # Within the same window
    if record.query_count >= RATE_LIMIT_QUERIES:
        remaining_seconds = int(
            (record.window_start_time + timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES) - now).total_seconds()
        )
        return False, (
            f"Rate limit exceeded. You have sent {RATE_LIMIT_QUERIES} queries "
            f"in the last {RATE_LIMIT_WINDOW_MINUTES} minutes. "
            f"Please wait {max(remaining_seconds, 1)} seconds before trying again."
        )

    record.query_count += 1
    record.last_query_time = now
    db.commit()
    return True, ""
