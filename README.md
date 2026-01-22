# vastai-scraper

Scrapes bid/ask prices from vast.ai and saves to CSV files

## Setup

```bash
pnpm install
```

## Run

```bash
node index.mjs
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `./data` | Output directory for CSV files |
| `SCHEDULE` | `*/5 * * * *` | Cron schedule |
| `HEALTHCHECK_URL` | — | Optional healthchecks.io ping URL |
| `USER_AGENT` | `vastai-scraper/1.0` | HTTP User-Agent header |

## Output

```
data/
  2026-01-21-asks.csv
  2026-01-21-bids.csv
```

## Commands

```bash
just deploy    # deploy to remote host
just monitor   # tail logs on remote
just pull      # pull CSV data from remote
just analyze   # run analysis (in analysis/)
```

## Alerting

Create a free check at [healthchecks.io](https://healthchecks.io) and set `HEALTHCHECK_URL` in the systemd service file. You'll be notified if the scraper stops running.
