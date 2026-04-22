package com.example.docxmath.word;

import org.w3c.dom.Document;
import org.w3c.dom.Element;

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
            TransformerFactory transformerFactory = TransformerFactory.newInstance();
            transformerFactory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            Transformer transformer = transformerFactory.newTransformer();
            transformer.setOutputProperty(OutputKeys.OMIT_XML_DECLARATION, "yes");
            transformer.setOutputProperty(OutputKeys.INDENT, "no");
            StringWriter out = new StringWriter();
            transformer.transform(new DOMSource(document), new StreamResult(out));
            return out.toString().trim();
        } catch (Exception ex) {
            return trimmed.replaceFirst("^<\\?xml[^>]*>\\s*", "");
        }
    }
}
