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

**Interpretasi:** Ada perbedaan nyata tapi BESARNYA KECIL (d=0.15). NEAR group RMSE lebih tinggi 8.5% dan R�� lebih rendah 0.25 — sebagian karena rolling mean contamination, sebagian karena **distribution shift** (area dekat hard anomaly secara inheren lebih sulit diprediksi). **Low R² (0.16 vs batch 0.99) BUKAN terutama disebabkan contamination**, tapi karena model streaming Ridge hanya punya 4 fitur vs 18 fitur di batch.

**v1 audit (invalid, d=0.03) diganti v2 (valid, d=0.16).**

### Hasil Prediksi Energi (Batch, 18 fitur, shift(1) anti-leakage)
- RF: R²_test=0.9952, RMSE=0.211 W (batch, 18 fitur)
- LR: R²_test=0.9649, RMSE=0.572 W (batch, 18 fitur)
- SGD Online: R²_test=0.595 (4 fitur, baseline streaming)
3. **Satu-satunya solusi:** upgrade ke 18 fitur untuk Ridge online, retrain tiap 250K records.

## Progress Selanjutnya
### Session Notes (2026-06-30)
- [x] Streaming pipeline 2M records + z=2.5 → `stream_full_audit.py`
- [x] Robustness audit: rolling mean contamination → `robustness_audit.py` (effect size d=0.03, TIDAK signifikan)
- [x] energy_prediction_models.ipynb: shift(1) fix applied, eval via CLI → `eval_energy_fixed.py`
- [x] edge_cloud_streaming.ipynb: z=2.5 applied
- [x] README.md + CLAUDE.md updated
- [ ] Evaluasi model energi selesai (pending: RF/LR with shift(1))
- [ ] Review referensi jurnal Scopus untuk paper submission

## Preferensi Kolaborasi
- **JANGAN** langsung menulis artikel/naskah jurnal — user hanya minta cek & validasi proyek
- **SELALU** cek file sebelum memberikan saran
- **GUNAKAN** task tracking untuk pekerjaan multi-step
- **REFERENSI** yang tersedia: 38 jurnal Scopus 2021-2026, 30 sudah jadi PDF
