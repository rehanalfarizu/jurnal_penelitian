# Setup YOLO di Raspberry Pi

## File YOLO yang Dibutuhkan

Untuk menjalankan people detection, Anda membutuhkan 3 file YOLO v3-tiny:

1. **yolov3-tiny.cfg** (konfigurasi model)
2. **yolov3-tiny.weights** (33.8 MB - model weight)
3. **coco.names** (daftar 80 objek yang bisa dideteksi)

## Cara Download di Raspberry Pi

### Opsi 1: Otomatis (Recommended)

```bash
# Transfer script ke Raspberry Pi
scp download_yolo.py pi@[raspberry_pi_ip]:~/

# SSH ke Raspberry Pi
ssh pi@[raspberry_pi_ip]

# Jalankan script download
python3 download_yolo.py
```

### Opsi 2: Download Manual

```bash
# Di Raspberry Pi, jalankan:
wget https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg
wget https://pjreddie.com/media/files/yolov3-tiny.weights
wget https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names
```

### Opsi 3: Transfer dari Komputer

Jika sudah download di komputer ini (d:\dashboard_digitaltwin\sensor iot\raspberry-pi):

```bash
# Transfer file ke Raspberry Pi
scp yolov3-tiny.cfg pi@[raspberry_pi_ip]:~/
scp yolov3-tiny.weights pi@[raspberry_pi_ip]:~/
scp coco.names pi@[raspberry_pi_ip]:~/
```

## Verifikasi Download

Setelah download, pastikan semua file ada:

```bash
ls -lh yolov3-tiny.*  coco.names
```

Output yang benar:
```
-rw-r--r-- 1 pi pi  610 Jan 25 yolov3-tiny.cfg
-rw-r--r-- 1 pi pi  34M Jan 25 yolov3-tiny.weights
-rw-r--r-- 1 pi pi  625 Jan 25 coco.names
```

## Jalankan People Counter

Setelah file YOLO ready:

```bash
# Test sederhana
python3 test_camera_connection.py

# Jalankan people detection penuh
python3 people_counter_yolo.py

# Atau dengan test mode
python3 people_counter_yolo.py --test
```

## Troubleshooting

### Download Gagal di Raspberry Pi

Jika koneksi internet lambat atau tidak stabil:

1. **Download di komputer** (sudah berhasil ✅)
2. **Transfer ke Raspberry Pi** menggunakan SCP
3. Atau gunakan USB flash drive untuk copy manual

### File Tidak Ditemukan

Pastikan file berada di direktori yang sama dengan script Python:
```bash
cd ~
ls -la *.cfg *.weights *.names
```

### Performa Lambat

YOLO v3-tiny sudah dioptimasi untuk Raspberry Pi dengan:
- Input size: 160x160 (kecil untuk performa)
- Skip frames: Process setiap 5 frame
- Confidence threshold: 50%

## Informasi File

**Kenapa YOLO v3-tiny?**
- Lebih ringan dari YOLO full (33MB vs 248MB)
- Lebih cepat di Raspberry Pi
- Akurasi masih bagus untuk people detection
- FPS lebih tinggi (sekitar 2-5 FPS di RPi 4)

**COCO Dataset**
- 80 kelas objek (person, car, dog, dll)
- People detection menggunakan kelas "person"
