import os
import json
import time
import glob
import warnings
from pathlib import Path
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
from sklearn.model_selection import StratifiedKFold, StratifiedGroupKFold
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

# Project-relative paths (zero hardcoded machine-specific paths)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
ROOT_DIR = PROJECT_DIR.parent
DATA_ROOT = PROJECT_DIR / "01_原始实验数据"
OUT_RES_DIR = PROJECT_DIR / "05_实验结果" / "模型结果"
SUB_FIG_DIR = PROJECT_DIR / "06_论文写作" / "Submission_Figures"
OUT_RES_DIR.mkdir(parents=True, exist_ok=True)
SUB_FIG_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# 1. Unified Data Loader with .npz Caching + Contiguous 5-Scan Pellet Grouping
# ==============================================================================
def load_dataset(name, folder, cache_name, label_map, class_order):
    t0 = time.time()
    cache_path = Path(folder) / cache_name
    if cache_path.exists():
        d = np.load(cache_path, allow_pickle=True)
        raw_a, raw_r, y, freq = d['raw_a'], d['raw_r'], d['y'], d['freq']
        print(f"  [{name}] Cache hit ({cache_name}): n={len(y)}, dim={raw_a.shape[1]} ({time.time()-t0:.2f}s)", flush=True)
    else:
        print(f"  [{name}] Parsing Excel files (first run -> creating {cache_name})...", flush=True)
        excel_files = sorted(glob.glob(str(Path(folder) / "*.xlsx")))
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
        freq = freq_valid
        np.savez(cache_path, raw_a=raw_a, raw_r=raw_r, y=y, freq=freq)
        print(f"  [{name}] Loaded & cached: n={len(y)}, dim={raw_a.shape[1]} ({time.time()-t0:.1f}s)", flush=True)

    # Assign pellet IDs BEFORE QC from contiguous 5-scan blocks within each class workbook
    groups = np.empty(len(y), dtype=object)
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        for local_i, g_i in enumerate(idx):
            groups[g_i] = f"{c}__P{local_i // 5:02d}"

    return raw_a, raw_r, y, groups, freq, class_order


def apply_physical_qc(raw_a, raw_r, y, groups, name):
    """
    100% Single-Spectrum Instrument-Level Physical Quality Control (Zero Cross-Sample Stats):
    1) Effective refractive index bound for dry herb-PE pellets: 1.2 <= mean(n) <= 2.6
    2) Single-spectrum transmission absorption bound: mean(alpha) <= 55.0 cm^-1
    Applied identically across all three botanical matrices and all audit scripts.
    """
    ma = raw_a.mean(axis=1)
    mr = raw_r.mean(axis=1)
    mask = (mr >= 1.2) & (mr <= 2.6) & (ma <= 55.0)
    n_drop = int((~mask).sum())
    dropped_breakdown = pd.Series(y[~mask]).value_counts().to_dict() if n_drop > 0 else {}
    n_pellets = int(len(np.unique(groups[mask])))
    print(f"  [{name}] Unified Single-Spectrum QC (1.2<=n<=2.6 & alpha<=55 cm^-1): "
          f"kept {int(mask.sum())}/{len(y)} scans across {n_pellets} pellets "
          f"(dropped {n_drop}: {dropped_breakdown})", flush=True)
    return raw_a[mask], raw_r[mask], y[mask], groups[mask], n_drop, dropped_breakdown


def plot_huangqi_fig1(raw_a, y, freq, classes, out_paths):
    """Generate clean 300 DPI Figure 1 (Mean ± SD Raw Absorption & Discrete SG 2nd Derivative)."""
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

    ax2.set_title('(b) Discrete SG 2nd Derivative Spectra (Mean ± SD)', fontsize=11.5, fontweight='bold', pad=10)
    ax2.set_xlabel('Frequency (THz)', fontsize=10.5)
    ax2.set_ylabel('Discrete 2nd Derivative d²α / dk² (a.u.)', fontsize=10.5)
    ax2.set_xlim(0.22, 1.04)
    ax2.axhline(0, color='gray', ls=':', lw=1)
    ax2.legend(frameon=True, fontsize=9)
    ax2.grid(True, ls='--', alpha=0.4)

    plt.tight_layout()
    for p in out_paths:
        plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close(fig)


# ==============================================================================
# 2. Pure Intra-Sample Dual-View Feature Extraction (Zero Cross-Sample Access)
# ==============================================================================
def sample_wise_snv(spec_1d):
    return (spec_1d - np.mean(spec_1d)) / (np.std(spec_1d) + 1e-8)


def extract_feature_sets(raw_a_all, raw_r_all):
    X_dual_view, X_snv_only, X_amp_only, X_abs_only, X_raw_dual = [], [], [], [], []
    for i in range(len(raw_a_all)):
        ra, rr = raw_a_all[i], raw_r_all[i]

        # View 1: Scatter-Attenuated Morphology (Intra-Sample SNV Multi-Scale, 1790-dim)
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

        X_dual_view.append(np.hstack([
            env_a, d1_a, d2_a, env_r, d1_r,
            raw_env_a, raw_d2_a, raw_env_r, raw_d1_r
        ]))
        X_snv_only.append(np.hstack([env_a, d1_a, d2_a, env_r, d1_r]))
        X_amp_only.append(np.hstack([raw_env_a, raw_d2_a, raw_env_r, raw_d1_r]))
        X_abs_only.append(np.hstack([env_a, d1_a, d2_a, raw_env_a, raw_d2_a]))
        X_raw_dual.append(np.hstack([ra, rr]))

    return (
        np.array(X_dual_view),
        np.array(X_snv_only),
        np.array(X_amp_only),
        np.array(X_abs_only),
        np.array(X_raw_dual),
    )


# ==============================================================================
# 3. Core Locked Fold State & Pellet-Grouped Double-Nested CV Engine
# ==============================================================================
def compute_fold_state(X_tr, y_tr, X_te, n_mc=30, pure_ratio=0.35, seed=42):
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    n_samples, n_features = X_tr_s.shape
    y_dummy = pd.get_dummies(y_tr).values[:, :-1].astype(float)
    actual_comp = y_dummy.shape[1]
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


def precompute_nested_states(X, y, groups, outer_splits, grouped=True):
    fold_bundle = []
    for fold_i, (tr_out, te_out) in enumerate(outer_splits, 1):
        X_tr_out, y_tr_out = X[tr_out], y[tr_out]
        X_te_out, y_te_out = X[te_out], y[te_out]
        g_tr_out = groups[tr_out]

        if grouped:
            assert len(set(groups[tr_out]) & set(groups[te_out])) == 0, "PELLET LEAKAGE IN OUTER SPLIT!"
            inner_cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED + fold_i)
            inner_splits = list(inner_cv.split(X_tr_out, y_tr_out, g_tr_out))
        else:
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


def compute_pellet_vote(y_true, y_pred, groups):
    uniq_p = np.unique(groups)
    p_true, p_pred = [], []
    for p in uniq_p:
        m = (groups == p)
        p_true.append(y_true[m][0])
        vals, cnts = np.unique(y_pred[m], return_counts=True)
        p_pred.append(vals[np.argmax(cnts)])
    p_true, p_pred = np.array(p_true), np.array(p_pred)
    return {
        'pellet_acc': float(accuracy_score(p_true, p_pred) * 100.0),
        'pellet_correct': int(np.sum(p_true == p_pred)),
        'pellet_total': int(len(uniq_p)),
        'pellet_macro_f1': float(f1_score(p_true, p_pred, average='macro')),
    }


def summarize_preds(y_true, y_pred, groups, fold_accs, cfgs):
    pv = compute_pellet_vote(y_true, y_pred, groups)
    return {
        'acc': float(accuracy_score(y_true, y_pred) * 100.0),
        'mean': float(np.mean(fold_accs)),
        'sd': float(np.std(fold_accs)),
        'macro_prec': float(precision_score(y_true, y_pred, average='macro') * 100.0),
        'macro_rec': float(recall_score(y_true, y_pred, average='macro') * 100.0),
        'macro_f1': float(f1_score(y_true, y_pred, average='macro')),
        'pellet_acc': pv['pellet_acc'],
        'pellet_correct': pv['pellet_correct'],
        'pellet_total': pv['pellet_total'],
        'pellet_macro_f1': pv['pellet_macro_f1'],
        'fold_accs': [float(x) for x in fold_accs],
        'cfgs': [str(c) for c in cfgs],
        'oof_preds': y_pred,
    }


def eval_sw_mcuve_variant(fold_bundle, y_all, groups, keep_ratio=0.35, alpha_w=0.5, lw_grid=(1.0, 2.0, 3.0),
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

    return summarize_preds(y_all, oof_preds, groups, fold_accs, chosen_cfgs)


def eval_baseline_double_nested(X, y_all, groups, outer_splits, model_type):
    oof_preds = np.empty_like(y_all)
    fold_accs = []
    chosen_cfgs = []
    uniq_classes = np.unique(y_all)

    for fold_i, (tr_out, te_out) in enumerate(outer_splits, 1):
        X_tr_out, y_tr_out = X[tr_out], y_all[tr_out]
        X_te_out, y_te_out = X[te_out], y_all[te_out]
        g_tr_out = groups[tr_out]

        inner_cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED + fold_i)
        inner_splits = list(inner_cv.split(X_tr_out, y_tr_out, g_tr_out))

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

    return summarize_preds(y_all, oof_preds, groups, fold_accs, chosen_cfgs)


def paired_pellet_bootstrap(y_true, pred_a, pred_b, groups, n_boot=2000, seed=42):
    """
    Paired pellet-cluster bootstrap (resampling independent pellets with replacement)
    comparing Acc(pred_a) - Acc(pred_b) on identical held-out predictions.
    """
    rng = np.random.RandomState(seed)
    uniq_p = np.unique(groups)
    p_indices = [np.where(groups == p)[0] for p in uniq_p]
    corr_a = (pred_a == y_true).astype(float)
    corr_b = (pred_b == y_true).astype(float)
    obs_diff = (corr_a.mean() - corr_b.mean()) * 100.0

    # Precompute per-pellet sum and count for fast cluster bootstrap
    p_ca = np.array([corr_a[idx].sum() for idx in p_indices])
    p_cb = np.array([corr_b[idx].sum() for idx in p_indices])
    p_n  = np.array([len(idx) for idx in p_indices], dtype=float)
    n_p = len(uniq_p)

    diffs = np.empty(n_boot)
    for b in range(n_boot):
        draw = rng.randint(0, n_p, size=n_p)
        tot = p_n[draw].sum()
        diffs[b] = ((p_ca[draw].sum() - p_cb[draw].sum()) / tot) * 100.0

    ci_lo, ci_hi = np.percentile(diffs, [2.5, 97.5])
    # Two-sided bootstrap p-value testing H0: diff == 0
    p_two = float(2.0 * min(np.mean(diffs <= 0.0), np.mean(diffs >= 0.0)))
    p_two = min(1.0, max(p_two, 1.0 / (n_boot + 1)))
    return {
        'delta_acc': round(float(obs_diff), 2),
        'ci95_lo': round(float(ci_lo), 2),
        'ci95_hi': round(float(ci_hi), 2),
        'p_boot': round(p_two, 4),
    }


# ==============================================================================
# 4. Publication-Grade Plotting Helpers (300 DPI, Times New Roman)
# ==============================================================================
def plot_confusion_matrix(y_true, y_pred, class_order, title_str, out_paths):
    fig, ax = plt.subplots(figsize=(6.8, 5.8), dpi=300)
    cm = confusion_matrix(y_true, y_pred, labels=class_order)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_order)
    disp.plot(cmap=plt.cm.Blues, ax=ax, values_format='d', colorbar=True)
    ax.set_title(title_str, fontsize=10.8, pad=12, fontweight='bold')
    ax.set_xlabel("Predicted Label", fontsize=10.5, labelpad=8)
    ax.set_ylabel("True Label", fontsize=10.5, labelpad=8)
    plt.xticks(rotation=20, ha='right', fontsize=9.5)
    plt.yticks(fontsize=9.5)
    plt.tight_layout()
    for p in out_paths:
        plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close(fig)


def plot_bar_comparison(items, title_str, out_paths, highlight_first=True):
    labels = [it[0] for it in items]
    means = [it[1] for it in items]
    sds = [it[2] for it in items]
    deltas = [it[3] for it in items]

    fig, ax = plt.subplots(figsize=(9.6, 5.1), dpi=300)
    x = np.arange(len(labels))
    if highlight_first:
        colors = ['#1B4F72'] + ['#5DADE2', '#7FB3D5', '#A9CCE3', '#BDC3C7'][:len(labels)-1]
    else:
        colors = ['#BDC3C7'] * (len(labels) - 1) + ['#1B4F72']

    bars = ax.bar(x, means, yerr=sds, capsize=4.5, width=0.58,
                  color=colors, edgecolor='#1B2631', linewidth=0.9,
                  error_kw=dict(ecolor='#2C3E50', lw=1.1))

    y_min = max(0, min(means) - max(sds) - 10)
    y_max = min(109.5, max(means) + max(sds) + 9.5)
    ax.set_ylim(y_min, y_max)
    ax.set_ylabel("Pellet-Grouped 5-Fold CV Accuracy (%)", fontsize=10.5, fontweight='bold')
    ax.set_title(title_str, fontsize=11.0, fontweight='bold', pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.8)
    ax.grid(axis='y', linestyle='--', alpha=0.45)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    for bar, m, s, d in zip(bars, means, sds, deltas):
        txt = f"{m:.2f}% ± {s:.2f}%"
        if d:
            txt += f"\n({d})"
        ax.text(bar.get_x() + bar.get_width() / 2.0, m + s + 0.8, txt,
                ha='center', va='bottom', fontsize=8.0, fontweight='bold', color='#1B2631')

    plt.tight_layout()
    for p in out_paths:
        plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close(fig)


def plot_mcuve_dft_alignment(freq, stab_hq, stab_szr, out_paths):
    """
    New Figure: Fold-Averaged MC-UVE Stability Spectrum (Absorption View) vs.
    Tentative B3LYP-D3(BJ)/6-31G(d) Intramolecular Vibrational Benchmarks.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.5, 6.8), dpi=300, sharex=True)
    n_f = len(freq)

    def aggregate_abs_stability(stab_3222):
        # Average normalized stability across the 5 absorption feature blocks:
        # env_a [0:n_f], d1_a [n_f:2n_f], d2_a [2n_f:3n_f], raw_env_a [5n_f:6n_f], raw_d2_a [6n_f:7n_f]
        blocks = [
            stab_3222[0:n_f], stab_3222[n_f:2*n_f], stab_3222[2*n_f:3*n_f],
            stab_3222[5*n_f:6*n_f], stab_3222[6*n_f:7*n_f]
        ]
        s_mean = np.mean(blocks, axis=0)
        return s_mean / (np.max(s_mean) + 1e-8)

    s_hq = aggregate_abs_stability(stab_hq)
    s_szr = aggregate_abs_stability(stab_szr)

    # Panel (a): Astragali Radix + Calycosin DFT modes
    ax1.plot(freq, s_hq, color='#1B4F72', lw=1.6, label='Mean MC-UVE Stability (Astragali Radix, 5-Fold Avg)')
    ax1.fill_between(freq, 0, s_hq, color='#5DADE2', alpha=0.22)
    hq_thresh = np.percentile(s_hq, 65)
    ax1.axhline(hq_thresh, color='#7F8C8D', ls='--', lw=1.0, label='Top 35% Stability Threshold')
    for f_dft, lbl in [(0.552, 'Calycosin\n0.552 THz'), (0.885, 'Calycosin\n0.885 THz')]:
        ax1.axvline(f_dft, color='#C0392B', ls='-.', lw=1.6)
        ax1.text(f_dft + 0.012, 0.88, lbl, color='#C0392B', fontsize=9.0, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='#C0392B', alpha=0.85))
    ax1.set_title('(a) Astragali Radix: MC-UVE Discriminative Stability vs. Tentative Calycosin DFT Benchmarks',
                  fontsize=10.8, fontweight='bold', pad=8)
    ax1.set_ylabel('Normalized Stability', fontsize=10.0)
    ax1.set_ylim(0, 1.08)
    ax1.legend(loc='upper left', fontsize=8.8, frameon=True)
    ax1.grid(True, ls='--', alpha=0.35)

    # Panel (b): Ziziphi Spinosae Semen + Spinosin DFT modes
    ax2.plot(freq, s_szr, color='#1E8449', lw=1.6, label='Mean MC-UVE Stability (Ziziphi Spinosae Semen, 5-Fold Avg)')
    ax2.fill_between(freq, 0, s_szr, color='#52BE80', alpha=0.22)
    szr_thresh = np.percentile(s_szr, 65)
    ax2.axhline(szr_thresh, color='#7F8C8D', ls='--', lw=1.0, label='Top 35% Stability Threshold')
    for f_dft, lbl, y_pos in [
        (0.605, 'Spinosin\n0.605 THz', 0.86),
        (0.886, 'Spinosin\n0.886 THz', 0.86),
        (0.979, 'Spinosin\n0.979 THz', 0.65),
    ]:
        ax2.axvline(f_dft, color='#D35400', ls='-.', lw=1.6)
        ax2.text(f_dft - 0.085 if f_dft > 0.95 else f_dft + 0.010, y_pos, lbl, color='#D35400',
                 fontsize=8.8, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='#D35400', alpha=0.85))
    ax2.set_title('(b) Ziziphi Spinosae Semen: MC-UVE Discriminative Stability vs. Tentative Spinosin DFT Benchmarks',
                  fontsize=10.8, fontweight='bold', pad=8)
    ax2.set_xlabel('Frequency (THz)', fontsize=10.5)
    ax2.set_ylabel('Normalized Stability', fontsize=10.0)
    ax2.set_xlim(0.22, 1.04)
    ax2.set_ylim(0, 1.08)
    ax2.legend(loc='upper left', fontsize=8.8, frameon=True)
    ax2.grid(True, ls='--', alpha=0.35)

    plt.tight_layout()
    for p in out_paths:
        plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close(fig)


# ==============================================================================
# 5. Master Dataset Registry
# ==============================================================================
DATASETS = [
    {
        'key': 'Astragali_Radix',
        'display': 'Astragali Radix (Fibrous Root)',
        'folder': DATA_ROOT / "黄芪",
        'cache': 'huangqi_fast_cache.npz',
        'label_map': {'山西大同': 'Datong (SX)', '固阳': 'Guyang (IM)', '曲靖': 'Qujing (YN)', '甘肃': 'Gansu (GS)'},
        'classes': ['Datong (SX)', 'Guyang (IM)', 'Qujing (YN)', 'Gansu (GS)'],
        'cm_outs': [ROOT_DIR / "Confusion_Matrix_SVM.png", SUB_FIG_DIR / "Figure_3_Confusion_Matrix_Root.png"],
        'abl_outs': [OUT_RES_DIR / "Ablation_Astragali_Radix.png", SUB_FIG_DIR / "Figure_2_Ablation_Root.png"],
        'base_outs': [OUT_RES_DIR / "Baseline_Astragali_Radix.png", SUB_FIG_DIR / "Figure_4_Baseline_Root.png"],
    },
    {
        'key': 'Ziziphi_Spinosae_Semen',
        'display': 'Ziziphi Spinosae Semen (Lipid-Rich Seed)',
        'folder': DATA_ROOT / "酸枣仁",
        'cache': 'suanzaoren_fast_cache.npz',
        'label_map': {
            '盒养河北': 'Boxed (HB)', '信盛常': 'SJZ/BZ', '散装大袋': 'Bulk-Bag',
            '散装50g': 'Bulk-50g', '同仁堂': 'Tongrentang (AH)'
        },
        'classes': ['Boxed (HB)', 'SJZ/BZ', 'Bulk-Bag', 'Bulk-50g', 'Tongrentang (AH)'],
        'cm_outs': [ROOT_DIR / "Suanzaoren_Confusion_Matrix.png", SUB_FIG_DIR / "Figure_5a_Confusion_Matrix_Seed.png"],
        'abl_outs': [OUT_RES_DIR / "Ablation_Ziziphi_Spinosae.png", SUB_FIG_DIR / "Figure_S1a_Ablation_Seed.png"],
        'base_outs': [OUT_RES_DIR / "Baseline_Ziziphi_Spinosae.png", SUB_FIG_DIR / "Figure_S1b_Baseline_Seed.png"],
    },
    {
        'key': 'Gastrodia_elata',
        'display': 'Gastrodia elata (Starchy Tuber)',
        'folder': DATA_ROOT / "天麻",
        'cache': 'tianma_fast_cache.npz',
        'label_map': {'安徽': 'Bozhou (AH)', '贵州': 'Leishan (GZ)', '吉林': 'Changbai (JL)', '云南': 'Yunnan (YN)'},
        'classes': ['Bozhou (AH)', 'Leishan (GZ)', 'Changbai (JL)', 'Yunnan (YN)'],
        'cm_outs': [OUT_RES_DIR / "Tianma_Confusion_Matrix.png", SUB_FIG_DIR / "Figure_5b_Confusion_Matrix_Tuber.png"],
        'abl_outs': [OUT_RES_DIR / "Ablation_Gastrodia_elata.png"],
        'base_outs': [OUT_RES_DIR / "Baseline_Gastrodia_elata.png"],
    }
]


# ==============================================================================
# 6. Execute Unified Pellet-Grouped Evaluation + Fair Input-Controlled Baselines
# ==============================================================================
all_summary = {}
md_lines = [
    "# Unified Pellet-Grouped Double-Nested Cross-Validation Summary",
    "",
    "- **Primary Validation Protocol**: Outer 5-Fold **Pellet-Grouped `StratifiedGroupKFold`** / Inner 3-Fold **Pellet-Grouped `StratifiedGroupKFold`** (each pellet's 5 replicate scans strictly locked in Train or Test; zero same-pellet leakage).",
    "- **Unified Single-Spectrum Physical QC**: `1.2 <= mean(n) <= 2.6` and `mean(alpha) <= 55.0 cm^-1` (applied identically across all three botanical matrices).",
    "- **Fair Input-Controlled Baselines**: Track A (identical 716-dim Raw Dual-Channel `[raw_a, raw_r]`) & Track B (identical 3,222-dim Dual-View `X_dual`).",
    ""
]

fold_mean_stabilities = {}
freq_ref = None

print("=" * 92)
print("  UNIFIED PELLET-GROUPED DOUBLE-NESTED SUITE (FAIR INPUT-CONTROLLED BASELINES + BOOTSTRAP)")
print("=" * 92)

for cfg in DATASETS:
    t_ds = time.time()
    print(f"\n>>> Processing {cfg['display']} ...", flush=True)
    raw_a, raw_r, y_raw, g_raw, freq, classes = load_dataset(
        cfg['key'], cfg['folder'], cfg['cache'], cfg['label_map'], cfg['classes']
    )
    freq_ref = freq
    n_raw = int(len(y_raw))
    raw_a, raw_r, y, groups, n_drop, dropped_breakdown = apply_physical_qc(raw_a, raw_r, y_raw, g_raw, cfg['key'])

    # Post-QC Dual-Channel Fisher Separability Ratio (S_B / S_W)
    X_raw_s = StandardScaler().fit_transform(np.hstack([raw_a, raw_r]))
    mu_all = X_raw_s.mean(axis=0)
    sb, sw = 0.0, 0.0
    for c in classes:
        Xc = X_raw_s[y == c]
        mc = Xc.mean(axis=0)
        sb += len(Xc) * float(np.sum((mc - mu_all) ** 2))
        sw += float(np.sum((Xc - mc) ** 2))
    fisher_ratio = sb / (sw + 1e-12)
    print(f"  [{cfg['key']}] Post-QC Dual-Channel Fisher Separability (S_B/S_W) = {fisher_ratio:.4f}", flush=True)

    if cfg['key'] == 'Astragali_Radix':
        plot_huangqi_fig1(raw_a, y, freq, classes, [
            ROOT_DIR / "Figure_1_THz_Spectra.png",
            SUB_FIG_DIR / "Figure_1_THz_Spectra.png",
        ])

    X_dual, X_snv, X_amp, X_abs, X_raw_dual = extract_feature_sets(raw_a, raw_r)

    # Primary splits: Pellet-Grouped 5-Fold StratifiedGroupKFold
    outer_cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    outer_splits = list(outer_cv.split(X_dual, y, groups))

    print("  [1/5] Precomputing Pellet-Grouped Nested MC-UVE + Purified Shrinkage LDA states...", flush=True)
    fb_dual = precompute_nested_states(X_dual, y, groups, outer_splits, grouped=True)
    fb_snv  = precompute_nested_states(X_snv,  y, groups, outer_splits, grouped=True)
    fb_amp  = precompute_nested_states(X_amp,  y, groups, outer_splits, grouped=True)
    fb_abs  = precompute_nested_states(X_abs,  y, groups, outer_splits, grouped=True)

    # Save fold-averaged MC-UVE stability for DFT alignment figure
    fold_mean_stabilities[cfg['key']] = np.mean([fb['out_state'][2] for fb in fb_dual], axis=0)

    print("  [2/5] Evaluating Proposed Dual-View Model & Module Knockout Ablations (Pellet-Grouped)...", flush=True)
    res_full        = eval_sw_mcuve_variant(fb_dual, y, groups, keep_ratio=0.35, alpha_w=0.5, lw_grid=(1.0, 2.0, 3.0))
    res_no_manifold = eval_sw_mcuve_variant(fb_dual, y, groups, keep_ratio=0.35, alpha_w=0.5, lw_grid=(0.0,))
    res_snv_only    = eval_sw_mcuve_variant(fb_snv,  y, groups, keep_ratio=0.35, alpha_w=0.5, lw_grid=(1.0, 2.0, 3.0))
    res_amp_only    = eval_sw_mcuve_variant(fb_amp,  y, groups, keep_ratio=0.35, alpha_w=0.5, lw_grid=(1.0, 2.0, 3.0))
    res_abs_only    = eval_sw_mcuve_variant(fb_abs,  y, groups, keep_ratio=0.35, alpha_w=0.5, lw_grid=(1.0, 2.0, 3.0))
    res_hard_dual   = eval_sw_mcuve_variant(fb_dual, y, groups, keep_ratio=0.35, alpha_w=0.0, lw_grid=(0.0,))

    print("  [3/5] Evaluating Fair Input-Controlled Baselines (Track A: Raw Dual-Channel; Track B: Same 3,222-dim Dual-View)...", flush=True)
    # Track A: Identical Raw Dual-Channel (716-dim)
    res_raw_plsda = eval_baseline_double_nested(X_raw_dual, y, groups, outer_splits, "PLS-DA")
    res_raw_rf    = eval_baseline_double_nested(X_raw_dual, y, groups, outer_splits, "RF")
    res_raw_svm   = eval_baseline_double_nested(X_raw_dual, y, groups, outer_splits, "Full-SVM")
    # Track B: Identical 3,222-dim Dual-View
    res_dv_plsda  = eval_baseline_double_nested(X_dual, y, groups, outer_splits, "PLS-DA")
    res_dv_rf     = eval_baseline_double_nested(X_dual, y, groups, outer_splits, "RF")
    res_dv_svm    = eval_baseline_double_nested(X_dual, y, groups, outer_splits, "Full-SVM")

    # Reference comparison: Ungrouped scan-level StratifiedKFold (to quantify replicate-scan optimism)
    print("  [4/5] Computing Ungrouped Scan-Level Reference & Paired Pellet-Cluster Bootstrap 95% CIs...", flush=True)
    rand_splits = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X_dual, y))
    fb_rand = precompute_nested_states(X_dual, y, groups, rand_splits, grouped=False)
    res_ungrouped = eval_sw_mcuve_variant(fb_rand, y, groups, keep_ratio=0.35, alpha_w=0.5, lw_grid=(1.0, 2.0, 3.0))

    # Paired pellet-cluster bootstrap (Proposed vs every baseline)
    baseline_map = {
        'PLS-DA (Raw Dual-Channel)': res_raw_plsda,
        'RF (Raw Dual-Channel)': res_raw_rf,
        'RBF-SVM (Raw Dual-Channel)': res_raw_svm,
        'PLS-DA (Dual-View 3222-d)': res_dv_plsda,
        'RF (Dual-View 3222-d)': res_dv_rf,
        'RBF-SVM (Dual-View 3222-d)': res_dv_svm,
        'Hard MC-UVE-SVM (Dual-View 3222-d)': res_hard_dual,
    }
    boot_stats = {}
    for bname, bres in baseline_map.items():
        boot_stats[bname] = paired_pellet_bootstrap(y, res_full['oof_preds'], bres['oof_preds'], groups)

    print(f"\n  ★ [{cfg['key']}] Pellet-Grouped Proposed (n={len(y)}, pellets={res_full['pellet_total']}): "
          f"Scan Acc = {res_full['acc']:.2f}% ({res_full['mean']:.2f}% ± {res_full['sd']:.2f}%), "
          f"Pellet Majority-Vote = {res_full['pellet_acc']:.2f}% ({res_full['pellet_correct']}/{res_full['pellet_total']})", flush=True)
    print(f"    (Ungrouped Scan-Level Ref: {res_ungrouped['acc']:.2f}% -> replicate-scan optimism = {res_ungrouped['acc'] - res_full['acc']:+.2f}%)", flush=True)
    for bname, bres in baseline_map.items():
        bs = boot_stats[bname]
        print(f"    vs {bname:35s}: {bres['acc']:6.2f}% (Pellet {bres['pellet_acc']:6.2f}%) | "
              f"Δ={bs['delta_acc']:+6.2f}% [95% CI: {bs['ci95_lo']:+.2f}, {bs['ci95_hi']:+.2f}], p={bs['p_boot']:.4f}", flush=True)

    print("  [5/5] Generating 300 DPI Publication Figures...", flush=True)
    cm_title = (f"{cfg['display']}: Pellet-Grouped 5-Fold CV (n={len(y)}, {res_full['pellet_total']} pellets)\n"
                f"Scan Acc: {res_full['acc']:.2f}% ({res_full['mean']:.2f}% ± {res_full['sd']:.2f}%) | "
                f"Pellet Vote: {res_full['pellet_acc']:.2f}%")
    plot_confusion_matrix(y, res_full['oof_preds'], classes, cm_title, cfg['cm_outs'])

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
        f"Module Knockout Ablation (Pellet-Grouped CV): {cfg['display']} (n={len(y)})",
        cfg['abl_outs'],
        highlight_first=True
    )

    base_items = [
        ("PLS-DA\n(Raw Dual)", res_raw_plsda['mean'], res_raw_plsda['sd'], None),
        ("RF\n(Raw Dual)", res_raw_rf['mean'], res_raw_rf['sd'], None),
        ("RBF-SVM\n(Raw Dual)", res_raw_svm['mean'], res_raw_svm['sd'], None),
        ("PLS-DA\n(Dual-View)", res_dv_plsda['mean'], res_dv_plsda['sd'], None),
        ("RBF-SVM\n(Dual-View)", res_dv_svm['mean'], res_dv_svm['sd'], None),
        ("Hard MC-UVE\n(Dual-View)", res_hard_dual['mean'], res_hard_dual['sd'], None),
        ("Proposed\n(Dual-View)", res_full['mean'], res_full['sd'],
         f"{res_full['acc'] - res_dv_svm['acc']:+.2f}% vs DV-SVM"),
    ]
    plot_bar_comparison(
        base_items,
        f"Input-Controlled Baseline Comparison (Pellet-Grouped CV): {cfg['display']}",
        cfg['base_outs'],
        highlight_first=False
    )

    rep_dict = classification_report(y, res_full['oof_preds'], labels=classes, output_dict=True)
    cm_mat = confusion_matrix(y, res_full['oof_preds'], labels=classes)

    def strip_preds(d):
        return {k: v for k, v in d.items() if k != 'oof_preds'}

    ds_record = {
        'n_raw': n_raw,
        'n_samples': int(len(y)),
        'n_pellets': int(res_full['pellet_total']),
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
        'proposed_pellet_grouped': strip_preds(res_full),
        'proposed_ungrouped_ref': strip_preds(res_ungrouped),
        'ablation': {
            'Full Proposed (Dual-View SW-MCUVE-Manifold)': strip_preds(res_full),
            'w/o Amplitude-Preserving View (SNV Only)': strip_preds(res_snv_only),
            'w/o Intra-Sample SNV View (Amplitude Only)': strip_preds(res_amp_only),
            'w/o Purified Manifold (lambda=0)': strip_preds(res_no_manifold),
            'w/o Refractive Index (Abs Only)': strip_preds(res_abs_only),
        },
        'baselines_fair': {k: strip_preds(v) for k, v in baseline_map.items()},
        'paired_bootstrap_vs_proposed': boot_stats,
    }
    all_summary[cfg['key']] = ds_record

    md_lines.append(f"## {cfg['display']} (n = {len(y)} post-QC across {res_full['pellet_total']} pellets; raw = {n_raw}, dropped = {n_drop})")
    md_lines.append(f"- **Pellet-Grouped 5-Fold CV Scan Accuracy**: **{res_full['acc']:.2f}%** (`{res_full['mean']:.2f}% ± {res_full['sd']:.2f}%`, Macro-F1 `{res_full['macro_f1']:.4f}`)")
    md_lines.append(f"- **Pellet-Level Majority-Vote Accuracy**: **{res_full['pellet_acc']:.2f}%** (`{res_full['pellet_correct']}/{res_full['pellet_total']}` pellets)")
    md_lines.append(f"- **Ungrouped Scan-Level Reference**: `{res_ungrouped['acc']:.2f}%` (replicate-scan optimism: `{res_ungrouped['acc'] - res_full['acc']:+.2f}%`)")
    md_lines.append("")
    md_lines.append("| Model (Input Representation) | Scan Acc (%) | Mean ± SD (%) | Pellet Vote (%) | Δ vs Proposed [95% CI] | p_boot |")
    md_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for bname, bres in baseline_map.items():
        bs = boot_stats[bname]
        md_lines.append(
            f"| {bname} | {bres['acc']:.2f} | {bres['mean']:.2f} ± {bres['sd']:.2f} | "
            f"{bres['pellet_acc']:.2f} | {bs['delta_acc']:+.2f}% [{bs['ci95_lo']:+.2f}, {bs['ci95_hi']:+.2f}] | {bs['p_boot']:.4f} |"
        )
    md_lines.append(
        f"| **Proposed Dual-View SW-MCUVE-Manifold** | **{res_full['acc']:.2f}** | "
        f"**{res_full['mean']:.2f} ± {res_full['sd']:.2f}** | **{res_full['pellet_acc']:.2f}** | Reference | — |"
    )
    md_lines.append("")
    print(f"  >>> [{cfg['key']}] Finished in {time.time() - t_ds:.1f}s!", flush=True)

# Generate New Figure 7: MC-UVE Stability vs. DFT Frequency Alignment
plot_mcuve_dft_alignment(
    freq_ref,
    fold_mean_stabilities['Astragali_Radix'],
    fold_mean_stabilities['Ziziphi_Spinosae_Semen'],
    [
        OUT_RES_DIR / "Figure_7_MCUVE_DFT_Alignment.png",
        SUB_FIG_DIR / "Figure_7_MCUVE_DFT_Alignment.png",
    ]
)

json_path = OUT_RES_DIR / "Unified_Double_Nested_Summary.json"
md_path   = OUT_RES_DIR / "Unified_Double_Nested_Summary.md"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(all_summary, f, ensure_ascii=False, indent=2)
with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print("\n" + "=" * 92)
print(f"  [ALL DONE] Pellet-Grouped Suite Completed in {time.time() - t_global:.1f}s!")
print(f"  * JSON Summary: {json_path}")
print(f"  * MD Summary:   {md_path}")
print("=" * 92)
