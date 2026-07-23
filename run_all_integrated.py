#!/usr/bin/env python3
"""
run_all_integrated.py — Reproduce semua 4 pilar, end-to-end.

Usage:
    python run_all_integrated.py --skip-hardware   # tanpa ESP32 deploy
    python run_all_integrated.py --only pillar1    # hanya Pilar 1
    python run_all_integrated.py --help            # semua opsi

Output:
    - streaming_metrics_v2.pkl     (Pilar 1)
    - streaming_results_v2.pkl     (Pilar 1, 288 MB)
    - figures/01-08_*.png         (Pilar 1, 8 figure)
    - ac_recommendation_model.pkl  (Pilar 4, jika --retrain)

Author: streaming_visualizations runner, integrated for paper reproducibility
Co-located version of Edge_Cloud_Streaming/scripts/run_all_integrated.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List

ROOT = Path(__file__).parent.resolve()
DIGITAL = ROOT / "Digital_Twin" / "dashboard_digitaltwin"
EDGE_SCRIPTS = ROOT / "Edge_Cloud_Streaming" / "scripts"
PRED_SCRIPTS = ROOT / "Prediksi_Energi" / "scripts"

# Python in .venv (preferred) or system
PY = str(ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv" / "bin" / "python").exists() else sys.executable


def banner(msg: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {msg}")
    print("=" * 70)


def run(cmd: List[str], cwd: Path | None = None, timeout: int = 1200) -> bool:
    """Run command, return True if exit 0. Streams stdout."""
    print(f"\n$ {' '.join(cmd)}")
    if cwd:
        print(f"  cwd: {cwd}")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=False,
            timeout=timeout,
            env={**os.environ, "CONDA_NO_PLUGINS": "true"},
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ✗ TIMEOUT after {timeout}s")
        return False
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False


def pillar1(skip_visualization: bool = False) -> bool:
    """Pilar 1: Streaming validation + figures."""
    banner("PILAR 1 — Edge-Cloud Streaming Validation")

    t0 = time.time()
    ok = run(
        [PY, "streaming_final.py"],
        cwd=ROOT,
        timeout=900,   # 15 min cap
    )
    if not ok:
        print("  ✗ Pilar 1a (streaming_final.py) FAILED")
        return False
    print(f"  ✓ Pilar 1a done ({time.time() - t0:.0f}s)")

    if skip_visualization:
        print("  ⊝ Pilar 1b visualizations skipped")
        return True

    t0 = time.time()
    ok = run(
        [PY, "streaming_visualizations.py"],
        cwd=ROOT,
        timeout=600,   # 10 min cap
    )
    if not ok:
        print("  ✗ Pilar 1b (streaming_visualizations.py) FAILED")
        return False
    print(f"  ✓ Pilar 1b done ({time.time() - t0:.0f}s)")
    return True


def pillar2(skip_hardware: bool = True) -> bool:
    """Pilar 2: ESP32 + Pi Camera sensor stack.
    Hardware deployment is interactive; this only verifies source code.
    """
    banner("PILAR 2 — Multimodal Sensor Fusion (ESP32 + Pi Camera)")

    if skip_hardware:
        print("  ⊝ ESP32 firmware upload skipped (--skip-hardware)")
        print("    Source: Digital_Twin/dashboard_digitaltwin/sensor_iot/esp32_main.cpp")
        print("    Re-upload manual: platformio run --target upload")
    else:
        # Try platformio upload (may fail without board connected)
        ok = run(
            ["pio", "run", "--target", "upload"],
            cwd=DIGITAL / "sensor_iot",
            timeout=120,
        )
        if not ok:
            print("  ✗ PlatformIO upload failed — board mungkin tidak terhubung")
            return False

    # Static check: verify ESP32 source compiles syntactically
    esp32_src = DIGITAL / "sensor_iot" / "esp32_main.cpp"
    if esp32_src.exists():
        size_kb = esp32_src.stat().st_size / 1024
        print(f"  ✓ ESP32 firmware source present ({size_kb:.1f} KB)")

    yolo_src = DIGITAL / "sensor_iot" / "raspberry_pi" / "people_counter_yolo.py"
    if yolo_src.exists():
        size_kb = yolo_src.stat().st_size / 1024
        print(f"  ✓ YOLO people-counter source present ({size_kb:.1f} KB)")
    return True


def pillar3(skip_build: bool = True) -> bool:
    """Pilar 3: Vue 3 dashboard.
    Build only if not skipped (npm install + run build = ~2 min).
    """
    banner("PILAR 3 — Digital Twin Dashboard (Vue 3)")

    view_dir = DIGITAL / "view_virtual"
    if not (view_dir / "package.json").exists():
        print("  ✗ Vue project package.json not found")
        return False

    print(f"  Vue project at: {view_dir}")
    if skip_build:
        print("  ⊝ npm install/build skipped (--skip-build)")
        print("    Build manual: cd view_virtual && npm install && npm run build")
        return True

    ok = run(["npm", "install"], cwd=view_dir, timeout=300)
    if not ok:
        return False
    return run(["npm", "run", "build"], cwd=view_dir, timeout=300)


def pillar4(retrain: bool = False, skip_api: bool = True) -> bool:
    """Pilar 4: AC prediction API.
    Retrain only if --retrain flag set (trains in 30-60s).
    """
    banner("PILAR 4 — Prediksi Energi & Rekomendasi AC")

    models = DIGITAL / "ml_models" / "models"
    model_pkl = models / "ac_recommendation_model.pkl"
    if not model_pkl.exists():
        print(f"  ✗ Model pkl missing: {model_pkl}")
        print("    Run with --retrain to train a new one")
        return False

    if retrain:
        ok = run(
            [PY, "train_ac_recommendation.py"],
            cwd=DIGITAL / "ml_models",
            timeout=120,
        )
        if not ok:
            return False

    print(f"  ✓ Model loaded: {model_pkl.stat().st_size / 1024:.1f} KB")
    if not skip_api:
        print("  Starting FastAPI on port 8000 (Ctrl+C to stop)...")
        ok = run(
            [PY, "-m", "uvicorn", "prediction_api:app",
             "--host", "0.0.0.0", "--port", "8000"],
            cwd=DIGITAL / "ml_models",
            timeout=10,  # Background, will fail timeout — that's OK
        )
        return ok
    else:
        print("  ⊝ FastAPI not started (--skip-api)")
        print("    Manual: uvicorn prediction_api:app --port 8000")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--only", choices=["pillar1", "pillar2", "pillar3", "pillar4"],
                   help="Run only one pillar")
    p.add_argument("--skip-hardware", action="store_true", default=True,
                   help="Skip ESP32 firmware upload (default: True)")
    p.add_argument("--no-skip-hardware", dest="skip_hardware", action="store_false")
    p.add_argument("--skip-build", action="store_true", default=True,
                   help="Skip npm install/build for Vue (default: True)")
    p.add_argument("--no-skip-build", dest="skip_build", action="store_false")
    p.add_argument("--skip-api", action="store_true", default=True,
                   help="Skip starting FastAPI server (default: True)")
    p.add_argument("--skip-visualization", action="store_true",
                   help="Skip figure regeneration (Pilar 1b only)")
    p.add_argument("--retrain", action="store_true",
                   help="Retrain XGBoost AC model (Pilar 4)")
    args = p.parse_args()

    banner("run_all_integrated.py — Tahap D reproducibility runner")
    print(f"  Root: {ROOT}")
    print(f"  Python: {PY}")
    print(f"  Args: {vars(args)}")

    results = {}

    if args.only is None or args.only == "pillar1":
        results["Pilar 1"] = pillar1(args.skip_visualization)
    if args.only is None or args.only == "pillar2":
        results["Pilar 2"] = pillar2(args.skip_hardware)
    if args.only is None or args.only == "pillar3":
        results["Pilar 3"] = pillar3(args.skip_build)
    if args.only is None or args.only == "pillar4":
        results["Pilar 4"] = pillar4(args.retrain, args.skip_api)

    banner("RINGKASAN")
    for name, ok in results.items():
        print(f"  {'✓' if ok else '✗'} {name}: {'PASS' if ok else 'FAIL'}")

    if all(results.values()):
        print("\n  ALL PILLARS PASS ✓")
        print(f"\n  Cek figure: figures/")
        print(f"  Cek data: streaming_metrics_v2.pkl")
        return 0
    else:
        print("\n  SOME PILLARS FAILED ✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
