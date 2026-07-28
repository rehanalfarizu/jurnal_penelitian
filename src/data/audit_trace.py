"""Audit the real trace and write machine-readable calibration statistics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


COLUMNS = {
    "Timestamp": "timestamp",
    "DeviceID": "device_id",
    "Suhu (C)": "temperature_c",
    "Kelembaban (%)": "humidity_pct",
    "Tegangan (V)": "voltage_v",
    "Arus (A)": "current_a",
    "Daya (W)": "power_w",
    "Jumlah Orang": "people_count",
}
NUMERIC_COLUMNS = [
    "temperature_c",
    "humidity_pct",
    "voltage_v",
    "current_a",
    "power_w",
    "people_count",
]


def load_trace(path: Path) -> pd.DataFrame:
    """Load the exported workbook and normalize its original Indonesian headers."""
    frame = pd.read_excel(path, sheet_name="Sensor Data")
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan: {sorted(missing)}")
    frame = frame.rename(columns=COLUMNS)[list(COLUMNS.values())]
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("timestamp").reset_index(drop=True)


def _series_summary(series: pd.Series) -> dict:
    values = series.dropna().astype(float)
    quantiles = values.quantile([0.01, 0.05, 0.5, 0.95, 0.99])
    return {
        "count": int(values.size),
        "missing": int(series.isna().sum()),
        "zero_rate": float((values == 0).mean()) if values.size else None,
        "mean": float(values.mean()) if values.size else None,
        "std": float(values.std()) if values.size > 1 else None,
        "min": float(values.min()) if values.size else None,
        "p01": float(quantiles.loc[0.01]) if values.size else None,
        "p05": float(quantiles.loc[0.05]) if values.size else None,
        "p50": float(quantiles.loc[0.5]) if values.size else None,
        "p95": float(quantiles.loc[0.95]) if values.size else None,
        "p99": float(quantiles.loc[0.99]) if values.size else None,
        "max": float(values.max()) if values.size else None,
    }


def audit_trace(path: Path) -> dict:
    frame = load_trace(path)
    timestamp = frame["timestamp"].dropna()
    gaps = timestamp.diff().dt.total_seconds().dropna()
    regular = frame[NUMERIC_COLUMNS].replace([np.inf, -np.inf], np.nan)
    correlations = regular.corr(numeric_only=True).round(6)

    with path.open("rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()

    return {
        "source": {
            "path": str(path),
            "sha256": digest,
            "rows": int(len(frame)),
            "device_count": int(frame["device_id"].nunique(dropna=True)),
            "device_ids": sorted(frame["device_id"].dropna().astype(str).unique().tolist()),
            "timestamp_start_utc": timestamp.min().isoformat() if not timestamp.empty else None,
            "timestamp_end_utc": timestamp.max().isoformat() if not timestamp.empty else None,
            "duplicate_timestamps": int(timestamp.duplicated().sum()),
        },
        "sampling": {
            "gap_seconds_p50": float(gaps.quantile(0.5)),
            "gap_seconds_p95": float(gaps.quantile(0.95)),
            "gap_seconds_p99": float(gaps.quantile(0.99)),
            "gap_seconds_max": float(gaps.max()),
        },
        "variables": {column: _series_summary(frame[column]) for column in NUMERIC_COLUMNS},
        "pearson_correlation": correlations.to_dict(),
        "limitations": [
            "Trace berasal dari satu device_id dan satu periode sekitar empat hari.",
            "Daya pada firmware lama dihitung sebagai tegangan dikali arus; faktor daya tidak diukur.",
            "Nilai nol dapat berarti beban mati, threshold sensor, atau kegagalan pembacaan.",
            "Jumlah orang berasal dari alur penyimpanan terpisah dan memiliki nilai hilang.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_trace(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Audit tersimpan: {args.output} ({result['source']['rows']:,} baris)")


if __name__ == "__main__":
    main()
