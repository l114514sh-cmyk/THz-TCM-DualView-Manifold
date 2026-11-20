import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# 设置标准学术字体
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']

current_dir = os.path.dirname(os.path.abspath(__file__))

# 5 张图片的文件名及对应标题
images_info = [
    ("calycosin.png", "(a) Calycosin (Equilibrium Structure)"),
    ("Calycosin_Mode1_0.885THz.png", "(b) Calycosin Mode 1 (0.885 THz)"),
    ("Spinosin.png", "(c) Spinosin (Equilibrium Structure)"),
    ("Spinosin_Mode3_0.605THz.png", "(d) Spinosin Mode 3 (0.605 THz)"),
    ("Spinosin_Mode5_0.979THz.png", "(e) Spinosin Mode 5 (0.979 THz)")
]

def autocrop(img):
    """自动裁剪 GaussView 导出的过大白边"""
    bg = Image.new(img.mode, img.size, (255, 255, 255))
    diff = Image.eval(img, lambda a: 255 - a if a > 240 else 0)
    bbox = img.convert("RGB").getbbox()
    if bbox:
        # 适当外扩 20 像素边距
        w, h = img.size
        bbox = (max(0, bbox[0]-20), max(0, bbox[1]-20), min(w, bbox[2]+20), min(h, bbox[3]+20))
        return img.crop(bbox)
    return img

# 创建排版画布：第一行放黄芪单体与振动模式（2张），第二行放酸枣仁单体与两个振动模式（3张）
fig = plt.figure(figsize=(13, 8))
gs = fig.add_gridspec(2, 6, height_ratios=[1, 1], hspace=0.15, wspace=0.1)

# 第一行：毛蕊异黄酮 (Calycosin)
ax1 = fig.add_subplot(gs[0, 0:3])
ax2 = fig.add_subplot(gs[0, 3:6])

# 第二行：斯诺新 (Spinosin)
ax3 = fig.add_subplot(gs[1, 0:2])
ax4 = fig.add_subplot(gs[1, 2:4])
ax5 = fig.add_subplot(gs[1, 4:6])

axes = [ax1, ax2, ax3, ax4, ax5]

for (fname, title), ax in zip(images_info, axes):
    fpath = os.path.join(current_dir, fname)
    if os.path.exists(fpath):
        img = Image.open(fpath)
        img_cropped = autocrop(img)
        ax.imshow(img_cropped)
        ax.set_title(title, fontsize=11, fontweight='bold', pad=8)
    else:
        print(f"Warning: {fname} not found!")
    ax.axis('off')  # 隐藏坐标轴

plt.tight_layout()
output_path = os.path.join(current_dir, "Figure 6.png")
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"\n[完成] 拼接成功的 Figure 6 已保存至: {output_path}")
plt.show()