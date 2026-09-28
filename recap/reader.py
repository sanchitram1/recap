"""M1 — Slack channel reader.

Low-level Slack I/O: resolve a channel name to its ID, read top-level
messages in a time window, and read the replies of a single thread.
The scanner (recap.scanner) layers game-aware filtering on top.

Takes a `slack_sdk.WebClient`-like object via dependency injection, so
tests pass a fake client that returns fixture JSON. The live client is
a plain `WebClient(token=...)` constructed once the bot token is ready.
"""

from __future__ import annotations

from typing import Protocol

from .models import Message

PAGE_SIZE = 200


class SlackClient(Protocol):
    """Structural type for the Slack methods we use. `WebClient` satisfies it."""

    def conversations_list(self, *, types: str, limit: int, cursor: str | None) -> dict: ...
    def conversations_history(self, *, channel: str, limit: int, oldest: str, latest: str, cursor: str | None) -> dict: ...
    def conversations_replies(self, *, channel: str, ts: str, limit: int, cursor: str | None) -> dict: ...


class SlackReader:
    def __init__(self, client: SlackClient, channel: str):
        """
        :param channel: channel name with or without leading '#'
        """
        self._client = client
        self._channel_name = channel.lstrip("#")
        self._channel_id: str | None = None

    def resolve_channel(self) -> str:
        """Resolve the channel name to its Slack ID via conversations.list."""
        if self._channel_id is not None:
            return self._channel_id
        cursor: str | None = None
        while True:
            resp = self._client.conversations_list(
                types="public_channel,private_channel",
                limit=PAGE_SIZE,
                cursor=cursor,
            )
            for ch in resp.get("channels", []):
                if ch["name"] == self._channel_name:
                    self._channel_id = ch["id"]
                    return self._channel_id
            cursor = _next_cursor(resp)
            if not cursor:
                break
        raise ValueError(f"Channel #{self._channel_name} not found")

    def read_top_level(self, *, oldest: float, latest: float) -> list[Message]:
        """Read top-level channel messages within [oldest, latest] (Unix epochs)."""
        channel_id = self.resolve_channel()
        messages: list[Message] = []
        cursor: str | None = None
        while True:
            resp = self._client.conversations_history(
                channel=channel_id,
                limit=PAGE_SIZE,
                oldest=str(oldest),
                latest=str(latest),
                cursor=cursor,
            )
            for raw in resp.get("messages", []):
                messages.append(_to_message(raw))
            if not resp.get("has_more"):
                break
            cursor = _next_cursor(resp)
            if not cursor:
                break
        return messages

    def read_replies(self, thread_ts: str) -> list[Message]:
        """Read replies of one thread, excluding the parent (which the caller
        already has from read_top_level)."""
        channel_id = self.resolve_channel()
        replies: list[Message] = []
        cursor: str | None = None
        while True:
            resp = self._client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=PAGE_SIZE,
                cursor=cursor,
            )
            msgs = resp.get("messages", [])
            # conversations.replies returns the parent as the first message.
            for raw in msgs[1:]:
                replies.append(_to_message(raw))
            if not resp.get("has_more"):
                break
            cursor = _next_cursor(resp)
            if not cursor:
                break
        return replies


def _to_message(raw: dict) -> Message:
    return Message(
        ts=raw["ts"],
        user=raw.get("user", ""),
        text=raw.get("text", ""),
        thread_ts=raw.get("thread_ts"),
    )


def _next_cursor(resp: dict) -> str:
    return (resp.get("response_metadata") or {}).get("next_cursor", "") or ""
