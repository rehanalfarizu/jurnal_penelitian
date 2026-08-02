# Model Web-3D Lokal

Dashboard memuat model glTF lokal berikut melalui Babylon.js:

- `3d twin/scene.gltf`: deskripsi scene dan referensi aset;
- `3d twin/scene.bin`: geometri biner;
- `3d twin/textures/`: tekstur yang dirujuk scene;
- `3d twin/license.txt`: atribusi dan lisensi CC-BY-4.0 aset.

Semua berkas tersebut harus dipertahankan bersama agar scene dapat dimuat dari
URL `/models/3d twin/scene.gltf`. Tidak ada ketergantungan pada Azure Blob atau
model GLB eksternal dalam implementasi penelitian saat ini.

Untuk verifikasi lokal:

```bash
npm ci
npm run dev
```

Kemudian periksa bahwa model tampil, tekstur termuat tanpa respons 404, dan
indikator visual telemetry berubah saat replay API mengirim payload baru.
