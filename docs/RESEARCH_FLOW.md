# Alur penelitian baru

```mermaid
flowchart TD
    A[Definisi scope dan pertanyaan penelitian] --> B[Audit trace asli 92.160 baris]
    A --> P[Audit CSV augmented 2.027.520 baris]
    P --> Q[Label 22 blok legacy_augmented_replay]
    B --> C[Ekstraksi parameter kalibrasi dan batas sensor]
    C --> D[Generator keadaan laten per skenario/run/seed]
    D --> E[Model observasi sensor, dropout, dan jitter]
    E --> F{Validasi diagnostik sintetis}
    F -->|Tidak memadai| C
    F -->|Memadai dan terdokumentasi| G[Split train validation test berbasis skenario]
    G --> H[Baseline V×I, median, Ridge, Random Forest]
    H --> I[Seleksi dari validation dan evaluasi test tertahan]
    I --> O[MAE RMSE R² dan 95% CI antarrun]
    O --> J[Model terpilih untuk inference]
    Q --> R[Sampel merata seluruh blok untuk workload arsitektur]
    R --> J
    J --> S[Benchmark komputasi lokal, serialisasi, routing, throughput]
    S --> K[Emulasi jaringan dengan label eksplisit]
    K --> L[Kontrak telemetry dan replay API]
    L --> M[Integrasi Digital Twin Web-3D]
    M --> N[Analisis sensitivitas, ancaman validitas, dan pelaporan]
```

Alur ini menggantikan gambar lama yang menyebut fusi multimodal dan kontrol.
Keduanya tidak didukung oleh bukti data dan bukan bagian dari scope penelitian
yang diperbarui.

Cabang sintetis menghasilkan bukti akurasi estimator. Cabang augmented
menghasilkan bukti workload arsitektur. Keduanya bertemu saat model terpilih
dijalankan pada jalur inference, tetapi metrik akurasi tidak pernah dihitung
dari data augmented.
