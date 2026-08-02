# Audit Workspace Lama `dashboard_digitaltwin`

> **Status:** dokumen provenance historis. Rekomendasi data sintetis pada
> bagian akhir tidak menjadi metode aktif. Lihat `docs/METHODOLOGY.md` dan
> `AUDIT_RESULTS.md` untuk keputusan penelitian mutakhir.

Sumber yang diperiksa secara read-only:

`/Users/macbookpro/Documents/dashboard_digitaltwin`

Tanggal audit: 28 Juli 2026.

## Kesimpulan

Workspace lama berguna untuk merekonstruksi pipeline akuisisi, schema telemetry,
dan perilaku sensor. Workspace tersebut tidak memiliki script augmentasi
92.160 → 2.027.520, tetapi riwayat Git masih menyimpan exporter Azure dan
generator sample sintetis lama.

Kode lama tidak membuktikan bahwa CSV augmented merupakan data lapangan.
Sebaliknya, kode tersebut menjelaskan mengapa terdapat banyak nilai nol dan
mengapa prediksi daya dari tegangan/arus bersifat sirkular.

## Firmware dan data contract

Snapshot firmware yang tersalin ke repositori penelitian:

`Digital_Twin/dashboard_digitaltwin/sensor_iot/esp32_main.cpp`

Karakteristik penting:

- perangkat ESP32;
- DHT11 pada GPIO 14;
- ZMPT101B didefinisikan pada GPIO 34;
- SCT013 pada GPIO 32;
- interval publish nominal 5 detik;
- `VOLTAGE_CALIBRATION = 660.0`;
- batas bawah tegangan pada snapshot adalah 100 V;
- `CURRENT_CALIBRATION = 300.0`;
- arus di bawah 0,1 A dianggap nol;
- daya dihitung di firmware sebagai `tegangan × arus`;
- payload mengandung suhu, kelembapan, tegangan, arus, daya, status sensor,
  device ID, dan timestamp UTC.

Snapshot ini berbeda dari parameter yang pernah ditemukan di workspace lama.
Tidak tersedia hash/version link yang menghubungkan firmware, deployment, dan
ekspor XLSX pada saat akuisisi. Karena itu file tersebut adalah bukti desain
legacy, bukan bukti bahwa snapshot persis inilah yang menghasilkan workbook.

Implikasi:

1. Nilai daya bukan hasil wattmeter independen; ia merupakan turunan dari
   tegangan dan arus.
2. Menggunakan tegangan dan arus sebagai fitur untuk menargetkan daya akan
   menghasilkan kebocoran definisional atau masalah yang terlalu trivial.
3. Banyak nilai nol pada workbook konsisten dengan threshold dan kondisi
   sensor dianggap tidak tersambung/tidak valid.
4. Workbook tidak menyimpan seluruh metadata firmware seperti status sensor
   dan state AC, sehingga informasi penting telah hilang saat ekspor.

Schema formal lama masih tersedia pada:

`sensor iot/azure-setup/models/EnergyMonitorSensor.json`

## Pipeline cloud lama

Alur aktual yang ditemukan:

1. ESP32 memublikasikan JSON melalui MQTT over TLS ke Azure IoT Hub.
2. `IoTHubToStorage` menyimpan telemetry ke tabel `SensorTelemetry`.
3. People counter disimpan terpisah ke tabel `PeopleCount`.
4. `GetTelemetryData` membaca telemetry untuk dashboard.
5. Dashboard melakukan polling Azure Function dan memetakan telemetry ke
   model Web-3D.

People count berasal dari stream/tabel terpisah. Penggabungannya dengan setiap
baris sensor membutuhkan aturan temporal yang eksplisit, misalnya nearest
previous observation dengan batas staleness. Mengacak jumlah orang bukan
pengganti sinkronisasi tersebut.

## Artefak yang tidak ikut tersalin ke workspace penelitian

Artefak lama yang berpotensi berguna:

- `CONTEXT.md` — dokumentasi arsitektur dan technical debt;
- `sensor iot/src/main.cpp` — firmware paling lengkap;
- `sensor iot/azure-setup/models/EnergyMonitorSensor.json` — schema DTDL;
- `ml_models/train_from_azure.py` — contoh fetch Azure, tetapi metodologi
  training-nya tidak layak dipakai langsung;
- `ml_models/train_model.py` — baseline lama, menggunakan random split;
- setup/deployment script Azure;
- exporter Azure lama yang masih dapat ditemukan sebagai blob Git
  `e90ab4fd35581b906e9fdfb670b93bbbb10de5c6`;
- generator sample lama pada blob Git
  `8553137847c4b4936b94a9fdd175ed7df78af699`.

Jangan menyalin `secrets.h`, `.env`, connection string, model PKL, dependency
build `.pio`, atau konfigurasi subscription lokal.

## Generator sintetis lama tidak layak digunakan

Generator sample historis membuat 30 hari data dengan sinus harian dan
`Math.random()`. Ia juga mencampur satuan: komentar menyebut 1–5 kW, nilai
`daya` sekitar 2–5, lalu arus dihitung sebagai `daya / 220`. Generator ini
tidak dikalibrasi dari workbook asli dan tidak mempunyai provenance seed.

Karena itu generator sintetis baru harus dibuat dari nol.

## Catatan historis: opsi data sintetis yang tidak dipilih

Bagian berikut merekam opsi yang pernah dipertimbangkan, bukan pipeline aktif.
Data sintetis hanya dapat digunakan bila paper secara eksplisit menyebut
**simulation-based evaluation** atau **synthetic workload calibrated from a
real four-day trace**.

Generator baru sebaiknya mempunyai dua lapisan:

### 1. Latent physical state

- waktu dan pola okupansi;
- status beban/appliance idle atau aktif;
- base load dan beban perangkat;
- suhu luar/dalam dan kelembapan;
- dinamika termal sederhana (misalnya model RC);
- tegangan jaringan dan true current;
- `true_power_w` sebagai ground truth sintetis.

### 2. Sensor observation model

- quantization DHT11;
- noise dan drift ZMPT101B/SCT013;
- faktor kalibrasi firmware;
- threshold yang menghasilkan nol;
- packet loss, keterlambatan, dan timestamp jitter;
- `observed_voltage_v`, `observed_current_a`, dan `observed_power_w`;
- status sensor serta missingness.

Setiap record wajib mempunyai:

- `scenario_id`;
- `run_id`;
- `seed`;
- `source_type` (`real` atau `synthetic`);
- `source_row_id` bila dikalibrasi dari trace asli;
- state beban dan status sensor;
- true value serta observed value yang dipisahkan.

## Validasi generator

Generator tidak cukup dinilai dari kemiripan mean dan standard deviation.
Bandingkan data sintetis dengan workbook asli menggunakan:

- distribusi dan quantile setiap sensor;
- proporsi nol/missing;
- autocorrelation dan partial autocorrelation;
- distribusi interval antar-record;
- durasi setiap regime daya;
- cross-correlation suhu, kelembapan, okupansi, dan daya;
- Wasserstein distance atau KS statistic;
- pola transisi state;
- sensitivity analysis terhadap parameter dan seed.

Data asli empat hari berfungsi sebagai trace kalibrasi dan pemeriksaan
sim-to-real. Ia tidak boleh digabung dengan data sintetis lalu diacak pada
train/test.

## Pemisahan evaluasi

### Akurasi estimator

- train pada skenario sintetis tertentu;
- validation pada seed/skenario sintetis yang berbeda;
- test pada skenario yang benar-benar ditahan;
- tambahkan evaluasi pada trace asli sejauh schema target memungkinkan;
- bandingkan baseline fisika, persistence, linear model, dan model ML.

### Performa arsitektur edge-cloud

- replay event sintetis dengan rate terkontrol;
- ukur runtime sebenarnya pada mesin yang digunakan;
- jika jaringan/cloud disimulasikan, beri label emulasi;
- laporkan P50/P95/P99 latency, throughput, queue depth, drop rate,
  bandwidth, dan Digital Twin staleness;
- jangan menyebut hasil laptop/emulator sebagai pengukuran Raspberry Pi atau
  Azure produksi.

## Judul alternatif historis jika data dominan sintetis

Versi yang lebih aman:

> Arsitektur Edge-Cloud untuk Estimasi Daya Near Real-Time Bangunan Cerdas
> Terintegrasi Digital Twin Web-3D: Evaluasi Berbasis Data Sintetis
> Terkalibrasi

Alternatif ini tidak dipakai. Judul dan pipeline aktif sekarang mengevaluasi
kinerja Digital Twin edge–cloud untuk monitoring energi–okupansi dengan visual
tapak–bangunan–indoor multiskala, memakai replay historis turunan tanpa
estimator dan tanpa generator sintetis.
