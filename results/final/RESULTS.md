# Hasil evaluasi kinerja Digital Twin edge–cloud multiskala

Judul: **Evaluasi Kinerja Digital Twin Edge–Cloud Multiskala untuk Monitoring Energi dan Okupansi**

Status: **evaluasi kinerja prototipe monitoring satu arah berbasis replay data
historis dengan pembanding edge–cloud dan cloud-only terkonfigurasi**.

## Cakupan data

- Trace asli: 92,160 baris bertimestamp unik dari
  1 ID gateway, periode
  2026-05-19T17:10:55.418478500+00:00 sampai
  2026-05-23T18:22:06.727676100+00:00. Trace ini adalah telemetry
  arsip dari sensor fisik pada instalasi listrik yang dipantau. `DeviceID`
  `RASPBERRY_PI_GATEWAY_001` adalah identitas gateway agregasi, bukan jumlah
  perangkat fisik.
- Peran perangkat: **ESP32** adalah node akuisisi lapangan untuk suhu, kelembapan, tegangan RMS, arus RMS, dan daya legacy V×I; **Raspberry Pi**
  adalah gateway agregasi edge; pipeline legacy mencatat ID gateway ini untuk telemetry gabungan dan membawa jalur kamera/okupansi secara terpisah. Workbook lama tidak menyimpan
  `source_node_id` per record, sehingga evaluasi ini tidak membandingkan
  performa ESP32 dan Raspberry Pi secara terpisah.
- Workload: 2,027,520 baris atau
  22 pengulangan
  deterministik dari satu blok historis turunan. Payload semua blok identik,
  tetapi blok turunan tidak identik dengan XLSX asli.
- Sampel benchmark: 5,000
  posisi yang mencakup
  22 blok.
- Klasifikasi lineage:
  `deterministic_replay_of_transformed_historical_trace`. Kode transformasi legacy
  tidak tersedia.
- Seluruh 2,027,520 baris dipindai untuk audit;
  hanya 5,000 pesan yang
  diproses benchmark. Ini bukan load test dua juta pesan.
- Trace sumber memuat 92,160 baris dengan timestamp
  unik. Independensi statistik antarbaris tidak diklaim; angka
  2,027,520 hanya volume workload replay.
- Firmware arsip merekam tegangan RMS melalui ZMPT101B
  dan arus RMS melalui SCT013-000,
  lalu menghitung daya sebagai V×I. Faktor daya tidak tersedia dalam trace.
- Energi dari trace sensor lapangan dihitung langsung dari XLSX asli dengan
  integrasi trapesium dan maksimum gap 10.0
  detik: **3355.317 Wh**
  (91,488 interval terintegrasi;
  672 interval dikecualikan).
- Satu blok payload CSV replay menghasilkan
  3474.371 Wh. Nilai replay ini dipakai untuk konteks
  payload/API dan dilaporkan terpisah karena blok CSV telah berubah dari XLSX.
- Peneliti melaporkan perbandingan perangkat dengan display reading of the PLN kWh meter for the monitored installation.
  Namun angka awal–akhir dan timestamp interval belum tersimpan di repositori;
  karena itu galat kalibrasi terhadap meter belum dapat dihitung ulang di paket
  hasil ini.
- Sampel benchmark memuat 4,748 status terisi
  dan 252 status kosong; jumlah orang
  maksimum 5.

## Hasil pemantauan lokal

| Komponen | P50 (ms) | P95 (ms) | P99 (ms) |
|---|---:|---:|---:|
| Pemeriksaan software, konsistensi, dan routing | 0.0449 | 0.1024 | 0.1806 |
| Serialisasi JSON | 0.0281 | 0.0676 | 0.1134 |
| Jalur edge aktual | 0.0732 | 0.1719 | 0.2699 |

Throughput sekuensial pada mesin uji:
**6,032.78 pesan/detik**. Angka ini mengukur loop Python lokal, bukan
kapasitas Raspberry Pi produksi.

## Routing dan kualitas pesan

- Edge: 4,886 pesan.
- Cloud: 114 pesan.
- Ambang anomali daya: 42.6 W
  berdasarkan P99 trace asli.
- Lolos pemeriksaan struktur/nilai elektrik: 5,000;
  tidak lolos:
  0.
- Selisih konsistensi |daya legacy − round(V×I, 1)|: mean
  0.5569 W, P95 1.1000 W, maksimum
  1.2000 W.

Rincian alasan routing, termasuk kategori dengan hitungan nol, tersedia di
`benchmark_metrics.json`. Pada sampel final, jalur cloud hanya terpicu oleh
daya di atas P99; cabang missing/non-finite, listrik invalid, dan arus rendah
belum tercakup data replay.

## Evaluasi edge–cloud dan baseline cloud-only

- Deadline operasional terkonfigurasi:
  3.5 detik atau
  3500.0 ms.
- Dasar deadline: pembulatan median interval antar-record trace asli
  3.5251918 detik; bukan interval
  publish nominal firmware legacy.
- Jalur cloud terkonfigurasi, khusus 114 pesan
  cloud: P50 43.534 ms,
  P95 68.018 ms, P99
  72.750 ms.
- End-to-end campuran seluruh rute: P50 0.073 ms,
  P95 0.202 ms, P99 46.106 ms.
- Baseline cloud-only dengan pesan, pemrosesan lokal, seed, dan profil jaringan
  yang sama: P50 45.486 ms,
  P95 64.680 ms, P99
  72.437 ms.
- Pada kondisi emulasi ini, edge–cloud menurunkan P95 terkonfigurasi sebesar
  99.69% dan menghindari
  10,672,144 byte transfer jaringan
  (97.72%).
- Deadline miss: 0 dari
  5,000 pesan terkirim
  (0.000%); drop terkonfigurasi:
  0.

Latensi jaringan pada bagian ini berasal dari profil emulasi yang dideklarasikan,
bukan pengukuran public cloud. Nilai campuran P50/P95 didominasi jalur edge,
sedangkan P99 memasuki kelompok pesan cloud karena
2.28%
pesan dirutekan ke cloud. Latensi render browser, replay clock, dan
multi-client juga belum
tercakup.

## Digital Twin geospasial–indoor multiskala

- **LoD-A (tapak geospasial)** menggunakan
  EPSG:4326 pada koordinat legacy
  -7.7230,
  110.5187.
- **LoD-B (bangunan)** mengikat rute edge–cloud, daya, energi kumulatif per siklus,
  dan okupansi pada payload yang sama.
- **LoD-C (indoor Babylon)** menampilkan indikator sensor, rute, dan jumlah
  orang.
- Ketiga tampilan merupakan LoD aplikatif proyek dengan perpindahan level
  manual. Kepatuhan terhadap LoD geometrik CityGML, IndoorGML, IFC, atau 3D
  Tiles belum dievaluasi. Koordinat legacy belum diverifikasi dengan survei.
- Aliran data satu arah dari sumber/replay ke representasi digital membuat
  implementasi ini tepat disebut prototipe Digital Twin berorientasi monitoring
  atau Digital Shadow, bukan sistem kendali dua arah.

## Visual hasil

- [Profil trace asli](figures/01_trace_profile.png)
- [Provenance replay](figures/02_replay_provenance.png)
- [Pemeriksaan software dan routing](figures/03_monitoring_checks.png)
- [Karakteristik latensi](figures/04_latency_characteristics.png)
- [Pemetaan Digital Twin multiskala](figures/05_multiscale_digital_twin.png)

## Kesimpulan yang didukung

Eksperimen mendukung evaluasi apakah pipeline monitoring, provenance,
integrasi energi dari trace sensor lapangan dan payload replay, monitoring
okupansi, routing edge–cloud, serialisasi,
replay API, dan prototipe geospasial–indoor satu arah bekerja dalam deadline
konfigurasi pada sampel workload replay yang tersedia.
Berdasarkan arah aliran data, implementasi lebih dekat dengan Digital Shadow
atau prototipe Digital Twin berorientasi monitoring daripada Digital Twin
operasional penuh. Eksperimen tidak mendukung klaim akurasi model, presisi
prediksi di atas 80/90 persen, load test dua juta pesan, atau generalisasi ke
banyak bangunan. Perbandingan lapangan dengan meter kWh PLN dicatat sebagai
informasi dari peneliti, tetapi paket ini belum dapat melaporkan galatnya tanpa
rekaman interval pembanding.
