# Unified Pellet-Grouped Double-Nested Cross-Validation Summary

- **Primary Validation Protocol**: Outer 5-Fold **Pellet-Grouped `StratifiedGroupKFold`** / Inner 3-Fold **Pellet-Grouped `StratifiedGroupKFold`** (each pellet's 5 replicate scans strictly locked in Train or Test; zero same-pellet leakage).
- **Unified Single-Spectrum Physical QC**: `1.2 <= mean(n) <= 2.6` and `mean(alpha) <= 55.0 cm^-1` (applied identically across all three botanical matrices).
- **Fair Input-Controlled Baselines**: Track A (identical 716-dim Raw Dual-Channel `[raw_a, raw_r]`) & Track B (identical 3,222-dim Dual-View `X_dual`).

## Astragali Radix (Fibrous Root) (n = 397 post-QC across 80 pellets; raw = 403, dropped = 6)
- **Pellet-Grouped 5-Fold CV Scan Accuracy**: **87.66%** (`87.64% ± 3.08%`, Macro-F1 `0.8769`)
- **Pellet-Level Majority-Vote Accuracy**: **92.50%** (`74/80` pellets)
- **Ungrouped Scan-Level Reference**: `93.20%` (replicate-scan optimism: `+5.54%`)

| Model (Input Representation) | Scan Acc (%) | Mean ± SD (%) | Pellet Vote (%) | Δ vs Proposed [95% CI] | p_boot |
| :--- | :---: | :---: | :---: | :---: | :---: |
| PLS-DA (Raw Dual-Channel) | 84.63 | 84.61 ± 4.56 | 90.00 | +3.02% [-1.51, +7.61] | 0.1960 |
| RF (Raw Dual-Channel) | 65.74 | 65.79 ± 5.87 | 75.00 | +21.91% [+16.50, +27.82] | 0.0005 |
| RBF-SVM (Raw Dual-Channel) | 81.61 | 81.61 ± 2.20 | 87.50 | +6.05% [+2.78, +9.32] | 0.0005 |
| PLS-DA (Dual-View 3222-d) | 83.12 | 83.10 ± 3.39 | 88.75 | +4.53% [+1.24, +8.08] | 0.0130 |
| RF (Dual-View 3222-d) | 84.89 | 84.86 ± 3.74 | 90.00 | +2.77% [-0.50, +6.30] | 0.1100 |
| RBF-SVM (Dual-View 3222-d) | 87.41 | 87.40 ± 4.05 | 91.25 | +0.25% [-1.78, +2.76] | 0.9340 |
| Hard MC-UVE-SVM (Dual-View 3222-d) | 88.41 | 88.39 ± 3.91 | 93.75 | -0.76% [-2.26, +0.26] | 0.3090 |
| **Proposed Dual-View SW-MCUVE-Manifold** | **87.66** | **87.64 ± 3.08** | **92.50** | Reference | — |

## Ziziphi Spinosae Semen (Lipid-Rich Seed) (n = 499 post-QC across 100 pellets; raw = 500, dropped = 1)
- **Pellet-Grouped 5-Fold CV Scan Accuracy**: **96.39%** (`96.40% ± 2.33%`, Macro-F1 `0.9640`)
- **Pellet-Level Majority-Vote Accuracy**: **100.00%** (`100/100` pellets)
- **Ungrouped Scan-Level Reference**: `96.99%` (replicate-scan optimism: `+0.60%`)

| Model (Input Representation) | Scan Acc (%) | Mean ± SD (%) | Pellet Vote (%) | Δ vs Proposed [95% CI] | p_boot |
| :--- | :---: | :---: | :---: | :---: | :---: |
| PLS-DA (Raw Dual-Channel) | 87.37 | 87.39 ± 6.52 | 94.00 | +9.02% [+5.60, +12.80] | 0.0005 |
| RF (Raw Dual-Channel) | 73.95 | 73.96 ± 6.54 | 81.00 | +22.44% [+17.43, +27.71] | 0.0005 |
| RBF-SVM (Raw Dual-Channel) | 84.77 | 84.79 ± 4.68 | 92.00 | +11.62% [+8.03, +15.40] | 0.0005 |
| PLS-DA (Dual-View 3222-d) | 91.18 | 91.19 ± 4.48 | 97.00 | +5.21% [+2.61, +8.02] | 0.0005 |
| RF (Dual-View 3222-d) | 90.38 | 90.39 ± 4.62 | 90.00 | +6.01% [+2.83, +9.40] | 0.0005 |
| RBF-SVM (Dual-View 3222-d) | 94.79 | 94.80 ± 2.56 | 100.00 | +1.60% [-0.20, +3.41] | 0.0970 |
| Hard MC-UVE-SVM (Dual-View 3222-d) | 93.99 | 94.00 ± 3.16 | 98.00 | +2.40% [+0.20, +4.80] | 0.0340 |
| **Proposed Dual-View SW-MCUVE-Manifold** | **96.39** | **96.40 ± 2.33** | **100.00** | Reference | — |

## Gastrodia elata (Starchy Tuber) (n = 404 post-QC across 82 pellets; raw = 405, dropped = 1)
- **Pellet-Grouped 5-Fold CV Scan Accuracy**: **98.51%** (`98.51% ± 0.51%`, Macro-F1 `0.9852`)
- **Pellet-Level Majority-Vote Accuracy**: **100.00%** (`82/82` pellets)
- **Ungrouped Scan-Level Reference**: `99.75%` (replicate-scan optimism: `+1.24%`)

| Model (Input Representation) | Scan Acc (%) | Mean ± SD (%) | Pellet Vote (%) | Δ vs Proposed [95% CI] | p_boot |
| :--- | :---: | :---: | :---: | :---: | :---: |
| PLS-DA (Raw Dual-Channel) | 99.01 | 99.00 ± 1.22 | 100.00 | -0.50% [-2.45, +1.25] | 0.7040 |
| RF (Raw Dual-Channel) | 88.37 | 88.32 ± 4.96 | 91.46 | +10.15% [+5.65, +15.10] | 0.0005 |
| RBF-SVM (Raw Dual-Channel) | 95.79 | 95.79 ± 3.28 | 97.56 | +2.72% [-0.25, +6.39] | 0.1110 |
| PLS-DA (Dual-View 3222-d) | 97.77 | 97.78 ± 2.09 | 98.78 | +0.74% [-0.98, +2.77] | 0.5510 |
| RF (Dual-View 3222-d) | 97.28 | 97.27 ± 1.22 | 100.00 | +1.24% [-0.73, +3.28] | 0.2590 |
| RBF-SVM (Dual-View 3222-d) | 96.53 | 96.54 ± 2.41 | 97.56 | +1.98% [-0.49, +5.15] | 0.1870 |
| Hard MC-UVE-SVM (Dual-View 3222-d) | 97.77 | 97.76 ± 2.67 | 98.78 | +0.74% [-0.50, +2.51] | 0.4830 |
| **Proposed Dual-View SW-MCUVE-Manifold** | **98.51** | **98.51 ± 0.51** | **100.00** | Reference | — |
