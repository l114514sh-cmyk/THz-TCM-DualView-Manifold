import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import glob
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import openpyxl
from joblib import Parallel, delayed
from scipy.stats import spearmanr
from sklearn.metrics import accuracy_score

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_ROOT = PROJECT_DIR / "01_原始实验数据"
OUT_V2_DIR = PROJECT_DIR / "05_实验结果" / "CHEMOLAB_V2"
SUMMARY_PATH = OUT_V2_DIR / "CHEMOLAB_V2_Master_Summary.json"
PLOT_NPZ_PATH = OUT_V2_DIR / "CHEMOLAB_V2_Plot_Data.npz"

sys.path.insert(0, str(SCRIPT_DIR))
from run_chemolab_v2_master import (
    INHOUSE_SPECS,
    SEED,
    assign_pellet_groups,
    extract_views,
    run_nested_proposed,
    transform_new_with_state,
    unified_physical_qc,
)

C_CM_THZ = 0.0299792458  # c = 2.99792458e10 cm/s / 1e12 Hz -> cm * THz
D0_CM = 0.15             # nominal 1.5 mm = 0.15 cm

RAW_EXCEL_FOLDERS = {
    "Astragali_Radix": DATA_ROOT / "黄芪",
    "Ziziphi_Spinosae_Semen": DATA_ROOT / "酸枣仁",
    "Gastrodia_elata": DATA_ROOT / "天麻",
}

STRESS_MODELS = [
    ("AmpRet_DualView_MCUVE", "Original_DualView", "mcuve"),
    ("SNV_Only_MCUVE", "SNV_Only", "mcuve"),
    ("Pure_rhoTF_MCUVE", "Pure_rhoTF_Only", "mcuve"),
    ("TIRG_StrictTF_Sup_MCUVE", "Strictly_TF_Fusion", "mcuve"),
    ("TIRG_StrictTF_Unsup_R", "Strictly_TF_Fusion", "unsup_r"),
]


# ==============================================================================
# Non-Circular Physical Optical Simulators (Exact Fresnel & Full Fabry-Perot)
# ==============================================================================
def sim_f1_exact_fresnel(ra, rr, s_vec, d0_cm=D0_CM):
    """
    Scenario F1: Unmeasured micrometer / software thickness mis-entry d_in = s_p * d0
    around true slab optical properties (Eqs. 2-3), retaining exact nonlinear Fresnel
    boundary-reflection mismatch across n_err != n_true.
    """
    n_err = 1.0 + (rr - 1.0) / s_vec
    f_true = 4.0 * rr / ((rr + 1.0) ** 2)
    f_err = 4.0 * np.maximum(n_err, 1.01) / ((np.maximum(n_err, 1.01) + 1.0) ** 2)
    a_err = ra / s_vec - (2.0 / (s_vec * d0_cm)) * np.log(f_true / f_err)
    return a_err, n_err


def sim_f2_full_fp_dr(ra, rr, freq, s_vec, d0_cm=D0_CM, noise_db=-68.0, rng=None):
    """
    Scenario F2: True physical pellet thickness changes d_true = s_p * d0,
    forward-propagating the full complex Fabry-Perot slab transfer function H_FP(w; d_true)
    with complex refractive index n_tilde = n - i*kappa and optional finite dynamic-range
    noise floor, followed by standard planar-slab inversion assuming nominal d0.
    """
    w_over_c = 2.0 * np.pi * freq[None, :] / C_CM_THZ  # rad/cm
    kappa = ra / (2.0 * w_over_c)
    n_tilde = rr - 1j * kappa
    d_true = s_vec * d0_cm

    t_fres = 4.0 * n_tilde / ((n_tilde + 1.0) ** 2)
    r_refl = (n_tilde - 1.0) / (n_tilde + 1.0)
    prop = np.exp(-1j * w_over_c * (n_tilde - 1.0) * d_true)
    fp = 1.0 / (1.0 - (r_refl ** 2) * np.exp(-2j * w_over_c * n_tilde * d_true))
    H_true = t_fres * prop * fp

    if rng is not None and noise_db is not None:
        sigma = 10.0 ** (noise_db / 20.0)
        H_true = H_true + sigma * (rng.randn(*H_true.shape) + 1j * rng.randn(*H_true.shape)) / np.sqrt(2.0)

    # Demodulate around bulk phase delay to unwrap smoothly without 2*pi jumps
    phi_base = w_over_c * (rr - 1.0) * d_true
    H_demod = H_true * np.exp(1j * phi_base)
    delta_phi = phi_base - np.angle(H_demod)

    n_app = 1.0 + delta_phi / (w_over_c * d0_cm)
    rho_app = np.maximum(np.abs(H_true), 1e-12)
    f_app = 4.0 * np.maximum(n_app, 1.01) / ((np.maximum(n_app, 1.01) + 1.0) ** 2)
    a_app = -(2.0 / d0_cm) * np.log(np.maximum(rho_app / f_app, 1e-12))
    return a_app, n_app


# ==============================================================================
# Top-Level Parallel Workers (Windows Spawn Compatible)
# ==============================================================================
def _f1_f2_model_worker(ds_key, ra, rr, freq, y, g, m_name, f_key, sel):
    views_clean = extract_views(ra, rr)
    uniq_p = np.unique(g)
    r_clean = run_nested_proposed(views_clean[f_key], y, g, selector=sel, n_mc=30, seed=SEED, grouped=True, logo=False)

    f1_draws, f2_draws = [], []
    for dr in range(5):
        rng = np.random.RandomState(700 + dr)
        s_map = {p: float(rng.uniform(0.90, 1.10)) for p in uniq_p}
        s_vec = np.array([s_map[gi] for gi in g])[:, None]

        # F1: Exact nonlinear Fresnel entry error (+-10% unseen test pellets)
        a1, n1 = sim_f1_exact_fresnel(ra, rr, s_vec)
        X1 = extract_views(a1, n1)[f_key]
        oof1 = np.empty_like(y)
        for te_out, lw, st_out, clf in r_clean["outer_models"]:
            _, _, F_te = transform_new_with_state(st_out, X1[te_out], latent_w=lw)
            oof1[te_out] = clf.predict(F_te)
        f1_draws.append(float(accuracy_score(y, oof1) * 100.0))

        # F2: Physical thickness change + Fabry-Perot + -68 dB noise floor (+-10% test)
        a2, n2 = sim_f2_full_fp_dr(ra, rr, freq, s_vec, noise_db=-68.0, rng=np.random.RandomState(800 + dr))
        X2 = extract_views(a2, n2)[f_key]
        oof2 = np.empty_like(y)
        for te_out, lw, st_out, clf in r_clean["outer_models"]:
            _, _, F_te = transform_new_with_state(st_out, X2[te_out], latent_w=lw)
            oof2[te_out] = clf.predict(F_te)
        f2_draws.append(float(accuracy_score(y, oof2) * 100.0))

    return ds_key, m_name, r_clean["scan_acc"], float(np.mean(f1_draws)), float(np.mean(f2_draws))


def _f2_s2_retrain_worker(ds_key, ra, rr, freq, y, g, m_name, f_key, sel, draw):
    uniq_p = np.unique(g)
    rng = np.random.RandomState(900 + draw)
    s_map = {p: float(rng.uniform(0.85, 1.15)) for p in uniq_p}
    s_vec = np.array([s_map[gi] for gi in g])[:, None]
    a2, n2 = sim_f2_full_fp_dr(ra, rr, freq, s_vec, noise_db=-68.0, rng=np.random.RandomState(950 + draw))
    Xp = extract_views(a2, n2)[f_key]
    assert np.all(np.isfinite(Xp)), f"Non-finite values in F2-S2 ({ds_key}, {m_name}, draw={draw})"
    r_p = run_nested_proposed(Xp, y, g, selector=sel, n_mc=20, seed=SEED, grouped=True, logo=False)
    return ds_key, m_name, r_p["scan_acc"]


# ==============================================================================
# Real TERA K15 Dynamic Range Extraction & R_j(w) Correlation
# ==============================================================================
def compute_dr_and_correlation(plot_npz):
    freq_q = plot_npz["Astragali_Radix__freq"]
    n_f = len(freq_q)
    corr_out = {}
    dr_arrays = {}
    for ds_key, folder in RAW_EXCEL_FOLDERS.items():
        fpath = sorted(glob.glob(str(folder / "*.xlsx")))[0]
        wb = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
        ws = wb["频域"]
        ws.reset_dimensions()
        rows = list(ws.iter_rows(values_only=True))
        wb.close()

        arr = np.array([[float(x) if x is not None else np.nan for x in r] for r in rows[1:]])
        f_dr, ref_db, samp_db = arr[:, 0], arr[:, 1], arr[:, 2:]
        nf = float(np.nanmean(ref_db[f_dr >= 2.5]))
        dr_samp = np.nanmean(samp_db, axis=1) - nf
        dr_interp = np.interp(freq_q, f_dr, dr_samp)

        stab = plot_npz[f"{ds_key}__TIRG_StrictTF_Unsup_R__stab"]
        r_prof = np.mean([stab[b * n_f:(b + 1) * n_f] for b in [0, 1, 2, 5, 6, 7]], axis=0)
        r_d0 = np.mean([stab[0:n_f], stab[5 * n_f:6 * n_f]], axis=0)

        rho_all, p_all = spearmanr(r_prof, dr_interp)
        rho_d0, p_d0 = spearmanr(r_d0, dr_interp)
        corr_out[ds_key] = {
            "spearman_r_all": round(float(rho_all), 4),
            "p_all": float(f"{p_all:.2e}"),
            "spearman_r_d0": round(float(rho_d0), 4),
            "p_d0": float(f"{p_d0:.2e}"),
            "dr_022_db": round(float(dr_interp[0]), 2),
            "dr_104_db": round(float(dr_interp[-1]), 2),
            "source_workbook": Path(fpath).name,
        }
        dr_arrays[f"{ds_key}__dr_interp"] = dr_interp
        print(
            f"  [DR Corr] {ds_key:23s}: Spearman(R, DR)={rho_all:.4f} (p={p_all:.2e}) | "
            f"DR {dr_interp[0]:.1f} -> {dr_interp[-1]:.1f} dB",
            flush=True,
        )
    return corr_out, dr_arrays


def main():
    t0 = time.time()
    n_jobs = min(10, max(1, (os.cpu_count() or 4) - 4))
    print("=" * 90, flush=True)
    print(f"  CHEMOLAB V2.1 NON-CIRCULAR OPTICAL PHYSICS & DR-CORRELATION ADDENDUM (n_jobs={n_jobs})", flush=True)
    print("=" * 90, flush=True)

    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    old_npz = np.load(PLOT_NPZ_PATH, allow_pickle=True)
    plot_npz = {k: old_npz[k] for k in old_npz.files}

    # Load clean datasets once
    ds_loaded = {}
    curve_shifts = {}
    rep_curves = {}
    for spec in INHOUSE_SPECS:
        d = np.load(spec["cache"], allow_pickle=True)
        ra_raw, rr_raw, y_raw, freq = d["raw_a"], d["raw_r"], d["y"], d["freq"]
        ra, rr, y, g, _ = unified_physical_qc(ra_raw, rr_raw, y_raw, assign_pellet_groups(y_raw))
        ds_loaded[spec["key"]] = (ra, rr, y, g, freq)

        # Curve-level mean relative shift under +10% F1 & F2 perturbations
        s10 = np.full((len(ra), 1), 1.10)
        rho0 = ra / np.maximum(rr - 1.0, 0.05)
        a1, n1 = sim_f1_exact_fresnel(ra, rr, s10)
        a2, n2 = sim_f2_full_fp_dr(ra, rr, freq, s10, noise_db=-68.0, rng=np.random.RandomState(42))
        r1 = a1 / np.maximum(n1 - 1.0, 0.05)
        r2 = a2 / np.maximum(n2 - 1.0, 0.05)
        curve_shifts[spec["key"]] = {
            "raw_alpha_plus10_mean_rel_pct": round(float(np.mean(np.abs(a1 - ra) / (np.abs(ra) + 1e-6)) * 100.0), 2),
            "rho_f1_fresnel_plus10_mean_rel_pct": round(float(np.mean(np.abs(r1 - rho0) / (np.abs(rho0) + 1e-6)) * 100.0), 2),
            "rho_f2_fp_dr_plus10_mean_rel_pct": round(float(np.mean(np.abs(r2 - rho0) / (np.abs(rho0) + 1e-6)) * 100.0), 2),
        }
        print(f"  [Curve Shift +10%] {spec['key']:23s}: {curve_shifts[spec['key']]}", flush=True)

        if spec["key"] == "Astragali_Radix":
            ra0, rr0 = ra[:1], rr[:1]
            for tag, sv in [("090", 0.90), ("110", 1.10)]:
                s_one = np.array([[sv]])
                fa1, fn1 = sim_f1_exact_fresnel(ra0, rr0, s_one)
                fa2, fn2 = sim_f2_full_fp_dr(ra0, rr0, freq, s_one, noise_db=-68.0, rng=np.random.RandomState(42 + int(sv * 100)))
                rep_curves[f"hq0_f1_a_{tag}"] = fa1[0]
                rep_curves[f"hq0_f1_rho_{tag}"] = (fa1 / np.maximum(fn1 - 1.0, 0.05))[0]
                rep_curves[f"hq0_f2_a_{tag}"] = fa2[0]
                rep_curves[f"hq0_f2_rho_{tag}"] = (fa2 / np.maximum(fn2 - 1.0, 0.05))[0]

    # Parallel F1 + F2 (+-10% test drift across 5 draws)
    print("\n[1/3] Running F1 (Exact Fresnel) & F2 (Full FP + -68 dB DR) +-10% Stress Tests...", flush=True)
    f12_jobs = [
        (ds_k, ra, rr, freq, y, g, mn, fk, sel)
        for ds_k, (ra, rr, y, g, freq) in ds_loaded.items()
        for mn, fk, sel in STRESS_MODELS
    ]
    f12_res = Parallel(n_jobs=n_jobs, prefer="processes")(delayed(_f1_f2_model_worker)(*j) for j in f12_jobs)

    # Parallel F2-S2 (+-15% all-pellet physical thickness + FP + -68 dB DR end-to-end retrain, 3 draws)
    print("\n[2/3] Running F2-S2 (+-15% All-Pellet Physical FP+DR End-to-End Retrain, 3 draws)...", flush=True)
    s2_jobs = [
        (ds_k, ra, rr, freq, y, g, mn, fk, sel, dr)
        for ds_k, (ra, rr, y, g, freq) in ds_loaded.items()
        for mn, fk, sel in STRESS_MODELS
        for dr in range(3)
    ]
    s2_res = Parallel(n_jobs=n_jobs, prefer="processes")(delayed(_f2_s2_retrain_worker)(*j) for j in s2_jobs)

    s2_map = {}
    for ds_k, mn, acc in s2_res:
        s2_map.setdefault(ds_k, {}).setdefault(mn, []).append(acc)

    per_matrix = {}
    for ds_k, mn, c_acc, f1_m, f2_m in f12_res:
        s2_m = float(np.mean(s2_map[ds_k][mn]))
        per_matrix.setdefault(ds_k, {})[mn] = {
            "clean_acc": round(c_acc, 2),
            "F1_fresnel_10pct_mean": round(f1_m, 2),
            "F1_drop": round(f1_m - c_acc, 2),
            "F2_fp_dr_10pct_mean": round(f2_m, 2),
            "F2_drop": round(f2_m - c_acc, 2),
            "F2_S2_fp_dr_15pct_mean": round(s2_m, 2),
            "F2_S2_drop": round(s2_m - c_acc, 2),
        }

    cross_avg = {}
    for mn, _, _ in STRESS_MODELS:
        c_m = np.mean([per_matrix[dk][mn]["clean_acc"] for dk in ds_loaded])
        f1_m = np.mean([per_matrix[dk][mn]["F1_fresnel_10pct_mean"] for dk in ds_loaded])
        f2_m = np.mean([per_matrix[dk][mn]["F2_fp_dr_10pct_mean"] for dk in ds_loaded])
        s2_m = np.mean([per_matrix[dk][mn]["F2_S2_fp_dr_15pct_mean"] for dk in ds_loaded])
        cross_avg[mn] = {
            "clean_mean": round(float(c_m), 2),
            "F1_mean": round(float(f1_m), 2),
            "F1_drop_mean": round(float(f1_m - c_m), 2),
            "F2_mean": round(float(f2_m), 2),
            "F2_drop_mean": round(float(f2_m - c_m), 2),
            "F2_S2_mean": round(float(s2_m), 2),
            "F2_S2_drop_mean": round(float(s2_m - c_m), 2),
        }

    for dk in ds_loaded:
        print(f"  [{dk}]", flush=True)
        for mn, _, _ in STRESS_MODELS:
            r = per_matrix[dk][mn]
            print(
                f"    {mn:25s}: Clean={r['clean_acc']:5.2f}% | F1={r['F1_fresnel_10pct_mean']:5.2f}% ({r['F1_drop']:+5.2f}%) | "
                f"F2={r['F2_fp_dr_10pct_mean']:5.2f}% ({r['F2_drop']:+5.2f}%) | F2-S2={r['F2_S2_fp_dr_15pct_mean']:5.2f}% ({r['F2_S2_drop']:+5.2f}%)",
                flush=True,
            )

    print("\n[3/3] Computing Direct Measured Dynamic Range DR(w) vs. R_j(w) Correlations...", flush=True)
    dr_corr, dr_arrays = compute_dr_and_correlation(plot_npz)

    summary["physics_stress_v21"] = {
        "per_matrix": per_matrix,
        "cross_matrix_avg": cross_avg,
        "curve_rel_shifts": curve_shifts,
        "notes": "Seed=42 outer 5-fold CV; F1=Exact Fresnel reflection mismatch (+-10% test, 5 draws); F2=Full complex Fabry-Perot + Beer-Lambert + -68 dB DR noise (+-10% test, 5 draws); F2_S2=Full FP+DR +-15% all-pellet retrain (3 draws).",
    }
    summary["repeatability_dr_correlation"] = dr_corr
    summary["v21_addendum_elapsed_sec"] = round(time.time() - t0, 2)

    plot_npz.update(dr_arrays)
    plot_npz.update(rep_curves)

    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    np.savez(PLOT_NPZ_PATH, **plot_npz)
    print("\n" + "=" * 90, flush=True)
    print(f"  [V2.1 ADDENDUM COMPLETE] Updated {SUMMARY_PATH.name} & {PLOT_NPZ_PATH.name} in {summary['v21_addendum_elapsed_sec']}s", flush=True)
    print("=" * 90, flush=True)


if __name__ == "__main__":
    main()
