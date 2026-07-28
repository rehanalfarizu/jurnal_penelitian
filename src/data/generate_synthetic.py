"""Generate scenario-based synthetic telemetry calibrated from the real trace.

The generator separates an unobservable physical state (``true_*``) from the
sensor/firmware observation (``observed_*``). It does not duplicate real rows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def _stat(calibration: dict, variable: str, name: str, fallback: float) -> float:
    value = calibration.get("variables", {}).get(variable, {}).get(name)
    return fallback if value is None or not np.isfinite(value) else float(value)


def _update_occupancy(
    rng: np.random.Generator, people: int, hour: float, scale: float
) -> int:
    """Markov occupancy calibrated for the near-real-time sampling interval."""
    business_hours = 8 <= hour < 18
    if business_hours and people == 0 and rng.random() < 0.0011 * scale:
        people = 5 if rng.random() < 0.03 else 3
    elif people > 0 and rng.random() < (0.0003 if business_hours else 0.0025):
        people = 0
    return int(np.clip(people, 0, 5))


def generate_run(
    calibration: dict,
    scenario: dict,
    run_index: int,
    seed: int,
    start_time: str,
    sample_interval_seconds: float,
    rows: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    occupancy_rng = np.random.default_rng(seed + 1_000_003)
    timestamps = pd.date_range(
        start=pd.Timestamp(start_time) + pd.Timedelta(days=run_index),
        periods=rows,
        freq=pd.Timedelta(seconds=sample_interval_seconds),
        tz="UTC",
    )

    temp_median = _stat(calibration, "temperature_c", "p50", 30.2)
    temp_p05 = _stat(calibration, "temperature_c", "p05", 26.9)
    temp_p95 = _stat(calibration, "temperature_c", "p95", 32.8)
    humidity_median = _stat(calibration, "humidity_pct", "p50", 67.0)
    humidity_p05 = _stat(calibration, "humidity_pct", "p05", 50.0)
    humidity_p95 = _stat(calibration, "humidity_pct", "p95", 76.0)
    voltage_median = _stat(calibration, "voltage_v", "p50", 227.0)
    power_median = max(5.0, _stat(calibration, "power_w", "p50", 36.5))
    power_p95 = max(power_median, _stat(calibration, "power_w", "p95", 41.1))
    voltage_dropout = _stat(calibration, "voltage_v", "zero_rate", 0.03)
    current_dropout = _stat(calibration, "current_a", "zero_rate", 0.013)
    sensor_dropout_scale = float(scenario.get("sensor_dropout_scale", 1.0))
    effective_voltage_dropout = min(0.2, voltage_dropout * sensor_dropout_scale)
    effective_current_dropout = min(
        effective_voltage_dropout, current_dropout * sensor_dropout_scale
    )

    dt_minutes = sample_interval_seconds / 60.0
    room_temp = temp_median
    room_humidity = humidity_median
    people = 0
    appliance_on = False
    ar_voltage = 0.0
    ar_load = 0.0
    voltage_invalid = False
    current_invalid_with_voltage = False
    current_sensor_bias = 0.0

    records: list[dict] = []
    for index, timestamp in enumerate(timestamps):
        hour = timestamp.hour + timestamp.minute / 60.0
        day_wave = np.sin(2 * np.pi * (hour - 8.0) / 24.0)
        outdoor_temp = (
            temp_median
            + max(2.0, (temp_p95 - temp_p05) * 0.62) * day_wave
            + float(scenario["outdoor_temperature_offset_c"])
            + rng.normal(0, 0.08)
        )
        dry_spell_offset = -15.0 if 10 <= hour < 12 else 0.0
        outdoor_humidity = np.clip(
            humidity_median
            - max(6.0, (humidity_p95 - humidity_p05) * 0.33) * day_wave
            + dry_spell_offset
            + float(scenario["humidity_offset_pct"])
            + rng.normal(0, 0.3),
            35,
            95,
        )

        people = _update_occupancy(
            occupancy_rng, people, hour, float(scenario["occupancy_scale"])
        )

        on_probability = (0.002 + 0.003 * people) * float(scenario["load_scale"])
        off_probability = 0.0015 if people else 0.006
        if not appliance_on and rng.random() < on_probability:
            appliance_on = True
        elif appliance_on and rng.random() < off_probability:
            appliance_on = False

        thermal_target = outdoor_temp - (0.9 if appliance_on else 0.0)
        room_temp += (thermal_target - room_temp) * dt_minutes / 38.0
        room_temp += people * 0.00012 * dt_minutes + rng.normal(0, 0.006)
        room_humidity += (outdoor_humidity - room_humidity) * dt_minutes / 32.0
        room_humidity -= (0.004 if appliance_on else 0.0) * dt_minutes
        room_humidity = float(np.clip(room_humidity + rng.normal(0, 0.025), 25, 95))

        ar_voltage = 0.995 * ar_voltage + rng.normal(0, 0.75)
        true_voltage = float(np.clip(voltage_median + ar_voltage, 200, 250))
        ar_load = 0.985 * ar_load + rng.normal(0, 0.18)
        base_power = power_median * (0.96 + 0.012 * people)
        switched_power = (power_p95 - power_median) * 0.85 if appliance_on else 0.0
        true_power = max(
            0.0,
            (base_power + switched_power + ar_load) * float(scenario["load_scale"]),
        )
        true_current = true_power / true_voltage

        observed_temperature = round(room_temp + rng.normal(0, 0.17), 1)
        observed_humidity = round(float(np.clip(room_humidity + rng.normal(0, 0.6), 0, 100)))
        observed_voltage = round(true_voltage + rng.normal(0, 0.35), 1)
        current_sensor_bias = 0.94 * current_sensor_bias + rng.normal(0, 0.0015)
        observed_current = round(
            true_current * (1 + rng.normal(0, 0.012)) + current_sensor_bias,
            2,
        )

        packet_loss_probability = min(
            0.2, 0.0015 * float(scenario["packet_loss_scale"])
        )
        packet_received = bool(rng.random() >= packet_loss_probability)
        recovery_probability = 0.02
        was_voltage_invalid = voltage_invalid
        if voltage_invalid:
            voltage_invalid = bool(rng.random() >= recovery_probability)
        else:
            failure_probability = (
                effective_voltage_dropout
                * recovery_probability
                / max(1 - effective_voltage_dropout, 1e-9)
            )
            voltage_invalid = bool(rng.random() < failure_probability)
        if voltage_invalid and not was_voltage_invalid:
            current_invalid_with_voltage = bool(
                rng.random()
                < min(
                    1.0,
                    1.8
                    * effective_current_dropout
                    / max(effective_voltage_dropout, 1e-9),
                )
            )
        elif not voltage_invalid:
            current_invalid_with_voltage = False
        voltage_valid = bool(not voltage_invalid and 150 <= observed_voltage <= 300)
        current_valid = bool(
            observed_current >= 0.1
            and not current_invalid_with_voltage
        )
        if not voltage_valid:
            observed_voltage = 0.0
        if not current_valid:
            observed_current = 0.0
        observed_power = round(observed_voltage * observed_current, 1)

        jitter_ms = int(round(rng.normal(0, 110)))
        observed_timestamp = timestamp + pd.Timedelta(milliseconds=jitter_ms)
        if not packet_received:
            observed_temperature = np.nan
            observed_humidity = np.nan
            observed_voltage = np.nan
            observed_current = np.nan
            observed_power = np.nan

        records.append(
            {
                "timestamp_utc": observed_timestamp.isoformat(),
                "device_id": "RASPBERRY_PI_GATEWAY_001",
                "scenario_id": scenario["id"],
                "scenario_role": scenario.get("role", "unspecified"),
                "run_id": f"{scenario['id']}_run_{run_index:02d}",
                "seed": seed,
                "source_type": "synthetic_calibrated",
                "source_row_id": f"{scenario['id']}:{run_index}:{index}",
                "packet_received": packet_received,
                "true_temperature_c": room_temp,
                "true_humidity_pct": room_humidity,
                "true_voltage_v": true_voltage,
                "true_current_a": true_current,
                "true_power_w": true_power,
                "true_people_count": people,
                "appliance_state": "active" if appliance_on else "idle",
                "observed_temperature_c": observed_temperature,
                "observed_humidity_pct": observed_humidity,
                "observed_voltage_v": observed_voltage,
                "observed_current_a": observed_current,
                "observed_power_w": observed_power,
                "observed_people_count": people,
                "voltage_status": "normal" if voltage_valid else "invalid",
                "current_status": "normal" if current_valid else "below_threshold",
            }
        )
    return pd.DataFrame.from_records(records)


def generate_dataset(config: dict, calibration: dict, rows_override: int | None = None) -> pd.DataFrame:
    data_config = config["data"]
    interval = float(data_config["sample_interval_seconds"])
    rows = rows_override or int(
        float(data_config["duration_hours"]) * 3600 / interval
    )
    frames = []
    for scenario_index, scenario in enumerate(config["scenarios"]):
        for run_index in range(int(data_config["runs_per_scenario"])):
            seed = (
                int(data_config["base_seed"])
                + scenario_index * 10_000
                + run_index
            )
            frames.append(
                generate_run(
                    calibration,
                    scenario,
                    run_index,
                    seed,
                    data_config["start_time_utc"],
                    interval,
                    rows,
                )
            )
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.json"))
    parser.add_argument("--calibration", type=Path, default=Path("outputs/trace_audit.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/synthetic_telemetry.csv"))
    parser.add_argument("--rows-per-run", type=int)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    frame = generate_dataset(config, calibration, args.rows_per_run)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    print(
        f"Data sintetis tersimpan: {args.output} "
        f"({len(frame):,} baris, {frame['run_id'].nunique()} run)"
    )


if __name__ == "__main__":
    main()
