# Akuisisi Sensor IoT — Prototipe Lama

Isi folder ini dipertahankan karena masih relevan sebagai titik awal akuisisi
telemetry, tetapi belum divalidasi untuk eksperimen penelitian baru.

- `esp32_main.cpp` dan `platformio.ini`: firmware/perangkat edge.
- `azure_setup/azure-function/`: fungsi ingest, penyimpanan, dan pembacaan
  telemetry.
- `raspberry_pi/`: people counter lama; gunakan hanya jika occupancy secara
  eksplisit dipilih sebagai variabel penelitian.

Endpoint dan model rekomendasi AC telah dihapus. Jangan memasukkan credential
ke source control; mulai dari `.env.template`.

Eksperimen baru harus mencatat timestamp dan ID message yang sama pada sensor,
edge, cloud, dan dashboard agar latency serta kehilangan paket dapat dihitung.
