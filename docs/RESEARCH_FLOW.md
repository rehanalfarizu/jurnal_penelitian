# Alur evaluasi Digital Twin edge–cloud multiskala

```mermaid
flowchart TD
    A[Definisi scope dan batas klaim] --> B[Audit trace asli 92.160 observasi]
    A --> C[Audit nilai CSV workload 2.027.520 baris]
    B --> D[Definisi daya legacy V×I, integral energi, dan okupansi]
    C --> E[Buktikan 22 blok identik dan audit perubahan vs XLSX]
    D --> E
    E --> F[Label blok turunan + replay ID, ancestry posisi, dan dua timestamp]
    F --> G[Sampel merata seluruh blok]
    G --> H[Validasi nilai + energi Wh + status okupansi]
    H --> I{Aturan routing}
    I -->|Normal| J[Jalur edge]
    I -->|Invalid, arus rendah, atau daya > P99| K[Jalur cloud terkonfigurasi]
    J --> L[Serialisasi kontrak telemetry]
    K --> L
    H --> K2[Baseline cloud-only dengan profil yang sama]
    L --> M[Kontrak API berprovenance]
    M --> N1[Skala tapak geospasial]
    M --> N2[Skala bangunan]
    M --> N3[Skala indoor Babylon]
    L --> O[Benchmark latency throughput freshness dan deadline]
    K2 --> O
    N1 --> P[Analisis kinerja dan ancaman validitas]
    N2 --> P
    N3 --> P
    O --> P
    P --> Q[Sintesis jurnal dan audit referensi]
```

Alur tidak memuat generator sintetis, train–validation–test, atau estimator
daya. Seluruh 2.027.520 baris CSV dipindai untuk audit lineage dan kualitas;
benchmark hanya memproses 5.000 posisi merata. Karena 22 blok mempunyai payload
identik, CSV tidak memberi 22 variasi observasi baru. Unit analisis lapangan
tetap trace sumber 92.160 observasi dari satu gateway. Energi adalah integral
proksi V×I per siklus dan okupansi berasal dari data legacy. Integrasi tiga
skala berorientasi monitoring satu arah dengan LoD-A tapak, LoD-B bangunan,
dan LoD-C indoor. Hirarki LoD aplikatif tersebut belum diuji sebagai kepatuhan
LoD geometrik CityGML/IndoorGML/IFC/3D Tiles, dan sistem belum membuktikan
Digital Twin operasional dua arah.
