# Metodologi evaluasi kinerja Digital Twin edge–cloud multiskala

## Posisi penelitian

> **Evaluasi Kinerja Digital Twin Edge–Cloud Multiskala untuk Monitoring
> Energi dan Okupansi**

Penelitian mengevaluasi arsitektur dengan memutar ulang telemetry historis.
Istilah *near real-time* mengacu pada kemampuan jalur pemrosesan memenuhi
deadline operasional terkonfigurasi 3,5 detik. Angka ini adalah pembulatan
median interval trace asli 3,5251918 detik, bukan interval publish nominal
firmware dan bukan kebaruan waktu observasi sumber.

## Pertanyaan penelitian

1. Apakah pemeriksaan software, integrasi energi trace sensor dan payload replay, routing, dan serialisasi
   dapat diproses di bawah deadline konfigurasi 3,5 detik?
2. Bagaimana distribusi routing pada sampel replay, serta apakah cabang nilai
   hilang/non-finite, pembacaan listrik invalid, arus di bawah threshold
   firmware, dan daya di atas P99 tercakup oleh replay atau unit test?
3. Bagaimana kinerja arsitektur edge–cloud selektif dibandingkan baseline
   cloud-only pada workload dan profil jaringan terkonfigurasi yang sama?
4. Dapatkah setiap payload ditelusuri ke blok replay dan posisi ancestry pada
   trace sumber serta divisualisasikan konsisten pada skala tapak, bangunan,
   dan indoor?
5. Bagaimana energi turunan dan status okupansi disajikan dengan membedakan
   telemetry sensor lapangan, payload replay, dan bukti pembandingan meter?

## Pemetaan judul terhadap bukti

| Unsur judul | Bukti |
|---|---|
| Arsitektur edge–cloud | aturan routing, hitungan jalur, pemrosesan lokal, dan profil jaringan terkonfigurasi |
| Monitoring energi | telemetry sensor lapangan, V×I hasil hitung ulang, integral XLSX asli, integral payload replay, dan batas metrologinya |
| Monitoring okupansi | jumlah orang legacy serta status occupied/unoccupied |
| Near real-time | P50/P95/P99, throughput, freshness proxy, dan deadline miss |
| Bangunan cerdas | telemetry suhu, kelembapan, listrik, dan okupansi dari arsitektur ESP32–Raspberry Pi; `DeviceID` merepresentasikan gateway |
| Visualisasi geospasial–indoor multiskala | satu payload pada skala tapak EPSG:4326, bangunan, dan indoor Babylon |
| Digital Twin | prototipe monitoring satu arah: skema JSON, replay API, provenance, grafik, dan model 3D |
| Replay data historis | 22 pengulangan deterministik blok turunan dengan `replay_id`, `source_row_id`, dan dua timestamp |

## Sumber data

Trace asli
`Data/sensor_data_export_2026-05-17_to_2026-05-23.xlsx` berisi 92.160 baris
dengan satu **ID gateway** dan periode aktual sekitar empat hari. Arsitektur
fisiknya mencakup ESP32 sebagai node akuisisi tegangan, arus, suhu, dan
kelembapan serta Raspberry Pi sebagai gateway agregasi dan jalur okupansi.
Pipeline penyimpanan lama meratakan telemetry tersebut di bawah
`RASPBERRY_PI_GATEWAY_001`; karena itu `DeviceID` bukan ID node sumber per
record dan tidak boleh dibaca sebagai bukti hanya ada satu perangkat fisik. CSV
`Data/sensor_data.csv` berisi 2.027.520 baris, tepat 22 kali ukuran trace
sumber. Pemeriksaan seluruh payload membuktikan bahwa semua 22 blok identik
satu sama lain pada `DeviceID` dan enam variabel sensor. Namun, blok pertama
berbeda dari XLSX pada 2 suhu, 2 kelembapan, 2.811 tegangan, 1.178 arus, 2.812
daya, dan 79.280 nilai okupansi. Oleh karena itu CSV diposisikan sebagai
**replay deterministik dari blok historis turunan yang telah
ditransformasi**, bukan salinan mentah, data augmented yang memberi keragaman,
atau observasi independen. Script transformasi legacy tidak tersedia.

Firmware menghitung kolom daya dengan V×I dan tidak mengukur faktor daya.
Karena itu sistem melaporkannya sebagai `power_legacy_w`. Nilai
`power_formula_w` adalah hasil hitung ulang V×I untuk pemeriksaan konsistensi,
bukan estimasi ML.

Energi dihitung pada satu siklus trace menggunakan integral trapesium:

`Eᵢ = ((Pᵢ₋₁ + Pᵢ) / 2) × Δt / 3600`

dengan satuan Wh. Interval hanya diintegrasikan bila timestamp valid,
`0 < Δt ≤ 10 detik`, serta kedua nilai daya finite dan non-negatif. Nilai
kumulatif di-reset pada awal setiap siklus replay. Karena `P` adalah proksi
legacy V×I tanpa faktor daya, hasil energi merupakan **indikator energi
legacy**. Peneliti melaporkan perbandingan perangkat terhadap meter kWh PLN,
tetapi pasangan pembacaan meter awal–akhir tidak tersedia di repositori untuk
menghitung galat kalibrasi secara reproduktif.

## Rekonstruksi provenance

Pipeline membaca seluruh 2.027.520 baris secara chunked. Setiap payload
dibandingkan dengan posisi modulo pada blok pertama; blok pertama kemudian
dibandingkan per kolom dengan 92.160 baris XLSX. Untuk setiap posisi CSV:

- `replay_block_id = floor(legacy_row_index / 92.160)`;
- `source_row_index = legacy_row_index mod 92.160`;
- `replay_id` mengidentifikasi satu dari 22 blok;
- `source_row_id` menyatakan ancestry berdasarkan posisi, bukan jaminan
  kesamaan nilai dengan XLSX;
- `source_timestamp_utc` menyimpan waktu observasi asli;
- `replay_timestamp_utc` menyimpan waktu yang berada pada CSV replay.

Sebanyak 5.000 posisi unik dipilih merata pada seluruh file untuk benchmark
default. Pemilihan ini memberi cakupan seluruh blok tanpa menganggap replay
sebagai replikasi statistik independen. Jadi, 2.027.520 adalah jumlah baris
yang dipindai untuk audit, sedangkan 5.000 adalah jumlah pesan yang melewati
benchmark. Eksperimen ini bukan stress/load test dua juta pesan dan server
replay default juga memuat sampel 5.000 baris.

## Pemrosesan dan routing

Setiap pesan melalui langkah berikut:

1. konversi dan pemeriksaan nilai non-finite;
2. validasi pembacaan tegangan, arus, dan daya;
3. hitung ulang `round(V×I, 1)` serta galat konsistensi;
4. petakan energi interval/kumulatif serta status okupansi;
5. routing ke cloud bila pembacaan invalid, arus di bawah threshold legacy
   0,1 A, atau daya legacy melampaui 42,6 W (P99 trace asli);
6. pembentukan dan serialisasi payload JSON.

Pesan lain tetap pada jalur edge. Routing cloud adalah keputusan arsitektur
untuk pemeriksaan lanjutan, bukan bukti bahwa public cloud benar-benar
dihubungi.

## Metrik

- latensi pemantauan lokal, serialisasi, dan jalur edge: mean, P50, P95, P99,
  maksimum;
- throughput pesan sekuensial pada mesin uji;
- jumlah edge/cloud dan alasan routing;
- nilai valid/invalid serta galat konsistensi daya;
- ukuran payload;
- latensi end-to-end, drop, dan deadline miss pada profil jaringan
  terkonfigurasi;
- pembanding cloud-only dengan pesan, payload, seed, dan draw jaringan yang
  sama: P50/P95/P99, deadline miss, offload jaringan, dan byte yang dihindari;
- energi trace XLSX lapangan, energi satu siklus payload replay, serta
  distribusi status okupansi.

Latensi lokal diukur menggunakan `time.perf_counter_ns`. Profil jaringan
normal dengan median, jitter, dan peluang drop dideklarasikan di konfigurasi.
Browser render latency tidak termasuk.

## Digital Twin geospasial–indoor multiskala

API mengirim `source_type`, blok/baris sumber, dua timestamp, energi, okupansi,
nilai monitoring, konteks tiga skala, klasifikasi lineage, status, rute,
latensi, dan freshness. Kontrak sengaja
tidak memiliki objek `estimate`, `model_name`, skenario sintetis, atau metrik
akurasi. Dashboard menampilkan tiga skala yang memakai payload sama:

1. **LoD-A, tapak geospasial**—marker koordinat legacy EPSG:4326 dan hubungan
   edge–cloud;
2. **LoD-B, bangunan**—ringkasan energi, okupansi, serta aliran
   sensor–edge–API;
3. **LoD-C, indoor**—scene glTF/Babylon dengan indikator sensor, rute, dan
   orang.

Ketiganya merupakan hirarki **application-level LoD** dengan granularitas
informasi yang meningkat dan perpindahan level melalui pilihan tampilan
manual. Implementasi belum mengonversi IFC/CityGML/IndoorGML atau menguji
kepatuhan LoD geometrik/tileset formal; koordinat legacy juga belum
diverifikasi survei.

Integrasi saat ini hanya dari replay API ke tampilan. Tidak ada perintah balik
dari representasi digital ke perangkat fisik. Berdasarkan definisi Digital
Twin versus Digital Shadow pada literatur, implementasi ini dinilai sebagai
prototipe Digital Twin berorientasi monitoring/digital shadow, bukan Digital
Twin operasional dua arah.

## Ancaman validitas

- satu trace, satu ID gateway, dan periode pendek; workbook tidak menyimpan ID
  sumber per node untuk memisahkan kontribusi ESP32 dan Raspberry Pi;
- tidak ada kanal faktor daya atau pembacaan kWh langsung pada arsip telemetry;
- perbandingan perangkat dengan meter kWh PLN dilaporkan oleh peneliti, tetapi
  interval pembandingnya belum tersedia untuk menghitung galat;
- integral energi mewarisi keterbatasan proksi V×I dan gap timestamp;
- nilai nol mencampur kemungkinan beban rendah dan kondisi sensor;
- okupansi banyak bernilai nol dan berasal dari alur berbeda;
- sensor okupansi legacy tidak divalidasi ulang terhadap ground truth;
- perubahan pada CSV lama tidak seluruhnya dapat direkonstruksi dari script
  transformasi yang hilang; audit hanya membuktikan perbedaannya;
- 22 replay bukan 22 eksperimen lapangan independen;
- benchmark hanya memproses sampel 5.000 dari 2.027.520 baris yang dipindai;
- data final tidak mencakup cabang invalid, non-finite, dan arus rendah;
- benchmark lokal tidak mewakili perangkat edge produksi;
- jaringan diemulasi dan tidak mewakili SLA public cloud;
- baseline cloud-only juga merupakan kontrafaktual terkonfigurasi;
- API bergerak satu baris per permintaan, bukan memakai replay clock sumber;
- koordinat dan perpindahan skala belum diuji terhadap data survei atau
  standar geospasial/indoor;
- Digital Twin menunjukkan integrasi/visualisasi satu arah, bukan validasi
  fisik gedung atau performa render browser.
