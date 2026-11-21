from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']

ROOT_DIR = Path(__file__).resolve().parent
SUB_FIG_DIR = ROOT_DIR / "THz_TCM_Research" / "06_论文写作" / "Submission_Figures"
SUB_FIG_DIR.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(10.5, 14.5), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 29.0)
ax.axis('off')

# Main Title (Larger, cleaner, single-column readable)
ax.text(5.0, 28.3, "Dual-View SW-MCUVE-Manifold THz Classification Pipeline",
        fontsize=17.5, fontweight='bold', ha='center', color='#1A202C')
ax.text(5.0, 27.6, "Pellet-Grouped Double-Nested 5-Fold CV Across Three Botanical Matrices",
        fontsize=12.0, style='italic', ha='center', color='#4A5568')


def draw_box(x, y, w, h, text, facecolor, edgecolor, fontsize=10.5, fontweight='normal'):
    rect = patches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.14",
        linewidth=1.4, edgecolor=edgecolor, facecolor=facecolor, zorder=2
    )
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
            fontsize=fontsize, fontweight=fontweight, color='#1A202C', zorder=3, linespacing=1.3)


def draw_arrow(x1, y1, x2, y2, ls='-', color='#2D3748'):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6, ls=ls, mutation_scale=14), zorder=4)


# ================= Module 1: Acquisition & Physical QC =================
rect_m1 = patches.FancyBboxPatch((0.35, 22.0), 9.3, 5.1, boxstyle="round,pad=0.08,rounding_size=0.18",
                                 linewidth=1.6, edgecolor='#2B5C8F', facecolor='#F7FAFC', linestyle='--', zorder=0)
ax.add_patch(rect_m1)
ax.text(0.6, 26.62, "1. THz-TDS Acquisition & Single-Spectrum Physical QC",
        fontsize=12.2, fontweight='bold', color='#2B5C8F')

draw_box(1.0, 24.95, 8.0, 1.25,
         "TERA K15 Transmission (Dry N₂ < 4% RH, 292 K, Pure Pressed Pellets)\n"
         "α(ω) & n(ω) across 0.22–1.04 THz (358 pts) | ~20 Pellets × 5 Scans/Class",
         '#EDF2F7', '#4A5568', fontsize=10.2)
draw_arrow(5.0, 24.95, 5.0, 23.75)

draw_box(1.2, 22.35, 7.6, 1.25,
         "Unified Single-Spectrum Physical QC (Zero Cross-Sample Stats)\n"
         "1.2 ≤ n̄ ≤ 2.6  AND  ᾱ ≤ 55.0 cm⁻¹  (1,300 / 1,308 Scans Kept)",
         '#DBEAFE', '#1E40AF', fontsize=10.4, fontweight='bold')

draw_arrow(5.0, 22.35, 5.0, 21.35)


# ================= Module 2: Intra-Sample Dual-View Representation =================
rect_m2 = patches.FancyBboxPatch((0.35, 15.6), 9.3, 5.65, boxstyle="round,pad=0.08,rounding_size=0.18",
                                 linewidth=1.6, edgecolor='#276749', facecolor='#F0FFF4', linestyle='--', zorder=0)
ax.add_patch(rect_m2)
ax.text(0.6, 20.78, "2. Intra-Sample Dual-View Feature Representation (3,222-Dim)",
        fontsize=12.2, fontweight='bold', color='#276749')

ax.plot([2.7, 7.3], [20.28, 20.28], color='#276749', lw=1.5, zorder=4)
draw_arrow(2.7, 20.28, 2.7, 19.75, color='#276749')
draw_arrow(7.3, 20.28, 7.3, 19.75, color='#276749')

draw_box(0.65, 17.75, 4.1, 1.9,
         "View 1: Scatter-Attenuated\nSNV + Multi-Scale SG (1,790-d)\n[env(α̃), d¹(α̃), d²(α̃), env(ñ), d¹(ñ)]",
         '#C6F6D5', '#22543D', fontsize=10.0)

draw_box(5.25, 17.75, 4.1, 1.9,
         "View 2: Amplitude-Preserving\nUn-normalized SG (1,432-d)\n[env(α), d²(α), env(n), d¹(n)]",
         '#C6F6D5', '#22543D', fontsize=10.0)

draw_arrow(2.7, 17.75, 4.2, 16.95)
draw_arrow(7.3, 17.75, 5.8, 16.95)

draw_box(1.3, 15.85, 7.4, 1.0,
         "Concatenated Dual-View Tensor (3,222-Dim, Strict Single-Sample Ops)",
         '#FEEBC8', '#C05621', fontsize=10.4, fontweight='bold')

draw_arrow(5.0, 15.85, 5.0, 14.9)


# ================= Module 3: Pellet-Grouped Double-Nested 5-Fold CV =================
rect_m3 = patches.FancyBboxPatch((0.35, 5.2), 9.3, 9.6, boxstyle="round,pad=0.08,rounding_size=0.18",
                                 linewidth=1.6, edgecolor='#9B2C2C', facecolor='#FFF5F5', linestyle='--', zorder=0)
ax.add_patch(rect_m3)
ax.text(0.6, 14.32, "3. Pellet-Grouped Double-Nested 5-Fold CV (StratifiedGroupKFold)",
        fontsize=12.2, fontweight='bold', color='#9B2C2C')

draw_box(1.0, 12.95, 8.0, 1.1,
         "Outer 5-Fold Split Grouped by Pellet ID (5 Scans/Pellet Locked Together)\n"
         "80% Training Pellets  |  20% Sequestered Held-Out Test Pellets",
         '#FED7D7', '#742A2A', fontsize=10.2, fontweight='bold')

draw_arrow(3.45, 12.95, 3.45, 12.1)
draw_arrow(7.95, 12.95, 7.95, 11.15, ls='--', color='#1E40AF')

ax.text(7.95, 9.55, "Held-Out\nTest Pellets\n(20%)\n\nZero Pellet\nOverlap",
        ha='center', va='center', fontsize=10.4, color='#1E40AF', fontweight='bold', zorder=3,
        bbox=dict(boxstyle='round,pad=0.4', facecolor='#EFF6FF', edgecolor='#60A5FA', lw=1.3))
draw_arrow(7.95, 7.9, 7.95, 6.9, ls='--', color='#1E40AF')

rect_inner = patches.FancyBboxPatch((0.65, 7.25), 5.6, 4.75, boxstyle="round,pad=0.06,rounding_size=0.14",
                                    linewidth=1.4, edgecolor='#E53E3E', facecolor='#FFFFFF', linestyle=':', zorder=1)
ax.add_patch(rect_inner)
ax.text(0.85, 11.65, "Inner 3-Fold Pellet-Grouped CV (Train Only)",
        fontsize=10.2, color='#9B2C2C', fontweight='bold', style='italic')

draw_box(0.9, 10.35, 5.1, 1.05,
         "Z-Score + Full-Rank MC-UVE\n(K−1 PLS, 30 Subsamples → Stability sⱼ)",
         '#FED7D7', '#742A2A', fontsize=9.8)
draw_arrow(3.45, 10.35, 3.45, 9.7)

draw_box(0.9, 8.65, 5.1, 1.0,
         "Top-35% Weighting wⱼ=(sⱼ/sₘₐₓ)^0.5\n+ Purified Shrinkage Eigen-LDA (λ)",
         '#FED7D7', '#742A2A', fontsize=9.8)
draw_arrow(3.45, 8.65, 3.45, 8.05)

draw_box(0.9, 7.4, 5.1, 0.62,
         "Tune (λ, C, γ) via Inner 3-Fold CV",
         '#FED7D7', '#742A2A', fontsize=9.8)

draw_arrow(3.45, 7.25, 3.45, 6.55)

draw_box(0.9, 5.5, 5.1, 1.0,
         "Refit Pipeline on Full Outer Train\n→ Anisotropic RBF-SVM Classifier",
         '#FCA5A5', '#742A2A', fontsize=10.0, fontweight='bold')

draw_box(6.55, 5.5, 2.8, 1.35,
         "Blind Test Evaluation\nScan Acc + Pellet Vote\n& Bootstrap 95% CI",
         '#DBEAFE', '#1E40AF', fontsize=9.9, fontweight='bold')

draw_arrow(6.0, 6.0, 6.55, 6.0)
draw_arrow(7.95, 5.5, 7.95, 4.55)


# ================= Module 4: Cross-Matrix Re-Evaluation & DFT =================
rect_m4 = patches.FancyBboxPatch((0.35, 0.5), 9.3, 3.95, boxstyle="round,pad=0.08,rounding_size=0.18",
                                 linewidth=1.6, edgecolor='#553C9A', facecolor='#FAF5FF', linestyle='--', zorder=0)
ax.add_patch(rect_m4)
ax.text(0.6, 3.98, "4. Multi-Matrix Re-Evaluation & Tentative DFT Benchmarks",
        fontsize=12.2, fontweight='bold', color='#553C9A')

draw_box(0.65, 0.85, 4.15, 2.8,
         "Matrix-Specific Nested CV\n(Fixed Architecture, No Retuning)\n\n"
         "• Root: Astragali Radix (80 Pellets)\n"
         "• Seed: Ziziphi Spinosae (100 Pellets)\n"
         "• Tuber: Gastrodia elata (82 Pellets)",
         '#E9D8FD', '#44337A', fontsize=9.8)

draw_box(5.2, 0.85, 4.15, 2.8,
         "Tentative DFT-D3(BJ)/6-31G(d)\n(Gas-Phase Vibrational Benchmarks)\n\n"
         "• Calycosin: 0.552, 0.885 THz\n"
         "• Spinosin: 0.605, 0.886, 0.979 THz\n"
         "• Aligned with MC-UVE Stability",
         '#E9D8FD', '#44337A', fontsize=9.8)

draw_arrow(4.8, 2.25, 5.2, 2.25, ls=':', color='#553C9A')

plt.tight_layout()
for out_p in [ROOT_DIR / "Pipeline_Flowchart_Clean.png", SUB_FIG_DIR / "Scheme_1_Pipeline.png"]:
    plt.savefig(out_p, dpi=300, bbox_inches='tight')
plt.close(fig)
print("Saved upgraded Scheme 1 successfully!")
