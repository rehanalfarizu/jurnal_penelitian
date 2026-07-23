import pickle
import os

base = "/Users/macbookpro/Documents/jurnal_penelitian/arsip/2026-07-23"
paths = {
    "BACKUP (pre_rerun — 15,729)": f"{base}/backup_pre_rerun_2026-07-23/streaming_metrics_v2.pkl",
    "CURRENT (today — 26,232)":     f"{base}/streaming_metrics_v2.pkl",
}

for label, p in paths.items():
    if not os.path.exists(p):
        print(f"SKIP: {label} -> NOT FOUND at {p}")
        continue
    with open(p, "rb") as f:
        m = pickle.load(f)
    print(f"\n=== {label} ===")
    for k, v in m.items():
        print(f"  {k}: {v}")
