"""Audit and adapt the legacy augmented CSV as an architecture workload.

The 2,027,520-row file is deliberately excluded from model fitting and model
evaluation. It is converted only into a canonical telemetry sample for the
edge-cloud latency/throughput benchmark.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


LEGACY_COLUMNS = {
    "Timestamp": "timestamp_utc",
    "DeviceID": "device_id",
    "Suhu (C)": "observed_temperature_c",
    "Kelembaban (%)": "observed_humidity_pct",
    "Tegangan (V)": "observed_voltage_v",
    "Arus (A)": "observed_current_a",
    "Daya (W)": "observed_power_w",
    "Jumlah Orang": "observed_people_count",
}

NUMERIC_COLUMNS = [
    "Suhu (C)",
    "Kelembaban (%)",
    "Tegangan (V)",
    "Arus (A)",
    "Daya (W)",
    "Jumlah Orang",
]


def _canonicalize(sample: pd.DataFrame, reference_rows: int) -> pd.DataFrame:
    result = sample.rename(columns=LEGACY_COLUMNS).copy()
    result["timestamp_utc"] = pd.to_datetime(
        result["timestamp_utc"], utc=True, format="mixed"
    ).astype(str)
    for column in LEGACY_COLUMNS.values():
        if column.startswith("observed_"):
            result[column] = pd.to_numeric(result[column], errors="coerce")
    result["observed_people_count"] = result["observed_people_count"].fillna(0.0)
    result["source_type"] = "legacy_augmented_replay"
    result["scenario_id"] = "architecture_stress_replay"
    result["replay_block_id"] = (
        result["legacy_row_index"] // reference_rows
    ).astype(int)
    result["source_row_index"] = (
        result["legacy_row_index"] % reference_rows
    ).astype(int)
    result["run_id"] = result["replay_block_id"].map(
        lambda value: f"legacy_replay_block_{value:02d}"
    )
    result["packet_received"] = True
    return result[
        [
            "timestamp_utc",
            "device_id",
            "scenario_id",
            "run_id",
            "source_type",
            "replay_block_id",
            "source_row_index",
            "observed_temperature_c",
            "observed_humidity_pct",
            "observed_voltage_v",
            "observed_current_a",
            "observed_power_w",
            "observed_people_count",
            "packet_received",
        ]
    ].reset_index(drop=True)


def prepare_augmented_workload(
    path: Path,
    *,
    expected_rows: int,
    reference_rows: int,
    sample_size: int,
    chunk_size: int = 100_000,
) -> tuple[pd.DataFrame, dict]:
    """Return an evenly-spaced canonical sample plus a full-file audit."""

    if expected_rows <= 0 or reference_rows <= 0 or sample_size <= 0:
        raise ValueError("expected_rows, reference_rows, dan sample_size harus positif.")

    selected_positions = np.unique(
        np.linspace(
            0,
            expected_rows - 1,
            min(sample_size, expected_rows),
            dtype=np.int64,
        )
    )
    selected_chunks: list[pd.DataFrame] = []
    total_rows = 0
    timestamp_min: str | None = None
    timestamp_max: str | None = None
    device_ids: set[str] = set()
    zero_counts = {column: 0 for column in NUMERIC_COLUMNS}
    missing_counts = {column: 0 for column in LEGACY_COLUMNS}

    reader = pd.read_csv(path, usecols=list(LEGACY_COLUMNS), chunksize=chunk_size)
    for chunk in reader:
        start = total_rows
        stop = start + len(chunk)
        positions = selected_positions[
            (selected_positions >= start) & (selected_positions < stop)
        ]
        if positions.size:
            selected = chunk.iloc[positions - start].copy()
            selected["legacy_row_index"] = positions
            selected_chunks.append(selected)

        timestamps = chunk["Timestamp"].dropna().astype(str)
        if not timestamps.empty:
            chunk_min = timestamps.min()
            chunk_max = timestamps.max()
            timestamp_min = chunk_min if timestamp_min is None else min(timestamp_min, chunk_min)
            timestamp_max = chunk_max if timestamp_max is None else max(timestamp_max, chunk_max)
        device_ids.update(chunk["DeviceID"].dropna().astype(str).unique())
        for column in NUMERIC_COLUMNS:
            numeric = pd.to_numeric(chunk[column], errors="coerce")
            zero_counts[column] += int(numeric.eq(0).sum())
        for column in LEGACY_COLUMNS:
            missing_counts[column] += int(chunk[column].isna().sum())
        total_rows = stop

    if not selected_chunks:
        raise ValueError(f"Tidak ada sampel yang dapat dibaca dari {path}.")

    sample = _canonicalize(pd.concat(selected_chunks, ignore_index=True), reference_rows)
    exact_blocks = total_rows / reference_rows
    audit = {
        "status": "architecture_workload_only",
        "source": {
            "path": str(path),
            "rows": total_rows,
            "expected_rows": expected_rows,
            "expected_rows_match": total_rows == expected_rows,
            "timestamp_start": timestamp_min,
            "timestamp_end": timestamp_max,
            "device_count": len(device_ids),
            "device_ids": sorted(device_ids),
        },
        "provenance": {
            "reference_rows": reference_rows,
            "inferred_replay_blocks": exact_blocks,
            "integer_replay_blocks": bool(exact_blocks.is_integer()),
            "relationship": (
                "Legacy augmented file: sequential replays derived from the "
                "single historical reference trace."
            ),
            "source_type": "legacy_augmented_replay",
        },
        "quality": {
            "zero_counts": zero_counts,
            "missing_counts": missing_counts,
        },
        "benchmark_sample": {
            "method": "evenly spaced positions across the complete augmented file",
            "requested_rows": sample_size,
            "selected_rows": len(sample),
            "covered_replay_blocks": sorted(
                int(value) for value in sample["replay_block_id"].unique()
            ),
        },
        "research_role": {
            "allowed": [
                "edge-cloud workload replay",
                "latency and throughput benchmark",
                "Digital Twin Web-3D telemetry demonstration",
            ],
            "prohibited": [
                "model accuracy validation",
                "independent field-observation count",
                "random train-test split across replayed rows",
            ],
            "model_training_used": False,
            "model_validation_used": False,
            "model_test_used": False,
        },
    }
    return sample, audit
