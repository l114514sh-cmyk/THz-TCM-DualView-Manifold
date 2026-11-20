import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']

fig, ax = plt.subplots(figsize=(10.4, 15.2), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 30.2)
ax.axis('off')

# Main Title
ax.text(5.0, 29.4, "Dual-View SW-MCUVE-Manifold THz Traceability Pipeline",
        fontsize=15.5, fontweight='bold', ha='center', color='#1A202C')
ax.text(5.0, 28.75, "(Strict Double-Nested 5-Fold Cross-Validation & Cross-Matrix Generalization)",
        fontsize=10.5, style='italic', ha='center', color='#4A5568')


def draw_box(x, y, w, h, text, facecolor, edgecolor, fontsize=8.8, fontweight='normal'):
    rect = patches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
        linewidth=1.25, edgecolor=edgecolor, facecolor=facecolor, zorder=2
    )
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
            fontsize=fontsize, fontweight=fontweight, color='#1A202C', zorder=3)


def draw_arrow(x1, y1, x2, y2, ls='-', color='#2D3748'):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.35, ls=ls, mutation_scale=12), zorder=4)


# ================= Module 1: Acquisition & Physical QC =================
rect_m1 = patches.FancyBboxPatch((0.45, 22.8), 9.1, 5.4, boxstyle="round,pad=0.08,rounding_size=0.18",
                                 linewidth=1.5, edgecolor='#2B5C8F', facecolor='#F7FAFC', linestyle='--', zorder=0)
ax.add_patch(rect_m1)
ax.text(0.7, 27.78, "Module 1: THz-TDS Measurement, Optical Extraction & Physical QC",
        fontsize=10.8, fontweight='bold', color='#2B5C8F')

draw_box(1.9, 26.3, 6.2, 1.0,
         "THz-TDS Transmission Measurement (TERA K15, Dry N₂ < 4% RH, 292 K)\nRoot (Astragali Radix) | Seed (Ziziphi Spinosae) | Tuber (Gastrodia elata)",
         '#EDF2F7', '#4A5568', fontsize=8.5)
draw_arrow(5.0, 26.3, 5.0, 25.7)

draw_box(1.6, 24.6, 6.8, 1.05,
         "FFT → Duvillaret–Dorney Optical Parameter Extraction\nα(ω) & n(ω) (0.22–1.04 THz, 358 Freq. Points)",
         '#EDF2F7', '#4A5568', fontsize=8.6)
draw_arrow(5.0, 24.6, 5.0, 24.0)

draw_box(1.8, 23.0, 6.4, 0.95,
         "Single-Spectrum Physical QC (Zero Cross-Sample Stats)\nOptical Bound 1.2 ≤ n̄ ≤ 2.6 & Attenuation Bound ᾱ ≤ 55 cm⁻¹",
         '#DBEAFE', '#1E40AF', fontsize=8.6, fontweight='bold')

# Clean single vertical connector from Module 1 -> Module 2 (no text crossing)
draw_arrow(5.0, 23.0, 5.0, 22.15)


# ================= Module 2: Intra-Sample Dual-View Representation =================
rect_m2 = patches.FancyBboxPatch((0.45, 16.2), 9.1, 5.9, boxstyle="round,pad=0.08,rounding_size=0.18",
                                 linewidth=1.5, edgecolor='#276749', facecolor='#F0FFF4', linestyle='--', zorder=0)
ax.add_patch(rect_m2)
ax.text(0.7, 21.65, "Module 2: Intra-Sample Dual-View Physical Feature Extraction (Zero Leakage)",
        fontsize=10.8, fontweight='bold', color='#276749')

# Internal horizontal split bar below header
ax.plot([2.75, 7.25], [21.15, 21.15], color='#276749', lw=1.35, zorder=4)
draw_arrow(2.75, 21.15, 2.75, 20.68, color='#276749')
draw_arrow(7.25, 21.15, 7.25, 20.68, color='#276749')

draw_box(0.8, 18.7, 3.9, 1.92,
         "View 1: Scattering-Invariant Morphology\nIntra-Sample SNV + Multi-Scale SG\n[env(α̃), d¹(α̃), d²(α̃), env(ñ), d¹(ñ)] (1,790-Dim)\nCancels Multiplicative Mie Scattering βᵢ",
         '#C6F6D5', '#22543D', fontsize=8.3)

draw_box(5.3, 18.7, 3.9, 1.92,
         "View 2: Amplitude-Preserving Dielectric\nUn-normalized SG Envelope & Derivatives\n[env(α), d²(α), env(n), d¹(n)] (1,432-Dim)\nPreserves Lipid/Moisture Dielectric Scale",
         '#C6F6D5', '#22543D', fontsize=8.3)

draw_arrow(2.75, 18.7, 4.3, 17.65)
draw_arrow(7.25, 18.7, 5.7, 17.65)

draw_box(1.7, 16.5, 6.6, 1.1,
         "Dual-View Physical Feature Tensor Concatenation (3,222-Dimensional Vector)\n100% Single-Sample Frequency-Axis Operations: ∂x̃ᵢ / ∂xₖ = 0 (for all i ≠ k)",
         '#FEEBC8', '#C05621', fontsize=8.6, fontweight='bold')

draw_arrow(5.0, 16.5, 5.0, 15.58)


# ================= Module 3: Strict Double-Nested 5-Fold CV =================
rect_m3 = patches.FancyBboxPatch((0.45, 5.55), 9.1, 10.0, boxstyle="round,pad=0.08,rounding_size=0.18",
                                 linewidth=1.5, edgecolor='#9B2C2C', facecolor='#FFF5F5', linestyle='--', zorder=0)
ax.add_patch(rect_m3)
ax.text(0.7, 15.1, "Module 3: Strict Double-Nested 5-Fold CV (Outer Blind Test + Inner Tuning)",
        fontsize=10.8, fontweight='bold', color='#9B2C2C')

draw_box(1.6, 13.85, 6.8, 0.95,
         "Stratified Outer 5-Fold Splitting (SEED = 42)\n80% Outer Training Fold  |  20% Sequestered Outer Blind Test Fold",
         '#FED7D7', '#742A2A', fontsize=8.6, fontweight='bold')

draw_arrow(3.52, 13.85, 3.52, 12.92)

# Clean vertical dashed routing through the Sequestered Test Fold badge (no overlap!)
draw_arrow(7.85, 13.85, 7.85, 11.75, ls='--', color='#1E40AF')
ax.text(7.85, 10.2, "Sequestered\nOuter Test Fold\n(20% Held-Out)\n\nZero Feature or\nHyperparameter\nLeakage",
        ha='center', va='center', fontsize=8.6, color='#1E40AF', fontweight='bold', zorder=3,
        bbox=dict(boxstyle='round,pad=0.38', facecolor='#EFF6FF', edgecolor='#60A5FA', lw=1.15))
draw_arrow(7.85, 8.65, 7.85, 7.22, ls='--', color='#1E40AF')

# Inner 3-Fold Loop Box
rect_inner = patches.FancyBboxPatch((0.8, 7.6), 5.45, 5.25, boxstyle="round,pad=0.06,rounding_size=0.14",
                                    linewidth=1.3, edgecolor='#E53E3E', facecolor='#FFFFFF', linestyle=':', zorder=1)
ax.add_patch(rect_inner)
ax.text(1.0, 12.5, "Inner 3-Fold CV (Strictly Inside 80% Outer Train)",
        fontsize=8.8, color='#9B2C2C', fontweight='bold', style='italic')

draw_box(1.05, 11.2, 4.95, 1.05,
         "Z-Score Scaling + Full-Rank MC-UVE\n(K−1 PLS Components, 30 MC Subsamples → Stability sⱼ)",
         '#FED7D7', '#742A2A', fontsize=8.3)
draw_arrow(3.52, 11.2, 3.52, 10.55)

draw_box(1.05, 9.45, 4.95, 1.05,
         "Anisotropic Stability Weighting & Purified Manifold\nwⱼ = (sⱼ/sₘₐₓ)^0.5 (Top 35%) + Shrinkage Eigen-LDA (λ)",
         '#FED7D7', '#742A2A', fontsize=8.3)
draw_arrow(3.52, 9.45, 3.52, 8.8)

draw_box(1.05, 7.82, 4.95, 0.92,
         "Inner 3-Fold Hyperparameter Selection (λ, C, γ)\nGrid: λ={1,2,3}, C={1,5,10,50}, γ={scale, 0.002, 0.005}",
         '#FED7D7', '#742A2A', fontsize=8.1)

draw_arrow(3.52, 7.6, 3.52, 6.9)

draw_box(1.05, 5.85, 4.95, 1.0,
         "Refit Locked Pipeline on Full Outer Train Fold\nwith Inner-Selected (λ*, C*, γ*) → Anisotropic RBF-SVM",
         '#FCA5A5', '#742A2A', fontsize=8.4, fontweight='bold')

draw_box(6.55, 5.85, 2.65, 1.32,
         "Single-Pass Blind Test\n20% Outer Test Fold\n→ Report Mean ± SD\n& Macro-F1",
         '#DBEAFE', '#1E40AF', fontsize=8.5, fontweight='bold')

draw_arrow(6.0, 6.35, 6.55, 6.35)
draw_arrow(7.85, 5.85, 7.85, 4.82)


# ================= Module 4: Cross-Matrix Validation & DFT Mechanism =================
rect_m4 = patches.FancyBboxPatch((0.45, 0.55), 9.1, 4.2, boxstyle="round,pad=0.08,rounding_size=0.18",
                                 linewidth=1.5, edgecolor='#553C9A', facecolor='#FAF5FF', linestyle='--', zorder=0)
ax.add_patch(rect_m4)
ax.text(0.7, 4.32, "Module 4: Cross-Matrix Methodological Validation & Quantum Chemical Benchmarks",
        fontsize=10.8, fontweight='bold', color='#553C9A')

draw_box(0.75, 0.98, 3.65, 2.95,
         "Locked Cross-Matrix Evaluation\n(Zero Architecture Changes)\n\n• Root: Astragali Radix (4 Origins)\n• Seed: Ziziphi Spinosae (5 Specs)\n• Tuber: Gastrodia elata (4 Origins,\n  Independent Cross-Matrix Validation)",
         '#E9D8FD', '#44337A', fontsize=8.2)

draw_box(5.6, 0.98, 3.65, 2.95,
         "DFT-D3(BJ)/6-31G(d) Benchmarks\n(Intramolecular Vibrational Reference)\n\n• Calycosin Aglycone Core:\n  B-Ring Torsion τ(C–C) at 0.885 THz\n• Spinosin Flavone Glycoside:\n  C-Glycosyl Rocking (0.552–0.979 THz)",
         '#E9D8FD', '#44337A', fontsize=8.2)

ax.text(5.0, 2.45, "◄ Bridge ►\nPhysical\nInterpretability", ha='center', va='center',
        fontsize=8.3, fontweight='bold', color='#553C9A')

plt.tight_layout()
out_path = r"e:\论文\Pipeline_Flowchart_Clean.png"
plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"[Done] Polished 300 DPI flowchart saved to: {out_path}")
