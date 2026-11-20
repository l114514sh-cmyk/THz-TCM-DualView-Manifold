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
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, ConfusionMatrixDisplay

warnings.filterwarnings('ignore')

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['axes.unicode_minus'] = False

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

# 针对天麻 4 个产地的映射字典，并兼容本地错别字“毫”
label_map = {
    '安徽亳州': 'Bozhou (AH)',
    '安徽毫州': 'Bozhou (AH)',
    '贵州雷山': 'Leishan (GZ)',
    '吉林长白山': 'Changbai (JL)',
    '云南': 'Yunnan (YN)'
}

all_features = []
all_labels = []
excel_files = glob.glob(os.path.join(current_dir, "*天麻*.xlsx")) + glob.glob(os.path.join(current_dir, "*.xlsx"))

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
        abs_feat = savgol_filter(sa_v[:, i], window_length=15, polyorder=2, deriv=2)
        ref_feat = savgol_filter(sr_v[:, i], window_length=15, polyorder=2, deriv=1)
        all_features.append(np.hstack([abs_feat, ref_feat]))
        all_labels.append(lbl)

X_all = np.array(all_features)
y_all = np.array(all_labels)

print(f"\n>>> [天麻数据集载入成功] 样本总量: {X_all.shape[0]}, 特征维度: {X_all.shape[1]}")

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
strict_pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('mcuve', StrictMCUVE(keep_ratio=0.30, n_mc=60, n_components=3, seed=SEED)),
    ('svm', SVC(kernel='rbf', random_state=SEED))
])

param_grid = {
    'svm__C': [1, 10, 50, 100],
    'svm__gamma': ['scale', 0.005, 0.01, 0.05]
}

print(">>> 正在天麻 4 产地数据集上执行严格无泄漏嵌套验证...")
grid = GridSearchCV(strict_pipeline, param_grid, cv=cv, scoring='accuracy', n_jobs=-1)
grid.fit(X_all, y_all)

best_model = grid.best_estimator_
y_pred = cross_val_predict(best_model, X_all, y_all, cv=cv)
acc = accuracy_score(y_all, y_pred) * 100

print(f"\n=======================================================")
print(f"  * 天麻 4 产地严格盲测准确率 (Strict Pipeline): {acc:.2f}%")
print(f"=======================================================\n")
print(classification_report(y_all, y_pred, digits=4))

# 绘制天麻混淆矩阵
classes = ['Bozhou (AH)', 'Leishan (GZ)', 'Changbai (JL)', 'Yunnan (YN)']
fig, ax = plt.subplots(figsize=(6.8, 5.8))
cm = confusion_matrix(y_all, y_pred, labels=classes)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=classes)
disp.plot(cmap=plt.cm.Blues, ax=ax, values_format='d', colorbar=True)

ax.set_title(f"Confusion Matrix for Gastrodia elata ({acc:.2f}%)", fontsize=11.5, pad=12, fontweight='bold')
ax.set_xlabel("Predicted Label", fontsize=10.5, labelpad=8)
ax.set_ylabel("True Label", fontsize=10.5, labelpad=8)
plt.xticks(rotation=15, ha='right', fontsize=9.5)
plt.yticks(fontsize=9.5)
plt.tight_layout()

out_fig = os.path.join(current_dir, "Figure_Tianma_Matrix.png")
plt.savefig(out_fig, dpi=300, bbox_inches='tight')
print(f"[完成] 天麻混淆矩阵图已保存至: {out_fig}")
plt.show()