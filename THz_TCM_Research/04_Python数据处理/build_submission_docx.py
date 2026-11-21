import os
import re
import json
import zipfile
from pathlib import Path
from PIL import Image
from xml.sax.saxutils import escape

# Project-relative paths (zero hardcoded local paths)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
ROOT_DIR = PROJECT_DIR.parent
RES_DIR = PROJECT_DIR / "05_实验结果" / "模型结果"
OUT_DIR = PROJECT_DIR / "06_论文写作"
SUB_FIG_DIR = OUT_DIR / "Submission_Figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

with open(RES_DIR / "Unified_Double_Nested_Summary.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)
with open(RES_DIR / "Strict_Leakage_Audit_Report.json", "r", encoding="utf-8") as f:
    AUDIT = json.load(f)

HQ = DATA["Astragali_Radix"]
SZ = DATA["Ziziphi_Spinosae_Semen"]
TM = DATA["Gastrodia_elata"]


# ==============================================================================
# Native OOXML (.docx) Builder: Supports BOTH Pure-EN and Bilingual (EN+ZH)
# ==============================================================================
class DocxBuilder:
    def __init__(self, bilingual=False):
        self.bilingual = bilingual
        self.body_parts = []
        self.media_files = []
        self._img_counter = 0

    @staticmethod
    def _run(text, bold=False, italic=False, size_pt=11.0, color=None):
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

    def add_para(self, runs_or_text, align="both", space_before=0, space_after=100, line=310,
                 first_line_indent=0, bold=False, italic=False, size_pt=11.0, color=None, keep_next=False):
        ppr = [f'<w:spacing w:before="{space_before}" w:after="{space_after}" w:line="{line}" w:lineRule="auto"/>']
        if align:
            ppr.append(f'<w:jc w:val="{align}"/>')
        if first_line_indent:
            ppr.append(f'<w:ind w:firstLine="{first_line_indent}"/>')
        if keep_next:
            ppr.append('<w:keepNext/>')
        inner = self._run(runs_or_text, bold=bold, italic=italic, size_pt=size_pt, color=color) if isinstance(runs_or_text, str) else "".join(runs_or_text)
        self.body_parts.append(f'<w:p><w:pPr>{"".join(ppr)}</w:pPr>{inner}</w:p>')

    def add_title(self, en_title, zh_title=""):
        self.add_para(en_title, align="center", space_before=80, space_after=90, line=300, bold=True, size_pt=14.0)
        if self.bilingual and zh_title:
            self.add_para(zh_title, align="center", space_before=0, space_after=150, line=300, bold=True, size_pt=12.5, color="2B4C7E")

    def add_heading(self, en_text, zh_text="", level=1):
        sz_en = 12.5 if level == 1 else 11.2
        sz_zh = 11.2 if level == 1 else 10.2
        sb = 220 if level == 1 else 150
        self.add_para(en_text, align="left", space_before=sb, space_after=40 if self.bilingual else 80,
                      line=280, bold=True, italic=(level == 2), size_pt=sz_en, keep_next=True)
        if self.bilingual and zh_text:
            self.add_para(zh_text, align="left", space_before=0, space_after=85,
                          line=260, bold=True, size_pt=sz_zh, color="2B4C7E", keep_next=True)

    def add_body(self, en_text, zh_text="", first_line_indent=420):
        self.add_para(en_text, align="both", space_before=20, space_after=60 if self.bilingual else 110,
                      line=310, first_line_indent=first_line_indent, size_pt=11.0)
        if self.bilingual and zh_text:
            self.add_para(zh_text, align="both", space_before=0, space_after=125,
                          line=300, first_line_indent=first_line_indent, size_pt=10.4, color="333333")

    def add_bullet(self, en_text, zh_text=""):
        self.add_para("•  " + en_text, align="both", space_before=20, space_after=40 if self.bilingual else 80,
                      line=290, size_pt=10.6)
        if self.bilingual and zh_text:
            self.add_para("   " + zh_text, align="both", space_before=0, space_after=90,
                          line=280, size_pt=10.0, color="333333")

    def add_equation(self, eq_text, eq_num):
        eq_r = self._run(eq_text, italic=True, size_pt=10.5)
        num_r = self._run(f"({eq_num})", bold=False, size_pt=10.5)
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

    def add_image(self, img_path, width_inches=5.6, max_height_inches=7.2,
                  en_prefix="", en_caption="", zh_prefix="", zh_caption=""):
        img_path = Path(img_path)
        if not img_path.exists():
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
        self.media_files.append((rel_id, arc_name, str(img_path)))

        drawing_xml = (
            f'<w:p><w:pPr><w:spacing w:before="120" w:after="50"/><w:jc w:val="center"/><w:keepNext/></w:pPr>'
            '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{self._img_counter}" name="Picture {self._img_counter}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:nvPicPr><pic:cNvPr id="{self._img_counter}" name="Picture {self._img_counter}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
        )
        self.body_parts.append(drawing_xml)
        if en_caption:
            self.add_para([self._run(en_prefix, bold=True, size_pt=9.6), self._run(en_caption, size_pt=9.6)],
                          align="both", space_before=20, space_after=40 if self.bilingual else 130, line=250)
        if self.bilingual and zh_caption:
            self.add_para([self._run(zh_prefix, bold=True, size_pt=9.4, color="2B4C7E"),
                           self._run(zh_caption, size_pt=9.4, color="333333")],
                          align="both", space_before=0, space_after=130, line=250)

    def add_table(self, headers, rows, col_widths_dxa, en_title="", zh_title="", bold_row_indices=None, font_pt=8.8):
        if en_title:
            self.add_para(en_title, align="left", space_before=140, space_after=30 if self.bilingual else 60,
                          line=250, bold=True, size_pt=10.0, keep_next=True)
        if self.bilingual and zh_title:
            self.add_para(zh_title, align="left", space_before=0, space_after=60,
                          line=240, bold=True, size_pt=9.6, color="2B4C7E", keep_next=True)
        bold_set = set(bold_row_indices or [])
        total_w = sum(col_widths_dxa)
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in col_widths_dxa)
        tbl_pr = (
            f'<w:tblPr><w:tblW w:w="{total_w}" w:type="dxa"/><w:jc w:val="center"/>'
            '<w:tblBorders>'
            '<w:top w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
            '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
            '<w:left w:val="none"/><w:right w:val="none"/>'
            '<w:insideH w:val="none"/><w:insideV w:val="none"/>'
            '</w:tblBorders>'
            '<w:tblCellMar><w:top w:w="50" w:type="dxa"/><w:bottom w:w="50" w:type="dxa"/>'
            '<w:left w:w="65" w:type="dxa"/><w:right w:w="65" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        )

        def make_row(cells, is_header=False, is_bold=False):
            tr_pr = '<w:trPr><w:cantSplit/>' + ('<w:tblHeader/>' if is_header else '') + '</w:trPr>'
            tds = []
            for idx, (val, w) in enumerate(zip(cells, col_widths_dxa)):
                jc = "left" if idx == 0 else "center"
                bdr = '<w:tcBorders><w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/></w:tcBorders>' if is_header else ''
                shd = '<w:shd w:val="clear" w:color="auto" w:fill="F2F5F9"/>' if is_header else ''
                run = self._run(val, bold=(is_header or is_bold), size_pt=font_pt)
                tds.append(
                    f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{bdr}{shd}<w:vAlign w:val="center"/></w:tcPr>'
                    f'<w:p><w:pPr><w:spacing w:before="20" w:after="20" w:line="220" w:lineRule="auto"/><w:jc w:val="{jc}"/></w:pPr>{run}</w:p></w:tc>'
                )
            return f'<w:tr>{tr_pr}{"".join(tds)}</w:tr>'

        all_rows = [make_row(headers, is_header=True)]
        for r_i, row in enumerate(rows):
            all_rows.append(make_row(row, is_header=False, is_bold=(r_i in bold_set)))
        self.body_parts.append(f'<w:tbl>{tbl_pr}<w:tblGrid>{grid}</w:tblGrid>{"".join(all_rows)}</w:tbl>')
        self.add_para("", space_before=0, space_after=60, line=120, size_pt=6)

    def save(self, out_path):
        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
            'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
            'xmlns:o="urn:schemas-microsoft-com:office:office" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
            'xmlns:v="urn:schemas-microsoft-com:vml" '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
            'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">'
            '<w:body>'
            + "".join(self.body_parts)
            + '<w:sectPr>'
            '<w:pgSz w:w="12240" w:h="15840"/>'
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>'
            '</w:sectPr></w:body></w:document>'
        )
        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>'
        )
        rels_root = (
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
            f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{img_rels}</Relationships>'
        )
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", rels_root)
            zf.writestr("word/_rels/document.xml.rels", doc_rels)
            zf.writestr("word/document.xml", doc_xml)
            for _, arc, fp in self.media_files:
                zf.write(fp, f"word/{arc}")


# ==============================================================================
# Verified Sequential References [1]..[39] (Strictly Ordered by First Citation!)
# ==============================================================================
REFS = [
    "[1] Chinese Pharmacopoeia Commission, Pharmacopoeia of the People's Republic of China (2025 Edition), Part I, China Medical Science Press, Beijing, 2025.",
    "[2] M. Tonouchi, Cutting-edge terahertz technology, Nat. Photonics 1 (2007) 97–105.",
    "[3] E. Pickwell, V.P. Wallace, Biomedical applications of terahertz technology, J. Phys. D: Appl. Phys. 39 (2006) R301–R310.",
    "[4] P.F. Taday, Applications of terahertz spectroscopy to pharmaceutical sciences, Philos. Trans. R. Soc. Lond. A 362 (2004) 351–363.",
    "[5] J.A. Zeitler, P.F. Taday, D.A. Newnham, M. Pepper, K.C. Gordon, T. Rades, Terahertz pulsed spectroscopy and imaging in the pharmaceutical setting—a review, J. Pharm. Pharmacol. 59 (2007) 209–223.",
    "[6] C.J. Strachan, T. Rades, D.A. Newnham, K.C. Gordon, M. Pepper, P.F. Taday, Using terahertz pulsed spectroscopy to study crystallinity of pharmaceutical materials, Chem. Phys. Lett. 390 (2004) 20–24.",
    "[7] M. Walther, B.M. Fischer, P.U. Jepsen, Noncovalent intermolecular forces in polycrystalline and amorphous saccharides in the far infrared, Chem. Phys. 288 (2003) 261–268.",
    "[8] V.P. Wallace, P.F. Taday, A.J. Fitzgerald, et al., Terahertz pulsed imaging and spectroscopy for biomedical and pharmaceutical applications, Faraday Discuss. 126 (2004) 255–263.",
    "[9] Y. Ueno, R. Rungsawang, I. Tomita, et al., Quantitative measurements of amino acids by terahertz time-domain transmission spectroscopy, Anal. Chem. 78 (2006) 5424–5428.",
    "[10] L. Xie, C. Wang, M. Chen, et al., Temperature-dependent terahertz vibrational spectra of tetracycline and its degradation products, Spectrochim. Acta Part A 222 (2019) 117179.",
    "[11] Z. Zhu, J. Zhang, Y. Song, et al., Broadband terahertz signatures and vibrations of dopamine, Analyst 145 (2020) 6006–6013.",
    "[12] J. Luo, Y. Liu, Q. Wei, Q. Li, H. Pu, Terahertz fingerprint detection and density functional theory analysis of the flavonoids from dried tangerine peel, Mod. Food Sci. Technol. 39 (2023) 304–311.",
    "[13] S. Pan, H. Zhang, Z. Li, et al., Classification of ginseng with different growth ages based on terahertz spectroscopy and machine learning algorithm, Optik 236 (2021) 166322.",
    "[14] M. Yin, S. Tang, M. Tong, Identification of edible oils using terahertz spectroscopy combined with genetic algorithm and partial least squares discriminant analysis, Anal. Methods 8 (2016) 2794–2798.",
    "[15] F. Qu, L. Lin, C. Cai, et al., Terahertz fingerprint characterization of 2,4-dichlorophenoxyacetic acid and its enhanced detection in food matrices combined with spectral baseline correction, Food Chem. 334 (2020) 127474.",
    "[16] X. Zhang, H. Chen, X. Qu, S. Jiang, et al., Rapid identification of Rhizoma Coptidis origin using terahertz spectroscopy and deep learning, Spectrochim. Acta Part A 328 (2026) 127283.",
    "[17] T. Xue, P.-P. Zhang, R. Li, Q. Wang, R. Liu, Origin traceability of Angelica dahurica based on multidimensional bionic sensory, near infrared spectroscopy combined with multi-source information fusion research on rapid identification method of index components, Spectrochim. Acta Part A 365 (2026) 128729.",
    "[18] S. Pan, Research method for rapid identification and content detection of Chinese herbals based on terahertz spectroscopy, Ph.D. thesis, Guilin University of Electronic Technology, 2022.",
    "[19] R.J. Barnes, M.S. Dhanoa, S.J. Lister, Standard normal variate transformation and de-trending of near-infrared diffuse reflectance spectra, Appl. Spectrosc. 43 (1989) 772–777.",
    "[20] A. Savitzky, M.J.E. Golay, Smoothing and differentiation of data by simplified least squares procedures, Anal. Chem. 36 (1964) 1627–1639.",
    "[21] V. Centner, D.L. Massart, O.E. de Noord, S. de Jong, B.M. Vandeginste, C. Sterna, Elimination of uninformative variables for multivariate calibration, Anal. Chem. 68 (1996) 3851–3858.",
    "[22] W. Cai, Y. Li, X. Shao, A variable selection method based on uninformative variable elimination for multivariate calibration of near-infrared spectra, Chemom. Intell. Lab. Syst. 90 (2008) 188–194.",
    "[23] H. Li, Y. Liang, Q. Xu, D. Cao, Key wavelengths screening using competitive adaptive reweighted sampling method for multivariate calibration, Anal. Chim. Acta 648 (2009) 77–84.",
    "[24] S. Varma, R. Simon, Bias in error estimation when using cross-validation for model selection, BMC Bioinformatics 7 (2006) 91.",
    "[25] G.C. Cawley, N.L.C. Talbot, On over-fitting in model selection and subsequent selection bias in performance evaluation, J. Mach. Learn. Res. 11 (2010) 2079–2107.",
    "[26] L. Duvillaret, F. Garet, J.L. Coutaz, Highly precise determination of optical constants and sample thickness in terahertz time-domain spectroscopy, Appl. Opt. 38 (1999) 409–415.",
    "[27] T.D. Dorney, R.G. Baraniuk, D.M. Mittleman, Material parameter estimation with terahertz time-domain spectroscopy, J. Opt. Soc. Am. A 18 (2001) 1562–1571.",
    "[28] P.U. Jepsen, B.M. Fischer, Dynamic range in terahertz time-domain transmission and reflection spectroscopy, Opt. Lett. 30 (2005) 29–31.",
    "[29] S. Wold, M. Sjöström, L. Eriksson, PLS-regression: a basic tool of chemometrics, Chemom. Intell. Lab. Syst. 58 (2001) 109–130.",
    "[30] M. Barker, W. Rayens, Partial least squares for discrimination, J. Chemom. 17 (2003) 166–173.",
    "[31] O. Ledoit, M. Wolf, A well-conditioned estimator for large-dimensional covariance matrices, J. Multivar. Anal. 88 (2004) 365–411.",
    "[32] C. Cortes, V. Vapnik, Support-vector networks, Mach. Learn. 20 (1995) 273–297.",
    "[33] F. Pedregosa, G. Varoquaux, A. Gramfort, et al., Scikit-learn: Machine learning in Python, J. Mach. Learn. Res. 12 (2011) 2825–2830.",
    "[34] L. Breiman, Random forests, Mach. Learn. 45 (2001) 5–32.",
    "[35] A.D. Becke, Density-functional thermochemistry. III. The role of exact exchange, J. Chem. Phys. 98 (1993) 5648–5652.",
    "[36] C. Lee, W. Yang, R.G. Parr, Development of the Colle-Salvetti correlation-energy formula into a functional of the electron density, Phys. Rev. B 37 (1988) 785–789.",
    "[37] S. Grimme, S. Ehrlich, L. Goerigk, Effect of the damping function in dispersion corrected density functional theory, J. Comput. Chem. 32 (2011) 1456–1465.",
    "[38] T. Lu, F. Chen, Multiwfn: A multifunctional wavefunction analyzer, J. Comput. Chem. 33 (2012) 580–592.",
    "[39] M.H. Jamróz, Vibrational energy distribution analysis (VEDA): Scopes and limitations, Spectrochim. Acta Part A 114 (2013) 220–230.",
]


# ==============================================================================
# Helper Metrics Extraction
# ==============================================================================
hq_p = HQ["proposed_pellet_grouped"]
sz_p = SZ["proposed_pellet_grouped"]
tm_p = TM["proposed_pellet_grouped"]
hq_u = HQ["proposed_ungrouped_ref"]
sz_u = SZ["proposed_ungrouped_ref"]
tm_u = TM["proposed_ungrouped_ref"]

avg_scan_prop = (hq_p["acc"] + sz_p["acc"] + tm_p["acc"]) / 3.0
avg_pellet_prop = (hq_p["pellet_acc"] + sz_p["pellet_acc"] + tm_p["pellet_acc"]) / 3.0


# ==============================================================================
# 1. Highlights (<= 85 characters per bullet, Elsevier SAA guideline)
# ==============================================================================
HIGHLIGHTS = [
    "Dual-view THz spectroscopy combines scatter-attenuated and dielectric-amplitude cues.",
    "Pellet-grouped double-nested CV prevents replicate-scan leakage across 262 pellets.",
    "Pellet majority-vote reaches 92.5% (root), 100.0% (seed), and 100.0% (tuber).",
    "Input-controlled baselines with pellet bootstrap separate feature vs model gain.",
    "DFT modes (0.55–0.98 THz) align tentatively with high-stability MC-UVE regions.",
]
for idx, h in enumerate(HIGHLIGHTS, 1):
    assert len(h) <= 85, f"Highlight {idx} exceeds 85 chars ({len(h)}): {h}"

hl = DocxBuilder(bilingual=False)
hl.add_para("Highlights", align="left", bold=True, size_pt=13.5, space_after=120)
for h in HIGHLIGHTS:
    hl.add_bullet(h)
hl.save(OUT_DIR / "Highlights.docx")
print("[OK] Saved Highlights.docx (all 5 bullets <= 85 chars)")


# ==============================================================================
# 2. Cover Letter (Strictly in Corresponding Author Yin Shen's Name)
# ==============================================================================
cl = DocxBuilder(bilingual=False)
cl.add_para("Cover Letter", align="center", bold=True, size_pt=14, space_after=160)
cl.add_para("Dear Editor-in-Chief and Editorial Board of Spectrochimica Acta Part A: Molecular and Biomolecular Spectroscopy,",
            align="left", space_after=110)
cl.add_para(
    "On behalf of my co-authors (Sihao Liu and Ziyuan Zhu), I am pleased to submit our original research manuscript "
    "entitled \"Dual-View Terahertz Spectroscopy and Stability-Weighted Chemometrics for Classification of Traditional "
    "Chinese Medicinal Materials Across Distinct Botanical Matrices\" for consideration for publication in "
    "Spectrochimica Acta Part A: Molecular and Biomolecular Spectroscopy.",
    first_line_indent=420, space_after=110
)
cl.add_para(
    "Terahertz time-domain spectroscopy (THz-TDS) provides direct access to low-frequency collective and skeletal "
    "vibrational dynamics (0.22–1.04 THz), yet robust chemometric classification across botanically diverse Traditional "
    "Chinese Medicinal (TCM) materials remains challenged by two persistent issues: (i) the trade-off between "
    "suppressing Mie scattering in fibrous roots and preserving absolute dielectric-amplitude contrast in lipid-rich "
    "seeds, and (ii) optimistic accuracy inflation when replicate scans from the same pellet are randomly split across "
    "training and test folds.",
    first_line_indent=420, space_after=110
)
cl.add_para(
    "In this work, we analyze 1,300 quality-controlled dual-channel THz-TDS spectra acquired across 262 pure-powder "
    "pressed pellets spanning three distinct botanical matrices: fibrous roots (Astragali Radix, 80 pellets), "
    "lipid-rich seeds (Ziziphi Spinosae Semen, 100 pellets), and starchy tubers (Gastrodia elata, 82 pellets). "
    "Our key contributions are: (1) an intra-sample Dual-View representation paired with stability-weighted MC-UVE "
    "and subspace-purified Ledoit–Wolf shrinkage LDA; (2) strict pellet-grouped double-nested 5-fold cross-validation "
    "(StratifiedGroupKFold) that locks all 5 replicate scans per pellet together, achieving 87.66%, 96.39%, and 98.51% "
    "scan-level accuracies and 92.50%, 100.00%, and 100.00% pellet-level majority-vote accuracies while explicitly "
    "quantifying replicate-scan optimism; (3) input-controlled baseline benchmarks with paired pellet-cluster bootstrap "
    "95% confidence intervals and a 30-permutation pellet-level Y-scrambling audit (empirical p = 0.0323); and "
    "(4) tentative gas-phase B3LYP-D3(BJ)/6-31G(d) vibrational benchmarks aligned against fold-averaged MC-UVE stability "
    "profiles. All cached datasets, relative-path Python scripts, and audit logs are openly archived on GitHub.",
    first_line_indent=420, space_after=110
)
cl.add_para(
    "We confirm that this manuscript is original, has not been published previously, and is not under consideration "
    "elsewhere. All authors have approved the manuscript and declare no competing financial interests. The spectral "
    "archive is part of a shared research resource at Chongqing Medical University; the dual-view chemometric "
    "architecture, pellet-grouped nested validation, input-controlled statistical benchmarks, and MC-UVE/DFT alignment "
    "reported here are distinct from all other studies using these records.",
    first_line_indent=420, space_after=140
)
cl.add_para("Thank you very much for your time and consideration.", align="left", space_after=140)
cl.add_para("Sincerely,", align="left", space_after=60)
cl.add_para("Yin Shen, Ph.D. (Corresponding Author)", align="left", bold=True, space_after=30)
cl.add_para("Chongqing Medical University, Chongqing 400016, China", align="left", space_after=30)
cl.add_para("Email: shenyin285819016@126.com  |  ORCID: https://orcid.org/0000-0002-3221-7875", align="left", space_after=30)
cl.save(OUT_DIR / "Cover_Letter.docx")
print("[OK] Saved Cover_Letter.docx (in Yin Shen's name)")


# ==============================================================================
# 3. Main Manuscript Builder (Builds BOTH Pure-EN Submission & Bilingual Ref)
# ==============================================================================
ABSTRACT_EN = (
    "Terahertz time-domain spectroscopy (THz-TDS) captures low-frequency dielectric and collective vibrational responses "
    "of herbal materials, yet chemometric classification across distinct botanical matrices is hindered by competing "
    "preprocessing needs—suppressing particulate scattering without erasing absolute dielectric contrast—and by "
    "replicate-scan leakage when multiple scans per pellet are randomly split. Here, we investigate 1,300 "
    "quality-controlled dual-channel THz-TDS spectra (0.22–1.04 THz) from 262 pure-powder pressed pellets spanning "
    "three botanical matrices: fibrous roots (Astragali Radix, four recorded origins), lipid-rich seeds (Ziziphi "
    "Spinosae Semen, five commercial batches/specifications), and starchy tubers (Gastrodia elata, four recorded "
    "origins). We construct an intra-sample Dual-View representation combining scatter-attenuated standard normal "
    "variate (SNV) derivatives (1,790-dim) with amplitude-preserving Savitzky–Golay envelopes and derivatives "
    "(1,432-dim), coupled with stability-weighted Monte Carlo uninformative variable elimination (MC-UVE), "
    "subspace-purified Ledoit–Wolf shrinkage LDA, and an anisotropic RBF-SVM. Under strict pellet-grouped "
    "double-nested 5-fold cross-validation (locking all five replicate scans per pellet together), the fixed "
    "architecture achieves scan-level accuracies of 87.66%, 96.39%, and 98.51%, and pellet-level majority-vote "
    "accuracies of 92.50% (74/80), 100.00% (100/100), and 100.00% (82/82) across root, seed, and tuber matrices, "
    "respectively, achieving the highest cross-matrix average (94.19% scan; 97.50% pellet) across input-controlled "
    "baselines. A differential perturbation probe (0.00e+00) and 30-permutation pellet-level Y-scrambling "
    "(empirical p = 0.0323) verify pipeline isolation, while B3LYP-D3(BJ)/6-31G(d) calculations provide tentative "
    "intramolecular vibrational benchmarks aligned with MC-UVE stability profiles."
)
abs_wc = len(ABSTRACT_EN.split())
print(f"[CHECK] English Abstract Word Count = {abs_wc} words (SAA limit <= 250)")
assert abs_wc <= 250, f"Abstract too long: {abs_wc} words!"

ABSTRACT_ZH = (
    "太赫兹时域光谱（THz-TDS）可捕获药材的低频介电与集体振动响应，但跨植物基质的化学计量学分类面临两大瓶颈：一是在抑制颗粒散射的同时保留绝对介电幅值差异的预处理矛盾，二是同一压片的重复扫描被随机拆分至训练与测试集导致的乐观偏倚。"
    "本研究分析了涵盖三类植物基质的 262 片纯药粉压片共 1,300 条质控双通道太赫兹光谱（0.22–1.04 THz）：纤维根茎类（黄芪，4 个标注产地）、油脂种子类（酸枣仁，5 个商业规格/批次）和淀粉块茎类（天麻，4 个标注产地）。"
    "我们构建了严格单样本内的双视图表征，融合散射衰减标准正态变量（SNV）多尺度导数视图（1,790 维）与幅值保留 Savitzky–Golay 包络导数视图（1,432 维），并耦合稳定性加权 MC-UVE、子空间提纯 Ledoit–Wolf 收缩 LDA 与各向异性 RBF-SVM。"
    "在严格压片分组双层嵌套五折交叉验证（将每片压片的 5 次重复扫描完整锁定在同一折内）下，该固定架构在根、种子和块茎基质上分别取得了 87.66%、96.39% 和 98.51% 的逐谱准确率，以及 92.50%（74/80）、100.00%（100/100）和 100.00%（82/82）的压片多数投票准确率，在全部输入受控基线中获得最高的跨基质平均性能（逐谱 94.19%；压片 97.50%）。"
    "差分扰动探针（0.00e+00）与 30 次独立压片级标签置换检验（经验 p = 0.0323）验证了管线隔离性，B3LYP-D3(BJ)/6-31G(d) 计算则提供了与 MC-UVE 稳定性谱初步对齐的分子内振动参考基准。"
)


def build_manuscript(bilingual=False):
    m = DocxBuilder(bilingual=bilingual)

    # Title & Authors
    m.add_title(
        "Dual-View Terahertz Spectroscopy and Stability-Weighted Chemometrics for Classification of Traditional Chinese Medicinal Materials Across Distinct Botanical Matrices",
        "双视图太赫兹光谱与稳定性加权化学计量学用于跨植物基质中药材分类研究"
    )
    m.add_para(
        "Sihao Liuᵃ, Ziyuan Zhuᵃ, Yin Shenᵃ,*",
        align="center", space_before=30, space_after=40, bold=True, size_pt=11.5
    )
    if bilingual:
        m.add_para("刘厶豪ᵃ，朱子元ᵃ，沈印ᵃ,*", align="center", space_before=0, space_after=40, size_pt=10.5, color="333333")
    m.add_para(
        "ᵃ Chongqing Medical University, Chongqing 400016, China",
        align="center", italic=True, space_before=0, space_after=40, size_pt=10.2
    )
    m.add_para(
        "* Corresponding author: Yin Shen (E-mail: shenyin285819016@126.com; ORCID: https://orcid.org/0000-0002-3221-7875). "
        "First author: Sihao Liu (E-mail: L114514SH@gmail.com). Second author: Ziyuan Zhu (E-mail: zzy2630816871@gmail.com; "
        "ORCID: https://orcid.org/0009-0005-1153-4926).",
        align="center", space_before=0, space_after=150, size_pt=9.2, color="444444"
    )

    # Abstract
    m.add_heading("Abstract", "摘要", level=1)
    m.add_body(ABSTRACT_EN, ABSTRACT_ZH, first_line_indent=0)
    m.add_para(
        [m._run("Keywords: ", bold=True, size_pt=10.5),
         m._run("Terahertz time-domain spectroscopy (THz-TDS); Traditional Chinese medicinal materials; Dual-view chemometrics; Pellet-grouped nested cross-validation; Stability-weighted MC-UVE; Density functional theory (DFT)", size_pt=10.5)],
        align="left", space_before=40, space_after=50 if bilingual else 140
    )
    if bilingual:
        m.add_para(
            [m._run("关键词：", bold=True, size_pt=10.2, color="2B4C7E"),
             m._run("太赫兹时域光谱（THz-TDS）；中药材；双视图化学计量学；压片分组嵌套交叉验证；稳定性加权 MC-UVE；密度泛函理论（DFT）", size_pt=10.2, color="333333")],
            align="left", space_before=0, space_after=140
        )

    # ==================== 1. Introduction ====================
    m.add_heading("1. Introduction", "1. 引言", level=1)
    m.add_body(
        "The chemical composition and therapeutic consistency of Traditional Chinese Medicinal (TCM) materials depend "
        "strongly on botanical species, cultivation environment, and post-harvest processing [1]. Rapid spectroscopic "
        "screening of medicinal powders is therefore widely pursued as a complement to wet-chemical chromatographic "
        "assays. Terahertz time-domain spectroscopy (THz-TDS, typically 0.1–3.0 THz) coherently measures both "
        "amplitude attenuation and phase delay of sub-picosecond electromagnetic pulses, enabling simultaneous retrieval "
        "of the absorption coefficient α(ω) and refractive index n(ω) during non-destructive spectroscopic measurement "
        "of prepared solid pellets [2–5]. Because THz photon energies (0.4–12 meV) correspond to low-frequency "
        "skeletal torsions, intermolecular hydrogen-bonding networks, and collective lattice vibrations, THz-TDS has "
        "been extensively applied to crystalline pharmaceuticals [6,7], biomolecules [8–11], flavonoid standards [12], "
        "and complex herbal matrices [13–15].",
        "中药材的化学成分与药效一致性高度依赖物种来源、产地生态环境及采后加工规格[1]。因此，快速光谱筛查作为传统湿法色谱分析的补充手段受到广泛关注。太赫兹时域光谱（THz-TDS，通常为 0.1–3.0 THz）可相干探测亚皮秒电磁脉冲的振幅衰减与相位延迟，从而在对压制固体药片进行非破坏性光谱测量时同步反演吸收系数 α(ω) 与折射率 n(ω)[2–5]。由于太赫兹光子能量（0.4–12 meV）对应低频骨架扭转、分子间氢键网络与集体晶格振动，THz-TDS 已被广泛应用于晶体药物[6,7]、生物分子[8–11]、黄酮标准品[12]及复杂草药基质研究[13–15]。"
    )
    m.add_body(
        "Recent studies in Spectrochimica Acta Part A have demonstrated high classification accuracy for single-herb "
        "origin discrimination using THz spectroscopy paired with deep learning—such as Rhizoma Coptidis [16]—or "
        "vibrational spectroscopy with multi-source fusion, such as Angelica dahurica [17]. However, deploying a "
        "single chemometric pipeline across structurally distinct botanical matrices—specifically lignified fibrous "
        "roots (Astragali Radix), lipid-rich seeds (Ziziphi Spinosae Semen), and starchy tubers (Gastrodia elata)—"
        "exposes three under-addressed methodological challenges [18]. First, single-view spectral preprocessing faces "
        "an inherent physical trade-off: standard normal variate (SNV) normalization [19] and Savitzky–Golay (SG) "
        "derivatives [20] attenuate particulate scattering and baseline drift in rough fibrous powders, but normalizing "
        "each spectrum to unit variance simultaneously discards absolute dielectric-amplitude and refractive-index "
        "differences that distinguish lipid-rich seeds and commercial processing grades. Second, conventional hard "
        "variable selection (e.g., UVE, MC-UVE, CARS [21–23]) assigns binary keep/discard weights, whereas "
        "high-dimensional classifiers evaluated under ungrouped random cross-validation risk severe optimistic bias "
        "when replicate scans from the same physical pellet appear in both training and test folds [24,25]. Third, "
        "many benchmark studies compare a proposed model using enhanced multi-scale features against classical "
        "baselines restricted to raw or single-derivative spectra, conflating feature-representation gains with "
        "classifier-architecture gains.",
        "《Spectrochimica Acta Part A》近期研究已表明，太赫兹光谱结合深度学习（如黄连产地识别[16]）或振动光谱结合多源融合（如白芷溯源[17]）在单一药材分类中可取得较高准确率。然而，当把同一套化学计量学管线部署到结构迥异的植物基质——特别是木质化纤维根茎（黄芪）、油脂种子（酸枣仁）与淀粉块茎（天麻）——时，存在三项尚未充分解决的方法学挑战[18]：其一，单视图预处理存在固有物理权衡：标准正态变量（SNV）[19]与 Savitzky–Golay（SG）导数[20]可衰减粗糙纤维粉末的颗粒散射与基线漂移，但将单条光谱归一化为单位方差的同时也会抹除区分油脂种子与商业规格的绝对介电幅值及折射率差异；其二，传统硬阈值变量选择（如 UVE、MC-UVE、CARS[21–23]）仅赋予二值保留/丢弃权重，而未按压片分组的随机交叉验证若将同一物理压片的重复扫描拆分至训练与测试折，会导致严重的乐观偏倚[24,25]；其三，现有对比实验常将使用多尺度增强特征的新模型与仅使用原始或单导数特征的传统基线比较，混淆了表征增益与分类器增益。"
    )
    m.add_body(
        "To address these gaps without conflating engineering integration with novel mathematical primitives, we "
        "develop and rigorously audit a unified Dual-View Stability-Weighted MC-UVE Manifold framework across 1,300 "
        "quality-controlled THz-TDS spectra from 262 pure-powder pressed pellets. Specifically, our work makes four "
        "focused contributions: (1) an intra-sample Dual-View representation that pairs scatter-attenuated SNV "
        "multi-scale derivatives with amplitude-preserving SG dielectric profiles via strictly single-spectrum "
        "operations; (2) pellet-grouped double-nested 5-fold cross-validation (StratifiedGroupKFold) that locks all "
        "five replicate scans of each pellet strictly into either training or held-out test folds, reporting both "
        "scan-level and pellet-level majority-vote accuracies while explicitly quantifying replicate-scan optimism; "
        "(3) input-controlled fair comparisons against PLS-DA, Random Forest, RBF-SVM, and Hard MC-UVE-SVM on both "
        "identical raw dual-channel spectra and identical 3,222-dimensional Dual-View features, backed by paired "
        "pellet-cluster bootstrap 95% confidence intervals and a 30-permutation pellet-level Y-scrambling audit; and "
        "(4) tentative gas-phase B3LYP-D3(BJ)/6-31G(d) vibrational benchmarks for Calycosin and Spinosin aligned "
        "directly against fold-averaged MC-UVE stability profiles.",
        "为系统解决上述问题并明确区分工程化集成与新数学原语，我们在涵盖 262 片纯药粉压片共 1,300 条质控太赫兹光谱的数据集上，构建并严格审计了统一的双视图稳定性加权 MC-UVE 流形框架。本研究包含四项核心贡献：（1）构建严格单样本内运算的双视图表征，并行融合散射衰减 SNV 多尺度导数与幅值保留 SG 介电谱；（2）以压片分组双层嵌套五折交叉验证（StratifiedGroupKFold）为主评估范式，将每片压片的 5 次重复扫描严格锁定在训练折或独立测试折中，同时报告逐谱与压片级多数投票准确率，并定量揭示未分组随机拆分带来的重复扫描乐观偏倚；（3）在完全相同的原始双通道输入与完全相同的 3,222 维双视图输入下，与 PLS-DA、随机森林、RBF-SVM 和硬阈值 MC-UVE-SVM 进行受控公平对比，结合压片聚类配对自助法（Bootstrap）95% 置信区间及 30 次压片级标签置换审计；（4）基于 B3LYP-D3(BJ)/6-31G(d) 开展毛蕊异黄酮与斯皮诺素气相分子振动参考计算，并与五折平均 MC-UVE 稳定性谱进行直接频率对齐。"
    )

    # ==================== 2. Materials and Methods ====================
    m.add_heading("2. Materials and Methods", "2. 材料与方法", level=1)

    m.add_heading("2.1. Sample Cohorts, Pellet Preparation, and THz-TDS Acquisition",
                  "2.1. 样本队列、纯药粉压片制备与太赫兹时域光谱采集", level=2)
    m.add_body(
        "A total of 1,308 raw dual-channel THz-TDS spectra were analyzed from commercially procured herbal materials "
        "grouped according to commercial labels and Pharmacopoeia classifications [1] without independent botanical or "
        "geographical certification: (1) Fibrous root — Astragali Radix (raw n = 403 spectra across 81 pellets), "
        "comprising four recorded origins: Datong, Shanxi (Datong (SX), n = 103), Guyang, Inner Mongolia (Guyang (IM), "
        "n = 100), Qujing, Yunnan (Qujing (YN), n = 100), and Gansu (Gansu (GS), n = 100); (2) Lipid-rich seed — "
        "Ziziphi Spinosae Semen (raw n = 500 spectra across 100 pellets, 100 scans per class), representing five "
        "commercial packaging formats and batches: Boxed Hebei (Boxed (HB)), Shijiazhuang/Bozhou Xinshengchang "
        "(SJZ/BZ), Bulk-Bag, Bulk-50g, and Tongrentang Bozhou (Tongrentang (AH)); and (3) Starchy tuber — Gastrodia "
        "elata (raw n = 405 spectra across 82 pellets), comprising four recorded origins: Bozhou, Anhui (Bozhou (AH), "
        "n = 103), Leishan, Guizhou (Leishan (GZ), n = 100), Changbai Mountain, Jilin (Changbai (JL), n = 102), and "
        "Yunnan (Yunnan (YN), n = 100). Each class workbook represents a single commercial procurement lot from which "
        "approximately 20 pellets were pressed and each pellet was scanned five consecutive times (verified by "
        "contiguous 5-scan blocks in the exported records).",
        "本研究共分析从商业渠道采购的 1,308 条原始双通道 THz-TDS 光谱，按商品标签及药典分类分组[1]（未另行实施独立植物学或地理原产地认证）：（1）纤维根茎类——黄芪（原始 n = 403 条，81 片压片），包含山西大同（Datong (SX)，103 条）、内蒙古固阳（Guyang (IM)，100 条）、云南曲靖（Qujing (YN)，100 条）和甘肃（Gansu (GS)，100 条）四个标注产地；（2）油脂种子类——酸枣仁（原始 n = 500 条，100 片压片，每组 100 条），涵盖盒养河北（Boxed (HB)）、石家庄/亳州信盛常（SJZ/BZ）、散装大袋（Bulk-Bag）、散装 50 g（Bulk-50g）与同仁堂亳州（Tongrentang (AH)）五个商业包装规格与批次；（3）淀粉块茎类——天麻（原始 n = 405 条，82 片压片），包含安徽亳州（Bozhou (AH)，103 条）、贵州雷山（Leishan (GZ)，100 条）、吉林长白山（Changbai (JL)，102 条）与云南（Yunnan (YN)，100 条）四个标注产地。每个类别工作簿对应单一商业采购批次，制备约 20 片压片且每片连续扫描 5 次（已在导出数据的连续 5 扫描区块中得到验证）。"
    )
    m.add_body(
        "Direct pure-powder pellet pressing was performed without polyethylene (PE) dilution and without an additional "
        "oven-drying step: procured herbal powders or directly pulverized herbal materials were compressed in a "
        "hydraulic pellet die (approximate pellet diameter 10–15 mm, dwell holding time 10 s, nominal thickness "
        "~1.5 mm) to form self-supporting flat discs. Transmission THz-TDS measurements were acquired by Yiyi Yang at "
        "the Terahertz Spectroscopy Laboratory of Southwest University (Chongqing, China) using a commercial TERA K15 "
        "spectrometer (Menlo Systems GmbH, Germany; 1,550 nm fiber laser, 33 mW average power) inside a dry-nitrogen-"
        "purged chamber (< 4% relative humidity, 292 K) to suppress atmospheric water-vapor lines. Sample spectra were "
        "referenced against the empty dry-nitrogen beam path, and frequency-domain optical constants α(ω) and n(ω) "
        "were exported directly by the instrument software across 0.22–1.04 THz (358 interpolated frequency points). "
        "Direct inspection of the raw frequency-domain power spectra confirms a reference dynamic range of 73.4–73.9 dB "
        "at 0.50 THz and 65.2–68.4 dB at 1.04 THz (noise floor −73.4 to −74.0 dB), with transmitted sample signals "
        "remaining 27.4–39.1 dB above the noise floor at 1.04 THz (Supplementary Fig. S2). All known and unrecorded "
        "experimental metadata are transparently summarized in Table 1.",
        "样品采用纯药粉直接压片工艺，未添加聚乙烯（PE）稀释剂，亦未进行额外烘箱烘干：市售药粉或直接粉碎后的药材粉末经模具压制（压片直径约 10–15 mm，保压时间 10 s，标称厚度约 1.5 mm）形成自支撑平整药片。透射式 THz-TDS 测量由西南大学太赫兹光谱实验室杨意艺采用商用 TERA K15 光谱仪（德国 Menlo Systems；1,550 nm 光纤激光器，平均功率 33 mW）在干燥氮气吹扫腔室（相对湿度 < 4%，温度 292 K）内完成，以消除空气水蒸气吸收线干扰。样品光谱以空光路干燥氮气作为光学参比，频域光学常数 α(ω) 与 n(ω) 由仪器软件在 0.22–1.04 THz（358 个频点）直接导出。对原始频域功率谱的直接核查证实，0.50 THz 处参比动态范围为 73.4–73.9 dB，1.04 THz 处为 65.2–68.4 dB（噪声底 −73.4 至 −74.0 dB），1.04 THz 处透射样品信号仍高出噪声底 27.4–39.1 dB（见补充图 S2）。表 1 如实汇总了所有已知及共享档案中未记录的实验元数据。"
    )

    # Table 1: Sample Preparation and Measurement Parameters (Major Comment 6)
    m.add_table(
        headers=["Parameter Category", "Specification / Recorded Value", "Notes / Provenance Status"],
        rows=[
            ["Sample material", "Pure herbal powder (no PE diluent)", "Confirmed by experimenter (Y. Yang)"],
            ["Pre-drying treatment", "None (no oven-drying step)", "Procured powder or direct milling"],
            ["Pellet diameter & dwell", "~10–15 mm die; 10 s holding time", "Self-supporting pure-powder pellets"],
            ["Nominal thickness", "~1.5 mm", "Per-pellet micrometer log not archived"],
            ["Press load & particle size", "Not recorded in shared archive", "Disclosed as experimental limitation"],
            ["Pellet & scan hierarchy", "~20 pellets/class × 5 consecutive scans", "Verified by 5-scan contiguous blocks"],
            ["THz-TDS spectrometer", "TERA K15 (Menlo Systems, 1,550 nm, 33 mW)", "Southwest Univ. THz Spectroscopy Lab"],
            ["Chamber environment", "Dry N₂ purge, RH < 4%, T = 292 K", "Empty dry-N₂ beam path reference"],
            ["Analyzed spectral band", "0.22–1.04 THz (358 exported points)", "Raw FFT grid Δf = 0.010 THz"],
            ["Measured dynamic range", "Ref: 65.2–68.4 dB; Sample: 27.4–39.1 dB @ 1.04 THz", "Direct from raw freq-domain exports (Fig. S2)"],
        ],
        col_widths_dxa=[2300, 3860, 3200],
        en_title="Table 1. Sample preparation, THz-TDS acquisition, and cohort metadata parameters.",
        zh_title="表 1. 样品制备、THz-TDS 采集与队列元数据参数汇总表。",
        font_pt=8.4
    )

    # 2.2 Optical Extraction & Unified Single-Spectrum Physical QC
    m.add_heading("2.2. Optical Parameter Retrieval and Unified Single-Spectrum Physical Quality Control",
                  "2.2. 光学常数反演与统一单谱物理质控", level=2)
    m.add_body(
        "Under the standard planar-slab transmission model against a dry-nitrogen reference (n_ref ≈ 1) [26–28], the "
        "complex transfer function H(ω) = E_sam(ω)/E_ref(ω) = ρ(ω)exp[−iΔφ(ω)] relates the phase delay Δφ(ω) and "
        "amplitude ratio ρ(ω) to the effective refractive index n(ω) and absorption coefficient α(ω) of a pellet of "
        "thickness d:",
        "在干燥氮气空光路参比（n_ref ≈ 1）的标准平板透射模型[26–28]下，复传递函数 H(ω) = E_sam(ω)/E_ref(ω) = ρ(ω)exp[−iΔφ(ω)] 将相位延迟 Δφ(ω) 与幅值比 ρ(ω) 关联至厚度为 d 的压片有效折射率 n(ω) 与吸收系数 α(ω)："
    )
    m.add_equation("H(ω) = E_sam(ω) / E_ref(ω) = ρ(ω) · exp[−iΔφ(ω)]", 1)
    m.add_equation("n(ω) = 1 + c · Δφ(ω) / (ω · d)", 2)
    m.add_equation("α(ω) = −(2 / d) · ln[ ρ(ω) · (n(ω) + 1)² / (4 · n(ω)) ]", 3)
    m.add_body(
        "Equations (1)–(3) represent the standard theoretical air/nitrogen-reference slab relations consistent with our "
        "pure-powder pellet measurements; actual numerical extraction of α(ω) and n(ω) was executed directly by the "
        "TERA K15 instrument software. Prior to modeling, a strictly single-spectrum, label-free physical quality "
        "control (QC) rule was applied identically across all three botanical matrices and all audit scripts: a "
        "spectrum was retained if and only if its band-averaged effective refractive index satisfied 1.2 ≤ n̄ ≤ 2.6 "
        "and its band-averaged absorption satisfied ᾱ ≤ 55.0 cm⁻¹. Values of n̄ < 1.2 or n̄ > 2.6 are physically "
        "inconsistent with dense dry herbal powder pellets in 0.22–1.04 THz and indicate phase-unwrapping errors or "
        "thickness mis-entry, while ᾱ > 55.0 cm⁻¹ indicates near-saturation transmission attenuation. This unified "
        "rule rejected exactly 8 of 1,308 spectra: 6 in Astragali Radix (one intact 5-scan Guyang pellet block at "
        "local indices 65–69 with n̄ = 2.96–3.12 and ᾱ = 55.7–60.8 cm⁻¹, independently confirming the 5-scan-per-pellet "
        "structure, plus 1 Gansu scan at ᾱ = 61.7 cm⁻¹), 1 in Ziziphi Spinosae Semen (1 SJZ/BZ scan at ᾱ = 62.6 cm⁻¹), "
        "and 1 in Gastrodia elata (1 Bozhou scan at n̄ = 0.901), yielding 1,300 clean spectra across 262 pellets "
        "(Astragali Radix: n = 397, 80 pellets; Ziziphi Spinosae Semen: n = 499, 100 pellets; Gastrodia elata: "
        "n = 404, 82 pellets).",
        "式（1）–（3）给出了与纯药粉压片测量一致的标准空气/氮气参比平板理论关系，实际数值反演由 TERA K15 仪器软件直接输出。建模前，在全部三类植物基质与所有审计脚本中统一实施严格单谱、无标签的物理质控（QC）准则：仅当单条光谱的频带平均有效折射率满足 1.2 ≤ n̄ ≤ 2.6 且平均吸收系数满足 ᾱ ≤ 55.0 cm⁻¹ 时予以保留。对于 0.22–1.04 THz 内的干燥致密纯药粉压片，n̄ < 1.2 或 n̄ > 2.6 提示相位解缠错误或厚度录入偏差，而 ᾱ > 55.0 cm⁻¹ 提示透射衰减接近动态范围上限。该统一准则共剔除 1,308 条中的 8 条异常谱：黄芪 6 条（固阳局部索引 65–69 的一整片 5 次连续扫描，n̄ = 2.96–3.12、ᾱ = 55.7–60.8 cm⁻¹，从数据层面独立印证了每片 5 扫的连续区块结构；另加甘肃 1 条 ᾱ = 61.7 cm⁻¹）、酸枣仁 1 条（SJZ/BZ 1 条 ᾱ = 62.6 cm⁻¹）、天麻 1 条（亳州 1 条 n̄ = 0.901），最终保留 262 片压片共 1,300 条高质量光谱（黄芪 n = 397/80 片，酸枣仁 n = 499/100 片，天麻 n = 404/82 片）。"
    )

    # 2.3 Dual-View Representation & Stability-Weighted Manifold
    m.add_heading("2.3. Intra-Sample Dual-View Feature Representation and Stability-Weighted Manifold",
                  "2.3. 单样本双视图表征与稳定性加权流形建模", level=2)
    m.add_body(
        "In heterogeneous herbal pellets, measured THz absorption can be approximated as a multiplicative-scattering "
        "plus baseline-drift model α_meas(ω) ≈ β·α_chem(ω) + b₀ + b₁ω, where β reflects particulate scattering and "
        "packing density variations, b₀ is a constant offset, and b₁ω is a linear frequency tilt. Applying sample-wise "
        "standard normal variate (SNV) transformation across the N = 358 frequency points of a single spectrum [19],",
        "在非均质药粉压片中，实测太赫兹吸收可近似表示为乘性散射叠加基线漂移模型 α_meas(ω) ≈ β·α_chem(ω) + b₀ + b₁ω，其中 β 反映颗粒散射与压实密度差异，b₀ 为常数偏置，b₁ω 为线性斜率漂移。对单条光谱的 N = 358 个频点执行样本内 SNV 变换[19]："
    )
    m.add_equation("α̃_i(ω) = [ α_i(ω) − μ(α_i) ] / [ σ(α_i) + ε ],    ε = 10⁻⁸", 4)
    m.add_body(
        "strictly cancels both b₀ and β when b₁ ≈ 0, and substantially attenuates multiplicative scattering when the "
        "linear drift is small (while noting that non-zero b₁ leaves a residual b₁(ω − ω̄) term prior to differentiation). "
        "Subsequent Savitzky–Golay (SG) polynomial filtering [20] provides complementary baseline control: zero-order "
        "SG smoothing suppresses high-frequency noise, first-order discrete differentiation eliminates constant offsets "
        "b₀, and second-order discrete differentiation eliminates both b₀ and linear slopes b₁ω (computed with unit "
        "frequency-index step Δk = 1, which is scale-invariant under fold-internal Z-score standardization). Because "
        "SNV normalization simultaneously compresses absolute dielectric-amplitude contrast across matrices, we construct "
        "a strictly intra-sample 3,222-dimensional Dual-View feature vector x_i ∈ ℝ³²²²:",
        "当 b₁ ≈ 0 时可严格消去 b₀ 与 β，在线性漂移较小时显著衰减乘性散射（当 b₁ ≠ 0 时，求导前分子与分母仍含 b₁(ω − ω̄) 残差项，故本研究将其严谨表述为“散射衰减”而非绝对散射不变）。随后的 Savitzky–Golay（SG）多项式滤波[20]提供互补基线控制：零阶平滑抑制高频噪声，一阶离散导数消除常数偏置 b₀，二阶离散导数同时消除 b₀ 与线性斜率 b₁ω（按单位频点索引步长 Δk = 1 计算，在折内 Z-score 标准化下具有尺度不变性）。由于 SNV 同时会压缩跨基质的绝对介电幅值对比度，我们构建了严格单样本内运算的 3,222 维双视图特征向量 x_i ∈ ℝ³²²²："
    )
    m.add_equation("x_i^(V1) = [ SG₀(α̃_i), SNV(SG₁(α̃_i)), SNV(SG₂(α̃_i)), SG₀(ñ_i), SNV(SG₁(ñ_i)) ] ∈ ℝ¹⁷⁹⁰", 5)
    m.add_equation("x_i^(V2) = [ SG₀(α_i), SG₂(α_i), SG₀(n_i), SG₁(n_i) ] ∈ ℝ¹⁴³²", 6)
    m.add_equation("x_i = [ x_i^(V1) ‖ x_i^(V2) ] ∈ ℝ³²²²", 7)
    m.add_body(
        "Here View 1 (1,790-dim; SG windows 19/19/15/19/15, quadratic order) captures scatter-attenuated spectral "
        "morphology, whereas View 2 (1,432-dim; SG windows 19/15/19/15) preserves absolute dielectric amplitude and "
        "curvature. Because every operation acts exclusively along the frequency axis of sample i, ∂x_i / ∂x_k ≡ 0 "
        "for all i ≠ k.",
        "其中视图 1（1,790 维，SG 窗宽 19/19/15/19/15，二阶多项式）刻画散射衰减后的光谱形态，视图 2（1,432 维，窗宽 19/15/19/15）保留绝对介电幅值与曲率。由于全部运算仅沿单条样本 i 的频率轴执行，严格满足 ∂x_i / ∂x_k ≡ 0（∀ i ≠ k）。"
    )
    m.add_body(
        "Inside each training fold exclusively, features are Z-score standardized (z_ij) and evaluated via full-rank "
        "(K − 1 latent components for K classes) multi-class PLS Monte Carlo uninformative variable elimination "
        "(MC-UVE; M = 30 random 80% subsamples) [22,29,30]. Feature stability s_j is defined as the mean-to-standard-"
        "deviation ratio of absolute PLS regression coefficients across subsamples:",
        "仅在每个训练折内部，对特征进行 Z-score 标准化（z_ij），并采用满秩（K 类取 K − 1 个潜变量）多分类 PLS 蒙特卡洛无信息变量消除（MC-UVE；M = 30 次 80% 随机子抽样）[22,29,30]，定义特征稳定性 s_j 为各子抽样绝对回归系数的均值与标准差之比："
    )
    m.add_equation("s_j = mean_m(|b_{m,j}|) / [ std_m(|b_{m,j}|) + ε ],    j = 1, …, 3222", 8)
    m.add_body(
        "Retaining the top 35% most stable coordinates (Ω, |Ω| = 1,127), continuous sublinear stability weights "
        "w_j = (s_j / s_max)^0.5 (j ∈ Ω) form the weighted physical vector x̃_i,phys = Λ^(1/2) z_i,Ω, where "
        "Λ = diag(w_j²). To capture compact global class geometry without singular covariance inversion in p > n "
        "regimes, a Ledoit–Wolf analytical shrinkage eigenvalue LDA [31] is fitted strictly on x̃_tr,phys to produce "
        "standardized (K − 1)-dimensional manifold coordinates z_i,man. The final coupled feature vector "
        "f_i = [ x̃_i,phys ‖ λ · z_i,man ] is fed into an RBF-SVM classifier [32], whose squared distance in the "
        "Gaussian kernel K(f_u, f_v) = exp(−γ ‖f_u − f_v‖₂²) expands cleanly without double-weighting as:",
        "保留稳定性排名前 35% 的坐标集合（Ω，|Ω| = 1,127），构建连续亚线性稳定性权重 w_j = (s_j / s_max)^0.5（j ∈ Ω），形成单次加权物理向量 x̃_i,phys = Λ^(1/2) z_i,Ω（其中 Λ = diag(w_j²)）。为在 p > n 条件下避免协方差奇异并提取紧致全局判别流形，仅在 x̃_tr,phys 上拟合 Ledoit–Wolf 解析收缩特征值 LDA[31]，输出标准化 (K − 1) 维流形坐标 z_i,man。最终耦合特征 f_i = [ x̃_i,phys ‖ λ · z_i,man ] 输入 RBF-SVM[32]，其高斯核平方距离可无重复加权地展开为："
    )
    m.add_equation("‖f_u − f_v‖₂² = (z_u,Ω − z_v,Ω)ᵀ Λ (z_u,Ω − z_v,Ω) + λ² ‖z_u,man − z_v,man‖₂²", 9)
    m.add_body(
        "We note explicitly that SNV, SG, MC-UVE, Ledoit–Wolf LDA, and RBF-SVM are established chemometric primitives; "
        "the methodological contribution here lies in their disciplined intra-sample Dual-View integration, continuous "
        "stability weighting, and unified evaluation across three botanically distinct matrices (Scheme 1).",
        "需要明确指出，SNV、SG、MC-UVE、Ledoit–Wolf LDA 与 RBF-SVM 均为成熟化学计量学原语；本研究的方法学价值在于严谨的单样本双视图集成、连续稳定性加权以及跨三类迥异植物基质的统一受控评估（见流程图 Scheme 1）。"
    )

    m.add_image(
        SUB_FIG_DIR / "Scheme_1_Pipeline.png", width_inches=5.4, max_height_inches=7.2,
        en_prefix="Scheme 1. ",
        en_caption="End-to-end Dual-View SW-MCUVE-Manifold workflow under strict pellet-grouped double-nested 5-fold cross-validation across three botanical matrices.",
        zh_prefix="流程图 1. ",
        zh_caption="严格压片分组双层嵌套五折交叉验证下的跨植物基质双视图 SW-MCUVE-Manifold 端到端分析流程。"
    )

    # 2.4 Pellet-Grouped Double-Nested CV, Fair Baselines, Bootstrap & Audits
    m.add_heading("2.4. Pellet-Grouped Double-Nested Validation, Input-Controlled Baselines, and Leakage Audits",
                  "2.4. 压片分组双层嵌套验证、输入受控基线与统计泄漏审计", level=2)
    m.add_body(
        "Because each physical pellet contributed five consecutive THz scans, random scan-level cross-validation "
        "allows replicate scans from the same pellet to span training and test folds. Therefore, our primary "
        "validation protocol enforces Outer 5-Fold / Inner 3-Fold Pellet-Grouped StratifiedGroupKFold (seed = 42, "
        "implemented in scikit-learn [33]), grouping all scans by pellet identifier (pellet_id = (class, local_index // 5)) "
        "assigned prior to QC. Every outer fold guarantees zero pellet overlap between training and test sets. "
        "Hyperparameters λ ∈ {1.0, 2.0, 3.0}, C ∈ {1, 5, 10, 50}, and γ ∈ {'scale', 0.002, 0.005} are tuned strictly "
        "via inner 3-fold pellet-grouped CV [24,25]. We report both individual scan-level accuracy and pellet-level "
        "majority-vote accuracy (aggregating the held-out predictions of each unseen pellet), alongside ungrouped "
        "scan-level StratifiedKFold as a diagnostic reference to quantify replicate-scan optimism.",
        "由于每片物理压片包含 5 次连续太赫兹扫描，随机按谱拆分会导致同一压片的重复扫描同时落入训练集与测试集。因此，本研究主评估协议严格采用外层 5 折 / 内层 3 折压片分组双层嵌套交叉验证（StratifiedGroupKFold，随机种子 42，基于 scikit-learn 实现[34]），在质控前按连续 5 扫区块为每条光谱分配压片编号（pellet_id = (class, local_index // 5)），确保任意外层折的训练与测试集零压片重叠。超参数 λ ∈ {1.0, 2.0, 3.0}、C ∈ {1, 5, 10, 50}、γ ∈ {'scale', 0.002, 0.005} 严格在内层 3 折压片分组中寻优[24,25]。本文同时报告逐谱准确率与压片级多数投票准确率（对每片未见压片的测试预测取众数），并给出未分组随机 StratifiedKFold 参考值以定量揭示重复扫描乐观偏倚。"
    )
    m.add_body(
        "To separate feature-representation gains from classifier gains, classical baselines—PLS-DA [30], Random "
        "Forest (RF) [34], and RBF-SVM [32]—were evaluated under identical outer/inner pellet-grouped splits on two "
        "controlled input tracks: Track A (identical 716-dim raw dual-channel [α, n]) and Track B (identical "
        "3,222-dim Dual-View features, plus Hard MC-UVE-SVM at top 35% with α_w = 0, λ = 0). Statistical significance "
        "of paired accuracy differences (ΔAcc = Acc_Proposed − Acc_Baseline) on identical held-out predictions was "
        "assessed via paired pellet-cluster bootstrapping (2,000 resamples over independent pellets) yielding 95% "
        "confidence intervals and two-sided empirical p-values. Finally, a four-part audit verified code-level "
        "isolation: (i) differential perturbation probe corrupting one held-out test spectrum by 500× + 10,000; "
        "(ii) raw uncleaned vs. unified single-spectrum QC comparison; (iii) multi-seed pellet-grouped stability "
        "(seeds 42, 100, 2026); and (iv) 30-permutation pellet-level Y-scrambling (re-fitting Z-score, MC-UVE, LDA, "
        "and SVM from scratch inside every fold) with empirical p = (1 + #{Acc_perm ≥ Acc_obs}) / 31.",
        "为严格区分特征表征增益与分类器增益，我们在完全相同的外层/内层压片分组划分下，分两条输入受控轨道评估传统基线 PLS-DA[30]、随机森林（RF）[33] 与 RBF-SVM[32]：轨道 A（完全相同的 716 维原始双通道 [α, n]）与轨道 B（完全相同的 3,222 维双视图特征，并增设同输入硬阈值 MC-UVE-SVM，取前 35%、α_w = 0、λ = 0）。在相同盲测预测上，采用以独立压片为重抽样单元的配对聚类自助法（2,000 次重抽样）计算 ΔAcc 的 95% 置信区间与双侧经验 p 值。最后，通过四项审计检验代码级隔离性：（i）差分扰动探针（对单条测试谱施加 500× + 10,000 扰动）；（ii）未清洗原始数据与统一单谱 QC 对比；（iii）多随机种子压片分组稳定性（42、100、2026）；（iv）30 次独立压片级标签置换检验（每折内重新拟合标准化、MC-UVE、LDA 与 SVM），按 p = (1 + #{Acc_perm ≥ Acc_obs}) / 31 计算经验 p 值。"
    )

    # 2.5 Tentative Quantum Chemical DFT Benchmarks
    m.add_heading("2.5. Tentative Quantum Chemical Vibrational Benchmarks (DFT)",
                  "2.5. 量子化学分子振动参考基准计算（DFT）", level=2)
    m.add_body(
        "To provide tentative intramolecular vibrational benchmarks for representative marker compounds, gas-phase "
        "geometry optimizations and harmonic frequency calculations were performed for Calycosin (Astragali Radix "
        "isoflavone aglycone) and Spinosin (Ziziphi Spinosae Semen C-glycosyl flavone) at the B3LYP-D3(BJ)/6-31G(d) "
        "level of theory [35–37] (no imaginary frequencies). Potential energy distribution (PED) mode analysis was "
        "performed using Multiwfn [38] and VEDA [39]. Because gas-phase isolated-molecule calculations omit solid-state "
        "crystal packing, amorphous matrix dispersion, and intermolecular hydrogen bonding present in pressed herbal "
        "pellets, these DFT frequencies are treated strictly as tentative intramolecular reference benchmarks rather "
        "than direct assignments of macroscopic pellet absorption bands.",
        "为给代表性指标成分提供初步分子内振动参考，本研究在 B3LYP-D3(BJ)/6-31G(d) 理论水平[35–37]下对毛蕊异黄酮（黄芪异黄酮苷元）与斯皮诺素（酸枣仁碳苷黄酮）进行了气相几何优化与谐振频率计算（均无虚频），并结合 Multiwfn[38] 与 VEDA[39] 进行势能分布（PED）归属分析。鉴于气相孤立分子计算未包含固态压片中的晶格堆积、无定形基质分散及分子间氢键效应，这些 DFT 频率严格定位为初步分子内参考基准，而非宏观药材吸收带的确证峰归属。"
    )

    # ==================== 3. Results and Discussion ====================
    m.add_heading("3. Results and Discussion", "3. 结果与讨论", level=1)

    # 3.1 Spectral Characteristics & Class Separability
    m.add_heading("3.1. Dual-Channel Spectral Profiles and Cohort Separability",
                  "3.1. 双通道光谱特征与队列可分性分析", level=2)
    m.add_body(
        "Figure 1 displays the post-QC mean ± SD raw absorption spectra and discrete SG second-derivative spectra "
        "(d²α/dk²) of Astragali Radix across 0.22–1.04 THz. As expected for complex amorphous herbal powders, the "
        "macroscopic absorption rises monotonically with frequency without sharp crystalline resonance peaks, while "
        "overlapping standard-deviation envelopes reflect strong intra-class scattering and packing variability. "
        "Discrete second-derivative filtering suppresses broad baseline tilt and exposes subtle curvature differences "
        "across 0.45–0.95 THz. Across the three post-QC cohorts, the standardized raw dual-channel Fisher "
        "separability ratio (S_B/S_W) is 0.2999 for Astragali Radix, 1.2087 for Ziziphi Spinosae Semen, and 1.0064 "
        "for Gastrodia elata. While this statistical separability ranking parallels the observed classification "
        "difficulty, we emphasize that S_B/S_W reflects the combined statistical separability of the present class "
        "labels (including origin/batch composition differences) and cannot by itself isolate botanical tissue "
        "physics as the sole causal factor.",
        "图 1 展示了质控后黄芪在 0.22–1.04 THz 内的原始吸收谱（均值 ± 标准差）及离散 SG 二阶导数谱（d²α/dk²）。与复杂无定形草药粉末的预期一致，宏观吸收随频率单调上升而无尖锐晶态特征峰，且重叠的标准差包络反映出较强的类内散射与压实变异；离散二阶导数有效抑制了宽带基线倾斜，在 0.45–0.95 THz 区间显现出细微曲率差异。三类质控队列的标准化原始双通道 Fisher 可分性比（S_B/S_W）分别为黄芪 0.2999、酸枣仁 1.2087 与天麻 1.0064。虽然该统计可分性排序与分类难易度一致，但需明确区分：S_B/S_W 反映的是当前类别标签（含产地/批次成分差异）的综合统计可分性，不能仅凭此断言植物组织物理特性是准确率差异的唯一原因。"
    )
    m.add_image(
        SUB_FIG_DIR / "Figure_1_THz_Spectra.png", width_inches=5.9, max_height_inches=3.3,
        en_prefix="Fig. 1. ",
        en_caption="Post-QC THz-TDS absorption profiles of Astragali Radix (n = 397, 80 pellets) across 0.22–1.04 THz: (a) mean ± SD raw absorption coefficient α(ω); (b) discrete Savitzky–Golay second-derivative spectra (d²α/dk², window = 19, quadratic).",
        zh_prefix="图 1. ",
        zh_caption="质控后黄芪（n = 397，80 片压片）在 0.22–1.04 THz 的太赫兹吸收谱：（a）原始吸收系数 α(ω) 均值 ± 标准差；（b）离散 Savitzky–Golay 二阶导数谱（d²α/dk²，窗宽 19，二阶）。"
    )

    # 3.2 Pellet-Grouped Performance, Replicate-Scan Optimism & Ablation
    m.add_heading("3.2. Pellet-Grouped Classification Performance, Replicate-Scan Optimism, and Ablation Analysis",
                  "3.2. 压片分组分类性能、重复扫描乐观偏倚与消融分析", level=2)
    m.add_body(
        f"Under strict pellet-grouped double-nested 5-fold CV (Table 2), the proposed Dual-View SW-MCUVE-Manifold "
        f"pipeline achieves an individual-scan accuracy of {hq_p['acc']:.2f}% ({hq_p['mean']:.2f}% ± {hq_p['sd']:.2f}%, "
        f"Macro-F1 = {hq_p['macro_f1']:.4f}) on Astragali Radix (n = 397, 80 pellets), rising to {hq_p['pellet_acc']:.2f}% "
        f"({hq_p['pellet_correct']}/{hq_p['pellet_total']} pellets) under held-out pellet majority voting (Fig. 3). "
        f"Crucially, comparing pellet-grouped CV ({hq_p['acc']:.2f}%) against ungrouped scan-level StratifiedKFold "
        f"({hq_u['acc']:.2f}%) reveals a +{hq_u['acc'] - hq_p['acc']:.2f}% replicate-scan optimism bias on the "
        f"fibrous root (and +{sz_u['acc'] - sz_p['acc']:.2f}% on seed, +{tm_u['acc'] - tm_p['acc']:.2f}% on tuber), "
        f"demonstrating that pellet-level grouping is essential whenever replicate scans are acquired per disc.",
        f"在严格压片分组双层嵌套五折交叉验证（表 2）下，所提双视图 SW-MCUVE-Manifold 管线在黄芪（n = 397，80 片）上取得 {hq_p['acc']:.2f}%（{hq_p['mean']:.2f}% ± {hq_p['sd']:.2f}%，Macro-F1 = {hq_p['macro_f1']:.4f}）的逐谱准确率，在未见压片多数投票下进一步提升至 {hq_p['pellet_acc']:.2f}%（{hq_p['pellet_correct']}/{hq_p['pellet_total']} 片，图 3）。尤为关键的是，将压片分组交叉验证（{hq_p['acc']:.2f}%）与未分组随机按谱拆分（{hq_u['acc']:.2f}%）对比，发现纤维根茎上存在 +{hq_u['acc'] - hq_p['acc']:.2f}% 的重复扫描乐观偏倚（种子 +{sz_u['acc'] - sz_p['acc']:.2f}%，块茎 +{tm_u['acc'] - tm_p['acc']:.2f}%），充分证明在单压片多次扫描场景下强制实施压片分组的必要性。"
    )

    # Table 2: Unified Cross-Matrix Pellet-Grouped Performance Summary
    m.add_table(
        headers=["Botanical Matrix (Cohort)", "n Scans (Pellets)", "Scan Acc (%) [Mean ± SD]", "Macro-F1", "Pellet Vote (%)", "Ungrouped Ref (%)"],
        rows=[
            ["Astragali Radix (4 recorded origins)", f"{HQ['n_samples']} ({HQ['n_pellets']})",
             f"{hq_p['acc']:.2f} [{hq_p['mean']:.2f} ± {hq_p['sd']:.2f}]", f"{hq_p['macro_f1']:.4f}",
             f"{hq_p['pellet_acc']:.2f} ({hq_p['pellet_correct']}/{hq_p['pellet_total']})", f"{hq_u['acc']:.2f}"],
            ["Ziziphi Spinosae (5 comm. batches)", f"{SZ['n_samples']} ({SZ['n_pellets']})",
             f"{sz_p['acc']:.2f} [{sz_p['mean']:.2f} ± {sz_p['sd']:.2f}]", f"{sz_p['macro_f1']:.4f}",
             f"{sz_p['pellet_acc']:.2f} ({sz_p['pellet_correct']}/{sz_p['pellet_total']})", f"{sz_u['acc']:.2f}"],
            ["Gastrodia elata (4 recorded origins)", f"{TM['n_samples']} ({TM['n_pellets']})",
             f"{tm_p['acc']:.2f} [{tm_p['mean']:.2f} ± {tm_p['sd']:.2f}]", f"{tm_p['macro_f1']:.4f}",
             f"{tm_p['pellet_acc']:.2f} ({tm_p['pellet_correct']}/{tm_p['pellet_total']})", f"{tm_u['acc']:.2f}"],
            ["Cross-Matrix Average", "1,300 (262)", f"{avg_scan_prop:.2f}",
             f"{(hq_p['macro_f1']+sz_p['macro_f1']+tm_p['macro_f1'])/3:.4f}", f"{avg_pellet_prop:.2f}",
             f"{(hq_u['acc']+sz_u['acc']+tm_u['acc'])/3:.2f}"],
        ],
        col_widths_dxa=[2350, 1200, 1950, 950, 1610, 1300],
        en_title="Table 2. Primary pellet-grouped double-nested 5-fold CV performance across all three botanical matrices (with ungrouped scan-level reference quantifying replicate-scan optimism).",
        zh_title="表 2. 三类植物基质在严格压片分组双层嵌套五折交叉验证下的主评估性能（附未分组按谱参考值以量化重复扫描偏倚）。",
        bold_row_indices=[3], font_pt=8.2
    )

    # Module Knockout Ablation (Table 3 & Fig 2)
    hq_ab = HQ["ablation"]
    sz_ab = SZ["ablation"]
    tm_ab = TM["ablation"]
    abl_keys = list(hq_ab.keys())
    abl_rows = []
    for ak in abl_keys:
        avg_a = (hq_ab[ak]["acc"] + sz_ab[ak]["acc"] + tm_ab[ak]["acc"]) / 3.0
        abl_rows.append([
            ak,
            f"{hq_ab[ak]['acc']:.2f} ({hq_ab[ak]['pellet_acc']:.1f}%)",
            f"{sz_ab[ak]['acc']:.2f} ({sz_ab[ak]['pellet_acc']:.1f}%)",
            f"{tm_ab[ak]['acc']:.2f} ({tm_ab[ak]['pellet_acc']:.1f}%)",
            f"{avg_a:.2f}"
        ])
    m.add_body(
        "Module knockout ablation under identical pellet-grouped splits (Table 3; Fig. 2 for root; Supplementary Fig. S1a "
        "for seed) clarifies each component's role. On Astragali Radix, the full Dual-View model ranks strictly first "
        "(87.66%, fold SD = 3.08%): removing either View 2 (SNV Only, 86.65%), View 1 (Amplitude Only, 86.40%), the "
        "purified manifold (λ = 0, 86.40%), or the refractive index channel (Abs Only, 85.89%, fold SD inflating to "
        "5.72%) consistently degrades unseen-pellet generalization. Across all three matrices, the full Dual-View "
        "configuration delivers the highest overall cross-matrix stability (mean scan accuracy 94.19%), whereas "
        "single-view ablations can slightly edge out the full model on an individual matrix (e.g., Amplitude Only "
        "on lipid-rich seeds) at the expense of lower fibrous-root performance—highlighting the value of the unified "
        "Dual-View architecture for cross-matrix robustness rather than claiming universal single-matrix dominance.",
        "相同压片分组划分下的模块敲除消融实验（表 3；根茎见图 2，种子见补充图 S1a）阐明了各模块的贡献。在黄芪上，完整双视图模型严格排名第一（87.66%，折间 SD = 3.08%）：移除视图 2（仅 SNV，86.65%）、视图 1（仅保幅，86.40%）、提纯流形（λ = 0，86.40%）或折射率通道（仅吸收，85.89%，折间 SD 恶化至 5.72%）均导致未见压片泛化性能下降。纵观三类基质，完整双视图架构取得最高的跨基质综合稳定性（平均逐谱 94.19%）；虽然个别单视图变体在单一基质（如仅保幅在油脂种子上）可能略高于完整模型，但在纤维根茎上表现下滑，这凸显了统一双视图架构在跨基质稳健性上的工程价值，而非宣称在每个单一基质上绝对最高。"
    )
    m.add_table(
        headers=["Ablation Configuration", "Root Scan (Pellet)", "Seed Scan (Pellet)", "Tuber Scan (Pellet)", "3-Matrix Avg (%)"],
        rows=abl_rows,
        col_widths_dxa=[3160, 1550, 1550, 1550, 1550],
        en_title="Table 3. Module knockout ablation under identical pellet-grouped 5-fold CV (scan accuracy % and pellet majority-vote % in parentheses).",
        zh_title="表 3. 相同压片分组五折交叉验证下的模块敲除消融结果（逐谱准确率 %，括号内为压片多数投票准确率 %）。",
        bold_row_indices=[0], font_pt=8.3
    )

    m.add_image(
        SUB_FIG_DIR / "Figure_2_Ablation_Root.png", width_inches=5.5, max_height_inches=3.6,
        en_prefix="Fig. 2. ",
        en_caption="Module knockout ablation on Astragali Radix (n = 397, 80 pellets) under strict pellet-grouped double-nested 5-fold CV.",
        zh_prefix="图 2. ",
        zh_caption="严格压片分组双层嵌套五折交叉验证下黄芪（n = 397，80 片）的模块敲除消融实验。"
    )
    m.add_image(
        SUB_FIG_DIR / "Figure_3_Confusion_Matrix_Root.png", width_inches=4.4, max_height_inches=4.0,
        en_prefix="Fig. 3. ",
        en_caption="Pellet-grouped double-nested 5-fold CV confusion matrix for Astragali Radix (n = 397 scans across 80 pellets; scan accuracy 87.66%, pellet majority-vote 92.50%).",
        zh_prefix="图 3. ",
        zh_caption="黄芪（n = 397，80 片压片）压片分组双层嵌套五折交叉验证混淆矩阵（逐谱 87.66%，压片投票 92.50%）。"
    )

    # 3.3 Fair Input-Controlled Baselines & Statistical Significance (Major Comments 3 & 10)
    m.add_heading("3.3. Input-Controlled Baseline Benchmarks and Paired Pellet-Cluster Bootstrap Analysis",
                  "3.3. 输入受控公平基线对比与压片聚类配对 Bootstrap 检验", level=2)
    m.add_body(
        "Table 4 and Fig. 4 (with seed baselines in Supplementary Fig. S1b) present input-controlled comparisons across "
        "identical pellet-grouped splits, cleanly decomposing representation gain from classifier gain. First, "
        "upgrading from raw dual-channel spectra (Track A, 716-dim) to the intra-sample Dual-View representation "
        "(Track B, 3,222-dim) substantially improves non-linear baselines across matrices: RBF-SVM rises from 81.61% "
        "to 87.41% on root and from 84.77% to 94.79% on seed, while RF jumps from 65.74% to 84.89% on root and from "
        "73.95% to 90.38% on seed. Second, holding the 3,222-dim Dual-View input strictly identical (Track B), the "
        "proposed SW-MCUVE-Manifold significantly outperforms Dual-View PLS-DA (+4.53%, p = 0.0130 on root; +5.21%, "
        "p = 0.0005 on seed), Dual-View RF (+6.01%, p = 0.0005 on seed), and Dual-View Hard MC-UVE-SVM (+2.40%, "
        "95% CI [+0.20%, +4.80%], p = 0.0340 on seed). On Astragali Radix, Dual-View RBF-SVM (87.41%, p = 0.934) and "
        "Hard MC-UVE-SVM (88.41%, p = 0.309) are statistically indistinguishable from Proposed (87.66%), confirming "
        "that on fibrous roots the dominant gain derives from the Dual-View representation itself, whereas on "
        "lipid-rich seeds the stability-weighted manifold provides an additional statistically significant improvement. "
        "Overall, Proposed achieves the highest three-matrix average scan accuracy (94.19%) and pellet-level "
        "majority-vote accuracy (97.50%).",
        "表 4 与图 4（种子基线见补充图 S1b）展示了相同压片分组划分下的输入受控公平对比，清晰解耦了“表征增益”与“分类器增益”。首先，从原始双通道输入（轨道 A，716 维）升级至单样本双视图表征（轨道 B，3,222 维）显著提升了非线性基线的泛化能力：RBF-SVM 在黄芪上从 81.61% 跃升至 87.41%、在酸枣仁上从 84.77% 跃升至 94.79%，RF 在黄芪与酸枣仁上分别从 65.74%/73.95% 跃升至 84.89%/90.38%。其次，在严格固定相同 3,222 维双视图输入（轨道 B）时，所提 SW-MCUVE-Manifold 在黄芪和酸枣仁上显著优于双视图 PLS-DA（黄芪 +4.53%，p = 0.0130；酸枣仁 +5.21%，p = 0.0005），在酸枣仁上显著优于双视图 RF（+6.01%，p = 0.0005）与硬阈值 MC-UVE-SVM（+2.40%，95% CI [+0.20%, +4.80%]，p = 0.0340）。在黄芪上，双视图 RBF-SVM（87.41%，p = 0.934）与硬阈值 MC-UVE-SVM（88.41%，p = 0.309）与本方法无统计学差异，表明纤维根茎上的主导性能增益来自双视图物理表征本身，而油脂种子上稳定性加权流形进一步带来了显著的额外增益。综合三类基质，本方法取得了最高的跨基质平均逐谱准确率（94.19%）与压片投票准确率（97.50%）。"
    )

    b_keys = [
        "PLS-DA (Raw Dual-Channel)",
        "RF (Raw Dual-Channel)",
        "RBF-SVM (Raw Dual-Channel)",
        "PLS-DA (Dual-View 3222-d)",
        "RF (Dual-View 3222-d)",
        "RBF-SVM (Dual-View 3222-d)",
        "Hard MC-UVE-SVM (Dual-View 3222-d)",
    ]
    t4_rows = []
    for bk in [
        "PLS-DA (Raw Dual-Channel)", "RF (Raw Dual-Channel)", "RBF-SVM (Raw Dual-Channel)",
        "PLS-DA (Dual-View 3222-d)", "RF (Dual-View 3222-d)", "RBF-SVM (Dual-View 3222-d)",
        "Hard MC-UVE-SVM (Dual-View 3222-d)",
    ]:
        r_hq, r_sz, r_tm = HQ["baselines_fair"][bk], SZ["baselines_fair"][bk], TM["baselines_fair"][bk]
        b_hq, b_sz = HQ["paired_bootstrap_vs_proposed"][bk], SZ["paired_bootstrap_vs_proposed"][bk]
        avg_s = (r_hq["acc"] + r_sz["acc"] + r_tm["acc"]) / 3.0
        avg_p = (r_hq["pellet_acc"] + r_sz["pellet_acc"] + r_tm["pellet_acc"]) / 3.0
        t4_rows.append([
            bk,
            f"{r_hq['acc']:.2f} (p={b_hq['p_boot']:.3f})",
            f"{r_sz['acc']:.2f} (p={b_sz['p_boot']:.3f})",
            f"{r_tm['acc']:.2f}",
            f"{avg_s:.2f} / {avg_p:.2f}",
        ])
    t4_rows.append([
        "Proposed SW-MCUVE-Manifold (Dual-View)",
        f"{hq_p['acc']:.2f} (Ref)",
        f"{sz_p['acc']:.2f} (Ref)",
        f"{tm_p['acc']:.2f}",
        f"{avg_scan_prop:.2f} / {avg_pellet_prop:.2f}",
    ])
    m.add_table(
        headers=["Model (Controlled Input)", "Root Acc % (p_boot)", "Seed Acc % (p_boot)", "Tuber Acc %", "3-Matrix Avg (Scan/Pellet %)"],
        rows=t4_rows,
        col_widths_dxa=[2960, 1650, 1650, 1150, 1950],
        en_title="Table 4. Input-controlled fair baseline comparisons under identical pellet-grouped 5-fold CV (two-sided paired pellet-cluster bootstrap p-values vs. Proposed shown for root and seed; full 95% CIs in Table S2).",
        zh_title="表 4. 相同压片分组五折交叉验证下的输入受控公平基线对比（括号内为相对本方法的配对压片聚类 Bootstrap 双侧 p 值；完整 95% 置信区间见表 S2）。",
        bold_row_indices=[len(t4_rows) - 1], font_pt=8.1
    )

    m.add_image(
        SUB_FIG_DIR / "Figure_4_Baseline_Root.png", width_inches=5.7, max_height_inches=3.6,
        en_prefix="Fig. 4. ",
        en_caption="Input-controlled baseline comparison on Astragali Radix (n = 397, 80 pellets) under identical pellet-grouped 5-fold CV across Track A (Raw Dual-Channel) and Track B (3,222-dim Dual-View).",
        zh_prefix="图 4. ",
        zh_caption="相同压片分组五折交叉验证下黄芪（n = 397，80 片）在轨道 A（原始双通道）与轨道 B（3,222 维双视图）上的输入受控公平基线对比。"
    )

    # 3.4 Multi-Matrix Re-Evaluation & Leakage Audits (Major Comments 2 & 4)
    m.add_heading("3.4. Multi-Matrix Re-Evaluation (Seed and Tuber) and Four-Stage Statistical Audit",
                  "3.4. 多基质架构重评估（种子与块茎）及四阶段统计泄漏审计", level=2)
    m.add_body(
        f"To evaluate architectural applicability beyond fibrous roots without retuning feature definitions or search "
        f"grids, the fixed analytical architecture was independently re-evaluated on Ziziphi Spinosae Semen (five "
        f"commercial batches/specifications, n = 499, 100 pellets) and on a third botanical matrix, Gastrodia elata "
        f"(four recorded origins, n = 404, 82 pellets), using matrix-specific pellet-grouped nested cross-validation "
        f"(Fig. 5a–b). Note that each matrix is trained and evaluated independently from scratch; this tests "
        f"cross-matrix architectural applicability rather than zero-shot cross-species model transfer. On Ziziphi "
        f"Spinosae Semen, scan-level accuracy reaches {sz_p['acc']:.2f}% ({sz_p['mean']:.2f}% ± {sz_p['sd']:.2f}%) "
        f"with {sz_p['pellet_acc']:.2f}% ({sz_p['pellet_correct']}/{sz_p['pellet_total']}) pellet majority-vote "
        f"accuracy. On Gastrodia elata, scan-level accuracy reaches {tm_p['acc']:.2f}% ({tm_p['mean']:.2f}% ± "
        f"{tm_p['sd']:.2f}%) with {tm_p['pellet_acc']:.2f}% ({tm_p['pellet_correct']}/{tm_p['pellet_total']}) "
        f"pellet majority-vote accuracy (while noting that Raw PLS-DA also achieves 99.01%, Δ = −0.50%, p = 0.704, "
        f"consistent with the high intrinsic linear separability of the starchy tuber cohort).",
        f"为在不改动特征定义与搜索空间的前提下评估该架构在纤维根茎之外的适用性，我们将固定分析架构在酸枣仁（五个商业规格/批次，n = 499，100 片）及第三种植物基质天麻（四个标注产地，n = 404，82 片）上分别执行了基质特异性的压片分组嵌套交叉验证（图 5a–b）。需明确说明，各基质均从零独立重训与评估，因此该实验检验的是跨基质算法架构适用性，而非无需重训的跨物种模型迁移。在酸枣仁上，逐谱准确率达 {sz_p['acc']:.2f}%（{sz_p['mean']:.2f}% ± {sz_p['sd']:.2f}%），压片多数投票达 {sz_p['pellet_acc']:.2f}%（{sz_p['pellet_correct']}/{sz_p['pellet_total']}）；在天麻上，逐谱准确率达 {tm_p['acc']:.2f}%（{tm_p['mean']:.2f}% ± {tm_p['sd']:.2f}%），压片多数投票达 {tm_p['pellet_acc']:.2f}%（{tm_p['pellet_correct']}/{tm_p['pellet_total']}；同时可见原始双通道 PLS-DA 亦达 99.01%，Δ = −0.50%，p = 0.704，符合淀粉块茎队列本身线性可分性较高的特征）。"
    )
    m.add_image(
        SUB_FIG_DIR / "Figure_5a_Confusion_Matrix_Seed.png", width_inches=4.3, max_height_inches=3.9,
        en_prefix="Fig. 5a. ",
        en_caption="Pellet-grouped 5-fold CV confusion matrix for Ziziphi Spinosae Semen (five commercial batches, n = 499 scans, 100 pellets; scan accuracy 96.39%, pellet vote 100.00%).",
        zh_prefix="图 5a. ",
        zh_caption="酸枣仁（五个商业规格/批次，n = 499，100 片）压片分组五折交叉验证混淆矩阵（逐谱 96.39%，压片投票 100.00%）。"
    )
    m.add_image(
        SUB_FIG_DIR / "Figure_5b_Confusion_Matrix_Tuber.png", width_inches=4.3, max_height_inches=3.9,
        en_prefix="Fig. 5b. ",
        en_caption="Matrix-specific pellet-grouped 5-fold CV confusion matrix for Gastrodia elata (four recorded origins, n = 404 scans, 82 pellets; scan accuracy 98.51%, pellet vote 100.00%).",
        zh_prefix="图 5b. ",
        zh_caption="天麻（四个标注产地，n = 404，82 片）基质特异性压片分组五折交叉验证混淆矩阵（逐谱 98.51%，压片投票 100.00%）。"
    )

    a1 = AUDIT["audit_1_differential_probe"]
    a2 = AUDIT["audit_2_qc_comparison"]
    a3 = AUDIT["audit_3_multiseed_stability"]
    a4 = AUDIT["audit_4_y_scrambling"]
    m.add_body(
        "Table 5 summarizes the unified four-stage code-level leakage and permutation audit conducted under the exact "
        "same single-spectrum QC rule and pellet-grouped splits. First, corrupting one held-out test spectrum by "
        "500× + 10,000 produced exact 0.000000e+00 deviation across all remaining 396 feature vectors, MC-UVE stability "
        "scores, Shrinkage-LDA training coordinates, and 0/77 prediction changes on other held-out scans—verifying "
        "strict code-level test-to-train isolation under that perturbation. Second, multi-seed pellet-grouped splits "
        "(seeds 42, 100, 2026) remain stable (87.49% ± 0.24% root; 95.26% ± 1.46% seed; 98.51% ± 0.81% tuber). "
        "Third, 30 independent pellet-level Y-scrambling permutations collapse accurately to theoretical chance levels "
        "(24.41% ± 3.45% vs. 25.0% on root; 20.57% ± 2.75% vs. 20.0% on seed; 25.06% ± 5.76% vs. 25.0% on tuber), "
        "with 0/30 permutations reaching the observed accuracy (empirical p = 0.0323 across all three matrices). "
        "We note responsibly that these audits verify absence of code-level leakage within the current cohort, but "
        "cannot substitute for prospective multi-batch external validation.",
        "表 5 汇总了在完全相同单谱 QC 规则与压片分组划分下执行的四阶段代码级泄漏与置换审计结果。首先，对单条盲测光谱施加 500× + 10,000 扰动后，其余 396 条特征向量、MC-UVE 稳定性向量与 Shrinkage-LDA 训练流形的最大偏差均为精确 0.000000e+00，其余盲测扫描预测零变化（0/77），验证了该扰动下严格的代码级训练-测试隔离。其次，多随机种子压片分组（42、100、2026）表现稳健（黄芪 87.49% ± 0.24%，酸枣仁 95.26% ± 1.46%，天麻 98.51% ± 0.81%）。第三，30 次独立压片级标签置换（Y-scrambling）均准确坍塌至理论随机水平（黄芪 24.41% ± 3.45% vs. 25.0%，酸枣仁 20.57% ± 2.75% vs. 20.0%，天麻 25.06% ± 5.76% vs. 25.0%），30 次置换无一达到观测准确率（三类基质经验 p 均为 0.0323）。需审慎指出，上述审计证明了当前队列内不存在代码级数据泄漏，但不能替代前瞻性多批次外部验证。"
    )
    m.add_table(
        headers=["Audit Stage (Unified Single-Spec QC)", "Astragali Radix", "Ziziphi Spinosae", "Gastrodia elata"],
        rows=[
            ["1. Differential Probe (500×+10,000)", "0.00e+00 (0/77 flip)", "Same code path", "Same code path"],
            ["2. Raw Uncleaned vs. Unified QC",
             f"{a2['Astragali Radix (Root)']['raw_acc']:.2f}% → {a2['Astragali Radix (Root)']['qc_acc']:.2f}%",
             f"{a2['Ziziphi Spinosae (Seed)']['raw_acc']:.2f}% → {a2['Ziziphi Spinosae (Seed)']['qc_acc']:.2f}%",
             f"{a2['Gastrodia elata (Tuber)']['raw_acc']:.2f}% → {a2['Gastrodia elata (Tuber)']['qc_acc']:.2f}%"],
            ["3. Multi-Seed Stability (42/100/2026)",
             f"{a3['Astragali Radix (Root)']['mean_acc']:.2f}% ± {a3['Astragali Radix (Root)']['sd_acc']:.2f}%",
             f"{a3['Ziziphi Spinosae (Seed)']['mean_acc']:.2f}% ± {a3['Ziziphi Spinosae (Seed)']['sd_acc']:.2f}%",
             f"{a3['Gastrodia elata (Tuber)']['mean_acc']:.2f}% ± {a3['Gastrodia elata (Tuber)']['sd_acc']:.2f}%"],
            ["4. Y-Scrambling (30 Pellet Perms)",
             f"{a4['Astragali Radix (Root)']['null_mean_pct']:.2f}% ± {a4['Astragali Radix (Root)']['null_sd_pct']:.2f}% (p={a4['Astragali Radix (Root)']['empirical_p_value']:.4f})",
             f"{a4['Ziziphi Spinosae (Seed)']['null_mean_pct']:.2f}% ± {a4['Ziziphi Spinosae (Seed)']['null_sd_pct']:.2f}% (p={a4['Ziziphi Spinosae (Seed)']['empirical_p_value']:.4f})",
             f"{a4['Gastrodia elata (Tuber)']['null_mean_pct']:.2f}% ± {a4['Gastrodia elata (Tuber)']['null_sd_pct']:.2f}% (p={a4['Gastrodia elata (Tuber)']['empirical_p_value']:.4f})"],
        ],
        col_widths_dxa=[2860, 2170, 2170, 2160],
        en_title="Table 5. Unified four-stage code-level isolation and 30-permutation pellet-level Y-scrambling audit.",
        zh_title="表 5. 统一单谱 QC 与压片分组条件下的四阶段代码级隔离与 30 次压片级标签置换审计汇总。",
        font_pt=8.2
    )

    # 3.5 Tentative DFT Vibrational Benchmarks & MC-UVE Alignment (Major Comment 9)
    m.add_heading("3.5. Tentative DFT Vibrational Benchmarks and Alignment with MC-UVE Stability Profiles",
                  "3.5. 初步 DFT 分子振动参考基准及与 MC-UVE 稳定性谱的频率对齐", level=2)
    m.add_body(
        "To examine whether the spectral regions prioritized by MC-UVE overlap with theoretically active low-frequency "
        "intramolecular modes of characteristic marker metabolites, Fig. 6 summarizes the B3LYP-D3(BJ)/6-31G(d) "
        "gas-phase harmonic spectra of Calycosin (Astragali Radix) and Spinosin (Ziziphi Spinosae Semen), and Fig. 7 "
        "directly overlays these theoretical frequencies onto the fold-averaged MC-UVE absorption stability profiles. "
        "Calycosin exhibits calculated skeletal B-ring torsional and out-of-plane bending modes at 0.552 THz and "
        "0.885 THz (PED > 68%), while the larger C-glycosyl flavone Spinosin exhibits coupled glycosyl-ring rocking "
        "and inter-ring libration modes at 0.605, 0.886, and 0.979 THz. As shown in Fig. 7, several high-stability "
        "MC-UVE bands (exceeding the top-35% selection threshold) occur in the general vicinity of 0.55–0.98 THz, "
        "providing plausible physical context for why derivative curvature in this window contributes to discrimination. "
        "Nevertheless, because pure-powder herbal pellets contain complex amorphous polysaccharides, lipids, proteins, "
        "and intermolecular hydrogen-bonding networks absent from gas-phase single-molecule DFT, these correspondences "
        "are interpreted strictly as tentative intramolecular vibrational benchmarks; definitive band assignment "
        "would require pure-standard THz measurements and periodic solid-state DFT.",
        "为检验 MC-UVE 优选的高稳定性频段是否与标志性代谢物的理论低频分子内振动模式存在交集，图 6 汇总了毛蕊异黄酮（黄芪）与斯皮诺素（酸枣仁）的 B3LYP-D3(BJ)/6-31G(d) 气相谐振频率谱，图 7 则将这些理论频率直接叠加至五折平均 MC-UVE 吸收稳定性谱上。计算表明，毛蕊异黄酮在 0.552 THz 与 0.885 THz 处存在骨架 B 环扭转与面外弯曲模式（PED > 68%），而分子量更大的碳苷黄酮斯皮诺素在 0.605、0.886 与 0.979 THz 处存在糖基摇摆与环间耦合振动。如图 7 所示，若干高于前 35% 筛选阈值的 MC-UVE 高稳定性波段分布于 0.55–0.98 THz 附近，为该窗口内的导数曲率贡献判别信息提供了合理的物理背景。然而，由于纯药粉压片包含气相单分子 DFT 未建模的无定形多糖、脂质、蛋白质与分子间氢键网络，上述对应关系严格解释为初步分子内振动参考基准；确切的实验峰归属仍有待纯标准品太赫兹实测与周期性固态 DFT 进一步证实。"
    )
    m.add_image(
        SUB_FIG_DIR / "Figure_6_DFT_Benchmarks.png", width_inches=5.7, max_height_inches=3.6,
        en_prefix="Fig. 6. ",
        en_caption="Tentative gas-phase B3LYP-D3(BJ)/6-31G(d) harmonic THz vibrational benchmarks for Calycosin (Astragali Radix) and Spinosin (Ziziphi Spinosae Semen) across 0.22–1.04 THz.",
        zh_prefix="图 6. ",
        zh_caption="B3LYP-D3(BJ)/6-31G(d) 计算得到的毛蕊异黄酮（黄芪）与斯皮诺素（酸枣仁）在 0.22–1.04 THz 的气相初步谐振振动参考基准。"
    )
    m.add_image(
        SUB_FIG_DIR / "Figure_7_MCUVE_DFT_Alignment.png", width_inches=5.7, max_height_inches=4.4,
        en_prefix="Fig. 7. ",
        en_caption="Direct frequency alignment between fold-averaged MC-UVE absorption stability spectra (pellet-grouped 5-fold CV) and tentative B3LYP-D3(BJ)/6-31G(d) intramolecular modes for (a) Astragali Radix (Calycosin) and (b) Ziziphi Spinosae Semen (Spinosin).",
        zh_prefix="图 7. ",
        zh_caption="五折平均 MC-UVE 吸收稳定性谱（压片分组交叉验证）与初步 B3LYP-D3(BJ)/6-31G(d) 分子内模式的直接频率对齐：（a）黄芪（毛蕊异黄酮）；（b）酸枣仁（斯皮诺素）。"
    )

    # 3.6 Limitations and Outlook
    m.add_heading("3.6. Limitations and Future Perspectives", "3.6. 研究局限性与未来展望", level=2)
    m.add_body(
        "Three methodological limitations must be explicitly noted. First, although pellet-grouped CV eliminates "
        "same-pellet replicate leakage across 262 independent pressed discs, each class workbook originates from a "
        "single commercial procurement lot without independent botanical or geographical origin certificates; "
        "consequently, current accuracies reflect within-cohort pellet-generalizable discrimination of recorded "
        "origins and commercial batches rather than multi-harvest external traceability. Second, certain archival "
        "preparation parameters (exact pressing load, particle-size distribution, and per-pellet micrometer thickness) "
        "were not recorded in the shared dataset and should be strictly logged in prospective acquisitions. Third, "
        "combining pure-standard THz measurements with periodic solid-state DFT and multi-season independent batches "
        "will be essential to transition from cohort-level classification to certified origin traceability.",
        "本研究存在三项必须明确披露的方法学局限：首先，尽管压片分组交叉验证在 262 片独立压片上消除了同片重复扫描泄漏，但每个类别工作簿均源自单一商业采购批次且缺乏独立植物学或地理原产地证书，因此当前准确率反映的是现有队列内对标注产地与商业批次的跨压片泛化能力，而非跨采收季、跨独立批次的外部溯源能力；其次，共享档案中未记录具体压片压力、粒径分布及单片千分尺厚度等制样参数，未来前瞻性采集需严格建档；第三，结合纯标准品太赫兹实测、周期性固态 DFT 与多产季独立批次数据，将是实现从队列内分类迈向权威产地溯源的关键。"
    )

    # ==================== 4. Conclusion ====================
    m.add_heading("4. Conclusion", "4. 结论", level=1)
    m.add_body(
        "We presented and rigorously audited a unified Dual-View THz-TDS chemometric pipeline across 1,300 "
        "quality-controlled spectra from 262 pure-powder pressed pellets representing fibrous roots (Astragali Radix), "
        "lipid-rich seeds (Ziziphi Spinosae Semen), and starchy tubers (Gastrodia elata). Enforcing strict "
        "pellet-grouped double-nested 5-fold cross-validation eliminated replicate-scan optimism (up to +5.54% on "
        "fibrous roots) while yielding 87.66%, 96.39%, and 98.51% scan-level accuracies and 92.50%, 100.00%, and "
        "100.00% pellet majority-vote accuracies across the three matrices. Input-controlled benchmarks with paired "
        "pellet-cluster bootstrapping demonstrated that the intra-sample Dual-View representation drives substantial "
        "gains over raw dual-channel baselines, while stability-weighted manifold coupling provides statistically "
        "significant additional improvement on lipid-rich seeds and delivers the highest three-matrix average "
        "(94.19% scan; 97.50% pellet). Coupled with unified single-spectrum QC, 30-permutation pellet-level "
        "Y-scrambling (p = 0.0323), and tentative DFT–MC-UVE alignment, this open-source framework provides a "
        "transparent, reproducible baseline for multi-matrix THz spectroscopic classification of medicinal materials.",
        "本文在涵盖纤维根茎（黄芪）、油脂种子（酸枣仁）和淀粉块茎（天麻）三类基质的 262 片纯药粉压片共 1,300 条质控太赫兹光谱上，构建并严格审计了统一双视图化学计量学管线。强制实施压片分组双层嵌套五折交叉验证消除了重复扫描乐观偏倚（纤维根茎高达 +5.54%），在三类基质上分别取得了 87.66%、96.39% 和 98.51% 的逐谱准确率以及 92.50%、100.00% 和 100.00% 的压片多数投票准确率。输入受控对比与压片聚类配对 Bootstrap 检验表明，单样本双视图表征带来了相对原始双通道基线的显著增益，而稳定性加权流形耦合在油脂种子上提供了显著的额外提升，并在三类基质上实现了最高的综合平均性能（逐谱 94.19%；压片 97.50%）。结合统一单谱 QC、30 次压片级标签置换审计（p = 0.0323）与初步 DFT–MC-UVE 频率对齐，该开源框架为跨基质中药材太赫兹光谱分类提供了透明、可复现的方法学基准。"
    )

    # ==================== Declarations (Elsevier Format) ====================
    m.add_heading("CRediT authorship contribution statement", "作者贡献声明", level=2)
    m.add_body(
        "Sihao Liu: Conceptualization, Methodology, Software, Formal analysis, Visualization, Writing – original draft. "
        "Ziyuan Zhu: Investigation, Validation, Data curation, Writing – review & editing. "
        "Yin Shen: Resources, Supervision, Project administration, Writing – review & editing.",
        "刘厶豪：构思、方法学、软件实现、形式分析、可视化、初稿撰写。朱子元：调研、验证、数据整理、审阅与修改。沈印：资源提供、指导监督、项目管理、审阅与修改。",
        first_line_indent=0
    )
    m.add_heading("Declaration of competing interest", "利益冲突声明", level=2)
    m.add_body(
        "The authors declare that they have no known competing financial interests or personal relationships that "
        "could have appeared to influence the work reported in this paper.",
        "作者声明不存在任何可能影响本研究报道内容的已知竞争性经济利益或个人关系。",
        first_line_indent=0
    )
    m.add_heading("Acknowledgments", "致谢", level=2)
    m.add_body(
        "The authors thank Yin Shen (Chongqing Medical University) for providing the shared THz-TDS dataset and "
        "academic supervision, and Yiyi Yang (Terahertz Spectroscopy Laboratory, Southwest University, Chongqing, "
        "China) for acquiring the THz-TDS measurements and confirming pellet preparation details.",
        "作者感谢重庆医科大学沈印老师提供共享 THz-TDS 数据集与学术指导，并感谢西南大学太赫兹光谱实验室杨意艺完成太赫兹光谱采集并核实压片制备细节。",
        first_line_indent=0
    )
    m.add_heading("Declaration of generative AI and AI-assisted technologies in the writing process",
                  "生成式人工智能使用声明", level=2)
    m.add_body(
        "During the preparation of this work, the authors used large-language-model coding and editing assistants "
        "(Google Gemini / Antigravity) solely to assist with Python script refactoring, documentation formatting, and "
        "English language polishing. All scientific calculations, statistical audits, figure verifications, and "
        "manuscript claims were independently executed, inspected, and verified by the authors, who take full "
        "responsibility for the content of the publication.",
        "在本文撰写与整理过程中，作者仅使用大语言模型编程与编辑辅助工具（Google Gemini / Antigravity）协助 Python 代码重构、文档排版及英文语言润色。所有科学计算、统计审计、图表核查及学术结论均由作者独立运行、审查与确认，作者对出版内容承担全部责任。",
        first_line_indent=0
    )
    m.add_heading("Data availability", "数据可用性声明", level=2)
    m.add_body(
        "The cached dual-channel THz-TDS spectra (.npz), project-relative Python analysis and audit scripts, "
        "requirements.txt, 300 DPI figures, and machine-readable JSON audit reports are publicly available at "
        "https://github.com/l114514sh-cmyk/THz-TCM-DualView-Manifold. Raw instrument Excel exports were acquired by "
        "Yiyi Yang and provided by Yin Shen as part of a shared research resource also utilized in other supervised "
        "studies; the Dual-View SW-MCUVE-Manifold architecture, pellet-grouped nested validation, input-controlled "
        "statistical benchmarks, and DFT–MC-UVE alignment presented here are unique to this work. Raw exports are "
        "available from the corresponding author upon reasonable request.",
        "双通道太赫兹光谱缓存（.npz）、相对路径 Python 分析与审计脚本、requirements.txt、300 DPI 图件及机器可读 JSON 审计日志已公开发布于 https://github.com/l114514sh-cmyk/THz-TCM-DualView-Manifold。原始仪器 Excel 导出文件由杨意艺采集、经沈印作为共享研究资源提供（亦用于课题组其他指导研究）；本文提出的双视图 SW-MCUVE-Manifold 架构、压片分组嵌套验证、输入受控统计基准及 DFT–MC-UVE 对齐分析为本研究独有。原始导出文件可向通讯作者合理申请获取。",
        first_line_indent=0
    )

    # References (Strictly sequential [1]..[39])
    m.add_page_break()
    m.add_heading("References", "参考文献", level=1)
    for ref in REFS:
        m.add_para(ref, align="both", space_before=0, space_after=45, line=240, size_pt=9.3)

    return m


# Build Pure-EN Submission Manuscript & Verify Citation Order!
m_en = build_manuscript(bilingual=False)
en_path = OUT_DIR / "Manuscript_EN_Submission.docx"
m_en.save(en_path)

# Programmatic Citation Order Check on Pure-EN Manuscript (before References section)
body_xml = "".join(m_en.body_parts)
ref_split = body_xml.split(">References<")[0]
cited_order = []
for grp in re.findall(r'\[(\d+(?:[–,]\d+)*)\]', ref_split):
    for part in grp.split(','):
        if '–' in part:
            a, b = map(int, part.split('–'))
            nums = list(range(a, b + 1))
        else:
            nums = [int(part)]
        for num in nums:
            if num not in cited_order:
                cited_order.append(num)
print(f"[CHECK] Unique references cited in main text: {len(cited_order)}/{len(REFS)}")
print(f"[CHECK] First-citation order matches 1..{len(REFS)}? {cited_order == list(range(1, len(REFS)+1))}")
if cited_order != list(range(1, len(REFS) + 1)):
    print("  Cited order:", cited_order)

# Build Bilingual Reference Copy
m_bi = build_manuscript(bilingual=True)
bi_path = OUT_DIR / "Manuscript_Bilingual_Reference.docx"
m_bi.save(bi_path)
print(f"[OK] Saved {en_path.name} ({len(m_en.media_files)} main figs) and {bi_path.name}")


# ==============================================================================
# 4. Separate Supplementary Material (Pure English, Figures S1a, S1b, S2 + Tables S1–S2)
# ==============================================================================
sm = DocxBuilder(bilingual=False)
sm.add_title("Supplementary Material")
sm.add_para(
    "Dual-View Terahertz Spectroscopy and Stability-Weighted Chemometrics for Classification of Traditional Chinese Medicinal Materials Across Distinct Botanical Matrices",
    align="center", italic=True, size_pt=11.0, space_after=60
)
sm.add_para("Sihao Liu, Ziyuan Zhu, Yin Shen* (Chongqing Medical University, Chongqing 400016, China)",
            align="center", size_pt=10.0, space_after=160)

sm.add_heading("Section S1. Supplementary Figures", level=1)
sm.add_image(
    SUB_FIG_DIR / "Figure_S1a_Ablation_Seed.png", width_inches=5.5, max_height_inches=3.6,
    en_prefix="Fig. S1a. ",
    en_caption="Module knockout ablation on Ziziphi Spinosae Semen (five commercial batches, n = 499 scans across 100 pellets) under strict pellet-grouped double-nested 5-fold CV."
)
sm.add_image(
    SUB_FIG_DIR / "Figure_S1b_Baseline_Seed.png", width_inches=5.7, max_height_inches=3.6,
    en_prefix="Fig. S1b. ",
    en_caption="Input-controlled baseline comparison on Ziziphi Spinosae Semen (n = 499, 100 pellets) under identical pellet-grouped 5-fold CV across Track A (Raw Dual-Channel) and Track B (3,222-dim Dual-View)."
)
sm.add_image(
    SUB_FIG_DIR / "Figure_S2_Dynamic_Range.png", width_inches=6.0, max_height_inches=3.2,
    en_prefix="Fig. S2. ",
    en_caption="Measured THz-TDS transmission dynamic range (TERA K15, empty dry-N₂ reference) computed directly from raw frequency-domain power exports across all three botanical matrices, confirming > 27.4 dB sample dynamic range at 1.04 THz."
)

sm.add_heading("Section S2. Complete Per-Class Metrics and Paired Pellet-Cluster Bootstrap 95% CIs", level=1)

# Table S1: Complete Per-Class Classification Metrics
s1_rows = []
for ds_lbl, ds_obj in [("Astragali Radix", HQ), ("Ziziphi Spinosae", SZ), ("Gastrodia elata", TM)]:
    for cls_name in ds_obj["classes"]:
        pc = ds_obj["per_class"][cls_name]
        s1_rows.append([
            f"{ds_lbl} — {cls_name}", str(pc["support"]), str(pc["correct"]),
            f"{pc['precision']:.2f}", f"{pc['recall']:.2f}", f"{pc['f1']:.4f}"
        ])
sm.add_table(
    headers=["Matrix — Class", "Support (n)", "Correct", "Precision (%)", "Recall (%)", "F1-Score"],
    rows=s1_rows,
    col_widths_dxa=[3460, 1100, 1000, 1300, 1250, 1250],
    en_title="Table S1. Per-class classification metrics under pellet-grouped double-nested 5-fold CV (all 13 classes across 262 pellets).",
    font_pt=8.4
)

# Table S2: Full Paired Pellet-Cluster Bootstrap 95% CIs
s2_rows = []
for ds_lbl, ds_obj in [("Astragali Radix", HQ), ("Ziziphi Spinosae", SZ), ("Gastrodia elata", TM)]:
    for bk in [
        "PLS-DA (Raw Dual-Channel)", "RF (Raw Dual-Channel)", "RBF-SVM (Raw Dual-Channel)",
        "PLS-DA (Dual-View 3222-d)", "RF (Dual-View 3222-d)", "RBF-SVM (Dual-View 3222-d)",
        "Hard MC-UVE-SVM (Dual-View 3222-d)",
    ]:
        bs = ds_obj["paired_bootstrap_vs_proposed"][bk]
        br = ds_obj["baselines_fair"][bk]
        s2_rows.append([
            ds_lbl, bk, f"{br['acc']:.2f}%", f"{br['pellet_acc']:.2f}%",
            f"{bs['delta_acc']:+.2f}% [{bs['ci95_lo']:+.2f}, {bs['ci95_hi']:+.2f}]",
            f"{bs['p_boot']:.4f}"
        ])
sm.add_table(
    headers=["Matrix", "Baseline Model", "Scan Acc", "Pellet Vote", "ΔAcc (Prop − Base) [95% CI]", "p_boot"],
    rows=s2_rows,
    col_widths_dxa=[1450, 2650, 1000, 1050, 2260, 950],
    en_title="Table S2. Complete paired pellet-cluster bootstrap (2,000 resamples) accuracy differences and two-sided p-values across all input-controlled baselines.",
    font_pt=8.0
)

sm_path = OUT_DIR / "Supplementary_Material.docx"
sm.save(sm_path)
print(f"[OK] Saved {sm_path.name} ({len(sm.media_files)} supplementary figs)")
