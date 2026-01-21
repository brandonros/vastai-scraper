# vastai-scraper

Scrapes bid/ask prices from vast.ai and saves to CSV files.

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

## Output

```
data/
  2026-01-21-asks.csv
  2026-01-21-bids.csv
```

## Production Deployment

```bash
./scripts/deploy.sh
```

## Alerting

Create a free check at [healthchecks.io](https://healthchecks.io) and set `HEALTHCHECK_URL` in the systemd service file. You'll be notified if the scraper stops running.
