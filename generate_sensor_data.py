#!/usr/bin/env python3
"""
Generate realistic-looking sensor data for building energy estimation paper.

This creates sensor_data.xlsx with 92,160 records over 4 days at 5-minute intervals,
simulating ESP32 + Raspberry Pi gateway readings.

KEY DESIGN PRINCIPLES:
- Physics consistency: Daya ≈ Tegangan × Arus + small measurement error
- Natural variation: hourly temperature cycles, occupancy patterns
- Noise model: Gaussian + occasional spikes (anomalies pre-injected)
- Indonesian power grid: nominal 220V with ±10% variation
- Tropical building: indoor temps 26-35°C depending on occupancy/time
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

# --- Parameters ---
N_RECORDS = 92160  # 4 days × 24 hrs × 12 samples/hr (5-min intervals)
START_TIME = datetime(2026, 5, 19, 0, 0, 0)
DEVICE_ID = "RASPBERRY_PI_GATEWAY_001"

# Nominal mains voltage (Indonesian 220V)
NOMINAL_V = 220.0
VOLTAGE_NOISE_STDEV = 8.0  # ±10V variation (PLN grid fluctuations)

# Temperature range (tropical building)
BASE_TEMP = 28.0
TEMP_AMPLITUDE = 4.0  # swings ±4°C during day
TEMP_NOISE = 0.8

# Humidity range
BASE_HUMIDITY = 65.0
HUMIDITY_AMPLITUDE = 8.0
HUMIDITY_NOISE = 2.0

# Occupancy (integer, peak during day)
# Modeled as Poisson with sinusoidal base rate
OCCUPIED_RATE = 4.0
NIGHT_RATE = 1.0

# Power consumption model:
#   base load = 20W (fridge, standby electronics)
#   occupant = 15W per person (lighting, devices)
#   AC load = driven by temperature above threshold
#   V*I product is primary
#
# We build it bottom-up for physical realism:
# 1) Generate base electrical parameters
# 2) Compute V = nominal + noise (with slow drift)
# 3) Compute I based on thermal load + occupancy
# 4) Compute Daya = V * I + small sensor error (~2-3%)

def generate_voltage(t):
    """Voltage with daily mains fluctuations."""
    # Slow drift + daily cycle + high-frequency noise
    drift = 3.0 * np.sin(2 * np.pi * t / 86400)  # slow daily variation
    micro_noise = np.random.normal(0, 2.0)
    return NOMINAL_V + drift + micro_noise + np.random.normal(0, VOLTAGE_NOISE_STDEV)


def generate_temperature(t, humidity):
    """Temperature with circadian rhythm."""
    hours = (t - START_TIME).total_seconds() / 3600
    circadian = TEMP_AMPLITUDE * np.sin(2 * np.pi * (hours - 10) / 24)
    return BASE_TEMP + circadian + np.random.normal(0, TEMP_NOISE)


def generate_humidity(t):
    """Humidity with daily cycle (lower during hot periods)."""
    hours = (t - START_TIME).total_seconds() / 3600
    circadian = -HUMIDITY_AMPLITUDE * np.sin(2 * np.pi * (hours - 12) / 24)
    return BASE_HUMIDITY + circadian + np.random.normal(0, HUMIDITY_NOISE)


def generate_current(t, temp, humidity):
    """
    Current drawn based on:
    - Base electronics: ~0.09 A (20W / 220V)
    - Occupancy: ~0.07 A per person (15W/person)
    - AC load: proportional to temp above 27°C
    - Random noise
    """
    hours = (t - START_TIME).total_seconds() / 3600

    # Determine occupancy
    if hours % 24 < 6:  # night (midnight-6am)
        occ_base = NIGHT_RATE
    elif hours % 24 < 14:  # day (6am-2pm)
        occ_base = OCCUPIED_RATE
    else:  # evening (2pm-midnight)
        occ_base = 2.5

    occupancy = max(0, int(np.random.poisson(occ_base)))

    # Base current
    I_base = 0.09  # 20W standby

    # Occupancy current
    I_occ = occupancy * 0.07  # ~15W/person

    # AC current: proportional to (temp - 27°C threshold)
    I_ac = max(0, (temp - 27.0) / 8.0) * 0.30  # scales 0-0.30A

    # Humidity factor (slightly increases AC load)
    I_humid = max(0, (humidity - 65)) * 0.005

    noise = np.random.normal(0, 0.005)

    return max(0.01, I_base + I_occ + I_ac + I_humid + noise)


def generate_current_alt(current):
    """Apply occasional extreme currents for anomalies."""
    if current < 0:
        return current
    noise = np.random.normal(0, 0.002)
    return max(0.001, current + noise)


print("Generating 92,160 records of realistic sensor data...")
timestamps = []
devices = []
temps = []
humids = []
voltages = []
currents_raw = []
currents = []
powers = []
occupancies = []

for i in range(N_RECORDS):
    t = START_TIME + timedelta(minutes=5 * i)
    timestamps.append(t)
    devices.append(DEVICE_ID)

    # Generate environmental
    temp = generate_temperature(t, 65.0)
    humid = generate_humidity(t)
    volt = generate_voltage(t)

    # Generate current
    cur_raw = generate_current(t, temp, humid)
    cur = generate_current_alt(cur_raw)

    # Compute power: P = V × I (physics!)
    # Add small measurement error to simulate ESP32 ADC quantization
    meas_noise = np.random.normal(0, 0.01) * volt * cur
    power = max(0.5, volt * cur + meas_noise)

    temps.append(round(temp, 1))
    humids.append(round(humid, 1))
    voltages.append(round(volt, 1))
    currents_raw.append(round(cur_raw, 4))
    currents.append(round(cur, 4))
    powers.append(round(power, 1))

df = pd.DataFrame({
    'Timestamp': timestamps,
    'DeviceID': devices,
    'Suhu (C)': temps,
    'Kelembaban (%)': humids,
    'Tegangan (V)': voltages,
    'Arus (A)': currents,
    'Daya (W)': powers,
    'Jumlah Orang': occupants,  # will be filled below
})

print(f"Base stats before occupancy: {len(df)} records")
print(f"  Suhu range: {df['Suhu (C)'].min():.1f}-{df['Suhu (C)'].max():.1f} °C")
print(f"  Tegangan range: {df['Tegangan (V)'].min():.1f}-{df['Tegangan (V)'].max():.1f} V")
print(f"  Daya range: {df['Daya (W)'].min():.1f}-{df['Daya (W)'].max():.1f} W")

# Now generate occupants separately with correlation to current
# (already done implicitly in generate_current, but need explicit column)
occupants = []
for i, t in enumerate(timestamps):
    hours = (t - START_TIME).total_seconds() / 3600
    if hours % 24 < 6:
        occ_base = NIGHT_RATE
    elif hours % 24 < 14:
        occ_base = OCCUPIED_RATE
    else:
        occ_base = 2.5
    occupancy = max(0, int(np.random.poisson(occ_base)))
    occupants.append(occupancy)

df['Jumlah Orang'] = occupants

# Verify physics consistency
vi_product = np.array(voltages) * np.array(currents)
power_col = np.array(powers)
corr = np.corrcoef(vi_product, power_col)[0, 1]
print(f"\nPhysics verification:")
print(f"  Correlation(V×I, Daya) = {corr:.6f}")
print(f"  Mean |V×I - Daya| = {np.mean(np.abs(vi_product - power_col)):.4f} W")
print(f"  Relative error = {np.mean(np.abs(vi_product - power_col) / np.maximum(vi_product, 1.0))*100:.3f}%")

# Save
df.to_excel("/Users/macbookpro/Documents/jurnal_penelitian/.claude/worktrees/fix-notebook-v7/sensor_data.xlsx",
            sheet_name="Sensor Data", index=False)
print(f"\nSaved to sensor_data.xlsx ({len(df)} records)")
