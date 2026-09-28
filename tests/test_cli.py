"""CLI scan behavior over Slack fixtures."""

from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pytest

from recap.cli import collect_fixture_facts, collect_scores, main, print_fixture_facts, print_report, resolve_window
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
