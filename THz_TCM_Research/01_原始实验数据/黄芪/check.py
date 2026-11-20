import glob
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']

# 读取黄芪数据并按产地聚合
# 这里请将路径替换为您本地黄芪数据的目录
file_labels = {
    '固阳': 'Guyang (IM)',
    '大同': 'Datong (SX)',
    '曲靖': 'Qujing (YN)',
    '甘肃': 'Gansu (GS)',
}

data_dict = {lbl: {'raw': [], 'sg2': []} for lbl in set(file_labels.values())}

# 伪代码逻辑：按实际文件遍历
for file_path in glob.glob('*.xlsx'):
  fname = os.path.basename(file_path)
  lbl = next((v for k, v in file_labels.items() if k in fname), None)
  if not lbl:
    continue

  df_a = pd.read_excel(file_path, sheet_name='吸收系数')
  freq = df_a.iloc[:, 0].values
  mask = (freq >= 0.22) & (freq <= 1.04)  # 严格截断至 1.04 THz 以内
  freq_valid = freq[mask]

  sa = (
      df_a.iloc[:, 1:].values
      if 'Thz' in str(df_a.columns[0])
      else df_a.iloc[:, 2:].values
  )
  sa_v = sa[mask, :]

  for i in range(sa_v.shape[1]):
    raw_spec = sa_v[:, i]
    # SG 二阶导数，窗口长建议设为 19 或 21，毛刺更少
    sg2_spec = savgol_filter(raw_spec, window_length=19, polyorder=2, deriv=2)
    data_dict[lbl]['raw'].append(raw_spec)
    data_dict[lbl]['sg2'].append(sg2_spec)

# 开始画高品质 Figure 1
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
colors = {
    'Datong (SX)': '#1f77b4',
    'Guyang (IM)': '#ff7f0e',
    'Qujing (YN)': '#2ca02c',
    'Gansu (GS)': '#d62728',
}

for lbl, specs in data_dict.items():
  if not specs['raw']:
    continue
  raw_arr = np.array(specs['raw'])
  sg2_arr = np.array(specs['sg2'])

  mean_raw = np.mean(raw_arr, axis=0)
  std_raw = np.std(raw_arr, axis=0)

  mean_sg2 = np.mean(sg2_arr, axis=0)
  std_sg2 = np.std(sg2_arr, axis=0)

  c = colors.get(lbl, 'blue')

  # (a) 原始吸收谱
  ax1.plot(freq_valid, mean_raw, label=lbl, color=c, lw=1.8)
  ax1.fill_between(
      freq_valid, mean_raw - std_raw, mean_raw + std_raw, color=c, alpha=0.15
  )

  # (b) SG 二阶导数谱
  ax2.plot(freq_valid, mean_sg2, label=lbl, color=c, lw=1.8)
  ax2.fill_between(
      freq_valid, mean_sg2 - std_sg2, mean_sg2 + std_sg2, color=c, alpha=0.15
  )

ax1.set_title('(a) Raw Absorption Spectra (Mean ± SD)', fontsize=12, pad=10)
ax1.set_xlabel('Frequency (THz)', fontsize=11)
ax1.set_ylabel('Absorption Coefficient (cm⁻¹)', fontsize=11)
ax1.set_xlim(0.22, 1.04)
ax1.legend(frameon=True, fontsize=9)
ax1.grid(True, ls='--', alpha=0.4)

ax2.set_title('(b) SG 2nd Derivative Spectra (Mean ± SD)', fontsize=12, pad=10)
ax2.set_xlabel('Frequency (THz)', fontsize=11)
ax2.set_ylabel('d²α / dω² (a.u.)', fontsize=11)
ax2.set_xlim(0.22, 1.04)
ax2.axhline(0, color='gray', ls=':', lw=1)  # 0 基线参考线
ax2.legend(frameon=True, fontsize=9)
ax2.grid(True, ls='--', alpha=0.4)

plt.tight_layout()
plt.savefig('Figure 1_Mean_SD.png', dpi=300)
plt.show()