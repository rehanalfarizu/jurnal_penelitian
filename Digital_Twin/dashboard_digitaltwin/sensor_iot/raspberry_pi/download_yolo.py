#!/usr/bin/env python3
"""
Script untuk download YOLO v3-tiny files
Jalankan ini di Raspberry Pi sebelum menjalankan people_counter_yolo.py
"""

import os
import urllib.request
import sys

print("="*60)
print("📥 YOLO v3-Tiny Files Downloader")
print("="*60)

files = {
    'yolov3-tiny.cfg': 'https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg',
    'yolov3-tiny.weights': 'https://pjreddie.com/media/files/yolov3-tiny.weights',
    'coco.names': 'https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names'
}

def download_file(filename, url):
    """Download file dengan progress bar"""
    if os.path.exists(filename):
        print(f"✓ {filename} sudah ada (skip)")
        return True
    
    print(f"\n📥 Downloading {filename}...")
    print(f"   URL: {url}")
    
    try:
        def reporthook(count, block_size, total_size):
            """Progress bar callback"""
            if total_size > 0:
                percent = int(count * block_size * 100 / total_size)
                downloaded = count * block_size / (1024 * 1024)  # MB
                total = total_size / (1024 * 1024)  # MB
                
                # Print progress bar
                bar_length = 40
                filled = int(bar_length * percent / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                sys.stdout.write(f'\r   [{bar}] {percent}% ({downloaded:.1f}/{total:.1f} MB)')
                sys.stdout.flush()
        
        urllib.request.urlretrieve(url, filename, reporthook)
        print(f"\n✅ {filename} berhasil didownload")
        return True
        
    except Exception as e:
        print(f"\n❌ Error downloading {filename}: {e}")
        return False

# Download semua files
print("\nMemulai download YOLO files...\n")
success = True

for filename, url in files.items():
    if not download_file(filename, url):
        success = False
        break

print("\n" + "="*60)
if success:
    print("✅ SEMUA FILE BERHASIL DIDOWNLOAD!")
    print("\nFile yang sudah didownload:")
    for filename in files.keys():
        if os.path.exists(filename):
            size = os.path.getsize(filename) / (1024 * 1024)
            print(f"   ✓ {filename} ({size:.1f} MB)")
    
    print("\n💡 Langkah selanjutnya:")
    print("   1. Jalankan: python3 people_counter_yolo.py")
    print("   2. Atau test dengan: python3 people_counter_yolo.py --test")
else:
    print("❌ DOWNLOAD GAGAL!")
    print("\n💡 Troubleshooting:")
    print("   - Pastikan Raspberry Pi terhubung ke internet")
    print("   - Coba download manual dari:")
    print("     https://pjreddie.com/media/files/yolov3-tiny.weights")

print("="*60)
