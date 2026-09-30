"""Normalized data structures consumed by score parsers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Message:
    """A single message loaded from an offline fixture."""

    ts: str
    user: str
    text: str
    thread_ts: str | None = None

    @property
    def posted_at(self) -> datetime:
        """Calendar instant parsed from the Slack `ts` (Unix epoch string)."""
        return datetime.fromtimestamp(float(self.ts), tz=timezone.utc)
