# 3D Models

## Overview

Folder ini berisi file 3D model untuk visualisasi Digital Twin.

## Files

- 3d digital twin.glb: Model utama ruangan dengan sensor
- floor_plan.glb: Floor plan 3D (opsional)

## File Size Limitation

File 3D model berukuran besar tidak di-commit ke Git. Upload ke Azure Blob Storage:

### Upload ke Azure Blob Storage

1. Buka Azure Portal
2. Navigate ke Storage Account
3. Buat container: 3dmodels
4. Set public access: Blob
5. Upload file .glb

### URL Format

```
https://[storage_account].blob.core.windows.net/3dmodels/[filename].glb
```

### Update Code

Set environment variable:

```
VITE_3D_MODEL_BASE_URL=https://[storage_account].blob.core.windows.net/3dmodels
```

Atau hardcode URL di DigitalTwin3D.vue.

## Supported Formats

- GLB (recommended): Binary glTF, lebih kecil
- GLTF: Text-based glTF dengan file terpisah
- FBX: Support via loader tambahan
- OBJ: Support via loader tambahan

## Testing

### Test Model Lokal

1. Letakkan file .glb di folder ini
2. Jalankan development server:
```bash
npm run dev
```
3. Buka dashboard dan verifikasi 3D model terload

### Test Model dari Azure

1. Update URL di environment variable atau code
2. Buka dashboard dan verifikasi model terload dari Azure

### Verifikasi File GLB

Gunakan tool online untuk preview GLB:
- https://gltf-viewer.donmccurdy.com/
- https://sandbox.babylonjs.com/
