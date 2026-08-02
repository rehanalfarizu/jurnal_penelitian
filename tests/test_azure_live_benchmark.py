import unittest

import pandas as pd

from scripts.run_azure_live_benchmark import build_payload, source_indices, summarize


class AzureLiveBenchmarkTest(unittest.TestCase):
    def test_source_indices_cover_trace_boundaries(self):
        self.assertEqual(source_indices(100, 5).tolist(), [0, 24, 49, 74, 99])

    def test_payload_marks_replay_and_node_attribution(self):
        row = pd.Series(
            {
                "timestamp": pd.Timestamp("2026-05-17T00:00:00Z"),
                "device_id": "RASPBERRY_PI_GATEWAY_001",
                "temperature_c": 27.5,
                "humidity_pct": 70,
                "voltage_v": 220,
                "current_a": 0.2,
                "power_w": 44,
                "people_count": 2,
            }
        )
        payload = build_payload(row, run_id="test-run", message_number=1, source_row=42)
        self.assertEqual(payload["benchmark"]["mode"], "historical_replay")
        self.assertEqual(payload["benchmark"]["sourceRowId"], "historical:000042")
        self.assertEqual(
            payload["benchmark"]["sourceNodeAttribution"],
            "architecture_metadata_not_row_level_field",
        )
        self.assertEqual(payload["esp32"]["daya"], 44.0)
        self.assertEqual(payload["camera"]["people_count"], 2)

    def test_summary_excludes_warmup_and_reports_deadline(self):
        records = [
            {
                "warmup": True,
                "contract_ok": True,
                "deadline_met": True,
                "http_status": 200,
                "end_to_end_ms": 900.0,
                "server_processing_ms": 400.0,
                "storage_write_ms": 300.0,
                "client_network_overhead_ms": 500.0,
            },
            {
                "warmup": False,
                "contract_ok": True,
                "deadline_met": True,
                "http_status": 200,
                "end_to_end_ms": 100.0,
                "server_processing_ms": 60.0,
                "storage_write_ms": 40.0,
                "client_network_overhead_ms": 40.0,
            },
            {
                "warmup": False,
                "contract_ok": False,
                "deadline_met": False,
                "http_status": 500,
                "end_to_end_ms": 50.0,
                "server_processing_ms": None,
                "storage_write_ms": None,
                "client_network_overhead_ms": None,
            },
        ]
        report = summarize(records, duration_seconds=2.0)
        self.assertEqual(report["sample"]["measured_requests"], 2)
        self.assertEqual(report["reliability"]["success_rate_percent"], 50.0)
        self.assertEqual(report["reliability"]["deadline_compliance_percent"], 100.0)
        self.assertEqual(report["latency_ms"]["client_end_to_end"]["n"], 1)


if __name__ == "__main__":
    unittest.main()
