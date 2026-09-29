#!/usr/bin/env python3
"""Read-only amux API probe — the skill's single orchestrated entry point.

Runs the two steps an agent would otherwise have to sequence from prose:

  1. GET {AMUX_URL}/health — token-free liveness, build and store state.
  2. If AMUX_AUTH_TOKEN is exported, GET {AMUX_URL}/api/board to confirm the
     Bearer token is accepted.

Every request is a GET: nothing is written to the amux server, and the token
value never reaches the report — only whether a token was present and which
status code the server answered with. The amux deployment uses a self-signed
certificate, so certificate verification is disabled for these calls.

Writes the JSON report that scripts/run_evals.py scores against the criteria in
evals/amux.eval.md. An unreachable server is reported inside the report rather
than raised: the criteria decide whether that is a failure, so the same command
works on a host with no amux running.

Exit codes:
    0 - report written (check the report's "reachable" field)
    2 - usage error (--output is required)
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_URL = "https://localhost:8824"
DEFAULT_TIMEOUT = 8.0
RETRIEVED_FIELDS = ("status", "build", "commit", "store")


def decode_body(raw: bytes) -> dict | None:
    """Parse a response body as JSON, or return None when it is not an object."""
    try:
        value = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def get_json(url: str, token: str | None, timeout: float) -> tuple[int | None, dict | None, str | None]:
    """GET one amux URL. Returns (http_status, body, transport_error).

    A non-2xx answer is not an error — it is a status with a body, which is
    exactly what the Bearer branch needs to distinguish 200 from 401.
    """
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    context = ssl._create_unverified_context()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:  # noqa: S310
            return response.status, decode_body(response.read()), None
    except HTTPError as exc:
        try:
            body = decode_body(exc.read())
        except OSError:
            body = None
        return exc.code, body, None
    except (URLError, TimeoutError, OSError) as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def scenario_of(input_path: str | None) -> str:
    """First non-empty line of the golden input, recorded for traceability."""
    if not input_path:
        return ""
    path = Path(input_path)
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            return line.strip()
    return ""


def probe(url: str, token: str | None, timeout: float, scenario: str) -> dict:
    """Run both probe steps and return the report payload."""
    errors: list[str] = []
    health_status, health, transport_error = get_json(f"{url}/health", None, timeout)
    if transport_error:
        errors.append(f"health: {transport_error}")

    board_answer: str
    if health_status is None:
        board_answer = "unreachable"
    elif not token:
        board_answer = "skipped"
    else:
        board_status, _, board_error = get_json(f"{url}/api/board", token, timeout)
        if board_error:
            errors.append(f"board: {board_error}")
            board_answer = "unreachable"
        else:
            board_answer = str(board_status)

    report = {
        "board_auth": board_answer,
        "build": health.get("build") if health else None,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": health.get("commit") if health else None,
        "errors": errors,
        "health_http": health_status,
        "health_status": health.get("status") if health else None,
        "reachable": health_status is not None,
        "scenario": scenario,
        "skill": "amux",
        "store": health.get("store") if health else None,
        "token_present": bool(token),
        "url": url,
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only probe of the amux HTTP API.")
    parser.add_argument("--input", default=None, help="Golden case input; its first line is recorded as the scenario.")
    parser.add_argument("--output", required=True, help="Where to write the JSON report.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Per-request timeout in seconds.")
    args = parser.parse_args(argv)

    url = (os.environ.get("AMUX_URL") or DEFAULT_URL).rstrip("/")
    token = os.environ.get("AMUX_AUTH_TOKEN") or None
    report = probe(url, token, args.timeout, scenario_of(args.input))

    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
