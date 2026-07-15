"""
run_all.py — One-command reproducibility runner
=================================================

Menjalankan seluruh pipeline paper:
  1. Verifikasi environment (CSV, pickles)
  2. Run streaming simulation (streaming_final.py)
  3. Generate figures (streaming_visualizations.py)
  4. Verify Azure live data (opsional, butuh `az` CLI)
  5. Print summary + cross-check

Usage:
  python run_all.py                      # full pipeline
  python run_all.py --skip-streaming     # skip step 2 (use existing pickles)
  python run_all.py --skip-azure         # skip Azure verification
  python run_all.py --quick              # subsample 1K records (testing only)

Exit code 0 jika sukses; non-zero jika ada step yang gagal.
"""
import argparse
import subprocess
import sys
import time
import os
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
CSV_FILE = ROOT / "sensor_data.csv"
PKL_METRICS = ROOT / "streaming_metrics_v2.pkl"
PKL_RESULTS = ROOT / "streaming_results_v2.pkl"
JSON_ENERGY = ROOT / "energy_model_results_fixed.json"
FIGURES_DIR = ROOT / "figures"

REQUIRED_FILES = [CSV_FILE, JSON_ENERGY]
EXPECTED_FIGURES = [
    "01_throughput_dashboard.png",
    "02_latency_distribution.png",
    "03_prediction_accuracy.png",
    "04_routing_breakdown.png",
    "05_anomaly_analysis.png",
    "06_energy_profile.png",
    "07_temporal_patterns.png",
    "08_streaming_r2_convergence.png",
]


class Step:
    def __init__(self, name, cmd, skip=False, required_outputs=None):
        self.name = name
        self.cmd = cmd
        self.skip = skip
        self.required_outputs = required_outputs or []

    def run(self, dry=False):
        if self.skip:
            print(f"  ⏭️  SKIP: {self.name}")
            return True
        print(f"\n{'='*70}")
        print(f"  STEP: {self.name}")
        print(f"  CMD : {self.cmd}")
        print(f"{'='*70}")
        t0 = time.perf_counter()
        if dry:
            print("  (dry run — not executing)")
            ok = True
        else:
            ok = subprocess.run(
                self.cmd, shell=True, cwd=ROOT, check=False
            ).returncode == 0
        dt = time.perf_counter() - t0
        print(f"  ⏱️  Duration: {dt:.1f}s  Result: {'✅ OK' if ok else '❌ FAIL'}")
        if ok:
            missing = [p for p in self.required_outputs if not (ROOT / p).exists()]
            if missing:
                print(f"  ⚠️  Missing outputs: {missing}")
                return False
        return ok


def check_environment():
    print(f"\n{'='*70}")
    print("  STEP 0: Environment check")
    print(f"{'='*70}")
    ok = True
    for f in REQUIRED_FILES:
        if f.exists():
            print(f"  ✅ {f.name} ({f.stat().st_size:,} bytes)")
        else:
            print(f"  ❌ MISSING: {f}")
            ok = False
    if ok:
        print(f"  ✅ Python: {sys.version.split()[0]}")
        print(f"  ✅ CWD: {ROOT}")
        if not FIGURES_DIR.exists():
            FIGURES_DIR.mkdir()
            print(f"  📂 Created {FIGURES_DIR}/")
        else:
            print(f"  ✅ {FIGURES_DIR}/ exists ({len(list(FIGURES_DIR.glob('*.png')))} PNG files)")
    return ok


def verify_pickles():
    print(f"\n{'='*70}")
    print("  STEP: Verify pickles")
    print(f"{'='*70}")
    cmd = (
        "python3 -c \""
        "import pickle, json; "
        f"m = pickle.load(open('{PKL_METRICS.name}', 'rb')); "
        "print(f'R²={m[\\\"test_r2\\\"]:.4f}, MAPE={m[\\\"test_mape\\\"]:.2f}%, throughput={m[\\\"throughput\\\"]:.0f}'); "
        f"d = json.load(open('{JSON_ENERGY.name}')); "
        "r = d['results'][0]; "
        "print(f'Ridge R²={r[\\\"r2\\\"]:.4f}, MAPE={r[\\\"mape\\\"]:.2f}%'); "
        "print('✅ All pickles readable'); "
        "\""
    )
    return Step("Verify pickles", cmd, ).run()


def verify_azure():
    """Opsional: verifikasi live data di Azure Storage."""
    print(f"\n{'='*70}")
    print("  STEP: Azure live verification (optional)")
    print(f"{'='*70}")
    cmd = (
        "az storage entity query "
        "--table-name SensorTelemetry "
        "--account-name stordigitaltwin2026 "
        "--auth-mode login "
        "--output tsv 2>/dev/null | wc -l"
    )
    print("  Note: requires `az` CLI logged in to stordigitaltwin2026")
    print(f"  CMD: {cmd}")
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        dt = time.perf_counter() - t0
        lines = result.stdout.strip() or "0"
        print(f"  ⏱️  Duration: {dt:.1f}s")
        if result.returncode == 0 and int(lines) > 1000:
            print(f"  ✅ Azure verification: {lines} entity rows")
            return True
        elif result.returncode == 0:
            print(f"  ⚠️  Azure returned {lines} rows (low or empty)")
            return False
        else:
            print(f"  ⚠️  Azure CLI failed (not logged in?): {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print("  ⏱️  Timeout — skipping")
        return False
    except FileNotFoundError:
        print("  ⚠️  az CLI not installed — skipping")
        return False


def print_summary():
    print(f"\n{'='*70}")
    print("  SUMMARY")
    print(f"{'='*70}")
    print()
    print("  Files generated (relative to repo root):")
    print(f"    {PKL_METRICS.name:40s}: {'✅' if PKL_METRICS.exists() else '❌'}")
    print(f"    {PKL_RESULTS.name:40s}: {'✅' if PKL_RESULTS.exists() else '❌'}")
    print(f"    {JSON_ENERGY.name:40s}: {'✅' if JSON_ENERGY.exists() else '❌'}")
    if FIGURES_DIR.exists():
        png_count = len(list(FIGURES_DIR.glob("*.png")))
        print(f"    figures/*.png{30*' '}: {png_count} files ({'✅' if png_count >= 8 else '❌ expected 8'})")
    print()
    print("  Numbers verified (from pickles):")
    try:
        import pickle, json
        m = pickle.load(open(PKL_METRICS, "rb"))
        d = json.load(open(JSON_ENERGY, "rb"))
        ridge = d["results"][0]
        print(f"    Streaming  R²     : {m['streaming_r2']:.4f}")
        print(f"    Streaming  MAPE   : {m['streaming_mape']:.2f}%")
        print(f"    Streaming  throughput: {m['throughput']:.0f} msg/sec")
        print(f"    Edge routing %    : {m['edge_eff']:.2f}%")
        print(f"    Edge latency P50  : {m['edge_latency_p50']:.2f} ms (simulated)")
        print(f"    Cloud latency P50 : {m['cloud_latency_p50']:.2f} ms (simulated)")
        print()
        print(f"    Batch Ridge  R²   : {ridge['r2']:.4f}")
        print(f"    Batch Ridge  MAPE : {ridge['mape']:.2f}%")
        rf = d["results"][1]
        print(f"    Batch RF     R²   : {rf['r2']:.4f}")
        print(f"    Batch RF     MAPE : {rf['mape']:.2f}%")
    except Exception as e:
        print(f"    ⚠️  Error loading pickles: {e}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Reproduce paper results")
    parser.add_argument("--skip-streaming", action="store_true",
                        help="Skip streaming_final.py (use existing pickles)")
    parser.add_argument("--skip-azure", action="store_true",
                        help="Skip Azure live verification")
    parser.add_argument("--quick", action="store_true",
                        help="Quick mode: subsample 1K records (testing)")
    parser.add_argument("--dry", action="store_true",
                        help="Dry run: print steps without executing")
    args = parser.parse_args()

    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " Edge-Cloud Energy Estimation — Reproducibility Runner ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    # Step 0: Environment
    if not check_environment():
        print("\n❌ Environment check failed. Aborting.")
        sys.exit(1)

    # Step 1: Verify existing pickles
    if not PKL_METRICS.exists() or not PKL_RESULTS.exists():
        print("\n⚠️  Pickles missing — must run streaming_final.py first")
        args.skip_streaming = False

    steps = []

    # Step 2: Streaming simulation
    if not args.skip_streaming and PKL_METRICS.exists() and not args.quick:
        print(f"\n  Note: {PKL_METRICS.name} exists. Run `--skip-streaming` to skip.")
    if not args.skip_streaming:
        cmd = "python3 streaming_final.py"
        if args.quick:
            cmd = "PILOT_SIZE=1000 python3 streaming_final.py"
        steps.append(Step(
            "Streaming simulation (1.3M records, ~5 min)",
            cmd,
            required_outputs=[PKL_METRICS.name, PKL_RESULTS.name]
        ))

    # Step 3: Visualizations
    steps.append(Step(
        "Generate figures (8 PNGs from pickles)",
        "python3 streaming_visualizations.py",
        required_outputs=[f"figures/{f}" for f in EXPECTED_FIGURES]
    ))

    # Step 4: Verify pickles
    steps.append(Step("Verify pickles (load + dump metrics)", verify_pickles.__name__))

    # Execute
    failed = []
    for step in steps:
        if step.name == "Verify pickles (load + dump metrics)":
            ok = verify_pickles()
        else:
            ok = step.run(dry=args.dry)
        if not ok:
            failed.append(step.name)

    # Step 5: Azure (optional)
    if not args.skip_azure:
        verify_azure()

    # Final summary
    print_summary()

    if failed:
        print(f"\n❌ {len(failed)} step(s) failed:")
        for name in failed:
            print(f"   - {name}")
        sys.exit(1)
    else:
        print("\n✅ All steps completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
