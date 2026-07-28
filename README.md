# Edge-Cloud Power Estimation for a Web-3D Digital Twin

Repositori penelitian untuk:

> **Arsitektur Edge-Cloud untuk Estimasi Daya Near Real-Time Bangunan Cerdas
> Terintegrasi Digital Twin Web-3D: Evaluasi Berbasis Data Sintetis
> Terkalibrasi**

## Status metodologi

Pipeline baru menggunakan **evaluasi berbasis simulasi**, dikalibrasi dari satu
trace sensor nyata berisi 92.160 baris. Hasilnya tidak boleh ditulis sebagai
validasi banyak bangunan, pengukuran Raspberry Pi baru, atau pengukuran public
cloud.

Data `Data/sensor_data.csv` berisi 2.027.520 baris augmentasi lama. File itu
merupakan 22 replay dari trace asli dengan beberapa transformasi, bukan 2 juta
observasi independen. Pipeline hanya menggunakannya sebagai workload benchmark
dan replay arsitektur; data tersebut tidak masuk training, validation, atau
test akurasi model.

## Struktur utama

- `configs/experiment.json` — skenario, seed, split, dan profil emulasi.
- `src/data/` — audit trace, generator sintetis, dan validasi diagnostik.
- `src/models/` — baseline serta evaluasi estimator.
- `src/benchmark/` — pengukuran komputasi lokal dan emulasi jaringan berlabel.
- `src/replay/` — API replay untuk integrasi Web-3D.
- `schemas/telemetry.schema.json` — kontrak telemetry.
- `Digital_Twin/` — firmware legacy, fungsi telemetry, dan dashboard Web-3D.
- `docs/METHODOLOGY.md` — metode dan ancaman validitas.
- `docs/RESEARCH_FLOW.md` — alur penelitian baru.
- `notebooks/01_evaluasi_final.ipynb` — ringkasan hasil final interaktif yang
  sudah dieksekusi.
- `results/final/` — laporan, visual, konfigurasi, metrik, dan manifest hash
  eksperimen final terkonfigurasi.
- `AUDIT_RESULTS.md` dan `LEGACY_PROJECT_AUDIT.md` — jejak keputusan reset.

## Menjalankan eksperimen

Siapkan Python 3.11+ dan dependensi:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Smoke test cepat:

```bash
python run_experiment.py --rows-per-run 600
python -m unittest discover -s tests
```

Eksperimen sesuai konfigurasi:

```bash
python run_experiment.py
python -m src.reporting.generate_figures --figures results/final/figures
python -m src.reporting.generate_final_report
```

Artefak dihasilkan ke `outputs/` dan tidak dilacak Git. Konfigurasi default
membuat lima skenario × empat run × 24 jam. Dua skenario digunakan untuk
training, satu untuk validation, dan dua skenario yang tidak terlihat selama
training digunakan sebagai test. Ringkasan yang siap ditinjau berada di
`results/final/RESULTS.md`.

Untuk membaca hasil secara interaktif:

```bash
jupyter lab notebooks/01_evaluasi_final.ipynb
```

Notebook menggunakan kernel `Python 3.11` dan membaca artefak
`results/final/`, sehingga tidak melatih ulang 493.700 baris ketika dibuka.

## Menjalankan replay dan Web-3D

Setelah pipeline menghasilkan model dan CSV:

```bash
python -m src.replay.replay_server
```

Perintah di atas mereplay data sintetis untuk membaca hasil estimasi. Untuk
demonstrasi workload augmented pada kontrak Web-3D:

```bash
python -m src.replay.replay_server \
  --input Data/sensor_data.csv \
  --input-format legacy_augmented
```

Pada terminal lain:

```bash
cd Digital_Twin/dashboard_digitaltwin/view_virtual
npm ci
npm run dev
```

Dashboard menggunakan `http://127.0.0.1:8000/api` secara default. Endpoint lain
dapat diatur melalui `VITE_TELEMETRY_API_URL`. Jangan commit credential atau
function key.

## Aturan pelaporan hasil

- Nyatakan daya firmware sebagai `V × I`; data nyata tidak memiliki faktor daya.
- Nyatakan data hasil generator sebagai `synthetic_calibrated`.
- Laporkan metrik keseluruhan dan per skenario/run.
- Bedakan latensi komputasi yang diukur dari latensi jaringan yang diemulasi.
- Gunakan CSV augmentasi lama hanya sebagai workload replay arsitektur.
- Jangan menggunakan CSV augmentasi lama sebagai train, validation, atau test
  akurasi model.
- Pertahankan `scenario_id`, `run_id`, `seed`, dan `source_type` pada turunan
  data.
