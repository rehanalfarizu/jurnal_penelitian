"""Create the reviewable multiscale Digital Twin evaluation package."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(path: Path, known_sha256: str | None = None) -> dict:
    return {
        "sha256": known_sha256 or _sha256(path),
        "bytes": path.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    parser.add_argument(
        "--destination", type=Path, default=Path("results/final")
    )
    parser.add_argument(
        "--config", type=Path, default=Path("configs/experiment.json")
    )
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    summary = json.loads(
        (args.outputs / "experiment_summary.json").read_text()
    )
    benchmark = json.loads(
        (args.outputs / "benchmark_metrics.json").read_text()
    )
    trace_audit = json.loads(
        (args.outputs / "trace_audit.json").read_text()
    )
    replay_audit = json.loads(
        (args.outputs / "historical_replay_audit.json").read_text()
    )

    json_names = [
        "trace_audit.json",
        "historical_replay_audit.json",
        "benchmark_metrics.json",
        "experiment_summary.json",
    ]
    for name in json_names:
        shutil.copy2(args.outputs / name, args.destination / name)
    shutil.copy2(
        args.outputs / "historical_replay_sample.csv",
        args.destination / "historical_replay_sample.csv",
    )
    shutil.copy2(
        args.config, args.destination / "experiment_config.json"
    )
    source_figures = args.outputs / "figures"
    destination_figures = args.destination / "figures"
    destination_figures.mkdir(exist_ok=True)
    source_figure_names = {path.name for path in source_figures.glob("*.png")}
    for stale_figure in destination_figures.glob("*.png"):
        if stale_figure.name not in source_figure_names:
            stale_figure.unlink()
    for figure in sorted(source_figures.glob("*.png")):
        shutil.copy2(figure, destination_figures / figure.name)

    reference_path = Path(config["data"]["reference_trace"])
    replay_path = Path(config["data"]["historical_replay"])

    local = benchmark["actual_local_monitoring"]
    serialization = benchmark["actual_json_serialization"]
    edge_path = benchmark["actual_edge_path"]
    cloud_route = benchmark["configured_cloud_route_end_to_end"]
    e2e = benchmark["configured_end_to_end"]
    cloud_only = benchmark["configured_cloud_only_baseline"]
    comparison = benchmark["architecture_comparison"]
    routing = benchmark["routing"]
    quality = benchmark["data_quality"]
    throughput = benchmark["throughput"][
        "sequential_messages_per_second"
    ]
    error = quality["power_consistency_error_w"]

    field_energy = trace_audit["derived_energy"]
    replay_energy = replay_audit["quality"]["energy_integration"]
    occupancy = replay_audit["quality"]["occupancy"]
    field_measurement = config["project"]["field_sensor_trace"]
    hardware_roles = field_measurement["hardware_roles"]
    pln_comparison = field_measurement["pln_kwh_reference_comparison"]

    report = f"""# Hasil evaluasi kinerja Digital Twin edge–cloud multiskala

Judul: **{config['project']['title']}**

Status: **evaluasi kinerja prototipe monitoring satu arah berbasis replay data
historis dengan pembanding edge–cloud dan cloud-only terkonfigurasi**.

## Cakupan data

- Trace asli: {trace_audit['source']['rows']:,} baris bertimestamp unik dari
  {trace_audit['source']['device_count']} ID gateway, periode
  {trace_audit['source']['timestamp_start_utc']} sampai
  {trace_audit['source']['timestamp_end_utc']}. Trace ini adalah telemetry
  arsip dari sensor fisik pada instalasi listrik yang dipantau. `DeviceID`
  `RASPBERRY_PI_GATEWAY_001` adalah identitas gateway agregasi, bukan jumlah
  perangkat fisik.
- Peran perangkat: **ESP32** adalah {hardware_roles['ESP32']}; **Raspberry Pi**
  adalah {hardware_roles['Raspberry Pi']}. Workbook lama tidak menyimpan
  `source_node_id` per record, sehingga evaluasi ini tidak membandingkan
  performa ESP32 dan Raspberry Pi secara terpisah.
- Workload: {replay_audit['source']['rows']:,} baris atau
  {replay_audit['provenance']['inferred_replay_blocks']:.0f} pengulangan
  deterministik dari satu blok historis turunan. Payload semua blok identik,
  tetapi blok turunan tidak identik dengan XLSX asli.
- Sampel benchmark: {replay_audit['benchmark_sample']['selected_rows']:,}
  posisi yang mencakup
  {len(replay_audit['benchmark_sample']['covered_replay_blocks'])} blok.
- Klasifikasi lineage:
  `{replay_audit['lineage']['classification']}`. Kode transformasi legacy
  tidak tersedia.
- Seluruh {replay_audit['source']['rows']:,} baris dipindai untuk audit;
  hanya {replay_audit['benchmark_sample']['selected_rows']:,} pesan yang
  diproses benchmark. Ini bukan load test dua juta pesan.
- Trace sumber memuat {trace_audit['source']['rows']:,} baris dengan timestamp
  unik. Independensi statistik antarbaris tidak diklaim; angka
  {replay_audit['source']['rows']:,} hanya volume workload replay.
- Firmware arsip merekam tegangan RMS melalui {field_measurement['firmware_sensor_chain']['voltage_sensor']}
  dan arus RMS melalui {field_measurement['firmware_sensor_chain']['current_sensor']},
  lalu menghitung daya sebagai V×I. Faktor daya tidak tersedia dalam trace.
- Energi dari trace sensor lapangan dihitung langsung dari XLSX asli dengan
  integrasi trapesium dan maksimum gap {field_energy['max_gap_seconds']:.1f}
  detik: **{field_energy['energy_wh']:.3f} Wh**
  ({field_energy['integrated_intervals']:,} interval terintegrasi;
  {field_energy['excluded_intervals']:,} interval dikecualikan).
- Satu blok payload CSV replay menghasilkan
  {replay_energy['energy_wh']:.3f} Wh. Nilai replay ini dipakai untuk konteks
  payload/API dan dilaporkan terpisah karena blok CSV telah berubah dari XLSX.
- Peneliti melaporkan perbandingan perangkat dengan {pln_comparison['reference']}.
  Namun angka awal–akhir dan timestamp interval belum tersimpan di repositori;
  karena itu galat kalibrasi terhadap meter belum dapat dihitung ulang di paket
  hasil ini.
- Sampel benchmark memuat {occupancy['occupied_sample_count']:,} status terisi
  dan {occupancy['unoccupied_sample_count']:,} status kosong; jumlah orang
  maksimum {occupancy['people_count_sample_max']}.

## Hasil pemantauan lokal

| Komponen | P50 (ms) | P95 (ms) | P99 (ms) |
|---|---:|---:|---:|
| Pemeriksaan software, konsistensi, dan routing | {local['p50_ms']:.4f} | {local['p95_ms']:.4f} | {local['p99_ms']:.4f} |
| Serialisasi JSON | {serialization['p50_ms']:.4f} | {serialization['p95_ms']:.4f} | {serialization['p99_ms']:.4f} |
| Jalur edge aktual | {edge_path['p50_ms']:.4f} | {edge_path['p95_ms']:.4f} | {edge_path['p99_ms']:.4f} |

Throughput sekuensial pada mesin uji:
**{throughput:,.2f} pesan/detik**. Angka ini mengukur loop Python lokal, bukan
kapasitas Raspberry Pi produksi.

## Routing dan kualitas pesan

- Edge: {routing['edge_count']:,} pesan.
- Cloud: {routing['cloud_count']:,} pesan.
- Ambang anomali daya: {routing['power_anomaly_threshold_w']:.1f} W
  berdasarkan P99 trace asli.
- Lolos pemeriksaan struktur/nilai elektrik: {quality['valid_count']:,};
  tidak lolos:
  {quality['invalid_count']:,}.
- Selisih konsistensi |daya legacy − round(V×I, 1)|: mean
  {error['mean']:.4f} W, P95 {error['p95']:.4f} W, maksimum
  {error['max']:.4f} W.

Rincian alasan routing, termasuk kategori dengan hitungan nol, tersedia di
`benchmark_metrics.json`. Pada sampel final, jalur cloud hanya terpicu oleh
daya di atas P99; cabang missing/non-finite, listrik invalid, dan arus rendah
belum tercakup data replay.

## Evaluasi edge–cloud dan baseline cloud-only

- Deadline operasional terkonfigurasi:
  {config['data']['near_realtime_deadline_seconds']:.1f} detik atau
  {e2e['deadline_ms']:.1f} ms.
- Dasar deadline: pembulatan median interval antar-record trace asli
  {trace_audit['sampling']['gap_seconds_p50']:.7f} detik; bukan interval
  publish nominal firmware legacy.
- Jalur cloud terkonfigurasi, khusus {cloud_route['routed_count']:,} pesan
  cloud: P50 {cloud_route['p50_ms']:.3f} ms,
  P95 {cloud_route['p95_ms']:.3f} ms, P99
  {cloud_route['p99_ms']:.3f} ms.
- End-to-end campuran seluruh rute: P50 {e2e['p50_ms']:.3f} ms,
  P95 {e2e['p95_ms']:.3f} ms, P99 {e2e['p99_ms']:.3f} ms.
- Baseline cloud-only dengan pesan, pemrosesan lokal, seed, dan profil jaringan
  yang sama: P50 {cloud_only['p50_ms']:.3f} ms,
  P95 {cloud_only['p95_ms']:.3f} ms, P99
  {cloud_only['p99_ms']:.3f} ms.
- Pada kondisi emulasi ini, edge–cloud menurunkan P95 terkonfigurasi sebesar
  {comparison['configured_p95_latency_reduction_percent']:.2f}% dan menghindari
  {comparison['network_payload_bytes_avoided']:,} byte transfer jaringan
  ({comparison['network_payload_reduction_rate']:.2%}).
- Deadline miss: {e2e['deadline_miss_count']:,} dari
  {e2e['delivered_count']:,} pesan terkirim
  ({e2e['deadline_miss_rate']:.3%}); drop terkonfigurasi:
  {e2e['dropped_count']:,}.

Latensi jaringan pada bagian ini berasal dari profil emulasi yang dideklarasikan,
bukan pengukuran public cloud. Nilai campuran P50/P95 didominasi jalur edge,
sedangkan P99 memasuki kelompok pesan cloud karena
{routing['cloud_count'] / (routing['edge_count'] + routing['cloud_count']):.2%}
pesan dirutekan ke cloud. Latensi render browser, replay clock, dan
multi-client juga belum
tercakup.

## Digital Twin geospasial–indoor multiskala

- **LoD-A (tapak geospasial)** menggunakan
  {config['digital_twin']['geospatial_reference']['crs']} pada koordinat legacy
  {config['digital_twin']['geospatial_reference']['latitude']:.4f},
  {config['digital_twin']['geospatial_reference']['longitude']:.4f}.
- **LoD-B (bangunan)** mengikat rute edge–cloud, daya, energi kumulatif per siklus,
  dan okupansi pada payload yang sama.
- **LoD-C (indoor Babylon)** menampilkan indikator sensor, rute, dan jumlah
  orang.
- Ketiga tampilan merupakan LoD aplikatif proyek dengan perpindahan level
  manual. Kepatuhan terhadap LoD geometrik CityGML, IndoorGML, IFC, atau 3D
  Tiles belum dievaluasi. Koordinat legacy belum diverifikasi dengan survei.
- Aliran data satu arah dari sumber/replay ke representasi digital membuat
  implementasi ini tepat disebut prototipe Digital Twin berorientasi monitoring
  atau Digital Shadow, bukan sistem kendali dua arah.

## Visual hasil

- [Profil trace asli](figures/01_trace_profile.png)
- [Provenance replay](figures/02_replay_provenance.png)
- [Pemeriksaan software dan routing](figures/03_monitoring_checks.png)
- [Karakteristik latensi](figures/04_latency_characteristics.png)
- [Pemetaan Digital Twin multiskala](figures/05_multiscale_digital_twin.png)

## Kesimpulan yang didukung

Eksperimen mendukung evaluasi apakah pipeline monitoring, provenance,
integrasi energi dari trace sensor lapangan dan payload replay, monitoring
okupansi, routing edge–cloud, serialisasi,
replay API, dan prototipe geospasial–indoor satu arah bekerja dalam deadline
konfigurasi pada sampel workload replay yang tersedia.
Berdasarkan arah aliran data, implementasi lebih dekat dengan Digital Shadow
atau prototipe Digital Twin berorientasi monitoring daripada Digital Twin
operasional penuh. Eksperimen tidak mendukung klaim akurasi model, presisi
prediksi di atas 80/90 persen, load test dua juta pesan, atau generalisasi ke
banyak bangunan. Perbandingan lapangan dengan meter kWh PLN dicatat sebagai
informasi dari peneliti, tetapi paket ini belum dapat melaporkan galatnya tanpa
rekaman interval pembanding.
"""
    (args.destination / "RESULTS.md").write_text(
        report, encoding="utf-8"
    )

    reproducibility_sources = [
        Path("run_experiment.py"),
        Path("configs/experiment.json"),
        Path("requirements.txt"),
        Path("scripts/build_evaluation_notebook.py"),
        Path("notebooks/01_evaluasi_final.ipynb"),
        Path("src/data/audit_trace.py"),
        Path("src/data/prepare_historical_replay.py"),
        Path("src/benchmark/edge_cloud_benchmark.py"),
        Path("src/replay/replay_server.py"),
        Path("src/reporting/generate_figures.py"),
        Path("src/reporting/generate_final_report.py"),
        Path("schemas/telemetry.schema.json"),
        Path("tests/test_pipeline.py"),
    ]
    frontend_root = Path(
        "Digital_Twin/dashboard_digitaltwin/view_virtual"
    )
    reproducibility_sources.extend(
        [
            frontend_root / "package.json",
            frontend_root / "package-lock.json",
            frontend_root / "vite.config.js",
            frontend_root / "vitest.config.js",
            frontend_root / "index.html",
            *sorted((frontend_root / "src").rglob("*.js")),
            *sorted((frontend_root / "src").rglob("*.vue")),
            *sorted((frontend_root / "src").rglob("*.css")),
        ]
    )
    reproducibility_sources.extend(
        sorted(
            path
            for path in (frontend_root / "public/models").rglob("*")
            if path.is_file()
        )
    )
    packaged_outputs = sorted(
        path
        for path in args.destination.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    )
    manifest_files = {
        str(path): _entry(path)
        for path in reproducibility_sources + packaged_outputs
        if path.exists()
    }
    manifest_files[str(reference_path)] = _entry(
        reference_path, trace_audit["source"]["sha256"]
    )
    manifest_files[str(replay_path)] = _entry(
        replay_path, replay_audit["source"]["sha256"]
    )
    manifest = {
        "evaluation_type": summary["evaluation_type"],
        "project_title": config["project"]["title"],
        "claim_scope": summary["claim_scope"],
        "lineage_classification": replay_audit["lineage"][
            "classification"
        ],
        "files": manifest_files,
        "provenance_statement": replay_audit["provenance"][
            "relationship"
        ],
        "manifest_note": (
            "artifact_manifest.json excludes its own hash; timing metrics "
            "may vary between hosts while lineage and seeded routing counts "
            "remain reproducible."
        ),
    }
    (args.destination / "artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Paket hasil tersimpan: {args.destination}")


if __name__ == "__main__":
    main()
