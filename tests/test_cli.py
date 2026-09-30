"""CLI scan behavior over Slack fixtures."""

from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pytest

from recap.cli import (
    ParseIssue,
    collect_fixture_facts,
    collect_scores,
    main,
    print_fixture_facts,
    print_report,
    print_unparsed,
    resolve_fixture_paths,
    resolve_window,
)
from recap.models import Message
from tests.fakes import FakeWebClient

OLDEST = 1726444800.0
LATEST = 1727049600.0
FIXTURES = Path(__file__).parent / "fixtures"


def test_collect_scores_reports_scores_and_parse_issues():
    report = collect_scores(FakeWebClient(), channel="#sanchit-test-clued-in", oldest=OLDEST, latest=LATEST)

    assert report.thread_count == 4
    assert len(report.scores) == 6
    assert len(report.issues) == 1
    assert report.issues[0].game_slug == "krillion"
    assert "header missing" in report.issues[0].reason


def test_print_report_includes_scores_and_issues():
    report = collect_scores(FakeWebClient(), channel="#sanchit-test-clued-in", oldest=OLDEST, latest=LATEST)
    output = StringIO()

    print_report(report, output)

    text = output.getvalue()
    assert "Parsed scores: 6" in text
    assert "Unparseable messages: 1" in text
    assert "krillion puzzle=70 user=UPARKER01 score=290" in text
    assert "krillion ts=1726997400.000000 user=UALEX001" in text


def test_resolve_window_defaults_to_days_before_latest():
    now = datetime(2026, 9, 28, 22, 0, tzinfo=timezone.utc)

    oldest, latest = resolve_window(oldest=None, latest=None, days=7, now=now)

    assert oldest == datetime(2026, 9, 21, 22, 0, tzinfo=timezone.utc)
    assert latest == now


def test_resolve_window_rejects_inverted_range():
    with pytest.raises(ValueError, match="--oldest must be before --latest"):
        resolve_window(oldest="2026-09-28", latest="2026-09-21", days=7)


def test_krillion_fixture_date_is_post_day_not_puzzle_number():
    facts, _ = collect_fixture_facts(FIXTURES / "krillion_september_23.json")
    kayla = next(fact for fact in facts if fact.person == "Kayla Fedewa" and fact.score == 200)

    assert kayla.date == "September 23"
    assert kayla.game == "krillion"


def test_collect_fixture_facts_from_manual_slack_copy():
    facts, issues = collect_fixture_facts(FIXTURES / "maptap_september_28.json")

    assert issues == []
    assert [(fact.date, fact.person, fact.game, fact.score) for fact in facts] == [
        ("September 28", "Dirk", "maptap", 862),
        ("September 28", "Sanchit Ram Arvind", "maptap", 938),
        ("September 28", "Eva", "maptap", 837),
        ("September 28", "Hannah Turk", "maptap", 895),
    ]


def test_print_fixture_facts_outputs_csv():
    facts, _ = collect_fixture_facts(FIXTURES / "maptap_september_28.json")
    output = StringIO()

    print_fixture_facts(facts, output)

    assert output.getvalue().splitlines() == [
        "date,person,game,score",
        "September 28,Dirk,maptap,862",
        "September 28,Sanchit Ram Arvind,maptap,938",
        "September 28,Eva,maptap,837",
        "September 28,Hannah Turk,maptap,895",
    ]


def test_main_accepts_misspelled_fixtures_alias(capsys):
    result = main(["fxitures", str(FIXTURES / "maptap_september_28.json")])

    assert result == 0
    assert "September 28,Sanchit Ram Arvind,maptap,938" in capsys.readouterr().out


def test_fixtures_reports_unparsed_messages_after_scores(capsys):
    result = main(["fixtures", str(FIXTURES / "krillion_september_21.json")])

    assert result == 0
    out = capsys.readouterr().out
    assert "September 21,Nader,krillion,275" in out
    assert out.index("September 21,Nader,krillion,275") < out.index("DID NOT PARSE 1 MESSAGES:")
    assert "Nader: not sure if this is totally a puzzle, but it’s a new daily game im into https://krillion.io/" in out


def test_fixtures_silent_omits_unparsed_messages(capsys):
    result = main(["fixtures", "--silent", str(FIXTURES / "krillion_september_21.json")])

    assert result == 0
    out = capsys.readouterr().out
    assert "September 21,Nader,krillion,275" in out
    assert "DID NOT PARSE" not in out


def test_fixtures_glob_prints_one_header(capsys):
    result = main(["fixtures", "--silent", str(FIXTURES / "krillion_september_2*.json")])

    assert result == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "date,person,game,score"
    assert lines.count("date,person,game,score") == 1
    assert "September 21,Sanchit Ram Arvind,krillion,245" in lines
    assert "September 22,Sara Verdi,krillion,285" in lines
    assert "DID NOT PARSE" not in lines


def test_fixtures_shell_expanded_paths_share_one_header(capsys):
    result = main(
        [
            "fixtures",
            "--silent",
            str(FIXTURES / "krillion_september_22.json"),
            str(FIXTURES / "krillion_september_21.json"),
        ]
    )

    assert result == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines.count("date,person,game,score") == 1
    assert lines.index("September 22,Sara Verdi,krillion,285") < lines.index("September 21,Sanchit Ram Arvind,krillion,245")


def test_resolve_fixture_paths_sorts_glob_matches():
    paths = resolve_fixture_paths([str(FIXTURES / "krillion_september_2*.json")])

    assert [path.name for path in paths] == [
        "krillion_september_21.json",
        "krillion_september_22.json",
        "krillion_september_23.json",
        "krillion_september_24.json",
        "krillion_september_25.json",
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
