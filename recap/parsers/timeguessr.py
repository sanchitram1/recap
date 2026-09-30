"""Parser for TimeGuessr share messages."""

from __future__ import annotations

import re

from recap.models import Message
from recap.parsers.base import ParseResult, Score

SLUG = "timeguessr"

_CLAIMS = re.compile(r"^\s*timeguessr\s+#", re.IGNORECASE)
_HEADER = re.compile(
    r"^\s*timeguessr\s+#(?P<puzzle>\d+)\s*[—–-]\s*"
    r"(?P<score>\d{1,3}(?:,\d{3})*)\s*/\s*50,000\b",
    re.IGNORECASE,
)
_ROUND = re.compile(
    r"^:(?P<number>one|two|three|four|five):\s+"
    r":trophy:[\d,]+\s+·\s+:date:\s*\d+y\s+·\s+:earth_africa:\s*\S+\s*$",
    re.IGNORECASE,
)
_ROUND_ORDER = ("one", "two", "three", "four", "five")


class TimeGuessrParser:
    slug = SLUG
    THREAD_TITLE = re.compile(r"^\s*timeguessr\s*$", re.IGNORECASE)

    def parse(self, message: Message) -> ParseResult:
        text = message.text
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        first = lines[0] if lines else ""

        if not _CLAIMS.match(first):
            return ParseResult(
                status="not_a_score",
                reason="first line is not a TimeGuessr score header",
                raw_text=text,
            )

        header = _HEADER.match(first)
        if header is None:
            return ParseResult(
                status="unparseable",
                reason="recognized TimeGuessr post but score header is malformed",
                raw_text=text,
                claimed_by=SLUG,
            )

        round_lines = _find_rounds(lines[1:])
        if round_lines is None:
            return ParseResult(
                status="unparseable",
                reason="recognized TimeGuessr post but five ordered round lines were not found",
                raw_text=text,
                claimed_by=SLUG,
            )

        return ParseResult(
            status="ok",
            score=Score(
                game_slug=SLUG,
                puzzle_id=header.group("puzzle"),
                slack_user_id=message.user,
                score_value=int(header.group("score").replace(",", "")),
                message_ts=message.ts,
                thread_ts=message.thread_ts,
                posted_at=message.posted_at,
                raw_text=text,
                emoji_grid="\n".join(round_lines),
            ),
            raw_text=text,
            claimed_by=SLUG,
        )


def _find_rounds(lines: list[str]) -> list[str] | None:
    rounds: list[str] = []
    round_numbers: list[str] = []
    for line in lines:
        match = _ROUND.match(line)
        if match:
            rounds.append(line)
            round_numbers.append(match.group("number").lower())

    if round_numbers != list(_ROUND_ORDER):
        return None
    return rounds
