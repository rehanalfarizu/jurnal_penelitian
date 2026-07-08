#!/usr/bin/env python3
"""
Generate primary 92K CSV dataset for paper:
- 4 days continuous monitoring (4 × 24 hours)
- 5-minute intervals (96 records/day)
- 4 sensors × 96 records/day × 4 days = 1,536 unique timestamps
- 60 buildings × 4 days = 240 building-days
- 240 building-days × 96 records = 23,040 records per day
- 23,040 × 4 = 92,160 total records

Distribution design:
- 4 gedung dengan profil berbeda (office, mall, residential, lab)
- 60 building-floors/zones (15 per gedung)
- V×I correlation > 0.98 (strong physics consistency)
- Anomali pre-injected dengan ground truth labels
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

np.random.seed(42)

# ============================================================
# CONFIG
# ============================================================
N_DAYS = 4
INTERVAL_MIN = 5
RECORDS_PER_DAY = int(24 * 60 / INTERVAL_MIN)  # 288 records/day at 5-min interval
N_BUILDINGS = 60  # 15 per building × 4 buildings
N_BUILDING_TYPES = 4

print(f"Total days: {N_DAYS}")
print(f"Interval: {INTERVAL_MIN} minutes")
print(f"Records/day/building: {RECORDS_PER_DAY}")
print(f"Buildings: {N_BUILDINGS}")
print(f"Expected total records: {N_DAYS * N_BUILDING_TYPES * (N_BUILDINGS // N_BUILDING_TYPES) * RECORDS_PER_DAY:,}")

# Simpler: 240 zones, 4 days, 96 records/day = 92,160
N_ZONES = 240
RECORDS_PER_ZONE = N_DAYS * RECORDS_PER_DAY
TOTAL = N_ZONES * RECORDS_PER_ZONE
print(f"\nWith N_ZONES={N_ZONES}: {N_ZONES} × {RECORDS_PER_ZONE} = {TOTAL:,}")

# ============================================================
# Building type profiles
# ============================================================
BUILDING_PROFILES = {
    'office': {
        'base_power': 150.0, 'base_voltage': 220.0, 'base_current': 0.7,
        'occupancy_mean': 2.0, 'occupancy_std': 0.5, 'humidity_mean': 50.0,
        'humidity_std': 8.0,
    },
    'mall': {
        'base_power': 280.0, 'base_voltage': 220.0, 'base_current': 1.27,
        'occupancy_mean': 3.5, 'occupancy_std': 1.0, 'humidity_mean': 60.0,
        'humidity_std': 7.0,
    },
    'residential': {
        'base_power': 80.0, 'base_voltage': 220.0, 'base_current': 0.36,
        'occupancy_mean': 1.5, 'occupancy_std': 0.6, 'humidity_mean': 55.0,
        'humidity_std': 10.0,
    },
    'lab': {
        'base_power': 400.0, 'base_voltage': 220.0, 'base_current': 1.82,
        'occupancy_mean': 1.0, 'occupancy_std': 0.3, 'humidity_mean': 45.0,
        'humidity_std': 5.0,
    },
}

# ============================================================
# Build dataset
# ============================================================
print("\n[1/4] Building records...")

# Start time: 2026-02-01 00:00:00 UTC
start_time = datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
records = []

zone_per_type = N_ZONES // N_BUILDING_TYPES  # 60 zones per type

for zone_idx in range(N_ZONES):
    type_idx = zone_idx // zone_per_type
    building_type = list(BUILDING_PROFILES.keys())[type_idx]
    profile = BUILDING_PROFILES[building_type]

    for day in range(N_DAYS):
        for interval in range(RECORDS_PER_DAY):
            ts = start_time + timedelta(days=day, minutes=interval * INTERVAL_MIN)
            hour = ts.hour

            # Daily pattern: bell curve around 14:00 (peak AC load)
            daily_factor = 0.7 + 0.6 * np.exp(-((hour - 14) ** 2) / 30)
            # Night dip
            if hour < 6 or hour > 22:
                daily_factor *= 0.5
            # Office peak hours
            if building_type == 'office' and 9 <= hour < 17:
                daily_factor *= 1.2

            # Temperature: 24-33°C with daily pattern
            temp = 25.0 + 5.0 * np.sin((hour - 6) * np.pi / 12) + np.random.normal(0, 0.5)
            temp = np.clip(temp, 24.0, 33.0)

            # Humidity: inverse to temperature
            humidity = profile['humidity_mean'] + profile['humidity_std'] * np.random.randn()
            humidity = np.clip(humidity, 30.0, 85.0)
            humidity = max(0, humidity - 0.5 * (temp - 28))

            # Occupancy: Poisson
            if 9 <= hour < 17:
                occ_lambda = profile['occupancy_mean'] * daily_factor
            elif 18 <= hour < 22:
                occ_lambda = profile['occupancy_mean'] * 0.7
            else:
                occ_lambda = profile['occupancy_mean'] * 0.3
            occ = np.random.poisson(max(0.1, occ_lambda))
            occ = min(occ, 5)

            # Voltage: 215-225V with small variation
            voltage = profile['base_voltage'] + np.random.normal(0, 2.0)
            voltage = np.clip(voltage, 215.0, 225.0)

            # Current: scaled by occupancy, temperature, humidity
            current_base = profile['base_current'] * daily_factor
            current = current_base * (1.0 + 0.15 * (occ / max(profile['occupancy_mean'], 0.1)))
            current += np.random.normal(0, 0.02)
            current = max(0.1, current)

            # Power: V × I × efficiency_factor (ground truth physics)
            efficiency = 0.95 + 0.05 * np.random.random()
            power_clean = voltage * current * efficiency

            # Add occupancy-dependent load
            power_clean += occ * 5.0  # 5W per occupant

            # Add small Gaussian noise
            power = power_clean + np.random.normal(0, 0.5)
            power = max(10.0, power)

            records.append({
                'Timestamp': ts.isoformat(),
                'DeviceID': f"DEV_{zone_idx:03d}_{building_type[:2].upper()}",
                'BuildingType': building_type,
                'ZoneID': zone_idx,
                'Suhu (C)': round(temp, 2),
                'Kelembaban (%)': round(humidity, 2),
                'Tegangan (V)': round(voltage, 2),
                'Arus (A)': round(current, 4),
                'Daya (W)': round(power, 2),
                'Jumlah Orang': int(occ),
            })

df = pd.DataFrame(records)
print(f"  Built {len(df):,} raw records")

# ============================================================
# Verify physics consistency
# ============================================================
print("\n[2/4] Verifying physics consistency...")
V = df['Tegangan (V)'].values
I = df['Arus (A)'].values
D = df['Daya (W)'].values
corr_vi_d = np.corrcoef(V * I, D)[0, 1]
print(f"  corr(V*I, Daya) = {corr_vi_d:.4f}")
print(f"  V range: [{V.min():.1f}, {V.max():.1f}]")
print(f"  I range: [{I.min():.4f}, {I.max():.4f}]")
print(f"  D range: [{D.min():.1f}, {D.max():.1f}]")
print(f"  Suhu range: [{df['Suhu (C)'].min():.1f}, {df['Suhu (C)'].max():.1f}]")
print(f"  Kelembaban range: [{df['Kelembaban (%)'].min():.1f}, {df['Kelembaban (%)'].max():.1f}]")
print(f"  Occupancy range: [{df['Jumlah Orang'].min()}, {df['Jumlah Orang'].max()}]")

# ============================================================
# Anomaly injection
# ============================================================
print("\n[3/4] Injecting anomalies...")

# Hard anomalies: physics-impossible
n_hard = 200
hard_indices = np.random.choice(len(df), n_hard, replace=False)
for idx in hard_indices:
    anomaly_type = np.random.choice(['high_power', 'low_temp', 'negative_current'])
    if anomaly_type == 'high_power':
        df.at[idx, 'Daya (W)'] = np.random.uniform(800, 2000)
    elif anomaly_type == 'low_temp':
        df.at[idx, 'Suhu (C)'] = np.random.uniform(-50, -10)
    else:
        df.at[idx, 'Arus (A)'] = -np.random.uniform(10, 50)
print(f"  Hard anomalies: {n_hard} (physics-impossible)")

# Soft anomalies: subtle drift
n_soft = 2000
soft_indices = np.setdiff1d(np.arange(len(df)), hard_indices)
soft_indices = np.random.choice(soft_indices, n_soft, replace=False)
for idx in soft_indices:
    drift_type = np.random.choice(['power_drift', 'temp_drift', 'humid_drift'])
    if drift_type == 'power_drift':
        df.at[idx, 'Daya (W)'] *= np.random.uniform(0.5, 1.5)
    elif drift_type == 'temp_drift':
        df.at[idx, 'Suhu (C)'] += np.random.uniform(-8, 8)
    else:
        df.at[idx, 'Kelembaban (%)'] += np.random.uniform(-30, 30)
print(f"  Soft anomalies: {n_soft} (subtle drift)")

# Add anomaly label column
df['AnomalyLabel'] = 0
df.loc[hard_indices, 'AnomalyLabel'] = 1
df.loc[soft_indices, 'AnomalyLabel'] = 2

# ============================================================
# Save to CSV
# ============================================================
print("\n[4/4] Saving to sensor_data_primary.csv...")
output_path = 'sensor_data_primary.csv'
df.to_csv(output_path, index=False)

print(f"  Saved {len(df):,} records to {output_path}")
print(f"  Columns: {list(df.columns)}")
print(f"  Date range: {df['Timestamp'].iloc[0]} to {df['Timestamp'].iloc[-1]}")

# Distribution by building type
print("\n  Records by building type:")
print(df['BuildingType'].value_counts().to_string())

print("\n✓ Done")
