"""Audit the archived physical-sensor trace and its derived energy."""

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


def integrate_legacy_energy(
    timestamps: pd.Series,
    power: pd.Series,
    *,
    max_gap_seconds: float,
    timestamp_basis: str,
    measurement_role: str,
) -> tuple[pd.DataFrame, dict]:
    """Integrate recorded V×I power while exposing the metrological scope.

    The legacy firmware records RMS voltage and current and derives its power
    field as V×I. This helper therefore reports a reproducible monitoring
    indicator in Wh, not a direct kWh-meter channel or an active-power truth.
    """
    if max_gap_seconds <= 0:
        raise ValueError("max_gap_seconds harus positif.")

    timestamp_values = pd.to_datetime(
        timestamps, utc=True, format="mixed", errors="coerce"
    )
    power_values = pd.to_numeric(power, errors="coerce")
    interval_seconds = timestamp_values.diff().dt.total_seconds()
    previous_power = power_values.shift(1)
    valid = (
        interval_seconds.gt(0)
        & interval_seconds.le(max_gap_seconds)
        & power_values.notna()
        & previous_power.notna()
        & power_values.ge(0)
        & previous_power.ge(0)
    )
    interval_wh = pd.Series(0.0, index=power_values.index, dtype=float)
    interval_wh.loc[valid] = (
        (power_values.loc[valid] + previous_power.loc[valid])
        * 0.5
        * interval_seconds.loc[valid]
        / 3600.0
    )
    status = pd.Series(
        "gap_or_value_excluded", index=power_values.index, dtype="string"
    )
    status.loc[valid] = "integrated"
    if len(status):
        status.iloc[0] = "trace_start"

    lookup = pd.DataFrame(
        {
            "energy_interval_legacy_wh": interval_wh,
            "energy_cumulative_legacy_wh": interval_wh.cumsum(),
            "energy_integration_status": status,
        }
    )
    energy_wh = float(lookup["energy_cumulative_legacy_wh"].iloc[-1])
    audit = {
        "method": "trapezoidal_integration_of_recorded_legacy_v_times_i_power",
        "timestamp_basis": timestamp_basis,
        "measurement_role": measurement_role,
        "max_gap_seconds": float(max_gap_seconds),
        "trace_cycle_rows": int(len(power_values)),
        "integrated_intervals": int(valid.sum()),
        "excluded_intervals": int((~valid).sum()),
        "energy_wh": energy_wh,
        "trace_cycle_energy_legacy_wh": energy_wh,
        "active_energy_ground_truth": False,
        "interpretation": (
            "Derived from the recorded legacy V×I power field. It is a "
            "reproducible monitoring indicator, not a direct kWh-meter "
            "channel or an active-energy measurement with recorded "
            "power-factor evidence."
        ),
    }
    return lookup, audit


def audit_trace(path: Path, *, max_energy_gap_seconds: float = 10.0) -> dict:
    frame = load_trace(path)
    timestamp = frame["timestamp"].dropna()
    gaps = timestamp.diff().dt.total_seconds().dropna()
    regular = frame[NUMERIC_COLUMNS].replace([np.inf, -np.inf], np.nan)
    correlations = regular.corr(numeric_only=True).round(6)

    with path.open("rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()

    _, derived_energy = integrate_legacy_energy(
        frame["timestamp"],
        frame["power_w"],
        max_gap_seconds=max_energy_gap_seconds,
        timestamp_basis="exported_workbook_timestamp",
        measurement_role="archived_physical_sensor_trace",
    )

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
        "derived_energy": derived_energy,
        "limitations": [
            "Trace memakai satu device_id yang berfungsi sebagai label gateway agregasi Raspberry Pi; ID ini tidak mengidentifikasi atau menghitung setiap node sensor fisik.",
            "Arsitektur legacy menggabungkan akuisisi ESP32 dan alur gateway/okupansi Raspberry Pi, tetapi workbook tidak menyimpan source-node ID per baris.",
            "Firmware lama merekam sensor tegangan dan arus fisik, lalu menghitung daya sebagai tegangan dikali arus; faktor daya tidak direkam.",
            "Nilai nol dapat berarti beban mati, threshold sensor, atau kegagalan pembacaan.",
            "Jumlah orang berasal dari alur penyimpanan terpisah dan memiliki nilai hilang.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-energy-gap-seconds", type=float, default=10.0)
    args = parser.parse_args()
    result = audit_trace(
        args.input, max_energy_gap_seconds=args.max_energy_gap_seconds
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Audit tersimpan: {args.output} ({result['source']['rows']:,} baris)")


if __name__ == "__main__":
    main()
