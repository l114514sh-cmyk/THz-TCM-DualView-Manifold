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
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

warnings.filterwarnings('ignore')

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['axes.unicode_minus'] = False

SEED = 42
np.random.seed(SEED)

# ==============================================================================
# 1. 严格无泄漏 MC-UVE 转换器 (嵌套在 CV 内部)
# ==============================================================================
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

# ==============================================================================
# 2. 自动检测目录并读取多通道数据
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
is_hq = ("黄芪" in current_dir) or any("黄芪" in f for f in os.listdir(current_dir))

if is_hq:
    target_name = "Astragali Radix"
    label_map = {
        '内蒙古固阳': 'Guyang (IM)',
        '山西大同': 'Datong (SX)',
        '甘肃': 'Gansu (GS)',
        '曲靖': 'Qujing (YN)'
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

print(f"\n==================================================================")
print(f"  正在启动消融实验 (Ablation Study) -> 目标体系: {target_name}")
print(f"==================================================================")

raw_abs_list, sg2_abs_list, dual_list, labels_list = [], [], [], []

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
        abs_sg2 = savgol_filter(raw_a, window_length=15, polyorder=2, deriv=2)
        ref_sg1 = savgol_filter(sr_v[:, i], window_length=15, polyorder=2, deriv=1)

        raw_abs_list.append(raw_a)
        sg2_abs_list.append(abs_sg2)
        dual_list.append(np.hstack([abs_sg2, ref_sg1]))
        labels_list.append(lbl)

X_raw = np.array(raw_abs_list)
X_sg2 = np.array(sg2_abs_list)
X_dual = np.array(dual_list)
y = np.array(labels_list)

print(f">>> 数据加载完成: 有效样本量 {X_raw.shape[0]}, 单通道频点 {X_raw.shape[1]}, 双通道拼接维度 {X_dual.shape[1]}\n")

# ==============================================================================
# 3. 统一采用相同的分层 5 折交叉验证进行消融评测
# ==============================================================================
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
svm_param_grid = {
    'svm__C': [1, 10, 50, 100],
    'svm__gamma': ['scale', 0.005, 0.01, 0.05]
}

ablation_models = {
    "Model 1: Raw Absorption (Baseline)": {
        "X": X_raw,
        "pipeline": Pipeline([
            ('scaler', StandardScaler()),
            ('svm', SVC(kernel='rbf', random_state=SEED))
        ])
    },
    "Model 2: SG 2nd-Der (Abs Only)": {
        "X": X_sg2,
        "pipeline": Pipeline([
            ('scaler', StandardScaler()),
            ('svm', SVC(kernel='rbf', random_state=SEED))
        ])
    },
    "Model 3: Dual-Channel (Full Spectrum)": {
        "X": X_dual,
        "pipeline": Pipeline([
            ('scaler', StandardScaler()),
            ('svm', SVC(kernel='rbf', random_state=SEED))
        ])
    },
    "Model 4: Proposed (Dual + Nested MC-UVE)": {
        "X": X_dual,
        "pipeline": Pipeline([
            ('scaler', StandardScaler()),
            ('mcuve', StrictMCUVE(keep_ratio=0.30, n_mc=60, n_components=3, seed=SEED)),
            ('svm', SVC(kernel='rbf', random_state=SEED))
        ])
    }
}

results = []

for model_name, cfg in ablation_models.items():
    print(f">>> 正在运行评测 -> {model_name} ...")
    X_curr = cfg["X"]
    pipe = cfg["pipeline"]

    grid = GridSearchCV(pipe, svm_param_grid, cv=cv, scoring='accuracy', n_jobs=-1)
    grid.fit(X_curr, y)
    best_pipe = grid.best_estimator_

    y_pred = cross_val_predict(best_pipe, X_curr, y, cv=cv)

    acc = accuracy_score(y, y_pred) * 100
    prec = precision_score(y, y_pred, average='macro') * 100
    rec = recall_score(y, y_pred, average='macro') * 100
    f1 = f1_score(y, y_pred, average='macro')

    results.append({
        "Model Configuration": model_name,
        "Accuracy (%)": f"{acc:.2f}",
        "Precision (%)": f"{prec:.2f}",
        "Recall (%)": f"{rec:.2f}",
        "Macro-F1": f"{f1:.4f}"
    })
    print(f"    -> 5-Fold CV Accuracy: {acc:.2f}%, Macro-F1: {f1:.4f}\n")

# ==============================================================================
# 4. 输出出版级消融大表并保存
# ==============================================================================
df_res = pd.DataFrame(results)

print("=" * 80)
print(f"            Table 3: Ablation Study Results ({target_name})")
print("=" * 80)
print(df_res.to_string(index=False))
print("=" * 80)

# 保存表格到本地文本
out_txt = os.path.join(current_dir, f"Table3_Ablation_{target_name.replace(' ', '_')}.txt")
with open(out_txt, "w", encoding="utf-8") as f:
    f.write(f"Table 3. Ablation evaluation metrics for {target_name} across different stages (5-fold CV).\n\n")
    f.write(df_res.to_markdown(index=False))
print(f"\n[完成] 消融实验表格已保存至: {out_txt}")

# ==============================================================================
# 5. 绘制出版级阶梯对比图 (Figure_Ablation.png)
# ==============================================================================
fig, ax = plt.subplots(figsize=(8.5, 4.8))
stages = ["Model 1\n(Raw Abs)", "Model 2\n(SG-2nd)", "Model 3\n(Dual Fused)", "Model 4\n(Proposed)"]
accuracies = [float(r["Accuracy (%)"]) for r in results]
f1_scores = [float(r["Macro-F1"]) * 100 for r in results]

x = np.arange(len(stages))
width = 0.35

rects1 = ax.bar(x - width/2, accuracies, width, label='Accuracy (%)', color='#2b5c8f', edgecolor='black', alpha=0.9)
rects2 = ax.bar(x + width/2, f1_scores, width, label='Macro-F1 (×100)', color='#d95f02', edgecolor='black', alpha=0.9)

ax.set_ylabel('Performance (%)', fontsize=11, labelpad=8)
ax.set_title(f'Ablation Study: Progressive Performance Gain ({target_name})', fontsize=12, pad=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(stages, fontsize=10)
ax.set_ylim(min(accuracies) - 10, 102)
ax.grid(True, linestyle='--', alpha=0.4, axis='y')
ax.legend(loc='lower right', frameon=True)

for rect in rects1 + rects2:
    h = rect.get_height()
    ax.annotate(f'{h:.2f}%',
                xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points",
                ha='center', va='bottom', fontsize=8.5, fontweight='bold')

plt.tight_layout()
out_fig = os.path.join(current_dir, f"Figure_Ablation_{target_name.replace(' ', '_')}.png")
plt.savefig(out_fig, dpi=300, bbox_inches='tight')
print(f"[完成] 消融阶梯柱状图已保存至: {out_fig}")
plt.show()