"""Maptap parser — unit tests against the real example format."""

from __future__ import annotations

from datetime import datetime, timezone

from recap.models import Message
from recap.parsers.maptap import MaptapParser

P = MaptapParser()

# Exactly 5 map tokens, matching the pinned count.
MAP = "99:dart: 98:dart: 82:star2: 87:mortar_board: 80:sparkles:"


def _msg(text: str, user: str = "UPARKER01", ts: str = "1790184619.488549") -> Message:
    return Message(ts=ts, user=user, text=text, thread_ts=ts)


VALID = f"September 23\n{MAP}\nFinal score: 862"


def test_valid_post_parses_ok():
    r = P.parse(_msg(VALID))
    assert r.status == "ok"
    assert r.score is not None
    assert r.score.game_slug == "maptap"
    assert r.score.puzzle_id == "September 23"
    assert r.score.score_value == 862
    assert r.score.emoji_grid == MAP


def test_valid_post_strips_maptap_url_from_date():
    r = P.parse(_msg(f"www.maptap.gg September 28\n{MAP}\nFinal score: 862"))
    assert r.status == "ok"
    assert r.score.puzzle_id == "September 28"


def test_valid_post_ignores_chatter_before_maptap_url():
    r = P.parse(
        _msg(
            "man they realy love indonesia\n"
            "www.maptap.gg September 28\n"
            "81:sparkles: 84:grin: 90:crown: 96:fire: 72:face_with_open_eyes_and_hand_over_mouth:\n"
            "Final score: 849"
        )
    )

    assert r.status == "ok"
    assert r.score.puzzle_id == "September 28"
    assert r.score.score_value == 849


def test_final_score_allows_slack_link_preview_trailing_text():
    r = P.parse(_msg(f"www.maptap.gg September 28\n{MAP}\nFinal score: 862:dart:MapTap Daily Geography Game"))
    assert r.status == "ok"
    assert r.score.score_value == 862


def test_valid_post_carries_message_metadata():
    r = P.parse(_msg(VALID, user="USAM001", ts="1790184619.488549"))
    s = r.score
    assert s.slack_user_id == "USAM001"
    assert s.message_ts == "1790184619.488549"
    assert s.posted_at == datetime.fromtimestamp(1790184619.488549, tz=timezone.utc)


def test_dedupe_key_is_person_game_puzzle():
    r = P.parse(_msg(VALID, user="UPARKER01"))
    assert r.score.dedupe_key == ("UPARKER01", "maptap", "September 23")


def test_non_maptap_message_is_not_a_score():
    r = P.parse(_msg("Anyone want to grab lunch today?"))
    assert r.status == "not_a_score"
    assert r.score is None


def test_krillion_message_is_not_a_score_for_maptap():
    r = P.parse(_msg("Krillion #70 :shrimp:\n290\n\n:bubbles::fish:"))
    assert r.status == "not_a_score"


def test_empty_message_is_not_a_score():
    r = P.parse(_msg(""))
    assert r.status == "not_a_score"


def test_missing_final_score_is_unparseable():
    r = P.parse(_msg(f"September 23\n{MAP}"))
    assert r.status == "unparseable"
    assert "Final score" in r.reason
    assert r.claimed_by == "maptap"


def test_missing_emoji_map_is_unparseable():
    r = P.parse(_msg("September 23\nFinal score: 862"))
    assert r.status == "unparseable"
    assert "emoji map" in r.reason


def test_missing_date_line_is_unparseable():
    r = P.parse(_msg(f"{MAP}\nFinal score: 862"))
    assert r.status == "unparseable"
    assert "date" in r.reason.lower()


def test_wrong_token_count_in_map_is_unparseable():
    # Only 3 tokens instead of 5 -> claimed (map-like) but fails loudly.
    short_map = "99:dart: 98:dart: 82:star2:"
    r = P.parse(_msg(f"September 23\n{short_map}\nFinal score: 862"))
    assert r.status == "unparseable"
    assert "5 tokens" in r.reason


def test_final_score_without_number_is_unparseable():
    r = P.parse(_msg(f"September 23\n{MAP}\nFinal score:"))
    assert r.status == "unparseable"


def test_raw_text_always_preserved():
    r = P.parse(_msg(VALID))
    assert r.raw_text == VALID


def test_different_dates_parse_independently():
    a = P.parse(_msg(f"September 23\n{MAP}\nFinal score: 862"))
    b = P.parse(_msg(f"September 24\n{MAP}\nFinal score: 700"))
    assert a.score.puzzle_id == "September 23"
    assert b.score.puzzle_id == "September 24"
    assert a.score.dedupe_key != b.score.dedupe_key
