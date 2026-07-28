"""Compare synthetic observations with the real calibration trace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.audit_trace import load_trace


MAPPING = {
    "temperature_c": "observed_temperature_c",
    "humidity_pct": "observed_humidity_pct",
    "voltage_v": "observed_voltage_v",
    "current_a": "observed_current_a",
    "power_w": "observed_power_w",
    "people_count": "observed_people_count",
}


def _acf(series: pd.Series, lag: int) -> float | None:
    values = series.dropna().to_numpy(dtype=float)
    if values.size <= lag or np.std(values) == 0:
        return None
    return float(np.corrcoef(values[:-lag], values[lag:])[0, 1])


def _quantile_distance(real: pd.Series, synthetic: pd.Series) -> dict:
    quantiles = np.array([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    real_q = real.dropna().quantile(quantiles).to_numpy(dtype=float)
    synthetic_q = synthetic.dropna().quantile(quantiles).to_numpy(dtype=float)
    scale = max(float(np.ptp(real_q)), 1e-9)
    return {
        "real_quantiles": dict(zip(quantiles.astype(str), real_q.tolist())),
        "synthetic_quantiles": dict(zip(quantiles.astype(str), synthetic_q.tolist())),
        "normalized_quantile_mae": float(np.mean(np.abs(real_q - synthetic_q)) / scale),
    }


def _compare_variables(real: pd.DataFrame, synthetic: pd.DataFrame) -> dict:
    variables = {}
    for real_name, synthetic_name in MAPPING.items():
        comparison = _quantile_distance(real[real_name], synthetic[synthetic_name])
        comparison["real_zero_rate"] = float((real[real_name].dropna() == 0).mean())
        comparison["synthetic_zero_rate"] = float(
            (synthetic[synthetic_name].dropna() == 0).mean()
        )
        comparison["real_acf_lag_1"] = _acf(real[real_name], 1)
        comparison["synthetic_acf_lag_1"] = _acf(synthetic[synthetic_name], 1)
        variables[real_name] = comparison
    return variables


def validate(real: pd.DataFrame, synthetic: pd.DataFrame) -> dict:
    normal = synthetic[synthetic["scenario_id"].eq("normal")]
    by_scenario = {
        scenario: _compare_variables(real, group)
        for scenario, group in synthetic.groupby("scenario_id")
    }
    calibration_variables = _compare_variables(
        real, normal if not normal.empty else synthetic
    )
    acceptance = {}
    for variable, comparison in calibration_variables.items():
        checks = {
            "normalized_quantile_mae_lte_0_10": bool(
                comparison["normalized_quantile_mae"] <= 0.10
            ),
            "zero_rate_absolute_error_lte_0_03": bool(
                abs(
                    comparison["real_zero_rate"]
                    - comparison["synthetic_zero_rate"]
                )
                <= 0.03
            ),
            "acf_lag_1_absolute_error_lte_0_20": bool(
                comparison["real_acf_lag_1"] is not None
                and comparison["synthetic_acf_lag_1"] is not None
                and abs(
                    comparison["real_acf_lag_1"]
                    - comparison["synthetic_acf_lag_1"]
                )
                <= 0.20
            ),
        }
        acceptance[variable] = {
            "checks": checks,
            "accepted": bool(all(checks.values())),
        }
    overall_accepted = bool(all(item["accepted"] for item in acceptance.values()))
    return {
        "status": "diagnostic_only",
        "interpretation": (
            "Kemiripan distribusi bukan bukti bahwa data sintetis adalah observasi nyata. "
            "Hasil model tetap harus dilaporkan sebagai evaluasi berbasis simulasi."
        ),
        "real_rows": int(len(real)),
        "synthetic_rows": int(len(synthetic)),
        "synthetic_runs": int(synthetic["run_id"].nunique()),
        "packet_loss_rate": float((~synthetic["packet_received"].astype(bool)).mean()),
        "calibration_comparison": {
            "basis": "real trace versus normal synthetic scenario",
            "variables": calibration_variables,
            "acceptance_criteria": {
                "thresholds_are_predeclared_diagnostic_tolerances": True,
                "by_variable": acceptance,
                "overall_accepted": overall_accepted,
            },
        },
        "sensitivity_by_scenario": by_scenario,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", type=Path, required=True)
    parser.add_argument("--synthetic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(load_trace(args.real), pd.read_csv(args.synthetic))
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Validasi diagnostik tersimpan: {args.output}")


if __name__ == "__main__":
    main()
