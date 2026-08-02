# Dashboard Digital Twin Geospasial–Indoor Multiskala

Dashboard Vue dan Babylon.js ini adalah konsumen telemetry penelitian. UI
menampilkan daya legacy, energi kumulatif per siklus, okupansi, sumber,
blok/baris replay, routing, dan freshness lokal API sebagai proksi. Komponen
kamera, rekomendasi AC,
kontrol energi, histori palsu, estimator, fallback data acak, serta fallback
kontrak gateway lama telah dihapus.

Grafik menyimpan paling banyak 60 payload dan memakai timestamp sumber (dengan
fallback ke timestamp replay), bukan waktu polling browser. Energi sudah
dihitung di pipeline dari seluruh satu siklus sumber sebelum sampling, sehingga
dashboard hanya mengonsumsi hasil Wh berprovenance dan tidak mengintegrasikan
ulang sampel renggang. Nilai hilang ditampilkan sebagai `—`, bukan nol.

Tiga tab memakai payload yang sama:

- LoD-A, tapak geospasial: koordinat legacy EPSG:4326 dan rute edge–cloud;
- LoD-B, bangunan: energi, okupansi, serta aliran sensor–edge–API;
- LoD-C, indoor: scene Babylon dengan indikator sensor dan okupansi abstrak.

Ketiganya merupakan LoD aplikatif proyek dengan perpindahan tab manual.
Koordinat belum diverifikasi survei dan kepatuhan LoD geometrik standar belum
diuji.

## Menjalankan

Jalankan pipeline dan replay API dari root repositori:

```bash
python run_experiment.py
python -m src.replay.replay_server
```

Perintah tersebut memakai sampel kanonis yang dihasilkan pipeline. Untuk
membaca CSV 22 blok secara langsung saat server dimulai:

```bash
python -m src.replay.replay_server \
  --input Data/sensor_data.csv \
  --input-format historical_csv \
  --sample-size 5000
```

Kemudian:

```bash
npm ci
npm run dev
```

Default API adalah `http://127.0.0.1:8000/api`. Untuk endpoint lain:

```bash
VITE_TELEMETRY_API_URL=https://example.invalid/api npm run dev
```

Salin `.env.example` ke `.env.local` bila konfigurasi perlu dipertahankan pada
mesin lokal. `VITE_TELEMETRY_POLL_INTERVAL_MS` hanya mengubah kecepatan
presentasi replay, bukan interval pengukuran historis.

Endpoint harus menyediakan:

- `GET /telemetry/latest`
- envelope `{ success, data }`, dengan field `data` yang memenuhi
  `schemas/telemetry.schema.json` pada root repositori.

Jika endpoint tidak tersedia, dashboard menampilkan status tidak terhubung dan
tidak membuat data demo.

## Batas interpretasi

Label `historical_replay` berarti payload berasal dari pengulangan trace lama
dan digunakan sebagai workload arsitektur. Data ini bukan sensor live dan 22
blok bukan 22 pengukuran lapangan independen. Digital Twin adalah prototipe
monitoring satu arah; tiga skala visual tidak dengan sendirinya membuktikan
validasi lapangan, akurasi geospasial, atau performa public cloud.
