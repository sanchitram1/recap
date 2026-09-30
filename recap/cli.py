"""Command-line scan for Slack score recap data."""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import TextIO
from zoneinfo import ZoneInfo

from slack_sdk import WebClient

from recap.models import Message
from recap.parsers import parse_message
from recap.parsers.base import Score
from recap.reader import SlackClient, SlackReader
from recap.scanner import find_score_threads


@dataclass(frozen=True)
class ParseIssue:
    game_slug: str
    message: Message
    reason: str


@dataclass(frozen=True)
class ScanReport:
    channel: str
    oldest: datetime
    latest: datetime
    thread_count: int
    scores: list[Score]
    issues: list[ParseIssue]


@dataclass(frozen=True)
class FixtureFact:
    date: str
    person: str
    game: str
    score: int


_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def fixture_date(score: Score) -> str:
    """Date column for fixture CSV. Krillion posts identify the puzzle by number, so use the post day."""
    if score.game_slug == "krillion":
        posted = score.posted_at.astimezone(ZoneInfo("America/Los_Angeles"))
        return f"{_MONTHS[posted.month - 1]} {posted.day}"
    return score.puzzle_id


def collect_scores(client: SlackClient, *, channel: str, oldest: float, latest: float) -> ScanReport:
    """Fetch matching score threads and parse every message in them."""
    reader = SlackReader(client, channel)
    threads = find_score_threads(reader, oldest=oldest, latest=latest)
    scores: list[Score] = []
    issues: list[ParseIssue] = []

    for score_thread in threads:
        for message in score_thread.thread.all_messages:
            result = parse_message(message)
            if result.status == "ok" and result.score is not None:
                scores.append(result.score)
            elif result.status == "unparseable":
                issues.append(ParseIssue(score_thread.game_slug, message, result.reason))

    return ScanReport(
        channel=channel,
        oldest=datetime.fromtimestamp(oldest, tz=timezone.utc),
        latest=datetime.fromtimestamp(latest, tz=timezone.utc),
        thread_count=len(threads),
        scores=scores,
        issues=issues,
    )


def collect_fixture_facts(path: Path) -> tuple[list[FixtureFact], list[ParseIssue]]:
    data = json.loads(path.read_text())
    rows = data["messages"] if isinstance(data, dict) else data
    facts: list[FixtureFact] = []
    issues: list[ParseIssue] = []

    for index, row in enumerate(rows, start=1):
        person = row.get("person") or row.get("user") or row.get("slack_user_id")
        if not person:
            raise ValueError(f"Fixture message {index} is missing person/user")
        message = Message(
            ts=str(row.get("ts") or f"{index}.000000"),
            user=person,
            text=row["text"],
            thread_ts=row.get("thread_ts"),
        )
        result = parse_message(message)
        if result.status == "ok" and result.score is not None:
            facts.append(
                FixtureFact(
                    date=fixture_date(result.score),
                    person=person,
                    game=result.score.game_slug,
                    score=result.score.score_value,
                )
            )
        elif result.status == "unparseable":
            issues.append(ParseIssue(result.claimed_by, message, result.reason))

    return facts, issues


def print_fixture_facts(facts: list[FixtureFact], output: TextIO | None = None) -> None:
    output = output or sys.stdout
    writer = csv.writer(output)
    writer.writerow(["date", "person", "game", "score"])
    for fact in facts:
        writer.writerow([fact.date, fact.person, fact.game, fact.score])


def print_unparsed(issues: list[ParseIssue], output: TextIO | None = None) -> None:
    """Report messages a parser claimed but could not turn into a score."""
    if not issues:
        return
    output = output or sys.stdout
    print(f"\nDID NOT PARSE {len(issues)} MESSAGES:", file=output)
    for issue in issues:
        text = " ".join(issue.message.text.split())
        print(f"{issue.message.user}: {text}", file=output)


def parse_datetime(value: str) -> datetime:
    """Parse YYYY-MM-DD or an ISO datetime as UTC unless a timezone is supplied."""
    if len(value) == 10:
        parsed = datetime.combine(date.fromisoformat(value), time.min, tzinfo=timezone.utc)
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def resolve_window(*, oldest: str | None, latest: str | None, days: int, now: datetime | None = None) -> tuple[datetime, datetime]:
    latest_dt = parse_datetime(latest) if latest else (now or datetime.now(timezone.utc))
    oldest_dt = parse_datetime(oldest) if oldest else latest_dt - timedelta(days=days)
    if oldest_dt >= latest_dt:
        raise ValueError("--oldest must be before --latest")
    return oldest_dt, latest_dt


def print_report(report: ScanReport, output: TextIO | None = None) -> None:
    output = output or sys.stdout
    print(f"Channel: {report.channel}", file=output)
    print(f"Window: {report.oldest.isoformat()} to {report.latest.isoformat()}", file=output)
    print(f"Score threads: {report.thread_count}", file=output)
    print(f"Parsed scores: {len(report.scores)}", file=output)
    print(f"Unparseable messages: {len(report.issues)}", file=output)

    if report.scores:
        print("\nScores:", file=output)
        for score in sorted(report.scores, key=lambda s: (s.posted_at, s.game_slug, s.slack_user_id)):
            print(
                f"- {score.posted_at.isoformat()} {score.game_slug} "
                f"puzzle={score.puzzle_id} user={score.slack_user_id} score={score.score_value}",
                file=output,
            )

    if report.issues:
        print("\nUnparseable:", file=output)
        for issue in report.issues:
            print(
                f"- {issue.game_slug} ts={issue.message.ts} user={issue.message.user}: {issue.reason}",
                file=output,
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Slack score threads and parse game scores.")
    parser.add_argument("--channel", required=True, help="Slack channel name or ID, for example #clued-in")
    parser.add_argument("--oldest", help="Start date/time, as YYYY-MM-DD or ISO datetime. Defaults to --days before latest.")
    parser.add_argument("--latest", help="End date/time, as YYYY-MM-DD or ISO datetime. Defaults to now.")
    parser.add_argument("--days", type=int, default=7, help="Lookback window when --oldest is omitted. Default: 7")
    parser.add_argument("--token-env", default="SLACK_BOT_TOKEN", help="Environment variable containing the Slack bot token.")
    return parser


def resolve_fixture_paths(patterns: list[str]) -> list[Path]:
    """Expand fixture paths and globs, in match order, without duplicates."""
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if not matches:
            raise ValueError(f"No fixtures matched {pattern}")
        for match in matches:
            path = Path(match)
            key = path.resolve()
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
    return paths


def build_fixtures_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse offline Slack message fixtures into recap facts.")
    parser.add_argument(
        "fixtures",
        nargs="+",
        help="Fixture path or glob, for example tests/fixtures/krillion_*",
    )
    parser.add_argument("--silent", action="store_true", help="Omit the DID NOT PARSE summary.")
    return parser


def main_fixtures(argv: list[str]) -> int:
    parser = build_fixtures_parser()
    args = parser.parse_args(argv)
    facts: list[FixtureFact] = []
    issues: list[ParseIssue] = []
    try:
        for path in resolve_fixture_paths(args.fixtures):
            file_facts, file_issues = collect_fixture_facts(path)
            facts.extend(file_facts)
            issues.extend(file_issues)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    print_fixture_facts(facts)
    if not args.silent:
        print_unparsed(issues)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"fixtures", "fxitures"}:
        return main_fixtures(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)

    token = os.environ.get(args.token_env)
    if not token:
        parser.error(f"{args.token_env} is not set")

    try:
        oldest_dt, latest_dt = resolve_window(oldest=args.oldest, latest=args.latest, days=args.days)
    except ValueError as exc:
        parser.error(str(exc))

    report = collect_scores(
        WebClient(token=token),
        channel=args.channel,
        oldest=oldest_dt.timestamp(),
        latest=latest_dt.timestamp(),
    )
    print_report(report)
    return 1 if report.issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
