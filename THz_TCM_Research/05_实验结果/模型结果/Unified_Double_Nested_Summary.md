# Unified Double-Nested 5-Fold CV Results (Dual-View SW-MCUVE-Manifold Framework)

Generated with `SEED = 42`, Outer 5-Fold Stratified CV + Inner 3-Fold Stratified CV, 100% intra-sample dual-view physical preprocessing (Scattering-Invariant SNV Morphology + Amplitude-Preserving Dielectric Scale), zero cross-sample leakage.

## Astragali Radix (Root) (n = 397 post-QC, raw = 403, dropped = 6)
- **Physical QC**: Unsupervised optical bound `1.2 <= n <= 2.6` & global `3xIQR` absorption fence (dropped: `{'Guyang (IM)': 5, 'Gansu (GS)': 1}`)
- **Post-QC Dual-Channel Fisher Separability ($S_B/S_W$)**: `0.2999`
- **Overall Double-Nested 5-Fold CV Accuracy**: **93.20%** (5-Fold Mean ± SD: **93.19% ± 2.73%**)
- **Macro-Averaged Metrics**: Precision `93.35%`, Recall `93.21%`, Macro-F1 `0.9321`
- **Outer Fold Accuracies**: `[92.5, 97.5, 94.94, 89.87, 91.14]`

### Per-Class Classification Metrics
| Class | n | Correct | Precision (%) | Recall (%) | F1-Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Datong (SX) | 103 | 92 | 94.85 | 89.32 | 0.9200 |
| Guyang (IM) | 95 | 87 | 96.67 | 91.58 | 0.9405 |
| Qujing (YN) | 100 | 96 | 91.43 | 96.00 | 0.9366 |
| Gansu (GS) | 99 | 95 | 90.48 | 95.96 | 0.9314 |
| **Overall / Macro** | **397** | **370** | **93.35** | **93.21** | **0.9321** |

### Ablation Study (Double-Nested 5-Fold CV)
| Configuration | Overall Acc (%) | Mean ± SD (%) | Delta Acc (%) | Macro-F1 |
| :--- | :---: | :---: | :---: | :---: |
| Full Proposed (Dual-View SW-MCUVE-Manifold) | 93.20 | 93.19 ± 2.73 | Reference | 0.9321 |
| w/o Amplitude-Preserving View (SNV Only) | 89.67 | 89.66 ± 4.02 | -3.53% | 0.8971 |
| w/o Intra-Sample SNV View (Amplitude Only) | 88.92 | 88.91 ± 3.78 | -4.28% | 0.8891 |
| w/o Purified Manifold (lambda=0) | 92.19 | 92.18 ± 2.46 | -1.01% | 0.9220 |
| w/o Refractive Index (Abs Only) | 93.70 | 93.70 ± 1.13 | +0.50% | 0.9375 |

### Baseline Model Comparison (Double-Nested 5-Fold CV)
| Model | Overall Acc (%) | Mean ± SD (%) | Macro-Precision (%) | Macro-Recall (%) | Macro-F1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| PLS-DA | 82.87 | 82.86 ± 3.85 | 83.26 | 82.84 | 0.8296 |
| Random Forest | 84.13 | 84.11 ± 5.33 | 84.90 | 84.05 | 0.8420 |
| Standard RBF-SVM (Full Spectrum) | 89.67 | 89.65 ± 3.91 | 89.68 | 89.65 | 0.8965 |
| Hard MC-UVE-SVM (Gen-1 Baseline) | 88.92 | 88.90 ± 3.65 | 88.90 | 88.83 | 0.8885 |
| Proposed (Dual-View SW-MCUVE-Manifold) | 93.20 | 93.19 ± 2.73 | 93.35 | 93.21 | 0.9321 |

## Ziziphi Spinosae Semen (Seed) (n = 500 post-QC, raw = 500, dropped = 0)
- **Physical QC**: Unsupervised optical bound `1.2 <= n <= 2.6` & global `3xIQR` absorption fence (dropped: `{}`)
- **Post-QC Dual-Channel Fisher Separability ($S_B/S_W$)**: `1.1268`
- **Overall Double-Nested 5-Fold CV Accuracy**: **97.40%** (5-Fold Mean ± SD: **97.40% ± 1.62%**)
- **Macro-Averaged Metrics**: Precision `97.41%`, Recall `97.40%`, Macro-F1 `0.9740`
- **Outer Fold Accuracies**: `[99.0, 98.0, 95.0, 96.0, 99.0]`

### Per-Class Classification Metrics
| Class | n | Correct | Precision (%) | Recall (%) | F1-Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Boxed (HB) | 100 | 99 | 98.02 | 99.00 | 0.9851 |
| SJZ/BZ | 100 | 98 | 98.99 | 98.00 | 0.9849 |
| Bulk-Bag | 100 | 96 | 95.05 | 96.00 | 0.9552 |
| Bulk-50g | 100 | 95 | 95.00 | 95.00 | 0.9500 |
| Tongrentang (AH) | 100 | 99 | 100.00 | 99.00 | 0.9950 |
| **Overall / Macro** | **500** | **487** | **97.41** | **97.40** | **0.9740** |

### Ablation Study (Double-Nested 5-Fold CV)
| Configuration | Overall Acc (%) | Mean ± SD (%) | Delta Acc (%) | Macro-F1 |
| :--- | :---: | :---: | :---: | :---: |
| Full Proposed (Dual-View SW-MCUVE-Manifold) | 97.40 | 97.40 ± 1.62 | Reference | 0.9740 |
| w/o Amplitude-Preserving View (SNV Only) | 94.40 | 94.40 ± 2.50 | -3.00% | 0.9440 |
| w/o Intra-Sample SNV View (Amplitude Only) | 98.40 | 98.40 ± 0.80 | +1.00% | 0.9840 |
| w/o Purified Manifold (lambda=0) | 97.40 | 97.40 ± 1.96 | +0.00% | 0.9740 |
| w/o Refractive Index (Abs Only) | 97.20 | 97.20 ± 1.94 | -0.20% | 0.9720 |

### Baseline Model Comparison (Double-Nested 5-Fold CV)
| Model | Overall Acc (%) | Mean ± SD (%) | Macro-Precision (%) | Macro-Recall (%) | Macro-F1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| PLS-DA | 92.80 | 92.80 ± 1.72 | 92.97 | 92.80 | 0.9278 |
| Random Forest | 92.00 | 92.00 ± 1.67 | 92.07 | 92.00 | 0.9201 |
| Standard RBF-SVM (Full Spectrum) | 95.20 | 95.20 ± 1.33 | 95.25 | 95.20 | 0.9522 |
| Hard MC-UVE-SVM (Gen-1 Baseline) | 96.40 | 96.40 ± 2.06 | 96.45 | 96.40 | 0.9641 |
| Proposed (Dual-View SW-MCUVE-Manifold) | 97.40 | 97.40 ± 1.62 | 97.41 | 97.40 | 0.9740 |

## Gastrodia elata (Tuber, Cross-Matrix Validation) (n = 404 post-QC, raw = 405, dropped = 1)
- **Physical QC**: Unsupervised optical bound `1.2 <= n <= 2.6` & global `3xIQR` absorption fence (dropped: `{'Bozhou (AH)': 1}`)
- **Post-QC Dual-Channel Fisher Separability ($S_B/S_W$)**: `1.0064`
- **Overall Double-Nested 5-Fold CV Accuracy**: **99.75%** (5-Fold Mean ± SD: **99.75% ± 0.50%**)
- **Macro-Averaged Metrics**: Precision `99.75%`, Recall `99.75%`, Macro-F1 `0.9975`
- **Outer Fold Accuracies**: `[100.0, 100.0, 100.0, 100.0, 98.75]`

### Per-Class Classification Metrics
| Class | n | Correct | Precision (%) | Recall (%) | F1-Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Bozhou (AH) | 102 | 102 | 100.00 | 100.00 | 1.0000 |
| Leishan (GZ) | 100 | 100 | 100.00 | 100.00 | 1.0000 |
| Changbai (JL) | 102 | 101 | 100.00 | 99.02 | 0.9951 |
| Yunnan (YN) | 100 | 100 | 99.01 | 100.00 | 0.9950 |
| **Overall / Macro** | **404** | **403** | **99.75** | **99.75** | **0.9975** |

### Ablation Study (Double-Nested 5-Fold CV)
| Configuration | Overall Acc (%) | Mean ± SD (%) | Delta Acc (%) | Macro-F1 |
| :--- | :---: | :---: | :---: | :---: |
| Full Proposed (Dual-View SW-MCUVE-Manifold) | 99.75 | 99.75 ± 0.50 | Reference | 0.9975 |
| w/o Amplitude-Preserving View (SNV Only) | 98.76 | 98.76 ± 0.78 | -0.99% | 0.9877 |
| w/o Intra-Sample SNV View (Amplitude Only) | 99.01 | 99.01 ± 0.92 | -0.74% | 0.9901 |
| w/o Purified Manifold (lambda=0) | 99.50 | 99.50 ± 0.61 | -0.25% | 0.9951 |
| w/o Refractive Index (Abs Only) | 98.02 | 98.02 ± 2.00 | -1.73% | 0.9803 |

### Baseline Model Comparison (Double-Nested 5-Fold CV)
| Model | Overall Acc (%) | Mean ± SD (%) | Macro-Precision (%) | Macro-Recall (%) | Macro-F1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| PLS-DA | 97.52 | 97.52 ± 0.78 | 97.59 | 97.54 | 0.9751 |
| Random Forest | 96.53 | 96.53 ± 2.13 | 96.58 | 96.54 | 0.9655 |
| Standard RBF-SVM (Full Spectrum) | 95.30 | 95.30 ± 1.44 | 95.56 | 95.28 | 0.9535 |
| Hard MC-UVE-SVM (Gen-1 Baseline) | 98.02 | 98.02 ± 1.48 | 98.03 | 98.04 | 0.9803 |
| Proposed (Dual-View SW-MCUVE-Manifold) | 99.75 | 99.75 ± 0.50 | 99.75 | 99.75 | 0.9975 |
