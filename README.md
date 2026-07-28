# Valdra Status

Public status page for [Valdra](https://valdra.ai) — **status.valdra.ai**

## Why this repo exists, and why it is public

A status page hosted on the servers it reports on is decoration: it goes down exactly
when it is needed. So nothing here touches our production estate.

```
GitHub Actions (cron)  ->  probes app.valdra.ai from outside our network
        v commits
   this repo           ->  90 days of history, as static JSON
        v auto-deploy
  Cloudflare Pages     ->  status.valdra.ai
```

The repo is **public on purpose**: GitHub Actions minutes are unlimited on public repos,
which makes the whole thing free. It contains only uptime results — nothing worth keeping
private.

## What is checked

Every 10 minutes, from GitHub's network:

| Component | Endpoint |
|---|---|
| Valdra application | `app.valdra.ai/` |
| Sign-in | `app.valdra.ai/en/login` |
| Trust Center | `app.valdra.ai/trust/canuckt-synergy` |
| valdra.ai | `valdra.ai/` |
| Legal documents | `valdra.ai/legal/sla.html` |

This is separate from, and does not replace, the 30-minute synthetic smoke test that runs
against production internally. That one signs in and exercises real workflows end to end
and drives our alerting. This one is the external, public view.

## Layout

```
scripts/probe.py            the checker — dependency-free, never raises
public/index.html           the page (static, no build step)
public/data/current.json    latest result per component
public/data/history.json    daily up/down buckets, 90-day retention
.github/workflows/check.yml the cron
```

## Local run

```bash
python3 scripts/probe.py          # writes public/data/*.json
cd public && python3 -m http.server 8000
```

## Adding a component

Append to `COMPONENTS` in `scripts/probe.py`. The page renders whatever the data
contains — no page change needed.

## Honest limitations

- GitHub's cron can drift by a few minutes under load, so "every 10 minutes" is a target
  rather than a guarantee.
- Probes come from one network. A regional routing problem invisible to GitHub would not
  appear here.
- It measures reachability, not correctness. A page that loads but misbehaves reads as up.
  The internal smoke test is what catches that.

Good enough to show a customer honestly. If we ever need multi-region probing with
sub-minute precision, that is the point at which paying for it makes sense.
