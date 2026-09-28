"""Krillion score parser.

Expected message format (from real #clued-in posts):

    Krillion #70 :shrimp:
    290

    :bubbles::bubbles::izakaya_lantern::squid::bubbles::fish:izakaya_lantern:

Three required components:
  1. Header line starting with "Krillion #<puzzle_number>" (case-insensitive).
     A trailing emoji like :shrimp: is decorative and optional.
  2. A line containing only the numeric score.
  3. An emoji grid line — exactly 7 :emoji: tokens in sequence.

If the header doesn't match -> not_a_score (not a Krillion post).
If the header matches but any component is missing or the grid isn't
exactly 7 tokens -> unparseable (fail loudly).
"""

from __future__ import annotations

import re

from recap.models import Message
from recap.parsers.base import ParseResult, Score

SLUG = "krillion"

# Loose recognition: the word "Krillion" anywhere in the first line,
# but NOT the thread-title form "krillion scores 🧵" (that's a title,
# not a score post). If this matches but the strict header doesn't,
# the post is claimed but malformed -> unparseable (fail loudly).
_CLAIMS = re.compile(r"\bkrillion\b(?!\s+scores\s+🧵)", re.IGNORECASE)
# "Krillion #70" possibly followed by decorative emoji/whitespace.
_HEADER = re.compile(r"^\s*krillion\s+#(\d+)\b", re.IGNORECASE)
# A line that is just digits (the score).
_SCORE_LINE = re.compile(r"^\s*(\d+)\s*$")
# Krillion grid is exactly 7 :emoji: tokens.
_EMOJI_GRID = re.compile(r"^(?::[a-z0-9_]+:){7}\s*$")


class KrillionParser:
    slug = SLUG
    # Top-level summary thread title: "krillion scores 🧵" (case-insensitive).
    THREAD_TITLE = re.compile(r"\bkrillion\s+scores\s+🧵", re.IGNORECASE)

    def parse(self, message: Message) -> ParseResult:
        text = message.text
        lines = text.split("\n")
        first = next((ln.strip() for ln in lines if ln.strip()), "")

        if not _CLAIMS.search(first):
            return ParseResult(
                status="not_a_score",
                reason="first line does not mention 'Krillion'",
                raw_text=text,
            )

        header = _HEADER.match(first)
        if not header:
            return ParseResult(
                status="unparseable",
                reason="recognized Krillion post but header missing '#<puzzle_number>'",
                raw_text=text,
                claimed_by=SLUG,
            )
        puzzle_id = header.group(1)

        score_value = _find_score(lines)
        if score_value is None:
            return ParseResult(
                status="unparseable",
                reason="recognized Krillion post but no numeric score line found",
                raw_text=text,
                claimed_by=SLUG,
            )

        emoji_grid = _find_emoji_grid(lines)
        if emoji_grid is None:
            return ParseResult(
                status="unparseable",
                reason="recognized Krillion post but emoji grid is not exactly 7 tokens",
                raw_text=text,
                claimed_by=SLUG,
            )

        return ParseResult(
            status="ok",
            score=Score(
                game_slug=SLUG,
                puzzle_id=puzzle_id,
                slack_user_id=message.user,
                score_value=score_value,
                message_ts=message.ts,
                thread_ts=message.thread_ts,
                posted_at=message.posted_at,
                raw_text=text,
                emoji_grid=emoji_grid,
            ),
            raw_text=text,
            claimed_by=SLUG,
        )


def _find_score(lines: list[str]) -> int | None:
    for ln in lines[1:]:
        m = _SCORE_LINE.match(ln)
        if m:
            return int(m.group(1))
    return None


def _find_emoji_grid(lines: list[str]) -> str | None:
    for ln in lines:
        s = ln.strip()
        if _EMOJI_GRID.match(s):
            return s
    return None
