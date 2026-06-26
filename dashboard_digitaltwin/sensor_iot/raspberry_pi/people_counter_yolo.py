#!/usr/bin/env python3
"""
USB Webcam dengan People Detection AKURAT
Menggunakan YOLO v3-tiny + Face Detection
Terintegrasi dengan Azure IoT Hub
"""

import cv2
from flask import Flask, Response
from flask_cors import CORS
import threading
import time
import json
import os
import ssl
from datetime import datetime
import numpy as np
import hmac
import hashlib
import base64
import urllib.parse

# Production WSGI server (lebih stabil dari Flask dev server)
try:
    from waitress import serve
    WAITRESS_AVAILABLE = True
except ImportError:
    WAITRESS_AVAILABLE = False
    print("⚠️  Waitress not installed. Run: pip install waitress")

# Azure IoT Hub SDK (optional - fallback ke MQTT jika tidak ada)
try:
    from azure.iot.device import IoTHubDeviceClient, Message
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False
    import paho.mqtt.client as mqtt

# ===== KONFIGURASI =====
WEBCAM_PORT = 0  # /dev/video0 - FHD Webcam
STREAM_PORT = 5000
FRAME_WIDTH = 1280  # HD 720p untuk lokal
FRAME_HEIGHT = 720
TARGET_FPS = 60  # FPS maksimal untuk ultra smooth

# ===== AZURE IoT Hub Configuration =====
IOT_HUB_NAME = os.getenv("IOT_HUB_NAME", "")
DEVICE_ID = os.getenv("IOT_DEVICE_ID", "RASPBERRY_PI_CAMERA_001")
DEVICE_KEY = os.getenv("IOT_DEVICE_KEY", "")

# Connection string format (alternatif)
# CONNECTION_STRING = "HostName=iothub-digitaltwin-2026.azure-devices.net;DeviceId=RASPBERRY_PI_CAMERA_001;SharedAccessKey=YOUR_KEY"

# ===== DETECTION =====
CONFIDENCE_THRESHOLD = 0.40  # 40% confidence - filter false positive
NMS_THRESHOLD = 0.4  # Non-maximum suppression
PUBLISH_INTERVAL = 5
INPUT_SIZE = 416  # YOLO input size (lebih besar untuk HD)
SKIP_FRAMES = 2  # Proses detection setiap 2 frame untuk smooth detection
MIN_FACE_SIZE = 50  # Minimum ukuran wajah (lebih kecil)
MIN_ASPECT_RATIO = 0.5  # Rasio minimum
MAX_ASPECT_RATIO = 2.0  # Rasio maksimum
MIN_PERSON_HEIGHT = 100  # Minimum tinggi box untuk dianggap orang

# ===== INISIALISASI =====
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": "*", "supports_credentials": True}})

# Cached snapshot untuk performance
cached_snapshot = None
cached_snapshot_time = 0
SNAPSHOT_CACHE_MS = 100  # Cache snapshot selama 100ms

# Add CORS headers to all responses
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, ngrok-skip-browser-warning'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

camera = None
output_frame = None
lock = threading.Lock()
people_count = 0
iot_client = None
iot_connected = False
net = None
output_layers = None
classes = None
face_cascade = None  # Haar Cascade untuk face detection

def download_yolo_files():
    """Download YOLO v3-tiny files (lebih ringan untuk Raspberry Pi)"""
    import os
    import urllib.request
    
    files = {
        'yolov3-tiny.cfg': 'https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg',
        'yolov3-tiny.weights': 'https://pjreddie.com/media/files/yolov3-tiny.weights',
        'coco.names': 'https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names'
    }
    
    for filename, url in files.items():
        if not os.path.exists(filename):
            print(f"📥 Downloading {filename}...")
            try:
                urllib.request.urlretrieve(url, filename)
                print(f"✓ {filename} downloaded")
            except Exception as e:
                print(f"✗ Error downloading {filename}: {e}")
                return False
    
    return True

def init_yolo():
    """Inisialisasi YOLO v3-tiny (lebih ringan)"""
    global net, output_layers, classes
    
    print("🤖 Initializing YOLO v3-tiny detector...")
    
    if not download_yolo_files():
        print("✗ Failed to download YOLO files")
        return False
    
    try:
        # Load YOLO v3-tiny
        net = cv2.dnn.readNet("yolov3-tiny.weights", "yolov3-tiny.cfg")
        
        # Set backend and target
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        
        # Get output layers
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
        
        # Load class names
        with open("coco.names", "r") as f:
            classes = [line.strip() for line in f.readlines()]
        
        print("✓ YOLO v3-tiny loaded successfully")
        print(f"  Classes: {len(classes)}")
        print(f"  Output layers: {len(output_layers)}")
        return True
        
    except Exception as e:
        print(f"✗ Error loading YOLO: {e}")
        return False

def init_face_detector():
    """Inisialisasi Haar Cascade Face Detector"""
    global face_cascade
    
    print("👤 Initializing Face Detector...")
    
    try:
        # Gunakan Haar Cascade bawaan OpenCV
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if face_cascade.empty():
            print("✗ Failed to load face cascade")
            return False
        
        print("✓ Face detector loaded successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error loading face detector: {e}")
        return False

# ===== AZURE IoT Hub Functions =====
def generate_sas_token(uri, key, expiry=3600):
    """Generate SAS token untuk Azure IoT Hub authentication"""
    ttl = int(time.time()) + expiry
    sign_key = f"{uri}\n{ttl}"
    signature = base64.b64encode(
        hmac.new(base64.b64decode(key), sign_key.encode('utf-8'), hashlib.sha256).digest()
    ).decode('utf-8')
    return f"SharedAccessSignature sr={uri}&sig={urllib.parse.quote(signature, safe='')}&se={ttl}"

def init_azure_iot():
    """Inisialisasi koneksi ke Azure IoT Hub"""
    global iot_client, iot_connected

    if not IOT_HUB_NAME or not DEVICE_KEY:
        print("✗ Azure IoT credentials belum dikonfigurasi.")
        print("  Set environment variables: IOT_HUB_NAME, IOT_DEVICE_ID, IOT_DEVICE_KEY")
        return False
    
    print("☁️  Initializing Azure IoT Hub...")
    
    if AZURE_SDK_AVAILABLE:
        # Gunakan Azure IoT SDK
        try:
            connection_string = f"HostName={IOT_HUB_NAME}.azure-devices.net;DeviceId={DEVICE_ID};SharedAccessKey={DEVICE_KEY}"
            iot_client = IoTHubDeviceClient.create_from_connection_string(connection_string)
            iot_client.connect()
            iot_connected = True
            print("✓ Azure IoT Hub connected (SDK)")
            return True
        except Exception as e:
            print(f"⚠️  Azure SDK error: {e}")
            print("   Trying MQTT fallback...")
    
    # Fallback ke MQTT langsung
    try:
        import paho.mqtt.client as mqtt
        
        # Azure IoT Hub MQTT settings
        mqtt_host = f"{IOT_HUB_NAME}.azure-devices.net"
        mqtt_port = 8883
        username = f"{IOT_HUB_NAME}.azure-devices.net/{DEVICE_ID}/?api-version=2021-04-12"
        
        # Generate SAS token
        resource_uri = urllib.parse.quote(f"{IOT_HUB_NAME}.azure-devices.net/devices/{DEVICE_ID}", safe='')
        sas_token = generate_sas_token(resource_uri, DEVICE_KEY)
        
        def on_connect(client, userdata, flags, rc):
            global iot_connected
            if rc == 0:
                iot_connected = True
                print("✓ Azure IoT Hub connected (MQTT)")
            else:
                print(f"✗ Connection failed with code {rc}")
        
        def on_disconnect(client, userdata, rc):
            global iot_connected
            iot_connected = False
            print("⚠️  Azure IoT Hub disconnected")
        
        iot_client = mqtt.Client(client_id=DEVICE_ID, protocol=mqtt.MQTTv311)
        iot_client.username_pw_set(username, sas_token)
        iot_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        iot_client.on_connect = on_connect
        iot_client.on_disconnect = on_disconnect
        
        iot_client.connect(mqtt_host, mqtt_port, 60)
        iot_client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        return iot_connected
        
    except Exception as e:
        print(f"✗ Azure IoT Hub error: {e}")
        return False

def publish_people_count(count):
    """Kirim data people count ke Azure IoT Hub"""
    global iot_client, iot_connected
    
    if not iot_connected or iot_client is None:
        return
    
    try:
        payload = {
            "deviceId": DEVICE_ID,
            "jumlahOrang": count,
            "timestamp": datetime.now().isoformat(),
            "location": "Ruang Server",
            "sensorType": "camera_people_counter"
        }
        
        if AZURE_SDK_AVAILABLE and hasattr(iot_client, 'send_message'):
            # Gunakan Azure SDK
            message = Message(json.dumps(payload))
            message.content_encoding = "utf-8"
            message.content_type = "application/json"
            iot_client.send_message(message)
        else:
            # Gunakan MQTT
            topic = f"devices/{DEVICE_ID}/messages/events/"
            iot_client.publish(topic, json.dumps(payload), qos=1)
        
        print(f"☁️  Azure IoT: {count} orang terdeteksi")
        
    except Exception as e:
        print(f"✗ Azure publish error: {e}")

def init_camera():
    global camera
    print("🎥 Initializing camera...")
    
    # Coba beberapa video device
    video_ports = [0, 1, '/dev/video0', '/dev/video1']
    
    for port in video_ports:
        print(f"   Trying {port}...")
        camera = cv2.VideoCapture(port, cv2.CAP_V4L2)
        if camera.isOpened():
            # Test read
            ret, frame = camera.read()
            if ret and frame is not None:
                print(f"   ✓ Found camera at {port}")
                break
            camera.release()
        camera = None
    
    if camera is None:
        # Fallback tanpa V4L2
        for port in [0, 1]:
            print(f"   Trying {port} (no V4L2)...")
            camera = cv2.VideoCapture(port)
            if camera.isOpened():
                ret, frame = camera.read()
                if ret and frame is not None:
                    print(f"   ✓ Found camera at {port}")
                    break
                camera.release()
            camera = None
    
    if camera is None or not camera.isOpened():
        print("✗ Cannot open camera")
        return False
    
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    camera.set(cv2.CAP_PROP_FPS, TARGET_FPS)  # Set FPS target
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer untuk kurangi lag
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    
    # Warm-up
    for _ in range(5):
        ret, _ = camera.read()
        if ret:
            break
        time.sleep(0.5)
    
    print(f"✓ Camera initialized ({FRAME_WIDTH}x{FRAME_HEIGHT} @ {TARGET_FPS}fps)")
    return True

def detect_people_yolo(frame):
    """Deteksi orang dengan YOLO v3-tiny"""
    global net, output_layers, classes
    
    if net is None:
        print("⚠️  YOLO net is None - model tidak ter-load!")
        return 0, frame
    
    height, width = frame.shape[:2]
    
    # Prepare input blob dengan size lebih kecil untuk speed
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (INPUT_SIZE, INPUT_SIZE), swapRB=True, crop=False)
    net.setInput(blob)
    
    # Forward pass
    outputs = net.forward(output_layers)
    
    # Process detections
    boxes = []
    confidences = []
    class_ids = []
    
    # Debug: count all detections
    total_detections = 0
    person_detections = 0
    
    for output in outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            total_detections += 1
            
            # Filter: only person class (class_id = 0 in COCO) and confidence threshold
            if class_id == 0 and confidence > CONFIDENCE_THRESHOLD:
                person_detections += 1
                # Get bounding box
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                
                # Filter: tinggi minimum untuk orang (bukan objek kecil)
                if h < MIN_PERSON_HEIGHT:
                    continue
                
                # Filter: aspect ratio manusia (tinggi > lebar biasanya)
                aspect = h / w if w > 0 else 0
                if aspect < 0.5 or aspect > 4.0:  # Orang biasanya portrait
                    continue
                
                # Rectangle coordinates
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)
    
    # Debug print setiap beberapa frame
    if len(boxes) > 0:
        print(f"🔍 Detected {len(boxes)} person(s) with confidences: {[f'{c:.2f}' for c in confidences]}")
    
    # Apply Non-Maximum Suppression
    indices = cv2.dnn.NMSBoxes(boxes, confidences, CONFIDENCE_THRESHOLD, NMS_THRESHOLD)
    
    people_detected = 0
    if len(indices) > 0:
        for i in indices.flatten():
            x, y, w, h = boxes[i]
            confidence = confidences[i]
            
            # Bounding box dengan warna hijau terang dan tebal
            color = (0, 255, 0)  # Hijau
            thickness = 3
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
            
            # Garis sudut untuk memperjelas detection
            corner_len = min(30, w // 4, h // 4)
            corner_color = (0, 255, 255)  # Kuning
            corner_thickness = 4
            
            # Top-left corner
            cv2.line(frame, (x, y), (x + corner_len, y), corner_color, corner_thickness)
            cv2.line(frame, (x, y), (x, y + corner_len), corner_color, corner_thickness)
            # Top-right corner
            cv2.line(frame, (x + w, y), (x + w - corner_len, y), corner_color, corner_thickness)
            cv2.line(frame, (x + w, y), (x + w, y + corner_len), corner_color, corner_thickness)
            # Bottom-left corner
            cv2.line(frame, (x, y + h), (x + corner_len, y + h), corner_color, corner_thickness)
            cv2.line(frame, (x, y + h), (x, y + h - corner_len), corner_color, corner_thickness)
            # Bottom-right corner
            cv2.line(frame, (x + w, y + h), (x + w - corner_len, y + h), corner_color, corner_thickness)
            cv2.line(frame, (x + w, y + h), (x + w, y + h - corner_len), corner_color, corner_thickness)
            
            # Label dengan background yang jelas
            label = f"ORANG {people_detected + 1}: {int(confidence * 100)}%"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            font_thickness = 2
            label_size, base_line = cv2.getTextSize(label, font, font_scale, font_thickness)
            
            # Background label
            label_y = max(y - 10, label_size[1] + 10)
            cv2.rectangle(frame, (x, label_y - label_size[1] - 8), 
                         (x + label_size[0] + 10, label_y + 4), (0, 0, 0), cv2.FILLED)
            cv2.rectangle(frame, (x, label_y - label_size[1] - 8), 
                         (x + label_size[0] + 10, label_y + 4), color, 2)
            cv2.putText(frame, label, (x + 5, label_y - 4), 
                       font, font_scale, (255, 255, 255), font_thickness)
            
            people_detected += 1
    
    # Tidak ada text overlay besar - biarkan video bersih
    
    return people_detected, frame

# Variabel untuk tracking box stabil
last_face_boxes = []
last_detection_time = 0
DETECTION_TIMEOUT = 0.5  # 500ms timeout - box lebih stabil

def is_valid_face(x, y, w, h):
    """Filter untuk memastikan deteksi adalah wajah yang valid"""
    # Filter berdasarkan ukuran minimum
    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
        return False
    
    # Filter berdasarkan aspect ratio (wajah biasanya hampir kotak)
    aspect_ratio = w / h if h > 0 else 0
    if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
        return False
    
    return True

def detect_faces(frame):
    """Deteksi wajah dengan Haar Cascade - untuk close-up view"""
    global face_cascade, last_face_boxes, last_detection_time
    
    if face_cascade is None:
        return 0, frame
    
    current_time = time.time()
    height, width = frame.shape[:2]
    
    # Resize untuk processing lebih cepat
    scale = 0.5
    small_frame = cv2.resize(frame, (int(width * scale), int(height * scale)))
    
    # Convert ke grayscale untuk Haar Cascade
    gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
    
    # Equalize histogram untuk deteksi lebih baik di berbagai pencahayaan
    gray = cv2.equalizeHist(gray)
    
    # Detect faces dengan parameter SENSITIF untuk wajah close-up
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,   # Akurat
        minNeighbors=3,    # Lebih sensitif!
        minSize=(20, 20),  # Ukuran minimum kecil
        maxSize=(300, 300) # Maksimum besar
    )
    
    # Scale back ke ukuran asli (TANPA filter ketat)
    valid_faces = []
    for (x, y, w, h) in faces:
        x, y, w, h = int(x/scale), int(y/scale), int(w/scale), int(h/scale)
        # Hanya filter ukuran minimum
        if w >= 40 and h >= 40:
            valid_faces.append((x, y, w, h))
    
    # Jika ada deteksi baru, update
    if len(valid_faces) > 0:
        last_face_boxes = valid_faces
        last_detection_time = current_time
    elif current_time - last_detection_time > DETECTION_TIMEOUT:
        # Timeout, hapus box
        last_face_boxes = []
    
    # Gunakan last known boxes untuk stabilitas
    people_detected = len(last_face_boxes)
    
    for i, (x, y, w, h) in enumerate(last_face_boxes):
        # Bounding box hijau tebal
        color = (0, 255, 0)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)
        
        # Corner decorations kuning
        corner_len = min(25, w // 4, h // 4)
        corner_color = (0, 255, 255)
        corner_thickness = 4
        
        # Top-left
        cv2.line(frame, (x, y), (x + corner_len, y), corner_color, corner_thickness)
        cv2.line(frame, (x, y), (x, y + corner_len), corner_color, corner_thickness)
        # Top-right
        cv2.line(frame, (x + w, y), (x + w - corner_len, y), corner_color, corner_thickness)
        cv2.line(frame, (x + w, y), (x + w, y + corner_len), corner_color, corner_thickness)
        # Bottom-left
        cv2.line(frame, (x, y + h), (x + corner_len, y + h), corner_color, corner_thickness)
        cv2.line(frame, (x, y + h), (x, y + h - corner_len), corner_color, corner_thickness)
        # Bottom-right
        cv2.line(frame, (x + w, y + h), (x + w - corner_len, y + h), corner_color, corner_thickness)
        cv2.line(frame, (x + w, y + h), (x + w, y + h - corner_len), corner_color, corner_thickness)
        
        # Label
        label = f"ORANG {i + 1}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        font_thickness = 2
        label_size, _ = cv2.getTextSize(label, font, font_scale, font_thickness)
        
        label_y = max(y - 10, label_size[1] + 10)
        cv2.rectangle(frame, (x, label_y - label_size[1] - 8), 
                     (x + label_size[0] + 10, label_y + 4), (0, 0, 0), cv2.FILLED)
        cv2.rectangle(frame, (x, label_y - label_size[1] - 8), 
                     (x + label_size[0] + 10, label_y + 4), color, 2)
        cv2.putText(frame, label, (x + 5, label_y - 4), font, font_scale, (255, 255, 255), font_thickness)
    
    return people_detected, frame

def detect_combined(frame):
    """Kombinasi YOLO (body) + Haar Cascade (face) untuk deteksi optimal"""
    # Coba YOLO dulu untuk full body
    yolo_count, yolo_frame = detect_people_yolo(frame.copy())
    
    if yolo_count > 0:
        # YOLO berhasil detect
        return yolo_count, yolo_frame
    else:
        # Fallback ke face detection untuk close-up
        face_count, face_frame = detect_faces(frame)
        return face_count, face_frame

def capture_frames():
    global camera, output_frame, lock, people_count
    
    print("📹 Starting capture and detection...")
    frame_count = 0
    start_time = time.time()
    last_publish = time.time()
    last_detected_frame = None  # Cache frame dengan detection
    
    while True:
        try:
            ret, frame = camera.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            frame_count += 1
            current_time = time.time()
            
            # Lakukan detection setiap frame untuk selalu menampilkan box
            count, detected_frame = detect_combined(frame)
            people_count = count
            last_detected_frame = detected_frame
            
            # Calculate FPS (only for tracking, not displayed)
            elapsed = current_time - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            
            # No text overlays - clean video with boxes only
            
            # Publish to MQTT
            if current_time - last_publish > PUBLISH_INTERVAL:
                publish_people_count(people_count)
                last_publish = current_time
            
            with lock:
                output_frame = last_detected_frame.copy() if last_detected_frame is not None else frame.copy()
            
            if frame_count >= 1000:
                frame_count = 0
                start_time = time.time()
                
        except Exception as e:
            print(f"⚠️  Capture error: {e}")
            time.sleep(1)

def generate_stream():
    global output_frame, lock
    while True:
        with lock:
            if output_frame is None:
                continue
            # JPEG quality 95 - HD crystal clear
            flag, encoded = cv2.imencode(".jpg", output_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            if not flag:
                continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encoded) + b'\r\n')
        
        # Minimal delay untuk streaming ultra smooth
        time.sleep(0.016)  # ~60 FPS max

@app.route('/video_feed')
def video_feed():
    return Response(generate_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>People Counter - Azure IoT</title>
        <style>
            body {{ font-family: Arial; background: #1a1a1a; color: white; text-align: center; padding: 20px; }}
            h1 {{ color: #00ff00; }}
            img {{ width: 100%; max-width: 640px; border: 3px solid #00ff00; border-radius: 8px; }}
            .info {{ background: #2a2a2a; padding: 15px; margin: 20px auto; max-width: 640px; border-radius: 8px; }}
            .status {{ color: #00ff00; font-weight: bold; font-size: 24px; }}
            .azure {{ color: #0078d4; }}
        </style>
        <script>
            setInterval(() => {{
                fetch('/count').then(r => r.json()).then(d => {{
                    document.getElementById('count').textContent = d.count;
                    document.getElementById('azure').textContent = d.azure_connected ? '✓ Connected' : '✗ Disconnected';
                    document.getElementById('azure').style.color = d.azure_connected ? '#00ff00' : '#ff4444';
                }});
            }}, 1000);
        </script>
    </head>
    <body>
        <h1>🎥 People Counter - Azure IoT Hub</h1>
        <p class="status">● LIVE | Orang Terdeteksi: <span id="count">0</span></p>
        <img src="/video_feed">
        <div class="info">
            <h3>📌 Info</h3>
            <p><strong>Detection:</strong> YOLO v3-tiny + Face Detection</p>
            <p><strong>Confidence:</strong> {CONFIDENCE_THRESHOLD*100:.0f}%</p>
            <p><strong>☁️ Azure IoT Hub:</strong> <span class="azure">{IOT_HUB_NAME}</span></p>
            <p><strong>📱 Device:</strong> {DEVICE_ID}</p>
            <p><strong>Status:</strong> <span id="azure">Checking...</span></p>
        </div>
    </body>
    </html>
    """

@app.route('/status')
def status():
    return {
        'status': 'online',
        'people_count': people_count,
        'azure_connected': iot_connected,
        'detection': 'YOLO v3-tiny + Face Detection',
        'confidence_threshold': CONFIDENCE_THRESHOLD,
        'iot_hub': IOT_HUB_NAME,
        'device_id': DEVICE_ID
    }

@app.route('/count')
def count():
    return {'count': people_count, 'azure_connected': iot_connected}

@app.route('/snapshot')
def snapshot():
    """Return single JPEG frame dengan caching untuk kurangi CPU load"""
    global output_frame, lock, cached_snapshot, cached_snapshot_time
    
    current_time = time.time() * 1000
    
    # Return cached snapshot jika masih fresh
    if cached_snapshot is not None and (current_time - cached_snapshot_time) < SNAPSHOT_CACHE_MS:
        response = Response(cached_snapshot, mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    with lock:
        if output_frame is None:
            return Response(status=503)
        # JPEG quality 95% untuk HD crystal clear
        flag, encoded = cv2.imencode(".jpg", output_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not flag:
            return Response(status=503)
        cached_snapshot = bytearray(encoded)
        cached_snapshot_time = current_time
    
    response = Response(cached_snapshot, mimetype='image/jpeg')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Add OPTIONS handler for CORS preflight
@app.route('/video_feed', methods=['OPTIONS'])
@app.route('/count', methods=['OPTIONS'])
@app.route('/status', methods=['OPTIONS'])
@app.route('/snapshot', methods=['OPTIONS'])
def options():
    response = app.make_default_options_response()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

def main():
    print("\n" + "="*60)
    print("YOLO + FACE DETECTION PEOPLE COUNTER")
    print("Terintegrasi Azure IoT Hub")
    print("="*60)
    
    if not init_yolo():
        print("⚠️  YOLO tidak tersedia - menggunakan face detection saja")
    
    if not init_face_detector():
        print("⚠️  Face detector tidak tersedia")
    
    if not init_camera():
        print("✗ Failed to initialize camera")
        return
    
    # Initialize Azure IoT Hub
    if not init_azure_iot():
        print("⚠️  Azure IoT Hub tidak terhubung - data tidak akan dikirim ke cloud")
    
    capture_thread = threading.Thread(target=capture_frames, daemon=True)
    capture_thread.start()
    
    # Wait for first frame
    print("\n⏳ Waiting for first frame...")
    for _ in range(100):
        if output_frame is not None:
            break
        time.sleep(0.1)
    
    if output_frame is None:
        print("✗ Timeout waiting for frame")
        return
    
    print("✓ First frame captured")
    print(f"\n🌐 Server running on port {STREAM_PORT}")
    print(f"📡 Stream: http://localhost:{STREAM_PORT}/video_feed")
    print(f"🏠 Home: http://localhost:{STREAM_PORT}/")
    print(f"👥 Count API: http://localhost:{STREAM_PORT}/count")
    print(f"\n☁️  Azure IoT Hub: {IOT_HUB_NAME}")
    print(f"📱 Device ID: {DEVICE_ID}")
    print("="*60 + "\n")
    
    try:
        if WAITRESS_AVAILABLE:
            print("🚀 Starting Waitress production server...")
            serve(app, host='0.0.0.0', port=STREAM_PORT, threads=4)
        else:
            print("⚠️  Using Flask dev server (install waitress for production)")
            app.run(host='0.0.0.0', port=STREAM_PORT, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping...")
    finally:
        if camera:
            camera.release()
        if iot_client:
            if AZURE_SDK_AVAILABLE and hasattr(iot_client, 'disconnect'):
                iot_client.disconnect()
            elif hasattr(iot_client, 'loop_stop'):
                iot_client.loop_stop()
                iot_client.disconnect()
        print("✓ Done")

if __name__ == '__main__':
    main()
