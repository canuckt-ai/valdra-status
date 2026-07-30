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

git fetch -q origin main 2>/dev/null
git reset -q --hard origin/main 2>/dev/null

python3 scripts/probe.py >/dev/null 2>&1 || exit 0
git add public/data/ 2>/dev/null
git diff --staged --quiet && exit 0

git commit -q -m "uptime: $(date -u +%Y-%m-%dT%H:%MZ) (probe @wp)"
# GitHub Actions may commit at the same moment. Rebase and retry rather than fail;
# a lost sample is invisible, a wedged cron is not.
for i in 1 2 3; do
  git push -q origin main 2>/dev/null && exit 0
  git pull -q --rebase --autostash origin main 2>/dev/null || break
  sleep 2
done
exit 0
