"""Command-line parsing for offline score fixtures."""

from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO
from zoneinfo import ZoneInfo

from recap.models import Message
from recap.parsers import parse_message
from recap.parsers.base import Score


@dataclass(frozen=True)
class ParseIssue:
    game_slug: str
    message: Message
    reason: str


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
    """Use the post day when a game's puzzle identifier is numeric."""
    if score.game_slug in {"krillion", "timeguessr"}:
        posted = score.posted_at.astimezone(ZoneInfo("America/Los_Angeles"))
        return f"{_MONTHS[posted.month - 1]} {posted.day}"
    return score.puzzle_id


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

    parser = argparse.ArgumentParser(description="Parse offline score fixtures.")
    parser.error("expected the 'fixtures' command")


if __name__ == "__main__":
    raise SystemExit(main())
