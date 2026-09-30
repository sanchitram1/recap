"""TimeGuessr parser tests against captured share-message formats."""

from __future__ import annotations

from datetime import datetime, timezone

from recap.models import Message
from recap.parsers.timeguessr import TimeGuessrParser

P = TimeGuessrParser()

ROUNDS = (
    ":one: :trophy:7,461 · :date: 9y · :earth_africa: 3795ft\n"
    ":two: :trophy:1,012 · :date: 20y · :earth_africa: 3969.7mi\n"
    ":three: :trophy:2,501 · :date: 16y · :earth_africa: 1862.2mi\n"
    ":four: :trophy:4,759 · :date: 15y · :earth_africa: 920.5mi\n"
    ":five: :trophy:3,998 · :date: 29y · :earth_africa: 311.6mi"
)
VALID = f"TimeGuessr #1216 — 19,731/50,000\n{ROUNDS}\nhttps://timeguessr.com\nabsolutely terrible"


def _msg(text: str, user: str = "Parker Stafford", ts: str = "1790625000.000000") -> Message:
    return Message(ts=ts, user=user, text=text, thread_ts=ts)


def test_valid_post_parses_ok():
    result = P.parse(_msg(VALID))

    assert result.status == "ok"
    assert result.score is not None
    assert result.score.game_slug == "timeguessr"
    assert result.score.puzzle_id == "1216"
    assert result.score.score_value == 19731
    assert result.score.emoji_grid == ROUNDS


def test_valid_post_carries_message_metadata():
    result = P.parse(_msg(VALID, user="Sragvi Vadali"))
    score = result.score

    assert score.slack_user_id == "Sragvi Vadali"
    assert score.message_ts == "1790625000.000000"
    assert score.thread_ts == "1790625000.000000"
    assert score.posted_at == datetime.fromtimestamp(1790625000, tz=timezone.utc)


def test_plain_game_name_is_not_a_score():
    result = P.parse(_msg("timeguessr"))

    assert result.status == "not_a_score"


def test_malformed_claimed_header_is_unparseable():
    result = P.parse(_msg(f"TimeGuessr #1216 — nope/50,000\n{ROUNDS}"))

    assert result.status == "unparseable"
    assert result.claimed_by == "timeguessr"
    assert "header" in result.reason


def test_missing_round_is_unparseable():
    result = P.parse(_msg("TimeGuessr #1216 — 15,733/50,000\n" + "\n".join(ROUNDS.splitlines()[:4])))

    assert result.status == "unparseable"
    assert "five" in result.reason


def test_rounds_must_be_in_order():
    lines = ROUNDS.splitlines()
    lines[0], lines[1] = lines[1], lines[0]

    result = P.parse(_msg("TimeGuessr #1216 — 19,731/50,000\n" + "\n".join(lines)))

    assert result.status == "unparseable"
