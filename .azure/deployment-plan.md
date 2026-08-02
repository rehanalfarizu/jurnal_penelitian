# Azure Deployment Plan

> **Status:** Deployed

Generated: 2026-08-02 (Asia/Jakarta)

---

## 1. Project Overview

**Goal:** Memulihkan jalur telemetry Azure live, menyelaraskan source Azure
Functions dengan repository, dan menghasilkan benchmark public-cloud yang
terukur serta terpisah dari baseline replay/emulasi.

**Path:** Modify Existing

**Scope:** Code-only redeployment ke resource yang sudah ada. Rencana ini tidak
membuat atau menghapus Resource Group, Function App, IoT Hub, Storage Account,
atau device identity.

---

## 2. Requirements

| Attribute | Value |
|---|---|
| Classification | POC penelitian |
| Scale | Small; benchmark terkontrol, bukan layanan produksi |
| Budget | Cost-optimized; gunakan resource Azure for Students yang sudah ada |
| Subscription | Azure for Students |
| Location | Southeast Asia (`southeastasia`) |
| Data residency | Tetap pada region resource yang sudah ada |
| Security | Secret hanya di Azure App Settings/CLI session; tidak disimpan di repository atau artefak hasil |
| Measurement scope | Latensi dan keberhasilan jalur public cloud Azure; bukan kalibrasi metrologi sensor |

### Policy Constraints

- `sys.regionrestriction` mengizinkan `southeastasia`.
- `SecurityCenterBuiltIn` aktif.
- Tidak ada resource baru sehingga tidak ada perubahan kapasitas/quota.

---

## 3. Components Detected

| Component | Type | Technology | Path/Resource |
|---|---|---|---|
| Telemetry functions | Azure Functions | Node.js, Azure Tables | `Digital_Twin/dashboard_digitaltwin/sensor_iot/azure_setup/azure-function` |
| Public function host | Existing Function App | Azure Functions | `func-digitaltwin-2026` |
| Device messaging | Existing IoT Hub | Azure IoT Hub F1 | `iothub-digitaltwin-2026` |
| Telemetry persistence | Existing Storage Account | Azure Table Storage | `stordigitaltwin2026v2` |
| Replay benchmark | Local experiment | Python | `src/benchmark`, `src/replay` |
| Digital Twin UI | SPA | Vue/Babylon.js | `Digital_Twin/dashboard_digitaltwin/view_virtual` |

### Current Live Findings

- Function host root: HTTP 200.
- `GetTelemetryData`: HTTP 200 setelah pembaruan connection string.
- `SaveSensorData`: kontrak valid terdeploy; request tanpa body menghasilkan
  HTTP 400 dengan `INVALID_SENSOR_DATA`, sedangkan replay valid tersimpan pada
  `BenchmarkTelemetry`.
- Deployed functions tetap `ExportSensorData`, `GetTelemetryData`, dan
  `SaveSensorData`; `.funcignore` mencegah fungsi legacy tidak terpakai ikut
  masuk deployment surface.
- IoT identities `ESP32_ENERGY_MONITOR_001`, `RASPBERRY_PI_GATEWAY_001`, dan
  `RASPBERRY_PI_CAMERA_001` enabled tetapi disconnected.
- `STORAGE_CONNECTION_STRING` telah diarahkan ulang secara aman ke current key
  `stordigitaltwin2026v2`; nilai rahasia tidak dicatat.
- `WEBSITE_NODE_DEFAULT_VERSION` diatur ke `~22`; konfigurasi package
  menggunakan `WEBSITE_RUN_FROM_PACKAGE=1` dan dependency produksi ikut
  disertakan dalam ZIP deployment.

---

## 4. Recipe Selection

**Selected:** AZCLI, code-only update of an existing Azure Function App.

**Rationale:** Infrastruktur sudah tersedia dan aktif. Perubahan yang diperlukan
adalah validasi/build package Function, deployment source ke Function App yang
sama, dan verifikasi endpoint; tidak diperlukan provisioning IaC baru.

Template discovery `functions_template_get` tidak tersedia pada toolset sesi
ini dan tidak diperlukan untuk jalur modify-existing: aplikasi memakai source
HTTP-trigger programming model v3 yang sudah ada, tanpa pembuatan IaC/resource.

---

## 5. Architecture

**Stack:** Serverless

`Historical replay / edge client -> HTTP Azure Function -> Azure Table Storage
-> telemetry read API -> benchmark results / Digital Twin UI`

IoT Hub tetap dicatat sebagai bagian implementasi lapangan lama. Karena seluruh
device sekarang disconnected, benchmark public-cloud yang dapat direproduksi
akan memakai payload replay historis dari edge client, bukan mengklaim streaming
sensor fisik live.

### Service Mapping

| Component | Azure Service | Existing SKU |
|---|---|---|
| Telemetry write/read API | Function App `func-digitaltwin-2026` | Existing App Service plan |
| Device identities | IoT Hub `iothub-digitaltwin-2026` | F1 |
| Telemetry tables | Storage `stordigitaltwin2026v2` | Standard_LRS |
| Runtime observability | Application Insights `func-digitaltwin-2026` | Existing |

Runtime target dan konfigurasi aktif adalah Azure Functions v4 dengan Node.js
22 pada Windows. Node.js 22 dipilih karena didukung untuk programming model v3
dan Windows Functions.
Rujukan resmi: <https://learn.microsoft.com/azure/azure-functions/functions-reference-node>.

### Supporting Services

| Service | Purpose |
|---|---|
| Application Insights | Invocation/error evidence and server-side duration |
| Azure App Settings | Secret/configuration storage |
| Azure Table Storage | Persisted live benchmark payloads |

---

## 6. Provisioning Limit Checklist

No resources will be provisioned. Code deployment does not increase resource
counts or consume additional regional quota.

| Resource Type | Number to Deploy | Total After Deployment | Limit/Quota | Notes |
|---|---:|---:|---|---|
| `Microsoft.Web/sites` | 0 | 1 | Unchanged | Existing Function App; code-only update |
| `Microsoft.Devices/IotHubs` | 0 | 1 | Unchanged | Existing F1 hub |
| `Microsoft.Storage/storageAccounts` | 0 | 2 | Unchanged | Existing accounts in `rg-digitaltwin` |

**Status:** All resource counts remain unchanged; quota/capacity provisioning
check is not applicable to this code-only deployment.

---

## 7. Execution Checklist

### Phase 1: Planning

- [x] Analyze workspace and active Azure resources
- [x] Record research classification, scale, budget, subscription, and location
- [x] Scan codebase and deployed function inventory
- [x] Check subscription policy assignments
- [x] Select code-only AZCLI recipe
- [x] Plan serverless architecture and measurement boundary
- [x] User approved this plan

### Phase 2: Execution

- [x] Preserve current deployment metadata and App Setting names without secret values
- [x] Reproduce the deployed contract mismatch and verify the corrected HTTP 400 contract in the local Functions runtime
- [x] Align write/read table schema and add explicit benchmark probe identity
- [x] Add automated tests for validation, write response, and provenance fields
- [x] Build a validated source package containing only the three deployed HTTP functions; secret-pattern scan is clean
- [x] Update this plan to `Ready for Validation`

### Phase 3: Validation

- [x] Validate Node/Azure Functions package and dependencies
- [x] Run source tests and static secret scan
- [x] Verify Azure App Settings names and Storage access
- [x] Record validation proof below
- [x] Update plan to `Validated`

### Phase 4: Deployment

- [x] Deploy validated package to `func-digitaltwin-2026`
- [x] Verify `https://func-digitaltwin-2026.azurewebsites.net`
- [x] Verify protected write and anonymous read endpoints
- [x] Run controlled Azure-live benchmark with replay payloads
- [x] Generate separate Azure-live JSON, CSV, graph, and journal-ready result text
- [x] Keep prior replay/emulation result as controlled baseline
- [x] Update plan to `Deployed`

---

## 8. Validation Proof

This section may only be populated by the Azure validation workflow after the
plan is approved and all checks actually run.

| Check | Command Run | Result | Timestamp |
|---|---|---|---|
| Python pipeline and live-benchmark tests | `python -m unittest discover -s tests -v` | 11/11 passed | 2026-08-02T16:34:11Z |
| Function syntax and contract tests | `npm run check`; `npm test` | 7/7 passed, including missing-table recovery | 2026-08-02T16:35:59Z |
| Runtime indexing and route contract | `func start --functions ...`; local POST `{}` | 3 functions loaded; expected HTTP 400 + version marker | 2026-08-02T16:34:11Z |
| Production dependency audit | `npm audit --omit=dev --audit-level=high` | 0 vulnerabilities after dependency minimization and compatible transitive update | 2026-08-02T16:35:59Z |
| Source/package secret-pattern scan | `rg`; ZIP content scan | No active credential pattern found | 2026-08-02T16:35:59Z |
| Azure configuration names/runtime | Azure CLI read-only queries | Required setting names present; Functions v4/Node; Node target `~22` documented | 2026-08-02T16:34:11Z |
| Storage target/access | Azure CLI with in-memory App Setting value | Expected account; `SensorTelemetry` exists | 2026-08-02T16:34:11Z |
| Protected endpoint key availability | Azure CLI key existence check | Available; value not printed or stored | 2026-08-02T16:34:11Z |
| Validated source package | ZIP manifest + SHA-256 | 16 KiB; 3 HTTP functions; SHA-256 recorded in inventory | 2026-08-02T16:35:59Z |

**Validated by:** Codex Azure validation workflow

**Validation timestamp:** 2026-08-02T16:35:59Z

### Deployment and live-measurement proof

| Check | Result | Timestamp |
|---|---|---|
| ZIP deployment to existing Function App | Succeeded; three HTTP functions indexed | 2026-08-02T16:43:56Z |
| Runtime after deployment | Functions v4, Node.js `~22`, package mode enabled | 2026-08-02T16:43:56Z |
| Public host and read route | Root HTTP 200; `GetTelemetryData` HTTP 200 | 2026-08-02T16:46:00Z |
| Protected write contract | Missing-key HTTP 401; temporary benchmark key valid; empty body HTTP 400 with `INVALID_SENSOR_DATA` | 2026-08-02T16:48:00Z |
| Azure live benchmark | 5 warmup + 200 measured; 200 HTTP 200; 0 errors; 100% deadline compliance | 2026-08-02T16:57:05Z |
| Storage persistence | 205 `BenchmarkTelemetry` entities confirmed | 2026-08-02T16:59:00Z |
| Temporary key cleanup | `azureLiveBenchmark` key deleted after measurement; no key value stored in repository | 2026-08-02T17:00:00Z |

Detailed metrics are in `results/final/azure_live_metrics.json`; the benchmark
is reproducible with `scripts/run_azure_live_benchmark.py`. The Azure live
measurement uses replay payloads from the archived field trace. It does not
claim that a physical ESP32/Raspberry Pi stream was active during this run.

---

## 9. Files to Generate or Update

| File | Purpose | Status |
|---|---|---|
| `.azure/deployment-plan.md` | Deployment source of truth | Created |
| `.azure/predeployment-inventory.json` | Non-secret snapshot of active app metadata | Created |
| Azure Function source/tests | Correct live write/read behavior | Prepared |
| Live benchmark script | Measure real HTTPS Azure route | Deployed and executed |
| `results/final/azure_live_*` | Separate live-cloud evidence | Generated and verified |
| README/method/results | Distinguish Azure live from emulation and state limits | Updated |

---

## 10. Approval Boundary

Approval authorizes a code-only deployment to the existing Function App and a
controlled replay benchmark. It does not authorize deletion, resource creation,
key rotation, IoT device reactivation, or claims of live physical sensing.

**Current phase:** Deployed and verified; Azure live benchmark completed with
replay payloads and separate evidence artifacts.
