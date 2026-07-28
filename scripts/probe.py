#!/usr/bin/env python3
"""Probe the Valdra estate from outside it and append the result to history.

Deliberately dependency-free and tolerant: a probe that crashes on a malformed response
would take the status page down with the thing it is meant to report on.

History is kept as one JSON file of daily buckets. That keeps the page a static asset —
no database, no API, nothing that can be down.
"""
from __future__ import annotations

import json
import pathlib
import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "public" / "data"
HISTORY = DATA / "history.json"
CURRENT = DATA / "current.json"

RETAIN_DAYS = 90
TIMEOUT = 20

# One row per FAILURE DOMAIN, not one per URL. Sign-in, the Trust Center and the legal
# pages were all dropped: sign-in and the Trust Center are served by the same container as
# the app, so their rows could never say anything the app row had not already said, and
# three strips moving in lockstep reads as padding. Legal shares a host with valdra.ai.
#
# The Trust Center probe also had to go on its own merits — it hit /trust/canuckt-synergy,
# publishing our own org slug on a public page.
#
# What is left can each fail independently:
#   app      Next.js container   (@shield)
#   api      comply-api container (@shield, separate container, separate process)
#   website  valdra.ai            (@wp — a different server entirely)
#
# The API earns its row: Partner API and MCP integrations talk to it directly, so it is a
# surface a customer loses without the dashboard looking any different.
COMPONENTS = [
    {"key": "app",     "name": "Valdra application", "url": "https://app.valdra.ai/",
     "ok": lambda c: 200 <= c < 400},
    {"key": "api",     "name": "API",                "url": "https://app.valdra.ai/health",
     "ok": lambda c: c == 200},
    {"key": "website", "name": "Website",            "url": "https://valdra.ai/",
     "ok": lambda c: 200 <= c < 400},
]


def probe(url: str) -> tuple[int | None, int | None, str | None]:
    """Return (status_code, latency_ms, error). Never raises."""
    req = urllib.request.Request(url, method="GET", headers={
        "User-Agent": "valdra-status/1.0 (+https://status.valdra.ai)"})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, int((time.monotonic() - started) * 1000), None
    except urllib.error.HTTPError as e:
        return e.code, int((time.monotonic() - started) * 1000), None
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, OSError) as e:
        return None, int((time.monotonic() - started) * 1000), str(e)[:120]


def load(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    history = load(HISTORY, {})
    current = {"checked_at": now.isoformat(), "components": []}

    for c in COMPONENTS:
        code, ms, err = probe(c["url"])
        up = bool(code is not None and c["ok"](code))
        current["components"].append({
            "key": c["key"], "name": c["name"], "url": c["url"],
            "up": up, "status": code, "latency_ms": ms, "error": err,
        })
        day = history.setdefault(c["key"], {}).setdefault(today, {"up": 0, "down": 0})
        day["up" if up else "down"] += 1
        print("  %-10s %-6s %sms%s" % (
            c["key"], code if code is not None else "ERR", ms, "" if up else "  <-- DOWN"))

    # Trim to the retention window so the file cannot grow without bound.
    cutoff = (now - timedelta(days=RETAIN_DAYS)).strftime("%Y-%m-%d")
    for key in history:
        for d in [d for d in history[key] if d < cutoff]:
            del history[key][d]

    # Overall state: degraded if some components are down, outage if all are.
    ups = [c["up"] for c in current["components"]]
    current["overall"] = "operational" if all(ups) else ("outage" if not any(ups) else "degraded")

    total_up = sum(d["up"] for k in history for d in history[k].values())
    total_all = sum(d["up"] + d["down"] for k in history for d in history[k].values())
    current["uptime_90d"] = round(100.0 * total_up / total_all, 3) if total_all else None

    HISTORY.write_text(json.dumps(history, sort_keys=True, separators=(",", ":")))
    CURRENT.write_text(json.dumps(current, indent=2, sort_keys=True))
    print("\noverall: %s   90-day uptime: %s%%" % (current["overall"], current["uptime_90d"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
