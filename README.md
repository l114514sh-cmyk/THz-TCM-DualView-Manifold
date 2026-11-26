# Thickness-Resilient, Repeatability-Guided Terahertz Chemometrics with Conformal and Out-of-Distribution Reliability Across Botanical Matrices (`TIRG-THz`)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-green.svg)](https://www.python.org/)
[![Validation: Pellet-Grouped Nested CV](https://img.shields.io/badge/Validation-Pellet--Grouped%20Nested%20CV-brightgreen.svg)](#reproducibility--verification)

This repository contains the reproducible chemometric analysis pipeline, cached dual-channel Terahertz Time-Domain Spectroscopy (THz-TDS) datasets (0.22–1.04 THz), non-circular optical physics stress tests, pellet-grouped double-nested cross-validation scripts, 500-permutation leakage audits, out-of-distribution (OOD) / conformal reliability evaluations, and 300 DPI publication figures accompanying our manuscript:

> **Thickness-Resilient, Repeatability-Guided Terahertz Chemometrics with Conformal and Out-of-Distribution Reliability Across Botanical Matrices**  
> Sihao Liu<sup>a</sup> (`liu3100853087@gmail.com`), Ziyuan Zhu<sup>a</sup>, Hongjun Xiang<sup>a</sup>, Wenjing Li<sup>a</sup>, Yin Shen<sup>a,\*</sup> (`shenyin285819016@126.com`, ORCID: `0000-0002-3221-7875`)  
> *<sup>a</sup>Chongqing Medical University, Chongqing 400016, China*

---

## Key Highlights (CHEMOLAB V2.1)

- **Thickness-Invariant Dielectric Ratio $\rho_{\text{TF}}(\omega)$ & Non-Circular Optical Stress Tests**: Ratios single-sample absorption coefficient $\alpha(\omega)$ against refractive-index excess $(n(\omega)-1)$ to cancel first-order thickness $d$ dependence. Under non-circular optical stress tests (`seed = 42`, nominal pellet thickness $d_0 = 0.15\text{ cm}$, $\pm 10\%$ thickness errors across 5 random draws):
  - **F1 (Exact Nonlinear Fresnel Mis-Entry)**: `Amp-Retaining Dual-View` drops `-7.82%` on average across the three matrices, whereas `TIRG-THz (Sup)` (`-0.02%`) and `TIRG-THz (Unsup R_j)` (`-0.08%`) remain stable.
  - **F2 (Full Complex Fabry–Pérot + Beer–Lambert + `-68 dB` Noise Floor)**: `Amp-Retaining Dual-View` drops `-10.30%` on average (`83.89%`) and `SNV-Only` drops `-3.11%` (`89.19%`), whereas `TIRG-THz (Sup)` holds `93.23%` (`-1.17%`) and `TIRG-THz (Unsup R_j)` holds `92.25%` (`-1.78%`).
  - **F2-S2 ($\pm 15\%$ All-Pellet Physical FP+DR End-to-End Retrain, 3 draws)**: `TIRG-THz (Sup)` achieves `93.39%` (`-1.01%`) and `TIRG-THz (Unsup R_j)` achieves `92.95%` (`-1.08%`), compared with `90.16%` (`-4.02%`) for `Amp-Retaining Dual-View`.
- **Unsupervised Repeatability Prior $R_j(\omega)$ & `88.2×` Speedup**: Exploits training-fold intra-pellet versus inter-pellet variance ratios without class labels, matching supervised MC-UVE across 3 seeds (`42, 100, 2026`: `94.32%` scan / `96.64%` pellet vs. `94.44%` / `96.78%`) while running `88.2×` faster (`0.0154 s/fold` vs. `1.3597 s/fold`). Directly grounded in measured `TERA K15` sample transmission dynamic range $\text{DR}(\omega)$ (`Spearman ρ = 0.8955` on *Astragali Radix*, `0.8964` on *Ziziphi Spinosae Semen*, `0.8491` on *Gastrodia elata*; all `p < 1e-99`).
- **Pellet-Grouped Double-Nested CV & 500-Permutation Audit**: Outer 5-Fold / Inner 3-Fold Pellet-Grouped `StratifiedGroupKFold` across 1,300 QC-retained spectra (`1.2 ≤ mean(n) ≤ 2.6`, `mean(α) ≤ 55.0 cm⁻¹`) covering 262 pellets across three botanical matrices (*Astragali Radix* root, *Ziziphi Spinosae Semen* seed, *Gastrodia elata* tuber). 500-permutation pellet-level Y-scrambling confirms `p = 0.0020` (`0/500 >= obs`) across all three matrices; differential blind-test perturbation probe yields `0.00e+00 (0/79 flips)`; ungrouped replicate splitting inflates root accuracy by `+7.30%`. Includes fair PyTorch deep-learning baselines (`Dual-View MLP` `92.06%`, `1D-CNN/ResNet/Transformer` `73.65%–76.76%`).
- **Dual-Mechanism OOD Detection & Split-Conformal Coverage**: Demonstrates LDA `T²` subspace collapse on unseen-origin pellets (C2 AUROC `0.3205–0.4701`), rescued by orthogonal residual `Q_res` (`0.6814–0.8770`) and probability uncertainty `U_prob` (`0.8208–0.9483`), alongside split-conformal coverage (`α = 0.10`: `95.0%–100.0%` in-house pellets) and an external negative-control stress test on the public NTHU Mendeley ginseng dataset (`DOI: 10.17632/hvbp5mdtxx.2`, 42 tablets, 6 groups; LOGO accuracy `50.0%`, conformal coverage `92.86%`, average set size `1.79`, `21.43%` singletons).

---

## Repository Structure

```text
.
├── requirements.txt                                   # Exact tested core Python dependencies
├── draw_pipeline.py                                   # Archived V1 Scheme 1 generator
└── THz_TCM_Research/
    ├── 01_原始实验数据/                                 # Cached .npz dual-channel spectra (0.22–1.04 THz)
    │   ├── 黄芪/huangqi_fast_cache.npz
    │   ├── 酸枣仁/suanzaoren_fast_cache.npz
    │   └── 天麻/tianma_fast_cache.npz
    ├── 04_Python数据处理/
    │   ├── run_chemolab_v2_master.py                  # CHEMOLAB V2.1 master pipeline (3-seed CV, 500-perm, DL, OOD, Conformal)
    │   ├── run_chemolab_v21_physics_addendum.py       # Non-circular F1/F2/F2-S2 optical physics & measured DR(ω) correlation
    │   ├── plot_chemolab_v2_figures.py                # Generates all 9 300 DPI CHEMOLAB V2.1 figures (Scheme 1, Fig 1–6, S1–S2)
    │   ├── run_unified_double_nested_all.py           # Archived V1 pipeline (retained for traceability)
    │   └── run_strict_leakage_audit.py                # Archived V1 leakage audit (retained for traceability)
    ├── 05_实验结果/
    │   ├── CHEMOLAB_V2/
    │   │   ├── CHEMOLAB_V2_Master_Summary.json        # Machine-readable V2.1 benchmarks, audits & physics stress results
    │   │   └── CHEMOLAB_V2_Plot_Data.npz              # Cached plot arrays & measured spectra/DR curves
    │   └── 模型结果/                                   # Archived V1 result summaries
    └── 06_论文写作/
        └── CHEMOLAB_V2_Figures/                       # All 9 300 DPI V2.1 figures (Scheme 1, Fig 1–6, S1–S2)
```

---

## Reproducibility & Verification

All public analysis scripts use **project-relative paths** (`Path(__file__).resolve()`) and run directly from the repository root with zero local path modifications:

```bash
# 1. Install core dependencies (Python 3.12+) plus PyTorch for deep-learning baselines
pip install -r requirements.txt
pip install torch

# 2. (Optional) External Mendeley Ginseng negative-control stress test:
# Download the NTHU THz Ginseng dataset from https://doi.org/10.17632/hvbp5mdtxx.2
# and extract the CSV files into:
# THz_TCM_Research/01_原始实验数据/External_Ginseng_Mendeley/Dataset/

# 3. Run V2.1 master experiment (3-seed nested CV, 500-perm audit, DL baselines, OOD & conformal)
python THz_TCM_Research/04_Python数据处理/run_chemolab_v2_master.py

# 4. Run non-circular F1 Fresnel & F2 Full Complex FP+DR stress tests + measured DR(ω) correlation
python THz_TCM_Research/04_Python数据处理/run_chemolab_v21_physics_addendum.py

# 5. Regenerate all 9 300 DPI figures into THz_TCM_Research/06_论文写作/CHEMOLAB_V2_Figures/
python THz_TCM_Research/04_Python数据处理/plot_chemolab_v2_figures.py
```

---

## Data Availability & Citation

The cached dual-channel THz-TDS spectra (`.npz`), `TIRG-THz` analysis scripts, V2.1 summary JSON/NPZ outputs, and 300 DPI figures are publicly provided in this repository. External benchmark tablets are cited via their public Mendeley Data DOI (`https://doi.org/10.17632/hvbp5mdtxx.2`). Raw instrument `.xlsx` files were acquired by previous students in Yin Shen's research group and provided by Yin Shen (Chongqing Medical University) as part of a shared research resource. For inquiries regarding raw time-domain exports or collaboration, please contact the corresponding author: **Yin Shen** (`shenyin285819016@126.com`).
