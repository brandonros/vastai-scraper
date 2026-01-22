# Vast.ai RTX 5090 Data Analysis

## Data Structure

### Files
- `data/YYYY-MM-DD-asks.csv` - Seller asking prices
- `data/YYYY-MM-DD-bids.csv` - Buyer bid prices

Both files have identical schemas and are scraped simultaneously every 5 minutes.

### Schema
| Column | Description |
|--------|-------------|
| `timestamp` | Scrape time (ms precision, but asks/bids are ~4ms apart) |
| `id` | **Offer ID** - unique listing for a specific GPU configuration |
| `host_id` | Provider/owner ID (can have multiple machines) |
| `machine_id` | Physical machine ID (can have multiple offers) |
| `dph_total` | **Price per hour** (dollars) |
| `min_bid` | Minimum acceptable bid |
| `num_gpus` | Number of GPUs in this offer (1, 2, 4, 8 used in analysis; rare 6/9 filtered out) |
| `gpu_ram` | GPU memory (MB) - always 32607 for 5090 |
| `cpu_cores` | CPU cores available |
| `cpu_ram` | System RAM (MB) |
| `cpu_ghz` | CPU frequency |
| `disk_space` | Storage (GB) |
| `disk_bw` | Disk bandwidth (MB/s) |
| `inet_up` | Upload speed (Mbps) |
| `inet_down` | Download speed (Mbps) |
| `geolocation` | Location string (e.g., "California, US") |
| `reliability2` | Reliability score (0-1) |
| `pci_gen` | PCIe generation (3, 4, 5) |
| `pcie_bw` | PCIe bandwidth (GB/s) |

### Batch Structure

Each scrape produces ~120-140 rows sharing an **identical timestamp**. The timestamp acts as the batch identifier.

```
2026-01-21T14:15:44.387Z  ← 125 rows (all same timestamp)
2026-01-21T14:20:00.022Z  ← 118 rows (next batch, 5 min later)
2026-01-21T14:25:00.090Z  ← 122 rows
```

**Key points:**
- Scraper runs every 5 minutes via cron
- All offers from one API call get the same timestamp (set once before fetch)
- asks.csv and bids.csv have slightly different timestamps (~4ms apart) because they're separate API calls
- Within a single file, raw `timestamp` is a perfect batch key
- To join asks↔bids, floor to minute: `timestamp.dt.floor('min')`

```python
# Group by batch within one file
for ts, batch in df.groupby('timestamp'):
    print(f"{ts}: {len(batch)} offers")

# Join asks to bids (align the 4ms gap)
asks['ts_min'] = asks.timestamp.dt.floor('min')
bids['ts_min'] = bids.timestamp.dt.floor('min')
merged = asks.merge(bids, on=['ts_min', 'machine_id', 'num_gpus'], ...)
```

### Entity Relationships

```
Host (provider)
  └── Machine (physical server)
        └── Offer (rental listing with specific GPU count)
              ├── appears in asks.csv (seller's asking price)
              └── appears in bids.csv (current highest bid / spot price)
```

### Critical: Offer ID is NOT Stable

**The `id` (offer ID) changes when a machine is rented and returns to market.**

Example from machine 40406:
```
14:55 - offer 29496002 (available)
15:00 - offer 29496006 (new ID after being rented!)
18:15 - offer 29496002 (old ID reappears)
```

Analysis of 416 machine/gpu combinations:
- 244 have 1 offer ID (stable)
- 172 have 2+ different offer IDs (unstable)

**Use `(machine_id, num_gpus)` as the stable identifier, NOT `id`.**

### Machine Availability (Churn)

Machines frequently go offline (rented out). Out of 78 scrapes:
- Median presence: 13 scrapes (17%)
- Only 34 machine/gpu combos available 70+ scrapes
- 182 combos present in <10 scrapes

This high churn means:
- Can't track most machines continuously
- New offer IDs created when machines return
- Focus analysis on consistently-available machines

### Matching Asks to Bids

To compare ask vs bid for the same listing at a point in time:

```python
asks['ts_min'] = asks.timestamp.dt.floor('min')
bids['ts_min'] = bids.timestamp.dt.floor('min')

# Option 1: Match by offer ID (same snapshot only)
merged = asks.merge(bids, on=['ts_min', 'id'], suffixes=('_ask', '_bid'))

# Option 2: Match by machine+gpu (works across time, preferred)
merged = asks.merge(bids, on=['ts_min', 'machine_id', 'num_gpus'], suffixes=('_ask', '_bid'))
```

## Sample Data (2026-01-21)

### Volume
- **78 scrapes** over ~6 hours (14:15 - 20:35 UTC)
- **~127 offers per scrape**
- **9,949 total rows** in each file

### Cardinality
| Entity | Asks | Bids |
|--------|------|------|
| Unique offers (`id`) | 788 | 780 |
| Unique machines | 268 | 263 |
| Unique hosts | 121 | 118 |

### GPU Configuration Distribution (unique offers)
| GPUs | Offers |
|------|--------|
| 1 | 420 |
| 2 | 205 |
| 4 | 105 |
| 8 | 56 |

*Note: Rare configs (6, 9 GPUs) filtered out of analysis.*

### Pricing (1-GPU offers)
| Metric | Ask (seller wants) | Bid (buyer pays) |
|--------|-------------------|------------------|
| Min | $0.282/hr | $0.015/hr |
| Max | $1.336/hr | $4.003/hr |
| Median | $0.535/hr | $0.322/hr |

**Spread**: Ask is typically ~$0.15-0.20/hr higher than bid for 1-GPU offers.

## Analysis Considerations

### Challenge: Heterogeneous Systems
Each scrape returns 100+ offers with varying:
- GPU count (1, 2, 4, 8)
- CPU cores (32-384)
- RAM (48-258 GB)
- Network speed
- Location
- Reliability scores

**This makes raw aggregation misleading** - averaging prices across 1-GPU and 8-GPU offers is meaningless.

### Recommended Approaches

1. **Filter to 1-GPU only** for apples-to-apples comparison
2. **Track by `(machine_id, num_gpus)`** - NOT offer ID (IDs change on re-listing)
3. **Focus on high-availability machines** (present in 50%+ scrapes) for trend analysis
4. **Segment by location or reliability** for market analysis

### Useful Derived Metrics

```python
# Spread per offer
spread = ask_price - bid_price

# Per-GPU price (for multi-GPU offers)
price_per_gpu = dph_total / num_gpus

# Price bands
cheap = df[df.dph_total < 0.40]
mid = df[(df.dph_total >= 0.40) & (df.dph_total < 0.70)]
expensive = df[df.dph_total >= 0.70]
```

## Current Analysis (`analyze.py`)

The script includes:
- **1-GPU focused analysis** - filters to `num_gpus == 1` for apples-to-apples comparison
- **Stable tracking** - uses `(machine_id, num_gpus)` instead of offer ID
- **Bid/ask spread** - plots spread over time with std deviation bands
- **Per-GPU normalized pricing** - computes `price_per_gpu = dph_total / num_gpus` for all configs
- **Configuration comparison** - box plots and summary table comparing per-GPU cost across 1/2/4/8 GPU offers

The per-GPU normalization reveals bulk pricing effects (discounts or premiums for multi-GPU bundles).

## Next Steps

- [x] ~~Rewrite analyze.py to focus on 1-GPU offers~~
- [x] ~~Track by (machine_id, num_gpus) instead of offer ID~~
- [x] ~~Plot bid/ask spread over time~~
- [x] ~~Per-GPU normalized pricing comparison~~
- [ ] Identify price movers (machines with changing prices)
- [ ] Market depth visualization (available supply at each price point)
- [ ] High-availability machine filtering (present in 50%+ scrapes)
