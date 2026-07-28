# Web-3D Research Dashboard

Dashboard Vue dan Babylon.js ini adalah konsumen telemetry penelitian. UI
menampilkan observasi sensor, estimasi daya, sumber data, skenario, run, dan
scope model. Komponen kamera, rekomendasi AC, kontrol energi, histori palsu,
serta fallback data acak telah dihapus.

## Menjalankan

Jalankan pipeline dan replay API dari root repositori:

```bash
python run_experiment.py --rows-per-run 600
python -m src.replay.replay_server
```

Mode tersebut mereplay `synthetic_calibrated`. Untuk memperagakan workload
arsitektur dari 22 blok augmented:

```bash
python -m src.replay.replay_server \
  --input Data/sensor_data.csv \
  --input-format legacy_augmented
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

Endpoint harus menyediakan:

- `GET /telemetry/latest`
- respons sesuai `schemas/telemetry.schema.json` pada root repositori.

Jika endpoint tidak tersedia, dashboard menampilkan status tidak terhubung dan
tidak membuat data demo.

## Batas interpretasi

Label `synthetic_calibrated` berarti replay berasal dari simulasi terkalibrasi.
Label `legacy_augmented_replay` berarti data berasal dari pengulangan trace lama
dan hanya digunakan sebagai workload arsitektur. Keduanya bukan sensor live.
Digital Twin adalah lapisan visualisasi; tampilan Web-3D tidak dengan sendirinya
membuktikan akurasi model maupun performa cloud.
