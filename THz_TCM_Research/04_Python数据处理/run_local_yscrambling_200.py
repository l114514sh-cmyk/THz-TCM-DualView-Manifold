import json
import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.signal import savgol_filter
from sklearn.cross_decomposition import PLSRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_ROOT = PROJECT_DIR / "01_原始实验数据"
OUT_RES_DIR = PROJECT_DIR / "05_实验结果" / "模型结果"
OUT_RES_DIR.mkdir(parents=True, exist_ok=True)

N_PERM = 200
N_JOBS = min(12, max(1, (os.cpu_count() or 4) - 4))

DATASETS = [
    ("Astragali Radix (Root)", DATA_ROOT / "黄芪" / "huangqi_fast_cache.npz", 4),
    ("Ziziphi Spinosae Semen (Seed)", DATA_ROOT / "酸枣仁" / "suanzaoren_fast_cache.npz", 5),
    ("Gastrodia elata (Tuber)", DATA_ROOT / "天麻" / "tianma_fast_cache.npz", 4),
]


def sample_wise_snv(spec_1d):
    return (spec_1d - np.mean(spec_1d)) / (np.std(spec_1d) + 1e-8)


def extract_single_sample_features(ra, rr):
    snv_a = sample_wise_snv(ra)
    snv_r = sample_wise_snv(rr)
    env_a = savgol_filter(snv_a, window_length=19, polyorder=2, deriv=0)
    d1_a = sample_wise_snv(savgol_filter(snv_a, window_length=19, polyorder=2, deriv=1))
    d2_a = sample_wise_snv(savgol_filter(snv_a, window_length=15, polyorder=2, deriv=2))
    env_r = savgol_filter(snv_r, window_length=19, polyorder=2, deriv=0)
    d1_r = sample_wise_snv(savgol_filter(snv_r, window_length=15, polyorder=2, deriv=1))

    raw_env_a = savgol_filter(ra, window_length=19, polyorder=2, deriv=0)
    raw_d2_a = savgol_filter(ra, window_length=15, polyorder=2, deriv=2)
    raw_env_r = savgol_filter(rr, window_length=19, polyorder=2, deriv=0)
    raw_d1_r = savgol_filter(rr, window_length=15, polyorder=2, deriv=1)

    return np.hstack([
        env_a, d1_a, d2_a, env_r, d1_r,
        raw_env_a, raw_d2_a, raw_env_r, raw_d1_r,
    ])


def extract_batch_features(raw_a_all, raw_r_all):
    return np.array([extract_single_sample_features(raw_a_all[i], raw_r_all[i]) for i in range(len(raw_a_all))])


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
    return raw_a[mask], raw_r[mask], y[mask], groups[mask]


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

    lda = LinearDiscriminantAnalysis(solver="eigen", shrinkage="auto")
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
    for fold_i, (tr_out, te_out) in enumerate(outer_cv.split(X, y, groups), 1):
        assert len(set(groups[tr_out]) & set(groups[te_out])) == 0
        X_tr_out, y_tr_out, g_tr_out = X[tr_out], y[tr_out], groups[tr_out]
        X_te_out = X[te_out]

        inner_cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed + fold_i)
        inner_splits = list(inner_cv.split(X_tr_out, y_tr_out, g_tr_out))
        inner_states = [
            compute_fold_state(X_tr_out[itr], y_tr_out[itr], X_tr_out[iva], seed=seed + fold_i)
            for itr, iva in inner_splits
        ]

        best_in_acc, best_cfg = -1.0, None
        for lw in [1.0, 2.0, 3.0]:
            for C in [1, 5, 10, 50]:
                for gamma in ["scale", 0.002, 0.005]:
                    in_oof = np.empty_like(y_tr_out)
                    for (itr, iva), st in zip(inner_splits, inner_states):
                        F_itr, F_iva = build_features(*st, keep_ratio=0.35, alpha_w=0.5, latent_w=lw)
                        clf = SVC(kernel="rbf", C=C, gamma=gamma, random_state=seed).fit(F_itr, y_tr_out[itr])
                        in_oof[iva] = clf.predict(F_iva)
                    acc = accuracy_score(y_tr_out, in_oof)
                    if acc > best_in_acc:
                        best_in_acc = acc
                        best_cfg = (lw, C, gamma)

        out_state = compute_fold_state(X_tr_out, y_tr_out, X_te_out, seed=seed + fold_i)
        F_tr_out, F_te_out = build_features(*out_state, keep_ratio=0.35, alpha_w=0.5, latent_w=best_cfg[0])
        clf_final = SVC(kernel="rbf", C=best_cfg[1], gamma=best_cfg[2], random_state=seed).fit(F_tr_out, y_tr_out)
        oof_preds[te_out] = clf_final.predict(F_te_out)
    return float(accuracy_score(y, oof_preds) * 100.0)


def eval_one_perm(X_q, g_q, uniq_p, pellet_true_y, p_i):
    rng_p = np.random.RandomState(1000 + p_i)
    shuf_pellet_y = rng_p.permutation(pellet_true_y)
    p_map = dict(zip(uniq_p, shuf_pellet_y))
    y_perm = np.array([p_map[gi] for gi in g_q])

    perm_seed = 2000 + p_i
    outer_cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=perm_seed)
    oof = np.empty_like(y_perm)
    for fi, (tr, te) in enumerate(outer_cv.split(X_q, y_perm, g_q), 1):
        assert len(set(g_q[tr]) & set(g_q[te])) == 0
        st = compute_fold_state(X_q[tr], y_perm[tr], X_q[te], n_mc=15, seed=perm_seed + fi)
        F_tr, F_te = build_features(*st, keep_ratio=0.35, alpha_w=0.5, latent_w=2.0)
        clf = SVC(kernel="rbf", C=10, gamma="scale", random_state=perm_seed).fit(F_tr, y_perm[tr])
        oof[te] = clf.predict(F_te)
    return float(accuracy_score(y_perm, oof) * 100.0)


def main():
    t0 = time.time()
    import sklearn
    print(f"=== LOCAL 200-PERM PELLET-LEVEL Y-SCRAMBLING | n_jobs={N_JOBS}/{os.cpu_count()} | sklearn={sklearn.__version__} ===", flush=True)

    report = {
        "n_permutations": N_PERM,
        "n_jobs": N_JOBS,
        "cpu_cores": os.cpu_count(),
        "sklearn_version": sklearn.__version__,
        "datasets": {},
    }

    for name, cp, n_cls in DATASETS:
        td = time.time()
        d = np.load(cp, allow_pickle=True)
        ra, rr, y = d["raw_a"], d["raw_r"], d["y"]
        g = assign_pellet_groups(y)
        ra_q, rr_q, y_q, g_q = unified_physical_qc(ra, rr, y, g)
        X_q = extract_batch_features(ra_q, rr_q)

        obs_acc = run_pellet_grouped_nested_cv(X_q, y_q, g_q, seed=42)
        uniq_p = np.unique(g_q)
        pellet_true_y = np.array([y_q[g_q == p][0] for p in uniq_p])

        perm_accs = np.array(
            Parallel(n_jobs=N_JOBS, prefer="processes")(
                delayed(eval_one_perm)(X_q, g_q, uniq_p, pellet_true_y, p_i) for p_i in range(N_PERM)
            )
        )
        n_ge = int(np.sum(perm_accs >= obs_acc))
        p_emp = float((1 + n_ge) / (N_PERM + 1))
        chance = 100.0 / n_cls
        dt = time.time() - td

        print(
            f"  [{name}] QC={len(y_q)} scans / {len(uniq_p)} pellets | Obs={obs_acc:.2f}% | "
            f"Null({N_PERM})={perm_accs.mean():.2f}% ± {perm_accs.std():.2f}% "
            f"(min={perm_accs.min():.2f}%, max={perm_accs.max():.2f}%) | "
            f"n_ge={n_ge}/{N_PERM}, empirical p={p_emp:.4f} ({dt:.1f}s)",
            flush=True,
        )

        report["datasets"][name] = {
            "qc_scans": int(len(y_q)),
            "qc_pellets": int(len(uniq_p)),
            "theoretical_chance_pct": round(chance, 2),
            "observed_acc_pct": round(obs_acc, 2),
            "n_permutations": N_PERM,
            "null_mean_pct": round(float(perm_accs.mean()), 2),
            "null_sd_pct": round(float(perm_accs.std()), 2),
            "null_min_pct": round(float(perm_accs.min()), 2),
            "null_max_pct": round(float(perm_accs.max()), 2),
            "n_perm_ge_obs": n_ge,
            "empirical_p_value": round(p_emp, 4),
            "elapsed_sec": round(dt, 2),
        }

    report["total_elapsed_sec"] = round(time.time() - t0, 2)
    out_json = OUT_RES_DIR / "YScrambling_200Perm_Report.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"=== DONE | Saved to {out_json} | Total Elapsed: {report['total_elapsed_sec']}s ===", flush=True)


if __name__ == "__main__":
    main()
