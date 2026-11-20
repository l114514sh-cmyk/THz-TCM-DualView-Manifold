import os
import json
import zipfile
from PIL import Image
from xml.sax.saxutils import escape

ROOT_DIR = r"e:\论文"
JSON_PATH = os.path.join(ROOT_DIR, "THz_TCM_Research", "05_实验结果", "模型结果", "Unified_Double_Nested_Summary.json")
AUDIT_PATH = os.path.join(ROOT_DIR, "THz_TCM_Research", "05_实验结果", "模型结果", "Strict_Leakage_Audit_Report.json")
OUT_DIR = os.path.join(ROOT_DIR, "THz_TCM_Research", "06_论文写作")
os.makedirs(OUT_DIR, exist_ok=True)

with open(JSON_PATH, "r", encoding="utf-8") as f:
    DATA = json.load(f)
with open(AUDIT_PATH, "r", encoding="utf-8") as f:
    AUDIT = json.load(f)

HQ = DATA["Astragali_Radix"]
SZ = DATA["Ziziphi_Spinosae_Semen"]
TM = DATA["Gastrodia_elata"]


# ==============================================================================
# Native OOXML (.docx) Builder: Bilingual (EN+ZH), Embedded 300 DPI PNGs, 3-Line Tables
# ==============================================================================
class DocxBuilder:
    def __init__(self):
        self.body_parts = []
        self.media_files = []
        self._img_counter = 0

    @staticmethod
    def _run(text, bold=False, italic=False, size_pt=11.5, color=None):
        rpr = ['<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" w:eastAsia="SimSun"/>']
        if bold:
            rpr.append('<w:b/>')
        if italic:
            rpr.append('<w:i/>')
        rpr.append(f'<w:sz w:val="{int(size_pt * 2)}"/><w:szCs w:val="{int(size_pt * 2)}"/>')
        if color:
            rpr.append(f'<w:color w:val="{color}"/>')
        t = escape(str(text))
        return f'<w:r><w:rPr>{"".join(rpr)}</w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'

    def add_para(self, runs_or_text, align="both", space_before=0, space_after=100, line=320,
                 first_line_indent=0, bold=False, italic=False, size_pt=11.5, color=None, keep_next=False):
        ppr = [f'<w:spacing w:before="{space_before}" w:after="{space_after}" w:line="{line}" w:lineRule="auto"/>']
        if align:
            ppr.append(f'<w:jc w:val="{align}"/>')
        if first_line_indent:
            ppr.append(f'<w:ind w:firstLine="{first_line_indent}"/>')
        if keep_next:
            ppr.append('<w:keepNext/>')
        inner = self._run(runs_or_text, bold=bold, italic=italic, size_pt=size_pt, color=color) if isinstance(runs_or_text, str) else "".join(runs_or_text)
        self.body_parts.append(f'<w:p><w:pPr>{"".join(ppr)}</w:pPr>{inner}</w:p>')

    def add_bilingual_title(self, en_title, zh_title):
        self.add_para(en_title, align="center", space_before=80, space_after=80, line=300, bold=True, size_pt=14.5)
        self.add_para(zh_title, align="center", space_before=0, space_after=160, line=300, bold=True, size_pt=13, color="2B4C7E")

    def add_bilingual_heading(self, en_text, zh_text, level=1):
        sz_en = 13 if level == 1 else 11.5
        sz_zh = 11.5 if level == 1 else 10.5
        sb = 220 if level == 1 else 150
        self.add_para(en_text, align="left", space_before=sb, space_after=30, line=280, bold=True, italic=(level == 2), size_pt=sz_en, keep_next=True)
        self.add_para(zh_text, align="left", space_before=0, space_after=90, line=260, bold=True, size_pt=sz_zh, color="2B4C7E", keep_next=True)

    def add_bilingual_para(self, en_text, zh_text, first_line_indent=420):
        self.add_para(en_text, align="both", space_before=20, space_after=50, line=310, first_line_indent=first_line_indent, size_pt=11)
        self.add_para(zh_text, align="both", space_before=0, space_after=130, line=300, first_line_indent=first_line_indent, size_pt=10.5, color="333333")

    def add_bilingual_bullet(self, en_text, zh_text):
        self.add_para("•  " + en_text, align="both", space_before=20, space_after=35, line=290, size_pt=10.8)
        self.add_para("   " + zh_text, align="both", space_before=0, space_after=95, line=280, size_pt=10.2, color="333333")

    def add_equation(self, eq_text, eq_num):
        eq_r = self._run(eq_text, italic=True, size_pt=10.8)
        num_r = self._run(f"({eq_num})", bold=False, size_pt=10.8)
        tbl = (
            '<w:tbl>'
            '<w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:jc w:val="center"/>'
            '<w:tblBorders><w:top w:val="none"/><w:bottom w:val="none"/><w:left w:val="none"/>'
            '<w:right w:val="none"/><w:insideH w:val="none"/><w:insideV w:val="none"/></w:tblBorders></w:tblPr>'
            '<w:tblGrid><w:gridCol w:w="8260"/><w:gridCol w:w="1100"/></w:tblGrid>'
            '<w:tr><w:trPr><w:cantSplit/></w:trPr>'
            f'<w:tc><w:tcPr><w:tcW w:w="8260" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:before="45" w:after="45" w:line="250" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>{eq_r}</w:p></w:tc>'
            f'<w:tc><w:tcPr><w:tcW w:w="1100" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:before="45" w:after="45" w:line="250" w:lineRule="auto"/><w:jc w:val="right"/></w:pPr>{num_r}</w:p></w:tc>'
            '</w:tr></w:tbl>'
        )
        self.body_parts.append(tbl)

    def add_page_break(self):
        self.body_parts.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def add_image(self, img_path, width_inches=5.6, max_height_inches=7.4,
                  en_prefix="", en_caption="", zh_prefix="", zh_caption=""):
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Missing figure file: {img_path}")
        with Image.open(img_path) as im:
            px_w, px_h = im.size
        aspect = px_h / float(px_w)
        w_in = width_inches
        h_in = w_in * aspect
        if h_in > max_height_inches:
            h_in = max_height_inches
            w_in = h_in / aspect
        cx = int(round(w_in * 914400))
        cy = int(round(h_in * 914400))

        self._img_counter += 1
        rel_id = f"rIdImg{self._img_counter}"
        arc_name = f"media/image{self._img_counter}.png"
        self.media_files.append((rel_id, arc_name, img_path))

        drawing_xml = (
            f'<w:p><w:pPr><w:spacing w:before="120" w:after="50"/><w:jc w:val="center"/><w:keepNext/></w:pPr>'
            '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{self._img_counter}" name="Picture {self._img_counter}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:nvPicPr><pic:cNvPr id="{self._img_counter}" name="{escape(os.path.basename(img_path))}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic>'
            '</wp:inline></w:drawing></w:r></w:p>'
        )
        self.body_parts.append(drawing_xml)
        if en_caption:
            self.add_para([self._run(en_prefix, bold=True, size_pt=9.5), self._run(en_caption, size_pt=9.5)],
                          align="both", space_before=10, space_after=35, line=240, keep_next=bool(zh_caption))
        if zh_caption:
            self.add_para([self._run(zh_prefix, bold=True, size_pt=9.5, color="2B4C7E"), self._run(zh_caption, size_pt=9.5, color="333333")],
                          align="both", space_before=0, space_after=150, line=240)

    def add_three_line_table(self, caption, headers, rows, col_widths_twips=None, bold_last_rows=None, note=None, is_zh=False):
        cap_color = "2B4C7E" if is_zh else None
        self.add_para(caption, align="left", space_before=140, space_after=60, line=250, bold=True, size_pt=10, color=cap_color, keep_next=True)
        bold_last_rows = set(bold_last_rows or [])
        n_cols = len(headers)
        if col_widths_twips is None:
            col_widths_twips = [9360 // n_cols] * n_cols

        tbl_pr = (
            '<w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:jc w:val="center"/>'
            '<w:tblBorders>'
            '<w:top w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
            '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
            '<w:left w:val="none"/><w:right w:val="none"/><w:insideH w:val="none"/><w:insideV w:val="none"/>'
            '</w:tblBorders>'
            '<w:tblCellMar><w:top w:w="45" w:type="dxa"/><w:bottom w:w="45" w:type="dxa"/>'
            '<w:left w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar>'
            '</w:tblPr>'
        )
        grid = '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{w}"/>' for w in col_widths_twips) + '</w:tblGrid>'

        def make_row(cells, is_header=False, is_bold=False):
            tr_cells = []
            for idx, (val, w) in enumerate(zip(cells, col_widths_twips)):
                tc_borders = '<w:tcBorders><w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/></w:tcBorders>' if is_header else ''
                align = "left" if idx == 0 else "center"
                r = self._run(val, bold=(is_header or is_bold), size_pt=9.0)
                tr_cells.append(
                    f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{tc_borders}<w:vAlign w:val="center"/></w:tcPr>'
                    f'<w:p><w:pPr><w:spacing w:before="15" w:after="15" w:line="220" w:lineRule="auto"/>'
                    f'<w:jc w:val="{align}"/></w:pPr>{r}</w:p></w:tc>'
                )
            hdr_tag = '<w:tblHeader/>' if is_header else ''
            return f'<w:tr><w:trPr>{hdr_tag}<w:cantSplit/></w:trPr>{"".join(tr_cells)}</w:tr>'

        tr_list = [make_row(headers, is_header=True)]
        for r_idx, row in enumerate(rows):
            tr_list.append(make_row(row, is_header=False, is_bold=(r_idx in bold_last_rows)))
        self.body_parts.append(f'<w:tbl>{tbl_pr}{grid}{"".join(tr_list)}</w:tbl>')
        if note:
            self.add_para(note, align="left", space_before=30, space_after=110, line=230, italic=(not is_zh), size_pt=9.0, color=("333333" if is_zh else None))
        else:
            self.add_para("", align="left", space_before=0, space_after=60, line=200, size_pt=8)

    def save(self, out_path):
        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '</Types>'
        )
        rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>'
        )
        img_rels = "".join(
            f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{arc}"/>'
            for rid, arc, _ in self.media_files
        )
        doc_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            f'{img_rels}</Relationships>'
        )
        styles_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:docDefaults><w:rPrDefault><w:rPr>'
            '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" w:eastAsia="SimSun"/>'
            '<w:sz w:val="22"/><w:szCs w:val="22"/>'
            '</w:rPr></w:rPrDefault></w:docDefaults>'
            '</w:styles>'
        )
        sect_pr = (
            '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
            '<w:pgMar w:top="1260" w:right="1260" w:bottom="1260" w:left="1260" w:header="720" w:footer="720" w:gutter="0"/>'
            '</w:sectPr>'
        )
        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
            f'<w:body>{"".join(self.body_parts)}{sect_pr}</w:body>'
            '</w:document>'
        )
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", content_types)
            z.writestr("_rels/.rels", rels)
            z.writestr("word/_rels/document.xml.rels", doc_rels)
            z.writestr("word/styles.xml", styles_xml)
            z.writestr("word/document.xml", doc_xml)
            for _, arc_name, src_path in self.media_files:
                z.write(src_path, f"word/{arc_name}")


# ==============================================================================
# 1. Build Highlights.docx (<= 85 chars per bullet)
# ==============================================================================
HIGHLIGHTS = [
    "Unified dual-view THz-TDS framework authenticates root, seed, and tuber TCMs.",
    "Intra-sample SNV and amplitude views adapt to fibrous and lipid-rich matrices.",
    "Strict double-nested 5-fold CV achieves 93.20% (root) and 97.40% (seed).",
    "Locked cross-matrix transfer reaches 99.75% accuracy on Gastrodia elata.",
    "Zero-leakage audits (Y-scrambling & multi-seed) and DFT benchmarks validate rigor."
]
for idx, h in enumerate(HIGHLIGHTS, 1):
    assert len(h) <= 85, f"Highlight {idx} exceeds 85 chars ({len(h)}): {h}"

h_doc = DocxBuilder()
h_doc.add_para("Highlights", align="center", space_before=100, space_after=160, bold=True, size_pt=14)
for h in HIGHLIGHTS:
    h_doc.add_para("•  " + h, align="left", space_before=30, space_after=80, line=300, size_pt=11.5)
h_path = os.path.join(OUT_DIR, "Highlights.docx")
h_doc.save(h_path)
print(f"[OK] Saved {h_path}")


# ==============================================================================
# 2. Build Cover_Letter.docx (Updated with Exact Authors, Chongqing Medical University & Email)
# ==============================================================================
TITLE_EN = (
    "Cross-Matrix Authentication and Origin Traceability of Traditional Chinese Medicines "
    "via Dual-View Terahertz Spectroscopy, Stability-Weighted Manifold Learning, and "
    "Quantum Chemical Vibrational Benchmarks"
)
TITLE_ZH = "基于双视图太赫兹光谱、稳定性加权流形学习与量子化学振动基准的中药材跨基质鉴别与产地溯源研究"

c_doc = DocxBuilder()
c_doc.add_para("Date: November 20, 2026", align="right", space_after=140, size_pt=11.5)
c_doc.add_para("To:\nEditor-in-Chief\nSpectrochimica Acta Part A: Molecular and Biomolecular Spectroscopy", align="left", space_after=160, line=280, size_pt=11.5)
c_doc.add_para("Dear Editor-in-Chief,", align="left", space_after=120, size_pt=11.5)
c_doc.add_para(
    f'On behalf of my co-authors (Sihao Liu and Ziyuan Zhu), I am pleased to submit our original research '
    f'manuscript entitled "{TITLE_EN}" for consideration for publication as a Research Article in Spectrochimica Acta '
    'Part A: Molecular and Biomolecular Spectroscopy.',
    first_line_indent=420, size_pt=11.5
)
c_doc.add_para(
    "Non-destructive authentication of Traditional Chinese Medicines (TCMs) across diverse botanical tissues remains "
    "challenging because fibrous roots, lipid-rich seeds, and starchy tubers exhibit contrasting terahertz (THz) "
    "scattering and dielectric physics. In this study, we establish a fully locked, leak-free Dual-View Stability-Weighted "
    "MC-UVE Manifold (Dual-View SW-MCUVE-Manifold) framework evaluated under strict double-nested 5-fold cross-validation "
    "across 1,301 post-QC dual-channel THz-TDS spectra (0.22–1.04 THz) acquired on a Menlo Systems TERA K15 spectrometer:",
    first_line_indent=420, size_pt=11.5
)
c_doc.add_para(
    "•  Single-Spectrum Physical QC & Dual-View Physics: Combining single-spectrum optical QC (1.2 ≤ n̄ ≤ 2.6, ᾱ ≤ 55 cm⁻¹) "
    "with intra-sample scattering-invariant SNV morphology and amplitude-preserving dielectric views eliminates "
    "cross-sample leakage and resolves the physical trade-off between fibrous roots and lipid-rich seeds.",
    space_after=80, size_pt=11
)
c_doc.add_para(
    f"•  Strict Double-Nested Dominance & Zero-Leakage Audits: The locked pipeline achieves {HQ['proposed']['acc']:.2f}% "
    f"({HQ['proposed']['mean']:.2f}% ± {HQ['proposed']['sd']:.2f}%) on 4-origin Astragali Radix roots (n = {HQ['n_samples']}), "
    f"{SZ['proposed']['acc']:.2f}% ({SZ['proposed']['mean']:.2f}% ± {SZ['proposed']['sd']:.2f}%) on 5-format commercial "
    f"Ziziphi Spinosae Semen seeds (n = {SZ['n_samples']}), and {TM['proposed']['acc']:.2f}% "
    f"({TM['proposed']['mean']:.2f}% ± {TM['proposed']['sd']:.2f}%) upon unmodified cross-matrix transfer to 4-origin "
    f"Gastrodia elata tubers (n = {TM['n_samples']}). Differential perturbation probes (0.00e+00 deviation), multi-seed "
    "repeats (93.12% / 97.20% / 99.67%), and Y-scrambling permutation tests (21.41% / 18.80% / 26.98%) confirm zero leakage.",
    space_after=80, size_pt=11
)
c_doc.add_para(
    "•  Quantum Chemical Vibrational Benchmarks: Dispersion-corrected B3LYP-D3(BJ)/6-31G(d) calculations on calycosin "
    "(aglycone core) and spinosin provide physically grounded intramolecular THz vibrational reference modes.",
    space_after=120, size_pt=11
)
c_doc.add_para(
    "This manuscript has not been published previously and is not under consideration elsewhere. All authors have read "
    "and approved the manuscript and declare no competing interests.",
    first_line_indent=420, size_pt=11.5
)
c_doc.add_para("Thank you very much for your time and consideration.", space_after=160, size_pt=11.5)
c_doc.add_para(
    "Sincerely yours,\n\nYin Shen (Corresponding Author)\nChongqing Medical University, Chongqing, China\n"
    "E-mail: shenyin285819016@126.com\nORCID: https://orcid.org/0000-0002-3221-7875\n\n"
    "Co-authors:\n"
    "Sihao Liu (First Author, E-mail: L114514SH@gmail.com)\n"
    "Ziyuan Zhu (Second Author, E-mail: zzy2630816871@gmail.com, ORCID: https://orcid.org/0009-0005-1153-4926)",
    align="left", line=270, size_pt=11
)
c_path = os.path.join(OUT_DIR, "Cover_Letter.docx")
c_doc.save(c_path)
print(f"[OK] Saved {c_path}")


# ==============================================================================
# 3. Build Bilingual Manuscript_Final.docx (中英文逐段对照，完全对齐参考文档格式)
# ==============================================================================
m = DocxBuilder()
m.add_bilingual_title(TITLE_EN, TITLE_ZH)
m.add_para("Sihao Liu¹, Ziyuan Zhu¹, Yin Shen¹*", align="center", space_after=30, bold=True, size_pt=11.5)
m.add_para("刘厶豪¹，朱子元¹，沈印¹*", align="center", space_after=50, size_pt=10.5, color="2B4C7E")
m.add_para(
    "¹ Chongqing Medical University, Chongqing, China (重庆医科大学)\n"
    "*Corresponding author: Yin Shen (E-mail: shenyin285819016@126.com; ORCID: https://orcid.org/0000-0002-3221-7875)\n"
    "First author: Sihao Liu (E-mail: L114514SH@gmail.com) | "
    "Second author: Ziyuan Zhu (E-mail: zzy2630816871@gmail.com; ORCID: https://orcid.org/0009-0005-1153-4926)",
    align="center", space_after=180, size_pt=9.5, line=240
)

# --- Abstract ---
m.add_bilingual_heading("Abstract", "摘要（中英文逐段对照）", level=1)
m.add_bilingual_para(
    "Established authentication of Traditional Chinese Medicines (TCMs) relies on morphological, microscopic, and "
    "chromatographic testing. We developed a unified, mathematically leak-free Dual-View Stability-Weighted Monte Carlo "
    "Uninformative Variable Elimination Manifold (Dual-View SW-MCUVE-Manifold) strategy for complementary terahertz "
    "time-domain spectroscopy (THz-TDS) discrimination across distinct botanical tissues. Dual-channel absorption α(ω) "
    "and refractive-index n(ω) exports (0.22–1.04 THz, 358 frequency coordinates per channel) acquired on a Menlo "
    "Systems TERA K15 spectrometer covered 1,308 raw polyethylene-diluted herbal pellets spanning fibrous roots "
    "(Astragali Radix, 4 origins, raw n = 403), lipid-rich seeds (Ziziphi Spinosae Semen, 5 commercial formats/batches, "
    "raw n = 500), and orchid tubers (Gastrodia elata, 4 origins, raw n = 405). Following single-spectrum physical "
    "quality control (1.2 ≤ n̄ ≤ 2.6 and ᾱ ≤ 55.0 cm⁻¹, requiring zero cross-sample statistics; 1,301 post-QC specimens "
    "retained), each spectrum is decomposed strictly within its own frequency axis into a scattering-invariant "
    "intra-sample SNV morphology view and an amplitude-preserving dielectric view (3,222 features). Within strict "
    "double-nested 5-fold cross-validation (outer 5-fold blind test; inner 3-fold tuning), full-rank MC-UVE constructs "
    "an anisotropic stability-weighted RBF kernel augmented by a subspace-purified Ledoit–Wolf shrinkage LDA manifold. "
    f"The locked pipeline achieved {HQ['proposed']['acc']:.2f}% ({HQ['proposed']['mean']:.2f}% ± {HQ['proposed']['sd']:.2f}%, "
    f"Macro-F1 = {HQ['proposed']['macro_f1']:.4f}) on Astragali Radix (n = {HQ['n_samples']}) and {SZ['proposed']['acc']:.2f}% "
    f"({SZ['proposed']['mean']:.2f}% ± {SZ['proposed']['sd']:.2f}%, Macro-F1 = {SZ['proposed']['macro_f1']:.4f}) on "
    f"Ziziphi Spinosae Semen (n = {SZ['n_samples']}), outperforming PLS-DA, Random Forest, full-spectrum RBF-SVM, and "
    "hard-threshold MC-UVE-SVM. Unmodified cross-matrix transfer to Gastrodia elata (n = 404) reached "
    f"{TM['proposed']['acc']:.2f}% ({TM['proposed']['mean']:.2f}% ± {TM['proposed']['sd']:.2f}%, Macro-F1 = "
    f"{TM['proposed']['macro_f1']:.4f}). Four zero-leakage audits—unfiltered raw-set retention (92.80% / 97.40% / "
    "99.26%), differential blind-test perturbation (0.00e+00 deviation), multi-seed stability (93.12% / 97.20% / "
    "99.67%), and Y-scrambling permutation (collapsing to 21.41% / 18.80% / 26.98%)—confirmed airtight generalization. "
    "Dispersion-corrected DFT (B3LYP-D3(BJ)/6-31G(d)) calculations on calycosin and spinosin provide intramolecular "
    "vibrational benchmarks supporting the physical interpretability of the 0.55–0.98 THz region.",

    "中药材的既有鉴定主要依赖性状、显微与色谱检验。本研究提出一种统一、数学上严格零泄漏的双视图稳定性加权蒙特卡洛无信息变量剔除流形（Dual-View SW-MCUVE-Manifold）策略，用于跨越不同植物组织基质的太赫兹时域光谱（THz-TDS）辅助判别。基于德国 Menlo Systems TERA K15 系统采集的双通道吸收系数 α(ω) 与折射率 n(ω) 导出光谱（0.22–1.04 THz，每通道 358 个频点），共覆盖 1,308 份掺入聚乙烯（PE）稀释剂压制的药材压片，涵盖纤维根茎类黄芪（4 产地，原始 n = 403）、油脂种子类酸枣仁（5 商业规格/批次，原始 n = 500）及兰科块茎类天麻（4 产地，原始 n = 405）。经零跨样本统计依赖的单谱物理质控（1.2 ≤ n̄ ≤ 2.6 且 ᾱ ≤ 55.0 cm⁻¹，质控后保留 1,301 份样品）后，每条光谱严格在其自身频率轴内分解为去散射单样本 SNV 形态视图与保幅介电视图（共 3,222 维特征）。在真·双层严格嵌套 5 折交叉验证（外层 5 折绝对盲测、内层 3 折超参寻优）内，满秩 MC-UVE 构建各向异性稳定性加权 RBF 核，并融合子空间净化的 Ledoit–Wolf 收缩 LDA 判别流形。完全锁死的统一流程在黄芪（n = 397）与酸枣仁（n = 500）上分别取得 93.20%（93.19% ± 2.73%，Macro-F1 = 0.9321）与 97.40%（97.40% ± 1.62%，Macro-F1 = 0.9740）的无偏盲测准确率，全面优于 PLS-DA、随机森林、全谱 RBF-SVM 与硬截断 MC-UVE-SVM；一字不改跨基质迁移至天麻（n = 404）更达到 99.75%（99.75% ± 0.50%，Macro-F1 = 0.9975）。四重无泄漏审计——原始未清洗全集评估（92.80% / 97.40% / 99.26%）、盲测微分扰动探针（0.00e+00 偏差）、三随机种子稳定性（93.12% / 97.20% / 99.67%）及 Y-标签随机置换检验（坍塌至 21.41% / 18.80% / 26.98%）——严密验证了零泄漏泛化性能。对毛蕊异黄酮与斯皮诺素的色散校正 DFT（B3LYP-D3(BJ)/6-31G(d)）计算为 0.55–0.98 THz 判别频段提供了分子内振动基准参考。",
    first_line_indent=0
)
m.add_para([m._run("Keywords: ", bold=True, size_pt=10.5),
            m._run("Terahertz time-domain spectroscopy; Traditional Chinese medicine; Cross-matrix authentication; Double-nested cross-validation; Anisotropic stability kernel; Density functional theory", size_pt=10.5)],
           space_after=30)
m.add_para([m._run("关键词：", bold=True, size_pt=10.5, color="2B4C7E"),
            m._run("太赫兹时域光谱；中药材；跨基质鉴别；双层嵌套交叉验证；各向异性稳定性核；密度泛函理论", size_pt=10.5, color="333333")],
           space_after=160)

# --- 1. Introduction ---
m.add_bilingual_heading("1. Introduction", "1. 引言", level=1)
m.add_bilingual_para(
    "Reliable identification of Traditional Chinese Medicines (TCMs) underpins clinical efficacy, safety, and quality "
    "control across herbal supply chains [1–3,37]. Established pharmacopoeial practice integrates morphological, "
    "microscopic, and chromatographic analyses (HPLC, GC–MS) [2,6,37]. Astragali Radix (dried root of Astragalus "
    "membranaceus, Huangqi) and Ziziphi Spinosae Semen (dried ripe seed of Ziziphus jujuba var. spinosa, Suanzaoren) "
    "represent two contrasting botanical matrices—lignified fibrous roots versus lipid-rich seeds—whose secondary "
    "metabolite profiles vary with provenance, microclimate, and commercial storage [3,37]. While chromatographic "
    "assays deliver high chemical selectivity, they are destructive, solvent-intensive, and slow, motivating rapid, "
    "non-destructive complementary spectroscopic techniques [2,6,11].",

    "中药材的可靠鉴别是保障临床疗效、用药安全及供应链质量控制的基础[1–3,37]。现行药典规范综合采用性状、显微及色谱检验（HPLC、GC–MS）[2,6,37]。黄芪（豆科植物干燥根）与酸枣仁（鼠李科干燥成熟种子）分别代表木质化粗纤维根茎与富含油脂的种子两类迥异的植物基质，其次生代谢物谱随地理产地、气候微环境及商品流通储存条件显著波动[3,37]。传统色谱法虽具高化学选择性，但具有破坏性、依赖有机溶剂且耗时较长，亟需发展快速、无损的互补光谱分析技术[2,6,11]。"
)
m.add_bilingual_para(
    "Terahertz time-domain spectroscopy (THz-TDS, 0.1–3.0 THz) coherently measures both amplitude and phase, "
    "simultaneously yielding paired refractive-index n(ω) and absorption-coefficient α(ω) spectra without ionizing "
    "radiation [4,5,11–14]. Because THz photon energies (0.4–12 meV) match low-frequency intramolecular skeletal "
    "torsions, conformational flexing, and collective hydrogen-bond or lattice vibrations [7–10,15,16], THz-TDS has "
    "been widely explored for pharmaceutical polymorphs, crystallinity analysis, and herbal discrimination [1,3,13–15,18].",

    "太赫兹时域光谱（THz-TDS，0.1–3.0 THz）可相干探测电磁波的振幅与相位，在无电离辐射条件下一次测量即可同时反演配对的折射率 n(ω) 与吸收系数 α(ω) 光谱[4,5,11–14]。由于太赫兹光子能量（0.4–12 meV）恰好对应低频分子内骨架扭转、构象摆动及氢键/晶格集体振动[7–10,15,16]，THz-TDS 已被广泛探索于药物多晶型识别、结晶度表征及中药材鉴别[1,3,13–15,18]。"
)
m.add_bilingual_para(
    "However, three methodological gaps restrict THz-TDS chemometrics from becoming a standardized multi-matrix tool. "
    "First, most published workflows are tuned to a single herbal matrix [3,6]. Compressed pellets of fibrous roots "
    "suffer strong inter-pellet multiplicative Mie scattering driven by heterogeneous fiber packing, whereas lipid-rich "
    "seeds carry discriminative macroscopic dielectric baselines governed by fatty-oil and moisture content. Standard "
    "normal variate (SNV) normalization [20] cancels multiplicative scattering in roots but erases absolute dielectric "
    "amplitude in seeds. Second, applying global scaling, variable selection (UVE [21], MC-UVE [22], CARS [23], or "
    "Random Forest [28]), or hyperparameter tuning outside cross-validation introduces data leakage and selection "
    "bias [29,30], while hard-threshold binary masks paired with isotropic Euclidean RBF-SVM [27] weight noisy edge "
    "bands identically to dominant resonances. Third, chemometric boundaries are either left uninterpreted or "
    "over-attributed to gas-phase single-molecule density functional theory (DFT) peaks despite trace metabolite "
    "abundance in crude herbal powders.",

    "然而，三大方法学瓶颈限制了太赫兹化学计量学向标准化跨基质工具的转化。首先，现有流程大多针对单一药材基质特化调优[3,6]：纤维根茎压片受限于纤维堆积孔隙度波动，存在剧烈的乘性米氏散射；而油脂种子则富含由脂肪油与水分决定的宏观绝对介电幅值差异。标准正态变量变换（SNV）[20]虽能约分消除根茎中的乘性散射，却会抹平种子中的绝对介电幅值。其次，在交叉验证外部执行全局标准化、特征选择（UVE[21]、MC-UVE[22]、CARS[23]或随机森林[28]）或超参数网格搜索会引入严重的数据泄漏与选择偏置[29,30]；而传统硬截断二值掩码配合各向同性欧氏 RBF-SVM[27]，使边缘噪声频点与核心共振峰享有相同权重。第三，既有模型往往缺乏物理解释，或在未测纯标准品时将粗粉宏观吸收过度归因于气相单分子密度泛函理论（DFT）振动峰。"
)
m.add_bilingual_para(
    "To establish an unbroken logical chain from standardized pellet metrology to leak-free statistical learning and "
    "transparent quantum chemical benchmarking, we introduce a locked Dual-View SW-MCUVE-Manifold framework. "
    "Specifically: (i) standardized ball-milling, polyethylene-diluted hydraulic pelletizing, and single-spectrum "
    "physical QC (1.2 ≤ n̄ ≤ 2.6, ᾱ ≤ 55.0 cm⁻¹) filter optical extraction faults without cross-sample statistics; "
    "(ii) strictly intra-sample dual-view preprocessing couples scattering-invariant SNV morphology with "
    "amplitude-preserving Savitzky–Golay (SG) dielectric envelopes and derivatives [19,20]; (iii) full-rank MC-UVE "
    "inside each training fold builds a stability-weighted anisotropic RBF kernel augmented by a subspace-purified "
    "Ledoit–Wolf shrinkage LDA manifold [26]; (iv) four rigorous zero-leakage audits validate performance across "
    "roots (Astragali Radix), seeds (Ziziphi Spinosae Semen), and independent orchid tuber cross-matrix transfer "
    "(Gastrodia elata); and (v) B3LYP-D3(BJ)/6-31G(d) calculations [31–35] on calycosin and spinosin provide "
    "intramolecular vibrational benchmarks.",

    "为打通从标准化压片制样、零泄漏统计学习到透明量子化学基准的完整逻辑链条，本文提出统一锁死的 Dual-View SW-MCUVE-Manifold 框架：（i）通过规范化的球磨、掺聚乙烯（PE）液压压片与零跨样本依赖的单谱物理质控（1.2 ≤ n̄ ≤ 2.6，ᾱ ≤ 55.0 cm⁻¹）拦截光学反演故障；（ii）严格在单条光谱内部构建“去散射 SNV 形态 + 保幅介电包络/导数”双视图特征[19,20]；（iii）在各训练折内部利用满秩 MC-UVE 构建稳定性加权各向异性 RBF 核，并耦合子空间净化的 Ledoit–Wolf 收缩 LDA 流形[26]；（iv）在黄芪（根）、酸枣仁（种子）及天麻（兰科块茎跨基质独立验证）上实施四重严苛无泄漏审计；（v）结合毛蕊异黄酮与斯皮诺素的 B3LYP-D3(BJ)/6-31G(d) 计算[31–35]建立分子内低频振动基准。"
)

# --- 2. Experimental and analytical methods ---
m.add_bilingual_heading("2. Experimental and analytical methods", "2. 实验与分析方法", level=1)

m.add_bilingual_heading("2.1. Materials, standardized pulverization–pelletizing workflow, and THz-TDS acquisition",
                        "2.1. 实验材料、标准磨粉压片流程与太赫兹光谱采集", level=2)
m.add_bilingual_para(
    "This study analyzed 1,308 raw medicinal-material specimens purchased from traditional Chinese medicine pharmacies "
    "and organized into three botanically distinct matrices according to their commercial labels and pharmacopoeial "
    "categories [37] (independent botanical authentication was not separately performed): "
    "(1) Fibrous root matrix — Astragali Radix (raw n = 403 pellets) from four recorded origins: Datong, Shanxi "
    "(Datong (SX), n = 103), Guyang, Inner Mongolia (Guyang (IM), n = 100), Qujing, Yunnan (Qujing (YN), n = 100), "
    "and Gansu (Gansu (GS), n = 100); "
    "(2) Lipid-rich seed matrix — Ziziphi Spinosae Semen (raw n = 500 pellets, 100 per group) spanning five commercial "
    "circulation specifications and packaging formats: Boxed Hebei (Boxed (HB)), Shijiazhuang/Bozhou lot (SJZ/BZ), "
    "Bulk-Bag, Bulk-50g, and Tongrentang Bozhou (Tongrentang (AH)); and "
    "(3) Starchy orchid tuber matrix (reserved strictly for independent cross-matrix methodological validation) — "
    "Gastrodia elata (raw n = 405 pellets) from four recorded origins: Bozhou, Anhui (Bozhou (AH), n = 103), "
    "Leishan, Guizhou (Leishan (GZ), n = 100), Changbai Mountain, Jilin (Changbai (JL), n = 102), and Yunnan "
    "(Yunnan (YN), n = 100).",

    "本研究共分析从中药房采购的 1,308 份原始药材样品，依据商品标签与药典分类归为三类植物学基质[37]（未另行开展独立植物学鉴定）：（1）纤维根茎类——黄芪（原始 n = 403 片），来自山西大同（Datong (SX)，103 片）、内蒙古固阳（Guyang (IM)，100 片）、云南曲靖（Qujing (YN)，100 片）和甘肃（Gansu (GS)，100 片）四个记录产地；（2）油脂种子类——酸枣仁（原始 n = 500 片，每组 100 片），涵盖盒养河北（Boxed (HB)）、石家庄/亳州信盛常（SJZ/BZ）、散装大袋（Bulk-Bag）、散装 50 g（Bulk-50g）和同仁堂亳州（Tongrentang (AH)）五个商业流通规格/批次；（3）淀粉块茎类（严格用于跨物种/跨基质独立方法学验证）——天麻（原始 n = 405 片），来自安徽亳州（Bozhou (AH)，103 片）、贵州雷山（Leishan (GZ)，100 片）、吉林长白山（Changbai (JL)，102 片）和云南（Yunnan (YN)，100 片）四个记录产地。"
)
m.add_bilingual_para(
    "To ensure reproducible optical path lengths, suppress free-water attenuation, and minimize particle-size Mie "
    "scattering [12,14,17], all specimens were prepared following a standardized five-step pulverization and "
    "polyethylene (PE)-diluted hydraulic pelletizing workflow using an XQM-0.4L planetary ball mill, a DHG101-0B "
    "drying oven, an FA2104N electronic balance, and an Atlas TM 15T manual hydraulic press:",

    "为保证光程一致性、抑制自由水宽带衰减并降低颗粒米氏散射[12,14,17]，全部样品均采用 XQM-0.4L 行星式球磨机、DHG101-0B 干燥箱、FA2104N 电子天平及 Atlas TM 15T 手动压片机，按标准五步磨粉压片流程制备："
)
m.add_bilingual_bullet(
    "Step 1 — Cleaning and Oven Drying: Raw herbal pieces were inspected to remove surface impurities and dried in the "
    "DHG101-0B drying oven to remove residual free moisture that causes strong broadband dipolar attenuation in the THz band.",
    "第一步——清理与烘干除水：剔除药材表面杂尘后置于 DHG101-0B 干燥箱充分干燥，去除会在太赫兹波段引发强烈宽带偶极衰减的游离水分。"
)
m.add_bilingual_bullet(
    "Step 2 — Planetary Ball-Mill Pulverization: Dried specimens were finely pulverized using the XQM-0.4L planetary "
    "ball mill into uniform micro-scale powder satisfying the sub-wavelength scattering criterion (particle diameter "
    "d_p ≪ λ_THz, where λ_THz ≈ 288–1,364 μm across 0.22–1.04 THz).",
    "第二步——行星式球磨粉碎：使用 XQM-0.4L 行星式球磨机将干燥药材精细研磨为均匀微粉，使其颗粒粒径远小于太赫兹波长（0.22–1.04 THz 对应波长约 288–1,364 μm），从源头压制高频米氏散射。"
)
m.add_bilingual_bullet(
    "Step 3 — Analytical Weighing and PE Dilution: Herbal powder was accurately weighed on the FA2104N electronic "
    "balance and thoroughly homogenized with spectroscopic-grade polyethylene (PE) powder (which exhibits negligible "
    "absorption and nearly flat refractive index in the THz range) to keep pellet attenuation within the spectrometer's "
    "linear dynamic range and improve mechanical cohesion.",
    "第三步——精密称量与聚乙烯（PE）稀释混匀：用 FA2104N 电子天平精密称取药材细粉，并与太赫兹波段几乎透明、折射率平坦的光谱级聚乙烯（PE）粉末充分混匀，以将压片衰减控制在仪器线性动态范围内并改善成型致密性。"
)
m.add_bilingual_bullet(
    "Step 4 — Hydraulic Pellet Compression: The homogenized herb–PE mixture was loaded into a clean cylindrical "
    "stainless-steel die and compressed using the Atlas TM 15T manual hydraulic press into smooth, flat, crack-free "
    "circular pellets with a uniform nominal thickness of d = 1.5 mm, followed by controlled pressure release to avoid "
    "lamination. A blank pure-PE pellet of matching geometry was pressed as the optical reference.",
    "第四步——液压成型压片：将混匀后的药粉–PE 混合物装入洁净不锈钢圆柱模具，采用 Atlas TM 15T 手动压片机压制成表面平整、无裂纹、标称厚度一致为 1.5 mm 的圆形压片，并平稳泄压防止层裂；同时压制同规格空白纯 PE 压片作为光学参考。"
)
m.add_bilingual_bullet(
    "Step 5 — Nitrogen-Purged THz-TDS Transmission Measurement: Transmission spectra were acquired by Yiyi Yang at "
    "the Terahertz Spectroscopy Laboratory of Southwest University (Chongqing, China) using a TERA K15 THz-TDS system "
    "(Menlo Systems, Germany; optical wavelength 1,550 nm, optical power 33 mW). All measurements were conducted at "
    "292 K inside a dry nitrogen-purged enclosure with relative humidity maintained below 4%, using the blank PE "
    "pellet response as reference.",
    "第五步——氮气吹扫太赫兹透射采集：由杨易易在西南大学太赫兹光谱实验室（中国重庆）采用德国 Menlo Systems 公司 TERA K15 太赫兹时域光谱系统（激光波长 1,550 nm，光功率 33 mW）进行透射测量；全程在 292 K、湿度低于 4% 的干氮吹扫密闭腔室内完成，并以空白聚乙烯压片响应作参考校正。"
)

m.add_bilingual_heading("2.2. Optical parameter definitions and single-spectrum physical quality control",
                        "2.2. 光学参数物理定义与单谱仪器级物理质控", level=2)
m.add_bilingual_para(
    "The paired absorption-coefficient α(ω) and refractive-index n(ω) arrays exported from the TERA K15 measurement "
    "workbooks were linked by specimen identifier and preserved on their original exported numerical scales. As "
    "physical definitions underlying the exported optical constants [4,5], the complex frequency-domain transmission "
    "transfer function H(ω) relates the FFT spectra of the sample E_sam(ω) and blank-PE reference E_ref(ω) pulses:",

    "从 TERA K15 测量工作簿导出的配对吸收系数 α(ω) 与折射率 n(ω) 数组按样品编号关联，并完整保留其原始导出数值尺度。作为导出光学常数的物理定义基础[4,5]（而非本次数据分析重新执行的光学反演），复频域透射传递函数 H(ω) 由样品脉冲 E_sam(ω) 与空白 PE 参考脉冲 E_ref(ω) 经快速傅里叶变换（FFT）后的比值给出："
)
m.add_equation("H(ω) = E_sam(ω) / E_ref(ω) = ρ(ω) · exp[ −i · Δφ(ω) ]", "1")
m.add_bilingual_para(
    "Under the weakly absorbing homogeneous slab approximation (κ(ω) ≪ n(ω)) of the Dorney–Duvillaret formulation "
    "[4,5], the refractive index n(ω), absorption coefficient α(ω), and extinction coefficient κ(ω) are defined from "
    "the amplitude ratio ρ(ω), unwrapped phase difference Δφ(ω), vacuum speed of light c, angular frequency ω = 2πf, "
    "and pellet thickness d (1.5 mm) as:",

    "在 Dorney–Duvillaret 模型的弱吸收均匀平板近似（κ(ω) ≪ n(ω)）下[4,5]，折射率 n(ω)、吸收系数 α(ω) 及消光系数 κ(ω) 由振幅比 ρ(ω)、解缠绕相位差 Δφ(ω)、真空光速 c、角频率 ω = 2πf 及压片厚度 d（1.5 mm）共同定义："
)
m.add_equation("n(ω) = 1 + [ c · Δφ(ω) ] / (ω · d)", "2")
m.add_equation("α(ω) = (2 / d) · ln{ [ 4 · n(ω) ] / [ ρ(ω) · (n(ω) + 1)² ] },    κ(ω) = c · α(ω) / (4πf)", "3")
m.add_bilingual_para(
    "As proven by Jepsen and Fischer [17], the upper limit of reliable transmission absorption α_max(ω) is strictly "
    "governed by the frequency-dependent spectrometer dynamic range DR(ω):",

    "正如 Jepsen 与 Fischer 所证明[17]，透射式 THz-TDS 可可靠测量的最大吸收系数 α_max(ω) 严格受限于随频率变化的仪器动态范围 DR(ω)："
)
m.add_equation("α_max(ω) = (2 / d) · ln{ DR(ω) · [ 4 · n(ω) ] / [ n(ω) + 1 ]² }", "4")
m.add_bilingual_para(
    "Because DR(ω) rolls off sharply above ~1.05 THz while low-frequency diffraction perturbs phase below ~0.22 THz, "
    "all three datasets were uniformly truncated to the high-SNR physical passband of 0.22–1.04 THz (358 frequency "
    "coordinates per channel, Δf ≈ 0.0023 THz). Prior to modeling, a strictly single-spectrum instrument-level "
    "physical quality control (QC) filter Q_i ∈ {0, 1} was applied identically to every scan without referencing any "
    "cross-sample quantiles or class labels:",

    "由于高于 ~1.05 THz 后仪器动态范围 DR(ω) 急剧跌落至噪声基底，而低于 ~0.22 THz 易受孔径衍射相位畸变影响，三套数据集统一截取至高信噪比物理通带 0.22–1.04 THz（每通道 358 个频点，Δf ≈ 0.0023 THz）。在进入任何建模步骤之前，对每条光谱独立施加零跨样本统计依赖、零标签接触的单谱仪器级物理质控判据 Q_i ∈ {0, 1}："
)
m.add_equation("Q_i = I( 1.2 ≤ n̄_i ≤ 2.6 ) · I( ᾱ_i ≤ 55.0 )", "5")
m.add_bilingual_para(
    "where n̄_i and ᾱ_i are the passband averages of scan i alone. Physically, n̄_i < 1.0 violates causal refractive "
    "index (2π phase-unwrapping error), n̄_i > 2.6 exceeds dry herb–PE pellet permittivity (consistent with a "
    "half-thickness entry fault doubling both n − 1 and α in Eqs. (2)–(3)), and ᾱ_i > 55.0 indicates severe pellet "
    "cracking or beam obstruction saturating Eq. (4). Eq. (5) rejected only 6/403 Astragali Radix scans (1.49%: five "
    "consecutive Guyang scans with n̄ = 2.96–3.12 and doubled α = 55.7–60.8, plus one Gansu scan at ᾱ = 61.7; "
    "post-QC n = 397), 0/500 Ziziphi Spinosae Semen scans (n = 500), and 1/405 Gastrodia elata scan (0.25%: one "
    "Bozhou phase-unwrapping fault at n̄ = 0.901 < 1.0; post-QC n = 404), leaving 1,301 verified dual-channel spectra.",

    "其中 n̄_i 与 ᾱ_i 仅为第 i 条单谱自身的通带均值。物理上，n̄_i < 1.0 违背因果折射率（2π 相位解缠绕故障），n̄_i > 2.6 超出干燥药粉–PE 压片介电上限（与厚度录入减半导致式（2）–（3）中 n − 1 与 α 同步翻倍一致），ᾱ_i > 55.0 则对应压片开裂或光路遮挡引起的动态范围饱和。式（5）仅剔除了黄芪 6/403 条故障谱（1.49%：固阳连续 5 条 n̄ = 2.96–3.12 且 α 翻倍的厚度/相位故障谱，及甘肃 1 条 ᾱ = 61.7 开裂散射谱，保留 n = 397）、酸枣仁 0/500 条（保留 n = 500）及天麻 1/405 条（0.25%：亳州 1 条 n̄ = 0.901 < 1.0 相位故障谱，保留 n = 404），共保留 1,301 份高完整度双通道光谱。"
)

m.add_bilingual_heading("2.3. Mathematical logic chain: Dual-View preprocessing and SW-MCUVE-Manifold learning",
                        "2.3. 完整数学逻辑链：双视图预处理与 SW-MCUVE-Manifold 学习", level=2)
m.add_bilingual_para(
    "To make every modeling step physically transparent and mathematically verifiable, the pipeline forms a four-link "
    "logic chain (Scheme 1). Link 1 (Physical Scattering Decoupling): In compressed herbal pellets, measured "
    "absorption obeys an extended Beer–Lambert scattering model combining chemical absorption α_chem,i(ω), additive "
    "baseline tilt (b_0,i + b_1,i·ω), and a sample-specific multiplicative Mie scattering factor β_i:",

    "为使每一步建模均具备清晰的物理动机与可验证的数学基础，整套流程构建为四环相扣的逻辑链条（图式 Scheme 1）。环节一（物理散射解耦）：在压片透射测量中，实测吸收谱遵循扩展比尔–朗伯散射模型，由本征化学吸收 α_chem,i(ω)、加性基线漂移（b_0,i + b_1,i·ω）以及压片孔隙度微差引起的乘性米氏散射因子 β_i 共同构成："
)
m.add_equation("α_meas,i(ω) = β_i · α_chem,i(ω) + b_0,i + b_1,i · ω", "6")
m.add_bilingual_para(
    "Applying intra-sample standard normal variate (SNV) normalization [20] exclusively along specimen i's own "
    "358-point frequency axis algebraically cancels β_i with strictly zero cross-sample derivative:",

    "仅在单个样品 i 自身的 358 个频点上执行单样本标准正态变量变换（SNV）[20]，可在分子分母中代数约去乘性散射因子 β_i，且对任意其他样品偏导恒为零（绝对零跨样本泄漏）："
)
m.add_equation("x̃_i(ω_k) = [ x_i(ω_k) − x̄_i ] / (σ_i + ε),     ∂x̃_i / ∂x_m ≡ 0  (∀ i ≠ m)", "7")
m.add_bilingual_para(
    "Coupling SNV with Savitzky–Golay (SG) quadratic polynomial convolution [19] of derivative order d ∈ {0, 1, 2} "
    "further removes additive baseline drift b_0,i + b_1,i·ω. However, pure SNV erases macroscopic amplitude cues "
    "(x̄_i, σ_i) that encode fatty-oil and moisture differences in lipid-rich seeds. Therefore, every sample is mapped "
    "strictly within its own frequency axis into a 3,222-dimensional Dual-View Physical Tensor x_i^dual combining "
    "View 1 (Scattering-Invariant Morphology x_i^SNV ∈ R^1790: smoothed SNV envelopes w = 19, SNV-normalized first "
    "derivatives w = 19/15, and SNV-normalized absorption second derivative w = 15) and View 2 (Amplitude-Preserving "
    "Dielectric Scale x_i^Amp ∈ R^1432: un-normalized SG smoothed envelopes w = 19 of α and n, raw absorption second "
    "derivative w = 15, and raw refractive dispersion slope w = 15):",

    "将 SNV 与 d ∈ {0, 1, 2} 阶 Savitzky–Golay（SG）二次多项式卷积滤波[19]结合，可进一步剥离加性基线漂移 b_0,i + b_1,i·ω。但纯 SNV 会同时抹去油脂种子中反映脂肪油与水分差异的宏观绝对幅值（x̄_i, σ_i）。为此，每条样本严格在自身频率轴内映射为 3,222 维双视图物理张量 x_i^dual，同步拼接视图 1（去散射形态 x_i^SNV ∈ R^1790：SNV 平滑包络 w=19、SNV 归一化一阶导 w=19/15 与吸收二阶导 w=15）和视图 2（保幅介电尺度 x_i^Amp ∈ R^1432：未归一化 α 与 n 的平滑包络 w=19、原始吸收二阶导 w=15 与原始折射率一阶色散斜率 w=15）："
)
m.add_equation("x_i^(d)(ω_k) = Σ_{m = −M}^{M} c_m^(d) · x_i(ω_{k+m}),     x_i^dual = [ x_i^SNV  ∥  x_i^Amp ] ∈ R^3222", "8")
m.add_bilingual_para(
    "Link 2 (Full-Rank MC-UVE & Anisotropic Stability Metric Tensor): Strictly inside each training fold after "
    "training-fitted Z-score scaling, full-rank Monte Carlo UVE [21,22] (M = 30 random 80% subsamples) fits PLS "
    "regression [24,25] using the exact rank of the K-class dummy target matrix (n_comp = K − 1: 3 for 4-class "
    "roots/tubers, 4 for 5-class seeds) to compute each coordinate's stability score s_j (Eq. (9)). Rather than "
    "applying an isotropic 0/1 hard mask, the top 35% highest-stability features (S_35%, q = 1,127) are weighted by a "
    "continuous anisotropic metric tensor Λ = diag(w_j²) (Eq. (10)), enabling automatic adaptation to root versus "
    "seed physics:",

    "环节二（满秩 MC-UVE 与各向异性稳定性度量张量）：在仅由训练折拟合 Z-score 标准化后，严格在训练折内部执行满秩蒙特卡洛无信息变量剔除（MC-UVE[21,22]，M = 30 轮 80% 随机子抽样），按 K 分类哑变量矩阵的精确满秩（n_comp = K − 1：4 分类取 3、5 分类取 4）拟合偏最小二乘（PLS[24,25]）回归以计算各特征稳定性得分 s_j（式（9））。摒弃传统粗糙的 0/1 硬截断，对前 35% 高稳定特征（S_35%，q = 1,127 维）施加连续各向异性度量张量加权 Λ = diag(w_j²)（式（10）），使模型在纤维根与油脂种子间自动调整主导物理视图权重："
)
m.add_equation("s_j = [ (1/M) Σ_{m=1}^{M} |b_{m,j}| ] / [ std_m(|b_{m,j}|) + ε ]", "9")
m.add_equation("w_j = ( s_j / s_max )^0.5   (j ∈ S_35%),     F_phys = X_tr[:, S_35%] ⊙ w", "10")
m.add_bilingual_para(
    "Link 3 (Subspace-Purified Shrinkage Manifold & Joint Anisotropic Kernel SVM): To overcome spectral collinearity "
    "(q ≫ N_train) without letting the eliminated 65% noisy dimensions contaminate the within-class scatter matrix S_W, "
    "Ledoit–Wolf shrinkage Eigen-LDA [26] is fitted exclusively on the purified subspace F_phys (Eq. (11)). Its "
    "standardized discriminant coordinates z = P^T F_phys are coupled with F_phys via weight λ inside a joint "
    "anisotropic RBF-SVM [27] (Eq. (12)):",

    "环节三（子空间净化收缩流形与联合各向异性核 SVM）：为克服高维光谱共线性（q ≫ N_train）并防止被淘汰的 65% 噪声维度污染类内散度矩阵 S_W，仅在 MC-UVE 净化后的纯净子空间 F_phys 上拟合 Ledoit–Wolf 协方差收缩特征值 LDA[26]（式（11））；随后将标准化正交判别流形坐标 z = P^T F_phys 以耦合权重 λ 与物理特征块 F_phys 拼接，输入联合各向异性 RBF-SVM[27]（式（12））："
)
m.add_equation("max_P  Tr( P^T S_B^pure P ) / Tr( P^T Σ̂_W^LW P ),    Σ̂_W^LW = (1 − δ) S_W^pure + δ · [Tr(S_W^pure)/q] · I", "11")
m.add_equation("K_SW-M(u, v) = exp{ −γ · [ ‖u_phys − v_phys‖_Λ² + λ² · ‖z_u − z_v‖_2² ] }", "12")
m.add_bilingual_para(
    "Link 4 (Strict Double-Nested 5-Fold CV & Physical Fisher Separability): Following Varma and Simon [29] and "
    "Cawley and Talbot [30], unbiased blind accuracy is evaluated via Strict Double-Nested 5-Fold Stratified CV "
    "(Eq. (13)): in each outer fold, 20% of specimens are sequestered untouched, while an inner 3-fold CV strictly "
    "within the 80% outer training fold selects θ_k* = (λ*, C*, γ*) over λ ∈ {1.0, 2.0, 3.0}, C ∈ {1, 5, 10, 50}, "
    "and γ ∈ {'scale', 0.002, 0.005}. To link empirical accuracy ceilings directly to tissue-level optical "
    "separability, the post-QC dual-channel Fisher trace ratio J_Fisher is quantified via Eq. (14). All baselines "
    "(PLS-DA [25], Random Forest [28], full-spectrum RBF-SVM [27], and Gen-1 hard MC-UVE-SVM [22]) and ablations "
    "used identical double-nested splits in Python 3.12 with Scikit-learn [36].",

    "环节四（真·双层严格嵌套 5 折交叉验证与物理 Fisher 可分性）：遵循 Varma 与 Simon[29] 及 Cawley 与 Talbot[30] 的无偏评估准则，采用双层严格嵌套分层 5 折交叉验证（式（13））：每一外层折物理隔离 20% 盲测样品，仅在 80% 外层训练折内部经内层 3 折 CV 从精简网格（λ ∈ {1.0, 2.0, 3.0}，C ∈ {1, 5, 10, 50}，γ ∈ {'scale', 0.002, 0.005}）选定最优 θ_k* = (λ*, C*, γ*) 后再单向盲测。为将实测准确率上限直接与植物组织天然物理可分性关联，通过式（14）计算质控后双通道 Fisher 迹散度比 J_Fisher。全部基线模型（PLS-DA[25]、随机森林[28]、全谱 RBF-SVM[27] 与 Gen-1 硬截断 MC-UVE-SVM[22]）及消融实验均基于 Python 3.12 与 Scikit-learn[36] 在完全相同的双层嵌套划分下完成。"
)
m.add_equation("Acc_DN = (1 / N) · Σ_{k=1}^{5} Σ_{i ∈ D_k^out} I( f̂_{θ_k*}(x_i) = y_i ),    θ_k* = argmax_{θ ∈ Θ} CV_inner^(3)(D_{-k}^out; θ)", "13")
m.add_equation("J_Fisher = Tr(S_B) / Tr(S_W) = [ Σ_c N_c ‖μ_c − μ‖_2² ] / [ Σ_c Σ_{i ∈ c} ‖x_i − μ_c‖_2² ]", "14")

m.add_image(
    os.path.join(ROOT_DIR, "Pipeline_Flowchart_Clean.png"),
    width_inches=5.5, max_height_inches=7.3,
    en_prefix="Scheme 1. ",
    en_caption="End-to-end architecture of the locked Dual-View SW-MCUVE-Manifold THz-TDS authentication framework, spanning TERA K15 measurement and single-spectrum physical QC (Module 1), zero-leakage intra-sample dual-view feature extraction (Module 2), strict double-nested 5-fold CV (Module 3), and locked cross-matrix validation bridged to DFT-D3(BJ) benchmarks (Module 4).",
    zh_prefix="图式 1。",
    zh_caption="统一锁死的 Dual-View SW-MCUVE-Manifold 太赫兹鉴别框架全流程图，涵盖 TERA K15 测量与单谱物理质控（模块 1）、零泄漏单样本双视图特征提取（模块 2）、真·双层严格嵌套 5 折交叉验证（模块 3）以及跨基质验证与 DFT-D3(BJ) 量子化学基准桥接（模块 4）。"
)

m.add_bilingual_heading("2.4. Quantum chemical DFT vibrational benchmarks", "2.4. 量子化学 DFT 振动基准计算", level=2)
m.add_bilingual_para(
    "Gas-phase single-molecule DFT calculations were performed in Gaussian 16 at the B3LYP-D3(BJ)/6-31G(d) level "
    "[31–33] on calycosin (the rigid isoflavone aglycone core representative of Astragali Radix, PubChem CID 5280448) "
    "and spinosin (the statutory C-glycosylflavone marker of Ziziphi Spinosae Semen, PubChem CID 155692). Geometry "
    "optimizations converged to true local minima (zero imaginary frequencies), and harmonic THz modes were assigned "
    "via Potential Energy Distribution (PED) using Multiwfn 3.8 [34], VEDA 4 [35], and GaussView 6.0. Because active "
    "flavonoids occupy trace mass fractions in crude herb–PE pellets and pure crystalline reference standards were not "
    "co-measured, these calculations serve strictly as intramolecular vibrational benchmarks offering tentative "
    "structural assignments rather than an exhaustive reconstruction of bulk absorption.",

    "采用 Gaussian 16 软件在 B3LYP-D3(BJ)/6-31G(d) 理论水平[31–33]下，对毛蕊异黄酮（黄芪异黄酮刚性苷元母核模型，PubChem CID 5280448）与斯皮诺素（酸枣仁法定碳苷黄酮质量标志物，PubChem CID 155692）开展气相单分子 DFT 计算。几何构型优化均收敛至无虚频的真实局域极小点，并借助 Multiwfn 3.8[34]、VEDA 4[35] 与 GaussView 6.0 进行势能分布（PED）振动归属。鉴于有效黄酮成分在药材–PE 压片中仅占微量质量分数且本研究未同步测定纯结晶标准品，单分子 DFT 计算明确定位为分子内低频振动理论基准与参考归属，而非对宏观总吸收的完全重构。"
)

# --- 3. Results and discussion ---
m.add_bilingual_heading("3. Results and discussion", "3. 结果与讨论", level=1)

m.add_bilingual_heading("3.1. THz spectral signatures, single-spectrum QC, and physical separability",
                        "3.1. 太赫兹光谱特征、单谱物理质控与物理可分性", level=2)
m.add_bilingual_para(
    "Figure 1 presents the post-QC mean ± SD raw absorption spectra (Figure 1a) and SG second-derivative spectra "
    "(Figure 1b) of the four Astragali Radix origins across 0.22–1.04 THz (n = 397). Raw α(ω) rises monotonically "
    "from ~10–16 to ~50–61 across the passband due to broad Rayleigh–Mie scattering, while SG second-derivative "
    "filtering eliminates the sloping baseline and resolves crisp second-derivative minima across 0.25–0.95 THz. "
    "Quantifying Eq. (14) revealed a pronounced physical separability hierarchy across tissues: fibrous Astragali "
    "Radix roots yielded J_Fisher = 0.2999 (up +48% from pre-QC 0.2026 after removing the 6 instrument-fault scans), "
    "which is 3.76-fold lower than lipid-rich Ziziphi Spinosae Semen (J_Fisher = 1.1268) and 3.36-fold lower than "
    "starchy Gastrodia elata tubers (J_Fisher = 1.0064). This native physical hierarchy explains why fibrous root "
    "authentication is inherently harder than seed or tuber discrimination.",

    "图 1 展示了质控后四产地黄芪（n = 397）在 0.22–1.04 THz 频段的均值 ± 标准差原始吸收谱（图 1a）与 SG 二阶导数谱（图 1b）。原始吸收谱受宽带瑞利–米氏散射主导，随频率由约 10–16 单调爬升至 50–61；经 SG 二阶导数滤波后，倾斜基线被有效消除，在 0.25–0.95 THz 区间解析出清晰的二阶导数极小值特征。由式（14）算得的质控后双通道物理 Fisher 可分性比呈现显著的植物组织层级：粗纤维黄芪根茎仅为 J_Fisher = 0.2999（较质控前 0.2026 提升 +48%），仍仅为油脂酸枣仁种子（1.1268）的 1/3.76 和致密天麻块茎（1.0064）的 1/3.36。这一原生底层物理信噪比差异直接解释了粗纤维根茎鉴别难度显著高于种子与块茎的内在根源。"
)
m.add_image(
    os.path.join(ROOT_DIR, "Figure 1.png"),
    width_inches=6.2, max_height_inches=3.2,
    en_prefix="Figure 1. ",
    en_caption="Post-QC THz spectral profiles (Mean ± SD, 0.22–1.04 THz) of four Astragali Radix origins (n = 397): (a) raw absorption spectra α(ω) showing monotonic scattering slopes; (b) Savitzky–Golay second-derivative spectra (d²α/dω², window = 19, polyorder = 2) resolving baseline-free second-derivative minima.",
    zh_prefix="图 1。",
    zh_caption="质控后四产地黄芪（n = 397）在 0.22–1.04 THz 频段的太赫兹光谱轮廓（均值 ± 标准差）：（a）呈现单调散射斜坡的原始吸收谱 α(ω)；（b）消除倾斜基线并解析出二阶导数极小值的 SG 二阶导数谱（窗口 19，二阶多项式）。"
)

m.add_bilingual_heading("3.2. Strict double-nested classification and four-stage zero-leakage audits",
                        "3.2. 双层严格嵌套分类性能与四重无泄漏审计", level=2)
m.add_bilingual_para(
    f"Under strict double-nested 5-fold CV (Eq. (13)), the locked Dual-View SW-MCUVE-Manifold pipeline achieved "
    f"{HQ['proposed']['acc']:.2f}% blind accuracy (370/397; 5-fold Mean ± SD = {HQ['proposed']['mean']:.2f}% ± "
    f"{HQ['proposed']['sd']:.2f}%; Macro-F1 = {HQ['proposed']['macro_f1']:.4f}) on four-origin Astragali Radix "
    "(Figure 2, Table 2), with all four origins achieving F1 ≥ 0.9200 and fold-to-fold SD reduced nearly in half "
    "compared with the unfiltered raw set (±2.73% vs. ±4.70%). On five-format commercial Ziziphi Spinosae Semen "
    f"(n = {SZ['n_samples']}), the identical locked architecture achieved {SZ['proposed']['acc']:.2f}% blind accuracy "
    f"(487/500; Mean ± SD = {SZ['proposed']['mean']:.2f}% ± {SZ['proposed']['sd']:.2f}%; Macro-F1 = "
    f"{SZ['proposed']['macro_f1']:.4f}; Figure 3, Table 2), with branded lots reaching 0.9849–0.9950 F1 and 9 of 13 "
    "residual errors confined strictly between the two loose bulk lots (Bulk-Bag and Bulk-50g).",

    "在真·双层严格嵌套 5 折交叉验证（式（13））下，统一锁死的 Dual-View SW-MCUVE-Manifold 流程在四产地黄芪（n = 397）上取得 93.20% 的真实盲测准确率（370/397；5 折均值 ± 标准差为 93.19% ± 2.73%，Macro-F1 = 0.9321；图 2、表 2），四个产地 F1 均不低于 0.9200，且单谱物理质控使折间标准差较未清洗全集（±4.70%）缩减近半。在五规格商业酸枣仁（n = 500）上，完全相同的锁死架构取得 97.40% 盲测准确率（487/500；97.40% ± 1.62%，Macro-F1 = 0.9740；图 3、表 2），其中三个品牌/包装规格 F1 达 0.9849–0.9950，其余 13 例误判中有 9 例集中于两类散装大货（Bulk-Bag 与 Bulk-50g）之间。"
)
m.add_image(
    os.path.join(ROOT_DIR, "Figure 2.png"),
    width_inches=4.3, max_height_inches=4.0,
    en_prefix="Figure 2. ",
    en_caption=f"Strict double-nested 5-fold CV confusion matrix for Astragali Radix (root, 4 origins, n = {HQ['n_samples']}): {HQ['proposed']['acc']:.2f}% ({HQ['proposed']['mean']:.2f}% ± {HQ['proposed']['sd']:.2f}%, Macro-F1 = {HQ['proposed']['macro_f1']:.4f}).",
    zh_prefix="图 2。",
    zh_caption="黄芪（根茎类，4 产地，n = 397）真·双层严格嵌套 5 折交叉验证混淆矩阵：总盲测准确率 93.20%（93.19% ± 2.73%，Macro-F1 = 0.9321）。"
)
m.add_image(
    os.path.join(ROOT_DIR, "Figure 3.png"),
    width_inches=4.4, max_height_inches=4.0,
    en_prefix="Figure 3. ",
    en_caption=f"Strict double-nested 5-fold CV confusion matrix for Ziziphi Spinosae Semen (seed, 5 commercial formats/batches, n = {SZ['n_samples']}): {SZ['proposed']['acc']:.2f}% ({SZ['proposed']['mean']:.2f}% ± {SZ['proposed']['sd']:.2f}%, Macro-F1 = {SZ['proposed']['macro_f1']:.4f}).",
    zh_prefix="图 3。",
    zh_caption="酸枣仁（种子类，5 商业规格/批次，n = 500）真·双层严格嵌套 5 折交叉验证混淆矩阵：总盲测准确率 97.40%（97.40% ± 1.62%，Macro-F1 = 0.9740）。"
)
m.add_bilingual_para(
    "Four adversarial zero-leakage audits (Table 5) rigorously verified the statistical integrity of the 3,222-dim "
    "pipeline: (i) Unfiltered raw-set evaluation (0 scans removed; n = 403/500/405) retained 92.80%, 97.40%, and "
    "99.26% blind accuracy; (ii) Differential blind-test perturbation (corrupting an outer test spectrum by 500× + "
    "10,000) induced an exact 0.000000e+00 deviation in all 402 other feature vectors, training-fold MC-UVE stability "
    "‖Δs‖_∞, Shrinkage-LDA projections ‖ΔZ_tr‖_∞, and all 80 remaining outer test predictions in that fold (0/80 "
    "mismatches); (iii) Multi-seed repeated double-nested CV (Seeds = 42, 100, 2026; 15 blind folds per matrix) "
    "maintained 93.12% ± 0.93%, 97.20% ± 0.28%, and 99.67% ± 0.12%; and (iv) Y-scrambling random label permutation "
    "collapsed accuracy strictly to theoretical chance—21.41% ± 2.47% (4-class chance 25.00%), 18.80% ± 1.33% "
    "(5-class chance 20.00%), and 26.98% ± 1.52% (4-class chance 25.00%)—conclusively ruling out spurious leakage.",

    "四重对抗式无泄漏审计（表 5）从数学与统计层面严密验证了 3,222 维流水线的可靠性：（i）未清洗原始全集（0 样本剔除，n = 403/500/405）仍取得 92.80%、97.40% 与 99.26% 的双层盲测准确率，证明高准确率并非依赖删样；（ii）盲测微分扰动探针（对外层测试样本注入 500× 乘性畸变与 +10,000 加性偏置）在其余 402 条特征向量、训练折 MC-UVE 稳定度 ‖Δs‖_∞、收缩 LDA 投影 ‖ΔZ_tr‖_∞ 及同折其余 80 份盲测预测上均产生精确的 0.000000e+00 偏差（0/80 误跳变）；（iii）三组独立随机种子（42、100、2026，各 15 个盲测折）跨种子均值稳定在 93.12% ± 0.93%、97.20% ± 0.28% 与 99.67% ± 0.12%；（iv）Y-标签随机打乱置换检验使三类药材准确率瞬间坍塌至理论纯随机水平——21.41% ± 2.47%（4 分类基准 25.00%）、18.80% ± 1.33%（5 分类基准 20.00%）与 26.98% ± 1.52%（4 分类基准 25.00%），彻底排除高维特征选择或调参泄漏。"
)

m.add_bilingual_heading("3.3. Module knockout ablation, dual-view physics, and baseline benchmarking",
                        "3.3. 模块敲除消融、双视图物理互补机制与基线模型对比", level=2)
m.add_bilingual_para(
    "Double-nested knockout ablations (Figure 4a–b, Figure S1b, Table 3) revealed sharp physical complementarity "
    "between View 1 and View 2. On fibrous Astragali Radix roots, removing SNV (Amplitude Only) caused a −4.28% drop "
    "(93.20% → 88.92%), removing amplitude preservation (SNV Only) caused a −3.53% drop (to 89.67%), and removing "
    "the purified Shrinkage-LDA manifold (λ = 0) dropped accuracy by −1.01%. Conversely, on lipid-rich Ziziphi "
    "Spinosae Semen seeds, removing the amplitude-preserving view (SNV Only) triggered a −3.00% drop (97.40% → 94.40%) "
    "because Bulk-Bag (ᾱ = 45.76 ± 1.77) and Bulk-50g (ᾱ = 50.09 ± 2.40) differ primarily in macroscopic absorption "
    "magnitude erased by pure SNV. Transparently, not every knockout was strictly negative: Amplitude-Only reached "
    "98.40% (+1.00%) on seeds while Absorption-Only reached 93.70% (+0.50%) on roots—both within one fold-to-fold SD, "
    "reflecting the inherent trade-off of a single locked cross-matrix architecture rather than matrix-specific tuning.",

    "双层嵌套模块敲除消融（图 4a–b、图 S1b、表 3）清晰揭示了双视图间的物理互补性：在纤维根茎黄芪上，剔除 SNV 视图（仅保幅）导致准确率骤降 −4.28%（93.20% → 88.92%），剔除保幅视图（仅 SNV）亦下降 −3.53%（至 89.67%），剔除净化收缩 LDA 流形（λ = 0）下降 −1.01%；反之，在油脂种子酸枣仁上，剔除保幅视图（仅 SNV）导致准确率下滑 −3.00%（97.40% → 94.40%），根源在于 Bulk-Bag（ᾱ = 45.76 ± 1.77）与 Bulk-50g（ᾱ = 50.09 ± 2.40）的核心差异位于被纯 SNV 抹平的宏观绝对吸收幅值。如实指出，并非所有单项敲除均为负值：酸枣仁仅保幅视图达 98.40%（+1.00%），黄芪仅吸收通道达 93.70%（+0.50%），两者幅度均小于单倍折间标准差，体现了统一锁死架构在跨基质普适性与单基质极值间的合理权衡。"
)
m.add_image(
    os.path.join(ROOT_DIR, "Figure 4.a.png"),
    width_inches=5.4, max_height_inches=3.3,
    en_prefix="Figure 4a. ",
    en_caption="Strict double-nested module knockout ablation (Mean ± SD) for Astragali Radix (n = 397), showing −4.28% degradation without SNV and −3.53% without amplitude preservation.",
    zh_prefix="图 4a。",
    zh_caption="黄芪（n = 397）真·双层严格嵌套模块敲除消融结果（均值 ± 标准差），剔除 SNV 下降 −4.28%、剔除保幅视图下降 −3.53%。"
)
m.add_image(
    os.path.join(ROOT_DIR, "Figure 4.b.png"),
    width_inches=5.4, max_height_inches=3.3,
    en_prefix="Figure 4b. ",
    en_caption="Strict double-nested module knockout ablation (Mean ± SD) for Ziziphi Spinosae Semen (n = 500), demonstrating the −3.00% penalty when amplitude preservation is removed.",
    zh_prefix="图 4b。",
    zh_caption="酸枣仁（n = 500）真·双层严格嵌套模块敲除消融结果（均值 ± 标准差），剔除保幅介电视图导致准确率下降 −3.00%。"
)
m.add_bilingual_para(
    "Across identical double-nested baseline comparisons (Figure 5a–b, Table 4), the proposed Dual-View "
    "SW-MCUVE-Manifold classifier ranked first across all three matrices: on Astragali Radix (93.20%), it surpassed "
    "PLS-DA (82.87%) by +10.33%, Random Forest (84.13%) by +9.07%, full-spectrum RBF-SVM (89.67%) by +3.53%, and "
    "Gen-1 Hard MC-UVE-SVM (88.92%) by +4.28%; on Ziziphi Spinosae Semen (97.40%), it outperformed PLS-DA (92.80%), "
    "Random Forest (92.00%), full-spectrum RBF-SVM (95.20%), and Gen-1 Hard MC-UVE-SVM (96.40%).",

    "在完全相同划分下的经典基线模型横向对比中（图 5a–b、表 4），本文 Dual-View SW-MCUVE-Manifold 在三大药材上均稳居第一：在黄芪（93.20%）上分别领先 PLS-DA（82.87%）+10.33%、随机森林（84.13%）+9.07%、全谱 RBF-SVM（89.67%）+3.53% 以及 Gen-1 硬截断 MC-UVE-SVM（88.92%）+4.28%；在酸枣仁（97.40%）上同样全面超越 PLS-DA（92.80%）、随机森林（92.00%）、全谱 RBF-SVM（95.20%）及 Gen-1 硬截断 MC-UVE-SVM（96.40%）。"
)
m.add_image(
    os.path.join(ROOT_DIR, "Figure 5.a.png"),
    width_inches=5.4, max_height_inches=3.3,
    en_prefix="Figure 5a. ",
    en_caption="Strict double-nested baseline model comparison on Astragali Radix (n = 397): Proposed Dual-View SW-MCUVE-Manifold (+4.28% over Gen-1 Hard MC-UVE-SVM) vs. classical baselines.",
    zh_prefix="图 5a。",
    zh_caption="黄芪（n = 397）同划分双层严格嵌套基线模型对比：本文方法较 Gen-1 硬截断基线净提升 +4.28%。"
)
m.add_image(
    os.path.join(ROOT_DIR, "Figure 5.b.png"),
    width_inches=5.4, max_height_inches=3.3,
    en_prefix="Figure 5b. ",
    en_caption="Strict double-nested baseline model comparison on Ziziphi Spinosae Semen (n = 500), confirming first-place performance (+1.00% over Gen-1 Hard MC-UVE-SVM).",
    zh_prefix="图 5b。",
    zh_caption="酸枣仁（n = 500）同划分双层严格嵌套基线模型对比，本文方法稳居首位（较 Gen-1 基线提升 +1.00%）。"
)

m.add_bilingual_heading("3.4. Independent cross-matrix methodological validation on Gastrodia elata",
                        "3.4. 天麻跨物种/跨基质独立方法学验证", level=2)
m.add_bilingual_para(
    "Migrated without a single modification to an independent orchid tuber dataset (Gastrodia elata, 4 origins, "
    f"n = {TM['n_samples']}), the locked architecture achieved {TM['proposed']['acc']:.2f}% blind accuracy (403/404 "
    f"correct; Mean ± SD = {TM['proposed']['mean']:.2f}% ± {TM['proposed']['sd']:.2f}%, Macro-F1 = "
    f"{TM['proposed']['macro_f1']:.4f}; Figure S1a, Table 2), with 100.00% recall on Bozhou, Leishan, and Yunnan and "
    "100.00% accuracy in four of five outer folds. Every ablation knockout (Figure S1b, Table 3) caused strictly "
    "negative degradation (−0.25% to −1.73%), and the locked pipeline outperformed every baseline (Table 4: +1.73% to "
    "+4.45%). Because the dual-view design and QC bounds were refined across the collected datasets, future acquisition "
    "of newly pressed independent batches on separate days remains important for prospective temporal validation.",

    "将完全锁死的同一套架构一字不改地迁移至独立兰科块茎数据集天麻（4 产地，n = 404）进行跨基质方法学验证，取得 99.75% 盲测准确率（403/404 命中；99.75% ± 0.50%，Macro-F1 = 0.9975；图 S1a、表 2），亳州、雷山与云南均获 100.00% 召回率，5 个外层盲测折中有 4 折达到 100.00%。天麻上全部四项模块敲除均为严格负向退化（−0.25% 至 −1.73%；图 S1b、表 3），且全面超越四类基线模型（+1.73% 至 +4.45%；表 4）。需要客观指出，因双视图设计与质控边界在现有采集数据上完成定型，未来跨天新压片独立批次的前瞻性采集验证仍具有重要价值。"
)
m.add_image(
    os.path.join(ROOT_DIR, "Figure S1.a.png"),
    width_inches=4.3, max_height_inches=4.0,
    en_prefix="Figure S1a. ",
    en_caption=f"Independent cross-matrix methodological validation confusion matrix on Gastrodia elata (tuber, 4 origins, n = {TM['n_samples']}): {TM['proposed']['acc']:.2f}% ({TM['proposed']['mean']:.2f}% ± {TM['proposed']['sd']:.2f}%, 403/404 correct).",
    zh_prefix="图 S1a。",
    zh_caption="天麻（兰科块茎，4 产地，n = 404）跨基质独立方法学验证混淆矩阵：盲测准确率 99.75%（99.75% ± 0.50%，403/404 命中）。"
)
m.add_image(
    os.path.join(ROOT_DIR, "Figure S1.b.png"),
    width_inches=5.4, max_height_inches=3.3,
    en_prefix="Figure S1b. ",
    en_caption="Strict double-nested module knockout ablation on Gastrodia elata (n = 404), confirming strictly positive contributions of every module.",
    zh_prefix="图 S1b。",
    zh_caption="天麻（n = 404）真·双层严格嵌套模块敲除消融结果，证实全部模块均贡献正向收益。"
)

m.add_bilingual_heading("3.5. Quantum chemical DFT intramolecular vibrational benchmarks",
                        "3.5. 量子化学 DFT 分子内振动基准分析", level=2)
m.add_bilingual_para(
    "Figure 6 and Table 1 summarize the B3LYP-D3(BJ)/6-31G(d) equilibrium geometries and intramolecular THz vibrational "
    "benchmarks of calycosin and spinosin. Calycosin Mode 1 at 0.885 THz (29.53 cm⁻¹, 2.446 km/mol) arises from "
    "intramolecular B-ring dihedral torsion τ(C–C) coupled with methoxy rocking. Spinosin exhibits four active "
    "intramolecular modes inside 0.22–1.04 THz: Mode 2 (0.552 THz, dual C-glycosyl breathing/shearing), Mode 3 "
    "(0.605 THz, 1.241 km/mol, C-glycosyl rocking relative to the flavone core with OH shift), Mode 4 (0.886 THz, "
    "flavone core out-of-plane bending), and Mode 5 (0.979 THz, 1.239 km/mol, 4'-hydroxyphenyl B-ring flapping). "
    "While bulk herb–PE absorption is dominated by macromolecular cellulose, starch, and lipid matrices, these "
    "benchmarks verify that representative flavonoid skeletons possess IR-active intramolecular modes precisely "
    "spanning 0.55–0.98 THz, providing physically grounded reference assignments.",

    "图 6 与表 1 总结了毛蕊异黄酮与斯皮诺素在 B3LYP-D3(BJ)/6-31G(d) 水平下的平衡构型及分子内太赫兹振动基准。毛蕊异黄酮 Mode 1 位于 0.885 THz（29.53 cm⁻¹，红外强度 2.446 km/mol），源于 B 环相对色酮母核的分子内二面角扭转 τ(C–C) 及甲氧基摇摆；斯皮诺素在 0.22–1.04 THz 通带内呈现四个活跃分子内模态：Mode 2（0.552 THz，双碳糖基呼吸与剪切）、Mode 3（0.605 THz，1.241 km/mol，碳糖基相对黄酮母核摇摆伴羟基位移）、Mode 4（0.886 THz，黄酮母核面外弯曲）及 Mode 5（0.979 THz，1.239 km/mol，4'-羟基苯环面外扑动）。尽管药粉–PE 压片的宏观吸收主要由纤维素、淀粉与脂质基质主导，这些理论基准证实典型黄酮骨架在 0.55–0.98 THz 区间具有明确的红外活性分子内扭转与糖基摇摆自由度，为化学计量学判别频段提供了物理参考依据。"
)
m.add_image(
    os.path.join(ROOT_DIR, "Figure 6.png"),
    width_inches=6.0, max_height_inches=4.1,
    en_prefix="Figure 6. ",
    en_caption="B3LYP-D3(BJ)/6-31G(d) optimized geometries and intramolecular atomic displacement vectors: (a) calycosin equilibrium structure, (b) calycosin Mode 1 (0.885 THz), (c) spinosin equilibrium structure, (d) spinosin Mode 3 (0.605 THz), and (e) spinosin Mode 5 (0.979 THz).",
    zh_prefix="图 6。",
    zh_caption="B3LYP-D3(BJ)/6-31G(d) 优化构型与分子内原子位移矢量：（a）毛蕊异黄酮平衡构型，（b）毛蕊异黄酮 Mode 1（0.885 THz），（c）斯皮诺素平衡构型，（d）斯皮诺素 Mode 3（0.605 THz），（e）斯皮诺素 Mode 5（0.979 THz）。"
)

# --- 4. Conclusions ---
m.add_bilingual_heading("4. Conclusions", "4. 结论", level=1)
m.add_bilingual_para(
    "This study established and audited a locked Dual-View SW-MCUVE-Manifold THz-TDS authentication framework across "
    "fibrous roots, lipid-rich seeds, and starchy tubers. Integrating standardized PE-diluted pelletizing and "
    "single-spectrum physical QC (1.2 ≤ n̄ ≤ 2.6, ᾱ ≤ 55.0 cm⁻¹) with intra-sample SNV morphology and "
    "amplitude-preserving dielectric views inside strict double-nested 5-fold CV achieved unbiased blind accuracies "
    f"of {HQ['proposed']['acc']:.2f}% ({HQ['proposed']['mean']:.2f}% ± {HQ['proposed']['sd']:.2f}%) for Astragali "
    f"Radix (n = {HQ['n_samples']}), {SZ['proposed']['acc']:.2f}% ({SZ['proposed']['mean']:.2f}% ± "
    f"{SZ['proposed']['sd']:.2f}%) for Ziziphi Spinosae Semen (n = {SZ['n_samples']}), and "
    f"{TM['proposed']['acc']:.2f}% ({TM['proposed']['mean']:.2f}% ± {TM['proposed']['sd']:.2f}%) on locked "
    f"cross-matrix validation using Gastrodia elata (n = {TM['n_samples']}), surpassing all tested baselines. Four "
    "zero-leakage audits (raw-set retention, 0.00e+00 perturbation probe, multi-seed repeats, and Y-scrambling "
    "permutation) confirmed statistical soundness, while Fisher separability and DFT-D3(BJ) benchmarks anchored the "
    "framework in physical spectroscopy.",

    "本研究建立并严密审计了一套横跨纤维根茎、油脂种子与淀粉块茎的锁死 Dual-View SW-MCUVE-Manifold 太赫兹鉴别框架。将规范化掺 PE 压片制样、单谱物理质控（1.2 ≤ n̄ ≤ 2.6，ᾱ ≤ 55.0 cm⁻¹）与单样本去散射 SNV 形态/保幅介电双视图耦合进真·双层严格嵌套 5 折交叉验证后，在黄芪（n = 397）、酸枣仁（n = 500）及天麻跨基质独立验证（n = 404）上分别取得 93.20%（93.19% ± 2.73%）、97.40%（97.40% ± 1.62%）与 99.75%（99.75% ± 0.50%）的无偏盲测准确率，全面优于各类基线模型。四重无泄漏审计（未清洗全集评估、0.00e+00 微分扰动探针、多随机种子重复及 Y-标签置换检验）证实了统计严密性，而 Fisher 物理可分性比与 DFT-D3(BJ) 振动基准则赋予了框架扎实的物理光谱可解释性。"
)

# --- Bilingual Tables Section ---
m.add_page_break()
m.add_bilingual_heading("Tables", "表格（中英文对照）", level=1)

# Table 1 (EN + ZH)
t1_en = [
    ["Calycosin", "Mode 1", "29.53", "0.885", "2.446", "Intramolecular B-ring torsion τ(C–C) + methoxy rocking"],
    ["", "Mode 2", "44.42", "1.332", "1.643", "Chromone core out-of-plane twisting (above 1.04 THz)"],
    ["Spinosin", "Mode 2", "18.40", "0.552", "0.155", "Dual C-glycosyl intramolecular breathing and shearing"],
    ["", "Mode 3", "20.17", "0.605", "1.241", "C-glycosyl rocking relative to flavone core + OH shift"],
    ["", "Mode 4", "29.57", "0.886", "0.609", "Flavone core low-frequency out-of-plane bending"],
    ["", "Mode 5", "32.64", "0.979", "1.239", "4'-Hydroxyphenyl B-ring out-of-plane flapping"],
]
t1_zh = [
    ["毛蕊异黄酮", "Mode 1", "29.53", "0.885", "2.446", "分子内 B 环二面角扭转 τ(C–C) + 甲氧基摇摆"],
    ["", "Mode 2", "44.42", "1.332", "1.643", "色酮母核面外扭转（高于 1.04 THz 截断）"],
    ["斯皮诺素", "Mode 2", "18.40", "0.552", "0.155", "双碳糖基分子内呼吸与剪切振动"],
    ["", "Mode 3", "20.17", "0.605", "1.241", "碳糖基相对黄酮母核摇摆 + 羟基位移"],
    ["", "Mode 4", "29.57", "0.886", "0.609", "黄酮母核低频面外弯曲"],
    ["", "Mode 5", "32.64", "0.979", "1.239", "4'-羟基苯环 B 环面外扑动"],
]
m.add_three_line_table("Table 1. Theoretical intramolecular vibrational mode benchmarks of calycosin and spinosin at B3LYP-D3(BJ)/6-31G(d).",
                       ["Compound", "Mode", "Freq. (cm⁻¹)", "Freq. (THz)", "IR Int. (km/mol)", "Intramolecular Vibrational Assignment"],
                       t1_en, [1150, 800, 1050, 1000, 1260, 4100])
m.add_three_line_table("表 1. 毛蕊异黄酮与斯皮诺素在 B3LYP-D3(BJ)/6-31G(d) 水平下的分子内太赫兹振动基准归属",
                       ["化合物", "模态", "波数 (cm⁻¹)", "频率 (THz)", "红外强度 (km/mol)", "分子内振动归属"],
                       t1_zh, [1150, 800, 1050, 1000, 1260, 4100], is_zh=True)

# Table 2 (EN + ZH)
t2_en, t2_zh, bold_t2 = [], [], []
zh_cls_map = {
    'Datong (SX)': '山西大同', 'Guyang (IM)': '内蒙古固阳', 'Qujing (YN)': '云南曲靖', 'Gansu (GS)': '甘肃',
    'Boxed (HB)': '盒养河北', 'SJZ/BZ': '石家庄/亳州信盛常', 'Bulk-Bag': '散装大袋', 'Bulk-50g': '散装 50g', 'Tongrentang (AH)': '同仁堂亳州',
    'Bozhou (AH)': '安徽亳州', 'Leishan (GZ)': '贵州雷山', 'Changbai (JL)': '吉林长白山', 'Yunnan (YN)': '云南'
}
for en_m, zh_m, ds_obj in [
    ("Root (Astragali Radix)", "根茎（黄芪）", HQ),
    ("Seed (Ziziphi Spinosae)", "种子（酸枣仁）", SZ),
    ("Tuber (Gastrodia elata)*", "块茎（天麻）*", TM),
]:
    for idx_c, c in enumerate(ds_obj["classes"]):
        pc = ds_obj["per_class"][c]
        t2_en.append([en_m if idx_c == 0 else "", c, str(pc["support"]), str(pc["correct"]), f"{pc['precision']:.2f}", f"{pc['recall']:.2f}", f"{pc['f1']:.4f}"])
        t2_zh.append([zh_m if idx_c == 0 else "", zh_cls_map[c], str(pc["support"]), str(pc["correct"]), f"{pc['precision']:.2f}", f"{pc['recall']:.2f}", f"{pc['f1']:.4f}"])
    prop = ds_obj["proposed"]
    tot_c = sum(ds_obj["per_class"][c]["correct"] for c in ds_obj["classes"])
    bold_t2.append(len(t2_en))
    t2_en.append(["", f"Overall / Macro ({prop['mean']:.2f} ± {prop['sd']:.2f}%)", str(ds_obj["n_samples"]), str(tot_c), f"{prop['macro_prec']:.2f}", f"{prop['macro_rec']:.2f}", f"{prop['macro_f1']:.4f}"])
    t2_zh.append(["", f"总体 / 宏平均（{prop['mean']:.2f} ± {prop['sd']:.2f}%）", str(ds_obj["n_samples"]), str(tot_c), f"{prop['macro_prec']:.2f}", f"{prop['macro_rec']:.2f}", f"{prop['macro_f1']:.4f}"])

m.add_three_line_table("Table 2. Quantitative classification metrics of the locked Dual-View SW-MCUVE-Manifold pipeline under strict double-nested 5-fold CV (post-QC, Macro-averaged).",
                       ["Botanical Matrix", "Origin / Format", "n", "Correct", "Prec. (%)", "Rec. (%)", "F1"],
                       t2_en, [1850, 2850, 620, 780, 1120, 1040, 1100], bold_last_rows=bold_t2,
                       note="*Independent cross-matrix methodological validation with the identical locked architecture.")
m.add_three_line_table("表 2. 统一锁死 Dual-View SW-MCUVE-Manifold 流程在三大药材上的双层严格嵌套 5 折分类指标（质控后，宏平均）",
                       ["植物基质", "产地 / 规格", "样本数", "命中数", "精确率 (%)", "召回率 (%)", "F1 值"],
                       t2_zh, [1850, 2850, 620, 780, 1120, 1040, 1100], bold_last_rows=bold_t2,
                       note="*表示一字不改迁移同一锁死架构的跨基质独立方法学验证。", is_zh=True)

# Table 3 (EN + ZH)
abl_zh_map = {
    'Full Proposed (Dual-View SW-MCUVE-Manifold)': '完整提出模型（双视图流形）',
    'w/o Amplitude-Preserving View (SNV Only)': '剔除保幅视图（仅 SNV）',
    'w/o Intra-Sample SNV View (Amplitude Only)': '剔除 SNV 视图（仅保幅）',
    'w/o Purified Manifold (lambda=0)': '剔除净化流形（λ = 0）',
    'w/o Refractive Index (Abs Only)': '剔除折射率通道（仅吸收）',
}
t3_en, t3_zh, bold_t3 = [], [], []
for en_m, zh_m, ds_obj in [
    ("Astragali Radix (n=397)", "黄芪（n=397）", HQ),
    ("Ziziphi Spinosae (n=500)", "酸枣仁（n=500）", SZ),
    ("Gastrodia elata (n=404)", "天麻（n=404）", TM),
]:
    ref_acc = ds_obj["proposed"]["acc"]
    for idx_k, (cfg_n, met) in enumerate(ds_obj["ablation"].items()):
        if idx_k == 0:
            bold_t3.append(len(t3_en))
        dlt_en = "Reference" if idx_k == 0 else f"{met['acc'] - ref_acc:+.2f}%"
        dlt_zh = "基准" if idx_k == 0 else f"{met['acc'] - ref_acc:+.2f}%"
        t3_en.append([en_m if idx_k == 0 else "", cfg_n, f"{met['acc']:.2f}", f"{met['mean']:.2f} ± {met['sd']:.2f}", dlt_en, f"{met['macro_f1']:.4f}"])
        t3_zh.append([zh_m if idx_k == 0 else "", abl_zh_map[cfg_n], f"{met['acc']:.2f}", f"{met['mean']:.2f} ± {met['sd']:.2f}", dlt_zh, f"{met['macro_f1']:.4f}"])
m.add_three_line_table("Table 3. Module knockout ablation study across all three matrices (strict double-nested 5-fold CV).",
                       ["Matrix", "Configuration", "Acc (%)", "Mean ± SD (%)", "Δ Acc", "Macro-F1"],
                       t3_en, [1950, 2950, 1000, 1450, 1010, 1000], bold_last_rows=bold_t3)
m.add_three_line_table("表 3. 三大药材同划分双层严格嵌套模块敲除消融实验结果",
                       ["药材基质", "消融配置", "总准确率 (%)", "5 折均值 ± 标准差 (%)", "变化量", "宏 F1"],
                       t3_zh, [1950, 2950, 1000, 1450, 1010, 1000], bold_last_rows=bold_t3, is_zh=True)

# Table 4 (EN + ZH)
base_zh_map = {
    'PLS-DA': 'PLS-DA',
    'Random Forest': '随机森林 (RF)',
    'Standard RBF-SVM (Full Spectrum)': '全谱标准 RBF-SVM',
    'Hard MC-UVE-SVM (Gen-1 Baseline)': '硬截断 MC-UVE-SVM（Gen-1）',
    'Proposed (Dual-View SW-MCUVE-Manifold)': '本文模型（Dual-View 流形）',
}
t4_en, t4_zh, bold_t4 = [], [], []
for en_m, zh_m, ds_obj in [
    ("Astragali Radix (n=397)", "黄芪（n=397）", HQ),
    ("Ziziphi Spinosae (n=500)", "酸枣仁（n=500）", SZ),
    ("Gastrodia elata (n=404)", "天麻（n=404）", TM),
]:
    items = list(ds_obj["baselines"].items())
    for idx_b, (mn, met) in enumerate(items):
        if idx_b == len(items) - 1:
            bold_t4.append(len(t4_en))
        t4_en.append([en_m if idx_b == 0 else "", mn, f"{met['acc']:.2f}", f"{met['mean']:.2f} ± {met['sd']:.2f}", f"{met['macro_prec']:.2f}", f"{met['macro_rec']:.2f}", f"{met['macro_f1']:.4f}"])
        t4_zh.append([zh_m if idx_b == 0 else "", base_zh_map[mn], f"{met['acc']:.2f}", f"{met['mean']:.2f} ± {met['sd']:.2f}", f"{met['macro_prec']:.2f}", f"{met['macro_rec']:.2f}", f"{met['macro_f1']:.4f}"])
m.add_three_line_table("Table 4. Baseline model comparison under identical strict double-nested 5-fold CV splits.",
                       ["Matrix", "Model", "Acc (%)", "Mean ± SD (%)", "Prec. (%)", "Rec. (%)", "Macro-F1"],
                       t4_en, [1950, 2550, 860, 1380, 880, 840, 900], bold_last_rows=bold_t4)
m.add_three_line_table("表 4. 三大药材同划分双层严格嵌套基线模型横向对比",
                       ["药材基质", "对比模型", "准确率 (%)", "均值 ± 标准差 (%)", "精确率 (%)", "召回率 (%)", "宏 F1"],
                       t4_zh, [1950, 2550, 860, 1380, 880, 840, 900], bold_last_rows=bold_t4, is_zh=True)

# Table 5 (EN + ZH): Zero-Leakage Audits
t5_en, t5_zh = [], []
for ds_key, en_l, zh_l in [
    ("Astragali Radix (Root)", "Astragali Radix (Root)", "黄芪（根茎）"),
    ("Ziziphi Spinosae (Seed)", "Ziziphi Spinosae (Seed)", "酸枣仁（种子）"),
    ("Gastrodia elata (Tuber)", "Gastrodia elata (Tuber)", "天麻（块茎）"),
]:
    raw_r = AUDIT["audit_2_qc_comparison"][ds_key]["raw_all"]
    ms_r  = AUDIT["audit_3_multi_seed"][ds_key]
    ys_r  = AUDIT["audit_4_y_scrambling"][ds_key]
    t5_en.append([en_l, f"{raw_r['acc']:.2f}% (n={raw_r['n']})", f"{ms_r['multi_seed_mean']:.2f}% ± {ms_r['multi_seed_sd']:.2f}%",
                  f"{ys_r['scrambled_acc']:.2f}% ± {ys_r['scrambled_sd']:.2f}%", f"{ys_r['theoretical_chance_pct']:.2f}%"])
    t5_zh.append([zh_l, f"{raw_r['acc']:.2f}%（n={raw_r['n']}）", f"{ms_r['multi_seed_mean']:.2f}% ± {ms_r['multi_seed_sd']:.2f}%",
                  f"{ys_r['scrambled_acc']:.2f}% ± {ys_r['scrambled_sd']:.2f}%", f"{ys_r['theoretical_chance_pct']:.2f}%"])
m.add_three_line_table("Table 5. Summary of four-stage zero-leakage statistical audits (differential blind-test perturbation deviation = 0.00e+00 across all training states and 80 remaining test predictions).",
                       ["Botanical Matrix", "Raw Unfiltered Acc", "3-Seed Mean ± SD", "Y-Scrambling Acc", "Random Chance"],
                       t5_en, [2200, 1800, 1900, 1960, 1500])
m.add_three_line_table("表 5. 四重无泄漏统计审计汇总（盲测微分扰动探针在训练状态与其余 80 份盲测预测上的偏差均为 0.00e+00）",
                       ["植物基质", "原始未清洗准确率", "三随机种子均值 ± SD", "Y-标签置换准确率", "理论随机基准"],
                       t5_zh, [2200, 1800, 1900, 1960, 1500], is_zh=True)

# --- End-Matter Statements & Declarations (Exact Format of Reference Document, Bilingual!) ---
m.add_page_break()
m.add_bilingual_heading("Acknowledgements", "致谢", level=1)
m.add_bilingual_para(
    "The first author thanks the supervisor and corresponding author, Yin Shen, for providing the experimental data "
    "and for guidance and support in manuscript preparation and submission. The authors also thank Yiyi Yang at the "
    "Terahertz Spectroscopy Laboratory of Southwest University (Chongqing, China) for acquiring and sharing the "
    "terahertz time-domain spectral records.",
    "第一作者感谢导师及通讯作者沈印（Yin Shen）提供实验数据，并在论文撰写和投稿方面给予指导与支持；同时感谢西南大学太赫兹光谱实验室（中国重庆）杨易易采集并分享太赫兹时域光谱数据。",
    first_line_indent=0
)

m.add_bilingual_heading("AI disclosure", "AI 使用披露", level=1)
m.add_bilingual_para(
    "AI-assisted tools were used during manuscript preparation to verify Python code, run statistical leakage audits, "
    "compile tables and figures, and refine English expression. All experimental design decisions, data integrity "
    "checks, scientific interpretations, and final manuscript content were reviewed and approved by the authors.",
    "在论文准备过程中，作者借助 AI 工具辅助核验 Python 代码、执行统计无泄漏审计、整理图表并润色英文表达。所有实验设计决策、数据完整性核查、科学解释及最终文稿内容均由作者审核并承担全部责任。",
    first_line_indent=0
)

m.add_bilingual_heading("Author contributions", "作者贡献", level=1)
m.add_bilingual_para(
    "Sihao Liu designed the analytical workflow, optimized the Dual-View SW-MCUVE-Manifold algorithms, conducted the "
    "DFT vibrational benchmark calculations, and wrote the manuscript. Ziyuan Zhu assisted with experimental "
    "methodology verification, code review, and manuscript refinement. Yin Shen provided the experimental data, "
    "supervised the project, and guided manuscript preparation and submission.",
    "刘厶豪（Sihao Liu）负责分析流程设计、Dual-View SW-MCUVE-Manifold 算法优化、DFT 振动基准计算及论文撰写。朱子元（Ziyuan Zhu）协助实验方法学核查、代码复核与论文完善。沈印（Yin Shen）提供实验数据、指导课题研究及论文准备与投稿。",
    first_line_indent=0
)

m.add_bilingual_heading("Statements and declarations", "声明", level=1)

m.add_bilingual_heading("Ethical considerations", "伦理事项", level=2)
m.add_bilingual_para(
    "This study analyzed herbal-material spectral records and involved neither human participants nor animals. "
    "Ethical approval was not required.",
    "本研究分析药材光谱记录，不涉及人体参与者或动物，无需伦理审批。",
    first_line_indent=0
)

m.add_bilingual_heading("Consent to participate", "参与同意", level=2)
m.add_bilingual_para("Not applicable.", "不适用。", first_line_indent=0)

m.add_bilingual_heading("Consent for publication", "发表同意", level=2)
m.add_bilingual_para("Not applicable.", "不适用。", first_line_indent=0)

m.add_bilingual_heading("Declaration of conflicting interest", "利益冲突声明", level=2)
m.add_bilingual_para(
    "The authors declared no potential conflicts of interest with respect to the research, authorship, and/or "
    "publication of this article.",
    "作者声明，本研究、论文署名及发表均无潜在利益冲突。",
    first_line_indent=0
)

m.add_bilingual_heading("Funding statement", "资金声明", level=2)
m.add_bilingual_para(
    "The authors received no financial support for the research, authorship, or publication of this article.",
    "本研究、论文撰写和发表未获得资金支持。",
    first_line_indent=0
)

m.add_bilingual_heading("Author approval", "作者批准", level=2)
m.add_bilingual_para(
    "All authors have read and approved the manuscript and accept responsibility for the accuracy and integrity of "
    "the work. This manuscript is not under consideration elsewhere.",
    "所有作者均已审阅并批准稿件，对工作的准确性和完整性承担责任。稿件未同时在其他期刊审理。",
    first_line_indent=0
)

m.add_bilingual_heading("Data availability", "数据可获得性", level=2)
m.add_bilingual_para(
    "The cached dual-channel terahertz spectra, origin/format labels, locked analysis scripts, 300 DPI figures, and "
    "four-stage zero-leakage audit logs are publicly available at "
    "https://github.com/l114514sh-cmyk/THz-TCM-DualView-Manifold and in the accompanying supplementary files. "
    "Yiyi Yang acquired and shared the spectral records; Yin Shen provided the dataset for this study as part of a "
    "shared research resource also used in other supervised studies.",
    "双通道太赫兹光谱缓存、产地/规格标签、统一锁死分析脚本、300 DPI 图表及四重无泄漏审计日志已公开发布于 "
    "https://github.com/l114514sh-cmyk/THz-TCM-DualView-Manifold 并随补充材料提供。杨易易采集并分享了光谱记录；"
    "沈印提供了本研究所用的数据，该数据亦作为共享研究资源用于其他指导研究。",
    first_line_indent=0
)

m.add_bilingual_heading("Supplemental material", "补充材料", level=2)
m.add_bilingual_para(
    "Supplemental material provides the independent Gastrodia elata cross-matrix validation figures (Figure S1a–b), "
    "complete double-nested per-fold summaries, and machine-readable JSON logs of the four-stage zero-leakage "
    "statistical audits.",
    "补充材料提供天麻跨基质独立验证图表（图 S1a–b）、完整双层嵌套逐折结果汇总，以及四重无泄漏统计审计的机器可读 JSON 日志。",
    first_line_indent=0
)

# --- 37 Verified Real References ---
m.add_page_break()
m.add_bilingual_heading("References", "参考文献", level=1)
REFS = [
    "[1] J. Luo, Y. Liu, Q. Wei, Q. Li, H. Pu, Terahertz fingerprint detection and density functional theory analysis of the flavonoids from dried tangerine peel, Mod. Food Sci. Technol. 39 (2023) 304–311.",
    "[2] S. Pan, Research method for rapid identification and content detection of Chinese herbals based on terahertz spectroscopy, Ph.D. thesis, Guilin University of Electronic Technology, 2022.",
    "[3] S. Pan, H. Zhang, Z. Li, et al., Classification of ginseng with different growth ages based on terahertz spectroscopy and machine learning algorithm, Optik 236 (2021) 166322.",
    "[4] T.D. Dorney, R.G. Baraniuk, D.M. Mittleman, Material parameter estimation with terahertz time-domain spectroscopy, J. Opt. Soc. Am. A 18 (2001) 1562–1571.",
    "[5] L. Duvillaret, F. Garet, J.L. Coutaz, Highly precise determination of optical constants and sample thickness in terahertz time-domain spectroscopy, Appl. Opt. 38 (1999) 409–415.",
    "[6] M. Yin, S. Tang, M. Tong, Identification of edible oils using terahertz spectroscopy combined with genetic algorithm and partial least squares discriminant analysis, Anal. Methods 8 (2016) 2794–2798.",
    "[7] F. Qu, L. Lin, C. Cai, et al., Terahertz fingerprint characterization of 2,4-dichlorophenoxyacetic acid and its enhanced detection in food matrices combined with spectral baseline correction, Food Chem. 334 (2020) 127474.",
    "[8] Z. Zhu, J. Zhang, Y. Song, et al., Broadband terahertz signatures and vibrations of dopamine, Analyst 145 (2020) 6006–6013.",
    "[9] Y. Ueno, R. Rungsawang, I. Tomita, et al., Quantitative measurements of amino acids by terahertz time-domain transmission spectroscopy, Anal. Chem. 78 (2006) 5424–5428.",
    "[10] L. Xie, C. Wang, M. Chen, et al., Temperature-dependent terahertz vibrational spectra of tetracycline and its degradation products, Spectrochim. Acta Part A 222 (2019) 117179.",
    "[11] M. Tonouchi, Cutting-edge terahertz technology, Nat. Photonics 1 (2007) 97–105.",
    "[12] E. Pickwell, V.P. Wallace, Biomedical applications of terahertz technology, J. Phys. D: Appl. Phys. 39 (2006) R301–R310.",
    "[13] P.F. Taday, Applications of terahertz spectroscopy to pharmaceutical sciences, Philos. Trans. R. Soc. Lond. A 362 (2004) 351–363.",
    "[14] J.A. Zeitler, P.F. Taday, D.A. Newnham, M. Pepper, K.C. Gordon, T. Rades, Terahertz pulsed spectroscopy and imaging in the pharmaceutical setting—a review, J. Pharm. Pharmacol. 59 (2007) 209–223.",
    "[15] C.J. Strachan, T. Rades, D.A. Newnham, K.C. Gordon, M. Pepper, P.F. Taday, Using terahertz pulsed spectroscopy to study crystallinity of pharmaceutical materials, Chem. Phys. Lett. 390 (2004) 20–24.",
    "[16] M. Walther, B.M. Fischer, P.U. Jepsen, Noncovalent intermolecular forces in polycrystalline and amorphous saccharides in the far infrared, Chem. Phys. 288 (2003) 261–268.",
    "[17] P.U. Jepsen, B.M. Fischer, Dynamic range in terahertz time-domain transmission and reflection spectroscopy, Opt. Lett. 30 (2005) 29–31.",
    "[18] V.P. Wallace, P.F. Taday, A.J. Fitzgerald, et al., Terahertz pulsed imaging and spectroscopy for biomedical and pharmaceutical applications, Faraday Discuss. 126 (2004) 255–263.",
    "[19] A. Savitzky, M.J.E. Golay, Smoothing and differentiation of data by simplified least squares procedures, Anal. Chem. 36 (1964) 1627–1639.",
    "[20] R.J. Barnes, M.S. Dhanoa, S.J. Lister, Standard normal variate transformation and de-trending of near-infrared diffuse reflectance spectra, Appl. Spectrosc. 43 (1989) 772–777.",
    "[21] V. Centner, D.L. Massart, O.E. de Noord, S. de Jong, B.M. Vandeginste, C. Sterna, Elimination of uninformative variables for multivariate calibration, Anal. Chem. 68 (1996) 3851–3858.",
    "[22] W. Cai, Y. Li, X. Shao, A variable selection method based on uninformative variable elimination for multivariate calibration of near-infrared spectra, Chemom. Intell. Lab. Syst. 90 (2008) 188–194.",
    "[23] H. Li, Y. Liang, Q. Xu, D. Cao, Key wavelengths screening using competitive adaptive reweighted sampling method for multivariate calibration, Anal. Chim. Acta 648 (2009) 77–84.",
    "[24] S. Wold, M. Sjöström, L. Eriksson, PLS-regression: a basic tool of chemometrics, Chemom. Intell. Lab. Syst. 58 (2001) 109–130.",
    "[25] M. Barker, W. Rayens, Partial least squares for discrimination, J. Chemom. 17 (2003) 166–173.",
    "[26] O. Ledoit, M. Wolf, A well-conditioned estimator for large-dimensional covariance matrices, J. Multivar. Anal. 88 (2004) 365–411.",
    "[27] C. Cortes, V. Vapnik, Support-vector networks, Mach. Learn. 20 (1995) 273–297.",
    "[28] L. Breiman, Random forests, Mach. Learn. 45 (2001) 5–32.",
    "[29] S. Varma, R. Simon, Bias in error estimation when using cross-validation for model selection, BMC Bioinformatics 7 (2006) 91.",
    "[30] G.C. Cawley, N.L.C. Talbot, On over-fitting in model selection and subsequent selection bias in performance evaluation, J. Mach. Learn. Res. 11 (2010) 2079–2107.",
    "[31] A.D. Becke, Density-functional thermochemistry. III. The role of exact exchange, J. Chem. Phys. 98 (1993) 5648–5652.",
    "[32] C. Lee, W. Yang, R.G. Parr, Development of the Colle-Salvetti correlation-energy formula into a functional of the electron density, Phys. Rev. B 37 (1988) 785–789.",
    "[33] S. Grimme, S. Ehrlich, L. Goerigk, Effect of the damping function in dispersion corrected density functional theory, J. Comput. Chem. 32 (2011) 1456–1465.",
    "[34] T. Lu, F. Chen, Multiwfn: A multifunctional wavefunction analyzer, J. Comput. Chem. 33 (2012) 580–592.",
    "[35] M.H. Jamróz, Vibrational energy distribution analysis (VEDA): Scopes and limitations, Spectrochim. Acta Part A 114 (2013) 220–230.",
    "[36] F. Pedregosa, G. Varoquaux, A. Gramfort, et al., Scikit-learn: Machine learning in Python, J. Mach. Learn. Res. 12 (2011) 2825–2830.",
    "[37] Chinese Pharmacopoeia Commission, Pharmacopoeia of the People's Republic of China (2025 Edition), Part I, China Medical Science Press, Beijing, 2025."
]
for ref in REFS:
    m.add_para(ref, align="both", space_before=0, space_after=45, line=240, size_pt=9.5)

m_path = os.path.join(OUT_DIR, "Manuscript_Final.docx")
m.save(m_path)
print(f"[OK] Saved bilingual {m_path} with {len(m.media_files)} embedded 300 DPI figures and {len(REFS)} real references!")
