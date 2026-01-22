#!/usr/bin/env python3
"""Analyze vast.ai RTX 5090 pricing data.

Focuses on 1-GPU offers for apples-to-apples comparison.
See docs/analysis.md for data structure documentation.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR = Path('data')


def load_matched_data():
    """Load asks/bids and match by (timestamp, machine_id, num_gpus)."""
    asks = pd.concat([
        pd.read_csv(f, parse_dates=['timestamp'])
        for f in DATA_DIR.glob('*-asks.csv')
    ], ignore_index=True)

    bids = pd.concat([
        pd.read_csv(f, parse_dates=['timestamp'])
        for f in DATA_DIR.glob('*-bids.csv')
    ], ignore_index=True)

    # Floor to minute to align asks/bids (they're ~4ms apart)
    asks['ts'] = asks['timestamp'].dt.floor('min')
    bids['ts'] = bids['timestamp'].dt.floor('min')

    # Filter to 1-GPU only
    asks = asks[asks['num_gpus'] == 1]
    bids = bids[bids['num_gpus'] == 1]

    # Match asks to bids by machine
    merged = asks.merge(
        bids,
        on=['ts', 'machine_id', 'num_gpus'],
        suffixes=('_ask', '_bid')
    )

    # Calculate spread
    merged['spread'] = merged['dph_total_ask'] - merged['dph_total_bid']

    return merged, asks, bids


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
    """Plot bid/ask spread over time."""
    fig, ax = plt.subplots(figsize=(12, 4))

    by_time = merged.groupby('ts')['spread'].agg(['median', 'mean', 'std'])

    ax.plot(by_time.index, by_time['median'], label='Median spread', marker='.', color='tab:blue')
    ax.fill_between(
        by_time.index,
        by_time['median'] - by_time['std'],
        by_time['median'] + by_time['std'],
        alpha=0.2
    )

    ax.axhline(0, color='black', linestyle='--', alpha=0.3)
    ax.set_xlabel('Time')
    ax.set_ylabel('Spread ($/hr)')
    ax.set_title('RTX 5090 1-GPU: Bid/Ask Spread (ask - bid)')
    ax.legend()
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


def print_summary(merged, asks, bids):
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


def main():
    merged, asks, bids = load_matched_data()

    print_summary(merged, asks, bids)

    plot_market_prices(asks, bids)
    plot_spread(merged)
    plot_supply(asks)

    plt.show()


if __name__ == '__main__':
    main()
