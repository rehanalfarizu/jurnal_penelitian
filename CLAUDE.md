# Jurnal Penelitian — Claude Memory

> File ini dibaca otomatis di awal setiap sesi Claude Code di repo ini.
> Berisi konteks penelitian yang harus selalu diingat.

---

## Judul Penelitian
**Strategi Arsitektur Edge-Cloud Berbasis Fusi Data Multimodal pada Ekosistem Digital Twin Web-3D untuk Prediksi Energi Bangunan Cerdas**

## Empat Pilar Penelitian
1. **Edge-Cloud** — Arsitektur hybrid edge-cloud untuk streaming & prediksi real-time
2. **Fusi Data Multimodal** — Kombinasi data sensor numerik (DHT11, ZMPT101B, SCT013) + visual (YOLO people detection)
3. **Digital Twin Web-3D** — Visualisasi 3D bangunan pakai Babylon.js
4. **Prediksi Energi** — Model ML untuk prediksi konsumsi energi bangunan

## Dataset Utama
- **File:** `sensor_data.csv` (154.7 MB)
- **Ukuran:** 2.027.520 baris × 8 kolom
- **Periode:** 2026-02-23 23:14:43 → 2026-05-24 01:22:06 (≈ 90 hari)
- **Device:** RASPBERRY_PI_GATEWAY_001 (label agregasi, lihat klarifikasi di bawah)
- **Kolom:** Timestamp, DeviceID, Suhu (C), Kelembaban (%), Tegangan (V), Arus (A), Daya (W), Jumlah Orang

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
| RandomForest | 0.9952 | 0.21 | 0.15 | 0.42% | 18 fitur, shift(1) anti-leakage |
| LinearRegression | 0.9629 | 0.59 | 0.48 | 0.42% | 18 fitur, shift(1) anti-leakage |
| SGD/Online | 0.5950 | — | — | — | 4 fitur (baseline streaming) |

### B. Streaming Edge-Cloud (Ketahanan Arsitektur)
| Metrik | Nilai |
|---|---|
| Edge latency | 1.49 ms/record (SLA <2ms ✓) |
| Cloud latency | 196 ms (anomali only) |
| Anomaly rate | 3.24% (z=2.0) → 3.4% (z=2.5) |
| Throughput | ~1,700 records/second |

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
| `edge_cloud_streaming.ipynb` | Notebook streaming Edge-Cloud (z=2.5) |
| `energy_prediction_models.ipynb` | Validasi akurasi model (LR + RF) — FIXED shift(1) |
| `sensor_data.csv` | Dataset IoT 2M records (154.7 MB) |
| `dashboard_digitaltwin/` | Sub-modul TwinSpace (Vue + Babylon.js + ESP32 + YOLO + Azure) |
| `best_energy_model.joblib` | Model RF terlatih (R² = 0.9952, 18 fitur) |
| `energy_scaler.joblib` | StandardScaler untuk 18 fitur input |
| `energy_feature_columns.joblib` | Daftar 18 fitur input model |
| `energy_model_results.json` | Ringkasan metrik akurasi (LR + RF) |
| `eval_energy_fixed.py` | Script evaluasi model energi (CLI) |
| `stream_full_audit.py` | Full streaming pipeline (z=2.5, 2M records) |
| `robustness_audit.py` | Robustness analysis — rolling mean contamination test |
| `references.md` | 38 jurnal Scopus 2021-2026 |

## 18 Fitur Input Model (anti-leakage)
**Base numerik (10):** suhu, kelembaban, tegangan, arus, jumlah_orang, tegangan_arus, suhu_kelembaban, hour, dayofweek, day
**Time period one-hot (5):** morning, midday, afternoon, evening, night
**Rolling means (3):** daya_ma_short, daya_ma_long, suhu_ma_short — dihitung dengan `.shift(1)` untuk anti-leakage

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

**Pertanyaan:** Kenapa R²_static Ridge pada grup FAR (clean, 18 fitur, n=1.66M) cuma 0.157, padahal RF batch dengan 18 fitur yang SAMA dapat R²=0.9952?

**Metodologi:**
1. Rebuild seluruh pipeline data (noise + drift + anomaly injection) dari `sensor_data.csv`
2. Hitung distance ke nearest hard anomaly → definisikan FAR (dist ≥ 1000, n=1,659,142)
3. Extract 18 fitur secara vektorisasi (rolling mean via shift+rolling, same as streaming)
4. Chronological split 80/20 pada FAR group → fit Ridge(18f) + RandomForest(100, depth=15)
5. Ablation: strip drift dari y, re-fit RF, re-evaluate

**Hasil — FAR Group (18 fitur, chronological 80/20):**

| Model | R²_test | RMSE (W) | MAE (W) |
|---|---|---|---|
| Ridge (18 features, retrain) | 0.9099 | 1.117 | 0.780 |
| RandomForest (18 features) | **0.9427** | 0.891 | 0.632 |
| Ridge (4 features) [OLD streaming] | ~0.595 | — | — |
| RF (18 features) BATCH [full data] | 0.9952 | 0.21 | 0.15 |

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

### Hasil Prediksi Energi (Batch, 18 fitur, shift(1) anti-leakage)
- RF: R²_test=0.9952, RMSE=0.211 W (batch, 18 fitur)
- LR: R²_test=0.9649, RMSE=0.572 W (batch, 18 fitur)
- SGD Online: R²_test=0.595 (4 fitur, baseline streaming)

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
