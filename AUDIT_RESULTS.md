# Audit Kesesuaian Proyek Penelitian

Tanggal audit: 29 Juli 2026

Judul penelitian:

> **Evaluasi Kinerja Digital Twin Edge–Cloud Multiskala untuk Monitoring
> Energi dan Okupansi**

Audit ini menilai kecocokan data, kode, benchmark, visual tiga skala,
notebook, dan referensi terhadap judul tersebut.

## Kesimpulan eksekutif

Repositori sudah dapat dipertahankan sebagai **evaluasi kinerja prototipe
Digital Twin edge–cloud berorientasi monitoring berbasis replay**. Judul baru
didukung oleh integrasi energi-proksi, okupansi, baseline cloud-only, serta
visual tapak–bangunan–indoor. Istilah `Digital Twin` tetap dibatasi karena
implementasi satu arah secara taksonomi lebih dekat dengan prototipe
monitoring/digital shadow.

Temuan data yang paling menentukan adalah:

- XLSX memuat 92.160 baris bertimestamp unik dari satu gateway dan sekitar
  empat hari;
- CSV memuat 2.027.520 baris = 22 × 92.160;
- seluruh tujuh payload non-timestamp identik pada 22 blok;
- blok CSV bukan salinan mentah XLSX dan kode transformasi legacy tidak ada;
- seluruh CSV dipindai untuk audit, tetapi benchmark default hanya memproses
  5.000 pesan.

Dengan demikian, angka 2.027.520 tidak boleh dipakai sebagai jumlah observasi
independen, keragaman augmentasi, jumlah pesan yang di-load-test, atau dasar
peningkatan presisi model.

## 1. Audit data dan lineage

Pipeline membandingkan setiap payload CSV dengan posisi modulo pada blok
pertama, kemudian membandingkan blok pertama dengan XLSX asli.

| Variabel | Cocok | Berubah | Tingkat cocok |
|---|---:|---:|---:|
| Device ID | 92.160 | 0 | 100,000% |
| Suhu | 92.158 | 2 | 99,998% |
| Kelembapan | 92.158 | 2 | 99,998% |
| Tegangan | 89.349 | 2.811 | 96,950% |
| Arus | 90.982 | 1.178 | 98,722% |
| Daya | 89.348 | 2.812 | 96,949% |
| Jumlah orang | 12.880 | 79.280 | 13,976% |

Klasifikasi machine-readable:
`deterministic_replay_of_transformed_historical_trace`.

`source_row_id` menyatakan ancestry berdasarkan posisi, bukan jaminan bahwa
nilai CSV sama dengan nilai XLSX. Perubahan terbesar ada pada okupansi dan
nilai listrik nol. Karena script transformasi hilang, pipeline hanya dapat
membuktikan pola perubahan, bukan merekonstruksi alasan setiap perubahan.

## 2. Audit benchmark edge-cloud

Yang benar-benar diukur:

- pemeriksaan struktur/nilai pada host lokal;
- pemeriksaan konsistensi `round(V×I, 1)`;
- keputusan routing dan pembentukan payload;
- serialisasi JSON;
- throughput loop sekuensial pada mesin eksekusi.

Yang dikonfigurasi, bukan diukur di lapangan:

- distribusi latensi jaringan jalur cloud;
- peluang drop jaringan;
- latensi end-to-end yang memasukkan profil jaringan tersebut.

Benchmark 5.000 pesan menghasilkan 4.886 rute edge dan 114 rute cloud. Semua
rute cloud berasal dari `power_above_trace_p99`. Data final tidak mencakup
cabang `missing_or_nonfinite_value`, `invalid_electrical_reading`, atau
`current_below_legacy_threshold`; ketiga cabang hanya diuji dengan fixture
unit test. Karena itu `5.000 valid` berarti lolos pemeriksaan software, bukan
validasi daya aktif atau validasi lapangan.

Angka daya adalah proxy legacy `V×I` yang dilabeli watt. Tanpa faktor daya dan
wattmeter pembanding, ia bukan ground truth metrologi daya aktif.

Energi dihitung dengan integral trapesium proksi tersebut pada timestamp
sumber, maksimum gap 10 detik, dan di-reset per siklus trace. Ini memberi
indikator Wh yang konsisten untuk monitoring, tetapi bukan pembacaan meter
energi aktif. Okupansi dibawa sebagai `people_count` dan status
`occupied/unoccupied`; akurasi sensor legacy belum divalidasi ulang.

Benchmark juga menghitung baseline cloud-only dengan payload, pemrosesan,
seed, dan draw jaringan yang sama. Perbandingan tersebut sah sebagai
eksperimen emulasi terkontrol, bukan pengukuran public cloud.

## 3. Audit replay dan near real-time

Replay API bergerak satu baris setiap permintaan HTTP. Server default memuat
5.000 sampel merata, bukan seluruh 2.027.520 baris. Interval antarbaris sumber
yang disampel jauh lebih besar daripada interval polling browser, sehingga
ini adalah replay berurutan berbasis permintaan, bukan reproduksi cadence
historis.

Klaim near real-time hanya didukung oleh:

- perbandingan latensi pemrosesan dengan deadline konfigurasi 3,5 detik,
  yaitu pembulatan median interval trace asli 3,5251918 detik dan bukan
  interval publish nominal firmware;
- throughput loop lokal;
- freshness proxy pemrosesan dan jaringan terkonfigurasi.

Klaim tersebut belum mencakup browser render, antrean multi-client, clocked
replay, perangkat edge fisik, atau public cloud.

## 4. Audit Digital Twin geospasial–indoor multiskala

Bukti yang tersedia:

- kontrak JSON dengan provenance;
- API `/health`, `/latest`, dan `/history`;
- pemetaan payload ke dashboard Vue;
- model glTF/Babylon.js dan visual telemetry;
- tampilan tapak EPSG:4326, ringkasan skala bangunan, dan indoor 3D;
- energi, okupansi, rute, serta provenance yang sama pada ketiga skala;
- unit test komponen/kontrak serta build frontend.

Bukti yang belum tersedia:

- sinkronisasi atau kontrol dua arah ke bangunan;
- validasi perubahan state fisik-spasial;
- pengukuran frame rate dan latensi browser;
- uji end-to-end pada deployment edge-cloud;
- uji concurrency/multi-client.
- validasi koordinat survei, transformasi CRS, atau kepatuhan LoD geometrik
  CityGML/IndoorGML/IFC/3D Tiles.

Karena aliran data hanya menuju representasi digital, klasifikasi yang aman
adalah **prototipe Digital Twin multiskala berorientasi monitoring/digital
shadow**. Sistem mempunyai LoD aplikatif proyek—LoD-A tapak, LoD-B bangunan,
dan LoD-C indoor—tetapi belum mengklaim kepatuhan LoD geometrik standar.

## 5. Audit referensi

Seluruh **30 PDF lokal** sudah dicatat di `pdf_references/PDF_INDEX.md` dan
dinilai di `pdf_references/REFERENCE_AUDIT.md`: 18 referensi inti, 4
pendukung/perlu kehati-hatian, dan 8 arsip yang tidak disarankan sebagai dasar
klaim utama. Lima artikel open-access terbaru ditambahkan untuk memperkuat
BIM–GIS indoor–outdoor, interoperabilitas geospasial–bangunan, energi–
okupansi, dan IoT terdistribusi pada Digital Twin bangunan.

Referensi inti paling selaras meliputi:

- Sepasgozar (2021) untuk batas Digital Twin versus Digital Shadow;
- Raith dkk. (2023) untuk evaluasi edge-cloud berbasis trace;
- Xhafa dkk. (2020) untuk stream processing pada edge;
- Sinthamrongruk dkk. (2026) untuk Digital Twin Web-3D;
- Wang dkk. (2025) untuk MQTT/WebSocket dan binding model bangunan;
- Himeur dkk. (2021/2022) untuk arsitektur edge-cloud energi.
- Chen dkk. (2021) dan Herle dkk. (2020) untuk BIM–GIS/multiskala;
- Clausen dkk. (2021) dan Smirnov & Re Cecconi (2026) untuk energi–okupansi;
- Walczyk & Ożadowicz (2024) untuk BIM–Digital Twin–IoT terdistribusi.

Korpus awal cukup besar, tetapi beberapa paper ML/forecasting, federated
learning, stadium, lighting, dan keselamatan konstruksi berada di luar metode
aktif. Paper keselamatan konstruksi juga memiliki DOI referensi internal yang
tidak dapat dipercaya dan tidak boleh dipakai sebagai landasan ilmiah.

## 6. Perubahan kode dari audit

- audit lineage isi 22 blok dan perbandingan XLSX–CSV ditambahkan;
- klasifikasi lineage ikut dibawa dalam payload telemetry;
- routing missing/non-finite dipastikan menuju cloud;
- semua alasan routing, termasuk kategori dengan hitungan nol, dilaporkan;
- integrasi energi-proksi dan status okupansi ditambahkan ke data kanonis,
  schema, API, benchmark, dan dashboard;
- baseline cloud-only yang dapat direproduksi ditambahkan;
- visual Digital Twin tapak–bangunan–indoor ditambahkan;
- scope benchmark membedakan baris yang dipindai dari pesan yang dibenchmark;
- istilah `field validation` dihapus dari definisi pemeriksaan software;
- notebook dibangun sebagai workflow eksekutabel, bukan pembaca artefak;
- konfigurasi Git diperbaiki agar kode konfigurasi frontend dan lisensi model
  tidak hilang pada fresh clone;
- file orphan, duplikat, cache, dependency build, dan output build lokal
  dibersihkan setelah pengujian.

Kode firmware, Azure Functions, dan people counter lama dipertahankan hanya
sebagai provenance akuisisi. Ketiganya tidak dipanggil pipeline evaluasi aktif.
Pemindaian source tidak menemukan credential aktif yang di-hard-code; nilai
konfigurasi sensitif berupa placeholder atau dibaca dari environment.

## 7. Verifikasi eksekusi

- notebook valid: 32 sel, 18/18 sel kode tereksekusi, tanpa output error;
- seluruh 2.027.520 baris dipindai dan 5.000 pesan dibenchmark;
- 5.000/5.000 payload benchmark lolos JSON Schema;
- smoke test API mencakup health, dua latest, history, input invalid, dan 404;
- 7/7 unit test Python lulus;
- 35/35 unit test frontend lulus;
- build produksi Vue/Vite berhasil;
- `npm audit --omit=dev` melaporkan 0 kerentanan pada dependensi produksi
  setelah pembaruan kompatibel PostCSS, Vite, dan Vitest;
- audit penuh masih melaporkan 11 temuan high pada rantai alat pengembangan
  `@vue/test-utils`/`js-beautify`/`minimatch`; perbaikan yang ditawarkan npm
  memerlukan `--force` dan perubahan breaking, sehingga tidak diterapkan;
- 30/30 PDF dapat dibuka dan tidak ada duplikat hash;
- seluruh entri manifest final mempunyai hash/ukuran yang cocok.

Peringatan `sysctlbyname` dari PyArrow pada sandbox macOS muncul saat membaca
data, tetapi tidak menyebabkan kegagalan pipeline atau uji.

## 8. Keputusan kelayakan

| Klaim | Status | Batas |
|---|---|---|
| Monitoring energi | Didukung terbatas | integral proksi V×I, bukan energi aktif terkalibrasi |
| Monitoring okupansi | Didukung terbatas | jumlah orang legacy, belum divalidasi ulang |
| Audit replay historis | Didukung | blok turunan telah ditransformasi |
| Routing edge-cloud | Didukung pada software | cloud nyata belum dipanggil |
| Near real-time | Didukung terbatas | host lokal + jaringan terkonfigurasi |
| Visual geospasial–indoor multiskala | Didukung sebagai prototipe | LoD-A/B/C aplikatif tersedia; koordinat dan kepatuhan LoD geometrik standar belum divalidasi |
| Digital Twin | Didukung sebagai prototipe satu arah | bukan DT dua arah/validasi fisik |
| Akurasi model >80% atau >90% | Tidak berlaku | tidak ada estimator |
| 2 juta observasi/load-test | Tidak didukung | 2 juta dipindai; 5.000 dibenchmark |
| Validasi lapangan final | Tidak didukung | sensor tidak direkam ulang |

## 9. Syarat sebelum naskah jurnal final

Hasil sekarang dapat digunakan dengan batas klaim di atas. Untuk memperkuat
paper final, prioritas berikutnya adalah:

1. menjalankan benchmark berulang pada perangkat edge yang dinyatakan;
2. menguji satu endpoint cloud nyata atau tetap menyebut jalur cloud sebagai
   emulasi;
3. menambahkan replay clock/rate dan uji beban yang benar bila ingin membuat
   klaim skala dua juta pesan;
4. mengukur render/freshness browser serta perpindahan skala visual;
5. menyatakan Digital Shadow/prototipe monitoring secara eksplisit;
6. memvalidasi koordinat, sensor okupansi, dan energi dengan instrumen bila
   perangkat/data baru kelak tersedia;
7. tidak melaporkan akurasi/presisi model karena model memang tidak digunakan.
