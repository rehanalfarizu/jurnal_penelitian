# Digital Twin Research Integration

Folder ini memisahkan dua jenis artefak:

- `sensor_iot/` adalah kode akuisisi legacy untuk menjelaskan asal dan batas
  sensor. Kode tersebut bukan implementasi edge yang diklaim telah diuji ulang.
- `view_virtual/` adalah dashboard Vue/Babylon.js yang sudah diselaraskan
  dengan kontrak telemetry penelitian baru.

Model rekomendasi/kontrol AC, endpoint terkait, kamera dashboard, data demo
acak, histori palsu, dan komponen admin lama telah dihapus karena berada di luar
scope estimasi daya.

Dashboard menerima payload dari replay API di `src/replay/replay_server.py`.
Payload memisahkan nilai observasi dan estimasi, serta membawa `source_type`,
`scenario_id`, `run_id`, nama model, scope model, dan timestamp.

Azure Functions yang tersisa adalah bahan provenance dari sistem lama. Pipeline
eksperimen baru tidak bergantung pada Azure dan tidak mengklaim bahwa benchmark
lokal adalah pengukuran Azure atau Raspberry Pi.

Lihat:

- `../../docs/METHODOLOGY.md`
- `../../schemas/telemetry.schema.json`
- `../../LEGACY_PROJECT_AUDIT.md`
