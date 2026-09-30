from __future__ import annotations

from datetime import date

from recap import jsonify


def test_parse_copied_thread_outputs_manual_fixture_shape():
    raw = """Nader
9:00 AM
:thread: maptap

Nader
9:16 AM
www.maptap.gg September 25
99:fire: 100:dart: 75:joy: 86:mortar_board: 84:grin:
Final score: 859

Sanchit Ram Arvind
9:37 AM
OK, so for Panama City, I put it exactly where San Jose Costa Rica was
"""

    messages = jsonify.parse_copied_messages(raw)
    fixture = jsonify.to_fixture(
        messages,
        copied_date=date(2026, 9, 25),
        timezone_name="America/Los_Angeles",
        base_ts=1.0,
        ts_step=60.0,
    )

    assert fixture["source"] == "manual Slack copy"
    assert fixture["thread"] == {
        "person": "Nader",
        "text": ":thread: maptap",
        "reply_count": 2,
    }
    assert fixture["messages"][0]["person"] == "Nader"
    assert fixture["messages"][0]["ts"] == "1790352960.000000"
    assert fixture["messages"][0]["text"] == (
        "www.maptap.gg September 25\n"
        "99:fire: 100:dart: 75:joy: 86:mortar_board: 84:grin:\n"
        "Final score: 859"
    )
    assert fixture["messages"][1]["text"] == "OK, so for Panama City, I put it exactly where San Jose Costa Rica was"


def test_parse_inline_headers_without_date_uses_synthetic_timestamps():
    raw = """Dirk 1:46 PM
www.maptap.gg September 28
79:clap: 83:star2: 92:trophy: 90:crown: 82:star2:
Final score: 862

Eva 2:30 PM
www.maptap.gg September 28
80:hugging_face: 78:grin: 89:tada: 87:mortar_board: 80:sun_with_face:
Final score: 837
"""

    messages = jsonify.parse_copied_messages(raw)
    fixture = jsonify.to_fixture(
        messages,
        copied_date=None,
        timezone_name="America/Los_Angeles",
        base_ts=100.0,
        ts_step=30.0,
    )

    assert "thread" not in fixture
    assert [message["person"] for message in fixture["messages"]] == ["Dirk", "Eva"]
    assert [message["ts"] for message in fixture["messages"]] == ["100.000000", "130.000000"]


def test_parse_bracketed_slack_copy_with_glued_headers():
    raw = """Ana Castillo (she/her)  [7:50 AM]
Geoguessr :thread:
13 repliesAna Castillo (she/her)  [7:50 AM]
TimeGuessr #1213 — 41,817/50,000

:one: :trophy:8,338 · :date: 7y · :earth_africa: 1.6mi

https://timeguessr.com
TimeGuessrTimeGuessr - the game that tests both your geography and history knowledge.timeguessr.comEitan Ghelman  [8:14 AM]
This is a fun one!

TimeGuessr #1213 — 47,246/50,000

:one: :trophy:9,510 · :date: 3y · :earth_africa: 2.7mi
Parker Stafford  [11:29 AM]
TimeGuessr #1213 — 31,432/50,000
[11:30 AM]wow the second one i rely thought it was dc
"""

    messages = jsonify.parse_copied_messages(raw)
    fixture = jsonify.to_fixture(
        messages,
        copied_date=None,
        timezone_name="America/Los_Angeles",
        base_ts=1.0,
        ts_step=60.0,
    )

    assert fixture["thread"] == {
        "person": "Ana Castillo (she/her)",
        "text": "Geoguessr :thread:",
        "reply_count": 4,
    }
    assert [message["person"] for message in fixture["messages"]] == [
        "Ana Castillo (she/her)",
        "Eitan Ghelman",
        "Parker Stafford",
        "Parker Stafford",
    ]
    assert fixture["messages"][0]["text"].startswith("TimeGuessr #1213")
    assert "This is a fun one!" in fixture["messages"][1]["text"]
    assert fixture["messages"][3]["text"] == "wow the second one i rely thought it was dc"


def test_bracketed_author_does_not_absorb_previous_multiline_message():
    raw = """Meredith Mende  [9:00 AM]
oh snap,
GAME ON
Eunice  [9:22 AM]
www.maptap.gg September 29
90:crown: 95:sports_medal: 55:shushing_face: 91:crown: 80:sun_with_face:
Final score: 808
"""

    messages = jsonify.parse_copied_messages(raw)

    assert [(message.person, message.text) for message in messages] == [
        ("Meredith Mende", "oh snap,\nGAME ON"),
        (
            "Eunice",
            (
                "www.maptap.gg September 29\n"
                "90:crown: 95:sports_medal: 55:shushing_face: 91:crown: 80:sun_with_face:\n"
                "Final score: 808"
            ),
        ),
    ]


def test_parse_maptap_copy_splits_same_author_inline_followup():
    raw = """Nader  [10:16 AM]
:thread: maptap
10 repliesNader  [10:16 AM]
www.maptap.gg September 25
99:fire: 100:dart: 75:joy: 86:mortar_board: 84:grin:
Final score: 859Parker Stafford  [10:28 AM]
www.maptap.gg September 25
89:tada: 86:mortar_board: 78:sun_with_face: 77:hugging_face: 73:grin:
Final score: 781Sanchit Ram Arvind  [10:36 AM]
www.maptap.gg September 25
90:crown: 84:grin: 90:crown: 100:dart: 78:joy:
Final score: 888[10:37 AM]OK, so for Panama City, I put it exactly where San Jose Costa Rica was

so, i kinda knew exactly where Costa Rica was after that haha
"""

    messages = jsonify.parse_copied_messages(raw)
    fixture = jsonify.to_fixture(
        messages,
        copied_date=None,
        timezone_name="America/Los_Angeles",
        base_ts=1.0,
        ts_step=60.0,
    )

    assert fixture["thread"] == {
        "person": "Nader",
        "text": ":thread: maptap",
        "reply_count": 4,
    }
    assert [message["person"] for message in fixture["messages"]] == [
        "Nader",
        "Parker Stafford",
        "Sanchit Ram Arvind",
        "Sanchit Ram Arvind",
    ]
    assert fixture["messages"][0]["text"].endswith("Final score: 859")
    assert fixture["messages"][1]["text"].endswith("Final score: 781")
    assert fixture["messages"][2]["text"].endswith("Final score: 888")
    assert fixture["messages"][3]["text"].startswith("OK, so for Panama City")
