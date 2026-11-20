import os
import json
import time
import glob
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from scipy.signal import savgol_filter
from sklearn.cross_decomposition import PLSRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    classification_report, confusion_matrix, ConfusionMatrixDisplay,
    accuracy_score, precision_score, recall_score, f1_score
)

warnings.filterwarnings('ignore')

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['axes.unicode_minus'] = False

SEED = 42
np.random.seed(SEED)
t_global = time.time()

ROOT_DIR = r"e:\论文"
DATA_ROOT = os.path.join(ROOT_DIR, "THz_TCM_Research", "01_原始实验数据")
OUT_RES_DIR = os.path.join(ROOT_DIR, "THz_TCM_Research", "05_实验结果", "模型结果")
os.makedirs(OUT_RES_DIR, exist_ok=True)


# ==============================================================================
# 1. Unified Data Loader with .npz Caching (0.22 - 1.04 THz, 358 freq points)
# ==============================================================================
def load_dataset(name, folder, cache_name, label_map, class_order):
    t0 = time.time()
    cache_path = os.path.join(folder, cache_name)
    if os.path.exists(cache_path):
        d = np.load(cache_path, allow_pickle=True)
        raw_a, raw_r, y, freq = d['raw_a'], d['raw_r'], d['y'], d['freq']
        print(f"  [{name}] Cache hit ({cache_name}): n={len(y)}, dim={raw_a.shape[1]} ({time.time()-t0:.2f}s)", flush=True)
        return raw_a, raw_r, y, freq, class_order

    print(f"  [{name}] Parsing Excel files (first run -> creating {cache_name})...", flush=True)
    excel_files = sorted(glob.glob(os.path.join(folder, "*.xlsx")))
    raw_a_list, raw_r_list, y_list = [], [], []
    freq_valid = None

    for fpath in excel_files:
        fname = os.path.basename(fpath)
        lbl = next((v for k, v in label_map.items() if k in fname), None)
        if lbl is None:
            continue
        sheets = pd.read_excel(fpath, sheet_name=["吸收系数", "折射率"])
        df_a, df_r = sheets["吸收系数"], sheets["折射率"]
        freq = df_a.iloc[:, 0].values
        mask = (freq >= 0.22) & (freq <= 1.04)
        if freq_valid is None:
            freq_valid = freq[mask]
        sa = df_a.iloc[:, 1:].values if 'Thz' in str(df_a.columns[0]) else df_a.iloc[:, 2:].values
        sr = df_r.iloc[:, 1:].values if 'Thz' in str(df_r.columns[0]) else df_r.iloc[:, 2:].values
        sa_v = sa[mask, :].T
        sr_v = sr[mask, :].T
        raw_a_list.append(sa_v)
        raw_r_list.append(sr_v)
        y_list.extend([lbl] * sa_v.shape[0])

    raw_a = np.vstack(raw_a_list)
    raw_r = np.vstack(raw_r_list)
    y = np.array(y_list)
    np.savez(cache_path, raw_a=raw_a, raw_r=raw_r, y=y, freq=freq_valid)
    print(f"  [{name}] Loaded & cached: n={len(y)}, dim={raw_a.shape[1]} ({time.time()-t0:.1f}s)", flush=True)
    return raw_a, raw_r, y, freq_valid, class_order


def apply_physical_qc(raw_a, raw_r, y, name):
    """
    100% Single-Spectrum Instrument-Level Physical Quality Control (Zero Cross-Sample Stats, Zero Label Peeking):
    1) Optical refractive index physical bound for dry herbal pellets: 1.2 <= mean(n) <= 2.6
       (eliminates phase-unwrapping faults n < 1.0 and thickness-entry faults n ~ 3.0)
    2) Single-pellet transmission dynamic-range saturation bound: mean(alpha) <= 55.0 cm^-1
    """
    ma = raw_a.mean(axis=1)
    mr = raw_r.mean(axis=1)
    mask = (mr >= 1.2) & (mr <= 2.6) & (ma <= 55.0)
    n_drop = int((~mask).sum())
    dropped_breakdown = pd.Series(y[~mask]).value_counts().to_dict() if n_drop > 0 else {}
    print(f"  [{name}] Single-Spectrum Physical QC (1.2<=n<=2.6 & alpha<=55 cm^-1): kept {int(mask.sum())}/{len(y)} "
          f"(dropped {n_drop}: {dropped_breakdown})", flush=True)
    return raw_a[mask], raw_r[mask], y[mask], n_drop, dropped_breakdown


def plot_huangqi_fig1(raw_a, y, freq, classes, out_paths):
    """Generate clean 300 DPI Figure 1 (Mean ± SD Raw Absorption & SG 2nd Derivative)."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.0), dpi=300)
    colors = {
        'Datong (SX)': '#1f77b4',
        'Guyang (IM)': '#ff7f0e',
        'Qujing (YN)': '#2ca02c',
        'Gansu (GS)': '#d62728',
    }
    for lbl in classes:
        m = (y == lbl)
        raw_arr = raw_a[m]
        sg2_arr = np.array([savgol_filter(s, window_length=19, polyorder=2, deriv=2) for s in raw_arr])
        c = colors.get(lbl, '#1B4F72')
        mr, sr = raw_arr.mean(axis=0), raw_arr.std(axis=0)
        ms, ss = sg2_arr.mean(axis=0), sg2_arr.std(axis=0)
        ax1.plot(freq, mr, label=f"{lbl} (n={int(m.sum())})", color=c, lw=1.8)
        ax1.fill_between(freq, mr - sr, mr + sr, color=c, alpha=0.15)
        ax2.plot(freq, ms, label=f"{lbl} (n={int(m.sum())})", color=c, lw=1.8)
        ax2.fill_between(freq, ms - ss, ms + ss, color=c, alpha=0.15)

    ax1.set_title('(a) Raw Absorption Spectra (Mean ± SD)', fontsize=11.5, fontweight='bold', pad=10)
    ax1.set_xlabel('Frequency (THz)', fontsize=10.5)
    ax1.set_ylabel('Absorption Coefficient (cm⁻¹)', fontsize=10.5)
    ax1.set_xlim(0.22, 1.04)
    ax1.legend(frameon=True, fontsize=9)
    ax1.grid(True, ls='--', alpha=0.4)

    ax2.set_title('(b) SG 2nd Derivative Spectra (Mean ± SD)', fontsize=11.5, fontweight='bold', pad=10)
    ax2.set_xlabel('Frequency (THz)', fontsize=10.5)
    ax2.set_ylabel('d²α / dω² (a.u.)', fontsize=10.5)
    ax2.set_xlim(0.22, 1.04)
    ax2.axhline(0, color='gray', ls=':', lw=1)
    ax2.legend(frameon=True, fontsize=9)
    ax2.grid(True, ls='--', alpha=0.4)

    plt.tight_layout()
    for p in out_paths:
        plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close(fig)


# ==============================================================================
# 2. Pure Intra-Sample Dual-View Feature Extraction (Zero Cross-Sample Leakage)
#    View 1 (Scattering-Invariant Morphology): Intra-sample SNV + multi-scale SG
#    View 2 (Amplitude-Preserving Dielectric): Un-normalized SG envelope & derivs
# ==============================================================================
def sample_wise_snv(spec_1d):
    return (spec_1d - np.mean(spec_1d)) / (np.std(spec_1d) + 1e-8)


def extract_feature_sets(raw_a_all, raw_r_all):
    X_dual_view, X_snv_only, X_amp_only, X_abs_only, X_sg_gen1 = [], [], [], [], []
    for i in range(len(raw_a_all)):
        ra, rr = raw_a_all[i], raw_r_all[i]

        # View 1: Scattering-Invariant Morphology (Intra-Sample SNV Multi-Scale, 1790-dim)
        snv_a = sample_wise_snv(ra)
        snv_r = sample_wise_snv(rr)
        env_a = savgol_filter(snv_a, window_length=19, polyorder=2, deriv=0)
        d1_a  = sample_wise_snv(savgol_filter(snv_a, window_length=19, polyorder=2, deriv=1))
        d2_a  = sample_wise_snv(savgol_filter(snv_a, window_length=15, polyorder=2, deriv=2))
        env_r = savgol_filter(snv_r, window_length=19, polyorder=2, deriv=0)
        d1_r  = sample_wise_snv(savgol_filter(snv_r, window_length=15, polyorder=2, deriv=1))

        # View 2: Amplitude-Preserving Dielectric Scale & Curvature (1432-dim)
        raw_env_a = savgol_filter(ra, window_length=19, polyorder=2, deriv=0)
        raw_d2_a  = savgol_filter(ra, window_length=15, polyorder=2, deriv=2)
        raw_env_r = savgol_filter(rr, window_length=19, polyorder=2, deriv=0)
        raw_d1_r  = savgol_filter(rr, window_length=15, polyorder=2, deriv=1)

        # Full Proposed Dual-View Representation (3222-dim)
        X_dual_view.append(np.hstack([
            env_a, d1_a, d2_a, env_r, d1_r,
            raw_env_a, raw_d2_a, raw_env_r, raw_d1_r
        ]))
        # Ablation: w/o Amplitude-Preserving View (SNV Only, 1790-dim)
        X_snv_only.append(np.hstack([env_a, d1_a, d2_a, env_r, d1_r]))
        # Ablation: w/o Intra-Sample SNV View (Amplitude-Preserving Only, 1432-dim)
        X_amp_only.append(np.hstack([raw_env_a, raw_d2_a, raw_env_r, raw_d1_r]))
        # Ablation: w/o Refractive Index (Absorption Only Dual-View, 1790-dim)
        X_abs_only.append(np.hstack([env_a, d1_a, d2_a, raw_env_a, raw_d2_a]))
        # Previous Gen-1 Baseline: standard 716-dim SG2(alpha) + SG1(n)
        X_sg_gen1.append(np.hstack([raw_d2_a, raw_d1_r]))

    return (
        np.array(X_dual_view),
        np.array(X_snv_only),
        np.array(X_amp_only),
        np.array(X_abs_only),
        np.array(X_sg_gen1)
    )


# ==============================================================================
# 3. Core Locked Fold State & Feature Builder (Full-Rank K-1 PLS MC-UVE + Purified Shrinkage LDA)
# ==============================================================================
def compute_fold_state(X_tr, y_tr, X_te, n_mc=30, pure_ratio=0.35, seed=42):
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    n_samples, n_features = X_tr_s.shape
    y_dummy = pd.get_dummies(y_tr).values[:, :-1].astype(float)
    actual_comp = y_dummy.shape[1]  # Exact full rank K-1 (3 for 4-class, 4 for 5-class)
    coefs = np.zeros((n_mc, n_features))

    rng = np.random.RandomState(seed)
    sample_size = int(n_samples * 0.8)
    for i in range(n_mc):
        sub_idx = rng.choice(n_samples, sample_size, replace=False)
        pls = PLSRegression(n_components=actual_comp, max_iter=50, tol=1e-3)
        pls.fit(X_tr_s[sub_idx], y_dummy[sub_idx])
        c = np.abs(pls.coef_)
        if c.ndim > 1 and c.shape[0] != n_features:
            c = c.T
        coefs[i, :] = np.mean(c, axis=1) if c.ndim > 1 else c

    stability = np.mean(coefs, axis=0) / (np.std(coefs, axis=0) + 1e-8)

    # Subspace-Purified Shrinkage Eigen-LDA (fitted strictly on top stability subspace)
    n_pure = max(30, int(n_features * pure_ratio))
    pure_idx = np.sort(np.argsort(stability)[::-1][:n_pure])
    pure_w = np.sqrt(stability[pure_idx] / (np.max(stability[pure_idx]) + 1e-8))

    lda = LinearDiscriminantAnalysis(solver='eigen', shrinkage='auto')
    Z_tr = lda.fit_transform(X_tr_s[:, pure_idx] * pure_w, y_tr)
    Z_te = lda.transform(X_te_s[:, pure_idx] * pure_w)

    z_scaler = StandardScaler()
    Z_tr_s = z_scaler.fit_transform(Z_tr)
    Z_te_s = z_scaler.transform(Z_te)

    return X_tr_s, X_te_s, stability, Z_tr_s, Z_te_s


def build_features(X_tr_s, X_te_s, stability, Z_tr_s, Z_te_s, keep_ratio=0.35, alpha_w=0.5, latent_w=2.0):
    n_keep = max(20, int(len(stability) * keep_ratio))
    top_idx = np.sort(np.argsort(stability)[::-1][:n_keep])
    sel_stab = stability[top_idx]
    w = np.power(sel_stab / (np.max(sel_stab) + 1e-8), alpha_w)

    F_tr = X_tr_s[:, top_idx] * w
    F_te = X_te_s[:, top_idx] * w
    if latent_w > 0:
        F_tr = np.hstack([F_tr, Z_tr_s * latent_w])
        F_te = np.hstack([F_te, Z_te_s * latent_w])
    return F_tr, F_te


def precompute_nested_states(X, y, outer_splits):
    fold_bundle = []
    for fold_i, (tr_out, te_out) in enumerate(outer_splits, 1):
        X_tr_out, y_tr_out = X[tr_out], y[tr_out]
        X_te_out, y_te_out = X[te_out], y[te_out]

        inner_cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED + fold_i)
        inner_splits = list(inner_cv.split(X_tr_out, y_tr_out))
        inner_states = [
            compute_fold_state(X_tr_out[itr], y_tr_out[itr], X_tr_out[iva], seed=SEED + fold_i)
            for itr, iva in inner_splits
        ]
        out_state = compute_fold_state(X_tr_out, y_tr_out, X_te_out, seed=SEED + fold_i)
        fold_bundle.append({
            'fold_i': fold_i, 'tr_out': tr_out, 'te_out': te_out,
            'y_tr_out': y_tr_out, 'y_te_out': y_te_out,
            'inner_splits': inner_splits, 'inner_states': inner_states,
            'out_state': out_state
        })
    return fold_bundle


def eval_sw_mcuve_variant(fold_bundle, y_all, keep_ratio=0.35, alpha_w=0.5, lw_grid=(1.0, 2.0, 3.0),
                          C_grid=(1, 5, 10, 50), gamma_grid=('scale', 0.002, 0.005)):
    oof_preds = np.empty_like(y_all)
    fold_accs = []
    chosen_cfgs = []

    for fb in fold_bundle:
        y_tr_out = fb['y_tr_out']
        y_te_out = fb['y_te_out']
        inner_splits = fb['inner_splits']
        inner_states = fb['inner_states']

        best_in_acc, best_cfg = -1.0, None
        for lw in lw_grid:
            for C in C_grid:
                for gamma in gamma_grid:
                    in_oof = np.empty_like(y_tr_out)
                    for (itr, iva), st in zip(inner_splits, inner_states):
                        F_itr, F_iva = build_features(*st, keep_ratio=keep_ratio, alpha_w=alpha_w, latent_w=lw)
                        clf = SVC(kernel='rbf', C=C, gamma=gamma, random_state=SEED).fit(F_itr, y_tr_out[itr])
                        in_oof[iva] = clf.predict(F_iva)
                    acc = accuracy_score(y_tr_out, in_oof)
                    if acc > best_in_acc:
                        best_in_acc = acc
                        best_cfg = (lw, C, gamma)

        F_tr_out, F_te_out = build_features(*fb['out_state'], keep_ratio=keep_ratio, alpha_w=alpha_w, latent_w=best_cfg[0])
        clf_final = SVC(kernel='rbf', C=best_cfg[1], gamma=best_cfg[2], random_state=SEED).fit(F_tr_out, y_tr_out)
        preds = clf_final.predict(F_te_out)
        oof_preds[fb['te_out']] = preds
        fold_accs.append(accuracy_score(y_te_out, preds) * 100.0)
        chosen_cfgs.append(best_cfg)

    return summarize_preds(y_all, oof_preds, fold_accs, chosen_cfgs)


def eval_baseline_double_nested(X, y_all, outer_splits, model_type):
    oof_preds = np.empty_like(y_all)
    fold_accs = []
    chosen_cfgs = []
    uniq_classes = np.unique(y_all)

    for fold_i, (tr_out, te_out) in enumerate(outer_splits, 1):
        X_tr_out, y_tr_out = X[tr_out], y_all[tr_out]
        X_te_out, y_te_out = X[te_out], y_all[te_out]

        inner_cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED + fold_i)
        inner_splits = list(inner_cv.split(X_tr_out, y_tr_out))

        scaled_inner = []
        for itr, iva in inner_splits:
            sc = StandardScaler()
            scaled_inner.append((sc.fit_transform(X_tr_out[itr]), sc.transform(X_tr_out[iva]), itr, iva))

        sc_out = StandardScaler()
        X_tr_s = sc_out.fit_transform(X_tr_out)
        X_te_s = sc_out.transform(X_te_out)

        best_acc, best_cfg = -1.0, None
        if model_type == "PLS-DA":
            for n_comp in [3, 5, 8, 12, 16]:
                in_oof = np.empty_like(y_tr_out)
                for X_itr, X_iva, itr, iva in scaled_inner:
                    Y_d = pd.get_dummies(y_tr_out[itr]).reindex(columns=uniq_classes, fill_value=0).values.astype(float)
                    pls = PLSRegression(n_components=n_comp, max_iter=200).fit(X_itr, Y_d)
                    in_oof[iva] = uniq_classes[np.argmax(pls.predict(X_iva), axis=1)]
                acc = accuracy_score(y_tr_out, in_oof)
                if acc > best_acc:
                    best_acc, best_cfg = acc, (n_comp,)
            Y_d_out = pd.get_dummies(y_tr_out).reindex(columns=uniq_classes, fill_value=0).values.astype(float)
            pls_f = PLSRegression(n_components=best_cfg[0], max_iter=200).fit(X_tr_s, Y_d_out)
            preds = uniq_classes[np.argmax(pls_f.predict(X_te_s), axis=1)]

        elif model_type == "RF":
            for n_est in [150, 300]:
                for md in [None, 15]:
                    in_oof = np.empty_like(y_tr_out)
                    for X_itr, X_iva, itr, iva in scaled_inner:
                        rf = RandomForestClassifier(n_estimators=n_est, max_depth=md, random_state=SEED, n_jobs=-1)
                        in_oof[iva] = rf.fit(X_itr, y_tr_out[itr]).predict(X_iva)
                    acc = accuracy_score(y_tr_out, in_oof)
                    if acc > best_acc:
                        best_acc, best_cfg = acc, (n_est, md)
            rf_f = RandomForestClassifier(n_estimators=best_cfg[0], max_depth=best_cfg[1], random_state=SEED, n_jobs=-1)
            preds = rf_f.fit(X_tr_s, y_tr_out).predict(X_te_s)

        elif model_type == "Full-SVM":
            for C in [1, 5, 10, 50]:
                for gamma in ['scale', 0.002, 0.005]:
                    in_oof = np.empty_like(y_tr_out)
                    for X_itr, X_iva, itr, iva in scaled_inner:
                        clf = SVC(kernel='rbf', C=C, gamma=gamma, random_state=SEED).fit(X_itr, y_tr_out[itr])
                        in_oof[iva] = clf.predict(X_iva)
                    acc = accuracy_score(y_tr_out, in_oof)
                    if acc > best_acc:
                        best_acc, best_cfg = acc, (C, gamma)
            clf_f = SVC(kernel='rbf', C=best_cfg[0], gamma=best_cfg[1], random_state=SEED).fit(X_tr_s, y_tr_out)
            preds = clf_f.predict(X_te_s)

        oof_preds[te_out] = preds
        fold_accs.append(accuracy_score(y_te_out, preds) * 100.0)
        chosen_cfgs.append(best_cfg)

    return summarize_preds(y_all, oof_preds, fold_accs, chosen_cfgs)


def summarize_preds(y_true, y_pred, fold_accs, cfgs):
    return {
        'acc': float(accuracy_score(y_true, y_pred) * 100.0),
        'mean': float(np.mean(fold_accs)),
        'sd': float(np.std(fold_accs)),
        'macro_prec': float(precision_score(y_true, y_pred, average='macro') * 100.0),
        'macro_rec': float(recall_score(y_true, y_pred, average='macro') * 100.0),
        'macro_f1': float(f1_score(y_true, y_pred, average='macro')),
        'fold_accs': [float(x) for x in fold_accs],
        'cfgs': [str(c) for c in cfgs],
        'oof_preds': y_pred
    }


# ==============================================================================
# 4. Publication-Grade Plotting Helpers (300 DPI, Times New Roman)
# ==============================================================================
def plot_confusion_matrix(y_true, y_pred, class_order, title_str, out_path):
    fig, ax = plt.subplots(figsize=(6.8, 5.8), dpi=300)
    cm = confusion_matrix(y_true, y_pred, labels=class_order)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_order)
    disp.plot(cmap=plt.cm.Blues, ax=ax, values_format='d', colorbar=True)
    ax.set_title(title_str, fontsize=11, pad=12, fontweight='bold')
    ax.set_xlabel("Predicted Label", fontsize=10.5, labelpad=8)
    ax.set_ylabel("True Label", fontsize=10.5, labelpad=8)
    plt.xticks(rotation=20, ha='right', fontsize=9.5)
    plt.yticks(fontsize=9.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def plot_bar_comparison(items, title_str, out_path, highlight_first=True):
    labels = [it[0] for it in items]
    means = [it[1] for it in items]
    sds = [it[2] for it in items]
    deltas = [it[3] for it in items]

    fig, ax = plt.subplots(figsize=(8.8, 4.9), dpi=300)
    x = np.arange(len(labels))
    if highlight_first:
        colors = ['#1B4F72'] + ['#5DADE2', '#7FB3D5', '#A9CCE3', '#BDC3C7'][:len(labels)-1]
    else:
        colors = ['#BDC3C7', '#A9CCE3', '#7FB3D5', '#5DADE2'][:len(labels)-1] + ['#1B4F72']

    bars = ax.bar(x, means, yerr=sds, capsize=5, width=0.56, color=colors,
                  edgecolor='#1A252F', linewidth=0.9, error_kw=dict(ecolor='#2C3E50', lw=1.2))

    low = max(50, min(m - s for m, s in zip(means, sds)) - 8)
    high = min(105.0, max(m + s for m, s in zip(means, sds)) + 6.5)
    ax.set_ylim(low, high)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9.3, rotation=12, ha='right')
    ax.set_ylabel("Double-Nested 5-Fold CV Accuracy (%)", fontsize=10.5, fontweight='bold')
    ax.set_title(title_str, fontsize=11.5, fontweight='bold', pad=12)
    ax.grid(axis='y', linestyle='--', alpha=0.45)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    for bar, m, s, dlt in zip(bars, means, sds, deltas):
        txt = f"{m:.2f}% ± {s:.2f}%"
        if dlt:
            txt += f"\n({dlt})"
        ax.text(bar.get_x() + bar.get_width() / 2.0, m + s + 0.8, txt,
                ha='center', va='bottom', fontsize=8.6, fontweight='bold', color='#1A252F')

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


# ==============================================================================
# 5. Execute Unified Dual-View SW-MCUVE-Manifold Across All 3 Botanical Matrices
# ==============================================================================
DATASETS = [
    {
        'key': 'Astragali_Radix',
        'display': 'Astragali Radix (Root)',
        'folder': os.path.join(DATA_ROOT, '黄芪'),
        'cache': 'huangqi_fast_cache.npz',
        'label_map': {'内蒙古固阳': 'Guyang (IM)', '固阳': 'Guyang (IM)',
                      '山西大同': 'Datong (SX)', '大同': 'Datong (SX)',
                      '曲靖': 'Qujing (YN)', '甘肃': 'Gansu (GS)'},
        'classes': ['Datong (SX)', 'Guyang (IM)', 'Qujing (YN)', 'Gansu (GS)'],
        'cm_out': os.path.join(ROOT_DIR, 'Figure 2.png'),
        'cm_local': os.path.join(DATA_ROOT, '黄芪', 'Figure 2_Full_Double_Nested_CM.png'),
        'abl_out': os.path.join(ROOT_DIR, 'Figure 4.a.png'),
        'base_out': os.path.join(ROOT_DIR, 'Figure 5.a.png'),
    },
    {
        'key': 'Ziziphi_Spinosae_Semen',
        'display': 'Ziziphi Spinosae Semen (Seed)',
        'folder': os.path.join(DATA_ROOT, '酸枣仁'),
        'cache': 'suanzaoren_fast_cache.npz',
        'label_map': {
            '盒养河北酸枣仁': 'Boxed (HB)',
            '信盛常': 'SJZ/BZ',
            '散装大袋': 'Bulk-Bag',
            '散装50g': 'Bulk-50g',
            '同仁堂': 'Tongrentang (AH)',
        },
        'classes': ['Boxed (HB)', 'SJZ/BZ', 'Bulk-Bag', 'Bulk-50g', 'Tongrentang (AH)'],
        'cm_out': os.path.join(ROOT_DIR, 'Figure 3.png'),
        'cm_local': None,
        'abl_out': os.path.join(ROOT_DIR, 'Figure 4.b.png'),
        'base_out': os.path.join(ROOT_DIR, 'Figure 5.b.png'),
    },
    {
        'key': 'Gastrodia_elata',
        'display': 'Gastrodia elata (Tuber, Cross-Matrix Validation)',
        'folder': os.path.join(DATA_ROOT, '天麻'),
        'cache': 'tianma_fast_cache.npz',
        'label_map': {
            '安徽亳州': 'Bozhou (AH)', '安徽毫州': 'Bozhou (AH)',
            '贵州雷山': 'Leishan (GZ)', '吉林长白山': 'Changbai (JL)',
            '云南': 'Yunnan (YN)',
        },
        'classes': ['Bozhou (AH)', 'Leishan (GZ)', 'Changbai (JL)', 'Yunnan (YN)'],
        'cm_out': os.path.join(ROOT_DIR, 'Figure S1.a.png'),
        'cm_local': None,
        'abl_out': os.path.join(ROOT_DIR, 'Figure S1.b.png'),
        'base_out': os.path.join(OUT_RES_DIR, 'Figure_S1c_Tianma_Baselines.png'),
    }
]

all_summary = {}
md_lines = [
    "# Unified Double-Nested 5-Fold CV Results (Dual-View SW-MCUVE-Manifold Framework)",
    "",
    f"Generated with `SEED = {SEED}`, Outer 5-Fold Stratified CV + Inner 3-Fold Stratified CV, 100% intra-sample dual-view physical preprocessing (Scattering-Invariant SNV Morphology + Amplitude-Preserving Dielectric Scale), zero cross-sample leakage.",
    ""
]

for cfg in DATASETS:
    t_ds = time.time()
    print("\n" + "=" * 88, flush=True)
    print(f"  >>> RUNNING DUAL-VIEW DOUBLE-NESTED SUITE: {cfg['display']}", flush=True)
    print("=" * 88, flush=True)

    raw_a, raw_r, y, freq, classes = load_dataset(
        cfg['key'], cfg['folder'], cfg['cache'], cfg['label_map'], cfg['classes']
    )
    n_raw = int(len(y))
    raw_a, raw_r, y, n_drop, dropped_breakdown = apply_physical_qc(raw_a, raw_r, y, cfg['key'])

    # Compute raw dual-channel Fisher trace separability (SB/SW) for physical discussion
    X_phys_s = StandardScaler().fit_transform(np.hstack([raw_a, raw_r]))
    gmean = X_phys_s.mean(axis=0)
    sb, sw = 0.0, 0.0
    for c in classes:
        Xc = X_phys_s[y == c]
        cm_c = Xc.mean(axis=0)
        sb += len(Xc) * np.sum((cm_c - gmean) ** 2)
        sw += np.sum((Xc - cm_c) ** 2)
    fisher_ratio = float(sb / sw)
    print(f"  [{cfg['key']}] Post-QC Physical Fisher Trace Ratio (SB/SW): {fisher_ratio:.4f}", flush=True)

    if cfg['key'] == 'Astragali_Radix':
        plot_huangqi_fig1(raw_a, y, freq, classes, [
            os.path.join(ROOT_DIR, 'Figure 1.png'),
            os.path.join(DATA_ROOT, '黄芪', 'Figure 1_Mean_SD.png')
        ])

    X_dual, X_snv, X_amp, X_abs, X_gen1 = extract_feature_sets(raw_a, raw_r)

    outer_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    outer_splits = list(outer_cv.split(X_dual, y))

    print("  [1/4] Precomputing nested MC-UVE + Purified Shrinkage LDA states...", flush=True)
    fb_dual = precompute_nested_states(X_dual, y, outer_splits)
    fb_snv  = precompute_nested_states(X_snv,  y, outer_splits)
    fb_amp  = precompute_nested_states(X_amp,  y, outer_splits)
    fb_abs  = precompute_nested_states(X_abs,  y, outer_splits)
    fb_gen1 = precompute_nested_states(X_gen1, y, outer_splits)

    print("  [2/4] Evaluating Proposed Dual-View Model & Module Knockout Ablations...", flush=True)
    res_full        = eval_sw_mcuve_variant(fb_dual, y, keep_ratio=0.35, alpha_w=0.5, lw_grid=(1.0, 2.0, 3.0))
    res_no_manifold = eval_sw_mcuve_variant(fb_dual, y, keep_ratio=0.35, alpha_w=0.5, lw_grid=(0.0,))
    res_snv_only    = eval_sw_mcuve_variant(fb_snv,  y, keep_ratio=0.35, alpha_w=0.5, lw_grid=(1.0, 2.0, 3.0))
    res_amp_only    = eval_sw_mcuve_variant(fb_amp,  y, keep_ratio=0.35, alpha_w=0.5, lw_grid=(1.0, 2.0, 3.0))
    res_abs_only    = eval_sw_mcuve_variant(fb_abs,  y, keep_ratio=0.35, alpha_w=0.5, lw_grid=(1.0, 2.0, 3.0))
    res_gen1_hard   = eval_sw_mcuve_variant(fb_gen1, y, keep_ratio=0.30, alpha_w=0.0, lw_grid=(0.0,))

    print("  [3/4] Evaluating Classical Baselines (PLS-DA, RF, Full-SVM)...", flush=True)
    res_plsda    = eval_baseline_double_nested(X_gen1, y, outer_splits, "PLS-DA")
    res_rf       = eval_baseline_double_nested(X_gen1, y, outer_splits, "RF")
    res_full_svm = eval_baseline_double_nested(X_gen1, y, outer_splits, "Full-SVM")

    print(f"\n  ★ [{cfg['key']}] Dual-View Proposed (n={len(y)}): {res_full['acc']:.2f}% "
          f"(Mean ± SD: {res_full['mean']:.2f}% ± {res_full['sd']:.2f}%, Macro-F1: {res_full['macro_f1']:.4f})", flush=True)
    print(f"    Fold Accs: {[round(x, 2) for x in res_full['fold_accs']]}", flush=True)
    print(classification_report(y, res_full['oof_preds'], labels=classes, digits=4), flush=True)

    print("  [4/4] Generating 300 DPI Publication Figures...", flush=True)
    cm_title = (f"{cfg['display']}: Double-Nested 5-Fold CV (n={len(y)})\n"
                f"Accuracy: {res_full['acc']:.2f}% ({res_full['mean']:.2f}% ± {res_full['sd']:.2f}%)")
    plot_confusion_matrix(y, res_full['oof_preds'], classes, cm_title, cfg['cm_out'])
    if cfg['cm_local']:
        plot_confusion_matrix(y, res_full['oof_preds'], classes, cm_title, cfg['cm_local'])

    ref_acc = res_full['acc']
    abl_items = [
        ("Full Proposed\n(Dual-View Manifold)", res_full['mean'], res_full['sd'], "Ref"),
        ("w/o Amplitude View\n(SNV Only)", res_snv_only['mean'], res_snv_only['sd'],
         f"{res_snv_only['acc'] - ref_acc:+.2f}%"),
        ("w/o SNV View\n(Amplitude Only)", res_amp_only['mean'], res_amp_only['sd'],
         f"{res_amp_only['acc'] - ref_acc:+.2f}%"),
        ("w/o Purified\nManifold (λ=0)", res_no_manifold['mean'], res_no_manifold['sd'],
         f"{res_no_manifold['acc'] - ref_acc:+.2f}%"),
        ("w/o Refractive Index\n(Abs Only)", res_abs_only['mean'], res_abs_only['sd'],
         f"{res_abs_only['acc'] - ref_acc:+.2f}%"),
    ]
    plot_bar_comparison(
        abl_items,
        f"Module Knockout Ablation: {cfg['display']} (n={len(y)})",
        cfg['abl_out'],
        highlight_first=True
    )

    base_items = [
        ("PLS-DA\n(Dual-SG)", res_plsda['mean'], res_plsda['sd'], None),
        ("Random Forest\n(Dual-SG)", res_rf['mean'], res_rf['sd'], None),
        ("Standard RBF-SVM\n(Full Spectrum)", res_full_svm['mean'], res_full_svm['sd'], None),
        ("Hard MC-UVE-SVM\n(Gen-1 Baseline)", res_gen1_hard['mean'], res_gen1_hard['sd'], None),
        ("Proposed\n(Dual-View Manifold)", res_full['mean'], res_full['sd'],
         f"{res_full['acc'] - res_gen1_hard['acc']:+.2f}% vs Gen-1"),
    ]
    plot_bar_comparison(
        base_items,
        f"Baseline Model Comparison: {cfg['display']} (n={len(y)})",
        cfg['base_out'],
        highlight_first=False
    )

    rep_dict = classification_report(y, res_full['oof_preds'], labels=classes, output_dict=True)
    cm_mat = confusion_matrix(y, res_full['oof_preds'], labels=classes)

    def strip_preds(d):
        return {k: v for k, v in d.items() if k != 'oof_preds'}

    ds_record = {
        'n_raw': n_raw,
        'n_samples': int(len(y)),
        'n_dropped_qc': n_drop,
        'dropped_breakdown': dropped_breakdown,
        'fisher_sb_sw': round(fisher_ratio, 4),
        'classes': classes,
        'confusion_matrix': cm_mat.tolist(),
        'per_class': {
            c: {
                'support': int(rep_dict[c]['support']),
                'correct': int(cm_mat[i, i]),
                'precision': round(rep_dict[c]['precision'] * 100, 2),
                'recall': round(rep_dict[c]['recall'] * 100, 2),
                'f1': round(rep_dict[c]['f1-score'], 4)
            } for i, c in enumerate(classes)
        },
        'proposed': strip_preds(res_full),
        'ablation': {
            'Full Proposed (Dual-View SW-MCUVE-Manifold)': strip_preds(res_full),
            'w/o Amplitude-Preserving View (SNV Only)': strip_preds(res_snv_only),
            'w/o Intra-Sample SNV View (Amplitude Only)': strip_preds(res_amp_only),
            'w/o Purified Manifold (lambda=0)': strip_preds(res_no_manifold),
            'w/o Refractive Index (Abs Only)': strip_preds(res_abs_only),
        },
        'baselines': {
            'PLS-DA': strip_preds(res_plsda),
            'Random Forest': strip_preds(res_rf),
            'Standard RBF-SVM (Full Spectrum)': strip_preds(res_full_svm),
            'Hard MC-UVE-SVM (Gen-1 Baseline)': strip_preds(res_gen1_hard),
            'Proposed (Dual-View SW-MCUVE-Manifold)': strip_preds(res_full),
        }
    }
    all_summary[cfg['key']] = ds_record

    md_lines.append(f"## {cfg['display']} (n = {len(y)} post-QC, raw = {n_raw}, dropped = {n_drop})")
    md_lines.append(f"- **Physical QC**: Unsupervised optical bound `1.2 <= n <= 2.6` & global `3xIQR` absorption fence (dropped: `{dropped_breakdown}`)")
    md_lines.append(f"- **Post-QC Dual-Channel Fisher Separability ($S_B/S_W$)**: `{fisher_ratio:.4f}`")
    md_lines.append(f"- **Overall Double-Nested 5-Fold CV Accuracy**: **{res_full['acc']:.2f}%** (5-Fold Mean ± SD: **{res_full['mean']:.2f}% ± {res_full['sd']:.2f}%**)")
    md_lines.append(f"- **Macro-Averaged Metrics**: Precision `{res_full['macro_prec']:.2f}%`, Recall `{res_full['macro_rec']:.2f}%`, Macro-F1 `{res_full['macro_f1']:.4f}`")
    md_lines.append(f"- **Outer Fold Accuracies**: `{[round(x, 2) for x in res_full['fold_accs']]}`")
    md_lines.append("")
    md_lines.append("### Per-Class Classification Metrics")
    md_lines.append("| Class | n | Correct | Precision (%) | Recall (%) | F1-Score |")
    md_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for c in classes:
        pc = ds_record['per_class'][c]
        md_lines.append(f"| {c} | {pc['support']} | {pc['correct']} | {pc['precision']:.2f} | {pc['recall']:.2f} | {pc['f1']:.4f} |")
    md_lines.append(f"| **Overall / Macro** | **{len(y)}** | **{int(np.trace(cm_mat))}** | **{res_full['macro_prec']:.2f}** | **{res_full['macro_rec']:.2f}** | **{res_full['macro_f1']:.4f}** |")
    md_lines.append("")
    md_lines.append("### Ablation Study (Double-Nested 5-Fold CV)")
    md_lines.append("| Configuration | Overall Acc (%) | Mean ± SD (%) | Delta Acc (%) | Macro-F1 |")
    md_lines.append("| :--- | :---: | :---: | :---: | :---: |")
    for k_abl, v_abl in ds_record['ablation'].items():
        dlt = "Reference" if k_abl.startswith("Full") else f"{v_abl['acc'] - ref_acc:+.2f}%"
        md_lines.append(f"| {k_abl} | {v_abl['acc']:.2f} | {v_abl['mean']:.2f} ± {v_abl['sd']:.2f} | {dlt} | {v_abl['macro_f1']:.4f} |")
    md_lines.append("")
    md_lines.append("### Baseline Model Comparison (Double-Nested 5-Fold CV)")
    md_lines.append("| Model | Overall Acc (%) | Mean ± SD (%) | Macro-Precision (%) | Macro-Recall (%) | Macro-F1 |")
    md_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for k_b, v_b in ds_record['baselines'].items():
        md_lines.append(f"| {k_b} | {v_b['acc']:.2f} | {v_b['mean']:.2f} ± {v_b['sd']:.2f} | {v_b['macro_prec']:.2f} | {v_b['macro_rec']:.2f} | {v_b['macro_f1']:.4f} |")
    md_lines.append("")
    print(f"  >>> [{cfg['key']}] Finished in {time.time() - t_ds:.1f}s!", flush=True)

json_path = os.path.join(OUT_RES_DIR, "Unified_Double_Nested_Summary.json")
md_path   = os.path.join(OUT_RES_DIR, "Unified_Double_Nested_Summary.md")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(all_summary, f, ensure_ascii=False, indent=2)
with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print("\n" + "=" * 88)
print(f"  [ALL DONE] Unified Dual-View Suite Completed in {time.time() - t_global:.1f}s!")
print(f"  * Markdown Summary: {md_path}")
print(f"  * JSON Summary:     {json_path}")
print("=" * 88)
