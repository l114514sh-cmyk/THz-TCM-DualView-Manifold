# 论文项目交接说明文档（Project Handoff Specification）

> 本文档用于在新对话/新协作者中**零丢失接管**本论文的全部代码、实验数据、投稿文件、环境约束与当前投稿状态。

---

## 1. 仓库与本地工作区信息

- **GitHub 公开仓库地址**：https://github.com/l114514sh-cmyk/THz-TCM-DualView-Manifold
- **SSH 推送地址**：`git@github.com:l114514sh-cmyk/THz-TCM-DualView-Manifold.git`
- **本地工作目录**：`e:\论文`（Windows / PowerShell）
- **Python 虚拟环境**：`e:\论文\THz_TCM_Research\01_原始实验数据\黄芪\.venv\Scripts\python.exe`（Python `3.12.14`）
  - 已安装核心库（见 `requirements.txt`）：`numpy==2.5.4`, `scipy==1.18.1`, `scikit-learn==1.9.1`, `pandas==3.1.0`, `matplotlib==3.11.2`, `openpyxl==3.1.5`, `Pillow>=10.0.0`。
  - **重要环境特性**：
    1. `.venv` 中**没有 `pip.exe` 也没有 `python-docx`**，因此所有 Word 文档均通过 `build_submission_docx.py` 内的**零依赖原生 OOXML（`zipfile` + XML）引擎**生成，修改论文时请直接修改该脚本并重新运行。
    2. 本地 Git 缺失 `git-remote-https.exe`，推送必须使用 **SSH**（已配置 Windows OpenSSH 与密钥 `C:\Users\jxgm\.ssh\id_ed25519`）。
    3. 13 个原始 `.xlsx` 文件仅保存在本地 `e:\论文\THz_TCM_Research\01_原始实验数据\{黄芪,酸枣仁,天麻}\`，已由 `.gitignore` 排除，**切勿修改或删除原始 `.xlsx`**。

---

## 2. 论文基本信息与作者名单（已锁定）

- **英文标题**：*Dual-View Terahertz Spectroscopy and Stability-Weighted Chemometrics for Classification of Traditional Chinese Medicinal Materials Across Distinct Botanical Matrices*
- **中文标题**：《双视图太赫兹光谱与稳定性加权化学计量学用于跨植物基质中药材分类研究》
- **目标期刊**：*Spectrochimica Acta Part A: Molecular and Biomolecular Spectroscopy (SAA)*（Elsevier，Full Length Article，已选 **Subscription 非 OA 免费发表**，Subject Area：`Chemometrics/Machine Learning`）
  - ⚠️ **避坑约束**：不可改投 *Applied Spectroscopy*（避免与二作朱子元基于共享数据集的另一篇投稿撞刊）。
- **5 位作者名单（全部归属重庆医科大学 / Chongqing Medical University, Chongqing 400016, China）**：
  1. **Sihao Liu（刘厶豪）** — 一作 | `L114514SH@gmail.com` | CRediT: Conceptualization, Methodology, Software, Formal analysis, Visualization, Writing – original draft.
  2. **Ziyuan Zhu（朱子元）** — 二作 | `zzy2630816871@gmail.com` | ORCID: `0009-0005-1153-4926` | CRediT: Investigation, Validation, Data curation, Writing – review & editing.
  3. **Hongjun Xiang（向宏俊）** — 三作 | `xhj2164618758@gmail.com` | CRediT: Formal analysis, Validation, Software, Writing – review & editing.
  4. **Wenjing Li（李文婧）** — 四作（贡献较轻） | `2712950900@qq.com` | CRediT: Data curation, Writing – review & editing.
  5. **Yin Shen*（沈印*）** — 五作兼通讯作者 | `shenyin285819016@126.com` | ORCID: `0000-0002-3221-7875` | CRediT: Resources, Supervision, Project administration, Writing – review & editing.
- **Cover Letter 要求**：必须始终以**通讯作者沈印（Yin Shen）名义**撰写。
- **数据采集者表述（重要已更新约束）**：
  - 论文与 README 中**已彻底清空“杨意艺 / Yiyi Yang / 西南大学 / Southwest University”**（0 残留），统一规范表述为 **`previous students in Yin Shen's research group`（沈印课题组历届学生）**。

---

## 3. 当前投稿状态与待办事项

- **初投已完成**：已于 2026-11-21 17:23 通过 Elsevier 新版投稿系统正式提交至 *Spectrochimica Acta Part A (SAA)*（上传文件：`Manuscript_EN_Submission.docx`、`Cover_Letter.docx`、`Highlights.docx`、`Supplementary_Material.docx`；无利益冲突已勾选；数据仓库填了本 GitHub 链接；未挂 SSRN 预印本）。
- **待处理事项**：初投上传时的 Word 稿件中仍含“杨意艺/西南大学”表述；随后已在本地和 GitHub 更新为 `previous students in Yin Shen's research group`（最新 `Manuscript_EN_Submission.docx` 已就绪）。正在联系通讯作者沈印老师：待其收到 `SAA-D-26-XXXXX` 确认邮件后，向编辑部请求退回稿件（`Send back to author`）并替换为最新 [Manuscript_EN_Submission.docx](THz_TCM_Research/06_论文写作/Manuscript_EN_Submission.docx)（或在返修阶段统一替换）。

---

## 4. 锁定实验事实与元数据（详表见 `06_论文写作/实验准备与环境元数据汇总表.md`）

- **制样工艺（实验者直接确认）**：纯药粉直接压片，**不加聚乙烯（PE）稀释剂、无额外烘箱烘干**；模具直径约 `10–15 mm`，保压时间 `10 s`，标称厚度 `~1.5 mm`；压片压力、过筛目数、逐片千分尺厚度未归档（已在 Table 1 与 Section 3.6 诚实披露）。
- **压片与扫描层级**：13 个 `.xlsx` 文件，每类 1 个商业批次，约 `20` 片压片 × **每片连续扫描 `5` 次**（`pellet_id = (class, local_idx // 5)`）。
- **测试仪器与环境**：透射式 Menlo `TERA K15`（1,550 nm，33 mW，干燥氮气吹扫 RH < 4%，292 K，空干燥氮气光路参比；注：设备与温湿度参数沿用同实验室模板，原始 `.xlsx` 未内嵌设备头信息）。
- **有效频段与网格**：原始 `折射率`/`吸收系数` 导出步长 `Δf = 0.002289 THz`；截窗 `0.22–1.04 THz`（`0.222015–1.039124 THz`）精确得 **`358` 频点**；吸收系数单位 **`cm⁻¹`**；1.04 THz 实测参比动态范围 `65.2–68.4 dB`，样品透射动态范围 `27.4–39.1 dB`（`Figure_S2_Dynamic_Range.png`）。

---

## 5. 锁定核心实验结果（统一单谱物理 QC + 压片分组双层嵌套 5 折 CV）

- **统一质控规则**：`1.2 <= mean(n) <= 2.6` 且 `mean(alpha) <= 55.0 cm⁻¹`，共保留 **`1,300 / 1,308` 条光谱（`262` 片压片）**：
  - **黄芪（*Astragali Radix*，4 标注产地）**：`397/403` 谱，`80` 片 → 扫描准确率 **`87.66%`**（`87.64% ± 3.08%`，Macro-F1 `0.8769`），**压片多数投票 `92.50%`（`74/80`）**；未分组随机 CV 参考 `93.20%`（揭示同片重复扫描泄漏虚高 `+5.54%`）。
  - **酸枣仁（*Ziziphi Spinosae Semen*，5 商业批次）**：`499/500` 谱，`100` 片 → 扫描准确率 **`96.39%`**（`96.40% ± 2.33%`，Macro-F1 `0.9640`），**压片多数投票 `100.00%`（`100/100`）**；配对压片簇 Bootstrap 显著优于 Dual-View PLS-DA（`+5.21%`, `p=0.0005`）、RF（`+6.01%`, `p=0.0005`）和 Hard MC-UVE-SVM（`+2.40%`, `p=0.0340`）。
  - **天麻（*Gastrodia elata*，4 标注产地）**：`404/405` 谱，`82` 片 → 扫描准确率 **`98.51%`**（`98.51% ± 0.51%`，Macro-F1 `0.9852`），**压片多数投票 `100.00%`（`82/82`）**。
  - **跨基质 3 矩阵均值**：扫描 **`94.19%`** / 压片投票 **`97.50%`**（在所有 Track A 原始双通道与 Track B 同输入 3,222 维双视图基线中排名第 1）。
- **泄露与稳健性审计**：
  - 差分盲测扰动探针：`0.000000e+00`（`0/77` 翻转）；
  - 30 次压片级 Y-scrambling 置换检验：三基质均 `0/30 >= obs`，经验 `p = 0.0323`；
  - 多种子稳定性（seeds `42, 100, 2026`）：黄芪 `87.49% ± 0.24%`、酸枣仁 `95.26% ± 1.46%`、天麻 `98.51% ± 0.81%`。
- **试探性 DFT 振动基准（B3LYP-D3(BJ)/6-31G(d)）**：毛蕊异黄酮（Calycosin）`0.552, 0.885 THz`；斯皮诺素（Spinosin）`0.605, 0.886, 0.979 THz`（与 MC-UVE 稳定性分布对齐，见 `Figure_7_MCUVE_DFT_Alignment.png`）。

---

## 6. 核心文件与脚本地图

| 路径 | 用途 |
| :--- | :--- |
| `THz_TCM_Research/04_Python数据处理/run_unified_double_nested_all.py` | 主实验总脚本：统一 QC、压片分组双层嵌套 CV、Track A/B 基线、消融实验、Bootstrap 检验及 300 DPI 主图生成 |
| `THz_TCM_Research/04_Python数据处理/run_strict_leakage_audit.py` | 4 阶段严格防泄露审计（差分探针、未清洗对比、多种子、30 次压片级 Y-scrambling） |
| `THz_TCM_Research/04_Python数据处理/plot_dynamic_range.py` | 直接从原始 `.xlsx` `频域` 表计算实测动态范围并绘制 `Figure_S2_Dynamic_Range.png` |
| `draw_pipeline.py` | 绘制 `Scheme_1_Pipeline.png` / `Pipeline_Flowchart_Clean.png` |
| `THz_TCM_Research/04_Python数据处理/build_submission_docx.py` | **核心文档构建器**：一键生成全部 6 份 Word 文档并自动校验英文摘要字数（210 词 ≤ 250）、Highlights（≤ 85 字符）和 39 篇文献严格顺序 `[1]..[39]` |
| `THz_TCM_Research/05_实验结果/模型结果/Unified_Double_Nested_Summary.json` | 锁定主实验机器可读结果汇总 |
| `THz_TCM_Research/05_实验结果/模型结果/Strict_Leakage_Audit_Report.json` | 锁定防泄露审计机器可读日志 |
| `THz_TCM_Research/06_论文写作/Manuscript_EN_Submission.docx` | 纯英文投稿终稿（0 中文、9 张 300 DPI 主图、5 张防截断三线表、39 篇文献） |
| `THz_TCM_Research/06_论文写作/Supplementary_Material.docx` | 纯英文补充材料（3 张附图 + Table S1/S2） |
| `THz_TCM_Research/06_论文写作/Cover_Letter.docx` & `Highlights.docx` | 沈印名义投稿信 + 5 条 ≤ 85 字符亮点 |
| `THz_TCM_Research/06_论文写作/Manuscript_ZH_Chinese.docx` & `Manuscript_Bilingual_Reference.docx` | 纯中文版 & 中英双语对照版 |
| `THz_TCM_Research/06_论文写作/Submission_Figures/` | 12 张 300 DPI 投稿高清图独立汇总目录 |
| `THz_TCM_Research/06_论文写作/实验准备与环境元数据汇总表.md` | 实验准备、测试环境、确定性分级与 13 个原始文件全明细 |

---

## 7. 给新对话的硬性规范（修改论文时务必遵守）

1. **严禁编造**任何实验参数、样本溯源或参考文献；新增文献必须先联网核实 DOI / 卷期页码。
2. **表格排版**：保持 `keepNext + cantSplit`（保证表格绝不跨页截断），**不要**强行前后插分页符留白（`standalone_page=False`）。
3. **英文投稿文件纯度**：`Manuscript_EN_Submission.docx`、`Supplementary_Material.docx`、`Cover_Letter.docx`、`Highlights.docx` 必须保持 **0 中文字符**，Abstract ≤ 250 词，Highlights 每条 ≤ 85 字符，参考文献严格按首次出现顺序 `[1]..[N]` 编号。
4. **公共脚本路径**：所有脚本使用**项目相对路径**，不得写死个人绝对路径；推送 GitHub 使用 SSH。
