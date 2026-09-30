---
name: capture-slack-game-threads
description: Captures complete game solution threads from Slack through browser computer-use, converts copied transcripts into recap JSON fixtures, and audits parsing. Use when copying Slack threads, backfilling game fixtures, or importing Slack messages into recap.
---

# Capture Slack game threads

Use the authenticated Slack browser and the repo's `jsonify` command. Preserve Slack's copied text; the converter already handles multiline and glued message headers.

## Pre-requisites

1. An authenticated Slack browser must be accessible. Consequently, this requires the Cursor / Codex / Claude Desktop Apps, and cannot be invoked from the CLI.
2. The Slack channel `#clued-in` must be present.

## Rules

1. The only considered games are `krillion`, `maptap`, or `timeguessr`

## Workflow

1. Make a capture manifest of every requested date and game.
2. Identify each target thread by its root message and game – `Krillion :thread:`, or `maptap :thread:`
3. Open one thread in Slack. Scroll through the full thread until the root, final reply, and reply count are all loaded and stable.
4. Select the entire thread transcript, including the root, and copy it with computer-use. Check `pbpaste` contains the expected first and last messages before continuing.
5. From the activated workspace virtualenv, immediately write the fixture:
  ```zsh
   pbpaste | python scripts/slack_copy_to_fixture.py --date YYYY-MM-DD > tests/fixtures/GAME_month_day.json
  ```
6. Inspect the JSON before moving on:
  - `source` is `manual Slack copy`;
  - `thread` identifies the intended game;
  - `messages` includes every reply, in order;
  - the first and last copied replies survived;
  - `thread.reply_count` equals `messages` length.
7. Audit parsing with:
  ```zsh
   recap fixtures tests/fixtures/GAME_month_day.json --silent
  ```
   Then use `--silent` when only CSV facts are wanted. Keep ordinary conversation in the fixture. Report claimed game-score messages under `DID NOT PARSE`; casual chatter is not a capture failure.
8. Repeat from the manifest, then report captured files, message counts, missing threads, and parse issues. A requested date/game pair is complete only when it has a verified fixture or is explicitly recorded as absent.

## Recovery

- If copied text glues `N replies`, authors, timestamps, or adjacent messages together, pass it through `scripts/slack_copy_to_fixture.py`; these Slack copy shapes are supported.
- If the first or last reply is missing, reload the thread, scroll end-to-end, and recopy it. Do not patch incomplete JSON by guessing.
- If `scripts/slack_copy_to_fixture.py` finds no messages, recopy from visible Slack message text rather than browser page chrome.
- If parsing fails, preserve the raw fixture and report the exact message. Capture and parser repair are separate tasks.

