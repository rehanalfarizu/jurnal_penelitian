# Raspberry Pi People Counter

## Overview

Sistem people detection menggunakan USB webcam dan YOLO v3-tiny untuk menghitung jumlah orang dalam ruangan.

## Requirements

### Hardware

- Raspberry Pi 3/4/5
- USB Webcam (V4L2 compatible)
- Minimal 2GB RAM

### Software

- Raspberry Pi OS (Bullseye atau lebih baru)
- Python 3.7+
- OpenCV
- Flask
- paho-mqtt

## Instalasi

### 1. Copy File ke Raspberry Pi

```bash
scp people_counter_yolo.py [user]@[raspberry_pi_ip]:~/
scp requirements.txt [user]@[raspberry_pi_ip]:~/
```

### 2. Install Dependencies

```bash
ssh [user]@[raspberry_pi_ip]
pip3 install -r requirements.txt
```

### 3. Verifikasi Webcam

```bash
ls /dev/video*
v4l2-ctl --list-devices
```

## Konfigurasi

Edit file people_counter_yolo.py untuk mengubah:

```python
# Port webcam (0 = default)
WEBCAM_PORT = 0

# Port server streaming
STREAM_PORT = 5000

# Resolusi frame
FRAME_WIDTH = 320
FRAME_HEIGHT = 240

# MQTT Broker
MQTT_BROKER = "your-broker.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "your-username"
MQTT_PASSWORD = "your-password"
MQTT_TOPIC = "sensor/camera/people"

# Detection settings
CONFIDENCE_THRESHOLD = 0.5
PUBLISH_INTERVAL = 5
```

## Menjalankan

### Foreground Mode

```bash
python3 people_counter_yolo.py
```

### Background Mode

```bash
nohup python3 people_counter_yolo.py > webcam.log 2>&1 &
```

### Sebagai Service (Autostart)

Buat file /etc/systemd/system/people-counter.service:

```ini
[Unit]
Description=People Counter YOLO
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/[user]/people_counter_yolo.py
WorkingDirectory=/home/[user]
Restart=always
User=[user]

[Install]
WantedBy=multi-user.target
```

Aktifkan:

```bash
sudo systemctl enable people-counter
sudo systemctl start people-counter
```

## Endpoints

### Video Stream

```
http://[raspberry_pi_ip]:5000/video_feed
```

Format MJPEG, bisa langsung digunakan di tag img HTML.

### Status

```
http://[raspberry_pi_ip]:5000/status
```

Response JSON:
```json
{
  "status": "online",
  "people_count": 3,
  "mqtt_connected": true,
  "detection": "YOLO v3-tiny"
}
```

### Count API

```
http://[raspberry_pi_ip]:5000/count
```

Response JSON:
```json
{
  "count": 3,
  "mqtt": true
}
```

### Preview Page

```
http://[raspberry_pi_ip]:5000/
```

Halaman HTML dengan video stream dan counter realtime.

## Testing

### Test 1: Verifikasi Webcam

```bash
ls /dev/video*
```

Output: /dev/video0 atau serupa

### Test 2: Jalankan Script

```bash
python3 people_counter_yolo.py
```

Output yang diharapkan:
```
Initializing YOLO v3-tiny detector...
YOLO v3-tiny loaded successfully
Initializing camera...
Camera initialized
MQTT connected
Server running on port 5000
```

### Test 3: Akses Video Stream

Buka browser:
```
http://[raspberry_pi_ip]:5000/video_feed
```

Harus terlihat video stream dengan bounding box hijau di setiap orang.

### Test 4: Verifikasi MQTT

Check MQTT client atau dashboard apakah menerima data:
```json
{
  "deviceId": "RASPBERRY_PI_CAMERA_001",
  "jumlahOrang": 2,
  "timestamp": "2026-01-13T10:30:00",
  "location": "Ruang Server"
}
```

### Test 5: Test API

```bash
curl http://[raspberry_pi_ip]:5000/status
curl http://[raspberry_pi_ip]:5000/count
```

## Troubleshooting

### Webcam Tidak Terdeteksi

Cek koneksi USB dan jalankan:
```bash
lsusb
v4l2-ctl --list-devices
```

### YOLO Download Gagal

Download manual:
```bash
wget https://pjreddie.com/media/files/yolov3-tiny.weights
wget https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg
wget https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names
```

### MQTT Tidak Connect

Verifikasi credentials dan broker URL. Pastikan port 8883 tidak diblokir firewall.

### High CPU Usage

Kurangi resolusi atau tingkatkan SKIP_FRAMES di konfigurasi.

## Portable Setup

Untuk menggunakan di berbagai lokasi tanpa setup ulang network:

1. Konfigurasi multiple WiFi di /etc/wpa_supplicant/wpa_supplicant.conf:

```conf
country=ID
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="WiFi_Lokasi_1"
    psk="password1"
    priority=1
}

network={
    ssid="Hotspot_HP"
    psk="passwordhp"
    priority=10
}
```

2. Atau gunakan kabel Ethernet untuk koneksi langsung ke router.
