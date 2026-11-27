"""A helper that takes its time to start (tests/test_program.py: closing never waits for the helpers)."""

import time


def start(home: str, name: str) -> None:
    time.sleep(300)
