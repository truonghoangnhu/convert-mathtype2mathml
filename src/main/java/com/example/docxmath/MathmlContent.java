package com.example.docxmath;

import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.xml.sax.InputSource;
import org.xml.sax.helpers.DefaultHandler;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.StringReader;
import java.util.Set;

/** A nonempty presentation-content gate, not a formula-equivalence validator. */
public final class MathmlContent {
    private static final String NS = "http://www.w3.org/1998/Math/MathML";
    private static final Set<String> TOKENS = Set.of("mi", "mn", "mo", "mtext", "ms");
    private static final Set<String> HIDDEN = Set.of(
            "annotation", "annotation-xml", "mphantom", "mspace", "none", "mprescripts");
    private static final int KNOWN_ARTIFACT = 0xEF0A;
    private static final java.util.regex.Pattern NORMAL_TEXT_SYMBOLS_REQUIRING_REVIEW = loadSymbolReviewPattern();

    private static java.util.regex.Pattern loadSymbolReviewPattern() {
        try (var stream = MathmlContent.class.getResourceAsStream("/letterlike_policy.xml")) {
            if (stream == null) throw new IllegalStateException("Missing letterlike_policy.xml");
            Element policy = parseRoot(new String(stream.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8));
            return java.util.regex.Pattern.compile(policy.getAttribute("review-class"));
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to load symbol review policy", ex);
        }
    }

    private MathmlContent() {}

    public static boolean hasFormula(String xml) {
        if (xml == null || xml.isBlank()) return false;
        try {
            Element root = parseRoot(xml);
            return "math".equals(root.getLocalName()) && validNamespace(root) && containsToken(root);
        } catch (Exception ex) {
            return false;
        }
    }

    public static boolean hasOmmlRunContent(String xml) {
        return ommlRejectionReason(xml) == null;
    }

    /** Null when eligible, otherwise a stable diagnostic; eligibility is not acceptance. */
    public static String ommlRejectionReason(String xml) {
        if (xml == null || xml.isBlank()) return "empty_omml";
        try {
            Element root = parseRoot(xml);
            String ns = "http://schemas.openxmlformats.org/officeDocument/2006/math";
            if (!ns.equals(root.getNamespaceURI())
                    || !("oMath".equals(root.getLocalName()) || "oMathPara".equals(root.getLocalName()))) return "invalid_omml_root";
            var tokens = root.getElementsByTagNameNS(ns, "t");
            boolean hasText = false;
            for (int i = 0; i < tokens.getLength(); i++) {
                Node token = tokens.item(i);
                Node parent = token.getParentNode();
                if (!ns.equals(parent.getNamespaceURI()) || !"r".equals(parent.getLocalName())) return "invalid_math_text_parent";
                // Unverified normal-text symbols keep the OLE; only four have measured
                // Word roundtrips. Do not infer behavior for the entire Unicode blocks.
                var nor = ((Element) parent).getElementsByTagNameNS(ns, "nor");
                if (nor.getLength() > 0) {
                    String value = ((Element) nor.item(0)).getAttributeNS(ns, "val");
                    if (!Set.of("0", "false", "off").contains(value)
                            && NORMAL_TEXT_SYMBOLS_REQUIRING_REVIEW.matcher(token.getTextContent()).find())
                        return "normal_text_symbol_requires_review";
                }
                hasText |= hasVisibleCodePoint(token.getTextContent());
            }
            if (!hasText) return "empty_math_content";
            if (hasBareText(root, ns)) return "bare_math_text";
            if (hasEmptyScriptBase(root, ns)) return "missing_script_base";
            return null;
        } catch (Exception ex) {
            return "invalid_omml_xml";
        }
    }

    /**
     * Whether a code point shows something by itself. Controls (Cc), format characters (Cf, e.g.
     * U+2061, U+2062, U+200B, U+00AD) and separators (Zs, Zl, Zp) do not, nor does the known
     * MathType artifact U+EF0A. CGJ and variation selectors are invisible nonspacing marks
     * (Mn), so checking only general categories misses them. They only gate a token:
     * a formula keeps them beside visible
     * content. Shared vectors: fixtures/mathml_content/visible_content_vectors.json.
     */
    public static boolean isVisibleCodePoint(int codePoint) {
        if (codePoint == KNOWN_ARTIFACT || Character.isWhitespace(codePoint)) return false;
        // Unicode variation selectors and COMBINING GRAPHEME JOINER have no glyph of
        // their own. Keep ordinary combining accents and visible base+selector sequences.
        if (codePoint == 0x034F || (codePoint >= 0x180B && codePoint <= 0x180D)
                || codePoint == 0x180F || (codePoint >= 0xFE00 && codePoint <= 0xFE0F)
                || (codePoint >= 0xE0100 && codePoint <= 0xE01EF)) return false;
        return switch (Character.getType(codePoint)) {
            case Character.CONTROL, Character.FORMAT, Character.SPACE_SEPARATOR,
                 Character.LINE_SEPARATOR, Character.PARAGRAPH_SEPARATOR -> false;
            default -> true;
        };
    }

    private static boolean hasVisibleCodePoint(String text) {
        return text.codePoints().anyMatch(MathmlContent::isVisibleCodePoint);
    }

    // These scripts need their own base. A neighbouring text run does not fill an empty m:e:
    // Word and Writer draw a placeholder. Do not guess whether to attach the script to a
    // preceding digit or a following chemical symbol; retain the original OLE for review.
    // Optional n-ary sub/sup limits are deliberately outside this bounded check.
    private static boolean hasEmptyScriptBase(Element root, String ns) {
        for (String name : Set.of("sSup", "sSub", "sSubSup", "sPre")) {
            var scripts = root.getElementsByTagNameNS(ns, name);
            for (int i = 0; i < scripts.getLength(); i++) {
                Element base = null;
                for (Node child = scripts.item(i).getFirstChild(); child != null; child = child.getNextSibling()) {
                    if (child instanceof Element e && ns.equals(e.getNamespaceURI()) && "e".equals(e.getLocalName())) {
                        base = e;
                        break;
                    }
                }
                if (base == null || !hasScriptBaseContent(base, ns)) return true;
            }
        }
        return false;
    }

    private static boolean hasScriptBaseContent(Element element, String ns) {
        if (!ns.equals(element.getNamespaceURI()) || element.getLocalName().endsWith("Pr")) return false;
        if ("t".equals(element.getLocalName())) return hasVisibleCodePoint(element.getTextContent());
        // Runs and transparent grouping boxes need actual content. Other math structures
        // (e.g. delimiters, radicals and fractions) can draw visible geometry of their own.
        if (!Set.of("e", "r", "box").contains(element.getLocalName())) return true;
        for (Node child = element.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (child instanceof Element e && hasScriptBaseContent(e, ns)) return true;
        }
        return false;
    }

    private static boolean hasBareText(Node node, String ns) {
        if (node.getNodeType() == Node.TEXT_NODE && !node.getNodeValue().isBlank()) {
            Node parent = node.getParentNode();
            return !ns.equals(parent.getNamespaceURI()) || !"t".equals(parent.getLocalName());
        }
        for (Node child = node.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (hasBareText(child, ns)) return true;
        }
        return false;
    }

    private static Element parseRoot(String xml) throws Exception {
        var factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        var builder = factory.newDocumentBuilder();
        builder.setErrorHandler(new DefaultHandler());
        return builder.parse(new InputSource(new StringReader(xml))).getDocumentElement();
    }

    private static boolean validNamespace(Element element) {
        return element.getNamespaceURI() == null || NS.equals(element.getNamespaceURI());
    }

    private static boolean containsToken(Element element) {
        if (!validNamespace(element) || HIDDEN.contains(element.getLocalName())) return false;
        if (TOKENS.contains(element.getLocalName())) {
            return hasVisibleCodePoint(element.getTextContent());
        }
        // Only the presentation branch of semantics is eligible; annotations are metadata.
        if ("semantics".equals(element.getLocalName())) {
            for (Node child = element.getFirstChild(); child != null; child = child.getNextSibling()) {
                if (child instanceof Element e) return containsToken(e);
            }
            return false;
        }
        for (Node child = element.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (child instanceof Element e && containsToken(e)) return true;
        }
        return false;
    }
}
