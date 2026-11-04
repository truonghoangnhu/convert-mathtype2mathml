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
        if (xml == null || xml.isBlank()) return false;
        try {
            Element root = parseRoot(xml);
            String ns = "http://schemas.openxmlformats.org/officeDocument/2006/math";
            if (!ns.equals(root.getNamespaceURI())
                    || !("oMath".equals(root.getLocalName()) || "oMathPara".equals(root.getLocalName()))) return false;
            var tokens = root.getElementsByTagNameNS(ns, "t");
            boolean hasText = false;
            for (int i = 0; i < tokens.getLength(); i++) {
                Node token = tokens.item(i);
                Node parent = token.getParentNode();
                if (!ns.equals(parent.getNamespaceURI()) || !"r".equals(parent.getLocalName())) return false;
                hasText |= token.getTextContent().codePoints()
                        .anyMatch(c -> !Character.isWhitespace(c) && !Character.isSpaceChar(c));
            }
            return hasText && !hasBareText(root, ns);
        } catch (Exception ex) {
            return false;
        }
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
            String text = element.getTextContent().replace("\uEF0A", "");
            return text.codePoints().anyMatch(c -> !Character.isWhitespace(c) && !Character.isSpaceChar(c));
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
