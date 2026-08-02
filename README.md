# Evaluasi Kinerja Digital Twin Edge–Cloud Multiskala

Repositori penelitian:

> **Evaluasi Kinerja Digital Twin Edge–Cloud Multiskala untuk Monitoring
> Energi dan Okupansi**

## Ruang lingkup

Pipeline mengevaluasi monitoring energi–okupansi, provenance, routing
edge–cloud, serialisasi, replay API, baseline cloud-only terkonfigurasi, dan
integrasi Digital Twin pada skala tapak geospasial, bangunan, serta indoor 3D.
Tidak ada tahap pelatihan atau evaluasi model estimasi.

Sumber asli adalah satu trace historis berisi 92.160 observasi dari arsitektur
sensor fisik ESP32–Raspberry Pi pada instalasi listrik yang dipantau. ESP32
mengakuisisi tegangan, arus, suhu, dan kelembapan; Raspberry Pi menjadi gateway
agregasi serta menjalankan jalur okupansi. Label data
`RASPBERRY_PI_GATEWAY_001` adalah ID gateway, bukan ID satu-satunya perangkat
fisik. Firmware arsip menggunakan ZMPT101B untuk tegangan dan SCT013-000 untuk
arus. Peneliti juga melaporkan
perbandingan pembacaan perangkat dengan meter kWh PLN, tetapi nilai awal–akhir
per interval belum tersimpan dalam repositori sehingga galatnya belum dapat
dihitung ulang. Audit nilai-per-nilai membuktikan bahwa `Data/sensor_data.csv`
berisi 2.027.520
baris atau 22 pengulangan deterministik dari satu blok turunan berukuran
92.160 baris. Ketujuh payload non-timestamp identik antarpengulangan, tetapi
blok turunan tidak identik dengan XLSX: terutama nilai listrik nol dan
okupansi telah berubah. Kode transformasi legacy tidak tersedia. Jumlah itu
adalah volume sumber replay, bukan observasi lapangan independen atau
keragaman hasil augmentasi.

Kolom daya berasal dari logika firmware lama `tegangan × arus`. Faktor daya
tidak direkam, sehingga repositori menyebutnya **daya legacy V×I**, bukan
pengukuran daya aktif langsung. Energi dari trace sensor lapangan dihitung
langsung dari XLSX asli; energi payload CSV replay dihitung dan dilaporkan
terpisah agar nilai fisik tidak tercampur dengan workload turunan.

## Struktur utama

- `configs/experiment.json` — sumber data, ukuran replay, routing, dan profil
  jaringan terkonfigurasi.
- `src/data/` — audit trace dan rekonstruksi provenance replay.
- `src/benchmark/` — pengukuran validasi, routing, serialisasi, throughput,
  dan emulasi jaringan berlabel.
- `src/replay/` — API HTTP untuk replay telemetry.
- `schemas/telemetry.schema.json` — kontrak pemantauan tanpa estimasi ML.
- `Digital_Twin/` — firmware legacy dan dashboard tapak–bangunan–indoor.
- `docs/METHODOLOGY.md` dan `docs/RESEARCH_FLOW.md` — metode serta alur.
- `notebooks/01_evaluasi_final.ipynb` — workflow eksekutabel dari audit sumber,
  lineage, benchmark, schema/API, visual, sampai pemeriksaan integrasi.
- `results/final/` — metrik, visual, konfigurasi, dan manifest hasil.
- `pdf_references/REFERENCE_AUDIT.md` — matriks relevansi korpus jurnal dan
  batas penggunaannya.

## Menjalankan evaluasi

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_experiment.py
python -m unittest discover -s tests -v
python -m src.reporting.generate_figures
python -m src.reporting.generate_final_report
```

Smoke test benchmark dapat menggunakan jumlah sampel lebih kecil:

```bash
python run_experiment.py --sample-size 200
```

## Replay API dan Digital Twin multiskala

Jalankan pipeline terlebih dahulu agar sampel kanonis tersedia, lalu:

```bash
python -m src.replay.replay_server
```

Untuk membaca langsung CSV replay dan membentuk sampel saat server dimulai:

```bash
python -m src.replay.replay_server \
  --input Data/sensor_data.csv \
  --input-format historical_csv \
  --sample-size 5000
```

Pada terminal lain:

```bash
cd Digital_Twin/dashboard_digitaltwin/view_virtual
npm ci
npm run test:run -- --maxWorkers=1 --no-file-parallelism
npm run dev
```

Dashboard menggunakan `http://127.0.0.1:8000/api` secara default. Endpoint
dapat diubah melalui `VITE_TELEMETRY_API_URL`.

Endpoint `/telemetry/latest` membungkus payload sebagai
`{ "success": true, "data": ... }`; JSON Schema berlaku pada objek `data`,
bukan pada envelope HTTP.

## Batas klaim

- Latensi pemrosesan lokal benar-benar diukur pada mesin yang menjalankan
  eksperimen.
- Latensi jaringan adalah emulasi dari parameter konfigurasi, bukan
  pengukuran public cloud.
- Perbandingan edge–cloud terhadap cloud-only memakai pesan, pemrosesan,
  seed, dan draw jaringan terkonfigurasi yang sama; ini pembanding terkontrol,
  bukan uji public cloud.
- `freshness` benchmark adalah proksi jalur pemrosesan; umur kalender data
  historis dilaporkan terpisah melalui timestamp sumber.
- Seluruh 2.027.520 baris dipindai untuk audit lineage/kualitas, sedangkan
  benchmark default memproses 5.000 posisi merata. Ini bukan load test dua
  juta pesan.
- Tidak ada metrik akurasi/presisi model karena penelitian ini memantau nilai
  daya historis dan tidak menjalankan estimator.
- Energi merupakan turunan V×I dan okupansi berasal dari kolom legacy. Asal
  sensor lapangan serta perbandingan praktis terhadap meter kWh PLN dilaporkan
  oleh peneliti, tetapi paket ini belum memuat pasangan pembacaan meter
  awal–akhir untuk menghitung galat kalibrasi secara reproduktif.
- Koordinat EPSG:4326 berasal dari implementasi lama dan belum diverifikasi
  survei. Visualisasi menerapkan LoD aplikatif proyek—LoD-A tapak, LoD-B
  bangunan, dan LoD-C indoor 3D. Kepatuhan terhadap LoD geometrik CityGML,
  IndoorGML, IFC, atau 3D Tiles belum dievaluasi.
- Hasil tidak digeneralisasi ke banyak bangunan.
- Aliran telemetry saat ini satu arah. Berdasarkan taksonomi literatur,
  implementasi merupakan prototipe monitoring/digital shadow, belum Digital
  Twin operasional dua arah.
