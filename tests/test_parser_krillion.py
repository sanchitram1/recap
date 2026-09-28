"""Krillion parser — unit tests against hand-crafted messages."""

from __future__ import annotations

from datetime import datetime, timezone

from recap.models import Message
from recap.parsers.krillion import KrillionParser

P = KrillionParser()

# Exactly 7 emoji tokens, matching the pinned grid count.
GRID = ":bubbles::bubbles::izakaya_lantern::squid::bubbles::fish::izakaya_lantern:"


def _msg(text: str, user: str = "UPARKER01", ts: str = "1726477200.000000") -> Message:
    return Message(ts=ts, user=user, text=text, thread_ts=ts)


VALID = f"Krillion #70 :shrimp:\n290\n\n{GRID}"


def test_valid_post_parses_ok():
    r = P.parse(_msg(VALID))
    assert r.status == "ok"
    assert r.score is not None
    assert r.score.game_slug == "krillion"
    assert r.score.puzzle_id == "70"
    assert r.score.score_value == 290
    assert r.score.slack_user_id == "UPARKER01"
    assert r.score.emoji_grid == GRID


def test_valid_post_carries_message_metadata():
    r = P.parse(_msg(VALID, user="USAM001", ts="1726573200.000000"))
    s = r.score
    assert s.slack_user_id == "USAM001"
    assert s.message_ts == "1726573200.000000"
    assert s.thread_ts == "1726573200.000000"
    assert s.posted_at == datetime.fromtimestamp(1726573200, tz=timezone.utc)


def test_game_name_case_insensitive():
    r = P.parse(_msg(f"krillion #70 :shrimp:\n290\n\n{GRID}"))
    assert r.status == "ok"
    assert r.score.puzzle_id == "70"


def test_header_emoji_optional():
    r = P.parse(_msg(f"Krillion #70\n290\n\n{GRID}"))
    assert r.status == "ok"
    assert r.score.score_value == 290


def test_dedupe_key_is_person_game_puzzle():
    r = P.parse(_msg(VALID, user="UPARKER01"))
    assert r.score.dedupe_key == ("UPARKER01", "krillion", "70")


def test_non_krillion_message_is_not_a_score():
    r = P.parse(_msg("Anyone want to grab lunch today?"))
    assert r.status == "not_a_score"
    assert r.score is None


def test_nice_score_reply_is_not_a_score():
    r = P.parse(_msg("Nice score!"))
    assert r.status == "not_a_score"


def test_empty_message_is_not_a_score():
    r = P.parse(_msg(""))
    assert r.status == "not_a_score"


def test_missing_puzzle_number_is_unparseable():
    r = P.parse(_msg(f"Krillion 285\n\n{GRID}"))
    assert r.status == "unparseable"
    assert r.score is None
    assert r.claimed_by == "krillion"


def test_missing_score_line_is_unparseable():
    r = P.parse(_msg(f"Krillion #70 :shrimp:\n\n{GRID}"))
    assert r.status == "unparseable"
    assert "numeric score" in r.reason


def test_missing_emoji_grid_is_unparseable():
    r = P.parse(_msg("Krillion #70 :shrimp:\n290"))
    assert r.status == "unparseable"
    assert "emoji grid" in r.reason


def test_wrong_token_count_in_grid_is_unparseable():
    # Only 6 tokens instead of 7 -> claimed (mentions Krillion) but fails loudly.
    short_grid = ":bubbles::bubbles::izakaya_lantern::squid::bubbles::fish:"
    r = P.parse(_msg(f"Krillion #70 :shrimp:\n290\n\n{short_grid}"))
    assert r.status == "unparseable"
    assert "emoji grid" in r.reason


def test_score_must_be_on_its_own_line():
    r = P.parse(_msg(f"Krillion #70 :shrimp: score 290\n\n{GRID}"))
    assert r.status == "unparseable"


def test_raw_text_always_preserved():
    text = f"Krillion 285\n\n{GRID}"
    r = P.parse(_msg(text))
    assert r.raw_text == text


def test_different_puzzle_ids_parse_independently():
    r1 = P.parse(_msg(f"Krillion #70 :shrimp:\n290\n\n{GRID}"))
    r2 = P.parse(_msg(f"Krillion #71 :shrimp:\n300\n\n{GRID}"))
    assert r1.score.puzzle_id == "70"
    assert r2.score.puzzle_id == "71"
    assert r1.score.dedupe_key != r2.score.dedupe_key
