package com.example.docxmath.word;

import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFStyles;
import org.w3c.dom.Element;
import org.w3c.dom.Node;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Decides whether an object-only paragraph can become a display equation without moving.
 *
 * <p>Word places an {@code m:oMathPara} by its own {@code m:jc} and does not apply the paragraph
 * alignment to it, whereas the OLE it replaces was an inline picture laid out by the paragraph.
 * Plain left/right/centred paragraphs use explicit mathematical justification. Word also centres
 * a lone inline oMath, so an inline fallback does not preserve placement. Indentation, numbering,
 * frame, bidi and unresolved style conflicts require review and retain the original object.
 */
final class DisplayEquationPlacement {
    private static final String WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
    private static final Set<String> CONTROLLED = Set.of("jc", "ind", "numPr", "bidi", "framePr");

    private DisplayEquationPlacement() {
    }

    static boolean keepsSourcePlacement(XWPFParagraph paragraph) {
        return justification(paragraph) != null;
    }

    static String justification(XWPFParagraph paragraph) {
        Element paragraphNode = (Element) paragraph.getCTP().getDomNode();
        StyleSheet styles = StyleSheet.of(paragraph.getDocument());
        Element direct = child(paragraphNode, "pPr");

        List<Element> paragraphStyles = styleChain(styles, styleId(direct, "pStyle", styles.defaultParagraphStyle()), "pPr");
        Element table = nearestAncestor(paragraphNode, "tbl");
        List<Element> tableStyles = List.of();
        if (table != null) {
            List<Element> chain = styleChain(styles, styleId(child(table, "tblPr"), "tblStyle", null), null);
            for (Element style : chain) {
                for (Element conditional : children(style, "tblStylePr")) {
                    if (controlsLayout(child(conditional, "pPr"))) {
                        return null;
                    }
                }
            }
            tableStyles = chain.stream().map(style -> child(style, "pPr")).filter(p -> p != null).toList();
        }
        Element defaults = styles.documentDefaults();

        // Paragraph style before table style before document defaults (ECMA-376 17.7.2).
        List<Element> sources = new ArrayList<>();
        if (direct != null) sources.add(direct);
        sources.addAll(paragraphStyles);
        sources.addAll(tableStyles);
        if (defaults != null) sources.add(defaults);

        if (direct == null || child(direct, "jc") == null) {
            String fromParagraphStyles = firstValue(paragraphStyles, "jc");
            String fromTableStyles = firstValue(tableStyles, "jc");
            if (fromParagraphStyles != null && fromTableStyles != null && !fromParagraphStyles.equals(fromTableStyles)) {
                return null;
            }
        }
        String alignment = firstValue(sources, "jc");
        // A lone oMath is displayed and centred by Word even when w:jc says left.
        // State the alignment on oMathPara instead of relying on an inline fallback.
        String mathAlignment = alignment == null ? "left" : switch (alignment) {
            case "center" -> "centerGroup";
            case "left", "both" -> "left"; // a sole image occupies the last line
            case "right" -> "right";
            default -> null;
        };
        Element numbering = first(sources, "numPr");
        if (numbering != null && !"0".equals(wordValue(child(numbering, "numId")))) {
            return null;
        }
        Element bidi = first(sources, "bidi");
        if (bidi != null && isOn(bidi)) {
            return null;
        }
        if (first(sources, "framePr") != null) {
            return null;
        }
        return indented(sources) ? null : mathAlignment;
    }

    // Indentation attributes merge one by one along the hierarchy; any non-zero value moves the line.
    private static boolean indented(List<Element> sources) {
        Map<String, String> effective = new HashMap<>();
        for (Element source : sources) {
            Element ind = child(source, "ind");
            if (ind == null) continue;
            for (int i = 0; i < ind.getAttributes().getLength(); i++) {
                Node attribute = ind.getAttributes().item(i);
                if (WORD_NS.equals(attribute.getNamespaceURI())) {
                    effective.putIfAbsent(attribute.getLocalName(), attribute.getNodeValue());
                }
            }
        }
        for (String value : effective.values()) {
            try {
                if (Integer.parseInt(value.trim()) != 0) return true;
            } catch (NumberFormatException ex) {
                return true;
            }
        }
        return false;
    }

    private static boolean controlsLayout(Element paragraphProperties) {
        if (paragraphProperties == null) return false;
        for (Node c = paragraphProperties.getFirstChild(); c != null; c = c.getNextSibling()) {
            if (WORD_NS.equals(c.getNamespaceURI()) && CONTROLLED.contains(c.getLocalName())) return true;
        }
        return false;
    }

    private record StyleSheet(Map<String, Element> byId, String defaultParagraphStyle, Element documentDefaults) {
        static StyleSheet of(XWPFDocument document) {
            Map<String, Element> byId = new HashMap<>();
            XWPFStyles styles = document == null ? null : document.getStyles();
            if (styles == null || styles.getCtStyles() == null) return new StyleSheet(byId, null, null);
            Element root = (Element) styles.getCtStyles().getDomNode();
            String defaultParagraph = null;
            for (Element style : children(root, "style")) {
                String id = style.getAttributeNS(WORD_NS, "styleId");
                if (id.isEmpty()) continue;
                byId.putIfAbsent(id, style);
                if (defaultParagraph == null && "paragraph".equals(style.getAttributeNS(WORD_NS, "type"))
                        && style.hasAttributeNS(WORD_NS, "default") && isOnValue(style.getAttributeNS(WORD_NS, "default"))) {
                    defaultParagraph = id;
                }
            }
            return new StyleSheet(byId, defaultParagraph, child(child(child(root, "docDefaults"), "pPrDefault"), "pPr"));
        }
    }

    // Styles from the given one up its basedOn chain; with a child name, that child of each style.
    private static List<Element> styleChain(StyleSheet styles, String styleId, String childName) {
        List<Element> chain = new ArrayList<>();
        List<String> seen = new ArrayList<>();
        while (styleId != null && !seen.contains(styleId)) {
            seen.add(styleId);
            Element style = styles.byId().get(styleId);
            if (style == null) break;
            if (childName == null) {
                chain.add(style);
            } else if (child(style, childName) != null) {
                chain.add(child(style, childName));
            }
            styleId = wordValue(child(style, "basedOn"));
        }
        return chain;
    }

    private static String styleId(Element properties, String name, String fallback) {
        String value = wordValue(child(properties, name));
        return value == null || value.isEmpty() ? fallback : value;
    }

    private static Element first(List<Element> sources, String name) {
        for (Element source : sources) {
            Element found = child(source, name);
            if (found != null) return found;
        }
        return null;
    }

    private static String firstValue(List<Element> sources, String name) {
        return wordValue(first(sources, name));
    }

    private static boolean isOn(Element toggle) {
        return !toggle.hasAttributeNS(WORD_NS, "val") || isOnValue(toggle.getAttributeNS(WORD_NS, "val"));
    }

    private static boolean isOnValue(String value) {
        return !("0".equals(value) || "false".equals(value) || "off".equals(value));
    }

    private static String wordValue(Element element) {
        return element == null || !element.hasAttributeNS(WORD_NS, "val") ? null : element.getAttributeNS(WORD_NS, "val");
    }

    private static Element nearestAncestor(Node node, String name) {
        for (Node n = node.getParentNode(); n != null; n = n.getParentNode()) {
            if (WORD_NS.equals(n.getNamespaceURI()) && name.equals(n.getLocalName())) return (Element) n;
        }
        return null;
    }

    private static Element child(Element parent, String name) {
        if (parent == null) return null;
        for (Node c = parent.getFirstChild(); c != null; c = c.getNextSibling()) {
            if (c instanceof Element e && WORD_NS.equals(e.getNamespaceURI()) && name.equals(e.getLocalName())) return e;
        }
        return null;
    }

    private static List<Element> children(Element parent, String name) {
        List<Element> found = new ArrayList<>();
        if (parent == null) return found;
        for (Node c = parent.getFirstChild(); c != null; c = c.getNextSibling()) {
            if (c instanceof Element e && WORD_NS.equals(e.getNamespaceURI()) && name.equals(e.getLocalName())) found.add(e);
        }
        return found;
    }
}
