package com.example.docxmath.word;

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
        if (trimmed.isEmpty()) {
            return null;
        }
        try {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            Document document = factory.newDocumentBuilder().parse(new InputSource(new StringReader(trimmed)));
            Element root = document.getDocumentElement();
            if (root != null && "math".equals(root.getLocalName()) && root.getNamespaceURI() == null) {
                root.setAttributeNS(XMLConstants.XMLNS_ATTRIBUTE_NS_URI, "xmlns", MATHML_NS);
            }
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
            String strippedXmlDeclaration = trimmed.replaceFirst("^<\\?xml[^>]*>\\s*", "");
            return stripKnownGlyphArtifacts(strippedXmlDeclaration);
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
