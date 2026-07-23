# Pilar 1 — Edge-Cloud Streaming

Modul ini adalah **delegasi** ke skrip di root repository dan
visualizer-nya. Tidak berdiri sendiri — semua kode asli hidup di
`../streaming_final.py` dan divisualisasikan oleh
`../streaming_visualizations.py`.

## Lokasi Kode Asli

| Komponen | Path Absolut |
|---|---|
| Skrip simulasi utama | `../streaming_final.py` |
| Generator 8 figure (PNG) | `../streaming_visualizations.py` |
| Dataset | `../Data/sensor_data.csv` (2.027.520 × 8) |
| Result summary | `streaming_results/streaming_metrics_v2.pkl` (symlink) |
| Result raw | `streaming_results/streaming_results_v2.pkl` (symlink, 288 MB, .gitignore) |
| Output figure | `../figures/01-08_*.png` (di-generate) |

## Cara Reproduksi

```bash
# dari root repo
CONDA_NO_PLUGINS=true .venv/bin/python -u streaming_final.py
CONDA_NO_PLUGINS=true .venv/bin/python -u streaming_visualizations.py
```

Atau dari sini:

```bash
CONDA_NO_PLUGINS=true ../.venv/bin/python -u ../streaming_final.py
```

Lihat juga: `../ARCHITECTURE_SPEC.md`, `../AUDIT_RESULTS.md`,
dan `../streaming_results/` (root pkl).

## Pilar dalam Sistem Terintegrasi

Pilar 1 adalah **lapisan transport dan routing** antara edge
(ESP32 + Raspberry Pi gateway) dan cloud (Azure Function + IoT
Hub). Layer ini menjamin setiap rekaman sensor:

1. Diproses lokal di edge dalam ≤ 1.3 ms (Ridge 19-fitur)
2. Di-route ke cloud hanya jika z-score ≥ 2.5 atau ada
   anomali fisik (suhu/kelembaban di luar rentang)
3. Disinkronkan ke Digital Twin (Layer 5) untuk visualisasi
   near real-time

Detail teknis ada di paper section 3 (System Architecture).

---
*Pemeliharaan: setiap perubahan pada Pilar 1 dilakukan
di `../streaming_final.py` (root). Folder ini adalah pointer
untuk kejelasan struktur "4 pilar".*
