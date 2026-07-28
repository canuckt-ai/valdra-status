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

## History before 28 July 2026

The external probe started on 2026-07-28. Rather than launch the page claiming "100% over
90 days" off a few hours of data, the `app` component was backfilled from the internal
end-to-end smoke monitor, which has run every 30 minutes since 2026-07-11:

```bash
ssh shield 'cat ~/backups/comply-smoke.log' > /tmp/smoke.log
python3 scripts/backfill_smoke.py /tmp/smoke.log
```

That window measured **99.357%** — including five real failures (two on 14 July, one on the
15th, two on the 27th). Those are left visible; a status page that hides its own outages is
worth nothing to the buyer reading it.

Only `app` was backfilled. The smoke test never checked the marketing site, Trust Center or
legal documents, so those rows show no data before the 28th rather than assumed uptime. The
script is idempotent and never overwrites a day the external probe already recorded, so
re-running it is safe.

The page renders the two sources identically because they answer the same question. They
are **not** the same measurement: the smoke test signs in and completes a full assessment,
so it is stricter than an HTTP check and reports the more conservative number. The footer
says so.

## Layout

```
scripts/probe.py            the checker — dependency-free, never raises
scripts/backfill_smoke.py   one-time import of internal smoke history (see above)
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

---

## Operational notes

### The DNS record must stay DNS-only

`status.valdra.ai` is a CNAME to `canuckt-ai.github.io` with **`proxied=false`** in
Cloudflare. Turning the orange cloud on breaks GitHub's certificate issuance and the site
goes to a TLS error. The record carries a comment saying so.

### Custom domain can only be set after a deployment exists

`gh api -X PUT repos/canuckt-ai/valdra-status/pages -f cname=status.valdra.ai` returns
*"The certificate does not exist yet"* until at least one Pages deployment has completed.
Deploy first, then set the domain. Committing `public/CNAME` alone did not set it.

### Workflow write permission

The `canuckt-ai` org disables *default* workflow write permissions, so
`actions/permissions/workflow` cannot be set to `write` at repo level. The explicit
`permissions: contents: write` block in the workflow overrides that and works — verified
by the runner committing results.

### Why GitHub Pages rather than Cloudflare Pages

Our Cloudflare API token is DNS-scoped only, so it cannot create a Pages project.
GitHub Pages gives the property that matters — hosting independent of the estate being
reported on.

Cloudflare Pages would be marginally better: faster edge, preview deployments, one
dashboard alongside DNS, and no ToS grey area about commercial use. There is also one
accepted downside here: the checker and the host are both GitHub, so a GitHub incident
takes out both, where two providers would not.

**Switching is cheap and nothing is locked in** — point a Cloudflare Pages project at this
same repo, change one DNS record. No content or workflow changes.

### Adding this link to customer documents

Once `status.valdra.ai` serves 200, link it from:

- **SLA section 2** — it states "an independent synthetic monitor every 30 minutes"; the
  link turns that claim into something a buyer can verify. Highest-value placement.
- **Security Overview** → Resilience
- The onboarding pack's service-commitments table

**Never link it before it resolves.** A dead `status.canuckt.ai` link was one of the
defects removed from the Shielk pages on 2026-07-28; the same mistake inside a signed
agreement would be considerably worse.
