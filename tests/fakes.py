"""Test doubles for the Slack reader.

`FakeWebClient` mimics `slack_sdk.WebClient` for the three methods the
reader uses. Responses are loaded from JSON fixture files on disk so
the fixtures stay in the exact shape Slack returns — swapping them for
real captured responses later is a drop-in replacement.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class FakeWebClient:
    """Records every call so tests can assert on arguments and call order."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def conversations_list(self, *, types: str, limit: int, cursor) -> dict:
        self.calls.append(("conversations_list", {"types": types, "limit": limit, "cursor": cursor}))
        return _load("conversations_list.json")

    def conversations_history(self, *, channel: str, limit: int, oldest: str, latest: str, cursor) -> dict:
        self.calls.append(
            (
                "conversations_history",
                {"channel": channel, "limit": limit, "oldest": oldest, "latest": latest, "cursor": cursor},
            )
        )
        if cursor in (None, ""):
            return _load("conversations_history_page1.json")
        return _load("conversations_history_page2.json")

    def conversations_replies(self, *, channel: str, ts: str, limit: int, cursor) -> dict:
        self.calls.append(
            (
                "conversations_replies",
                {"channel": channel, "ts": ts, "limit": limit, "cursor": cursor},
            )
        )
        return _load(f"conversations_replies_{ts.split('.')[0]}.json")
