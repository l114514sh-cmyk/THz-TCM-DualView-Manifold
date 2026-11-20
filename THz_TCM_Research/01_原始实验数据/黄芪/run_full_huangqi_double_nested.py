import os
import time
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from scipy.signal import savgol_filter
from sklearn.cross_decomposition import PLSRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
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
t_start = time.time()

current_dir = os.path.dirname(os.path.abspath(__file__))
cache_file = os.path.join(current_dir, "huangqi_fast_cache.npz")

if not os.path.exists(cache_file):
    raise FileNotFoundError("未找到 huangqi_fast_cache.npz，请确保脚本放在黄芪数据目录下且已生成缓存！")

# ==============================================================================
# 1. 加载全部 403 个黄芪样本
# ==============================================================================
data = np.load(cache_file, allow_pickle=True)
raw_a_all = data['raw_a']
raw_r_all = data['raw_r']
y_all = data['y']

print("================================================================================")
print(f"  [Step 1] 全量黄芪样本加载完成: 共 {len(y_all)} 片 (100% 样本进入双层严格嵌套评估)")
print("================================================================================")
for k, v in pd.Series(y_all).value_counts().items():
    print(f"  * {k:<15s}: {v} 片")


# ==============================================================================
# 2. 单样本内部多尺度去散射物理特征提取 (纯单条光谱内部运算，零跨样本信息泄漏)
# ==============================================================================
def sample_wise_snv(spec_1d):
    return (spec_1d - np.mean(spec_1d)) / (np.std(spec_1d) + 1e-8)

X_opt_list = []
for i in range(len(y_all)):
    ra, rr = raw_a_all[i], raw_r_all[i]
    snv_a = sample_wise_snv(ra)
    snv_r = sample_wise_snv(rr)

    env_a = savgol_filter(snv_a, window_length=19, polyorder=2, deriv=0)
    d1_a  = sample_wise_snv(savgol_filter(snv_a, window_length=19, polyorder=2, deriv=1))
    d2_a  = sample_wise_snv(savgol_filter(snv_a, window_length=15, polyorder=2, deriv=2))

    env_r = savgol_filter(snv_r, window_length=19, polyorder=2, deriv=0)
    d1_r  = sample_wise_snv(savgol_filter(snv_r, window_length=15, polyorder=2, deriv=1))

    X_opt_list.append(np.hstack([env_a, d1_a, d2_a, env_r, d1_r]))

X_opt = np.array(X_opt_list)


# ==============================================================================
# 3. 严格无泄漏折叠状态计算 (MC-UVE 稳定性 + 净化子空间收缩判别流形)
# ==============================================================================
def compute_fold_state(X_tr, y_tr, X_te, n_mc=30, n_comp=3, pure_ratio=0.35, seed=42):
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    n_samples, n_features = X_tr_s.shape
    y_dummy = pd.get_dummies(y_tr).values[:, :-1].astype(float)
    coefs = np.zeros((n_mc, n_features))

    rng = np.random.RandomState(seed)
    sample_size = int(n_samples * 0.8)
    for i in range(n_mc):
        sub_idx = rng.choice(n_samples, sample_size, replace=False)
        pls = PLSRegression(n_components=n_comp, max_iter=50, tol=1e-3)
        pls.fit(X_tr_s[sub_idx], y_dummy[sub_idx])
        c = np.abs(pls.coef_)
        if c.ndim > 1 and c.shape[0] != n_features:
            c = c.T
        coefs[i, :] = np.mean(c, axis=1) if c.ndim > 1 else c

    stability = np.mean(coefs, axis=0) / (np.std(coefs, axis=0) + 1e-8)

    # 先通过稳定性净化子空间，再在纯净子空间拟合 Shrinkage LDA，避免噪声维度污染类内散度矩阵
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


# ==============================================================================
# 4. 执行【真·双层严格嵌套 5 折交叉验证】
#    外层 5 折绝对锁死仅做盲测；内层 3 折在每折训练集内部独立挑选最优超参数
# ==============================================================================
print("\n================================================================================")
print("  [Step 2] 启动全样本【双层严格嵌套 5-Fold CV】(外层绝对盲测 + 内层独立寻优)")
print("================================================================================")

outer_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
oof_preds = np.empty_like(y_all)
fold_accs = []

for fold_i, (tr_out, te_out) in enumerate(outer_cv.split(X_opt, y_all), 1):
    t_f = time.time()
    X_tr_out, y_tr_out = X_opt[tr_out], y_all[tr_out]
    X_te_out, y_te_out = X_opt[te_out], y_all[te_out]

    # 内层 3 折 CV：完全隔离外层测试集 te_out，仅在 tr_out 内决定超参数
    inner_cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED + fold_i)
    inner_splits = list(inner_cv.split(X_tr_out, y_tr_out))
    inner_states = [
        compute_fold_state(X_tr_out[itr], y_tr_out[itr], X_tr_out[iva], seed=SEED + fold_i)
        for itr, iva in inner_splits
    ]

    best_in_acc, best_cfg = -1, None
    for lw in [1.0, 2.0, 3.0]:
        for C in [1, 5, 10, 50]:
            for gamma in ['scale', 0.002, 0.005]:
                in_oof = np.empty_like(y_tr_out)
                for (itr, iva), st in zip(inner_splits, inner_states):
                    F_itr, F_iva = build_features(*st, keep_ratio=0.35, alpha_w=0.5, latent_w=lw)
                    clf = SVC(kernel='rbf', C=C, gamma=gamma, random_state=SEED).fit(F_itr, y_tr_out[itr])
                    in_oof[iva] = clf.predict(F_iva)
                acc = accuracy_score(y_tr_out, in_oof)
                if acc > best_in_acc:
                    best_in_acc = acc
                    best_cfg = (lw, C, gamma)

    # 使用内层定好的超参数在外层训练集上拟合，并对从未见过的外层测试折进行单向盲测
    out_state = compute_fold_state(X_tr_out, y_tr_out, X_te_out, seed=SEED + fold_i)
    F_tr_out, F_te_out = build_features(*out_state, keep_ratio=0.35, alpha_w=0.5, latent_w=best_cfg[0])
    clf_final = SVC(kernel='rbf', C=best_cfg[1], gamma=best_cfg[2], random_state=SEED).fit(F_tr_out, y_tr_out)

    preds = clf_final.predict(F_te_out)
    oof_preds[te_out] = preds
    f_acc = accuracy_score(y_te_out, preds) * 100
    fold_accs.append(f_acc)

    print(f"  * Outer Fold {fold_i}/5 | 盲测准确率: {f_acc:6.2f}% | 内层选定参数(λ,C,γ): {best_cfg} | 耗时 {time.time()-t_f:.1f}s", flush=True)

total_acc = accuracy_score(y_all, oof_preds) * 100
macro_f1 = f1_score(y_all, oof_preds, average='macro')
mean_acc = np.mean(fold_accs)
std_acc = np.std(fold_accs)

print("\n================================================================================")
print(f"  ★ 全样本 (n={len(y_all)}) 双层严格嵌套真实盲测准确率: {total_acc:.2f}%")
print(f"  ★ 5 折稳定性统计 (Mean ± SD):                  {mean_acc:.2f}% ± {std_acc:.2f}%")
print(f"  ★ 全样本 Macro-F1 指标:                        {macro_f1:.4f}")
print(f"  ★ 全流程总耗时:                                {time.time() - t_start:.1f} 秒")
print("================================================================================\n")

classes = ['Datong (SX)', 'Guyang (IM)', 'Qujing (YN)', 'Gansu (GS)']
present_classes = [c for c in classes if c in np.unique(y_all)]
print(classification_report(y_all, oof_preds, labels=present_classes, digits=4))

# ==============================================================================
# 5. 绘制并保存全样本出版级混淆矩阵 (Figure 2)
# ==============================================================================
fig, ax = plt.subplots(figsize=(6.8, 5.8), dpi=300)
cm = confusion_matrix(y_all, oof_preds, labels=present_classes)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=present_classes)
disp.plot(cmap=plt.cm.Blues, ax=ax, values_format='d', colorbar=True)

ax.set_title(
    f"Astragali Radix: Double-Nested 5-Fold CV (n={len(y_all)})\n"
    f"Accuracy: {total_acc:.2f}% ({mean_acc:.2f}% ± {std_acc:.2f}%)",
    fontsize=11, pad=12, fontweight='bold'
)
ax.set_xlabel("Predicted Label", fontsize=10.5, labelpad=8)
ax.set_ylabel("True Label", fontsize=10.5, labelpad=8)
plt.xticks(rotation=20, ha='right', fontsize=9.5)
plt.yticks(fontsize=9.5)
plt.tight_layout()

out_fig = os.path.join(current_dir, "Figure 2_Full_Double_Nested_CM.png")
plt.savefig(out_fig, dpi=300, bbox_inches='tight')
print(f"[完成] 全样本双层严格嵌套混淆矩阵图已保存至: {out_fig}")
