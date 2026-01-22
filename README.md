# vastai-scraper

Scrapes bid/ask prices from vast.ai and saves to CSV files

## Commands

```bash
just run       # run scraper locally
just deploy    # deploy to remote host
just monitor   # tail logs on remote
just pull      # pull CSV data from remote
just analyze   # run analysis
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

Example (`asks.csv`):
```csv
timestamp,id,host_id,machine_id,dph_total,min_bid,num_gpus,gpu_ram,cpu_cores,cpu_ram,cpu_ghz,disk_space,disk_bw,inet_up,inet_down,geolocation,reliability2,pci_gen,pcie_bw
2026-01-21T14:15:44.387Z,29496002,208874,40406,0.284,0.280,1,32607,208,64448,4.20,558.1,1667.0,289.4,476.2,"California, US",0.995,5,53.5
2026-01-21T14:15:44.387Z,29332107,155381,43567,0.310,0.307,1,32607,192,64349,2.40,499.5,3423.0,449.8,676.9,"Washington, US",0.997,5,54.1
```

## Alerting

Create a free check at [healthchecks.io](https://healthchecks.io) and set `HEALTHCHECK_URL` in the systemd service file. You'll be notified if the scraper stops running.
