"""Parser framework — turn raw Slack messages into structured scores.

Each game ships its own parser implementing `GameParser`. The registry
`GAMES` maps slug -> parser instance. `parse_message` dispatches a
message across all registered parsers and returns the best result.

Parse outcomes:
  - "ok"          : recognized as a score for this game, fully parsed
  - "not_a_score" : this parser does not claim the message (wrong game)
  - "unparseable" : this parser DOES claim the message (recognized the
                    game) but could not extract a valid score. The run
                    continues; these messages are reported afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from recap.models import Message

ParseStatus = Literal["ok", "not_a_score", "unparseable"]


@dataclass(frozen=True)
class Score:
    """A successfully parsed game score — the unit we aggregate and store."""

    game_slug: str
    puzzle_id: str
    slack_user_id: str
    score_value: int
    message_ts: str
    thread_ts: str | None
    posted_at: datetime
    raw_text: str
    emoji_grid: str

    @property
    def dedupe_key(self) -> tuple[str, str, str]:
        return (self.slack_user_id, self.game_slug, self.puzzle_id)


@dataclass(frozen=True)
class ParseResult:
    status: ParseStatus
    score: Score | None = None
    reason: str = ""
    raw_text: str = ""
    claimed_by: str = ""


class GameParser(Protocol):
    """Per-game parser. `slug` identifies the game; `parse` extracts a score."""

    slug: str

    def parse(self, message: Message) -> ParseResult: ...
