# Hasil eksperimen final terkonfigurasi

Status: **evaluasi berbasis simulasi; bukan validasi lapangan**.

## Cakupan

- Trace kalibrasi: 92,160 baris, satu gateway.
- Workload sintetis: 493,700 baris dan 20 run.
- Workload replay arsitektur: 2,027,520 baris augmented,
  setara 22 replay trace asli.
- Durasi: 24 jam per run.
- Interval: 3.5 detik.
- Train scenario: hot_busy, normal.
- Validation scenario: humid_unstable.
- Test scenario ditahan: cool_low_load, sensor_degraded.

## Pemeriksaan kalibrasi skenario normal

| Variabel | Normalized quantile MAE | Galat zero-rate | Galat ACF lag-1 | Status |
|---|---:|---:|---:|---|
| temperature_c | 0.064 | 0.000 | 0.023 | Lulus |
| humidity_pct | 0.032 | 0.000 | 0.005 | Lulus |
| voltage_v | 0.006 | 0.001 | 0.018 | Lulus |
| current_a | 0.023 | 0.011 | 0.046 | Lulus |
| power_w | 0.011 | 0.001 | 0.002 | Lulus |
| people_count | 0.000 | 0.017 | 0.000 | Lulus |

Status keseluruhan: **Lulus**.
Ambang diagnostik dideklarasikan di `synthetic_validation.json`.

## Estimasi daya pada skenario test tertahan

Angka adalah rata-rata per run dan 95% confidence interval.

| Model | MAE W [95% CI] | RMSE W [95% CI] | R² [95% CI] |
|---|---:|---:|---:|
| Median train | 6.855 [4.074, 9.636] | 7.267 [4.652, 9.882] | -14.822 [-25.354, -4.291] |
| Firmware V×I | 3.154 [2.322, 3.986] | 8.687 [6.598, 10.777] | -13.413 [-17.732, -9.095] |
| Ridge | 1.277 [1.196, 1.359] | 1.748 [1.591, 1.904] | 0.357 [0.124, 0.589] |
| Random Forest | 2.306 [1.600, 3.012] | 2.667 [1.994, 3.339] | -0.844 [-1.901, 0.214] |

Model terpilih: **ridge**, menggunakan kriteria
`lowest validation MAE`. Test metrics tidak digunakan saat seleksi.

Metrik ini hanya mengukur generalisasi antarskenario sintetis. Workbook asli
tidak mempunyai ground truth daya independen.

## Posisi data augmented 2 juta

File augmented **tidak digunakan** untuk training, validation, maupun test
akurasi model. File digunakan sebagai workload replay arsitektur dengan label
`legacy_augmented_replay`.

- Baris tersedia: 2,027,520.
- Sampel benchmark: 5,000 posisi
  yang tersebar merata pada seluruh
  22 blok replay.
- Fungsi: menguji inference, serialisasi, routing, throughput, dan aliran
  telemetry menuju Digital Twin Web-3D.
- Larangan klaim: bukan 2 juta observasi lapangan independen dan bukan bukti
  akurasi estimasi daya.

## Benchmark arsitektur

- Sumber workload: `legacy_augmented_replay`.
- Mesin/runtime: `macOS-15.7-x86_64-i386-64bit`; Python 3.11.9.
- Inference lokal aktual: P50 2.191 ms, P95 6.299 ms, P99 11.009 ms.
- Edge-path aktual: P50 2.220 ms, P95 6.350 ms, P99 11.039 ms.
- Cloud-path terkonfigurasi: P50 48.386 ms, P95 68.037 ms, P99 75.852 ms.
- Hybrid end-to-end terkonfigurasi: P50 2.253 ms, P95 7.817 ms, P99 50.637 ms.
- Routing: 4,886 pesan ke edge dan
  114 pesan anomali/invalid ke cloud
  menggunakan ambang daya legacy 42.6 W.
- Deadline miss: 0 (0.000%) pada deadline 3500.0 ms.
- Profil jaringan adalah emulasi, bukan pengukuran public cloud.
- Browser render latency belum termasuk.

## Visual

- [Kalibrasi distribusi](figures/01_calibration_distribution.png)
- [Contoh estimasi pada test scenario](figures/02_power_timeseries.png)
- [Perbandingan model dan confidence interval](figures/03_model_comparison.png)
- [Karakteristik latency](figures/04_latency_characteristics.png)

## Batas klaim

Hasil dapat digunakan sebagai hasil final untuk studi **simulation-based
evaluation calibrated from a real four-day trace**. Hasil tidak boleh disebut
sebagai akurasi lapangan, pengukuran Raspberry Pi, pengukuran Azure produksi,
atau validasi banyak bangunan.
