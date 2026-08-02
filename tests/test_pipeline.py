import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd
from jsonschema import Draft202012Validator

from src.benchmark.edge_cloud_benchmark import (
    benchmark,
    build_monitoring_record,
)
from src.data.audit_trace import integrate_legacy_energy
from src.data.prepare_historical_replay import prepare_historical_replay
from src.replay.replay_server import ReplayState


def make_legacy_frame(rows=8):
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range(
                "2026-01-01", periods=rows, freq="5s", tz="UTC"
            ).astype(str),
            "DeviceID": ["gateway"] * rows,
            "Suhu (C)": [30.0] * rows,
            "Kelembaban (%)": [65.0] * rows,
            "Tegangan (V)": [220.0] * rows,
            "Arus (A)": [0.2, 0.05, 0.2, 0.2] * (rows // 4),
            "Daya (W)": [44.0, 0.0, 44.0, 44.0] * (rows // 4),
            "Jumlah Orang": [2] * rows,
        }
    )


CONFIG = {
    "data": {
        "near_realtime_deadline_seconds": 5.0,
        "deadline_basis": "test deadline",
    },
    "replay": {
        "benchmark_sample_size": 8,
        "random_seed": 7,
    },
    "benchmark": {
        "cloud_routing": {
            "power_anomaly_threshold_w": 42.6,
            "basis": "test threshold",
        },
        "cloud_network_profile": {
            "label": "configured test profile",
            "median_ms": 45.0,
            "jitter_ms": 0.0,
            "drop_probability": 0.0,
        },
    },
}


class HistoricalReplayPipelineTest(unittest.TestCase):
    def test_energy_integration_exposes_legacy_measurement_scope(self):
        timestamps = pd.Series(
            pd.date_range("2026-01-01", periods=3, freq="5s", tz="UTC")
        )
        power = pd.Series([40.0, 44.0, 44.0])
        lookup, audit = integrate_legacy_energy(
            timestamps,
            power,
            max_gap_seconds=10.0,
            timestamp_basis="test_timestamp",
            measurement_role="test_physical_trace",
        )
        self.assertAlmostEqual(
            lookup["energy_cumulative_legacy_wh"].iloc[-1],
            ((40.0 + 44.0) * 0.5 * 5.0 + (44.0 + 44.0) * 0.5 * 5.0)
            / 3600.0,
        )
        self.assertEqual(audit["measurement_role"], "test_physical_trace")
        self.assertFalse(audit["active_energy_ground_truth"])

    def prepare_sample(self):
        directory = TemporaryDirectory()
        path = Path(directory.name) / "historical_replay.csv"
        make_legacy_frame().to_csv(path, index=False)
        sample, audit = prepare_historical_replay(
            path,
            expected_rows=8,
            reference_rows=4,
            sample_size=8,
            chunk_size=3,
        )
        return directory, sample, audit

    def test_replay_provenance_separates_volume_from_observations(self):
        directory, sample, audit = self.prepare_sample()
        self.addCleanup(directory.cleanup)
        self.assertEqual(audit["provenance"]["inferred_replay_blocks"], 2)
        self.assertEqual(
            audit["benchmark_sample"]["covered_replay_blocks"], [0, 1]
        )
        self.assertFalse(
            audit["research_role"]["independent_field_observations_claimed"]
        )
        self.assertFalse(audit["research_role"]["model_training_used"])
        self.assertEqual(
            sample["source_type"].unique().tolist(),
            ["historical_replay"],
        )
        self.assertTrue(
            audit["lineage"]["all_replay_payloads_identical_to_first_block"]
        )
        self.assertEqual(
            audit["lineage"]["classification"],
            "deterministic_replay_block_without_reference_comparison",
        )
        self.assertFalse(
            any(audit["lineage"]["cross_block_mismatch_counts"].values())
        )
        self.assertEqual(sample.iloc[0]["source_row_id"], "historical:000000")
        self.assertEqual(sample.iloc[4]["replay_id"], "historical_replay_01")
        self.assertEqual(
            sample.iloc[0]["energy_integration_status"], "trace_start"
        )
        self.assertAlmostEqual(
            sample.iloc[1]["energy_interval_legacy_wh"],
            (44.0 + 0.0) * 0.5 * 5.0 / 3600.0,
        )
        self.assertEqual(sample.iloc[0]["occupancy_status"], "occupied")
        self.assertFalse(
            audit["quality"]["energy_integration"][
                "active_energy_ground_truth"
            ]
        )

    def test_lineage_detects_transformation_against_exported_workbook(self):
        with TemporaryDirectory() as directory:
            directory_path = Path(directory)
            csv_path = directory_path / "historical_replay.csv"
            replay = make_legacy_frame()
            replay.to_csv(csv_path, index=False)

            reference = replay.iloc[:4].rename(
                columns={
                    "Timestamp": "timestamp",
                    "DeviceID": "device_id",
                    "Suhu (C)": "temperature_c",
                    "Kelembaban (%)": "humidity_pct",
                    "Tegangan (V)": "voltage_v",
                    "Arus (A)": "current_a",
                    "Daya (W)": "power_w",
                    "Jumlah Orang": "people_count",
                }
            )
            reference.loc[1, "voltage_v"] = 0.0
            reference.loc[1, "current_a"] = 0.0
            reference.loc[1, "people_count"] = 1
            reference["timestamp"] = pd.to_datetime(
                reference["timestamp"], utc=True
            )

            with patch(
                "src.data.prepare_historical_replay.load_trace",
                return_value=reference,
            ):
                _, audit = prepare_historical_replay(
                    csv_path,
                    expected_rows=8,
                    reference_rows=4,
                    sample_size=8,
                    reference_trace=directory_path / "exported_workbook.xlsx",
                    chunk_size=3,
                )
            lineage = audit["lineage"]
            comparison = lineage["first_block_vs_exported_workbook"]
            self.assertEqual(
                lineage["classification"],
                "deterministic_replay_of_transformed_historical_trace",
            )
            self.assertTrue(
                lineage["all_replay_payloads_identical_to_first_block"]
            )
            self.assertEqual(
                comparison["by_column"]["voltage_v"]["changed_count"],
                1,
            )
            self.assertEqual(
                comparison["by_column"]["current_a"]["changed_count"],
                1,
            )
            self.assertEqual(
                comparison["by_column"]["people_count"]["changed_count"],
                1,
            )

    def test_legacy_power_is_checked_not_estimated(self):
        directory, sample, _ = self.prepare_sample()
        self.addCleanup(directory.cleanup)
        record, _ = build_monitoring_record(sample.iloc[0], 42.6)
        self.assertIn("monitoring", record)
        self.assertNotIn("estimate", record)
        self.assertEqual(record["monitoring"]["power_legacy_w"], 44.0)
        self.assertEqual(record["monitoring"]["power_formula_w"], 44.0)
        self.assertEqual(
            record["monitoring"]["energy_integration_status"],
            "trace_start",
        )
        self.assertEqual(
            record["monitoring"]["occupancy_status"], "occupied"
        )
        self.assertEqual(
            record["digital_twin"]["supported_views"],
            ["geospatial_site", "building", "indoor"],
        )
        self.assertEqual(
            [
                item["lod_id"]
                for item in record["digital_twin"]["application_lod"]
            ],
            ["LoD-A", "LoD-B", "LoD-C"],
        )
        self.assertEqual(
            record["digital_twin"]["lod_transition"],
            "manual_view_selection",
        )
        self.assertEqual(record["processing"]["tier"], "cloud")
        self.assertEqual(
            record["processing"]["route_reason"],
            "power_above_trace_p99",
        )
        schema = json.loads(
            Path("schemas/telemetry.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator(schema).validate(record)

    def test_benchmark_measures_monitoring_path_without_model_metrics(self):
        directory, sample, audit = self.prepare_sample()
        self.addCleanup(directory.cleanup)
        report = benchmark(
            sample,
            CONFIG,
            {"available_rows": audit["source"]["rows"]},
        )
        self.assertIn("actual_local_monitoring", report)
        self.assertIn("sequential_messages_per_second", report["throughput"])
        self.assertNotIn("prediction_checksum", report)
        self.assertNotIn("model_name", report["scope"])
        self.assertEqual(
            report["routing"]["edge_count"]
            + report["routing"]["cloud_count"],
            len(sample),
        )
        self.assertEqual(
            report["configured_end_to_end"]["deadline_miss_count"], 0
        )
        self.assertEqual(
            report["configured_end_to_end"]["deadline_basis"],
            "test deadline",
        )
        self.assertEqual(
            report["configured_end_to_end"]["attempted_count"],
            len(sample),
        )
        self.assertEqual(
            report["configured_end_to_end"]["delivered_count"]
            + report["configured_end_to_end"]["dropped_count"],
            len(sample),
        )
        self.assertEqual(
            report["configured_cloud_route_end_to_end"]["routed_count"],
            report["routing"]["cloud_count"],
        )
        self.assertEqual(
            set(report["routing"]["reason_counts"]),
            {
                "normal_local_monitoring",
                "missing_or_nonfinite_value",
                "invalid_electrical_reading",
                "current_below_legacy_threshold",
                "power_above_trace_p99",
            },
        )
        self.assertIn(
            "missing_or_nonfinite_value",
            report["routing"]["uncovered_reasons"],
        )
        self.assertTrue(
            report["scope"]["available_rows_are_not_messages_benchmarked"]
        )
        self.assertIn("configured_cloud_only_baseline", report)
        self.assertIn("architecture_comparison", report)
        self.assertGreaterEqual(
            report["architecture_comparison"][
                "configured_p95_latency_reduction_percent"
            ],
            0,
        )
        self.assertGreaterEqual(
            report["architecture_comparison"][
                "network_payload_bytes_avoided"
            ],
            0,
        )

    def test_missing_non_electrical_value_routes_to_cloud(self):
        directory, sample, _ = self.prepare_sample()
        self.addCleanup(directory.cleanup)
        row = sample.iloc[2].copy()
        row["temperature_c"] = float("nan")
        record, _ = build_monitoring_record(row, 42.6)
        self.assertEqual(record["processing"]["tier"], "cloud")
        self.assertFalse(record["processing"]["valid"])
        self.assertEqual(
            record["processing"]["route_reason"],
            "missing_or_nonfinite_value",
        )

    def test_replay_state_keeps_request_history_with_lineage(self):
        directory, sample, _ = self.prepare_sample()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "canonical_sample.csv"
        sample.to_csv(path, index=False)
        state = ReplayState(path, CONFIG)

        first = state.latest()
        second = state.latest()
        history = state.history(10)

        self.assertEqual(len(history), 2)
        self.assertEqual(
            [record["provenance"]["source_row_id"] for record in history],
            [
                first["provenance"]["source_row_id"],
                second["provenance"]["source_row_id"],
            ],
        )
        self.assertEqual(history, [first, second])
        self.assertEqual(history[0]["timestamp_utc"], first["timestamp_utc"])
        self.assertEqual(
            history[0]["processing"]["compute_latency_ms"],
            first["processing"]["compute_latency_ms"],
        )
        self.assertEqual(
            first["provenance"]["lineage_classification"],
            "deterministic_replay_block_without_reference_comparison",
        )

    def test_row_count_mismatch_is_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "historical_replay.csv"
            make_legacy_frame().to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "Jumlah baris replay"):
                prepare_historical_replay(
                    path,
                    expected_rows=9,
                    reference_rows=4,
                    sample_size=4,
                )


if __name__ == "__main__":
    unittest.main()
