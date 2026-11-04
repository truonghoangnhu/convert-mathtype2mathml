package com.example.docxmath.word;

import com.example.docxmath.MathmlContent;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.StringReader;
import java.io.StringWriter;

import org.xml.sax.InputSource;

public final class BasicMathmlNormalizer implements MathmlNormalizer {
    private static final String MATHML_NS = "http://www.w3.org/1998/Math/MathML";
    private static final char KNOWN_PRIVATE_USE_GLYPH_ARTIFACT = '\uEF0A';

    @Override
    public String normalize(String rawMathml) {
        if (rawMathml == null) {
            return null;
        }
        String trimmed = rawMathml.trim();
        if (!MathmlContent.hasFormula(trimmed)) {
            return null;
        }
        try {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
            factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
            Document document = factory.newDocumentBuilder().parse(new InputSource(new StringReader(trimmed)));
            normalizeElementNamespaces(document, document.getDocumentElement());
            sanitizeKnownGlyphArtifacts(document);
            TransformerFactory transformerFactory = TransformerFactory.newInstance();
            transformerFactory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            Transformer transformer = transformerFactory.newTransformer();
            transformer.setOutputProperty(OutputKeys.OMIT_XML_DECLARATION, "yes");
            transformer.setOutputProperty(OutputKeys.INDENT, "no");
            StringWriter out = new StringWriter();
            transformer.transform(new DOMSource(document), new StreamResult(out));
            return out.toString().trim();
        } catch (Exception ex) {
            return null;
        }
    }

    private static void normalizeElementNamespaces(Document document, Element element) {
        if (element.getNamespaceURI() == null) {
            element = (Element) document.renameNode(element, MATHML_NS, element.getNodeName());
        }
        if ("annotation".equals(element.getLocalName()) || "annotation-xml".equals(element.getLocalName())) {
            return;
        }
        for (Node child = element.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (child instanceof Element e) normalizeElementNamespaces(document, e);
        }
    }

    private static void sanitizeKnownGlyphArtifacts(Document document) {
        if (document == null) {
            return;
        }
        sanitizeNodeText(document.getDocumentElement());
    }

    private static void sanitizeNodeText(Node node) {
        if (node == null) {
            return;
        }
        if (node.getNodeType() == Node.TEXT_NODE) {
            String value = node.getNodeValue();
            String sanitized = stripKnownGlyphArtifacts(value);
            if (!sanitized.equals(value)) {
                node.setNodeValue(sanitized);
            }
            return;
        }
        NodeList children = node.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            sanitizeNodeText(children.item(i));
        }
    }

    private static String stripKnownGlyphArtifacts(String text) {
        if (text == null || text.indexOf(KNOWN_PRIVATE_USE_GLYPH_ARTIFACT) < 0) {
            return text;
        }
        return text.replace(String.valueOf(KNOWN_PRIVATE_USE_GLYPH_ARTIFACT), "");
    }
}
