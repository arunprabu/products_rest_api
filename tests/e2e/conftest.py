"""Live-server fixtures for browser-based end-to-end tests."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator

import httpx
import pytest

_STARTUP_TIMEOUT_SECONDS = 30.0
_POLL_INTERVAL_SECONDS = 0.2


def _free_port() -> int:
    """Reserve an available TCP port on the loopback interface."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until_ready(base_url: str, process: subprocess.Popen[bytes]) -> None:
    """Block until the API answers, failing fast if the process exits."""
    deadline = time.monotonic() + _STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else b""
            raise RuntimeError(
                "API server exited before becoming ready: "
                f"{output.decode(errors='replace')}"
            )
        try:
            response = httpx.get(f"{base_url}/openapi.json", timeout=1.0)
        except httpx.HTTPError:
            time.sleep(_POLL_INTERVAL_SECONDS)
            continue
        if response.status_code == 200:
            return
        time.sleep(_POLL_INTERVAL_SECONDS)
    raise RuntimeError("API server did not become ready in time")


@pytest.fixture(scope="session")
def live_server_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """Run the API in a real uvicorn process backed by an isolated database."""
    port = _free_port()
    database_path = tmp_path_factory.mktemp("e2e-db") / "products.db"
    env = {
        **os.environ,
        "DATABASE_PATH": str(database_path),
        "LOG_LEVEL": "WARNING",
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            "src",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_ready(base_url, process)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


@pytest.fixture(scope="session")
def base_url(live_server_url: str) -> str:
    """Point Playwright's browser context at the live server."""
    return live_server_url
