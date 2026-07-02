"""
compare_architectures.py — Compare resource metrics across edge/cloud/full-cloud
deployment architectures using the recorded streaming_results_z25.pkl.

Inputs:
  - streaming_results_z25.pkl: results from the EDGE-PREFERRED pipeline
    (records contain edge_latency_ms, cloud_latency_ms, total_latency_ms,
    routed_to_cloud, energy_mw).

Three architectures are simulated (counterfactual based on the same stream):

  1. EDGE_PREFERRED (recorded)
        edge-only when the local model is confident; cloud when routed_to_cloud
        energy = routed_to_cloud ? energy_cloud : energy_edge

  2. FULL_EDGE
        every record runs on the edge; latency = edge_latency_ms (or its
        local-only analog if we had edge-only runs); energy = edge energy.
        Estimated by assuming edge_latency_ms is the edge path's local cost.

  3. FULL_CLOUD
        every record is sent to the cloud; latency = cloud_latency_ms;
        energy = cloud transmission energy.

Resource metrics reported per architecture:
  - mean latency (ms)
  - P95 latency (ms)
  - mean power / energy-score (mW)
  - fraction routed to cloud
  - effective throughput (records/sec)

Output:
  - Prints a comparison table to stdout
  - Writes compare_architectures.json next to the script

Usage:
  python compare_architectures.py
"""
import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent


@dataclass
class RecordMetrics:
    sample_idx: int
    timestamp: str
    anomaly: bool
    routed_to_cloud: bool
    edge_latency_ms: float
    cloud_latency_ms: float
    total_latency_ms: float
    energy_mw: float
    energy_score: float
    r2_running: float
    r2_raw: float
    daya: float
    pred_daya: float


def load_records():
    with open(HERE / 'streaming_results_z25.pkl', 'rb') as f:
        results = pickle.load(f)
    df = pd.DataFrame([
        {
            'sample_idx': r.sample_idx,
            'timestamp': r.timestamp,
            'routed_to_cloud': bool(r.routed_to_cloud),
            'edge_latency_ms': float(r.edge_latency_ms),
            'cloud_latency_ms': float(r.cloud_latency_ms),
            'total_latency_ms': float(r.total_latency_ms),
            'energy_mw': float(r.energy_mw),
            'energy_score': float(r.energy_score),
        }
        for r in results
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.sort_values('sample_idx').reset_index(drop=True)


def summarize(df, label, latency_col):
    n = len(df)
    lat = df[latency_col].astype(float).values
    energy = df['energy_mw'].astype(float).values
    duration_s = max(1e-9, (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds())
    throughput = n / duration_s

    return {
        'architecture': label,
        'n': n,
        'latency_mean_ms': round(float(np.mean(lat)), 3),
        'latency_p50_ms': round(float(np.percentile(lat, 50)), 3),
        'latency_p95_ms': round(float(np.percentile(lat, 95)), 3),
        'latency_p99_ms': round(float(np.percentile(lat, 99)), 3),
        'latency_max_ms': round(float(np.max(lat)), 3),
        'energy_mean_mw': round(float(np.mean(energy)), 3),
        'energy_total_j': round(float(np.mean(energy) * np.mean(lat) / 1000.0) * n, 3),
        'fraction_routed_cloud': round(float(df['routed_to_cloud'].mean()), 6),
        'throughput_records_per_s': round(float(throughput), 1),
    }


def main():
    df = load_records()
    n = len(df)
    print('=' * 78)
    print(f'Loaded {n:,} stream results.')

    # Architecture 1 — recorded EDGE_PREFERRED
    arch1 = summarize(df, 'EDGE_PREFERRED (recorded)', 'total_latency_ms')

    # Architecture 2 — FULL_EDGE
    # Counterfactual: every record uses edge_latency_ms and the edge-energy cost.
    # We approximate "edge-only energy" with energy_mw of records that were
    # NOT routed to cloud in the recorded run.
    edge_only = df[~df['routed_to_cloud']]
    df_full_edge = df.copy()
    df_full_edge['routed_to_cloud'] = False
    # Replace each record's latency with a representative edge-only sample by
    # bootstrapping observed edge latencies; energy is held to the recorded
    # edge-energy distribution (energy_mw of routed=False records).
    rng = np.random.default_rng(seed=42)
    df_full_edge['edge_latency_ms'] = rng.choice(
        edge_only['edge_latency_ms'].values, size=n, replace=True
    )
    df_full_edge['total_latency_ms'] = df_full_edge['edge_latency_ms']
    df_full_edge['energy_mw'] = rng.choice(
        edge_only['energy_mw'].values, size=n, replace=True
    )
    arch2 = summarize(df_full_edge, 'FULL_EDGE (counterfactual)', 'total_latency_ms')

    # Architecture 3 — FULL_CLOUD
    # Counterfactual: every record uses cloud_latency_ms and the cloud-energy cost.
    cloud_only = df[df['routed_to_cloud']]
    df_full_cloud = df.copy()
    df_full_cloud['routed_to_cloud'] = True
    if len(cloud_only) == 0:
        # Fall back: no routing observed; use cloud fields on every record.
        df_full_cloud['cloud_latency_ms'] = df['cloud_latency_ms']
    else:
        rng2 = np.random.default_rng(seed=43)
        df_full_cloud['cloud_latency_ms'] = rng2.choice(
            cloud_only['cloud_latency_ms'].values, size=n, replace=True
        )
    df_full_cloud['total_latency_ms'] = df_full_cloud['cloud_latency_ms']
    if len(cloud_only) > 0:
        rng3 = np.random.default_rng(seed=44)
        df_full_cloud['energy_mw'] = rng3.choice(
            cloud_only['energy_mw'].values, size=n, replace=True
        )
    arch3 = summarize(df_full_cloud, 'FULL_CLOUD (counterfactual)', 'total_latency_ms')

    rows = [arch1, arch2, arch3]
    cols = ['latency_mean_ms', 'latency_p95_ms', 'energy_mean_mw',
            'fraction_routed_cloud', 'throughput_records_per_s']

    print()
    print('=' * 78)
    print('Architecture comparison')
    print('-' * 78)
    header = f"{'Architecture':<35} {'mean ms':>10} {'P95 ms':>10} {'energy mW':>11} " \
             f"{'to cloud':>10} {'rec/s':>12}"
    print(header)
    print('-' * 78)
    for r in rows:
        print(f"{r['architecture']:<35} {r['latency_mean_ms']:>10.2f} "
              f"{r['latency_p95_ms']:>10.2f} {r['energy_mean_mw']:>11.2f} "
              f"{r['fraction_routed_cloud']*100:>9.2f}% {r['throughput_records_per_s']:>12.1f}")

    # Ratios vs FULL_EDGE (typical comparison anchor)
    print()
    print('=' * 78)
    print('Ratios vs FULL_EDGE (baseline)')
    print('-' * 78)
    ratio_col = lambda a, b: 'n/a' if b == 0 else f"{a / b:.2f}x"
    for r in [arch1, arch3]:
        ratio_lat = ratio_col(r['latency_mean_ms'], arch2['latency_mean_ms'])
        ratio_p95 = ratio_col(r['latency_p95_ms'], arch2['latency_p95_ms'])
        ratio_pow = ratio_col(r['energy_mean_mw'], arch2['energy_mean_mw'])
        print(f"  {r['architecture']:<35} latency_mean={ratio_lat:>6}  "
              f"P95={ratio_p95:>6}  energy={ratio_pow:>6}")

    # Save JSON
    summary = {
        'n_records': n,
        'duration_s': round(float((df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds()), 3),
        'architectures': rows,
    }
    out_path = HERE / 'compare_architectures.json'
    with open(out_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print()
    print(f'Saved: {out_path.name}')


if __name__ == '__main__':
    main()
