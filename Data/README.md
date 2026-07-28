# Provenance Dataset

## File saat ini

`sensor_data.csv`

- Baris data: 2.027.520
- SHA-1 lokal: `85d9b1b16726fe0adff1cc196f0ca088fb11ed7c`
- Device ID: satu nilai dominan/eksklusif,
  `RASPBERRY_PI_GATEWAY_001`
- Rentang timestamp: 23 Februari–24 Mei 2026
- Status: **data augmented**, bukan data primer

Pemilik penelitian menyatakan bahwa file ini diperluas dari dataset asli
sekitar 93 ribu baris menjadi sekitar 2 juta baris.

## Data asli yang ditemukan

`sensor_data_export_2026-05-17_to_2026-05-23.xlsx`

- Baris data: 92.160
- SHA-1 lokal: `e96ef3b4f467d0ada07090778b8a42cce1a77275`
- Sheet: `Sensor Data`
- Kolom: 8, sama dengan CSV augmented
- Device ID: `RASPBERRY_PI_GATEWAY_001`
- Rentang timestamp aktual: 19 Mei 2026 17:10:55 UTC sampai
  23 Mei 2026 18:22:06 UTC
- Semua 92.160 timestamp unik dan terurut
- Durasi aktual: sekitar 4,05 hari

Nama file menyebut 17–23 Mei, tetapi record di dalamnya baru dimulai pada
19 Mei. Workbook ini merupakan kandidat data primer yang dikonfirmasi oleh
pemilik penelitian.

Masalah kualitas yang harus ditangani secara eksplisit:

- 2.811 record mempunyai tegangan 0;
- 1.178 record mempunyai arus 0;
- 2.812 record mempunyai daya 0;
- masing-masing terdapat sedikit nilai suhu/kelembapan 0;
- dua nilai `Jumlah Orang` kosong dan 67.349 bernilai 0;
- record didominasi kondisi daya rendah, dengan satu nilai awal 484 W.

Nilai nol tidak boleh langsung diganti tanpa membedakan kondisi perangkat
mati, sensor gagal, komunikasi gagal, dan konsumsi yang benar-benar nol.

## Hubungan data asli dan augmented

Ukuran CSV augmented tepat 22 kali ukuran workbook:

`2.027.520 = 92.160 × 22`

Perbandingan posisional seluruh baris menunjukkan:

- `DeviceID` sama 100%;
- suhu sama pada 99,998% baris;
- kelembapan sama pada 99,998% baris;
- tegangan sama pada 96,95% baris;
- arus sama pada 98,72% baris;
- daya sama pada 96,95% baris;
- jumlah orang hanya sama pada 13,98% baris.

CSV augmented terdiri dari 22 replay/pengulangan berurutan dataset asli.
Timestamp setiap blok digeser sehingga rentangnya menjadi Februari–Mei 2026,
termasuk tanggal sebelum pengukuran asli. Perubahan terutama terjadi pada
nilai listrik nol dan jumlah orang. Dengan demikian, 2.027.520 baris tersebut
tidak boleh diperlakukan sebagai observasi lapangan independen.

## Temuan dari riwayat Git

Commit `4109b0a` juga mempunyai `sensor_data_primary.csv` sebanyak 92.160 baris dan
tiga generator:

- `generate_92k_dataset.py`
- `generate_primary_dataset.py`
- `generate_sensor_data.py`

Generator tersebut membuat dataset sintetis lain menggunakan profil bangunan,
pola harian, distribusi acak, noise, dan anomali injeksi. File historis itu
berbeda konsep dari workbook hasil ekspor yang sekarang tersedia dan tidak
boleh tertukar dengannya.

Riwayat dokumentasi juga pernah menyebut sumber Azure sebanyak sedikitnya
240.087 baris. Klaim tersebut belum dapat direkonsiliasi dengan pernyataan
dataset asli sekitar 93 ribu.

## Berkas yang masih dibutuhkan

Sebelum eksperimen baru, tambahkan:

1. ekspor data primer yang lebih baru jika sumber Azure masih tersedia;
2. script pembersihan data primer dengan audit alasan setiap record dibuang
   atau ditandai;
3. script augmentasi baru hanya jika augmentasi memang dibutuhkan;
4. seed random dan seluruh parameter augmentasi;
5. mapping setiap baris augmented ke baris/waktu sumber;
6. catatan perangkat, lokasi, periode, interval sampling, dan satuan;
7. checksum untuk setiap snapshot data mentah dan data turunannya.

## Aturan evaluasi

- Split train/validation/test harus dilakukan pada data asli terlebih dahulu.
- Augmentasi hanya boleh diterapkan pada bagian training.
- Validation dan test harus tetap berupa observasi asli yang tidak
  diaugmentasi.
- Baris turunan dari satu observasi sumber tidak boleh tersebar antara train
  dan test.
- Dataset augmented digunakan oleh pipeline sebagai workload replay untuk
  stress test throughput, latency, routing, dan integrasi Digital Twin Web-3D.
- Pipeline memberi label `legacy_augmented_replay`, merekonstruksi
  `replay_block_id` dan `source_row_index`, serta mengambil sampel yang tersebar
  merata pada seluruh 22 blok.
- Jumlah 2.027.520 harus dilaporkan sebagai volume workload replay, bukan
  sebagai jumlah observasi lapangan independen.
- Dataset augmented tetap dilarang untuk train, validation, dan test akurasi
  model final.

## Konteks dari firmware lama

Audit `/Users/macbookpro/Documents/dashboard_digitaltwin/sensor iot/src/main.cpp`
menunjukkan bahwa firmware:

- mengirim telemetry nominal setiap 5 detik;
- menghitung daya sebagai `tegangan × arus`;
- mengubah tegangan di luar 150–300 V menjadi tidak valid/nol;
- menganggap arus di bawah 0,1 A sebagai nol;
- mempunyai field status sensor yang tidak ikut dipertahankan dalam workbook.

Karena itu nol pada workbook tidak boleh diperlakukan sebagai missing at
random. Selain itu, tegangan dan arus tidak boleh digunakan tanpa penjelasan
untuk memprediksi target daya yang memang dihitung dari dua nilai tersebut.

Audit workspace lama yang lebih lengkap tersedia di
`../LEGACY_PROJECT_AUDIT.md`.

## Diagnosis baseline pada data asli

Audit 28 Juli 2026 menggunakan split kronologis 70% train, 15% validation,
dan 15% test. Hasil test:

| Baseline/model | Fitur | R² | MAE |
|---|---|---:|---:|
| Mean data train | konstanta | -2,930 | 3,652 W |
| Ridge | suhu, kelembapan, okupansi, waktu | -9,908 | 6,605 W |
| HistGradientBoosting | suhu, kelembapan, okupansi, waktu | -6,094 | 4,726 W |
| Persistence | daya sebelumnya | 0,741 | 0,410 W |
| Rolling mean 10 sampel | riwayat daya | 0,839 | 0,380 W |
| Rumus fisika | tegangan × arus | 0,909 | 0,541 W |
| HistGradientBoosting | tegangan, arus | 0,875 | 0,608 W |

Test hanya memiliki simpangan baku daya sekitar 2,10 W. Train mempunyai mean
34,90 W dan memuat seluruh 2.812 nilai daya nol, sedangkan test mempunyai mean
38,49 W tanpa nilai nol. Pergeseran distribusi ini membuat R² sangat sensitif.

Korelasi terhadap daya pada seluruh data:

- tegangan: 0,935;
- arus: 0,565;
- jumlah orang: 0,195;
- suhu: -0,169;
- kelembapan: -0,187.

Artinya, model berbasis kondisi lingkungan tidak memiliki sinyal yang cukup
untuk menjelaskan daya saat ini. Augmentasi baris tidak dapat memperbaiki
ketiadaan fitur kausal. Jika tegangan dan arus tersedia, `P = V × I` harus
menjadi baseline utama; model ML wajib menunjukkan manfaat di atas baseline
fisika tersebut.
