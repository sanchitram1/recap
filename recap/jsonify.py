"""Convert copied Slack thread text into recap fixture JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TIME_RE = re.compile(r"^\s*(?P<time>\d{1,2}:\d{2}\s*(?:AM|PM))\s*$", re.IGNORECASE)
INLINE_HEADER_RE = re.compile(r"^\s*(?P<person>.+?)\s+(?P<time>\d{1,2}:\d{2}\s*(?:AM|PM))\s*$", re.IGNORECASE)
NAME_TOKEN = r"(?:[A-Z][A-Za-z.'-]*|\([^)]+\))"
BRACKET_HEADER_RE = re.compile(
    rf"(?P<person>{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,6}})\s+\[(?P<time>\d{{1,2}}:\d{{2}}\s*(?:[AaPp][Mm]))\]",
)
INLINE_TIMESTAMP_RE = re.compile(r"\[(?P<time>\d{1,2}:\d{2}\s*(?:[AaPp][Mm]))\]")
THREAD_TITLE_RE = re.compile(r"(?i)(?:\bscores\b|:thread:|:world_map:|🧵)")


@dataclass(frozen=True)
class CopiedMessage:
    person: str
    time_text: str | None
    text: str


def parse_copied_messages(text: str) -> list[CopiedMessage]:
    """Split a Slack copy/paste transcript into message blocks."""
    normalized = _normalize_copy_text(text)
    bracket_messages = _parse_bracket_headers(normalized)
    if bracket_messages:
        return _split_inline_timestamp_messages(bracket_messages)

    lines = normalized.split("\n")
    messages: list[CopiedMessage] = []
    i = 0

    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue

        header = _read_header(lines, i)
        if header is None:
            i += 1
            continue

        person, time_text, body_start = header
        body: list[str] = []
        i = body_start
        while i < len(lines):
            if _read_header(lines, i) is not None:
                break
            body.append(lines[i].rstrip())
            i += 1

        messages.append(CopiedMessage(person=person, time_text=time_text, text=_clean_body("\n".join(body))))

    return _split_inline_timestamp_messages([message for message in messages if message.text])


def _normalize_copy_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    return re.sub(
        r"(\b\d+\s+replies)(?=[^\n]{1,120}?\d{1,2}:\d{2}\s*(?:AM|PM)\])",
        r"\1\n",
        normalized,
        flags=re.IGNORECASE,
    )


def _parse_bracket_headers(text: str) -> list[CopiedMessage]:
    matches = list(BRACKET_HEADER_RE.finditer(text))
    messages: list[CopiedMessage] = []
    for index, match in enumerate(matches):
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        messages.append(
            CopiedMessage(
                person=match.group("person").strip(),
                time_text=_normalize_time(match.group("time")),
                text=_clean_body(text[body_start:body_end]),
            )
        )
    return [message for message in messages if message.text]


def _split_inline_timestamp_messages(messages: list[CopiedMessage]) -> list[CopiedMessage]:
    split_messages: list[CopiedMessage] = []
    for message in messages:
        matches = list(INLINE_TIMESTAMP_RE.finditer(message.text))
        if not matches:
            split_messages.append(message)
            continue

        first_text = _clean_body(message.text[: matches[0].start()])
        if first_text:
            split_messages.append(CopiedMessage(person=message.person, time_text=message.time_text, text=first_text))

        for index, match in enumerate(matches):
            body_start = match.end()
            body_end = matches[index + 1].start() if index + 1 < len(matches) else len(message.text)
            text = _clean_body(message.text[body_start:body_end])
            if text:
                split_messages.append(
                    CopiedMessage(person=message.person, time_text=_normalize_time(match.group("time")), text=text)
                )

    return split_messages


def _clean_body(text: str) -> str:
    lines = [line.rstrip() for line in text.strip().split("\n")]
    lines = [line for line in lines if not re.fullmatch(r"\d+\s+replies", line.strip(), flags=re.IGNORECASE)]
    return "\n".join(lines).strip()


def _read_header(lines: list[str], i: int) -> tuple[str, str | None, int] | None:
    """Return (person, time, next_index) if lines[i:] starts a Slack header."""
    line = lines[i].strip()
    if not line:
        return None

    inline = INLINE_HEADER_RE.match(line)
    if inline and i + 1 < len(lines) and lines[i + 1].strip():
        return inline.group("person").strip(), _normalize_time(inline.group("time")), i + 1

    if i + 1 < len(lines):
        time_match = TIME_RE.match(lines[i + 1])
        if time_match:
            return line, _normalize_time(time_match.group("time")), i + 2

    return None


def _normalize_time(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().upper())


def to_fixture(
    messages: list[CopiedMessage],
    *,
    copied_date: date | None,
    timezone_name: str,
    base_ts: float,
    ts_step: float,
) -> dict:
    if not messages:
        raise ValueError("No Slack messages found. Expected 'Person' followed by '9:41 AM' headers.")

    thread: CopiedMessage | None = None
    fixture_messages = messages
    if len(messages) > 1 and THREAD_TITLE_RE.search(messages[0].text):
        thread = messages[0]
        fixture_messages = messages[1:]

    output: dict = {"source": "manual Slack copy"}
    if thread is not None:
        output["thread"] = {
            "person": thread.person,
            "text": thread.text,
            "reply_count": len(fixture_messages),
        }
    output["messages"] = [
        {
            "person": message.person,
            "ts": _message_ts(
                message,
                index=index,
                copied_date=copied_date,
                timezone_name=timezone_name,
                base_ts=base_ts,
                ts_step=ts_step,
            ),
            "text": message.text,
        }
        for index, message in enumerate(fixture_messages)
    ]
    return output


def _message_ts(
    message: CopiedMessage,
    *,
    index: int,
    copied_date: date | None,
    timezone_name: str,
    base_ts: float,
    ts_step: float,
) -> str:
    if copied_date is not None and message.time_text is not None:
        parsed_time = datetime.strptime(message.time_text, "%I:%M %p").time()
        posted_at = datetime.combine(copied_date, parsed_time, tzinfo=ZoneInfo(timezone_name))
        return f"{posted_at.timestamp():.6f}"
    return f"{base_ts + index * ts_step:.6f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert copied Slack thread text into recap fixture JSON.")
    parser.add_argument("input", nargs="?", type=Path, help="Text file containing copied Slack messages. Defaults to stdin.")
    parser.add_argument("--date", dest="copied_date", type=date.fromisoformat, help="Message date as YYYY-MM-DD.")
    parser.add_argument("--timezone", default="America/Los_Angeles", help="Timezone for --date times. Default: America/Los_Angeles.")
    parser.add_argument("--base-ts", type=float, default=1.0, help="Synthetic first timestamp when --date is omitted.")
    parser.add_argument("--ts-step", type=float, default=60.0, help="Synthetic timestamp spacing when --date is omitted.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    raw = args.input.read_text() if args.input else sys.stdin.read()
    try:
        messages = parse_copied_messages(raw)
        fixture = to_fixture(
            messages,
            copied_date=args.copied_date,
            timezone_name=args.timezone,
            base_ts=args.base_ts,
            ts_step=args.ts_step,
        )
    except ValueError as exc:
        parser.error(str(exc))

    json.dump(fixture, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0
