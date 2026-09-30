# Recap

How well do we do on the games?

## Flow

1. Agent copies all text from a solution thread from `#clued-in`
2. `jsonify` each message to produce a list of messages
3. `parse` each message to produce `(date, person, game, score)`

## Usage

Invoke the `capture-slack-game-threads` skill in your favorite harness. It will output:

```json

{
  "source": "manual Slack copy",
  "messages": [
    {
      "person": "John Adams",
      "ts": "1790615160.000000",
      "text": "Krillion (spoilers)\nJohn Adams"
    },
    {
      "person": "Ben Franklin",
      "ts": "1790615160.000000",
      "text": "Krillion #75\n310\n\nBen Franklin"
    }
  ]
}
```

Alternatively, you can copy an individual thread into a fixture, and then run `jsonify` followed by `recap`:

```bash
# 1. activate
uv sync
source .venv/bin/activate

# 2. make JSON from copied content
jsonify --date $TODAY path/to/copied/file.txt

# 3. parse it
recap fixtures tests/fixtures/jsonified_file.json --silent
# recap accepts globs: tests/fixtures/krillion_*
```

Recap outputs a csv shaped like:

```csv
date,person,game,score
September 28,Dirk,maptap,862
September 28,Sanchit Ram Arvind,maptap,938
September 28,Eva,maptap,837
September 28,Hannah Turk,maptap,895
```

> [!note]
>
> There might be some parsing errors in this. Feel free to adjust the parsers to improve our detection. The `--silent` flag suppresses the parsing failures to a count at the end of the result.

## Contributing

- [x] Parser for `timeguessr`
- [ ] Ignore non-score messages in each parser
- [ ] Reliably identify a solution thread
- [ ] Parse the emojis to collect scoring-specific information

