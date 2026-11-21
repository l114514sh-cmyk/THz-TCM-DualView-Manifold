# Dual-View Terahertz Spectroscopy and Stability-Weighted Chemometrics for Classification of Traditional Chinese Medicinal Materials Across Distinct Botanical Matrices

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-green.svg)](https://www.python.org/)
[![Validation: Pellet-Grouped Nested CV](https://img.shields.io/badge/Validation-Pellet--Grouped%20Nested%20CV-brightgreen.svg)](#reproducibility--verification)

This repository contains the reproducible chemometric analysis pipeline, cached dual-channel Terahertz Time-Domain Spectroscopy (THz-TDS) datasets (0.22–1.04 THz), pellet-grouped double-nested cross-validation scripts, input-controlled baseline benchmarks, multi-permutation leakage audits, and publication-grade figures accompanying our manuscript:

> **Dual-View Terahertz Spectroscopy and Stability-Weighted Chemometrics for Classification of Traditional Chinese Medicinal Materials Across Distinct Botanical Matrices**  
> Sihao Liu, Ziyuan Zhu, Hongjun Xiang, Wenjing Li, Yin Shen\*  
> *Chongqing Medical University, Chongqing, China*

---

## Key Highlights

- **Pellet-Grouped Double-Nested Cross-Validation**: Each pure-powder herbal pellet was scanned 5 times consecutively (~20 pellets × 5 scans per class). All primary evaluations enforce **Outer 5-Fold / Inner 3-Fold Pellet-Grouped `StratifiedGroupKFold`**, locking all replicate scans of any pellet strictly within either training or held-out test folds (zero same-pellet leakage), and report both **scan-level** and **pellet-level majority-vote** accuracies.
- **Unified Single-Spectrum Physical QC**: `1.2 ≤ mean(n) ≤ 2.6` and `mean(α) ≤ 55.0 cm⁻¹`, applied identically across all three botanical matrices and all audit scripts (1,300/1,308 spectra retained across 262 pellets).
- **Intra-Sample Dual-View Feature Representation (3,222-Dim)**: Combines **View 1** (scatter-attenuated intra-sample SNV + multi-scale Savitzky–Golay derivatives, 1,790-dim) and **View 2** (amplitude-preserving Savitzky–Golay dielectric envelope & derivatives, 1,432-dim) via strictly single-sample frequency-axis operations.
- **Input-Controlled Fair Benchmarks & Statistical Inference**: Compares PLS-DA, Random Forest, RBF-SVM, Hard MC-UVE-SVM, and Proposed Dual-View SW-MCUVE-Manifold under **both** identical raw dual-channel input (716-dim) and identical 3,222-dim Dual-View input, with paired pellet-cluster bootstrap 95% CIs.
- **Multi-Permutation Leakage Audit**: Includes differential blind-test perturbation probe (`0.00e+00`), raw-vs-QC comparison, multi-seed pellet-grouped stability, and 30-permutation pellet-level Y-scrambling with empirical *p*-values.
- **Tentative DFT Vibrational Benchmarks**: B3LYP-D3(BJ)/6-31G(d) gas-phase harmonic modes for Calycosin and Spinosin aligned against fold-averaged MC-UVE stability profiles.

---

## Repository Structure

```text
.
├── requirements.txt                                   # Exact tested Python dependencies
├── draw_pipeline.py                                   # Generates 300 DPI Scheme 1 (relative paths)
├── Pipeline_Flowchart_Clean.png                       # 300 DPI Scheme 1
├── Figure_1_THz_Spectra.png                           # 300 DPI Figure 1 (Mean ± SD & SG2)
├── Confusion_Matrix_SVM.png                           # 300 DPI Root Confusion Matrix
├── Suanzaoren_Confusion_Matrix.png                    # 300 DPI Seed Confusion Matrix
├── Figure 6.png                                       # 300 DPI DFT Vibrational Benchmarks
└── THz_TCM_Research/
    ├── 01_原始实验数据/                                 # Cached .npz dual-channel spectra (0.22–1.04 THz)
    │   ├── 黄芪/huangqi_fast_cache.npz
    │   ├── 酸枣仁/suanzaoren_fast_cache.npz
    │   └── 天麻/tianma_fast_cache.npz
    ├── 04_Python数据处理/
    │   ├── run_unified_double_nested_all.py           # Master Pellet-Grouped CV, Fair Baselines & Figures
    │   ├── run_strict_leakage_audit.py                # Differential Probe + 30-Perm Pellet Y-Scrambling
    │   ├── plot_dynamic_range.py                      # Measured THz-TDS Dynamic Range (requires raw .xlsx)
    │   └── build_submission_docx.py                   # Rebuilds EN Submission, Supp Material & Bilingual Docs
    ├── 05_实验结果/模型结果/
    │   ├── Unified_Double_Nested_Summary.json         # Machine-readable primary & baseline metrics
    │   ├── Unified_Double_Nested_Summary.md           # Human-readable summary tables
    │   ├── Strict_Leakage_Audit_Report.json           # Machine-readable audit & permutation p-values
    │   └── *.png                                      # 300 DPI ablation, baseline, DFT-alignment & DR figures
    └── 06_论文写作/
        ├── Submission_Figures/                        # All 300 DPI upload-ready figures (Scheme 1, Fig 1–7, S1–S2)
        ├── Manuscript_EN_Submission.docx              # Pure English journal submission manuscript
        ├── Supplementary_Material.docx                # Separate Supplementary Material
        ├── Manuscript_Bilingual_Reference.docx        # Bilingual EN+ZH reference copy
        ├── Cover_Letter.docx                          # Cover letter (Corresponding Author: Yin Shen)
        └── Highlights.docx                            # 5 highlights (≤ 85 characters each)
```

---

## Reproducibility & Verification

All public analysis scripts use **project-relative paths** (`Path(__file__).resolve()`) and run directly from the repository root with zero local path modifications:

```bash
# 1. Install exact tested dependencies (Python 3.12+)
pip install -r requirements.txt

# 2. Run Pellet-Grouped Double-Nested CV, Fair Baselines, Ablations, Bootstrap CIs & Figures
python THz_TCM_Research/04_Python数据处理/run_unified_double_nested_all.py

# 3. Run Unified Single-Spectrum QC + Differential Probe + 30-Permutation Pellet Y-Scrambling Audit
python THz_TCM_Research/04_Python数据处理/run_strict_leakage_audit.py

# 4. Regenerate Scheme 1 flowchart
python draw_pipeline.py

# 5. Rebuild submission Word documents (pure EN manuscript, Supplementary Material, Bilingual reference)
python THz_TCM_Research/04_Python数据处理/build_submission_docx.py
```

---

## Data Availability & Citation

The cached dual-channel THz-TDS spectra (`.npz`), pellet-grouped scripts, and audit logs are publicly provided in this repository. Raw instrument `.xlsx` files were acquired by previous students in Yin Shen's research group and provided by Yin Shen (Chongqing Medical University) as part of a shared research resource. For inquiries regarding raw time-domain exports or collaboration, please contact the corresponding author: **Yin Shen** (`shenyin285819016@126.com`).
