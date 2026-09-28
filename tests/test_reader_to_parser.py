"""End-to-end: scanner -> parser -> expected scores.

Wires M1 (reader) + scanner + M2 (parser) against the fixture set.
When real fixtures replace the hand-crafted ones, this test must still
pass (or we update expectations deliberately).
"""

from __future__ import annotations

from recap.parsers import parse_message
from recap.reader import SlackReader
from recap.scanner import find_score_threads
from tests.fakes import FakeWebClient

OLDEST = 1726444800.0
LATEST = 1727049600.0


def _all_score_threads():
    reader = SlackReader(FakeWebClient(), "#sanchit-test-clued-in")
    return find_score_threads(reader, oldest=OLDEST, latest=LATEST)


def test_valid_scores_extracted_from_summary_threads():
    threads = _all_score_threads()
    scores: dict[tuple[str, str, str], int] = {}
    for st in threads:
        for message in st.thread.all_messages:
            r = parse_message(message)
            if r.status == "ok":
                scores[r.score.dedupe_key] = r.score.score_value

    assert scores == {
        ("UPARKER01", "krillion", "70"): 290,
        ("USAM001", "krillion", "70"): 245,
        ("UPARKER01", "krillion", "71"): 300,
        ("UPARKER01", "maptap", "September 16"): 862,
        ("USAM001", "maptap", "September 16"): 700,
        ("UALEX001", "maptap", "September 22"): 750,
    }


def test_summary_thread_parents_are_not_scores():
    """The 'krillion scores 🧵' parent message itself is not a score post."""
    threads = _all_score_threads()
    for st in threads:
        r = parse_message(st.thread.parent)
        assert r.status == "not_a_score", st.thread.parent.text


def test_malformed_reply_fails_loudly():
    threads = _all_score_threads()
    krillion_day2 = next(t for t in threads if t.game_slug == "krillion" and t.thread.parent.ts == "1726995600.000000")
    malformed = next(m for m in krillion_day2.thread.replies if m.text == "Krillion 285")
    r = parse_message(malformed)
    assert r.status == "unparseable"
    assert r.claimed_by == "krillion"


def test_lunch_message_never_reaches_parser():
    """The scanner skips non-game top-level messages entirely."""
    threads = _all_score_threads()
    parents = {t.thread.parent.text for t in threads}
    assert "Anyone want to grab lunch today?" not in parents
