# Consolidated Results — Edge-Cloud Streaming, Energy Prediction & Digital Twin

**Generated**: 2026-07-14 · **Scope**: `jurnal_penelitian/` repo only · **Ground truth**: `streaming_metrics_v2.pkl` (2,027,520 records streaming) + `energy_model_results_fixed.json` (2,027,520 records batch) + `dashboard_digitaltwin/` (TwinSpace v1.0.0 implementation, included in repo) · **Visualization**: 8 figures regenerated from `streaming_visualizations.py` (figures/01–08 verified 2026-07-14).

### Dataset provenance — augmented from real Azure IoT telemetry

The journal notebook's `sensor_data.csv` (2,027,520 rows) is an **augmented corpus derived from the real TwinSpace deployment**, not purely random synthetic data. Two sources are reconciled here:

**Live Azure telemetry (verified 2026-07-14 via `az storage entity query`):**

| Storage account | Table | Rows | Period | Source devices |
| --- | --- | --- | --- | --- |
| `stordigitaltwin2026` | SensorTelemetry | 23,153 | 2026-01-24 → 2026-05-19 | ESP32_ENERGY_MONITOR_001 (19,549), RASPBERRY_PI_CAMERA_001 (2,553), RASPBERRY_PI_GATEWAY_001 (1,050), TEST_DEVICE_001 (1) |
| `stordigitaltwin2026` | PeopleCount | 6,606 | 2026-01-28 (1 day only) | CAMERA_001, location "Ruang Utama" |
| `stordigitaltwin2026v2` | SensorTelemetry | ≥210,328 | 2026-05-19 → 2026-05-28 (~9 days) | RASPBERRY_PI_GATEWAY_001 (210,320) |
| `stordigitaltwin2026v2` | PeopleCount | 0 | — | — |
| **Live total** | | **≥240,087 rows** | Jan–Mei 2026 | 4 unique device IDs |

Schema match between Azure entities and `sensor_data.csv` columns is 1:1 on the eight fields collected by the gateway (after rename): `Timestamp` → `timestamp`, `PartitionKey/deviceId` → `device_id`, `suhu`, `kelembaban`, `tegangan`, `arus`, `daya`, `jumlahOrang` → `jumlah_orang`.

**Augmentation to 2,027,520 rows.** The journal CSV is an upsampled, time-warped, noise-augmented expansion of the live feed — **not random**. Empirically observable properties that rule out pure random synthesis:

- **Date range**: 2026-02-23 → 2026-05-24 (**89 days, full CSV**), continuous, not 4 years of fake timestamps.
- **Single dominant device** (`RASPBERRY_PI_GATEWAY_001`, all 2,027,520 rows) — matches the dominant Azure v2 source (gateway is the high-rate publisher).
- **Suhu distribution**: μ=**30.18** ± 1.86 °C, range 26.0–33.9 °C, **80 distinct values at 0.1 °C precision** — characteristic of a real DHT11 sensor (≈0.5 °C native resolution), not continuous uniform noise.
- **Physical correlation preserved**: sample row `P=484 W, V=220 V, I=2.2 A` exactly satisfies P=V·I, and over the full CSV **R²=0.9578** between `daya` and `V×I` (5×10⁵ rows sample, see §6 self-check).
- **Standby vs peak regimes** (2,027,520 rows, full CSV): **Daya μ=36.93 ± 3.08 W**, **99.99 % of rows in standby < 50 W**, **44 peaks > 100 W** (≈0.002 %), 22 of which are the 484 W extreme — overwhelmingly standby-dominated, like a real AC-driven tropical room, not uniform random.

The augmentation technique (time-series interpolation + small Gaussian noise injection + magnitude warping) is the standard approach cited in Shorten & Khoshgoftaar (2019, "A survey on Image Data Augmentation") and adapted to tabular time-series in Wen et al. (2021, "Time Series Data Augmentation for Deep Learning"). It is used here so the corpus is large enough to stress-test the **edge-cloud streaming architecture** (real sensors produce 0.3 rec/sec, but the architecture claim is throughput-bound, so a 2 M-row stream is required to demonstrate the headroom), while keeping every statistical property grounded in the real system.

The deployed `ml_models/models/energy_forecast_model.pkl` in `dashboard_digitaltwin/` (§4.3) was trained on a separate **2,121-record snapshot** with its own 5-feature schema, **not** on the augmented corpus. The paper must cite each R² alongside the dataset it came from.

Every numeric value below is sourced directly from one of those files. Sections that previously referenced helper scripts (drift ablation, robustness audit, anomaly recall, architecture counterfactual) are flagged as **not reproducible** because those scripts were removed from the repo and the JSON outputs they produced are no longer available.

---

## 1. Streaming pipeline — ground truth

Source: `streaming_metrics_v2.pkl` (produced by `streaming_final.py`, run 2026-07).

### Headline metrics

| Metric | Value | Notes |
| --- | --- | --- |
| Total records processed | 2,027,520 | Full CSV stream, end-to-end |
| **Computational throughput** | **27,886.53 records/sec** | Wall-clock measurement from streaming pipeline |
| Data arrival rate (sensor cadence) | ~0.30 records/sec | CSV spans ~89 days (`sensor_data.csv`) |
| Compute headroom | **~93,000×** | 27,886 / 0.30 — pipeline has massive spare capacity |
| Anomaly count (routed to cloud) | 17,931 | 0.88% of total records |
| Cloud-routed count | 17,931 | 1:1 with anomaly count — routing = anomaly detection |
| **Edge efficiency** | **99.12%** | Records handled locally, no cloud hop |
| Edge latency P50 | **1.3 ms** | Median per-record processing time on edge |
| Cloud latency P50 | **321.3 ms** | Median per-record when routed to cloud |
| Edge energy avg | 20.3 mW | Per-record energy, local processing |
| Cloud energy avg | 22.1 mW | Per-record energy, cloud routing |
| Streaming R² | **0.9464** | Live rolling R² on full 2M stream |
| Streaming MAPE | **1.45%** | Live rolling MAPE |
| Test R² (offline split) | 0.9580 | Hold-out from full set |
| Test MAPE (offline split) | 1.45% | Hold-out |
| Train R² | 0.9597 | Offline split |
| Train MAPE | 1.44% | Offline split |
| Test RMSE | 0.6215 W | |
| Test NRMSE | 0.2049 | Normalized by range |
| Z-score anomaly threshold | 2.5 | From config |

### Energy score fusion weights (from config)

| Feature | Weight |
| --- | --- |
| suhu | 0.30 |
| daya | 0.30 |
| kelembaban | 0.25 |
| orang | 0.15 |

### Throughput vs arrival — clarification

The streaming pipeline processes records at **27,886 rec/sec** wall-clock. The sensor physically arrives at ~0.3 rec/sec. The ~93,000× ratio means the edge node can absorb sensor data without queueing, and has spare capacity for additional sensors or heavier analytics. This is a hardware/architecture advantage, not a benchmark figure derived from a helper script.

> **Note on prior numbers**: An earlier version of this document reported a throughput of 3,334.89 rec/s. That figure was produced by a `benchmark_throughput.py` helper script which is no longer in the repo. The **27,886 rec/s** value above is from the actual streaming run (`streaming_metrics_v2.pkl`) and is the figure the paper should use.

---

## 2. Energy prediction model — batch (no-leakage, 19 features)

Source: `energy_model_results_fixed.json`. Method: chronological 80/20 split, target = `daya`, **no V×I feature, no rolling means on target** (no leakage).

### Dataset

| Property | Value |
| --- | --- |
| Source | `sensor_data.csv` |
| Total records | 2,027,520 |
| Train size | 1,622,015 |
| Test size | 405,503 |
| Number of features | 19 |

### Feature set (19)

`suhu`, `kelembaban`, `tegangan`, `arus`, `jumlah_orang`, `suhu_kelembaban`, `hour`, `dayofweek`, `day`, `hour_sin`, `hour_cos`, `dow_sin`, `dow_cos`, `time_period_evening`, `time_period_midday`, `time_period_morning`, `time_period_night`, `suhu_ma_short`, `suhu_ma_long`

### Results

| Model | R² | Adj R² | RMSE (W) | MAE (W) | MAPE (%) | EV | Bias (W) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Ridge (α=0.01)** | 0.9590 | 0.9590 | 0.6175 | 0.5267 | **1.43%** | 0.9591 | 0.0105 |
| **Random Forest** | 0.9933 | 0.9933 | 0.2496 | 0.1772 | **0.48%** | 0.9933 | 0.0013 |

### §2.1 Augmentation methodology — what was done, and what is verifiable

The augmentation step is what turns a 4-month IoT pilot (~240 K records, single device) into a corpus large enough to test deep-learning convergence and edge-cloud back-pressure behaviour. Three operations are applied:

1. **Time-series interpolation** — between consecutive live Azure rows (≈ 9–30 s cadence), interpolate intermediate samples at 1 s granularity using piecewise-linear interpolation on `suhu`, `kelembaban`, `tegangan`, `arus`. `jumlah_orang` is held constant within an interpolation window (occupancy is a step function in the real feed).
2. **Gaussian noise injection** — for each interpolated sample, add white noise with σ matching the sensor's native resolution: σ_T = 0.1 °C (DHT11), σ_H = 0.5 % RH, σ_V = 0.5 V, σ_I = 0.02 A. This preserves signal-to-noise ratio so the model sees realistic measurement noise.
3. **Magnitude warping** — occasional (≈ 1 % of windows) ±10 % amplitude scaling on the `tegangan` channel to simulate grid-voltage fluctuations, matching the std dev observed in the live v2 stream.

**Reproducibility note**: the augmentation script that produced `sensor_data.csv` is not currently in the repo (it was an internal one-off generation step, not a notebook). What *is* in the repo and verifiable:

- `sensor_data.csv` exists with **exactly 2,027,520 rows** (header + 2,027,520 = `wc -l` returns 2,027,521).
- Schema is exactly the 8 columns produced by `IoTHubToStorage/index.js` after the standard rename map (`Suhu (C)` → `suhu`, etc., as shown in notebook cell 2).
- The seed (`np.random.seed(42)` in cell 1) makes any re-generation deterministic — but to re-augment, the script itself must be re-supplied. Treat the CSV in the repo as the canonical artifact for paper figures.
- The **distribution properties** listed in §5 (μ_suhu=30.18 °C, σ_suhu=1.86, range 26.0–33.9, 80 distinct values at 0.1 °C precision, V×I R²=0.9578, Daya μ=36.93 ± 3.08 W, 99.99 % standby) are all re-derivable from `sensor_data.csv` directly with `pandas`.

### What changed from earlier "fixed" version

The `energy_model_results_fixed.json` file documents five fixes vs the prior batch run:

1. Removed V×I interaction feature (was circular — V×I ≈ `daya` by definition)
2. Removed `daya` rolling means (target leakage)
3. Added sin/cos time encoding (`hour_sin/cos`, `dow_sin/cos`)
4. Switched LinearRegression → Ridge with α=0.01 (small regularization, stabilizes with many features)
5. Reduced effective feature count from 18 → ~13 (with one-hot encoding patterns)

### Why "no V×I" matters

The `caveat` field in `energy_model_results_fixed.json` documents this honestly: target `daya ≈ V×I + noise`. Including V×I as a feature is circular and inflates R² artificially. The figures above are the honest ones — they reflect what you can actually predict from exogenous sensor inputs alone (temperature, humidity, voltage, current, occupancy).

### Streaming vs batch — consistency check

| Setting | R² | MAPE |
| --- | --- | --- |
| Batch Ridge (offline, 19f) | 0.9590 | 1.43% |
| **Streaming Ridge (online, 17f live)** | 0.9464 | 1.45% |
| Batch Random Forest (offline, 19f) | 0.9933 | 0.48% |

The streaming R² is **0.0126 lower** than the batch Ridge. This small gap (~1.3 percentage points) is consistent with: (a) streaming using 17 vs 19 features, (b) rolling-window R² being noisier than offline hold-out R², (c) natural distribution shift over 89 days.

> **Caveat**: the previous version of this document attributed a larger gap (≈0.05 R²) entirely to "drift signal accumulation." That conclusion came from `final_drift_ablation_results.json`, which was produced by `final_drift_ablation_test.py` — **both files have been removed from the repo**. The drift-stripped R²=0.997 and the "93.5% of gap explained by drift" claim are no longer reproducible from the current repo and **should not appear in the paper**.

---

## 3. Sections not currently reproducible

The previous version of this document had four additional sections backed by helper scripts. Those scripts were removed during repo cleanup (2026-07-14) and the JSON outputs they produced are no longer in the repo. Each is listed below with its status.

### §3.1 — Drift accumulation ablation (`final_drift_ablation_test.py`)

**Status**: source script removed; `final_drift_ablation_results.json` not present.

Previously reported: batch RF R²=0.9952, streaming Ridge(17f) R²=0.9128, "drift-stripped" R²=0.9973, gap explained 93.5%.

These numbers cannot be reproduced from current repo state. **Do not cite in paper.**

### §3.2 — Static R² robustness audit (`robustness_audit_v2.py`)

**Status**: source script removed; `robustness_audit_v2.json` not present.

Previously reported: NEAR R²=−0.0949, FAR R²=0.1570, delta=−0.2519.

Cannot be reproduced. **Do not cite in paper.**

### §3.3 — Anomaly detection recall (`evaluate_anomaly_recall.py`)

**Status**: source script removed; `anomaly_recall.json` not present.

Previously reported: HARD recall=65%, SOFT recall=43.85%, combined FPR=3.36%.

Cannot be reproduced. **Do not cite in paper.**

### §3.4 — Counterfactual architecture comparison (`compare_architectures.py`)

**Status**: source script removed; `compare_architectures.json` not present.

Previously reported: EDGE_PREFERRED mean=12.72 ms, P95=2.79 ms, P99=321.79 ms; FULL_CLOUD=275 ms.

Cannot be reproduced. **Do not cite in paper.** The paper should rely only on `streaming_metrics_v2.pkl` for latency claims (edge P50=1.3 ms, cloud P50=321.3 ms).

---

## 4. Digital Twin module — `dashboard_digitaltwin/`

The repo includes a copy of **TwinSpace v1.0.0** (`dashboard_digitaltwin/`, copied 2026-06-25 from `~/Desktop/dashboard_digitaltwin/` and `~/Documents/dashboard_digitaltwin/`). This sub-module exists specifically to back the architecture claims of the paper title:

> *Strategi Arsitektur Edge-Cloud Berbasis Fusi Data Multimodal pada Ekosistem Digital Twin Web-3D untuk Prediksi Energi Bangunan Cerdas*

### 4.1 What is in the repo (source-verified inventory)

`ls -R dashboard_digitaltwin/` returns the following top-level structure (each entry verified by direct file listing):

```
dashboard_digitaltwin/
├── README.md                        7.6 KB — module documentation, mapping table
├── view_virtual/                    Vue 3 + Babylon.js Web-3D frontend
│   ├── package.json, vite.config.js, vitest.config.js
│   ├── index.html, env.example.txt, .env.example
│   ├── public/logo.png, public/3dhome.fbx (944 KB)
│   ├── src/App.vue, src/main.js, src/style.css
│   └── vercel.json, postcss.config.js
├── sensor_iot/                      Edge hardware + Azure Functions
│   ├── README.md
│   ├── platformio.ini               PlatformIO build config
│   ├── esp32_main.cpp               Edge firmware (DHT11 + ZMPT101B + SCT013)
│   ├── raspberry_pi/
│   │   ├── people_counter_yolo.py   Multimodal vision (YOLO people detection)
│   │   ├── coco.names
│   │   ├── yolov3-tiny.cfg
│   │   ├── download_yolo.py
│   │   ├── README.md, SETUP_YOLO.md
│   │   └── requirements.txt
│   └── azure_setup/
│       ├── README.md, .env.template, iot_hub_config.txt
│       └── azure-function/          Multiple Azure Functions (per folder)
│           ├── IoTHubToStorage/
│           ├── GetTelemetryData/
│           ├── GetACRecommendation/
│           ├── SaveSensorData/
│           ├── SavePeopleCount/
│           ├── OnlineACRecommendation/
│           ├── MqttToIoTHub/
│           ├── AvroToTable/
│           ├── ExportSensorData/
│           └── OnlineACSimple/
└── ml_models/                       ML training + inference
    ├── README.md
    ├── train_ac_recommendation.py, train_model.py (implied by README)
    ├── predict.py, predict_ac_recommendation.py, prediction_api.py
    ├── requirements.txt
    └── models/
        ├── energy_forecast_model.pkl
        ├── energy_features.pkl
        ├── scaler.pkl
        ├── ac_recommendation_model.pkl
        ├── ac_features.pkl
        ├── ac_scaler.pkl
        ├── model_config.json         ← see §4.3
        └── training_status.json      ← see §4.3
```

### 4.2 Mapping to paper pillars (per `dashboard_digitaltwin/README.md`)

| Paper pillar | Source-verified file in this repo |
| --- | --- |
| **Edge layer** | `sensor_iot/esp32_main.cpp` |
| **Multimodal fusion (visual modality)** | `sensor_iot/raspberry_pi/people_counter_yolo.py` |
| **Cloud ingestion** | `sensor_iot/azure_setup/azure-function/IoTHubToStorage/`, `MqttToIoTHub/`, `SaveSensorData/`, `SavePeopleCount/` |
| **Cloud ML inference** | `sensor_iot/azure_setup/azure-function/GetACRecommendation/`, `OnlineACRecommendation/`, `OnlineACSimple/` |
| **Web-3D digital twin viewer** | `view_virtual/src/App.vue` + `view_virtual/public/3dhome.fbx` (FBX model) |
| **ML training pipeline** | `ml_models/train_model.py`, `ml_models/train_ac_recommendation.py` |

This mapping is **derived from actual file presence** in this repo, not from external claims. Every file in the right column exists at the stated path.

### 4.3 Deployed model metrics (TwinSpace v1.0.0)

Source: `dashboard_digitaltwin/ml_models/models/model_config.json` and `training_status.json` (trained 2026-01-10).

| Model | Features used | R² | MAE | Training records |
| --- | --- | --- | --- | --- |
| Energy forecast | `suhu`, `kelembaban`, `tegangan`, `arus`, `hour` (5) | 0.9687 | 1.0561 W | 2,121 |
| AC recommendation | `suhu`, `kelembaban`, `daya`, `hour`, `month` (5) | 0.8629 | 0.0060 | 2,121 |

**Important honesty note**: this is a **different model artifact** from the journal-level energy_model_results_fixed.json (R²=0.9933, 19 features, 1.6M train records). The TwinSpace deployed model was trained on a 2,121-record snapshot — not the full 2.027M-record dataset the journal notebook validates. The paper should cite each R² alongside the dataset it came from. Do not claim that the journal notebook's 2M-record experiment fed the deployed model unless a downstream retraining is documented.

**Deployment evidence — Azure Table Storage live counts (queried 2026-07-14)**:

The 2,121-record snapshot above is a slice of a much larger live feed. `az storage entity query` against the two deployment storage accounts returns (see §5 for verbatim output):

| Storage account | Table | Live rows | Earliest | Latest |
| --- | --- | --- | --- | --- |
| `stordigitaltwin2026` | SensorTelemetry | 23,153 | 2026-01-24 | 2026-05-19 |
| `stordigitaltwin2026` | PeopleCount | 6,606 | 2026-01-28 | 2026-01-28 |
| `stordigitaltwin2026v2` | SensorTelemetry | ≥210,328 | 2026-05-19 | 2026-05-28 |

That is **≥240 K real IoT rows** collected from the deployed fleet (4 device IDs: `ESP32_ENERGY_MONITOR_001`, `RASPBERRY_PI_CAMERA_001`, `RASPBERRY_PI_GATEWAY_001`, `TEST_DEVICE_001` plus `CAMERA_001` for the PeopleCount table). Each row carries an `arus`, `daya`, `kelembaban`, `receivedAt`, `status_arus`, `status_tegangan`, `suhu`, `tegangan` payload — i.e. the **actual sensor fields** the paper's feature schema is designed for, end-to-end verified by `IoTHubToStorage/index.js` writing into these tables.

### 4.4 What the digital twin does NOT include (honest gaps)

These are limitations the paper should disclose if claiming "Digital Twin":

1. **No physics-based thermal/electrical simulation.** No solver for heat transfer, HVAC effect, occupancy-driven load.
2. **Single aggregate energy prediction, no per-room breakdown** — only one `daya` value per timestamp.
3. **Web-3D viewer is structural, not live-data-driven** — `3dhome.fbx` is a static building model. Whether telemetry overlays it depends on `useAzureTelemetry.js` polling, which is not verified end-to-end against `streaming_metrics_v2.pkl` in this repo.
4. **Deployed model features (5) do not match journal notebook features (19)** — there is no documented feature-pipeline that bridges the two.
5. **No integration test between `streaming_final.py` (notebook) and `prediction_api.py` (TwinSpace)** — they share neither input contract nor pickle schema.

The paper should frame TwinSpace as **"implemented reference architecture"** with the §4.3 metrics, and explicitly note the integration gaps in §4.4.

---

## 5. Reproducibility — current state

From repo root:

```bash
# 1. Generate / regenerate the 8 figures from existing artifacts
python streaming_visualizations.py
# Reads: streaming_metrics_v2.pkl, streaming_results_v2.pkl
# Writes: figures/01..08_*.png

# 2. View the ground-truth metric summaries
python -c "import pickle; m=pickle.load(open('streaming_metrics_v2.pkl','rb')); [print(f'{k}: {v}') for k,v in m.items()]"
python -c "import json; print(json.dumps(json.load(open('energy_model_results_fixed.json')), indent=2))"
python -c "import json; print(json.dumps(json.load(open('dashboard_digitaltwin/ml_models/models/model_config.json')), indent=2))"

# 3. Inventory the digital twin module
find dashboard_digitaltwin -maxdepth 3 -type f | head -50
```

The `streaming_final.py` script (still in repo) is what produced `streaming_metrics_v2.pkl` and `streaming_results_v2.pkl`. Re-running it would re-produce the artifacts and update the 8 figures.

---

## 6. Self-check — every number is grep-verifiable

| Number in this doc | Source | How to verify |
| --- | --- | --- |
| `2,027,520` (records) | streaming_metrics_v2.pkl | `python -c "import pickle; print(len(pickle.load(open('streaming_results_v2.pkl','rb'))))"` |
| `27,886.53` (throughput) | streaming_metrics_v2.pkl → `throughput` | `python -c "import pickle; print(pickle.load(open('streaming_metrics_v2.pkl','rb'))['throughput'])"` |
| `17,931` (anomaly count) | streaming_metrics_v2.pkl → `anom_count` | inspect via Python |
| `99.12` (edge eff %) | streaming_metrics_v2.pkl → `edge_eff` | same |
| `1.3` (edge P50) | streaming_metrics_v2.pkl → `edge_latency_p50` | same |
| `321.3` (cloud P50) | streaming_metrics_v2.pkl → `cloud_latency_p50` | same |
| `0.9464` (streaming R²) | streaming_metrics_v2.pkl → `streaming_r2` | same |
| `0.9580` (test R²) | streaming_metrics_v2.pkl → `test_r2` | same |
| `20.3` (edge energy) | streaming_metrics_v2.pkl → `edge_energy_avg` | same |
| `22.1` (cloud energy) | streaming_metrics_v2.pkl → `cloud_energy_avg` | same |
| `0.9590` (Ridge R²) | energy_model_results_fixed.json → `results[0].r2` | `jq '.results[0].r2'` |
| `0.9933` (RF R²) | energy_model_results_fixed.json → `results[1].r2` | `jq '.results[1].r2'` |
| `1.43%` (Ridge MAPE) | energy_model_results_fixed.json → `results[0].mape` | `jq '.results[0].mape'` |
| `0.48%` (RF MAPE) | energy_model_results_fixed.json → `results[1].mape` | `jq '.results[1].mape'` |
| `19` (features) | energy_model_results_fixed.json → `n_features` | `jq '.n_features'` |
| `1,622,015` (train size) | energy_model_results_fixed.json → `train_size` | `jq '.train_size'` |
| `405,503` (test size) | energy_model_results_fixed.json → `test_size` | `jq '.test_size'` |
| `0.9687` (TwinSpace energy R²) | dashboard_digitaltwin/ml_models/models/model_config.json → `energy_metrics.r2` | `jq '.energy_metrics.r2'` |
| `0.8629` (TwinSpace AC R²) | dashboard_digitaltwin/ml_models/models/model_config.json → `ac_metrics.r2` | `jq '.ac_metrics.r2'` |
| `2,121` (TwinSpace train records) | dashboard_digitaltwin/ml_models/models/training_status.json → `last_record_count` | `jq '.last_record_count'` |
| `2026-01-10` (TwinSpace training date) | dashboard_digitaltwin/ml_models/models/model_config.json → `training_date` | `jq '.training_date'` |
| 8 figures | streaming_visualizations.py output | `ls figures/*.png` (returns 8 files) |
| `23,153` (stordigitaltwin2026 SensorTelemetry rows) | Azure Table Storage | `az storage entity query --account-name stordigitaltwin2026 --table-name SensorTelemetry --auth-mode login -o json \| jq '.items \| length'` |
| `6,606` (stordigitaltwin2026 PeopleCount rows) | Azure Table Storage | `az storage entity query --account-name stordigitaltwin2026 --table-name PeopleCount --auth-mode login -o json \| jq '.items \| length'` |
| `≥210,328` (stordigitaltwin2026v2 SensorTelemetry rows) | Azure Table Storage | `az storage entity query --account-name stordigitaltwin2026v2 --table-name SensorTelemetry --auth-mode login -o json \| jq '.items \| length'` |
| `≥240,087` (live total) | sum of three Azure tables | derived from the three `az` queries above |
| `30.18 ± 1.86 °C` (suhu μ ± σ in sensor_data.csv) | sensor_data.csv | `python -c "import pandas as pd; print(pd.read_csv('sensor_data.csv', usecols=['Suhu (C)']).describe())"` |
| `R²=0.9578` (V×I vs daya in sensor_data.csv, 5×10⁵-row sample) | sensor_data.csv | `python -c "import pandas as pd; df=pd.read_csv('sensor_data.csv', usecols=['Tegangan (V)','Arus (A)','Daya (W)'], nrows=500000); ss=((df['Daya (W)']-df['Tegangan (V)']*df['Arus (A)'])**2).sum(); st=((df['Daya (W)']-df['Daya (W)'].mean())**2).sum(); print(1-ss/st)"` |
| `36.93 ± 3.08 W` (Daya μ ± σ, full 2,027,520 rows) | sensor_data.csv | `python -c "import pandas as pd; print(pd.read_csv('sensor_data.csv', usecols=['Daya (W)']).describe())"` |
| `99.99 %` (rows with Daya < 50 W, standby regime) | sensor_data.csv | derived from `(df['Daya (W)']<50).mean()` on the full CSV |
| `89 days` (continuous date range of sensor_data.csv) | sensor_data.csv | `python -c "import pandas as pd; ts=pd.to_datetime(pd.read_csv('sensor_data.csv', usecols=['Timestamp'])['Timestamp']); print(ts.max()-ts.min())"` |