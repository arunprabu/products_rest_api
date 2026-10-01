"""Summarize the JSON application log produced by the Products REST API.

Reads ``logs/app.log`` (one JSON object per line, as emitted by
``app.core.logging.JsonFormatter``) and prints a human-readable summary:
total requests, requests per status code, ERROR/WARNING counts, average
response time, and the five slowest requests.

Only the Python standard library is used. Missing files and malformed
lines are handled gracefully.

Usage:
    python monitoring/parse_logs.py [path/to/app.log]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "app.log"
SLOWEST_LIMIT = 5


@dataclass(frozen=True)
class RequestEntry:
    """A single request log record with the fields we summarize."""

    method: str
    path: str
    status_code: int
    duration_ms: float


@dataclass
class LogSummary:
    """Aggregated statistics derived from a log file."""

    total_lines: int = 0
    malformed_lines: int = 0
    total_requests: int = 0
    status_counts: Counter[int] | None = None
    error_count: int = 0
    warning_count: int = 0
    total_duration_ms: float = 0.0
    slowest: list[RequestEntry] | None = None

    def __post_init__(self) -> None:
        if self.status_counts is None:
            self.status_counts = Counter()
        if self.slowest is None:
            self.slowest = []

    @property
    def average_duration_ms(self) -> float:
        """Average response time across all request entries."""
        if self.total_requests == 0:
            return 0.0
        return self.total_duration_ms / self.total_requests


def _as_float(value: Any) -> float | None:
    """Coerce a JSON value to float, returning None when not numeric."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: Any) -> int | None:
    """Coerce a JSON value to int, returning None when not integral."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _parse_request(record: dict[str, Any]) -> RequestEntry | None:
    """Build a RequestEntry from a decoded record, or None if not a request."""
    status_code = _as_int(record.get("status_code"))
    duration_ms = _as_float(record.get("duration_ms"))
    if status_code is None or duration_ms is None:
        return None
    return RequestEntry(
        method=str(record.get("method", "-")),
        path=str(record.get("path", "-")),
        status_code=status_code,
        duration_ms=duration_ms,
    )


def summarize(lines: list[str]) -> LogSummary:
    """Aggregate a list of raw log lines into a LogSummary."""
    summary = LogSummary()
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        summary.total_lines += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            summary.malformed_lines += 1
            continue
        if not isinstance(record, dict):
            summary.malformed_lines += 1
            continue

        level = str(record.get("level", "")).upper()
        if level == "ERROR":
            summary.error_count += 1
        elif level == "WARNING":
            summary.warning_count += 1

        request = _parse_request(record)
        if request is None:
            continue
        summary.total_requests += 1
        summary.total_duration_ms += request.duration_ms
        assert summary.status_counts is not None
        assert summary.slowest is not None
        summary.status_counts[request.status_code] += 1
        summary.slowest.append(request)

    assert summary.slowest is not None
    summary.slowest.sort(key=lambda entry: entry.duration_ms, reverse=True)
    summary.slowest = summary.slowest[:SLOWEST_LIMIT]
    return summary


def read_log_lines(path: Path) -> list[str] | None:
    """Read the log file, returning None when it does not exist."""
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    except OSError as exc:
        print(f"Could not read log file '{path}': {exc}", file=sys.stderr)
        return None


def _format_duration(duration_ms: float) -> str:
    """Render a duration in milliseconds with two decimals."""
    return f"{duration_ms:.2f} ms"


def print_summary(summary: LogSummary, path: Path) -> None:
    """Print a readable summary of the parsed log to stdout."""
    print("=" * 60)
    print(f"Log summary: {path}")
    print("=" * 60)
    print(f"Lines parsed:        {summary.total_lines}")
    print(f"Malformed lines:     {summary.malformed_lines}")
    print(f"Total requests:      {summary.total_requests}")
    print(f"Average response:    {_format_duration(summary.average_duration_ms)}")
    print(f"ERROR entries:       {summary.error_count}")
    print(f"WARNING entries:     {summary.warning_count}")

    print("\nRequests by status code:")
    status_counts = summary.status_counts or Counter()
    if status_counts:
        for code in sorted(status_counts):
            print(f"  {code}: {status_counts[code]}")
    else:
        print("  (none)")

    print(f"\nTop {SLOWEST_LIMIT} slowest requests:")
    slowest = summary.slowest or []
    if slowest:
        for rank, entry in enumerate(slowest, start=1):
            print(
                f"  {rank}. {_format_duration(entry.duration_ms):>12}  "
                f"{entry.method} {entry.path} -> {entry.status_code}"
            )
    else:
        print("  (none)")
    print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    """Entry point: parse the log file and print the summary."""
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else DEFAULT_LOG_PATH

    lines = read_log_lines(path)
    if lines is None:
        print(
            f"Log file not found: {path}\n"
            "Nothing to summarize yet. Start the API and generate some traffic, "
            "then run this script again.",
            file=sys.stderr,
        )
        return 1

    summary = summarize(lines)
    print_summary(summary, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
