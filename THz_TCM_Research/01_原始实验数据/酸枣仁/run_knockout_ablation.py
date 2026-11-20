import os
import glob
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

from scipy.signal import savgol_filter
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cross_decomposition import PLSRegression
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, GridSearchCV, cross_val_predict
from sklearn.metrics import accuracy_score, f1_score

warnings.filterwarnings('ignore')

SEED = 42
np.random.seed(SEED)

class StrictMCUVE(BaseEstimator, TransformerMixin):
    def __init__(self, keep_ratio=0.30, n_mc=60, n_components=3, seed=42):
        self.keep_ratio = keep_ratio
        self.n_mc = n_mc
        self.n_components = n_components
        self.seed = seed
        self.selected_indices_ = None

    def fit(self, X, y):
        n_samples, n_features = X.shape
        y_dummy = pd.get_dummies(y).values.astype(float)
        coefs = np.zeros((self.n_mc, n_features))
        rng = np.random.RandomState(self.seed)
        sample_size = int(n_samples * 0.8)

        for i in range(self.n_mc):
            sub_idx = rng.choice(n_samples, sample_size, replace=False)
            pls = PLSRegression(n_components=min(self.n_components, sample_size - 1))
            pls.fit(X[sub_idx], y_dummy[sub_idx])

            c = np.abs(pls.coef_)
            if c.ndim > 1 and c.shape[0] != n_features:
                c = c.T
            coefs[i, :] = np.mean(c, axis=1) if c.ndim > 1 else c

        mean_b = np.mean(coefs, axis=0)
        std_b = np.std(coefs, axis=0) + 1e-8
        stability = mean_b / std_b

        n_keep = max(20, int(n_features * self.keep_ratio))
        top_idx = np.argsort(stability)[::-1][:n_keep]
        self.selected_indices_ = np.sort(top_idx)
        return self

    def transform(self, X):
        return X[:, self.selected_indices_]

current_dir = os.path.dirname(os.path.abspath(__file__))
is_hq = ("黄芪" in current_dir) or any("黄芪" in f for f in os.listdir(current_dir))

if is_hq:
    target_name = "Astragali Radix"
    label_map = {
        '内蒙古固阳': 'Guyang (IM)',
        '山西大同': 'Datong (SX)',
        '曲靖': 'Qujing (YN)',
        '甘肃': 'Gansu (GS)'
    }
    excel_files = glob.glob(os.path.join(current_dir, "*黄芪*.xlsx")) + glob.glob(os.path.join(current_dir, "*.xlsx"))
else:
    target_name = "Ziziphi Spinosae Semen"
    label_map = {
        "盒养河北酸枣仁202606070619.xlsx": "Boxed (HB)",
        "酸枣仁信盛常河北石家庄安徽亳州202606070550.xlsx": "SJZ/BZ",
        "酸枣仁信盛常河北石家庄安徽毫州202606070550.xlsx": "SJZ/BZ",
        "酸枣仁散装大袋202606070510.xlsx": "Bulk-Bag",
        "散装50g202606070729.xlsx": "Bulk-50g",
        "同仁堂安徽亳州202606070657.xlsx": "Tongrentang (AH)",
        "同仁堂安徽毫州202606070657.xlsx": "Tongrentang (AH)"
    }
    excel_files = glob.glob(os.path.join(current_dir, "*.xlsx"))

raw_dual_list, full_dual_list, abs_only_list, labels_list = [], [], [], []

for file_path in set(excel_files):
    fname = os.path.basename(file_path)
    lbl = next((v for k, v in label_map.items() if k in fname), None)
    if lbl is None:
        continue
    try:
        df_a = pd.read_excel(file_path, sheet_name="吸收系数")
        df_r = pd.read_excel(file_path, sheet_name="折射率")
    except:
        continue

    freq = df_a.iloc[:, 0].values
    mask = (freq >= 0.22) & (freq <= 1.04)

    sa = df_a.iloc[:, 1:].values if 'Thz' in str(df_a.columns[0]) else df_a.iloc[:, 2:].values
    sr = df_r.iloc[:, 1:].values if 'Thz' in str(df_r.columns[0]) else df_r.iloc[:, 2:].values

    sa_v = sa[mask, :]
    sr_v = sr[mask, :]

    for i in range(sa_v.shape[1]):
        raw_a = sa_v[:, i]
        raw_r = sr_v[:, i]
        abs_sg2 = savgol_filter(raw_a, window_length=15, polyorder=2, deriv=2)
        ref_sg1 = savgol_filter(raw_r, window_length=15, polyorder=2, deriv=1)

        # 1. 完整特征: 双通道 SG 导数
        full_dual_list.append(np.hstack([abs_sg2, ref_sg1]))
        # 2. 敲除折射率特征: 仅吸收 SG-2nd
        abs_only_list.append(abs_sg2)
        # 3. 敲除导数预处理特征: 原始吸收 + 原始折射率拼合
        raw_dual_list.append(np.hstack([raw_a, raw_r]))
        labels_list.append(lbl)

X_full = np.array(full_dual_list)
X_no_ref = np.array(abs_only_list)
X_no_sg = np.array(raw_dual_list)
y = np.array(labels_list)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
svm_param_grid = {'svm__C': [1, 10, 50, 100], 'svm__gamma': ['scale', 0.005, 0.01, 0.05]}

# 定义严格的敲除实验组
knockout_experiments = {
    "Full Proposed Model": {
        "X": X_full,
        "pipe": Pipeline([
            ('scaler', StandardScaler()),
            ('mcuve', StrictMCUVE(keep_ratio=0.30, n_mc=60, n_components=3, seed=SEED)),
            ('svm', SVC(kernel='rbf', random_state=SEED))
        ])
    },
    "w/o MC-UVE (Full Spectrum)": {
        "X": X_full,
        "pipe": Pipeline([
            ('scaler', StandardScaler()),
            ('svm', SVC(kernel='rbf', random_state=SEED))
        ])
    },
    "w/o Refractive Index (Abs Only)": {
        "X": X_no_ref,
        "pipe": Pipeline([
            ('scaler', StandardScaler()),
            ('mcuve', StrictMCUVE(keep_ratio=0.30, n_mc=60, n_components=3, seed=SEED)),
            ('svm', SVC(kernel='rbf', random_state=SEED))
        ])
    },
    "w/o SG-Derivative (Raw Fused)": {
        "X": X_no_sg,
        "pipe": Pipeline([
            ('scaler', StandardScaler()),
            ('mcuve', StrictMCUVE(keep_ratio=0.30, n_mc=60, n_components=3, seed=SEED)),
            ('svm', SVC(kernel='rbf', random_state=SEED))
        ])
    }
}

knockout_results = []
print(f"\n==================================================================")
print(f"  正在执行标准【模块敲除消融实验 (Leave-One-Out Ablation)】: {target_name}")
print(f"==================================================================")

baseline_acc = None

for name, cfg in knockout_experiments.items():
    print(f">>> 正在测试配置: {name} ...")
    X_curr = cfg["X"]
    pipe = cfg["pipe"]

    grid = GridSearchCV(pipe, svm_param_grid, cv=cv, scoring='accuracy', n_jobs=-1)
    grid.fit(X_curr, y)
    best_pipe = grid.best_estimator_

    y_pred = cross_val_predict(best_pipe, X_curr, y, cv=cv)
    acc = accuracy_score(y, y_pred) * 100
    f1 = f1_score(y, y_pred, average='macro')

    if baseline_acc is None:
        baseline_acc = acc
        diff_str = "0.00 (Reference)"
    else:
        diff = acc - baseline_acc
        diff_str = f"{diff:+.2f}%"

    knockout_results.append({
        "Configuration": name,
        "Accuracy (%)": f"{acc:.2f}",
        "Delta Acc (%)": diff_str,
        "Macro-F1": f"{f1:.4f}"
    })
    print(f"    -> Accuracy: {acc:.2f}%, 相对完整模型差异: {diff_str}\n")

df_knock = pd.DataFrame(knockout_results)
print("=" * 85)
print(f"       Strict Leave-One-Out Ablation Table ({target_name})")
print("=" * 85)
print(df_knock.to_string(index=False))
print("=" * 85)

out_file = os.path.join(current_dir, f"Strict_Ablation_{target_name.replace(' ', '_')}.txt")
with open(out_file, "w", encoding="utf-8") as f:
    f.write(df_knock.to_string(index=False))
print(f"[完成] 标准敲除消融数据已存至: {out_file}")

# ==============================================================================
# 追加绘图模块：生成出版级模块敲除相对贡献图 (Figure_Strict_Ablation.png)
# ==============================================================================
configs = [r["Configuration"].replace(" (Reference)", "") for r in knockout_results]
deltas = []
for r in knockout_results:
    val_str = r["Delta Acc (%)"].replace("%", "").replace("(Reference)", "").strip()
    deltas.append(float(val_str) if val_str else 0.0)

fig, ax = plt.subplots(figsize=(8.2, 4.5))

# 剔除第一个基准 Reference，只画敲除项的相对变动
ablation_labels = configs[1:]
delta_vals = deltas[1:]
y_pos = np.arange(len(ablation_labels))

colors = ['#2b5c8f' if v >= 0 else '#d95f02' for v in delta_vals]

bars = ax.barh(y_pos, delta_vals, height=0.45, color=colors, edgecolor='black', alpha=0.88)

ax.axvline(0, color='black', linewidth=1.2, linestyle='--')
ax.set_yticks(y_pos)
ax.set_yticklabels(ablation_labels, fontsize=10.5)
ax.invert_yaxis()  # 从上到下显示

ax.set_xlabel(r"$\Delta$ Accuracy (%) relative to Full Proposed Model", fontsize=10.5, labelpad=8)
ax.set_title(f"Leave-One-Out Ablation Analysis ({target_name})", fontsize=12, pad=12, fontweight='bold')
ax.grid(True, linestyle=':', alpha=0.5, axis='x')

# 在柱子两端标注具体数值
for bar, val in zip(bars, delta_vals):
    offset = 0.15 if val >= 0 else -0.15
    ha = 'left' if val >= 0 else 'right'
    ax.annotate(f"{val:+.2f}%",
                xy=(val, bar.get_y() + bar.get_height() / 2),
                xytext=(offset * 20, 0), textcoords="offset points",
                ha=ha, va='center', fontsize=9.5, fontweight='bold',
                color='#1a3b5c' if val >= 0 else '#9e3d00')

# 自动调整 X 轴范围留出标注空隙
max_abs = max(abs(min(delta_vals)), abs(max(delta_vals)), 1.5) + 2.0
ax.set_xlim(-max_abs, max_abs)

plt.tight_layout()
out_fig = os.path.join(current_dir, f"Figure_Strict_Ablation_{target_name.replace(' ', '_')}.png")
plt.savefig(out_fig, dpi=300, bbox_inches='tight')
print(f"[完成] 敲除消融相对偏差图已保存至: {out_fig}")
plt.show()