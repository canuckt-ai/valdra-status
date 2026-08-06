#!/usr/bin/env bash
# Run the probe from @wp on a REAL ten-minute cron, and push the result.
#
# Why this exists: GitHub deprioritises frequent scheduled workflows on free
# runners. Measured over 25 consecutive runs, the "*/10" schedule actually fired
# with a median gap of 82 minutes and a worst case of 194. A status page checked
# three times a day cannot honestly report an outage that lasted an hour.
#
# So the probe runs here, where cron means cron. The PAGE still lives on GitHub
# Pages, so it survives an outage of the estate it reports on — that property is
# the whole point and is not traded away.
#
# Honest limitation: @wp is our own infrastructure. If @wp itself dies, checks
# stop and the page freezes with a visible "Updated N hours ago". The GitHub
# Actions schedule is deliberately LEFT IN PLACE as a slow independent fallback
# that would still catch it.
set -uo pipefail
cd "$HOME/valdra-status" || exit 0
export GIT_SSH_COMMAND="ssh -i $HOME/.ssh/valdra_status_deploy -o IdentitiesOnly=yes -o BatchMode=yes"

# Samples go to the `data` branch, NEVER to `main`.
#
# WHY (2026-08-06): GitHub Pages republishes on every push to the branch it serves.
# While samples landed on `main` that meant ~144 republishes a day of an HTML shell that
# never changes. Two of them collided, one jammed, and Pages then refused every
# republish for hours ("due to in progress deployment"). The page stayed up but frozen
# at 11:39 while this script kept working perfectly.
#
# `main` now holds only code, so it changes rarely and Pages almost never rebuilds.
# The page reads these samples straight off the `data` branch over
# raw.githubusercontent.com, so publishing is no longer in the freshness path at all.

git fetch -q origin main data 2>/dev/null
# Code comes from main, so script/probe changes still reach us automatically.
git reset -q --hard origin/main 2>/dev/null

# Carry the accumulated samples forward. Without this the hard reset above would drop us
# back to whatever data snapshot happened to be committed on main, and probe.py — which
# READS history.json and appends to it — would silently restart history from scratch
# every ten minutes. 27 days of uptime history would evaporate one cycle at a time.
git checkout -q origin/data -- public/data/ 2>/dev/null || true

python3 scripts/probe.py >/dev/null 2>&1 || exit 0
git add public/data/ 2>/dev/null
git diff --staged --quiet && exit 0

git commit -q -m "uptime: $(date -u +%Y-%m-%dT%H:%MZ) (probe @wp)"

# Force-push to `data`. This branch is a data carrier with no history worth preserving —
# each run publishes main's code plus the newest sample — so forcing is correct here and
# avoids the rebase races the old main-targeted push had to retry around. Nothing else
# ever commits to this branch.
git push -q -f origin HEAD:data 2>/dev/null && exit 0

# One retry, in case the fetch above raced a concurrent run.
git fetch -q origin data 2>/dev/null
git checkout -q origin/data -- public/data/ 2>/dev/null || true
python3 scripts/probe.py >/dev/null 2>&1 || exit 0
git add public/data/ 2>/dev/null
git diff --staged --quiet && exit 0
git commit -q --amend --no-edit -q 2>/dev/null
git push -q -f origin HEAD:data 2>/dev/null
exit 0
