<!-- markdownlint-disable MD060 -->

# AUDIT REPORT — `jurnal_penelitian`

**Tanggal audit:** 2026-07-02
**Judul jurnal:** Strategi Arsitektur Edge-Cloud Berbasis Fusi Data Multimodal pada Ekosistem Digital Twin Web-3D untuk Prediksi Energi Bangunan Cerdas
**Tujuan:** single source of truth untuk semua angka & klaim sebelum penulisan paper dimulai.
**TIDAK termasuk:** narasi paper, abstract, atau claims yang belum dibuktikan oleh kode.

---

## 0. CARA BACA LAPORAN INI

- **Status klaim:**
  - 🟢 **VALID** — terverifikasi, reproducible (script ada, last-run artefact ada)
  - 🟡 **VALID DENGAN CATATAN** — angka benar, tapi framing/scope perlu disesuaikan
  - 🔴 **INVALID / TIDAK BISA DIPERTAHANKAN** — angka atau klaim butuh koreksi substantif
- **Tidak semua angka yang Anda lihat di README/CLAUDE.md berasal dari eksperimen yang sama.** Tabel rekonsiliasi di Bagian 2 memetakan satu per satu.

---

## 1. RINGKASAN EKSEKUTIF (5 butir paling kritis)

1. **V×I CIRCULARITY MENGINFEKSI KEDUA UTAMA KLAIM.** Model "prediksi energi" pada dasarnya belajar f(V, I) ≈ daya (lihat Bagian 3). Target di `sensor_data.csv` adalah V×I secara langsung (corr 0.989, MAE 0.5 W terhadap V×I), dan notebook energy_prediction_models.ipynb menambahkannya sebagai fitur (`tegangan_arus`). Streaming notebook bahkan lebih eksplisit: target = `clean_day = V*I + noise + drift`, dengan V×I sebagai fitur, lalu Ridge belajar. R²=0.9952 valid secara metrik, tetapi TIDAK menggambarkan "Prediksi Energi Bangunan Cerdas" — itu cuma restatement hukum Ohm. Judul perlu reframing (lihat Bagian 3.3).
2. **"RF streaming 0.9427" adalah eksperimen BERBEDA — bukan streaming.** `final_drift_ablation_test.py` (1 Juli) memilih subset FAR (jarak ≥ 1000 dari hard anomaly), split chronological 80/20, lalu fit RF. Ini adalah **batch-with-cherry-picked-clean-data**, bukan pipeline streaming. Streaming ridge yang sebenarnya (dari `stream_full_audit.py` setelah fix z=2.5 + buffered R²) R²-nya cuma ~0.27–0.35 (avg chunks 36–41). Dua angka ini tidak comparable; lihat Bagian 2 tabel.
3. **Tiga angka "196 ms cloud / 275 ms cloud / 196+200ms cloud" adalah konstanta hardcoded, bukan hasil benchmark.** `CLOUD_NET_OVERHEAD + CLOUD_PROC_LAT + CLOUD_DT_SYNC_LAT = 45+150+80 = 275 ms` di dalam source. README mengubahnya jadi "~196 ms" tanpa justifikasi terdokumentasi. Tidak ada pengukuran jaringan atau benchmark round-trip yang tersimpan.
4. **Modul Digital Twin (`dashboard_digitaltwin/`) masih berupa prototype UI 3D — belum kembaran digital yang fungsional.** Yang ada: glTF floor plan dengan icon sensor overlay, polling 5-detik ke Azure Function, particle effect pada AC. Yang TIDAK ada: physics-based simulation (tidak ada thermal model, tidak ada occupancy-driven HVAC), evaluasi prediksi vs terukur per-ruangan, atau metrik yang membuktikan "Digital Twin Web-3D" itu fungsional di paper. Lihat Bagian 4.
5. **"Multi-node multi-modal" di CSV adalah post-hoc labelling, bukan really-multi-source.** CSV punya `DeviceID = RASPBERRY_PI_GATEWAY_001` untuk SEMUA baris. Klaim multimodal (numerik + visual + health) berdiri di kode `esp32_main.cpp` dan `people_counter_yolo.py`, bukan di data CSV yang dipakai di eksperimen. Lihat Bagian 5 item "multimodal".

---

## 2. TABEL REKONSILIASI ANGKA

> Singkatan: 🟢 valid · 🟡 valid dengan catatan · 🔴 invalid/cherry-picked · ⚪ tidak dinilai di sini.

| Metrik | Klaim lama (assessment) | Klaim README/CLAUDE.md | Nilai tervalidasi | Sumber file | Status |
|---|---|---|---|---|---|
| **R² batch RF** (energy, 18 fitur, shift(1), 80/20 chrono) | 0.9952 | 0.9952 | 0.9952 (RF_test=0.9952, RMSE=0.211W) | `energy_model_results_fixed.json`, `eval_energy_fixed.py` | 🟡 lihat Bagian 3 |
| **R² batch LR** (energy, 18 fitur, shift(1)) | 0.9629 | 0.9649 → "FIXED" | 0.9649 (LR_test=0.9649, RMSE=0.572W) | `energy_model_results_fixed.json` | 🟡 lihat Bagian 3 |
| **SGD online R²** (4 fitur baseline) | 0.595 | 0.595 | 0.595 (claimed; tidak ada script reproduce) | `edge_cloud_streaming.ipynb` (referensi) | 🟡 disclaimer saja |
| **R² streaming Ridge retrain (z=2.0 lama)** | "robustness moderate" | "0.35 avg chunks 29-40" | 0.3480 static clean / 0.18 rolling mean | `decisive_r2_test_hasil_mentah.txt` (29 Juni) | 🟡 |
| **R² streaming Ridge retrain (z=2.5 baru)** | — | "~0.27 avg chunks 36-41" | tidak ada angka static yang dihitung ulang pada z=2.5; angka "~0.27" klaim dari rolling window di `stream_full_audit.py` | `stream_full_audit.py`, README L54 | 🟡 rentan terhadap bug #1/#2 yang sudah diperbaiki |
| **R² streaming RF "0.9427"** | 0.9427 (di assessment) | TIDAK ada di README/CLAUDE.md | **0.9629** Ridge(18f) / **0.9629** RF(18f) pada FAR-only chronological 80/20 | `final_drift_ablation_results.json`, `final_drift_ablation_test.py` | 🔴 eksperimen berbeda, lihat Bagian 2.1 |
| **R² statis Ridge pada FAR-only full** | — | 0.1570 (di robustness_audit_v2) | 0.1570 | `robustness_audit_v2.json` | 🟡 |
| **R² drift-stripped RF** | — | 0.997 (definitive finding) | Ridge+strip 0.9973 / RF+strip 0.9973 | `final_drift_ablation_results.json` L41-46 | 🟡 |
| **Hard anomaly detection rate** | "hard 100%" | 3.24% z=2.0 → 3.4% z=2.5 (union with soft) | 3.4% (union); **recall per-class TIDAK dilaporkan** | `stream_full_audit.py`, README L32 | 🔴 angka union tidak sama dengan "hard 100%" |
| **Soft anomaly recall** | "soft 8.5%" | TIDAK ada | tidak dihitung terpisah per-kelas di script mana pun yang ditemukan | — | 🔴 angka tidak ditemukan sumbernya |
| **Edge latency (median)** | — | 1.49 ms/record | BENAR hanya kalau `SUM_EDGE_LAT_MEDIAN` (= 1.3 ms constant) dipakai; ini bukan benchmark runtime, ini hardcoded | `edge_cloud_streaming.ipynb` L33-36 | 🔴 bukan empiris |
| **Cloud latency (median)** | "275 ms diasumsikan" | "196 ms (incl network + heavy processing)" | sumber konstanta: `CLOUD_NET_OVERHEAD (45) + CLOUD_PROC_LAT (150) + CLOUD_DT_SYNC_LAT (80) = 275 ms` (ini dipakai `stream_full_audit.py`). README mengatakan 196 ms — tidak ada script yang menghitung 196 ms | `edge_cloud_streaming.ipynb`, `stream_full_audit.py` | 🔴 |
| **Throughput** | ~1,700 records/s (CLAUDE.md) | README: tidak eksplisit | `stream_full_audit.py` chunked ke 50K/chunk, throughput per-chunk dilaporkan, tidak ada angka global single-number | README, `stream_full_audit.py` | 🟡 benchmark per-chunk ≠ throughput realistis |
| **18 fitur** | disebutkan | disebutkan | 10 numerik + 5 time-period one-hot + 3 rolling = 18 | `eval_energy_fixed.py` L57-77 | 🟢 reproducible |

### 2.1 Rekonsiliasi "RF streaming 0.9427"

**Assessment lama:** "RF streaming R² = 0.9427."
**README sekarang:** tidak ada angka itu. README hanya menampilkan R² streaming Ridge (0.27–0.35).
**Asal angka:** Eksperimen di `final_drift_ablation_test.py` (commit 35751dc, 1 Juli). METODOLOGI:

1. Filter hanya record dengan jarak ≥ 1000 dari nearest hard anomaly (FAR group = 90.4% data = 1.66M records).
2. Chronological 80/20 split pada FAR group saja.
3. Fit RandomForest(100, depth=15) pada train 80%, evaluasi pada test 20%.
4. Hasil: **RF R²_test = 0.9629** (bukan 0.9427; bukan "streaming"; pada data FAR-only).

**Bedanya dengan streaming sungguhan:**

- Streaming sungguhan (di `stream_full_audit.py`) memproses 2M baris SEKALUAN dengan update model periodik. Ridge di sana kesulitan karena distribusi y drift (drift_signal grow ~+7W di akhir stream).
- Ablation script memilih FAR group (yang tidak terkena noise anomali) DAN chronological split (bukan streaming). R² yang lebih tinggi di ablation dibandingkan streaming bukan bukti RF lebih baik — itu bukti bahwa splitting+filtering+chronological berbeda dari streaming online.

**Kesimpulan:** Angka "RF streaming 0.9427" adalah misrepresentasi. Angka sebenarnya dari eksperimen itu adalah:

- RF(18f) test on FAR group = **0.9629** (R²)
- Ridge(18f) test on FAR group = **0.9128**
- RF+drift-stripped = **0.9973**
- Ridge+drift-stripped = **0.9973**

`final_drift_ablation_results.json` line 50-52 mencatat gap=0.053 antara RF batch dan RF ablation, dan ablation DRIFT-STRIPPED naik ke 0.997, mengkonfirmasikan hipotesis: drift akumulatif menjelaskan gap 0.995→0.943. Penemuan ini sahih secara saintifik (bukan angka palsu), tapi framing "RF streaming 0.9427" tidak benar.

### 2.2 Rekonsiliasi "anomaly detection"

- **Hard anomaly rate:** 200/2,027,520 = **0.0099%**. Soft anomaly rate: 2000/2,027,520 = **0.0987%**.
- **Union rate yang dilaporkan README (3.24% / 3.4%)** ≈ 65,000-69,000 record (lihat README Tabel B, z=2.5 → 69,099 anom = 3.4%). Ini 30× lebih banyak dari union ground truth 2,200.
- Artinya: deteksi anomali berdasarkan z-score energy_score menandai **68,000-an record** yang **bukan** ground-truth hard/soft anomaly. Klaim "100% hard recall" tidak bisa diverifikasi dari script mana pun di repo (recall per-kelas tidak pernah dihitung).
- Rekomendasi: tambah script `evaluate_anomaly_recall.py` yang:
  1. Load hard_indices (200 record) + soft_indices (2000 record) dari `anomaly_indices.pkl`.
  2. Load hasil streaming (`streaming_results_z25.pkl` di LFS).
  3. Hitung precision/recall/F1 per-kelas.

---

## 3. V×I CIRCULARITY — TEMUAN DETAIL + REKOMENDASI

### 3.1 Bukti di `sensor_data.csv`

```bash
$ python -c "import pandas as pd, numpy as np; df = pd.read_csv('sensor_data.csv', nrows=20000);
  print('corr(V*I, daya):', np.corrcoef(df['Tegangan (V)']*df['Arus (A)'], df['Daya (W)'])[0,1]);
  print('mean abs(daya - V*I):', np.abs(df['Daya (W)'] - df['Tegangan (V)']*df['Arus (A)']).mean())"
corr(V*I, daya): 0.9892532132549907
mean abs(daya - V*I): 0.49923357500000004 W
```

Kolom `Daya (W)` di CSV adalah V×I (atau V×I+small noise) secara langsung. Ini adalah **definisi daya listrik sesaat**, bukan "konsumsi energi bangunan terukur".

### 3.2 Bukti di notebook

**`energy_prediction_models.ipynb`** (line 41 → feature engineering):

```python
df["tegangan_arus"] = df["tegangan"] * df["arus"]   # ← fitur baru
y = df["daya"].values                                  # ← target
```

Target = `daya` (≈ V×I dari CSV). Fitur termasuk `tegangan_arus` (= V×I). Jadi model belajar `daya ≈ a*V + b*I + c*V*I + ...` — secara matematis harusnya nyaris `daya ≈ k*V*I` dengan `k ≈ 1`.

**`edge_cloud_streaming.ipynb`** (Cell 3, lebih eksplisit):

```python
V = raw['tegangan'].values
I = raw['arus'].values
clean_day = V * I
noise_std = 0.05 * np.std(clean_day)
noise = np.random.normal(0, noise_std, len(clean_day))
raw['daya'] = clean_day + noise   # ← TARGET = V*I + noise
...
drift_signal = ... random walk ...
raw['daya'] += drift_signal
```

Target streaming = `V*I + noise + drift_signal`. Lalu:

```python
def _extract_features(self, row):
    ...
    tegangan = row.get("tegangan", 220.0)
    arus = row.get("arus", row["daya"] / max(tegangan, 1))
    ...
    return np.array([[
        row["suhu"], row["kelembaban"], tegangan, arus,
        row["jumlah_orang"],
        tegangan * arus,   # ← V*I sebagai fitur
        ...
    ]])
```

Ridge predict pada fitur yang sudah termasuk V×I untuk menghasilkan target yang juga V×I (+ noise + drift). Ini bukan leakage dalam pengertian standar (data train-test split chronological, shift(1)), tapi bukan predictive modelling secara meaningful — Ridge pada dasarnya mengingat konstanta proporsionalitas V×I ≈ daya.

**`dashboard_digitaltwin/ml_models/predict.py`** (line 40-49):

```python
features = ['suhu', 'kelembaban', 'jumlahOrang', 'tegangan']
# Arus TIDAK dipakai — predicted_power dikembalikan dari V tanpa I!
```

Model deployment di dashboard hanya tahu V (bukan I), tetapi targetnya daya. Model ini akan gagal saat deployment — fitur tidak lengkap.

### 3.3 Seberapa fatal & apa opsinya?

**Fatally undermining?**

- Untuk paper SINTA 1-2 atau Scopus Q1: YA, fatal. Reviewer akan menolak karena R² tinggi dari proses yang essentially trivial.
- Untuk SINTA 2-3 atau Scopus Q3-Q4: marginal, tapi perlu diaddress eksplisit.

**Tiga opsi mitigasi:**

**Opsi A — Reframe judul & klaim.** Ganti "Prediksi Energi Bangunan Cerdas" → "Estimasi Daya Real-time Berbasis Sensor Tegangan dan Arus di Edge", atau "Indoor Power State Inference dengan Edge Streaming". Pertahankan R²=0.9952 (valid secara teknis) tapi claim yang lebih lemah. Cocok untuk paper Q3.

- PRO: angka tetap valid, eksperimen lain (drift ablation, edge-cloud) tetap utuh.
- CON: klaim "cerdas" hilang, kontribusi mengecil.

**Opsi B — Tambahkan skenario forecasting multi-step.** Training: lagged V, I, suhu, occupancy, jam, hari, bulan, weekend, kalender. Target: daya pada t+5min, t+15min, t+1h. Tanpa V dan I saat prediction horizon sebagai input (hanya yang tersedia di t). Ini forecasting sungguhan.

- PRO: scientific contribution nyata.
- CON: butuh re-train + re-eval. Apakah R² tetap 0.99? Mungkin turun banyak di horizon panjang karena V,I di masa depan tidak diketahui.

**Opsi C — Hybrid: jadikan V×I sebagai fitur baseline, tambahkan exogenous regressors.** Training target = daya; fitur = V×I + lagged_external (suhu, kelembaban, occupancy_count, hour_sin, hour_cos, day_of_week, is_weekend, AC_setpoint, weather). Lalu ukung kontribusi incremental exogenous: ΔR²(block_information) = R²(V×I + exogenous) − R²(V×I only). Apakah exogenous menyumbang 5%? 50%? Itu pertanyaan riset yang sah.

- PRO: V×I jadi baseline yang defensible, exogenous sebagai novel contribution.
- CON: butuh data exogenous yang TIDAK ada di CSV (cuaca, AC_setpoint, holiday flag). CSV hanya punya 6 fitur numerik + timestamp + device_id.

**Rekomendasi saya:** Opsi C jika Anda punya waktu untuk generate data exogenous sintetis (cuaca dari API, AC schedule dari logging simulasi). Kalau tidak, Opsi A.

### 3.4 Apakah masalah serupa ada di `energy_prediction_models.ipynb`?

YA, identik. Notebook ini memakai `daya` dari CSV langsung (bukan V×I+noise+drift), tapi karena `daya ≈ V×I` di CSV, hasilnya sama saja. Kedua notebook rentan terhadap kritik yang sama.

---

## 4. STATUS MODUL DIGITAL TWIN — `dashboard_digitaltwin/`

### 4.1 Apa yang ada

**Frontend (view_virtual/):**

- Vue 3 + Babylon.js (3D rendering), `@babylonjs/core` ^8.43.0
- Komponen `DigitalTwin3D_Babylon.vue` (1285 baris): load glTF `3dhome.fbx`/`scene.gltf` (965 KB), sensor icon overlay (suhu/humidity/voltage/current/power), AC unit 3D primitive dengan particle system "cold air"
- `CesiumViewer.vue`: peta geospasial 3D (alternatif ke Babylon)
- Komponen lain: DashboardHome, SensorStatus, EnergyManagement, ACRecommendation, AdminDashboard, CameraStream, HistoricalAnalytics, ElectricityChart, TemperatureChart, PeopleChart, AlertSettings, DataTable
- 7 composables: `useAzureTelemetry.js` (polling 5s ke Azure Function `/telemetry/latest`), `useMLPrediction.js`, `useDummyData.js`, `useEnergyManagement.js`, `useFirebaseAuth.js`, `useMQTT.js`, `useHistoricalData.js`

**Hardware IoT (sensor_iot/):**

- `esp32_main.cpp` (2475 baris): firmware ESP32 — DHT11 + ZMPT101B + SCT013, WiFi, MQTT ke Azure IoT Hub
- `raspberry_pi/people_counter_yolo.py` (801 baris): YOLO v3-tiny people detection, publish ke MQTT broker
- `azure_setup/azure-function/`: 7+ Azure Functions (IoTHubToStorage, SaveSensorData, GetTelemetryData, OnlineACRecommendation, dll.)

**ML (ml_models/):**

- `train_model.py`, `train_ac_recommendation.py`, `predict.py`, `prediction_api.py` (Flask API)
- 5 .pkl (energy_forecast_model, ac_recommendation_model, scaler, ac_scaler, features)
- `model_config.json` klaim: Energy R²=0.969, AC R²=0.863 (model_version 1, training_date 2026-01-10)

### 4.2 Apa yang TIDAK ada (gap untuk klaim "Digital Twin Web-3D")

1. **Tidak ada physics-based thermal/electrical simulation.** Yang ditampilkan adalah glTF floor plan + icon overlay dari data Azure. Tidak ada solver yang menghitung "kalor dari 1 AC setara pengaruh suhu ruangan dalam 5 menit". Sensor icon hanya teks overlay statis.
2. **Tidak ada room-level energy breakdown.** Bangunan ditampilkan sebagai flat apartment dengan 6 ruangan (Living Room, Kitchen, Toilet, Bedroom) tapi model ML deployment (`predict.py`) hanya return single aggregate kW. Tidak ada disaggregation per-ruangan.
3. **Tidak ada benchmark / validasi "Digital Twin" sebagai klaim saintifik.** Tidak ada plot prediksi-vs-terukur, tidak ada error metric per-ruangan, tidak ada evaluasi occupancy-driven HVAC.
4. **Model deployment di dashboard tidak match dengan notebook.** Energy model di `ml_models/models/` punya 5 fitur (`suhu, kelembaban, tegangan, arus, hour`), sedangkan notebook energy punya 18 fitur (termasuk interaksi, rolling, one-hot). Model `.pkl` yang ada di-commit TIDAK dipanggil oleh notebook energy_prediction, dan script `train_model.py` di `dashboard_digitaltwin/` tidak reproducible dari state repo (data source = Azure Storage live, bukan CSV).
5. **TIDAK ada integrasi nyata antara notebook streaming 2M-record dan dashboard.** Notebook `edge_cloud_streaming.ipynb` berdiri sendiri dengan `sensor_data.csv` 2M record, sedangkan dashboard baca dari Azure Function (yang akan return data kosong jika Azure tidak aktif). `ml_models/models/*.pkl` adalah artifact terpisah, dilatih dengan script terpisah (`train_model.py`) yang tidak pernah dijalankan ulang dengan 2M record.

### 4.3 Penilaian kematangan

| Kriteria SINTA/Q2-Q3 | Status |
|---|---|
| Visualisasi 3D berjalan | 🟢 Ada glTF, sensor overlay, AC particle |
| Sensor data real-time fetch ke UI | 🟢 Polling ke Azure Function per 5s, fallback localStorage |
| Kode firmware IoT terdokumentasi | 🟢 ESP32 cpp + README wiring detail |
| Multimodal (numerik + visual) | 🟡 Ada YOLO + ESP32, tapi CSV yang dipakai di eksperimen hanya punya 1 device_id |
| ML integration dengan 3D viewer | 🔴 `predict.py` fitur tidak match notebook; tidak ada test bahwa prediction muncul di UI |
| Evaluation: prediksi vs aktual per-ruangan | 🔴 Tidak ada metric |
| Physics-based simulation | 🔴 Tidak ada thermal/HVAC solver |
| Reproducible deployment (npm install + python train) | 🟡 Sintaks `npm install` ada tapi `train_from_azure.py` butuh Azure live |

**Verdict:** Modul ini **prototype UI 3D yang menarik untuk demo, tapi belum cukup untuk diklaim sebagai "Digital Twin Web-3D" di paper Q2-Q3**. Untuk defensible di reviewer:

- Minimal: tambahkan metric "predicted vs measured" di setidaknya 1 ruangan, dengan time-series.
- Ideal: thermal RC-model atau HVAC model yang menghitung suhu/occupancy effect, sehingga 3D viewer benar-benar kembaran digital bukan cuma visualisasi.

---

## 5. CHECKLIST ITEM MERAH/ORANYE LAMA

| # | Item | Status lama | Status terkini (2026-07-02) | Bukti |
|---|---|---|---|---|
| 1 | **Baseline arsitektur (cloud-only vs edge-only vs hybrid)** | ❌ belum ada | ❌ **masih belum ada**. Yang ada di notebook: histogram "edge-only" vs "cloud-routed" — itu routing decision per-record, bukan perbandingan tiga arsitektur. Tidak ada script `compare_architectures.py` atau sel notebook yang fit Ridge di cloud dengan batch lalu compare latency/throughput/R² vs streaming. | `edge_cloud_streaming.ipynb` cell plotting — `df_edge` = record yang TIDAK di-route, bukan "edge-only architecture" |
| 2 | **final_drift_ablation.py** | ❓ | ✅ **SUDAH di-commit**. `final_drift_ablation_test.py` (29 KB) + `final_drift_ablation_results.json` (87 baris) + `final_drift_ablation_data.pkl` (308 MB LFS) + 3 .joblib. Commit `35751dc` (1 Juli). | `git log -- final_drift_ablation_test.py` |
| 3 | **Justifikasi klaim "multimodal"** | ❓ eksplisit | 🟡 **setengah jadi**. `CLAUDE.md` punya tabel "Klarifikasi Single-Column DeviceID di CSV" yang menjelaskan sumber multi-modal di kode ESP32+RPi+YOLO+Azure. Tapi kertas belum ditulis, dan CSV yang dipakai di eksperimen hanya 1 device_id (gateway). Belum ada paper section "3.2 Data Fusion Architecture" yang menjelaskan bagaimana CSV 2M record merepresentasikan fusion. | `CLAUDE.md` L20-37 |
| 4 | **Disclosure simulasi (asumsi cloud latency, data sintetis)** | ❓ | 🔴 **BELUM konsisten**. README L25-26 menampilkan "Edge: 1.49 ms/record (median), SLA <2ms" — ini adalah `SUM_EDGE_LAT_MEDIAN = 1.3 ms` hardcoded, bukan benchmark runtime. README L31 menampilkan "Cloud: 196 ms" — angka tidak ditemukan asalnya di source (yang ada 275 ms hardcoded = 45+150+80). Tidak ada kalimat eksplisit "Cloud latency di angka ini adalah asumsi untuk skenario akademik, bukan hasil benchmark round-trip." | `edge_cloud_streaming.ipynb` L33-36 vs README L31 |
| 5 | **Penjelasan dua R² (batch vs streaming)** | ❓ | 🟡 **tersirat**. README L61-69 punya tabel perbandingan dua hasil. CLAUDE.md punya bagian "Temuan Penentu — Drift Akumulatif" yang menjelaskan. TAPI: tidak eksplisit disebut bahwa drift_signal adalah artefak sintetik yang di-inject, bukan phenomena yang terukur di real-world deployment. R² 0.18 vs 0.995 dikontraskan sebagai "drift hurts streaming", padahal kedua R² dihitung pada y yang sudah terkontaminasi drift_signal yang sengaja di-inject. | CLAUDE.md L107-115 (definitive finding section) |

---

## 6. KONSISTENSI ANTAR NOTEBOOK

### `energy_prediction_models.ipynb` vs `edge_cloud_streaming.ipynb`

| Aspek | energy_prediction_models.ipynb | edge_cloud_streaming.ipynb |
|---|---|---|
| **Source y (target)** | `df['daya']` dari CSV (≈ V×I+0.5W) | `V*I + noise(N(0,0.15)) + drift_signal` (di-inject) |
| **Source V×I** | dari CSV nyata | deterministic V*I + 5% random noise |
| **Fitur model** | 18 sama: 10 numerik (suhu, hum, V, I, org, V*I, T*hum, hour, dow, day) + 5 one-hot + 3 rolling shift(1) | 18 sama persis, termasuk `tegangan_arus` |
| **Train-test split** | Chronological 80/20 pada CSV | Streaming sequential: warmup 50K, retrain every 5 chunks |
| **Scaler** | StandardScaler fit on train | StandardScaler refit setiap retrain |
| **Bug fix history** | sudah pakai shift(1) | bug #1 (#2 r2_buf_train=0) dan bug #2 (r2_window_recent = mean(daya)) sudah diperbaiki (`fix_ridge_bugs_verifikasi.txt`) |
| **Hasil R² headlining** | RF=0.9952, LR=0.9649 | one-shot ridge R²~-1.7 chunk1, retrained R²~0.27-0.35 |

### Apakah ada dependency tak terdokumentasi?

**TIDAK ada dependency langsung antar notebook.** Keduanya load `sensor_data.csv` secara independen. Ini baik untuk reproducibility, tapi juga berarti:

- `energy_prediction_models.ipynb` tidak menggunakan `streaming_results_z25.pkl` (output streaming).
- Notebook energy tidak menggunakan model `.pkl` apapun dari `dashboard_digitaltwin/ml_models/models/`.
- Dashboard ML models dilatih oleh script terpisah (`dashboard_digitaltwin/ml_models/train_model.py`) yang tidak ada di notebook jurnal.

**Rekomendasi:** dokumentasikan secara eksplisit di notebook bahwa "energy prediction models dan streaming models adalah dua eksperimen independen, dengan headlining R² yang berbeda secara desain — yang satu batch train-test, yang satu streaming online dengan drift."

---

## 7. DAFTAR KEPUTUSAN YANG HARUS ANDA AMBIL SEBELUM PENULISAN PAPER

> Setiap keputusan di bawah akan mengunci angka/framing di paper. Saya merekomendasikan salah satu opsi (REKOMENDASI) tetapi Anda yang pilih.

### D1. Angka R² untuk klaim "akurasi prediksi energi" — (PILIH SALAH SATU)

- **Opsi 1 (REKOMENDASI):** Pakai `energy_model_results_fixed.json` R²=0.9952 (RF) sebagai akurasi prediksi energi, dengan **disclaimer eksplisit** bahwa target adalah daya sesaat (V×I) sehingga ini lebih merupakan "power state estimation" daripada "energy prediction". (Opsi A dari Bagian 3.3.)
- **Opsi 2:** Jalankan ulang eksperimen forecasting (Opsi B dari Bagian 3.3) — butuh ~1 hari untuk re-train, apakah layak committing ke paper tanpa forecasting sebagai novelty.
- **Opsi 3:** Eksklusi klaim R²=0.9952 dari paper; fokus ke drift ablation + edge-cloud sebagai kontribusi utama.

### D2. Angka R² untuk klaim "streaming robustness" — (PILIH SALAH SATU)

- **Opsi 1 (REKOMENDASI):** Pakai `R² retrained Ridge avg ~0.27-0.35` dari `stream_full_audit.py` (z=2.5), dengan klarifikasi bahwa ini static R² pada test region setelah drif akumulatif. Kontraskan dengan R²=0.99 batch untuk menunjukkan gap.
- **Opsi 2:** Pakai "0.18 rolling" / "0.348 static clean" yang ada di `decisive_r2_test_hasil_mentah.txt` — lebih konservatif dari opsi 1.
- **Opsi 3:** Tambahkan drift compensation layer (rekomendasi utama CLAUDE.md L150-160) lalu laporkan R² setelah kompensasi.

### D3. Apakah "RF streaming 0.9427" boleh disebut di paper — (WAJIB JELAS)

- **Opsi 1 (REKOMENDASI):** JANGAN sebut angka 0.9427. Ganti dengan "RF R²_test=0.9629 pada FAR subset chronological split (90.4% clean records, n=1.66M)" dan jelaskan bahwa ini adalah eksperimen terpisah (bukan streaming). Sebut sebagai "ablation study on clean subset."
- **Opsi 2:** Angkat angka 0.9427 dengan footnote eksplisit "non-streaming batch ablation, bukan hasil pipeline streaming sungguhan."

### D4. Apakah Digital Twin di paper sebagai "prototype" atau "validated platform"

- **Opsi 1 (REKOMENDASI):** Frame sebagai "implemented reference architecture" — kode ada, deployment feasible, evaluation terbatas. Jangan klaim "validated Digital Twin" kecuali Anda menambahkan metric.
- **Opsi 2:** Skip klaim Digital Twin dari kontribusi utama. Fokus paper ke Edge-Cloud + Drift Ablation sebagai 2 kontribusi, dan Digital Twin di bagian implementation discussion saja.

### D5. Apa status klaim "multimodal" jika CSV hanya 1 device_id

- **Opsi 1 (REKENDASI):** Tulis eksplisit di section 3.x (Data): "CSV 2M record adalah data teragregasi dari gateway yang menerima payload dari multiple modalities (ESP32 numerik + RPi camera + RPi gateway health). Pembedaan modality ada di source code ESP32+RPi, dengan 2M record merepresentasikan observasi post-fusion. Validasi arsitektur multi-modal ada di sub-modul `dashboard_digitaltwin/sensor_iot/` yang menunjukkan data flow ESP32→IoT Hub + RPi→MQTT→Azure."
- **Opsi 2:** Jalankan ulang eksperimen dengan data source langsung dari Azure Storage (bukan CSV gateway-aggregated) yang punya device_id berbeda per source. Butuh waktu lama.

### D6. Latency claim framing — (WAJIB JELAS)

- **Opsi 1 (REKOMENDASI):** Ganti semua angka latency dengan disclaimer: "Nilai latency pada section ini adalah asumsi skenario akademik berdasarkan dekomposisi protokol (network/processing/sync). Bukan hasil benchmark round-trip. Validasi empiris latency end-to-end adalah future work."
- **Opsi 2:** Jalankan benchmark latency aktual (curl berulang ke Azure Function yang sudah live) — butuh Azure live + waktu.

---

## 8. APPENDIX — INVENTARIS FILE KUNCI

| File | Baris / Ukuran | Git commit terakhir | Reproducible? | Status |
|---|---|---|---|---|
| `README.md` | 71 lines | 517201a (30 Juni) | n/a | terkini, klaim eksplisit "V×I bukan deterministik", acknowledgment of drift |
| `CLAUDE.md` | 160 lines | 664886b (30 Juni) | n/a | dokumentasi auto-memory, bukan paper |
| `edge_cloud_streaming.ipynb` | 58.5 KB | 517201a | ✅ script + hasil | aktif |
| `energy_prediction_models.ipynb` | 16.7 KB | 517201a | ✅ via `eval_energy_fixed.py` | aktif |
| `eval_energy_fixed.py` | 6.3 KB | 277b15c | ✅ runs in ~10 min | aktif, hasil di `energy_model_results_fixed.json` |
| `stream_full_audit.py` | 14 KB | 21103a8 | ✅ runs in ~30 min | aktif, hasil di `streaming_results_z25.pkl` (LFS) |
| `robustness_audit.py` | 5.5 KB | 21103a8 | ✅ | lama (v1, tidak dipakai) |
| `robustness_audit_v2.py` | 11.5 KB | 14cf4ab | ✅ | aktif, hasil di `robustness_audit_v2.json` |
| `final_drift_ablation_test.py` | 30 KB | 35751dc (1 Juli) | ✅ runs in ~10-15 min | aktif, hasil di `final_drift_ablation_results.json` |
| `final_drift_ablation_results.json` | 2.5 KB | 35751dc | n/a | reference utama ablation |
| `final_drift_ablation_data.pkl` | 308 MB LFS | c30cf06 | n/a | data pickle untuk replikasi |
| `energy_model_results_fixed.json` | 801 B | 277b15c | n/a | reference utama batch R² |
| `streaming_results_z25.pkl` | 295 MB LFS | c30cf06 | n/a | output stream_full_audit.py |
| `decisive_r2_test_hasil_mentah.txt` | 4.8 KB | TIDAK di git | ❌ (raw, tidak reproducible) | historis, jangan dipakai |
| `ridge_streaming_diagnostic_hasil_mentah.txt` | 22.6 KB | 382fce7 (29 Juni) | ⚠️ (output diagnostic) | historis, kontekstual |
| `fix_ridge_bugs_verifikasi.txt` | 4.4 KB | 382fce7 | ⚠️ | historis, dokumentasi bug fix |
| `uji1_dan_uji2_hasil_mentah.txt` | 5.5 KB | 382fce7 | ⚠️ | historis, dokumentasi robustness |
| `audit_complete.py` | 45.9 KB | 74b1247 | ⚠️ (raw audit sebelum fix) | historis |
| `audit_output.txt` | 18 KB | TIDAK di git | ❌ | historis, jangan dipakai |
| `anomaly_indices.pkl` | 18 KB | TIDAK di git (commit?) | ❌ | indeks untuk replay, tapi tidak di-commit |

---

## 9. KESIMPULAN AUDIT

Repo ini BUKAN kumpulan angka yang saling kontradiktif tanpa penjelasan. Justru sebaliknya: ada satu set angka yang konsisten dan reproducible (`energy_model_results_fixed.json`, `final_drift_ablation_results.json`, `robustness_audit_v2.json`), dengan dokumentasi fix bug (#1, #2) yang baik. Masalah utama bukan pada angka, tapi pada **framing**:

1. V×I leakage perlu ditangani secara terbuka, bukan disembunyikan di balik disclaimer sebaris. Ini menentukan apakah reviewer menganggap "Building Energy Prediction" sungguhan atau tidak.
2. Angka 0.9427 yang Anda lihat di assessment lama bukan streaming; pakai ablation number (0.9629) dengan framing eksplisit.
3. Latency adalah asumsi skenario akademik, bukan benchmark — perlu disclosure eksplisit.
4. Modul Digital Twin perlu tambahan minimal 1 metric evaluasi prediksi-vs-terukur jika diklaim sebagai kontribusi fungsional.

Setelah 6 keputusan di Bagian 7 Anda ambil, baru bisa mulai writing.
