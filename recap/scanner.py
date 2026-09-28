"""Scanner — finds per-game summary threads and expands them.

Flow (per the spec):
  1. Read top-level messages in a time window (a day, or a week).
  2. Match each top-level message against a game's summary-thread title
     pattern (e.g. "krillion scores 🧵", "maptap scores 🧵").
  3. For each match, expand the thread (parent + replies).
  4. Return ScoreThread(game_slug, Thread) pairs — one per matched thread.

The parser then consumes every message in each ScoreThread.
"""

from __future__ import annotations

from recap.models import Message, ScoreThread, Thread
from recap.parsers import GAMES
from recap.reader import SlackReader


def find_score_threads(
    reader: SlackReader,
    *,
    oldest: float,
    latest: float,
    games=GAMES,
) -> list[ScoreThread]:
    """Find and expand all per-game summary threads in [oldest, latest]."""
    top_level = reader.read_top_level(oldest=oldest, latest=latest)
    results: list[ScoreThread] = []
    for msg in top_level:
        slug = _match_thread_title(msg, games)
        if slug is None:
            continue
        replies = reader.read_replies(msg.ts)
        results.append(
            ScoreThread(
                game_slug=slug,
                thread=Thread(channel_id=reader.resolve_channel(), parent=msg, replies=replies),
            )
        )
    return results


def _match_thread_title(message: Message, games) -> str | None:
    """Return the slug of the game whose thread-title pattern matches, or None."""
    for parser in games:
        if parser.THREAD_TITLE.search(message.text):
            return parser.slug
    return None
