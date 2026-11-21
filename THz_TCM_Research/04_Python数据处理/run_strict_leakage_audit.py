import json
import time
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from sklearn.cross_decomposition import PLSRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import accuracy_score, f1_score

warnings.filterwarnings('ignore')

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_ROOT = PROJECT_DIR / "01_原始实验数据"
OUT_RES_DIR = PROJECT_DIR / "05_实验结果" / "模型结果"
OUT_RES_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# 1. Pure Single-Sample Dual-View Feature Extraction (100% Intra-Sample)
# ==============================================================================
def sample_wise_snv(spec_1d):
    return (spec_1d - np.mean(spec_1d)) / (np.std(spec_1d) + 1e-8)


def extract_single_sample_features(ra, rr):
    """Strictly operates on a single 1D spectrum pair (ra, rr). Zero cross-sample access."""
    snv_a = sample_wise_snv(ra)
    snv_r = sample_wise_snv(rr)
    env_a = savgol_filter(snv_a, window_length=19, polyorder=2, deriv=0)
    d1_a  = sample_wise_snv(savgol_filter(snv_a, window_length=19, polyorder=2, deriv=1))
    d2_a  = sample_wise_snv(savgol_filter(snv_a, window_length=15, polyorder=2, deriv=2))
    env_r = savgol_filter(snv_r, window_length=19, polyorder=2, deriv=0)
    d1_r  = sample_wise_snv(savgol_filter(snv_r, window_length=15, polyorder=2, deriv=1))

    raw_env_a = savgol_filter(ra, window_length=19, polyorder=2, deriv=0)
    raw_d2_a  = savgol_filter(ra, window_length=15, polyorder=2, deriv=2)
    raw_env_r = savgol_filter(rr, window_length=19, polyorder=2, deriv=0)
    raw_d1_r  = savgol_filter(rr, window_length=15, polyorder=2, deriv=1)

    return np.hstack([
        env_a, d1_a, d2_a, env_r, d1_r,
        raw_env_a, raw_d2_a, raw_env_r, raw_d1_r
    ])


def extract_batch_features(raw_a_all, raw_r_all):
    return np.array([extract_single_sample_features(raw_a_all[i], raw_r_all[i]) for i in range(len(raw_a_all))])


def assign_pellet_groups(y):
    """Assign deterministic 5-scan contiguous pellet IDs BEFORE QC."""
    groups = np.empty(len(y), dtype=object)
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        for local_i, g_i in enumerate(idx):
            groups[g_i] = f"{c}__P{local_i // 5:02d}"
    return groups


def unified_physical_qc(raw_a, raw_r, y, groups):
    """
    Identical single-spectrum physical QC used in run_unified_double_nested_all.py:
    1.2 <= mean(n) <= 2.6 and mean(alpha) <= 55.0 cm^-1.
    """
    ma = raw_a.mean(axis=1)
    mr = raw_r.mean(axis=1)
    mask = (mr >= 1.2) & (mr <= 2.6) & (ma <= 55.0)
    return raw_a[mask], raw_r[mask], y[mask], groups[mask]


# ==============================================================================
# 2. Core Locked Training-Fold Estimator (Zero Access to Test Labels/Stats)
# ==============================================================================
def compute_fold_state(X_tr, y_tr, X_te, n_mc=30, pure_ratio=0.35, seed=42):
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    n_samples, n_features = X_tr_s.shape
    y_dummy = pd.get_dummies(y_tr).values[:, :-1].astype(float)
    actual_comp = max(1, y_dummy.shape[1])
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


def run_pellet_grouped_nested_cv(X, y, groups, seed=42):
    outer_cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    oof_preds = np.empty_like(y)
    fold_accs = []

    for fold_i, (tr_out, te_out) in enumerate(outer_cv.split(X, y, groups), 1):
        assert len(set(groups[tr_out]) & set(groups[te_out])) == 0, "PELLET OVERLAP!"
        X_tr_out, y_tr_out, g_tr_out = X[tr_out], y[tr_out], groups[tr_out]
        X_te_out, y_te_out = X[te_out], y[te_out]

        inner_cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed + fold_i)
        inner_splits = list(inner_cv.split(X_tr_out, y_tr_out, g_tr_out))
        inner_states = [
            compute_fold_state(X_tr_out[itr], y_tr_out[itr], X_tr_out[iva], seed=seed + fold_i)
            for itr, iva in inner_splits
        ]

        best_in_acc, best_cfg = -1.0, None
        for lw in [1.0, 2.0, 3.0]:
            for C in [1, 5, 10, 50]:
                for gamma in ['scale', 0.002, 0.005]:
                    in_oof = np.empty_like(y_tr_out)
                    for (itr, iva), st in zip(inner_splits, inner_states):
                        F_itr, F_iva = build_features(*st, keep_ratio=0.35, alpha_w=0.5, latent_w=lw)
                        clf = SVC(kernel='rbf', C=C, gamma=gamma, random_state=seed).fit(F_itr, y_tr_out[itr])
                        in_oof[iva] = clf.predict(F_iva)
                    acc = accuracy_score(y_tr_out, in_oof)
                    if acc > best_in_acc:
                        best_in_acc = acc
                        best_cfg = (lw, C, gamma)

        out_state = compute_fold_state(X_tr_out, y_tr_out, X_te_out, seed=seed + fold_i)
        F_tr_out, F_te_out = build_features(*out_state, keep_ratio=0.35, alpha_w=0.5, latent_w=best_cfg[0])
        clf_final = SVC(kernel='rbf', C=best_cfg[1], gamma=best_cfg[2], random_state=seed).fit(F_tr_out, y_tr_out)
        preds = clf_final.predict(F_te_out)
        oof_preds[te_out] = preds
        fold_accs.append(accuracy_score(y_te_out, preds) * 100.0)

    return (
        float(accuracy_score(y, oof_preds) * 100.0),
        float(np.mean(fold_accs)),
        float(np.std(fold_accs)),
        float(f1_score(y, oof_preds, average='macro')),
    )


def run_single_permutation_eval(X, y_perm, groups, perm_seed):
    """
    Pellet-grouped 5-fold CV under a pellet-level label permutation,
    re-fitting StandardScaler, MC-UVE, Shrinkage-LDA, and RBF-SVM strictly inside each outer training fold.
    """
    outer_cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=perm_seed)
    oof = np.empty_like(y_perm)
    for fi, (tr, te) in enumerate(outer_cv.split(X, y_perm, groups), 1):
        st = compute_fold_state(X[tr], y_perm[tr], X[te], n_mc=15, seed=perm_seed + fi)
        F_tr, F_te = build_features(*st, keep_ratio=0.35, alpha_w=0.5, latent_w=2.0)
        clf = SVC(kernel='rbf', C=10, gamma='scale', random_state=perm_seed).fit(F_tr, y_perm[tr])
        oof[te] = clf.predict(F_te)
    return float(accuracy_score(y_perm, oof) * 100.0)


# ==============================================================================
# Execute the Unified Pellet-Grouped Leakage & Permutation Audit Suite
# ==============================================================================
t0 = time.time()
print("=" * 92)
print("  UNIFIED PELLET-GROUPED LEAKAGE & MULTI-PERMUTATION AUDIT SUITE")
print("=" * 92)

DATASETS = [
    ("Astragali Radix (Root)", DATA_ROOT / "黄芪" / "huangqi_fast_cache.npz", 4),
    ("Ziziphi Spinosae (Seed)", DATA_ROOT / "酸枣仁" / "suanzaoren_fast_cache.npz", 5),
    ("Gastrodia elata (Tuber)", DATA_ROOT / "天麻" / "tianma_fast_cache.npz", 4),
]

audit_report = {
    "qc_rule": "Unified Single-Spectrum Physical Bound: 1.2 <= mean(n) <= 2.6 and mean(alpha) <= 55.0 cm^-1",
    "cv_protocol": "Pellet-Grouped StratifiedGroupKFold (5-scan contiguous pellet blocks)",
}

# ------------------------------------------------------------------------------
# AUDIT 1: Mathematical Differential Perturbation Probe (Code-Level Isolation)
# ------------------------------------------------------------------------------
print("\n[AUDIT 1] Differential Blind-Test Perturbation Probe", flush=True)
d_hq = np.load(DATASETS[0][1], allow_pickle=True)
ra_hq, rr_hq, y_hq = d_hq['raw_a'], d_hq['raw_r'], d_hq['y']
g_hq = assign_pellet_groups(y_hq)
ra_hq, rr_hq, y_hq, g_hq = unified_physical_qc(ra_hq, rr_hq, y_hq, g_hq)

ra_pert = ra_hq.copy()
rr_pert = rr_hq.copy()
ra_pert[100] = ra_pert[100] * 500.0 + 10000.0
rr_pert[100] = rr_pert[100] * 500.0 + 10000.0
X_orig = extract_batch_features(ra_hq, rr_hq)
X_pert = extract_batch_features(ra_pert, rr_pert)

non_100 = [i for i in range(len(y_hq)) if i != 100]
max_feat_diff = float(np.max(np.abs(X_orig[non_100] - X_pert[non_100])))

outer_cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
for tr_idx, te_idx in outer_cv.split(X_orig, y_hq, g_hq):
    if 100 in te_idx:
        st_orig = compute_fold_state(X_orig[tr_idx], y_hq[tr_idx], X_orig[te_idx], seed=43)
        st_pert = compute_fold_state(X_pert[tr_idx], y_hq[tr_idx], X_pert[te_idx], seed=43)
        stab_diff = float(np.max(np.abs(st_orig[2] - st_pert[2])))
        tr_z_diff = float(np.max(np.abs(st_orig[3] - st_pert[3])))
        F_tr1, F_te1 = build_features(*st_orig, latent_w=2.0)
        F_tr2, F_te2 = build_features(*st_pert, latent_w=2.0)
        p1 = SVC(kernel='rbf', C=5, gamma='scale', random_state=42).fit(F_tr1, y_hq[tr_idx]).predict(F_te1)
        p2 = SVC(kernel='rbf', C=5, gamma='scale', random_state=42).fit(F_tr2, y_hq[tr_idx]).predict(F_te2)
        other_te = [idx for idx in range(len(te_idx)) if te_idx[idx] != 100]
        pred_mismatch = int(np.sum(p1[other_te] != p2[other_te]))
        break

print(f"  * Max feature deviation (other {len(non_100)} samples): {max_feat_diff:.6e}")
print(f"  * Max MC-UVE stability deviation ||Δs||_∞:             {stab_diff:.6e}")
print(f"  * Max Shrinkage-LDA manifold deviation ||ΔZ_tr||_∞:    {tr_z_diff:.6e}")
print(f"  * Prediction mismatches on remaining held-out scans:   {pred_mismatch}/{len(other_te)}")
assert max_feat_diff == 0.0 and stab_diff == 0.0 and tr_z_diff == 0.0 and pred_mismatch == 0

audit_report["audit_1_differential_probe"] = {
    "max_feat_diff": max_feat_diff,
    "stab_diff": stab_diff,
    "tr_z_diff": tr_z_diff,
    "other_test_pred_mismatch": pred_mismatch,
    "status": "PASS (Exact 0.000000e+00)"
}

# ------------------------------------------------------------------------------
# AUDIT 2: Raw Uncleaned vs Unified Single-Spectrum QC (Pellet-Grouped)
# ------------------------------------------------------------------------------
print("\n[AUDIT 2] Raw Uncleaned vs. Unified Single-Spectrum QC (Pellet-Grouped CV)", flush=True)
audit_report["audit_2_qc_comparison"] = {}

for name, cp, n_cls in DATASETS:
    d = np.load(cp, allow_pickle=True)
    ra, rr, y = d['raw_a'], d['raw_r'], d['y']
    g = assign_pellet_groups(y)

    X_raw = extract_batch_features(ra, rr)
    acc_raw, m_raw, s_raw, f1_raw = run_pellet_grouped_nested_cv(X_raw, y, g, seed=42)

    ra_q, rr_q, y_q, g_q = unified_physical_qc(ra, rr, y, g)
    X_q = extract_batch_features(ra_q, rr_q)
    acc_q, m_q, s_q, f1_q = run_pellet_grouped_nested_cv(X_q, y_q, g_q, seed=42)

    print(f"  [{name}]")
    print(f"    Raw Uncleaned (n={len(y)}):        {acc_raw:.2f}% ({m_raw:.2f}% ± {s_raw:.2f}%, F1={f1_raw:.4f})")
    print(f"    Unified Single-Spec QC (n={len(y_q)}): {acc_q:.2f}% ({m_q:.2f}% ± {s_q:.2f}%, F1={f1_q:.4f})")
    audit_report["audit_2_qc_comparison"][name] = {
        "raw_n": int(len(y)),
        "raw_acc": round(acc_raw, 2),
        "raw_mean_sd": f"{m_raw:.2f}% ± {s_raw:.2f}%",
        "qc_n": int(len(y_q)),
        "qc_pellets": int(len(np.unique(g_q))),
        "qc_acc": round(acc_q, 2),
        "qc_mean_sd": f"{m_q:.2f}% ± {s_q:.2f}%",
        "qc_f1": round(f1_q, 4),
    }

# ------------------------------------------------------------------------------
# AUDIT 3: Multi-Seed Pellet-Grouped Stability (Seeds 42, 100, 2026)
# ------------------------------------------------------------------------------
print("\n[AUDIT 3] Multi-Seed Pellet-Grouped CV Stability (Seeds: 42, 100, 2026)", flush=True)
audit_report["audit_3_multiseed_stability"] = {}

for name, cp, n_cls in DATASETS:
    d = np.load(cp, allow_pickle=True)
    ra, rr, y = d['raw_a'], d['raw_r'], d['y']
    g = assign_pellet_groups(y)
    ra_q, rr_q, y_q, g_q = unified_physical_qc(ra, rr, y, g)
    X_q = extract_batch_features(ra_q, rr_q)

    seed_accs = {}
    for sd in [42, 100, 2026]:
        acc_s, _, _, _ = run_pellet_grouped_nested_cv(X_q, y_q, g_q, seed=sd)
        seed_accs[str(sd)] = round(acc_s, 2)
    vals = list(seed_accs.values())
    print(f"  [{name}] Seeds {seed_accs} -> Mean ± SD: {np.mean(vals):.2f}% ± {np.std(vals):.2f}%", flush=True)
    audit_report["audit_3_multiseed_stability"][name] = {
        "per_seed_acc": seed_accs,
        "mean_acc": round(float(np.mean(vals)), 2),
        "sd_acc": round(float(np.std(vals)), 2),
    }

# ------------------------------------------------------------------------------
# AUDIT 4: Multi-Permutation Pellet-Level Y-Scrambling (N_perm = 30)
# ------------------------------------------------------------------------------
N_PERM = 30
print(f"\n[AUDIT 4] Multi-Permutation Pellet-Level Y-Scrambling (N_perm = {N_PERM})", flush=True)
audit_report["audit_4_y_scrambling"] = {}

for name, cp, n_cls in DATASETS:
    d = np.load(cp, allow_pickle=True)
    ra, rr, y = d['raw_a'], d['raw_r'], d['y']
    g = assign_pellet_groups(y)
    ra_q, rr_q, y_q, g_q = unified_physical_qc(ra, rr, y, g)
    X_q = extract_batch_features(ra_q, rr_q)

    obs_acc = audit_report["audit_2_qc_comparison"][name]["qc_acc"]
    uniq_p = np.unique(g_q)
    pellet_true_y = np.array([y_q[g_q == p][0] for p in uniq_p])

    perm_accs = []
    for p_i in range(N_PERM):
        rng_p = np.random.RandomState(1000 + p_i)
        shuf_pellet_y = rng_p.permutation(pellet_true_y)
        p_map = dict(zip(uniq_p, shuf_pellet_y))
        y_perm = np.array([p_map[gi] for gi in g_q])
        p_acc = run_single_permutation_eval(X_q, y_perm, g_q, perm_seed=2000 + p_i)
        perm_accs.append(p_acc)

    perm_accs = np.array(perm_accs)
    n_ge = int(np.sum(perm_accs >= obs_acc))
    p_emp = float((1 + n_ge) / (N_PERM + 1))
    chance = 100.0 / n_cls
    print(f"  [{name}] Chance={chance:.1f}% | Null ({N_PERM} perms): "
          f"{perm_accs.mean():.2f}% ± {perm_accs.std():.2f}% (range {perm_accs.min():.2f}%–{perm_accs.max():.2f}%) | "
          f"Obs={obs_acc:.2f}%, empirical p = {p_emp:.4f}", flush=True)

    audit_report["audit_4_y_scrambling"][name] = {
        "n_permutations": N_PERM,
        "theoretical_chance_pct": round(chance, 2),
        "observed_acc_pct": obs_acc,
        "null_mean_pct": round(float(perm_accs.mean()), 2),
        "null_sd_pct": round(float(perm_accs.std()), 2),
        "null_min_pct": round(float(perm_accs.min()), 2),
        "null_max_pct": round(float(perm_accs.max()), 2),
        "n_perm_ge_obs": n_ge,
        "empirical_p_value": round(p_emp, 4),
    }

out_json = OUT_RES_DIR / "Strict_Leakage_Audit_Report.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(audit_report, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 92)
print(f"  [AUDIT COMPLETE] Saved to {out_json} in {time.time() - t0:.1f}s")
print("=" * 92)
