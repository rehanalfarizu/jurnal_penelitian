# Provenance Dataset

## File saat ini

`sensor_data.csv`

- Baris data: 2.027.520
- SHA-1 lokal: `85d9b1b16726fe0adff1cc196f0ca088fb11ed7c`
- Gateway ID: satu nilai dominan/eksklusif,
  `RASPBERRY_PI_GATEWAY_001`. Nilai ini adalah label gateway pengumpul
  Raspberry Pi, bukan bukti bahwa hanya ada satu perangkat sensor fisik.
- Rentang timestamp: 23 Februari–24 Mei 2026
- Status: **artefak turunan legacy yang dipakai sebagai replay historis**,
  bukan data primer

Pemilik penelitian menyatakan bahwa file ini diperluas dari dataset asli
sekitar 93 ribu baris menjadi sekitar 2 juta baris.

## Data asli yang ditemukan

`sensor_data_export_2026-05-17_to_2026-05-23.xlsx`

- Baris data: 92.160
- SHA-1 lokal: `e96ef3b4f467d0ada07090778b8a42cce1a77275`
- Sheet: `Sensor Data`
- Kolom: 8, sama dengan CSV replay turunan (pada dokumentasi lama disebut
  “augmented”)
- Gateway ID: `RASPBERRY_PI_GATEWAY_001` (label agregasi Raspberry Pi)
- Rentang timestamp aktual: 19 Mei 2026 17:10:55 UTC sampai
  23 Mei 2026 18:22:06 UTC
- Semua 92.160 timestamp unik dan terurut
- Durasi aktual: sekitar 4,05 hari

Nama file menyebut 17–23 Mei, tetapi record di dalamnya baru dimulai pada
19 Mei. Workbook ini merupakan kandidat data primer yang dikonfirmasi oleh
pemilik penelitian. Menurut pemilik penelitian, telemetry berasal dari dua
peran perangkat fisik: ESP32 mengakuisisi sensor tegangan, arus, suhu, dan
kelembapan; Raspberry Pi menjalankan peran gateway agregasi serta alur
okupansi/kamera. Pipeline penyimpanan lama menuliskan seluruh record dengan ID
gateway Raspberry Pi, sehingga ID tersebut tidak dapat dipakai untuk memisahkan
node sumber per baris. Hasil akumulasi perangkat pernah dibandingkan dengan
pembacaan meter kWh PLN. Nilai meter awal–akhir beserta timestamp interval
belum tersedia di repositori, sehingga pipeline tidak mengklaim atau menghitung
galat kalibrasi.

Masalah kualitas yang harus ditangani secara eksplisit:

- 2.811 record mempunyai tegangan 0;
- 1.178 record mempunyai arus 0;
- 2.812 record mempunyai daya 0;
- masing-masing terdapat sedikit nilai suhu/kelembapan 0;
- dua nilai `Jumlah Orang` kosong dan 67.349 bernilai 0;
- record didominasi kondisi daya rendah, dengan satu nilai awal 484 W.

Nilai nol tidak boleh langsung diganti tanpa membedakan kondisi perangkat
mati, sensor gagal, komunikasi gagal, dan konsumsi yang benar-benar nol.

## Hubungan data asli dan workload replay turunan

Ukuran CSV replay turunan tepat 22 kali ukuran workbook:

`2.027.520 = 92.160 × 22`

Perbandingan posisional seluruh baris menunjukkan:

- `DeviceID` sama 100%;
- suhu sama pada 99,998% baris;
- kelembapan sama pada 99,998% baris;
- tegangan sama pada 96,95% baris;
- arus sama pada 98,72% baris;
- daya sama pada 96,95% baris;
- jumlah orang hanya sama pada 13,98% baris.

CSV replay turunan terdiri dari 22 replay/pengulangan deterministik satu blok
turunan; seluruh tujuh payload non-timestamp identik antarpengulangan.
Timestamp setiap blok digeser sehingga rentangnya menjadi Februari–Mei 2026,
termasuk tanggal sebelum pengukuran asli. Perubahan terutama terjadi pada
nilai listrik nol dan jumlah orang. Dengan demikian, 2.027.520 baris tersebut
tidak boleh diperlakukan sebagai observasi lapangan independen, keragaman
augmentasi, maupun salinan mentah XLSX. `source_row_id` yang direkonstruksi
pipeline adalah ancestry posisional dan bukan bukti kesamaan nilai.

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

## Jika transformasi data diaktifkan kembali

Bagian ini adalah daftar kebutuhan provenance untuk rekonstruksi transformasi
legacy, bukan langkah pipeline aktif:

1. script pembersihan data primer dengan audit alasan setiap record dibuang
   atau ditandai;
2. seed dan seluruh parameter jika augmentasi/simulasi baru benar-benar
   digunakan;
3. mapping setiap baris turunan ke baris/waktu sumber;
4. catatan perangkat, lokasi, periode, interval sampling, dan satuan;
5. checksum untuk setiap snapshot data mentah dan data turunannya.

Ekspor data primer yang lebih baru tetap bermanfaat bila sumber Azure suatu
saat tersedia, tetapi tidak menjadi prasyarat untuk mereproduksi evaluasi
replay sekarang.

## Aturan replay aktif

- Workload replay turunan dipindai seluruhnya oleh pipeline untuk audit
  lineage dan kualitas, lalu digunakan sebagai sumber sampel replay untuk
  throughput, latency, routing, energi payload replay, okupansi, dan integrasi
  visual tapak–bangunan–indoor.
- Pipeline memberi label `historical_replay`, merekonstruksi
  `replay_block_id` dan `source_row_index`, serta mengambil sampel yang tersebar
  merata pada seluruh 22 blok.
- Jumlah 2.027.520 harus dilaporkan sebagai volume workload replay, bukan
  sebagai jumlah observasi lapangan independen.
- Benchmark default hanya memproses 5.000 pesan; jangan menyebutnya stress
  test atau load test 2.027.520 pesan.
- Pipeline aktif tidak melakukan train, validation, test, atau evaluasi
  akurasi model.
- Energi trace lapangan dihitung langsung dari XLSX asli dengan integral
  trapesium daya legacy V×I terhadap timestamp sumber. Energi satu blok CSV
  replay dihitung terpisah untuk payload/API; keduanya tidak diperlakukan
  sebagai pembacaan langsung kanal kWh atau bukti galat kalibrasi tanpa
  pasangan pembacaan meter PLN per interval.

Jika penelitian kelak kembali memakai machine learning, barulah split
train/validation/test dilakukan pada data asli sebelum augmentasi; baris
turunan dari satu observasi sumber tidak boleh tersebar antara training dan
validation/test. Ketentuan ini tidak dijalankan oleh pipeline aktif.

## Konteks dari firmware lama

Snapshot firmware yang disimpan di
`Digital_Twin/dashboard_digitaltwin/sensor_iot/esp32_main.cpp` menunjukkan
bahwa firmware:

- mengirim telemetry nominal setiap 5 detik;
- menghitung daya sebagai `tegangan × arus`;
- mengubah tegangan di luar 100–300 V menjadi tidak valid/nol;
- menganggap arus di bawah 0,1 A sebagai nol;
- mempunyai field status sensor yang tidak ikut dipertahankan dalam workbook.

Karena itu nol pada workbook tidak boleh diperlakukan sebagai missing at
random. Selain itu, tegangan dan arus tidak boleh digunakan tanpa penjelasan
untuk memprediksi target daya yang memang dihitung dari dua nilai tersebut.

Audit workspace lama yang lebih lengkap tersedia di
`../LEGACY_PROJECT_AUDIT.md`.
