"""Normalized data structures for messages and threads.

These are the reader's output shape. The parser (M2) consumes `Message`
instances; storage (M3) persists parsed scores. Keeping the reader's
output decoupled from Slack's raw JSON lets us swap fixtures for live
data without touching downstream code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Message:
    """A single Slack message, normalized from the raw API response."""

    ts: str
    user: str
    text: str
    thread_ts: str | None = None

    @property
    def posted_at(self) -> datetime:
        """Calendar instant parsed from the Slack `ts` (Unix epoch string)."""
        return datetime.fromtimestamp(float(self.ts), tz=timezone.utc)

    @property
    def is_thread_parent(self) -> bool:
        return self.thread_ts is not None and self.thread_ts == self.ts


@dataclass
class Thread:
    """A top-level message plus its replies (possibly empty)."""

    channel_id: str
    parent: Message
    replies: list[Message] = field(default_factory=list)

    @property
    def all_messages(self) -> list[Message]:
        """Parent first, then replies — every message in the thread."""
        return [self.parent, *self.replies]


@dataclass
class ScoreThread:
    """A summary thread matched to a specific game (e.g. 'krillion scores 🧵')."""

    game_slug: str
    thread: Thread
