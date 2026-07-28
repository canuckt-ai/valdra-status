#!/usr/bin/env python3
"""One-time backfill of history from the internal end-to-end smoke monitor.

The external probe in probe.py only began on 2026-07-28, so the page would otherwise
show a single day and claim 100% — which reads as "we have never had an outage" when it
actually means "we have barely started measuring".

The internal monitor has run every 30 minutes since 2026-07-11 and is the STRICTER
check: it signs in and drives a full assessment (create, save, persist, submit, score)
rather than asking for an HTTP status. Its failures are real — two on 14 July, one on the
15th, two on the 27th (the AI spend-cap bug) — and hiding them would defeat the purpose
of the page.

Only the `app` component is backfilled, because that is what the smoke test actually
exercises. Inventing history for the marketing site or the legal documents, which it
never checked, would be fabricating data on a page whose entire job is being believed.

Usage (reads the log over ssh, writes public/data/history.json):
    python3 scripts/backfill_smoke.py path/to/comply-smoke.log
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HISTORY = ROOT / "public" / "data" / "history.json"

# Backfill stops the day before external probing began, so no single day mixes sources.
BACKFILL_THROUGH = "2026-07-27"
COMPONENT = "app"

LINE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s.*SMOKE TEST (PASSED|FAILED)")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: backfill_smoke.py <smoke.log>", file=sys.stderr)
        return 2

    days: dict[str, dict[str, int]] = {}
    with open(sys.argv[1], encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = LINE.match(line)
            if not m:
                continue
            day, result = m.group(1), m.group(2)
            if day > BACKFILL_THROUGH:
                continue
            b = days.setdefault(day, {"up": 0, "down": 0})
            b["up" if result == "PASSED" else "down"] += 1

    if not days:
        print("no smoke results parsed — refusing to write", file=sys.stderr)
        return 1

    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else {}
    comp = history.setdefault(COMPONENT, {})

    added = 0
    for day, b in sorted(days.items()):
        # Never overwrite a day the external probe already recorded.
        if day in comp:
            continue
        comp[day] = b
        added += 1
        flag = "" if not b["down"] else "   <-- %d failure(s)" % b["down"]
        print("  %s  up=%-4d down=%d%s" % (day, b["up"], b["down"], flag))

    HISTORY.write_text(json.dumps(history, sort_keys=True, separators=(",", ":")))
    total_up = sum(v["up"] for v in days.values())
    total_all = sum(v["up"] + v["down"] for v in days.values())
    print("\n  backfilled %d days into '%s'" % (added, COMPONENT))
    print("  smoke availability over that window: %.3f%% (%d/%d checks)"
          % (100.0 * total_up / total_all, total_up, total_all))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
