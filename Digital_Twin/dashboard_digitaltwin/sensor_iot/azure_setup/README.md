# Azure Telemetry — Catatan Reset

Folder ini hanya menyimpan fungsi yang berkaitan dengan ingest, penyimpanan,
ekspor, dan pembacaan telemetry:

- `MqttToIoTHub`
- `IoTHubToStorage`
- `AvroToTable`
- `SaveSensorData`
- `SavePeopleCount`
- `GetTelemetryData`
- `ExportSensorData`

Fungsi rekomendasi/kontrol AC telah dihapus karena berada di luar target
pemantauan daya.

Gunakan `.env.template` untuk membuat konfigurasi lokal. Jangan commit
connection string, function key, device key, atau password. Nama resource,
schema tabel, retry policy, dan clock synchronization harus didokumentasikan
ulang sebelum pengukuran.
