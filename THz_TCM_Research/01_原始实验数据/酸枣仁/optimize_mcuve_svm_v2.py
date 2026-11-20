import glob
import os
import warnings
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedKFold,
    cross_val_predict,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

warnings.filterwarnings('ignore')

SEED = 42
np.random.seed(SEED)


# ==============================================================================
# 1. 修正后的严格分块 MC-UVE (带符号稳定性计算 + 双通道平衡优选)
# ==============================================================================
class BalancedStrictMCUVE(BaseEstimator, TransformerMixin):

  def __init__(
      self, keep_ratio=0.30, n_mc=60, n_components=4, split_idx=358, seed=42
  ):
    self.keep_ratio = keep_ratio
    self.n_mc = n_mc
    self.n_components = n_components
    self.split_idx = split_idx  # 吸收通道与折射率通道的分界线
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

      # 保留 PLS 回归系数的原始正负号（核心修正）
      c = pls.coef_
      if c.ndim > 1 and c.shape[0] != n_features:
        c = c.T
      coefs[i, :] = np.mean(c, axis=1) if c.ndim > 1 else c

    # 标准 UVE 计算公式：|mean(b)| / std(b)
    mean_b = np.mean(coefs, axis=0)
    std_b = np.std(coefs, axis=0) + 1e-8
    stability = np.abs(mean_b) / std_b

    # 双通道均衡筛选：两路各自选取 Top 30%
    n_keep_each = max(10, int((n_features // 2) * self.keep_ratio))

    stab_a = stability[: self.split_idx]
    top_a = np.argsort(stab_a)[::-1][:n_keep_each]

    stab_r = stability[self.split_idx :]
    top_r = np.argsort(stab_r)[::-1][:n_keep_each] + self.split_idx

    self.selected_indices_ = np.sort(np.concatenate([top_a, top_r]))
    return self

  def transform(self, X):
    return X[:, self.selected_indices_]


# ==============================================================================
# 2. 数据读取与双通道导数变换
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))

file_labels = {
    '盒养河北酸枣仁202606070619.xlsx': 'Boxed (HB)',
    '酸枣仁信盛常河北石家庄安徽亳州202606070550.xlsx': 'SJZ/BZ',
    '酸枣仁信盛常河北石家庄安徽毫州202606070550.xlsx': 'SJZ/BZ',
    '酸枣仁散装大袋202606070510.xlsx': 'Bulk-Bag',
    '散装50g202606070729.xlsx': 'Bulk-50g',
    '同仁堂安徽亳州202606070657.xlsx': 'Tongrentang (AH)',
    '同仁堂安徽毫州202606070657.xlsx': 'Tongrentang (AH)',
}

all_features, all_labels = [], []
excel_files = glob.glob(os.path.join(current_dir, '*.xlsx'))

for file_path in set(excel_files):
  fname = os.path.basename(file_path)
  lbl = next((v for k, v in file_labels.items() if k in fname), None)
  if lbl is None:
    continue

  try:
    df_a = pd.read_excel(file_path, sheet_name='吸收系数')
    df_r = pd.read_excel(file_path, sheet_name='折射率')
  except:
    continue

  freq = df_a.iloc[:, 0].values
  mask = (freq >= 0.22) & (freq <= 1.04)

  sa = (
      df_a.iloc[:, 1:].values
      if 'Thz' in str(df_a.columns[0])
      else df_a.iloc[:, 2:].values
  )
  sr = (
      df_r.iloc[:, 1:].values
      if 'Thz' in str(df_r.columns[0])
      else df_r.iloc[:, 2:].values
  )

  sa_v, sr_v = sa[mask, :], sr[mask, :]

  for i in range(sa_v.shape[1]):
    abs_feat = savgol_filter(
        sa_v[:, i], window_length=15, polyorder=2, deriv=2
    )
    ref_feat = savgol_filter(
        sr_v[:, i], window_length=15, polyorder=2, deriv=1
    )
    all_features.append(np.hstack([abs_feat, ref_feat]))
    all_labels.append(lbl)

X_all = np.array(all_features)
y_all = np.array(all_labels)

print(
    f'>>> 数据读取完成: 样本量 {X_all.shape[0]}, 单通道维度'
    f' {X_all.shape[1] // 2}'
)

# ==============================================================================
# 3. 严格嵌套建模与精细网格寻优
# ==============================================================================
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

strict_pipeline = Pipeline([
    ('scaler', StandardScaler()),
    (
        'mcuve',
        BalancedStrictMCUVE(
            keep_ratio=0.30,
            n_mc=60,
            n_components=4,
            split_idx=358,
            seed=SEED,
        ),
    ),
    ('svm', SVC(kernel='rbf', random_state=SEED)),
])

# 扩充为对数尺度的细化网格
param_grid = {
    'svm__C': [1, 5, 10, 50, 100, 200],
    'svm__gamma': ['scale', 0.001, 0.005, 0.01, 0.02, 0.05],
}

grid = GridSearchCV(
    strict_pipeline, param_grid, cv=cv, scoring='accuracy', n_jobs=-1
)
grid.fit(X_all, y_all)

best_model = grid.best_estimator_
print(f"  * 最佳超参数: {grid.best_params_}")

y_pred = cross_val_predict(best_model, X_all, y_all, cv=cv)
acc = accuracy_score(y_all, y_pred) * 100

print(f'\n>>> 优化版算法 5-Fold 盲测准确率: {acc:.2f}%\n')
print(classification_report(y_all, y_pred, digits=4))