#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

EXAM_MARKER_RE = re.compile(r">\s*ĐỀ\s*(\d+)\s*<", re.IGNORECASE)
IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*\"([^\"]*)\"")
UNSUPPORTED_SPAN_TAG_RE = re.compile(
    r"(<span\b[^>]*class=\"[^\"]*unsupported-equation[^\"]*\"[^>]*>)\[([^\]]+)\]</span>",
    re.IGNORECASE,
)
MATH_OPEN_RE = re.compile(r"<(?:\w+:)?math\b", re.IGNORECASE)
MATH_FRAGMENT_RE = re.compile(r"<(?:\w+:)?math\b.*?</(?:\w+:)?math>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
CHEM_FIXED_RE = re.compile(r'data-chem-fixed\s*=\s*"1"', re.IGNORECASE)
CHEM_ARROW_FIXED_RE = re.compile(r'data-chem-arrow-fixed\s*=\s*"1"', re.IGNORECASE)
CHEM_UNIT_FIXED_RE = re.compile(r'data-chem-unit-fixed\s*=\s*"1"', re.IGNORECASE)

CORRUPTION_PATTERNS = {
    "dien_tro": re.compile(r"(?iu)điện\s+trờ"),
    "voi_corrupt": re.compile(r"(?iu)(?<!\w)(?:vớ(?:ii+)?|vöi(?:i+)?|với{2,})(?!\w)"),
    "thoi_diem": re.compile(r"(?iu)thừi\s+điềm"),
    "mpa_case": re.compile(r"\bMpa\b"),
    "unit_cm2_split": re.compile(r"(?iu)\bc\s+m\s*(?:²|2)\b"),
    "unit_mol_split": re.compile(r"(?iu)\bm\s+o\s+l\b"),
    "trong_giai_doan": re.compile(r"(?iu)trọng\s+giai\s+đoạn"),
    "t_lag_glucose": re.compile(r"(?iu)\bT\s+lag\s+glucose\b"),
    "hai_to_thi_nghiem": re.compile(r"(?iu)có\s+2\s+tố\s+thí\s+nghiệm"),
    "daet": re.compile(r"Ñaët"),
    "taan": re.compile(r"taán"),
}

PHYSICS_UNIT_ISSUE_PATTERNS = {
    "unit_cm2_split": re.compile(r"(?iu)\bc\s+m\s*(?:²|2)\b"),
    "unit_cm3_split": re.compile(r"(?iu)\bc\s+m\s*(?:³|3)\b"),
    "unit_mpa_case": re.compile(r"\bMpa\b"),
    "unit_mol_split": re.compile(r"(?iu)\b(?:m\s+o\s+l|mo\s+l)\b"),
    "unit_mol_inv_split": re.compile(r"(?iu)\b(?:m\s+o\s+l|mo\s+l)\s*(?:\^?\s*-\s*1|[−⁻-]\s*1)\b"),
}

PHYSICS_TEXT_CORRUPTION_PATTERNS = {
    "dien_tro": re.compile(r"(?iu)điện\s+trờ"),
    "thoi_diem": re.compile(r"(?iu)thừi\s+điềm"),
    "ket_qua": re.compile(r"(?iu)kết\s+quà"),
    "khoi_luong": re.compile(r"(?iu)khối\s+lương"),
    "phong_xa": re.compile(r"(?iu)phóng\s*xạ̣"),
    "nhiet": re.compile(r"(?iu)nhiệ̣t"),
    "can_thiet_de": re.compile(r"(?iu)cần\s+thiết\s+đề\b"),
    "su_dung_de_xac_dinh": re.compile(r"(?iu)được\s+sử\s+dụng\s+đề\s+xác\s+định"),
    "do_dai": re.compile(r"(?iu)đồ\s+dài"),
    "the_tich": re.compile(r"(?iu)thế\s+tích"),
    "bien_doi": re.compile(r"(?iu)biến\s+đối"),
    "truong": re.compile(r"(?iu)truờng"),
    "chuyen_thanh_nhiet": re.compile(r"(?iu)chuyền\s+thành\s+nhiệt"),
}

MATH_TEXT_GLYPH_CORRUPTION_PATTERNS = {
    "private_use_glyph": re.compile(r"[\uE000-\uF8FF]"),
    "bullet_glyph": re.compile(r""),
    "mot_ta": re.compile(r"(?iu)\bmôt\s+tả\b"),
    "ket_qua": re.compile(r"(?iu)\bk[ée]t\s+quả\b"),
    "ket_qua_alt": re.compile(r"(?iu)\bkết\s+quá\b"),
    "ta_do": re.compile(r"(?iu)\bTa\s+đó\b"),
    "ti_le": re.compile(r"(?iu)\btí\s+lệ\b"),
    "ta_can_tinh": re.compile(r"(?iu)\bTa\s+cẩn\s+tính\b"),
    "do_thi_ham_so": re.compile(r"(?iu)\bđô\s+thị(?=\s+của\s+hàm\s+số\b)"),
}

MATH_MATHML_GLYPH_ISSUE_PATTERNS = {
    "malgun_conditional_bar": re.compile(r'(?is)<mo\b[^>]*fontfamily="Malgun Gothic"[^>]*>\s*[∣|]\s*</mo>'),
    "set_membership_plain_z": re.compile(r"(?is)<mo\b[^>]*>\s*∈\s*</mo>\s*<mi\b[^>]*>\s*Z\s*</mi>"),
    "vector_combining_arrow_operator": re.compile(r"(?is)<(?:mml:)?mo\b[^>]*>\s*⃗\s*</(?:mml:)?mo>"),
}

MIXED_MATH_TEXT_LAYOUT_PATTERNS = {
    "mathml_cm2_split": re.compile(
        r"(?is)<mtext\b[^>]*>\s*c\s*</mtext>\s*<msup\b[^>]*>\s*<mtext\b[^>]*>\s*m\s*</mtext>\s*<mn\b[^>]*>\s*2\s*</mn>\s*</msup>"
    ),
    "mathml_cm3_split": re.compile(
        r"(?is)<mtext\b[^>]*>\s*c\s*</mtext>\s*<msup\b[^>]*>\s*<mtext\b[^>]*>\s*m\s*</mtext>\s*<mn\b[^>]*>\s*3\s*</mn>\s*</msup>"
    ),
    "mathml_mol_inv_split": re.compile(
        r"(?is)<mtext\b[^>]*>\s*mo\s*</mtext>\s*<msup\b[^>]*>\s*<mtext\b[^>]*>\s*l\s*</mtext>\s*<mrow\b[^>]*>\s*<mo\b[^>]*>\s*[−-]\s*</mo>\s*<mn\b[^>]*>\s*1\s*</mn>\s*</mrow>\s*</msup>"
    ),
    "mathml_blank_degree_base": re.compile(
        r"(?is)<msup\b[^>]*>\s*<mn\b[^>]*>\s*(?:&nbsp;|\u00A0)?\s*</mn>\s*<mtext\b[^>]*>\s*[∘°]\s*</mtext>\s*</msup>\s*<mtext\b[^>]*>\s*C\s*</mtext>"
    ),
}

CHEM_INLINE_ISSUE_RE = re.compile(
    r"(?<![\w])(?:[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?[A-Z][A-Za-z0-9()·•/]*[₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻][A-Za-z0-9()·•/₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻+\-−]*",
    re.UNICODE,
)
CHEM_ARROW_ISSUE_RE = re.compile(r"(?:<=>|<->|->|â†’|âž”|â‡Œ|â†”|[\uf0ae\uf0e0\uf0de\uf0f0\uf0ad\uf0af])")
CHEM_UNIT_ISSUE_RE = re.compile(r"(?iu)(?:mol\s*[·•.]?\s*L\s*(?:\^-?\s*1|[⁻−-]\s*1)|\d+\s*(?:\^0|⁰)\s*C\b|\b10\^\d+\b)")
CHEM_GLYPH_ISSUE_RE = re.compile(r"[\uf0ae\uf0e0\uf0de\uf0f0\uf0ad\uf0af]")
WORD_FIELD_LEAKAGE_RE = re.compile(r"(?iu)\b(?:INCLUDEPICTURE|MERGEFORMATINET|MERGEFORMAT)\b")
PUBLISH_DEBUG_ATTR_RE = re.compile(
    r'(?iu)\sdata-(?:render-attempted|render-source-used|render-source-exts|render-source-assets|render-role)="[^"]*"'
)
PUBLISH_NAMESPACE_LEAKAGE_RE = re.compile(r'(?iu)xmlns:tr="http://transpect\.io"')
DOWNS_REACTION_ISSUE_RE = re.compile(
    r"(?is)2Cl<sup>\s*[-−]\s*</sup>\s*→\s*(?:<span\b[^>]*class=\"[^\"]*chem-inline[^\"]*\"[^>]*>)?\s*2e<sup>\s*\+\s*</sup>\s*(?:</span>)?\s*Cl<sub>\s*2\s*</sub>"
)
NUMERIC_MULTIPLY_ZERO_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*[x*×]\s*0\s*=\s*(\d+(?:[.,]\d+)?)")
NUMERIC_M_EQ_29_RE = re.compile(r"\bM\s*=\s*29\b")
SVG_ROOT_TAG_RE = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)
SVG_ATTR_RE = re.compile(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*"([^"]*)"')
EMPTY_PARAGRAPH_HTML_RE = r"<p>\s*(?:(?:<br\s*/?>)|&nbsp;|&#160;|\s)*</p>"
EMPTY_PARAGRAPH_TAG_RE = re.compile(rf"(?is){EMPTY_PARAGRAPH_HTML_RE}")
EMPTY_PARAGRAPH_CHAIN_BEFORE_DOCX_TABLE_RE = re.compile(
    rf'(?is)(?P<empties>(?:{EMPTY_PARAGRAPH_HTML_RE}\s*)+)(?=<table\b(?=[^>]*class="[^"]*docx-table[^"]*")[^>]*>)'
)
EMPTY_PARAGRAPH_CHAIN_AFTER_DOCX_TABLE_RE = re.compile(
    rf'(?is)</table>\s*(?P<empties>(?:{EMPTY_PARAGRAPH_HTML_RE}\s*)+)'
)
EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_START_RE = re.compile(
    rf'(?is)<td\b[^>]*>\s*(?P<empties>(?:{EMPTY_PARAGRAPH_HTML_RE}\s*)+)'
)
EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_END_RE = re.compile(
    rf'(?is)(?P<empties>(?:{EMPTY_PARAGRAPH_HTML_RE}\s*)+)\s*</td>'
)
MATH_BLOCK_CAPTURE_RE = re.compile(r'(?is)<div class="math-block[^"]*">(?P<body>.*?)</div>')

FALLBACK_CLASSES = {
    "equation-fallback",
    "equation-preview",
    "diagram-asset",
    "physics-diagram",
    "physics-chart",
    "diagram-preview",
    "chemical-diagram",
    "chem-diagram",
    "ole-preview",
    "embedded-object",
}

TYPE_KEYS = (
    "Equation.DSMT4",
    "Visio.Drawing.15",
    "ChemDraw.Document.6.0",
    "ChemDraw_x64.Document.6.0",
    "ACD.ChemSketch.20",
    "ChemWindow.Document",
    ".emf",
    ".wmf",
)
CLASSIFICATION_KEYS = {
    "equation",
    "diagram",
    "chart",
    "chemical-diagram",
    "generic-image",
    "unknown-preview",
}
OUTPUT_MODES = {"internal", "publish"}
QA_SCHEMA_VERSION = "qa.v1"
PUBLISH_GATE_SEVERITIES = ("info", "warning", "error", "blocker")

BLANK_MEAN_THRESHOLD = 0.9995
BLANK_STDDEV_THRESHOLD = 0.001
NEAR_WHITE_MEAN_THRESHOLD = 0.985
NEAR_WHITE_STDDEV_THRESHOLD = 0.03
TINY_WIDTH_THRESHOLD = 140
TINY_HEIGHT_THRESHOLD = 60
BAD_CROP_RATIO_THRESHOLD = 10.0
OVERSIZED_PNG_WIDTH_THRESHOLD = 1000
OVERSIZED_PNG_HEIGHT_THRESHOLD = 760
OVERSIZED_SVG_WIDTH_MM_THRESHOLD = 150.0
OVERSIZED_SVG_HEIGHT_MM_THRESHOLD = 120.0
CSS_BASE_REM_PX = 16.0
MM_PER_PX = 25.4 / 96.0
CHEM_DIAGRAM_DISPLAY_MAX_REM = 30.0
CHEM_DIAGRAM_DISPLAY_TABLE_MAX_REM = 22.0
CHEM_DIAGRAM_DISPLAY_MAX_PX = CHEM_DIAGRAM_DISPLAY_MAX_REM * CSS_BASE_REM_PX
CHEM_DIAGRAM_DISPLAY_TABLE_MAX_PX = CHEM_DIAGRAM_DISPLAY_TABLE_MAX_REM * CSS_BASE_REM_PX
CHEM_DIAGRAM_DISPLAY_MAX_MM = CHEM_DIAGRAM_DISPLAY_MAX_PX * MM_PER_PX
CHEM_DIAGRAM_DISPLAY_TABLE_MAX_MM = CHEM_DIAGRAM_DISPLAY_TABLE_MAX_PX * MM_PER_PX
PLACEHOLDER_GIF_SIZE_THRESHOLD = 128
WEB_SAFE_IMAGE_EXTENSIONS = {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp"}
TABLE_INLINE_TRIMMED_RULE_RE = re.compile(r"td\s+\.inline-image-trimmed\s*\{([^}]*)\}", re.IGNORECASE)
CSS_MAX_WIDTH_REM_RE = re.compile(r"max-width\s*:\s*(?:min\(\s*100%\s*,\s*)?([0-9]+(?:\.[0-9]+)?)rem", re.IGNORECASE)
CSS_NON_AUTO_WIDTH_RE = re.compile(r"width\s*:\s*(?!auto\b)[^;]+;", re.IGNORECASE)
TABLE_INLINE_IMAGE_POLICY_MAX_REM_THRESHOLD = 20.0
TABLE_TWO_CELL_LAYOUT_RE = re.compile(
    r'(?is)<table class="docx-table">\s*<tr>\s*<td>(?P<left>.*?)</td>\s*<td>(?P<right>.*?)</td>\s*</tr>\s*</table>'
)
INLINE_IMAGE_CLASS_TAG_RE = re.compile(r'(?is)<img\b(?=[^>]*class="[^"]*inline-image[^"]*")[^>]*>')
STANDALONE_INLINE_IMAGE_PARAGRAPH_RE = re.compile(
    r'(?is)<p>\s*(?P<img><img\b(?=[^>]*class="[^"]*inline-image[^"]*")[^>]*?/?>)\s*</p>'
)
ESSAY_FIGURE_IMAGE_TAG_RE = re.compile(r'(?is)<img\b(?=[^>]*class="[^"]*essay-figure-image[^"]*")[^>]*>')
ESSAY_ESSENTIAL_FIGURE_TAG_RE = re.compile(
    r'(?is)<figure\b[^>]*class="[^"]*(?:essay-figure|question-figure)[^"]*essential-figure[^"]*"'
)
ESSAY_QUESTION_MARKER_RE = re.compile(r"(?iu)\bcâu\s*\d+\b")
ESSAY_ASK_SIGNAL_RE = re.compile(
    r"(?iu)\b(?:hỏi|tính|bao\s+nhiêu|làm\s+tròn|xác\s+suất|chi\s+phí|quãng\s+đường|thể\s+tích|chiều\s+cao|khoảng\s+cách|độ\s+dốc|độ\s+dài)\b"
)
ESSAY_ESSENTIAL_FIGURE_SIGNAL_RE = re.compile(
    r"(?iu)\b(?:đồ\s*thị|biểu\s*đồ|sơ\s*đồ|bảng\s*biến\s*thiên|tham\s*khảo\s*hình|xem\s*hình|hình\s*bên|hình\s*dưới|hình\s*vẽ|như\s+trong\s+hình|hình\s+minh\s*họa|hình\s+minh\s*hoạ)\b"
)
ESSAY_CONTEXT_FIGURE_SIGNAL_RE = re.compile(
    r"(?iu)\b(?:trực\s*thăng|tòa\s*nhà|toà\s*nhà|nhà\s*hàng|sân\s*bay|khách\s*hàng|khung\s*cảnh|cứu\s*hộ|ảnh\s*minh\s*họa|hyperloop)\b"
)
MULTI_CHOICE_OPTION_MARKER_RE = re.compile(r"(?iu)\b[ABCD]\.")
NONESSENTIAL_STANDALONE_CONTEXT_SIGNAL_RE = re.compile(
    r"(?iu)\b(?:cabin|cáp\s*treo|cap\s*treo|trực\s*thăng|truc\s*thang|tòa\s*nhà|toà\s*nhà|toa\s*nha|hyperloop|ảnh\s*minh\s*họa|anh\s*minh\s*hoa)\b"
)
NONESSENTIAL_STANDALONE_KEEP_CONTEXT_SIGNAL_RE = re.compile(
    r"(?iu)\b(?:một\s+cabin\s+cáp\s*treo|cabin\s+cáp\s*treo|cabin\s+cap\s*treo)\b"
)


@dataclass
class UnresolvedObject:
    scope: str
    location: str
    exam: str
    source_asset: str
    classification: str
    fallback_type: str
    prog_id: str
    source_ext: str
    alt: str
    render_attempted: bool
    render_source_used: str
    render_output_type: str
    render_success: bool
    render_source_exts: str
    render_source_assets: str


def parse_attrs(tag: str) -> Dict[str, str]:
    attrs: Dict[str, str] = {}
    for key, value in ATTR_RE.findall(tag):
        attrs[key.lower()] = value
    return attrs


def extract_nonessential_standalone_candidate_src(tag: str) -> Optional[str]:
    attrs = parse_attrs(tag)
    css_class = attrs.get("class", "").lower()
    if "inline-image" not in css_class:
        return None
    if any(
        token in css_class
        for token in (
            "essay-figure-image",
            "essential-figure-image",
            "context-figure-image",
            "equation",
            "diagram",
            "chart",
            "chemical-diagram",
            "chem-diagram",
        )
    ):
        return None
    if any(key in attrs for key in ("data-ole-kind", "data-ole-progid", "data-fallback-type")):
        return None
    render_role = attrs.get("data-render-role", "").lower()
    if any(token in render_role for token in ("equation", "diagram", "chart", "chemical")):
        return None
    render_output_type = attrs.get("data-render-output-type", "").lower()
    if (
        "equation" in render_output_type
        or "diagram" in render_output_type
        or render_output_type in {"chart", "chemical-diagram"}
    ):
        return None
    alt = attrs.get("alt", "").lower()
    if any(token in alt for token in ("equation", "diagram", "graph", "đồ thị")):
        return None
    trim_candidate = attrs.get("data-trim-candidate", "").lower()
    trim_applied = attrs.get("data-trim-applied", "").lower()
    if trim_candidate != "false" or trim_applied != "false":
        return None
    src = attrs.get("src", "").strip()
    if not src:
        return None
    src_lower = src.lower()
    if not src_lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff")):
        return None
    return src


def extract_adjacent_paragraph_text(html_text: str, anchor: int, forward: bool) -> str:
    if not html_text:
        return ""
    if forward:
        p_open = html_text.find("<p", max(0, anchor))
        if p_open < 0:
            return ""
        open_end = html_text.find(">", p_open)
        if open_end < 0:
            return ""
        close = html_text.find("</p>", open_end)
        if close < 0:
            return ""
        paragraph_html = html_text[open_end + 1 : close]
    else:
        close = html_text.rfind("</p>", 0, max(0, anchor))
        if close < 0:
            return ""
        p_open = html_text.rfind("<p", 0, close)
        if p_open < 0:
            return ""
        open_end = html_text.find(">", p_open)
        if open_end < 0 or open_end >= close:
            return ""
        paragraph_html = html_text[open_end + 1 : close]
    paragraph_html = INLINE_IMAGE_CLASS_TAG_RE.sub(" ", paragraph_html)
    return normalize_visible_text(paragraph_html)


def count_remaining_nonessential_standalone_image_candidates(html_text: str) -> int:
    candidates: List[Tuple[str, bool, bool, bool]] = []
    for match in STANDALONE_INLINE_IMAGE_PARAGRAPH_RE.finditer(html_text):
        tag = match.group("img")
        src = extract_nonessential_standalone_candidate_src(tag)
        if src is None:
            continue
        previous_text = extract_adjacent_paragraph_text(html_text, match.start(), forward=False)
        next_text = extract_adjacent_paragraph_text(html_text, match.end(), forward=True)
        context_text = f"{previous_text} {next_text}".strip()
        has_figure_reference = bool(ESSAY_ESSENTIAL_FIGURE_SIGNAL_RE.search(context_text))
        has_context_signal = bool(
            ESSAY_CONTEXT_FIGURE_SIGNAL_RE.search(context_text)
            or NONESSENTIAL_STANDALONE_CONTEXT_SIGNAL_RE.search(context_text)
        )
        has_protected_keep_context = bool(NONESSENTIAL_STANDALONE_KEEP_CONTEXT_SIGNAL_RE.search(context_text))
        candidates.append((src, has_figure_reference, has_context_signal, has_protected_keep_context))
    if not candidates:
        return 0
    count_by_src: Dict[str, int] = {}
    figure_reference_by_src: Dict[str, bool] = {}
    context_signal_by_src: Dict[str, bool] = {}
    protected_keep_context_by_src: Dict[str, bool] = {}
    for src, has_figure_reference, has_context_signal, has_protected_keep_context in candidates:
        count_by_src[src] = count_by_src.get(src, 0) + 1
        figure_reference_by_src[src] = figure_reference_by_src.get(src, False) or has_figure_reference
        context_signal_by_src[src] = context_signal_by_src.get(src, False) or has_context_signal
        protected_keep_context_by_src[src] = (
            protected_keep_context_by_src.get(src, False) or has_protected_keep_context
        )
    suppressible_sources = {
        src
        for src, count in count_by_src.items()
        if count >= 2
        and context_signal_by_src.get(src, False)
        and not figure_reference_by_src.get(src, False)
        and not protected_keep_context_by_src.get(src, False)
    }
    return sum(1 for src, _, _, _ in candidates if src in suppressible_sources)


def detect_subject(raw_name: str) -> str:
    if not raw_name:
        return "generic"
    ascii_name = unicodedata.normalize("NFD", raw_name)
    ascii_name = "".join(ch for ch in ascii_name if unicodedata.category(ch) != "Mn")
    tokens = set(re.sub(r"[^a-z0-9]+", " ", ascii_name.lower()).split())
    if {"hoa", "chem", "chemistry"} & tokens:
        return "chemistry"
    if "ly" in tokens or {"phys", "physics"} & tokens or {"vat", "ly"} <= tokens:
        return "physics"
    if {"toan", "math"} & tokens:
        return "math"
    if {"sinh", "bio", "biology"} & tokens:
        return "biology"
    return "generic"


def detect_exam(line: str, current: str) -> str:
    match = EXAM_MARKER_RE.search(line)
    if not match:
        return current
    return f"DE_{match.group(1)}"


def parse_conversion_log(log_path: Optional[Path]) -> Dict[str, Optional[int]]:
    result = {
        "normalized_text_fixes_applied": None,
        "unresolved_visio_previews": None,
        "ole_preview_images": None,
        "emf_wmf_previews": None,
        "rasterized_metafile_previews": None,
        "rasterized_metafile_cache_hits": None,
        "sidecar_mathml_equations": None,
        "omml_equations": None,
        "chemistry_inline_fixes_applied": None,
        "chemistry_arrow_symbol_fixes_applied": None,
        "chemistry_unit_fixes_applied": None,
        "physics_unit_fixes_applied": None,
        "physics_text_fixes_applied": None,
        "mixed_math_text_cleanup_fixes_applied": None,
        "math_glyph_cleanup_fixes_applied": None,
        "empty_paragraph_removed_count": None,
        "table_adjacent_empty_paragraph_cleanup_count": None,
        "table_cell_empty_paragraph_removed_count": None,
        "math_block_flow_cleanup_count": None,
        "suppressed_blank_standalone_image_count": None,
        "suppressed_nonessential_standalone_image_count": None,
        "restored_context_image_count": None,
    }
    if log_path is None or not log_path.exists():
        return result

    text = log_path.read_text(encoding="utf-8", errors="ignore")
    regex_by_field = {
        "normalized_text_fixes_applied": r"Text normalizations applied:\s*(\d+)",
        "unresolved_visio_previews": r"Unresolved Visio previews:\s*(\d+)",
        "ole_preview_images": r"OLE fallback images used:\s*(\d+)",
        "emf_wmf_previews": r"EMF/WMF previews encountered:\s*(\d+)",
        "rasterized_metafile_previews": r"EMF/WMF previews rasterized to PNG:\s*(\d+)",
        "rasterized_metafile_cache_hits": r"EMF/WMF raster-cache hits:\s*(\d+)",
        "sidecar_mathml_equations": r"Transpect sidecar equations used:\s*(\d+)",
        "omml_equations": r"OMML equations converted:\s*(\d+)",
        "chemistry_inline_fixes_applied": r"Chemistry inline fixes applied:\s*(\d+)",
        "chemistry_arrow_symbol_fixes_applied": r"Chemistry arrow/symbol fixes applied:\s*(\d+)",
        "chemistry_unit_fixes_applied": r"Chemistry unit fixes applied:\s*(\d+)",
        "physics_unit_fixes_applied": r"Physics unit fixes applied:\s*(\d+)",
        "physics_text_fixes_applied": r"Physics text fixes applied:\s*(\d+)",
        "mixed_math_text_cleanup_fixes_applied": r"Mixed math/text cleanup fixes applied:\s*(\d+)",
        "math_glyph_cleanup_fixes_applied": r"Math glyph/text fixes applied:\s*(\d+)",
        "empty_paragraph_removed_count": r"Empty paragraphs removed:\s*(\d+)",
        "table_adjacent_empty_paragraph_cleanup_count": r"Table-adjacent empty paragraph cleanups:\s*(\d+)",
        "table_cell_empty_paragraph_removed_count": r"Table-cell empty paragraphs removed:\s*(\d+)",
        "math_block_flow_cleanup_count": r"Math-block flow cleanups:\s*(\d+)",
        "suppressed_blank_standalone_image_count": r"Suppressed blank standalone images:\s*(\d+)",
        "suppressed_nonessential_standalone_image_count": r"Suppressed nonessential standalone context images:\s*(\d+)",
        "restored_context_image_count": r"Restored context images kept:\s*(\d+)",
    }
    for key, pattern in regex_by_field.items():
        match = re.search(pattern, text)
        if match:
            result[key] = int(match.group(1))
    return result


def normalize_visible_text(line: str) -> str:
    text = MATH_FRAGMENT_RE.sub(" ", line)
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return text.replace("\xa0", " ")


def count_matches(patterns: Dict[str, re.Pattern[str]], text: str) -> int:
    total = 0
    for pattern in patterns.values():
        total += len(pattern.findall(text))
    return total


def count_chem_inline_issues(text: str) -> int:
    return len(CHEM_INLINE_ISSUE_RE.findall(text))


def count_chem_arrow_symbol_issues(text: str) -> int:
    return len(CHEM_ARROW_ISSUE_RE.findall(text))


def count_chem_unit_issues(text: str) -> int:
    return len(CHEM_UNIT_ISSUE_RE.findall(text))


def count_chem_glyph_issues(text: str) -> int:
    return len(CHEM_GLYPH_ISSUE_RE.findall(text))


def count_physics_unit_issues(text: str) -> int:
    return count_matches(PHYSICS_UNIT_ISSUE_PATTERNS, text)


def count_physics_text_corruption_issues(text: str) -> int:
    return count_matches(PHYSICS_TEXT_CORRUPTION_PATTERNS, text)


def count_mixed_math_text_layout_issues(html_line: str) -> int:
    return count_matches(MIXED_MATH_TEXT_LAYOUT_PATTERNS, html_line)


def count_math_glyph_issues(visible_text: str, html_line: str) -> int:
    return count_matches(MATH_TEXT_GLYPH_CORRUPTION_PATTERNS, visible_text) + count_matches(
        MATH_MATHML_GLYPH_ISSUE_PATTERNS, html_line
    )


def extract_table_inline_image_policy(html_text: str) -> Dict[str, object]:
    match = TABLE_INLINE_TRIMMED_RULE_RE.search(html_text)
    if not match:
        return {
            "rule_found": False,
            "max_width_rem": None,
            "has_non_auto_width": False,
            "sizing_adjusted": False,
        }
    rule = match.group(1)
    rem_values = [float(v) for v in CSS_MAX_WIDTH_REM_RE.findall(rule)]
    max_width_rem = max(rem_values) if rem_values else None
    has_non_auto_width = bool(CSS_NON_AUTO_WIDTH_RE.search(rule))
    sizing_adjusted = bool(
        max_width_rem is not None
        and max_width_rem >= TABLE_INLINE_IMAGE_POLICY_MAX_REM_THRESHOLD
        and has_non_auto_width
    )
    return {
        "rule_found": True,
        "max_width_rem": max_width_rem,
        "has_non_auto_width": has_non_auto_width,
        "sizing_adjusted": sizing_adjusted,
    }


def is_likely_essay_question_text(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if len(normalized) < 160:
        return False
    if not ESSAY_QUESTION_MARKER_RE.search(normalized):
        return False
    if not ESSAY_ASK_SIGNAL_RE.search(normalized):
        return False
    if len(MULTI_CHOICE_OPTION_MARKER_RE.findall(normalized)) >= 2:
        return False
    return True


def extract_essay_figure_layout_metrics(html_text: str) -> Dict[str, int]:
    relocated_count = len(ESSAY_FIGURE_IMAGE_TAG_RE.findall(html_text))
    centered_block_count = len(ESSAY_ESSENTIAL_FIGURE_TAG_RE.findall(html_text))
    remaining_layout_issues = 0
    figure_in_table_too_small_count = 0

    for table_match in TABLE_TWO_CELL_LAYOUT_RE.finditer(html_text):
        left = table_match.group("left")
        right = table_match.group("right")
        left_images = INLINE_IMAGE_CLASS_TAG_RE.findall(left)
        right_images = INLINE_IMAGE_CLASS_TAG_RE.findall(right)
        if len(left_images) + len(right_images) != 1:
            continue
        text_cell = right if left_images else left
        image_cell = left if left_images else right
        text_plain = normalize_visible_text(text_cell)
        if not is_likely_essay_question_text(text_plain):
            continue
        if ESSAY_FIGURE_IMAGE_TAG_RE.search(table_match.group(0)):
            continue
        remaining_layout_issues += 1
        if re.search(r'(?is)<img\b[^>]*class="[^"]*inline-image-trimmed[^"]*"', image_cell):
            figure_in_table_too_small_count += 1

    for paragraph_match in re.finditer(r"(?is)<p>(?P<body>.*?)</p>", html_text):
        body = paragraph_match.group("body")
        images = INLINE_IMAGE_CLASS_TAG_RE.findall(body)
        if len(images) != 1:
            continue
        if ESSAY_FIGURE_IMAGE_TAG_RE.search(body):
            continue
        text_without_image = INLINE_IMAGE_CLASS_TAG_RE.sub(" ", body)
        if is_likely_essay_question_text(normalize_visible_text(text_without_image)):
            remaining_layout_issues += 1

    return {
        "essay_question_figure_relocated_count": relocated_count,
        "essay_question_figure_centered_block_count": centered_block_count,
        "remaining_essay_question_figure_layout_issues": remaining_layout_issues,
        "figure_in_table_too_small_count": figure_in_table_too_small_count,
    }


def find_suspected_numeric_corruption(text: str, exam: str, location: str) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    for match in NUMERIC_MULTIPLY_ZERO_RE.finditer(text):
        rhs = match.group(2).replace(",", ".")
        try:
            rhs_value = float(rhs)
        except ValueError:
            continue
        if abs(rhs_value) > 1e-9:
            findings.append(
                {
                    "exam": exam,
                    "location": location,
                    "type": "multiply_zero_mismatch",
                    "snippet": match.group(0).strip(),
                }
            )
    for match in NUMERIC_M_EQ_29_RE.finditer(text):
        findings.append(
            {
                "exam": exam,
                "location": location,
                "type": "suspicious_mass_value",
                "snippet": match.group(0).strip(),
            }
        )
    return findings


def analyze_image_quality(image_path: Path) -> Dict[str, Optional[float]]:
    if not image_path.exists() or not image_path.is_file():
        return {
            "available": False,
            "width": None,
            "height": None,
            "mean": None,
            "stddev": None,
            "blank": False,
            "near_white": False,
            "tiny": False,
            "bad_crop": False,
        }

    magick_bin = shutil.which("magick")
    if not magick_bin:
        return {
            "available": False,
            "width": None,
            "height": None,
            "mean": None,
            "stddev": None,
            "blank": False,
            "near_white": False,
            "tiny": False,
            "bad_crop": False,
        }

    cmd = [
        magick_bin,
        str(image_path),
        "-colorspace",
        "Gray",
        "-format",
        "%w %h %[fx:mean] %[fx:standard_deviation]",
        "info:",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except Exception:
        return {
            "available": False,
            "width": None,
            "height": None,
            "mean": None,
            "stddev": None,
            "blank": False,
            "near_white": False,
            "tiny": False,
            "bad_crop": False,
        }
    if proc.returncode != 0:
        return {
            "available": False,
            "width": None,
            "height": None,
            "mean": None,
            "stddev": None,
            "blank": False,
            "near_white": False,
            "tiny": False,
            "bad_crop": False,
        }

    parts = proc.stdout.strip().split()
    if len(parts) != 4:
        return {
            "available": False,
            "width": None,
            "height": None,
            "mean": None,
            "stddev": None,
            "blank": False,
            "near_white": False,
            "tiny": False,
            "bad_crop": False,
        }

    width = int(parts[0])
    height = int(parts[1])
    mean = float(parts[2])
    stddev = float(parts[3])

    ratio = max((width / height) if height else 9999.0, (height / width) if width else 9999.0)
    blank = mean >= BLANK_MEAN_THRESHOLD and stddev <= BLANK_STDDEV_THRESHOLD
    near_white = not blank and mean >= NEAR_WHITE_MEAN_THRESHOLD and stddev <= NEAR_WHITE_STDDEV_THRESHOLD
    tiny = width < TINY_WIDTH_THRESHOLD or height < TINY_HEIGHT_THRESHOLD
    bad_crop = ratio >= BAD_CROP_RATIO_THRESHOLD

    return {
        "available": True,
        "width": width,
        "height": height,
        "mean": mean,
        "stddev": stddev,
        "blank": blank,
        "near_white": near_white,
        "tiny": tiny,
        "bad_crop": bad_crop,
    }


def analyze_gif_placeholder(image_path: Path, quality: Dict[str, Optional[float]]) -> Dict[str, bool]:
    result = {"placeholder": False, "blank": False, "tiny_pixel": False, "size_tiny": False}
    if not image_path.exists() or not image_path.is_file():
        return result
    try:
        file_size = image_path.stat().st_size
    except OSError:
        file_size = 0
    size_tiny = file_size <= PLACEHOLDER_GIF_SIZE_THRESHOLD
    width = quality.get("width") or 0
    height = quality.get("height") or 0
    tiny_pixel = width <= 1 or height <= 1
    blank = bool(quality.get("blank"))
    result["size_tiny"] = size_tiny
    result["tiny_pixel"] = tiny_pixel
    result["blank"] = blank
    result["placeholder"] = size_tiny or tiny_pixel or blank
    return result


def parse_svg_length_mm(raw: str) -> Optional[float]:
    if not raw:
        return None
    value = raw.strip().lower().replace(",", ".")
    match = re.match(r"^([+-]?\d+(?:\.\d+)?)([a-z%]*)$", value)
    if not match:
        return None
    num = float(match.group(1))
    unit = match.group(2)
    if unit == "mm":
        return num
    if unit == "cm":
        return num * 10.0
    if unit == "in":
        return num * 25.4
    if unit == "pt":
        return num * 25.4 / 72.0
    if unit == "px":
        return num * 25.4 / 96.0
    if unit == "":
        return num
    return None


def analyze_svg_dimensions(svg_path: Path) -> Dict[str, Optional[float]]:
    if not svg_path.exists() or not svg_path.is_file():
        return {"available": False, "width_mm": None, "height_mm": None, "oversized": False}
    try:
        text = svg_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"available": False, "width_mm": None, "height_mm": None, "oversized": False}

    root_match = SVG_ROOT_TAG_RE.search(text)
    if not root_match:
        return {"available": False, "width_mm": None, "height_mm": None, "oversized": False}

    attrs: Dict[str, str] = {}
    for key, value in SVG_ATTR_RE.findall(root_match.group(0)):
        attrs[key.lower()] = value

    width_mm = parse_svg_length_mm(attrs.get("width", ""))
    height_mm = parse_svg_length_mm(attrs.get("height", ""))
    view_box = attrs.get("viewbox", "")
    if (width_mm is None or height_mm is None) and view_box:
        parts = [p for p in re.split(r"[,\s]+", view_box.strip()) if p]
        if len(parts) == 4:
            try:
                vb_width = float(parts[2])
                vb_height = float(parts[3])
                if width_mm is None:
                    width_mm = vb_width * 25.4 / 96.0
                if height_mm is None:
                    height_mm = vb_height * 25.4 / 96.0
            except ValueError:
                pass

    oversized = bool(
        (width_mm is not None and width_mm > OVERSIZED_SVG_WIDTH_MM_THRESHOLD)
        or (height_mm is not None and height_mm > OVERSIZED_SVG_HEIGHT_MM_THRESHOLD)
    )
    return {
        "available": width_mm is not None or height_mm is not None,
        "width_mm": width_mm,
        "height_mm": height_mm,
        "oversized": oversized,
    }


def is_inside_table_context(line: str, tag_start: int) -> bool:
    prefix = line[:tag_start].lower()
    td_open = prefix.rfind("<td")
    td_close = prefix.rfind("</td")
    return td_open != -1 and td_open > td_close


def classify_occurrence(attrs: Dict[str, str], css_class: str, alt: str, src: str, prog_id: str) -> str:
    kind = attrs.get("data-ole-kind", "").strip().lower()
    if kind == "equation":
        return "equation"
    if kind == "diagram":
        return "diagram"
    if kind == "chemical-diagram":
        return "chemical-diagram"
    if kind == "illustration":
        return "generic-image"

    class_set = {c.strip() for c in css_class.split() if c.strip()}
    joined = f"{css_class} {alt} {src} {prog_id}".lower()

    if "equation-fallback" in class_set or "equation-preview" in class_set:
        return "equation"
    if "chemical-diagram" in class_set or "chem-diagram" in class_set:
        return "chemical-diagram"
    if "physics-chart" in class_set:
        return "chart"
    if "diagram-asset" in class_set or "diagram-preview" in class_set or "physics-diagram" in class_set:
        return "diagram"
    if "ole-preview" in class_set or "embedded-object" in class_set:
        if prog_id.strip() or source_or_alt_has_type_signal(joined):
            return infer_from_text_signal(joined)
        return "unknown-preview"

    if any(tok in joined for tok in ["chemdraw", "chemsketch", "chemwindow", "acd."]):
        return "chemical-diagram"
    if any(tok in joined for tok in ["chart", "graph"]):
        return "chart"
    if any(tok in joined for tok in ["visio", "diagram"]):
        return "diagram"
    if "equation" in joined or "mathtype" in joined or "dsmt" in joined:
        return "equation"
    if src.strip():
        return "generic-image"
    return "unknown-preview"


def source_or_alt_has_type_signal(joined: str) -> bool:
    return any(tok in joined for tok in ["equation", "mathtype", "dsmt", "visio", "diagram", "graph", "chart", "chemdraw", "chemsketch", "chemwindow", "acd."])


def infer_from_text_signal(joined: str) -> str:
    if any(tok in joined for tok in ["chemdraw", "chemsketch", "chemwindow", "acd."]):
        return "chemical-diagram"
    if any(tok in joined for tok in ["chart", "graph"]):
        return "chart"
    if any(tok in joined for tok in ["visio", "diagram"]):
        return "diagram"
    if "equation" in joined or "mathtype" in joined or "dsmt" in joined:
        return "equation"
    return "generic-image"


def normalize_classification(value: str) -> str:
    return value if value in CLASSIFICATION_KEYS else "unknown-preview"


def is_fallback_image(attrs: Dict[str, str], css_class: str) -> bool:
    if attrs.get("data-ole-kind"):
        return True
    class_set = {c.strip() for c in css_class.split() if c.strip()}
    return bool(class_set.intersection(FALLBACK_CLASSES))


def count_by_type(by_type: Dict[str, int], prog_id: str, source_ext: str) -> None:
    normalized_prog = prog_id.lower()
    if "equation.dsmt4" in normalized_prog:
        by_type["Equation.DSMT4"] += 1
    if "visio.drawing.15" in normalized_prog:
        by_type["Visio.Drawing.15"] += 1
    if "chemdraw.document.6.0" in normalized_prog:
        by_type["ChemDraw.Document.6.0"] += 1
    if "chemdraw_x64.document.6.0" in normalized_prog:
        by_type["ChemDraw_x64.Document.6.0"] += 1
    if "acd.chemsketch.20" in normalized_prog:
        by_type["ACD.ChemSketch.20"] += 1
    if "chemwindow.document" in normalized_prog:
        by_type["ChemWindow.Document"] += 1
    normalized_ext = source_ext.lower()
    if normalized_ext in {".emf", ".wmf"}:
        by_type[normalized_ext] += 1


def extract_table_whitespace_layout_metrics(html_text: str) -> Dict[str, int]:
    def count_empty_in_named_group(pattern: re.Pattern[str]) -> int:
        total = 0
        for match in pattern.finditer(html_text):
            total += len(EMPTY_PARAGRAPH_TAG_RE.findall(match.group("empties")))
        return total

    remaining_empty_paragraph_count = len(EMPTY_PARAGRAPH_TAG_RE.findall(html_text))
    remaining_table_adjacent_empty_paragraph_count = (
        count_empty_in_named_group(EMPTY_PARAGRAPH_CHAIN_BEFORE_DOCX_TABLE_RE)
        + count_empty_in_named_group(EMPTY_PARAGRAPH_CHAIN_AFTER_DOCX_TABLE_RE)
    )
    remaining_table_cell_empty_paragraph_count = (
        count_empty_in_named_group(EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_START_RE)
        + count_empty_in_named_group(EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_END_RE)
    )
    remaining_malformed_math_block_flow_count = 0
    for block in MATH_BLOCK_CAPTURE_RE.finditer(html_text):
        body = block.group("body")
        if "<math" in body and ("</span>" in body or 'class="math-inline' in body):
            remaining_malformed_math_block_flow_count += 1

    remaining_table_whitespace_layout_issues = (
        remaining_table_adjacent_empty_paragraph_count
        + remaining_table_cell_empty_paragraph_count
        + remaining_malformed_math_block_flow_count
    )
    return {
        "remaining_empty_paragraph_count": remaining_empty_paragraph_count,
        "remaining_table_adjacent_empty_paragraph_count": remaining_table_adjacent_empty_paragraph_count,
        "remaining_table_cell_empty_paragraph_count": remaining_table_cell_empty_paragraph_count,
        "remaining_malformed_math_block_flow_count": remaining_malformed_math_block_flow_count,
        "remaining_table_whitespace_layout_issues": remaining_table_whitespace_layout_issues,
    }


def _legacy_publish_verdict(publish_verdict: str) -> str:
    return "safe to publish" if publish_verdict == "safe_to_publish" else "still needs cleanup"


def evaluate_publish_gates(
    totals: Dict[str, Optional[int]],
    unresolved_object_count: int,
    output_mode: str,
) -> Dict[str, object]:
    mode = (output_mode or "publish").strip().lower()
    if mode not in OUTPUT_MODES:
        mode = "publish"

    findings: List[Dict[str, object]] = []

    def add_metric_finding(metric: str, severity: str, title: str, recommendation: str) -> None:
        value = int(totals.get(metric, 0) or 0)
        if value <= 0:
            return
        findings.append(
            {
                "severity": severity,
                "metric": metric,
                "value": value,
                "title": title,
                "recommendation": recommendation,
            }
        )

    if unresolved_object_count > 0:
        findings.append(
            {
                "severity": "blocker",
                "metric": "unresolved_objects",
                "value": unresolved_object_count,
                "title": "Unresolved objects remain in output",
                "recommendation": "Resolve or classify all unresolved object fallbacks before publishing.",
            }
        )

    add_metric_finding(
        "remaining_preview_images",
        "blocker",
        "Preview/fallback images remain",
        "Convert remaining equation/diagram previews or mark bundle blocked.",
    )
    add_metric_finding(
        "word_field_code_leakage_count",
        "blocker",
        "Word field-code leakage detected",
        "Strip leaked field code text from final publish HTML.",
    )
    add_metric_finding(
        "image_field_text_contamination_count",
        "blocker",
        "Word field remnants around image blocks detected",
        "Clean image-adjacent field code leakage before publishing.",
    )
    add_metric_finding(
        "unsupported_web_image_count",
        "blocker",
        "Unsupported web image formats still referenced",
        "Convert unsupported image formats to web-safe assets.",
    )
    add_metric_finding(
        "web_safe_asset_violation_count",
        "blocker",
        "Web-safe asset policy violations detected",
        "Remove/replace violating assets for publish output.",
    )
    add_metric_finding(
        "chemical_diagram_placeholder_count",
        "blocker",
        "Chemical diagram placeholders remain",
        "Render real diagram output or keep bundle blocked.",
    )
    add_metric_finding(
        "chemical_diagram_render_failed_count",
        "blocker",
        "Chemical diagram render failures remain",
        "Fix rendering failures for chemistry diagrams.",
    )
    add_metric_finding(
        "chemical_diagram_blank_image_count",
        "blocker",
        "Blank chemical diagram images detected",
        "Regenerate blank diagram assets before publishing.",
    )

    publish_leakage_severity = "blocker" if mode == "publish" else "info"
    add_metric_finding(
        "publish_debug_attr_leakage_count",
        publish_leakage_severity,
        "Debug attributes found in output HTML",
        "Keep debug attrs in internal mode only; strip them in publish mode.",
    )
    add_metric_finding(
        "publish_namespace_leakage_count",
        publish_leakage_severity,
        "Internal namespaces found in output HTML",
        "Keep internal namespaces in internal mode only; strip in publish mode.",
    )

    add_metric_finding(
        "remaining_text_corruption_count",
        "error",
        "Visible text corruption remains",
        "Apply deterministic text normalization for remaining corruption issues.",
    )
    add_metric_finding(
        "remaining_chemistry_inline_issues",
        "error",
        "Chemistry inline notation issues remain",
        "Normalize chemistry inline notation where output remains malformed.",
    )
    add_metric_finding(
        "remaining_chemistry_arrow_symbol_issues",
        "error",
        "Chemistry arrow/symbol issues remain",
        "Fix reaction arrow/symbol rendering in chemistry text context.",
    )
    add_metric_finding(
        "remaining_chemistry_unit_issues",
        "error",
        "Chemistry unit notation issues remain",
        "Normalize chemistry unit formatting (for example mol·L⁻¹, °C).",
    )
    add_metric_finding(
        "remaining_chemistry_glyph_issues",
        "error",
        "Chemistry glyph artifacts remain",
        "Normalize unreadable chemistry glyph artifacts in visible output.",
    )
    add_metric_finding(
        "remaining_physics_unit_issues",
        "error",
        "Physics unit formatting issues remain",
        "Normalize residual physics unit tokenization issues.",
    )
    add_metric_finding(
        "remaining_physics_text_corruption_issues",
        "error",
        "Physics text corruption issues remain",
        "Apply conservative physics text dictionary cleanup for residual corruption.",
    )
    add_metric_finding(
        "remaining_mixed_math_text_layout_issues",
        "error",
        "Mixed text+MathML layout issues remain",
        "Polish text/math boundary spacing and punctuation binding.",
    )
    add_metric_finding(
        "remaining_math_glyph_issues",
        "error",
        "Math glyph artifacts remain",
        "Normalize unreadable math glyph artifacts conservatively.",
    )
    add_metric_finding(
        "remaining_math_unreadable_glyph_issues",
        "error",
        "Unreadable math symbols remain",
        "Replace unreadable fallback symbols with intended readable output.",
    )
    add_metric_finding(
        "downs_reaction_notation_issue_count",
        "error",
        "Chemistry Downs reaction notation issues remain",
        "Correct residual Downs reaction/electron notation errors.",
    )

    add_metric_finding(
        "remaining_table_whitespace_layout_issues",
        "warning",
        "Table whitespace/layout residual issues remain",
        "Collapse empty paragraph noise and tighten table-adjacent spacing.",
    )
    add_metric_finding(
        "table_inline_image_too_small_count",
        "warning",
        "Table inline images remain too small",
        "Adjust table inline image caps to keep figures readable.",
    )
    add_metric_finding(
        "remaining_table_inline_image_too_small_count",
        "warning",
        "Remaining too-small table inline images detected",
        "Rebalance table-cell image sizing where figures are unreadable.",
    )
    add_metric_finding(
        "remaining_essay_question_figure_layout_issues",
        "warning",
        "Essay figure placement/layout residual issues remain",
        "Apply role-aware deterministic figure placement policy.",
    )
    add_metric_finding(
        "figure_in_table_too_small_count",
        "warning",
        "Figures in table layout are still too small",
        "Promote essential figures out of narrow side-cell layout where needed.",
    )
    add_metric_finding(
        "generic_inline_image_oversized_whitespace_count",
        "warning",
        "Inline images with oversized whitespace remain",
        "Apply safe trim for whitespace-heavy inline image assets.",
    )
    add_metric_finding(
        "generic_inline_image_bad_crop_count",
        "warning",
        "Suspicious inline image crops detected",
        "Review and correct suspicious crops while preserving content.",
    )
    add_metric_finding(
        "generic_inline_image_blank_count",
        "warning",
        "Blank generic inline images detected",
        "Suppress or replace blank generic inline image artifacts.",
    )
    add_metric_finding(
        "generic_gif_placeholder_count",
        "warning",
        "Placeholder-like GIF assets remain",
        "Replace placeholder GIFs with real web-safe assets.",
    )
    add_metric_finding(
        "chemical_diagram_oversized_display_count",
        "warning",
        "Oversized chemical diagram display cases remain",
        "Trim or rebalance chemistry diagram display sizing without cropping content.",
    )
    add_metric_finding(
        "remaining_nonessential_standalone_image_candidates",
        "warning",
        "Nonessential standalone image suppression candidates remain",
        "Review nonessential standalone context-image candidates for publish cleanup.",
    )

    severity_counts = Counter(item["severity"] for item in findings)
    summary = {severity: int(severity_counts.get(severity, 0)) for severity in PUBLISH_GATE_SEVERITIES}

    if summary["blocker"] > 0:
        publish_verdict = "blocked"
    elif summary["error"] > 0 or summary["warning"] > 0:
        publish_verdict = "needs_review"
    else:
        publish_verdict = "safe_to_publish"

    findings_sorted = sorted(
        findings,
        key=lambda item: (
            PUBLISH_GATE_SEVERITIES.index(str(item.get("severity", "info"))),
            str(item.get("metric", "")),
        ),
    )
    return {
        "publish_verdict": publish_verdict,
        "publish_verdict_legacy": _legacy_publish_verdict(publish_verdict),
        "publish_gate_summary": summary,
        "publish_gate_findings": findings_sorted,
    }


def audit(
    html_path: Path,
    asset_dir: Path,
    conversion_log: Optional[Path],
    subject: str,
    output_mode: str = "publish",
) -> Dict:
    normalized_output_mode = (output_mode or "publish").strip().lower()
    if normalized_output_mode not in OUTPUT_MODES:
        normalized_output_mode = "publish"
    html_text = html_path.read_text(encoding="utf-8", errors="ignore")
    lines = html_text.splitlines()
    table_inline_policy = extract_table_inline_image_policy(html_text)
    essay_layout_metrics = extract_essay_figure_layout_metrics(html_text)
    table_whitespace_metrics = extract_table_whitespace_layout_metrics(html_text)
    remaining_nonessential_standalone_image_candidates = count_remaining_nonessential_standalone_image_candidates(html_text)
    by_type = {key: 0 for key in TYPE_KEYS}
    unresolved_objects: List[UnresolvedObject] = []
    suspected_numeric_corruption: List[Dict[str, str]] = []
    per_exam: Dict[str, Dict[str, int]] = {}
    chemical_diagram_quality_cache: Dict[str, Dict[str, Optional[float]]] = {}
    chemical_diagram_svg_dimension_cache: Dict[str, Dict[str, Optional[float]]] = {}
    generic_image_quality_cache: Dict[str, Dict[str, Optional[float]]] = {}
    per_exam_blank_assets: Dict[str, set[str]] = {}
    per_exam_near_white_assets: Dict[str, set[str]] = {}
    per_exam_tiny_assets: Dict[str, set[str]] = {}
    per_exam_bad_crop_assets: Dict[str, set[str]] = {}
    per_exam_oversized_assets: Dict[str, set[str]] = {}
    per_exam_trimmed_assets: Dict[str, set[str]] = {}
    per_exam_generic_inline_assets: Dict[str, set[str]] = {}
    per_exam_generic_inline_trim_candidate_assets: Dict[str, set[str]] = {}
    per_exam_generic_inline_trim_applied_assets: Dict[str, set[str]] = {}
    per_exam_generic_inline_oversized_assets: Dict[str, set[str]] = {}
    per_exam_generic_inline_blank_assets: Dict[str, set[str]] = {}
    per_exam_generic_inline_near_white_assets: Dict[str, set[str]] = {}
    per_exam_generic_inline_bad_crop_assets: Dict[str, set[str]] = {}
    per_exam_generic_inline_svg_trim_applied_assets: Dict[str, set[str]] = {}
    per_exam_generic_inline_raster_trim_applied_assets: Dict[str, set[str]] = {}
    per_exam_table_inline_trimmed_assets: Dict[str, set[str]] = {}
    generic_emf_inline_assets: set[str] = set()
    generic_wmf_inline_assets: set[str] = set()
    generic_emf_converted_svg_assets: set[str] = set()
    generic_emf_converted_png_assets: set[str] = set()
    generic_gif_assets: set[str] = set()
    generic_gif_placeholder_assets: set[str] = set()
    generic_gif_blank_assets: set[str] = set()
    generic_inline_image_assets: set[str] = set()
    generic_inline_image_trim_candidate_assets: set[str] = set()
    generic_inline_image_trim_applied_assets: set[str] = set()
    generic_inline_image_oversized_whitespace_assets: set[str] = set()
    generic_inline_image_blank_assets: set[str] = set()
    generic_inline_image_near_white_assets: set[str] = set()
    generic_inline_image_bad_crop_assets: set[str] = set()
    generic_inline_image_svg_trim_applied_assets: set[str] = set()
    generic_inline_image_raster_trim_applied_assets: set[str] = set()
    table_inline_image_trimmed_assets: set[str] = set()
    unsupported_web_image_assets: set[str] = set()
    web_safe_asset_violation_assets: set[str] = set()
    web_asset_inventory: List[Dict[str, object]] = []
    web_asset_inventory_seen: set[tuple[str, str]] = set()

    def exam_bucket(exam_id: str) -> Dict[str, int]:
        if exam_id not in per_exam:
            per_exam[exam_id] = {
                "mathml_formulas": 0,
                "remaining_preview_count": 0,
                "remaining_text_corruption_count": 0,
                "remaining_chemistry_inline_issues": 0,
                "chemistry_inline_fixes": 0,
                "chemistry_arrow_symbol_fixes": 0,
                "chemistry_unit_fixes": 0,
                "chemistry_glyph_fix_count": 0,
                "remaining_chemistry_arrow_symbol_issues": 0,
                "remaining_chemistry_unit_issues": 0,
                "remaining_chemistry_glyph_issues": 0,
                "physics_unit_fix_count": 0,
                "physics_text_fix_count": 0,
                "remaining_physics_unit_issues": 0,
                "remaining_physics_text_corruption_issues": 0,
                "mixed_math_text_cleanup_count": 0,
                "remaining_mixed_math_text_layout_issues": 0,
                "math_glyph_cleanup_count": 0,
                "math_unreadable_glyph_fix_count": 0,
                "remaining_math_glyph_issues": 0,
                "remaining_math_unreadable_glyph_issues": 0,
                "table_inline_image_too_small_count": 0,
                "remaining_table_inline_image_too_small_count": 0,
                "table_inline_image_sizing_adjusted_count": 0,
                "essay_question_figure_relocated_count": 0,
                "essay_question_figure_centered_block_count": 0,
                "remaining_essay_question_figure_layout_issues": 0,
                "figure_in_table_too_small_count": 0,
                "downs_reaction_notation_issue_count": 0,
                "word_field_code_leakage_count": 0,
                "publish_debug_attr_leakage_count": 0,
                "publish_namespace_leakage_count": 0,
                "image_field_text_contamination_count": 0,
                "chemical_diagram_blank_image_count": 0,
                "chemical_diagram_near_white_image_count": 0,
                "chemical_diagram_tiny_image_count": 0,
                "chemical_diagram_bad_crop_count": 0,
                "chemical_diagram_oversized_display_count": 0,
                "chemical_diagram_placeholder_count": 0,
                "chemical_diagram_rendered_svg_count": 0,
                "chemical_diagram_rendered_png_count": 0,
                "chemical_diagram_render_failed_count": 0,
                "chemical_diagram_trim_applied_count": 0,
                "generic_inline_image_count": 0,
                "generic_inline_image_trim_candidate_count": 0,
                "generic_inline_image_trim_applied_count": 0,
                "generic_inline_image_oversized_whitespace_count": 0,
                "generic_inline_image_bad_crop_count": 0,
                "generic_inline_image_blank_count": 0,
                "generic_inline_image_near_white_count": 0,
                "generic_inline_image_svg_trim_applied_count": 0,
                "generic_inline_image_raster_trim_applied_count": 0,
                "unresolved_visio_placeholders": 0,
            }
        return per_exam[exam_id]

    def add_web_asset_inventory(
        src: str,
        exam_id: str,
        line_no: int,
        css_class: str,
        classification: str,
        ext: str,
        web_safe: bool,
        blank: bool,
        placeholder: bool,
        width: Optional[float],
        height: Optional[float],
        trim_candidate: bool = False,
        trim_applied: bool = False,
        trim_type: str = "",
    ) -> None:
        key = (src, classification)
        if key in web_asset_inventory_seen:
            return
        web_asset_inventory_seen.add(key)
        web_asset_inventory.append(
            {
                "source_path": src,
                "exam": exam_id,
                "location": f"{html_path}:{line_no}",
                "role_class": css_class,
                "classification": classification,
                "extension": ext,
                "web_safe_format": web_safe,
                "blank_or_placeholder": bool(blank or placeholder),
                "blank": bool(blank),
                "placeholder_like": bool(placeholder),
                "width": width,
                "height": height,
                "trim_candidate": bool(trim_candidate),
                "trim_applied": bool(trim_applied),
                "trim_type": trim_type or "",
            }
        )

    current_exam = "DE_UNKNOWN"
    table_depth = 0
    for line_no, line in enumerate(lines, start=1):
        current_exam = detect_exam(line, current_exam)
        bucket = exam_bucket(current_exam)

        math_count = len(MATH_OPEN_RE.findall(line))
        if math_count:
            bucket["mathml_formulas"] += math_count

        if subject == "chemistry":
            chem_fix_count = len(CHEM_FIXED_RE.findall(line))
            if chem_fix_count:
                bucket["chemistry_inline_fixes"] += chem_fix_count
            arrow_fix_count = len(CHEM_ARROW_FIXED_RE.findall(line))
            if arrow_fix_count:
                bucket["chemistry_arrow_symbol_fixes"] += arrow_fix_count
            unit_fix_count = len(CHEM_UNIT_FIXED_RE.findall(line))
            if unit_fix_count:
                bucket["chemistry_unit_fixes"] += unit_fix_count
            glyph_fix_count = arrow_fix_count + unit_fix_count
            if glyph_fix_count:
                bucket["chemistry_glyph_fix_count"] += glyph_fix_count

        visible_text = normalize_visible_text(line)
        word_field_hits = len(WORD_FIELD_LEAKAGE_RE.findall(visible_text))
        if word_field_hits:
            bucket["word_field_code_leakage_count"] += word_field_hits
            if "<img" in line.lower():
                bucket["image_field_text_contamination_count"] += word_field_hits
        publish_debug_attr_hits = len(PUBLISH_DEBUG_ATTR_RE.findall(line))
        if publish_debug_attr_hits:
            bucket["publish_debug_attr_leakage_count"] += publish_debug_attr_hits
        publish_namespace_hits = len(PUBLISH_NAMESPACE_LEAKAGE_RE.findall(line))
        if publish_namespace_hits:
            bucket["publish_namespace_leakage_count"] += publish_namespace_hits
        corruption_hits = count_matches(CORRUPTION_PATTERNS, visible_text)
        if corruption_hits:
            bucket["remaining_text_corruption_count"] += corruption_hits

        if subject == "physics":
            physics_unit_issue_hits = count_physics_unit_issues(visible_text)
            if physics_unit_issue_hits:
                bucket["remaining_physics_unit_issues"] += physics_unit_issue_hits
            physics_text_issue_hits = count_physics_text_corruption_issues(visible_text)
            if physics_text_issue_hits:
                bucket["remaining_physics_text_corruption_issues"] += physics_text_issue_hits
            mixed_math_layout_hits = count_mixed_math_text_layout_issues(line)
            if mixed_math_layout_hits:
                bucket["remaining_mixed_math_text_layout_issues"] += mixed_math_layout_hits

        if subject == "math":
            math_glyph_issue_hits = count_math_glyph_issues(visible_text, line)
            if math_glyph_issue_hits:
                bucket["remaining_math_glyph_issues"] += math_glyph_issue_hits
                bucket["remaining_math_unreadable_glyph_issues"] += math_glyph_issue_hits

        if subject == "chemistry":
            downs_issue_hits = len(DOWNS_REACTION_ISSUE_RE.findall(line))
            if downs_issue_hits:
                bucket["downs_reaction_notation_issue_count"] += downs_issue_hits
            chem_issue_hits = count_chem_inline_issues(visible_text)
            if chem_issue_hits:
                bucket["remaining_chemistry_inline_issues"] += chem_issue_hits
            chem_arrow_issue_hits = count_chem_arrow_symbol_issues(visible_text)
            if chem_arrow_issue_hits:
                bucket["remaining_chemistry_arrow_symbol_issues"] += chem_arrow_issue_hits
            chem_unit_issue_hits = count_chem_unit_issues(visible_text)
            if chem_unit_issue_hits:
                bucket["remaining_chemistry_unit_issues"] += chem_unit_issue_hits
            chem_glyph_issue_hits = count_chem_glyph_issues(visible_text)
            if chem_glyph_issue_hits:
                bucket["remaining_chemistry_glyph_issues"] += chem_glyph_issue_hits
        suspected_numeric_corruption.extend(
            find_suspected_numeric_corruption(visible_text, current_exam, f"{html_path}:{line_no}")
        )

        for img_match in IMG_TAG_RE.finditer(line):
            tag = img_match.group(0)
            attrs = parse_attrs(tag)
            src = attrs.get("src", "")
            alt = attrs.get("alt", "")
            css_class = attrs.get("class", "")
            prog_id = attrs.get("data-ole-progid", "")
            source_ext = attrs.get("data-source-ext", "")
            fallback_type = attrs.get("data-fallback-type", "")
            render_attempted = attrs.get("data-render-attempted", "").lower() == "true"
            render_source_used = attrs.get("data-render-source-used", "")
            render_output_type = attrs.get("data-render-output-type", "")
            render_success = attrs.get("data-render-success", "").lower() == "true"
            render_source_exts = attrs.get("data-render-source-exts", "")
            render_source_assets = attrs.get("data-render-source-assets", "")
            chem_trim_applied = attrs.get("data-chem-trim-applied", "").lower() == "true"
            trim_candidate = attrs.get("data-trim-candidate", "").lower() == "true"
            trim_applied = attrs.get("data-trim-applied", "").lower() == "true"
            trim_type = attrs.get("data-trim-type", "").strip().lower()
            classification = normalize_classification(classify_occurrence(attrs, css_class, alt, src, prog_id))
            src_lower = src.lower()
            src_ext = Path(src_lower).suffix
            web_safe = src_ext in WEB_SAFE_IMAGE_EXTENSIONS if src_ext else True
            class_set = {c.strip() for c in css_class.split() if c.strip()}
            is_generic_inline = "inline-image" in class_set and "data-ole-kind" not in attrs
            inside_table = table_depth > 0 or is_inside_table_context(line, img_match.start())
            source_ext_lower = source_ext.lower()

            if "essay-figure-image" in class_set:
                bucket["essay_question_figure_relocated_count"] += 1
            if "essential-figure-image" in class_set:
                bucket["essay_question_figure_centered_block_count"] += 1

            asset_path: Optional[Path] = None
            if src:
                src_relative = src
                if asset_dir.name and src.startswith(asset_dir.name + "/"):
                    src_relative = src[len(asset_dir.name) + 1 :]
                asset_path = asset_dir / src_relative

            inventory_blank = False
            inventory_placeholder = False
            inventory_width: Optional[float] = None
            inventory_height: Optional[float] = None

            if is_generic_inline and src:
                generic_inline_image_assets.add(src)
                per_exam_generic_inline_assets.setdefault(current_exam, set()).add(src)
                if inside_table and "inline-image-trimmed" in class_set:
                    table_inline_image_trimmed_assets.add(src)
                    per_exam_table_inline_trimmed_assets.setdefault(current_exam, set()).add(src)
                if trim_candidate:
                    generic_inline_image_trim_candidate_assets.add(src)
                    per_exam_generic_inline_trim_candidate_assets.setdefault(current_exam, set()).add(src)
                if trim_applied:
                    generic_inline_image_trim_applied_assets.add(src)
                    per_exam_generic_inline_trim_applied_assets.setdefault(current_exam, set()).add(src)
                if trim_candidate and not trim_applied:
                    generic_inline_image_oversized_whitespace_assets.add(src)
                    per_exam_generic_inline_oversized_assets.setdefault(current_exam, set()).add(src)
                if trim_applied and trim_type == "svg-viewbox":
                    generic_inline_image_svg_trim_applied_assets.add(src)
                    per_exam_generic_inline_svg_trim_applied_assets.setdefault(current_exam, set()).add(src)
                if trim_applied and trim_type == "raster-bbox":
                    generic_inline_image_raster_trim_applied_assets.add(src)
                    per_exam_generic_inline_raster_trim_applied_assets.setdefault(current_exam, set()).add(src)

            if is_generic_inline and src_ext == ".emf":
                generic_emf_inline_assets.add(src)
            if is_generic_inline and src_ext == ".wmf":
                generic_wmf_inline_assets.add(src)
            if is_generic_inline and source_ext_lower == ".emf" and src_ext == ".svg":
                generic_emf_converted_svg_assets.add(src)
            if is_generic_inline and source_ext_lower == ".emf" and src_ext == ".png":
                generic_emf_converted_png_assets.add(src)

            if is_generic_inline and src_ext == ".gif" and src:
                generic_gif_assets.add(src)
                if src not in generic_image_quality_cache and asset_path is not None:
                    generic_image_quality_cache[src] = analyze_image_quality(asset_path)
                quality = generic_image_quality_cache.get(src, {})
                inventory_width = quality.get("width")
                inventory_height = quality.get("height")
                gif_info = analyze_gif_placeholder(asset_path, quality) if asset_path is not None else {
                    "placeholder": False,
                    "blank": False,
                    "tiny_pixel": False,
                    "size_tiny": False,
                }
                inventory_blank = bool(gif_info.get("blank"))
                inventory_placeholder = bool(gif_info.get("placeholder"))
                if inventory_blank:
                    generic_gif_blank_assets.add(src)
                if inventory_placeholder:
                    generic_gif_placeholder_assets.add(src)

            if is_generic_inline and src_ext in {".png", ".jpg", ".jpeg", ".gif"} and src:
                if src not in generic_image_quality_cache and asset_path is not None:
                    generic_image_quality_cache[src] = analyze_image_quality(asset_path)
                quality = generic_image_quality_cache.get(src, {})
                if inventory_width is None:
                    inventory_width = quality.get("width")
                if inventory_height is None:
                    inventory_height = quality.get("height")
                if quality.get("blank"):
                    generic_inline_image_blank_assets.add(src)
                    per_exam_generic_inline_blank_assets.setdefault(current_exam, set()).add(src)
                if quality.get("near_white"):
                    generic_inline_image_near_white_assets.add(src)
                    per_exam_generic_inline_near_white_assets.setdefault(current_exam, set()).add(src)
                width_px = float(quality.get("width") or 0.0)
                height_px = float(quality.get("height") or 0.0)
                ratio = max((width_px / height_px) if height_px else 9999.0, (height_px / width_px) if width_px else 9999.0)
                # Ignore deliberately long strip-like assets (for example wide separators),
                # and only flag near-thumbnail extreme-aspect crops as suspicious.
                generic_bad_crop = (
                    ratio >= 16.0
                    and min(width_px, height_px) <= 48.0
                    and max(width_px, height_px) <= 320.0
                )
                if trim_applied and generic_bad_crop:
                    generic_inline_image_bad_crop_assets.add(src)
                    per_exam_generic_inline_bad_crop_assets.setdefault(current_exam, set()).add(src)

            if src_ext and not web_safe:
                unsupported_web_image_assets.add(src)
            if src_ext in {".emf", ".wmf"} or inventory_placeholder:
                web_safe_asset_violation_assets.add(src)

            if src_ext in {".emf", ".wmf", ".gif"}:
                add_web_asset_inventory(
                    src=src,
                    exam_id=current_exam,
                    line_no=line_no,
                    css_class=css_class,
                    classification=classification,
                    ext=src_ext,
                    web_safe=web_safe,
                    blank=inventory_blank,
                    placeholder=inventory_placeholder,
                    width=inventory_width,
                    height=inventory_height,
                    trim_candidate=trim_candidate,
                    trim_applied=trim_applied,
                    trim_type=trim_type,
                )

            if not is_fallback_image(attrs, css_class):
                continue

            if classification == "chemical-diagram" and src:
                if src not in chemical_diagram_quality_cache:
                    src_relative = src
                    if asset_dir.name and src.startswith(asset_dir.name + "/"):
                        src_relative = src[len(asset_dir.name) + 1:]
                    image_path = asset_dir / src_relative
                    chemical_diagram_quality_cache[src] = analyze_image_quality(image_path)
                src_relative = src
                if asset_dir.name and src.startswith(asset_dir.name + "/"):
                    src_relative = src[len(asset_dir.name) + 1:]
                image_path = asset_dir / src_relative
                quality = chemical_diagram_quality_cache[src]
                inside_table = inside_table or is_inside_table_context(line, img_match.start())
                display_cap_px = CHEM_DIAGRAM_DISPLAY_TABLE_MAX_PX if inside_table else CHEM_DIAGRAM_DISPLAY_MAX_PX
                display_cap_mm = CHEM_DIAGRAM_DISPLAY_TABLE_MAX_MM if inside_table else CHEM_DIAGRAM_DISPLAY_MAX_MM
                if quality.get("blank"):
                    per_exam_blank_assets.setdefault(current_exam, set()).add(src)
                if quality.get("near_white"):
                    per_exam_near_white_assets.setdefault(current_exam, set()).add(src)
                if quality.get("tiny"):
                    per_exam_tiny_assets.setdefault(current_exam, set()).add(src)
                if quality.get("bad_crop"):
                    per_exam_bad_crop_assets.setdefault(current_exam, set()).add(src)
                if render_output_type == "png":
                    width_px = float(quality.get("width") or 0.0)
                    height_px = float(quality.get("height") or 0.0)
                    if width_px > 0 and height_px > 0:
                        scale = min(1.0, display_cap_px / width_px)
                        display_width_px = width_px * scale
                        display_height_px = height_px * scale
                        if (
                            display_width_px > OVERSIZED_PNG_WIDTH_THRESHOLD
                            or display_height_px > OVERSIZED_PNG_HEIGHT_THRESHOLD
                        ):
                            per_exam_oversized_assets.setdefault(current_exam, set()).add(src)
                if render_output_type == "svg":
                    if src not in chemical_diagram_svg_dimension_cache:
                        chemical_diagram_svg_dimension_cache[src] = analyze_svg_dimensions(image_path)
                    svg_dims = chemical_diagram_svg_dimension_cache[src]
                    width_mm = float(svg_dims.get("width_mm") or 0.0)
                    height_mm = float(svg_dims.get("height_mm") or 0.0)
                    if width_mm > 0 and height_mm > 0:
                        scale = min(1.0, display_cap_mm / width_mm)
                        display_width_mm = width_mm * scale
                        display_height_mm = height_mm * scale
                        if (
                            display_width_mm > OVERSIZED_SVG_WIDTH_MM_THRESHOLD
                            or display_height_mm > OVERSIZED_SVG_HEIGHT_MM_THRESHOLD
                        ):
                            per_exam_oversized_assets.setdefault(current_exam, set()).add(src)
                if render_success and render_output_type == "svg":
                    bucket["chemical_diagram_rendered_svg_count"] += 1
                if render_success and render_output_type == "png":
                    bucket["chemical_diagram_rendered_png_count"] += 1
                if not render_success and render_attempted:
                    bucket["chemical_diagram_render_failed_count"] += 1
                if chem_trim_applied:
                    per_exam_trimmed_assets.setdefault(current_exam, set()).add(src)

            rendered_non_equation_success = (
                classification in {"diagram", "chart", "chemical-diagram", "generic-image"}
                and render_success
                and render_output_type in {"svg", "png", "gif", "jpg", "jpeg", "webp"}
            )
            if rendered_non_equation_success:
                continue

            bucket["remaining_preview_count"] += 1
            count_by_type(by_type, prog_id, source_ext)
            unresolved_objects.append(
                UnresolvedObject(
                    scope="html-image",
                    location=f"{html_path}:{line_no}",
                    exam=current_exam,
                    source_asset=src,
                    classification=classification,
                    fallback_type=fallback_type or "rendered-image",
                    prog_id=prog_id,
                    source_ext=source_ext,
                    alt=alt,
                    render_attempted=render_attempted,
                    render_source_used=render_source_used,
                    render_output_type=render_output_type or "unknown",
                    render_success=render_success,
                    render_source_exts=render_source_exts,
                    render_source_assets=render_source_assets,
                )
            )

        for match in UNSUPPORTED_SPAN_TAG_RE.finditer(line):
            tag = match.group(1)
            attrs = parse_attrs(tag)
            title = html.unescape(attrs.get("title", ""))
            label = html.unescape(match.group(2))
            joined = f"{title} {label}"
            prog_id = attrs.get("data-ole-progid", "")
            if not prog_id:
                for key in TYPE_KEYS:
                    if key.startswith("."):
                        continue
                    if key in joined:
                        prog_id = key
                        break
            classification = normalize_classification(classify_occurrence(attrs, "", label, "", prog_id))
            render_attempted = attrs.get("data-render-attempted", "").lower() == "true"
            render_source_used = attrs.get("data-render-source-used", "")
            render_output_type = attrs.get("data-render-output-type", "placeholder")
            render_success = attrs.get("data-render-success", "").lower() == "true"
            render_source_exts = attrs.get("data-render-source-exts", "")
            render_source_assets = attrs.get("data-render-source-assets", "")
            source_asset = render_source_assets or ""
            fallback_type = attrs.get("data-fallback-type", "unsupported-placeholder")
            if "Visio.Drawing.15" in joined:
                bucket["unresolved_visio_placeholders"] += 1
                by_type["Visio.Drawing.15"] += 1
            if classification == "chemical-diagram":
                bucket["chemical_diagram_placeholder_count"] += 1
                bucket["chemical_diagram_render_failed_count"] += 1
            if fallback_type in {"unsupported-inline-metafile", "unsupported-web-image-inline", "placeholder-gif-inline-image"}:
                src_ext = Path(source_asset.lower()).suffix if source_asset else ""
                web_safe = src_ext in WEB_SAFE_IMAGE_EXTENSIONS if src_ext else False
                placeholder_like = fallback_type == "placeholder-gif-inline-image"
                blank = False
                width = None
                height = None
                if src_ext == ".gif" and source_asset:
                    src_relative = source_asset
                    if asset_dir.name and source_asset.startswith(asset_dir.name + "/"):
                        src_relative = source_asset[len(asset_dir.name) + 1 :]
                    image_path = asset_dir / src_relative
                    quality = analyze_image_quality(image_path)
                    width = quality.get("width")
                    height = quality.get("height")
                    blank = bool(quality.get("blank"))
                    if blank:
                        generic_gif_blank_assets.add(source_asset)
                    if placeholder_like:
                        generic_gif_placeholder_assets.add(source_asset)
                    generic_gif_assets.add(source_asset)
                if src_ext == ".emf":
                    generic_emf_inline_assets.add(source_asset)
                if src_ext == ".wmf":
                    generic_wmf_inline_assets.add(source_asset)
                if not web_safe and source_asset:
                    unsupported_web_image_assets.add(source_asset)
                if source_asset:
                    web_safe_asset_violation_assets.add(source_asset)
                    add_web_asset_inventory(
                        src=source_asset,
                        exam_id=current_exam,
                        line_no=line_no,
                        css_class="inline-image",
                        classification=classification,
                        ext=src_ext,
                        web_safe=web_safe,
                        blank=blank,
                        placeholder=placeholder_like,
                        width=width,
                        height=height,
                    )
            unresolved_objects.append(
                UnresolvedObject(
                    scope="html-placeholder",
                    location=f"{html_path}:{line_no}",
                    exam=current_exam,
                    source_asset=source_asset,
                    classification=classification,
                    fallback_type=fallback_type,
                    prog_id=prog_id,
                    source_ext="",
                    alt=title,
                    render_attempted=render_attempted,
                    render_source_used=render_source_used,
                    render_output_type=render_output_type,
                    render_success=render_success,
                    render_source_exts=render_source_exts,
                    render_source_assets=render_source_assets,
                )
            )

        table_depth += len(re.findall(r"<table\b", line, re.IGNORECASE))
        table_depth -= len(re.findall(r"</table>", line, re.IGNORECASE))
        if table_depth < 0:
            table_depth = 0

    for exam_id, bucket in per_exam.items():
        bucket["chemical_diagram_blank_image_count"] = len(per_exam_blank_assets.get(exam_id, set()))
        bucket["chemical_diagram_near_white_image_count"] = len(per_exam_near_white_assets.get(exam_id, set()))
        bucket["chemical_diagram_tiny_image_count"] = len(per_exam_tiny_assets.get(exam_id, set()))
        bucket["chemical_diagram_bad_crop_count"] = len(per_exam_bad_crop_assets.get(exam_id, set()))
        bucket["chemical_diagram_oversized_display_count"] = len(per_exam_oversized_assets.get(exam_id, set()))
        bucket["chemical_diagram_trim_applied_count"] = len(per_exam_trimmed_assets.get(exam_id, set()))
        bucket["generic_inline_image_count"] = len(per_exam_generic_inline_assets.get(exam_id, set()))
        bucket["generic_inline_image_trim_candidate_count"] = len(per_exam_generic_inline_trim_candidate_assets.get(exam_id, set()))
        bucket["generic_inline_image_trim_applied_count"] = len(per_exam_generic_inline_trim_applied_assets.get(exam_id, set()))
        bucket["generic_inline_image_oversized_whitespace_count"] = len(per_exam_generic_inline_oversized_assets.get(exam_id, set()))
        bucket["generic_inline_image_bad_crop_count"] = len(per_exam_generic_inline_bad_crop_assets.get(exam_id, set()))
        bucket["generic_inline_image_blank_count"] = len(per_exam_generic_inline_blank_assets.get(exam_id, set()))
        bucket["generic_inline_image_near_white_count"] = len(per_exam_generic_inline_near_white_assets.get(exam_id, set()))
        bucket["generic_inline_image_svg_trim_applied_count"] = len(per_exam_generic_inline_svg_trim_applied_assets.get(exam_id, set()))
        bucket["generic_inline_image_raster_trim_applied_count"] = len(per_exam_generic_inline_raster_trim_applied_assets.get(exam_id, set()))
        table_trimmed_assets = per_exam_table_inline_trimmed_assets.get(exam_id, set())
        if table_inline_policy.get("sizing_adjusted"):
            bucket["table_inline_image_sizing_adjusted_count"] = len(table_trimmed_assets)
            bucket["table_inline_image_too_small_count"] = 0
        else:
            bucket["table_inline_image_sizing_adjusted_count"] = 0
            bucket["table_inline_image_too_small_count"] = len(table_trimmed_assets)
        bucket["remaining_table_inline_image_too_small_count"] = bucket["table_inline_image_too_small_count"]
        bucket["remaining_math_unreadable_glyph_issues"] = bucket["remaining_math_glyph_issues"]

    chemical_diagram_blank_image_count = sum(
        1 for quality in chemical_diagram_quality_cache.values() if quality.get("blank")
    )
    chemical_diagram_near_white_image_count = sum(
        1 for quality in chemical_diagram_quality_cache.values() if quality.get("near_white")
    )
    chemical_diagram_tiny_image_count = sum(
        1 for quality in chemical_diagram_quality_cache.values() if quality.get("tiny")
    )
    chemical_diagram_bad_crop_count = sum(
        1 for quality in chemical_diagram_quality_cache.values() if quality.get("bad_crop")
    )
    chemical_diagram_oversized_display_count = len(
        {asset for assets in per_exam_oversized_assets.values() for asset in assets}
    )
    chemical_diagram_trim_applied_count = len(
        {asset for assets in per_exam_trimmed_assets.values() for asset in assets}
    )

    conversion_metrics = parse_conversion_log(conversion_log)

    unique_unresolved_objects: List[UnresolvedObject] = []
    unresolved_seen: Set[Tuple[str, str, str, str, str, str, str, str, str, bool]] = set()
    for obj in unresolved_objects:
        dedup_key = (
            obj.scope,
            obj.exam,
            obj.classification,
            obj.fallback_type,
            obj.prog_id,
            obj.source_ext,
            obj.source_asset,
            obj.render_source_used,
            obj.render_output_type,
            obj.render_success,
        )
        if dedup_key in unresolved_seen:
            continue
        unresolved_seen.add(dedup_key)
        unique_unresolved_objects.append(obj)

    totals = {
        "mathml_formulas": sum(v["mathml_formulas"] for v in per_exam.values()),
        "remaining_preview_images": sum(v["remaining_preview_count"] for v in per_exam.values()),
        "remaining_text_corruption_count": sum(v["remaining_text_corruption_count"] for v in per_exam.values()),
        "remaining_chemistry_inline_issues": sum(v["remaining_chemistry_inline_issues"] for v in per_exam.values()),
        "chemistry_inline_fixes": sum(v["chemistry_inline_fixes"] for v in per_exam.values()),
        "chemistry_arrow_symbol_fixes": sum(v["chemistry_arrow_symbol_fixes"] for v in per_exam.values()),
        "chemistry_unit_fixes": sum(v["chemistry_unit_fixes"] for v in per_exam.values()),
        "chemistry_glyph_fix_count": sum(v["chemistry_glyph_fix_count"] for v in per_exam.values()),
        "remaining_chemistry_arrow_symbol_issues": sum(v["remaining_chemistry_arrow_symbol_issues"] for v in per_exam.values()),
        "remaining_chemistry_unit_issues": sum(v["remaining_chemistry_unit_issues"] for v in per_exam.values()),
        "remaining_chemistry_glyph_issues": sum(v["remaining_chemistry_glyph_issues"] for v in per_exam.values()),
        "remaining_physics_unit_issues": sum(v["remaining_physics_unit_issues"] for v in per_exam.values()),
        "remaining_physics_text_corruption_issues": sum(v["remaining_physics_text_corruption_issues"] for v in per_exam.values()),
        "remaining_mixed_math_text_layout_issues": sum(v["remaining_mixed_math_text_layout_issues"] for v in per_exam.values()),
        "remaining_math_glyph_issues": sum(v["remaining_math_glyph_issues"] for v in per_exam.values()),
        "remaining_math_unreadable_glyph_issues": sum(v["remaining_math_unreadable_glyph_issues"] for v in per_exam.values()),
        "table_inline_image_too_small_count": sum(v["table_inline_image_too_small_count"] for v in per_exam.values()),
        "remaining_table_inline_image_too_small_count": sum(v["remaining_table_inline_image_too_small_count"] for v in per_exam.values()),
        "table_inline_image_sizing_adjusted_count": sum(
            v["table_inline_image_sizing_adjusted_count"] for v in per_exam.values()
        ),
        "essay_question_figure_relocated_count": essay_layout_metrics["essay_question_figure_relocated_count"],
        "essay_question_figure_centered_block_count": essay_layout_metrics["essay_question_figure_centered_block_count"],
        "remaining_essay_question_figure_layout_issues": essay_layout_metrics["remaining_essay_question_figure_layout_issues"],
        "figure_in_table_too_small_count": essay_layout_metrics["figure_in_table_too_small_count"],
        "downs_reaction_notation_issue_count": sum(v["downs_reaction_notation_issue_count"] for v in per_exam.values()),
        "word_field_code_leakage_count": sum(v["word_field_code_leakage_count"] for v in per_exam.values()),
        "publish_debug_attr_leakage_count": sum(v["publish_debug_attr_leakage_count"] for v in per_exam.values()),
        "publish_namespace_leakage_count": sum(v["publish_namespace_leakage_count"] for v in per_exam.values()),
        "image_field_text_contamination_count": sum(v["image_field_text_contamination_count"] for v in per_exam.values()),
        "unresolved_visio_previews": conversion_metrics["unresolved_visio_previews"]
        if conversion_metrics["unresolved_visio_previews"] is not None
        else sum(v["unresolved_visio_placeholders"] for v in per_exam.values()),
        "normalized_text_fixes_applied": conversion_metrics["normalized_text_fixes_applied"],
        "ole_preview_images": conversion_metrics["ole_preview_images"],
        "emf_wmf_previews": conversion_metrics["emf_wmf_previews"],
        "rasterized_metafile_previews": conversion_metrics["rasterized_metafile_previews"],
        "rasterized_metafile_cache_hits": conversion_metrics["rasterized_metafile_cache_hits"],
        "sidecar_mathml_equations": conversion_metrics["sidecar_mathml_equations"],
        "omml_equations": conversion_metrics["omml_equations"],
        "chemistry_inline_fixes_applied": conversion_metrics["chemistry_inline_fixes_applied"],
        "chemistry_arrow_symbol_fixes_applied": conversion_metrics["chemistry_arrow_symbol_fixes_applied"],
        "chemistry_unit_fixes_applied": conversion_metrics["chemistry_unit_fixes_applied"],
        "physics_unit_fix_count": conversion_metrics["physics_unit_fixes_applied"] or 0,
        "physics_text_fix_count": conversion_metrics["physics_text_fixes_applied"] or 0,
        "mixed_math_text_cleanup_count": conversion_metrics["mixed_math_text_cleanup_fixes_applied"] or 0,
        "math_glyph_cleanup_count": conversion_metrics["math_glyph_cleanup_fixes_applied"] or 0,
        "math_unreadable_glyph_fix_count": conversion_metrics["math_glyph_cleanup_fixes_applied"] or 0,
        "empty_paragraph_removed_count": conversion_metrics["empty_paragraph_removed_count"] or 0,
        "table_adjacent_empty_paragraph_cleanup_count": conversion_metrics["table_adjacent_empty_paragraph_cleanup_count"] or 0,
        "table_cell_empty_paragraph_removed_count": conversion_metrics["table_cell_empty_paragraph_removed_count"] or 0,
        "math_block_flow_cleanup_count": conversion_metrics["math_block_flow_cleanup_count"] or 0,
        "suppressed_blank_standalone_image_count": conversion_metrics["suppressed_blank_standalone_image_count"] or 0,
        "suppressed_nonessential_standalone_image_count": conversion_metrics["suppressed_nonessential_standalone_image_count"] or 0,
        "restored_context_image_count": conversion_metrics["restored_context_image_count"] or 0,
        "remaining_nonessential_standalone_image_candidates": remaining_nonessential_standalone_image_candidates,
        "remaining_empty_paragraph_count": table_whitespace_metrics["remaining_empty_paragraph_count"],
        "remaining_table_adjacent_empty_paragraph_count": table_whitespace_metrics["remaining_table_adjacent_empty_paragraph_count"],
        "remaining_table_cell_empty_paragraph_count": table_whitespace_metrics["remaining_table_cell_empty_paragraph_count"],
        "remaining_malformed_math_block_flow_count": table_whitespace_metrics["remaining_malformed_math_block_flow_count"],
        "remaining_table_whitespace_layout_issues": table_whitespace_metrics["remaining_table_whitespace_layout_issues"],
        "chemical_diagram_blank_image_count": chemical_diagram_blank_image_count,
        "chemical_diagram_near_white_image_count": chemical_diagram_near_white_image_count,
        "chemical_diagram_tiny_image_count": chemical_diagram_tiny_image_count,
        "chemical_diagram_bad_crop_count": chemical_diagram_bad_crop_count,
        "chemical_diagram_oversized_display_count": chemical_diagram_oversized_display_count,
        "chemical_diagram_placeholder_count": sum(v["chemical_diagram_placeholder_count"] for v in per_exam.values()),
        "chemical_diagram_rendered_svg_count": sum(v["chemical_diagram_rendered_svg_count"] for v in per_exam.values()),
        "chemical_diagram_rendered_png_count": sum(v["chemical_diagram_rendered_png_count"] for v in per_exam.values()),
        "chemical_diagram_render_failed_count": sum(v["chemical_diagram_render_failed_count"] for v in per_exam.values()),
        "chemical_diagram_trim_applied_count": chemical_diagram_trim_applied_count,
        "generic_emf_inline_count": len(generic_emf_inline_assets),
        "generic_wmf_inline_count": len(generic_wmf_inline_assets),
        "generic_emf_converted_svg_count": len(generic_emf_converted_svg_assets),
        "generic_emf_converted_png_count": len(generic_emf_converted_png_assets),
        "generic_gif_count": len(generic_gif_assets),
        "generic_gif_placeholder_count": len(generic_gif_placeholder_assets),
        "generic_gif_blank_count": len(generic_gif_blank_assets),
        "generic_inline_image_count": len(generic_inline_image_assets),
        "generic_inline_image_trim_candidate_count": len(generic_inline_image_trim_candidate_assets),
        "generic_inline_image_trim_applied_count": len(generic_inline_image_trim_applied_assets),
        "generic_inline_image_oversized_whitespace_count": len(generic_inline_image_oversized_whitespace_assets),
        "generic_inline_image_bad_crop_count": len(generic_inline_image_bad_crop_assets),
        "generic_inline_image_blank_count": len(generic_inline_image_blank_assets),
        "generic_inline_image_near_white_count": len(generic_inline_image_near_white_assets),
        "generic_inline_image_svg_trim_applied_count": len(generic_inline_image_svg_trim_applied_assets),
        "generic_inline_image_raster_trim_applied_count": len(generic_inline_image_raster_trim_applied_assets),
        "unsupported_web_image_count": len(unsupported_web_image_assets),
        "web_safe_asset_violation_count": len(web_safe_asset_violation_assets),
    }
    chemistry_arrow_fixed_applied = conversion_metrics["chemistry_arrow_symbol_fixes_applied"]
    chemistry_unit_fixed_applied = conversion_metrics["chemistry_unit_fixes_applied"]
    if chemistry_arrow_fixed_applied is not None or chemistry_unit_fixed_applied is not None:
        totals["chemistry_glyph_fix_count"] = (chemistry_arrow_fixed_applied or 0) + (chemistry_unit_fixed_applied or 0)
    totals["core_promotion_candidate_count"] = 0
    totals["total_mathml_formulas"] = totals["mathml_formulas"]
    totals["total_previews"] = totals["remaining_preview_images"]
    totals["equation_dsmt4_preview_count"] = by_type["Equation.DSMT4"]
    totals["chemdraw_preview_count"] = by_type["ChemDraw.Document.6.0"] + by_type["ChemDraw_x64.Document.6.0"]
    totals["chemdraw_x64_preview_count"] = by_type["ChemDraw_x64.Document.6.0"]
    totals["chemsketch_preview_count"] = by_type["ACD.ChemSketch.20"]
    totals["chemwindow_preview_count"] = by_type["ChemWindow.Document"]
    totals["emf_count"] = by_type[".emf"]
    totals["wmf_count"] = by_type[".wmf"]
    totals["chemistry_inline_fix_count"] = totals["chemistry_inline_fixes"]
    totals["chemistry_arrow_symbol_fix_count"] = totals["chemistry_arrow_symbol_fixes"]
    totals["chemistry_unit_fix_count"] = totals["chemistry_unit_fixes"]
    totals["math_unreadable_glyph_fix_count"] = totals["math_glyph_cleanup_count"]
    totals["remaining_math_unreadable_glyph_issues"] = totals["remaining_math_glyph_issues"]
    totals["remaining_table_inline_image_too_small_count"] = totals["table_inline_image_too_small_count"]
    totals["blank_image_count"] = totals["chemical_diagram_blank_image_count"]
    totals["near_white_image_count"] = totals["chemical_diagram_near_white_image_count"]
    totals["tiny_image_count"] = totals["chemical_diagram_tiny_image_count"]
    totals["suspicious_crop_count"] = totals["chemical_diagram_bad_crop_count"]

    report = {
        "schema_version": QA_SCHEMA_VERSION,
        "output_mode": normalized_output_mode,
        "subject": subject,
        "total_mathml_formulas": totals["total_mathml_formulas"],
        "total_previews": totals["total_previews"],
        "equation_dsmt4_preview_count": totals["equation_dsmt4_preview_count"],
        "chemdraw_preview_count": totals["chemdraw_preview_count"],
        "chemdraw_x64_preview_count": totals["chemdraw_x64_preview_count"],
        "chemsketch_preview_count": totals["chemsketch_preview_count"],
        "chemwindow_preview_count": totals["chemwindow_preview_count"],
        "emf_count": totals["emf_count"],
        "wmf_count": totals["wmf_count"],
        "chemistry_inline_fix_count": totals["chemistry_inline_fix_count"],
        "chemistry_arrow_symbol_fix_count": totals["chemistry_arrow_symbol_fix_count"],
        "chemistry_unit_fix_count": totals["chemistry_unit_fix_count"],
        "chemistry_glyph_fix_count": totals["chemistry_glyph_fix_count"],
        "remaining_chemistry_arrow_symbol_issues": totals["remaining_chemistry_arrow_symbol_issues"],
        "remaining_chemistry_unit_issues": totals["remaining_chemistry_unit_issues"],
        "remaining_chemistry_glyph_issues": totals["remaining_chemistry_glyph_issues"],
        "core_promotion_candidate_count": totals["core_promotion_candidate_count"],
        "physics_unit_fix_count": totals["physics_unit_fix_count"],
        "physics_text_fix_count": totals["physics_text_fix_count"],
        "remaining_physics_unit_issues": totals["remaining_physics_unit_issues"],
        "remaining_physics_text_corruption_issues": totals["remaining_physics_text_corruption_issues"],
        "mixed_math_text_cleanup_count": totals["mixed_math_text_cleanup_count"],
        "remaining_mixed_math_text_layout_issues": totals["remaining_mixed_math_text_layout_issues"],
        "math_glyph_cleanup_count": totals["math_glyph_cleanup_count"],
        "math_unreadable_glyph_fix_count": totals["math_unreadable_glyph_fix_count"],
        "empty_paragraph_removed_count": totals["empty_paragraph_removed_count"],
        "table_adjacent_empty_paragraph_cleanup_count": totals["table_adjacent_empty_paragraph_cleanup_count"],
        "table_cell_empty_paragraph_removed_count": totals["table_cell_empty_paragraph_removed_count"],
        "math_block_flow_cleanup_count": totals["math_block_flow_cleanup_count"],
        "suppressed_blank_standalone_image_count": totals["suppressed_blank_standalone_image_count"],
        "suppressed_nonessential_standalone_image_count": totals["suppressed_nonessential_standalone_image_count"],
        "restored_context_image_count": totals["restored_context_image_count"],
        "remaining_nonessential_standalone_image_candidates": totals["remaining_nonessential_standalone_image_candidates"],
        "remaining_empty_paragraph_count": totals["remaining_empty_paragraph_count"],
        "remaining_table_adjacent_empty_paragraph_count": totals["remaining_table_adjacent_empty_paragraph_count"],
        "remaining_table_cell_empty_paragraph_count": totals["remaining_table_cell_empty_paragraph_count"],
        "remaining_malformed_math_block_flow_count": totals["remaining_malformed_math_block_flow_count"],
        "remaining_table_whitespace_layout_issues": totals["remaining_table_whitespace_layout_issues"],
        "remaining_math_glyph_issues": totals["remaining_math_glyph_issues"],
        "remaining_math_unreadable_glyph_issues": totals["remaining_math_unreadable_glyph_issues"],
        "table_inline_image_too_small_count": totals["table_inline_image_too_small_count"],
        "remaining_table_inline_image_too_small_count": totals["remaining_table_inline_image_too_small_count"],
        "table_inline_image_sizing_adjusted_count": totals["table_inline_image_sizing_adjusted_count"],
        "essay_question_figure_relocated_count": totals["essay_question_figure_relocated_count"],
        "essay_question_figure_centered_block_count": totals["essay_question_figure_centered_block_count"],
        "remaining_essay_question_figure_layout_issues": totals["remaining_essay_question_figure_layout_issues"],
        "figure_in_table_too_small_count": totals["figure_in_table_too_small_count"],
        "downs_reaction_notation_issue_count": totals["downs_reaction_notation_issue_count"],
        "word_field_code_leakage_count": totals["word_field_code_leakage_count"],
        "publish_debug_attr_leakage_count": totals["publish_debug_attr_leakage_count"],
        "publish_namespace_leakage_count": totals["publish_namespace_leakage_count"],
        "image_field_text_contamination_count": totals["image_field_text_contamination_count"],
        "chemical_diagram_blank_image_count": totals["chemical_diagram_blank_image_count"],
        "chemical_diagram_near_white_image_count": totals["chemical_diagram_near_white_image_count"],
        "chemical_diagram_tiny_image_count": totals["chemical_diagram_tiny_image_count"],
        "chemical_diagram_bad_crop_count": totals["chemical_diagram_bad_crop_count"],
        "chemical_diagram_oversized_display_count": totals["chemical_diagram_oversized_display_count"],
        "chemical_diagram_placeholder_count": totals["chemical_diagram_placeholder_count"],
        "chemical_diagram_rendered_svg_count": totals["chemical_diagram_rendered_svg_count"],
        "chemical_diagram_rendered_png_count": totals["chemical_diagram_rendered_png_count"],
        "chemical_diagram_render_failed_count": totals["chemical_diagram_render_failed_count"],
        "chemical_diagram_trim_applied_count": totals["chemical_diagram_trim_applied_count"],
        "generic_emf_inline_count": totals["generic_emf_inline_count"],
        "generic_wmf_inline_count": totals["generic_wmf_inline_count"],
        "generic_emf_converted_svg_count": totals["generic_emf_converted_svg_count"],
        "generic_emf_converted_png_count": totals["generic_emf_converted_png_count"],
        "generic_gif_count": totals["generic_gif_count"],
        "generic_gif_placeholder_count": totals["generic_gif_placeholder_count"],
        "generic_gif_blank_count": totals["generic_gif_blank_count"],
        "generic_inline_image_count": totals["generic_inline_image_count"],
        "generic_inline_image_trim_candidate_count": totals["generic_inline_image_trim_candidate_count"],
        "generic_inline_image_trim_applied_count": totals["generic_inline_image_trim_applied_count"],
        "generic_inline_image_oversized_whitespace_count": totals["generic_inline_image_oversized_whitespace_count"],
        "generic_inline_image_bad_crop_count": totals["generic_inline_image_bad_crop_count"],
        "generic_inline_image_blank_count": totals["generic_inline_image_blank_count"],
        "generic_inline_image_near_white_count": totals["generic_inline_image_near_white_count"],
        "generic_inline_image_svg_trim_applied_count": totals["generic_inline_image_svg_trim_applied_count"],
        "generic_inline_image_raster_trim_applied_count": totals["generic_inline_image_raster_trim_applied_count"],
        "unsupported_web_image_count": totals["unsupported_web_image_count"],
        "web_safe_asset_violation_count": totals["web_safe_asset_violation_count"],
        "html": str(html_path),
        "asset_dir": str(asset_dir),
        "totals": totals,
        "suspected_numeric_corruption": suspected_numeric_corruption,
        "web_asset_inventory": web_asset_inventory,
        "generic_inline_trimmed_assets": sorted(generic_inline_image_trim_applied_assets),
        "count_by_type": by_type,
        "per_exam": dict(sorted(per_exam.items(), key=lambda kv: kv[0])),
        "unresolved_objects": [
            {
                "scope": obj.scope,
                "location": obj.location,
                "exam": obj.exam,
                "source_asset": obj.source_asset,
                "classification": obj.classification,
                "fallback_type": obj.fallback_type,
                "prog_id": obj.prog_id,
                "source_ext": obj.source_ext,
                "alt": obj.alt,
                "render_attempted": obj.render_attempted,
                "render_source_used": obj.render_source_used,
                "render_output_type": obj.render_output_type,
                "render_success": obj.render_success,
                "render_source_exts": obj.render_source_exts,
                "render_source_assets": obj.render_source_assets,
            }
            for obj in unique_unresolved_objects
        ],
    }
    gate_result = evaluate_publish_gates(totals, len(unique_unresolved_objects), normalized_output_mode)
    report["publish_gate_summary"] = gate_result["publish_gate_summary"]
    report["publish_gate_findings"] = gate_result["publish_gate_findings"]
    report["publish_verdict"] = gate_result["publish_verdict"]
    report["publish_verdict_legacy"] = gate_result["publish_verdict_legacy"]
    return report


def to_markdown(report: Dict) -> str:
    lines: List[str] = []
    lines.append("# QA Audit Summary")
    lines.append("")
    lines.append(f"- Subject: `{report['subject']}`")
    lines.append(f"- Output mode: `{report.get('output_mode', 'publish')}`")
    lines.append(f"- HTML: `{report['html']}`")
    lines.append(f"- Asset dir: `{report['asset_dir']}`")
    lines.append(f"- Publish verdict: `{report['publish_verdict']}`")
    if report.get("publish_verdict_legacy"):
        lines.append(f"- Legacy publish verdict: `{report['publish_verdict_legacy']}`")
    lines.append("")

    gate_summary = report.get("publish_gate_summary", {})
    lines.append("## Publish Gates")
    lines.append("")
    lines.append(f"- blocker: {int(gate_summary.get('blocker', 0) or 0)}")
    lines.append(f"- error: {int(gate_summary.get('error', 0) or 0)}")
    lines.append(f"- warning: {int(gate_summary.get('warning', 0) or 0)}")
    lines.append(f"- info: {int(gate_summary.get('info', 0) or 0)}")
    lines.append("")
    gate_findings = report.get("publish_gate_findings", [])
    if gate_findings:
        lines.append("| severity | metric | value | title | recommendation |")
        lines.append("|---|---|---:|---|---|")
        for finding in gate_findings:
            lines.append(
                "| {} | `{}` | {} | {} | {} |".format(
                    finding.get("severity", ""),
                    finding.get("metric", ""),
                    finding.get("value", 0),
                    finding.get("title", ""),
                    finding.get("recommendation", ""),
                )
            )
        lines.append("")

    totals = report["totals"]
    lines.append("## Totals")
    lines.append("")
    lines.append(f"- MathML formulas: {totals['mathml_formulas']}")
    lines.append(f"- Remaining preview images: {totals['remaining_preview_images']}")
    lines.append(f"- Remaining text corruption count: {totals['remaining_text_corruption_count']}")
    lines.append(f"- Remaining chemistry inline issues: {totals['remaining_chemistry_inline_issues']}")
    lines.append(f"- Chemistry inline fixes: {totals['chemistry_inline_fixes']}")
    lines.append(f"- Chemistry arrow/symbol fixes: {totals['chemistry_arrow_symbol_fixes']}")
    lines.append(f"- Chemistry unit fixes: {totals['chemistry_unit_fixes']}")
    lines.append(f"- Chemistry glyph fixes: {totals['chemistry_glyph_fix_count']}")
    lines.append(f"- Remaining chemistry arrow/symbol issues: {totals['remaining_chemistry_arrow_symbol_issues']}")
    lines.append(f"- Remaining chemistry unit issues: {totals['remaining_chemistry_unit_issues']}")
    lines.append(f"- Remaining chemistry glyph issues: {totals['remaining_chemistry_glyph_issues']}")
    lines.append(f"- Core promotion candidate count: {totals['core_promotion_candidate_count']}")
    lines.append(f"- Physics unit fixes applied (converter log): {totals['physics_unit_fix_count']}")
    lines.append(f"- Physics text fixes applied (converter log): {totals['physics_text_fix_count']}")
    lines.append(f"- Mixed math/text cleanup fixes applied (converter log): {totals['mixed_math_text_cleanup_count']}")
    lines.append(f"- Math glyph/text fixes applied (converter log): {totals['math_glyph_cleanup_count']}")
    lines.append(f"- Math unreadable glyph fixes applied (converter log): {totals['math_unreadable_glyph_fix_count']}")
    lines.append(f"- Empty paragraphs removed (converter log): {totals['empty_paragraph_removed_count']}")
    lines.append(
        f"- Table-adjacent empty paragraph cleanups (converter log): {totals['table_adjacent_empty_paragraph_cleanup_count']}"
    )
    lines.append(
        f"- Table-cell empty paragraphs removed (converter log): {totals['table_cell_empty_paragraph_removed_count']}"
    )
    lines.append(f"- Math-block flow cleanups (converter log): {totals['math_block_flow_cleanup_count']}")
    lines.append(
        f"- Suppressed blank standalone images (converter log): {totals['suppressed_blank_standalone_image_count']}"
    )
    lines.append(
        f"- Suppressed nonessential standalone context images (converter log): {totals['suppressed_nonessential_standalone_image_count']}"
    )
    lines.append(
        f"- Restored context images kept (converter log): {totals['restored_context_image_count']}"
    )
    lines.append(
        f"- Remaining nonessential standalone image candidates: {totals['remaining_nonessential_standalone_image_candidates']}"
    )
    lines.append(f"- Remaining empty paragraphs: {totals['remaining_empty_paragraph_count']}")
    lines.append(
        f"- Remaining table-adjacent empty paragraphs: {totals['remaining_table_adjacent_empty_paragraph_count']}"
    )
    lines.append(
        f"- Remaining table-cell empty paragraphs: {totals['remaining_table_cell_empty_paragraph_count']}"
    )
    lines.append(
        f"- Remaining malformed math-block flow issues: {totals['remaining_malformed_math_block_flow_count']}"
    )
    lines.append(f"- Remaining table whitespace/layout issues: {totals['remaining_table_whitespace_layout_issues']}")
    lines.append(f"- Remaining physics unit issues: {totals['remaining_physics_unit_issues']}")
    lines.append(f"- Remaining physics text corruption issues: {totals['remaining_physics_text_corruption_issues']}")
    lines.append(f"- Remaining mixed math/text layout issues: {totals['remaining_mixed_math_text_layout_issues']}")
    lines.append(f"- Remaining math glyph issues: {totals['remaining_math_glyph_issues']}")
    lines.append(f"- Remaining math unreadable glyph issues: {totals['remaining_math_unreadable_glyph_issues']}")
    lines.append(f"- Table inline-image too-small count: {totals['table_inline_image_too_small_count']}")
    lines.append(f"- Remaining table inline-image too-small count: {totals['remaining_table_inline_image_too_small_count']}")
    lines.append(f"- Table inline-image sizing adjusted count: {totals['table_inline_image_sizing_adjusted_count']}")
    lines.append(f"- Essay-question figure relocated count: {totals['essay_question_figure_relocated_count']}")
    lines.append(f"- Essay-question figure centered-block count: {totals['essay_question_figure_centered_block_count']}")
    lines.append(f"- Remaining essay-question figure layout issues: {totals['remaining_essay_question_figure_layout_issues']}")
    lines.append(f"- Figure-in-table too-small count: {totals['figure_in_table_too_small_count']}")
    lines.append(f"- Downs reaction notation issue count: {totals['downs_reaction_notation_issue_count']}")
    lines.append(f"- Word field-code leakage count: {totals['word_field_code_leakage_count']}")
    lines.append(f"- Publish debug-attribute leakage count: {totals['publish_debug_attr_leakage_count']}")
    lines.append(f"- Publish namespace leakage count: {totals['publish_namespace_leakage_count']}")
    lines.append(f"- Image-field text contamination count: {totals['image_field_text_contamination_count']}")
    lines.append(f"- Chemistry inline fixes applied (converter log): {totals['chemistry_inline_fixes_applied']}")
    lines.append(f"- Chemistry arrow/symbol fixes applied (converter log): {totals['chemistry_arrow_symbol_fixes_applied']}")
    lines.append(f"- Chemistry unit fixes applied (converter log): {totals['chemistry_unit_fixes_applied']}")
    lines.append(f"- Chemical-diagram blank images: {totals['chemical_diagram_blank_image_count']}")
    lines.append(f"- Chemical-diagram near-white images: {totals['chemical_diagram_near_white_image_count']}")
    lines.append(f"- Chemical-diagram tiny images: {totals['chemical_diagram_tiny_image_count']}")
    lines.append(f"- Chemical-diagram suspicious crops: {totals['chemical_diagram_bad_crop_count']}")
    lines.append(f"- Chemical-diagram oversized display count: {totals['chemical_diagram_oversized_display_count']}")
    lines.append(f"- Chemical-diagram trim applied count: {totals['chemical_diagram_trim_applied_count']}")
    lines.append(f"- Chemical-diagram placeholders: {totals['chemical_diagram_placeholder_count']}")
    lines.append(f"- Chemical-diagram rendered SVG: {totals['chemical_diagram_rendered_svg_count']}")
    lines.append(f"- Chemical-diagram rendered PNG: {totals['chemical_diagram_rendered_png_count']}")
    lines.append(f"- Chemical-diagram render failed: {totals['chemical_diagram_render_failed_count']}")
    lines.append(f"- Generic inline `.emf` count: {totals['generic_emf_inline_count']}")
    lines.append(f"- Generic inline `.wmf` count: {totals['generic_wmf_inline_count']}")
    lines.append(f"- Generic `.emf` converted to SVG count: {totals['generic_emf_converted_svg_count']}")
    lines.append(f"- Generic `.emf` converted to PNG count: {totals['generic_emf_converted_png_count']}")
    lines.append(f"- Generic inline GIF count: {totals['generic_gif_count']}")
    lines.append(f"- Generic GIF placeholder count: {totals['generic_gif_placeholder_count']}")
    lines.append(f"- Generic GIF blank count: {totals['generic_gif_blank_count']}")
    lines.append(f"- Generic inline-image count: {totals['generic_inline_image_count']}")
    lines.append(f"- Generic inline-image trim candidates: {totals['generic_inline_image_trim_candidate_count']}")
    lines.append(f"- Generic inline-image trim applied: {totals['generic_inline_image_trim_applied_count']}")
    lines.append(f"- Generic inline-image oversized whitespace remaining: {totals['generic_inline_image_oversized_whitespace_count']}")
    lines.append(f"- Generic inline-image bad crop count: {totals['generic_inline_image_bad_crop_count']}")
    lines.append(f"- Generic inline-image blank count: {totals['generic_inline_image_blank_count']}")
    lines.append(f"- Generic inline-image near-white count: {totals['generic_inline_image_near_white_count']}")
    lines.append(f"- Generic inline-image SVG trim applied: {totals['generic_inline_image_svg_trim_applied_count']}")
    lines.append(f"- Generic inline-image raster trim applied: {totals['generic_inline_image_raster_trim_applied_count']}")
    lines.append(f"- Unsupported web image count: {totals['unsupported_web_image_count']}")
    lines.append(f"- Web-safe asset violation count: {totals['web_safe_asset_violation_count']}")
    lines.append(f"- Unresolved Visio previews: {totals['unresolved_visio_previews']}")
    lines.append(f"- Normalized text fixes applied: {totals['normalized_text_fixes_applied']}")
    lines.append(f"- OLE fallback images (converter log): {totals['ole_preview_images']}")
    lines.append(f"- EMF/WMF previews encountered: {totals['emf_wmf_previews']}")
    lines.append(f"- EMF/WMF previews rasterized to PNG: {totals['rasterized_metafile_previews']}")
    lines.append(f"- EMF/WMF raster-cache hits: {totals['rasterized_metafile_cache_hits']}")
    lines.append(f"- Sidecar MathML equations: {totals['sidecar_mathml_equations']}")
    lines.append(f"- OMML equations: {totals['omml_equations']}")
    lines.append(f"- Suspected numeric corruption findings: {len(report.get('suspected_numeric_corruption', []))}")
    lines.append("")

    lines.append("## Count By Type")
    lines.append("")
    lines.append("| type | count |")
    lines.append("|---|---:|")
    for key in TYPE_KEYS:
        lines.append(f"| `{key}` | {report['count_by_type'][key]} |")
    lines.append("")

    lines.append("## Per-Exam")
    lines.append("")
    lines.append("| exam | mathml | previews | corruption | chem-inline issues | chem-inline fixes | chem-arrow issues | chem-arrow fixes | chem-unit issues | chem-unit fixes | physics-unit issues | physics-text issues | math-glyph issues | table-img-too-small | table-img-adjusted | downs-issue | field-leak | img-field-leak | chem-blank | chem-near-white | chem-tiny | chem-bad-crop | chem-oversized | chem-trimmed | chem-placeholder | chem-svg | chem-png | chem-render-failed | generic-inline | generic-trim-candidate | generic-trim-applied | generic-oversized-left | generic-bad-crop | generic-blank | generic-near-white | generic-svg-trim | generic-raster-trim | unresolved visio |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for exam, stats in report["per_exam"].items():
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                exam,
                stats["mathml_formulas"],
                stats["remaining_preview_count"],
                stats["remaining_text_corruption_count"],
                stats["remaining_chemistry_inline_issues"],
                stats["chemistry_inline_fixes"],
                stats["remaining_chemistry_arrow_symbol_issues"],
                stats["chemistry_arrow_symbol_fixes"],
                stats["remaining_chemistry_unit_issues"],
                stats["chemistry_unit_fixes"],
                stats["remaining_physics_unit_issues"],
                stats["remaining_physics_text_corruption_issues"],
                stats["remaining_math_glyph_issues"],
                stats["table_inline_image_too_small_count"],
                stats["table_inline_image_sizing_adjusted_count"],
                stats["downs_reaction_notation_issue_count"],
                stats["word_field_code_leakage_count"],
                stats["image_field_text_contamination_count"],
                stats["chemical_diagram_blank_image_count"],
                stats["chemical_diagram_near_white_image_count"],
                stats["chemical_diagram_tiny_image_count"],
                stats["chemical_diagram_bad_crop_count"],
                stats["chemical_diagram_oversized_display_count"],
                stats["chemical_diagram_trim_applied_count"],
                stats["chemical_diagram_placeholder_count"],
                stats["chemical_diagram_rendered_svg_count"],
                stats["chemical_diagram_rendered_png_count"],
                stats["chemical_diagram_render_failed_count"],
                stats["generic_inline_image_count"],
                stats["generic_inline_image_trim_candidate_count"],
                stats["generic_inline_image_trim_applied_count"],
                stats["generic_inline_image_oversized_whitespace_count"],
                stats["generic_inline_image_bad_crop_count"],
                stats["generic_inline_image_blank_count"],
                stats["generic_inline_image_near_white_count"],
                stats["generic_inline_image_svg_trim_applied_count"],
                stats["generic_inline_image_raster_trim_applied_count"],
                stats["unresolved_visio_placeholders"],
            )
        )
    lines.append("")

    if report["subject"] == "chemistry":
        lines.append("## Chemistry Result")
        lines.append("")
        lines.append("- Core fixes observed: rendered-successful chemical diagrams are no longer counted as unresolved previews.")
        lines.append("- Core fixes observed: unresolved object classification remains separated by equation/diagram/chart/chemical-diagram/generic-image/unknown-preview.")
        lines.append("- Chemistry fixes observed: inline formula rewrites plus arrow/symbol and unit normalization counters captured.")
        lines.append("- Chemistry display sizing: `chem-diagram` uses chemistry-specific width caps; oversized display is audited separately.")
        lines.append(f"- Remaining unresolved chemistry diagrams: {totals['chemdraw_preview_count'] + totals['chemsketch_preview_count'] + totals['chemwindow_preview_count']}")
        lines.append(f"- Chemical-diagram blank images: {totals['chemical_diagram_blank_image_count']}")
        lines.append(f"- Chemical-diagram near-white images: {totals['chemical_diagram_near_white_image_count']}")
        lines.append(f"- Chemical-diagram tiny images: {totals['chemical_diagram_tiny_image_count']}")
        lines.append(f"- Chemical-diagram suspicious crops: {totals['chemical_diagram_bad_crop_count']}")
        lines.append(f"- Chemical-diagram oversized display count: {totals['chemical_diagram_oversized_display_count']}")
        lines.append(f"- Chemical-diagram trim applied count: {totals['chemical_diagram_trim_applied_count']}")
        lines.append(f"- Chemical-diagram placeholders: {totals['chemical_diagram_placeholder_count']}")
        lines.append(f"- Chemical-diagram rendered SVG: {totals['chemical_diagram_rendered_svg_count']}")
        lines.append(f"- Chemical-diagram rendered PNG: {totals['chemical_diagram_rendered_png_count']}")
        lines.append(f"- Chemical-diagram render failed: {totals['chemical_diagram_render_failed_count']}")
        lines.append(f"- Generic inline `.emf`: {totals['generic_emf_inline_count']}")
        lines.append(f"- Generic inline `.wmf`: {totals['generic_wmf_inline_count']}")
        lines.append(f"- Generic GIF placeholders: {totals['generic_gif_placeholder_count']}")
        lines.append(f"- Generic inline-image trim candidates: {totals['generic_inline_image_trim_candidate_count']}")
        lines.append(f"- Generic inline-image trim applied: {totals['generic_inline_image_trim_applied_count']}")
        lines.append(f"- Generic inline-image oversized whitespace remaining: {totals['generic_inline_image_oversized_whitespace_count']}")
        lines.append(f"- Generic inline-image bad crop count: {totals['generic_inline_image_bad_crop_count']}")
        lines.append(f"- Web-safe asset violations: {totals['web_safe_asset_violation_count']}")
        lines.append(f"- Downs reaction notation issues: {totals['downs_reaction_notation_issue_count']}")
        lines.append(f"- Word field-code leakage count: {totals['word_field_code_leakage_count']}")
        lines.append(f"- Image-field text contamination count: {totals['image_field_text_contamination_count']}")
        lines.append(f"- Remaining plain-text symbol issues: {totals['remaining_chemistry_arrow_symbol_issues']}")
        lines.append(f"- Remaining unit/notation issues: {totals['remaining_chemistry_unit_issues']}")
        lines.append("")

    if report["subject"] == "physics":
        lines.append("## Physics Result")
        lines.append("")
        lines.append(f"- Physics unit fixes applied (converter log): {totals['physics_unit_fix_count']}")
        lines.append(f"- Physics text fixes applied (converter log): {totals['physics_text_fix_count']}")
        lines.append(f"- Mixed math/text cleanup fixes applied (converter log): {totals['mixed_math_text_cleanup_count']}")
        lines.append(f"- Remaining physics unit issues: {totals['remaining_physics_unit_issues']}")
        lines.append(f"- Remaining physics text corruption issues: {totals['remaining_physics_text_corruption_issues']}")
        lines.append(f"- Remaining mixed math/text layout issues: {totals['remaining_mixed_math_text_layout_issues']}")
        lines.append(f"- Generic inline-image trim candidates: {totals['generic_inline_image_trim_candidate_count']}")
        lines.append(f"- Generic inline-image trim applied: {totals['generic_inline_image_trim_applied_count']}")
        lines.append(f"- Generic inline-image oversized whitespace remaining: {totals['generic_inline_image_oversized_whitespace_count']}")
        lines.append(f"- Generic inline-image bad crop count: {totals['generic_inline_image_bad_crop_count']}")
        lines.append("")

    if report["subject"] == "math":
        lines.append("## Math Result")
        lines.append("")
        lines.append(f"- Math glyph/text fixes applied (converter log): {totals['math_glyph_cleanup_count']}")
        lines.append(f"- Math unreadable glyph fixes applied (converter log): {totals['math_unreadable_glyph_fix_count']}")
        lines.append(f"- Remaining math glyph issues: {totals['remaining_math_glyph_issues']}")
        lines.append(f"- Remaining math unreadable glyph issues: {totals['remaining_math_unreadable_glyph_issues']}")
        lines.append(f"- Table inline-image too-small count: {totals['table_inline_image_too_small_count']}")
        lines.append(f"- Remaining table inline-image too-small count: {totals['remaining_table_inline_image_too_small_count']}")
        lines.append(f"- Table inline-image sizing adjusted count: {totals['table_inline_image_sizing_adjusted_count']}")
        lines.append(f"- Essay-question figure relocated count: {totals['essay_question_figure_relocated_count']}")
        lines.append(f"- Essay-question figure centered-block count: {totals['essay_question_figure_centered_block_count']}")
        lines.append(f"- Remaining essay-question figure layout issues: {totals['remaining_essay_question_figure_layout_issues']}")
        lines.append(f"- Figure-in-table too-small count: {totals['figure_in_table_too_small_count']}")
        lines.append(f"- Generic inline-image trim candidates: {totals['generic_inline_image_trim_candidate_count']}")
        lines.append(f"- Generic inline-image trim applied: {totals['generic_inline_image_trim_applied_count']}")
        lines.append(f"- Generic inline-image bad crop count: {totals['generic_inline_image_bad_crop_count']}")
        lines.append("")

    if report.get("suspected_numeric_corruption"):
        lines.append("## Suspected Numeric Corruption")
        lines.append("")
        lines.append("| exam | location | type | snippet |")
        lines.append("|---|---|---|---|")
        for item in report["suspected_numeric_corruption"]:
            lines.append(
                "| {} | `{}` | {} | `{}` |".format(
                    item.get("exam", ""),
                    item.get("location", ""),
                    item.get("type", ""),
                    item.get("snippet", ""),
                )
            )
        lines.append("")

    if report.get("web_asset_inventory"):
        lines.append("## Web Asset Inventory")
        lines.append("")
        lines.append("| exam | location | source path | class | classification | ext | web-safe | placeholder-like | blank | trim-candidate | trim-applied | trim-type | width | height |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---:|---:|")
        for item in report["web_asset_inventory"]:
            lines.append(
                "| {} | `{}` | `{}` | `{}` | {} | `{}` | {} | {} | {} | {} | {} | `{}` | {} | {} |".format(
                    item.get("exam", ""),
                    item.get("location", ""),
                    item.get("source_path", ""),
                    item.get("role_class", ""),
                    item.get("classification", ""),
                    item.get("extension", ""),
                    item.get("web_safe_format", False),
                    item.get("placeholder_like", False),
                    item.get("blank", False),
                    item.get("trim_candidate", False),
                    item.get("trim_applied", False),
                    item.get("trim_type", ""),
                    item.get("width", "") if item.get("width") is not None else "",
                    item.get("height", "") if item.get("height") is not None else "",
                )
            )
        lines.append("")

    if report.get("generic_inline_trimmed_assets"):
        lines.append("## Generic Inline Trimmed Assets")
        lines.append("")
        for src in report["generic_inline_trimmed_assets"]:
            lines.append(f"- `{src}`")
        lines.append("")

    lines.append("## Unresolved Objects")
    lines.append("")
    lines.append("| exam | location | classification | fallback | prog id | source ext | source asset | render attempted | render source | output type | render success |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for obj in report["unresolved_objects"]:
        lines.append(
            "| {} | `{}` | {} | {} | `{}` | `{}` | `{}` | {} | `{}` | `{}` | {} |".format(
                obj["exam"],
                obj["location"],
                obj["classification"],
                obj["fallback_type"],
                obj["prog_id"],
                obj["source_ext"],
                obj["source_asset"],
                obj.get("render_attempted"),
                obj.get("render_source_used", ""),
                obj.get("render_output_type", ""),
                obj.get("render_success"),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit converted exam HTML bundle.")
    parser.add_argument("html", type=Path)
    parser.add_argument("--asset-dir", type=Path, default=None)
    parser.add_argument("--conversion-log", type=Path, default=None)
    parser.add_argument("--subject", choices=["generic", "physics", "chemistry", "math", "biology"], default=None)
    parser.add_argument("--output-mode", choices=["internal", "publish"], default="publish")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--print-md", action="store_true")
    args = parser.parse_args()

    html_path = args.html.resolve()
    asset_dir = args.asset_dir.resolve() if args.asset_dir else html_path.with_name(html_path.stem + "_files")
    subject = args.subject or detect_subject(html_path.name)
    report = audit(
        html_path,
        asset_dir,
        args.conversion_log.resolve() if args.conversion_log else None,
        subject,
        output_mode=args.output_mode,
    )

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(to_markdown(report), encoding="utf-8")
    if args.print_md or (not args.json_out and not args.md_out):
        print(to_markdown(report))


if __name__ == "__main__":
    main()
