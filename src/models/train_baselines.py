"""Train and evaluate transparent power-estimation baselines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


FEATURES = [
    "observed_temperature_c",
    "observed_humidity_pct",
    "observed_voltage_v",
    "observed_current_a",
    "observed_power_w",
    "observed_people_count",
    "hour_sin",
    "hour_cos",
]
TARGET = "true_power_w"


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    timestamp = pd.to_datetime(result["timestamp_utc"], utc=True, format="mixed")
    hour = timestamp.dt.hour + timestamp.dt.minute / 60.0
    result["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    result["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    result = result[result["packet_received"].astype(str).str.lower().eq("true")]
    return result.dropna(subset=FEATURES + [TARGET]).reset_index(drop=True)


def split_by_scenario(
    frame: pd.DataFrame, model_config: dict
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_ids = set(model_config["train_scenarios"])
    validation_ids = set(model_config["validation_scenarios"])
    test_ids = set(model_config["test_scenarios"])
    if (train_ids & validation_ids) or (train_ids & test_ids) or (validation_ids & test_ids):
        raise ValueError("Train, validation, dan test scenario harus saling terpisah.")
    train = frame[frame["scenario_id"].isin(train_ids)].copy()
    validation = frame[frame["scenario_id"].isin(validation_ids)].copy()
    test = frame[frame["scenario_id"].isin(test_ids)].copy()
    if train.empty or validation.empty or test.empty:
        raise ValueError("Set train, validation, atau test kosong.")
    return train, validation, test


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "mae_w": float(mean_absolute_error(y_true, y_pred)),
        "rmse_w": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def evaluate_predictions(test: pd.DataFrame, predictions: dict[str, np.ndarray]) -> dict:
    report: dict[str, dict] = {}
    y_true = test[TARGET].to_numpy()
    for name, predicted in predictions.items():
        model_report = {
            "overall": _metrics(y_true, predicted),
            "by_scenario": {},
            "by_run": {},
        }
        for scenario, indexes in test.groupby("scenario_id").groups.items():
            positions = test.index.get_indexer(indexes)
            model_report["by_scenario"][scenario] = _metrics(
                y_true[positions], predicted[positions]
            )
        for run_id, indexes in test.groupby("run_id").groups.items():
            positions = test.index.get_indexer(indexes)
            model_report["by_run"][run_id] = _metrics(
                y_true[positions], predicted[positions]
            )
        run_metrics = list(model_report["by_run"].values())
        model_report["run_level_summary"] = {}
        for metric in ("mae_w", "rmse_w", "r2"):
            values = np.asarray([item[metric] for item in run_metrics], dtype=float)
            mean = float(values.mean())
            standard_deviation = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            margin = 1.96 * standard_deviation / np.sqrt(len(values))
            model_report["run_level_summary"][metric] = {
                "n_runs": int(len(values)),
                "mean": mean,
                "standard_deviation": standard_deviation,
                "ci95_low": float(mean - margin),
                "ci95_high": float(mean + margin),
            }
        report[name] = model_report
    return report


def train_and_evaluate(frame: pd.DataFrame, config: dict) -> tuple[dict, dict]:
    prepared = prepare(frame)
    train, validation, test = split_by_scenario(prepared, config["model"])
    train = train.reset_index(drop=True)
    validation = validation.reset_index(drop=True)
    test = test.reset_index(drop=True)
    x_train, y_train = train[FEATURES], train[TARGET]

    models = {
        "ridge": TransformedTargetRegressor(
            regressor=make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
            transformer=StandardScaler(),
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=int(config["model"]["random_forest_trees"]),
            min_samples_leaf=3,
            max_features=0.8,
            n_jobs=-1,
            random_state=int(config["model"]["random_state"]),
        ),
    }
    for model in models.values():
        model.fit(x_train, y_train)

    def predictions_for(frame_to_score: pd.DataFrame) -> dict[str, np.ndarray]:
        x = frame_to_score[FEATURES]
        return {
            "constant_train_median": np.full(
                len(frame_to_score), float(y_train.median())
            ),
            "firmware_v_times_i": frame_to_score["observed_power_w"].to_numpy(),
            "ridge": models["ridge"].predict(x),
            "random_forest": models["random_forest"].predict(x),
        }

    validation_predictions = predictions_for(validation)
    test_predictions = predictions_for(test)
    validation_metrics = evaluate_predictions(validation, validation_predictions)
    test_metrics = evaluate_predictions(test, test_predictions)
    selected_model_name = min(
        models,
        key=lambda name: validation_metrics[name]["overall"]["mae_w"],
    )
    report = {
        "evaluation_design": {
            "split_unit": "held-out scenario_id; uncertainty summarized across run_id",
            "train_rows": int(len(train)),
            "validation_rows": int(len(validation)),
            "test_rows": int(len(test)),
            "train_runs": sorted(train["run_id"].unique().tolist()),
            "validation_runs": sorted(validation["run_id"].unique().tolist()),
            "test_runs": sorted(test["run_id"].unique().tolist()),
            "train_scenarios": sorted(train["scenario_id"].unique().tolist()),
            "validation_scenarios": sorted(validation["scenario_id"].unique().tolist()),
            "test_scenarios": sorted(test["scenario_id"].unique().tolist()),
            "target": TARGET,
            "features": FEATURES,
            "warning": "Metrics quantify synthetic scenarios, not field generalization.",
        },
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "metrics": test_metrics,
        "model_selection": {
            "criterion": "lowest validation MAE",
            "selected_model": selected_model_name,
            "test_metrics_not_used_for_selection": True,
        },
    }
    artifact = {
        "model": models[selected_model_name],
        "features": FEATURES,
        "target": TARGET,
        "model_name": selected_model_name,
        "scope": "synthetic_calibrated_scenarios_only",
        "train_scenarios": sorted(train["scenario_id"].unique().tolist()),
        "held_out_test_scenarios": sorted(test["scenario_id"].unique().tolist()),
    }
    return report, artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.json"))
    parser.add_argument("--input", type=Path, default=Path("outputs/synthetic_telemetry.csv"))
    parser.add_argument("--metrics", type=Path, default=Path("outputs/model_metrics.json"))
    parser.add_argument("--model", type=Path, default=Path("outputs/power_estimator.joblib"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    report, artifact = train_and_evaluate(pd.read_csv(args.input), config)
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.write_text(json.dumps(report, indent=2), encoding="utf-8")
    joblib.dump(artifact, args.model)
    selected_name = report["model_selection"]["selected_model"]
    selected = report["metrics"][selected_name]["overall"]
    print(
        f"Evaluasi tersimpan: {args.metrics}; "
        f"{selected_name} test MAE={selected['mae_w']:.3f} W, "
        f"R²={selected['r2']:.3f}"
    )


if __name__ == "__main__":
    main()
