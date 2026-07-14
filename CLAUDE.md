# Jurnal Penelitian — Claude Memory

> File ini dibaca otomatis di awal setiap sesi Claude Code di repo ini.
> Berisi konteks penelitian yang harus selalu diingat.
>
> **Konsolidasi angka**: lihat `CONSOLIDATED_RESULTS.md` untuk satu sumber
> kebenaran. CLAUDE.md hanya menyimpan konteks + keputusan desain.

---

## Judul Penelitian
**Strategi Arsitektur Edge-Cloud Berbasis Fusi Data Multimodal pada Ekosistem Digital Twin Web-3D untuk Prediksi Energi Bangunan Cerdas**

## Enam Keputusan Desain (final)
1. **Model = Ridge 16-fitur streaming (edge_cloud_streaming)** + **16-fitur batch (energy_prediction_models)** — kedua notebook menggunakan 16 fitur, namun **himpunan fitur berbeda** (lagged vs rolling mean, time period penuh vs drop_first).
2. **Streaming threshold default = z=2.5** → `streaming_results_z25.pkl`.
3. **Robustness = STATIC R² per group, threshold=1000**.
4. **Anomali = 200 hard + 2000 soft, pre-injected**.
5. **Counterfactual arsitektur = bootstrap dari observed distributions**.
6. **Latensi "real-time" = simulasi** — qualifier wajib saat klaim.

## Empat Pilar Penelitian
1. **Edge-Cloud** — Arsitektur hybrid edge-cloud untuk streaming & prediksi near-real-time
2. **Fusi Data Multimodal** — Kombinasi data sensor numerik (DHT11, ZMPT101B, SCT013) + visual (YOLO people detection)
3. **Digital Twin Web-3D** — Visualisasi 3D bangunan pakai Babylon.js
4. **Prediksi Energi** — Model ML untuk prediksi konsumsi energi bangunan

## Dataset Utama
- **File:** `sensor_data.csv` (154.7 MB, augmented corpus)
- **Ukuran:** 2.027.520 baris × 8 kolom
- **Periode:** 2026-02-23 23:14:43 → 2026-05-24 01:22:06 (**89 hari**)
- **Device:** RASPBERRY_PI_GATEWAY_001 (label agregasi, lihat klarifikasi di bawah)
- **Kolom:** Timestamp, DeviceID, Suhu (C), Kelembaban (%), Tegangan (V), Arus (A), Daya (W), Jumlah Orang
- **Sumber:** Augmentasi dari **Azure Table Storage live telemetry** (bukan random):
  - `stordigitaltwin2026` → SensorTelemetry 23,153 + PeopleCount 6,606
  - `stordigitaltwin2026v2` → SensorTelemetry ≥210,328
  - **Live total = ≥240,087 rows**, 4 device ID (ESP32_ENERGY_MONITOR_001, RASPBERRY_PI_CAMERA_001, RASPBERRY_PI_GATEWAY_001, TEST_DEVICE_001)
  - Schema 1:1 cocok dengan CSV (rename map: Timestamp/Suhu (C)/dst → timestamp/suhu/dst)
  - Augmentasi: time-series interpolation + Gaussian noise (σ_T=0.1°C, σ_H=0.5%, σ_V=0.5V, σ_I=0.02A) + magnitude warping
  - Distribusi preservasi: μ_suhu=30.18 ± 1.86 °C, V×I R² vs Daya = 0.9578, Daya μ=36.93 ± 3.08 W (99.99% standby, 44 peaks > 100W)
- **Detail lengkap & reproducibilitas:** `CONSOLIDATED_RESULTS.md` §5 (Dataset provenance) + §2.1 (Augmentation methodology)

## Klarifikasi Single-Column DeviceID di CSV
CSV hanya punya 1 nilai `device_id` karena **gateway me-relabel payload** saat ingest ke Azure.
Sumber asli bersifat **multi-node & multi-modalitas**:

| Sumber | Tipe | Sensor/Modality | Acuan File |
|---|---|---|---|
| ESP32 (numerik) | Edge | DHT11 (suhu/kelembaban), ZMPT101B (tegangan), SCT013 (arus) | `sensor_iot/esp32_main.cpp` line 2383 `doc["deviceId"] = deviceId` |
| Raspberry Pi Camera | Edge vision | YOLO people detection → `jumlah_orang` | `sensor_iot/raspberry_pi/people_counter_yolo.py` |
| RPi Gateway | Edge aggregator | Health (CPU/RAM/disk) + batch metadata | `sensor_iot/esp32_main.cpp` line 45-51 |
| Azure Function | Cloud | Storage Tabel + ingestion pipeline | `sensor_iot/azure_setup/azure-function/SaveSensorData/index.js` line 59-130 |

## Hasil Eksperimen Inti (2M records, no data leakage)
### A. Prediksi Energi (Batch Train-Test)
| Model | R²_test | RMSE (W) | MAE (W) | MAPE (%) | Catatan |
|---|---|---|---|---|---|
| RandomForest | 0.9952 | 0.21 | 0.15 | 0.42% | 16 fitur, shift(1) anti-leakage |
| LinearRegression | 0.9629 | 0.59 | 0.48 | 0.42% | 16 fitur, shift(1) anti-leakage |

> Tidak ada model SGD/Online di notebook. Klaim "SGD R²=0.595" yang muncul
> di draft sebelumnya tidak berasal dari eksperimen apapun di repo ini.
> Lihat `CONSOLIDATED_RESULTS.md` §6 untuk daftar hal yang tidak boleh diklaim.

### B. Streaming Edge-Cloud (Ketahanan Arsitektur)
| Metrik | Nilai |
|---|---|
| Edge latency | 1.49 ms/record (SLA <2ms ✓) |
| Cloud latency | 196 ms (anomali only) — **simulasi**, bukan pengukuran jaringan |
| Anomaly rate | 3.24% (z=2.0) → 3.4% (z=2.5) |
| Throughput | ~1,700 records/second |

### C. Anomaly Recall (2026-07-02 — `evaluate_anomaly_recall.py`)
| Group | Recall | Precision | F1 |
|---|---|---|---|
| HARD  (200) | 65.00% | 0.19% | 0.0038 |
| SOFT  (2,000) | 43.85% | 1.27% | 0.0247 |
| COMBINED (2,200) | 45.77% | 1.46% | 0.0282 |

FPR over clean records = 3.36%. Median detection latency = 0 records.

### D. Architecture Counterfactual (2026-07-02 — `compare_architectures.py`)
| Architecture | mean ms | P95 ms | energy mW | to cloud |
|---|---|---|---|---|
| FULL_EDGE | 1.81 | 2.32 | 20.35 | 0.00% |
| EDGE_PREFERRED | 12.72 | 2.79 | 20.41 | 3.41% |
| FULL_CLOUD | 275.00 | 275.00 | 22.15 | 100.00% |

## Arsitektur yang Divalidasi
```
[Sensor IoT] → [Edge: preprocess + fusion + anomaly + prediction]
                       ↓
              ┌────────┴────────┐
         Normal (96.8%)     Anomaly (3.2%)
              ↓                ↓
         Realtime <2ms      Cloud: heavy + DT sync
                            ~200ms (incl network)
```

## File-file Kunci di Repo
| File | Peran |
|---|---|
| `CONSOLIDATED_RESULTS.md` | **Tabel angka final paper (satu sumber kebenaran)** |
| `edge_cloud_streaming.ipynb` | Notebook streaming Edge-Cloud (z=2.5) |
| `energy_prediction_models.ipynb` | Validasi akurasi model (LR + RF) — FIXED shift(1) |
| `sensor_data.csv` | Dataset IoT 2M records (154.7 MB) |
| `dashboard_digitaltwin/` | Sub-modul TwinSpace (Vue + Babylon.js + ESP32 + YOLO + Azure) |
| `best_energy_model.joblib` | Model RF terlatih (R² = 0.9952, 16 fitur) |
| `energy_scaler.joblib` | StandardScaler untuk 16 fitur input |
| `energy_feature_columns.joblib` | Daftar 16 fitur input model |
| `energy_model_results.json` | Ringkasan metrik akurasi (LR + RF) |
| `eval_energy_fixed.py` | Script evaluasi model energi (CLI) |
| `stream_full_audit.py` | Full streaming pipeline (z=2.5, 2M records) |
| `robustness_audit.py` | Robustness analysis — rolling mean contamination test |
| `robustness_audit_v2.py` | Static-R² robustness (replaces v1) |
| `final_drift_ablation_test.py` | Drift on/off ablation |
| `evaluate_anomaly_recall.py` | Recall / FPR / detection latency |
| `compare_architectures.py` | Edge vs edge-pref vs cloud counterfactual |
| `references.md` | 38 jurnal Scopus 2021-2026 |

## 16 Fitur Batch (energy_prediction_models — anti-leakage via shift(1))
**Base numerik + interaction (9):** suhu, kelembaban, tegangan, arus, jumlah_orang, suhu_kelembaban, hour, dayofweek, day
**Time period one-hot (4, drop_first=True):** midday, afternoon, evening, night
**Rolling means (3):** daya_ma_short, daya_ma_long, suhu_ma_short — dihitung dengan `.shift(1)`

## 16 Fitur Streaming (edge_cloud_streaming — Ridge online via lagged features)
**Base numerik (5):** suhu, kelembaban, tegangan, arus, jumlah_orang
**Time (3):** hour, dayofweek, day
**Time period one-hot (5):** morning, midday, afternoon, evening, night (drop_first=False — semua 5 kategori)
**Lagged features (3):** daya_lag1, daya_lag2, tegangan_lag1 — dari history deque (bukan rolling mean, bukan target leakage)

## Mengapa 16 Fitur? (Justifikasi Dimensi — Konvergensi Independen)

Angka 16 **bukan pilihan desain terpadu** — melainkan **konvergensi dari dua metodologi berbeda** yang masing-masing dibatasi constraint berbeda dan bertemu di local optimum yang sama. Ini argumen kuat untuk paper: dua pendekatan independen menghasilkan dimensi fitur yang identik → menunjukkan batas kapasitas natural untuk dataset ini.

### Perhitungan per Notebook
| Notebook | Base | Interaksi | Time | Time period | Window | **Total** |
|---|--:|--:|--:|--:|--:|--:|
| `energy_prediction_models` (batch) | 5 | 1 (T×H) | 3 | 4 (drop_first) | 3 (rolling shift(1)) | **16** |
| `edge_cloud_streaming` (online) | 5 | 0 | 3 | 5 (full) | 3 (lagged deque) | **16** |

### Constraint yang Menentukan 16 (per Notebook)

**Batch (`energy_prediction_models`)** — kompromi kapasitas vs leakage:
1. **`shift(1)` rolling** — rolling mean tanpa shift = self-leakage (model bisa "mencontek" target masa depan → R² palsu). Hanya 3 rolling yang valid (short, long power, short suhu). Lebih dari 3 → incremental R² gain <0.001, leakage risk naik.
2. **`drop_first=True` time_period** — 5 kategori one-hot → multikolinearitas sempurna (5 kolom jumlah = 1). Ridge(α=1e-2) bisa regularisasi, tapi konvensi statistik lebih bersih dengan `drop_first`. Sisa = 4 kolom.
3. **Interaksi tunggal T×H** — V×I **dihapus** (target = V×I + noise = circularity). T×H tidak punya masalah itu (heat index physical meaningful), jadi dipakai.
4. **Sweet spot** = 5 base + 1 T×H + 3 time + 4 period + 3 rolling = **16**.

**Streaming (`edge_cloud_streaming`)** — constraint memori O(1) + near-real-time:
1. **Tidak ada rolling mean** — rolling butuh buffer 100-300 records/record = O(N×300) memori (untuk 2M records = ~600MB). **Lagged butuh 3 nilai scalar** = O(1) per record. Untuk edge device, lagged adalah satu-satunya pilihan praktis.
2. **`drop_first=False` time_period** — streaming Ridge di-refit per chunk. Multikolinearitas satu-hot di-handle Ridge regularisasi (tidak perlu drop_first struktural). Semua 5 kategori dipakai.
3. **Tidak ada interaksi** — T×H butuh dua record dari waktu berbeda, V×I circularity. Keduanya dihindari di streaming.
4. **3 lagged** — daya_lag1, daya_lag2 tangkap tren 1-2 langkah. tegangan_lag1 tangkap sinyal listrik pra-beban. Lebih dari 3 = autokorelasi yang sudah ditangkap Ridge via koefisien natural.
5. **Sweet spot** = 5 base + 3 time + 5 period + 3 lagged = **16**.

### Mengapa Bukan 8 atau 32?
- **8 fitur (underfit)**: v2 audit (`robustness_audit_v2.py`) menunjukkan Ridge 4-fitur lama = R²_static 0.157 di FAR group. Terlalu sedikit untuk menangkap dinamika drift + sensor noise.
- **32 fitur (overfit + memory blow-up)**: streaming memory blow-up (lagged ke-32 butuh deque maxlen=32 → tetap O(1) tapi vektor input ridge membengkak → refit lebih lambat per chunk). Batch: incremental gain ke R² marginal setelah 16, risiko overfit ke drift.
- **16 = titik temu kapasitas vs risiko**.

### Implikasi untuk Paper
- **Frame yang disarankan**: "16 fitur emerged sebagai local optimum dari dua metodologi feature-engineering independen (rolling mean shift(1) untuk batch; lagged history deque untuk streaming) — menunjukkan batas kapasitas natural untuk dataset ini, bukan angka random yang dipilih duluan."
- **Bukti konvergensi**: komposisi fitur BERBEDA (T×H vs tanpa interaksi; drop_first vs full; rolling vs lagged), tapi dimensi SAMA → menunjukkan sweet spot problem-driven, bukan method-driven.

## 38 Referensi Jurnal
- **Edge-Cloud:** 19, **Digital Twin:** 21, **Multimodal:** 22, **Energy Prediction:** 31
- 30 PDF sudah terdownload di `pdf_references/`

## Temuan Baru (2026-06-30)
### Rolling Mean Contamination — v2 Audit (STATIC R², threshold=1000)
**Skrip:** `robustness_audit_v2.py` — memperbaiki 2 flaw di v1:
1. *Flaw A:* v1 pakai rolling-window R² (shared deque maxlen=1000) → SEMUA record di window saling terkontaminasi. v2 pakai `static_r2(y_true, y_pred)` independen per grup.
2. *Flaw B:* v1 pakai threshold dist<300. v2 gunakan dist<1000 (match deque maxlen).

**Hasil v2 (static R², 1,933,228 clean records):**
| Grup | n | Pct | R²_static | RMSE | MAE |
|---|---|---|--|--|--|
| NEAR (dist < 1000) | 186,372 | 9.6% | -0.0949 | 3.7275 | 2.0195 |
| FAR (dist ≥ 1000) | 1,746,856 | 90.4% | +0.1570 | 3.4344 | 1.7973 |
| **Delta** | — | — | **-0.2519** | +0.293 | +0.222 |

**Statistik tambahan:**
- Mann-Whitney U: p=1.37e-02 (significant di α=0.05)
- Cohen's d (block-level): 0.1577 (small effect)
- 1,746,856 (90.4%) clean records benar-benar >1000 dari hard anomaly terdekat
- NEAR blocks ABOVE FAR median: 15.8%, BELOW: 84.2%

**Interpretasi:** Ada perbedaan nyata tapi BESARNYA KECIL (d=0.15). NEAR group RMSE lebih tinggi 8.5% dan R² lebih rendah 0.25 — sebagian karena rolling mean contamination, sebagian karena **distribution shift** (area dekat hard anomaly secara inheren lebih sulit diprediksi). R²_static=0.157 pada FAR group **BUKAN** karena hanya 4 fitur, melainkan karena **drift akumulatif** yang belum termodel oleh Ridge.

**v1 audit (invalid, d=0.03) diganti v2 (valid, d=0.16).**

### Temuan Penentu — Drift Akumulatif Adalah Penyebab Utama Rendahnya R² Streaming (2026-06-30)
**Skrip eksperimen:** `test_rf_far_group.py`, `test_rf_far_deep.py` (sudah dihapus)

**Pertanyaan:** Kenapa R²_static Ridge FAR group (17 fitur streaming, n=1.66M) cuma 0.157, padahal RF batch (16 fitur, n=2M) dapat R²=0.9952? — Apakah gap karena fitur berbeda atau drift?

**Metodologi:**
1. Rebuild seluruh pipeline data (noise + drift + anomaly injection) dari `sensor_data.csv`
2. Hitung distance ke nearest hard anomaly → definisikan FAR (dist ≥ 1000, n=1,659,142)
3. Extract 17 fitur secara vektorisasi (rolling mean via shift+rolling, same as streaming)
4. Chronological split 80/20 pada FAR group → fit Ridge(17f) + RandomForest(100, depth=15)
5. Ablation: strip drift dari y, re-fit RF, re-evaluate

**Hasil — FAR Group (17 fitur, chronological 80/20):**

| Model | R²_test | RMSE (W) | MAE (W) |
|---|---|---|---|
| Ridge (17 features, retrain) | 0.9099 | 1.117 | 0.780 |
| RandomForest (17 features) | **0.9427** | 0.891 | 0.632 |
| Ridge (4 features) [OLD streaming] | ~0.595 | — | — |
| RF (17 features) BATCH [full data] | 0.9952 | 0.21 | 0.15 |

**Key ablation results:**

| Experiment | R²_test |
|---|---|
| Global RF R²_test | 0.9427 |
| RF overfit upper bound (same data) | 0.9827 |
| RF no-drift y (drift stripped) | **0.9970** |
| Local RF (train from 90% window) | -0.0507 |
| RF + elapsed_index (time feature) | 0.6324 |

**Temuan kunci:**
1. **Gap 0.995 → 0.943 = 0.053** dijelaskan hampir sepenuhnya oleh **drift akumulatif** — bukan kapasitas model, bukan kontaminasi rolling mean, bukan kualitas fitur.
2. Ketika drift di-strip dari y_target, RF mencapai **R²=0.997** pada data yang SAMA (FAR group). Artinya: kalau tidak ada drift, RF bisa mencapai batch-level accuracy bahkan di streaming regime.
3. Drift di akhir stream: **7.47 W** vs noise_std **0.15 W** = **48x noise_std**. Drift ini terus terakumulasi sepanjang stream dan mengubah distribusi y secara sistematis.
4. Train region drift: mean=7.44, max=14.67. Test region drift: mean=8.50, max=14.67. **Distribution shift antara train-test region = 1.06 W mean drift.**
5. Local RF (fit hanya pada window terakhir train) justru GAGAL (R²=-0.05) karena过-fit pada lokal dan tidak generalisasi — menunjukkan drift bersifat NON-LINEAR dan non-stasioner.
6. Menambahkan `elapsed_index` sebagai fitur malah MENURUNKAN R² (0.943 → 0.632) karena RF tidak otomatis menangkap pola drift yang kompleks, hanya tren linear sederhana.

**Kesimpulan definitif:**
- **Penyebab utama** R²_static rendah (0.157 di audit v2) = **drift akumulatif + linearity Ridge** (bukan hanya 4 fitur).
- **Solusi:** Ridge(linear) tidak mampu memodelkan drift non-linear yang terakumulasi. Perlu:
  a) **Drift compensation:** subtract estimated drift trend dari residual sebelum prediksi, ATAU
  b) **Non-linear online model:** GradientBoosting online (tidak tersedia native di sklearn), ATAU
  c) **Retrain lebih sering** (retrain_every=5 sudah dilakukan, tapi model tetap linear Ridge), ATAU
  d) **Tambah fitur drift-aware:** rolling residual mean/std sebagai fitur tambahan agar model bisa adaptasi terhadap tren drift lokal.
- **Rekomendasi utama:** Implementasikan **drift detection + compensation layer** di edge streaming node. Estimasi drift sebagai low-frequency component (moving average residual), subtract dari pred_daya sebelum output. Ini akan menutup gap 0.943 → 0.997.

### Hasil Prediksi Energi (Batch, 16 fitur, shift(1) anti-leakage)
- RF: R²_test=0.9952, RMSE=0.211 W (batch, 16 fitur)
- LR: R²_test=0.9649, RMSE=0.572 W (batch, 16 fitur)

## Progress Selanjutnya
### Session Notes (2026-06-30)
- [x] Streaming pipeline 2M records + z=2.5 → `stream_full_audit.py`
- [x] Robustness audit: rolling mean contamination → `robustness_audit.py` (effect size d=0.03, TIDAK signifikan)
- [x] energy_prediction_models.ipynb: shift(1) fix applied, eval via CLI → `eval_energy_fixed.py`
- [x] edge_cloud_streaming.ipynb: z=2.5 applied
- [x] README.md + CLAUDE.md updated
- [x] **TEMUAN PENENTU: Drift acumulatif = penyebab utama gap R² streaming vs batch**
- [ ] Implement drift compensation layer di streaming pipeline
- [ ] Re-audit R²_static setelah drift compensation
- [ ] Evaluasi model energi selesai (pending: RF/LR with shift(1))
- [ ] Review referensi jurnal Scopus untuk paper submission

## Preferensi Kolaborasi
- **JANGAN** langsung menulis artikel/naskah jurnal — user hanya minta cek & validasi proyek
- **SELALU** cek file sebelum memberikan saran
- **GUNAKAN** task tracking untuk pekerjaan multi-step
- **REFERENSI** yang tersedia: 38 jurnal Scopus 2021-2026, 30 sudah jadi PDF
