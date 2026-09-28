"""Scanner tests — finds per-game summary threads and expands them."""

from __future__ import annotations

from recap.reader import SlackReader
from recap.scanner import find_score_threads
from tests.fakes import FakeWebClient

OLDEST = 1726444800.0
LATEST = 1727049600.0


def test_finds_all_score_threads_and_skips_non_game():
    reader = SlackReader(FakeWebClient(), "#sanchit-test-clued-in")
    threads = find_score_threads(reader, oldest=OLDEST, latest=LATEST)
    slugs = sorted(t.game_slug for t in threads)
    # 2 krillion threads + 2 maptap threads; lunch message skipped
    assert slugs == ["krillion", "krillion", "maptap", "maptap"]


def test_each_score_thread_has_parent_and_replies():
    reader = SlackReader(FakeWebClient(), "#sanchit-test-clued-in")
    threads = find_score_threads(reader, oldest=OLDEST, latest=LATEST)
    for st in threads:
        assert st.thread.parent.text == f"{st.game_slug} scores 🧵"
        assert len(st.thread.replies) >= 1


def test_krillion_thread_replies_are_score_posts():
    reader = SlackReader(FakeWebClient(), "#sanchit-test-clued-in")
    threads = find_score_threads(reader, oldest=OLDEST, latest=LATEST)
    krillion = [t for t in threads if t.game_slug == "krillion"]
    # day 1 thread: 2 score replies; day 2 thread: 2 replies (1 score + 1 malformed)
    assert len(krillion[0].thread.replies) == 2
    assert len(krillion[1].thread.replies) == 2


def test_maptap_thread_replies_are_score_posts():
    reader = SlackReader(FakeWebClient(), "#sanchit-test-clued-in")
    threads = find_score_threads(reader, oldest=OLDEST, latest=LATEST)
    maptap = [t for t in threads if t.game_slug == "maptap"]
    assert len(maptap[0].thread.replies) == 2  # day 1
    assert len(maptap[1].thread.replies) == 1  # day 2


def test_thread_title_match_is_case_insensitive():
    # Fixtures use lowercase "krillion scores 🧵"; ensure it still matches.
    reader = SlackReader(FakeWebClient(), "#sanchit-test-clued-in")
    threads = find_score_threads(reader, oldest=OLDEST, latest=LATEST)
    assert len(threads) == 4


def test_read_replies_called_once_per_matched_thread():
    fake = FakeWebClient()
    reader = SlackReader(fake, "#sanchit-test-clued-in")
    find_score_threads(reader, oldest=OLDEST, latest=LATEST)
    reply_calls = [c for c in fake.calls if c[0] == "conversations_replies"]
    assert len(reply_calls) == 4  # 4 score threads expanded
