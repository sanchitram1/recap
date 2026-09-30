"""Parser registry and message dispatch.

`GAMES` is the fixed list of registered parsers. `parse_message` runs a
message through every parser and returns the best result:

  - If one parser returns "ok", use it.
  - Else if any parser returns "unparseable" (it claimed the message but
    failed), return that so the caller can report it after parsed scores.
  - Else (all "not_a_score"), return not_a_score.
"""

from __future__ import annotations

from recap.models import Message
from recap.parsers.base import GameParser, ParseResult
from recap.parsers.krillion import KrillionParser
from recap.parsers.maptap import MaptapParser

# Fixed list — grows as new game parsers are added.
GAMES: list[GameParser] = [
    KrillionParser(),
    MaptapParser(),
]


def parse_message(message: Message) -> ParseResult:
    not_a_score: ParseResult | None = None
    unparseable: ParseResult | None = None

    for parser in GAMES:
        result = parser.parse(message)
        if result.status == "ok":
            return result
        if result.status == "unparseable" and unparseable is None:
            unparseable = result
        elif result.status == "not_a_score" and not_a_score is None:
            not_a_score = result

    if unparseable is not None:
        return unparseable
    return not_a_score or ParseResult(status="not_a_score", reason="no parser claimed this message", raw_text=message.text)
