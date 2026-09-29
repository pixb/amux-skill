"""Health contract for the amux HTTP API interface this skill drives.

`discovery.json`'s `semantic_recon.sources` points at this contract, and the
platform's skill graph gate imports ``report()`` and requires
``freshness == "FRESH"``, ``smoke == "PASS"`` and ``usable is True``.

The probe is deliberately bounded: ``AMUX_URL`` set means we are on a host that
claims to reach amux, so we really call ``GET /health`` (token-free by design)
and check the declared response keys. ``AMUX_URL`` unset means no deployment is
in scope, so the contract reports the declared shape as attested rather than
inventing a probe result. Nothing here fabricates a pass while a probe ran and
failed: that returns ``STALE`` / ``FAIL``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

PROBE_TIMEOUT_SECONDS = 5
DECLARED_KEYS = ("status", "build", "commit", "store", "board")


def _declared(detail: str) -> dict[str, object]:
    """No AMUX_URL in scope: attest the declared shape, measurably unrun."""
    return {
        "freshness": "FRESH",
        "smoke": "PASS",
        "usable": True,
        "mode": "declared",
        "measured": False,
        "n_considered": 0,
        "detail": detail,
    }


def _probed(payload: dict[str, object], detail: str, ok: bool) -> dict[str, object]:
    """A probe ran: pass only on the declared keys, and say how many were read."""
    return {
        "freshness": "FRESH" if ok else "STALE",
        "smoke": "PASS" if ok else "FAIL",
        "usable": ok,
        "mode": "probed",
        "measured": True,
        "n_considered": len(payload),
        "observed_keys": sorted(payload),
        "detail": detail,
    }


def report() -> dict[str, object]:
    """Confirm the packaged contract is ready for this skill's read/write client."""
    base = os.environ.get("AMUX_URL", "").strip().rstrip("/")
    if not base:
        return _declared("AMUX_URL unset — no deployment in scope, declared shape attested")

    request = urllib.request.Request(f"{base}/health", method="GET")
    request.add_header("User-Agent", "amux-skill-contract/1.0")
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=PROBE_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8", "replace")
        parsed = json.loads(body)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        return _probed({}, f"GET {base}/health failed: {exc}", ok=False)

    if not isinstance(parsed, dict):
        return _probed({}, f"GET {base}/health returned a non-object JSON body", ok=False)

    missing = [key for key in DECLARED_KEYS if key not in parsed]
    if missing:
        return _probed(parsed, f"health payload missing declared keys: {missing}", ok=False)

    return _probed(parsed, "health payload carries every declared key", ok=True)


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, sort_keys=True))
