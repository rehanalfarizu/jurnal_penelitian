"""Prepare the 2,027,520-row historical replay with explicit provenance.

The source CSV contains 22 repetitions of a transformed 92,160-row historical
trace.  It is an architecture workload, not 2,027,520 independent field
observations.  The transformation program is unavailable, so this module
verifies the relationship empirically instead of assuming row-count equality
is sufficient provenance.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.audit_trace import integrate_legacy_energy, load_trace


LEGACY_COLUMNS = {
    "Timestamp": "replay_timestamp_utc",
    "DeviceID": "device_id",
    "Suhu (C)": "temperature_c",
    "Kelembaban (%)": "humidity_pct",
    "Tegangan (V)": "voltage_v",
    "Arus (A)": "current_a",
    "Daya (W)": "power_legacy_w",
    "Jumlah Orang": "people_count",
}
NUMERIC_COLUMNS = list(LEGACY_COLUMNS)[2:]
PAYLOAD_COLUMNS = list(LEGACY_COLUMNS)[1:]
REFERENCE_COLUMNS = {
    "DeviceID": "device_id",
    "Suhu (C)": "temperature_c",
    "Kelembaban (%)": "humidity_pct",
    "Tegangan (V)": "voltage_v",
    "Arus (A)": "current_a",
    "Daya (W)": "power_w",
    "Jumlah Orang": "people_count",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _equality_mask(
    left: pd.Series | np.ndarray,
    right: pd.Series | np.ndarray,
    *,
    numeric: bool,
) -> np.ndarray:
    """Compare aligned arrays while treating paired missing values as equal."""
    if numeric:
        left_values = pd.to_numeric(
            pd.Series(left, copy=False), errors="coerce"
        ).to_numpy(dtype=float)
        right_values = pd.to_numeric(
            pd.Series(right, copy=False), errors="coerce"
        ).to_numpy(dtype=float)
        return np.isclose(
            left_values,
            right_values,
            rtol=0.0,
            atol=1e-9,
            equal_nan=True,
        )

    left_values = pd.Series(left, copy=False).astype("string").fillna("<NA>")
    right_values = pd.Series(right, copy=False).astype("string").fillna("<NA>")
    return left_values.to_numpy() == right_values.to_numpy()


def _compare_first_block_to_reference(
    first_block: pd.DataFrame,
    reference_frame: pd.DataFrame,
) -> dict:
    """Quantify which legacy-derived values differ from the exported workbook."""
    if len(first_block) != len(reference_frame):
        raise ValueError(
            "Blok replay pertama dan trace rujukan tidak memiliki jumlah baris "
            "yang sama."
        )

    by_column: dict[str, dict] = {}
    total_changed = 0
    for legacy_column, reference_column in REFERENCE_COLUMNS.items():
        matches = _equality_mask(
            first_block[legacy_column],
            reference_frame[reference_column],
            numeric=legacy_column in NUMERIC_COLUMNS,
        )
        match_count = int(matches.sum())
        changed_count = int(len(matches) - match_count)
        total_changed += changed_count
        by_column[reference_column] = {
            "rows_compared": int(len(matches)),
            "match_count": match_count,
            "changed_count": changed_count,
            "match_rate": float(match_count / len(matches)),
        }

    return {
        "rows_compared": int(len(first_block)),
        "all_payload_values_equal": total_changed == 0,
        "total_changed_cells": total_changed,
        "comparison_tolerance": (
            "strings exact after missing-value normalization; numerics "
            "absolute tolerance 1e-9"
        ),
        "by_column": by_column,
    }


def _canonicalize(
    sample: pd.DataFrame,
    reference_rows: int,
    source_timestamps: pd.Series | None,
    energy_lookup: pd.DataFrame,
) -> pd.DataFrame:
    result = sample.rename(columns=LEGACY_COLUMNS).copy()
    replay_ts = pd.to_datetime(
        result["replay_timestamp_utc"], utc=True, format="mixed", errors="coerce"
    )
    result["replay_timestamp_utc"] = replay_ts.map(
        lambda value: value.isoformat() if pd.notna(value) else None
    )
    result["timestamp_utc"] = result["replay_timestamp_utc"]
    for column in (
        "temperature_c",
        "humidity_pct",
        "voltage_v",
        "current_a",
        "power_legacy_w",
        "people_count",
    ):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result["people_count"] = result["people_count"].fillna(0).round().astype(int)
    result["replay_block_id"] = (
        result["legacy_row_index"] // reference_rows
    ).astype(int)
    result["source_row_index"] = (
        result["legacy_row_index"] % reference_rows
    ).astype(int)
    result["source_row_id"] = result["source_row_index"].map(
        lambda value: f"historical:{int(value):06d}"
    )
    result["replay_id"] = result["replay_block_id"].map(
        lambda value: f"historical_replay_{int(value):02d}"
    )
    result["source_type"] = "historical_replay"
    if source_timestamps is not None:
        mapping = source_timestamps.reset_index(drop=True)
        result["source_timestamp_utc"] = result["source_row_index"].map(
            lambda index: (
                mapping.iloc[int(index)].isoformat()
                if int(index) < len(mapping) and pd.notna(mapping.iloc[int(index)])
                else None
            )
        )
    else:
        result["source_timestamp_utc"] = None

    computed = (result["voltage_v"] * result["current_a"]).round(1)
    result["power_formula_w"] = computed
    result["power_consistency_error_w"] = (
        result["power_legacy_w"] - computed
    ).abs()
    result["voltage_status"] = np.where(result["voltage_v"] > 0, "normal", "invalid")
    result["current_status"] = np.where(
        result["current_a"] >= 0.1, "normal", "below_threshold"
    )
    result["occupancy_status"] = np.where(
        result["people_count"] > 0, "occupied", "unoccupied"
    )
    for column in energy_lookup.columns:
        result[column] = result["source_row_index"].map(
            energy_lookup[column]
        )
    return result[
        [
            "timestamp_utc",
            "source_timestamp_utc",
            "replay_timestamp_utc",
            "device_id",
            "source_type",
            "replay_id",
            "replay_block_id",
            "source_row_id",
            "source_row_index",
            "temperature_c",
            "humidity_pct",
            "voltage_v",
            "current_a",
            "power_legacy_w",
            "power_formula_w",
            "power_consistency_error_w",
            "energy_interval_legacy_wh",
            "energy_cumulative_legacy_wh",
            "energy_integration_status",
            "people_count",
            "occupancy_status",
            "voltage_status",
            "current_status",
        ]
    ].reset_index(drop=True)


def _build_energy_lookup(
    first_block: pd.DataFrame,
    source_timestamps: pd.Series | None,
    *,
    max_gap_seconds: float,
) -> tuple[pd.DataFrame, dict]:
    """Integrate the replay payload while keeping it distinct from field data."""
    timestamp_source = (
        source_timestamps.reset_index(drop=True)
        if source_timestamps is not None
        else first_block["Timestamp"].reset_index(drop=True)
    )
    lookup, audit = integrate_legacy_energy(
        timestamp_source,
        first_block["Daya (W)"],
        max_gap_seconds=max_gap_seconds,
        timestamp_basis=(
            "exported_workbook_source_timestamp"
            if source_timestamps is not None
            else "legacy_replay_timestamp"
        ),
        measurement_role="historical_replay_payload",
    )
    audit["interpretation"] = (
        "Derived from the transformed CSV replay payload. It supports the "
        "replay API and workload demonstration only; the field-trace energy "
        "is calculated separately from the exported XLSX. The cumulative "
        "value resets for each replay cycle."
    )
    return lookup, audit


def prepare_historical_replay(
    path: Path,
    *,
    expected_rows: int,
    reference_rows: int,
    sample_size: int,
    reference_trace: Path | None = None,
    chunk_size: int = 100_000,
    max_energy_gap_seconds: float = 10.0,
) -> tuple[pd.DataFrame, dict]:
    """Return an evenly spaced canonical sample and a full-file provenance audit."""
    if expected_rows <= 0 or reference_rows <= 0 or sample_size <= 0:
        raise ValueError("expected_rows, reference_rows, dan sample_size harus positif.")

    first_block = pd.read_csv(
        path,
        usecols=list(LEGACY_COLUMNS),
        nrows=reference_rows,
    )
    if len(first_block) != reference_rows:
        raise ValueError(
            f"Blok replay pertama hanya berisi {len(first_block):,} baris; "
            f"dibutuhkan {reference_rows:,} baris."
        )
    baseline_payload = {
        column: (
            pd.to_numeric(first_block[column], errors="coerce").to_numpy(dtype=float)
            if column in NUMERIC_COLUMNS
            else first_block[column].astype("string").fillna("<NA>").to_numpy()
        )
        for column in PAYLOAD_COLUMNS
    }

    reference_frame = None
    source_timestamps = None
    first_block_reference_comparison = None
    if reference_trace is not None:
        reference_frame = load_trace(reference_trace)
        if len(reference_frame) != reference_rows:
            raise ValueError("Jumlah baris trace rujukan tidak sesuai reference_rows.")
        source_timestamps = reference_frame["timestamp"]
        first_block_reference_comparison = _compare_first_block_to_reference(
            first_block,
            reference_frame,
        )

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
    previous_timestamp: pd.Timestamp | None = None
    non_monotonic_timestamps = 0
    duplicate_timestamps = 0
    device_ids: set[str] = set()
    zero_counts = {column: 0 for column in NUMERIC_COLUMNS}
    missing_counts = {column: 0 for column in LEGACY_COLUMNS}
    cross_block_mismatch_counts = {column: 0 for column in PAYLOAD_COLUMNS}

    for chunk in pd.read_csv(path, usecols=list(LEGACY_COLUMNS), chunksize=chunk_size):
        start = total_rows
        stop = start + len(chunk)
        source_indices = np.arange(start, stop, dtype=np.int64) % reference_rows
        positions = selected_positions[
            (selected_positions >= start) & (selected_positions < stop)
        ]
        if positions.size:
            selected = chunk.iloc[positions - start].copy()
            selected["legacy_row_index"] = positions
            selected_chunks.append(selected)

        timestamps = pd.to_datetime(
            chunk["Timestamp"], utc=True, format="mixed", errors="coerce"
        )
        valid_ts = timestamps.dropna()
        if not valid_ts.empty:
            if previous_timestamp is not None:
                non_monotonic_timestamps += int(valid_ts.iloc[0] < previous_timestamp)
                duplicate_timestamps += int(valid_ts.iloc[0] == previous_timestamp)
            non_monotonic_timestamps += int((valid_ts.diff().dropna() < pd.Timedelta(0)).sum())
            duplicate_timestamps += int(valid_ts.duplicated().sum())
            previous_timestamp = valid_ts.iloc[-1]
            chunk_min = valid_ts.min().isoformat()
            chunk_max = valid_ts.max().isoformat()
            timestamp_min = chunk_min if timestamp_min is None else min(timestamp_min, chunk_min)
            timestamp_max = chunk_max if timestamp_max is None else max(timestamp_max, chunk_max)

        device_ids.update(chunk["DeviceID"].dropna().astype(str).unique())
        for column in NUMERIC_COLUMNS:
            numeric = pd.to_numeric(chunk[column], errors="coerce")
            zero_counts[column] += int(numeric.eq(0).sum())
        for column in LEGACY_COLUMNS:
            missing_counts[column] += int(chunk[column].isna().sum())
        for column in PAYLOAD_COLUMNS:
            expected_values = baseline_payload[column][source_indices]
            matches = _equality_mask(
                chunk[column],
                expected_values,
                numeric=column in NUMERIC_COLUMNS,
            )
            cross_block_mismatch_counts[column] += int((~matches).sum())
        total_rows = stop

    if not selected_chunks:
        raise ValueError(f"Tidak ada sampel yang dapat dibaca dari {path}.")
    if total_rows != expected_rows:
        raise ValueError(
            f"Jumlah baris replay {total_rows:,} tidak sama dengan ekspektasi "
            f"{expected_rows:,}."
        )

    energy_lookup, energy_audit = _build_energy_lookup(
        first_block,
        source_timestamps,
        max_gap_seconds=max_energy_gap_seconds,
    )
    sample = _canonicalize(
        pd.concat(selected_chunks, ignore_index=True),
        reference_rows,
        source_timestamps,
        energy_lookup,
    )
    exact_blocks = total_rows / reference_rows
    block_count = int(exact_blocks) if exact_blocks.is_integer() else exact_blocks
    covered_blocks = sorted(int(value) for value in sample["replay_block_id"].unique())
    blocks_repeat_first_payload = (
        bool(exact_blocks.is_integer())
        and not any(cross_block_mismatch_counts.values())
    )
    transformed_from_reference = (
        first_block_reference_comparison is not None
        and not first_block_reference_comparison["all_payload_values_equal"]
    )
    if blocks_repeat_first_payload and transformed_from_reference:
        lineage_classification = (
            "deterministic_replay_of_transformed_historical_trace"
        )
    elif blocks_repeat_first_payload and first_block_reference_comparison:
        lineage_classification = "deterministic_replay_of_raw_historical_trace"
    elif blocks_repeat_first_payload:
        lineage_classification = (
            "deterministic_replay_block_without_reference_comparison"
        )
    else:
        lineage_classification = "non_identical_replay_blocks"
    sample["lineage_classification"] = lineage_classification
    if first_block_reference_comparison is None:
        relationship = (
            f"The CSV contains {block_count} candidate repetitions of one "
            f"{reference_rows:,}-row block. No exported workbook was supplied "
            "for value-level lineage comparison; replay rows are not counted "
            "as independent field observations."
        )
    elif transformed_from_reference:
        relationship = (
            f"The CSV contains {block_count} deterministic repetitions of one "
            f"{reference_rows:,}-row legacy-derived block. The block differs "
            "from the exported workbook in audited fields and the legacy "
            "transformation code is unavailable; replay rows are therefore "
            "not raw copies or independent field observations."
        )
    else:
        relationship = (
            f"The CSV contains {block_count} deterministic repetitions of one "
            f"{reference_rows:,}-row block that matches the exported workbook "
            "on the audited payload fields. Repeated rows are not independent "
            "field observations."
        )
    audit = {
        "status": "historical_replay_workload",
        "source": {
            "path": str(path),
            "sha256": _sha256(path),
            "rows": total_rows,
            "expected_rows": expected_rows,
            "expected_rows_match": True,
            "timestamp_start_utc": timestamp_min,
            "timestamp_end_utc": timestamp_max,
            "duplicate_timestamps": duplicate_timestamps,
            "non_monotonic_timestamps": non_monotonic_timestamps,
            "device_count": len(device_ids),
            "device_ids": sorted(device_ids),
        },
        "provenance": {
            "reference_trace": str(reference_trace) if reference_trace else None,
            "reference_rows": reference_rows,
            "inferred_replay_blocks": exact_blocks,
            "integer_replay_blocks": bool(exact_blocks.is_integer()),
            "source_type": "historical_replay",
            "lineage_classification": lineage_classification,
            "source_row_identity_basis": (
                "Positional modulo mapping to the workbook row index; "
                "source_row_id denotes ancestry, not value equality."
            ),
            "relationship": relationship,
        },
        "lineage": {
            "classification": lineage_classification,
            "payload_columns_checked": PAYLOAD_COLUMNS,
            "all_replay_payloads_identical_to_first_block": (
                blocks_repeat_first_payload
            ),
            "cross_block_mismatch_counts": cross_block_mismatch_counts,
            "first_block_vs_exported_workbook": (
                first_block_reference_comparison
            ),
            "transformation_code_available": False,
            "interpretation": (
                "The full CSV is suitable as a deterministic replay workload. "
                "It must not be described as new measurements, independent "
                "samples, augmentation diversity, or a raw copy of the XLSX."
            ),
        },
        "quality": {
            "zero_counts": zero_counts,
            "missing_counts": missing_counts,
            "sample_power_consistency_error_w": {
                "mean": float(sample["power_consistency_error_w"].mean()),
                "p95": float(sample["power_consistency_error_w"].quantile(0.95)),
                "max": float(sample["power_consistency_error_w"].max()),
            },
            "energy_integration": energy_audit,
            "occupancy": {
                "occupied_sample_count": int(
                    sample["occupancy_status"].eq("occupied").sum()
                ),
                "unoccupied_sample_count": int(
                    sample["occupancy_status"].eq("unoccupied").sum()
                ),
                "people_count_sample_mean": float(
                    sample["people_count"].mean()
                ),
                "people_count_sample_max": int(
                    sample["people_count"].max()
                ),
            },
        },
        "benchmark_sample": {
            "method": "evenly spaced positions across all historical replay blocks",
            "requested_rows": sample_size,
            "selected_rows": len(sample),
            "covered_replay_blocks": covered_blocks,
        },
        "research_role": {
            "allowed": [
                "edge-cloud monitoring replay",
                "legacy-proxy energy integration over the source trace",
                "occupancy monitoring from the historical people-count field",
                "latency, throughput, routing, and freshness benchmark",
                "multiscale geospatial-building-indoor telemetry demonstration",
            ],
            "prohibited": [
                "independent field-observation count",
                "raw historical trace equivalence",
                "data augmentation diversity",
                "model accuracy validation",
                "field validation of active power",
                "calibrated active-energy measurement",
                "survey-validated geospatial accuracy",
            ],
            "independent_field_observations_claimed": False,
            "model_training_used": False,
        },
    }
    return sample, audit
