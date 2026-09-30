# Recap

how well do we do on the games?

## Flow

```
Read from solution threads on #clued-in
==> Parse outputs from each message in the thread
==> (date, person, game, score)
==> math
```

parse into the output is done, math and Slack are not

## Calculations

- average per game for last week – beat this!

## Run a fixture

```zsh
source .venv/bin/activate
recap fixtures --silent tests/fixtures/krillion_*
```

`--silent` is the way to run this. It leaves off the DID NOT PARSE section, so stdout is one header row and then the scores. A single file works the same way: `recap fixtures --silent tests/fixtures/maptap_september_28.json`.
