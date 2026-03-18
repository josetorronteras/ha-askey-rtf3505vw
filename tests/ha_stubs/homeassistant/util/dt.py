"""Minimal stub for homeassistant.util.dt."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)
