# Digital Twin Research Integration

Folder ini memisahkan dua jenis artefak:

- `sensor_iot/` adalah kode akuisisi legacy untuk menjelaskan asal dan batas
  sensor. Kode tersebut bukan implementasi edge yang diklaim telah diuji ulang.
- `view_virtual/` adalah dashboard Vue/Babylon.js yang sudah diselaraskan
  dengan kontrak telemetry penelitian baru.

Model rekomendasi/kontrol AC, endpoint terkait, kamera dashboard, data demo
acak, histori palsu, dan komponen admin lama telah dihapus karena berada di
luar scope monitoring energi dan okupansi.

Dashboard menerima payload dari replay API di `src/replay/replay_server.py`.
Payload membawa nilai daya legacy, energi Wh per siklus, okupansi, status
sensor, konteks tiga skala, keputusan routing, timestamp sumber/replay,
`replay_id`, dan `source_row_id`.
`source_row_id` hanya menyatakan ancestry posisi; audit nilai menunjukkan
trace replay berasal dari data lama yang telah ditransformasi, bukan salinan
mentah workbook. Tidak ada estimasi ML pada kontrak aktif.

Integrasi saat ini bersifat satu arah: dashboard memvisualisasikan telemetry
yang sama pada LoD-A tapak geospasial, LoD-B bangunan, dan LoD-C indoor 3D.
Ketiganya adalah LoD aplikatif proyek; koordinat legacy dan kepatuhan LoD
geometrik standar belum divalidasi. Karena belum ada kontrol balik ke aset
fisik, implementasi ini lebih
tepat disebut **prototipe Digital Twin berorientasi monitoring/digital
shadow**, bukan Digital Twin operasional penuh.

Azure Functions yang tersisa adalah bahan provenance dari sistem lama. Pipeline
eksperimen baru tidak bergantung pada Azure dan tidak mengklaim bahwa benchmark
lokal adalah pengukuran Azure atau Raspberry Pi.

Lihat:

- `../../docs/METHODOLOGY.md`
- `../../schemas/telemetry.schema.json`
- `../../LEGACY_PROJECT_AUDIT.md`
