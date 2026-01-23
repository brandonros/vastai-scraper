#!/usr/bin/env python3
"""Analyze vast.ai RTX 5090 pricing data.

Focuses on 1-GPU offers for apples-to-apples comparison.
See docs/analysis.md for data structure documentation.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'


VALID_GPU_COUNTS = [1, 2, 4, 8]


def load_all_data():
    """Load all asks/bids data with per-GPU normalized pricing."""
    asks = pd.concat([
        pd.read_csv(f)
        for f in DATA_DIR.glob('*-asks.csv')
    ], ignore_index=True)
    asks['timestamp'] = pd.to_datetime(asks['timestamp'], utc=True)

    bids = pd.concat([
        pd.read_csv(f)
        for f in DATA_DIR.glob('*-bids.csv')
    ], ignore_index=True)
    bids['timestamp'] = pd.to_datetime(bids['timestamp'], utc=True)

    # Filter to standard GPU configs only (drop rare 6, 9, etc.)
    asks = asks[asks['num_gpus'].isin(VALID_GPU_COUNTS)]
    bids = bids[bids['num_gpus'].isin(VALID_GPU_COUNTS)]

    # Floor to minute to align asks/bids
    asks['ts'] = asks['timestamp'].dt.floor('min')
    bids['ts'] = bids['timestamp'].dt.floor('min')

    # Deduplicate in case scraper ran twice in same minute
    asks = asks.drop_duplicates(subset=['ts', 'machine_id', 'num_gpus'])
    bids = bids.drop_duplicates(subset=['ts', 'machine_id', 'num_gpus'])

    # Add per-GPU pricing
    asks['price_per_gpu'] = asks['dph_total'] / asks['num_gpus']
    bids['price_per_gpu'] = bids['dph_total'] / bids['num_gpus']

    return asks, bids


def load_data_for_analysis():
    """Load all market data and prepare for analysis.

    Returns:
        merged_1gpu: 1-GPU asks/bids matched by (ts, machine_id) with spread
        asks_1gpu: All 1-GPU ask offers
        bids_1gpu: All 1-GPU bid offers
        asks_all: All ask offers (1/2/4/8 GPU configs)
        bids_all: All bid offers (1/2/4/8 GPU configs)
    """
    asks_all, bids_all = load_all_data()

    # Filter to 1-GPU only for matched analysis
    asks_1gpu = asks_all[asks_all['num_gpus'] == 1].copy()
    bids_1gpu = bids_all[bids_all['num_gpus'] == 1].copy()

    # Match asks to bids by machine
    merged_1gpu = asks_1gpu.merge(
        bids_1gpu,
        on=['ts', 'machine_id', 'num_gpus'],
        suffixes=('_ask', '_bid')
    )

    # Calculate spread
    merged_1gpu['spread'] = merged_1gpu['dph_total_ask'] - merged_1gpu['dph_total_bid']

    return merged_1gpu, asks_1gpu, bids_1gpu, asks_all, bids_all


def plot_market_prices(asks, bids):
    """Plot price percentiles over time for asks and bids."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    percentiles = [1, 5, 10, 25, 50, 75, 95]

    for ax, df, name, color in [(axes[0], asks, 'Ask', 'tab:red'),
                                 (axes[1], bids, 'Bid', 'tab:green')]:
        by_time = df.groupby('ts')['dph_total'].quantile(
            [p/100 for p in percentiles]
        ).unstack()
        by_time.columns = [f'p{p}' for p in percentiles]

        # Plot percentile bands (light to dark toward median)
        ax.fill_between(by_time.index, by_time['p1'], by_time['p95'], alpha=0.05, color=color, label='P1-P95')
        ax.fill_between(by_time.index, by_time['p5'], by_time['p95'], alpha=0.1, color=color, label='P5-P95')
        ax.fill_between(by_time.index, by_time['p10'], by_time['p75'], alpha=0.15, color=color, label='P10-P75')
        ax.fill_between(by_time.index, by_time['p25'], by_time['p75'], alpha=0.2, color=color, label='P25-P75')

        # Plot key lines
        ax.plot(by_time.index, by_time['p50'], color=color, linewidth=2, label='P50 (median)')
        ax.plot(by_time.index, by_time['p1'], color=color, linewidth=1, linestyle=':', alpha=0.5, label='P1')
        ax.plot(by_time.index, by_time['p5'], color=color, linewidth=1, linestyle=':', alpha=0.7, label='P5')
        ax.plot(by_time.index, by_time['p10'], color=color, linewidth=1, linestyle='--', alpha=0.7, label='P10')

        ax.set_ylabel('Price ($/hr)')
        ax.set_title(f'RTX 5090 1-GPU: {name} Prices Over Time')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)

    axes[1].set_xlabel('Time')
    plt.tight_layout()
    return fig


def plot_spread(merged):
    """Plot bid/ask spread over time with percentile bands."""
    fig, ax = plt.subplots(figsize=(12, 4))

    percentiles = [10, 25, 50, 75, 90]
    by_time = merged.groupby('ts')['spread'].quantile(
        [p/100 for p in percentiles]
    ).unstack()
    by_time.columns = [f'p{p}' for p in percentiles]

    # Percentile bands
    ax.fill_between(by_time.index, by_time['p10'], by_time['p90'],
                    alpha=0.1, color='tab:blue', label='P10-P90')
    ax.fill_between(by_time.index, by_time['p25'], by_time['p75'],
                    alpha=0.2, color='tab:blue', label='P25-P75')

    # Median line
    ax.plot(by_time.index, by_time['p50'], color='tab:blue', linewidth=2,
            marker='.', markersize=3, label='Median')

    ax.axhline(0, color='black', linestyle='--', alpha=0.3, label='Break-even')
    ax.set_xlabel('Time')
    ax.set_ylabel('Spread ($/hr)')
    ax.set_title('RTX 5090 1-GPU: Bid/Ask Spread (ask - bid)')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


def plot_supply(asks):
    """Plot number of available 1-GPU offers over time."""
    fig, ax = plt.subplots(figsize=(12, 4))

    supply = asks.groupby('ts').size()

    ax.plot(supply.index, supply.values, marker='.', color='tab:purple')
    ax.fill_between(supply.index, 0, supply.values, alpha=0.2, color='tab:purple')

    ax.set_xlabel('Time')
    ax.set_ylabel('Available Offers')
    ax.set_title('RTX 5090 1-GPU: Supply (number of listings)')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


def plot_per_gpu_over_time(asks_all, bids_all):
    """Overlay per-GPU median prices over time for all configurations."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    gpu_counts = sorted(asks_all['num_gpus'].unique())
    colors = {1: 'tab:blue', 2: 'tab:orange', 4: 'tab:green', 8: 'tab:purple'}

    for ax, df, name in [(axes[0], asks_all, 'Ask'), (axes[1], bids_all, 'Bid')]:
        for n in gpu_counts:
            subset = df[df['num_gpus'] == n]
            median = subset.groupby('ts')['price_per_gpu'].median()
            ax.plot(median.index, median.values, label=f'{n}-GPU',
                    color=colors[n], linewidth=1.5, alpha=0.8)

        ax.set_ylabel('Price per GPU ($/hr)')
        ax.set_title(f'RTX 5090: {name} Price per GPU Over Time')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)

    axes[1].set_xlabel('Time')
    plt.tight_layout()
    return fig


def print_summary(merged, asks, bids, asks_all, bids_all):
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("RTX 5090 1-GPU MARKET SUMMARY")
    print("=" * 60)

    print(f"\nData range: {merged['ts'].min()} to {merged['ts'].max()}")
    print(f"Batches: {merged['ts'].nunique()}")
    print(f"Matched pairs: {len(merged):,}")

    print(f"\nPRICE PERCENTILES (1-GPU)")
    print(f"         Ask         Bid      Spread")
    print(f"      -------     -------     ------")
    for p in [1, 5, 10, 25, 50, 75, 95]:
        ask_p = asks['dph_total'].quantile(p/100)
        bid_p = bids['dph_total'].quantile(p/100)
        spread = ask_p - bid_p
        print(f"P{p:<3}  ${ask_p:.3f}/hr  ${bid_p:.3f}/hr  ${spread:+.3f}")

    print(f"\nSPREAD (ask - bid)")
    print(f"  Median: ${merged['spread'].median():.3f}/hr")
    print(f"  Mean:   ${merged['spread'].mean():.3f}/hr")

    print("\n" + "=" * 60)
    print("PER-GPU PRICING BY CONFIGURATION")
    print("=" * 60)

    gpu_counts = sorted(asks_all['num_gpus'].unique())
    print(f"\n{'GPUs':>4}  {'Count':>6}  {'Ask $/GPU':>10}  {'Bid $/GPU':>10}  {'Ask Δ':>8}  {'Bid Δ':>8}")
    print(f"{'':>4}  {'':>6}  {'(median)':>10}  {'(median)':>10}  {'vs 1':>8}  {'vs 1':>8}")
    print("-" * 60)

    ask_1gpu = asks_all[asks_all['num_gpus'] == 1]['price_per_gpu'].median()
    bid_1gpu = bids_all[bids_all['num_gpus'] == 1]['price_per_gpu'].median()

    for n in gpu_counts:
        ask_n = asks_all[asks_all['num_gpus'] == n]
        bid_n = bids_all[bids_all['num_gpus'] == n]
        ask_med = ask_n['price_per_gpu'].median()
        bid_med = bid_n['price_per_gpu'].median()
        ask_discount = (ask_med - ask_1gpu) / ask_1gpu * 100
        bid_discount = (bid_med - bid_1gpu) / bid_1gpu * 100
        count = len(ask_n['id'].unique())
        print(f"{n:>4}  {count:>6}  ${ask_med:>8.3f}  ${bid_med:>8.3f}  {ask_discount:>+7.1f}%  {bid_discount:>+7.1f}%")

    print("\n" + "=" * 60)


def main():
    merged, asks, bids, asks_all, bids_all = load_data_for_analysis()

    print_summary(merged, asks, bids, asks_all, bids_all)

    plot_market_prices(asks, bids)
    plot_spread(merged)
    plot_supply(asks)
    plot_per_gpu_over_time(asks_all, bids_all)

    plt.show()


if __name__ == '__main__':
    main()
