import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from src.data.generate_synthetic import generate_run
from src.data.prepare_augmented_workload import prepare_augmented_workload
from src.models.train_baselines import (
    FEATURES,
    prepare,
    split_by_scenario,
)


CALIBRATION = {
    "variables": {
        "temperature_c": {"p50": 30.0},
        "humidity_pct": {"p50": 67.0},
        "voltage_v": {"p50": 227.0, "zero_rate": 0.03},
        "current_a": {"zero_rate": 0.01},
        "power_w": {"p50": 36.5, "p95": 42.0},
    }
}
SCENARIO = {
    "id": "test",
    "outdoor_temperature_offset_c": 0.0,
    "humidity_offset_pct": 0.0,
    "occupancy_scale": 1.0,
    "load_scale": 1.0,
    "packet_loss_scale": 1.0,
    "sensor_dropout_scale": 1.0,
}


class SyntheticPipelineTest(unittest.TestCase):
    def make_run(self, run_index=0, seed=7):
        return generate_run(
            CALIBRATION,
            SCENARIO,
            run_index=run_index,
            seed=seed,
            start_time="2026-06-01T00:00:00Z",
            sample_interval_seconds=5,
            rows=240,
        )

    def test_generation_is_reproducible(self):
        first = self.make_run()
        second = self.make_run()
        self.assertEqual(first.to_json(), second.to_json())

    def test_truth_and_observation_are_separate(self):
        frame = self.make_run()
        self.assertIn("true_power_w", frame)
        self.assertIn("observed_power_w", frame)
        differences = (
            frame["true_power_w"] - frame["observed_power_w"]
        ).abs().dropna()
        self.assertTrue(np.any(differences > 1e-6))
        self.assertEqual(frame["source_type"].unique().tolist(), ["synthetic_calibrated"])

    def test_scenarios_are_strictly_held_out(self):
        frames = []
        for index, scenario_id in enumerate(["train", "validation", "test"]):
            frame = self.make_run(index, 20 + index)
            frame["scenario_id"] = scenario_id
            frame["run_id"] = f"{scenario_id}_run_00"
            frames.append(frame)
        prepared = prepare(pd.concat(frames, ignore_index=True))
        config = {
            "train_scenarios": ["train"],
            "validation_scenarios": ["validation"],
            "test_scenarios": ["test"],
        }
        train, validation, test = split_by_scenario(prepared, config)
        self.assertEqual(set(train["scenario_id"]), {"train"})
        self.assertEqual(set(validation["scenario_id"]), {"validation"})
        self.assertEqual(set(test["scenario_id"]), {"test"})
        self.assertTrue(set(FEATURES).issubset(train.columns))

    def test_augmented_data_is_adapted_only_as_replay_workload(self):
        legacy = pd.DataFrame(
            {
                "Timestamp": pd.date_range(
                    "2026-01-01", periods=8, freq="5s", tz="UTC"
                ).astype(str),
                "DeviceID": ["gateway"] * 8,
                "Suhu (C)": [30.0] * 8,
                "Kelembaban (%)": [65.0] * 8,
                "Tegangan (V)": [220.0] * 8,
                "Arus (A)": [0.2] * 8,
                "Daya (W)": [44.0] * 8,
                "Jumlah Orang": [2] * 8,
            }
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.csv"
            legacy.to_csv(path, index=False)
            sample, audit = prepare_augmented_workload(
                path,
                expected_rows=8,
                reference_rows=4,
                sample_size=6,
                chunk_size=3,
            )
        self.assertEqual(audit["provenance"]["inferred_replay_blocks"], 2)
        self.assertEqual(
            audit["benchmark_sample"]["covered_replay_blocks"], [0, 1]
        )
        self.assertFalse(audit["research_role"]["model_training_used"])
        self.assertEqual(
            sample["source_type"].unique().tolist(),
            ["legacy_augmented_replay"],
        )


if __name__ == "__main__":
    unittest.main()
