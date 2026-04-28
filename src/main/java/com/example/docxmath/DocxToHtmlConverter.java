package com.example.docxmath;

import org.apache.poi.openxml4j.exceptions.OpenXML4JException;
import org.apache.poi.openxml4j.opc.PackagePart;
import org.apache.poi.openxml4j.opc.PackageRelationship;
import org.apache.poi.hemf.usermodel.HemfPicture;
import org.apache.poi.hwmf.usermodel.HwmfPicture;
import org.apache.poi.xwpf.usermodel.IBody;
import org.apache.poi.xwpf.usermodel.IBodyElement;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFTable;
import org.apache.poi.xwpf.usermodel.XWPFTableCell;
import org.apache.poi.xwpf.usermodel.XWPFTableRow;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NamedNodeMap;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.geom.Rectangle2D;
import java.awt.image.BufferedImage;
import java.util.HashSet;
import java.util.HashMap;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.StringReader;
import java.io.StringWriter;
import javax.imageio.ImageIO;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Practical converter focused on text, tables and equations.
 * <p>
 * The design choice is intentional:
 * Apache POI is used to open and inspect the .docx package,
 * while OMML is converted to MathML and then rendered consistently in the browser by MathJax.
 * This variant can also consume external MathML sidecars produced by transpect mathtype-extension
 * for MathType WMF/BIN assets discovered in the .docx package.
 */
public final class DocxToHtmlConverter {
    private static final String MATHML_NAMESPACE_URI = "http://www.w3.org/1998/Math/MathML";
    private static final String TRANSPECT_NAMESPACE_URI = "http://transpect.io";
    private static final Set<String> INLINE_CONTAINER_NAMES = Set.of(
            "hyperlink", "smartTag", "customXml", "ins", "del", "sdt", "sdtContent", "proofErr"
    );
    private static final Pattern BLOCK_MATH_PATTERN = Pattern.compile("(?s)<div class=\"math-block[^\\\"]*\">.*?</div>");
    private static final Pattern INLINE_IMAGE_TO_TEXT_PATTERN = Pattern.compile("(<img\\b[^>]*?/?>)(?=[\\p{L}\\p{N}])");
    private static final Pattern TEXT_TO_INLINE_IMAGE_PATTERN = Pattern.compile("([\\p{L}\\p{N}])(<img\\b[^>]*?/?>)");
    private static final Pattern INLINE_MATH_TO_TEXT_PATTERN = Pattern.compile(
            "(<span\\b(?=[^>]*class=\"[^\"]*math-inline[^\"]*\")[^>]*>.*?</span>)(?=[\\p{L}\\p{N}])",
            Pattern.DOTALL
    );
    private static final Pattern INLINE_MATH_SPACE_BEFORE_PUNCT_PATTERN = Pattern.compile(
            "(</span>)\\s+([,.;:!?])"
    );
    private static final Pattern TEXT_TO_INLINE_MATH_PATTERN = Pattern.compile(
            "([\\p{L}\\p{N}])(<span\\b(?=[^>]*class=\"[^\"]*math-inline[^\"]*\")[^>]*>)"
    );
    private static final Pattern PUNCT_TO_INLINE_MATH_PATTERN = Pattern.compile(
            "([,.;:!?])(<span\\b(?=[^>]*class=\"[^\"]*math-inline[^\"]*\")[^>]*>)"
    );
    private static final Pattern INLINE_MATH_TO_INLINE_MATH_PATTERN = Pattern.compile(
            "(</span>)(<span\\b(?=[^>]*class=\"[^\"]*math-inline[^\"]*\")[^>]*>)",
            Pattern.DOTALL
    );
    private static final Pattern INLINE_MATH_DEGREE_C_SUFFIX_PATTERN = Pattern.compile(
            "(?is)(<span\\b(?=[^>]*class=\"[^\"]*math-inline[^\"]*\")[^>]*><math\\b[^>]*>)(?<before>.*?)<msup\\b[^>]*>\\s*<mn\\b[^>]*>\\s*(?<value>[^<\\s]+)\\s*</mn>\\s*<(?:mo|mtext)\\b[^>]*>\\s*[∘°]\\s*</(?:mo|mtext)>\\s*</msup>(?<after>.*?)</math></span>\\s*C\\b"
    );
    private static final Pattern EMPTY_BASE_MINUS_MSUP_MATH_INLINE_PATTERN = Pattern.compile(
            "(?is)<span\\b(?=[^>]*class=\"[^\"]*math-inline[^\"]*mathml[^\"]*\")[^>]*>\\s*<math\\b[^>]*>\\s*<msup\\b[^>]*>\\s*"
                    + "(?:<mrow\\b[^>]*/>|<mrow\\b[^>]*>\\s*</mrow>)\\s*"
                    + "(?:<mrow\\b[^>]*>\\s*<mo\\b[^>]*>\\s*[−-]\\s*</mo>\\s*</mrow>|<mo\\b[^>]*>\\s*[−-]\\s*</mo>)\\s*"
                    + "</msup>\\s*</math>\\s*</span>"
    );
    private static final Pattern DIACRITIC_MARK_PATTERN = Pattern.compile("\\p{M}+");
    private static final Pattern SINGLE_INLINE_MATH_PATTERN = Pattern.compile("^<span class=\"math-inline([^\\\"]*)\">(.*)</span>$", Pattern.DOTALL);
    private static final Pattern SINGLE_BLOCK_MATH_PATTERN = Pattern.compile("^<div class=\"math-block([^\\\"]*)\">(.*)</div>$", Pattern.DOTALL);
    private static final Pattern LEADING_IMAGES_PATTERN = Pattern.compile("^(?:\\s*)(?<images>(?:<img\\b[^>]*?/?>\\s*)+)(?<rest>.+)$", Pattern.DOTALL);
    private static final Pattern INLINE_IMAGE_TAG_PATTERN = Pattern.compile(
            "(?is)<img\\b(?=[^>]*class=\"[^\"]*inline-image[^\"]*\")[^>]*?/?>"
    );
    private static final Pattern TABLE_FIGURE_IMAGE_TAG_PATTERN = Pattern.compile(
            "(?is)<img\\b(?=[^>]*class=\"[^\"]*(?:inline-image|physics-diagram|physics-chart|diagram-asset|chemical-diagram|chem-diagram)[^\"]*\")[^>]*?/?>"
    );
    private static final Pattern IMAGE_ONLY_PARAGRAPH_BEFORE_QUESTION_PATTERN = Pattern.compile(
            "(?is)<p>\\s*(?<img><img\\b(?=[^>]*class=\"[^\"]*inline-image[^\"]*\")[^>]*?/?>)\\s*</p>\\s*<p>(?<text>.*?)</p>"
    );
    private static final Pattern QUESTION_STEM_PATTERN = Pattern.compile("(?iu)\\bcâu\\s*\\d+\\b");
    private static final Pattern ESSAY_ASK_SIGNAL_PATTERN = Pattern.compile(
            "(?iu)\\b(?:hỏi|tính|bao\\s+nhiêu|làm\\s+tròn|xác\\s+suất|chi\\s+phí|quãng\\s+đường|thể\\s+tích|chiều\\s+cao|khoảng\\s+cách|độ\\s+dốc|độ\\s+dài)\\b"
    );
    private static final Pattern ESSAY_ESSENTIAL_FIGURE_SIGNAL_PATTERN = Pattern.compile(
            "(?iu)\\b(?:đồ\\s*thị|biểu\\s*đồ|sơ\\s*đồ|bảng\\s*biến\\s*thiên|tham\\s*khảo\\s*hình|xem\\s*hình|hình\\s*bên|hình\\s*dưới|hình\\s*vẽ|như\\s+trong\\s+hình|hình\\s+minh\\s*họa|hình\\s+minh\\s*hoạ)\\b"
    );
    private static final Pattern ESSAY_CONTEXT_FIGURE_SIGNAL_PATTERN = Pattern.compile(
            "(?iu)\\b(?:trực\\s*thăng|tòa\\s*nhà|toà\\s*nhà|nhà\\s*hàng|sân\\s*bay|khách\\s*hàng|khung\\s*cảnh|cứu\\s*hộ|ảnh\\s*minh\\s*họa|hyperloop)\\b"
    );
    private static final Pattern NONESSENTIAL_STANDALONE_CONTEXT_SIGNAL_PATTERN = Pattern.compile(
            "(?iu)\\b(?:cabin|cáp\\s*treo|cap\\s*treo|trực\\s*thăng|truc\\s*thang|tòa\\s*nhà|toà\\s*nhà|toa\\s*nha|hyperloop|ảnh\\s*minh\\s*họa|anh\\s*minh\\s*hoa)\\b"
    );
    private static final Pattern NONESSENTIAL_STANDALONE_KEEP_CONTEXT_SIGNAL_PATTERN = Pattern.compile(
            "(?iu)\\b(?:một\\s+cabin\\s+cáp\\s*treo|cabin\\s+cáp\\s*treo|cabin\\s+cap\\s*treo)\\b"
    );
    private static final Pattern MULTI_CHOICE_OPTION_MARKER_PATTERN = Pattern.compile("(?iu)\\b[ABCD]\\.");
    private static final Pattern IMG_CLASS_ATTR_PATTERN = Pattern.compile("(?i)\\bclass\\s*=\\s*\"([^\"]*)\"");
    private static final Pattern QUESTION_OR_SECTION_PATTERN = Pattern.compile("(?is)^(câu\\s*\\d+|phần\\b|hướng\\s*dẫn\\b|đáp\\s*án\\b).*");
    private static final Pattern HTML_TAG_PATTERN = Pattern.compile("<[^>]+>");
    private static final Pattern CONSECUTIVE_ESSENTIAL_FIGURES_AFTER_STEM_PATTERN = Pattern.compile(
            "(?is)(?<stem><p>\\s*(?:(?!</p>).)*?\\bcâu\\s*\\d+\\b(?:(?!</p>).)*?</p>\\s*)(?<figs>(?:<figure\\b(?=[^>]*data-figure-role=\"essential-figure\")[^>]*>.*?</figure>\\s*){2,})"
    );
    private static final Pattern REDUNDANT_EQUATION_FALLBACK_PATTERN = Pattern.compile(
            "(?s)<img\\b(?=[^>]*class=\"[^\"]*equation-(?:fallback|preview)[^\"]*\")[^>]*?/?>\\s*(?=(?:<span\\b(?=[^>]*class=\"[^\"]*math-inline[^\"]*\")[^>]*>|<div\\b(?=[^>]*class=\"[^\"]*math-block[^\"]*\")[^>]*>))"
    );
    private static final Pattern REDUNDANT_UNSUPPORTED_EQUATION_SPAN_PATTERN = Pattern.compile(
            "(?s)<span\\b(?=[^>]*class=\"[^\"]*unsupported-equation[^\"]*\")(?=[^>]*data-ole-kind=\"equation\")[^>]*>\\[[^\\]]+]</span>\\s*(?=(?:<span\\b(?=[^>]*class=\"[^\"]*math-inline[^\"]*\")[^>]*>|<div\\b(?=[^>]*class=\"[^\"]*math-block[^\"]*\")[^>]*>))"
    );
    private static final Pattern CORR_MATHML_SPLIT_DAET_PATTERN = Pattern.compile(
            "(?s)<mtext>Ñ</mtext><mi[^>]*>a</mi><mtext>ë</mtext><mi[^>]*>t</mi>"
    );
    private static final Pattern WORD_FIELD_INCLUDEPICTURE_COMMAND_PATTERN = Pattern.compile(
            "(?is)INCLUDEPICTURE\\b\\s+(?:&quot;[^<]*?&quot;|\"[^\"<]*?\")\\s*\\\\\\*\\s*MERGEFORMAT(?:INET)?\\b"
    );
    private static final Pattern WORD_FIELD_HTTP_QUOTED_URL_BEFORE_IMAGE_PATTERN = Pattern.compile(
            "(?is)(?:&quot;https?://[^<\\s]+&quot;\\s*)+(?=<img\\b)"
    );
    private static final Pattern WORD_FIELD_LEAKAGE_TOKEN_PATTERN = Pattern.compile(
            "(?iu)\\b(?:INCLUDEPICTURE|MERGEFORMATINET|MERGEFORMAT)\\b"
    );
    private static final Pattern WORD_FIELD_SWITCH_TOKEN_PATTERN = Pattern.compile(
            "(?iu)\\\\\\*"
    );
    private static final Pattern PUBLISH_DEBUG_ATTR_PATTERN = Pattern.compile(
            "\\sdata-(?:render-attempted|render-source-used|render-source-exts|render-source-assets|render-role)=\"[^\"]*\""
    );
    private static final String EMPTY_PARAGRAPH_HTML_REGEX = "<p>\\s*(?:(?:<br\\s*/?>)|&nbsp;|&#160;|\\u00A0|\\s)*</p>";
    private static final Pattern EMPTY_PARAGRAPH_TAG_PATTERN = Pattern.compile("(?is)" + EMPTY_PARAGRAPH_HTML_REGEX);
    private static final Pattern EMPTY_PARAGRAPH_CHAIN_BEFORE_DOCX_TABLE_PATTERN = Pattern.compile(
            "(?is)(?<empties>(?:" + EMPTY_PARAGRAPH_HTML_REGEX + "\\s*)+)(?=<table\\b(?=[^>]*class=\"[^\"]*docx-table[^\"]*\")[^>]*>)"
    );
    private static final Pattern EMPTY_PARAGRAPH_CHAIN_AFTER_DOCX_TABLE_PATTERN = Pattern.compile(
            "(?is)(</table>\\s*)(?<empties>(?:" + EMPTY_PARAGRAPH_HTML_REGEX + "\\s*)+)"
    );
    private static final Pattern EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_START_PATTERN = Pattern.compile(
            "(?is)(<td\\b[^>]*>\\s*)(?<empties>(?:" + EMPTY_PARAGRAPH_HTML_REGEX + "\\s*)+)"
    );
    private static final Pattern EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_END_PATTERN = Pattern.compile(
            "(?is)(?<empties>(?:" + EMPTY_PARAGRAPH_HTML_REGEX + "\\s*)+)(\\s*</td>)"
    );
    private static final Pattern STANDALONE_INLINE_IMAGE_PARAGRAPH_PATTERN = Pattern.compile(
            "(?is)<p>\\s*(?<img><img\\b(?=[^>]*class=\"[^\"]*inline-image[^\"]*\")[^>]*?/?>)\\s*</p>"
    );
    private static final Pattern STANDALONE_QUESTION_IMAGE_PARAGRAPH_PATTERN = Pattern.compile(
            "(?is)<p>\\s*(?<img><img\\b(?=[^>]*class=\"[^\"]*(?:diagram-asset|embedded-object|physics-diagram|physics-chart)[^\"]*\")[^>]*?/?>)\\s*</p>"
    );
    private static final Pattern MATH_BLOCK_CAPTURE_PATTERN = Pattern.compile(
            "(?is)<div class=\"math-block(?<classes>[^\"]*)\">(?<content>.*?)</div>"
    );
    private static final Pattern MATH_TAG_PATTERN = Pattern.compile("(?is)<math\\b[^>]*>.*?</math>");
    private static final Pattern MATHML_CM2_SPLIT_PATTERN = Pattern.compile(
            "(?is)(<mtext\\b[^>]*>)([\\s\\u00A0]*)c\\s*</mtext>\\s*<msup\\b[^>]*>\\s*<mtext\\b[^>]*>\\s*m\\s*</mtext>\\s*<mn\\b[^>]*>\\s*2\\s*</mn>\\s*</msup>"
    );
    private static final Pattern MATHML_CM3_SPLIT_PATTERN = Pattern.compile(
            "(?is)(<mtext\\b[^>]*>)([\\s\\u00A0]*)c\\s*</mtext>\\s*<msup\\b[^>]*>\\s*<mtext\\b[^>]*>\\s*m\\s*</mtext>\\s*<mn\\b[^>]*>\\s*3\\s*</mn>\\s*</msup>"
    );
    private static final Pattern MATHML_MOL_INV_SPLIT_PATTERN = Pattern.compile(
            "(?is)(<mtext\\b[^>]*>)([\\s\\u00A0]*)mo\\s*</mtext>\\s*<msup\\b[^>]*>\\s*<mtext\\b[^>]*>\\s*l\\s*</mtext>\\s*<mrow\\b[^>]*>\\s*<mo\\b[^>]*>\\s*[−-]\\s*</mo>\\s*<mn\\b[^>]*>\\s*1\\s*</mn>\\s*</mrow>\\s*</msup>"
    );
    private static final Pattern MATHML_BLANK_BASE_DEGREE_C_PATTERN = Pattern.compile(
            "(?is)<msup\\b[^>]*>\\s*<mn\\b[^>]*>\\s*(?:&nbsp;|\\u00A0)?\\s*</mn>\\s*<mtext\\b[^>]*>\\s*[∘°]\\s*</mtext>\\s*</msup>\\s*(<mtext\\b[^>]*>)\\s*C\\s*</mtext>"
    );
    private static final Pattern MATHML_J_PER_MOL_DOT_K_PATTERN = Pattern.compile(
            "(?is)(<mtext\\b[^>]*>)([\\s\\u00A0]*)J\\s*/\\s*mol\\s*</mtext>\\s*<mo\\b[^>]*>\\s*[⋅·]\\s*</mo>\\s*<mtext\\b[^>]*>[\\s\\u00A0]*K\\s*</mtext>"
    );
    private static final Pattern MATHML_R_CONSTANT_UNIT_PATTERN = Pattern.compile(
            "(?is)(<mtext\\b[^>]*>)\\s*J\\s*</mtext>\\s*<mo\\b[^>]*>\\s*[⋅·]\\s*</mo>\\s*<mtext\\b[^>]*>\\s*mol⁻¹\\s*</mtext>\\s*<mo\\b[^>]*>\\s*[⋅·]\\s*</mo>\\s*<msup\\b[^>]*>\\s*<mtext\\b[^>]*>\\s*K\\s*</mtext>\\s*<mrow\\b[^>]*>\\s*<mo\\b[^>]*>\\s*[−-]\\s*</mo>\\s*<mn\\b[^>]*>\\s*1\\s*</mn>\\s*</mrow>\\s*</msup>"
    );
    private static final Pattern MATHML_M_PER_S2_PATTERN = Pattern.compile(
            "(?is)(<mtext\\b[^>]*>)([\\s\\u00A0]*)m\\s*/\\s*</mtext>\\s*<msup\\b[^>]*>\\s*<mtext\\b[^>]*>\\s*s\\s*</mtext>\\s*<(?:mtext|mn)\\b[^>]*>\\s*2\\s*</(?:mtext|mn)>\\s*</msup>"
    );
    private static final Pattern MATHML_EMPTY_BASE_ISOTOPE_PATTERN = Pattern.compile(
            "(?is)<msup\\b[^>]*>\\s*(?:<mrow\\b[^>]*/>|<mrow\\b[^>]*>\\s*</mrow>)\\s*<(?:mn|mi|mtext)\\b[^>]*>\\s*([^<\\s]+)\\s*</(?:mn|mi|mtext)>\\s*</msup>\\s*<(?:mn|mi|mtext)\\b[^>]*>\\s*([^<\\s]+)\\s*</(?:mn|mi|mtext)>\\s*<(?<symbolTag>mi|mtext)\\b(?<symbolAttrs>[^>]*)>\\s*(?<symbol>[A-Z][a-z]?)\\s*</(?:mi|mtext)>"
    );
    private static final Pattern MATHML_EMPTY_BASE_MSUBSUP_ISOTOPE_PATTERN = Pattern.compile(
            "(?is)<msubsup\\b(?<attrs>[^>]*)>\\s*<mn\\b[^>]*>\\s*(?:&nbsp;|\\u00A0|\\s)*</mn>\\s*<(?:mn|mi|mtext)\\b[^>]*>\\s*(?<atomic>[^<\\s]+)\\s*</(?:mn|mi|mtext)>\\s*<(?:mn|mi|mtext)\\b[^>]*>\\s*(?<mass>[^<\\s]+)\\s*</(?:mn|mi|mtext)>\\s*</msubsup>\\s*<(?<symbolTag>mi|mtext)\\b(?<symbolAttrs>[^>]*)>\\s*(?<symbol>[A-Z][a-z]?)\\s*</(?:mi|mtext)>"
    );
    private static final Pattern MATHML_DEGREE_C_SUP_PATTERN = Pattern.compile(
            "(?is)<msup\\b[^>]*>\\s*<mn\\b[^>]*>\\s*([^<\\s]+)\\s*</mn>\\s*<(?:mo|mtext)\\b[^>]*>\\s*[∘°]\\s*</(?:mo|mtext)>\\s*</msup>\\s*<mtext\\b[^>]*>\\s*C\\s*</mtext>"
    );
    private static final Pattern MATHML_NUMBER_WITH_TRAILING_COMMA_BEFORE_UNIT_PATTERN = Pattern.compile(
            "(?is)<mn\\b(?<numAttrs>[^>]*)>\\s*(?<value>\\d+(?:,\\d+)?)\\s*,\\s*</mn>\\s*(?<unit><(?:mi\\b[^>]*mathvariant=\"normal\"[^>]*>\\s*Ω\\s*</mi>|mtext\\b[^>]*>\\s*(?:Ω|psi|MW|T|N|W|V)\\s*</mtext>))"
    );
    private static final Pattern MATHML_SPLIT_MICRO_UNIT_PATTERN = Pattern.compile(
            "(?is)<mn\\b(?<numAttrs>[^>]*)>\\s*(?<value>\\d+(?:,\\d+)?)\\s*</mn>\\s*<mi\\b[^>]*>\\s*[μµ]\\s*</mi>\\s*<mi\\b[^>]*>\\s*(?<suffix>[mF])\\s*</mi>"
    );
    private static final Pattern MATHML_SPLIT_TRIG_FUNCTION_PATTERN = Pattern.compile(
            "(?is)<mi\\b(?<prefixAttrs>[^>]*)>\\s*(?<head>[cst])\\s*</mi>\\s*<mtext\\b[^>]*>\\s*(?<tail>(?:os|in|an))\\s*</mtext>(?<open>\\s*<mo\\b[^>]*>\\s*\\(\\s*</mo>)?"
    );
    private static final Pattern MATHML_DEGREE_SYMBOL_PLUS_C_PATTERN = Pattern.compile(
            "(?is)<mo\\b[^>]*>\\s*[∘°]\\s*</mo>\\s*<mtext\\b[^>]*>\\s*C\\s*</mtext>"
    );
    private static final Pattern MATHML_MALGUN_CONDITIONAL_BAR_PATTERN = Pattern.compile(
            "(?is)<mo\\b[^>]*fontfamily=\"Malgun Gothic\"[^>]*>\\s*[∣|]\\s*</mo>"
    );
    private static final Pattern MATHML_INTEGER_SET_Z_PATTERN = Pattern.compile(
            "(?is)<mo\\b[^>]*>\\s*∈\\s*</mo>\\s*<mi\\b[^>]*>\\s*Z\\s*</mi>"
    );
    private static final Pattern MATHML_VECTOR_COMBINING_ARROW_PATTERN = Pattern.compile(
            "(?is)<mo\\b[^>]*>\\s*⃗\\s*</mo>"
    );
    private static final Pattern MATHML_MML_VECTOR_COMBINING_ARROW_PATTERN = Pattern.compile(
            "(?is)<mml:mo\\b[^>]*>\\s*⃗\\s*</mml:mo>"
    );
    private static final Pattern MATHML_TRANSPECT_NAMESPACE_PATTERN = Pattern.compile(
            "\\s+xmlns:tr=\"http://transpect\\.io\""
    );
    private static final Pattern MATHML_PREFIXED_ROOT_NAMESPACE_PATTERN = Pattern.compile(
            "(?is)<mml:math\\b([^>]*)xmlns:mml=\"http://www\\.w3\\.org/1998/Math/MathML\"([^>]*)>"
    );
    private static final Pattern MATHML_PREFIXED_TAG_PATTERN = Pattern.compile("(?is)(</?)mml:");
    private static final Pattern MATHML_DATA_SOURCE_ATTR_PATTERN = Pattern.compile(
            "\\s+data-math-source=\"[^\"]*\""
    );
    private static final Pattern MATHML_DISPLAY_ATTR_PATTERN = Pattern.compile(
            "\\s+display\\s*=\\s*(?:\"[^\"]*\"|'[^']*')"
    );
    private static final Map<Integer, String> CORE_SYMBOL_FONT_LOW_BYTE_MAP = Map.ofEntries(
            Map.entry(0xDE, "⇒"),
            Map.entry(0xB7, "•"),
            Map.entry(0x6C, "λ"),
            Map.entry(0x6D, "μ")
    );
    private static final Map<Integer, String> CORE_WINGDINGS_FONT_LOW_BYTE_MAP = Map.of(
            0x77, "•"
    );
    private static final Map<Integer, String> MATH_WINGDINGS2_FONT_LOW_BYTE_MAP = Map.ofEntries(
            Map.entry(0x6A, "1"),
            Map.entry(0x76, "2"),
            Map.entry(0x6C, "3"),
            Map.entry(0x78, "4"),
            Map.entry(0x6E, "5"),
            Map.entry(0x7A, "6"),
            Map.entry(0x70, "7"),
            Map.entry(0x7C, "8"),
            Map.entry(0x72, "9")
    );
    private static final Pattern CHEMICAL_TOKEN_PATTERN = Pattern.compile(
            "(?<![\\p{L}_])(?:[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?[A-Z][A-Za-z0-9()\\[\\]₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻+\\-−·•/]*"
    );
    private static final Pattern CHEMICAL_UNIT_TOKEN_PATTERN = Pattern.compile("mol\\s*[·•.]\\s*L\\s*(?:\\^\\s*-?\\s*1|[⁻−-]\\s*1|⁻¹)");
    private static final Pattern CHEMICAL_TEMP_C_TOKEN_PATTERN = Pattern.compile("(?iu)(\\d+)\\s*(?:\\^\\s*(?:0|º|o)|⁰|°)\\s*C\\b");
    private static final Pattern CHEMICAL_POWER_OF_TEN_PATTERN = Pattern.compile("\\b10\\s*\\^\\s*([0-9]{1,3})\\b");
    private static final Pattern CHEMICAL_ENTHALPY_TOKEN_PATTERN = Pattern.compile("Δ([fr])H°\\s*([0-9]{2,4})");
    private static final Pattern CHEMICAL_ELECTRON_CHARGE_PATTERN = Pattern.compile("(?iu)(?<!\\p{L})(\\d*)\\s*e\\s*([+−-])(?!\\p{L})");
    private static final Pattern CHEMICAL_ELECTRON_LOOSE_PLUS_PATTERN = Pattern.compile("(?iu)(?<!\\p{L})(\\d*)\\s*e\\s*\\+\\s*(?=[A-Z(\\[])");
    private static final Pattern CHEMICAL_BI_ARROW_PATTERN = Pattern.compile("(?<=\\S)\\s*(?:<=>|<->|&lt;=&gt;|&lt;-&gt;|⇌|⇄|↔)\\s*(?=\\S)");
    private static final Pattern CHEMICAL_FORWARD_ARROW_PATTERN = Pattern.compile("(?<=\\S)\\s*(?:->|=>|-&gt;|=&gt;|â†’|âž”|⟶)\\s*(?=\\S)");
    private static final Pattern SVG_BOUNDING_BOX_RECT_PATTERN = Pattern.compile(
            "<rect\\b(?=[^>]*class=\"[^\"]*BoundingBox[^\"]*\")[^>]*>",
            Pattern.CASE_INSENSITIVE
    );
    private static final Pattern SVG_ROOT_TAG_PATTERN = Pattern.compile("<svg\\b[^>]*>", Pattern.CASE_INSENSITIVE);
    private static final Pattern SVG_ATTR_PATTERN = Pattern.compile("([a-zA-Z_:][-a-zA-Z0-9_:.]*)\\s*=\\s*\"([^\"]*)\"");
    private static final Set<String> INLINE_TRIMMABLE_RASTER_EXTENSIONS = Set.of(".png", ".jpg", ".jpeg", ".gif");
    private static final Pattern CHEM_INLINE_WRAPPER_PATTERN = Pattern.compile("^<span class=\"chem-inline\" data-chem-fixed=\"1\">(.*)</span>$", Pattern.DOTALL);
    private static final Pattern HTML_SUB_TAG_UNICODE_PATTERN = Pattern.compile("(?s)<sub>([₀₁₂₃₄₅₆₇₈₉]+)</sub>");
    private static final Pattern HTML_SUP_TAG_UNICODE_PATTERN = Pattern.compile("(?s)<sup>([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)</sup>");
    private static final Pattern ADJACENT_HTML_SUP_TAG_PATTERN = Pattern.compile("(?s)<sup>\\s*([^<]*?)\\s*</sup>\\s*<sup>\\s*([^<]*?)\\s*</sup>");
    private static final Pattern EMPTY_SUBSCRIPT_SPACER_PATTERN = Pattern.compile("(?is)<sub>\\s*(?:&emsp;|&nbsp;|&#160;|\\u00A0|\\s)+\\s*</sub>");
    private static final Pattern HTML_TEMP_SUP_C_PATTERN = Pattern.compile("(?iu)(\\d+)\\s*<sup>\\s*(?:0|º|o|⁰)\\s*</sup>\\s*C\\b");
    private static final Pattern HTML_PHYSICS_TEMP_SUP_C_PATTERN = Pattern.compile("(?iu)(\\d+)\\s*<sup>\\s*(?:0|º|o|⁰)\\s*</sup>\\s*C\\b");
    private static final Pattern CHEM_PUNCTUATION_IN_SCRIPT_PATTERN = Pattern.compile(
            "(?is)<(?:sub|sup)>\\s*([,.;:!?])\\s*</(?:sub|sup)>"
    );
    private static final Pattern FALSE_STRUCTURAL_CO_NH_CHARGE_PATTERN = Pattern.compile("(?i)(CO-NH)<sup>\\s*[-−]\\s*</sup>");
    private static final Pattern FALSE_STRUCTURAL_CO_CHARGE_PATTERN = Pattern.compile("(?i)(CO)<sup>\\s*[-−]\\s*</sup>(?=(?:</span>)*(?:\\s|\\)|\\.|,|;|:|$))");
    private static final Pattern CHEMICAL_DOWNS_ANODE_MALFORMED_PATTERN = Pattern.compile(
            "(?is)2Cl<sup>\\s*[-−]\\s*</sup>\\s*→\\s*(?:<span\\b[^>]*class=\"[^\"]*chem-inline[^\"]*\"[^>]*>)?\\s*2e<sup>\\s*\\+\\s*</sup>\\s*(?:</span>)?\\s*Cl<sub>\\s*2\\s*</sub>"
    );
    private static final Pattern UNICODE_SUP_BEFORE_HTML_SUP_PATTERN = Pattern.compile("([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)<sup>([^<]*)</sup>");
    private static final Pattern HTML_SUP_BEFORE_UNICODE_SUP_PATTERN = Pattern.compile("(?s)<sup>([^<]*)</sup>([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)");
    private static final Map<Character, String> UNICODE_SUBSCRIPT_MAP = Map.ofEntries(
            Map.entry('₀', "0"),
            Map.entry('₁', "1"),
            Map.entry('₂', "2"),
            Map.entry('₃', "3"),
            Map.entry('₄', "4"),
            Map.entry('₅', "5"),
            Map.entry('₆', "6"),
            Map.entry('₇', "7"),
            Map.entry('₈', "8"),
            Map.entry('₉', "9")
    );
    private static final Map<Character, String> UNICODE_SUPERSCRIPT_MAP = Map.ofEntries(
            Map.entry('⁰', "0"),
            Map.entry('¹', "1"),
            Map.entry('²', "2"),
            Map.entry('³', "3"),
            Map.entry('⁴', "4"),
            Map.entry('⁵', "5"),
            Map.entry('⁶', "6"),
            Map.entry('⁷', "7"),
            Map.entry('⁸', "8"),
            Map.entry('⁹', "9"),
            Map.entry('⁺', "+"),
            Map.entry('⁻', "-")
    );
    private static final Set<String> CHEMICAL_ELEMENT_SYMBOLS = Set.of(
            "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
            "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
            "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
            "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
            "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
            "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
            "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
            "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
            "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
            "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
            "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
            "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og"
    );
    private static final ThreadLocal<DocumentBuilder> XML_BUILDER = ThreadLocal.withInitial(DocxToHtmlConverter::newSecureDocumentBuilder);
    private static final ThreadLocal<Transformer> NODE_SERIALIZER = ThreadLocal.withInitial(DocxToHtmlConverter::newSecureNodeSerializer);

    private final boolean includeMathJax;
    private final OmmlToMathmlTransformer ommlTransformer;
    private final MathmlSidecarRegistry sidecarRegistry;
    private final Subject subject;
    private final OutputMode outputMode;
    private final boolean chemistrySubject;
    private final SubjectProfile subjectProfile;
    private final SubjectRules subjectRules;
    private final Map<String, SavedBinary> savedAssetByRelationship = new HashMap<>();
    private final AtomicInteger assetCounter = new AtomicInteger(1);
    private final AtomicInteger ommlCounter = new AtomicInteger(0);
    private final AtomicInteger sidecarMathmlCounter = new AtomicInteger(0);
    private final AtomicInteger olePreviewCounter = new AtomicInteger(0);
    private final AtomicInteger oleEquationPreviewCounter = new AtomicInteger(0);
    private final AtomicInteger oleDiagramPreviewCounter = new AtomicInteger(0);
    private final AtomicInteger oleIllustrationPreviewCounter = new AtomicInteger(0);
    private final AtomicInteger emfWmfPreviewCounter = new AtomicInteger(0);
    private final AtomicInteger unresolvedVisioPreviewCounter = new AtomicInteger(0);
    private final AtomicInteger olePlaceholderCounter = new AtomicInteger(0);
    private final AtomicInteger dsmt4TotalCounter = new AtomicInteger(0);
    private final AtomicInteger dsmt4SidecarResolvedCounter = new AtomicInteger(0);
    private final AtomicInteger dsmt4UnresolvedCounter = new AtomicInteger(0);
    private final AtomicInteger dsmt4ManifestMissingCounter = new AtomicInteger(0);
    private final AtomicInteger dsmt4ManifestMismatchCounter = new AtomicInteger(0);
    private final AtomicInteger dsmt4FallbackPlaceholderCounter = new AtomicInteger(0);
    private final AtomicInteger normalizedTextFixCounter = new AtomicInteger(0);
    private final AtomicInteger chemistryInlineFixCounter = new AtomicInteger(0);
    private final AtomicInteger chemistryArrowSymbolFixCounter = new AtomicInteger(0);
    private final AtomicInteger chemistryUnitFixCounter = new AtomicInteger(0);
    private final AtomicInteger physicsUnitFixCounter = new AtomicInteger(0);
    private final AtomicInteger physicsTextFixCounter = new AtomicInteger(0);
    private final AtomicInteger mixedMathTextCleanupCounter = new AtomicInteger(0);
    private final AtomicInteger mathGlyphCleanupCounter = new AtomicInteger(0);
    private final AtomicInteger emptyParagraphRemovedCounter = new AtomicInteger(0);
    private final AtomicInteger tableAdjacentEmptyParagraphCleanupCounter = new AtomicInteger(0);
    private final AtomicInteger tableCellEmptyParagraphRemovedCounter = new AtomicInteger(0);
    private final AtomicInteger mathBlockFlowCleanupCounter = new AtomicInteger(0);
    private final AtomicInteger suppressedBlankStandaloneImageCounter = new AtomicInteger(0);
    private final AtomicInteger suppressedNonessentialStandaloneImageCounter = new AtomicInteger(0);
    private final AtomicInteger restoredContextImageCounter = new AtomicInteger(0);
    private final AtomicInteger rasterizedMetafileCounter = new AtomicInteger(0);
    private final AtomicInteger rasterizedMetafileCacheHitCounter = new AtomicInteger(0);
    private final AtomicLong stageDocxLoadNanos = new AtomicLong(0L);
    private final AtomicLong stageBodyRenderNanos = new AtomicLong(0L);
    private final AtomicLong stageEssayPolicyNanos = new AtomicLong(0L);
    private final AtomicLong stageHtmlBuildNanos = new AtomicLong(0L);
    private final AtomicLong stagePublishSanitizeNanos = new AtomicLong(0L);
    private final AtomicLong stageHtmlWriteNanos = new AtomicLong(0L);
    private final AtomicLong stageOmmlHandlingNanos = new AtomicLong(0L);
    private final AtomicLong stageMathTypeHandlingNanos = new AtomicLong(0L);
    private final AtomicLong stageImageRenderingNanos = new AtomicLong(0L);
    private final AtomicLong stageHtmlCleanupNanos = new AtomicLong(0L);
    private final String rasterToolCommand = detectRasterToolCommand();
    private final String officeToolCommand = detectOfficeToolCommand();
    private final AtomicInteger officeRenderFailureCounter = new AtomicInteger(0);
    private final Set<String> trimmedChemicalDiagramAssets = new HashSet<>();
    private final Map<String, GenericInlineTrimResult> genericInlineTrimByAsset = new HashMap<>();
    private final Path metafileRasterCacheDir = initMetafileRasterCacheDir();
    private final Set<String> warnedMalformedRelationshipKeys = new HashSet<>();
    private String currentSourceDocxContext = "";

    public DocxToHtmlConverter(boolean includeMathJax) {
        this(includeMathJax, MathmlSidecarRegistry.empty(), Subject.GENERIC, OutputMode.PUBLISH);
    }

    public DocxToHtmlConverter(boolean includeMathJax, MathmlSidecarRegistry sidecarRegistry) {
        this(includeMathJax, sidecarRegistry, Subject.GENERIC, OutputMode.PUBLISH);
    }

    public DocxToHtmlConverter(boolean includeMathJax, MathmlSidecarRegistry sidecarRegistry, Subject subject) {
        this(includeMathJax, sidecarRegistry, subject, OutputMode.PUBLISH);
    }

    public DocxToHtmlConverter(boolean includeMathJax, MathmlSidecarRegistry sidecarRegistry, Subject subject, OutputMode outputMode) {
        configureHeadlessAwtForRasterization();
        this.includeMathJax = includeMathJax;
        this.sidecarRegistry = sidecarRegistry == null ? MathmlSidecarRegistry.empty() : sidecarRegistry;
        this.subject = subject == null ? Subject.GENERIC : subject;
        this.outputMode = outputMode == null ? OutputMode.PUBLISH : outputMode;
        this.chemistrySubject = this.subject == Subject.CHEMISTRY;
        this.subjectProfile = SubjectProfileFactory.create(this.subject);
        this.subjectRules = this.subjectProfile.getRules();
        this.ommlTransformer = new OmmlToMathmlTransformer();
    }

    private static void configureHeadlessAwtForRasterization() {
        if (System.getProperty("java.awt.headless") == null) {
            System.setProperty("java.awt.headless", "true");
        }
    }

    public ConversionSummary convert(Path inputDocx, Path outputHtml) throws Exception {
        Path normalizedOutput = outputHtml.toAbsolutePath().normalize();
        Path parent = normalizedOutput.getParent();
        if (parent == null) {
            parent = Path.of(".").toAbsolutePath().normalize();
        }
        Files.createDirectories(parent);

        String baseName = stripExtension(normalizedOutput.getFileName().toString());
        Path assetDir = parent.resolve(baseName + "_files");
        Files.createDirectories(assetDir);

        String previousDocxContext = currentSourceDocxContext;
        currentSourceDocxContext = inputDocx.toAbsolutePath().normalize().toString();
        warnedMalformedRelationshipKeys.clear();
        try {
            long openStart = System.nanoTime();
            try (InputStream is = Files.newInputStream(inputDocx);
                 XWPFDocument doc = new XWPFDocument(is)) {
                stageDocxLoadNanos.addAndGet(System.nanoTime() - openStart);

                long bodyRenderStart = System.nanoTime();
                StringBuilder body = new StringBuilder(16_384);
                for (IBodyElement element : doc.getBodyElements()) {
                    body.append(renderBodyElement(element, doc, assetDir));
                }
                stageBodyRenderNanos.addAndGet(System.nanoTime() - bodyRenderStart);

                long essayPolicyStart = System.nanoTime();
                String bodyHtml = applyEssayFigurePlacementPolicy(body.toString());
                stageEssayPolicyNanos.addAndGet(System.nanoTime() - essayPolicyStart);

                long structuralCleanupStart = System.nanoTime();
                bodyHtml = applyCoreStructuralHtmlCleanup(bodyHtml, assetDir);
                stageHtmlCleanupNanos.addAndGet(System.nanoTime() - structuralCleanupStart);

                long buildHtmlStart = System.nanoTime();
                String html = buildHtmlDocument(inputDocx.getFileName().toString(), bodyHtml);
                stageHtmlBuildNanos.addAndGet(System.nanoTime() - buildHtmlStart);

                if (outputMode == OutputMode.PUBLISH) {
                    long sanitizeStart = System.nanoTime();
                    html = sanitizePublishHtmlOutput(html);
                    stagePublishSanitizeNanos.addAndGet(System.nanoTime() - sanitizeStart);
                }

                long writeStart = System.nanoTime();
                Files.writeString(normalizedOutput, html, StandardCharsets.UTF_8);
                stageHtmlWriteNanos.addAndGet(System.nanoTime() - writeStart);
            }

            return new ConversionSummary(
                    ommlCounter.get(),
                    sidecarMathmlCounter.get(),
                    olePreviewCounter.get(),
                    olePlaceholderCounter.get(),
                    dsmt4TotalCounter.get(),
                    dsmt4SidecarResolvedCounter.get(),
                    dsmt4UnresolvedCounter.get(),
                    dsmt4ManifestMissingCounter.get(),
                    dsmt4ManifestMismatchCounter.get(),
                    dsmt4FallbackPlaceholderCounter.get(),
                    oleEquationPreviewCounter.get(),
                    oleDiagramPreviewCounter.get(),
                    oleIllustrationPreviewCounter.get(),
                    emfWmfPreviewCounter.get(),
                    unresolvedVisioPreviewCounter.get(),
                    normalizedTextFixCounter.get(),
                    chemistryInlineFixCounter.get(),
                    chemistryArrowSymbolFixCounter.get(),
                    chemistryUnitFixCounter.get(),
                    physicsUnitFixCounter.get(),
                    physicsTextFixCounter.get(),
                    mixedMathTextCleanupCounter.get(),
                    mathGlyphCleanupCounter.get(),
                    emptyParagraphRemovedCounter.get(),
                    tableAdjacentEmptyParagraphCleanupCounter.get(),
                    tableCellEmptyParagraphRemovedCounter.get(),
                    mathBlockFlowCleanupCounter.get(),
                    suppressedBlankStandaloneImageCounter.get(),
                    suppressedNonessentialStandaloneImageCounter.get(),
                    restoredContextImageCounter.get(),
                    rasterizedMetafileCounter.get(),
                    rasterizedMetafileCacheHitCounter.get(),
                    nanosToMillis(stageDocxLoadNanos.get()),
                    nanosToMillis(stageBodyRenderNanos.get()),
                    nanosToMillis(stageEssayPolicyNanos.get()),
                    nanosToMillis(stageHtmlBuildNanos.get()),
                    nanosToMillis(stagePublishSanitizeNanos.get()),
                    nanosToMillis(stageHtmlWriteNanos.get()),
                    nanosToMillis(stageOmmlHandlingNanos.get()),
                    nanosToMillis(stageMathTypeHandlingNanos.get()),
                    nanosToMillis(stageImageRenderingNanos.get()),
                    nanosToMillis(stageHtmlCleanupNanos.get())
            );
        } finally {
            currentSourceDocxContext = previousDocxContext;
            warnedMalformedRelationshipKeys.clear();
        }
    }

    private String renderBodyElement(IBodyElement element, XWPFDocument doc, Path assetDir) throws Exception {
        return switch (element.getElementType()) {
            case PARAGRAPH -> renderParagraph((XWPFParagraph) element, doc, assetDir);
            case TABLE -> renderTable((XWPFTable) element, doc, assetDir);
            default -> "";
        };
    }

    private String renderBodyElements(IBody body, XWPFDocument doc, Path assetDir) throws Exception {
        StringBuilder out = new StringBuilder();
        for (IBodyElement element : body.getBodyElements()) {
            out.append(renderBodyElement(element, doc, assetDir));
        }
        return out.toString();
    }

    private String renderParagraph(XWPFParagraph paragraph, XWPFDocument doc, Path assetDir) throws Exception {
        Document xml = parseXml(paragraph.getCTP().xmlText());
        String content = renderNodes(xml.getDocumentElement().getChildNodes(), doc, assetDir, false);
        boolean insideTableCell = paragraph.getBody() instanceof XWPFTableCell;
        return composeParagraphHtml(content, insideTableCell);
    }

    private String renderTable(XWPFTable table, XWPFDocument doc, Path assetDir) throws Exception {
        String essayLayout = maybeRenderEssayQuestionTableAsFigure(table, doc, assetDir);
        if (essayLayout != null) {
            return essayLayout;
        }
        StringBuilder out = new StringBuilder();
        out.append("<table class=\"docx-table\">\n");
        for (XWPFTableRow row : table.getRows()) {
            out.append("  <tr>\n");
            for (XWPFTableCell cell : row.getTableCells()) {
                out.append("    <td>");
                out.append(renderBodyElements(cell, doc, assetDir));
                out.append("</td>\n");
            }
            out.append("  </tr>\n");
        }
        out.append("</table>\n");
        return out.toString();
    }

    private String composeParagraphHtml(String rawContent, boolean insideTableCell) {
        String content = Objects.toString(rawContent, "");
        if (content.isBlank()) {
            return "<p></p>\n";
        }

        StringBuilder out = new StringBuilder(content.length() + 32);
        var matcher = BLOCK_MATH_PATTERN.matcher(content);
        int lastEnd = 0;
        while (matcher.find()) {
            appendInlineParagraphSegment(out, content.substring(lastEnd, matcher.start()), insideTableCell);
            String blockMathHtml = matcher.group();
            if (insideTableCell) {
                String demotedInline = demoteSimpleBlockMathInTableCell(blockMathHtml);
                if (demotedInline != null) {
                    appendInlineParagraphSegment(out, demotedInline, true);
                } else {
                    out.append(blockMathHtml).append('\n');
                }
            } else {
                out.append(blockMathHtml).append('\n');
            }
            lastEnd = matcher.end();
        }
        appendInlineParagraphSegment(out, content.substring(lastEnd), insideTableCell);

        if (out.isEmpty()) {
            return "<p></p>\n";
        }
        return out.toString();
    }

    private void appendInlineParagraphSegment(StringBuilder out, String rawSegment, boolean insideTableCell) {
        String normalized = normalizeInlineSpacing(rawSegment).trim();
        normalized = normalizeInlineHtmlSegment(normalized);
        if (normalized.isEmpty()) {
            return;
        }

        EssayInlineFigureSplit essayInlineFigureSplit = splitEssayInlineFigureParagraph(normalized);
        if (essayInlineFigureSplit != null) {
            String questionParagraph = "<p>" + essayInlineFigureSplit.questionHtml() + "</p>";
            if (essayInlineFigureSplit.role() == FigureRole.CONTEXT) {
                out.append(buildEssayContextLayout(questionParagraph, essayInlineFigureSplit.imageTag())).append('\n');
            } else {
                out.append(questionParagraph).append('\n');
                out.append(buildEssayFigureBlock(essayInlineFigureSplit.imageTag(), FigureRole.ESSENTIAL)).append('\n');
            }
            return;
        }

        SegmentSplit split = splitLeadingImageParagraph(normalized);
        if (split != null) {
            out.append("<p>").append(split.imageHtml()).append("</p>\n");
            normalized = split.trailingHtml();
            if (normalized.isEmpty()) {
                return;
            }
        }

        String promotedDisplay = promoteStandaloneInlineMathToBlock(normalized, insideTableCell);
        if (promotedDisplay != null) {
            out.append(promotedDisplay).append('\n');
            return;
        }
        out.append("<p>").append(normalized).append("</p>\n");
    }

    private String normalizeInlineHtmlSegment(String htmlSegment) {
        long start = System.nanoTime();
        try {
            if (htmlSegment == null || htmlSegment.isEmpty()) {
                return htmlSegment;
            }
            String out = htmlSegment;
            if (containsWordFieldLeakageMarkers(out)) {
                out = stripWordFieldCodeLeakage(out);
            }
            out = normalizeVisibleHtmlText(out);
            out = normalizeContextualBetaMinusFromEmptyBaseMsuP(out);
            if (containsCoreHtmlScriptNormalizationSignals(out)) {
                out = normalizeCoreHtmlScriptRuns(out);
            }
            if (subject == Subject.PHYSICS) {
                out = normalizePhysicsInlineMathTemperatureSuffix(out);
            }
            if (subjectRules.chemistryHtmlScriptNormalizationEnabled()) {
                out = normalizeChemistryHtmlScriptRuns(out);
            }
            if (containsWordFieldLeakageMarkers(out)) {
                out = stripWordFieldCodeLeakage(out);
            }
            return dropRedundantEquationFallbacks(out);
        } finally {
            stageHtmlCleanupNanos.addAndGet(System.nanoTime() - start);
        }
    }

    private String normalizeContextualBetaMinusFromEmptyBaseMsuP(String html) {
        if (html == null || html.isBlank()) {
            return html;
        }
        Matcher matcher = EMPTY_BASE_MINUS_MSUP_MATH_INLINE_PATTERN.matcher(html);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            int contextStart = Math.max(0, matcher.start() - 260);
            int contextEnd = Math.min(html.length(), matcher.end() + 260);
            String contextWindow = html.substring(contextStart, contextEnd);
            if (!containsRadiationNotationContext(contextWindow)) {
                continue;
            }
            if (out == null) {
                out = new StringBuffer(html.length() + 32);
            }
            hitCount++;
            matcher.appendReplacement(out, Matcher.quoteReplacement(
                    "<span class=\"math-inline mathml\"><math xmlns=\"http://www.w3.org/1998/Math/MathML\"><msup><mi>β</mi><mo>−</mo></msup></math></span>"
            ));
        }
        if (out == null || hitCount == 0) {
            return html;
        }
        matcher.appendTail(out);
        normalizedTextFixCounter.addAndGet(hitCount);
        return out.toString();
    }

    private static boolean containsRadiationNotationContext(String htmlWindow) {
        if (htmlWindow == null || htmlWindow.isBlank()) {
            return false;
        }
        String plain = HTML_TAG_PATTERN.matcher(htmlWindow).replaceAll(" ").toLowerCase(Locale.ROOT);
        String ascii = DIACRITIC_MARK_PATTERN.matcher(Normalizer.normalize(plain, Normalizer.Form.NFD))
                .replaceAll("")
                .toLowerCase(Locale.ROOT);
        return plain.contains("tia")
                || plain.contains("phóng xạ")
                || plain.contains("đồng vị")
                || plain.contains("hạt nhân")
                || plain.contains("cacbon")
                || plain.contains("c-14")
                || plain.contains("phân rã")
                || ascii.contains("phong xa")
                || ascii.contains("dong vi")
                || ascii.contains("hat nhan")
                || ascii.contains("phan ra");
    }

    private static String normalizeInlineSpacing(String html) {
        if (html == null || html.isEmpty()) {
            return "";
        }
        String out = html;
        out = INLINE_IMAGE_TO_TEXT_PATTERN.matcher(out).replaceAll("$1 ");
        out = TEXT_TO_INLINE_IMAGE_PATTERN.matcher(out).replaceAll("$1 $2");
        out = INLINE_MATH_TO_TEXT_PATTERN.matcher(out).replaceAll("$1 ");
        out = INLINE_MATH_SPACE_BEFORE_PUNCT_PATTERN.matcher(out).replaceAll("$1$2");
        out = TEXT_TO_INLINE_MATH_PATTERN.matcher(out).replaceAll("$1 $2");
        out = PUNCT_TO_INLINE_MATH_PATTERN.matcher(out).replaceAll("$1 $2");
        out = INLINE_MATH_TO_INLINE_MATH_PATTERN.matcher(out).replaceAll("$1 $2");
        return out;
    }

    private String normalizeTextContent(String rawText) {
        return normalizeTextValue(rawText, true);
    }

    private String replaceAndCount(String input, Pattern pattern, String replacement, boolean countFixes) {
        ReplacementOutcome outcome = applyReplacement(input, pattern, replacement);
        if (countFixes) {
            normalizedTextFixCounter.addAndGet(outcome.hitCount());
        }
        return outcome.replaced();
    }

    private static ReplacementOutcome applyReplacement(String input, Pattern pattern, String replacement) {
        Matcher matcher = pattern.matcher(input);
        StringBuffer replaced = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (replaced == null) {
                replaced = new StringBuffer(input.length() + 16);
            }
            hitCount++;
            matcher.appendReplacement(replaced, Matcher.quoteReplacement(replacement));
        }
        if (hitCount == 0 || replaced == null) {
            return new ReplacementOutcome(input, 0);
        }
        matcher.appendTail(replaced);
        return new ReplacementOutcome(replaced.toString(), hitCount);
    }

    private String normalizeTextValue(String rawText, boolean countFixes) {
        if (rawText == null || rawText.isEmpty()) {
            return rawText;
        }
        String out = Normalizer.normalize(rawText, Normalizer.Form.NFC);
        ReplacementOutcome legacySymbolOutcome = normalizeLegacySymbolGlyphs(out);
        if (countFixes && legacySymbolOutcome.hitCount() > 0) {
            normalizedTextFixCounter.addAndGet(legacySymbolOutcome.hitCount());
        }
        out = legacySymbolOutcome.replaced();
        out = applyDeterministicTextRules(out, countFixes);
        return out;
    }

    private static ReplacementOutcome normalizeLegacySymbolGlyphs(String input) {
        if (input == null || input.isEmpty()) {
            return new ReplacementOutcome(input, 0);
        }
        StringBuilder out = null;
        int hitCount = 0;
        int len = input.length();
        for (int i = 0; i < len; i++) {
            char ch = input.charAt(i);
            String mapped = switch (ch) {
                case '\uf061' -> "α";
                case '\uf062' -> "β";
                case '\uf067' -> "γ";
                case '\uf070' -> "π";
                case '\uf077' -> "ω";
                case '\uf057' -> "Ω";
                case '\uf044' -> "Δ";
                case '\uf0ae' -> "→";
                case '\uf0b0' -> "°";
                case '\uf0b4' -> "×";
                case '\uf02d' -> "−";
                case '\uf0bb' -> "≈";
                case '\uf0b7' -> "•";
                default -> null;
            };
            if (mapped == null) {
                if (out != null) {
                    out.append(ch);
                }
                continue;
            }
            if (out == null) {
                out = new StringBuilder(len + 16);
                out.append(input, 0, i);
            }
            out.append(mapped);
            hitCount++;
        }
        if (out == null) {
            return new ReplacementOutcome(input, 0);
        }
        return new ReplacementOutcome(out.toString(), hitCount);
    }

    private String applyDeterministicTextRules(String input, boolean countFixes) {
        String out = input;
        for (TextReplacementRule rule : subjectRules.textReplacementRules()) {
            ReplacementOutcome outcome = applyReplacement(out, rule.pattern(), rule.replacement());
            if (countFixes && outcome.hitCount() > 0) {
                normalizedTextFixCounter.addAndGet(outcome.hitCount());
                if (subject == Subject.PHYSICS) {
                    if (isPhysicsUnitReplacement(rule.replacement())) {
                        physicsUnitFixCounter.addAndGet(outcome.hitCount());
                    } else {
                        physicsTextFixCounter.addAndGet(outcome.hitCount());
                    }
                }
                if (subject == Subject.MATH && isMathGlyphTextReplacement(rule.replacement())) {
                    mathGlyphCleanupCounter.addAndGet(outcome.hitCount());
                }
            }
            out = outcome.replaced();
        }
        return out;
    }

    private static boolean isPhysicsUnitReplacement(String replacement) {
        if (replacement == null || replacement.isBlank()) {
            return false;
        }
        return replacement.contains("cm²")
                || replacement.contains("cm³")
                || replacement.contains("mol")
                || replacement.contains("MPa");
    }

    private static boolean isMathGlyphTextReplacement(String replacement) {
        if (replacement == null || replacement.isBlank()) {
            return false;
        }
        return replacement.contains("•")
                || replacement.contains("mô tả")
                || replacement.contains("kết quả")
                || replacement.contains("Ta có")
                || replacement.contains("tỉ lệ")
                || replacement.contains("cần tính")
                || replacement.contains("đồ thị");
    }

    private String normalizeVisibleHtmlText(String html) {
        if (html == null || html.isEmpty()) {
            return html;
        }
        if (html.indexOf('<') < 0) {
            return normalizeVisibleTextChunk(html);
        }
        StringBuilder out = new StringBuilder(html.length() + 64);
        Matcher matcher = HTML_TAG_PATTERN.matcher(html);
        int last = 0;
        int mathDepth = 0;
        while (matcher.find()) {
            if (matcher.start() > last) {
                String textChunk = html.substring(last, matcher.start());
                out.append(mathDepth > 0 ? textChunk : normalizeVisibleTextChunk(textChunk));
            }
            String tag = matcher.group();
            out.append(tag);
            mathDepth += mathDepthDelta(tag);
            last = matcher.end();
        }
        if (last < html.length()) {
            String trailing = html.substring(last);
            out.append(mathDepth > 0 ? trailing : normalizeVisibleTextChunk(trailing));
        }
        return out.toString();
    }

    private static int mathDepthDelta(String tag) {
        String lower = tag.toLowerCase(Locale.ROOT);
        if (lower.startsWith("</math")) {
            return -1;
        }
        if (lower.startsWith("<math") && !lower.endsWith("/>")) {
            return 1;
        }
        return 0;
    }

    private String normalizeVisibleTextChunk(String textChunk) {
        String normalized = normalizeTextValue(textChunk, true);
        if (!subjectRules.chemistryInlineNormalizationEnabled()) {
            return normalized;
        }
        normalized = normalizeChemistryArrowSymbols(normalized);
        normalized = normalizeChemicalUnits(normalized);
        return normalizeChemicalInlineTokens(normalized);
    }

    private String normalizeCoreHtmlScriptRuns(String html) {
        if (html == null || html.isBlank()) {
            return html;
        }
        if (!containsCoreHtmlScriptNormalizationSignals(html)) {
            return html;
        }
        String out = decodeHtmlScriptTagContent(html, HTML_SUB_TAG_UNICODE_PATTERN, false);
        out = decodeHtmlScriptTagContent(out, HTML_SUP_TAG_UNICODE_PATTERN, true);
        out = mergeAdjacentSuperscripts(out, UNICODE_SUP_BEFORE_HTML_SUP_PATTERN, true);
        out = mergeAdjacentSuperscripts(out, HTML_SUP_BEFORE_UNICODE_SUP_PATTERN, false);
        out = mergeAdjacentHtmlSupTags(out);
        if (subject == Subject.PHYSICS) {
            out = normalizePhysicsInlineTemperatureHtml(out);
        }
        return replaceAndCount(out, EMPTY_SUBSCRIPT_SPACER_PATTERN, "&emsp;", true);
    }

    private String normalizeChemistryHtmlScriptRuns(String html) {
        String out = html;
        out = replaceChemicalPattern(
                out,
                HTML_TEMP_SUP_C_PATTERN,
                matcher -> wrapChemInlineWithFlags(HtmlUtil.escape(matcher.group(1) + "°C"), true, false),
                chemistryUnitFixCounter
        );
        out = replaceChemicalPattern(
                out,
                CHEMICAL_DOWNS_ANODE_MALFORMED_PATTERN,
                matcher -> "2Cl<sup>-</sup> → Cl<sub>2</sub> + " + wrapChemInlineWithFlags("2e<sup>−</sup>", true, false),
                chemistryArrowSymbolFixCounter
        );
        out = replaceAndCountChemistryHtmlFix(out, CHEM_PUNCTUATION_IN_SCRIPT_PATTERN, "$1");
        out = replaceAndCountChemistryHtmlFix(out, FALSE_STRUCTURAL_CO_NH_CHARGE_PATTERN, "$1-");
        out = replaceAndCountChemistryHtmlFix(out, FALSE_STRUCTURAL_CO_CHARGE_PATTERN, "$1-");
        return out;
    }

    private String normalizePhysicsInlineTemperatureHtml(String html) {
        Matcher matcher = HTML_PHYSICS_TEMP_SUP_C_PATTERN.matcher(html);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (out == null) {
                out = new StringBuffer(html.length() + 16);
            }
            hitCount++;
            matcher.appendReplacement(out, Matcher.quoteReplacement(matcher.group(1) + " °C"));
        }
        if (out == null || hitCount == 0) {
            return html;
        }
        matcher.appendTail(out);
        normalizedTextFixCounter.addAndGet(hitCount);
        physicsUnitFixCounter.addAndGet(hitCount);
        return out.toString();
    }

    private String normalizePhysicsInlineMathTemperatureSuffix(String html) {
        Matcher matcher = INLINE_MATH_DEGREE_C_SUFFIX_PATTERN.matcher(html);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (out == null) {
                out = new StringBuffer(html.length() + 32);
            }
            hitCount++;
            String replacement = matcher.group(1)
                    + Objects.toString(matcher.group("before"), "")
                    + "<mn>" + HtmlUtil.escape(Objects.toString(matcher.group("value"), "").trim()) + "</mn><mspace width=\"0.33em\"/><mtext>°C</mtext>"
                    + Objects.toString(matcher.group("after"), "")
                    + "</math></span>";
            matcher.appendReplacement(out, Matcher.quoteReplacement(replacement));
        }
        if (out == null || hitCount == 0) {
            return html;
        }
        matcher.appendTail(out);
        normalizedTextFixCounter.addAndGet(hitCount);
        physicsUnitFixCounter.addAndGet(hitCount);
        return out.toString();
    }

    private String stripWordFieldCodeLeakage(String html) {
        if (html == null || html.isBlank()) {
            return html;
        }
        if (!containsWordFieldLeakageMarkers(html)) {
            return html;
        }
        String out = html;
        out = replaceAndCount(out, WORD_FIELD_INCLUDEPICTURE_COMMAND_PATTERN, "", true);
        out = replaceAndCount(out, WORD_FIELD_HTTP_QUOTED_URL_BEFORE_IMAGE_PATTERN, "", true);
        out = replaceAndCount(out, WORD_FIELD_LEAKAGE_TOKEN_PATTERN, "", true);
        out = replaceAndCount(out, WORD_FIELD_SWITCH_TOKEN_PATTERN, "", true);
        return out;
    }

    private String decodeHtmlScriptTagContent(String html, Pattern pattern, boolean superscript) {
        Matcher matcher = pattern.matcher(html);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (out == null) {
                out = new StringBuffer(html.length() + 32);
            }
            String decoded = superscript ? decodeSuperscript(matcher.group(1)) : decodeSubscript(matcher.group(1));
            hitCount++;
            matcher.appendReplacement(out, Matcher.quoteReplacement((superscript ? "<sup>" : "<sub>") + HtmlUtil.escape(decoded) + (superscript ? "</sup>" : "</sub>")));
        }
        if (out == null || hitCount == 0) {
            return html;
        }
        matcher.appendTail(out);
        incrementChemistryInlineFixes(hitCount);
        return out.toString();
    }

    private String mergeAdjacentSuperscripts(String html, Pattern pattern, boolean unicodeFirst) {
        Matcher matcher = pattern.matcher(html);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (out == null) {
                out = new StringBuffer(html.length() + 24);
            }
            String merged = unicodeFirst
                    ? decodeSuperscript(matcher.group(1)) + matcher.group(2)
                    : matcher.group(1) + decodeSuperscript(matcher.group(2));
            hitCount++;
            matcher.appendReplacement(out, Matcher.quoteReplacement("<sup>" + HtmlUtil.escape(merged) + "</sup>"));
        }
        if (out == null || hitCount == 0) {
            return html;
        }
        matcher.appendTail(out);
        incrementChemistryInlineFixes(hitCount);
        return out.toString();
    }

    private String mergeAdjacentHtmlSupTags(String html) {
        String out = html;
        int totalFixes = 0;
        while (true) {
            Matcher matcher = ADJACENT_HTML_SUP_TAG_PATTERN.matcher(out);
            StringBuffer replaced = null;
            int hitCount = 0;
            while (matcher.find()) {
                String left = Objects.toString(matcher.group(1), "").trim();
                String right = Objects.toString(matcher.group(2), "").trim();
                if (left.isEmpty() || right.isEmpty()) {
                    continue;
                }
                if (replaced == null) {
                    replaced = new StringBuffer(out.length() + 24);
                }
                hitCount++;
                String merged = "<sup>" + HtmlUtil.escape(left + right) + "</sup>";
                matcher.appendReplacement(replaced, Matcher.quoteReplacement(merged));
            }
            if (replaced == null || hitCount == 0) {
                break;
            }
            matcher.appendTail(replaced);
            out = replaced.toString();
            totalFixes += hitCount;
        }
        if (totalFixes > 0) {
            incrementChemistryInlineFixes(totalFixes);
        }
        return out;
    }

    private String replaceAndCountChemistryHtmlFix(String input, Pattern pattern, String replacement) {
        Matcher matcher = pattern.matcher(input);
        StringBuffer replaced = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (replaced == null) {
                replaced = new StringBuffer(input.length() + 16);
            }
            hitCount++;
            matcher.appendReplacement(replaced, replacement);
        }
        if (replaced == null || hitCount == 0) {
            return input;
        }
        matcher.appendTail(replaced);
        incrementChemistryInlineFixes(hitCount);
        return replaced.toString();
    }

    private String normalizeChemicalUnits(String input) {
        String out = replaceChemicalPattern(
                input,
                CHEMICAL_UNIT_TOKEN_PATTERN,
                matcher -> wrapChemInlineWithFlags("mol·L<sup>−1</sup>", true, false),
                chemistryUnitFixCounter
        );
        out = replaceChemicalPattern(
                out,
                CHEMICAL_ELECTRON_CHARGE_PATTERN,
                matcher -> {
                    String coeff = Objects.toString(matcher.group(1), "");
                    String sign = Objects.toString(matcher.group(2), "");
                    String normalizedSign = ("+".equals(sign) ? "+" : "−");
                    String prefix = coeff.isBlank() ? "" : HtmlUtil.escape(coeff);
                    return wrapChemInlineWithFlags(prefix + "e<sup>" + normalizedSign + "</sup>", true, false);
                },
                chemistryUnitFixCounter
        );
        out = replaceChemicalPattern(
                out,
                CHEMICAL_ELECTRON_LOOSE_PLUS_PATTERN,
                matcher -> {
                    String coeff = Objects.toString(matcher.group(1), "");
                    String prefix = coeff.isBlank() ? "" : HtmlUtil.escape(coeff);
                    return wrapChemInlineWithFlags(prefix + "e<sup>−</sup> + ", true, false);
                },
                chemistryUnitFixCounter
        );
        out = replaceChemicalPattern(
                out,
                CHEMICAL_TEMP_C_TOKEN_PATTERN,
                matcher -> wrapChemInlineWithFlags(HtmlUtil.escape(matcher.group(1) + "°C"), true, false),
                chemistryUnitFixCounter
        );
        out = replaceChemicalPattern(
                out,
                CHEMICAL_POWER_OF_TEN_PATTERN,
                matcher -> wrapChemInlineWithFlags("10<sup>" + HtmlUtil.escape(matcher.group(1)) + "</sup>", true, false),
                chemistryUnitFixCounter
        );
        return replaceChemicalPattern(
                out,
                CHEMICAL_ENTHALPY_TOKEN_PATTERN,
                matcher -> wrapChemInlineWithFlags(
                        HtmlUtil.escape("Δ" + matcher.group(1) + "H°") + "<sub>" + HtmlUtil.escape(matcher.group(2)) + "</sub>",
                        true,
                        false
                ),
                chemistryUnitFixCounter
        );
    }

    private String normalizeChemistryArrowSymbols(String input) {
        String out = replaceChemicalPattern(
                input,
                CHEMICAL_BI_ARROW_PATTERN,
                matcher -> wrapChemInlineWithFlags("⇌", false, true),
                chemistryArrowSymbolFixCounter
        );
        return replaceChemicalPattern(
                out,
                CHEMICAL_FORWARD_ARROW_PATTERN,
                matcher -> wrapChemInlineWithFlags("→", false, true),
                chemistryArrowSymbolFixCounter
        );
    }

    private String normalizeChemicalInlineTokens(String input) {
        Matcher matcher = CHEMICAL_TOKEN_PATTERN.matcher(input);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            String token = matcher.group();
            String normalized = normalizeChemicalToken(token);
            if (normalized.equals(token)) {
                continue;
            }
            if (out == null) {
                out = new StringBuffer(input.length() + 64);
            }
            hitCount++;
            matcher.appendReplacement(out, Matcher.quoteReplacement(normalized));
        }
        if (out == null || hitCount == 0) {
            return input;
        }
        matcher.appendTail(out);
        incrementChemistryInlineFixes(hitCount);
        return out.toString();
    }

    private String normalizeChemicalToken(String token) {
        if (token == null || token.isEmpty() || !looksLikeChemicalToken(token)) {
            return token;
        }

        StringBuilder out = new StringBuilder(token.length() + 24);
        boolean changed = false;
        int i = 0;

        int isotopeEnd = scanUnicodeSuperscriptSequence(token, 0);
        if (isotopeEnd > 0 && isotopeEnd < token.length() && startsWithChemicalElement(token, isotopeEnd)) {
            out.append("<sup>").append(HtmlUtil.escape(decodeUnicodeSuperscript(token.substring(0, isotopeEnd)))).append("</sup>");
            i = isotopeEnd;
            changed = true;
        }

        while (i < token.length()) {
            char current = token.charAt(i);
            if (isGroupOpen(current)) {
                int close = findClosingGroup(token, i);
                if (close > i) {
                    String innerToken = token.substring(i + 1, close);
                    String normalizedInner = normalizeChemicalToken(innerToken);
                    String innerHtml = normalizedInner.equals(innerToken) ? HtmlUtil.escape(innerToken) : unwrapChemInline(normalizedInner);
                    out.append(HtmlUtil.escape(Character.toString(current)))
                            .append(innerHtml)
                            .append(HtmlUtil.escape(Character.toString(groupCloseFor(current))));
                    i = close + 1;
                    int subEnd = scanSubscriptSequence(token, i);
                    if (subEnd > i) {
                        out.append("<sub>").append(HtmlUtil.escape(decodeSubscript(token.substring(i, subEnd)))).append("</sub>");
                        changed = true;
                        i = subEnd;
                    }
                    int supEnd = scanTrailingChargeSequence(token, i);
                    if (supEnd > i) {
                        out.append("<sup>").append(HtmlUtil.escape(decodeSuperscript(token.substring(i, supEnd)))).append("</sup>");
                        changed = true;
                        i = supEnd;
                    }
                    if (!normalizedInner.equals(innerToken)) {
                        changed = true;
                    }
                    continue;
                }
            }
            if (current == ')' || current == ']') {
                out.append(HtmlUtil.escape(Character.toString(current)));
                i++;
                int subEnd = scanSubscriptSequence(token, i);
                if (subEnd > i) {
                    out.append("<sub>").append(HtmlUtil.escape(decodeSubscript(token.substring(i, subEnd)))).append("</sub>");
                    changed = true;
                    i = subEnd;
                }
                int supEnd = scanTrailingChargeSequence(token, i);
                if (supEnd > i) {
                    out.append("<sup>").append(HtmlUtil.escape(decodeSuperscript(token.substring(i, supEnd)))).append("</sup>");
                    changed = true;
                    i = supEnd;
                }
                continue;
            }

            String symbol = readChemicalElement(token, i);
            if (symbol != null) {
                out.append(HtmlUtil.escape(symbol));
                i += symbol.length();
                int subEnd = scanSubscriptSequence(token, i);
                if (subEnd > i) {
                    out.append("<sub>").append(HtmlUtil.escape(decodeSubscript(token.substring(i, subEnd)))).append("</sub>");
                    changed = true;
                    i = subEnd;
                }
                int supEnd = scanTrailingChargeSequence(token, i);
                if (supEnd > i) {
                    out.append("<sup>").append(HtmlUtil.escape(decodeSuperscript(token.substring(i, supEnd)))).append("</sup>");
                    changed = true;
                    i = supEnd;
                }
                continue;
            }

            char ch = token.charAt(i);
            if (isUnicodeSuperscript(ch) || isUnicodeSubscript(ch)) {
                changed = true;
            }
            out.append(HtmlUtil.escape(Character.toString(ch)));
            i++;
        }

        if (!changed) {
            return token;
        }
        return wrapChemInline(out.toString());
    }

    private boolean looksLikeChemicalToken(String token) {
        if (token == null || token.length() < 2) {
            return false;
        }
        if (CHEMICAL_UNIT_TOKEN_PATTERN.matcher(token).matches()) {
            return true;
        }
        if (isSimpleElementFormula(token)) {
            return true;
        }
        int requiredSignals = 0;
        if (token.indexOf('(') >= 0 || token.indexOf('/') >= 0) {
            requiredSignals++;
        }
        if (token.chars().anyMatch(ch -> Character.isDigit(ch) || isUnicodeSubscript((char) ch) || isUnicodeSuperscript((char) ch))) {
            requiredSignals++;
        }
        if (token.indexOf('+') >= 0 || token.indexOf('-') >= 0 || token.indexOf('⁺') >= 0 || token.indexOf('⁻') >= 0 || token.indexOf('−') >= 0) {
            requiredSignals++;
        }
        int elementCount = countChemicalElements(token);
        if (elementCount >= 2 && requiredSignals > 0) {
            return true;
        }
        return elementCount == 1 && requiredSignals >= 2;
    }

    private boolean isSimpleElementFormula(String token) {
        int offset = scanUnicodeSuperscriptSequence(token, 0);
        String symbol = readChemicalElement(token, offset);
        if (symbol == null) {
            return false;
        }
        offset += symbol.length();
        int subEnd = scanSubscriptSequence(token, offset);
        boolean hasSubscript = subEnd > offset;
        offset = subEnd;
        int supEnd = scanTrailingChargeSequence(token, offset);
        boolean hasSuperscript = supEnd > offset;
        if (!hasSubscript && !hasSuperscript) {
            return false;
        }
        return (hasSuperscript ? supEnd : offset) == token.length();
    }

    private int countChemicalElements(String token) {
        int count = 0;
        for (int i = 0; i < token.length(); ) {
            if (isGroupOpen(token.charAt(i))) {
                int close = findClosingGroup(token, i);
                if (close > i) {
                    count += countChemicalElements(token.substring(i + 1, close));
                    i = close + 1;
                    continue;
                }
            }
            String symbol = readChemicalElement(token, i);
            if (symbol != null) {
                count++;
                i += symbol.length();
                continue;
            }
            i++;
        }
        return count;
    }

    private static String readChemicalElement(String token, int offset) {
        if (offset < 0 || offset >= token.length() || !Character.isUpperCase(token.charAt(offset))) {
            return null;
        }
        if (offset + 1 < token.length() && Character.isLowerCase(token.charAt(offset + 1))) {
            String candidate = token.substring(offset, offset + 2);
            if (CHEMICAL_ELEMENT_SYMBOLS.contains(candidate)) {
                return candidate;
            }
        }
        String candidate = token.substring(offset, offset + 1);
        return CHEMICAL_ELEMENT_SYMBOLS.contains(candidate) ? candidate : null;
    }

    private static boolean startsWithChemicalElement(String token, int offset) {
        return readChemicalElement(token, offset) != null;
    }

    private static boolean isGroupOpen(char ch) {
        return ch == '(' || ch == '[';
    }

    private static char groupCloseFor(char openChar) {
        return openChar == '[' ? ']' : ')';
    }

    private static int findClosingGroup(String token, int openIndex) {
        char openChar = token.charAt(openIndex);
        char closeChar = groupCloseFor(openChar);
        int depth = 0;
        for (int i = openIndex; i < token.length(); i++) {
            char ch = token.charAt(i);
            if (ch == openChar) {
                depth++;
            } else if (ch == closeChar) {
                depth--;
                if (depth == 0) {
                    return i;
                }
            }
        }
        return -1;
    }

    private static int scanSubscriptSequence(String token, int offset) {
        int i = offset;
        while (i < token.length()) {
            char ch = token.charAt(i);
            if (Character.isDigit(ch) || isUnicodeSubscript(ch)) {
                i++;
                continue;
            }
            break;
        }
        return i;
    }

    private static int scanUnicodeSuperscriptSequence(String token, int offset) {
        int i = offset;
        while (i < token.length() && isUnicodeSuperscript(token.charAt(i))) {
            i++;
        }
        return i;
    }

    private static int scanTrailingChargeSequence(String token, int offset) {
        int i = offset;
        boolean sawSignal = false;
        while (i < token.length()) {
            char ch = token.charAt(i);
            if (Character.isDigit(ch) || isUnicodeSuperscript(ch)) {
                sawSignal = true;
                i++;
                continue;
            }
            if (ch == '+' || ch == '⁺' || ch == '⁻') {
                sawSignal = true;
                i++;
                continue;
            }
            if (ch == '-' || ch == '−') {
                if (i + 1 < token.length()) {
                    char next = token.charAt(i + 1);
                    if (Character.isLetter(next) || isGroupOpen(next)) {
                        break;
                    }
                }
                sawSignal = true;
                i++;
                continue;
            }
            break;
        }
        return sawSignal ? i : offset;
    }

    private static String decodeSubscript(String raw) {
        StringBuilder out = new StringBuilder(raw.length());
        for (int i = 0; i < raw.length(); i++) {
            char ch = raw.charAt(i);
            out.append(UNICODE_SUBSCRIPT_MAP.getOrDefault(ch, Character.toString(ch)));
        }
        return out.toString();
    }

    private static String decodeSuperscript(String raw) {
        StringBuilder out = new StringBuilder(raw.length());
        for (int i = 0; i < raw.length(); i++) {
            char ch = raw.charAt(i);
            if (Character.isDigit(ch)) {
                out.append(ch);
                continue;
            }
            if (ch == '−') {
                out.append('-');
                continue;
            }
            out.append(UNICODE_SUPERSCRIPT_MAP.getOrDefault(ch, Character.toString(ch)));
        }
        return out.toString();
    }

    private static String decodeUnicodeSuperscript(String raw) {
        return decodeSuperscript(raw);
    }

    private static boolean isUnicodeSubscript(char ch) {
        return UNICODE_SUBSCRIPT_MAP.containsKey(ch);
    }

    private static boolean isUnicodeSuperscript(char ch) {
        return UNICODE_SUPERSCRIPT_MAP.containsKey(ch);
    }

    private String replaceChemicalPattern(
            String input,
            Pattern pattern,
            Function<Matcher, String> replacementBuilder,
            AtomicInteger subjectFixCounter
    ) {
        Matcher matcher = pattern.matcher(input);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (out == null) {
                out = new StringBuffer(input.length() + 32);
            }
            hitCount++;
            matcher.appendReplacement(out, Matcher.quoteReplacement(replacementBuilder.apply(matcher)));
        }
        if (out == null || hitCount == 0) {
            return input;
        }
        matcher.appendTail(out);
        incrementChemistryInlineFixes(hitCount);
        subjectFixCounter.addAndGet(hitCount);
        return out.toString();
    }

    private void incrementChemistryInlineFixes(int delta) {
        if (delta > 0 && chemistrySubject) {
            chemistryInlineFixCounter.addAndGet(delta);
        }
    }

    private static String wrapChemInline(String innerHtml) {
        return "<span class=\"chem-inline\" data-chem-fixed=\"1\">" + innerHtml + "</span>";
    }

    private static String wrapChemInlineWithFlags(String innerHtml, boolean unitFix, boolean arrowFix) {
        StringBuilder span = new StringBuilder(96);
        span.append("<span class=\"chem-inline\" data-chem-fixed=\"1\"");
        if (unitFix) {
            span.append(" data-chem-unit-fixed=\"1\"");
        }
        if (arrowFix) {
            span.append(" data-chem-arrow-fixed=\"1\"");
        }
        span.append(">").append(innerHtml).append("</span>");
        return span.toString();
    }

    private static String unwrapChemInline(String html) {
        Matcher matcher = CHEM_INLINE_WRAPPER_PATTERN.matcher(html);
        return matcher.matches() ? Objects.toString(matcher.group(1), "") : html;
    }

    private String normalizeMathmlFragment(String mathml) {
        if (mathml == null || mathml.isBlank()) {
            return mathml;
        }
        String out = normalizePhysicsMathmlUnitLayout(mathml);
        out = normalizeMathMathmlGlyphLayout(out);
        boolean suspicious = out.contains("Ñ")
                || out.contains("Ð")
                || out.contains("ð")
                || out.contains("taán")
                || out.contains("phaûn")
                || out.contains("öùng")
                || out.contains("taïo")
                || out.contains("thaønh")
                || out.contains("Mpa");
        if (!suspicious) {
            return sanitizeMathmlForPublish(out);
        }
        try {
            Document mathDocument = parseXml(out);
            normalizeXmlTextNodes(mathDocument.getDocumentElement());
            out = serializeNode(mathDocument.getDocumentElement());
        } catch (Exception ignored) {
            out = applyDeterministicTextRules(out, true);
        }
        if (subjectRules.chemistryHtmlScriptNormalizationEnabled()) {
            out = replaceAndCount(out, CORR_MATHML_SPLIT_DAET_PATTERN, "<mtext>Đặt</mtext>", true);
        }
        return sanitizeMathmlForPublish(out);
    }

    private String normalizePhysicsMathmlUnitLayout(String mathml) {
        if (subject != Subject.PHYSICS || mathml == null || mathml.isBlank()) {
            return mathml;
        }
        String out = mathml;
        out = normalizePhysicsIsotopeMathml(out);
        out = replaceMathmlLayoutAndCount(out, MATHML_CM2_SPLIT_PATTERN, "$1$2cm²</mtext>");
        out = replaceMathmlLayoutAndCount(out, MATHML_CM3_SPLIT_PATTERN, "$1$2cm³</mtext>");
        out = replaceMathmlLayoutAndCount(out, MATHML_MOL_INV_SPLIT_PATTERN, "$1$2mol⁻¹</mtext>");
        out = replaceMathmlLayoutAndCount(out, MATHML_BLANK_BASE_DEGREE_C_PATTERN, "$1°C</mtext>");
        out = normalizePhysicsDegreeCMathml(out);
        out = normalizePhysicsNumberUnitMathml(out);
        out = normalizePhysicsTrigFunctionMathml(out);
        out = replaceMathmlLayoutAndCount(out, MATHML_DEGREE_SYMBOL_PLUS_C_PATTERN, "<mtext>°C</mtext>");
        out = replaceMathmlLayoutAndCount(out, MATHML_J_PER_MOL_DOT_K_PATTERN, "$1$2J/mol·K</mtext>");
        out = replaceMathmlLayoutAndCount(out, MATHML_R_CONSTANT_UNIT_PATTERN, "$1J·mol⁻¹·K⁻¹</mtext>");
        out = replaceMathmlLayoutAndCount(out, MATHML_M_PER_S2_PATTERN, "$1$2m/s²</mtext>");
        return out;
    }

    private String normalizePhysicsIsotopeMathml(String input) {
        String cleaned = normalizePhysicsEmptyBaseMsubsupIsotope(input);
        Matcher matcher = MATHML_EMPTY_BASE_ISOTOPE_PATTERN.matcher(cleaned);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            String massNumber = Objects.toString(matcher.group(1), "").trim();
            String atomicNumber = Objects.toString(matcher.group(2), "").trim();
            String symbolTag = Objects.toString(matcher.group("symbolTag"), "mtext");
            String symbolAttrs = Objects.toString(matcher.group("symbolAttrs"), "");
            String symbol = Objects.toString(matcher.group("symbol"), "").trim();
            if (massNumber.isEmpty() || atomicNumber.isEmpty() || symbol.isEmpty()) {
                continue;
            }
            if (out == null) {
                out = new StringBuffer(input.length() + 48);
            }
            hitCount++;
            String replacement = "<msubsup><mrow/>"
                    + buildMathmlScalarToken(atomicNumber)
                    + buildMathmlScalarToken(massNumber)
                    + "</msubsup><" + symbolTag + symbolAttrs + ">" + HtmlUtil.escape(symbol) + "</" + symbolTag + ">";
            matcher.appendReplacement(out, Matcher.quoteReplacement(replacement));
        }
        if (out == null || hitCount == 0) {
            return cleaned;
        }
        matcher.appendTail(out);
        mixedMathTextCleanupCounter.addAndGet(hitCount);
        return out.toString();
    }

    private String normalizePhysicsEmptyBaseMsubsupIsotope(String input) {
        Matcher matcher = MATHML_EMPTY_BASE_MSUBSUP_ISOTOPE_PATTERN.matcher(input);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            String attrs = Objects.toString(matcher.group("attrs"), "");
            String atomic = Objects.toString(matcher.group("atomic"), "").trim();
            String mass = Objects.toString(matcher.group("mass"), "").trim();
            String symbolTag = Objects.toString(matcher.group("symbolTag"), "mtext");
            String symbolAttrs = Objects.toString(matcher.group("symbolAttrs"), "");
            String symbol = Objects.toString(matcher.group("symbol"), "").trim();
            if (atomic.isEmpty() || mass.isEmpty() || symbol.isEmpty()) {
                continue;
            }
            if (out == null) {
                out = new StringBuffer(input.length() + 48);
            }
            hitCount++;
            String replacement = "<msubsup" + attrs + "><mrow/>"
                    + buildMathmlScalarToken(atomic)
                    + buildMathmlScalarToken(mass)
                    + "</msubsup><" + symbolTag + symbolAttrs + ">" + HtmlUtil.escape(symbol) + "</" + symbolTag + ">";
            matcher.appendReplacement(out, Matcher.quoteReplacement(replacement));
        }
        if (out == null || hitCount == 0) {
            return input;
        }
        matcher.appendTail(out);
        mixedMathTextCleanupCounter.addAndGet(hitCount);
        return out.toString();
    }

    private String normalizePhysicsDegreeCMathml(String input) {
        Matcher matcher = MATHML_DEGREE_C_SUP_PATTERN.matcher(input);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (out == null) {
                out = new StringBuffer(input.length() + 32);
            }
            hitCount++;
            String replacement = "<mn>" + HtmlUtil.escape(matcher.group(1).trim()) + "</mn><mspace width=\"0.33em\"/><mtext>°C</mtext>";
            matcher.appendReplacement(out, Matcher.quoteReplacement(replacement));
        }
        if (out == null || hitCount == 0) {
            return input;
        }
        matcher.appendTail(out);
        mixedMathTextCleanupCounter.addAndGet(hitCount);
        return out.toString();
    }

    private String normalizePhysicsNumberUnitMathml(String input) {
        String out = normalizePhysicsTrailingCommaUnits(input);
        return normalizePhysicsSplitMicroUnits(out);
    }

    private String normalizePhysicsTrailingCommaUnits(String input) {
        Matcher matcher = MATHML_NUMBER_WITH_TRAILING_COMMA_BEFORE_UNIT_PATTERN.matcher(input);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (out == null) {
                out = new StringBuffer(input.length() + 32);
            }
            hitCount++;
            String replacement = "<mn" + matcher.group("numAttrs") + ">" + HtmlUtil.escape(matcher.group("value").trim())
                    + "</mn><mspace width=\"0.33em\"/>" + matcher.group("unit");
            matcher.appendReplacement(out, Matcher.quoteReplacement(replacement));
        }
        if (out == null || hitCount == 0) {
            return input;
        }
        matcher.appendTail(out);
        mixedMathTextCleanupCounter.addAndGet(hitCount);
        return out.toString();
    }

    private String normalizePhysicsSplitMicroUnits(String input) {
        Matcher matcher = MATHML_SPLIT_MICRO_UNIT_PATTERN.matcher(input);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (out == null) {
                out = new StringBuffer(input.length() + 32);
            }
            hitCount++;
            String replacement = "<mn" + matcher.group("numAttrs") + ">" + HtmlUtil.escape(matcher.group("value").trim())
                    + "</mn><mspace width=\"0.33em\"/><mtext>μ" + HtmlUtil.escape(matcher.group("suffix").trim()) + "</mtext>";
            matcher.appendReplacement(out, Matcher.quoteReplacement(replacement));
        }
        if (out == null || hitCount == 0) {
            return input;
        }
        matcher.appendTail(out);
        mixedMathTextCleanupCounter.addAndGet(hitCount);
        return out.toString();
    }

    private String normalizePhysicsTrigFunctionMathml(String input) {
        Matcher matcher = MATHML_SPLIT_TRIG_FUNCTION_PATTERN.matcher(input);
        StringBuffer out = null;
        int hitCount = 0;
        while (matcher.find()) {
            String head = Objects.toString(matcher.group("head"), "");
            String tail = Objects.toString(matcher.group("tail"), "");
            String combined = head + tail;
            if (!combined.equals("cos") && !combined.equals("sin") && !combined.equals("tan")) {
                continue;
            }
            if (out == null) {
                out = new StringBuffer(input.length() + 24);
            }
            hitCount++;
            String openParen = Objects.toString(matcher.group("open"), "").isEmpty() ? "" : "<mo>(</mo>";
            String replacement = "<mi" + matcher.group("prefixAttrs") + ">" + combined + "</mi>" + openParen;
            matcher.appendReplacement(out, Matcher.quoteReplacement(replacement));
        }
        if (out == null || hitCount == 0) {
            return input;
        }
        matcher.appendTail(out);
        mixedMathTextCleanupCounter.addAndGet(hitCount);
        return out.toString();
    }

    private static String buildMathmlScalarToken(String value) {
        if (value != null && value.chars().allMatch(Character::isDigit)) {
            return "<mn>" + HtmlUtil.escape(value) + "</mn>";
        }
        return "<mi>" + HtmlUtil.escape(Objects.toString(value, "")) + "</mi>";
    }

    private String normalizeMathMathmlGlyphLayout(String mathml) {
        if (subject != Subject.MATH || mathml == null || mathml.isBlank()) {
            return mathml;
        }
        String out = mathml;
        out = replaceMathmlGlyphAndCount(out, MATHML_MALGUN_CONDITIONAL_BAR_PATTERN, "<mo>|</mo>");
        out = replaceMathmlGlyphAndCount(out, MATHML_INTEGER_SET_Z_PATTERN, "<mo>∈</mo><mtext>ℤ</mtext>");
        out = replaceMathmlGlyphAndCount(out, MATHML_MML_VECTOR_COMBINING_ARROW_PATTERN, "<mml:mo stretchy=\"true\">→</mml:mo>");
        out = replaceMathmlGlyphAndCount(out, MATHML_VECTOR_COMBINING_ARROW_PATTERN, "<mo stretchy=\"true\">→</mo>");
        return out;
    }

    private static String sanitizeMathmlForPublish(String mathml) {
        if (mathml == null || mathml.isBlank()) {
            return mathml;
        }
        try {
            Document mathDocument = parseXml(mathml);
            Element canonicalRoot = canonicalizeMathmlForPublish(mathDocument.getDocumentElement(), mathDocument);
            return serializeNode(canonicalRoot);
        } catch (Exception ignored) {
            String sanitized = MATHML_TRANSPECT_NAMESPACE_PATTERN.matcher(mathml).replaceAll("");
            sanitized = MATHML_DATA_SOURCE_ATTR_PATTERN.matcher(sanitized).replaceAll("");
            sanitized = MATHML_PREFIXED_ROOT_NAMESPACE_PATTERN.matcher(sanitized)
                    .replaceFirst("<math$1xmlns=\"" + MATHML_NAMESPACE_URI + "\"$2>");
            return MATHML_PREFIXED_TAG_PATTERN.matcher(sanitized).replaceAll("$1");
        }
    }

    private static Element canonicalizeMathmlForPublish(Element element, Document ownerDocument) {
        Element current = element;
        String localName = current.getLocalName();
        if (localName == null || localName.isBlank()) {
            localName = stripXmlPrefix(current.getNodeName());
        }
        if (!MATHML_NAMESPACE_URI.equals(current.getNamespaceURI()) || current.getPrefix() != null) {
            current = (Element) ownerDocument.renameNode(current, MATHML_NAMESPACE_URI, localName);
        }
        removeMathPublishLeakageAttributes(current);
        List<Element> childElements = new ArrayList<>();
        NodeList children = current.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child instanceof Element childElement) {
                childElements.add(childElement);
            }
        }
        for (Element childElement : childElements) {
            canonicalizeMathmlForPublish(childElement, ownerDocument);
        }
        return current;
    }

    private static void removeMathPublishLeakageAttributes(Element element) {
        List<String> attrNamesToRemove = new ArrayList<>();
        NamedNodeMap attributes = element.getAttributes();
        for (int i = 0; i < attributes.getLength(); i++) {
            Node attribute = attributes.item(i);
            String namespaceUri = attribute.getNamespaceURI();
            String nodeName = attribute.getNodeName();
            String localName = attribute.getLocalName();
            if (XMLConstants.XMLNS_ATTRIBUTE_NS_URI.equals(namespaceUri)
                    || TRANSPECT_NAMESPACE_URI.equals(namespaceUri)
                    || "data-math-source".equals(nodeName)
                    || "data-math-source".equals(localName)) {
                attrNamesToRemove.add(nodeName);
            }
        }
        for (String attrName : attrNamesToRemove) {
            element.removeAttribute(attrName);
        }
        if (!MATHML_NAMESPACE_URI.equals(element.getNamespaceURI())) {
            return;
        }
        if (!MATHML_NAMESPACE_URI.equals(element.getAttribute("xmlns"))) {
            element.setAttribute("xmlns", MATHML_NAMESPACE_URI);
        }
    }

    private static String stripXmlPrefix(String name) {
        if (name == null || name.isBlank()) {
            return "";
        }
        int colon = name.indexOf(':');
        return colon >= 0 ? name.substring(colon + 1) : name;
    }

    private static String sanitizePublishHtmlOutput(String html) {
        if (html == null || html.isBlank()) {
            return html;
        }
        return PUBLISH_DEBUG_ATTR_PATTERN.matcher(html).replaceAll("");
    }

    private String replaceMathmlLayoutAndCount(String input, Pattern pattern, String replacement) {
        Matcher matcher = pattern.matcher(input);
        StringBuffer replaced = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (replaced == null) {
                replaced = new StringBuffer(input.length() + 32);
            }
            hitCount++;
            matcher.appendReplacement(replaced, replacement);
        }
        if (replaced == null || hitCount == 0) {
            return input;
        }
        matcher.appendTail(replaced);
        mixedMathTextCleanupCounter.addAndGet(hitCount);
        return replaced.toString();
    }

    private String replaceMathmlGlyphAndCount(String input, Pattern pattern, String replacement) {
        Matcher matcher = pattern.matcher(input);
        StringBuffer replaced = null;
        int hitCount = 0;
        while (matcher.find()) {
            if (replaced == null) {
                replaced = new StringBuffer(input.length() + 32);
            }
            hitCount++;
            matcher.appendReplacement(replaced, Matcher.quoteReplacement(replacement));
        }
        if (replaced == null || hitCount == 0) {
            return input;
        }
        matcher.appendTail(replaced);
        mathGlyphCleanupCounter.addAndGet(hitCount);
        return replaced.toString();
    }

    private void normalizeXmlTextNodes(Node node) {
        if (node == null) {
            return;
        }
        if (node.getNodeType() == Node.TEXT_NODE) {
            node.setNodeValue(normalizeTextValue(node.getNodeValue(), true));
            return;
        }
        NodeList children = node.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            normalizeXmlTextNodes(children.item(i));
        }
    }

    private static String dropRedundantEquationFallbacks(String html) {
        if (html == null || html.isBlank()) {
            return html;
        }
        if (!containsEquationFallbackCandidates(html)) {
            return html;
        }
        String out = REDUNDANT_EQUATION_FALLBACK_PATTERN.matcher(html).replaceAll("");
        return REDUNDANT_UNSUPPORTED_EQUATION_SPAN_PATTERN.matcher(out).replaceAll("");
    }

    private static String promoteStandaloneInlineMathToBlock(String normalized, boolean insideTableCell) {
        if (insideTableCell) {
            return null;
        }
        var matcher = SINGLE_INLINE_MATH_PATTERN.matcher(normalized);
        if (!matcher.matches()) {
            return null;
        }
        String inlineClasses = Objects.toString(matcher.group(1), "").trim();
        String inner = Objects.toString(matcher.group(2), "");
        if (!shouldUseDisplayMath(inner)) {
            return null;
        }
        inner = enforceMathDisplay(inner, true);
        String blockClass = inlineClasses.isEmpty() ? "math-block" : "math-block " + inlineClasses;
        return "<div class=\"" + blockClass + "\">" + inner + "</div>";
    }

    private static String demoteSimpleBlockMathInTableCell(String blockMathHtml) {
        var matcher = SINGLE_BLOCK_MATH_PATTERN.matcher(Objects.toString(blockMathHtml, "").trim());
        if (!matcher.matches()) {
            return null;
        }
        String blockClasses = Objects.toString(matcher.group(1), "").trim();
        String inner = Objects.toString(matcher.group(2), "");
        if (shouldUseDisplayMath(inner)) {
            return null;
        }
        inner = enforceMathDisplay(inner, false);
        String inlineClass = blockClasses.isEmpty() ? "math-inline" : "math-inline " + blockClasses;
        return "<span class=\"" + inlineClass + "\">" + inner + "</span>";
    }

    private static boolean shouldUseDisplayMath(String innerMathHtml) {
        String s = Objects.toString(innerMathHtml, "").toLowerCase(Locale.ROOT);
        if (s.length() >= 220) {
            return true;
        }
        return s.contains("<mfrac")
                || s.contains("<msqrt")
                || s.contains("<mroot")
                || s.contains("<mtable")
                || s.contains("<munderover")
                || s.contains("<munder")
                || s.contains("<mover")
                || s.contains("displaystyle=\"true\"");
    }

    private static SegmentSplit splitLeadingImageParagraph(String normalized) {
        var matcher = LEADING_IMAGES_PATTERN.matcher(normalized);
        if (!matcher.matches()) {
            return null;
        }
        String images = Objects.toString(matcher.group("images"), "").trim();
        String rest = Objects.toString(matcher.group("rest"), "").trim();
        if (images.isEmpty() || rest.isEmpty()) {
            return null;
        }
        String plainRest = rest.replaceAll("<[^>]+>", " ").replace("&nbsp;", " ").trim();
        if (!QUESTION_OR_SECTION_PATTERN.matcher(plainRest).matches()) {
            return null;
        }
        return new SegmentSplit(images, rest);
    }

    private String maybeRenderEssayQuestionTableAsFigure(XWPFTable table, XWPFDocument doc, Path assetDir) throws Exception {
        if (table == null || table.getRows().size() != 1) {
            return null;
        }
        XWPFTableRow row = table.getRows().get(0);
        if (row == null || row.getTableCells().size() != 2) {
            return null;
        }

        String leftCellHtml = renderBodyElements(row.getTableCells().get(0), doc, assetDir);
        String rightCellHtml = renderBodyElements(row.getTableCells().get(1), doc, assetDir);

        EssayTableFigureLayout layout = detectEssayTableFigureLayout(leftCellHtml, rightCellHtml, subject);
        if (layout == null) {
            return null;
        }
        StringBuilder out = new StringBuilder(layout.textHtml().length() + layout.imageTag().length() + 96);
        if (layout.role() == FigureRole.CONTEXT) {
            out.append(buildEssayContextLayout(layout.textHtml(), layout.imageTag())).append('\n');
        } else {
            out.append(buildEssentialQuestionFigureLayout(layout.textHtml(), layout.imageTag())).append('\n');
        }
        return out.toString();
    }

    private static EssayTableFigureLayout detectEssayTableFigureLayout(String firstCellHtml, String secondCellHtml, Subject subject) {
        List<String> firstImages = extractTableFigureImageTags(firstCellHtml);
        List<String> secondImages = extractTableFigureImageTags(secondCellHtml);
        if (firstImages.size() + secondImages.size() != 1) {
            return null;
        }
        boolean firstIsImageCell = firstImages.size() == 1;
        String imageCellHtml = firstIsImageCell ? firstCellHtml : secondCellHtml;
        String textCellHtml = firstIsImageCell ? secondCellHtml : firstCellHtml;
        String imageTag = firstIsImageCell ? firstImages.get(0) : secondImages.get(0);

        if (imageTag.contains("essay-figure-image")) {
            return null;
        }
        if (!extractTableFigureImageTags(textCellHtml).isEmpty()) {
            return null;
        }

        String imageCellResidual = stripHtmlToPlainText(TABLE_FIGURE_IMAGE_TAG_PATTERN.matcher(imageCellHtml).replaceAll(" "));
        if (imageCellResidual.length() > 32) {
            return null;
        }
        String textPlain = stripHtmlToPlainText(TABLE_FIGURE_IMAGE_TAG_PATTERN.matcher(textCellHtml).replaceAll(" "));
        FigureRole role = classifyEssayFigureRole(textPlain, imageTag);
        if (!isEligibleFigureTablePlacementText(textPlain, role, subject)) {
            return null;
        }
        return new EssayTableFigureLayout(textCellHtml, imageTag, role);
    }

    private static String buildEssentialQuestionFigureLayout(String textHtml, String imageTag) {
        String normalizedText = Objects.toString(textHtml, "").trim();
        String figureBlock = buildEssayFigureBlock(imageTag, FigureRole.ESSENTIAL);
        if (normalizedText.isBlank()) {
            return figureBlock;
        }
        String lower = normalizedText.toLowerCase(Locale.ROOT);
        if (!lower.startsWith("<p")) {
            return normalizedText + "\n" + figureBlock;
        }
        int firstParagraphEnd = lower.indexOf("</p>");
        if (firstParagraphEnd < 0) {
            return normalizedText + "\n" + figureBlock;
        }
        String stemParagraph = normalizedText.substring(0, firstParagraphEnd + 4).trim();
        String trailingParagraphs = normalizedText.substring(firstParagraphEnd + 4).trim();
        if (trailingParagraphs.isBlank()) {
            return stemParagraph + "\n" + figureBlock;
        }
        return stemParagraph + "\n" + figureBlock + "\n" + trailingParagraphs;
    }

    private static EssayInlineFigureSplit splitEssayInlineFigureParagraph(String normalized) {
        Matcher matcher = INLINE_IMAGE_TAG_PATTERN.matcher(normalized);
        if (!matcher.find()) {
            return null;
        }
        String imageTag = matcher.group();
        int start = matcher.start();
        int end = matcher.end();
        if (imageTag.contains("essay-figure-image")) {
            return null;
        }
        if (matcher.find()) {
            return null;
        }

        String questionHtml = (normalized.substring(0, start) + " " + normalized.substring(end)).trim();
        questionHtml = normalizeInlineSpacing(questionHtml).trim();
        String plainText = stripHtmlToPlainText(questionHtml);
        FigureRole role = classifyEssayFigureRole(plainText, imageTag);
        if (!isEligibleEssayFigurePlacementText(plainText, role)) {
            return null;
        }
        return new EssayInlineFigureSplit(questionHtml, imageTag, role);
    }

    private String applyEssayFigurePlacementPolicy(String bodyHtml) {
        if (subject != Subject.MATH || bodyHtml == null || bodyHtml.isBlank()) {
            return bodyHtml;
        }
        String relocated = relocateLeadingImageParagraphBeforeEssayQuestion(bodyHtml);
        return wrapConsecutiveEssentialFigures(relocated);
    }

    private String applyCoreStructuralHtmlCleanup(String bodyHtml, Path assetDir) {
        if (bodyHtml == null || bodyHtml.isBlank()) {
            return bodyHtml;
        }
        int beforeEmptyParagraphCount = countPatternMatches(EMPTY_PARAGRAPH_TAG_PATTERN, bodyHtml);
        int beforeTableAdjacentEmptyParagraphCount = countEmptyParagraphsInNamedGroup(bodyHtml, EMPTY_PARAGRAPH_CHAIN_BEFORE_DOCX_TABLE_PATTERN)
                + countEmptyParagraphsInNamedGroup(bodyHtml, EMPTY_PARAGRAPH_CHAIN_AFTER_DOCX_TABLE_PATTERN);
        int beforeTableCellEmptyParagraphCount = countEmptyParagraphsInNamedGroup(bodyHtml, EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_START_PATTERN)
                + countEmptyParagraphsInNamedGroup(bodyHtml, EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_END_PATTERN);
        int beforeMalformedMathBlockFlowCount = countMalformedMathBlockFlowIssues(bodyHtml);

        String out = normalizeMalformedMathBlockFlow(bodyHtml);
        out = promoteStandaloneQuestionImageParagraphs(out);
        out = suppressBlankStandaloneInlineImageParagraphs(out, assetDir);
        out = suppressNonessentialStandaloneContextImageParagraphs(out);
        out = stripEmptyParagraphChains(out, EMPTY_PARAGRAPH_CHAIN_BEFORE_DOCX_TABLE_PATTERN, matcher -> "");
        out = stripEmptyParagraphChains(out, EMPTY_PARAGRAPH_CHAIN_AFTER_DOCX_TABLE_PATTERN, matcher -> Objects.toString(matcher.group(1), ""));
        out = stripEmptyParagraphChains(out, EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_START_PATTERN, matcher -> Objects.toString(matcher.group(1), ""));
        out = stripEmptyParagraphChains(out, EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_END_PATTERN, matcher -> Objects.toString(matcher.group(2), ""));
        out = EMPTY_PARAGRAPH_TAG_PATTERN.matcher(out).replaceAll("");
        out = out.replaceAll("\\n{3,}", "\n\n");

        int afterEmptyParagraphCount = countPatternMatches(EMPTY_PARAGRAPH_TAG_PATTERN, out);
        int afterTableAdjacentEmptyParagraphCount = countEmptyParagraphsInNamedGroup(out, EMPTY_PARAGRAPH_CHAIN_BEFORE_DOCX_TABLE_PATTERN)
                + countEmptyParagraphsInNamedGroup(out, EMPTY_PARAGRAPH_CHAIN_AFTER_DOCX_TABLE_PATTERN);
        int afterTableCellEmptyParagraphCount = countEmptyParagraphsInNamedGroup(out, EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_START_PATTERN)
                + countEmptyParagraphsInNamedGroup(out, EMPTY_PARAGRAPH_CHAIN_AT_TABLE_CELL_END_PATTERN);
        int afterMalformedMathBlockFlowCount = countMalformedMathBlockFlowIssues(out);

        emptyParagraphRemovedCounter.addAndGet(Math.max(0, beforeEmptyParagraphCount - afterEmptyParagraphCount));
        tableAdjacentEmptyParagraphCleanupCounter.addAndGet(Math.max(0, beforeTableAdjacentEmptyParagraphCount - afterTableAdjacentEmptyParagraphCount));
        tableCellEmptyParagraphRemovedCounter.addAndGet(Math.max(0, beforeTableCellEmptyParagraphCount - afterTableCellEmptyParagraphCount));
        mathBlockFlowCleanupCounter.addAndGet(Math.max(0, beforeMalformedMathBlockFlowCount - afterMalformedMathBlockFlowCount));
        return out;
    }

    private String promoteStandaloneQuestionImageParagraphs(String bodyHtml) {
        if (bodyHtml == null || bodyHtml.isBlank()) {
            return bodyHtml;
        }
        Matcher matcher = STANDALONE_QUESTION_IMAGE_PARAGRAPH_PATTERN.matcher(bodyHtml);
        StringBuffer out = null;
        int promotedCount = 0;
        while (matcher.find()) {
            String imageTag = Objects.toString(matcher.group("img"), "");
            Map<String, String> attrs = parseTagAttributes(imageTag);
            if (!attrs.containsKey("data-ole-kind") && !attrs.containsKey("data-fallback-type")) {
                continue;
            }
            if (out == null) {
                out = new StringBuffer(bodyHtml.length() + 96);
            }
            String replacement = buildEssayFigureBlock(imageTag, FigureRole.ESSENTIAL);
            matcher.appendReplacement(out, Matcher.quoteReplacement(replacement));
            promotedCount++;
        }
        if (out == null || promotedCount == 0) {
            return bodyHtml;
        }
        matcher.appendTail(out);
        normalizedTextFixCounter.addAndGet(promotedCount);
        return out.toString();
    }

    private String suppressBlankStandaloneInlineImageParagraphs(String bodyHtml, Path assetDir) {
        if (bodyHtml == null || bodyHtml.isBlank()) {
            return bodyHtml;
        }
        Matcher matcher = STANDALONE_INLINE_IMAGE_PARAGRAPH_PATTERN.matcher(bodyHtml);
        StringBuffer out = null;
        int suppressedCount = 0;
        Map<String, Boolean> suppressibilityBySource = new HashMap<>();
        while (matcher.find()) {
            String imageTag = Objects.toString(matcher.group("img"), "");
            if (hasProtectedContextSignalAroundStandaloneImage(bodyHtml, matcher.start(), matcher.end())) {
                continue;
            }
            if (!isSuppressibleStandaloneInlineImageTag(imageTag, assetDir, suppressibilityBySource)) {
                continue;
            }
            if (out == null) {
                out = new StringBuffer(bodyHtml.length() + 48);
            }
            matcher.appendReplacement(out, "");
            suppressedCount++;
        }
        if (out == null || suppressedCount == 0) {
            return bodyHtml;
        }
        matcher.appendTail(out);
        suppressedBlankStandaloneImageCounter.addAndGet(suppressedCount);
        return out.toString();
    }

    private static boolean isSuppressibleStandaloneInlineImageTag(
            String imageTag,
            Path assetDir,
            Map<String, Boolean> suppressibilityBySource
    ) {
        if (imageTag == null || imageTag.isBlank()) {
            return false;
        }
        Map<String, String> attrs = parseTagAttributes(imageTag);
        String cssClass = Objects.toString(attrs.get("class"), "").toLowerCase(Locale.ROOT);
        if (!cssClass.contains("inline-image")) {
            return false;
        }
        if (cssClass.contains("essay-figure-image")
                || cssClass.contains("essential-figure-image")
                || cssClass.contains("context-figure-image")) {
            return false;
        }
        if (attrs.containsKey("data-ole-kind")) {
            return false;
        }
        String trimCandidate = Objects.toString(attrs.get("data-trim-candidate"), "").toLowerCase(Locale.ROOT);
        String trimApplied = Objects.toString(attrs.get("data-trim-applied"), "").toLowerCase(Locale.ROOT);
        if (!"false".equals(trimCandidate) || !"false".equals(trimApplied)) {
            return false;
        }
        String src = Objects.toString(attrs.get("src"), "").trim();
        if (src.isEmpty()) {
            return false;
        }
        String srcLower = src.toLowerCase(Locale.ROOT);
        if (!(srcLower.endsWith(".png")
                || srcLower.endsWith(".jpg")
                || srcLower.endsWith(".jpeg")
                || srcLower.endsWith(".gif")
                || srcLower.endsWith(".webp")
                || srcLower.endsWith(".bmp")
                || srcLower.endsWith(".tiff"))) {
            return false;
        }
        Boolean cached = suppressibilityBySource.get(src);
        if (cached != null) {
            return cached;
        }
        Path imagePath = resolveAssetPath(assetDir, src);
        boolean suppressible = isSuppressibleBlankOrInvisibleRasterImage(imagePath);
        suppressibilityBySource.put(src, suppressible);
        return suppressible;
    }

    private static boolean isSuppressibleBlankOrInvisibleRasterImage(Path imagePath) {
        if (imagePath == null || !Files.exists(imagePath)) {
            return false;
        }
        try (InputStream in = Files.newInputStream(imagePath)) {
            BufferedImage image = ImageIO.read(in);
            if (image == null) {
                return false;
            }
            int width = image.getWidth();
            int height = image.getHeight();
            if (width <= 0 || height <= 0) {
                return true;
            }

            int stepX = Math.max(1, width / 300);
            int stepY = Math.max(1, height / 300);
            long samples = 0L;
            long brightSamples = 0L;
            long meaningfulSamples = 0L;
            double sum = 0.0d;
            double sumSq = 0.0d;
            for (int y = 0; y < height; y += stepY) {
                for (int x = 0; x < width; x += stepX) {
                    int argb = image.getRGB(x, y);
                    int alpha = (argb >>> 24) & 0xff;
                    if (alpha < 10) {
                        continue;
                    }
                    int red = (argb >>> 16) & 0xff;
                    int green = (argb >>> 8) & 0xff;
                    int blue = argb & 0xff;
                    double luminance = (0.2126d * red + 0.7152d * green + 0.0722d * blue) / 255.0d;
                    samples++;
                    sum += luminance;
                    sumSq += luminance * luminance;
                    if (luminance >= 0.99d) {
                        brightSamples++;
                    }
                    if (isMeaningfulRasterContentPixel(argb)) {
                        meaningfulSamples++;
                    }
                }
            }
            if (samples == 0L) {
                return true;
            }
            double mean = sum / samples;
            double variance = Math.max(0.0d, (sumSq / samples) - (mean * mean));
            double stddev = Math.sqrt(variance);
            double brightRatio = (double) brightSamples / (double) samples;
            double meaningfulRatio = (double) meaningfulSamples / (double) samples;

            boolean blank = (brightRatio >= 0.999d && stddev <= 0.001d) || mean >= 0.9995d;
            if (blank) {
                return true;
            }
            boolean nearWhite = mean >= 0.985d && stddev <= 0.03d && brightRatio >= 0.97d;
            boolean visuallySparse = meaningfulRatio <= 0.003d;
            return nearWhite && visuallySparse;
        } catch (IOException ignored) {
            return false;
        }
    }

    private String suppressNonessentialStandaloneContextImageParagraphs(String bodyHtml) {
        if (bodyHtml == null || bodyHtml.isBlank()) {
            return bodyHtml;
        }
        Matcher matcher = STANDALONE_INLINE_IMAGE_PARAGRAPH_PATTERN.matcher(bodyHtml);
        Map<String, Integer> candidateCountBySource = new HashMap<>();
        Map<String, Boolean> hasFigureReferenceBySource = new HashMap<>();
        Map<String, Boolean> hasContextSignalBySource = new HashMap<>();
        Map<String, Boolean> hasProtectedContextSignalBySource = new HashMap<>();
        while (matcher.find()) {
            String imageTag = Objects.toString(matcher.group("img"), "");
            String source = extractNonessentialStandaloneContextCandidateSource(imageTag);
            if (source == null) {
                continue;
            }
            candidateCountBySource.merge(source, 1, Integer::sum);
            boolean hasFigureReference = hasFigureReferenceAroundStandaloneImage(bodyHtml, matcher.start(), matcher.end());
            boolean hasContextSignal = hasContextScenarioAroundStandaloneImage(bodyHtml, matcher.start(), matcher.end());
            boolean hasProtectedContextSignal = hasProtectedContextSignalAroundStandaloneImage(bodyHtml, matcher.start(), matcher.end());
            hasFigureReferenceBySource.put(source, hasFigureReferenceBySource.getOrDefault(source, false) || hasFigureReference);
            hasContextSignalBySource.put(source, hasContextSignalBySource.getOrDefault(source, false) || hasContextSignal);
            hasProtectedContextSignalBySource.put(source, hasProtectedContextSignalBySource.getOrDefault(source, false) || hasProtectedContextSignal);
        }
        if (candidateCountBySource.isEmpty()) {
            return bodyHtml;
        }

        Set<String> suppressibleSources = new HashSet<>();
        int restoredCount = 0;
        for (Map.Entry<String, Integer> entry : candidateCountBySource.entrySet()) {
            String source = entry.getKey();
            int count = entry.getValue();
            boolean hasFigureReference = hasFigureReferenceBySource.getOrDefault(source, false);
            boolean hasContextSignal = hasContextSignalBySource.getOrDefault(source, false);
            boolean hasProtectedContextSignal = hasProtectedContextSignalBySource.getOrDefault(source, false);
            if (count >= 2 && hasContextSignal && !hasFigureReference && !hasProtectedContextSignal) {
                suppressibleSources.add(source);
            } else if (count >= 2 && hasContextSignal && !hasFigureReference && hasProtectedContextSignal) {
                restoredCount += count;
            }
        }
        if (restoredCount > 0) {
            restoredContextImageCounter.addAndGet(restoredCount);
        }
        if (suppressibleSources.isEmpty()) {
            return bodyHtml;
        }

        matcher = STANDALONE_INLINE_IMAGE_PARAGRAPH_PATTERN.matcher(bodyHtml);
        StringBuffer out = null;
        int suppressedCount = 0;
        while (matcher.find()) {
            String imageTag = Objects.toString(matcher.group("img"), "");
            String source = extractNonessentialStandaloneContextCandidateSource(imageTag);
            if (source == null || !suppressibleSources.contains(source)) {
                continue;
            }
            if (out == null) {
                out = new StringBuffer(bodyHtml.length() + 64);
            }
            matcher.appendReplacement(out, "");
            suppressedCount++;
        }
        if (out == null || suppressedCount == 0) {
            return bodyHtml;
        }
        matcher.appendTail(out);
        suppressedNonessentialStandaloneImageCounter.addAndGet(suppressedCount);
        return out.toString();
    }

    private static String extractNonessentialStandaloneContextCandidateSource(String imageTag) {
        if (imageTag == null || imageTag.isBlank()) {
            return null;
        }
        Map<String, String> attrs = parseTagAttributes(imageTag);
        String cssClass = Objects.toString(attrs.get("class"), "").toLowerCase(Locale.ROOT);
        if (!cssClass.contains("inline-image")) {
            return null;
        }
        if (cssClass.contains("essay-figure-image")
                || cssClass.contains("essential-figure-image")
                || cssClass.contains("context-figure-image")) {
            return null;
        }
        if (cssClass.contains("equation")
                || cssClass.contains("diagram")
                || cssClass.contains("chart")
                || cssClass.contains("chemical-diagram")
                || cssClass.contains("chem-diagram")) {
            return null;
        }
        if (attrs.containsKey("data-ole-kind")
                || attrs.containsKey("data-ole-progid")
                || attrs.containsKey("data-fallback-type")) {
            return null;
        }
        String renderRole = Objects.toString(attrs.get("data-render-role"), "").toLowerCase(Locale.ROOT);
        if (renderRole.contains("equation")
                || renderRole.contains("diagram")
                || renderRole.contains("chart")
                || renderRole.contains("chemical")) {
            return null;
        }
        String renderOutputType = Objects.toString(attrs.get("data-render-output-type"), "").toLowerCase(Locale.ROOT);
        if (renderOutputType.contains("equation")
                || renderOutputType.contains("diagram")
                || "chart".equals(renderOutputType)
                || "chemical-diagram".equals(renderOutputType)) {
            return null;
        }
        String alt = Objects.toString(attrs.get("alt"), "").toLowerCase(Locale.ROOT);
        if (alt.contains("equation")
                || alt.contains("diagram")
                || alt.contains("graph")
                || alt.contains("đồ thị")) {
            return null;
        }
        String trimCandidate = Objects.toString(attrs.get("data-trim-candidate"), "").toLowerCase(Locale.ROOT);
        String trimApplied = Objects.toString(attrs.get("data-trim-applied"), "").toLowerCase(Locale.ROOT);
        if (!"false".equals(trimCandidate) || !"false".equals(trimApplied)) {
            return null;
        }
        String source = Objects.toString(attrs.get("src"), "").trim();
        if (source.isEmpty()) {
            return null;
        }
        String sourceLower = source.toLowerCase(Locale.ROOT);
        if (!(sourceLower.endsWith(".png")
                || sourceLower.endsWith(".jpg")
                || sourceLower.endsWith(".jpeg")
                || sourceLower.endsWith(".gif")
                || sourceLower.endsWith(".webp")
                || sourceLower.endsWith(".bmp")
                || sourceLower.endsWith(".tif")
                || sourceLower.endsWith(".tiff"))) {
            return null;
        }
        return source;
    }

    private static boolean hasFigureReferenceAroundStandaloneImage(String bodyHtml, int paragraphStart, int paragraphEnd) {
        return hasPatternInAdjacentParagraphText(bodyHtml, paragraphStart, paragraphEnd, ESSAY_ESSENTIAL_FIGURE_SIGNAL_PATTERN);
    }

    private static boolean hasContextScenarioAroundStandaloneImage(String bodyHtml, int paragraphStart, int paragraphEnd) {
        return hasPatternInAdjacentParagraphText(bodyHtml, paragraphStart, paragraphEnd, ESSAY_CONTEXT_FIGURE_SIGNAL_PATTERN)
                || hasPatternInAdjacentParagraphText(bodyHtml, paragraphStart, paragraphEnd, NONESSENTIAL_STANDALONE_CONTEXT_SIGNAL_PATTERN);
    }

    private static boolean hasProtectedContextSignalAroundStandaloneImage(String bodyHtml, int paragraphStart, int paragraphEnd) {
        return hasPatternInAdjacentParagraphText(bodyHtml, paragraphStart, paragraphEnd, NONESSENTIAL_STANDALONE_KEEP_CONTEXT_SIGNAL_PATTERN);
    }

    private static boolean hasPatternInAdjacentParagraphText(String bodyHtml, int paragraphStart, int paragraphEnd, Pattern pattern) {
        if (bodyHtml == null || bodyHtml.isBlank() || pattern == null) {
            return false;
        }
        String previousParagraphText = extractAdjacentParagraphText(bodyHtml, paragraphStart, false);
        if (!previousParagraphText.isBlank() && pattern.matcher(previousParagraphText).find()) {
            return true;
        }
        String nextParagraphText = extractAdjacentParagraphText(bodyHtml, paragraphEnd, true);
        return !nextParagraphText.isBlank() && pattern.matcher(nextParagraphText).find();
    }

    private static String extractAdjacentParagraphText(String bodyHtml, int anchor, boolean forward) {
        if (bodyHtml == null || bodyHtml.isBlank()) {
            return "";
        }
        if (forward) {
            int paragraphOpen = bodyHtml.indexOf("<p", Math.max(0, anchor));
            if (paragraphOpen < 0) {
                return "";
            }
            int openEnd = bodyHtml.indexOf('>', paragraphOpen);
            if (openEnd < 0) {
                return "";
            }
            int close = bodyHtml.indexOf("</p>", openEnd);
            if (close < 0) {
                return "";
            }
            String paragraphHtml = bodyHtml.substring(openEnd + 1, close);
            String withoutImages = INLINE_IMAGE_TAG_PATTERN.matcher(paragraphHtml).replaceAll(" ");
            return stripHtmlToPlainText(withoutImages);
        }
        int searchAnchor = Math.max(0, anchor - 1);
        int close = bodyHtml.lastIndexOf("</p>", searchAnchor);
        if (close < 0) {
            return "";
        }
        int paragraphOpen = bodyHtml.lastIndexOf("<p", close);
        if (paragraphOpen < 0) {
            return "";
        }
        int openEnd = bodyHtml.indexOf('>', paragraphOpen);
        if (openEnd < 0 || openEnd >= close) {
            return "";
        }
        String paragraphHtml = bodyHtml.substring(openEnd + 1, close);
        String withoutImages = INLINE_IMAGE_TAG_PATTERN.matcher(paragraphHtml).replaceAll(" ");
        return stripHtmlToPlainText(withoutImages);
    }

    private static String stripEmptyParagraphChains(String html, Pattern pattern, Function<Matcher, String> replacementBuilder) {
        Matcher matcher = pattern.matcher(Objects.toString(html, ""));
        StringBuffer out = null;
        while (matcher.find()) {
            if (out == null) {
                out = new StringBuffer(html.length() + 64);
            }
            String replacement = replacementBuilder.apply(matcher);
            matcher.appendReplacement(out, Matcher.quoteReplacement(Objects.toString(replacement, "")));
        }
        if (out == null) {
            return html;
        }
        matcher.appendTail(out);
        return out.toString();
    }

    private static String normalizeMalformedMathBlockFlow(String html) {
        Matcher matcher = MATH_BLOCK_CAPTURE_PATTERN.matcher(Objects.toString(html, ""));
        StringBuffer out = null;
        while (matcher.find()) {
            String blockContent = Objects.toString(matcher.group("content"), "");
            if (!looksLikeMalformedMathBlockFlow(blockContent)) {
                continue;
            }
            String classSuffix = Objects.toString(matcher.group("classes"), "");
            String repaired = rebuildMalformedMathBlock(blockContent, classSuffix);
            if (repaired == null || repaired.isBlank()) {
                continue;
            }
            if (out == null) {
                out = new StringBuffer(html.length() + 96);
            }
            matcher.appendReplacement(out, Matcher.quoteReplacement(repaired));
        }
        if (out == null) {
            return html;
        }
        matcher.appendTail(out);
        return out.toString();
    }

    private static int countMalformedMathBlockFlowIssues(String html) {
        Matcher matcher = MATH_BLOCK_CAPTURE_PATTERN.matcher(Objects.toString(html, ""));
        int count = 0;
        while (matcher.find()) {
            String blockContent = Objects.toString(matcher.group("content"), "");
            if (looksLikeMalformedMathBlockFlow(blockContent)) {
                count++;
            }
        }
        return count;
    }

    private static boolean looksLikeMalformedMathBlockFlow(String blockContent) {
        if (blockContent == null || blockContent.isBlank()) {
            return false;
        }
        if (!blockContent.contains("<math")) {
            return false;
        }
        return blockContent.contains("</span>") || blockContent.contains("<span class=\"math-inline");
    }

    private static String rebuildMalformedMathBlock(String blockContent, String classSuffix) {
        Matcher mathMatcher = MATH_TAG_PATTERN.matcher(blockContent);
        List<String> mathFragments = new ArrayList<>();
        while (mathMatcher.find()) {
            mathFragments.add(mathMatcher.group());
        }
        if (mathFragments.isEmpty()) {
            return null;
        }
        String firstMathBlock = enforceMathDisplay(mathFragments.get(0), true);
        if (mathFragments.size() == 1 || areEquivalentMathFragments(mathFragments)) {
            return "<div class=\"math-block" + classSuffix + "\">" + firstMathBlock + "</div>";
        }

        StringBuilder paragraph = new StringBuilder(blockContent.length() + 96);
        int lastEnd = 0;
        mathMatcher = MATH_TAG_PATTERN.matcher(blockContent);
        while (mathMatcher.find()) {
            String separator = normalizeMathFlowSeparator(blockContent.substring(lastEnd, mathMatcher.start()));
            if (!separator.isBlank()) {
                paragraph.append(HtmlUtil.escape(separator));
            }
            paragraph.append("<span class=\"math-inline mathml\">")
                    .append(enforceMathDisplay(mathMatcher.group(), false))
                    .append("</span>");
            lastEnd = mathMatcher.end();
        }
        String trailing = normalizeMathFlowSeparator(blockContent.substring(lastEnd));
        if (!trailing.isBlank()) {
            paragraph.append(HtmlUtil.escape(trailing));
        }
        String normalized = normalizeInlineSpacing(paragraph.toString()).trim();
        if (normalized.isBlank()) {
            return "<div class=\"math-block" + classSuffix + "\">" + firstMathBlock + "</div>";
        }
        return "<p>" + normalized + "</p>";
    }

    private static boolean areEquivalentMathFragments(List<String> mathFragments) {
        if (mathFragments == null || mathFragments.size() <= 1) {
            return true;
        }
        String first = normalizeMathFragmentForComparison(mathFragments.get(0));
        for (int i = 1; i < mathFragments.size(); i++) {
            if (!first.equals(normalizeMathFragmentForComparison(mathFragments.get(i)))) {
                return false;
            }
        }
        return true;
    }

    private static String normalizeMathFragmentForComparison(String mathFragment) {
        String normalized = enforceMathDisplay(Objects.toString(mathFragment, ""), false);
        return normalized.replaceAll("\\s+", "");
    }

    private static String normalizeMathFlowSeparator(String rawSeparator) {
        String plain = stripHtmlToPlainText(rawSeparator);
        if (plain == null || plain.isBlank()) {
            return "";
        }
        plain = plain.replaceAll("\\s+", " ").trim();
        if (plain.isBlank()) {
            return "";
        }
        plain = plain.replaceAll("\\s*([,;:])\\s*", "$1 ");
        plain = plain.replaceAll("\\s+", " ").trim();
        return plain.isBlank() ? "" : plain + " ";
    }

    private static int countEmptyParagraphsInNamedGroup(String html, Pattern containerPattern) {
        Matcher matcher = containerPattern.matcher(Objects.toString(html, ""));
        int count = 0;
        while (matcher.find()) {
            String empties = Objects.toString(matcher.group("empties"), "");
            count += countPatternMatches(EMPTY_PARAGRAPH_TAG_PATTERN, empties);
        }
        return count;
    }

    private static int countPatternMatches(Pattern pattern, String input) {
        Matcher matcher = pattern.matcher(Objects.toString(input, ""));
        int count = 0;
        while (matcher.find()) {
            count++;
        }
        return count;
    }

    private static String relocateLeadingImageParagraphBeforeEssayQuestion(String bodyHtml) {
        Matcher matcher = IMAGE_ONLY_PARAGRAPH_BEFORE_QUESTION_PATTERN.matcher(bodyHtml);
        StringBuffer out = null;
        while (matcher.find()) {
            String imageTag = Objects.toString(matcher.group("img"), "").trim();
            String textHtml = Objects.toString(matcher.group("text"), "").trim();
            if (imageTag.isBlank() || textHtml.isBlank() || imageTag.contains("essay-figure-image")) {
                continue;
            }
            if (!extractInlineImageTags(textHtml).isEmpty()) {
                continue;
            }
            String plainText = stripHtmlToPlainText(textHtml);
            FigureRole role = classifyEssayFigureRole(plainText, imageTag);
            if (!isEligibleEssayFigurePlacementText(plainText, role)) {
                continue;
            }
            if (out == null) {
                out = new StringBuffer(bodyHtml.length() + 128);
            }
            String replacement;
            if (role == FigureRole.CONTEXT) {
                replacement = buildEssayContextLayout("<p>" + textHtml + "</p>", imageTag);
            } else {
                replacement = "<p>" + textHtml + "</p>\n" + buildEssayFigureBlock(imageTag, FigureRole.ESSENTIAL);
            }
            matcher.appendReplacement(out, Matcher.quoteReplacement(replacement));
        }
        if (out == null) {
            return bodyHtml;
        }
        matcher.appendTail(out);
        return out.toString();
    }

    private static String wrapConsecutiveEssentialFigures(String bodyHtml) {
        Matcher matcher = CONSECUTIVE_ESSENTIAL_FIGURES_AFTER_STEM_PATTERN.matcher(bodyHtml);
        StringBuffer out = null;
        while (matcher.find()) {
            String stem = Objects.toString(matcher.group("stem"), "");
            String figures = Objects.toString(matcher.group("figs"), "");
            if (figures.isBlank()) {
                continue;
            }
            if (out == null) {
                out = new StringBuffer(bodyHtml.length() + 96);
            }
            String wrapped = stem
                    + "<div class=\"essential-figure-group question-essential-figure-group\" data-figure-role=\"essential-figure-group\">"
                    + figures.trim()
                    + "</div>\n";
            matcher.appendReplacement(out, Matcher.quoteReplacement(wrapped));
        }
        if (out == null) {
            return bodyHtml;
        }
        matcher.appendTail(out);
        return out.toString();
    }

    private static List<String> extractInlineImageTags(String html) {
        List<String> images = new ArrayList<>();
        Matcher matcher = INLINE_IMAGE_TAG_PATTERN.matcher(Objects.toString(html, ""));
        while (matcher.find()) {
            images.add(matcher.group());
        }
        return images;
    }

    private static List<String> extractTableFigureImageTags(String html) {
        List<String> images = new ArrayList<>();
        Matcher matcher = TABLE_FIGURE_IMAGE_TAG_PATTERN.matcher(Objects.toString(html, ""));
        while (matcher.find()) {
            images.add(matcher.group());
        }
        return images;
    }

    private static FigureRole classifyEssayFigureRole(String plainText, String imageTag) {
        String normalizedText = Objects.toString(plainText, "");
        String imageLower = Objects.toString(imageTag, "").toLowerCase(Locale.ROOT);
        boolean likelyContextRaster = imageLower.contains("data-trim-candidate=\"false\"")
                && imageLower.contains("data-trim-applied=\"false\"")
                && (imageLower.contains("data-source-ext=\".jpg\"")
                || imageLower.contains("data-source-ext=\".jpeg\"")
                || imageLower.contains("data-source-ext=\".png\""));
        if (likelyContextRaster && ESSAY_CONTEXT_FIGURE_SIGNAL_PATTERN.matcher(normalizedText).find()) {
            return FigureRole.CONTEXT;
        }
        if (ESSAY_ESSENTIAL_FIGURE_SIGNAL_PATTERN.matcher(normalizedText).find()) {
            return FigureRole.ESSENTIAL;
        }
        return FigureRole.ESSENTIAL;
    }

    private static boolean isEligibleEssayFigurePlacementText(String plainText, FigureRole role) {
        if (role == FigureRole.CONTEXT) {
            return looksLikeContextQuestionText(plainText);
        }
        return looksLikeEssayQuestionText(plainText);
    }

    private static boolean isEligibleFigureTablePlacementText(String plainText, FigureRole role, Subject subject) {
        if (role == FigureRole.CONTEXT) {
            return looksLikeContextQuestionText(plainText);
        }
        if (subject == Subject.MATH) {
            return looksLikeEssayQuestionText(plainText);
        }
        return looksLikeEssentialProblemFigureText(plainText)
                || looksLikeQuestionFigureTableText(plainText);
    }

    private static String buildEssayContextLayout(String questionHtml, String imageTag) {
        String normalizedQuestion = Objects.toString(questionHtml, "").trim();
        String normalizedImageTag = Objects.toString(imageTag, "");
        StringBuilder out = new StringBuilder(normalizedQuestion.length() + normalizedImageTag.length() + 160);
        out.append("<table class=\"question-context-table essay-context-layout question-context-layout\" data-figure-role=\"context-figure\">")
                .append("<tr>")
                .append("<td class=\"question-context-text-cell essay-context-text\">")
                .append(normalizedQuestion)
                .append("</td>")
                .append("<td class=\"question-context-figure-cell essay-context-aside\">")
                .append(buildEssayFigureBlock(normalizedImageTag, FigureRole.CONTEXT))
                .append("</td>")
                .append("</tr>")
                .append("</table>");
        return out.toString();
    }

    private static String buildEssayFigureBlock(String imageTag, FigureRole role) {
        String styledImageTag = ensureImageTagClass(imageTag, "essay-figure-image");
        if (role == FigureRole.CONTEXT) {
            styledImageTag = ensureImageTagClass(styledImageTag, "context-figure-image");
            return "<figure class=\"context-figure question-context-figure\" data-figure-role=\"context-figure\">"
                    + styledImageTag
                    + "</figure>";
        }
        styledImageTag = ensureImageTagClass(styledImageTag, "essential-figure-image");
        return "<figure class=\"essay-figure question-figure essential-figure\" data-figure-role=\"essential-figure\">"
                + styledImageTag
                + "</figure>";
    }

    private static String ensureImageTagClass(String imageTag, String requiredClass) {
        if (imageTag == null || imageTag.isBlank() || requiredClass == null || requiredClass.isBlank()) {
            return Objects.toString(imageTag, "");
        }
        Matcher classMatcher = IMG_CLASS_ATTR_PATTERN.matcher(imageTag);
        if (!classMatcher.find()) {
            int close = imageTag.lastIndexOf("/>");
            if (close < 0) {
                close = imageTag.lastIndexOf('>');
            }
            if (close <= 0) {
                return imageTag;
            }
            return imageTag.substring(0, close) + " class=\"" + HtmlUtil.escapeAttribute(requiredClass) + "\"" + imageTag.substring(close);
        }
        String currentClasses = Objects.toString(classMatcher.group(1), "");
        List<String> classTokens = new ArrayList<>();
        for (String token : currentClasses.trim().split("\\s+")) {
            if (!token.isBlank()) {
                classTokens.add(token);
            }
        }
        if (!classTokens.contains(requiredClass)) {
            classTokens.add(requiredClass);
        }
        String updatedClass = String.join(" ", classTokens);
        return classMatcher.replaceFirst(Matcher.quoteReplacement("class=\"" + HtmlUtil.escapeAttribute(updatedClass) + "\""));
    }

    private static String stripHtmlToPlainText(String html) {
        if (html == null || html.isBlank()) {
            return "";
        }
        String plain = HTML_TAG_PATTERN.matcher(html).replaceAll(" ");
        plain = plain.replace("&nbsp;", " ")
                .replace("&#160;", " ")
                .replace("&emsp;", " ")
                .replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&quot;", "\"")
                .replace("&#39;", "'");
        return plain.replaceAll("\\s+", " ").trim();
    }

    private static boolean looksLikeEssayQuestionText(String plainText) {
        if (plainText == null || plainText.isBlank()) {
            return false;
        }
        String normalized = plainText.replaceAll("\\s+", " ").trim();
        if (normalized.length() < 160) {
            return false;
        }
        if (!QUESTION_STEM_PATTERN.matcher(normalized).find()) {
            return false;
        }
        if (!ESSAY_ASK_SIGNAL_PATTERN.matcher(normalized).find()) {
            return false;
        }
        return countMultiChoiceOptionMarkers(normalized) < 2;
    }

    private static boolean looksLikeContextQuestionText(String plainText) {
        if (plainText == null || plainText.isBlank()) {
            return false;
        }
        String normalized = plainText.replaceAll("\\s+", " ").trim();
        if (normalized.length() < 120) {
            return false;
        }
        if (!QUESTION_STEM_PATTERN.matcher(normalized).find()) {
            return false;
        }
        return ESSAY_CONTEXT_FIGURE_SIGNAL_PATTERN.matcher(normalized).find();
    }

    private static boolean looksLikeEssentialProblemFigureText(String plainText) {
        if (plainText == null || plainText.isBlank()) {
            return false;
        }
        String normalized = plainText.replaceAll("\\s+", " ").trim();
        if (normalized.length() < 110) {
            return false;
        }
        if (!QUESTION_STEM_PATTERN.matcher(normalized).find()) {
            return false;
        }
        return ESSAY_ESSENTIAL_FIGURE_SIGNAL_PATTERN.matcher(normalized).find();
    }

    private static boolean looksLikeQuestionFigureTableText(String plainText) {
        if (plainText == null || plainText.isBlank()) {
            return false;
        }
        String normalized = plainText.replaceAll("\\s+", " ").trim();
        if (normalized.length() < 80) {
            return false;
        }
        if (!QUESTION_STEM_PATTERN.matcher(normalized).find()) {
            return false;
        }
        if (ESSAY_ASK_SIGNAL_PATTERN.matcher(normalized).find()) {
            return true;
        }
        return countMultiChoiceOptionMarkers(normalized) >= 2;
    }

    private static int countMultiChoiceOptionMarkers(String text) {
        Matcher optionMatcher = MULTI_CHOICE_OPTION_MARKER_PATTERN.matcher(Objects.toString(text, ""));
        int optionCount = 0;
        while (optionMatcher.find()) {
            optionCount++;
        }
        return optionCount;
    }

    private String renderNodes(NodeList nodes, XWPFDocument doc, Path assetDir, boolean preserveWhitespace) throws Exception {
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < nodes.getLength(); i++) {
            Node node = nodes.item(i);
            if (node.getNodeType() == Node.TEXT_NODE) {
                String text = normalizeTextContent(node.getNodeValue());
                if (text != null && (preserveWhitespace || !text.isBlank())) {
                    out.append(HtmlUtil.escape(text));
                }
                continue;
            }
            if (node.getNodeType() != Node.ELEMENT_NODE) {
                continue;
            }

            Element el = (Element) node;
            String local = el.getLocalName();
            if (local == null) {
                continue;
            }

            switch (local) {
                case "r" -> out.append(renderRun(el, doc, assetDir));
                case "oMath" -> out.append(renderOmml(el, false));
                case "oMathPara" -> out.append(renderOmmlParagraph(el));
                case "object" -> out.append(renderOleObject(el, doc, assetDir));
                default -> {
                    if (INLINE_CONTAINER_NAMES.contains(local)) {
                        out.append(renderNodes(el.getChildNodes(), doc, assetDir, preserveWhitespace));
                    }
                }
            }
        }
        return out.toString();
    }

    private String renderRun(Element run, XWPFDocument doc, Path assetDir) throws Exception {
        StringBuilder out = new StringBuilder();
        String verticalAlign = resolveRunVerticalAlign(run);
        NodeList children = run.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node node = children.item(i);
            if (node.getNodeType() != Node.ELEMENT_NODE) {
                continue;
            }
            Element el = (Element) node;
            String local = el.getLocalName();
            if (local == null) {
                continue;
            }
            switch (local) {
                case "t", "delText" -> out.append(HtmlUtil.escape(normalizeTextContent(el.getTextContent())));
                case "instrText" -> {
                    // Word field codes (for example INCLUDEPICTURE / MERGEFORMATINET) are metadata, not visible content.
                }
                case "tab" -> out.append("&emsp;");
                case "br", "cr" -> out.append("<br/>");
                case "noBreakHyphen" -> out.append("&#8209;");
                case "softHyphen" -> out.append("&shy;");
                case "sym" -> out.append(renderSymbol(el));
                case "drawing", "pict" -> out.append(renderImageLikeNode(el, doc, assetDir));
                case "object" -> out.append(renderOleObject(el, doc, assetDir));
                default -> out.append(renderNodes(el.getChildNodes(), doc, assetDir, true));
            }
        }
        String rendered = out.toString();
        if (rendered.isEmpty()) {
            return rendered;
        }
        if ("subscript".equals(verticalAlign)) {
            return "<sub>" + rendered + "</sub>";
        }
        if ("superscript".equals(verticalAlign)) {
            return "<sup>" + rendered + "</sup>";
        }
        return rendered;
    }

    private String renderSymbol(Element el) {
        String hex = attrByLocalName(el, "char");
        if (hex == null || hex.isBlank()) {
            return "";
        }
        hex = hex.replace("0x", "").replace("0X", "");
        try {
            int codePoint = Integer.parseInt(hex, 16);
            String font = normalizeWordSymbolFontName(attrByLocalName(el, "font"));
            String mapped = mapCoreWordSymbol(font, codePoint);
            if (mapped == null && subject == Subject.MATH) {
                mapped = mapMathWordSymbol(font, codePoint);
            }
            if (mapped != null) {
                if (subject == Subject.MATH) {
                    mathGlyphCleanupCounter.incrementAndGet();
                }
                return HtmlUtil.escape(mapped);
            }
            return HtmlUtil.escape(new String(Character.toChars(codePoint)));
        } catch (Exception ex) {
            return "";
        }
    }

    private static String normalizeWordSymbolFontName(String font) {
        if (font == null || font.isBlank()) {
            return "";
        }
        return font.trim().toLowerCase(Locale.ROOT).replaceAll("\\s+", " ");
    }

    private static String mapCoreWordSymbol(String normalizedFont, int codePoint) {
        int lowByte = codePoint & 0xFF;
        if ("symbol".equals(normalizedFont)) {
            return CORE_SYMBOL_FONT_LOW_BYTE_MAP.get(lowByte);
        }
        if ("wingdings".equals(normalizedFont)) {
            return CORE_WINGDINGS_FONT_LOW_BYTE_MAP.get(lowByte);
        }
        return null;
    }

    private static String mapMathWordSymbol(String normalizedFont, int codePoint) {
        if (!"wingdings 2".equals(normalizedFont) && !"wingdings2".equals(normalizedFont)) {
            return null;
        }
        return MATH_WINGDINGS2_FONT_LOW_BYTE_MAP.get(codePoint & 0xFF);
    }

    private static String resolveRunVerticalAlign(Element run) {
        Element runProps = findDirectChild(run, "rPr");
        if (runProps == null) {
            return "";
        }
        Element vertAlign = findDirectChild(runProps, "vertAlign");
        if (vertAlign == null) {
            return "";
        }
        return Objects.toString(attrByLocalName(vertAlign, "val"), "").toLowerCase(Locale.ROOT);
    }

    private String renderOmmlParagraph(Element ommlPara) throws Exception {
        StringBuilder out = new StringBuilder();
        NodeList children = ommlPara.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node node = children.item(i);
            if (node.getNodeType() == Node.ELEMENT_NODE && "oMath".equals(((Element) node).getLocalName())) {
                out.append(renderOmml((Element) node, true));
            }
        }
        return out.toString();
    }

    private String renderOmml(Element omml, boolean display) throws Exception {
        long start = System.nanoTime();
        try {
            String mathml = normalizeMathmlFragment(ommlTransformer.transformOmmlToMathml(serializeNode(omml)));
            ommlCounter.incrementAndGet();
            return wrapMathml(mathml, display, "omml");
        } finally {
            stageOmmlHandlingNanos.addAndGet(System.nanoTime() - start);
        }
    }

    private String renderOleObject(Element objectEl, XWPFDocument doc, Path assetDir) throws Exception {
        long start = System.nanoTime();
        try {
            Element oleObject = findDescendant(objectEl, "OLEObject");
            String progId = oleObject != null ? attrByLocalName(oleObject, "ProgID") : null;
            if (progId == null || progId.isBlank()) {
                progId = oleObject != null ? attrByLocalName(oleObject, "progId") : null;
            }
            OleKind oleKind = classifyOleKind(progId);

            String oleRelId = oleObject != null ? attrByLocalName(oleObject, "id") : null;
            Element imageData = findDescendant(objectEl, "imagedata");
            String imageRelId = imageData != null ? attrByLocalName(imageData, "id") : null;
            if (oleKind == OleKind.DSMT4_EQUATION) {
                return renderDsmt4Object(doc, progId, oleRelId, imageRelId);
            }
            boolean shouldTryMathSidecar = oleKind == OleKind.EQUATION || progId == null || progId.isBlank();
            boolean attemptedOleSourceRender = false;
            boolean attemptedPreviewRender = false;
            String oleSourceExt = guessRelatedExtension(doc, oleRelId);
            String previewSourceExt = guessRelatedExtension(doc, imageRelId);
            String oleSourceAsset = "";
            String previewSourceAsset = "";

            try {
                if (shouldTryMathSidecar) {
                    String sidecarFromOle = renderSidecarMathml(doc, oleRelId, false);
                    if (sidecarFromOle != null) {
                        return sidecarFromOle;
                    }
                    String sidecarFromPreview = renderSidecarMathml(doc, imageRelId, false);
                    if (sidecarFromPreview != null) {
                        return sidecarFromPreview;
                    }
                }

                if (oleKind == OleKind.CHEMICAL_DIAGRAM && oleRelId != null && !oleRelId.isBlank()) {
                    attemptedOleSourceRender = true;
                    SavedBinary sourceSaved = saveRelatedBinary(doc, oleRelId, assetDir, "chem-diagram-source", true, oleKind);
                    if (sourceSaved != null) {
                        oleSourceAsset = sourceSaved.relativePath();
                    }
                    if (sourceSaved != null && isWebRenderableImage(sourceSaved.relativePath())) {
                        return buildOleFallbackImageHtml(sourceSaved, oleKind, progId, "ole-source");
                    }
                }

                // Last-resort fallback: use preview relation if source rendering is unavailable.
                if (imageRelId != null && !imageRelId.isBlank()) {
                    attemptedPreviewRender = true;
            SavedBinary saved = saveRelatedBinary(doc, imageRelId, assetDir, buildOlePrefix(oleKind), true, oleKind);
                    if (saved != null) {
                        previewSourceAsset = saved.relativePath();
                    }
                    if (saved != null && (oleKind != OleKind.CHEMICAL_DIAGRAM || isWebRenderableImage(saved.relativePath()))) {
                        return buildOleFallbackImageHtml(saved, oleKind, progId, "preview-image");
                    }
                }
            } catch (Exception ex) {
                olePlaceholderCounter.incrementAndGet();
                String sourceExtTrace = "ole:" + Objects.toString(oleSourceExt, "") + ",preview:" + Objects.toString(previewSourceExt, "");
                String sourceAssetTrace = "ole:" + Objects.toString(oleSourceAsset, "") + ",preview:" + Objects.toString(previewSourceAsset, "");
                return buildUnsupportedOlePlaceholder(
                        buildOlePlaceholderLabel(oleKind, progId),
                        oleKind,
                        progId,
                        attemptedOleSourceRender || attemptedPreviewRender,
                        "render-exception",
                        sourceExtTrace,
                        sourceAssetTrace,
                        buildUnresolvedPlaceholderFamily(oleKind),
                        "ole-render-exception:" + ex.getClass().getSimpleName(),
                        shouldHideOlePlaceholder(oleKind)
                );
            }

            if (isVisioProgId(progId)) {
                unresolvedVisioPreviewCounter.incrementAndGet();
            }
            olePlaceholderCounter.incrementAndGet();
            String label = buildOlePlaceholderLabel(oleKind, progId);
            String renderSourceUsed = "none";
            if (attemptedOleSourceRender && attemptedPreviewRender) {
                renderSourceUsed = "ole-source,preview-image";
            } else if (attemptedOleSourceRender) {
                renderSourceUsed = "ole-source";
            } else if (attemptedPreviewRender) {
                renderSourceUsed = "preview-image";
            }
            String sourceExtTrace = "ole:" + Objects.toString(oleSourceExt, "") + ",preview:" + Objects.toString(previewSourceExt, "");
            String sourceAssetTrace = "ole:" + Objects.toString(oleSourceAsset, "") + ",preview:" + Objects.toString(previewSourceAsset, "");
            return buildUnsupportedOlePlaceholder(
                    label,
                    oleKind,
                    progId,
                    attemptedOleSourceRender || attemptedPreviewRender,
                    renderSourceUsed,
                    sourceExtTrace,
                    sourceAssetTrace,
                    buildUnresolvedPlaceholderFamily(oleKind),
                    buildUnresolvedPlaceholderReason(
                            oleKind,
                            progId,
                            attemptedOleSourceRender || attemptedPreviewRender,
                            renderSourceUsed,
                            sourceExtTrace,
                            sourceAssetTrace
                    ),
                    shouldHideOlePlaceholder(oleKind)
            );
        } finally {
            stageImageRenderingNanos.addAndGet(System.nanoTime() - start);
        }
    }

    private String buildOleFallbackImageHtml(SavedBinary saved, OleKind oleKind, String progId, String renderSourceUsed) {
        if (isMetafileReference(saved.relativePath())) {
            if (isVisioProgId(progId)) {
                unresolvedVisioPreviewCounter.incrementAndGet();
            }
            olePlaceholderCounter.incrementAndGet();
            String label = buildOlePlaceholderLabel(oleKind, progId) + " (unsupported web image format)";
            String sourceExtTrace = "ole:" + Objects.toString(saved.sourceExtension(), "");
            String sourceAssetTrace = "ole:" + Objects.toString(saved.relativePath(), "");
            return buildUnsupportedOlePlaceholder(
                    label,
                    oleKind,
                    progId,
                    true,
                    renderSourceUsed,
                    sourceExtTrace,
                    sourceAssetTrace,
                    buildUnresolvedPlaceholderFamily(oleKind),
                    buildUnresolvedPlaceholderReason(
                            oleKind,
                            progId,
                            true,
                            renderSourceUsed,
                            sourceExtTrace,
                            sourceAssetTrace
                    ),
                    shouldHideOlePlaceholder(oleKind)
            );
        }
        String cssClass = buildOleCssClass(oleKind);
        String alt = buildOleAltText(oleKind, progId);
        String outputType = inferRenderOutputType(saved.relativePath());
        StringBuilder img = new StringBuilder(256);
        img.append("<img class=\"").append(cssClass)
                .append("\" src=\"").append(HtmlUtil.escapeAttribute(saved.relativePath()))
                .append("\" alt=\"").append(HtmlUtil.escapeAttribute(alt)).append("\"")
                .append(" data-ole-kind=\"").append(HtmlUtil.escapeAttribute(oleKind.dataValue())).append("\"")
                .append(" data-render-attempted=\"true\"")
                .append(" data-render-source-used=\"").append(HtmlUtil.escapeAttribute(renderSourceUsed)).append("\"")
                .append(" data-render-output-type=\"").append(HtmlUtil.escapeAttribute(outputType)).append("\"")
                .append(" data-render-success=\"true\"");
        if (progId != null && !progId.isBlank()) {
            img.append(" data-ole-progid=\"").append(HtmlUtil.escapeAttribute(progId)).append("\"");
        }
        olePreviewCounter.incrementAndGet();
        if (saved.isMetafileSource()) {
            emfWmfPreviewCounter.incrementAndGet();
            img.append(" data-source-ext=\"").append(HtmlUtil.escapeAttribute(saved.sourceExtension())).append("\"");
        }
        if (oleKind == OleKind.EQUATION) {
            oleEquationPreviewCounter.incrementAndGet();
            img.append(" data-fallback-type=\"equation-image\"");
        } else if (oleKind == OleKind.DIAGRAM) {
            oleDiagramPreviewCounter.incrementAndGet();
            img.append(" data-render-role=\"diagram\"");
            img.append(" data-fallback-type=\"diagram-image\"");
        } else if (oleKind == OleKind.CHEMICAL_DIAGRAM) {
            oleDiagramPreviewCounter.incrementAndGet();
            img.append(" data-render-role=\"chemical-diagram\"");
            img.append(" data-fallback-type=\"chemical-diagram-image\"");
            img.append(" data-chem-trim-applied=\"")
                    .append(trimmedChemicalDiagramAssets.contains(saved.relativePath()) ? "true" : "false")
                    .append("\"");
        } else {
            oleIllustrationPreviewCounter.incrementAndGet();
            img.append(" data-render-role=\"illustration\"");
            img.append(" data-fallback-type=\"illustration-image\"");
        }
        img.append("/>");
        return img.toString();
    }

    private String renderDsmt4Object(XWPFDocument doc, String progId, String oleRelId, String imageRelId) throws Exception {
        dsmt4TotalCounter.incrementAndGet();
        Dsmt4Resolution resolution = resolveDsmt4Sidecar(doc, oleRelId, imageRelId);
        if (resolution.html() != null) {
            dsmt4SidecarResolvedCounter.incrementAndGet();
            return resolution.html();
        }

        dsmt4UnresolvedCounter.incrementAndGet();
        if (resolution.status() == Dsmt4ResolutionStatus.MANIFEST_MISSING) {
            dsmt4ManifestMissingCounter.incrementAndGet();
        } else {
            dsmt4ManifestMismatchCounter.incrementAndGet();
        }
        dsmt4FallbackPlaceholderCounter.incrementAndGet();
        olePlaceholderCounter.incrementAndGet();

        String unresolvedReason = resolution.status() == Dsmt4ResolutionStatus.MANIFEST_MISSING
                ? "dsmt4-manifest-missing"
                : "dsmt4-manifest-mismatch";
        if (!resolution.debugDetail().isBlank()) {
            unresolvedReason = unresolvedReason + ":" + resolution.debugDetail();
        }
        return buildUnsupportedOlePlaceholder(
                buildOlePlaceholderLabel(OleKind.DSMT4_EQUATION, progId),
                OleKind.DSMT4_EQUATION,
                progId,
                false,
                "sidecar-first",
                resolution.sourceExtTrace(),
                resolution.sourceAssetTrace(),
                buildUnresolvedPlaceholderFamily(OleKind.DSMT4_EQUATION),
                unresolvedReason,
                shouldHideOlePlaceholder(OleKind.DSMT4_EQUATION)
        );
    }

    private Dsmt4Resolution resolveDsmt4Sidecar(XWPFDocument doc, String oleRelId, String imageRelId) throws Exception {
        String sourceExtTrace = buildDsmt4SourceExtTrace(doc, oleRelId, imageRelId);
        String sourceAssetTrace = buildDsmt4SourceAssetTrace(doc, oleRelId, imageRelId);
        if (sidecarRegistry.isEmpty()) {
            return new Dsmt4Resolution(
                    Dsmt4ResolutionStatus.MANIFEST_MISSING,
                    null,
                    sourceExtTrace,
                    sourceAssetTrace,
                    "registry-empty"
            );
        }

        SidecarProbe oleProbe = probeSidecarMathml(doc, oleRelId, false);
        if (oleProbe.html() != null) {
            return new Dsmt4Resolution(Dsmt4ResolutionStatus.RESOLVED, oleProbe.html(), sourceExtTrace, sourceAssetTrace, "ole-part");
        }
        SidecarProbe previewProbe = probeSidecarMathml(doc, imageRelId, false);
        if (previewProbe.html() != null) {
            return new Dsmt4Resolution(Dsmt4ResolutionStatus.RESOLVED, previewProbe.html(), sourceExtTrace, sourceAssetTrace, "preview-part");
        }
        return new Dsmt4Resolution(
                Dsmt4ResolutionStatus.MANIFEST_MISMATCH,
                null,
                sourceExtTrace,
                sourceAssetTrace,
                "ole=" + oleProbe.debugDetail() + ",preview=" + previewProbe.debugDetail()
        );
    }

    private SidecarProbe probeSidecarMathml(XWPFDocument doc, String relId, boolean block) throws Exception {
        if (relId == null || relId.isBlank()) {
            return new SidecarProbe(null, "missing-rel");
        }
        PackagePart relatedPart = resolveRelatedPart(doc, relId);
        if (relatedPart == null) {
            return new SidecarProbe(null, "missing-part");
        }
        String partName = relatedPart.getPartName().getName();
        if (!sidecarRegistry.hasMathmlForPart(partName)) {
            return new SidecarProbe(null, "no-manifest-entry:" + partName);
        }
        String mathml = sidecarRegistry.readMathmlForPart(partName);
        if (mathml == null || mathml.isBlank()) {
            return new SidecarProbe(null, "empty-sidecar:" + partName);
        }
        mathml = normalizeMathmlFragment(mathml);
        sidecarMathmlCounter.incrementAndGet();
        return new SidecarProbe(wrapMathml(mathml, block, "sidecar"), "resolved:" + partName);
    }

    private String buildDsmt4SourceExtTrace(XWPFDocument doc, String oleRelId, String imageRelId) {
        return "ole:" + Objects.toString(guessRelatedExtension(doc, oleRelId), "")
                + ",preview:" + Objects.toString(guessRelatedExtension(doc, imageRelId), "");
    }

    private String buildDsmt4SourceAssetTrace(XWPFDocument doc, String oleRelId, String imageRelId) {
        return "ole:" + Objects.toString(resolveRelatedPartName(doc, oleRelId), "")
                + ",preview:" + Objects.toString(resolveRelatedPartName(doc, imageRelId), "");
    }

    private String resolveRelatedPartName(XWPFDocument doc, String relId) {
        if (relId == null || relId.isBlank()) {
            return "";
        }
        try {
            PackagePart relatedPart = resolveRelatedPart(doc, relId);
            return relatedPart == null ? "" : relatedPart.getPartName().getName();
        } catch (Exception ignored) {
            return "";
        }
    }

    private static String buildUnsupportedOlePlaceholder(
            String label,
            OleKind oleKind,
            String progId,
            boolean renderAttempted,
            String renderSourceUsed,
            String sourceExtTrace,
            String sourceAssetTrace,
            String placeholderFamily,
            String unresolvedReason,
            boolean qaHidden
    ) {
        StringBuilder span = new StringBuilder(240);
        String visibleLabel = qaHidden ? "" : "[" + HtmlUtil.escape(label) + "]";
        span.append("<span class=\"")
                .append(buildOlePlaceholderClass(oleKind));
        if (qaHidden) {
            span.append(" qa-hidden");
        }
        span.append("\"")
                .append(" title=\"").append(HtmlUtil.escapeAttribute(label)).append("\"")
                .append(" data-ole-kind=\"").append(HtmlUtil.escapeAttribute(oleKind.dataValue())).append("\"")
                .append(" data-placeholder-family=\"").append(HtmlUtil.escapeAttribute(placeholderFamily)).append("\"")
                .append(" data-placeholder-label=\"").append(HtmlUtil.escapeAttribute(label)).append("\"")
                .append(" data-unresolved-reason=\"").append(HtmlUtil.escapeAttribute(unresolvedReason)).append("\"")
                .append(" data-render-attempted=\"").append(renderAttempted ? "true" : "false").append("\"")
                .append(" data-render-source-used=\"").append(HtmlUtil.escapeAttribute(renderSourceUsed)).append("\"")
                .append(" data-render-output-type=\"placeholder\"")
                .append(" data-render-success=\"false\"")
                .append(" data-render-source-exts=\"").append(HtmlUtil.escapeAttribute(sourceExtTrace)).append("\"")
                .append(" data-render-source-assets=\"").append(HtmlUtil.escapeAttribute(sourceAssetTrace)).append("\"");
        if (progId != null && !progId.isBlank()) {
            span.append(" data-ole-progid=\"").append(HtmlUtil.escapeAttribute(progId)).append("\"");
        }
        span.append(">").append(visibleLabel).append("</span>");
        return span.toString();
    }

    private boolean shouldHideOlePlaceholder(OleKind oleKind) {
        return outputMode == OutputMode.PUBLISH
                && (oleKind == OleKind.DSMT4_EQUATION || oleKind == OleKind.EQUATION);
    }

    private static String buildUnsupportedInlineImagePlaceholder(
            String label,
            String sourceExt,
            String sourceAsset,
            String fallbackType
    ) {
        StringBuilder span = new StringBuilder(240);
        String placeholderFamily = isMetafileExtension(sourceExt) ? "inline-metafile" : "inline-image";
        span.append("<span class=\"unsupported-equation qa-hidden")
                .append(isMetafileExtension(sourceExt) ? " unsupported-inline-metafile" : " unsupported-inline-image")
                .append("\"")
                .append(" title=\"").append(HtmlUtil.escapeAttribute(label)).append("\"")
                .append(" data-ole-kind=\"illustration\"")
                .append(" data-placeholder-family=\"").append(HtmlUtil.escapeAttribute(placeholderFamily)).append("\"")
                .append(" data-unresolved-reason=\"").append(HtmlUtil.escapeAttribute(fallbackType)).append("\"")
                .append(" data-render-attempted=\"true\"")
                .append(" data-render-source-used=\"inline-image\"")
                .append(" data-render-output-type=\"placeholder\"")
                .append(" data-render-success=\"false\"")
                .append(" data-fallback-type=\"").append(HtmlUtil.escapeAttribute(fallbackType)).append("\"")
                .append(" data-render-source-exts=\"").append(HtmlUtil.escapeAttribute(sourceExt)).append("\"")
                .append(" data-render-source-assets=\"").append(HtmlUtil.escapeAttribute(sourceAsset)).append("\"")
                .append(">[")
                .append(HtmlUtil.escape(label))
                .append("]</span>");
        return span.toString();
    }

    private static String inferRenderOutputType(String relativePath) {
        String lower = Objects.toString(relativePath, "").toLowerCase(Locale.ROOT);
        if (lower.endsWith(".svg")) {
            return "svg";
        }
        if (lower.endsWith(".png")) {
            return "png";
        }
        return "other";
    }

    private static boolean isWebRenderableImage(String relativePath) {
        String lower = Objects.toString(relativePath, "").toLowerCase(Locale.ROOT);
        return lower.endsWith(".png")
                || lower.endsWith(".jpg")
                || lower.endsWith(".jpeg")
                || lower.endsWith(".gif")
                || lower.endsWith(".webp")
                || lower.endsWith(".svg");
    }

    private static String sniffWebImageExtension(Path imagePath) throws IOException {
        byte[] header = new byte[16];
        int read;
        try (InputStream in = Files.newInputStream(imagePath)) {
            read = in.read(header);
        }
        if (read >= 8
                && (header[0] & 0xff) == 0x89
                && header[1] == 'P'
                && header[2] == 'N'
                && header[3] == 'G'
                && header[4] == 0x0d
                && header[5] == 0x0a
                && header[6] == 0x1a
                && header[7] == 0x0a) {
            return ".png";
        }
        if (read >= 3
                && (header[0] & 0xff) == 0xff
                && (header[1] & 0xff) == 0xd8
                && (header[2] & 0xff) == 0xff) {
            return ".jpg";
        }
        if (read >= 6
                && header[0] == 'G'
                && header[1] == 'I'
                && header[2] == 'F'
                && header[3] == '8'
                && (header[4] == '7' || header[4] == '9')
                && header[5] == 'a') {
            return ".gif";
        }
        if (read >= 12
                && header[0] == 'R'
                && header[1] == 'I'
                && header[2] == 'F'
                && header[3] == 'F'
                && header[8] == 'W'
                && header[9] == 'E'
                && header[10] == 'B'
                && header[11] == 'P') {
            return ".webp";
        }
        return "";
    }

    private String guessRelatedExtension(XWPFDocument doc, String relId) {
        if (relId == null || relId.isBlank()) {
            return "";
        }
        try {
            PackagePart relatedPart = resolveRelatedPart(doc, relId);
            if (relatedPart == null) {
                return "";
            }
            return guessExtension(relatedPart);
        } catch (Exception ignored) {
            return "";
        }
    }

    private String renderImageLikeNode(Element node, XWPFDocument doc, Path assetDir) throws Exception {
        long start = System.nanoTime();
        try {
        Element blip = findDescendant(node, "blip");
        String relId = blip != null ? attrByLocalName(blip, "embed") : null;
        if (relId == null || relId.isBlank()) {
            Element imageData = findDescendant(node, "imagedata");
            relId = imageData != null ? attrByLocalName(imageData, "id") : null;
        }
        if (relId == null || relId.isBlank()) {
            return "";
        }

        String sidecarMathml = renderSidecarMathml(doc, relId, false);
        if (sidecarMathml != null) {
            return sidecarMathml;
        }

        SavedBinary saved = saveRelatedBinary(doc, relId, assetDir, "image", true);
        if (saved == null) {
            return buildUnsupportedInlineImagePlaceholder(
                    "Missing inline image asset",
                    "",
                    "",
                    "missing-inline-image"
            );
        }
        Path imagePath = resolveAssetPath(assetDir, saved.relativePath());
        if (isMetafileReference(saved.relativePath())) {
            return buildUnsupportedInlineImagePlaceholder(
                    "Unsupported inline image format: " + saved.sourceExtension(),
                    saved.sourceExtension(),
                    saved.relativePath(),
                    "unsupported-inline-metafile"
            );
        }
        if (saved.relativePath().toLowerCase(Locale.ROOT).endsWith(".gif") && isPlaceholderGifAsset(imagePath)) {
            // Placeholder GIFs (1x1/blank) are non-publishable inline artifacts; drop them from final HTML.
            return "";
        }
        if (!isWebRenderableImage(saved.relativePath())) {
            return buildUnsupportedInlineImagePlaceholder(
                    "Unsupported inline image format: " + saved.sourceExtension(),
                    saved.sourceExtension(),
                    saved.relativePath(),
                    "unsupported-web-image-inline"
            );
        }
        GenericInlineTrimResult trimResult = trimGenericInlineImage(saved.relativePath(), imagePath);
        String inlineCssClass = trimResult.applied() ? "inline-image inline-image-trimmed" : "inline-image";

        StringBuilder img = new StringBuilder(192);
        img.append("<img class=\"").append(inlineCssClass).append("\" src=\"").append(HtmlUtil.escapeAttribute(saved.relativePath()))
                .append("\" alt=\"\"")
                .append(" data-render-output-type=\"").append(HtmlUtil.escapeAttribute(inferRenderOutputType(saved.relativePath()))).append("\"")
                .append(" data-render-success=\"true\"")
                .append(" data-trim-candidate=\"").append(trimResult.candidate() ? "true" : "false").append("\"")
                .append(" data-trim-applied=\"").append(trimResult.applied() ? "true" : "false").append("\"")
                .append(" data-trim-safe=\"").append(trimResult.safe() ? "true" : "false").append("\"");
        if (!trimResult.trimType().isBlank()) {
            img.append(" data-trim-type=\"").append(HtmlUtil.escapeAttribute(trimResult.trimType())).append("\"");
        }
        if (!saved.sourceExtension().isBlank()) {
            img.append(" data-source-ext=\"").append(HtmlUtil.escapeAttribute(saved.sourceExtension())).append("\"");
        }
        img.append("/>");
        return img.toString();
        } finally {
            stageImageRenderingNanos.addAndGet(System.nanoTime() - start);
        }
    }

    private String renderSidecarMathml(XWPFDocument doc, String relId, boolean block) throws Exception {
        long start = System.nanoTime();
        try {
            SidecarProbe probe = probeSidecarMathml(doc, relId, block);
            if (probe.html() == null) {
                return null;
            }
            return probe.html();
        } finally {
            stageMathTypeHandlingNanos.addAndGet(System.nanoTime() - start);
        }
    }

    private SavedBinary saveRelatedBinary(
            XWPFDocument doc,
            String relId,
            Path assetDir,
            String prefix,
            boolean rasterizeMetafiles
    ) throws OpenXML4JException, IOException {
        return saveRelatedBinary(doc, relId, assetDir, prefix, rasterizeMetafiles, null);
    }

    private SavedBinary saveRelatedBinary(
            XWPFDocument doc,
            String relId,
            Path assetDir,
            String prefix,
            boolean rasterizeMetafiles,
            OleKind oleKind
    ) throws OpenXML4JException, IOException {
        if (relId == null || relId.isBlank()) {
            return null;
        }
        SavedBinary cached = savedAssetByRelationship.get(relId);
        if (cached != null) {
            return cached;
        }
        PackagePart relatedPart = resolveRelatedPart(doc, relId);
        if (relatedPart == null) {
            return null;
        }

        String extension = guessExtension(relatedPart);
        String normalizedExtension = extension.toLowerCase(Locale.ROOT);
        String fileBase = prefix + "-" + assetCounter.getAndIncrement();
        String fileName = fileBase + normalizedExtension;
        Path out = assetDir.resolve(fileName);

        try (InputStream in = relatedPart.getInputStream()) {
            Files.copy(in, out, StandardCopyOption.REPLACE_EXISTING);
        }
        String relativePath = assetDir.getFileName() + "/" + fileName;
        if (!isWebRenderableImage(fileName) && !isMetafileExtension(normalizedExtension)) {
            String sniffedWebExtension = sniffWebImageExtension(out);
            if (!sniffedWebExtension.isBlank()) {
                Path promoted = assetDir.resolve(fileBase + sniffedWebExtension);
                Files.move(out, promoted, StandardCopyOption.REPLACE_EXISTING);
                relativePath = assetDir.getFileName() + "/" + promoted.getFileName();
                SavedBinary saved = new SavedBinary(relativePath, normalizedExtension, false);
                savedAssetByRelationship.put(relId, saved);
                return saved;
            }
        }
        if (rasterizeMetafiles && isMetafileExtension(normalizedExtension)) {
            Path svgOutput = assetDir.resolve(fileBase + ".svg");
            boolean shouldRenderSvg = oleKind != OleKind.EQUATION;
            if (shouldRenderSvg && renderMetafileToSvg(out, svgOutput)) {
                Files.deleteIfExists(out);
                relativePath = assetDir.getFileName() + "/" + svgOutput.getFileName();
                if ((oleKind == OleKind.CHEMICAL_DIAGRAM
                        || oleKind == OleKind.DIAGRAM
                        || oleKind == OleKind.ILLUSTRATION)
                        && trimSvgByBoundingBoxes(svgOutput)) {
                    // Preserve existing marker for chemical diagram assets while also trimming
                    // oversized canvas whitespace for diagram/illustration SVG exports.
                    if (oleKind == OleKind.CHEMICAL_DIAGRAM) {
                    trimmedChemicalDiagramAssets.add(relativePath);
                    }
                }
                SavedBinary saved = new SavedBinary(relativePath, normalizedExtension, false);
                savedAssetByRelationship.put(relId, saved);
                return saved;
            }
            Path pngOutput = assetDir.resolve(fileBase + ".png");
            boolean allowPoiMetafileFallback = oleKind != OleKind.EQUATION;
            if (rasterizeMetafileWithCache(out, normalizedExtension, pngOutput, allowPoiMetafileFallback)) {
                Files.deleteIfExists(out);
                relativePath = assetDir.getFileName() + "/" + pngOutput.getFileName();
                SavedBinary saved = new SavedBinary(relativePath, normalizedExtension, true);
                savedAssetByRelationship.put(relId, saved);
                return saved;
            }
        }
        SavedBinary saved = new SavedBinary(relativePath, normalizedExtension, false);
        savedAssetByRelationship.put(relId, saved);
        return saved;
    }

    private PackagePart resolveRelatedPart(XWPFDocument doc, String relId) throws OpenXML4JException {
        if (relId == null || relId.isBlank()) {
            return null;
        }
        PackageRelationship relationship = doc.getPackagePart().getRelationship(relId);
        if (relationship == null) {
            return null;
        }
        try {
            return doc.getPackagePart().getRelatedPart(relationship);
        } catch (OpenXML4JException ex) {
            warnMalformedRelationshipResolution(relId, relationship, ex);
            return null;
        } catch (RuntimeException ex) {
            if (!isLikelyMalformedRelationshipPart(ex)) {
                throw ex;
            }
            warnMalformedRelationshipResolution(relId, relationship, ex);
            return null;
        }
    }

    private static boolean isLikelyMalformedRelationshipPart(RuntimeException ex) {
        String message = Objects.toString(ex.getMessage(), "").toLowerCase(Locale.ROOT);
        return message.contains("part name")
                || message.contains("forward slash")
                || message.contains("m1.4")
                || message.contains(" null")
                || message.contains("no part found for relationship id=");
    }

    private void warnMalformedRelationshipResolution(String relId, PackageRelationship relationship, Exception ex) {
        String target = "<unknown>";
        if (relationship != null) {
            try {
                String rawTarget = Objects.toString(relationship.getTargetURI(), "").trim();
                if (!rawTarget.isBlank()) {
                    target = rawTarget;
                }
            } catch (RuntimeException ignored) {
                target = "<unavailable>";
            }
        }
        String reason = classifyMalformedRelationshipReason(target, ex);
        String key = relId + "|" + target + "|" + reason;
        if (!warnedMalformedRelationshipKeys.add(key)) {
            return;
        }
        String source = currentSourceDocxContext == null || currentSourceDocxContext.isBlank()
                ? "<unknown-docx>"
                : currentSourceDocxContext;
        System.err.println(
                "[docx-html-convert] Warning: skipping malformed relationship while converting '"
                        + source
                        + "' (relId="
                        + relId
                        + ", target="
                        + target
                        + "): "
                        + reason
                        + ". Conversion continues after skipping the offending object."
        );
    }

    private static String classifyMalformedRelationshipReason(String target, Exception ex) {
        String normalizedTarget = Objects.toString(target, "").trim();
        String message = Objects.toString(ex.getMessage(), "").toLowerCase(Locale.ROOT);
        if ("NULL".equalsIgnoreCase(normalizedTarget) || message.contains(" null")) {
            return "invalid/null relationship target part name";
        }
        if (message.contains("no part found for relationship id=")) {
            return "relationship target part is missing or invalid";
        }
        if (message.contains("part name") || message.contains("forward slash") || message.contains("m1.4")) {
            return "malformed package part name in relationship target";
        }
        return "relationship/package metadata is invalid (" + ex.getClass().getSimpleName() + ")";
    }

    private String guessExtension(PackagePart part) {
        String fileName = part.getPartName().getName();
        int dot = fileName.lastIndexOf('.');
        if (dot >= 0 && dot < fileName.length() - 1) {
            return fileName.substring(dot).toLowerCase(Locale.ROOT);
        }

        String contentType = Objects.toString(part.getContentType(), "").toLowerCase(Locale.ROOT);
        if (contentType.contains("png")) return ".png";
        if (contentType.contains("jpeg") || contentType.contains("jpg")) return ".jpg";
        if (contentType.contains("gif")) return ".gif";
        if (contentType.contains("svg")) return ".svg";
        if (contentType.contains("webp")) return ".webp";
        if (contentType.contains("bmp")) return ".bmp";
        if (contentType.contains("tiff")) return ".tiff";
        if (contentType.contains("wmf")) return ".wmf";
        if (contentType.contains("emf")) return ".emf";
        return ".bin";
    }

    private static OleKind classifyOleKind(String progId) {
        String normalized = Objects.toString(progId, "").toLowerCase(Locale.ROOT);
        if (normalized.contains("equation.dsmt4")) {
            return OleKind.DSMT4_EQUATION;
        }
        if (normalized.contains("equation")
                || normalized.contains("mathtype")
                || normalized.contains("dsmt")
                || normalized.contains("mtef")) {
            return OleKind.EQUATION;
        }
        if (normalized.contains("chemdraw")
                || normalized.contains("chemsketch")
                || normalized.contains("chemwindow")
                || normalized.contains("acd.")) {
            return OleKind.CHEMICAL_DIAGRAM;
        }
        if (normalized.contains("visio")
                || normalized.contains("diagram")
                || normalized.contains("graph")
                || normalized.contains("chart")) {
            return OleKind.DIAGRAM;
        }
        return OleKind.ILLUSTRATION;
    }

    private static String buildOlePrefix(OleKind kind) {
        return switch (kind) {
            case DSMT4_EQUATION -> "ole-dsmt4";
            case EQUATION -> "ole-equation";
            case DIAGRAM -> "ole-diagram";
            case CHEMICAL_DIAGRAM -> "chem-diagram";
            case ILLUSTRATION -> "embedded-object";
        };
    }

    private String buildOleCssClass(OleKind kind) {
        return switch (kind) {
            case DSMT4_EQUATION -> "equation-fallback";
            case EQUATION -> "equation-fallback";
            case DIAGRAM -> subjectRules.diagramCssClass();
            case CHEMICAL_DIAGRAM -> subjectRules.chemicalDiagramCssClass();
            case ILLUSTRATION -> "embedded-object";
        };
    }

    private String buildOleAltText(OleKind kind, String progId) {
        String base = switch (kind) {
            case DSMT4_EQUATION -> "Legacy Equation fallback image";
            case EQUATION -> "Equation fallback image";
            case DIAGRAM -> subjectRules.diagramAltText();
            case CHEMICAL_DIAGRAM -> subjectRules.chemicalDiagramAltText();
            case ILLUSTRATION -> "Embedded illustration";
        };
        if (progId == null || progId.isBlank()) {
            return base;
        }
        return base + " (" + progId + ")";
    }

    private static String buildOlePlaceholderLabel(OleKind kind, String progId) {
        String base = switch (kind) {
            case DSMT4_EQUATION -> "Unresolved OLE equation";
            case EQUATION -> "Unresolved OLE equation";
            case DIAGRAM -> "Unresolved OLE diagram";
            case CHEMICAL_DIAGRAM -> "Unresolved chemical diagram";
            case ILLUSTRATION -> "Unresolved OLE object";
        };
        if (progId == null || progId.isBlank()) {
            return base;
        }
        return base + ": " + progId;
    }

    private static String buildOlePlaceholderClass(OleKind kind) {
        return switch (kind) {
            case DSMT4_EQUATION -> "unsupported-equation unsupported-ole-equation unsupported-ole-dsmt4";
            case EQUATION -> "unsupported-equation unsupported-ole-equation";
            case DIAGRAM -> "unsupported-equation unsupported-ole-diagram";
            case CHEMICAL_DIAGRAM -> "unsupported-equation unsupported-chemical-diagram";
            case ILLUSTRATION -> "unsupported-equation unsupported-ole-object";
        };
    }

    private static String buildUnresolvedPlaceholderFamily(OleKind kind) {
        return switch (kind) {
            case DSMT4_EQUATION -> "ole-equation-dsmt4";
            case EQUATION -> "ole-equation";
            case DIAGRAM -> "ole-diagram";
            case CHEMICAL_DIAGRAM -> "chemical-diagram";
            case ILLUSTRATION -> "ole-object";
        };
    }

    private static String buildUnresolvedPlaceholderReason(
            OleKind kind,
            String progId,
            boolean renderAttempted,
            String renderSourceUsed,
            String sourceExtTrace,
            String sourceAssetTrace
    ) {
        String sourceTrace = (Objects.toString(sourceExtTrace, "") + " " + Objects.toString(sourceAssetTrace, "")).toLowerCase(Locale.ROOT);
        String renderSource = Objects.toString(renderSourceUsed, "").trim().toLowerCase(Locale.ROOT);
        if (kind == OleKind.CHEMICAL_DIAGRAM) {
            if (!renderAttempted) {
                return "missing-embedded-chemical-preview";
            }
            if (sourceTrace.contains(".emf") || sourceTrace.contains(".wmf")) {
                return "chemical-diagram-metafile-not-rasterizable";
            }
            if (renderSource.contains("preview-image")) {
                return "chemical-diagram-preview-not-renderable";
            }
            return "chemical-diagram-unresolved";
        }
        if (kind == OleKind.DSMT4_EQUATION) {
            return "dsmt4-unresolved";
        }
        if (kind == OleKind.DIAGRAM && isVisioProgId(progId)) {
            return "visio-preview-not-renderable";
        }
        if (renderSource.isBlank() || "none".equals(renderSource)) {
            return "missing-renderable-preview";
        }
        if (sourceTrace.contains(".emf") || sourceTrace.contains(".wmf")) {
            return "metafile-not-rasterizable";
        }
        return "unresolved-embedded-object";
    }

    private static boolean isVisioProgId(String progId) {
        return Objects.toString(progId, "").toLowerCase(Locale.ROOT).contains("visio");
    }

    private static String wrapMathml(String mathml, boolean display, String source) {
        String normalizedMathml = enforceMathDisplay(mathml, display);
        if (display) {
            return "<div class=\"math-block mathml\">" + normalizedMathml + "</div>";
        }
        return "<span class=\"math-inline mathml\">" + normalizedMathml + "</span>";
    }

    private static boolean isMetafileExtension(String extension) {
        String ext = Objects.toString(extension, "").toLowerCase(Locale.ROOT);
        return ".emf".equals(ext) || ".wmf".equals(ext);
    }

    private static boolean isMetafileReference(String relativePath) {
        String lower = Objects.toString(relativePath, "").toLowerCase(Locale.ROOT);
        return lower.endsWith(".emf") || lower.endsWith(".wmf");
    }

    private static Path resolveAssetPath(Path assetDir, String relativePath) {
        if (assetDir == null) {
            return null;
        }
        String rel = Objects.toString(relativePath, "");
        if (rel.isBlank()) {
            return assetDir;
        }
        if (assetDir.getFileName() != null) {
            String prefix = assetDir.getFileName() + "/";
            if (rel.startsWith(prefix)) {
                return assetDir.resolve(rel.substring(prefix.length()));
            }
        }
        return assetDir.resolve(rel);
    }

    private static boolean isPlaceholderGifAsset(Path gifPath) {
        if (gifPath == null || !Files.exists(gifPath)) {
            return false;
        }
        String lower = Objects.toString(gifPath.getFileName(), "").toLowerCase(Locale.ROOT);
        if (!lower.endsWith(".gif")) {
            return false;
        }
        try {
            if (Files.size(gifPath) <= 128) {
                return true;
            }
        } catch (IOException ignored) {
            return false;
        }
        try (InputStream in = Files.newInputStream(gifPath)) {
            BufferedImage image = ImageIO.read(in);
            if (image == null) {
                return true;
            }
            if (image.getWidth() <= 1 || image.getHeight() <= 1) {
                return true;
            }
        } catch (IOException ignored) {
            return false;
        }
        return isLikelyBlankRasterImage(gifPath);
    }

    private GenericInlineTrimResult trimGenericInlineImage(String relativePath, Path imagePath) {
        if (relativePath == null || relativePath.isBlank() || imagePath == null || !Files.exists(imagePath)) {
            return GenericInlineTrimResult.none();
        }
        GenericInlineTrimResult cached = genericInlineTrimByAsset.get(relativePath);
        if (cached != null) {
            return cached;
        }
        String lower = relativePath.toLowerCase(Locale.ROOT);
        GenericInlineTrimResult result;
        if (lower.endsWith(".svg")) {
            result = trimGenericInlineSvgWhitespace(imagePath);
        } else if (INLINE_TRIMMABLE_RASTER_EXTENSIONS.stream().anyMatch(lower::endsWith)) {
            result = trimGenericInlineRasterWhitespace(imagePath, lower);
        } else {
            result = GenericInlineTrimResult.none();
        }
        genericInlineTrimByAsset.put(relativePath, result);
        return result;
    }

    private static GenericInlineTrimResult trimGenericInlineSvgWhitespace(Path svgPath) {
        if (svgPath == null || !Files.exists(svgPath)) {
            return GenericInlineTrimResult.none();
        }
        boolean candidate = false;
        try {
            String svg = Files.readString(svgPath, StandardCharsets.UTF_8);
            Matcher rootMatcher = SVG_ROOT_TAG_PATTERN.matcher(svg);
            if (!rootMatcher.find()) {
                return GenericInlineTrimResult.none();
            }
            String rootTag = rootMatcher.group();
            Map<String, String> rootAttrs = parseTagAttributes(rootTag);
            String viewBox = rootAttrs.get("viewbox");
            if (viewBox == null || viewBox.isBlank()) {
                return GenericInlineTrimResult.none();
            }
            double[] vb = parseViewBox(viewBox);
            if (vb == null) {
                return GenericInlineTrimResult.none();
            }

            Double minX = null;
            Double minY = null;
            Double maxX = null;
            Double maxY = null;
            int bboxCount = 0;

            Matcher bboxMatcher = SVG_BOUNDING_BOX_RECT_PATTERN.matcher(svg);
            while (bboxMatcher.find()) {
                String tag = bboxMatcher.group();
                Map<String, String> attrs = parseTagAttributes(tag);
                Double x = parseSvgNumber(attrs.get("x"));
                Double y = parseSvgNumber(attrs.get("y"));
                Double w = parseSvgNumber(attrs.get("width"));
                Double h = parseSvgNumber(attrs.get("height"));
                if (x == null || y == null || w == null || h == null || w <= 0 || h <= 0) {
                    continue;
                }
                bboxCount++;
                minX = minX == null ? x : Math.min(minX, x);
                minY = minY == null ? y : Math.min(minY, y);
                maxX = maxX == null ? (x + w) : Math.max(maxX, x + w);
                maxY = maxY == null ? (y + h) : Math.max(maxY, y + h);
            }

            if (bboxCount == 0 || minX == null || minY == null || maxX == null || maxY == null) {
                return GenericInlineTrimResult.none();
            }

            double oldX = vb[0];
            double oldY = vb[1];
            double oldW = vb[2];
            double oldH = vb[3];
            if (oldW <= 0 || oldH <= 0) {
                return GenericInlineTrimResult.none();
            }

            double contentW = maxX - minX;
            double contentH = maxY - minY;
            if (contentW <= 0 || contentH <= 0) {
                return GenericInlineTrimResult.none();
            }
            double contentAreaRatio = (contentW * contentH) / (oldW * oldH);
            candidate = contentAreaRatio < 0.90d;
            if (!candidate) {
                return GenericInlineTrimResult.notCandidate();
            }

            double padding = Math.max(24.0d, Math.min(contentW, contentH) * 0.04d);
            double newX = Math.max(oldX, minX - padding);
            double newY = Math.max(oldY, minY - padding);
            double newMaxX = Math.min(oldX + oldW, maxX + padding);
            double newMaxY = Math.min(oldY + oldH, maxY + padding);
            double newW = Math.max(1.0d, newMaxX - newX);
            double newH = Math.max(1.0d, newMaxY - newY);

            if (newW >= oldW * 0.995d && newH >= oldH * 0.995d) {
                return GenericInlineTrimResult.notCandidate();
            }

            double unitsPerMm = 100.0d;
            Double widthMm = parseLengthInMillimeters(rootAttrs.get("width"));
            if (widthMm != null && widthMm > 0.0d) {
                unitsPerMm = oldW / widthMm;
            }
            if (unitsPerMm <= 0.0d || Double.isNaN(unitsPerMm) || Double.isInfinite(unitsPerMm)) {
                unitsPerMm = 100.0d;
            }
            double newWidthMm = newW / unitsPerMm;
            double newHeightMm = newH / unitsPerMm;

            String rewrittenRoot = rootTag;
            rewrittenRoot = upsertSvgAttribute(rewrittenRoot, "viewBox", formatSvgNumber(newX) + " " + formatSvgNumber(newY) + " " + formatSvgNumber(newW) + " " + formatSvgNumber(newH));
            rewrittenRoot = upsertSvgAttribute(rewrittenRoot, "width", formatSvgNumber(newWidthMm) + "mm");
            rewrittenRoot = upsertSvgAttribute(rewrittenRoot, "height", formatSvgNumber(newHeightMm) + "mm");
            rewrittenRoot = upsertSvgAttribute(rewrittenRoot, "preserveAspectRatio", "xMidYMid meet");

            String rewritten = svg.substring(0, rootMatcher.start()) + rewrittenRoot + svg.substring(rootMatcher.end());
            Files.writeString(svgPath, rewritten, StandardCharsets.UTF_8);
            return GenericInlineTrimResult.applied("svg-viewbox");
        } catch (Exception ignored) {
            return candidate
                    ? GenericInlineTrimResult.candidateNotApplied("svg-viewbox", false)
                    : GenericInlineTrimResult.none();
        }
    }

    private static GenericInlineTrimResult trimGenericInlineRasterWhitespace(Path imagePath, String lowerRelativePath) {
        if (imagePath == null || !Files.exists(imagePath)) {
            return GenericInlineTrimResult.none();
        }
        String format = "";
        if (lowerRelativePath.endsWith(".png")) {
            format = "png";
        } else if (lowerRelativePath.endsWith(".jpg") || lowerRelativePath.endsWith(".jpeg")) {
            format = "jpg";
        } else if (lowerRelativePath.endsWith(".gif")) {
            format = "gif";
        }
        if (format.isBlank()) {
            return GenericInlineTrimResult.none();
        }

        boolean candidate = false;
        try (InputStream in = Files.newInputStream(imagePath)) {
            BufferedImage image = ImageIO.read(in);
            if (image == null) {
                return GenericInlineTrimResult.none();
            }
            int width = image.getWidth();
            int height = image.getHeight();
            if (width <= 0 || height <= 0) {
                return GenericInlineTrimResult.none();
            }

            int minX = width;
            int minY = height;
            int maxX = -1;
            int maxY = -1;
            for (int y = 0; y < height; y++) {
                for (int x = 0; x < width; x++) {
                    int argb = image.getRGB(x, y);
                    if (!isMeaningfulRasterContentPixel(argb)) {
                        continue;
                    }
                    minX = Math.min(minX, x);
                    minY = Math.min(minY, y);
                    maxX = Math.max(maxX, x);
                    maxY = Math.max(maxY, y);
                }
            }
            if (maxX < minX || maxY < minY) {
                return GenericInlineTrimResult.none();
            }

            int contentW = maxX - minX + 1;
            int contentH = maxY - minY + 1;
            double contentAreaRatio = (double) contentW * (double) contentH / ((double) width * (double) height);
            int leftMargin = minX;
            int topMargin = minY;
            int rightMargin = width - 1 - maxX;
            int bottomMargin = height - 1 - maxY;
            int minMarginX = Math.max(6, (int) Math.round(width * 0.03d));
            int minMarginY = Math.max(6, (int) Math.round(height * 0.03d));
            int totalMarginX = leftMargin + rightMargin;
            int totalMarginY = topMargin + bottomMargin;
            boolean hasRequiredAxisMargin = leftMargin >= minMarginX
                    || rightMargin >= minMarginX
                    || topMargin >= minMarginY
                    || bottomMargin >= minMarginY;
            boolean hasStrongOuterWhitespace = totalMarginX >= Math.max(22, (int) Math.round(width * 0.05d))
                    || totalMarginY >= Math.max(22, (int) Math.round(height * 0.05d));
            boolean hasModerateOuterWhitespace = totalMarginX >= Math.max(10, (int) Math.round(width * 0.025d))
                    || totalMarginY >= Math.max(10, (int) Math.round(height * 0.025d));
            int shortEdge = Math.min(width, height);
            int compactMargin = Math.max(4, (int) Math.round(shortEdge * 0.02d));
            boolean hasCompactOuterWhitespace = totalMarginX >= compactMargin || totalMarginY >= compactMargin;
            candidate = (contentAreaRatio < 0.93d && hasRequiredAxisMargin)
                    || (contentAreaRatio < 0.95d && hasStrongOuterWhitespace)
                    || (contentAreaRatio < 0.958d && hasModerateOuterWhitespace)
                    || (contentAreaRatio < 0.965d && hasCompactOuterWhitespace);
            if (!candidate) {
                return GenericInlineTrimResult.notCandidate();
            }

            int padding = Math.max(2, (int) Math.round(Math.min(width, height) * 0.01d));
            int cropX = Math.max(0, minX - padding);
            int cropY = Math.max(0, minY - padding);
            int cropMaxX = Math.min(width - 1, maxX + padding);
            int cropMaxY = Math.min(height - 1, maxY + padding);
            int cropW = cropMaxX - cropX + 1;
            int cropH = cropMaxY - cropY + 1;

            if (cropW >= width * 0.995d && cropH >= height * 0.995d) {
                return GenericInlineTrimResult.notCandidate();
            }

            BufferedImage sub = image.getSubimage(cropX, cropY, cropW, cropH);
            int targetType = "jpg".equals(format) ? BufferedImage.TYPE_INT_RGB : BufferedImage.TYPE_INT_ARGB;
            BufferedImage trimmed = new BufferedImage(cropW, cropH, targetType);
            Graphics2D graphics = trimmed.createGraphics();
            try {
                if ("jpg".equals(format)) {
                    graphics.setColor(Color.WHITE);
                    graphics.fillRect(0, 0, cropW, cropH);
                }
                graphics.drawImage(sub, 0, 0, null);
            } finally {
                graphics.dispose();
            }

            Path tempFile = Files.createTempFile(imagePath.getParent(), "inline-trim-", ".tmp");
            try {
                if (!ImageIO.write(trimmed, format, tempFile.toFile())) {
                    return GenericInlineTrimResult.candidateNotApplied("raster-bbox", false);
                }
                Files.move(tempFile, imagePath, StandardCopyOption.REPLACE_EXISTING);
            } finally {
                Files.deleteIfExists(tempFile);
            }
            return GenericInlineTrimResult.applied("raster-bbox");
        } catch (Exception ignored) {
            return candidate
                    ? GenericInlineTrimResult.candidateNotApplied("raster-bbox", false)
                    : GenericInlineTrimResult.none();
        }
    }

    private static boolean isMeaningfulRasterContentPixel(int argb) {
        int alpha = (argb >>> 24) & 0xff;
        if (alpha <= 12) {
            return false;
        }
        int red = (argb >>> 16) & 0xff;
        int green = (argb >>> 8) & 0xff;
        int blue = argb & 0xff;
        int max = Math.max(red, Math.max(green, blue));
        int min = Math.min(red, Math.min(green, blue));
        return !(max >= 240 && (max - min) <= 14);
    }

    private static Path initMetafileRasterCacheDir() {
        String configured = Objects.toString(System.getenv("DOCX_MATH_METAFILE_CACHE_DIR"), "").trim();
        String home = Objects.toString(System.getenv("HOME"), "").trim();
        Path cacheDir;
        if (!configured.isEmpty()) {
            cacheDir = Path.of(configured).toAbsolutePath().normalize();
        } else if (!home.isEmpty()) {
            cacheDir = Path.of(home, ".cache", "docx-html-math", "metafile-raster").toAbsolutePath().normalize();
        } else {
            cacheDir = Path.of(".cache", "docx-html-math", "metafile-raster").toAbsolutePath().normalize();
        }
        try {
            Files.createDirectories(cacheDir);
            return cacheDir;
        } catch (IOException ignored) {
            return null;
        }
    }

    private static String sha256(Path file) {
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (Exception ex) {
            throw new IllegalStateException("SHA-256 not available", ex);
        }

        try (InputStream in = Files.newInputStream(file)) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = in.read(buffer)) >= 0) {
                if (read > 0) {
                    digest.update(buffer, 0, read);
                }
            }
        } catch (IOException ex) {
            throw new IllegalStateException("Unable to hash file " + file, ex);
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    private static String detectRasterToolCommand() {
        for (String candidate : List.of("magick", "convert")) {
            if (isCommandAvailable(candidate, "-version")) {
                return candidate;
            }
        }
        return "";
    }

    private static String detectOfficeToolCommand() {
        for (String candidate : List.of("soffice", "libreoffice")) {
            if (isCommandAvailable(candidate, "--version")) {
                return candidate;
            }
        }
        return "";
    }

    private static boolean isCommandAvailable(String command, String... args) {
        List<String> cmd = new ArrayList<>();
        cmd.add(command);
        cmd.addAll(List.of(args));
        ProcessBuilder builder = new ProcessBuilder(cmd);
        builder.redirectErrorStream(true);
        try {
            Process process = builder.start();
            try (InputStream stdout = process.getInputStream()) {
                stdout.transferTo(OutputStream.nullOutputStream());
            }
            if (!process.waitFor(4, TimeUnit.SECONDS)) {
                process.destroyForcibly();
                return false;
            }
            return process.exitValue() == 0;
        } catch (Exception ignored) {
            return false;
        }
    }

    private boolean rasterizeMetafileWithCache(Path sourceMetafile, String sourceExtension, Path targetPng, boolean allowPoiFallback) {
        if (metafileRasterCacheDir == null) {
            return rasterizeMetafileToPng(sourceMetafile, targetPng, allowPoiFallback);
        }
        String digest;
        try {
            digest = sha256(sourceMetafile);
        } catch (Exception ignored) {
            return rasterizeMetafileToPng(sourceMetafile, targetPng, allowPoiFallback);
        }
        Path cacheEntry = metafileRasterCacheDir.resolve(digest + sourceExtension + ".png");
        try {
            if (Files.exists(cacheEntry) && Files.size(cacheEntry) > 0) {
                if (isLikelyBlankRasterImage(cacheEntry)) {
                    Files.deleteIfExists(cacheEntry);
                } else {
                    Files.copy(cacheEntry, targetPng, StandardCopyOption.REPLACE_EXISTING);
                    rasterizedMetafileCacheHitCounter.incrementAndGet();
                    return true;
                }
            }
        } catch (IOException ignored) {
            // fall through to conversion path
        }
        if (!rasterizeMetafileToPng(sourceMetafile, targetPng, allowPoiFallback)) {
            return false;
        }
        if (isLikelyBlankRasterImage(targetPng)) {
            try {
                Files.deleteIfExists(targetPng);
            } catch (IOException ignored) {
                // no-op
            }
            return false;
        }
        try {
            Files.copy(targetPng, cacheEntry, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException ignored) {
            // no-op: conversion already succeeded
        }
        return true;
    }

    private boolean rasterizeMetafileToPng(Path sourceMetafile, Path targetPng, boolean allowPoiFallback) {
        try {
            if (Files.exists(targetPng) && Files.size(targetPng) > 0) {
                if (!isLikelyBlankRasterImage(targetPng)) {
                    return true;
                }
                Files.deleteIfExists(targetPng);
            }
        } catch (IOException ignored) {
            // continue and attempt conversion
        }

        boolean converted = false;
        if (!rasterToolCommand.isBlank()) {
            converted = rasterizeMetafileWithExternalTool(sourceMetafile, targetPng);
            if (converted && isLikelyBlankRasterImage(targetPng)) {
                converted = false;
                try {
                    Files.deleteIfExists(targetPng);
                } catch (IOException ignored) {
                    // no-op
                }
            }
        }
        if (!converted && allowPoiFallback) {
            converted = rasterizeMetafileWithPoi(sourceMetafile, targetPng);
            if (converted && isLikelyBlankRasterImage(targetPng)) {
                converted = false;
                try {
                    Files.deleteIfExists(targetPng);
                } catch (IOException ignored) {
                    // no-op
                }
            }
        }
        if (converted) {
            rasterizedMetafileCounter.incrementAndGet();
            return true;
        }
        try {
            Files.deleteIfExists(targetPng);
        } catch (IOException ignored) {
            // no-op
        }
        return false;
    }

    private boolean renderMetafileToSvg(Path sourceMetafile, Path targetSvg) {
        if (officeToolCommand.isBlank()) {
            return false;
        }

        Path tempOutputDir = null;
        Path tempProfileDir = null;
        try {
            tempOutputDir = Files.createTempDirectory("chem-svg-out");
            tempProfileDir = Files.createTempDirectory("chem-svg-profile");
            String sourceName = sourceMetafile.getFileName().toString();
            int dot = sourceName.lastIndexOf('.');
            String baseName = dot > 0 ? sourceName.substring(0, dot) : sourceName;
            Path generatedSvg = tempOutputDir.resolve(baseName + ".svg");

            List<String> command = new ArrayList<>();
            command.add(officeToolCommand);
            command.add("-env:UserInstallation=" + tempProfileDir.toUri());
            command.add("--headless");
            command.add("--nologo");
            command.add("--nolockcheck");
            command.add("--nodefault");
            command.add("--norestore");
            command.add("--convert-to");
            command.add("svg");
            command.add("--outdir");
            command.add(tempOutputDir.toString());
            command.add(sourceMetafile.toString());

            ProcessBuilder builder = new ProcessBuilder(command);
            builder.redirectErrorStream(true);
            builder.redirectOutput(ProcessBuilder.Redirect.DISCARD);
            Process process = builder.start();
            if (!process.waitFor(25, TimeUnit.SECONDS)) {
                process.destroyForcibly();
                officeRenderFailureCounter.incrementAndGet();
                return false;
            }
            if (process.exitValue() != 0) {
                officeRenderFailureCounter.incrementAndGet();
                return false;
            }
            if (!Files.exists(generatedSvg) || Files.size(generatedSvg) == 0) {
                officeRenderFailureCounter.incrementAndGet();
                return false;
            }
            if (!isRenderableSvg(generatedSvg)) {
                officeRenderFailureCounter.incrementAndGet();
                return false;
            }
            Files.move(generatedSvg, targetSvg, StandardCopyOption.REPLACE_EXISTING);
            return true;
        } catch (Exception ignored) {
            officeRenderFailureCounter.incrementAndGet();
            return false;
        } finally {
            deleteDirectoryQuietly(tempOutputDir);
            deleteDirectoryQuietly(tempProfileDir);
        }
    }

    private static boolean trimSvgByBoundingBoxes(Path svgPath) {
        if (svgPath == null || !Files.exists(svgPath)) {
            return false;
        }
        try {
            String svg = Files.readString(svgPath, StandardCharsets.UTF_8);
            Matcher rootMatcher = SVG_ROOT_TAG_PATTERN.matcher(svg);
            if (!rootMatcher.find()) {
                return false;
            }
            String rootTag = rootMatcher.group();
            Map<String, String> rootAttrs = parseTagAttributes(rootTag);
            String viewBox = rootAttrs.get("viewbox");
            if (viewBox == null || viewBox.isBlank()) {
                return false;
            }
            double[] vb = parseViewBox(viewBox);
            if (vb == null) {
                return false;
            }

            Double minX = null;
            Double minY = null;
            Double maxX = null;
            Double maxY = null;
            int bboxCount = 0;

            Matcher bboxMatcher = SVG_BOUNDING_BOX_RECT_PATTERN.matcher(svg);
            while (bboxMatcher.find()) {
                String tag = bboxMatcher.group();
                Map<String, String> attrs = parseTagAttributes(tag);
                Double x = parseSvgNumber(attrs.get("x"));
                Double y = parseSvgNumber(attrs.get("y"));
                Double w = parseSvgNumber(attrs.get("width"));
                Double h = parseSvgNumber(attrs.get("height"));
                if (x == null || y == null || w == null || h == null || w <= 0 || h <= 0) {
                    continue;
                }
                bboxCount++;
                minX = minX == null ? x : Math.min(minX, x);
                minY = minY == null ? y : Math.min(minY, y);
                maxX = maxX == null ? (x + w) : Math.max(maxX, x + w);
                maxY = maxY == null ? (y + h) : Math.max(maxY, y + h);
            }

            if (bboxCount == 0 || minX == null || minY == null || maxX == null || maxY == null) {
                return false;
            }

            double oldX = vb[0];
            double oldY = vb[1];
            double oldW = vb[2];
            double oldH = vb[3];
            if (oldW <= 0 || oldH <= 0) {
                return false;
            }

            double contentW = maxX - minX;
            double contentH = maxY - minY;
            if (contentW <= 0 || contentH <= 0) {
                return false;
            }
            double contentAreaRatio = (contentW * contentH) / (oldW * oldH);
            if (contentAreaRatio > 0.9d) {
                return false;
            }

            double padding = Math.max(40.0d, Math.min(contentW, contentH) * 0.05d);
            double newX = Math.max(oldX, minX - padding);
            double newY = Math.max(oldY, minY - padding);
            double newMaxX = Math.min(oldX + oldW, maxX + padding);
            double newMaxY = Math.min(oldY + oldH, maxY + padding);
            double newW = Math.max(1.0d, newMaxX - newX);
            double newH = Math.max(1.0d, newMaxY - newY);
            if (newW >= oldW * 0.995d && newH >= oldH * 0.995d) {
                return false;
            }

            double unitsPerMm = 100.0d;
            Double widthMm = parseLengthInMillimeters(rootAttrs.get("width"));
            if (widthMm != null && widthMm > 0.0d) {
                unitsPerMm = oldW / widthMm;
            }
            if (unitsPerMm <= 0.0d || Double.isNaN(unitsPerMm) || Double.isInfinite(unitsPerMm)) {
                unitsPerMm = 100.0d;
            }
            double newWidthMm = newW / unitsPerMm;
            double newHeightMm = newH / unitsPerMm;

            String rewrittenRoot = rootTag;
            rewrittenRoot = upsertSvgAttribute(rewrittenRoot, "viewBox", formatSvgNumber(newX) + " " + formatSvgNumber(newY) + " " + formatSvgNumber(newW) + " " + formatSvgNumber(newH));
            rewrittenRoot = upsertSvgAttribute(rewrittenRoot, "width", formatSvgNumber(newWidthMm) + "mm");
            rewrittenRoot = upsertSvgAttribute(rewrittenRoot, "height", formatSvgNumber(newHeightMm) + "mm");
            rewrittenRoot = upsertSvgAttribute(rewrittenRoot, "preserveAspectRatio", "xMidYMid meet");

            String rewritten = svg.substring(0, rootMatcher.start()) + rewrittenRoot + svg.substring(rootMatcher.end());
            Files.writeString(svgPath, rewritten, StandardCharsets.UTF_8);
            return true;
        } catch (Exception ignored) {
            return false;
        }
    }

    private static Map<String, String> parseTagAttributes(String tag) {
        Map<String, String> attrs = new HashMap<>();
        if (tag == null || tag.isBlank()) {
            return attrs;
        }
        Matcher matcher = SVG_ATTR_PATTERN.matcher(tag);
        while (matcher.find()) {
            attrs.put(matcher.group(1).toLowerCase(Locale.ROOT), matcher.group(2));
        }
        return attrs;
    }

    private static double[] parseViewBox(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String[] parts = value.trim().split("[,\\s]+");
        if (parts.length != 4) {
            return null;
        }
        try {
            return new double[]{
                    Double.parseDouble(parts[0]),
                    Double.parseDouble(parts[1]),
                    Double.parseDouble(parts[2]),
                    Double.parseDouble(parts[3])
            };
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private static Double parseSvgNumber(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String normalized = value.trim().replace(',', '.');
        StringBuilder buf = new StringBuilder();
        for (int i = 0; i < normalized.length(); i++) {
            char ch = normalized.charAt(i);
            if ((ch >= '0' && ch <= '9') || ch == '.' || ch == '-' || ch == '+') {
                buf.append(ch);
            } else {
                break;
            }
        }
        if (buf.isEmpty()) {
            return null;
        }
        try {
            return Double.parseDouble(buf.toString());
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private static Double parseLengthInMillimeters(String length) {
        if (length == null || length.isBlank()) {
            return null;
        }
        String raw = length.trim().toLowerCase(Locale.ROOT);
        Double num = parseSvgNumber(raw);
        if (num == null) {
            return null;
        }
        if (raw.endsWith("mm")) {
            return num;
        }
        if (raw.endsWith("cm")) {
            return num * 10.0d;
        }
        if (raw.endsWith("in")) {
            return num * 25.4d;
        }
        if (raw.endsWith("pt")) {
            return num * 25.4d / 72.0d;
        }
        if (raw.endsWith("px")) {
            return num * 25.4d / 96.0d;
        }
        return num;
    }

    private static String upsertSvgAttribute(String tag, String attrName, String attrValue) {
        Pattern attrPattern = Pattern.compile("\\b" + Pattern.quote(attrName) + "\\s*=\\s*\"[^\"]*\"", Pattern.CASE_INSENSITIVE);
        Matcher matcher = attrPattern.matcher(tag);
        String replacement = attrName + "=\"" + attrValue + "\"";
        if (matcher.find()) {
            return matcher.replaceFirst(Matcher.quoteReplacement(replacement));
        }
        int close = tag.lastIndexOf('>');
        if (close <= 0) {
            return tag;
        }
        return tag.substring(0, close) + " " + replacement + tag.substring(close);
    }

    private static String formatSvgNumber(double value) {
        if (Math.abs(value - Math.rint(value)) < 1e-6d) {
            return Long.toString(Math.round(value));
        }
        return String.format(Locale.ROOT, "%.2f", value).replaceAll("0+$", "").replaceAll("\\.$", "");
    }

    private static boolean isRenderableSvg(Path svgPath) {
        try {
            String svg = Files.readString(svgPath, StandardCharsets.UTF_8).toLowerCase(Locale.ROOT);
            if (!svg.contains("<svg")) {
                return false;
            }
            return svg.contains("<path")
                    || svg.contains("<polyline")
                    || svg.contains("<polygon")
                    || svg.contains("<line")
                    || svg.contains("<text")
                    || svg.contains("<circle")
                    || svg.contains("<ellipse")
                    || svg.contains("<rect");
        } catch (Exception ignored) {
            return false;
        }
    }

    private static void deleteDirectoryQuietly(Path dir) {
        if (dir == null) {
            return;
        }
        try {
            Files.walk(dir)
                    .sorted((a, b) -> b.getNameCount() - a.getNameCount())
                    .forEach(path -> {
                        try {
                            Files.deleteIfExists(path);
                        } catch (IOException ignored) {
                            // no-op
                        }
                    });
        } catch (IOException ignored) {
            // no-op
        }
    }

    private static boolean isLikelyBlankRasterImage(Path imagePath) {
        if (imagePath == null) {
            return false;
        }
        try (InputStream in = Files.newInputStream(imagePath)) {
            BufferedImage image = ImageIO.read(in);
            if (image == null) {
                return false;
            }
            int width = image.getWidth();
            int height = image.getHeight();
            if (width <= 0 || height <= 0) {
                return true;
            }

            int stepX = Math.max(1, width / 300);
            int stepY = Math.max(1, height / 300);
            long samples = 0;
            long brightSamples = 0;
            double sum = 0.0d;
            double sumSq = 0.0d;

            for (int y = 0; y < height; y += stepY) {
                for (int x = 0; x < width; x += stepX) {
                    int argb = image.getRGB(x, y);
                    int alpha = (argb >>> 24) & 0xff;
                    if (alpha < 10) {
                        continue;
                    }
                    int red = (argb >>> 16) & 0xff;
                    int green = (argb >>> 8) & 0xff;
                    int blue = argb & 0xff;
                    double luminance = (0.2126d * red + 0.7152d * green + 0.0722d * blue) / 255.0d;
                    samples++;
                    sum += luminance;
                    sumSq += luminance * luminance;
                    if (luminance >= 0.99d) {
                        brightSamples++;
                    }
                }
            }

            if (samples == 0) {
                return true;
            }
            double mean = sum / samples;
            double variance = Math.max(0.0d, (sumSq / samples) - (mean * mean));
            double stddev = Math.sqrt(variance);
            double brightRatio = (double) brightSamples / (double) samples;
            return (brightRatio >= 0.999d && stddev <= 0.001d) || mean >= 0.9995d;
        } catch (IOException ignored) {
            return false;
        }
    }

    private boolean rasterizeMetafileWithExternalTool(Path sourceMetafile, Path targetPng) {
        List<String> command = new ArrayList<>();
        command.add(rasterToolCommand);
        command.add("-density");
        command.add("240");
        command.add(sourceMetafile.toString());
        command.add("-background");
        command.add("white");
        command.add("-alpha");
        command.add("remove");
        command.add("-alpha");
        command.add("off");
        command.add(targetPng.toString());

        ProcessBuilder builder = new ProcessBuilder(command);
        builder.redirectErrorStream(true);
        try {
            Process process = builder.start();
            try (InputStream stdout = process.getInputStream()) {
                stdout.transferTo(OutputStream.nullOutputStream());
            }
            if (!process.waitFor(20, TimeUnit.SECONDS)) {
                process.destroyForcibly();
                return false;
            }
            if (process.exitValue() != 0) {
                return false;
            }
            return Files.exists(targetPng) && Files.size(targetPng) > 0;
        } catch (Exception ignored) {
            // keep original metafile path as fallback
            return false;
        }
    }

    private static int toPixelSize(double size) {
        if (Double.isNaN(size) || Double.isInfinite(size) || size <= 0.0d) {
            return 1200;
        }
        return Math.max(32, (int) Math.ceil(size * 2.0d));
    }

    private static Graphics2D createGraphics(BufferedImage image) {
        Graphics2D graphics = image.createGraphics();
        graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        graphics.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_QUALITY);
        graphics.setColor(Color.WHITE);
        graphics.fillRect(0, 0, image.getWidth(), image.getHeight());
        return graphics;
    }

    private boolean rasterizeMetafileWithPoi(Path sourceMetafile, Path targetPng) {
        String fileName = sourceMetafile.getFileName().toString().toLowerCase(Locale.ROOT);
        try {
            if (fileName.endsWith(".wmf")) {
                try (InputStream in = Files.newInputStream(sourceMetafile)) {
                    HwmfPicture picture = new HwmfPicture(in);
                    int width = toPixelSize(picture.getSize().getWidth());
                    int height = toPixelSize(picture.getSize().getHeight());
                    BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
                    Graphics2D graphics = createGraphics(image);
                    try {
                        picture.draw(graphics, new Rectangle2D.Double(0, 0, width, height));
                    } finally {
                        graphics.dispose();
                    }
                    return ImageIO.write(image, "png", targetPng.toFile());
                }
            }
            if (fileName.endsWith(".emf")) {
                try (InputStream in = Files.newInputStream(sourceMetafile)) {
                    HemfPicture picture = new HemfPicture(in);
                    int width = toPixelSize(picture.getSize().getWidth());
                    int height = toPixelSize(picture.getSize().getHeight());
                    BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
                    Graphics2D graphics = createGraphics(image);
                    try {
                        picture.draw(graphics, new Rectangle2D.Double(0, 0, width, height));
                    } finally {
                        graphics.dispose();
                    }
                    return ImageIO.write(image, "png", targetPng.toFile());
                }
            }
        } catch (Throwable ignored) {
            // keep original metafile path as fallback
        }
        return false;
    }

    private String buildHtmlDocument(String title, String body) {
        String mathJax = includeMathJax
                ? "<script>window.MathJax={options:{skipHtmlTags:['script','noscript','style','textarea','pre','code']}};</script>\n"
                + "<script defer src=\"https://cdn.jsdelivr.net/npm/mathjax@4/tex-mml-chtml.js\"></script>\n"
                : "";

        return "<!doctype html>\n"
                + "<html lang=\"en\">\n"
                + "<head>\n"
                + "  <meta charset=\"utf-8\"/>\n"
                + "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
                + "  <title>" + HtmlUtil.escape(title) + "</title>\n"
                + "  <style>\n"
                + "    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.6;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1f2328;}\n"
                + "    p{margin:0 0 1rem;}\n"
                + "    table.docx-table{border-collapse:collapse;margin:1rem 0;width:100%;}\n"
                + "    table.docx-table td{border:1px solid #d0d7de;padding:.5rem;vertical-align:top;}\n"
                + "    table.docx-table td>p:first-child{margin-top:0;}\n"
                + "    table.docx-table td>p:last-child{margin-bottom:0;}\n"
                + "    .math-block{margin:1rem 0;overflow-x:auto;}\n"
                + "    .math-inline{display:inline;vertical-align:baseline;}\n"
                + "    .math-inline + .math-inline{margin-left:.08em;}\n"
                + "    .math-inline.mathml math{display:inline;}\n"
                + "    p>img.inline-image:only-child,p>img.equation-fallback:only-child,p>img.diagram-asset:only-child{display:block;margin:.35rem auto;}\n"
                + "    .chem-inline{display:inline-block;white-space:nowrap;}\n"
                + "    .chem-inline sub,.chem-inline sup,p sub,p sup,td sub,td sup{font-size:.75em;line-height:0;position:relative;vertical-align:baseline;}\n"
                + "    .chem-inline sub,p sub,td sub{bottom:-.3em;}\n"
                + "    .chem-inline sup,p sup,td sup{top:-.5em;}\n"
                + "    .unsupported-equation{display:inline-block;padding:.1rem .35rem;border:1px solid #d0d7de;border-radius:.35rem;background:#fff8c5;color:#6f4e00;font-size:.95em;}\n"
                + "    .qa-hidden{display:none !important;}\n"
                + "    .equation-fallback,.diagram-asset,.physics-diagram,.physics-chart,.chemical-diagram,.chem-diagram,.embedded-object,.inline-image{max-width:100%;height:auto;vertical-align:middle;}\n"
                + "    .inline-image-trimmed{display:block;width:auto;max-width:26rem;max-width:min(100%,26rem);height:auto;margin:.5rem auto;}\n"
                + "    td .inline-image-trimmed{width:min(100%,24rem);max-width:24rem;max-width:min(100%,24rem);margin:.35rem auto;}\n"
                + "    .essay-figure,.question-figure{display:block;margin:.75rem auto;text-align:center;}\n"
                + "    .essay-figure .essay-figure-image,.question-figure .essay-figure-image,.essay-figure img,.question-figure img{display:block;width:auto;max-width:min(100%,42rem);height:auto;margin:.25rem auto;}\n"
                + "    .essential-figure-group,.question-essential-figure-group{display:flex;flex-wrap:wrap;justify-content:center;align-items:flex-start;gap:.5rem 1rem;margin:.5rem auto 1rem;}\n"
                + "    .essential-figure-group .essential-figure,.question-essential-figure-group .essential-figure{margin:.1rem .35rem;}\n"
                + "    .question-context-table{width:100%;border-collapse:collapse;table-layout:fixed;margin:.35rem 0 1rem;}\n"
                + "    .question-context-table .question-context-text-cell,.question-context-table .question-context-figure-cell{border:none;padding:0;vertical-align:top;}\n"
                + "    .question-context-table .question-context-text-cell{width:auto;min-width:0;padding-right:.85rem;}\n"
                + "    .question-context-table .question-context-figure-cell{width:18rem;max-width:18rem;text-align:center;}\n"
                + "    .question-context-table .question-context-text-cell > p:first-child{margin-top:0;}\n"
                + "    .question-context-table .question-context-text-cell > p:last-child{margin-bottom:0;}\n"
                + "    .question-context-table .context-figure{margin:0;text-align:center;}\n"
                + "    .question-context-table .context-figure .context-figure-image{display:block;width:auto;max-width:100%;height:auto;margin:0 auto;}\n"
                + "    @media (max-width:760px){.question-context-table,.question-context-table tbody,.question-context-table tr,.question-context-table .question-context-text-cell,.question-context-table .question-context-figure-cell{display:block;width:100%;}.question-context-table .question-context-text-cell{padding-right:0;}.question-context-table .question-context-figure-cell{max-width:100%;margin-top:.5rem;text-align:center;}}\n"
                + "    .essay-figure figcaption,.question-figure figcaption{margin-top:.25rem;font-size:.95em;color:#57606a;}\n"
                + "    .chem-diagram,.chemical-diagram{display:block;width:auto;max-width:30rem;max-width:min(100%,30rem);height:auto;margin:.55rem auto;}\n"
                + "    td .chem-diagram,td .chemical-diagram{max-width:22rem;max-width:min(100%,22rem);margin:.4rem auto;}\n"
                + "    mjx-container[jax=\"CHTML\"]{overflow-x:auto;overflow-y:hidden;}\n"
                + "  </style>\n"
                + mathJax
                + "</head>\n"
                + "<body data-subject=\"" + HtmlUtil.escapeAttribute(subject.cliName()) + "\">\n"
                + body
                + "</body>\n"
                + "</html>\n";
    }

    private static Document parseXml(String xml) throws Exception {
        return XML_BUILDER.get().parse(new InputSource(new StringReader(xml)));
    }

    private static String serializeNode(Node node) throws Exception {
        StringWriter writer = new StringWriter();
        NODE_SERIALIZER.get().transform(new DOMSource(node), new StreamResult(writer));
        return writer.toString();
    }

    private static String enforceMathDisplay(String mathml, boolean displayBlock) {
        if (mathml == null || mathml.isBlank()) {
            return mathml;
        }
        String out = MATHML_DISPLAY_ATTR_PATTERN.matcher(mathml).replaceAll("");
        if (displayBlock) {
            out = out.replaceFirst("<math(\\s|>)", "<math display=\"block\"$1");
        }
        return out;
    }

    private static boolean containsWordFieldLeakageMarkers(String value) {
        if (value == null || value.isBlank()) {
            return false;
        }
        String lower = value.toLowerCase(Locale.ROOT);
        return lower.contains("includepicture")
                || lower.contains("mergeformat")
                || lower.contains("\\*")
                || lower.contains("&quot;http")
                || lower.contains("&quot;https");
    }

    private static boolean containsCoreHtmlScriptNormalizationSignals(String value) {
        if (value == null || value.isBlank()) {
            return false;
        }
        if (value.contains("<sub>") || value.contains("<sup>")) {
            return true;
        }
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            if (isUnicodeSubscript(ch) || isUnicodeSuperscript(ch)) {
                return true;
            }
        }
        return false;
    }

    private static boolean containsEquationFallbackCandidates(String value) {
        return value.contains("equation-fallback")
                || value.contains("equation-preview")
                || value.contains("unsupported-equation");
    }

    private static long nanosToMillis(long nanos) {
        return TimeUnit.NANOSECONDS.toMillis(Math.max(0L, nanos));
    }

    private static DocumentBuilder newSecureDocumentBuilder() {
        try {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            return factory.newDocumentBuilder();
        } catch (ParserConfigurationException ex) {
            throw new IllegalStateException("Unable to initialize secure XML parser", ex);
        }
    }

    private static Transformer newSecureNodeSerializer() {
        try {
            TransformerFactory factory = TransformerFactory.newInstance();
            factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            Transformer transformer = factory.newTransformer();
            transformer.setOutputProperty(OutputKeys.OMIT_XML_DECLARATION, "yes");
            transformer.setOutputProperty(OutputKeys.INDENT, "no");
            return transformer;
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to initialize secure XML serializer", ex);
        }
    }

    private static Element findDescendant(Element root, String localName) {
        if (root == null) {
            return null;
        }
        if (localName.equals(root.getLocalName())) {
            return root;
        }
        NodeList children = root.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node node = children.item(i);
            if (node.getNodeType() == Node.ELEMENT_NODE) {
                Element found = findDescendant((Element) node, localName);
                if (found != null) {
                    return found;
                }
            }
        }
        return null;
    }

    private static Element findDirectChild(Element root, String localName) {
        if (root == null) {
            return null;
        }
        NodeList children = root.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child.getNodeType() == Node.ELEMENT_NODE && localName.equals(((Element) child).getLocalName())) {
                return (Element) child;
            }
        }
        return null;
    }

    private static String attrByLocalName(Element element, String localName) {
        NamedNodeMap attributes = element.getAttributes();
        for (int i = 0; i < attributes.getLength(); i++) {
            Node attr = attributes.item(i);
            if (localName.equals(attr.getLocalName()) || localName.equals(attr.getNodeName())) {
                return attr.getNodeValue();
            }
        }
        return null;
    }

    private static String stripExtension(String name) {
        int dot = name.lastIndexOf('.');
        return (dot > 0) ? name.substring(0, dot) : name;
    }

    private enum OleKind {
        DSMT4_EQUATION,
        EQUATION,
        DIAGRAM,
        CHEMICAL_DIAGRAM,
        ILLUSTRATION

        ;

        private String dataValue() {
            return switch (this) {
                case DSMT4_EQUATION -> "equation-dsmt4";
                case EQUATION -> "equation";
                case DIAGRAM -> "diagram";
                case CHEMICAL_DIAGRAM -> "chemical-diagram";
                case ILLUSTRATION -> "illustration";
            };
        }
    }

    private record SavedBinary(String relativePath, String sourceExtension, boolean rasterizedToPng) {
        private boolean isMetafileSource() {
            return isMetafileExtension(sourceExtension);
        }
    }

    private record ReplacementOutcome(String replaced, int hitCount) {
    }

    private record GenericInlineTrimResult(boolean candidate, boolean applied, String trimType, boolean safe) {
        private static GenericInlineTrimResult none() {
            return new GenericInlineTrimResult(false, false, "", true);
        }

        private static GenericInlineTrimResult notCandidate() {
            return new GenericInlineTrimResult(false, false, "", true);
        }

        private static GenericInlineTrimResult applied(String trimType) {
            return new GenericInlineTrimResult(true, true, trimType, true);
        }

        private static GenericInlineTrimResult candidateNotApplied(String trimType, boolean safe) {
            return new GenericInlineTrimResult(true, false, trimType, safe);
        }
    }

    private enum FigureRole {
        ESSENTIAL,
        CONTEXT
    }

    private record EssayInlineFigureSplit(String questionHtml, String imageTag, FigureRole role) {
    }

    private record EssayTableFigureLayout(String textHtml, String imageTag, FigureRole role) {
    }

    private record SegmentSplit(String imageHtml, String trailingHtml) {
    }

    private record SidecarProbe(String html, String debugDetail) {
    }

    private record Dsmt4Resolution(
            Dsmt4ResolutionStatus status,
            String html,
            String sourceExtTrace,
            String sourceAssetTrace,
            String debugDetail
    ) {
    }

    private enum Dsmt4ResolutionStatus {
        RESOLVED,
        MANIFEST_MISSING,
        MANIFEST_MISMATCH
    }

    public record ConversionSummary(
            int ommlEquations,
            int sidecarMathmlEquations,
            int olePreviewImages,
            int olePlaceholders,
            int dsmt4Total,
            int dsmt4SidecarResolved,
            int dsmt4Unresolved,
            int dsmt4ManifestMissing,
            int dsmt4ManifestMismatch,
            int dsmt4FallbackPlaceholderCount,
            int oleEquationPreviews,
            int oleDiagramPreviews,
            int oleIllustrationPreviews,
            int emfWmfPreviewImages,
            int unresolvedVisioPreviews,
            int normalizedTextFixes,
            int chemistryInlineFixes,
            int chemistryArrowSymbolFixes,
            int chemistryUnitFixes,
            int physicsUnitFixes,
            int physicsTextFixes,
            int mixedMathTextCleanupFixes,
            int mathGlyphCleanupFixes,
            int emptyParagraphRemovedCount,
            int tableAdjacentEmptyParagraphCleanupCount,
            int tableCellEmptyParagraphRemovedCount,
            int mathBlockFlowCleanupCount,
            int suppressedBlankStandaloneImageCount,
            int suppressedNonessentialStandaloneImageCount,
            int restoredContextImageCount,
            int rasterizedMetafilePreviews,
            int rasterizedMetafileCacheHits,
            long docxLoadMillis,
            long bodyRenderMillis,
            long essayPolicyMillis,
            long htmlBuildMillis,
            long publishSanitizeMillis,
            long htmlWriteMillis,
            long ommlHandlingMillis,
            long mathTypeHandlingMillis,
            long imageRenderingMillis,
            long htmlCleanupMillis
    ) {
    }
}
