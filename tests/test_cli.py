"""CLI scan behavior over Slack fixtures."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

from recap.cli import (
    ParseIssue,
    collect_fixture_facts,
    main,
    print_fixture_facts,
    print_unparsed,
    resolve_fixture_paths,
)
from recap.models import Message

FIXTURES = Path(__file__).parent / "fixtures" / "slack_copies" / "parsed"


def test_krillion_fixture_date_is_post_day_not_puzzle_number():
    facts, _ = collect_fixture_facts(FIXTURES / "krillion_sep_29.json")
    kayla = next(fact for fact in facts if fact.person == "Kayla Fedewa" and fact.score == 275)

    assert kayla.date == "September 29"
    assert kayla.game == "krillion"


def test_collect_fixture_facts_from_manual_slack_copy():
    facts, issues = collect_fixture_facts(FIXTURES / "maptap_sep_28.json")

    assert issues == []
    assert [(fact.date, fact.person, fact.game, fact.score) for fact in facts] == [
        ("September 28", "Dirk", "maptap", 862),
        ("September 28", "Sanchit Ram Arvind", "maptap", 938),
        ("September 28", "Eva", "maptap", 837),
        ("September 28", "Hannah Turk", "maptap", 895),
        ("September 28", "Parker Stafford", "maptap", 849),
        ("September 28", "Sragvi Vadali", "maptap", 872),
        ("September 28", "Nader", "maptap", 839),
        ("September 28", "Nathan Sutherland", "maptap", 895),
        ("September 28", "Hannah Turk", "maptap", 910),
    ]


def test_collect_fixture_facts_parses_timeguessr_scores():
    facts, issues = collect_fixture_facts(FIXTURES / "timeguessr_sep_29.json")

    assert issues == []
    assert len(facts) == 12
    assert ("September 29", "AZ Nicdao", "timeguessr", 44843) in [
        (fact.date, fact.person, fact.game, fact.score) for fact in facts
    ]


def test_print_fixture_facts_outputs_csv():
    facts, _ = collect_fixture_facts(FIXTURES / "maptap_sep_28.json")
    output = StringIO()

    print_fixture_facts(facts, output)

    assert output.getvalue().splitlines() == [
        "date,person,game,score",
        "September 28,Dirk,maptap,862",
        "September 28,Sanchit Ram Arvind,maptap,938",
        "September 28,Eva,maptap,837",
        "September 28,Hannah Turk,maptap,895",
        "September 28,Parker Stafford,maptap,849",
        "September 28,Sragvi Vadali,maptap,872",
        "September 28,Nader,maptap,839",
        "September 28,Nathan Sutherland,maptap,895",
        "September 28,Hannah Turk,maptap,910",
    ]


def test_main_accepts_misspelled_fixtures_alias(capsys):
    result = main(["fxitures", str(FIXTURES / "maptap_sep_28.json")])

    assert result == 0
    assert "September 28,Sanchit Ram Arvind,maptap,938" in capsys.readouterr().out


def write_fixture_with_unparsed_message(tmp_path: Path) -> Path:
    path = tmp_path / "krillion.json"
    path.write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "person": "Nader",
                        "ts": "1790591160.000000",
                        "text": "Krillion #75 :shrimp:\n275\n:bubbles::fish::squid::bubbles::fish::fish::fish:",
                    },
                    {
                        "person": "Nader",
                        "ts": "1790591220.000000",
                        "text": "Krillion is great but this result is malformed",
                    },
                ]
            }
        )
    )
    return path


def test_fixtures_reports_unparsed_messages_after_scores(capsys, tmp_path):
    result = main(["fixtures", str(write_fixture_with_unparsed_message(tmp_path))])

    assert result == 0
    out = capsys.readouterr().out
    assert "September 28,Nader,krillion,275" in out
    assert out.index("September 28,Nader,krillion,275") < out.index("DID NOT PARSE 1 MESSAGES:")
    assert "Nader: Krillion is great but this result is malformed" in out


def test_fixtures_silent_omits_unparsed_messages(capsys, tmp_path):
    result = main(["fixtures", "--silent", str(write_fixture_with_unparsed_message(tmp_path))])

    assert result == 0
    out = capsys.readouterr().out
    assert "September 28,Nader,krillion,275" in out
    assert "DID NOT PARSE" not in out


def test_fixtures_glob_prints_one_header(capsys):
    result = main(["fixtures", "--silent", str(FIXTURES / "krillion_sep_2*.json")])

    assert result == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "date,person,game,score"
    assert lines.count("date,person,game,score") == 1
    assert "September 28,Sanchit Ram Arvind,krillion,310" in lines
    assert "September 29,Kayla Fedewa,krillion,275" in lines
    assert "DID NOT PARSE" not in lines


def test_fixtures_shell_expanded_paths_share_one_header(capsys):
    result = main(
        [
            "fixtures",
            "--silent",
            str(FIXTURES / "krillion_sep_29.json"),
            str(FIXTURES / "krillion_sep_28.json"),
        ]
    )

    assert result == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines.count("date,person,game,score") == 1
    assert lines.index("September 29,Kayla Fedewa,krillion,275") < lines.index(
        "September 28,Sanchit Ram Arvind,krillion,310"
    )


def test_resolve_fixture_paths_sorts_glob_matches():
    paths = resolve_fixture_paths([str(FIXTURES / "krillion_sep_2*.json")])

    assert [path.name for path in paths] == [
        "krillion_sep_28.json",
        "krillion_sep_29.json",
    ]


def test_fixtures_glob_with_no_matches_errors():
    with pytest.raises(SystemExit):
        main(["fixtures", str(FIXTURES / "no_such_game_*.json")])


def test_print_unparsed_lists_messages_from_either_parser():
    issues = [
        ParseIssue(
            "krillion",
            Message(ts="1.000000", user="Nader", text="i LOVE Krillion"),
            "recognized Krillion post but header missing '#<puzzle_number>'",
        ),
        ParseIssue(
            "maptap",
            Message(ts="2.000000", user="Sara", text="Final score:\nnope"),
            "recognized maptap post but no 'Final score: <n>' line",
        ),
    ]
    output = StringIO()

    print_unparsed(issues, output)

    assert output.getvalue().splitlines() == [
        "",
        "DID NOT PARSE 2 MESSAGES:",
        "Nader: i LOVE Krillion",
        "Sara: Final score: nope",
    ]
