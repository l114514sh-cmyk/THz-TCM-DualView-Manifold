from pathlib import Path
import glob
import openpyxl
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_ROOT = PROJECT_DIR / "01_原始实验数据"
OUT_RES_DIR = PROJECT_DIR / "05_实验结果" / "模型结果"
SUB_FIG_DIR = PROJECT_DIR / "06_论文写作" / "Submission_Figures"
OUT_RES_DIR.mkdir(parents=True, exist_ok=True)
SUB_FIG_DIR.mkdir(parents=True, exist_ok=True)

herbs = [
    ("Astragali Radix (Root)", DATA_ROOT / "黄芪", "#1B4F72"),
    ("Ziziphi Spinosae Semen (Seed)", DATA_ROOT / "酸枣仁", "#1E8449"),
    ("Gastrodia elata (Tuber)", DATA_ROOT / "天麻", "#B03A2E"),
]

fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.3), dpi=300, sharey=True)

for ax, (title, folder, col) in zip(axes, herbs):
    fpath = sorted(glob.glob(str(folder / "*.xlsx")))[0]
    wb = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
    ws = wb["频域"]
    ws.reset_dimensions()
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    arr = np.array([[float(x) if x is not None else np.nan for x in r] for r in rows[1:]])
    freq = arr[:, 0]
    ref_db = arr[:, 1]
    samp_db = arr[:, 2:]

    nf_mask = freq >= 2.5
    nf_ref = float(np.nanmean(ref_db[nf_mask]))
    dr_ref = ref_db - nf_ref
    dr_samp_m = np.nanmean(samp_db, axis=1) - nf_ref
    dr_samp_s = np.nanstd(samp_db, axis=1)

    m_plot = (freq >= 0.05) & (freq <= 2.5)
    f_p = freq[m_plot]

    ax.axvspan(0.22, 1.04, color='#D6EAF8', alpha=0.55, label='Analyzed Band (0.22–1.04 THz)')
    ax.plot(f_p, dr_ref[m_plot], color='#2C3E50', lw=1.6, ls='--', label='Reference DR (Dry N₂)')
    ax.plot(f_p, dr_samp_m[m_plot], color=col, lw=1.8, label='Sample Mean DR (±1 SD)')
    ax.fill_between(f_p, (dr_samp_m - dr_samp_s)[m_plot], (dr_samp_m + dr_samp_s)[m_plot],
                    color=col, alpha=0.20)
    ax.axhline(0, color='#7F8C8D', ls=':', lw=1.0, label='Noise Floor (0 dB)')

    dr_104 = float(dr_samp_m[np.argmin(np.abs(freq - 1.04))])
    ax.annotate(f"1.04 THz:\n{dr_104:.1f} dB", xy=(1.04, dr_104), xytext=(1.28, dr_104 + 12),
                fontsize=8.5, fontweight='bold', color=col,
                arrowprops=dict(arrowstyle='->', color=col, lw=1.1),
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec=col, alpha=0.9))

    ax.set_title(title, fontsize=10.5, fontweight='bold', pad=8)
    ax.set_xlabel('Frequency (THz)', fontsize=10.0)
    ax.set_xlim(0.05, 2.5)
    ax.set_ylim(-5, 82)
    ax.grid(True, ls='--', alpha=0.35)
    if ax is axes[0]:
        ax.set_ylabel('Measured Dynamic Range (dB)', fontsize=10.2, fontweight='bold')
    ax.legend(loc='upper right', fontsize=7.6, frameon=True)

fig.suptitle('Measured THz-TDS Transmission Dynamic Range (TERA K15, Pure Pressed Herbal Pellets)',
             fontsize=11.5, fontweight='bold', y=1.02)
plt.tight_layout()
for out_p in [OUT_RES_DIR / "Figure_S2_Dynamic_Range.png", SUB_FIG_DIR / "Figure_S2_Dynamic_Range.png"]:
    plt.savefig(out_p, dpi=300, bbox_inches='tight')
plt.close(fig)
print("Saved Figure_S2_Dynamic_Range.png successfully!")
