#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import hashlib
import html
import json
import re
import time
import unicodedata
from io import StringIO
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

try:
    from lxml import etree as lxml_etree  # type: ignore
    from lxml import html as lxml_html  # type: ignore
except Exception:  # pragma: no cover - optional dependency fallback
    lxml_etree = None
    lxml_html = None

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - optional dependency fallback
    pd = None


SCHEMA_VERSION = "output_contract.v1"
PARSER_SCHEMA_VERSION = "parser_report.v1"
OVERRIDE_AUDIT_SCHEMA_VERSION = "override_audit.v1"
OVERRIDE_MANIFEST_SCHEMA_VERSION = "override_manifest.v1"

OVERRIDE_ACTIONS = {
    "asset_visibility",
    "asset_role_override",
    "placement_override",
    "text_patch",
    "publish_exception",
    "answer_override",
}
OVERRIDE_ASSET_ROLES = {"equation", "diagram", "chart", "chemical-diagram", "generic-image", "unknown-preview"}
OVERRIDE_PLACEMENTS = {"inline", "display", "context-right", "context-below", "centered", "table-cell", "unknown"}
OVERRIDE_VISIBILITY = {"keep", "suppress"}
OVERRIDE_TEXT_MATCH_MODE = {"literal", "regex"}
OVERRIDE_SEVERITIES = {"info", "warning", "error", "blocker"}
OVERRIDE_ANSWER_MODES = {"single_choice", "boolean_group", "short_answer", "rubric", "none"}

BLOCK_RE = re.compile(r"(?is)<(p|div|table|figure|h[1-6])\b[^>]*>.*?</\1>")
IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*\"([^\"]*)\"")
TAG_RE = re.compile(r"<[^>]+>")
MATH_FRAGMENT_RE = re.compile(r"<(?:\w+:)?math\b.*?</(?:\w+:)?math>", re.IGNORECASE | re.DOTALL)
TABLE_ROW_RE = re.compile(r"(?is)<tr\b[^>]*>(.*?)</tr>")
TABLE_CELL_RE = re.compile(r"(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>")

EXAM_HEADER_RE = re.compile(r"(?iu)^\s*đề\s*(\d{1,3})\b")
QUESTION_HEADER_RE = re.compile(
    r"(?iu)^\s*(?:câu|question)\s*(\d{1,3})\b(?:\s*\([^)]+\))?\s*(?:[\.:\)-])?\s*(.*)$"
)
EN_QUESTION_HEADER_RE = re.compile(r"(?iu)^\s*question\s*(\d{1,3})\b")
QUESTION_RANGE_RE = re.compile(r"(?iu)từ\s*câu\s*\d+\s*đến\s*câu\s*\d+")
QUESTION_DECORATIVE_PREFIX_RE = re.compile(r"^[\s\u00a0]*(?:[\u00bb\u2022\uf0b7\uf040]+[\s\u00a0]*)+")
OPTION_MARKER_RE = re.compile(r"(?iu)(?:^|\s)([ABCD])\.")
TRUE_FALSE_RE = re.compile(
    r"(?iu)(?:"
    r"đúng\s*sai"
    r"|đúng\s*[/\\-–]\s*sai"
    r"|phát\s*biểu\s*sau\s*đây\s*đúng"
    r"|phát\s*biểu\s*sai"
    r")"
)
SHORT_ANSWER_RE = re.compile(r"(?iu)(?:trả\s*lời\s*ngắn|điền\s*vào|viết\s*phương\s*trình|nêu\s*kết\s*quả)")
ESSAY_RE = re.compile(r"(?iu)(?:chứng\s*minh|trình\s*bày|phân\s*tích|giải\s*thích|bình\s*luận)")
QUESTION_TYPE_APPENDIX_RE = re.compile(
    r"(?iu)(?:"
    r"------------------------\s*hết\s*------------------------"
    r"|lời\s*giải(?:\s*chi\s*tiết)?"
    r"|hướng\s*dẫn\s*giải(?:\s*chi\s*tiết)?"
    r"|đáp\s*án(?:\s*và\s*lời\s*giải(?:\s*tham\s*khảo)?)?"
    r"|đáp\s*số"
    r"|hướng\s*dẫn\s*chấm"
    r"|bảng\s*đáp\s*án"
    r")"
)
ANSWER_ZONE_HEADING_RE = re.compile(
    r"(?iu)^\s*(?:"
    r"(?:[ivxlcdm]+|phần\s*[ivxlcdm]+)\s*[\.\):]?\s*"
    r")?(?:"
    r"đáp\s*án(?:\s*và\s*lời\s*giải(?:\s*tham\s*khảo)?|\s*tham\s*khảo)?"
    r"|bảng\s*đáp\s*án"
    r"|tóm\s*tắt\s*đáp\s*án"
    r")\s*[:\.\)\-]?\s*$"
)
SHORT_VALUE_RE = re.compile(r"(?iu)^[\d\.,+\-−/%:]+(?:\s*[a-zA-Zµ°²³⁻]+)?$")
SUMMARY_LIST_CHOICE_RE = re.compile(r"(?iu)^\s*(?:câu\s*)?(\d{1,3})\s*[:\.\)\-]\s*([ABCD])\s*$")
LOCAL_CHOICE_RE = re.compile(r"(?iu)\bđáp\s*(?:án|án)\s*[:：]?\s*([ABCD])\b")
LOCAL_SHORT_RE = re.compile(r"(?iu)\b(?:đáp\s*số|đáp\s*án)\s*[:：]\s*([^\n]{1,80})")
LOCAL_BOOLEAN_ROW_RE = re.compile(r"(?iu)\b([abcd])\)\s*(đúng|sai)\b")
BOOLEAN_ROW_RE = re.compile(r"(?iu)\b([abcd])\)\s*(đúng|sai|đ|s|t|f)\b")
BOOLEAN_GROUP_TOKEN_RE = re.compile(r"(?iu)\b(?:đúng|sai|true|false|đ|s|t|f|1|0)\b")
# "Trả lời" is a frequent instruction fragment ("Học sinh trả lời từ câu ..."), so only treat it as
# an explicit-answer cue when it uses punctuation like "Trả lời:" / "Trả lời.".
SOLUTION_EXPLICIT_VALUE_RE = re.compile(
    r"(?iu)(?:\b(?:đáp\s*án|đáp\s*số|đs)\b\s*[:：.]?|\btrả\s*lời\b\s*[:：.])\s*([^\n]{1,120})"
)
SOLUTION_CHOICE_RE = re.compile(r"(?iu)\b(?:chọn|chon)\s*([ABCD])\b")
SOLUTION_SHORT_RE = re.compile(r"(?iu)\b(?:kết\s*quả|suy\s*ra|vậy)\s*[:：]?\s*([^\n]{1,80})")
RUBRIC_MARKER_RE = re.compile(r"(?iu)(?:^|\s)(?:\[R\]|R\.)")
INLINE_SOLUTION_MARKER_RE = re.compile(
    r"(?iu)^\s*(?:cách\s*giải|hướng\s*dẫn\s*giải(?:\s*chi\s*tiết)?|lời\s*giải|giải\s*thích|phương\s*pháp|phân\s*tích|kết\s*luận)\b"
)
RUBRIC_SCORING_MARKER_RE = re.compile(
    r"(?iu)(?:hướng\s*dẫn\s*chấm|thang\s*điểm|nội\s*dung\s*điểm)"
)
QUESTION_ANCHOR_RE = re.compile(
    r"(?iu)^\s*(?:câu|question)\s*(\d{1,3})\b(?:\s*\([^)]+\))?\s*(?:[:\.\)\-]\s*)?(.*)$"
)
QUESTION_ANCHOR_INLINE_RE = re.compile(
    r"(?iu)(?:^|(?<=\s))(?:câu|question)\s*(\d{1,3})\b(?:\s*\([^)]+\))?\s*(?:[:\.\)\-]\s*)?"
)
RUBRIC_TABLE_MARKER_RE = re.compile(r"(?iu)\b(?:hướng\s*dẫn\s*chấm|nội\s*dung|điểm|thang\s*điểm)\b")
PACKED_SUMMARY_CELL_RE = re.compile(
    r"(?iu)^\s*(?:câu\s*)?(\d{1,3})\s*[:\.\)\-]\s*([ABCD]|đúng|sai|đ|s|t|f)\s*$"
)
END_KEY_MARKER_RE = ANSWER_ZONE_HEADING_RE

DOCUMENT_FAMILY_OBJECTIVE_END_KEY = "objective_with_end_key"
DOCUMENT_FAMILY_OBJECTIVE_INLINE = "objective_with_inline_solution"
DOCUMENT_FAMILY_RUBRIC = "rubric_scoring_doc"
DOCUMENT_FAMILY_UNKNOWN = "unknown"

DOCUMENT_FAMILY_PRIORITY_PATHS = {
    DOCUMENT_FAMILY_OBJECTIVE_END_KEY: [
        "manual_override",
        "answer_summary_table",
        "answer_summary_list",
        "anchored_solution_block",
        "solution_explicit",
        "solution_inferred",
        "local_formatting",
    ],
    DOCUMENT_FAMILY_OBJECTIVE_INLINE: [
        "manual_override",
        "anchored_solution_block",
        "solution_explicit",
        "solution_inferred",
        "answer_summary_table",
        "answer_summary_list",
        "local_formatting",
    ],
    DOCUMENT_FAMILY_RUBRIC: [
        "manual_override",
        "anchored_rubric_block",
        "rubric_marker",
        "solution_explicit",
        "solution_inferred",
        "local_formatting",
        "answer_summary_table",
        "answer_summary_list",
    ],
    DOCUMENT_FAMILY_UNKNOWN: [
        "manual_override",
        "anchored_solution_block",
        "answer_summary_table",
        "answer_summary_list",
        "solution_explicit",
        "solution_inferred",
        "local_formatting",
    ],
}


@dataclass
class HtmlBlock:
    block_index: int
    tag_name: str
    start: int
    end: int
    line: int
    exam_id: str
    html: str
    text: str


@dataclass
class ParserWarning:
    severity: str
    code: str
    message: str
    exam_id: str
    question_id: str
    line: int


@dataclass
class ParsedQuestion:
    item_id: str
    exam_id: str
    question_number: int
    start_block_index: int
    end_block_index: int
    start_line: int
    prompt_preview: str
    question_type: str
    parse_confidence: float
    warning_codes: List[str]
    warnings: List[ParserWarning]
    assets: List[Dict[str, object]]
    math_fragments: List[Dict[str, object]]
    text_content: str
    html_content: str
    block_texts: List[str]
    answer_key: Dict[str, Any] = field(default_factory=dict)
    answer_sources: List[Dict[str, Any]] = field(default_factory=list)
    reconciliation: Dict[str, Any] = field(default_factory=dict)
    answer_detection: Dict[str, Any] = field(default_factory=dict)
    rubric: Dict[str, Any] = field(default_factory=dict)
    rubric_detection: Dict[str, Any] = field(default_factory=dict)
    qa_flags: List[str] = field(default_factory=list)
    manual_answer_override: Dict[str, Any] = field(default_factory=dict)


PARSER_SUPPORT_PACKAGES = {
    "lxml_available": lxml_html is not None,
    "pandas_available": pd is not None,
    "docx2python_available": importlib.util.find_spec("docx2python") is not None,
}


def sha256_file(path: Optional[Path]) -> str:
    if path is None:
        return "none"
    try:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except FileNotFoundError:
        return "missing"


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
    if ("tieng" in tokens and "anh" in tokens) or {"english", "eng"} & tokens:
        return "english"
    if {"van", "literature", "literary", "nguvan"} & tokens or ("ngu" in tokens and "van" in tokens):
        return "literature"
    return "generic"


def normalize_visible_text(html_fragment: str) -> str:
    text = MATH_FRAGMENT_RE.sub(" ", html_fragment)
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _parse_html_fragment_dom(html_fragment: str):
    if lxml_html is None:
        return None
    try:
        return lxml_html.fragment_fromstring(html_fragment, create_parent="div")
    except Exception:
        try:
            return lxml_html.fromstring(f"<div>{html_fragment}</div>")
        except Exception:
            return None


def _dom_element_html(element: Any) -> str:
    if element is None or lxml_etree is None:
        return ""
    try:
        return lxml_etree.tostring(element, encoding="unicode", method="html")
    except Exception:
        return ""


def _extract_dom_structural_blocks(fragment_html: str) -> List[Dict[str, Any]]:
    root = _parse_html_fragment_dom(fragment_html)
    if root is None:
        return []
    blocks: List[Dict[str, Any]] = []
    structural_tags = {"p", "div", "table", "figure", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol"}
    for idx, child in enumerate(list(root)):
        tag = getattr(child, "tag", "")
        if not isinstance(tag, str):
            continue
        tag_name = tag.lower()
        if tag_name not in structural_tags:
            continue
        text = _normalize_space(getattr(child, "text_content", lambda: "")())
        html_text = _dom_element_html(child)
        if not text and tag_name != "table":
            continue
        blocks.append(
            {
                "block_index": idx,
                "tag_name": tag_name,
                "text": text,
                "html": html_text,
            }
        )
    return blocks


def _table_rows_from_pandas(table_html: str) -> List[List[str]]:
    if pd is None:
        return []
    try:
        dataframes = pd.read_html(StringIO(table_html), header=None, keep_default_na=False, displayed_only=False)
    except Exception:
        return []
    rows: List[List[str]] = []
    for dataframe in dataframes:
        if dataframe is None or getattr(dataframe, "empty", False):
            continue
        try:
            dataframe = dataframe.fillna("")
        except Exception:
            pass
        for _, row in dataframe.iterrows():
            cells = [_normalize_space(str(cell)) for cell in list(row)]
            cleaned = [cell for cell in cells if cell or len(cells) == 1]
            if cleaned:
                rows.append(cleaned)
    return rows


def _table_rows_from_lxml(table_html: str) -> List[List[str]]:
    root = _parse_html_fragment_dom(table_html)
    if root is None:
        return []
    tables = []
    if getattr(root, "tag", "").lower() == "table":
        tables = [root]
    else:
        try:
            tables = list(root.xpath(".//table"))
        except Exception:
            tables = []
    rows: List[List[str]] = []
    for table in tables:
        try:
            row_nodes = table.xpath(".//tr")
        except Exception:
            row_nodes = []
        for row in row_nodes:
            try:
                cell_nodes = row.xpath("./th|./td")
            except Exception:
                cell_nodes = []
            cells = [_normalize_space("".join(cell.itertext())) for cell in cell_nodes]
            cleaned = [cell for cell in cells if cell or len(cells) == 1]
            if cleaned:
                rows.append(cleaned)
    return rows


def _extract_table_rows(table_html: str) -> List[List[str]]:
    rows = _table_rows_from_pandas(table_html)
    if rows:
        return rows
    rows = _table_rows_from_lxml(table_html)
    if rows:
        return rows
    return _extract_table_cells_regex(table_html)


def _extract_table_cells_regex(table_html: str) -> List[List[str]]:
    rows: List[List[str]] = []
    for row_html in TABLE_ROW_RE.findall(table_html):
        cells = [_normalize_space(normalize_visible_text(cell_html)) for cell_html in TABLE_CELL_RE.findall(row_html)]
        cleaned = [cell for cell in cells if cell or len(cells) == 1]
        if cleaned:
            rows.append(cleaned)
    return rows


def _parse_packed_summary_cell(value: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    normalized = _normalize_space(value)
    match = PACKED_SUMMARY_CELL_RE.match(normalized)
    if not match:
        return None
    qnum = str(int(match.group(1)))
    token = _normalize_space(match.group(2)).lower()
    if token in {"a", "b", "c", "d"}:
        return qnum, {"mode": "single_choice", "value": token.upper()}
    boolean_value = _normalize_boolean_value(token)
    if boolean_value is not None:
        return qnum, {"mode": "boolean_group", "subanswers": {"a": boolean_value}}
    return None


def exam_sort_key(exam_id: str) -> Tuple[int, str]:
    if exam_id.startswith("DE_"):
        suffix = exam_id[3:]
        if suffix.isdigit():
            return (int(suffix), exam_id)
    return (10**9, exam_id)


def parse_attrs(tag: str) -> Dict[str, str]:
    attrs: Dict[str, str] = {}
    for key, value in ATTR_RE.findall(tag):
        attrs[key.lower()] = value
    return attrs


def offset_to_line(line_starts: List[int], offset: int) -> int:
    return bisect_right(line_starts, max(0, offset))


def build_line_starts(text: str) -> List[int]:
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def infer_asset_role(attrs: Dict[str, str]) -> str:
    css = attrs.get("class", "").lower()
    alt = attrs.get("alt", "").lower()
    prog = attrs.get("data-ole-progid", "").lower()
    joined = f"{css} {alt} {prog}".lower()

    if "equation" in joined:
        return "equation"
    if any(tok in joined for tok in ("chemdraw", "chemsketch", "chemwindow", "chemical-diagram", "chem-diagram")):
        return "chemical-diagram"
    if any(tok in joined for tok in ("diagram", "graph", "chart", "visio", "physics-diagram", "diagram-asset")):
        return "diagram"
    return "generic-image"


def infer_asset_fallback_type(attrs: Dict[str, str]) -> str:
    css = attrs.get("class", "").lower()
    if "equation-preview" in css or "equation-fallback" in css:
        return "equation_preview"
    if "diagram-preview" in css or "diagram-asset" in css or "physics-diagram" in css:
        return "diagram_preview"
    if "chemical-diagram" in css or "chem-diagram" in css:
        return "chemical_diagram_preview"
    if "ole-preview" in css or "embedded-object" in css:
        return "ole_preview"
    return "inline_image"


def infer_asset_placement(chunk_html: str, tag_start: int, attrs: Dict[str, str]) -> str:
    css = attrs.get("class", "").lower()
    if "essential-figure-image" in css:
        return "centered"
    prefix = chunk_html[max(0, tag_start - 240):tag_start].lower()
    if prefix.rfind("<td") > prefix.rfind("</td"):
        return "table-cell"
    if "math-block" in prefix:
        return "display"
    return "inline"


def extract_assets(chunk_html: str, question_id: str) -> List[Dict[str, object]]:
    assets: List[Dict[str, object]] = []
    for idx, match in enumerate(IMG_TAG_RE.finditer(chunk_html), start=1):
        tag = match.group(0)
        attrs = parse_attrs(tag)
        role = infer_asset_role(attrs)
        placement = infer_asset_placement(chunk_html, match.start(), attrs)
        src = attrs.get("src", "")
        assets.append(
            {
                "asset_id": f"{question_id}-A{idx:03d}",
                "src": src,
                "role": role,
                "placement": placement,
                "fallback_type": infer_asset_fallback_type(attrs),
                "alt": attrs.get("alt", ""),
                "css_class": attrs.get("class", ""),
                "source_ext": attrs.get("data-source-ext", ""),
                "prog_id": attrs.get("data-ole-progid", ""),
            }
        )
    return assets


def extract_math_fragments(chunk_html: str, question_id: str) -> List[Dict[str, object]]:
    fragments: List[Dict[str, object]] = []
    for idx, match in enumerate(MATH_FRAGMENT_RE.finditer(chunk_html), start=1):
        frag = match.group(0)
        lower = frag.lower()
        display = "display=\"block\"" in lower or "display='block'" in lower
        if not display:
            prefix = chunk_html[max(0, match.start() - 180):match.start()].lower()
            if "math-block" in prefix:
                display = True
        fragments.append(
            {
                "fragment_id": f"{question_id}-M{idx:03d}",
                "placement": "display" if display else "inline",
                "char_length": len(frag),
            }
        )
    return fragments


def infer_question_type(text: str) -> Tuple[str, float, Dict[str, int]]:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    option_count = len(set(OPTION_MARKER_RE.findall(normalized)))

    # Rubric/scoring blocks should stay essay-like even if they contain many
    # stray A/B/C/D tokens from tables or worked examples.
    if RUBRIC_SCORING_MARKER_RE.search(normalized):
        return "essay", 0.82, {"option_count": option_count}
    if TRUE_FALSE_RE.search(normalized) and option_count < 4:
        return "true_false", 0.82, {"option_count": option_count}
    if SHORT_ANSWER_RE.search(normalized):
        return "short_answer", 0.76, {"option_count": option_count}
    # Explicit solution text should not be typed as essay. These chunks are
    # solution/rubric material, and downstream reconciliation will pick up the
    # concrete answer mode from the explicit cue.
    if SOLUTION_EXPLICIT_VALUE_RE.search(normalized):
        return "unknown", 0.58, {"option_count": option_count}
    if option_count >= 4:
        return "single_choice", 0.90, {"option_count": option_count}
    if ESSAY_RE.search(normalized) and len(normalized) >= 180:
        return "essay", 0.74, {"option_count": option_count}
    return "unknown", 0.56, {"option_count": option_count}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def parse_html_structure(html_text: str) -> Dict[str, object]:
    line_starts = build_line_starts(html_text)
    blocks: List[HtmlBlock] = []
    current_exam = "DE_UNKNOWN"

    for block_index, match in enumerate(BLOCK_RE.finditer(html_text)):
        chunk = match.group(0)
        text = normalize_visible_text(chunk)
        line = offset_to_line(line_starts, match.start())
        exam_match = EXAM_HEADER_RE.match(text)
        if exam_match:
            current_exam = f"DE_{int(exam_match.group(1))}"
        blocks.append(
            HtmlBlock(
                block_index=block_index,
                tag_name=match.group(1).lower(),
                start=match.start(),
                end=match.end(),
                line=line,
                exam_id=current_exam,
                html=chunk,
                text=text,
            )
        )

    # English exams often encode multiple "Question n" choice items inside a single table
    # (one row per question). We do a narrow structural split so segmentation can find
    # those questions without enabling Vietnamese "Câu n" starts from tables.
    def split_english_question_tables(blocks_in: List[HtmlBlock]) -> List[HtmlBlock]:
        expanded: List[HtmlBlock] = []
        for block in blocks_in:
            if block.tag_name != "table":
                expanded.append(block)
                continue
            if not block.text or "question" not in block.text.lower():
                expanded.append(block)
                continue
            # Keep Vietnamese tables intact (answer keys, rubric tables, etc.).
            if re.search(r"(?iu)\bcâu\s*\d{1,3}\b", _normalize_question_header_candidate(block.text)):
                expanded.append(block)
                continue

            row_blocks: List[HtmlBlock] = []
            for row_match in TABLE_ROW_RE.finditer(block.html):
                tr_html = row_match.group(0)
                first_cell = TABLE_CELL_RE.search(tr_html)
                if not first_cell:
                    continue
                first_text = normalize_visible_text(first_cell.group(1))
                if not EN_QUESTION_HEADER_RE.match(_normalize_question_header_candidate(first_text)):
                    continue

                row_text = normalize_visible_text(tr_html)
                # Require A/B/C/D markers to avoid splitting unrelated "Question n" tables.
                if len(set(OPTION_MARKER_RE.findall(row_text))) < 3:
                    continue

                row_table_html = f'<table class="docx-table">{tr_html}</table>'
                row_blocks.append(
                    HtmlBlock(
                        block_index=block.block_index,
                        tag_name="table",
                        start=block.start,
                        end=block.end,
                        line=block.line,
                        exam_id=block.exam_id,
                        html=row_table_html,
                        text=normalize_visible_text(row_table_html),
                    )
                )

            if len(row_blocks) >= 2:
                expanded.extend(row_blocks)
            else:
                expanded.append(block)

        # Re-index to keep block_index stable and unique after expansion.
        for idx, block in enumerate(expanded):
            block.block_index = idx
        return expanded

    blocks = split_english_question_tables(blocks)

    def split_embedded_english_question_paragraphs(blocks_in: List[HtmlBlock]) -> List[HtmlBlock]:
        expanded: List[HtmlBlock] = []
        for block in blocks_in:
            if block.tag_name not in {"p", "div"}:
                expanded.append(block)
                continue
            if not block.text or "question" not in block.text.lower():
                expanded.append(block)
                continue
            if EN_QUESTION_HEADER_RE.match(_normalize_question_header_candidate(block.text)):
                expanded.append(block)
                continue
            # Avoid rewriting rich HTML blocks (math, spans, images, tables).
            if re.search(r"(?is)<\s*(?:span|math|img|table|figure|div)\b", block.html):
                expanded.append(block)
                continue

            text = block.text
            # Split when an embedded "Question n." marker appears inside an otherwise plain paragraph.
            # Require punctuation after the number to avoid matching incidental mentions like "question 1".
            inline_match = re.search(r"(?iu)(?<=\s)question\s*(\d{1,3})\s*[\.\):]", text)
            if not inline_match:
                expanded.append(block)
                continue
            prefix_probe = text[: inline_match.start()]
            if len(set(OPTION_MARKER_RE.findall(prefix_probe))) < 2 and len(_normalize_space(prefix_probe)) < 80:
                expanded.append(block)
                continue

            prefix = _normalize_space(text[: inline_match.start()])
            suffix = _normalize_space(text[inline_match.start() :])
            if prefix:
                expanded.append(
                    HtmlBlock(
                        block_index=block.block_index,
                        tag_name="p",
                        start=block.start,
                        end=block.end,
                        line=block.line,
                        exam_id=block.exam_id,
                        html=f"<p>{html.escape(prefix)}</p>",
                        text=prefix,
                    )
                )
            expanded.append(
                HtmlBlock(
                    block_index=block.block_index,
                    tag_name="p",
                    start=block.start,
                    end=block.end,
                    line=block.line,
                    exam_id=block.exam_id,
                    html=f"<p>{html.escape(suffix)}</p>",
                    text=suffix,
                )
            )

        for idx, block in enumerate(expanded):
            block.block_index = idx
        return expanded

    blocks = split_embedded_english_question_paragraphs(blocks)

    question_starts: List[Tuple[int, str, int, int]] = []
    start_counter: Dict[Tuple[str, int], int] = {}

    # Once we enter an end-key/answer appendix zone for an exam, do not treat subsequent
    # "Question n"/"Câu n" headers as new question blocks. This prevents answer keys and
    # detailed explanations from duplicating question segmentation.
    answer_zone_active_by_exam: set[str] = set()
    english_mode = (
        sum(
            1
            for block in blocks
            if block.text and EN_QUESTION_HEADER_RE.match(_normalize_question_header_candidate(block.text))
        )
        >= 4
    )

    for block in blocks:
        text = block.text
        if not text:
            continue
        normalized_question_header_text = _normalize_question_header_candidate(text)
        if english_mode and _is_answer_zone_heading(text):
            answer_zone_active_by_exam.add(block.exam_id)
            continue
        if english_mode and block.exam_id in answer_zone_active_by_exam:
            continue
        if block.tag_name == "table" and not EN_QUESTION_HEADER_RE.match(normalized_question_header_text):
            continue
        if QUESTION_RANGE_RE.search(normalized_question_header_text):
            continue
        m = QUESTION_HEADER_RE.match(normalized_question_header_text)
        if not m:
            continue
        qn = int(m.group(1))
        key = (block.exam_id, qn)
        start_counter[key] = start_counter.get(key, 0) + 1
        question_starts.append((block.block_index, block.exam_id, qn, block.line))

    warnings: List[ParserWarning] = []
    questions: List[ParsedQuestion] = []
    covered_block_indexes: set[int] = set()

    for idx, (start_block_index, exam_id, question_number, start_line) in enumerate(question_starts):
        if idx + 1 < len(question_starts):
            end_block_index = question_starts[idx + 1][0] - 1
        else:
            end_block_index = len(blocks) - 1
        if end_block_index < start_block_index:
            end_block_index = start_block_index

        chunk_blocks = blocks[start_block_index:end_block_index + 1]
        for block in chunk_blocks:
            covered_block_indexes.add(block.block_index)
        chunk_html = "".join(block.html for block in chunk_blocks)
        chunk_text = re.sub(r"\s+", " ", " ".join(block.text for block in chunk_blocks if block.text)).strip()

        item_id = f"{exam_id}-Q{question_number:03d}-{idx + 1:02d}"
        assets = extract_assets(chunk_html, item_id)
        math_fragments = extract_math_fragments(chunk_html, item_id)
        question_type_text = _question_type_probe_text(chunk_text)
        question_type, base_confidence, signals = infer_question_type(question_type_text)

        confidence = base_confidence
        if assets:
            confidence += 0.03
        if math_fragments:
            confidence += 0.03
        if len(chunk_text) < 24:
            confidence -= 0.10
        if question_type == "unknown":
            confidence -= 0.06
        if signals.get("option_count", 0) >= 2 and question_type not in {"single_choice", "multiple_choice"}:
            confidence -= 0.08

        key = (exam_id, question_number)
        duplicate = start_counter.get(key, 0) > 1
        if duplicate:
            confidence -= 0.20
            warnings.append(
                ParserWarning(
                    severity="warning",
                    code="duplicate_question_number",
                    message=f"Duplicate question number {question_number} in {exam_id}",
                    exam_id=exam_id,
                    question_id=item_id,
                    line=start_line,
                )
            )

        if question_type == "unknown":
            warnings.append(
                ParserWarning(
                    severity="info",
                    code="unknown_question_type",
                    message="Question type could not be inferred confidently",
                    exam_id=exam_id,
                    question_id=item_id,
                    line=start_line,
                )
            )

        confidence = round(clamp(confidence, 0.05, 0.99), 3)
        if confidence < 0.60:
            warnings.append(
                ParserWarning(
                    severity="warning",
                    code="low_parse_confidence",
                    message=f"Low parser confidence ({confidence:.3f})",
                    exam_id=exam_id,
                    question_id=item_id,
                    line=start_line,
                )
            )

        question_warning_codes = sorted({w.code for w in warnings if w.question_id == item_id})
        questions.append(
            ParsedQuestion(
                item_id=item_id,
                exam_id=exam_id,
                question_number=question_number,
                start_block_index=start_block_index,
                end_block_index=end_block_index,
                start_line=start_line,
                prompt_preview=chunk_text[:260],
                question_type=question_type,
                parse_confidence=confidence,
                warning_codes=question_warning_codes,
                warnings=[w for w in warnings if w.question_id == item_id],
                assets=assets,
                math_fragments=math_fragments,
                text_content=chunk_text,
                html_content=chunk_html,
                block_texts=[block.text for block in chunk_blocks if block.text],
            )
        )

    orphan_asset_count = 0
    orphan_math_count = 0
    for block in blocks:
        if block.block_index in covered_block_indexes:
            continue
        if not block.html.strip():
            continue
        asset_matches = list(IMG_TAG_RE.finditer(block.html))
        math_matches = list(MATH_FRAGMENT_RE.finditer(block.html))
        if asset_matches:
            orphan_asset_count += len(asset_matches)
            warnings.append(
                ParserWarning(
                    severity="info",
                    code="orphan_assets_outside_question",
                    message=f"{len(asset_matches)} asset(s) detected outside question blocks",
                    exam_id=block.exam_id,
                    question_id="",
                    line=block.line,
                )
            )
        if math_matches:
            orphan_math_count += len(math_matches)
            warnings.append(
                ParserWarning(
                    severity="info",
                    code="orphan_math_outside_question",
                    message=f"{len(math_matches)} math fragment(s) detected outside question blocks",
                    exam_id=block.exam_id,
                    question_id="",
                    line=block.line,
                )
            )

    sections: Dict[str, Dict[str, object]] = {}
    for q in questions:
        section = sections.setdefault(
            q.exam_id,
            {
                "exam_id": q.exam_id,
                "question_count": 0,
                "asset_count": 0,
                "math_fragment_count": 0,
                "warning_count": 0,
                "avg_confidence": 0.0,
                "question_ids": [],
            },
        )
        section["question_count"] += 1
        section["asset_count"] += len(q.assets)
        section["math_fragment_count"] += len(q.math_fragments)
        section["warning_count"] += len(q.warning_codes)
        section["question_ids"].append(q.item_id)

    for exam_id, section in sections.items():
        confidences = [q.parse_confidence for q in questions if q.exam_id == exam_id]
        section["avg_confidence"] = round(mean(confidences), 3) if confidences else 0.0

    if not sections:
        sections["DE_UNKNOWN"] = {
            "exam_id": "DE_UNKNOWN",
            "question_count": 0,
            "asset_count": 0,
            "math_fragment_count": 0,
            "warning_count": 1,
            "avg_confidence": 0.0,
            "question_ids": [],
        }
        warnings.append(
            ParserWarning(
                severity="warning",
                code="no_questions_detected",
                message="No question headers were detected in HTML output",
                exam_id="DE_UNKNOWN",
                question_id="",
                line=1,
            )
        )

    questions.sort(
        key=lambda q: (
            exam_sort_key(q.exam_id),
            q.question_number,
            q.start_line,
            q.item_id,
        )
    )

    for exam_id, section in sections.items():
        if section["question_count"] == 0:
            warnings.append(
                ParserWarning(
                    severity="warning",
                    code="empty_exam_section",
                    message=f"Section {exam_id} has no parsed questions",
                    exam_id=exam_id,
                    question_id="",
                    line=1,
                )
            )

    all_assets = sum(len(q.assets) for q in questions)
    all_math = sum(len(q.math_fragments) for q in questions)
    confidences = [q.parse_confidence for q in questions]

    confidence_histogram = {
        "ge_0_9": 0,
        "0_75_to_0_9": 0,
        "0_6_to_0_75": 0,
        "lt_0_6": 0,
    }
    for score in confidences:
        if score >= 0.90:
            confidence_histogram["ge_0_9"] += 1
        elif score >= 0.75:
            confidence_histogram["0_75_to_0_9"] += 1
        elif score >= 0.60:
            confidence_histogram["0_6_to_0_75"] += 1
        else:
            confidence_histogram["lt_0_6"] += 1

    summary = {
        "sections_count": len(sections),
        "question_count": len(questions),
        "asset_count": all_assets,
        "math_fragment_count": all_math,
        "orphan_asset_count": orphan_asset_count,
        "orphan_math_fragment_count": orphan_math_count,
        "avg_confidence": round(mean(confidences), 3) if confidences else 0.0,
        "min_confidence": min(confidences) if confidences else 0.0,
        "unknown_question_type_count": sum(1 for q in questions if q.question_type == "unknown"),
        "warning_count": len(warnings),
        "parser_support_packages": dict(PARSER_SUPPORT_PACKAGES),
    }

    warnings_sorted = sorted(
        warnings,
        key=lambda w: (exam_sort_key(w.exam_id), w.question_id, w.line, w.code, w.message),
    )

    return {
        "blocks": blocks,
        "sections": [sections[key] for key in sorted(sections.keys(), key=exam_sort_key)],
        "questions": questions,
        "summary": summary,
        "confidence_histogram": confidence_histogram,
        "warnings": warnings_sorted,
    }


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def _normalize_question_header_candidate(value: str) -> str:
    normalized = _normalize_space(value)
    if not normalized:
        return ""
    normalized = QUESTION_DECORATIVE_PREFIX_RE.sub("", normalized)
    return _normalize_space(normalized)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_choice_value(value: str) -> Optional[str]:
    token = _normalize_space(value).upper()
    if token in {"A", "B", "C", "D"}:
        return token
    return None


def _normalize_boolean_value(value: str) -> Optional[bool]:
    token = _normalize_space(value).lower().strip(".:;")
    if token in {"đ", "đúng", "d", "t", "true"}:
        return True
    if token in {"s", "sai", "f", "false"}:
        return False
    return None


def _normalize_short_answer_value(value: str) -> Dict[str, str]:
    raw = _normalize_space(value)
    raw = raw.strip(" .;:")
    raw = re.split(r"(?iu)\b(?:câu|đ/a|đáp\s*án|ý\s*/\s*câu)\b", raw, maxsplit=1)[0].strip()
    numeric_prefix = re.match(r"^[+\-−]?\d+(?:[\.,]\d+)?", raw)
    if numeric_prefix and len(raw) > len(numeric_prefix.group(0)):
        remainder = raw[len(numeric_prefix.group(0)):].strip()
        if not remainder or remainder[0] in {"%", "°"}:
            raw = numeric_prefix.group(0) + remainder
    normalized = raw
    if re.fullmatch(r"[+\-−]?\d+(?:[\.,]\d+)?(?:\s*[%°])?", raw):
        normalized = raw.replace("−", "-").replace(",", ".")
    normalized = _normalize_space(normalized)
    return {"raw": raw, "normalized": normalized}


def _normalize_boolean_group_compact_value(value: str) -> Optional[Dict[str, bool]]:
    token = unicodedata.normalize("NFKC", _normalize_space(value)).upper().replace("Đ", "D")
    token = re.sub(r"[^A-Z0-9]+", "", token)
    if len(token) != 4:
        return None

    mapping: Dict[str, bool] = {}
    for idx, label in enumerate(("a", "b", "c", "d")):
        char = token[idx]
        if char in {"D", "T", "1", "+"}:
            mapping[label] = True
        elif char in {"S", "F", "0", "-"}:
            mapping[label] = False
        else:
            return None
    return mapping


def _extract_boolean_group_from_text(value: str) -> Optional[Dict[str, bool]]:
    text = _normalize_space(value)
    if not text:
        return None

    prefix_match = re.search(
        r"(?iu)\b(?:đáp\s*(?:án|án|số)|đs|trả\s*lời)\b\s*[:：.]?\s*(.*)$",
        text,
    )
    if prefix_match:
        text = _normalize_space(prefix_match.group(1))

    tokens: List[bool] = []
    for match in BOOLEAN_GROUP_TOKEN_RE.finditer(text):
        boolean_value = _normalize_boolean_value(match.group(0))
        if boolean_value is None:
            continue
        tokens.append(boolean_value)
        if len(tokens) == 4:
            return {label: tokens[idx] for idx, label in enumerate(("a", "b", "c", "d"))}

    compact = _normalize_boolean_group_compact_value(text)
    if compact is not None:
        return compact
    return None


def _extract_true_false_group_from_table_html(fragment_html: str) -> Optional[Dict[str, bool]]:
    root = _parse_html_fragment_dom(fragment_html)
    if root is None:
        return None

    if getattr(root, "tag", "").lower() == "table":
        tables = [root]
    else:
        try:
            tables = list(root.xpath(".//table"))
        except Exception:
            tables = []

    for table in tables:
        rows = _extract_table_rows(_dom_element_html(table))
        if not rows:
            continue

        header = [_normalize_space(cell).lower() for cell in rows[0]]
        has_truth_header = any("đúng" in cell for cell in header)
        has_false_header = any("sai" in cell for cell in header)
        if not (has_truth_header and has_false_header):
            continue

        subanswers: Dict[str, bool] = {}
        for row in rows[1:]:
            if not row:
                continue
            label_match = re.search(r"(?iu)\b([abcd])\)", row[0]) or re.search(r"(?iu)^\s*([abcd])\b", row[0])
            if not label_match:
                continue
            label = label_match.group(1).lower()
            for cell in row[1:]:
                boolean_value = _normalize_boolean_value(cell)
                if boolean_value is not None:
                    subanswers[label] = boolean_value
                    break

        if subanswers:
            return dict(sorted(subanswers.items(), key=lambda kv: kv[0]))

    return None


def _question_type_probe_text(chunk_text: str) -> str:
    text = _normalize_space(chunk_text)
    if not text:
        return text
    cutoff = len(text)
    for match in QUESTION_TYPE_APPENDIX_RE.finditer(text):
        if match.start() >= 40 and match.start() < cutoff:
            cutoff = match.start()
    return text[:cutoff].strip()


def _parse_question_number(value: str) -> Optional[str]:
    m = re.search(r"(?iu)\b(\d{1,3})\b", value or "")
    if not m:
        return None
    return str(int(m.group(1)))


def _build_answer_issue(
    *,
    code: str,
    severity: str,
    message: str,
    exam_id: str = "DE_UNKNOWN",
    question_id: str = "",
    line: int = 1,
    stage: str = "",
) -> Dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "exam_id": exam_id,
        "question_id": question_id,
        "line": int(line or 1),
        "stage": stage,
    }


def _extract_table_cells(table_html: str) -> List[List[str]]:
    return _extract_table_rows(table_html)


def _extract_rubric_table_signals(table_html: str) -> Dict[str, Any]:
    rows = _extract_table_cells(table_html)
    if not rows:
        return {}

    flattened = [cell for row in rows for cell in row if cell]
    lowered = [cell.lower() for cell in flattened]
    has_hdc = any("hướng dẫn chấm" in cell for cell in lowered)
    has_nội_dung = any(cell == "nội dung" for cell in lowered)
    has_điểm = any(cell == "điểm" for cell in lowered)
    has_thang_diem = any("thang điểm" in cell for cell in lowered)

    scoring_rows: List[str] = []
    for row in rows:
        row_text = _normalize_space(" ".join(row))
        if not row_text:
            continue
        if re.search(r"(?iu)\b\d+(?:[.,]\d+)?\s*điểm\b", row_text) or re.fullmatch(r"(?iu)\d+(?:[.,]\d+)?", row_text):
            scoring_rows.append(row_text)

    if not (has_hdc or has_thang_diem or (has_nội_dung and has_điểm and len(rows) >= 2) or len(scoring_rows) >= 2):
        return {}

    cues: List[str] = []
    if has_hdc:
        cues.append("table_cell:hướng_dẫn_chấm")
    if has_nội_dung and has_điểm:
        cues.append("table_cells:nội_dung+điểm")
    if has_thang_diem:
        cues.append("table_cell:thang_điểm")
    if scoring_rows:
        cues.append(f"table_scoring_rows:{len(scoring_rows)}")

    confidence = 0.68
    if has_hdc:
        confidence += 0.16
    if has_thang_diem:
        confidence += 0.10
    if has_nội_dung and has_điểm and len(rows) >= 2:
        confidence += 0.12
    if len(scoring_rows) >= 2:
        confidence += min(0.08, 0.02 * len(scoring_rows))

    return {
        "rows": rows,
        "cues": cues,
        "confidence": round(clamp(confidence, 0.0, 0.96), 3),
        "has_columns": has_nội_dung and has_điểm,
        "scoring_rows": scoring_rows,
    }


def _extract_answer_summary_from_table(block: HtmlBlock) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str], float]:
    entries: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []
    source_cues: List[str] = []
    confidence = 0.0

    rows = _extract_table_cells(block.html)
    if not rows:
        return entries, issues, source_cues, confidence

    packed_cells: List[Tuple[str, str, Dict[str, Any]]] = []
    packed_grid_only = True
    for row in rows:
        for cell in row:
            normalized = _normalize_space(cell)
            if not normalized:
                continue
            packed = _parse_packed_summary_cell(normalized)
            if packed is None:
                packed_grid_only = False
                break
            packed_cells.append((str(packed[0]), normalized, packed[1]))
        if not packed_grid_only:
            break

    if packed_grid_only and len(packed_cells) >= 3:
        for qnum, _raw, payload in packed_cells:
            entries.append({"exam_id": block.exam_id, "question_number": qnum, **payload})
        source_cues.append("table:packed-grid")
        confidence = 0.93
        deduped: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for entry in entries:
            key = (str(entry.get("exam_id", "DE_UNKNOWN")), str(entry.get("question_number", "")), str(entry.get("mode", "")))
            if key in deduped:
                issues.append(
                    _build_answer_issue(
                        code="answer_summary_duplicate_question_number",
                        severity="warning",
                        message=f"Duplicate summary entry for question {key[1]} ({key[2]})",
                        exam_id=block.exam_id,
                        line=block.line,
                        stage="answer_summary_extraction",
                    )
                )
                continue
            deduped[key] = entry
        return list(deduped.values()), issues, source_cues, confidence

    for row in rows:
        if len(row) != 1:
            continue
        packed = _parse_packed_summary_cell(row[0])
        if not packed:
            continue
        qnum, payload = packed
        entries.append({"exam_id": block.exam_id, "question_number": qnum, **payload})
        source_cues.append("table:packed-answer-cell")
        confidence = max(confidence, 0.89)

    grid_qnums = [_parse_question_number(cell) for cell in rows[0]]
    if len(rows) >= 2 and len(grid_qnums) >= 3 and all(grid_qnums):
        answer_row = rows[1]
        if len(answer_row) != len(grid_qnums):
            issues.append(
                _build_answer_issue(
                    code="answer_summary_table_shape_unexpected",
                    severity="warning",
                    message="Grid-style answer table has mismatched question/answer columns",
                    exam_id=block.exam_id,
                    line=block.line,
                    stage="answer_summary_extraction",
                )
            )
        limit = min(len(grid_qnums), len(answer_row))
        grid_entries: List[Dict[str, Any]] = []
        for idx in range(limit):
            qnum = grid_qnums[idx]
            value = _normalize_space(answer_row[idx])
            if not qnum or not value:
                continue
            packed = _parse_packed_summary_cell(value)
            if packed is not None:
                packed_qnum, payload = packed
                if packed_qnum == qnum:
                    grid_entries.append({"exam_id": block.exam_id, "question_number": qnum, **payload})
                    continue
            compact_boolean = _normalize_boolean_group_compact_value(value)
            choice = _normalize_choice_value(value)
            boolean_value = _normalize_boolean_value(value)
            if compact_boolean is not None:
                grid_entries.append(
                    {
                        "exam_id": block.exam_id,
                        "question_number": qnum,
                        "mode": "boolean_group",
                        "subanswers": dict(sorted(compact_boolean.items(), key=lambda kv: kv[0])),
                    }
                )
                continue
            if choice is not None:
                grid_entries.append(
                    {
                        "exam_id": block.exam_id,
                        "question_number": qnum,
                        "mode": "single_choice",
                        "value": choice,
                    }
                )
                continue
            if boolean_value is not None:
                grid_entries.append(
                    {
                        "exam_id": block.exam_id,
                        "question_number": qnum,
                        "mode": "boolean_group",
                        "subanswers": {"a": boolean_value},
                    }
                )
                continue
            short_value = _normalize_short_answer_value(value)
            if short_value["normalized"]:
                grid_entries.append(
                    {
                        "exam_id": block.exam_id,
                        "question_number": qnum,
                        "mode": "short_answer",
                        "accepted_answers": [short_value],
                    }
                )
                continue
            issues.append(
                _build_answer_issue(
                    code="answer_summary_unknown_answer_mode",
                    severity="warning",
                    message=f"Could not classify grid summary value '{value}' for question {qnum}",
                    exam_id=block.exam_id,
                    line=block.line,
                    stage="answer_summary_extraction",
                )
            )
        if grid_entries:
            entries.extend(grid_entries)
            source_cues.append("table:grid-answers")
            confidence = max(confidence, 0.93)

    first_cell = rows[0][0].lower() if rows and rows[0] else ""
    has_cau_header = "câu" in first_cell
    has_y_cau_header = "ý" in first_cell and any("câu" in cell.lower() for cell in rows[0][1:])

    # Boolean matrix style:
    # | Ý/Câu | Câu 1 | Câu 2 |
    # | a)    | Đ     | S     |
    if has_y_cau_header and len(rows) >= 2:
        question_headers = rows[0][1:]
        qnums = [_parse_question_number(cell) for cell in question_headers]
        if not all(qnums):
            issues.append(
                _build_answer_issue(
                    code="answer_summary_table_shape_unexpected",
                    severity="warning",
                    message="Boolean summary table has invalid question header mapping",
                    exam_id=block.exam_id,
                    line=block.line,
                    stage="answer_summary_extraction",
                )
            )
        else:
            by_question: Dict[str, Dict[str, bool]] = {str(q): {} for q in qnums if q}
            for row in rows[1:]:
                if not row:
                    continue
                label_match = re.search(r"(?iu)\b([abcd])\)", row[0]) or re.search(r"(?iu)\b([abcd])\b", row[0])
                if not label_match:
                    continue
                label = label_match.group(1).lower()
                for idx, qnum in enumerate(qnums):
                    if not qnum:
                        continue
                    if idx + 1 >= len(row):
                        issues.append(
                            _build_answer_issue(
                                code="answer_summary_short_answer_span_ambiguous",
                                severity="warning",
                                message=f"Missing boolean cell for question {qnum} label {label}",
                                exam_id=block.exam_id,
                                line=block.line,
                                stage="answer_summary_extraction",
                            )
                        )
                        continue
                    boolean_value = _normalize_boolean_value(row[idx + 1])
                    if boolean_value is None:
                        issues.append(
                            _build_answer_issue(
                                code="answer_summary_boolean_value_invalid",
                                severity="warning",
                                message=f"Invalid boolean summary value '{row[idx + 1]}' for question {qnum}/{label}",
                                exam_id=block.exam_id,
                                line=block.line,
                                stage="answer_summary_extraction",
                            )
                        )
                        continue
                    by_question[str(qnum)][label] = boolean_value
            for qnum, subanswers in sorted(by_question.items(), key=lambda kv: int(kv[0])):
                if not subanswers:
                    continue
                entries.append(
                    {
                        "exam_id": block.exam_id,
                        "question_number": qnum,
                        "mode": "boolean_group",
                        "subanswers": dict(sorted(subanswers.items(), key=lambda kv: kv[0])),
                    }
                )
            if entries:
                source_cues.append("table:boolean-matrix")
                confidence = max(confidence, 0.94)

    # Pivot style:
    # | Câu | 1 | 2 |
    # | Đ/A | A | C |
    if has_cau_header and len(rows) >= 2 and rows[0] and rows[1]:
        second_header = rows[1][0].lower()
        if any(token in second_header for token in ("đ/a", "đáp án", "da")):
            question_cells = rows[0][1:]
            answer_cells = rows[1][1:]
            choice_like_count = sum(1 for cell in answer_cells if _normalize_choice_value(cell) is not None)
            expected_choice_mode = choice_like_count >= max(1, len(answer_cells) // 2)
            if len(question_cells) != len(answer_cells):
                issues.append(
                    _build_answer_issue(
                        code="answer_summary_table_shape_unexpected",
                        severity="warning",
                        message="Answer summary table has mismatched question/answer columns",
                        exam_id=block.exam_id,
                        line=block.line,
                        stage="answer_summary_extraction",
                    )
                )
            limit = min(len(question_cells), len(answer_cells))
            for idx in range(limit):
                qnum = _parse_question_number(question_cells[idx])
                value = answer_cells[idx]
                if not qnum:
                    issues.append(
                        _build_answer_issue(
                            code="answer_summary_question_reference_unknown",
                            severity="warning",
                            message=f"Cannot parse question number from summary cell '{question_cells[idx]}'",
                            exam_id=block.exam_id,
                            line=block.line,
                            stage="answer_summary_extraction",
                        )
                    )
                    continue
                packed = _parse_packed_summary_cell(value)
                if packed is not None:
                    packed_qnum, payload = packed
                    if packed_qnum == qnum:
                        entries.append({"exam_id": block.exam_id, "question_number": qnum, **payload})
                        continue
                choice = _normalize_choice_value(value)
                if choice is not None:
                    entries.append(
                        {
                            "exam_id": block.exam_id,
                            "question_number": qnum,
                            "mode": "single_choice",
                            "value": choice,
                        }
                    )
                    continue
                if expected_choice_mode:
                    issues.append(
                        _build_answer_issue(
                            code="answer_summary_choice_value_invalid",
                            severity="warning",
                            message=f"Invalid choice value '{value}' for question {qnum}",
                            exam_id=block.exam_id,
                            line=block.line,
                            stage="answer_summary_extraction",
                        )
                    )
                    continue
                boolean_value = _normalize_boolean_value(value)
                if boolean_value is not None:
                    entries.append(
                        {
                            "exam_id": block.exam_id,
                            "question_number": qnum,
                            "mode": "boolean_group",
                            "subanswers": {"a": boolean_value},
                        }
                    )
                    continue
                if _normalize_space(value):
                    entries.append(
                        {
                            "exam_id": block.exam_id,
                            "question_number": qnum,
                            "mode": "short_answer",
                            "accepted_answers": [_normalize_short_answer_value(value)],
                        }
                    )
                elif _normalize_space(value):
                    issues.append(
                        _build_answer_issue(
                            code="answer_summary_unknown_answer_mode",
                            severity="warning",
                            message=f"Could not classify summary value '{value}' for question {qnum}",
                            exam_id=block.exam_id,
                            line=block.line,
                            stage="answer_summary_extraction",
                        )
                    )
                else:
                    issues.append(
                        _build_answer_issue(
                            code="answer_summary_entry_parse_failed",
                            severity="warning",
                            message=f"Empty summary value for question {qnum}",
                            exam_id=block.exam_id,
                            line=block.line,
                            stage="answer_summary_extraction",
                        )
                    )
            if entries:
                source_cues.append("table:question-answer-pivot")
                confidence = max(confidence, 0.95)

    handled_question_answer_rows = False

    # Row style (two-pair / 4-column):
    # | Câu | Đáp án | Câu | Đáp án |
    # | 1   | C      | 10  | A      |
    if len(rows) >= 2 and len(rows[0]) >= 4:
        header_a = rows[0][0].lower()
        header_b = rows[0][1].lower()
        header_c = rows[0][2].lower()
        header_d = rows[0][3].lower()
        if (
            "câu" in header_a
            and "câu" in header_c
            and any(token in header_b for token in ("đáp án", "đ/a", "da"))
            and any(token in header_d for token in ("đáp án", "đ/a", "da"))
        ):
            # If the table "looks like" a choice key, do not coerce non-choice values into short answers.
            answer_values: List[str] = []
            for row in rows[1:]:
                if len(row) >= 2:
                    answer_values.append(row[1])
                if len(row) >= 4:
                    answer_values.append(row[3])
            choice_like_count = sum(1 for cell in answer_values if _normalize_choice_value(cell) is not None)
            expected_choice_mode = choice_like_count >= max(1, len(answer_values) // 2)

            for row in rows[1:]:
                for qcol, vcol in ((0, 1), (2, 3)):
                    if len(row) <= vcol:
                        continue
                    qnum = _parse_question_number(row[qcol])
                    if not qnum:
                        issues.append(
                            _build_answer_issue(
                                code="answer_summary_question_reference_unknown",
                                severity="warning",
                                message=f"Cannot parse question number from row '{row[qcol]}'",
                                exam_id=block.exam_id,
                                line=block.line,
                                stage="answer_summary_extraction",
                            )
                        )
                        continue

                    value = row[vcol]
                    packed = _parse_packed_summary_cell(value)
                    if packed is not None:
                        packed_qnum, payload = packed
                        if packed_qnum == qnum:
                            entries.append({"exam_id": block.exam_id, "question_number": qnum, **payload})
                            continue

                    choice = _normalize_choice_value(value)
                    if choice is not None:
                        entries.append(
                            {
                                "exam_id": block.exam_id,
                                "question_number": qnum,
                                "mode": "single_choice",
                                "value": choice,
                            }
                        )
                        continue

                    if expected_choice_mode:
                        normalized = _normalize_space(value)
                        if normalized:
                            issues.append(
                                _build_answer_issue(
                                    code="answer_summary_choice_value_invalid",
                                    severity="warning",
                                    message=f"Invalid choice value '{value}' for question {qnum}",
                                    exam_id=block.exam_id,
                                    line=block.line,
                                    stage="answer_summary_extraction",
                                )
                            )
                        else:
                            issues.append(
                                _build_answer_issue(
                                    code="answer_summary_entry_parse_failed",
                                    severity="warning",
                                    message=f"Empty summary value for question {qnum}",
                                    exam_id=block.exam_id,
                                    line=block.line,
                                    stage="answer_summary_extraction",
                                )
                            )
                        continue

                    boolean_value = _normalize_boolean_value(value)
                    if boolean_value is not None:
                        entries.append(
                            {
                                "exam_id": block.exam_id,
                                "question_number": qnum,
                                "mode": "boolean_group",
                                "subanswers": {"a": boolean_value},
                            }
                        )
                        continue

                    if _normalize_space(value):
                        entries.append(
                            {
                                "exam_id": block.exam_id,
                                "question_number": qnum,
                                "mode": "short_answer",
                                "accepted_answers": [_normalize_short_answer_value(value)],
                            }
                        )
                    else:
                        issues.append(
                            _build_answer_issue(
                                code="answer_summary_entry_parse_failed",
                                severity="warning",
                                message=f"Empty short-answer summary value for question {qnum}",
                                exam_id=block.exam_id,
                                line=block.line,
                                stage="answer_summary_extraction",
                            )
                        )

            if entries:
                source_cues.append("table:question-answer-rows-two-pair")
                confidence = max(confidence, 0.93)
                handled_question_answer_rows = True

    # Row style:
    # | Câu | Đáp án |
    # | 1   | 12,5 |
    if not handled_question_answer_rows and len(rows) >= 2 and len(rows[0]) >= 2:
        header_a = rows[0][0].lower()
        header_b = rows[0][1].lower()
        if "câu" in header_a and any(token in header_b for token in ("đáp án", "đ/a", "da")):
            for row in rows[1:]:
                if len(row) < 2:
                    continue
                qnum = _parse_question_number(row[0])
                if not qnum:
                    issues.append(
                        _build_answer_issue(
                            code="answer_summary_question_reference_unknown",
                            severity="warning",
                            message=f"Cannot parse question number from row '{row[0]}'",
                            exam_id=block.exam_id,
                            line=block.line,
                            stage="answer_summary_extraction",
                        )
                    )
                    continue
                value = row[1]
                packed = _parse_packed_summary_cell(value)
                if packed is not None:
                    packed_qnum, payload = packed
                    if packed_qnum == qnum:
                        entries.append({"exam_id": block.exam_id, "question_number": qnum, **payload})
                        continue
                choice = _normalize_choice_value(value)
                if choice is not None:
                    entries.append(
                        {
                            "exam_id": block.exam_id,
                            "question_number": qnum,
                            "mode": "single_choice",
                            "value": choice,
                        }
                    )
                    continue
                boolean_value = _normalize_boolean_value(value)
                if boolean_value is not None:
                    entries.append(
                        {
                            "exam_id": block.exam_id,
                            "question_number": qnum,
                            "mode": "boolean_group",
                            "subanswers": {"a": boolean_value},
                        }
                    )
                    continue
                if _normalize_space(value):
                    entries.append(
                        {
                            "exam_id": block.exam_id,
                            "question_number": qnum,
                            "mode": "short_answer",
                            "accepted_answers": [_normalize_short_answer_value(value)],
                        }
                    )
                else:
                    issues.append(
                        _build_answer_issue(
                            code="answer_summary_entry_parse_failed",
                            severity="warning",
                            message=f"Empty short-answer summary value for question {qnum}",
                            exam_id=block.exam_id,
                            line=block.line,
                            stage="answer_summary_extraction",
                        )
                    )
            if entries:
                source_cues.append("table:question-answer-rows")
                confidence = max(confidence, 0.92)

    # De-duplicate entries (table parser can hit multiple branches in irregular inputs)
    deduped: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for entry in entries:
        key = (str(entry.get("exam_id", "DE_UNKNOWN")), str(entry.get("question_number", "")), str(entry.get("mode", "")))
        if key in deduped:
            issues.append(
                _build_answer_issue(
                    code="answer_summary_duplicate_question_number",
                    severity="warning",
                    message=f"Duplicate summary entry for question {key[1]} ({key[2]})",
                    exam_id=block.exam_id,
                    line=block.line,
                    stage="answer_summary_extraction",
                )
            )
            continue
        deduped[key] = entry

    return list(deduped.values()), issues, source_cues, confidence


def _extract_answer_summary_list_candidates(blocks: List[HtmlBlock]) -> Tuple[List[Dict[str, Any]], List[str], float]:
    entries: List[Dict[str, Any]] = []
    cues: List[str] = []
    confidence = 0.0
    heading_indexes = [block.block_index for block in blocks if _is_answer_zone_heading(block.text)]
    if heading_indexes:
        candidate_blocks = [block for block in blocks if block.block_index > min(heading_indexes)]
        cues.append("heading:answer-summary")
    else:
        candidate_blocks = [
            block
            for block in blocks
            if block.tag_name in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6"}
        ]

    grouped: List[Tuple[int, HtmlBlock, str, str]] = []
    for block in candidate_blocks:
        if block.tag_name not in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6"}:
            continue
        normalized = _normalize_space(block.text)
        m = re.search(r"(?iu)\bcâu\s*(\d{1,3})\b.*?\bđáp\s*án\b\s*[:：]?\s*([ABCD])\b", normalized)
        if not m:
            m = re.search(r"(?iu)^\s*(?:câu\s*)?(\d{1,3})\s*[:\.\)\-]\s*([ABCD])\b", normalized)
        if not m:
            continue
        grouped.append((block.block_index, block, str(int(m.group(1))), str(m.group(2)).upper()))

    if len(grouped) < 3:
        return entries, cues, confidence

    for _, block, qnum, value in grouped:
        entries.append(
            {
                "exam_id": block.exam_id,
                "question_number": qnum,
                "mode": "single_choice",
                "value": value,
            }
        )
    if entries:
        cues.append("list:question-choice")
        confidence = 0.88 if heading_indexes else 0.80
    return entries, cues, confidence


def extract_answer_summary(parsed: Dict[str, Any]) -> Dict[str, Any]:
    blocks: List[HtmlBlock] = list(parsed.get("blocks", []))
    table_entries: List[Dict[str, Any]] = []
    table_html_parts: List[str] = []
    source_cues: List[str] = []
    issues: List[Dict[str, Any]] = []
    confidences: List[float] = []

    for block in blocks:
        if block.tag_name != "table":
            continue
        entries, table_issues, cues, confidence = _extract_answer_summary_from_table(block)
        if entries:
            table_entries.extend(entries)
            table_html_parts.append(block.html)
            source_cues.extend(cues)
            if confidence > 0:
                confidences.append(confidence)
        issues.extend(table_issues)

    list_entries, list_cues, list_conf = _extract_answer_summary_list_candidates(blocks)
    if list_entries:
        source_cues.extend(list_cues)
        if list_conf > 0:
            confidences.append(list_conf)

    all_entries = table_entries + list_entries
    seen_entry_keys: set[Tuple[str, str, str]] = set()
    seen_entry_payloads: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    deduped_entries: List[Dict[str, Any]] = []
    zone_ambiguous = False
    for entry in all_entries:
        key = (
            str(entry.get("exam_id", "DE_UNKNOWN")),
            str(entry.get("question_number", "")),
            str(entry.get("mode", "")),
        )
        if key in seen_entry_keys:
            if seen_entry_payloads.get(key, {}) != entry:
                zone_ambiguous = True
            issues.append(
                _build_answer_issue(
                    code="answer_summary_duplicate_question_number",
                    severity="warning",
                    message=f"Duplicate summary entry for exam={key[0]} question={key[1]} mode={key[2]}",
                    exam_id=key[0],
                    stage="answer_summary_extraction",
                )
            )
            continue
        seen_entry_keys.add(key)
        seen_entry_payloads[key] = dict(entry)
        deduped_entries.append(entry)

    table_present = bool(table_entries)
    list_present = bool(list_entries)
    if table_present and list_present:
        source_type = "mixed"
    elif table_present:
        source_type = "table"
    elif list_present:
        source_type = "list"
    else:
        source_type = "mixed"

    if not deduped_entries:
        issues.append(
            _build_answer_issue(
                code="answer_summary_zone_missing",
                severity="warning",
                message="No answer summary zone detected",
                stage="answer_summary_extraction",
            )
        )

    if zone_ambiguous or (table_present and len(table_html_parts) > 1 and len({entry.get("mode") for entry in table_entries}) > 1):
        issues.append(
            _build_answer_issue(
                code="answer_summary_zone_ambiguous",
                severity="warning",
                message="Multiple summary zones produce ambiguous answer mapping",
                stage="answer_summary_extraction",
            )
        )

    detection_confidence = round(mean(confidences), 3) if confidences else 0.0
    parser_notes = [issue["message"] for issue in issues[:12]]
    summary_html = "\n".join(table_html_parts)
    if not summary_html and list_entries:
        summary_html = "\n".join(
            block.html
            for block in blocks
            if block.tag_name in {"p", "div"}
            and (
                re.search(r"(?iu)\bcâu\s*(\d{1,3})\b.*?\bđáp\s*án\b\s*[:：]?\s*([ABCD])\b", _normalize_space(block.text))
                or re.search(r"(?iu)^\s*(?:câu\s*)?(\d{1,3})\s*[:\.\)\-]\s*([ABCD])\b", _normalize_space(block.text))
            )
        )

    deduped_entries.sort(
        key=lambda entry: (
            exam_sort_key(str(entry.get("exam_id", "DE_UNKNOWN"))),
            int(str(entry.get("question_number", "0")) or 0),
            str(entry.get("mode", "")),
        )
    )

    return {
        "present": bool(deduped_entries),
        "source_type": source_type,
        "html": summary_html,
        "entries": deduped_entries,
        "detection": {
            "source_cues": sorted(set(source_cues)),
            "confidence": detection_confidence,
            "parser_notes": parser_notes,
            "dom_backend": "lxml.html" if lxml_html is not None else "regex_fallback",
            "table_backend": "pandas.read_html" if pd is not None else "regex_fallback",
        },
        "qa_flags": [
            {"code": issue["code"], "severity": issue["severity"], "message": issue["message"]}
            for issue in issues
        ],
        "issues": issues,
    }


def _family_source_priority_path(document_family: str) -> List[str]:
    return list(DOCUMENT_FAMILY_PRIORITY_PATHS.get(document_family, DOCUMENT_FAMILY_PRIORITY_PATHS[DOCUMENT_FAMILY_UNKNOWN]))


def _select_priority_source_name(values: Dict[str, Any], document_family: str) -> str:
    if not values:
        return ""
    for priority_name in _family_source_priority_path(document_family):
        if priority_name in values:
            return priority_name
    if "answer_summary_table" in values:
        return "answer_summary_table"
    if "answer_summary_list" in values:
        return "answer_summary_list"
    return sorted(values.keys())[0]


def _is_answer_zone_heading(text: str) -> bool:
    return bool(ANSWER_ZONE_HEADING_RE.match(_normalize_space(text)))


def _is_inline_solution_heading(text: str) -> bool:
    return bool(INLINE_SOLUTION_MARKER_RE.match(_normalize_space(text)))


def _is_rubric_heading(text: str) -> bool:
    return bool(RUBRIC_SCORING_MARKER_RE.search(_normalize_space(text)))


def _detect_anchored_zone_kind(text: str) -> Tuple[str, str, int]:
    normalized = _normalize_space(text)
    if not normalized:
        return "", "", -1

    for regex, kind in (
        (ANSWER_ZONE_HEADING_RE, "solution"),
        (INLINE_SOLUTION_MARKER_RE, "solution"),
        (RUBRIC_SCORING_MARKER_RE, "rubric"),
    ):
        match = regex.search(normalized)
        if match:
            return kind, _normalize_space(match.group(0)), match.end()

    table_match = RUBRIC_TABLE_MARKER_RE.search(normalized)
    if table_match:
        return "rubric", _normalize_space(table_match.group(0)), table_match.end()
    return "", "", -1


def _parse_solution_text_for_question(
    question: ParsedQuestion,
    solution_text: str,
    *,
    source_name: str,
    confidence: float,
    anchor_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cleaned = _normalize_space(solution_text)
    meta = dict(anchor_meta or {})
    if not cleaned:
        return {
            "mode": "none",
            "source": source_name,
            "confidence": 0.0,
            "details": {**meta, "cue": "empty_anchored_solution"},
        }

    if question.question_type in {"true_false", "unknown"}:
        explicit_boolean = _extract_boolean_group_from_text(cleaned)
        if explicit_boolean is not None:
            return {
                "mode": "boolean_group",
                "subanswers": explicit_boolean,
                "source": source_name,
                "confidence": max(confidence, 0.82),
                "details": {**meta, "cue": "anchored_boolean_group"},
            }

    explicit_solution = _extract_explicit_solution_value(cleaned)
    if explicit_solution is not None:
        result = dict(explicit_solution)
        result["source"] = source_name
        result["confidence"] = max(_safe_float(result.get("confidence", 0.0)), confidence)
        details = dict(result.get("details", {}))
        details.update(meta)
        details.setdefault("cue", "anchored_explicit")
        result["details"] = details
        return result

    boolean_hits = [(m.group(1).lower(), m.group(2)) for m in BOOLEAN_ROW_RE.finditer(cleaned)]
    if boolean_hits:
        # Statement verdicts like "(a) Đúng/(b) Sai" appear in both true/false grids and
        # single-choice "choose the correct statements" questions. Only emit a boolean_group
        # answer when the question itself is a true/false-style item (or unknown).
        #
        # For single_choice, keep these verdicts available for deterministic option matching
        # via _infer_single_choice_from_solution(...) further below (no semantic guessing).
        if question.question_type in {"true_false", "unknown"}:
            subanswers: Dict[str, bool] = {}
            for label, value in boolean_hits:
                normalized = _normalize_boolean_value(value)
                if normalized is not None:
                    subanswers[label] = normalized
            if subanswers:
                return {
                    "mode": "boolean_group",
                    "subanswers": dict(sorted(subanswers.items(), key=lambda kv: kv[0])),
                    "source": source_name,
                    "confidence": max(confidence, 0.80),
                    "details": {**meta, "cue": "anchored_boolean_group"},
                }

    m_choice = SOLUTION_CHOICE_RE.search(cleaned)
    if m_choice:
        choice = _normalize_choice_value(m_choice.group(1))
        if choice:
            return {
                "mode": "single_choice",
                "value": choice,
                "source": source_name,
                "confidence": max(confidence, 0.78),
                "details": {**meta, "cue": "anchored_choice"},
            }

    m_short = SOLUTION_SHORT_RE.search(cleaned)
    if m_short:
        value = _normalize_solution_short_text(m_short.group(1))
        if value is not None:
            return {
                "mode": "short_answer",
                "accepted_answers": [value],
                "source": source_name,
                "confidence": max(confidence, 0.76),
                "details": {**meta, "cue": "anchored_short_answer"},
            }

    if question.question_type in {"single_choice", "multiple_choice"}:
        inferred_choice = _infer_single_choice_from_solution(question, cleaned)
        if inferred_choice:
            return {
                "mode": "single_choice",
                "value": inferred_choice,
                "source": source_name,
                "confidence": max(confidence, 0.72),
                "details": {**meta, "cue": "anchored_option_match"},
            }

    return {
        "mode": "none",
        "source": source_name,
        "confidence": 0.0,
        "details": {**meta, "cue": "anchored_block_unparsed"},
    }


def _extract_anchored_zone_entries(question: ParsedQuestion) -> List[Dict[str, Any]]:
    dom_blocks = _extract_dom_structural_blocks(question.html_content)
    if dom_blocks:
        blocks = [_normalize_space(str(block.get("text", ""))) for block in dom_blocks if _normalize_space(str(block.get("text", "")))]
    else:
        blocks = [_normalize_space(text) for text in question.block_texts if _normalize_space(text)]
    entries: List[Dict[str, Any]] = []
    if not blocks:
        return entries

    zone_kind = ""
    zone_heading = ""
    zone_heading_end = -1
    zone_start_index: Optional[int] = None
    zone_tail_parts: List[str] = []

    for idx, text in enumerate(blocks):
        detected_kind, detected_heading, detected_end = _detect_anchored_zone_kind(text)
        if detected_kind:
            zone_kind = detected_kind
            zone_heading = detected_heading
            zone_heading_end = detected_end
            zone_start_index = idx
            break

    if not zone_kind or zone_start_index is None:
        # Narrow fallback for common corpus pattern where solution appendix is segmented
        # into per-question chunks like "Câu 1 (TH):" followed by "Đáp án: A", but the
        # global heading ("HƯỚNG DẪN GIẢI...") lives outside the chunk boundary.
        head = blocks[0] if blocks else ""
        head_norm = _normalize_space(head)
        anchor_match = QUESTION_ANCHOR_RE.match(head_norm)
        full_text = _normalize_space(" ".join(blocks))
        if anchor_match and "(" in head_norm and SOLUTION_EXPLICIT_VALUE_RE.search(full_text):
            qnum = _parse_question_number(anchor_match.group(1))
            if qnum:
                entries.append(
                    {
                        "exam_id": question.exam_id,
                        "question_number": qnum,
                        "zone_kind": "solution",
                        "zone_heading": "implicit_solution_appendix",
                        "anchor_text": _normalize_space(anchor_match.group(0)),
                        "block_text": full_text,
                        "block_index": 0,
                        "line": question.start_line,
                        "chunk_question_id": question.item_id,
                    }
                )
        return entries

    # Build "effective" block texts for the zone tail (strip the heading prefix on the first block).
    effective_blocks: List[str] = []
    for block_index in range(zone_start_index, len(blocks)):
        text = blocks[block_index]
        if not text:
            effective_blocks.append("")
            continue
        if block_index == zone_start_index and zone_heading_end >= 0:
            effective_blocks.append(text[zone_heading_end:])
        else:
            effective_blocks.append(text)

    # Gather anchors across blocks and slice a block-range from each anchor to the next anchor.
    # This matches the common corpus pattern:
    # - "Câu n. ..." in one paragraph
    # - "Đáp án: X" in the next paragraph(s)
    anchored_positions: List[Tuple[int, int, str, str]] = []
    for rel_block_index, text in enumerate(effective_blocks):
        search_text = text or ""
        if not _normalize_space(search_text):
            continue
        zone_tail_parts.append(_normalize_space(search_text))
        for match in QUESTION_ANCHOR_INLINE_RE.finditer(search_text):
            prefix = _normalize_space(search_text[: match.start()]).rstrip()
            if prefix and prefix[-1] not in {".", ":", ";", ")", "-", "–", "—"}:
                continue
            qnum = _parse_question_number(match.group(1))
            if not qnum:
                continue
            anchored_positions.append((rel_block_index, match.start(), qnum, _normalize_space(match.group(0))))

    if anchored_positions:
        anchored_positions.sort(key=lambda item: (item[0], item[1], int(item[2])))
        for idx, (start_block_rel, start_offset, qnum, anchor_text) in enumerate(anchored_positions):
            if idx + 1 < len(anchored_positions):
                end_block_rel, end_offset, _qn2, _a2 = anchored_positions[idx + 1]
            else:
                end_block_rel, end_offset = len(effective_blocks), 0

            parts: List[str] = []
            if end_block_rel == start_block_rel:
                parts.append(effective_blocks[start_block_rel][start_offset:end_offset])
            else:
                parts.append(effective_blocks[start_block_rel][start_offset:])
                for mid in range(start_block_rel + 1, min(end_block_rel, len(effective_blocks))):
                    parts.append(effective_blocks[mid])
                if end_block_rel < len(effective_blocks):
                    parts.append(effective_blocks[end_block_rel][:end_offset])

            block_text = _normalize_space(" ".join(part for part in parts if _normalize_space(part)))
            if not block_text:
                continue

            absolute_block_index = zone_start_index + start_block_rel
            entries.append(
                {
                    "exam_id": question.exam_id,
                    "question_number": qnum,
                    "zone_kind": zone_kind,
                    "zone_heading": zone_heading,
                    "anchor_text": anchor_text,
                    "block_text": block_text,
                    "block_index": absolute_block_index,
                    "line": question.start_line + absolute_block_index,
                    "chunk_question_id": question.item_id,
                }
            )

    if not entries and zone_kind in {"solution", "rubric"}:
        tail_text = _normalize_space(" ".join(zone_tail_parts))
        if tail_text:
            if zone_kind == "solution":
                parsed = _parse_solution_text_for_question(
                    question,
                    tail_text,
                    source_name="anchored_solution_block",
                    confidence=0.78,
                    anchor_meta={
                        "zone_kind": zone_kind,
                        "zone_heading": zone_heading,
                        "anchor_text": f"Câu {question.question_number}",
                        "block_index": zone_start_index,
                        "chunk_question_id": question.item_id,
                        "fallback_kind": "chunk_question_zone",
                    },
                )
                if parsed.get("mode") != "none":
                    entries.append(
                        {
                            "exam_id": question.exam_id,
                            "question_number": str(question.question_number),
                            "zone_kind": zone_kind,
                            "zone_heading": zone_heading,
                            "anchor_text": f"Câu {question.question_number}",
                            "block_text": tail_text,
                            "block_index": zone_start_index,
                            "line": question.start_line + zone_start_index,
                            "chunk_question_id": question.item_id,
                        }
                    )
            else:
                entries.append(
                    {
                        "exam_id": question.exam_id,
                        "question_number": str(question.question_number),
                        "zone_kind": zone_kind,
                        "zone_heading": zone_heading,
                        "anchor_text": f"Câu {question.question_number}",
                        "block_text": tail_text,
                        "block_index": zone_start_index,
                        "line": question.start_line + zone_start_index,
                        "chunk_question_id": question.item_id,
                    }
                )

    return entries


def _anchored_candidate_priority(zone_kind: str, question_type: str) -> Optional[int]:
    qtype = str(question_type or "unknown")
    if zone_kind == "solution":
        if qtype in {"single_choice", "multiple_choice", "true_false", "short_answer"}:
            return 0
        if qtype == "unknown":
            return 1
        return None
    if zone_kind == "rubric":
        if qtype == "essay":
            return 0
        if qtype == "unknown":
            return 1
        return None
    return None


def _text_has_solution_marker(text: str) -> bool:
    """
    Structural signal that a chunk contains solution/answer material.

    Used only to disambiguate duplicate question-number candidates. Must not be used
    to invent answers.
    """

    normalized = _normalize_space(text)
    if not normalized:
        return False
    if INLINE_SOLUTION_MARKER_RE.search(normalized):
        return True
    if SOLUTION_EXPLICIT_VALUE_RE.search(normalized):
        return True
    # Common boolean-solution form: "a) Sai.", "b) Đúng.", ...
    if re.search(r"(?iu)\b[a-d]\)\s*(?:đúng|sai)\b", normalized):
        return True
    return False


def _infer_solution_mode_hint(block_text: str) -> str:
    """
    Best-effort mode hint for candidate picking when question numbers repeat across parts.
    Must degrade to "none" instead of guessing.
    """

    cleaned = _normalize_space(block_text)
    if not cleaned:
        return "none"
    if _extract_boolean_group_from_text(cleaned) is not None:
        return "boolean_group"
    if BOOLEAN_ROW_RE.search(cleaned):
        return "boolean_group"
    explicit = _extract_explicit_solution_value(cleaned)
    if isinstance(explicit, dict):
        mode = str(explicit.get("mode", "none"))
        if mode in {"single_choice", "short_answer", "boolean_group"}:
            return mode
    if SOLUTION_CHOICE_RE.search(cleaned):
        return "single_choice"
    if SOLUTION_SHORT_RE.search(cleaned):
        return "short_answer"
    return "none"


def _infer_question_mode_hint(question: ParsedQuestion) -> str:
    qtype = str(question.question_type or "unknown")
    if qtype in {"single_choice", "multiple_choice"}:
        return "single_choice"
    if qtype == "true_false":
        return "boolean_group"
    if qtype == "short_answer":
        return "short_answer"

    text = _normalize_space(str(question.text_content or ""))
    if not text:
        return "none"

    # Strong choice option signal.
    if re.search(r"(?iu)\bA\.\s", text) and re.search(r"(?iu)\bB\.\s", text):
        return "single_choice"

    # Strong boolean-group statement signal.
    if re.search(r"(?iu)\ba\)\s", text) and re.search(r"(?iu)\bb\)\s", text) and re.search(r"(?iu)\bc\)\s", text):
        return "boolean_group"

    return "none"


def _solution_mode_penalty(solution_hint: str, candidate_hint: str) -> int:
    if not solution_hint or solution_hint == "none":
        return 0
    if candidate_hint == solution_hint:
        return 0
    if candidate_hint == "none":
        # Unknown structure is better than a known mismatch when numbers repeat.
        return 1
    # Known mismatch (e.g. boolean solution attached to single-choice question).
    return 3


def _parse_anchored_rubric_source(question: ParsedQuestion, entry: Dict[str, Any]) -> Dict[str, Any]:
    block_text = _normalize_space(str(entry.get("block_text", "")))
    if not block_text:
        return {
            "mode": "none",
            "source": "anchored_rubric_block",
            "confidence": 0.0,
            "details": {"cue": "empty_anchored_rubric"},
        }
    rubric = {
        "mode": "analytic",
        "rubric_text": block_text,
        "blocks": [{"order": 1, "content_text": block_text, "points": None}],
    }
    return {
        "mode": "rubric",
        "source": "anchored_rubric_block",
        "rubric": rubric,
        "rubric_detection": {
            "source_cues": [
                {"type": "anchor", "value": str(entry.get("anchor_text", ""))},
                {"type": "zone", "value": str(entry.get("zone_heading", ""))},
            ],
            "confidence": 0.86,
            "parser_notes": ["anchored_rubric_block_detected"],
        },
        "confidence": 0.86,
        "details": {
            "zone_kind": str(entry.get("zone_kind", "rubric")),
            "anchor_text": str(entry.get("anchor_text", "")),
            "block_index": int(entry.get("block_index", 0) or 0),
            "chunk_question_id": str(entry.get("chunk_question_id", "")),
        },
    }


def _build_anchored_source_index(questions: List[ParsedQuestion]) -> Dict[str, Any]:
    by_exam_question: Dict[Tuple[str, int], List[ParsedQuestion]] = {}
    for question in questions:
        by_exam_question.setdefault((question.exam_id, question.question_number), []).append(question)

    for key in by_exam_question:
        by_exam_question[key] = sorted(by_exam_question[key], key=lambda q: (q.start_line, q.item_id))

    raw_entries: List[Dict[str, Any]] = []
    for question in questions:
        raw_entries.extend(_extract_anchored_zone_entries(question))

    solution_sources: Dict[str, Dict[str, Any]] = {}
    rubric_sources: Dict[str, Dict[str, Any]] = {}
    solution_blocks_by_item_id: Dict[str, Dict[str, Any]] = {}
    rubric_blocks_by_item_id: Dict[str, Dict[str, Any]] = {}
    assigned_solution_item_ids: set[str] = set()
    assigned_rubric_item_ids: set[str] = set()
    solution_examples: List[Dict[str, Any]] = []
    rubric_examples: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []

    for entry in raw_entries:
        zone_kind = str(entry.get("zone_kind", ""))
        exam_id = str(entry.get("exam_id", "DE_UNKNOWN"))
        qnum = int(str(entry.get("question_number", "0")) or 0)
        candidates = by_exam_question.get((exam_id, qnum), [])
        if not candidates and exam_id == "DE_UNKNOWN":
            global_candidates = [q for q in questions if q.question_number == qnum]
            if len({q.exam_id for q in global_candidates}) == 1:
                candidates = sorted(global_candidates, key=lambda q: (q.start_line, q.item_id))

        chunk_question_id = str(entry.get("chunk_question_id", ""))
        exact_candidates = [candidate for candidate in candidates if candidate.item_id == chunk_question_id]
        # In many real bundles, solution appendices are segmented into "question-like"
        # chunks (duplicate Câu n) with low confidence/unknown type. When we detect a
        # zone inside such a chunk, we still want to attach the anchored evidence to
        # the best compatible *real* question item, not to the appendix chunk itself.
        use_exact_pool = False
        if zone_kind == "solution" and exact_candidates:
            exact = exact_candidates[0]
            exact_conf = _safe_float(exact.parse_confidence, 0.0)
            use_exact_pool = exact.question_type != "unknown" and exact_conf >= 0.65
        candidate_pool = exact_candidates if use_exact_pool else candidates

        # If this anchored entry comes from a solution-appendix chunk (e.g. "Câu n (TH): ... Đáp án: A"),
        # do not attach the evidence back to that appendix chunk when there are multiple same-number
        # candidates. Prefer attaching to the "real" question block instead.
        source_is_solution_appendix = str(entry.get("zone_heading", "")) == "implicit_solution_appendix"
        source_candidate = exact_candidates[0] if exact_candidates else None
        source_text_norm = _normalize_space(str((source_candidate.text_content if source_candidate else "") or ""))
        if not source_is_solution_appendix and source_text_norm:
            # Narrow structural signal used in the canonical corpus: solution chunks contain an explicit
            # "Đáp án:" cue and often include parenthetical level markers like "(TH)" / "(NB)" / "(VD)".
            if SOLUTION_EXPLICIT_VALUE_RE.search(source_text_norm) and re.search(r"(?iu)\bcâu\s*\d{1,3}\b.*\(", source_text_norm[:80] or ""):
                source_is_solution_appendix = True
            # Another narrow structural signal: a second copy of questions that contains
            # "Hướng dẫn giải"/explicit answer cues while an earlier candidate does not.
            if (
                not source_is_solution_appendix
                and zone_kind == "solution"
                and len(candidates) > 1
                and _text_has_solution_marker(source_text_norm)
                and any(not _text_has_solution_marker(str(c.text_content or "")) for c in candidates)
            ):
                source_is_solution_appendix = True

        # If the anchored entry originates from a solution-appendix candidate, we must
        # relax away from the exact-candidate pool so we can attach evidence to the
        # real question block. Otherwise we can end up skipping the only candidate in
        # the pool (the appendix chunk itself) and silently dropping the entry.
        if zone_kind == "solution" and source_is_solution_appendix and use_exact_pool and len(candidates) > 1:
            candidate_pool = candidates

        solution_hint = _infer_solution_mode_hint(str(entry.get("block_text", ""))) if zone_kind == "solution" else "none"
        has_non_solution_variant = (
            zone_kind == "solution"
            and len(candidates) > 1
            and any(not _text_has_solution_marker(str(c.text_content or "")) for c in candidates)
        )

        compatible_candidates: List[Tuple[int, int, int, int, float, str, ParsedQuestion]] = []
        for candidate in candidate_pool:
            if (
                zone_kind == "solution"
                and source_is_solution_appendix
                and candidate.item_id == chunk_question_id
                and len(candidates) > 1
            ):
                continue
            if zone_kind == "solution" and candidate.item_id in assigned_solution_item_ids:
                continue
            if zone_kind == "rubric" and candidate.item_id in assigned_rubric_item_ids:
                continue
            effective_type = str(candidate.question_type or "unknown")
            if zone_kind == "solution" and solution_hint != "none" and effective_type == "unknown":
                # Disambiguate common patterns in the canonical corpus where question numbers repeat
                # across parts (e.g. PHẦN I/II/III all contain "Câu 1"). Do not guess an answer;
                # only use structure to choose the correct target candidate.
                hint = _infer_question_mode_hint(candidate)
                if hint == "single_choice":
                    effective_type = "single_choice"
                elif hint == "boolean_group":
                    effective_type = "true_false"
                elif hint == "short_answer":
                    effective_type = "short_answer"
                elif solution_hint == "boolean_group":
                    effective_type = "true_false"
                elif solution_hint == "short_answer":
                    effective_type = "short_answer"
                elif solution_hint == "single_choice":
                    effective_type = "single_choice"

            priority = _anchored_candidate_priority(zone_kind, effective_type)
            if priority is None:
                continue
            mode_penalty = _solution_mode_penalty(solution_hint, _infer_question_mode_hint(candidate)) if zone_kind == "solution" else 0
            solution_variant_penalty = 0
            if has_non_solution_variant and _text_has_solution_marker(str(candidate.text_content or "")):
                solution_variant_penalty = 1
            compatible_candidates.append(
                (
                    priority,
                    mode_penalty,
                    solution_variant_penalty,
                    int(candidate.start_line or 0),
                    -_safe_float(candidate.parse_confidence, 0.0),
                    candidate.item_id,
                    candidate,
                )
            )

        if not compatible_candidates:
            continue

        compatible_candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3], item[4], item[5]))
        target = compatible_candidates[0][6]

        if zone_kind == "solution":
            if target.item_id not in solution_blocks_by_item_id:
                solution_blocks_by_item_id[target.item_id] = dict(entry)
            source = _parse_solution_text_for_question(
                target,
                str(entry.get("block_text", "")),
                source_name="anchored_solution_block",
                confidence=0.78,
                anchor_meta={
                    "zone_kind": zone_kind,
                    "zone_heading": str(entry.get("zone_heading", "")),
                    "anchor_text": str(entry.get("anchor_text", "")),
                    "block_index": int(entry.get("block_index", 0) or 0),
                    "chunk_question_id": str(entry.get("chunk_question_id", "")),
                },
            )
            if source.get("mode") != "none":
                solution_sources[target.item_id] = source
                assigned_solution_item_ids.add(target.item_id)
                if len(solution_examples) < 3:
                    solution_examples.append(
                        {
                            "question_id": target.item_id,
                            "question_number": target.question_number,
                            "anchor_text": str(entry.get("anchor_text", "")),
                            "preview": str(entry.get("block_text", ""))[:180],
                            "parsed_mode": source.get("mode"),
                        }
                    )
        elif zone_kind == "rubric":
            if target.item_id not in rubric_blocks_by_item_id:
                rubric_blocks_by_item_id[target.item_id] = dict(entry)
            source = _parse_anchored_rubric_source(target, entry)
            if source.get("mode") != "none":
                rubric_sources[target.item_id] = source
                assigned_rubric_item_ids.add(target.item_id)
                if len(rubric_examples) < 3:
                    rubric_examples.append(
                        {
                            "question_id": target.item_id,
                            "question_number": target.question_number,
                            "anchor_text": str(entry.get("anchor_text", "")),
                            "preview": str(entry.get("block_text", ""))[:180],
                        }
                    )

    objective_questions = [question for question in questions if question.question_type in {"single_choice", "multiple_choice", "true_false", "short_answer"}]
    rubric_questions = [question for question in questions if question.question_type == "essay"]

    solution_found_questions = [question for question in objective_questions if question.item_id in solution_blocks_by_item_id]
    rubric_found_questions = [question for question in rubric_questions if question.item_id in rubric_blocks_by_item_id]

    return {
        "solution_sources": solution_sources,
        "rubric_sources": rubric_sources,
        "solution_blocks_by_item_id": solution_blocks_by_item_id,
        "rubric_blocks_by_item_id": rubric_blocks_by_item_id,
        "solution_found_count": len(solution_found_questions),
        "solution_missing_count": max(0, len(objective_questions) - len(solution_found_questions)),
        "rubric_found_count": len(rubric_found_questions),
        "rubric_missing_count": max(0, len(rubric_questions) - len(rubric_found_questions)),
        "solution_examples": solution_examples,
        "rubric_examples": rubric_examples,
        "issues": issues,
    }


def _question_solution_zone_text(question: ParsedQuestion) -> Tuple[str, bool, List[str]]:
    lines = [_normalize_space(line) for line in question.block_texts if _normalize_space(line)]
    if not lines:
        return "", False, []

    zone_started = False
    zone_start_index: Optional[int] = None
    zone_lines: List[str] = []
    zone_cues: List[str] = []
    for idx, line in enumerate(lines):
        if _is_inline_solution_heading(line):
            zone_started = True
            zone_cues.append(line)
            zone_start_index = idx + 1
            continue

    if zone_started and zone_start_index is not None:
        for line in lines[zone_start_index:]:
            zone_lines.append(line)

    if not zone_started or not zone_lines:
        return "", False, zone_cues
    return " ".join(zone_lines).strip(), True, zone_cues


def _question_pre_solution_text(question: ParsedQuestion) -> str:
    lines = [_normalize_space(line) for line in question.block_texts if _normalize_space(line)]
    if not lines:
        return ""

    cutoff = len(lines)
    for idx, line in enumerate(lines):
        if _is_inline_solution_heading(line) or _is_answer_zone_heading(line) or _is_rubric_heading(line):
            cutoff = idx
            break
    return " ".join(lines[:cutoff]).strip()


def _detect_document_family(parsed: Dict[str, Any], answer_summary: Dict[str, Any]) -> Dict[str, Any]:
    blocks: List[HtmlBlock] = list(parsed.get("blocks", []))
    questions: List[ParsedQuestion] = list(parsed.get("questions", []))
    first_answer_zone_index = min((block.block_index for block in blocks if _is_answer_zone_heading(block.text)), default=None)

    family_scores: Dict[str, float] = {
        DOCUMENT_FAMILY_OBJECTIVE_END_KEY: 0.0,
        DOCUMENT_FAMILY_OBJECTIVE_INLINE: 0.0,
        DOCUMENT_FAMILY_RUBRIC: 0.0,
    }
    evidence: List[Dict[str, Any]] = []

    def add_evidence(
        family: str,
        *,
        cue: str,
        weight: float,
        detail: str = "",
        line: int = 1,
        question_id: str = "",
    ) -> None:
        if family not in family_scores:
            return
        family_scores[family] += weight
        evidence.append(
            {
                "family": family,
                "cue": cue,
                "weight": round(weight, 3),
                "detail": detail,
                "line": int(line or 1),
                "question_id": question_id,
            }
        )

    summary_present = bool(answer_summary.get("present"))
    summary_entries = list(answer_summary.get("entries", []) or [])
    summary_source_type = str(answer_summary.get("source_type", "mixed"))
    summary_detection = answer_summary.get("detection", {}) if isinstance(answer_summary.get("detection", {}), dict) else {}
    summary_confidence = _safe_float(summary_detection.get("confidence", 0.0), 0.0)
    summary_cues = [str(cue) for cue in summary_detection.get("source_cues", []) if _is_non_empty_string(str(cue))]

    if summary_present and summary_entries:
        add_evidence(
            DOCUMENT_FAMILY_OBJECTIVE_END_KEY,
            cue="answer_summary_present",
            weight=4.25,
            detail=f"{len(summary_entries)} entries; source_type={summary_source_type}",
        )
        if summary_confidence >= 0.8:
            add_evidence(
                DOCUMENT_FAMILY_OBJECTIVE_END_KEY,
                cue="answer_summary_confident",
                weight=1.0,
                detail=f"confidence={summary_confidence:.3f}",
            )
    if summary_cues:
        if any("table" in cue for cue in summary_cues):
            add_evidence(
                DOCUMENT_FAMILY_OBJECTIVE_END_KEY,
                cue="answer_summary_table_cue",
                weight=1.5,
                detail=";".join(summary_cues[:4]),
            )
        if any("list" in cue for cue in summary_cues):
            add_evidence(
                DOCUMENT_FAMILY_OBJECTIVE_END_KEY,
                cue="answer_summary_list_cue",
                weight=1.35,
                detail=";".join(summary_cues[:4]),
            )

    end_key_hits = 0
    inline_hits = 0
    rubric_hits = 0
    answer_zone_hits = 0

    for block in blocks:
        visible = _normalize_space(block.text)
        if not visible:
            continue
        rubric_table_signals = _extract_rubric_table_signals(block.html) if block.tag_name == "table" else {}
        if _is_answer_zone_heading(visible):
            answer_zone_hits += 1
            end_key_hits += 1
            add_evidence(
                DOCUMENT_FAMILY_OBJECTIVE_END_KEY,
                cue="end_key_heading",
                weight=2.75,
                detail=visible[:120],
                line=block.line,
            )
        if _is_rubric_heading(visible):
            rubric_hits += 1
            add_evidence(
                DOCUMENT_FAMILY_RUBRIC,
                cue="rubric_heading",
                weight=2.0,
                detail=visible[:120],
                line=block.line,
            )
        if rubric_table_signals:
            rubric_hits += 1
            add_evidence(
                DOCUMENT_FAMILY_RUBRIC,
                cue="rubric_table_cells",
                weight=2.25 + min(0.75, 0.08 * len(rubric_table_signals.get("scoring_rows", []))),
                detail=";".join(rubric_table_signals.get("cues", [])[:4]),
                line=block.line,
            )
        if (first_answer_zone_index is None or block.block_index < first_answer_zone_index) and _is_inline_solution_heading(visible):
            inline_hits += 1
            add_evidence(
                DOCUMENT_FAMILY_OBJECTIVE_INLINE,
                cue="question_inline_solution",
                weight=1.25,
                detail=visible[:120],
            )

    if inline_hits >= 2:
        add_evidence(
            DOCUMENT_FAMILY_OBJECTIVE_INLINE,
            cue="repeated_inline_solution",
            weight=2.15 + min(1.2, inline_hits * 0.12),
            detail=f"{inline_hits} question blocks",
        )
    elif inline_hits == 1:
        add_evidence(
            DOCUMENT_FAMILY_OBJECTIVE_INLINE,
            cue="single_inline_solution",
            weight=0.65,
            detail="single inline solution marker",
        )

    if rubric_hits >= 1:
        add_evidence(
            DOCUMENT_FAMILY_RUBRIC,
            cue="rubric_scoring_zone",
            weight=2.0 + min(1.5, rubric_hits * 0.12),
            detail=f"{rubric_hits} rubric markers",
        )

    if end_key_hits >= 1 and not summary_present:
        add_evidence(
            DOCUMENT_FAMILY_OBJECTIVE_END_KEY,
            cue="end_key_zone_without_summary",
            weight=0.9,
            detail=f"{end_key_hits} end-key headings; summary missing",
        )

    family_rank = {
        DOCUMENT_FAMILY_RUBRIC: 3,
        DOCUMENT_FAMILY_OBJECTIVE_END_KEY: 2,
        DOCUMENT_FAMILY_OBJECTIVE_INLINE: 1,
        DOCUMENT_FAMILY_UNKNOWN: 0,
    }
    scored = sorted(
        family_scores.items(),
        key=lambda kv: (kv[1], family_rank.get(kv[0], -1), kv[0]),
        reverse=True,
    )
    best_family, best_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0.0

    if best_score <= 0.0:
        family = DOCUMENT_FAMILY_UNKNOWN
        confidence = 0.0
    else:
        family = best_family
        confidence = round(clamp(best_score / max(best_score + second_score, 1.0), 0.5, 0.99), 3)

    ambiguous = family == DOCUMENT_FAMILY_UNKNOWN or confidence < 0.72 or (best_score - second_score < 0.75 and second_score > 0)
    priority_path = _family_source_priority_path(family)
    issue_code = ""
    if family == DOCUMENT_FAMILY_RUBRIC:
        issue_code = "rubric_scoring_zone_detected"
    elif family == DOCUMENT_FAMILY_OBJECTIVE_INLINE and (inline_hits < 2 or confidence < 0.8):
        issue_code = "inline_solution_zone_weak"
    elif family == DOCUMENT_FAMILY_OBJECTIVE_END_KEY and not summary_present:
        issue_code = "objective_end_key_missing_for_expected_family"
    elif ambiguous:
        issue_code = "document_family_ambiguous"

    return {
        "family": family,
        "confidence": confidence,
        "scores": {key: round(value, 3) for key, value in family_scores.items()},
        "evidence": evidence[:12],
        "priority_path": priority_path,
        "ambiguous": ambiguous,
        "issue_code": issue_code,
    }


def _build_answer_summary_index(
    *,
    answer_summary: Dict[str, Any],
    questions: List[ParsedQuestion],
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    mapping: Dict[str, Dict[str, Any]] = {}
    issues: List[Dict[str, Any]] = []
    assigned_item_ids: set[str] = set()

    by_exam_question: Dict[Tuple[str, int], List[ParsedQuestion]] = {}
    for question in questions:
        by_exam_question.setdefault((question.exam_id, question.question_number), []).append(question)

    for key in by_exam_question:
        by_exam_question[key] = sorted(by_exam_question[key], key=lambda q: (q.start_line, q.item_id))

    for entry in answer_summary.get("entries", []):
        exam_id = str(entry.get("exam_id", "DE_UNKNOWN"))
        qnum_raw = entry.get("question_number")
        try:
            qnum = int(str(qnum_raw))
        except ValueError:
            issues.append(
                _build_answer_issue(
                    code="answer_summary_question_reference_unknown",
                    severity="warning",
                    message=f"Invalid summary question number '{qnum_raw}'",
                    exam_id=exam_id,
                    stage="answer_reconciliation",
                )
            )
            continue

        candidates = by_exam_question.get((exam_id, qnum), [])
        if not candidates and exam_id == "DE_UNKNOWN":
            global_candidates = [q for q in questions if q.question_number == qnum]
            if len({q.exam_id for q in global_candidates}) == 1:
                candidates = sorted(global_candidates, key=lambda q: (q.start_line, q.item_id))
        if not candidates:
            issues.append(
                _build_answer_issue(
                    code="answer_summary_question_reference_unknown",
                    severity="warning",
                    message=f"Summary entry references unknown question {qnum} ({exam_id})",
                    exam_id=exam_id,
                    stage="answer_reconciliation",
                )
            )
            continue
        entry_mode = str(entry.get("mode", "none"))
        compatible_candidates: List[Tuple[int, int, float, str, ParsedQuestion]] = []
        for candidate in candidates:
            if candidate.item_id in assigned_item_ids:
                continue
            priority = _summary_candidate_priority(entry_mode, candidate.question_type)
            if priority is None:
                continue
            compatible_candidates.append(
                (
                    priority,
                    int(candidate.start_line or 0),
                    -_safe_float(candidate.parse_confidence, 0.0),
                    candidate.item_id,
                    candidate,
                )
            )

        if not compatible_candidates:
            if candidates:
                issues.append(
                    _build_answer_issue(
                        code="summary_mapping_invalid",
                        severity="warning",
                        message=(
                            f"Summary entry mode {entry_mode} has no compatible question item for question {qnum} "
                            f"({exam_id}); candidates={[candidate.question_type for candidate in candidates]}"
                        ),
                        exam_id=exam_id,
                        question_id=candidates[0].item_id,
                        line=candidates[0].start_line,
                        stage="answer_reconciliation",
                    )
                )
            else:
                issues.append(
                    _build_answer_issue(
                        code="answer_summary_question_reference_unknown",
                        severity="warning",
                        message=f"Summary entry references unknown question {qnum} ({exam_id})",
                        exam_id=exam_id,
                        stage="answer_reconciliation",
                    )
                )
            continue

        compatible_candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        best_priority = compatible_candidates[0][0]
        best_candidates = [candidate for candidate in compatible_candidates if candidate[0] == best_priority]
        if len(best_candidates) > 1:
            issues.append(
                _build_answer_issue(
                    code="answer_summary_duplicate_question_number",
                    severity="warning",
                    message=(
                        f"Ambiguous summary mapping for question {qnum} ({exam_id}), using first compatible "
                        f"{'exact' if best_priority == 0 else 'fallback'} match"
                    ),
                    exam_id=exam_id,
                    question_id=best_candidates[0][4].item_id,
                    line=best_candidates[0][4].start_line,
                    stage="answer_reconciliation",
                )
            )

        target = best_candidates[0][4]
        if target.item_id in mapping:
            continue
        mapping[target.item_id] = entry
        assigned_item_ids.add(target.item_id)

    return mapping, issues


def _summary_candidate_priority(entry_mode: str, question_type: str) -> Optional[int]:
    mode = str(entry_mode or "none")
    qtype = str(question_type or "unknown")
    if mode == "single_choice":
        if qtype in {"single_choice", "multiple_choice"}:
            return 0
        if qtype == "unknown":
            return 1
    elif mode == "boolean_group":
        if qtype == "true_false":
            return 0
        if qtype == "unknown":
            return 1
    elif mode == "short_answer":
        if qtype == "short_answer":
            return 0
        if qtype == "unknown":
            return 1
    elif mode == "rubric":
        if qtype == "essay":
            return 0
        if qtype == "unknown":
            return 1
    return None


def _extract_local_answer(question: ParsedQuestion) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    issues: List[Dict[str, Any]] = []
    source_cues: List[Dict[str, Any]] = []
    text = question.text_content

    if question.question_type == "true_false":
        table_rows = _extract_table_rows(question.html_content)
        if table_rows:
            table_answer = _extract_true_false_group_from_table_html(question.html_content)
            if table_answer:
                source_cues.append({"type": "table", "value": "true_false_matrix"})
                return (
                    {
                        "mode": "boolean_group",
                        "subanswers": table_answer,
                        "source": "local_formatting",
                        "confidence": 0.92,
                        "answer_detection": {
                            "source_cues": source_cues,
                            "confidence": 0.92,
                            "parser_notes": [],
                        },
                    },
                    issues,
                )
        local_text = _question_pre_solution_text(question)
        if re.search(r"(?iu)\bphát\s*biểu\b", local_text) and re.search(r"(?iu)\bđúng\b", local_text) and re.search(r"(?iu)\bsai\b", local_text):
            text_answer = _extract_boolean_group_from_text(local_text)
            if text_answer:
                source_cues.append({"type": "marker", "value": "Phát biểu/Đúng/Sai"})
                return (
                    {
                        "mode": "boolean_group",
                        "subanswers": text_answer,
                        "source": "local_formatting",
                        "confidence": 0.90,
                        "answer_detection": {
                            "source_cues": source_cues,
                            "confidence": 0.90,
                            "parser_notes": [],
                        },
                    },
                    issues,
                )
        return (
            {
                "mode": "none",
                "source": "local_formatting",
                "confidence": 0.0,
                "answer_detection": {
                    "source_cues": [],
                    "confidence": 0.0,
                    "parser_notes": ["no_local_answer_marker_detected"],
                },
            },
            issues,
        )

    if question.question_type == "unknown":
        table_rows = _extract_table_rows(question.html_content)
        if table_rows:
            table_answer = _extract_true_false_group_from_table_html(question.html_content)
            if table_answer:
                source_cues.append({"type": "table", "value": "true_false_matrix"})
                return (
                    {
                        "mode": "boolean_group",
                        "subanswers": table_answer,
                        "source": "local_formatting",
                        "confidence": 0.92,
                        "answer_detection": {
                            "source_cues": source_cues,
                            "confidence": 0.92,
                            "parser_notes": [],
                        },
                    },
                    issues,
                )
        local_text = _question_pre_solution_text(question)
        if re.search(r"(?iu)\bphát\s*biểu\b", local_text) and re.search(r"(?iu)\bđúng\b", local_text) and re.search(r"(?iu)\bsai\b", local_text):
            text_answer = _extract_boolean_group_from_text(local_text)
            if text_answer:
                source_cues.append({"type": "marker", "value": "Phát biểu/Đúng/Sai"})
                return (
                    {
                        "mode": "boolean_group",
                        "subanswers": text_answer,
                        "source": "local_formatting",
                        "confidence": 0.90,
                        "answer_detection": {
                            "source_cues": source_cues,
                            "confidence": 0.90,
                            "parser_notes": [],
                        },
                    },
                    issues,
                )

    # true/false local cues
    boolean_hits = [(m.group(1).lower(), m.group(2)) for m in LOCAL_BOOLEAN_ROW_RE.finditer(text)]
    if boolean_hits:
        subanswers: Dict[str, bool] = {}
        for label, value in boolean_hits:
            normalized = _normalize_boolean_value(value)
            if normalized is None:
                continue
            subanswers[label] = normalized
            source_cues.append({"type": "marker", "value": f"{label}) {value}"})
        return (
            {
                "mode": "boolean_group",
                "subanswers": dict(sorted(subanswers.items(), key=lambda kv: kv[0])),
                "source": "local_formatting",
                "confidence": 0.90 if len(subanswers) >= 2 else 0.78,
                "answer_detection": {
                    "source_cues": source_cues,
                    "confidence": 0.90 if len(subanswers) >= 2 else 0.78,
                    "parser_notes": [],
                },
            },
            issues,
        )

    choice_hits = [_normalize_choice_value(m.group(1)) for m in LOCAL_CHOICE_RE.finditer(text)]
    choice_hits = [hit for hit in choice_hits if hit is not None]
    unique_choices = sorted(set(choice_hits))
    if unique_choices:
        if len(unique_choices) > 1:
            issues.append(
                _build_answer_issue(
                    code="answer_source_conflict",
                    severity="blocker",
                    message=f"Local answer cues contain multiple choices: {unique_choices}",
                    exam_id=question.exam_id,
                    question_id=question.item_id,
                    line=question.start_line,
                    stage="local_answer_normalization",
                )
            )
        source_cues.append({"type": "marker", "value": "Đáp án"})
        return (
            {
                "mode": "single_choice",
                "value": unique_choices[0],
                "source": "local_formatting",
                "confidence": 0.94,
                "answer_detection": {
                    "source_cues": source_cues,
                    "confidence": 0.94,
                    "parser_notes": [],
                },
            },
            issues,
        )

    short_hits = [m.group(1) for m in LOCAL_SHORT_RE.finditer(text)]
    normalized_shorts = []
    for hit in short_hits:
        cleaned = _normalize_space(hit)
        if not cleaned:
            continue
        if _normalize_choice_value(cleaned) is not None and question.question_type in {"single_choice", "multiple_choice"}:
            continue
        short_value = _normalize_solution_short_text(cleaned)
        if short_value is None:
            continue
        normalized_shorts.append(short_value)
    if normalized_shorts:
        source_cues.append({"type": "marker", "value": "Đáp số/Đáp án"})
        return (
            {
                "mode": "short_answer",
                "accepted_answers": normalized_shorts[:3],
                "source": "local_formatting",
                "confidence": 0.88,
                "answer_detection": {
                    "source_cues": source_cues,
                    "confidence": 0.88,
                    "parser_notes": [],
                },
            },
            issues,
        )

    return (
        {
            "mode": "none",
            "source": "local_formatting",
            "confidence": 0.0,
            "answer_detection": {
                "source_cues": [],
                "confidence": 0.0,
                "parser_notes": ["no_local_answer_marker_detected"],
            },
        },
        issues,
    )


def _question_has_solution_context(question: ParsedQuestion) -> bool:
    _, has_zone, _ = _question_solution_zone_text(question)
    return has_zone


def _normalize_solution_short_text(value: str) -> Optional[Dict[str, str]]:
    normalized = _normalize_short_answer_value(value)
    compact = _normalize_space(normalized.get("normalized", ""))
    if not compact:
        return None
    compact = re.sub(r"(?iu)\s*[-–—\s]*(?:h[eêéèẻẽẹếềểễệ]t)\s*[-–—\s]*$", "", compact).strip()
    normalized["raw"] = compact
    normalized["normalized"] = compact
    compact = _normalize_space(normalized.get("normalized", ""))
    if not compact:
        return None
    if len(compact) > 60:
        return None
    word_count = len(compact.split())
    if word_count > 8:
        return None
    return normalized


def _is_heading_like_solution_value(raw: str) -> bool:
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", raw or "")).strip().lower()
    if not normalized:
        return True
    normalized = normalized.strip(" .,:;!-–—")
    if normalized in {
        "đáp án",
        "đáp số",
        "tham khảo",
        "lời giải",
        "lời giải tham khảo",
        "và lời giải tham khảo",
        "đáp án và lời giải",
        "đáp án và lời giải tham khảo",
    }:
        return True
    if "tham khảo" in normalized and len(normalized.split()) <= 5:
        # Generic heading fragments like "VÀ LỜI GIẢI THAM KHẢO" should not be
        # promoted to short-answer content.
        return True
    return False


def _extract_explicit_solution_value(solution_text: str) -> Optional[Dict[str, Any]]:
    m_explicit = SOLUTION_EXPLICIT_VALUE_RE.search(solution_text)
    if not m_explicit:
        return None
    raw = _normalize_space(m_explicit.group(1))
    if not raw:
        return None
    if _is_heading_like_solution_value(raw):
        return None

    choice = _normalize_choice_value(raw)
    if choice is not None:
        return {
            "mode": "single_choice",
            "value": choice,
            "source": "solution_explicit",
            "confidence": 0.84,
            "details": {"cue": "đáp án"},
        }

    compact_boolean = _normalize_boolean_group_compact_value(raw)
    if compact_boolean is not None:
        return {
            "mode": "boolean_group",
            "subanswers": dict(sorted(compact_boolean.items(), key=lambda kv: kv[0])),
            "source": "solution_explicit",
            "confidence": 0.82,
            "details": {"cue": "đáp án"},
        }

    boolean_value = _normalize_boolean_value(raw)
    if boolean_value is not None:
        return {
            "mode": "boolean_group",
            "subanswers": {"a": boolean_value},
            "source": "solution_explicit",
            "confidence": 0.80,
            "details": {"cue": "đáp án"},
        }

    short_value = _normalize_solution_short_text(raw)
    if short_value is not None:
        return {
            "mode": "short_answer",
            "accepted_answers": [short_value],
            "source": "solution_explicit",
            "confidence": 0.76,
            "details": {"cue": "đáp án"},
        }

    return None


def _extract_solution_answer(
    question: ParsedQuestion,
    document_family: str,
    summary_available: bool,
    anchored_solution_source: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if anchored_solution_source and str(anchored_solution_source.get("mode", "none")) != "none":
        source = dict(anchored_solution_source)
        source.setdefault("source", "anchored_solution_block")
        return source
    # The fast-path now comes from anchored zone parsing. If no anchored block is
    # available, we keep the source missing rather than guessing from the stem.
    return {"mode": "none", "source": "anchored_solution_block", "confidence": 0.0, "details": {"cue": "no_anchored_solution_block"}}


def _extract_rubric(question: ParsedQuestion, anchored_rubric_source: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if anchored_rubric_source and str(anchored_rubric_source.get("mode", "none")) == "rubric":
        rubric = dict(anchored_rubric_source.get("rubric", {}))
        rubric_detection = dict(anchored_rubric_source.get("rubric_detection", {}))
        return rubric, rubric_detection

    # Anchored rubric blocks are handled upstream. Fall back to the existing
    # table/marker parser only when no anchored source is supplied.
    table_signals = _extract_rubric_table_signals(question.html_content)
    if table_signals:
        rows = table_signals.get("rows", [])
        blocks = []
        rubric_lines = []
        for idx, row in enumerate(rows):
            row_text = _normalize_space(" | ".join(row))
            if not row_text:
                continue
            rubric_lines.append(row_text)
            points = None
            point_match = re.search(r"(?iu)\b(\d+(?:[.,]\d+)?)\s*điểm\b", row_text)
            if point_match:
                try:
                    points = float(point_match.group(1).replace(",", "."))
                except ValueError:
                    points = None
            elif re.fullmatch(r"(?iu)\d+(?:[.,]\d+)?", row_text):
                try:
                    points = float(row_text.replace(",", "."))
                except ValueError:
                    points = None
            blocks.append({"order": idx + 1, "content_text": row_text, "points": points})

        rubric_text = " ".join(rubric_lines).strip()
        if rubric_text:
            rubric_detection = {
                "source_cues": [{"type": "table_cell", "value": cue} for cue in table_signals.get("cues", [])],
                "confidence": _safe_float(table_signals.get("confidence", 0.82), 0.82),
                "parser_notes": ["rubric_table_marker_detected"] + (["scoring_rows_detected"] if table_signals.get("scoring_rows") else []),
            }
            return (
                {
                    "mode": "analytic",
                    "rubric_text": rubric_text,
                    "blocks": blocks,
                },
                rubric_detection,
            )

    lines = [_normalize_space(line) for line in question.block_texts if _normalize_space(line)]
    marker_index = -1
    marker_value = ""
    for idx, line in enumerate(lines):
        if "[R]" in line:
            marker_index = idx
            marker_value = "[R]"
            break
        if re.search(r"(?iu)\bR\.\s*", line):
            marker_index = idx
            marker_value = "R."
            break

    if marker_index < 0:
        return (
            {},
            {
                "source_cues": [],
                "confidence": 0.0,
                "parser_notes": ["missing_rubric_marker"],
            },
        )

    rubric_lines = lines[marker_index:]
    rubric_text = " ".join(rubric_lines).strip()
    blocks = [{"order": i + 1, "content_text": line, "points": None} for i, line in enumerate(rubric_lines) if line]
    rubric = {
        "mode": "analytic",
        "rubric_text": rubric_text,
        "blocks": blocks,
    }
    rubric_detection = {
        "source_cues": [{"type": "marker", "value": marker_value}],
        "confidence": 0.90,
        "parser_notes": [],
    }
    return rubric, rubric_detection


def _extract_choice_option_texts(question: ParsedQuestion) -> Dict[str, str]:
    text = _normalize_space(question.text_content)
    stem_text = re.split(r"(?iu)\bHướng dẫn giải\b|\bĐáp án\b|\bĐáp số\b", text, maxsplit=1)[0]
    parts = re.split(r"(?<!\w)([A-D])[\.:\)]\s*", stem_text)
    options: Dict[str, str] = {}
    for idx in range(1, len(parts), 2):
        letter = parts[idx].upper()
        option_text = _normalize_space(parts[idx + 1] if idx + 1 < len(parts) else "")
        if option_text:
            options[letter] = option_text
    return options


def _compact_choice_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", _normalize_space(value).lower())
    return re.sub(r"[^0-9a-zα-ω+\-]", "", normalized)


def _infer_single_choice_from_solution(question: ParsedQuestion, solution_text_override: Optional[str] = None) -> Optional[str]:
    options = _extract_choice_option_texts(question)
    if not options:
        return None

    if solution_text_override is not None:
        solution_text = _normalize_space(solution_text_override)
    else:
        solution_text, solution_context, _ = _question_solution_zone_text(question)
        if not solution_context:
            return None
    solution_compact = _compact_choice_text(solution_text)

    # 1. Numerical final answers that map directly to a numeric option.
    numeric_matches = re.findall(r"(?<!\w)([-+]?\d+(?:[.,]\d+)?)(?!\w)", solution_text)
    if numeric_matches:
        final_numeric = numeric_matches[-1]
        normalized_numeric = final_numeric.replace(",", ".")
        matching_letters = [
            letter
            for letter, option_text in options.items()
            if re.search(rf"(?<!\w){re.escape(normalized_numeric)}(?!\w)", _compact_choice_text(option_text))
        ]
        if len(matching_letters) == 1:
            return matching_letters[0]

    # 1b. Numeric-choice questions where the solution explicitly identifies the correct
    #     statement labels (a/b/c/d). Example:
    #       Options: A. 3. B. 2. C. 4. D. 1.
    #       Solution: "Các biện pháp (a), (b), (c) đều đúng ..."
    #     This is deterministic structure matching (no semantic guessing).
    numeric_options: Dict[str, int] = {}
    pure_numeric_count = 0
    for letter, option_text in options.items():
        normalized = _normalize_space(option_text)
        # Prefer strict numeric-only options (allow trailing punctuation like "3."), but tolerate
        # one polluted option when the other options are clearly numeric (common segmentation artifact).
        full = re.fullmatch(r"(?iu)(\d{1,2})[.,]?", normalized)
        if full:
            numeric_options[letter] = int(full.group(1))
            pure_numeric_count += 1
            continue
        prefix = re.match(r"(?iu)^(\d{1,2})[.,]?(?:\s|$)", normalized)
        if prefix:
            numeric_options[letter] = int(prefix.group(1))
    if numeric_options and (len(numeric_options) == len(options)) and (pure_numeric_count >= max(3, len(options) - 1)):
        # Explicit per-label verdicts: "(a) Đúng", "(b) Sai", ...
        true_labels = {
            label.lower()
            for label, verdict in re.findall(r"(?iu)\(([a-d])\)\s*(đúng|sai)", solution_text)
            if verdict.lower().startswith("đúng")
        }
        if true_labels:
            desired = len(true_labels)
            matching_letters = [letter for letter, value in numeric_options.items() if value == desired]
            if len(matching_letters) == 1:
                return matching_letters[0]

        # Group verdict: "... (a), (b), (c) đều đúng ..."
        group_match = re.search(
            r"(?iu)(?:các\s+)?(?:biện\s*pháp|phát\s*biểu|mệnh\s*đề).{0,160}?đều\s*đúng",
            solution_text,
        )
        if group_match:
            labels = {m.lower() for m in re.findall(r"(?iu)\(([a-d])\)", group_match.group(0))}
            if labels:
                desired = len(labels)
                matching_letters = [letter for letter, value in numeric_options.items() if value == desired]
                if len(matching_letters) == 1:
                    return matching_letters[0]

    # 2. Statement-set questions like "(a), (b)".
    true_labels = {
        label.lower()
        for label, verdict in re.findall(r"(?iu)\(([a-d])\)\s*(đúng|sai)", solution_text)
        if verdict.lower().startswith("đúng")
    }
    if true_labels:
        matching_letters = []
        for letter, option_text in options.items():
            option_labels = {match.lower() for match in re.findall(r"\(([a-d])\)", option_text, flags=re.IGNORECASE)}
            if option_labels and option_labels == true_labels:
                matching_letters.append(letter)
        if len(matching_letters) == 1:
            return matching_letters[0]

    # 3. Normalized text overlap between the solution explanation and one option.
    matching_letters = [
        letter
        for letter, option_text in options.items()
        if _compact_choice_text(option_text) and _compact_choice_text(option_text) in solution_compact
    ]
    if len(matching_letters) == 1:
        return matching_letters[0]

    return None


def _answer_values_equivalent(a: Dict[str, str], b: Dict[str, str]) -> bool:
    return _normalize_space(str(a.get("normalized", ""))).lower() == _normalize_space(str(b.get("normalized", ""))).lower()


def _question_answer_mode_family(question_type: str) -> str:
    qtype = str(question_type or "unknown")
    if qtype in {"single_choice", "multiple_choice"}:
        return "single_choice"
    if qtype == "true_false":
        return "boolean_group"
    if qtype == "short_answer":
        return "short_answer"
    if qtype == "essay":
        return "rubric"
    return "unknown"


def _build_peer_answer_source(peer: ParsedQuestion) -> Dict[str, Any]:
    mode = str((peer.answer_key or {}).get("mode", "none"))
    if mode == "single_choice":
        value = _normalize_choice_value(str((peer.answer_key or {}).get("value", "")))
        if not value:
            return {}
        return {
            "source": "same_question_number_peer",
            "confidence": max(
                [_safe_float(source.get("confidence", 0.0)) for source in (peer.answer_sources or [])]
                or [_safe_float(peer.parse_confidence, 0.0)]
            ),
            "details": {
                "mode": mode,
                "peer_item_id": peer.item_id,
                "peer_question_number": peer.question_number,
                "peer_question_type": peer.question_type,
                "peer_line": peer.start_line,
                "peer_chosen_source": str((peer.reconciliation or {}).get("chosen_source", "")),
            },
        }
    if mode == "boolean_group":
        subanswers = dict((peer.answer_key or {}).get("subanswers", {}))
        if not subanswers:
            return {}
        return {
            "source": "same_question_number_peer",
            "confidence": max(
                [_safe_float(source.get("confidence", 0.0)) for source in (peer.answer_sources or [])]
                or [_safe_float(peer.parse_confidence, 0.0)]
            ),
            "details": {
                "mode": mode,
                "peer_item_id": peer.item_id,
                "peer_question_number": peer.question_number,
                "peer_question_type": peer.question_type,
                "peer_line": peer.start_line,
                "peer_chosen_source": str((peer.reconciliation or {}).get("chosen_source", "")),
            },
        }
    if mode == "short_answer":
        accepted_answers = list((peer.answer_key or {}).get("accepted_answers", []) or [])
        if not accepted_answers:
            return {}
        return {
            "source": "same_question_number_peer",
            "confidence": max(
                [_safe_float(source.get("confidence", 0.0)) for source in (peer.answer_sources or [])]
                or [_safe_float(peer.parse_confidence, 0.0)]
            ),
            "details": {
                "mode": mode,
                "peer_item_id": peer.item_id,
                "peer_question_number": peer.question_number,
                "peer_question_type": peer.question_type,
                "peer_line": peer.start_line,
                "peer_chosen_source": str((peer.reconciliation or {}).get("chosen_source", "")),
            },
        }
    return {}


def _remove_answer_issues_for_question(answer_issues: List[Dict[str, Any]], question_id: str, codes: set[str]) -> None:
    answer_issues[:] = [
        issue
        for issue in answer_issues
        if not (str(issue.get("question_id", "")) == str(question_id) and str(issue.get("code", "")) in codes)
    ]


def _apply_peer_fill_if_available(
    *,
    question: ParsedQuestion,
    siblings: List[ParsedQuestion],
    answer_issues: List[Dict[str, Any]],
) -> bool:
    if question.reconciliation and str(question.reconciliation.get("status", "")) not in {"blocked"}:
        return False
    if str((question.answer_key or {}).get("mode", "none")) != "none":
        return False

    group_anchor = min(siblings, key=lambda q: (q.start_line, q.item_id)) if siblings else question
    objective_siblings = [q for q in siblings if _question_answer_mode_family(q.question_type) != "unknown"]
    if objective_siblings:
        group_anchor = min(objective_siblings, key=lambda q: (q.start_line, q.item_id))
    if group_anchor.item_id != question.item_id:
        return False

    target_family = _question_answer_mode_family(question.question_type)
    usable_peers = [
        sibling
        for sibling in siblings
        if sibling.item_id != question.item_id
        and str((sibling.answer_key or {}).get("mode", "none")) in {"single_choice", "boolean_group", "short_answer"}
        and str((sibling.reconciliation or {}).get("status", "")) in {"resolved", "resolved_with_fill", "resolved_normalized_equivalent"}
    ]
    if not usable_peers:
        return False

    if target_family == "unknown":
        peer_modes = {str((peer.answer_key or {}).get("mode", "none")) for peer in usable_peers}
        if len(peer_modes) != 1:
            return False
        chosen_peer = sorted(usable_peers, key=lambda peer: (peer.start_line, peer.item_id))[0]
    else:
        matching_peers = [peer for peer in usable_peers if str((peer.answer_key or {}).get("mode", "none")) == target_family]
        if not matching_peers:
            return False
        if target_family == "single_choice":
            values = sorted({str((peer.answer_key or {}).get("value", "")) for peer in matching_peers if (peer.answer_key or {}).get("value")})
            if len(values) > 1:
                answer_issues.append(
                    _build_answer_issue(
                        code="answer_source_conflict",
                        severity="blocker",
                        message=f"Conflicting peer single-choice answers for question {question.question_number}: {values}",
                        exam_id=question.exam_id,
                        question_id=question.item_id,
                        line=question.start_line,
                        stage="answer_reconciliation",
                    )
                )
                return False
        elif target_family == "boolean_group":
            normalized = []
            for peer in matching_peers:
                subanswers = dict((peer.answer_key or {}).get("subanswers", {}) or {})
                normalized.append(tuple(sorted((k, bool(v)) for k, v in subanswers.items())))
            if len({tuple_value for tuple_value in normalized}) > 1:
                answer_issues.append(
                    _build_answer_issue(
                        code="answer_source_conflict",
                        severity="blocker",
                        message=f"Conflicting peer boolean answers for question {question.question_number}",
                        exam_id=question.exam_id,
                        question_id=question.item_id,
                        line=question.start_line,
                        stage="answer_reconciliation",
                    )
                )
                return False
        elif target_family == "short_answer":
            values = sorted(
                {
                    str((answer or {}).get("normalized", ""))
                    for peer in matching_peers
                    for answer in (peer.answer_key or {}).get("accepted_answers", []) or []
                    if str((answer or {}).get("normalized", ""))
                }
            )
            if len(values) > 1:
                answer_issues.append(
                    _build_answer_issue(
                        code="short_answer_value_conflict",
                        severity="blocker",
                        message=f"Conflicting peer short-answer values for question {question.question_number}: {values}",
                        exam_id=question.exam_id,
                        question_id=question.item_id,
                        line=question.start_line,
                        stage="answer_reconciliation",
                    )
                )
                return False
        chosen_peer = sorted(matching_peers, key=lambda peer: (peer.start_line, peer.item_id))[0]

    peer_source = _build_peer_answer_source(chosen_peer)
    if not peer_source:
        return False

    question.answer_sources = list(question.answer_sources or [])
    if all(str(source.get("source", "")) != "same_question_number_peer" for source in question.answer_sources):
        question.answer_sources.append(peer_source)

    question.answer_key = dict(chosen_peer.answer_key or {})
    question.reconciliation = {
        "status": "resolved_with_fill",
        "chosen_source": "same_question_number_peer",
        "notes": [
            f"filled from sibling question block {chosen_peer.item_id} at line {chosen_peer.start_line}",
        ],
    }

    question.qa_flags = [flag for flag in (question.qa_flags or []) if flag != "canonical_answer_missing"]
    if all(flag != "answer_resolved_from_peer_question" for flag in question.qa_flags):
        question.qa_flags.append("answer_resolved_from_peer_question")

    _remove_answer_issues_for_question(answer_issues, question.item_id, {"canonical_answer_missing"})
    answer_issues.append(
        _build_answer_issue(
            code="answer_resolved_from_peer_question",
            severity="info",
            message=(
                f"Canonical answer filled from sibling question block {chosen_peer.item_id} "
                f"for question {question.question_number}"
            ),
            exam_id=question.exam_id,
            question_id=question.item_id,
            line=question.start_line,
            stage="answer_reconciliation",
        )
    )
    return True


def _merge_answer_findings(
    *,
    qa_report: Dict[str, Any],
    answer_issues: List[Dict[str, Any]],
) -> None:
    findings: List[Dict[str, Any]] = list(qa_report.get("publish_gate_findings", []))
    aggregated: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for issue in answer_issues:
        code = str(issue.get("code", "answer_issue"))
        severity = str(issue.get("severity", "warning"))
        key = (code, severity)
        if key not in aggregated:
            aggregated[key] = {
                "metric": code,
                "title": code.replace("_", " ").capitalize(),
                "severity": severity,
                "value": 0,
                "recommendation": "Review answer extraction/reconciliation evidence and resolve conflict before publish.",
            }
        aggregated[key]["value"] += 1
    findings.extend(aggregated.values())
    summary, verdict, legacy = _recompute_publish_gate_from_findings(findings)
    qa_report["publish_gate_findings"] = findings
    qa_report["publish_gate_summary"] = summary
    qa_report["publish_verdict"] = verdict
    qa_report["publish_verdict_legacy"] = legacy


def _is_objective_answer_question(question: ParsedQuestion) -> bool:
    answer_mode = str((question.answer_key or {}).get("mode", "none"))
    if answer_mode in {"single_choice", "boolean_group", "short_answer"}:
        return True
    return question.question_type in {"single_choice", "multiple_choice", "true_false", "short_answer"}


def _retune_answer_summary_zone_missing_issue(
    *,
    answer_summary: Dict[str, Any],
    answer_issues: List[Dict[str, Any]],
    questions: List[ParsedQuestion],
) -> None:
    if bool(answer_summary.get("present")):
        return

    missing_issues = [issue for issue in answer_issues if str(issue.get("code", "")) == "answer_summary_zone_missing"]
    if not missing_issues:
        return

    objective_questions = [question for question in questions if _is_objective_answer_question(question)]
    resolved_statuses = {"resolved", "resolved_with_fill", "resolved_normalized_equivalent"}
    unresolved_statuses = {"conflict", "needs_review", "blocked"}

    if not objective_questions:
        target_severity = "info"
        rationale = "No answer summary zone detected; bundle has no objective-answer questions that require summary reconciliation."
    else:
        strong_local_count = 0
        unresolved_count = 0
        for question in objective_questions:
            status = str(question.reconciliation.get("status", ""))
            if status in unresolved_statuses:
                unresolved_count += 1

            answer_mode = str((question.answer_key or {}).get("mode", "none"))
            local_sources = [source for source in question.answer_sources if str(source.get("source", "")) == "local_formatting"]
            best_local = None
            if local_sources:
                best_local = sorted(
                    local_sources,
                    key=lambda source: float(source.get("confidence", 0.0) or 0.0),
                    reverse=True,
                )[0]
            local_confidence = float((best_local or {}).get("confidence", 0.0) or 0.0)
            local_mode = str((best_local or {}).get("details", {}).get("mode", ""))
            mode_matches = local_mode == answer_mode or not local_mode
            if (
                best_local
                and answer_mode in {"single_choice", "boolean_group", "short_answer"}
                and status in resolved_statuses
                and local_confidence >= 0.88
                and mode_matches
            ):
                strong_local_count += 1

        local_coverage = strong_local_count / len(objective_questions)
        if unresolved_count == 0 and local_coverage >= 0.85:
            target_severity = "info"
            rationale = (
                "No answer summary zone detected; local answer extraction is strong and complete "
                f"({strong_local_count}/{len(objective_questions)} objective questions, unresolved={unresolved_count})."
            )
        else:
            target_severity = "warning"
            rationale = (
                "No answer summary zone detected; local answer extraction is incomplete or less reliable "
                f"({strong_local_count}/{len(objective_questions)} objective questions, unresolved={unresolved_count})."
            )

    for issue in missing_issues:
        issue["severity"] = target_severity
        issue["message"] = rationale

    summary_issues = answer_summary.get("issues", [])
    if isinstance(summary_issues, list):
        for issue in summary_issues:
            if str(issue.get("code", "")) != "answer_summary_zone_missing":
                continue
            issue["severity"] = target_severity
            issue["message"] = rationale

    answer_summary["qa_flags"] = [
        {
            "code": str(issue.get("code", "answer_issue")),
            "severity": str(issue.get("severity", "warning")),
            "message": str(issue.get("message", "")),
        }
        for issue in summary_issues
        if isinstance(issue, dict)
    ]

    detection = answer_summary.get("detection", {})
    if isinstance(detection, dict):
        parser_notes = detection.get("parser_notes")
        if not isinstance(parser_notes, list):
            parser_notes = []
        tuning_note = f"answer_summary_zone_missing severity tuned to {target_severity}"
        if tuning_note not in parser_notes:
            parser_notes.append(tuning_note)
        detection["parser_notes"] = parser_notes
        answer_summary["detection"] = detection


def _resolve_answer_for_question(
    *,
    question: ParsedQuestion,
    local_source: Dict[str, Any],
    summary_source: Dict[str, Any],
    solution_source: Dict[str, Any],
    rubric_source: Dict[str, Any],
    document_family: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    qa_flags: List[str] = []
    answer_sources: List[Dict[str, Any]] = []

    manual_override = dict(question.manual_answer_override or {})
    if local_source.get("mode") != "none":
        answer_sources.append(
            {
                "source": str(local_source.get("source", "local_formatting")),
                "confidence": _safe_float(local_source.get("confidence", 0.0)),
                "details": {"mode": local_source.get("mode")},
            }
        )
    if summary_source.get("mode") != "none":
        answer_sources.append(
            {
                "source": str(summary_source.get("source", "answer_summary_table")),
                "confidence": _safe_float(summary_source.get("confidence", 0.0)),
                "details": {"mode": summary_source.get("mode")},
            }
        )
    if solution_source.get("mode") != "none":
        answer_sources.append(
            {
                "source": str(solution_source.get("source", "solution_explicit")),
                "confidence": _safe_float(solution_source.get("confidence", 0.0)),
                "details": {"mode": solution_source.get("mode")},
            }
        )
    if rubric_source.get("mode") == "rubric":
        answer_sources.append(
            {
                "source": str(rubric_source.get("source", "rubric_marker")),
                "confidence": _safe_float(rubric_source.get("confidence", 0.0), 0.9),
                "details": {"mode": "rubric"},
            }
        )

    if manual_override:
        answer_sources.append(
            {
                "source": "manual_override",
                "confidence": 1.0,
                "details": {"mode": manual_override.get("mode", "")},
            }
        )

    mode_hint = "none"
    if manual_override:
        mode_hint = str(manual_override.get("mode", "none"))
    elif rubric_source.get("mode") == "rubric":
        mode_hint = "rubric"
    elif question.question_type == "true_false":
        mode_hint = "boolean_group"
    elif question.question_type == "short_answer":
        mode_hint = "short_answer"
    elif question.question_type == "essay":
        mode_hint = "rubric"
    elif question.question_type in {"single_choice", "multiple_choice"}:
        mode_hint = "single_choice"
    elif solution_source.get("mode") in {"single_choice", "boolean_group", "short_answer"}:
        mode_hint = str(solution_source.get("mode"))
    elif summary_source.get("mode") not in {None, "none"}:
        mode_hint = str(summary_source.get("mode"))
    elif local_source.get("mode") not in {None, "none"}:
        mode_hint = str(local_source.get("mode"))
    elif question.question_type == "unknown" and solution_source.get("mode") in {"single_choice", "boolean_group", "short_answer"}:
        # Unknown question types still benefit from an explicit solution cue when the
        # extractor has already recognized a concrete answer mode. This stays conservative
        # because the solution source must already have passed the mode-specific parser.
        mode_hint = str(solution_source.get("mode"))

    reconciliation = {"status": "needs_review", "chosen_source": "", "notes": []}
    answer_key: Dict[str, Any] = {"mode": "none"}
    family = document_family if document_family in DOCUMENT_FAMILY_PRIORITY_PATHS else DOCUMENT_FAMILY_UNKNOWN
    family_priority_path = _family_source_priority_path(family)

    def _family_resolution_issue_severity(primary_source: str) -> str:
        if family == DOCUMENT_FAMILY_OBJECTIVE_INLINE and primary_source in {"solution_explicit", "solution_inferred", "anchored_solution_block"}:
            return "info"
        if family == DOCUMENT_FAMILY_OBJECTIVE_END_KEY and (
            primary_source.startswith("answer_summary") or primary_source.startswith("anchored_solution_block")
        ):
            return "info"
        if family == DOCUMENT_FAMILY_RUBRIC and primary_source in {"rubric_marker", "anchored_rubric_block"}:
            return "info"
        return "warning"

    if mode_hint == "single_choice":
        values: Dict[str, str] = {}
        for source in (local_source, summary_source, solution_source):
            if source.get("mode") == "single_choice" and source.get("value"):
                values[str(source.get("source", "unknown"))] = str(source.get("value"))
        if manual_override and str(manual_override.get("mode")) == "single_choice":
            override_value = _normalize_choice_value(str(manual_override.get("value", "")))
            if override_value is not None:
                answer_key = {"mode": "single_choice", "value": override_value}
                reconciliation = {"status": "resolved", "chosen_source": "manual_override", "notes": []}
                if values and any(v != override_value for v in values.values()):
                    issues.append(
                        _build_answer_issue(
                            code="answer_source_conflict",
                            severity="warning",
                            message=f"manual_override={override_value} conflicts with detected values {values}",
                            exam_id=question.exam_id,
                            question_id=question.item_id,
                            line=question.start_line,
                            stage="answer_reconciliation",
                        )
                    )
                    reconciliation["notes"].append("manual override applied; conflicts retained as warning evidence")
            else:
                issues.append(
                    _build_answer_issue(
                        code="summary_mapping_invalid",
                        severity="blocker",
                        message="manual answer_override single_choice value is invalid",
                        exam_id=question.exam_id,
                        question_id=question.item_id,
                        line=question.start_line,
                        stage="answer_reconciliation",
                    )
                )
        elif not values:
            issues.append(
                _build_answer_issue(
                    code="canonical_answer_missing",
                    severity="blocker",
                    message="Canonical answer missing for single_choice question",
                    exam_id=question.exam_id,
                    question_id=question.item_id,
                    line=question.start_line,
                    stage="answer_reconciliation",
                )
            )
            reconciliation = {"status": "blocked", "chosen_source": "", "notes": ["no answer source available"]}
        else:
            unique_values = sorted(set(values.values()))
            primary_source = _select_priority_source_name(values, family)
            if len(unique_values) == 1:
                chosen = unique_values[0]
                answer_key = {"mode": "single_choice", "value": chosen}
                if primary_source.startswith("answer_summary"):
                    if "local_formatting" not in values:
                        reconciliation = {
                            "status": "resolved_with_fill",
                            "chosen_source": primary_source,
                            "notes": ["summary filled missing local answer"],
                        }
                        issues.append(
                            _build_answer_issue(
                                code="answer_resolved_from_summary_only",
                                severity=_family_resolution_issue_severity(primary_source),
                                message="Answer resolved from summary source only",
                                exam_id=question.exam_id,
                                question_id=question.item_id,
                                line=question.start_line,
                                stage="answer_reconciliation",
                            )
                        )
                    else:
                        reconciliation = {
                            "status": "resolved",
                            "chosen_source": primary_source,
                            "notes": ["consistent sources"],
                        }
                        if len(values) > 1:
                            issues.append(
                                _build_answer_issue(
                                    code="answer_summary_redundant_but_consistent",
                                    severity="info",
                                    message="Summary/local sources are redundant but consistent",
                                    exam_id=question.exam_id,
                                    question_id=question.item_id,
                                    line=question.start_line,
                                    stage="answer_reconciliation",
                                )
                            )
                elif primary_source == "anchored_solution_block":
                    reconciliation = {
                        "status": "resolved",
                        "chosen_source": primary_source,
                        "notes": ["anchored solution block"],
                    }
                    if len(values) == 1:
                        issues.append(
                            _build_answer_issue(
                                code="answer_resolved_from_solution_only",
                                severity="info",
                                message="Answer resolved from anchored solution block",
                                exam_id=question.exam_id,
                                question_id=question.item_id,
                                line=question.start_line,
                                stage="answer_reconciliation",
                            )
                        )
                elif primary_source in {"solution_explicit", "solution_inferred"}:
                    if family == DOCUMENT_FAMILY_OBJECTIVE_INLINE:
                        reconciliation = {
                            "status": "resolved",
                            "chosen_source": primary_source,
                            "notes": ["solution primary for inline-solution family"],
                        }
                        if len(values) == 1:
                            issues.append(
                                _build_answer_issue(
                                    code="answer_resolved_from_solution_only",
                                    severity="info",
                                    message="Answer resolved from inline solution source",
                                    exam_id=question.exam_id,
                                    question_id=question.item_id,
                                    line=question.start_line,
                                    stage="answer_reconciliation",
                                )
                            )
                    else:
                        reconciliation = {
                            "status": "needs_review",
                            "chosen_source": primary_source,
                            "notes": ["solution-only cue used as fallback"],
                        }
                        issues.append(
                            _build_answer_issue(
                                code="answer_resolved_from_solution_only",
                                severity=_family_resolution_issue_severity(primary_source),
                                message="Answer resolved from solution-only explicit cue",
                                exam_id=question.exam_id,
                                question_id=question.item_id,
                                line=question.start_line,
                                stage="answer_reconciliation",
                            )
                        )
                elif primary_source in {"rubric_marker", "anchored_rubric_block"}:
                    reconciliation = {
                        "status": "resolved",
                        "chosen_source": primary_source,
                        "notes": ["rubric marker extracted" if primary_source == "rubric_marker" else "anchored rubric block"],
                    }
                else:
                    reconciliation = {
                        "status": "resolved",
                        "chosen_source": primary_source or "+".join(sorted(values.keys())),
                        "notes": ["consistent sources"],
                    }
                    if len(values) > 1:
                        issues.append(
                            _build_answer_issue(
                                code="answer_summary_redundant_but_consistent",
                                severity="info",
                                message="Summary/local sources are redundant but consistent",
                                exam_id=question.exam_id,
                                question_id=question.item_id,
                                line=question.start_line,
                                stage="answer_reconciliation",
                            )
                        )
            else:
                issues.append(
                    _build_answer_issue(
                        code="answer_source_conflict",
                        severity="blocker",
                        message=f"Conflicting single-choice sources: {values}",
                        exam_id=question.exam_id,
                        question_id=question.item_id,
                        line=question.start_line,
                        stage="answer_reconciliation",
                    )
                )
                if "local_formatting" in values and "answer_summary_table" in values and values["local_formatting"] != values["answer_summary_table"]:
                    issues.append(
                        _build_answer_issue(
                            code="summary_vs_local_conflict",
                            severity="blocker",
                            message=f"Summary/local mismatch: {values['answer_summary_table']} vs {values['local_formatting']}",
                            exam_id=question.exam_id,
                            question_id=question.item_id,
                            line=question.start_line,
                            stage="answer_reconciliation",
                        )
                    )
                if "answer_summary_table" in values and "solution_explicit" in values and values["answer_summary_table"] != values["solution_explicit"]:
                    issues.append(
                        _build_answer_issue(
                            code="summary_vs_solution_conflict",
                            severity="blocker",
                            message=f"Summary/solution mismatch: {values['answer_summary_table']} vs {values['solution_explicit']}",
                            exam_id=question.exam_id,
                            question_id=question.item_id,
                            line=question.start_line,
                            stage="answer_reconciliation",
                        )
                    )
                if "local_formatting" in values and "solution_explicit" in values and values["local_formatting"] != values["solution_explicit"]:
                    issues.append(
                        _build_answer_issue(
                            code="local_vs_solution_conflict",
                            severity="blocker",
                            message=f"Local/solution mismatch: {values['local_formatting']} vs {values['solution_explicit']}",
                            exam_id=question.exam_id,
                            question_id=question.item_id,
                            line=question.start_line,
                            stage="answer_reconciliation",
                        )
                    )
                reconciliation = {
                    "status": "conflict",
                    "chosen_source": "",
                    "notes": [f"conflict: {values}"],
                }

    elif mode_hint == "boolean_group":
        source_subanswers: Dict[str, Dict[str, bool]] = {}
        for source in (local_source, summary_source, solution_source):
            if source.get("mode") == "boolean_group":
                source_subanswers[str(source.get("source", "unknown"))] = dict(source.get("subanswers", {}))
        if manual_override and str(manual_override.get("mode")) == "boolean_group":
            source_subanswers["manual_override"] = {
                str(k).lower(): bool(v) for k, v in dict(manual_override.get("subanswers", {})).items()
            }

        if not source_subanswers:
            issues.append(
                _build_answer_issue(
                    code="canonical_answer_missing",
                    severity="blocker",
                    message="Canonical boolean_group answer missing",
                    exam_id=question.exam_id,
                    question_id=question.item_id,
                    line=question.start_line,
                    stage="answer_reconciliation",
                )
            )
            reconciliation = {"status": "blocked", "chosen_source": "", "notes": ["no boolean subanswers found"]}
        else:
            labels = sorted({label for sub in source_subanswers.values() for label in sub.keys() if label in {"a", "b", "c", "d"}})
            merged: Dict[str, bool] = {}
            conflict_labels: List[str] = []
            for label in labels:
                label_values = {src: vals[label] for src, vals in source_subanswers.items() if label in vals}
                unique_values = sorted(set(label_values.values()))
                if len(unique_values) == 1:
                    merged[label] = unique_values[0]
                elif "manual_override" in label_values:
                    merged[label] = label_values["manual_override"]
                    issues.append(
                        _build_answer_issue(
                            code="boolean_subanswer_conflict",
                            severity="warning",
                            message=f"manual override kept {label}={merged[label]} over {label_values}",
                            exam_id=question.exam_id,
                            question_id=question.item_id,
                            line=question.start_line,
                            stage="answer_reconciliation",
                        )
                    )
                else:
                    conflict_labels.append(label)
                    issues.append(
                        _build_answer_issue(
                            code="boolean_subanswer_conflict",
                            severity="blocker",
                            message=f"Conflicting boolean subanswer for {label}: {label_values}",
                            exam_id=question.exam_id,
                            question_id=question.item_id,
                            line=question.start_line,
                            stage="answer_reconciliation",
                        )
                    )

            if conflict_labels and "manual_override" not in source_subanswers:
                reconciliation = {
                    "status": "blocked",
                    "chosen_source": "",
                    "notes": [f"boolean conflicts in labels: {','.join(conflict_labels)}"],
                }
            elif merged:
                answer_key = {"mode": "boolean_group", "subanswers": merged}
                fill_used = "local_formatting" in source_subanswers and "answer_summary_table" in source_subanswers and any(
                    label not in source_subanswers.get("local_formatting", {}) and label in source_subanswers.get("answer_summary_table", {})
                    for label in merged
                )
                reconciliation = {
                    "status": "resolved_with_fill" if fill_used else "resolved",
                    "chosen_source": "manual_override" if "manual_override" in source_subanswers else "multi_source",
                    "notes": ["summary filled missing local values"] if fill_used else ["boolean answers reconciled"],
                }
            else:
                issues.append(
                    _build_answer_issue(
                        code="canonical_answer_missing",
                        severity="blocker",
                        message="No usable boolean subanswers after reconciliation",
                        exam_id=question.exam_id,
                        question_id=question.item_id,
                        line=question.start_line,
                        stage="answer_reconciliation",
                    )
                )
                reconciliation = {"status": "blocked", "chosen_source": "", "notes": ["no resolved subanswers"]}

    elif mode_hint == "short_answer":
        candidates: Dict[str, Dict[str, str]] = {}
        for source in (local_source, summary_source, solution_source):
            if source.get("mode") == "short_answer":
                answers = source.get("accepted_answers", [])
                if answers:
                    candidates[str(source.get("source", "unknown"))] = dict(answers[0])

        if manual_override and str(manual_override.get("mode")) == "short_answer":
            override_answers = manual_override.get("accepted_answers", [])
            if override_answers:
                candidates["manual_override"] = dict(override_answers[0])
            elif manual_override.get("value"):
                candidates["manual_override"] = _normalize_short_answer_value(str(manual_override.get("value")))

        if not candidates:
            issues.append(
                _build_answer_issue(
                    code="canonical_answer_missing",
                    severity="blocker",
                    message="Canonical short_answer missing",
                    exam_id=question.exam_id,
                    question_id=question.item_id,
                    line=question.start_line,
                    stage="answer_reconciliation",
                )
            )
            reconciliation = {"status": "blocked", "chosen_source": "", "notes": ["no short-answer source"]}
        else:
            unique_norm = sorted({_normalize_space(v.get("normalized", "")).lower() for v in candidates.values() if v.get("normalized", "")})
            if len(unique_norm) <= 1:
                chosen = next(iter(candidates.values()))
                answer_key = {"mode": "short_answer", "accepted_answers": [chosen]}
                raw_values = {_normalize_space(v.get("raw", "")) for v in candidates.values()}
                primary_source = _select_priority_source_name(candidates, family)
                if primary_source == "anchored_solution_block":
                    reconciliation = {
                        "status": "resolved",
                        "chosen_source": primary_source,
                        "notes": ["anchored solution block"],
                    }
                    if len(candidates) == 1:
                        issues.append(
                            _build_answer_issue(
                                code="answer_resolved_from_solution_only",
                                severity="info",
                                message="Short answer resolved from anchored solution block",
                                exam_id=question.exam_id,
                                question_id=question.item_id,
                                line=question.start_line,
                                stage="answer_reconciliation",
                            )
                        )
                elif primary_source in {"solution_explicit", "solution_inferred"} and family == DOCUMENT_FAMILY_OBJECTIVE_INLINE:
                    reconciliation = {
                        "status": "resolved",
                        "chosen_source": primary_source,
                        "notes": ["solution primary for inline-solution family"],
                    }
                    if len(candidates) == 1:
                        issues.append(
                            _build_answer_issue(
                                code="answer_resolved_from_solution_only",
                                severity="info",
                                message="Short answer resolved from inline solution source",
                                exam_id=question.exam_id,
                                question_id=question.item_id,
                                line=question.start_line,
                                stage="answer_reconciliation",
                            )
                        )
                elif len(raw_values) > 1:
                    reconciliation = {
                        "status": "resolved_normalized_equivalent",
                        "chosen_source": primary_source or "multi_source",
                        "notes": ["local and summary normalized to equivalent value"],
                    }
                elif primary_source.startswith("answer_summary"):
                    reconciliation = {
                        "status": "resolved_with_fill",
                        "chosen_source": primary_source,
                        "notes": ["summary filled missing local short answer"],
                    }
                    issues.append(
                        _build_answer_issue(
                            code="answer_resolved_from_summary_only",
                            severity=_family_resolution_issue_severity(primary_source),
                            message="Short answer resolved from summary only",
                            exam_id=question.exam_id,
                            question_id=question.item_id,
                            line=question.start_line,
                            stage="answer_reconciliation",
                        )
                    )
                else:
                    reconciliation = {"status": "resolved", "chosen_source": primary_source or "multi_source", "notes": ["short answer reconciled"]}
            else:
                issues.append(
                    _build_answer_issue(
                        code="short_answer_value_conflict",
                        severity="blocker",
                        message=f"Conflicting short-answer values: {candidates}",
                        exam_id=question.exam_id,
                        question_id=question.item_id,
                        line=question.start_line,
                        stage="answer_reconciliation",
                    )
                )
                if "answer_summary_table" in candidates and "solution_explicit" in candidates and not _answer_values_equivalent(
                    candidates["answer_summary_table"], candidates["solution_explicit"]
                ):
                    issues.append(
                        _build_answer_issue(
                            code="summary_vs_solution_conflict",
                            severity="blocker",
                            message=f"Summary/solution short-answer mismatch: {candidates}",
                            exam_id=question.exam_id,
                            question_id=question.item_id,
                            line=question.start_line,
                            stage="answer_reconciliation",
                        )
                    )
                if "local_formatting" in candidates and "solution_explicit" in candidates and not _answer_values_equivalent(
                    candidates["local_formatting"], candidates["solution_explicit"]
                ):
                    issues.append(
                        _build_answer_issue(
                            code="local_vs_solution_conflict",
                            severity="blocker",
                            message=f"Local/solution short-answer mismatch: {candidates}",
                            exam_id=question.exam_id,
                            question_id=question.item_id,
                            line=question.start_line,
                            stage="answer_reconciliation",
                        )
                    )
                reconciliation = {"status": "needs_review", "chosen_source": "", "notes": [f"conflicting values: {candidates}"]}

    elif mode_hint == "rubric":
        if manual_override and str(manual_override.get("mode")) == "rubric":
            answer_key = {"mode": "rubric"}
            reconciliation = {"status": "resolved", "chosen_source": "manual_override", "notes": ["manual rubric override"]}
            rubric_source = {
                "mode": "rubric",
                "rubric": {
                    "mode": "analytic",
                    "rubric_text": str(manual_override.get("rubric_text", "")),
                    "blocks": manual_override.get("blocks", []),
                },
                "confidence": 1.0,
            }
        elif rubric_source.get("mode") == "rubric":
            answer_key = {"mode": "rubric"}
            chosen_rubric_source = str(rubric_source.get("source", "rubric_marker"))
            reconciliation = {"status": "resolved", "chosen_source": chosen_rubric_source, "notes": ["rubric marker extraction"]}
        else:
            if solution_source.get("mode") != "none":
                issues.append(
                    _build_answer_issue(
                        code="rubric_source_conflict",
                        severity="warning",
                        message="Essay has solution cue but missing rubric marker",
                        exam_id=question.exam_id,
                        question_id=question.item_id,
                        line=question.start_line,
                        stage="answer_reconciliation",
                    )
                )
                reconciliation = {"status": "needs_review", "chosen_source": str(solution_source.get("source", "solution_explicit")), "notes": ["missing rubric"]}
            else:
                issues.append(
                    _build_answer_issue(
                        code="canonical_answer_missing",
                        severity="blocker",
                        message="Essay missing canonical rubric answer",
                        exam_id=question.exam_id,
                        question_id=question.item_id,
                        line=question.start_line,
                        stage="answer_reconciliation",
                    )
                )
                reconciliation = {"status": "blocked", "chosen_source": "", "notes": ["missing rubric source"]}

    else:
        issues.append(
            _build_answer_issue(
                code="canonical_answer_missing",
                severity="blocker",
                message="Canonical answer mode could not be inferred",
                exam_id=question.exam_id,
                question_id=question.item_id,
                line=question.start_line,
                stage="answer_reconciliation",
            )
        )
        reconciliation = {"status": "blocked", "chosen_source": "", "notes": ["unknown answer mode"]}

    for issue in issues:
        qa_flags.append(str(issue.get("code", "")))

    answer_detection = dict(local_source.get("answer_detection", {})) if isinstance(local_source.get("answer_detection", {}), dict) else {}
    rubric = dict(rubric_source.get("rubric", {})) if isinstance(rubric_source.get("rubric", {}), dict) else {}
    rubric_detection = (
        dict(rubric_source.get("rubric_detection", {}))
        if isinstance(rubric_source.get("rubric_detection", {}), dict)
        else {}
    )

    return answer_key, answer_sources, reconciliation, issues, answer_detection, {"rubric": rubric, "rubric_detection": rubric_detection, "qa_flags": qa_flags}


def run_answer_pipeline(
    parsed: Dict[str, Any],
    answer_summary: Dict[str, Any],
    document_family_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    questions: List[ParsedQuestion] = list(parsed.get("questions", []))
    family = str((document_family_info or {}).get("family", DOCUMENT_FAMILY_UNKNOWN))
    family_priority_path = list(
        (document_family_info or {}).get("priority_path", _family_source_priority_path(family))
    )
    anchored_index = _build_anchored_source_index(questions)
    summary_index, mapping_issues = _build_answer_summary_index(answer_summary=answer_summary, questions=questions)
    answer_issues: List[Dict[str, Any]] = list(answer_summary.get("issues", [])) + mapping_issues + list(anchored_index.get("issues", []))

    for question in questions:
        local_source, local_issues = _extract_local_answer(question)
        answer_issues.extend(local_issues)

        summary_entry = summary_index.get(question.item_id)
        if summary_entry:
            summary_source = {
                **summary_entry,
                "source": "answer_summary_table" if answer_summary.get("source_type") in {"table", "mixed"} else "answer_summary_list",
                "confidence": _safe_float(answer_summary.get("detection", {}).get("confidence", 0.0), 0.85),
            }
        else:
            summary_source = {"mode": "none", "source": "answer_summary_table", "confidence": 0.0}

        summary_available = str(summary_source.get("mode", "none")) != "none"
        anchored_solution_source = dict(anchored_index.get("solution_sources", {}).get(question.item_id, {"mode": "none", "source": "anchored_solution_block", "confidence": 0.0}))
        anchored_rubric_source = dict(anchored_index.get("rubric_sources", {}).get(question.item_id, {"mode": "none", "source": "anchored_rubric_block", "confidence": 0.0}))
        solution_source = _extract_solution_answer(
            question,
            family,
            summary_available,
            anchored_solution_source=anchored_solution_source,
        )
        rubric, rubric_detection = _extract_rubric(question, anchored_rubric_source=anchored_rubric_source)
        rubric_source = {
            "mode": "rubric" if rubric else "none",
            "rubric": rubric,
            "rubric_detection": rubric_detection,
            "confidence": _safe_float(rubric_detection.get("confidence", 0.0), 0.0),
        }

        answer_key, answer_sources, reconciliation, reconcile_issues, answer_detection, extras = _resolve_answer_for_question(
            question=question,
            local_source=local_source,
            summary_source=summary_source,
            solution_source=solution_source,
            rubric_source=rubric_source,
            document_family=family,
        )
        answer_issues.extend(reconcile_issues)

        question.answer_key = answer_key
        question.answer_sources = answer_sources
        question.reconciliation = reconciliation
        question.answer_detection = answer_detection
        question.rubric = dict(extras.get("rubric", {}))
        question.rubric_detection = dict(extras.get("rubric_detection", {}))
        question.qa_flags = list(dict.fromkeys(question.qa_flags + list(extras.get("qa_flags", []))))
        question.answer_detection = {
            **(question.answer_detection or {}),
            "document_family": family,
            "source_priority_path": family_priority_path,
            "anchored_solution_block_found": question.item_id in anchored_index.get("solution_blocks_by_item_id", {}),
            "anchored_rubric_block_found": question.item_id in anchored_index.get("rubric_blocks_by_item_id", {}),
            "anchored_solution_anchor": str(
                (solution_source.get("details", {}) if isinstance(solution_source.get("details", {}), dict) else {}).get("anchor_text", "")
                or anchored_index.get("solution_blocks_by_item_id", {}).get(question.item_id, {}).get("anchor_text", "")
            ),
            "anchored_rubric_anchor": str(
                (rubric_source.get("details", {}) if isinstance(rubric_source.get("details", {}), dict) else {}).get("anchor_text", "")
                or anchored_index.get("rubric_blocks_by_item_id", {}).get(question.item_id, {}).get("anchor_text", "")
            ),
        }

    questions_by_group: Dict[Tuple[str, int], List[ParsedQuestion]] = {}
    for question in questions:
        questions_by_group.setdefault((question.exam_id, question.question_number), []).append(question)
    for siblings in questions_by_group.values():
        siblings.sort(key=lambda q: (q.start_line, q.item_id))

    for question in questions:
        siblings = questions_by_group.get((question.exam_id, question.question_number), [])
        _apply_peer_fill_if_available(question=question, siblings=siblings, answer_issues=answer_issues)

    _retune_answer_summary_zone_missing_issue(
        answer_summary=answer_summary,
        answer_issues=answer_issues,
        questions=questions,
    )

    objective_questions = [question for question in questions if _is_objective_answer_question(question)]
    rubric_questions = [question for question in questions if str(question.answer_key.get("mode", "")) == "rubric" or question.question_type == "essay"]
    anchored_solution_found = sum(1 for question in objective_questions if question.item_id in anchored_index.get("solution_blocks_by_item_id", {}))
    anchored_rubric_found = sum(1 for question in rubric_questions if question.item_id in anchored_index.get("rubric_blocks_by_item_id", {}))

    blocker_count = sum(1 for issue in answer_issues if issue.get("severity") == "blocker")
    warning_count = sum(1 for issue in answer_issues if issue.get("severity") == "warning")
    info_count = sum(1 for issue in answer_issues if issue.get("severity") == "info")
    canonical_missing_count = sum(1 for issue in answer_issues if issue.get("code") == "canonical_answer_missing")
    conflict_count = sum(1 for issue in answer_issues if "conflict" in str(issue.get("code", "")))
    unresolved_count = sum(
        1
        for question in questions
        if str(question.reconciliation.get("status", "")) in {"conflict", "needs_review", "blocked"}
    )

    parsed_summary = dict(parsed.get("summary", {}))
    parsed_summary["answer_issue_count"] = len(answer_issues)
    parsed_summary["answer_blocker_count"] = blocker_count
    parsed_summary["answer_warning_count"] = warning_count
    parsed_summary["answer_info_count"] = info_count
    parsed_summary["canonical_answer_missing_count"] = canonical_missing_count
    parsed_summary["answer_conflict_count"] = conflict_count
    parsed_summary["unresolved_reconciliation_count"] = unresolved_count
    parsed_summary["anchored_solution_block_count"] = anchored_solution_found
    parsed_summary["anchored_solution_block_missing_count"] = max(0, len(objective_questions) - anchored_solution_found)
    parsed_summary["anchored_rubric_block_count"] = anchored_rubric_found
    parsed_summary["anchored_rubric_block_missing_count"] = max(0, len(rubric_questions) - anchored_rubric_found)
    parsed_summary["anchored_solution_block_examples"] = list(anchored_index.get("solution_examples", []))
    parsed_summary["anchored_rubric_block_examples"] = list(anchored_index.get("rubric_examples", []))
    parsed["summary"] = parsed_summary

    parser_warnings: List[ParserWarning] = list(parsed.get("warnings", []))
    for issue in answer_issues:
        parser_warnings.append(
            ParserWarning(
                severity=str(issue.get("severity", "warning")),
                code=str(issue.get("code", "answer_issue")),
                message=str(issue.get("message", "Answer issue")),
                exam_id=str(issue.get("exam_id", "DE_UNKNOWN")),
                question_id=str(issue.get("question_id", "")),
                line=int(issue.get("line", 1) or 1),
            )
        )
    parser_warnings_sorted = sorted(
        parser_warnings,
        key=lambda w: (exam_sort_key(w.exam_id), w.question_id, w.line, w.code, w.message),
    )
    parsed["warnings"] = parser_warnings_sorted
    parsed["summary"]["warning_count"] = sum(
        1
        for warning in parser_warnings_sorted
        if str(warning.severity).lower() in {"warning", "error", "blocker"}
    )
    warning_codes_by_question: Dict[str, List[str]] = {}
    for warning in parser_warnings_sorted:
        if not warning.question_id:
            continue
        warning_codes_by_question.setdefault(warning.question_id, []).append(warning.code)
    for question in questions:
        merged_codes = sorted(set(question.warning_codes + warning_codes_by_question.get(question.item_id, [])))
        question.warning_codes = merged_codes

    sections: Dict[str, Dict[str, Any]] = {}
    for question in questions:
        section = sections.setdefault(
            question.exam_id,
            {
                "exam_id": question.exam_id,
                "question_count": 0,
                "asset_count": 0,
                "math_fragment_count": 0,
                "warning_count": 0,
                "avg_confidence": 0.0,
                "question_ids": [],
            },
        )
        section["question_count"] += 1
        section["asset_count"] += len(question.assets)
        section["math_fragment_count"] += len(question.math_fragments)
        section["warning_count"] += len(question.warning_codes)
        section["question_ids"].append(question.item_id)
    for exam_id, section in sections.items():
        scores = [q.parse_confidence for q in questions if q.exam_id == exam_id]
        section["avg_confidence"] = round(mean(scores), 3) if scores else 0.0
    parsed["sections"] = [sections[key] for key in sorted(sections.keys(), key=exam_sort_key)]

    return {
        "answer_summary": answer_summary,
        "answer_issues": answer_issues,
        "answer_qa_summary": {
            "issue_count": len(answer_issues),
            "blocker_count": blocker_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "canonical_answer_missing_count": canonical_missing_count,
            "conflict_count": conflict_count,
            "unresolved_reconciliation_count": unresolved_count,
            "anchored_solution_block_count": anchored_solution_found,
            "anchored_solution_block_missing_count": max(0, len(objective_questions) - anchored_solution_found),
            "anchored_rubric_block_count": anchored_rubric_found,
            "anchored_rubric_block_missing_count": max(0, len(rubric_questions) - anchored_rubric_found),
            "anchored_solution_block_examples": list(anchored_index.get("solution_examples", [])),
            "anchored_rubric_block_examples": list(anchored_index.get("rubric_examples", [])),
        },
    }


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load_override_manifest(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Override manifest root must be a JSON object")
    if payload.get("schema_version") != OVERRIDE_MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"Override manifest schema_version must be {OVERRIDE_MANIFEST_SCHEMA_VERSION}")
    overrides = payload.get("overrides")
    if not isinstance(overrides, list):
        raise ValueError("Override manifest 'overrides' must be a JSON array")
    return payload


def _question_matches_selector(selector: Dict[str, Any], question: ParsedQuestion) -> bool:
    exam_id = selector.get("exam_id")
    if exam_id is not None and str(exam_id) != question.exam_id:
        return False
    question_id = selector.get("question_id")
    if question_id is not None and str(question_id) != question.item_id:
        return False
    question_number = selector.get("question_number")
    if question_number is not None:
        try:
            if int(question_number) != int(question.question_number):
                return False
        except (TypeError, ValueError):
            return False
    return True


def _asset_matches_selector(selector: Dict[str, Any], question: ParsedQuestion, asset: Dict[str, Any]) -> bool:
    if not _question_matches_selector(selector, question):
        return False
    asset_id = selector.get("asset_id")
    if asset_id is not None and str(asset_id) != str(asset.get("asset_id", "")):
        return False
    asset_src = selector.get("asset_src")
    if asset_src is not None and str(asset_src) != str(asset.get("src", "")):
        return False
    asset_src_contains = selector.get("asset_src_contains")
    if asset_src_contains is not None and str(asset_src_contains) not in str(asset.get("src", "")):
        return False
    prog_id = selector.get("prog_id")
    if prog_id is not None and str(prog_id).lower() != str(asset.get("prog_id", "")).lower():
        return False
    source_ext = selector.get("source_ext")
    if source_ext is not None and str(source_ext).lower() != str(asset.get("source_ext", "")).lower():
        return False
    fallback_type = selector.get("fallback_type")
    if fallback_type is not None and str(fallback_type).lower() != str(asset.get("fallback_type", "")).lower():
        return False
    css_class_contains = selector.get("css_class_contains")
    if css_class_contains is not None and str(css_class_contains).lower() not in str(asset.get("css_class", "")).lower():
        return False
    return True


def _literal_replace_count(text: str, find_text: str, replace_text: str, max_replacements: Optional[int]) -> Tuple[str, int]:
    if not find_text:
        return text, 0
    if max_replacements is None:
        count = text.count(find_text)
        return text.replace(find_text, replace_text), count
    count = text.count(find_text)
    applied = min(count, max_replacements)
    return text.replace(find_text, replace_text, max_replacements), applied


def _apply_text_patch_to_question(question: ParsedQuestion, value: Dict[str, Any]) -> int:
    target = str(value.get("target", "visible_text"))
    match_mode = str(value.get("match_mode", "literal"))
    find_text = str(value.get("find", ""))
    replace_text = str(value.get("replace", ""))
    max_replacements = value.get("max_replacements")
    if isinstance(max_replacements, int) and max_replacements <= 0:
        max_replacements = None
    if not isinstance(max_replacements, int):
        max_replacements = None

    if target == "html":
        target = "visible_text"
    if target not in {"visible_text", "stem_html", "solution_html"}:
        return 0
    if match_mode not in OVERRIDE_TEXT_MATCH_MODE:
        return 0

    original = question.text_content
    replaced = original
    replacement_count = 0
    if match_mode == "literal":
        replaced, replacement_count = _literal_replace_count(original, find_text, replace_text, max_replacements)
    else:
        flags = re.MULTILINE
        count = 0 if max_replacements is None else max_replacements
        replaced, replacement_count = re.subn(find_text, replace_text, original, count=count, flags=flags)
    if replacement_count > 0:
        question.text_content = re.sub(r"\s+", " ", replaced).strip()
        question.prompt_preview = question.text_content[:260]
    return replacement_count


def _recompute_publish_gate_from_findings(findings: List[Dict[str, Any]]) -> Tuple[Dict[str, int], str, str]:
    summary = {"blocker": 0, "error": 0, "warning": 0, "info": 0}
    for finding in findings:
        severity = str(finding.get("severity", "")).lower()
        if severity in summary:
            summary[severity] += 1
    if summary["blocker"] > 0:
        verdict = "blocked"
    elif summary["error"] > 0 or summary["warning"] > 0:
        verdict = "needs_review"
    else:
        verdict = "safe_to_publish"
    legacy = "safe to publish" if verdict == "safe_to_publish" else "still needs cleanup"
    return summary, verdict, legacy


def _refresh_parsed_aggregates(parsed: Dict[str, Any]) -> None:
    questions: List[ParsedQuestion] = list(parsed.get("questions", []))
    warnings: List[ParserWarning] = list(parsed.get("warnings", []))

    sections: Dict[str, Dict[str, Any]] = {}
    for q in questions:
        section = sections.setdefault(
            q.exam_id,
            {
                "exam_id": q.exam_id,
                "question_count": 0,
                "asset_count": 0,
                "math_fragment_count": 0,
                "warning_count": 0,
                "avg_confidence": 0.0,
                "question_ids": [],
            },
        )
        section["question_count"] += 1
        section["asset_count"] += len(q.assets)
        section["math_fragment_count"] += len(q.math_fragments)
        section["warning_count"] += len(q.warning_codes)
        section["question_ids"].append(q.item_id)

    for exam_id, section in sections.items():
        scores = [q.parse_confidence for q in questions if q.exam_id == exam_id]
        section["avg_confidence"] = round(mean(scores), 3) if scores else 0.0

    if not sections:
        sections["DE_UNKNOWN"] = {
            "exam_id": "DE_UNKNOWN",
            "question_count": 0,
            "asset_count": 0,
            "math_fragment_count": 0,
            "warning_count": 0,
            "avg_confidence": 0.0,
            "question_ids": [],
        }

    confidences = [q.parse_confidence for q in questions]
    confidence_histogram = {"ge_0_9": 0, "0_75_to_0_9": 0, "0_6_to_0_75": 0, "lt_0_6": 0}
    for score in confidences:
        if score >= 0.90:
            confidence_histogram["ge_0_9"] += 1
        elif score >= 0.75:
            confidence_histogram["0_75_to_0_9"] += 1
        elif score >= 0.60:
            confidence_histogram["0_6_to_0_75"] += 1
        else:
            confidence_histogram["lt_0_6"] += 1

    summary = dict(parsed.get("summary", {}))
    summary["sections_count"] = len(sections)
    summary["question_count"] = len(questions)
    summary["asset_count"] = sum(len(q.assets) for q in questions)
    summary["math_fragment_count"] = sum(len(q.math_fragments) for q in questions)
    summary["avg_confidence"] = round(mean(confidences), 3) if confidences else 0.0
    summary["min_confidence"] = min(confidences) if confidences else 0.0
    summary["unknown_question_type_count"] = sum(1 for q in questions if q.question_type == "unknown")
    summary["warning_count"] = len(warnings)
    summary["parser_support_packages"] = dict(PARSER_SUPPORT_PACKAGES)
    parsed["summary"] = summary
    parsed["confidence_histogram"] = confidence_histogram
    parsed["sections"] = [sections[key] for key in sorted(sections.keys(), key=exam_sort_key)]


def apply_override_manifest(
    *,
    parsed: Dict[str, Any],
    qa_report: Dict[str, Any],
    override_manifest_path: Optional[Path],
) -> Dict[str, Any]:
    audit: Dict[str, Any] = {
        "schema_version": OVERRIDE_AUDIT_SCHEMA_VERSION,
        "artifact_type": "override_audit",
        "manifest_provided": override_manifest_path is not None,
        "manifest_path": str(override_manifest_path.resolve()) if override_manifest_path else "",
        "manifest_id": "",
        "summary": {
            "override_count": 0,
            "enabled_override_count": 0,
            "applied_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "actions": {},
        },
        "records": [],
    }
    if override_manifest_path is None:
        return audit

    payload = _load_override_manifest(override_manifest_path)
    if payload is None:
        return audit

    overrides = payload.get("overrides", [])
    audit["manifest_id"] = str(payload.get("manifest_id", ""))
    audit["summary"]["override_count"] = len(overrides)

    questions: List[ParsedQuestion] = list(parsed.get("questions", []))
    findings: List[Dict[str, Any]] = list(qa_report.get("publish_gate_findings", []))

    for idx, override in enumerate(overrides):
        record: Dict[str, Any] = {
            "index": idx,
            "override_id": str(override.get("id", f"override-{idx+1:03d}")),
            "action": str(override.get("action", "")),
            "enabled": bool(override.get("enabled", True)),
            "status": "skipped",
            "reason": "",
            "matched_count": 0,
            "mutated_count": 0,
        }
        action = record["action"]
        enabled = record["enabled"]
        if not enabled:
            record["reason"] = "disabled"
            audit["records"].append(record)
            continue
        audit["summary"]["enabled_override_count"] += 1
        if action not in OVERRIDE_ACTIONS:
            record["status"] = "failed"
            record["reason"] = f"unsupported action '{action}'"
            audit["summary"]["failed_count"] += 1
            audit["records"].append(record)
            continue

        selector = override.get("match", {})
        if not isinstance(selector, dict):
            record["status"] = "failed"
            record["reason"] = "match must be an object"
            audit["summary"]["failed_count"] += 1
            audit["records"].append(record)
            continue

        value = override.get("value", {})
        if not isinstance(value, dict):
            record["status"] = "failed"
            record["reason"] = "value must be an object"
            audit["summary"]["failed_count"] += 1
            audit["records"].append(record)
            continue

        mutated = 0
        matched = 0
        if action == "asset_visibility":
            visibility = str(value.get("visibility", "")).strip().lower()
            if visibility not in OVERRIDE_VISIBILITY:
                record["status"] = "failed"
                record["reason"] = f"invalid visibility '{visibility}'"
                audit["summary"]["failed_count"] += 1
                audit["records"].append(record)
                continue
            for question in questions:
                kept_assets: List[Dict[str, Any]] = []
                for asset in question.assets:
                    if _asset_matches_selector(selector, question, asset):
                        matched += 1
                        if visibility == "suppress":
                            mutated += 1
                            continue
                    kept_assets.append(asset)
                question.assets = kept_assets
        elif action == "asset_role_override":
            role = str(value.get("role", "")).strip()
            if role not in OVERRIDE_ASSET_ROLES:
                record["status"] = "failed"
                record["reason"] = f"invalid role '{role}'"
                audit["summary"]["failed_count"] += 1
                audit["records"].append(record)
                continue
            for question in questions:
                for asset in question.assets:
                    if _asset_matches_selector(selector, question, asset):
                        matched += 1
                        if str(asset.get("role", "")) != role:
                            asset["role"] = role
                            mutated += 1
        elif action == "placement_override":
            placement = str(value.get("placement", "")).strip()
            if placement not in OVERRIDE_PLACEMENTS:
                record["status"] = "failed"
                record["reason"] = f"invalid placement '{placement}'"
                audit["summary"]["failed_count"] += 1
                audit["records"].append(record)
                continue
            for question in questions:
                for asset in question.assets:
                    if _asset_matches_selector(selector, question, asset):
                        matched += 1
                        if str(asset.get("placement", "")) != placement:
                            asset["placement"] = placement
                            mutated += 1
        elif action == "text_patch":
            match_mode = str(value.get("match_mode", "literal")).strip()
            if match_mode not in OVERRIDE_TEXT_MATCH_MODE:
                record["status"] = "failed"
                record["reason"] = f"invalid text match_mode '{match_mode}'"
                audit["summary"]["failed_count"] += 1
                audit["records"].append(record)
                continue
            if not _is_non_empty_string(value.get("find")):
                record["status"] = "failed"
                record["reason"] = "text_patch requires non-empty value.find"
                audit["summary"]["failed_count"] += 1
                audit["records"].append(record)
                continue
            for question in questions:
                if not _question_matches_selector(selector, question):
                    continue
                matched += 1
                mutated += _apply_text_patch_to_question(question, value)
        elif action == "publish_exception":
            metric = str(value.get("metric", "")).strip()
            allow_if_lte = value.get("allow_if_lte")
            severity_override = value.get("severity_override")
            if not _is_non_empty_string(metric):
                record["status"] = "failed"
                record["reason"] = "publish_exception requires value.metric"
                audit["summary"]["failed_count"] += 1
                audit["records"].append(record)
                continue
            if not isinstance(allow_if_lte, (int, float)):
                record["status"] = "failed"
                record["reason"] = "publish_exception requires numeric value.allow_if_lte"
                audit["summary"]["failed_count"] += 1
                audit["records"].append(record)
                continue
            if severity_override is not None and str(severity_override) not in OVERRIDE_SEVERITIES:
                record["status"] = "failed"
                record["reason"] = f"invalid severity_override '{severity_override}'"
                audit["summary"]["failed_count"] += 1
                audit["records"].append(record)
                continue
            for finding in findings:
                if str(finding.get("metric", "")) != metric:
                    continue
                finding_value = finding.get("value")
                if not isinstance(finding_value, (int, float)):
                    continue
                matched += 1
                if float(finding_value) <= float(allow_if_lte):
                    finding["severity"] = str(severity_override) if severity_override is not None else "info"
                    mutated += 1
            summary, verdict, legacy = _recompute_publish_gate_from_findings(findings)
            qa_report["publish_gate_summary"] = summary
            qa_report["publish_verdict"] = verdict
            qa_report["publish_verdict_legacy"] = legacy
            qa_report["publish_gate_findings"] = findings
        elif action == "answer_override":
            mode = str(value.get("mode", "")).strip()
            if mode not in OVERRIDE_ANSWER_MODES:
                record["status"] = "failed"
                record["reason"] = f"invalid answer_override mode '{mode}'"
                audit["summary"]["failed_count"] += 1
                audit["records"].append(record)
                continue
            for question in questions:
                if not _question_matches_selector(selector, question):
                    continue
                matched += 1
                question.manual_answer_override = dict(value)
                mutated += 1

        record["matched_count"] = matched
        record["mutated_count"] = mutated
        if matched == 0:
            record["status"] = "skipped"
            record["reason"] = "no_match"
            audit["summary"]["skipped_count"] += 1
        elif mutated == 0:
            record["status"] = "skipped"
            record["reason"] = "matched_but_no_change"
            audit["summary"]["skipped_count"] += 1
        else:
            record["status"] = "applied"
            record["reason"] = "applied"
            audit["summary"]["applied_count"] += 1

        action_stats = audit["summary"]["actions"].setdefault(action, {"applied": 0, "skipped": 0, "failed": 0})
        if record["status"] == "applied":
            action_stats["applied"] += 1
        elif record["status"] == "failed":
            action_stats["failed"] += 1
        else:
            action_stats["skipped"] += 1
        audit["records"].append(record)

    _refresh_parsed_aggregates(parsed)
    return audit


def dominant_placement(assets: List[Dict[str, object]], math_fragments: List[Dict[str, object]]) -> str:
    placements: List[str] = []
    placements.extend(str(asset.get("placement", "unknown")) for asset in assets)
    placements.extend(str(fragment.get("placement", "unknown")) for fragment in math_fragments)
    filtered = [p for p in placements if p and p != "unknown"]
    if not filtered:
        return "unknown"
    counts: Dict[str, int] = {}
    for p in filtered:
        counts[p] = counts.get(p, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def build_bundle_id(
    *,
    source_docx: Optional[Path],
    source_docx_sha256: str,
    html_path: Path,
    qa_path: Path,
    subject: str,
    output_mode: str,
    override_manifest: Optional[Path],
) -> str:
    payload = {
        "source_docx": str(source_docx.resolve()) if source_docx else "",
        "source_docx_sha256": source_docx_sha256,
        "html": str(html_path.resolve()),
        "html_sha256": sha256_file(html_path.resolve()),
        "qa": str(qa_path.resolve()),
        "qa_sha256": sha256_file(qa_path.resolve()),
        "subject": subject,
        "output_mode": output_mode,
        "override_manifest_path": str(override_manifest.resolve()) if override_manifest else "",
        "override_manifest_sha256": sha256_file(override_manifest.resolve()) if override_manifest else "none",
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_exam_sections(qa_report: Dict[str, object], parsed: Dict[str, object]) -> List[Dict[str, object]]:
    qa_per_exam = qa_report.get("per_exam", {})
    parsed_sections = {
        section.get("exam_id", "DE_UNKNOWN"): section
        for section in parsed.get("sections", [])
        if isinstance(section, dict)
    }

    exam_ids = set(parsed_sections.keys())
    if isinstance(qa_per_exam, dict):
        exam_ids.update(str(k) for k in qa_per_exam.keys())

    sections: List[Dict[str, object]] = []
    family_info = parsed.get("document_family_detection", {})
    family_name = str((parsed.get("summary", {}) or {}).get("document_family", family_info.get("family", DOCUMENT_FAMILY_UNKNOWN)))
    family_confidence = float((parsed.get("summary", {}) or {}).get("document_family_confidence", family_info.get("confidence", 0.0)) or 0.0)
    family_priority_path = list((parsed.get("summary", {}) or {}).get("document_family_priority_path", family_info.get("priority_path", [])) or [])
    for exam_id in sorted(exam_ids, key=exam_sort_key):
        parser_section = parsed_sections.get(exam_id, {})
        qa_metrics = qa_per_exam.get(exam_id, {}) if isinstance(qa_per_exam, dict) else {}
        sections.append(
            {
                "exam_id": exam_id,
                "question_count": int(parser_section.get("question_count", 0) or 0),
                "metrics": qa_metrics if isinstance(qa_metrics, dict) else {},
                "parser": {
                    "asset_count": int(parser_section.get("asset_count", 0) or 0),
                    "math_fragment_count": int(parser_section.get("math_fragment_count", 0) or 0),
                    "warning_count": int(parser_section.get("warning_count", 0) or 0),
                    "avg_confidence": float(parser_section.get("avg_confidence", 0.0) or 0.0),
                    "question_ids": list(parser_section.get("question_ids", [])),
                },
                "document_family": family_name,
                "document_family_confidence": family_confidence,
                "document_family_priority_path": family_priority_path,
            }
        )
    return sections


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate stable JSON output contract artifacts.")
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--qa-json", type=Path, required=True)
    parser.add_argument("--source-docx", type=Path, default=None)
    parser.add_argument("--subject", choices=["generic", "physics", "chemistry", "math", "biology", "english", "literature"], default=None)
    parser.add_argument("--output-mode", choices=["internal", "publish"], default="publish")
    parser.add_argument("--override-manifest", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    html_path = args.html.resolve()
    qa_json_path = args.qa_json.resolve()
    source_docx = args.source_docx.resolve() if args.source_docx else None
    override_manifest_path = args.override_manifest.resolve() if args.override_manifest else None
    out_dir = args.out_dir.resolve()

    qa_report = json.loads(qa_json_path.read_text(encoding="utf-8"))
    html_text = html_path.read_text(encoding="utf-8", errors="ignore")
    subject = args.subject or str(qa_report.get("subject") or detect_subject(html_path.name))
    output_mode = args.output_mode or str(qa_report.get("output_mode") or "publish")
    source_sha256 = sha256_file(source_docx)

    parser_start = time.perf_counter()
    parsed = parse_html_structure(html_text)
    parser_build_seconds = time.perf_counter() - parser_start

    bundle_id = build_bundle_id(
        source_docx=source_docx,
        source_docx_sha256=source_sha256,
        html_path=html_path,
        qa_path=qa_json_path,
        subject=subject,
        output_mode=output_mode,
        override_manifest=override_manifest_path,
    )
    asset_dir = html_path.with_name(html_path.stem + "_files")

    override_audit = apply_override_manifest(
        parsed=parsed,
        qa_report=qa_report,
        override_manifest_path=override_manifest_path,
    )
    override_audit["bundle_id"] = bundle_id
    override_audit["subject"] = subject
    override_audit["output_mode"] = output_mode

    answer_summary = extract_answer_summary(parsed)
    document_family = _detect_document_family(parsed, answer_summary)
    parsed["document_family_detection"] = document_family
    parsed_summary = parsed.get("summary", {})
    if isinstance(parsed_summary, dict):
        parsed_summary["document_family"] = document_family.get("family", DOCUMENT_FAMILY_UNKNOWN)
        parsed_summary["document_family_confidence"] = float(document_family.get("confidence", 0.0) or 0.0)
        parsed_summary["document_family_priority_path"] = list(document_family.get("priority_path", []))
        parsed_summary["source_priority_path"] = list(document_family.get("priority_path", []))
        parsed_summary["document_family_scores"] = dict(document_family.get("scores", {}))
        parsed_summary["document_family_evidence"] = list(document_family.get("evidence", []))
        parsed["summary"] = parsed_summary
    answer_detection = answer_summary.get("detection", {}) if isinstance(answer_summary.get("detection", {}), dict) else {}
    answer_detection["document_family"] = document_family.get("family", DOCUMENT_FAMILY_UNKNOWN)
    answer_detection["document_family_confidence"] = float(document_family.get("confidence", 0.0) or 0.0)
    answer_detection["document_family_priority_path"] = list(document_family.get("priority_path", []))
    answer_detection["source_priority_path"] = list(document_family.get("priority_path", []))
    answer_detection["document_family_evidence"] = list(document_family.get("evidence", []))
    answer_detection["parser_support_packages"] = dict(PARSER_SUPPORT_PACKAGES)
    answer_summary["detection"] = answer_detection
    if document_family.get("issue_code"):
        parsed.setdefault("warnings", []).append(
            ParserWarning(
                severity="info" if document_family.get("issue_code") == "rubric_scoring_zone_detected" else "warning",
                code=str(document_family.get("issue_code", "document_family_ambiguous")),
                message=(
                    f"Detected document family {document_family.get('family', DOCUMENT_FAMILY_UNKNOWN)} "
                    f"(confidence={float(document_family.get('confidence', 0.0) or 0.0):.3f})"
                ),
                exam_id="DE_UNKNOWN",
                question_id="",
                line=1,
            )
        )

    answer_pipeline = run_answer_pipeline(parsed, answer_summary, document_family)
    answer_issues: List[Dict[str, Any]] = list(answer_pipeline.get("answer_issues", []))
    answer_qa_summary: Dict[str, Any] = dict(answer_pipeline.get("answer_qa_summary", {}))
    _merge_answer_findings(qa_report=qa_report, answer_issues=answer_issues)

    question_items_list: List[Dict[str, object]] = []
    for question in parsed["questions"]:
        roles = sorted({str(asset.get("role", "unknown-preview")) for asset in question.assets})
        question_items_list.append(
            {
                "item_id": question.item_id,
                "exam_id": question.exam_id,
                "question_number": question.question_number,
                "question_type": question.question_type,
                "placement": dominant_placement(question.assets, question.math_fragments),
                "asset_roles": roles,
                "prompt_preview": question.prompt_preview,
                "source_location": {"line": question.start_line},
                "parse_confidence": question.parse_confidence,
                "parser_warning_codes": question.warning_codes,
                "asset_count": len(question.assets),
                "math_fragment_count": len(question.math_fragments),
                "answer_key": question.answer_key or {"mode": "none"},
                "answer_sources": question.answer_sources,
                "reconciliation": question.reconciliation,
                "answer_detection": question.answer_detection,
                "rubric": question.rubric,
                "rubric_detection": question.rubric_detection,
                "qa_flags": question.qa_flags,
                "document_family": document_family.get("family", DOCUMENT_FAMILY_UNKNOWN),
                "document_family_confidence": float(document_family.get("confidence", 0.0) or 0.0),
                "source_priority_path": list(document_family.get("priority_path", [])),
            }
        )

    question_items = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "question_bank_items",
        "bundle_id": bundle_id,
        "subject": subject,
        "output_mode": output_mode,
        "item_count": len(question_items_list),
        "items": question_items_list,
    }

    exam_sections = build_exam_sections(qa_report, parsed)
    totals = qa_report.get("totals", {}) if isinstance(qa_report.get("totals", {}), dict) else {}
    unresolved_objects = qa_report.get("unresolved_objects", [])
    publish_gate_summary = qa_report.get("publish_gate_summary", {})
    publish_gate_findings = qa_report.get("publish_gate_findings", [])

    exam_bundle = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "exam_bundle",
        "bundle_id": bundle_id,
        "subject": subject,
        "output_mode": output_mode,
        "source": {
            "docx_path": str(source_docx.resolve()) if source_docx else "",
            "docx_sha256": source_sha256,
            "html_path": str(html_path),
            "asset_dir": str(asset_dir),
            "qa_source_path": str(qa_json_path),
        },
        "summary": {
            "total_mathml_formulas": int(qa_report.get("total_mathml_formulas", totals.get("mathml_formulas", 0)) or 0),
            "total_previews": int(qa_report.get("total_previews", totals.get("remaining_preview_images", 0)) or 0),
            "publish_verdict": str(qa_report.get("publish_verdict", "needs_review")),
            "unresolved_object_count": len(unresolved_objects) if isinstance(unresolved_objects, list) else 0,
            "parser_question_count": int(parsed["summary"].get("question_count", 0)),
            "parser_warning_count": int(parsed["summary"].get("warning_count", 0)),
            "parser_avg_confidence": float(parsed["summary"].get("avg_confidence", 0.0) or 0.0),
            "canonical_answer_missing_count": int(answer_qa_summary.get("canonical_answer_missing_count", 0) or 0),
            "answer_conflict_count": int(answer_qa_summary.get("conflict_count", 0) or 0),
            "document_family": document_family.get("family", DOCUMENT_FAMILY_UNKNOWN),
            "document_family_confidence": float(document_family.get("confidence", 0.0) or 0.0),
            "document_family_priority_path": list(document_family.get("priority_path", [])),
        },
        "exams": exam_sections,
        "answer_summary": answer_summary,
        "answer_qa_summary": answer_qa_summary,
        "question_item_count": len(question_items_list),
        "document_family": document_family.get("family", DOCUMENT_FAMILY_UNKNOWN),
        "document_family_detection": document_family,
    }

    parser_report = {
        "schema_version": PARSER_SCHEMA_VERSION,
        "artifact_type": "parser_report",
        "bundle_id": bundle_id,
        "subject": subject,
        "output_mode": output_mode,
        "summary": parsed["summary"],
        "answer_summary": answer_summary,
        "answer_qa_summary": answer_qa_summary,
        "confidence_histogram": parsed["confidence_histogram"],
        "sections": parsed["sections"],
        "document_family": document_family.get("family", DOCUMENT_FAMILY_UNKNOWN),
        "document_family_detection": document_family,
        "questions": [
            {
                "item_id": question.item_id,
                "exam_id": question.exam_id,
                "question_number": question.question_number,
                "question_type": question.question_type,
                "parse_confidence": question.parse_confidence,
                "warning_codes": question.warning_codes,
                "asset_count": len(question.assets),
                "math_fragment_count": len(question.math_fragments),
                "source_location": {"line": question.start_line},
                "answer_key": question.answer_key or {"mode": "none"},
                "answer_sources": question.answer_sources,
                "reconciliation": question.reconciliation,
                "answer_detection": question.answer_detection,
                "rubric_detection": question.rubric_detection,
                "qa_flags": question.qa_flags,
            }
            for question in parsed["questions"]
        ],
        "warnings": [
            {
                "severity": warning.severity,
                "code": warning.code,
                "message": warning.message,
                "exam_id": warning.exam_id,
                "question_id": warning.question_id,
                "line": warning.line,
            }
            for warning in parsed["warnings"]
        ],
        "timings": {
            "parser_json_build_seconds": round(parser_build_seconds, 6),
        },
    }

    qa_contract = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qa",
        "bundle_id": bundle_id,
        "subject": subject,
        "output_mode": output_mode,
        "publish_verdict": str(qa_report.get("publish_verdict", "needs_review")),
        "publish_gate_summary": publish_gate_summary if isinstance(publish_gate_summary, dict) else {},
        "publish_gate_findings": publish_gate_findings if isinstance(publish_gate_findings, list) else [],
        "totals": totals,
        "count_by_type": qa_report.get("count_by_type", {}),
        "per_exam": qa_report.get("per_exam", {}),
        "unresolved_objects": unresolved_objects if isinstance(unresolved_objects, list) else [],
        "parser_summary": parsed["summary"],
        "answer_summary": answer_summary,
        "answer_qa_summary": answer_qa_summary,
        "answer_qa_issues": answer_issues,
        "document_family": document_family.get("family", DOCUMENT_FAMILY_UNKNOWN),
        "document_family_detection": document_family,
        "override_audit": {
            "manifest_id": str(override_audit.get("manifest_id", "")),
            "applied_count": int(override_audit.get("summary", {}).get("applied_count", 0) or 0),
            "skipped_count": int(override_audit.get("summary", {}).get("skipped_count", 0) or 0),
            "failed_count": int(override_audit.get("summary", {}).get("failed_count", 0) or 0),
        },
        "qa_report_source_path": str(qa_json_path),
    }

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "manifest",
        "bundle_id": bundle_id,
        "subject": subject,
        "output_mode": output_mode,
        "source": {
            "docx_path": str(source_docx.resolve()) if source_docx else "",
            "docx_sha256": source_sha256,
            "html_path": str(html_path),
            "asset_dir": str(asset_dir),
            "qa_source_path": str(qa_json_path),
        },
        "publish": {
            "publish_verdict": str(qa_report.get("publish_verdict", "needs_review")),
            "publish_gate_summary": publish_gate_summary if isinstance(publish_gate_summary, dict) else {},
        },
        "artifacts": {
            "manifest": "manifest.json",
            "exam_bundle": "exam_bundle.json",
            "question_bank_items": "question_bank_items.json",
            "qa": "qa.json",
            "parser_report": "parser_report.json",
            "override_audit": "override_audit.json",
        },
        "enums": {
            "question_types": ["unknown", "single_choice", "multiple_choice", "true_false", "short_answer", "essay"],
            "answer_modes": ["single_choice", "boolean_group", "short_answer", "rubric", "none"],
            "document_families": [
                DOCUMENT_FAMILY_OBJECTIVE_END_KEY,
                DOCUMENT_FAMILY_OBJECTIVE_INLINE,
                DOCUMENT_FAMILY_RUBRIC,
                DOCUMENT_FAMILY_UNKNOWN,
            ],
            "reconciliation_statuses": [
                "resolved",
                "resolved_with_fill",
                "resolved_normalized_equivalent",
                "conflict",
                "needs_review",
                "blocked",
            ],
            "asset_roles": ["equation", "diagram", "chart", "chemical-diagram", "generic-image", "unknown-preview"],
            "placements": ["inline", "display", "context-right", "context-below", "centered", "table-cell", "unknown"],
            "qa_severities": ["info", "warning", "error", "blocker"],
            "publish_verdicts": ["safe_to_publish", "needs_review", "blocked"],
            "output_modes": ["internal", "publish"],
        },
    }

    write_json(out_dir / "manifest.json", manifest)
    write_json(out_dir / "exam_bundle.json", exam_bundle)
    write_json(out_dir / "question_bank_items.json", question_items)
    write_json(out_dir / "qa.json", qa_contract)
    write_json(out_dir / "parser_report.json", parser_report)
    write_json(out_dir / "override_audit.json", override_audit)
    print(out_dir)


if __name__ == "__main__":
    main()
