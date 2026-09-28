"""Maptap score parser.

Expected message format (from real #clued-in posts):

    September 23
    99:dart: 98:dart: 82:star2: 87:mortar_board: 80:sparkles:
    Final score: 862

Three required components:
  1. A date line (the puzzle identifier), e.g. "September 23".
  2. An emoji map line: exactly 5 "<number>:<emoji>:" tokens, space-separated.
  3. A "Final score: <number>" line.

Claim markers (two-stage, fail loudly): the message is claimed if it has
"Final score:" OR a map-like line (2+ map tokens). If claimed but any
component is missing or the map isn't exactly 5 tokens -> unparseable.
"""

from __future__ import annotations

import re

from recap.models import Message
from recap.parsers.base import ParseResult, Score

SLUG = "maptap"

_TOKEN = r"\d+:[a-zA-Z0-9_]+:"
_CLAIMS = re.compile(r"final\s+score\s*:", re.IGNORECASE)
# Loose map line: 2+ tokens — used to claim a message as maptap-like.
_LOOSE_MAP = re.compile(rf"^{_TOKEN}(?:\s+{_TOKEN})+\s*$")
# Strict map line: exactly 5 tokens — required for a valid score.
_MAP_LINE = re.compile(rf"^{_TOKEN}(?:\s+{_TOKEN}){{4}}\s*$")
_FINAL_SCORE = re.compile(r"^\s*final\s+score\s*:\s*(\d+)\b.*$", re.IGNORECASE)
_PUZZLE_PREFIX = re.compile(r"^(?:https?://)?(?:www\.)?maptap\.gg\s+", re.IGNORECASE)
# A line that is neither a map line nor a final-score line (the date/puzzle).
_NOT_MAP_OR_SCORE = re.compile(
    rf"^(?!{_TOKEN}(?:\s+{_TOKEN})*\s*$)(?!\s*final\s+score\s*:\s*\d+\b.*$).+",
    re.IGNORECASE,
)


class MaptapParser:
    slug = SLUG
    # Top-level summary thread title: "maptap scores 🧵" (case-insensitive).
    THREAD_TITLE = re.compile(r"\bmaptap\s+scores\s+🧵", re.IGNORECASE)

    def parse(self, message: Message) -> ParseResult:
        text = message.text
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

        has_final_score = bool(_CLAIMS.search(text))
        has_loose_map = any(_LOOSE_MAP.match(ln) for ln in lines)
        if not has_final_score and not has_loose_map:
            return ParseResult(
                status="not_a_score",
                reason="no 'Final score:' line and no emoji map line",
                raw_text=text,
            )

        score_value = _find(lines, _FINAL_SCORE)
        if score_value is None:
            return ParseResult(
                status="unparseable",
                reason="recognized maptap post but no 'Final score: <n>' line",
                raw_text=text,
                claimed_by=SLUG,
            )

        emoji_map = _find_line(lines, _MAP_LINE)
        if emoji_map is None:
            return ParseResult(
                status="unparseable",
                reason="recognized maptap post but emoji map is not exactly 5 tokens",
                raw_text=text,
                claimed_by=SLUG,
            )

        puzzle_id = _find_line(lines, _NOT_MAP_OR_SCORE)
        if puzzle_id is None:
            return ParseResult(
                status="unparseable",
                reason="recognized maptap post but no date/puzzle line",
                raw_text=text,
                claimed_by=SLUG,
            )

        return ParseResult(
            status="ok",
            score=Score(
                game_slug=SLUG,
                puzzle_id=_normalize_puzzle_id(puzzle_id),
                slack_user_id=message.user,
                score_value=int(score_value.group(1)),
                message_ts=message.ts,
                thread_ts=message.thread_ts,
                posted_at=message.posted_at,
                raw_text=text,
                emoji_grid=emoji_map,
            ),
            raw_text=text,
            claimed_by=SLUG,
        )


def _find(lines: list[str], pattern: re.Pattern) -> re.Match | None:
    for ln in lines:
        m = pattern.match(ln)
        if m:
            return m
    return None


def _find_line(lines: list[str], pattern: re.Pattern) -> str | None:
    for ln in lines:
        if pattern.match(ln):
            return ln
    return None


def _normalize_puzzle_id(value: str) -> str:
    return _PUZZLE_PREFIX.sub("", value).strip()
