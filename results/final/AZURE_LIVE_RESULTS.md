# Pengukuran Azure live berbasis replay

Artefak ini mendokumentasikan pengukuran aktual jalur public cloud Azure yang
digunakan untuk melengkapi baseline emulasi pada `RESULTS.md`. Pengukuran tidak
dimaksudkan sebagai pengambilan sensor lapangan baru.

## Konfigurasi pengukuran

- Endpoint: `https://func-digitaltwin-2026.azurewebsites.net/api/sensor/save`
- Resource: Azure Functions `func-digitaltwin-2026` → Azure Table Storage
  `stordigitaltwin2026v2`, Southeast Asia.
- Input: trace XLSX historis `Data/sensor_data_export_2026-05-17_to_2026-05-23.xlsx`;
  SHA-256 `dd8b5028eda7bca0265da4ada881e1ed1f1ec84afb6b6f0a33cd82f9984f4d29`;
  92.160 baris.
- Sampling: 5 warmup dan 200 request pengukuran, dipilih merata dari trace,
  concurrency 1 dengan koneksi HTTPS persistent.
- Isolasi: payload `benchmark.mode=historical_replay` disimpan pada
  `BenchmarkTelemetry`, bukan `SensorTelemetry`.
- Provenance: setiap payload membawa `runId`, `messageId`, `sourceRowId`,
  `sourceTimestamp`, `replaySentAt`, dan penanda bahwa sensor fisik tidak live.

## Hasil

| Metrik | Hasil |
|---|---:|
| Request pengukuran berhasil | 200/200 (100%) |
| Error | 0 (0%) |
| Kepatuhan deadline 3.500 ms | 200/200 (100%) |
| End-to-end P50 / P95 / P99 | 46,6 / 56,9 / 99,7 ms |
| Function server processing P50 / P95 / P99 | 8,0 / 14,0 / 19,0 ms |
| Table Storage write P50 / P95 / P99 | 7,7 / 13,7 / 18,8 ms |
| Overhead client/network estimasi P50 / P95 / P99 | 38,2 / 45,5 / 62,3 ms |
| Throughput sekuensial | 19,70 request/detik |
| Entity terkonfirmasi pada `BenchmarkTelemetry` | 205 |

Sumber angka: [`azure_live_metrics.json`](azure_live_metrics.json) dan data
per-request [`azure_live_requests.csv`](azure_live_requests.csv). Grafik
ringkas tersedia di
[`06_azure_live_performance.png`](figures/06_azure_live_performance.png).

## Batas interpretasi

Angka di atas adalah pengukuran aktual jalur HTTPS publik hingga penulisan
Azure Table Storage dikonfirmasi. Payloadnya merupakan replay terkontrol dari
rekaman sensor fisik yang diarsipkan; ESP32/Raspberry Pi tidak mengirimkan
stream baru selama benchmark. IoT Hub, jalur kamera live, dan render browser
tidak termasuk. Kolom sumber hanya memiliki label gateway
`RASPBERRY_PI_GATEWAY_001`, bukan `source_node_id` per baris. Hasil ini
mendukung klaim kinerja infrastruktur pada workload replay, bukan klaim
akurasi/presisi estimator atau validasi lapangan live.
