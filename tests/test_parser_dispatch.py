"""Parser registry dispatch — tests for `parse_message`."""

from __future__ import annotations

from recap.models import Message
from recap.parsers import parse_message

GRID = ":bubbles::bubbles::izakaya_lantern::squid::bubbles::fish::izakaya_lantern:"


def _msg(text: str, user: str = "UPARKER01", ts: str = "1726477200.000000") -> Message:
    return Message(ts=ts, user=user, text=text, thread_ts=ts)


VALID = f"Krillion #70 :shrimp:\n290\n\n{GRID}"


def test_dispatch_returns_ok_for_valid_krillion():
    r = parse_message(_msg(VALID))
    assert r.status == "ok"
    assert r.score.game_slug == "krillion"


def test_dispatch_returns_not_a_score_for_non_game():
    r = parse_message(_msg("Anyone want to grab lunch?"))
    assert r.status == "not_a_score"


def test_dispatch_fails_loudly_for_unparseable():
    r = parse_message(_msg(f"Krillion 285\n\n{GRID}"))
    assert r.status == "unparseable"
    assert r.claimed_by == "krillion"


def test_dispatch_treats_thread_title_as_not_a_score():
    r = parse_message(_msg("krillion scores 🧵"))
    assert r.status == "not_a_score"
