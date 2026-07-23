# Architecture Spec — Strategi A: Multimodal Transformer + GNN-DT

> **Judul paper (working):** *Edge-Cloud Collaborative Digital Twin with Multimodal Transformer for Real-Time Energy Prediction in Smart Buildings*

## 1. Visi Arsitektur (Single Unified)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        EDGE LAYER (Real-Time)                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │ Vision Encoder  │  │ Sensor Encoder  │  │ Text/Metadata   │           │
│  │ (MobileNet-V3)  │  │ (1D-CNN/Tiny    │  │ Encoder (Mini   │           │
│  │                 │  │  Transformer)   │  │  BERT/Embedding)│           │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘           │
│           │                    │                    │                    │
│           └────────────────────┼────────────────────┘                    │
│                                ↓                                        │
│                  ┌──────────────────────────┐                            │
│                  │ Edge Feature Aggregator │  (<10ms latency)            │
│                  │ (concatenate + norm)    │                            │
│                  └──────────┬───────────────┘                            │
└─────────────────────────────┼────────────────────────────────────────────┘
                              ↓ (bandwidth-limited stream)
┌─────────────────────────────┼────────────────────────────────────────────┐
│                       CLOUD LAYER                                         │
│                             ↓                                             │
│  ┌──────────────────────────────────────────────────────────┐             │
│  │   Multimodal Transformer Fusion (cross-attention)         │             │
│  │   - Query: Vision, Key/Value: Sensor+Time                │             │
│  │   - Multi-head attention (8 heads, d_model=256)           │             │
│  └──────────────────────────┬───────────────────────────────┘             │
│                              ↓                                            │
│  ┌──────────────────────────────────────────────────────────┐             │
│  │   GNN-DT (Digital Twin State Sync)                        │             │
│  │   - Building graph: HVAC ↔ Zone ↔ Sensor ↔ Actuator      │             │
│  │   - GAT (Graph Attention) layer x3                        │             │
│  │   - Kalman Filter untuk real-time state estimation        │             │
│  └──────────────────────────┬───────────────────────────────┘             │
│                              ↓                                            │
│  ┌──────────────────────────────────────────────────────────┐             │
│  │   Energy Prediction Head (Informer)                       │             │
│  │   - Long-horizon forecasting (24h, 7d)                    │             │
│  │   - ProbSparse self-attention untuk efisiensi             │             │
│  └──────────────────────────────────────────────────────────┘             │
└───────────────────────────────────────────────────────────────────────────┘
```

## 2. Komponen Detail

### 2.1 Edge Encoders
| Encoder | Input | Output Dim | Model | Latency Target |
|---|---|---|---|---|
| **Vision** | Camera frames (224×224×3) | 128-d | MobileNet-V3-Small (pretrained, frozen) | <20ms |
| **Sensor** | Multivariate time series (N×T×F) | 128-d | 1D-CNN atau Tiny-Transformer | <5ms |
| **Metadata** | Building specs, weather API, time | 64-d | Embedding layer | <1ms |

### 2.2 Multimodal Transformer (Cloud)
- **Input:** Concatenated edge features (vision + sensor + metadata)
- **Architecture:**
  - Linear projection → d_model=256
  - Positional encoding (sinusoidal)
  - **Cross-attention block:** Vision tokens sebagai Query, Sensor+Time sebagai Key/Value
  - Multi-head (8), FFN dim=1024
  - 4 layers, dropout=0.1
- **Output:** Unified embedding (256-d) per timestep

### 2.3 GNN-DT (Cloud)
- **Graph structure:** Building topology
  - Nodes: Zones (room), HVAC units, Sensors, Actuators
  - Edges: Physical (duct, pipe) + Functional (control signal)
- **GAT layers:** 3× Graph Attention (hidden=128, heads=4)
- **Kalman Filter:** State vector = [temperature, CO2, occupancy, energy_flow]
- **Output:** Synchronized DT state (real-time estimate + uncertainty)

### 2.4 Energy Prediction (Informer)
- **Input:** DT state time-series (24h history)
- **Architecture:** Informer encoder (ProbSparse attention)
- **Output horizon:** 1h, 6h, 24h, 7d
- **Loss:** MSE + Quantile loss (untuk uncertainty)

## 3. Training Strategy

### 3.1 Two-Stage Training
1. **Stage 1 (Edge pretraining):** Train MobileNet-V3 (vision) + 1D-CNN (sensor) pada labeled building dataset secara terpisah
2. **Stage 2 (Cloud joint training):** Freeze edge encoders, train Multimodal Transformer + GNN + Informer end-to-end dengan loss gabungan

### 3.2 Loss Function
```
L_total = λ1 * L_fusion + λ2 * L_dt_state + λ3 * L_energy_pred
       = 0.2 * L_contrastive + 0.3 * L_kalman + 0.5 * L_energy_MSE
```

### 3.3 Datasets (target)
- **Vision:** CCTV building (synthetic via Unity atau real)
- **Sensor:** ASHRAE 2019, BDG2, atau UCI Individual Household Electric Power Consumption
- **Metadata:** Weather (OpenWeatherMap API), time, building specs
- **Energy ground truth:** Smart meter readings

## 4. Evaluasi (Counterfactual: 3 Skenario)

| Skenario | Deskripsi | Expected Result |
|---|---|---|
| **FULL_EDGE** | Semua inference di edge, no cloud | Low latency, high latency variance, lower accuracy |
| **EDGE_PREFERRED** (proposed) | Edge untuk filtering, cloud untuk heavy inference | Optimal balance |
| **FULL_CLOUD** | Semua dikirim ke cloud | High latency, best accuracy |

Metrics: **MAE, RMSE, MAPE, latency, bandwidth, energy consumption, DT sync error**

## 5. Novelty Claims (vs 27 PDF existing)

1. **Unified architecture** — belum ada jurnal yang gabungkan Multimodal Transformer + GNN-DT + Informer dalam satu end-to-end pipeline untuk building
2. **Cross-modal attention dengan DT state** — Inovasi: DT state jadi query, sensor+vision jadi key/value
3. **Counterfactual 3-skenario** — hanya ada 1 jurnal (SciencePress CCIS 2023) yang bandingkan cloud vs edge, tapi tanpa DT atau multimodal

## 6. Implementation Plan (akan di-code)

| Step | Output | Tech Stack |
|---|---|---|
| 1 | Dataset loader (ASHRAE + synthetic multimodal) | PyTorch |
| 2 | Edge encoders (MobileNet-V3 + 1D-CNN) | torchvision + custom |
| 3 | Multimodal Transformer fusion | PyTorch nn.Module |
| 4 | GNN-DT (GAT + Kalman) | PyTorch Geometric |
| 5 | Informer forecasting head | Custom (atau Autoformer lib) |
| 6 | End-to-end training loop | PyTorch Lightning |
| 7 | Counterfactual evaluation (3 skenario) | Custom benchmark |
| 8 | Visualization + paper figures | matplotlib + plotly |

## 7. Dependencies (akan di-install)

```
torch>=2.0
torchvision
torch-geometric
pytorch-lightning
numpy, pandas, scikit-learn
matplotlib, plotly, seaborn
tqdm
pyyaml
```