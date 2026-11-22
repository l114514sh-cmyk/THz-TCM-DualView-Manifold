# 主力论文端 ↔ Colab 算力端 协同计算与审计日志（Compute Exchange & Audit Log）

> **文件定位**：本文件保存在本地主力工作区 `e:\论文\COMPUTE_EXCHANGE_LOG.md`，是**主力论文端（本地）**与**Colab 算力端（远端算力对话）**之间的唯一官方通信审计台账。  
> **核心分工**：
> - **主力论文端（本对话 / 本地 `e:\论文`）**：负责论文正文、科学严谨性审定、结果核验、Word 投稿文档生成（`build_submission_docx.py`）与 GitHub 仓库维护。
> - **Colab 算力端（远端 Colab 对话）**：负责承接高算力任务（如大规模压片级置换检验、GPU 深度学习/1D-CNN/Transformer 同输入公平对比基线、大规模超参/Bootstrap 稳健性扫频或量子化学/DFT 补充计算），并将**真实运行日志、脚本与 JSON 结果**回传给主力论文端核验。

---

## 一、不可逾越的学术真实性与防造假铁律（双方共同遵守）

1. **绝对真实、严禁虚构**：所有汇报的数值、准确率、$p$ 值、置信区间、硬件型号与运行耗时，**必须来自实际执行后的终端/Notebook 原始输出**。严禁估算、插值、记忆复述或编造任何未运行出来的数字。
2. **绝不隐瞒不利结果**：如果某项实验报错、跑不出来、显存/内存溢出，或者对比基线/新模型结果**不如**现有模型、甚至**高于**现有模型，必须**原样如实汇报**，严禁挑选好看的结果或篡改随机种子刷榜。
3. **强制锁定数据与防泄露口径（所有实验必须严格对齐）**：
   - **唯一数据源**：GitHub 公开仓库 `https://github.com/l114514sh-cmyk/THz-TCM-DualView-Manifold` 中的 3 个实测双通道缓存文件（无需本地 `.xlsx` 即可直接拉取运行）：
     - `THz_TCM_Research/01_原始实验数据/黄芪/huangqi_fast_cache.npz`（原始 `403 × 358`）
     - `THz_TCM_Research/01_原始实验数据/酸枣仁/suanzaoren_fast_cache.npz`（原始 `500 × 358`）
     - `THz_TCM_Research/01_原始实验数据/天麻/tianma_fast_cache.npz`（原始 `405 × 358`）
   - **唯一统一质控（QC）规则**：单谱级别 `1.2 <= mean(n) <= 2.6` **且** `mean(alpha) <= 55.0`（保留样本必须精确为：黄芪 `397` 条 / `80` 片、酸枣仁 `499` 条 / `100` 片、天麻 `404` 条 / `82` 片；合计 `1,300` 条 / `262` 片）。
   - **唯一合法验证协议**：**压片分组双层嵌套 5 折交叉验证（Pellet-Grouped `StratifiedGroupKFold`）**，压片分组键必须严格定义为 `pellet_id = (class_label, local_idx // 5)`，**严禁将同一片压片的 5 条连续扫描拆分到训练集与测试集**；任何标准化、特征筛选（MC-UVE）、降维（LDA/PCA）、模型超参调优必须严格封装在每个外层/内层训练折内部完成。
4. **可审计交付物**：每一轮算力端回报结果，必须附带：（a）完整可复现代码或精确改动 diff；（b）实际运行环境（GPU/CPU 型号、Python 与关键库版本）；（c）原始终端输出或机器可读 JSON 摘要；（d）明确标注“已完成 / 部分失败 / 异常说明”。
5. **单向采纳权**：算力端**不直接修改主力论文正文**；任何算力端产出的新结果，必须经主力论文端核验口径一致、无数据泄露且登记进本日志后，方可写入论文或返修回复信。

---

## 二、标准交流记录模板（后续每轮按序追加，禁止篡改历史记录）

```markdown
### [ROUND N] YYYY-MM-DD HH:MM — 任务主题
- **主力端本轮实际做了什么**：...
- **下发给算力端的明确指令**：...
- **算力端回报（原样摘要 + 环境 + 原始结果 + 异常/局限）**：...
- **主力端核验与采纳结论**：[待核验 / 已通过并采纳 / 驳回重跑（附原因）]
```

---

## 三、交流与审计正式记录

### [ROUND 0] 2026-11-22 22:55 — 建档初始化与算力端握手校验（Handshake）

- **主力端本轮实际做了什么（100% 事实记录）**：
  1. 通过 `git ls-files "*.npz"` 实地核查确认：3 个 `.npz` 光谱缓存文件（黄芪、酸枣仁、天麻）均已真实提交并托管在 GitHub 公开仓库 `main` 分支，Colab 算力端可直接 `git clone` 获取，无需手动上传本地 `.xlsx`。
  2. 在本地工作区新建本通信与审计日志 `e:\论文\COMPUTE_EXCHANGE_LOG.md`，明确了双方分工、绝对真实与防造假铁律、统一 QC 口径、压片分组防泄露协议及标准回合制审计模板。
  3. 同步起草了 Round 0 握手消息，要求 Colab 算力端在承接任何正式重算力任务前，先完成**环境自检 + 仓库拉取 + 3 个 `.npz` 样本数/压片数核对**（确保双方数据基座一模一样，零偏差）。
  4. **未改动**任何已锁定论文数值、模型代码或投稿 `.docx` 文件。

- **下发给算力端的明确指令（Round 0 握手任务）**：
  1. 在 Colab 中克隆仓库：`git clone https://github.com/l114514sh-cmyk/THz-TCM-DualView-Manifold.git`；
  2. 汇报当前 Colab 真实硬件与软件环境（GPU 型号与显存 / CPU 核数 / 内存 / Python、PyTorch、scikit-learn、numpy、scipy 版本；如果没有 GPU 也要如实写“仅 CPU”）；
  3. 仅运行一段只读校验脚本：加载 3 个 `.npz` 文件，应用统一 QC（`1.2 <= mean(n) <= 2.6` 且 `mean(alpha) <= 55.0`）并按 `pellet_id = (class, local_idx // 5)` 统计压片数，回报实际跑出的保留谱数与压片数，核对是否与主力端锁定基准（黄芪 `397/80`、酸枣仁 `499/100`、天麻 `404/82`）完全一致；
  4. 阅读仓库中的 `HANDOFF_PROJECT_SUMMARY.md` 和 `THz_TCM_Research/04_Python数据处理/run_unified_double_nested_all.py`，确认已理解口径后，等待主力端按需下发正式重算力任务（不要擅自改动论文口径或自创实验）。

- **算力端回报（2026-11-22 23:42 原样记录）**：
  - **状态**：`已完成`（零报错，耗时 12 秒，使用副号免费版未消耗 Colab Pro 额度）。
  - **仓库版本**：`Repo HEAD: f42d480`（与主力端一致）。
  - **实测环境**：`Tesla T4 (15,360 MiB VRAM)`，`CUDA=True`，`CPU=2 cores`，`RAM=12.67 GiB`，`Python 3.13.16`，`numpy 2.4.6`，`scipy 1.16.3`，`scikit-learn 1.6.1`，`torch 2.14.1+cu130`。
  - **只读 QC & 压片校验原始输出**：
    - 黄芪：`raw=403 -> QC_kept=397 scans, 80 pellets (dropped=6)`
    - 酸枣仁：`raw=500 -> QC_kept=499 scans, 100 pellets (dropped=1)`
    - 天麻：`raw=405 -> QC_kept=404 scans, 82 pellets (dropped=1)`
    - 总计：`raw=1308 -> QC_kept=1300 scans, 262 pellets`，`freq=0.222015~1.039124 THz (358 pts)`。

- **主力端核验与采纳结论**：`✅ 已通过（ROUND 0 核验零偏差）`。代码核查确认 `groups` 在 QC 掩码之前按 `local_i // 5` 生成，避免剔除单谱导致后续压片编号错位；与主力端基准 100% 一致。

---

### [ROUND 1] 2026-11-22 23:43 — Rebuttal 储备：严格压片分组 1D 深度学习公平对比基准（GPU）

- **主力端本轮实际做了什么（100% 事实记录）**：
  1. 完整核验了 Colab 算力端回传的 `ROUND 0` 原始输出与只读代码，确认环境（Tesla T4 + PyTorch CUDA）、仓库 HEAD（`f42d480`）、数据量与压片分组逻辑 100% 一致，并在本台账中归档。
  2. 针对 *Spectrochimica Acta Part A* 审稿人极高概率提出的“为何未与 1D 深度学习基线（1D-CNN / 1D-ResNet / MLP）对比”问题，设计了 **ROUND 1 严格防泄露 GPU 深度学习基准实验**（作为 Rebuttal 储备，**暂不修改已提交正文**）。
  3. 明确锁定输入轨道（Track A 双通道原始光谱 `2×358` + Track B 同输入双视图特征 `3,222` 维）、外层 5 折压片分组划分（与 `run_unified_double_nested_all.py` 完全相同的 `StratifiedGroupKFold(n_splits=5)`）、内层压片分组早停验证（严禁看外层测试折早停）、折内标准化及 3 种子均值汇报规范。

- **下发给算力端的明确指令（ROUND 1）**：
  在 Tesla T4 GPU 上编写并运行独立脚本 `run_colab_dl_baselines.py`（仅在 Colab 内存/临时目录运行，输出完整终端日志 + JSON 摘要），严格按以下防泄露协议在三类药材（黄芪、酸枣仁、天麻）上评估 **3 个代表性深度学习基线**：
  1. **Model 1 — 1D-CNN（Track A 原始双通道输入 `(2, 358)`）**：轻量级 3 层 1D 卷积（Conv1d + BatchNorm1d + ReLU + MaxPool + GlobalAvgPool + Dropout + Linear），每通道严格按外层训练折做逐通道标准化。
  2. **Model 2 — 1D-ResNet（Track A 原始双通道输入 `(2, 358)`）**：轻量级 1D 残差网络（2–3 个 Residual Block + GlobalAvgPool + Dropout + Linear），同样仅在训练折内拟合标准化。
  3. **Model 3 — Dual-View MLP（Track B 同输入 3,222 维双视图特征）**：复用 `run_unified_double_nested_all.py` 中的双视图特征构造（或精确等价实现），2 层隐藏层 + BatchNorm + ReLU + Dropout + Weight Decay，`StandardScaler` 严格在训练折内拟合。
  4. **防泄露硬性要求**：
     - 外层划分必须与主实验完全一致：`StratifiedGroupKFold(n_splits=5)`（分组键 `pellet_id = (class, local_idx // 5)`）；
     - 早停（Early Stopping）与最佳权重挑选**严禁使用外层测试折**，必须从外层训练折内部再按压片分组切分约 20% 压片作为内层验证集（`GroupShuffleSplit` / `StratifiedGroupKFold`）；
     - 跑 `3` 个随机种子（`42, 100, 2026`），汇报每个模型在每个基质上的：
       - **Scan-level Accuracy（均值 ± 标准差）** & **Macro-F1**
       - **Pellet-level Majority-Vote Accuracy（均值 ± 标准差，以及 seed=42 的精确正确压片数 `k/N`）**
       - **3 基质跨矩阵平均准确率（Scan / Pellet）**
       - 单模型总运行耗时与 GPU 显存占用。
     - 如实汇报真实结果，哪怕某深度学习模型超过或低于我们的 SW-MCUVE-Manifold（Scan `94.19%` / Pellet `97.50%`），绝不隐瞒、不调参刷榜。

- **算力端回报（2026-11-23 00:04 原样记录）**：
  - **状态**：`已完成`（`EXIT_CODE: 0`，零报错，耗时 `420.02 s`，峰值 GPU 显存 `35.54 MiB`，使用副号免费版未消耗主号 200 额度，未修改仓库正文）。
  - **仓库版本**：`Repo HEAD: be21874`，随机种子 `[42, 100, 2026]`，设备 `Tesla T4`。
  - **3 基质跨矩阵平均准确率对比（3 种子均值 ± 标准差）**：
    - `1D-CNN`（Track A 原始双通道 `(2, 358)`）：Scan **`73.65% ± 0.34%`** / Pellet **`77.73% ± 1.06%`**（黄芪 `62.47%` / `70.00%`，酸枣仁 `79.36%` / `84.33%`，天麻 `79.13%` / `78.86%`）
    - `1D-ResNet`（Track A 原始双通道 `(2, 358)`）：Scan **`76.25% ± 2.89%`** / Pellet **`80.43% ± 4.14%`**（黄芪 `61.54%` / `67.08%`，酸枣仁 `84.77%` / `89.67%`，天麻 `82.43%` / `84.55%`）
    - `Dual-View MLP`（Track B 同输入 3,222 维双视图）：Scan **`92.06% ± 1.21%`** / Pellet **`95.18% ± 1.47%`**（黄芪 `84.80%` / `89.58%`，酸枣仁 `94.59%` / `98.00%`，天麻 `96.78%` / `97.97%`）
    - *对照（主力端已锁定 Proposed SW-MCUVE-Manifold）*：Scan **`94.19%`** / Pellet **`97.50%`**（多种子稳定性：黄芪 `87.49% ± 0.24%`、酸枣仁 `95.26% ± 1.46%`、天麻 `98.51% ± 0.81%`）。
  - **如实标注细节**：黄芪单种子 `seed=42` 下 `Dual-View MLP` 达 `88.41%` / `93.75% (75/80)`，单点略高，但 3 种子均值降至 `84.80% ± 2.60%`，方差是原模型（`±0.24%`）的 10 倍以上。
  - **完整 JSON 已归档至**：`THz_TCM_Research/05_实验结果/模型结果/Colab_Round1_DL_Baselines.json`。

- **主力端核验与采纳结论**：`✅ 代码审计通过、零数据泄露，正式归档为 Rebuttal 储备`。
  - **代码逐行核查结论**：主力端实际读取并审阅了 `run_round1_dl_benchmark.py`（1–300 行），确认：（1）`extract_dual_view_3222` 与 `run_unified_double_nested_all.py` 完全一致；（2）`groups` 在 QC 前按 `local_i // 5` 生成；（3）外层与内层均使用 `StratifiedGroupKFold` 且带双层 `assert` 零重叠校验；（4）Track A 均值方差与 Track B `StandardScaler` 均仅在内层训练子折 `X_itr` 上 `fit`，测试折完全盲测。
  - **核心学术价值（Rebuttal 杀手锏）**：直接证明（1）小样本中药压片上端到端 1D-CNN/1D-ResNet 落后本文方法 **17.9–20.5 个百分点**；（2）将本文双视图 3,222 维表征喂给 MLP 后，深度学习直接暴涨 **+15.8% ~ +18.4%**，独立印证了双视图物理表征的核心价值；（3）即使同输入下，本文 SW-MCUVE-Manifold 仍在 3 基质均值和多种子稳定性上全面领先 `Dual-View MLP`。
  - **正文状态**：暂不修改已投 SAA 初稿，保留作一审返修（Rebuttal）强力证据。
