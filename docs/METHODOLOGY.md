# Metodologi penelitian yang diperbarui

## Posisi penelitian

Judul kerja yang disarankan:

> **Arsitektur Edge-Cloud untuk Estimasi Daya Near Real-Time Bangunan Cerdas
> Terintegrasi Digital Twin Web-3D: Evaluasi Berbasis Data Sintetis
> Terkalibrasi**

Penelitian ini adalah evaluasi berbasis simulasi yang dikalibrasi menggunakan
satu trace sensor nyata. Penelitian **bukan** eksperimen operasional pada banyak
bangunan, bukan validasi public cloud, dan bukan pengukuran perangkat Raspberry
Pi baru. Batas ini harus dinyatakan pada abstrak, metode, hasil, dan kesimpulan.

## Pertanyaan penelitian

1. Seberapa baik estimator mengoreksi galat observasi daya pada skenario
   sintetis terkalibrasi dibandingkan baseline `tegangan × arus`?
2. Berapa latensi komputasi dan throughput inference pada lingkungan uji yang
   disebutkan secara eksplisit?
3. Bagaimana perubahan asumsi jaringan memengaruhi latensi end-to-end
   edge-cloud pada emulasi terkontrol?
4. Dapatkah hasil estimasi dan provenance disajikan konsisten pada Digital Twin
   Web-3D?

## Pemetaan judul terhadap bukti eksperimen

| Unsur judul | Bukti dan sumber data |
|---|---|
| Arsitektur Edge-Cloud | Benchmark inference, serialisasi, routing edge/cloud, dan emulasi jaringan |
| Estimasi daya | Ridge dan baseline diuji pada skenario sintetis dengan `true_power_w` |
| Near real-time | P50/P95/P99, throughput, dan deadline miss terhadap interval 3,5 detik |
| Bangunan cerdas | Variabel lingkungan, kelistrikan, okupansi, serta gangguan sensor terkalibrasi |
| Digital Twin Web-3D | Kontrak telemetry, replay API, provenance, dan dashboard Babylon.js |
| Evaluasi sintetis terkalibrasi | Generator dikalibrasi dari trace asli dan diuji pada skenario/run tertahan |

## Sumber data dan batasannya

Trace asli adalah workbook
`Data/sensor_data_export_2026-05-17_to_2026-05-23.xlsx`, berisi 92.160 baris
dari satu `device_id`. Waktu aktual di dalam file hanya sekitar empat hari.
Firmware lama menghitung daya sebagai `tegangan × arus` tanpa sensor faktor
daya. Karena itu variabel tersebut diperlakukan sebagai daya semu legacy,
meskipun nama kolom historis menggunakan watt.

CSV 2.027.520 baris adalah artefak augmentasi lama yang setara dengan 22 replay
trace asli. Baris tersebut bukan observasi independen dan tidak digunakan untuk
training, validation, atau test akurasi model. Posisi resminya adalah
**workload replay arsitektur** dengan `source_type=legacy_augmented_replay`.
Sampel yang tersebar pada seluruh blok digunakan untuk benchmark inference,
serialisasi, routing, dan throughput.

## Pembentukan data sintetis

Generator memiliki dua lapisan:

1. **Keadaan laten:** waktu, okupansi, kondisi termal, kelembapan, status beban,
   tegangan sebenarnya, arus sebenarnya, dan daya sebenarnya.
2. **Observasi sensor:** noise, kuantisasi DHT, threshold arus 0,1 A,
   validasi tegangan 150–300 V, dropout, packet loss, dan jitter timestamp.

Setiap baris membawa `scenario_id`, `run_id`, `seed`, `source_type`, serta
pasangan kolom `true_*` dan `observed_*`. `device_id` tetap satu karena memang
merepresentasikan gateway lama; variasi eksperimen dinyatakan melalui skenario
dan run, bukan identitas perangkat palsu.

## Validasi sintetis

Pemeriksaan mencakup kuantil, proporsi nol, autokorelasi lag-1, packet loss, dan
perbandingan per skenario. Kesesuaian statistik hanya menunjukkan kalibrasi,
bukan membuktikan data sintetis sebagai data nyata. Parameter dan seed wajib
dilaporkan.

## Evaluasi estimator

Target adalah `true_power_w`. Kandidat:

- konstanta median train;
- baseline firmware `observed_voltage_v × observed_current_a`;
- Ridge;
- Random Forest.

Pemisahan dilakukan berdasarkan skenario: `normal` dan `hot_busy` untuk
training, `humid_unstable` untuk validation, serta `cool_low_load` dan
`sensor_degraded` sebagai test yang benar-benar ditahan. Setiap skenario
mempunyai empat run 24 jam dengan seed berbeda. Tidak ada random row split.
Model dipilih menggunakan MAE validation; test tidak digunakan untuk seleksi.
Metrik utama MAE, RMSE, dan R² dilaporkan per skenario dan per run, disertai
95% confidence interval antarrun.

Workbook asli tidak mempunyai ground truth daya independen karena kolom dayanya
juga berasal dari `V × I`. Karena itu akurasi terhadap `true_power_w` hanya
dapat dievaluasi pada domain sintetis. Workbook asli digunakan untuk kalibrasi
dan pemeriksaan statistik, bukan untuk mengklaim akurasi lapangan.

## Evaluasi arsitektur

Input workload arsitektur berasal dari CSV augmented 2.027.520 baris. Pipeline
mengaudit jumlah baris, jumlah replay, perangkat, rentang waktu, nilai nol, dan
nilai hilang. Sebanyak 5.000 posisi dipilih merata di seluruh 22 blok untuk
benchmark latency per-pesan. Pesan dengan tegangan/arus nol atau daya legacy di
atas 42,6 W (P99 trace kalibrasi) dirutekan ke cloud emulasi; pesan lain
diproses di edge. Jumlah 2.027.520 hanya menyatakan volume workload replay,
bukan ukuran sampel statistik untuk akurasi model.

Latensi komputasi diukur dengan monotonic high-resolution clock pada mesin yang
menjalankan eksperimen. Latensi jaringan berasal dari profil emulasi di
`configs/experiment.json` dan harus diberi label **configured/emulated**.
Jangan menyebut hasil itu sebagai pengukuran Azure atau Raspberry Pi.

Metrik: P50/P95/P99 latensi komputasi, serialisasi, edge-path aktual,
cloud-path terkonfigurasi, hybrid end-to-end, throughput, ukuran payload,
routing, drop, dan deadline miss.

## Digital Twin Web-3D

Web-3D menerima kontrak `schemas/telemetry.schema.json`. UI harus menampilkan
sumber data (`synthetic_calibrated`, `legacy_augmented_replay`,
`real_trace_replay`, atau `live_sensor`), nama model, scope model, nilai
observasi, serta estimasi. Mode sintetis digunakan untuk membaca hasil ilmiah
model, sedangkan mode augmented digunakan untuk demonstrasi workload replay.
Digital Twin adalah lapisan visualisasi dan integrasi; keberadaannya tidak
membuktikan ketepatan model atau performa cloud.

## Ancaman validitas

- hanya satu trace pendek dan satu gateway;
- tidak ada ground truth daya aktif atau faktor daya pada data nyata;
- beberapa nol dapat bercampur antara kondisi beban dan kegagalan sensor;
- okupansi berasal dari alur berbeda dan banyak nilai hilang;
- dinamika sintetis bergantung pada asumsi generator;
- workload augmented adalah replay, bukan variasi lapangan tambahan;
- benchmark lokal tidak mewakili hardware edge produksi;
- emulasi jaringan tidak mewakili SLA public cloud.
