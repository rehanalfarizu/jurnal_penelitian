# Pilar 2 — Multimodal Fusion

Modul ini adalah **delegasi** ke sub-modul di bawah
`../Digital_Twin/dashboard_digitaltwin/sensor_iot/`. Tidak berdiri
sendiri — kode asli (ESP32 C++ + YOLO Python) tinggal di sana.

## Lokasi Kode Asli

| Komponen | Path |
|---|---|
| Modality numerik (DHT11, ZMPT101B, SCT013) | `../Digital_Twin/dashboard_digitaltwin/sensor_iot/esp32_main.cpp` |
| PlatformIO config | `../Digital_Twin/dashboard_digitaltwin/sensor_iot/platformio.ini` |
| Modality visual (YOLOv3-tiny people counter) | `../Digital_Twin/dashboard_digitaltwin/sensor_iot/raspberry_pi/people_counter_yolo.py` |
| Downloader YOLO weights | `../Digital_Twin/dashboard_digitaltwin/sensor_iot/raspberry_pi/download_yolo.py` |
| COCO class names | `../Digital_Twin/dashboard_digitaltwin/sensor_iot/raspberry_pi/coco.names` |
| YOLO config | `../Digital_Twin/dashboard_digitaltwin/sensor_iot/raspberry_pi/yolov3-tiny.cfg` |

Symlink di folder ini adalah pointer `ln -s` ke file yang sama —
tidak ada duplikasi.

## Dua Modalitas yang Difusikan

1. **Numerik** (ESP32, edge): suhu (DHT11), tegangan (ZMPT101B),
   arus (SCT013), daya turunan, jumlah orang dummy. Sampling
   ~1 Hz dari gateway MQTT ke Azure IoT Hub. Feature schema
   5-kolom untuk `energy_forecast_model.pkl`.
2. **Visual** (Raspberry Pi + PiCamera): manusia dihitung oleh
   YOLOv3-tiny (cfg + weights, total ~33 MB). Output `count`
   digabung dengan feature numerik via bobot fusion 0.15
   (lihat `streaming_final.py` CONFIG.fuse_weights.orang).

## Fusion Rule (di Edge)

```python
# streaming_final.py CONFIG
fuse_weights = {
    "suhu": 0.30,
    "kelembaban": 0.25,
    "daya": 0.30,
    "orang": 0.15,
}
```

Hasil fusion dipakai sebagai feature input Ridge di Pilar 1.
Aturan terperinci ada di `../streaming_final.py` method
`EdgeStreamingNode._compute_anomaly_score()`.

## Cara Reproduksi

```bash
# Download weights YOLO (sekali, ~33 MB)
CONDA_NO_PLUGINS=true ../.venv/bin/python -u ../Digital_Twin/dashboard_digitaltwin/sensor_iot/raspberry_pi/download_yolo.py

# Run people counter (butuh PiCamera live atau video)
CONDA_NO_PLUGINS=true ../.venv/bin/python ../Digital_Twin/dashboard_digitaltwin/sensor_iot/raspberry_pi/people_counter_yolo.py
```

---
*Pemeliharaan: perubahan pada Pilar 2 dilakukan di folder
sensor_iot yang asli. Folder ini hanya pointer struktural.*
