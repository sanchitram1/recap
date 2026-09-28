"""M1 reader tests — against fixture JSON that mirrors real Slack responses."""

from __future__ import annotations

from datetime import datetime, timezone

from recap.reader import SlackReader
from tests.fakes import FakeWebClient

CHANNEL_ID = "C08TESTCLUED"
OLDEST = 1726444800.0
LATEST = 1727049600.0


def test_resolve_channel_strips_hash_and_returns_id():
    reader = SlackReader(FakeWebClient(), "#sanchit-test-clued-in")
    assert reader.resolve_channel() == CHANNEL_ID


def test_resolve_channel_works_without_hash():
    reader = SlackReader(FakeWebClient(), "sanchit-test-clued-in")
    assert reader.resolve_channel() == CHANNEL_ID


def test_resolve_channel_caches_id_so_list_is_called_once():
    fake = FakeWebClient()
    reader = SlackReader(fake, "#sanchit-test-clued-in")
    reader.resolve_channel()
    reader.resolve_channel()
    list_calls = [c for c in fake.calls if c[0] == "conversations_list"]
    assert len(list_calls) == 1


def test_resolve_channel_raises_for_missing_channel():
    reader = SlackReader(FakeWebClient(), "#does-not-exist")
    try:
        reader.resolve_channel()
    except ValueError as e:
        assert "does-not-exist" in str(e)
    else:
        raise AssertionError("expected ValueError for missing channel")


def test_read_top_level_returns_all_messages_across_pages():
    reader = SlackReader(FakeWebClient(), "#sanchit-test-clued-in")
    messages = reader.read_top_level(oldest=OLDEST, latest=LATEST)
    assert len(messages) == 5  # 3 on page 1 + 2 on page 2


def test_read_top_level_passes_oldest_and_latest_to_history():
    fake = FakeWebClient()
    reader = SlackReader(fake, "#sanchit-test-clued-in")
    reader.read_top_level(oldest=OLDEST, latest=LATEST)
    history_calls = [c for c in fake.calls if c[0] == "conversations_history"]
    assert len(history_calls) == 2
    first = history_calls[0][1]
    assert first["oldest"] == str(OLDEST)
    assert first["latest"] == str(LATEST)
    assert first["channel"] == CHANNEL_ID


def test_read_top_level_paginates_history_using_cursor():
    fake = FakeWebClient()
    reader = SlackReader(fake, "#sanchit-test-clued-in")
    reader.read_top_level(oldest=OLDEST, latest=LATEST)
    history_calls = [c for c in fake.calls if c[0] == "conversations_history"]
    assert history_calls[0][1]["cursor"] is None
    assert history_calls[1][1]["cursor"] == "dXNlcjpVMDYxTkZUVDI9"


def test_read_top_level_preserves_ts_and_text():
    reader = SlackReader(FakeWebClient(), "#sanchit-test-clued-in")
    messages = reader.read_top_level(oldest=OLDEST, latest=LATEST)
    first = messages[0]
    assert first.ts == "1726477200.000000"
    assert first.text == "krillion scores 🧵"
    assert first.posted_at == datetime.fromtimestamp(1726477200, tz=timezone.utc)


def test_read_replies_excludes_parent():
    fake = FakeWebClient()
    reader = SlackReader(fake, "#sanchit-test-clued-in")
    replies = reader.read_replies("1726477200.000000")
    assert len(replies) == 2
    assert all(r.ts != "1726477200.000000" for r in replies)


def test_read_replies_called_with_thread_ts():
    fake = FakeWebClient()
    reader = SlackReader(fake, "#sanchit-test-clued-in")
    reader.read_replies("1726477800.000000")
    reply_calls = [c for c in fake.calls if c[0] == "conversations_replies"]
    assert len(reply_calls) == 1
    assert reply_calls[0][1]["ts"] == "1726477800.000000"
    assert reply_calls[0][1]["channel"] == CHANNEL_ID
