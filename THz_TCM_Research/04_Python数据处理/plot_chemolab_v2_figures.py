import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif"]
plt.rcParams["axes.unicode_minus"] = False

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
V2_RES_DIR = PROJECT_DIR / "05_实验结果" / "CHEMOLAB_V2"
V1_FIG_DIR = PROJECT_DIR / "06_论文写作" / "Submission_Figures"
V2_FIG_DIR = PROJECT_DIR / "06_论文写作" / "CHEMOLAB_V2_Figures"
V2_FIG_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY = json.loads((V2_RES_DIR / "CHEMOLAB_V2_Master_Summary.json").read_text(encoding="utf-8"))
PLOT_NPZ = np.load(V2_RES_DIR / "CHEMOLAB_V2_Plot_Data.npz", allow_pickle=True)


# ==============================================================================
# Scheme 1: Clean End-to-End TIRG-THz Framework Schematic (300 DPI)
# ==============================================================================
def draw_scheme_1():
    fig, ax = plt.subplots(figsize=(14.5, 6.4), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 48)
    ax.axis("off")

    def box(x, y, w, h, title, body, fc, ec, title_c="white", text_c="#1B2631", fs_t=9.5, fs_b=8.0):
        # Header band + light body card
        card = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.35,rounding_size=1.0",
                              fc=fc, ec=ec, lw=1.5, zorder=2)
        ax.add_patch(card)
        hdr_h = min(4.2, h * 0.34)
        hdr = FancyBboxPatch((x, y + h - hdr_h), w, hdr_h,
                             boxstyle="round,pad=0.35,rounding_size=0.8",
                             fc=ec, ec=ec, lw=0.8, zorder=3)
        ax.add_patch(hdr)
        ax.text(x + w / 2, y + h - hdr_h / 2, title, ha="center", va="center",
                fontsize=fs_t, fontweight="bold", color=title_c, zorder=4)
        ax.text(x + w / 2, y + (h - hdr_h) / 2, body, ha="center", va="center",
                fontsize=fs_b, color=text_c, linespacing=1.32, zorder=4)

    def arrow(x1, y1, x2, y2, lbl="", c="#2C3E50", rad=0.0):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>,head_width=0.45,head_length=0.6",
                                    color=c, lw=1.6, connectionstyle=f"arc3,rad={rad}"),
                    zorder=5)
        if lbl:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my + 0.9, lbl, ha="center", va="bottom", fontsize=7.6,
                    fontweight="bold", color=c,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85), zorder=6)

    ax.text(50, 46.2,
            "TIRG-THz: Thickness-Resilient, Repeatability-Guided Terahertz Chemometrics & Reliability Pipeline",
            ha="center", va="center", fontsize=12.0, fontweight="bold", color="#1B2631")

    # Stage 1: Acquisition & Pre-QC Grouping
    box(1.5, 25.5, 19.5, 16.5, "1. Raw THz-TDS & Pre-QC Lock",
        "Pure-powder pellets (1,308 scans)\nTERA K15, N2 purge (<4% RH)\nDual channel: α(ω), n(ω) [358 pts]\n"
        "-------------------------\nAssign pellet_id BEFORE QC\nUnified QC: 1.2<=n<=2.6, α<=55\nKept: 1,300 scans / 262 pellets",
        "#EBF5FB", "#1B4F72", fs_b=7.7)

    # Stage 2: Thickness-Resilient Views (Intra-Sample)
    box(25.0, 25.5, 22.0, 16.5, "2. Thickness-Resilient Views",
        "Zero cross-sample access\nView 1 (1,790d): Sample-wise SNV\n  SG(d0, d1, d2) -> shape invariance\n"
        "View 2 (1,074d): Ratio Attenuation\n  ρ_TF(ω) = α(ω) / max(n(ω)−1, 0.05)\n"
        "  1st-order d->s·d cancellation\nCombined X_TF: 2,864 dims",
        "#E8F8F5", "#117A65", fs_b=7.7)

    # Stage 3: Nest-Isolated Training Fold Engine
    box(51.5, 25.5, 23.0, 16.5, "3. Label-Free R_j & Subspace",
        "Strictly inside StratifiedGroupKFold\nUnsupervised Repeatability Prior:\n"
        "  R_j = clip(1 − σ²_within / σ²_total)\n"
        "  Tracks DR(ω) (ρ=0.85–0.90) | 88× faster\nTop 35% weighted -> Shrinkage-LDA\n  + Anisotropic RBF-SVM classifier",
        "#FEF9E7", "#B7950B", fs_b=7.6)

    # Stage 4: Dual Deployment Reliability
    box(78.5, 25.5, 20.0, 16.5, "4. Deployment Reliability",
        "Dual-Mechanism OOD Gate:\n  T² (Subspace) -> 0.96–1.00 defects\n  Q-Res + U_prob -> 0.76–0.95 OOD\n"
        "Non-Empty Split-Conformal:\n  >=95% pellet cov | 100% singleton\n  Honest abstention on OOD/hard sets",
        "#FDEDEC", "#B03A2E", fs_b=7.7)

    # Bottom row: Audits & External Validation
    box(1.5, 3.0, 29.0, 16.0, "Zero-Leakage & Permutation Audits",
        "• Differential Perturbation Probe: 0.00e+00 (0 flips)\n"
        "• 500-Perm Pellet Y-Scrambling: 0/500 >= obs (p=0.0020)\n"
        "• Replicate-Scan Optimism Quantified: +7.30% on Root\n"
        "• Paired Pellet-Cluster Bootstrap (2,000 resamples)",
        "#F4F6F7", "#566573", fs_b=7.8)

    box(35.0, 3.0, 30.0, 16.0, "Non-Circular Optical & Cross-Benchmarks",
        "• F1 Exact Fresnel (±10%): Amp-Ret −7.8% vs TIRG −0.02%\n"
        "• F2 Full FP + −68 dB DR (±10%): Amp-Ret −10.3% vs TIRG −1.17%\n"
        "• 3-Seed Track A & Track B + 4 DL Baselines (CNN/ResNet/TF/MLP)\n"
        "• 3-Matrix Avg: 94.44% (Sup) / 94.32% (Unsup R_j)",
        "#F4F6F7", "#2874A6", fs_b=7.6)

    box(69.5, 3.0, 29.0, 16.0, "External Cross-Lab Stress Test",
        "• NTHU Mendeley Ginseng (10.17632/hvbp5mdtxx.2)\n"
        "• 42 tablets in 6 groups (0.20–1.60 THz, 65 pts)\n"
        "• Strict 6-fold LOGO Acc: 50.0% (low Fisher 0.15–0.33)\n"
        "• Split-Conformal abstains (avg size 1.79, 92.86% cov)",
        "#F5EEF8", "#7D3C98", fs_b=7.8)

    # Connecting arrows top row
    arrow(21.4, 33.8, 24.6, 33.8)
    arrow(47.4, 33.8, 51.1, 33.8)
    arrow(74.9, 33.8, 78.1, 33.8)

    # Vertical/diagonal validation arrows
    arrow(63.0, 25.1, 16.0, 19.4, c="#566573", rad=0.08)
    arrow(36.0, 25.1, 50.0, 19.4, c="#2874A6", rad=-0.05)
    arrow(88.5, 25.1, 84.0, 19.4, c="#7D3C98")

    plt.tight_layout()
    plt.savefig(V2_FIG_DIR / "Scheme_1_TIRG_Pipeline.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# Figure 1: Thickness-Invariant Optical Ratio Physics (2x2 Panel, 300 DPI)
# ==============================================================================
def draw_figure_1():
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 8.6), dpi=300)
    ds_cfg = [
        ("Astragali_Radix", "Astragali Radix (Root)", "#1B4F72"),
        ("Ziziphi_Spinosae_Semen", "Ziziphi Spinosae Semen (Seed)", "#1E8449"),
        ("Gastrodia_elata", "Gastrodia elata (Tuber)", "#B03A2E"),
    ]
    freq = PLOT_NPZ["Astragali_Radix__freq"]

    ax1, ax2, ax3, ax4 = axes.ravel()
    for key, lbl, col in ds_cfg:
        ra = PLOT_NPZ[f"{key}__ra_q"]
        rr = PLOT_NPZ[f"{key}__rr_q"]
        rho = ra / np.maximum(rr - 1.0, 0.05)

        ma, sa = ra.mean(axis=0), ra.std(axis=0)
        mr, sr = rho.mean(axis=0), rho.std(axis=0)
        ax1.plot(freq, ma, color=col, lw=1.8, label=f"{lbl} (n={len(ra)})")
        ax1.fill_between(freq, ma - sa, ma + sa, color=col, alpha=0.14)
        ax2.plot(freq, mr, color=col, lw=1.8, label=f"{lbl}")
        ax2.fill_between(freq, mr - sr, mr + sr, color=col, alpha=0.14)

    ax1.set_title("(a) Raw Absorption Coefficient α(ω) Across Three Matrices", fontsize=10.8, fontweight="bold")
    ax1.set_ylabel("Absorption Coefficient α (cm⁻¹)", fontsize=10.0)
    ax1.set_xlim(0.22, 1.04)
    ax1.legend(loc="upper left", fontsize=8.4, frameon=True)
    ax1.grid(True, ls="--", alpha=0.35)

    ax2.set_title("(b) Algebraic Thickness-Free Optical Ratio ρ_TF(ω) = α / (n − 1)", fontsize=10.8, fontweight="bold")
    ax2.set_ylabel("Ratio ρ_TF(ω) (cm⁻¹)", fontsize=10.0)
    ax2.set_xlim(0.22, 1.04)
    ax2.legend(loc="upper left", fontsize=8.4, frameon=True)
    ax2.grid(True, ls="--", alpha=0.35)

    # Panel (c) & (d): Non-circular F2 (Full Fabry-Perot + -68 dB DR) & F1 (Exact Fresnel) on Astragali scan
    ra0 = PLOT_NPZ["Astragali_Radix__ra_q"][0]
    rr0 = PLOT_NPZ["Astragali_Radix__rr_q"][0]
    rho0 = ra0 / np.maximum(rr0 - 1.0, 0.05)

    ax3.plot(freq, PLOT_NPZ["hq0_f2_a_090"], ls="--", lw=1.7, color="#D35400", label="F2: s = 0.90 (−10% true d, FP+DR)")
    ax3.plot(freq, ra0, ls="-", lw=2.1, color="#1B4F72", label="Nominal Thickness (s = 1.00)")
    ax3.plot(freq, PLOT_NPZ["hq0_f2_a_110"], ls=":", lw=1.9, color="#2E86C1", label="F2: s = 1.10 (+10% true d, FP+DR)")

    ax4.plot(freq, rho0, ls="-", lw=3.2, color="#1B4F72", alpha=0.42, label="Nominal ρ_TF (s = 1.00)")
    ax4.plot(freq, PLOT_NPZ["hq0_f1_rho_090"], ls="-.", lw=1.4, color="#8E44AD", label="F1 Fresnel: s = 0.90 (small residual)")
    ax4.plot(freq, PLOT_NPZ["hq0_f2_rho_090"], ls="--", lw=1.6, color="#D35400", label="F2 Full FP+DR: s = 0.90")
    ax4.plot(freq, PLOT_NPZ["hq0_f2_rho_110"], ls=":", lw=1.7, color="#1E8449", label="F2 Full FP+DR: s = 1.10")

    ax3.set_title("(c) Apparent α(ω) Drift Under Physical FP+DR Thickness Error", fontsize=10.5, fontweight="bold")
    ax3.set_xlabel("Frequency (THz)", fontsize=10.0)
    ax3.set_ylabel("Apparent α(ω) (cm⁻¹)", fontsize=10.0)
    ax3.set_xlim(0.22, 1.04)
    ax3.legend(loc="upper left", fontsize=8.0, frameon=True)
    ax3.grid(True, ls="--", alpha=0.35)

    cs_hq = SUMMARY["physics_stress_v21"]["curve_rel_shifts"]["Astragali_Radix"]
    ax4.set_title("(d) Strong Collapse of ρ_TF(ω) Under Non-Circular Fresnel & FP+DR", fontsize=10.5, fontweight="bold")
    ax4.set_xlabel("Frequency (THz)", fontsize=10.0)
    ax4.set_ylabel("Ratio ρ_TF(ω) (cm⁻¹)", fontsize=10.0)
    ax4.set_xlim(0.22, 1.04)
    ax4.legend(loc="upper left", fontsize=7.9, frameon=True)
    ax4.grid(True, ls="--", alpha=0.35)
    ax4.text(0.55, 0.14,
             f"Non-Circular +10% Mean Shift (Root):\n"
             f"Raw α(ω): {cs_hq['raw_alpha_plus10_mean_rel_pct']:.2f}%\n"
             f"ρ_TF F1 (Exact Fresnel): {cs_hq['rho_f1_fresnel_plus10_mean_rel_pct']:.2f}% residual\n"
             f"ρ_TF F2 (Full FP + DR): {cs_hq['rho_f2_fp_dr_plus10_mean_rel_pct']:.2f}% residual",
             transform=ax4.transAxes, fontsize=8.0, fontweight="bold", color="#1B2631",
             bbox=dict(boxstyle="round,pad=0.32", fc="#E8F8F5", ec="#117A65"))

    plt.tight_layout()
    plt.savefig(V2_FIG_DIR / "Figure_1_Thickness_Invariant_Physics.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# Figure 2: Non-Circular Optical Thickness-Drift Stress Test Across 3 Matrices (300 DPI)
# ==============================================================================
def draw_figure_2():
    st_data = SUMMARY["physics_stress_v21"]["per_matrix"]
    matrices = [
        ("Astragali_Radix", "(a) Astragali Radix (Root)"),
        ("Ziziphi_Spinosae_Semen", "(b) Ziziphi Spinosae Semen (Seed)"),
        ("Gastrodia_elata", "(c) Gastrodia elata (Tuber)"),
    ]
    models = [
        ("AmpRet_DualView_MCUVE", "Amp-Retaining\nDual-View"),
        ("SNV_Only_MCUVE", "SNV-Only\n(Ablation)"),
        ("TIRG_StrictTF_Sup_MCUVE", "TIRG-THz\n(Sup MC-UVE)"),
        ("TIRG_StrictTF_Unsup_R", "TIRG-THz\n(Unsup R_j)"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(14.8, 5.1), dpi=300, sharey=True)

    for ax, (ds_key, title) in zip(axes, matrices):
        x = np.arange(len(models))
        w = 0.26
        c_clean = [st_data[ds_key][m]["clean_acc"] for m, _ in models]
        c_f1 = [st_data[ds_key][m]["F1_fresnel_10pct_mean"] for m, _ in models]
        c_f2 = [st_data[ds_key][m]["F2_fp_dr_10pct_mean"] for m, _ in models]
        d_f2 = [st_data[ds_key][m]["F2_drop"] for m, _ in models]

        ax.bar(x - w, c_clean, width=w, label="Clean Baseline (seed = 42)", color="#1B4F72", ec="#1B2631", lw=0.7)
        ax.bar(x, c_f1, width=w, label="F1: Exact Fresnel (±10% Test)", color="#2E86C1", ec="#1B2631", lw=0.7)
        ax.bar(x + w, c_f2, width=w, label="F2: Full FP + −68 dB DR (±10% Test)", color="#D35400", ec="#1B2631", lw=0.7)

        for xi, v1, v2, v3, dv in zip(x, c_clean, c_f1, c_f2, d_f2):
            lbl = f"{dv:+.1f}%"
            col_t = "#C0392B" if dv < -5.0 else ("#B9770E" if dv < -2.0 else "#117A65")
            top_y = max(v1, v2, v3)
            ax.text(xi, top_y + 0.8, f"F2: {v3:.1f}%\n({lbl})", ha="center", va="bottom",
                    fontsize=7.2, fontweight="bold", color=col_t)

        ax.set_title(title, fontsize=10.5, fontweight="bold", pad=8)
        ax.set_xticks(x)
        ax.set_xticklabels([lbl for _, lbl in models], fontsize=8.2)
        ax.set_ylim(68, 108.5)
        ax.grid(axis="y", ls="--", alpha=0.4)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Pellet-Grouped 5-Fold Scan Accuracy (%, seed = 42)", fontsize=9.8, fontweight="bold")
    axes[1].legend(loc="lower center", bbox_to_anchor=(0.5, 1.07), ncol=3, fontsize=8.6, frameon=True)
    plt.tight_layout()
    plt.savefig(V2_FIG_DIR / "Figure_2_Thickness_Stress_Test.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# Figure 3: Unsupervised Repeatability R_j(w) Tracks Measured TERA K15 DR(w) + Speedup (2x2, 300 DPI)
# ==============================================================================
def draw_figure_3():
    fig, axes = plt.subplots(2, 2, figsize=(13.8, 8.2), dpi=300)
    axes_flat = axes.ravel()
    freq = PLOT_NPZ["Astragali_Radix__freq"]
    n_f = len(freq)
    dr_meta = SUMMARY["repeatability_dr_correlation"]

    def abs_ratio_profile(vec_2864):
        blocks = [vec_2864[b * n_f:(b + 1) * n_f] for b in [0, 1, 2, 5, 6, 7]]
        m = np.mean(blocks, axis=0)
        return m / (np.max(m) + 1e-8)

    panels = [
        (axes_flat[0], "Astragali_Radix", "(a) Astragali Radix (Root): R_j(ω) vs. Sample DR(ω)", "#1B4F72", "#2874A6"),
        (axes_flat[1], "Ziziphi_Spinosae_Semen", "(b) Ziziphi Spinosae Semen (Seed): R_j(ω) vs. Sample DR(ω)", "#1E8449", "#2E86C1"),
        (axes_flat[2], "Gastrodia_elata", "(c) Gastrodia elata (Tuber): R_j(ω) vs. Sample DR(ω)", "#B03A2E", "#566573"),
    ]
    for ax, ds_k, ttl, c_r, c_mc in panels:
        r_p = abs_ratio_profile(PLOT_NPZ[f"{ds_k}__TIRG_StrictTF_Unsup_R__stab"])
        m_p = abs_ratio_profile(PLOT_NPZ[f"{ds_k}__TIRG_StrictTF_Sup_MCUVE__stab"])
        dr_db = PLOT_NPZ[f"{ds_k}__dr_interp"]
        meta = dr_meta[ds_k]

        l1, = ax.plot(freq, r_p, color=c_r, lw=1.9, label="Unsup. Repeatability R_j(ω)")
        l2, = ax.plot(freq, m_p, color=c_mc, lw=1.4, ls="--", alpha=0.85, label="Supervised MC-UVE(ω)")
        ax.set_xlim(0.22, 1.04)
        ax.set_ylim(0.0, 1.15)
        ax.set_xlabel("Frequency (THz)", fontsize=9.8)
        ax.set_ylabel("Normalized Weight", fontsize=9.8, fontweight="bold", color=c_r)
        ax.set_title(ttl, fontsize=10.2, fontweight="bold")
        ax.grid(True, ls="--", alpha=0.35)
        ax.spines["top"].set_visible(False)

        ax_r = ax.twinx()
        l3, = ax_r.plot(freq, dr_db, color="#2C3E50", lw=1.7, ls="-.", alpha=0.82, label="Measured TERA K15 DR (dB)")
        ax_r.set_ylim(18, 82)
        ax_r.set_ylabel("Measured Sample DR (dB)", fontsize=9.4, fontweight="bold", color="#2C3E50")
        ax_r.spines["top"].set_visible(False)

        lines = [l1, l2, l3]
        ax.legend(lines, [ln.get_label() for ln in lines], loc="upper right", fontsize=7.6, frameon=True)
        ax.text(
            0.03, 0.06,
            f"Spearman ρ(R_j, DR) = {meta['spearman_r_all']:.4f} (p = {meta['p_all']:.1e})\n"
            f"DR roll-off: {meta['dr_022_db']:.1f} → {meta['dr_104_db']:.1f} dB",
            transform=ax.transAxes, fontsize=8.0, fontweight="bold", color="#1B2631",
            bbox=dict(boxstyle="round,pad=0.25", fc="#F8F9F9", ec=c_r, alpha=0.93), zorder=6
        )

    # Panel (d) Pareto Trade-off: 3-Seed Accuracy vs Selection Runtime
    ax_p = axes_flat[3]
    ca = SUMMARY["benchmarks"]["cross_matrix_avg"]
    pts = [
        ("Amp-Retaining Dual-View\n(MC-UVE)", ca["Original_DualView_MCUVE"]["avg_sel_sec_per_fold"],
         ca["Original_DualView_MCUVE"]["three_seed_scan_mean"], "#566573", "s", (-132, -26)),
        ("TIRG-THz\n(Sup MC-UVE)", ca["TIRG_StrictTF_Sup_MCUVE"]["avg_sel_sec_per_fold"],
         ca["TIRG_StrictTF_Sup_MCUVE"]["three_seed_scan_mean"], "#2E86C1", "o", (-112, 10)),
        ("TIRG-THz\n(Unsup R_j)", ca["TIRG_StrictTF_Unsup_R"]["avg_sel_sec_per_fold"],
         ca["TIRG_StrictTF_Unsup_R"]["three_seed_scan_mean"], "#1E8449", "*", (12, 10)),
    ]
    for lbl, t_s, acc, col, mk, ofs in pts:
        ax_p.scatter(t_s, acc, s=260 if mk == "*" else 115, color=col, marker=mk, edgecolor="#1B2631", zorder=4)
        ax_p.annotate(f"{lbl}\n({acc:.2f}%, {t_s:.3f}s)", xy=(t_s, acc), xytext=ofs,
                      textcoords="offset points", fontsize=8.1, fontweight="bold", color=col,
                      bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))

    spd = ca["unsup_r_speedup_vs_mcuve_on_strict_tf"]
    ax_p.annotate(f"{spd}× faster\n(zero label use!)",
                  xy=(ca["TIRG_StrictTF_Unsup_R"]["avg_sel_sec_per_fold"], 94.28),
                  xytext=(0.048, 93.80), fontsize=8.5, fontweight="bold", color="#117A65",
                  arrowprops=dict(arrowstyle="->", color="#117A65", lw=1.4),
                  bbox=dict(boxstyle="round,pad=0.25", fc="#E8F8F5", ec="#117A65"))
    ax_p.set_xscale("log")
    ax_p.set_xlim(0.008, 4.0)
    ax_p.set_ylim(93.2, 95.0)
    ax_p.set_title("(d) 3-Seed Accuracy vs. Feature Selection Time", fontsize=10.2, fontweight="bold")
    ax_p.set_xlabel("Mean Feature Selection Time / Fold (s, log scale)", fontsize=9.8)
    ax_p.set_ylabel("3-Seed Cross-Matrix Scan Acc. (%)", fontsize=9.8, fontweight="bold")
    ax_p.grid(True, which="both", ls="--", alpha=0.35)
    ax_p.spines["top"].set_visible(False)
    ax_p.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(V2_FIG_DIR / "Figure_3_Repeatability_Prior_and_Speedup.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# Figure 4: Unified 3-Matrix Benchmarks Including 4 DL Baselines (300 DPI)
# ==============================================================================
def draw_figure_4():
    pm = SUMMARY["benchmarks"]["per_matrix"]
    dl = SUMMARY["archived_dl_baselines"]
    ca = SUMMARY["benchmarks"]["cross_matrix_avg"]

    # Build unified sorted cross-matrix comparison
    entries = [
        ("1D-CNN (Track A)", dl["1D-CNN"]["cross_matrix_mean"]["scan_acc_mean"],
         dl["1D-CNN"]["cross_matrix_mean"]["pellet_acc_mean"], "#BDC3C7"),
        ("Track A Raw RF", ca["TrackA_Raw_RF"]["three_seed_scan_mean"],
         ca["TrackA_Raw_RF"]["three_seed_pellet_mean"], "#BDC3C7"),
        ("1D-ResNet (Track A)", dl["1D-ResNet"]["cross_matrix_mean"]["scan_acc_mean"],
         dl["1D-ResNet"]["cross_matrix_mean"]["pellet_acc_mean"], "#BDC3C7"),
        ("1D-Transformer (Track A)", dl["1D-Transformer"]["cross_matrix_mean"]["scan_acc_mean"],
         dl["1D-Transformer"]["cross_matrix_mean"]["pellet_acc_mean"], "#BDC3C7"),
        ("Track A Raw RBF-SVM", ca["TrackA_Raw_SVM"]["three_seed_scan_mean"],
         ca["TrackA_Raw_SVM"]["three_seed_pellet_mean"], "#A6ACAF"),
        ("Track A Raw PLS-DA", ca["TrackA_Raw_PLSDA"]["three_seed_scan_mean"],
         ca["TrackA_Raw_PLSDA"]["three_seed_pellet_mean"], "#A6ACAF"),
        ("Track B StrictTF RF", ca["TrackB_StrictTF_RF"]["three_seed_scan_mean"],
         ca["TrackB_StrictTF_RF"]["three_seed_pellet_mean"], "#85C1E9"),
        ("Track B StrictTF PLS-DA", ca["TrackB_StrictTF_PLSDA"]["three_seed_scan_mean"],
         ca["TrackB_StrictTF_PLSDA"]["three_seed_pellet_mean"], "#85C1E9"),
        ("Track B Dual-View MLP", dl["Dual-View MLP"]["cross_matrix_mean"]["scan_acc_mean"],
         dl["Dual-View MLP"]["cross_matrix_mean"]["pellet_acc_mean"], "#5DADE2"),
        ("Amp-Retaining Dual-View (MC-UVE)", ca["Original_DualView_MCUVE"]["three_seed_scan_mean"],
         ca["Original_DualView_MCUVE"]["three_seed_pellet_mean"], "#2E86C1"),
        ("TIRG-THz (Unsup R_j)", ca["TIRG_StrictTF_Unsup_R"]["three_seed_scan_mean"],
         ca["TIRG_StrictTF_Unsup_R"]["three_seed_pellet_mean"], "#1E8449"),
        ("TIRG-THz (Sup MC-UVE)", ca["TIRG_StrictTF_Sup_MCUVE"]["three_seed_scan_mean"],
         ca["TIRG_StrictTF_Sup_MCUVE"]["three_seed_pellet_mean"], "#1B4F72"),
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.2, 6.2), dpi=300, gridspec_kw={"width_ratios": [1.35, 1.0]})

    # Left: Cross-Matrix 3-Seed Scan & Pellet horizontal bars
    y_pos = np.arange(len(entries))
    names = [e[0] for e in entries]
    scans = [e[1] for e in entries]
    pels = [e[2] for e in entries]
    cols = [e[3] for e in entries]

    h = 0.38
    ax1.barh(y_pos - h / 2, scans, height=h, color=cols, ec="#1B2631", lw=0.6, label="3-Seed Scan Mean (%)")
    ax1.barh(y_pos + h / 2, pels, height=h, color=cols, ec="#1B2631", lw=0.6, alpha=0.55, hatch="///", label="3-Seed Pellet Vote Mean (%)")

    for yp, sv, pv in zip(y_pos, scans, pels):
        ax1.text(max(sv, pv) + 0.6, yp, f"{sv:.2f}% / {pv:.2f}%", va="center", fontsize=7.6, fontweight="bold", color="#1B2631")

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(names, fontsize=8.5, fontweight="bold")
    ax1.set_xlim(62, 108.5)
    ax1.set_xlabel("3-Seed Cross-Matrix Average Accuracy (%)", fontsize=10.0, fontweight="bold")
    ax1.set_title("(a) 3-Seed Cross-Matrix Benchmarks (Track A/B Classical + 4 DL + TIRG)", fontsize=10.4, fontweight="bold")
    ax1.legend(loc="lower right", fontsize=8.3, frameon=True)
    ax1.grid(axis="x", ls="--", alpha=0.35)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # Right: Per-matrix breakdown for hardest matrix (Astragali Radix) & Ziziphi & Gastrodia
    key_models = [
        ("1D-CNN", "#BDC3C7", lambda k: dl["1D-CNN"]["datasets"][k]["scan_acc_mean"]),
        ("1D-Transformer", "#95A5A6", lambda k: dl["1D-Transformer"]["datasets"][k]["scan_acc_mean"]),
        ("TrackB StrictTF PLS-DA", "#5DADE2", lambda k: pm[k]["TrackB_StrictTF_PLSDA"]["three_seed_scan_mean"]),
        ("Dual-View MLP", "#3498DB", lambda k: dl["Dual-View MLP"]["datasets"][k]["scan_acc_mean"]),
        ("TIRG (Unsup R_j)", "#1E8449", lambda k: pm[k]["TIRG_StrictTF_Unsup_R"]["three_seed_scan_mean"]),
        ("TIRG (Sup MC-UVE)", "#1B4F72", lambda k: pm[k]["TIRG_StrictTF_Sup_MCUVE"]["three_seed_scan_mean"]),
    ]
    ds_keys = ["Astragali_Radix", "Ziziphi_Spinosae_Semen", "Gastrodia_elata"]
    ds_short = ["Astragali Radix\n(Root)", "Ziziphi Semen\n(Seed)", "Gastrodia elata\n(Tuber)"]
    x = np.arange(len(ds_keys))
    bw = 0.13
    for mi, (mlbl, mcol, fn) in enumerate(key_models):
        vals = [fn(dk) for dk in ds_keys]
        ofs = (mi - (len(key_models) - 1) / 2.0) * bw
        bars = ax2.bar(x + ofs, vals, width=bw, color=mcol, ec="#1B2631", lw=0.5, label=mlbl)
        if mi >= 4:
            for b, v in zip(bars, vals):
                ax2.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.1f}", ha="center", va="bottom",
                         fontsize=6.9, fontweight="bold", rotation=90, color=mcol)

    ax2.set_xticks(x)
    ax2.set_xticklabels(ds_short, fontsize=9.0, fontweight="bold")
    ax2.set_ylim(55, 113)
    ax2.set_ylabel("3-Seed Pellet-Grouped Scan Accuracy (%)", fontsize=10.0, fontweight="bold")
    ax2.set_title("(b) Per-Matrix 3-Seed Scan Accuracy Breakdown", fontsize=10.4, fontweight="bold")
    ax2.legend(loc="upper left", fontsize=7.6, frameon=True, ncol=2)
    ax2.grid(axis="y", ls="--", alpha=0.35)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(V2_FIG_DIR / "Figure_4_Cross_Matrix_Benchmarks_and_DL.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# Figure 5: Leakage Audit & 500-Permutation Y-Scrambling (4-Panel, 300 DPI)
# ==============================================================================
def draw_figure_5():
    la = SUMMARY["leakage_audit"]
    gr = la["audit3_grouped_vs_random"]
    p500 = la["audit4_y_scrambling_500"]

    fig, axes = plt.subplots(1, 4, figsize=(16.0, 4.3), dpi=300)

    # Panel (a): Grouped vs Ungrouped Optimism
    ds_keys = ["Astragali_Radix", "Ziziphi_Spinosae_Semen", "Gastrodia_elata"]
    ds_lbls = ["Root", "Seed", "Tuber"]
    x = np.arange(3)
    w = 0.34
    g_vals = [gr[k]["pellet_grouped_scan_acc"] for k in ds_keys]
    r_vals = [gr[k]["ungrouped_random_scan_acc"] for k in ds_keys]
    axes[0].bar(x - w / 2, g_vals, width=w, color="#1B4F72", ec="#1B2631", label="Pellet-Grouped CV")
    axes[0].bar(x + w / 2, r_vals, width=w, color="#C0392B", ec="#1B2631", alpha=0.82, label="Ungrouped Random CV")
    for xi, gv, rv in zip(x, g_vals, r_vals):
        gap = rv - gv
        axes[0].text(xi + w / 2, rv + 0.6, f"{gap:+.2f}%", ha="center", va="bottom",
                     fontsize=7.8, fontweight="bold", color="#C0392B" if gap > 0 else "#117A65")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(ds_lbls, fontsize=9.2, fontweight="bold")
    axes[0].set_ylim(75, 106)
    axes[0].set_ylabel("Scan Accuracy (%)", fontsize=9.8, fontweight="bold")
    axes[0].set_title("(a) Replicate-Scan Leakage Gap", fontsize=10.2, fontweight="bold")
    axes[0].legend(loc="lower right", fontsize=7.6, frameon=True)
    axes[0].grid(axis="y", ls="--", alpha=0.35)

    # Panels (b)-(d): 500-Permutation Y-Scrambling Histograms
    cols = ["#1B4F72", "#1E8449", "#B03A2E"]
    titles = ["(b) Root: 500-Perm Null", "(c) Seed: 500-Perm Null", "(d) Tuber: 500-Perm Null"]
    for ax, dk, col, ttl in zip(axes[1:], ds_keys, cols, titles):
        arr = PLOT_NPZ[f"{dk}__perm500"]
        info = p500[dk]
        ax.hist(arr, bins=20, color=col, alpha=0.65, edgecolor="#1B2631", lw=0.6, label="Null Dist. (n=500)")
        ax.axvline(info["chance_pct"], color="#7F8C8D", ls=":", lw=1.4, label=f"Chance ({info['chance_pct']:.0f}%)")
        ax.axvline(info["obs_acc"], color="#C0392B", ls="-", lw=2.2, label=f"Observed ({info['obs_acc']:.2f}%)")
        ax.text(0.60, 0.44, f"Null: {info['null_mean']:.1f}±{info['null_sd']:.1f}%\nMax: {info['null_max']:.1f}%\n0/500 >= Obs\np = {info['empirical_p']:.4f}",
                transform=ax.transAxes, ha="center", fontsize=7.6, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=col, alpha=0.92))
        ax.set_title(ttl, fontsize=10.2, fontweight="bold")
        ax.set_xlabel("Accuracy (%)", fontsize=9.5)
        ax.set_xlim(5, 105)
        ax.legend(loc="upper center", bbox_to_anchor=(0.60, 0.98), fontsize=7.1, frameon=True)
        ax.grid(axis="y", ls="--", alpha=0.3)

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(V2_FIG_DIR / "Figure_5_Leakage_and_500Perm_Audit.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# Figure 6: OOD Subspace Collapse vs Rescue + Conformal Across 4 Datasets (300 DPI)
# ==============================================================================
def draw_figure_6():
    rel = SUMMARY["deployment_reliability"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.4, 5.2), dpi=300)

    # Panel (a): OOD AUROC Discovery (Real Defects vs Unseen Origins)
    cats = [
        "Root\nBad Pellet", "Seed\nBad Pellet", "Tuber\nBad Pellet",
        "Root\nUnseen Origin", "Seed\nUnseen Origin", "Tuber\nUnseen Origin",
    ]
    t2_vals = [
        rel["Astragali_Radix"]["C1_real_corrupted_auroc"]["T2"],
        rel["Ziziphi_Spinosae_Semen"]["C1_real_corrupted_auroc"]["T2"],
        rel["Gastrodia_elata"]["C1_real_corrupted_auroc"]["T2"],
        rel["Astragali_Radix"]["C2_unseen_origin_pellet_auroc"]["T2"],
        rel["Ziziphi_Spinosae_Semen"]["C2_unseen_origin_pellet_auroc"]["T2"],
        rel["Gastrodia_elata"]["C2_unseen_origin_pellet_auroc"]["T2"],
    ]
    q_vals = [
        rel["Astragali_Radix"]["C1_real_corrupted_auroc"]["Q_res"],
        rel["Ziziphi_Spinosae_Semen"]["C1_real_corrupted_auroc"]["Q_res"],
        rel["Gastrodia_elata"]["C1_real_corrupted_auroc"]["Q_res"],
        rel["Astragali_Radix"]["C2_unseen_origin_pellet_auroc"]["Q_res"],
        rel["Ziziphi_Spinosae_Semen"]["C2_unseen_origin_pellet_auroc"]["Q_res"],
        rel["Gastrodia_elata"]["C2_unseen_origin_pellet_auroc"]["Q_res"],
    ]
    qu_vals = [
        rel["Astragali_Radix"]["C1_real_corrupted_auroc"]["Q+U_prob"],
        rel["Ziziphi_Spinosae_Semen"]["C1_real_corrupted_auroc"]["Q+U_prob"],
        rel["Gastrodia_elata"]["C1_real_corrupted_auroc"]["Q+U_prob"],
        rel["Astragali_Radix"]["C2_unseen_origin_pellet_auroc"]["Q+U_prob"],
        rel["Ziziphi_Spinosae_Semen"]["C2_unseen_origin_pellet_auroc"]["Q+U_prob"],
        rel["Gastrodia_elata"]["C2_unseen_origin_pellet_auroc"]["Q+U_prob"],
    ]
    x = np.arange(len(cats))
    w = 0.26
    ax1.bar(x - w, t2_vals, width=w, color="#C0392B", ec="#1B2631", label="LDA Subspace T² (Collapses on Unseen!)")
    ax1.bar(x, q_vals, width=w, color="#2E86C1", ec="#1B2631", label="PCA Orthogonal Q-Residual")
    ax1.bar(x + w, qu_vals, width=w, color="#1E8449", ec="#1B2631", label="Combined Q-Res + Kernel Prob (U_prob)")
    ax1.axhline(0.5, color="#7F8C8D", ls="--", lw=1.2, label="Random Chance (0.50)")
    ax1.axvline(2.5, color="#2C3E50", ls=":", lw=1.3)

    for xi, t2v, quv in zip(x, t2_vals, qu_vals):
        if t2v < 0.52:
            ax1.text(xi - w, t2v - 0.06, f"{t2v:.2f}", ha="center", va="center", fontsize=7.4, fontweight="bold", color="white")
        ax1.text(xi + w, quv + 0.02, f"{quv:.2f}", ha="center", va="bottom", fontsize=7.4, fontweight="bold", color="#1E8449")

    ax1.set_xticks(x)
    ax1.set_xticklabels(cats, fontsize=8.3, fontweight="bold")
    ax1.set_ylim(0, 1.16)
    ax1.set_ylabel("OOD Detection AUROC", fontsize=10.0, fontweight="bold")
    ax1.set_title("(a) OOD Detection: Subspace T² Collapse vs. Orthogonal Q + Prob Rescue", fontsize=10.4, fontweight="bold")
    ax1.legend(loc="lower left", fontsize=7.8, frameon=True)
    ax1.grid(axis="y", ls="--", alpha=0.35)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # Panel (b): Non-Empty Split-Conformal Coverage & Singleton Rate Across All 4 Datasets
    ds4_lbls = [
        "Root\n(Pellet, 4-cls)", "Seed\n(Pellet, 5-cls)", "Tuber\n(Pellet, 4-cls)", "Ext. Ginseng\n(Cross-Lab, 2-cls)"
    ]
    covs = [
        rel["Astragali_Radix"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_coverage_pct"],
        rel["Ziziphi_Spinosae_Semen"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_coverage_pct"],
        rel["Gastrodia_elata"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_coverage_pct"],
        rel["External_Ginseng_Mendeley"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["sample_coverage_pct"],
    ]
    sing_rates = [
        rel["Astragali_Radix"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_singleton_rate_pct"],
        rel["Ziziphi_Spinosae_Semen"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_singleton_rate_pct"],
        rel["Gastrodia_elata"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_singleton_rate_pct"],
        rel["External_Ginseng_Mendeley"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["sample_singleton_rate_pct"],
    ]
    sing_accs = [
        rel["Astragali_Radix"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_singleton_acc_pct"],
        rel["Ziziphi_Spinosae_Semen"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_singleton_acc_pct"],
        rel["Gastrodia_elata"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_singleton_acc_pct"],
        rel["External_Ginseng_Mendeley"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["sample_singleton_acc_pct"],
    ]
    avg_sizes = [
        rel["Astragali_Radix"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_avg_set_size"],
        rel["Ziziphi_Spinosae_Semen"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_avg_set_size"],
        rel["Gastrodia_elata"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["pellet_avg_set_size"],
        rel["External_Ginseng_Mendeley"]["NonEmpty_Split_Conformal"]["alpha=0.10"]["sample_avg_set_size"],
    ]

    x2 = np.arange(4)
    w2 = 0.26
    ax2.bar(x2 - w2, covs, width=w2, color="#1B4F72", ec="#1B2631", label="Empirical Coverage (%)")
    ax2.bar(x2, sing_rates, width=w2, color="#D35400", ec="#1B2631", label="Singleton Decision Rate (%)")
    ax2.bar(x2 + w2, sing_accs, width=w2, color="#1E8449", ec="#1B2631", label="Accuracy Among Singletons (%)")
    ax2.axhline(90.0, color="#7F8C8D", ls="--", lw=1.3, label="Target Coverage (1 − α = 90%)")

    for xi, cv, sr, sz in zip(x2, covs, sing_rates, avg_sizes):
        ax2.text(xi - w2, cv + 1.2, f"{cv:.1f}%", ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#1B4F72")
        ax2.text(xi, sr + 1.2, f"{sr:.1f}%\n(μ={sz:.2f})", ha="center", va="bottom", fontsize=7.2, fontweight="bold", color="#D35400")

    ax2.set_xticks(x2)
    ax2.set_xticklabels(ds4_lbls, fontsize=8.4, fontweight="bold")
    ax2.set_ylim(0, 118)
    ax2.set_ylabel("Percentage (%)", fontsize=10.0, fontweight="bold")
    ax2.set_title("(b) Non-Empty Split-Conformal Reliability (α = 0.10, All 4 Datasets)", fontsize=10.4, fontweight="bold")
    ax2.legend(loc="lower left", fontsize=7.8, frameon=True)
    ax2.grid(axis="y", ls="--", alpha=0.35)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(V2_FIG_DIR / "Figure_6_OOD_Collapse_and_Conformal.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# Figure S1: 1x3 Confusion Matrices of TIRG-THz (Unsup R_j, seed=42)
# ==============================================================================
def draw_figure_s1():
    cohorts = SUMMARY["cohorts"]
    bm = SUMMARY["benchmarks"]["per_matrix"]
    fig, axes = plt.subplots(1, 3, figsize=(15.2, 4.6), dpi=300)
    ds_keys = ["Astragali_Radix", "Ziziphi_Spinosae_Semen", "Gastrodia_elata"]
    titles = [
        f"(a) Astragali Radix\nScan {bm['Astragali_Radix']['TIRG_StrictTF_Unsup_R']['seed42']['scan_acc']}% | Pellet {bm['Astragali_Radix']['TIRG_StrictTF_Unsup_R']['seed42']['pellet_ratio']}",
        f"(b) Ziziphi Spinosae Semen\nScan {bm['Ziziphi_Spinosae_Semen']['TIRG_StrictTF_Unsup_R']['seed42']['scan_acc']}% | Pellet {bm['Ziziphi_Spinosae_Semen']['TIRG_StrictTF_Unsup_R']['seed42']['pellet_ratio']}",
        f"(c) Gastrodia elata\nScan {bm['Gastrodia_elata']['TIRG_StrictTF_Unsup_R']['seed42']['scan_acc']}% | Pellet {bm['Gastrodia_elata']['TIRG_StrictTF_Unsup_R']['seed42']['pellet_ratio']}",
    ]
    for ax, dk, ttl in zip(axes, ds_keys, titles):
        classes = cohorts[dk]["classes"]
        yt = PLOT_NPZ[f"{dk}__y_q"]
        yp = PLOT_NPZ[f"{dk}__tirg_unsup_oof42"]
        cm = confusion_matrix(yt, yp, labels=classes)
        ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=classes).plot(cmap=plt.cm.Blues, ax=ax, values_format="d", colorbar=False)
        ax.set_title(ttl, fontsize=9.8, fontweight="bold", pad=8)
        ax.set_xticklabels(classes, rotation=22, ha="right", fontsize=8.0)
        ax.set_yticklabels(classes, fontsize=8.0)

    plt.tight_layout()
    plt.savefig(V2_FIG_DIR / "Figure_S1_Confusion_Matrices_V2.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    draw_scheme_1()
    draw_figure_1()
    draw_figure_2()
    draw_figure_3()
    draw_figure_4()
    draw_figure_5()
    draw_figure_6()
    draw_figure_s1()
    shutil.copy2(V1_FIG_DIR / "Figure_S2_Dynamic_Range.png", V2_FIG_DIR / "Figure_S2_Dynamic_Range.png")
    print("Generated all 9 CHEMOLAB V2 figures in:", V2_FIG_DIR)
    for p in sorted(V2_FIG_DIR.glob("*.png")):
        print(f"  {p.name}: {p.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
