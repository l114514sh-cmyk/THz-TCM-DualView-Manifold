import json
import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.signal import savgol_filter
from sklearn.covariance import LedoitWolf
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut, StratifiedGroupKFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

warnings.filterwarnings("ignore")

SEED = 42
SEEDS = [42, 100, 2026]
N_JOBS = min(12, max(1, (os.cpu_count() or 4) - 4))

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_ROOT = PROJECT_DIR / "01_原始实验数据"
OLD_RES_DIR = PROJECT_DIR / "05_实验结果" / "模型结果"
OUT_V2_DIR = PROJECT_DIR / "05_实验结果" / "CHEMOLAB_V2"
OUT_V2_DIR.mkdir(parents=True, exist_ok=True)

OUT_JSON = OUT_V2_DIR / "CHEMOLAB_V2_Master_Summary.json"
OUT_PLOT_NPZ = OUT_V2_DIR / "CHEMOLAB_V2_Plot_Data.npz"

INHOUSE_SPECS = [
    {
        "key": "Astragali_Radix",
        "display": "Astragali Radix (Root)",
        "cache": DATA_ROOT / "黄芪" / "huangqi_fast_cache.npz",
        "classes": ["Datong (SX)", "Guyang (IM)", "Qujing (YN)", "Gansu (GS)"],
    },
    {
        "key": "Ziziphi_Spinosae_Semen",
        "display": "Ziziphi Spinosae Semen (Seed)",
        "cache": DATA_ROOT / "酸枣仁" / "suanzaoren_fast_cache.npz",
        "classes": ["Boxed (HB)", "SJZ/BZ", "Bulk-Bag", "Bulk-50g", "Tongrentang (AH)"],
    },
    {
        "key": "Gastrodia_elata",
        "display": "Gastrodia elata (Tuber)",
        "cache": DATA_ROOT / "天麻" / "tianma_fast_cache.npz",
        "classes": ["Bozhou (AH)", "Leishan (GZ)", "Changbai (JL)", "Yunnan (YN)"],
    },
]
GINSENG_DIR = DATA_ROOT / "External_Ginseng_Mendeley" / "Dataset"


# ==============================================================================
# 1. Data Loading, Pre-QC Pellet Grouping & Intra-Sample View Constructors
# ==============================================================================
def assign_pellet_groups(y):
    groups = np.empty(len(y), dtype=object)
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        for local_i, g_i in enumerate(idx):
            groups[g_i] = f"{c}__P{local_i // 5:02d}"
    return groups


def unified_physical_qc(raw_a, raw_r, y, groups):
    ma = raw_a.mean(axis=1)
    mr = raw_r.mean(axis=1)
    mask = (mr >= 1.2) & (mr <= 2.6) & (ma <= 55.0)
    return raw_a[mask], raw_r[mask], y[mask], groups[mask], mask


def load_external_ginseng():
    ra_list, rr_list, y_list, g_list = [], [], [], []
    freq_ref = None
    for j in range(1, 7):
        da = pd.read_csv(GINSENG_DIR / f"data_a{j}.csv")
        dn = pd.read_csv(GINSENG_DIR / f"data_n{j}.csv")
        lbl = pd.read_csv(GINSENG_DIR / f"label_{j}.csv", header=None).values.ravel().astype(int)
        freq = da.iloc[:, 0].values.astype(float)
        if freq_ref is None:
            freq_ref = freq
        a_arr = da.iloc[:, 1:].values.T.astype(float)
        n_arr = dn.iloc[:, 1:].values.T.astype(float)
        ra_list.append(a_arr)
        rr_list.append(n_arr)
        y_list.append(lbl)
        g_list.extend([f"G{j}"] * len(lbl))
    ra = np.vstack(ra_list)
    rr = np.vstack(rr_list)
    y = np.concatenate(y_list)
    groups = np.array(g_list, dtype=object)
    ra_q, rr_q, y_q, g_q, _ = unified_physical_qc(ra, rr, y, groups)
    assert len(y_q) == 42
    return ra_q, rr_q, y_q, g_q, freq_ref


def sample_wise_snv(spec_1d):
    return (spec_1d - np.mean(spec_1d)) / (np.std(spec_1d) + 1e-8)


def extract_views(raw_a_all, raw_r_all):
    n_pts = raw_a_all.shape[1]
    w_long, w_short = (19, 15) if n_pts >= 150 else (7, 5)
    X_dual, X_snv, X_rho, X_strict_tf, X_raw = [], [], [], [], []
    for i in range(len(raw_a_all)):
        ra, rr = raw_a_all[i], raw_r_all[i]

        snv_a = sample_wise_snv(ra)
        snv_r = sample_wise_snv(rr)
        env_a = savgol_filter(snv_a, window_length=w_long, polyorder=2, deriv=0)
        d1_a = sample_wise_snv(savgol_filter(snv_a, window_length=w_long, polyorder=2, deriv=1))
        d2_a = sample_wise_snv(savgol_filter(snv_a, window_length=w_short, polyorder=2, deriv=2))
        env_r = savgol_filter(snv_r, window_length=w_long, polyorder=2, deriv=0)
        d1_r = sample_wise_snv(savgol_filter(snv_r, window_length=w_short, polyorder=2, deriv=1))
        v1 = np.hstack([env_a, d1_a, d2_a, env_r, d1_r])

        raw_env_a = savgol_filter(ra, window_length=w_long, polyorder=2, deriv=0)
        raw_d2_a = savgol_filter(ra, window_length=w_short, polyorder=2, deriv=2)
        raw_env_r = savgol_filter(rr, window_length=w_long, polyorder=2, deriv=0)
        raw_d1_r = savgol_filter(rr, window_length=w_short, polyorder=2, deriv=1)
        v2 = np.hstack([raw_env_a, raw_d2_a, raw_env_r, raw_d1_r])

        rho_tf = ra / np.maximum(rr - 1.0, 0.05)
        rho_d0 = savgol_filter(rho_tf, window_length=w_long, polyorder=2, deriv=0)
        rho_d1 = savgol_filter(rho_tf, window_length=w_long, polyorder=2, deriv=1)
        rho_d2 = savgol_filter(rho_tf, window_length=w_short, polyorder=2, deriv=2)
        v_rho = np.hstack([rho_d0, rho_d1, rho_d2])

        X_dual.append(np.hstack([v1, v2]))
        X_snv.append(v1)
        X_rho.append(v_rho)
        X_strict_tf.append(np.hstack([v1, v_rho]))
        X_raw.append(np.hstack([ra, rr]))

    return {
        "Original_DualView": np.asarray(X_dual),
        "SNV_Only": np.asarray(X_snv),
        "Pure_rhoTF_Only": np.asarray(X_rho),
        "Strictly_TF_Fusion": np.asarray(X_strict_tf),
        "TrackA_Raw": np.asarray(X_raw),
    }


def compute_pellet_vote(y_true, y_pred, groups):
    uniq_p = np.unique(groups)
    p_true, p_pred = [], []
    for p in uniq_p:
        m = groups == p
        p_true.append(y_true[m][0])
        vals, cnts = np.unique(y_pred[m], return_counts=True)
        p_pred.append(vals[np.argmax(cnts)])
    p_true, p_pred = np.asarray(p_true), np.asarray(p_pred)
    corr = int(np.sum(p_true == p_pred))
    tot = int(len(uniq_p))
    return float(corr / tot * 100.0), corr, tot, float(f1_score(p_true, p_pred, average="macro"))


def paired_pellet_bootstrap(y_true, pred_a, pred_b, groups, n_boot=2000, seed=42):
    rng = np.random.RandomState(seed)
    uniq_p = np.unique(groups)
    p_indices = [np.where(groups == p)[0] for p in uniq_p]
    corr_a = (pred_a == y_true).astype(float)
    corr_b = (pred_b == y_true).astype(float)
    obs_diff = (corr_a.mean() - corr_b.mean()) * 100.0

    p_ca = np.array([corr_a[idx].sum() for idx in p_indices])
    p_cb = np.array([corr_b[idx].sum() for idx in p_indices])
    p_n = np.array([len(idx) for idx in p_indices], dtype=float)
    n_p = len(uniq_p)

    diffs = np.empty(n_boot)
    for b in range(n_boot):
        draw = rng.randint(0, n_p, size=n_p)
        tot = p_n[draw].sum()
        diffs[b] = ((p_ca[draw].sum() - p_cb[draw].sum()) / tot) * 100.0

    ci_lo, ci_hi = np.percentile(diffs, [2.5, 97.5])
    p_two = float(2.0 * min(np.mean(diffs <= 0.0), np.mean(diffs >= 0.0)))
    p_two = min(1.0, max(p_two, 1.0 / (n_boot + 1)))
    return {
        "delta_acc": round(float(obs_diff), 2),
        "ci95_lo": round(float(ci_lo), 2),
        "ci95_hi": round(float(ci_hi), 2),
        "p_boot": round(p_two, 4),
    }


# ==============================================================================
# 2. Core Selectors (Unsupervised R_j vs Supervised MC-UVE) & Fold Engine
# ==============================================================================
def compute_unsupervised_repeatability(X_tr_s, g_tr):
    n_features = X_tr_s.shape[1]
    ss_within = np.zeros(n_features, dtype=np.float64)
    dof = 0
    for p in np.unique(g_tr):
        m = g_tr == p
        k = int(m.sum())
        if k >= 2:
            xp = X_tr_s[m]
            ss_within += np.sum((xp - xp.mean(axis=0)) ** 2, axis=0)
            dof += (k - 1)
    var_within = ss_within / max(1, dof)
    var_total = np.var(X_tr_s, axis=0) + 1e-8
    return np.clip(1.0 - var_within / var_total, 0.05, 1.0)


def compute_fold_state(X_tr, y_tr, X_te, g_tr=None, selector="unsup_r", n_mc=30, pure_ratio=0.35, seed=42):
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    t_sel0 = time.perf_counter()
    n_samples, n_features = X_tr_s.shape
    if selector == "unsup_r":
        stability = compute_unsupervised_repeatability(X_tr_s, g_tr)
    else:
        y_dummy = pd.get_dummies(y_tr).values[:, :-1].astype(float)
        actual_comp = max(1, y_dummy.shape[1])
        coefs = np.zeros((n_mc, n_features))
        rng = np.random.RandomState(seed)
        sample_size = max(actual_comp + 2, int(n_samples * 0.8))
        for i in range(n_mc):
            sub_idx = rng.choice(n_samples, sample_size, replace=False)
            pls = PLSRegression(n_components=actual_comp, max_iter=50, tol=1e-3)
            pls.fit(X_tr_s[sub_idx], y_dummy[sub_idx])
            c = np.abs(pls.coef_)
            if c.ndim > 1 and c.shape[0] != n_features:
                c = c.T
            coefs[i, :] = np.mean(c, axis=1) if c.ndim > 1 else c
        stability = np.mean(coefs, axis=0) / (np.std(coefs, axis=0) + 1e-8)
    sel_time = time.perf_counter() - t_sel0

    n_pure = min(n_features, max(20, int(n_features * pure_ratio)))
    pure_idx = np.sort(np.argsort(stability)[::-1][:n_pure])
    pure_w = np.sqrt(stability[pure_idx] / (np.max(stability[pure_idx]) + 1e-8))

    lda = LinearDiscriminantAnalysis(solver="eigen", shrinkage="auto")
    Z_tr = lda.fit_transform(X_tr_s[:, pure_idx] * pure_w, y_tr)
    Z_te = lda.transform(X_te_s[:, pure_idx] * pure_w)

    z_scaler = StandardScaler()
    Z_tr_s = z_scaler.fit_transform(Z_tr)
    Z_te_s = z_scaler.transform(Z_te)

    return {
        "scaler": scaler, "X_tr_s": X_tr_s, "X_te_s": X_te_s,
        "stability": stability, "Z_tr_s": Z_tr_s, "Z_te_s": Z_te_s,
        "lda": lda, "z_scaler": z_scaler, "pure_idx": pure_idx, "pure_w": pure_w,
        "sel_time": sel_time,
    }


def build_features(st, keep_ratio=0.35, alpha_w=0.5, latent_w=2.0):
    stab = st["stability"]
    n_keep = min(len(stab), max(20, int(len(stab) * keep_ratio)))
    top_idx = np.sort(np.argsort(stab)[::-1][:n_keep])
    sel_stab = stab[top_idx]
    w = np.power(sel_stab / (np.max(sel_stab) + 1e-8), alpha_w)
    F_tr = st["X_tr_s"][:, top_idx] * w
    F_te = st["X_te_s"][:, top_idx] * w
    if latent_w > 0:
        F_tr = np.hstack([F_tr, st["Z_tr_s"] * latent_w])
        F_te = np.hstack([F_te, st["Z_te_s"] * latent_w])
    return F_tr, F_te


def transform_new_with_state(st, X_new, latent_w=2.0, keep_ratio=0.35, alpha_w=0.5):
    X_new_s = st["scaler"].transform(X_new)
    Z_new_s = st["z_scaler"].transform(st["lda"].transform(X_new_s[:, st["pure_idx"]] * st["pure_w"]))
    stab = st["stability"]
    n_keep = min(len(stab), max(20, int(len(stab) * keep_ratio)))
    top_idx = np.sort(np.argsort(stab)[::-1][:n_keep])
    w = np.power(stab[top_idx] / (np.max(stab[top_idx]) + 1e-8), alpha_w)
    F_new = X_new_s[:, top_idx] * w
    if latent_w > 0:
        F_new = np.hstack([F_new, Z_new_s * latent_w])
    return X_new_s, Z_new_s, F_new


def run_nested_proposed(X, y, groups, selector="unsup_r", n_mc=30, seed=42, grouped=True, logo=False):
    if logo:
        outer_splits = list(LeaveOneGroupOut().split(X, y, groups))
    elif grouped:
        outer_splits = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y, groups))
    else:
        outer_splits = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y))

    oof_preds = np.empty_like(y)
    fold_accs, sel_times, stabilities, outer_models = [], [], [], []

    for fold_i, (tr_out, te_out) in enumerate(outer_splits, 1):
        X_tr_out, y_tr_out, g_tr_out = X[tr_out], y[tr_out], groups[tr_out]
        X_te_out, y_te_out = X[te_out], y[te_out]

        if logo:
            inner_splits = list(LeaveOneGroupOut().split(X_tr_out, y_tr_out, g_tr_out))
        elif grouped:
            assert len(set(groups[tr_out]) & set(groups[te_out])) == 0
            inner_splits = list(StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed + fold_i).split(X_tr_out, y_tr_out, g_tr_out))
        else:
            inner_splits = list(StratifiedKFold(n_splits=3, shuffle=True, random_state=seed + fold_i).split(X_tr_out, y_tr_out))

        inner_states = []
        for itr, iva in inner_splits:
            if grouped or logo:
                assert len(set(g_tr_out[itr]) & set(g_tr_out[iva])) == 0
            inner_states.append(
                compute_fold_state(X_tr_out[itr], y_tr_out[itr], X_tr_out[iva], g_tr=g_tr_out[itr],
                                   selector=selector, n_mc=n_mc, seed=seed + fold_i)
            )

        best_acc, best_cfg = -1.0, None
        for lw in [1.0, 2.0, 3.0]:
            for C in [1, 5, 10, 50]:
                for gamma in ["scale", 0.002, 0.005]:
                    in_oof = np.empty_like(y_tr_out)
                    for (itr, iva), st in zip(inner_splits, inner_states):
                        F_itr, F_iva = build_features(st, latent_w=lw)
                        in_oof[iva] = SVC(kernel="rbf", C=C, gamma=gamma, random_state=seed).fit(F_itr, y_tr_out[itr]).predict(F_iva)
                    acc = accuracy_score(y_tr_out, in_oof)
                    if acc > best_acc:
                        best_acc, best_cfg = acc, (lw, C, gamma)

        st_out = compute_fold_state(X_tr_out, y_tr_out, X_te_out, g_tr=g_tr_out, selector=selector, n_mc=n_mc, seed=seed + fold_i)
        sel_times.append(st_out["sel_time"])
        stabilities.append(st_out["stability"])
        F_tr, F_te = build_features(st_out, latent_w=best_cfg[0])
        clf = SVC(kernel="rbf", C=best_cfg[1], gamma=best_cfg[2], random_state=seed).fit(F_tr, y_tr_out)
        preds = clf.predict(F_te)
        oof_preds[te_out] = preds
        fold_accs.append(float(accuracy_score(y_te_out, preds) * 100.0))
        outer_models.append((te_out, best_cfg[0], st_out, clf))

    pellet_acc, p_corr, p_tot, p_f1 = compute_pellet_vote(y, oof_preds, groups)
    return {
        "scan_acc": round(float(accuracy_score(y, oof_preds) * 100.0), 2),
        "fold_mean": round(float(np.mean(fold_accs)), 2),
        "fold_sd": round(float(np.std(fold_accs)), 2),
        "macro_f1": round(float(f1_score(y, oof_preds, average="macro")), 4),
        "pellet_acc": round(pellet_acc, 2),
        "pellet_ratio": f"{p_corr}/{p_tot}",
        "pellet_macro_f1": round(p_f1, 4),
        "avg_sel_sec_per_fold": round(float(np.mean(sel_times)), 5),
        "oof_preds": oof_preds,
        "mean_stability": np.mean(stabilities, axis=0),
        "outer_models": outer_models,
    }


def run_nested_plain_baseline(X, y, groups, model_type, seed=42, logo=False):
    if logo:
        outer_splits = list(LeaveOneGroupOut().split(X, y, groups))
    else:
        outer_splits = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y, groups))

    oof = np.empty_like(y)
    fold_accs = []
    uniq_classes = np.unique(y)
    for fold_i, (tr_out, te_out) in enumerate(outer_splits, 1):
        assert len(set(groups[tr_out]) & set(groups[te_out])) == 0
        X_tr_out, y_tr_out, g_tr_out = X[tr_out], y[tr_out], groups[tr_out]
        X_te_out, y_te_out = X[te_out], y[te_out]
        if logo:
            inner_splits = list(LeaveOneGroupOut().split(X_tr_out, y_tr_out, g_tr_out))
        else:
            inner_splits = list(StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed + fold_i).split(X_tr_out, y_tr_out, g_tr_out))

        scaled_in = []
        for itr, iva in inner_splits:
            sc = StandardScaler()
            scaled_in.append((sc.fit_transform(X_tr_out[itr]), sc.transform(X_tr_out[iva]), itr, iva))
        sc_out = StandardScaler()
        X_tr_s, X_te_s = sc_out.fit_transform(X_tr_out), sc_out.transform(X_te_out)

        if model_type == "PLS-DA":
            best_acc, best_nc = -1.0, 3
            for nc in [3, 5, 8, 12, 16]:
                if nc >= len(y_tr_out) // 2:
                    continue
                in_oof = np.empty_like(y_tr_out)
                for X_itr, X_iva, itr, iva in scaled_in:
                    Yd = pd.get_dummies(y_tr_out[itr]).reindex(columns=uniq_classes, fill_value=0).values.astype(float)
                    pls = PLSRegression(n_components=nc, max_iter=150).fit(X_itr, Yd)
                    in_oof[iva] = uniq_classes[np.argmax(pls.predict(X_iva), axis=1)]
                acc = accuracy_score(y_tr_out, in_oof)
                if acc > best_acc:
                    best_acc, best_nc = acc, nc
            Yd_out = pd.get_dummies(y_tr_out).reindex(columns=uniq_classes, fill_value=0).values.astype(float)
            pls_f = PLSRegression(n_components=best_nc, max_iter=150).fit(X_tr_s, Yd_out)
            preds = uniq_classes[np.argmax(pls_f.predict(X_te_s), axis=1)]
        elif model_type == "RF":
            best_acc, best_cfg = -1.0, (150, None)
            for n_est in [150, 300]:
                for md in [None, 15]:
                    in_oof = np.empty_like(y_tr_out)
                    for X_itr, X_iva, itr, iva in scaled_in:
                        in_oof[iva] = RandomForestClassifier(n_estimators=n_est, max_depth=md, random_state=seed, n_jobs=1).fit(X_itr, y_tr_out[itr]).predict(X_iva)
                    acc = accuracy_score(y_tr_out, in_oof)
                    if acc > best_acc:
                        best_acc, best_cfg = acc, (n_est, md)
            preds = RandomForestClassifier(n_estimators=best_cfg[0], max_depth=best_cfg[1], random_state=seed, n_jobs=1).fit(X_tr_s, y_tr_out).predict(X_te_s)
        elif model_type == "RBF-SVM":
            best_acc, best_cfg = -1.0, (10, "scale")
            for C in [1, 5, 10, 50]:
                for gamma in ["scale", 0.002, 0.005]:
                    in_oof = np.empty_like(y_tr_out)
                    for X_itr, X_iva, itr, iva in scaled_in:
                        in_oof[iva] = SVC(kernel="rbf", C=C, gamma=gamma, random_state=seed).fit(X_itr, y_tr_out[itr]).predict(X_iva)
                    acc = accuracy_score(y_tr_out, in_oof)
                    if acc > best_acc:
                        best_acc, best_cfg = acc, (C, gamma)
            preds = SVC(kernel="rbf", C=best_cfg[0], gamma=best_cfg[1], random_state=seed).fit(X_tr_s, y_tr_out).predict(X_te_s)
        else:
            raise ValueError(model_type)

        oof[te_out] = preds
        fold_accs.append(float(accuracy_score(y_te_out, preds) * 100.0))

    pellet_acc, p_corr, p_tot, p_f1 = compute_pellet_vote(y, oof, groups)
    return {
        "scan_acc": round(float(accuracy_score(y, oof) * 100.0), 2),
        "fold_sd": round(float(np.std(fold_accs)), 2),
        "macro_f1": round(float(f1_score(y, oof, average="macro")), 4),
        "pellet_acc": round(pellet_acc, 2),
        "pellet_ratio": f"{p_corr}/{p_tot}",
        "oof_preds": oof,
    }


# ==============================================================================
# 3. Top-Level Parallel Job Workers (Windows spawn compatible)
# ==============================================================================
def _bench_job(ds_key, model_label, X, y, g, kind, seed, selector="mcuve"):
    if kind == "proposed":
        r = run_nested_proposed(X, y, g, selector=selector, n_mc=30, seed=seed, grouped=True, logo=False)
        r.pop("outer_models", None)
        if seed != 42:
            r.pop("oof_preds", None)
            r.pop("mean_stability", None)
    else:
        r = run_nested_plain_baseline(X, y, g, kind, seed=seed, logo=False)
        if seed != 42:
            r.pop("oof_preds", None)
    return ds_key, model_label, seed, r


def _s2_stress_job(raw_a, raw_r, y, groups, model_name, feat_key, selector, draw):
    uniq_p = np.unique(groups)
    rng = np.random.RandomState(900 + draw)
    s_map = {p: float(rng.uniform(0.85, 1.15)) for p in uniq_p}
    s_vec = np.array([s_map[g] for g in groups])[:, None]
    ra_p = raw_a / s_vec
    rr_p = 1.0 + (raw_r - 1.0) / s_vec
    Xp = extract_views(ra_p, rr_p)[feat_key]
    r_p = run_nested_proposed(Xp, y, groups, selector=selector, n_mc=20, seed=SEED, grouped=True, logo=False)
    return model_name, r_p["scan_acc"]


def _perm_500_job(X, g, uniq_p, pellet_true_y, p_i):
    rng_p = np.random.RandomState(3000 + p_i)
    shuf_y = rng_p.permutation(pellet_true_y)
    p_map = dict(zip(uniq_p, shuf_y))
    y_perm = np.array([p_map[gi] for gi in g])
    perm_seed = 4000 + p_i
    outer_cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=perm_seed)
    oof = np.empty_like(y_perm)
    for fi, (tr, te) in enumerate(outer_cv.split(X, y_perm, g), 1):
        assert len(set(g[tr]) & set(g[te])) == 0
        st = compute_fold_state(X[tr], y_perm[tr], X[te], g_tr=g[tr], selector="unsup_r", seed=perm_seed + fi)
        F_tr, F_te = build_features(st, latent_w=2.0)
        oof[te] = SVC(kernel="rbf", C=10, gamma="scale", random_state=perm_seed).fit(F_tr, y_perm[tr]).predict(F_te)
    return float(accuracy_score(y_perm, oof) * 100.0)


# ==============================================================================
# 4. OOD + Conformal Helpers
# ==============================================================================
def eval_ood_and_conformal(X, y, groups, selector="unsup_r", X_bad=None, logo=False):
    out = {}

    if X_bad is not None and len(X_bad) > 0:
        outer_cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
        sc_id = {k: np.empty(len(y), dtype=float) for k in ["T2", "Q_res", "U_prob", "Q+U_prob", "T2+Q"]}
        sc_bad = {k: [] for k in sc_id}
        for fold_i, (tr_out, te_out) in enumerate(outer_cv.split(X, y, groups), 1):
            st = compute_fold_state(X[tr_out], y[tr_out], X[te_out], g_tr=groups[tr_out], selector=selector, n_mc=30, seed=SEED + fold_i)
            F_tr, F_te = build_features(st, latent_w=2.0)
            clf = SVC(kernel="rbf", C=10, gamma="scale", probability=True, random_state=SEED + fold_i).fit(F_tr, y[tr_out])
            lw_cov = LedoitWolf().fit(st["Z_tr_s"])
            pca = PCA(n_components=0.95, svd_solver="full").fit(st["X_tr_s"])

            q95_t2 = float(np.percentile(lw_cov.mahalanobis(st["Z_tr_s"]), 95)) + 1e-8
            q_tr = np.sum((st["X_tr_s"] - pca.inverse_transform(pca.transform(st["X_tr_s"]))) ** 2, axis=1)
            q95_q = float(np.percentile(q_tr, 95)) + 1e-8

            t2_te = lw_cov.mahalanobis(st["Z_te_s"]) / q95_t2
            q_te = np.sum((st["X_te_s"] - pca.inverse_transform(pca.transform(st["X_te_s"]))) ** 2, axis=1) / q95_q
            u_te = 1.0 - np.max(clf.predict_proba(F_te), axis=1)
            sc_id["T2"][te_out] = t2_te
            sc_id["Q_res"][te_out] = q_te
            sc_id["U_prob"][te_out] = u_te
            sc_id["Q+U_prob"][te_out] = q_te + 2.0 * u_te
            sc_id["T2+Q"][te_out] = t2_te + q_te

            Xb_s, Zb_s, F_bad = transform_new_with_state(st, X_bad, latent_w=2.0)
            t2_b = lw_cov.mahalanobis(Zb_s) / q95_t2
            q_b = np.sum((Xb_s - pca.inverse_transform(pca.transform(Xb_s))) ** 2, axis=1) / q95_q
            u_b = 1.0 - np.max(clf.predict_proba(F_bad), axis=1)
            sc_bad["T2"].append(t2_b)
            sc_bad["Q_res"].append(q_b)
            sc_bad["U_prob"].append(u_b)
            sc_bad["Q+U_prob"].append(q_b + 2.0 * u_b)
            sc_bad["T2+Q"].append(t2_b + q_b)

        out["C1_real_corrupted_auroc"] = {}
        lbl = np.hstack([np.zeros(len(y)), np.ones(len(X_bad))])
        for k in sc_id:
            b_arr = np.mean(sc_bad[k], axis=0)
            out["C1_real_corrupted_auroc"][k] = round(float(roc_auc_score(lbl, np.hstack([sc_id[k], b_arr]))), 4)

    classes = sorted(np.unique(y).tolist())
    if len(classes) >= 3:
        auroc_scan = {k: [] for k in ["T2", "Q_res", "U_prob", "Q+U_prob", "T2+Q+U_prob"]}
        auroc_pel = {k: [] for k in auroc_scan}
        for held in classes:
            km, om = (y != held), (y == held)
            Xk, yk, gk = X[km], y[km], groups[km]
            Xo, go = X[om], groups[om]
            id_s = {k: np.empty(len(yk), dtype=float) for k in auroc_scan}
            ood_f = {k: [] for k in auroc_scan}
            cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
            for fold_i, (tr_k, te_k) in enumerate(cv.split(Xk, yk, gk), 1):
                st = compute_fold_state(Xk[tr_k], yk[tr_k], Xk[te_k], g_tr=gk[tr_k], selector=selector, n_mc=25, seed=SEED + fold_i)
                F_tr, F_te = build_features(st, latent_w=2.0)
                clf = SVC(kernel="rbf", C=10, gamma="scale", probability=True, random_state=SEED + fold_i).fit(F_tr, yk[tr_k])
                lw_cov = LedoitWolf().fit(st["Z_tr_s"])
                pca = PCA(n_components=0.95, svd_solver="full").fit(st["X_tr_s"])

                q95_t2 = float(np.percentile(lw_cov.mahalanobis(st["Z_tr_s"]), 95)) + 1e-8
                q_tr = np.sum((st["X_tr_s"] - pca.inverse_transform(pca.transform(st["X_tr_s"]))) ** 2, axis=1)
                q95_q = float(np.percentile(q_tr, 95)) + 1e-8

                t2_te = lw_cov.mahalanobis(st["Z_te_s"]) / q95_t2
                q_te = np.sum((st["X_te_s"] - pca.inverse_transform(pca.transform(st["X_te_s"]))) ** 2, axis=1) / q95_q
                u_te = 1.0 - np.max(clf.predict_proba(F_te), axis=1)
                id_s["T2"][te_k] = t2_te
                id_s["Q_res"][te_k] = q_te
                id_s["U_prob"][te_k] = u_te
                id_s["Q+U_prob"][te_k] = q_te + 2.0 * u_te
                id_s["T2+Q+U_prob"][te_k] = t2_te + q_te + 2.0 * u_te

                Xo_s, Zo_s, Fo = transform_new_with_state(st, Xo, latent_w=2.0)
                t2_o = lw_cov.mahalanobis(Zo_s) / q95_t2
                q_o = np.sum((Xo_s - pca.inverse_transform(pca.transform(Xo_s))) ** 2, axis=1) / q95_q
                u_o = 1.0 - np.max(clf.predict_proba(Fo), axis=1)
                ood_f["T2"].append(t2_o)
                ood_f["Q_res"].append(q_o)
                ood_f["U_prob"].append(u_o)
                ood_f["Q+U_prob"].append(q_o + 2.0 * u_o)
                ood_f["T2+Q+U_prob"].append(t2_o + q_o + 2.0 * u_o)

            lbl_s = np.hstack([np.zeros(len(yk)), np.ones(len(Xo))])
            uniq_gk, uniq_go = np.unique(gk), np.unique(go)
            lbl_p = np.hstack([np.zeros(len(uniq_gk)), np.ones(len(uniq_go))])
            for k in auroc_scan:
                o_s = np.mean(ood_f[k], axis=0)
                auroc_scan[k].append(float(roc_auc_score(lbl_s, np.hstack([id_s[k], o_s]))))
                p_id = [float(id_s[k][gk == p].mean()) for p in uniq_gk]
                p_ood = [float(o_s[go == p].mean()) for p in uniq_go]
                auroc_pel[k].append(float(roc_auc_score(lbl_p, np.hstack([p_id, p_ood]))))

        out["C2_unseen_origin_scan_auroc"] = {k: round(float(np.mean(v)), 4) for k, v in auroc_scan.items()}
        out["C2_unseen_origin_pellet_auroc"] = {k: round(float(np.mean(v)), 4) for k, v in auroc_pel.items()}

    # Non-Empty Split-Conformal Prediction
    c2i = {c: i for i, c in enumerate(classes)}
    y_idx = np.array([c2i[c] for c in y])
    outer_splits = list(LeaveOneGroupOut().split(X, y_idx, groups)) if logo else list(
        StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED).split(X, y_idx, groups)
    )
    oof_probs = np.zeros((len(y_idx), len(classes)), dtype=float)
    q_scan_fold = {0.10: np.zeros(len(y_idx)), 0.05: np.zeros(len(y_idx))}
    q_pel_fold = {0.10: {}, 0.05: {}}

    for fold_i, (tr_out, te_out) in enumerate(outer_splits, 1):
        assert len(set(groups[tr_out]) & set(groups[te_out])) == 0
        cal_cv = StratifiedGroupKFold(n_splits=3 if logo else 4, shuffle=True, random_state=SEED + fold_i)
        prop_i, cal_i = next(cal_cv.split(X[tr_out], y_idx[tr_out], groups[tr_out]))
        prop_g, cal_g = tr_out[prop_i], tr_out[cal_i]
        assert len(set(groups[prop_g]) & set(groups[cal_g])) == 0

        st = compute_fold_state(X[prop_g], y_idx[prop_g], X[cal_g], g_tr=groups[prop_g], selector=selector, n_mc=25, seed=SEED + fold_i)
        F_prop, F_cal = build_features(st, latent_w=2.0)
        _, _, F_te = transform_new_with_state(st, X[te_out], latent_w=2.0)

        clf = SVC(kernel="rbf", C=10, gamma="scale", probability=True, random_state=SEED + fold_i).fit(F_prop, y_idx[prop_g])
        p_cal = clf.predict_proba(F_cal)
        oof_probs[te_out] = clf.predict_proba(F_te)

        s_cal_scan = 1.0 - p_cal[np.arange(len(cal_g)), y_idx[cal_g]]
        n_c = len(s_cal_scan)
        uniq_cal_p = np.unique(groups[cal_g])
        s_cal_pel = np.asarray([1.0 - p_cal[groups[cal_g] == gp].mean(axis=0)[y_idx[cal_g][groups[cal_g] == gp][0]] for gp in uniq_cal_p])
        n_cp = len(s_cal_pel)
        te_pellets = np.unique(groups[te_out])

        for alpha in [0.10, 0.05]:
            ql_s = min(1.0, np.ceil((n_c + 1) * (1.0 - alpha)) / n_c)
            q_scan_fold[alpha][te_out] = float(np.quantile(s_cal_scan, ql_s, method="higher"))
            ql_p = min(1.0, np.ceil((n_cp + 1) * (1.0 - alpha)) / n_cp)
            qv_p = float(np.quantile(s_cal_pel, ql_p, method="higher"))
            for gp in te_pellets:
                q_pel_fold[alpha][gp] = qv_p

    conformal = {}
    for alpha in [0.10, 0.05]:
        sets_s = (1.0 - oof_probs) <= q_scan_fold[alpha][:, None]
        empty_s = sets_s.sum(axis=1) == 0
        if np.any(empty_s):
            sets_s[empty_s, np.argmax(oof_probs[empty_s], axis=1)] = True
        sizes_s = sets_s.sum(axis=1)
        single_m = sizes_s == 1
        single_acc_s = float(np.mean(np.argmax(oof_probs[single_m], axis=1) == y_idx[single_m]) * 100.0) if single_m.sum() > 0 else 0.0

        if not logo:
            uniq_p = np.unique(groups)
            p_covs, p_sizes, p_sing_ok, p_sing_tot = [], [], 0, 0
            for gp in uniq_p:
                m = groups == gp
                mp = oof_probs[m].mean(axis=0)
                yt = y_idx[m][0]
                cset = (1.0 - mp) <= q_pel_fold[alpha][gp]
                if cset.sum() == 0:
                    cset[int(np.argmax(mp))] = True
                p_covs.append(bool(cset[yt]))
                p_sizes.append(int(cset.sum()))
                if cset.sum() == 1:
                    p_sing_tot += 1
                    if int(np.argmax(mp)) == yt:
                        p_sing_ok += 1
            pel_dict = {
                "pellet_coverage_pct": round(float(np.mean(p_covs) * 100.0), 2),
                "pellet_avg_set_size": round(float(np.mean(p_sizes)), 2),
                "pellet_singleton_rate_pct": round(float(p_sing_tot / len(uniq_p) * 100.0), 2),
                "pellet_singleton_acc_pct": round(float(p_sing_ok / max(1, p_sing_tot) * 100.0), 2),
            }
        else:
            pel_dict = {}

        conformal[f"alpha={alpha:.2f}"] = {
            "sample_coverage_pct": round(float(np.mean(sets_s[np.arange(len(y_idx)), y_idx]) * 100.0), 2),
            "sample_avg_set_size": round(float(np.mean(sizes_s)), 2),
            "sample_singleton_rate_pct": round(float(np.mean(single_m) * 100.0), 2),
            "sample_singleton_acc_pct": round(single_acc_s, 2),
            **pel_dict,
        }
    out["NonEmpty_Split_Conformal"] = conformal
    return out


# ==============================================================================
# 5. Master Pipeline Execution
# ==============================================================================
def main():
    t0 = time.time()
    print("=" * 94, flush=True)
    print(f"  CHEMOLAB V2 MASTER COMPUTATION & AUDIT (n_jobs={N_JOBS}/{os.cpu_count()})", flush=True)
    print("=" * 94, flush=True)

    summary = {"meta": {"seeds": SEEDS, "n_jobs": N_JOBS}, "cohorts": {}}
    plot_npz = {}

    # Load archived DL baselines verbatim
    dl1 = json.loads((OLD_RES_DIR / "Colab_Round1_DL_Baselines.json").read_text(encoding="utf-8"))
    dl2 = json.loads((OLD_RES_DIR / "Colab_Round2A_Transformer.json").read_text(encoding="utf-8"))
    summary["archived_dl_baselines"] = {
        "1D-CNN": dl1["models"]["1D-CNN"],
        "1D-ResNet": dl1["models"]["1D-ResNet"],
        "1D-Transformer": dl2,
        "Dual-View MLP": dl1["models"]["Dual-View MLP"],
    }

    # Load 3 in-house matrices
    inhouse_data = {}
    for spec in INHOUSE_SPECS:
        d = np.load(spec["cache"], allow_pickle=True)
        ra_raw, rr_raw, y_raw, freq = d["raw_a"], d["raw_r"], d["y"], d["freq"]
        g_raw = assign_pellet_groups(y_raw)
        ra_q, rr_q, y_q, g_q, qc_mask = unified_physical_qc(ra_raw, rr_raw, y_raw, g_raw)
        views_q = extract_views(ra_q, rr_q)
        views_bad = extract_views(ra_raw[~qc_mask], rr_raw[~qc_mask]) if int((~qc_mask).sum()) > 0 else None
        inhouse_data[spec["key"]] = {
            "spec": spec, "ra_raw": ra_raw, "rr_raw": rr_raw, "y_raw": y_raw, "g_raw": g_raw,
            "ra_q": ra_q, "rr_q": rr_q, "y_q": y_q, "g_q": g_q, "freq": freq, "qc_mask": qc_mask,
            "views_q": views_q, "views_bad": views_bad,
        }
        summary["cohorts"][spec["key"]] = {
            "display": spec["display"], "raw_scans": int(len(y_raw)), "qc_scans": int(len(y_q)),
            "qc_pellets": int(len(np.unique(g_q))), "dropped": int((~qc_mask).sum()), "classes": spec["classes"],
        }
        plot_npz[f"{spec['key']}__freq"] = freq
        plot_npz[f"{spec['key']}__ra_q"] = ra_q
        plot_npz[f"{spec['key']}__rr_q"] = rr_q
        plot_npz[f"{spec['key']}__y_q"] = y_q

    # 1. Parallel Multi-Seed Benchmarks across all 3 in-house matrices (Track A + Track B + TIRG-THz)
    print("\n[1/4] Running 3-Seed Pellet-Grouped Nested CV Benchmarks (Track A & Track B)...", flush=True)
    model_specs = [
        ("TrackA_Raw_PLSDA", "TrackA_Raw", "PLS-DA", "mcuve"),
        ("TrackA_Raw_RF", "TrackA_Raw", "RF", "mcuve"),
        ("TrackA_Raw_SVM", "TrackA_Raw", "RBF-SVM", "mcuve"),
        ("TrackB_DualView_PLSDA", "Original_DualView", "PLS-DA", "mcuve"),
        ("TrackB_DualView_RF", "Original_DualView", "RF", "mcuve"),
        ("TrackB_StrictTF_PLSDA", "Strictly_TF_Fusion", "PLS-DA", "mcuve"),
        ("TrackB_StrictTF_RF", "Strictly_TF_Fusion", "RF", "mcuve"),
        ("Original_DualView_MCUVE", "Original_DualView", "proposed", "mcuve"),
        ("TIRG_StrictTF_Sup_MCUVE", "Strictly_TF_Fusion", "proposed", "mcuve"),
        ("TIRG_StrictTF_Unsup_R", "Strictly_TF_Fusion", "proposed", "unsup_r"),
    ]
    jobs = []
    for ds_key, idat in inhouse_data.items():
        for m_lbl, f_key, kind, sel in model_specs:
            for sd in SEEDS:
                jobs.append((ds_key, m_lbl, idat["views_q"][f_key], idat["y_q"], idat["g_q"], kind, sd, sel))

    raw_b = Parallel(n_jobs=N_JOBS, prefer="processes")(delayed(_bench_job)(*j) for j in jobs)
    bench_map = {}
    for ds_key, m_lbl, sd, r in raw_b:
        bench_map.setdefault(ds_key, {}).setdefault(m_lbl, {})[str(sd)] = r

    benchmarks_summary = {}
    oof_seed42 = {}
    for ds_key, idat in inhouse_data.items():
        benchmarks_summary[ds_key] = {}
        oof_seed42[ds_key] = {}
        print(f"  [{ds_key}]", flush=True)
        for m_lbl, _, kind, _ in model_specs:
            per_s = bench_map[ds_key][m_lbl]
            r42 = per_s["42"]
            oof_seed42[ds_key][m_lbl] = r42.pop("oof_preds")
            if "mean_stability" in r42:
                st42 = r42.pop("mean_stability")
                if m_lbl in ("TIRG_StrictTF_Unsup_R", "TIRG_StrictTF_Sup_MCUVE"):
                    plot_npz[f"{ds_key}__{m_lbl}__stab"] = st42

            scans = [per_s[str(s)]["scan_acc"] for s in SEEDS]
            pels = [per_s[str(s)]["pellet_acc"] for s in SEEDS]
            f1s = [per_s[str(s)]["macro_f1"] for s in SEEDS]
            sel_t = [per_s[str(s)].get("avg_sel_sec_per_fold", 0.0) for s in SEEDS]

            entry = {
                "seed42": r42,
                "three_seed_scan_mean": round(float(np.mean(scans)), 2),
                "three_seed_scan_sd": round(float(np.std(scans)), 2),
                "three_seed_pellet_mean": round(float(np.mean(pels)), 2),
                "three_seed_pellet_sd": round(float(np.std(pels)), 2),
                "three_seed_f1_mean": round(float(np.mean(f1s)), 4),
            }
            if kind == "proposed":
                entry["avg_sel_sec_per_fold"] = round(float(np.mean(sel_t)), 5)
            benchmarks_summary[ds_key][m_lbl] = entry
            print(f"    {m_lbl:26s}: s42={r42['scan_acc']}% (Pel={r42['pellet_acc']}% {r42['pellet_ratio']}) | "
                  f"3-seed={entry['three_seed_scan_mean']}±{entry['three_seed_scan_sd']}%", flush=True)

        # Save seed=42 OOF predictions for confusion matrices
        plot_npz[f"{ds_key}__tirg_unsup_oof42"] = oof_seed42[ds_key]["TIRG_StrictTF_Unsup_R"]

    # Cross-matrix averages & speedup factors
    cross_avg = {}
    for m_lbl, _, kind, _ in model_specs:
        s42_m = np.mean([benchmarks_summary[k][m_lbl]["seed42"]["scan_acc"] for k in inhouse_data])
        p42_m = np.mean([benchmarks_summary[k][m_lbl]["seed42"]["pellet_acc"] for k in inhouse_data])
        s3_m = np.mean([benchmarks_summary[k][m_lbl]["three_seed_scan_mean"] for k in inhouse_data])
        p3_m = np.mean([benchmarks_summary[k][m_lbl]["three_seed_pellet_mean"] for k in inhouse_data])
        d_avg = {
            "seed42_scan_mean": round(float(s42_m), 2),
            "seed42_pellet_mean": round(float(p42_m), 2),
            "three_seed_scan_mean": round(float(s3_m), 2),
            "three_seed_pellet_mean": round(float(p3_m), 2),
        }
        if kind == "proposed":
            d_avg["avg_sel_sec_per_fold"] = round(float(np.mean([benchmarks_summary[k][m_lbl]["avg_sel_sec_per_fold"] for k in inhouse_data])), 5)
        cross_avg[m_lbl] = d_avg
    cross_avg["unsup_r_speedup_vs_mcuve_on_strict_tf"] = round(
        cross_avg["TIRG_StrictTF_Sup_MCUVE"]["avg_sel_sec_per_fold"] / max(1e-6, cross_avg["TIRG_StrictTF_Unsup_R"]["avg_sel_sec_per_fold"]), 1
    )
    summary["benchmarks"] = {"per_matrix": benchmarks_summary, "cross_matrix_avg": cross_avg}

    # Paired Pellet-Cluster Bootstrap (2,000 resamples) for TIRG_StrictTF_Unsup_R and TIRG_StrictTF_Sup_MCUVE
    boot_out = {}
    comp_targets = [
        "TrackA_Raw_PLSDA", "TrackA_Raw_SVM", "TrackB_DualView_PLSDA",
        "TrackB_StrictTF_PLSDA", "TrackB_DualView_RF", "Original_DualView_MCUVE",
    ]
    for ds_key, idat in inhouse_data.items():
        boot_out[ds_key] = {}
        for cand in ["TIRG_StrictTF_Unsup_R", "TIRG_StrictTF_Sup_MCUVE"]:
            boot_out[ds_key][cand] = {
                base: paired_pellet_bootstrap(idat["y_q"], oof_seed42[ds_key][cand], oof_seed42[ds_key][base], idat["g_q"], n_boot=2000, seed=SEED)
                for base in comp_targets
            }
    summary["paired_cluster_bootstrap"] = boot_out

    # 2. Thickness-Drift Stress Tests (S1 +-10% Test-Only & S2 +-15% All-Pellet)
    print("\n[2/4] Running Thickness-Drift Stress Tests (S1 +-10% & S2 +-15%)...", flush=True)
    stress_models = [
        ("Original_DualView_MCUVE", "Original_DualView", "mcuve"),
        ("SNV_Only_MCUVE", "SNV_Only", "mcuve"),
        ("Pure_rhoTF_MCUVE", "Pure_rhoTF_Only", "mcuve"),
        ("TIRG_StrictTF_Sup_MCUVE", "Strictly_TF_Fusion", "mcuve"),
        ("TIRG_StrictTF_Unsup_R", "Strictly_TF_Fusion", "unsup_r"),
    ]
    stress_summary = {}
    for ds_key, idat in inhouse_data.items():
        ra, rr, y, g = idat["ra_q"], idat["rr_q"], idat["y_q"], idat["g_q"]
        uniq_p = np.unique(g)
        clean_res, s1_res = {}, {}
        for m_name, f_key, sel in stress_models:
            r_clean = run_nested_proposed(idat["views_q"][f_key], y, g, selector=sel, n_mc=30, seed=SEED, grouped=True, logo=False)
            clean_res[m_name] = r_clean["scan_acc"]
            s1_draws = []
            for dr in range(5):
                rng = np.random.RandomState(700 + dr)
                s_map = {p: float(rng.uniform(0.90, 1.10)) for p in uniq_p}
                s_vec = np.array([s_map[gi] for gi in g])[:, None]
                Xp = extract_views(ra / s_vec, 1.0 + (rr - 1.0) / s_vec)[f_key]
                oof_p = np.empty_like(y)
                for te_out, lw, st_out, clf in r_clean["outer_models"]:
                    _, _, F_te = transform_new_with_state(st_out, Xp[te_out], latent_w=lw)
                    oof_p[te_out] = clf.predict(F_te)
                s1_draws.append(float(accuracy_score(y, oof_p) * 100.0))
            s1_res[m_name] = float(np.mean(s1_draws))

        s2_jobs = [(m_name, f_key, sel, dr) for dr in range(3) for m_name, f_key, sel in stress_models]
        s2_raw = Parallel(n_jobs=N_JOBS, prefer="processes")(
            delayed(_s2_stress_job)(ra, rr, y, g, m_n, fk, sl, dr) for m_n, fk, sl, dr in s2_jobs
        )
        s2_draws = {m_n: [] for m_n, _, _ in stress_models}
        for m_n, acc in s2_raw:
            s2_draws[m_n].append(acc)

        stress_summary[ds_key] = {}
        print(f"  [{ds_key}]", flush=True)
        for m_name, _, _ in stress_models:
            c_acc = clean_res[m_name]
            s1_m = s1_res[m_name]
            s2_m = float(np.mean(s2_draws[m_name]))
            stress_summary[ds_key][m_name] = {
                "clean_acc": round(c_acc, 2),
                "S1_test10pct_mean": round(s1_m, 2),
                "S1_drop": round(s1_m - c_acc, 2),
                "S2_all15pct_mean": round(s2_m, 2),
                "S2_drop": round(s2_m - c_acc, 2),
            }
            print(f"    {m_name:26s}: Clean={c_acc:.2f}% | S1={s1_m:.2f}% ({s1_m-c_acc:+.2f}%) | S2={s2_m:.2f}% ({s2_m-c_acc:+.2f}%)", flush=True)
    summary["thickness_stress_test"] = stress_summary

    # 3. 4-Stage Leakage & 500-Permutation Y-Scrambling Audit on TIRG-THz (Unsup R_j)
    print("\n[3/4] Running 4-Stage Leakage & 500-Perm Y-Scrambling Audit on TIRG-THz (Unsup R_j)...", flush=True)
    # Audit 1: Differential Blind-Test Perturbation Probe
    hq = inhouse_data["Astragali_Radix"]
    X_hq = hq["views_q"]["Strictly_TF_Fusion"]
    cv1 = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    tr_idx, te_idx = next(cv1.split(X_hq, hq["y_q"], hq["g_q"]))
    ra_pert = hq["ra_q"].copy(); rr_pert = hq["rr_q"].copy()
    probe_idx = te_idx[0]
    ra_pert[probe_idx] *= 5.0
    rr_pert[probe_idx] += 2.0
    X_hq_pert = extract_views(ra_pert, rr_pert)["Strictly_TF_Fusion"]

    st_orig = compute_fold_state(X_hq[tr_idx], hq["y_q"][tr_idx], X_hq[te_idx], g_tr=hq["g_q"][tr_idx], selector="unsup_r", seed=SEED)
    st_pert = compute_fold_state(X_hq_pert[tr_idx], hq["y_q"][tr_idx], X_hq_pert[te_idx], g_tr=hq["g_q"][tr_idx], selector="unsup_r", seed=SEED)
    F_tr_o, F_te_o = build_features(st_orig, latent_w=2.0)
    F_tr_p, F_te_p = build_features(st_pert, latent_w=2.0)
    pred_o = SVC(kernel="rbf", C=10, gamma="scale", random_state=SEED).fit(F_tr_o, hq["y_q"][tr_idx]).predict(F_te_o[1:])
    pred_p = SVC(kernel="rbf", C=10, gamma="scale", random_state=SEED).fit(F_tr_p, hq["y_q"][tr_idx]).predict(F_te_p[1:])
    diff_x = float(np.max(np.abs(st_orig["X_tr_s"] - st_pert["X_tr_s"])))
    diff_r = float(np.max(np.abs(st_orig["stability"] - st_pert["stability"])))
    diff_z = float(np.max(np.abs(st_orig["Z_tr_s"] - st_pert["Z_tr_s"])))
    flips = int(np.sum(pred_o != pred_p))
    assert diff_x == 0.0 and diff_r == 0.0 and diff_z == 0.0 and flips == 0
    print(f"  [Audit 1 Differential Probe] X_tr={diff_x:.1e}, R_j={diff_r:.1e}, Z_tr={diff_z:.1e}, flips={flips}/{len(pred_o)} -> PASS", flush=True)

    # Audit 2 & 3 & 4 per matrix
    audit_raw_vs_qc, audit_grouped_vs_random, audit_perm500 = {}, {}, {}
    for ds_key, idat in inhouse_data.items():
        X_raw_unclean = extract_views(idat["ra_raw"], idat["rr_raw"])["Strictly_TF_Fusion"]
        r_unclean = run_nested_proposed(X_raw_unclean, idat["y_raw"], idat["g_raw"], selector="unsup_r", seed=SEED, grouped=True)
        r_qc = benchmarks_summary[ds_key]["TIRG_StrictTF_Unsup_R"]["seed42"]
        audit_raw_vs_qc[ds_key] = {
            "raw_n": int(len(idat["y_raw"])), "raw_scan_acc": r_unclean["scan_acc"], "raw_pellet_acc": r_unclean["pellet_acc"],
            "qc_n": int(len(idat["y_q"])), "qc_scan_acc": r_qc["scan_acc"], "qc_pellet_acc": r_qc["pellet_acc"],
        }

        X_q = idat["views_q"]["Strictly_TF_Fusion"]
        r_rand = run_nested_proposed(X_q, idat["y_q"], idat["g_q"], selector="unsup_r", seed=SEED, grouped=False)
        audit_grouped_vs_random[ds_key] = {
            "pellet_grouped_scan_acc": r_qc["scan_acc"],
            "ungrouped_random_scan_acc": r_rand["scan_acc"],
            "optimism_gap_pct": round(r_rand["scan_acc"] - r_qc["scan_acc"], 2),
        }

        # 500-Perm Pellet-Level Y-Scrambling
        uniq_p = np.unique(idat["g_q"])
        p_true_y = np.array([idat["y_q"][idat["g_q"] == p][0] for p in uniq_p])
        perm_accs = np.array(
            Parallel(n_jobs=N_JOBS, prefer="processes")(
                delayed(_perm_500_job)(X_q, idat["g_q"], uniq_p, p_true_y, pi) for pi in range(500)
            )
        )
        n_ge = int(np.sum(perm_accs >= r_qc["scan_acc"]))
        p_emp = float((1 + n_ge) / 501.0)
        audit_perm500[ds_key] = {
            "n_perm": 500, "obs_acc": r_qc["scan_acc"],
            "chance_pct": round(100.0 / len(idat["spec"]["classes"]), 2),
            "null_mean": round(float(perm_accs.mean()), 2), "null_sd": round(float(perm_accs.std()), 2),
            "null_min": round(float(perm_accs.min()), 2), "null_max": round(float(perm_accs.max()), 2),
            "n_ge_obs": n_ge, "empirical_p": round(p_emp, 4),
        }
        plot_npz[f"{ds_key}__perm500"] = perm_accs
        print(f"  [{ds_key}] Raw={r_unclean['scan_acc']}% vs QC={r_qc['scan_acc']}% | Rand={r_rand['scan_acc']}% (gap +{audit_grouped_vs_random[ds_key]['optimism_gap_pct']}%) | "
              f"500-Perm Null={perm_accs.mean():.2f}±{perm_accs.std():.2f}% (max={perm_accs.max():.2f}%), p={p_emp:.4f}", flush=True)

    summary["leakage_audit"] = {
        "audit1_differential_probe": {"max_X_diff": diff_x, "max_R_diff": diff_r, "max_Z_diff": diff_z, "pred_flips": flips, "status": "PASS"},
        "audit2_raw_vs_qc": audit_raw_vs_qc,
        "audit3_grouped_vs_random": audit_grouped_vs_random,
        "audit4_y_scrambling_500": audit_perm500,
    }

    # 4. Deployment Reliability (OOD + Non-Empty Conformal) Across All 4 Datasets
    print("\n[4/4] Evaluating Dual-Mechanism OOD & Non-Empty Split-Conformal Across All 4 Datasets...", flush=True)
    rel_out = {}
    for ds_key, idat in inhouse_data.items():
        X_stf = idat["views_q"]["Strictly_TF_Fusion"]
        X_stf_bad = idat["views_bad"]["Strictly_TF_Fusion"] if idat["views_bad"] is not None else None
        rel_out[ds_key] = eval_ood_and_conformal(X_stf, idat["y_q"], idat["g_q"], selector="unsup_r", X_bad=X_stf_bad, logo=False)
        print(f"  [{ds_key}] C1_RealBad={rel_out[ds_key].get('C1_real_corrupted_auroc')} | "
              f"C2_Pellet={rel_out[ds_key]['C2_unseen_origin_pellet_auroc']} | "
              f"Conformal(a=0.10)={rel_out[ds_key]['NonEmpty_Split_Conformal']['alpha=0.10']}", flush=True)

    # External NTHU Mendeley Ginseng (42 tablets across 6 groups, Leave-One-Group-Out)
    ra_g, rr_g, y_g, g_g, freq_g = load_external_ginseng()
    views_g = extract_views(ra_g, rr_g)
    g_raw_svm = run_nested_plain_baseline(views_g["TrackA_Raw"], y_g, g_g, "RBF-SVM", seed=SEED, logo=True)
    g_plsda = run_nested_plain_baseline(views_g["Strictly_TF_Fusion"], y_g, g_g, "PLS-DA", seed=SEED, logo=True)
    g_dual = run_nested_proposed(views_g["Original_DualView"], y_g, g_g, selector="mcuve", seed=SEED, logo=True)
    g_tirg = run_nested_proposed(views_g["Strictly_TF_Fusion"], y_g, g_g, selector="mcuve", seed=SEED, logo=True)
    g_conf = eval_ood_and_conformal(views_g["Strictly_TF_Fusion"], y_g, g_g, selector="mcuve", X_bad=None, logo=True)

    for dd in (g_raw_svm, g_plsda, g_dual, g_tirg):
        dd.pop("oof_preds", None); dd.pop("mean_stability", None); dd.pop("outer_models", None)

    summary["cohorts"]["External_Ginseng_Mendeley"] = {
        "doi": "10.17632/hvbp5mdtxx.2", "n_tablets": int(len(y_g)), "n_groups": int(len(np.unique(g_g))),
        "freq_range_thz": [float(freq_g[0]), float(freq_g[-1])], "n_freq_pts": int(len(freq_g)),
    }
    rel_out["External_Ginseng_Mendeley"] = {
        "LOGO_classification": {"TrackA_Raw_SVM": g_raw_svm, "TrackB_StrictTF_PLSDA": g_plsda, "Original_DualView": g_dual, "TIRG_StrictTF_MCUVE": g_tirg},
        "NonEmpty_Split_Conformal": g_conf["NonEmpty_Split_Conformal"],
    }
    print(f"  [External Ginseng LOGO] RawSVM={g_raw_svm['scan_acc']}% | PLSDA={g_plsda['scan_acc']}% | DualView={g_dual['scan_acc']}% | TIRG={g_tirg['scan_acc']}%", flush=True)
    print(f"  [External Ginseng Conformal] a=0.10 -> {g_conf['NonEmpty_Split_Conformal']['alpha=0.10']} | a=0.05 -> {g_conf['NonEmpty_Split_Conformal']['alpha=0.05']}", flush=True)

    summary["deployment_reliability"] = rel_out
    summary["total_elapsed_sec"] = round(time.time() - t0, 2)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    np.savez(OUT_PLOT_NPZ, **plot_npz)

    print("\n" + "=" * 94, flush=True)
    print(f"  [MASTER V2 COMPLETE] JSON={OUT_JSON} | PlotNPZ={OUT_PLOT_NPZ} | Elapsed={summary['total_elapsed_sec']}s", flush=True)
    print("=" * 94, flush=True)


if __name__ == "__main__":
    main()
