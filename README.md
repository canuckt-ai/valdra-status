# Valdra Status

Public status page for [Valdra](https://valdra.ai) — **status.valdra.ai**

## Why this repo exists, and why it is public

A status page hosted on the servers it reports on is decoration: it goes down exactly
when it is needed. So nothing here touches our production estate.

```
cron on @wp (every 10 min, real)  ->  probes app.valdra.ai + valdra.ai
        v commits + pushes (repo-scoped deploy key)
   this repo                      ->  90 days of history, as static JSON
        v push trigger (NOT throttled)
   GitHub Pages                   ->  status.valdra.ai

GitHub Actions schedule           ->  slow independent fallback, still runs
```

**Why the probe moved off GitHub Actions.** Scheduled workflows are deprioritised on
free runners: measured over 25 consecutive runs, the `*/10` schedule fired with a
**median gap of 82 minutes** and a worst case of **194**. A status page cannot honestly
report a one-hour outage if it only looks three times a day. No setting or payment
changes this on a public repo.

`@wp` runs the probe on a real cron and pushes. A **push** trigger is not throttled, so
Pages redeploys within about a minute. The page still lives on GitHub Pages, so it
survives an outage of the estate it reports on — that property is not traded away.

**Honest limitation:** @wp is our own infrastructure, on a different machine from the
app it monitors (@shield) but in the same provider. If @wp itself dies, checks stop and
the page freezes showing "Updated N hours ago". The GitHub Actions schedule is
deliberately left in place as a slow fallback that would still catch that from
infrastructure we do not own.

The repo is **public on purpose**: GitHub Actions minutes are unlimited on public repos,
which makes the whole thing free. It contains only uptime results — nothing worth keeping
private.

## What is checked

Every 10 minutes, from GitHub's network:

**One row per failure domain, not one per URL.**

| Component | Endpoint | Fails independently because |
|---|---|---|
| Valdra application | `app.valdra.ai/` | Next.js container on @shield |
| API | `app.valdra.ai/health` | comply-api — a separate container and process |
| Website | `valdra.ai/` | @wp — a different server entirely |

Sign-in, the Trust Center and the legal pages were removed on 2026-07-28. Sign-in and the
Trust Center are served by the *same container* as the app, so their rows could not say
anything the app row had not already said — three strips moving in lockstep reads as
padding, and a buyer notices. Legal shares a host with valdra.ai. The Trust Center probe
also pointed at `/trust/canuckt-synergy`, publishing our own org slug on a public page.

The API row was added at the same time: Partner API and MCP integrations talk to it
directly, so it is a surface a customer can lose while the dashboard still looks fine.
`/health` is comply-api; `/api/health` is the Next.js frontend — do not confuse them.

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
so it is stricter than an HTTP check and reports the more conservative number.

The footer discloses that the earlier history is our own monitoring, but deliberately does
**not** describe how that monitor works. A public page is read by competitors as well as
customers, and "we sign in every 30 minutes and drive a full assessment" is a description
of our tooling, not a fact a customer needs. Disclose the provenance, not the mechanism.

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

Apply one test before adding: **can it fail while everything already listed stays up?**
If not, it is a duplicate row that dilutes the page rather than informing it. Renaming or
merging a component means migrating its key in `public/data/history.json` by hand, or the
old history is orphaned and silently vanishes from the page.

## Honest limitations

- **GitHub does not honour the 10-minute schedule.** Measured over 25 consecutive runs on
  2026-07-30: median gap **82 minutes**, range 5–194. GitHub deprioritises frequent
  scheduled workflows on free runners, and there is no way to buy your way out of it on a
  public repo. The cron stays at `*/10` because asking for more yields more; just do not
  believe it.
  **The page therefore no longer claims a frequency** — it shows when the last check
  actually ran and lets the reader judge. A status page that overstates its own cadence is
  worse than one that says nothing, because a gap of two hours reads as two hours of uptime.
  If sub-hourly certainty is ever needed, that is the point to add a second checker
  somewhere GitHub isn't.
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
