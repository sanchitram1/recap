#!/usr/bin/env python3
"""Compatibility wrapper for the `jsonify` entrypoint."""

from recap.jsonify import main


if __name__ == "__main__":
    raise SystemExit(main())
