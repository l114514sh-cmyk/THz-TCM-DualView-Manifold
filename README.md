# Dual-View SW-MCUVE-Manifold THz-TDS Authentication for Traditional Chinese Medicines

**Authors:** Sihao Liu¹, Ziyuan Zhu¹, Yin Shen¹\*  
**Affiliation:** ¹Chongqing Medical University, Chongqing, China  
**Corresponding Author:** Yin Shen (`shenyin285819016@126.com`, ORCID: [0000-0002-3221-7875](https://orcid.org/0000-0002-3221-7875))  
**Co-authors:** Sihao Liu (`L114514SH@gmail.com`), Ziyuan Zhu (`zzy2630816871@gmail.com`, ORCID: [0009-0005-1153-4926](https://orcid.org/0009-0005-1153-4926))

---

## Overview

This repository accompanies the manuscript:

> *Cross-Matrix Authentication and Origin Traceability of Traditional Chinese Medicines via Dual-View Terahertz Spectroscopy, Stability-Weighted Manifold Learning, and Quantum Chemical Vibrational Benchmarks*

It contains the complete locked Python pipeline, full-precision cached dual-channel THz-TDS spectra (`0.22–1.04 THz`, 358 frequency points per channel, acquired on a Menlo Systems TERA K15 system), four-stage zero-leakage statistical audit suite, 300 DPI publication figures, and Word submission package.

## Key Results (Strict Double-Nested 5-Fold CV, Post-QC)

| Botanical Matrix | Task | Post-QC $n$ | Double-Nested Acc | 5-Fold Mean ± SD | Macro-F1 | 3-Seed Mean ± SD | Y-Scrambling Acc |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| ***Astragali Radix*** (Root) | 4 Geographical Origins | 397 | **93.20%** | 93.19% ± 2.73% | 0.9321 | 93.12% ± 0.93% | 21.41% (chance 25%) |
| ***Ziziphi Spinosae Semen*** (Seed) | 5 Commercial Formats | 500 | **97.40%** | 97.40% ± 1.62% | 0.9740 | 97.20% ± 0.28% | 18.80% (chance 20%) |
| ***Gastrodia elata*** (Tuber) | 4 Origins (Cross-Matrix) | 404 | **99.75%** | 99.75% ± 0.50% | 0.9975 | 99.67% ± 0.12% | 26.98% (chance 25%) |

## Repository Structure

- `THz_TCM_Research/04_Python数据处理/`
  - `run_unified_double_nested_all.py`: Master locked Dual-View SW-MCUVE-Manifold pipeline (all 3 matrices + knockout ablations + baseline benchmarks + 300 DPI plots).
  - `run_strict_leakage_audit.py`: Four-stage zero-leakage mathematical & statistical audit (differential blind-test perturbation probe, fold-internal QC check, 3-seed stability, Y-scrambling permutation test).
  - `build_submission_docx.py`: Generates bilingual `Manuscript_Final.docx` (with embedded 300 DPI figures), `Highlights.docx`, and `Cover_Letter.docx`.
- `THz_TCM_Research/01_原始实验数据/`
  - `黄芪/huangqi_fast_cache.npz`, `酸枣仁/suanzaoren_fast_cache.npz`, `天麻/tianma_fast_cache.npz`: Full-precision cached dual-channel THz-TDS spectra (`raw_a`, `raw_r`, `y`, `freq`) for rapid reproduction.
  - `3d分子/`: Initial 3D conformers (`.sdf`) for DFT-D3(BJ) calculations on calycosin and spinosin.
- `THz_TCM_Research/05_实验结果/模型结果/`
  - `Unified_Double_Nested_Summary.md` & `.json`: Exact quantitative metrics across all models, ablations, and baselines.
  - `Strict_Leakage_Audit_Report.json`: Machine-readable zero-leakage audit logs.
- `THz_TCM_Research/06_论文写作/`
  - `Manuscript_Final.docx`, `Cover_Letter.docx`, `Highlights.docx`
- Root figures: `Pipeline_Flowchart_Clean.png` (Scheme 1), `Figure 1.png` – `Figure 6.png`, `Figure S1.a.png`, `Figure S1.b.png`, `draw_pipeline.py`.

## Quick Reproduction

```bash
python THz_TCM_Research/04_Python数据处理/run_unified_double_nested_all.py
python THz_TCM_Research/04_Python数据处理/run_strict_leakage_audit.py
python THz_TCM_Research/04_Python数据处理/build_submission_docx.py
```

## Acknowledgements

Spectral data were acquired by Yiyi Yang at the Terahertz Spectroscopy Laboratory of Southwest University (Chongqing, China) and provided by Yin Shen as part of a shared research resource.
