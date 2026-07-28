"""Small local HTTP replay service for the Web-3D research prototype."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import joblib
import numpy as np
import pandas as pd

from src.data.prepare_augmented_workload import prepare_augmented_workload


def _safe_number(value):
    if pd.isna(value):
        return None
    return float(value)


class ReplayState:
    def __init__(
        self,
        csv_path: Path,
        model_path: Path | None,
        *,
        input_format: str = "synthetic",
        legacy_config: dict | None = None,
    ):
        if input_format == "legacy_augmented":
            if legacy_config is None:
                raise ValueError("legacy_config wajib untuk legacy_augmented.")
            self.frame, self.workload_audit = prepare_augmented_workload(
                csv_path,
                expected_rows=int(legacy_config["expected_rows"]),
                reference_rows=int(legacy_config["reference_rows_per_replay"]),
                sample_size=int(legacy_config["sample_size"]),
            )
            self.source_label = "legacy_augmented_replay"
        else:
            self.frame = pd.read_csv(csv_path)
            self.workload_audit = None
            self.source_label = "synthetic_calibrated"
        self.frame = self.frame[
            self.frame["packet_received"].astype(str).str.lower().eq("true")
        ].dropna(
            subset=[
                "observed_temperature_c",
                "observed_humidity_pct",
                "observed_voltage_v",
                "observed_current_a",
                "observed_power_w",
                "observed_people_count",
            ]
        )
        self.frame = self.frame.reset_index(drop=True)
        if self.frame.empty:
            raise ValueError("Tidak ada baris telemetry valid untuk direplay.")
        self.artifact = joblib.load(model_path) if model_path else None
        self.index = 0

    def _estimate(self, row: pd.Series) -> tuple[float, str, str]:
        if not self.artifact:
            return float(row["observed_power_w"]), "firmware_v_times_i", "observation_only"
        timestamp = pd.Timestamp(row["timestamp_utc"])
        hour = timestamp.hour + timestamp.minute / 60.0
        values = row.to_dict()
        values["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
        values["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
        features = self.artifact["features"]
        x = pd.DataFrame([[values[name] for name in features]], columns=features)
        estimate = float(self.artifact["model"].predict(x)[0])
        return estimate, self.artifact["model_name"], self.artifact["scope"]

    def record(self, row: pd.Series) -> dict:
        estimate, model_name, model_scope = self._estimate(row)
        return {
            "timestamp_utc": row["timestamp_utc"],
            "device_id": row["device_id"],
            "scenario_id": row["scenario_id"],
            "run_id": row["run_id"],
            "source_type": row["source_type"],
            "observed": {
                "temperature_c": _safe_number(row["observed_temperature_c"]),
                "humidity_pct": _safe_number(row["observed_humidity_pct"]),
                "voltage_v": _safe_number(row["observed_voltage_v"]),
                "current_a": _safe_number(row["observed_current_a"]),
                "power_w": _safe_number(row["observed_power_w"]),
                "people_count": int(row["observed_people_count"]),
            },
            "estimate": {
                "power_w": estimate,
                "model_name": model_name,
                "model_scope": model_scope,
            },
            "processing": {
                "tier": "replay",
                "compute_latency_ms": 0.0,
                "network_latency_ms": None,
                "end_to_end_latency_ms": None,
            },
        }

    def latest(self) -> dict:
        row = self.frame.iloc[self.index]
        self.index = (self.index + 1) % len(self.frame)
        return self.record(row)

    def history(self, limit: int) -> list[dict]:
        start = max(0, self.index - limit)
        return [self.record(row) for _, row in self.frame.iloc[start : self.index].iterrows()]


def make_handler(state: ReplayState):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, payload: dict, status: int = 200) -> None:
            encoded = json.dumps(payload, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:  # noqa: N802
            request = urlparse(self.path)
            if request.path == "/api/telemetry/latest":
                self._send({"success": True, "data": state.latest()})
                return
            if request.path == "/api/telemetry/history":
                query = parse_qs(request.query)
                limit = min(500, max(1, int(query.get("limit", ["60"])[0])))
                self._send({"success": True, "data": state.history(limit)})
                return
            if request.path == "/api/health":
                self._send({"status": "ok", "source": state.source_label})
                return
            self._send({"success": False, "error": "not_found"}, status=404)

        def log_message(self, format: str, *args) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("outputs/synthetic_telemetry.csv"))
    parser.add_argument("--model", type=Path, default=Path("outputs/power_estimator.joblib"))
    parser.add_argument(
        "--input-format",
        choices=["synthetic", "legacy_augmented"],
        default="synthetic",
    )
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.json"))
    parser.add_argument("--sample-size", type=int)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    legacy_config = None
    if args.input_format == "legacy_augmented":
        config = json.loads(args.config.read_text(encoding="utf-8"))
        workload = config["benchmark"]["workload"]
        legacy_config = {
            **workload,
            "sample_size": args.sample_size or config["benchmark"]["sample_size"],
        }
    state = ReplayState(
        args.input,
        args.model if args.model.exists() else None,
        input_format=args.input_format,
        legacy_config=legacy_config,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    print(f"Replay API: http://{args.host}:{args.port}/api/telemetry/latest")
    server.serve_forever()


if __name__ == "__main__":
    main()
