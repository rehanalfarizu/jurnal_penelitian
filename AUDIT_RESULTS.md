# Audit dan Reset Penelitian

Tanggal audit: 28 Juli 2026

## Kesimpulan

Versi lama tidak layak dijadikan baseline hasil penelitian. Penyebab utamanya
adalah pencampuran simulasi dengan pengukuran nyata, target model yang tidak
sesuai judul, provenance dataset yang tidak lengkap, dan dokumentasi yang
bertentangan dengan kode.

## Temuan kritis

### 1. Latency dan throughput bukan hasil pengukuran end-to-end

`streaming_final.py` lama menetapkan latency edge dari konstanta total 1,3 ms
dan latency cloud dari konstanta komponen jaringan/komputasi/sinkronisasi.
Distribusi kemudian dibuat dengan noise Gaussian dan clipping. Throughput
"edge node" dihitung balik dari jumlah latency sintetis tersebut.

Naskah lama, sebaliknya, menyebut angka itu sebagai pengukuran Raspberry Pi
dan sistem Azure nyata. Klaim 1,3 ms, sekitar 321 ms, 246×, 15.729 record/s,
dan 52.400× headroom karena itu tidak boleh digunakan.

### 2. Evaluasi streaming tidak benar-benar memprediksi setiap record

Prediksi Ridge dijalankan satu kali setiap 50 record. Hanya sekitar 2% record
yang mempunyai prediksi, tetapi hasilnya dipakai untuk mendukung klaim sistem
streaming keseluruhan.

### 3. Model rekomendasi AC tidak sesuai target penelitian

Target rekomendasi suhu AC dibuat oleh fungsi aturan manual, lalu model
Gradient Boosting dilatih untuk meniru aturan tersebut dengan random split.
Itu bukan estimasi daya near real-time dan bukan ground truth hasil observasi.
Dataset yang dirujuk script training juga tidak tersedia pada path tersebut.

### 4. Scope penelitian melebar tanpa dukungan data

Dokumen lama menambahkan YOLO, multimodal fusion, Transformer, GNN, Kalman
filter, Informer, anomaly routing, dan kontrol AC. Sebagian besar tidak
diimplementasikan atau tidak diperlukan oleh judul. Kompleksitas ini menutupi
pertanyaan penelitian inti.

### 5. Dataset augmented bukan observasi independen

`Data/sensor_data.csv` berisi 2.027.520 record dari satu device, rentang
23 Februari–24 Mei 2026. Audit lokal menemukan:

- 2.027.520 timestamp unik dan terurut;
- 87.890 kombinasi payload sensor unik;
- sekitar 95,67% record mengulang kombinasi nilai sensor yang pernah muncul;
- cadence dominan sekitar 3,4–3,6 detik;
- daya 25,4–484,0 W, dengan mean sekitar 36,93 W;
- hanya satu `DeviceID`.

Workbook asli kemudian tersedia pada
`Data/sensor_data_export_2026-05-17_to_2026-05-23.xlsx`: 92.160 baris dari satu
gateway, dengan waktu aktual sekitar 19–23 Mei 2026. Perbandingan posisi
menunjukkan CSV 2.027.520 baris sama dengan 22 replay dari 92.160 baris.
Sebagian nilai nol diimputasi dan jumlah orang diubah, tetapi mayoritas kolom
sensor tetap identik. Timestamp hasil replay bahkan ditempatkan sebelum waktu
akuisisi asli.

Script yang benar-benar mengubah data sekitar 93 ribu menjadi 2.027.520 baris
tidak ditemukan. Dokumentasi lama hanya menyebut interpolasi deret waktu,
Gaussian noise, dan magnitude warping. Dataset 2 juta dipertahankan hanya
sebagai bukti audit legacy. Pipeline baru tidak membacanya untuk training,
validasi, test, ataupun benchmark.

### 6. Istilah target bercampur

Kode memprediksi daya sesaat dalam watt, sedangkan dokumen berulang kali
menyebut "energy prediction". Daya (W) dan energi (Wh/kWh) adalah target yang
berbeda dan harus dipisahkan.

### 7. Digital Twin lama belum tervalidasi sebagai twin

Web viewer lama menampilkan model 3D dan telemetry, tetapi juga mempunyai
dummy fallback, komponen rekomendasi AC, dan beberapa jalur API. Komponen
tersebut sekarang telah dihapus. Dashboard baru hanya mengonsumsi kontrak
telemetry dengan provenance eksplisit; ia tetap merupakan lapisan visualisasi,
bukan bukti akurasi model atau deployment cloud.

## Yang dihapus

- kode streaming/simulasi dan visualisasinya;
- seluruh PKL hasil eksperimen, model lama, grafik, log, dan backup;
- draf paper serta dokumen arsitektur yang memuat klaim tidak valid;
- modul rekomendasi AC dan Azure Function terkait;
- wrapper folder pilar yang hanya berupa symlink;
- virtual environment, `node_modules`, build `dist`, cache, dan `.DS_Store`;
- arsip eksperimen lama setelah ekspor Scopus diselamatkan;
- referensi yang jelas di luar domain inti (heritage conservation,
  shipbuilding, EV charging, edge multimodal LLM, building-function remote
  sensing, farmland energy, dan data-center optimization);
- kredensial/config lokal `.env` dan file identitas subscription lokal.

## Baseline metodologi yang diterapkan saat renewal

Pertanyaan inti yang lebih defensible:

> Seberapa baik estimasi daya pada workload sintetis terkalibrasi, dan bagaimana
> karakteristik komputasi lokal serta profil jaringan teremulasi memengaruhi
> pembaruan Digital Twin Web-3D?

Implementasi baru:

1. audit otomatis trace asli dan karakteristik sampling;
2. generator keadaan laten serta observasi sensor per skenario/run/seed;
3. pemisahan `true_*` dari `observed_*`;
4. baseline median, `V × I`, Ridge, dan Random Forest;
5. test split berdasarkan run lengkap;
6. benchmark komputasi lokal terukur dan jaringan teremulasi yang diberi label;
7. kontrak telemetry dan replay API untuk Web-3D;
8. MAE/RMSE/R² serta P50/P95/P99, payload, drop, deadline miss, dan proxy
   staleness.

Kode baru berada di `src/`, konfigurasi di `configs/experiment.json`, dan
metode lengkap di `docs/METHODOLOGY.md`.

Tidak ada hasil lama yang boleh disalin ke paper baru tanpa pengukuran ulang.
